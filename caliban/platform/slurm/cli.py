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
"""slurm cli support"""

import json
import logging
import os
import pprint as pp
import re
import shlex
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

import caliban.cli as cli
import caliban.config as conf
import caliban.util as u
from caliban.history.util import (create_experiments, generate_container_spec,
                                  get_mem_engine, get_sql_engine, session_scope)


# ----------------------------------------------------------------------------
# Remote access via ssh
_hostname = "symmetry.pi.local"
_username = "eschnetter"

# Job management via Slurm
_partition = "debugq"
_timelimit = "00:10:00"
_slurm_path = "/cm/shared/apps/slurm/19.05.5"
_sbatch = _slurm_path + "/bin/sbatch"
_sinfo = _slurm_path + "/bin/sinfo"
_squeue = _slurm_path + "/bin/squeue"


# ----------------------------------------------------------------------------
def run_cli_command(args: dict) -> None:
  """cli entrypoint for Slurm commands"""
  SLURM_CMDS = {
      'ls': _partition_ls,
      'job': _job_commands,
  }
  SLURM_CMDS[args['slurm_cmd']](args)


# ----------------------------------------------------------------------------
def _partition_ls(args: dict) -> None:
  """list Slurm partitions"""
  cmd = [_sinfo, '-h', '-o', '%P']
  process = subprocess.run(_with_ssh(cmd),
                           stdout=subprocess.PIPE,
                           universal_newlines=True)
  partitions = process.stdout.splitlines()
  logging.info("{} partitions found".format(len(partitions)))
  for p in partitions:
    logging.info("  " + p)


# ----------------------------------------------------------------------------
def _job_commands(args: dict) -> None:
  """job commands"""
  JOB_CMDS = {
    'ls': _job_ls,
    'submit': _job_submit,
    #TODO 'submit_file': _job_submit_file
  }
  JOB_CMDS[args['job_cmd']](args)


# ----------------------------------------------------------------------------
def _job_ls(args: dict) -> None:
  """list Slurm jobs"""
  # TODO: Look also for jobs that have terminated a long time ago?
  cmd = [_squeue, '-h', '-o', "%A", '-t', "all", '-u', _username]
  process = subprocess.run(_with_ssh(cmd),
                           stdout=subprocess.PIPE,
                           universal_newlines=True)
  jobs = process.stdout.splitlines()
  logging.info("{} jobs found".format(len(jobs)))
  for j in jobs:
    # TODO: Look up and output job metadata
    logging.info("  " + j)


# ----------------------------------------------------------------------------
def _job_submit(args: dict) -> None:
  """submits Slurm job(s)

  Args:
  args: argument dictionary
  """

  dt = datetime.now().astimezone()
  jobname = f'caliban-{dt.strftime("%Y%m%d-%H%M%S")}'
  outputname = jobname + ".log"

  script = """\
#!/bin/bash
echo 'Hello, World!'
echo Date: $(date)
echo Hostname: $(hostname)
"""

  logging.info("Submitting job...")
  cmd = [_sbatch,
         "--job-name", jobname,
         "--nodes", "1",
         "--output", outputname,
         "--partition", _partition,
         "--time", _timelimit]
  process = subprocess.run(_with_ssh(cmd),
                           input=script,
                           stdout=subprocess.PIPE,
                           universal_newlines=True)
  output = process.stdout.rstrip()
  logging.info("Received response \"{}\"".format(output))
  # Output looks like "Submitted batch job 133417"
  m = re.search(r"Submitted batch job (\d+)", output)
  assert m.lastindex == 1
  job_id = m.group(1)
  assert job_id != ''
  logging.info("Submitted job {}".format(job_id))


# ----------------------------------------------------------------------------
def _with_ssh(args: [str]) -> [str]:
  """adds ssh command to execute command remotely"""
  # Quote command and arguments
  qargs = []
  for arg in args:
    qargs.append(shlex.quote(arg))
  # Add ssh command prefix
  return ['ssh', '-l', _username, _hostname] + qargs
