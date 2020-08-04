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
from contextlib import contextmanager
from typing import Dict, Any, List, Optional

CLOUD_SQL_WRAPPER_SCRIPT = 'cloud_sql_proxy.py'
WRAPPER_SCRIPT = 'caliban_launcher.py'
RESOURCE_DIR = "/.resources"
WRAPPER_CONFIG_FILE = 'caliban_wrapper_cfg.json'
WRAPPER_CONFIG_PATH = os.path.join(RESOURCE_DIR, WRAPPER_CONFIG_FILE)


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


@contextmanager
def wrapper_config_file(
    path: str,
    caliban_config: Optional[Dict[str, Any]] = None,
):
  '''creates a configuration file for the caliban wrapper script
  This file contains the wrapper configuration that does not vary across
  each caliban job being submitted, so it can be copied into the container.

  This is to be used as a contextmanager yielding the path to the file:

  with wrapper_config_file('.', caliban_config) as cfg_file:
    # do things

  The config file is deleted upon exiting the context scope.

  Args:
  path: directory in which to write file (this must exist
  caliban_config: caliban configuration dictionary

  Yields:
  path to configuration file
  '''

  cfg = {}
  mlflow_cfg = caliban_config.get('mlflow_config', None)
  config_file_path = os.path.join(path, WRAPPER_CONFIG_FILE)

  if mlflow_cfg is not None:
    user = mlflow_cfg['user']
    pw = mlflow_cfg['password']
    db = mlflow_cfg['db']
    project = mlflow_cfg['project']
    region = mlflow_cfg['region']
    artifact_root = mlflow_cfg['artifact_root']

    socket_path = '/tmp/cloudsql'
    proxy_path = os.path.join(os.sep, 'usr', 'bin', 'cloud_sql_proxy')

    proxy_config = json.dumps({
        'proxy': proxy_path,
        'path': socket_path,
        'project': project,
        'region': region,
        'db': db,
        'creds': '~/.config/gcloud/application_default_credentials.json',
    })

    proxy_cmd = [
        'python',
        os.path.join(RESOURCE_DIR, CLOUD_SQL_WRAPPER_SCRIPT), proxy_config
    ]

    tracking_uri = (
        f'postgresql+pg8000://{user}:{pw}@/{db}?unix_sock={socket_path}/'
        f'{project}:{region}:{db}/.s.PGSQL.5432')

    config = {
        'services': [proxy_cmd],
        'env': {
            'MLFLOW_TRACKING_URI': tracking_uri,
            'MLFLOW_ARTIFACT_ROOT': artifact_root
        }
    }

  with open(config_file_path, 'w') as f:
    json.dump(config, f, indent=2)

  try:
    yield config_file_path
  finally:
    if os.path.exists(config_file_path):
      os.remove(config_file_path)


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
  caliban_config: caliban config dictionary
  index: job index

  Returns:
  mlflow args
  '''

  launcher_config = json.dumps({
      'env': {
          'MLFLOW_EXPERIMENT_NAME': experiment.xgroup.name,
          'MLFLOW_RUN_NAME': _mlflow_job_name(index=index)
      }
  })

  return ['--caliban_config', launcher_config]
