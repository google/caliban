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
"""gke cli support"""

import json
import logging
import os
import pprint as pp
from datetime import datetime
from typing import Any, Dict, List, Optional

import googleapiclient
from google.auth.credentials import Credentials
from kubernetes.client import V1Job

import caliban.cli as cli
import caliban.config as conf
import caliban.platform.cloud.util as cu
import caliban.platform.gke.constants as k
import caliban.platform.gke.util as util
import caliban.util as u
import caliban.util.metrics as um
from caliban.history.util import (create_experiments, generate_container_spec,
                                  get_mem_engine, get_sql_engine, session_scope)
from caliban.platform.cloud.core import generate_image_tag
from caliban.platform.gke.cluster import Cluster


# ----------------------------------------------------------------------------
def _project_and_creds(fn):
  """wrapper to supply project and credentials from args"""

  def wrapper(args: dict):
    project_id = args.get('project_id')
    creds_file = args.get('cloud_key')

    creds_data = util.credentials(creds_file)
    creds = creds_data.credentials

    if project_id is None:
      project_id = creds_data.project_id

    return fn(args, project_id, creds)

  return wrapper


# ----------------------------------------------------------------------------
def _with_cluster(fn):
  """decorator for cluster methods to get cluster from args"""

  def wrapper(args: dict,
              project_id: str,
              creds: Credentials,
              zone: str = k.ZONE_DEFAULT):
    cluster_name = args.get('cluster_name')

    cluster = Cluster.get(name=cluster_name,
                          project_id=project_id,
                          zone=zone,
                          creds=creds)

    return fn(args, cluster=cluster) if cluster else None

  return wrapper


# ----------------------------------------------------------------------------
def _check_for_existing_cluster(cluster_name: str, project_id: str,
                                creds: Credentials):
  '''checks for an existing cluster and confirms new cluster creation with user

  Args:
  cluster_name: name of cluster to create
  project_id: project id
  creds: credentials

  Returns:
  True if cluster creation should proceed, False otherwise
  '''

  clusters = Cluster.list(project_id=project_id, creds=creds)

  if clusters is None:
    return False

  if len(clusters) == 0:
    return True

  if cluster_name in clusters:
    logging.error('cluster {} already exists'.format(cluster_name))
    return False

  logging.info('{} clusters already exist for this project:'.format(
      len(clusters)))
  for c in clusters:
    logging.info(c)

  return util.user_verify('Do you really want to create a new cluster?',
                          default=False)


# ----------------------------------------------------------------------------
def _export_jobs(export: str, jobs: List[V1Job]) -> bool:
  """exports job(s) to file

  If there is more than one job in the list, the output filenames are
  generated as:
  {export string without extension}_{list index}.{export file extension}

  Args:
  export: filename for exported job spec, must have extension of .json or .yaml
  jobs: V1Job list

  Returns:
  True on success, False otherwise
  """

  if len(jobs) == 1:
    return util.export_job(jobs[0], export)
  else:
    base, ext = os.path.splitext(export)
    for i, j in enumerate(jobs):
      if not util.export_job(j, f'{base}_{i}{ext}'):
        return False

  return True


# ----------------------------------------------------------------------------
@_project_and_creds
def _cluster_create(args: dict, project_id: str, creds: Credentials) -> None:
  """creates a gke cluster

  Args:
  args: commandline args
  project_id: project in which to create cluster
  creds: credentials to use
  """
  dry_run = args['dry_run']
  cluster_name = args['cluster_name'] or k.DEFAULT_CLUSTER_NAME
  zone = args['zone']
  dashboard_url = util.dashboard_cluster_url(cluster_name, zone, project_id)
  release_channel = args['release_channel']
  single_zone = args['single_zone']

  # --------------------------------------------------------------------------
  cluster_client = googleapiclient.discovery.build('container',
                                                   k.CLUSTER_API_VERSION,
                                                   credentials=creds,
                                                   cache_discovery=False)

  if cluster_client is None:
    logging.error('error building cluster client')
    return

  request = Cluster.create_request(cluster_client, creds, cluster_name,
                                   project_id, zone, release_channel,
                                   single_zone)

  if request is None:
    logging.error('error creating cluster creation request')
    return

  if dry_run:
    logging.info('request:\n{}'.format(pp.pformat(json.loads(request.body))))
    return

  # --------------------------------------------------------------------------
  # see if cluster(s) already exist, and if so, check with the user before
  # creating another
  if not _check_for_existing_cluster(cluster_name, project_id, creds):
    return

  logging.info('creating cluster {} in project {} in {}...'.format(
      cluster_name, project_id, zone))
  logging.info('please be patient, this may take several minutes')
  logging.info(
      'visit {} to monitor cluster creation progress'.format(dashboard_url))

  # --------------------------------------------------------------------------
  # create the cluster
  cluster = Cluster.create(cluster_client, creds, request, project_id)

  return


# ----------------------------------------------------------------------------
@_project_and_creds
@_with_cluster
def _cluster_delete(args: dict, cluster: Cluster) -> None:
  """deletes given cluster

  Args:
  args: commandline args
  cluster: cluster to delete

  Returns:
  None
  """

  if util.user_verify('Are you sure you want to delete {}?'.format(
      cluster.name),
                      default=False):
    cluster.delete()

  return


# ----------------------------------------------------------------------------
@_project_and_creds
def _cluster_ls(args: dict, project_id: str, creds: Credentials) -> None:
  """lists clusters

  Args:
  args: commandline args
  project_id: list clusters in the project
  creds: credentials to use
  """
  clusters = Cluster.list(project_id=project_id, creds=creds)

  if clusters is None:
    return

  cluster_name = args.get('cluster_name', None)

  if cluster_name is not None:
    if cluster_name not in clusters:
      logging.error('cluster {} not found'.format(cluster_name))
      return
    logging.error(cluster_name)
    return

  logging.info('{} clusters found'.format(len(clusters)))
  for c in clusters:
    logging.info(c)

  return


# ----------------------------------------------------------------------------
@_project_and_creds
@_with_cluster
def _node_pool_ls(args: dict, cluster: Cluster) -> None:
  """lists cluster node pools

  Args:
  args: commandline args
  cluster: lists node pools in this cluster instance
  """

  np = cluster.node_pools()

  if np is None:
    return

  if len(np) == 0:
    logging.info('no node pools found')
    return

  FMT = '%-20s%-20s%-40s%-20s'
  logging.info(FMT, 'NAME', 'MACHINE TYPE', 'ACCELERATORS', 'MAX NODES')
  for p in np:
    accel = ','.join([
        '%s(%d)' % (a.accelerator_type, a.accelerator_count)
        for a in p.config.accelerators
    ])
    logging.info(
        FMT %
        (p.name, p.config.machine_type, accel, p.autoscaling.max_node_count))

  return


# ----------------------------------------------------------------------------
@_project_and_creds
@_with_cluster
def _pod_ls(args: dict, cluster: Cluster):
  """lists pods for given cluster

  Args:
  args: commandline args
  cluster: list pods in this cluster
  """
  pods = cluster.pods()
  if pods is None:
    return

  logging.info('{} pods found'.format(len(pods)))
  for p in pods:
    logging.info(p.metadata.name)

  return


# ----------------------------------------------------------------------------
@_project_and_creds
@_with_cluster
def _job_ls(args: dict, cluster: Cluster):
  """lists jobs in given cluster

  Args:
  args: commandline args
  cluster: lists jobs from this cluster
  """
  jobs = cluster.jobs()

  if jobs is None:
    return

  logging.info('{} jobs found'.format(len(jobs)))
  for j in jobs:
    logging.info(j.metadata.name)

  return


# ----------------------------------------------------------------------------
def _generate_job_name(name: Optional[str]) -> str:
  '''simple utility to generate a job name automatically if none is provided'''
  if name is None:
    dt = datetime.now().astimezone()
    name = f'caliban-{u.current_user()}-{dt.strftime("%Y%m%d-%H%M%S")}'
  return name


# ----------------------------------------------------------------------------
@_project_and_creds
@_with_cluster
def _job_submit(args: dict, cluster: Cluster) -> None:
  """submits job(s) to cluster

  Args:
  args: argument dictionary
  cluster: cluster instance
  """

  script_args = conf.extract_script_args(args)
  job_mode = cli.resolve_job_mode(args)
  docker_args = cli.generate_docker_args(job_mode, args)
  docker_run_args = args.get('docker_run_args', []) or []
  dry_run = args['dry_run']
  package = args['module']
  job_name = _generate_job_name(args.get('name'))
  gpu_spec = args.get('gpu_spec')
  preemptible = not args['nonpreemptible']
  min_cpu = args.get('min_cpu')
  min_mem = args.get('min_mem')
  experiment_config = args.get('experiment_config') or [{}]
  xgroup = args.get('xgroup')
  image_tag = args.get('image_tag')
  export = args.get('export', None)
  caliban_config = docker_args.get('caliban_config', {})

  labels = args.get('label')
  if labels is not None:
    labels = dict(cu.sanitize_labels(labels))
  labels = labels or {}

  # Arguments to internally build the image required to submit to Cloud.
  docker_m = {'job_mode': job_mode, 'package': package, **docker_args}

  # --------------------------------------------------------------------------
  # validatate gpu spec
  if job_mode == conf.JobMode.GPU and gpu_spec is None:
    gpu_spec = k.DEFAULT_GPU_SPEC

  if not cluster.validate_gpu_spec(gpu_spec):
    return

  # --------------------------------------------------------------------------
  # validate tpu spec and driver
  tpu_spec = args.get('tpu_spec')
  preemptible_tpu = not args.get('nonpreemptible_tpu')
  tpu_driver = args.get('tpu_driver')

  if tpu_spec is not None:
    available_tpu = cluster.get_tpu_types()
    if available_tpu is None:
      logging.error('error getting valid tpu types for cluster')
      return

    if tpu_spec not in available_tpu:
      logging.error('invalid tpu spec, cluster supports:')
      for t in available_tpu:
        logging.info('{}x{}'.format(t.count, t.tpu.name))
      return

    if not cluster.validate_tpu_driver(tpu_driver):
      logging.error('error: unsupported tpu driver {}'.format(tpu_driver))
      logging.info('supported tpu drivers for this cluster:')
      for d in cluster.get_tpu_drivers():
        logging.info('  {}'.format(d))
      return

  if tpu_spec is None and gpu_spec is None:  # cpu-only job
    min_cpu = min_cpu or k.DEFAULT_MIN_CPU_CPU
    min_mem = min_mem or k.DEFAULT_MIN_MEM_CPU
  else:  # gpu/tpu-accelerated job
    min_cpu = min_cpu or k.DEFAULT_MIN_CPU_ACCEL
    min_mem = min_mem or k.DEFAULT_MIN_MEM_ACCEL

  # convert accelerator spec
  accel_spec = Cluster.convert_accel_spec(gpu_spec, tpu_spec)
  if accel_spec is None:
    return

  accel, accel_count = accel_spec

  # --------------------------------------------------------------------------
  engine = get_mem_engine() if dry_run else get_sql_engine()

  with session_scope(engine) as session:
    container_spec = generate_container_spec(session, docker_m, image_tag)

    if image_tag is None:
      image_tag = generate_image_tag(cluster.project_id, docker_m, dry_run)

    labels[um.GPU_ENABLED_TAG] = str(job_mode == conf.JobMode.GPU).lower()
    labels[um.TPU_ENABLED_TAG] = str(tpu_spec is not None)
    labels[um.DOCKER_IMAGE_TAG] = image_tag

    experiments = create_experiments(
        session=session,
        container_spec=container_spec,
        script_args=script_args,
        experiment_config=experiment_config,
        xgroup=xgroup,
    )

    specs = list(
        cluster.create_simple_experiment_job_specs(
            name=util.sanitize_job_name(job_name),
            image=image_tag,
            min_cpu=min_cpu,
            min_mem=min_mem,
            experiments=experiments,
            args=script_args,
            accelerator=accel,
            accelerator_count=accel_count,
            preemptible=preemptible,
            preemptible_tpu=preemptible_tpu,
            tpu_driver=tpu_driver,
            labels=labels,
            caliban_config=caliban_config,
        ))

    # just a dry run
    if dry_run:
      logging.info('jobs that would be submitted:')
      for s in specs:
        logging.info(f'\n{json.dumps(s.spec, indent=2)}')
      return

    # export jobs to file
    if export is not None:
      if not _export_jobs(
          export,
          cluster.create_v1jobs(specs, job_name, labels),
      ):
        print('error exporting jobs to {}'.format(export))
      return

    for s in specs:
      try:
        cluster.submit_job(job_spec=s, name=job_name, labels=labels)
      except Exception as e:
        logging.error(f'exception: {e}')
        session.commit()  # commit here, otherwise will be rolled back
        return

  # --------------------------------------------------------------------------
  logging.info(f'jobs submitted, visit {cluster.dashboard_url()} to monitor')

  return


# ----------------------------------------------------------------------------
@_project_and_creds
@_with_cluster
def _job_submit_file(args: dict, cluster: Cluster) -> None:
  """submit gke job from k8s yaml/json file"""

  job_file = args['job_file']

  job_spec = util.parse_job_file(job_file)
  if job_spec is None:
    logging.error('error parsing job file {}'.format(job_file))
    return

  if args['dry_run']:
    logging.info('job to submit:\n{}'.format(pp.pformat(job_spec)))
    return

  job = cluster.submit_v1job(job=job_spec)
  if job is None:
    logging.error('error submitting job:\n{}'.format(pp.pformat(job_spec)))
    return

  logging.info('submitted job: {}'.format(cluster.job_dashboard_url(job)))

  return


# ----------------------------------------------------------------------------
def run_cli_command(args) -> None:
  """cli entrypoint for cluster commands"""
  CLUSTER_CMDS = {
      'ls': _cluster_ls,
      'create': _cluster_create,
      'delete': _cluster_delete,
      'pod': _pod_commands,
      'job': _job_commands,
      'node_pool': _node_pool_commands
  }
  CLUSTER_CMDS[args['cluster_cmd']](args)
  return


# ----------------------------------------------------------------------------
def _pod_commands(args) -> None:
  """pod commands"""
  POD_CMDS = {'ls': _pod_ls}
  POD_CMDS[args['pod_cmd']](args)
  return


# ----------------------------------------------------------------------------
def _job_commands(args) -> None:
  """job commands"""
  JOB_CMDS = {
      'ls': _job_ls,
      'submit': _job_submit,
      'submit_file': _job_submit_file
  }
  JOB_CMDS[args['job_cmd']](args)
  return


# ----------------------------------------------------------------------------
def _node_pool_commands(args) -> None:
  """node pool commands"""
  NODE_POOL_CMDS = {'ls': _node_pool_ls}
  NODE_POOL_CMDS[args['node_pool_cmd']](args)
  return


# ----------------------------------------------------------------------------
@_project_and_creds
@_with_cluster
def submit_job_specs(
    args: Dict[str, Any],
    cluster: Cluster,
) -> None:
  """submits jobs to cluster

  Args:
  args: dictionary of args
  cluster: cluster instance
  """
  job_specs = args.get('specs', [])

  for s in job_specs:
    name = s.spec['template']['spec']['containers'][0]['name']
    cluster.submit_job(job_spec=s, name=name)
