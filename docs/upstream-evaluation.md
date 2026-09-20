# Upstream evaluation — 2026-09-20

Jev Kit remains the common entry point. This evaluation supports an **experimental
Ego browser integration**, further compaction research, and keeping Foreman off
by default. It does not establish a general coding-agent improvement.

| Component | Experiment | Result | Decision |
|---|---|---|---|
| jev-ultrafast policy + Ego Lite | Same executor/verifier; Jev vs Fable low with up to five actions and inline text | Local: both 6/6, median 6.35 s vs 7.30 s. Public initially Jev 3/4 vs batch 4/4; after target-disappearance fix both 4/4, 5.42 s vs 7.23 s | Keep optional browser adapter; familiar-task diagnostics, broader reliability untested |
| fast-jev-compaction | 6 synthetic transcripts × 2; then native Claude continuation on first repeat | All required facts retained in 12/12; median serialized-size reduction 31.6%; compaction 0.288 s. Continuation: full 6/6, Jev 6/6, equal-size recency 1/6 | Candidate for preserving context under size pressure; no demonstrated speedup |
| Foreman | Synthetic assessment, then real Codex App Server repair workers | Synthetic 16/16 allowed actions; real follow-up external tests both arms 2/2, but Foreman finished only 1/2 and took longer | Keep isolated; do not install as default supervisor |

## Browser integration and evidence

The shipped experimental command is `./jev browser --input job.json`; it is not
a sixth MCP tool or an automatic host hook. It imports the pinned upstream Python
policy and DOM reader, replacing Chrome/Browser Harness execution with Ego Page
methods. The main agent delegates a complete bounded job. Jev decides inside the
loop; a text helper is invoked only when typing is needed. Current observations
bind executable targets, and a separate check validates completion.

The earlier v4 comparison has three unique authored form tasks, repeated twice, and
two unique public Wikipedia tasks, run once. Timing includes initial navigation,
observation, session/policy setup, all decisions, text generation and verification.
Both arms use the same Ego executor and native Claude text helper. Dependency
installation is excluded. The 44.1% lower local median and 48.0% lower public median
are descriptive results from these tiny samples, not estimates for arbitrary sites.
The v4 LLM comparator selects one action per round. The stronger v5/v6 follow-up
now batches up to five observed operations and generates field text inline.
Against that baseline, the local median advantage is **13.0%**, and the post-fix
public advantage is **25.1%**. This still does not establish an advantage over
arbitrary native Ego JavaScript programs or a full coding-agent loop.

v5 ran 30 attempts (five familiar tasks × two repeats × three strategies). All
18 local attempts passed. Public Jev passed 3/4; both Fable strategies passed 4/4.
Three Jev public attempts discarded a stale decision and recovered successfully.
A separate attempt lost its target between the guard and native click. Its failure is
retained, and its latency must not be treated as a quality-matched speedup. The
executor now discards only a precisely identified zero-match locator failure and
requests a fresh decision. An injected real-browser regression verifies one actual
click after recovery. v6 then reran only public tasks: all 12 attempts passed.
These follow-ups are not untouched holdouts and do not demonstrate improved
decision accuracy. One v6 matched pair was faster with batch Fable.

The CLI now supports cooperative SIGINT/SIGTERM cancellation and checkpoint time
budgets, re-observes before DONE, stops on immediate popup/dialog or uncertain
execution receipts, and records initialization/cleanup failures. These are adapter
reliability improvements; they are not changes to Jev's model or the Ego Lite app.

Earlier attempts are retained. `ego-v1` had a missing Claude executable in Ego's
minimal PATH; `ego-v2` was contaminated by the first embedded script continuing
after its CLI was interrupted. Both comparisons are invalid. A per-page lease
now prevents concurrent Kit executors. `ego-v3` passed all local attempts but
failed all four public attempts because of navigation/DOM synchronization.
`ego-v4` reran all 16 attempts after adding document readiness, post-input rendering
waits and bounded discard/re-observe of stale decisions. It is a post-fix follow-up,
not an untouched holdout. Replaced-node and covered-node live guard checks pass.

No Chrome-versus-Ego speed comparison was made. The original repo's policy runs
unmodified, but this is an **Ego integration test**, not a reproduction of its
Google Flights recording or its original Browser Harness executor.

[Browser study and raw numeric receipts](../benchmarks/ego-upstream/README.md) ·
[Adapter setup and limits](../integrations/ego-browser/README.md)

## Compaction interpretation

The original library is used with its default keep threshold, six recent pinned
messages and 300-character truncation. The fixtures put required values in old
tool results. Half provide meaningful tool-input labels; half use opaque labels.
User/assistant prose remains unchanged. The recency comparator preserves the same
pinned messages and removes oldest complete tool pairs until it fits Jev's achieved
serialized-size budget. It does not see gold answers.

Jev's decision state omits result bodies. Consequently, preservation can depend on
retaining broad groups of opaque results. Reduction ranges from 0% to 56.2%; it is
not content-aware proof that every discarded result was irrelevant. Byte reduction
is not tokenizer-measured context reduction. All tested call/result pairs stay valid.

The continuation probe asks native Claude to recover three exact values; it is
not a code-repair task. Including compaction, median latency is **2.87 s**, versus
**2.66 s** with the full transcript. Claude CLI cost estimates total $2.00 versus
$2.81 across six requests, excluding Jev billing. These are host estimates, not
provider invoices or a demonstrated total-cost saving.

The native Claude `/compact` implementation and function-hook lifecycle were not
compared. No global Claude plugin/settings changes were made. A long-session,
native-compaction continuation comparison remains the next acceptance gate.

[Compaction reproduction and receipts](../benchmarks/upstream-compaction/README.md)

## Foreman interpretation

The first screen feeds eight authored frozen observations to the actual upstream
Jev adapter and deterministic policy, twice each. All 16 actions fit the predefined
allowed sets, compared with 8/16 for a weak exit-status-only rule. Median assessment
latency is 0.280 s. This establishes a working semantic assessment component, not
an agent improvement.

The real-worker comparison uses **Codex CLI 0.155.0, gpt-6-astra, xhigh**, verified
from these workers' local session metadata. Both arms use upstream's App Server
worker and coding mission in clean fixture repositories. External checks are
stored outside the worker checkout. Two authored Python repair tasks are tested:
strict integer parsing and case-insensitive header lookup with duplicate pairs.

An initial run exhausted a 12-assessment budget; its full results remain available.
A separately recorded follow-up allows 40 assessments while retaining the same
thresholds, 90-second worker timeout, 180-second overall timeout and two-worker cap.

| Follow-up task | Direct Codex | Foreman + Jev | Independent checks |
|---|---:|---:|---|
| Integer parser | 44.74 s, completed | 92.45 s, escalated at worker cap | Both pass |
| Header lookup | 38.80 s, completed | 65.18 s, finished | Both pass |

Foreman used two coding workers per task, versus one for direct Codex, and 29 Jev
assessments total. It did not improve external correctness, and one already passing
repository was not accepted as complete by the supervisor. These two tasks do not
rule out benefits on long, stalled jobs, but they do not justify a default integration.
Jev's assessment wrapper does not retain resolved-model/usage metadata; no Foreman
Jev cost claim is made. Numeric Codex worker usage is included when available.

[Foreman reproduction and receipts](../benchmarks/upstream-foreman/README.md)

## Provenance and installation status

| Repo | Pinned SHA | Offline tests |
|---|---|---:|
| [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) | `1231850a0bf1a0c0341fe408ef1668dbbfdfac46` | 31 passed |
| [tamaratran/fast-jev-compaction](https://github.com/tamaratran/fast-jev-compaction) | `e3f262a7f4d42bd8dd32ced30d26176f7cb545b0` | 29 passed |
| [thruwire/foreman](https://github.com/thruwire/foreman) | `3de1556a59b7a7e14daa1f89b2fc49080bbb8cce` | 80 passed |

All three were installed only in isolated experiment checkouts. The existing
managed Jev Kit installation and daily host settings were not updated. The official
[TypeSafe Skill](https://github.com/typesafe-ai/skills) remains a design aid, not a
runtime with an independent speedup benchmark. No extra Skill/plugin was installed.
Private provider transcripts stay outside the public tree; exported reports use
allowlisted numeric receipts and synthetic fixture data.
