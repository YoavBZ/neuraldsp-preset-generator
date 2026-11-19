# The learning-curve diagnostic: would more recordings help? (results)

**Status:**
- **Run:** 2026-11-19, from main at `d45cb302` (the squash of PR #519, which holds the declared phases), in a clean
  detached worktree. `8da62eb6` (PR #521) changed only docs and the ledger's wording.
- **Audited:** 2026-11-19 by an independent blind recompute, PASS WITH CORRECTIONS. Every number reproduced to 1.9e-4
  or better, the cell re-derived, and the provenance is clean. The corrections are to wording and are taken here.
- **Plan:** [half-data-plan.md](half-data-plan.md).
- **Ledger:** `pipeline-fix` `phase_s6_half_outcome`, `preset-ladder` `phase_l6_half_outcome`.
- **Data:** `PF/step6/half/` (`PF` is `~/ndsp-presets/learn/trusted-data/pipeline-fix`):
  - `selection.json`: content sha256 `04486424…87fa26b`;
  - `runs-a.json`;
  - `report-a.json`: sha256 `34565832…a3a3646`;
  - the cell: `6dbc7316…5afef13eb`.
- **Cost, measured:**
  - training: 16 runs one at a time on the MPS, 17:42 to 18:32 (49.5 min wall, 39.0 run-minutes);
  - answers: under a minute of CPU;
  - renders: 3,840 on 3 shards, from about 18:35 to about 19:31;
  - zero separations, no sealed set.

Every number is by the score: J0, ln(d_row / d_against) on the held half, below zero closer, 90% cluster t intervals;
the deciding pool is BKS, GOAT and the panel weighted equally. The model trained on half the recordings is
**R-half1** (code arm `a`, half key `A`, rows `half-a-xl@-3`). Its partner on the other half, **R-half2**, was not
trained. Items marked **post hoc** come from the audit and were not declared before the run.

## The read

- **The cheaper stop reads A-stop.** H_a is R-half1 against its matched R-all (the same W state and fine-tune seed in
  every fold run), re-centred, on the product's input. It reads `rc-half-a-xl@-3 − rc-xl@-3` = **+0.025 [−0.003,
  +0.053]** on the deciding pool (478 parts, Silent Waves's 2 left out as declared), undecided.
- **Under the user's rule it reads "short":** the upper end just passes +0.05, so the interval reaches past the heard
  size, but it is not decided, so no gap counts. In practice "short"
  and "not readable by the score" carry the same action: none.
- **The declared direction note** (`outcome.direction_note`, verbatim): "halving is not shown to cost. If the gain per
  doubling does not grow, doubling is not shown to buy a heard-size gain either. This read does not show where the
  limit lies".
- **What that licenses:** only the stop.
  - D-data, the one acting cell, needs H_a decided worse, so none remains.
  - As declared, R-half2 is not trained (saving about 80 min of training and 57 min of renders), and the full
    `D_TABLE` read is not run.
  - No doublings figure is computed: the code computes one only for a decided cost.
  - Nothing changes in the product.
- **What the interval rules out:** a halving cost above about +0.053 on the re-centred row.
- **Power.** H_a's own half-width is 0.028, wider than the 0.012 to 0.02 the plan gave for the two-model decision
  row H.

## The rows

478 parts, 956 directions. Clusters: BKS 8, GOAT 130, the panel 4 DI files (10 parts). n12's 2 apart parts are read
apart as always.

| Row | Deciding pool | BKS | GOAT | cap1 | n12 | Panel | Every set by DI file |
|---|---|---|---|---|---|---|---|
| **H_a** `rc-half-a-xl@-3 − rc-xl@-3` | **+0.025 [−0.003, +0.053]** | +0.037 [−0.001, +0.075] | +0.005 [−0.013, +0.024] | +0.033 [+0.004, +0.062] | −0.021 | +0.032 | +0.012 [−0.002, +0.025] |
| raw `half-a-xl@-3 − xl@-3` | +0.060 [+0.036, +0.085] | +0.120 | +0.055 | +0.084 | +0.065 | +0.006 | +0.061 [+0.042, +0.081] |
| against R-rep `rc-half-a-xl@-3 − rc-rep-xl@-3` | +0.037 [+0.011, +0.064] | +0.054 | −0.000 | +0.041 | −0.031 | +0.059 | +0.009 |
| the full spread `rc-rep-xl@-3 − rc-xl@-3` | −0.013 [−0.028, +0.002] | −0.017 | +0.006 | −0.008 | +0.010 | −0.026 | +0.002 |
| the full models against Cen `rc-xl@-3+rc-rep-xl@-3 − cen` | +0.004 [−0.073, +0.081] | +0.033 | +0.030 | +0.054 | +0.115 | −0.051 | +0.036 |
| R-half1 against Cen `rc-half-a-xl@-3 − cen` | +0.035 [−0.031, +0.101] | +0.078 | +0.032 | +0.091 | +0.089 | −0.005 | +0.047 |

Every row other than H_a is beside: it has no table and decides nothing.

- **H_a's adversarial read:**
  - The pool leaving one set out: without BKS +0.019 [−0.024, +0.062]; without GOAT +0.035 [−0.006, +0.075]; without
    the panel +0.021 [+0.001, +0.042].
  - Leave one cluster out: BKS +0.026 to +0.052, GOAT +0.002 to +0.009, the panel +0.008 to +0.054.
  - By class, post hoc: BKS crunch +0.066 [+0.011, +0.121] against clean +0.009; GOAT crunch +0.042
    [+0.019, +0.066] against clean −0.030 [−0.052, −0.007].
  - Per-set and per-class reads between separately trained models are untrustworthy at about 0.015 (stage N).

## Training

- **The halves:** draw 20, as declared. Half 1 holds BKS 7 of 14 chains, GOAT 108 of 214, cap1 24 of 48, n12 6 of 12
  and the panel 2 of 5. Its shares of each set's records are BKS 0.471, GOAT 0.505, cap1 0.496, n12 0.500 and panel
  0.500. Every (amp, class) cell is kept in both halves in all 8 fold runs.
- **The runs:** every one at R-all's rate, cap, mask, held ids and units, init state and plugin rows. Training units
  sit inside half 1 and inside the full run's. The fold bans hold, and every protected file is unchanged. None reached
  the cap.
- **E, R-half1 against R-all's same run:**
  - FT_k: k0 22 against 84 and 21 against 70; k1 38 against 55 and 21 against 60; k2 26 against 50 and 24 against
    58; k3 42 against 51 and 43 against 46.
  - As ratios: 0.26 to 0.52 in 5 of the 8, 0.69 in one, and 0.82 and 0.93 at fold 3. This is the early-stop caveat
    the plan names. An epoch-matched read was not planned.
- **Silent Waves:** its chain is in half 2, so R-half1 did not train on it; R-all and R-rep did. The read leaves its
  parts out.

## Post hoc (the audit's reading, not declared)

- **The undecided reading is fragile.** Other reads of the same model come out decided worse:
  - with every part (Silent Waves in): +0.023 [+0.001, +0.045], which would have read A-go;
  - without the panel: +0.021 [+0.001, +0.042];
  - against R-rep: +0.037 [+0.011, +0.064];
  - against both full models: +0.031 [+0.005, +0.058].

  The declared read stands, and the stop loses no acting cell. D-data needs H's lower end over 0.05, which would need
  R-half2's row near 0.1, far beyond any noise seen.
- **Against R-rep's +0.037.** It is H_a minus the full spread (−0.013), so it is the comparator's seed noise, not a
  separate effect. The line between undecided and decided sits inside that noise. The size is the robust part: about
  0.03, with an upper end of about 0.06.
- **Raw against re-centred.**
  - Re-centring gains −0.085 on R-half1 against −0.049 on R-all. So about 60% of the raw cost (+0.060, decided) is
    the mean answer drifting, which re-centring removes without labels.
  - Cen already beats the full models' raw answers (+0.061).
  - Half the data mainly costs the model's aim, not its reading of each recording.
- **The early stop.**
  - E comes from each run's own validation, so part of the early stop is the genuine effect of less data. A premature
    stop would under-train R-half1 and bias the cost up.
  - By fold, the raw cost tracks the early stops (k0 +0.130, k1 +0.093, k3 −0.005), and the re-centred cost does not
    (k0 −0.004, k1 +0.067, k3 +0.011).
  - So the stop mostly shifts the aim, and the re-centred bound is, if anything, conservative.
- **The doublings, at constant returns per doubling** (n = (F + 0.06) / g; with diminishing returns n is a lower
  bound). F is the full models against Cen, +0.004.

  | Halving cost g | Doublings to about −0.06 against Cen | More trusted chains |
  |---|---|---|
  | +0.053, H_a's 90% upper end | 1.2 | about 380 |
  | +0.031, against both full models | 2.1 | about 940 |
  | +0.025, H_a's point estimate | 2.6 | about 1,400 |
  | +0.064, the upper end against R-rep (the most favourable pairing) | 1.0 | about 293 |

  F's own interval, ±0.077, dominates. At F's lower end the goal is already met; at its upper end it takes 2.7
  doublings or more.

## What it says (post hoc)

This rests on the post hoc doublings above, not on a declared cell.

**By the score, more recordings would help a little, but not by enough.** Halving the chains costs the per-unit
reading about 0.02 to 0.04, under the heard size, and it costs the raw answers mostly through their aim. A gain big
enough to hear would take about two doublings or more, roughly 900 to 1,400 more trusted chains. Even at the most
favourable 90% end it takes about 300 to 380. That is beyond the stated supply, or at best at its edge. TONE3000's
calibrated clean and low-gain rigs are mostly used, and about 175 labelled capture units already failed the ear or DI
checks.

## What it does not show

- **R-half2:** not trained, by the declared stop. So half-choice noise is not sampled, and there is no second draw of
  the half-data side.
- **Anything by ear.**
- **The curve's shape:** it is one halving point, read on the ladder's built mixes at −3 dB on six lender sessions,
  conditional on W's two states.
- **Whether the cost is the data or the epoch count:** not separated; the reading above says which way it leans.
