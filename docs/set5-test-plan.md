# Held-out test on set 5: the corrected DI network, three seeds — plan

Declared 2026-10-12, before any set-5 audio is rendered, judged or heard.

## Why

- **Development left the question open.** On the 18 development parts, the corrected network
  (C′, trained with a correct spectral gradient) picked presets closer than the old network
  C: seed 0 by −0.036, seed 1 by −0.020. Together that is −0.028, too small for one seed to
  decide ([results](residual-di-results.md)).
- **Both seeds beat the fixed crunch preset on development crunch,** by −0.12 to −0.17.
- **Set 5 is fresh:** 7 new bands, declared held out and never scored
  ([declaration](validation-set5.md)).

## Parts

- **Set 5's clean and crunch parts** (in scope), at the gain class its declaration assigns.
  High-gain parts are report only.
- **Counted as declared:** 26 parts in 6 bands, stratified by each part's own gain class.
  BKS has both clean and crunch parts.
  - **Clean:** 16 parts in 3 bands (Ronnie Jones 8, Hazael 4, BKS 4).
  - **Crunch:** 10 parts in 5 bands (BKS 5, Saturn Syndicate 2, Ronnie Jones 1, The
    Ferryboat Men 1, Fytakyte 1).
  - **Pooled:** 6 bands, so 5 degrees of freedom. Crunch has 5 bands, so 4.
- **Report only:** 5 high-gain parts (Nova-One Studio 4, Saturn Syndicate ElecGtr4).
- **The powers are small.** Gate 2's crunch stratum has 5 bands, two of them a single
  re-hosted part. The smallest detectable effect is reported, and an inconclusive result
  leads to the combined test below, not to more set-5 analyses.
- **Sensitivity:** publisher originals only. This drops the two bands that rest on one
  Hugging Face re-hosted part each.

## Networks (fold 2; no set-5 band is in any training data)

- **C:** `models-set3/fold2.pt`, the old network.
- **C′:** three seeds trained with a correct gradient, the same recipe and data:
  `models-cprime` (seed 0), `models-cprime-s1` (seed 1) and `models-cprime-s2` (seed 2).
  Seed 2 is trained for this test and is unseen on development.

## Procedure (per part)

- **The measure:** the take's true DI, re-equalised to the pinned average and set to
  −22.9 LUFS (`measfix`), rendered through all 111 dry menu presets. Scored with the `flat`
  judge on half A (1.0–5.5 s) and half B (5.5–10 s).
- **Each network:** rebuild the DI from the amp track (uncut, at −22.9 LUFS), and render it
  through the same presets.
- **Judge lag:** each part's `judge_lag_samples` as declared (set 4's convention).
  Rebuilt DIs use `rebuilt_distance`'s convention, as on development.
- **Mixes are absent** for most set-5 crops, so this tests from the amp track, as the
  set-4 confirmation did. A song-level (stem) check is not part of this test.
- **Picks:** judge each render with `rebuilt_distance` on one half, pick per amp, and score
  the pick with the measure on the other half. Both directions are averaged.

## Gates (band means, t-interval with bands − 1 degrees of freedom)

Per part-amp cell, the log ratio is averaged over both directions. A band mean is the mean
of its cells. The 90% interval is over the band means.
- **Helps:** the interval lies below 0, and more than half the bands are negative.
- **Futile:** the lower bound is above −0.02.
- **Inconclusive:** anything else.

1. **Gate 1, a correct gradient:** C′ against C.
   - Each cell's ratio is the mean over the three seeds of `log(pick_seed / pick_C)`.
   - The seed averaging is declared here, before any result.
2. **Gate 2, the product question:** C′ against `generate`'s own starting preset for the
   part's class.
   - The clean baseline (Royally Ambient, Pedal Platform Clean, Low-Watt Americana) or the
     crunch baseline (Modern Metal (Pick Hard), Hair Metal, AC20 Mid-Gain Drive), dry.
   - Each cell's ratio is the mean over seeds of `log(pick_seed / start)`.
   - Reported pooled and by class. **Crunch decides,** because development showed no
     headroom on clean.

## Reported

- Each seed alone, against C and against the start.
- C against the start.
- The oracle (the measure's own best preset) against the start.
- Per class and per band, band-weighted and part-weighted.
- Leave-one-band-out, the band sign-flip p, and the smallest detectable effect.
- The publisher-originals sensitivity.
- High-gain parts, report only.

## Consequences (declared now)

- **Gate 1 helps:** C′ replaces C as the research network.
- **Gate 2 helps on crunch:** a product proposal goes to the product session to offer the
  chooser's pick on the audition page for crunch songs, marked experimental. That session
  decides.
- **Inconclusive:**
  - set 5 joins MedleyDB (once approved) for one combined declared test;
  - no further set-5-only analyses that could decide anything.
- **Futile:** the network chooser is not pursued for that class.

## Safety

- **Ledger:** this is set 5's first declared use, recorded before any render.
- **Renders:** about 5 kinds × 111 presets × the part count, Morgan in reused instances,
  about an hour.
- **Independent reviews:** one checks this plan before any render, and an adversarial audit
  re-derives the result before it is reported.
