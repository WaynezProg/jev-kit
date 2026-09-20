import unittest
from modules.record_tools import coerce_flag

class FlagTests(unittest.TestCase):
    def test_whitespace_around_known_text_is_accepted(self):
        self.assertTrue(coerce_flag(True))
        self.assertFalse(coerce_flag(False))
        self.assertTrue(coerce_flag("yes"))
        self.assertFalse(coerce_flag("OFF"))
        self.assertTrue(coerce_flag(" YES "))
        self.assertFalse(coerce_flag(" off "))
        with self.assertRaises(ValueError):
            coerce_flag("perhaps")
