"""
Utilities for our job runner, for working with configs.
"""

from __future__ import absolute_import, division, print_function

import commentjson
import yaml

from typing import Any, Dict, List

METACONFIG_ARGS = [
    'uses_metaconfig', 'job_name', 'numjobs', 'docker_tag', 'DOCKERFILE',
    'hypertype', 'DOCKERFILEGPU', 'setup_loc', 'module', 'runtime_version',
    'pythonVersion', 'region', 'bucket_id', 'project_id', 'param_id'
]


def load_yaml_config(path):
  """returns the config parsed based on the info in the flags.

  Grabs the config file, written in yaml, slurps it in.
  """
  with open(path) as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

  return config


def load_config(path, mode='yaml'):
  """
  Load a JSON config.

  TODO attempt to load a JSON config as well.
  """
  if mode == 'json':
    return commentjson.loads(path)

  return load_yaml_config(path)


def get_metaconfig(conf):
  """load respective metaconfig unless file has all details. So you can either
  specify your own separate metaconfig, or you can load one by planting a
  string.

  TODO: Add support for actually including a map in the metaconfig field.
  """
  if 'uses_metaconfig' in conf:
    metaconf = load_config(conf['uses_metaconfig'])
  else:
    metaconf = conf
  return metaconf


def get_reserved_args(metaconf):
  """Extracts reserved arguments in the current version of this code.
  """
  reserved_args = METACONFIG_ARGS

  param_ids = metaconf.get('param_id')

  if param_ids is not None:
    if isinstance(param_ids, str):
      param_ids = [param_ids]

    for param_id in param_ids:
      # For each parameter we want to broadcast...

      # Note that there are a bunch of different things that we can note
      # about a param- min, max, num, _list, hyper
      reserved_args += [
          'min' + param_id, 'max' + param_id, 'num' + param_id,
          param_id + '_list', 'hyper' + param_id
      ]

  return reserved_args


def extract_script_args(m: Dict[str, Any]) -> List[str]:
  """Strip off the "--" argument if it was passed in as a separator."""
  script_args = m.get("script_args")
  if script_args is None or script_args == []:
    return script_args

  head, *tail = script_args

  return tail if head == "--" else script_args
