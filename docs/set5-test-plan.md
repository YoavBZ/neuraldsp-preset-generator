# Held-out test on set 5: the corrected DI network, three seeds — plan

Declared 2026-10-12, before any set-5 audio is rendered, judged or heard.

## Why

- **Development left the question open.** On the 18 development parts, the corrected network
  (C′, trained with a correct spectral gradient) picked presets closer than the old network
  C: seed 0 by −0.036, seed 1 by −0.020. Together that is −0.028, too small for one seed to
  decide ([results](residual-di-results.md)).
- **Both seeds beat the leave-band-out best factory preset on development crunch,** by −0.12
  to −0.17. That comparator is not `generate`'s starting preset, so it doesn't set gate 2's
  expectation. Development's C′ against `generate`'s start is computed before the run
  (below).
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
  - **Fytakyte is merged with BKS** (the declaration's amendment), so crunch has 4 bands
    (3 degrees of freedom) and the pooled set has 5 (4 degrees of freedom).
  - **Saturn Syndicate's two crunch parts** are one tone, double-tracked.
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
   - Reported pooled and by class. **Crunch decides:** on development C′ was neutral on
     clean, though the oracle reached −0.087 there.

## Rules for every comparison (after review)

- **Weighting:** band means are the mean of each band's part-amp cells. The interval is over
  the band means, which weights each band equally.
- **t-values by degrees of freedom:** pooled 5 bands, t(4) = 2.132; crunch 4 bands,
  t(3) = 2.353; clean 3 bands, t(2) = 2.920.
- **"More than half":** at least 3 of 5, 3 of 4, or 2 of 3 bands.
- **One common set of cells:** a part-amp cell counts in every comparison only if C, every
  C′ seed, the start and the oracle all give a scored pick in both directions.
  - A pick refused for every preset drops the cell.
  - Proxy fallbacks count as scored, and are reported per part.
- **High-gain parts are in no gate.**
- **If seed 2 fails to train,** the gates use seeds 0 and 1, and this is stated.
- **The networks' `fold2.pt` SHA-256s** are pinned in the ledger entry, before any render.
- **If gate 2 helps,** the product proposal ships seed 0, and only if each seed's own crunch
  band mean against the start is also below 0.

## Before any set-5 render

- **The scoring code is checked on the 18 development parts.** It must reproduce
  `residual_eval`'s per-seed C′-against-C band means exactly (seed 0 −0.0361, seed 1
  −0.0204).
- **The same check reports development's C′ against `generate`'s start** (development
  bands, report only), as the realistic expectation for gate 2.
- **An independent review** checks the scoring code.

## Reported

- Each seed alone, against C and against the start.
- C against the start.
- The oracle (the measure's own best preset) against the start.
- Per class and per band, band-weighted and part-weighted.
- Leave-one-band-out, the band sign-flip p, and the smallest detectable effect.
- The publisher-originals sensitivity.
- Crunch without the two parts whose crop reads high-gain (BKS Bulldozer ElecGtr5a and
  Saturn ElecGtr3).
- Proxy-fallback counts per part. Ronnie Jones ElecGtr05's DI plays in 22% of its crop.
- The sign-flip p, as description only: with 4 bands it can't go below 0.125.
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

- **Ledger:** this is set 5's first declared use. It is recorded before any render, with the
  network hashes, and `tests/test_set5.py` is updated to expect exactly this use.
- **Expected power:**
  - **Gate 1:** the interval half-width is about 0.04 against an expected effect of about
    −0.028, so roughly 30% power. "Inconclusive" is the likely outcome.
  - **Gate 2 (crunch):** the half-width is about 0.12.
- **Renders:** about 5 kinds × 111 presets × the part count, Morgan in reused instances,
  about an hour.
- **Independent reviews:** one checks this plan before any render, and an adversarial audit
  re-derives the result before it is reported.
