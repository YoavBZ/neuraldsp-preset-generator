# Kill tests K1–K3 again, on clean PR12 presets, where the judge is validated

Declared on 2026-10-04, before any of these results is computed. The user asked for
it after stage 0b.

**Why.** The kill tests (`docs/kill-test-results.md`) ran on the SW50R panel and did
not pass as declared: K3's reading under the judge's union bands failed by one tie.
Stage 0b then validated the judge only for clear differences between clean-to-crunch
PR12 renders (`docs/listening-validation-results.md`), and the SW50R presets are
mostly high-gain, outside that range. This asks the same questions inside the
validated range. Whether to build the model stays the user's decision; this result
informs it.

## Material

- **Renders.** The PR12 panel (`~/ndsp-presets/runs/kill/pr12`, rendered for stage
  0b), limited to its 21 factory presets that are not high-gain (no drive pedal, PR12
  volume 0.75 or less, as declared in `docs/listening-validation-plan.md`), with
  template+R as the baseline and the shipped template as K1's reported comparator.
  The menu is those 21 presets, so chance top-1 is 1/21.
- **The limited panel.** A derived panel folder with its own `index.json` listing only
  those rows. It points at the same render files, and its config stamp records the
  source index's sha256 and the 21 names.
- **Parts and rules.** The set-2 development parts, their crops, and every rule of the
  declared tests: K1's and K3's half-playing rules, K2's 4 folds of bands with seed
  20261003, features and recognisers, K3's comparators (the constant chosen on the
  training bands, the shuffled control, the oracle as a bound).

## How it is computed

`scripts/kill_tests.py` (K1, K2), `scripts/kill_test_k3.py` (K3) and
`scripts/kill_tests_judge.py` (the judge's readings), unchanged, run on the derived
panel.

- **Lags.** The judge uses each part's recorded lag (`docs/validation-lags.json`) less
  the 52-sample latency, written into the judge's lag table. The four parts whose lag
  is ambiguous get none, so the judge leaves them out, and the output lists them.
- **ALM.** It keeps its catalogued lags, as declared. It is reported, not deciding.

## What decides

The decision uses the judge alone, under both band sets: the kill tests' clause for
"validates the judge but not ALM" (`docs/kill-test-k3-plan.md`). Stage 0b's own
decision adds one condition: a gain below the clear cut, |log ratio| 0.150, rests on
an unvalidated range and cannot open a gate.

| Test | Passes only if |
|---|---|
| K1 | the oracle's band-median log ratio against template+R is ≤ log 0.75 under the judge's default and union bands |
| K2 | as declared (`docs/supervised-model-plan.md` §0): some recogniser reaches 3× chance top-1 (here 3/21) and at most 0.75× the constant guess's median regret |
| K3 | one recogniser meets the declared rule under both of the judge's band sets, and its most common pick is no more than half its parts' picks. The declared rule asks for: a band-median log ratio against template+R ≤ log 0.9; closer than template+R, than the constant and than the shuffled control on a majority of parts. A tie counts as not closer, as the declaration's text says. In addition, its band-median log ratio against template+R is ≤ −0.150 under both band sets. |

The gate here is "**passes on clean PR12**" only if K1, K2 and K3 all pass as above.
Everything else is reported, not deciding:
- ALM's readings, and the code's own tie-as-half counts;
- the declared log 0.9 threshold without the −0.150 condition;
- per-band figures, distinct picks, the shift-one-band reading;
- open-set K2.

## What follows

- **Passes on clean PR12.** Render-trained recognition carries over to real amp
  tracks, inside the validated range. That supports a model POC limited to
  clean-to-crunch material (no drive pedal, low volume), under the four conditions in
  `docs/kill-test-results.md` ("What follows"), with results read only above the
  clear cut. The SW50R verdict stays "not passed" for high-gain material.
- **Does not pass.** No evidence, even inside the validated range, that recognition
  learned from renders carries over. The model POC as planned is not supported. The
  write-up says which test failed and how, so the user can choose between stopping
  model work and a narrower next step.
- **Either way,** the user decides.

## What is known before computing

- The SW50R kill-test results, all of them.
- Stage 0b's result: 30 trials on 18 of these parts, 4-s windows, offered PR12
  presets.
- The listening pool's distances: every offered pair's judge, union, ALM and v3c
  distances over each part's 4-s window. They were seen as aggregates only (the median
  cut, counts) and through the 24 scored pairs of the trial table.
- Nothing has been computed over the 1.0–10 s windows, or for K2's recognisers, on
  this panel.
