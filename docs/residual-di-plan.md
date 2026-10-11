# A residual DI network: plan (development)

Declared 2026-10-11, before any residual network is trained. Reviewed
(`tmp/residual-di-plan-review.md`, local): approved with required changes, all folded in
("After review" below replaces the matching text above it).

## Why

The [audit](audit-2026-10-11.md) found that every DI network so far rebuilds a DI *less*
coherent with the true DI than the recording it was given.
- **Held-out clean parts, coherence with the true DI:**

  | band | the recording itself | every network |
  |---|---|---|
  | 1–3 kHz | 0.72 | 0.44–0.50 |
  | 3–8 kHz | 0.41 | about 0.02 |

- **So the detail is in the input, and the networks throw it away.**
- **All five past attempts shared a design with no pass-through path:** the output must be
  built entirely by the U-Net. A linear filter can't lower coherence, so a path that
  filters the input and adds a learned correction starts no worse than the recording.

This tests that one change, with everything else held equal to the network the chooser
uses today (`models-set3/fold2.pt`, "C").

## The model (R)

**`R(x) = FIR(x) + U(x)`.**
- **`FIR`:** one learned linear filter of the input, 2,049 taps centred (±21 ms, so it
  can learn the plugin's latency and the cab's inverse colour). It starts as the
  identity.
- **`U`:** the current U-Net with the normalised bottleneck (v3's `norm`, which keeps
  training finite on MPS). Its last layer is scaled by 0.01 at the start, so R begins as
  the input.

**Everything else is as C was trained:**
- the data (`cache` plus the SW50R and AC20 pair caches, K3 fold 2 left out);
- the loss (100·L1 + MR-STFT magnitude), the augmentation and the batch;
- the schedule: 60 minutes at 3e-4, then 300 minutes of cosine to 2e-5;
- the same seed, so the same validation clips.

**A linear-only control, L:** FIR alone, the same data, trained for 30 minutes. It shows
what a pure EQ of the recording gets.

## Pre-check (after R's first 60 minutes; stop if it fails)

R's 60-minute checkpoint against C's (`models-set3-1h`). R passes only if both hold:
1. **Validation loss** is at most C's 61.5 at the same point.
2. **Coherence with the true DI on real recordings:** the median over the 18 test parts
   below, at 1–3 kHz, is at least C's.
   - Also reported: the recording's own coherence, at 80 Hz–1 kHz, 1–3 kHz and 3–8 kHz.

**If it fails:** stop, and report.

## The test (development, after the full schedule)

**Parts:** the pinned development clean and crunch parts (`docs/sound-desc-test-parts.json`)
whose bands no fold-2 network trained on: set 3's (never in any training data) and K3
fold 2's.
- 18 parts in 8 bands: 12 crunch in 5 bands, 6 clean in 4 bands (Diesel13 has both).

**For R, C and L:**
- Rebuild each part's DI from its amp track, at −22.9 LUFS, uncut (no 3 kHz cut: the
  audit found it hurts on clean).
- Render it through all 111 menu presets, dry (`RULE_SET`).
- Judge with `rebuilt_distance` (reference-proxy fallback) on one half.
- Pick per amp, and score with the stored fixed-level measure on the other half.

**Gate (R against C, pooled clean and crunch).** Per part-amp cell, the log ratio of R's
pick to C's pick, averaged over both directions. A band-clustered 90% t-interval with 7
degrees of freedom.
- **Helps:** the interval lies below 0, and the band-weighted mean is negative.
- **Futile:** the lower bound is above −0.02.
- **Inconclusive:** anything else.

**Reported, all band-weighted and part-weighted:**
- each class alone;
- R, C and L against the leave-band-out fixed preset (as in
  [sound-desc](sound-desc-results.md));
- the oracle;
- the coherence table;
- per-band rows;
- the leave-one-band-out range;
- the band sign-flip p.

**If R helps,** it becomes the candidate network for the next declared held-out test,
once fresh clean and crunch sessions are sourced. It is not a product claim. These 18
parts are development and have been seen many times.

## Cost and safety

- **Caches:** the two pair caches are rebuilt from their stored renders (about 35 GB);
  disk stays above 30 GB free.
- **Training:**
  - R takes 6 hours on MPS, with the pre-check at hour 1;
  - L takes 30 minutes.
- **Renders:** 18 parts × 111 presets × 3 networks, about 6,000 Morgan renders in a reused
  instance.
- **No held-out data.**
- **An independent reviewer** checks this plan before training, and the result before
  it is reported.

## After review (2026-10-11, before any training)

1. **No confound with C.**
   - R drops the normalised bottleneck, as C was trained.
   - R uses C's interpreter (`demucs-venv`, torch 2.14), seed 0, and C's two-stage recipe.
   - **First, a 15-minute reproduction check:** current code, C's architecture, the same
     settings. It must give C's validation at steps 500 and 1,000 (64.84, 65.02) to within
     ±0.5. If it doesn't, stop.
2. **The same number of steps, not minutes.**
   - R's FIR slows each step, so R runs C's step counts: 5,150 at 3e-4, then 23,100 with
     cosine decay by step to 2e-5.
   - The FIR is 513 taps (±5 ms, enough for the 52-sample latency).
   - The FIR learns at a tenth of the rate.
   - Its impulse and magnitude response are logged.
3. **Pre-check bars, at R's step 5,150.** Measured on this set: the recording itself is at
   0.511 / 0.248 / 0.044 (80 Hz–1 kHz / 1–3 kHz / 3–8 kHz), and C at 0.424 / 0.150 / 0.011.
   - **Stop** if R's 1–3 kHz median coherence is below 0.20, or its validation loss at that
     step is above 62.0 (C's was 61.48, and C's own readings swing by about ±0.3).
   - **The mechanism counts as shown** only at 0.228 or more, near the recording's own.
   - **L must match the recording's coherence within 0.01.** Filtering can't change
     coherence, so this checks the pipeline.
   - Band-weighted medians are reported too.
4. **The gate is on the 8 band means:** a t-interval with 7 degrees of freedom.
   - **Helps:** the interval lies below 0, and more than half the bands are negative.
   - **Futile:** the lower bound is above −0.02.
   - **Inconclusive:** anything else.
   - The smallest detectable effect is reported; with a standard error near 0.03 it is about
     −0.057.
   - **Declared now:** if inconclusive, R is carried to the next held-out test only if its
     band mean against C is −0.03 or lower and its coherence passes. Otherwise the
     pass-through route is paused until fresh data, with this loss.
5. **Each network's misalignment is reported.** The judge reads every rebuilt DI as if
   aligned with the recording, so a network that learns a different advance would be a
   hidden confound.
6. **Facts:**
   - each pair cache is about 17 GB;
   - seed 0, the `demucs-venv` interpreter;
   - this set's coherence is as in item 3.
7. **Wording:** this is development, on 18 parts in 8 bands seen many times, and also
   used for the pre-check. The band-weighted reading comes first. It tests pass-through
   under the same magnitude-heavy loss only, so a null result does not rule out
   pass-through with a phase-aware loss.

## Amendment: the MPS gradient bug (2026-10-11, before any comparison run)

**The reproduction check failed,** and the cause is a bug that affects every DI network.
- **`torch.stft`'s gradient on MPS is wrong:** 34–100% off the CPU's at every FFT size,
  under torch 2.8 and 2.14.
- **The MPS matrix product on an unfolded, overlapping view is wrong too:** in the forward
  pass, and in the gradient even when made contiguous.
- **So every DI network trained on MPS** (all of them, C included) learned from a wrong
  spectral-loss gradient. Only the L1 term's gradient was right.
- **The original code still reproduces C** (64.94 at step 500, against 64.84). Current
  code with the NaN-safe magnitude diverges on MPS. Either way the spectral gradient is
  wrong.
- **The fix:** `mrstft` computes on the CPU when given MPS tensors, and the gradient flows
  back. The training-loss gradient on MPS now matches the CPU's to 0.04%, and a step takes
  about 0.62 s (C's took 0.69 s). A test guards it (`tests/test_direc_mps_gradient.py`,
  run where MPS exists).

**What this changes:**
- **The comparison with C is no longer fair:** C trained on broken gradients.
- **So two networks are trained with correct gradients, side by side on MPS,** each with
  C's recipe in steps (5,150 at 3e-4, then 23,100 with cosine decay to 2e-5), seed 0,
  `demucs-venv`, no normalised bottleneck:
  - **C′:** C's architecture;
  - **R:** the residual design (513-tap FIR at a tenth of the learning rate).
- **L** is unchanged (FIR alone, 30 minutes).

**The pre-check is now at step 5,150, R against C′.**
- **Stop** if R's 1–3 kHz coherence is below 0.20.
- **R's validation loss** must be at most C′'s at that step plus 0.5.
- **The mechanism counts as shown** at 0.228 or more.
- **C′ and C** are both reported (validation loss and coherence).

**Two gates,** each the band-mean rule from "After review" item 4:
1. **C′ against C:** does a correct gradient help the chooser?
2. **R against C′:** does pass-through help, given a correct gradient?

The declared consequences for an inconclusive result apply to each.

**The 2,049-tap timing and the "C's minutes" arguments are superseded:** the arms are
matched in steps.

### Corrections after the bug review (`tmp/mps-bug-review.md`, local)

- **The bug depends on signal length, not FFT size.** torch.stft's gradient on MPS is
  wrong for signals longer than 65,536 samples (81–100% off), and its forward is right.
  Training crops are 144,000 samples.
- **Unfold-then-matmul is right on MPS once made contiguous.** The "gradient still wrong"
  above did not reproduce.
- **`complex_stft_loss` is wrong on MPS even in the forward pass,** and is now routed to the
  CPU too.
- **The test** now uses the training crop length (at 48,000 samples it couldn't fail) and
  asserts finite gradients.
- **Which networks:** every DI network was trained on MPS except the SI-SDR loss pilot
  (CPU).
  - That pilot, with a correct gradient, reached the same 1–3 kHz coherence as
    MPS-trained C (0.170 against 0.169).
  - This is weak evidence that the bug isn't the main reason the networks lose
    coherence, so gate 1 (C′ against C) is a real question.
- **L runs by steps (2,000),** not minutes, so CPU contention can't shorten it.
- **One seed per arm.** If a gate lands near the −0.03 carry-forward rule, a second C′
  seed calibrates run-to-run noise before anything is carried forward.
- **Earlier DI-network conclusions are flagged,** in the roadmap and the audit, as trained
  with a corrupted spectral gradient: the confirmation, the clean and crunch checks, v2,
  v3 and the 3 kHz cut. Their measured numbers stand as measurements of those networks.
