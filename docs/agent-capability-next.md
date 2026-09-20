# Next capability: debug evidence and executable verification

Status: proposed experiment, not shipped functionality or measured improvement.
Reviewed 2026-09-20. Optional `jev_rerank` is shipped separately in v0.3.0.

## What would strengthen the agent?

Prioritize obtaining missing evidence and checking repairs with executable tests.
Our earlier inline judgments did not establish a general coding benefit. A new
failure classifier alone would repeat that weakness. The useful output should be
an additional source, reproduction, or regression result that changes what the
agent can know or do.

| Capability | Concrete output | Jev's optional role |
|---|---|---|
| Debug evidence collector | Failing assertion, relevant implementation, callers and nearby tests with source references | Order already-resolved inspection probes when deterministic signals are ambiguous |
| Repair verifier | Reproduction fails before patch, passes after patch, and related regression commands pass | Prioritize extra checks within a budget; never decide whether a command passed |
| Repository evidence bundle | Symbol/caller relationships, tests and matching-version documentation | Rerank retrieved candidates without deleting the rest |

Reuse ripgrep, code graphs, documentation retrieval and static analysis rather
than rebuilding them inside Jev. The development machine has CodeGraph, Context7
and Semgrep configurations across some hosts. Configuration inventory does not
establish current connectivity or equivalent behavior in every host.

## Proposed bounded workflow

1. Accept the task, repository revision and actual failure receipt. Deterministically
   resolve stack paths, symbols and changed files; retain parser failures.
2. Build a small catalog of concrete probes: inspect the failing test, inspect a
   caller, fetch documentation for the installed version, or run an already
   specified reproduction. Reject unresolved paths and ambiguous commands.
3. Collect obvious evidence directly. Optionally let Jev order the remaining
   probes. Execute only within the host's existing task permissions, with a
   maximum of three probes and a fixed time/output budget.
4. Return observations, source references, hashes and missing evidence to the
   main model. Do not require it to rephrase each probe or approve a semantic
   hint at every intermediate step.
5. The main model proposes the patch. Verify it in an isolated checkout with the
   same reproduction and relevant regression checks. Capture actual exit codes,
   test outcomes, revision and patch hash; missing checks remain unverified.

Jev does not generate arbitrary shell commands, grant permissions, certify a
repair, or silently discard evidence. Tool output remains untrusted. An invalid
selection returns to deterministic ordering or the main agent; no repeated
calls until Jev agrees. Expensive test execution is distinct from read-only probes.

## Experiment before promotion

Freeze independent real repository failures, environments, hidden regression
tests and budgets before running. Separate wrong-file, cross-module, API-version
and environment failures. Include failures that require no semantic routing.

Compare the same model and thinking level across:

- **Rules-first:** deterministic probes with normal agent investigation.
- **Collect-all-bounded:** collect the same available evidence in a single bounded batch.
- **Jev-select:** identical probes and permissions, Jev chooses order/subset.

Use fresh isolated checkouts and serial timed runs, with randomized arm order.
Measure actual repair and regression success first, then total wall time, tool
time, model round trips, tokens, API failures and missing-evidence rate. Include
Jev overhead and fallbacks. Test low and high model tiers separately; repeats
are not additional independent tasks. Predeclare a held-out evaluation and require
no repair-success loss plus a meaningful time/cost benefit before making routing
the default. Otherwise keep it optional or remove it from the workflow.

## Related project worth testing separately

[jev-gateway](https://github.com/vinilana/jev-gateway) intercepts tool selection.
Its direct mode skips the main LLM only when every argument is closed-set.
Ordinary file paths and shell commands still require the LLM; Claude Code often
receives an ignorable hint. A separate advice MCP is not equivalent to this inline
gateway and may add another round trip.

The external [gateway benchmark](https://github.com/vinilana/jev-gateway-bench)
reports 120 launched sessions (119 clean) over only two chess tasks, six models
and five repeats per mode. Some debugging combinations improved, while Fable
and Opus debugging medians were 6% and 2% slower. Luna feature success fell from
5/5 without routing to 3/5 with it. These are external, limited findings, not
our measurements or evidence of universal capability gains. Test this integration
separately before adopting its provider proxy or making it a default.
