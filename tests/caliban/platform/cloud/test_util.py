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

import re

import hypothesis.strategies as st
from hypothesis import given

import caliban.platform.cloud.util as u


def non_empty_dict(vgen):
  return st.dictionaries(st.text(), vgen, min_size=1)


def test_key_value_label():
  """unit tests for specific cases of key and value label conversion."""
  assert "face" == u.key_label("--face")
  assert "fa_ce" == u.key_label("------fA.!! ce")

  # Empty string roundtrips.
  assert "" == u.key_label("")
  assert "" == u.value_label("")

  # keys can't have leading digits, just letters, so we append a k.
  assert "k0helper" == u.key_label("--0helper")

  # values CAN have leading digits and underscores.
  assert "0helper" == u.value_label("--0helper")
  assert "_helper" == u.value_label("--_helper")


def assert_valid_label(label):
  """Assertion that passes if the supplied string is a valid label by all the
  rules of Cloud.

  """
  assert len(label) <= 63

  if label != "":
    # check that the output has only lowercase, letters, dashes or
    # underscores.
    assert re.match('^[a-z0-9_-]+$', label)


def assert_valid_key_label(k):
  """Assertion that passes if the input is a valid key by all the rules of
  Cloud.

  """
  assert_valid_label(k)
  if k != "":
    assert k[0].isalpha()


@given(st.text(min_size=1))
def test_valid_key_label(s):
  cleaned = u.key_label(s)
  assert_valid_key_label(cleaned)


@given(st.text(min_size=1))
def test_valid_value_label(s):
  cleaned = u.value_label(s)
  assert_valid_label(cleaned)


def assert_script_args_to_labels(s, m):
  """Assertion that passes if the supplied string of arguments parses to a
  dictionary that equals the supplied m, representing the expected kv pairs.

  """
  parsed_args = u.script_args_to_labels(s.split(" "))
  assert parsed_args == m


def test_script_args_to_labels():
  """unit tests of our script_args_to_labels function behavior."""

  # Args like --!!! that parse keys to the empty string should not make it
  # through.
  assert_script_args_to_labels("--lr 1 --!!! 2 --face 3", {
      "lr": "1",
      "face": "3"
  })

  # Duplicates get overwritten.
  assert_script_args_to_labels("--lr 1 --lr 2", {"lr": "2"})

  assert_script_args_to_labels("--LR 1 --item-label --fa!!ce cake --a", {
      "lr": "1",
      "item-label": "",
      "face": "cake",
      "a": "",
  })

  # Multiple values are dropped for now, for the purpose of creating labels.
  assert_script_args_to_labels("--lr 1 2 3 --item_underscoRE!! --face cake --a",
                               {
                                   "lr": "1",
                                   "item_underscore": "",
                                   "face": "cake",
                                   "a": "",
                               })

  assert_script_args_to_labels("--face", {"face": ""})

  # single arguments get ignore if they're not boolean flags.
  assert_script_args_to_labels("face", {})


def test_sanitize_labels_kill_empty():
  """Keys that are sanitized to the empty string should NOT make it through."""
  assert {} == u.sanitize_labels([["--!!", "face"]])


@given(
    st.one_of(non_empty_dict(st.text()),
              st.lists(st.tuples(st.text(), st.text()))))
def test_sanitize_labels(pairs):
  """Test that any input we could possibly be provided, as long as it parses into
  kv pairs, will only make it into a dict of labels if it's properly
  sanitized.

  Checks that the functions works for dicts OR for lists of pairs.

  """
  for k, v in u.sanitize_labels(pairs).items():
    assert_valid_key_label(k)
    assert_valid_label(v)


@given(st.lists(st.tuples(st.text(), st.text())))
def test_sanitize_labels_second_noop(pairs):
  """Test that passing the output of sanitize_labels back into the function
  returns its input. Sanitizing a set of sanitized kv pairs should have no
  effect.

  """
  once = u.sanitize_labels(pairs)
  twice = u.sanitize_labels(once)
  assert once == twice
