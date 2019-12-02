"""cloud utilities."""

from __future__ import absolute_import, division, print_function

import datetime
import itertools
from pprint import pformat
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import tqdm
from absl import logging
from googleapiclient import discovery
from googleapiclient.errors import HttpError

import caliban.cloud.types as ct
import caliban.docker as d
import caliban.util as u
from blessings import Terminal

t = Terminal()

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

# int, str and bool are allowed in a final experiment; lists are markers for
# expansion.
ExpValue = Union[int, str, bool]

# Entry in an experiment config. If any values are lists they're expanded into
# a sequence of experiment configs.
Expansion = Dict[str, Union[ExpValue, List[ExpValue]]]

# An experiment config can be a single (potentially expandable) dictionary, or
# a list of many such dicts.
ExpConf = Union[Expansion, List[Expansion]]

# A final experiment can only contain valid ExpValues, no expandable entries.
Experiment = Dict[str, ExpValue]


def get_accelerator_config(gpu_spec: Optional[ct.GPUSpec]) -> Dict[str, Any]:
  """Returns the accelerator config for the supplied GPUSpec if present; else,
  returns the default accelerator config.

  """
  conf = DEFAULT_ACCELERATOR_CONFIG

  if gpu_spec is not None:
    conf = gpu_spec.accelerator_config()

  return conf


def experiment_to_args(m: Experiment, base: List[str]) -> List[str]:
  """Returns the list of flag keys and values that corresponds to the supplied
  experiment.

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

  def callback(_, exception):
    logging.debug(f"spec for job {job_id}: {spec}")
    prefix = f"Request for job '{spec['jobId']}'"

    if exception is None:
      url = job_url(project_id, job_id)
      stream_command = _stream_cmd(job_id)

      logging.info(t.green(f"{prefix} succeeded!"))
      logging.info(t.green(f"Job URL: {url}"))
      logging.info(t.green(f"Streaming log CLI command: $ {stream_command}"))
    else:
      logging.error(t.red(f"{prefix} failed! Details:"))
      logging.error(t.red(exception._get_reason()))

  return callback


def log_spec(spec: JobSpec, i: int) -> JobSpec:
  """Returns the input spec after triggering logging side-effects.

  """
  job_id = spec['jobId']
  training_input = spec['trainingInput']
  machine_type = training_input['masterType']
  region = training_input['region']
  accelerator = training_input['masterConfig']['acceleratorConfig']
  image_uri = training_input['masterConfig']['imageUri']
  args = training_input['args']

  def prefixed(s: str, level=logging.INFO):
    logging.log(level, f"Job {i} - {s}")

  prefixed(f"Spec: {spec}", logging.DEBUG)
  prefixed(f"jobId: {t.yellow(job_id)}, image: {image_uri}")
  prefixed(
      f"Accelerator: {accelerator}, machine: '{machine_type}', region: '{region}'"
  )
  prefixed(f"Experiment arguments: {t.yellow(str(args))}")
  prefixed(f"labels: {spec['labels']}")
  return spec


def logged_specs(specs: Iterable[JobSpec]) -> Iterable[JobSpec]:
  """Returns a generator that produces the same values as the supplied iterable;
  wrapping the iterable in `logged_specs` will trigger a logging side-effect
  for each JobSpec instance before it's produced.

  """
  for i, spec in enumerate(specs, 1):
    yield log_spec(spec, i)


def log_specs(specs: Iterable[JobSpec]) -> List[JobSpec]:
  """Equivalent to logged_specs, except all logging side effects are forced to
  occur immediately before return.

  Returns the realized list of JobSpec instances.

  """
  return list(logged_specs(specs))


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
                         limit: int) -> List[List[JobSpec]]:
  """Equivalent to logged_batches, except all logging side effects are forced to
  occur immediately before return.

  Returns the realized list of lists of JobSpec instances.

  """
  return [list(batch) for batch in logged_batches(specs, limit=limit)]


def create_requests(specs: List[JobSpec],
                    project_id: str) -> Iterable[Tuple[Any, JobSpec, Any]]:
  """Returns an iterator of (HttpRequest, JobSpec, Callback).

  HttpRequests look like:
  https://googleapis.github.io/google-api-python-client/docs/epy/googleapiclient.http.HttpRequest-class.html

  Iterating across the requests will trigger logging side-effects for its
  corresponding spec.

  Cloud API docs for the endpoint each request submits to:
  https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs/create

  Python specific docs:
  http://googleapis.github.io/google-api-python-client/docs/dyn/ml_v1.projects.jobs.html#create

  """
  parent = f"projects/{project_id}"

  # cache_discovery=False prevents an error bubbling up from a missing file
  # cache, which no user of this code is going to be using.
  ml = discovery.build('ml', 'v1', cache_discovery=False)
  jobs = ml.projects().jobs()

  for spec in logged_specs(specs):
    cb = logging_callback(spec, project_id)
    yield jobs.create(body=spec, parent=parent), spec, cb


def execute(req, callback, num_retries: Optional[int] = None):
  """Executes the supplied request and calls the callback with a first-arg
  response if successful, second-arg exception otherwise.

  num_retries is the number of times a request will be retried if it fails for
  a timeout or a rate limiting (429) exception.

  num_retries = 10 by default.

  """
  if num_retries is None:
    num_retries = 10

  logging.info("Submitting request!")
  try:
    resp = req.execute(num_retries=num_retries)
    callback(resp, None)

  except HttpError as e:
    callback(None, e)


def execute_requests(requests: Iterable[Tuple[Any, JobSpec, Any]],
                     count: Optional[int] = None,
                     num_retries: Optional[int] = None) -> None:
  """Execute all batches in the supplied generator of batch requests. Results
  aren't returned directly; the callbacks passed to each request when it was
  generated handle any response or exception.

  """
  with u.tqdm_logging() as orig_stream:
    pbar = tqdm.tqdm(requests,
                     file=orig_stream,
                     total=count,
                     unit="requests",
                     desc="submitting")
    for req, spec, cb in pbar:
      pbar.set_description(f"Submitting {spec['jobId']}")
      execute(req, cb, num_retries=num_retries)


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
  job_id = f"{job_name}_{uuid}_{idx}"
  job_args = training_input.get("args")
  return {
      "jobId": job_id,
      "trainingInput": training_input,
      "labels": {
          **labels,
          **u.script_args_to_labels(job_args)
      }
  }


def expand_experiment_config(items: ExpConf) -> List[Experiment]:
  """Expand out the experiment config for job submission to Cloud.

  """
  if isinstance(items, list):
    return list(
        itertools.chain.from_iterable(
            [expand_experiment_config(m) for m in items]))

  return list(u.dict_product(items))


def _job_specs(job_name: str, training_input: Dict[str, Any],
               base_args: List[str], labels: Dict[str, str], uuid: str,
               experiments: Iterable[Experiment]) -> Iterable[JobSpec]:
  """Returns a generator that yields a JobSpec instance for every possible
  combination of parameters in the supplied experiment config.

  All other arguments parametrize every JobSpec that's generated; labels,
  arguments and job id change for each JobSpec.

  This is lower-level than build_job_specs below.

  """
  for idx, m in enumerate(experiments, 1):
    args = experiment_to_args(m, base_args)
    yield _job_spec(job_name=job_name,
                    idx=idx,
                    training_input={
                        **training_input, "args": args
                    },
                    labels=labels,
                    uuid=uuid)


def build_job_specs(job_name: str, image_tag: str, region: ct.Region,
                    machine_type: ct.MachineType, script_args: List[str],
                    experiments: Iterable[Experiment],
                    user_labels: Dict[str, str],
                    gpu_spec: Optional[ct.GPUSpec]) -> Iterable[JobSpec]:
  """Returns a generator that yields a JobSpec instance for every possible
  combination of parameters in the supplied experiment config.

  All other arguments parametrize every JobSpec that's generated. Various base
  labels such as 'gpu_enabled', etc are filled in for each job.

  Each job in the batch will have a unique jobId.

  """
  logging.info(f"Building jobs for name: {job_name}")

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
                    experiments=experiments,
                    uuid=uuid)


def _generate_image_tag(project_id, docker_args, dry_run: bool = False):
  """Generates a new Docker image and pushes an image to the user's GCloud
  Container Repository, tagged using the UUID of the generated image.

  If dry_run is true, logs the Docker image build parameters and returns a
  bogus tag.

  """
  logging.info("Generating Docker image with parameters:")
  logging.info(t.yellow(pformat(docker_args)))

  if dry_run:
    logging.info("Dry run - skipping actual 'docker build' and 'docker push'.")
    image_tag = "dry_run_tag"
  else:
    image_id = d.build_image(**docker_args)
    image_tag = d.push_uuid_tag(project_id, image_id)

  return image_tag


def execute_dry_run(specs: List[JobSpec]) -> None:
  log_specs(specs)

  logging.info('')
  logging.info(
      t.yellow(f"To build your image and submit these jobs, \
run your command again without {DRY_RUN_FLAG}."))
  logging.info('')
  return None


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
                  script_args: Optional[List[str]] = None,
                  request_retries: Optional[int] = None) -> None:
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
  - request_retries: the number of times to retry each request if it fails for
    a timeout or a rate limiting request.

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

  if request_retries is None:
    request_retries = 10

  image_tag = _generate_image_tag(project_id, docker_args, dry_run=dry_run)

  experiments = expand_experiment_config(experiment_config)
  specs = build_job_specs(job_name=job_name,
                          image_tag=image_tag,
                          region=region,
                          machine_type=machine_type,
                          script_args=script_args,
                          experiments=experiments,
                          user_labels=labels,
                          gpu_spec=gpu_spec)

  if dry_run:
    return execute_dry_run(specs)

  requests = create_requests(specs, project_id)
  execute_requests(requests, len(experiments), num_retries=request_retries)
  logging.info("")
  logging.info(
      t.green(
          f"Visit {job_url(project_id, '')} to see the status of all jobs."))
  logging.info("")
