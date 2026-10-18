# The rebuild's short-time treble: a loss aimed at it, judged on rendered ranking. Plan (2026-10-17)

Declared 2026-10-17, before any training, gate measurement or render of this step. Development data
only: step 3's 24 parts, the frozen Σ `ee91f710947dbb5c`, the PR12 training cache. It follows the
[rebuild-gap study](rebuild-gap-results.md) and reuses its stage-T and stage-TR machinery
unchanged. Code: `learn/rebuild_tone_train.py` (torch: the loss, the fine-tunes, the gate's
measurements, the rebuilds), `learn/rebuild_tone.py` (main `.venv`: the curve, the EQ arms, the
renders and scores through `learn/rebuild_gap.py`, the report), `learn/rebuild_tone_run.zsh`
(the runner); tests `tests/test_rebuild_tone.py`, `tests/test_rebuild_tone_train.py`. Outputs
under `~/ndsp-presets/learn/rebuild-tone/`.

The user's rules apply:
- **No pass/fail bars.** Every result is an effect size with a 90% band-clustered interval (t,
  bands − 1 df), the leave-one-band-out range and the bands above and below 0. Any improvement is
  built on; undecided is not failed.
- **No fixed render limit.** Each render stage has a declared, evidence-based rule, an expected
  count, and reports what it used.

**Status:** reviewed 2026-10-17 by an independent agent: approved with 5 required changes, all made; re-reviewed: **approved**
(the sections below are revised; [amendment 1](#amendment-1-2026-10-17-review-before-any-training-gate-or-render)
lists them and governs where anything differs). Done before the review: the zero-render E_st
measurement of stored networks, the curve's build, and a fold-0 pilot to a scratch folder (below).

## Why

- **With a perfect stem, C′'s rebuild loses ranking through its short-time magnitude, mostly above
  2 kHz** (stage R): the true magnitude recovers the whole gap (+0.313), the true treble above 2 kHz
  about 0.8 of it (+0.241), the true phase nothing.
- **The costly error is structured,** at time scales between 21-ms frames and the long-term
  spectrum. A fixed long-term EQ (`dep_eq`) closes at most about half of it: +0.133 [−0.009,
  +0.276], and its curve included the DI recordings of 17 of the 24 parts.
- **The proxy-ranking fine-tune `rank` leans better** (+0.075 [−0.031, +0.182] against C′, +0.104
  [−0.005, +0.214] against its matched-step control) but looks like a learned long-term EQ: it lowered
  the long-term spectral distance and left the short-time treble error slightly higher (18 of 24
  parts). One seed per fold, selected on a noisy proxy.
- **Measured for this plan (zero renders):**
  - the declared metric E_st (below) on fold 0's 96 held-out validation crops: C′ 6.25 dB, `rank`
    6.45 (+0.19), `ctl` 6.32 (+0.07). So `rank` raises it in domain too, as it did on the real amp
    tracks (8.87 → 8.97 dB median). On the real amp tracks C′ sits about 2.6 dB higher than on PR12
    crops;
  - **the gate's stored networks** (run before launch; zero renders): on the 768 gate crops, stage
    T's `rank` − C′ on E_st is **+0.21 [+0.15, +0.27] dB** (LSD −0.48 dB), its `ctl` − C′ +0.04
    [−0.01, +0.08]. So in domain too `rank` traded short-time treble for long-term balance;
  - **a pilot of the new loss** (fold 0, the declared recipe, stopped after 500 steps, output to a scratch folder,
    not used by this step): λ_st 0.41; E_st on the 96 selection crops 6.25 → **6.00 dB at step 250
    and 5.95 at step 500** (−0.30), with C′'s reconstruction loss rising a little (38.25 → 38.32 →
    38.74); 0.66–0.76 steps/s with validation. (The pilot drew stage T's sequential stream, before
    amendment 1's per-step batches; it is not used.) So the term moves the error in domain; whether that carries to real amp tracks and
    to ranking is the question.

## The question

**Does a C′ fine-tune that lowers the short-time magnitude error above 2 kHz, with no credit for any
long-term EQ, raise rendered ranking?** Beside it: does it add to a long-term EQ built without the
test parts, and does `rank`'s lean survive a second seed?

## The loss (`stm`)

Each fold's final C′ fine-tuned on the PR12 pair cache with C′'s own loss (100·L1 + multi-resolution
STFT; it keeps carrying the long-term balance) plus one term:
- **Short-time log-magnitude, offset removed:** at 4 resolutions (Hann 256, 512, 1,024, 2,048; hop
  ¼: about 5–43 ms), the dB magnitude of the output against the target DI. Masked to the target's
  frames within 40 dB of its loudest and bins within 60 dB of each frame's loudest target bin.
  **Each bin's mean difference over the crop's masked frames is subtracted** before the smooth
  absolute value, so no fixed EQ can lower it (a crop is 3 s).
- **Weighted to 2–8 kHz:** weight 1 inside, raised-cosine edges falling to 0 over ⅓ octave outside
  (0 below about 1.59 kHz and above about 10 kHz).
- **Its weight λ_st** is fixed at step 0 by the share rule stage T used: on 50 calibration batches of
  C′ (seeds 2 and 3), the weighted term's mean is **half** C′'s loss (stage T's two terms were a
  quarter each, so the added weight is the same).
- Computed on the **CPU** (`torch.stft`'s backward is wrong on MPS above 65,536 samples); the
  network on MPS; stage T's hand clip and non-finite-step skip and recovery (`clip_grad_norm_`
  gives NaN on MPS).

**The metric E_st** (declared; the gate, the selection and the 24-part diagnostic): the mean |ΔdB| of
the STFT magnitudes (Hann 1,024, hop 256) over 2–8 kHz (hard edges), on the target's frames within
40 dB of its loudest and bins within 60 dB of each frame's loudest target bin, after removing each
bin's mean offset over those frames. It is the metric of the TR write-up, made declared.

## The arms

Per fold (the K3 folds, each part rebuilt by its own fold's network, as 1b):

| Arm | What | Training |
|---|---|---|
| **`stm`** | C′ + the loss above | seed 0 (stage T's seeds, drawn per step: see Seeds below), selected on E_st |
| **`ctl_stm`** | C′'s loss only, the same stream and schedule, **stopped at `stm`'s best step** | seed 0 |
| **`cprime_eq`** | C′'s stored 1b rebuild through the **leak-free `dep_eq`** (below) | none |
| **`stm_eq`** | `stm`'s rebuild through the same leak-free `dep_eq` | as `stm` |
| **`ctl_stm_eq`** | `ctl_stm`'s rebuild through it | as `ctl_stm` |
| **`rank_s1`** | stage T's `rank` recipe on a second seed (batches drawn per step) | seed 1, selected on the proxy as stage T |
| **`ctl_s1`** | its matched-step control | seed 1 |

- **The 2 × 2 is the point.** The EQ arms give every rebuild the same long-term balance, so
  `stm_eq` − `cprime_eq` reads the short-time change on top of a long-term fix, and `stm_eq` −
  `ctl_stm_eq` reads it net of both the long-term balance and more fine-tuning; `stm` − `ctl_stm`
  reads it against more fine-tuning.
- **`cprime_eq` − C′ is not a pure re-measure of stage R's `dep_eq`.** It changes the curve (free of
  the test parts) **and** the configuration together: R applied `dep_eq` to the rebuild shifted onto
  the truth's timeline and scored it as a probe (the measure DI's mask, `judge_lag`); here it runs on
  the rebuild's own timeline and is scored as 1b's arm (own mask, −52), as every arm here is. A
  smaller gain than R's can't be read as the leak alone.
- **`stm` + `rank` is not run here.** `rank` looked like a learned long-term EQ, which the EQ arms
  carry already; a combined arm follows only if `stm` leans positive.
- **Training recipe (stage T's, unchanged):** batch 12; 200-step warm-up to 1e-4, cosine to 2e-5 over
  4,000 steps; a check every 250 steps; the best checkpoint (E_st at least **0.02 dB** lower for
  `stm`; proxy fidelity at least 0.005 higher for `rank`); stop 1,500 steps after the best (at least
  1,500, at most 4,000). If the best is step 0, that fold's arm and its control are C′, reported so.
- **Seeds and the batch stream:** each training step's batch (its rows and its augmentation) and,
  for `rank`, its proxy draws come from generators seeded by (stream seed, step) alone, so an arm and
  its control see the same batch at every step, whatever either skipped (a skipped non-finite step
  still counts as a step, unapplied). Seed 0: data 0, proxy 1, torch 0; seed 1: data 100, proxy
  101, torch 1. (Stage T drew one sequential stream, so a skip shifted it; the order differs from
  stage T's, the recipe doesn't.) The weight calibration keeps seeds 2 and 3, so λ is the
  same; the validation crops and their proxy draws (`rebuild-gap|val|<fold>`) are stage T's.
- **Every check logs E_st and C′'s reconstruction loss;** `rank` and both controls also the proxy
  fidelity, as stage T did.

## Leaks and the test parts

- **Training pool** (stage T's): the PR12 cache's rows outside fold f and outside the fold's two
  validation bands; no Guitar-TECHS P3 row (asserted); 1b's leak assertion and the parent C′'s at
  rebuild time. The network that rebuilds a part never trained on or selected on its band.
- **Selection only on held-out training-fold bands** (stage T's 96 validation crops per fold: fold 0
  Eat The Feeder, Zeno; 1 Adam Buckley, Starnes And Shah; 2 Starnes And Shah, Swatkins; 3 Swatkins,
  Zeno), never on the 24 parts' amp tracks or renders.
  - As in stage T, those bands' cache rows include the DI recordings of 4 of the 24 parts from other
    folds (Signs, Today's The Day, Drag Me Down, Prodigal). They are never the recording of a part the
    selecting network rebuilds.
- **The leak-free curve** (`curve.npy`): built as `average-fold2.npy` (power average of the PR12
  cache's long-term DI spectra from bands outside K3 fold 2, mean removed) **without any row from a
  test part's own DI recording.** The recording is named from each part's crop record (the guitar DI
  it verified), matched by band, file name and a session folder naming the song (where none does,
  every same-named file of the band is dropped).
  - **Built (zero renders):** 4,734 rows of 19 recordings out (the audit's count), 10,585 kept. It
    sits **1.23 dB RMS (80 Hz–8 kHz) from `average-fold2.npy`, at most 3.2 dB.** The measure DI (the
    truth) stays normalised to `average-fold2.npy` (the yardstick isn't changed), so the leak-free
    `dep_eq` no longer shares the truth's own curve: part of `dep_eq`'s R gain may go.
  - `dep_eq` is stage R's: `to_lufs(eq_to(x, curve − (own − mean(own))))`, ±15 dB, zero-phase, on
    the rebuild's own timeline (no true DI anywhere). Checks: the same length, GCC within 3 samples
    of its source, −22.9 ± 0.05 LUFS.
- **No target spectrum is new.** Training targets are C′'s pipeline's (each row EQ'd to its fold's
  average, as C′ trained); the loss removes each bin's offset, so it uses no curve.

## Stage G: the zero-render gate (CPU, before any render of `stm`)

- **The gate crops:** per fold, 192 crops of the fold's held-out band rows **outside the 96
  selection crops** (`rebuild-tone|gate|<fold>`, centre 3-s crops), each scored by its fold's
  network. Same bands as selection, different rows: a held-out check of the selection, not a fresh
  band.
- **Per crop:** E_st, LSD (80 Hz–8 kHz), coherence 1–3 kHz and 3–8 kHz, against the target DI.
- **Contrasts** (crop-paired, band-clustered over the 5 validation bands, 4 df; recording-clustered
  beside it): `stm` − C′, `stm` − `ctl_stm`, `ctl_stm` − C′, stage T's `rank` − C′ and `ctl` − C′, and
  after the second seed `rank_s1` − C′, `ctl_s1` − C′, `rank_s1` − `ctl_s1`.
- **The declared rule (a direction rule):** `stm`'s four arms (`stm`, `ctl_stm`, `stm_eq`,
  `ctl_stm_eq`) render if `stm` − C′ on E_st is below 0 (band-weighted estimate; its interval is
  reported, not required: with 4 df and crops from the selection bands, the gate adds little beyond
  "the loss moved E_st at all"). Otherwise they are not rendered and the report says so;
  `cprime_eq` and the second seed render either way.
- **The 24 parts (descriptive, after the rebuilds, before nothing;** E_st's offset is removed over the
  whole 10-s part there, against a 3-s crop in training and the gate): E_st, LSD and coherence of every
  rebuild of the amp track against the measure DI (aligned as stage R), paired with C′ by band. It
  shows whether the in-domain change carries to real amp tracks (C′'s rotation and coherence there are
  a real-chain shift: stage T's phase check). It gates, stops and selects nothing.

## Stage J: rendered judgement (TR's design)

- **Rebuilds:** each trained arm rebuilds every part's `reference.wav` exactly as 1b
  (`local_objective.rebuild_from`: re-EQ'd by fold 2's average − fold f's, −22.9 LUFS, 2a's checks,
  the leak assertions). The EQ arms as above.
- **J1 (fixed): the 24 probe cells** (one amp per part, `rebuild-gap|cells`), all 48 of Σ's settings
  and a warm-up per cell: 1,176 renders per arm, plus the arm comparator (C′'s 1b rebuild at S,
  warm-up and S, against 1b's stored score; 48).
  - **Group 1** (after `stm` and its control): `stm`, `ctl_stm`, `stm_eq`, `ctl_stm_eq`,
    `cprime_eq`: **5,928** (or 1,224 if the gate keeps `stm`'s arms out).
  - **Group 2** (after the second seed): `rank_s1`, `ctl_s1`: **2,352**.
- **Scored as 1b's matched cell:** `reference.wav`, −52, own mask with the record fallback; paired
  cell by cell with 1b's stored C′ scores and stage TR's stored `rank`/`ctl` scores.
- **Guards** (stage TR's code, unchanged): `knob_ceiling.Renderer` with `isolate=True`; each cell's S
  against its warm-up within 0.005; FLAC against float at S; the comparator within 0.005; stop files
  (this step's and `local_objective`'s); the disk guard (31 GB, every remaining render counted at
  0.7 MB); the swap guard; at most 3 render processes machine-wide (`-m learn.rebuild_tone render` is
  added to `local_objective.RENDERS`, so other jobs count these); `OMP_NUM_THREADS=1`.

**Declared primaries** (band-weighted cross-half local Spearman, reliable-pair accuracy co-primary):

| Contrast | Asks |
|---|---|
| **`stm` − C′** | does the short-time loss help? |
| **`stm` − `ctl_stm`** | is it the loss, not more fine-tuning? |
| **`stm_eq` − `cprime_eq`** | does it add on top of a long-term fix? |
| **`rank_s1` − C′**, and **seed-pooled `rank` − C′** (the per-cell mean of `rank` and `rank_s1`) | does `rank`'s lean survive a second seed? |
| `rank_s1` − `ctl_s1`, seed-pooled `rank` − pooled `ctl` | is it `rank`'s loss, on two seeds? |

**Declared secondaries:** `cprime_eq` − C′ (leak-free `dep_eq`, with the configuration change
above), `stm_eq` − `ctl_stm_eq` (the fully controlled reading), `ctl_stm_eq` − `cprime_eq`, `stm_eq`
− C′ (the combined candidate), `ctl_stm` − C′, `ctl_s1` − C′, and descriptively `stm` − `rank`, `stm_eq` − `rank`,
`rank_s1` − `rank`.

**Every contrast reports:** the estimate with its 90% band-clustered interval, LOBO range, bands +/−,
part-weighted interval, per amp and class (crunch: 5 parts, descriptive), reliable-pair accuracy, the
share of C′'s gap (against C′, Fieller), truth − arm, and **the no-high-bleed row** (parts with a half
flagged high in the bleed table out: First Offering GTR_1, Gym Hours GTR_1, Long Way Home,
Sculptor's Request GTR_1, as the rule finds them) beside the all-parts row.

**Stopping, J1 → J2 (stage TR's rule, per group).** The narrowing ratio is the stored one
(`rebuild_gap.narrowing_ratio`, 0.948). A group renders on the other 48 cells (2 × 2,352 = **4,704**)
if one of its declared contrasts is positive, its J1 interval contains 0, and the interval narrowed
by the ratio would exclude 0. In this priority order (the disk guard may stop a later group):
- group `stm` (`stm`, `ctl_stm`): `stm` − C′ or `stm` − `ctl_stm`;
- group `eq` (`stm_eq`, `ctl_stm_eq`, `cprime_eq`; 7,056): `stm_eq` − `cprime_eq` or `cprime_eq` − C′
  (`dep_eq` missed this rule in R by 0.0015);
- group `seed` (`rank_s1`, `ctl_s1`): `rank_s1` − C′.

A group renders only its arms that rendered at J1. The first J2 group also renders the comparator on
the 48 new cells (96).

A decided contrast doesn't extend (more cells would not change the reading); nothing extends past
the 72 cells. J2's contrasts are reported on all 72 cells beside J1's. If the disk guard stops a
group (it counts 0.7 MB a render; renders have run about 0.4 MB), rendering stops resumably and the
user is asked what to delete; this plan deletes nothing.

## What would follow (estimates, not bars)

- **`stm` positive against C′ and `ctl_stm`, and E_st lower on the gate:** the short-time treble is a
  lever; build on it (`stm` + `rank`, more seeds, the product cell, the fresh full-mix test).
- **`stm_eq` − `cprime_eq` positive:** it adds to a long-term fix; `stm_eq` is the product candidate.
  Near 0 while `stm` − C′ is positive: `stm` gained mainly through its long-term balance after all.
- **E_st lower on the gate and on the 24 parts, but no rendered gain:** the short-time treble error
  that a network can learn to lower is not the one that costs ranking (R's oracle error is the full
  difference to the truth, including content the amp output may not carry); the next lever is
  elsewhere (a learned Morgan surrogate, or ranking-trained in the plugin's own terms).
- **E_st lower on the gate but not on the 24 parts:** a domain gap (PR12 renders against real amp
  chains); the next step is training data, not the loss.
- **E_st not lower on the gate:** `stm` isn't rendered; the loss as built can't move the error.
- **`cprime_eq` − C′:** whether `dep_eq` survives a curve free of the test parts (and off the truth's
  own curve), read with the change of scoring configuration from stage R.
- **`rank_s1`:** a second seed near the first (+0.075) strengthens `rank`; near 0 says the first was
  one draw.
- **Multiplicity:** 5 primaries, 7 secondaries, each with part-weighted, reliable-pair, per-amp/class
  and no-high-bleed rows, on the same 24 cells and Σ, after experiments 1–1d and stages R and TR.
  Read the families, not single intervals.

## The follow-on decision test (not this step)

Any rebuild change this step builds on is checked **where the product works: fresh parts outside the
24, on full mixes** (the [roadmap](ROADMAP.md)'s decision point: one fresh-song test of arm A with
the improved rebuild). That test needs its own plan. A note for it: stage F's fresh parts include
recordings that are in the PR12 training cache (She's Gone, Doom Flamingo's Strangest Places,
Russian Cream GTR 1), so a fresh draw should be checked against the cache's recordings.

## Machine order, hours and disk

| Stage | Renders | Hours | Lane |
|---|---|---|---|
| Curve and `cprime_eq` | 0 | minutes (curve done) | CPU, now |
| `stm` (4 folds) | 0 | 2.2–5.9 h MPS (0.76 steps/s measured) | GPU, now |
| `ctl_stm` (4 folds, to `stm`'s best steps) | 0 | 0–4.4 h MPS (expected about 1–2 h) | GPU |
| Gate 1, rebuilds | 0 | about 0.3 h CPU | CPU, after `ctl_stm` |
| J1 group 1 | 5,928 (or 1,224) | about 1 h at 3 processes + 0.2 h scoring | CPU, beside the GPU lane |
| `rank_s1`, `ctl_s1` (4 folds each) | 0 | about 3.3 + 0.7 h MPS (stage T's) | GPU |
| Gate 2, rebuilds, J1 group 2 | 2,352 | about 0.6 h + scoring | CPU |
| Diagnostic, report | 0 | minutes | CPU |
| J2 (by the rule) | 0–16,560 (expected 0–4,800) | 0–3.5 h | CPU |

- **MPS: about 7–14 h** (one training job at a time; the runner waits for any other `fit`/`train`).
- **Renders: 8,280 at J1** (3,576 if the gate keeps `stm` out), **at most about 24.8k** with every
  group extending; expected 8–13k.
- **Wall clock:** about 9–16 h from launch, most of it the GPU lane.
- **Disk:** 40 GB free at planning; checkpoints about 1.9 GB (16 folders × 3 files × 39 MB); J1
  about 3.6 GB at the measured 0.43 MB a render. That leaves about 34 GB, and the guard counts 0.7 MB
  a render: **about one J2 group fits** (the first in the priority order; `eq`'s 7,056 alone counts
  4.9 GB). A refused group stops resumably, and the user is asked what to delete; nothing is deleted
  by this plan.
- **CPU:** the GPU lane uses 2 threads for the spectral terms; renders 3 single-thread processes;
  the gate and rebuilds 2 threads on the CPU (`DIREC_DEVICE=cpu`), never MPS.

- **Queue:** the render command waits for the Mega-53 runner (`rebuild_gap.wait_mega`), which has
  ended; a new Mega-53 run started meanwhile would hold the renders without a log line.
- **The runner's gates** read only this run's lines of its appended log and match whole lines; a GPU
  lane that dies without its terminal line stops the CPU lane with a log line, so "all done" always
  appears.
- **`report.json` lists each fine-tune's kept step, steps run, skipped steps and recoveries;** a fold
  whose best is step 0 is C′ (and its control too).

## Seeds

- Cells: `random.Random("rebuild-gap|cells")` (stage R/TR's 24).
- Selection crops and proxy draws: `rebuild-gap|val|<fold>` (stage T's); gate crops
  `rebuild-tone|gate|<fold>`.
- Training: per step, generators seeded by (data seed, step) and (proxy seed, step); seed 0 = data 0,
  proxy 1, torch 0; seed 1 = data 100, proxy 101, torch 1; calibration 2 and 3.
- Nothing else is random.

## Ledger

The entry `rebuild-tone` in [dev-test-ledger.json](dev-test-ledger.json) is entered with this plan,
before any training, gate or render. It is a further unblinded development use of step 3's 24 parts
and Σ, after experiments 1–1d and the rebuild-gap study; every figure is a development reading.
Training and selection never touch the 24 parts; the curve leaves out their recordings. No
held-out data.

## Limits

- 24 parts (19 clean), one amp per part at J1; crunch descriptive.
- One seed for `stm`; two for `rank`.
- PR12 renders only for training; the gate's crops come from the selection bands.
- E_st is one choice of the short-time error (2–8 kHz, 21-ms frames, offset over a crop); the loss
  uses 4 resolutions and a 3-s crop's offset.
- The truth is the judge, not listening; the measure DI keeps `average-fold2.npy`'s normalisation.

## Amendment 1 (2026-10-17, review, before any training, gate or render)

The independent review approved the plan with 5 required changes, all made in the sections above, in
code and in tests:

1. **The arm comparator crashed under the binding.** `rebuild_gap.comparator` scores C′'s rebuild at
   S under the name `arm_rank`; with this step's arms bound, that name took the probe path. The
   binding now keeps `arm_rank` an arm (`rebuild_tone.bound`), with a test of that scoring call.
2. **The runner read stale lines** of its appended log. Its gates now read only this run's lines,
   match whole lines, and stop with a log line if the GPU lane dies without its terminal line.
3. **The gate was a pass/fail bar** (upper end below 0 on 4 df, nearly in-sample). It is now a
   direction rule: `stm`'s arms render if its E_st estimate is below C′'s; the interval is reported.
4. **Disk and renders:** checkpoints about 1.9 GB; about one J2 group fits above the guard, so the
   groups have a declared priority (`stm`, `eq`, `seed`); the first J2 group's 96 comparator renders
   counted.
5. **`cprime_eq` − C′** changes the curve and the scoring configuration together; said where it is
   read.

Also taken from the review's suggestions: `ctl_stm_eq` added (1,176 renders, no training) for the
fully controlled `stm_eq` − `ctl_stm_eq`; the curve compares DI file names by base name and refuses
to build if a test part with cache rows drops no file; `report.json` lists each fine-tune's kept
step, steps and skips; the `wait_mega` queue and the diagnostic's 10-s offset window are noted. From
the coordinator (a review of the parallel PR): a skipped step no longer shifts the data stream
between an arm and its control (the batch is drawn by step index), with a test.

**The re-review** (approve, no required changes) left four notes, all taken: the arms table no longer
calls seed 0 stage T's stream; `render` refuses an empty arm list; the runner reads from its last
start line (a reused PID can't pull in an older run); the pilot is marked as drawn on the old stream.
Measured before launch (zero renders): the gate's rows for C′ and stage T's `rank` and `ctl` (above).
