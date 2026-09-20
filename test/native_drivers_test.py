import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("native_drivers", Path(__file__).resolve().parents[1] / "scripts/native_drivers.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


FAKE = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["NATIVE_LOG"], "a") as f: f.write(json.dumps(args) + "\n")
host = os.path.basename(sys.argv[0])
source = os.environ["NATIVE_SOURCE"]
if host == "muse" and not os.getenv("MUSE_AVAILABLE"):
    print("plugins are not available in this build", file=sys.stderr); sys.exit(2)
if host == "muse" and args[:3] == ["plugins", "inspect", "jev-kit"]:
    status = "trusted_enabled" if not os.getenv("MUSE_UNTRUSTED") else "review_needed"
    print(json.dumps({"runtime_capabilities":[{"candidate":{"stable_id":"plugin:jev-kit:mcp_server:jev-kit"}, "status":status}]})); sys.exit(0)
if args[:3] == ["plugin", "marketplace", "list"]:
    print(json.dumps([] if os.getenv("CLAUDE_NO_MARKET") else [{ "name":"jev-kit-managed", "path":os.environ["CLAUDE_MARKET"], "source":"directory", "installLocation":"user" }]))
elif args[-2:] == ["list", "--json"]:
    if host == "claude":
        items = [] if os.getenv("CLAUDE_EMPTY") else [{ "id":"jev-kit@jev-kit-managed", "enabled":True, "version":"1.2" }]
        if os.getenv("CLAUDE_FOREIGN_MARKET"): items.append({"id":"other@jev-kit-managed", "enabled":True, "version":"1.2"})
        print(json.dumps(items))
    elif host == "grok": print(json.dumps([{ "status":"installed", "name":"jev-kit", "repo_key":"jev-key", "version":"1.2", "source":source }]))
    elif host == "muse": print(json.dumps({"plugins":[] if os.getenv("MUSE_EMPTY") else [{"record":{"id":"jev-kit", "enabled":True, "source":{"path":os.environ["MUSE_SOURCE"]}, "version":"1.2"}, "active":True}]}))
    else: print(json.dumps([]))
elif args[:2] == ["extensions", "list"]:
    print(json.dumps([{ "name":"jev-kit", "id":"jev-kit", "enabled":True, "version":"1.2", "path":os.environ["GEMINI_INSTALL"] }]), file=sys.stderr)
'''


class NativeDriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = self.base / "home"; self.home.mkdir()
        self.root = self.base / "release"; self.log = self.base / "calls.jsonl"
        self.bin = self.base / "bin"; self.bin.mkdir()
        self.executables = {}
        for host in native.HOSTS:
            command = self.bin / host
            command.write_text(FAKE); command.chmod(0o755)
            self.executables[host] = str(command)
        self.driver = native.NativeDrivers(self.home, self.root, self.executables)
        for host in native.HOSTS:
            package = self.driver.package_path(host)
            package.mkdir(parents=True)
            manifest = {"claude": package / ".claude-plugin/plugin.json", "gemini": package / "gemini-extension.json",
                        "grok": package / "plugin.json", "muse": package / ".muse-plugin/plugin.json"}[host]
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps({"version": "1.2"}))
        self.gemini_install = self.home / ".gemini/extensions/jev-kit"; self.gemini_install.mkdir(parents=True)
        (self.gemini_install / ".gemini-extension-install.json").write_text(json.dumps({"source": str(self.driver.package_path("gemini")), "type": "local"}))
        self.old_env = os.environ.copy()
        os.environ.update({"NATIVE_LOG": str(self.log), "NATIVE_SOURCE": str(self.driver.package_path("grok")),
                           "GEMINI_INSTALL": str(self.gemini_install),
                           "CLAUDE_MARKET": str(self.driver.package_path("claude").parent.parent),
                           "MUSE_SOURCE": str(self.driver.package_path("muse"))})

    def tearDown(self):
        os.environ.clear(); os.environ.update(self.old_env); self.temp.cleanup()

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_probe_and_inventory_normalize_host_state(self):
        self.assertEqual(self.driver.probe("muse"), {"available": False, "reason": "plugins are not available in this build"})
        self.assertTrue(self.driver.probe("claude")["available"])
        self.assertEqual(self.driver.inventory("claude")[0]["source"], str(self.driver.package_path("claude")))
        self.assertEqual(self.driver.inventory("grok")[0], {"id":"jev-key", "name":"jev-kit", "enabled":True,
                                                              "source":str(self.driver.package_path("grok")), "version":"1.2"})
        self.assertEqual(self.driver.inventory("gemini")[0]["source"], str(self.driver.package_path("gemini")))
        self.assertEqual(native.NativeDrivers._json("gemini", "warning", "[1]"), [1])
        os.environ["MUSE_AVAILABLE"] = "1"
        try:
            self.assertTrue(self.driver.probe("muse")["available"])
            self.assertEqual(self.driver.inventory("muse")[0]["source"], str(self.driver.package_path("muse")))
        finally:
            os.environ.pop("MUSE_AVAILABLE")

    def test_host_contracts_use_user_scope_and_owned_source(self):
        for host in ("claude", "gemini", "grok"):
            package = self.driver.package_path(host)
            self.driver.update(host, package)
            self.driver.remove(host, package)
        calls = self.calls()
        self.assertIn(["plugin", "marketplace", "update", "jev-kit-managed"], calls)
        self.assertIn(["plugin", "uninstall", "jev-kit", "--confirm"], calls)

    def test_muse_available_contract_uses_user_scope_and_approval(self):
        os.environ["MUSE_AVAILABLE"] = "1"
        try:
            package = self.driver.package_path("muse")
            self.driver.update("muse", package)
            self.driver.remove("muse", package)
        finally:
            os.environ.pop("MUSE_AVAILABLE")
        calls = self.calls()
        self.assertIn(["plugins", "update", "jev-kit", "--json"], calls)
        self.assertIn(["plugins", "approve", "jev-kit:mcp_server:jev-kit", "--json"], calls)
        self.assertIn(["plugins", "remove", "jev-kit", "--json"], calls)

    def test_muse_install_approves_mcp_capability_after_validation(self):
        os.environ.update({"MUSE_AVAILABLE": "1", "MUSE_EMPTY": "1"})
        original_verify = self.driver._verify_version
        self.driver._verify_version = lambda host, package: {"version": "1.2"}
        try:
            package = self.driver.package_path("muse")
            self.driver.install("muse", package)
        finally:
            self.driver._verify_version = original_verify
            os.environ.pop("MUSE_AVAILABLE")
            os.environ.pop("MUSE_EMPTY")
        calls = self.calls()
        self.assertIn(["plugins", "install", str(package), "--scope", "user", "--json"], calls)
        self.assertIn(["plugins", "approve", "jev-kit:mcp_server:jev-kit", "--json"], calls)

    def test_muse_unapproved_mcp_is_drift(self):
        os.environ.update({"MUSE_AVAILABLE": "1", "MUSE_UNTRUSTED": "1"})
        try:
            with self.assertRaisesRegex(ValueError, "not approved"):
                self.driver.check("muse", self.driver.package_path("muse"), True)
        finally:
            os.environ.pop("MUSE_AVAILABLE")
            os.environ.pop("MUSE_UNTRUSTED")

    def test_install_refuses_existing_plugin_but_uses_contract_when_absent(self):
        for host in ("claude", "gemini", "grok"):
            with self.assertRaisesRegex(ValueError, "already exists"):
                self.driver.install(host, self.driver.package_path(host))
        original_check = self.driver.check
        self.driver.check = lambda host, package, owned: {"version": "1.2"}
        os.environ["CLAUDE_NO_MARKET"] = "1"
        try:
            for host in ("claude", "gemini", "grok"):
                self.driver.install(host, self.driver.package_path(host))
        finally:
            self.driver.check = original_check
            os.environ.pop("CLAUDE_NO_MARKET")
        calls = self.calls()
        self.assertIn(["plugin", "marketplace", "add", str(self.driver.package_path("claude").parent.parent)], calls)
        self.assertIn(["plugin", "install", "jev-kit@jev-kit-managed", "--scope", "user"], calls)
        self.assertIn(["extensions", "install", str(self.driver.package_path("gemini")), "--consent", "--skip-settings"], calls)
        self.assertIn(["plugin", "install", str(self.driver.package_path("grok")), "--trust"], calls)

    def test_refuses_foreign_or_disabled_installations(self):
        with self.assertRaisesRegex(ValueError, "managed native package"):
            self.driver.validate("grok", self.base / "foreign")
        (self.home / ".grok").mkdir()
        (self.home / ".grok/config.toml").write_text("[plugins]\ndisabled = ['jev-kit']\n")
        with self.assertRaisesRegex(ValueError, "disabled"):
            self.driver.update("grok", self.driver.package_path("grok"))

    def test_check_rejects_collision_and_disabled_grok_before_install(self):
        original_inventory = self.driver.inventory
        self.driver.inventory = lambda host: [
            {"id": "jev-kit@jev-kit-managed", "name": "jev-kit", "enabled": True,
             "source": str(self.driver.package_path("claude")), "version": "1"},
            {"id": "jev-kit@other-market", "name": "jev-kit", "enabled": True,
             "source": "/foreign", "version": "1"},
        ]
        try:
            with self.assertRaisesRegex(ValueError, "another source"):
                self.driver.check("claude", self.driver.package_path("claude"), True)
        finally:
            self.driver.inventory = original_inventory
        (self.home / ".grok").mkdir(exist_ok=True)
        (self.home / ".grok/config.toml").write_text("[plugins]\ndisabled = ['jev-kit']\n")
        self.driver.inventory = lambda host: []
        try:
            with self.assertRaisesRegex(ValueError, "disabled"):
                self.driver.check("grok", self.driver.package_path("grok"), False)
        finally:
            self.driver.inventory = original_inventory

    def test_claude_partial_install_rollback_removes_only_owned_marketplace(self):
        os.environ["CLAUDE_EMPTY"] = "1"
        try:
            self.driver.remove("claude", self.driver.package_path("claude"))
        finally:
            os.environ.pop("CLAUDE_EMPTY")
        self.assertIn(["plugin", "marketplace", "remove", "jev-kit-managed"], self.calls())

    def test_claude_refuses_other_plugin_from_managed_marketplace(self):
        os.environ["CLAUDE_FOREIGN_MARKET"] = "1"
        try:
            with self.assertRaisesRegex(ValueError, "another installed plugin"):
                self.driver.remove("claude", self.driver.package_path("claude"))
        finally:
            os.environ.pop("CLAUDE_FOREIGN_MARKET")

    def test_local_update_replaces_owned_package_when_host_skips_version(self):
        for host, uninstall, install in (
            ("gemini", ["extensions", "uninstall", "jev-kit"], ["extensions", "install", str(self.driver.package_path("gemini")), "--consent", "--skip-settings"]),
            ("grok", ["plugin", "uninstall", "jev-kit", "--confirm"], ["plugin", "install", str(self.driver.package_path("grok")), "--trust"]),
        ):
            outcomes = [native._VersionMismatch("stale version"), {"version": "1.2"}]
            original_verify = self.driver._verify_version
            def verify(h, p):
                result = outcomes.pop(0)
                if isinstance(result, Exception):
                    raise result
                return result
            self.driver._verify_version = verify
            try:
                self.driver.update(host, self.driver.package_path(host))
            finally:
                self.driver._verify_version = original_verify
            calls = self.calls()
            self.assertIn(uninstall, calls)
            self.assertIn(install, calls)


if __name__ == "__main__":
    unittest.main()
