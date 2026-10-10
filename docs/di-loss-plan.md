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

**Third amendment** (still before any pre-check result).

**The complex-STFT term can't train on MPS.** It produced non-finite gradients after one
update in every form tried:
- compressed, uncompressed, without the DC and Nyquist bins;
- rebuilt from real cosine and sine projections.

Some forms also failed MPS command buffers. All were finite on CPU.

**A side finding: the default loss's MR-STFT term had the same weakness.** Complex `abs`
has a NaN gradient at 0. It now uses `_magnitude` (values unchanged to ~1e-6), and the
default loss ran 150 MPS steps with no non-finite gradient. This is the likely cause of
the "MPS non-finite gradient" episodes since 2026-10-06.

**SI-SDR alone diverged with the original architecture.** The loss reached 2e8: the
unnormalised bottleneck, which the default loss had shut off, blew up. With the
normalised bottleneck (`--norm`, from the [v3 plan](di-network-v3-plan.md)) it was stable,
with 1 non-finite step in 200.

**The pre-check arm is therefore `--loss sisdr --norm`:** the default loss plus 0.5 ×
negative SI-SDR, with the normalised bottleneck. That is two changes against the
baseline, reported as one arm. The pre-check rules are unchanged: 1–3 kHz coherence of at
least 0.22, and a default-loss validation figure of at most 63 at 60 minutes.

**Fourth amendment** (before any pre-check result): `--loss sisdr --norm` also gave
non-finite gradients on MPS in real training. They began at step 0 in `enc.0`, and the
loss diverged by step 111. On CPU it trains cleanly at 0.84 it/s, against about 1.4 on
MPS.
- **The pre-check therefore runs on CPU** (`DIREC_DEVICE=cpu`) for 100 minutes. That is
  about 5,000 steps, the number `models-set3-1h` took in its 60 minutes, so the
  comparison is at equal steps rather than equal time.
- **The pass rules are unchanged.**
- **A long run, if any,** also uses CPU, with its minutes scaled to match the original's
  steps.

## Pre-check result (2026-10-10): fails; no long run

`--loss sisdr --norm` on CPU, 5,000 steps in 95 minutes, with no non-finite step. Against
`models-set3-1h` (same recipe, default loss, about 5,000 steps), on 96 held-out-fold
pairs:

| | coherence 80–1,000 Hz | 1–3 kHz | 3–8 kHz | validation (default loss) |
|---|---|---|---|---|
| the input itself | 0.577 | 0.300 | 0.166 | 111.8 |
| default loss (1 h) | 0.543 | 0.169 | 0.026 | 61.5 |
| **SI-SDR + normalised bottleneck** | 0.560 | **0.170** | 0.015 | **77.1** |

Both conditions fail. Coherence is 0.170, under the 0.22 bar. Validation is 77.1, over
the 63 bar.

**Rewarding the waveform directly didn't make the network keep it,** and the spectrum
got worse. Above 1 kHz the network keeps less of the true waveform than its own input
does, under either loss. Heavy distortion appears to leave too little to rebuild that
detail at this scale. The roadmap's remaining step-4 ideas (stem-aware training, room
and mic augmentation) don't address this. The next lever is to make the preset choice
robust to the detail the rebuild can't recover, rather than to rebuild it.
