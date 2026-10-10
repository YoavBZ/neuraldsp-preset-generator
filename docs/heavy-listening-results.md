# Listening check H (heavy tones): results

Taken 2026-10-10 by the user, in two phone sittings, as declared in
[heavy-listening-plan.md](heavy-listening-plan.md).
- **Hashes:** the answer sheets were hash-locked before the key was read (sitting 1,
  sitting 2, and the answers-only sheet `heavy-listening-answers.sha256`).
- **Amendment:** the plan was amended for unanswered trials, also before the key was
  read.
- **Score:** `heavy-listening-score.json`.

**Outcome: not void. Block 1 "neither", block 2 inconclusive.** 9 of 36 trials could
not be answered.

## Reliability: excellent

- **Hidden references:** 3 of 3 found.
- **Repeats:** all 3 answered the same way both times (with A and B swapped).

## The blocks (answered trials only)

| block | result | outcome |
|---|---|---|
| 1: tonal against temporal, where they disagree | tonal 5, temporal 8 of 13 (p 0.29 for temporal) | **neither**; leans temporal (drive and texture) |
| 2: clear heavy pairs (SW50R, AC20) | agrees with the judge on 5 of 6 (p 0.11) | **inconclusive**; 4 of 10 trials unanswered |
| 3: small differences (report only) | 1 of 2 | |

- **Block 1:** the ear doesn't clearly favour tone balance over drive and texture. The
  judge's sum stays, and aggregate differences under 0.10 count as ties.
- **Block 2:** what was answered agrees with the judge, but too few trials for a
  decision. The judge stays unvalidated by ear on heavy SW50R and AC20.

## The unanswered trials: broken low notes

The listener: "A & B sounded bad, almost only lower notes, which affected the
comparison" (sitting 1: "clipping?").
- **Not clipping.** Every clip peaks at −4.5 to −13.5 dBFS, also after the page's AAC
  encoding.
- **Not loudness-matching either.** At −22.9 LUFS the bass-heavy DIs sit at most about
  1.4 dB above a typical DI's RMS.
- **They are the low-tuned guitars:**
  - 7 of the 9 unanswered trials use DIs with 25–53% of their energy below 200 Hz:
    Burial Of Silence 3 and 4, Less Than Nothing, Split Brow, The Well 01;
  - only 3 of the 27 answered trials do;
  - the other two unanswered trials are Magilla ElecGtr2 (and its double) on PR12 and
    SW50R.
- **The likely cause.** Both options are menu presets through the same low-tuned DI. A
  heavy menu preset without a tight boost or a bass cut before the amp makes low notes
  flab and break up. The record's real rig almost certainly tightened them, as metal
  rigs do.
- **A product lesson as much as a measurement one.** For low-tuned heavy songs, the
  starting presets probably need a tightened low end, such as a drive pedal as a tight
  boost or a pre-amp bass cut. To be tested.

## What follows

- **Judge v3 against the current judge** gets the dedicated calibration round from the
  [v3 review](judge-v3-results.md): about 55 trials, headphones at a fixed level,
  rather than more of this check.
- **That round should leave out low-tuned material,** or include it only where the
  options were tightened, so that trials stay answerable.
- **A new candidate for a cheap product test:** a tight boost on the driven baseline for
  low-tuned songs, scored on development first.
