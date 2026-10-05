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
scored on half B (5.5–10 s). Choosing on one half and scoring on the other keeps a
bigger menu from winning by fitting half A's noise.

It is run on the two menus the kill tests were given, each against menus drawn from
all three amps:
- **SW50R:** all 44 of its factory presets, against the joint menu of all 108.
- **PR12:** its 21 clean presets, against the joint menu of the 55 clean ones (17 AC20,
  21 PR12, 17 SW50R). "Clean" is stage 0b's rule: no drive pedal, volume at most 0.75.

AC20, never kill-tested, gets the same reading against all 108, reported only.

## What decides

The question is whether to re-run the kill tests with all three amps together. For each
tested menu, under both band sets:

| Reading | Rule |
|---|---|
| **Size-matched** | a joint menu of the same size, drawn evenly from the three amps (200 draws, the same under both band sets), is at least 10% closer: median of band medians of log(joint / tested) ≤ log 0.9 |
| **A minority the amp can't reach** | on at least a third of the parts, spanning at least 3 bands, the full joint menu's pick is another amp's preset and at least 0.150 (the judge's validated cut) closer on half B than the tested menu's |

If either holds for either tested menu under both band sets, the kill tests are
re-declared on the joint menu, with the amp as part of the label as the model would
have it. If neither holds, testing one amp at a time loses little for these two
verdicts.

**The minority rule's null** (added after a first run crashed before writing anything,
before any output of the re-run was read). The minority count compares the full joint menu with a
smaller tested menu, so it can fire when the amps are interchangeable. So the joint
menu's presets are reassigned to amps at random 1000 times
(`scripts/amp_reach_null.py`). Each reassignment keeps each amp's menu size and uses
one assignment for every part. The minority rule holds only if, under both band sets,
the observed count also exceeds the null's 95th percentile.

**Order of reading.** First only `canary_misses` is read. If the canaries missed,
nothing else is read. Otherwise the decision comes from `scripts/amp_reach_null.py`.

**Canaries.** Each tested menu against its own template reproduces the earlier K1 under
the judge, on the same 25 parts in 9 bands. The recorded lags equal the frozen ones on
every part used. The expected values, to 4 decimals:
- SW50R: −0.3888 (default bands) and −0.3280 (union);
- PR12 clean: −0.2670 and −0.2064.

If either misses, the run stops and nothing is read.

**Reported, not deciding:**
- the full joint menu against each tested menu;
- AC20's reading;
- each amp's share of the full joint menu's picks, against the share its menu size
  alone would give;
- the parts and bands of every reading;
- the parts left out (a quiet half, or no clear lag).

## Limits, stated now

- **The validated range.** The judge is validated only for clear differences between
  clean-to-crunch PR12 renders. Cross-amp and high-gain distances are outside that
  range, so this is provisional.
- **A bigger menu.** The full joint menu is larger as well as more varied; the
  size-matched reading is the one that separates "a better amp" from "more presets".
  Matching size does not match variety: three of Neil Zaza's SW50R presets render
  identically.
- **What a joint gain is.** Another amp's preset also brings its own mics, EQ and
  compressor, so a joint gain is an upper bound on what the amp itself adds.
- **Headroom only.** This is K1-style reach. Whether a recogniser can pick the amp from
  a real track (K3) is not measured here; the amp identifiability check used renders
  through the same DI.
- **Not independent.** These are the same 25 development parts and 9 bands as the
  earlier K1.
- **Below the validated cut.** A 10% band-median gain is under the 0.150 per-pair cut
  that listening validated.
- **High gain.** 53 of the 108 presets are high-gain, outside the validated range. The
  PR12 reading uses clean presets only.
- **Factory presets only.** An oracle over factory presets measures what a whole-preset
  menu reaches, not what a search over each amp's knobs could reach.
