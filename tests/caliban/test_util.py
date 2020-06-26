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

import io
import itertools
import re
import unittest
from collections import OrderedDict
from enum import Enum
from typing import Union

import hypothesis.strategies as st
from hypothesis import given
from tqdm._utils import _term_move_up

import caliban.util as u

text_set = st.sets(st.text(), min_size=1)
ne_text_set = st.sets(st.text(min_size=1), min_size=1)


def non_empty_dict(vgen):
  return st.dictionaries(st.text(), vgen, min_size=1)


def test_capture_stdout():
  buf = io.StringIO()
  ret_string, code = u.capture_stdout(["echo", "hello!"], file=buf)
  assert code == 0

  # Verify that the stdout is reported to the supplied file, and that it's
  # captured by the function and returned correctly.
  assert ret_string == "hello!\n"
  assert buf.getvalue() == ret_string


def test_carriage_return():

  def through(xs):
    buf = io.StringIO()
    f = u.TqdmFile(file=buf)

    for x in xs:
      f.write(x)
      f.flush()

    return buf.getvalue()

  # Strings pass through tqdmfile with no newline attached.
  assert through(["Yo!"]) == "Yo!"

  # Empty lines do nothing.
  assert through(["", "", ""]) == ""

  # A carriage return is converted to a newline, but the next line, if it's
  # written, will have the proper prefix to trigger a carriage return.
  assert through(["Yo!\r"]) == "Yo!\n"

  # Boom, triggered.
  assert through(["Yo!\r", "continue"]) == f"Yo!\n{_term_move_up()}\rcontinue"


def test_capture_stdout_input():
  ret_string, code = u.capture_stdout(["cat"], input_str="hello!")
  assert code == 0
  assert ret_string.rstrip() == "hello!"


class UtilTestSuite(unittest.TestCase):
  """Tests for the util package."""

  @given(ne_text_set, ne_text_set)
  def test_enum_vals(self, ks, vs):
    """Setup ensures that the values are unique."""
    m = dict(zip(ks, vs))
    enum = Enum('TestEnum', m)

    # enum_vals returns the values from the enum.
    self.assertListEqual(list(m.values()), u.enum_vals(enum))

  def test_any_of_unit(self):
    MyEnum = Enum('MyEnum', {"a": "a_string", "b": "b_string"})
    SecondEnum = Enum('SecondEnum', {"c": "c_cake", "d": "d_face"})
    SomeEnum = Union[MyEnum, SecondEnum]

    # Asking for a value not in ANY enum raises a value error.
    with self.assertRaises(ValueError):
      u.any_of("face", SomeEnum)

  @given(ne_text_set, ne_text_set, ne_text_set, ne_text_set)
  def test_any_of(self, k1, v1, k2, v2):
    m1 = dict(zip(k1, v1))
    m2 = dict(zip(k2, v2))
    enum1 = Enum('enum1', m1)
    enum2 = Enum('enum2', m2)
    union = Union[enum1, enum2]

    # If the item appears in the first map any_of will return it.
    for k, v in m1.items():
      self.assertEqual(u.any_of(v, union), enum1(v))

    for k, v in m2.items():
      # If a value from the second enum appears in enum1 any_of will return it;
      # else, it'll return the value from enum2.
      try:
        expected = enum1(v)
      except ValueError:
        expected = enum2(v)

      self.assertEqual(u.any_of(v, union), expected)

  def test_dict_product(self):
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

    self.assertListEqual(result, expected)

  def test_compound_key_handling(self):
    """ tests the full assembly line transforming a configuration dictionary
    including compound keys into a list of dictionaries for passing to the script
    """

    tests = [{
        'input': {
            '[a,b]': [['c', 'd'], ['e', 'f']]
        },
        'after_tupleization': {
            ('a', 'b'): [('c', 'd'), ('e', 'f')]
        },
        'after_dictproduct': [{
            ('a', 'b'): ('c', 'd')
        }, {
            ('a', 'b'): ('e', 'f')
        }],
        'after_expansion': [{
            'a': 'c',
            'b': 'd'
        }, {
            'a': 'e',
            'b': 'f'
        }]
    }, {
        'input': {
            '[a,b]': ['c', 'd']
        },
        'after_tupleization': {
            ('a', 'b'): ('c', 'd')
        },
        'after_dictproduct': [{
            ('a', 'b'): ('c', 'd')
        }],
        'after_expansion': [{
            'a': 'c',
            'b': 'd'
        }]
    }, {
        'input': {
            'hi': 'there',
            '[k1,k2]': [['v1a', 'v2a'], ['v1b', 'v2b']]
        },
        'after_tupleization': {
            'hi': 'there',
            ('k1', 'k2'): [('v1a', 'v2a'), ('v1b', 'v2b')]
        },
        'after_dictproduct': [{
            'hi': 'there',
            ('k1', 'k2'): ('v1a', 'v2a')
        }, {
            'hi': 'there',
            ('k1', 'k2'): ('v1b', 'v2b')
        }],
        'after_expansion': [{
            'hi': 'there',
            'k1': 'v1a',
            'k2': 'v2a'
        }, {
            'hi': 'there',
            'k1': 'v1b',
            'k2': 'v2b'
        }]
    }, {
        'input': {
            'hi': 'there',
            '[a,b]': ['c', 'd']
        },
        'after_tupleization': {
            'hi': 'there',
            ('a', 'b'): ('c', 'd')
        },
        'after_dictproduct': [{
            'hi': 'there',
            ('a', 'b'): ('c', 'd')
        }],
        'after_expansion': [{
            'hi': 'there',
            'a': 'c',
            'b': 'd'
        }]
    }, {
        'input': {
            '[a,b]': [0, 1]
        },
        'after_tupleization': {
            ('a', 'b'): (0, 1)
        },
        'after_dictproduct': [{
            ('a', 'b'): (0, 1)
        }],
        'after_expansion': [{
            'a': 0,
            'b': 1
        }]
    }, {
        'input': {
            '[a,b]': [[0, 1]]
        },
        'after_tupleization': {
            ('a', 'b'): [(0, 1)]
        },
        'after_dictproduct': [{
            ('a', 'b'): (0, 1)
        }],
        'after_expansion': [{
            'a': 0,
            'b': 1
        }]
    }, {
        'input': {
            'hi': 'blueshift',
            '[a,b]': [[0, 1]]
        },
        'after_tupleization': {
            'hi': 'blueshift',
            ('a', 'b'): [(0, 1)]
        },
        'after_dictproduct': [{
            'hi': 'blueshift',
            ('a', 'b'): (0, 1)
        }],
        'after_expansion': [{
            'hi': 'blueshift',
            'a': 0,
            'b': 1
        }]
    }]

    def check_tupleization(test_dict):
      self.assertDictEqual(test_dict['after_tupleization'],
                           u.tupleize_dict(test_dict['input']))

    def check_dictproduct(test_dict):
      self.assertListEqual(
          test_dict['after_dictproduct'],
          list(u.dict_product(test_dict['after_tupleization'])))

    def check_expansion(test_dict):
      self.assertListEqual(
          test_dict['after_expansion'],
          list(u.expand_compound_dict(test_dict['after_dictproduct'])))

    for test in tests:
      check_tupleization(test)
      check_dictproduct(test)
      check_expansion(test)

  @given(st.integers())
  def test_compose(self, x):
    """Functions should compose; the composed function accepts any arguments that the rightmost function accepts."""

    def plus1(x):
      return x + 1

    def square(x):
      return x * x

    square_plus_one = u.compose(plus1, square)
    times_plus_one = u.compose(plus1, lambda l, r: l * r)

    self.assertEqual(square_plus_one(x), x * x + 1)
    self.assertEqual(square_plus_one(x), times_plus_one(l=x, r=x))

  @given(st.dictionaries(st.text(), st.text()),
         st.dictionaries(st.text(), st.text()))
  def test_merge(self, m1, m2):
    merged = u.merge(m1, m2)

    # Every item from the second map should be in the merged map.
    for k, v in m2.items():
      self.assertEqual(merged[k], v)

    # Every item from the first map should be in the merged map, OR, if it
    # shares a key with m2, m2's value will have bumped it.
    for k, v in m1.items():
      self.assertEqual(merged[k], m2.get(k, v))

  def test_flipm_unit(self):
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
    self.assertDictEqual(u.flipm(m), expected)

  @given(
      st.dictionaries(st.text(),
                      st.dictionaries(st.text(), st.text(), min_size=1)))
  def test_flipm(self, m):
    # As long as an inner dictionary isn't empty, flipping is invertible.
    self.assertDictEqual(m, u.flipm(u.flipm(m)))

  @given(st.sets(st.text()))
  def test_flipm_empty_values(self, ks):
    """Flipping a dictionary with empty values always equals the empty map."""
    m = u.dict_by(ks, lambda k: {})
    self.assertDictEqual({}, u.flipm(m))

  def test_invertm_unit(self):
    m = {"a": [1, 2, 3], "b": [2, 3, 4]}
    expected = {
        1: {"a"},
        2: {"a", "b"},
        3: {"a", "b"},
        4: {"b"},
    }
    self.assertDictEqual(u.invertm(m), expected)

  @given(non_empty_dict(non_empty_dict(text_set)))
  def test_reorderm(self, m):

    def invert_inner(d):
      return {k: u.invertm(v) for k, v in d.items()}

    flipped = u.flipm(m)

    # flipping the inner map.
    self.assertDictEqual(u.reorderm(m, (0, 2, 1)), invert_inner(m))

    # Flipping the outer keys is equivalent to calling flipm once.
    self.assertDictEqual(u.reorderm(m, (1, 0, 2)), flipped)

    # Reordering the inner keys is equiv to flipping the outer keys the
    # flipping the new inner dictionary.
    self.assertDictEqual(u.reorderm(m, (1, 2, 0)), invert_inner(flipped))

    # Flipping again brings the original list entry out.
    self.assertDictEqual(u.reorderm(m, (2, 1, 0)),
                         u.flipm(invert_inner(flipped)))

  @given(non_empty_dict(text_set))
  def test_invertm(self, m):
    self.assertDictEqual(m, u.invertm(u.invertm(m)))

  @given(st.sets(st.text()))
  def test_dict_by(self, xs):
    """dict_by should apply a function to each item in a set to generate the values
    of the returned dict.

    """
    m = u.dict_by(xs, len)

    # every value is properly constructed
    for k, v in m.items():
      self.assertEqual(len(k), v)

    # the key set of the dict is equal to the incoming original set.
    self.assertSetEqual(set(m.keys()), xs)

  def test_expand_args(self):
    m = OrderedDict([("a", "item"), ("b", None), ("c", "d")])
    expanded = u.expand_args(m)

    # None is excluded from the results.
    self.assertListEqual(expanded, ["a", "item", "b", "c", "d"])

  def test_generate_package(self):
    """validate that the generate_package function can handle all sorts of inputs
    and generate valid Package objects.

    """
    m = {
        # normal module syntax should just work.
        "caliban.util":
            u.module_package("caliban.util"),

        # This one is controversial, maybe... if something exists as a module
        # if you replace slashes with dots, THEN it will also parse as a
        # module. If it exists as a file in its own right this won't happen.
        #
        # TODO get a test in for this final claim using temp directories.
        "caliban/util":
            u.module_package("caliban.util"),

        # root scripts or packages should require the entire local directory.
        "setup":
            u.module_package("setup"),
        "cake.py":
            u.script_package("cake.py", "python"),

        # This is busted but should still parse.
        "face.cake.py":
            u.script_package("face.cake.py", "python"),

        # Paths into directories should parse properly into modules and include
        # the root as their required package to import.
        "face/cake.py":
            u.script_package("face/cake.py", "python"),

        # Deeper nesting works.
        "face/cake/cheese.py":
            u.script_package("face/cake/cheese.py", "python"),

        # Other executables work.
        "face/cake/cheese.sh":
            u.script_package("face/cake/cheese.sh"),
    }
    for k in m:
      self.assertEqual(u.generate_package(k), m[k])

  def test_module_to_path(self):
    """verify that we can go the other way and turn modules back into expected
    relative paths.

    """
    m = {
        # normal modules get nesting.
        "face.cake": "face/cake.py",

        # root-level modules just get a py extension.
        "face": "face.py",

        # This will get treated as a module nested inside of a folder, which is
        # clearly invalid; marking this behavior in the tests.
        "face/cake.py": "face/cake/py.py"
    }
    for k in m:
      self.assertEqual(u.module_to_path(k), m[k])

  def test_is_key(self):
    """A key is anything that starts with a dash; nothing else!

    """
    self.assertTrue(u._is_key("--face"))
    self.assertTrue(u._is_key("-f"))
    self.assertFalse(u._is_key(""))
    self.assertFalse(u._is_key("face"))
    self.assertFalse(u._is_key("f"))

    # this should never happen, but what the heck, why not test that it's a
    # fine thing, accepted yet strange.
    self.assertTrue(u._is_key("-----face"))

  def test_key_value_label(self):
    """unit tests for specific cases of key and value label conversion."""
    self.assertEqual("face", u.key_label("--face"))
    self.assertEqual("fa_ce", u.key_label("------fA.!! ce"))

    # Empty string roundtrips.
    self.assertEqual("", u.key_label(""))
    self.assertEqual("", u.value_label(""))

    # keys can't have leading digits, just letters, so we append a k.
    self.assertEqual("k0helper", u.key_label("--0helper"))

    # values CAN have leading digits and underscores.
    self.assertEqual("0helper", u.value_label("--0helper"))
    self.assertEqual("_helper", u.value_label("--_helper"))

  def assertValidLabel(self, label):
    """Assertion that passes if the supplied string is a valid label by all the
    rules of Cloud.

    """
    self.assertLessEqual(len(label), 63)

    if label != "":
      # check that the output has only lowercase, letters, dashes or
      # underscores.
      self.assertTrue(re.match('^[a-z0-9_-]+$', label))

  def assertValidKeyLabel(self, k):
    """Assertion that passes if the input is a valid key by all the rules of
    Cloud.

    """
    self.assertValidLabel(k)
    if k != "":
      self.assertTrue(k[0].isalpha())

  @given(st.text(min_size=1))
  def test_valid_key_label(self, s):
    cleaned = u.key_label(s)
    self.assertValidKeyLabel(cleaned)

  @given(st.text(min_size=1))
  def test_valid_value_label(self, s):
    cleaned = u.value_label(s)
    self.assertValidLabel(cleaned)

  @given(st.lists(st.integers()), st.integers(min_value=1, max_value=500))
  def test_n_chunks(self, xs, n):
    singletons = list(map(lambda x: [x], xs))

    # If the chunks equal the length we get all singletons.
    self.assertListEqual(u.n_chunks(xs, len(xs)), singletons)

    # one chunk returns a single singleton.
    self.assertListEqual(u.n_chunks(xs, 1), [xs])

    sharded = u.n_chunks(xs, n)
    recombined = list(itertools.chain(*sharded))

    # The ordering might not be the same, but the total number of items is the
    # same if we break down and recombine.
    self.assertEqual(len(recombined), len(xs))

    # And the items are equal too.
    self.assertSetEqual(set(xs), set(recombined))

  def test_chunks_below_limit(self):
    xs = [0, 1, 2, 3, 4, 5]

    # Below the limit, there's no breakdown.
    self.assertListEqual([xs], u.chunks_below_limit(xs, 100))

    # Below the limit, there's no breakdown.
    shards = [[0, 2, 4], [1, 3, 5]]
    self.assertListEqual(shards, u.chunks_below_limit(xs, 5))

    # You can recover the original list by zipping together the shards (if they
    # happen to be equal in length, as here.)
    self.assertListEqual(xs, list(itertools.chain(*list(zip(*shards)))))

  @given(st.lists(st.integers(), min_size=1))
  def test_partition_first_items(self, xs):
    """retrieving the first item of each grouping recovers the original list."""
    rt = list(map(lambda pair: pair[0], u.partition(xs, 1)))
    self.assertListEqual(rt, xs)

  @given(st.lists(st.integers(), min_size=1))
  def test_partition_by_one_gives_singletons(self, xs):
    """Partition by 1 gives a list of singletons."""
    singletons = list(u.partition(xs, 1))
    self.assertListEqual(singletons, [[x] for x in xs])

  @given(st.lists(st.integers(), min_size=1), st.integers(min_value=0))
  def test_partition_by_big_gives_singleton(self, xs, n):
    """partitioning by a number >= the list length returns a singleton containing
    just the list.

    """
    one_entry = list(u.partition(xs, len(xs) + n))
    self.assertListEqual(one_entry, [xs])

  def test_partition(self):
    """Various unittests of partition."""

    # partitioning by 1 generates singletons.
    self.assertListEqual(list(u.partition([1, 2, 3, 4, 5], 1)),
                         [[1], [2], [3], [4], [5]])

    # partition works into groups of 2
    self.assertListEqual(list(u.partition([1, 2, 3, 4], 2)),
                         [[1, 2], [2, 3], [3, 4]])

    # >= case
    self.assertListEqual(list(u.partition([1, 2, 3], 3)), [[1, 2, 3]])
    self.assertListEqual(list(u.partition([1, 2, 3], 10)), [[1, 2, 3]])

  def assertScriptArgsToLabels(self, s, m):
    """Assertion that passes if the supplied string of arguments parses to a
    dictionary that equals the supplied m, representing the expected kv pairs.

    """
    parsed_args = u.script_args_to_labels(s.split(" "))
    self.assertDictEqual(parsed_args, m)

  def test_script_args_to_labels(self):
    """unit tests of our script_args_to_labels function behavior."""

    # Args like --!!! that parse keys to the empty string should not make it
    # through.
    self.assertScriptArgsToLabels("--lr 1 --!!! 2 --face 3", {
        "lr": "1",
        "face": "3"
    })

    # Duplicates get overwritten.
    self.assertScriptArgsToLabels("--lr 1 --lr 2", {"lr": "2"})

    self.assertScriptArgsToLabels("--LR 1 --item-label --fa!!ce cake --a", {
        "lr": "1",
        "item-label": "",
        "face": "cake",
        "a": "",
    })

    # Multiple values are dropped for now, for the purpose of creating labels.
    self.assertScriptArgsToLabels(
        "--lr 1 2 3 --item_underscoRE!! --face cake --a", {
            "lr": "1",
            "item_underscore": "",
            "face": "cake",
            "a": "",
        })

    self.assertScriptArgsToLabels("--face", {"face": ""})

    # single arguments get ignore if they're not boolean flags.
    self.assertScriptArgsToLabels("face", {})

  def test_sanitize_labels_kill_empty(self):
    """Keys that are sanitized to the empty string should NOT make it through."""
    self.assertDictEqual({}, u.sanitize_labels([["--!!", "face"]]))

  @given(
      st.one_of(non_empty_dict(st.text()),
                st.lists(st.tuples(st.text(), st.text()))))
  def test_sanitize_labels(self, pairs):
    """Test that any input we could possibly be provided, as long as it parses into
    kv pairs, will only make it into a dict of labels if it's properly
    sanitized.

    Checks that the functions works for dicts OR for lists of pairs.

    """
    for k, v in u.sanitize_labels(pairs).items():
      self.assertValidKeyLabel(k)
      self.assertValidLabel(v)

  @given(st.lists(st.tuples(st.text(), st.text())))
  def test_sanitize_labels_second_noop(self, pairs):
    """Test that passing the output of sanitize_labels back into the function
    returns its input. Sanitizing a set of sanitized kv pairs should have no
    effect.

    """
    once = u.sanitize_labels(pairs)
    twice = u.sanitize_labels(once)
    self.assertDictEqual(once, twice)


if __name__ == '__main__':
  unittest.main()
