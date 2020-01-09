"""types relevant to gke"""

from enum import Enum
from typing import Set

# Node image types
# see https://cloud.google.com/kubernetes-engine/docs/concepts/node-images
NodeImage = Enum(
    'NODE_IMAGE', {
        'COS': 'cos',
        'UBUNTU': 'ubuntu',
        'COS_CONTAINERD': 'cos_containerd',
        'UBUNTU_CONTAINERD': 'ubuntu_containerd'
    })
