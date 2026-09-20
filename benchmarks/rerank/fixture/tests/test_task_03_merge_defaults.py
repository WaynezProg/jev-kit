import unittest
from modules.collection_tools import merge_defaults

class MergeDefaultTests(unittest.TestCase):
    def test_none_means_unspecified(self):
        self.assertEqual(
            merge_defaults({"timeout": 30, "label": "default"}, {"timeout": None, "label": "custom"}),
            {"timeout": 30, "label": "custom"},
        )
