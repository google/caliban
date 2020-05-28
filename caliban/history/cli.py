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

'''caliban history cli support'''

import os
import logging
import pprint as pp
from typing import Optional, Iterable, Dict, Any

from sqlalchemy import or_, and_

from caliban.util import current_user, Package
from caliban.history.utils import (get_sql_engine, session_scope,
                                   update_job_status, get_gke_job_name)
from caliban.history.types import (ContainerSpec, ExperimentGroup, Experiment,
                                   JobSpec, Job, Platform, JobStatus, Platform)
from caliban.gke.utils import user_verify, credentials

from caliban.docker import build_image, push_uuid_tag, execute_jobs

# default max jobs to return for status command
_DEFAULT_STATUS_MAX_JOBS = 8


# ----------------------------------------------------------------------------
def _job_str(j: Job) -> str:
  '''returns a job string for cli commands'''
  s = f'{j.id:<8d} {update_job_status(j):9s} {j.spec.platform.name:>8s} '
  s += f'{str(j.created):.19s} container: {j.container} '
  if j.spec.platform == Platform.CAIP:
    s += f'name: {j.details["jobId"]}'
  elif j.spec.platform == Platform.GKE:
    s += f'name: {get_gke_job_name(j)}'
  return s


def _experiment_command_str(e: Experiment) -> str:
  '''returns experiment string for cli commands'''
  return (f'{Package(*e.container_spec.spec["package"]).script_path} '
          f'{" ".join(e.args)} '
          f'{" ".join(["--" + k + " " + str(v) for k,v in e.kwargs.items()])}')


def _container_spec_str(cs: ContainerSpec) -> str:
  '''returns container spec string for cli commands'''
  build_path = cs.spec.get('build_path')
  if build_path is not None:
    build_path = build_path.replace(os.path.expanduser('~'), '~')
  return (f'{cs.id}: job_mode: {cs.spec.get("job_mode", "GPU")}, '
          f'build url: {build_path}, '
          f'extra dirs: {cs.spec.get("extra_dirs")}')


# ----------------------------------------------------------------------------
def _display_jobs_hierarchy(jobs: Iterable[Job]) -> None:
  '''displays jobs in a hierarchical format using experiment groups, container
  specs, and experiments'''

  xgroups = sorted(set([j.experiment.xgroup for j in jobs]), key=lambda x: x.id)

  for xg in xgroups:
    logging.info(f'xgroup {xg.name}:')
    xg_jobs = list(filter(lambda j: j.experiment.xgroup == xg, jobs))
    container_specs = sorted(
        set([x.experiment.container_spec for x in xg_jobs]),
        key=lambda x: x.id,
    )

    for cs in container_specs:
      logging.info(f'docker config {_container_spec_str(cs)}')
      cs_jobs = list(
          filter(lambda j: (j.experiment.container_spec == cs), xg_jobs))
      experiments = sorted(
          set([x.experiment for x in cs_jobs]),
          key=lambda x: x.id,
      )

      for e in experiments:
        logging.info(f'  experiment id {e.id}: {_experiment_command_str(e)}')
        exp_jobs = filter(lambda x: x.experiment == e, cs_jobs)

        for j in exp_jobs:
          logging.info(f'    job {_job_str(j)}')

    logging.info('')


# ----------------------------------------------------------------------------
def _display_recent_jobs(
    user: str,
    max_jobs: Optional[int] = None,
) -> None:
  '''display recent jobs for given user'''

  # max_jobs here controls the maximum number of jobs to retrieve and display
  # across all experiment groups for the given user
  if max_jobs is None:
    max_jobs = _DEFAULT_STATUS_MAX_JOBS

  max_jobs = max(0, max_jobs)

  with session_scope(get_sql_engine()) as session:
    recent_jobs = session.query(Job).filter(Job.user == user).order_by(
        Job.created.desc())

    if max_jobs > 0:
      recent_jobs = recent_jobs.limit(max_jobs)

    recent_jobs = recent_jobs.all()
    recent_jobs.reverse()

    if len(recent_jobs) == 0:
      logging.info(f'No recent jobs found for user {user}.')
      return

    if max_jobs > 0:
      logging.info(f'most recent {max_jobs} jobs for user {user}:\n')
    else:
      logging.info(f'all jobs for user {user}:\n')

    _display_jobs_hierarchy(jobs=recent_jobs)

    return


# ----------------------------------------------------------------------------
def _display_xgroup(
    xgroup: str,
    user: str,
    max_jobs: Optional[int] = None,
) -> None:
  '''display information for given experiment group and user'''

  # max_jobs here controls how many jobs to display for each experiment in
  # the specified experiment group, by default we only display the most recent
  # job for each experiment
  if max_jobs is None:
    max_jobs = 1

  max_jobs = max(0, max_jobs)

  with session_scope(get_sql_engine()) as session:
    xg = session.query(ExperimentGroup).filter(
        ExperimentGroup.name == xgroup).filter(
            ExperimentGroup.user == user).first()

    if xg is None:
      logging.info(f'xgroup {xgroup} not found')
      return

    container_specs = sorted(
        set([e.container_spec for e in xg.experiments]),
        key=lambda x: x.id,
    )

    logging.info(f'xgroup {xg.name}:')
    for cs in container_specs:
      logging.info(f'docker config {_container_spec_str(cs)}')
      for e in xg.experiments:
        if e.container_spec.id != cs.id:
          continue
        logging.info(f'  experiment id {e.id}: {_experiment_command_str(e)}')
        if len(e.jobs) == 0:
          logging.info(f'    no jobs found')
        else:
          for j in e.jobs[-max_jobs:]:
            logging.info(f'    job {_job_str(j)}')


# ----------------------------------------------------------------------------
def get_status(args: Dict[str, Any]) -> None:
  '''executes the `caliban status` cli command
  '''

  xgroup = args.get('xgroup')
  max_jobs = args.get('max_jobs')
  user = args.get('user') or current_user()

  if xgroup is None:
    _display_recent_jobs(user, max_jobs)
  else:
    _display_xgroup(xgroup, user, max_jobs)
