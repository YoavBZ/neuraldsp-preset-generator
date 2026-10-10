# How we measure closeness: a deep review (2026-10-10)

Four independent reviews of how song-to-preset results are measured, each from the
code, the docs and stored renders only (no new plugin renders):
1. the judge itself;
2. the scoring protocol and its reliability;
3. the statistics and decision gates;
4. perceptual validity.

Reports and scripts are local: `tmp/closeness-review-{1-judge,2-protocol,3-stats,4-perception}.md`.
The key claims below were re-checked in this session.

## What holds

- **The judge is arithmetically sound and repeatable.**
  - Its level removal is exact, its alignment correct, and its three frame sizes agree
    (ρ ≥ 0.998).
  - Half A ranks presets almost exactly as half B does (median ρ 0.99). A pick's
    log-distance moves about 0.04 between halves.
- **Robust conclusions** (band-clustered intervals):
  - the rebuilt-DI gap (−0.21) and its "rest" share (−0.18);
  - level is not half the gap;
  - longer training doesn't help (v2b);
  - the 6 kHz cut does nothing;
  - the driven presets beat the clean template (−0.39);
  - the true-DI oracle beats the fixed preset under every measure tried.
- **The judge's weighting is broadly reasonable.** A perceptually weighted loudness
  distance agrees with it about as often as the judge agrees with itself across halves
  (62 against 65 of 84 driven menus). MR-STFT and PANNs mostly disagree, but in the
  literature they also correlate weakly with listeners.

## What is wrong or fragile

### The judge

1. **It is deaf to treble on parts with a dominant low fundamental.**
   - **What happens:** the band selection (30 dB) and the per-frame floor (40 dB) are
     both measured from the recording's loudest band in unweighted dB.
   - **The extreme cases:** on the three Ill Fate parts only 7–12 of 64 bands are
     scored (below 350–630 Hz), under both band sets; the median part scores 45.
   - **The effect:** boosting a render 12 dB above 5 kHz moves its distance by exactly
     0, and the winner there is 37–41 dB too bright above 2.5 kHz.
2. **Excess treble and fizz are nearly free under `recording` bands.**
   - On clean parts the scored bands stop near 3 kHz, and both band sets are blind
     above 8 kHz.
   - Winners on Colour Me Red and Magilla are 13–25 dB too bright at 5–10 kHz.
3. **The floor is lopsided.** Missing content is clamped while excess is counted in
   full (a median 5.6% of cells, up to 31%).
4. **Smaller points.**
   - The mel filters are not area-normalised: treble bands gain up to 13 dB from
     bandwidth alone.
   - `union` scores each candidate on a different band set.
   - The judge barely sees drive amount once the spectrum is matched (+0.05).

### The measure and the protocol

5. **The DI's own level is a recording artefact.**
   - **What the measure does:** it feeds each true DI at its session level (−46.5 to
     −16.8 LUFS). That is the interface's gain, not the guitar, so it is neither what the
     record's amp heard nor "an average guitar".
   - **At a fixed −22.9 LUFS,** several conclusions change:
     - the 3 kHz cut is −0.062 (it passes);
     - the cut against the fixed driven preset is −0.137, with an interval that excludes
       zero.
6. **Picks are near-ties.**
   - The best and second-best menu presets differ by a median 0.043; only 10% clear the
     validated 0.15.
   - Half A and half B pick different winners 27% of the time.
   - One 10 s crop per part, and crops one second apart pick differently.
7. **Selection bias.** The fixed driven presets were chosen on the same 33 parts, a head
   start of 0.01–0.05, the size of our bars. Against leave-band-out constants, the
   network goes from −0.037 to −0.070.

### Perception

8. **The verdict "the network hasn't beaten the fixed preset" depends on the judge's
   weighting.**
   - **The two halves split:** on the tonal part the network's picks win 51 to 29; on
     the temporal part they lose 22 to 58.
   - **The reason: the picks are under-driven.** Their gain knob is below the oracle's
     on 43 parts and above on 14.
     - **Not the level:** at the true level the bias is −0.106; the true DI at a fixed
       level is nearly unbiased (−0.022).
     - **The rebuilt waveform:** its spurious detail makes every preset sound dirtier,
       so the chooser picks less gain. The 3 kHz cut reduces the bias from −0.124 to
       −0.088.
9. **No heavy-tone pair has ever been played to a listener.**
   - The listening validation is one listener, on clean-to-crunch PR12, at margins
     above 0.15.
   - The decisions are made on driven SW50R and AC20, at 0.01–0.05.

### Statistics

10. **The pooled p-values were overconfident.** The sign flip ran on 33 amp × band
    groups, which are not independent.
    - **Clustering on the band** moves "balance hurts" from p 0.002 to 0.12, and
      "3 kHz cut vs constant" from 0.009 to 0.39.
    - **The median of band medians** is 0 in most pick comparisons, and can disagree in
      sign with the mean.
11. **The held-out gate was nearly unpassable.**
    - **With six bands,** two or more zero band medians make p < 0.1 impossible; that
      happened in 70% of resamples.
    - **Even a true −0.28 effect** passes only 28% of the time, and the true-DI oracle
      itself fails the SW50R gate.
    - **The accurate wording:** "no edge shown". SW50R vs constant is +0.065, with a 95%
      interval of −0.27 to +0.40.
12. **Many tests reused the same 33 parts.** About 15 decision comparisons were run on
    them. After a Holm correction, only the gap, its "rest" and driven-vs-template
    survive.

## Changes adopted now (no decision needed)

- **The analysis protocol** for future tests:
  - the band is the unit, with amps pooled within it;
  - the primary statistic is the part-weighted mean log ratio, with a band-clustered 90%
    interval and an exact band sign flip on band totals;
  - three outcomes, declared in advance: helps, futile or inconclusive, each with a
    declared action;
  - power is checked before running, using the true-DI oracle;
  - picks that change are reported separately from the gain per changed pick;
  - one ledger of tests on the development parts.
- **Score on both halves** (choose on A and score on B, and the reverse), and average.
- **Compare against leave-band-out constants** on development.
- **Report the tonal and temporal parts** beside every decision, and flag sign conflicts.
- **Add a drive-bias diagnostic** (pick vs oracle gain knob) to rebuilt-DI evaluations.

## Decisions for the user

- **The measure's DI level:** the session's own level (as now), or a fixed average
  level. The reviewers recommend the fixed level; results under both are reported until
  decided.
- **A heavy-tone listening check** (36 trials, two phone sittings). It asks which the
  ear weighs more when the tonal and temporal parts disagree, and extends the judge's
  validation to SW50R and AC20.
- **Judge fixes**, as a new judge version beside the current one:
  - hearing-weighted band selection and floor;
  - a fixed band set per part, up to about 10 kHz;
  - a refusal when too few bands are scored.

  These change what "closer" means, so they go together with the listening check.
