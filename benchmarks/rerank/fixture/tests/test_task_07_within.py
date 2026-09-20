import unittest
from modules.number_tools import within

class WithinTests(unittest.TestCase):
    def test_tolerance_boundary_is_inclusive(self):
        self.assertTrue(within(12, 10, 2))
        self.assertFalse(within(12.1, 10, 2))
        with self.assertRaises(ValueError):
            within(10, 10, -1)
