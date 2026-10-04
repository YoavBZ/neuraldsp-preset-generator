# "Without a DI, keep the starting preset" under the judge: void

Computed at b383ec3 as declared in `docs/no-di-rule-under-the-judge-plan.md`, by
`scripts/rescore_no_di.py`, from the renders on disk. The result, with every row, is
`docs/no-di-rule-under-the-judge.json`. A fresh-context reviewer re-derived the
statistics from the rows and re-computed several rows with `aligned_distance`. It found
no computation bug.

## The declared outcome: void

The positive control does not pass. That control is SW50R's search with the part's
own DI, against its start. It is closer to the amp track in most bands, but not
significantly, under either band set:

| Band set | median of band medians | sum | bands closer | raw p |
|---|---|---|---|---|
| default | −0.147 | −2.63 | 10 of 12 | 0.078 |
| union | −0.088 | −2.23 | 9 of 12 | 0.149 |

The plan says that if the positive control fails, every verdict is void.

**What void means here:**
- Nothing is concluded about any arm: not better, not worse, not "no closer".
- PR #107's rule and all of the current product text stay as they are, marked "not
  confirmed under the judge". That includes the sentences on the library search
  ("ended level with it", "closer on 23–30 of 43"); they are not updated to the
  judge's numbers.
- Any change of wording, including that mark, goes in a separate PR after the
  listening test (`docs/listening-validation-plan.md`).

The data does not show why the control failed. The plan's label for a failure is "the
pipeline is broken", but the measurement computes as declared. Context only, not a
rescue:
- The positive arm was itself searched against the retired score (`unpaired-v3`),
  which it improved on all 43 parts.
- Under the judge it is closer on 18 of 21 Cambridge parts (part median −0.36), but
  on only 7 of 16 Telefunken parts (+0.04).
- Its p stays above 0.05 because of two bands that lean the other way: Swatkins, a
  single part (Honey), at +0.57, and Doom Flamingo at +0.13.

## The other controls

- **Null (two Tone King start renders): fails under the union bands.** Raw p is 0.108
  with the default bands and 0.042 with the union bands, so Tone King would not have
  been read even with a passing positive. This is a real property of the renders,
  not a bug. Per-part differences are at most 0.010 and band medians at most 0.003,
  100 to 1000 times smaller than the arms' effects. The sign-flip test ignores scale
  and the rule has no effect-size floor, so a lean of that size can trip it; one part
  (Honey) flips sign under the union bands.
- **Replicate (SW50R no-DI search, seed 0):** same sign as seed 11. Band medians are
  +0.386 and +0.426, p 0.003.

## Descriptive only (void, not verdicts)

37 parts in 12 bands; the six parts left out are those the judge refuses on the start
renders, five for their pauses and Hikikomori for too few DI frames. Each value is the
median of band medians of log(d_arm / d_start), under the default and union bands:

| Arm | SW50R | PR12 | AC20 | Tone King |
|---|---|---|---|---|
| no-DI search | +0.48 / +0.50 | +0.49 / +0.48 | +0.49 / +0.49 | +0.57 / +0.56 |
| calculated from the noise probe | +0.35 / +0.33 | +0.40 / +0.39 | +0.31 / +0.29 | +0.30 / +0.32 |
| library search | +0.17 / +0.16 | +0.14 / +0.19 | +0.08 / +0.08 | +0.11 / +0.09 |
| calculated from the library probe | +0.10 / +0.11 | +0.10 / +0.12 | +0.10 / +0.08 | +0.11 / +0.07 |

**The product arms** (no-DI search, noise probe):
- Under both band sets, 0 or 1 of 12 bands and 0 to 3 of 37 parts are closer.
- Holm p is at most 0.005.
- With a passing positive control, the six SW50R, PR12 and AC20 product arms would
  have been "worse". The two Tone King product arms would have been "not read", since
  the null failed.
- One loss: SW50R's no-DI answer on It Was My Fault ElecGtr1 is 23.3 LU under its
  start.

**The research arms** (library search, library probe):
- Every band median leans further from the recording, but none is significant.
- 11 to 19 of 37 parts are closer, and Holm p is at least 0.45.

**No sensitivity reading changes any verdict:**
- ambiguous-lag parts dropped (33 parts, 12 bands);
- each render's own lag (37 parts, 12 bands);
- pause-heavy parts dropped (34 parts, 10 bands).

Own lags more than 0.5 ms from the recorded lag:
- by part: 31 of the 37 kept parts (37 of all 43);
- by render: 271 of 1161 (23%), mostly the searched arms. The start renders account
  for 41 of 387.
- 12 renders sit at the ±2 ms edge, where `estimate_lag` would refuse.

The own-lag reading's medians stay within 0.002 of the main reading's.

## What follows

- Nothing changes in the product now.
- The result stays provisional until stage 0b validates the judge, and is void in
  any case.
- A future re-check needs a positive control that can pass. For example, a search
  with the DI, run under the judge rather than the retired score, should be declared
  before it is computed.
