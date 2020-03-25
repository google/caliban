"""types relevant to gke"""

from enum import Enum
from typing import NamedTuple, Optional

from google.auth.credentials import Credentials

# ----------------------------------------------------------------------------
# Node image types
# see https://cloud.google.com/kubernetes-engine/docs/concepts/node-images
NodeImage = Enum(
    'NODE_IMAGE', {
        'COS': 'cos',
        'UBUNTU': 'ubuntu',
        'COS_CONTAINERD': 'cos_containerd',
        'UBUNTU_CONTAINERD': 'ubuntu_containerd'
    })

# ----------------------------------------------------------------------------
# GKE operation status, see:
# https://cloud.google.com/kubernetes-engine/docs/reference/rest/v1/projects.locations.operations
OpStatus = Enum(
    'OP_STATUS', {
        'STATUS_UNSPECIFIED': 'STATUS_UNSPECIFIED',
        'PENDING': 'PENDING',
        'RUNNING': 'RUNNING',
        'DONE': 'DONE',
        'ABORTING': 'ABORTING'
    })

# ----------------------------------------------------------------------------
# Credentials data (credentials, project id)
CredentialsData = NamedTuple("CredentialsData",
                             [("credentials", Optional[Credentials]),
                              ("project_id", Optional[str])])

# ----------------------------------------------------------------------------
# GKE release channel, see:
# https://cloud.google.com/kubernetes-engine/docs/concepts/release-channels
# https://cloud.google.com/kubernetes-engine/docs/reference/rest/v1beta1/projects.locations.clusters#Cluster.ReleaseChannel
# https://cloud.google.com/kubernetes-engine/docs/reference/rest/v1beta1/projects.locations.clusters#channel
ReleaseChannel = Enum(
    'RELEASE_CHANNEL', {
        'UNSPECIFIED': 'UNSPECIFIED',
        'RAPID': 'RAPID',
        'REGULAR': 'REGULAR',
        'STABLE': 'STABLE'
    })
