import unittest

import caliban.docker as d


class DockerTestSuite(unittest.TestCase):
  """Tests for the docker package."""

  def test_shell_dict(self):
    """Tests that the shell dict has an entry for all possible Shell values."""

    self.assertSetEqual(set(d.Shell), set(d.SHELL_DICT.keys()))

  def test_image_tag_for_project(self):
    """Tests that we generate a valid image tag for domain-scoped and modern
    project IDs.

    """
    self.assertEqual(d._image_tag_for_project("face", "imageid"),
                     "gcr.io/face/imageid:latest")

    self.assertEqual(d._image_tag_for_project("google.com:face", "imageid"),
                     "gcr.io/google.com/face/imageid:latest")
