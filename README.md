# Jev Kit

Source-bound evidence checks and bounded batch judgments for coding agents, powered by [TypeSafe Jev](https://typesafe.ai/).

Jev Kit combines the batch engine from [jev-use](https://github.com/shitianfang/jev-use), task patterns from [jev-mcp](https://github.com/jkudish/jev-mcp), and local source/quote validation. It is an independent integration, not an official release of either project or TypeSafe.

| Tool | Use |
|---|---|
| `jev_evidence` | Check each claim against its own source; verify supplied quotes locally |
| `jev_classify` | Classify multiple records against a shared catalog |
| `jev_extract` | Select exact values from bounded regex candidates |
| `jev_decide` | Compare 2–6 alternatives using supplied evidence and requirements |

Use existing sources and tool outputs. You do not need an extra LLM summary before calling Jev. The host still constructs the tool input and reviews the result, so this does not establish lower total token cost, faster development, or a lower required thinking level.

## Quick start

Requires Node.js 22+. The checked-in bundles run without installing dependencies. Host setup also requires Python 3.11+ and a POSIX shell; the installer has been exercised on macOS, not Windows.

```sh
git clone https://github.com/WaynezProg/jev-kit.git
cd jev-kit
node scripts/configure-mcp.mjs
```

Provide a TypeSafe API key through `TYPESAFE_API_KEY` or `TYPESAFE_API_KEY_FILE`. Prefer a private file outside the repository, with mode `0600`. For desktop hosts that do not inherit shell environment variables, the existing fallback location is `~/.config/jev-benchmark/typesafe-api-key`. The key is not included in MCP configuration or tool arguments.

```sh
# Point to a file you have already populated securely.
export TYPESAFE_API_KEY_FILE="$HOME/.config/jev-kit/typesafe-api-key"

# Offline schema validation; no key or network needed.
node dist/cli.js evidence --input examples/evidence.json --validate-only

# Real API request; creates a NEW receipt file.
node dist/cli.js evidence --input examples/evidence.json --output /tmp/jev-evidence-result.json
```

Supplied task text is sent to TypeSafe for model judgments. Include only relevant, authorized material; never credentials. Local quote mismatches and certain empty-candidate checks do not need the API.

## One-command host management

For macOS/Linux with Git, Node.js 22+ and Python 3.11+ already installed:

```sh
curl -fsSL https://raw.githubusercontent.com/WaynezProg/jev-kit/main/install.sh | sh
```

This downloads a clean checkout and installs into `~/.local/share/jev-kit`. It detects hosts with existing configuration files, plus existing Codex/Pi directories. API credentials must be configured separately. To inspect the script first, download it and run it locally; from a clone, the equivalent command is:

```sh
./jev install
```

Select one host, several hosts, or explicitly create integrations for all nine:

```sh
./jev install --hosts claude,opencode
./jev install --hosts all
```

| Host selector | Integration |
|---|---|
| `codex` | Native plugin, installed using Codex CLI into a dedicated local marketplace |
| `claude` | MCP + Skill |
| `opencode` | MCP + Skill |
| `muse` | No-argument launcher + MCP + Skill |
| `grok` | MCP + Skill |
| `gemini` | MCP + Skill |
| `cursor` | MCP + Skill |
| `vscode` | MCP for Copilot Agent; macOS/Linux configuration paths |
| `pi` | Native extension + Skill |

All integrations expose the same four tools. This is a unified lifecycle manager, not a claim that all hosts use the same native plugin format. Codex requires a CLI version with `plugin` commands. Other host configuration formats are JSON, and Grok uses TOML. JSONC/commented JSON is currently refused safely; convert that configuration to strict JSON before using the manager. Windows is not supported by this POSIX installer.

After installation, the manager works without the original checkout:

```sh
~/.local/share/jev-kit/jev status
~/.local/share/jev-kit/jev update
~/.local/share/jev-kit/jev uninstall --hosts muse
~/.local/share/jev-kit/jev uninstall
```

`update` downloads the current GitHub `main` into a temporary directory and updates all managed hosts together. The temporary clone is discarded; it does not run npm scripts or install dependencies. `--source /absolute/checkout` selects a local release instead. A content-addressed release is staged and checked before switching the shared runtime. Codex refreshes its plugin cache through its native CLI.

`uninstall` removes only entries and Skill/extension links recorded as managed. It preserves unrelated settings, credentials, release snapshots, the manager itself, and private receipts. It does not restore an old whole-file backup over new user settings. If an owned entry/link was manually changed, it refuses and reports the conflict. Keep the runtime directory until all integrations have been removed.

`status` reports configuration drift and the installed release. It is not a live MCP connectivity test. Existing sessions may retain old tools; restart them after install/update/removal and start a new Codex task.

### Migrating the earlier installer

Existing entries are never silently claimed. If you used the previous `scripts/install-hosts.py`, migrate entries that exactly match its source directory:

```sh
./jev install --adopt-from /absolute/path/to/old/jev-kit
```

This also migrates a matching Codex Jev plugin to the dedicated managed marketplace, preserving other plugins. Any mismatch stops before editing host settings. The old source directory is retained. Use `./jev update --source "$PWD"` before adding new hosts from a newer checkout to an existing managed runtime.

Private backups and operation receipts are stored under `~/.local/share/jev-kit/receipts`; backups can contain credentials for unrelated servers. Never share that directory. Ordinary write/native-CLI failures trigger rollback; machine crashes or concurrent external configuration edits may require inspecting the private receipt and repairing the affected installation.

### Compatibility evidence

Nine-host lifecycle fixtures cover install, update, selective removal, repeat operations, legacy migration, manual drift, unrelated settings added after installation, and failure rollback. On the development Mac, Codex native CLI was additionally exercised in an isolated home through a full lifecycle. Earlier host-native diagnostics connected for Claude Code, OpenCode, Muse, Grok and Gemini; Pi's actual SDK loaded its tools and completed a real Jev call. Cursor and VS Code have config-driven protocol evidence, not editor UI acceptance. Host versions may differ.

For manual integration, `node scripts/configure-mcp.mjs` creates a local `.mcp.json`; copy its command/args into a host configuration. `node dist/cli.js serve` is stdio, not HTTP. The Pi extension is `dist/pi-extension.js`, and the shared Skill is in `skills/jev-kit/`.

Example request after installation:

> Use jev-kit to classify these issues into bug, feature, or manual review. Preserve IDs and unresolved items.

## Results and limits

- Inspect `status` and each item's `requires_review`. A tentative answer marked for review is unresolved.
- A source supporting a claim does not independently prove the claim true. Confidence is not a correctness guarantee.
- Invalid provider responses are rejected before projecting decisions. Sources have anti-injection framing, but this is not a security boundary or a guarantee against prompt injection.
- No approval gate, arbitrary command execution, automatic context pruning, or model-setting mutation is exposed.
- CLI exit `0` means processing completed, `3` means review is required, and `2` means invalid input or service/validation failure. Exit `0` does not certify task completion or claim truth.
- Receipts are new `0600` files containing IDs, source/claim hashes, results, usage, resolved model, and timing. Full sources remain in the original input; keep it for replay.
- TypeSafe requests use a fixed endpoint, a 15-second timeout, and no automatic retry. API availability and charges are external to this package.

See [input schemas and examples](skills/jev-kit/references/inputs.md) and [the agent Skill](skills/jev-kit/SKILL.md).

## Development and checks

```sh
npm ci --ignore-scripts
npm run build
npm test
python3 -m unittest discover -s test -p '*_test.py'
```

The offline suite exercises malformed responses, source/quote binding, batching, candidate extraction, decision conflicts, CLI receipts, standalone bundles, MCP contracts, Pi registration, and host configuration preservation. A separate live smoke test calls all four tools and requires your key:

```sh
node scripts/smoke.mjs /tmp/new-jev-live-smoke.json
```

Tests establish covered behavior, not semantic reliability on arbitrary tasks. No private benchmark dataset or local installation receipts are included in this repository.

## License and provenance

MIT for this integration. Vendored components retain their upstream licenses. Exact upstream commits, adaptations, and dependency notices are documented in [THIRD_PARTY.md](THIRD_PARTY.md) and `vendor/`. `jev-use` is pinned to a vendored source/build rather than relying on an unavailable npm version at the time of integration.
