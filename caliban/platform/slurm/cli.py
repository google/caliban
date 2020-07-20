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
from blessings import Terminal
from datetime import datetime
from pprint import pformat
from typing import Any, Dict, List, Optional

import caliban.cli as cli
import caliban.config as conf
import caliban.docker.build as db
import caliban.util as u
from caliban.history.util import (create_experiments, generate_container_spec,
                                  get_mem_engine, get_sql_engine, session_scope)
from caliban.platform.cloud.core import generate_image_tag


t = Terminal()


# ----------------------------------------------------------------------------
# Remote access via ssh
_ssh = "ssh"
_hostname = "symmetry.pi.local"
_username = "eschnetter"

# Environment modules
_setup_cmds = [["source", "/etc/profile"],
               ["module", "load", "slurm"]]

# Job management via Slurm
_sbatch = "sbatch"
_sinfo = "sinfo"
_squeue = "squeue"
_partition = "debugq"
_timelimit = "00:10:00"
_nodes = 1


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

  script_args = conf.extract_script_args(args)
  job_mode = cli.resolve_job_mode(args)
  docker_args = cli.generate_docker_args(job_mode, args)
  docker_run_args = args.get('docker_run_args', []) or []
  dry_run = args['dry_run']
  package = args['module']
  job_name = args.get('name')
  gpu_spec = args.get('gpu_spec')
  preemptible = not args['nonpreemptible']
  min_cpu = args.get('min_cpu')
  min_mem = args.get('min_mem')
  experiment_config = args.get('experiment_config') or [{}]
  xgroup = args.get('xgroup')
  image_tag = args.get('image_tag')
  export = args.get('export', None)

  labels = args.get('label')
  if labels is not None:
    labels = dict(cu.sanitize_labels(args.get('label')))

  # Generate job name
  dt = datetime.now().astimezone()
  job_prefix = f'caliban-{dt.strftime("%Y%m%d-%H%M%S")}'
  # TODO: Sanitize job_name
  if job_name is None:
    job_name = job_prefix
    output_filename = job_name + ".log"
  else:
    output_filename = job_prefix + "-" + job_name + ".log"

  # Arguments to internally build the image required to submit to Slurm
  docker_m = {'job_mode': job_mode, 'package': package, **docker_args}

  # --------------------------------------------------------------------------
  engine = get_mem_engine() if dry_run else get_sql_engine()

  logging.info("*** engine")
  with session_scope(engine) as session:
    container_spec = generate_container_spec(session, docker_m, image_tag)

    logging.info("*** image_tag")
    if image_tag is None:
      # Create Docker image, and push it to a Docker repository
      logging.info("Generating Docker image with parameters:")
      logging.info(t.yellow(pformat(docker_args)))

      if dry_run:
        logging.info("Dry run - skipping actual 'docker build' and 'docker push'.")
        image_tag = "dry_run_tag"
      else:
        image_id = db.build_image(**docker_m)

        project_id = args['project_id']
        project_s = project_id.replace(":", "/")
        # TODO: Use sub-project "caliban" or similar?
        # base = f"docker.io/{project_s}/{image_id}"
        base = f"{project_s}/{image_id}"
        image_tag = f"{base}:latest"
        subprocess.run(["docker", "tag", image_id, image_tag], check=True)
        subprocess.run(["docker", "push", image_tag], check=True)

    logging.info("*** experiments")
    experiments = create_experiments(
        session=session,
        container_spec=container_spec,
        script_args=script_args,
        experiment_config=experiment_config,
        xgroup=xgroup,
    )

    for experiment in experiments:
      logging.info("*** script")
      # TODO: Use srun to start job, then use singularity inside srun
      script = f"""\
#!/bin/bash
source /etc/profile
set -euxo pipefail
date
hostname
nproc
module load singularity
env PYTHONUNBUFFERED=1 singularity run --tmpdir /gpfs/eschnetter/singularity/tmp --workdir /gpfs/eschnetter/singularity/work --pwd /usr/app docker://{image_tag} exe/cactus_sim arrangements/CactusWave/WaveToyC/par/wavetoyc_rad.par
"""
      logging.info(f"Script is {script}")

      logging.info("Submitting job...")
      cmd = [_sbatch,
             "--job-name", job_name,
             "--nodes", str(_nodes),
             "--output", output_filename,
             "--partition", _partition,
             "--time", _timelimit]
      process = subprocess.run(_with_ssh(cmd),
                               input=script,
                               stdout=subprocess.PIPE,
                               universal_newlines=True,
                               check=True)
      output = process.stdout.rstrip()
      logging.info("Received response \"{}\"".format(output))
      # Output looks like "Submitted batch job 133417"
      m = re.search(r"Submitted batch job (\d+)", output)
      assert m.lastindex == 1
      job_id = m.group(1)
      assert job_id != ''
      logging.info("Submitted job {}".format(job_id))


# ----------------------------------------------------------------------------
def _quote_args(args: [str]) -> str:
  """converts a command into a shell command string"""
  qargs = []
  for arg in args:
    qargs.append(shlex.quote(arg))
  return " ".join(qargs)


# ----------------------------------------------------------------------------
def _join_cmds(cmds: [str]) -> str:
  """joins several shell commands into a single one"""
  return "; ".join(cmds)


# ----------------------------------------------------------------------------
def _with_ssh(cmd: [str]) -> [str]:
  """adds ssh command to execute command remotely"""
  # Add module load commands
  cmds = _setup_cmds + [cmd]
  cmd = _join_cmds(map(_quote_args, cmds))
  # Add ssh command prefix
  assert _hostname[0] != '-'
  return [_ssh, '-l', _username, _hostname, cmd]
