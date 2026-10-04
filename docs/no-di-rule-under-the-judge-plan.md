# Does "without a DI, keep the starting preset" hold under the judge?

Declared before anything is computed. PR #107 made `scripts/match_preset.py` refuse to
search without a DI and keep the starting preset, because every no-DI answer measured
ended no closer to the recording than the start, and some further (`docs/tone-matching-plan.md`,
"The real-guitar probe, from neutral settings and from the shipped presets"). Those
measurements used `unpaired-v3`, since retired as a judge (`docs/measuring-closeness.md`),
and the searches had been optimised against that same score. This re-scores the same
renders with the judge, `analysis/aligned.py`. It covers the shipped starting points
(Morgan's templates, Tone King's Default), not a user's own preset, and isolated amp
tracks, not mixes.

## Renders (already on disk; nothing new is rendered)

Per amp, the 43 set-2 development parts, each rendered through its own DI in a fresh
process. Each arm is paired with its own run's start render (`template.wav`).

| Amp | Start (as it is) | Arms |
|---|---|---|
| SW50R | shipped template | no-DI search (seed 11); library search; calculated from the library probe; calculated from the noise probe |
| PR12 | shipped template | the same four |
| AC20 | shipped template | the same four |
| Tone King | Default | the same four |

The search answers come from the `start-*` and `match-pipeline-template-s11` runs, the
library and calculated ones from the `lib-*` runs (the runs PR #107 relied on). The
library arms' probe is built from the project's own development DIs, so it cannot
ship: a library arm that beats the start is a research lead, not a product change.

**Controls**, reported, not in the decision family:
- **Positive**: SW50R's search with the part's own DI (`set2-rehearsal`, `di.wav`). It
  must beat the start; if it does not, the pipeline is broken and nothing here is read.
- **Replicate**: SW50R's no-DI search with seed 0 (`set2-rehearsal`, `no_di.wav`).
- **Null**: Tone King's two start renders (the `lib-tk-default` and `start-tk-default`
  runs, which differ only by render noise) scored as arm and start.

## Measure

`aligned_distance` between each render and the part's amp-track crop, over 1.0–10 s,
under both band sets (default and union), with the part's recorded lag from
`docs/validation-lags.json` (ambiguous lags included) less the amp's latency (52
samples for Morgan, 51 for Tone King). Every render's DI is checked against the crop's
by hash, and its pack against the amp's. A window the judge refuses for its pauses leaves that part out of every
comparison (expected: six parts, leaving about 37 in 12 bands); an arm render with no
measurable loudness against a measurable start counts as a loss.

## Statistic

Per part, log(d_arm / d_start). Per comparison and band set: the band medians over the
bands, their median and their sum, the exact two-sided band sign-flip p (unrounded),
the parts closer, the part median, and the same split by source (Cambridge,
Telefunken). With 12 bands the smallest p is 2/4096.

## Decision

Holm over the 16 comparisons, separately in each band set. Under one band set, an arm
is **better** than the start if the median and the sum of its band medians are both
below 0 and its Holm-adjusted p is below 0.05; **worse** if both are above 0 and the
same p is below 0.05; **not shown** otherwise. Its verdict is better or worse only if
both band sets agree; otherwise not shown.

The verdict must also hold in three sensitivity readings, or it is reported as fragile:
the four parts with ambiguous lags dropped; each render scored at its own best lag (the
peak of its own 80 Hz–2 kHz correlation with the amp track, as `estimate_lag` computes
it, within ±2 ms of the recorded lag); and the parts with over 20% of their scored
frames pauses (the judge's own count, at 2048-point frames) dropped.

What follows:

- **No arm better** (all not shown or worse): the rule stands. Where an arm is worse
  under the judge, the product's wording "further from the recording" stays for it;
  where it is only not shown, that wording becomes "no closer" (`scripts/match_preset.py`'s
  refusal message, `skills/match/SKILL.md`, `reference/reading-a-reference.md`, the
  README). The wording is changed in a separate PR, after the listening test.
- **An arm better**: it is reported to the user with its controls and sensitivities,
  before anything in the product changes; this analysis changes nothing.
- Either way the result is provisional until stage 0b validates the judge
  (`docs/listening-validation-plan.md`).
