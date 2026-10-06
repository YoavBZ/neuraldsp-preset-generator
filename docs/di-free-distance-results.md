# Which distance without a DI reproduces the judge's choices? Results

Run on 2026-10-07 as declared in [di-free-distance-plan.md](di-free-distance-plan.md)
(revised after two independent reviews, all before any distance was computed). Scored
by `research/di_free_distance.py`; the full output is
[di-free-distance.json](di-free-distance.json).

## Verdict: no row passes

None of the eight DI-free distances passes the gate on any menu or band set. v3 is not
"already enough" either (its regret is far above the 0.09 stop), so the step has no
answer. As declared, the next candidates are those that need downloads or training:
round 4's embedding rows (AFx-Rep, CLAP as a floor) and round 1's own contrastive
encoder (approach 3c).

## The numbers

Regret is in log distance under the judge (0 is the judge's own pick), as the band
statistic over the 25 parts' 9 bands, each part over 19–26 donors from the other bands.

| | recording, all 111 | recording, clean 58 | union, all 111 | union, clean 58 |
|---|---|---|---|---|
| A random pick | 0.44 | 0.38 | 0.47 | 0.37 |
| The song-blind constant | 0.42 | 0.42 | 0.36 | 0.36 |
| v3 (baseline) | 0.35 | 0.34 | 0.36 | 0.38 |
| v3c | 0.35 | 0.32 | 0.37 | 0.33 |
| Long-term spectrum | 0.36 | 0.39 | 0.36 | 0.38 |
| Log-mel mean and spread | 0.32 | 0.40 | 0.33 | 0.42 |
| MFCC statistics | 0.38 | 0.36 | 0.44 | 0.39 |
| Lean fingerprint | 0.42 | 0.38 | 0.45 | 0.38 |
| Masked long-term spectrum | 0.36 | 0.34 | 0.38 | 0.30 |
| Masked log-mel mean and spread | 0.35 | 0.34 | 0.41 | 0.39 |
| LDA | 0.46 | 0.35 | 0.48 | 0.45 |

- **No row is clearly better than the song-blind constant.** The best figure in any
  block, 0.30 (masked long-term spectrum, union, clean menu), is 0.83 times the
  constant's 0.36; the gate asked for 0.75. On the full 111 menu several rows beat a
  random pick by about 0.1 (log-mel mean and spread 0.32 against 0.44), mostly by
  avoiding high-gain presets, which the constant does as well. On the recording/clean
  block the constant (0.42) is itself worse than a random pick (0.38), so it is a weak
  anchor there; no row clears the 0.75 ratio against v3 either.
- **No row beats the constant across bands.** The closest row's raw one-sided sign-flip
  p is 0.15 to 0.30 per block (0.18, 0.15, 0.28, 0.30; all in the JSON's `raw_p`),
  before Holm across the 8 rows takes every one to 1.0: each row wins in some bands and
  loses in others.
- **Agreement with the judge on the clean menu is low:** at most 0.38 (the two
  unmasked log-mel rows), against the gate's 0.6. v3 agrees at 0.01 and −0.03.
- **On stems (12 parts)** every row is worse than the constant in every block: the best
  row's regret is 0.35 to 0.38, against the constant's 0.33.

## Why: the rows track the tone only when the notes match

Added after the run (and computed by the same code, `own_di_regret`): each row's regret
when it picks among the candidates rendered through the part's **own** DI, the same
notes as the amp track, instead of through another player's.

| Row (recording, all 111) | Own DI: same notes | Donors: other notes |
|---|---|---|
| Masked long-term spectrum | 0.04 | 0.36 |
| Masked log-mel mean and spread | 0.035 | 0.35 |
| v3c | 0.13 | 0.35 |
| Log-mel mean and spread | 0.16 | 0.32 |
| v3 | 0.24 | 0.35 |
| LDA | 0.30 | 0.46 |

With the notes matched, the two masked rows pick within the judge's near-tie range
(0.09). Through another player's notes, the same rows fall to about the song-blind
constant. So the performance (its notes, guitar and playing) moves these distances
more than the preset does. Part of the same-notes success is circular, since the masked
rows copy the judge's spectral treatment; the other-notes failure is not.

The own-DI share (in a mixed menu, how often a row picks a render of the take itself)
is 0.73 (LDA) to 0.98 (masked mean and spread) over all part and donor pairs; the
plan's band statistic of it reads 1.00. Every row sits closer to renders of the take
itself, but that is expected even of a fair tone distance (another player shifts every
render at once), so it is not by itself why the picks fail. (The plan's "0.5 if the
row cannot tell them apart" was also wrong: exact ties go to the donor.)

## Reported, not deciding

- **Per amp** (recording, all): the rows' regret within one amp's presets ranges from
  0.23 to 0.57 across rows and amps.
- **Per band:** the spread is wide for every row (for the log-mel mean and spread,
  0.07 in one band to 0.59 in another), which is why no row beats the constant across
  bands.
- **Another teacher** (the average-guitar measure, branch `poc/sound-model`, on the 22
  clean PR12 candidates, half B): the rows' regret is 0.11 to 0.22, against 0.24 for a
  random pick's expected regret on that menu (a post-hoc reference, computed after the
  run, and not a test). The lean fingerprint is lowest (0.11 / 0.11). Under the judge's
  own half-B distance on the same menu, the rows' regret is 0.19 to 0.45, against 0.27
  to 0.28 for a random pick, so some rows are worse than random there (LDA 0.31 / 0.45).
  As declared, this cannot change the verdict. The average-guitar measure is not yet
  validated; if its listening check confirms it, a check under it, covering all three
  amps, would be worth declaring.
- **Empty distances:** none. One render (a preset through one donor's DI) is silent and
  was skipped.

## Deviations, all before any distance was computed

- The plan was revised after an independent review (anchoring the gate on the
  song-blind constant, band statistics, the clean menu, qualified stems, active donors,
  the masked and LDA rows), and amended after a review of the code (regret over the
  whole menu when a distance is empty, the stop deciding the answer, the stem
  tie-break).
- The code review's amendment also changed two things that move numbers: the
  song-blind constant became the candidate with the lowest median judge distance (as
  the plan says), not the lowest median log distance; and non-finite distances count
  as empty. Both used judge data only, before any row distance existed.
- Two inputs turned out unmeasurable and were declared before the run: one silent
  render, skipped; and an empty loudness range on 325 of 4,773 renders, handled in the
  lean and LDA rows.
- After the run, the results review led to three readings added to the output (the
  own-DI regret, the raw own-DI share, the raw sign-flip p-values); re-running
  reproduced every earlier number.

## What follows

- **Roadmap step 2 is not met by hand-made features.** The next candidates are an
  effects encoder (AFx-Rep, a 1.2 GB download that needs approval) and a contrastive
  encoder trained on the panels to ignore the performance (round 1, approach 3c: 2 to 3
  weeks, and the panels already hold every preset through 43 players' DIs, the pairs
  such training needs). The reading to watch is the gap between own-DI and donor
  regret: a useful distance keeps its own-DI accuracy through other players' notes.
- **The other route stays open:** rebuilding the DI from the song (the other session's
  work on `poc/sound-model`) would let the judge itself work from a song.
