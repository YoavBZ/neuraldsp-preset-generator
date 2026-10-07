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
