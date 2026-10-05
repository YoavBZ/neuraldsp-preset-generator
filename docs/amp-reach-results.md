# Each Morgan amp's reach, and what a joint menu adds

Computed as declared in `docs/amp-reach-plan.md`.
- **Which code ran:** `scripts/amp_reach.py` at 5129499, a re-run after a first run
  crashed before writing anything. The decision comes from `scripts/amp_reach_null.py`
  at a7b8082.
- **One edit after the output existed:** a7b8082 was committed 85 s after the re-run's
  output was written and before the null ran. It only changed the one-third rule's
  denominator to the one `amp_reach.py` uses (25 parts either way) and paired the
  null's permutations across band sets. With the earlier seeds, the null's 95th
  percentiles are the same.
- **Checked independently:** a fresh-context reviewer re-derived every figure from the
  stored distances without the scripts. It used its own menus, an exact
  expected-oracle computation and 4000 permutations of its own. Everything matched.

**Canaries reproduced** on the same 25 parts in 9 bands, per part as well as in the
median: SW50R −0.389 / −0.328 and clean PR12 −0.267 / −0.206 against their own
templates. The earlier SW50R K1 ran on 27 parts; the two dropped here no longer have a
clear lag, and the median is unchanged.

## Decision: don't re-run the kill tests jointly

Figures are under default / union bands, as log(joint / tested); negative means the
joint menu is closer.

| Tested menu | size-matched joint | full joint menu | another amp ≥ 0.150 closer | null 95th percentile |
|---|---|---|---|---|
| SW50R, all 44 | +0.018 / −0.005 | −0.004 / −0.048 | 4 / 4 of 25 parts (3 bands) | 6 / 6 |
| PR12, clean 21 | +0.005 / −0.006 | −0.058 / −0.056 | 4 / 6 of 25 (3 bands) | 6 / 7 |

Neither rule holds for either menu under either band set.

**At equal size, a joint menu reaches no closer.** The full joint menu's small gains
match a menu-size null: the tested menu replaced by a random same-size subset of the
joint menu.
- **SW50R:** −0.004 / −0.048 observed, against a null median of −0.020 / −0.026 (p 0.65
  / 0.21).
- **Clean PR12:** −0.058 / −0.056 observed, against −0.025 / −0.033 (p 0.12 / 0.20).

So testing SW50R's and clean PR12's menus one amp at a time was not what made their
kill tests fail.

## AC20 (reported, not deciding): where an amp falls short

| | size-matched joint | full joint menu | another amp ≥ 0.150 closer |
|---|---|---|---|
| AC20, all 30 | −0.098 / −0.058 | −0.150 / −0.187 | 14 / 15 of 25 parts (5 / 6 bands; null 95th percentile 9, chance < 0.001) |

- **It is not menu size.** The full joint menu's gain is well beyond the menu-size null
  (median about −0.05, p ≤ 0.001).
- **At equal size AC20 falls short of the other two:**
  - 17 clean presets each: +0.14 / +0.07 against PR12, +0.07 / +0.09 against SW50R;
  - 30 presets each: +0.15 / +0.10 against PR12, +0.08 / +0.06 against SW50R.
  - It reaches 7 of the 9 bands.
- **It is not AC20's preset mix:**
  - High gain: 43% of AC20's presets, against SW50R's 61% and PR12's 38%.
  - Compressor: 63%, against PR12's 79% and SW50R's 52%.
  - Its high-gain presets add nothing over its clean ones.
  - About 14 different presets from the other amps win. Removing the five most frequent
    still leaves −0.11 / −0.10.
- **What it points to** is how AC20 sounds on these mostly clean parts. That is the amp
  together with its presets' cab, mic and EQ choices; factory presets cannot separate
  the two. Several winners are presets whose character is mostly EQ and cab, two of them
  bass presets, so a joint gain is an upper bound on what the amp itself adds.
- **Under the declared rules,** if AC20 had been a tested menu its minority rule would
  have called for a joint re-run. The size-matched rule misses narrowly: −0.096 exact
  against −0.105.

**Joint picks roughly follow menu size.** On the clean menu SW50R wins 44–48% of picks
against a 31% share of the menu, and PR12 24% against 38%. Neither difference is
significant (p 0.12–0.17).

## What it means

- **For the kill tests:** the per-amp verdicts on SW50R and clean PR12 stand. A joint
  re-run is not indicated.
- **For "don't split flows per amp":** a joint menu never cost anything here at equal
  size, and it protects against an AC20-type shortfall, where one amp's menu misses
  recordings other amps reach. That is real but modest support for choosing among
  amps instead of fixing one.

## Limits

- **Few parts:** 25 development parts in 9 bands; one band, Dom McLennon, supplies 8 of
  them.
- **Mostly clean material:** clean to edge-of-breakup, so heavier recordings could
  differ.
- **Factory presets and headroom only:** this is K1-style reach. It is not what a search
  over each amp's knobs could reach, and not whether a recogniser could pick the amp.
- **The validated range:** cross-amp comparisons, and high-gain winners such as PR12
  "Creature of the Cave" on Eat The Feeder, are outside the range listening validated.
- **No AC20 canary:** none covers the AC20 distances themselves, and AC20 is the result
  that stands out.
