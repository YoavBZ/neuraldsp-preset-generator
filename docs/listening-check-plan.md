# Does a real ear pick well on the audition page?

Declared on 2026-10-05, before any trial is built. Revised on 2026-10-06 after a
second and a third independent review, still before any trial existed.

The shortlist measurement (`docs/song-only-shortlist-results.md`) found that a perfect
ear choosing among four generated presets lands closer than one preset: about 18%
closer than the template, and about 10% closer than the agent's own first choice (G1).
The product's ear is not perfect, and it listens through a shipped riff (another
performance), not the song's own part. This check asks whether the user's picks on
the page beat chance, and beat a listener who ignores the song and follows a fixed
taste for an amp or for drive.

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
- **Controls:** 4, two per sitting, one in each half, one through each riff. They check
  playback and attention, not use of the song: each pits one candidate against three of
  the other gain class, so the odd one out can be heard without the song.
  - **Gain classes,** read from the preset: high-gain is a drive pedal at 0.7 or more,
    or a PR12 (whose volume is its gain) above 0.75; clean is no drive pedal and the
    amp's volume at most 0.5. Anything between, and any preset made for a bass, has no
    class and is never used in a control.
  - **Parts:** one per song, clearing the same -10 dB floor, those outside the 16 first,
    each most exposed first. A part qualifies only if every other guitar track in its
    song's instrumental mix belongs to a part whose closest classed factory preset is
    of the same class, so a cue that points the ear at the wrong guitar still finds the
    right class. Three parts outside the 16 qualify (First Offering GTR 1, Gym Hours
    GTR 2, Sculptor's Request GTR 1, at -7.8 to -8.9 dB); the fourth is a part under
    test, Farthest Step GTR (-1.9 dB), the only guitar in its mix.
  - **Candidates:** the part's closest unused classed factory preset, against the three
    farthest of the other class that are each more than 0.5 (log) farther under both
    band sets, through the part's own DI, from the stored panels. The correct answer
    is 2.0 to 3.7 times closer than its wrong ones.
  - No factory preset serves twice across the controls and the practice trial.
- **Practice:** one trial first, on the most exposed part left that is neither under
  test nor a control (Today's The Day ElecGtr10, -8.8 dB), with each amp's closest
  unused factory preset and one more clean one. The page marks it "Practice, not
  scored".
- **Sittings:** two, about 25 minutes, 20 trials each. Controls are placed last, so
  their halves hold whatever else is inserted.
  - The 32 main trials are split evenly by part, each sitting holding one riff of half
    the parts and the other riff of the rest.
- **The page:** for each trial, the instrumental mix excerpt, then A–D through the
  trial's riff, all at one loudness.
  - It carries no amp, preset name, note or path.
  - It is built in a private folder; only the stripped page and letter-named clips go
    to the listener's folder (`listen/`), and a check fails the build if that folder
    names an amp, G1–G4, `.xml`, or any preset on trial by name.
  - Every clip gets fresh dither (one 16-bit step), so a repeat's files never match its
    original's byte for byte.
- **The answer:** "Which of A–D sounds most like the guitar in the song?" One letter, or
  "?" for "can't tell", for every trial including the practice, one line per sitting,
  exactly as the page shows: `Sitting 1: 1A 2C 3? 4B` and so on.
  - `check-sheet` reads the sheet against the trial numbers on the public pages (which
    reveal nothing of the key) before its SHA-256 is committed. If it fails, the
    listener rewrites the sheet from their own notes, changing only its form, and it is
    checked again.
  - `score` refuses a sheet with any other line, a malformed answer, a trial answered
    twice, or a built trial unanswered or extra.
- **Before anything is rendered,** `build` checks the inputs, the shortlist renders
  index, the factory-preset panels, every generated and factory preset against the
  hashes they were scored with, and that the plugin still renders what the judge
  scored. It re-renders the first part's four candidates through its own DI, and every
  judge distance must be within 0.01 (log) of the inputs'. Fresh renders differ from
  the stored ones sample by sample (about 10% RMS on three parts tried), while the
  judge's distances agreed to three decimals.
- **Conduct:**
  - `build` prints the key's SHA-256; it is committed before sitting 1, and `score`
    refuses any other key. `score` also re-checks every clip against the key.
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
- **Primary: the ear follows the song,** when both of these hold under both band sets,
  each at one-sided p < 0.05 on the sum of c over the 32 main trials, by 10^6 Monte
  Carlo draws (4^32 picks cannot be enumerated). A "can't tell" stays 0 in both.
  - **It beats chance:** the null redraws each trial's pick uniformly from its four.
  - **It beats a song-blind taste:** the null redraws each trial's pick from its four in
    proportion to how often the listener picked that candidate's class when it was
    offered, over the 32 trials. A class is the amp and whether a drive pedal is on
    (six classes, 9 to 14 candidates each).
  - Why both: the judge's best is a PR12 on 11 of 16 parts, and was validated only on
    the PR12. In simulation, a listener who ignores the song and always picks a PR12
    passes the chance test 98% of the time, and one who always picks a preset without
    drive 83%. Neither passes the taste test more than 5% of the time (table below).
- **Inconclusive,** which overrides the primary:
  - more than 8 "can't tell" answers among the 32 main trials (25%), or
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
- **Power and size,** simulated from the stored distances and classes, 1,000 listeners
  each, how often the primary passes:

  | Listener | Chance test alone | Primary (chance and taste) |
  |---|---|---|
  | Picks at random | 0.04 | 0.01 |
  | Ignores the song, always a PR12 | 0.98 | 0.03 |
  | Ignores the song, always no drive | 0.83 | 0.05 |
  | Picks the judge's best 20% of the time beyond chance | 0.36 | 0.14 |
  | … 30% | 0.58 | 0.29 |
  | … 40% | 0.80 | 0.50 |
  | … 60% | 0.98 | 0.86 |

  The taste test costs power: a fail reads "not shown", never "the ear can't".
- **Reported, not deciding,** each under both band sets, over all 32 trials, per riff,
  and split at the median gap between the part's DI loudness and the riffs' (-23.7
  LUFS). The DIs span -32.0 to -10.7 LUFS, so through a riff some candidates sound
  cleaner, and some dirtier, than in the scored renders.
  - The share of the perfect-ear gain captured, in aggregate: Σc / Σ(best - mean), in
    log. Not a median of per-trial ratios, which is unstable where the best candidate
    is barely below the mean.
  - Σc split in two: the part carried by choosing the class (the mean log d of the
    pick's class among the four, less the mean of all four) and the part carried by
    the choice within the class.
  - How often the pick is the judge's best (chance 25%; exact one-sided binomial p, a
    "can't tell" counting as a miss).
  - On candidate pairs the judge separates by more than 0.15 (log) that include the
    pick, the share where the pick is the closer one. Its randomization p, by the
    chance null, is for the net count: the pairs the pick wins less those it loses.
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
- **The taste null is estimated from the same answers:** the class weights are the
  listener's own pick rates. In simulation this kept a random picker under 5% (above).
- **Which guitar is meant:** the cue names a track and how it plays, and every target
  is quieter than the rest of its mix (-1.1 to -8.1 dB). A listener who follows the
  wrong guitar loses power in the main trials; the controls are chosen so it cannot
  change their answer.
- **A control on a part under test:** Farthest Step GTR is both, so its control
  plays the same excerpt as two main trials, with factory presets, not G1–G4.

## Inputs, fixed before any trial

`research/listening_check.py inputs` wrote `docs/listening-check-inputs.json`: the
parts, cues, presets and their hashes, each candidate's taste class, each part's DI
loudness, the G1 rule's chance pass rate, the controls, the practice part, the factory
presets' hashes, and every candidate's judge distance. Its
SHA-256 is
`3cee9a075fbcfd2d94ce0a2efd2790e5d0c589b47752e641896bbd75a926ae98`. `build` refuses any
other file.
