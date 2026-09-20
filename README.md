# Jev Kit

**English** | [繁體中文](README.zh-TW.md)

Batch judgments for coding agents and experimental Ego Lite browser automation, powered by [TypeSafe Jev](https://typesafe.ai/).

## Features

| Tool | What it does |
|---|---|
| `jev_evidence` | Check claims against their sources and verify exact quotes |
| `jev_classify` | Classify records using a shared catalog |
| `jev_extract` | Select exact values from regex candidates |
| `jev_decide` | Compare 2–6 alternatives using supplied evidence |
| `jev_rerank` | Reorder up to 30 existing search results, preserving all IDs |
| Ego Lite browser | Use Jev to choose page actions and independently check the requested outcome; experimental |

Pass existing source text directly. Uncertain results return to the agent for review.

[Tool inputs and examples](skills/jev-kit/references/inputs.md) · [Ego Lite setup](integrations/ego-browser/README.md)

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
