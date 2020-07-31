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
"""Caliban has built-in (alpha) support for configuring containers for easy
metrics tracking via MLFlow. This module provides functions useful for
configuring a container for this behavior.

"""

import datetime
import json
import os

import caliban.util as u
import caliban.history.types as ht
from typing import Dict, Any, List

CLOUD_SQL_WRAPPER_SCRIPT = 'cloud_sql_proxy.py'
WRAPPER_SCRIPT = 'caliban_wrapper.py'
RESOURCE_DIR = "/.resources"


def cloud_sql_proxy_path() -> str:
  """Returns an absolute path to the cloud_sql_proxy python wrapper that we
  inject into containers.

  """
  return u.resource(CLOUD_SQL_WRAPPER_SCRIPT)


def wrapper_script_path() -> str:
  """Returns an absolute path to the caliban_wrapper python script that we
  inject into containers.

  """
  return u.resource(WRAPPER_SCRIPT)


def _mlflow_job_name(index: int, user: str = None) -> str:
  '''returns mlflow job name for local caliban job'''
  user = user or u.current_user()
  timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
  return f'{user}-{timestamp}-{index}'


def mlflow_args(
    experiment: ht.Experiment,
    caliban_config: Dict[str, Any],
    index: int,
) -> List[str]:
  '''returns mlflow args for caliban wrapper
  experiment: experiment
  command: docker command to execute
  caliban_config: caliban config dictionary
  index: job index

  Returns:
  mlflow args
  '''

  mlflow_cfg = caliban_config.get('mlflow_config', None)
  if mlflow_cfg is None:
    return []

  user = mlflow_cfg['user']
  pw = mlflow_cfg['password']
  db = mlflow_cfg['db']
  project = mlflow_cfg['project']
  region = mlflow_cfg['region']
  artifact_root = mlflow_cfg['artifact_root']

  socket_path = '/tmp/cloudsql'
  proxy_path = os.path.join('.', 'cloud_sql_proxy')

  config = json.dumps({
      'proxy': proxy_path,
      'path': socket_path,
      'project': project,
      'region': region,
      'db': db,
      'creds': '~/.config/gcloud/application_default_credentials.json',
  })

  cmd = ['python', os.path.join(RESOURCE_DIR, CLOUD_SQL_WRAPPER_SCRIPT), config]

  uri = (f'postgresql+pg8000://{user}:{pw}@/{db}?unix_sock={socket_path}/'
         f'{project}:{region}:{db}/.s.PGSQL.5432')

  args = [
      '--caliban_service',
      json.dumps(cmd),
      '--caliban_env',
      f'MLFLOW_TRACKING_URI={uri}',
      '--caliban_env',
      f'MLFLOW_ARTIFACT_ROOT={artifact_root}',
      '--caliban_env',
      f'CALIBAN_EXPERIMENT_NAME={experiment.xgroup.name}',
      '--caliban_env',
      f'CALIBAN_RUN_NAME={_mlflow_job_name(index=index)}',
  ]

  return args
