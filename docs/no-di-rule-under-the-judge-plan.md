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

**Controls**, not in the decision families, each with a declared consequence:
- **Positive**: SW50R's search with the part's own DI (`set2-rehearsal`, `di.wav`). It
  passes if, under both band sets, the median and sum of its band medians are below 0
  with a raw band sign-flip p below 0.05. If it fails, the pipeline is broken and every
  verdict here is void.
- **Replicate**: SW50R's no-DI search with seed 0 (`set2-rehearsal`, `no_di.wav`; its
  seed is from the run's history, not recorded on disk). If its median of band medians
  has the other sign from seed 11's under either band set, SW50R's no-DI verdict is
  fragile.
- **Null**: Tone King's two start renders (the `lib-tk-default` and `start-tk-default`
  runs, which differ only by render noise, up to 6.7 dB in a band) scored as arm and
  start. If its raw p is below 0.05 under either band set, Tone King's four verdicts
  are not read.

## Measure

`aligned_distance` between each render and the part's amp-track crop, over 1.0–10 s,
under both band sets (default and union), with the part's recorded lag from
`docs/validation-lags.json` (ambiguous lags included) less the amp's latency (52
samples for Morgan, 51 for Tone King). Every render's DI is checked against the crop's
by hash, its pack and amp model against the amp's, and both crops against their
records.

The judge normalises loudness, so this compares tone, not level; each render's level
offset and loudness over the window are kept. A part the judge refuses on any start
render, under either band set, is left out of every comparison and reading: from the
start renders alone, six (five for their pauses, Hikikomori for a DI that plays in too
few frames), leaving 37 parts in 12 bands. (The own-lag reading also leaves out a part
a start render refuses at its own lag: none, from the start renders.) An arm **loses** on a part, a log ratio of
+1.0 (2.7 times the start's distance), when its render has no measurable loudness, is
more than 20 LU under its start over the window (the product's own guitar check fails
an answer 20 dB under the template), or is refused where its start is not.

## Statistic

Per part, log(d_arm / d_start). Per comparison and band set: the band medians over the
bands, their median and their sum, the exact two-sided band sign-flip p (unrounded),
the band medians themselves, the parts closer, the losses, the part median, and the
parts closer and part median by source (Cambridge, Telefunken). With 12 bands the
smallest p is 2/4096.

## Decision

Holm within two families of eight, separately in each band set: the **product** arms
(the no-DI search and the answer calculated from the noise probe, which could ship)
and the **research** arms (the library search and the answer calculated from the
library probe, which cannot). Under one band set, an arm is **better** than the start
if the median and the sum of its band medians are both below 0 and its Holm-adjusted p
is below 0.05; **worse** if both are above 0 and the same p is below 0.05; **not shown**
otherwise. Its verdict is better or worse only if both band sets agree; otherwise not
shown. (The two families replaced one Holm family of 16 before any result under the
judge, prompted by a review's concern that a reading with fewer bands could not reach
significance over 16; the split follows which arms could ship. The error rate is held
at 0.05 per family, so a research "better" is significant within its family only.)

The verdict must also hold in three sensitivity readings, or it is reported as fragile:
the four parts with ambiguous lags dropped; each render scored at its own best lag (the
peak of its own 80 Hz–2 kHz correlation with the amp track, as `estimate_lag` computes
it, within ±2 ms of the recorded lag; how many land over 0.5 ms from the recorded lag
is reported); and the parts with over 20% of their scored frames pauses (the judge's
own count, at 2048-point frames) dropped. Counted from the start renders alone, these
keep 33 parts in 12 bands, 37 in 12, and 34 in 10. A reading only counts against a
verdict if it could reach significance at all (8 × 2/2^bands below 0.05, 9 bands or
more); all three can, though at 10 bands the pause-heavy reading has much less power,
so it can make a verdict fragile by power alone (which only ever moves the wording to
"no closer"). Every reading's full statistics are kept.

What follows:

- For the product's wording a fragile verdict counts as not shown. A void result (the
  positive control fails) or an unread one (Tone King, when the null fails) leaves the
  current text, marked as not confirmed under the judge.
- **No product arm better** (all not shown or worse): the rule stands. For every
  product arm, whatever its text says now, worse under the judge means "further from
  the recording" and not shown means "no closer" (`scripts/match_preset.py`'s refusal
  message, `skills/match/SKILL.md`, `reference/reading-a-reference.md`, the README).
- The research arms never change the rule or the advice; only the sentences that
  report them (`scripts/match_preset.py`'s note that a search through real guitar
  clips "ended level with it", and `skills/match/SKILL.md`'s "closer on 23–30 of 43")
  are updated to their verdicts under the judge.
- The wording is changed in a separate PR, after the listening test.
- **An arm better** (product or research): it is reported to the user with its
  controls and sensitivities, before anything in the product changes; this analysis
  changes nothing.
- Either way the result is provisional until stage 0b validates the judge
  (`docs/listening-validation-plan.md`).
