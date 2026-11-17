# The preset ladder: results

**Status:** in progress. Stage 0 ran on 2026-11-17 and is audited; stage 1 waits for its renders (below). Plan:
[preset-ladder-plan.md](preset-ladder-plan.md); ledger `preset-ladder` (`phase_l0`, `phase_l0_outcome`, `phase_l1`).
Data: `~/ndsp-presets/learn/trusted-data/pipeline-fix/ladder/` (`report-stage0.json`, `centres.json`, `answers/`,
`controls/`). Every reading here is by the score (J0), not by ear.

## Stage 0 (2026-11-17, zero renders, zero separations)

Run from commit 9d83064c in the plan's section 9 order, each command under 70 s. Audited by separate code: it stands
with corrections (652 score fields reproduced, the largest difference 3.6e-15; Cen rebuilt for all 30 cells from the
raw labels; Aconst recomputed for 3 cells; the fold bans, the same-input pools and the lenders re-derived with no
problem). It decides nothing; it checks the machinery and reads what is stored.

**The controls.** `check0` passed: the ladder's code reproduces all 960 of C3r's stored R-all answers (equal sha256),
the fold bans show no problem (per fold the split's counts equal each run record's, and the held units equal
`real_held_units` by name), and its pairing reproduces 97 fields of C3r's R-all − S row exactly.

**The lenders.** 1,243 candidates, 22 out as silent. Clean: 203 units, lent by The Travelling Band 102, Hazael 88,
Dunning Kruger 7, Forkupines 6. Crunch: 197 units, lent by Forkupines 173, Storm Of Particles 13, The Travelling Band 8,
Ale Lak 3. The same as the plan's dry run.

**The constants.** Cen and Aconst for every part, the two same-input constants (own-fold pools of 8 to 29 parts), and
`centres.json`: the all-labels constants from every C3r training record, built with `adopted-model.json`'s pair
(142517a2…, ad2fd3fb…), held as C3-cabS, each entry a full setting (129 keys) with `select` as the amp's int index. The
audit cleared it for stage 1 and for Step 1. Example input gains, Cen against Aconst: pr12 crunch −12.2 against −6.9 dB,
sw50r clean −6.5 against −5.8 dB.

**R-all on its stored input**, against S and against 5C's stored core centres (90% cluster t intervals; BKS by DI file,
GOAT by item):

| Row | GOAT | BKS | Panel | cap1 | n12 | Deciding pool |
|---|---|---|---|---|---|---|
| R-all − S | −0.103 [−0.133, −0.072] | −0.130 [−0.212, −0.048] | −0.168 [−0.324, −0.012] | −0.152 [−0.205, −0.099] | −0.338 [−0.631, −0.044] | −0.133 [−0.188, −0.078] |
| R-all − RcBG | −0.029 [−0.059, +0.000] | +0.011 [−0.036, +0.059] | | | | |
| R-all − RcGk | −0.018 [−0.047, +0.011] | | | | | |
| R-all − Rcs2 | | +0.028 [−0.028, +0.085] | | | | |

The R-all − S row is C3r's own. Against the core centres, the planner's preview reproduces for the set rows. GOAT's
R-all − RcBG is undecided by 0.0001 at its top end and flips with one item left out in 47 of 130 cases; what is decided
is narrower (crunch −0.046, half A −0.038).

**By exposure** (R-all − RcBG; post hoc, the lender a seeded draw):

| Ratio | GOAT, the lender's drawn ratio | GOAT, the stored input's own ratio | BKS, the lender's drawn ratio |
|---|---|---|---|
| under −12 dB | +0.046 [−0.007, +0.099] | +0.067 [−0.002, +0.136] | +0.137 [+0.042, +0.232] (5 DI files) |
| −12 to −6 dB | −0.044 [−0.090, +0.002] | +0.036 [−0.019, +0.090] | −0.028 [−0.074, +0.019] |
| −6 dB and over | −0.062 [−0.105, −0.020] | −0.097 [−0.131, −0.064] | −0.035 [−0.240, +0.169] |

- The stored input's own target-to-backing ratio has quartiles −9.65, −6.51 and −3.39 dB (list positions; the
  interpolated median is −6.57). The lender's drawn ratio, which counted the lender's other guitars in the backing:
  −12.14, −9.15, −5.83.
- BKS's bins differ from the planner's preview (+0.156 / −0.018 / −0.023), which weighted units with no DI clustering;
  under the plan's rule the figures above are right.
- Slopes on cluster means: −0.008 to −0.020 per dB, R-all gaining on the centre as the guitar gets louder. The slope
  drops a whole DI cluster when any of its units lacks a ratio (BKS's `24_ElecGtr3aDI`, 2 of its 4 units have no
  backing level); dropping only those 2 units gives RcBG −0.0065 per dB (reported −0.0113), Rcs2 −0.0181 (−0.0197),
  S +0.0001 (+0.0012).

**The knob reads** (descriptive; knob error understates sound):
- The answers' within-cell r with the labels is +0.09 to +0.21 for drive, tone, cab and the EQ (pedals −0.04 on the
  stored input); `clean-kind` and `xl-v0` read alike.
- The answers' within-cell spread is 15–25% of the labels'.
- An answer is farther from its label than the cell's mean label of the other clusters on about 50% of knob values
  (pedals 66%); per cell 34–47% (pedals 63%); the constants themselves score 45–53%. The review's "about 60% of knob
  cells" doesn't hold on this measure.
- A part's answer moves about as much between inputs (RMS 0.041–0.044 in unit terms) as answers differ between parts
  (0.039–0.044).
- The model's mean answer sits close to Aconst (RMS shift 0.013–0.036 by group) and far from Cen (0.04–0.12: drive
  0.12, cab 0.12, pedals 0.10, tone 0.08, EQ 0.05).

**R1's seven model-path windows**, stem LUFS less mix LUFS (metadata only): −5.74, −5.54, −4.28, −3.78, −3.65 dB (the
user's centre version), −1.97, −1.56 dB (the default stem).

**Statistics note.** `pipeline_fix.t95` uses 1.6449 beyond 30 df, so GOAT's 130-cluster intervals are about 0.7%
narrower than the exact t; no reading changes.

## Caveats for reading stage 1 (from stage 0's audit)

- GOAT's R-all − RcBG is undecided by 0.0001 and unstable to one item left out; only the crunch (−0.046) and half A
  (−0.038) readings are decided.
- The exposure split is post hoc. It supports keeping the exposure rows, not a decided effect of exposure. "Worse when
  buried" is decided only on BKS's 7-unit bin and doesn't survive a DI left out.
- `mix@-3` sits in the exposed regime, where the stored input's edge over the core centres was largest (GOAT −0.097 at
  the stored input's own −6 dB and over).
- The core centres set only the core controls (`K.space`), while R-all also sets the EQ, pedals and gate, and their
  renders are older (5C's). Stage 1's Cen and Aconst set every trained control and are rendered now.
- Rows against a constant resolve about ±0.03 on GOAT and ±0.055 on the pool, not the ±0.02 the plan gave for
  model-against-model rows; every Q1 rule row is against a constant.

## Stage 1: waiting

`check1` passed (10 of 10 stored S0 items and 10 of 10 variant-0 inputs rebuilt exactly); the `mix@-3` build, its
answers and `sic-mix@-3` are made (zero renders). The replay control crashed before its first render:
`song_bank.measure`, the DI treatment every render applies, reads `learn/direc/cache/average-fold2.npy` (sha256
9aa3c3bf…), which the 2026-11-14 cleanup removed. Nothing is rendered until that file is back with that sha256.
