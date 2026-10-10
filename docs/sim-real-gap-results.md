# Does the network rebuild real amps worse than plugin renders? Results

Run 2026-10-10 as declared in [sim-real-gap-plan.md](sim-real-gap-plan.md) (plan
committed 10:35:46; outputs written 10:36:30). An independent reviewer re-ran all 99
plugin-side rebuilds and five real-side rebuilds, re-derived every number, and added
ceiling and floor checks (`tmp/sim-real-review.md`, local).

**Outcome under the declared rule: real-world recording is not the lever.** The plan's
"otherwise" branch follows: the network and its loss are the limit, even on plugin
renders.

## Numbers

Medians over 33 parts × 3 amps; each rebuild is compared with the measure DI.

| | 80–1,000 Hz coherence | 1–3 kHz coherence | 3–8 kHz coherence | log-spectral distance |
|---|---|---|---|---|
| rebuilt from the plugin render (sim) | 0.517 | 0.196 | 0.012 | 3.74 dB |
| rebuilt from the real amp track (real) | 0.420 | 0.108 | 0.004 | 3.86 dB |
| sim better in | 90 of 99 | 94 of 99 | 86 of 99 | 66 of 99 |

The rule needed three things:
- **1–3 kHz coherence at least 0.1 higher:** it is 0.089, or 0.079 paired. Fails.
- **Spectral distance at least 1 dB lower:** it is 0.17 dB. Fails.
- **Two-thirds wins on both:** met, the spectral one only just.

At part level the outcome is the same, because the real side is one rebuild per part:
coherence +0.098 (33 of 33 wins), spectral distance −0.20 dB (23 of 33).

## Ceiling and floor: the network loses information

Medians against the true DI (reviewer's checks):
- **Ceiling:** a delayed copy of the DI scores 1.00 in every band. Re-equalising it
  costs nothing (0.98–1.00).
- **The inputs themselves, 1–3 kHz:** the plugin render scores 0.24 and the real amp
  track 0.12.
- **The rebuilds:** 0.196 and 0.108.

**So the rebuild is less coherent with the true DI than the distorted input it came
from**, in 96 of 99 plugin cases and 93 of 99 real ones. Above 3 kHz it never improves
on its input. The sim-versus-real difference is inherited from the inputs: the gap is
0.078 before the network and 0.079 after, correlating r = 0.82 across cases.
Real rooms and mics are not what the network fails on.

## What it means

- **The network does not invert the amp.** It produces a DI with a plausible spectrum
  whose waveform detail has drifted from the input's. Its loss is mostly multi-resolution
  spectral magnitude (100·L1 is the only waveform term), which does not reward keeping
  phase.
- **The phase matters.** A driven amp responds to the waveform, not only to its spectrum,
  so a DI with the right spectrum and the wrong waveform distorts differently. This
  fits the gap split: the loss is in "the rest", and matching the long-term spectrum
  hurt.
- **Next lever: the training target and loss.** For example:
  - a stronger waveform term (larger L1, or SI-SDR), or a complex-spectrum loss;
  - checking that a rebuild is at least as coherent with the DI as its input is;
  - stem-aware training stays a candidate.

  Room and mic augmentation is not supported by this result.
