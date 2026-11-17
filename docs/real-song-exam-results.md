# The real-song exam: results

**Status:** the score rows are run and audited. The listening page is built and published privately to the user, and
the ear read will be added after the sitting. Plan: [real-song-exam-plan.md](real-song-exam-plan.md). Ledger
`pipeline-fix`: `phase_exam`, `phase_exam_inputs`, `phase_exam_answers`, `phase_exam_ear`, `phase_exam_outcome`. Code
`learn/real_song_exam.py`. Data: `~/ndsp-presets/learn/trusted-data/pipeline-fix/exam/` (`report-exam.json`,
`tables.json`, `chain/`, `research/`, `page/`) and `vreal/answers/EX-*.json`, `vreal/judge/EX-*/`. Every number here is
by the score (J0, ln distance on the held half; below 0 means the first arm is closer). Each interval is the 90%
band-clustered t over 7 bands. Nothing here has been heard yet.

## Headline (the independent audit's wording, signed)

> The shipped model path was run once, with no human help, on 10 parts from released mixes (7 bands), and scored
> against each part's real amp track. Against research it is a tie, −0.019 [−0.126, +0.087]. That is undecided: with 7
> bands, only a difference of about 0.15 or more would show. Research here mostly picked a class and an amp for the
> factory preset, so this mainly compares the model with a factory preset. Against the factory start on its own amp the
> model reads +0.06 worse (undecided). Its amp pick does no better than a random amp, while the best amp is worth about
> 0.07. The stored search labels are still far ahead (−0.19 against S, every band), so these songs have real headroom
> and the model has recovered at most about 30% of it. Nothing changes in the product; this is the baseline for later
> candidates. An ear check follows.

By the plan's declared map, M − R holds 0, so it is **undecided**. That means no product change, and this read becomes
the baseline for later candidates. The interval's half-width, 0.107, sits at the low end of the declared width (about
±0.10 to ±0.15). The audit puts the smallest effect this design finds 80% of the time (α = 0.10) at about 0.16.
Undecided is not failed.

## What ran (2026-11-17)

| Stage | What | Measured |
|---|---|---|
| CP2 | `inputs` (7 songs decoded, every crop check reproduced, T3's crop passed), `guards`, `r1-repro` (12 renders, identical), the runner check (passed on its second try; the first failed the CLI's sign-in before any model call) | |
| Research | 10 blinded headless generate runs, one per unit, one at a time | 10 of 10 passed the audit; 0 excluded, 0 aborted, no rerun; 1.7 to 2.6 min each (median 2.0) |
| CP3 chain | 41 runs of `scripts/model_preset.py`: M 10, M-crop 10, M-unity 10, M-lab 1, M-x 10; none failed | 36 min 53 s; 46 to 66 s a run; 41 X-LANCE separations |
| CP3 `c-pick`, `answers` | C's three presets through the stock-DI pick, then every arm's answers file | 98 s and 4 s |
| Hashes | the 20 `phase_exam_answers` hashes, in the ledger (PR #507, merged 14:04:10) before the first judge record (14:04:40) | |
| CP4 judge | 232 groups, each answer rendered fresh and primed in its own process | 24 min 0 s, one render shard at a time (the shard count changes only the time) |
| CP4 `report` | run once | about 1 s; sha256 `60386b47…a0a6` in `phase_exam_outcome` |

**Renders.** Each render here is one discarded priming render followed by the kept one (`audibility_measure.fresh_render`).
Plugin renders, kept renders in brackets:
- `r1-repro`: 12 (6);
- the chain: 492 (246), 12 per run for 6 kept stock-DI renders (2 stock DIs × 3 amps);
- `c-pick`: 24 (12);
- the judge: 524 (262).

In all **1,052 plugin renders (526 kept)**, inside the plan's cap of 1,400. The page needed none.

**Controls, all passed:**
- S's positive control: 60 of 60, max |ln| 1.0e-4.
- EX-S re-rendered on M's amp: identical to phase 4's S on all 11 groups (render hashes and judge values).
- L fresh against stored: 60 values, max |ln| 8.1e-5, 0 over the 0.005 tolerance; the fresh values are used.
- M against M3 on M's amp: max |ln ratio| 7.2e-9, so the output gain is not scored, as declared.
- No held half dropped (S finite everywhere) and no refused answer. Every unit has R.

**The audit** (independent, its own code, importing nothing from the exam's or `pipeline_fix`'s code) recomputed all 29
declared rows from the raw judge files. Its largest difference is 1.9e-6, from rounding t. It also confirmed:
- the hashes were merged before the first judge record, and the code that ran is the reviewed code;
- C and C-own equal `ladder/centres.json`'s entries; L equals the stored labels; M's amp is the least of its distances in 41 of 41 runs.

**Verdict: stands with corrections.** The corrections are about meaning, and they are carried below.

## The score rows (all declared rows)

| Row | Band-weighted mean [90%] | Bands better | Parts better | Part-weighted | Leave one band out (min, max) |
|---|---|---|---|---|---|
| **M − R (primary)** | **−0.019 [−0.126, +0.088]** | 4/7 | 5/10 | −0.031 | −0.049, +0.017 |
| M − S | +0.028 [−0.070, +0.127] | 4/7 | 5/10 | +0.034 | −0.013, +0.053 |
| M − S on M's amp | +0.062 [−0.043, +0.168] | 2/7 | 3/10 | +0.066 | +0.017, +0.096 |
| R − S | +0.047 [−0.053, +0.148] | 3/7 | 4/10 | +0.064 | +0.006, +0.074 |
| R − S on R's amp | +0.048 [−0.014, +0.110] | 0/7 | 0/10 | +0.054 | +0.023, +0.056 |
| R-wet − R, R − R-route | 0 exactly | | | | |
| R-route − S | +0.047 [−0.053, +0.148] | 3/7 | 4/10 | +0.064 | +0.006, +0.074 |
| M3 − S on pr12 | −0.018 [−0.187, +0.151] | 4/7 | 5/10 | +0.007 | −0.076, +0.034 |
| M3 − S on sw50r | +0.023 [−0.155, +0.200] | 3/7 | 4/10 | +0.039 | −0.034, +0.075 |
| M3 − S on ac20 | +0.096 [+0.023, +0.168] | 2/7 | 2/10 | +0.105 | +0.067, +0.113 |
| M3 − S (three amps) | +0.033 [−0.094, +0.161] | 3/7 | 3/10 | +0.050 | −0.008, +0.070 |
| M − C on M's amp | +0.005 [−0.111, +0.120] | 4/7 | 5/10 | −0.018 | −0.032, +0.037 |
| M − C-own on M's amp | −0.061 [−0.152, +0.031] | 4/7 | 6/10 | −0.053 | −0.091, −0.030 |
| M − C-pick | +0.029 [−0.072, +0.130] | 4/7 | 6/10 | +0.007 | −0.004, +0.063 |
| C − S | +0.030 [−0.065, +0.125] | 3/7 | 4/10 | +0.037 | +0.000, +0.062 |
| C-own − S | +0.062 [−0.078, +0.202] | 3/7 | 3/10 | +0.065 | +0.012, +0.105 |
| C-pick − S | −0.001 [−0.090, +0.089] | 3/7 | 5/10 | +0.027 | −0.025, +0.031 |
| M-x − M | +0.153 [−0.032, +0.338] | 3/7 | 3/10 | +0.119 | +0.073, +0.192 |
| M-lab − M (1 unit) | −0.285 | 1/1 | 1/1 | −0.285 | |
| M-crop − M | −0.013 [−0.053, +0.026] | 5/7 | 7/10 | −0.024 | −0.032, −0.005 |
| M-unity − M | +0.041 [−0.091, +0.173] | 2/7 | 4/10 | +0.024 | +0.001, +0.089 |
| M − M3's mean | −0.005 [−0.066, +0.056] | 4/7 | 5/10 | −0.016 | −0.030, +0.010 |
| M − M3's best amp (an oracle) | +0.068 [+0.007, +0.129] | 2/7 | 3/10 | +0.057 | +0.039, +0.079 |
| L − S (V-real-10) | −0.192 [−0.238, −0.145] | 7/7 | 9/9 | −0.202 | −0.204, −0.176 |
| M − S (V-real-10) | +0.040 [−0.057, +0.137] | 3/7 | 4/9 | +0.050 | +0.000, +0.066 |
| M − FT on M's amp (stored) | +0.048 [−0.087, +0.184] | 1/7 | 2/10 | +0.064 | +0.015, +0.111 |
| M − D_fix on M's amp (stored) | −0.017 [−0.197, +0.163] | 3/7 | 4/10 | −0.001 | −0.068, +0.059 |
| M − RcG on M's amp (stored) | +0.038 [−0.061, +0.137] | 3/7 | 5/10 | +0.030 | +0.002, +0.071 |

The primary's top end is +0.0875: the report's t table rounds it to +0.088, and the audit's t to +0.087. Every row but
M − R is beside it, a lead and never a verdict.

**Not declared (the audit's, a lead only): M − L on V-real-10, +0.231 [+0.133, +0.330].** 0 of 7 bands and 1 of 9 parts
are better, and every leave-one-band-out interval is clear of 0. The audit's other extra rows:
- L − S on M's amp: −0.165 [−0.213, −0.116].
- C on ac20 − S: +0.061 [−0.044, +0.167]. C-own on ac20 − S: +0.086 [−0.023, +0.195].
- C-own − C (three amps): +0.032 [−0.027, +0.091].

## How to read the rows (the audit's corrections)

1. **What M − R measures.** R equals its dry start on all 10 units: every research run left the preset at its starting
   preset. On 8 of 10 units R's render is byte-identical to S on R's amp. The 2 exceptions are research's class misses:
   - Colour Me Red ElecGtr02 (crunch, against the label's clean): R − S on R's amp +0.405.
   - Femme ElecGtr5 (heavier, on Wall Of Doom): +0.136.

   M − R splits exactly into three parts:
   - M's settings against the factory start on M's amp: +0.062 [−0.043, +0.168];
   - the model path's amp against research's: −0.033 [−0.085, +0.018];
   - research's two class misses: −0.048 [−0.110, +0.014].

   The near-zero primary is M's settings reading about 0.06 worse than the factory start, offset by a slightly better
   amp and by research's misses. It is not a test of the model's reading against research's reading: here research read
   only a class and an amp. Without Femme, M − R is −0.049 [−0.159, +0.060]. Without Colour Me Red ElecGtr02 it is
   unchanged. Neither exclusion decides it.
2. **(M − S) / (L − S) is −0.21, with a 90% Fieller interval of [−0.78, +0.29], so it is undecided.** It rules out M
   recovering more than about 30% of the label's headroom over S, by the score. It does not show that M sits on the far
   side of S.
3. **M − M3's best amp (+0.068) is above zero by construction.** M3 on M's amp is M, so the best of the three amps can
   only be as close or closer. The informative row is **M − M3's mean, −0.005 [−0.066, +0.056]**: by the score, the amp
   pick does no better than a random amp.
   - The oracle amp is worth about 0.07, and a random amp's expected loss to it is 0.073.
   - M picks the oracle's amp on 8 of 22 directions, against about 7.3 by chance.
   - The pick's cosine margins are tiny (Femme 0.0001, It Was My Fault ElecGtr1 0.0007), and M's amp differs from at
     least one input variant's on all 10 units.
4. **M3 − S on ac20 (+0.096 [+0.023, +0.168]) is marginal.** It is one of three per-amp rows, so with any multiplicity
   correction it is marginal (band sign-flip p = 0.06), and dropping Wall Of Death brings its low end to +0.000. It is
   not specific to the model: the constants lean the same way on ac20 (C +0.061, C-own +0.086, both undecided), and ac20's
   factory start is S's best amp on 13 of 22 directions. Read it as "learned settings on ac20 give up a strong factory
   start". That matters because M picks ac20 on 5 of 10 units.
5. **The loudness row is clear of 0, not "decided".** The plan declared no reading rule for it. M renders +0.75 dB
   [+0.21, +1.29] louder than S of M's class on M's amp:
   - 6 of 7 bands louder; every leave-one-band-out mean is 0.55 to 0.89 dB; the median |difference| is 0.43 dB;
   - the two parts over 1 dB are Femme +1.94 and Get Out Of Bed +1.39, and Get Out Of Bed's output gain hit its 24 dB
     ceiling.

   J0 matches level, and the page plays at −23 LUFS, so the row affects no score row and no ear read. It is a lead on
   how the loudness step, matched on the stock DIs, carries to each song's own DI.
6. **The primary's half-width, 0.107, is at the low end of the declared width,** not "inside" it.

**The strata are not read.** Clean has 2 bands (1 df), and the centred stratum is one unit (Femme). For the record, the
primary reads clean −0.159 [−0.635, +0.317] (2 bands), crunch +0.037 [−0.081, +0.154] (5), dense −0.071 (4), sparse
+0.017 (4), off-centre −0.049 [−0.159, +0.060] (6), centred +0.163 (1), V-real-10 −0.004 [−0.109, +0.101].

**M against the ladder's constants.** In the ladder, the model path read +0.061 [+0.005, +0.117] against Cen. Here M − C
on M's amp is +0.005 [−0.111, +0.120], which holds both 0 and +0.061: it is consistent with the ladder and cannot confirm
it. M − C-own is −0.061 [−0.152, +0.031], undecided. By knobs, M sits nearer C-own than C (below), yet by the score it
reads level with C and better than C-own.

## Per part (selected rows)

| Part | Band | M − R | M − S on M's amp | M − C on M's amp | M − C-own on M's amp | M − C-pick | M-x − M | M-crop − M | M-unity − M | L − S |
|---|---|---|---|---|---|---|---|---|---|---|
| It Was My Fault For Waiting ElecGtr1 | Atlantis Bound | −0.188 | −0.020 | −0.397 | −0.268 | −0.337 | +0.250 | −0.028 | +0.000 | (no label) |
| It Was My Fault For Waiting ElecGtr3 | Atlantis Bound | +0.022 | +0.076 | +0.016 | −0.047 | −0.010 | +0.157 | −0.068 | +0.038 | −0.118 |
| Signs ElecGtr3 | Zeno | −0.007 | −0.007 | −0.101 | −0.102 | −0.009 | +0.283 | −0.025 | +0.278 | −0.288 |
| Colour Me Red ElecGtr02 | Diesel13 | −0.232 | +0.172 | −0.255 | −0.123 | −0.126 | −0.176 | −0.141 | +0.024 | −0.397 |
| Colour Me Red ElecGtr03 | Diesel13 | −0.236 | +0.051 | −0.005 | +0.129 | −0.005 | +0.100 | +0.087 | −0.001 | −0.063 |
| Femme ElecGtr5 | Wall Of Death | +0.163 | +0.332 | +0.226 | −0.092 | +0.226 | −0.077 | −0.028 | +0.061 | −0.164 |
| Get Out Of Bed ElecGtr2 | Magician's Nephew | +0.023 | +0.023 | +0.149 | +0.122 | +0.149 | +0.114 | +0.098 | −0.245 | −0.167 |
| Let's Dance ElecGtr3 | Szymon Skiba | −0.140 | −0.140 | −0.027 | −0.242 | −0.027 | +0.633 | +0.003 | +0.241 | −0.130 |
| Wickerman ElecGtr1 | Eat The Feeder | +0.129 | +0.043 | +0.055 | +0.033 | +0.055 | +0.021 | −0.019 | −0.035 | −0.232 |
| Wickerman ElecGtr2 and 3 | Eat The Feeder | +0.160 | +0.134 | +0.157 | +0.057 | +0.151 | −0.114 | −0.114 | −0.123 | −0.255 |

M-lab − M on Colour Me Red ElecGtr02 is −0.285. With the label's clean class on pr12, M reads much closer than with
research's crunch on ac20, so a wrong research class hurts both R and M there (one unit, a lead). M-unity − M on It Was
My Fault ElecGtr1 is +0.0004 for two different presets (28 settings differ), not a duplicate.

## The zero-render tables (main points; `tables.json`)

- **Classes:** research's class equals the label's on 8 of 10 units. Colour Me Red ElecGtr02 went crunch (label clean),
  so it also has M-lab, EX-Cm, EX-Cownm and EX-Sm. Femme ElecGtr5 went heavier and ran as crunch (flagged).
- **Windows:** M's window overlaps the crop by 4 to 9 s. The target's DI is active through at least 0.99 of every M
  window, except Colour Me Red ElecGtr03 (0.55, from 5 candidate windows). M-x's stem is near empty on It Was My Fault
  ElecGtr1 and ElecGtr3 and Let's Dance ElecGtr3 (exposure −44, −48 and −41 dB, against −2 to −9 dB for M). On Let's
  Dance M-x − M reads +0.633. `xlst_mdxc` removes off-centre guitars by design, and its row is scoped to centred targets,
  of which there is one (Femme, −0.077).
- **Amp picks:** M picks ac20 on 5 units, pr12 on 3 and sw50r on 2, and equals R's amp on 4 of 11 slugs. The cosine
  margins run from 0.0001 to 0.044. The output gain is at its 24 dB ceiling with a shortfall on M Get Out Of Bed
  (0.41 dB), M-unity Signs (0.70) and C-pick Get Out Of Bed (1.04).
- **Knob distances:** M's mean continuous-knob distance from C-own is 0.009 to 0.029, and from C 0.014 to 0.049. M moves
  less between a unit's input variants (median 0.008 for M-crop, 0.013 for M-x and M-unity) than between units of one
  class (median 0.021, 72 pairs).

## The listening page (built 2026-11-17; the ear read follows the sitting)

Built by `page` as `phase_exam_ear` declares (build `bea9b4292fd6`, zero renders), and published privately to the user's
claude.ai so it can be sat on a phone. The page is guitar only, ties are allowed, it switches instantly, its order is
blind and seeded, and it plays at −23 LUFS:
- 12 cards: the 10 units and 2 repeats (Colour Me Red ElecGtr03, Get Out Of Bed ElecGtr2);
- R, M, C-pick and L on each card. It Was My Fault ElecGtr1 has three, since it has no stored label;
- no two presets were identical, so no letter is shared;
- every clip is the judged render, hash-checked against its judge record.

**Declared before the page was built** (the plan's dated note, commit 21d680df, after the score rows and their audit):
- **L over R is read first,** as the page's positive control.
- **M over R is expected to read "not known by ear".** If L is not heard above R, that reading means the page had no
  power, not that there is no difference.

The ear read will be added here after the sitting, with the score on the same clips beside it.

## For the goal

- **The model path as generate's default: no.** The declared rule gives no change, and the flag stays.
- **Cen as Step 3's start: not contradicted and not supported here** (C − S +0.030, M − C +0.005, C-pick − S −0.001).
  The case for Cen rests on the ladder's 400 units.
- **What this read adds, as leads:**
  - (a) the amp pick is at chance by the score, and the oracle amp is worth about 0.07, the size of the whole M − S
    question: a cheap research target;
  - (b) on these little-documented bands research reads only a class and an amp, and its two class misses cost 0.14 to
    0.41 each;
  - (c) V-real cannot resolve effects under about 0.15, so later candidates need a bigger effect or more bands;
  - (d) these songs hold real headroom: L − S is −0.192, every band.
- **Stop rule:** one build, one read. The report is written and its hash is in `phase_exam_outcome`. V-real is recorded as
  read once more. A later candidate is compared with these stored renders, hash-checked, and its read declared as such.
