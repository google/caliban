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
"""types relevant to gke"""

from enum import Enum
from typing import NamedTuple, Optional

from google.auth.credentials import Credentials
from kubernetes.client import V1Job

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


# ----------------------------------------------------------------------------
class JobStatus(Enum):
  '''gke job status'''
  STATE_UNSPECIFIED = 0
  PENDING = 1
  RUNNING = 2
  FAILED = 3
  SUCCEEDED = 4
  UNAVAILABLE = 5

  def is_terminal(self) -> bool:
    return self.name in ['FAILED', 'SUCCEEDED', 'UNAVAILABLE']

  @classmethod
  def from_job_info(cls, job_info: V1Job) -> "JobStatus":
    if job_info is None:
      return JobStatus.STATE_UNSPECIFIED

    if job_info.status is None:
      return JobStatus.STATE_UNSPECIFIED

    # completed
    if job_info.status.completion_time is not None:
      if job_info.status.succeeded is not None:
        if job_info.status.succeeded > 0:
          return JobStatus.SUCCEEDED
        else:
          return JobStatus.FAILED

    # active/pending
    if job_info.status.active is not None:
      if job_info.status.active > 0:
        return JobStatus.RUNNING
      else:
        return JobStatus.PENDING

    # unknown
    return JobStatus.STATE_UNSPECIFIED
