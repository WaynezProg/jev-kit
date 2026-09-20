import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    'native_packages', Path(__file__).resolve().parents[1] / 'scripts/native_packages.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class NativePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'skills/jev-kit/references').mkdir(parents=True)
        (self.root / 'skills/jev-kit/SKILL.md').write_text('# Jev Kit\n')
        (self.root / 'skills/jev-kit/references/inputs.md').write_text('Inputs\n')
        (self.root / 'LICENSE').write_text('MIT\n')
        (self.root / 'package.json').write_text(json.dumps({'version': '0.3.0'}))
        native.build_packages(self.root, '/opt/node/bin/node', '/private/runtime/serve', 'a1b2c3')

    def tearDown(self):
        self.temp.cleanup()

    def package(self, host):
        return self.root / 'native' / host / 'jev-kit'

    def read(self, host, path):
        return json.loads((self.package(host) / path).read_text())

    def test_layout_payload_and_containment(self):
        for host in native.HOSTS:
            package = self.package(host)
            self.assertEqual((package / 'skills/jev-kit/SKILL.md').read_text(), '# Jev Kit\n')
            self.assertEqual((package / 'LICENSE').read_text(), 'MIT\n')
            self.assertFalse(any(path.is_symlink() for path in package.rglob('*')))
            self.assertFalse(any('credential' in path.name.lower() or 'secret' in path.name.lower()
                                 for path in package.rglob('*')))
            self.assertTrue((package / 'mcp/serve.mjs').is_file())

    def test_manifests_reference_shared_launcher_and_version(self):
        expected_version = '0.3.0+native.a1b2c3'
        claude = self.read('claude', '.claude-plugin/plugin.json')
        self.assertEqual(claude['version'], expected_version)
        self.assertEqual(self.read('claude', '.mcp.json')['mcpServers']['jev-kit']['command'], '/private/runtime/serve')
        gemini = self.read('gemini', 'gemini-extension.json')
        self.assertNotIn('skills', gemini)
        self.assertEqual(gemini['mcpServers']['jev-kit']['command'], '/private/runtime/serve')
        muse = self.read('muse', '.muse-plugin/plugin.json')
        self.assertEqual(muse['schemaVersion'], 1)
        self.assertEqual(muse['compat'], {'source': 'native', 'manifestDir': '.muse-plugin'})
        self.assertEqual(muse['capabilities']['mcpServers'][0]['command'], ['/private/runtime/serve'])
        self.assertEqual(self.read('grok', '.mcp.json')['mcpServers']['jev-kit']['command'], '/private/runtime/serve')
        cursor = self.read('cursor', '.cursor-plugin/plugin.json')
        self.assertEqual(cursor['skills'], './skills/')
        self.assertEqual(self.read('cursor', 'mcp.json')['mcpServers']['jev-kit']['command'], '/private/runtime/serve')
        vscode = self.read('vscode', 'plugin.json')
        self.assertEqual(vscode['$schema'], 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json')
        self.assertNotIn('mcpServers', vscode)
        self.assertNotIn('skills', vscode)
        vscode_mcp = self.read('vscode', 'mcp.json')
        self.assertEqual(vscode_mcp['$schema'], native.AGENT_PLUGIN_MCP_SCHEMA)
        self.assertEqual(vscode_mcp['mcpServers']['jev-kit']['type'], 'stdio')

    def test_wrapper_is_valid_node_and_has_no_embedded_secrets(self):
        wrapper = self.package('muse') / 'mcp/serve.mjs'
        subprocess.run(['node', '--check', str(wrapper)], check=True, capture_output=True, text=True)
        text = wrapper.read_text()
        self.assertIn("spawn(\"/private/runtime/serve\"", text)
        self.assertIn("stdio: 'inherit'", text)
        self.assertNotIn('process.env', text)


if __name__ == '__main__':
    unittest.main()
