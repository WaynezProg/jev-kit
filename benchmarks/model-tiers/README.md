# Model-tier screening: two different hypotheses

Adding Jev to a lower-tier model should be tested for **better decisions**. Adding Jev before a stronger model should be tested for **less work at equal quality**. Neither benefit follows automatically from Jev's service latency.

The [48 cases and explained answers](evidence.json) were newly authored and frozen before any scored call. They cover release status, source scope, corrections, conflicting evidence, retry arithmetic, authorization conditions, version ordering, missing validation, and three Traditional Chinese records. There is one distinct source per case and 16 examples each of `supports`, `contradicts`, and `insufficient`. This is an authored screening set, not externally adjudicated production ground truth. It is separate from the earlier repository-code fixtures and weak GitHub-label corpus.

The four paths use the same Claude Code harness:

| Path | Behavior | Primary purpose |
|---|---|---|
| Haiku direct | Claude Haiku 4.5 judges all original records | Lower-tier baseline |
| Haiku assisted | Program calls Jev, then Haiku reads every original record plus advisory Jev labels, confidence and review flags | Test decision improvement |
| Fable direct | Claude Fable 5.1 judges all original records | Higher-tier baseline and upgrade alternative |
| Fable cascade | Program calls Jev, accepts only bound unflagged results, and sends unresolved rows plus a deterministic 10% audit to Fable | Test equal-quality speedup |

No model generates tool arguments or rewrites the evidence. Sources and claims are separately hash-bound. Jev's shipped review thresholds are unchanged. Failures and uncertainty go to the main model. Haiku advice is never treated as proof; Fable reviewers see original records without the earlier Jev guesses. No heuristic can establish these semantic entailment labels across all cases, so the no-Jev baseline judges all records; the separate real-issue study includes a useful keyword-rule baseline.

Haiku uses model ID `claude-haiku-4-5-20251001` with native default effort. Fable uses `claude-fable-5-1` with `--effort low`. Model tier and lower thinking effort are different variables; this study does not test lowering thinking effort within a model. Resolved IDs and native token usage are recorded. A successful tiny Haiku availability probe preceded scored runs and is excluded from measurements.

Each path runs three times, serially in fresh CLI sessions, with paired input orders and rotated arm order. Rotation is not full counterbalancing. Native cache state is observed, not reset. Wall time includes Jev and CLI startup/review, but not one-time dataset creation. Native logs, prompts and receipts remain private; fixtures, hashes, aggregate metrics and per-case decisions are public. Model calls have a 240-second timeout and a host-reported budget cap of USD 2 per call; Jev has its normal provider limits. Failures remain in the results.

Frozen gates:

- **Lower tier:** at least 5 percentage points higher aggregate accuracy than Haiku alone, with all runs complete. Compare with Fable alone as a possible simpler upgrade. Corrections and regressions are reported separately.
- **Higher tier:** no accuracy loss in aggregate or any repeat, at least 30% lower median total wall time, at most 1% observed unreviewed error, and all runs complete.

These are practical screening thresholds, not statistical significance or confidence bounds. Repeating 48 cases three times does not create 144 independent examples. A ceiling score can prevent proving a 5-point improvement; thresholds and cases are not changed after seeing that outcome. A positive signal needs an independently adjudicated production sample before becoming default behavior.

Post-run inspection identified a defensible alternative label for case 42. The original key is preserved; the results include an explicitly post-hoc exclusion analysis, which leaves the qualitative conclusion unchanged. See [measured results](results/RESULTS.md). Reproduce with authenticated Claude Code, Node 22+, Python 3.11+ and the normal TypeSafe credential setup:

```sh
python3 benchmarks/model-tiers/run.py --out /tmp/jev-tier-runs --plan-only
python3 benchmarks/model-tiers/run.py --out /tmp/jev-tier-runs
python3 benchmarks/model-tiers/analyze.py --raw /tmp/jev-tier-runs --out /tmp/jev-tier-summary
```

The dataset SHA-256 and criteria are recorded before measurements in `plan.json`; resuming rejects a changed plan. Keep raw outputs private. This runner is experimental benchmark code, not an installed automatic routing feature. Production MCP, CLI and Skill behavior are unchanged.
