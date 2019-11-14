import unittest
import caliban.util as u


class UtilTestSuite(unittest.TestCase):
  """Tests for the util package."""

  def test_generate_package(self):
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


if __name__ == '__main__':
  unittest.main()
