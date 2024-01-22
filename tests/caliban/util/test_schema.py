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

import tempfile

import schema as s

import caliban.util.schema as us
import pytest


def test_directory(tmpdir):
  # Proper directories pass validation.
  assert us.Directory.validate(tmpdir) == tmpdir

  # random dirs that I made up dont!
  with pytest.raises(s.SchemaError) as e:
    assert us.Directory.validate('random')

  # Check that the formatting string works.
  assert e.match("Directory 'random' doesn't exist")


def test_file():
  with tempfile.NamedTemporaryFile() as tmp:
    # Existing files pass validation.
    assert us.File.validate(tmp.name) == tmp.name

  # random paths that I made up dont!
  with pytest.raises(s.SchemaError) as e:
    assert us.File.validate('random')

  # Check that the formatting string works.
  assert e.match("File 'random' isn't")
