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
"""Functions required to interact with Docker to build and run images, shells
and notebooks in a Docker environment.

"""

import os
from pathlib import Path
from typing import List, Optional

import caliban.config as c
import caliban.docker.build as b
import caliban.platform.run as r


def _home_mount_cmds(enable_home_mount: bool) -> List[str]:
  """Returns the argument needed by Docker to mount a user's local home directory
  into the home directory location inside their container.

  If enable_home_mount is false returns an empty list.

  """
  ret = []
  if enable_home_mount:
    ret = ["-v", "{}:{}".format(Path.home(), b.container_home())]
  return ret


def _interactive_opts(workdir: str) -> List[str]:
  """Returns the basic arguments we want to run a docker process locally.

  """
  return [
      "-w", workdir,
      "-u", "{}:{}".format(os.getuid(), os.getgid()), \
      "-v", "{}:{}".format(os.getcwd(), workdir) \
  ]


def run_interactive(job_mode: c.JobMode,
                    workdir: Optional[str] = None,
                    image_id: Optional[str] = None,
                    run_args: Optional[List[str]] = None,
                    mount_home: Optional[bool] = None,
                    shell: Optional[b.Shell] = None,
                    entrypoint: Optional[str] = None,
                    entrypoint_args: Optional[List[str]] = None,
                    **build_image_kwargs) -> None:
  """Start a live shell in the terminal, with all dependencies installed and the
  current working directory (and optionally the user's home directory) mounted.

  Keyword args:

  - job_mode: c.JobMode.
  - image_id: ID of the image to run. Supplying this will skip an image build.
  - run_args: extra arguments to supply to `docker run`.
  - mount_home: if true, mounts the user's $HOME directory into the container
    to `/home/$USERNAME`. If False, nothing.
  - shell: name of the shell to install into the container. Also configures the
    entrypoint if that's not supplied.
  - entrypoint: command to run. Defaults to the executable command for the
    supplied shell.
  - entrypoint_args: extra arguments to supply to the entrypoint.

  any extra kwargs supplied are passed through to build_image.

  """
  if workdir is None:
    workdir = b.DEFAULT_WORKDIR

  if run_args is None:
    run_args = []

  if entrypoint_args is None:
    entrypoint_args = []

  if mount_home is None:
    mount_home = True

  if shell is None:
    # Only set a default shell if we're also mounting the home volume.
    # Otherwise a custom shell won't have access to the user's profile.
    shell = b.default_shell() if mount_home else b.Shell.bash

  if entrypoint is None:
    entrypoint = b.SHELL_DICT[shell].executable

  interactive_run_args = _interactive_opts(workdir) + [
      "-it", \
      "--entrypoint", entrypoint
  ] + _home_mount_cmds(mount_home) + run_args

  r.run(job_mode=job_mode,
        run_args=interactive_run_args,
        script_args=entrypoint_args,
        image_id=image_id,
        shell=shell,
        workdir=workdir,
        **build_image_kwargs)
