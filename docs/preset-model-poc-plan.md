# A learned settings model, proof of concept: the plan

Written 2026-10-06, before any model was trained or any result read. The renders
started at the same time; nothing is computed from them until this is committed.

## The question

Does a network trained on plugin renders of *sampled* settings (not a menu of factory
presets) transfer to real amp tracks? This is the test the earlier recognisers failed
(K3 on clean PR12, [kill-tests-pr12-results.md](kill-tests-pr12-results.md)). They were
1-NN and LDA over hand-made long-term features, labelled with 21 factory presets, from
about 900 renders. This POC changes the model, the labels and the data, and keeps the
test.

## What is built

- **Data** (`learn/di_pool.py`, `learn/render_job.py`): 20,000 renders of PR12 with
  sampled settings. Half are drawn over each control's range; half are jittered PR12
  factory presets.
  - The DI windows come from the 13 set-2 development bands' full-session DIs, plus
    Guitar-TECHS P1 as a 14th player. There are 3,936 windows of 2 s pre-roll and 6 s
    kept.
  - The rule set R applies, as in the panels.
  - The labels are amp knobs, effective drive (`inputGain` plus the window's loudness
    above −22.9 LUFS), 9-band EQ, filters, compressor, both drive pedals, both cab mics
    (type, position, distance, level) and the right mic on/off.
- **Model** (`learn/train.py`): a CNN on loudness-normalised 128-band log-mel of 4-s
  crops. Its outputs are continuous heads (masked by their pedal's switch), switches and
  mic types.
  - Training augmentation adds bleed (the instrumental backing of a training-band crop,
    12–30 dB under the guitar) and a noise floor.
  - One model per fold, trained only on renders whose DI is from another fold's band.
    Guitar-TECHS is in every fold.
- **Prediction for a part** (`learn/evaluate.py`): the fold model reads the part's real
  amp-track crop (4-s windows, outputs averaged). The prediction is rendered through
  the part's DI with `inputGain` = predicted effective drive. That is the level a song
  does not reveal, assumed rather than read from the DI.

## The test (K3's, unchanged)

- **Parts, folds and lags:** K3's 28 parts in 11 bands, its 4 band folds (seed
  20261003), and its frozen lags (`runs/kill/pr12-clean-judge-lags.json`).
- **Measure:** the judge, `analysis/aligned.py`, over 1.0–10 s, under both band sets.
- **Comparators:** template+R, and the constant re-chosen under the judge on the
  training bands, both read from K3's rows. Also a shuffled control: the model's
  prediction from three other bands' amp tracks, rendered through this part's DI,
  averaged in log distance.

**Pass** (K3's declared rule, under both band sets):
- the band median of log(D_model / D_template+R) is at most log 0.9; and
- the model is closer than template+R, than the shuffled control and than the constant
  on more than half the parts.

The band sign-flip p against template+R is reported. Results are also set beside the K3
recognisers' rows (best of them: LDA+1-NN, −0.064 / −0.030) and the menu's
best-in-hindsight oracle (−0.27 / −0.22).

Also reported, not deciding:
- the same prediction with `inputGain` set from the part's own DI level (a leak, shown
  to size what the assumed level costs);
- in-domain accuracy on held-out-band renders.

## Limits, stated now

- These are the same development parts every earlier choice was tuned on, so a pass
  here is a reason to build the full model (`tmp/preset-model-prompt.md`), not a
  product claim.
- PR12 only, and amp tracks only: no mixes or separated stems yet.
- The judge is validated for clean-to-crunch PR12 differences, which is this material.
- Model choices (architecture, augmentation) are fixed here. If the first run fails,
  any change is logged as a second look, and its result is reported as such.

## Amendment, 2026-10-06, before any model was trained

An independent review of the code, run while the renders ran, confirmed:
- the folds match K3's draw;
- there is no leak from held-out, set-1 or test-band audio;
- the labels round-trip;
- the scoring reproduces K3's recorded rows exactly.

It found these, fixed before training:

- **Noise clips.** About 0.25% of renders were numerical noise: a pedal flipped on with
  its Level at 0, or the volume near 0. Clips whose peak-normalisation gain exceeds
  60 dB are dropped. So are DI windows under −40 LUFS, and the few settings written with
  an exponent, which the plugin may not have parsed. Values are now written in fixed
  point.
- **Mic levels.** After loudness normalisation only the left/right mic-level difference
  is audible. The label is now that difference, and a prediction renders the left mic at
  0 dB. The compressor's release switch is masked when the compressor is off.
- **Scoring.**
  - The shuffled control draws three distinct other bands.
  - A part the judge refuses for the model counts as a loss.
  - The band p-value is K3's own `band_stat`: two-sided, over band medians.

Two corrections to the text above: the DI pool has 3,509 windows (not 3,936), and the
factory share of the sampler jitters 34 PR12 factory presets (not K3's clean menu of 21).
