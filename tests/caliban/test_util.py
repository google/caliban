import re
import unittest

import hypothesis.strategies as st
from hypothesis import given

import caliban.util as u


class UtilTestSuite(unittest.TestCase):
  """Tests for the util package."""

  def test_dict_product(self):
    result = list(u.dict_product({"a": [1, 2, 3], "b": [4, 5], "c": "d"}))
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
    m = u.expand_args({"a": "item", "b": None, "c": "d"})
    expanded = u.expand_args(m)

    # None is excluded from the results.
    self.assertListEqual(expanded, ["a", "item", "b", "c", "d"])

  def test_generate_package(self):
    """validate that the generate_package function can handle all sorts of inputs
    and generate valid Package objects.

    """
    m = {
        # normal module syntax should just work.
        "face.cake": u.Package("face", "face.cake"),

        # root scripts or packages should require the entire local directory.
        "cake": u.Package(".", "cake"),
        "cake.py": u.Package(".", "cake"),

        # This is busted but should still parse.
        "face.cake.py": u.Package("face", "face.cake"),

        # Paths into directories should parse properly into modules and include
        # the root as their required package to import.
        "face/cake.py": u.Package("face", "face.cake"),

        # Deeper nesting works.
        "face/cake/cheese.py": u.Package("face", "face.cake.cheese"),
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

        # paths shouldn't be touched.
        "face/cake.py": "face/cake.py"
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
    self.assertEqual("face", u.key_label("------fA.!! ce"))

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

  def test_n_chunks(self):
    pass

  def test_expand_args(self):
    pass

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

  def test_sanitize_labels_kill_empty(self):
    """Keys that are sanitized to the empty string should NOT make it through."""
    self.assertDictEqual({}, u.sanitize_labels([["--!!", "face"]]))

  @given(st.lists(st.tuples(st.text(), st.text())))
  def test_sanitize_labels(self, pairs):
    """Test that any input we could possibly be provided, as long as it parses into
    kv pairs, will only make it into a dict of labels if it's properly
    sanitized.

    """
    for k, v in u.sanitize_labels(pairs).items():
      self.assertValidKeyLabel(k)
      self.assertValidLabel(v)


if __name__ == '__main__':
  unittest.main()
