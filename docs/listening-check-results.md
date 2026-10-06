# Listening check of the audition page: results

Run on 2026-10-06 as declared in [listening-check-plan.md](listening-check-plan.md)
(amended the same day to match each part's riff to its playing style, before any
answer). One listener, two sittings on a phone, 37 trials. Scored by
`research/listening_check.py score`; the full output is
[listening-check-score.json](listening-check-score.json).

## Outcome: inconclusive

**Sitting 1 is void.** Its two controls were both answered "?", so it hit neither,
and only 2 of the 4 controls were hit, fewer than the declared 3. By the plan, the
check is inconclusive and the primary does not decide anything. The page stays an
option in `generate`, not its main path.

- Both missed controls were the second guitar of a two-guitar Telefunken song (First
  Offering GTR 1, Gym Hours GTR 2, 7.8 and 8.9 dB under the rest of the mix). Both of
  sitting 2's controls were answered and hit, and one of them, Sculptor's Request GTR 1,
  is the same kind of part and the quietest control (8.9 dB under).
- "Can't tell": 6 of the 32 main trials (the limit was 8), and 2 of the 4 controls.
  They cluster in sitting 1: 4 main and both controls there, with a run at trials 8,
  9, 10 and 12 (the controls were 9 and 12); 2 in sitting 2.
- "Can't tell" does not follow how exposed the part is: Signs ElecGtr2, the second
  most exposed part (1.4 dB under the mix), got "?" both times, while the two least
  exposed, Today's The Day ElecGtr07 and Quicksand ElecGtr1 (about 8 dB under), were
  answered both times. So the void sitting is not explained by quiet targets alone,
  and a cause specific to sitting 1, such as a stretch of playback trouble, is not
  ruled out. That is what the declared playback check is for.

## What the listener reported

Unprompted, after sitting 1 and before any result: "Some songs didn't include a
guitar or the song and the A-D had different notes/chords and couldn't be compared,
so I chose '?'". Earlier, on the set-aside first build, the listener had pointed out
that strummed chords can't be compared with a single-note part, which led to the
style-matched riffs. Together these say that, for some songs, the listener could not
find the target guitar or could not compare a tone across different notes. Which
trials those were is not recorded beyond the "?" answers above.

## Readings, reported only

The check was inconclusive, so none of these decides anything. Under the recording
and union band sets:

| Reading | Recording | Union |
|---|---|---|
| Σc over 32 main trials (log, lower is closer) | −1.35 | −1.99 |
| …from choosing the amp and drive state | −1.09 | −1.69 |
| …from the choice within those | −0.27 | −0.30 |
| Chance test, one-sided p | 0.075 | 0.025 |
| Song-blind taste test, one-sided p | 0.32 | 0.23 |
| Share of the perfect-ear gain captured | 0.25 | 0.34 |
| Picks of the judge's best (chance 8 of 32) | 10, p 0.26 | 10, p 0.26 |
| Clear pairs (> 0.15 log) won by the pick, net count p, against chance only | 0.69, p 0.050 | 0.75, p 0.019 |
| Median log(d(delivered) / d(G1)) | 0.00 | 0.00 |
| Median log(d(delivered) / d(template+R)) | −0.02 | −0.04 |

These include sitting 1's 16 main trials: a void sitting voids the decision, not the
data.

- The picks lean closer than chance, but not under both band sets, and not at all
  once a song-blind taste for an amp, drive or gain is allowed for (p 0.23 to 0.32).
  Most of the gain comes from choosing the amp and drive state, which a taste could
  explain as well as an ear could. The clear-pairs reading is the only one under 0.05
  on both band sets, but it is tested against chance only, not a taste, and overlaps
  Σc.
- **Same preset both times:** 5 of the 12 parts answered on both showings (chance about
  3 of 12 for a random picker; 5 or more by chance 0.16). Three of the five were the
  judge's closest candidate and two its farthest, so this fits a fixed taste as well
  as an ear.
- **By style:** chords parts captured 0.29 / 0.38 of the perfect-ear gain, line parts
  0.20 / 0.28; neither passes either test alone.
- **By DI level:** parts whose DI sits near the riffs' level captured 0.39 / 0.44 of
  the perfect-ear gain (chance p 0.072 / 0.061); parts with DIs hotter than the median
  gap 0.06 / 0.23 (p 0.39 / 0.15). This bears on whether the riff's level, not only its
  notes, limits the page.

## What follows

As declared, an inconclusive check is not a fail: the own-DI follow-up is not
triggered, and the page stays an option. **The declared consequence is to declare the
check again with fresh trials, after a playback check**, and that is the default. The
options:

- **The declared rerun** (default): fresh letters, a playback check before each
  sitting. It would show whether sitting 1's cluster of "?" was a playback or
  attention problem. Unchanged, it would still meet the listener's two reported
  difficulties.
- **A rerun with findable targets:** controls, and perhaps main parts, only where the
  part is its song's only guitar or clearly its loudest. The data above do not show
  quiet targets were the cause, so this alone may not help.
- **Comparable notes:** the declared own-DI follow-up (A–D play the part's own notes)
  would show whether the ear can match tone when the notes line up, and with the DI
  level split above, whether the riff's level matters. It does not test what the
  product can offer from a song alone.
- **Move on:** the roadmap's next step, a DI-free distance, does not depend on this
  check.

Departing from the declared rerun would be recorded here, with the reason.

## Deviations

- The first build was set aside unanswered (see the plan's amendment).
- After the key was first read by `score`, the scorer was extended to list each
  control's trial, part and whether it was answered. Re-scoring reproduced every
  other number exactly (an independent review re-ran the old scorer too).
- Chain of custody: the key's hash was committed and pushed before sitting 1, each
  answer sheet's hash after its sitting and before the next step, and the joined
  sheet's before `score` first ran (branch `listening-check-run`, commits ca5991a,
  41362fc, 8e695b8).
