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

- **Every row is about as far from the judge's best as a random pick or the song-blind
  constant.** The best figure in any block, 0.30 (masked long-term spectrum, union,
  clean menu), is 0.83 times the constant's 0.36; the gate asked for 0.75.
- **No row beats the constant across bands.** Raw one-sided sign-flip p-values are
  0.18 to 0.42 for the closest rows (before Holm across the 8 rows, which takes all to
  1.0): each row wins in some bands and loses in others.
- **Agreement with the judge on the clean menu is low:** at most 0.38 (the two
  unmasked log-mel rows), against the gate's 0.6. v3 agrees at 0.01 and −0.03.
- **On stems (12 parts)** every row's regret is 0.34 to 0.57, again near the constant.

## Why: the rows hear the take, not the tone

**Own-DI share is 1.00 for every row in every block.** Given a mixed menu of each
candidate rendered through another player's DI and through the part's own DI, every
row picked an own-DI render, for every part and donor. These distances sit much closer
to anything that shares the take's notes, guitar and playing than to anything that
shares its tone: the performance swamps the preset. That is round 4's "main danger"
(the notes leaking in), measured. It is also why round 1 and round 4 point to features
trained to ignore the performance, not hand-made statistics.

## Reported, not deciding

- **Per amp** (recording, all): the rows' regret within one amp's presets ranges from
  0.23 to 0.57 across rows and amps.
- **Per band:** the spread is wide for every row (for the log-mel mean and spread,
  0.07 in one band to 0.59 in another), which is why no row beats the constant across
  bands.
- **Another teacher** (the average-guitar measure, branch `poc/sound-model`, on the 22
  clean PR12 candidates, half B): the rows' regret is 0.11 to 0.22, against 0.24 for a
  random pick on that menu (post-hoc reference point, computed after the run). The
  lean fingerprint does best (0.11 / 0.11). Under the judge's own half-B distance on
  the same menu, the rows' regret is 0.19 to 0.45, against 0.27 to 0.28 for a random
  pick. As declared, this cannot change the verdict; it says that on a narrow clean
  menu, under the average-guitar measure, simple spectra do better than chance, and a
  check under that measure, once it is confirmed and covers all three amps, would be
  worth declaring.
- **Empty distances:** none. One render (a preset through one donor's DI) is silent and
  was skipped.

## Deviations, all before any distance was computed

- The plan was revised after an independent review (anchoring the gate on the
  song-blind constant, band statistics, the clean menu, qualified stems, active donors,
  the masked and LDA rows), and amended after a review of the code (regret over the
  whole menu when a distance is empty, the stop deciding the answer, the stem
  tie-break).
- Two inputs turned out unmeasurable and were declared before the run: one silent
  render, skipped; and an empty loudness range on 325 of 4,773 renders, handled in the
  lean and LDA rows.

## What follows

- **Roadmap step 2 is not met by hand-made features.** The next candidates are an
  effects encoder (AFx-Rep, a 1.2 GB download that needs approval) and a contrastive
  encoder trained on the panels to ignore the performance (round 1, approach 3c: 2 to 3
  weeks, and the panels already hold every preset through 43 players' DIs, the pairs
  such training needs). The own-DI share is the reading to watch: a useful distance
  must stop preferring the take.
- **The other route stays open:** rebuilding the DI from the song (the other session's
  work on `poc/sound-model`) would let the judge itself work from a song.
