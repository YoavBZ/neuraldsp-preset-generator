# How close can each Morgan amp get to a recording, and what does a menu of all three add?

Declared on 2026-10-05, before anything is computed.

**Why.** Every kill test so far ran one amp's presets at a time
(`docs/kill-test-results.md`, `docs/kill-tests-pr12-results.md`). The settings model the
tests gate treats the amp as one categorical choice, with each amp's knobs conditional
on it (`docs/supervised-model-plan.md` §2). The user pointed out that not every amp can
come close to a given recording, so testing one amp's menu caps the headroom and the
variety a recogniser sees. This measures that cap before any kill test is re-run.

## Material

- **Renders.** The SW50R, PR12 and AC20 panels (`scripts/render_preset_panel.py`), each
  through every development part's DI as cut by the first crop rule (`validation-crops`,
  the crops the panels were rendered from):
  - every factory preset with time effects off: 44 SW50R, 34 PR12 and 30 AC20;
  - each amp's template with time effects off, as a reference point.
- **Parts.** Development parts whose DI plays in at least half of each half (K1's rule)
  and whose recorded lag is clear (`docs/validation-lags.json`).
- **Distance.** The judge (`aligned_distance`), both band sets, at the recorded lag
  less the 52-sample latency.

## Procedure

K1's split-half oracle: the preset closest to the amp track on half A (1.0–5.5 s) is
scored on half B (5.5–10 s). It is computed for each amp's menu alone, and for the three
menus together (the joint menu). Choosing on one half and scoring on the other keeps the
bigger joint menu from winning by fitting half A's noise.

## What is reported

For each band set:
- **The joint menu against each amp alone:** the median over bands of each band's
  median log(joint oracle / that amp's oracle), on half B. The **best single amp** is
  the one this gap is smallest for.
- **Which amp the joint oracle picks**, as a share of parts.
- **Each amp's oracle against its own template.** That is K1's statistic, so this
  reading reproduces the earlier per-amp headroom.
- **Size-matched:** each amp's oracle over 30 of its presets (the mean of 50 random
  draws), against the closest of the three templates. Menus of different sizes don't
  then decide which amp reaches furthest.

## What decides

The question here is whether to re-run the kill tests with all three amps together.

| Reading | Rule |
|---|---|
| **The joint menu adds reach** | under both band sets, the joint oracle is at least 10% closer than the best single amp's (band median ≤ log 0.9) |
| **The best amp varies** | under the default bands, no amp holds the joint oracle's pick on more than 2/3 of parts |

If either holds, the kill tests are re-declared on the joint menu, with the amp as part
of the label as the model would have it. If neither holds, testing one amp at a time
loses little, and the per-amp verdicts stand as the model's gate.

## Limits, stated now

- **The validated range.** The judge is validated only for clear differences between
  clean-to-crunch PR12 renders. Cross-amp and high-gain distances are outside that
  range, so this is provisional.
- **A bigger menu.** The joint menu is larger as well as more varied. The size-matched
  reading separates "a better amp" from "more presets".
- **Factory presets only.** An oracle over factory presets measures what a whole-preset
  menu reaches, not what a search over each amp's knobs could reach.
