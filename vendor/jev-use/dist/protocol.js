/**
 * The jev-use handoff protocol.
 *
 * Jev (TypeSafe AI's System One model) answers typed questions about a state
 * in one forward pass — it never generates text. An LLM and Jev cooperate by
 * handing off:
 *
 *   LLM ──(state + typed questions)──▶ Jev        fast, cheap, calibrated
 *   Jev ──(verdict, escalate=true)──▶ LLM         when a boundary is hit
 *
 * Escalation is not an error: it is a typed signal that this step belongs to
 * the LLM. The boundaries, in the words the verdict uses:
 *
 *   - writing     : the step must produce new content (text, code, free-form
 *     tool arguments). Structurally impossible for Jev; decided BEFORE
 *     calling it.
 *   - open_ended  : the question cannot be expressed as noul / choice / score
 *     (no enumerable options, no ordered levels). Decided BEFORE calling.
 *   - oversized   : the state itself does not fit in Jev's context. Also
 *     decided BEFORE calling, for the whole batch.
 *   - unsure      : Jev answered but the distribution is too flat to act on.
 *     Decided AFTER calling, against a configurable threshold.
 *
 * Plus one operational reason, `unreachable`: Jev being down must degrade to
 * "the LLM handles it", never block the loop.
 *
 * Questions are written with the three builders at the bottom of this file —
 * `check` (noul), `pick` (choice), `rate` (score). The type names and wire
 * values keep Jev's own vocabulary; the builders only spell it in English.
 */
/** Escalate below this confidence unless the backend or caller says otherwise. */
export const DEFAULT_CONFIDENCE_THRESHOLD = 0.75;
/**
 * Ceiling for the serialized state, in estimated tokens. Jev's context is
 * 64k with at most 32k for the state; stay under it with margin.
 */
export const DEFAULT_MAX_STATE_TOKENS = 30_000;
/** The id a question gets when the caller named none. */
export function defaultQuestionId(index) {
    return `q${index}`;
}
/** Normalize choice options to label → meaning ("" when labels-only). */
export function optionEntries(options) {
    return Array.isArray(options)
        ? options.map((label) => [label, ""])
        : Object.entries(options);
}
/** Rough token estimate (~4 chars/token) — a guard rail, not an accountant. */
export function estimateTokens(state) {
    const text = typeof state === "string" ? state : JSON.stringify(state);
    return Math.ceil(text.length / 4);
}
/** The state as the backends send it: strings verbatim, everything else JSON. */
export function serializeState(state) {
    return typeof state === "string" ? state : JSON.stringify(state);
}
/**
 * Ask whether something is true (Jev's `noul` primitive). The verdict answers
 * with the probability, and `confidence` is how far that sits from a coin flip.
 *
 * ```ts
 * check("Did the run fully succeed?")
 * check("Is the branch safe to merge?", {
 *   true: "green CI and no conflicts",
 *   false: "anything failing or unmerged",
 * })
 * ```
 */
export function check(question, criteria) {
    return criteria
        ? { type: "noul", question, criteria }
        : { type: "noul", question };
}
/**
 * Ask which of the enumerated options fits (Jev's `choice` primitive). Pass
 * labels, or label → what picking it means (the meanings measurably help).
 * The verdict answers with one of those labels, and nothing else.
 *
 * ```ts
 * pick("Next action?", { merge: "all green", rerun: "looks flaky", hold: "needs attention" })
 * pick("Next action?", ["merge", "rerun", "hold"])
 * ```
 *
 * Fewer than two options is not a choice; such a question escalates as
 * `open_ended` instead of being sent.
 */
export function pick(question, options) {
    return { type: "choice", question, options };
}
/**
 * Ask where the state sits on an ordered scale (Jev's `score` primitive). The
 * verdict answers with a possibly-fractional index into the levels, and
 * `legend` maps indices back to your words.
 *
 * ```ts
 * rate("How risky?", ["routine", "worth a look", "incident"])
 * ```
 *
 * Fewer than two levels is not a scale; such a question escalates as
 * `open_ended` instead of being sent.
 */
export function rate(question, levels) {
    return { type: "score", question, levels };
}
