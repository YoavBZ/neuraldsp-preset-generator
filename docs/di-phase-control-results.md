# Frozen Morgan model: fixed periodic phase challenge

2026-10-09. **Independently verified PASS.**
The reviewed source, tests, scientific body and approval were committed at
`03b8c00` before actual audio/model access. The original CPU environment completed
the panel in 23.36 seconds, exit 0; all twelve cases and 48 stage progress records
are retained. There was no run exception.

Before any phase prediction, the original 108 scalar scores replayed within
absolute 1e-8, all twelve original predictions reproduced float32 bytes exactly,
all 36 original network scores matched their archive, and all twelve independent
construction checks passed. Each complete PASS barrier was saved first.

The independently recomputed screen passes: median improvement over the better transformed
simple arm is **57.56%**, with **12/12 strict wins**. Chord and scale group medians
are positive. A fresh verifier agrees on all 15,976 recorded checks, with zero failures.
The phase test is closed. It supports recovery under this one controlled change;
it does not establish accuracy on real songs.

## Procedure

One fixed periodic six-second phase transform, a=-0.9, changes waveform phase
while preserving full-window frequency magnitudes in ideal arithmetic. The model
receives the transformed raw input; both simple competitors receive the same
transform. Target/raw DI stay fixed. There is no fitted delay/gain or inverse
correction of the model prediction. The inverse construction oracle uses a
separate time-domain algorithm. Scoring, thresholds and original model are frozen.

## Evidence

- [Frozen procedure](di-phase-control-plan.md) and
  [fresh independent approval](research/di-phase-control-review-2026-10-08.md).
- [Scores, changes and screen](di-phase-control.json).
- [Original108 replay](di-phase-control-baseline-replay.json),
  [durable attempt snapshots](di-phase-control-replay-attempts.json), and
  [original12 prediction-byte/direct36-score replay](di-phase-control-baseline-inference-replay.json).
- [Construction controls and coefficient identities](di-phase-control-construction-controls.json).
- [Provenance](di-phase-control-provenance.json) and [input identities](di-phase-control-inputs.json).
- The two blocked reviews remain preserved with their repairs:
  [initial](research/di-phase-control-blocked-review-2026-10-09.md),
  [second](research/di-phase-control-blocked-rereview-2026-10-09.md).
- Full local output is `tmp/di-phase-control-20261008/`, with exclusive log
  `tmp/di-phase-control-20261008.log`. Original baseline, coefficient, construction
  and phase NPZs are retained locally with file/member hashes; no waveform bytes
  are embedded in the JSON or added to Git.

The fresh verifier independently implemented the architecture, preprocessing,
phase/inverse checks, scoring and gates. All 37 independent NPZs and complete
numerical derivations were saved and read back before primary results were opened.
Original predictions and all 145 exact member comparisons agree byte for byte;
primary score discrepancy is zero. Independent inverse algorithms differ by at
most 9.99e-16 in absolute samples. The saved primary inverse residuals also pass
the unchanged 1e-12 and 1e-6 construction bounds.

See the [independent report](di-phase-control-verification.md),
[lossless full comparisons](di-phase-control-verification.json.gz),
[lossless independent derivation](di-phase-control-independent-derivation.json.gz),
[read barrier](di-phase-control-independent-read-barrier.json),
[transcript](di-phase-control-independent-transcript.jsonl),
[final verification source](research/di-phase-control-independent.py),
[original blind derivation source](research/di-phase-control-independent-derivation.py),
and [archive identities](di-phase-control-verification-archive.json).
No inference or scoring was repeated when comparison/reporting was added.
The 15,976 checks include metadata and stability comparisons; they are not
15,976 independent musical examples. Prior studies' check counts are not added.

## Next development step

Timing and this single phase change preserve the known clean-chain advantage.
Next prepare a small, separately reviewed test of actual Morgan processing
variation. Retain full renders and plugin commands; replay the clean control
first and compare against an appropriate simple baseline for each new chain.
Declare and commit the design before new audio/numerical access. No long training
is justified yet. The stopped native screen and spent final test remain closed.

## Limits

This is one artificial periodic transform of twelve dependent performances from
one player/guitar and one clean Morgan chain. It is not a causal cabinet, a broad
processing panel, native transfer, preset selection, real-song accuracy or product
validation. Whole-window magnitude conservation does not promise identical
finite-window scores or waveform samples. No augmentation training or physical
failure explanation follows automatically. Original full-render/plugin transcript/
physical-latency limits remain. The verifier shares NumPy/SciPy/Torch and CPU
with the primary implementation. Primary exit status and elapsed time were
reported by the main session, not independently observed. Saved source/review and timing evidence do not
independently observe historical runtime calls. No average, raw/native/reserved
recording, alternate model, plugin rendering or training was accessed.

Attribution: Pedroza et al., Guitar-TECHS, CC BY4.0,
https://zenodo.org/records/14963133.
