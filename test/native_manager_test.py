import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('manage', SCRIPTS / 'manage.py')
manage = importlib.util.module_from_spec(spec)
sys.modules['manage'] = manage
spec.loader.exec_module(manage)
spec = importlib.util.spec_from_file_location('native_manager', SCRIPTS / 'native_manager.py')
native = importlib.util.module_from_spec(spec)
sys.modules['native_manager'] = native
spec.loader.exec_module(native)
import native_packages


class FakeDrivers:
    """In-memory host CLIs; Grok can emulate a CLI policy rewrite."""
    def __init__(self, home, root):
        self.home, self.root = Path(home).resolve(), Path(root).resolve()
        self.installed, self.disabled, self.calls = set(), set(), []
        self.versions, self.stale_updates = {}, set()
        self.rewrite_grok_policy = False

    def probe(self, host):
        if host == 'muse':
            return {'available': False, 'reason': 'plugins are not available in this build'}
        return {'available': True, 'reason': None}

    def package_path(self, host):
        if host == 'claude':
            return self.root / 'native/claude/marketplace/plugins/jev-kit'
        return self.root / 'native' / host / 'jev-kit'

    def check(self, host, package, owned):
        self.calls.append(('check', host, owned))
        if host in self.disabled:
            raise ValueError(f'{host}: native plugin is disabled')
        if owned and host not in self.installed:
            raise ValueError(f'{host}: managed native plugin is missing')
        if not owned and host in self.installed:
            raise ValueError(f'{host}: native plugin already exists; inspect before replacing it')
        if owned:
            return {'version': self.versions.get(host)}

    def package_version(self, host, package):
        manifest = {'claude': '.claude-plugin/plugin.json', 'gemini': 'gemini-extension.json',
                    'grok': 'plugin.json', 'muse': '.muse-plugin/plugin.json'}[host]
        return json.loads((Path(package) / manifest).read_text())['version']

    def validate(self, host, package):
        self.calls.append(('validate', host))

    def install(self, host, package):
        self.calls.append(('install', host)); self.installed.add(host)
        self.versions[host] = self.package_version(host, package)
        if host == 'grok' and self.rewrite_grok_policy:
            path = self.home / '.grok/config.toml'
            path.write_text(path.read_text().rstrip() + '\n\n[plugins]\nenabled = ["jev-kit", "other"]\n')

    def update(self, host, package):
        self.calls.append(('update', host)); self.check(host, package, True)
        if host not in self.stale_updates:
            self.versions[host] = self.package_version(host, package)

    def remove(self, host, package):
        self.calls.append(('remove', host)); self.installed.discard(host); self.versions.pop(host, None)


class Harness(native.NativeManager):
    def __init__(self, home, drivers, integration='auto'):
        super().__init__(home, node='/fake/node', codex='/fake/codex', integration=integration, drivers=drivers)
        self.plugins, self.marketplaces, self.release_number = [], {}, 0

    def detect(self):
        return manage.HOSTS.copy()

    def codex_call(self, *args):
        if args[0] == 'list':
            return json.dumps({'installed': self.plugins})
        if args[:2] == ('marketplace', 'list'):
            return json.dumps({'marketplaces': [{'name': k, 'root': v} for k, v in self.marketplaces.items()]})
        if args[:2] == ('marketplace', 'add'):
            self.marketplaces[manage.MARKET] = args[2]
        elif args[:2] == ('marketplace', 'remove'):
            self.marketplaces.pop(args[2], None)
        elif args[0] == 'add':
            self.plugins = [{'name': manage.NAME, 'pluginId': args[1], 'enabled': True}]
        elif args[0] == 'remove':
            self.plugins = []
        return '{}'

    def prepare_release(self, source):
        self.release_number += 1
        release_id = f'fixture{self.release_number}'
        destination = self.root / 'releases' / release_id
        destination.mkdir(parents=True)
        (destination / 'skills/jev-kit').mkdir(parents=True)
        (destination / 'skills/jev-kit/SKILL.md').write_text('# Jev Kit\n')
        (destination / 'LICENSE').write_text('MIT\n')
        (destination / 'package.json').write_text(json.dumps({'version': '0.3.0'}))
        (destination / 'dist').mkdir()
        (destination / 'dist/cli.js').write_text('// fixture\n')
        (destination / 'dist/pi-extension.js').write_text('// fixture\n')
        (destination / 'dist/opencode-plugin.js').write_text('// fixture\n')
        native_packages.build_packages(destination, self.node, str(self.launcher), release_id)
        return release_id, destination


class NativeManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / 'home'; self.home.mkdir()
        self.drivers = FakeDrivers(self.home, self.home / '.local/share/jev-kit')
        self.manager = Harness(self.home, self.drivers)
        self.original = {}
        for host, (rel, key) in manage.CONFIGS.items():
            path = self.home / rel; path.parent.mkdir(parents=True, exist_ok=True)
            raw = (b'# keep this\n[mcp_servers.other]\ncommand = "other"\n'
                   if host == 'grok' else manage.dump({'unrelated': {'keep': True}, key: {'other': {'command': 'other'}}}))
            path.write_bytes(raw); self.original[host] = manage.parsed(host, raw)

    def tearDown(self):
        self.temp.cleanup()

    def assert_unrelated(self):
        for host, (rel, key) in manage.CONFIGS.items():
            data = manage.parsed(host, (self.home / rel).read_bytes())
            data.get(key, {}).pop(manage.NAME, None)
            self.assertEqual(data, self.original[host])

    def test_auto_nine_host_lifecycle_and_muse_fallback(self):
        installed = self.manager.change('install', [])
        self.assertEqual(installed['hosts'], manage.HOSTS)
        state = self.manager.state()
        self.assertEqual(len(state['hosts']), 9)
        self.assertEqual(state['hosts']['muse']['kind'], 'mcp')
        self.assertIn('plugins are not available', state['hosts']['muse']['fallback_reason'])
        self.assertTrue(all(row['status'] == 'configured' for row in self.manager.status()['hosts']))
        first = state['release']
        self.manager.change('update', [])
        self.assertNotEqual(self.manager.state()['release'], first)
        self.manager.change('uninstall', [])
        self.assertEqual(self.manager.state()['hosts'], {})
        self.assert_unrelated()
        self.manager.change('install', [])
        self.assertEqual(len(self.manager.state()['hosts']), 9)

    def test_legacy_mcp_records_migrate_without_duplicate_entry_or_skill(self):
        legacy = manage.Manager(self.home, node='/fake/node', codex='/fake/codex')
        legacy.root.mkdir(parents=True)
        release = legacy.root / 'releases/legacy'; (release / 'dist').mkdir(parents=True)
        (release / 'dist/cli.js').write_text('// old\n'); (release / 'skills/jev-kit').mkdir(parents=True)
        legacy.current.symlink_to(release)
        legacy.launcher.parent.mkdir(parents=True, exist_ok=True)
        legacy.launcher.write_text('#!/bin/sh\n'); legacy.launcher.chmod(0o755)
        records = {}
        for host in ('claude', 'muse'):
            path = self.home / manage.CONFIGS[host][0]
            raw = manage.rewrite(host, path.read_bytes(), None, manage.entry(host, legacy.launcher))
            path.write_bytes(raw)
            link = self.home / manage.SKILLS[host]; link.parent.mkdir(parents=True, exist_ok=True); link.symlink_to(release / 'skills/jev-kit')
            records[host] = {'entry': manage.entry(host, legacy.launcher), 'links': {manage.SKILLS[host]: str(release / 'skills/jev-kit')}}
        legacy.state_path.write_bytes(manage.dump({'format': 1, 'release': 'legacy', 'hosts': records}))
        self.manager.change('update', [])
        claude = manage.parsed('claude', (self.home / manage.CONFIGS['claude'][0]).read_bytes())
        self.assertNotIn(manage.NAME, claude['mcpServers'])
        self.assertEqual(manage.parsed('muse', (self.home / manage.CONFIGS['muse'][0]).read_bytes())['mcpServers'].keys(), {'other', manage.NAME})
        self.assertFalse((self.home / manage.SKILLS['claude']).exists())
        self.assertTrue((self.home / manage.SKILLS['muse']).is_symlink())
        self.assertEqual(self.manager.state()['format'], 2)

    def test_native_file_drift_and_unowned_file_are_preserved(self):
        self.manager.change('install', ['claude'])
        package = self.drivers.package_path('claude')
        managed = next(package.rglob('SKILL.md')); managed.write_text('manual edit\n')
        with self.assertRaisesRegex(ValueError, 'managed package file changed'):
            self.manager.change('update', [])
        self.assertEqual(managed.read_text(), 'manual edit\n')
        managed.write_text('# Jev Kit\n')
        foreign = package / 'manual.txt'; foreign.write_text('keep\n')
        with self.assertRaisesRegex(ValueError, 'package contains unowned files'):
            self.manager.change('uninstall', [])
        self.assertEqual(foreign.read_text(), 'keep\n')

    def test_disabled_native_host_refuses_without_changes(self):
        self.manager.change('install', ['grok'])
        before = (self.home / '.grok/config.toml').read_bytes()
        self.drivers.disabled.add('grok')
        with self.assertRaisesRegex(ValueError, 'disabled'):
            self.manager.change('update', [])
        self.assertEqual((self.home / '.grok/config.toml').read_bytes(), before)

    def test_foreign_claude_marketplace_sibling_stops_removal(self):
        self.manager.change('install', ['claude'])
        foreign = self.drivers.package_path('claude').parent / 'other/SKILL.md'
        foreign.parent.mkdir(); foreign.write_text('unrelated plugin')
        previous_calls = list(self.drivers.calls)
        with self.assertRaisesRegex(ValueError, 'unowned files'):
            self.manager.change('uninstall', [])
        self.assertEqual(self.drivers.calls, previous_calls)
        self.assertEqual(foreign.read_text(), 'unrelated plugin')
        self.assertIn('claude', self.drivers.installed)

    def test_strict_native_refuses_muse_before_other_host_changes(self):
        self.manager.integration = 'native'
        with self.assertRaisesRegex(ValueError, 'native integration unavailable'):
            self.manager.change('install', ['claude', 'muse'])
        self.assertFalse(self.manager.state_path.exists())
        self.assertEqual(self.drivers.installed, set())
        self.assert_unrelated()

    def test_existing_empty_plugin_array_survives_removal(self):
        path = self.home / manage.CONFIGS['opencode'][0]
        data = json.loads(path.read_text()); data['plugin'] = []
        path.write_bytes(manage.dump(data))
        self.manager.change('install', ['opencode'])
        self.manager.change('uninstall', [])
        self.assertEqual(json.loads(path.read_text()), data)

    def test_successful_cli_update_with_stale_version_rolls_back_without_state_commit(self):
        self.manager.change('install', ['gemini'])
        prior_release = self.manager.state()['release']
        prior_version = self.drivers.versions['gemini']
        self.drivers.stale_updates.add('gemini')
        with self.assertRaisesRegex(RuntimeError, 'installed native version does not match'):
            self.manager.change('update', [])
        self.assertEqual(self.manager.state()['release'], prior_release)
        self.assertEqual(self.manager.current.resolve(), self.manager.root / 'releases' / prior_release)
        self.assertEqual(self.drivers.versions['gemini'], prior_version)
        self.assertTrue(all(row['status'] == 'configured' for row in self.manager.status()['hosts']))

    def install_legacy_grok_record(self):
        release = self.manager.root / 'releases/legacy'; (release / 'dist').mkdir(parents=True)
        (release / 'dist/cli.js').write_text('// old\n'); (release / 'skills/jev-kit').mkdir(parents=True)
        self.manager.current.symlink_to(release)
        self.manager.launcher.parent.mkdir(parents=True, exist_ok=True)
        self.manager.launcher.write_text('#!/bin/sh\n'); self.manager.launcher.chmod(0o755)
        config = self.home / manage.CONFIGS['grok'][0]
        config.write_bytes(manage.rewrite('grok', config.read_bytes(), None, manage.entry('grok', self.manager.launcher)))
        skill = self.home / manage.SKILLS['grok']; skill.parent.mkdir(parents=True, exist_ok=True); skill.symlink_to(release / 'skills/jev-kit')
        self.manager.state_path.write_bytes(manage.dump({'format': 1, 'release': 'legacy', 'hosts': {
            'grok': {'entry': manage.entry('grok', self.manager.launcher),
                     'links': {manage.SKILLS['grok']: str(release / 'skills/jev-kit')}}}}))

    def test_legacy_grok_rollback_restores_mcp_and_keeps_cli_policy_change(self):
        self.install_legacy_grok_record()
        self.drivers.rewrite_grok_policy = True
        real_put = native.put
        def fail_state(path, desired):
            if path == self.manager.state_path:
                raise OSError('simulated full disk')
            real_put(path, desired)
        with patch.object(native, 'put', fail_state):
            with self.assertRaisesRegex(RuntimeError, 'simulated full disk'):
                self.manager.change('update', [])
        config = (self.home / '.grok/config.toml').read_text()
        self.assertIn('[mcp_servers.jev-kit]', config)
        self.assertIn('enabled = ["jev-kit", "other"]', config)
        self.assertNotIn('grok', self.drivers.installed)
        self.assertEqual(self.manager.state()['format'], 1)

    def test_fresh_native_install_failure_leaves_no_mcp_entry(self):
        real_put = native.put
        def fail_state(path, desired):
            if path == self.manager.state_path:
                raise OSError('simulated full disk')
            real_put(path, desired)
        with patch.object(native, 'put', fail_state):
            with self.assertRaisesRegex(RuntimeError, 'simulated full disk'):
                self.manager.change('install', ['grok'])
        config = manage.parsed('grok', (self.home / '.grok/config.toml').read_bytes())
        self.assertNotIn(manage.NAME, config.get('mcp_servers', {}))
        self.assertFalse(self.manager.state_path.exists())


if __name__ == '__main__':
    unittest.main()
