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
"""
Utilities relevant to AI Platform.
"""
import re
from typing import Dict, List, Optional, Tuple, Union

import caliban.util as u
import caliban.util.argparse as ua

# key and value for labels can be at most this-many-characters long.
AI_PLATFORM_MAX_LABEL_LENGTH = 63


def _truncate(s: str, max_length: int) -> str:
  """Returns the input string s truncated to be at most max_length characters
  long.

  """
  return s if len(s) <= max_length else s[0:max_length]


def _clean_label(s: Optional[str], is_key: bool) -> str:
  """Processes the string into the sanitized format required by AI platform
  labels.

  https://cloud.google.com/ml-engine/docs/resource-labels

  """
  if s is None:
    return ""

  # periods are not allowed by AI Platform labels, but often occur in,
  # e.g., learning rates
  DECIMAL_REPLACEMENT = '_'
  s = s.replace('.', DECIMAL_REPLACEMENT)

  # lowercase, letters, - and _ are valid, so strip the leading dashes, make
  # everything lowercase and then kill any remaining unallowed characters.
  cleaned = re.sub(r'[^a-z0-9_-]', '', s.lower()).lstrip("-")

  # Keys must start with a letter. If is_key is set and the cleaned version
  # starts with something else, append `k`.
  if is_key and cleaned != "" and not cleaned[0].isalpha():
    cleaned = "k" + cleaned

  return _truncate(cleaned, AI_PLATFORM_MAX_LABEL_LENGTH)


def key_label(k: Optional[str]) -> str:
  """converts the argument into a valid label, suitable for submission as a label
  key to Cloud.

  """
  return _clean_label(k, True)


def value_label(v: Optional[str]) -> str:
  """converts the argument into a valid label, suitable for submission as a label
  value to Cloud.

  """
  return _clean_label(v, False)


def script_args_to_labels(script_args: Optional[List[str]]) -> Dict[str, str]:
  """Converts the arguments supplied to our scripts into a dictionary usable as
  labels valid for Cloud submission.

  """
  ret = {}

  def process_pair(k, v):
    if ua.is_key(k):
      clean_k = key_label(k)
      if clean_k != "":
        ret[clean_k] = "" if ua.is_key(v) else value_label(v)

  if script_args is None or len(script_args) == 0:
    return ret

  elif len(script_args) == 1:
    process_pair(script_args[0], None)

  # Handle the case where the final argument in the list is a boolean flag.
  # This won't get picked up by partition.
  elif len(script_args) > 1:
    for k, v in u.partition(script_args, 2):
      process_pair(k, v)

    process_pair(script_args[-1], None)

  return ret


def sanitize_labels(
    pairs: Union[Dict[str, str], List[Tuple[str, str]]]) -> Dict[str, str]:
  """Turns a dict, or a list of unsanitized key-value pairs (each represented by
  a tuple) into a dictionary suitable to submit to Cloud as a label dict.

  """
  if isinstance(pairs, dict):
    return sanitize_labels(pairs.items())

  return {key_label(k): value_label(v) for (k, v) in pairs if key_label(k)}
