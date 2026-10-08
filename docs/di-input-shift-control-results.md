# Frozen Morgan model: known input-shift control

2026-10-08. **PASS, independently verified with zero unresolved mismatches.**
The procedure, code, tests and review were committed at `885907f` before array or
model access. The original CPU environment completed the run in 19.60 seconds,
with all 60 cases, five screens and returned prediction archives retained.
No run exception occurred.

Both mandatory controls passed before shifted inference:

- All 108 original scalar scores reproduced within the unchanged absolute 1e-8
  tolerance, with complete PASS saved before loading the model.
- All twelve unshifted predictions reproduced the original float32 bytes exactly.
  All 36 network scalar scores matched their original archive within absolute 1e-8.
  The complete prediction replay and passing zero screen were saved before any
  shifted call. Zero predictions and scores were reused.

Verified results (rounded percentages):

| Known input shift (samples) | Role | Median improvement over better simple arm | Strict wins | Screen |
| --- | --- | ---: | ---: | --- |
| -3 | Required robustness | 57.80% | 12/12 | PASS |
| -2 | Required robustness | 57.81% | 12/12 | PASS |
| 0 | Replayed prerequisite | 57.83% | 12/12 | PASS |
| +2 | Required robustness | 57.86% | 12/12 | PASS |
| +3 | Required robustness | 57.87% | 12/12 | PASS |

Both group medians are positive at each offset. All four nonzero offsets must pass
the original stronger gate; there is no selected offset or new threshold.
Fresh-context Noether independently implemented preprocessing, Torch architecture,
reconstruction, shifts, scoring and gates. All sixty derivations were persisted
before opening primary numerical outputs. All twelve original predictions and
all 120 primary raw/corrected prediction member-byte checks match exactly.
The final comparison has **21,246 checks and zero failures**. New primary numerical
discrepancy is **zero**; original replay maximum is 8.05e-12 and inherited metadata
maximum is 8.26e-12, below the unchanged absolute 1e-8 tolerance. All 63 pinned
dependencies, 48 original artifacts, checkpoint and 67 primary artifacts are stable.

The initial comparison recorded 53,958 checks and 36 schema-only mismatches: the
verifier omitted the required empty `nonfinite_diagnostic_fields` lists on replay
records. Those failures remain in the record. Adding the source-defined metadata
field resolved them without repeating inference/scoring, changing numerical
derivations, selecting cases or relaxing tolerance.

## Evidence

- [Frozen procedure](di-input-shift-control-plan.md) and
  [independent design/code review](research/di-input-shift-control-review-2026-10-08.md).
- [Full scores, paired changes and gates](di-input-shift-control.json).
- [108-scalar replay](di-input-shift-control-baseline-replay.json).
- [Twelve prediction-byte and 36-score replay](di-input-shift-control-baseline-inference-replay.json).
- [Source, model and environment provenance](di-input-shift-control-provenance.json).
- [Input artifact and waveform identities](di-input-shift-control-inputs.json).
- Original output: `tmp/di-input-shift-control-20261008/`; log:
  `tmp/di-input-shift-control-20261008.log`. Progress has twelve baseline-stage
  records followed by sixty case-stage records. All returned raw/corrected
  prediction NPZs are retained locally.

- [Independent verification report](research/di-input-shift-control-verification-2026-10-08.md),
  [implementation](research/di-input-shift-control-independent-2026-10-08.py),
  [full numerical/check record](di-input-shift-control-verification.json.gz) and
  [archive identities](di-input-shift-control-verification-archive.json).
- The full original JSON and its lossless compressed copy remain locally in
  `tmp/di-input-shift-verification.json` and `.full.json.gz`. Only embedded prediction
  payloads are replaced with pointers and content hashes in the tracked record;
  all numeric derivations, checks and initial failures are retained. This keeps
  duplicated audio bytes out of Git. The original report SHA256 is
  `51c0a420e4819f525c8e9d3d2eb022089f1450d9ff7c24a206d6db4acdd1fc41`.

## Interpretation limits

This shifts the full six-second raw input before frozen-model prediction, then
reverses only the known imposed shift on the prediction. The original 52-sample
renderer latency remains. Target/raw DI and wet/flatref competitors are fixed.
No delay is fitted to the target. Finite padding, window normalization and context
effects are part of this test; it cannot isolate an encoder-stride cause.

Twelve reused performances from one player/guitar and one clean Morgan chain are
dependent development cases. This does not establish native transfer, native
failure causation, preset ranking, song accuracy or product readiness. Original
full-render, plugin-parameter transcript and physical-latency evidence limits
remain. No average, catalog, raw/native/reserved audio, alternate checkpoint,
rendering or training was accessed. Guard/revision/review and saved timing evidence
are not an independent retrospective audit of runtime access.

This study is closed. The clean-chain advantage survives the declared small
input shifts, narrowing this particular timing concern. Move next to a bounded
processing-diversity control under a separate reviewed declaration. Closed
native/reserved procedures stay closed; no threshold changes, panel rescue or
longer training follow from this result.

The independent implementation shares NumPy/SciPy/Torch libraries and CPU kernels
with the primary. The verifier did not retrospectively observe primary runtime
calls; source, saved artifacts and timestamps support the replay ordering.

Pedroza et al., Guitar-TECHS, CC BY4.0, https://zenodo.org/records/14963133.
