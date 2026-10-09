# Separate Morgan startup readiness

> **Review 2026-10-09** ([codex-continuation-review.md](codex-continuation-review.md)): it duplicates the working renderer (match/renderer_au.py); drop it. The lesson is only: run AU work outside Codex's sandbox.


2026-10-09. **READY for the declared instance/version/process-exit check. Closed.**

The corrected source, tests, fresh independent approval and declaration were
committed at `9aab649` before the single host execution. The original checker
process, session 57308, exited **0**. It compiled the dedicated probe once,
instantiated Morgan once, received version **1.1.1**, sent only `quit:true` and
reaped the child with exit **0**, without a cleanup error.

Compiler stdout/stderr, native stderr and checker stdout/stderr are empty.
The exact raw startup reply matches the saved ready/version object. All six
source/review/plan pins and the compiled binary identity match after execution.
No pending, provisional or failure record exists. Main inspected this complete
evidence before accepting READY; a JSON disposition alone was not the decision.

## Scope and evidence

- [Committed procedure](morgan-au-startup-plan.md) and
  [fresh independent review](research/morgan-au-startup-review-2026-10-09.md).
- [Exact metadata and logs](morgan-au-startup-evidence.json.gz), including compiler
  command/diagnostics, launch command, raw reply, child cleanup, source provenance,
  original checker exit record and main evidence review.
- [Lossless archive identities](morgan-au-startup-evidence-archive.json).
- [First blocked review](research/morgan-au-startup-blocked-review-2026-10-09.md)
  caught excess startup work and discarded compiler diagnostics. The
  [second](research/morgan-au-startup-blocked-review-v2-2026-10-09.md) caught a
  potentially deadlocking main-thread wait. Both remain preserved. Corrections
  passed 24 synthetic tests and fresh source review before any actual probe.

Local output is `tmp/morgan-au-startup-20261009/`, with original checker log
`tmp/morgan-au-startup-execution-20261009.log`. The binary and local Swift module
cache remain outside Git. No audio, preset, parameter, render, model or dataset
command ran. Native instantiation may internally initialize plugin state.

## Limits and next work

This establishes one instance/version/direct-process-exit observation in the
approved host execution context. It does not establish DSP rendering, destructor
completion, plugin service cleanup, model accuracy or song matching. The parent
checks deadlines, but there is no hard bound on all compiler descendants or
filesystem operations. The probe reports registration version, not live parameters.

The earlier [processing attempt](di-morgan-processing-control-results.md) stays
**VERIFIED INCONCLUSIVE and closed**. Different host code and execution context
mean this result does not isolate its failure's cause or permit a retry.

Next assess whether existing development metadata can support the
[direct preset-ranker proposal](research/direct-preset-ranker-proposal-2026-10-09.md):
exact excerpt identity, complete guitar targets, rights, grouping and baseline
availability. The proposed equal-weight multi-guitar target is not adopted.
No model/feature/score computation is declared by this readiness result. A new
experiment still needs meaningful controls, fresh review and a committed procedure.
The spent reserved confirmation and failed native pilot remain closed.
