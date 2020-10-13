#!/usr/bin/env python3
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
"""Git commit prerun hook example."""

from __future__ import absolute_import, division, print_function

from typing import Any, Dict, List, NamedTuple, NewType, Optional, Union

from absl import app
from absl import flags
from caliban.hooks.git_commit_hooks import git_commit_prerun_hook

FLAGS = flags.FLAGS
flags.DEFINE_string('container_id', None, 'ID of Docker container to use')

  
def main(argv):
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')

  git_commit_prerun_hook(FLAGS.container_id)

if __name__ == '__main__':
  app.run(main)  