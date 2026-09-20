#!/usr/bin/env python3
"""Summarize the frozen reranking/repair screening without publishing raw prompts.

Input directories are private experiment receipts.  Output intentionally keeps
only trial IDs, aggregate metrics, task IDs, and frozen-gate conclusions: it
does not copy source snippets, prompts, replacement code, stderr, or paths.
"""
import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def read_json(path):
    with path.open() as handle:
        return json.load(handle)


def median(values):
    return statistics.median(values) if values else None


def percent(value):
    return round(value * 100, 2) if value is not None else None


def ratio_reduction(reference, candidate):
    if not reference or candidate is None:
        return None
    return (reference - candidate) / reference


def load_receipts(directory, plan):
    """Return one known result per planned ID plus missing/invalid IDs."""
    results, missing, invalid = {}, [], []
    for trial in plan["trials"]:
        trial_id = trial["id"]
        receipt = directory / trial_id / "result.json"
        if not receipt.exists():
            missing.append(trial_id)
            continue
        try:
            value = read_json(receipt)
        except (OSError, ValueError, TypeError):
            invalid.append(trial_id)
            continue
        if value.get("id") != trial_id:
            invalid.append(trial_id)
            continue
        results[trial_id] = value
    return results, missing, invalid


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def mapping(value):
    return value if isinstance(value, dict) else {}


def rank_usage(row):
    return mapping(mapping(row.get("ranking")).get("usage"))


def observed_models(rows, key):
    return sorted({model for row in rows for model in (mapping(row.get(key)).get("models") or []) if isinstance(model, str) and model != "<synthetic>"})


def valid_rank_api_rows(rows):
    return [row for row in rows if mapping(row.get("ranking")).get("status") == "ok" and number(mapping(row.get("ranking")).get("api_s")) > 0]


def valid_main_api_rows(rows):
    return [row for row in rows if mapping(row.get("main")).get("complete") and number(mapping(row.get("main")).get("api_s")) > 0]


def aggregate_usage(rows, key="main"):
    totals = Counter()
    for row in rows:
        usage = mapping(mapping(row.get(key)).get("usage"))
        for field in ("input", "output", "cache_read", "cache_write", "reasoning"):
            totals[field] += number(usage.get(field))
    return dict(totals)


def coding_arm(rows):
    times = lambda key: [number(row.get(key)) for row in rows]
    rank_api_rows = valid_rank_api_rows(rows)
    main_api_rows = valid_main_api_rows(rows)
    return {
        "assigned": len(rows),
        "passed": sum(bool(row.get("passed")) for row in rows),
        "wall_s_median_all_attempts": median(times("wall_s")),
        "retrieval_s_median_all_attempts": median(times("retrieval_s")),
        "rank_wall_s_median_all_attempts": median([number(row.get("ranking", {}).get("wall_s")) for row in rows]),
        "rank_api_s_median_valid": median([number(mapping(row.get("ranking")).get("api_s")) for row in rank_api_rows]),
        "rank_api_valid_count": len(rank_api_rows),
        "main_wall_s_median_all_attempts": median([number(row.get("main", {}).get("wall_s")) for row in rows]),
        "main_api_s_median_valid": median([number(mapping(row.get("main")).get("api_s")) for row in main_api_rows]),
        "main_api_valid_count": len(main_api_rows),
        "test_s_median_all_attempts": median(times("test_s")),
        "main_usage_total": aggregate_usage(rows),
        "main_model_call_count": sum(bool(mapping(row.get("main"))) for row in rows),
        "main_observed_models": observed_models(rows, "main"),
        "rank_call_count": sum(number(mapping(row.get("ranking")).get("calls")) for row in rows),
        "rank_observed_models": observed_models(rows, "ranking"),
        "jev_rank_usage_total": {
            "inputTokens": sum(number(rank_usage(row).get("inputTokens")) for row in rows if row.get("arm") == "jev"),
            "outputTokens": sum(number(rank_usage(row).get("outputTokens")) for row in rows if row.get("arm") == "jev"),
        },
        "llm_rank_usage_total": aggregate_usage([row for row in rows if row.get("arm") == "llm"], "ranking"),
        "ranking_fallbacks": sum(row.get("ranking", {}).get("status") != "ok" for row in rows),
    }


def coding_summary(plan, results, missing, invalid):
    expected = len(plan["trials"])
    rows = list(results.values())
    complete = not missing and not invalid and len(rows) == expected
    by_arm = defaultdict(list)
    by_repeat_arm = defaultdict(list)
    by_key = {}
    for row in rows:
        by_arm[row.get("arm")].append(row)
        by_repeat_arm[(row.get("repeat"), row.get("arm"))].append(row)
        by_key[(row.get("repeat"), row.get("task"), row.get("arm"))] = row
    arms = {arm: coding_arm(by_arm[arm]) for arm in ("bm25", "jev", "llm", "full30")}
    per_repeat = {}
    for repeat in (1, 2):
        per_repeat[str(repeat)] = {}
        for arm in ("bm25", "jev", "llm", "full30"):
            values = by_repeat_arm[(repeat, arm)]
            per_repeat[str(repeat)][arm] = {
                "assigned": len(values),
                "passed": sum(bool(value.get("passed")) for value in values),
                "distinct_tasks_passed": sorted(value["task"] for value in values if value.get("passed")),
                "distinct_task_count": len({value["task"] for value in values if value.get("passed")}),
                "wall_s_median_all_attempts": median([number(value.get("wall_s")) for value in values]),
            }

    paired = {}
    for comparator in ("bm25", "llm", "full30"):
        pairs = []
        for repeat in (1, 2):
            for task in {trial.get("task") for trial in plan["trials"]}:
                jev = by_key.get((repeat, task, "jev"))
                other = by_key.get((repeat, task, comparator))
                if jev and other and jev.get("passed") and other.get("passed"):
                    pairs.append((jev, other))
        reductions = [ratio_reduction(other.get("wall_s"), jev.get("wall_s")) for jev, other in pairs]
        paired[comparator] = {
            "shared_success_pairs": len(pairs),
            "jev_wall_s_median": median([pair[0].get("wall_s") for pair in pairs]),
            "comparator_wall_s_median": median([pair[1].get("wall_s") for pair in pairs]),
            "paired_reduction_median_percent": percent(median(reductions)),
            "faster_pairs": sum(reduction > 0 for reduction in reductions),
            "slower_or_equal_pairs": sum(reduction <= 0 for reduction in reductions),
        }

    jev_rows = by_arm["jev"]
    all_jev_valid = len(jev_rows) == 16 and all(row.get("ranking", {}).get("status") == "ok" for row in jev_rows)
    quality = {
        str(repeat): {
            "jev_vs_full30": per_repeat[str(repeat)]["jev"]["distinct_task_count"] >= per_repeat[str(repeat)]["full30"]["distinct_task_count"],
            "jev_vs_llm": per_repeat[str(repeat)]["jev"]["distinct_task_count"] >= per_repeat[str(repeat)]["llm"]["distinct_task_count"],
        }
        for repeat in (1, 2)
    }
    jev_median = arms["jev"]["wall_s_median_all_attempts"]
    speed = {arm: ratio_reduction(arms[arm]["wall_s_median_all_attempts"], jev_median) for arm in ("bm25", "llm", "full30")}
    quality_ok = all(all(check.values()) for check in quality.values())
    speed_ok = all((speed[arm] is not None and speed[arm] >= .20) for arm in ("llm", "full30"))
    alternative = {}
    for repeat in (1, 2):
        solved_more = per_repeat[str(repeat)]["jev"]["distinct_task_count"] >= per_repeat[str(repeat)]["bm25"]["distinct_task_count"] + 2
        match_and_speed = (per_repeat[str(repeat)]["jev"]["distinct_task_count"] == per_repeat[str(repeat)]["bm25"]["distinct_task_count"]
                           and speed["bm25"] is not None and speed["bm25"] >= .20)
        alternative[str(repeat)] = {"solve_two_more_than_bm25": solved_more, "match_bm25_and_speed_20_percent": match_and_speed, "pass": solved_more or match_and_speed}
    gate_checks = {
        "all_jev_rank_calls_valid": all_jev_valid,
        "quality_no_worse_each_repeat": quality_ok,
        "median_wall_20_percent_faster_than_full30_and_llm": speed_ok,
        "bm25_alternative_each_repeat": all(value["pass"] for value in alternative.values()),
    }
    gate_pass = complete and all(gate_checks.values())
    task_rows = []
    for repeat in (1, 2):
        for task in sorted({trial.get("task") for trial in plan["trials"]}):
            entry = {"repeat": repeat, "task": task}
            for arm in ("bm25", "jev", "llm", "full30"):
                row = by_key.get((repeat, task, arm))
                entry[arm] = None if row is None else {
                    "passed": bool(row.get("passed")), "wall_s": row.get("wall_s"),
                    "candidate_recall": bool(row.get("candidate_recall")),
                    "top5_recall": bool(row.get("top5_recall")),
                    "visible_recall": bool(row.get("visible_recall")),
                    "ranking_status": row.get("ranking", {}).get("status"),
                }
            task_rows.append(entry)
    bm25_visible = [row for row in by_arm["bm25"] if row.get("visible_recall")]
    notes = [
        "This is an authored synthetic local-code screen with eight tasks and two repeats; it is not a general productivity measurement.",
        "All baseline BM25 selected-five trials place the gold target in view." if len(bm25_visible) == len(by_arm["bm25"]) else "Some BM25 selected-five trials omit the gold target.",
        "Because the frozen local fixture has all gold targets in BM25 top five, it has zero recall headroom for reranking; repair quality and latency remain the relevant coding measures.",
    ]
    return {
        "kind": "coding", "status": "complete" if complete else "incomplete", "completion": {"expected": expected, "present": len(rows), "missing_ids": missing, "invalid_ids": invalid},
        "arms": arms, "per_repeat": per_repeat, "paired_shared_success": paired,
        "gate": {"frozen_text": plan.get("gate", {}).get("end_to_end"), "checks": gate_checks, "quality_by_repeat": quality, "speed_reduction_vs_comparator": {key: percent(value) for key, value in speed.items()}, "bm25_alternative": alternative, "pass": gate_pass},
        "per_task": task_rows, "notes": notes,
    }


def retrieval_arm(rows):
    n = len(rows)
    rank_api_rows = valid_rank_api_rows(rows)
    return {
        "assigned": n,
        "top1": sum(bool(row.get("top1")) for row in rows),
        "top1_rate_percent": percent(sum(bool(row.get("top1")) for row in rows) / n) if n else None,
        "recall5": sum(bool(row.get("recall5")) for row in rows),
        "recall5_rate_percent": percent(sum(bool(row.get("recall5")) for row in rows) / n) if n else None,
        "rank_wall_s_median_all_attempts": median([number(row.get("ranking", {}).get("wall_s")) for row in rows]),
        "rank_api_s_median_valid": median([number(mapping(row.get("ranking")).get("api_s")) for row in rank_api_rows]),
        "rank_api_valid_count": len(rank_api_rows),
        "fallback_count": sum(row.get("ranking", {}).get("status") != "ok" for row in rows),
        "rank_call_count": sum(number(mapping(row.get("ranking")).get("calls")) for row in rows),
        "rank_observed_models": observed_models(rows, "ranking"),
        "jev_rank_usage_total": {
            "inputTokens": sum(number(rank_usage(row).get("inputTokens")) for row in rows if row.get("arm") == "jev"),
            "outputTokens": sum(number(rank_usage(row).get("outputTokens")) for row in rows if row.get("arm") == "jev"),
        },
        "llm_rank_usage_total": aggregate_usage([row for row in rows if row.get("arm") == "llm"], "ranking"),
        "valid_only": {
            "assigned": len(rank_api_rows),
            "top1": sum(bool(row.get("top1")) for row in rank_api_rows),
            "recall5": sum(bool(row.get("recall5")) for row in rank_api_rows),
            "top1_rate_percent": percent(sum(bool(row.get("top1")) for row in rank_api_rows) / len(rank_api_rows)) if rank_api_rows else None,
            "recall5_rate_percent": percent(sum(bool(row.get("recall5")) for row in rank_api_rows) / len(rank_api_rows)) if rank_api_rows else None,
        },
    }


def retrieval_summary(plan, results, missing, invalid):
    expected = len(plan["trials"])
    rows = list(results.values())
    complete = not missing and not invalid and len(rows) == expected
    by_arm = defaultdict(list)
    by_case = defaultdict(dict)
    for row in rows:
        by_arm[row.get("arm")].append(row)
        by_case[row.get("case")][row.get("arm")] = row
    arms = {arm: retrieval_arm(by_arm[arm]) for arm in ("bm25", "jev", "llm")}

    conditional_rows = {arm: [row for row in by_arm[arm] if row.get("candidate_recall")] for arm in ("bm25", "jev", "llm")}
    conditional = {arm: retrieval_arm(conditional_rows[arm]) for arm in ("bm25", "jev", "llm")}
    pairs = {}
    for comparator in ("bm25", "llm"):
        complete_pairs = [(case, values["jev"], values[comparator]) for case, values in by_case.items() if "jev" in values and comparator in values]
        wins = sum(jev.get("top1") and not other.get("top1") for _, jev, other in complete_pairs)
        losses = sum(other.get("top1") and not jev.get("top1") for _, jev, other in complete_pairs)
        ties = len(complete_pairs) - wins - losses
        recall_wins = sum(jev.get("recall5") and not other.get("recall5") for _, jev, other in complete_pairs)
        recall_losses = sum(other.get("recall5") and not jev.get("recall5") for _, jev, other in complete_pairs)
        pairs[comparator] = {
            "paired_cases": len(complete_pairs),
            "top1_wins": wins, "top1_losses": losses, "top1_ties": ties,
            "jev_minus_comparator_top1_pp": percent((sum(bool(j.get("top1")) for _, j, _ in complete_pairs) - sum(bool(o.get("top1")) for _, _, o in complete_pairs)) / len(complete_pairs)) if complete_pairs else None,
            "recall5_wins": recall_wins,
            "recall5_losses": recall_losses,
            "recall5_ties": len(complete_pairs) - recall_wins - recall_losses,
            "jev_minus_comparator_recall5_pp": percent((sum(bool(j.get("recall5")) for _, j, _ in complete_pairs) - sum(bool(o.get("recall5")) for _, _, o in complete_pairs)) / len(complete_pairs)) if complete_pairs else None,
        }
    jev_valid = len(by_arm["jev"]) == 64 and all(row.get("ranking", {}).get("status") == "ok" for row in by_arm["jev"])
    jev_top1 = arms["jev"]["top1_rate_percent"]
    bm25_top1 = arms["bm25"]["top1_rate_percent"]
    llm_top1 = arms["llm"]["top1_rate_percent"]
    speed = ratio_reduction(arms["llm"]["rank_wall_s_median_all_attempts"], arms["jev"]["rank_wall_s_median_all_attempts"])
    gate_checks = {
        "all_jev_rank_calls_valid": jev_valid,
        "top1_at_least_bm25_plus_10pp": jev_top1 is not None and bm25_top1 is not None and jev_top1 >= bm25_top1 + 10,
        "recall5_at_least_bm25": arms["jev"]["recall5_rate_percent"] is not None and arms["bm25"]["recall5_rate_percent"] is not None and arms["jev"]["recall5_rate_percent"] >= arms["bm25"]["recall5_rate_percent"],
        "top1_within_5pp_of_llm": jev_top1 is not None and llm_top1 is not None and jev_top1 >= llm_top1 - 5,
        "median_rank_wall_30_percent_faster_than_llm": speed is not None and speed >= .30,
    }
    cases = []
    for case in sorted(by_case, key=str):
        values = by_case[case]
        cases.append({"case": case, **{arm: None if arm not in values else {"candidate_recall": bool(values[arm].get("candidate_recall")), "top1": bool(values[arm].get("top1")), "recall5": bool(values[arm].get("recall5")), "ranking_status": values[arm].get("ranking", {}).get("status"), "rank_wall_s": values[arm].get("ranking", {}).get("wall_s")} for arm in ("bm25", "jev", "llm")}})
    return {
        "kind": "retrieval", "status": "complete" if complete else "incomplete", "completion": {"expected": expected, "present": len(rows), "missing_ids": missing, "invalid_ids": invalid},
        "all_cases": arms, "conditional_on_candidate_recall": conditional, "paired_top1": pairs,
        "gate": {"frozen_text": plan.get("gate", {}).get("ranking"), "checks": gate_checks, "jev_vs_llm_rank_wall_reduction_percent": percent(speed), "pass": complete and all(gate_checks.values())},
        "per_case": cases,
        "notes": ["Ranking results measure ordering among supplied candidates; they do not establish coding productivity."],
    }


def seconds(value):
    if value is None:
        return "—"
    if value < .001:
        return "<0.001 s"
    return f"{value:.3f} s"


def count_rate(hits, total, rate):
    return f"{hits}/{total} ({rate:.2f}%)" if rate is not None else f"{hits}/{total} (—)"


def api_seconds(value, count):
    return f"{seconds(value)} (n={count})" if count else "N/A (n=0)"


def failed_checks(report):
    failures = [name for name, passed in report["gate"]["checks"].items() if not passed]
    if report["status"] != "complete":
        completion = report["completion"]
        failures.insert(0, f"incomplete assigned trials ({completion['present']}/{completion['expected']})")
    return failures


def markdown(summary):
    coding = summary["coding"]
    retrieval = summary["retrieval"]
    lines = ["# Jev reranking screening results", "", f"Overall status: **{summary['status']}**.", ""]

    lines += ["## Coding repair screen", "", f"Status: **{coding['status']}** ({coding['completion']['present']}/{coding['completion']['expected']} assigned trials present).", "", "| Arm | Assigned pipeline | Repairs passed | Main input total | Median total wall | Fallbacks |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for arm, values in coding["arms"].items():
        lines.append(f"| {arm} | {values['assigned']} | {values['passed']} | {values['main_usage_total'].get('input', 0):,} | {seconds(values['wall_s_median_all_attempts'])} | {values['ranking_fallbacks']} |")
    lines += ["", "Wall-time medians include every assigned pipeline attempt. API medians use only valid status-OK responses with API time above zero; zero denotes no provider API observation, not a measured zero-latency call.", "", "| Arm | Rank wall | Rank API valid-only | Main wall | Main API valid-only | Test |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for arm, values in coding["arms"].items():
        lines.append(f"| {arm} | {seconds(values['rank_wall_s_median_all_attempts'])} | {api_seconds(values['rank_api_s_median_valid'], values['rank_api_valid_count'])} | {seconds(values['main_wall_s_median_all_attempts'])} | {api_seconds(values['main_api_s_median_valid'], values['main_api_valid_count'])} | {seconds(values['test_s_median_all_attempts'])} |")
    lines += ["", "| Repeat | Arm | Passed | Median total wall |", "| --- | --- | ---: | ---: |"]
    for repeat, arms in coding["per_repeat"].items():
        for arm, values in arms.items():
            lines.append(f"| {repeat} | {arm} | {values['passed']} | {seconds(values['wall_s_median_all_attempts'])} |")
    lines += ["", "| Jev compared with | Shared successful pairs | Jev median | Comparator median | Median of paired reductions | Faster/slower-or-equal |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for comparator, values in coding["paired_shared_success"].items():
        reduction = values["paired_reduction_median_percent"]
        rendered = "—" if reduction is None else f"{reduction:.2f}%"
        lines.append(f"| {comparator} | {values['shared_success_pairs']} | {seconds(values['jev_wall_s_median'])} | {seconds(values['comparator_wall_s_median'])} | {rendered} | {values['faster_pairs']}/{values['slower_or_equal_pairs']} |")
    lines += [""]
    for arm, values in coding["arms"].items():
        lines.append(f"- `{arm}`: main calls {values['main_model_call_count']}; rank attempts {values['rank_call_count']}; main models {', '.join(values['main_observed_models']) or 'none'}; rank models {', '.join(values['rank_observed_models']) or 'none'}.")
    coding_failures = failed_checks(coding)
    lines += ["", f"Frozen coding gate: **{'PASS' if coding['gate']['pass'] else 'NOT PASS'}**. Its speed check uses the ratio of arm medians, distinct from the paired-reduction descriptive table."]
    if coding_failures:
        lines += ["Failing checks:"] + [f"- `{item}`" for item in coding_failures]
    lines += [""] + coding["notes"] + [""]

    lines += ["## Retrieval reranking screen", "", f"Status: **{retrieval['status']}** ({retrieval['completion']['present']}/{retrieval['completion']['expected']} assigned trials present).", "", "| Arm | Assigned pipeline | Top-1 | Recall@5 | Median rank wall | Median rank API valid-only | Fallbacks |", "| --- | ---: | --- | --- | ---: | ---: | ---: |"]
    for arm, values in retrieval["all_cases"].items():
        lines.append(f"| {arm} | {values['assigned']} | {count_rate(values['top1'], values['assigned'], values['top1_rate_percent'])} | {count_rate(values['recall5'], values['assigned'], values['recall5_rate_percent'])} | {seconds(values['rank_wall_s_median_all_attempts'])} | {api_seconds(values['rank_api_s_median_valid'], values['rank_api_valid_count'])} | {values['fallback_count']} |")
    lines += ["", "Valid-response sensitivity only; this does not replace the assigned-pipeline counts above.", "", "| Arm | Valid provider responses | Top-1 | Recall@5 |", "| --- | ---: | --- | --- |"]
    for arm, values in retrieval["all_cases"].items():
        valid = values["valid_only"]
        lines.append(f"| {arm} | {valid['assigned']} | {count_rate(valid['top1'], valid['assigned'], valid['top1_rate_percent'])} | {count_rate(valid['recall5'], valid['assigned'], valid['recall5_rate_percent'])} |")
    lines += ["", "Conditional on a gold candidate being in the supplied 30-candidate set:", "", "| Arm | Eligible cases | Top-1 | Recall@5 |", "| --- | ---: | --- | --- |"]
    for arm, values in retrieval["conditional_on_candidate_recall"].items():
        lines.append(f"| {arm} | {values['assigned']} | {count_rate(values['top1'], values['assigned'], values['top1_rate_percent'])} | {count_rate(values['recall5'], values['assigned'], values['recall5_rate_percent'])} |")
    lines += ["", "| Jev compared with | Paired cases | Top-1 W/L/T | Recall@5 W/L/T | Top-1 difference | Recall@5 difference |", "| --- | ---: | --- | --- | ---: | ---: |"]
    for comparator, values in retrieval["paired_top1"].items():
        top1 = "—" if values["jev_minus_comparator_top1_pp"] is None else f"{values['jev_minus_comparator_top1_pp']:.2f} pp"
        recall = "—" if values["jev_minus_comparator_recall5_pp"] is None else f"{values['jev_minus_comparator_recall5_pp']:.2f} pp"
        lines.append(f"| {comparator} | {values['paired_cases']} | {values['top1_wins']}/{values['top1_losses']}/{values['top1_ties']} | {values['recall5_wins']}/{values['recall5_losses']}/{values['recall5_ties']} | {top1} | {recall} |")
    lines += ["", "Rank wall time includes native CLI startup; rank API time is reported separately above. `<synthetic>` receipt model markers are excluded from actual-model lists, while raw receipts remain unchanged. The two LLM fallbacks were native-session quota outcomes on cases 623 and 78; no new Claude requests were made for this analysis."]
    for arm, values in retrieval["all_cases"].items():
        lines.append(f"- `{arm}`: rank attempts {values['rank_call_count']}; valid provider responses {values['rank_api_valid_count']}; rank models {', '.join(values['rank_observed_models']) or 'none'}.")
    retrieval_failures = failed_checks(retrieval)
    lines += ["", f"Frozen retrieval gate: **{'PASS' if retrieval['gate']['pass'] else 'NOT PASS'}**."]
    if retrieval_failures:
        lines += ["Failing checks:"] + [f"- `{item}`" for item in retrieval_failures]
    lines += [""] + retrieval["notes"] + [""]

    lines += ["The coding fixture contains eight independent authored synthetic tasks, and all gold targets are in BM25 top five; it cannot support a general product claim or a local recall-improvement claim. The frozen public retrieval design is a 64-case sample under a newly cleaned source condition; when complete, 61 cases had a gold candidate in the supplied 30-candidate set. Partial runs use the available conditional denominator shown above. Paired target labels show benchmark relevance, not complete task or user relevance.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coding", type=Path, required=True)
    parser.add_argument("--retrieval", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    coding_plan = read_json(args.coding / "plan.json")
    retrieval_plan = read_json(args.retrieval / "plan.json")
    coding_results, coding_missing, coding_invalid = load_receipts(args.coding, coding_plan)
    retrieval_results, retrieval_missing, retrieval_invalid = load_receipts(args.retrieval, retrieval_plan)
    summary = {
        "status": "complete" if not (coding_missing or coding_invalid or retrieval_missing or retrieval_invalid) else "incomplete",
        "coding": coding_summary(coding_plan, coding_results, coding_missing, coding_invalid),
        "retrieval": retrieval_summary(retrieval_plan, retrieval_results, retrieval_missing, retrieval_invalid),
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (args.out / "RESULTS.md").write_text(markdown(summary))
    print(json.dumps({"status": summary["status"], "coding": summary["coding"]["status"], "retrieval": summary["retrieval"]["status"]}))


if __name__ == "__main__":
    main()
