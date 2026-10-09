# Frozen DI recovery across recording chains: development pilot

**Declared: 2026-10-08, before execution.** Independent design/code review and
meaningful synthetic checks passed; commit this declaration before opening new audio.
This is a diagnostic of the existing checkpoint, not adaptation or another final test.

## Question and limits

The [training audit](research/di-domain-transfer-audit-2026-10-08.md) found Morgan
renders as all audited wet supervision. Does the same frozen model recover a useful
average-balanced DI from an existing real amp recording, when it can recover the
same unseen guitar/performance after a Morgan render?

Use Guitar-TECHS P2 only. This is one player and a clean bass-amp/microphone/room
chain, with several recording offsets. It cannot establish driven-amp transfer,
robustness to separated multi-guitar stems, preset-ranking gains or shipping readiness.
P2 has already been catalogued: it is development material, not a new reserved test.
No fitting of the neural model, checkpoint selection or search for better windows.

## Fixed inputs

- Catalog: `~/ndsp-presets/references/datasets/guitar-techs/P2-catalog.json`.
  Select the first six chord crops sorted by `(take, start_frame)`, then all six scale
  crops in that order. Join exact `(content,take)` to their native DI/micamp source
  paths under `P2-downloads`. Require twelve distinct takes. Commit the explicit
  [path/time manifest](di-domain-pilot-inputs.json) before audio access; do not
  replace rejected takes.
- Model: `~/ndsp-presets/learn/direc/models-set3/fold2.pt`, SHA256
  `16b2b734b49cc1cc2d7e547d96d3bb56208007c9cae0d0e33acb1c2a1cdd042b`.
- Average: `~/ndsp-presets/learn/direc/cache/average-fold2.npy`, SHA256
  `9aa3c3bfefc2bc5ba21394be29876b5ef5e0120ad2f55f0b890e599ec3bee9a8`.
  These identify existing training assets; no final-test audio or score is read.
- Matched render: shipped `samples/Example_Clean_PR12.xml`, rule R applied through
  `research/render_preset_panel.py:preset_edits`.
  The DI's original recording level is retained, with no gain search. This is one
  fixed training-compatible setting, not representative coverage of all Morgan amps.
- Guitar-TECHS authors license all data CC BY 4.0. Retain Pedroza et al. attribution
  and [the release](https://zenodo.org/records/14963133) in every result artifact.
  Native recordings were made by simultaneous splitting, but release offsets must
  be checked. See the audit for primary references and hardware uncertainties.

No P1, P3, reserved songs, held-out scores or newly downloaded data. Fail on a source
path outside the explicit P2 root, duplicate take, missing pair or changed pinned
model/average. Record catalog, source excerpts, preset, code, model and average hashes
and software versions. Hash native excerpts only during execution, after declaration.

## Time separation and preparation

Each catalog crop spans ten seconds. Read bounded source slices at 48 kHz, with
512-sample guards on each side; use the arithmetic channel mean. Never load a whole
source track. Calibration is seconds **0–4**; evaluation input/target is **4–10**.
The center three seconds of that six-second evaluation window, **5.5–8.5**, supply
all scores. The inherited catalog selected crops and estimated lags using the full
ten seconds. This is not an untouched calibration/test partition. The new operative
alignment and FIR fitting use calibration only; inherited metadata is a consistency
check, never a fallback to rescue failed calibration.

Determine native offset on calibration only, using GCC-PHAT restricted to 80–4,000 Hz
and lags within ±512 samples. Positive lag means `wet[n+lag]` matches `DI[n]`.
Require peak sharpness (peak/median absolute correlation over searched lags) >10
for the full calibration interval and both halves. Require the winning absolute
peak to exceed the strongest peak outside its ±8-sample neighborhood by >1.2× in
all three estimates; catalog proximity cannot rescue an ambiguous peak. Also require
absolute band-limited waveform correlation ≥0.5, lag within 16 samples of the catalog,
and the two calibration halves' lags within 8 samples. Fix polarity from the sign of
the calibration correlation. Use the same lag/polarity for every native arm. Never
fit a delay or polarity to a prediction or evaluation target.

Reject nonfinite audio, clipping fraction `abs(x)>=0.999` >0.0001, RMS <1e-5, or
activity <80% of non-overlapping 10-ms frames above −40 dB relative to the loudest
frame RMS. Check calibration and evaluation separately for DI and aligned wet.
Report all rejected takes and exact reasons. A valid complete screen requires all12;
incomplete results cannot pass or justify training.

The canonical target matches `direc.py`: on the six-second raw DI, compute its
smoothed spectrum, remove that spectrum's dB mean, subtract it from the frozen
average, clamp gain to ±15 dB, interpolate and apply by six-second FFT. Compute
`flatref` with the same procedure from the wet recording's own spectrum. The neural
prediction sees only the wet input and frozen weights. Normalize each compared
center-three-second waveform independently by standard deviation to 0.1, matching
training validation; do not infer absolute pickup/input level from this test.

## Arms and cheap controls

1. **Native baselines:** aligned wet as DI; `flatref` from that wet alone.
2. **Frozen native network:** `direc.rebuild`, CPU, no gradient, one six-second input.
   Training's wet input contains the renderer's 52-sample latency, while its DI
   target is unshifted. After calibration alignment/polarity, delay native wet by
   exactly 52 samples (zero-pad its start, truncate its end) for the network only.
   Baselines use aligned wet without this extra delay. There is no fitted output
   correction. The inner scored crop avoids the artificially padded boundary.
3. **Matched Morgan control:** render the same raw DI with the fixed PR12 preset,
   seconds 2–4 as pre-roll and seconds 4–10 retained. Render an extra 52 samples.
   Retain the renderer's latency for network input, matching training; for its wet
   baseline only, remove exactly 52 samples with the extra guard. No delay fitting.
   Compare frozen-network recovery with input-as-DI against the same canonical target.
4. **Metric control:** target against itself must give primary error <1e-6.
5. **Native recoverability control:** a centered 256-tap wet→raw-DI ridge FIR, fitted
   only on calibration, every eighth valid sample. Penalty is 0.001 × mean diagonal
   of the input Gram matrix. Center n uses wet samples `n-128:n+128`, chronological
   order. Trim 512 samples at BOTH calibration ends before computing means or
   fitting any valid centered row; this keeps dependencies inside raw-source 0–4 s
   for every allowed alignment. Remove trimmed calibration input/target means for
   fitting and retain a calibration-only intercept. Evaluation prediction context
   uses only the six-second evaluation wet, reflect-padded by 512 samples per side.
   Refuse nonfinite coefficients or predictions. Apply the fixed filter to evaluation
   wet without fitting anything on evaluation. Compare FIR, wet-as-DI and flatref
   against **raw DI**, after a fourth-order Butterworth 80–4,000 Hz SOS zero-phase
   filter (`padtype=odd`, `padlen=27`) applied to each six-second evaluation waveform
   separately, then center-crop
   and standardization. Filter calibration separately, never across the split.
   This deliberately measures retained
   information, separately from the model's canonical-target task. It is an
   oracle-assisted diagnostic needing the true calibration DI, not a product method.
   Its 5.33-ms support is limited; failure cannot establish irrecoverability.

Run synthetic metric/lag/FIR checks first. Then native QC and recoverability controls;
preserve failures. Only after valid pairing and metric controls, proceed to twelve
matched renders and 24 CPU neural inferences. Use one reused renderer, close it in
`finally`, retain its host logs and a repeatability check on the first render.
The existing backend records roughly −17 dB waveform repeat variation and a 0.23 dB
band-noise floor; sample identity is therefore not required. Compare the first six-
second aligned Morgan baseline with its immediate repeat. Require absolute global
RMS drift ≤1 dB and absolute raw band-power drift ≤1 dB in fixed bands
80–160–320–640–1,280–2,560–4,000 Hz. Use a periodic Hann over six seconds; include only
bands whose FIRST render power is at least 1e-4 of that render's largest declared-band
power. Bands are half-open except the final 4,000-Hz edge is included. No repeat-derived
normalization or fitted delay. Save both waveforms, all
drifts, plugin/build metadata, declared noise floor and the canary outcome. This
engineering stability check does not make reused rendering deterministic or measure
uncertainty in the final screen's improvement estimate. Use a cooperative fifteen-
minute budget per stage; stop with a partial artifact when the budget check detects
an overrun. No training, install
or download is needed. If a control fails, retain the evidence and limit the conclusion;
do not tune offsets, filters, presets, normalization or thresholds to rescue it.

## Scores and one-time screen rules

Primary: the exact five-resolution MR-STFT in `direc.mrstft` (FFT sizes
256/512/1024/2048/4096, quarter-window hops, periodic Hann, centered reflect padding,
spectral convergence plus natural-log magnitude L1, additive magnitude epsilon
1e-6, and 1e-6 added to the target-norm denominator). Score one take at
a time, not a concatenated batch. Verify an independent NumPy implementation against
torch on synthetic signals in the inference environment. Report fixed-alignment
waveform L1 separately; it cannot replace the primary score. MR-STFT alone differs
from training's combined waveform-plus-spectral loss. Six-second inference follows
`rebuild`, while training validation predicts from a three-second input context.
Those procedures are deliberately identified, not described as identical.

For each take define native relative improvement as
`1 - net_loss/min(wet_loss, flatref_loss)`; a zero denominator is an explicit invalid
comparison, never silently dropped. The proposed native screen passes only with:

- median relative improvement ≥10%;
- strict improvement on ≥9 of 12 takes;
- positive median relative improvement in both the six chords and six scales.

All controls must also pass: twelve valid pairs, metric error <1e-6 for all,
Morgan network median relative improvement ≥10% over Morgan wet-as-DI, and native
FIR median low-band relative improvement ≥10% over native wet-as-DI against raw DI.
These are engineering screens, not calibrated significance tests; takes share one
player/chain. Report every individual loss, relative improvement, QC and control.
At the inclusive 10% boundaries only, code absorbs subtraction/division roundoff
within eight `math.ulp(0.1)`; wins and positive group medians remain strict.

Interpretation is conditional:

- Native failure with passing controls supports investigating coverage of recorded
  chains. It does not establish that domain shift caused previous preset failures.
- Native success permits declaring a broader development diagnostic; it does not
  authorize long training, a shipping claim or a fresh reserved-data test.
- Failed Morgan or native-recoverability controls make this screen inconclusive for
  a neural transfer diagnosis. Review that specific failure before another experiment.

Use exclusive run folders under project `tmp/`, incremental progress and append-only
logs; never overwrite failed outputs. Independently recompute decision-driving scores
and gates before recording a verified conclusion. Update roadmap/index/main DI plan
and `learn/README.md` on completion. The spent final confirmation remains untouched.

## Execution interface

`learn/run_di_domain_pilot.py STAGE --run tmp/di-domain-pilot-20261008` uses four
stages: `metric`, `native`, `render`, `infer`. The first stage exclusively creates
the run folder; every stage exclusively creates its own subfolder and checks that
the committed code/declaration/manifest pins and assets remain unchanged. No stage
can overwrite a previous failure or change the procedure mid-run.

`metric` compares the NumPy replica with `direc.mrstft` on four synthetic three-second
signals in float64; maximum absolute difference must be ≤1e-8. It must pass before
native audio access. Use the existing CPU torch environment for `metric` and `infer`,
and the project environment through `neuraldsp-safe python-file` for `native` and
`render`. The helper's project environment lacks torch; interpreter switching is an
explicit separate operation, not an embedded bypass in the script. Keep logs and
record live session IDs in `tmp/ml-continuation-monitor.md`.

The fifteen-minute budget is checked between takes and after stage work; individual
library calls have no new hard interrupt. The live monitor must check elapsed time,
progress and errors and stop a stuck stage while preserving its artifacts. Do not
describe the cooperative budget as a guaranteed hard wall-clock cutoff.

Fresh-context Zeno independently approved the corrected design, utility, runner and
current snapshots on 2026-10-08. Combined targeted synthetic checks: **105 passed,
2 skipped** (Torch unavailable in the helper environment). The mandatory CPU-Torch
`metric` stage remains outstanding and precedes native audio. Independent fixtures
cover metric definitions, raw-source calibration/FIR isolation, strict coverage and
gate outcomes. Mocked orchestration checks delay/pre-roll, original DI level,
failure cleanup and rejection without silently dropping bad takes. The review is
archived in [the review record](research/di-domain-pilot-review-2026-10-08.md).
This approval freezes a bounded diagnostic, not a result or authorization to train.
