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
"""Python wrapper around Google's cloud_sql_proxy tool that accepts
configuration via a JSON dictionary of the form:

{
    "proxy": "path to cloud_sql_proxy",
    "path": "cloud_sql socket path",
    "project": "gcp_project",
    "region": "gcp_region",
    "db": "database_name",
    "creds": "path_to_credentials (optional)"
}

This script lives in a dotfile
"""

import argparse
import copy
import json
import logging
import os
import subprocess
import sys

logging.basicConfig(level=logging.INFO)


# ----------------------------------------------------------------------------
def _parser():
  parser = argparse.ArgumentParser(
      description='cloud_sql_proxy wrapper that allows JSON configuration.',
      prog='cloud_sql_proxy',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  parser.add_argument("config", type=json.loads)
  return parser


# ----------------------------------------------------------------------------
def _parse_flags(argv):
  return _parser().parse_args(argv[1:])


# ----------------------------------------------------------------------------
def main(proxy="",
         path="",
         project="",
         region="",
         db="",
         creds=None,
         debug=False):
  cmd = [
      proxy,
      '-dir',
      path,
      '-instances',
      f"{project}:{region}:{db}",
  ]

  if not debug:
    cmd.append('-quiet')

  env = copy.copy(dict(os.environ))

  if creds is not None:
    env['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath(
        os.path.expanduser(creds))

  subprocess.check_call(cmd, env=env)


# ----------------------------------------------------------------------------
if __name__ == '__main__':
  m = _parse_flags(sys.argv)
  main(**m.config)
