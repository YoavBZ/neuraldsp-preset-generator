# A correct gradient and a residual DI network: results (development)

Run 2026-10-11 under the [plan](residual-di-plan.md) and its amendments. An independent
review re-derived every number with its own code (`tmp/residual-di-result-review.md`,
local). These are development parts seen many times, with one seed per network: not a
held-out or product claim.

> **Update 2026-10-12: the second C′ seed did not confirm gate 1.** The correct-gradient
> gain is **unconfirmed**, and C′ is not carried forward (the declared rule; see "Second seed"
> below, adversarially audited in `tmp/seed2-audit.md`, local). Gate 2 is unaffected.

## In short

- **The bug:** `torch.stft`'s gradient on Apple's GPU is wrong for signals longer than
  65,536 samples, so every DI network had learned its spectral loss from a corrupted
  gradient. It is fixed (the loss runs on the CPU), and a test guards it.
- **Gate 1, a correct gradient (C′ against the old network C): helps, marginally.**
  - The band mean is −0.036 (90% −0.071 to −0.001), with 6 of 8 bands better.
  - All of it is on crunch (−0.070); clean is neutral (+0.007).
  - It passes the declared rule by 0.001, and it doesn't survive leaving out Eat The Feeder,
    Szymon Skiba or Wall Of Death.
  - Because it lands near the −0.03 rule, the plan requires a **second C′ seed**, which is
    training now.
- **Gate 2, passing the recording through (residual R against C′): futile.**
  - The band mean is +0.059 (90% −0.001 to +0.119), with 1 of 8 bands better.
  - It is robust: every leave-one-band-out lower bound stays above −0.02.
  - The harm is on crunch (+0.105, 0 of 5 bands better); clean is neutral.

## Numbers (band-weighted first; part-weighted in brackets)

| | all (8 bands) | clean (4) | crunch (5) |
|---|---|---|---|
| C′ against C | **−0.036** (−0.050) | +0.007 | −0.070 |
| R against C′ | **+0.059** (+0.072) | −0.007 | +0.105 |
| C′ against the fixed preset | −0.099 (−0.114) | −0.048 | −0.171 |
| C against the fixed preset | −0.063 (−0.065) | −0.055 | −0.101 |
| R against the fixed preset | −0.040 (−0.042) | −0.055 | −0.066 |
| L (linear only) against the fixed preset | +0.250 | +0.067 | +0.364 |
| oracle (true DI) against the fixed preset | −0.131 (−0.147) | −0.087 | −0.186 |

**On crunch, the corrected network gets −0.12 to −0.17 against the fixed preset over its
two seeds (seed 0 −0.171, seed 1 −0.124); the oracle gets −0.186.** Before the fix, C got
−0.101.

**Coherence with the true DI** (median over the 18 parts):

| | 80 Hz–1 kHz | 1–3 kHz | 3–8 kHz |
|---|---|---|---|
| the recording | 0.511 | 0.248 | 0.044 |
| R | 0.467 | 0.217 | 0.019 |
| C′ | 0.472 | 0.207 | 0.015 |
| C | 0.424 | 0.150 | 0.011 |

- **R's final coherence (0.217)** fell below the 0.228 "mechanism shown" bar it met at the
  pre-check (0.235).
- **Validation loss doesn't track pick quality:** C′'s rose from 60.2 to 62.3 during the
  decay, yet its picks are the best.

## Why pass-through hurt (the review's reading)

- **R's FIR stayed close to identity** (within ±3 dB; it learned at a tenth of the rate).
  So on crunch, R carries the recording's distortion and brightness into the rebuilt DI,
  and the U-Net learns to cancel most of it, but not all.
- **At 3–8 kHz against the true DI:**
  - R is +3.1 dB, C′ +0.6 dB and C −4.8 dB;
  - R is brighter than C′ on 11 of 12 crunch parts.
- **A brighter, partly distorted rebuilt DI** plausibly biases which preset wins. This is a
  hypothesis.
- **Coherence measures linear predictability, not spectral fidelity,** so it can rise while
  picks get worse. It should not stand in for chooser quality.
- **This rules out this design only:** an identity-start FIR at a low learning rate with a
  magnitude loss. It doesn't rule out pass-through in general.

## Audit

- **The order was right:** plans and amendments were committed before training and before
  any evaluation output, and the pre-check ran as declared.
- **Same presets and level for every network:** the same 111 presets throughout, no judge
  refusals, and every rebuilt DI at exactly −22.90 LUFS.
- **Alignment:** each network sits within 0.1 ms of the others.
- **The reference-proxy fallback** fired only for C and L, on one part's half A. Dropping
  that part leaves both gates unchanged.
- **Gate 1 changes more than the gradient:** C′ also uses the newer training code and the
  rebuilt caches.

## Second seed (2026-10-12)

**The rule,** declared before the result: C′ is carried forward only if seed 1 also passes
gate 1 against C.

**The result:**
- **Seed 1 against C:** −0.020 (90% −0.054 to +0.013), with 4 of 8 bands better. Every
  leave-one-band-out version is also inconclusive.
- **So the correct-gradient gain is unconfirmed,** and C′ is not carried forward.
- **Seed 1 against seed 0:** +0.016, about the gate's own standard error (0.018).
- **Seed 1 against the fixed preset:** −0.084 band-weighted (crunch −0.124).
- **Coherence (1–3 kHz):** 0.198, against seed 0's 0.207 and C's 0.150.

**The audit:**
- **Integrity:** the rule was committed before any seed-1 output. The recipe was the same
  apart from the seed, the re-scoring reproduced seed 0's numbers byte for byte, and no
  errors were found.
- **The per-band pattern doesn't replicate across seeds** (correlation 0.15). Most of the
  band-to-band variation is seed noise, about 0.05 per band.
- **"Unconfirmed" means under-powered, not "no gain".**
  - The two seeds together, as a description only and not a rescue, give −0.028 (−0.054
    to −0.002).
  - At an effect that size, both seeds pass only about 15–25% of the time.
- **C is itself one draw.** The two C′ seeds pick the same preset 75% of the time, but agree
  with C only 56–58%.
- **C′ differs from C in more than the gradient:** the code and the caches changed too.

**Next:** a fresh held-out test (set 5 and MedleyDB), with a mean over two or three C′ seeds
declared before any result, rather than more seeds on this development set.

## Listening (one listener, one song)

- **What was played:** "Cut It Out" (Gary Moore, 0:35–1:00) through the old rebuild and
  through interim C′ and R rebuilds.
- **What the listener heard:** the residual rebuild was the cleanest. Through all three
  rebuilds, the same preset (the dry SW50R crunch start) stayed closest to the record.
- **The measured test prefers C′'s picks.** "Cleaner to the ear" and "better at picking
  presets" are not the same, so a blinded re-run with the final rebuilds was requested.
- **Blinded re-run (2026-10-11):**
  - Labels hidden as X, Y and Z: C′ was cleanest, the residual next and the old rebuild
    least clean. The C′-against-residual difference was "very subtle".
  - Presets A and B were still labelled, and B was closest to the record again.

## What this means

- **Earlier crunch conclusions about the network are open again.** "The network chooser
  doesn't beat the fixed preset on crunch" came from networks trained with the bug.
  Corrected, both C′ seeds beat the fixed crunch preset on development (−0.12 to −0.17).
- **Earlier clean conclusions probably hold:** clean picks barely move.
- **Next:**
  1. The second C′ seed: done, unconfirmed (above).
  2. A fresh held-out test on set 5 (7 new bands) and MedleyDB, once approved and
     declared.
