# The rebuild's short-time treble: results (2026-10-18)

Run under the [plan](rebuild-tone-plan.md); its amendment 1 governs. Development data only: step
3's 24 parts, Σ `ee91f710947dbb5c`, the PR12 training cache. Outputs are in
`~/ndsp-presets/learn/rebuild-tone/` (`report.json`, `gate.json`, `diag.json`, `scores/`,
`renders/`, `models-*`, `logs/`). Every declared stage ran: the curve, the fine-tunes, the gate,
J1 for both groups (J2 not due). The run started 2026-10-17 21:10 and logged `all done (GPU lane 0,
CPU lane 0; renders 8280)` at 2026-10-18 10:46.

- **Audited 2026-10-18 by an independent agent; changes:** it recomputed every figure from the
  stored scores, logs and records with its own code (the primaries with its own band-clustered t),
  and all matched except two roundings; it confirmed the leak rules (the curve reproduces exactly
  without the 19 recordings; selection only on the validation bands), the arm/control matching,
  the J2 decisions, the 8,280 renders and the restart. Changes:
  - the headline's "did not raise ranking" and "this loss doesn't help is shown" softened to no
    measurable gain, with the interval's upper end (about 0.16 of the gap);
  - the reconciliation rewritten: the plan's declared reading kept as the main one, "too little of
    the right error" as a weakly supported post-hoc alternative; `onset` and the probes'
    non-monotone gains added; "fixed most of the long-term balance" made "much of";
  - `stm` − `ctl_stm` split corrected (about half from each side band-weighted);
  - the second seed's E_st rise restricted to the gate (on the amp tracks it is not repeated);
  - the part-weighted intervals' lack of band clustering, and the parts carrying them, stated;
  - `cprime_eq` described as reproducing R's `dep_eq`, not replicating it, with amendment 5's
    caveat in the headline;
  - the controls' lean worded as slightly negative on three runs (two seeds), each interval
    containing 0;
  - the incident: the sender not in the logs, the renamed log, and the one-line
    `local_objective.py` change between the run commits;
  - `stm_eq`'s share 0.41, `cprime_eq`'s projected bound −0.021;
  - near S labelled post hoc, with the count of intervals computed and the other leads named;
  - the E_st baseline against the plan's and TR's 8.87 dB explained;
  - the missing secondary rows added (per amp/class, truth − arm, shares, the gate's
    recording-clustered figures);
  - also taken: medians over the controls, `stm`'s 3–8 kHz coherence on the gate, recon 0.07, the
    dose probe's LSD and an `onset`-type control.
- **Reading these figures:** post-hoc development estimates, a further unblinded use of the 24
  parts and Σ after experiments 1–1d and the rebuild-gap study. Fidelity is the cross-half local
  Spearman against the amp track (1 means perfect local ranking).
  - Every figure is band-weighted with a 90% band-clustered t interval (13 df on the 14 bands), the
    leave-one-band-out (LOBO) range and the bands above/below 0, unless it says otherwise.
- **Multiplicity:** 7 primaries, 9 secondaries, each with part-weighted, reliable-pair, per-amp,
  per-class, no-high-bleed and 4 near-S rows, on the same 24 cells. Read the families, not single
  intervals.

## Headline

**The short-time treble loss (`stm`) lowered the error it targets, clearly, and did not
measurably improve rendered ranking.**
- **Its error fell everywhere it was measured.** On the held-out gate crops, E_st fell −0.544
  [−0.586, −0.502] dB against C′. On the 24 parts' amp tracks it fell −0.634 [−0.746, −0.523] dB,
  lower on all 24 parts.
- **Its ranking barely moved; any gain at this strength is small:**
  - `stm` − C′: +0.012 [−0.023, +0.047], 7/7 bands (the upper end is about 0.16 of the gap);
  - `stm` − `ctl_stm`: +0.024 [−0.006, +0.054], 8/6;
  - on top of the leak-free long-term EQ, `stm_eq` − `cprime_eq`: −0.012 [−0.038, +0.014], 8/6.
- **So this loss does not capture the stage-R lever** (the structured short-time magnitude). The
  plan's declared reading follows: the short-time error a network learns to lower here is not the
  one that costs ranking. A post-hoc alternative remains open: the loss moved E_st by only about 8%
  of C′'s error (7.57 → 6.99 dB on the amp tracks), while the stage-R probes that recovered most of
  the gap moved it by 39–98% and fixed much of the long-term balance too. The probes' gains are not
  ordered by their E_st cut, though, so they don't clearly support it
  ([reconciliation](#reconciling-with-stage-r)).

**The long-term balance levers lean positive, hold up on a second seed or a leak-free curve, and are
still undecided:**
- **`rank`'s second seed** (`rank_s1`) − C′: +0.099 [−0.036, +0.233], against stage TR's +0.075.
  Seed-pooled `rank` − C′: +0.087 [−0.031, +0.204]. Against the matched controls: `rank_s1` −
  `ctl_s1` +0.126 [−0.017, +0.269]; pooled +0.115 [−0.007, +0.238].
  - The per-part gain over the control agrees across seeds (Spearman +0.81). Part-weighted (a t on
    the 24 parts without band clustering, less conservative than the declared interval) every one
    of these excludes 0; Eggy (3 parts) and Doom Flamingo (2) carry much of that.
- **The leak-free long-term EQ** (`cprime_eq` − C′; a secondary): +0.132 [−0.030, +0.294], 9/5.
  Stage R's `dep_eq` read +0.133 with a curve that included 17 of the 24 parts' recordings. It is
  the same C′ rebuild on the same cells with a curve 1.23 dB RMS away, so this reproduces R's
  figure rather than replicating it independently (per part, Spearman +0.98). Taking the test parts
  out of the curve and changing the scoring configuration together left it unchanged; the two
  can't be separated.
- **No group extended to J2.** The closest was pooled `rank` − pooled `ctl`, whose projected lower
  bound was −0.0006; it was not a declared extension contrast.

**Proposed next** ([below](#the-next-step-a-proposal-not-yet-planned-or-reviewed)), hedged:
- first, an oracle dose probe that isolates the short-time component on top of the leak-free EQ
  (renders only, no training): how much of the remaining gap it carries, and how large an E_st cut
  is needed;
- if it carries the remainder, then option 2 of the
  [HF research](research/hf-detail-losses-2026-10.md): a bounded per-bin log-gain on C′'s own
  output, gated on reaching that size of cut.

## Renders used

**8,280 renders**, exactly the J1 declared (5,928 for group 1 and 2,352 for group 2). J2 rendered
nothing. The plan expected about 8–13k.
- 7 arms × 24 cells × 49 (48 settings and a warm-up) = 8,232, plus the arm comparator's 48.
- Every render record holds 49 renders. `report.json`'s `renders.total` (8,280) counts each warm-up
  once.
- No render was lost or redone. The [incident](#operational-incident) hit training only, before any
  render.

**Guards, all within tolerance:**
- **Comparator** (C′'s 1b rebuild at S, warm-up and S, against 1b's stored score): largest
  deviation 1.3e-4 over 24 cells; tolerance 0.005.
- **Each cell's S against its warm-up:** largest 7.4e-4 (tolerance 0.005).
- **FLAC against float at S:** largest 3.2e-5.
- **Rebuild checks** (`arms/check.json`): all 7 arms pass on all 24 parts (lag against the source,
  −22.9 LUFS, the leak assertions). Each EQ arm passed its own checks too (same length, GCC within 3
  samples, −22.9 ± 0.05 LUFS).

**MPS:** about 12.6 h (`stm` 5.5 h, `ctl_stm` 3.3 h, `rank_s1` 3.1 h, `ctl_s1` 0.6 h), plus about
0.3 h lost to the incident. The plan expected 7–14 h. Wall clock 13.6 h.

## The curve (zero renders)

Built as declared: `average-fold2.npy`'s construction without the 19 DI recordings of the 24 parts.
- 4,734 rows out of 15,319, 10,585 kept; no part lacked a DI name.
- It sits 1.23 dB RMS (80 Hz–8 kHz) from `average-fold2.npy`, at most 3.2 dB.
- The curve was built at 21:10 and rebuilt at the 01:28 restart; both builds logged identical
  figures.

## Stage T: the fine-tunes (zero renders, MPS)

**Weights by the declared share rule** (50 calibration batches of C′, seeds 2 and 3):
- `stm`: λ_st 0.404–0.419 across folds, against C′'s loss of 5.06–5.61;
- `rank_s1`: λ_rank 2.54–3.01, λ_match 0.55–0.59, the same as stage T's (the calibration seeds are
  the same).

**Training pools** as stage T's: 10,467–12,593 rows; validation 2,715–2,788 rows on the two held-out
bands per fold; no step was skipped and none needed a recovery, in any of the 16 runs.

### `stm` and its control (seed 0; selected on E_st over the 96 selection crops)

| Fold | Validation bands | E_st step 0 | `stm` best step | E_st at best | Steps run | `ctl_stm` E_st at that step | Recon at the kept step: `stm` / `ctl_stm` (step 0) |
|---|---|---|---|---|---|---|---|
| 0 | Eat The Feeder, Zeno | 6.25 | 2,750 | 5.81 (−0.44) | 4,000 (cap) | 6.38 | 39.29 / 39.17 (38.25) |
| 1 | Adam Buckley, Starnes And Shah | 6.42 | 1,750 | 6.04 (−0.38) | 3,250 | 6.45 | 39.24 / 38.96 (37.66) |
| 2 | Starnes And Shah, Swatkins | 6.63 | **4,000** | 6.01 (−0.63) | 4,000 (cap) | 6.65 | 35.57 / 35.51 (35.54) |
| 3 | Swatkins, Zeno | 7.12 | 3,500 | 6.40 (−0.72) | 4,000 (cap) | 7.23 | 44.03 / 43.55 (42.60) |

- **Fold 2's best checkpoint is at the step cap (4,000): possibly still improving.** Its E_st was
  still falling at the end (6.028 at 3,250, 6.015 at 3,750, 6.008 at 4,000).
- **Folds 0 and 3 were also stopped by the cap,** before the full 1,500 steps of patience:
  - fold 3's best is 500 steps before the cap (its last two checks were 0.005 and 0.007 dB higher);
  - fold 0's best is 1,250 steps before it. Its 3,250 check was 0.012 dB lower, under the 0.02-dB
    rule.
  - So on 3 of 4 folds `stm` had not clearly flattened. The learning-rate schedule ends at its floor
    (2e-5) at step 4,000, so more steps would mean a longer schedule.
- **The control stopped at `stm`'s best step** on every fold (2,750, 1,750, 4,000, 3,500), as
  declared. More of C′'s own loss raised E_st a little (+0.02 to +0.12 on these crops).
- **`stm` costs little reconstruction:** its validation recon sits 0.07–0.48 above `ctl_stm`'s at
  the kept step.

### `rank_s1` and its control (seed 1; selected on proxy fidelity, as stage T)

| Fold | Proxy step 0 | `rank_s1` best step | Best proxy | Steps run | `ctl_s1` proxy at that step | E_st at the kept step: `rank_s1` / `ctl_s1` | Recon: `rank_s1` / `ctl_s1` |
|---|---|---|---|---|---|---|---|
| 0 | 0.537 | 250 | 0.674 | 1,750 | 0.485 | 6.29 / 6.29 | 39.00 / 38.60 |
| 1 | 0.434 | 250 | 0.582 | 1,750 | 0.333 | 6.59 / 6.45 | 39.23 / 38.28 |
| 2 | 0.354 | 1,250 | 0.670 | 2,750 | 0.400 | 6.96 / 6.64 | 36.99 / 35.46 |
| 3 | 0.421 | 500 | 0.592 | 2,000 | 0.367 | 7.19 / 7.15 | 44.30 / 42.96 |

- **Every fold stopped early,** 1,500 steps after its best; none at the cap and none at step 0.
- **The kept checkpoints are early on folds 0 and 1** (step 250, the first check). The validation
  proxy is as noisy as in stage T: fold 1 runs 0.39–0.53 after its best of 0.58, fold 2 0.41–0.67 over its checks. So the
  kept proxy (+0.14 to +0.32 over step 0) is optimistic, as in stage T, and the control is not
  selected, so `rank_s1` − `ctl_s1` keeps stage T's selection asymmetry.
  - Stage T's seed 0 kept steps 500, 1,000, 1,000 and 250.

## Stage G: the zero-render gate

On 768 gate crops (192 per fold, from the selection bands, outside the 96 selection crops); each
crop scored by its fold's network. Band-clustered over the 5 validation bands (4 df), with the
recording-clustered figure beside it:

| Contrast | E_st (dB) | LSD (dB) | Coherence 1–3 kHz | Coherence 3–8 kHz |
|---|---|---|---|---|
| **`stm` − C′** | **−0.544 [−0.586, −0.502]**, 0/5; rec. −0.583 | +0.577 [+0.231, +0.922] | +0.062 | −0.010 |
| **`stm` − `ctl_stm`** | **−0.624 [−0.725, −0.523]**, 0/5; rec. −0.665 | +0.369 [+0.085, +0.653] | +0.052 | −0.009 |
| `ctl_stm` − C′ | +0.080 [+0.020, +0.140]; rec. +0.083 | +0.208 | +0.010 | −0.001 |
| stage T's `rank` − C′ | +0.211 [+0.151, +0.270]; rec. +0.190 | −0.478 [−0.906, −0.050] | −0.033 | −0.007 |
| stage T's `ctl` − C′ | +0.036 [−0.008, +0.079]; rec. +0.037 | +0.218 | +0.007 | −0.001 |
| `rank_s1` − C′ | +0.164 [+0.070, +0.257]; rec. +0.123 | −0.564 [−0.885, −0.243] | −0.031 | −0.006 |
| `ctl_s1` − C′ | +0.030 [+0.005, +0.054]; rec. +0.028 | +0.267 | +0.003 | +0.000 |
| `rank_s1` − `ctl_s1` | +0.134 [+0.033, +0.235]; rec. +0.095 | −0.831 [−1.203, −0.459] | −0.034 | −0.006 |

- **The declared rule** (`stm`'s four arms render if `stm` − C′ on E_st is below 0): −0.544, so they
  rendered (`render stm: True`, 06:34).
- C′'s mean E_st on these crops is 6.65 dB, so `stm` lowered it by about 8%.
- **Both `rank` seeds raised E_st and lowered LSD,** as stage T's did: the second seed repeats
  the trade of short-time treble for long-term balance on these crops. `stm` did the opposite: lower
  E_st, higher LSD, higher 1–3 kHz coherence (and 3–8 kHz coherence slightly lower, −0.010, 5/5
  bands).

### The 24 parts (descriptive; each rebuild of the amp track against the measure DI)

Medians over the 24 parts, and the band-clustered difference against C′ with the parts lower
(`diag.json`; E_st's offset removed over the whole 10-s part):

| Rebuild | E_st (dB) | − C′ | LSD (dB) | − C′ | Coh. 1–3 kHz |
|---|---|---|---|---|---|
| C′ | 7.57 | | 3.30 | | 0.39 |
| `stm` | 6.99 | **−0.634 [−0.746, −0.523], 24/24 lower** | 3.45 | +0.371, 4/24 lower | 0.44 (higher on 24/24) |
| `ctl_stm` | 7.65 | +0.038 [−0.013, +0.089] | 3.42 | +0.158 | 0.41 |
| `stm_eq` | 7.00 | −0.626, 24/24 lower | 1.69 | −0.952, 20/24 lower | 0.45 |
| `ctl_stm_eq` | 7.65 | +0.042 | 1.61 | −1.016 | 0.41 |
| `cprime_eq` | 7.58 | +0.005 | 1.59 | −1.019, 20/24 lower | 0.39 |
| `rank` (stage TR) | 7.79 | +0.246, 4/24 lower | 2.52 | −0.618 | 0.33 |
| `rank_s1` | 7.72 | +0.093 [−0.017, +0.203] | 2.38 | −0.664, 20/24 lower | 0.34 |
| `ctl_s1` | 7.62 | +0.076 | 3.54 | +0.289 | 0.40 |

- **E_st here and in earlier documents.** The plan's "Why" and the TR write-up give C′ 8.87 dB on
  the amp tracks (`rank` 8.97), from TR's ad hoc script. The declared metric (`rebuild_tone_train.est`,
  this table) gives 7.57 (`rank` 7.79) on the same tracks; neither this write-up nor the audit could
  reproduce 8.87 (alignment variants give 7.57–7.63), so the difference is an unrecorded detail of
  that earlier script. Within each, comparisons are paired and agree in direction. With the declared
  metric the amp tracks sit about 0.5–1.3 dB above the PR12 selection crops (6.25–7.12), not 2.6.
- **The in-domain change carried to the real amp tracks in full:** −0.63 dB here against −0.54 on
  the gate. So the plan's "domain gap" reading (lower on the gate, not on the 24) doesn't apply.
- The EQ arms leave E_st unchanged (it removes each bin's offset, by design) and cut LSD by about
  1 dB.

## Stage J: rendered judgement (J1, 24 cells, 14 bands)

**Fidelity on the same 24 cells:** the truth 0.850 [0.732, 0.967]; C′ 0.561 [0.407, 0.715]; `stm`
0.573; `ctl_stm` 0.550; `cprime_eq` 0.693 [0.556, 0.829]; `stm_eq` 0.681; `ctl_stm_eq` 0.701;
stage TR's `rank` 0.636; `rank_s1` 0.660 [0.559, 0.760]; `ctl_s1` 0.533; pooled `rank` 0.648,
pooled `ctl` 0.533. The gap, truth − C′, is +0.289.

### The primaries

| Contrast | Estimate | LOBO | Bands +/− | Part-weighted | Reliable-pair accuracy Δ | No high bleed (20 cells) |
|---|---|---|---|---|---|---|
| **`stm` − C′** | **+0.012 [−0.023, +0.047]** | +0.002 to +0.020 | 7/7 | +0.014 [−0.019, +0.048] | +0.009 [−0.008, +0.026], 7/7 | +0.005 [−0.028, +0.039] |
| **`stm` − `ctl_stm`** | **+0.024 [−0.006, +0.054]** | +0.015 to +0.030 | 8/6 | +0.041 [+0.013, +0.069] | +0.010 [−0.004, +0.024], 8/6 | +0.025 [−0.005, +0.055] |
| **`stm_eq` − `cprime_eq`** | **−0.012 [−0.038, +0.014]** | −0.019 to −0.002 | 8/6 | −0.008 [−0.030, +0.014] | −0.007 [−0.021, +0.006], 7/7 | −0.013 [−0.039, +0.013] |
| **`rank_s1` − C′** | **+0.099 [−0.036, +0.233]** | +0.062 to +0.137 | 9/5 | +0.173 [+0.028, +0.318] | +0.047 [−0.007, +0.101], 10/4 | +0.083 [−0.043, +0.210] |
| **pooled `rank` − C′** | **+0.087 [−0.031, +0.204]** | +0.050 to +0.118 | 7/7 | +0.155 [+0.029, +0.281] | +0.042 [−0.005, +0.089], 9/5 | +0.071 [−0.034, +0.177] |
| `rank_s1` − `ctl_s1` | +0.126 [−0.017, +0.269] | +0.082 to +0.165 | 7/7 | +0.213 [+0.057, +0.369] | +0.054 [−0.004, +0.112], 9/5 | +0.112 [−0.020, +0.244] |
| pooled `rank` − pooled `ctl` | +0.115 [−0.007, +0.238] | +0.075 to +0.146 | 8/6 | +0.187 [+0.054, +0.320] | **+0.052 [+0.002, +0.101]**, 10/4 | +0.099 [−0.009, +0.207] |

- **Share of the gap** (against C′, Fieller): `stm` 0.04 [−0.17, 0.13]; `rank_s1` 0.34 [−0.26,
  0.64]; pooled `rank` 0.30 [−0.23, 0.56].
- **Truth − arm:** `stm` +0.276 [+0.113, +0.440]; `rank_s1` +0.190 [+0.072, +0.308]; pooled `rank`
  +0.202 [+0.083, +0.320]; `stm_eq` +0.169 [+0.084, +0.254].
- The no-high-bleed rows (First Offering GTR_1, Gym Hours GTR_1, Long Way Home and Sculptor's
  Request GTR_1 out) read the same way, a little smaller for `rank`.

**Per amp and class** (descriptive; per amp 8 parts, crunch 5):

| Contrast | AC20 | PR12 | SW50R | Clean | Crunch |
|---|---|---|---|---|---|
| `stm` − C′ | +0.019 | +0.014 | +0.020 | +0.037 | −0.032 |
| `stm` − `ctl_stm` | +0.024 | +0.032 | +0.045 | +0.042 | −0.009 |
| `stm_eq` − `cprime_eq` | −0.005 | −0.029 | −0.000 | −0.002 | −0.030 |
| `rank_s1` − C′ | +0.131 | +0.317 | +0.040 | +0.180 | −0.049 |
| pooled `rank` − C′ | +0.093 | +0.303 | +0.052 | +0.157 | −0.038 |
| `rank_s1` − `ctl_s1` | +0.155 | +0.361 | +0.081 | +0.218 | −0.040 |
| pooled `rank` − pooled `ctl` | +0.111 | +0.333 | +0.101 | +0.185 | −0.011 |
| `cprime_eq` − C′ | +0.105 | +0.414 | +0.059 | +0.216 | −0.019 |
| *gap: truth − C′* | +0.347 | +0.612 | +0.081 | +0.419 | +0.055 |

As in stage R and TR, the long-term levers gain where the gap is (PR12, clean parts) and nothing on
crunch, which has almost no gap.

**Per fold** (part means; descriptive, 6, 10, 3 and 5 parts):
- `stm` − C′: +0.015, −0.001, −0.008, +0.058; `stm` − `ctl_stm`: +0.033, +0.051, +0.004, +0.053.
  Fold 2, whose `stm` was possibly still improving, shows nothing, but it has 3 parts.
- `rank_s1` − C′: +0.129, +0.202, +0.007, +0.267 (stage TR's seed 0: +0.06, +0.15, −0.01, +0.29).
- `cprime_eq` − C′: +0.246, +0.116, −0.171, +0.458.

**Near S** (post hoc: the plan declared no near-S rows. A1's knob families, 3-way agreement on S's
±1/8 neighbourhood, computed for this write-up with stage TR's method, which reproduces TR's
`rank` rows). Few bands differ from 0 here; 64 intervals were computed and these are the leads:
- `stm` − C′: input gain +0.036, amp gain −0.040, amp tone +0.027, cab +0.027 [+0.001, +0.052];
  all but cab contain 0.
- `stm` − `ctl_stm`: input gain +0.101 [+0.013, +0.189] (4/0 bands), cab +0.025 [+0.000, +0.049];
  amp gain and tone near 0.
- `stm_eq` − `cprime_eq`: cab −0.033 [−0.053, −0.012] (0/6); the rest contain 0.
- `rank_s1` − C′ and pooled `rank` − C′: every family +0.01 to +0.07, each interval containing 0.
- **`cprime_eq` − C′ leans worse on gain staging near S:** amp gain −0.127 [−0.206, −0.048], 0/6
  bands. That reproduces stage R's `dep_eq` (−0.110 [−0.192, −0.028]) with the leak-free curve.
  Its gain on all of Σ comes from pairs farther from S (an inference).
- Of the 64 near-S intervals computed (16 contrasts × 4 families), the others that exclude 0 are
  `stm_eq` − C′ amp gain −0.159 [−0.287, −0.030] and `stm_eq` − `rank` amp gain −0.185 [−0.334,
  −0.035], both carrying the EQ's lean; every other one contains 0.

### The secondaries

| Contrast | Estimate | LOBO | Bands +/− | Part-weighted | Reliable-pair Δ | No high bleed |
|---|---|---|---|---|---|---|
| **`cprime_eq` − C′** (leak-free `dep_eq`) | **+0.132 [−0.030, +0.294]** | +0.084 to +0.185 | 9/5 | +0.184 [+0.010, +0.358] | +0.064 [+0.001, +0.126] | +0.105 [−0.043, +0.253] |
| `stm_eq` − `ctl_stm_eq` | −0.020 [−0.054, +0.013] | −0.030 to −0.009 | 7/7 | −0.006 [−0.032, +0.021] | −0.016 [−0.041, +0.009] | −0.020 [−0.054, +0.014] |
| `ctl_stm_eq` − `cprime_eq` | +0.008 [−0.014, +0.031] | −0.002 to +0.013 | 9/5 | −0.002 [−0.022, +0.018] | +0.008 [−0.007, +0.024] | +0.007 [−0.016, +0.031] |
| `stm_eq` − C′ | +0.120 [−0.054, +0.294] | +0.072 to +0.174 | 8/6 | +0.176 [−0.006, +0.357] | +0.056 [−0.013, +0.126] | +0.093 [−0.067, +0.252] |
| `ctl_stm` − C′ | −0.011 [−0.035, +0.012] | −0.018 to −0.006 | 6/8 | −0.027 [−0.062, +0.009] | −0.001 [−0.012, +0.011] | −0.020 [−0.048, +0.008] |
| `ctl_s1` − C′ | −0.028 [−0.061, +0.005] | −0.038 to −0.017 | 7/7 | −0.040 [−0.069, −0.011] | −0.007 [−0.022, +0.008] | −0.029 [−0.061, +0.004] |
| `stm` − `rank` (descriptive) | −0.063 [−0.147, +0.021] | −0.087 to −0.033 | 7/7 | −0.122 [−0.228, −0.017] | −0.028 [−0.065, +0.008] | −0.054 [−0.135, +0.026] |
| `stm_eq` − `rank` (descriptive) | +0.044 [−0.065, +0.154] | +0.009 to +0.086 | 7/7 | +0.039 [−0.060, +0.138] | +0.019 [−0.032, +0.070] | +0.033 [−0.077, +0.143] |
| `rank_s1` − `rank` (descriptive) | +0.023 [−0.034, +0.080] | +0.001 to +0.039 | 7/7 | +0.036 [−0.023, +0.095] | +0.010 [−0.014, +0.033] | +0.024 [−0.035, +0.083] |

- **Shares of the gap:** `cprime_eq` 0.46 [−0.26, 0.69]; `stm_eq` 0.41 [−0.46, 0.70]; `ctl_stm`
  −0.04 [−0.22, 0.04]; `ctl_s1` −0.10 [−0.30, 0.02].
- **Truth − arm:** `cprime_eq` +0.157 [+0.083, +0.230]; `stm_eq` +0.169 [+0.084, +0.254];
  `ctl_stm_eq` +0.149 [+0.072, +0.225]; `ctl_stm` +0.300 [+0.119, +0.481]; `ctl_s1` +0.316
  [+0.122, +0.511].
- **Per amp and class** (descriptive; AC20 / PR12 / SW50R; clean / crunch):
  - `stm_eq` − `ctl_stm_eq`: −0.052 / −0.003 / −0.002; −0.016 / −0.029;
  - `ctl_stm_eq` − `cprime_eq`: +0.048 / −0.026 / +0.002; +0.014 / −0.001;
  - `stm_eq` − C′: +0.100 / +0.385 / +0.059; +0.214 / −0.049;
  - `ctl_stm` − C′: −0.005 / −0.018 / −0.025; −0.005 / −0.023;
  - `ctl_s1` − C′: −0.024 / −0.044 / −0.042; −0.038 / −0.009;
  - `stm` − `rank`: −0.036 / −0.276 / −0.044; −0.096 / −0.004;
  - `stm_eq` − `rank`: +0.045 / +0.095 / −0.006; +0.081 / −0.021;
  - `rank_s1` − `rank`: +0.076 / +0.027 / −0.025; +0.047 / −0.021.
  - Every row is also in `report.json` (`r1`).
- **What remains after the leak-free EQ is decided:** truth − `cprime_eq` +0.157 [+0.083, +0.230],
  13/1 bands.
- **More fine-tuning on C′'s loss alone leans slightly negative on three control runs (two seeds),
  each band-weighted interval containing 0:**
  `ctl_stm` −0.011, `ctl_s1` −0.028 (part-weighted −0.040 [−0.069, −0.011]), stage TR's `ctl`
  −0.029.

### J1 → J2: the stopping rule

The narrowing ratio is the stored 0.948. A group extends if one of its declared contrasts is
positive, its J1 interval contains 0, and the interval narrowed by the ratio excludes 0. Projected
lower bounds:
- group `stm`: `stm` − C′ −0.021; `stm` − `ctl_stm` −0.005;
- group `eq`: `stm_eq` − `cprime_eq` is negative (it can't extend); `cprime_eq` − C′ −0.021;
- group `seed`: `rank_s1` − C′ −0.029.
- **So no group extended** (`TR1 report: extend []`, `TR2: no group extends`).
- Beside the rule (not declared extension contrasts): pooled `rank` − pooled `ctl` −0.0006 and
  `rank_s1` − `ctl_s1` −0.009.

## Reading

**By the plan's declared readings:**
- **"E_st lower on the gate and on the 24 parts, but no rendered gain"** is the outcome (no gain
  that can be told from 0). The plan reads it as: the short-time treble error a network can learn
  to lower is not the one that costs ranking, and the next lever is elsewhere (a learned Morgan
  surrogate, or ranking-trained in the plugin's own terms). **That is the main reading here.**
  - **One post-hoc qualification:** the loss moved E_st by about 8% of C′'s error, while the probes
    that recovered most of the gap in stage R moved it by 39–98%. So "too little of the right
    error" can't be excluded, though the probes' gains don't clearly support it
    ([below](#reconciling-with-stage-r)). The proposal below checks it with one oracle probe
    before anything is built; the declared alternatives follow if it fails.
- **`stm_eq` − `cprime_eq` near 0:** on top of a long-term fix the short-time change adds at most
  about +0.014 (0.05 of the gap) by the interval's upper end, at this strength. The fully
  controlled `stm_eq` − `ctl_stm_eq` reads −0.020 [−0.054, +0.013].
- **`stm` − `ctl_stm` leans positive** (+0.024 [−0.006, +0.054]; part-weighted +0.041 [+0.013,
  +0.069]). Band-weighted, about half of it is `stm` above C′ (+0.012) and half `ctl_stm` below it
  (−0.011); part-weighted it is mostly the control (+0.014 against −0.027). It is undecided, and it did not meet the extension rule.
- **`rank_s1`: a second seed near the first strengthens `rank`.** It reads +0.099 against stage TR's
  +0.075 (`rank_s1` − `rank` +0.023 [−0.034, +0.080]). Its gain over its control follows seed 0's
  part by part (Spearman +0.81 between the two seeds' `rank` − `ctl`; the two share no arm). Both
  are still undecided band-weighted.
  - What tempers it: the checkpoints are the best of noisy proxy checks (two folds kept step 250),
    the control is not selected, and the median part gains only +0.013 to +0.032 over C′ (pooled
    and `rank_s1`; +0.018 and +0.023 over the controls).
  - It again looks like a learned long-term EQ: both seeds lower LSD and coherence. On the gate
    crops both raise E_st; on the 24 amp tracks the second seed does not repeat that (`rank_s1` − C′
    +0.093 [−0.017, +0.203], lower on 13 of 24; about 0 against its control, against seed 0's +0.20);
    pooled `rank`'s per-part gain follows `cprime_eq`'s (Spearman +0.84, partly built in by the
    shared C′ term).
- **`cprime_eq`: `dep_eq` survives a curve free of the test parts.** It reads +0.132 against R's
  +0.133; reliable-pair accuracy +0.064 [+0.001, +0.126] and part-weighted +0.184 [+0.010, +0.358]
  exclude 0, band-weighted does not.
  - Both the curve and the scoring configuration changed from stage R, and the result is the same.
    So neither seems to matter much here, but the two can't be separated. It is a re-measurement of
    the same rebuild, not an independent replication.
  - Its caveats stay: it gains on PR12 and clean parts, leans worse on gain staging near S, and
    part of its gain is agreement with the yardstick's own normalisation (the measure DI is EQ'd
    to `average-fold2.npy`, which the leak-free curve sits 1.23 dB RMS from).

### Reconciling with stage R

Stage R's `mag` probe gave the rebuild the true 21-ms magnitude, **both its long-term balance and its
short-time structure**, and recovered the whole gap. `high` did the same above 2 kHz. This step
splits the two:

- **The long-term part alone** (the leak-free EQ, no true DI): +0.132, about 0.46 of the gap, the
  same as R's `dep_eq`. `rank` (two seeds) reaches about 0.30 by what looks like the same route.
- **What remains after it is real:** truth − `cprime_eq` +0.157 [+0.083, +0.230], 13/1 bands. On R's
  evidence it lives in the short-time magnitude (with true magnitude the rebuild reaches the
  truth; with true phase it gains nothing).
- **The short-time part, as this loss moved it, gave nothing measurable:** −0.012 [−0.038, +0.014]
  on top of the EQ.

**E_st of stage R's stored probes** (computed for this write-up, zero renders; each probe against the
measure DI on its own timeline, median over the 24 parts; R's rendered gains against `rot`/`reb`):

| Rebuild | E_st (dB) | Cut from C′ | LSD (dB, R) | Rendered gain (share of the gap) |
|---|---|---|---|---|
| C′ (`reb`) | 7.57 | — | 3.3 | — |
| `dep_eq` / `cprime_eq` | 7.58 | 0% | 0.8 / 1.6 | 0.46 |
| `stm` | 6.99 | 8% | 3.4 | 0.04 |
| `phase` | 6.50 | 14% | 3.6 | −0.10 |
| `onset` | 6.70 | 12% | 1.9 | 0.40 |
| `noise` | 4.59 | 39% | 1.3 | 0.92 |
| `half` | 4.08 | 46% | 2.3 | 0.51 |
| `sustain` | 3.06 | 60% | 0.6 | 1.06 |
| `mag` | 2.08 | 73% | 0.2 | 1.05 |
| `high` | 0.12 | 98% | 1.9 | 0.81 |

What the combined evidence implies (hedged; post hoc, one seed of `stm`):
- **The main reading is the plan's declared one:** the short-time treble error that this network
  learned to lower is not the error that costs ranking. `stm` cut E_st on every part and moved
  ranking by an amount that can't be told from 0.
- **A post-hoc alternative stays open, weakly supported: too little of the right error.**
  - For it: `stm` cut E_st by only 8%. Every probe that recovered most of the gap cut it by about
    40% or more and fixed much of the long-term balance too (`high` only from 3.3 to 1.9 dB LSD).
    The two changes that cut E_st by 8–14% with the long-term balance untouched (`stm`, `phase`)
    gained nothing, and a long-term fix alone gains about half.
  - A crude linear reading of `half` alone (a 46% cut with half the long-term error gone, share
    0.51) would predict something like +0.01 to +0.03 from an 8% cut, which these intervals can't
    tell from 0. That leans on one probe and is an inference, not a measurement.
  - Against it: the probes' gains are not ordered by their E_st cut. `noise` (39%) recovers 0.92
    and `half` (46%) 0.51; `sustain` (60%) 1.06 and `high` (98%) 0.81. `onset` cut only 12%, partly
    fixed the long-term balance (LSD 1.9) and recovered 0.40, about what the EQ alone gains. And
    `phase` cut 14% (through the 21-ms frames' phase sensitivity) and gained nothing. So the E_st
    cut is not established as a dose measure.
- **What the evidence doesn't contain:** no stage-R probe isolated the offset-removed short-time
  component with the long-term balance held fixed. The remaining half of the gap (+0.157 after the
  EQ) is real, and R places it in the magnitude, but not specifically in what E_st measures.
- **One probe would decide between the readings:** keep the leak-free EQ's long-term balance and
  C′'s phase, restore only the offset-removed short-time magnitude, at a few doses.

### The next step (a proposal, not yet planned or reviewed)

1. **Measure before building: a short-time oracle dose probe** (renders only, no training; about
   1,176 renders per dose on these 24 cells, TR's design).
   - Take `cprime_eq`'s rebuild and move its offset-removed short-time log-magnitude toward the
     measure DI's by a fraction (for example 25%, 50% and 100%), keeping its long-term spectrum
     and its phase.
     The 100% dose asks whether the short-time component carries the remaining +0.157. The
     smaller doses ask how large an E_st cut is needed before ranking moves.
   - Either above 2 kHz only (as E_st) or full-band, to test the 2 kHz edge. That choice is for
     the plan.
   - It is an oracle (it uses the true DI), so it is a diagnostic only. Report each dose's LSD
     too, and consider an `onset`-type control, so dose and long-term balance can be told apart.
2. **If the 100% dose recovers most of the remainder: option 2 of the
   [HF research](research/hf-detail-losses-2026-10.md).** That is a zero-initialised, bounded
   per-bin, per-frame log-gain on the STFT of C′'s own output, resynthesised with C′'s phase and
   applied after the leak-free EQ. Its ceiling is the 100% dose.
   - It would be trained with this step's loss, or a stronger weight of it. **The gate would require
     the E_st cut the dose curve says matters, not just a cut below 0,** since this step shows the
     loss can lower E_st without moving ranking.
   - The research's ±12 dB bound may sit below what the ceiling needs; the plan should check that
     against the probe's realised gains. A longer schedule, since 3 of 4 `stm` folds hadn't
     flattened at 4,000 steps.
3. **If even the 100% dose recovers little:** the remainder is not in the offset-removed short-time
   magnitude as E_st measures it. The plan's declared alternatives come next: a learned Morgan
   surrogate, or ranking trained in the plugin's own terms.
4. **Beside it, the long-term levers:** `cprime_eq` is a near-free product candidate (no training,
   test parts out of its curve) and the cheapest to carry into the fresh full-mix decision test.
   Pooled `rank` is close behind, and the two may not add (their gains follow each other, +0.84).
   Neither is decided on the 24 parts; the fresh full-mix test is the one that counts.

## Operational incident

**stm fold 2 was killed at 01:22**, 17 minutes into its training. It is attributed to a stray
`kill` from another session: the log simply stops, with no traceback, and nothing in the logs
records the sender. This step's code showed no fault.
- The runner logged `T stm s0 fold 2 FAILED`, `GPU STM FAILED`, `stage 1 not started (GPU failed)`
  and `all done (GPU lane 1, CPU lane 1; renders )`. No gate, rebuild or render had started. Its
  FAILED line points to `train-stm-s0-f2.log`; the partial log was renamed by hand to
  `-killed1` before the restart, so that name now holds the restarted run.
- **Restarted at 01:28** (pid 99493, commit f93aa4e on the same branch; the rebuild-tone code was
  unchanged since the first start's 2350566, and the worktree's copies are byte-identical to
  f93aa4e. The other differences were multi-section files and one line of `learn/local_objective.py`
  adding `-m learn.multi_section run` to the render-cap patterns, which only affects how other
  jobs' renders are counted). The runner kept
  folds 0 and 1 of `stm` and `ctl_stm` (`already done`) and **trained fold 2 from scratch.**
- **The partial run is kept, unused:** `models-stm-s0-f2-killed1/` (no `result.json` or DONE marker)
  and `logs/train-stm-s0-f2-killed1.log`. It reached step 500. Its λ_st (0.4038) and its checks at
  steps 0, 250 and 500 (E_st 6.634, 6.352, 6.360; recon 35.54, 35.03, 35.50) are identical to the
  restarted run's, as the per-step batch stream intends.
- **Cost:** about 0.3 h of MPS and the 6-minute gap. Nothing else was redone; the rest of the
  run completed without failure.
