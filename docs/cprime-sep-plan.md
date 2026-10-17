# Separator-robust C′: plan (2026-10-16)

Declared 2026-10-16 at night, before any training. An overnight MPS job for the bottleneck the
local-objective experiments found: the separated stem and the rebuild together. **Zero renders.**
The evaluation that needs renders is queued for later (below), not run tonight. Revised before
any training after an independent review (approved with two required changes, both made; see
[amendment 1](#amendment-1-2026-10-17-review-before-any-training)).

## Why

- **Experiment 1b** ([results](local-objective-results.md)): C′ rebuilt from the amp track and
  scored against it ranks nearby settings at 0.541, against today's 0.289 (C′ rebuilt from the
  htdemucs stem, scored against the stem): **+0.252 [0.139, 0.365]**. About half of that comes from
  *rebuilding from a clean guitar*, half from scoring against one.
- **C′ never trained on anything like a real stem.** Its inputs are clean plugin renders with
  backing bleed at −12 to −30 dB on half the clips. Measured tonight (zero renders, the
  library below): in a real stem, what is not the part's own guitar is **at about the guitar's
  own level** (median +0.1 dB; htdemucs about +0.4 to +1.9 dB on the multi-guitar Telefunken
  parts, BS-Roformer about −5 to −12 dB). Most of it is other guitars, which every guitar stem
  keeps.
- So a rebuild trained on stem-like inputs could recover part of the "rebuild from a clean
  guitar" half of 1b's gain, with any separator, including the one experiment 1c is testing.
- **Why this and not something else tonight:**
  - the CPU is full (renders, the 1c separation), so the job must be GPU-only with no renders and
    no separation;
  - arm B's sound-space training needs about 18k renders first;
  - the fine-structure fine-tunes didn't change steering, so more of the same loss isn't the lever;
  - the data for this exists: 20 usable sets 1–2 parts with both their amp track and four real
    stems (htdemucs_6s and BS-Roformer-SW, each from the full mix and from the instrumental).

## The residual library (built, zero renders; `learn/direc_sep.py lib`)

- **Per part and stem:** the least-squares transfer function G per STFT bin (stem ≈ G · amp
  track, 4096-point, hop 1024), and the residual r = stem − G · amp track.
- **Stored:** r (10 s), |G| smoothed over a third of an octave (dB, mean removed over
  100 Hz–8 kHz, clipped to −30…+10 dB), and the residual-to-guitar ratio rms(r) / rms(G · amp
  track).
- **80 entries:** 20 usable parts × 4 stems, in 10 K3 bands
  (`~/ndsp-presets/learn/direc-sep/lib.{npz,json}`, 154 MB).
  - Only sets 1–2 (the stem manifest's "usable" rule: SNR ≥ 1 dB).
  - **Set 3's stems are never used:** set 3 parts are evaluation parts for every fold.

## Training (MPS; `learn.direc fit --sep-lib`)

**Per K3 fold f (0, 1, 2, 3, in that order),** a fine-tune of that fold's final C′
(`models-cprime-f{f}`, fold 2: `models-cprime/fold2.pt`):
- **The augmentation:** with probability 0.75 a training clip gets one library entry's |G|
  (zero-phase) and a random 6-s window of its residual, at that entry's own
  residual-to-guitar ratio ±3 dB (uniform), *in place of* C′'s backing bleed. The other 25%
  keep C′'s own augmentation. C′'s tilt, bell and noise augmentation stays on every clip.
  - The entry is drawn band-first (a band, then one of its entries), so the six Dom McLennon
    parts don't dominate.
- **Leak rules:**
  - no entry comes from a band in fold f (asserted in `load_lib`);
  - inside the other folds' bands, whole bands are held out for the separator validation below:
    the smallest first (ties broken by `random.Random("cprime-sep|f")`), until they hold at least
    2 parts. So the large bands stay in training. Their residuals never train fold f's network.
  - **Per fold:**
    - fold 0: 12 training parts in 4 bands; validation Eat The Feeder and Zeno;
    - fold 1: 10 in 6; validation Adam Buckley and Starnes And Shah;
    - fold 2: 16 in 6; validation Starnes And Shah and Swatkins;
    - fold 3: 14 in 6; validation Swatkins and Zeno.
- **The recipe:** experiment 4's fine-tune schedule. Seed 0, batch 12, a 200-step warm-up to
  1e-4, cosine to 2e-5 over at most 5,150 steps. Loss on the CPU, as in C′. Hand clipping at 5.0
  and the non-finite recovery are unchanged.
- **The data, a dated deviation:** only the PR12 pair cache (18,843 rows) exists on disk. The
  SW50R and AC20 caches were deleted after the C′ folds. Rebuilding them needs 35 GB, which would
  break the 31 GB free-disk guard. So the fine-tune sees PR12 renders only. The control arm (below)
  shares this, so the contrast with it isolates the augmentation.
- **Validation at step 0 and every 250 steps, two curves:**
  - **clean (printed only, never selected on):** C′'s own measure on 96 fold-f validation crops
    (PR12), as `fit` prints it;
  - **separator (selects and stops):** 96 PR12 crops of the *held-out validation bands*, each
    with a fixed entry from its own band and a fixed window (a separate seeded generator), and its
    input-as-DI baseline. Those bands' rows and backings leave fold f's training.
- **The stopping rule (evidence-based):** stop when the separator validation hasn't improved by
  0.2% for 1,500 steps (after at least 1,500 steps), or at 5,150.
  - **The network kept** (`fold{f}.pt`, with `DONE`) is the best separator-validation checkpoint,
    step 0 (C′ itself) included; the last is kept as `fold{f}-last.pt`.
  - That choice uses only the held-out *training-fold* bands: their renders and their residuals. It
    never sees a fold-f band's data or any set 3 stem.
- **Outputs:** `~/ndsp-presets/learn/direc-sep/models-sep-f{f}/` with logs `fit-sep-f{f}.log`.

**The control arm (queued after; descriptive):** the same fine-tune with the augmentation off
(probability 0, C′'s bleed as before), same data, same validation and stopping rule, into
`models-ctl-f{f}`. It separates "trained on stem-like inputs" from "fine-tuned more on PR12".
It runs after the four main folds and the main evaluation, as GPU time allows. Folds that don't
finish are reported as missing.

## What is reported (zero renders; `learn/direc_sep.py eval`, `report`)

**The parts:** step 3's 24 parts (Honey out). Each is rebuilt by its own fold's network, folds as
in `docs/song-settings-folds.json`, exactly as step 3 and experiments 1–1c pick them. None of these
parts' bands is in its network's training data or its residual library.

**The inputs:**
- **htdemucs** (the product's stem today, step 3's `instrumental_guitar.wav`): primary;
- **BS-Roformer** (19 sets 1–2 parts): a second separator;
- **the amp track** (`reference.wav`): the clean-input check.

**The measures,** against the true DI (aligned as `cprime_folds check`):
- **coherence** in 80 Hz–1 kHz, 1–3 kHz and 3–8 kHz. 1–3 kHz is the declared network check's
  measure;
- **the spectral-envelope error (LSD):** the RMS over third-octave bands, 80 Hz–8 kHz, of the dB
  difference of the long-term spectra, mean offset removed. Coherence can't see a linear
  colouration, and half the augmentation trains exactly that.

**The contrasts (paired per part; band-weighted mean; 90% band-clustered t interval, bands − 1 df;
leave-one-band-out range):**
- **Primary (two):** separator-robust − C′ from the htdemucs stem, in 1–3 kHz coherence and in LSD.
- **Also:**
  - coherence on the mean of the three bands, and per band;
  - both without the high-bleed parts (the bleed audit's flags);
  - from BS-Roformer, and from the amp track;
  - **stem − amp track, in differences:** (sep − C′ on the stem) − (sep − C′ on the amp track).
    It is a partial internal control until the control arm lands. A gain as large on the amp track
    as on the stem would point to the extra PR12 fine-tune, not the augmentation;
  - per fold (fold 0's library is mostly Telefunken);
  - the share of C′'s own amp-track − stem gap that each primary closes;
  - the control's rows, and separator-robust − control, when it exists.
  - `report` asserts that every arm's rebuilds ran on the same device.
- **The curves:** both validation curves per fold, the step the rule stopped at, and
  input-as-DI baselines.

**Reading:** estimates, no bars. The 1b decomposition puts the reachable gain in local ranking at
up to about +0.12 (the "rebuild from a clean guitar" half). Coherence and LSD are proxies, and
better fine structure didn't steer better before (experiment 4). **A gain in either is a
pre-filter, not evidence for local ranking.** So the readout decides only whether the render test
below is worth running, not the product. Without the control, a gain isn't attributed to the
augmentation.

## The decision test, queued (needs renders; not tonight)

- **1b's matched design with the new rebuild:** rebuild each part's htdemucs stem with its fold's
  separator-robust network and render the frozen Σ (hash `ee91f710947dbb5c`).
  - 72 × 48 + 72 warm-ups = **3,528 renders.**
  - Score against the htdemucs stem at the native lag, as today's objective.
- **The primary contrast:** cross-half local Spearman, cell-paired against today's objective (0.289)
  and beside 1b's 0.541.
- Its own amendment to the local-objective plan before any render. It runs when render slots are
  free.

## Machine and guards

- **One process:** `~/ndsp-presets/tools/demucs-venv` (torch 2.14), MPS, with
  `OMP_NUM_THREADS=2` and `MKL_NUM_THREADS=2`. Launched with `setopt no_bg_nice`, `nohup` and
  `caffeinate -i`.
- **Measured in a 100-step smoke test (fold 3, beside the renders):**
  - 0.87 steps/s;
  - about one CPU core;
  - 3.3 GB resident, 4.4 GB peak footprint.
- **Expected time:** at most about 1.7 h per fold, 6.6 h for the four, then about 15 minutes of
  evaluation on MPS. The control is another about 6.6 h.
- **The start waits for experiment 1c.** 1c's separation refuses to run beside training, so this
  job starts only after `1c separate+rebuild done` appears in 1c's log. If it shows `FAILED`, the
  job exits.
- **Before each fold:**
  - free disk ≥ 31 GB (`df`);
  - system free memory ≥ 25% (`memory_pressure`);
  - no other `learn.* fit|train` process.

  Otherwise it waits, polling every 5 minutes.
- **Disk:** about 40 MB per network, plus logs. 59 GB free at launch.
- **No renders, no separation,** and nothing under `learn/local-objective/` or `ks-ceiling-extend/`
  is touched.

## Ledger

`docs/dev-test-ledger.json` gains `cprime-sep` before training:
- the library's 20 parts and 10 bands;
- per fold, the bands left out and the held-out validation bands;
- the 24 evaluation parts;
- zero renders.

It is a further development use of step 3's parts, read after experiments 1 and 1b. Any adoption
needs the render test, then a fresh draw.

## Limits

- **A small library:** 20 parts, 10 bands, two separators. Within a fold, 10–16 training parts.
  Fold 0's are mostly Telefunken (its four Cambridge bands are left out or held for validation).
  The network may learn these residuals rather than separator error in general. The held-out-band
  validation and the BS-Roformer row are the checks.
- **PR12 renders only** (above).
- One seed per fold.
- The residual is added, not produced by masking. Separator damage to the guitar itself enters only
  through |G| and the part of the residual that correlates with its own guitar.
- Coherence with the true DI is a proxy. The render test decides.

## Amendment 1 (2026-10-17, review, before any training)

An independent review approved the plan with two required changes. Both are made in code and
tested (`tests/test_direc_sep.py`, 35 passed with `tests/test_direc_fine.py`'s bit-identity
checks).

**1. Checkpoint selection no longer touches fold f.**
- **The problem:** the separator validation scored fold f's own validation renders (with held-out
  residuals). So the best-checkpoint choice and the stop selected on the DI clips of the evaluation
  bands, which C′ never did.
- **Now:** it scores 96 PR12 crops of the library's held-out validation bands, each paired with an
  entry from its own band.
  - Those bands' cache rows and backings leave fold f's training (`fit` asserts that no fold-f row
    is among them).
  - The clean fold-f validation is printed only.
- Step 0 (C′ itself) is validated too and can be the kept network.

**2. A spectral-envelope measure.**
- Coherence is blind to linear colouration, so `evaluate` also records LSD (above), and `report`
  gives every contrast in it.
- C′'s baseline rows were recomputed with it. Coherence reproduced exactly (largest difference 0).

**Also taken from the review's suggestions:**
- the stem − amp track difference in differences;
- per-fold rows;
- the device recorded and checked;
- a step-0 validation;
- same-band pairing in validation.

**Not taken tonight:**
- **A Mega-53 input row.** Its stems live under experiment 1c's folder, which this job must not
  touch. It is added when 1c is reported.

**Disclosed:** C′'s baseline evaluation rows were computed (and seen) at 23:56 and 00:05, before
any training. They are the existing network's numbers. Nothing in the recipe was changed after
seeing them.
