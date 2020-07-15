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

import os
import sys
from enum import Enum
from typing import Any, Dict, List, Optional

import schema as s

import caliban.platform.cloud.types as ct
import caliban.util.schema as us


class JobMode(str, Enum):
  """Represents the two modes that you can use to execute a Caliban job."""
  CPU = 'CPU'
  GPU = 'GPU'

  @staticmethod
  def parse(label):
    return JobMode(label.upper())


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

# Schema for Caliban Config

AptPackages = s.Or(
    [str], {
        s.Optional("gpu", default=list): [str],
        s.Optional("cpu", default=list): [str]
    },
    error=""""apt_packages" entry must be a dictionary or list, not '{}'""")

CalibanConfig = s.Schema({
    s.Optional("build_time_credentials", default=False):
        bool,
    s.Optional("default_mode", default=JobMode.CPU):
        s.Use(JobMode.parse),
    s.Optional("project_id"):
        s.And(str, len),
    s.Optional("cloud_key"):
        s.And(str, len),
    s.Optional("base_image"):
        str,
    s.Optional("apt_packages", default=dict):
        AptPackages,

    # Allow extra entries without killing the schema to allow for backwards
    # compatibility.
    s.Optional(str):
        str,
})

# Accessors


def gpu(job_mode: JobMode) -> bool:
  """Returns True if the supplied JobMode is JobMode.GPU, False otherwise.

  """
  return job_mode == JobMode.GPU


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
  caliban.platform.cloud.

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
  packages = conf["apt_packages"]

  if isinstance(packages, dict):
    k = "gpu" if gpu(mode) else "cpu"
    return packages[k]

  return packages


def caliban_config(conf_path: str = CALIBAN_CONFIG) -> CalibanConfig:
  """Returns a dict that represents a `.calibanconfig.json` file if present,
  empty dictionary otherwise.

  If the supplied conf_path is present, but doesn't pass the supplied schema,
  errors and kills the program.

  """
  if not os.path.isfile(conf_path):
    return {}

  with us.error_schema(conf_path):
    return s.And(us.Json, CalibanConfig).validate(conf_path)
