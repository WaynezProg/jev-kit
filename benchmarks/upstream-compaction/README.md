# Original fast-jev-compaction evaluation

Pinned upstream: `e3f262a7f4d42bd8dd32ced30d26176f7cb545b0` (MIT).
Install its local dependencies with `npm ci --ignore-scripts`, then `npm run build`.
Upstream `npm test`: 29 passed. No global plugin/hook configuration was changed.

```sh
node benchmarks/upstream-compaction/run.mjs /absolute/upstream /absolute/new-replay
node benchmarks/upstream-compaction/continue.mjs /absolute/new-replay /absolute/new-continuation
```

Both commands make paid model requests. The first reads the existing private
`TYPESAFE_API_KEY_FILE` (or Jev Kit's key-file fallback); the second needs a signed-in
Claude CLI. Use new output directories. Plans and all attempts are written before/
during execution. Six synthetic transcripts, two repeats, default library thresholds.
Only first-repeat outputs enter the native Claude fact-continuation probe.

- Required old facts retained: 12/12 runs, all 36 fact checks.
- Median serialized JSON reduction: 31.6%; range 0–56.2%.
- Median live compaction: 0.288 s; actual model `jev-1.13.0`.
- Native Fable 5.1 low continuation: full 6/6, Jev 6/6, equal-size recency 1/6.
- Including compaction, median Jev continuation pipeline 2.87 s vs full 2.66 s.

Recency preserves the same pinned messages and removes oldest complete pairs until
its serialized size is no larger than Jev's. This is a simple comparator, not native
Claude summarization. Inputs alternate meaningful diagnostic labels and opaque labels.
Jev does not see original result bodies; it may preserve opaque evidence by keeping
more output. Gold retrieval and pairing are measured separately from compression.

This tests deletion behavior and continuation recall, not coding skill, a native
`/compact` event, total billed cost, or long-session success. No default enablement.

[Summary](results/summary.json) · [All replay receipts](results/replay.json) ·
[Continuation receipts](results/continuation.json) · [Combined report](../../docs/upstream-evaluation.md)
