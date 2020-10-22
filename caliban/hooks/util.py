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

import importlib
from absl import logging
import json
import sys

import caliban.util.fs as ufs

def perform_prebuild_hooks(caliban_config: Dict[str, Any]) -> Dict[str, str]:
  """ Performs pre-build hooks (specified in the caliban_config) and:
    1) If these run without error, accumulates their outputs into a
       combined dictionary and returns it
    2) If one of them errors, immediately stops and throws an Exception
       displaying the error message for the user.

  Prebuild hooks are python functions, which
    1) Take no arguments, and
    2) Output a dictionary with 'Succeeded' bool indicating success, and
       a. 'Error' str in the case of failure
       b. 'Data' Dict[str, str] in the case of success
    3) Live in the 'hooks' module in the project's root directory
  """
  import sys
  sys.path.append('.')
  all_hooks = importlib.import_module('hooks')
  sys.path.remove('.')

  all_outputs = {}

  for hook_name in caliban_config.get('pre_build_hooks', []):
    hook = getattr(all_hooks, f'hook_{hook_name}')
    logging.info(f'Running pre-build hook {hook_name}')
    output = hook()

    if not output['Succeeded']:
      # Hook errored. Stop the build and inform the user
      raise Exception(f'Pre-build hook {hook_name} errored with the following message:\n           {output["Error"]}')
    else:
      all_outputs.update(output['Data'])

  logging.debug(f"Prebuild hook outputs: {all_outputs}")

  return all_outputs

def perform_prerun_hooks(caliban_config: Dict[str, Any], container_id: str) -> Dict[str, str]:
  """ Performs pre-run hooks (specified in the caliban_config) and:
    1) If these run without error, accumulates their outputs into a
       combined dictionary and returns it
    2) If one of them errors, immediately stops and throws an Exception
       displaying the error message for the user.

  Prerun hooks are python functions, which
    1) Take a single str argument, the cotainer_id of the container
       which the run will use, and
    2) Output a dictionary with 'Succeeded' bool indicating success, and
       a. 'Error' str in the case of failure
       b. 'Data' Dict[str, str] in the case of success
    3) Live in the 'hooks' module in the project's root directory
  """
  import sys
  sys.path.append('.')
  all_hooks = importlib.import_module('hooks')
  sys.path.remove('.')

  all_outputs = {}

  for hook_name in caliban_config.get('pre_run_hooks', []):
    hook = getattr(all_hooks, f'hook_{hook_name}')
    logging.info(f'Running pre-run hook {hook_name}')
    output = hook(container_id)

    if not output['Succeeded']:
      # Hook errored. Stop the run and inform the user
      raise Exception(f'Pre-run hook {hook_name} errored with the following message:\n           {output["Error"]}')
    else:
      all_outputs.update(output['Data'])

  logging.debug(f"Prerun hook outputs: {all_outputs}")

  return all_outputs
