# Inputs

All inputs are JSON. Unknown fields and duplicate IDs are rejected. Inputs are capped at 1 MB. No thresholds or backend URLs are supplied by tool callers. Current backend: TypeSafe, model alias jev-latest; resolved model is recorded.

## evidence

```json
{"items":[{"id":"release","claim":"Deployment completed.","source_ref":"log:42","source_text":"Build passed; deployment has not started.","quote":"deployment has not started"}]}
```

Up to 256 items. claim ≤8,000 characters, source_text ≤80,000; quote optional/null. Source identifiers and hashes stay local. Only source_text, claim and optional quote enter model state. Each item uses its own source. All original source whitespace is preserved.

## classify

```json
{"purpose":"Triage issue reports","items":[{"id":"a","text":"Save crashes the app"}],"classes":[{"id":"bug","description":"Existing functionality fails"},{"id":"manual_review","description":"Insufficient information","requires_review":true}]}
```

Up to 64 items, 8,000 characters each, and 2–32 classes. Define class precedence in descriptions when meanings overlap. Include an explicit review class when inputs may not fit. confidence ≥0.8, top probability ≥0.85 and margin ≥0.5 are necessary for a non-review result, not proof of correctness.

## extract

```json
{"document":"Previous: 1.0.0. Current stable: 2.1.0.","source_ref":"changelog","fields":[{"id":"version","description":"Current stable version","pattern":"[0-9]+\\.[0-9]+\\.[0-9]+"}]}
```

Document ≤50,000 characters; up to 8 fields. Regex matches the entire candidate value; use a pattern that excludes surrounding labels. Optional flags: i, m, s, u (global matching is automatic). Workers have a one-second timeout. Each field admits up to 20 unique candidates of ≤2,000 characters; skipped/overflow candidates force review. No-match results avoid a model call.

## decide

```json
{"decision":"Choose processing","evidence":"Local: 200/s, data stays on-device. Cloud: 400/s, uploads data.","priorities":"Keep data local; at least 100/s.","candidates":[{"id":"local","description":"Local processing"},{"id":"cloud","description":"Cloud API"}],"requirements":["Data stays on-device.","At least 100/s."]}
```

Supply 2–6 candidates, existing evidence ≤12,000 characters, explicit priorities and up to 3 atomic requirements. The runtime adds ask_user / investigate / none internally; user IDs cannot collide with these wire options. Omitted requirements mean no separate requirement checks were performed. Results do not predict user consent or approve actions.

## rerank

```json
{"query":"Find the total of a numeric list","candidates":[{"id":"sort","text":"def ordered(xs): return sorted(xs)","source_ref":"math.py:2"},{"id":"sum","text":"def total(xs): return sum(xs)","source_ref":"math.py:8"}],"top_k":1}
```

Supply 1–30 unique candidates, query ≤8,000 characters, each text ≤24,000,
optional source_ref ≤2,048. The actual JSON state (query plus candidate IDs/text)
must fit 160,000 UTF-8 bytes; no silent truncation. top_k defaults to min(5, count)
and cannot exceed the candidate count. Source references are not sent to Jev.
One candidate uses no API; otherwise one batch rates relevance from 0 to 3.
Results preserve every ID, source reference and text hash. Scores are expected
relevance levels, not probabilities of correctness. selected_ids is only a prefix;
remaining_ids must remain available. Failure returns original order with partial
status and requires_review=true; do not treat the fallback as a Jev ranking.
