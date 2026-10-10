# A DI-rebuilding loss that keeps the waveform: plan (set 3, development)

Declared 2026-10-10, before any training with it.

## Why

- **The rebuild loses waveform coherence its input had.** The
  [sim-to-real check](sim-real-gap-results.md) found that the rebuilt DI is less
  coherent with the true DI than the distorted input it came from. On held-out-fold
  training pairs (`learn/coherence_check.py`, 96 clips):
  - the input scores 0.300 at 1–3 kHz;
  - the set-3 network after 6 h, 0.177;
  - the same network after 1 h, 0.169.
- **The cause is the loss.** It is 100·L1 plus a multi-resolution STFT *magnitude* loss,
  which lets phase drift while the spectrum looks right.
- **The drift matters.** A driven amp responds to the waveform. Its invented detail
  drives presets dirtier, so picks come out under-driven.

## The change

`--loss phase` (`learn/direc.training_loss`) adds two terms to the default loss:
- **A compressed complex-STFT L1:** magnitude^0.3 with the original phase, at 512, 1,024
  and 2,048 samples, weight 10.
- **Negative SI-SDR:** weight 0.5.

The weights were set so each term is about 2 of the ~8 total, measured on the current
network. Everything else is the set-3 recipe: the PR12 cache plus the SW50R and AC20
pairs, K3 fold 2 held out, and the K3 fold-2 average-balance target.

## Pre-check: 60 minutes from scratch on MPS, learning rate 3e-4, seed 20261010

It is compared with `models-set3-1h`, the same recipe with the default loss, also
60 minutes. It passes if both hold:
- **Waveform:** the mean coherence at 1–3 kHz on the 96 clips is at least 0.22, which
  is 0.05 above the old network's 0.169;
- **The default loss:** its validation figure at 60 minutes is at most 63 (the old run
  ended at 61.5), so the spectrum isn't traded away.

If it fails, stop and report; no long run.

## Long run and test (only after a pass)

- **Training:** 60 minutes at 3e-4, then 300 minutes on a cosine decay to 2e-5.
- **Test:** the 33 development parts. The new rebuilt DIs go through the adopted 3 kHz
  cut, and are scored under the fixed-level protocol (`learn/rescore.py`) against the
  current cut chooser (`lp3k`).
- **Decision rule** (smallest effect worth having: 0.05):
  - **Helps:** the 90% interval lies below 0. Then it replaces the current network.
  - **Futile:** the lower bound is above −0.05.
  - **Inconclusive:** anything else. The current network stays, and the new one is kept
    as a candidate.

The gain-knob bias and coherence are reported beside the result. An independent reviewer
re-derives the numbers.

## Amendment (2026-10-10, before any pre-check result)

**The first pre-check launch stopped at step 31 with non-finite gradients.** Complex
`abs` has an undefined gradient at 0, which silent stretches reach.

The complex term now takes the magnitude from the real and imaginary parts with a
1e-10 floor, and SI-SDR is clamped to ±50 dB. Gradients were verified finite on CPU, for
noise, half-silent and silent targets. The loss is otherwise unchanged, and the
pre-check restarts from scratch under the same rules.

**Second launch** (also before any result): non-finite again at step 231 on MPS. The
compression's gradient, magnitude^−1.7, overflows near a 1e-5 floor. The floor is now
1e-2 in magnitude, about 40 dB under typical bins. On CPU, gradient norms are 1.4–1.9
times the default loss's, on both a fresh and a trained network. The pre-check restarts
from scratch again.
