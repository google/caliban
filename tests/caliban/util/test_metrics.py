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

import json
import os
import tempfile

import caliban.util as u
import caliban.util.metrics as um


def test_cloud_sql_proxy_path():
  """Check that the proxy resource exists and wasn't deleted or renamed."""
  assert um.cloud_sql_proxy_path() is not None

  # check that the name matches the global variable.
  expected = os.path.join(u.resource(""), um.CLOUD_SQL_WRAPPER_SCRIPT)
  assert um.cloud_sql_proxy_path() == expected


def test_launcher_path():
  """Check that the launcher resource exists and wasn't deleted or renamed."""
  assert um.launcher_path() is not None

  # check that the name matches the global variable.
  expected = os.path.join(u.resource(""), um.LAUNCHER_SCRIPT)
  assert um.launcher_path() == expected


def test_mlflow_args():
  '''verifies that we generate the dynamic args for the caliban launcher
  script for mlflow integration'''

  # test case when caliban_config has no mlflow configuration
  cfg = {
      'caliban_config': {
          'base_image': 'gcr.io/a/b'
      },
      'experiment_name': 'foo',
      'index': 42,
      'tags': {
          'a': 'x',
          'b': 7
      },
  }

  mlflow_args = um.mlflow_args(**cfg)
  assert len(mlflow_args) == 0

  # test case when caliban_config has empty mlflow configuration
  cfg = {
      'caliban_config': {
          'base_image': 'gcr.io/a/b',
          'mlflow_config': None
      },
      'experiment_name': 'foo',
      'index': 42,
      'tags': {
          'a': 'x',
          'b': 7
      },
  }

  mlflow_args = um.mlflow_args(**cfg)
  assert len(mlflow_args) == 0

  # test case when caliban_config has mlflow configuration
  cfg = {
      'caliban_config': {
          'mlflow_config': {}
      },
      'experiment_name': 'foo',
      'index': 42,
      'tags': {
          'a': 'x',
          'b': 7
      },
  }

  mlflow_args = um.mlflow_args(**cfg)

  assert len(mlflow_args) == 2
  assert mlflow_args[0] == '--caliban_config'

  # make sure that config is json dict
  arg_dict = json.loads(mlflow_args[1])
  assert isinstance(arg_dict, dict)

  assert 'env' in arg_dict
  env_vars = arg_dict['env']
  assert 'MLFLOW_EXPERIMENT_NAME' in env_vars
  assert env_vars['MLFLOW_EXPERIMENT_NAME'] == cfg['experiment_name']

  assert 'MLFLOW_RUN_NAME' in env_vars
  assert isinstance(env_vars['MLFLOW_RUN_NAME'], str)

  for k, v in cfg['tags'].items():
    k_e = f'ENVVAR_{k}'
    assert k_e in env_vars
    assert env_vars[k_e] == v


def test_launcher_config_file():
  '''verifies that we generate the static caliban launcher config file
  properly for different scenarios'''

  # test config file without mlflow
  with tempfile.TemporaryDirectory() as tmpdir:
    cfg = {
        'path': tmpdir,
        'caliban_config': {
            'base_image': 'gcr.io/blueshift-playground/blueshift:cpu',
            'apt_packages': ['curl'],
        },
    }

    cfg_fname = ''
    with um.launcher_config_file(**cfg) as fname:
      cfg_fname = fname
      assert fname is not None
      assert os.path.exists(fname)
      assert fname == os.path.join(tmpdir, um.LAUNCHER_CONFIG_FILE)

      with open(fname, 'r') as f:
        lcfg = json.load(f)

      assert isinstance(lcfg, dict)
      assert 'services' in lcfg
      assert 'env' in lcfg
      services = lcfg['services']
      env = lcfg['env']
      assert isinstance(services, list)
      assert isinstance(env, dict)
      assert len(services) == 0

    # make sure we clean up
    assert not os.path.exists(cfg_fname)

  # test config file with mlflow
  with tempfile.TemporaryDirectory() as tmpdir:

    project = 'foo-project'
    region = 'foo-region'
    db = 'foo-db'
    user = 'foo-user'
    password = 'foo-password'
    artifact_root = 'foo-artifact-root'

    cfg = {
        'path': tmpdir,
        'caliban_config': {
            'base_image': 'gcr.io/blueshift-playground/blueshift:cpu',
            'apt_packages': ['curl'],
            'mlflow_config': {
                'project': project,
                'region': region,
                'db': db,
                'user': user,
                'password': password,
                'artifact_root': artifact_root,
            },
            'uv': {
                'mlflow': {
                    'pubsub_topic': 'mlflow',
                }
            }
        },
    }

    proxy_config = {
        'proxy': os.path.join(os.sep, 'usr', 'bin', 'cloud_sql_proxy'),
        'path': '/tmp/cloudsql',
        'project': project,
        'region': region,
        'db': db,
        'creds': '~/.config/gcloud/application_default_credentials.json',
    }

    proxy_cmd = [
        'python',
        os.path.join(um.RESOURCE_DIR, um.CLOUD_SQL_WRAPPER_SCRIPT),
        proxy_config,
    ]

    cfg_fname = ''
    with um.launcher_config_file(**cfg) as fname:
      cfg_fname == fname
      assert fname is not None
      assert os.path.exists(fname)
      assert fname == os.path.join(tmpdir, um.LAUNCHER_CONFIG_FILE)

      with open(fname, 'r') as f:
        lcfg = json.load(f)

      assert isinstance(lcfg, dict)
      assert 'services' in lcfg
      assert 'env' in lcfg

      services = lcfg['services']
      env = lcfg['env']

      assert isinstance(services, list)
      assert isinstance(env, dict)
      assert len(services) == 1

      cfg_proxy_cmd = services[0]
      assert cfg_proxy_cmd[0] == proxy_cmd[0]
      assert cfg_proxy_cmd[1] == proxy_cmd[1]
      cfg_proxy_config = proxy_cmd[2]
      for k, v in proxy_config.items():
        assert k in cfg_proxy_config
        assert cfg_proxy_config[k] == v

    # make sure we clean up appropriately
    assert not os.path.exists(cfg_fname)
