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
JobMode = Enum("JobMode", ("CPU", "GPU"))

DRY_RUN_FLAG = "--dry_run"

# Defaults for various input values that we can supply given some partial set
# of info from the CLI.
DEFAULT_REGION = ct.US.central1
DEFAULT_MACHINE_TYPE: Dict[JobMode, ct.MachineType] = {
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
        f"""File '{path}' doesn't seem to contain valid JSON. Try again!""")


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
        f"\nNo project_id found. 'caliban cloud' requires that you either set a \n\
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
  return m.get("region") or \
    ct.parse_region(os.environ.get("REGION")) or \
    DEFAULT_REGION


def extract_cloud_key(m: Dict[str, Any]) -> Optional[str]:
  """Returns the Google service account key filepath specified in the args;
  defaults to the $GOOGLE_APPLICATION_CREDENTIALS variable.

  """
  return m.get("cloud_key") or \
    os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")


def validate_expansion(m: Expansion) -> Expansion:
  """Check that:

  - all key are strings
  - all values are either boolean, strings, numbers or lists
  """

  def valid_k(k):
    return isinstance(k, str)

  def valid_v(v):
    types = [list, bool, str, int]
    return any(map(lambda t: isinstance(v, t), types))

  for k, v in m.items():
    if not valid_k(k):
      raise argparse.ArgumentTypeError(
          f"Key '{k}' is invalid! Keys must be strings.")

    if not valid_v(v):
      raise argparse.ArgumentTypeError(f"Value '{v}' is invalid! \
Values must be strings, lists, ints or bools.")

  return m


def validate_experiment_config(items: ExpConf) -> ExpConf:
  """Check that the input is either a list of valid experiment configs or a valid
  expansion itself. Returns the list/dict or throws an exception if invalid.

  """
  if isinstance(items, list):
    return [validate_experiment_config(item) for item in items]

  elif isinstance(items, dict):
    return validate_expansion(items)

  else:
    raise argparse.ArgumentTypeError(f"The experiment config is invalid! \
The JSON file must contain either a dict or a list.")


def load_experiment_config(s):
  if s.lower() == 'stdin':
    json = commentjson.load(sys.stdin)
  else:
    with open(u.validated_file(s)) as f:
      json = commentjson.load(f)

  return validate_experiment_config(json)


def expand_experiment_config(items: ExpConf) -> List[Experiment]:
  """Expand out the experiment config for job submission to Cloud.

  """
  if isinstance(items, list):
    return list(
        itertools.chain.from_iterable(
            [expand_experiment_config(m) for m in items]))

  return list(u.dict_product(items))


def experiment_to_args(m: Experiment, base: List[str]) -> List[str]:
  """Returns the list of flag keys and values that corresponds to the supplied
  experiment.

  Keys all expand to the full '--key_name' style that typical Python flags are
  represented by.

  All values except for boolean values are inserted as str(v). For boolean
  values, if the value is True, the key is inserted by itself (in the format
  --key_name). If the value is False, the key isn't inserted at all.

  """
  ret = [] + base

  for k, v in m.items():
    opt = f"--{k}"
    if isinstance(v, bool):
      # Append a flag if the boolean flag is true, else do nothing.
      if v:
        ret.append(opt)
    else:
      ret.append(f"--{k}")
      ret.append(str(v))

  return ret
