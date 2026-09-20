import unittest
from modules.query_tools import replace_parameter

class ReplaceParameterTests(unittest.TestCase):
    def test_appends_absent_key_and_collapses_duplicates(self):
        self.assertEqual(replace_parameter("q=old&page=1", "q", "new"), "q=new&page=1")
        self.assertEqual(replace_parameter("page=1", "q", "new"), "page=1&q=new")
        self.assertEqual(replace_parameter("q=a&q=b", "q", "new"), "q=new")
