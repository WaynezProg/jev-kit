import unittest
from modules.security_tools import safe_header_value

class HeaderValueTests(unittest.TestCase):
    def test_rejects_both_kinds_of_line_break(self):
        self.assertEqual(safe_header_value("  hello  "), "hello")
        with self.assertRaises(ValueError):
            safe_header_value("one\ntwo")
        with self.assertRaises(ValueError):
            safe_header_value("one\rtwo")
