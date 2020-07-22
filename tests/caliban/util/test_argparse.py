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

from collections import OrderedDict

import caliban.util.argparse as ua


def test_expand_args():
  m = OrderedDict([("a", "item"), ("b", None), ("c", "d")])
  expanded = ua.expand_args(m)

  # None is excluded from the results.
  assert expanded == ["a", "item", "b", "c", "d"]


def test_is_key():
  """A key is anything that starts with a dash; nothing else!

  """
  assert ua.is_key("--face")
  assert ua.is_key("-f")
  assert not ua.is_key("")
  assert not ua.is_key("face")
  assert not ua.is_key("f")

  # this should never happen, but what the heck, why not test that it's a
  # fine thing, accepted yet strange.
  assert ua.is_key("-----face")
