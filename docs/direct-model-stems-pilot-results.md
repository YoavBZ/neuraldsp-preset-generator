# The direct model with realistic stems: pilot results (2026-10-21)

Run under the [plan](direct-model-stems-plan.md): step 2 as amendment 1 has it, and amendments 3
and 4. Amendment 2 (X-LANCE) is still a draft. Development data only; no judged renders.
- **Code:** `learn/direct_stems.py`, tests `tests/test_direct_stems.py` (branch
  `ml/direct-stems-xlance`). An independent code review came before each launch, and its fixes
  were applied.
- **Data:** `~/ndsp-presets/learn/direct-stems/`: `build/` (rows and features), `pilot/`
  (runs, `pilot-report.json`, `constant-check.json`, `curve.json`), `step4/` (parity, stems),
  `xlance-time/`, `logs/`.

## Headline

- **The pilot read `PILOT STEM`.** The stem-only model D_stem beat the old recipe D0 on the
  readout outside the new pipeline (R_out): **−0.0127 [−0.0216, −0.0039]** of E. Its
  augmentations are kept. Under the rules, the rest is built and step 3 trains D_stem.
- **But every pilot model is worse than a constant predictor.** The constant guesses each
  setting as the median of the training labels for the amp and base class. D_stem − constant
  reads +0.0128 [−0.0013, +0.0269] on R_in and +0.0178 [+0.0011, +0.0344] on R_out. This check
  is descriptive; step 3's early stop needs D below the constant.
- **More data helps:** −0.017 of E per doubling on R_in (−0.0170 [−0.0232, −0.0108]). That
  slope averages two very different seeds: about −0.028 per doubling for seed 20261042 and about
  −0.006 for seed 20261043. The log-linear projection to the full 20,311 is −0.020 [−0.047,
  +0.007] against the constant, likely optimistic given part C's flattening. That gives
  `PROBE CONTINUE`, so the plan goes on.
- **The full model is projected to land near the constant, so step 3's MODEL STOP is a real
  risk.** Neither projection's interval clears 0. The capped projection is −0.004, and the two
  seeds project to opposite signs.

## What ran

| Stage | Examples | Refused | Renders (incl. priming) | Separations |
|---|---|---|---|---|
| Pilot, mix stage (5k + 1,000 early stopping) | 6,000 | 5 (re-render differed from part C's mels) | 6,831 (831 priming) | 0 |
| V_sep, mix stage | 1,720 | 0 | 1,885 (165 priming) | 0 |
| Pilot, Mega-53 stem stage | 5,995 | 0 | about 6,830* | 5,995 Mega-53 fast (an MPS and a CPU worker); median 4.9 s each |
| V_sep, Mega-53 stem stage | 1,720 | 0 | about 1,890* | 1,720 Mega-53 fast; median 4.5 s |
| V_sep, htdemucs stem stage | 1,720 | 0 | about 1,890* | 1,720 htdemucs (CPU); median 11.1 s |

\*The stem stages re-render each example, since no audio is kept. Each worker primes once per
(section, amp) group, and the per-render counts were not logged. The figures are examples plus
groups.

- **Renders:** about 19.3k for the build, none judged. With step 4's 74 parity and diagnosis
  renders (two parity runs of 36, and 2 for the diagnosis) it is about 19.4k.
- **Mastered:** 2,994 of the pilot's mixes and 901 of V_sep's (p 0.5).
- **Build order:** the pilot mix stage ran on 2026-10-20 from 19:42 and the stem stages from
  21:00, with V_sep's Mega-53 stems following at 02:32. The rest's mix stage started at 06:14
  on 2026-10-21 and is running: 3,982 rows so far, 2 refused.

**Training** (MPS, part C's recipe, patience 4; every run trained on 4,997 examples with 998 for
early stopping, and dropped the same 5 refusals):

| Run | Seed 20261042: best / run epochs, minutes | Seed 20261043 |
|---|---|---|
| D0 | 31 / 36, 16.9 | 19 / 24, 11.1 |
| D_mix | 39 / 40, 18.4 | 31 / 36, 18.0 |
| D_stem | 30 / 35, 16.9 | 38 / 40, 19.3 |
| D_stem-noaug | 38 / 40, 18.5 | 20 / 25, 11.6 |

- **GPU time:** 2.2 h for the pilot, plus 23 min for amendment 4's four runs. About 170–180
  examples a second; no skipped steps.
- **Epoch caps:** three runs had their best epoch within 4 of the cap of 40, so they may be
  under-trained: D_mix seed 20261042 (39/40), D_stem seed 20261043 (38/40) and D_stem-noaug seed
  20261042 (38/40).

## The pilot's rules (`pilot/pilot-report.json`)

E is seed-averaged and paired per example, with 90% band-clustered t intervals over V_sep's 4
bands (3 df). Bannockburn (MUSDB18 train, 313 examples; all of the band Cnoc An Tursa's V_sep
examples) is left out.
- **R_in:** all of V_sep, Mega-53 stem: 1,407 examples.
- **R_out:** the unmastered examples, htdemucs stem: 672 examples.

| Contrast | Value | Rule |
|---|---|---|
| **D_stem − D0, R_out** | **−0.0127 [−0.0216, −0.0039]** | rule 1: D_stem beats the old recipe |
| D_mix − D0, R_out | +0.0063 [−0.0047, +0.0173] | rule 1 |
| **D_mix − D_stem, R_in** | **+0.0223 [+0.0142, +0.0304]** | rule 2: D_mix is worse, so no mix-only route |
| **D_stem − D_stem-noaug, R_in** | **−0.0115 [−0.0184, −0.0045]** | rule 4: augmentations help, kept |
| D_stem − D0, R_in | −0.0256 [−0.0346, −0.0166] | beside |
| D_mix − D0, R_in | −0.0033 [−0.0147, +0.0080] | beside |
| D_mix − D_stem, R_out | +0.0191 [+0.0069, +0.0312] | beside |
| D_stem − D_stem-noaug, R_out | −0.0066 [−0.0154, +0.0022] | beside |

**Levels (E):**

| Arm | R_in | R_out |
|---|---|---|
| D_stem | 0.216 | 0.219 |
| D_stem-noaug | 0.228 | 0.225 |
| D_mix | 0.238 | 0.238 |
| D0 | 0.242 | 0.232 |

**Scope-in contrasts** (descriptive) agree with the deciding contrasts. They use part C's keep_in
rule: 1,590 V_sep examples, intersected with each readout, leaving 1,292 on R_in and 623 on
R_out. D_stem − D0, R_out −0.0134 [−0.0225, −0.0043]; D_mix − D0, R_out +0.0062; D_mix − D_stem,
R_in +0.0222; D_stem − D_stem-noaug, R_in −0.0116.

## Against a constant predictor (`constant-check`, descriptive)

The constant is the median of the pilot's training labels per amp and base class. Its E is 0.203
on R_in and 0.201 on R_out.

| Arm (seed-averaged) − constant | R_in | R_out |
|---|---|---|
| D_stem | +0.0128 [−0.0013, +0.0269] | +0.0178 [+0.0011, +0.0344] |
| D_stem-noaug | +0.0243 [+0.0042, +0.0443] | +0.0244 [+0.0060, +0.0427] |
| D_mix | +0.0351 [+0.0256, +0.0446] | +0.0368 [+0.0228, +0.0509] |
| D0 | +0.0384 [+0.0204, +0.0564] | +0.0305 [+0.0182, +0.0429] |

- **D_stem's seeds differ:** seed 20261042 reads +0.003 on R_in, seed 20261043 +0.023.
- **D_existing against the same constant** (`pilot/dexisting-constant.json`, zero renders, CPU,
  seed-averaged; written by an uncommitted scratch script, so no repo command reproduces it): on
  V_dev (1,720 examples, 5 bands, Cnoc An Tursa's Bannockburn included) it is nominally better, −0.0143 [−0.0351,
  +0.0066], but the interval spans 0. On R_out (672 examples) it is worse, +0.0369 [+0.0182,
  +0.0556], and on R_in (1,407) worse still, +0.0595 [+0.0453, +0.0738].
- **What the readouts reward:** the pilot's gains are real against the old recipe, but these
  models have not yet learned more than the per-class centre of the labels.

## Amendment 4: the learning-curve probe (`curve`, descriptive)

D_stem (with its augmentations) was trained on nested subsets of the pilot's 5k, stratified by
band and amp: 1,250 and 2,500 examples, seeds 20261042 and 20261043. Epoch caps were 160 and 80,
so every n got the same number of optimisation steps. The constant is the 5k's throughout (the
full pool's constant is the same within ±0.0003).

| n | E − constant, R_in | R_out | Best epochs (cap) |
|---|---|---|---|
| 1,250 | +0.0468 [+0.0424, +0.0513] | +0.0508 [+0.0464, +0.0552] | 9, 21 (160) |
| 2,500 | +0.0346 [+0.0227, +0.0465] | +0.0433 [+0.0350, +0.0517] | 26, 35 (80) |
| 5,000 | +0.0128 [−0.0013, +0.0269] | +0.0178 [+0.0011, +0.0344] | 30, **38** (40) |

| At 20,311 | R_in | R_out |
|---|---|---|
| Slope per doubling | −0.0170 [−0.0232, −0.0108] | −0.0165 [−0.0226, −0.0104] |
| **Log-linear (likely optimistic, given part C's flattening)** | **−0.0200 [−0.0473, +0.0072]** | −0.0126 [−0.0405, +0.0154] |
| Capped (the last doubling's gain, halved each further doubling) | −0.0037 [−0.0204, +0.0130] | −0.0015 [−0.0255, +0.0225] |
| Seed 20261042's chain | −0.0513 [−0.0844, −0.0182] | −0.0504 [−0.0776, −0.0231] |
| Seed 20261043's chain | +0.0113 [−0.0136, +0.0361] | +0.0252 [−0.0035, +0.0539] |

- **The declared reading is `PROBE CONTINUE`.** R_in's projected interval is not entirely above
  0.
- **The advisory flag did not fire:** the projected point and the slope are both negative.
- **Caveats:**
  - The band interval does not capture the seed spread. The two chains project to opposite
    signs, and most of the projected gain comes from seed 20261042's 2,500 → 5,000 step.
  - The pilot's seed-20261043 run had its best epoch at 38 of 40, so it may be under-trained
    at 5,000.
  - Part C's curve flattened at 20k–40k (its 10k → 20k step was −0.0069), so the log-linear line
    is likely optimistic. It is not an upper bound: seed 20261042's chain alone projects to
    −0.051.
  - The seed-averaged slope (−0.017 per doubling) averages about −0.028 (seed 20261042) and
    about −0.006 (seed 20261043).

## Separately

- **X-LANCE gtr_mss on MPS** (`time-mps`, 10 audit clips): **0.988×** Mega-53 fast's time
  (4.27 s against 4.32 s a clip). Both match their stored CPU stems to at least 99 dB. gtr_mss
  now passes every leg of its screen. Switching the build to it awaits the user: it would
  re-separate the pilot's and V_sep's 9,440 examples, each re-rendered first (amendment 2,
  still a draft).
- **Step 4's parity: `PARITY OK`, under a post-hoc rule (amendment 3).**
  - The first run failed on one quiet stem half (V_sep 1002075, half B, +0.171 LU). One gating
    block sat at BS.1770's relative gate.
  - Under amendment 3 the stem LUFS tolerance is 0.03 LU (the mix's stays 0.01), and a miss
    passes only if toggling the one block at the gate explains it.
  - The stored record re-reads OK: worst unexplained difference 0.0011 LU, mel shares all 1.0.
  - Renders: 36 per parity run (two runs), 2 for the diagnosis.
- **Step 4's stems:** gate 1's 21 stage F fast stems are reused (hash-recorded). The 16
  known-answer crops were separated once with Mega-53 fast on the CPU (`step4/stems/stems.json`).

## What this means

- **The pilot's choice holds.** The separated target stem alone (D_stem) is the best of the
  four recipes, by about 0.013–0.026 of E over the old recipe. Its augmentations help.
- **More data helps,** about −0.017 of E per doubling, but the two seeds differ a lot: about
  −0.028 and −0.006. The full build's 4× more data should help; by how much is uncertain.
- **The full model is projected to land near the constant predictor, not clearly below it:**
  −0.020 if the log-linear trend holds, −0.004 if it slows as part C's did. The seeds disagree.
  Step 3's declared early stop (MODEL STOP unless D is clearly below the constant on R_in) is a
  real risk, after about 20 h of separation and 6 GPU h.
- **Under the rules the plan continues.** Whether to spend that before a cheaper check is the
  user's call.
