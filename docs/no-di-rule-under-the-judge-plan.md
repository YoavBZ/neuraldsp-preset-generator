# Does "without a DI, keep the starting preset" hold under the judge?

Declared before anything is computed. PR #107 made `scripts/match_preset.py` refuse to
search without a DI and keep the starting preset, because every no-DI answer measured
ended no closer to the recording than the start (`docs/tone-matching-plan.md`, "The
real-guitar probe, from neutral settings and from the shipped presets"). Those
measurements used `unpaired-v3`, since retired as a judge (`docs/measuring-closeness.md`);
the searches had also been optimised against that same score. This re-scores the same
renders with the judge, `analysis/aligned.py`.

## Renders (already on disk; nothing new is rendered)

Per amp, the 43 set-2 development parts, each rendered through its own DI:

| Amp | Start (as it is) | Arms |
|---|---|---|
| SW50R | shipped template | no-DI search (seed 11); library search; calculated from the library probe; calculated from the noise probe |
| PR12 | shipped template | the same four |
| AC20 | shipped template | the same four |
| Tone King | Default | the same four |

The search answers come from the `start-*` and `match-pipeline-template-s11` runs, the
library and calculated ones from the `lib-*` runs; each run's own `template.wav` is its
start.

## Measure

`aligned_distance` (default bands) between each render and the part's amp-track crop,
over 1.0–10 s, with the part's lag from `docs/validation-lags.json` less the amp's
latency (52 samples for Morgan, 51 for Tone King). The union band set is reported
beside it. A window the judge refuses (over half its scored frames pauses) leaves that
part out of that comparison; refusals are listed. Results on the three parts whose lag
is ambiguous are listed too.

## Statistic

Per part, log(d_arm / d_start). Per arm and amp: the band median over the 13 bands, the
parts closer than the start, and the exact two-sided band sign-flip p.

## Decision

- An arm **beats the start** if its band median is below 0 and its band p, Holm-adjusted
  over the 16 arm-and-amp comparisons, is below 0.05.
- If no arm does, the rule stands as it is.
- If one does, it is reported to the user before anything in the product changes; this
  analysis changes nothing in the product.
- Either way the result is provisional until stage 0b validates the judge
  (`docs/listening-validation-plan.md`), and it covers isolated amp tracks, not mixes.
