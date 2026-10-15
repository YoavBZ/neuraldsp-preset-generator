# C′'s successor for fine structure: plan (DI-recovery experiment 4)

Declared 2026-10-15, before any experiment-4 compute. The design is
[`research/di-rebuild-fine-structure-2026-10.md`](research/di-rebuild-fine-structure-2026-10.md)
(called "the research" below); this file makes it concrete: the code, the numbers, the order and
the rules. Development data only. The rules of
[`research/ml-plan-2026-10.md`](research/ml-plan-2026-10.md) section 5 apply throughout.

**Review:** reviewed 2026-10-15 (`tmp/di-fine-structure-plan-review.md`, local): approved with
changes, all folded in.

## Why

Arm A's known-target control failed: through C′'s rebuild, the search closed ≥ 50% of the gap on
3 of 9 informative cells, with mean shortfall +0.320 against the measure-DI run's −0.062
([song-settings-plan.md](song-settings-plan.md), recorded outcome). The rank-margin ladder then
showed that C′'s tone balance and slow envelope are not the cause: an oracle 5–10-ms envelope
transplant recovers about 6% of C′'s margin loss. What is left is waveform detail under about
10 ms ([rank-margin-ladder-results.md](rank-margin-ladder-results.md)).

So experiment 4 keeps C′'s network and changes what it is trained against: fine-tunes from C′ with
short-window spectral terms, a phase-derivative term, a peakiness term with a gap guard, and last
a balanced discriminator. Fold 3 goes first.

## Process

Plan, review, the ledger entry, a message to the product session, then run, then an audit. Changes
are dated amendments.

## The gate

**Only the full known-target control can pass or stop a rebuild.** The rank margin is computed and
reported for every rebuild, but it never gates. It agreed with search success on 14 of 18, and on
5 of 9 within C′'s run. On fold 3, C′'s margin is ≤ 0 on 3 of 4 cells, yet its search closed 2.

The control is song-settings' arm-A control, unchanged: the same 12 cells
(`song_settings.control_cells`), the same fakes and targets, `knob_search` from S at 150 renders
with seed 20261013 on half A, and every best judged through the measure DI on half B. Only the
rebuilt run is new; the stored measure-DI run is reused.

**The pass rule, and where −0.032 comes from.** Amendment 2 makes a cell informative only if
d_S − d_target ≥ 0.1 on half B. With at least 6 informative cells, row 2 says the rebuilt run
passes if either:
- it closes ≥ 50% of the gap on at least two-thirds of the informative cells; or
- its mean shortfall over the informative cells is within 0.03 of the measure-DI run's.

The readout code (`song_readout.py`) reads "within" as one-sided and "two-thirds" as inclusive.
On the recorded control, 9 cells are informative, and the measure-DI run's mean shortfall is
−0.0615. So a successor passes with:

- **≥ 6 of 9 informative cells closing ≥ 50% of the gap, or**
- **a mean shortfall ≤ −0.0615 + 0.03 = −0.0315.**

The research's −0.032 is the same rule with −0.062 rounded first. The code computes the figure
live, so −0.0315 binds; the two differ by 0.0005.

**On fold 3 alone (step 2, a pre-check, not the gate).** Fold 3 holds 4 of the 9 informative
cells:
- Prodigal × PR12 and SW50R (Starnes And Shah);
- just-don't-talk × PR12 and SW50R (Timo And The Timezone).

With fewer than 6 cells, the readout code would switch to amendment 2's all-cell shortfall mode.
That mode also passes at a shortfall ≤ 0, which is looser. Step 2 therefore has its own, stricter
rule, built the way row 2 is:

| | Closed ≥ 50% (of 4) | Mean shortfall, fold-3 informative cells |
|---|---|---|
| Measure-DI run (stored) | 4 | −0.043 |
| C′ (stored, searched with the −52 objective) | 2 (Prodigal PR12 0.64, just-don't-talk SW50R 0.71) | +0.201 |
| **Go** | **≥ 3** | **or ≤ −0.043 + 0.03 = −0.013** |
| **Stop the arm** | ≤ 2 | and > +0.201 − 0.03 = +0.171 |
| Otherwise | | undecided (step 2's fold-1 branch) |

- **Why not −0.032 on fold 3:** that is the 9-cell figure. On fold 3 it would be stricter than
  amendment 2's own reading.
- **Where the figures come from:** the stored `armA-control/*-result.json` files, read while
  drafting. The review re-derived them.
- **C′ is not re-run at lag 0:** its two closures sit 0.14–0.21 above the 0.5 line, and its misses
  are at 0.01 and −0.46. A lag shift of 0.002–0.01 in log shortfall can't move its count. The
  missing baseline is fine-tuning noise, and 1z answers that (step 2).

## Repeat use, declared

This is the **third** development use of the 12 control cells: first step 3's control and its
audit (`diag1`–`diag4`), then the rank-margin ladder. For colour-me-red and just-don't-talk it is a
later use still. Those two parts were also used by:
- cprime-folds check 2, which 1d reuses on their set-3 stems;
- the separator screen;
- the separator upgrade.

Inside experiment 4 the cells are touched several times, all under this one declared use:
- 0a's gap spectra;
- 0b's D0, idempotence and swap rung;
- 0c's DAC check;
- steps 2 and 4.

Nothing is fitted on them. Arm choices before step 2 use only the held fold's validation pairs.

**The weakness, stated plainly:**
- There are 9 informative cells from 5 DIs and 6 bands.
- Fold 3 is 4 cells from 2 parts, so one cell is 25% of fold 3's count and 11% of the full count.
- The arm is chosen on fold 3's cells (and, on the fold-1 branch, fold 1's: 7 of step 4's 9).

Step 4 also reports its 5 non-fold-3 cells apart, and step 5's fresh draw is the guard against a
fit to these cells.

## Step 0: diagnostics and checks before any arm

| # | What | Renders | Machine | Decides |
|---|---|---|---|---|
| 0a | Zero-cost reads (below) | 0 | CPU, < 1 h | Arm order; the fold-3 bar (done above) |
| 0b | D0, C′ idempotence, swap rung | 48 + 24 + 36 = 108 | CPU, < 1 h | Where in time C′'s error is; magnitude over time against phase |
| 0c | DAC ceiling check | 48 | CPU, < 1 h | Whether E1′ is opened in experiment 4 |
| 0d | Loss-scale calibration, 200-step timing and gradient check per arm | 0 | MPS, ~1 h; needs the rebuilt caches | Real step times; the exact weights |
| 0e | Capacity check (overfit) | 0 | MPS, ~1–2 h; needs the rebuilt caches | Whether arm 1e joins |

**0a, the zero-cost reads.**
- **Phase scramble and bleed** (read while drafting, from `rank-margin/report.json`), on the 9
  informative cells:
  - scrambling the true DI's phase above 1 kHz inverts 0 of 9 (mean m 0.244 → 0.142);
  - bleed at −20 dB inverts 0 (0.159), and at −10 dB inverts 2 (0.070).

  By the research's rule ("if it inverts none, phase above 1 kHz is not the lever"), the
  short-window and peakiness terms lead, so arm 1a runs first, as declared. 1b still runs: the
  scramble cost 42% of the mean margin, and on Prodigal PR12 it cut the true DI's margin from
  0.115 to 0.018.
- **C′'s gate state:** the logs show `dec.0` open at 0.52–0.58 on every fold (fold 3: 0.55), so
  the bottom levels are alive. `gate_open` is recomputed on each checkpoint's 96 validation crops
  to confirm.
- **The gap-spectrum test:** compare C′'s gap spectra (the stored `<cell>-rebuilt.npy`) with the
  fake's gaps and the true DI's. A high correlation with the fake means pass-through; a flat
  broadband excess means an error floor. Report only.
- **Free disk:** 69 GiB (74 GB) on 2026-10-15, while drafting.

**0b (renders saved this time, as 16-bit FLAC).** The first 0.25 s of each saved render is trimmed
before any audio use. On the 12 cells:
- **D0:** S and T through C′'s rebuild and through the measure DI (48 renders). Each frame's judge
  error is split into:
  - attack: ≤ 50 ms after an onset;
  - sustain;
  - quiet: record frame ≥ 20 dB below its peak.
- **Idempotence:** r₁ = A_T(x̂), x̂₂ = C′(r₁), then S and T through x̂₂ (24 renders). Compare
  `crest_db` and the envelope of x̂₂ with x̂'s. Report only.
- **The swap rung (36 renders):** on the 9 informative cells, S and T through (the true DI's STFT
  magnitude with C′'s phase), and through the reverse. FFT 1024, hop 256, with the ladder's lag
  check (±3 samples).
  - If the true magnitude restores the margin, the error is magnitude over time.
  - If the true phase restores it, the error is phase and fine shape.
  - It is descriptive. It moves 1b ahead of 1a only if the true phase restores m > 0 on ≥ 6 of 9
    and the true magnitude on ≤ 3.

**0c, the DAC ceiling check (zero training, CPU).**
- **The round trips:** each cell's measure DI through the 44-kHz DAC (MIT; the weights E0 and E0b
  used), with 4 and 9 codebooks. It is resampled 48 → 44.1 → 48 kHz around the model only.
- **What is measured, against the true DI:**
  - crest at 1, 5 and 10 ms, and the quiet-frame level;
  - the shift stability of the post-quantisation `z` under 1–8-sample delays;
  - the margin, with S and T rendered through each round trip (12 × 2 × 2 = 48 renders).
- **The comparator** comes from 0c's own scoring: the same half, lag and judge as the round-trip
  renders, reusing D0's measure-DI renders. It is not taken from `report.json`.
- **A resample-only control** (48 → 44.1 → 48 kHz without DAC) is measured on crest and quiet
  level only, at zero renders, to separate the resampler's loss.
- **E1′ opens only if the 9-codebook round trip:**
  - keeps m > 0 on all 4 fold-3 informative cells;
  - has a fold-3 mean m ≥ 0.75 × the true DI's (as scored in 0c);
  - keeps its 1-ms crest within 1 dB of the true DI's.

  Otherwise E1′ is closed for experiment 4, not for good: the margin disagreed with search on 4
  of 18.
- **If it opens,** E1′ gets its own plan after step 2's readout. Its training and renders are not
  budgeted here.

**0d, the calibration (the share rule, pre-registered).** The code is listed under Bookkeeping.
- **"Share":** a term's weighted mean divided by L_C′'s mean, both measured on the same 50 batches.
  - **The batches:** fold 3's training split, seed 0, batch 12, C′'s augmentation.
  - **The network:** `models-cprime-f3/fold3.pt`, unchanged.
- **The weight:** a term keeps its provisional weight (Arms, below) if its share lies in the
  declared range. Otherwise it is set to the range's midpoint, rounded to one significant figure.
- **Order:**
  1. 1a's three terms are calibrated together.
  2. 1b's phase weight is calibrated with 1a's final weights in place. Its range is 0.3 × (the
     short-window MR-STFT plus C′'s `mrstft`) ± 50%.
- **Once, on fold 3.** Step 3's folds reuse the same weights, with no per-fold recalibration.
- **The ledger** records the 50-batch means and the final weights before step 1a starts.

**0d, the gradient check and timing.**
- **The gradient check:** CPU against MPS at crop length (144,000 samples), before training and
  again after 200 steps, as in the EG-VAE plan. Every STFT and phase term runs on the CPU, as
  `mrstft` does. A term whose gradients disagree (cosine < 0.99) stops its arm.
- **Timing:** 200 steps per arm, which replaces every hour estimate below.

**0e, the capacity check (zero renders).** Does C′'s output stage draw sub-millisecond detail at
all? It is one linear transposed convolution from 12-kHz features, with no full-rate path.
- **The set-up:**
  - from `models-cprime-f3/fold3.pt`, 8 fixed crops from fold 3's *training* split (seed 0, no
    augmentation);
  - batch 8, 2,000 steps at a constant 1e-4;
  - two runs: one with arm 1b's loss, and one with L_C′ alone as the reference;
  - the checkpoints are thrown away and never rendered.
- **Pass (1b's loss), on those 8 crops:**
  - **in the loss:** the mean 1-ms and 2.5-ms crest within 1 dB of the true DI's, and the gap
    level within 3 dB;
  - **out of the loss, both required:**
    - the 0.5-ms crest (24-sample frames, not in any loss) within 1 dB of the true DI's;
    - the waveform SNR against the true DI at least 3 dB above the L_C′-only run's.

  C′'s starting values and the L_C′-only run are reported beside them. A pass shows only that the
  network can memorise the detail, not that it will learn it.
- **If it fails:** run the same overfit with the full-rate head (arm 1e).
  - If the head passes, arm 1e joins step 1.
  - If both fail, the loss route is reported as limited by capacity. The arms still run, read
    with that caveat.

## Step 1: the fold-3 arms

**Shared.** Every arm fine-tunes `~/ndsp-presets/learn/direc/models-cprime-f3/fold3.pt` with
`learn.direc fit --fold 3`.
- **The data:** C′'s recipe, unchanged:
  - `--cache cache --extra-cache cache-sw50r cache-ac20`;
  - the frozen `average-fold3.npy`;
  - bleed from the training folds' backings;
  - C′'s augmentation and per-crop scaling (input and target each to std 0.1).
- **The interpreter:** `~/ndsp-presets/tools/demucs-venv` (torch 2.14), on MPS, with
  `setopt no_bg_nice`.
- **Seed 0** for every arm, so the arms differ only in the loss.
- **The schedule:** 5,150 steps at batch 12.
  - A new `--warmup 200` ramps linearly from 0 to 1e-4. A cosine decay then runs to 2e-5
    (`--lr 1e-4 --lr-end 2e-5`).
  - `--resume` loads weights only, so the optimiser is a fresh AdamW (weight decay 1e-5), as in
    C′'s stage 2.
  - Gradients are clipped by hand at 5.0, and non-finite steps are recovered as in `fit`.
- **The preflight:** `learn/cprime_folds.py preflight --fold 3` must give 38,204 / 10,602 / 33.
- **The outputs:** `models-fs-<arm>-f3/`, each with a DONE marker. C′'s folders are never
  written.

C′'s own loss is L_C′ = 100·L1 + mrstft(256–4096), about 6 per training batch. The new terms, with
their provisional weights and the share ranges used by 0d:

| Term | Definition | Device | Provisional weight | Share of L_C′ |
|---|---|---|---|---|
| Short-window MR-STFT | `mrstft` with FFT 32, 64, 128 (hop n/4): spectral convergence + log-magnitude L1, floor 1e-6 | CPU | 1.0 | 15–40% |
| Peakiness | Mean \|crest_pred − crest_true\| in dB, on non-overlapping 1-ms (48) and 2.5-ms (120) frames within 35 dB of the crop's loudest | MPS (reshape only: no STFT, no matmul on unfolded frames) | 0.1 | 5–15% |
| Gap guard | Mean relu(L_pred − L_true), L in dB re the crop, on 5-ms frames more than 35 dB under the crop's loudest; floor −90 dB | MPS | 0.02 | 3–10% |
| Phase derivative | Magnitude-weighted 1 − cos of the instantaneous-frequency difference (across time) and the group-delay difference (across frequency). Computed as phasor products, never `atan2` or complex `abs`. FFT 256, 512, 1024, hop n/4 | CPU only | 1.0 | 0.3 × (short-window + `mrstft`) ± 50% |

| Arm | Loss | Steps | MPS time (to be replaced by 0d) |
|---|---|---|---|
| **1z** | L_C′ alone, on the same schedule: the fine-tuning noise control. Rendered in step 2 under R1's condition | 5,150 | ~1.5 h |
| **1a** | L_C′ + short-window + peakiness + gap guard | 5,150 | ~1.5–2 h |
| **1b** | 1a + phase derivative | 5,150 | ~2–3 h |
| **1c** | The better of 1a and 1b by 1d's 1-ms crest error (ties within 0.2 dB go to 1a), + MPD/MSD | 5,150 | ~3–5 h |
| 1e | Only if 0e failed and the head passed it: the better of 1a and 1b + the full-rate head | 5,150 | ~2–3 h |

**1c's adversarial set-up.**
- **The discriminators:** HiFi-GAN's MPD (periods 2, 3, 5, 7, 11) and MSD (3 scales). LSGAN with
  feature matching, on MPS (waveform convolutions only).
- **The optimiser:** AdamW at 1e-4, betas (0.8, 0.99), with a cosine decay to 2e-5 alongside the
  generator.
- **The warm start:** for steps 0–500 the discriminators train, and the generator sees only the
  reconstruction loss.
- **The balancer (EnCodec style):** from step 500, each term's gradient with respect to the output
  waveform is scaled by an EMA (decay 0.999) of its norm. The shares are:
  - reconstruction (the whole 1a or 1b loss) 0.7;
  - feature matching 0.2;
  - adversarial 0.1.
- **Memory:** if batch 12 does not fit beside the discriminators, batch 6 with 2-step
  accumulation.

**1e's head.** y = C′(x) + h(C′(x), x).
- **h:** three 48-kHz convolutions (32 channels, kernel 9, dilations 1, 2 and 4, GELU), then a 1×1
  output convolution initialised to zero, so the model starts out identical to C′.
- **The risk:** it feeds the input at full rate, so the residual network's lesson applies (R kept
  the amp's distortion). 1d's 3–8 kHz guard covers it.

**1d, the in-training screen.** It runs on the held fold's 96 fixed validation crops, never on
control cells. Each arm's final checkpoint is compared with C′'s.

**Hard stops: breakage guards only.** An arm with any of these gets no renders:
- **Validation:** (val / input-as-DI baseline) for the arm is above C′'s ratio + 0.02, on the same
  96 crops (C′ fold 3: 0.519).
- **Network check:** cprime-folds check 2 below 0.1126.
- **Brightness:** the 3–8 kHz level more than 2 dB above C′'s.

**Reported, not gating:**
- crest at 1, 5 and 10 ms against the true DI (C′ is 3.6–5.5 dB low on the cells);
- the gap level against the true DI's (C′ is 15–20 dB over);
- 1z beside every arm.

Crest and gap are the hypothesis under test, so they never stop an arm. They are used only to rank
arms when more pass than the cap allows (step 2).

## Step 2: the fold-3 pre-check

**Which arms are rendered.**
- **The cap:** at most 3 arms are rendered without the user's yes: 1a, 1b, and the better of 1c and
  1e by 1d's 1-ms crest error.
- **A fourth arm** needs the user's yes.
- **An arm that hit a breakage stop** is dropped.

**For each rendered arm:**
1. **Rebuild** the 4 fold-3 control fakes with the arm's network, on the CPU, as
   `song_settings.control_rebuild` does: re-equalised by (fold 2's average − fold 3's), then set
   to −22.9 LUFS.
2. **Lag check:** the GCC lag against the raw DI must be within ±3 samples, or the cell stops and
   is reported.
3. **The rebuilt run:** 150 renders per cell. The objective is `rebuilt_distance` on half A at
   **lag 0**, since the rebuild is aligned to the input DI. The render latency of 52 is unchanged.
   C′'s stored run used −52.
4. **The margin:** S and T through the rebuild (2 renders per cell), reported only.
5. **The rule:** the fold-3 table under The gate.

**The noise control (1z).** If any arm reads go or undecided, 1z's fold-3 rebuilt run is rendered
at lag 0 (about 0.61k) before step 3 starts.
- If 1z itself meets the go row, the gain is put down to fine-tuning, not to the fine-structure
  terms.
- An arm goes ahead of 1z only if it closes more cells, or has a mean shortfall at least 0.03
  lower.

**Combining the arms.**
- **Go:** any arm's go wins. Undecided and stopped arms are dropped.
  - If several arms go, the one recipe that goes forward has the most cells closed, then the lower
    mean shortfall, then the cheapest: 1z, 1a, 1b, 1e, 1c.
  - If 1z ties with an arm under the rule above, 1z goes forward, and experiment 4's terms are
    reported as not shown.
- **Undecided:** if no arm goes, only the undecided arms take the fold-1 branch.
- **Stop:** if every arm stops, step 2 ends with its numbers reported. Experiment 4's loss route is
  then reported as failed on fold 3.

**The fold-1 branch (needs the user's yes).** The fold-3 network trained on folds 0–2, so it can't
rebuild fold-1 cells: their bands are in its training pool.
- **The cost:** each undecided arm is fine-tuned on fold 1 from `models-cprime-f1`, with the same
  recipe and weights. That is 1.5–5 h of MPS per arm, plus 3 informative cells × ~153 renders per
  arm (≤ 1.4k).
- **The 7 cells** (fold 3's 4, plus colour-me-red PR12 and SW50R and Blind Spots SW50R) are read in
  the readout's ≥ 6-informative mode:

| | Closed ≥ 50% (of 7) | Mean shortfall |
|---|---|---|
| Measure-DI run (stored) | 7 | −0.0777 |
| C′ (stored) | 3 | +0.232 |
| **Go** | **≥ 5** | **or ≤ −0.0777 + 0.03 = −0.048** |
| **Stop** | ≤ 4 | and > +0.232 − 0.03 = +0.202 |
| Otherwise | | undecided: report it and ask the user |

- **The cost to the test:** fold 1's cells then join the selection set, so 7 of step 4's 9 cells
  helped choose the arm.

## Steps 3–5: four folds, the gate, and a fresh draw

**Step 3: the winning recipe on the remaining folds.** It runs on folds 0, 1 and 2 (fold 1 only if
the branch didn't already train it). Each starts from its own fold's C′: `models-cprime-f0`,
`models-cprime-f1` or `models-cprime/fold2.pt`. The fold-leak rules are cprime-folds':
- **The fold:** `--fold f` with the same caches, the frozen `average-fold{f}.npy` and the training
  folds' bleed.
- **The preflight counts must match:**
  - fold 0: 34,792 / 14,014 / 27;
  - fold 1: 38,188 / 10,618 / 29;
  - fold 2: 38,709 / 10,097 / 37.
- **The pin:** the run is pinned to a commit, recorded in its log.
- **The outputs:** `models-fs-<arm>-f{f}/`. `cprime_ready` is generalised so every `models-fs-*`
  network needs its DONE marker before use.
- **New in code: every rebuild asserts no leak** against the network's actual training pool. The
  pool is the bands in the caches' `meta.json` after the fold split, plus the bleed parts' bands,
  not the K3 label alone. The cprime-folds audit found this was checked by hand only.
- **No bank pairs and no stems** in this stage. Guitar-TECHS P1 trains every fold, as in C′.

Fold 3's network is the step-1 checkpoint itself.

**Step 4: the full known-target control (the gate).**
- **The renders:** rebuilt runs on the remaining cells. Fold 3's 4 cells (and fold 1's, after the
  branch) are reused from the winning arm's own folder: the same network and seed.
- **The rule:** the one under The gate, read by `song_readout`'s control function on the new
  results.
- **Reported:** per band, leave-one-band-out, the 5 non-fold-3 cells apart (descriptive), and the
  margin beside it.

**Step 5: confirmation on a fresh draw.**
- **The cells:** 12 new cells, declared in an amendment before any of their renders.
  - **The bands:** the 8 song-settings development bands outside the control's 6: Adam Buckley,
    Atlantis Bound, Dom McLennon, Eggy, Magician's Nephew, Turbosauro, Wall Of Death and Zeno.
  - **The draw:** `random.Random(20261019)`, 6 bands (at least 2 crunch if 2 remain), one part per
    band, × PR12 and SW50R.
- **The networks:** each cell is rebuilt by the network whose held fold contains its band, with the
  same leak assertion.
- **The runs:** both runs at 150 renders. The control's own rule applies, with amendment 2,
  reported band-weighted with leave-one-band-out.
- **If the measure-DI run gives row 1** (set-up wrong): undecided. Arm A does not re-run, and the
  user is asked.
- **Only a pass here lets arm A re-run.**

## Stage 2, the hedge, and E1′ (after the gate)

- **Stage 2 runs only after step 4 passes,** each part in its own plan:
  - **Amp conditioning:** FiLM on amp identity in the decoder's last blocks. Gain goes through an
    "unknown" token 10–20% of the time. It is gated on fold 3's crest and peakiness.
  - **Stems:** first, the zero-render separator-share test: C′ on separated bank examples, from the
    pre-mix render and from the stem.
    - Arm B's `build` has finished, so the stem waveforms were not saved. Re-separating 5k items
      costs about 28–39 CPU hours.
    - The bank's `average-fold2.npy` target must be reconciled with each fold's before mixing.
    - The 59 real-stem parts are validation only.
- **The scoring hedge (S)** isn't pre-registered here. It needs its own plan, review and ledger
  amendment before any panel render. Only its ~3.0k render reservation is kept below.
- **E1′:** only if 0c opens it, in its own plan.

## Machine order (one sequence)

The Mac has 32 GiB. A C′-scale fine-tune holds about 17–18 GB. Only one MPS job runs at a time.

1. **Now, while arm B trains on MPS:** write the code and tests, then run 0a, 0b and 0c (CPU).
   0b and 0c run only if resident memory leaves room beside arm B's training.
2. **Arm B's training ends.**
3. **Arm B's readout renders.**
4. **The Mega-53 separator screen, alone:** no MPS job, no rebuild and no render beside it (its
   plan).
5. **The SW50R and AC20 cache rebuild** (`rebuild_caches.sh`; see Disk).
6. **0d, then 0e.** Both need the rebuilt caches.
7. **1z, 1a, 1b, 1c (and 1e),** one after another on MPS. Step 2's rebuilds and renders run on the
   CPU while the next arm trains, as C′'s folds ran beside step 2; throughput is logged.
8. **Step 3's folds,** then step 4, then step 5.

**The loss stays on the CPU.** `torch.stft`'s gradient is wrong on MPS above 65,536 samples, and
crops are 144,000. Every spectral and phase term goes through the CPU, as `mrstft` does.

**Machine time:**
- step 1, with 1z and 0d–0e: about 10–17 h of MPS;
- step 3: 6–15 h;
- 1e: about 2–3 h more if it runs;
- the fold-1 branch: 1.5–5 h per arm.

## Disk

- **Before the rebuild:** free disk must be ≥ 66 GB. It was 74 GB on 2026-10-15.
- **The rebuild** writes 34.5 GB, leaving about 39.5 GB before arm B's readout, Mega-53's output
  and 0b's FLACs.
- **Checks after the rebuild:** the `meta.json` hashes are unchanged, and the row counts are 14,965
  (SW50R) and 14,998 (AC20), as in cprime-folds.
- **The guard:** renders stop writing below 31 GB, and 30 GB is kept free.
- **If free disk is below 66 GB before the rebuild:** ask the user. Nothing is deleted without
  approval, as on 2026-10-14.
- **When step 4 ends** (or the route stops), `input.npy` and `di.npy` are deleted again.

## Budget

Renders, all `isolate=True`:

| Item | Renders |
|---|---|
| 0b: D0, idempotence, swap rung | 108 |
| 0c: DAC ceiling check | 48 |
| Step 2: ≤ 3 arms × 4 cells × (~151 + 2 margin) | ≤ 1.85k |
| Step 2: 1z's noise control (if any arm reads go or undecided) | ≈ 0.61k |
| Step 4: 8 cells × (~151 + 2), bound kept at the research's 1.8k | ≤ 1.8k |
| Step 5: fresh 12-cell draw, both runs | ≈ 3.7k |
| Hedge S: reservation only (its own plan) | ≈ 3.0k |
| **Experiment 4, budgeted maximum** | **≈ 11.1k** |

- **The running total:** about 131k at the end of step 3 + the ladder's 0.92k + the separator
  screen's ≈ 0.14k + 11.1k ≈ **143.2k** of the 200k limit.
  - 131k is still an estimate while arm B's readout is pending.
  - The ledger's tally uses actual counts after each step.
- **The DI track:** about **12.2k**. Its ~12k figure was the project's own estimate, not a user
  limit; the user's limit is 200k in total.
- **What needs the user's yes first:**
  - the fold-1 branch: the per-arm fine-tunes (MPS) and ≤ 1.4k renders;
  - a fourth step-2 arm (≈ 0.6k);
  - a second hedge control (≈ 1.8k);
  - any E1′ renders;
  - a second seed for any arm;
  - anything that would pass 200k.

## Bookkeeping

**The code** goes on the ML branch and is reviewed before any run. With the defaults, C′'s
behaviour stays bit-identical.
- **`learn/direc.py`:**
  - **loss terms:** `short_mrstft` (via `mrstft(ffts=(32, 64, 128))`), `peakiness_loss`,
    `gap_guard`, and `phase_deriv_loss` (CPU, with a real-matrix STFT like `_real_stft`);
  - **`training_loss`:** takes the term weights; `kind="default"` is unchanged;
  - **`fit` flags:** `--terms` (e.g. `short=1,peak=0.1,gap=0.02,phase=1`), `--warmup`, `--adv`
    (MPD/MSD, balancer, warm start), `--fullrate-head`, and `--overfit N` (fixed crops, no
    augmentation, for 0e). All are off by default;
  - **`build_model(fullrate_head=...)`,** with `load_model` detecting the head's keys;
  - **`fine_metrics`:** crest at 0.5, 1, 5 and 10 ms, peakiness, gap level, waveform SNR and the
    3–8 kHz level. It is logged at each validation and used by 0e and 1d.
- **`learn/rebuilt_judge.py`:** `rebuilt_distance(..., lag=-LATENCY)`, so a call can pass `lag=0`.
  The default is unchanged.
- **`learn/song_settings.py`:**
  - `control_rebuild` and `control_search` take a network folder and an output folder. They default
    to `armA-control`, exactly as now.
  - Every new run writes to a per-arm folder, because outputs are skip-if-exists (amendment 4).
  - New runs do the rebuilt run only, reading the stored measure-DI run, filter by fold, and run
    the ±3-sample lag check and the margin renders.
  - The leak assertion checks the network's actual training pool (step 3).
  - `cprime_ready` requires a DONE marker for every `models-fs-*` network.
- **`learn/di_fine_structure.py`:** step 0's diagnostics (D0, idempotence, swap rung, gap spectra,
  the DAC check), the 0d calibration, the step-2, fold-1 and step-4 readouts with the rules above,
  and the render tally.
- **Tests:**
  - **Bit-identity:**
    - C′'s `training_loss` equals the old formula on fixed tensors.
    - The default `build_model` has the same keys and 9.8M parameters.
    - 3 CPU steps of `fit` on a tiny synthetic cache, **with a validation pass** (`log_every` ≤
      3), give the same weights hash as the pre-change commit. This runs with `resume=None` and
      with `resume=<ckpt>`.
    - `fine_metrics` doesn't consume `rng` or change the batch sequence.
    - With `--warmup 0` and no `--terms`, the learning-rate trajectory is identical.
  - **The new terms:**
    - each is zero at p = y, with finite gradients;
    - each moves the right way: peakiness on a smeared transient, and the gap guard silent when
      the prediction is quieter.
  - **The full-rate head** at init gives exactly C′'s output.
  - **The balancer's** shares.
  - **CPU against MPS** gradients per term at crop length (skipped without MPS, beside
    `test_direc_mps_gradient.py`).
  - **The rules** on synthetic numbers:
    - step 2: 3 of 4, −0.013, the stop row, and 1z's rule;
    - the fold-1 branch: 5 of 7, −0.048, +0.202;
    - step 4: 6 of 9, −0.0315.
  - **Output safety:** the stored `armA-control/*-result.json` hashes are unchanged after a new
    run, and step 4 reads fold 3's cells from the winning arm's folder.
  - **The leak assertion** against a synthetic training pool.

**The ledger entry** (`docs/dev-test-ledger.json`), entered before any experiment-4 compute:

```json
{
 "test_id": "di-fine-structure",
 "plan": "docs/di-fine-structure-plan.md",
 "entered": "2026-10-15, before any experiment-4 compute",
 "repeat_use": "third development use of song-settings' 12 known-target control cells (first: step 3's control and its audit; second: rank-margin-ladder); later still for colour-me-red and just-don't-talk (also cprime-folds check 2, reused here as 1d's breakage guard on their set-3 stems, separator-upgrade, separator-screen). Touched by 0a gap spectra, 0b D0/idempotence/swap, 0c DAC, step 2 (fold 3; fold 1 on its branch) and step 4, all under this use. Nothing fitted on them; arms chosen on fold 3's 4 cells (7 of 9 with the fold-1 branch).",
 "parts": [
  "cambridge-Today's_The_Day-ElecGtr10",
  "cambridge-Prodigal-ElecGtr5",
  "cambridge-just-don-t-talk-elecgtr3",
  "telefunken-Blind_Spots-GTR",
  "cambridge-Passing_Ships-ElecGtr6",
  "cambridge-colour-me-red-elecgtr01"
 ],
 "bands": "Diesel13, Doom Flamingo, Eat The Feeder, Starnes And Shah, The Travelling Band, Timo And The Timezone (song_settings.control_cells); step 5 draws 6 of Adam Buckley, Atlantis Bound, Dom McLennon, Eggy, Magician's Nephew, Turbosauro, Wall Of Death, Zeno (random.Random(20261019)), entered as an amendment before its renders",
 "training": "fine-tunes of C' per K3 fold from models-cprime(-f{f}) into models-fs-<arm>-f{f}; fold 3 first; cprime-folds' fold-leak rules and preflight counts; leak asserted against each network's actual training pool; seed 0; 5,150 steps, 200-step warm-up to 1e-4, cosine to 2e-5. Arms 1z (L_C' only, noise control), 1a, 1b, 1c, 1e (contingent). Loss weights by 0d's share rule, calibrated once on fold 3; 50-batch means and final weights recorded here before step 1a",
 "gate": "Full known-target control only (margin reported, never gating). Step 4 passes if >= 6 of 9 informative cells close >= 50% of the gap, or the informative-cell mean shortfall <= measure-DI run's + 0.03 = -0.0315 (one-sided); the 5 non-fold-3 cells reported apart. Step 2 (fold 3, 4 cells, stricter than the readout's <6-cell mode): go if >= 3 of 4 close >= 50% or mean shortfall <= -0.013; stop if <= 2 of 4 and mean > +0.171; else undecided. At most 3 arms rendered (1a, 1b, better of 1c/1e by 1d's 1-ms crest). If any arm reads go or undecided, 1z is rendered at lag 0; if 1z meets go, gains are attributed to fine-tuning; an arm beats 1z only with more cells closed or a mean shortfall >= 0.03 lower; tie-break 1z, 1a, 1b, 1e, 1c. Any go wins; only undecided arms (no go) take the fold-1 branch (user's yes; per-arm fold-1 fine-tunes): 7 cells, go if >= 5 of 7 or mean <= -0.048, stop if <= 4 of 7 and mean > +0.202, else undecided and ask. Step 5: the control's own rule with amendment 2 on a fresh 12-cell draw, band-weighted with leave-one-band-out; row 1 there -> undecided, ask the user; only a pass re-runs arm A. 1d hard stops are breakage guards only (val ratio > C' + 0.02, check 2 < 0.1126, 3-8 kHz > C' + 2 dB); crest and gap reported and used only to rank. 0c opens E1' (for experiment 4 only) if DAC-9 keeps m > 0 on 4 of 4 fold-3 cells, fold-3 mean m >= 0.75 x the true DI's (0c's own scoring), 1-ms crest within 1 dB.",
 "renders": "budgeted max ~11.1k (0b 108, 0c 48, step 2 <= 1.85k, 1z ~0.61k, step 4 <= 1.8k, step 5 ~3.7k, hedge S reservation ~3.0k, its own plan); DI track ~12.2k; running total ~143.2k of 200k (131k still an estimate). User's yes needed for the fold-1 branch, a fourth arm, a hedge control beyond the reservation, E1' renders, second seeds, and anything past 200k",
 "tally": [],
 "outcome": null
}
```

## Stated limits

- **Few cells:** 9 informative cells from 5 DIs and 6 bands, used for the third time. Fold 3 is 4
  cells from 2 parts.
- **One seed per arm.** 1z bounds the fine-tuning noise, but seed noise isn't separated.
- **One amp family** (Morgan), and clean renders, not stems. A pass here is necessary for arm A,
  not sufficient.
- **C′'s fold-3 baseline** was searched with the −52 objective, and the arms with lag 0. 1z, at
  lag 0, is the like-for-like comparator.
- **The arm is chosen on fold 3's cells** (and fold 1's on the branch), which the step-4 gate also
  contains. Step 5 is the guard.
- **The 1d screen** uses validation pairs from C′'s own training domain. It catches breakage only.
- **0e shows memorisation capacity,** not learnability.
- **Fine-tunes may stay in C′'s basin.** A from-scratch run is declared only if every fine-tune
  stalls at C′'s solution, in its own amendment.
- **The phase-scramble rung was read while drafting** (the report is not blinded). It only orders
  the arms.
