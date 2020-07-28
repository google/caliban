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
'''caliban utility to run google cloud_sql_proxy'''

import argparse
import copy
import logging
import os
import subprocess
import sys
import tempfile

logging.basicConfig(level=logging.INFO)


# ----------------------------------------------------------------------------
def _parser():
  '''generates argument parser'''

  parser = argparse.ArgumentParser(
      description='caliban utility for cloud_sql_proxy',
      prog='caliban_cloud_sql',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  parser.add_argument('--path', help='cloud sql socket path')
  parser.add_argument('--proxy', help='path to cloud_sql_proxy')
  parser.add_argument('--project', help='cloud sql instance project')
  parser.add_argument('--region', help='cloud sql instance region')
  parser.add_argument('--db', help='database name')
  parser.add_argument('--creds', help='path to credentials (optional)')

  return parser


# ----------------------------------------------------------------------------
def _parse_flags(argv):
  return _parser().parse_args(argv[1:])


# ----------------------------------------------------------------------------
def main(args):

  cmd = [
      args.proxy,
      '-dir',
      args.path,
      '-instances',
      '%s:%s:%s' % (args.project, args.region, args.db),
  ]

  logging.info(' '.join(cmd))

  env = copy.copy(dict(os.environ))
  if args.creds is not None:
    env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(
        os.path.expanduser(args.creds))

  subprocess.check_call(cmd, env=env)


# ----------------------------------------------------------------------------
if __name__ == '__main__':
  main(_parse_flags(sys.argv))
