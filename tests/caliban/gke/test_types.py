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
