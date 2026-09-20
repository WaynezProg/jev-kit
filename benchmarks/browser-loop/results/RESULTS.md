# Matched browser-loop results

**Eight authored local semantic wizards, three repeats, actual Ego Lite interactions and real API/model calls.** These are not 96 independent production tasks or an open-web reliability benchmark. All 96 attempts are retained.

| Path | Verified completed | Blocked / uncertain | Wrong clicks | Median all-attempt seconds | Median successful seconds | Main / Jev calls |
|---|---:|---:|---:|---:|---:|---:|
| keywords | 6/24 | 18 / 0 | 0 | 0.65 | 3.19 | 0 / 0 |
| llm_plan | 21/24 | 3 / 0 | 0 | 7.43 | 7.59 | 24 / 0 |
| llm_step | 24/24 | 0 / 0 | 0 | 8.40 | 8.40 | 96 / 0 |
| jev_step | 24/24 | 0 / 0 | 0 | 3.82 | 3.82 | 0 / 96 |

A blocked run that ends early is unresolved work, not a fast successful task. The rules baseline abstains on zero/tied matches; its failure count is not a count of harmful actions. The plan baseline generates semantic terms once and uses a fixed matcher; it is not an unrestricted coding agent.

| Model path | Median decision seconds | Median planning seconds | Median browser seconds | Median native API seconds |
|---|---:|---:|---:|---:|
| llm_plan | 0.01 | 4.43 | 3.18 | 3.21 |
| llm_step | 5.01 | 0.00 | 3.32 | 3.74 |
| jev_step | 1.46 | 0.00 | 2.34 | — |

Native process startup is included in wall/decision or planner time; Claude remains running between steps. Native API duration is reported separately. Component medians need not sum to the median total. Browser work also measured differently across arms (same executor, different decision cadence), so the full wall-time gain must not be attributed solely to the Jev API. Browser time includes clicks and subsequent observations; one-time fixture setup, navigation and the first observation are excluded equally. Final independent verification is included.

| Jev comparison | Jointly successful task/repeat pairs | Median paired time reduction |
|---|---:|---:|
| vs keywords | 6 | -19.36% |
| vs llm_plan | 21 | 48.59% |
| vs llm_step | 24 | 54.57% |

Frozen practical screen: **PASS**. All component checks are in [summary.json](summary.json). Positive scope is limited to these semantic wizards and this Fable low/Ego configuration. Confidence is not a universal error bound.

Exact author-known routes allow deterministic verification, but the app also provides immediate wrong-choice feedback. Real sites usually do not. The tasks omit typing, network races, uploads, logins, payments, canvas, iframes and long planning. No claims about those capabilities follow from this screen.

A suitable candidate integration is a persistent browser subtask executor, with deterministic handling where available, Jev for bounded semantic choices, and explicit escalation. The mixed fallback workflow itself was not measured here. Main-model host dollar estimates omit Jev and are not subscription bills; token counts and call counts are provided without an unsupported total monetary-saving claim.

See [protocol and reproduction](../README.md), [fixtures](../fixture/tasks.json), [all attempts](runs.json), and [primary-source research](../RESEARCH.md).
