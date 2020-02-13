"""unit tests for gke utilities"""
import unittest

import hypothesis.strategies as st
from hypothesis import given, settings
from typing import Dict, List, Any
import re

from caliban.gke.types import ReleaseChannel


# ----------------------------------------------------------------------------
class TypesTestSuite(unittest.TestCase):
  """tests for caliban.gke.types"""

  # --------------------------------------------------------------------------
  @given(st.from_regex('\A(?!UNSPECIFIED\Z|RAPID\Z|REGULAR\Z|STABLE\Z).*\Z'),
         st.sampled_from(ReleaseChannel))
  def test_release_channel(self, invalid: str, valid: ReleaseChannel):
    '''test ReleaseChannel'''

    with self.assertRaises(ValueError) as e:
      x = ReleaseChannel(invalid)

    self.assertEqual(valid, ReleaseChannel(valid.value))

    return
