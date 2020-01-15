"""constants for gke"""

from caliban.config import JobMode, DEFAULT_MACHINE_TYPE
from caliban.cloud.types import GPUSpec, GPU

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
TEMPLATE_META_ANNOTATION_TPU_DRIVER = 'tf-version.cloud-tpus.google.com'
DEFAULT_TPU_DRIVER = '1.14'
ZONE_DEFAULT = '-'  # all zones
DEFAULT_MACHINE_TYPE_CPU = DEFAULT_MACHINE_TYPE[JobMode.CPU].value
DEFAULT_MACHINE_TYPE_GPU = DEFAULT_MACHINE_TYPE[JobMode.GPU].value
DEFAULT_GPU_SPEC = GPUSpec(GPU.P100, 1)
DASHBOARD_JOB_URL = 'https://pantheon.corp.google.com/kubernetes/job'
DASHBOARD_CLUSTER_URL = 'https://pantheon.corp.google.com/kubernetes/clusters/details'
MAX_GB_PER_CPU = 64
DEFAULT_CLUSTER_NAME = 'blueshift'

# ----------------------------------------------------------------------------
# The following urls specify kubernetes daemonsets that apply the appropriate
# nvidia drivers to auto-created gpu instances. If this is not running, then your
# gpu jobs will mysteriously fail to schedule, and you will be sad.
# see https://cloud.google.com/kubernetes-engine/docs/how-to/gpus#installing_drivers

# daemonset for COS instances
NVIDIA_DRIVER_COS_DAEMONSET_URL = 'https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml'

# daemonset for Ubuntu instances
NVIDIA_DRIVER_UBUNTU_DAEMONSET_URL = 'https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/ubuntu/daemonset-preloaded.yaml'
