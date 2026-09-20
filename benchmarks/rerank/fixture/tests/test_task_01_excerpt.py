import unittest
from modules.text_tools import clamp_excerpt

class ExcerptTests(unittest.TestCase):
    def test_does_not_exceed_display_limit(self):
        self.assertEqual(clamp_excerpt("abcdefgh", 5), "ab...")
        self.assertEqual(clamp_excerpt("abcdefgh", 2), "..")
        self.assertEqual(clamp_excerpt("abc", 5), "abc")
        self.assertEqual(clamp_excerpt("abc", 0), "")
