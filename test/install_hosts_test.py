import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest

spec = importlib.util.spec_from_file_location('installer', Path(__file__).resolve().parents[1] / 'scripts/install-hosts.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class HostConfigTests(unittest.TestCase):
    def test_preserves_unrelated_config_and_is_idempotent(self):
        for host, (_, key) in installer.HOSTS.items():
            with self.subTest(host=host), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'config'
                if host == 'grok':
                    original = '# keep comment\nname="example"\n[mcp_servers.existing]\ncommand="unchanged"\n'
                    parse = tomllib.loads
                else:
                    original = json.dumps({'preferences': {'keep': True}, key: {'existing': {'command': 'unchanged'}}})
                    parse = json.loads
                path.write_text(original)
                old, new = installer.plan_config(host, path, Path('/test path/serve'))
                self.assertEqual(old.decode(), original)
                before, after = parse(original), parse(new.decode())
                self.assertEqual(after[key].pop('jev-kit'), installer.definition(host, Path('/test path/serve')))
                self.assertEqual(before, after)
                if host == 'grok':
                    self.assertTrue(new.startswith(old))
                path.write_bytes(new)
                self.assertEqual(installer.plan_config(host, path, Path('/test path/serve')), (new, new))

    def test_conflicting_entry_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config'
            original = json.dumps({'mcpServers': {'jev-kit': {'command': 'other'}}})
            path.write_text(original)
            with self.assertRaises(ValueError):
                installer.plan_config('claude', path, Path('/serve'))
            self.assertEqual(path.read_text(), original)

    def test_muse_duplicate_alias_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config'
            path.write_text('{"mcpServers":{},"mcp_servers":{}}')
            with self.assertRaises(ValueError):
                installer.plan_config('muse', path, Path('/serve'))

    def test_explicit_grok_disable_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config'
            path.write_text('disabled_mcp_servers=["jev-kit"]\n')
            with self.assertRaises(ValueError):
                installer.plan_config('grok', path, Path('/serve'))
