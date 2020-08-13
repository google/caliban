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
"""unit tests for gke utilities"""
import unittest

from datetime import datetime
import hypothesis.strategies as st
from hypothesis import given
from kubernetes.client import V1Job, V1JobStatus

import caliban.platform.gke.types as gt
from caliban.platform.gke.types import ReleaseChannel, JobStatus


# ----------------------------------------------------------------------------
class TypesTestSuite(unittest.TestCase):
  """tests for caliban.platform.gke.types"""

  # --------------------------------------------------------------------------
  @given(st.from_regex('\A(?!UNSPECIFIED\Z|RAPID\Z|REGULAR\Z|STABLE\Z).*\Z'),
         st.sampled_from(ReleaseChannel))
  def test_release_channel(self, invalid: str, valid: ReleaseChannel):
    '''test ReleaseChannel'''

    with self.assertRaises(ValueError) as e:
      x = ReleaseChannel(invalid)

    self.assertEqual(valid, ReleaseChannel(valid.value))


# ----------------------------------------------------------------------------
def test_job_status():
  for s in JobStatus:
    terminal = s.is_terminal()
    if s.name in ['FAILED', 'SUCCEEDED', 'UNAVAILABLE']:
      assert terminal
    else:
      assert not terminal

  # completed jobs
  status = V1JobStatus(completion_time=datetime.now(), succeeded=1)
  job_info = V1Job(status=status)
  job_status = JobStatus.from_job_info(job_info)
  assert job_status == JobStatus.SUCCEEDED

  status = V1JobStatus(completion_time=datetime.now(), succeeded=0)
  job_info = V1Job(status=status)
  job_status = JobStatus.from_job_info(job_info)
  assert job_status == JobStatus.FAILED

  # active jobs
  status = V1JobStatus(completion_time=None, active=1)
  job_info = V1Job(status=status)
  job_status = JobStatus.from_job_info(job_info)
  assert job_status == JobStatus.RUNNING

  # pending jobs
  status = V1JobStatus(completion_time=None, active=0)
  job_info = V1Job(status=status)
  job_status = JobStatus.from_job_info(job_info)
  assert job_status == JobStatus.PENDING

  # unknown state
  status = V1JobStatus()
  job_info = V1Job(status=status)
  job_status = JobStatus.from_job_info(job_info)
  assert job_status == JobStatus.STATE_UNSPECIFIED

  job_info = V1Job()
  job_status = JobStatus.from_job_info(job_info)
  assert job_status == JobStatus.STATE_UNSPECIFIED

  job_status = JobStatus.from_job_info(None)
  assert job_status == JobStatus.STATE_UNSPECIFIED
