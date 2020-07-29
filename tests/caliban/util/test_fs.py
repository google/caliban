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
import json
import os

import caliban.util.fs as ufs


def test_module_to_path():
  """verify that we can go the other way and turn modules back into expected
  relative paths.

  """
  m = {
      # normal modules get nesting.
      "face.cake": "face/cake.py",

      # root-level modules just get a py extension.
      "face": "face.py",

      # This will get treated as a module nested inside of a folder, which is
      # clearly invalid; marking this behavior in the tests.
      "face/cake.py": "face/cake/py.py"
  }
  for k in m:
    assert ufs.module_to_path(k) == m[k]


def test_generate_package():
  """validate that the generate_package function can handle all sorts of inputs
  and generate valid Package objects.

  """
  m = {
      # normal module syntax should just work.
      "caliban.cli":
          ufs.module_package("caliban.cli"),

      # This one is controversial, maybe... if something exists as a module
      # if you replace slashes with dots, THEN it will also parse as a
      # module. If it exists as a file in its own right this won't happen.
      #
      # TODO get a test in for this final claim using temp directories.
      "caliban/cli":
          ufs.module_package("caliban.cli"),

      # root scripts or packages should require the entire local directory.
      "setup":
          ufs.module_package("setup"),
      "cake.py":
          ufs.script_package("cake.py", "python"),

      # This is busted but should still parse.
      "face.cake.py":
          ufs.script_package("face.cake.py", "python"),

      # Paths into directories should parse properly into modules and include
      # the root as their required package to import.
      "face/cake.py":
          ufs.script_package("face/cake.py", "python"),

      # Deeper nesting works.
      "face/cake/cheese.py":
          ufs.script_package("face/cake/cheese.py", "python"),

      # Other executables work.
      "face/cake/cheese.sh":
          ufs.script_package("face/cake/cheese.sh"),
  }
  for k in m:
    assert ufs.generate_package(k) == m[k]


def test_tmp_copy(tmpdir):
  # from and to exist.
  from_a_path = str(tmpdir.join('from_a.json'))
  to_a_path = str(tmpdir.join('to_a.json'))

  # to doesn't exist; test that this still works.
  from_b_path = str(tmpdir.join('from_b.json'))
  to_b_path = None

  # this should be ignored!
  from_c_path = None
  to_c_path = str(tmpdir.join('to_c.json'))

  # same here.
  from_d_path = None
  to_d_path = None

  # prepare valid data in the a and b sources.
  a_data = {"apt_packages": ["face"]}

  with open(from_a_path, 'w') as f:
    json.dump(a_data, f)

  b_data = {"key": ["value"]}

  with open(from_b_path, 'w') as f:
    json.dump(b_data, f)

  # note that a duplicate None key is fine.
  tmpcopy = ufs.TempCopy({
      from_a_path: to_a_path,
      from_b_path: to_b_path,
      from_c_path: to_c_path,
      from_d_path: to_d_path
  })
  assert not tmpcopy.active

  frozen_m = None
  with tmpcopy as m:

    # save the m for later inspection.
    frozen_m = m

    # inside the context manager, tmpcopy is active.
    assert tmpcopy.active

    # check that all keys work as expected.
    assert m[from_a_path] == to_a_path
    assert m[from_b_path] is not None
    assert from_c_path not in m
    assert from_d_path not in m

    # data exists in the location we specified:
    with open(to_a_path, 'r') as a_file:
      assert a_data == json.load(a_file)

    # the reference is correct too, inside the map:
    with open(m[from_a_path], 'r') as a_file:
      assert a_data == json.load(a_file)

    # We provided None for to_b_path, but the data still makes it into the
    # correct location.
    with open(m[from_b_path], 'r') as b_file:
      assert b_data == json.load(b_file)

  # Outside the manager, no longer active.
  assert not tmpcopy.active

  # files are now deleted:
  assert not os.path.exists(m[from_a_path])
  assert not os.path.exists(m[from_b_path])


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
