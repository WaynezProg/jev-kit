# Jev Kit

**English** | [繁體中文](README.zh-TW.md)

Batch judgments for coding agents and experimental Ego Lite browser automation, powered by [TypeSafe Jev](https://typesafe.ai/).

## Features

### Batch judgments

Built on `jev-use` and `jev-mcp` patterns, with local source/quote validation. Pass existing text or tool output directly; no extra LLM summary is needed.

| Tool | Capability | Example use |
|---|---|---|
| `jev_evidence` | Check up to 256 claim/source pairs per input. Verify exact quotes locally; return support, contradiction, insufficient evidence or review | Check report citations, release claims or answers against logs and documents |
| `jev_classify` | Classify up to 64 records against 2–32 custom classes, with an explicit manual-review option | Triage issues, group feedback or label tool outputs |
| `jev_extract` | Use regex to find candidates, then select exact source values for up to 8 fields | Find the current version, date or identifier among several mentions |
| `jev_decide` | Compare 2–6 supplied alternatives against priorities and up to 3 requirements; flag missing or conflicting evidence | Choose an implementation or processing route using known tradeoffs |
| `jev_rerank` | Reorder up to 30 supplied search results; select an inspection prefix while retaining all remaining IDs | Prioritize code snippets or document passages from existing search results |

These are advisory judgments. Sources and alternatives come from the caller; the tools do not search for missing evidence or execute the selected decision. [Input schemas and examples](skills/jev-kit/references/inputs.md).

### Ego Lite browser automation — experimental

Run a browser job with a goal, starting URL and expected outcome. The pinned `jev-ultrafast` policy chooses actions; Ego Lite executes them.

- Click controls, fill fields, select options and navigate pages for searches, forms and article lookup. Generated field text uses a configured text model or Claude CLI helper.
- Check target identity, visibility and page state before acting. Re-observe supported stale-target failures instead of replaying the old action.
- Verify the expected URL and/or page text independently of Jev's completion signal.
- Set allowed origins, a step limit and a time budget; stop for caller handoff on observed popups or dialogs. Record actions and outcomes in a private receipt.

```sh
~/.local/share/jev-kit/jev browser --input job.json
```

Requires separate Ego Lite/upstream setup. Time limits are checked between operations; login, transaction approvals, frames, shadow DOM and popup continuation are outside the tested scope. [Setup and job example](integrations/ego-browser/README.md).

### Agent integration and lifecycle

- **Native integration, MCP and Skill:** expose the same five judgment tools across supported hosts; the included Skill explains when to use them and how to handle uncertain results.
- **CLI batch processing:** read JSON from a file or stdin, return structured JSON, and validate inputs offline with `--validate-only`.
- **Shared installation manager:** detect hosts, select integrations, update managed hosts together, check configuration drift and remove individual integrations while preserving unrelated settings.

Installation makes tools available for the agent to call. It does not add automatic permission hooks, context compaction or model routing.

### Review and result tracking

Low-confidence, incomplete or invalid judgments remain marked for review. Reranking failures retain the original candidate order. Local quote checks, empty extraction candidates and single-candidate reranking can skip model calls.

Results include review flags, timing, resolved model and usage when a call returns them; source-based tools also retain IDs/references and hashes for comparison with the original input. CLI output can be saved as a new private receipt without overwriting an existing file.

## Install

Requires Git, Node.js 22+, Python 3.11+ and a POSIX shell. Host installation tested on macOS; Windows unsupported.

```sh
curl -fsSL https://raw.githubusercontent.com/WaynezProg/jev-kit/main/install.sh | sh
```

The installer detects configured hosts: **Codex, Claude Code, OpenCode, Muse, Grok, Gemini CLI, Cursor, VS Code and Pi**. It prefers native integration, with MCP + Skill fallback where supported.

Save your TypeSafe API key to `~/.config/jev-benchmark/typesafe-api-key` with file permission `0600`, or configure `TYPESAFE_API_KEY` / `TYPESAFE_API_KEY_FILE` in the host environment. Restart the host after installation; start a new Codex task.

```sh
# Status, update, remove
~/.local/share/jev-kit/jev status
~/.local/share/jev-kit/jev update
~/.local/share/jev-kit/jev uninstall
```

[Host configuration and verification details](docs/native-integrations.md). Cursor/VS Code editor UI discovery remains unverified; OpenCode V2 has contract tests only.

## Test results

Measured workflow results; browser timings compare Jev against **Fable 5.1 low with up to five actions per response**. Times are medians.

| Workload | Observed result |
|---|---|
| Ego Lite: 3 form tasks × 2 runs | Both passed 6/6; Jev **6.35 s** vs Fable **7.30 s** (13.0% less time) |
| Ego Lite: 2 Wikipedia tasks × 2 runs, after fix | Both passed 4/4; Jev **5.42 s** vs Fable **7.23 s** (25.1% less time) |
| Code search: 64 queries | Paired target ranked first: BM25 **46.9%**, Jev **70.3%**, Fable **93.8%**. In the separate repair test, Jev was slower than BM25: **5.25 s vs 4.42 s** |
| Model assistance | Haiku accuracy did not improve; Fable routing was faster but less accurate. No demonstrated reduction in required thinking level |

The browser sample is small and uses familiar tasks; Wikipedia initially passed only 3/4 before the fix. These results support further browser trials, not a general coding speedup or cost-saving claim.

[Browser measurements](https://github.com/WaynezProg/jev-kit/blob/37e1265b55f772bdc880662da11b834ea54d5392/benchmarks/ego-upstream/README.md) · [Search and repair measurements](https://github.com/WaynezProg/jev-kit/blob/37e1265b55f772bdc880662da11b834ea54d5392/benchmarks/rerank/results/RESULTS.md) · [Model comparisons](https://github.com/WaynezProg/jev-kit/blob/37e1265b55f772bdc880662da11b834ea54d5392/benchmarks/model-tiers/results/RESULTS.md) — links pin the tested historical revision.

Engineering checks: **47 JavaScript + 36 Python tests passed**, with [macOS/Linux CI passing](https://github.com/WaynezProg/jev-kit/actions/runs/35521891562) on 2026-09-21. These check implementation behavior, separately from the task results above.
