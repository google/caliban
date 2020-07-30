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

import itertools
import json
import os
import uuid
from collections import OrderedDict
from enum import Enum
from typing import Union

import hypothesis.strategies as st
from hypothesis import given

import caliban.util as u
import pytest

text_set = st.sets(st.text(), min_size=1)
ne_text_set = st.sets(st.text(min_size=1), min_size=1)


def non_empty_dict(vgen):
  return st.dictionaries(st.text(), vgen, min_size=1)


@given(ne_text_set, ne_text_set)
def test_enum_vals(ks, vs):
  """Setup ensures that the values are unique."""
  m = dict(zip(ks, vs))
  enum = Enum('TestEnum', m)

  # enum_vals returns the values from the enum.
  assert list(m.values()) == u.enum_vals(enum)


def test_resource_path():
  resource_dir = u.resource("")
  test_path = f"{uuid.uuid1()}.json"
  full_path = os.path.join(resource_dir, test_path)

  # Before writing any data, we get None back.
  assert u.resource(test_path) is None

  # Now write some data...
  resource_data = {"apt_packages": ["face"]}
  with open(full_path, 'w') as f:
    json.dump(resource_data, f)

  # now we see the full path.
  assert u.resource(test_path) == full_path

  os.remove(full_path)

  # Just for fun, check that we've deleted it.
  assert u.resource(test_path) is None


def test_any_of_unit():
  MyEnum = Enum('MyEnum', {"a": "a_string", "b": "b_string"})
  SecondEnum = Enum('SecondEnum', {"c": "c_cake", "d": "d_face"})
  SomeEnum = Union[MyEnum, SecondEnum]

  # Asking for a value not in ANY enum raises a value error.
  with pytest.raises(ValueError):
    u.any_of("face", SomeEnum)


@given(ne_text_set, ne_text_set, ne_text_set, ne_text_set)
def test_any_of(k1, v1, k2, v2):
  m1 = dict(zip(k1, v1))
  m2 = dict(zip(k2, v2))
  enum1 = Enum('enum1', m1)
  enum2 = Enum('enum2', m2)
  union = Union[enum1, enum2]

  # If the item appears in the first map any_of will return it.
  for k, v in m1.items():
    assert u.any_of(v, union) == enum1(v)

  for k, v in m2.items():
    # If a value from the second enum appears in enum1 any_of will return it;
    # else, it'll return the value from enum2.
    try:
      expected = enum1(v)
    except ValueError:
      expected = enum2(v)

    assert u.any_of(v, union) == expected


def test_dict_product():
  input_m = OrderedDict([("a", [1, 2, 3]), ("b", [4, 5]), ("c", "d")])
  result = list(u.dict_product(input_m))

  expected = [{
      'a': 1,
      'b': 4,
      'c': 'd'
  }, {
      'a': 1,
      'b': 5,
      'c': 'd'
  }, {
      'a': 2,
      'b': 4,
      'c': 'd'
  }, {
      'a': 2,
      'b': 5,
      'c': 'd'
  }, {
      'a': 3,
      'b': 4,
      'c': 'd'
  }, {
      'a': 3,
      'b': 5,
      'c': 'd'
  }]

  assert result == expected


@given(st.dictionaries(st.text(), st.text()),
       st.dictionaries(st.text(), st.text()))
def test_merge(m1, m2):
  merged = u.merge(m1, m2)

  # Every item from the second map should be in the merged map.
  for k, v in m2.items():
    assert merged[k] == v

  # Every item from the first map should be in the merged map, OR, if it
  # shares a key with m2, m2's value will have bumped it.
  for k, v in m1.items():
    assert merged[k] == m2.get(k, v)


def test_flipm_unit():
  m = {"a": {1: "a_one", 2: "a_two"}, "b": {1: "b_one", 3: "b_three"}}
  expected = {
      1: {
          "a": "a_one",
          "b": "b_one"
      },
      2: {
          "a": "a_two"
      },
      3: {
          "b": "b_three"
      }
  }

  # Flipping does what we expect!
  assert u.flipm(m) == expected


@given(
    st.dictionaries(st.text(), st.dictionaries(st.text(), st.text(),
                                               min_size=1)))
def test_flipm(m):
  # As long as an inner dictionary isn't empty, flipping is invertible.
  assert m == u.flipm(u.flipm(m))


@given(st.sets(st.text()))
def test_flipm_empty_values(ks):
  """Flipping a dictionary with empty values always equals the empty map."""
  m = u.dict_by(ks, lambda k: {})
  assert {} == u.flipm(m)


def test_invertm_unit():
  m = {"a": [1, 2, 3], "b": [2, 3, 4]}
  expected = {
      1: {"a"},
      2: {"a", "b"},
      3: {"a", "b"},
      4: {"b"},
  }
  assert u.invertm(m) == expected


@given(non_empty_dict(non_empty_dict(text_set)))
def test_reorderm(m):

  def invert_inner(d):
    return {k: u.invertm(v) for k, v in d.items()}

  flipped = u.flipm(m)

  # flipping the inner map.
  assert u.reorderm(m, (0, 2, 1)) == invert_inner(m)

  # Flipping the outer keys is equivalent to calling flipm once.
  assert u.reorderm(m, (1, 0, 2)) == flipped

  # Reordering the inner keys is equiv to flipping the outer keys the
  # flipping the new inner dictionary.
  assert u.reorderm(m, (1, 2, 0)) == invert_inner(flipped)

  # Flipping again brings the original list entry out.
  assert u.reorderm(m, (2, 1, 0)) == u.flipm(invert_inner(flipped))


@given(non_empty_dict(text_set))
def test_invertm(m):
  assert m == u.invertm(u.invertm(m))


@given(st.sets(st.text()))
def test_dict_by(xs):
  """dict_by should apply a function to each item in a set to generate the values
  of the returned dict.

  """
  m = u.dict_by(xs, len)

  # every value is properly constructed
  for k, v in m.items():
    assert len(k) == v

  # the key set of the dict is equal to the incoming original set.
  assert set(m.keys()) == xs


@given(st.lists(st.integers()), st.integers(min_value=1, max_value=500))
def test_n_chunks(xs, n):
  singletons = list(map(lambda x: [x], xs))

  # If the chunks equal the length we get all singletons.
  assert u.n_chunks(xs, len(xs)) == singletons

  # one chunk returns a single singleton.
  assert u.n_chunks(xs, 1) == [xs]

  sharded = u.n_chunks(xs, n)
  recombined = list(itertools.chain(*sharded))

  # The ordering might not be the same, but the total number of items is the
  # same if we break down and recombine.
  assert len(recombined) == len(xs)

  # And the items are equal too.
  assert set(xs) == set(recombined)


def test_chunks_below_limit():
  xs = [0, 1, 2, 3, 4, 5]

  # Below the limit, there's no breakdown.
  assert [xs] == u.chunks_below_limit(xs, 100)

  # Below the limit, there's no breakdown.
  shards = [[0, 2, 4], [1, 3, 5]]
  assert shards == u.chunks_below_limit(xs, 5)

  # You can recover the original list by zipping together the shards (if they
  # happen to be equal in length, as here.)
  assert xs == list(itertools.chain(*list(zip(*shards))))


@given(st.lists(st.integers(), min_size=1))
def test_partition_first_items(xs):
  """retrieving the first item of each grouping recovers the original list."""
  rt = list(map(lambda pair: pair[0], u.partition(xs, 1)))
  assert rt == xs


@given(st.lists(st.integers(), min_size=1))
def test_partition_by_one_gives_singletons(xs):
  """Partition by 1 gives a list of singletons."""
  singletons = list(u.partition(xs, 1))
  assert singletons == [[x] for x in xs]


@given(st.lists(st.integers(), min_size=1), st.integers(min_value=0))
def test_partition_by_big_gives_singleton(xs, n):
  """partitioning by a number >= the list length returns a singleton containing
  just the list.

  """
  one_entry = list(u.partition(xs, len(xs) + n))
  assert one_entry == [xs]


def test_partition():
  """Various unittests of partition."""

  # partitioning by 1 generates singletons.
  assert list(u.partition([1, 2, 3, 4, 5], 1)) == [[1], [2], [3], [4], [5]]

  # partition works into groups of 2
  assert list(u.partition([1, 2, 3, 4], 2)) == [[1, 2], [2, 3], [3, 4]]

  # >= case
  assert list(u.partition([1, 2, 3], 3)), [[1, 2, 3]]
  assert list(u.partition([1, 2, 3], 10)) == [[1, 2, 3]]
