"""gke utility routines"""

from typing import Dict, List, Optional
import logging
from urllib.parse import urlencode

import caliban.gke.constants as k
from caliban.gke.types import NodeImage
from caliban.cloud.types import (GPU, GPUSpec)

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
    logging.error(
        f'unsupported gpu type {gpu_spec.gpu.name}. ' +
        f'Supported types for {limit_type}: {[g.name for g in gpu_limits]}')
    return False

  if gpu_spec.count > gpu_limits[gpu_spec.gpu]:
    logging.error(
        f'error: requested {gpu_spec.gpu.name} gpu count {gpu_spec.count} unsupported,'
        + f' {limit_type} max = {gpu_limits[gpu_spec.gpu]}')
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
  return f'{k.DASHBOARD_CLUSTER_URL}/{zone}/{cluster_id}?{query}'
