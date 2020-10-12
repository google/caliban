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

import subprocess
from absl import logging
import json

import caliban.util.fs as ufs

def perform_prebuild_hooks(caliban_config: Dict[str, Any]) -> Dict:

  hook_outputs = {}
  for single_hook in caliban_config.get('pre-build-hooks', []):
    hook_outputs.update(perform_single_prebuild_hook(single_hook))

  logging.info(f"Hook outputs: {hook_outputs}")

  return hook_outputs

def perform_single_prebuild_hook(script_file: str) -> Dict:

  try:
    stdout = subprocess.run(script_file, check=True, capture_output=True).stdout.decode('utf-8')
  except subprocess.CalledProcessError as e:
    logging.info(e.stdout)
    raise subprocess.CalledProcessError(returncode=e.returncode, cmd=e.cmd, stderr=e.stderr)

  logging.info("Loading output dict")
  logging.info(f"Stdout: {stdout}")
  if stdout == '':
    output_dict = {}
  else:
    output_dict = json.loads(stdout)
  logging.info(output_dict)
  return output_dict

def perform_prerun_hooks(caliban_config: Dict[str, Any], container_id: str) -> Dict:
  """ performs pre-run hooks and returns the resulting outputs (tags) """
  hook_outputs = {}
  for single_hook in caliban_config.get('pre-run-hooks', []):
    hook_outputs.update(perform_single_prerun_hook(single_hook, container_id))

  logging.info(f"Hook outputs: {hook_outputs}")

  return hook_outputs

def perform_single_prerun_hook(script_file: str, container_id: str) -> Dict:
  print(f"About to perform hook {script_file}")

  try:
    stdout = subprocess.run([script_file, '--container_id', container_id], check=True, capture_output=True).stdout.decode('utf-8')
  except subprocess.CalledProcessError as e:
    logging.info(e.stdout)
    raise subprocess.CalledProcessError(returncode=e.returncode, cmd=e.cmd, stderr=e.stderr)

  logging.info("Loading output dict")
  logging.info(f"Stdout: {stdout}")
  if stdout == '':
    output_dict = {}
  else:
    output_dict = json.loads(stdout)
  logging.info(output_dict)
  return output_dict

