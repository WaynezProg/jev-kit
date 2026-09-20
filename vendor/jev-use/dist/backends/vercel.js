/**
 * Vercel AI Gateway backend. A genuinely different dialect:
 * POST https://ai-gateway.vercel.sh/v4/ai/evaluation-model with the model
 * in a HEADER (ai-model-id), `noul` renamed to `boolean` (answer field
 * `probability`), camelCase usage, and NO confidence/legend passthrough —
 * confidence is reconstructed from the distribution margin downstream.
 * Wire shapes verified against @ai-sdk/gateway dist source (2026-09).
 */
import { optionEntries } from "../protocol.js";
import { postJson } from "./http.js";
import { BackendError, } from "./types.js";
export const VERCEL_BASE_URL = "https://ai-gateway.vercel.sh";
export const VERCEL_DEFAULT_MODEL = "typesafe-ai/jev";
function toGatewayQuestion(question) {
    switch (question.type) {
        case "noul":
            return {
                type: "boolean",
                instructions: question.question,
                ...(question.criteria ? { criteria: question.criteria } : {}),
            };
        case "choice":
            return {
                type: "choice",
                instructions: question.question,
                criteria: Object.fromEntries(optionEntries(question.options ?? []).map(([label, meaning]) => [
                    label,
                    meaning || label,
                ])),
            };
        case "score":
            return {
                type: "score",
                instructions: question.question,
                criteria: question.levels ?? [],
            };
    }
}
export class VercelBackend {
    options;
    name = "vercel";
    /**
     * The gateway returns no confidence field, so confidence here is the
     * distribution margin — live probes (bench/RESULTS.md) show decisive
     * answers landing at margins 0.5–1.0 where a vendor head reads ~0.9, so
     * the vendor-calibrated 0.75 default over-escalates. 0.4 = the winner
     * leads the runner-up by 40 points.
     */
    defaultConfidenceThreshold = 0.4;
    constructor(options) {
        this.options = options;
    }
    async judge(request) {
        const model = request.model ?? this.options.defaultModel ?? VERCEL_DEFAULT_MODEL;
        const body = {
            state: request.state,
            questions: Object.fromEntries(request.questions.map((question) => [question.id, toGatewayQuestion(question)])),
        };
        const started = Date.now();
        const response = (await postJson(this.name, `${this.options.baseUrl ?? VERCEL_BASE_URL}/v4/ai/evaluation-model`, {
            Authorization: `Bearer ${this.options.apiKey}`,
            "ai-gateway-protocol-version": "0.0.1",
            "ai-evaluation-model-specification-version": "4",
            "ai-model-id": model,
        }, body, this.options));
        const answers = request.questions.map((question) => {
            const answer = response.answers?.[question.id];
            if (!answer) {
                throw new BackendError(this.name, `response missing answer for question "${question.id}"`);
            }
            switch (question.type) {
                case "noul":
                    if (typeof answer.probability !== "number") {
                        throw new BackendError(this.name, `answer "${question.id}" has no probability`);
                    }
                    return { answer: answer.probability };
                case "choice":
                    if (typeof answer.choice !== "string") {
                        throw new BackendError(this.name, `answer "${question.id}" has no choice`);
                    }
                    return { answer: answer.choice, distribution: answer.probabilities };
                case "score":
                    if (typeof answer.score !== "number") {
                        throw new BackendError(this.name, `answer "${question.id}" has no score`);
                    }
                    return { answer: answer.score, distribution: answer.probabilities };
            }
        });
        return {
            answers,
            model,
            latencyMs: Date.now() - started,
            usage: {
                inputTokens: response.usage?.inputTokens,
                outputTokens: response.usage?.outputTokens,
            },
        };
    }
}
