# Code search reranking and executable repair screening

This experiment tests an optional search-internal Jev reranker. It is not
registered as a production MCP tool and does not change installed host behavior.
See [design and frozen acceptance criteria](DESIGN.md).

The [completed results](results/RESULTS.md) show better paired-target retrieval
than BM25, a substantial quality gap to Fable, and no speed benefit on the eight
easy repair tasks. Both frozen gates fail. A [post-hoc rounding diagnostic](results/ROUNDING.md)
fixes validation precision without changing that adoption conclusion.

## Reproduce

Requires Node 22+, Python 3.10+, authenticated Claude Code supporting
`claude-fable-5-1` with low effort, and a TypeSafe key in the normal private
Jev Kit credential location. The scripts do not print credentials. Model calls
use the existing accounts and consume their usage. Keep raw logs outside the
repository; they can contain host details and full candidate text.

The main published campaign used `frozen-rank-v1.mjs`. To recreate that exact
condition, copy it to `rank.mjs` **in a disposable checkout** before creating a
new plan. Current `rank.mjs` includes the documented rounding fixes; fresh runs
using it are a new condition, and cannot resume the historical frozen plan.
The standalone `check_rounding.mjs` replays the archived v2 diagnostic condition.

```sh
# Offline fixture/contract validation
python3 benchmarks/rerank/fixture/verify_fixture.py
node --test test/rerank.test.js
python3 -m unittest discover -s test -p 'rerank_test.py'

# Prepare the fixed public sample; downloads public data, no model calls.
python3 benchmarks/rerank/prepare_public.py \
  --public-dir /tmp/jev-rerank/public-data \
  --private-raw-dir /tmp/jev-rerank/raw-source

# Freeze inputs and runner hashes before any measured calls.
python3 benchmarks/rerank/run.py --out /tmp/jev-rerank/coding --plan-only
python3 benchmarks/rerank/run.py --out /tmp/jev-rerank/retrieval \
  --public-input /tmp/jev-rerank/public-data/input.json --plan-only

# Paid/authenticated calls; run these serially, not in parallel.
python3 benchmarks/rerank/run.py --out /tmp/jev-rerank/coding
python3 benchmarks/rerank/run.py --out /tmp/jev-rerank/retrieval \
  --public-input /tmp/jev-rerank/public-data/input.json

python3 benchmarks/rerank/analyze.py --coding /tmp/jev-rerank/coding \
  --retrieval /tmp/jev-rerank/retrieval --out /tmp/jev-rerank/report

# The committed authored-fixture patches can be checked without API calls.
python3 benchmarks/rerank/verify_patches.py
```

Each completed trial has an immutable result file. Re-running the command
resumes missing trials and rejects changes to the frozen plan. Interrupted
trials without a result need separate review; do not silently replace them with
successful retries in a published campaign. The macOS run uses `sandbox-exec`
to deny test-subprocess network access and filesystem writes; other platforms
record the absence of that sandbox and should use a container before evaluating
untrusted generated patches.

## What is and is not measured

- Public retrieval: 64 seeded queries, 30 candidates each from 989 cleaned
  Python functions. All 64 remain in scoring, including three whose paired
  target is absent from the candidates. Gold is paired-function identity, not
  exhaustive human relevance judgment. Candidate code has no docstrings or
  comments; this differs from the external benchmark's condition.
- Repairs: eight authored synthetic bug reports, four arms, two repeats,
  deterministic hidden tests. Even after removing candidate docstrings,
  BM25 already places all eight repair targets in top5. This subset is a
  low-headroom cost/regression screen, not evidence that semantic retrieval
  cannot help harder repositories.
- Native Fable sessions have tools disabled. The host runner supplies candidates
  and applies the returned patch. This is an executable retrieval-to-repair
  pipeline, not an unrestricted interactive coding-agent or MCP-adoption test.
- Total wall time includes ranking, process startup, repair generation and
  testing. API timing is reported separately. Fable rank and repair use separate
  sessions so that all30 context cannot leak into the top5 arm.
- No effort setting changes, automatic context deletion, model routing,
  permission decisions or completion certification are tested.

[Public-data preparation and provenance](PUBLIC-DATA.md).

The [sample manifest](results/sample-manifest.json) binds public query/candidate
IDs to hashes without redistributing dataset text. [Every assigned attempt](results/runs.json)
and all [authored-fixture patches](results/patches.json) are available. Raw host
logs and full public-dataset snippets remain outside this repository.
