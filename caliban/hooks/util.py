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
"""Functions to execute hooks
"""

from __future__ import absolute_import, division, print_function

from typing import Any, Dict, List, NamedTuple, NewType, Optional, Union

from absl import logging

import caliban.config as c
import caliban.util as u
import caliban.util.fs as ufs
import caliban.util.metrics as um

def perform_prebuild_hooks(caliban_config: Dict[str, Any]) -> None:
  if caliban_config.get("pre-build-hook", None) is not None:
    pre_build_hook = caliban_config['pre-build-hook']
    _, ret_code = ufs.capture_stdout(pre_build_hook, None)

    if ret_code != 0:
      raise Exception(f"Pre-build hook returned non-zero exit code {ret_code}")

