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

import caliban.util.fs as ufs


def test_capture_stdout():
  buf = io.StringIO()
  ret_string, code = ufs.capture_stdout(["echo", "hello!"], file=buf)
  assert code == 0

  # Verify that the stdout is reported to the supplied file, and that it's
  # captured by the function and returned correctly.
  assert ret_string == "hello!\n"
  assert buf.getvalue() == ret_string


def test_capture_stdout_input():
  ret_string, code = ufs.capture_stdout(["cat"], input_str="hello!")
  assert code == 0
  assert ret_string.rstrip() == "hello!"
