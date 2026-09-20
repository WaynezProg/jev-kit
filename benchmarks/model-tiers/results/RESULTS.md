# Model-tier screening results

48 newly authored source-bound cases, three repeats per path, actual Claude Code and Jev calls. These are 48 distinct examples, not 144 independent examples. Gold labels were authored with explanations before scored calls; they were not independently adjudicated.

| Path | Correct over repeats | Median wall seconds | Median main input tokens | Median main output tokens | Median thinking tokens | Median records sent to main model |
|---|---:|---:|---:|---:|---:|---:|
| haiku_direct | 140/144 | 73.42 | 5312 | 6384 | 5576 | 48 |
| haiku_assisted | 140/144 | 87.67 | 6742 | 7666 | 6857 | 48 |
| fable_direct | 142/144 | 9.65 | 6645 | 891 | 0 | 48 |
| fable_cascade | 139/144 | 6.35 | 3113 | 212 | 0 | 11 |

Lower-tier accuracy gain: **0.00 percentage points**. Frozen gate (at least 5 pp plus complete trials): **FAIL**.

Higher-tier median wall reduction: **34.2%**. Frozen gate (no aggregate or per-repeat quality loss, at least 30% faster, at most 1% observed unreviewed error, complete trials): **FAIL**.

| Paired comparison | Wrong → correct | Correct → wrong |
|---|---:|---:|
| haiku_direct → haiku_assisted | 1 | 1 |
| fable_direct → fable_cascade | 0 | 3 |

Main-model input tokens include cache reads and writes. Thinking tokens are a subset of reported output tokens. Wall times include the Jev process/API and main-model startup/review; one-time fixture preparation is excluded. Host monetary estimates in raw metrics omit Jev and are not subscription bills; this study does not establish total cost savings.

Haiku uses its native default effort; Fable is explicitly set to low effort. Different model families, defaults, cache states and output-generation speeds all affect wall time. Only within-model intervention comparisons estimate the benefit of the tested Jev path.

A passing screening gate would justify independent production validation, not a claim of general coding improvement, security assurance, or a guaranteed 1% error bound. No threshold was tuned from these results. See [protocol](../README.md), [gate components](summary.json), [all runs](runs.json) and [frozen plan](plan.json).
