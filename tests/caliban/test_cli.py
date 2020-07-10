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

import unittest

import caliban.cli as c
import caliban.platform.cloud.types as ct
from caliban.config import JobMode


class CLITestSuite(unittest.TestCase):
  """Tests for caliban.cli."""

  def test_job_mode(self):
    """Tests for all possible combinations of the three arguments to
    resolve_job_mode.

    """
    gpu_spec = ct.GPUSpec(ct.GPU.P100, 4)
    tpu_spec = ct.TPUSpec(ct.TPU.V2, 8)

    def assertMode(expected_mode, use_gpu, gpu_spec, tpu_spec):
      mode = c._job_mode(use_gpu, gpu_spec, tpu_spec)
      self.assertEqual(mode, expected_mode)

    # --nogpu and no override.
    assertMode(JobMode.CPU, False, None, None)

    # TPU doesn't need GPUs
    assertMode(JobMode.CPU, False, None, tpu_spec)

    # Default GPUSpec filled in.
    assertMode(JobMode.GPU, True, None, None)

    # Explicit GPU spec, so GPU gets attached.
    assertMode(JobMode.GPU, True, gpu_spec, None)
    assertMode(JobMode.GPU, True, gpu_spec, tpu_spec)

    # If NO explicit GPU is supplied but a TPU is supplied, execute in CPU
    # mode, ie, don't attach a GPU.
    assertMode(JobMode.CPU, True, None, tpu_spec)

    # explicit GPU spec is incompatible with --nogpu in both of the following
    # cases, irrespective of TPU spec.
    with self.assertRaises(AssertionError):
      c._job_mode(False, gpu_spec, None)

    with self.assertRaises(AssertionError):
      c._job_mode(False, gpu_spec, tpu_spec)
