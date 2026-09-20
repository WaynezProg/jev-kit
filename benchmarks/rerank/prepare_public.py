#!/usr/bin/env python3
"""Build a fixed, source-cleaned CodeSearchNet retrieval input for reranking.

The downloaded dataset rows are deliberately kept outside the repository.  This
script writes only derived benchmark input to ``--public-dir`` so it can be
reviewed for licensing before being committed.
"""
import argparse
import ast
import collections
import hashlib
import json
import math
import random
import re
import textwrap
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DATASET = "mteb/CodeSearchNetRetrieval"
SEED = 20260920
PAGE_SIZE = 100
EXPECTED_REVISION = "68e8f0731a656fa4bd5b7c81936d95ad48a39bfe"
RAW_NAMES = ("corpus", "queries", "qrels")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def request_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": "jev-kit-benchmark/1"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
            retry_after = error.headers.get("Retry-After")
            delay = min(int(retry_after), 15) if retry_after and retry_after.isdigit() else 2**attempt
            time.sleep(delay)
    raise AssertionError("unreachable")


def rows(config: str) -> list[dict]:
    """Fetch every row, following the server's advertised pagination."""
    result: list[dict] = []
    offset = 0
    total = None
    while total is None or offset < total:
        params = urllib.parse.urlencode(
            {"dataset": DATASET, "config": config, "split": "test", "offset": offset, "length": PAGE_SIZE}
        )
        response = request_json("https://datasets-server.huggingface.co/rows?" + params)
        page = response["rows"]
        total = response["num_rows_total"]
        if not page:
            raise RuntimeError(f"{config}: empty page at offset {offset} before {total} rows")
        result.extend(item["row"] for item in page)
        offset += len(page)
    if len(result) != total:
        raise RuntimeError(f"{config}: fetched {len(result)} rows, expected {total}")
    return result


def dataset_metadata() -> dict:
    return request_json("https://huggingface.co/api/datasets/" + DATASET)


def validate_revision(metadata: dict, expected: str, when: str) -> str:
    observed = metadata.get("sha")
    if observed != expected:
        raise RuntimeError(f"dataset revision drift {when}: expected {expected}, observed {observed}")
    return observed


def raw_paths(directory: Path) -> dict[str, Path]:
    return {name: directory / f"python-{name}.json" for name in RAW_NAMES}


def raw_hashes(directory: Path) -> dict[str, str]:
    paths = raw_paths(directory)
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise RuntimeError("saved raw input missing: " + ", ".join(missing))
    return {path.name: sha256(path) for path in paths.values()}


def load_raw(directory: Path) -> dict[str, list[dict]]:
    return {name: json.loads(path.read_text()) for name, path in raw_paths(directory).items()}


def source_manifest(directory: Path, expected: str, mode: str, metadata_before: dict | None, metadata_after: dict | None) -> dict:
    """Store replay information separately from source rows and public provenance."""
    hashes = raw_hashes(directory)
    prior = directory / "source-metadata.json"
    if mode.endswith("replay") and prior.exists():
        saved = json.loads(prior.read_text())
        if saved.get("raw_sha256") != hashes:
            raise RuntimeError("saved raw hashes do not match source-metadata.json")
        if saved.get("expected_revision") != expected:
            raise RuntimeError("saved expected revision does not match this replay")
        return saved
    manifest = {
        "dataset": DATASET,
        "expected_revision": expected,
        "mode": mode,
        "observed_revision_before": metadata_before.get("sha") if metadata_before else None,
        "observed_revision_after": metadata_after.get("sha") if metadata_after else None,
        "raw_sha256": hashes,
        "rows_endpoint": "https://datasets-server.huggingface.co/rows",
        "note": "Rows API requests do not include a revision parameter. The revision was validated before and after live retrieval; raw hashes provide exact offline replay verification.",
    }
    write_json(prior, manifest)
    return manifest


class RemoveDocstrings(ast.NodeTransformer):
    @staticmethod
    def remove(body: list[ast.stmt]) -> list[ast.stmt]:
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            return body[1:]
        return body

    def visit_Module(self, node):
        self.generic_visit(node)
        node.body = self.remove(node.body)
        return node

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        node.body = self.remove(node.body)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        node.body = self.remove(node.body)
        return node


def clean_python(source: str) -> str:
    """Drop comments via AST round-trip and leading docstrings from every scope."""
    tree = ast.parse(textwrap.dedent(source))
    tree = RemoveDocstrings().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree).strip()


def tokens(text: str) -> list[str]:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return re.findall(r"[a-z0-9]+", text.lower())


def bm25(query: str, corpus: list[dict], docs: list[collections.Counter], lengths: list[int], average: float, frequencies: collections.Counter, n: int = 30) -> list[dict]:
    query_terms = set(tokens(query))
    scored = []
    for index, (candidate, document) in enumerate(zip(corpus, docs)):
        score = 0.0
        for term in query_terms:
            frequency = document.get(term, 0)
            if frequency:
                score += math.log(1 + (len(docs) - frequencies[term] + 0.5) / (frequencies[term] + 0.5)) * frequency * 2.5 / (frequency + 1.5 * (0.25 + 0.75 * lengths[index] / average))
        scored.append((score, index, candidate))
    return [candidate for _, _, candidate in sorted(scored, key=lambda item: (-item[0], item[1]))[:n]]


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-dir", type=Path, required=True)
    parser.add_argument("--private-raw-dir", type=Path, required=True)
    parser.add_argument("--from-raw", action="store_true", help="rebuild only from saved raw JSON; make no network requests")
    parser.add_argument("--expected-revision", default=EXPECTED_REVISION)
    args = parser.parse_args()
    public, private = args.public_dir, args.private_raw_dir
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)

    if args.from_raw:
        raw = load_raw(private)
        # Existing raw captures from before this manifest was introduced can be
        # replayed, but are marked as recovered rather than falsely claiming a
        # before/after network observation.
        manifest = source_manifest(private, args.expected_revision, "recovered-replay", None, None)
        observed_revision = manifest.get("observed_revision_after") or manifest.get("expected_revision")
        if observed_revision != args.expected_revision:
            raise RuntimeError("saved raw manifest revision does not match expected revision")
    else:
        before = dataset_metadata()
        validate_revision(before, args.expected_revision, "before download")
        raw = {name: rows("python-" + name) for name in RAW_NAMES}
        for name, value in raw.items():
            write_json(private / f"python-{name}.json", value)
        after = dataset_metadata()
        validate_revision(after, args.expected_revision, "after download")
        manifest = source_manifest(private, args.expected_revision, "live", before, after)
        observed_revision = after["sha"]

    cleaned_by_original: dict[str, str] = {}
    canonical_by_cleaned: dict[str, str] = {}
    clean_candidates: list[dict] = []
    unparseable: list[str] = []
    duplicates = 0
    for row in raw["corpus"]:
        try:
            cleaned = clean_python(row["text"])
        except (SyntaxError, ValueError, TypeError):
            unparseable.append(row["id"])
            continue
        if not cleaned:
            unparseable.append(row["id"])
            continue
        if cleaned in canonical_by_cleaned:
            cleaned_by_original[row["id"]] = canonical_by_cleaned[cleaned]
            duplicates += 1
            continue
        canonical_by_cleaned[cleaned] = row["id"]
        cleaned_by_original[row["id"]] = row["id"]
        clean_candidates.append({"id": row["id"], "text": cleaned})

    query_by_id = {row["id"]: row["text"] for row in raw["queries"]}
    gold_by_query: dict[str, set[str]] = collections.defaultdict(set)
    for row in raw["qrels"]:
        if row["score"] > 0 and row["corpus-id"] in cleaned_by_original:
            gold_by_query[row["query-id"]].add(cleaned_by_original[row["corpus-id"]])
    qrels_lost_to_parse = sorted({row["query-id"] for row in raw["qrels"] if row["score"] > 0 and row["corpus-id"] not in cleaned_by_original})

    # Detect literal query leakage only after stripping comments/docstrings.
    leaks: dict[str, list[str]] = collections.defaultdict(list)
    candidate_leaks: set[str] = set()
    for query_id, query in query_by_id.items():
        literal = normalized(query)
        if not literal:
            continue
        for candidate in clean_candidates:
            if literal in normalized(candidate["text"]):
                leaks[query_id].append(candidate["id"])
                candidate_leaks.add(candidate["id"])
    eligible_corpus = [candidate for candidate in clean_candidates if candidate["id"] not in candidate_leaks]
    eligible_ids = {candidate["id"] for candidate in eligible_corpus}
    eligible_queries = [
        query_id for query_id in sorted(query_by_id, key=lambda value: int(value) if value.isdigit() else value)
        if query_id not in qrels_lost_to_parse and gold_by_query[query_id] & eligible_ids
    ]
    if len(eligible_queries) < 64:
        raise RuntimeError(f"only {len(eligible_queries)} eligible queries after cleaning")
    sampled_ids = random.Random(SEED).sample(eligible_queries, 64)

    documents = [collections.Counter(tokens(candidate["text"])) for candidate in eligible_corpus]
    lengths = [sum(document.values()) for document in documents]
    average = sum(lengths) / len(lengths)
    frequencies = collections.Counter(term for document in documents for term in document)
    cases = []
    recall_at_30 = 0
    for query_id in sampled_ids:
        candidates = bm25(query_by_id[query_id], eligible_corpus, documents, lengths, average, frequencies)
        gold = sorted(gold_by_query[query_id] & eligible_ids)
        hit = bool(set(gold) & {candidate["id"] for candidate in candidates})
        recall_at_30 += hit
        cases.append({"id": query_id, "query": query_by_id[query_id], "candidates": candidates, "gold_ids": gold})
    write_json(public / "input.json", {"dataset": DATASET, "seed": SEED, "cases": cases})

    provenance = {
        "dataset": DATASET,
        "revision": observed_revision,
        "expected_revision": args.expected_revision,
        "source_verification": {"raw_manifest_sha256": sha256(private / "source-metadata.json"), "mode": manifest["mode"], "pinning": "revision observed before and after download, not a rows-endpoint revision pin"},
        "source": "https://datasets-server.huggingface.co/rows",
        "license": "mit",
        "seed": SEED,
        "raw_rows": {name: len(value) for name, value in raw.items()},
        "raw_sha256": manifest["raw_sha256"],
        "cleaning": {"method": "ast.parse(textwrap.dedent(source)); remove leading docstrings in module/class/function scopes; ast.unparse", "unparseable_or_empty_corpus": len(unparseable), "deduplicated_exact_cleaned_functions": duplicates, "clean_unique_corpus": len(clean_candidates)},
        "leak_audit": {"normalization": "lowercase and collapse whitespace; exact normalized query substring in cleaned candidate", "query_candidate_pairs": sum(map(len, leaks.values())), "candidates_removed": len(candidate_leaks), "affected_queries": len(leaks), "removed_candidate_ids_sha256": hashlib.sha256("\n".join(sorted(candidate_leaks)).encode()).hexdigest()},
        "eligible": {"corpus": len(eligible_corpus), "queries": len(eligible_queries), "queries_lost_to_unparseable_gold": len(qrels_lost_to_parse), "sampled_queries": len(cases)},
        "bm25": {"implementation": "benchmarks/rerank/run.py retrieve-equivalent BM25; top_k=30; full eligible cleaned corpus", "all_case_candidate_recall_at_30": {"hits": recall_at_30, "total": len(cases), "rate": recall_at_30 / len(cases)}},
        "artifacts": {"input_sha256": sha256(public / "input.json")},
        "notes": ["Cases with no gold candidate in BM25 top 30 are retained.", "Raw source rows are outside the repository; review the derived input's dataset licensing before committing it."],
    }
    write_json(public / "provenance.json", provenance)
    print(json.dumps({"input": str(public / "input.json"), "provenance": str(public / "provenance.json"), "sampled": len(cases), "candidate_recall_at_30": provenance["bm25"]["all_case_candidate_recall_at_30"]}, indent=2))


if __name__ == "__main__":
    main()
