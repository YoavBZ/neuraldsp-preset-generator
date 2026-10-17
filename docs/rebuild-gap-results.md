# The rebuild gap: results (stages A, R and TR, 2026-10-17)

Run under the [plan](rebuild-gap-plan.md); its amendment 1 governs. Development data only: step 3's
24 parts, Σ `ee91f710947dbb5c`. Outputs are in `~/ndsp-presets/learn/rebuild-gap/`. All
declared stages have run: A, B0, R1 (R2 not due), T, B1 and TR1 (TR2 not due).
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
- **(stage TR) audited 2026-10-17 by an independent agent; changes:** it recomputed every TR
  figure from the stored scores, training logs and records with its own code, and all matched; it
  confirmed the leak rules, the control's design, the TR2 decision (projected lower bound −0.025)
  and the net renders (TR 2,400; the study 18,981).
  - fold 2's noisy-validation example corrected (0.14 between consecutive checks, 0.21 across two);
  - the list of the largest per-part gains corrected (Passing Ships and Farthest Step added;
    Fragments is outside the 7);
  - "unchanged" short-time treble error and coherence corrected to slightly worse (18 of 24; 1–3
    kHz coherence 0.39 → 0.33);
  - "the lean belongs to the loss" softened to "points to the loss", with `rank` − `ctl`'s
    interval and the checkpoint-selection asymmetry stated;
  - the plan's declared build-ons (more seeds, a learned surrogate, the product cell) added to the
    next step, with a second seed as the cheapest check;
  - also taken: `rank`'s gain set at a little over half of `dep_eq`'s; the −0.53 Spearman marked as
    partly built in; the partial correlation (+0.75) and `ctl`'s (−0.23) added; the ad hoc
    metric's frame and bin floors stated; the validation-band parts named; near S worded as "no
    contrast decided"; `ctl`'s LSD rise noted.
- **Reading these figures:** they are post-hoc development estimates. Fidelity is the cross-half
  local Spearman against the amp track (1 means perfect local ranking).
  - Every figure is band-weighted, with a 90% band-clustered t interval (bands − 1 df: 13 for
    stage R and A1 on all bands), the leave-one-band-out (LOBO) range, and the count of bands above
    and below 0.
- **Multiplicity:** 14 probes, 11 family contrasts, about 52 knob-family contrasts and stage TR's
  two primaries (with their control and 12 near-S contrasts) share the parts and Σ. Read the
  families, not single intervals.

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

**Stage TR: a C′ fine-tuned with a proxy-ranking loss (`rank`) leans better on rendered ranking,
undecided** ([below](#stage-tr-the-ranking-trained-rebuild-judged-on-rendered-ranking-tr1-24-cells-14-bands)):
- **`rank` − C′: +0.075 [−0.031, +0.182],** 7 of 14 bands above 0, LOBO +0.039 to +0.099,
  part-weighted +0.137 [+0.025, +0.249]. About a quarter of the gap (0.26 [−0.23, 0.51]).
- **`rank` − its matched-step control: +0.104 [−0.005, +0.214],** 9 of 14 bands, part-weighted
  +0.162 [+0.045, +0.278], reliable-pair accuracy +0.050 [+0.005, +0.095]. The control itself
  leans slightly below C′ (−0.029 [−0.063, +0.005]). So, on these undecided estimates, the lean
  points to the loss rather than to more fine-tuning (`rank` − `ctl`'s interval still reaches
  −0.005, and only `rank`'s checkpoint was chosen on the proxy).
- **The gain is uneven:** it sits mostly on the 7 parts C′ ranks worst (median part +0.015).
- **It looks like a learned long-term EQ** (post hoc): `rank` lowered the rebuild's long-term
  spectral distance, its gain follows `dep_eq`'s part by part, and it left the short-time
  magnitude error above 2 kHz slightly higher (on 18 of 24 parts) and lowered coherence. That
  error is what R points to, and neither fix reduces it.
- **The proxy read the arm as slightly worse on the 24 parts** (B1), while rendered ranking read it
  as better. TR2 was not due.
- **Proposed next** ([below](#the-next-step-these-imply-a-proposal-not-yet-planned-or-reviewed)):
  a rebuild change aimed at the short-time treble magnitude, judged on rendered ranking, built
  without the test parts, and checked on fresh full mixes.

## Renders used

**The study: 18,981 renders** (R1 16,581 and TR1 2,400; R2 and TR2 none), against about 19–24k
expected. With the 27 lost in R1's crashed rotation choice, the machine rendered 19,008. TR's
count is [with its stage](#renders-used-and-guards).

**R1: 16,581 renders, against at most 16,728 declared.** A crashed first attempt at the rotation
choice also rendered 27 that were lost ([failures](#operational-failures-and-fixes)), so the
machine rendered 16,608.
- Probes: 13 probes × 24 cells × 49 (48 settings and a warm-up) = 15,288. `dep_rot` rendered 21
  cells (1,029). On the other 3 its rule kept no rotation, so it reused `reb`'s renders, as
  declared.
- `dep_rot`'s rotation choice: 216 (24 × 9). The comparator: 48.
- **`report-r1.json` says 16,914.** That is wrong: `renders_used` adds each cell's warm-up a second
  time. The warm-up is already in the record's `renders` (49 per cell).
  - `renders_used` also sums all of `renders/` and `comparator/`, so TR's report does include R1
    and the same overcount ([TR's count](#renders-used-and-guards)).
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

## Stage TR: the ranking-trained rebuild, judged on rendered ranking (TR1, 24 cells, 14 bands)

**The arms.** `rank` is each fold's C′ fine-tuned with C′'s loss plus the two proxy terms
(ranking and output match). `ctl` is the same run with both weights at 0, on the same data
stream, stopped at `rank`'s best step. **C′** is 1b's stored rebuild (`cprime_ref`). Each arm
rebuilt every part's `reference.wav` with its part's fold network and was scored as 1b's matched
cell: `reference.wav`, −52, own mask with the record fallback, paired cell by cell with C′.
Folds hold 6, 10, 3 and 5 of the 24 parts.

### Stage T: the fine-tunes (zero renders, MPS)

- **Weights by the declared share rule** (50 batches at step 0): λ_rank 2.54–3.01 and λ_match
  0.55–0.59 across folds, against C′'s loss of 5.06–5.61.
- **The training pool** is the PR12 cache's rows outside fold f and outside the two validation
  bands: 10,467–12,593 rows. Validation is 2,715–2,788 rows; bleed 22–29 clips.
- **Selection** is proxy fidelity on 96 fixed crops of the two held-out training-fold bands, every
  250 steps:

| Fold | Validation bands | Step 0 (C′) | `rank` best step | `rank` best proxy | `rank` stopped at | `ctl` at that step | Validation recon at the kept step: `rank` / `ctl` (step 0) |
|---|---|---|---|---|---|---|---|
| 0 | Eat The Feeder, Zeno | 0.537 | 500 | 0.668 | 2,000 | 0.478 | 39.1 / 38.6 (38.3) |
| 1 | Adam Buckley, Starnes And Shah | 0.434 | 1,000 | 0.628 | 2,500 | 0.436 | 40.1 / 38.4 (37.7) |
| 2 | Starnes And Shah, Swatkins | 0.354 | 1,000 | 0.669 | 2,500 | 0.398 | 36.9 / 35.3 (35.5) |
| 3 | Swatkins, Zeno | 0.421 | 250 | 0.600 | 1,750 | 0.351 | 43.4 / 43.1 (42.6) |

- **Every fold stopped early**, 1,500 steps after its best, at 1,750–2,500 of the 4,000 steps
  allowed. No fold kept step 0, so every arm is a fine-tune. No step was skipped and none needed a
  recovery.
- **4.0 h of MPS** (`rank` 3.3 h, `ctl` 0.7 h), at the low end of the 4–6 h expected.
- **The validation curves are noisy.** Within a fold the proxy moves by up to 0.14 between
  consecutive checks (fold 2: 0.526 at step 750, 0.669 at 1,000) and by 0.21 across two (0.458 at
  step 500); fold 1 runs 0.419–0.628. The
  kept checkpoint is the best of 7–10 such checks, so its gain over step 0 (+0.13 to +0.31) is
  optimistic.
- **The control's proxy at the matched step** fell on folds 0 and 3, stayed flat on fold 1 and
  rose 0.04 on fold 2. More of C′'s own loss does not raise proxy fidelity.
- **`rank` trades a little reconstruction:** its validation recon (100 · L1 + multi-resolution
  STFT) sits 0.3–1.7 above `ctl`'s at the kept step.
- **Leak rules, as declared.** Checkpoints were selected only on held-out training-fold bands,
  never on the 24 parts' amp tracks or renders. Each fold's validation bands are other folds'
  bands, so the network that rebuilds a part never trained or selected on that part's band. The
  rebuild-time leak assertion and 2a's checks (lag 0 against C′'s stem rebuild, −22.9 LUFS) passed
  on all 48 rebuilds (`arms/check.json`). No Guitar-TECHS P3 row is in the cache (asserted).
  - As with C′'s own training pool, the validation bands' cache rows can include PR12 renders of
    the DI recordings of 24-set parts from other folds (the stage-A audit found the cache holds
    recordings of 17 of the 24). The validation bands are the bands of 4 of the 24 parts: Signs
    (Zeno, validation in folds 0 and 3), Today's The Day (Eat The Feeder, fold 0), Drag Me Down
    (Adam Buckley, fold 1) and Prodigal (Starnes And Shah, folds 1 and 2). The cache's `meta.json` has no part field, so whether those
    recordings are among the validation rows can't be confirmed. They are never the recording of a
    part that the network rebuilds.

### B1: the proxy on the 24 parts (zero renders)

- **Mean proxy fidelity of the amp-track rebuilds:** C′ 0.471, `ctl` 0.438, `rank` 0.425.
  - **The validation gain did not carry to the real amp tracks, as the proxy sees them.**
    `rank` − C′ is −0.046 on the proxy, with 12 of 24 parts up.
  - Per part it swings widely: down from 0.77 to 0.11 and from 0.71 to 0.08 on two parts, up from
    0.18 to 0.57 and from 0.24 to 0.58 on two others.
- **Against the rendered result** (per part, the arms' differences, computed for this write-up):

  | Contrast | Proxy, mean | Rendered, part mean | Spearman across parts | Same sign |
  |---|---|---|---|---|
  | `rank` − C′ | −0.046 | +0.137 | +0.47 | 17 of 24 |
  | `rank` − `ctl` | −0.013 | +0.162 | +0.49 | 17 of 24 |
  | `ctl` − C′ | −0.033 | −0.025 | +0.30 | 14 of 24 |

  - **The proxy picks out moderately well which parts the change helps, but its average is
    wrong:** it reads the change as a small loss, and rendered ranking reads a gain.
  - This matches B0, where the proxy missed `dep_eq`'s gain. See
    [what `rank` changed](#what-rank-changed-in-the-rebuild) for why that may be the same miss.

### Renders used and guards

- **TR1: 2,400 renders, as declared:** 2 arms × 24 cells × 49 (48 settings and a warm-up) =
  2,352, plus the comparator's 48. **TR2: none** ([below](#tr1--tr2-the-stopping-rule)).
- **`report-tr.json` says 19,362.** That is R1's overcounted 16,914 plus TR's 2,448. In TR's
  count each arm cell's warm-up is counted twice (48 extra), the same `renders_used` fault as in R1.
- **The study, net:** R1 16,581 + TR1 2,400 = **18,981 renders.** With the 27 lost in R1's crashed
  rotation choice, the machine rendered 19,008. The plan expected about 19–24k.
- **Guards, all within tolerance:**
  - comparator (C′'s 1b rebuild at S, warm-up and S, against 1b's stored score at S): largest
    1.3e-4 over 24 cells; tolerance 0.005;
  - each cell's S against its warm-up: largest 5.9e-7;
  - FLAC against float at S: largest 1.5e-5.
- Rendered and scored 19:53–20:13. The first report crashed at its last step and was rerun at
  20:20 on the same scores ([failures](#operational-failures-and-fixes)).

### The primaries

**On the same 24 cells:** the truth 0.850 [0.732, 0.967], C′ 0.561 [0.407, 0.715], `ctl` 0.532
[0.375, 0.689] and **`rank` 0.636 [0.526, 0.747]**.

| Contrast | Estimate | LOBO | Bands +/− | Part-weighted | Reliable-pair accuracy Δ |
|---|---|---|---|---|---|
| **`rank` − C′** (does the change help?) | **+0.075 [−0.031, +0.182]** | +0.039 to +0.099 | 7/7 | +0.137 [+0.025, +0.249] | +0.037 [−0.005, +0.080], 9/5 |
| **`rank` − `ctl`** (is it the loss?) | **+0.104 [−0.005, +0.214]** | +0.063 to +0.126 | 9/5 | +0.162 [+0.045, +0.278] | +0.050 [+0.005, +0.095], 10/4 |
| `ctl` − C′ (more fine-tuning alone) | −0.029 [−0.063, +0.005] | −0.036 to −0.013 | 6/8 | −0.025 [−0.048, −0.001] | −0.012 [−0.029, +0.004], 6/7 |
| *truth − `rank`* | +0.213 [+0.088, +0.339] | +0.178 to +0.243 | 12/2 | +0.217 [+0.094, +0.340] | +0.192 [+0.135, +0.248] |

- **Share of the gap** (truth − C′ +0.289 on these cells): `rank` closes 0.26 [−0.23, 0.51];
  `ctl` −0.10 [−0.38, 0.02].
- **Per amp and class** (descriptive; per amp is 8 parts, crunch is 5):

  | Contrast | AC20 | PR12 | SW50R | Clean | Crunch |
  |---|---|---|---|---|---|
  | `rank` − C′ | +0.055 | +0.290 | +0.065 | +0.133 | −0.028 |
  | `rank` − `ctl` | +0.068 | +0.305 | +0.121 | +0.152 | +0.018 |
  | `ctl` − C′ | −0.013 | −0.015 | −0.057 | −0.019 | −0.046 |
  | *gap: truth − C′* | +0.347 | +0.612 | +0.081 | +0.419 | +0.055 |

  As in stage R, the gain sits where the gap is: PR12 and the clean parts.
- **Per fold** (part means; descriptive, 3–10 parts each): `rank` − C′ +0.06, +0.15, −0.01 and
  +0.29 on folds 0–3; `rank` − `ctl` +0.11, +0.15, −0.00 and +0.35; `ctl` − C′ −0.05, +0.01,
  −0.01 and −0.06. Fold 2 (3 parts, where C′ already ranks 0.39–0.97 and the truth sits below C′
  on one part) shows nothing either way.
- **Near S** (A1's knob families, 3-way agreement on S's ±1/8 neighbourhood): no family's
  contrast is decided. `rank` − C′ runs from −0.018 to +0.026, each interval containing 0 (input
  gain's is ±0.16 wide). Against `ctl`, amp tone is +0.058 [+0.015, +0.101], one interval among 12.
  An inference, as with `dep_eq`: the gain on all of Σ comes from pairs farther from S.

### Where the gain sits (post hoc, descriptive)

- **It is uneven across parts.** `rank` beats C′ on 13 of 24 parts, and the median part gains
  +0.015.
- **Most of it is on the parts C′ ranks worst.** On the 7 parts where C′'s fidelity is under 0.35
  (a cut chosen after looking; on 4 of them C′'s ranking is near 0 or inverted), `rank` − C′ is
  +0.465 on average, with 6 of 7 up. On the other 17 it is +0.002, with 7 up. Across all 24, the
  gain's Spearman with C′'s fidelity is −0.53, but that is partly built in: the gain contains C′,
  and shuffling `rank`'s values across parts gives about −0.77 on average. The split with `ctl`
  beside it (next bullet) is the better evidence.
  - The largest: Bloomlight −0.82 → +0.29, Long Way Home −0.28 → +0.69, First Offering (GTR 2)
    0.00 → 0.44, Passing Ships (ElecGtr6) −0.26 → +0.07, Farthest Step 0.31 → 0.61. Outside the 7,
    the largest is Fragments 0.72 → 0.97.
  - The largest losses: Just Don't Talk 0.81 → 0.58, Sculptor's Request (GTR 1) 0.72 → 0.54.
  - **`ctl` does not do this on the same 7 parts** (−0.019), so it is not an effect of any further
    fine-tuning. But `rank` moves the rebuild further than `ctl` does, and a part at the floor can
    only rise. So part of the pattern may be any larger change moving extreme parts toward the
    middle. These data can't separate the two.

### What `rank` changed in the rebuild

Computed for this write-up (zero renders; each rebuild against the measure DI, aligned as in stage
R, medians over the 24 parts):

| Rebuild | LSD, 80 Hz–8 kHz (dB) | Coherence 3–8 kHz | Coherence 1–3 kHz | Short-time magnitude error above 2 kHz (dB) |
|---|---|---|---|---|
| C′ | 3.30 | 0.012 | 0.39 | 8.87 |
| `ctl` | 3.60 | 0.013 | 0.41 | 8.79 |
| `rank` | **2.52** (lower on 18 of 24) | 0.010 | 0.33 | 8.97 (higher on 18 of 24) |

- The last column is a metric added for this write-up, not a declared one: the mean |ΔdB| of
  the STFT magnitudes (1,024-sample frames, hop 256) over 2–8 kHz, on frames within 40 dB of the
  true DI's loudest and bins within 60 dB of each frame's loudest true bin, after removing each
  bin's long-term offset. That removal takes out any fixed EQ.
- **`rank` moved the rebuild's long-term spectrum toward the true DI's.** It slightly raised the
  short-time magnitude error above 2 kHz (median +0.23 dB, 18 of 24) and lowered coherence (1–3
  kHz 0.39 → 0.33, lower on 21 of 24; 3–8 kHz lower on 20 of 24).
- `ctl` went the other way on the long-term spectrum (LSD 3.30 → 3.60, higher on 22 of 24), while
  its fidelity fell only 0.029.
- **Per part, `rank`'s rendered gain follows `dep_eq`'s** (R1, the same cells): Spearman +0.82,
  and +0.75 with C′'s fidelity partialled out. `ctl`'s gain correlates −0.23 with `dep_eq`'s. It
  follows `high`'s at +0.75, its own LSD drop at −0.46, and not its change in short-time treble
  error (−0.12). `rank` − `dep_eq` is −0.058 [−0.131, +0.016].
- **Reading, hedged:** the proxy-ranking loss seems to have moved the rebuild mostly as `dep_eq`
  does, toward the right long-term spectral balance. Both are post hoc, and both gains sit on the
  parts where C′ ranks worst, so the correlation is partly shared difficulty.
  - That fits the proxy's construction: its tone stack and cab are fixed long-term filters and its
    distance is a frame-averaged log-mel, so a long-term balance error is what it sees most
    readily. It still did not reward this change on the 24 parts (B1).

### Reading

- **Both primaries are undecided, and both lean positive.** Neither band-weighted interval
  excludes 0. By the plan's rules that is not a failure, and the lean is built on.
- **What the lean is worth:**
  - every leave-one-band-out value is positive for both (`rank` − C′ +0.039 to +0.099; `rank` −
    `ctl` +0.063 to +0.126);
  - part-weighted, both intervals exclude 0;
  - `rank` − `ctl`'s reliable-pair accuracy excludes 0 (+0.050 [+0.005, +0.095]);
  - **against that,** `rank` − C′ splits the bands 7 and 7, the median part gains +0.015, and the
    gain rests mostly on 7 parts where C′ ranks badly.
  - The size: about a quarter of the rebuild gap (0.26, with an interval reaching −0.23). `rank`
    stays +0.213 below the truth.
- **The declared reading** ("a positive `rank` − C′ is built on … positive against C′ but not
  against `ctl` points to the extra fine-tuning"): `rank` leans positive against both, and `ctl`
  leans slightly below C′ (part-weighted −0.025 [−0.048, −0.001]). **So, on these undecided
  estimates, the lean points to the loss rather than to more fine-tuning** (`rank` − `ctl`'s
  interval still reaches −0.005, and only `rank`'s checkpoint was chosen on the proxy: it is the
  best of its own noisy checks, while `ctl` is not selected). Fine-tuning on C′'s loss alone, if
  anything, costs a little.
- **How it relates to stage R.** R found that what costs ranking is a structured short-time
  magnitude error, mostly above 2 kHz, of which a fixed long-term EQ (`dep_eq`) removes at most
  about half. TR's change looks like a learned version of the long-term part:
  - its gain is a little over half of `dep_eq`'s (+0.075 against +0.133; `rank` − `dep_eq`
    −0.058 [−0.131, +0.016]);
  - it follows `dep_eq` part by part;
  - it lowered the LSD and slightly worsened the short-time treble error and the coherence.
  - **The structured short-time error above 2 kHz is the part that neither `dep_eq` nor `rank`
    reduces,** and on R's evidence it is most of what remains. A proxy that reads frame-averaged
    log-mel through fixed filters is a weak lever on it. B0 already showed the proxy underrates
    `high`'s gain at about 58%.
- **Multiplicity:** two primaries, the control contrast, their part-weighted and reliable-pair
  rows, per-fold rows and 12 near-S contrasts share the 24 cells and Σ, after experiments 1–1d and
  stage R. One seed per fold, and fold 2 has 3 parts. These are development estimates.

### TR1 → TR2: the stopping rule

- **The declared rule is on `rank` − C′:** positive, its interval containing 0, and the interval
  narrowed by the stored ratio (0.948, the same six contrasts as R1) excluding 0.
- The half-width is 0.106; narrowed, it is 0.101, above the estimate's 0.075. The projected
  lower bound is −0.025, so **TR2 was not due**, and TR stopped at TR1. The runner logged `TR2 not
  due`.
- `rank` − `ctl` would have met the narrowing test, by 0.0006 (projected lower bound +0.0006), but
  the rule was declared on `rank` − C′ only.
- The product cell (the arms rebuilding the htdemucs stem) was not run. The plan ties it to a
  positive TR reading and the user's yes.

## What it decides (stages A, R and TR together)

- **Where the rebuild loses ranking, with a perfect stem: its short-time magnitude,** above all
  above 2 kHz, through the whole note (A, R).
  - Not its phase: the true phase under the rebuild's magnitude recovers nothing.
  - Not one knob: every knob family loses about equally (A1).
  - Sustain carries more than attacks only because it covers 76% of the samples.
- **The error that costs is structured and signal-dependent,** at time scales between 21-ms frames
  and the long-term spectrum. It is not the error's frame-level size (`noise`).
  - **A long-term spectral fix gets part of the way, by two routes:**
    - the fixed EQ `dep_eq`, +0.133 [−0.009, +0.276] (R);
    - the proxy-ranking fine-tune `rank`, +0.075 [−0.031, +0.182] against C′ and +0.104 [−0.005,
      +0.214] against its control (TR).
  - Both are undecided and lean positive. Both close roughly a quarter to a half of the gap, and
    both help mostly the parts C′ ranks worst.
  - **`rank` seems to work mostly as `dep_eq` does** (post hoc): it lowers the long-term spectral
    distance, its gain follows `dep_eq`'s part by part (+0.82), and it slightly worsens the
    short-time treble error and coherence.
  - **The structured short-time error above 2 kHz is not reduced by either,** and on R's evidence it is
    most of what remains.
- **The proxy-ranking loss is a lean worth building on, but the proxy is not the lever for what
  remains.**
  - On these undecided estimates its lean points to the loss rather than to more fine-tuning:
    `ctl` leans slightly below C′. (`rank` − `ctl`'s interval still reaches −0.005, and only
    `rank`'s checkpoint was chosen on the proxy.)
  - But the proxy read the arm as worse on the 24 parts (B1) while rendered ranking read it as
    better. The proxy also underrated `high`'s gain and missed `dep_eq`'s (B0).
- **Rotation fixes are deprioritised:** rotation augmentation, a rotation-invariant objective and
  `dep_rot`. The rotation's cost is decided but small, about 4% of the gap, and removing it gains
  nothing measurable.
- **`dep_eq` stays a near-free product candidate,** leaning positive and undecided. Read it with
  its caveats: its gain is concentrated on PR12 and clean parts, it leans worse near S on gain
  staging, part of its gain is agreement with the yardstick's own normalisation, and its curve
  includes 17 of the 24 parts' recordings.

### The next step these imply (a proposal, not yet planned or reviewed)

**A rebuild change aimed at the short-time magnitude structure above 2 kHz, beyond the long-term
spectrum.** For example, a C′ fine-tune with a loss on short-time log-magnitude at a few
resolutions (about 5–40 ms), weighted above 2 kHz, with each bin's long-term offset removed so
that it cannot be met by one more EQ. `dep_eq`'s normalisation (or `rank`) would carry the
long-term part beside it. How it would be judged:
- **Measure first, zero renders:** on held-out training-fold bands, check that the change lowers
  the short-time treble error (the metric [above](#what-rank-changed-in-the-rebuild) or a declared
  version of it) where `rank` and `dep_eq` did not. Only then render.
- **Judged on rendered ranking,** with TR's design: the arm, a matched-step control, C′, paired
  cells, and the `rank` arm beside it for comparison. No proxy decides it.
- **Built without the test parts:** the average curve and any spectral targets made without the
  test parts' recordings (`dep_eq`'s current curve includes 17 of the 24), and checkpoints
  selected off them, as in stage T.
- **Checked where the product works: fresh parts outside the 24, on full mixes.** Stage R's
  findings come from the 24 parts and a perfect stem. Arm A's recipe on fresh full mixes reads
  only H − S −0.028 [−0.064, +0.008] ([Mega-53 results](arm-a-mega53-results.md)), against
  −0.083 on its development parts. A rebuild gain on the amp track may shrink after separation and
  vocals, so the fresh full-mix song-level reading is the one that counts.
- **The plan's declared build-ons for a positive `rank` − C′** (more seeds, a learned surrogate,
  the product cell) come before or beside this. With one seed per fold and noisy proxy selection,
  a second seed of `rank` and `ctl` (about 4 h of MPS and 2,352 renders) is the cheapest check
  that the lean is not one seed's or one checkpoint's draw.
- Whether `rank` and `dep_eq` add is untested. If they pull the same lever, as TR suggests, they
  may not.

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
3. **The TR report crashed as it wrote its file** (20:13, `logs/report-tr-failed1.log`).
   - `tr2_due` returned a numpy bool (the rule's comparison is on numpy floats), which `json`
     can't write. Everything before the write had been computed.
   - Fixed in 8e69204 (`tr2_due` returns a plain bool, with a test). The report was rerun by hand
     at 20:20 on the same scores (`logs/report-tr.log`), and the TR2 check run after it logged
     `TR2 not due`.
   - Nothing was re-rendered or rescored. The R1 report never reached this line, since its rule
     returns a list of names.
