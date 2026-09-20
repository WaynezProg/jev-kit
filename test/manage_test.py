import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('manage', Path(__file__).resolve().parents[1] / 'scripts/manage.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FakeCodex(m.Manager):
    def __init__(self, home):
        super().__init__(home)
        self.plugins = []
        self.marketplaces = {}
        self.fail_add = False

    def codex_call(self, *args):
        if args[0] == 'list':
            return json.dumps({'installed': self.plugins})
        if args[:2] == ('marketplace', 'list'):
            return json.dumps({'marketplaces': [{'name': k, 'root': v} for k, v in self.marketplaces.items()]})
        if args[:2] == ('marketplace', 'add'):
            self.marketplaces[m.MARKET] = args[2]
        elif args[:2] == ('marketplace', 'remove'):
            self.marketplaces.pop(args[2], None)
        elif args[0] == 'add':
            if self.fail_add:
                raise RuntimeError('simulated native failure')
            self.plugins = [p for p in self.plugins if p['pluginId'] != args[1]]
            self.plugins.append({'name': m.NAME, 'pluginId': args[1], 'enabled': True})
        elif args[0] == 'remove':
            self.plugins = [p for p in self.plugins if p['pluginId'] != args[1]]
        return '{}'


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name).resolve()
        self.manager = FakeCodex(self.home)
        self.original = {}
        for host, (rel, key) in m.CONFIGS.items():
            path = self.home / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = b'# preserve this\npreference="keep"\n[mcp_servers.other]\ncommand="other"\n' if host == 'grok' else m.dump({'preference': 'keep', key: {'other': {'command': 'other'}}})
            path.write_bytes(raw)
            self.original[host] = m.parsed(host, raw)

    def tearDown(self):
        self.temp.cleanup()

    def assert_unrelated_preserved(self):
        for host, (rel, key) in m.CONFIGS.items():
            now = m.parsed(host, (self.home / rel).read_bytes())
            now[key].pop(m.NAME, None)
            self.assertEqual(now, self.original[host])

    def test_nine_host_install_update_uninstall_and_reinstall(self):
        self.manager.change('install', m.HOSTS)
        self.assertEqual(len(self.manager.state()['hosts']), 9)
        self.assertTrue(all(h['status'] == 'configured' for h in self.manager.status()['hosts']))
        first_release = self.manager.state()['release']
        self.manager.change('install', m.HOSTS)
        self.assertEqual(self.manager.state()['release'], first_release)
        self.assert_unrelated_preserved()
        # Add unrelated settings AFTER installation: uninstall must not restore old snapshots.
        path = self.home / m.CONFIGS['claude'][0]
        data = json.loads(path.read_text()); data['new_preference'] = 42; path.write_bytes(m.dump(data))
        self.original['claude']['new_preference'] = 42
        with tempfile.TemporaryDirectory() as source:
            root = Path(source)
            for part in m.PAYLOAD:
                src = m.SOURCE / part
                if src.is_dir():
                    shutil.copytree(src, root / part, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                else:
                    shutil.copy2(src, root / part)
            with (root / 'README.md').open('a') as f:
                f.write('\nUpdate fixture.\n')
            self.manager.change('update', [], root)
        self.assertNotEqual(self.manager.state()['release'], first_release)
        self.manager.change('uninstall', ['muse', 'pi'])
        self.assertEqual(len(self.manager.state()['hosts']), 7)
        self.assertFalse((self.home / m.SKILLS['muse']).exists())
        self.assertTrue((self.home / m.SKILLS['claude']).exists())
        self.manager.change('uninstall', [])
        self.assertEqual(self.manager.state()['hosts'], {})
        self.assert_unrelated_preserved()
        self.assertEqual(self.manager.plugins, [])
        self.assertEqual(self.manager.marketplaces, {})
        self.manager.change('uninstall', m.HOSTS)
        self.manager.change('install', m.HOSTS)
        self.assertEqual(len(self.manager.state()['hosts']), 9)

    def test_unowned_entry_refused_before_any_host_changes(self):
        path = self.home / m.CONFIGS['muse'][0]
        data = json.loads(path.read_text()); data['mcpServers'][m.NAME] = {'command': 'foreign'}; path.write_bytes(m.dump(data))
        with self.assertRaises(ValueError):
            self.manager.change('install', ['claude', 'muse'])
        self.assertEqual(m.parsed('claude', (self.home / m.CONFIGS['claude'][0]).read_bytes()), self.original['claude'])
        self.assertFalse(self.manager.state_path.exists())

    def test_modified_entry_and_link_survive_update_and_uninstall(self):
        self.manager.change('install', ['claude'])
        path = self.home / m.CONFIGS['claude'][0]
        original = path.read_bytes()
        data = json.loads(original); data['mcpServers'][m.NAME]['extra'] = 'manual'; path.write_bytes(m.dump(data))
        modified = path.read_bytes()
        for action in ['update', 'uninstall']:
            with self.assertRaises(ValueError):
                self.manager.change(action, [])
            self.assertEqual(path.read_bytes(), modified)
        path.write_bytes(original)
        link = self.home / m.SKILLS['claude']; link.unlink(); link.write_text('user replacement')
        with self.assertRaises(ValueError):
            self.manager.change('uninstall', [])
        self.assertEqual(link.read_text(), 'user replacement')
        self.assertEqual(self.manager.status()['hosts'][0]['status'], 'drift')

    def test_failed_state_write_rolls_back_all_config_and_links(self):
        real_put = m.put
        def fail_state(path, desired):
            if path == self.manager.state_path:
                raise OSError('simulated full disk')
            real_put(path, desired)
        with patch.object(m, 'put', fail_state):
            with self.assertRaises(RuntimeError):
                self.manager.change('install', ['claude', 'pi'])
        self.assert_unrelated_preserved()
        self.assertFalse((self.home / m.SKILLS['claude']).exists())
        self.assertFalse(os.path.lexists(self.manager.current))

    def test_native_failure_rolls_back_mcp_changes(self):
        self.manager.fail_add = True
        with self.assertRaises(RuntimeError):
            self.manager.change('install', ['codex', 'claude'])
        self.assert_unrelated_preserved()
        self.assertEqual(self.manager.marketplaces, {})
        self.assertFalse(self.manager.state_path.exists())

    def test_explicit_legacy_adoption_only_matches_exact_source(self):
        legacy = self.home / 'old-source'
        (legacy / 'skills/jev-kit').mkdir(parents=True)
        path = self.home / m.CONFIGS['muse'][0]
        data = json.loads(path.read_text()); data['mcpServers'][m.NAME] = m.entry('muse', legacy / 'scripts/serve'); path.write_bytes(m.dump(data))
        link = self.home / m.SKILLS['muse']; link.parent.mkdir(parents=True); link.symlink_to(legacy / 'skills/jev-kit')
        with self.assertRaises(ValueError):
            self.manager.change('install', ['muse'], adopt=self.home / 'wrong')
        self.manager.change('install', ['muse'], adopt=legacy)
        self.assertEqual(link.resolve(), (self.manager.current / 'skills/jev-kit').resolve())
        self.manager.change('uninstall', [])
        self.assertTrue((legacy / 'skills/jev-kit').is_dir())

    def test_unknown_hosts_and_partial_update_refused(self):
        with self.assertRaises(ValueError):
            self.manager.change('install', ['typo'])
        self.manager.change('install', ['claude', 'pi'])
        with self.assertRaises(ValueError):
            self.manager.change('update', ['pi'])

    def test_missing_config_creation_and_private_receipts(self):
        with tempfile.TemporaryDirectory() as home:
            manager = FakeCodex(home)
            result = manager.change('install', ['gemini', 'pi'])
            path = Path(home) / m.CONFIGS['gemini'][0]
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(Path(result['receipt']).stat().st_mode & 0o777, 0o700)
            self.assertEqual(manager.state_path.stat().st_mode & 0o777, 0o600)
            manager.change('uninstall', [])
            self.assertNotIn(m.NAME, json.loads(path.read_text())['mcpServers'])

    def test_grok_inline_table_and_muse_alias_refuse_safely(self):
        raw = b'mcp_servers={"jev-kit"={command="x"}}\n'
        with self.assertRaises(ValueError):
            m.rewrite('grok', raw, {'command': 'x'}, None)
        with self.assertRaises(ValueError):
            m.rewrite('muse', b'{"mcp_servers":{}}', None, {})

    def test_existing_codex_plugin_requires_exact_adoption(self):
        self.manager.plugins = [{'name': m.NAME, 'pluginId': 'jev-kit@personal', 'enabled': True, 'source': {'path': str(self.home / 'legacy')}}]
        with self.assertRaises(ValueError):
            self.manager.change('install', ['codex'])
        self.manager.change('install', ['codex'], adopt=self.home / 'legacy')
        self.assertEqual([p['pluginId'] for p in self.manager.plugins], ['jev-kit@jev-kit-managed'])

    def test_foreign_marketplace_and_runtime_pointer_are_preserved(self):
        self.manager.marketplaces[m.MARKET] = str(self.home / 'someone-else')
        with self.assertRaises(ValueError):
            self.manager.change('install', ['codex'])
        self.manager.change('install', ['pi'])
        self.manager.current.unlink()
        self.manager.current.symlink_to(self.home / 'manual-runtime')
        with self.assertRaises(ValueError):
            self.manager.change('update', [])
        self.assertEqual(os.readlink(self.manager.current), str(self.home / 'manual-runtime'))

    def test_managed_command_runs_independently_of_checkout(self):
        self.manager.change('install', ['pi'])
        output = subprocess.check_output([str(self.manager.root / 'jev'), 'status', '--home', str(self.home)], cwd=self.home, text=True)
        self.assertEqual(json.loads(output)['hosts'][0]['status'], 'configured')


if __name__ == '__main__':
    unittest.main()
