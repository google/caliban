import unittest
from argparse import ArgumentTypeError
from typing import (Any, Callable, Dict, Iterable, List, NamedTuple, Optional,
                    Set, Tuple, Union)

import hypothesis.strategies as st
from hypothesis import given

import caliban.cloud.types as ct


class TypesTestSuite(unittest.TestCase):
  """Tests for caliban.cloud.types."""

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
    self.assertEquals(ct.MachineType.standard_8,
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

    # Valid!
    self.assertEqual(ct.GPUSpec(ct.GPU.V100, 8), ct.GPUSpec.parse_arg("8xV100"))
