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
Utilities for our job runner.
"""
import argparse
import itertools as it
import os
from typing import Dict, List, Optional, Tuple

from blessings import Terminal

import caliban.util as u
import caliban.util.fs as ufs
import schema as s

t = Terminal()


def expand_args(items: Dict[str, str]) -> List[str]:
  """Converts the input map into a sequence of k, v pair strings. A None value is
  interpreted to mean that the key is a solo flag; it's evicted from the
  output.

  """
  pairs = [[k, v] if v is not None else [k] for k, v in items.items()]
  return list(it.chain.from_iterable(pairs))


def argparse_schema(schema):
  """Wrapper that performs validation and converts SchemaErrors into
  ArgumentTypeErrors for better argument error reporting.

  """

  def check(x):
    try:
      return schema.validate(x)
    except s.SchemaError as e:
      raise argparse.ArgumentTypeError(e.code) from None

  return check


# TODO: Now that we use schema, validated_package and parse_kv_pair should be
# converted to schema instances.


def validated_package(path: str) -> u.Package:
  """similar to generate_package but runs argparse validation on packages that
  don't actually exist in the filesystem.

  """
  p = ufs.generate_package(path)

  if not os.path.isdir(p.package_path):
    raise argparse.ArgumentTypeError(
        """Directory '{}' doesn't exist in directory. Code must be
nested in a folder that exists in the current directory.""".format(
            p.package_path))

  filename = p.script_path
  if not ufs.file_exists_in_cwd(filename):
    raise argparse.ArgumentTypeError(
        """File '{}' doesn't exist locally as a script or python module; code
must live inside the current directory.""".format(filename))

  return p


def parse_kv_pair(s: str) -> Tuple[str, str]:
  """
    Parse a key, value pair, separated by '='

    On the command line (argparse) a declaration will typically look like:
        foo=hello
    or
        foo="hello world"
    """
  items = s.split('=')
  k = items[0].strip()  # Remove whitespace around keys

  if len(items) <= 1:
    raise argparse.ArgumentTypeError(
        "Couldn't parse label '{}' into k=v format.".format(s))

  v = '='.join(items[1:])
  return (k, v)


def is_key(k: Optional[str]) -> bool:
  """Returns True if the argument is a valid argparse optional arg input, False
  otherwise.

  Strings that start with - or -- are considered valid for now.

  """
  return k is not None and len(k) > 0 and k[0] == "-"
