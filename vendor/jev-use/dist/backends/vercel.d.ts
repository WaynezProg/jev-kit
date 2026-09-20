/**
 * Vercel AI Gateway backend. A genuinely different dialect:
 * POST https://ai-gateway.vercel.sh/v4/ai/evaluation-model with the model
 * in a HEADER (ai-model-id), `noul` renamed to `boolean` (answer field
 * `probability`), camelCase usage, and NO confidence/legend passthrough —
 * confidence is reconstructed from the distribution margin downstream.
 * Wire shapes verified against @ai-sdk/gateway dist source (2026-09).
 */
import { type HttpOptions } from "./http.js";
import { type BackendRequest, type BackendResponse, type JevBackend } from "./types.js";
export declare const VERCEL_BASE_URL = "https://ai-gateway.vercel.sh";
export declare const VERCEL_DEFAULT_MODEL = "typesafe-ai/jev";
/** How to reach the Vercel AI Gateway. */
export interface VercelOptions extends HttpOptions {
    apiKey: string;
    /** Override the gateway origin (proxy, test server). */
    baseUrl?: string;
    /** Model used when a call names none. Default "typesafe-ai/jev". */
    defaultModel?: string;
}
export declare class VercelBackend implements JevBackend {
    private readonly options;
    readonly name = "vercel";
    /**
     * The gateway returns no confidence field, so confidence here is the
     * distribution margin — live probes (bench/RESULTS.md) show decisive
     * answers landing at margins 0.5–1.0 where a vendor head reads ~0.9, so
     * the vendor-calibrated 0.75 default over-escalates. 0.4 = the winner
     * leads the runner-up by 40 points.
     */
    readonly defaultConfidenceThreshold = 0.4;
    constructor(options: VercelOptions);
    judge(request: BackendRequest): Promise<BackendResponse>;
}
