# Agent benchmark results — 2026-09-20

Real CLI/model calls over controlled source-evidence and issue-routing tasks. See [methodology](../README.md). These are repeated observations of 43 records, not independent production tasks.

| Phase | Profile | Workload | Baseline correct | Jev-arm correct | Baseline median s | Jev-arm median s | Paired median time ratio | Valid Jev calls |
|---|---|---|---:|---:|---:|---:|---:|---:|
| additional-hosts | grok-46-low | issue-triage | 50/50 | 50/50 | 18.70 | 47.74 | 2.58× | 2/2 |
| additional-hosts | grok-46-low | repository-evidence | 36/36 | 36/36 | 23.20 | 129.52 | 5.58× | 0/2 |
| additional-hosts | opencode-luna-low | issue-triage | 50/50 | 50/50 | 9.14 | 32.49 | 3.56× | 2/2 |
| additional-hosts | opencode-luna-low | repository-evidence | 35/36 | 36/36 | 14.02 | 139.49 | 10.01× | 0/2 |
| file-adapter | codex-luna-low | repository-evidence | 54/54 | 51/54 | 13.43 | 23.45 | 1.64× | 3/3 |
| file-adapter | pi-luna-low | repository-evidence | 51/54 | 51/54 | 16.15 | 15.94 | 1.03× | 3/3 |
| primary | claude-fable-low | issue-triage | 75/75 | 75/75 | 6.31 | 23.19 | 3.67× | 3/3 |
| primary | claude-fable-low | repository-evidence | 54/54 | 54/54 | 5.47 | 97.42 | 17.83× | 3/3 |
| primary | codex-luna-low | issue-triage | 75/75 | 75/75 | 10.64 | 43.25 | 4.11× | 3/3 |
| primary | codex-luna-low | repository-evidence | 52/54 | 52/54 | 12.76 | 146.58 | 11.85× | 0/3 |
| primary | muse-spark-low | issue-triage | 75/75 | 75/75 | 32.10 | 37.43 | 0.94× | 3/3 |
| primary | muse-spark-low | repository-evidence | 53/54 | 51/54 | 24.57 | 58.00 | 2.27× | 2/3 |
| primary | pi-luna-low | issue-triage | 75/75 | 75/75 | 12.01 | 33.99 | 2.82× | 3/3 |
| primary | pi-luna-low | repository-evidence | 52/54 | 53/54 | 15.19 | 140.45 | 9.24× | 0/3 |

A valid Jev intervention requires one completed call with preserved input records. Rejected or altered-input calls remain in the assigned-arm accuracy and timing totals. A correct final answer does not establish that Jev helped. Failed/timeout attempts are retained. Paired ratios are medians of matched-repeat ratios, not ratios of the two arm medians; these can point in different directions in a small noisy sample.

## Main-model tokens and Jev service work

| Profile | Workload | Phase | Median main input: direct → Jev | Median main output: direct → Jev | Median cached input: direct → Jev | Median Jev input/output | Median Jev service s |
|---|---|---|---:|---:|---:|---:|---:|
| grok-46-low | issue-triage | additional-hosts | 20,348 → 77,388 | 845 → 1,776 | 960 → 49,344 | 7,708 / 1,412 | 1.46 |
| grok-46-low | repository-evidence | additional-hosts | 27,100 → 104,464 | 1,199 → 8,788 | 64 → 43,904 | 13,534 / 776 | 1.36 |
| opencode-luna-low | issue-triage | additional-hosts | 4,238 → 13,332 | 356 → 1,445 | 896 → 3,584 | 7,708 / 1,412 | 1.51 |
| opencode-luna-low | repository-evidence | additional-hosts | 10,161 → 31,172 | 408 → 7,424 | 0 → 9,728 | 13,529 / 776 | 1.43 |
| codex-luna-low | repository-evidence | file-adapter | 24,272 → 76,589 | 492 → 648 | 8,960 → 62,720 | 13,534 / 776 | 1.43 |
| pi-luna-low | repository-evidence | file-adapter | 7,629 → 18,581 | 555 → 406 | 0 → 6,656 | 13,534 / 777 | 1.91 |
| claude-fable-low | issue-triage | primary | 3,773 → 17,828 | 466 → 2,316 | 0 → 8,115 | 7,708 / 1,412 | 1.51 |
| claude-fable-low | repository-evidence | primary | 13,326 → 46,728 | 362 → 11,676 | 0 → 17,669 | 13,534 / 777 | 1.40 |
| codex-luna-low | issue-triage | primary | 18,370 → 59,997 | 363 → 1,667 | 8,960 → 45,312 | 7,708 / 1,412 | 1.50 |
| codex-luna-low | repository-evidence | primary | 24,270 → 83,716 | 482 → 7,493 | 8,960 → 56,576 | 13,518 / 776 | 1.44 |
| muse-spark-low | issue-triage | primary | not reported → not reported | not reported → not reported | not reported → not reported | 7,708 / 1,412 | 1.51 |
| muse-spark-low | repository-evidence | primary | not reported → not reported | not reported → not reported | not reported → not reported | 13,534 / 775 | 1.34 |
| pi-luna-low | issue-triage | primary | 1,727 → 7,983 | 362 → 1,422 | 0 → 1,536 | 7,708 / 1,412 | 1.82 |
| pi-luna-low | repository-evidence | primary | 7,628 → 25,755 | 443 → 7,309 | 0 → 7,680 | 13,535 / 776 | 1.88 |

Input totals include cached input once. Output includes reasoning once where reported; OpenCode exposes it separately, so its output and reasoning fields are recombined. An unavailable reasoning breakdown is null. Token totals are not dollar charges; Muse main-model usage is absent from its CLI events. Host contexts differ, so use within-profile comparisons.

## Standalone Jev engine (no agent review)

| Input order | Workload | Median s | Raw correct | Accepted correct | Held for review |
|---|---|---:|---:|---:|---:|
| source-grouped | repository-evidence | 0.90 | 54/54 | 50/50 | 4 |
| source-grouped | issue-triage | 1.06 | 75/75 | 60/60 | 15 |
| agent-shuffled | repository-evidence | 0.91 | 50/54 | 36/37 | 17 |
| agent-shuffled | issue-triage | 1.14 | 75/75 | 60/60 | 15 |

Standalone engine timings exclude host reasoning/review and are not directly equivalent to finished agent answers. Accepted means not flagged for review, not independently certified correct.

## Limitations

- Small sample: three repeats in primary/file cohorts; two in additional-host cohort. No statistical significance or universal speed/cost improvement claim.
- Gold labels are authored from source semantics/routing rules; no independent external annotation.
- Real authenticated services and native CLIs were used, but tasks are controlled judgments, not full repository repair or feature delivery.
- Provider caching, network latency, model scheduling and host context contribute to wall-time differences. Phase comparisons are exploratory; fresh baselines exist within each phase.
- Fixed-file tools exist only in this benchmark adapter. The standard plugin still expects inline structured MCP inputs; its CLI already accepts input files.
- Missing model usage is not zero. No subscription invoice or Jev monetary charge was measured.
- Raw private CLI logs are excluded; public predictions, labels, usage, timings and per-call success counters are in `runs.json`.

## Incomplete or noncompliant attempts

All rows below remain in the assigned-arm totals. A changed source can be semantically harmless, but it fails exact source preservation.

| Trial | Final schema complete | Source preserved | Jev API calls | Tool error |
|---|---|---|---:|---|
| primary/codex-luna-low-repository-evidence-r1-jev | True | None | 0 | duplicate_ids |
| primary/pi-luna-low-repository-evidence-r1-jev | True | False | 3 | — |
| primary/codex-luna-low-repository-evidence-r2-jev | True | False | 3 | — |
| primary/pi-luna-low-repository-evidence-r2-jev | True | False | 3 | — |
| primary/muse-spark-low-repository-evidence-r2-jev | True | False | 3 | — |
| primary/codex-luna-low-repository-evidence-r3-baseline | False | None | 0 | — |
| primary/codex-luna-low-repository-evidence-r3-jev | True | False | 3 | — |
| primary/pi-luna-low-repository-evidence-r3-jev | True | False | 3 | — |
| additional-hosts/opencode-luna-low-repository-evidence-r1-jev | True | False | 3 | — |
| additional-hosts/grok-46-low-repository-evidence-r1-jev | True | False | 3 | — |
| additional-hosts/opencode-luna-low-repository-evidence-r2-jev | True | False | 3 | — |
| additional-hosts/grok-46-low-repository-evidence-r2-jev | True | False | 3 | — |

## Agent review of Jev labels

Only interventions with preserved input and successful Jev API calls appear here. These are descriptive comparisons, not independent model evaluations.

| Phase / profile / task | Raw Jev correct | Final agent correct | Agent fixed Jev errors | Agent introduced errors | Items flagged for review |
|---|---:|---:|---:|---:|---:|
| additional-hosts / grok-46-low / issue-triage | 50/50 | 50/50 | 0 | 0 | 10 |
| additional-hosts / opencode-luna-low / issue-triage | 50/50 | 50/50 | 0 | 0 | 10 |
| file-adapter / codex-luna-low / repository-evidence | 50/54 | 51/54 | 3 | 2 | 17 |
| file-adapter / pi-luna-low / repository-evidence | 49/54 | 51/54 | 2 | 0 | 18 |
| primary / claude-fable-low / issue-triage | 75/75 | 75/75 | 0 | 0 | 15 |
| primary / claude-fable-low / repository-evidence | 50/54 | 54/54 | 4 | 0 | 17 |
| primary / codex-luna-low / issue-triage | 75/75 | 75/75 | 0 | 0 | 15 |
| primary / muse-spark-low / issue-triage | 75/75 | 75/75 | 0 | 0 | 15 |
| primary / muse-spark-low / repository-evidence | 32/36 | 34/36 | 3 | 1 | 11 |
| primary / pi-luna-low / issue-triage | 75/75 | 75/75 | 0 | 0 | 15 |
