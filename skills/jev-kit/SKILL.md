---
name: jev-kit
description: Use Jev for batches of source-bound claim checks, semantic classification, exact candidate extraction, bounded choices, or optional reranking of existing search candidates. Prefer existing tool outputs and fixed templates. Does not browse, write code, approve actions, certify completion, or automatically reduce context or reasoning.
---

# Jev Kit

Use for repeated, bounded semantic judgments where the evidence is already available. Keep planning, new code/text, missing evidence and final acceptance in the main agent. Skip an extra model call for one obvious fact or a deterministic rule.

## Decide whether Jev helps

- Prefer Jev for repeated classification with a stable catalog, or many independent checks whose outputs can be consumed by ordinary code. Apply exact rules first; retain ambiguous items for review.
- If the main model already has a small set of sources and can answer in one response, answer directly. Two-host evidence trials found an extra Jev round slower; a smaller model did not gain a dependable accuracy advantage.
- Do not send only flagged evidence back to the main model and silently accept the rest. Both high-confidence Jev mistakes and main-model review mistakes occurred in tests. When correctness matters, check the relevant original sources regardless of confidence. A representative labeled sample can evaluate a new low-impact workload before bulk use.
- Avoid using Jev to lower reasoning effort, certify completion, or rerank every search. Choose it for a measured workload, not merely because the tool is installed.

## Choose one tool

| Need | Registered tool | CLI mode |
|---|---|---|
| Check claims against their own sources | `jev_evidence` | `evidence` |
| Classify texts using a shared catalog | `jev_classify` | `classify` |
| Find exact values among regex matches | `jev_extract` | `extract` |
| Compare 2–6 known alternatives | `jev_decide` | `decide` |
| Optionally rank 1–30 existing search candidates | `jev_rerank` | `rerank` |

Use the registered native or MCP tool for inputs already available in context. When structured inputs already exist in local files, prefer `jev-kit MODE --input /absolute/input.json --output /absolute/new-receipt.json`; pass the file directly instead of having an LLM retype its sources into tool arguments. Use ordinary code to map existing records to the schema. For a managed installation, the shared CLI is `node "$HOME/.local/share/jev-kit/current/dist/cli.js" MODE ...`. Native packages contain a copy of this Skill, so do not assume its parent directory contains the runtime. Only for a checkout-based Skill, resolve its symlink and run `node ../../dist/cli.js MODE ...` relative to that source directory. The bundle requires Node 22+ and no dependency installation. See [schemas and examples](references/inputs.md) for the selected mode only. `--validate-only` checks locally without API calls.

Reuse raw sources and existing structured outputs; do not ask another LLM to summarize sources just to call Jev. Preserve qualifiers, corrections and contradictory context. Submit related records in one tool/CLI call rather than one call per record. Evidence/classification keep at most 8 items per batch and overlap up to 4 batches per invocation; larger batches degraded accuracy in tests. Evidence splits by the engine's state-size budget and reuses identical source strings within a batch. Reranking uses one bounded batch. Oversized single items remain unresolved without truncation. Supplied text goes to TypeSafe; include only material relevant and authorized for the current task, never credentials.

For file workflows, retain the private input and full receipt for replay; inspect only the needed result columns first, then read original sources for follow-up. Avoid pasting full probability distributions and hashes back into model context when only IDs, proposed labels and review flags are needed. Compact output does not make unreviewed answers correct.

Images (experimental): evidence items, classify items and decide candidates accept `images: [{"path": "/absolute/file.png"}]` (≤4 per item; PNG/JPEG by content; ≤8 MiB and 280–1568 px per side; ≤20 MiB and ≤16 images per request). Text may be omitted when images are present. The TypeSafe images header is added automatically; receipts keep only counts and hashes. Use only when the image itself is the evidence; accuracy is not yet established.

## Read the result

Read `status`, then each result's **`requires_review`**. `partial` means some provider checks failed: keep all affected items unresolved. A review retains a raw guess for diagnostics; it is not a settled answer. Preserve original IDs and source references for follow-up.

- Evidence: `verdict` is supports / contradicts / insufficient / quote_not_found / review. Source support is not independent truth or completion evidence. Quote mismatch refers only to this exact supplied text, including whitespace/OCR differences.
- Classification: `classification` is the proposed class. Classes marked `requires_review`, including `manual_review`, remain review even with high confidence.
- Extraction: use `value` only when status=extracted and requires_review=false. `candidate_value` may be a tentative guess. Incomplete candidate sets and regex errors remain review. `not_found` concerns this pattern/document, not all possible evidence.
- Reranking: `selected_ids` is an inspection prefix, not proof of relevance. `remaining_ids` retains the rest. Keep original candidate texts and expand retrieval if the first set is insufficient. On failure, use the preserved original order and review flags. Do not enable automatically on every search: current tests did not show a coding speedup.
- Decision: `selected` is an advisory candidate. Escape choices and uncertain, unsupported or contradicted requirements force review. No decision authorizes execution.

For review, inspect the original material using the normal workflow; do not repeatedly call Jev until it agrees. Confidence is not a correctness guarantee. No tool replaces actual tests, browser/device validation, user authorization or existing permissions.

## Experimental browser use

The separate browser CLI is most promising for choosing among visible controls with little text generation. Keep a capable text model for writing fields and planning dependent actions. New local tasks found Jev faster on semantic selection, but slower than a native bounded-batch planner on a text-heavy form and blocked on a form whose required field appeared only after another selection. Treat BLOCKED as a handoff; re-observe and continue with the normal browser workflow. Do not restart the same failed job or change its goal merely to obtain a completion signal. See the runtime's `integrations/ego-browser/README.md` for setup; browser use is not automatically enabled by installing these five tools.

CLI exit 0 means processing completed; 3 means review is needed; 2 means invalid input or a service/validation failure. Never interpret exit 0 as all claims being true. Receipts are new files with mode 0600; existing files are not overwritten. They retain hashes, results, usage and resolved model, not full source bodies; retain the input for replay.

Credentials: `TYPESAFE_API_KEY`, then `TYPESAFE_API_KEY_FILE`, then `~/.config/jev-benchmark/typesafe-api-key`. Do not put the key in tool input, shell arguments or reports. Missing keys return unresolved results, not mock success.
