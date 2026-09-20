# Matched browser decision-loop screening

This experiment tests the strongest remaining integration hypothesis: Jev replaces repeated model decisions **inside a tool's execution loop**, using state already produced by the browser. The parent coding agent does not serialize source text or approve each intermediate choice.

It follows the earlier [negative evidence-assistance and cascade experiments](../model-tiers/README.md). Those experiments are retained; they measured different workflows and do not establish that a browser loop will fail or succeed.

## What is compared

All arms use one real Ego Lite page, the same visible DOM observations, the same `page.click()` executor, the same task order, and an independent exact-path verifier.

| Arm | Decisions |
|---|---|
| `keywords` | Local goal-token matching, simple plural normalization, unique matches only; no model calls |
| `llm_plan` | One Claude Fable 5.1 low call expands the goal into semantic terms; a fixed local matcher then selects visible buttons |
| `llm_step` | Claude Fable 5.1 low selects each next visible action; one persistent CLI process per task, not a new process for every click |
| `jev_step` | Jev selects each next visible action; fixed confidence threshold 0.8, uncertainty stops for escalation |

The plan arm is **one-time semantic compilation plus a fixed matcher**, not unrestricted generated JavaScript and not a full coding-agent implementation. Its limitations must not be used to claim a win over every form of code-based browser automation. A known deterministic workflow with suitable selectors/API can remain preferable to either model.

The current page includes failed-choice feedback in every arm's state. Both step models explicitly receive the last six actions. Claude additionally retains its conversation within the task; Jev receives the explicit state. This is a matched workflow comparison, not an isolation of architecture-independent model intelligence.

## Dataset and limits

[Fixture](fixture/README.md): 2 pilot tasks and 8 held-out tasks, each with four sequential stages and three buttons per stage. The held-out set has four product-filter tasks and four developer-documentation tasks. Each goal has an authored, auditable correct path. No hidden answer keys, rationales or future-stage choices enter model prompts. Only the final verifier reads the expected path.

**These are synthetic semantic wizards in a real browser, not live shopping sites or independent production tasks.** The app itself knows the target route and provides immediate feedback after a wrong choice. Ordinary websites generally do not provide that oracle. Completion and repair results therefore do not demonstrate arbitrary-site reliability. There are eight distinct held-out tasks, not 96 independent tasks.

The initial pilot exposed an environment problem: the Ego Node process did not inherit the native Claude CLI path. An explicit executable path supplied outside the repository fixed it. Plural normalization and ambiguous fixture requirements were also corrected before held-out scoring. All pilot attempts are excluded from scored results and preserved privately. No model threshold, goal, answer or matcher was tuned after held-out runs began.

## Frozen protocol

Three repeats × eight tasks × four arms = 96 serial task attempts. Arm order rotates by task and repeat. Each attempt reloads the same app; sessions and plans are never reused across attempts. The fixture hash, order and criteria are written to `plan.json` before measurements. Limits are 12 decisions per attempt, 45 seconds per native request, and a native estimated budget cap of USD 2 per task. Jev uses the shipped backend and its 15-second timeout without automatic retries.

Wall time starts after navigation and the initial observation. It includes native process startup, planning, every decision, clicks, subsequent observations, and final independent verification. It excludes the one-time fixture/server setup and process teardown. Decision, planner and browser work are reported separately. Initial loads are excluded equally; no screenshot-versus-DOM mismatch is introduced.

The practical screen requires Jev to complete all 24 attempts, at least match each comparator's completion count, reduce median time by 30% versus stepwise Claude, and by 20% versus the one-call plan/matcher. Failures and abstentions stay in the data. Report time together with completion counts: an early blocked attempt is not a fast successful task. Comparisons restricted to jointly successful attempts are descriptive only.

`BLOCKED`/low confidence means unresolved work, not an incorrect click. Unknown action IDs and malformed decisions cannot execute. Outcome error categories and wrong clicks are reported separately. The app's terminal marker is checked deterministically for all arms; Jev is not trusted to certify completion.

## Reproduction

Requires Node 22+, Python 3.11+, the Ego Lite browser/runtime, authenticated Claude Code, and the normal Jev Kit TypeSafe credential setup. Run `npm ci --ignore-scripts` in the repository first because these source-level benchmark modules use development dependencies. No host integration is installed or changed by these benchmark files.

```sh
python3 -m http.server 8768 --bind 127.0.0.1 --directory benchmarks/browser-loop/fixture
```

In another terminal, create **one** Ego TaskSpace and keep its printed ID. In `ego-browser nodejs`, import `run.mjs` by its absolute file URL and invoke:

```js
// Set this to the actual native CLI path if Ego's process PATH lacks it.
process.env.JEV_BROWSER_CLAUDE = "/absolute/path/to/claude";
const {runStudy} = await import("file:///absolute/jev-kit/benchmarks/browser-loop/run.mjs");
const task = await taskSpace("Jev matched browser decision study");
console.log({spaceId: task.spaceId});
await runStudy(task.page("p1"), {
  out: "/absolute/private/jev-browser-runs",
  baseUrl: "http://127.0.0.1:8768",
  planOnly: true,
});
// Repeat with planOnly omitted to execute the frozen plan, using the same space.
```

Use `split: "pilot", repeats: 1` and a different output folder for the two pilot cases. Never reuse pilot outcomes as held-out observations. The native event logs and complete traces remain private. The analyzer publishes only sanitized measurements and decisions. `native_duration_api_ms` and host monetary estimates are cumulative within a native session; token totals are reconstructed from each result event, whose usage is per turn. Host dollar estimates exclude Jev and are not subscription bills.

See [results](results/RESULTS.md) and [research comparison](RESEARCH.md). This is an experimental benchmark runner; it does not add an autonomous browser tool to the shipped MCP server.
