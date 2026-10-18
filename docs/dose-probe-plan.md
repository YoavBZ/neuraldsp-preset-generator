# The rebuild's short-time magnitude, by dose: an oracle probe on top of the leak-free EQ. Plan (2026-10-18)

Declared 2026-10-18, before any render of this step. Development data only: step 3's 24 parts, the
frozen Σ `ee91f710947dbb5c`, the rebuild-tone step's stored `cprime_eq` rebuilds and scores. It
follows the [rebuild-tone results](rebuild-tone-results.md) (their proposed next step 1) and reuses
the rebuild-gap study's stage-TR cells, guards, comparator and scoring (in a render loop that scores
as it renders, to keep the disk free; below). Code: `learn/rebuild_dose.py`
(the probes, their checks, the renders, the scores, the report; main `.venv`, no torch), the render
entry `-m learn.rebuild_tone render-dose`, the runner `learn/rebuild_dose_run.zsh`; tests
`tests/test_rebuild_dose.py`. Outputs under `~/ndsp-presets/learn/rebuild-dose/`.

The user's rules apply:
- **No pass/fail bars.** Every result is an effect size with a 90% band-clustered interval (t, bands
  − 1 df), the leave-one-band-out range and the bands above and below 0. The readings below are
  declared before the run; they interpret estimates, they gate nothing.
- **No fixed render limit.** The render stage has a declared, evidence-based extension rule and an
  expected count, and the write-up reports what it used.
- **Renders only, no training.** It is an oracle (it uses the true DI), so a diagnostic, never a
  product candidate.

**Status:** reviewed 2026-10-18 by an independent agent: approved with 5 required changes, all made;
re-reviewed: **approved** (the sections below are revised; [amendment 1](#amendment-1-2026-10-18-review-before-any-render) lists
them and governs where anything differs).

## Why

- **What is left after the long-term fix is real:** truth − `cprime_eq` +0.157 [+0.083, +0.230]
  (13/1 bands), about half of C′'s gap (+0.289 on these cells). Stage R places it in the magnitude
  (`mag` recovered the whole gap, `phase` nothing), but no probe isolated the **offset-removed
  short-time magnitude with the long-term balance held fixed**.
- **The trained loss moved too little to tell:** `stm` cut E_st by about 8% (7.57 → 6.99 dB on the
  amp tracks) and moved ranking by +0.012 [−0.023, +0.047]; on top of the EQ, −0.012 [−0.038,
  +0.014]. Stage R's probes that recovered most of the gap cut E_st by 39–98%, but also changed the
  long-term balance, and their gains are not ordered by the cut.
- **The next build depends on it:** option 2 of the [HF research](research/hf-detail-losses-2026-10.md),
  a bounded per-bin, per-frame log-gain on the STFT of C′'s own output, resynthesised with C′'s
  phase. Its ceiling is exactly a probe of this kind. Before building it we need (a) whether that
  ceiling carries the remainder, and (b) how large an E_st cut is needed before ranking moves, so
  its gate can require that cut rather than "any cut".

## The question

**On top of the leak-free EQ, does restoring the true short-time magnitude raise rendered ranking,
and how does the gain grow with the size of the restoration (the E_st cut)?**

## Measured for this plan (zero renders)

A prototype of the construction below, on all 24 parts (`cprime_eq`'s stored rebuilds against the
measure DI; medians over parts; E_st as `rebuild_tone_train.est`, aligned as the rebuild-tone
diagnostic):

| Probe | E_st (dB) | Realised cut (range) | LSD to the truth (dB) | LSD to `cprime_eq` | Peak over max(anchor, truth) |
|---|---|---|---|---|---|
| `cprime_eq` (dose 0) | 7.58 | — | 1.59 | 0 (identical to 2.7e-15) | 0 |
| `dose25` | 6.43 | 15% (13–16%) | 1.59 | 0.016 | ≤ +0.4 dB |
| `dose50` | 5.40 | 29% (24–31%) | 1.59 | 0.031 | ≤ +0.6 dB |
| `dose100` | 4.00 | 47% (39–51%) | 1.59 | 0.061 | ≤ +0.8 dB |
| `full100` | 3.61 | 52% (43–57%) | 1.58 | 0.108 | ≤ +4.1 dB |
| `full_gl` | 2.29 | 69% (49–73%) | 1.55 | 0.187 | ≤ +4.3 dB |
| `shift100` (control) | 9.14 | −20% (−42 to −11%) | 1.60 | 0.078 | ≤ +0.7 dB |

(The construction as amended: edge frames untouched, the doses' mask requiring both signals, the
hold on the interior frames; "peak" is the probe's peak against the larger of the anchor's and the
truth's at −22.9 LUFS.)

- **The long-term balance is held:** every probe's LSD to the truth is within 0.08 dB of
  `cprime_eq`'s on every part (within 0.02 for the doses), so the stage-R confound (probes that also
  fixed the long-term balance) is removed by construction. `cprime_eq`'s E_st reproduces the
  rebuild-tone diagnostic's stored value on every part exactly.
- **A single resynthesis with C′'s phase caps the cut at about half:** restoring 100% of the
  short-time gain field in 2–8 kHz realises a 47% cut, the full-band true magnitude 52%; 8
  Griffin–Lim iterations (as stage R's `mag`) reach 69%. The overlap-add of an inconsistent STFT
  smooths the gains. So **the ceiling of a direct oracle gain field is `full100`, not stage R's
  `mag`**, which the HF research took as option 2's ceiling; the plan renders both. (A trained head
  whose loss is taken after the inverse STFT could pre-compensate some of the smoothing; the review's
  quick test of 8 fixed-phase gain projections reached only 4.44 dB, so there is no sign of it.)
- **A ±12 dB bound costs little:** about 16% of the masked 2–8 kHz bins need more than ±12 dB
  (9–25% by part; 95th percentile of |gain| 14–21 dB), but bounding them moved the realised cut
  only from 47% to 43% in the first prototype. Reported again by the build, not rendered (the
  renders couldn't resolve 4 points of cut).
- **The review found boundary spikes in the first prototype** (a 59 dB gain in the last STFT frame
  of Gym Hours; `full_gl` peaking at 9.3 against the anchor's 0.66), which grew with dose. The
  construction below leaves the two edge frames at each end untouched, requires both signals in the
  doses' mask and holds the balance on the interior frames; with that, every dose peaks within 0.8
  dB of max(anchor, truth), and the full-band probes within 4.3 dB (their truths are peakier than
  C′: the truth peaks above the anchor on 12 of 24 parts).
- All probes: the same length as `cprime_eq`, GCC 0 samples against it, −22.9 LUFS.
- The prototypes are `scratchpad/proto3.py` (first) and `proto5.py` (as amended); the module
  re-implements them, and its build re-measures and logs every figure above.

## The probes

Everything on `cprime_eq`'s own timeline (the rebuild-tone step's stored `arm_cprime_eq/<part>.npy`,
the anchor), so every probe is scored exactly as its arms were, and the anchor's stored scores are
reused.

- **The truth on the rebuild's timeline:** t = the measure DI, shifted by the lag `rebuild_gap.align`
  finds between `cprime_eq` and t (the judge_lag-anchored analytic correlation in 80 Hz–2 kHz, ±100
  samples; the same alignment as the rebuild-tone diagnostic). Its rotation is not applied (it
  doesn't change STFT magnitudes). The alignment checks of stage R are logged (|c|, coherence 80
  Hz–2 kHz).
- **STFT:** Hann 1,024, hop 256 (`rebuild_gap.stft`/`istft`; E_st's resolution). X = `cprime_eq`'s,
  T = the aligned truth's; A, B their dB magnitudes.
- **Edge frames:** the two STFT frames at each end (whose windows run past the signal, with
  `boundary="zeros"`) are left as X in every probe.
- **The short-time gain field (E_st's definition, both signals present):** the mask M = E_st's mask
  of T (`st_mask_np`: frames within 40 dB of T's loudest, bins within 60 dB of each frame's loudest
  T bin) **and** the same mask of X, on the interior frames; per bin, the offset o = the mean of
  B − A over its masked frames (over the whole 10-s part, as the diagnostic's E_st); g = (B − A − o)
  inside M, 0 outside, times the 2–8 kHz weight with ⅓-octave raised-cosine edges (`st_weights`, as
  the `stm` loss: 0 below about 1.59 kHz and above about 10 kHz). No bound (the ±12 dB question is
  answered at zero renders).
- **Holding the long-term balance (every probe):** after the modification, (1) each STFT bin's
  power summed over the interior frames is scaled back to X's there (edge frames stay X), the STFT
  is resynthesised once (`istft`), then (2) twice, `eq_to(y, S(x) − S(y))` (S the smoothed
  long-term spectrum that `dep_eq` and LSD use; zero-phase, ±15 dB), and (3) levelled to −22.9
  LUFS. At dose 0 this returns `cprime_eq` exactly.

| Probe | The DI | Asks |
|---|---|---|
| **`dose25`, `dose50`, `dose100`** | X · 10^(α·g/20), α = 0.25, 0.5, 1; C′'s phase; one resynthesis | **the dose response in E_st's band and mask**; `dose100` is option 2's ceiling restricted to 2–8 kHz |
| **`full100`** | \|T\| with X's phase, all bins and interior frames (the offset is absorbed by the hold); one resynthesis | **option 2's full-band ceiling as a direct oracle gain field** (per bin and frame, resynthesised with C′'s phase) |
| **`full_gl`** | \|T\| from X's phase with 8 Griffin–Lim iterations (stage R's `mag` construction; edge frames then X again), then the hold | **the short-time magnitude ceiling**: stage R's `mag` with the long-term balance held at `cprime_eq`'s |
| **`shift100`** (control) | X · 10^(g′/20), g′ = `dose100`'s field circularly shifted by half the part's frames (5 s) | **the right content or any modulation?** The same gains, at the wrong times |

- **No `onset`-type control is rendered.** Its purpose in the proposal was to tell dose from
  long-term balance. Here the balance is held by construction and checked per part (above and in
  the build checks), so it would add nothing; `shift100` controls the other confound (that any
  added short-time modulation of this size, or the processing itself, moves ranking).
- **Why 2–8 kHz for the doses:** E_st, the `stm` loss and option 2's planned gate all use it, and
  stage R's `high` (the truth above 2 kHz) recovered 0.81 of the gap. `full100` against `dose100`
  tests the edge and the mask together; `full_gl` against `full100` tests the resynthesis.

**Build checks (zero renders, before any render; a failure stops the render stage,
`arms/check.json`):** the same length as `cprime_eq`, finite; GCC within 3 samples of it; −22.9 ±
0.05 LUFS; LSD to the truth within 0.25 dB of `cprime_eq`'s and LSD to `cprime_eq` at most 1.0 dB
(the hold worked); **peak at most 6 dB above the larger of the anchor's and the truth's** (at
−22.9 LUFS; the anchor itself peaks at 1.13 on one part, so an absolute bound would stop at dose
0); the alignment |c| ≥ 0.3 and 80 Hz–2 kHz coherence ≥ 0.3 (stage R's); dose 0 equal to
`cprime_eq` within 1e-9; `cprime_eq`'s E_st equal to the rebuild-tone diagnostic's stored value
within 1e-6 (the same metric and alignment). The realised E_st, cut, LSD, coherence (1–3 and 3–8
kHz), peak and crest factor and the gain field's statistics (|g| > 12 dB and > 30 dB shares, 95th
percentile, maximum, the ±12 dB-bounded `dose100`'s E_st) are logged per part (`arms/build.json`).
- **No probe audio is stored.** The build records each probe's SHA-256 (float64 bytes); a render
  process rebuilds the probe for its cell (about 1–2 s) and refuses to render if the hash differs
  (the same code, `OMP_NUM_THREADS=1` everywhere). The probe is cast to float32 for the renderer, as
  the anchor's float64 rebuild was (the anchor comparator covers that path).

## Rendering (TR's design; scored as it renders)

- **Cells:** stage R/TR's 24 (`rebuild-gap|cells`, one amp per part, all 14 bands), all 48 of Σ's
  settings and a warm-up per (cell, probe): **1,176 renders per probe**.
- **The comparators, per cell before its first probe render (96 renders):** C′'s 1b rebuild at S
  (warm-up and S) against 1b's stored score (stage TR's arm comparator, `rebuild_gap.comparator`),
  and **the anchor at S** (`cprime_eq`, warm-up and S) against the rebuild-tone step's stored
  `cprime_eq` score at S, both within 0.005 (log) on both halves.
- **Scored as 1b's matched cell** (`reference.wav`, −52, own mask with the record fallback;
  `rebuild_gap.score_one` for an arm), paired cell by cell with the stored scores of `cprime_eq`, C′
  (1b) and the truth.
- **Scored at render time, from the float render.** Stage TR wrote every render as a 16-bit FLAC
  (about 0.48 MB) and scored the FLACs later; here each render is scored in the render process and
  only its scores are kept, so the step stores about 0.1 GB instead of about 3.5 GB (below). The S
  render of each (cell, probe) is still written as FLAC and rescored, so the FLAC-against-float check
  at S stays (stage TR's largest was 3.2e-5, against the 0.005 tolerance); the anchor's stored scores
  came from FLACs, a difference of that size.
- **Beside it, a fixed-mask diagnostic (zero renders, scored in the same pass):** each render also
  scored with `cprime_eq` as the activity mask (the anchor's own mask, with the same fallback), so a
  gain that comes only through the probe moving the judge's activity mask can be told apart. For
  `cprime_eq` it is its declared score.
- **Guards** (stage TR's): `knob_ceiling.Renderer` with `isolate=True` (asserted at start); arm B's
  stored S against the live menu's; each cell's S against its warm-up within 0.005; FLAC against
  float at S; the comparators; the probe's hash; stop files (this step's and `local_objective`'s;
  a breakage writes this step's and stops every shard); the swap guard; the disk guard (31 GB,
  checked per (cell, probe)); `OMP_NUM_THREADS=1`.
- **Order:** probe by probe, all 24 cells each, so a stop leaves whole probes: `dose100`,
  `shift100` (the control can void readings 1–4, so it comes second), `full_gl`, `full100`,
  `dose50`, `dose25`.

### Sharing the machine (at most 3 render processes)

- **The render command is `-m learn.rebuild_tone render-dose`.** The pattern
  `-m learn\.rebuild_tone render\b` is already in `local_objective.RENDERS` in every current
  checkout, including the one the self-render runner (the known-answer search, then part C) runs
  from, so those jobs count these processes. An explicit line for it is added to
  `local_objective.RENDERS` too, with a test that both the old and the new pattern match it.
- **No waiting while alive.** The existing per-cell `wait_cap` counts waiting processes as
  rendering, and part C's shards wait (`_wait_cap`) at start and at each amp change. With this
  step's shards waiting too, all six would wait on each other (a deadlock; the review confirmed it).
  So a render-dose process **never waits**: before each (cell, probe) it counts the other render
  processes (`local_objective.RENDERS` and the rebuild-gap patterns) and any separation, and if
  there are 3 or more other render processes, or a separation, it exits with code 75 after logging
  `YIELD` (the cell it was on is resumed later). Its own sibling lanes count only if their PID is
  lower, so lanes that launch together don't all yield to each other (re-review note).
- **The runner counts before launching:** each of three lanes asks `-m learn.rebuild_dose slots` (a
  command no render pattern matches) and launches its render process only when fewer than 3 render
  processes run and no separation does; otherwise it waits 90–120 s and asks again. So a retrying
  lane is never counted by another job while it is only checking. A lane ends on its shard's
  `RENDER DONE <probe> i/3` lines; any other exit stops it and is logged.
  - The count can still race (two jobs reading 2 at once); the window is one `ps` call, as for every
    job on the machine.
- **When it renders:** the known-answer search holds 3 slots until about 13:00. Part C then renders
  about 43k in one stretch (about 6.5–7 h), then fits its curve on the GPU (3–5 h, no renders), then
  decides (it may render more). This step renders in whatever slots are free: most likely during
  part C's curve fit, or after it. When another job's shards start they see this step's processes,
  which yield within one cell (about 2 min).
- **Memory:** the runner logs memory pressure with every lane start (part C's GPU guard wants 25%
  free).

## Measures and contrasts

The measure is stage TR's: the cross-half local Spearman per cell (each probe's objective on one half
against the true d on the other, averaged over halves), with reliable-pair accuracy as co-primary;
cells → parts → bands; band-weighted mean with the 90% band-clustered t interval (13 df), LOBO
range, bands +/−, the part-weighted interval, per amp and class (crunch: 5 parts, descriptive), and
the no-high-bleed row (First Offering GTR_1, Gym Hours GTR_1, Long Way Home, Sculptor's Request
GTR_1 out, as the rule finds them). "The remainder" is truth − `cprime_eq` on the same cells
(+0.157 on R1).

**Declared primaries** (each against the anchor, with its share of the remainder: (probe −
`cprime_eq`) / (truth − `cprime_eq`), band-weighted, Fieller's interval):

| Contrast | Asks |
|---|---|
| **`full_gl` − `cprime_eq`** | is the remainder a short-time magnitude problem at all? |
| **`full100` − `cprime_eq`** | can option 2's mechanism (one resynthesis, C′'s phase) carry it? |
| **`dose100` − `cprime_eq`** | can it, in E_st's band and mask? |
| **`dose50` − `cprime_eq`, `dose25` − `cprime_eq`** | how does the gain grow with the cut? |

**The dose shape:** `dose25`'s and `dose50`'s shares **of `dose100`'s gain** (Fieller), beside the
realised cuts (about 15%, 29%, 47%).

**Declared secondaries:** `dose100` − `full100` (band and mask), `full_gl` − `full100` (one
resynthesis against a consistent one), `dose100` − `dose50`, `dose50` − `dose25`, `shift100` −
`cprime_eq`, `dose100` − `shift100`; every probe − C′ and truth − probe; the fixed-mask diagnostic
of each primary; per-part gain against the realised cut (descriptive, Spearman).

## Readings (declared now, before any render)

Read on the band-weighted estimates and their intervals; where an interval spans two readings, both
are stated and the contrast is **undecided** between them. Two terms, declared:
- **near 0** (for a contrast against the anchor, or a difference of two probes): its interval
  contains 0 and its end on the side in question lies within a quarter of the remainder (±0.04 on
  R1). The side in question is the upper end everywhere except reading 3 (`dose100` − `full100`,
  the lower end). **Below / above:** the interval excludes 0 on that side. Otherwise undecided.
- **most of the remainder:** the share's point estimate at 0.5 or more, its Fieller interval stated.

1. **Is the remainder short-time magnitude?** (`full_gl` − `cprime_eq`)
   - **Most of the remainder:** yes; stage R's `mag` result holds with the long-term balance fixed.
     Go to 2.
   - **Near 0:** no; stage R's `mag` gain was mostly its long-term part. This closes option 2 and
     a stronger `stm` as routes to the remainder (not the rebuild as a research target); the
     declared alternatives come next (a learned Morgan surrogate, or ranking trained in the
     plugin's own terms).
   - **Positive but under half:** part of it; options are read from 2–4 against how much is left.
   - **Below 0:** restoring the true short-time magnitude with C′'s phase costs ranking; the
     magnitude can't be fixed apart from the phase (the probes' mixed phase is the suspect), stated
     with `full100` and the doses.
2. **Can option 2's mechanism carry it?** (`full100` − `cprime_eq`, and `full_gl` − `full100`)
   - **`full_gl` − `full100` near 0:** one resynthesis with C′'s phase is enough; option 2's ceiling
     is what `full100` shows. Go to 3.
   - **`full_gl` − `full100` above 0:** the consistency matters (52% against 69% of cut); option 2
     would need a consistent resynthesis (Griffin–Lim steps inside the head) or a phase output.
   - **`full_gl` − `full100` below 0:** the Griffin–Lim phase costs what its deeper cut gains; read
     `full100` as the better ceiling.
   - **`full100` − `cprime_eq` below 0:** the direct gain field hurts (artefacts of the
     inconsistent resynthesis); option 2 as specified is not supported.
3. **Is E_st's region the one that matters?** (`dose100` − `full100`)
   - **Near 0:** 2–8 kHz on E_st's mask carries the full-band field's gain; E_st is the right gate
     metric.
   - **Below 0:** content outside the doses' region (below about 1.6 kHz, or the frames and bins
     outside E_st's mask restricted to where C′ is present) matters; the gate metric must widen
     before option 2 is built.
   - **Above 0:** the full-band field costs something the treble field doesn't (the low band or the
     quiet frames); option 2 should be restricted to E_st's region.
4. **The dose shape** (read only if `dose100` − `cprime_eq` is above 0; otherwise reported, not
   read). S25 and S50 are the doses' shares of `dose100`'s gain (Fieller); r25 and r50 the ratios of
   their realised median cuts to `dose100`'s, from the build (about 0.32 and 0.62):
   - **Proportional to the cut:** S50 within r50 ± 0.15. Every unit of cut pays; `stm`'s 8% cut
     predicts about a sixth of `dose100`'s gain, which its result can't exclude.
   - **Concave:** S50 above r50 + 0.15. A modest cut pays most. `stm`'s null then says its cut was
     not in the oracle's direction, not that it was too small; a stronger weight of the same loss
     would not help, and option 2 needs a loss aimed at the oracle's field.
   - **Convex:** S50 below r50 − 0.15. Only near-full restoration pays; option 2 has to reach most
     of its ceiling.
   - S25 is read the same way against r25, beside it; where S25 and S50 disagree, the shape is
     undecided.
   - **The cut that matters (the gate for option 2):** the smallest realised median cut among the
     doses whose gain is at least half of `dose100`'s (point estimate), stated with S25's and S50's
     intervals. If `dose100` isn't above 0, no cut is named.
   - **Non-monotone** (`dose50` above `dose100`): read as noise unless `dose100` − `dose50` is below
     0; then the full field overshoots (likely C′'s phase under the larger gains), stated.
5. **The control** (`shift100` − `cprime_eq`, and `dose100` − `shift100`):
   - `shift100` near 0 or below while `dose100` − `shift100` is above 0: the gain is the true
     content's timing;
   - `dose100` − `shift100` near 0 while `shift100` is above 0: the gain is generic (modulation or
     processing), and readings 1–4 are void for option 2;
   - otherwise (the control in between): undecided, and readings 1–4 carry that caveat.
6. **The fixed-mask diagnostic:** if a primary's gain mostly vanishes (under half) with
   `cprime_eq`'s mask, the gain came through the judge's activity mask (the probe changing which
   frames count), not through the amp's response; stated beside the reading.

**Multiplicity:** 5 primaries, 6 secondaries and their rows, on the same 24 cells and Σ, after
experiments 1–1d, stages R and TR and the rebuild-tone step. Read the family (the dose series and
the ceilings together), not single intervals.

## Stopping: R1 → R2 (stage TR's rule)

The narrowing ratio is the stored one (`rebuild_gap.narrowing_ratio`, 0.948). A probe renders on the
other 48 cells if its contrast against `cprime_eq` is positive, its R1 interval contains 0, and the
interval narrowed by the ratio would exclude 0; in the priority order `dose100`, `full100`,
`full_gl`, `dose50`, `dose25` (the control extends with `dose100` if `dose100` extends). The first
extension also renders the anchor `cprime_eq` on those cells (it was never rendered there) and the
comparators: 2,352 + 2,352 + 192 for one probe. A decided contrast doesn't extend; nothing extends
past the 72 cells. Scored as it renders, R2 stores about 0.1 GB, so the disk is not expected to
limit it; the disk guard still applies per (cell, probe).

## Machine order, hours and disk

| Stage | Renders | Hours | When |
|---|---|---|---|
| Build and checks | 0 | about 5 min CPU | at launch |
| R1 (6 probes + comparators) | 7,152 | about 2 h at 3 processes (scoring in the render processes) | in free render slots (above) |
| Report | 0 | minutes | after R1 |
| R2 (by the rule) | 0–16,656 (expected 0–4,896) | 0–5 h | after the report, in free slots |

- **Renders: 7,152 at R1** (6 × 1,176 + 96); at most 16,656 more at R2 (every probe, the control
  and the anchor on the other 48 cells, with the comparators); expected 7,152 to about 12k.
- **Disk:** 38.4 GB free at planning; part C needs about 3.3 GB. This step stores about 0.1 GB at R1
  (144 S FLACs, about 70 MB, and the score files) and no probe audio. Part C's own disk rules (its
  shards stop under 31 GB, its curve waits for 31 GiB free, about 33.3 GB, and its extension wants
  34 GB) are the binding ones on this machine, and this step's footprint leaves them as they were.
- **The runner** (`learn/rebuild_dose_run.zsh`, `nohup`, `setopt no_bg_nice`, `caffeinate -i`)
  logs every step; its gates match whole lines of this run's log only (from its last start line);
  the lanes yield and retry as above; it ends with `all done (…; renders N)` whatever happens. The
  PIDs it starts are recorded in its log.

## Seeds

- Cells: `random.Random("rebuild-gap|cells")` (stage R/TR's 24).
- Nothing else is random (Griffin–Lim starts from C′'s phase; the shift is fixed at half the frames).

## Ledger

The entry `dose-probe` in [dev-test-ledger.json](dev-test-ledger.json) is entered with this plan,
before any render. It is a further unblinded development use of step 3's 24 parts and Σ, after
experiments 1–1d, the rebuild-gap study and the rebuild-tone step; every figure is a development
reading. It uses the true DI by design (an oracle) and trains nothing. No held-out data.

## Limits

- 24 parts (19 clean), one amp per part; crunch descriptive.
- One construction of each probe: Hann 1,024 resolution, E_st's mask restricted to where C′ is
  present (the doses), C′'s phase; other
  resolutions or a learned field might do better or worse than these oracles.
- The realised cuts differ by part (39–53% for `dose100`); the dose series is three points.
- The measure DI keeps `average-fold2.npy`'s normalisation; the truth is the judge, not listening.
- An oracle bounds what a rebuild could gain from this component; it doesn't show a network can
  learn it.

## Amendment 1 (2026-10-18, review, before any render)

The independent review approved the design (it checked every figure in the zero-render table, the
alignment's sign, the counts and the deadlock argument) with 5 required changes, all made above:

1. **Disk.** R1's FLACs would have taken about 3.5 GB (0.48 MB a render, not 0.43), which would
   have pushed part C under its own disk rules (its curve waits for 31 GiB, its extension wants 34
   GB). Now each render is scored as it renders, both masks; only the S render's FLAC is kept per
   (cell, probe), and no probe audio is stored (rebuilt per cell, hash-checked). The step stores
   about 0.1 GB. Part C's schedule is corrected (one 6.5–7 h stretch, then a 3–5 h GPU curve).
2. **Build checks and artefacts.** An absolute peak bound would have stopped at the anchor (1.13
   on one part), and the first prototype had boundary spikes that grew with dose (a 59 dB gain in
   Gym Hours' last frame). Now the edge frames are untouched, the doses' mask needs both signals,
   the hold runs on the interior frames, and the peak check is relative (within 6 dB of the larger
   of the anchor's and the truth's peak), with the crest factor logged. The table is re-measured.
3. **The dose shape** is read against the realised cut ratios (r25, r50 about 0.32 and 0.62), not
   against α.
4. **The readings** define near, below/above and undecided by the intervals, say "most" is read on
   the point estimate, and cover the missing outcomes (a probe below the anchor, `full100` above
   `full_gl`, `dose100` above `full100`, the control in between).
5. **The control renders second,** right after `dose100`.

**The re-review** (approve, no required changes) left three notes, all taken: sibling lanes yield
only to lower PIDs; the doses' mask is described as E_st's restricted to where C′ is present; the
per-part peak margins are in `arms/build.json`. The build runs with `OMP_NUM_THREADS=1`, as the
render processes do, so the hashes match.

Also taken from the review's suggestions: the runner counts slots with a command no render pattern
matches before launching a render process; `full100` is called the ceiling of a direct oracle gain
field (a trained head might pre-compensate some smoothing); reading 1's "near 0" closes option 2
and a stronger `stm`, not the rebuild as a target; the float32 cast is noted; memory pressure is
logged.
