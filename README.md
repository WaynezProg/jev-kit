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

The current measurements do not justify an always-on integration: inline calls often add substantial overhead, and program-driven evidence routing traded accuracy for speed in the model-tier screening. Keep Jev optional and validate the workload-specific benefit. See [model-tier results](benchmarks/model-tiers/results/RESULTS.md).

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

## Real coding-agent measurements (2026-09-20)

Real authenticated CLI/model calls, using the same 18 source-evidence records and 25 issue-routing records in each A/B pair. These are controlled judgments inside coding agents, **not a benchmark of end-to-end coding productivity**. All profiles request low effort; provider effort labels are not equivalent.

The full study contains **76 agent runs across six CLIs and four requested models**, plus 12 standalone Jev batches. The primary cohort has three repeats per task/arm (48 runs). Correct-label counts below aggregate repeated observations of the same records; times are per-batch medians.

| Host / requested model | Task | Correct labels: direct → Jev | Seconds: direct → Jev | Valid Jev interventions |
|---|---|---:|---:|---:|
| Claude Code / Fable 5.1 | Issue routing | 75/75 → 75/75 | 6.31 → 23.19 | 3/3 |
| Claude Code / Fable 5.1 | Code evidence | 54/54 → 54/54 | 5.47 → 97.42 | 3/3 |
| Codex / GPT-5.6 Luna | Issue routing | 75/75 → 75/75 | 10.64 → 43.25 | 3/3 |
| Codex / GPT-5.6 Luna | Code evidence | 52/54 → 52/54 | 12.76 → 146.58 | 0/3 |
| Muse / Spark 1.3 Contributor | Issue routing | 75/75 → 75/75 | 32.10 → 37.43 | 3/3 |
| Muse / Spark 1.3 Contributor | Code evidence | 53/54 → 51/54 | 24.57 → 58.00 | 2/3 |
| Pi / GPT-5.6 Luna | Issue routing | 75/75 → 75/75 | 12.01 → 33.99 | 3/3 |
| Pi / GPT-5.6 Luna | Code evidence | 52/54 → 53/54 | 15.19 → 140.45 | 0/3 |

**The standard inline MCP/extension path did not show a consistent accuracy or speed benefit.** All primary issue-routing answers were correct in both arms. Code-evidence outcomes were mixed. One Codex direct run omitted a record; missing records count as wrong.

Only 5 of 12 inline code-evidence interventions completed with preserved input: six calls changed source bytes and one was rejected for duplicate IDs. Correct final answers after failed/altered calls remain in the table; they do not establish that Jev helped. Harmless item reordering and absent/null optional quotes are normalized, but source text is compared exactly.

Jev service work usually took about 1–2 seconds per batch. Host startup, argument generation and final review accounted for the rest. Where main-model usage was reported, inline delegation increased input and output tokens on these workloads. Muse did not report main-model token usage. Cached tokens are counted once, and token totals are not dollar charges.

### Additional hosts

A later, separate cohort used two repeats per task/arm (16 runs). It is not pooled with primary timing.

| Host / requested model | Task | Correct labels: direct → Jev | Seconds: direct → Jev | Valid Jev interventions |
|---|---|---:|---:|---:|
| Grok Build / Grok 4.6 | Issue routing | 50/50 → 50/50 | 18.70 → 47.74 | 2/2 |
| Grok Build / Grok 4.6 | Code evidence | 36/36 → 36/36 | 23.20 → 129.52 | 0/2 |
| OpenCode / GPT-5.6 Luna | Issue routing | 50/50 → 50/50 | 9.14 → 32.49 | 2/2 |
| OpenCode / GPT-5.6 Luna | Code evidence | 35/36 → 36/36 | 14.02 → 139.49 | 0/2 |

The initially selected OpenCode Spark free endpoint returned HTTP 403 in its availability probe. Luna through existing OpenAI OAuth was selected before any scored additional-host run. The failed probe is [disclosed separately](benchmarks/agent-ab/results/availability.json).

### Experimental fixed-file input

A separate 12-run study used an empty-argument tool that reads the exact runner-provided input. It had fresh direct baselines, the same code-evidence records, and three repeats. All six file-tool calls preserved input.

| Host / model | Correct labels: direct → file tool | Seconds: direct → file tool |
|---|---:|---:|
| Codex / GPT-5.6 Luna | 54/54 → 51/54 | 13.43 → 23.45 |
| Pi / GPT-5.6 Luna | 51/54 → 51/54 | 16.15 → 15.94 |

The file adapter greatly reduced the long inline-call overhead observed in the earlier phase, but did not establish an accuracy gain or a general advantage over direct judgment. **This adapter is benchmark code, not a shipped MCP feature.** The existing CLI already accepts input files.

### Standalone Jev and batch composition

With already prepared input and no host/model review, Jev was fast. We also repeated the direct-engine check with the exact shuffled orders used by the agents; input content and gold labels stayed fixed. Each cell has three repeats.

| Input order / task | Median seconds | Raw correct | Unflagged correct | Held for review |
|---|---:|---:|---:|---:|
| Grouped / code evidence | 0.90 | 54/54 | 50/50 | 4 |
| Grouped / issue routing | 1.06 | 75/75 | 60/60 | 15 |
| Shuffled / code evidence | 0.91 | 50/54 | 36/37 | 17 |
| Shuffled / issue routing | 1.14 | 75/75 | 60/60 | 15 |

**One wrong code-evidence judgment was not flagged for review.** Confidence is not a correctness guarantee. Grouping/order and batch composition showed different outcomes in this small exploratory follow-up; the two order cohorts were sequential, not counterbalanced, so this is not a controlled causal estimate. Standalone timings exclude input preparation and agent review and must not be presented as completed-agent speedups.

### How to use these findings

- Prefer batches that already exist as structured data. Pass their original text through code or the CLI's `--input` path, then review unresolved rows. Avoid paying a model to rewrite long sources merely to invoke Jev.
- Use inline MCP for compact, bounded judgments when the additional check is worth a tool round trip. Routine questions that the main model already handles well can stay on the direct path.
- Test grouping related records by source or task; this sample suggests batch composition matters, but the improvement is not established generally.
- Keep Jev optional. File-based transport is a promising integration improvement; lower thinking levels, better coding quality and lower total monetary cost still need separate experiments.

Full [results and token tables](benchmarks/agent-ab/results/RESULTS.md), [per-run data](benchmarks/agent-ab/results/runs.json), [fixtures, methodology and reproduction commands](benchmarks/agent-ab/README.md) are public. Small repeat counts, authored gold labels, different host contexts and provider caching limit generalization. These tests do not establish that adding Jev lets you lower the model thinking level.

## Separate model-tier goals: quality versus speed

A follow-up uses the same Claude Code harness and 48 newly authored source-bound cases, with three repeats per path. Programmatic input avoids the expensive LLM argument-copying step. Haiku receives all original evidence plus advisory Jev judgments; Fable's cascade reviews only unresolved rows and a deterministic 10% sample of unflagged rows. Total wall time includes Jev and main-model review.

| Goal / comparison | Correct: direct → with Jev | Median total seconds: direct → with Jev | Result |
|---|---:|---:|---|
| Lower-tier quality: Haiku 4.5 | 140/144 → 140/144 | 73.42 → 87.67 | No net accuracy gain; slower |
| Higher-tier speed: Fable 5.1 low | 142/144 → 139/144 | 9.65 → 6.35 | 34.2% faster, but quality regressed |

**Neither path passed its frozen gate.** Lower-tier assistance needed at least a 5-percentage-point gain; higher-tier routing needed at least 30% lower median wall time without aggregate or per-repeat accuracy loss and at most 1% observed unreviewed error. Two of 112 automatically accepted judgments in the Fable cascade were wrong. Confidence plus a small audit did not preserve quality.

These are 48 distinct authored examples repeated three times, not 144 independent production cases. Haiku's native default used substantial thinking tokens; Fable was explicitly set to low effort. Model tier and thinking level are different variables, and this experiment does not show that thinking levels can be reduced. The high direct scores also leave little room to demonstrate a large lower-tier improvement. Post-run review identified an ambiguous guarantee claim (case 42). Excluding it leaves Haiku at 140/141 with or without Jev and Fable at 141/141 → 139/141; the conclusion is unchanged. The original key and scores are preserved, and this exclusion is explicitly post-hoc. Full [protocol](benchmarks/model-tiers/README.md), [results](benchmarks/model-tiers/results/RESULTS.md), and [per-run predictions](benchmarks/model-tiers/results/runs.json) are public.

A separate [24-run real GitHub issue study](benchmarks/cascade/README.md) compared direct LLM, rules-first, Jev-first, and rules-plus-Jev paths. No Jev path passed the combined gate against both no-Jev baselines. Existing GitHub tags proved to be weak reference labels rather than reliable semantic answers, so those agreement scores must not be presented as decision accuracy. One failed Jev API call fell back to main-model review and remains in the results.

The practical next step is an independently adjudicated production sample for an optional batch classifier or ranker, with a cheap rules baseline and explicit error tolerance. These results do not support default automatic acceptance of evidence claims, universal installation, or a general coding-productivity claim. The experimental runners do not change shipped plugin/MCP behavior.

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

Tests establish covered behavior, not semantic reliability on arbitrary tasks. Only the public benchmark fixtures and sanitized metrics are included; private agent logs and local installation receipts are excluded.

## License and provenance

MIT for this integration. Vendored components retain their upstream licenses. Exact upstream commits, adaptations, and dependency notices are documented in [THIRD_PARTY.md](THIRD_PARTY.md) and `vendor/`. `jev-use` is pinned to a vendored source/build rather than relying on an unavailable npm version at the time of integration.
