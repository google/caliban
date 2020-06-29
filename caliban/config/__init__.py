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
"""
Utilities for our job runner, for working with configs.
"""

from __future__ import absolute_import, division, print_function

import argparse
import os
import sys
from enum import Enum
from typing import Any, Dict, List, Optional

import commentjson
import yaml

import caliban.cloud.types as ct


class JobMode(str, Enum):
  CPU = 'CPU'
  GPU = 'GPU'


# Special config for Caliban.
CalibanConfig = Dict[str, Any]

DRY_RUN_FLAG = "--dry_run"
CALIBAN_CONFIG = ".calibanconfig.json"

# Defaults for various input values that we can supply given some partial set
# of info from the CLI.
DEFAULT_REGION = ct.US.central1

# : Dict[JobMode, ct.MachineType]
DEFAULT_MACHINE_TYPE = {
    JobMode.CPU: ct.MachineType.highcpu_32,
    JobMode.GPU: ct.MachineType.standard_8
}
DEFAULT_GPU = ct.GPU.P100

# Config to supply for CPU jobs.
DEFAULT_ACCELERATOR_CONFIG = {
    "count": 0,
    "type": "ACCELERATOR_TYPE_UNSPECIFIED"
}


def gpu(job_mode: JobMode) -> bool:
  """Returns True if the supplied JobMode is JobMode.GPU, False otherwise.

  """
  return job_mode == JobMode.GPU


def load_yaml_config(path):
  """returns the config parsed based on the info in the flags.

  Grabs the config file, written in yaml, slurps it in.
  """
  with open(path) as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

  return config


def load_config(path, mode='yaml'):
  """Load a JSON or YAML config.

  """
  if mode == 'json':
    with open(path) as f:
      return commentjson.load(f)

  return load_yaml_config(path)


def valid_json(path: str) -> Dict[str, Any]:
  """Loads JSON if the path points to a valid JSON file; otherwise, throws an
  exception that's picked up by argparse.

  """
  try:
    return load_config(path, mode='json')
  except commentjson.JSONLibraryException:
    raise argparse.ArgumentTypeError(
        """File '{}' doesn't seem to contain valid JSON. Try again!""".format(
            path))


def extract_script_args(m: Dict[str, Any]) -> List[str]:
  """Strip off the "--" argument if it was passed in as a separator."""
  script_args = m.get("script_args")
  if script_args is None or script_args == []:
    return script_args

  head, *tail = script_args

  return tail if head == "--" else script_args


def extract_project_id(m: Dict[str, Any]) -> str:
  """Attempts to extract the project_id from the args; falls back to an
  environment variable, or exits if this isn't available. There's no sensible
  default available.

  """
  project_id = m.get("project_id") or os.environ.get("PROJECT_ID")

  if project_id is None:
    print()
    print(
        "\nNo project_id found. 'caliban cloud' requires that you either set a \n\
$PROJECT_ID environment variable with the ID of your Cloud project, or pass one \n\
explicitly via --project_id. Try again, please!")
    print()

    sys.exit(1)

  return project_id


def extract_region(m: Dict[str, Any]) -> ct.Region:
  """Returns the region specified in the args; defaults to an environment
  variable. If that's not supplied defaults to the default cloud provider from
  caliban.cloud.

  """
  region = m.get("region") or os.environ.get("REGION")

  if region:
    return ct.parse_region(region)

  return DEFAULT_REGION


def extract_zone(m: Dict[str, Any]) -> str:
  return "{}-a".format(extract_region(m))


def extract_cloud_key(m: Dict[str, Any]) -> Optional[str]:
  """Returns the Google service account key filepath specified in the args;
  defaults to the $GOOGLE_APPLICATION_CREDENTIALS variable.

  """
  return m.get("cloud_key") or \
    os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")


def apt_packages(conf: CalibanConfig, mode: JobMode) -> List[str]:
  """Returns the list of aptitude packages that should be installed to satisfy
  the requests in the config.

  """
  packages = conf.get("apt_packages") or {}

  if isinstance(packages, dict):
    k = "gpu" if gpu(mode) else "cpu"
    return packages.get(k, [])

  elif isinstance(packages, list):
    return packages

  else:
    raise argparse.ArgumentTypeError(
        """{}'s "apt_packages" entry must be a dictionary or list, not '{}'""".
        format(CALIBAN_CONFIG, packages))
