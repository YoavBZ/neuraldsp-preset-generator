# The rebuild's short-time magnitude, by dose: results (2026-10-18)

Run under the [plan](dose-probe-plan.md); its amendments 1 and 2 govern. Development data only:
step 3's 24 parts, Σ `ee91f710947dbb5c`, the rebuild-tone step's stored `cprime_eq` rebuilds and
scores. Outputs are in `~/ndsp-presets/learn/rebuild-dose/` (`report-r1.json` = `report.json`,
`arms/build.json`, `arms/check.json`, `renders/`, `scores/`, `comparator/`, `cleared/`,
`unrecorded.json`, `logs/`). R1 ran in full on all 24 cells; R2 was not due. The fourth launch
logged `all done (R1 ok; renders 7448)` at 19:58.

- **Audited 2026-10-18 by an independent agent; changes:** it recomputed every figure from the raw
  score files with its own code (its own band-clustered t, Fieller and reliable-pair code), and all
  matched except three roundings of Fieller interval ends; it confirmed that no scoring path changed
  between the launches (only the renderer in the fourth), the comparators on all 24 cells, which
  cells used which render server, the priming renders, the Σ-order repeat check (20 comparisons,
  largest 2.0e-7), the resume (144 records and score files of exactly 48, each written once; no
  stale or temporary files) and the 7,448 renders. Changes:
  - the three roundings (`dose100`'s share 0.25 [0.01, 0.59]; `full100`'s and `dose25`'s shares of
    C′'s gap);
  - truth − `full100` is about a quarter of the remainder, not a fifth, and its part-weighted
    interval includes 0;
  - the post-hoc `full100` − `shift100` no longer read as support: it equals `full100` −
    `cprime_eq` because `shift100` ≈ `cprime_eq`, so there is no control for the full-band probes,
    and the next-build implication now carries reading 5's caveat;
  - the 2–8 kHz cap stated with its interval (upper end above half); "clearly below" dropped for
    `dose100` − `full100` (upper end −0.002) and both boundary readings named;
  - what lies outside E_st corrected (above about 10 kHz and the ⅓-octave edges too, not separated);
    "revises" stage R's "above 2 kHz" made "qualifies" (its `high` also restored phase, the band above
    8 kHz and much of the long-term balance); `stm`'s null also explained by its small cut;
  - the per-amp region sentence marked descriptive; the render decomposition (137 priming, 10
    repeats, 149 redone); the alignment floor |c| ≥ 0.39; the third launch's lane order;
  - also taken: `full100`'s peak (4.1 dB) for the ±12 dB note, "same hashes" for the rebuilds at each
    launch, the repeat check's sample of transitions, `dose25`'s marginal R2 projection and the
    unrecorded renders on Drag_Me_Down.

- **Reading these figures:** post-hoc development estimates, a further unblinded use of the 24
  parts and Σ after experiments 1–1d, the rebuild-gap study and the rebuild-tone step. Every probe
  is an **oracle** (built from the true DI), so this is a diagnostic, never a product candidate.
  Fidelity is the cross-half local Spearman against the amp track (1 means perfect local ranking).
  - Every figure is band-weighted with a 90% band-clustered t interval (13 df on the 14 bands), the
    leave-one-band-out (LOBO) range and the bands above/below 0, unless it says otherwise.
  - **The remainder** is truth − `cprime_eq` on these cells: +0.157 [+0.083, +0.230], 13/1 bands.
    "Near 0" uses a quarter of it (±0.039), as declared.
- **Multiplicity:** 5 primaries and 6 secondaries (plus every probe against C′), each with
  part-weighted, reliable-pair, per-amp, per-class, no-high-bleed and fixed-mask rows, on the same
  24 cells. Read the family (the dose series and the ceilings together), not single intervals.
  Two declared readings sit on a boundary: `dose100` − `cprime_eq`'s lower end is +0.002 and
  `dose100` − `full100`'s upper end −0.002.

## Headline

**The full-band true short-time magnitude, laid on top of the leak-free EQ, recovers most of what
the EQ leaves; restoring it only in 2–8 kHz on E_st's mask recovers about a quarter.**
- **Full band, one resynthesis with C′'s phase** (`full100` − `cprime_eq`): **+0.116 [+0.045,
  +0.187]**, 13/1 bands, **0.74 [0.50, 0.86] of the remainder**.
- **Full band with Griffin–Lim** (`full_gl` − `cprime_eq`): **+0.123 [+0.051, +0.194]**, 13/1,
  0.78 [0.59, 0.87]. The extra consistency adds nothing measurable: `full_gl` − `full100` +0.007
  [−0.003, +0.017], near 0.
- **2–8 kHz on E_st's mask** (`dose100` − `cprime_eq`): +0.039 [+0.002, +0.077], 11/3, 0.25 [0.01,
  0.59] of the remainder. It is below the full-band field by the declared rule: `dose100` −
  `full100` **−0.076 [−0.150, −0.002]**, 2/12 bands (upper end −0.002; reliable-pair −0.057
  [−0.085, −0.028], 0/14 bands).
- **Against C′:** `full100` reaches 0.86 [0.65, 0.92] of C′'s whole gap (+0.248 [+0.069, +0.426]),
  `full_gl` 0.88 (+0.255 [+0.075, +0.434]). Something is still left: truth − `full100` +0.041
  [+0.021, +0.061] (part-weighted +0.032 [−0.017, +0.081] includes 0).
- **The time-shift control is undecided, as declared** (it controls `dose100`, not the full-band
  probes): `shift100` − `cprime_eq` −0.000 [−0.099, +0.098]; `dose100` − `shift100` +0.040
  [−0.074, +0.153]. So readings 1–4 carry the plan's caveat, and no control exists for the
  full-band probes ([below](#the-time-shift-control)).

**What it implies for the next build (hedged):** option 2 of the
[HF research](research/hf-detail-losses-2026-10.md), a bounded per-bin, per-frame log-gain on C′'s
own output resynthesised with C′'s phase, is supported only as a **full-band** field, under
reading 5's caveat (the control is undecided, and no control exists for the full-band probes:
`shift100` controls `dose100` only). Its oracle ceiling is `full100` (about three quarters of the
remainder). A version restricted to E_st's 2–8 kHz region and mask would cap at about a quarter
(0.25 [0.01, 0.59] of the remainder; the oracle's upper end is above half), and E_st (2–8 kHz)
is not the right gate metric for it. One resynthesis with C′'s phase is enough; no Griffin–Lim
steps or phase output are needed.
([Next step](#the-next-step-a-proposal-not-yet-planned-or-reviewed).)

## Renders used

**7,448 renders**, exactly amendment 2's expected R1 total. R2 rendered nothing. **With the stop
audit's 70 diagnostic renders** (not stored under this step), **7,518 renders were spent because of
this step.** The plan first declared 7,152; amendment 2 added 137 priming renders (every (cell, probe)
but the 7 kept `dose100` cells), the 10 repeat renders and 149 spent renders redone (the first
launch's 49 on each of its three cells, and the stopped cell's 2): 7,152 + 137 + 10 + 149 =
7,448.

| Part | Renders |
|---|---|
| `dose100` records (24 cells) | 1,279 |
| `dose100` cleared record (the stopped cell, first and second launches) | 40 |
| `shift100`, `full_gl`, `full100`, `dose50`, `dose25` (24 cells × 50 each) | 6,000 |
| Comparators (24 cells × 4) | 96 |
| Rendered but never recorded (first launch, `unrecorded.json`) | 33 |
| **Total (`report.json` `renders.total`)** | **7,448** |
| The stop audit (reported beside it) | 70 |

- **Per `dose100` cell:** 15 cells at 50 (priming + warm-up + 48); 6 cells at 49 and Drag_Me_Down
  ElecGtr4 at 87 (38 recorded + 49; 49 + 49 were rendered, 11 of them among the unrecorded 33),
  kept from the first two launches without a priming render, as amendment 2 declared;
  It_Was_My_Fault ElecGtr2 at 88 (38 recorded in the first launch + 50); the stopped cell,
  It_Was_My_Fault ElecGtr1 pr12, at 60 (50 + the 10 repeat renders), beside its cleared record (40).
- **By launch:** 159 (first; 126 recorded and 33 not), 369 (second; cumulative 528, logged 495
  before the correction), 2,114 (third; cumulative 2,642), 4,806 (fourth; cumulative 7,448).
- **Wall clock:** about 1.0 h of rendering in the third launch (lane 0) and 1.1 h in the fourth
  (lanes 1–2), after about 3 h of the third launch's lanes waiting for free slots.

**Guards, all within tolerance:**
- **Comparators** (per cell, before its first probe render): C′'s 1b rebuild at S against 1b's
  stored score, largest 1.3e-4; the anchor (`cprime_eq`) at S against the rebuild-tone step's
  stored score, largest 5.9e-5. All 24 cells, tolerance 0.005.
- **Each (cell, probe)'s S against its warm-up:** largest 2.3e-7 (`dose100`, one of the cells kept
  from the second launch); exactly 0 on all 120 cells of the other five probes, which all had the
  priming render.
- **FLAC against float at S:** largest 3.2e-5 (`full_gl`).
- **The Σ-order repeat check** (amendment 2, item 2; It_Was_My_Fault ElecGtr1, pr12, `dose100`,
  indices 1, 6, …, 46, both halves): largest deviation **2.0e-7** over 20 comparisons (tolerance
  0.005). So on the quiet-opening part that stopped the run, a Σ score does not depend on the
  previous Σ setting, on the 10 sampled transitions (every 5th index).
- **Probe hashes:** every one of the 144 records carries the hash in the current `build.json`.
  The build ran at each launch and gave the same hashes; renders refuse a mismatch.
- **No STOP.json at the end;** the only breakage was the second launch's (below).

## The probes (zero renders; `arms/build.json`)

Built as declared and amended, rebuilt at each launch with the same hashes (the build files are
overwritten each time, so only the hashes can be compared across launches). Medians over the
24 parts:

| Probe | E_st (dB) | Realised cut (range) | LSD to the truth (dB) | LSD to `cprime_eq` | Peak over max(anchor, truth), worst part |
|---|---|---|---|---|---|
| `cprime_eq` (anchor) | 7.58 | — | 1.59 | 0 | 0 |
| `dose25` | 6.43 | 15% (13–16%) | 1.59 | 0.016 | +0.4 dB |
| `dose50` | 5.40 | 29% (24–31%) | 1.59 | 0.031 | +0.6 dB |
| `dose100` | 4.00 | 47% (39–51%) | 1.59 | 0.061 | +0.8 dB |
| `full100` | 3.61 | 52% (43–57%) | 1.58 | 0.108 | +4.1 dB |
| `full_gl` | 2.29 | 69% (49–73%) | 1.55 | 0.187 | +4.3 dB |
| `shift100` (control) | 9.14 | −20% (−42 to −11%) | 1.60 | 0.078 | +0.7 dB |
| `dose100` bounded ±12 dB (not rendered) | 4.30 | 43% (37–47%) | 1.59 | 0.054 | +0.8 dB |

- **Build checks pass on all 24 parts and 7 probes** (`check.json`: ok, no problems): the same
  length as `cprime_eq`, GCC 0, −22.9 LUFS, LSD to the truth within 0.072 dB of the anchor's (doses
  within 0.016), LSD to `cprime_eq` at most 0.38 dB, peak at most 4.3 dB over max(anchor, truth),
  alignment |c| ≥ 0.39 and 80 Hz–2 kHz coherence ≥ 0.31 (stage R's floors 0.3).
- **The long-term balance is held,** so stage R's confound (probes that also fixed the long-term
  spectrum) is removed by construction.
- **The gain field:** 9–25% of masked 2–8 kHz bins need more than ±12 dB (95th percentile of |g|
  14–21 dB by part, largest 59 dB). Bounding at ±12 dB moves `dose100`'s realised cut from 47% to
  43% (not rendered, as declared).

## Rendered judgement (R1, 24 cells, 14 bands)

**Fidelity on the same 24 cells:** the truth 0.850 [0.732, 0.967]; C′ 0.561 [0.407, 0.715];
`cprime_eq` 0.693 [0.556, 0.829]; `dose25` 0.706; `dose50` 0.711; `dose100` 0.732 [0.588, 0.877];
`full100` 0.809 [0.686, 0.931]; `full_gl` 0.815 [0.696, 0.935]; `shift100` 0.692 [0.548, 0.837].

### The primaries (each against the anchor `cprime_eq`)

| Contrast | Estimate | LOBO | Bands +/− | Share of the remainder | Part-weighted | Reliable-pair Δ | No high bleed (20 cells) | Truth − probe |
|---|---|---|---|---|---|---|---|---|
| **`full_gl` − `cprime_eq`** | **+0.123 [+0.051, +0.194]** | +0.103 to +0.150 | 13/1 | **0.78 [0.59, 0.87]** | +0.142 [+0.067, +0.218] | +0.082 [+0.055, +0.110], 14/0 | +0.139 [+0.063, +0.215] | +0.034 [+0.021, +0.047] |
| **`full100` − `cprime_eq`** | **+0.116 [+0.045, +0.187]** | +0.095 to +0.143 | 13/1 | **0.74 [0.50, 0.86]** | +0.138 [+0.063, +0.214] | +0.079 [+0.051, +0.108], 14/0 | +0.133 [+0.056, +0.209] | +0.041 [+0.021, +0.061] |
| **`dose100` − `cprime_eq`** | **+0.039 [+0.002, +0.077]** | +0.028 to +0.048 | 11/3 | 0.25 [0.01, 0.59] | +0.050 [+0.018, +0.082] | +0.023 [+0.003, +0.043], 11/3 | +0.046 [+0.008, +0.085] | +0.117 [+0.040, +0.195] |
| **`dose50` − `cprime_eq`** | +0.018 [−0.006, +0.042] | +0.009 to +0.026 | 11/3 | 0.12 [−0.04, 0.34] | +0.025 [−0.000, +0.051] | +0.010 [−0.003, +0.023], 10/4 | +0.023 [−0.003, +0.049] | +0.139 [+0.061, +0.217] |
| **`dose25` − `cprime_eq`** | +0.013 [−0.001, +0.028] | +0.007 to +0.016 | 10/4 | 0.09 [−0.01, 0.21] | +0.019 [+0.000, +0.037] | +0.007 [−0.000, +0.015], 10/4 | +0.017 [+0.001, +0.032] | +0.144 [+0.070, +0.217] |

- The no-high-bleed rows (First Offering GTR_1, Gym Hours GTR_1, Long Way Home and Sculptor's
  Request GTR_1 out) read the same way, slightly larger.
- **The fixed-mask diagnostic (reading 6):** with `cprime_eq` as the judge's activity mask every
  primary is unchanged to the third decimal (for example `full100` +0.116, `dose100` +0.039). The
  gains come through the amp's response, not through the probes moving the activity mask.

### The secondaries

| Contrast | Estimate | LOBO | Bands +/− | Part-weighted | Reliable-pair Δ | No high bleed |
|---|---|---|---|---|---|---|
| **`dose100` − `full100`** (region) | **−0.076 [−0.150, −0.002]** | −0.101 to −0.048 | 2/12 | −0.089 [−0.158, −0.019] | −0.057 [−0.085, −0.028], 0/14 | −0.087 [−0.162, −0.011] |
| **`full_gl` − `full100`** (consistency) | +0.007 [−0.003, +0.017] | +0.002 to +0.009 | 7/7 | +0.004 [−0.004, +0.011] | +0.003 [−0.004, +0.010] | +0.006 [−0.004, +0.017] |
| `dose100` − `dose50` | +0.021 [−0.000, +0.042] | +0.014 to +0.029 | 12/2 | +0.024 [+0.007, +0.042] | +0.013 [+0.002, +0.023] | +0.023 [+0.002, +0.045] |
| `dose50` − `dose25` | +0.005 [−0.008, +0.018] | +0.001 to +0.010 | 10/4 | +0.007 [−0.004, +0.017] | +0.003 [−0.004, +0.010] | +0.007 [−0.007, +0.020] |
| **`shift100` − `cprime_eq`** (control) | −0.000 [−0.099, +0.098] | −0.035 to +0.031 | 8/6 | −0.020 [−0.123, +0.082] | +0.003 [−0.039, +0.046] | −0.010 [−0.113, +0.093] |
| **`dose100` − `shift100`** (control) | +0.040 [−0.074, +0.153] | −0.003 to +0.083 | 8/6 | +0.070 [−0.050, +0.190] | +0.020 [−0.031, +0.070] | +0.056 [−0.064, +0.177] |

**Every probe against C′** (1b's rebuild; share of C′'s gap, truth − C′ = +0.289):

| Probe − C′ | Estimate | Bands +/− | Share of the gap | Reliable-pair Δ |
|---|---|---|---|---|
| `full_gl` | +0.255 [+0.075, +0.434] | 11/3 | 0.88 [0.72, 0.93] | +0.146 [+0.071, +0.222] |
| `full100` | +0.248 [+0.069, +0.426] | 11/3 | 0.86 [0.65, 0.92] | +0.143 [+0.069, +0.218] |
| `dose100` | +0.171 [+0.002, +0.341] | 11/2 | 0.59 [0.02, 0.84] | +0.087 [+0.018, +0.155] |
| `dose50` | +0.150 [−0.024, +0.324] | 10/4 | 0.52 [−0.20, 0.78] | +0.074 [+0.004, +0.143] |
| `dose25` | +0.145 [−0.026, +0.316] | 9/5 | 0.50 [−0.22, 0.75] | +0.071 [+0.003, +0.139] |
| `shift100` | +0.131 [+0.001, +0.262] | 11/3 | 0.46 [0.01, 0.75] | +0.067 [+0.019, +0.115] |
| `cprime_eq` (the anchor) | +0.132 [−0.030, +0.294] | 9/5 | 0.46 [−0.26, 0.69] | +0.064 [+0.001, +0.126] |

The anchor's row reproduces the rebuild-tone step's (+0.132, from its stored scores).

**Per amp and class** (descriptive; per amp 8 parts, crunch 5):

| Contrast | AC20 | PR12 | SW50R | Clean | Crunch |
|---|---|---|---|---|---|
| `full_gl` − `cprime_eq` | +0.176 | +0.167 | +0.065 | +0.164 | +0.048 |
| `full100` − `cprime_eq` | +0.168 | +0.168 | +0.056 | +0.157 | +0.042 |
| `dose100` − `cprime_eq` | +0.033 | +0.011 | +0.077 | +0.029 | +0.058 |
| `dose50` − `cprime_eq` | +0.033 | −0.015 | +0.042 | +0.019 | +0.016 |
| `dose25` − `cprime_eq` | +0.035 | −0.009 | +0.023 | +0.020 | +0.001 |
| `dose100` − `full100` | −0.135 | −0.158 | +0.022 | −0.128 | +0.016 |
| `shift100` − `cprime_eq` | −0.033 | +0.100 | −0.074 | −0.046 | +0.081 |
| *remainder: truth − `cprime_eq`* | +0.242 | +0.198 | +0.022 | +0.203 | +0.074 |

The full-band probes gain where the remainder is (AC20, PR12, clean parts) and little where it is
small (SW50R, crunch). There `dose100` matches the full-band field; the region difference is
carried by AC20 and PR12.

### The dose shape (reading 4)

`dose100` − `cprime_eq` is above 0 (its lower end +0.002), so the shape is read, as declared:

| Dose | Realised cut | r (cut / `dose100`'s) | Gain over the anchor | S (share of `dose100`'s gain, Fieller) | Shape against r ± 0.15 |
|---|---|---|---|---|---|
| `dose25` | 15% | 0.32 | +0.013 | 0.34 [−0.05, 2.45] | proportional |
| `dose50` | 29% | 0.62 | +0.018 | 0.46 [−1.50, 1.01] | convex (0.46 against a boundary of 0.47) |
| `dose100` | 47% | 1 | +0.039 | 1 | — |

- **The shape is undecided** by the declared rule (S25 and S50 disagree), and both shares'
  intervals are very wide. Read as data, the doses' gains rise roughly with the cut (dose50 sits a
  hair under proportional), and `dose100` − `dose50` +0.021 [−0.000, +0.042] is not decided.
- **The cut that matters** (the smallest cut whose dose gains at least half of `dose100`'s): **47%,
  `dose100`'s own.** `dose50` gains 0.46 of it, just under half.
- **Per-part gain against the realised cut** (Spearman over the 24 parts, descriptive): `dose100`
  +0.32, `dose50` +0.02, `dose25` +0.04, `full100` −0.13, `full_gl` −0.05, `shift100` +0.26.
- **The E_st cut does not index the gain across regions:** `full100` cuts E_st only 5 points more
  than `dose100` (52% against 47%) and gains three times as much. Presumably the extra gain comes
  from changes E_st weighs little or not at all: below about 1.6 kHz, above about 10 kHz, the
  ⅓-octave edges, and frames and bins outside the doses' both-signals mask. Not separated here.

### The time-shift control

`shift100` is `dose100`'s field shifted by half the part (5 s): the same gains at the wrong times.
- **As declared, undecided:** `shift100` − `cprime_eq` −0.000 [−0.099, +0.098] (its upper end is
  not near 0), `dose100` − `shift100` +0.040 [−0.074, +0.153].
- **It is a noisy control.** Misplaced short-time gains swing single cells both ways: Passing Ships
  ElecGtr6 (SW50R) −0.93, Blind Spots −0.28, Drag Me Down ElecGtr4 −0.24; It_Was_My_Fault
  ElecGtr1 (PR12, the quiet-opening part) +0.91, femme +0.20. On It_Was_My_Fault the gain is
  mostly through the judge's activity mask: +0.20 with the anchor's mask. With the anchor's mask the
  control reads −0.026 [−0.104, +0.053] and `dose100` − `shift100` +0.065 [−0.025, +0.155], still
  undecided.
- **Post hoc (not declared; computed for this write-up with the report's own contrast code):**
  `full100` − `shift100` **+0.116 [+0.011, +0.221]**, 11/3 (part-weighted +0.159 [+0.048, +0.269];
  reliable-pair +0.076 [+0.032, +0.120]; with the anchor's mask +0.141 [+0.037, +0.245]); `full_gl`
  − `shift100` +0.123 [+0.015, +0.231]. These carry nothing beyond reading 1: since `shift100` −
  `cprime_eq` is −0.0004, `full100` − `shift100` is numerically `full100` − `cprime_eq`. The
  shifted 2–8 kHz field is not a full-band shifted field, so there is no control for the full-band
  reading.

### R1 → R2: the stopping rule

The narrowing ratio is the stored 0.948. No probe extended (`extend: none`; `R2: no probe
extends`):
- `full_gl`, `full100` and `dose100` against the anchor are already decided (their intervals
  exclude 0), so they don't extend;
- `dose50`'s projected lower bound is −0.005 and `dose25`'s −0.00007: neither would exclude 0
  (`dose25` by a hair).

## Reading

**By the plan's declared readings** (`report.json` `readings`):
1. **Is the remainder short-time magnitude? Most of the remainder** (`full_gl` above 0, share 0.78
   [0.59, 0.87]). Stage R's `mag` result holds with the long-term balance held at `cprime_eq`'s.
   About a fifth is still left (truth − `full_gl` +0.034 [+0.021, +0.047]).
2. **Can option 2's mechanism carry it? `full_gl` − `full100` near 0** (+0.007, upper end 0.017),
   **`full100` above 0** (share 0.74 [0.50, 0.86]). One resynthesis with C′'s phase is enough;
   **option 2's oracle ceiling is what `full100` shows.** The deeper E_st cut of Griffin–Lim (69%
   against 52%) buys nothing measurable.
3. **Is E_st's region the one that matters? `dose100` − `full100` below 0.** Content outside the
   doses' region (below about 1.6 kHz, above about 10 kHz, or the frames and bins outside E_st's
   mask restricted to where C′ is present) matters. **The gate metric must widen before option 2
   is built.** Descriptively (per amp 8 parts, crunch 5, no intervals): on SW50R and crunch the
   region made little difference; on AC20 and PR12 clean parts it carried most of it.
4. **The dose shape: undecided** (S50 reads convex by 0.004, S25 proportional, both intervals
   very wide). The cut that matters, within E_st's region, is `dose100`'s 47%. Given reading 3,
   that cut is of limited use: E_st's region holds about a third of the full-band field's gain.
5. **The control: undecided,** so readings 1–4 carry the declared caveat that some of the gain may be
   generic short-time modulation or processing. The post-hoc `full100` − `shift100` (+0.116
   [+0.011, +0.221]) equals `full100` − `cprime_eq` because `shift100` ≈ `cprime_eq`; it is not a
   control for the full-band probes.
6. **Fixed mask:** no primary's gain changes with the anchor's mask; the gains are not
   activity-mask artefacts.

**Where the remaining gap lies (hedged; one construction per probe, development parts, an
oracle):**
- After the leak-free EQ, about three quarters of what is left is recovered by giving the rebuild
  the true short-time magnitude over the **whole band**, with C′'s phase, its long-term balance
  held. Together with the EQ that is about 0.86 of C′'s gap.
- **The 2–8 kHz treble on E_st's mask is probably not where most of it is.** That region gives
  about a quarter of the remainder (0.25 [0.01, 0.59]), and the full-band field gains three times
  as much for a similar E_st cut. This qualifies the rebuild-gap study's "above 2 kHz": stage R's
  `high` (0.81 of the gap) also restored phase, the band above 8 kHz and much of the long-term
  balance, so it did not isolate the 2–8 kHz short-time magnitude. It is consistent with `stm`'s
  null, which a small cut in this region would also explain (`dose25`, a 15% cut, +0.013, undecided).
- **Which part of the outside matters is not separated:** below 1.6 kHz, above 10 kHz, the
  ⅓-octave edges around 2 and 8 kHz, and the frames and bins outside the doses' mask all changed
  together between `dose100` and `full100`.
- **About a quarter stays** even with full-band true magnitude (truth − `full100` +0.041 [+0.021,
  +0.061]; part-weighted, its interval includes 0), so some of the gap is in what C′'s phase, or
  the resynthesis, can't carry.
- **Not shown:** that a network can learn this field from C′'s output alone. The oracle gives the
  ceiling, not the reach.

### What it implies for the next build

- **Option 2 as a full-band field.** A zero-initialised, bounded per-bin, per-frame log-gain on the
  STFT of C′'s own output (after the leak-free EQ), resynthesised once with C′'s phase, over all
  bins and the interior frames. **Its oracle ceiling is `full100`: about 0.74 of the remainder,
  0.86 of C′'s gap.** A 2–8 kHz version would cap at about `dose100`'s 0.25 (0.25 [0.01, 0.59] of
  the remainder; the oracle's upper end is above half).
- **No consistency machinery:** Griffin–Lim steps or a phase output add nothing measurable over one
  resynthesis.
- **Its loss and gate need a full-band short-time error,** not E_st's 2–8 kHz. `full100`'s E_st
  cut (52%) says little about its gain; the gate metric should be the full-band, offset-removed
  short-time magnitude error over the frames where the truth is present, with the cut `full100`
  reaches on it as the reference.
- **The ±12 dB bound** was checked only for the 2–8 kHz field (43% against 47% of cut); it has to
  be re-measured on the full-band field, whose truths are peakier (`full100` peaks up to 4.1 dB
  over max(anchor, truth)).
- **The control's caveat** (undecided) applies; a full-band shifted control would close it.

### The next step (a proposal, not yet planned or reviewed)

1. **Zero renders first: the full-band gate metric.** Define the full-band offset-removed short-time
   error (E_st's definition on all bins and E_st's frame mask), measure it on the 24 parts for
   every probe here, and check it orders their rendered gains (per probe and per part) better than
   E_st does. Re-measure the ±12 dB bound on `full100`'s field.
2. **A small localising probe, if it is cheap enough to be worth it** (about 2,400 renders, TR's
   design): `low100`, `full100`'s field restricted to below about 1.6 kHz, and `fullshift100`,
   `full100`'s field shifted by half the part (the control the full-band reading lacks). It says
   how much the low band carries (the band above 10 kHz, the edges and the masked-out frames would
   stay together in what is left), and closes reading 5 for the full band.
3. **Then option 2, full band,** trained against the full-band metric, gated on reaching a
   declared share of `full100`'s cut on it, rendered on these cells against `cprime_eq`, and then on
   fresh full mixes, the only yardstick for progress.
4. If the full-band head can't learn the field, the declared alternatives stay (a learned Morgan
   surrogate, or ranking trained in the plugin's own terms).

## Operational history

Four launches of `learn/rebuild_dose_run.zsh` (`logs/run.log`), all on R1:

1. **12:52, commit b12cdd2: a missing folder.** Each of the three lanes rendered its first cell's
   comparators and 49 `dose100` renders, then failed writing the score file (the score folder was
   never created; `FileNotFoundError`). Fixed in #218. 159 renders, 126 recorded (the record was
   then saved every 12 renders); the other 33 are in `unrecorded.json`.
2. **13:34, commit 8fe087d: the declared stop.** Lane 0 resumed Drag_Me_Down ac20 and completed six
   new `dose100` cells. Lane 1, on It_Was_My_Fault ElecGtr1 pr12, stopped on the S-against-warm-up
   check (0.0171 on half A); STOP.json then stopped the other lanes. The
   [audit](audits/dose-stop-2026-10-18.md) (70 renders) found a plugin start transient exposed by
   that part's quiet opening; [amendment 2](dose-probe-plan.md#amendment-2-2026-10-18-after-the-stop-before-any-re-run)
   (#222) added the priming render and the Σ-order repeat check, and the cell was cleared under it.
   369 renders (cumulative 528; the log's 495 lacked the 33).
3. **14:46, commit a99bf60: the disk guard.** The lanes waited for free render slots until 17:42.
   Lane 1 started at 17:42, re-rendered the stopped cell (60 renders, with the repeat check) and
   stopped on this step's 31 GB disk guard at 17:44 (`resumable`); lane 2 stopped on it at its
   start, 17:44. Lane 0 started at 17:45, rendered Russian_Cream's comparators and `dose100` (54)
   and all five other probes on its 8 cells, and finished at 18:41. R1 incomplete; 2,114 renders
   (cumulative 2,642).
4. **18:46, commit 5fe3c5d: the resume.** Lane 0 found its cells done. Lanes 1 and 2 rendered the
   remaining 16 cells: comparators on 14 of them, and every probe still missing (all six on 15
   cells, five on the stopped cell), done at 19:58. 4,806 renders.

**Cells mixed across launches are scored the same way:**
- **The scoring code** (`learn/rebuild_dose.py`, `rebuild_gap`, `local_objective`) did not change
  between the third and fourth launches. Between the second and third it changed only for amendment
  2 (the priming render, the repeat check, `clear`, the count). Every cell's score file is written
  once, at the cell's end, from that run's renders; a cell interrupted mid-way restarts from its
  priming render, so no cell holds scores from two runs.
- **The renderer changed:** the fourth launch's commit includes #224 (at most four DI files kept on
  disk) and #226 (learn's renders through a bounded-memory copy of the render server; 22 of 22
  renders bit-identical to the shipped server's in its verification). So lane 0's 8 cells (every
  probe) and the stopped cell's `dose100` were rendered with the shipped server, and the other 16
  cells' probes with the bounded one. Both comparators passed on every cell (largest 1.3e-4 and
  5.9e-5); 14 of the 16 cells' comparators ran in the fourth launch, so they check the bounded
  server directly. The two It_Was_My_Fault cells' comparators ran in the first launch (shipped
  server).
- **Priming:** 7 `dose100` cells kept from the first two launches had no priming render, as
  amendment 2 declared (their S checks 0 to 2.3e-7); every other (cell, probe) had one.
