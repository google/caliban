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

import os
import sys
from contextlib import contextmanager
from copy import deepcopy
from typing import Any, Dict, List, Optional

from absl import logging
from blessings import Terminal
from googleapiclient import discovery
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

import caliban.config.experiment as ce
import caliban.util.auth as ua
from caliban.history.types import (ContainerSpec, Experiment, ExperimentGroup,
                                   Job, JobSpec, JobStatus, Platform, init_db)
from caliban.platform.cloud.types import JobStatus as CloudStatus
from caliban.platform.gke.cluster import Cluster
from caliban.platform.gke.types import JobStatus as GkeStatus
from caliban.platform.gke.util import default_credentials

DB_URL_ENV = 'CALIBAN_DB_URL'
MEMORY_DB_URL = 'sqlite:///:memory:'
SQLITE_FILE_DB_URL = 'sqlite:///~/.caliban/caliban.db'

t = Terminal()


# ----------------------------------------------------------------------------
def _create_sqa_engine(
    url: str = SQLITE_FILE_DB_URL,
    echo: bool = False,
) -> Engine:
  '''creates a sqlalchemy Engine instance

  Args:
  url: url of database
  echo: if True, will echo all SQL commands to terminal

  Returns:
  sqlalchemy Engine instance
  '''

  # this is a local sqlite db
  if url.startswith('sqlite:///') and url != 'sqlite:///:memory:':
    path, db = os.path.split(url.replace('sqlite:///', ''))
    path = os.path.expanduser(path)
    os.makedirs(path, exist_ok=True)
    full_path = os.path.join(path, db)
    url = f'sqlite:///{full_path}'

  engine = create_engine(url, echo=echo)
  init_db(engine)
  return engine


# ----------------------------------------------------------------------------
def get_mem_engine(echo: bool = False) -> Engine:
  '''gets a sqlalchemy engine connection to an in-memory sqlite instance

  Args:
  echo: if True, will echo all SQL commands to terminal

  Returns:
  sqlalchemy Engine instance
  '''
  return _create_sqa_engine(url=MEMORY_DB_URL, echo=echo)


# ----------------------------------------------------------------------------
def get_sql_engine(
    url: Optional[str] = None,
    strict=False,
    echo: bool = False,
) -> Engine:
  '''gets a sqlalchemy Engine instance

  Args:
  url: url of database, if None, uses DB_URL_ENV environment variable or
       SQLITE_FILE_DB_URL as fallbacks, in that order
  strict: if True, won't attempt to fall back to local or memory engines.
  echo: if True, will echo all SQL commands to terminal

  Returns:
  sqlalchemy Engine instance
  '''
  if url is None:
    url = os.environ.get(DB_URL_ENV) or SQLITE_FILE_DB_URL

  try:
    return _create_sqa_engine(url=url, echo=echo)

  except (OperationalError, OSError) as e:
    logging.error("")
    logging.error(
        t.red(
            f"Caliban failed to connect to its experiment tracking database! Details:"
        ))
    logging.error("")
    logging.error(t.red(str(e)))
    logging.error(t.red(f"Caliban attempted to connect to '{url}'."))
    logging.error(t.red(f"Try setting a different URL using ${DB_URL_ENV}."))
    logging.error("")

    if strict:
      sys.exit(1)

    else:
      # For now, we allow two levels of fallback. The goal is to make sure that
      # the job can proceed, no matter what.
      #
      # If you specify a custom URL, Caliban will fall back to the local
      # default database location. If that fails, Caliban will attempt once
      # more using an in-memory instance of SQLite. The only reason that should
      # fail is if your system doesn't support SQLite at all.

      if url == SQLITE_FILE_DB_URL:
        logging.warning(
            t.yellow(f"Attempting to proceed with in-memory database."))

        # TODO when we add our strict flag, bail here and don't even allow
        # in-memory.
        logging.warning(
            t.yellow(
                f"WARNING! This means that your job's history won't be accessible "
                f"via any of the `caliban history` commands. Proceed at your future self's peril."
            ))
        return get_sql_engine(url=MEMORY_DB_URL, strict=True, echo=echo)

      logging.info(
          t.yellow(f"Falling back to local sqlite db: {SQLITE_FILE_DB_URL}"))
      return get_sql_engine(url=SQLITE_FILE_DB_URL, strict=False, echo=echo)


# ----------------------------------------------------------------------------
@contextmanager
def session_scope(engine: Engine) -> Session:
  '''returns a sqlalchemy session using the provided engine

  This contextmanager commits all pending session changes on scope exit,
  and on an exception rolls back pending changes. The returned session is
  closed on final scope exit.

  Args:
  engine: sqlalchemy engine

  Returns:
  Session
  '''
  session = sessionmaker(bind=engine)()
  try:
    yield session
    session.commit()
  except:
    session.rollback()
    raise
  finally:
    session.close()


def generate_container_spec(
    session: Session,
    docker_args: Dict[str, Any],
    image_tag: Optional[str] = None,
) -> ContainerSpec:
  '''generates a container spec

  Args:
  session: sqlalchemy session
  docker_args: args for building docker container
  image_tag: if not None, then an existing docker image is used

  Returns:
  ContainerSpec instance
  '''

  if image_tag is None:
    spec = docker_args
  else:
    spec = {'image_id': image_tag}

  return ContainerSpec.get_or_create(session=session, spec=spec)


def create_experiments(
    session: Session,
    container_spec: ContainerSpec,
    script_args: List[str],
    experiment_config: ce.ExpConf,
    xgroup: Optional[str] = None,
) -> List[Experiment]:
  '''create experiment instances

  Args:
  session: sqlalchemy session
  container_spec: container spec for the generated experiments
  script_args: these are extra arguments that will be passed to every job
    executed, in addition to the arguments created by expanding out the
    experiment config.
  experiment_config: dict of string to list, boolean, string or int. Any
    lists will trigger a cartesian product out with the rest of the config. A
    job will be submitted for every combination of parameters in the experiment
    config.
  xgroup: experiment group name for the generated experiments
  '''

  xg = ExperimentGroup.get_or_create(session=session, name=xgroup)
  session.add(xg)  # this ensures that any new objects get persisted

  return [
      Experiment.get_or_create(
          xgroup=xg,
          container_spec=container_spec,
          args=script_args,
          kwargs=kwargs,
      ) for kwargs in ce.expand_experiment_config(experiment_config)
  ]


# ----------------------------------------------------------------------------
def _get_caip_job_name(j: Job) -> str:
  '''gets job name for use with caip rest api'''
  job_id = j.details['jobId']
  project_id = j.details['project_id']
  return f'projects/{project_id}/jobs/{job_id}'


# ----------------------------------------------------------------------------
def _get_caip_job_api(credentials_path: Optional[str] = None) -> Any:
  credentials = ua.gcloud_credentials(credentials_path)
  return discovery.build('ml',
                         'v1',
                         cache_discovery=False,
                         credentials=credentials).projects().jobs()


# ----------------------------------------------------------------------------
def get_caip_job_status(j: Job) -> JobStatus:
  '''gets caip job status

    https://cloud.google.com/ai-platform/training/docs/reference/rest/v1/projects.jobs#State

    Returns:
    JobStatus
'''

  CAIP_TO_JOB_STATUS = {
      CloudStatus.STATE_UNSPECIFIED: JobStatus.UNKNOWN,
      CloudStatus.QUEUED: JobStatus.SUBMITTED,
      CloudStatus.PREPARING: JobStatus.SUBMITTED,
      CloudStatus.RUNNING: JobStatus.RUNNING,
      CloudStatus.SUCCEEDED: JobStatus.SUCCEEDED,
      CloudStatus.FAILED: JobStatus.FAILED,
      CloudStatus.CANCELLING: JobStatus.RUNNING,
      CloudStatus.CANCELLED: JobStatus.STOPPED
  }

  api = _get_caip_job_api()
  job_id = j.details['jobId']
  name = _get_caip_job_name(j)

  try:
    rsp = api.get(name=name).execute()
    caip_status = CloudStatus[rsp['state']]
  except Exception as e:
    logging.error(f'error getting job status for {job_id}')
    return JobStatus.UNKNOWN

  return CAIP_TO_JOB_STATUS.get(caip_status) or JobStatus.UNKNOWN


# ----------------------------------------------------------------------------
def get_gke_job_name(j: Job) -> str:
  '''gets gke job name from Job object'''
  return j.details['job']['metadata']['name']


# ----------------------------------------------------------------------------
def get_job_cluster(j: Job) -> Optional[Cluster]:
  '''gets the cluster name from a Job object'''
  if j.spec.platform != Platform.GKE:
    return None

  return Cluster.get(name=j.details['cluster_name'],
                     project_id=j.details['project_id'],
                     zone=j.details['cluster_zone'],
                     creds=default_credentials().credentials)


# ----------------------------------------------------------------------------
def get_gke_job_status(j: Job) -> JobStatus:
  '''get gke job status

    see:
    https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.11/#jobcondition-v1-batch

    Returns:
    JobStatus
  '''

  GKE_TO_JOB_STATUS = {
      GkeStatus.STATE_UNSPECIFIED: JobStatus.SUBMITTED,
      GkeStatus.PENDING: JobStatus.SUBMITTED,
      GkeStatus.RUNNING: JobStatus.RUNNING,
      GkeStatus.FAILED: JobStatus.FAILED,
      GkeStatus.SUCCEEDED: JobStatus.SUCCEEDED,
      GkeStatus.UNAVAILABLE: JobStatus.UNKNOWN
  }

  cluster_name = j.details['cluster_name']
  job_name = get_gke_job_name(j)

  cluster = get_job_cluster(j)
  if cluster is None:
    logging.error(f'unable to connect to cluster {cluster_name}, '
                  f'so unable to update run status')
    return JobStatus.UNKNOWN

  job_info = cluster.get_job(job_name)
  if job_info is None:
    logging.error(f'unable to get job info from cluster {cluster_name}, '
                  f'so unable to update run status')
    return JobStatus.UNKNOWN

  return GKE_TO_JOB_STATUS[GkeStatus.from_job_info(job_info)]


# ----------------------------------------------------------------------------
def update_job_status(j: Job) -> JobStatus:
  '''updates and returns job status

    Returns:
    current status for this job
    '''

  if j.status is not None and j.status.is_terminal():
    return j.status

  if j.spec.platform == Platform.LOCAL:
    return j.status

  if j.spec.platform == Platform.CAIP:
    j.status = get_caip_job_status(j)
    return j.status

  if j.spec.platform == Platform.GKE:
    j.status = get_gke_job_status(j)
    return j.status

  assert False, "can't get job status for platform {j.platform.name}"


# ----------------------------------------------------------------------------
def _stop_caip_job(j: Job) -> bool:
  '''stops a running caip job

  see:
  https://cloud.google.com/ai-platform/training/docs/reference/rest/v1/projects.jobs/cancel

  Args:
  j: job to stop

  Returns:
  True on success, False otherwise
  '''

  api = _get_caip_job_api()
  name = _get_caip_job_name(j)

  try:
    rsp = api.cancel(name=name).execute()
  except Exception as e:
    logging.error('error stopping CAIP job {name}: {e}')
    return False

  if rsp != {}:
    logging.error('error stopping CAIP job {name}: {pp.format(rsp)}')
    return False

  return True


# ----------------------------------------------------------------------------
def _stop_gke_job(j: Job) -> bool:
  '''stops a running gke job

  see:
  https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.11/#delete-job-v1-batch

  Args:
  j: job to stop

  Returns:
  True on success, False otherwise
  '''

  cluster_name = j.details['cluster_name']
  job_name = get_gke_job_name(j)

  cluster = get_job_cluster(j)
  if cluster is None:
    logging.error(f'unable to connect to cluster {cluster_name}, '
                  f'so unable to delete job {job_name}')
    return False

  status = cluster.delete_job(job_name=job_name)

  # gke deletes the job completely, so we can't then query its status later
  # thus if the request went through ok, then we mark as stopped
  if status:
    j.status = JobStatus.STOPPED

  return status


# ----------------------------------------------------------------------------
def stop_job(j: Job) -> bool:
  '''stops a running job

  Args:
  j: job to stop

  Returns:
  True on success, False otherwise
  '''

  current_status = update_job_status(j)

  if current_status not in [JobStatus.RUNNING, JobStatus.SUBMITTED]:
    return True

  if j.spec.platform == Platform.LOCAL:
    return True  # local jobs run to completion

  if j.spec.platform == Platform.CAIP:
    return _stop_caip_job(j)

  if j.spec.platform == Platform.GKE:
    return _stop_gke_job(j)

  return False


# ----------------------------------------------------------------------------
def replace_local_job_spec_image(spec: JobSpec, image_id: str) -> JobSpec:
  '''generates a new JobSpec based on an existing one, but replacing the
  image id

  Args:
  spec: job spec used as basis
  image_id: new image id

  Returns:
  new JobSpec
  '''

  old_image = spec.spec['container']
  old_cmd = spec.spec['command']
  new_cmd = list(map(lambda x: x if x != old_image else image_id, old_cmd))

  return JobSpec.get_or_create(
      experiment=spec.experiment,
      spec={
          'command': new_cmd,
          'container': image_id,
      },
      platform=Platform.LOCAL,
  )


# ----------------------------------------------------------------------------
def replace_caip_job_spec_image(spec: JobSpec, image_id: str) -> JobSpec:
  '''generates a new JobSpec based on an existing one, but replacing the
  image id

  Args:
  spec: job spec used as basis
  image_id: new image id

  Returns:
  new JobSpec
  '''

  new_spec = deepcopy(spec.spec)
  new_spec['trainingInput']['masterConfig']['imageUri'] = image_id

  return JobSpec.get_or_create(experiment=spec.experiment,
                               spec=new_spec,
                               platform=Platform.CAIP)


# ----------------------------------------------------------------------------
def replace_gke_job_spec_image(spec: JobSpec, image_id: str) -> JobSpec:
  '''generates a new JobSpec based on an existing one, but replacing the
  image id

  Args:
  spec: job spec used as basis
  image_id: new image id

  Returns:
  new JobSpec
  '''

  new_spec = deepcopy(spec.spec)
  for i in range(len(new_spec['template']['spec']['containers'])):
    new_spec['template']['spec']['containers'][i]['image'] = image_id

  print
  return JobSpec.get_or_create(
      experiment=spec.experiment,
      spec=new_spec,
      platform=Platform.GKE,
  )


# ----------------------------------------------------------------------------
def replace_job_spec_image(spec: JobSpec, image_id: str) -> JobSpec:
  '''generates a new JobSpec based on an existing one, but replacing the
  image id

  Args:
  spec: job spec used as basis
  image_id: new image id

  Returns:
  new JobSpec
  '''

  if spec.platform == Platform.LOCAL:
    return replace_local_job_spec_image(spec=spec, image_id=image_id)

  if spec.platform == Platform.CAIP:
    return replace_caip_job_spec_image(spec=spec, image_id=image_id)

  if spec.platform == Platform.GKE:
    return replace_gke_job_spec_image(spec=spec, image_id=image_id)

  return None
