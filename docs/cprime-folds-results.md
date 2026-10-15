# C′ folds 0, 1 and 3: results (ML plan step 1, 2026-10-15)

Run under the [plan](cprime-folds-plan.md). Three new DI-rebuild networks (C′), one per K3 fold
left out, with fold 2's recipe: seed 0, 5,150 steps at 3e-4, then 23,100 steps from there at 3e-4
falling to 2e-5, on MPS.

- **Training:**
  - fold 0: 14 Oct 22:24 to 15 Oct 06:23 (paused once, 03:00–04:15, under the rule since
    dropped);
  - fold 1: to 12:49;
  - fold 3: to 19:18 (about 8% slower for its last 2.5 h while a CPU separation job ran
    alongside).
- **Splits:** every fold's preflight matched the declared counts:
  - fold 0: 34,792 / 14,014 / 27;
  - fold 1: 38,188 / 10,618 / 29;
  - fold 3: 38,204 / 10,602 / 33.

  The only band outside K3 is Guitar-TECHS P1, as declared.
- **Models:** `~/ndsp-presets/learn/direc/models-cprime-f{0,1,3}/fold{f}.pt`.

## Checks

**1. Sanity:** passed for all three folds. There were no NaN lines and no recoveries.

| Fold | Last validation (step 23,000) | Input-as-DI baseline | Ratio (limit 0.65) |
|---|---|---|---|
| 0 | 59.89 | 106.08 | 0.565 |
| 1 | 62.34 | 114.28 | 0.545 |
| 3 | 57.00 | 109.81 | 0.519 |
| 2 (reference) | 62.27 | 110.57 | 0.563 |
| 2, seed 1 | 61.01 | 110.17 | 0.554 |

The validation sets differ by fold, so the ratios aren't directly comparable. They sit in the same
range as fold 2's.

**2. The declared network check:** passed for all three folds. The measure is the mean 1–3 kHz
coherence between the stem-rebuilt DI and the true DI, over set 3's 5 clean and crunch parts. It
fails below 0.1126.

| Network | Mean | colour-me-red | femme | get-out-of-bed | just-don't-talk | magilla |
|---|---|---|---|---|---|---|
| fold 2, seed 0 | 0.1360 | 0.150 | 0.056 | 0.044 | 0.294 | 0.136 |
| fold 2, seed 1 | 0.1326 | 0.160 | 0.057 | 0.047 | 0.266 | 0.133 |
| fold 2, seed 2 | 0.1343 | 0.165 | 0.060 | 0.048 | 0.259 | 0.139 |
| **fold 0** | **0.1253** | 0.144 | 0.061 | 0.037 | 0.244 | 0.140 |
| **fold 1** | **0.1356** | 0.160 | 0.060 | 0.044 | 0.285 | 0.128 |
| **fold 3** | **0.1287** | 0.150 | 0.065 | 0.048 | 0.254 | 0.126 |

- Fold 0 is the lowest. It is 0.007 under the seeds' minimum, well inside the 0.02 margin.
- just-don't-talk accounts for the largest share of its gap (about two-thirds against the
  seeds' mean). That part also varies most across seeds (0.259–0.294). colour-me-red and
  get-out-of-bed account for the rest.

**3. Report-only:** the menu-pick figure per fold is reported inside step 3.

## After the run

- **Caches:** the runner removed the temporary SW50R and AC20 input/DI caches after the check, as
  declared. Their spectra and metadata are kept. About 34 GB was freed.
- **Step 3:** the plans don't say whether a fold may be used before check 2. Arm A's searches
  on fold 0 and fold 1 parts started before the check ran (about 06:59 and 13:07), on the
  condition that it pass. It ran only at 19:18 and passed for every fold, so no result is
  affected. Fold 3's searches started at 19:19. The rebuild now also requires each fold's
  DONE marker, so a mid-training checkpoint can't be used by mistake.
- **Independent audit:**
  - Every number was re-derived. Check 2 was re-run for all three folds and reproduces to 6
    decimals.
  - No step-3 part's band is in its network's training data. The step-3 plan says the code
    asserts this, but the code doesn't; the audit checked it by hand.
  - The recipe and code pin (ddb3c8c) match fold 2's.

## Stated limits

- One seed per new fold, so seed noise (about 0.004 in this measure for fold 2) isn't separated
  from fold differences.
- The check uses only 5 parts, all from Cambridge set 3. It guards against a broken network,
  not small differences in quality.
