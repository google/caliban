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
Useful shared schemas.
"""
import os
import sys
from contextlib import contextmanager
from typing import Optional

import commentjson

import caliban.util as u
import schema as s


class FatalSchemaError(Exception):
  """Wrapper for an exception that can bubble itself up to the top level of the
program."""

  def __init__(self, message, context):
    self.message = message
    self.context = context
    super().__init__(self.message)


@contextmanager
def error_schema(context: Optional[str] = None):
  """Wrap functions that check schemas in this context manager to throw an
  appropriate error with a nice message.

  """
  prefix = ""
  if context is not None:
    prefix = f"\nValidation error while parsing {context}:\n"

  try:
    yield
  except s.SchemaError as e:
    raise FatalSchemaError(e.code, prefix)


@contextmanager
def fatal_errors():
  """Context manager meant to wrap an entire program and present schema errors in
  an easy-to-read way.

  """
  try:
    yield
  except FatalSchemaError as e:
    u.err(f"{e.context}\n{e.message}\n\n")
    sys.exit(1)
  except s.SchemaError as e:
    u.err(f"\n{e.code}\n\n")
    sys.exit(1)


def load_json(path):
  with open(path) as f:
    return commentjson.load(f)


# TODO Once a release with this patch happens:
# https://github.com/keleshev/schema/pull/238,, Change `Or` to `Schema`. This
# problem only occurs for callable validators.

Directory = s.Or(
    os.path.isdir,
    False,
    error="""Directory '{}' doesn't exist in this directory. Check yourself!""")

File = s.Or(lambda path: os.path.isfile(os.path.expanduser(path)),
            False,
            error="""File '{}' isn't a valid file on your system. Try again!""")

Json = s.And(
    File,
    s.Use(load_json,
          error="""File '{}' doesn't seem to contain valid JSON. Try again!"""))
