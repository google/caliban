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
import itertools
import os
import sys
from enum import Enum
from typing import Any, Dict, List, Union, Optional
import re
import commentjson
import yaml

import caliban.cloud.types as ct
import caliban.util as u

# int, str and bool are allowed in a final experiment; lists are markers for
# expansion.
ExpValue = Union[int, str, bool]

# Entry in an experiment config. If any values are lists they're expanded into
# a sequence of experiment configs.
Expansion = Dict[str, Union[ExpValue, List[ExpValue]]]

# An experiment config can be a single (potentially expandable) dictionary, or
# a list of many such dicts.
ExpConf = Union[Expansion, List[Expansion]]

# A final experiment can only contain valid ExpValues, no expandable entries.
Experiment = Dict[str, ExpValue]


# Mode
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


def caliban_config() -> CalibanConfig:
  """Returns a dict that represents a `.calibanconfig.json` file if present,
  empty dictionary otherwise.

  """
  if not os.path.isfile(CALIBAN_CONFIG):
    return {}

  with open(CALIBAN_CONFIG) as f:
    conf = commentjson.load(f)
    return conf


def expand_experiment_config(items: ExpConf) -> List[Experiment]:
  """Expand out the experiment config for job submission to Cloud.

  """
  if isinstance(items, list):
    return list(
        itertools.chain.from_iterable(
            [expand_experiment_config(m) for m in items]))

  tupleized_items = u.tupleize_dict(items)
  return [u.expand_compound_dict(d) for d in u.dict_product(tupleized_items)]


def validate_compound_keys(m: ExpConf) -> ExpConf:
  """Check that:

  - all key are strings, which do not:
      contain spaces or consecutive commas
      contain commas unless inside a '[...]' compound key
      contain '[' unless at the beginning, and matched by a ']' at the end
      contain ']' unless at the end, and matched by a '[' at the beginning
      begin with '[' and end with ']' unless also containing a comma
  - all values are either boolean, strings, numbers or lists
  """

  def check_k(k):
    if not isinstance(k, str):
      raise argparse.ArgumentTypeError(
          "Key '{}' is invalid! Keys must be strings.".format(k))

    valid_re_str = "[^\s\,\]\[]+"
    list_re = re.compile('\A({}|\[\s*({})(\s*,\s*{})*\s*\])\Z'.format(
        valid_re_str, valid_re_str, valid_re_str))

    if list_re.match(k) is None:
      raise argparse.ArgumentTypeError(
          "Key '{}' is invalid! Not a valid compound key.".format(k))

  def check_v(v):
    types = [list, bool, str, int, float]
    if not any(map(lambda t: isinstance(v, t), types)):
      raise argparse.ArgumentTypeError("Value '{}' in the expanded \
    experiment config '{}' is invalid! Values must be strings, \
    lists, ints, floats or bools.".format(v, m))

  def check_kv_compatibility(k, v):
    """ For already validated k and v, check that
    if k is a compound key, the number of arguments in each sublist must match the
    number of arguments in k """

    if k[0] == '[':
      n_args = len(k.strip('][').split(','))
      if not (isinstance(v, list)):
        raise argparse.ArgumentTypeError(
            "Key '{}' and value '{}' are incompatible: \
                key is compound, but value is not.".format(k, v))
      else:
        if isinstance(v[0], list):
          for vi in v:
            if len(vi) != n_args:
              raise argparse.ArgumentTypeError("Key '{}' and value '{}' have \
                              incompatible arities.".format(k, vi))
        else:
          if len(v) != n_args:
            raise argparse.ArgumentTypeError("Key '{}' and value '{}' have \
                            incompatible arities.".format(k, v))

  if isinstance(m, list):
    return [validate_compound_keys(i) for i in m]

  for k, v in m.items():
    check_k(k)
    check_v(v)
    check_kv_compatibility(k, v)

  return m


def validate_expansion(m: Expansion) -> Expansion:
  """Check that:

  - all key are strings
  - all values are either boolean, strings, numbers or lists
  """

  def valid_k(k):
    return isinstance(k, str)

  def valid_v(v):
    types = [list, bool, str, int, float]
    return any(map(lambda t: isinstance(v, t), types))

  for k, v in m.items():
    if not valid_k(k):
      raise argparse.ArgumentTypeError(
          "Key '{}' is invalid! Keys must be strings.".format(k))

    if not valid_v(v):
      raise argparse.ArgumentTypeError("Value '{}' in the expanded \
experiment config '{}' is invalid! Values must be strings, \
lists, ints, floats or bools.".format(v, m))

  return m


def validate_experiment_config(items: ExpConf) -> ExpConf:
  """Check that the input is either a list of valid experiment configs or a valid
  expansion itself. Returns the list/dict or throws an exception if invalid.

  """

  # Validate the compound keys before expansion
  if isinstance(items, list) or isinstance(items, dict):
    validate_compound_keys(items)
  else:
    raise argparse.ArgumentTypeError("The experiment config is invalid! \
    The JSON file must contain either a dict or a list.")

  for item in expand_experiment_config(items):
    validate_expansion(item)
  return items


def load_experiment_config(s):
  if s.lower() == 'stdin':
    json = commentjson.load(sys.stdin)
  else:
    with open(u.validated_file(s)) as f:
      json = commentjson.load(f)

  return validate_experiment_config(json)


def experiment_to_args(m: Experiment,
                       base: Optional[List[str]] = None) -> List[str]:
  """Returns the list of flag keys and values that corresponds to the supplied
  experiment.

  Keys all expand to the full '--key_name' style that typical Python flags are
  represented by.

  All values except for boolean values are inserted as str(v). For boolean
  values, if the value is True, the key is inserted by itself (in the format
  --key_name). If the value is False, the key isn't inserted at all.

  """
  if base is None:
    base = []

  ret = [] + base

  for k, v in m.items():
    opt = "--{}".format(k)
    if isinstance(v, bool):
      # Append a flag if the boolean flag is true, else do nothing.
      if v:
        ret.append(opt)
    else:
      ret.append("--{}".format(k))
      ret.append(str(v))

  return ret
