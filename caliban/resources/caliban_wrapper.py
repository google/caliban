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
'''caliban wrapper utility'''

import argparse
import copy
import json
import logging
import os
import subprocess
import sys
import time

logging.basicConfig(level=logging.INFO)


# ----------------------------------------------------------------------------
def _parse_kv_pair(s):
  """
    Parse a key, value pair, separated by '='

    On the command line (argparse) a declaration will typically look like:
        foo=hello
    or
        foo="hello world"

  Returns: (key,value) tuple"""
  items = s.split('=')
  k = items[0].strip()  # Remove whitespace around keys

  if len(items) <= 1:
    raise argparse.ArgumentTypeError(
        "Couldn't parse label '{}' into k=v format.".format(s))

  v = '='.join(items[1:])
  return (k, v)


# ----------------------------------------------------------------------------
def _parse_json(argname, json_string, expected_type):
  """parses a json string, validating the return type"""

  try:
    obj = json.loads(json_string)
    assert isinstance(obj, expected_type)
  except Exception as e:
    raise argparse.ArgumentTypeError(
        '%s must be a json %s' % (argname, expected_type.__name__),)

  return obj


# ----------------------------------------------------------------------------
def _parser():
  '''generates argument parser'''

  parser = argparse.ArgumentParser(
      description='caliban wrapper for container',
      prog='caliban_wrapper',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  parser.add_argument(
      '--caliban_env',
      metavar="KEY=VALUE",
      action='append',
      type=_parse_kv_pair,
      help='environment variables to set for container',
  )

  parser.add_argument(
      '--caliban_command',
      type=lambda x: _parse_json('command', x, list),
      help='main container command to execute, as json list',
  )

  parser.add_argument(
      '--caliban_service',
      type=lambda x: _parse_json('service', x, list),
      action='append',
      help=
      'run the given command as a service prior to running the main entrypoint')

  parser.add_argument(
      '--caliban_delay',
      type=int,
      default=5,
      help='delay in seconds between service executions',
  )

  return parser


# ----------------------------------------------------------------------------
def _parse_flags(argv):
  return _parser().parse_known_args(argv[1:])


# ----------------------------------------------------------------------------
def _start_services(services, env, delay):
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


# ----------------------------------------------------------------------------
def _execute_command(cmd, args, env):
  '''executes the given command with the provided args and env vars
  this blocks until the given command completes
  '''

  cmd = cmd + args
  logging.info(' '.join(cmd))
  subprocess.check_call(cmd, env=env)


# ----------------------------------------------------------------------------
def main(args, passthrough_args):

  env = copy.copy(dict(os.environ))
  caliban_env = dict(args.caliban_env or [])
  cmd = args.caliban_command
  services = args.caliban_service
  delay = args.caliban_delay

  logging.info('base env: %s' % str(env))
  logging.info('env vars: %s' % str(caliban_env))
  logging.info('command: %s' % ' '.join([str(x) for x in cmd]))
  logging.info('passthrough args: %s' % str(passthrough_args))
  logging.info('caliban services: %s' % str(services))

  env.update(caliban_env)

  logging.info('dir:\n%s' % str(os.listdir()))
  logging.info('env:\n%s' % str(env))

  _start_services(services, env, delay)
  _execute_command(cmd, passthrough_args, env)


# ----------------------------------------------------------------------------
if __name__ == '__main__':
  main(*_parse_flags(sys.argv))
