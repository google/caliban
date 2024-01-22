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

import logging
import os
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from caliban.docker.build import build_image
from caliban.docker.push import push_uuid_tag
from caliban.history.submit import submit_job_specs
from caliban.history.types import (ContainerSpec, Experiment, ExperimentGroup,
                                   Job, JobStatus, Platform)
from caliban.history.util import (get_gke_job_name, get_sql_engine,
                                  replace_job_spec_image, session_scope,
                                  stop_job, update_job_status)
from caliban.platform.gke.util import credentials, user_verify
from caliban.util import Package, current_user

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


# ----------------------------------------------------------------------------
def stop(args: Dict[str, Any]) -> None:
  '''executes the `caliban stop` cli command'''

  user = current_user()
  xgroup = args.get('xgroup')
  dry_run = args.get('dry_run', False)

  # querying and stopping jobs can take a long time, especially on CAIP,
  # so we check with the user up-front rather than waiting for our full
  # query to return
  if (not dry_run and not user_verify(
      f'Warning: this will potentially stop many jobs, do you wish to continue?',
      False)):
    return

  with session_scope(get_sql_engine()) as session:
    running_jobs = session.query(Job).join(Experiment).join(
        ExperimentGroup).filter(
            or_(Job.status == JobStatus.SUBMITTED,
                Job.status == JobStatus.RUNNING))

    if xgroup is not None:
      running_jobs = running_jobs.filter(ExperimentGroup.name == xgroup)

    running_jobs = running_jobs.all()

    if len(running_jobs) == 0:
      logging.info(f'no running jobs found')
      return

    logging.info(f'the following jobs will be stopped:')
    for j in running_jobs:
      logging.info(_experiment_command_str(j.experiment))
      logging.info(f'    job {_job_str(j)}')

    if dry_run:
      logging.info(f'to actually stop these jobs, re-run the command without '
                   f'the --dry_run flag')
      return

    for j in running_jobs:
      logging.info(f'stopping job: {_job_str(j)}')
      stop_job(j)

    logging.info(
        f'requested job cancellation, please be patient as it may take '
        f'a short while for this status change to be reflected in the '
        f'gcp dashboard or from the `caliban status` command.')


# ----------------------------------------------------------------------------
def _rebuild_containers(
    jobs: Iterable[Job],
    project_id: Optional[str] = None,
) -> Dict[Job, str]:
  '''this utility rebuilds all the needed containers for the given jobs

  This also tags and uploads the containers to the appropriate project
  cloud registry if necessary.

  Args:
  jobs: iterable of jobs for which to rebuild containers
  project_id: project id

  Returns:
  dictionary mapping jobs to new image tags
  '''

  image_id_map = {}

  container_specs = set([j.experiment.container_spec for j in jobs])
  for c in container_specs:
    image_id = build_image(**c.spec)
    cs_jobs = filter(lambda x: x.experiment.container_spec == c, jobs)

    image_tag = None
    for j in cs_jobs:
      if j.spec.platform in [Platform.CAIP, Platform.GKE]:
        assert project_id != None, 'project id must be specified for CAIP, GKE jobs'

        if image_tag is None:
          image_tag = push_uuid_tag(project_id, image_id)
        image_id_map[j] = image_tag
      else:
        image_id_map[j] = image_id

  return image_id_map


# ----------------------------------------------------------------------------
def _get_resubmit_project_id(
    jobs: Iterable[Job],
    project_id: Optional[str],
    creds_file: Optional[str],
) -> Optional[str]:
  '''checks CAIP or GKE jobs in provided list, and if any exist, then ensures
  that a valid project_id can be determined, either using defaults or an
  explicitly-provided value

  Args:
  jobs: list of jobs to inspect
  project_id: explicitly-provided project id, or if None attempt to determine
  creds_file: optional credentials file to use for determining project id

  Returns:
  project_id
  '''

  if project_id is not None:
    return project_id

  cloud_jobs = filter(
      lambda j: j.spec.platform in [Platform.CAIP, Platform.GKE],
      jobs,
  )

  if len(list(cloud_jobs)) == 0:
    return project_id

  return credentials(creds_file).project_id


# ----------------------------------------------------------------------------
def _get_resubmit_jobs(
    session: Session,
    xgroup: str,
    user: str,
    all_jobs: bool,
) -> Optional[List[Job]]:
  '''gets jobs for resubmission'''

  xg = session.query(ExperimentGroup).filter(
      ExperimentGroup.user == user,
      ExperimentGroup.name == xgroup,
  ).first()

  if xg is None:
    logging.error(f'could not find experiment group {xgroup}')
    return None

  # we get the most recent job for each experiment
  # note that these are already ordered by creation time
  jobs = []
  for e in xg.experiments:
    if len(e.jobs) > 0:
      jobs.append(e.jobs[-1])

  if len(jobs) == 0:
    logging.error(f'no jobs found in experiment group')
    return None

  # we are only resubmitting stopped or failed jobs
  if not all_jobs:
    jobs = list(
        filter(
            lambda x: update_job_status(x) in
            [JobStatus.FAILED, JobStatus.STOPPED], jobs))

  if len(jobs) == 0:
    logging.error(f'no jobs found in FAILED or STOPPED state')
    return None

  return jobs


# ----------------------------------------------------------------------------
def resubmit(args: Dict[str, Any]) -> None:
  '''executes the `caliban resubmit` command'''

  user = current_user()
  xgroup = args.get('xgroup')
  dry_run = args.get('dry_run', False)
  all_jobs = args.get('all_jobs', False)
  project_id = args.get('project_id')
  creds_file = args.get('cloud_key')
  rebuild = True

  if xgroup is None:
    logging.error(f'you must specify an experiment group for this command')
    return

  with session_scope(get_sql_engine()) as session:
    jobs = _get_resubmit_jobs(
        session=session,
        xgroup=xgroup,
        user=user,
        all_jobs=all_jobs,
    )

    if jobs is None:
      return

    # if we have CAIP or GKE jobs, then we need to have a project_id
    project_id = _get_resubmit_project_id(jobs, project_id, creds_file)

    # show what would be done
    logging.info(f'the following jobs would be resubmitted:')
    for j in jobs:
      logging.info(_experiment_command_str(j.experiment))
      logging.info(f'  job {_job_str(j)}')

    if dry_run:
      logging.info(f'to actually resubmit these jobs, run this command again '
                   f'without the --dry_run flag')
      return

    # make sure
    if not user_verify(f'do you wish to resubmit these {len(jobs)} jobs?',
                       False):
      return

    # rebuild all containers first
    if rebuild:
      logging.info(f'rebuilding containers...')
      image_id_map = _rebuild_containers(jobs, project_id=project_id)
    else:
      image_id_map = {j: j.container for j in jobs}

    # create new job specs
    job_specs = [
        replace_job_spec_image(spec=j.spec, image_id=image_id_map[j])
        for j in jobs
    ]

    # submit jobs, grouped by platform
    for platform in [Platform.CAIP, Platform.GKE, Platform.LOCAL]:
      pspecs = list(filter(lambda x: x.platform == platform, job_specs))
      try:
        submit_job_specs(
            specs=pspecs,
            platform=platform,
            project_id=project_id,
            credentials_path=creds_file,
        )
      except Exception as e:
        session.commit()  # avoid rollback
        logging.error(f'there was an error submitting some jobs')

    return
