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
Progress bar utilities.
"""

import contextlib
import sys

from absl import logging
from blessings import Terminal

import tqdm
from tqdm.utils import _term_move_up

t = Terminal()


class TqdmFile(object):
  """Dummy file-like that will write to tqdm"""
  file = None
  prefix = _term_move_up() + '\r'

  def __init__(self, file):
    self.file = file
    self._carriage_pending = False

  def write(self, line):
    if self._carriage_pending:
      line = self.prefix + line
      self._carriage_pending = False

    if line.endswith('\r'):
      self._carriage_pending = True
      line = line[:-1] + '\n'

    tqdm.tqdm.write(line, file=self.file, end='')

  def flush(self):
    return getattr(self.file, "flush", lambda: None)()

  def isatty(self):
    return getattr(self.file, "isatty", lambda: False)()

  def close(self):
    return getattr(self.file, "close", lambda: None)()


def config_logging():
  """Overrides logging to go through TQDM.

  TODO use this call to kill then restore:
  https://github.com/tqdm/tqdm#redirecting-writing

  """
  h = logging.get_absl_handler()
  old = h.python_handler
  h._python_handler = logging.PythonHandler(stream=TqdmFile(sys.stderr))
  logging.use_python_logging()


@contextlib.contextmanager
def tqdm_logging():
  """Overrides logging to go through TQDM.

  https://github.com/tqdm/tqdm#redirecting-writing

  """
  handler = logging.get_absl_handler()
  orig = handler.python_handler

  try:
    handler._python_handler = logging.PythonHandler(stream=TqdmFile(sys.stderr))

    # The changes won't take effect if this hasn't been called. Defensively
    # call it again here.
    logging.use_python_logging()
    yield orig.stream
  except Exception as exc:
    raise exc
  finally:
    handler._python_handler = orig
