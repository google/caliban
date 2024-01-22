#!/usr/bin/python
#
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""cloud utilities."""

from __future__ import absolute_import, division, print_function

import datetime
import traceback
from copy import deepcopy
from pprint import pformat
from typing import Any, Dict, Iterable, List, Optional, Tuple

import tqdm
from absl import logging
from blessings import Terminal
from googleapiclient import discovery
from googleapiclient.errors import HttpError

import caliban.config as conf
import caliban.config.experiment as ce
import caliban.docker.build as db
import caliban.docker.push as dp
import caliban.history.types as ht
import caliban.platform.cloud.types as ct
import caliban.platform.cloud.util as cu
import caliban.util as u
import caliban.util.auth as ua
import caliban.util.metrics as um
import caliban.util.tqdm as ut
from caliban.history.util import (create_experiments, generate_container_spec,
                                  get_mem_engine, get_sql_engine, session_scope)

t = Terminal()


def get_accelerator_config(gpu_spec: Optional[ct.GPUSpec]) -> Dict[str, Any]:
  """Returns the accelerator config for the supplied GPUSpec if present; else,
  returns the default accelerator config.

  """
  config = conf.DEFAULT_ACCELERATOR_CONFIG

  if gpu_spec is not None:
    config = gpu_spec.accelerator_config()

  return config


def job_url(project_id: str, job_id: str) -> str:
  """Returns a URL that will load the default page for the newly launched AI
  Platform job.

  """
  prefix = "https://console.cloud.google.com/ai-platform/jobs"
  return "{}/{}?projectId={}".format(prefix, job_id, project_id)


def _stream_cmd(job_id: str) -> str:
  """Returns a CLI command that, if executed, will stream the logs for the job
  with the supplied ID to the terminal.

  """
  items = ["gcloud", "ai-platform", "jobs", "stream-logs", job_id]
  return " ".join(items)


def logging_callback(spec: Dict[str, Any], project_id: str):
  """Returns a callback of the format required by the GCloud REST api's job
  creation endpoint. The returned function accepts:

  - a request_id
  - a Job object, in case the request succeeds:
    https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs#Job
  - an exception if the request fails.

  """
  job_id = spec["jobId"]

  def callback(_, exception):
    logging.debug("spec for job {}: {}".format(job_id, spec))
    prefix = "Request for job '{}'".format(spec['jobId'])

    if exception is None:
      url = job_url(project_id, job_id)
      stream_command = _stream_cmd(job_id)

      logging.info(t.green("{} succeeded!".format(prefix)))
      logging.info(t.green("Job URL: {}".format(url)))
      logging.info(
          t.green("Streaming log CLI command: $ {}".format(stream_command)))
    else:
      logging.error(t.red("{} failed! Details:".format(prefix)))
      logging.error(t.red(exception._get_reason()))

  return callback


def job_callback(spec: ht.JobSpec, project_id: str, body: Dict[str, Any]):
  '''callback for job submission

  This returns a function that accepts a response object from a caip
  job submission request and an optional exception argument, and logs
  some status output and then creates a Job instance that will be
  persisted.

  Args:
  JobSpec: job spec describing job to be submitted
  project_id: project for caip submission
  body: dictionary forming body of job submission request

  Returns:
  callable taking response and optional exception
  '''
  logging_cb = logging_callback(spec=body, project_id=project_id)

  def callback(resp, exception):
    logging_cb(resp, exception)
    if exception is not None:
      status = ht.JobStatus.FAILED
    else:
      status = ht.JobStatus.SUBMITTED
    # create and persist Job
    _ = ht.Job(
        spec=spec,
        container=spec.spec['trainingInput']['masterConfig']['imageUri'],
        details={
            'jobId': body['jobId'],
            'project_id': project_id
        },
        status=status,
    )

  return callback


def log_spec(spec: ht.JobSpec, i: int) -> ht.JobSpec:
  """Returns the input spec after triggering logging side-effects.

  """
  job_id = spec.spec['jobId']
  training_input = spec.spec['trainingInput']
  machine_type = training_input['masterType']
  region = training_input['region']
  masterConf = training_input['masterConfig']
  accelerator = masterConf['acceleratorConfig']
  image_uri = masterConf['imageUri']
  workerConf = training_input.get('workerConfig')
  args = training_input['args']

  def prefixed(s: str, level=logging.INFO):
    logging.log(level, "Job {} - {}".format(i, s))

  prefixed("Spec: {}".format(spec), logging.DEBUG)
  prefixed("jobId: {}, image: {}".format(t.yellow(job_id), image_uri))
  prefixed("Accelerator: {}, machine: '{}', region: '{}'".format(
      accelerator, machine_type, region))
  if workerConf is not None:
    prefixed("Worker config: {}, machine: '{}'".format(
        workerConf, training_input['workerType']))

  prefixed("Experiment arguments: {}".format(t.yellow(str(args))))
  prefixed(f'labels: {spec.spec["labels"]}\n')
  return spec


def logged_specs(specs: Iterable[ht.JobSpec]) -> Iterable[ht.JobSpec]:
  """Returns a generator that produces the same values as the supplied iterable;
  wrapping the iterable in `logged_specs` will trigger a logging side-effect
  for each JobSpec instance before it's produced.

  """
  for i, spec in enumerate(specs, 1):
    yield log_spec(spec, i)


def log_specs(specs: Iterable[ht.JobSpec]) -> List[ht.JobSpec]:
  """Equivalent to logged_specs, except all logging side effects are forced to
  occur immediately before return.

  Returns the realized list of JobSpec instances.

  """
  return list(logged_specs(specs))


def logged_batches(specs: Iterable[ht.JobSpec],
                   limit: int) -> Iterable[Iterable[ht.JobSpec]]:
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
  logging.info("Generating {} {} for {} {}.".format(total_chunks, plural_batch,
                                                    total_specs, plural_job))
  for i, chunk in enumerate(chunked_seq, 1):
    logging.info("Batch {} of {}:".format(i, total_chunks))
    yield logged_specs(chunk)


def log_batch_parameters(specs: Iterable[ht.JobSpec],
                         limit: int) -> List[List[ht.JobSpec]]:
  """Equivalent to logged_batches, except all logging side effects are forced to
  occur immediately before return.

  Returns the realized list of lists of JobSpec instances.

  """
  return [list(batch) for batch in logged_batches(specs, limit=limit)]


def ml_api(credentials_path: Optional[str] = None):
  """Returns an instance of the API object required to submit jobs to AI
  Platform.

  If you provide the path to a service account key JSON file, the function will
  use those credentials to authenticate with the API; otherwise, the default
  will be

  - the value of $GOOGLE_APPLICATION_CREDENTIALS
  - the application default credentials registered on your machine
  - the account you used to log in to gcloud.

  The actual details are a little byzantine.

  """
  credentials = ua.gcloud_credentials(credentials_path)
  return discovery.build('ml',
                         'v1',
                         cache_discovery=False,
                         credentials=credentials)


def create_requests(
    specs: List[ht.JobSpec],
    project_id: str,
    credentials_path: Optional[str] = None
) -> Iterable[Tuple[Any, ht.JobSpec, Any]]:
  """Returns an iterator of (HttpRequest, ht.JobSpec, Callback).

  HttpRequests look like:
  https://googleapis.github.io/google-api-python-client/docs/epy/googleapiclient.http.HttpRequest-class.html

  Iterating across the requests will trigger logging side-effects for its
  corresponding spec.

  Cloud API docs for the endpoint each request submits to:
  https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs/create

  Python specific docs:
  http://googleapis.github.io/google-api-python-client/docs/dyn/ml_v1.projects.jobs.html#create

  """
  parent = "projects/{}".format(project_id)

  # cache_discovery=False prevents an error bubbling up from a missing file
  # cache, which no user of this code is going to be using.
  ml = ml_api(credentials_path)

  jobs = ml.projects().jobs()

  for job_spec in logged_specs(specs):
    # replace the jobId field with a uid-appended id upon request creation
    spec = deepcopy(job_spec.spec)
    uid = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    index = spec['jobId'].split('_')[-1]
    job_name = '_'.join(spec['jobId'].split('_')[:-1])
    spec['jobId'] = f'{job_name}_{uid}_{index}'
    cb = job_callback(spec=job_spec, project_id=project_id, body=spec)
    yield jobs.create(body=spec, parent=parent), job_spec, cb


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


def execute_requests(
    requests: Iterable[Tuple[Any, ht.JobSpec, Any]],
    count: Optional[int] = None,
    num_retries: Optional[int] = None,
) -> None:
  """Execute all batches in the supplied generator of batch requests. Results
  aren't returned directly; the callbacks passed to each request when it was
  generated handle any response or exception.

  """
  with ut.tqdm_logging() as orig_stream:
    pbar = tqdm.tqdm(
        requests,
        file=orig_stream,
        total=count,
        unit="requests",
        desc="submitting",
        ascii=True,
    )
    for req, spec, cb in pbar:
      pbar.set_description(f'Submitting {spec.spec["jobId"]}')
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


def tpu_fields(tpu_spec: Optional[ct.TPUSpec]) -> Dict[str, str]:
  """Returns the fields necessary to append to a job request's trainingInput
  field to activate TPU mode.

  """
  if tpu_spec is None:
    return {}

  return {
      "workerCount": 1,
      "workerType": "cloud_tpu",
      "workerConfig": {
          "acceleratorConfig": tpu_spec.accelerator_config(),
          "tpuTfVersion": "1.14"
      }
  }


def _job_spec(
    job_name: str,
    idx: int,
    training_input: Dict[str, Any],
    labels: Dict[str, str],
    experiment: ht.Experiment,
) -> ht.JobSpec:
  """Returns the final object required by the Google AI Platform training job
  submission endpoint.

  """
  job_id = f'{job_name}_{idx}'
  job_args = training_input.get("args")
  return ht.JobSpec.get_or_create(
      experiment=experiment,
      spec={
          "jobId": job_id,
          "trainingInput": training_input,
          "labels": {
              **cu.sanitize_labels(labels),
              **cu.script_args_to_labels(job_args)
          }
      },
      platform=ht.Platform.CAIP,
  )


def _job_specs(
    job_name: str,
    training_input: Dict[str, Any],
    labels: Dict[str, str],
    experiments: Iterable[ht.Experiment],
    caliban_config: Optional[Dict[str, Any]] = None,
) -> Iterable[ht.JobSpec]:
  """Returns a generator that yields a JobSpec instance for every possible
  combination of parameters in the supplied experiment config.

  All other arguments parametrize every JobSpec that's generated; labels,
  arguments and job id change for each JobSpec.

  This is lower-level than build_job_specs below.

  """
  caliban_config = caliban_config or {}

  for idx, m in enumerate(experiments, 1):

    launcher_args = um.mlflow_args(
        caliban_config=caliban_config,
        experiment_name=m.xgroup.name,
        index=idx,
        tags={
            um.PLATFORM_TAG: ht.Platform.CAIP.value,
            **labels,
        },
    )

    cmd_args = ce.experiment_to_args(m.kwargs, m.args)

    # cmd args *must* be last in order for the launcher to pass them through
    args = launcher_args + cmd_args

    yield _job_spec(job_name=job_name,
                    idx=idx,
                    training_input={
                        **training_input, "args": args
                    },
                    labels=labels,
                    experiment=m)


def build_job_specs(
    job_name: str,
    image_tag: str,
    region: ct.Region,
    machine_type: ct.MachineType,
    experiments: Iterable[ht.Experiment],
    user_labels: Dict[str, str],
    gpu_spec: Optional[ct.GPUSpec],
    tpu_spec: Optional[ct.TPUSpec],
    caliban_config: Optional[Dict[str, Any]] = None,
) -> Iterable[ht.JobSpec]:
  """Returns a generator that yields a JobSpec instance for every possible
  combination of parameters in the supplied experiment config.

  All other arguments parametrize every JobSpec that's generated. Various base
  labels such as 'gpu_enabled', etc are filled in for each job.

  Each job in the batch will have a unique jobId.

  """
  logging.info(f'Building jobs for name: {job_name}')

  caliban_config = caliban_config or {}
  accelerator_conf = get_accelerator_config(gpu_spec)
  training_input = base_training_input(image_tag, region, machine_type,
                                       accelerator_conf)

  # Add in TPU, potentially.
  training_input.update(tpu_fields(tpu_spec))

  gpu_enabled = gpu_spec is not None
  tpu_enabled = tpu_spec is not None
  base_labels = {
      "gpu_enabled": str(gpu_enabled).lower(),
      "tpu_enabled": str(tpu_enabled).lower(),
      "job_name": job_name,
      "docker_image": image_tag,
      **user_labels
  }

  return _job_specs(job_name,
                    training_input=training_input,
                    labels=base_labels,
                    experiments=experiments,
                    caliban_config=caliban_config)


def generate_image_tag(project_id, docker_args, dry_run: bool = False):
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
    image_id = db.build_image(**docker_args)
    image_tag = dp.push_uuid_tag(project_id, image_id)

  return image_tag


def execute_dry_run(specs: List[ht.JobSpec]) -> None:
  log_specs(specs)

  logging.info('')
  logging.info(
      t.yellow("To build your image and submit these jobs, \
run your command again without {}.".format(conf.DRY_RUN_FLAG)))
  logging.info('')
  return None


def submit_job_specs(
    specs: Iterable[ht.JobSpec],
    project_id: str,
    credentials_path: Optional[str] = None,
    num_specs: Optional[int] = None,
    request_retries: Optional[int] = 10,
) -> None:
  '''submit job specs to CAIP

  Args:
  specs: iterable of job specs
  project_id: project id for submission
  credentials_path: path to credentials
  num_specs: used for progress bar if supplied
  request_retries: number of times to retry submission request
  '''

  requests = create_requests(
      specs,
      project_id=project_id,
      credentials_path=credentials_path,
  )

  execute_requests(requests, num_specs, num_retries=request_retries)


def submit_ml_job(
    job_mode: conf.JobMode,
    docker_args: Dict[str, Any],
    region: ct.Region,
    project_id: str,
    credentials_path: Optional[str] = None,
    dry_run: bool = False,
    job_name: Optional[str] = None,
    machine_type: Optional[ct.MachineType] = None,
    gpu_spec: Optional[ct.GPUSpec] = None,
    tpu_spec: Optional[ct.TPUSpec] = None,
    image_tag: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None,
    experiment_config: Optional[ce.ExpConf] = None,
    script_args: Optional[List[str]] = None,
    request_retries: Optional[int] = None,
    xgroup: Optional[str] = None,
) -> None:
  """Top level function in the module. This function:

  - builds an image using the supplied docker_args, in either CPU or GPU mode
  - pushes that image to the Cloud Container Repository of the supplied
    project_id
  - generates a sequence of 'JobSpec' instances, one for every combination in
    the supplied experiment_config, and
  - batch-submits all jobs to AI Platform

  Keyword args:

  - job_mode: caliban.config.JobMode.
  - docker_args: these arguments are passed through to
    caliban.docker.build.build_image.
  - region: the region to use for AI Platform job submission. Different regions
    support different GPUs.
  - project_id: GCloud project ID for container storage and job submission.
  - credentials_path: explicit path to a service account JSON file, if it exists.
  - dry_run: if True, no actual jobs will be submitted and docker won't
    actually build; logging side effects will show the user what will happen
    without dry_run=True.
  - job_name: optional custom name. This is applied as a label to every job,
    and used as a prefix for all jobIds submitted to Cloud.
  - machine_type: the machine type to allocate for each job. Must be one
    supported by Cloud.
  - gpu_spec: if None and job_mode is GPU, defaults to a standard single GPU.
    Else, configures the count and type of GPUs to attach to the machine that
    runs each job.
  - tpu_spec: if None, defaults to no TPU attached. Else, configures the count
    and type of TPUs to attach to the machine that runs each job.
  - image_tag: optional explicit tag of a Container-Registry-available Docker
    container. If supplied, submit_ml_job will skip the docker build and push
    phases and use this image_tag directly.
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
  - xgroup: experiment group for this submission, if None a new group will
    be created
  """
  if script_args is None:
    script_args = []

  if job_name is None:
    job_name = "caliban_{}".format(u.current_user())

  if job_mode == conf.JobMode.GPU and gpu_spec is None:
    gpu_spec = ct.GPUSpec(ct.GPU.P100, 1)

  if machine_type is None:
    machine_type = conf.DEFAULT_MACHINE_TYPE[job_mode]

  if experiment_config is None:
    experiment_config = {}

  if labels is None:
    labels = {}

  if request_retries is None:
    request_retries = 10

  caliban_config = docker_args.get('caliban_config', {})

  engine = get_mem_engine() if dry_run else get_sql_engine()

  with session_scope(engine) as session:
    container_spec = generate_container_spec(session, docker_args, image_tag)

    if image_tag is None:
      image_tag = generate_image_tag(project_id, docker_args, dry_run=dry_run)

    experiments = create_experiments(
        session=session,
        container_spec=container_spec,
        script_args=script_args,
        experiment_config=experiment_config,
        xgroup=xgroup,
    )

    specs = build_job_specs(
        job_name=job_name,
        image_tag=image_tag,
        region=region,
        machine_type=machine_type,
        experiments=experiments,
        user_labels=labels,
        gpu_spec=gpu_spec,
        tpu_spec=tpu_spec,
        caliban_config=caliban_config,
    )

    if dry_run:
      return execute_dry_run(specs)

    try:
      submit_job_specs(
          specs=specs,
          project_id=project_id,
          credentials_path=credentials_path,
          num_specs=len(experiments),
          request_retries=request_retries,
      )
    except Exception as e:
      logging.error(f'exception: {e}')
      logging.error(f'{traceback.format_exc()}')
      session.commit()  # commit here, otherwise will be rolled back

    logging.info("")
    logging.info(
        t.green("Visit {} to see the status of all jobs.".format(
            job_url(project_id, ''))))
    logging.info("")
