"""Build self-contained native host packages around the shared Jev runtime."""
import json
from pathlib import Path
import shutil


NAME = 'jev-kit'
HOSTS = ('claude', 'gemini', 'muse', 'grok', 'cursor', 'vscode')
DESCRIPTION = ('Optional candidate reranking, evidence checks, classification, extraction and '
               'bounded decisions with validated Jev responses.')
AGENT_PLUGIN_MCP_SCHEMA = 'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json'


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def _version(release_root: Path, release_id: str) -> str:
    base = json.loads((release_root / 'package.json').read_text())['version'].split('+', 1)[0]
    return f'{base}+native.{release_id}'


def _mcp(launcher: str) -> dict:
    return {'mcpServers': {NAME: {'command': launcher, 'args': []}}}


def _agent_plugin_mcp(launcher: str) -> dict:
    return {'$schema': AGENT_PLUGIN_MCP_SCHEMA,
            'mcpServers': {NAME: {'type': 'stdio', 'command': launcher, 'args': []}}}


def _copy_payload(release_root: Path, package: Path) -> None:
    shutil.copytree(release_root / 'skills' / NAME, package / 'skills' / NAME, symlinks=False)
    shutil.copy2(release_root / 'LICENSE', package / 'LICENSE')


def _wrapper(package: Path, launcher: str) -> None:
    script = """import { spawn } from 'node:child_process';

const child = spawn(%s, process.argv.slice(2), { stdio: 'inherit' });
const forward = signal => { if (!child.killed) child.kill(signal); };
process.on('SIGINT', () => forward('SIGINT'));
process.on('SIGTERM', () => forward('SIGTERM'));
child.on('error', error => { console.error(error.message); process.exit(1); });
child.on('exit', (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  process.exit(code ?? 1);
});
""" % json.dumps(launcher)
    path = package / 'mcp' / 'serve.mjs'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script)


def _common(version: str) -> dict:
    return {'name': NAME, 'version': version, 'description': DESCRIPTION,
            'author': {'name': 'Jev Kit contributors'}}


def _manifest(host: str, package: Path, node: str, launcher: str, version: str) -> None:
    direct_mcp = _mcp(launcher)
    if host == 'claude':
        data = _common(version)
        data.update({'skills': './skills/', 'mcpServers': './.mcp.json'})
        _write(package / '.claude-plugin' / 'plugin.json', data)
        _write(package / '.mcp.json', direct_mcp)
    elif host == 'gemini':
        data = _common(version)
        data.update({'mcpServers': direct_mcp['mcpServers']})
        _write(package / 'gemini-extension.json', data)
    elif host == 'muse':
        data = {
            'schemaVersion': 1, 'name': NAME, 'displayName': 'Jev Kit', 'version': version,
            'description': DESCRIPTION,
            'compat': {'source': 'native', 'manifestDir': '.muse-plugin'},
            'capabilities': {
                'skills': [{'id': NAME, 'path': 'skills/jev-kit/SKILL.md', 'enabledDefault': True}],
                'commands': [], 'hooks': [],
                'mcpServers': [{'id': NAME, 'transport': 'stdio', 'command': [launcher]}],
                'reminders': [],
            },
        }
        _write(package / '.muse-plugin' / 'plugin.json', data)
    elif host == 'grok':
        _write(package / 'plugin.json', _common(version))
        _write(package / '.mcp.json', direct_mcp)
    elif host == 'cursor':
        data = _common(version)
        data.update({'skills': './skills/'})
        _write(package / '.cursor-plugin' / 'plugin.json', data)
        _write(package / 'mcp.json', direct_mcp)
    elif host == 'vscode':
        data = _common(version)
        data.update({'$schema': 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'})
        _write(package / 'plugin.json', data)
        _write(package / 'mcp.json', _agent_plugin_mcp(launcher))


def build_packages(release_root: Path, node: str, launcher: str, release_id: str) -> None:
    """Write native packages below ``release_root/native`` for supported hosts.

    Each package copies its Skill and license, while the process it starts remains
    the manager-owned absolute launcher so no runtime or credentials are bundled.
    """
    release_root = Path(release_root)
    version = _version(release_root, release_id)
    for host in HOSTS:
        package = release_root / 'native' / host / NAME
        if package.exists():
            shutil.rmtree(package)
        _copy_payload(release_root, package)
        _wrapper(package, launcher)
        _manifest(host, package, node, launcher, version)
