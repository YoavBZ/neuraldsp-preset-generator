# Set 4 confirmation: plan (DRAFT, not approved)

Drafted 2026-10-10. **Nothing in it runs until the user approves.** Running it spends set
4 ([validation-set4.md](validation-set4.md)), which nothing has used. It also waits for
the heavy-tone listening check ([heavy-listening-plan.md](heavy-listening-plan.md)): if the
listener does not back the judge on clear heavy pairs (block 2, 5 or fewer of 10), this
test is postponed. A measure the ear doesn't support can't confirm anything.

## The claim under test

On set 3's development parts, under the fixed-level measure, choosing a menu preset through
the network's rebuilt DI, low-passed at 3 kHz, beat a fixed driven preset per amp: −0.143,
90% interval −0.274 to −0.012 ([results](fixed-level-rescore-results.md)). That result had
many forks; the reviewer expected about half the size on fresh material. This test
checks it once on fresh bands.

## Frozen before any set-4 audio is used

- **Network:** `~/ndsp-presets/learn/direc/models-set3/fold2.pt` (the set-3 network,
  unchanged; it never heard set 4). CPU inference; its rebuilt DI is low-passed at 3 kHz
  (`learn/rebuilt_judge.lowpass`) and played at −22.9 LUFS.
- **Choosing:** on each half (1.0–5.5 s and 5.5–10 s) against the amp track, at lag −52,
  with the reference-proxy fallback (`learn/rebuilt_judge.rebuilt_distance`). The judge is
  the validated one (`flat` weighting, `recording` bands).
- **Menus:** the three amp menus of set 3 (factory presets plus template+R).
- **Fixed presets,** chosen now by the declared rule. That is the lowest median, over all
  33 set-3 development parts, of the mean of the half-A and half-B fixed-level distances,
  factory presets only:

  | amp | fixed preset | median distance |
  |---|---|---|
  | PR12 | Keyan Houshmand / Modern Metal (Pick Hard) | 4.596 |
  | SW50R | Royce Whittaker / Wall Of Doom | 4.427 |
  | AC20 | Danny Dela Cruz / Raw N Crunchy | 4.825 |

  (`generate` ships Vintage Metal and Dirty Coil Rhythm for PR12 and AC20, from the
  earlier own-level rule. They are within 1.2% and 0.6% of these, so the product is
  unchanged.)
- **The measure:** the set-4 part's true DI, re-equalised to K3 fold 2's average balance,
  at −22.9 LUFS, rendered through the chosen preset and judged against the amp track on the
  other half, at the part's judge lag.
- **Statistics** ([closeness review](closeness-review-2026-10-10.md)):
  - the unit is the band, with amps pooled within it;
  - each part-amp cell averages both scoring directions;
  - the statistic is the part-weighted mean log ratio, with a band-clustered 90%
    interval (t, bands − 1 degrees of freedom), plus wins/ties/losses and the exact band
    sign flip.

## Gates, in order

1. **Positive control: the true-DI oracle vs the fixed presets.** Its 90% interval must
   lie below 0. If not, the test is **uninformative** and stops: set 4 can't resolve even
   the oracle's edge.
2. **Primary: the cut chooser vs the fixed presets,** pooled over the three amps.
   - **Confirmed:** the 90% interval lies below 0.
   - **No meaningful edge:** the lower bound is above −0.05.
   - **Inconclusive:** anything else.

**Reported, not gates:**
- per amp;
- the cut chooser vs the uncut rebuilt DI;
- the tonal and temporal parts;
- each pick's gain-knob bias against the oracle;
- the same comparisons under judge v2, as a sensitivity check only;
- refusals.

## Power

Set 4 has 5 bands, and up to about 9 if the Internet Archive sessions pass their checks.
From resampling set 3's bands:
- **The oracle's edge** (about −0.26) is resolvable with 5 or 6 bands about 96% of the
  time.
- **The chooser's observed −0.143** has about 34% power with 6 bands and about 60–70%
  with 9–11.
- **The expected −0.07** has 15% or less.

So a "confirmed" outcome would be strong evidence, while "inconclusive" is the likely
outcome unless the effect is near its development size. The final band count and its
power go in the approval request.

## Before running

- **Approval:** the user's approval, after the listening check.
- **Freezing:** a committed manifest of the frozen inputs (network hash, menus, fixed
  presets, set-4 declaration hash, code commit).
- **Review:** an independent reviewer re-derives the result before it is reported.
