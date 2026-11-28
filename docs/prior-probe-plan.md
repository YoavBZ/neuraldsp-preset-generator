# The LOUDAR prior timing probe (`phase_scratch_prior_probe`)

Declared 2026-11-28 on the user's route call ("Spectral steps first (Recommended)" plus the LOUDAR MPS timing probe
in parallel), after an independent review of the planner's plan (Opus, high): PASS WITH AMENDMENTS. B's amendments 1
to 6 are binding and override the plan where they differ; the non-binding notes are taken. Code
`learn/prior_probe.py`, tests `tests/test_prior_probe.py`, ledger `preset-ladder` `phase_scratch_prior_probe`, later
`phase_scratch_prior_probe_outcome`. Zero renders. No model is ever written. Not run.

## Goal

Price route 3's fine-tune of LOUDAR's DI prior on this Mac. The probe measures steps per second on MPS at the real
segment length, the memory used, and whether MPS gradients can be trusted on LOUDAR's training path. It also totals
the trusted DI hours per source, which the fine-tune's declaration needs. One code, then stop. 200 steps say nothing
about whether a fine-tune helps. The fine-tune needs its own declaration and go.

## Design

### What runs (amendment 1)

- **LOUDAR's own code.** `Trainer.train_step` and `Trainer.update_ema` run unbound on a stub object. The stub holds
  exactly the attributes they read: `args`, `network`, `diff_params`, `optimizer`, `ema`, `it`, `dset`, `device`, and
  `get_batch` bound from `Trainer.get_batch`.
  - The optimizer and EMA are built as `Trainer.__init__` builds them.
  - The order is `training_loop`'s: `train_step`, `update_ema`, `it += 1`.
  - `logging.log` and `log_spectrograms` are False.
  - No LOUDAR file is edited.
- **Two placeholder modules.** `training/trainer.py` imports `utils.log` (pandas, plotly) and `utils.training_utils`
  (torchaudio). Neither library is in the venv, and nothing is downloaded. The steps never use either module with a
  plain tensor batch, so both are placeholders during the import only, and a placeholder raises on any use.
- **The training config.**
  - The defaults of `config_train_GuitarFx.yaml`: network `dit_M2L`, `diff_params` `FM_m2l`, exp `GuitarFx`.
  - `diff_params` is class FM. It is not the tester's `FM_to_EDM_wrapper`, which overrides `sample_prior` (equal at
    t=None).
  - AdamW lr 1e-4, weight decay 0.01, betas 0.9/0.999, eps 1e-8; batch 2; 526,080 samples (10.96 s); clip max_norm 1;
    EMA 0.9999, ramp-up 10,000.
  - No augmentation: `train_step` never calls it, and `randomize_segment_length` is False.
  - `config_refusal` checks every value the probe relies on.
- **The EMA branch.** Timed steps start at `it = 0`, as `training_loop` sets it. All 200 are on the ramp-up branch (it x
  batch < 10,000). The EMA check covers both branches (it 1 and 175,000).
- **Pins.** The sha256 of 12 LOUDAR files at `loudar_run.LOUDAR_COMMIT` and of 11 functions' source text: `train_step`,
  `update_ema`, `get_batch`, `FM.loss_fn`, `prepare_train_preconditioning`, `sample_time_training`, `sample_prior`, both
  `transform_fwd`s, and the two RMS functions. The running function must come from the pinned file and line. A pin that
  fails is PP-anomaly, found before anything of LOUDAR's runs.
- **Observers only.**
  - The FM instance's `loss_fn`, `sample_time_training` and `sample_prior` are wrapped on the instance. Each calls the
    class's own method and keeps a copy of what it returns.
  - `torch.nn.utils.clip_grad_norm_` is wrapped for the run. It keeps the gradients before and after and the returned
    norm, and it applies a declared fallback when one is in use.
  - No value changes.
- **Environment.**
  - `tools/loudar-venv`: Python 3.12.13, torch 2.10.0 and omegaconf 2.3.1 at their pins.
  - `loudar_run.set_env`: offline, wandb disabled, no `torch.compile`, weights-only loads.
  - `PYTORCH_ENABLE_MPS_FALLBACK` must be unset, or the command refuses. An unsupported op is reported, not hidden.
  - 4 CPU threads. No `.pyc` is written into LOUDAR's tree.
- **Weights.**
  - `GuitarFx-175000.pt` loads through `loudar_run.load_checkpoint`: safe load, EMA weights only. Its size and sha256
    are checked before torch is imported.
  - The network starts on the CPU in training mode, as hydra builds it, and is copied to each device.
  - The optimizer starts fresh.

### The segments (`prep`)

- **What they are.** 16 GOAT DI segments of 526,080 samples at 48 kHz, cycled two a step. They are float32 `.npy`
  files under `PF/fs/prior-probe/segments/`, about 34 MB.
- **The rule** (`segment_rule`, seed 20264001).
  - The GOAT items outside the fs draw (its 24 GOAT items), never `item_5`.
  - Each item needs 5C's screened window and must not be near full scale.
  - Take a seeded order, then the first 16 whose window start plus 10.96 s lies inside the item.
  - Each segment starts at its item's window.
  - No Cambridge or MedleyDB file, so BKS and the panel's bands are out.
- **The rate.** GOAT is 44.1 kHz, so `prep` resamples to 48 kHz (`clean_di.resample`) before cutting.
- **The level.** `check` and `time` RMS-normalise each segment to -18 dB with LOUDAR's own
  `apply_RMS_normalization(use_gate=True)`, as `GuitarFxIterable` does. LOUDAR normalises at the file's rate and
  resamples in `get_batch`, so the gain differs negligibly.
- **The record.** `prep.json` holds each file's and its samples' sha256, the zip member's sha256 and each item's
  12-hex tag.

### The gradient check (`check`, CPU at 4 threads and MPS; amendment 2)

One fixed batch (segments 0 and 1) and one seed for t and the noise. LOUDAR's code draws both on the CPU, so the
devices get the same draws. This is checked; if the draws differ, the probe stops.

| Check | Compared | Tolerance (relative) |
|---|---|---|
| Encoder forward | MPS latents against the CPU's; this check alone judges the encoder | 1e-3, L2 |
| Run 1: the network alone, shared CPU latents | Loss | 1e-4 |
| | Every gradient before the clip, per tensor and globally | 1e-3, L2; worst tensor reported |
| | `clip_grad_norm_`: returned norm, non-finite count, gradients after | 1e-3; none non-finite; whether it scaled |
| Run 2: end to end | The MPS step with the chosen encoder, against the CPU network fed that MPS run's own latents; the same figures | The same |
| AdamW's step, from identical gradients and weights | Per tensor and globally | 1e-3 |
| The EMA update, at it 1 and 175,000 | Per tensor and globally | 1e-3 |
| Five steps on each device | Loss sequence, clip norms, weight change | Reported; the CPU rate from steps 2 to 5 |

- **Per tensor.** A tensor's error is its L2 difference over its own norm. The norm is floored at 1% of the RMS tensor
  norm, so near-zero tensors don't read as broken.
- **Calibration.** A figure that misses its tolerance passes only if its error against a CPU float64 reference is
  within 3 times CPU float32's own error against that reference.
  - The reference runs LOUDAR's `FM.loss_fn` on a float64 copy of the network, with the same t and noise and the
    run's shared latents (run 2's are the MPS run's own).
  - The rotary frequency buffer stays float32. LOUDAR computes rotary angles in float32 and rounds q and k to float32
    around the rotary step, so the reference carries float32 rounding there and float64 elsewhere.
  - If the reference cannot run, nothing is calibrated.
  - **The gate** (the review of #666, fix 2). A calibrated pass is allowed only when the reference itself holds: CPU
    float32 against float64 within the direct tolerances on both the loss (1e-4) and the global gradient (1e-3), and
    the same draws on both devices. No tensor is calibrated whose CPU error against float64 is above 0.1. AdamW, the
    EMA and the encoder are gated the same way on their own CPU-against-float64 error. Otherwise only the direct
    checks apply, and each row records why.
- **Why these tolerances.** The known MPS fault was 81-100% off. The tolerances catch a broken op and decide no route.
- **Fallbacks,** each checked the same way.
  - The clip: `foreach=False` first, then the clip norm computed on the CPU (torch's own rule applied to the device's
    gradients).
  - The encoder: on the CPU, with the latents moved to MPS, only when the encoder's own latent check fails. A run-2
    miss never switches the encoder; it is PP-cpu-only (the review of #666, fix 1).
  - An unsupported op in the encoder or the clip tries its fallback.
  - An unsupported op anywhere else, or MPS out of memory, is PP-cpu-only with the op or the memory named.
  - Any other error stops the probe, and goes to the orchestrator.
- **When it refuses.** `check` refuses while another torch or MPS process runs, and beside renders (it competes for
  the CPU's performance cores).

### The timing (`time`, MPS)

- **The configuration.** `time` runs the configuration the check passed, fallbacks included. It refuses after an
  anomaly or a cpu-only check.
- **The long block.** 200 steps at 526,080 samples, with `torch.mps.synchronize()` before each clock read.
  - Steps 1-20 are warm-up, reported apart. Steps 21-200 give the rate.
  - The rate excludes LOUDAR's in-step resample (`get_batch`'s `resample_batch`, which GOAT's 44.1-kHz files take in
    LOUDAR's own training), which is right for 48 kHz data.
  - The data are on the device before the clock. The non-finite and memory checks run outside it.
- **The encode split.** An encode-only block (50 encodes, 5 warm-up) after each timed block gives the encode/network
  split. It never comes from a sync inside the step.
- **Beside.** 100 steps (20 warm-up) at 218,624 samples, our 216,000-sample clip padded as LOUDAR pads it. The
  fine-tune may choose this length, and its latents could be cached.
- **A non-finite step** is one whose loss, `clip_grad_norm_`'s returned norm, or any parameter at its end is not
  finite.
- **The report.**
  - Steps per second.
  - Seconds and hours per 1,000 steps and for 175,000, the released checkpoint's count. No target count is chosen here.
  - Audio per 1,000 steps: 6.09 h.
  - Peak RSS and MPS driver memory, against the Mac's memory.
  - Non-finite steps.
  - The hours.

### Idle (amendment 6)

- **The rule.** A block is idle when, at its start and its end, no render process runs (`pgrep -f au_render_server`)
  and no other torch or MPS process runs (`pgrep -f` on the tools' venvs and the fit, train and curve commands). The
  probe's own process and its parents are left out, and the counts are recorded.
- **Never two MPS jobs.** `check` and `time` refuse while another torch or MPS process runs.
- **Beside renders.** `time` may run beside the envelope floors: one MPS job beside 3 renders was measured as fine. A
  block that was not idle at both ends is labelled. The quoted rate comes only from an idle 526,080-sample block of
  200 steps, so `read` refuses until one exists. The repeat is a rerun of `time`; each run writes its own
  `time-<stamp>.json`.

### The codes (amendment 3)

`pp_code`: the first that holds, in this order; one code, then stop.

| Code | When |
|---|---|
| PP-anomaly | A pin or hash fails, a file outside the list is read, or a weights file is written |
| PP-cpu-only | MPS gradients do not match even with the declared fallbacks; an unsupported op outside the encoder and the clip; MPS out of memory (the op or the memory named). The CPU rate is quoted from steps 2 to 5 of the five |
| PP-unstable | The checks hold but a non-finite step appears (the five MPS steps or any timed step) |
| PP-mps-fallback | The checks hold only with a declared fallback; the fine-tune must use it |
| PP-mps | Every check holds on LOUDAR's own path, and 200 finite steps |

- **The file rule.** An `open` audit hook runs in `check` and `time`.
  - A data read outside the list is PP-anomaly. The list is LOUDAR's code, the models' cache, the venv, the repo and
    the probe's folder. A data read is one under the data root, or of an audio or array file anywhere under the home
    directory.
  - So is any write under the home directory outside the probe's folder, and any weights-like file opened for writing.
  - `torch.save` raises.
  - The probe's folder holds only JSON and `prep`'s 16 segments; `check`, `time` and `read` check it.

### The hours (`hours`, zero renders; amendment 4)

A count only, from stored inventories. The fine-tune declares its own set.

- **The clean-DI library.** The manifest's sections that are training_ok, clean, disjoint and split library. These
  passed its screens: hum, hiss, bleed, drop-outs and clipping. They are counted by source and set. Each excluded
  section counts under the first of these reasons:
  1. `untrusted` (fails the rule above);
  2. Silent Waves and Drowning;
  3. the held bands (`capture_labels.HELD_BANDS`: V-real, NS, the panel, BKS, the reserve; `window_count.held_reasons`
     names which);
  4. `clean_di.refuse_held_out` (sets 1 to 6's declared held-out material, Guitar-TECHS P3);
  5. the reserve's stage-F DIs;
  6. the DIs the user marked too low or metal-style (the DI-scope page's drops and batch 3's marks);
  7. the hum-audit superset;
  8. the fs draw's 47 sections.
- **EGDB.** Its DIs as stored (the manifest's seconds), unscreened here. It is LOUDAR's test set, so a fresh source.
- **EGFxSet.** Its clean single notes, by WAV header, unscreened here.
- **GOAT, apart.** The prior's own training data, never checked for scope. Each item's 5C-measured length, less, in
  order: `item_5`, the drawn items, 5C's items with no screened window, and its near-full-scale items. Tunings are
  listed.
- **Not counted.** MedleyDB (the panel's source), sets 4 to 6 (held out), the intakes outside the library manifest
  (no stored section screen), and Guitar-TECHS P3.
- **A dry run at declaration** (`hours --dry`, nothing written): library 0.889 h (320 sections), EGDB 1.791 h,
  EGFxSet 0.958 h, GOAT apart 4.262 h (117 items).

### Terms (amendment 5)

- LOUDAR's code: MIT.
- Its checkpoint is tagged MIT and was trained on GOAT (CC BY-NC, granted on request).
- The `m2l` autoencoder is linear-cae 0.1.4's (BernardoTorres/linear_consistency_autoencoders). It is Apache-2.0, as
  the codec manifest and the ledger's `phase_scratch_codec` record it: a retrained Music2Latent, not Music2Latent's CC
  BY-NC weights.
- Research use only. No model is kept, and nothing ships.

## Phases

| # | Phase | Where | Verify |
|---|---|---|---|
| 1 | Declare, one PR | — | `tests/test_prior_probe.py` and the ledger test pass; nothing run |
| 2 | `hours`, `prep` | main `.venv`, CPU | `hours.json`; `prep.json` with 16 segments, about 34 MB |
| 3 | `check` | loudar venv, CPU at 4 threads and MPS; not beside renders | `check.json` with a configuration, or PP-anomaly or PP-cpu-only |
| 4 | `time` | loudar venv, MPS | `time-<stamp>.json`; an idle long block of 200 steps |
| 5 | `read` | any | `outcome.json`; one PP code; hand-back, light audit, `phase_scratch_prior_probe_outcome` |

CPU step time is not measured here; the five CPU steps give it. LOUDAR's sampler ran 300 network steps a clip in 59 s
on the CPU.

## Commands

    $MAIN -m learn.prior_probe hours [--dry]
    $MAIN -m learn.prior_probe prep [--dry]
    $LV learn/prior_probe.py check --code ~/ndsp-presets/tools/loudar --models ~/ndsp-presets/tools/codec-models
    $LV learn/prior_probe.py time --steps 200
    $MAIN -m learn.prior_probe read

- Every command but the dry runs refuses unless this checkout's `learn/prior_probe.py` and `learn/loudar_run.py` and
  its `phase_scratch_prior_probe*` keys are main's.
- `--dry` computes in memory and writes nothing, so it can run before the merge.
- Launch `check` and `time` with `setopt no_bg_nice` and caffeinate, and record their PIDs.

## Dependencies and risks

- **Known MPS faults.** `clip_grad_norm_` gave NaN on torch 2.8 and 2.14; 2.10 is untested. Non-finite gradients have
  appeared after another GPU job ended. Never two MPS jobs at once.
- **The encoder.** `linear_cae`'s frontend frames with `unfold`, the known MPS fault class. It runs under `no_grad`, so
  the known `stft`-backward fault is off the path. The encoder check and its CPU fallback cover it.
- **The placeholders.** They stand in for two of LOUDAR's logging and IO modules. If a step ever touched one, it
  would raise, and the probe would stop.
- **A probe only.** The optimizer starts fresh, which does not affect timing. GOAT is the prior's own training data,
  which lowers the reported losses but changes neither the timing nor the MPS-against-CPU gradients.
- **No download.** Nothing is written but the segments and JSON.

## Done test

Main holds `phase_scratch_prior_probe_outcome` with:

- one PP code;
- the idle steps per second;
- the projections and memory;
- the gradient table;
- the hours.

No weights file exists under `PF/fs/prior-probe/`.
