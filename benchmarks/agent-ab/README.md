# Real coding-agent Jev A/B study

This study runs actual installed coding CLIs and authenticated model services. It measures bounded judgments inside coding agents, **not end-to-end feature development, autonomous coding quality, or production issue resolution**.

Read the [measured results](results/RESULTS.md), [per-run records](results/runs.json), and [exact CLI/environment versions](results/environment.json). The source-evidence fixture uses Jev Kit revision `4558554f8cc4737d97453bce31e3e8ead8823579`; source excerpts and this integration are MIT licensed.

## Frozen primary design

- Hosts: Codex CLI, Claude Code, Pi, Muse Code.
- Requested models: `gpt-5.6-luna` through Codex and Pi; `claude-fable-5-1` through Claude Code; `muse-spark-1.3-contributor` through Muse.
- All profiles request low reasoning/effort. Effort labels are provider-specific; this is not a thinking-level equivalence claim.
- Workloads: 18 source-to-claim checks using actual MIT-licensed Jev Kit code, and 25 authored realistic issue reports with five balanced routing classes. The reports are synthetic, not sampled customer tickets.
- The evidence workload has six distinct code excerpts with three claims each. Its current MCP contract repeats source text per claim; this exercises the copying overhead of that input shape. It does not represent every coding workload.
- Two arms: direct model judgment, versus one explicit native MCP/extension Jev call followed by model review. Both see the same complete source material. The Jev arm must construct the structured tool arguments itself.
- Three repeats per profile/workload/arm: 48 primary runs. Inputs are shuffled identically within a pair. Arm order is counterbalanced, all trials execute sequentially, and each run starts a new session. Timeout is 180 seconds. No retries to improve scores.
- The plan and fixture SHA-256 hashes are written before execution. Pilot runs are excluded. Gold labels are authored from source semantics and explicit routing rules, not taken from model majority votes. They have not received independent external annotation.

All agents are asked not to browse, execute shell commands, read other files, or delegate. The raw sources are included in the prompt; gold labels are not. The benchmark wrappers preserve Jev Kit's schemas and core behavior, adding only private request/receipt capture. They are not model API simulations.

Host context is intentionally not assumed equivalent: Codex can still discover installed skills despite ignoring its main user configuration; Claude uses a controlled system prompt and no built-in tools; Pi disables skill/context/extension discovery except the selected benchmark extension; Muse uses isolated MCP configuration but still loads its own skill catalog. Therefore, compare **within a host/model pair**, not absolute token counts or latency as a ranking of harnesses.

## Secondary studies

After a primary run exposed slow/error-prone copying of repeated source text into tool arguments, a separate fixed-file adapter study was frozen. It uses Codex and Pi, the same 18 source checks, three fresh counterbalanced baseline/file pairs each (12 runs). The model still sees the same complete sources, but `jev_evidence_file({})` loads the exact runner-supplied input without retyping it.

**The file adapter is experimental benchmark code, not a shipped Jev Kit MCP tool.** It demonstrates an integration design, not the performance of the standard inline API. The secondary study is exploratory and was motivated by the primary observation; its fresh baselines are scored separately.

A standalone engine comparison uses the original, unshuffled fixture order and makes three calls per workload through the same core, with no coding host and no model review. Its speed is not a replacement for an end-to-end agent result. Report both raw relation accuracy and the number of items held for review. After the grouped-order results differed from the agent runs, a six-batch exploratory follow-up used the exact three agent permutations in `agent-orders.json`. Both order modes are retained (12 standalone batches). These later sequential cohorts were not counterbalanced, so order effects are descriptive, not a causal estimate. One shuffled-order wrong answer was not flagged for review.

A separately frozen additional-host cohort uses OpenCode with `openai/gpt-5.6-luna` and Grok Build with `grok-4.6`, both requesting low effort. Each has two repeats per workload/arm (16 attempts). Availability/tool probes precede this cohort and are excluded from scored runs. Do not pool this later phase with primary timing. The initially selected OpenCode `opencode/muse-spark-1.3-contributor-free` endpoint returned HTTP 403 in its availability probe. Before any scored additional-host run, the plan was revised to use existing OpenAI OAuth access with Luna; the failed endpoint is disclosed in `results/availability.json`, not silently counted as a model result.

OpenCode runs without external plugins and disables configured MCP servers in a process-local override, enabling only the benchmark server in its Jev arm. This follows its [configuration](https://opencode.ai/docs/config/) and [permission](https://opencode.ai/docs/permissions/) interfaces. Grok uses the already installed `jev-kit` MCP entry, native permission rules, and its existing host context, including skill reads and lazy `search_tool` / `use_tool` dispatch; install Jev Kit for Grok before reproducing that cohort. No global host configuration is rewritten by the runner.

## Measurements and publication rules

- Wall time includes CLI startup, tool selection, argument generation, Jev calls, and final model response. It excludes fixture creation and evaluation.
- Score every scheduled attempt, retaining timeouts, tool validation failures, and noncompliant runs. Report whether Jev was actually called with unchanged input; a correct final answer after a rejected tool call is not evidence that Jev helped.
- Repeated answers to the same 18/25 records are repeated observations, not new independent test cases. Per-cell `n=3` is small. Report medians, paired differences, completion, and failures without claiming statistical significance or population-wide improvement.
- Main-model input includes cache reads/writes once. Codex input already includes cached input. Claude input is uncached + cache read + cache creation. Pi input is uncached + cache read + cache write. Reasoning tokens are reported separately and are not added a second time to output totals.
- OpenCode input is uncached + cache read + cache write. Its event output excludes reasoning, so total output is reconstructed as output + reasoning, once, following the [v1.18.31 usage implementation](https://github.com/anomalyco/opencode/blob/v1.18.31/packages/opencode/src/session/session.ts#L321). Counts are summed across `step_finish` events, not taken only from the last step.
- Muse's headless event stream does not expose main-model token usage in these runs. Missing usage is null, never zero. Do not invent token savings or a combined price.
- Keep Jev API input/output tokens and elapsed time separate from main-model usage. CLI-reported dollar estimates are not subscription invoices or verified marginal cost.
- Capture review flags, agent interventions, native tool failures, source-input preservation, and resolved Jev model IDs.
- Raw host logs can contain private machine paths, session IDs, and reasoning/signature fields. Keep them outside this repository. Publish only an allowlisted numeric/label summary plus public fixtures and scripts.

## Reproduce

Install Node.js 22+, Python 3.11+, the relevant CLIs, and authenticate each CLI normally. Provide your own TypeSafe key through the documented environment/file mechanism. Model access and host versions may differ. No keys are included. Running the study consumes model/API usage.

```sh
npm ci --ignore-scripts
python3 benchmarks/agent-ab/run.py --out /absolute/private/main --plan-only
python3 benchmarks/agent-ab/run.py --out /absolute/private/main
# Run AFTER the primary study to avoid parallel latency interference.
python3 benchmarks/agent-ab/file-study.py --out /absolute/private/file-study --plan-only
python3 benchmarks/agent-ab/file-study.py --out /absolute/private/file-study
python3 benchmarks/agent-ab/extra-hosts.py --out /absolute/private/additional-probe --probe
python3 benchmarks/agent-ab/extra-hosts.py --out /absolute/private/additional --plan-only
python3 benchmarks/agent-ab/extra-hosts.py --out /absolute/private/additional
node benchmarks/agent-ab/direct.mjs /absolute/private/direct
node benchmarks/agent-ab/direct.mjs /absolute/private/direct-shuffled --agent-order
python3 benchmarks/agent-ab/analyze.py --private /absolute/private --out /absolute/public-summary
```

Use a new output directory. Completed primary trials resume from saved results; the frozen plan must still match. Do not regenerate fixtures between arms. `make-fixtures.py` is for creating a new dataset/version; the checked-in JSON is the frozen dataset for this study.
