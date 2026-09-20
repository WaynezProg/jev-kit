import unittest
from modules.path_tools import relative_path

class RelativePathTests(unittest.TestCase):
    def test_requires_path_component_boundary(self):
        self.assertEqual(relative_path("/srv/app/config.py", "/srv/app"), "config.py")
        self.assertEqual(relative_path("/srv/app", "/srv/app"), "")
        with self.assertRaises(ValueError):
            relative_path("/srv/application/config.py", "/srv/app")
