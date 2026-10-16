# Local objective, experiment 1: results (2026-10-16)

Run under the [plan](local-objective-plan.md) and its amendment 1. Step 0 and experiment 1 used
7,061 renders: 5 for step 0, then 7,056.
- **Independent audit:** every cell was recomputed, and 18 FLACs were re-scored by hand to 4e-16.
  The corner checks are all within 0.005. Its scripts are in
  [audits/local-objective-2026-10-16](audits/local-objective-2026-10-16/).
- **Reading these figures:** they are post-hoc development estimates. Cross-half local Spearman is
  band-weighted with 90% band-clustered intervals; 1 means perfect local ranking.

## Step 0

- **Input gain is an exact pre-gain:** the residual is −88 dB, with the compressor on. DI level and
  input gain are one thing.
- **Holding input gain fixed doesn't rescue the current objective.**
- **The three large judge_lags are real session offsets** ([lag audit](audits/judge-lag-2026-10-16/README.md)).

## Experiment 1: what ranks nearby settings

| DI \ reference | Amp track (`reference.wav`) | Separated stem (htdemucs) |
|---|---|---|
| True measure DI | **0.864** (the ceiling) | 0.351 |
| C′ rebuild | 0.409 | **0.289** (today's objective) |

**The steps that matter for a song-only product, from today's objective:**
- **A perfect DI, same stem:** +0.062 [−0.28, +0.41]. Undecided, and it inverts on 7 of 24 parts.
- **The amp track as reference, same C′:** +0.120 [−0.04, +0.28]. Undecided, leaning positive.
- **Both together:** reaches the ceiling, but that is the truth itself, which a song never gives.
- **Lag and mask:** ≤ 0.005, closed.

**The reading: the two errors partly cancel; they don't simply add.**
- C′ is rebuilt from the stem and scored against that same stem.
- Near S, today's objective ranks better than either single fix: 0.51 against 0.41 and 0.47 on S's
  neighbourhood.
- Its input-gain decisions agree best: 0.66 against 0.56 and 0.49.
- How far a stem is from its amp track predicts where the true DI against the stem fails
  (ρ ≈ −0.55), but not where today's objective fails (≈ 0).
- **An earlier version of this reading said the two errors compound. The audit corrected it.**
  The large main effects (+0.32 reference, +0.25 DI) average in the truth corner and overstate
  what either fix does alone.

**The fold-3 figure in arm A levers 2b (−0.126) is explained.** 2b's settings were all from the
true search's paths. On those points this experiment's fold 3 is −0.04, and on the full Σ +0.37.

**Σ's composition matters.**
- On S's neighbourhood each single fix is ≤ 0.
- Most of the "reference helps" signal sits on arm A's own path points, which carry a winner's
  curse against today's objective.

## What it decides

- **Drop DI-only work against the htdemucs stem,** including the DAC-9 add-on. Its best case is the
  +0.06 cell.
- **Keep the rebuild for the whole search.** Concordance is flat across step sizes, and the
  52-render, shrink-halfway recipe already limits the damage.
- **Next: improve the separator and the rebuild together.**
  - First the missing matched cell: C′ rebuilt from the amp track and scored against it, about
    3.5k renders. That is the ceiling for any separator with today's C′.
  - If it is high, test a better separator feeding both the rebuild and the reference.
  - If it stays near 0.3–0.4, the rebuild limits even with a perfect stem.

## Experiment 1b: the matched cell (C′ rebuilt from the amp track, scored against it)

3,528 renders; audited independently. Every figure was recomputed, the 24 rebuilds were re-run
within 2e-7, and the S-repeat and FLAC-against-float checks were all within 4e-5.

| | Cross-half local Spearman |
|---|---|
| Today's objective (C′ / stem) | 0.289 [0.081, 0.497] |
| **Matched (C′ from the amp track / the amp track)** | **0.541 [0.375, 0.707]** |
| Ceiling (true DI / amp track) | 0.864 |

- **Matched − today's objective: +0.252 [0.139, 0.365],** reading "above". That closes about 44% of
  the gap.
  - Leaving out each band in turn: +0.22 to +0.28.
  - 11 of 14 bands and 20 of 24 parts are positive.
  - Reliable-pair accuracy: +0.128 [0.074, 0.182].
- **It is robust:**
  - without arm A's points (winner's curse): +0.205 [0.075, 0.335];
  - without the two strongest bands: +0.188 [0.089, 0.287];
  - every amp and class is above 0.

  The robust share of the gap is about 38–44%.
- **The two cautions:**
  - **Right around S the gain is undecided:** +0.085 [−0.03, +0.20], about 24% of the gap. That is
    where a local search starts.
  - **More than half the gap remains with a perfect stem** (0.54 against 0.86). That part is the
    rebuild's own limit.
- **Where the gain comes from:** about half from scoring against a clean guitar, and half from
  rebuilding from one.

**What it decides:** a better separator, feeding both the rebuild and the reference, is a real lever
for arm A's fine ranking: up to about 40% of the gap with today's C′. Next is a real separator
(Mega-53, already on disk) in the same matched design. Then comes the rebuild's own share.
