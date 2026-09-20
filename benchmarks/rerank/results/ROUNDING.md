# Post-hoc validation diagnostic

The original campaign remains unchanged in `runs.json`, `summary.json`, and
`RESULTS.md`. Its two frozen gates did not pass.

Five original Jev attempts fell back to BM25 order. The original adapter kept
only a generic provider/validation error, so their precise original causes
cannot be reconstructed. Five separate diagnostic rechecks produced four valid
responses and one `inconsistent_score`: a reported score of 0.28 versus a
probability expectation of 0.25. Binary subtraction was slightly greater than
the frozen tolerance 0.03. This reproduces a validator defect on an affected
input; it does not prove that all five original failures had that cause.

For four probabilities rounded to two decimals, expectation rounding can reach
0.005 × (1 + 2 + 3) = 0.03; the separately rounded score can add 0.005. The v2
diagnostic therefore changes tolerance to 0.035000001. It reruns **all the same
64 queries**, with no new Claude calls and no replacement of original receipts.

| Jev run | Valid responses | Assigned-pipeline Top-1 | Recall@5 |
|---|---:|---:|---:|
| Original frozen v1 | 59/64 | 45/64 (70.31%) | 54/64 (84.38%) |
| Post-hoc v2 | 64/64 | 44/64 (68.75%) | 51/64 (79.69%) |

The corrected validation removes observed fallback in this diagnostic, but
does not close the quality gap to the original Fable pipeline or establish
coding speedup. Fallback can preserve a correct BM25 result, so fewer fallbacks
do not necessarily increase retrieval scores. Other provider-output variation
also exists; this is not an isolated causal estimate for the tolerance change.

V2 uses one persistent Node process; the original campaign starts a Node process
per Jev query. V2 is also later in time. Its saved latency must not be compared
with original/Fable latency as a matched speedup or attributed to validation.
A persistent client is appropriate for a future search service, but its
end-to-end advantage still requires a matched test.

`frozen-rank-v1.mjs` and `frozen-rank-v2.mjs` match the source hashes in their
respective saved plans. The current `rank.mjs` additionally adds floating-point
slack to the probability-sum boundary (`0.02` → `0.020000001`). That final
boundary correction is covered by offline regression tests, not a third live
campaign. The two frozen snapshots preserve exactly what was measured.

The Fable pipeline's last two original rank attempts (cases 623 and 78) hit the
Claude session limit and received no model answer. Both remained in the assigned
pipeline as raw-order fallbacks; they were not retried or scored as model
responses. Valid-response sensitivity appears separately in the main report.
