#!/usr/bin/env python3
"""Manage Jev Kit integrations. Standard library only; macOS/Linux, Python 3.11+."""
import argparse
import contextlib
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import tomllib

NAME = 'jev-kit'
MARKET = 'jev-kit-managed'
REPOSITORY = 'https://github.com/WaynezProg/jev-kit.git'
SOURCE = Path(__file__).resolve().parents[1]
CONFIGS = {
    'claude': ('.claude.json', 'mcpServers'),
    'opencode': ('.config/opencode/opencode.json', 'mcp'),
    'muse': ('.config/muse/settings.json', 'mcpServers'),
    'grok': ('.grok/config.toml', 'mcp_servers'),
    'gemini': ('.gemini/settings.json', 'mcpServers'),
    'cursor': ('.cursor/mcp.json', 'mcpServers'),
    'vscode': ('Library/Application Support/Code/User/mcp.json' if sys.platform == 'darwin' else '.config/Code/User/mcp.json', 'servers'),
}
SKILLS = {
    'claude': '.claude/skills/jev-kit', 'opencode': '.config/opencode/skills/jev-kit',
    'muse': '.agents/skills/jev-kit', 'grok': '.grok/skills/jev-kit',
    'gemini': '.gemini/skills/jev-kit', 'cursor': '.cursor/skills/jev-kit',
    'pi': '.pi/agent/skills/jev-kit',
}
HOSTS = ['codex', *CONFIGS, 'pi']
PAYLOAD = ['dist', 'src', 'scripts', 'skills', 'vendor', 'examples', '.codex-plugin',
           'jev', 'package.json', 'package-lock.json', 'README.md', 'LICENSE', 'THIRD_PARTY.md']


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, timeout=120, **kwargs).stdout


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def entry(host, launcher):
    if host == 'opencode':
        return {'type': 'local', 'command': [str(launcher)], 'enabled': True}
    if host == 'muse':
        return {'transport': 'stdio', 'command': str(launcher), 'mode': 'optional'}
    if host == 'grok':
        return {'command': str(launcher), 'args': [], 'enabled': True}
    return {'type': 'stdio', 'command': str(launcher), 'args': []}


def parsed(host, raw):
    return tomllib.loads(raw.decode()) if host == 'grok' else json.loads(raw or b'{}')


def rewrite(host, raw, expected, replacement):
    """Compare just our entry; preserve all unrelated semantic data and TOML text."""
    data = parsed(host, raw)
    key = CONFIGS[host][1]
    servers = data.get(key, {})
    if not isinstance(servers, dict):
        raise ValueError(f'{host}: {key} must be an object')
    if servers.get(NAME) != expected:
        raise ValueError(f'{host}: Jev entry changed or belongs to another installation')
    if host == 'muse' and 'mcp_servers' in data:
        raise ValueError('Muse: conflicting legacy mcp_servers field; inspect first')
    if host == 'grok' and replacement is not None and NAME in data.get('disabled_mcp_servers', []):
        raise ValueError('Grok: Jev is explicitly disabled')
    wanted = copy.deepcopy(data)
    if replacement is None:
        wanted.get(key, {}).pop(NAME, None)
    else:
        wanted.setdefault(key, {})[NAME] = replacement
    if host != 'grok':
        return dump(wanted)
    text = raw.decode()
    if expected is not None:
        # Only our exact table is edited. Unusual/inline/nested TOML refuses safely.
        pattern = r'(?m)^\[mcp_servers\.(?:jev-kit|"jev-kit"|\'jev-kit\')\][ \t]*(?:#[^\n]*)?\n[\s\S]*?(?=^\[|\Z)'
        text, count = re.subn(pattern, '', text)
        if count != 1:
            raise ValueError('Grok: cannot safely locate the Jev TOML table')
    if replacement is not None:
        text = text.rstrip() + '\n\n[mcp_servers.jev-kit]\ncommand = ' + json.dumps(replacement['command']) + '\nargs = []\nenabled = true\n'
    result = tomllib.loads(text)
    # Removing the only child table can remove its implicit parent as well.
    if not wanted.get(key):
        wanted.pop(key, None)
    if not result.get(key):
        result.pop(key, None)
    if result != wanted:
        raise ValueError('Grok: edit would affect unrelated TOML; refusing')
    return text.encode()


def snapshot(path):
    if path.is_symlink():
        return ('link', os.readlink(path), 0)
    if path.is_file():
        return ('file', path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
    if path.exists():
        raise ValueError(f'Expected file or link: {path}')
    return ('absent', None, 0)


def put(path, value):
    kind, data, mode = value
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == 'absent':
        path.unlink(missing_ok=True)
        return
    fd, temp = tempfile.mkstemp(prefix='.jev-', dir=path.parent)
    try:
        os.close(fd)
        if kind == 'link':
            os.unlink(temp)
            os.symlink(data, temp)
        else:
            os.chmod(temp, mode)
            with open(temp, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.lexists(temp):
            os.unlink(temp)


class Manager:
    def __init__(self, home, node=None, codex=None):
        self.home = Path(home).resolve()
        self.root = self.home / '.local/share/jev-kit'
        self.state_path = self.root / 'state.json'
        self.current = self.root / 'current'
        self.launcher = self.root / 'serve'
        self.node = node or shutil.which('node')
        self.codex = codex or shutil.which('codex')
        self.env = {**os.environ, 'HOME': str(self.home), 'CODEX_HOME': str(self.home / '.codex')}

    def state(self):
        return json.loads(self.state_path.read_text()) if self.state_path.exists() else {'format': 1, 'hosts': {}}

    @contextlib.contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.root / 'lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

    def codex_call(self, *args):
        if not self.codex:
            raise ValueError('Codex CLI is required for the native Codex plugin')
        (self.home / '.codex').mkdir(parents=True, exist_ok=True, mode=0o700)
        return run([self.codex, 'plugin', *args], env=self.env)

    def codex_existing(self):
        return [x for x in json.loads(self.codex_call('list', '--json')).get('installed', []) if x.get('name') == NAME]

    def detect(self):
        found = [h for h, (rel, _) in CONFIGS.items() if (self.home / rel).exists()]
        if self.codex and (self.home / '.codex').is_dir():
            found.insert(0, 'codex')
        if (self.home / '.pi/agent').is_dir():
            found.append('pi')
        return found

    def status(self):
        state = self.state()
        rows = []
        for host, record in state['hosts'].items():
            problems = []
            if host in CONFIGS:
                try:
                    raw = (self.home / CONFIGS[host][0]).read_bytes()
                    if parsed(host, raw).get(CONFIGS[host][1], {}).get(NAME) != record['entry']:
                        problems.append('entry_changed')
                except (OSError, ValueError):
                    problems.append('config_missing_or_invalid')
            if host == 'codex':
                try:
                    if not any(p['pluginId'] == NAME + '@' + MARKET and p.get('enabled') for p in self.codex_existing()):
                        problems.append('plugin_missing_or_disabled')
                except (ValueError, subprocess.SubprocessError):
                    problems.append('codex_diagnostic_failed')
            for rel, target in record.get('links', {}).items():
                if snapshot(self.home / rel) != ('link', target, 0):
                    problems.append('link_changed:' + rel)
            rows.append({'host': host, 'status': 'configured' if not problems else 'drift', 'problems': problems})
        return {'release': state.get('release'), 'hosts': rows, 'runtime_ready': (self.current / 'dist/cli.js').is_file(),
                'note': 'Configuration status is not native host connectivity; restart existing sessions after changes.'}

    def prepare_release(self, source):
        if not self.node or int(run([self.node, '--version']).strip().lstrip('v').split('.')[0]) < 22:
            raise ValueError('Node.js 22+ is required')
        source = Path(source).resolve()
        files = []
        for item in PAYLOAD:
            path = source / item
            if not path.exists():
                raise ValueError(f'Missing release component: {item}')
            for p in sorted(path.rglob('*')) if path.is_dir() else [path]:
                if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and p.suffix != '.pyc' and p != source / 'scripts/serve':
                    files.append((p.relative_to(source), p))
        digest = hashlib.sha256()
        for rel, p in files:
            digest.update(str(rel).encode() + b'\0' + p.read_bytes() + b'\0')
        release_id = digest.hexdigest()[:20]
        destination = self.root / 'releases' / release_id
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix='.stage-', dir=destination.parent))
            try:
                for rel, p in files:
                    (temporary / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, temporary / rel)
                manifest = json.loads((temporary / '.codex-plugin/plugin.json').read_text())
                manifest['version'] = manifest['version'].split('+')[0] + '+codex.' + release_id
                (temporary / '.codex-plugin/plugin.json').write_bytes(dump(manifest))
                (temporary / '.mcp.json').write_bytes(dump({'mcpServers': {NAME: {'command': str(self.launcher), 'args': []}}}))
                run([self.node, str(temporary / 'dist/cli.js'), 'evidence', '--input', str(temporary / 'examples/evidence.json'), '--validate-only'])
                temporary.rename(destination)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
        return release_id, destination

    def change(self, action, hosts, source=SOURCE, adopt=None):
        with self.locked():
            state = self.state()
            if state.get('release') and snapshot(self.current) != ('link', str(self.root / 'releases' / state['release']), 0):
                raise ValueError('Managed runtime pointer changed; inspect before updating or removing integrations')
            if not hosts:
                hosts = list(state['hosts']) if action in ('update', 'uninstall') else self.detect()
            if not hosts:
                return {'action': action, 'hosts': [], 'note': 'No hosts detected. Select --hosts explicitly.'}
            if any(h not in HOSTS for h in hosts):
                raise ValueError('Unknown host; choose: ' + ','.join(HOSTS))
            if action == 'update' and set(hosts) != set(state['hosts']):
                raise ValueError('Update applies to all managed hosts because they share one runtime')
            changes, next_state = [], copy.deepcopy(state)
            old_codex = []
            adopt = Path(adopt).resolve() if adopt else None
            def add(path, desired):
                original = snapshot(path)
                if original != desired:
                    changes.append((path, original, desired))
            for host in hosts:
                record = state['hosts'].get(host)
                if action == 'uninstall' and not record:
                    continue  # Never remove an installation we do not own.
                if host in CONFIGS:
                    path = self.home / CONFIGS[host][0]
                    if path.is_symlink():
                        raise ValueError(f'{host}: configuration is a symlink; refusing to replace it')
                    raw = path.read_bytes() if path.exists() else b''
                    expected = record['entry'] if record else None
                    existing = parsed(host, raw).get(CONFIGS[host][1], {}).get(NAME)
                    if not record and existing is not None and adopt:
                        if existing != entry(host, adopt / 'scripts/serve'):
                            raise ValueError(f'{host}: entry does not exactly match --adopt-from')
                        expected = existing
                    desired = None if action == 'uninstall' else entry(host, self.launcher)
                    new = rewrite(host, raw, expected, desired)
                    add(path, ('file', new, stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600))
                if host == 'codex':
                    markets = json.loads(self.codex_call('marketplace', 'list', '--json')).get('marketplaces', [])
                    if any(x.get('name') == MARKET and Path(x['root']).resolve() != (self.root / 'marketplace').resolve() for x in markets):
                        raise ValueError('Codex marketplace name belongs to another installation')
                    installed = self.codex_existing()
                    external = [p for p in installed if p['pluginId'] != NAME + '@' + MARKET]
                    if external:
                        if not adopt or action == 'uninstall' or any(Path(p.get('source', {}).get('path', '')).resolve() != adopt for p in external):
                            raise ValueError('Existing Codex Jev plugin is not managed; use --adopt-from with its exact source to migrate')
                        old_codex = external
                    if record and not any(p['pluginId'] == NAME + '@' + MARKET and p.get('enabled') for p in installed):
                        raise ValueError('Codex managed plugin missing or disabled; refusing to override manual changes')
                    if not record and any(p['pluginId'] == NAME + '@' + MARKET for p in installed):
                        raise ValueError('Codex plugin exists without ownership state; refusing to adopt implicitly')
                links = {}
                if host in SKILLS:
                    links[SKILLS[host]] = str(self.current / 'skills/jev-kit')
                if host == 'pi':
                    links['.pi/agent/extensions/jev-kit.js'] = str(self.current / 'dist/pi-extension.js')
                for rel, target in links.items():
                    path = self.home / rel
                    actual = snapshot(path)
                    expected_link = ('link', target, 0)
                    if record and actual != expected_link:
                        raise ValueError(f'{host}: managed link changed: {rel}')
                    if not record and actual[0] != 'absent':
                        legacy_target = adopt / ('dist/pi-extension.js' if rel.endswith('.js') else 'skills/jev-kit') if adopt else None
                        if not legacy_target or not path.is_symlink() or path.resolve() != legacy_target.resolve():
                            raise ValueError(f'{host}: existing Skill/extension is not owned: {rel}')
                    add(path, ('absent', None, 0) if action == 'uninstall' else expected_link)
                if action == 'uninstall':
                    next_state['hosts'].pop(host, None)
                else:
                    next_state['hosts'][host] = {'links': links}
                    if host in CONFIGS:
                        next_state['hosts'][host]['entry'] = desired
            if action != 'uninstall':
                release_id, release = self.prepare_release(source)
                if action == 'install' and state['hosts'] and state.get('release') != release_id:
                    raise ValueError('Run update before adding hosts from a different release; existing hosts share the runtime')
                add(self.current, ('link', str(release), 0))
                add(self.launcher, ('file', ('#!/bin/sh\nexec ' + shlex.quote(self.node) + ' ' + shlex.quote(str(self.current / 'dist/cli.js')) + ' serve "$@"\n').encode(), 0o755))
                add(self.root / 'jev', ('file', ('#!/bin/sh\nexec python3 ' + shlex.quote(str(self.current / 'scripts/manage.py')) + ' "$@"\n').encode(), 0o755))
                next_state['release'] = release_id
            if 'codex' in hosts and action != 'uninstall':
                market = self.root / 'marketplace'
                add(market / 'plugins/jev-kit', ('link', str(self.current), 0))
                descriptor = {'name': MARKET, 'plugins': [{'name': NAME, 'source': {'source': 'local', 'path': './plugins/jev-kit'}, 'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'}, 'category': 'Productivity'}]}
                add(market / '.agents/plugins/marketplace.json', ('file', dump(descriptor), 0o600))
            receipt = self.root / 'receipts' / (str(time.time_ns()) + '-' + action)
            receipt.mkdir(parents=True, mode=0o700)
            journal = []
            for i, (path, original, desired) in enumerate(changes):
                if original[0] == 'file':
                    backup = receipt / str(i)
                    backup.write_bytes(original[1]); backup.chmod(0o600)
                journal.append({'path': str(path), 'before': original[0], 'after': desired[0]})
            (receipt / 'journal.json').write_bytes(dump({'action': action, 'changes': journal, 'status': 'prepared'}))
            applied, native_started = [], False
            try:
                for path, original, desired in changes:
                    if snapshot(path) != original:
                        raise ValueError(f'Concurrent change detected: {path}')
                    put(path, desired); applied.append((path, original, desired))
                if 'codex' in hosts and (action != 'uninstall' or 'codex' in state['hosts']):
                    native_started = True
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
                rollback_errors = []
                for path, original, desired in reversed(applied):
                    try:
                        if snapshot(path) != desired:
                            raise ValueError('changed again; preserved')
                        put(path, original)
                    except Exception as rollback_error:
                        rollback_errors.append(str(path) + ': ' + str(rollback_error))
                if native_started:
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
                        rollback_errors.append('Codex native rollback failed; inspect plugin list and receipt')
                (receipt / 'result.json').write_bytes(dump({'status': 'failed', 'rollback_errors': rollback_errors}))
                raise RuntimeError(f'{action} failed: {error}; rollback issues: {rollback_errors}; receipt: {receipt}') from error
            result = {'action': action, 'hosts': hosts, 'release': next_state.get('release'), 'receipt': str(receipt),
                      'restart_required': action != 'uninstall', 'retained': 'API keys, unrelated settings, private backups and release snapshots'}
            (receipt / 'result.json').write_bytes(dump(result))
            return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'update', 'uninstall', 'status'])
    parser.add_argument('--hosts', help='Comma-separated hosts; default detects installed hosts, or all managed hosts for update/uninstall')
    parser.add_argument('--source', type=Path, help='Local release source; update defaults to latest GitHub main')
    parser.add_argument('--home', type=Path, default=Path.home(), help='Alternate home for isolated validation')
    parser.add_argument('--adopt-from', type=Path, help='Migrate only legacy entries/links exactly matching this source checkout')
    args = parser.parse_args(argv)
    manager = Manager(args.home)
    hosts = HOSTS.copy() if args.hosts == 'all' else list(dict.fromkeys(args.hosts.split(','))) if args.hosts else []
    try:
        if args.action == 'status':
            result = manager.status()
        elif args.action == 'update' and not args.source:
            if not manager.state()['hosts']:
                raise ValueError('No managed hosts; install first')
            with tempfile.TemporaryDirectory(prefix='jev-kit-update-') as temp:
                run(['git', 'clone', '--depth', '1', '--branch', 'main', REPOSITORY, temp])
                result = manager.change('update', hosts, Path(temp), args.adopt_from)
        else:
            result = manager.change(args.action, hosts, args.source or SOURCE, args.adopt_from)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        # Do not print captured host stdout/stderr, which may contain unrelated secrets.
        print('Jev Kit: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
