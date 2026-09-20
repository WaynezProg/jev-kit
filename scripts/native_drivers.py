"""Small, host-specific wrappers for Jev Kit's native plugin CLIs.

The manager owns files and rollback.  This module only invokes a host CLI and
normalises the small amount of state needed to decide whether that invocation
is safe.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import tomllib
from typing import Any


NAME = "jev-kit"
MARKETPLACE = "jev-kit-managed"
HOSTS = ("claude", "gemini", "muse", "grok")


class _NativeError(RuntimeError):
    def __init__(self, host: str, unavailable: bool = False):
        super().__init__(f"{host}: native command failed")
        self.unavailable = unavailable


class _VersionMismatch(RuntimeError):
    pass


class NativeDrivers:
    def __init__(self, home: Path, root: Path, executables: dict | None = None):
        self.home = Path(home).resolve()
        self.root = Path(root).resolve()
        self.executables = executables or {}

    def package_path(self, host: str) -> Path:
        self._host(host)
        if host == "claude":
            return self.root / "native" / host / "marketplace" / "plugins" / NAME
        return self.root / "native" / host / NAME

    def _host(self, host: str) -> None:
        if host not in HOSTS:
            raise ValueError("unsupported native host: " + host)

    def _executable(self, host: str) -> str:
        executable = self.executables.get(host) or shutil.which(host)
        if not executable:
            raise ValueError(f"{host}: CLI is not installed")
        # mise shims consult HOME. Resolve them before the isolated-home env is
        # applied, otherwise a test or managed install can select the wrong CLI.
        path = Path(executable)
        if "mise/shims" in str(path):
            try:
                found = subprocess.run(["mise", "which", host], text=True, capture_output=True,
                                       timeout=20, check=True).stdout.strip()
                if found:
                    return found
            except (OSError, subprocess.SubprocessError):
                pass
        return str(executable)

    def _env(self) -> dict[str, str]:
        home = str(self.home)
        return {**os.environ, "HOME": home, "XDG_CONFIG_HOME": home + "/.config",
                "XDG_DATA_HOME": home + "/.local/share", "XDG_STATE_HOME": home + "/.local/state",
                "CLAUDE_CONFIG_DIR": home + "/.claude", "GROK_HOME": home + "/.grok",
                # Gemini appends .gemini itself. Supplying home/.gemini creates
                # an accidental .gemini/.gemini tree.
                "GEMINI_CLI_HOME": home}

    def _call(self, host: str, *args: str, input: str | None = None) -> tuple[str, str]:
        # Node CLIs can lose/truncate large JSON when their stdout/stderr is a
        # pipe during process shutdown. Private file-backed capture retains the
        # complete stream without exposing other installed-extension metadata.
        with tempfile.TemporaryFile(mode="w+b") as stdout_file, tempfile.TemporaryFile(mode="w+b") as stderr_file:
            process = subprocess.Popen([self._executable(host), *args], cwd=self.home, env=self._env(), stdin=subprocess.PIPE,
                                       stdout=stdout_file, stderr=stderr_file, text=True, start_new_session=True)
            try:
                process.communicate(input, timeout=60)
            except subprocess.TimeoutExpired:
                # Host CLIs can spawn Node children. Killing the process group keeps
                # a timed-out isolated operation from leaking into later runs.
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                raise _NativeError(host)
            stdout_file.seek(0); stderr_file.seek(0)
            stdout = stdout_file.read().decode("utf-8", "replace")
            stderr = stderr_file.read().decode("utf-8", "replace")
        if process.returncode:
            raise _NativeError(host, host == "muse" and "plugins are not available in this build" in stderr)
        return stdout, stderr

    @staticmethod
    def _package_version(host: str, package: Path) -> str:
        manifest = {"claude": package / ".claude-plugin/plugin.json", "gemini": package / "gemini-extension.json",
                    "grok": package / "plugin.json", "muse": package / ".muse-plugin/plugin.json"}[host]
        try:
            return json.loads(manifest.read_text())["version"]
        except (OSError, json.JSONDecodeError, KeyError) as error:
            raise ValueError(f"{host}: managed package version is invalid") from error

    def _verify_version(self, host: str, package: Path) -> dict:
        row = self.check(host, package, True)
        if row.get("version") != self._package_version(host, package):
            raise _VersionMismatch(f"{host}: installed plugin does not match the managed package version")
        return row

    def _replace_owned_local(self, host: str, package: Path) -> None:
        """Refresh a local package when a host's update command skips it."""
        self.check(host, package, True)
        if host == "gemini":
            self._call(host, "extensions", "uninstall", NAME)
            self.validate(host, package)
            self._call(host, "extensions", "install", str(package), "--consent", "--skip-settings", input="y\n")
        elif host == "grok":
            self._call(host, "plugin", "uninstall", NAME, "--confirm")
            self.validate(host, package)
            self._call(host, "plugin", "install", str(package), "--trust")
        else:
            raise ValueError(f"{host}: local replacement is unsupported")

    @staticmethod
    def _json(host: str, stdout: str, stderr: str) -> Any:
        # Gemini 1.x writes successful --output-format json output to stderr.
        errors = []
        for raw in (stdout.strip(), stderr.strip()):
            if not raw:
                continue
            try:
                return json.loads(raw)
            except json.JSONDecodeError as error:
                errors.append(error)
        raise RuntimeError(f"{host}: native command returned invalid JSON") from (errors[-1] if errors else None)

    def _package(self, host: str, package: Path) -> Path:
        package = Path(package).resolve()
        if package != self.package_path(host).resolve():
            raise ValueError(f"{host}: package is not the managed native package")
        return package

    def probe(self, host: str) -> dict:
        self._host(host)
        try:
            if host == "claude":
                self._call(host, "plugin", "list", "--json")
            elif host == "gemini":
                self._call(host, "extensions", "list", "--output-format", "json")
            elif host == "grok":
                self._call(host, "plugin", "list", "--json")
            else:
                self._call(host, "plugins", "list", "--json")
        except _NativeError as error:
            if host == "muse" and error.unavailable:
                # Current 1.3.0-R3401.1 deliberately exits 2 for this feature.
                return {"available": False, "reason": "plugins are not available in this build"}
            raise
        return {"available": True, "reason": None}

    def _grok_disabled(self) -> bool:
        config = self.home / ".grok" / "config.toml"
        if not config.exists():
            return False
        try:
            plugins = tomllib.loads(config.read_text()).get("plugins", {})
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise RuntimeError("grok: cannot read plugin policy") from error
        if NAME in plugins.get("disabled", []):
            return True
        # An enabled allow-list is not a disable declaration. Do not let this
        # wrapper alter policy or claim that another plugin's setting disables us.
        return False

    def _claude_marketplace_owned(self, package: Path) -> bool:
        """Return whether the managed marketplace exists at its exact path.

        A same-named marketplace is not safe to adopt. This also lets rollback
        remove a marketplace that was added before Claude installed its plugin.
        """
        stdout, stderr = self._call("claude", "plugin", "marketplace", "list", "--json")
        markets = self._json("claude", stdout, stderr)
        matches = [item for item in markets if item.get("name") == MARKETPLACE]
        if not matches:
            return False
        expected = package.parent.parent.resolve()
        if len(matches) != 1 or matches[0].get("source") != "directory" or not matches[0].get("path"):
            raise ValueError("claude: marketplace name belongs to another installation")
        if Path(matches[0]["path"]).resolve() != expected:
            raise ValueError("claude: marketplace name belongs to another installation")
        return True

    def _muse_mcp_approved(self) -> None:
        stdout, stderr = self._call("muse", "plugins", "inspect", NAME, "--json")
        inspected = self._json("muse", stdout, stderr)
        runtime = inspected.get("runtime_capabilities", []) if isinstance(inspected, dict) else []
        if not any(item.get("candidate", {}).get("stable_id") == f"plugin:{NAME}:mcp_server:{NAME}"
                   and item.get("status") == "trusted_enabled" for item in runtime if isinstance(item, dict)):
            raise ValueError("muse: native MCP capability is not approved")

    def inventory(self, host: str) -> list[dict]:
        self._host(host)
        if host == "claude":
            stdout, stderr = self._call(host, "plugin", "list", "--json")
            items = self._json(host, stdout, stderr)
            managed_market = self._claude_marketplace_owned(self.package_path("claude"))
            rows = []
            for item in items:
                plugin_id = item.get("id") or item.get("pluginId")
                if plugin_id and plugin_id.endswith("@" + MARKETPLACE) and plugin_id != f"{NAME}@{MARKETPLACE}":
                    raise ValueError("claude: marketplace contains another installed plugin")
                if plugin_id and plugin_id.split("@", 1)[0] == NAME:
                    rows.append({"id": plugin_id, "name": NAME,
                                 "enabled": bool(item.get("enabled", True)),
                                 "source": str(self.package_path("claude")) if managed_market and plugin_id == f"{NAME}@{MARKETPLACE}" else None,
                                 "version": item.get("version")})
            return rows
        if host == "grok":
            stdout, stderr = self._call(host, "plugin", "list", "--json")
            items = self._json(host, stdout, stderr)
            return [{"id": item.get("repo_key") or item.get("name"), "name": item.get("name"),
                     "enabled": not self._grok_disabled(), "source": item.get("source"), "version": item.get("version")}
                    for item in items if item.get("name") == NAME and item.get("status") == "installed"]
        if host == "gemini":
            stdout, stderr = self._call(host, "extensions", "list", "--output-format", "json")
            items = self._json(host, stdout, stderr)
            if isinstance(items, dict):
                items = items.get("extensions", items.get("installed", []))
            rows = []
            for item in items:
                if item.get("name") != NAME:
                    continue
                install = Path(item.get("path") or self.home / ".gemini" / "extensions" / NAME)
                source = item.get("source")
                metadata = install / ".gemini-extension-install.json"
                if not metadata.exists():
                    raise RuntimeError("gemini: extension source metadata is missing")
                try:
                    data = json.loads(metadata.read_text())
                    if data.get("type") != "local":
                        raise RuntimeError("gemini: extension is not a local managed source")
                    source = data.get("source") or data.get("path") or source
                except (OSError, json.JSONDecodeError) as error:
                    raise RuntimeError("gemini: invalid extension metadata") from error
                rows.append({"id": item.get("id") or NAME, "name": NAME, "enabled": bool(item.get("enabled", True)),
                             "source": source, "version": item.get("version")})
            return rows
        # A successful Muse list is intentionally handled normally; unsupported
        # builds are only converted to a probe result above.
        stdout, stderr = self._call(host, "plugins", "list", "--json")
        items = self._json(host, stdout, stderr)
        if isinstance(items, dict):
            items = items.get("plugins", items.get("installed", []))
        if not isinstance(items, list):
            raise RuntimeError("muse: native command returned invalid plugin list")
        rows = []
        for item in items:
            if not isinstance(item, dict):
                raise RuntimeError("muse: native command returned invalid plugin record")
            record = item.get("record", item)
            if not isinstance(record, dict) or record.get("id") != NAME:
                continue
            source = record.get("source") or record.get("path")
            if isinstance(source, dict):
                source = source.get("path")
            rows.append({"id": record.get("id"), "name": record.get("id"),
                         "enabled": bool(record.get("enabled", False)) and bool(item.get("active", True)),
                         "source": source, "version": record.get("version")})
        return rows

    def check(self, host: str, package: Path, owned: bool) -> dict | None:
        package = self._package(host, package)
        if host == "grok" and self._grok_disabled():
            raise ValueError("grok: native plugin is disabled")
        if host == "claude":
            # Validate marketplace ownership even if plugin list is empty: a
            # name collision otherwise looks like a clean installation slot.
            self._claude_marketplace_owned(package)
        rows = self.inventory(host)
        if not rows:
            if owned:
                raise ValueError(f"{host}: managed native plugin is missing")
            return None
        for row in rows:
            source = row.get("source")
            if not source or Path(source).resolve() != package:
                raise ValueError(f"{host}: native plugin belongs to another source")
            if not row.get("enabled", False):
                raise ValueError(f"{host}: native plugin is disabled")
        if host == "muse":
            self._muse_mcp_approved()
        if not owned:
            raise ValueError(f"{host}: native plugin already exists; inspect before replacing it")
        return rows[0]

    def validate(self, host: str, package: Path):
        package = self._package(host, package)
        if host == "claude": self._call(host, "plugin", "validate", str(package))
        elif host == "gemini": self._call(host, "extensions", "validate", str(package))
        elif host == "grok": self._call(host, "plugin", "validate", str(package))
        else: self._call(host, "plugins", "validate", str(package), "--json")

    def install(self, host: str, package: Path):
        package = self._package(host, package); self.validate(host, package); self.check(host, package, False)
        if host == "claude":
            if not self._claude_marketplace_owned(package):
                self._call(host, "plugin", "marketplace", "add", str(package.parent.parent))
            self._call(host, "plugin", "install", f"{NAME}@{MARKETPLACE}", "--scope", "user")
        elif host == "gemini":
            self._call(host, "extensions", "install", str(package), "--consent", "--skip-settings", input="y\n")
        elif host == "grok": self._call(host, "plugin", "install", str(package), "--trust")
        else:
            self._call(host, "plugins", "install", str(package), "--scope", "user", "--json")
            self._call(host, "plugins", "approve", f"{NAME}:mcp_server:{NAME}", "--json")
        self._verify_version(host, package)

    def update(self, host: str, package: Path):
        package = self._package(host, package)
        self.check(host, package, True)
        if host == "claude":
            self._call(host, "plugin", "marketplace", "update", MARKETPLACE)
            self._call(host, "plugin", "update", f"{NAME}@{MARKETPLACE}", "--scope", "user")
        elif host == "gemini": self._call(host, "extensions", "update", NAME, input="y\n")
        elif host == "grok": self._call(host, "plugin", "update", NAME)
        else:
            self._call(host, "plugins", "update", NAME, "--json")
            # Muse invalidates trust when a refreshed capability definition
            # changes. The pre-update check above ensures we never override a
            # manually withdrawn approval.
            self._call(host, "plugins", "approve", f"{NAME}:mcp_server:{NAME}", "--json")
        try:
            self._verify_version(host, package)
        except _VersionMismatch:
            # Gemini and Grok can exit zero without refreshing a local source;
            # replace only after check() established exact owned/enabled source.
            if host not in ("gemini", "grok"):
                raise
            self._replace_owned_local(host, package)
            self._verify_version(host, package)

    def remove(self, host: str, package: Path):
        package = self._package(host, package)
        if host == "claude":
            market_exists = self._claude_marketplace_owned(package)
            rows = self.inventory(host)
            if not rows:
                if market_exists:
                    self._call(host, "plugin", "marketplace", "remove", MARKETPLACE)
                return
            self.check(host, package, True)
            self._call(host, "plugin", "uninstall", f"{NAME}@{MARKETPLACE}", "--scope", "user")
            self._call(host, "plugin", "marketplace", "remove", MARKETPLACE)
            return
        try:
            self.check(host, package, True)
        except ValueError as error:
            if str(error).endswith("managed native plugin is missing"):
                return
            raise
        if host == "gemini": self._call(host, "extensions", "uninstall", NAME)
        elif host == "grok": self._call(host, "plugin", "uninstall", NAME, "--confirm")
        else: self._call(host, "plugins", "remove", NAME, "--json")
