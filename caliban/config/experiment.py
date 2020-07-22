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
"""Utilities for working with experiment.json files.

"""

from __future__ import absolute_import, division, print_function

import argparse
import itertools
import re
import sys
from collections import ChainMap
from typing import Any, Dict, List, Optional, Tuple, Union

import commentjson

import caliban.util as u
import caliban.util.argparse as ua
import caliban.util.schema as us

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


def _is_compound_key(s: Any) -> bool:
  """ compound key is defined as a string which uses square brackets to enclose
  a comma-separated list, e.g. "[batch_size,learning_rate]" or "[a,b,c]"
  """

  if type(s) is not str or len(s) <= 2:
    return False
  else:
    return s[0] == '[' and s[-1] == ']'


def _tupleize_compound_key(k: str) -> List[str]:
  """ converts a JSON-input compound key into a tuple """
  assert _is_compound_key(k), "{} must be a valid compound key".format(k)
  return tuple([x.strip() for x in k.strip('][').split(',')])


def _tupleize_compound_value(
    v: Union[List, bool, str, int, float]) -> Union[List, Tuple]:
  """ list of lists -> list of tuples
      list of primitives -> tuple of primitives
      single primitive -> length-1 tuple of that primitive

  E.g., [[0,1],[3,4]] -> [(0,1),(3,4)]
        [0,1] -> (0,1)
        0 -> (0, )
  """
  if isinstance(v, list):
    if isinstance(v[0], list):
      # v is list of lists
      return [tuple(vi) for vi in v]
    else:
      # v is list of primitives
      return tuple(v)
  else:
    # v is a single primitive (bool, str, int, float)
    return tuple([v])


def _tupleize_compound_item(k: Union[Tuple, str], v: Any) -> Dict:
  """ converts a JSON-input compound key/value pair into a dictionary of tuples """
  if _is_compound_key(k):
    return {_tupleize_compound_key(k): _tupleize_compound_value(v)}
  else:
    return {k: v}


def tupleize_dict(m: Dict) -> Dict:
  """ given a dictionary with compound keys, converts those keys to tuples, and
  converts the corresponding values to a tuple or list of tuples

  Compound key: a string which uses square brackets to enclose
  a comma-separated list, e.g. "[batch_size,learning_rate]" or "[a,b,c]"
  """

  formatted_items = [_tupleize_compound_item(k, v) for k, v in m.items()]
  return dict(ChainMap(*formatted_items))


def _expand_compound_pair(k: Union[Tuple, str], v: Any) -> Dict:
  """ given a key-value pair k v, where k is either:
      a) a primitive representing a single, e.g. k = 'key', v = 'value', or
      b) a tuple of primitives representing multiple keys, e.g. k = ('key1','key2'), v = ('value1', 'value2')
      this function returns the corresponding dictionary without compound keys
  """

  if isinstance(k, tuple):
    if not isinstance(v, tuple):
      raise argparse.ArgumentTypeError(
          """function _expand_compound_pair(k, v) requires that if type(k) is tuple,
             type(v) must also be tuple.""")
    else:
      return dict(zip(k, v))
  else:
    return {k: v}


def expand_compound_dict(m: Union[Dict, List]) -> Union[Dict, List]:
  """ given a dictionary with some compound keys, aka tuples,
  returns a dictionary which each compound key separated into primitives

  given a list of such dictionaries, will apply the transformation
  described above to each dictionary and return the list, maintaining
  structure
  """

  if isinstance(m, list):
    return [expand_compound_dict(mi) for mi in m]
  else:
    expanded_dicts = [_expand_compound_pair(k, v) for k, v in m.items()]
    return dict(ChainMap(*expanded_dicts))


def expand_experiment_config(items: ExpConf) -> List[Experiment]:
  """Expand out the experiment config for job submission to Cloud.

  """
  if isinstance(items, list):
    return list(
        itertools.chain.from_iterable(
            [expand_experiment_config(m) for m in items]))

  tupleized_items = tupleize_dict(items)
  return [expand_compound_dict(d) for d in u.dict_product(tupleized_items)]


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
  if isinstance(s, str) and s.lower() == 'stdin':
    json = commentjson.load(sys.stdin)
  else:
    json = ua.argparse_schema(us.Json)(s)

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
