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

## Experiment 1c: a real separator (Mega-53) in 1b's matched design

Run under [amendments 3 and 3a](local-objective-plan.md). C′ rebuilds Mega-53's guitar stem, and the
renders are scored against that same stem. **Everything here is on the instrumental context:**
both separators saw the record with its vocal tracks removed, as step 3's stems did. A product gets
the full mix.

- **Renders used: 3,528,** exactly the 3,528 expected (72 cells × 48 + 72 warm-ups). Every cell's S
  matched its warm-up within 1.4e-5; FLAC against float on S: 144 checks, largest 2.8e-5, none over
  0.005.
- **Separation was paused once and resumed cleanly.** It stopped before
  telefunken-First_Offering-GTR_1 when a training job started (the memory gate's training blocker),
  after 16 parts. The resumed run did the other 8. Each part appears once in the logs, the rebuild
  and the scoring (72 cells, each scored once), and every cell has 49 renders with one warm-up (none
  re-rendered). So nothing was skipped or run twice.

| | Cross-half local Spearman |
|---|---|
| Today's objective (C′ / htdemucs stem) | 0.289 [0.081, 0.497] |
| **Mega-53 matched (C′ from Mega-53 / Mega-53)** | **0.398 [0.205, 0.591]** |
| 1b matched (C′ from the amp track / the amp track) | 0.541 [0.375, 0.707] |
| Ceiling (true DI / amp track) | 0.864 |

**The headline, on the instrumental context: Mega-53 − today's objective is +0.109 [+0.058,
+0.160]. The declared reading is "above".**
- 11 of 14 bands are positive; leaving out each band in turn gives +0.097 to +0.127.
- Reliable-pair accuracy: +0.056 [+0.031, +0.082] (0.688 against 0.631).
- **It recovers about 43% of 1b's separator gain:** 0.43 [0.26, 0.70] (Fieller, 13 df; leaving out
  each band, 0.35 to 0.47). On reliable-pair accuracy it is 0.44 [0.29, 0.65].
- **It stays below 1b's amp-track cell:** Mega-53 − 1b is −0.143 [−0.239, −0.047] on all of Σ, and
  −0.162 [−0.237, −0.086] on Cambridge only.
- Every amp and class is above 0 (+0.08 to +0.14).

**Bleed and leak rows** (all of Σ; each share has its numerator and denominator on the same cells):

| Row | Cells | Bands (df) | Mega-53 − current | 1b − current | Share of 1b's gain |
|---|---|---|---|---|---|
| (a) all of Σ: the declared reading | 72 | 14 (13) | +0.109 [0.058, 0.160] | +0.252 [0.139, 0.365] | 0.43 [0.26, 0.70] |
| (b) no high bleed | 60 | 14 (13) | +0.109 [0.060, 0.159] | +0.227 [0.127, 0.326] | 0.48 [0.29, 0.77] |
| (c) no moderate or high bleed | 42 | 12 (11) | +0.144 [0.072, 0.217] | +0.253 [0.145, 0.360] | 0.57 [0.28, 1.06] |
| **(d) Cambridge only** | 39 | 11 (10) | +0.112 [0.065, 0.158] | +0.273 [0.162, 0.385] | **0.41 [0.32, 0.52]** |
| Telefunken only (descriptive) | 33 | 3 (2) | +0.101 [−0.23, +0.44] | +0.174 [−0.49, +0.83] | 0.58, unbounded (whole line) |
| Without the MUSDB18-train bands | 63 | 12 (11) | +0.115 [0.058, 0.171] | +0.265 [0.135, 0.396] | 0.43 [0.25, 0.76] |

- The direction rule gives the same (b), and for (c) +0.113 [0.041, 0.185] on 13 bands (48 cells),
  share 0.49 [0.19, 0.92].
- On the bleed parts 1b is not a separator ceiling (a separator can shed bleed the amp track
  carries), so a share above 1 is possible and not an error. Several upper bounds here exceed 1.
- **The reading stays on (a). (d), Cambridge only, is where the share reads cleanest:** there 1b
  really is a perfect-separator cell, and the share is 0.41 [0.32, 0.52].
- Dropping bleed or the bands htdemucs trained on doesn't shrink the gain; it is +0.11 to +0.14 on
  every row with enough bands.
- **Fieller's shapes:** a bounded interval on rows (a)–(d) and without MUSDB18-train. Telefunken only
  is the whole line (its 1b gain is undecided on 3 bands). Near S it is also the whole line (below).

**Where the gain comes from: on the point estimates, mostly from scoring against Mega-53's stem;
neither part is decided on its own.**
- Reference only (experiment 1's C′ renders scored against Mega-53): +0.096 [−0.029, +0.222] over
  today's objective.
- Rebuild only (C′ of Mega-53, scored against the htdemucs stem): −0.027 [−0.134, +0.079]. This
  breaks the stem errors' cancellation (experiment 1), so a negative reading is expected and is not
  evidence that the rebuild hurts.
- Mega-53 − reference only: +0.013 [−0.088, +0.114].
- Interaction: +0.040 [−0.123, +0.203], undecided. The split depends on the order: taken via
  rebuild only first, the reference step is +0.136.
- In 1b about half the gain came from each. Rebuilding from Mega-53 has neither been shown to help
  nor ruled out: on top of the reference it is +0.013 [−0.088, +0.114].
- The gcc-lag diagnostic changes nothing (0.398 either way).

**The subsets (descriptive):**
- **Right around S, no gain detected:** −0.002 [−0.049, +0.045]. Even the perfect stem's gain there
  is undecided (+0.085 [−0.03, +0.20]), so the share is unbounded (whole line).
- K_S points (where the true search goes): +0.122 [+0.045, +0.199]; share 0.61 [0.32, 1.46].
- Arm A's own points: +0.066 [−0.041, +0.173], undecided; share 0.21 [−0.23, +0.46].
- **Without arm A's points (the robustness row): +0.110 [+0.052, +0.168];** share 0.54 [0.29, 1.18].
- Per band, the gain runs from −0.12 (Doom Flamingo) to +0.27 (Eggy).

**The stems** (gain-fitted SNR against `reference.wav`, per part, from the separation log):
- Mega-53 is higher on 23 of 24 parts: median 3.97 dB against htdemucs's 2.13; median paired gain
  +0.68 dB (range −1.42 dB on First_Offering GTR_2 to +7.72 dB on Signs).
- Its biggest gains are on Telefunken parts (+1.9 to +4.7 dB on 7 of 11) and on Signs.
- Above 6 kHz it is quieter than htdemucs: median −5.7 dB (−36 to +4 dB).
- Timing: every Mega-53 crop sits at GCC 0 against the htdemucs stem. On the screen's 5 parts it
  matches the screen's stems exactly.
- Separation took 78–96 s per 30-s context on the CPU (33 minutes of separation for 24 parts),
  against htdemucs's about 15 s.

**The rebuild checks (amendment 2a's):** all 24 rebuilds sit at GCC 0 against C′'s stem rebuild
(limit 3 samples) and at −22.9 LUFS (limit ±0.05). The rebuild's GCC against the Mega-53 crop reads
either 0 or −52 to −55 samples. 1b's rebuilds against the amp track show a similar split (0 or −51
to −54), and the gcc-lag diagnostic shows it doesn't matter.

**What it means for arm A.**
- **On local fidelity, a real separator (Mega-53) closes about 43% [26%, 70%] of the perfect-stem
  gain** (0.41 [0.32, 0.52] on the Cambridge-only row), on the instrumental context. That is about
  0.11 of cross-half local Spearman, out of 1b's 0.25.
- **It does not by itself show a song-level gain.** That needs arm A's song test with Mega-53 in the
  loop. Right around S, where a local search starts, no gain is detected (−0.002 [−0.049, +0.045]).
- Per the declared reading, the product path is to switch the separator, after a fresh-draw check
  on parts outside the 24 (full mixes with vocals, both separators), weighing its cost (about 5–6×
  htdemucs's CPU time).
- The decided configuration is the matched one (rebuild and reference both from Mega-53).
  Reference only, the cheaper form, reads +0.096 [−0.029, +0.222], undecided; whether the rebuild
  source matters is open.
- This is a further unblinded, development use of the same 24 parts and Σ, read after experiments 1
  and 1b. The truth is the judge, not listening.

Audited 2026-10-17 by an independent agent, which recomputed every figure from the stored scores
(all match; pairing, df and Fieller shapes correct; no part or cell skipped or run twice); changes:
the decomposition is no longer read as settled (neither part decided; rebuild only's negative
reading explained), "no gain" near S became "no gain detected" with its interval, the 43% now
carries its interval and the declared "above" consequence, share above 1 noted on the bleed parts,
cell counts added to the bleed rows.
