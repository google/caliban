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

import io

from tqdm.utils import _term_move_up

import caliban.util.tqdm as ut


def test_carriage_return():

  def through(xs):
    buf = io.StringIO()
    f = ut.TqdmFile(file=buf)

    for x in xs:
      f.write(x)
      f.flush()

    return buf.getvalue()

  # Strings pass through tqdmfile with no newline attached.
  assert through(["Yo!"]) == "Yo!"

  # Empty lines do nothing.
  assert through(["", "", ""]) == ""

  # A carriage return is converted to a newline, but the next line, if it's
  # written, will have the proper prefix to trigger a carriage return.
  assert through(["Yo!\r"]) == "Yo!\n"

  # Boom, triggered.
  assert through(["Yo!\r", "continue"]) == f"Yo!\n{_term_move_up()}\rcontinue"
