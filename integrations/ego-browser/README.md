# Experimental Ego Lite adapter

Run `./jev browser --input job.json` through Jev Kit. The five existing MCP tools
are unchanged. This is an explicit browser job, not an automatically enabled hook.
It requires the `ego-browser` CLI and a running Ego Lite.

The adapter imports the **unmodified, pinned** `jev-ultrafast` policy into a
persistent Python process. Its DOM snapshot and operation/target fan-out stay
upstream; Ego Page methods replace the Browser Harness/Chrome executor. It does
not connect to Chrome, select a profile, or modify Ego Lite itself.

```text
agent -> Jev Kit -> Ego DOM snapshot -> Jev operation + target
                        ^                       |
                        |         identity/freshness/occlusion check
                        |                       |
                        +---- Ego click / fill / selectOption
                        |
                  independent outcome check
```

## Optional runtime setup

Use Python 3.12+ and `uv`, with a separate checkout. Keep credentials outside it.

```sh
git clone https://github.com/browser-use/jev-ultrafast.git /absolute/jev-ultrafast
git -C /absolute/jev-ultrafast checkout --detach 1231850a0bf1a0c0341fe408ef1668dbbfdfac46
cd /absolute/jev-ultrafast
uv sync --frozen
```

The adapter rejects another revision or modified upstream policy/snapshot source.
Original MIT attribution stays in that checkout; adapted execution guards are
also attributed in [UPSTREAM-LICENSE](UPSTREAM-LICENSE).

`TYPESAFE_API_KEY_FILE` defaults to the existing private Jev Kit key-file location.
For generated typing, configure upstream's `TEXT_MODEL_API_KEY`,
`TEXT_MODEL_BASE_URL`, and `TEXT_MODEL` in Ego's execution environment. A missing
text helper stops the job. Alternatively set `claude_path` in the job to an absolute
Claude CLI path: this uses the signed-in native Fable 5.1 low session solely to
generate field text, with tools/MCP/hooks disabled. No additional text API key is
needed. The executor does not invent field values.

## Job example

```json
{
  "upstream": "/absolute/jev-ultrafast",
  "python": "/absolute/jev-ultrafast/.venv/bin/python",
  "url": "https://example.com",
  "goal": "Read the Example Domain page and stop once its heading is visible.",
  "origins": ["https://example.com"],
  "expect_url": "https://example.com/",
  "expect_text": "Example Domain",
  "max_steps": 8,
  "max_seconds": 180,
  "output": "/absolute/new-browser-receipt.json"
}
```

```sh
./jev browser --input job.json --validate-only
./jev browser --input job.json
```

Validation checks schema, pinned checkout and Python path without network/browser
calls. `expect_url` is exact; `expect_text` must occur in body text. If both are
supplied, both must match. These checks verify only their explicit assertions,
not general task completion. Jev `DONE` alone is never reported as verified.

Omit `space_id` to create a TaskSpace. A verified newly created space is finished
once, keeping no pages. A supplied `space_id` reuses its `p1` (or the supplied
`page`, such as `p2`), **navigates to the
given URL**, and leaves lifecycle ownership to the caller. It does not resume the
current page. Failure receipts identify the space to inspect; do not create another
space to evade a blocked or user-controlled page.

The CLI and programmatic runner acquire an exclusive local per-page lease. Inspect stale locks before
removing them. Frontend exit alone is not proof that embedded execution has stopped.

The CLI writes a private cancellation flag on `SIGINT`/`SIGTERM`. The embedded
loop checks it before each model request, after model responses and before every
input. `cancelled` in the terminal receipt confirms that no later input will be
dispatched by that run. A pending model/browser request must still return;
`max_seconds` (default 180, maximum 600) is likewise a **checkpoint budget**, not
a hard kill of in-flight work. If the frontend exits without a terminal receipt,
it reports `completion_unconfirmed` and preserves the `stop_file`. Do not start
another executor until the prior run has ended and its lease is released.

Runtime initialization and cleanup failures also produce receipts. Cleanup errors prevent
a job from being marked verified; `outcome_verified` retains any earlier successful
application check. Receipts contain action kind, timing, model usage and sanitized
Ego dispatch information. They omit explicit field text, prompts and raw dialog
content, but retain the final URL and runtime error message. Keep job receipts
private; URLs can include search terms.

## Tested boundary

- Top-document HTML/ARIA controls; native SELECT uses `selectOption`, custom
  comboboxes depend on supported fill/click controls.
- Only current observed IDs can execute. Disconnected, disabled, stale and
  covered targets cannot execute. At most three stale or pre-dispatch target
  disappearance decisions are discarded in total;
  the next choice uses a fresh observation. Text helpers cannot supply selectors.
- A click whose exact owned locator disappears between the guard and native
  dispatch is also discarded and re-observed. Only Ego's explicit zero-match
  locator timeout qualifies. Generic timeouts and uncertain input are not retried;
  the old action is never replayed automatically.
- Bounded waits observe URL, text and form-state changes; not general app readiness.
- Ordinary anchor destinations are checked before clicking. Scripted navigation
  is detected at the next observation. `origins` is an execution scope check,
  not network isolation.
- DONE always obtains a fresh observation, checks its origin, then runs the
  independent verifier. Safe error paths report the current URL.
- Immediately observed popups stop the loop with `popup_requires_handoff` and
  page labels in the receipt. Dialogs stop with `dialog_requires_user`; uncertain
  execution stops without another DOM operation. The caller handles TaskSpace
  handoff; the adapter never automatically accepts a dialog or adopts a popup.
- Frames, shadow DOM, canvas, uploads, popup continuation, login and transaction
  approval workflows are outside the tested scope. Delayed popups are not covered
  by immediate dispatch receipts.
- Observation temporarily tags controls with random `data-jev-kit-target` values
  and cleans its own attributes on normal completion and safe error paths.
- The sequential policy bridge stops on timeout. Upstream HTTP retry behavior stays.

The programmatic runner also accepts a bounded plan of up to five observed action
IDs for caller-supplied control policies. Before each subsequent action it checks the
original document, node identity and unchanged target semantics against a fresh
observation. Own form edits can proceed; navigation, a replaced target or changed
meaning discards the remaining plan. This does not make Jev a multi-action planner,
and the CLI continues to use the upstream one-decision-at-a-time policy.

This adapter remains experimental. See the [main README](../../README.md) for the
shared judgment tools and host installation.
