import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('rerank_runner', ROOT / 'benchmarks/rerank/run.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RerankExecutorTests(unittest.TestCase):
    def test_replacement_cannot_change_signature_or_other_functions(self):
        original = 'def first(x, *, scale=2):\n    return x * scale\n\ndef other():\n    return 7\n'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'module.py'
            for invalid in ['def first(x):\n    return x', 'def other(x, *, scale=2):\n    return x', 'def first(x, *, scale=2):\n    return x\ndef extra():\n    return 0']:
                path.write_text(original)
                with self.assertRaises(ValueError):
                    runner.replace_function(path, 'first', invalid)
                self.assertEqual(path.read_text(), original)
            runner.replace_function(path, 'first', 'def first(x, *, scale=2):\n    return x + scale')
            self.assertIn('def other():\n    return 7', path.read_text())

    def test_retrieval_tie_keeps_original_order_and_never_uses_gold(self):
        corpus = [{'id': 'b', 'text': 'def same(): return 1', 'gold': True}, {'id': 'a', 'text': 'def same(): return 1', 'gold': False}]
        self.assertEqual([c['id'] for c in runner.retrieve('same', corpus)], ['b', 'a'])


if __name__ == '__main__':
    unittest.main()
