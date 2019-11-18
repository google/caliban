"""
Utilities for our job runner, for working with configs.
"""

from __future__ import absolute_import, division, print_function

from typing import Any, Dict, List

import commentjson
import yaml


def load_yaml_config(path):
  """returns the config parsed based on the info in the flags.

  Grabs the config file, written in yaml, slurps it in.
  """
  with open(path) as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

  return config


def load_config(path, mode='yaml'):
  """Load a JSON config.

  TODO attempt to load a JSON config as well. This will be useful once we start
  using the experiment config.

  """
  if mode == 'json':
    return commentjson.loads(path)

  return load_yaml_config(path)


def extract_script_args(m: Dict[str, Any]) -> List[str]:
  """Strip off the "--" argument if it was passed in as a separator."""
  script_args = m.get("script_args")
  if script_args is None or script_args == []:
    return script_args

  head, *tail = script_args

  return tail if head == "--" else script_args
