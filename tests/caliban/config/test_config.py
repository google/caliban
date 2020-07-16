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

import hypothesis.strategies as st
from hypothesis import given

import caliban.config as c
import caliban.platform.cloud.types as ct
import caliban.util.schema as us
import pytest


def test_parse_job_mode():
  assert c.JobMode.parse('CpU') == c.JobMode.CPU
  assert c.JobMode.parse('cpu') == c.JobMode.CPU
  assert c.JobMode.parse('cpU  ') == c.JobMode.CPU

  assert c.JobMode.parse('  GpU') == c.JobMode.GPU
  assert c.JobMode.parse('gpu') == c.JobMode.GPU
  assert c.JobMode.parse('GPU') == c.JobMode.GPU

  with pytest.raises(Exception):
    c.JobMode.parse('random')


@given(st.text() | st.sampled_from(sorted(c.DLVM_CONFIG.keys())))
def test_expand_image(s):
  """Expanded images either exist in the DLVM_CONFIG, or are round-tripped
  without getting changed.

  """
  if s in c.DLVM_CONFIG:
    assert c.expand_image(s) == c.DLVM_CONFIG[s]
  else:
    assert c.expand_image(s) == s


def test_gpu():
  assert c.gpu(c.JobMode.GPU)
  assert not c.gpu(c.JobMode.CPU)
  assert not c.gpu("face")


def test_extract_script_args():
  # Basic cases. If there are NO script args, or if the default is present,
  # they're passed back out.
  assert c.extract_script_args({}) is None
  assert c.extract_script_args({'script_args': None}) is None
  assert c.extract_script_args({'script_args': []}) == []

  args = ["--carrot", "stick"]

  # If a '--' is passed in at the head it's stripped off and ignored.
  assert c.extract_script_args({"script_args": ["--"] + args}) == args
  assert c.extract_script_args({"script_args": args}) == args


def test_extract_project_id(monkeypatch):
  if os.environ.get('PROJECT_ID'):
    monkeypatch.delenv('PROJECT_ID')

  # if NO project ID is specified on the environment OR in the supplied config,
  # the system attempts to exit.
  with pytest.raises(SystemExit) as wrapped_e:
    c.extract_project_id({})

  assert wrapped_e.type == SystemExit
  assert wrapped_e.value.code == 1

  # the project ID gets mirrored back if it exists in the config.
  assert c.extract_project_id({'project_id': "face"}) == "face"

  monkeypatch.setenv('PROJECT_ID', "env_id")

  # If the env variable is set it's returned:
  assert c.extract_project_id({'project_id': None}) == "env_id"

  # Unless the project ID's set in the config.
  assert c.extract_project_id({'project_id': "face"}) == "face"


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


def test_extract_cloud_key(monkeypatch):
  k = 'GOOGLE_APPLICATION_CREDENTIALS'
  if os.environ.get(k):
    monkeypatch.delenv(k)

  # initial missing case.
  assert c.extract_cloud_key({}) == None

  monkeypatch.setenv(k, "key.json")

  # env override:
  assert c.extract_cloud_key({}) == "key.json"

  # conf takes precedence.
  assert c.extract_cloud_key({"cloud_key": "mynewkey.json"}) == "mynewkey.json"


def test_base_image():
  # If NO base image is specified, None is returned.
  assert c.base_image({}, c.JobMode.CPU) == None
  assert c.base_image({}, c.JobMode.GPU) == None

  dlvm = c.CalibanConfig.validate({"base_image": "dlvm:pytorch-{}-1.4"})

  # If you leave a {} format block, base_image will splice in the job mode.
  assert c.base_image(dlvm,
                      c.JobMode.CPU) == c.DLVM_CONFIG["dlvm:pytorch-cpu-1.4"]
  assert c.base_image(dlvm,
                      c.JobMode.GPU) == c.DLVM_CONFIG["dlvm:pytorch-gpu-1.4"]

  conf = c.CalibanConfig.validate(
      {"base_image": {
          "cpu": "dlvm:tf2-{}-2.1",
          "gpu": "random:latest"
      }})

  # Same trick works even nested in dicts. If the image is NOT a specially
  # keyed DLVM, it's untouched.
  assert c.base_image(conf, c.JobMode.CPU) == c.DLVM_CONFIG["dlvm:tf2-cpu-2.1"]
  assert c.base_image(conf, c.JobMode.GPU) == "random:latest"


def test_caliban_config(tmpdir):
  """Tests validation of the CalibanConfig schema and the method that returns the
  parsed config.

  """
  valid = {"apt_packages": {"cpu": ["face"]}}
  valid_path = tmpdir.join('valid.json')

  with open(valid_path, 'w') as f:
    json.dump(valid, f)

  valid_shared = {"apt_packages": ["face"]}
  valid_shared_path = tmpdir.join('valid_shared.json')

  with open(valid_shared_path, 'w') as f:
    json.dump(valid_shared, f)

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

  # If the user supplies a list instead of a dict, all still works well.
  valid_shared_conf = c.caliban_config(valid_shared_path)
  cpu = c.apt_packages(valid_shared_conf, c.JobMode.CPU)
  gpu = c.apt_packages(valid_shared_conf, c.JobMode.GPU)

  assert cpu == gpu
  assert cpu == ["face"]
