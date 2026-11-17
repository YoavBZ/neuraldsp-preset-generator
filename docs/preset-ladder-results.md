# The preset ladder: results

**Status:** in progress. Stages 0 and 1 ran on 2026-11-17 and are audited; stage 2 is drafted, not yet in force.
Plan: [preset-ladder-plan.md](preset-ladder-plan.md); ledger `preset-ladder` (`phase_l0`, `phase_l0_outcome`,
`phase_l1`, `phase_l1_outcome`, `phase_l2_draft`).
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

## Stage 1 (2026-11-17, 8,640 renders plus the replay's 60, zero separations)

**Outcome 1 by the declared rule, by the score: on the exposed backed mix (guitar about level with its backing, other
guitars removed, no separator), R-all's answers beat the mean of its own answers to other units by −0.075 [−0.123,
−0.026] (GOAT −0.058 [−0.082, −0.035]): it reads something of each recording. The size isn't settled, since that mean
answer is itself worse than the label centre (+0.049). Against the label centre the model is −0.025 [−0.075, +0.025]
on the pool, undecided (decided on GOAT and cap1, −0.038). In plain words: the model listens a little when the guitar is
exposed, but its average guess sits off, so on this input it is level with a good fixed preset, not shown better.**

Audited by separate code: it stands with corrections to meaning and wording, none to a number (968 report fields
reproduced, the largest difference 3.6e-15; the rule identical at the reviewed and the run commits; every judge file's
answer hash equal to its answer; no rerun, nothing dropped). The constant for Steps 1 and 3 stays Cen (`aconst - cen`
+0.022 [−0.011, +0.054], undecided).

**How it ran.** `check1` passed (10 of 10 stored S0 items and 10 of 10 variant-0 inputs rebuilt exactly). The replay
control first crashed before its first render: the 2026-11-14 cleanup had removed
`learn/direc/cache/average-fold2.npy`, which `song_bank.measure` (the DI treatment every render applies) reads. Restored
bit-exact the same day (sha256 9aa3c3bf…e9a8, rebuilt by inverting 16 stored treated DIs against their raw DIs), the
replay passed: 30 of 30 kept renders equal C3r's stored ones. The renders ran 05:35 to 07:39 on three shards, 2,880
each.

**Q1's rule rows** (90% cluster t intervals; the deciding pool weighs BKS, GOAT and the panel equally):

| Rule row | Deciding pool | BKS | GOAT | Panel | cap1 | n12 |
|---|---|---|---|---|---|---|
| mix@-3 − sic-mix@-3 | **−0.075 [−0.123, −0.026]** | −0.119 [−0.220, −0.018] | −0.058 [−0.082, −0.035] | −0.046 [−0.172, +0.080] | −0.052 | −0.024 |
| clean-kind − sic-clean-kind | −0.035 [−0.090, +0.020] | −0.055 [−0.099, −0.011] | −0.047 [−0.072, −0.022] | −0.004 [−0.169, +0.162] | −0.048 | −0.055 |
| mix-drawn − sic-mix-drawn | −0.052 [−0.090, −0.014] | −0.065 | −0.008 | −0.081 [−0.129, −0.033] | +0.012 | +0.125 |
| mix@-3 − cen | −0.025 [−0.075, +0.025] | −0.026 | −0.038 [−0.066, −0.009] | −0.012 | −0.038 | −0.125 |
| mix@-3 − aconst | −0.047 [−0.078, −0.016] | −0.036 | −0.051 | −0.053 | −0.020 | +0.045 |
| clean-kind − cen | +0.011 [−0.047, +0.070] | −0.001 | −0.018 | +0.053 | −0.023 | −0.135 |
| clean-kind − aconst | −0.010 [−0.055, +0.034] | −0.011 | −0.032 | +0.011 | −0.005 | +0.035 |
| mix-drawn − cen | −0.012 [−0.055, +0.030] | +0.036 | +0.003 | −0.076 | −0.005 | −0.062 |
| mix-drawn − aconst | −0.034 [−0.060, −0.009] | +0.026 | −0.011 | −0.118 | +0.013 | +0.108 |
| aconst − cen | +0.022 [−0.011, +0.054] | +0.010 | +0.014 | +0.041 | −0.017 | −0.170 |
| mix@-3 − mix-drawn | −0.013 [−0.039, +0.014] | −0.062 [−0.107, −0.017] | −0.041 [−0.062, −0.020] | +0.065 [−0.008, +0.137] | −0.033 | −0.063 |

Beside: Cen − S −0.121 [−0.177, −0.065], Aconst − S −0.099, `mix@-3` − S −0.146 [−0.213, −0.079], `mix-drawn` − S
−0.133 (stage 0's and C3r's own, to 0.0); the same-input constants against Cen +0.049 [+0.010, +0.089] (`mix@-3`),
+0.046 [+0.006, +0.086] (`clean-kind`), +0.039 [−0.010, +0.089] (`mix-drawn`); `clean-kind − mix@-3` +0.036 [+0.007,
+0.066]; label − Cen −0.404 [−0.458, −0.350]. `mix@-3` closes 7% of the Cen-to-label gap on GOAT, 15% on BKS (n12's
share uses its 12 label directions).

**Where the headline is thin.**
- It needs BKS: without BKS the pool is −0.052 [−0.117, +0.013]. BKS's same-input pools are 88% other sets' parts, so
  set-level reading counts as per-unit reading there, and BKS's units sit on W's training DIs.
- Half A alone (the product's half) is −0.067 [−0.142, +0.007] and the crunch pool −0.056 [−0.254, +0.143]: both
  undecided.
- It is decided by the declared rule, not at a family-wise level: Holm over the eleven rule rows gives 0.22; it
  survives Bonferroni over the three per-unit rows (one-sided 0.0098).
- Robust to any one cluster left out (pool −0.093 to −0.060), the exact t, the lenders (crunch/Forkupines −0.084, the
  two big clean lenders −0.053 and −0.056) and DI clustering.

**The size.** Two-thirds of the −0.075 is the same-input constant scoring worse than Cen (+0.049 [+0.010, +0.089]).
What the audit's zero-render checks show: the constant is not off-manifold (its discrete choices are some pool answer's
own in 460 of 480 pools, and its knobs sit closer to the nearest pool answer than answers sit to each other); where an
answer's discrete choices equal the constant's, the gain is still −0.042 [−0.059, −0.025]; the gain tracks the
answer's approach to its label in knob space (−0.119 where it approaches, +0.045 where it doesn't); and on GOAT the
constants of the two inputs score alike while `mix@-3` gains −0.058 and `mix-drawn` −0.008, which a fixed averaging
handicap would not produce. What they don't settle: the size, between the knob-explained part (about a third of
−0.075) and the whole; and, on BKS, set-level against per-unit reading. Stage 2's swap rows read the size.

**The negatives are underpowered, not absent.**
- `clean-kind − sic-clean-kind` is decided on BKS, GOAT and cap1; one panel DI file holds the pool undecided.
- `mix@-3 − cen` neither shows nor rules out a heard-size gain; it rules out a loss beyond +0.025.
- `mix@-3 − mix-drawn` (decided better on BKS, GOAT and cap1) and `mix-drawn − sic-mix-drawn` (resting on the panel
  and BKS; GOAT −0.008, n12 +0.125) depend on the panel in opposite directions.
- Any cut other than the declared pool (without the panel, by DI file, the five-set pool) is post hoc and beside.

**The build, as measured.** Unmastered units sit at exactly −3.00 dB target-to-rest; mastering moves the ratio by more
than 1 dB on 38 of 400 units (up to +3.8 dB); the backed mix's target sits −3.2 to +6.2 dB over its bare backing
(interquartile −1.8 to +1.7).

**Knob reads.** `mix@-3`'s answers follow their labels within cells about as `mix-drawn`'s do (tone r +0.25, drive +0.12,
cab +0.17, EQ +0.11), with a spread 15–21% of the labels'; its mean answer sits close to Aconst (RMS shift 0.012–0.025)
and far from Cen (0.04–0.11).

**Next by the table:** a full stage 2; stage 3 by its triggers (outcome 1 fired the exposure and pooling triggers).
Stage 2's declaration is drafted in the plan's section 15, with the audit's four changes, and runs only after its
review.
