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

from typing import List, Optional

from blessings import Terminal

import caliban.config as c
import caliban.docker.build as b
import caliban.platform.shell as ps
import caliban.util.fs as ufs

t = Terminal()


def run_notebook(job_mode: c.JobMode,
                 port: Optional[int] = None,
                 lab: Optional[bool] = None,
                 version: Optional[bool] = None,
                 run_args: Optional[List[str]] = None,
                 **run_interactive_kwargs) -> None:
  """Start a notebook in the current working directory; the process will run
  inside of a Docker container that's identical to the environment available to
  Cloud jobs that are submitted by `caliban cloud`, or local jobs run with
  `caliban run.`

  if you pass mount_home=True your jupyter settings will persist across calls.

  Keyword args:

  - port: the port to pass to Jupyter when it boots, useful if you have
    multiple instances running on one machine.
  - lab: if True, starts jupyter lab, else jupyter notebook.
  - version: explicit Jupyter version to install.

  run_interactive_kwargs are all extra arguments taken by run_interactive.

  """

  if port is None:
    port = ufs.next_free_port(8888)

  if lab is None:
    lab = False

  if run_args is None:
    run_args = []

  inject_arg = b.NotebookInstall.lab if lab else b.NotebookInstall.jupyter
  jupyter_cmd = "lab" if lab else "notebook"
  jupyter_args = [
    "-m", "jupyter", jupyter_cmd, \
    "--ip=0.0.0.0", \
    "--port={}".format(port), \
    "--no-browser"
  ]
  docker_args = ["-p", "{}:{}".format(port, port)] + run_args

  ps.run_interactive(job_mode,
                     entrypoint="python",
                     entrypoint_args=jupyter_args,
                     run_args=docker_args,
                     inject_notebook=inject_arg,
                     jupyter_version=version,
                     **run_interactive_kwargs)
