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

## Coding agent setup

First inspect the changes, then apply them to existing configurations:

```sh
python3 scripts/install-hosts.py
python3 scripts/install-hosts.py --apply --receipt /tmp/jev-kit-install-receipt
```

Use a new receipt directory each time. The installer adds only `jev-kit`, preserves other settings, rejects conflicting existing entries, and saves private backups. Backups can contain other services' credentials: do not publish them. Missing host configuration files are skipped and listed in the output.

| Host | Integration | Integration evidence from the development environment |
|---|---|---|
| Codex | Plugin + MCP + Skill | Installed plugin; four-tool live API smoke test passed |
| Claude Code, OpenCode, Grok, Gemini CLI | MCP + Skill | Native MCP diagnostics connected |
| Muse Code | No-argument launcher + MCP + Skill | Fresh TUI listed four connected tools |
| Pi | Native extension + Skill | Installed SDK loaded four tools; a real Jev call passed |
| Cursor, VS Code Copilot | MCP | Config-driven handshake and local tool calls passed; editor UI loading not verified |

These observations are not a compatibility guarantee for every host version. The installer configures the seven non-Codex MCP hosts above and creates Skill/Pi extension links where supported directories exist. Codex packaging is separate: after generating `.mcp.json`, the root contains a `.codex-plugin/plugin.json` manifest ready for your local marketplace workflow. This repository is not automatically registered in a marketplace.

Restart the relevant session to load new settings; use a new Codex task. Example request:

> Use jev-kit to classify these issues into bug, feature, or manual review. Preserve IDs and unresolved items.

For manual MCP setup, copy the generated `.mcp.json` command/args into your host's MCP configuration. `node dist/cli.js serve` is a stdio server, not an HTTP endpoint. Pi loads `dist/pi-extension.js` as an extension. The Skill is in `skills/jev-kit/`.

The launcher and MCP configuration are generated for your installation directory and intentionally ignored by Git. Keep the checkout in place after installation. Moving it requires updating the corresponding host entries and symlinks; the installer refuses conflicting paths instead of silently overwriting them.

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
