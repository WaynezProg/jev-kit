# Original Foreman evaluation

Pinned upstream: `3de1556a59b7a7e14daa1f89b2fc49080bbb8cce` (MIT).
Run `uv sync --extra dev` in its isolated checkout. Upstream tests: 80 passed.
Then run these scripts with that environment's Python, using fresh output folders:

```sh
/absolute/foreman/.venv/bin/python benchmarks/upstream-foreman/run.py /absolute/new-replay
/absolute/foreman/.venv/bin/python benchmarks/upstream-foreman/native.py /absolute/new-native
```

These make paid Jev calls; the second starts actual signed-in Codex App Server
workers in freshly created fixture repositories. It uses the user's configured
Codex model; record actual session metadata when reproducing. No global settings change.

The component screen has eight authored observations repeated twice: 16/16 allowed
policy actions, compared with 8/16 for a weak test-exit/status-only rule. This is
neither a calibrated accuracy estimate nor a coding benchmark. Median assessment
0.280 s; requested model `jev-latest`, resolved model not retained by upstream wrapper.

Actual-worker follow-up: gpt-6-astra xhigh, two tasks × two arms, counterbalanced
arm order, one run per arm/task. Both arms use the same App Server implementation
and coding mission; external tests sit outside each worker checkout. Both pass
2/2 external checks. Direct takes 44.74/38.80 s; Foreman takes 92.45/65.18 s and
finishes only one task, escalating the other after two workers despite passing code.

The initial 12-assessment-budget run is preserved in `native-v1.json`. The separately
recorded follow-up increases only that budget to 40; thresholds and worker/time caps
are unchanged. The checked-in runner reproduces the follow-up. Neither run supports
default supervision. Two small tasks do not assess long-running or weak-model recovery.

[Summary](results/summary.json) · [Replay](results/replay.json) ·
[Initial real runs](results/native-v1.json) · [Budget follow-up](results/native-v2.json)
