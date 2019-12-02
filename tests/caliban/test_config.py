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

    valid = {"a": [1, 2, 3], "b": True, "c": 1, "d": "e"}
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


if __name__ == '__main__':
  unittest.main()
