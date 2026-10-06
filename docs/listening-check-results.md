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
  Offering GTR 1, Gym Hours GTR 2), 7.8 and 8.9 dB under the rest of the mix. Both of
  sitting 2's controls were answered, and both were hit.
- "Can't tell": 6 of the 32 main trials (the limit was 8), and 2 of the 4 controls.

## What the listener reported

Unprompted, after sitting 1 and before any result: "Some songs didn't include a
guitar or the song and the A-D had different notes/chords and couldn't be compared,
so I chose '?'". Earlier, on the set-aside first build, the listener had pointed out
that strummed chords can't be compared with a single-note part, which led to the
style-matched riffs. Together these are the clearest finding: **through a stock riff,
the listener often could not find the target guitar in the song, or could not
compare a tone across different notes.**

## Readings, reported only

The check was inconclusive, so none of these decides anything. Under the recording
and union band sets:

| Reading | Recording | Union |
|---|---|---|
| Σc over 32 main trials (log, lower is closer) | −1.35 | −1.99 |
| Chance test, one-sided p | 0.075 | 0.025 |
| Song-blind taste test, one-sided p | 0.32 | 0.23 |
| Share of the perfect-ear gain captured | 0.26 | 0.34 |
| …of which from choosing the amp and drive state | −1.09 | −1.69 |
| …of which from the choice within those | −0.27 | −0.30 |
| Picks of the judge's best (chance 8 of 32) | 10, p 0.26 | 10, p 0.26 |
| Median log(d(delivered) / d(G1)) | 0.00 | 0.00 |

- The picks lean closer than chance, but not under both band sets, and not at all
  once a song-blind taste for an amp, drive or gain is allowed for (p 0.23 to 0.32).
  Most of the gain comes from choosing the amp and drive state, which a taste could
  explain as well as an ear could.
- **Same preset both times:** 5 of the 12 parts answered on both showings (chance about
  3 of 12 for a random picker).
- **By style:** chords parts captured 0.30 / 0.38 of the perfect-ear gain, line parts
  0.20 / 0.28; neither passes either test alone.

## What follows

As declared, an inconclusive check is not a fail: the own-DI follow-up is not
triggered, and the page stays an option. Re-declaring the check unchanged would meet
the same two problems, so the next step is a decision, not a rerun:

- **Make the target findable:** controls, and perhaps main parts, only where the part
  is the song's only guitar or clearly its loudest.
- **Make the notes comparable:** the listener's report says tone through different
  notes is hard to judge. The declared own-DI follow-up (A–D play the part's own
  notes) would show whether the ear can match tone at all when the notes line up;
  it does not test what the product can offer from a song alone.
- **Or move on:** the roadmap's next step, a DI-free distance, does not depend on
  this check.

## Deviations

- The first build was set aside unanswered (see the plan's amendment).
- After the key was first read by `score`, the scorer was extended to list each
  control's trial, part and whether it was answered. Re-scoring reproduced every
  other number exactly.
