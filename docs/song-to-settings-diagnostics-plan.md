# Arm B diagnostics: does the model's posterior hold good answers? (experiment 1): plan

Declared 2026-10-16, before any experiment-1 compute. Experiment 1 of
[`research/song-to-settings-rethink-2026-10.md`](research/song-to-settings-rethink-2026-10.md)
(the rethink), which sets its design. This file makes it concrete: the targets, the seeds, the
readings, the code and the order. Development data only. No training.

**Review:** reviewed 2026-10-16 by an independent agent
(`tmp/song-to-settings-diagnostics-plan-review.md`, local): approved with changes, all folded in
(10 required, and every recommended item).

**Status: waiting for the user's yes.** Step 3's readout ended in step 6, row 4 ("no arm passes"),
and row 4's next step is not this one. So this plan starts only when the user says so. Everything
below is prepared so that it can start on that yes.

## The question

Arm B failed its positive control, and failed harder once the planted targets were reachable
(1 of 33 units; [results](song-settings-results.md)). Why? Four answers lead to different next
steps:
- **the model's samples hold good answers, but its single answer averages them** (a picker is
  missing);
- **the song path hides the cues** (backing, mastering, separation);
- **many settings sound alike,** so averaging explains the failure;
- **few settings sound alike,** so the model is simply weak.

Experiment 1 tells these apart on the four existing fold models, with fresh reachable targets.

**Against "1 of 33":** the old control drew every target from Guitar-TECHS P1/P2 windows, whose
players and takes every fold model had heard. These targets are unheard, so they are harder.

## Shared

- **Models:** arm B's four full-bank fold models, `song-settings/models/fold{f}/model.pt`, as
  scored at step 3. Not retrained, not changed. Their files are hashed into the output first.
- **Renders:** `knob_ceiling.Renderer` (`isolate=True`) through each target's **measure DI**:
  `song_bank.measure(load_window(w))`, measured on the untrimmed 10.25-s window exactly as
  `song_bank.render` does (average-guitar balance, −22.9 LUFS), never re-measured on the trimmed
  10 s. This fixes the readout audit's finding: the old control rendered its targets through the
  raw DI.
- **One timeline:** the DI, the target and every candidate render are cut by the same 12,000
  samples, to [0.25 s, 10.25 s) (the `isolate` fade-in trimmed). The features and the judge's
  reference use that same cut. The model's halves and the judge's halves are then the same
  samples, and the render latency is kept, so lag 0 is right. (The old control's features used
  the trimmed clip and its judge the untrimmed one: a 0.25-s offset, fixed here.)
- **The judge:** `knob_ceiling.judge` at lag 0 against the target render, both halves (`flat`).
- **Units:** a (target, direction) pair. Direction = (search half, held half), A→B or B→A. The
  model reads the search half's features; a best-of-K pick uses the search half; every score is
  on the held half.
- **Informative unit:** d_S, d_T and the target are finite on the held half, and
  d_S − d_T ≥ 0.1 there (d_T is the target's repeat render, about 0). The audit's re-renders had
  d_S of 0.97–7.7, so nearly every unit should qualify. Units dropped for a non-finite value (a
  silent half: windows need only 60% activity) are counted and listed, as
  `song_readout.positive_control` does.
- **Refused candidates:** a candidate whose held half is non-finite counts as not closing the gap
  in every count and is left out of every mean; refusals are reported per candidate type. A
  best-of-K pick never chooses a candidate with a non-finite search half; if all K are non-finite,
  the pick counts as not closing and is left out of the means.
- **Gap closed:** (d_S − d_cand) / (d_S − d_T). **Log ratio:** log(d_cand / d_ref).
- **Knob distance:** the mean, over the amp's continuous settings in `space(amp, S)`, of |Δ| on the
  0–1 scale. Settings that step 1.2 finds flat are dropped. Mics and switches are reported apart
  (share matching), never in the distance. It reads the landscape only; the model is never graded
  on it.

## Step 1.0: read the models and the stored searches (0 renders, CPU)

**The models, on held-out bank features.** The fold-f model reads fold f's bank examples (it
never trained on them), both halves. The figures below are on **fold-own-window examples only**.
About half of fold f's examples use P1/P2 windows, whose audio the fold-f model heard; those are
reported apart, descriptively. Reported per fold and per setting, by name:
- **collapse:** the mode separation (below), exp(H(π)), the top weight, the top mean against the
  mixture mean, and the top component's σ against the label spread;
- **calibration:** PIT histograms per continuous setting (10 bins, χ² against uniform), TARP on
  the amp's continuous vector (200 samples per example), reliability for switches and mics (ECE);
- **point error:** knob MAE against the fold's median label, Pearson and Spearman per setting,
  mic accuracy, prediction spread over label spread. Also restricted to step 1.2's audible
  settings.

This commits the per-setting figures the audit left outside git. None of it is a gate.
- **Mode separation:** per example and audible continuous setting, Σ_k π_k |μ_k − μ̄| divided by
  Σ_k π_k σ_k (μ̄ the mixture mean), then averaged over the settings. Below 0.5, the components
  sit within half a σ of each other: one mode, however π is spread.
- **Collapse flag:** median mode separation < 0.5 in at least 3 of 4 folds. It chooses experiment
  3B's first step (below). exp(H(π)) is reported only: the audit's median top weight of 0.69
  means exp(H) ≤ 1.2 could not fire, while the top mean sat within 0.05 of the mixture mean.
  **This threshold was set after the audit's diagnostics were readable.**
- **Label-sampling flag:** step 1.1's split by target type (below).

**The K_S replay.** Each of step 3's stored K_S runs (`knob-ceiling/cells/*/*/result.json`,
`runs[search]["K_S"]["evals"]`) is replayed: `knob_search` with K_S's dims, start, budget 150
and seed 20261013, where `f` returns the stored search-half values in order and records each
setting.
- **It counts only if every replayed run ends on its stored best** (`K_S-{search}.json`) after
  exactly the stored number of renders. If today's code does not reproduce a run, the replay is
  tried once at the commit that produced it. If that fails too, it is reported as not reproduced
  and nothing uses it.
- **If it counts:** per run, the settings within 0.03 and 0.1 (log ratio) of the run's best
  held-half distance. Reported: how many, their knob spread, the share ≥ 0.2 from the held best,
  and mic agreement. On real records, with the true DI, at zero renders. Descriptive only: a
  search path is not a uniform sample.

**Threads:** step 1.0, separation and every torch step use `torch.set_num_threads(2)`, because
experiment 4 computes its spectral losses on the CPU.

## Step 1.1: fresh targets, two views, many candidates (about 7.1k renders)

**The targets: 120, 30 per fold.**
- **DI windows:** from `bank/windows.json`, fold-own development bands only (the band's fold, by
  `docs/song-settings-folds.json`). The fold-f model trains on `fold != f` rows only, so it has
  never heard any of them.
- **Excluded:**
  - the DI tracks and backings of knob ceiling's 25 parts. That covers step 3's evaluation parts
    and the 12 known-target cells;
  - every band that experiment 4's step 5 may draw from (Adam Buckley, Atlantis Bound, Dom
    McLennon, Eggy, Magician's Nephew, Turbosauro, Wall Of Death, Zeno). Its draw is not made
    yet, and its part pool is not pinned in writing, so whole bands are left out. If it draws
    from knob ceiling's parts, as `song_settings.control_cells` does, the part exclusion above
    already suffices; the band exclusion costs only extra bands in folds 0–2;
  - Guitar-TECHS P1 and P2. Every fold model trained on P1/P2 windows that share about half their
    audio with any "unused" start (amendment 4's limit).
- **What is left, counted on 2026-10-16 (windows / DI tracks):**

  | Fold | Bands |
  |---|---|
  | 0 | Rebuild The Evil 58/2, Swatkins 89/2, Szymon Skiba 47/2, The Travelling Band 49/4 |
  | 1 | Ale Lak 5/1, Diesel13 14/2, Doom Flamingo 102/2, Renesans 77/2 |
  | 2 | Death Of A Romantic 103/4, Eat The Feeder 187/7, Hollow Ground 78/3, John Morgan Kimock 40/1 |
  | 3 | Bernard Purdie Tribute All-Stars 63/1, Starnes And Shah 52/3 |

  14 bands. **Fold 3 has 2 bands whatever is decided about step 5:** its other bands, Eggy and
  Timo And The Timezone, have no DI track outside knob ceiling's parts. The band exclusion does
  not cause this.
- **The draw:** `random.Random(20261020)`. Per fold, bands are taken in turn (a seeded order),
  and a window is drawn without replacement within the band. A window that overlaps an already
  drawn window on the same track by any amount is skipped (windows are 10.25 s on a 5-s hop, so
  starts must be ≥ 10.25 s apart); Ale Lak gives at most 3. A band that runs out passes its turn.
- **Top-up:** if a fold ends with fewer than 40 informative units, the same seeded draw continues
  for that fold until it has 40 (d_S reveals nothing about the model). Top-up renders count in the
  budget and are listed.
- **Settings:** an amp and a class start (S) uniform per target. Alternating within each fold:
  - **broad (15):** uniform on the 0–1 scale; uniform switches and mics, as the bank's broad half;
  - **K_S-prior (15):** σ 0.1 around a K_S optimum of the same amp and class from **another fold**
    (`song_bank.ks_optima`), mics and switches kept with p 0.7, as the bank's jittered half.
- **Backing:** a same-fold backing from the eligible bands (not knob ceiling's crops), **never from
  the target DI's own song** (its backing could hold that take's real amp track). Guitar-to-backing
  level and mix loudness are drawn as in `song_aug.mixture`. No second guitar.
- **Asserted in code:** each target's band maps to its fold; its DI track and backing appear in
  no bank example the fold-f model trained on; no excluded track, band or crop is used; no backing
  comes from the target's own song.

**Two views of the same target** (the same guitar, backing and levels):
- **1a, light:** the guitar at its level in the mix, plus the backing. No mastering, no separation.
- **1b, song-like:** the mix mastered as the bank's mastered branch (bus compression, −1 dBFS
  limiter, AAC with p 0.5), and the stem from htdemucs_6s on that mix (`GuitarSeparator`, CPU).

Features: `song_aug.features(stem, mix)`, per half, computed from the target render's 16-bit
peak-normalised copy, the bank's own path (`song_aug.load_render`). Parity with the bank's
feature code is tested on 3 targets.

**Candidates per target, all through its measure DI:**

| Candidate | Renders |
|---|---|
| The target, and its repeat render (d_T) | 2 |
| S | 1 |
| View 1a, per direction: the top-component mean + 4 MDN samples | 10 |
| View 1b, per direction: the top mean + 8 MDN samples + the mixture mean | 20 |
| The fold's bank median (`song_armb.bank_median`) and the song-blind constant (`constant_settings`) | 2 |
| 8 random bank labels: stored settings of fold ≠ f bank examples with the same amp and class | 8 |
| 8 jitters around S (σ 0.1, mics and switches kept with p 0.7) | 8 |
| 8 jitters around the target: 4 continuous-only (σ 0.1, the target's mics and switches kept) and 4 bank-style (mics and switches kept with p 0.7) | 8 |
| **Per target** | **59** |

- **MDN samples:** a component by π, then each continuous setting from its Gaussian **truncated
  to [0, 1]** (redrawn until inside), so no mass piles on the range limits (σ can reach e¹). Each
  switch by its sigmoid, each mic by its softmax. Seed:
  `numpy.random.SeedSequence([20261021, target, view, direction])`. The share of sampled values
  within 0.01 of 0 or 1 is reported beside the baselines'.
- **Baselines and jitters:** `numpy.random.SeedSequence([20261022, target])`, in a fixed order per
  target, so a dropped target shifts no other draw. "Best of K" for a baseline uses its first K
  draws.
- **Identical settings are rendered once,** so 59 × 120 = 7,080 is a ceiling (before any top-up).

## Step 1.2: knob sensitivity (about 0.8k renders)

- **15 windows,** 5 per amp, and their bases, all drawn by `random.Random(20261023)` from step
  1.1's eligible pool, outside its targets' tracks.
- **4 bases per window:** S, and 3 settings drawn like step 1.1's targets.
- **Per base:** the base, each continuous setting moved 0.15 toward the interior, and each switch
  flipped. That is 11 (PR12), 16 (SW50R) or 13 (AC20) renders per base, 800 in all.
- **Δjudge** = the judge between the base render and the moved one (both halves, mean). A setting
  is **flat** (level-only or inaudible) if its median Δjudge over its amp's 20 bases is below 0.05
  (half the informative floor). Flat settings are dropped from every knob diagnostic.
- **Jacobian:** finite differences of the judge's own 64-band log-mel frames, per amp. Its
  eigen-spectrum (participation ratio, and the settings in its smallest directions) shows which
  settings compensate for each other. Descriptive.

## The readings (declared now; first match wins in the next table)

- **Counts** ("≥ 2/3 of informative units") are unweighted unit shares within the fold, as in the
  old control. A band-weighted share is reported beside each.
- **Means** are band-weighted within the fold. Each figure also gets a pooled band-clustered 90%
  interval (14 bands, `song_readout.bw_stats`).
- **Thresholds** are inclusive ("at least"); "closer" is strict.
- **Fragile:** a fold's pass that flips when any one of its bands is left out. With 2 bands, fold
  3's check leaves 1 band, so it will often be fragile.

| Reading | Rule | Meaning |
|---|---|---|
| **R1, single shot** (per view) | The top-component mean closes ≥ 50% of the gap on ≥ 2/3 of informative units, **and** is strictly closer than the bank median on ≥ 2/3 | One answer works in the render domain |
| **R2, coverage** (per view) | Best of K MDN samples (K = 4 on 1a, K = 8 on 1b), picked on the search half, closes ≥ 50% on ≥ 2/3 of informative units, **and** its mean held log ratio against best-of-K random labels ≤ −0.03, **and** against best-of-K S-jitters ≤ −0.03 (the same K, the same picking) | The posterior holds good answers; what is missing is a picker |
| **R3, pipeline** | R1 passes on 1a and fails on 1b; or R2 at K = 4 passes on 1a and fails on 1b at K = 4 (1b's first 4 samples, no extra renders) | The song path (backing, mastering, separation) is the main loss |
| **R4, ill-posed at the control's bar** | Of the candidate renders that close ≥ 50% (pool below), ≥ 1/3 lie at knob distance ≥ 0.2 from the target, **and** on ≥ 2/3 of informative units at least 2 of the 4 continuous-only target jitters close ≥ 50% | A broad equal-score set exists; averaging explains R1's failure |
| **R4′, well-posed** | That share is < 10%, **and** the band-weighted mean, over informative units, of the within-unit Spearman between knob distance and gap closed is ≤ −0.5 | A sharp valley: the model is weak |

- **Per view, R1 and R2 read:**
  - **pass:** every fold passes, and no pass is fragile;
  - **undecided (ask the user):** 3 of 4 folds pass, or every fold passes but one or more passes
    is fragile (fold 3's fragility included);
  - **fail:** otherwise.
- **R4's pool:** per unit, every distinct setting rendered for that target except the target, its
  repeat and S. That is both views' and both directions' MDN proposals, the median, the constant,
  the random labels and all jitters, scored on the unit's held half (the landscape is model-free).
  Identical settings count once. The share is pooled over the fold's (unit, setting) pairs,
  unweighted; the band-weighted share is reported beside it, and so is the share split by whether
  the mics match the target's.
- **R4 and R4′** each need every fold. If neither holds, or the folds split, the reading is
  **between**. They depend on this candidate mix, which is fixed here.
- **Reported, not gating:**
  - the best-of-K curves (K = 1–4 on 1a, 1–8 on 1b), search-picked and oracle (held-picked), for
    the samples, random labels and S-jitters;
  - the top mean against the mixture mean (1b);
  - the bank-style target jitters beside the continuous-only ones;
  - every reading split by target type, broad and K_S-prior. The **label-sampling flag** is raised
    if the K_S-prior half meets R1's or R2's count while the broad half does not, in ≥ 3 of 4
    folds.

**Set-up check (read first).**
- **Pre-flight, before the draw:** twenty judge calls are timed, and d(render, repeat) is measured
  on 3–5 renders of non-target windows. If any repeat exceeds 1e-3, the tolerance is amended
  before the draw.
- **The check:**
  - the target's repeat render is within 1e-3 of it on both halves for at least 95% of targets
    (the rest are dropped and listed);
  - each fold has at least 40 informative units, after any top-up;
  - the top-mean code reproduces `song_model.predict_settings` exactly on 3 stored control inputs.
- **If any of these fails:** stop. A fix is a dated amendment; there are no silent re-runs.

## What each reading triggers

Read in order; the first match wins. Experiments 2 and 3 are the rethink's; each gets its own plan.

| # | Result | Next |
|---|---|---|
| 0 | Set-up check fails | Stop; amend; no reading |
| 1 | R1 passes on 1b | Arm B works one-shot on song-like renders, so step 3's loss is the record side. Experiments 2 and 3 do not run. Next: rung 2 (a fresh known-target draw, its own plan), then ask the user |
| 2 | R2 passes on 1b | A picker is missing. Experiment 2 is skipped. Then experiment 3A (the verifier) if experiment 4 has no passing rebuild by then; if it has one, arm C with the judge through that rebuild as the scorer (its own plan). **Step 1.3** is offered to the user (below) |
| 3 | R1 or R2 is undecided on either view, and no row above matches | Undecided: ask the user, with the per-fold and leave-one-band-out figures. Rows 4–6 do not run on their own |
| 4 | R3 (R1, or R2 at K = 4, passes on 1a only) | The song path is the loss. Experiment 2 runs as the confirmation. The next model step is song-robustness (for example, a clean-trained teacher distilled into a song-view student). Experiment 3 does not run |
| 5 | Both views fail; R4 | Experiment 2. If it passes R1: as row 4. R2 only: 3A. Fails both: **3B**, starting with a flow head if step 1.0 raised the collapse flag, else the render-in-the-loop relabel |
| 6 | Both views fail; R4′ | Experiment 2. If it fails both: the front-end follow-up (no time pooling, or a finer input), its own plan, ranked low. 3B does not run |
| 7 | Both views fail; between | Experiment 2, read on its own: R1 as row 4, R2 only 3A, fails both 3B with the front-end follow-up as its control |

Experiment 2 scores on these 120 targets, so their target renders, DI recipes and candidate
distances are kept.

**Step 1.3 (ask first, about 2.3k renders).** It is offered only on row 2 and runs only on the
user's own yes, even after this plan is approved.
- **What:** on step 3's 144 directions (24 parts × 3 amps × 2), fold-correct models, step 3's
  stored stem and mix features, 16 MDN samples per direction, through the part's measure DI,
  judged against the record at each part's `judge_lag` (as `song_armb.score`'s cells were), not
  lag 0. It is a further use of step 3's parts, entered in the ledger's tally before it runs.
- **Reported:** best-of-16 picked on the search half (a 16-render true-DI search) against S, the
  constant and K_S's stored incumbent at render 16, all band-weighted with intervals.
- **Reading:** "the posterior covers records" if the pick's band-weighted log ratio against K_S at
  16 is ≤ 0 and it beats S in ≥ 60% of bands; otherwise "renders only".
- **Consequence:** "covers records": row 2 as written. "Renders only": 3A or arm C still run, but
  rung 3 (songs) comes before any product step, and the user is told.

## Code (written and tested before any compute)

**A new module, `learn/song_diag.py`.** It reuses `song_bank`, `song_aug`, `song_model` and
`song_armb`, and `song_readout`'s band statistics and `gap_closed`. It changes none of them.

```
$TORCH_PY      -m learn.song_diag models          # step 1.0: collapse, calibration, correlations
.venv/bin/python -m learn.song_diag ks-replay     # step 1.0: replay the stored K_S searches
.venv/bin/python -m learn.song_diag preflight     # judge timing and repeat check, non-target windows
.venv/bin/python -m learn.song_diag draw          # step 1.1 targets and step 1.2 bases -> targets.json
.venv/bin/python -m learn.song_diag render-targets --shard i/3
$TORCH_PY      -m learn.song_diag features        # views 1a and 1b (separation, one process)
$TORCH_PY      -m learn.song_diag propose         # every candidate's settings -> candidates.json
.venv/bin/python -m learn.song_diag score --shard i/3
.venv/bin/python -m learn.song_diag sensitivity --shard i/3
.venv/bin/python -m learn.song_diag report        # set-up check, R1–R4′, the trigger row
```

- **Outputs** go to `~/ndsp-presets/learn/song-settings/diag/`. Each score file records the hash
  of the `candidates.json` it came from.
- **Kept:** distances and settings, target renders as 24-bit FLAC with their peak (plus the 16-bit
  copy the features use), no candidate audio. The committed summary is
  `docs/song-to-settings-diagnostics.json`.

**Tests, in `tests/test_song_diag.py`:**
- the draw: seeded and reproducible; no excluded track, band, crop or P1/P2 window; no backing
  from the target's own song; folds right; no overlapping windows; 15 + 15 per fold; the top-up;
- the fold check: each target goes to the model that held out its band, asserted against the
  bank's training rows;
- step 1.0's split: own-window examples apart from P1/P2 ones;
- the sampler: truncated to [0, 1], seeded, components chosen by π; top mean equal to
  `predict_settings`; per-target baseline seeds independent of other targets;
- the jitters: the continuous-only four keep the target's mics and switches;
- one timeline: the features' halves and the judge's halves are the same samples;
- best of K: picked on the search half, scored on the held half; a baseline uses its first K;
  non-finite search halves never picked;
- non-finite handling: units dropped and listed; refused candidates not closing and out of means;
- the mode separation and the collapse flag;
- R1–R4′, the pass / undecided / fail rule, fragility and the trigger table on synthetic units,
  including inclusive and strict edges, R3 at matched K, and a fold split into "between";
- knob distance with flat settings dropped;
- the K_S replay on a synthetic search;
- the memory guard's `vm_stat` parsing.

## Budget

| Item | Renders |
|---|---|
| Step 1.0 | 0 |
| Pre-flight (repeat check) | ≈ 10 |
| Step 1.1: 120 × 59 (ceiling) | ≤ 7,080 |
| Step 1.2: 60 bases × 11–16 | ≈ 800 |
| **Experiment 1** | **≈ 7.9k (hard stop at 8.2k, top-up included: ask)** |
| Step 1.3, ask first, only on row 2 | ≈ 2.3k |

**The running total:** about 132–133k actual before this (the ledger's 143.2k includes experiment
4), plus experiment 4's declared ≈ 11.1k, gives ≈ 144k. With experiment 1 it is ≈ 152k, and
≈ 154.5k if step 1.3 runs, against the 200k limit. The rethink's worst path (experiments 2 and
3A) is ≈ 173k. The kNN proposer (the rethink's optional 1k) is not run here; adding it needs an
amendment before any step-1.1 score is read.

## Order on the machine

Experiment 4's MPS training holds about 17 GB of the 32 GB and has priority. Experiment 1 uses
the CPU only.
1. **Code, tests and an independent review of this plan** (done 2026-10-16). Then the ledger
   entry (below) and a message to the product session.
2. **On the user's yes:** step 1.0 (one torch process on the CPU, 2 threads, bank features
   streamed in batches of 256) and the K_S replay.
3. **Step 1.1:** pre-flight, draw, then target renders (3 processes), then features (one process,
   2 threads, alone), then candidates, then scoring (3 processes).
4. **Step 1.2** (3 processes).
5. **The report,** an independent audit, then `docs/song-to-settings-diagnostics-results.md`, the
   ledger outcome, the roadmap and the docs index.

**Wall clock:** about 2–3 h of renders at the label table's 3-process rate (about 5k/h), slower
beside training. Add about 15 min of separation and about an hour for step 1.0.

**Guards:**
- **Processes:** at most 3 Morgan render processes on the Mac at once, counting experiment 4's.
  Its CPU renders go first, and experiment 1's shards pause and resume (skip-if-exists).
  Processes are reused; the licence daemon is never touched.
- **Threads:** torch and separation steps are capped at 2 threads.
- **Memory:** a process starts only if `vm_stat` shows at least 6 GB available (free + inactive
  + speculative). Each process re-checks every 20 renders. Below 3 GB, or if swap use has grown
  by more than 1 GB since launch (`sysctl vm.swapusage`), it sleeps in 60-s steps and exits after
  15 min. Torch steps (1.0, features, propose) never run beside the render processes.
- **Training speed:** if experiment 4's logged step time grows by more than 25% against its median
  before launch, experiment 1 drops to 2 processes.
- **Disk:** `knob_ceiling2.disk_ok` (31 GB) every 50 renders; 30 GB is kept free. Experiment 1
  writes under 1 GB.

## The ledger entry (entered 2026-10-16, before any experiment-1 compute)

```json
{
 "test_id": "song-settings-diagnostics",
 "plan": "docs/song-to-settings-diagnostics-plan.md",
 "entered": "2026-10-16, before any experiment-1 compute; reviewed 2026-10-16, approved with changes, all folded in; starts only on the user's yes (step 3's readout is step 6 row 4, whose next step this is not)",
 "repeat_use": "No development record is scored. Audio only: DI tracks and backings of classed development parts outside knob ceiling's 25 parts (also used in arm B's bank and the label table). Step 1.0 reads arm B's bank (fold-own-window examples; P1/P2 apart) and replays step 3's stored K_S runs on knob ceiling's 24 parts (zero renders, descriptive). Step 1.3 is ask-first (the user's own yes, only on reading row 2); if run it is a further use of step 3's 144 directions, judged at each part's judge_lag, and is entered in the tally before it runs. Experiment 1's target tracks stay out of any later training set, so a later rung-2 draw on those parts stays clean",
 "parts": ["no development record is scored: targets are DI windows drawn at run time (random.Random(20261020)); the drawn window list is appended here before any render"],
 "bands": "Rebuild The Evil, Swatkins, Szymon Skiba, The Travelling Band (fold 0); Ale Lak, Diesel13, Doom Flamingo, Renesans (fold 1); Death Of A Romantic, Eat The Feeder, Hollow Ground, John Morgan Kimock (fold 2); Bernard Purdie Tribute All-Stars, Starnes And Shah (fold 3; 2 bands whatever step 5 decides: Eggy and Timo have no track outside knob ceiling's parts). Excluded: knob ceiling's 25 parts' DI tracks and crops, experiment 4 step 5's 8 candidate bands (whole bands: its part pool is not pinned), Guitar-TECHS P1/P2",
 "audio_only": "120 target windows (plus any declared top-up) + 15 sensitivity windows from those bands' DI tracks, no two overlapping on a track, and same-fold backings never from the target's own song; the exact tracks and windows are added to the tally at the draw, before any render",
 "folds": "docs/song-settings-folds.json; each target scored by song-settings/models/fold{f}/model.pt for its band's fold (asserted)",
 "seeds": "targets random.Random(20261020) (top-up continues it); MDN samples numpy SeedSequence([20261021, target, view, direction]), truncated to [0,1]; baselines and jitters numpy SeedSequence([20261022, target]); sensitivity windows and bases random.Random(20261023); K_S replay 20261013 (K_S's)",
 "gate": "Diagnostic. Units informative if d_S, d_T and the target are finite on the held half and d_S - d_T >= 0.1; non-finite units dropped and listed; refused candidates count as not closing and are out of means. Counts are unweighted unit shares within a fold; means band-weighted; pooled band-clustered 90% intervals; fragile = a fold pass flips with one band left out. Set-up: pre-flight repeat <= 1e-3 on non-target renders, target repeat within 1e-3 on >= 95% of targets, >= 40 informative units per fold after top-up, top-mean parity. R1 (per view): top mean closes >= 50% on >= 2/3 and strictly closer than the bank median on >= 2/3. R2 (per view): best-of-K truncated-normal samples (K=4 view 1a, 8 view 1b) picked on the search half close >= 50% on >= 2/3 and mean held log ratio <= -0.03 vs best-of-K random labels and vs best-of-K S-jitters. Per view R1/R2: pass = every fold, none fragile; undecided (ask the user) = 3 of 4 folds, or any fragile pass (fold 3 included); else fail. R3: R1 passes on 1a and fails on 1b, or R2 at K=4 passes on 1a and fails on 1b at K=4. R4 (pool: every distinct setting for the target except target, repeat and S, on the unit's held half; pooled unweighted per fold): >= 1/3 of renders closing >= 50% lie >= 0.2 mean knob distance from the target, and >= 2 of the 4 continuous-only target jitters close >= 50% on >= 2/3 of units. R4': that share < 10% and band-weighted within-unit Spearman(knob distance, gap closed) <= -0.5. Neither or folds split: between. Triggers (first match): set-up fails -> stop; R1 on 1b -> rung 2, no experiments 2-3; R2 on 1b -> 3A (or arm C if experiment 4 passes), step 1.3 offered (ask first; 'renders only' puts rung 3 before any product step); R1/R2 undecided -> ask the user; R3 -> experiment 2 as confirmation, then song-robustness; both views fail -> experiment 2, then by R4 (3B), R4' (front-end follow-up), between (experiment 2 alone decides). Flags: collapse (median mode separation sum_k pi_k|mu_k - mu_bar| / sum_k pi_k sigma_k over audible settings < 0.5 in >= 3 of 4 folds; threshold set after the audit was readable) picks 3B's flow head; label sampling (K_S-prior half meets R1/R2 counts, broad half not, >= 3 of 4 folds); flat settings (median Delta-judge < 0.05) dropped from knob diagnostics",
 "renders": "budgeted ~7.9k (pre-flight ~10, step 1.1 <= 7,080, step 1.2 ~0.8k), hard stop 8.2k including any top-up; step 1.3 ~2.3k ask-first, only on row 2. Running total ~132-133k actual + experiment 4's ~11.1k declared = ~144k; with experiment 1 ~152k; with step 1.3 ~154.5k of 200k. CPU only, <= 3 render processes counting experiment 4's, torch and separation at 2 threads, memory guard",
 "tally": [],
 "outcome": null
}
```

## Deviations from the rethink

- **No Guitar-TECHS P1/P2 windows,** and fold-own bands only. Every fold model heard overlapping
  P1/P2 audio from the same players, so "unseen" would hold for the window but not the audio.
  Step 1.0 likewise reads fold-own-window examples, with P1/P2 apart.
- **Experiment 4's step-5 bands are left out entirely,** not only its parts, because its draw is
  not made and its part pool is not pinned. This does not change fold 3's count.
- **One trimmed timeline** for features and judging (the old control was offset by 0.25 s).
- **A repeat render per target** (+120) measures d_T rather than assuming it is 0.
- **Target jitters are split** 4 continuous-only and 4 bank-style, and R4's jitter clause reads
  the continuous-only four (at least 2 of 4). Bank-style jitters change a mic or switch 55–72% of
  the time, which the knob distance does not see.
- **MDN samples are truncated to [0, 1],** not clipped.
- **R3 compares the views at matched K** (4); row 2 keeps K = 8.
- **An undecided outcome** for R1 and R2, which asks the user.
- **The collapse flag** uses mode separation, not exp(H(π)).
- **Step 1.3 is ask-first,** with a declared consequence.
- **Step 1.2 uses 15 windows × 4 bases** (5 per amp, so each amp has 20 bases), not 10 × 4.
  Mics are not moved.
- **No second guitar** in either view, so the views differ only by mastering and separation.
- **The kNN proposer is not run.**

## Stated limits

- **The models are fixed:** one architecture, one recipe, one seed per fold.
- **The targets are reachable by construction** (measure DI, synthetic). Passing here says nothing
  yet about records; rung 2 and step 1.3 do that.
- **Fold 3 has 2 bands,** and 14 bands are pooled for intervals. The two directions of a target
  are nearly the same draw, so each fold has at most about 30 effective units from 2–4 bands.
  The every-fold rule is strict: at a true rate of 0.75, all four folds pass about 64% of the
  time. The undecided row keeps a near miss from being read as a fail.
- **View 1b is harder than step 3's inputs:** step 3's mixes were unmastered, and the 10-s
  separation is not the 30-s context step 3's stems came from. R3 cannot tell mastering from
  separation; experiment 2 takes that question.
- **R4 and R4′ depend on the candidate mix** declared here. The K_S replay's equal-score sets come
  from search paths, not uniform samples.
- **The collapse threshold was set after the audit was readable.**
- **The judge's taste for extremes** applies to every distance here; no listening is planned,
  because no preset is chosen.
- **Development data only.**

## Implementation notes (2026-10-16, before any compute)

- **Per-target seeds:** `random.Random(20261020)` fixes the window order. Each target's own draws
  use a SeedSequence over (20261020, fold, index in fold), so a top-up shifts no existing target.
- **Step 1.3's sample seed:** 20261024, declared when step 1.3 is offered.
- **Two guards the operator runs by hand:**
  - experiment 4's slowdown, read from its log;
  - the 3-process cap, applied as `--shard` ≤ 3 per step.
- **The target's held distance is 0 by definition:** the repeat render supplies d_T.
- **A top-up suggests `ceil(shortfall / 2)` targets.**
- **Step 1.0 runs one example at a time.**
- **The Jacobian** uses the judge's log-mel at FFT 2048.
- **`models` runs twice:** a second run after `report` gives the audible-setting figures, read
  from `flat.json`.
