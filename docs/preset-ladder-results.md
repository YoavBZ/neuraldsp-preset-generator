# The preset ladder: results

**Status:** Step 2 stopped by its stop rule (plan section 15, "After stage 2", branch 3). Stages 0, 1 and 2 and the
re-centred answer ran on 2026-11-17 and are audited; stage 3 is not run and goes to the user with separator work. Plan: [preset-ladder-plan.md](preset-ladder-plan.md); ledger `preset-ladder` (`phase_l0`,
`phase_l0_outcome`, `phase_l1`, `phase_l1_outcome`, `phase_l2`, `phase_l2_outcome`, `phase_lrc`, `phase_lrc_outcome`).
Data: `~/ndsp-presets/learn/trusted-data/pipeline-fix/ladder/` (`report-stage0.json`, `report-stage1.json`,
`report-stage2.json`, `report-rc.json`, `centres.json`, `answers/`, `controls/`). Every reading here is by the score (J0), not by ear.

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
| clean-kind − cen | +0.011 [−0.047, +0.070] | −0.001 | −0.018 | +0.053 | −0.022 | −0.135 |
| clean-kind − aconst | −0.010 [−0.055, +0.034] | −0.011 | −0.032 | +0.011 | −0.005 | +0.035 |
| mix-drawn − cen | −0.012 [−0.055, +0.030] | +0.036 | +0.003 | −0.076 | −0.005 | −0.062 |
| mix-drawn − aconst | −0.034 [−0.060, −0.009] | +0.026 | −0.011 | −0.118 | +0.013 | +0.108 |
| aconst − cen | +0.022 [−0.011, +0.054] | +0.010 | +0.014 | +0.041 | −0.017 | −0.170 |
| mix@-3 − mix-drawn | −0.013 [−0.039, +0.014] | −0.062 [−0.107, −0.017] | −0.041 [−0.062, −0.020] | +0.065 [−0.008, +0.137] | −0.033 | −0.063 |

Beside: Cen − S −0.121 [−0.177, −0.065], Aconst − S −0.099, `mix@-3` − S −0.146 [−0.213, −0.079], `mix-drawn` − S
−0.133 (equal to stage 0's and C3r's own on every field); the same-input constants against Cen +0.049 [+0.010, +0.088] (`mix@-3`),
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

**The size.** Two-thirds of the −0.075 is the same-input constant scoring worse than Cen (+0.049 [+0.010, +0.088]).
What the audit's zero-render checks show: the constant is not off-manifold (its discrete choices are some pool answer's
own in 460 of 480 pools, and its knobs sit closer to the nearest pool answer than answers sit to each other); where an
answer's discrete choices equal the constant's, the gain is still −0.042 [−0.059, −0.025]; the gain tracks the
answer's approach to its label in knob space (−0.119 where it approaches, +0.045 where it doesn't); and on GOAT the
constants of the two inputs score alike while `mix@-3` gains −0.058 and `mix-drawn` −0.008, which a fixed averaging
handicap would not produce. What they don't settle: the size, between the knob-explained part (about a third of
−0.075) and the whole; and, on BKS, set-level against per-unit reading. Stage 2's swap rows size the per-unit reading
free of the averaging question; they draw from the same cross-set pools, so they still count set-level differences as
reading and leave the BKS question open.

**The negatives are underpowered, not absent** (what each pool interval rules out, at 90%):
- `clean-kind − sic-clean-kind` −0.035 [−0.090, +0.020] rules out a loss beyond +0.020 and leaves a gain up to 0.09
  open; it is decided on BKS, GOAT and cap1, and one panel DI file holds the pool undecided.
- `mix@-3 − cen` −0.025 [−0.075, +0.025] rules out a loss beyond +0.025; a heard-size gain is neither shown nor ruled
  out.
- `clean-kind − cen` +0.011 [−0.047, +0.070] rules out a heard-size gain (its lower end is above −0.05).
- `mix-drawn − cen` −0.012 [−0.055, +0.030] rules out a loss beyond +0.030.
- `aconst − cen` +0.022 [−0.011, +0.054] rules out Aconst gaining more than 0.011 on Cen.
- `mix@-3 − mix-drawn` −0.013 [−0.039, +0.014] rules out a build loss beyond +0.014; it is decided better on BKS, GOAT
  and cap1, and `mix-drawn − sic-mix-drawn` (resting on the panel and BKS; GOAT −0.008, n12 +0.125) depends on the
  panel in the opposite direction.
- Any cut other than the declared pool (without the panel, by DI file, the five-set pool) is post hoc and beside.

**The build, as measured.** Unmastered units sit at exactly −3.00 dB target-to-rest; mastering moves the ratio by more
than 1 dB on 38 of 400 units (up to +3.8 dB); the backed mix's target sits −3.2 to +6.2 dB over its bare backing
(interquartile −1.8 to +1.7).

**Knob reads.** `mix@-3`'s answers follow their labels within cells about as `mix-drawn`'s do (tone r +0.25, drive +0.12,
cab +0.17, EQ +0.11), with a spread 15–21% of the labels'; its mean answer sits close to Aconst (RMS shift 0.012–0.025)
and far from Cen (0.04–0.11).

**Next by the table:** a full stage 2; stage 3 by its triggers (outcome 1 fired the exposure and pooling triggers).
Stage 2's declaration is in the plan's section 15, with the audit's four changes; it ran after its review (below).

## Stage 2 (2026-11-17, 800 separations, 12,480 renders)

> **Stage 2, by the score.** On the product's own input (X-LANCE's stem of a full mix), the model's preset is not
> better than the fixed label-centre preset Cen. By the declared rule it reads worse: +0.061 [+0.005, +0.117]. That
> reading is fragile: it is undecided with any one of BKS, GOAT or most single panel recordings left out, or on half A
> alone. But a heard-size gain over Cen is ruled out in every cut. So Cen goes to Step 3 as the candidate start, and
> the model path is not the default.
>
> **Where the loss is.**
> - The product's level step costs nothing (a cost beyond 0.006 is ruled out).
> - The separator itself costs +0.053 [+0.009, +0.096], mostly on crunch. Part of that is the model reading an
>   isolated guitar worse than the backed mix it was trained on, part is X-LANCE's artefacts.
> - The other guitars cost about +0.07 to +0.09, mostly on clean songs with clean other guitars. They are undecided
>   on the declared pool only because the panel's five recordings disagree.
>
> **The ceilings.** By the declared rule they open separator work: removing the other guitars perfectly would recover
> -0.085 [-0.120, -0.051] of the stem's loss. But even a perfect input only brings today's model about level with Cen
> (-0.025 [-0.072, +0.023]). So a better separator alone isn't shown to beat the fixed preset; it pays only with a
> readout that beats Cen.
>
> **The model does read each recording.** Its answer beats another recording's answer by -0.129 [-0.171, -0.087] on
> the backed mix, and by -0.099 [-0.184, -0.013] on the stem. On GOAT and cap1 this isn't a set-level effect. But its
> average guess sits off: +0.117 from Cen on the stem.
>
> **In plain words:** the model listens, but aims off-centre. Fixing the aim is the next lever, and a better separator
> on its own is not.

(The audit's signed summary, verbatim.)

Audited by separate code: it **stands with corrections** to fragility and meaning, none to a number or the rule (836
report fields reproduced, the largest difference 5.3e-15; the exact t changes no reading; the code that ran is
byte-identical to the reviewed 7efe8e9a, and the rule's functions are unchanged on main (this PR changes `q2q3_outcome` only for a missing Q2 reading); every judge file's answer
hash equal to its answer; 64 of 64 sampled answers re-made from the stored stems' features; no rerun, nothing dropped).

**How it ran.** From commit a59e94e9, launched 09:02:57. X-LANCE separated 800 stems (400 units, the full mix and the
mix without other guitars) on the MPS in 61 min (4.6 s a stem); every unit's rebuilt mixes equalled stage 1's stored
features exactly (the rebuild check), so the stems come from the same mixes stage 1 read. Then the answers (about a
minute), `sic-xl@-3` and the two swap rows (seconds), and 12,480 renders on three shards, 10:05:56 to 13:09:44 (3 h 4
min). `report --stage 2` took 34 s. Every row has all 480 parts (960 directions). Stage 1's judge files were reused
untouched; the rows that cross the two stages add up exactly (largest difference 4e-17).

**Q2 and Q3, the rule rows** (90% cluster t intervals; the deciding pool weighs BKS, GOAT and the panel equally):

| Rule row | Deciding pool | Reading | BKS | GOAT | Panel | cap1 | n12 |
|---|---|---|---|---|---|---|---|
| Q2 xl@-3 − cen | **+0.061 [+0.005, +0.117]** | worse | +0.073 [+0.031, +0.114] | +0.067 [+0.032, +0.102] | +0.043 [−0.123, +0.208] | +0.117 | +0.050 |
| Q2 xl@-3 − sic-xl@-3 | −0.056 [−0.134, +0.021] | undecided | −0.100 [−0.257, +0.057] | −0.016 [−0.047, +0.015] | −0.053 [−0.253, +0.148] | +0.022 | +0.130 |
| Q3 the separator alone, xlnoG@-3 − mixp@-3 | +0.053 [+0.009, +0.096] | worse | +0.025 | +0.033 [+0.017, +0.049] | +0.100 [−0.003, +0.204] | +0.052 | +0.075 |
| Q3 the level step, mixp@-3 − mix@-3 | +0.001 [−0.005, +0.006] | undecided | +0.007 | +0.001 | −0.006 | −0.002 | −0.037 |
| Q3 the other guitars, xl@-3 − xlnoG@-3 | +0.032 [−0.012, +0.077] | undecided | +0.066 [−0.044, +0.176] | +0.071 [+0.042, +0.099] | −0.040 [−0.131, +0.052] | +0.104 | +0.137 |

`Q2_STEP3` (reading "worse"): the model path leaves the road to default; Cen goes to Step 3 as the candidate start.
"Worse" and "undecided" send the same action; they differ only in wording. Q3's declared consequence: the separator
alone reads worse (fragile, item 2 below), so Step 6 (fine-tune on what the product feeds) gets a measured target.
The level step reads undecided (nil, item 3), so no level fix is called for.

**The ceilings** (`separator_ceiling`, read together by `ceiling_together`):

| Pair | Deciding pool | Reading | BKS | GOAT | Panel | cap1 |
|---|---|---|---|---|---|---|
| clean@-3 − xl@-3 (a perfect separator; confounded) | −0.060 [−0.108, −0.012] | heard-size gain | −0.080 [−0.168, +0.009] | −0.091 [−0.119, −0.063] | −0.010 [−0.139, +0.119] | −0.140 |
| mixp@-3 − xl@-3 (only the other guitars removed) | −0.085 [−0.120, −0.051] | heard-size gain | −0.092 [−0.165, −0.019] | −0.104 [−0.135, −0.072] | −0.061 [−0.145, +0.023] | −0.156 |

`ceiling_together` reads **"opens separator work"** by its first branch. It is robust on `mixp@-3 − xl@-3` (Holm
0.008, decided in every cut, no cluster flips it; its whole interval lies beyond −0.05, by 0.0007) and fragile on
`clean@-3 − xl@-3` (undecided with BKS or GOAT left out, flipped by two panel DI files, −0.046 without the heavier
lenders), which the opening doesn't need. **What it means:** both ceilings are measured against today's stem path,
the worst input in the stage, so they say how much of the stem's loss a separator could recover, not whether the
model path would then beat a fixed preset. It isn't shown to: `mixp@-3 − cen` (the other guitars removed perfectly, no
separator) is −0.025 [−0.072, +0.023] and `clean@-3 − cen` (a perfect separator) +0.001 [−0.051, +0.052], which rules
out a heard-size gain at about 0.05. The ceiling reaches only about Cen. The plan's section 15 note "After stage 2"
(written before the re-centred report was run, revised after this write-up's review) narrows how the opening is acted
on: the ladder plans separator work only if a re-centred read beats Cen, and otherwise puts it to the user with both
readings, since the approved gate is met.

**The trigger and exposure rows** (stage 2's):

| Row | Deciding pool | Reading | GOAT |
|---|---|---|---|
| mixp@-3 − cen | −0.025 [−0.072, +0.023] | undecided | −0.037 [−0.065, −0.008] |
| xlnoG@-3 − cen | +0.028 [−0.028, +0.085] | undecided | −0.004 |
| clean@-3 − cen | +0.001 [−0.051, +0.052] | undecided | −0.024 [−0.053, +0.005] |

Beside: `xl@-3 − aconst` +0.039 [−0.010, +0.088]; `xl@-3 − S` −0.060 [−0.132, +0.012] (undecided; GOAT −0.039
decided); `sic-xl@-3 − cen` +0.117 [+0.054, +0.180]; `xl@-3 − mix@-3` (the whole stem path) +0.086 [+0.051, +0.121];
`xlnoG@-3 − mix@-3` (separator and level step) +0.054 [+0.007, +0.100]. The gap shares of `xl@-3 − cen` are negative
(it moves away from the label: GOAT −0.18, BKS −0.27, cap1 −0.30).

**Stage 3's triggers.** By the rule the exposure rows and pooling fire, both from stage 1's rows (Q1's outcome 1,
`mix@-3 − sic-mix@-3`, `mix-drawn − sic-mix-drawn`); no stage 2 trigger row reads better. `xlmdxc` and `xl-real` don't
fire (the other guitars undecided). Stage 3 is held until the re-centred read (plan section 15, "After stage 2"), since
it measures the un-re-centred path, whose best case here is about Cen.

**Where it is thin** (the audit's corrections; every cut other than the declared pool is post hoc and beside):
1. **Q2's "worse" is decided by the declared rule but fragile.** One-sided p 0.038; Holm over stage 2's ten
   adversarial rows 0.54. It is undecided with BKS left out (+0.055 [−0.031, +0.140]), GOAT left out (+0.058
   [−0.028, +0.143]), any one of four of the panel's five recordings left out (Big Troubles +0.039 [−0.003, +0.082],
   Drowning +0.058, Silent Waves +0.059, The Laminar Flow +0.070 [−0.008, +0.147]; each leaves the panel 4 DI files,
   which widens its t), on half A alone (+0.035 [−0.023, +0.093]) and without the heavier bands' lenders (+0.043
   [−0.0015, +0.087]). It holds without the whole panel (+0.070 [+0.044, +0.096]), on every set clustered by DI file
   (+0.076 [+0.050, +0.103]), on the five-set pool (+0.070 [+0.020, +0.120]) and on clean (+0.071 [+0.002, +0.140]).
   The robust statement: in every cut the lower end is −0.031 or above, so a heard-size gain over Cen is ruled out throughout
   (the crunch-only pool, on the panel's 2 crunch DI files, is uninformative). The stem path loses to the unseparated
   backed mix at product level by a robust margin (+0.085), and that mix was only about level with Cen.
2. **The separator alone is fragile, mostly crunch, and not a separator quality cost alone.** Undecided without GOAT
   (+0.063 [−0.002, +0.128]), without the panel (+0.029 [−0.022, +0.081]) or the heavier lenders (+0.050); decided by
   DI file (+0.033 [+0.020, +0.047]) and on half A (+0.042 [+0.005, +0.080]). Crunch +0.117 [+0.022, +0.212] (Forkupines
   +0.059, Storm Of Particles +0.154), clean +0.001. It splits into two parts, each undecided on the pool: isolation
   itself, `clean@-3 − mixp@-3` +0.025 [−0.005, +0.056] (the model reads an isolated guitar, an input it never trained
   on, worse than the backed mix, as in stage 1), and X-LANCE's artefacts against perfect isolation, `xlnoG@-3 −
   clean@-3` +0.028 [−0.025, +0.080] (decided worse in crunch, +0.107 [+0.069, +0.145], and better in clean, −0.031
   [−0.050, −0.012]).
3. **The level step is nil, by measurement.** A cost beyond 0.006 is ruled out; every cut lies within ±0.007, every
   set by DI file −0.002 [−0.005, +0.001], flat across the product gains tested (−5 to +7 dB, median +0.7; r 0.01 with
   the gain). The model's mels depend on level and `mixp@-3`'s answers differ from `mix@-3`'s in all 960 directions,
   so this is an empirical finding, not a property of the build.
4. **"The other guitars undecided" is underpowered, not absent.** The panel's five DI files alone hold it undecided
   (−0.040 [−0.131, +0.052]); without the panel +0.068 [+0.012, +0.125], every set by DI file +0.090 [+0.069, +0.112],
   the five-set pool +0.068 [+0.027, +0.108], clean +0.110 [+0.066, +0.154]; crunch is level (−0.052 [−0.165,
   +0.060]). The trigger is correctly not fired by the rule; very likely a false negative. X-LANCE's SI-SDR doesn't
   track the cost: worst on crunch/Forkupines (median −1.1 dB, leak +0.4 dB), where the cost is nil, and better on
   clean/The Travelling Band (+4.2 dB, leak −5.0 dB), where it is largest. Separator work judged by SI-SDR would aim
   at the wrong target.
5. **"Opens separator work" reaches only about Cen** (above).
6. **The swap rows read an averaging gain, not a penalty** (below).
7. **Every lender row is conditional on the six lender sessions** (plan section 7). Q2's loss and the other guitars'
   cost sit mostly on one lender, The Travelling Band's clean sections: `xl@-3 − cen` there by DI file +0.216 [+0.159,
   +0.272] (124 parts), and `xl@-3 − xlnoG@-3` +0.231 [+0.184, +0.277]; Hazael's +0.052 and +0.075; the small clean
   lenders Dunning Kruger (+0.27, 7 parts) and Forkupines (+0.64, 6 parts); crunch/Forkupines (211 parts) level, −0.013
   [−0.032, +0.006].

**The swap rows** (the per-unit size, beside the same-input constant's):

| Row | Deciding pool | GOAT | BKS | Panel |
|---|---|---|---|---|
| mix@-3 − swap-mix@-3 | **−0.129 [−0.171, −0.087]** | −0.103 [−0.128, −0.077] | −0.168 [−0.244, −0.093] | −0.117 [−0.231, −0.002] |
| xl@-3 − swap-xl@-3 | **−0.099 [−0.184, −0.013]** | −0.060 [−0.090, −0.029] | −0.113 [−0.219, −0.008] | −0.123 [−0.376, +0.130] |
| swap-mix@-3 − sic-mix@-3 | +0.055 [+0.030, +0.079] | +0.044 [+0.027, +0.062] | +0.049 | +0.070 [+0.024, +0.117] |
| swap-xl@-3 − sic-xl@-3 | +0.043 [+0.002, +0.083] | +0.044 [+0.021, +0.067] | +0.013 | +0.070 |

- **`swap − sic` reads an averaging gain.** A single other unit's answer scores worse than the averaged constant, so
  the constant was the stronger comparator: stage 1's `mix@-3 − sic-mix@-3` (−0.075) was conservative, and its open
  "averaged preset scoring worse" explanation is ruled out at 90%. (The plan's "read the averaging penalty directly"
  reads its reverse.) `i − swap-i` exceeds `i − sic-i` by exactly that amount.
- **`mix@-3 − swap-mix@-3` is robust** (no cluster flips it; decided with any deciding set left out, on half A
  −0.115, on clean −0.141, per lender band −0.10 to −0.13, by DI file −0.111). The per-unit reading on the exposed
  backed mix lies between −0.075 (against the mean answer) and −0.129 (against a random other answer).
- **`xl@-3 − swap-xl@-3` is fragile** (five clusters flip it; undecided with any one deciding set left out; decided by
  DI file, −0.053 [−0.076, −0.030], and on GOAT; nil on cap1, −0.019, and on clean units lent The Travelling Band's
  guitars, +0.020): the stem keeps some per-unit reading, smaller and less sure, and none where the other guitars
  bleed in. Its pool interval is about 1.6 times the half-width the audit's simulation expected (±0.054; GOAT's ±0.030
  as expected).
- **Set-level against per-unit reading, settled on GOAT and cap1 at zero renders.** Within a cluster, draws from the
  same set gain as much as draws from other sets (same set − other set: GOAT `mix` −0.009 [−0.058, +0.039], 90
  clusters; GOAT `xl` −0.014 [−0.064, +0.036], 92 clusters; cap1 `mix` −0.004 [−0.088, +0.079], 18 clusters). Set-level
  reading would make same-set draws gain less, so there per-unit reading drives the swap gain. On BKS (4 clusters with
  any same-set draw) and the panel (one part) it can't be separated: the BKS question stays open.
- Draws from other sets: `swap-mix@-3` BKS 88.7%, GOAT 54.0%, cap1 78.1%, the panel 95.8%; `swap-xl@-3` 87.5%, 51.2%,
  79.8%, 95.8% (the plan's 89/54/78/96 are `swap-mix@-3`'s).
- What it means: the model reads each unit, but around a misplaced centre (`sic-mix@-3 − cen` +0.049, `sic-xl@-3 −
  cen` +0.117; a single answer's scatter costs too, `swap-mix@-3 − cen` +0.104); the per-unit reading wins back only
  enough to net about Cen on the mix (−0.025) and not on the stem (+0.061). That is the case for re-centring (and
  pooling, which reduces scatter), not for a better separator first.

**The stems, as measured** (half A, against the target; per unit, the 400 separation records, interpolated
quartiles): X-LANCE on the full mix, SI-SDR median +0.75 dB (quartiles −1.47, +4.79), the other guitars' leak median
−1.27 dB (−5.79, +0.70); on the mix without other guitars, SI-SDR median +17.2 dB (+14.4, +20.1). Stem loudness less
the mix's: median −2.25 dB (full), −2.95 dB (without other guitars).

**Renders used in Step 2 so far:** 21,180 (stage 1's 8,640 and the replay's 60; stage 2's 12,480). Separations 800.

**Next** (plan section 15, "After stage 2", decided before the re-centred report): stage 3 is held; the re-centred
read decides. If `rc-xl@-3 − cen` reads better, the re-centred path becomes the candidate (`RC_JOINT`'s "propose")
and Step 1 confirms; if only `rc-mix@-3 − cen` does, separator work is planned, judged by the preset score; if
neither, the ladder stops and Cen goes to Step 3, `RC_JOINT`'s "flagged" cell still applies, separator work and stage
3's rows are put to the user with both readings, and the next levers are the approved plan's Steps 5 and 6.

## The re-centred answer (2026-11-17, 9,600 renders, zero separations)

> **The re-centred answer, by the score.** Moving the model's centre onto the label centre while keeping its
> per-recording deviation does not make the model path beat the fixed label-centre preset Cen on the product's input.
> On X-LANCE's stem, `rc-xl@-3 − cen` is +0.008 [−0.042, +0.059] on the deciding pool: undecided, and it rules out a
> gain beyond 0.042, so this is a real negative, not an underpowered one. On both large deciding sets it reads worse
> (BKS +0.041, GOAT +0.027; cap1 +0.058 beside). The pool sits on the neutral side only through the panel's 12 parts
> (5 recordings), which carry 89% of its variance, as declared beforehand.
>
> **What it does do.** Re-centring improves the model's own answer on the stem: `rc-xl@-3 − xl@-3` −0.052 [−0.078,
> −0.027], better. That is the joint table's "flagged" cell: if the model path stays behind its flag, it is re-centred,
> as its own reviewed change; not the default. The −0.052 comes from the ladder's per-part, input-matched table, so it
> is optimistic for a product table, which can do worse. On the exposed backed mix the gain isn't shown (`rc-mix@-3 −
> mix@-3` −0.002 [−0.029, +0.025]), and even there the re-centred answer is only level with Cen (`rc-mix@-3 − cen`
> −0.027 [−0.061, +0.007], undecided).
>
> **The stop rule** (plan section 15, "After stage 2", set before this report was run) gives **branch 3, neither reads
> better**: the ladder (Step 2) stops and Cen goes to Step 3. Separator work and stage 3's rows (exposure, pooling) are
> put to the user with both readings, pending the user's call. The heard-size clause fires for `rc-mix@-3 − cen` (its
> lower end −0.061 holds a heard-size gain: undecided and underpowered, not failed) and not for the goal row.
>
> **In plain words:** the model hears something of each recording (its own deviation beats another recording's), but
> that deviation adds nothing over the fixed preset on the product's input. Today the most accurate preset without
> human intervention, by the score, is Cen, which beats S by about 0.11 to 0.12. The reader is the limit; the approved
> plan's Steps 5 and 6 are the next levers.

Audited by separate code: it **passes with corrections** to wording only, none to a number, a reading or an action
(768 values recomputed blind from the raw judge files, the largest difference 5.3e-15; the exact t moves no interval by
more than 0.0004 and changes no reading; every `sources_sha256` equals the current file; every judge file's answer
hash equals its answer in 480 of 480 parts in all five rows; 960 distinct render hashes per row).

**How it ran.** Declared as `phase_lrc` at 10:00:22 (rename commit e891325d, pushed 10:00:37), before `report --stage
2` was run (`report-stage2.json` was written at 13:11:03). Launched at 13:09:47 from e891325d on 2 shards, beside the
real-song exam's one render process (the launcher checked that `learn/` outside the ladder module equalled a59e94e9's,
the code that rendered stages 1 and 2). The five rows' 4,800 answers took about 30 s; 9,600 renders (4,800 kept: 5 rows ×
480 parts × 2 halves, plus priming) ran 13:10:18 to 16:37:39 (3 h 27 min, about 23 a minute a process). The stop rule
was written at 13:30:22 and revised at 13:44:31, after the renders began and before `report-rc` ran (16:38:07, 23 s).
Every row has all 480 parts; every pair reads 960 of 960 directions.

**The joint table** (`RC_JOINT`, deciding pool: BKS, GOAT and the panel weighed equally; 90% cluster t intervals):

| Action row | Deciding pool | Reading | BKS | GOAT | Panel | cap1 | n12 |
|---|---|---|---|---|---|---|---|
| rc-xl@-3 − cen (goal) | **+0.008 [−0.042, +0.059]** | undecided | +0.041 [+0.001, +0.081] | +0.027 [+0.004, +0.050] | −0.043 [−0.193, +0.107] | +0.058 [+0.016, +0.101] | +0.110 |
| rc-xl@-3 − xl@-3 (own) | **−0.052 [−0.078, −0.027]** | better | −0.032 [−0.068, +0.004] | −0.040 [−0.068, −0.013] | −0.085 [−0.157, −0.014] | −0.059 [−0.087, −0.031] | +0.060 |

`rc_outcome`: goal undecided, own better → **"flagged"**: re-centring helps the model's own answer on the stem but
isn't shown better than Cen; if the model path stays behind its flag, re-centre it (its own reviewed change); not the
default; Step 3's start stays as stage 2's Q2 sends it (Cen). "Undecided" and "worse" on the goal row share this cell.

**The stop rule's rows** (plan section 15, "After stage 2"):

| Row | Deciding pool | Reading | BKS | GOAT | Panel | cap1 |
|---|---|---|---|---|---|---|
| rc-xl@-3 − cen (branch 1) | +0.008 [−0.042, +0.059] | undecided | +0.041 | +0.027 | −0.043 | +0.058 |
| rc-mix@-3 − cen (branch 2) | −0.027 [−0.061, +0.007] | undecided | −0.008 [−0.059, +0.044] | −0.041 [−0.058, −0.023] | −0.032 [−0.128, +0.064] | −0.047 [−0.079, −0.015] |
| rc-mix@-3 − rc-xl@-3 (the separator's ceiling after re-centring; beside) | −0.035 [−0.066, −0.004] | better | −0.049 [−0.105, +0.007] | −0.067 [−0.095, −0.040] | +0.011 [−0.072, +0.094] | −0.105 |

Neither branch row reads better, so **branch 3**. Its clauses: the flagged cell applies (above); separator work and
stage 3's rows go to the user with both readings; the heard-size clause fires for `rc-mix@-3 − cen` (lo90 −0.061,
below −0.05) and not for `rc-xl@-3 − cen` (lo90 −0.042); the next levers are Steps 5 and 6. The separator's ceiling
after re-centring is a gain shown with heard size undecided (mean inside −0.05), carried by GOAT; BKS is undecided and
the panel +0.011. Even the ideal input reaches only about Cen.

**The other declared rows:**

| Row | Deciding pool | Reading | Label (`RC_LABELS`) |
|---|---|---|---|
| rc-mix@-3 − mix@-3 | −0.002 [−0.029, +0.025] | undecided | |
| rc-xl@-3 − S | −0.113 [−0.189, −0.036] | better | |
| rc-mix@-3 − S | −0.148 [−0.211, −0.085] | better | |
| rca-mix@-3 − mix@-3 (the knobs' re-centring alone) | −0.004 [−0.028, +0.020] | undecided | not settled |
| rc-mix@-3 − rca-mix@-3 (the discrete rule) | +0.002 [−0.018, +0.023] | undecided | not settled |
| rc-mix@-3 − rcs-mix@-3 | −0.096 [−0.134, −0.058] | better | p's own deviation reads p on the exposed backed mix |
| rcs-mix@-3 − cen | +0.069 [+0.047, +0.092] | worse | another unit's deviation on Cen loses to Cen (mix) |
| rc-xl@-3 − rcs-xl@-3 | −0.075 [−0.145, −0.005] | better | p's own deviation reads p on the stem (see below) |
| rcs-xl@-3 − cen | +0.083 [+0.042, +0.125] | worse | another unit's deviation on Cen loses to Cen on the stem |

Gap shares of the `− cen` rows (the share of the Cen-to-label gap closed): `rc-xl@-3` negative in four sets (BKS
−0.12, GOAT −0.07, cap1 −0.14, n12 −0.21; the panel +0.20 on 12 directions); `rc-mix@-3` +0.07 to +0.12 (n12 +0.24 on
12 directions); `rcs-mix@-3` and `rcs-xl@-3` negative in every set but n12 on the mix (+0.02).

**Where it is thin, and what each row means** (the audit's corrections; every cut other than the declared pool is post
hoc and beside):
1. **The goal row's pool and the panel.** The pool's weights and degrees of freedom (5.08) follow the declared method;
   the panel decides because it has at least 3 recordings (5 here), and its dominance of the pool's variance was
   stated in advance. The cuts that read worse are all post hoc: without the panel +0.034 [+0.012, +0.056]; an
   inverse-variance weighting +0.029; every set by DI file +0.034 [+0.015, +0.054]. The other way, also post hoc:
   without the heavier lenders −0.013 [−0.036, +0.010], a cut that moves the panel from −0.043 to −0.110 by removing
   one one-part panel cluster. Undecided and worse share the same action.
2. **Branch 2's row, without the heavier lenders.** Post hoc and beside: `rc-mix@-3 − cen` without the heavier bands'
   lenders reads better, −0.039 [−0.063, −0.015]. Branch 2 turns on this row, but the declared pool decides, and it is
   undecided.
3. **Re-centring is not shown on the mix, and helps on the stem.** `rc-mix@-3 − mix@-3` −0.002 [−0.029, +0.025] is
   undecided, not nil. The contrast with the stem is decided (post hoc difference of differences, `(rc-xl@-3 − xl@-3)
   − (rc-mix@-3 − mix@-3)` −0.051 [−0.066, −0.036], better in every deciding set), consistent with the stem path's mean
   answer sitting further from Cen (`sic-xl@-3 − cen` +0.117 against the mix's +0.049).
4. **The own row is exact arithmetic.** The pool means add exactly (same directions and clusters): `rc-xl@-3 − xl@-3`
   = `rc-xl@-3 − cen` − `xl@-3 − cen` = +0.0084 − 0.0608 = −0.0524. Likewise `rc − rcs` = `(rc − cen) − (rcs − cen)`
   on both inputs.
5. **`rc-xl@-3 − rcs-xl@-3` better is +0.008 − 0.083.** p's own deviation beats another unit's on Cen, but it is no
   better than no deviation (Cen itself) on the stem. The declared label's second clause ("a goal 'better' is the
   model's reading") is moot: there is no goal "better". On the mix, `rc − rcs` −0.096 is −0.027 (`rc-mix@-3 − cen`)
   less +0.069.
6. **The deviation controls lose to Cen.** Another unit's deviation added to Cen loses to Cen on both inputs (+0.069,
   +0.083): Cen's averaging penalty, which these rows were declared to read, is not shown.
7. **The knobs moved onto Cen; the discrete rule brings knobs with it.** Re-centring brings the sounding knobs' cell
   mean to within 0.002–0.005 (RMS, unit space) of Cen's, against the raw answers' 0.04–0.12; that covers only knobs
   that sound in both the answer and Cen, not the whole preset. The continuous output of `rc-mix@-3` and `rca-mix@-3`
   is identical, but their rendered presets differ wherever the rule switches a feature on from Cen with Cen's knobs
   (the compressor in 219 of 960 directions, the first drive in 102, the right mic's cab knobs in 102, the mic types
   in 219 and 177); so `rc − rca` reads the discrete rule together with the Cen knobs it brings in. The within-cell
   correlation of answer and label is the raw answer's to within 0.013 in every group (the deviation is kept); for
   the rcs answers it is about zero, as expected.
8. **The lender rows hold for the six lender sessions** (plan section 7), as in stages 1 and 2.

**Renders used in Step 2:** 30,780 (stage 1's 8,640 and the replay's 60; stage 2's 12,480; the re-centred answer's
9,600). Separations 800. Report and data: `PF/ladder/report-rc.json`; the two stop-rule rows beside the report were
computed with the report's own pairing and statistics (`rc-mix@-3 − cen` equals the report's row).

**Next** (branch 3): Step 2 stops; Cen goes to Step 3 as the candidate start. Pending the user's call, with both
readings: separator work (its ceiling after re-centring −0.035, heard size undecided; a perfect input reaches only
about Cen) and stage 3's rows (they measure the un-re-centred path, and `clean@-3 − cen` is +0.001). The flagged
re-centring is its own reviewed change if the model path stays behind its flag. The next levers are the approved
plan's Step 5 (targets the model can learn) and Step 6 (fine-tune on what the product feeds; after re-centring the
remaining stem-against-mix gap is about 0.035, smaller than its stated target of +0.053).
