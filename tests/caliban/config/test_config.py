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

import os
from argparse import ArgumentTypeError

import caliban.cloud.types as ct
import caliban.config as c
import pytest


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
