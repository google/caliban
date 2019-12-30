import unittest
from argparse import ArgumentTypeError

import caliban.config as c


class ConfigTestSuite(unittest.TestCase):
  """Tests for the config package."""

  def test_validate_experiment_config(self):
    """basic examples of validate experiment config."""
    invalid = {1: "face", "2": "3"}
    with self.assertRaises(ArgumentTypeError):
      c.validate_experiment_config(invalid)

    # a dict value is invalid, even if it's hidden in a list.
    with self.assertRaises(ArgumentTypeError):
      c.validate_experiment_config({"key": [{1: 2}, "face"]})

    valid = {"a": [1.0, 2, 3], "b": True, "c": 1, "d": "e", "f": 1.2}
    self.assertDictEqual(valid, c.validate_experiment_config(valid))

    # Lists are okay too...
    items = [valid, valid]
    self.assertListEqual(items, c.validate_experiment_config(items))

    # As are lists of lists.
    lol = [valid, [valid]]
    self.assertListEqual(lol, c.validate_experiment_config(lol))

    # Invalid types are caught even nested inside lists.
    lol_invalid = [valid, valid, [invalid]]
    with self.assertRaises(ArgumentTypeError):
      c.validate_experiment_config(lol_invalid)

  def test_expand_experiment_config(self):
    # An empty config expands to a singleton list. This is important so that
    # single job submission without a spec works.
    self.assertListEqual([{}], list(c.expand_experiment_config({})))


if __name__ == '__main__':
  unittest.main()
