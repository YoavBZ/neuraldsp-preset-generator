# Does the ear agree with the average-guitar measure? Results

Declared in [avg-measure-listening-plan.md](avg-measure-listening-plan.md), with its
phone amendment. Taken by the user on a phone in two sittings (2026-10-06 and
2026-10-07). The answer sheet's sha256 (`4a932dae…0c37`) was committed in
`docs/avg-measure-listening-answers.sha256` before scoring. Scored by
`learn/build_avg_listening.py score`.

## Outcome: passed

| | result | rule |
|---|---|---|
| disagreement trials agreeing with the average-guitar measure | **23 of 24** (one-sided binomial p = 1.5e-6) | ≥ 17 of 24 |
| hidden repeats answered the same way | 6 of 6 | ≥ 5 of 6, else void |
| swap trials (another player's DI) agreeing with the measure | 6 of 6 (p = 0.016) | reported |
| answers "A" | 18 of 36 | balance check |

Agreement by sitting: 14 of 15 disagreement trials in sitting 1, 9 of 9 in sitting 2.
The one disagreement trial against the measure (trial 8) was answered the same way when
repeated (trial 34).

## What it licenses, and what it doesn't

- **The ear follows the measure.** When the average-guitar measure clearly separates two
  presets (≥ 0.15 in log distance), the listener's ear followed it on 23 of 24 trials.
  It did so too when the presets were heard through another player's guitar.
- **Not a verdict on the old judge.** On most of these trials the true-DI judge preferred
  the other preset only narrowly (median margin about 0.04). So this does not show that
  the true-DI judge is wrong where it is confident.
- **The limits:** one listener, clean PR12 material, factory presets, clear margins.
  High gain and small differences are untested.

**Decision.** The average-guitar measure is adopted as the measure for song-to-preset,
as the user decided on 2026-10-06. This check was the plan's Phase 0 L, and it passed.

## Verified independently (2026-10-07)

A fresh-context reviewer re-scored the check from the key and the answer sheet with its
own code, and matched every figure.
- **Hashes:** the key's matches the plan's. The answer sheet's hash was committed (736bbed)
  before the results commit, and the scorer's own record of it was written a second
  later.
- **No cue but tone:** every R, A and B clip is −20.00 LUFS, and A and B are equal to the
  sample.
  - The measure's pick is not systematically the brighter clip: by spectral centroid on
    11 of 30 trials, by high-frequency energy on 12 of 30.
  - It is A on exactly half the trials, and agreement was 11 of 12 when it was A and
    12 of 12 when it was B.
- **The old judge's margins:** the true-DI judge's margin on the disagreement trials has a
  median of 0.038 (13 of 24 under 0.05). On the 4 trials where it was confident (0.19–0.37),
  the ear followed the average-guitar measure all 4 times. That is too few to conclude
  anything from.
- **A note:** the measure's pick is closer to the reference by spectral centroid on 25 of
  30 trials. The ear and the measure may both track overall spectral balance.
