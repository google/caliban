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
"""constants for gke"""

import re

from caliban.config import DEFAULT_MACHINE_TYPE, JobMode
from caliban.platform.cloud.types import GPU, GPUSpec
from caliban.platform.gke.types import ReleaseChannel

COMPUTE_SCOPE_URL = 'https://www.googleapis.com/auth/compute'
COMPUTE_READONLY_SCOPE_URL = 'https://www.googleapis.com/auth/compute.readonly'
CLOUD_PLATFORM_SCOPE_URL = 'https://www.googleapis.com/auth/cloud-platform'
KUBE_SYSTEM_NAMESPACE = 'kube-system'
DEFAULT_NAMESPACE = 'default'
BATCH_V1_VERSION = 'batch/v1'
NODE_SELECTOR_GKE_ACCELERATOR = 'cloud.google.com/gke-accelerator'
NODE_SELECTOR_INSTANCE_TYPE = 'beta.kubernetes.io/instance-type'
NODE_SELECTOR_PREEMPTIBLE = 'cloud.google.com/gke-preemptible'
CONTAINER_RESOURCE_LIMIT_TPU = 'cloud-tpus.google.com'
CONTAINER_RESOURCE_LIMIT_GPU = 'nvidia.com/gpu'
CONTAINER_RESOURCE_REQUEST_CPU = 'cpu'
CONTAINER_RESOURCE_REQUEST_MEM = 'memory'
TEMPLATE_META_ANNOTATION_TPU_DRIVER = 'tf-version.cloud-tpus.google.com'
DEFAULT_TPU_DRIVER = '1.14'
ZONE_DEFAULT = '-'  # all zones
DEFAULT_MACHINE_TYPE_CPU = DEFAULT_MACHINE_TYPE[JobMode.CPU].value
DEFAULT_MACHINE_TYPE_GPU = DEFAULT_MACHINE_TYPE[JobMode.GPU].value
DEFAULT_GPU_SPEC = GPUSpec(GPU.P100, 1)
DASHBOARD_JOB_URL = 'https://console.cloud.google.com/kubernetes/job'
DASHBOARD_CLUSTER_URL = 'https://console.cloud.google.com/kubernetes/clusters/details'
MAX_GB_PER_CPU = 64
DEFAULT_CLUSTER_NAME = 'blueshift'
VALID_JOB_FILE_EXT = ('.yaml', '.json')
DEFAULT_RELEASE_CHANNEL = ReleaseChannel.REGULAR
CLUSTER_API_VERSION = 'v1beta1'

# default min_cpu for gpu/tpu -accelerated jobs (in milli-cpu)
DEFAULT_MIN_CPU_ACCEL = 1500
# default min_cpu for cpu-only jobs (in milli-cpu)
DEFAULT_MIN_CPU_CPU = 31000

# default min_mem for gpu/tpu jobs (in MB)
DEFAULT_MIN_MEM_ACCEL = 7000
#default min_mem for cpu-only jobs (in MB)
DEFAULT_MIN_MEM_CPU = 25000

# ----------------------------------------------------------------------------
# The following urls specify kubernetes daemonsets that apply the appropriate
# nvidia drivers to auto-created gpu instances. If this is not running, then your
# gpu jobs will mysteriously fail to schedule, and you will be sad.
# see https://cloud.google.com/kubernetes-engine/docs/how-to/gpus#installing_drivers

# daemonset for COS instances
NVIDIA_DRIVER_COS_DAEMONSET_URL = 'https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml'

# daemonset for Ubuntu instances
NVIDIA_DRIVER_UBUNTU_DAEMONSET_URL = 'https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/ubuntu/daemonset-preloaded.yaml'

# ----------------------------------------------------------------------------
DNS_1123_RE = re.compile('\A[a-z0-9]([a-z0-9\-\.]*[a-z0-9])?\Z')
