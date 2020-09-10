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
from typing import Any, Dict, List, Optional, Tuple

import schema as s

import caliban.platform.cloud.types as ct
import caliban.util.schema as us


class JobMode(str, Enum):
  """Represents the two modes that you can use to execute a Caliban job."""
  CPU = 'CPU'
  GPU = 'GPU'

  @staticmethod
  def parse(label):
    return JobMode(label.upper().strip())


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

# Dictionary of the DLVM "Platform" to a sequence of versions that are
# currently available as DLVMs. The full list of images is here:
# https://console.cloud.google.com/gcr/images/deeplearning-platform-release/GLOBAL/
DLVMS = {
    "pytorch": [None, "1.0", "1.1", "1.2", "1.3", "1.4"],
    "tf": [None, "1.0", "1.13", "1.14", "1.15"],
    "tf2": [None, "2.0", "2.1", "2.2"],
}

# Schema for Caliban Config


def _dlvm_config(job_mode: JobMode) -> Dict[str, str]:
  """Generates a dict of custom DLVM image identifier -> the actual image ID
  available from GCR.

  """
  mode = job_mode.lower()

  def with_version(s: str, version: Optional[str], sep: str) -> Tuple[str, str]:
    return f"{s}{sep}{version}" if version else s

  def image(lib: str, version: Optional[str]) -> str:
    base = f"gcr.io/deeplearning-platform-release/{lib}-{mode}"
    k = with_version(f"dlvm:{lib}-{mode}", version, "-")
    v = with_version(base, version.replace('.', '-') if version else None, ".")
    return (k, v)

  return dict(
      [image(lib, v) for lib, versions in DLVMS.items() for v in versions])


# This is a dictionary of some identifier like 'dlvm:pytorch-1.0' to the actual
# Docker image ID.
DLVM_CONFIG = {
    **_dlvm_config(JobMode.CPU),
    **_dlvm_config(JobMode.GPU),
}


def expand_image(image: str) -> str:
  """If the supplied image is one of our special prefixed identifiers, returns
  the expanded Docker image ID. Else, returns the input.

  """
  return DLVM_CONFIG.get(image, image)


AptPackages = s.Or(
    [str], {
        s.Optional("gpu", default=list): [str],
        s.Optional("cpu", default=list): [str]
    },
    error=""""apt_packages" entry must be a dictionary or list, not '{}'""")

Image = s.And(str, s.Use(expand_image))

BaseImage = s.Or(
    Image, {
        s.Optional("gpu", default=None): Image,
        s.Optional("cpu", default=None): Image
    },
    error=
    """"base_image" entry must be a string OR dict with 'cpu' and 'gpu' keys, not '{}'"""
)

GCloudConfig = {
    s.Optional("project_id"): s.And(str, len),
    s.Optional("cloud_key"): s.And(str, len)
}

MLFlowConfig = {
    'project': str,
    'region': str,
    'db': str,
    'user': str,
    'password': str,
    'artifact_root': str,
    s.Optional('debug'): bool,
}

UVMLFlowConfig = {
    s.Optional('pubsub_project'): str,  # default = mlflow_config.project
    s.Optional('pubsub_topic', default='mlflow'): str,
}

UVConfig = {
    s.Optional('mlflow'): UVMLFlowConfig,
}

# Config items that are project-specific, and don't belong in a global
# .calibanconfig shared between projects.
ProjectConfig = {
    s.Optional("build_time_credentials", default=False):
        bool,
    s.Optional("base_image", default=None):
        BaseImage,
    s.Optional("apt_packages", default=AptPackages.validate({})):
        AptPackages,
    # If present, Caliban will attempt to install Julia into the base container.
    s.Optional("julia_version", default=None):
        s.And(str, s.Use(lambda s: s.strip())),
}

# Elements of calibanconfig that are fair game to share between projects.
#
SystemConfig = {
    s.Optional("default_mode", default=JobMode.CPU): s.Use(JobMode.parse),
    s.Optional("gcloud", default={}): GCloudConfig,
    s.Optional("mlflow_config", default=None): MLFlowConfig,
    s.Optional("uv", default={}): UVConfig,
}

# The final, parsed calibanconfig.
CalibanConfig = s.Schema({**ProjectConfig, **SystemConfig})

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
  packages = conf.get("apt_packages", [])

  if isinstance(packages, dict):
    k = "gpu" if gpu(mode) else "cpu"
    return packages[k]

  return packages


def base_image(conf: CalibanConfig, mode: JobMode) -> Optional[str]:
  """Returns a custom base image, if the user has supplied one in the
  calibanconfig.

  If the custom base image has a marker for a format string, like 'pytorch-{}',
  this method will fill it in with the current mode (cpu or gpu).

  """
  ret = None
  mode_s = mode.lower()

  image = conf.get("base_image")
  if image is None:
    return ret

  elif isinstance(image, str):
    ret = image

  else:
    # dictionary case.
    ret = image[mode_s]

  # we run expand_image again in case the user has included a format {} in the
  # string.
  return expand_image(ret.format(mode_s))


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
