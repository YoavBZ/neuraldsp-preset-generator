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

## Experiment 1d: the separator-robust rebuild in 1b's matched design

Run under [amendments 4, 4a and 4b](local-objective-plan.md), 2026-10-17 09:21 to 10:38 (commit
`d71367b`). The four separator-robust networks of the [separator-robust C′
readout](cprime-sep-results.md) (`models-sep-f{f}`, sha256-pinned) replace C′ in the rebuild;
nothing else changes. Two cells (DIs) on the frozen Σ (`ee91f710947dbb5c`):
- **`csep_stem`:** the network rebuilds each part's htdemucs stem, scored against that stem. It is
  today's objective with only the network changed.
- **`csep_mega53`:** the network rebuilds 1c's Mega-53 crop, scored against that crop. It is 1c's
  cell with only the network changed.

**Everything here is on the instrumental context** (the record's vocal tracks removed, as step 3's
stems and 1c). Artefacts: `~/ndsp-presets/learn/local-objective/report-1d.json`,
`logs/report1d.log`, `logs/run1d.log`, `logs/rebuild1d-*.log`, `logs/render1d-*.log`,
`logs/score1d.log`.

**Plumbing: all gates passed.**
- **Renders used: 7,200,** exactly the 7,200 expected: 3,528 per DI (72 cells × 48 + 72 warm-ups)
  and the 144 comparator renders. Every cell of each DI was scored once; none was skipped or
  re-rendered. Renders took 61 minutes (09:22–10:23) and scoring 15, against the planned 1 h and
  0.3–0.45 h.
- **The renderer against the stored comparators (4a, item 4):** C′'s stem rebuild at S, rendered
  once per cell (a warm-up, then S) and scored on today's objective, matched experiment 1's stored
  score on both halves in all 72 cells; largest deviation 3.3e-5 (limit 0.005), none over.
- **S against the cell's warm-up:** 0.0 on every `csep_stem` cell; on `csep_mega53` at most 2.6e-6
  (5 of 72 cells non-zero), all far under 0.005. **FLAC against float on S:** 144 checks per DI,
  largest 2.3e-5 (`csep_stem`) and 1.2e-4 (`csep_mega53`), none over 0.005.
- **The rebuilds:**
  - Both identity checks passed: C′ through the generalised rebuild reproduces the stored C′
    rebuilds within 1.8e-7 on the stem and exactly 0 on Mega-53 (4a's pre-run read 1.7e-7; the
    fresh rerun under 4b reads 0).
  - On both sources all 24 rebuilds sit at GCC 0 against C′'s stem rebuild (2a's check), and within
    0.05 LU of C′'s rebuild of the same source (4b's rule). The largest gap is magilla's 0.002 LU
    (−23.020 against −23.018); every other is about 1e-14. The log line "at −22.9 ± 0.05 LUFS" in
    `run1d.log` is a stale message; the check that ran is the comparator-relative one.
  - Every part logged its fold's pinned sha256 (the files on disk hash to the pins), and the leak
    assertions (parent pool, fine-tune caches, residual library) passed.
- **The first launch stopped at the stem rebuild's level check** (magilla, zero renders); amendment
  4b's comparator-relative rule was declared and reviewed before the relaunch.

| | Cross-half local Spearman |
|---|---|
| **Separator-robust rebuild of the htdemucs stem / that stem (`csep_stem`)** | **0.162 [−0.017, +0.342]** |
| Today's objective (C′ / htdemucs stem) | 0.289 [0.081, 0.497] |
| **Separator-robust rebuild of Mega-53 / Mega-53 (`csep_mega53`)** | **0.347 [0.192, 0.503]** |
| 1c: C′ from Mega-53 / Mega-53 | 0.398 [0.205, 0.591] |
| 1b: C′ from the amp track / the amp track | 0.541 [0.375, 0.707] |
| Ceiling (true DI / amp track) | 0.864 |

**The two declared primaries (row (a), all of Σ, 14 bands, 13 df). Both estimates are negative;
neither interval excludes 0 on the declared row (P1's top is +0.003, P2's +0.065). No gain is
detected, and P1 rules out more than a negligible one.**
- **P1, the network on today's stem: `csep_stem` − today's objective −0.127 [−0.256, +0.003].**
  - 11 of 14 bands are negative; leaving out each band in turn gives −0.154 to −0.074.
  - Reliable-pair accuracy: −0.036 [−0.095, +0.024]. Part-weighted −0.124 [−0.214, −0.033]; that
    interval treats parts as independent and is not the declared one.
  - Its share of 1b's +0.252: −0.50 [−1.31, +0.01] (Fieller, 13 df).
- **P2, the network on Mega-53: `csep_mega53` − 1c's mega53 cell −0.051 [−0.166, +0.065].**
  - 9 of 14 bands negative; leaving out each band, −0.077 to −0.003.
  - Reliable-pair accuracy −0.020 [−0.066, +0.025]; part-weighted −0.057 [−0.136, +0.023].
  - Its share of the 1b − 1c gap (+0.143): −0.36 [−2.11, +0.45].
- **Read with the plan's multiplicity note in mind:** neither primary is promoted. Neither is a
  positive estimate, so the plan's "build on a positive estimate" branch has nothing to build on.

**Also (not primaries; not corrected for multiplicity):**
- **The stacked route against today's objective** (`csep_mega53` − current): +0.058 [−0.071,
  +0.188]; 5 of 14 bands negative; reliable-pair accuracy +0.036 [−0.019, +0.091]. Its share of
  1b's gain is 0.23 [−0.36, +0.72], against 1c's 0.43 with C′. It is a positive estimate because
  Mega-53 helps (+0.109 in 1c); on the point estimates the network takes some of that back (P2).
- **Each cell against 1b:** `csep_stem` −0.379 [−0.544, −0.213], `csep_mega53` −0.193 [−0.329,
  −0.058].
- **The interaction, P2 − P1: +0.076 [+0.031, +0.121]** (12 of 14 bands positive; part-weighted
  +0.067 [+0.028, +0.105]; reliable-pair accuracy +0.015 [−0.017, +0.047]). It describes where the
  network costs less (on Mega-53's stem than on htdemucs's), not a gain.
- **`csep_mega53` − `csep_stem`** (Mega-53's gain with the network in both): +0.185 [+0.117,
  +0.253], all 14 bands positive. Mega-53's advantage over htdemucs holds; it is larger here than
  with C′ (+0.109) because, on the point estimates, the network costs more on the htdemucs stem.

**The diagnostics** (each against its C′ counterpart from 1c):
- **The network's rebuild of the htdemucs stem, scored against Mega-53** (1c's better reference):
  0.320, against C′'s 0.385 (1c's reference only): −0.065 [−0.180, +0.050].
- **The network's rebuild of Mega-53, scored against the htdemucs stem** (rebuild only): 0.142,
  against C′'s 0.262: −0.120 [−0.241, +0.001].
- **The gcc lag changes nothing:** 0.162 and 0.347 either way.
- All four point estimates of the network against C′ (two primaries, two diagnostics) are
  negative. None of the intervals excludes 0, and they share the network, the parts and Σ, so they
  are not independent: the network did not do better whichever stem it rebuilt or was scored
  against.

**Bleed and leak rows** (as amendment 3a; each row's cells and bands; df = bands − 1):

| Row | Cells | Bands | P1: `csep_stem` − current | P2: `csep_mega53` − mega53 | Stacked: `csep_mega53` − current |
|---|---|---|---|---|---|
| **(a) all of Σ: the declared row** | 72 | 14 | −0.127 [−0.256, +0.003] | −0.051 [−0.166, +0.065] | +0.058 [−0.071, +0.188] |
| (b) no high bleed | 60 | 14 | −0.114 [−0.241, +0.013] | −0.039 [−0.154, +0.077] | +0.071 [−0.052, +0.193] |
| (c) no moderate or high bleed (cell rule) | 42 | 12 | −0.107 [−0.258, +0.044] | −0.046 [−0.182, +0.091] | +0.099 [−0.049, +0.246] |
| (c) direction rule | 48 | 13 | −0.118 [−0.256, +0.021] | −0.031 [−0.155, +0.093] | +0.082 [−0.057, +0.221] |
| (d) Cambridge only | 39 | 11 | −0.115 [−0.281, +0.051] | −0.036 [−0.186, +0.114] | +0.075 [−0.081, +0.231] |
| Telefunken only (descriptive) | 33 | 3 | −0.171 [−0.405, +0.063] | −0.104 [−0.218, +0.011] | −0.003 [−0.444, +0.438] |
| Without the MUSDB18-train bands | 63 | 12 | −0.143 [−0.295, +0.009] | −0.058 [−0.195, +0.079] | +0.057 [−0.096, +0.209] |

- (b) is the same under the direction rule (60 cells, 14 bands).
- **No row changes the picture:** P1 is −0.11 to −0.17 on every row and P2 −0.03 to −0.10; bleed
  and the bands htdemucs trained on don't explain it.
- **Shares on the Cambridge-only row,** where 1b is a true perfect-separator cell: `csep_stem`
  −0.42 [−1.24, +0.19], the stacked route 0.28 [−0.39, +0.77]. Fieller's shapes: bounded intervals
  for P1's and the stacked route's shares on every row except Telefunken only (whole line). P2's
  share (of 1b − 1c) is two rays on (c) cell rule and on Telefunken only.

**The subsets (descriptive):**

| Subset | P1 | P2 | Stacked |
|---|---|---|---|
| Right around S | −0.046 [−0.152, +0.060] | +0.012 [−0.078, +0.101] | +0.010 [−0.099, +0.119] |
| K_S points (where the true search goes) | **−0.094 [−0.165, −0.022]** | −0.071 [−0.160, +0.018] | +0.051 [−0.050, +0.152] |
| Arm A's own points | −0.042 [−0.129, +0.045] | +0.006 [−0.072, +0.085] | +0.072 [−0.058, +0.202] |
| **Without arm A's points (the robustness row)** | **−0.181 [−0.335, −0.028]** | −0.086 [−0.217, +0.045] | +0.025 [−0.119, +0.168] |

- On K_S and without arm A's points, P1's interval is below 0 (P1's share of 1b's gain there:
  −0.47 [−1.58, −0.12] and −0.88 [−2.91, −0.13]). These are descriptive subsets, not the declared
  row.
- Right around S, where a local search starts, nothing is detected either way, as in 1c (shares
  unbounded).

**Where the loss sits (descriptive, post hoc):**
- **By class it sits in crunch,** which is only 5 parts in 5 bands: P1 −0.291 [−0.63, +0.05] crunch
  against −0.035 clean; P2 −0.220 [−0.51, +0.07] crunch against +0.043 clean. Within crunch it is two
  parts: Eat The Feeder's Today's_The_Day (P1 −0.82) and Magician's Nephew's get-out-of-bed
  (−0.50); the other three crunch parts are −0.01 to −0.10.
- By amp, P1 is −0.10 to −0.15 on all three.
- **Per band, three bands carry most of it:** Eat The Feeder (P1 −0.82, P2 −0.67), Magician's
  Nephew (−0.50, −0.41) and Doom Flamingo (−0.31, −0.16), 92% of P1's band sum. **Without those
  three, P1 is −0.013 [−0.087, +0.060] and P2 +0.048 [−0.016, +0.113]** (11 bands). On the other
  side: Zeno (+0.23, +0.18), Adam Buckley (+0.18, +0.29) and The Travelling Band (+0.04, +0.16).
  No single band sets the sign (leave-one-band-out above), but two or three do.

**The reading (estimates; no bars).**
- **The readout's small envelope gain shows no sign of carrying to local ranking.** The
  [separator-robust readout](cprime-sep-results.md) found the network's rebuild slightly closer to
  the true DI, inside the noise on the stem (LSD −0.24 dB [−0.66, +0.17], 1–3 kHz coherence +0.003
  [−0.002, +0.009]) and decided only on the amp track's LSD (−0.26 [−0.51, −0.02]). Rendered and
  ranked, both primaries are negative estimates, and their upper bounds rule out gains above +0.003
  (P1) and +0.065 (P2). On the htdemucs stem it points the other way: P1 is −0.127, and below 0 on
  K_S and without arm A's points, though mostly from three bands.
- **No gain to build on.** "Learn from any improvement" applies to positive estimates; both
  primaries and both diagnostics are negative. The only positive estimates are the stacked route
  (Mega-53's own gain, smaller than with C′), P2 near S and on arm A's points (+0.01, both
  undecided), the clean class on Mega-53 (+0.043) and a few bands. None is a reason to put this
  network in the rebuild.
- **Keep C′ in the rebuild.** The separator lever from 1c (Mega-53 with C′) stands as it was; this
  network adds nothing to it.
- **What it can't say:**
  - Whether a differently trained robust rebuild (a larger residual library, more separators, or
    one selected on a ranking-based validation) would help; this tests one fine-tune recipe, one
    seed per fold.
  - Without a renders-level control (a PR12-only fine-tune) the result can't be pinned on the
    augmentation rather than the extra fine-tuning. The optional `csep_ref` cell (4a, "not taken")
    wasn't run either, so "stem robustness" and "a generally different rebuild" aren't separated.
  - **Cell (ii) is a transfer:** the networks' residual library holds only htdemucs_6s and
    BS-Roformer residuals, so P2 tests an unseen separator. Mega-53's training data is unstated
    (a possible leak, as in 1c), and cell (ii) was added after seeing 1c's result (declared before
    any 1d render).
  - The library holds other folds' evaluation parts' stems (development use; no part's own band is
    in its network's library).
  - The readout's rebuilds ran on MPS and 1d's on CPU; 4a declined a CPU-against-MPS check, a
    small caveat on comparing the two.

**What it implies for the Mega-53 song test.** The [arm A with Mega-53 plan](arm-a-mega53-plan.md)'s
`decide-x` rule, applied to `report-1d.json["primary"]` as it stands:
1. P2 `lo90 > 0`? No: P2's `lo90` is −0.166.
2. P1 `lo90 > 0`? No: P1's `lo90` is −0.256.
3. The report is complete (72 cells and 3,528 renders per DI, every gate passed), so the rule
   reaches its third branch: **no arm X.** Both intervals contain 0 and both estimates are below
   it. `decide-x` records this in `x.json` and the ledger when that plan's runner calls it; this
   section doesn't run it.

**A lesson for future rebuild work:** one network, whose envelope gain on the stem was itself
undecided, gave no ranking gain (estimates negative, mostly from two crunch parts). That is no
evidence that envelope and coherence metrics on the rebuild predict local ranking fidelity; with
experiment 4 (better fine structure didn't steer better) it argues for judging rebuild changes on
rendered ranking (this design, or a cheaper rendered proxy) before investing in them, not on
envelope metrics alone. One hypothesis, untested: the readout found the fine-tune worse than its
control fine-tune's matched checkpoints on clean PR12 validation crops (23 of 24; C′'s own clean
value was never logged), and local ranking may lean more on the rebuild's drive-dependent detail
than on its envelope.

- This is a further unblinded, development use of the same 24 parts and Σ, read after experiments
  1, 1b and 1c and after the separator-robust readout. The truth is the judge, not listening.

Audited 2026-10-17 by an independent agent, which recomputed every figure from the stored per-cell
scores with its own scripts (all match; pairing, df and Fieller shapes correct; renders, comparator,
FLAC, identity, sha256 and level checks verified from the records; `decide-x` applied correctly);
changes: the primaries are no longer read as "ranks worse" (neither declared interval excludes 0),
the four network-against-C′ comparisons are not read as independent confirmations, the crunch and
per-band loss is shown to rest on two to three parts (with P1 and P2 without those three bands),
the envelope sentence and the lesson are scaled to one network whose envelope gain was itself
undecided, the declared limits on cell (ii) were added, the list of positive estimates was
completed, the warm-up and GCC-check wording was corrected, "per cell" became "per DI", and one
per-band digit was fixed.
