"""gke cli support"""

import pprint as pp
import re
import logging
import json

from typing import Optional, List, Tuple
from google.auth.credentials import Credentials
import googleapiclient
from googleapiclient import discovery
from kubernetes.client import (V1Job, V1ObjectMeta, V1JobSpec, V1Pod)

import caliban.cli as cli
import caliban.config as conf
from caliban.gke import Cluster
import caliban.gke.constants as k
import caliban.gke.utils as utils
from caliban.gke.types import NodeImage, CredentialsData
from caliban.cloud.core import generate_image_tag


# ----------------------------------------------------------------------------
def _project_and_creds(fn):
  """wrapper to supply project and credentials from args"""

  def wrapper(args: dict):
    project_id = args.get('project_id')
    creds_file = args.get('cloud_key')

    creds_data = utils.credentials(creds_file)
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

  if len(clusters) == 0:
    return True

  if cluster_name in clusters:
    logging.error(f'cluster {cluster_name} already exists')
    return False

  logging.info(f'{len(clusters)} clusters already exist for this project:')
  for c in clusters:
    logging.info(c)

  return utils.user_verify('Do you really want to create a new cluster?',
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
    return utils.export_job(jobs[0], export)
  else:
    base, ext = os.path.splitext(export)
    for i, j in enumerate(jobs):
      if not utils.export_job(j, f'{base}_{i}{ext}'):
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
  dashboard_url = utils.dashboard_cluster_url(cluster_name, zone, project_id)
  release_channel = args['release_channel']

  # --------------------------------------------------------------------------
  # see https://buganizer.corp.google.com/issues/148180423 for why we use the
  # discovery api here
  cluster_client = googleapiclient.discovery.build('container',
                                                   k.CLUSTER_API_VERSION,
                                                   credentials=creds,
                                                   cache_discovery=False)

  if cluster_client is None:
    logging.error('error building cluster client')
    return

  request = Cluster.create_request(cluster_client, creds, cluster_name,
                                   project_id, zone, release_channel)

  if request is None:
    logging.error('error creating cluster creation request')
    return

  if dry_run:
    logging.info(f'request:\n{pp.pformat(json.loads(request.body))}')
    return

  # --------------------------------------------------------------------------
  # see if cluster(s) already exist, and if so, check with the user before
  # creating another
  if not _check_for_existing_cluster(cluster_name, project_id, creds):
    return

  logging.info(
      f'creating cluster {cluster_name} in project {project_id} in {zone}...')
  logging.info(f'please be patient, this may take several minutes')
  logging.info(f'visit {dashboard_url} to monitor cluster creation progress')

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

  if utils.user_verify(f'Are you sure you want to delete {cluster.name}?',
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
      logging.error(f'cluster {cluster_name} not found')
      return
    logging.error(cluster_name)
    return

  logging.info(f'{len(clusters)} clusters found')
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

  logging.info(f'{len(pods)} pods found')
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

  logging.info(f'{len(jobs)} jobs found')
  for j in jobs:
    logging.info(j.metadata.name)

  return


# ----------------------------------------------------------------------------
@_project_and_creds
@_with_cluster
def _job_submit(args: dict, cluster: Cluster) -> Optional[List[V1Job]]:
  """submits job(s) to cluster

  Args:
  args: argument dictionary
  cluster: cluster instance

  Returns:
  list of V1Jobs submitted on success, None otherwise
  """

  script_args = conf.extract_script_args(args)
  job_mode = cli.resolve_job_mode(args)
  docker_args = cli.generate_docker_args(job_mode, args)
  docker_run_args = args.get('docker_run_args', []) or []
  dry_run = args['dry_run']
  package = args['module']
  job_name = args.get('name') or f"caliban_{u.current_user()}"
  gpu_spec = args.get('gpu_spec')

  # todo: enable this when supported
  preemptible = False  # not args['nonpreemptible']

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
      logging.error(f'invalid tpu spec, cluster supports:')
      for t in available_tpu:
        logging.info(f'{t.count}x{t.tpu.name}')
      return

    if not cluster.validate_tpu_driver(tpu_driver):
      logging.error(f'error: unsupported tpu driver {tpu_driver}')
      logging.info('supported tpu drivers for this cluster:')
      for d in cluster.get_tpu_drivers():
        logging.info(f'  {d}')
      return

  # --------------------------------------------------------------------------
  image_tag = (args.get('image_tag') or generate_image_tag(
      cluster.project_id, docker_args=docker_m, dry_run=dry_run))

  if args.get('machine_type') is None:
    machine_type = conf.DEFAULT_MACHINE_TYPE[job_mode]
  else:
    machine_type = parse_machine_type(args.get('machine_type'))

  experiments = conf.expand_experiment_config(
      args.get('experiment_config') or [{}])

  labels = args.get('label')
  if labels is not None:
    labels = dict(u.sanitize_labels(args.get('label')))

  # convert accelerator spec
  accel_spec = Cluster.convert_accel_spec(gpu_spec, tpu_spec)
  if accel_spec is None:
    return

  accel, accel_count = accel_spec

  # create V1 jobs
  jobs = cluster.create_simple_experiment_jobs(
      name=utils.sanitize_job_name(job_name),
      image=image_tag,
      experiments=experiments,
      args=script_args,
      accelerator=accel,
      accelerator_count=accel_count,
      machine_type=machine_type,
      preemptible=preemptible,
      labels=labels,
      preemptible_tpu=preemptible_tpu,
      tpu_driver=tpu_driver)

  job_list = [j for j in jobs]

  # just a dry run
  if dry_run:
    logging.info('jobs that would be submitted:')
    for j in job_list:
      logging.info(f'\n{utils.job_str(j)}')
    return

  # export jobs to file
  export = args.get('export', None)
  if export is not None:
    if not _export_jobs(export, job_list):
      print(f'error exporting jobs to {export}')
      return

  submitted = []
  for j in job_list:
    sj = cluster.submit_job(j)
    if sj is None:
      logging.error(f'error submitting job:\n {j}')
    else:
      submitted.append(sj)
      md = sj.metadata
      spec = sj.spec
      container = sj.spec.template.spec.containers[0]
      logging.info(
          f'submitted job:\n{md.name}: {" ".join(container.args or [])}\n'
          f'{cluster.job_dashboard_url(sj)}')

  return submitted


# ----------------------------------------------------------------------------
@_project_and_creds
@_with_cluster
def _job_submit_file(args: dict, cluster: Cluster) -> None:
  """submit gke job from k8s yaml/json file"""

  job_file = args['job_file']

  job_spec = utils.parse_job_file(job_file)
  if job_spec is None:
    logging.error(f'error parsing job file {job_file}')
    return

  if args['dry_run']:
    logging.info(f'job to submit:\n{pp.pformat(job_spec)}')
    return

  job = cluster.submit_job(job=job_spec)
  if job is None:
    logging.error(f'error submitting job:\n{pp.pformat(job_spec)}')
    return

  logging.info(f'submitted job: {cluster.job_dashboard_url(job)}')

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
