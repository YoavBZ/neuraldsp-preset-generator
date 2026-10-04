# Kill tests on clean PR12 presets: not passed

Computed as declared in `docs/kill-tests-pr12-plan.md`.
- **What ran:** the three kill-test scripts at 69d34a2, on the 21-preset clean PR12
  panel at the parts' recorded lags.
- **The verdict:** `scripts/kill_tests_pr12_verdict.py` at d82eddf, committed before any
  output was read. Its output is `docs/kill-tests-pr12-verdict.json`.
- **Checked independently:** a fresh-context reviewer re-derived every figure from the
  outputs and recomputed every judge distance from the audio. Every K1 and K3 row
  matched exactly. It found no bug.

## Verdict

| Test | Result | Detail |
|---|---|---|
| K1 headroom | **fail** | the oracle's median of band medians against template+R is −0.267 (23%) with default bands and −0.206 (19%) with union bands, not ≤ log 0.75 (−0.288); 25 parts in 9 bands |
| K2 across players | pass | top-1 21.5% (1-NN), 43.1% (LDA), 43.5% (LDA+1-NN) against 3/21 = 14.3%; regret ratios 0.44–0.67 |
| K3 real amp tracks | **fail** | no recogniser under either band set reaches −0.150, or even the declared log 0.9 (−0.105) |

The K3 figures for each recogniser, under default / union bands. All counts are out
of 28 parts in 11 bands.

| | band median | closer than template+R | better than shuffled | closer than constant | most common pick |
|---|---|---|---|---|---|
| 1-NN | −0.012 / −0.013 | 15 / 17 | 16 / 17 | 11 / 13 | 29% |
| LDA | −0.023 / −0.009 | 16 / 17 | 19 / 19 | 13 / 16 | 54% |
| LDA+1-NN | −0.064 / −0.030 | 18 / 18 | 19 / 18 | 11 / 15 | 57% |

**Does not pass on clean PR12.** The failure doesn't hang on a threshold or a tie rule:
- counting ties as half changes no outcome;
- the band sign-flip p for K3's gain is 0.40–0.96.

## Reading

- **K3's failure is not just K1's.** Under the plan, a K1 failure says nothing about
  transfer by itself. But there is headroom here, just under the bar:
  - The best preset per part, chosen knowing the track, is 24% / 20% closer than
    template+R over the full window.
  - The recognisers capture 4% (1-NN), 9% / 4% (LDA) and 24% / 13% (LDA+1-NN) of that.
    On SW50R, 1-NN captured 81–90%.
  - 1-NN's picks sit at the median of the 21 presets for their part, where chance
    would put them; on SW50R they sat at the 22nd percentile.
  - Giving each part the next band's pick does a little better than its own. The picks
    match K1's oracle preset on 0–2 of 25 parts.
- **The menu, more than the step to real audio, may be why.** K2's open-set reading
  holds each preset out of training, as a real track requires; it is reported, not
  deciding. There the recognisers' mean regret (3.62–3.68 dB) is worse than the
  constant's (3.38). On SW50R they beat it (3.70–4.01 against 4.65). That predicts a
  near-zero K3 from renders alone.
- **But clean presets were recognised on SW50R.** Within SW50R's clean presets, 1-NN's
  picks ranked in the top 12–16%. So SW50R's success was not just telling clean from
  high-gain.
- **What the data cannot separate:**
  - The amp and the menu changed together.
  - Most per-part differences fall below the validated 0.150 cut, so the per-part
    counts rest on an unvalidated range.
  - Only 28 parts in 11 bands.
- **The constant is about template+R:** +0.005 / −0.005 against it. The best single
  preset in hindsight, Pedal Steel at −0.072, beats every recogniser except LDA+1-NN
  under default bands.
- **The LDA variants pile onto one preset.** They pick Out of this World Clean on 15–17
  of 30 parts, though as a constant it scores +0.13. That looks like real tracks
  landing near one hub preset in feature space, a sign of the render-to-real gap.
- **ALM tells the same story.**
  - K1 passes under ALM (−0.326).
  - ALM's best K3 figure, LDA+1-NN at −0.138, rests on the four parts whose catalogued
    lags are 9.5–14 ms off; without them it is +0.029.
  - Per part, ALM and the judge agree closely (Spearman 0.89–0.92).

## What follows

- **Model work:** not supported by the kill tests on either material. The SW50R verdict
  stays "not passed", and on the validated clean range the recognisers carry almost no
  part-specific information. Whether to proceed is the user's decision; the amp
  identifiability check (`docs/amp-identifiability-plan.md`) is still running.
