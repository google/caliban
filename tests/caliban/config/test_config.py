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

import json
import os
from argparse import ArgumentTypeError

import caliban.config as c
import caliban.platform.cloud.types as ct
import caliban.util.schema as us
import pytest


def test_gpu():
  assert c.gpu(c.JobMode.GPU)
  assert not c.gpu(c.JobMode.CPU)
  assert not c.gpu("face")


def test_extract_region(monkeypatch):
  if os.environ.get('REGION'):
    monkeypatch.delenv('REGION')

  assert c.extract_region({}) == c.DEFAULT_REGION

  # You have to provide a valid region.
  with pytest.raises(ArgumentTypeError):
    c.extract_region({"region": "face"})

  # Same goes for the environment variable setting approach.
  monkeypatch.setenv('REGION', "face")
  with pytest.raises(ArgumentTypeError):
    c.extract_region({})

  # an empty string is fine, and ignored.
  monkeypatch.setenv('REGION', "")
  assert c.extract_region({}) == c.DEFAULT_REGION

  assert c.extract_region({"region": "us-west1"}) == ct.US.west1


def test_caliban_config(tmpdir):
  """Tests validation of the CalibanConfig schema and the method that returns the
  parsed config.

  """
  valid = {"apt_packages": {"cpu": ["face"]}, "random": "entry"}
  valid_path = tmpdir.join('valid.json')

  with open(valid_path, 'w') as f:
    json.dump(valid, f)

  invalid = {"apt_packages": "face"}
  invalid_path = tmpdir.join('invalid.json')

  with open(invalid_path, 'w') as f:
    json.dump(invalid, f)

  # Failing the schema raises an error.
  with pytest.raises(us.FatalSchemaError):
    c.caliban_config(invalid_path)

  # paths that don't exist return an empty map:
  assert c.caliban_config('random_path') == {}

  # If the config is valid, c.apt_packages can fetch the packages we specified.
  config = c.caliban_config(valid_path)
  assert c.apt_packages(config, c.JobMode.GPU) == []
  assert c.apt_packages(config, c.JobMode.CPU) == ["face"]
