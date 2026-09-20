import unittest
from modules.time_tools import retry_delays

class RetryDelayTests(unittest.TestCase):
    def test_attempts_counts_retries_not_initial_request(self):
        self.assertEqual(retry_delays(0, 2), [])
        self.assertEqual(retry_delays(3, 2), [2, 4, 8])
        with self.assertRaises(ValueError):
            retry_delays(-1, 2)
