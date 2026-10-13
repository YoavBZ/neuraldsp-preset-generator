# EG-VAE-lite E1: the codes-to-codes mapper — failed pre-check 1 (2026-10-13)

Run under the [plan](egvae-lite-plan.md), E1 section and amendments. Development data only.
An independent adversarial audit checked the failure before this report
(`tmp/egvae-e1-audit.md`, local; numbers in `egvae-e1-floors.json` and
`egvae-e1-code-stability.json`).

## In short

- **E1 failed pre-check 1, and the failure is real, not a bug.** As declared, nothing was
  rendered or scored.
- **The cause is the design:** predicting DAC's exact codes. DAC's codes are locked to the
  waveform's timing, below a millisecond, and the amp scrambles that timing. So no network can
  guess the DI's exact codes from the recording.
- **The DAC route itself isn't refuted.** The codec loses little (E0, and the floor below). What
  failed is asking for exact codes instead of a sound that is close.

## Numbers

**Pre-check 1:** the mean mel distance to the true DI on C′'s 96 validation clips. Lower is
better.

| what is compared with the true DI | mean mel |
|---|---|
| true DI through DAC, 9 codebooks | 0.90 |
| true DI through DAC, 4 codebooks (the codec's floor) | 1.17 |
| **C′** | **2.29** |
| the recording, no rebuild at all | 3.10 |
| E1 at its final weights (reported only) | 3.23 |
| **E1 at its best checkpoint (the gate)** | **3.44** |
| a constant most-common code | 3.74 |

**Training:**
- It stopped early at step 14,000; the best was at step 9,000.
- Validation cross-entropy was 26.06, against 26.90 for always guessing the most common codes.
- The share of codes guessed exactly was 3.1% on codebook 1, and 0.8%, 0.5% and 0.5% on
  codebooks 2–4.
- Training loss kept falling (26.7 to 21.5): the network memorised and didn't generalise.

## What the audit checked

- **The data was paired correctly.** Twelve clips rebuilt from scratch reproduce the stored
  codes exactly, for both the recording and the DI, in all 9 codebooks. The pairs aren't
  shuffled, and the targets are the declared average-balance DI.
- **Time alignment:** the recording lags its DI by 37–123 samples at 48 kHz, under a quarter
  of a code frame.
- **The rest of the pipeline is correct:** shapes, codebooks, windowing and crossfade, sample
  rates and levels.
- **Code stability, on the true DI re-encoded with changes no one could hear:**

  | change | codes kept, codebook 1 | codebooks 2–4 |
  |---|---|---|
  | 1-sample delay | 83% | 64%, 52%, 47% |
  | 8-sample delay (0.18 ms) | 33% | 8%, 3%, 2% |
  | white noise at −40 dB | 35% | — |

  Many different code sequences decode to the same sound. Cross-entropy rewards only one
  exact sequence, so the mapper learns a spread-out guess, which decodes to junk.

## What follows

- **E1 is closed.**
- **The obvious repair** is to predict DAC's continuous latent and train through the frozen
  decoder with a timing-insensitive loss: a mel loss, computed on the CPU because of the MPS
  gradient bug. Plain L1 or L2 on the latent averages: the earlier review measured about 2.0–2.2
  for "halfway between recording and DI" and 2.6 for 9-frame smoothing. So that repair is
  marginal against C′'s 2.29.
- **It wasn't declared.** If tried, it needs its own plan ("E1′") with a cheap probe first. The
  declared next step is E2: the full content/tone model on DAC, with pitch and tone-class
  supervision and a C″ control. The plan allows E2 because E0 showed room.
