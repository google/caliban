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

import argparse
import builtins
from google.auth import credentials
import json
import os
import pytest
import tempfile
from typing import Any

from caliban.resources import caliban_launcher


@pytest.mark.parametrize('obj', [['a', 2, 3], {'a': 1, 'b': 2}])
def test_parse_json(obj: Any):
  # valid json, type
  j = caliban_launcher._parse_json('foo', json.dumps(obj), type(obj))
  assert j == obj

  # valid json, invalid type
  with pytest.raises(argparse.ArgumentTypeError):
    j = caliban_launcher._parse_json('bar', json.dumps(None), int)

  # invalid json
  with pytest.raises(argparse.ArgumentTypeError):
    j = caliban_launcher._parse_json('baz', '[', int)


def test_start_services():
  with tempfile.TemporaryDirectory() as tmpdir:
    outfile = os.path.join(tmpdir, 'bar')
    svc = [['bash', '-c', 'touch $FOO']]
    env = {'FOO': outfile}
    caliban_launcher._start_services(svc, env, delay=1)

    assert os.path.exists(outfile)


def test_execute_command():
  with tempfile.TemporaryDirectory() as tmpdir:
    outfile = os.path.join(tmpdir, 'bar')
    cmd = ['bash', '-c']
    args = ['touch $FOO']
    env = {'FOO': outfile}
    caliban_launcher._execute_command(cmd, args, env)

    assert os.path.exists(outfile)


def test_load_config_file(monkeypatch):
  monkeypatch.setattr(os.path, 'exists', lambda x: False)
  assert caliban_launcher._load_config_file() == {}

  cfg = {'foo': 7}

  class MockFile():

    def __enter__(self):
      pass

    def __exit__(self, a, b, c):
      pass

  monkeypatch.setattr(os.path, 'exists', lambda x: True)
  monkeypatch.setattr(builtins, 'open', lambda x: MockFile())
  monkeypatch.setattr(json, 'load', lambda x: cfg)
  assert caliban_launcher._load_config_file() == cfg


def test_get_config(monkeypatch):
  cfg = {'foo': 3, 'env': {'a': 0}, 'services': ['ls']}

  class MockArgs():

    def __init__(self):
      self.caliban_config = cfg

  class MockFile():

    def __enter__(self):
      pass

    def __exit__(self, a, b, c):
      pass

  monkeypatch.setattr(os.path, 'exists', lambda x: True)
  monkeypatch.setattr(builtins, 'open', lambda x: MockFile())
  monkeypatch.setattr(json, 'load', lambda x: {'env': {}, 'services': []})
  assert caliban_launcher._get_config(MockArgs()) == cfg


def test_ensure_non_null_project(monkeypatch):

  # test case where GOOGLE_CLOUD_PROJECT is already set
  env = {'foo': 'bar', 'GOOGLE_CLOUD_PROJECT': 'project'}

  new_env = caliban_launcher._ensure_non_null_project(env)
  assert env == new_env

  # GOOGLE_CLOUD_PROJECT not set, but valid project from default()
  def mock_default(scopes=None, request=None, quota_project_id=None):
    return (credentials.AnonymousCredentials(), 'foo')

  monkeypatch.setattr('google.auth.default', mock_default)
  env = {'foo': 'bar'}
  assert caliban_launcher._ensure_non_null_project(env) == env

  # GOOGLE_CLOUD_PROJECT not set, no valid project from default()
  def mock_default(scopes=None, request=None, quota_project_id=None):
    return (credentials.AnonymousCredentials(), None)

  monkeypatch.setattr('google.auth.default', mock_default)
  env = {'foo': 'bar'}
  new_env = caliban_launcher._ensure_non_null_project(env)
  for k, v in env.items():
    assert new_env.get(k) == v

  assert new_env.get('GOOGLE_CLOUD_PROJECT') is not None
