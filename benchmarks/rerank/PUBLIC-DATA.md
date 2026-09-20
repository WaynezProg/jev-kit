# Public retrieval input preparation

`prepare_public.py` fetches the Python test split of
`mteb/CodeSearchNetRetrieval` from the Hugging Face datasets server, validates
the expected dataset revision before and after retrieval, records raw-file
hashes in a private `source-metadata.json`, then creates a fixed 64-query
reranking input. The rows endpoint itself cannot be pinned to a revision; the
saved hashes make the exact source replayable offline. It removes comments and
docstrings through a Python AST round-trip, deduplicates identical cleaned
functions, and excludes literal query leakage from the eligible corpus.

The raw source rows are written outside this repository. `input.json` is also
left untracked until its dataset-license treatment has been reviewed. The
companion `provenance.json` records counts, hashes, the exact cleaning policy,
and BM25 candidate recall on every sampled case, including cases where BM25
does not retrieve a gold item in its top 30.

Example:

```sh
python3 benchmarks/rerank/prepare_public.py \
  --public-dir /tmp/jev-rerank/public-data \
  --private-raw-dir /tmp/jev-rerank/raw-source
```

Replay saved source rows without network access:

```sh
python3 benchmarks/rerank/prepare_public.py \
  --from-raw \
  --public-dir /tmp/jev-rerank/replay-public-data \
  --private-raw-dir /tmp/jev-rerank/raw-source
```
