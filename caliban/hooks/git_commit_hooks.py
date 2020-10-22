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
"""Git commit prerun and prebuild hooks.
"""

from __future__ import absolute_import, division, print_function

from typing import Any, Dict, List, NamedTuple, NewType, Optional, Union

import sys
from absl import logging
import docker
from git import Repo

def get_hash_from_image(container_id: str) -> str:
  """Load git hash from docker image label."""
  client = docker.from_env()
  labels = client.images.get(container_id).labels
  try:
    return labels['commit']
  except KeyError as e:
    logging.error(f'Docker image {container_id} does not contain a git commit label.')
    raise e

def git_commit_prebuild_hook() -> None:
  """Git commit hash prebuild hook."""
  logging.info('Running git-cleanliness prebuild hook.')

  repo = Repo('.') # TODO deal with this

  # check repo is clean
  if len(repo.untracked_files) != 0 or repo.is_dirty():
    logging.error('Git cleanliness hook found repo not up-to-date!')
    logging.error('Either you have untracked files, or changes \n ...
                  staged for commit but not committed.')
    sys.exit(1)

  # get commit hash
  commit_hash = repo.commit().hexsha
  print('{"commit": "%s"}' % commit_hash)

def git_commit_prerun_hook(container_id) -> None:
  """Git commit hash prerun hook."""
  commit_hash = get_hash_from_image(container_id)
  print('{"commit": "%s"}' % commit_hash)  

  
