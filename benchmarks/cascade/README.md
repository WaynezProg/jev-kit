# Real-issue cascade screening

This experiment tests actual program-driven routing rather than asking an LLM to rewrite source text into MCP arguments. It is a negative result against its frozen combined gate. See [results](results/RESULTS.md), [per-run data](results/runs.json) and [frozen plan](results/plan.json).

64 real closed `openai/codex` issues were selected, 16 each bearing `auth`, `mcp`, `sandbox`, or `windows-os`. For each tag, the latest 100 updated closed issues were retrieved. Pull requests, records outside the selected 100–4000-character length range, and issues with multiple selected subsystem tags were excluded. Eligible records were ranked by SHA-256 of `jev-cascade-v1:<issue number>` and the first 16 selected. The retained title/body text totals 130,504 characters. URLs and exact text hashes are in [the manifest](corpus-manifest.json); issue bodies and native logs remain outside the repository.

**Existing GitHub tags are weak references, not independently adjudicated answers.** The taxonomy asks for the main reported subsystem while tags may indicate the environment. In particular, an issue occurring on Windows need not primarily concern Windows. `manual_review` is an allowed and sometimes appropriate model response, but has no matching reference label. Therefore label agreement cannot establish model quality or a quality improvement. This limitation motivated the separate [model-tier screening](../model-tiers/README.md).

The four paths are LLM-all, frozen keyword rules then LLM, Jev then LLM, and rules then Jev then LLM. Rules prioritize an unambiguous title match, then an unambiguous full-body match. Jev uses the shipped classification review policy without threshold tuning. Every automated path sends a deterministic 10% sample of accepted items (rounded up), plus all unresolved items, to the main model. Reviewers receive original records, without earlier predictions. Exact IDs and source hashes are checked before acceptance. Jev failures fall back to review.

Codex / GPT-5.6 Luna low and Claude Code / Claude Fable 5.1 low each ran all four paths three times, in fresh CLI sessions, serially. Input order is paired within each repeat; arm order is rotated, not fully counterbalanced. Wall time includes routing, Jev calls, CLI startup and final judgment; it excludes one-time source collection. Total input tokens include native cached tokens; cache state was observed, not reset. No native tools were used by the reviewers. One of 60 Jev API calls returned a provider/validation failure; its unresolved rows fell back to the main model. That run is retained. Successful calls resolved to Jev 1.13.0; the failed call has only the requested alias.

The frozen pass gate requires at least equal aggregate reference agreement, 30% lower median wall time, and 50% fewer main-model input tokens **against both** no-Jev baselines, plus at most 1% unreviewed disagreement and completion of every run. No Jev path passed all requirements. Keep the comparison to cheap deterministic rules; beating only an expensive full-model baseline is insufficient evidence of Jev's incremental value.

Reproduce with Node 22+, Python 3.11+, authenticated `gh`, Codex and Claude CLIs, and a TypeSafe key in the normal Jev Kit credential location. Source edits on GitHub make exact reproduction fail explicitly; retained private snapshots were used for the published measurements.

```sh
python3 benchmarks/cascade/fetch-corpus.py --out /tmp/jev-cascade-corpus.json
python3 benchmarks/cascade/run.py --corpus /tmp/jev-cascade-corpus.json --out /tmp/jev-cascade-runs --plan-only
python3 benchmarks/cascade/run.py --corpus /tmp/jev-cascade-corpus.json --out /tmp/jev-cascade-runs
python3 benchmarks/cascade/analyze.py --raw /tmp/jev-cascade-runs --out /tmp/jev-cascade-summary
```

Keep raw outputs private. Repeated runs over the same 64 issues are not independent samples. No production plugin feature, approval policy, or model configuration was changed.
