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
from argparse import ArgumentTypeError

import hypothesis.strategies as st
from hypothesis import given

import caliban.platform.cloud.types as ct


class TypesTestSuite(unittest.TestCase):
  """Tests for caliban.platform.cloud.types."""

  @given(st.integers(min_value=0, max_value=40),
         st.sampled_from(list(ct.GPU) + list(ct.TPU)))
  def test_validate_accelerator_count(self, i, accel):
    valid_counts = ct.accelerator_counts(accel)
    if i in valid_counts:
      self.assertEqual(i, ct.validate_accelerator_count(accel, i))
    else:
      with self.assertRaises(ArgumentTypeError):
        ct.validate_accelerator_count(accel, i)

  def test_parse_machine_type(self):
    """Test that strings parse into machine types using the Google Cloud strings,
    NOT the name string for the enum.

    """
    self.assertEqual(ct.MachineType.standard_8,
                     ct.parse_machine_type("n1-standard-8"))

    with self.assertRaises(ArgumentTypeError):
      ct.parse_machine_type("random-string")

  def test_gpuspec_parse_arg(self):
    with self.assertRaises(ArgumentTypeError):
      # invalid format string, no x separator.
      ct.GPUSpec.parse_arg("face")

    with self.assertRaises(ArgumentTypeError):
      # Invalid number.
      ct.GPUSpec.parse_arg("randomxV100")

    with self.assertRaises(ArgumentTypeError):
      # invalid GPU type.
      ct.GPUSpec.parse_arg("8xNONSTANDARD")

    with self.assertRaises(ArgumentTypeError):
      # Invalid number for the valid GPU type.
      ct.GPUSpec.parse_arg("15xV100")

    self.assertEqual(ct.GPUSpec(ct.GPU.V100, 7),
                     ct.GPUSpec.parse_arg("7xV100", validate_count=False))

    # Valid!
    self.assertEqual(ct.GPUSpec(ct.GPU.V100, 8), ct.GPUSpec.parse_arg("8xV100"))

  def test_tpuspec_parse_arg(self):
    with self.assertRaises(ArgumentTypeError):
      # invalid format string, no x separator.
      ct.TPUSpec.parse_arg("face")

    with self.assertRaises(ArgumentTypeError):
      # Invalid number.
      ct.TPUSpec.parse_arg("randomxV3")

    with self.assertRaises(ArgumentTypeError):
      # invalid TPU type.
      ct.TPUSpec.parse_arg("8xNONSTANDARD")

    with self.assertRaises(ArgumentTypeError):
      # Invalid number for the valid TPU type.
      ct.TPUSpec.parse_arg("15xV3")

    self.assertEqual(ct.TPUSpec(ct.TPU.V3, 7),
                     ct.TPUSpec.parse_arg("7xV3", validate_count=False))

    # Valid!
    self.assertEqual(ct.TPUSpec(ct.TPU.V3, 8), ct.TPUSpec.parse_arg("8xV3"))
