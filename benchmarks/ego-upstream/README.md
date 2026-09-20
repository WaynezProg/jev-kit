# jev-ultrafast on Ego Lite

## Stronger baseline and reliability follow-up (v5/v6)

The newest comparison lets Fable generate field text in the same response as its
action plan. One arm chooses a single action; the stronger arm plans up to five
already visible actions. Both use the same guarded Ego executor and independent
outcome checks as Jev. This compares complete control strategies, including Jev's
separate Fable text calls; it is not a pure inference-latency comparison.

| Cohort | Jev | Fable single + inline text | Fable batch + inline text |
|---|---|---|---|
| v5: 3 local forms × 2 | 6/6, median **6.35 s** | 6/6, 10.74 s | 6/6, **7.30 s** |
| v5: 2 Wikipedia tasks × 2 | **3/4**, 6.01 s | 4/4, 10.00 s | 4/4, 9.64 s |
| v6: same Wikipedia tasks after fix | 4/4, median **5.42 s** | 4/4, 10.09 s | 4/4, **7.23 s** |

All medians include failed attempts. v5 public latency is **not** a quality-matched
speedup because Jev failed one task. Three other Jev public attempts each discarded
a stale decision and recovered successfully. The failed target disappeared after the guard but
before native click resolution. That failure remains in the receipts. The adapter
now recognizes only the exact owned-locator zero-match timeout, discards the old
decision, re-observes and asks the policy again. A deterministic real-Ego injection
test replaces the node between guard and dispatch: three decisions, one actual
click, independently verified. General click timeouts are still terminal errors.

Against the stronger batch baseline, the local median improvement is **13.0%**,
and the post-fix public median improvement is **25.1%**. These tiny, familiar-task
diagnostics do not establish broad reliability or higher decision accuracy. One
public follow-up pair was faster with batch Fable. Do not advertise the earlier
44–48% comparison as the advantage over an optimized LLM baseline.

Local Fable calls: Jev **6**, single **34**, batch **18**; all execute 28 actions.
Jev makes 34 separate decision requests. In v6 public: Jev uses 5 Fable text calls
plus 15 Jev decisions, compared with 13 batch Fable calls. Discarded planned actions
are recorded per step. No total API cost saving is claimed. Timers include model
session initialization, navigation, observations, typing, verification and cleanup
dispatch; Claude process shutdown is not awaited by this benchmark. All strategies
still use observed-ID plans and per-action observations, not arbitrary native Ego
JavaScript programs or the host's entire coding-agent loop.

Reproduce with `runBatchStudy` from `batch-study.mjs` using the same arguments as
the older example below. Add `publicOnly: true` for the v6-sized follow-up. Use a
new output directory and the same owned TaskSpace. The runner freezes its schedule
before calls; keep every attempt. `export-batch.py /private/ego-v5` (or `ego-v6`)
exports only allowlisted receipts. Raw native-model transcripts remain private.

Eight real-browser regressions cover batch form edits, fresh DONE checks, origin
changes, cancellation, time budgets, replaced targets, overlays and immediate
popup detection. The additional dispatch-race test covers the v5 failure mode.
Three actual CLI checks also pass: runtime initialization failure receipt, SIGINT
with zero dispatched input, and a subsequent successful job on the same page.
[CLI lifecycle receipts](results/ego-cli-lifecycle.json). Popup/dialog continuation,
frames, login and uploads remain outside scope.

[v5 plan](results/ego-v5-plan.json) · [v5 receipts](results/ego-v5.json) ·
[v5 summary](results/ego-v5-summary.json) · [v6 receipts](results/ego-v6.json) ·
[v6 summary](results/ego-v6-summary.json) · [guard checks](results/ego-v5-guards.json) ·
[dispatch-race check](results/ego-dispatch-race.json)

## Earlier one-action baseline (v1–v4)

Pinned upstream: `1231850a0bf1a0c0341fe408ef1668dbbfdfac46` (MIT), original Python
policy and DOM reader, Ego executor adapter. Upstream offline tests: 31 passed.
Prepare its Python environment with `uv sync --frozen`.

Run from `ego-browser nodejs` using one owned TaskSpace/Page for the full study:

```js
const task = await taskSpace("Jev browser comparison");
const {runStudy} = await import("/absolute/jev-kit/benchmarks/ego-upstream/run.mjs");
await runStudy(task.page("p1"), {
  upstream: "/absolute/jev-ultrafast",
  python: "/absolute/jev-ultrafast/.venv/bin/python",
  claude: "/absolute/claude",
  out: "/absolute/new-browser-results"
});
await task.finish({keep: []});
```

Paid API calls. Requires a TypeSafe key file and signed-in native Claude. The explicit
Claude path matters: Ego's embedded runtime PATH may omit user-installed binaries.
The study starts an ephemeral local HTTP fixture, uses the existing page for every
trial, and stops the server at completion. Do not run two studies on one page.

Three authored form tasks, twice each, exercise fill, native select, checkbox,
submit and result navigation. Two public Wikipedia tasks require finding/opening
the exact article. Both arms use identical observations, execution, independent
verification and native Fable 5.1 low text helper; Jev replaces action decisions.
Timing includes initial navigation, setup, typing and final verification.
The comparison is against one LLM action per round, not an optimized multi-action
LLM program. The stronger baseline is now covered in v5/v6 above.

| Final follow-up cohort | Jev | Fable low |
|---|---|---|
| Local form attempts | 6/6; median 6.61 s | 6/6; median 11.83 s |
| Public article attempts | 2/2; median 5.62 s | 2/2; median 10.81 s |
| Local main-model calls | 6 for text | 40 for choices + text |
| Local Jev decisions | 34 | 0 |

These are three unique local tasks and two public tasks, not eight independent
tasks. Final public results are post-fix diagnostics, not general-site evidence.
Actual Jev model `jev-1.13.0`. No matched Chrome comparison; no login, frames,
uploads, popup, payment or broad reliability coverage. Cost data are partial:
Claude CLI estimates and Jev token counts, not complete provider billing.

All stages remain in numeric receipts:

- `ego-v1`: invalid infrastructure comparison, missing Claude executable; later
  execution was also affected by shared runtime environment/concurrency.
- `ego-v2`: invalid comparison, previous embedded script still active after its
  CLI was interrupted. These results must not be used for model performance.
- `ego-v3`: first isolated complete run; local 6/6 each, public 0/2 each.
- `ego-v4`: rerun after readiness/rendering/stale-decision handling fixes; all pass.

Do not overwrite failed runs. Per-page leases now prevent overlapping Kit runs.
Replaced-node and covered-node real-browser guard checks both reject dispatch.

[Summary](results/summary.json) · [Final receipts](results/ego-v4.json) ·
[Previous complete run](results/ego-v3.json) · [Adapter](../../integrations/ego-browser/README.md)
