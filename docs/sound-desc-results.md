# Predict the sound, not the knobs: results of the first test (development)

Run 2026-10-11 under [plan v2 and its amendments](sound-desc-plan.md). Independently
reviewed: every headline figure was reproduced with the reviewer's own code
(`tmp/sound-desc-stage1-review.md`, local).

> **Corrected by the [2026-10-11 audit](audit-2026-10-11.md).** The gates stay
> inconclusive, but "no better than untrained baselines" and "below the chooser" were
> part-weighted readings driven by one song (Eat The Feeder's Wickerman, 12 of 39 crunch
> cells). Counting each band once, the translator is −0.147 against the fixed crunch
> preset, level with the chooser (−0.145) and near the ceiling (−0.163); without that
> band it matches the ceiling. The sim-to-real explanation holds for the MLP, not for
> ridge. **Verdict: undecided, not failed.** The text below is kept as first written.

## In short

- **Stage 0 passed:** with the same notes, matching a simple sound description picks
  crunch presets well (−0.124 against the fixed crunch preset, 35 of 39 cells closer).
- **Stage 1 was not shown to help.** A translator from a record's description to the
  plugin's description of "an average guitar through preset p" picks presets no better
  than the cheap untrained baselines, on crunch, and is worse than the fixed preset on
  clean.
- **Both gates are inconclusive,** so Phase B (a model of every setting) does not start.
- **It is below the existing rebuilt-DI chooser** everywhere (+0.077 overall).
- **Why:** real records sit about twice as far from the plugin's renders as renders sit
  from each other, and each record is off in its own direction. A model trained only on
  renders can't learn that gap.

## What ran

- **Training data:** 323 DI windows from 27 non-test bands, each treated the measure's
  way (average balance, −22.9 LUFS), rendered through all 111 menu presets: about
  36,000 renders, two 4.5-s segments each, plus a noise-only augmented copy.
- **Models:** ridge (primary), an MLP and a bias-only model, from the render's
  description (D130, carried from stage 0) to `T(p)`. 15 folds, each holding out one
  test band.
- **Test:** the 35 pinned development parts (22 clean, 13 crunch, 15 bands). Choose on
  one half, score with the fixed-level measure on the other, both directions.

## Results (mean log ratio, band-clustered 90% interval; negative is closer)

Against the leave-band-out fixed preset (`base`), per gain class:

| method | crunch (6 bands) | clean (10 bands) |
|---|---|---|
| oracle (true best) | −0.183 | −0.087 |
| same-notes ceiling | −0.124 | −0.005 |
| rebuilt-DI chooser | −0.118 | −0.039 |
| **ridge translator** | **−0.081** [−0.208, +0.046] | **+0.062** [0.000, +0.125] |
| centroid | −0.063 | +0.044 |
| no learning | −0.053 | +0.029 |
| bias only | −0.041 | +0.060 |
| MLP | −0.006 | +0.033 |

**The gates (crunch decides):**
1. **Ridge against centroid** (the better cheap baseline): −0.018 [−0.157, +0.121],
   18 better, 13 worse. **Inconclusive.** It closes 30% of the gap to the ceiling.
2. **Ridge against the fixed preset:** −0.081 [−0.208, +0.046]. **Inconclusive.**

**Phase B:** not started. **Positive control** (the minimum held): fed the test parts' own
stored renders, ridge beats centroid by −0.013.

## What the review found

- **Order and integrity:** render code, evaluation code and the gate amendment were all
  committed before any result existed. Under the original pooled gate 1, the outcome is
  also inconclusive (+0.011).
- **No bug that sinks the translator:** consistent standardisation, all 111 presets
  matched everywhere, no band leakage, the same descriptor code and the same level and
  balance treatment as the measure. One cosmetic mislabel in the result file is fixed
  (it counted presets as windows).
- **The ridge penalty at the top of the grid is immaterial:** a wider grid gives the
  same gates (−0.013, −0.076). The model is informative, not a disguised bias: it finds
  the right preset on held-out renders 50% of the time, against 38% with no learning.
- **Gate 1 could hardly have passed:** with 6 crunch bands, one holding 15 of 39 cells,
  even a perfect same-notes translator scores −0.061 [−0.138, +0.016] against centroid,
  still inconclusive. The plan's reviews missed this. It doesn't change the reading
  below, which doesn't rest on the gate.
- **The loss is sim-to-real, not translation:**
  - Fed renders, every method is already near its best: ridge −0.139, no learning
    −0.135, centroid −0.126 on crunch.
  - Fed real records, ridge falls to −0.081: about 0.058 lost between render and record,
    against about 0.01 gained by learning.
  - Records' distance to the nearest training render is 6.8 (crunch) and 9.9 (clean),
    against 3.3–4.0 for renders. They are far even from the best render of their own DI.
  - 82% of that gap is in the long-term tone, and it differs per record: no shared
    offset a model could learn.

## What this means

- **The idea isn't disproved, but this form of it is done.** A translator trained only
  on plugin renders can't see what real records add (the mic, the real cab and room, the
  mix EQ), so it ends up near "no learning".
- **Any further attempt needs record-like inputs or a metric learned on records,** plus a
  test with enough crunch bands to decide. With 6 development crunch bands, nothing short
  of the oracle is decidable.
- **The bar that matters is the rebuilt-DI chooser** (−0.118 on development crunch),
  not the cheap baselines.
