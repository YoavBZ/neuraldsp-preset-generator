# Does a real ear pick well on the audition page?

Declared on 2026-10-05, before any trial is built. Revised on 2026-10-06 after a
second independent review, still before any trial existed.

The shortlist measurement (`docs/song-only-shortlist-results.md`) found that a perfect
ear choosing among four generated presets lands closer than one preset: about 18%
closer than the template, and about 10% closer than the agent's own first choice (G1).
The product's ear is not perfect, and it listens through a shipped riff (another
performance), not the song's own part. This check asks whether the user's picks on
the page beat chance.

## Material

- **Parts:** one per song of the shortlist measurement's 16 songs.
  - Each song's part is the one most exposed in its mix: the part's amp track's loudness
    minus the loudness of the rest of the instrumental mix (`backing_instrumental.wav`),
    over the 10-second crop.
  - All 16 clear a floor of -10 dB (they range from -8.1 to -1.1 dB).
  - The ranking uses no render or score. The "rest of the mix" is the song's other
    tracks: every one of the part's own amp tracks (both mics, on Telefunken and
    Cambridge sessions alike) is left out of it.
- **What the song is:** the crop's instrumental mix (`mix_instrumental.wav`): every
  track summed, vocals left out. The user found loud vocals made the earlier test hard;
  the product itself plays the real song.
- **Candidates:** the part's four generated presets, G1–G4, as the runs wrote them.
  Each is checked against the SHA-256 it was scored with before it is rendered.
- **Renders:** every candidate with the rule set R (time effects, gate, doubler,
  transpose and spring reverb off), as the judge scored them. So the listener compares
  what was scored, not reverb or delay. This differs from the product page, which plays
  presets whole.
  - Each part's candidates go through both shipped riffs (`chords`, `line`) in one
    fresh plugin process.
  - Each render must be non-silent and finite, and is bound by hash.
- **Cue:** each trial names the part as the session does (its track name) and says how
  it plays (the run's pace description). These describe the playing, nothing about
  tone.

## Trials

- **Main trials:** 32, each one part through one riff, with four candidates labelled
  A–D.
  - The letters are a shuffle drawn per trial from system randomness (so a repeat gets
    fresh letters). There is no seed; the mapping is kept only in a private key, which
    only the scorer reads.
- **Repeats:** 3 of sitting 1's main trials again, with fresh letters: two in sitting 2,
  one later in sitting 1 with at least two trials between. Their consistency (the same
  preset picked) is reported.
- **Controls:** 4, two per sitting, one in each half, one through each riff.
  - They are the four most exposed parts outside the 16 that clear the same -10 dB floor
    (-7.8 to -8.9 dB).
  - Each offers the part's closest factory preset not already used, against three of
    the opposite gain class (high-gain against a clean part, clean against a high-gain
    one), each more than 0.5 (log) farther under both band sets, the farthest first.
    The distances come from the stored panels, through the part's own DI. A gain-class
    difference is audible through any riff.
  - No factory preset serves twice across the controls and the practice trial.
- **Practice:** one trial first, on the most exposed part left (-10.3 dB), with each
  amp's closest unused factory preset and one more clean one. Not scored.
- **Sittings:** two, about 25 minutes, 20 trials each.
  - The 32 main trials are split evenly by part, each sitting holding one riff of half
    the parts and the other riff of the rest.
- **The page:** for each trial, the instrumental mix excerpt, then A–D through the
  trial's riff, all at one loudness.
  - It carries no amp, preset name, note or path.
  - It is built in a private folder; only the stripped page and letter-named clips go
    to the listener's folder (`listen/`), and a check fails the build if that folder
    names an amp, G1–G4, `.xml`, or any preset on trial by name.
- **The answer:** "Which of A–D sounds most like the guitar in the song?" One letter, or
  "?" for "can't tell", for every trial including the practice, one line per sitting,
  exactly as the page shows: `Sitting 1: 1A 2C 3? …`.
  - `score` refuses a sheet with any other line, a malformed answer, a trial answered
    twice, or a built trial unanswered or extra. The sheet's SHA-256 is committed
    before any key is read, so a slip cannot be mended afterwards.
- **Conduct:**
  - `build` prints the key's SHA-256; it is committed before sitting 1, and `score`
    refuses any other key.
  - The listener is given only the `listen/` folder.
  - The person running the session neither reads the key nor gives feedback.
  - A trial that fails technically (no sound, wrong page) is presented once more.
  - No result is looked at between sittings, and there is no early stopping.

## Scoring

Each candidate's distance is the judge's, through the part's own DI, from the
shortlist measurement's renders (`research/score_shortlists.py`'s scoring: the full
1.0–10 s window, the recorded lag less 52 samples, both band sets). These distances,
the controls, the practice part and each part's DI loudness are in
`docs/listening-check-inputs.json`, fixed before any trial is built (below).

- **Per trial:** c = log d(pick) - the mean of log d over the four. It is 0 in
  expectation under a random pick. A "can't tell" scores c = 0.
- **Primary: the ear beats chance** when, under both band sets, the sum of c over the 32
  main trials is below what a random pick gives, at one-sided p < 0.05. The null redraws
  each trial's pick uniformly from its four (a "can't tell" stays 0), by 10^6 Monte
  Carlo draws: 4^32 picks cannot be enumerated.
- **Inconclusive,** which overrides the primary:
  - more than 8 "can't tell" answers (25%), or
  - fewer than 3 of the 4 controls hit. A guessing listener reaches 3 by chance 5.1% of
    the time. A sitting that misses both its controls (void) always lands here.
  An inconclusive check is declared again with fresh trials, after a playback check.
- **The decision rests on the primary alone.** The rule first declared, "the median of
  log(d(pick) / d(G1)) is at most 0 under both band sets", passes for a random picker
  99.3% of the time on this material (`g1_rule_chance_pass` in the inputs). G1 ranks
  2.8 of 4 on average (the worst on 6 of the 16 parts under the recording band set, 5
  under union), so a random pick is already about as close as G1: the median over parts
  of the four's mean log d less G1's is -0.010 (recording) and -0.015 (union). The rule
  cannot tell an ear from chance, so it is reported, not deciding. For the same reason,
  on this material an ear that beats chance also beats what G1 would deliver.
- **Power,** simulated in review from the measured distances, at one-sided p < 0.05:

  | Listener picks the judge's best this often, beyond chance | 0.2 | 0.3 | 0.4 |
  |---|---|---|---|
  | 16 trials | 0.22 | 0.36 | 0.54 |
  | 32 trials (this check) | 0.37 | 0.61 | 0.80 |

  So a fail reads "not shown", never "the ear can't".
- **Reported, not deciding,** each under both band sets, over all 32 trials, per riff,
  and split at the median gap between the part's DI loudness and the riffs' (-23.7
  LUFS). The DIs span -32.0 to -10.7 LUFS, so through a riff some candidates sound
  cleaner, and some dirtier, than in the scored renders.
  - The share of the perfect-ear gain captured, in aggregate: Σc / Σ(best - mean), in
    log. Not a median of per-trial ratios, which is unstable where the best candidate
    is barely below the mean.
  - How often the pick is the judge's best (chance 25%; exact one-sided binomial p, a
    "can't tell" counting as a miss).
  - On candidate pairs the judge separates by more than 0.15 (log) that include the
    pick, the share where the pick is the closer one, with a randomization p by the same
    null.
  - The median over trials of log(d(delivered) / d(G1)) and of log(d(delivered) /
    d(template+R)), where a "can't tell" delivers G1, the product's default.
  - The repeats' consistency, each control, the void sittings, and the "can't tell"
    count.

## What follows

| Inconclusive | Primary holds | Then |
|---|---|---|
| no | yes | the page is generate's main path: offer four and let the user choose |
| no | no | the page stays an option, and a declared own-DI sitting follows (below) |
| yes | — | the check is declared again with fresh trials, after a playback check |

**Own-DI follow-up** (declared now, run only if the primary fails). The same trials,
through each part's own DI instead of a riff. These renders already exist, from the
shortlist measurement. If own-DI passes, the riff, or its level, is the bottleneck; if
it fails too, the ear or the judge is.

## Limits

- **16 parts, one listener:** development material, mostly clean. The listener has
  heard several of these amp tracks in the earlier test.
- **The judge:** listening validated it only for clear clean-to-crunch PR12
  differences. These candidates span amps and are often closer than that.
- **G1 here:** G1 is no better than a random pick on this material, which is why
  beating chance is enough to beat it. That may not hold where the agent's first choice is better.
- **The song:** an instrumental unmixed sum, not a mastered song.
- **Renders with R:** this tests the ear on what was scored, not the product page's
  full presets.
- **Blinding is procedural:** the public inputs name every preset, so a listener who
  rendered them could match the clips. The listener here does not.

## Inputs, fixed before any trial

`research/listening_check.py inputs` wrote `docs/listening-check-inputs.json`: the
parts, cues, presets and their hashes, each part's DI loudness, the G1 rule's chance
pass rate, the controls, the practice part, and every candidate's judge distance. Its
SHA-256 is
`2d313ecc292da9d92995774120b10450d2992232e2bc9ff229c16090d16007cb`. `build` refuses any
other file.
