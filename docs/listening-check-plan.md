# Does a real ear pick well on the audition page?

Declared on 2026-10-05, before any trial is built. Revised the same day after an
independent review, still before any trial existed.

The shortlist measurement (`docs/song-only-shortlist-results.md`) found that a perfect
ear choosing among four generated presets lands closer than one preset: about 18%
closer than the template, and about 10% closer than the agent's own first choice.
The product's ear is not perfect, and it listens through a shipped riff (another
performance), not the song's own part. This check asks whether the user's picks on
the page beat chance and beat the default the product would otherwise deliver (G1).

## Material

- **Parts:** one per song of the shortlist measurement's 16 songs.
  - Each song's part is the one most exposed in its mix: the part's amp track's loudness
    minus the loudness of the rest of the instrumental mix (`backing_instrumental.wav`),
    over the 10-second crop.
  - All 16 clear a floor of -10 dB (they range from -8.1 to -1.1 dB).
  - The ranking uses no render or score. The "rest of the mix" includes the song's
    other guitars and, on Cambridge sessions, the part's own second mic.
- **What the song is:** the crop's instrumental mix (`mix_instrumental.wav`): every
  track summed, vocals left out. The user found loud vocals made the earlier test hard;
  the product itself plays the real song.
- **Candidates:** the part's four generated presets, G1–G4, as the runs wrote them.
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
  - The order is a shuffle seeded from system randomness, drawn per trial (so a repeat
    gets fresh labels).
  - The seed and the mapping are kept only in a private key, which only the scorer
    reads.
- **Repeats:** 3 of the main trials again, with fresh labels, spread across sittings.
  Their consistency is reported.
- **Easy controls:** 2, on shortlist parts not among the 16, taken in name order.
  - Each has one candidate the judge puts more than 0.5 (log) closer than the other
    three under both band sets: the part's closest factory preset, and the three nearest
    beyond that gap, all rendered with R. The distances come from the stored panels.
  - If a sitting misses both controls, it is void and is run again after a playback
    check.
- **Practice:** one trial first, on the next such part, with each amp's closest factory
  preset and one more clean one. Not scored.
- **Sittings:** two, about 25 minutes each.
  - The 32 main trials are split evenly by part, each sitting holding one riff of half
    the parts and the other riff of the rest.
  - Repeats and controls are spread over both sittings.
- **The page:** for each trial, the instrumental mix excerpt, then A–D through the
  trial's riff, all at one loudness.
  - It carries no amp, preset name, note or path.
  - It is built in a private folder; only the stripped page and letter-named clips go
    to the listener's folder, and a check fails the build if that folder names an amp,
    G1–G4, a preset or `.xml`.
- **The answer:** "Which of A–D sounds most like the guitar in the song?"
  - One letter, or "can't tell". The answer sheet's SHA-256 is committed before any key
    is read.
- **Conduct:**
  - The person running the session neither reads the key nor gives feedback.
  - A trial that fails technically (no sound, wrong page) is presented once more.
  - No result is looked at between sittings, and there is no early stopping.

## Inputs, fixed before any trial

`research/listening_check.py inputs` wrote `docs/listening-check-inputs.json`: the
parts, cues, presets, controls, practice part, and every candidate's judge distance.
Its SHA-256 is
`ab19294796fd3cabce5092e22853e803d3019f6678cfa5961e7d75c872b59a51`. `build` refuses any
other file.

## Scoring

Each candidate's distance is the judge's, through the part's own DI, from the
shortlist measurement's renders (`research/score_shortlists.py`'s scoring: the full
1.0–10 s window, the recorded lag less 52 samples, both band sets). The per-candidate
distances are computed and their file's SHA-256 committed before any trial is built.

- **Per trial:** c = log d(pick) - the mean of log d over the four. It is 0 in
  expectation under a random pick. A "can't tell" scores c = 0.
- **Primary: the ear beats chance** when, under both band sets, the sum of c over the 32
  main trials is below what a random pick gives, at one-sided p < 0.05. The null is
  exact: each trial's pick is redrawn uniformly from its four, by complete enumeration
  or 10^6 Monte Carlo draws.
- **The page becomes generate's main path** when the primary holds and, under both band
  sets, the median over the 16 parts of log(d(pick) / d(G1)) is at most 0. A part's two
  riffs count as two trials; the median is over trials.
- **Inconclusive:** more than 8 "can't tell" answers (25%), or a void sitting that
  can't be re-run.
- **Power,** simulated in review from the measured distances, at one-sided p < 0.05:

  | Listener picks the judge's best this often, beyond chance | 0.2 | 0.3 | 0.4 |
  |---|---|---|---|
  | 16 trials | 0.22 | 0.36 | 0.54 |
  | 32 trials (this check) | 0.37 | 0.61 | 0.80 |

  So a fail reads "not shown", never "the ear can't".
- **Reported, not deciding:**
  - The share of the perfect-ear gain captured: (pick - mean) / (best - mean), in log.
  - How often the pick is the judge's best (chance 25%, exact binomial p).
  - On candidate pairs the judge separates by more than 0.15 (log), the share where the
    pick is the closer one, against the same null.
  - Each reading per riff, and by the gap between the part's DI loudness and the riff's
    (-23.7 LUFS). Several DIs are 9–13 dB hotter, so candidates sound cleaner on the
    page than in the scored renders.
  - The pick vs the template (template+R), the repeats' consistency, the controls, and
    the "can't tell" count.

## What follows

| Primary holds | Pick vs G1 median ≤ 0 | Then |
|---|---|---|
| yes | yes | the page is generate's main path: offer four and let the user choose |
| yes | no | the ear beats chance but not the default here: the page stays an option, and the result is reported as such |
| no | — | the page stays an option, and a declared own-DI sitting follows (below) |

**Own-DI follow-up** (declared now, run only if the primary fails). The same trials,
through each part's own DI instead of a riff. These renders already exist, from the
shortlist measurement. If own-DI passes, the riff, or its level, is the bottleneck; if
it fails too, the ear or the judge is.

## Limits

- **16 parts, one listener:** development material, mostly clean. The listener has
  heard several of these amp tracks in the earlier test.
- **The judge:** listening validated it only for clear clean-to-crunch PR12
  differences. These candidates span amps and are often closer than that.
- **The song:** an instrumental unmixed sum, not a mastered song.
- **Renders with R:** this tests the ear on what was scored, not the product page's
  full presets.
