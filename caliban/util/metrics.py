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
"""Caliban has built-in (alpha) support for configuring containers for easy
metrics tracking via MLFlow. This module provides functions useful for
configuring a container for this behavior.

"""

import caliban.util as u

CLOUD_SQL_WRAPPER_SCRIPT = 'cloud_sql_proxy.py'


def cloud_sql_proxy_path() -> str:
  """Returns an absolute path to the cloud_sql_proxy python wrapper that we
  inject into containers.

  """
  return u.resource(CLOUD_SQL_WRAPPER_SCRIPT)
