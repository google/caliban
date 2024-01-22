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
"""gke utility routines"""

from __future__ import absolute_import

import argparse
import json
import logging
import os
import pprint as pp
import re
from time import sleep
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse

import google
import yaml
from google.auth._cloud_sdk import get_application_default_credentials_path
from google.auth._default import (_AUTHORIZED_USER_TYPE, _SERVICE_ACCOUNT_TYPE,
                                  load_credentials_from_file)
from google.cloud.container_v1 import ClusterManagerClient
from google.cloud.container_v1.types import Cluster as GKECluster
from google.oauth2 import service_account
from googleapiclient import discovery
from kubernetes.client import V1Job
from kubernetes.client.api_client import ApiClient
from yaspin import yaspin
from yaspin.spinners import Spinners

import caliban.platform.gke.constants as k
from caliban.platform.cloud.types import GPU, TPU, GPUSpec, TPUSpec
from caliban.platform.gke.types import CredentialsData, NodeImage, OpStatus


# ----------------------------------------------------------------------------
def trap(error_value: Any, silent: bool = True) -> Any:
  """decorator that traps exceptions

  Args:
  error_value: value to return on error
  silent: do not log exceptions

  Returns:
  error_value on exception, function return value otherwise
  """

  def check(fn):

    def wrapper(*args, **kwargs):
      try:
        response = fn(*args, **kwargs)
      except Exception as e:
        if not silent:
          logging.exception('exception in call {}:\n{}'.format(fn, e))
        return error_value
      return response

    return wrapper

  return check


# ----------------------------------------------------------------------------
def validate_gpu_spec_against_limits(
    gpu_spec: GPUSpec,
    gpu_limits: Dict[GPU, int],
    limit_type: str,
) -> bool:
  """validate gpu spec against provided limits

  Args:
  gpu_spec: gpu spec
  gpu_limits: limits
  limit_type: label for error messages

  Returns:
  True if spec is valid, False otherwise
  """

  if gpu_spec.gpu not in gpu_limits:
    logging.error('unsupported gpu type {}. '.format(gpu_spec.gpu.name) +
                  'Supported types for {}: {}'.format(
                      limit_type, [g.name for g in gpu_limits]))
    return False

  if gpu_spec.count > gpu_limits[gpu_spec.gpu]:
    logging.error('error: requested {} gpu count {} unsupported,'.format(
        gpu_spec.gpu.name, gpu_spec.count) +
                  ' {} max = {}'.format(limit_type, gpu_limits[gpu_spec.gpu]))
    return False

  return True


# ----------------------------------------------------------------------------
def nvidia_daemonset_url(node_image: NodeImage) -> Optional[str]:
  '''gets nvidia driver daemonset url for given node image

  Args:
  node_image: node image type

  Returns:
  daemonset yaml url on success, None otherwise
  '''

  DAEMONSETS = {
      NodeImage.COS: k.NVIDIA_DRIVER_COS_DAEMONSET_URL,
      NodeImage.UBUNTU: k.NVIDIA_DRIVER_UBUNTU_DAEMONSET_URL
  }

  return DAEMONSETS.get(node_image, None)


# ----------------------------------------------------------------------------
def dashboard_cluster_url(cluster_id: str, zone: str, project_id: str):
  """returns gcp dashboard url for given cluster

  Args:
  cluster_id: cluster name
  zone: zone string
  project_id: project name

  Returns:
  url string
  """

  query = urlencode({'project': project_id})
  return '{}/{}/{}?{}'.format(k.DASHBOARD_CLUSTER_URL, zone, cluster_id, query)


# ----------------------------------------------------------------------------
@trap(None)
def get_tpu_drivers(tpu_api: discovery.Resource, project_id: str,
                    zone: str) -> Optional[List[str]]:
  """gets supported tpu drivers for given project, zone

  Args:
  tpu_api: discovery tpu api resource
  project_id: project id
  zone: zone identifier

  Returns:
  list of supported drivers on success, None otherwise
  """

  location = 'projects/{}/locations/{}'.format(project_id, zone)

  rsp = tpu_api.projects().locations().tensorflowVersions().list(
      parent=location).execute()

  if rsp is None:
    logging.error('error getting tpu drivers')
    return None

  return [d['version'] for d in rsp['tensorflowVersions']]


# ----------------------------------------------------------------------------
def user_verify(msg: str, default: bool) -> bool:
  """prompts user to verify a choice

  Args:
  msg: message to display to user
  default: default value if user simply hit 'return'

  Returns:
  boolean choice
  """
  choice_str = '[Yn]' if default else '[yN]'

  while True:
    ok = input('\n {} {}: '.format(msg, choice_str)).lower()

    if len(ok) == 0:
      return default

    if ok not in ['y', 'n']:
      print('please enter y or n')
      continue

    return (ok == 'y')


# ----------------------------------------------------------------------------
@trap(None)
def wait_for_operation(cluster_api: discovery.Resource,
                       name: str,
                       conditions: List[OpStatus] = [
                           OpStatus.DONE, OpStatus.ABORTING
                       ],
                       sleep_sec: int = 1,
                       message: str = '',
                       spinner: bool = True) -> Optional[dict]:
  """waits for cluster operation to reach given state(s)

  Args:
  cluster_api: cluster api client
  name: operation name, of form projects/*/locations/*/operations/*
  conditions: exit status conditions
  sleep_sec: polling interval
  message: wait message
  spinner: display spinner while waiting

  Returns:
  response dictionary on success, None otherwise
  """

  if len(conditions) == 0:
    return None

  condition_strings = [x.name for x in conditions]

  def _wait():
    while True:
      rsp = cluster_api.projects().locations().operations().get(
          name=name).execute()

      if rsp['status'] in condition_strings:
        return rsp

      sleep(sleep_sec)

  if spinner:
    with yaspin(Spinners.line, text=message) as spinner:
      return _wait()

  return _wait()


# ----------------------------------------------------------------------------
@trap(None)
def gke_tpu_to_tpuspec(tpu: str) -> Optional[TPUSpec]:
  """convert gke tpu accelerator string to TPUSpec

  Args:
  tpu: gke tpu string

  Returns:
  TPUSpec on success, None otherwise
  """

  tpu_re = re.compile('^(?P<tpu>(v2|v3))-(?P<count>[0-9]+)$')
  match = tpu_re.match(tpu)
  if match is None:
    return None
  gd = match.groupdict()

  return TPUSpec(TPU[gd['tpu'].upper()], int(gd['count']))


# ----------------------------------------------------------------------------
@trap(None)
def get_zone_tpu_types(tpu_api: discovery.Resource, project_id: str,
                       zone: str) -> Optional[List[TPUSpec]]:
  """gets list of tpus available in given zone

  Args:
  tpu_api: tpu api instance
  project_id: project id
  zone: zone string

  Returns:
  list of supported tpu specs on success, None otherwise
  """

  location = 'projects/{}/locations/{}'.format(project_id, zone)
  rsp = tpu_api.projects().locations().acceleratorTypes().list(
      parent=location).execute()

  tpus = []
  for t in rsp['acceleratorTypes']:
    spec = gke_tpu_to_tpuspec(t['type'])
    if spec is None:
      continue
    tpus.append(spec)

  return tpus


# ----------------------------------------------------------------------------
@trap(None)
def gke_gpu_to_gpu(gpu: str) -> Optional[GPU]:
  """convert gke gpu string to GPU type

  Args:
  gpu: gke gpu string

  Returns:
  GPU on success, None otherwise
  """

  gpu_re = re.compile('^nvidia-tesla-(?P<type>[a-z0-9]+)$')
  match = gpu_re.match(gpu)
  if match is None:
    return None
  gd = match.groupdict()
  return GPU[gd['type'].upper()]


# ----------------------------------------------------------------------------
@trap(None)
def get_zone_gpu_types(compute_api: discovery.Resource, project_id: str,
                       zone: str) -> Optional[List[GPUSpec]]:
  """gets list of gpu accelerators available in given zone

  Args:
  compute_api: compute api instance
  project_id: project id
  zone: zone string

  Returns:
  list of GPUSpec on success (count is max count), None otherwise
  """

  rsp = compute_api.acceleratorTypes().list(project=project_id,
                                            zone=zone).execute()

  gpus = []

  for x in rsp['items']:
    gpu = gke_gpu_to_gpu(x['name'])
    if gpu is None:
      continue
    gpus.append(GPUSpec(gpu, int(x['maximumCardsPerInstance'])))

  return gpus


# ----------------------------------------------------------------------------
@trap(None, silent=False)
def get_region_quotas(compute_api: discovery.Resource, project_id: str,
                      region: str) -> Optional[List[Dict[str, Any]]]:
  """gets compute quotas for given region

  These quotas include cpu and gpu quotas for the given region.
  (tpu quotas are not included here)

  Args:
  compute_api: compute_api instance
  project_id: project id
  region: region string

  Returns:
  list of quota dicts, with keys {'limit', 'metric', 'usage'}, None on error
  """

  return compute_api.regions().get(project=project_id,
                                   region=region).execute().get('quotas', [])


# ----------------------------------------------------------------------------
@trap(None)
def resource_limits_from_quotas(
    quotas: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
  """create resource limits from quota dictionary

  Args:
  quotas: list of quota dicts, with keys {'limit', 'metric', 'usage'}

  Returns:
  resource limits dictionaries on success, None otherwise
  """

  limits = []

  gpu_re = re.compile('^NVIDIA_(?P<gpu>[A-Z0-9]+)_GPUS$')

  for q in quotas:
    metric = q['metric']
    limit = int(q['limit'])

    # the api can return a limit of 0, but specifying a limit of zero
    # causes an error when configuring the cluster, so we skip any
    # resources with no quota
    if limit < 1:
      continue

    if metric == 'CPUS':
      limits.append({'resourceType': 'cpu', 'maximum': str(limit)})
      limits.append({
          'resourceType': 'memory',
          'maximum': str(limit * k.MAX_GB_PER_CPU)
      })
      continue

    gpu_match = gpu_re.match(metric)
    if gpu_match is None:
      continue

    gd = gpu_match.groupdict()
    gpu_type = gd['gpu']

    limits.append({
        'resourceType': 'nvidia-tesla-{}'.format(gpu_type.lower()),
        'maximum': str(limit)
    })

  return limits


# ----------------------------------------------------------------------------
@trap(None)
def generate_resource_limits(compute_api: discovery.Resource, project_id: str,
                             region: str) -> Optional[List[Dict[str, Any]]]:
  """generates resource limits from quota information

  Args:
  compute_api: compute_api instance
  project_id: project id
  region: region string

  Returns:
  resource limits dictionaries on success, None otherwise
  """

  quotas = get_region_quotas(compute_api, project_id, region)
  if quotas is None:
    return None

  return resource_limits_from_quotas(quotas)


# ----------------------------------------------------------------------------
@trap(None, silent=False)
def job_to_dict(job: V1Job) -> Optional[dict]:
  """convert V1Job to dictionary

  Note that this is *different* than what is returned by V1Job.to_dict().
  That method uses object attribute names, which are often different than
  the names used in the REST api and yaml/json spec files.

  Args:
  job: V1Job instance

  Returns:
  dictionary representation on success, None otherwise
  """

  return ApiClient().sanitize_for_serialization(job)


# ----------------------------------------------------------------------------
def nonnull_list(lst: list) -> list:
  """recursively removes all None-valued entries from list

  Note that this recursively removes None values only for lists or dicts.

  Args:
  lst: input list

  Returns:
  list with None-valued entries removed
  """

  nnl = []
  for x in lst:
    if x is None:
      continue

    new_x: Any = x

    if type(x) == dict:
      new_x = nonnull_dict(x)
    elif type(x) == list:
      new_x = nonnull_list(x)

    nnl.append(new_x)

  return nnl


# ----------------------------------------------------------------------------
def nonnull_dict(d: dict) -> dict:
  """recursively removes all None-valued keys from a dictionary

  Note that this recursively removes None values only for dicts or lists.

  Args:
  d: input dictionary

  Returns:
  dictionary with None-valued keys removed
  """

  nnd = {}
  for k, v in d.items():
    if v is None:
      continue
    new_val: Any = v

    if type(v) == dict:
      new_val = nonnull_dict(v)
    elif type(v) == list:
      new_val = nonnull_list(v)

    nnd[k] = new_val

  return nnd


# ----------------------------------------------------------------------------
def job_str(job: V1Job) -> str:
  """formats job string to remove all default (None) values

  Args:
  job: job spec

  Returns:
  string describing job
  """
  return pp.pformat(nonnull_dict(job_to_dict(job)), indent=2, width=80)


# ----------------------------------------------------------------------------
def valid_job_file_ext(ext: str) -> bool:
  '''tests validity of file extension for job spec
  Args:
  ext: extension (must include '.', i.e. '.json')
  Returns:
  True if valid, False otherwise '''
  return ext in k.VALID_JOB_FILE_EXT


# ----------------------------------------------------------------------------
def validate_job_filename(s: str) -> str:
  '''validates a job filename string
  if invalid, raises argparse.ArgumentTypeError
  '''
  _, ext = os.path.splitext(s)

  if not valid_job_file_ext(ext):
    raise argparse.ArgumentTypeError(
        'invalid job file extension: {}, must be in {}'.format(
            ext, k.VALID_JOB_FILE_EXT))
  return s


# ----------------------------------------------------------------------------
@trap(False, silent=False)
def export_job(job: V1Job, filename: str) -> bool:
  """exports job as a kubernetes job spec to file

  The output format is determined from the file extension.
  (only .json and .yaml are supported)

  Args:
  job: V1Job instance
  filename: output file

  Returns:
  True on success, False on error
  """

  _, ext = os.path.splitext(filename)

  if not valid_job_file_ext(ext):
    logging.error('invalid job file extension: {}, must be in {}'.format(
        ext, k.VALID_JOB_FILE_EXT))
    return False

  with open(filename, 'w') as f:
    if ext == '.json':
      json.dump(nonnull_dict(job_to_dict(job)), f, indent=4)
    else:
      yaml.dump(nonnull_dict(job_to_dict(job)), f)

  return True


# ----------------------------------------------------------------------------
def sanitize_job_name(name: str) -> str:
  """sanitizes job name to fit DNS-1123 restrictions:

  ... a DNS-1123 subdomain must consist of lower case alphanumeric characters,
  '-' or '.', and must start and end with an alphanumeric character.

  An zero-len string returns 'job'
  Invalid characters are replaced with '-'.
  If the job does not start with an alnum, then the prefix 'job-' is prepended.
  If the job does not end with an alnum, then the suffix '-0' is appended.

  Args:
  name (str): job name

  Returns:
  sanitized job name
  """

  if len(name) == 0:
    return 'job'

  name = name.lower()

  # ugh, in python '²'.isalnum() returns True, so can't use isalnum
  # also, DNS-1123 is restricted, so just use re here

  def _valid(name):
    return k.DNS_1123_RE.match(name) is not None

  alnum_re = re.compile('[a-z0-9]')
  invalid_re = re.compile('[^a-z0-9\-\.]')

  def _alnum(x):
    return alnum_re.match(x) is not None

  # already valid, so done
  if _valid(name):
    return name

  # first char must be alnum
  if not _alnum(name[0]):
    name = 'job-' + name

  # last char must be alnum
  if not _alnum(name[-1]):
    name = name + '-0'

  # replace all invalid chars with '-'
  return invalid_re.sub('-', name)


# ----------------------------------------------------------------------------
def application_default_credentials_path() -> str:
  """gets gcloud default credentials path"""
  return get_application_default_credentials_path()


# ----------------------------------------------------------------------------
@trap(CredentialsData(None, None), silent=False)
def default_credentials(
    scopes: List[str] = [k.CLOUD_PLATFORM_SCOPE_URL, k.COMPUTE_SCOPE_URL]
) -> CredentialsData:
  """gets default cloud credentials

  Args:
  scopes: list of scopes for credentials

  Returns:
  CredentialsData

  both credentials and project id may be None if unable to resolve
  """

  creds, project_id = google.auth.default(scopes=scopes)
  creds.refresh(google.auth.transport.requests.Request())

  return CredentialsData(creds, project_id)


# ----------------------------------------------------------------------------
@trap(CredentialsData(None, None), silent=False)
def credentials_from_file(
    cred_file: str,
    scopes: List[str] = [k.CLOUD_PLATFORM_SCOPE_URL, k.COMPUTE_SCOPE_URL]
) -> CredentialsData:
  """gets cloud credentials from service account file

  Args:
  cred_file: service account credentials file to read
  scopes: list of scopes for credentials

  Returns:
  CredentialsData
  """

  with open(cred_file, 'r') as f:
    info = json.load(f)

  cred_type = info.get('type')

  # first we try reading as service account file
  if cred_type == _SERVICE_ACCOUNT_TYPE:
    creds = service_account.Credentials.from_service_account_file(cred_file,
                                                                  scopes=scopes)
    project_id = info.get('project_id')
  elif cred_type == _AUTHORIZED_USER_TYPE:
    creds, project_id = load_credentials_from_file(cred_file)
  else:
    logging.error('invalid credentials file format: {}'.format(cred_type))
    return CredentialsData(None, None)

  creds.refresh(google.auth.transport.requests.Request())

  return CredentialsData(credentials=creds, project_id=project_id)


# ----------------------------------------------------------------------------
def credentials(creds_file: Optional[str] = None) -> CredentialsData:
  """get credentials data, either from provided file or from system defaults

  Args:
  creds_file: (optional) path to credentials file

  Returns:
  CredentialsData
  """

  if creds_file is None:
    return default_credentials()

  return credentials_from_file(creds_file)


# --------------------------------------------------------------------------
@trap(None)
def get_gke_clusters(client: ClusterManagerClient,
                     project_id: str,
                     zone: str = '-') -> Optional[List[GKECluster]]:
  """gets list of gcp clusters for given project, zone

  Args:
  client: cluster api client
  project_id: project id
  zone: zone, - = all zones

  Returns:
  list of clusters on success, None otherwise
  """

  return client.list_clusters(project_id=project_id, zone=zone).clusters


# ----------------------------------------------------------------------------
@trap(None)
def get_gke_cluster(client: ClusterManagerClient,
                    name: str,
                    project_id: str,
                    zone: str = '-') -> Optional[GKECluster]:
  """gets specific cluster instance by name

  Args:
  client: cluster api client
  name: cluster name
  project_id: project id
  zone: zone, - = all zones

  Returns:
  GKECluster on success, None otherwise
  """

  return next(
      filter(
          lambda x: x.name == name,
          get_gke_clusters(client, project_id, zone),
      ))


# ----------------------------------------------------------------------------
def parse_job_file(job_file: str) -> Optional[dict]:
  '''parses a kubernetes job spec file

  Args:
  job_file: path to job spec file (.json or .yaml)

  Returns:
  job spec dictionary on success, None otherwise
  '''

  _, ext = os.path.splitext(job_file)

  if not valid_job_file_ext(ext):
    logging.error('invalid job file extension: {}, '.format(ext) +
                  'must be in {}'.format(k.VALID_JOB_FILE_EXT))
    return None

  if not os.path.exists(job_file):
    logging.error('error: job file {} not found'.format(job_file))
    return None

  try:
    if ext == '.json':
      with open(job_file, 'r') as f:
        job_spec = json.load(f)
    else:
      with open(job_file, 'r') as f:
        job_spec = yaml.load(f, Loader=yaml.FullLoader)

  except Exception as e:
    logging.error('error loading job file {}:\n{}'.format(job_file, e))
    return None

  return job_spec


# ----------------------------------------------------------------------------
@trap(None)
def get_zones_in_region(compute_api: discovery.Resource, project_id: str,
                        region: str) -> Optional[List[str]]:
  '''get list of zones for given region

  Args:
  compute_api: compute_api instance
  project_id: project id
  region: region

  Returns:
  list of zone strings on success, None otherwise
  '''

  rsp = compute_api.regions().get(project=project_id, region=region).execute()

  return [urlparse(x).path.split('/')[-1] for x in rsp['zones']]
