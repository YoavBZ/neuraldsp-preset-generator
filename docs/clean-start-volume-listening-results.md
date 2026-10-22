# Are the turned-down clean starts closer by ear? Results (2026-10-22)

[Plan](clean-start-volume-listening-plan.md), declared before any trial was built; numbers in
[clean-start-volume-listening-results.json](clean-start-volume-listening-results.json). One
listener, two sittings (23 and 24 trials), 13 clean development parts each through its own DI
on all three amps, the clean start as shipped against turned down, beside the recorded guitar.
Key SHA-256 `c73ef0f0…afe5b` and answers SHA-256 `42027ad5…ff670` were committed before the
key was read. Renders reproduced the stored scores (half B worst |Δ log| 0.00025, with
`isolate`); the set-12 DIs, removed in the 2026-10-20 cleanup, were rebuilt by the same recipe.

## Checks

- **Hidden references:** both found; no sitting void.
- **Reversed taste:** on both controls (crunch parts on SW50R and AC20, where the judge prefers
  the shipped start) the listener chose the shipped start. A plain preference for the cleaner
  option did not drive these two (two trials: it argues against such a preference, it
  cannot rule it out).
- **Repeats:** one of three decided twice, consistent; the other two had a "?" in one of the
  pair.

## Readings

| amp | turned down chosen | share (95% interval) | can't tell | judge chose turned down |
|---|---|---|---|---|
| PR12 (49.2 → 35) | 0 of 3 | 0.00 (0.00-0.71) | 10 | 7 of 13 |
| SW50R (35.2 → 15) | 5 of 11 | 0.45 (0.17-0.77) | 2 | 2 of 13 |
| AC20 (30 → 10) | 9 of 12 | 0.75 (0.43-0.95) | 1 | 8 of 13 |
| pooled, descriptive | 14 of 26 | 0.54 (0.33-0.73) | 13 | |

- **By how driven the record is** (stored-score margin, split at the median): AC20 6 of 6 on
  the cleaner records, 3 of 6 on the more driven; SW50R 3 of 5 and 2 of 6; PR12 0 of 2 and 0 of 1.
- **By part:** no part got the turned-down start on all three amps; 4 parts got it on none.
- **Ear and judge** agreed on 18 of 26 decided trials, on all 7 where the judge's margin was
  over 0.15.
- **Levelling:** the turned-down renders are quieter and got more gain (median: PR12 2.6 dB,
  SW50R 5.6, AC20 12.5), so their hiss rose with them; AC20's was preferred with more hiss, which on references that
  carry room bleed could itself sound closer.

## Bleed in the references (added after the results, not declared)

The listener noticed other instruments in some references. R is the part's own amp track from
the multitrack, not the mix, but the Telefunken sessions were recorded live and their guitar
mics carry bleed ([bleed audit](audits/bleed-2026-10-16/README.md), half B): First Offering
GTR_1 and Long Way Home high, Blind Spots, Bloomlight and First Offering GTR_2 moderate; the
other 8 parts low. The project reports the no-bleed row beside all parts, so:

| amp | all 13 parts | 8 low-bleed parts | 5 moderate or high |
|---|---|---|---|
| AC20 | 9 of 12 | 4 of 7 | 5 of 5 |
| SW50R | 5 of 11 | 2 of 7 | 3 of 4 |
| PR12 | 0 of 3 | 0 of 2 | 0 of 1 |

The decisions are the same on the low-bleed parts (AC20 at least half, SW50R below), but
AC20's lead is much weaker on clean references (4 of 7) than over all parts: most of it came
from parts whose reference itself carries other instruments. The two splits overlap: 4 of the
6 "cleaner" parts are bleed-flagged, so AC20's 6 of 6 on cleaner records and 5 of 5 on bleed
parts are largely the same trials (on low-bleed parts AC20 is 2 of 2 cleaner, 2 of 5 more
driven), and SW50R's 3 of 5 on cleaner records also rests on bleed parts. Two small choices,
not spelled out in the plan: the median part goes to "more driven" (6 and 7), and the
same-song reading drops all four parts of the two pairs.

## Decision (as declared)

- **AC20: keep the rule** (`ac20Volume` 10 for a part documented as fully clean), weakly:
  4 of 7 on the low-bleed parts.
- **SW50R: revert** to saying the start may break up, without changing its volume. 5 of 11 is
  below half; the interval is wide, and on the cleaner records it leaned the other way (3 of 5),
  so this is a best estimate, not a finding that the shipped volume is better.
- **PR12: no change.** Mostly "can't tell": 35 and the shipped 49 are hard to tell apart on real
  clean parts; the borderline breakup heard on the synthetic riff was rarely audible on these
  (the 3 decided trials went to the shipped start).

## Limits

One listener, not blind to the hypothesis, in-sample; 13 parts, half B only; each amp's
decision rests on a few trials (the intervals). The parts are labelled clean, not documented as
fully clean.
