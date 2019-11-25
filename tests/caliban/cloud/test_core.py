import unittest

import caliban.cloud.core as c


class CoreTestSuite(unittest.TestCase):
  """Tests for caliban.cloud.core."""

  def test_expand_experiment_config(self):
    # An empty config expands to a singleton list. This is important so that
    # single job submission without a spec works.
    self.assertListEqual([{}], list(c.expand_experiment_config({})))
