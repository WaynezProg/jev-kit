# Real-issue cascade screening

**These are matches to existing GitHub labels, not decision accuracy.** The catalog asks for the main subsystem; repository tags may instead describe environment or overlapping concerns. A correct abstention can therefore disagree with a reference tag. Do not compare model intelligence from these scores.

All 24 runs completed, including fallback review after one provider/validation failure among 60 Jev API calls. Successful calls resolved to jev-1.13.0; the failed call retained the requested jev-latest alias. No Jev arm met its entire frozen gate against both the direct-LLM and rules-first baselines.

| Model | Path | Reference matches | Median seconds | Median LLM items | Median main input tokens | Unreviewed disagreements |
|---|---|---:|---:|---:|---:|---:|
| claude-fable-low | jev_llm | 134/192 | 10.52 | 29 | 23164 | 0/104 |
| claude-fable-low | llm_all | 114/192 | 13.56 | 64 | 56797 | 0/0 |
| claude-fable-low | rules_jev_llm | 165/192 | 6.00 | 12 | 11700 | 4/155 |
| claude-fable-low | rules_llm | 163/192 | 5.72 | 18 | 16852 | 4/138 |
| codex-luna-low | jev_llm | 163/192 | 23.57 | 30 | 31154 | 0/96 |
| codex-luna-low | llm_all | 160/192 | 31.55 | 64 | 51309 | 0/0 |
| codex-luna-low | rules_jev_llm | 180/192 | 13.26 | 12 | 23150 | 4/154 |
| codex-luna-low | rules_llm | 179/192 | 16.41 | 18 | 26406 | 4/138 |

Three repeats of the same 64 records are not 192 independent examples. Rules-first and hybrid paths retained some disagreements without review; confidence and audit sampling are not error guarantees. The labels were not changed after inspecting results. Full gate components are in [summary.json](summary.json).
