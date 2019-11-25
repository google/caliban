"""
Utilities for our job runner, for working with configs.
"""

from __future__ import absolute_import, division, print_function

import argparse
import os
import sys
from typing import Any, Dict, List

import commentjson
import yaml

from caliban import cloud


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


def extract_region(m: Dict[str, Any]) -> cloud.Region:
  """Returns the region specified in the args; defaults to an environment
  variable. If that's not supplied defaults to the default cloud provider from
  caliban.cloud.

  """
  return m.get("region") or \
    cloud.parse_region(os.environ.get("REGION")) or \
    cloud.DEFAULT_REGION


def validate_experiment_config(m: Dict[str, Any]) -> Dict[str, Any]:
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
