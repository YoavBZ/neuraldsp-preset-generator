# Fixed Morgan renders: learned DI versus simple tone correction

**Declared: 2026-10-08, before new computation.**

Fresh independent design/code review approved the exact procedure and implementation:
[review and snapshot hashes](research/di-morgan-flatref-review-2026-10-08.md).
188 synthetic tests pass; two optional Torch tests skip in the helper environment.
Only declaration metadata and this review link changed after approval. Commit this
declaration before computing the diagnostic.

## Question and prerequisite

The [known-DI Morgan control](di-morgan-control-results.md), declared at `a5b9605`,
passes its original standalone gate: 72.18% median improvement over processed
audio directly, all twelve wins. Fresh independent replay confirms 767 checks,
byte-identical predictions and zero mismatches. That baseline does not establish
an advantage over simple tone correction. Compare the existing `flatref` stand-in
on the **same twelve fixed saved renders/predictions**, without new rendering,
inference, training, tuning or native microphone data.

The previous model/target/preprocessing/canonical-MR-STFT choices remain fixed.
All twelve original P2 performances are included. No subset/crop/checkpoint/amp
selection. This is another bounded development diagnostic, not reserved validation.

## Inputs and frozen execution

`learn/di_morgan_flatref.py --out tmp/di-morgan-flatref-20261008` through the
approved project helper. Require the committed declaration and all inherited
source/dependency pins, including Swift helper, plus this code/test/declaration,
archived original control result and independent verification, and original
prepare/render reports. Require successful original independent verification and
byte-identical archived result/reports. Check old infer source pins against the
unchanged current source set. No use of results to alter thresholds or features.

Freeze exactly **36** input array files by bytes in
`docs/di-morgan-flatref-inputs.sha256`: twelve each from original `prepare`,
`render`, `infer`. Paths must exactly match the original slugs under
`tmp/di-morgan-control-20261008/`; no additions, duplicates or escapes. These
hashes are declaration-time artifact identity, not new scoring. Frozen average
path/hash remains in the original manifest; verify before loading it. No model
checkpoint, raw audio or catalog access is needed. Reuse exact saved Torch32 window
coefficients, checked by the approved loader. Actual helper NumPy metric environment
already passed its declared preflight; same code/coefficients required.

1. **Complete original-score replay first on all twelve:** read raw score DI and
   canonical target from `prepare`; latency-corrected processed audio from
   `render.baseline`; frozen predictions from `infer.prediction`. Recompute each
   input/network primary, waveform L1 and raw-DI low-band score, and require all
   **72 scalar scores** to match the archived result at absolute ≤1e-8. Save the
   complete replay report before calculating any experimental stand-in. Any replay
   failure stops without flatref scoring.
2. For each saved six-second latency-corrected processed input, compute
   **`P.canonical_target(wet, frozen_average)`**, the existing training-free
   `flatref` definition: its own smoothed spectrum, mean dB removed, frozen average
   minus that spectrum clamped ±15 dB, six-second FFT interpolation/EQ. No use of
   the target DI in constructing the stand-in, no new filter or gain fitting.
3. Score the stand-in against the **same** saved canonical DI target: center three
   seconds, independent standard deviation normalization to0.1, unchanged exact
   Torch32-window five-resolution MR-STFT. Report waveform L1 and raw-DI low-band
   scores as diagnostics. Save every stand-in waveform and individual score.

Outputs exclusively created under project `tmp`, including source/input hashes,
versions, replay, incremental progress, all scores and failure evidence. Cooperative
15-minute budget; no claim of hard interruption inside a library. Log
`tmp/di-morgan-flatref-20261008.log`. Preserve prior artifacts; no rerender/repeat
selection or model replay in this diagnostic.

## Fixed gate and interpretation

For each take use **the better of the two simple baselines**:
`simple = min(wet_primary, flatref_primary)`, then
`improvement = (simple-net_primary)/simple`. This avoids making the learned model
look better when the new simple correction itself fails. Require finite nonnegative
losses, positive baseline denominators, correct identities/coverage/raw QC/oracles
for all twelve; otherwise inconclusive.

The learned model passes this stronger screen only with **median improvement≥10%**,
**≥9/12 strict wins**, and **positive medians in both six-chord and six-scale groups**.
These are the original native-primary engineering criteria, now explicitly applied
to this separate known-DI Morgan comparison. Keep eight `math.ulp(0.1)` allowance
only at the inclusive10% boundary; strict wins/group positivity remain strict.
Do not import the original standalone Morgan control's weaker median-only gate
without these additional criteria. Report all twelve simple-baseline choices/losses.

- Pass: supports learned improvement over these two simple stand-ins on one fixed
  Morgan chain. It only permits declaring another bounded development diagnostic.
- Completed valid failure: do not treat the earlier72% control as evidence that a
  neural model is necessary here. Investigate the specific model/target/baseline
  weakness without tuning this panel or training longer by default.
- Failed replay/coverage/input checks: inconclusive; preserve and review failure.

No outcome establishes native transfer, multi-guitar/driven/song preset ranking,
shipping readiness, or justification for long training. Carry forward original
render-evidence limits (unsaved full wet output for eleven takes; no separate
plugin-command transcript). No fresh plugin-state claim is introduced.

Meaningful synthetic tests, fresh independent code/design review and commit before
new computation. Fresh independent result verification rederives stand-ins/scores/
coverage/gates from frozen artifacts before decisions. Update results/roadmap/index/
DI plan/learn README; no P1/P3/reserved data or external downloads.

Pedroza et al., Guitar-TECHS, CC BY4.0, https://zenodo.org/records/14963133.
