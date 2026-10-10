# Does the network rebuild real amps worse than plugin renders? Plan (set 3, development)

Declared 2026-10-10, before any computation below. No training, no new renders.

## Why

The DI network trained only on Morgan renders. It is tested on real amps, recorded
through real microphones in real rooms. Neither more data of the same kind nor
architecture repairs moved it ([v2](di-network-v2-results.md), [v3](di-network-v3-plan.md)).
If the real-world recording itself is what the network can't invert, the next lever is
real-world variation in training: room and microphone simulation, or real paired
recordings. If not, it is the network or its loss.

## Method

- **The plugin version of each performance.** For each of the 33 development parts and
  each amp, the stored Morgan render of the true measure DI through that amp's oracle
  preset (`phase2-set3/measure/<part>/<amp>/`, the lowest half-A distance, recording
  bands). This is the same performance, through the plugin preset that sounds closest
  to the record.
- **Rebuilds.** The current set-3 network (CPU) rebuilds the DI from:
  - the plugin render (sim);
  - the real amp track (real; the stored `phase2-set3/net` DI).
- **Comparison against the measure DI.** Each rebuild is aligned to it by
  cross-correlation within ±2,000 samples. Over the whole crop:
  - magnitude-squared coherence (Welch, 2,048 samples) averaged in 80–1,000 Hz,
    1–3 kHz and 3–8 kHz;
  - the log-spectral distance between 1/6-octave smoothed spectra (dB, 80 Hz–8 kHz).

## Reported

Per amp and pooled: medians and paired differences (sim − real), with wins and losses
over parts.

## Decision rule (declared)

**The sim-to-real gap is the lever** if, pooled over parts and amps, all three hold:
- the sim rebuild's median coherence in 1–3 kHz is at least 0.1 higher than the real
  rebuild's;
- its log-spectral distance is at least 1 dB lower;
- it wins on at least two thirds of part-amp cases for both measures.

**What follows:**
- **If it is the lever:** next comes real-world variation in training. That means room
  and mic augmentation (reverb, mic colouring, distance) on the render side. Its first
  check is that it closes this same gap on these parts.
- **Otherwise:** the network and its loss are the limit even on plugin renders. The next
  ideas are stem-aware training and a loss closer to the judge.

An independent reviewer re-derives the numbers before they route anything.
