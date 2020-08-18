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
"""cluster abstraction for gcloud/gke"""

import json
import logging
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import googleapiclient
import kubernetes
import requests
# silence warnings about ssl connection not being verified
import urllib3
import yaml
from google.auth.credentials import Credentials
from google.cloud.container_v1 import ClusterManagerClient
from google.cloud.container_v1.types import NodePool, Cluster as GKECluster
from googleapiclient import discovery
from googleapiclient.http import HttpRequest
from kubernetes.client import (V1Container, V1DaemonSet, V1EnvVar, V1Job,
                               V1JobSpec, V1ObjectMeta, V1Pod, V1PodSpec,
                               V1PodTemplateSpec, V1ResourceRequirements,
                               V1Toleration)
from kubernetes.client.api_client import ApiClient

import caliban.config.experiment as ce
import caliban.platform.gke.constants as k
import caliban.platform.gke.util as util
from caliban.history.types import Experiment, Job, JobSpec, JobStatus, Platform
from caliban.platform.cloud.types import (GPU, TPU, Accelerator, GPUSpec,
                                          MachineType, TPUSpec)
from caliban.platform.gke.types import NodeImage, OpStatus, ReleaseChannel
from caliban.platform.gke.util import trap
import caliban.util.metrics as um

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ----------------------------------------------------------------------------
# tone down logging from discovery
logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)


# ----------------------------------------------------------------------------
def _parse_zone(zone: str) -> Optional[Tuple[str, str]]:
  """parses zone into region and zone tuple

  Args:
  zone: zone string

  Returns:
  (region, zone) string tuple on success, None otherwise
  """

  if zone is None:
    return None

  zone_re = re.compile('^(?P<region>[a-z0-9]+-[a-z0-9]+)-(?P<zone>[a-z]+)$')
  match = zone_re.match(zone)
  if match is None:
    return None

  gd = match.groupdict()

  return (gd['region'], gd['zone'])


# ----------------------------------------------------------------------------
def connected(error_value: Any) -> Any:
  """decorator for Cluster that checks connection status

  Args:
  error_value: return value on error

  Returns:
  error_value if error connecting, function return value otherwise
  """

  def check(fn):

    def wrapper(self, *args, **kwargs):
      if not self.connected:
        if not self.connect():
          logging.error('error connecting to cluster')
          return error_value
      return fn(self, *args, **kwargs)

    return wrapper

  return check


# ----------------------------------------------------------------------------
def _create_cluster_spec(cluster_name: str, zone: str, node_zones: List[str],
                         resource_limits: dict,
                         release_channel: ReleaseChannel) -> dict:
  """creates cluster spec dictionary

  Args:
  cluster_name: name of cluster
  zone: zone for cluster
  node_locations: zones where nodes can be created
  resource_limits: resource limits dictionary
  release_channel: release channel for cluster

  Returns:
  dictionary
  """

  # see https://cloud.google.com/container-engine/reference/rest/v1/projects.zones.clusters
  cluster_spec = {
      'name': cluster_name,
      'zone': zone,
      'ipAllocationPolicy': {
          'useIpAliases': 'true'
      },
      'enable_tpu': 'true',
      'autoscaling': {
          'enableNodeAutoprovisioning': 'true',
          'autoprovisioningNodePoolDefaults': {
              'oauthScopes': [k.COMPUTE_SCOPE_URL, k.CLOUD_PLATFORM_SCOPE_URL],
          },
          'resourceLimits': resource_limits,
      },
      'nodePools': [{
          'name': 'default-pool',
          'initialNodeCount': '3',
          'config': {
              'oauthScopes': [
                  'https://www.googleapis.com/auth/devstorage.read_only',
                  'https://www.googleapis.com/auth/logging.write',
                  'https://www.googleapis.com/auth/monitoring',
                  'https://www.googleapis.com/auth/service.management.readonly',
                  'https://www.googleapis.com/auth/servicecontrol',
                  'https://www.googleapis.com/auth/trace.append'
              ],
          },
      }],
      'releaseChannel': {
          'channel': release_channel.value
      },
      'locations': node_zones,
  }

  return cluster_spec


# ----------------------------------------------------------------------------
def _cluster_create_request_body(project_id: str, zone: str,
                                 cluster_spec: dict) -> dict:
  '''creates a cluster create request body

  Args:
  project_id: project id for cluster
  zone: zone where cluster will exist
  cluster_spec: dictionary specifying cluster parameters

  Returns:
  cluster creation request body dictionary
  '''

  return {
      'cluster': cluster_spec,
      'parent': 'projects/{}/locations/{}'.format(project_id, zone)
  }


# ----------------------------------------------------------------------------
class Cluster(object):
  """cluster

  This is meant as a thin wrapper around GKE clusters and the raw kubernetes
  python api, mainly to provide a simple interface for the most common
  cluster tasks.
  """

  # --------------------------------------------------------------------------
  def __init__(self, name: Optional[str], project_id: str, zone: str,
               credentials: Credentials):
    self._cluster_client = None
    self._gke_cluster: Optional[GKECluster] = None
    self._core_api: Optional[kubernetes.client.CoreV1Api] = None
    self._batch_api: Optional[kubernetes.client.BatchV1Api] = None
    self._apps_api: Optional[kubernetes.client.AppsV1Api] = None
    self._tpu_api = None
    self.name = name
    self.project_id = project_id
    self.zone = zone
    self.credentials = credentials
    self.connected = False
    return

  # --------------------------------------------------------------------------
  @trap(False)
  def connect(self) -> bool:
    """connects to cluster instance

    Returns:
    True on success, False otherwise
    """

    self.connected = False

    # if gke cluster info already populated, then noop
    # otherwise uses cluster api to get cluster info
    if not self._set_gke_cluster():
      return False

    if self._gke_cluster is None:
      return False

    # resolve our zone in case the wildcard '-' was passed
    self.zone = self._gke_cluster.zone

    # set our name in case None was passed
    self.name = self._gke_cluster.name

    # ok, now we set up the kubernetes api using our cluster info and
    # credentials
    cfg = kubernetes.client.Configuration()
    cfg.host = 'https://{}:443'.format(self._gke_cluster.endpoint)
    cfg.verify_ssl = False  #True #todo: figure out how to do this properly
    #cfg.ssl_ca_cert = c.master_auth.cluster_ca_certificate
    cfg.api_key = {'authorization': 'Bearer ' + self.credentials.token}

    api_client = kubernetes.client.ApiClient(cfg)

    self._core_api = kubernetes.client.CoreV1Api(api_client)
    self._batch_api = kubernetes.client.BatchV1Api(api_client)
    self._apps_api = kubernetes.client.AppsV1Api(api_client)

    self._tpu_api = googleapiclient.discovery.build(
        'tpu', 'v1', credentials=self.credentials, cache_discovery=False)

    # using this as a connection test
    # todo: is there a better way to verify connectivity?
    self.connected = (self._core_api.get_api_resources(async_req=False) is
                      not None)

    return self.connected

  # --------------------------------------------------------------------------
  def _set_gke_cluster(self) -> bool:
    """sets the gke cluster for this instance

    Returns:
    True on success, False otherwise
    """

    if self._gke_cluster is not None:
      return True

    self._cluster_client = ClusterManagerClient(credentials=self.credentials)

    if self._cluster_client is None:
      logging.error('error getting cluster management client')
      return False

    cluster_list = util.get_gke_clusters(self._cluster_client, self.project_id,
                                         self.zone)
    if cluster_list is None:
      return False
    if len(cluster_list) < 1:
      return False

    if self.name is None and len(cluster_list) > 1:
      logging.error('multiple clusters found, please specify:')
      for c in cluster_list:
        logging.info(c.name)
      return False

    if self.name is None:
      self._gke_cluster = cluster_list[0]
      return True

    cluster_dict = dict([(c.name, c) for c in cluster_list])
    if self.name not in cluster_dict:
      logging.error('cluster {} not found'.format(self.name))
      return False

    self._gke_cluster = cluster_dict[self.name]

    return True

  # --------------------------------------------------------------------------
  @staticmethod
  def list(project_id: str,
           creds: Credentials,
           zone: str = '-') -> Optional[List[str]]:
    """gets a list of clusters for given project and zone

    Args:
    project_id: gke project id
    creds: credentials
    zone: zone, - = all zones

    Returns:
    list of cluster names on success, None otherwise
    """

    client = ClusterManagerClient(credentials=creds)

    if client is None:
      logging.error('error getting cluster management client')
      return None

    clusters = util.get_gke_clusters(client, project_id, zone)
    return [c.name for c in clusters] if clusters is not None else None

  # --------------------------------------------------------------------------
  @staticmethod
  def get(name: Optional[str], project_id: str, zone: str,
          creds: Credentials) -> "Optional[Cluster]":
    """factory method for generating Cluster object

    Note that this also calls connect(), so the resulting cluster is
    already connected. If connect fails, then this method returns None.

    Args:
    name: name of cluster, if None, auto-detect
    project_id: project id
    zone: zone, - = all zones

    Returns:
    cluster instance on success, None otherwise
    """

    cluster = Cluster(name=name,
                      project_id=project_id,
                      zone=zone,
                      credentials=creds)

    return cluster if cluster.connect() else None

  # --------------------------------------------------------------------------
  @staticmethod
  def container_limits(
      accelerator: Optional[Accelerator],
      count: int = 1,
      preemptible_tpu: bool = True) -> Optional[Dict[str, int]]:
    """creates container limits dictionary for given accelerator type and count

    Args:
    accelerator: accelerator type
    count: accelerator count
    preemptible_tpu: use preemptible tpus (valid only for v2-8 and v3-8)
                     see: https://cloud.google.com/tpu/docs/preemptible this is
                       ignored for other tpu specs

    Returns:
    None for cpu, limits dictionary for gpu/tpu
    """

    if accelerator is None:  # cpu-only
      return None

    if type(accelerator) == GPU:
      return {k.CONTAINER_RESOURCE_LIMIT_GPU: count}

    # todo: should we validate tpu/count compatibility here, or should we
    #       assume this is done upstream?
    if type(accelerator) == TPU:
      return {
          '/'.join([
              k.CONTAINER_RESOURCE_LIMIT_TPU,
              ('preemptible-' if (preemptible_tpu and count == 8) else '') + accelerator.name.lower(
              )
          ]):
              count
      }

    logging.error('error: invalid accelerator type: {}'.format(
        type(accelerator)))

    return None

  # --------------------------------------------------------------------------
  @staticmethod
  def container_requests(min_cpu: int, min_mem: int) -> Dict[str, str]:
    '''generates container requests

    Args:
    min_cpu: minimum cpu needed, in milli-cpu
    min_mem: minimum memory needed, in MB

    Returns:
    dictionary of requests
    '''

    return {
        k.CONTAINER_RESOURCE_REQUEST_CPU: '{}m'.format(min_cpu),
        k.CONTAINER_RESOURCE_REQUEST_MEM: '{}M'.format(min_mem)
    }

  # --------------------------------------------------------------------------
  @staticmethod
  def template_metadata(
      accelerator: Optional[Accelerator] = None,
      tpu_driver: str = k.DEFAULT_TPU_DRIVER) -> Optional[V1ObjectMeta]:
    """generates template metadata for given accelerator type

    Args:
    accelerator: accelerator type, or None for cpu
    tpu_driver: tpu driver to use

    Returns:
    template metadata necessary for given accelerator
    """

    if type(accelerator) == TPU:
      return V1ObjectMeta(
          annotations={k.TEMPLATE_META_ANNOTATION_TPU_DRIVER: tpu_driver})

    return None

  # --------------------------------------------------------------------------
  @staticmethod
  def node_selector(
      preemptible: bool = True,
      machine_type: Optional[MachineType] = None,
      accelerator: Optional[Accelerator] = None) -> Optional[Dict[str, str]]:
    """gets node selector for given accelerator type and machine spec

    Args:
    preemptible: request preemptible instance
    machine_type: machine type, None = not specified
    accelerator: accelerator, or None for cpu

    Returns:
    node selector dictionary for given criteria
    """

    selector = {}

    if preemptible:
      selector[k.NODE_SELECTOR_PREEMPTIBLE] = 'true'

    if machine_type is not None:
      selector[k.NODE_SELECTOR_INSTANCE_TYPE] = machine_type.value

    # see: https://cloud.google.com/kubernetes-engine/docs/how-to/gpus
    if isinstance(accelerator, GPU):
      selector[
          k.NODE_SELECTOR_GKE_ACCELERATOR] = accelerator.value.lower().replace(
              '_', '-')

    if len(selector) == 0:
      return None

    return selector

  # --------------------------------------------------------------------------
  @staticmethod
  def tolerations(preemptible: bool = True) -> Optional[List[V1Toleration]]:
    """creates tolerations for pod spec

    Args:
    preemptible: tolerate preemptible vm instances

    Returns:
    list of tolerations
    """

    if not preemptible:
      return []

    return [
        V1Toleration(key=k.NODE_SELECTOR_PREEMPTIBLE,
                     operator='Equal',
                     value='true',
                     effect='NoSchedule')
    ]

  # --------------------------------------------------------------------------
  @trap(None)
  @connected(None)
  def pods(self) -> Optional[List[V1Pod]]:
    """gets a list of pods for this cluster

    Note that this filters out the pods in the kube-system namespace

    Returns:
    list of V1Pod instances on success, None otherwise
    """

    if self._core_api is None:
      return None

    # this returns a V1PodList
    rsp = self._core_api.list_pod_for_all_namespaces(watch=False)

    cluster_pods = [
        p for p in rsp.items if p.metadata.namespace != k.KUBE_SYSTEM_NAMESPACE
    ]

    return cluster_pods

  # --------------------------------------------------------------------------
  @trap(None)
  @connected(None)
  def jobs(self) -> Optional[List[V1Job]]:
    """gets a list of jobs for this cluster

    Returns:
    list of V1Job instances on success, None otherwise
    """
    if self._batch_api is None:
      return None

    return self._batch_api.list_job_for_all_namespaces(watch=False).items

  # --------------------------------------------------------------------------
  @trap(None)
  @connected(None)
  def get_job(self, job_name: str) -> Optional[V1Job]:
    '''gets a v1job from the cluster from the given job name'''
    if self._batch_api is None:
      return None

    jobs = self._batch_api.list_job_for_all_namespaces(
        watch=False, field_selector=f'metadata.name={job_name}').items
    if len(jobs) != 1:
      return None
    return jobs[0]

  # --------------------------------------------------------------------------
  @connected(None)
  def delete_job(
      self,
      job_name: str,
      namespace: str = k.DEFAULT_NAMESPACE,
  ) -> bool:
    '''deletes a job from the cluster
    see:
    github.com/kubernetes-client/python/blob/master/kubernetes/docs/BatchV1Api.md#delete_namespaced_job
    github.com/kubernetes-client/python/blob/master/kubernetes/docs/V1Status.md

    Args:
    job_name: name of job to delete

    Returns:
    True on success, False otherwise
    '''
    if self._batch_api is None:
      return False

    try:
      # The propagation_policy arg here is important, as the default is
      # 'Orphan', which deletes the job, but keeps any running pods.
      # By setting this to 'Foreground', then all child pods, etc. get
      # deleted in a cascade, which is what we want here.
      rsp = self._batch_api.delete_namespaced_job(
          name=job_name,
          namespace=namespace,
          propagation_policy='Foreground',
      )
    except Exception as e:
      logging.error(
          f'error deleting job {job_name} from cluster {self.name}: {e}')
      return False

    return True

  # --------------------------------------------------------------------------
  @connected(None)
  def node_pools(self) -> Optional[List[NodePool]]:
    """gets a list of node pools for this cluster

    Returns:
    list of node pools on success, None otherwise
    """

    if self._gke_cluster is None:
      return None

    return self._gke_cluster.node_pools

  # --------------------------------------------------------------------------
  @trap(None, silent=False)
  @connected(None)
  def submit_v1job(
      self,
      job: V1Job,
      namespace: str = k.DEFAULT_NAMESPACE,
  ) -> Optional[V1Job]:
    """submits kubernetes job to cluster

    Args:
    job: job spec
    namespace: kubernetes namespace

    Returns:
    V1Job on success, None otherwise
    """

    if self._batch_api is None:
      return None

    return self._batch_api.create_namespaced_job(namespace=namespace,
                                                 body=job,
                                                 async_req=False,
                                                 pretty=True)

  # --------------------------------------------------------------------------
  @classmethod
  def create_v1job(
      cls,
      job_spec: JobSpec,
      name: str,
      labels: Optional[Dict[str, str]] = None,
  ) -> V1Job:
    '''creates a V1Job from a JobSpec, a job name, and an optional set of labels'''

    name = util.sanitize_job_name(name)

    # todo: sanitize labels
    job_metadata = V1ObjectMeta(generate_name=name + '-')  #, labels=labels)

    return V1Job(api_version=k.BATCH_V1_VERSION,
                 kind='Job',
                 metadata=job_metadata,
                 spec=job_spec.spec)

  # --------------------------------------------------------------------------
  @classmethod
  def create_v1jobs(
      cls,
      job_specs: Iterable[JobSpec],
      name: str,
      labels: Optional[Dict[str, str]] = None,
  ) -> List[V1Job]:
    '''create a list of V1Jobs from a list of JobSpecs'''
    return [
        cls.create_v1job(job_spec=s, name=name, labels=labels)
        for s in job_specs
    ]

  # --------------------------------------------------------------------------
  @trap(None, silent=False)
  @connected(None)
  def submit_job(
      self,
      job_spec: JobSpec,
      name: str,
      labels: Optional[Dict[str, str]] = None,
  ) -> Optional[Job]:
    '''submits a job to the cluster based on the given job spec'''

    v1job = self.create_v1job(job_spec=job_spec, name=name, labels=labels)
    submitted = self.submit_v1job(v1job)
    container = job_spec.spec['template']['spec']['containers'][0]['image']

    if submitted is not None:
      details = {
          'cluster_name': self.name,
          'project_id': self.project_id,
          'cluster_zone': self.zone,
          'job': ApiClient().sanitize_for_serialization(submitted),
      }

      return Job(
          spec=job_spec,
          container=container,
          details=details,
          status=JobStatus.SUBMITTED,
      )

    return None

  # --------------------------------------------------------------------------
  @connected(None)
  def create_simple_job_spec(
      self,
      experiment: Experiment,
      name: str,
      image: str,
      min_cpu: int,
      min_mem: int,
      index: int,
      command: Optional[List[str]] = None,
      env: Dict[str, str] = {},
      accelerator: Optional[Accelerator] = None,
      accelerator_count: int = 1,
      namespace: str = k.DEFAULT_NAMESPACE,
      machine_type: Optional[MachineType] = None,
      preemptible: bool = True,
      preemptible_tpu: bool = True,
      tpu_driver: str = k.DEFAULT_TPU_DRIVER,
      labels: Optional[Dict[str, str]] = None,
      caliban_config: Optional[Dict[str, Any]] = None,
  ) -> Optional[JobSpec]:
    """creates a simple kubernetes job (1 container, 1 pod) JobSpec for this cluster

    Args:
    name: job name
    image: container image url (gcr.io/...)
    min_cpu: minimum cpu needed, in milli-cpu
    min_mem: minimum memory needed, in MB
    command: command to execute, None = container entrypoint
    args: args to pass to command
    env: environment vars for container
    accelerator: accelerator type, None=cpu only
    accelerator_count: accelerator count
    namespace: kubernetes namespace
    machine_type: machine type, None=default for mode (cpu/gpu)
    preemptible: use preemptible instance
    preemptible_tpu: use preemptible tpus
    tpu_driver: tpu driver to use
    labels: user labels to set
    caliban_config: caliban configuration dictionary

    Returns:
    JobSpec on success, None otherwise
    """

    caliban_config = caliban_config or {}
    labels = labels or {}

    launcher_args = um.mlflow_args(
        caliban_config=caliban_config,
        experiment_name=experiment.xgroup.name,
        index=index,
        tags={
            um.PLATFORM_TAG: Platform.GKE.value,
            **labels,
        },
    )

    cmd_args = ce.experiment_to_args(experiment.kwargs, experiment.args)

    # cmd args *must* be last in order for the launcher to pass them through
    args = launcher_args + cmd_args

    # ------------------------------------------------------------------------
    # container

    # tpu/gpu resources
    container_resources = V1ResourceRequirements(
        requests=Cluster.container_requests(min_cpu, min_mem),
        limits=Cluster.container_limits(
            accelerator,
            accelerator_count,
            preemptible_tpu,
        ),
    )

    container_env = [V1EnvVar(name=k, value=v) for k, v in env.items()]

    # this is a simple 1-container, 1-pod job, so we just name the
    # container the same thing (minus the generated suffix) as the job itself
    container = V1Container(
        name=name,
        image=image,
        command=command,
        args=args,
        resources=container_resources,
        env=container_env,
        image_pull_policy='Always',
    )

    # ------------------------------------------------------------------------
    # template

    # todo: should we support anything other than a 'never' restart policy?
    # see this for discussion
    # https://kubernetes.io/docs/concepts/workloads/controllers/jobs-run-to-completion/#pod-backoff-failure-policy

    tolerations = Cluster.tolerations(preemptible=preemptible)

    # backoff count plus 'OnFailure' may be correct here
    template_spec = V1PodSpec(
        restart_policy='Never',
        containers=[container],
        tolerations=tolerations,
        node_selector=Cluster.node_selector(
            preemptible=preemptible,
            machine_type=machine_type,
            accelerator=accelerator,
        ),
        host_ipc=True,
    )

    template = V1PodTemplateSpec(
        metadata=Cluster.template_metadata(
            accelerator=accelerator,
            tpu_driver=tpu_driver,
        ),
        spec=template_spec,
    )

    # ------------------------------------------------------------------------
    # job
    job_spec = V1JobSpec(template=template, backoff_limit=4)

    return JobSpec.get_or_create(
        experiment=experiment,
        spec=ApiClient().sanitize_for_serialization(job_spec),
        platform=Platform.GKE,
    )

  # --------------------------------------------------------------------------
  @connected(None)
  def create_simple_experiment_job_specs(
      self,
      name: str,
      image: str,
      min_cpu: int,
      min_mem: int,
      experiments: Iterable[Experiment],
      command: Optional[List[str]] = None,
      args: Optional[List[str]] = None,
      env: Dict[str, str] = {},
      accelerator: Optional[Accelerator] = None,
      accelerator_count: int = 1,
      namespace: str = k.DEFAULT_NAMESPACE,
      machine_type: Optional[MachineType] = None,
      preemptible: bool = True,
      preemptible_tpu: bool = True,
      tpu_driver: str = k.DEFAULT_TPU_DRIVER,
      labels: Optional[Dict[str, str]] = None,
      caliban_config: Optional[Dict[str, Any]] = None,
  ) -> Iterable[JobSpec]:
    """creates an iterable of JobSpec instances for a set of experiments for
    this cluster

    Args:
    name: job name
    image: container image url (gcr.io/...)
    min_cpu: minimum cpu needed, in milli-cpu
    min_mem: minimum memory needed, in MB
    experiments: experiment list
    command: command to execute, None = container entrypoint
    args: args to pass to command
    env: environment vars for container
    accelerator: accelerator type, None=cpu only
    accelerator_count: accelerator count
    namespace: kubernetes namespace
    machine_type: machine type, None=default for mode (cpu/gpu)
    preemptible: use preemptible instances
    preemptible_tpu: use preemptible tpus
    tpu_driver: tpu driver to use
    labels: user labels to set
    caliban_config: caliban config dict

    Returns:
    JobSpec iterable on success, None otherwise
    """

    job_specs = []
    for index, exp in enumerate(list(experiments)):
      job_specs.append(
          self.create_simple_job_spec(
              experiment=exp,
              name=name,
              image=image,
              min_cpu=min_cpu,
              min_mem=min_mem,
              index=index,
              command=command,
              env=env,
              accelerator=accelerator,
              accelerator_count=accelerator_count,
              namespace=namespace,
              machine_type=machine_type,
              preemptible=preemptible,
              preemptible_tpu=preemptible_tpu,
              tpu_driver=tpu_driver,
              labels=labels,
              caliban_config=caliban_config,
          ))

    return job_specs

  # --------------------------------------------------------------------------
  @staticmethod
  def convert_accel_spec(
      gpu_spec: Optional[GPUSpec], tpu_spec: Optional[TPUSpec]
  ) -> Optional[Tuple[Optional[Accelerator], int]]:
    """converts gpu/tpu spec pair to accelerator,count tuple

    Args:
    gpu_spec: gpu spec
    tpu_spec: tpu spec

    Returns:
    (Accelerator, count) tuple, (none, count) tuple if cpu-only, None on error
    """

    if gpu_spec is not None and tpu_spec is not None:
      logging.error('error: cannot specify both tpu and gpu')
      return None

    # gpu
    if gpu_spec is not None:
      return (gpu_spec.gpu, gpu_spec.count)

    # tpu
    if tpu_spec is not None:
      return (tpu_spec.tpu, tpu_spec.count)

    # cpu
    return (None, 1)

  # --------------------------------------------------------------------------
  @connected(None)
  def dashboard_url(self) -> Optional[str]:
    """returns gke dashboard url for this cluster on success, None otherwise"""
    if self.name is None:
      return None
    return util.dashboard_cluster_url(self.name, self.zone, self.project_id)

  # --------------------------------------------------------------------------
  @connected(None)
  def job_dashboard_url(self, job: V1Job) -> Optional[str]:
    """returns dashboard url for given job

    Args:
    job: job spec

    Returns:
    dashboard url for given job, None on error
    """

    md = job.metadata

    url = '{}/{}/{}'.format(k.DASHBOARD_JOB_URL, self.zone, self.name)
    url += '/{}/{}'.format(md.namespace, md.name)

    return url

  # --------------------------------------------------------------------------
  @connected(None)
  def get_tpu_types(self) -> Optional[List[TPUSpec]]:
    """gets supported tpu types for cluster

    Returns:
    list of supported tpu types on success, None otherwise
    """

    return util.get_zone_tpu_types(self._tpu_api, self.project_id, self.zone)

  # --------------------------------------------------------------------------
  @connected(None)
  def get_gpu_types(self) -> Optional[List[GPUSpec]]:
    """gets supported gpu types for cluster

    Returns:
    list of supported gpu types on success, None otherwise
    """

    container_api = googleapiclient.discovery.build(
        'container', 'v1', credentials=self.credentials, cache_discovery=False)

    # for some reason, autoprovisioning data is not in the _gke_cluster
    # instance, so we query using the container api here
    rsp = container_api.projects().locations().clusters().get(
        name='projects/{}/locations/{}/clusters/{}'.format(
            self.project_id, self.zone, self.name)).execute()

    if rsp is None:
      logging.error('error getting cluster info')
      return None

    # for now we just return the gpu resource limits from the autoprovisioning
    # configuration for the cluster
    # todo: take node pool data into account here?
    if 'autoscaling' not in rsp:
      return None

    if 'resourceLimits' not in rsp['autoscaling']:
      return None

    limits = rsp['autoscaling']['resourceLimits']

    gpu_re = re.compile('^nvidia-tesla-(?P<type>[a-z0-9]+)$')
    gpus = []

    for x in limits:
      match = gpu_re.match(x['resourceType'])
      if match is None:
        continue
      gd = match.groupdict()
      gpus.append(GPUSpec(GPU[gd['type'].upper()], int(x['maximum'])))

    return gpus

  # --------------------------------------------------------------------------
  def validate_gpu_spec(self, gpu_spec: Optional[GPUSpec]) -> bool:
    """validates gpu spec against zone and cluster contraints

    Args
    gpu_spec: gpu spec

    Returns:
    True if valid spec, False otherwise
    """
    if gpu_spec is None:
      return True

    # ------------------------------------------------------------------------
    # validate against zone instance limits
    compute_api = googleapiclient.discovery.build('compute',
                                                  'v1',
                                                  credentials=self.credentials,
                                                  cache_discovery=False)

    zone_gpus = util.get_zone_gpu_types(compute_api, self.project_id, self.zone)

    if zone_gpus is None:
      return False

    gpu_limits = dict([(x.gpu, x.count) for x in zone_gpus])
    if not util.validate_gpu_spec_against_limits(gpu_spec, gpu_limits, 'zone'):
      return False

    # ------------------------------------------------------------------------
    # validate against cluster limits
    available_gpu = self.get_gpu_types()
    if available_gpu is None:
      return False

    gpu_limits = dict([(x.gpu, x.count) for x in available_gpu])
    if not util.validate_gpu_spec_against_limits(gpu_spec, gpu_limits,
                                                 'cluster'):
      return False

    return True

  # --------------------------------------------------------------------------
  @trap(None)
  @connected(None)
  def apply_daemonset(
      self,
      daemonset: V1DaemonSet,
      namespace: str = k.DEFAULT_NAMESPACE) -> Optional[V1DaemonSet]:
    """applies daemonset to cluster

    Args:
    daemonset: daemonset
    namespace: kubernetes namespace

    Returns:
    V1DaemonSet (with status) on success, None otherwise
    """

    if self._apps_api is None:
      return None

    return self._apps_api.create_namespaced_daemon_set(namespace=namespace,
                                                       body=daemonset,
                                                       async_req=False,
                                                       pretty=True)

  # --------------------------------------------------------------------------
  @connected(None)
  def apply_daemonset_from_url(
      self, url: str, parser: Callable[[bytes], dict]) -> Optional[V1DaemonSet]:
    """applies daemonset to cluster from file url

    Args:
    url: url for data
    parser: parser for url data, must convert to dictionary or V1DaemonSet

    Returns:
    V1DaemonSet on success, None otherwise
    """

    response = requests.get(url)
    if response.status_code != requests.codes.ok:
      print('error getting data from {}'.format(url))
      return None

    body = parser(response.content)

    namespace = k.DEFAULT_NAMESPACE
    if 'metadata' in body:
      namespace = body['metadata'].get('namespace', k.DEFAULT_NAMESPACE)

    return self.apply_daemonset(daemonset=body, namespace=namespace)

  # --------------------------------------------------------------------------
  @connected(False)
  def delete(self):
    """delete this cluster

    Returns:
    True on success, False otherwise
    """

    # for some reason we cannot monitor cluster deletion progress, either
    # by using the discovery client or the ClusterManagementClient
    # due to a strange permissions error, which persists despite having
    # complete project ownership IAM privileges
    op = self._cluster_client.delete_cluster(project_id=self.project_id,
                                             zone=self.zone,
                                             cluster_id=self.name)

    print('deleting cluster {}...'.format(self.name))
    print('visit {} to monitor deletion progress'.format(self.dashboard_url()))

    return

  # --------------------------------------------------------------------------
  @connected(None)
  def get_tpu_drivers(self) -> Optional[List[str]]:
    """gets supported tpu drivers for this cluster

    Returns:
    list of supported tpu drivers on success, None otherwise
    """

    return util.get_tpu_drivers(self._tpu_api, self.project_id, self.zone)

  # --------------------------------------------------------------------------
  @connected(None)
  def validate_tpu_driver(self, tpu_driver: str) -> bool:
    """validates tpu driver for this cluster

    Args:
    tpu_driver: tpu driver

    Returns:
    True if valid, False otherwise
    """

    valid_drivers = self.get_tpu_drivers()
    if valid_drivers is None:
      return False

    return tpu_driver in valid_drivers

  # ----------------------------------------------------------------------------
  @staticmethod
  @trap(None, silent=False)
  def create_request(cluster_api: discovery.Resource, creds: Credentials,
                     cluster_name: str, project_id: str, zone: str,
                     release_channel: ReleaseChannel,
                     single_zone: bool) -> Optional[HttpRequest]:
    '''generates cluster create request

    Args:
    cluster_api: cluster api client
    creds: credentials
    cluster_name: name of cluster to create
    project_id: project id
    zone: zone in which to create cluster
          For a single-zone cluster (see below), this zone will contain the
          cluster control plane and all worker nodes. For a multi-zone cluster
          this zone will contain the control plane, but worker nodes can be
          created in any zone in the same region as the control plane.
    release_channel: release channel for cluster
    single_zone: create a single-zone cluster if true, multi-zone otherwise.
                 A single-zone cluster only creates worker nodes in the same
                 zone as the cluster control-plane (specified in the 'zone'
                 argument above), whereas a multi-zone cluster can create
                 worker nodes in every zone in the same region as the
                 cluster control plane. A multi-zone cluster can help
                 job response time when a given zone becomes overburdened.

    Returns:
    HttpRequest on success, None otherwise
    '''

    rz = _parse_zone(zone)
    if rz is None:
      logging.error('invalid zone specified: {}'.format(zone))
      return None

    region, _ = rz

    compute_api = discovery.build('compute',
                                  'v1',
                                  credentials=creds,
                                  cache_discovery=False)

    resource_limits = util.generate_resource_limits(compute_api, project_id,
                                                    region)

    if resource_limits is None:
      logging.error('error generating resource limits')
      return None

    if single_zone:
      node_zones = [zone]
    else:
      node_zones = util.get_zones_in_region(compute_api, project_id, region)

    if node_zones is None:
      logging.error('error getting zones for region {}'.format(region))
      return None

    request_body = _cluster_create_request_body(
        project_id, zone,
        _create_cluster_spec(cluster_name, zone, node_zones, resource_limits,
                             release_channel))

    # see https://cloud.google.com/kubernetes-engine/docs/reference/rest/v1/projects.zones.clusters/create
    return cluster_api.projects().zones().clusters().create(
        projectId=project_id, zone=zone, body=request_body)

  # ----------------------------------------------------------------------------
  @staticmethod
  @trap(None, silent=False)
  def create(cluster_api: discovery.Resource, creds: Credentials,
             request: HttpRequest, project_id: str) -> "Optional[Cluster]":
    '''create cluster

    Note that this is a blocking call.

    Args:
    cluster_api: cluster api client
    cred: credentials
    request: cluster creation http request
    project_id: project id
    zone: zone

    Returns:
    Cluster instance on success, None otherwise
    '''

    daemonset_url = util.nvidia_daemonset_url(NodeImage.COS)
    body = json.loads(request.body)
    zone = body['cluster']['zone']
    cluster_name = body['cluster']['name']

    # execute
    rsp = request.execute()

    if rsp is None:
      logging.error('error: could not create cluster')
      return None

    # wait for creation operation to complete
    operation_name = rsp['name']
    rsp = util.wait_for_operation(
        cluster_api,
        'projects/{}/locations/{}/operations/{}'.format(project_id, zone,
                                                        operation_name))

    if rsp['status'] != OpStatus.DONE.value:
      logging.error('error creating cluster {}!'.format(cluster_name))
      return None

    # get our newly-created cluster
    cluster = Cluster.get(name=cluster_name,
                          project_id=project_id,
                          zone=zone,
                          creds=creds)

    if cluster is None:
      logging.error(
          'error: unable to connect to cluster {}'.format(cluster_name))
      logging.error('nvidia-driver daemonset not applied, to do this manually:')
      logging.error('kubectl apply -f {}'.format(daemonset_url))
      return None

    logging.info('created cluster {} successfully'.format(cluster_name))
    logging.info('applying nvidia driver daemonset...')

    rsp = cluster.apply_daemonset_from_url(
        daemonset_url, lambda x: yaml.load(x, Loader=yaml.FullLoader))

    return cluster
