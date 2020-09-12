#!/usr/bin/env python
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
'''This utility wraps the caliban user's entrypoint in order to configure
additional service processes and environment variables for each caliban
job.
'''

import argparse
import copy
import google.auth
import json
import logging
import os
import subprocess
import sys
import time

RESOURCE_DIR = "/.resources"
LAUNCHER_CONFIG_FILE = 'caliban_launcher_cfg.json'
LAUNCHER_CONFIG_PATH = os.path.join(RESOURCE_DIR, LAUNCHER_CONFIG_FILE)

logging.basicConfig(level=logging.INFO)


def _parse_json(argname, json_string, expected_type):
  """parses a json string, validating the return type"""

  try:
    obj = json.loads(json_string)
    assert isinstance(obj, expected_type)
  except Exception:
    raise argparse.ArgumentTypeError(
        "%s must be a json %s. Got '%s'." %
        (argname, expected_type.__name__, json_string))

  return obj


def _parser():  # pragma: no cover
  parser = argparse.ArgumentParser(
      description='caliban launcher for container.',
      prog='caliban_launcher',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  parser.add_argument(
      '--caliban_config',
      type=lambda x: _parse_json('env', x, dict),
      default={},
      help='JSON config dictionary',
  )

  parser.add_argument(
      '--caliban_command',
      type=lambda x: _parse_json('command', x, list),
      help='main container command to execute, as json list',
  )

  return parser


def _parse_flags(argv):  # pragma: no cover
  return _parser().parse_known_args(argv[1:])


def _start_services(services, env, delay=5):
  '''runs the commands in the services list, returns a list of Popen instances
  sets the environment variables in <env>, and delays by <delay> between
  commands
  '''
  procs = []
  for cmd in services:
    procs.append(subprocess.Popen(cmd, env=env))
    time.sleep(delay)

  return procs


def _execute_command(cmd, args, env):
  '''executes the given command with the provided args and env vars
  this blocks until the given command completes
  '''

  cmd = cmd + args
  logging.info(' '.join(cmd))
  subprocess.check_call(cmd, env=env)


def _load_config_file():
  '''loads the launcher configuration data from the config file
  at ./resources/'caliban_laucher_cfg.json as a dict
  '''
  if not os.path.exists(LAUNCHER_CONFIG_PATH):
    return {}

  with open(LAUNCHER_CONFIG_PATH) as f:
    cfg = json.load(f)

  return cfg


def _get_config(args):
  '''gets the configuration dictionary for the launcher by combining the
  static configuration in the launcher config file and the dynamic
  configuration passed in the command args. Here the dynamic args take
  precedence over static args where there is a collision.
  '''

  cfg = _load_config_file()
  dynamic_config = args.caliban_config

  for k, v in dynamic_config.items():
    if k not in cfg:
      cfg[k] = v
    elif k == 'env':
      cfg[k].update(v)
    elif k == 'services':
      cfg[k] += v

  return cfg


def _ensure_non_null_project(env):
  '''Ensures that the google cloud python api methods can get a non-none
  project id. This is useful because google.cloud.storage.Client()
  requires a non-none project, and writing to a storage bucket is a fairly
  common use case. We first attempt to determine the project via
  google.auth.default(), and if this is not successful, we then resort to
  setting the GOOGLE_CLOUD_PROJECT environment variable to a placeholder value.

  Args:
  env: dictionary of environment variables

  Returns:
  possibly modified env dictionary
  '''

  if 'GOOGLE_CLOUD_PROJECT' in env:
    return env

  _, project_id = google.auth.default()
  if project_id is not None:
    return env

  new_env = copy.copy(env)
  new_env['GOOGLE_CLOUD_PROJECT'] = 'placeholder'
  return new_env


def main(args, passthrough_args):  # pragma: no cover

  config = _get_config(args)

  env = copy.copy(dict(os.environ))
  caliban_env = config.get('env', {})

  cmd = args.caliban_command
  services = config.get('services', [])

  env.update(caliban_env)
  env = _ensure_non_null_project(env)

  _start_services(services, env)
  _execute_command(cmd, passthrough_args, env)


if __name__ == '__main__':  # pragma: no cover
  main(*_parse_flags(sys.argv))
