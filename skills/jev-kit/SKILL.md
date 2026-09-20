---
name: jev-kit
description: Use Jev for batches of source-bound claim checks, semantic classification, exact candidate extraction, bounded choices, or optional reranking of existing search candidates. Prefer existing tool outputs and fixed templates. Does not browse, write code, approve actions, certify completion, or automatically reduce context or reasoning.
---

# Jev Kit

Use for repeated, bounded semantic judgments where the evidence is already available. Keep planning, new code/text, missing evidence and final acceptance in the main agent. Skip an extra model call for one obvious fact or a deterministic rule.

## Choose one tool

| Need | Registered tool | CLI mode |
|---|---|---|
| Check claims against their own sources | `jev_evidence` | `evidence` |
| Classify texts using a shared catalog | `jev_classify` | `classify` |
| Find exact values among regex matches | `jev_extract` | `extract` |
| Compare 2–6 known alternatives | `jev_decide` | `decide` |
| Optionally rank 1–30 existing search candidates | `jev_rerank` | `rerank` |

Prefer the registered native or MCP tool when available. Otherwise use `jev-kit MODE --input /absolute/input.json --output /absolute/new-receipt.json`. For a managed installation, the shared CLI is `node "$HOME/.local/share/jev-kit/current/dist/cli.js" MODE ...`. Native packages contain a copy of this Skill, so do not assume its parent directory contains the runtime. Only for a checkout-based Skill, resolve its symlink and run `node ../../dist/cli.js MODE ...` relative to that source directory. The bundle requires Node 22+ and no dependency installation. See [schemas and examples](references/inputs.md) for the selected mode only. `--validate-only` checks locally without API calls.

Reuse raw sources and existing structured outputs; do not ask another LLM to summarize sources just to call Jev. Preserve qualifiers, corrections and contradictory context. Batch existing records in one call; the runtime splits classification/evidence requests; reranking uses one bounded batch. It rejects oversized input instead of silently truncating evidence. Supplied text goes to TypeSafe; include only material relevant and authorized for the current task, never credentials.

## Read the result

Read `status`, then each result's **`requires_review`**. `partial` means some provider checks failed: keep all affected items unresolved. A review retains a raw guess for diagnostics; it is not a settled answer. Preserve original IDs and source references for follow-up.

- Evidence: `verdict` is supports / contradicts / insufficient / quote_not_found / review. Source support is not independent truth or completion evidence. Quote mismatch refers only to this exact supplied text, including whitespace/OCR differences.
- Classification: `classification` is the proposed class. Classes marked `requires_review`, including `manual_review`, remain review even with high confidence.
- Extraction: use `value` only when status=extracted and requires_review=false. `candidate_value` may be a tentative guess. Incomplete candidate sets and regex errors remain review. `not_found` concerns this pattern/document, not all possible evidence.
- Reranking: `selected_ids` is an inspection prefix, not proof of relevance. `remaining_ids` retains the rest. Keep original candidate texts and expand retrieval if the first set is insufficient. On failure, use the preserved original order and review flags. Do not enable automatically on every search: current tests did not show a coding speedup.
- Decision: `selected` is an advisory candidate. Escape choices and uncertain, unsupported or contradicted requirements force review. No decision authorizes execution.

For review, inspect the original material using the normal workflow; do not repeatedly call Jev until it agrees. Confidence is not a correctness guarantee. No tool replaces actual tests, browser/device validation, user authorization or existing permissions.

CLI exit 0 means processing completed; 3 means review is needed; 2 means invalid input or a service/validation failure. Never interpret exit 0 as all claims being true. Receipts are new files with mode 0600; existing files are not overwritten. They retain hashes, results, usage and resolved model, not full source bodies; retain the input for replay.

Credentials: `TYPESAFE_API_KEY`, then `TYPESAFE_API_KEY_FILE`, then `~/.config/jev-benchmark/typesafe-api-key`. Do not put the key in tool input, shell arguments or reports. Missing keys return unresolved results, not mock success.
