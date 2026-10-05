# Three quick checks: a set of amps, not too-alike presets, no cheap fix

Computed as declared in `docs/quick-checks-plan.md` (after two reviews), at a7ada5b:
`scripts/reach_sets.py` and `scripts/k3_hub_fixes.py`, from the judge distances in
`~/ndsp-presets/runs/kill/amp-reach.json`. The `commit` field in both outputs says
4da5860, which is a7ada5b before the branch was rebased.

**Checked independently.** A fresh-context reviewer re-derived checks 1 and 2 with its
own code: an exact expected oracle, and a complete linkage of its own cross-checked
against scipy. It recomputed check 3's conditions from the readings and spot-checked the
band medians against the stored distances. Everything matched.

**A code fix made after the run** (73fb0b9):
- **Check 2's combined flag** was more lenient than the plan, so the plan's rule was
  applied by hand to the committed output. It makes no difference here.
- **Float ties:** a 1e-9 tolerance at the 1/3 class cut and the 0.5 one-amp threshold.
- **Input hashes:** `k3_hub_fixes.py` now also hashes the K3 outputs and the panel
  indexes. The committed `k3-hub-fixes.json` predates this and hashes only
  `amp-reach.json`.

A re-run of `reach_sets.py` with the fix reproduces `docs/reach-sets.json` exactly,
apart from the commit field.

## 1. How many amps can answer each recording? A set

On the clean menus, both band sets (default / union):

| | parts with one acceptable amp | band-weighted share | acceptable on (band-weighted) |
|---|---|---|---|
| default | 3 of 25 (2 bands) | 0.08 | PR12 0.87, SW50R 0.87, AC20 0.72 |
| union | 5 of 25 (3 bands) | 0.12 | PR12 0.86, SW50R 0.89, AC20 0.56 |

**Decision: the amp label is a set of acceptable amps.**
- The single-amp rule needs half the parts, and the share is nowhere near it: even at a
  cut of 0.075 it is only 0.38 / 0.33.
- The usual set is {PR12, SW50R} (9 / 10 parts) or all three (9 / 8).
- AC20 alone is acceptable on 1 part, SW50R alone on 2 / 4.

Both PR12 and SW50R are acceptable on 18 of 25 parts (band-weighted 0.79 / 0.80), and
AC20 on 14 / 11 parts. So a product shortlist would show PR12 and SW50R about four
times in five, and AC20 more often than not. The result depends on the cut not being
far below 0.150: at a cut of 0.05 the one-amp share reaches 0.62 / 0.60.

## 2. How many distinct answers does each menu hold? Enough

| Menu | classes (default / union) | separating parts |
|---|---|---|
| clean PR12, 21 presets | 9 / 10 | 24 / 23 |
| SW50R, 21-preset subsets (mean of 200) | 9.4 / 9.2 (range 7–12 / 6–12 in the reviewer's re-draw) | |
| SW50R, all 44 | 15 / 15 | 25 / 25 |
| AC20, all 30 | 12 / 11 | 25 / 24 |

**Decision: identifiability does not explain clean PR12's K3 failure.**
- Clean PR12 has more than 5 classes under both band sets.
- It holds about as many distinct answers as SW50R at the same size.
- The reviewer varied the span (0–0.4), the cut (up to 1/2) and the clear threshold (up
  to 0.2): clean PR12 stays at 6 or more classes, within about 1.5 classes of SW50R's
  size-matched mean either side, and never collapses relative to it.
- The full SW50R and AC20 counts depend on tie-breaking (14–16 and 10–13); neither feeds
  the decision.

## 3. Does a cheap fix rescue K3's recognisers? No

**Canary.** Without a fix, the recognisers reproduced K3's picks exactly: all 30 parts
× 3 recognisers, on both menus.

**No fix meets all four conditions on clean PR12 under both band sets.**
- **The gain is what fails.** The largest gain under both band sets at once is 0.026
  (csls and realnorm+csls on 1-NN), against the 0.05 required. Those two also fail the
  top-share condition (0.32, and exactly 0.25).
- **Some fail only on the gain:** realnorm on 1-NN and on LDA, and realnorm+csls on LDA.
- **bias on 1-NN** gains 0.080 under union bands but only 0.017 under default bands,
  and its top share is 0.32.
- **No fix gets close to the headroom.** As a median of band medians, the menu's best
  preset sits about 0.27 / 0.22 below template+R (25 parts), a random preset about
  +0.04 above it (28 parts).
- **The smallest Holm-adjusted p** is 0.19.

| Clean PR12 (median of band medians vs template+R) | unfixed | best fix |
|---|---|---|
| 1-NN | −0.012 / −0.013 | −0.038 / −0.043 (csls) |
| LDA | −0.023 / −0.009 | −0.064 / −0.030 (csls) |
| LDA+1-NN | −0.064 / −0.030 | −0.023 / −0.009 (csls; every fix makes it worse) |

**What the fixes do:**
- **realnorm breaks the hub but doesn't help.** The most common pick falls from 54–57%
  to 14–21%, but the picks get no closer. Scattering the hub's picks is not the problem.
- **csls and bias** leave the hub in place.
- **Fixes change sign between menus.** On SW50R every fix hurts 1-NN: from −0.326 to
  between −0.008 and +0.10. realnorm helps SW50R's LDA variants (LDA+1-NN meets all four
  conditions there, still about 0.2 behind SW50R's unfixed 1-NN), yet the same fix hurts
  clean PR12's LDA+1-NN.

## What follows (the plan's table)

**Check 2 does not explain the failure, and check 3 found no rescue.** So the failure is
transfer: recognition trained on renders does not reach real amp tracks with these
features. Model work stays parked until the "judge as teacher" step
(`docs/research-audio-ml.md` §5, experiment 4) finds features that do. If the model is
ever built, its amp output is a set of acceptable amps, mostly PR12 and SW50R.

**Limits:**
- These are the same 25 and 28 development parts the kill tests used.
- Cross-amp distances (check 1), and SW50R and AC20 distances (check 2's comparison),
  lie outside the range listening validated.
- K3's features use the catalogued lags.
