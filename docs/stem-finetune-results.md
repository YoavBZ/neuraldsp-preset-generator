# Step 6: stages 0 and N, the training-noise repeat (results)

**Status:**
- **Run:** 2026-11-17 to 18, from main at `150da932` (the squash of PR #513, which holds the declared phases).
- **Audited:** 2026-11-18 by an independent recompute, PASS WITH CORRECTIONS. Every number reproduced and the cell is
  right. The corrections are to labels and reading; they are taken here.
- **Plan:** [stem-finetune-plan.md](stem-finetune-plan.md).
- **Ledger:** `pipeline-fix` `phase_s6_noise_outcome`, `preset-ladder` `phase_l6_noise_outcome`.
- **Data:** `PF/step6/` (`PF` is `~/ndsp-presets/learn/trusted-data/pipeline-fix`):
  - `stage0.json`: sha256 `c40c2bec…f32330`;
  - `gauge-n.json`: `923bda9c…914162`;
  - `report-n.json`: `9cdde4f1…a42da`;
  - N's cell: `a7e497f7…c60ef`.
- **Cost, measured:**
  - stage 0: one CPU pass;
  - training: 18 runs one at a time on the MPS in 90.5 min of wall time (R-rep's 16 runs logged 72.4 run-minutes,
    the replay's 2 logged 6.9; the plan's 126.3 was R-all's, run two at a time);
  - answers: about 2 min of CPU;
  - renders: 5,760 on 3 shards in about 85 min;
  - zero separations, no sealed set.

Every number is by the score: J0, ln(d_row / d_against) on the held half, below zero closer, 90% cluster t intervals;
the deciding pool is BKS, GOAT and the panel weighted equally. Items marked **post hoc** come from the audit and were
not declared before the run.

## The read

- **Stage 0 reads S0-ok.** All 17 controls passed: the stored answers reproduced bit for bit from the stored features,
  report-rc's rows were re-derived, and the fold bans and the disk guard held.
- **Stage N reads N-quiet.** N, R-all's recipe trained again with two new fine-tune seeds against R-all, is
  `rep-xl@-3 − xl@-3` = **+0.0031 [−0.0043, +0.0104]** on the deciding pool (df 15): undecided.
- **What that licenses:** only the stop and the hand-back. Nothing starts by itself. The pilot waits for the user's
  answer to open question 1, and, by the user's word, no decision is taken before the separate listening check of
  whether the score can be trusted at small differences.
- **What N is:** one draw of the fine-tune's seed noise. R-rep shares W's two states and D_fix's draws, so N does not
  sample W's training noise (see the gauges below).

## The rows

960 directions over the five sets (956 in the main rows, 4 read apart). The deciding pool holds 694 of them: BKS 240,
GOAT 430, the panel 24. Clusters: BKS 8, GOAT 130, cap1 19, n12 8, the panel 5. Every row is complete (480 parts,
none missing) and made from today's answers.

| Row | Deciding pool | BKS | GOAT | cap1 | n12 | Panel | Every set by DI file |
|---|---|---|---|---|---|---|---|
| **N** `rep-xl@-3 − xl@-3` | **+0.003 [−0.004, +0.010]** | −0.006 [−0.021, +0.009] | +0.015 [+0.006, +0.024] | −0.008 [−0.016, −0.001] | +0.048 [−0.011, +0.107] | +0.000 [−0.017, +0.017] | +0.010 [+0.003, +0.017] |
| `rc-rep-xl@-3 − rc-xl@-3` (the noise on O's row) | −0.010 [−0.023, +0.003] | −0.017 | +0.006 | −0.008 | +0.010 | −0.019 | +0.002 |
| `rc-rep-xl@-3 − cen` (a second draw of the goal row) | −0.002 [−0.059, +0.056] | +0.024 | +0.032 | +0.050 | +0.120 | −0.062 | +0.037 |
| `ens4-xl@-3 − xl@-3` (side row, no table) | +0.004 [−0.000, +0.008] | −0.002 | +0.007 [+0.002, +0.013] | −0.006 | +0.007 | +0.006 | +0.005 |

- **For scale, the stored rows** (reproduced by the audit): `rc-xl@-3 − cen` +0.008 and `rc-xl@-3 − xl@-3` −0.052.
  O's ceiling for Step 6 was `rc-mix@-3 − rc-xl@-3` −0.035.
- **N's adversarial read:**
  - The pool leaving one set out: without BKS +0.008, without GOAT −0.003, without the panel +0.004.
  - Leave one cluster out: BKS −0.009 to −0.001, GOAT +0.012 to +0.016, the panel −0.007 to +0.005.
  - GOAT reads worse in its clean, crunch and half-A rows alike.

## The gauges (knob space, zero renders)

RMS move between two answers in unit terms, over knob heads both answers sound and the part's label holds
(`knob_read`'s definition), on `xl@-3`:

| Pair | RMS move |
|---|---|
| R-all's two seeds (different W states) | 0.0675 |
| R-rep's two seeds (different W states) | 0.0668 |
| A new fine-tune seed against R-all's from the same W state | 0.0210 and 0.0163 |
| R-rep's pair against R-all's pair | 0.0127 |
| `ens4` against R-all's pair | 0.0063 |
| R-all's pair, `xl@-3` against `mix@-3` | 0.0597 |
| Spread between parts in a cell | 0.051 to 0.057 (one seed), 0.048 (the pair) |

- **What the seed-to-seed figure is.** The 0.067 is W's state plus the fine-tune seed. Pairs across W states move
  0.067 whatever the fine-tune seed. The fine-tune seed alone moves answers 0.016 to 0.021, and N samples only that
  part.
- **The replay is bit for bit.** Fold 3's inner run and FT_3 for seed 20261043, trained again with nothing changed,
  read E 46 for both, as stored. Every epoch's loss and all 84 state tensors are identical. The checkpoint files
  differ only in the zip archive's root folder name, which `torch.save` takes from the file name. So the
  `"model identical": false` in `gauge-n.json` is a false negative of a whole-file hash. The answers on fold 3's parts
  are identical.
- **E by fold:** R-rep's against R-all's from the same W state.

  | Fold | 20261181 (W 42) | R-all 42 | 20261182 (W 43) | R-all 43 |
  |---|---|---|---|---|
  | 0 | 75 | 84 | 67 | 70 |
  | 1 | 60 | 55 | 60 | 60 |
  | 2 | 59 | 50 | 57 | 58 |
  | 3 | 66 | 51 | 46 | 46 |

  None is at the cap. Every run trained on R-all's same fold's rows, ids, inputs, rate, cap and mask.
- **A correction to the plan.** Plan section 4 put "between inputs 0.041 to 0.044, between parts 0.039 to 0.044"
  beside this gauge. Those are the ladder's stage 0 inputs (`mix-drawn`, `clean-kind`, `xl-v0`). For `xl@-3` against
  `mix@-3` the figures are 0.060 and 0.039 (mix) or 0.048 (xl), from the ladder's stage 2 report. Both are right in
  their own context.

## Post hoc (the audit's reading, not declared)

- **What the pool's interval covers.** The ±0.007 is the sampling of units for two fixed models; it holds no training
  variance. One draw barely bounds the training noise: its SD could be roughly 0.002 to 0.05. One repeat is not enough
  to size it. Each further repeat costs about 72 run-minutes and 27 min of renders a row, at the measured rates.
- **Per-set reads between separate trainings are not trustworthy at about 0.015.** The fine-tune seed alone gave
  decided per-set reads both ways: GOAT +0.015 worse, cap1 −0.0085 better, every set by DI file +0.010 worse (and
  `ens4` GOAT +0.007 worse).
  - The same doubt extends to earlier per-set or one-pair-against-one-pair claims of that size between separately
    trained models, such as C3r's "worse on one deciding set" adoption rule and the model-comparison rows. None is
    re-read here.
  - Reads that keep one model and change only its input or its readout (`rc-xl@-3 − xl@-3`, `xl@-3 − mix@-3`, a model
    against Cen) are not affected in this way.
- **The goal row.** The seed alone moved O's like-for-like row by −0.010, against O's ceiling of −0.035, so the noise
  rule's O2 is needed.
- **W's state dominates the knob answers.** The 0.067 between W states exceeds the spread between units (0.051 to
  0.057), and the move from the backed mix to the stem (0.060). Under independent noise, about 70% of one network's
  per-unit spread is W-state noise, and about half of the pair's. Comparisons that retrain W carry more noise than N
  shows.
- **Pooling four seeds gained nothing** by the score: +0.004, leaning worse.
- **The replay.** This recipe trains bit-reproducibly on the MPS with today's torch, by one replay. It says nothing
  about the older MPS stft-gradient bug, which was wrong deterministically.

## What it does not show

- **The noise's size or distribution:** N is one draw, and its per-set rows are correlated.
- **W's training noise:** N shares W's states.
- **Whether the score can be trusted at small differences by ear:** the user's separate listening check.
- **Anything about stems:** the pilot and the full run are not built.
