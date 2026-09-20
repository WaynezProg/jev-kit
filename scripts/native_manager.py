"""Transactional native integration layer; legacy MCP records migrate in place."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import time

from manage import (Manager, CONFIGS, SKILLS, HOSTS, SOURCE, NAME, MARKET,
                    dump, entry, parsed, rewrite, snapshot, put)
from native_drivers import NativeDrivers, HOSTS as CLI_HOSTS

ABSENT = ('absent', None, 0)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_config(path):
    if path.is_symlink():
        raise ValueError(f'Configuration is a symlink; refusing to replace: {path}')
    return path.read_bytes() if path.exists() else b''


def json_registration(raw, host, registration, expected, wanted, remove_empty=False):
    data = json.loads(raw or b'{}')
    if host == 'opencode':
        plugins = data.get('plugin', [])
        if not isinstance(plugins, list) or any(not isinstance(p, str) for p in plugins):
            raise ValueError('OpenCode plugin must be an array of strings')
        if plugins.count(registration) != int(expected):
            raise ValueError('OpenCode native registration changed or is unowned')
        if wanted and not expected:
            data['plugin'] = [*plugins, registration]
        elif expected and not wanted:
            data['plugin'] = [p for p in plugins if p != registration]
            if remove_empty and not data['plugin']:
                data.pop('plugin')
    else:
        locations = data.get('chat.pluginLocations', {})
        if not isinstance(locations, dict):
            raise ValueError('VS Code chat.pluginLocations must be an object')
        if (registration in locations) != expected or (expected and locations[registration] is not True):
            raise ValueError('VS Code native registration changed or is unowned')
        if wanted and data.get('chat.plugins.enabled') is False:
            raise ValueError('VS Code native plugins are explicitly disabled')
        if wanted:
            data.setdefault('chat.pluginLocations', {})[registration] = True
        else:
            data.get('chat.pluginLocations', {}).pop(registration, None)
            if remove_empty and not data.get('chat.pluginLocations'):
                data.pop('chat.pluginLocations', None)
    return dump(data)


class NativeManager(Manager):
    def __init__(self, home, node=None, codex=None, integration='auto', drivers=None):
        super().__init__(home, node, codex)
        self.integration = integration
        self.drivers = drivers or NativeDrivers(self.home, self.root)

    def kind(self, host, record, action):
        old = (record or {}).get('kind', 'native' if host in ('codex', 'pi') else 'mcp')
        if action == 'uninstall':
            return old, None
        if host in ('codex', 'pi'):
            return 'native', None
        if self.integration == 'mcp':
            if old == 'native':
                raise ValueError(f'{host}: uninstall native integration before selecting MCP mode')
            return 'mcp', 'explicit MCP mode'
        if host in CLI_HOSTS:
            try:
                capability = self.drivers.probe(host)
            except ValueError as error:
                if 'CLI is not installed' not in str(error):
                    raise
                capability = {'available': False, 'reason': 'host CLI is not installed'}
            if not capability['available']:
                if self.integration == 'native' or old == 'native':
                    raise ValueError(f'{host}: native integration unavailable: {capability["reason"]}')
                return 'mcp', capability['reason']
        return 'native', None

    def package_path(self, host):
        if host == 'cursor':
            return self.home / '.cursor/plugins/local/jev-kit'
        if host in CLI_HOSTS:
            return self.drivers.package_path(host)
        return self.root / 'native' / host / NAME

    def registration(self, host):
        if host == 'opencode':
            return (self.current / 'dist/opencode-plugin.js').as_uri()
        return str(self.package_path(host))

    def settings_path(self, host):
        if host == 'opencode':
            return self.home / CONFIGS[host][0]
        return (self.home / CONFIGS['vscode'][0]).with_name('settings.json')

    def check_native(self, host):
        row = self.drivers.check(host, self.package_path(host), True)
        manifest = {'claude': '.claude-plugin/plugin.json', 'gemini': 'gemini-extension.json',
                    'grok': 'plugin.json', 'muse': '.muse-plugin/plugin.json'}[host]
        expected = json.loads((self.package_path(host) / manifest).read_text())['version']
        if not row or row.get('version') != expected:
            raise ValueError(f'{host}: installed native version does not match the managed package')
        return row

    def check_files(self, host, record):
        files = record.get('files', {})
        for rel, digest in files.items():
            path = self.home / rel
            if path.is_symlink() or not path.is_file() or file_hash(path) != digest:
                raise ValueError(f'{host}: managed package file changed: {rel}')
        if files:
            root = self.package_path(host)
            if host == 'claude':
                # Removing this marketplace unregisters everything it contains.
                # Refuse sibling content, not just edits inside our own plugin.
                root = root.parent.parent
            actual = {str(p.relative_to(self.home)) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
            expected = {r for r in files if Path(r).is_relative_to(root.relative_to(self.home))}
            if actual != expected:
                raise ValueError(f'{host}: package contains unowned files; inspect before changing')

    def status(self):
        state = self.state()
        rows = []
        for host, record in state['hosts'].items():
            kind = record.get('kind', 'native' if host in ('codex', 'pi') else 'mcp')
            problems = []
            try:
                self.check_files(host, record)
                if host in CONFIGS:
                    actual = parsed(host, read_config(self.home / CONFIGS[host][0])).get(CONFIGS[host][1], {}).get(NAME)
                    if actual != record.get('entry'):
                        problems.append('mcp_entry_changed_or_duplicated')
                for rel, target in record.get('links', {}).items():
                    if snapshot(self.home / rel) != ('link', target, 0):
                        problems.append('link_changed:' + rel)
                if host == 'codex':
                    if not any(p['pluginId'] == NAME + '@' + MARKET and p.get('enabled') for p in self.codex_existing()):
                        problems.append('plugin_missing_or_disabled')
                elif kind == 'native' and host in CLI_HOSTS:
                    self.check_native(host)
                elif kind == 'native' and host in ('opencode', 'vscode'):
                    json_registration(read_config(self.settings_path(host)), host, record['registration'], True, True)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                problems.append(str(error))
            rows.append({'host': host, 'integration': kind, 'status': 'configured' if not problems else 'drift',
                         'fallback_reason': record.get('fallback_reason'), 'problems': problems})
        return {'release': state.get('release'), 'hosts': rows, 'runtime_ready': (self.current / 'dist/cli.js').is_file(),
                'note': 'Configuration and native inventory checks only; restart hosts and verify tool loading separately.'}

    def change(self, action, hosts, source=SOURCE, adopt=None):
        with self.locked():
            state = self.state()
            if state.get('release') and snapshot(self.current) != ('link', str(self.root / 'releases' / state['release']), 0):
                raise ValueError('Managed runtime pointer changed; inspect before changing integrations')
            hosts = hosts or (list(state['hosts']) if action != 'install' else self.detect())
            if not hosts:
                return {'action': action, 'hosts': [], 'note': 'No hosts detected. Select --hosts explicitly.'}
            if any(h not in HOSTS for h in hosts):
                raise ValueError('Unknown host; choose: ' + ','.join(HOSTS))
            if action == 'update' and set(hosts) != set(state['hosts']):
                raise ValueError('Update applies to all managed hosts because they share one runtime')
            active = [h for h in hosts if action != 'uninstall' or h in state['hosts']]
            modes = {h: self.kind(h, state['hosts'].get(h), action) for h in active}
            next_state = copy.deepcopy(state)
            next_state['format'] = 2
            changes, cli_actions, old_codex = [], [], []
            adopt = Path(adopt).resolve() if adopt else None

            def add(path, desired, transform=None):
                original = snapshot(path)
                if original != desired:
                    changes.append((path, original, desired, transform))

            def config(path, transform):
                raw = read_config(path)
                new = transform(raw, False)
                mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
                add(path, ('file', new, mode), transform)

            # Preflight every selected host before preparing or changing its files.
            for host in active:
                record = state['hosts'].get(host, {})
                kind, reason = modes[host]
                old_native = record.get('kind') == 'native'
                self.check_files(host, record)
                if host in CLI_HOSTS and kind == 'native':
                    if old_native:
                        self.check_native(host)
                    else:
                        self.drivers.check(host, self.package_path(host), False)
                    cli_actions.append((host, old_native))
                if host == 'codex':
                    markets = json.loads(self.codex_call('marketplace', 'list', '--json')).get('marketplaces', [])
                    if any(x.get('name') == MARKET and Path(x['root']).resolve() != (self.root / 'marketplace').resolve() for x in markets):
                        raise ValueError('Codex marketplace name belongs to another installation')
                    installed = self.codex_existing()
                    external = [p for p in installed if p['pluginId'] != NAME + '@' + MARKET]
                    if external:
                        if not adopt or action == 'uninstall' or any(Path(p.get('source', {}).get('path', '')).resolve() != adopt for p in external):
                            raise ValueError('Existing Codex Jev plugin is not managed; use --adopt-from with its exact source')
                        old_codex = external
                    if record and not any(p['pluginId'] == NAME + '@' + MARKET and p.get('enabled') for p in installed):
                        raise ValueError('Codex managed plugin missing or disabled; refusing to override manual changes')
                    if not record and any(p['pluginId'] == NAME + '@' + MARKET for p in installed):
                        raise ValueError('Codex plugin exists without ownership state')
                expected_entry = record.get('entry')
                if host in CONFIGS and not record and adopt:
                    actual = parsed(host, read_config(self.home / CONFIGS[host][0])).get(CONFIGS[host][1], {}).get(NAME)
                    if actual is not None:
                        if actual != entry(host, adopt / 'scripts/serve'):
                            raise ValueError(f'{host}: MCP entry does not exactly match --adopt-from')
                        expected_entry = actual
                desired_entry = entry(host, self.launcher) if action != 'uninstall' and kind == 'mcp' else None
                registration = self.registration(host) if host in ('opencode', 'vscode') else None
                was_registered = old_native and bool(record.get('registration'))
                want_registered = action != 'uninstall' and kind == 'native'
                container_created = False
                if host in ('opencode', 'vscode'):
                    field = 'plugin' if host == 'opencode' else 'chat.pluginLocations'
                    container_created = record.get('registration_container_created',
                        field not in json.loads(read_config(self.settings_path(host)) or b'{}'))
                if was_registered and record['registration'] != registration:
                    raise ValueError(f'{host}: native registration source changed')
                if host in CONFIGS:
                    def patch_mcp(raw, reverse, h=host, before=expected_entry, after=desired_entry,
                                  reg=registration, was=was_registered, want=want_registered,
                                  created=container_created):
                        raw = rewrite(h, raw, after if reverse else before, before if reverse else after)
                        if h == 'opencode':
                            raw = json_registration(raw, h, reg, want if reverse else was, was if reverse else want, created)
                        return raw
                    config(self.home / CONFIGS[host][0], patch_mcp)
                if host == 'vscode':
                    def patch_registration(raw, reverse, reg=registration, was=was_registered, want=want_registered, created=container_created):
                        return json_registration(raw, 'vscode', reg, want if reverse else was, was if reverse else want, created)
                    config(self.settings_path(host), patch_registration)
                links = {}
                if host in SKILLS and (kind == 'mcp' or host in ('pi', 'opencode')) and action != 'uninstall':
                    links[SKILLS[host]] = str(self.current / 'skills/jev-kit')
                if host == 'pi' and action != 'uninstall':
                    links['.pi/agent/extensions/jev-kit.js'] = str(self.current / 'dist/pi-extension.js')
                known_links = dict(record.get('links', {}))
                if not record and host in SKILLS:
                    known_links[SKILLS[host]] = None
                if not record and host == 'pi':
                    known_links['.pi/agent/extensions/jev-kit.js'] = None
                for rel in known_links.keys() | links.keys():
                    path = self.home / rel
                    actual = snapshot(path)
                    if known_links.get(rel):
                        if actual != ('link', known_links[rel], 0):
                            raise ValueError(f'{host}: managed link changed: {rel}')
                    elif actual != ABSENT:
                        legacy = adopt / ('dist/pi-extension.js' if rel.endswith('.js') else 'skills/jev-kit') if adopt else None
                        if not legacy or not path.is_symlink() or path.resolve() != legacy.resolve():
                            raise ValueError(f'{host}: existing Skill/extension is unowned: {rel}')
                    add(path, ('link', links[rel], 0) if rel in links else ABSENT)
                if action == 'uninstall':
                    next_state['hosts'].pop(host, None)
                else:
                    next_state['hosts'][host] = {'kind': kind, 'links': links}
                    if desired_entry is not None:
                        next_state['hosts'][host]['entry'] = desired_entry
                    if reason:
                        next_state['hosts'][host]['fallback_reason'] = reason
                    if registration and want_registered:
                        next_state['hosts'][host]['registration'] = registration
                        next_state['hosts'][host]['registration_container_created'] = container_created

            if action != 'uninstall':
                release_id, release = self.prepare_release(source)
                if action == 'install' and state['hosts'] and state.get('release') != release_id:
                    raise ValueError('Run update before adding hosts from a different release')
                add(self.current, ('link', str(release), 0))
                add(self.launcher, ('file', ('#!/bin/sh\nexec ' + shlex.quote(self.node) + ' ' + shlex.quote(str(self.current / 'dist/cli.js')) + ' serve "$@"\n').encode(), 0o755))
                add(self.root / 'jev', ('file', ('#!/bin/sh\nexec python3 ' + shlex.quote(str(self.current / 'scripts/manage.py')) + ' "$@"\n').encode(), 0o755))
                next_state['release'] = release_id
            for host in active:
                old_files = state['hosts'].get(host, {}).get('files', {})
                files = {}
                if action != 'uninstall' and modes[host][0] == 'native' and host not in ('codex', 'pi', 'opencode'):
                    package = self.package_path(host)
                    if not old_files and package.exists() and any(package.iterdir()):
                        raise ValueError(f'{host}: native package directory is unowned')
                    if package.is_symlink():
                        raise ValueError(f'{host}: native package directory must not be a symlink')
                    source_package = release / 'native' / host / NAME
                    for path in source_package.rglob('*'):
                        if path.is_file():
                            target = package / path.relative_to(source_package)
                            rel = str(target.relative_to(self.home))
                            if rel not in old_files and snapshot(target) != ABSENT:
                                raise ValueError(f'{host}: native package file is unowned: {target}')
                            files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
                            add(target, ('file', path.read_bytes(), 0o644))
                    if host == 'claude':
                        target = package.parent.parent / '.claude-plugin/marketplace.json'
                        raw = dump({'name': MARKET, 'owner': {'name': 'Jev Kit contributors'}, 'plugins': [{'name': NAME, 'source': './plugins/jev-kit'}]})
                        rel = str(target.relative_to(self.home))
                        if rel not in old_files and snapshot(target) != ABSENT:
                            raise ValueError('Claude marketplace descriptor is unowned')
                        files[rel] = hashlib.sha256(raw).hexdigest()
                        add(target, ('file', raw, 0o644))
                    next_state['hosts'][host]['files'] = files
                for rel in old_files.keys() - files.keys():
                    add(self.home / rel, ABSENT)
            if 'codex' in active and action != 'uninstall':
                market = self.root / 'marketplace'
                add(market / 'plugins/jev-kit', ('link', str(self.current), 0))
                descriptor = {'name': MARKET, 'plugins': [{'name': NAME, 'source': {'source': 'local', 'path': './plugins/jev-kit'}, 'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'}, 'category': 'Productivity'}]}
                add(market / '.agents/plugins/marketplace.json', ('file', dump(descriptor), 0o600))

            receipt = self.root / 'receipts' / (str(time.time_ns()) + '-' + action)
            receipt.mkdir(parents=True, mode=0o700)
            journal = []
            for i, (path, before, after, _) in enumerate(changes):
                if before[0] == 'file':
                    backup = receipt / str(i)
                    backup.write_bytes(before[1]); backup.chmod(0o600)
                journal.append({'path': str(path), 'before': before[0], 'after': after[0]})
            (receipt / 'journal.json').write_bytes(dump({'action': action, 'status': 'prepared', 'changes': journal}))
            applied, started, codex_started = [], [], False
            try:
                # Remove native registrations while their source files still exist.
                if action == 'uninstall':
                    for host, owned in cli_actions:
                        started.append((host, owned))
                        self.drivers.remove(host, self.package_path(host))
                for path, before, after, transform in changes:
                    # Native Grok removal can edit its policy table. Recheck only our
                    # MCP entry, and retain that native CLI edit plus unrelated data.
                    if transform:
                        raw = read_config(path)
                        desired_raw = transform(raw, False)
                        after = ('file', desired_raw, after[2])
                    elif snapshot(path) != before:
                        raise ValueError(f'Concurrent change detected: {path}')
                    put(path, after); applied.append((path, before, after, transform))
                if action != 'uninstall':
                    for host, owned in cli_actions:
                        started.append((host, owned))
                        if owned:
                            self.drivers.validate(host, self.package_path(host))
                            self.drivers.update(host, self.package_path(host))
                        else:
                            self.drivers.install(host, self.package_path(host))
                        self.check_native(host)
                if 'codex' in active:
                    codex_started = True
                    if action == 'uninstall':
                        self.codex_call('remove', NAME + '@' + MARKET)
                        self.codex_call('marketplace', 'remove', MARKET)
                    else:
                        self.codex_call('marketplace', 'add', str(self.root / 'marketplace'))
                        self.codex_call('add', NAME + '@' + MARKET)
                        for plugin in old_codex:
                            self.codex_call('remove', plugin['pluginId'])
                put(self.state_path, ('file', dump(next_state), 0o600))
            except BaseException as error:
                issues = []
                # New native installs must be removed before their packages disappear.
                for host, owned in reversed(started):
                    if not owned:
                        try:
                            self.drivers.remove(host, self.package_path(host))
                        except Exception:
                            issues.append(host + ': native rollback removal failed')
                for path, before, after, transform in reversed(applied):
                    try:
                        if transform:
                            raw = read_config(path)
                            restored = transform(raw, True)
                            # Restore exact bytes when no other/native fields changed.
                            if raw == after[1]:
                                put(path, before)
                            else:
                                put(path, ('file', restored, before[2] if before[0] == 'file' else 0o600))
                        else:
                            if snapshot(path) != after:
                                raise ValueError('changed again; preserved')
                            put(path, before)
                    except Exception as failure:
                        issues.append(str(path) + ': ' + str(failure))
                for host, owned in started:
                    if owned:
                        try:
                            if action == 'uninstall':
                                self.drivers.install(host, self.package_path(host))
                            else:
                                # Refresh a native cache from the restored source.
                                try:
                                    self.drivers.check(host, self.package_path(host), True)
                                except ValueError as missing:
                                    if not str(missing).endswith('managed native plugin is missing'):
                                        raise
                                    self.drivers.install(host, self.package_path(host))
                                else:
                                    self.drivers.update(host, self.package_path(host))
                            self.check_native(host)
                        except Exception:
                            issues.append(host + ': native rollback refresh failed')
                if codex_started:
                    try:
                        if 'codex' in state['hosts']:
                            self.codex_call('marketplace', 'add', str(self.root / 'marketplace'))
                            self.codex_call('add', NAME + '@' + MARKET)
                        else:
                            if any(p['pluginId'] == NAME + '@' + MARKET for p in self.codex_existing()):
                                self.codex_call('remove', NAME + '@' + MARKET)
                            self.codex_call('marketplace', 'remove', MARKET)
                        for plugin in old_codex:
                            self.codex_call('add', plugin['pluginId'])
                    except Exception:
                        issues.append('Codex native rollback failed')
                (receipt / 'result.json').write_bytes(dump({'status': 'failed', 'rollback_errors': issues}))
                raise RuntimeError(f'{action} failed: {error}; rollback issues: {issues}; receipt: {receipt}') from error
            # Only empty directories inside our package roots can be removed.
            if action == 'uninstall':
                for host in active:
                    if state['hosts'].get(host, {}).get('files'):
                        package = self.package_path(host)
                        for folder in sorted([*package.rglob('*'), package], key=lambda p: len(p.parts), reverse=True):
                            if folder.is_dir() and not folder.is_symlink():
                                try:
                                    folder.rmdir()
                                except OSError:
                                    pass
            result = {'action': action, 'hosts': active, 'integrations': {h: {'kind': modes[h][0], 'fallback_reason': modes[h][1]} for h in active},
                      'release': next_state.get('release'), 'receipt': str(receipt), 'restart_required': bool(active),
                      'retained': 'API keys, unrelated settings, private backups and release snapshots'}
            (receipt / 'result.json').write_bytes(dump(result))
            return result
