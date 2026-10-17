# Separator-robust C′: results (2026-10-17)

Run under the [plan](cprime-sep-plan.md) and its amendment 1, overnight 2026-10-16/17 (00:06 to
03:47, commit `7fbafc8`). **Audited 2026-10-17** by an independent auditor (fresh context), who
recomputed every number from the stored data and checked the leak and stopping rules: sound, with
ten wording changes, all made below. Readings are descriptive, under the user's rule: effect sizes with 90%
band-clustered intervals, no pass/fail bars. **Zero renders.** The artefacts are in
`~/ndsp-presets/learn/direc-sep/` (`run.log`, `fit-{sep,ctl}-f*.log`, `eval-*.json`,
`report.json`, `report-main.log`, `report-all.log`).

## Headline

- **On the htdemucs stem (the product's input), the separator-robust rebuild is slightly closer
  to the true DI, by amounts inside the noise:**
  - 1–3 kHz coherence **+0.003 [−0.002, +0.009]**;
  - spectral-envelope error (LSD) **−0.24 dB [−0.66, +0.17]** (lower is better).
- **From BS-Roformer** (19 parts, 9 bands) the envelope gain looks clearer: LSD **−0.56 dB
  [−0.94, −0.18]**, lower in all 9 bands; coherence +0.006 [−0.000, +0.013]. But that is mostly a
  property of those 19 parts, not of the separator: on the same parts the htdemucs stem gains
  −0.43 dB and the amp track −0.47 dB (lower in all 9 bands too), and BS-Roformer − amp track is
  −0.09 [−0.47, +0.29].
- **But it gains about as much from the amp track** (LSD −0.26 [−0.51, −0.02], coherence +0.010
  [+0.001, +0.020]). In LSD the difference in differences (stem − amp track) is about zero
  (+0.02 dB); in 1–3 kHz coherence the amp track gains more than the stem (−0.007 [−0.015, +0.001],
  10 of 14 bands). So what the fine-tune learned isn't specific to stems, and this readout can't say whether the augmentation
  or the extra fine-tune did it (below).
- **The control arm never moved off C′:** on every fold its best separator-validation checkpoint
  was step 0, so the control's rows are C′'s rows exactly.
- **Size against the gap it was aimed at:** C′'s own amp-track − stem gap is +0.156 in coherence
  and −1.57 dB in LSD. The stem primaries close about **2%** and **16%** of it.
- **For the render test:** this is a pre-filter, not evidence for local ranking. A small
  envelope gain on stems is in the direction the test needs, so it is worth running (amendment 4
  of the [local-objective plan](local-objective-plan.md)).

## The training

Each fold fine-tunes that fold's final C′ on PR12 renders. Validation every 250 steps;
"sepval" is the separator validation (96 PR12 crops of the held-out training-fold bands, with
their own band's residuals), which selects and stops. Lower is better.

| Fold | Validation bands | sepval at step 0 (C′) | Main arm: best (step) | Stopped at | Control: best (step) | Control range, steps 250–1500 |
|---|---|---|---|---|---|---|
| 0 | Eat The Feeder, Zeno | 69.07 | 66.61 (250), −3.6% | 1,750 | 69.07 (0) | 70.66–72.64 |
| 1 | Adam Buckley, Starnes And Shah | 79.25 | 75.79 (750), −4.4% | 2,250 | 79.25 (0) | 79.92–82.07 |
| 2 | Starnes And Shah, Swatkins | 64.93 | 64.03 (500), −1.4% | 2,000 | 64.93 (0) | 65.46–67.16 |
| 3 | Swatkins, Zeno | 58.96 | 57.96 (250), −1.7% | 1,750 | 58.96 (0) | 59.82–60.61 |

- **Input-as-DI baselines** on the same crops: 111.9, 111.5, 104.7 and 107.2. Both arms sit far
  below them.
- **The stopping rule worked as declared:** every main fold stopped 1,500 steps after its best
  checkpoint (at least 1,500 steps); every control fold at step 1,500.
- **The main arm's best came early (250–750 steps) and the curve then drifted up slightly.** The
  gain on sepval is 1–4%.
- **The control got worse on sepval at every checkpoint on every fold** (by 0.8–5.2%).
- **On the clean fold-f validation the main arm was worse than the control** at 23 of 24 matched
  checkpoints (by −0.2 to +3.1, mean +1.4). C′'s own clean value at step 0 was not logged (the
  plan asked for both curves at step 0), so neither arm's clean change from C′ is known. Worse on
  clean PR12 crops yet better on real amp tracks fits the colouration reading below.
- **The checkpoint rule's nuance:** "best" moves only on a gain of at least 0.2%, so a checkpoint
  lower by less than that would not be kept. It never happened here.
- **Run time:** 29–38 minutes per main fold, 23 minutes per control fold, about 3.7 hours in all.
  Devices: every rebuild on MPS (`report` checks it).

## The contrasts (24 parts, 14 bands)

Separator-robust − C′, paired per part; band-weighted mean, 90% band-clustered t interval
(bands − 1 df), and the leave-one-band-out range. Coherence: higher is better. LSD (dB): lower
is better.

| Input and measure | Estimate [90%] | Bands +/− | Leave-one-band-out |
|---|---|---|---|
| **htdemucs, 1–3 kHz coherence (primary)** | **+0.0034 [−0.0021, +0.0088]** | 8 / 6 | +0.0008 to +0.0043 |
| **htdemucs, LSD (primary)** | **−0.24 [−0.66, +0.17]** | 3 / 11 | −0.36 to −0.09 |
| htdemucs, coherence, mean of 3 bands | +0.0018 [−0.0013, +0.0049] | 8 / 6 | +0.0004 to +0.0025 |
| htdemucs, coherence 80 Hz–1 kHz | +0.0012 [−0.0029, +0.0053] | 9 / 5 | −0.0005 to +0.0022 |
| htdemucs, coherence 3–8 kHz | +0.0008 [−0.0003, +0.0019] | 11 / 3 | +0.0004 to +0.0011 |
| htdemucs without the 4 high-bleed parts, 1–3 kHz | +0.0037 [−0.0018, +0.0092] | 8 / 6 | +0.0011 to +0.0046 |
| htdemucs without the 4 high-bleed parts, LSD | −0.30 [−0.72, +0.11] | 3 / 11 | −0.42 to −0.15 |
| BS-Roformer (19 parts, 9 bands), 1–3 kHz | +0.0062 [−0.0001, +0.0125] | 8 / 1 | +0.0031 to +0.0071 |
| BS-Roformer, LSD | −0.56 [−0.94, −0.18] | 0 / 9 | −0.63 to −0.38 |
| htdemucs on the same 19 parts, LSD (descriptive, from the audit) | −0.43 [−1.03, +0.17] | 1 / 8 | −0.64 to −0.20 |
| Amp track on the same 19 parts, LSD (descriptive, from the audit) | −0.47 [−0.77, −0.18] | 0 / 9 | −0.52 to −0.33 |
| Amp track, 1–3 kHz | +0.0103 [+0.0012, +0.0195] | 8 / 6 | +0.0066 to +0.0119 |
| Amp track, LSD | −0.26 [−0.51, −0.02] | 2 / 12 | −0.35 to −0.16 |
| htdemucs − amp track (difference in differences), 1–3 kHz | −0.0070 [−0.0146, +0.0007] | 4 / 10 | −0.0081 to −0.0030 |
| htdemucs − amp track, LSD | +0.02 [−0.29, +0.33] | 6 / 8 | −0.09 to +0.15 |
| BS-Roformer − amp track, 1–3 kHz (descriptive, added) | −0.0069 [−0.0195, +0.0057] | 4 / 5 | −0.0088 to −0.0006 |
| BS-Roformer − amp track, LSD (descriptive, added) | −0.09 [−0.47, +0.29] | 4 / 5 | −0.18 to +0.08 |

(Bands +/−: bands with a positive / negative mean difference.)

- **The levels** (band-weighted, for orientation only):

  | | htdemucs 1–3 kHz | htdemucs LSD | BS-Roformer 1–3 kHz | BS-Roformer LSD | Amp track 1–3 kHz | Amp track LSD |
  |---|---|---|---|---|---|---|
  | C′ (= control) | 0.161 | 6.64 | 0.203 | 7.42 | 0.318 | 5.07 |
  | Separator-robust | 0.165 | 6.40 | 0.209 | 6.86 | 0.328 | 4.81 |

- **Share of C′'s amp-track − stem gap closed:** 2.2% in 1–3 kHz coherence, 15.5% in LSD.

**Per fold (descriptive; 3–10 parts in 3–4 bands each):**

| Fold | Parts | htdemucs 1–3 kHz [90%] | htdemucs LSD | BS-Roformer LSD | Amp track 1–3 kHz | Amp track LSD |
|---|---|---|---|---|---|---|
| 0 | 6 | +0.014 [−0.007, +0.034] | −0.48 | −0.60 | +0.030 | −0.48 |
| 1 | 10 | +0.001 [−0.005, +0.007] | +0.11 | −0.20 | +0.001 | +0.06 |
| 2 | 3 | +0.001 [−0.013, +0.014] | −0.47 | −1.20 | +0.005 | −0.36 |
| 3 | 5 | −0.005 [−0.009, −0.000] | −0.17 | −0.23 | +0.002 | −0.31 |

The per-fold LSD and amp-track columns were computed from `eval-*.json` with `report`'s own
`contrast` function; `report` itself gives only the per-fold 1–3 kHz row.

## Reading

- **The per-fold rows are descriptive.** Each holds 3–10 parts in 3–4 bands; their intervals
  are wide and fold 3's "negative" coherence row is three bands. Fold 0 (whose library is mostly
  Telefunken, 11 of 12 parts, and whose parts are all Cambridge) gains most in 1–3 kHz coherence
  on both the stem and the amp track and in amp-track LSD, and about as much as fold 2 in stem LSD:
  the opposite of the concern the plan raised about it. (The plan's Limits says fold 0's four
  Cambridge bands are all left out or held for validation; in fact Starnes And Shah's
  cambridge-Prodigal is in fold 0's training library.)
- **Absolute LSD is not quality.** It measures how far the long-term spectral envelope is from
  the true DI's, mean offset removed, over 80 Hz–8 kHz. A 0.24 dB smaller RMS envelope error is a
  small change; nothing here says it is audible or that it steers a search.
- **The amp track gains as much as the stem.** The plan said such a result would point to the
  extra PR12 fine-tune rather than the augmentation. Two things limit that reading:
  - **The control can't separate them here.** Its own selection rule kept step 0 on every fold,
    so the control evaluated is C′ itself, and "separator-robust − control" equals
    "separator-robust − C′". What a PR12 fine-tune *without* the augmentation does to the 24
    parts at 250–750 steps was never measured on them.
  - **The control's curves are consistent with, but weak evidence against, "it's just more
    fine-tuning":** on the held-out separator validation, more PR12 fine-tuning without the
    augmentation was worse than C′ at every checkpoint on every fold, while the main arm was
    better at its best checkpoint (and most others; it was worse than C′ at fold 2 step 1,250 and
    fold 3 step 1,750). But sepval's inputs are PR12 renders plus a separator's |G| and residual:
    the main arm trains on exactly that and the control never does, so the control getting worse
    there is expected. It says little about what plain PR12 fine-tuning, re-warmed to 1e-4, does
    to real amp tracks.
  - **A third reading fits both:** half the augmentation is a linear colouration (the
    separator's |G|), and real amp tracks are coloured relative to PR12 renders too. A rebuild
    that learned to ignore colouration would gain on both inputs alike, which is what the LSD rows
    show (in LSD the difference in differences is about zero), and with the main arm doing worse
    than the control on clean PR12 crops. That reading is a hypothesis.
  - **So:** the evaluation gain can't be attributed to stem robustness specifically. A cheap
    zero-render check would be to evaluate the control's `fold{f}-last.pt` networks on the 24
    parts; it is not declared and was not run. Only the best and last checkpoints were saved, so
    it could use only step 1,500, at a different point of the learning-rate schedule from the main
    arm's best steps (250–750).
- **Coherence barely moves.** The 1–3 kHz gain is 2% of the amp-track − stem gap. The fine
  structure a stem destroys isn't recovered; what moves is the envelope.
- **BS-Roformer's envelope gain** is on 9 bands, sets 1–2 only, and is matched by the htdemucs
  and amp-track rows on the same parts (above). Both separators' stems (htdemucs_6s and
  BS-Roformer, mix and instrumental) of other folds' parts were in the training library, so
  neither row tests an unseen separator.
- **What it is worth:** experiment 1b put the reachable gain in local ranking from a cleaner
  rebuild at up to about +0.12. Whether a 0.24 dB envelope gain buys any of that is what the
  render test answers. Better fine structure didn't steer better before (experiment 4).

## Leak and rule checks (from the stored data)

- No evaluation part's band is in its network's library entries (training or validation),
  asserted in `evaluate` and re-checked from `config.json`.
- Set 3's stems are not in the library (only sets 1–2 are usable).
- The separator validation used only held-out training-fold bands, whose cache rows left
  training (`fit` logs: 2,715–2,788 rows per fold removed).
- No held-out data: no Guitar-TECHS P3. The PR12 cache's 1,335 Guitar-TECHS P1 rows train every
  fold, as in C′ (declared in the C′ folds plan).
- Development data only: step 3's 24 parts are evaluated (Honey out). Honey is in the library
  although it is out of the evaluation (Swatkins band: training for fold 1, validation for folds
  2–3). That is allowed by the plan; it is disclosed here.
- The four evaluation folds' library bands sit in the same fold under `TR.k3_folds()` and
  `docs/song-settings-folds.json`.

## Not done from the plan

- **The Mega-53 input row** (amendment 1, "not taken tonight") was not added; it waits for 1c's
  report. The render test (amendment 4 of the local-objective plan) uses Mega-53 instead.
- **The clean validation curve has no step-0 point,** although the plan asks for both curves at
  step 0.

## Renders

**Zero.** About 3.7 hours of MPS (main arm 2.1 h, control 1.6 h) and three evaluation passes (C′'s
baseline at 00:05, the main arm and the control).
