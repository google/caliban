"""unit tests for gke utilities"""
import unittest
import hypothesis.strategies as st
from hypothesis import given
from typing import Dict, List

import caliban.cloud.types as ct
import caliban.gke
import caliban.gke.utils as utils
from caliban.gke.types import NodeImage


# ----------------------------------------------------------------------------
class UtilsTestSuite(unittest.TestCase):
  """tests for caliban.gke.utils"""

  # --------------------------------------------------------------------------
  @given(
      st.lists(
          st.integers(min_value=0, max_value=4),
          min_size=len(ct.GPU),
          max_size=len(ct.GPU)), st.sampled_from(ct.GPU),
      st.integers(min_value=1, max_value=8))
  def test_validate_gpu_spec_against_limits(
      self,
      limits: List[int],
      gpu_type: ct.GPU,
      count: int,
  ):
    """test gpu validation against limits"""

    gpu_list = [g for g in ct.GPU]
    gpu_limits = dict([
        (gpu_list[i], limits[i]) for i in range(len(limits)) if limits[i]
    ])
    spec = ct.GPUSpec(gpu_type, count)
    valid = utils.validate_gpu_spec_against_limits(spec, gpu_limits, 'test')

    # to see this output use the --nocapture flag in nosetests
    print(f'gpu_limits: {dict([(k.name, v) for k,v in gpu_limits.items()])}, ' +
          f'gpu: {spec.gpu.name}, count: {spec.count}, valid: {valid}')

    if spec.gpu not in gpu_limits:
      self.assertFalse(valid)
    else:
      self.assertTrue(valid == (spec.count <= gpu_limits[spec.gpu]))

    return

  # --------------------------------------------------------------------------
  def test_nvidia_daemonset_url(self):
    """test nvidia driver daemonset url generation"""
    VALID_NODE_IMAGES = [NodeImage.COS, NodeImage.UBUNTU]

    for n in NodeImage:
      url = utils.nvidia_daemonset_url(n)

      if n in VALID_NODE_IMAGES:
        self.assertIsNotNone(url)
      else:
        self.assertIsNone(url)

    return
