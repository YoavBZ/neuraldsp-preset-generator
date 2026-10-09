# Development activity-proxy diagnostic: independently verified

> **Review 2026-10-09** ([codex-continuation-review.md](codex-continuation-review.md)): the outcome is mislabelled. The reference-proxy fallback rescues the refused part and changes no control pick; adopt it. The rule 'at least 3 controls improved' could not sensibly be met by a refusal fix.


Computed 2026-10-08 after the independently reviewed declaration and implementation
were committed at `8739009`. Independent recomputation agrees on all 42,054 compared
scalar fields with zero discrepancies. All 22 fresh audio spot checks and 600
selected-source storage checks agree. These are development findings, not a
replacement reserved confirmation.

Evidence: [complete output](EVIDENCE-OUTSIDE-GIT.md) and
[independent verification](EVIDENCE-OUTSIDE-GIT.md).

## Execution

- 12 fixed development parts from 11 bands; SW50R, 45 candidates, both band sets.
- Original A scores reproduced before either alternative was evaluated: all 1,080
  candidate comparisons match within the declared absolute tolerance and all picks
  match exactly, including the target's missing choice. Maximum absolute numerical
  difference is 3.55e-15.
- Completed successfully, 07:36:58–07:40:13 UTC. Log:
  `tmp/set3-mask-diagnostic-20261008.log`; output:
  `tmp/set3-mask-diagnostic-20261008.json`.
- Existing audio only; no plugin invocation, rendering, model inference or training.
  No reserved scores or audio were opened.

## Findings

Both known-DI and isolated-reference proxies remove the target refusal under both
band sets. The original chooser refuses all 45 candidates because 51% of its scored
frames are pauses, above its fixed 50% limit. Neither alternative refuses a target
candidate; both choose `Artists/Richard Henshall/Tremolo Jam`. Its saved B distances
are 4.112928 (recording) and 4.049345 (union), versus 19.530161/17.545392 for the
leave-band-out constant and 7.111085/6.330522 for template+R. This is one case, not
an estimate of a general gain.

All 11 control parts keep exactly the same preset under both proxies and both band
sets: zero B improvements, zero losses, 11 ties. All original/reference control B
evaluations and rescued target B evaluations are raw-valid. There are no new missing
selections, but the predetermined requirement of at least three improved controls
fails in both band sets. The isolated-reference heuristic therefore does NOT qualify
for an all-development expansion. Do not tune it or expand the panel after this result.

The rescue attributes this refusal to the activity-proxy argument and its downstream
effects within the primitive. It does not demonstrate that the rebuilt waveform is
accurate or that better activity detection solves the general ranking problem. The
unchanged control picks also do not show that all their numerical scores are unchanged.
Transfer of the isolated-reference heuristic to mixes or separated stems is untested.

## Next

Close this particular proxy experiment. Keep the
existing product behavior and frozen network unchanged. A separately declared
[rank-calibration experiment](set3-rank-calibration-plan.md) asks whether learning
when to trust song-specific scores versus a preset's past performance improves
choice. It uses existing development scores only, with nested band exclusion and a
B-trained prior-only comparator, before considering new waveform training.

The spent reserved split remains unavailable for training/tuning or another test.
Any changed method still needs heavier-tone listening and fresh reserved confirmation.
