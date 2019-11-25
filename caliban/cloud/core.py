"""cloud utilities."""

from __future__ import absolute_import, division, print_function

import datetime
from pprint import pformat
from typing import Any, Dict, Iterable, List, Optional

from absl import logging
from googleapiclient import discovery

import caliban.cloud.types as ct
import caliban.docker as d
import caliban.util as u

# Max number of jobs we can create in a single batch submission to AI platform.
ML_JOB_CREATION_LIMIT = 1000
DRY_RUN_FLAG = "--dry_run"

# Defaults for various input values that we can supply given some partial set
# of info from the CLI.
DEFAULT_REGION = ct.US.central1
DEFAULT_MACHINE_TYPE: Dict[ct.JobMode, ct.MachineType] = {
    ct.JobMode.CPU: ct.MachineType.highcpu_32,
    ct.JobMode.GPU: ct.MachineType.standard_8,
    ct.JobMode.TPU: ct.MachineType.cloud_tpu
}
DEFAULT_GPU = ct.GPU.P100

# Config to supply for CPU jobs.
DEFAULT_ACCELERATOR_CONFIG = {
    "count": 0,
    "type": "ACCELERATOR_TYPE_UNSPECIFIED"
}

# Marker type to make things more readable below.
JobSpec = Dict[str, Any]

# Marker type for our experiment config.
ExpConf = Dict[str, Any]


def get_accelerator_config(gpu_spec: Optional[ct.GPUSpec]) -> Dict[str, Any]:
  """Returns the accelerator config for the supplied GPUSpec if present; else,
  returns the default accelerator config.

  """
  conf = DEFAULT_ACCELERATOR_CONFIG

  if gpu_spec is not None:
    conf = gpu_spec.accelerator_config()

  return conf


def experiment_config_to_args(m: ExpConf, base: List[str]) -> List[str]:
  """Returns the list of flag keys and values that corresponds to the supplied
  experiment configuration.

  Keys all expand to the full '--key_name' style that typical Python flags are
  represented by.

  All values except for boolean values are inserted as str(v). For boolean
  values, if the value is True, the key is inserted by itself (in the format
  --key_name). If the value is False, the key isn't inserted at all.

  """
  ret = [] + base

  for k, v in m.items():
    opt = f"--{k}"
    if isinstance(v, bool):
      # Append a flag if the boolean flag is true, else do nothing.
      if v:
        ret.append(opt)
    else:
      ret.append(f"--{k}")
      ret.append(str(v))

  return ret


def job_url(project_id: str, job_id: str) -> str:
  """Returns a URL that will load the default page for the newly launched AI
  Platform job.

  """
  prefix = "https://pantheon.corp.google.com/ai-platform/jobs"
  return f"{prefix}/{job_id}?projectId={project_id}"


def _stream_cmd(job_id: str) -> str:
  """Returns a CLI command that, if executed, will stream the logs for the job
  with the supplied ID to the terminal.

  """
  items = ["gcloud", "ai-platform", "jobs", "stream-logs", job_id]
  return " ".join(items)


def logging_callback(spec: JobSpec, project_id: str):
  """Returns a callback of the format required by the GCloud REST api's job
  creation endpoint. The returned function accepts:

  - a request_id
  - a Job object, in case the request succeeds:
    https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs#Job
  - an exception if the request fails.

  """
  job_id = spec["jobId"]

  def callback(request_id: str, response, exception):
    logging.debug(f"spec for requestId {request_id}: {spec}")
    prefix = f"Req {request_id} for jobId {spec['jobId']}"

    if exception is None:
      url = job_url(project_id, job_id)
      stream_command = _stream_cmd(job_id)

      logging.info(f"{prefix} succeeded!")

      logging.info(f"jobId URL: {url}")
      logging.info(f"Streaming log CLI command: $ {stream_command}")
    else:
      logging.error(f"{prefix} failed! Details:")
      logging.error(exception._get_reason())

  return callback


def log_spec(spec: JobSpec, i: int) -> JobSpec:
  """Returns the input spec after triggering logging side-effects.

  """

  def prefixed(s: str):
    logging.info(f"Job {i} - {s}")

  prefixed(f"jobId: {spec['jobId']}")
  prefixed(f"trainingInput: {spec['trainingInput']}")
  prefixed(f"labels: {spec['labels']}")
  return spec


def logged_specs(specs: Iterable[JobSpec]) -> Iterable[JobSpec]:
  """Returns a generator that produces the same values as the supplied iterable;
  wrapping the iterable in `logged_specs` will trigger a logging side-effect
  for each JobSpec instance before it's produced.

  """
  for i, spec in enumerate(specs, 1):
    yield log_spec(spec, i)


def logged_batches(specs: Iterable[JobSpec],
                   limit: int) -> Iterable[Iterable[JobSpec]]:
  """Accepts an iterable of specs and a 'chunk limit'; returns an iterable of
  iterable of JobSpec, each of which is guaranteed to contain at most 'chunk
  limit' items.

  The subsequences don't pull contiguous chunks off of the original input
  sequence, but the set of the union of the subsequences is the set of all
  original items.

  As you realize the generator you'll trigger:

  - a logging side-effect at the beginning of each batch
  - a logging effect between each item in each batch

  These logging effects will track the index of each batch and each item within
  the batch.

  """
  # Realize the input generator to get a count for logging.
  spec_list = list(specs)
  total_specs = len(spec_list)

  # Build N chunks such that each chunk contains <= items than the supplied
  # limit.
  chunked_seq = u.chunks_below_limit(spec_list, limit=limit)
  total_chunks = len(chunked_seq)

  # Go the extra mile.
  plural_batch = "batch" if total_chunks == 1 else "batches"
  plural_job = "job" if total_specs == 1 else "jobs"
  logging.info(
      f"Generating {total_chunks} {plural_batch} for {total_specs} {plural_job}."
  )
  for i, chunk in enumerate(chunked_seq, 1):
    logging.info(f"Batch {i} of {total_chunks}:")
    yield logged_specs(chunk)


def log_batch_parameters(specs: Iterable[JobSpec],
                         limit: int = ML_JOB_CREATION_LIMIT
                        ) -> List[List[JobSpec]]:
  """Equivalent to logged_batches, except all logging side effects are forced to
  occur immediately before return.

  Returns the realized list of lists of JobSpec instances.

  """
  return [list(batch) for batch in logged_batches(specs, limit=limit)]


def create_request_batches(specs: List[JobSpec],
                           project_id: str,
                           limit: int = ML_JOB_CREATION_LIMIT) -> Iterable[Any]:
  """Returns an iterator of BatchHttpRequest instances:
  https://googleapis.github.io/google-api-python-client/docs/epy/googleapiclient.http.BatchHttpRequest-class.html#execute

  Each batch contains requests corresponding to a a
  roughly-equal-in-cardinality subset of the supplied list of specs.

  Iterating across the batches will trigger logging side-effects for each spec
  added to its batch.

  Cloud API docs for the endpoint that we're batch-submitting to:
  https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs/create

  Python specific docs:
  http://googleapis.github.io/google-api-python-client/docs/dyn/ml_v1.projects.jobs.html#create

  """
  parent = f"projects/{project_id}"

  # cache_discovery=False prevents an error bubbling up from a missing file
  # cache, which no user of this code is going to be using.
  ml = discovery.build('ml', 'v1', cache_discovery=False)
  jobs = ml.projects().jobs()

  for spec_batch in logged_batches(specs, limit=limit):
    request_batch = ml.new_batch_http_request()

    for spec in spec_batch:
      req = jobs.create(body=spec, parent=parent)
      request_batch.add(req, callback=logging_callback(spec, project_id))

    yield request_batch


def execute_batches(batches: Iterable[Any]) -> None:
  """Execute all batches in the supplied generator of batch requests. Results
  aren't returned directly; the callbacks passed to each request when it was
  generated handle any response or exception.

  """
  for batch in batches:
    batch.execute()


def base_training_input(image_tag: str, region: ct.Region,
                        machine_type: ct.MachineType,
                        accelerator_conf: Dict[str, Any]) -> Dict[str, Any]:
  """Returns a dictionary that represents a complete TrainingInput with every
  field except for 'args'.

  """
  return {
      "masterConfig": {
          "imageUri": image_tag,
          "acceleratorConfig": accelerator_conf
      },
      "scaleTier": "CUSTOM",
      "masterType": machine_type.value,
      "region": region.value
  }


def _job_spec(job_name: str, idx: int, training_input: Dict[str, Any],
              labels: Dict[str, str], uuid: str) -> JobSpec:
  """Returns the final object required by the Google AI Platform training job
  submission endpoint.

  """
  job_id = f"{job_name}_{idx}_{uuid}"
  job_args = training_input.get("args")
  return {
      "jobId": job_id,
      "trainingInput": training_input,
      "labels": {
          **labels,
          **u.script_args_to_labels(job_args)
      }
  }


def expand_experiment_config(m: ExpConf) -> Iterable[ExpConf]:
  """Expand out the experiment config for job submission to Cloud. This is where
  to add support for more expressive forms of experiment config.

  """
  return u.dict_product(m)


def _job_specs(job_name: str, training_input: Dict[str, Any],
               base_args: List[str], labels: Dict[str, str], uuid: str,
               experiment_config: ExpConf) -> Iterable[JobSpec]:
  """Returns a generator that yields a JobSpec instance for every possible
  combination of parameters in the supplied experiment config.

  All other arguments parametrize every JobSpec that's generated; labels,
  arguments and job id change for each JobSpec.

  This is lower-level than build_job_specs below.

  """
  expanded = expand_experiment_config(experiment_config)
  for idx, m in enumerate(expanded):
    args = experiment_config_to_args(m, base_args)
    yield _job_spec(job_name=job_name,
                    idx=idx,
                    training_input={
                        **training_input, "args": args
                    },
                    labels=labels,
                    uuid=uuid)


def build_job_specs(job_name: str, image_tag: str, region: ct.Region,
                    machine_type: ct.MachineType, script_args: List[str],
                    experiment_config: Dict[str, Any],
                    user_labels: Dict[str, str],
                    gpu_spec: Optional[ct.GPUSpec]) -> Iterable[JobSpec]:
  """Returns a generator that yields a JobSpec instance for every possible
  combination of parameters in the supplied experiment config.

  All other arguments parametrize every JobSpec that's generated. Various base
  labels such as 'gpu_enabled', etc are filled in for each job.

  Each job in the batch will have a unique jobId.

  """
  logging.info(f"Building job with name: {job_name}")

  uuid = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

  accelerator_conf = get_accelerator_config(gpu_spec)
  training_input = base_training_input(image_tag, region, machine_type,
                                       accelerator_conf)

  # TODO when we support TPUs this might take JobMode and use that instead.
  gpu_enabled = gpu_spec is not None
  base_labels = {
      "gpu_enabled": str(gpu_enabled).lower(),
      "job_name": job_name,
      **user_labels
  }

  return _job_specs(job_name,
                    training_input=training_input,
                    base_args=script_args,
                    labels=base_labels,
                    experiment_config=experiment_config,
                    uuid=uuid)


def _generate_image_tag(project_id, docker_args, dry_run: bool = False):
  """Generates a new Docker image and pushes an image to the user's GCloud
  Container Repository, tagged using the UUID of the generated image.

  If dry_run is true, logs the Docker image build parameters and returns a
  bogus tag.

  """
  logging.info("Generating Docker image with parameters:")
  logging.info(pformat(docker_args))

  if dry_run:
    logging.info("Dry run - skipping actual 'docker build' and 'docker push'.")
    image_tag = "dry_run_tag"
  else:
    image_id = d.build_image(**docker_args)
    image_tag = d.push_uuid_tag(project_id, image_id)

  return image_tag


def submit_ml_job(use_gpu: bool,
                  docker_args: Dict[str, Any],
                  region: ct.Region,
                  project_id: str,
                  dry_run: bool = False,
                  job_name: Optional[str] = None,
                  machine_type: Optional[ct.MachineType] = None,
                  gpu_spec: Optional[ct.GPUSpec] = None,
                  labels: Optional[Dict[str, str]] = None,
                  experiment_config: Optional[ExpConf] = None,
                  script_args: Optional[List[str]] = None) -> None:
  """Top level function in the module. This function:

  - builds an image using the supplied docker_args, in either CPU or GPU mode
  - pushes that image to the Cloud Container Repository of the supplied
    project_id
  - generates a sequence of 'JobSpec' instances, one for every combination in
    the supplied experiment_config, and
  - batch-submits all jobs to AI Platform

  Keyword args:

  - use_gpu: if True, builds the supplied container in GPU mode and sets
    machine_type and GPU defaults for the submitted jobs.
  - docker_args: these arguments are passed through to
    caliban.docker.build_image.
  - region: the region to use for AI Platform job submission. Different regions
    support different GPUs.
  - project_id: GCloud project ID for container storage and job submission.
  - dry_run: if True, no actual jobs will be submitted and docker won't
    actually build; logging side effects will show the user what will happen
    without dry_run=True.
  - job_name: optional custom name. This is applied as a label to every job,
    and used as a prefix for all jobIds submitted to Cloud.
  - machine_type: the machine type to allocate for each job. Must be one
    supported by Cloud.
  - gpu_spec: if None and use_gpu is true, defaults to a standard single GPU.
    Else, configures the count and type of GPUs to attach to the machine that
    runs each job.
  - labels: dictionary of KV pairs to apply to each job. User args will also be
    applied as labels, plus a few default labels supplied by Caliban.
  - experiment_config: dict of string to list, boolean, string or int. Any
    lists will trigger a cartesian product out with the rest of the config. A
    job will be submitted for every combination of parameters in the experiment
    config.
  - script_args: these are extra arguments that will be passed to every job
    executed, in addition to the arguments created by expanding out the
    experiment config.

  """

  job_mode = ct.JobMode.GPU if use_gpu else ct.JobMode.CPU

  if job_mode == ct.JobMode.CPU:
    # This should never happen, due to our CLI validation.
    assert gpu_spec is None, "gpu_spec isn't allowed for CPU only jobs!"

  if script_args is None:
    script_args = []

  if job_name is None:
    job_name = f"caliban_{u.current_user()}"

  if job_mode == ct.JobMode.GPU and gpu_spec is None:
    gpu_spec = ct.GPUSpec(ct.GPU.P100, 1)

  if machine_type is None:
    machine_type = DEFAULT_MACHINE_TYPE[job_mode]

  if experiment_config is None:
    experiment_config = {}

  if labels is None:
    labels = {}

  image_tag = _generate_image_tag(project_id, docker_args, dry_run=dry_run)

  specs = build_job_specs(job_name=job_name,
                          image_tag=image_tag,
                          region=region,
                          machine_type=machine_type,
                          script_args=script_args,
                          experiment_config=experiment_config,
                          user_labels=labels,
                          gpu_spec=gpu_spec)

  request_batches = create_request_batches(specs, project_id)
  if dry_run:
    log_batch_parameters(specs)

    logging.info(f"To build your image and submit these jobs, \
run your command again without {DRY_RUN_FLAG}.")
    return None

  execute_batches(request_batches)
  logging.info("")
  logging.info(
      f"Visit {job_url(project_id, '')} to see the status of all jobs.")
