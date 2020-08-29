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
"""Functions required to interact with Docker to build and run images, shells
and notebooks in a Docker environment.

"""

from __future__ import absolute_import, division, print_function

from datetime import datetime
import json
import os
import subprocess
import sys
import traceback
from typing import Any, Dict, Iterable, List, Optional

import tqdm
from absl import logging
from blessings import Terminal
from tqdm.utils import _screen_shape_wrapper

import caliban.config as c
import caliban.config.experiment as ce
import caliban.docker.build as b
import caliban.util as u
import caliban.util.fs as ufs
import caliban.util.metrics as um
import caliban.util.tqdm as ut
from caliban.history.types import Experiment, Job, JobSpec, JobStatus, Platform
from caliban.history.util import (create_experiments, generate_container_spec,
                                  get_mem_engine, get_sql_engine, session_scope)

t = Terminal()


def _run_cmd(job_mode: c.JobMode,
             run_args: Optional[List[str]] = None) -> List[str]:
  """Returns the sequence of commands for the subprocess run functions required
  to execute `docker run`. in CPU or GPU mode, depending on the value of
  job_mode.

  Keyword args:
  - run_args: list of args to pass to docker run.

  """
  if run_args is None:
    run_args = []

  runtime = ["--runtime", "nvidia"] if c.gpu(job_mode) else []
  return ["docker", "run"] + runtime + ["--ipc", "host"] + run_args


def log_job_spec_instance(job_spec: JobSpec, i: int) -> JobSpec:
  """Prints logging as a side effect for the supplied sequence of job specs
  generated from an experiment definition; returns the input job spec.

  """
  args = ce.experiment_to_args(job_spec.experiment.kwargs,
                               job_spec.experiment.args)
  logging.info("")
  logging.info("Job {} - Experiment args: {}".format(i, t.yellow(str(args))))
  return job_spec


def logged_job_specs(job_specs: Iterable[JobSpec]) -> Iterable[JobSpec]:
  """Generates an iterable of job specs that should be passed to `docker run` to
  execute the experiments defined by the supplied iterable.

  """
  for i, s in enumerate(job_specs, 1):
    yield log_job_spec_instance(s, i)


def execute_dry_run(job_specs: Iterable[JobSpec]) -> None:
  """Expands the supplied sequence of experiments into sequences of args and logs
  the jobs that WOULD have been executed, had the dry run flag not been
  applied.

  """
  list(logged_job_specs(job_specs))

  logging.info('')
  logging.info(
      t.yellow("To build your image and execute these jobs, \
run your command again without {}.".format(c.DRY_RUN_FLAG)))
  logging.info('')
  return None


def local_callback(idx: int, job: Job) -> None:
  """Provides logging feedback for jobs run locally. If the return code is 0,
  logs success; else, logs the failure as an error and logs the script args
  that provided the failure.

  """
  if job.status == JobStatus.SUCCEEDED:
    logging.info(t.green(f'Job {idx} succeeded!'))
  else:
    logging.error(
        t.red(f'Job {idx} failed with return code {job.details["ret_code"]}.'))
    args = ce.experiment_to_args(job.spec.experiment.kwargs,
                                 job.spec.experiment.args)
    logging.error(t.red(f'Failing args for job {idx}: {args}'))


def window_size_env_cmds():
  """Returns a sequence of `docker run` arguments that will internally configure
  the terminal columns and lines, so that progress bars and other terminal
  interactions will work properly.

  These aren't required for interactive Docker commands like those triggered by
  `caliban shell`.

  """
  ret = []
  cols, lines = _screen_shape_wrapper()(0)
  if cols:
    ret += ["-e", f"COLUMNS={cols}"]
  if lines:
    ret += ["-e", f"LINES={lines}"]
  return ret


# ----------------------------------------------------------------------------
def _create_job_spec_dict(
    experiment: Experiment,
    job_mode: c.JobMode,
    image_id: str,
    index: int,
    caliban_config: Dict[str, Any],
    run_args: Optional[List[str]] = None,
) -> Dict[str, Any]:
  '''creates a job spec dictionary for a local job'''

  # Without the unbuffered environment variable, stderr and stdout won't be
  # emitted in the proper order from inside the container.
  terminal_cmds = ["-e", "PYTHONUNBUFFERED=1"] + window_size_env_cmds()

  base_cmd = _run_cmd(job_mode, run_args) + terminal_cmds + [image_id]

  launcher_args = um.mlflow_args(
      caliban_config=caliban_config,
      experiment_name=experiment.xgroup.name,
      index=index,
      tags={
          um.GPU_ENABLED_TAG: str(job_mode == c.JobMode.GPU).lower(),
          um.TPU_ENABLED_TAG: 'false',
          um.DOCKER_IMAGE_TAG: image_id,
          um.PLATFORM_TAG: Platform.LOCAL.value,
      },
  )

  cmd_args = ce.experiment_to_args(experiment.kwargs, experiment.args)

  # cmd args *must* be last in order for the launcher to pass them through
  command = base_cmd + launcher_args + cmd_args

  return {'command': command, 'container': image_id}


# ----------------------------------------------------------------------------
def execute_jobs(
    job_specs: Iterable[JobSpec],
    dry_run: bool = False,
    caliban_config: Optional[Dict[str, Any]] = None,
):
  '''executes a sequence of jobs based on job specs

  Arg:
  job_specs: specifications for jobs to be executed
  dry_run: if True, only print what would be done
  caliban_config: caliban configuration data
  '''
  caliban_config = caliban_config or {}

  with ut.tqdm_logging() as orig_stream:
    pbar = tqdm.tqdm(logged_job_specs(job_specs),
                     file=orig_stream,
                     total=len(job_specs),
                     ascii=True,
                     unit="experiment",
                     desc="Executing")
    for idx, job_spec in enumerate(pbar, 1):
      command = job_spec.spec['command']
      logging.info(f'Running command: {" ".join(command)}')
      if not dry_run:
        _, ret_code = ufs.capture_stdout(command, "", ut.TqdmFile(sys.stderr))
      else:
        ret_code = 0
      j = Job(spec=job_spec,
              container=job_spec.spec['container'],
              details={'ret_code': ret_code},
              status=JobStatus.SUCCEEDED if ret_code == 0 else JobStatus.FAILED)
      local_callback(idx=idx, job=j)

  if dry_run:
    logging.info(
        t.yellow(f'\nTo build your image and execute these jobs, '
                 f'run your command again without {c.DRY_RUN_FLAG}\n'))

  return None


def run_experiments(job_mode: c.JobMode,
                    run_args: Optional[List[str]] = None,
                    script_args: Optional[List[str]] = None,
                    image_id: Optional[str] = None,
                    dry_run: bool = False,
                    experiment_config: Optional[ce.ExpConf] = None,
                    xgroup: Optional[str] = None,
                    **build_image_kwargs) -> None:
  """Builds an image using the supplied **build_image_kwargs and calls `docker
  run` on the resulting image using sensible defaults.

  Keyword args:

  - job_mode: c.JobMode.

  - run_args: extra arguments to supply to `docker run` after our defaults.
  - script_args: extra arguments to supply to the entrypoint. (You can
  - override the default container entrypoint by supplying a new one inside
    run_args.)
  - image_id: ID of the image to run. Supplying this will skip an image build.
  - experiment_config: dict of string to list, boolean, string or int. Any
    lists will trigger a cartesian product out with the rest of the config. A
    job will be executed for every combination of parameters in the experiment
    config.
  - dry_run: if True, no actual jobs will be executed and docker won't
    actually build; logging side effects will show the user what will happen
    without dry_run=True.

  any extra kwargs supplied are passed through to build_image.
  """
  if run_args is None:
    run_args = []

  if script_args is None:
    script_args = []

  if experiment_config is None:
    experiment_config = {}

  docker_args = {k: v for k, v in build_image_kwargs.items()}
  docker_args['job_mode'] = job_mode
  caliban_config = docker_args.get('caliban_config', {})

  engine = get_mem_engine() if dry_run else get_sql_engine()

  with session_scope(engine) as session:
    container_spec = generate_container_spec(session, docker_args, image_id)

    if image_id is None:
      if dry_run:
        logging.info("Dry run - skipping actual 'docker build'.")
        image_id = 'dry_run_tag'
      else:
        image_id = b.build_image(**docker_args)

    experiments = create_experiments(
        session=session,
        container_spec=container_spec,
        script_args=script_args,
        experiment_config=experiment_config,
        xgroup=xgroup,
    )

    job_specs = [
        JobSpec.get_or_create(
            experiment=x,
            spec=_create_job_spec_dict(
                experiment=x,
                job_mode=job_mode,
                run_args=run_args,
                image_id=image_id,
                index=i,
                caliban_config=caliban_config,
            ),
            platform=Platform.LOCAL,
        ) for i, x in enumerate(experiments)
    ]

    try:
      execute_jobs(job_specs=job_specs,
                   dry_run=dry_run,
                   caliban_config=caliban_config)
    except Exception as e:
      logging.error(f'exception: {e}')
      logging.error(f'{traceback.format_exc()}')
      session.commit()  # commit here, otherwise will be rolled back


def run(job_mode: c.JobMode,
        run_args: Optional[List[str]] = None,
        script_args: Optional[List[str]] = None,
        image_id: Optional[str] = None,
        **build_image_kwargs) -> None:
  """Builds an image using the supplied **build_image_kwargs and calls `docker
  run` on the resulting image using sensible defaults.
  Keyword args:
  - job_mode: c.JobMode.
  - run_args: extra arguments to supply to `docker run` after our defaults.
  - script_args: extra arguments to supply to the entrypoint. (You can
  - override the default container entrypoint by supplying a new one inside
    run_args.)
  - image_id: ID of the image to run. Supplying this will skip an image build.
  any extra kwargs supplied are passed through to build_image.
  """
  if run_args is None:
    run_args = []

  if script_args is None:
    script_args = []

  if image_id is None:
    image_id = b.build_image(job_mode, **build_image_kwargs)

  base_cmd = _run_cmd(job_mode, run_args)

  command = base_cmd + [image_id] + script_args

  logging.info("Running command: {}".format(' '.join(command)))
  subprocess.call(command)
  return None
