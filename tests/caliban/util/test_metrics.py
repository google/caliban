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

import caliban.util as u
import caliban.util.metrics as um


def test_cloud_sql_proxy_path():
  """Check that the proxy resource exists and wasn't deleted or renamed."""
  assert um.cloud_sql_proxy_path() is not None

  # check that the name matches the global variable.
  expected = os.path.join(u.resource(""), um.CLOUD_SQL_WRAPPER_SCRIPT)
  assert um.cloud_sql_proxy_path() == expected


def test_launcher_path():
  """Check that the launcher resource exists and wasn't deleted or renamed."""
  assert um.launcher_path() is not None

  # check that the name matches the global variable.
  expected = os.path.join(u.resource(""), um.LAUNCHER_SCRIPT)
  assert um.launcher_path() == expected
