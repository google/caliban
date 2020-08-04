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
import json
import logging
import os
import subprocess
import sys
import time

RESOURCE_DIR = "/.resources"
WRAPPER_CONFIG_FILE = 'caliban_wrapper_cfg.json'
WRAPPER_CONFIG_PATH = os.path.join(RESOURCE_DIR, WRAPPER_CONFIG_FILE)

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


def _parser():
  '''generates argument parser'''

  parser = argparse.ArgumentParser(
      description='caliban wrapper for container.',
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


def _parse_flags(argv):
  return _parser().parse_known_args(argv[1:])


def _start_services(services, env, delay=5):
  '''runs the commands in the services list, returns a list of Popen instances
  sets the environment variables in <env>, and delays by <delay> between
  commands
  '''
  procs = []
  for cmd in services:
    logging.info(' '.join(cmd))
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
  at ./resources/'caliban_wrapper_cfg.json as a dict
  '''
  if not os.path.exists(WRAPPER_CONFIG_PATH):
    return {}

  with open(WRAPPER_CONFIG_PATH) as f:
    cfg = json.load(f)

  return cfg


# ----------------------------------------------------------------------------
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


def main(args, passthrough_args):

  config = _get_config(args)

  env = copy.copy(dict(os.environ))
  caliban_env = config.get('env', {})
  cmd = args.caliban_command
  services = config.get('services', [])

  logging.info('base env: %s' % str(env))
  logging.info('env vars: %s' % str(caliban_env))
  logging.info('command: %s' % ' '.join([str(x) for x in cmd]))
  logging.info('passthrough args: %s' % str(passthrough_args))
  logging.info('caliban services: %s' % str(services))

  env.update(caliban_env)

  logging.info('env:\n%s' % str(env))

  _start_services(services, env)
  _execute_command(cmd, passthrough_args, env)


# ----------------------------------------------------------------------------
if __name__ == '__main__':
  main(*_parse_flags(sys.argv))