# Jev Kit

**English** | [繁體中文](README.zh-TW.md)

Source-bound evidence checks and bounded batch judgments for coding agents, powered by [TypeSafe Jev](https://typesafe.ai/).

Jev Kit combines the batch engine from [jev-use](https://github.com/shitianfang/jev-use), task patterns from [jev-mcp](https://github.com/jkudish/jev-mcp), and local source/quote validation. It is an independent integration.

## Features

| Tool | Use |
|---|---|
| `jev_evidence` | Check each claim against its own source; verify supplied quotes locally |
| `jev_classify` | Classify records against a shared catalog |
| `jev_extract` | Select exact values from bounded regex candidates |
| `jev_decide` | Compare 2–6 alternatives using supplied evidence and requirements |
| `jev_rerank` | Optionally order up to 30 existing search candidates, retaining every ID |

Use batches of existing sources and tool outputs. Pass original text directly; an extra LLM summary is unnecessary. Keep unresolved items for the main agent to review. Jev remains optional: this package does not establish better coding accuracy, lower total cost, faster development, or a lower required thinking level.

An [experimental Ego Lite adapter](integrations/ego-browser/README.md) also runs explicit browser jobs through the pinned `jev-ultrafast` policy. It is separate from the five judgment tools.

## Install

Requires Git, Node.js 22+, Python 3.11+ and a POSIX shell. Host installation has been exercised on macOS; Windows is unsupported. The checked-in runtime bundles need no dependency installation.

```sh
curl -fsSL https://raw.githubusercontent.com/WaynezProg/jev-kit/main/install.sh | sh
```

The installer downloads a clean checkout, detects existing host configurations and installs into `~/.local/share/jev-kit`. To inspect the code first or select hosts explicitly:

```sh
git clone https://github.com/WaynezProg/jev-kit.git
cd jev-kit
./jev install --hosts claude,opencode
```

Provide your TypeSafe API key through `TYPESAFE_API_KEY` or a private file named by `TYPESAFE_API_KEY_FILE`. Keep the file outside the repository with mode `0600`. Desktop hosts that do not inherit shell variables can use the supported default file `~/.config/jev-benchmark/typesafe-api-key`. Credentials are configured separately and are never embedded in generated host packages.

```sh
# Point to a file you have already populated securely.
export TYPESAFE_API_KEY_FILE="$HOME/.config/jev-benchmark/typesafe-api-key"

# Offline validation from the checkout; no key or network needed.
node dist/cli.js evidence --input examples/evidence.json --validate-only

# Real API request; the output path must be new.
node dist/cli.js evidence --input examples/evidence.json --output /tmp/jev-evidence-result.json
```

Supplied task text goes to TypeSafe for model judgments. Include only relevant, authorized material; never credentials. Local quote mismatches and certain empty-candidate checks skip the API.

## Supported hosts

| Host selector | Managed integration |
|---|---|
| `codex` | Native plugin in a dedicated local marketplace |
| `claude` | Native plugin through Claude CLI |
| `opencode` | JavaScript native plugin + Skill |
| `muse` | Native plugin when available in the host environment; otherwise MCP + Skill |
| `grok` | Native plugin through Grok CLI |
| `gemini` | Native extension through Gemini CLI |
| `cursor` | Local native plugin package |
| `vscode` | Agent Plugin through `chat.pluginLocations` |
| `pi` | Native extension + Skill |

`--integration auto` prefers native packages and falls back to MCP + Skill only when the host CLI is missing or reports native plugins unavailable. `--integration native` requires native support; `--integration mcp` selects compatibility mode for the seven configurable hosts. Codex and Pi always use their native integrations. Uninstall an existing native integration before switching that host to MCP.

Native packaging does not enable automatic hooks or change model settings. Cursor/VS Code package and MCP checks passed, but editor UI discovery remains unverified. OpenCode V1 tool discovery was verified; V2 has contract tests only. Muse availability depends on its configured environment. See [host-specific validation and limitations](docs/native-integrations.md).

## Update and remove

After installation, the manager works without the original checkout:

```sh
~/.local/share/jev-kit/jev status
~/.local/share/jev-kit/jev update
~/.local/share/jev-kit/jev uninstall --hosts muse
~/.local/share/jev-kit/jev uninstall
```

From a checkout, use `./jev install --hosts all` to create integrations for all nine hosts. `update` downloads GitHub `main` and updates all managed hosts together; `update --source /absolute/checkout` uses local source. Update the shared runtime before adding a host from a newer checkout.

The manager checks ownership and refuses changed files, foreign entries and explicitly disabled registrations. Uninstall removes managed integrations while preserving unrelated settings, credentials, release snapshots and private receipts. Ordinary failures attempt rollback; crashes or concurrent edits can require manual repair. JSONC/commented JSON is refused; host JSON files must use strict JSON.

`status` checks configuration and inventory, not live model usage. Restart affected hosts after installation, update or removal, and start a new Codex task. Keep private backups and receipts under `~/.local/share/jev-kit/receipts` off GitHub; they can contain unrelated credentials.

## Use with an agent or CLI

Example request after installation:

> Use jev-kit to classify these issues into bug, feature, or manual review. Preserve IDs and unresolved items.

For manual MCP setup, `node scripts/configure-mcp.mjs` creates a local `.mcp.json`. Copy its command/args into your host configuration. `node dist/cli.js serve` uses stdio. The standalone Pi extension is `dist/pi-extension.js`.

All five tools also support file input through the CLI:

```sh
node dist/cli.js rerank --input examples/rerank.json --output /tmp/jev-rerank-result.json
```

Reranking accepts existing search results; it does not search. `top_k` selects an inspection prefix, with remaining IDs preserved in the receipt. Invalid responses, timeouts or missing keys retain original order and review flags. Keep original texts available for follow-up.

See [input schemas and examples](skills/jev-kit/references/inputs.md) and [the agent Skill](skills/jev-kit/SKILL.md).

## Ego Lite browser jobs

Requires a running Ego Lite, its `ego-browser` CLI, and a separately pinned upstream checkout with Python 3.12+ and `uv`. Follow the [adapter setup and job example](integrations/ego-browser/README.md), then run:

```sh
./jev browser --input job.json --validate-only
./jev browser --input job.json
```

The adapter observes page controls, asks Jev for the next action, checks the target before dispatch and independently verifies the supplied outcome assertions. Generated field text requires a configured text model or Claude CLI helper. Login, transaction approvals, frames, shadow DOM and popup continuation are outside its tested scope. Browser jobs are experimental and never enabled automatically by host installation.

## Result interpretation

- Read `status` and each item's `requires_review`; unresolved results need review.
- Source support is not independent proof of truth. Confidence and ranking do not guarantee correctness.
- The five judgment tools do not fetch sources, execute arbitrary commands, approve actions, prune context or change model settings. Source framing is not a prompt-injection security boundary.
- Judgment CLI exit `0` means processing completed, `3` means review is required, and `2` means invalid input or a service/validation failure. Exit `0` does not certify task completion.
- Judgment receipts are new `0600` files containing IDs, hashes, results, usage, resolved model and timing. Retain original inputs for replay.
- Judgment requests use a fixed TypeSafe endpoint, a 15-second timeout and no automatic retry. API availability and charges are external to this package.

## Development

```sh
npm ci --ignore-scripts
npm run build
npm test
python3 -m unittest discover -s test -p '*_test.py'
```

The offline suites cover judgment contracts, source binding, malformed responses, bundles, MCP/native registration, host lifecycle preservation and browser execution guards. An optional live smoke test calls all five tools and requires a key:

```sh
node scripts/smoke.mjs /tmp/new-jev-live-smoke.json
```

`dist/` and `vendor/` are intentionally tracked so clean installs work without npm setup. Local experiments, benchmark reports, credentials, logs, receipts and scratch outputs are excluded from Git.

## License

MIT. Vendored components retain their upstream licenses. See [THIRD_PARTY.md](THIRD_PARTY.md) for pinned commits, adaptations and attribution, and [SECURITY.md](SECURITY.md) for data handling.
