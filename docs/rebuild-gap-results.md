# The rebuild gap: results (stages A and R, 2026-10-17)

Run under the [plan](rebuild-gap-plan.md); its amendment 1 governs. Development data only: step 3's
24 parts, Σ `ee91f710947dbb5c`. Outputs are in `~/ndsp-presets/learn/rebuild-gap/`. Stage T has
finished training. Its rendered test (TR) is running and is reported [below](#stage-tr-pending)
when it ends.
- **Audited 2026-10-17 by an independent agent (stages A and R).**
  - It recomputed every figure from the stored scores with its own code. Every figure matched
    except the chance figure for `dep_rot`.
  - It confirmed the render count, the narrowing ratio and the R2 decision.
  - **Changes:**
    - `dep_rot`'s chance figure: 6 in 24, not 9;
    - the A3 crest metric read as signed;
    - `dep_eq`'s average curve disclosed as including the recordings of 17 of the 24 parts;
    - "the same curve" made approximate;
    - `noise` set against `dep_eq` (`dep_eq` − truth added) and the reading narrowed;
    - the realised DI metrics added beside each probe, and "magnitude, not phase" argued from
      them;
    - the sustain/onset hedge carried into the headline;
    - the rotation reading's departure from the plan's declared reading stated;
    - part-weighted, per-amp and per-class figures for every probe;
    - the where section and A2's separator contrasts hedged;
    - the proxy's view of `high` corrected.
- **Reading these figures:** they are post-hoc development estimates. Fidelity is the cross-half
  local Spearman against the amp track (1 means perfect local ranking).
  - Every figure is band-weighted, with a 90% band-clustered t interval (bands − 1 df: 13 for
    stage R and A1 on all bands), the leave-one-band-out (LOBO) range, and the count of bands above
    and below 0.
- **Multiplicity:** 14 probes, 11 family contrasts and about 52 knob-family contrasts share the
  parts and Σ. Read the families, not single intervals.

## Headline

**With a perfect stem, C′'s rebuild loses ranking through its magnitude, not its phase.**
- **The loss sits mostly above 2 kHz.**
- **It is spread through the notes,** not concentrated in the attacks.
- **The error that costs is structured** (signal-dependent at time scales between 21-ms frames and
  the long-term spectrum), not its frame-level size.
- **A constant phase rotation costs a little,** about 4% of the gap.

The main figures:
- **The true magnitude under the rebuild's phase** (`mag`) recovers the whole gap: +0.313 [+0.146,
  +0.481], a share of 1.05 [0.93, 1.33]. That puts it at the truth.
- **The true phase under the rebuild's magnitude** (`phase`) recovers nothing: −0.031 [−0.071,
  +0.010]. That is despite making the waveform about as coherent with the true DI as `mag` does.
- **The true treble above 2 kHz** (`high`) recovers most of the gap: +0.241 [+0.104, +0.378], a
  share of 0.81.
- **The deployable EQ** (`dep_eq`) leans positive but is undecided: +0.133 [−0.009, +0.276], with 10
  of 14 bands above 0 and a share of 0.46 [−0.08, 0.66].
  - It needs no true DI at deployment. Its average curve, though, includes the DI recordings of 17
    of the 24 parts.
  - The measure DI is normalised to close to the same curve
    ([what it is](#dep_eq-exactly)).
- **No probe extended to R2.** `dep_eq` missed the rule by 0.0015 ([below](#r1--r2-the-stopping-rule)).

## Renders used

**R1: 16,581 renders, against at most 16,728 declared.** A crashed first attempt at the rotation
choice also rendered 27 that were lost ([failures](#operational-failures-and-fixes)), so the
machine rendered 16,608.
- Probes: 13 probes × 24 cells × 49 (48 settings and a warm-up) = 15,288. `dep_rot` rendered 21
  cells (1,029). On the other 3 its rule kept no rotation, so it reused `reb`'s renders, as
  declared.
- `dep_rot`'s rotation choice: 216 (24 × 9). The comparator: 48.
- **`report-r1.json` says 16,914.** That is wrong: `renders_used` adds each cell's warm-up a second
  time. The warm-up is already in the record's `renders` (49 per cell).
  - `renders_used` also sums all of `renders/` and `comparator/`, so TR's report will include R1
    and the same overcount.
- Stages A, A2 and B0 rendered nothing.

**Guards, all within tolerance:**
- **Comparator** (the measure DI at S against experiment 1's stored score): largest deviation
  1.0e-4 over 24 cells. The tolerance is 0.005.
- **Each cell's S against its warm-up:** largest 4.2e-6.
- **FLAC against float at S:** largest 5.8e-5.
- **The probe checks:** all 24 parts pass (`probes/check.json`):
  - levels within 2.5e-14 LU of the measure DI;
  - `noise` calibration reached within 2.9e-8 dB;
  - no mix comb-filters or cancels;
  - the alignment checks.
- **`reb` against 1b's stored scores** (the plumbing check): −0.0004 [−0.0014, +0.0005].

## Stage A: the stored data (zero renders)

### A1. Which knobs are mis-ranked (1b, all 72 cells)

**Every knob family loses about the same with a perfect stem.** The matched cell trails the
truth's own cross-half order by 0.15–0.21 in each family's 3-way agreement on S's ±1/8
neighbourhood:

| Family | Matched (1b) | Today's objective | Truth | Truth − matched | Chance |
|---|---|---|---|---|---|
| Input gain | 0.712 | 0.667 | 0.925 | +0.212 [+0.079, +0.345] | 0.333 |
| Amp gain staging | 0.753 | 0.706 | 0.919 | +0.166 [+0.071, +0.261] | 0.370 |
| Amp tone | 0.675 | 0.618 | 0.855 | +0.180 [+0.103, +0.257] | 0.397 |
| Cab and mic | 0.714 | 0.645 | 0.864 | +0.149 [+0.017, +0.282] | 0.388 |

- **Pairwise concordance on all of Σ, by dominant family:** truth − matched is +0.13 to +0.17 in
  every family, mixed pairs included. Each interval excludes 0.
- **By class (descriptive):** most of each family's gap is in the clean parts. The 3-way gap is
  0.21–0.28 on clean parts and 0.01–0.10 on crunch. On crunch, cab is 0.006.
- **By drive:**
  - pairs above S's input gain (13 bands): matched 0.688, truth 0.907, gap +0.22 [+0.08, +0.36];
  - pairs below: matched 0.670, truth 0.864, gap +0.20 [+0.09, +0.30].
  - So no drive region carries the loss.
- **Reading:** the rebuild's error is not one knob's problem. It degrades the ranking of every
  family about equally.

### A2. Five rebuilds scored against the amp track (all 72 cells)

The identity check passed: rescoring a cell of 1b's own renders reproduced its stored scores
exactly (deviation 0).

| Rebuild (source, network) | Fidelity | Matched (1b) − this |
|---|---|---|
| C′ from the amp track (1b) | **0.541** [0.375, 0.707] | — |
| C′ from Mega-53 | 0.463 [0.254, 0.673] | +0.078 [+0.008, +0.147] |
| Separator-robust C′ from Mega-53 | 0.446 [0.253, 0.639] | +0.095 [+0.027, +0.164] |
| C′ from the htdemucs stem | 0.409 [0.221, 0.598] | +0.132 [+0.010, +0.253] |
| Separator-robust C′ from the htdemucs stem | 0.400 [0.215, 0.584] | +0.141 [+0.003, +0.280] |
| True measure DI (the ceiling) | 0.864 [0.754, 0.974] | truth − 1b: +0.323 [+0.132, +0.514] |

- **Every rebuild sits far below the ceiling, even scored against the same clean reference.** The
  rebuild from the amp track ranks best of the five.
- **Two contrasts lean but are undecided:**
  - Mega-53 sources lean above htdemucs ones: C′ +0.054 [−0.045, +0.153], separator-robust +0.046
    [−0.062, +0.154];
  - the separator-robust networks lean below C′ on the same source: −0.010 [−0.078, +0.059] on
    htdemucs and −0.018 [−0.070, +0.035] on Mega-53.

### A3. Which DI properties track rendered ranking (descriptive)

**Within part** (the Spearman across the five rebuilds of A2, n = 5 per part, band-weighted).
Source and network are confounded, so this is noisy:
- **B0's proxy fidelity tracks best:** +0.435 [+0.212, +0.657], 11 of 14 bands above 0.
- **The 1-ms crest error:** +0.260 [+0.037, +0.482].
  - This metric is signed (the rebuild's crest minus the truth's), and rebuilds fall on both sides
    of 0. So a higher 1-ms crest relative to the truth went with better ranking.
  - Taken as an absolute error, the association is about −0.15 (the audit's figure): more error,
    worse ranking.
- **SNR after removing the rotation, |c| and 80 Hz–1 kHz coherence:** each about +0.22, with
  intervals touching 0.
- **LSD, 3–8 kHz coherence, and crest at 5 and 10 ms:** about 0.
- **SNR with the rotation kept:** −0.16 [−0.46, +0.13].

**Across parts** (each metric against 1b's per-part gap to the ceiling, 24 parts, Spearman, no
interval):
- 1–3 kHz coherence +0.61, quiet-frame level error −0.45, 3–8 kHz coherence +0.41, 80 Hz–1 kHz
  coherence +0.39.
  - The quiet-frame error is signed: positive means gaps filled.
- The coherence signs are counter-intuitive: more coherence went with a larger gap. That is
  probably part difficulty, not cause.
- Every other metric is within ±0.29, and proxy fidelity is −0.09.
- **Reading:** no waveform metric explains which parts lose ranking. Within a part, the proxy bank
  orders rebuilds better than any waveform metric.

### A4. The rotation split

- **Parts rotated 90° or more (14 parts, 8 bands):** 1b fidelity 0.467 [0.142, 0.792].
- **The other 10 (7 bands):** 0.581 [0.317, 0.845].
- The two are not paired and they overlap.
- By class: 10 of 19 clean parts and 4 of 5 crunch parts are rotated 90° or more.
- Stage R's `t_rot` and `rot` test the rotation directly; see below.

### B0. The proxy bank against rendered ranking (zero renders)

- **Proxy fidelity of the five rebuilds** (mean over parts, 32 draws per part): 0.47 for 1b, and
  0.34–0.39 for the other four.
  - 1b is top on both measures. The other four are ordered differently from A2.
- **Against the probes' rendered fidelity, after R1** (computed for this write-up from `b0.json`
  and the R1 scores): the within-part Spearman over 13 probes is +0.618 [+0.465, +0.771], with 13
  of 14 bands above 0.
  - `dep_rot` is built after B0, so it is not in B0.
  - The probes span from rebuild-like to truth-like, so a high correlation is the easy case.
- **Where the proxy misjudges** (mean over parts, proxy against rendered):
  - it overrates `t_rot` (0.94 against 0.84) and `mag` (0.96 against 0.85);
  - it underrates `high`'s gain: +0.17 over `rot` against +0.30 rendered, about 58%;
  - it underrates `noise` (0.74 against 0.82);
  - it **misses `dep_eq`'s gain:** 0.50 against `reb`'s 0.47, while the rendered fidelity is 0.68.
  - That matters for stage T, which trains through this proxy.

## Stage R: the oracle probes (R1, 24 cells, 14 bands)

**Construction, as declared** (the audit confirmed it against the code):
- Every probe is a DI on the measure DI's timeline, levelled to −22.9 LUFS.
- Each is scored as the truth is: against `reference.wav`, at the part's `judge_lag`, with the
  measure DI as the activity mask.
- One amp per part, 8 parts per amp. The anchors are as declared.
- **The alignment, logged per part:**
  - the lag sits −21 to +17 samples from `judge_lag` (median −5);
  - |c| is 0.51–0.88 and 80 Hz–2 kHz coherence 0.32–0.78;
  - the rotation |φ| has a median of 107°, with 14 of 24 parts at 90° or more;
  - `onset` covers 10–26% of samples (median 23.5%);
  - `mag`'s realised magnitude error is a median of 1.5 dB.
- **On the same 24 cells:** the truth is 0.850 [0.732, 0.967] and `reb` is 0.561 [0.406, 0.715].
  The gap is +0.289 [+0.104, +0.474] against `reb` and +0.299 [+0.118, +0.481] against `rot`.

### Each probe against its anchor (declared configuration)

| Probe | Fidelity | Against its anchor | LOBO | Bands +/− | Share of the gap | Reliable-pair accuracy Δ |
|---|---|---|---|---|---|---|
| `reb` (the anchor) | 0.561 | 1b stored: −0.000 [−0.001, +0.001] | | | | |
| `rot` | 0.551 | `reb`: −0.010 [−0.026, +0.006] | −0.013 to −0.003 | 7/7 | −0.03 [−0.17, 0.02] | −0.003 [−0.010, +0.004] |
| `t_rot` | 0.838 | truth: −0.012 [−0.019, −0.005] | −0.013 to −0.008 | 2/12 | — | −0.023 [−0.028, −0.018] |
| **`mag`** | **0.864** | `rot`: **+0.313 [+0.146, +0.481]** | +0.269 to +0.350 | 12/2 | **1.05 [0.93, 1.33]** | +0.202 [+0.132, +0.272] |
| `phase` | 0.520 | `rot`: −0.031 [−0.071, +0.010] | −0.044 to −0.018 | 4/10 | −0.10 [−0.33, 0.04] | −0.010 [−0.031, +0.011] |
| `low` (< 500 Hz) | 0.598 | `rot`: +0.048 [−0.031, +0.126] | +0.019 to +0.076 | 12/2 | 0.16 [−0.20, 0.35] | +0.033 [+0.009, +0.057] |
| `mid` (500 Hz–2 kHz) | 0.600 | `rot`: +0.049 [+0.007, +0.091] | +0.039 to +0.065 | 11/3 | 0.16 [0.02, 0.45] | +0.036 [+0.022, +0.051] |
| **`high`** (> 2 kHz) | **0.791** | `rot`: **+0.241 [+0.104, +0.378]** | +0.196 to +0.265 | 12/2 | **0.81 [0.59, 1.18]** | +0.112 [+0.054, +0.170] |
| `onset` | 0.671 | `rot`: +0.121 [+0.055, +0.186] | +0.098 to +0.131 | 13/1 | 0.40 [0.26, 0.71] | +0.060 [+0.035, +0.085] |
| **`sustain`** | **0.867** | `rot`: **+0.316 [+0.152, +0.480]** | +0.272 to +0.351 | 13/1 | **1.06 [0.97, 1.33]** | +0.195 [+0.129, +0.261] |
| `half` | 0.702 | `rot`: +0.152 [+0.056, +0.247] | +0.119 to +0.169 | 11/3 | 0.51 [0.31, 0.80] | +0.082 [+0.047, +0.117] |
| `noise` | 0.827 | `rot`: +0.276 [+0.117, +0.436] | +0.231 to +0.299 | 13/1 | 0.92 [0.67, 1.35] | +0.158 [+0.089, +0.228] |
| **`dep_eq`** | 0.694 | `reb`: **+0.133 [−0.009, +0.276]** | +0.086 to +0.174 | 10/4 | 0.46 [−0.08, 0.66] | +0.058 [−0.002, +0.119] |
| `dep_rot` | 0.542 | `reb`: −0.019 [−0.052, +0.015] | −0.022 to +0.000 | 5/7 | −0.06 [−0.36, 0.04] | −0.006 [−0.015, +0.004] |

- **The own-mask diagnostic (record fallback)** agrees with the declared rows to within 0.001 on
  every probe and family. For example, `mag` is +0.313 [+0.146, +0.481], `dep_eq` +0.133 [−0.009,
  +0.275] and `t_rot` −0.012 [−0.019, −0.005].
- **Against the truth on the same cells:**
  - `mag` +0.014 [−0.025, +0.053];
  - `sustain` +0.017 [−0.012, +0.046];
  - `noise` −0.023 [−0.107, +0.061];
  - `high` −0.058 [−0.145, +0.028];
  - `half` −0.148 [−0.265, −0.030];
  - `dep_eq` −0.156 [−0.236, −0.075], 1/13 bands;
  - `onset` −0.179 [−0.319, −0.039].

**Part-weighted, per amp and per class** (each probe against its anchor; per amp is 8 parts, and
crunch is 5 parts, both descriptive):

| Probe − anchor | Part-weighted | AC20 | PR12 | SW50R | Clean | Crunch |
|---|---|---|---|---|---|---|
| `rot` − `reb` | −0.007 [−0.017, +0.003] | −0.013 | +0.000 | −0.009 | +0.001 | −0.029 |
| `t_rot` − truth | −0.008 [−0.013, −0.002] | −0.012 | −0.005 | −0.012 | −0.009 | −0.017 |
| `mag` − `rot` | +0.366 [+0.175, +0.557] | +0.397 | +0.612 | +0.081 | +0.445 | +0.076 |
| `phase` − `rot` | **−0.036 [−0.065, −0.006]** | −0.069 | −0.050 | −0.003 | −0.069 | +0.038 |
| `low` − `rot` | +0.062 [−0.016, +0.140] | +0.029 | +0.139 | +0.005 | +0.066 | +0.014 |
| `mid` − `rot` | +0.049 [+0.007, +0.092] | +0.079 | +0.062 | −0.005 | +0.055 | +0.039 |
| `high` − `rot` | +0.303 [+0.146, +0.460] | +0.303 | +0.444 | +0.173 | +0.349 | +0.047 |
| `onset` − `rot` | +0.165 [+0.084, +0.245] | +0.121 | +0.236 | +0.082 | +0.174 | +0.024 |
| `sustain` − `rot` | +0.386 [+0.209, +0.564] | +0.358 | +0.618 | +0.172 | +0.428 | +0.115 |
| `half` − `rot` | +0.198 [+0.079, +0.317] | +0.140 | +0.302 | +0.086 | +0.205 | +0.057 |
| `noise` − `rot` | +0.334 [+0.156, +0.512] | +0.338 | +0.483 | +0.158 | +0.379 | +0.092 |
| `dep_eq` − `reb` | +0.184 [+0.021, +0.346] | +0.091 | +0.428 | +0.062 | +0.213 | −0.010 |
| `dep_rot` − `reb` | −0.016 [−0.037, +0.005] | −0.043 | −0.011 | +0.005 | −0.032 | +0.006 |
| *gap: truth − `reb`* | +0.354 [+0.159, +0.550] | +0.348 | +0.613 | +0.081 | +0.419 | +0.055 |

- SW50R's gap is small to begin with (+0.08), and crunch has almost none (+0.055).
- So almost all of every probe's gain is in the clean parts and on AC20 and PR12.
- `phase`'s part-weighted interval excludes 0 on the negative side. Band-weighted it is undecided.

**The realised DI metrics** (median over parts, against the measure DI; `probes/log.json`):

| Probe | SNR (dB) | LSD (dB) | Coherence 80 Hz–1 kHz | 1–3 kHz | 3–8 kHz | Crest error 1 ms (dB, signed) |
|---|---|---|---|---|---|---|
| `reb` | 1.1 | 3.3 | 0.60 | 0.39 | 0.01 | −0.13 |
| `rot` | 3.3 | 3.3 | 0.60 | 0.39 | 0.01 | −0.15 |
| `t_rot` | 2.2 | 0.0 | 1.00 | 1.00 | 1.00 | +0.04 |
| `mag` | 6.2 | 0.2 | 0.87 | 0.71 | 0.07 | +0.01 |
| `phase` | 5.9 | 3.6 | 0.80 | 0.71 | 0.47 | −0.20 |
| `low` | 6.3 | 3.2 | 0.79 | 0.39 | 0.01 | −0.19 |
| `mid` | 5.6 | 3.1 | 0.82 | 0.61 | 0.01 | −0.10 |
| `high` | 3.5 | 1.9 | 0.60 | 0.71 | 1.00 | +0.07 |
| `onset` | 4.4 | 1.9 | 0.64 | 0.38 | 0.17 | −0.13 |
| `sustain` | 8.9 | 0.6 | 0.84 | 0.69 | 0.64 | −0.03 |
| `half` | 7.5 | 2.3 | 0.86 | 0.67 | 0.38 | −0.16 |
| `noise` | 5.9 | 1.3 | 0.70 | 0.55 | 0.47 | +0.17 |
| `dep_eq` | 1.1 | 0.8 | 0.59 | 0.39 | 0.01 | +0.23 |

### The families (paired)

| Contrast | Estimate | LOBO | Bands +/− |
|---|---|---|---|
| `mag` − `phase` | +0.344 [+0.163, +0.525] | +0.292 to +0.383 | 13/1 |
| `low` − `mid` | −0.002 [−0.099, +0.096] | −0.033 to +0.033 | 4/10 |
| `low` − `high` | −0.193 [−0.311, −0.076] | −0.214 to −0.148 | 3/11 |
| `mid` − `high` | −0.192 [−0.331, −0.053] | −0.216 to −0.149 | 4/10 |
| `onset` − `sustain` | −0.196 [−0.316, −0.075] | −0.228 to −0.165 | 1/13 |
| `noise` − `rot` | +0.276 [+0.117, +0.436] | +0.231 to +0.299 | 13/1 |
| `half` − `rot` | +0.152 [+0.056, +0.247] | +0.119 to +0.169 | 11/3 |
| `rot` − `reb` | −0.010 [−0.026, +0.006] | −0.013 to −0.003 | 7/7 |
| `dep_rot` − `reb` | −0.019 [−0.052, +0.015] | −0.022 to +0.000 | 5/7 |
| `dep_eq` − `reb` | +0.133 [−0.009, +0.276] | +0.086 to +0.174 | 10/4 |
| `t_rot` − truth | −0.012 [−0.019, −0.005] | −0.013 to −0.008 | 2/12 |

### Where the probes act (A1's knob families, S's neighbourhood, against the anchor)

The full breakdown for every probe is in `report-r1.json` (`where`). The leads:
- **`sustain` raises every family, each interval above 0:** input gain +0.19 [+0.03, +0.36], amp
  gain +0.14, amp tone +0.12, cab +0.11.
- **`mag` leans the same way:**
  - amp gain +0.14 [+0.03, +0.24] and cab +0.14 [+0.02, +0.25] are above 0;
  - input gain +0.17 [−0.004, +0.34] and amp tone +0.09 [−0.03, +0.21] touch 0.
- **`high` leans the same way** (+0.05 to +0.11), with each interval touching 0.
- **`dep_eq` does not lean positive near S:**
  - amp gain −0.110 [−0.192, −0.028], with 1 band above, 5 below and 8 tied;
  - input gain −0.083 [−0.264, +0.097];
  - amp tone +0.048 and cab +0.046, both undecided.
  - The amp-gain figure is one interval among about 52 such contrasts, so it is a lean against
    gain staging near S, not a decided harm.
  - An inference, not shown: its gain on all of Σ then comes from pairs farther from S.
- **`t_rot` has no row against the truth** (`probe_where` computes none).
- **On S's neighbourhood most bands tie** with the anchor (3-way agreement is coarse), so few
  bands fall above or below 0. Read these as leans.

### What the probes say about where the rebuild loses ranking

These are oracle diagnostics on the measure DI's timeline, at the plan's resolutions (21-ms
magnitude, band edges at 500 Hz and 2 kHz, 17-ms attack windows), and read as families.

- **Magnitude, not phase.**
  - `mag` − `phase` is +0.344 [+0.163, +0.525].
  - **The cleanest evidence is `phase`.** It gives the rebuild the true phase and keeps the
    rebuild's magnitude (LSD 3.6 dB, as `rot`'s 3.3). That raises coherence with the true DI about
    as much as `mag` does (0.80 / 0.71 / 0.47 against `mag`'s 0.87 / 0.71 / 0.07), yet it recovers
    nothing. It leans negative: every LOBO value is below 0, and part-weighted it is −0.036
    [−0.065, −0.006].
  - **`mag` is not a pure magnitude swap.** Its 8 Griffin–Lim iterations pull the waveform toward
    the true DI below 3 kHz (coherence 0.87 and 0.71 against `rot`'s 0.60 and 0.39). So "true
    magnitude under the rebuild's phase" holds literally only above about 3 kHz, where `mag` keeps
    the rebuild's incoherence (0.07) and still reaches the truth.
  - Together the two say the ranking follows the short-time magnitude, and waveform coherence
    restored without it does not help.
- **The high band carries most of it.** Restoring the treble above 2 kHz recovers about 0.8 of the
  gap; below 500 Hz or 500 Hz–2 kHz, about 0.16 each. `high` beats both, at about +0.19.
  - The shares sum to about 1.1, so the bands roughly add.
  - The rebuild has almost no coherent content above 3 kHz (coherence about 0.01).
  - The 2 kHz edge is a choice of the plan, so "above 2 kHz" is resolved only that finely.
- **Spread through the notes, not concentrated in attacks.**
  - True sustain recovers the whole gap (1.06); true attacks 0.40. `onset` − `sustain` is −0.196
    [−0.316, −0.075].
  - **Per unit of signal they are not far apart.** The attack windows cover a median 23.5% of the
    samples, and sustain the rest. 0.40 at 24% coverage is no less per sample than 1.06 at 76%.
  - So sustain matters more because it covers 76% of the samples. Attacks are not unimportant.
  - The two shares sum to about 1.5, so attack and sustain do not add.
- **The error's structure costs ranking, not its frame-level size.**
  - `noise` is the true DI plus random-phase noise. It is calibrated so that its 16-band,
    frame-by-frame level error to the true DI equals r̃'s. It recovers 0.92 [0.67, 1.35] of the gap
    and sits at the truth: −0.023 [−0.107, +0.061].
  - **What `noise` does not hold equal:**
    - it keeps the whole true waveform underneath (3–8 kHz coherence 0.47 against 0.01, SNR 5.9
      against 3.3 dB);
    - its long-term spectrum is much closer to the true DI's than r̃'s (LSD 1.3 against 3.3 dB).
  - **And the long-term bias is not the whole story.** `dep_eq` removes most of the long-term
    spectral bias (LSD 3.3 → 0.8 dB) but recovers only about half the gap (0.46). It stays below
    the truth: −0.156 [−0.236, −0.075], 13 of 14 bands below.
  - So the costly error is **a structured, signal-dependent magnitude error at time scales between
    21-ms frames and the long-term spectrum.** About half of it at most is a fixed long-term EQ
    bias. An unstructured error of the same frame-level band size costs little.
  - **Against the plan's declared reading** ("`noise` close to the truth while `rot` isn't … a
    spectral loss alone won't close the gap and a ranking-aware loss is the route"): the outcome
    is the one it names, and the reading stands, with one refinement. A spectral loss that matches
    only band levels frame by frame may not be enough. A loss on the short-time magnitude
    structure, above all above 2 kHz, or one judged on ranking, is the lead.
- **Dose.**
  - `half` (halfway in log-magnitude and phase) recovers about half the gap: 0.51 [0.31, 0.80].
  - That is one point, not a curve. It is consistent with ranking recovering steadily as the error
    shrinks, rather than only near zero error.
- **The rotation costs a little, and removing it gains nothing.**
  - `t_rot` gives the true DI the rebuild's rotation. It costs −0.012 [−0.019, −0.005], with 12 of
    14 bands below 0 and reliable-pair accuracy −0.023 in all 14 bands.
  - That is decided below the truth. It is about 4% of the gap; at the interval's far end, about
    6.5%.
  - Removing the rotation from the rebuild (`rot`) gains nothing: it leans −0.010 [−0.026,
    +0.006].
  - **This departs from the plan's declared reading,** which said "`t_rot` below the truth … the
    rotation matters; then the rebuild needs a rotation fix". The departure rests on two things:
    the cost is about 4% of the gap, and `rot` shows the rebuild gains no ranking when its
    rotation is removed (at most +0.006).
  - A rotation fix is deprioritised, not ruled out.
  - A4's split (0.47 against 0.58) is therefore not mainly the rotation.

### What the deployable fixes show

- **`dep_rot` (the rotation chosen by 8 S renders) leans negative and is undecided:** −0.019
  [−0.052, +0.015].
  - It kept no rotation on 3 of 24 parts.
  - Its choice landed within 45° of the oracle rotation on 5 of 24. Chance is about 6 in 24, since
    any angle has 2 of the 8 choices within 45°.
  - With the rotation's own cost so small, there is little for it to find.
- **`dep_eq` leans positive:** +0.133 [−0.009, +0.276].
  - The interval touches 0. LOBO is +0.086 to +0.174, and 10 of 14 bands are above 0.
  - Part-weighted it is +0.184 [+0.021, +0.346]. Reliable-pair accuracy is +0.058 [−0.002,
    +0.119].
  - It closes about 0.46 of the gap, with an interval reaching below 0. It stays well below the
    truth (−0.156).
  - **What tempers it:**
    - The gain is concentrated: PR12 +0.43 against AC20 +0.09 and SW50R +0.06, and clean +0.21
      against crunch −0.01.
    - On S's neighbourhood it leans worse on gain staging (amp gain −0.110 [−0.192, −0.028]; a
      lean, given the number of such contrasts).
    - The proxy bank does not see its gain (B0).
    - Its curve overlaps the evaluated parts ([below](#dep_eq-exactly)).
  - It removes the long-term part of the magnitude error. It cannot touch the shorter-time
    structure, or the missing coherence above 3 kHz that `sustain` and `high` restore.

### `dep_eq`, exactly

`dep_eq = to_lufs(eq_to(ra, avg − (own − mean(own))))`
(`learn/rebuild_gap.py`, `build_probes`), where:
- **`ra`** is 1b's stored rebuild of `reference.wav` (`rebuilt-ref/<part>.npy`), shifted onto the
  measure DI's timeline.
  - That shift uses the true DI (the alignment lag), as every probe does, `reb` included. So the
    paired contrast `dep_eq` − `reb` does not depend on it.
  - The EQ is zero-phase, and the shift moves no spectrum.
- **`own`** is `smoothed_spectrum(ra)`: the rebuild's own long-term spectrum, 1/6-octave smoothed,
  over frames within 40 dB of its loudest.
- **`avg`** is `average-fold2.npy` (`confirm_run.AVERAGE`): the power-averaged, mean-removed
  spectrum of the PR12 cache's DIs from bands outside fold 2. It is the same file for every part.
- `eq_to` applies that gain (clipped to ±15 dB) as a zero-phase FFT filter.

**At deployment `dep_eq` needs no true DI.** It needs only the rebuild and a fixed curve.

**The curve is not independent of the evaluated parts.** The audit found this:
- `average-fold2.npy` averages 15,319 cache rows. 4,734 of them (31%) come from the DI recordings
  of 17 of the 24 parts: those outside fold 2 and the set-3 parts.
- That is 128–514 rows per part (0.8–3.4% of the average), including windows that overlap each
  part's scored 10-s excerpt.
- Leaving a part's recording out moves the curve by 0.005–0.43 dB RMS over 80 Hz–8 kHz, and by up
  to 1.6 dB in single bins.
- The effect is small, and the truth is EQ'd to the same curve. But it is a small use of the
  evaluated recordings. **A fresh-draw test needs a curve built without the test parts'
  recordings.**

**The truth follows close to the same convention.** The measure DI, which defines the ranking
here, is built by the same rule from the raw DI: `knob_ceiling.measure_di` is `eq_to(di, avg −
(own_di − mean))`.
- Its long-term spectrum sits a median 1.06 dB LSD from `avg` (0.43–4.80 dB; the ±15 dB clip binds
  on some parts). `dep_eq`'s sits 0.65 dB from it (0.40–1.00).
- So `dep_eq` does not borrow the part's true spectrum. It makes the rebuild follow close to the
  yardstick's own normalisation: the average guitar at a fixed level.
- Under that yardstick it is a fair product candidate.
- It would not be expected to carry to a truth that kept the player's own guitar spectrum. Part of
  its gain is agreement with how the truth was normalised.

### R1 → R2: the stopping rule

- **The narrowing ratio from the stored contrasts is 0.948.** That is the median of six: 0.85,
  0.86, 0.93, 0.96, 1.03 and 1.40. The audit recomputed all six.
- **A probe extends only if three things hold:** its estimate is positive, its R1 interval contains
  0, and the interval narrowed by that ratio would exclude 0.
- **Two probes were candidates:**
  - `low`: the projected lower bound is −0.027. It does not extend.
  - `dep_eq`: the projected lower bound is −0.0015. It does not extend, **by 0.0015.**
- **The family contrasts, in either direction:**
  - `rot` − `reb`'s projected upper bound is +0.005, so it does not extend;
  - `dep_rot` − `reb` and `low` − `mid` are farther from extending;
  - the others are already decided.
- **So R2 rendered nothing,** as the runner logged (`R2 extends: []`).
- This follows the declared rule exactly. **`dep_eq` is the closest undecided lead.** The plan
  already requires that any fix to ship be scored on a fresh draw of parts outside the 24 first.

## What it decides

- **The rebuild's training target is its short-time magnitude,** above all above 2 kHz, through
  the whole note. Sustain carries more only because it covers 76% of the samples.
- **Rotation fixes are deprioritised:** rotation augmentation, a rotation-invariant objective and
  `dep_rot`.
  - The rotation's cost is decided but small, about 4% of the gap.
  - Removing it gains nothing measurable.
- **What costs is a structured, signal-dependent magnitude error,** not the error's frame-level
  size.
  - A fixed long-term EQ removes at most about half of it.
  - A loss that only matches band levels frame by frame may not be enough. A loss on the
    short-time magnitude structure, especially in the treble, or one judged on ranking, is the
    lead.
- **`dep_eq` is a near-free product candidate,** leaning positive and undecided.
  - Its next step is a fresh-draw test, with an average curve built without the test parts'
    recordings.
  - Read it with its caveats:
    - its gain is concentrated on PR12 and clean parts;
    - it leans worse near S on gain staging;
    - part of its gain is agreement with the yardstick's own normalisation.
- **The proxy bank tracks the probes' order** (within part +0.62). But it underrates `high`'s gain
  and misses `dep_eq`'s. Read stage T in that light.

## Operational failures and fixes

1. **A3 failed on its first run** (13:42, `logs/metrics-failed1.log`).
   - `within_part_assoc` called `K.R.bw_stats`, which doesn't exist (an `AttributeError`).
   - Fixed in 312f3ba to use `song_readout.bw_stats`, with a test. The rerun completed at 14:18
     (`logs/metrics.log`).
   - It was a CPU analysis with zero renders. Nothing upstream changed.
2. **The rotation choice crashed at its first write** (17:11, `logs/choose-rot-failed1-{0,1,2}.log`).
   - `cmd_choose_rot` wrote its JSON into a `rotation/` folder it had not created.
   - Each of the 3 shards had rendered its first cell (9 renders, 27 in all) before the crash.
     Those results were lost and redone.
   - The original runner then logged `TR not started (lane R failed)`.
   - Fixed in 216ae4e (the folder is created first). Lane R and TR resumed at 17:17 through
     `learn/rebuild_gap_resume_r.zsh` (8c31078).
   - The rotation was chosen at 17:19, the R1 renders were done at 19:29, and the report ran at
     19:53.
   - No probe render had started before the crash, and none was rendered twice.

## Stage TR (pending)

> **Placeholder.** Stage T (the proxy-ranking fine-tune, `rank` and its matched-step `ctl`, 4
> folds) finished at 18:01. Its rendered test, TR1 (2,352 renders and the 48-render comparator), is
> running. It, B1 and the TR1 → TR2 decision will be written here when the report lands (about
> 22:00). Nothing in this section is a result yet. Its render total must be taken net of R1 and of
> the double-counted warm-ups ([renders used](#renders-used)).
