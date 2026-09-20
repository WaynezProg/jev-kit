# Jev reranking screening results

Overall status: **complete**.

## Coding repair screen

Status: **complete** (64/64 assigned trials present).

| Arm | Assigned pipeline | Repairs passed | Main input total | Median total wall | Fallbacks |
| --- | ---: | ---: | ---: | ---: | ---: |
| bm25 | 16 | 16 | 40,018 | 4.417 s | 0 |
| jev | 16 | 16 | 39,651 | 5.251 s | 0 |
| llm | 16 | 16 | 39,388 | 7.637 s | 0 |
| full30 | 16 | 16 | 71,896 | 4.356 s | 0 |

Wall-time medians include every assigned pipeline attempt. API medians use only valid status-OK responses with API time above zero; zero denotes no provider API observation, not a measured zero-latency call.

| Arm | Rank wall | Rank API valid-only | Main wall | Main API valid-only | Test |
| --- | ---: | ---: | ---: | ---: | ---: |
| bm25 | <0.001 s | N/A (n=0) | 4.354 s | 2.591 s (n=16) | 0.063 s |
| jev | 0.920 s | 0.883 s (n=16) | 4.225 s | 2.451 s (n=16) | 0.067 s |
| llm | 3.243 s | 1.494 s (n=16) | 4.238 s | 2.497 s (n=16) | 0.068 s |
| full30 | <0.001 s | N/A (n=0) | 4.284 s | 2.456 s (n=16) | 0.063 s |

| Repeat | Arm | Passed | Median total wall |
| --- | --- | ---: | ---: |
| 1 | bm25 | 8 | 4.414 s |
| 1 | jev | 8 | 5.201 s |
| 1 | llm | 8 | 7.545 s |
| 1 | full30 | 8 | 4.385 s |
| 2 | bm25 | 8 | 4.417 s |
| 2 | jev | 8 | 5.321 s |
| 2 | llm | 8 | 7.742 s |
| 2 | full30 | 8 | 4.356 s |

| Jev compared with | Shared successful pairs | Jev median | Comparator median | Median of paired reductions | Faster/slower-or-equal |
| --- | ---: | ---: | ---: | ---: | ---: |
| bm25 | 16 | 5.251 s | 4.417 s | -20.43% | 0/16 |
| llm | 16 | 5.251 s | 7.637 s | 30.70% | 16/0 |
| full30 | 16 | 5.251 s | 4.356 s | -19.87% | 1/15 |

- `bm25`: main calls 16; rank attempts 0; main models claude-fable-5-1; rank models none.
- `jev`: main calls 16; rank attempts 16; main models claude-fable-5-1; rank models jev-1.13.0.
- `llm`: main calls 16; rank attempts 16; main models claude-fable-5-1; rank models claude-fable-5-1.
- `full30`: main calls 16; rank attempts 0; main models claude-fable-5-1; rank models none.

Frozen coding gate: **NOT PASS**. Its speed check uses the ratio of arm medians, distinct from the paired-reduction descriptive table.
Failing checks:
- `median_wall_20_percent_faster_than_full30_and_llm`
- `bm25_alternative_each_repeat`

This is an authored synthetic local-code screen with eight tasks and two repeats; it is not a general productivity measurement.
All baseline BM25 selected-five trials place the gold target in view.
Because the frozen local fixture has all gold targets in BM25 top five, it has zero recall headroom for reranking; repair quality and latency remain the relevant coding measures.

## Retrieval reranking screen

Status: **complete** (192/192 assigned trials present).

| Arm | Assigned pipeline | Top-1 | Recall@5 | Median rank wall | Median rank API valid-only | Fallbacks |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| bm25 | 64 | 30/64 (46.88%) | 48/64 (75.00%) | <0.001 s | N/A (n=0) | 0 |
| jev | 64 | 45/64 (70.31%) | 54/64 (84.38%) | 1.127 s | 1.068 s (n=59) | 5 |
| llm | 64 | 60/64 (93.75%) | 61/64 (95.31%) | 3.324 s | 1.554 s (n=62) | 2 |

Valid-response sensitivity only; this does not replace the assigned-pipeline counts above.

| Arm | Valid provider responses | Top-1 | Recall@5 |
| --- | ---: | --- | --- |
| bm25 | 0 | 0/0 (—) | 0/0 (—) |
| jev | 59 | 44/59 (74.58%) | 50/59 (84.75%) |
| llm | 62 | 58/62 (93.55%) | 59/62 (95.16%) |

Conditional on a gold candidate being in the supplied 30-candidate set:

| Arm | Eligible cases | Top-1 | Recall@5 |
| --- | ---: | --- | --- |
| bm25 | 61 | 30/61 (49.18%) | 48/61 (78.69%) |
| jev | 61 | 45/61 (73.77%) | 54/61 (88.52%) |
| llm | 61 | 60/61 (98.36%) | 61/61 (100.00%) |

| Jev compared with | Paired cases | Top-1 W/L/T | Recall@5 W/L/T | Top-1 difference | Recall@5 difference |
| --- | ---: | --- | --- | ---: | ---: |
| bm25 | 64 | 16/1/47 | 8/2/54 | 23.44 pp | 9.38 pp |
| llm | 64 | 0/15/49 | 0/7/57 | -23.44 pp | -10.94 pp |

Rank wall time includes native CLI startup; rank API time is reported separately above. `<synthetic>` receipt model markers are excluded from actual-model lists, while raw receipts remain unchanged. The two LLM fallbacks were native-session quota outcomes on cases 623 and 78; no new Claude requests were made for this analysis.
- `bm25`: rank attempts 0; valid provider responses 0; rank models none.
- `jev`: rank attempts 64; valid provider responses 59; rank models jev-1.13.0.
- `llm`: rank attempts 64; valid provider responses 62; rank models claude-fable-5-1.

Frozen retrieval gate: **NOT PASS**.
Failing checks:
- `all_jev_rank_calls_valid`
- `top1_within_5pp_of_llm`

Ranking results measure ordering among supplied candidates; they do not establish coding productivity.

The coding fixture contains eight independent authored synthetic tasks, and all gold targets are in BM25 top five; it cannot support a general product claim or a local recall-improvement claim. The frozen public retrieval design is a 64-case sample under a newly cleaned source condition; when complete, 61 cases had a gold candidate in the supplied 30-candidate set. Partial runs use the available conditional denominator shown above. Paired target labels show benchmark relevance, not complete task or user relevance.
