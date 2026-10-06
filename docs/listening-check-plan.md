# Does a real ear pick well on the audition page?

> **Amended on 2026-10-06, before any answer was given.** The first build (commit
> 6787638, key SHA-256 `dec7547a…c67f`, set aside at
> `~/ndsp-presets/runs/listening-check-set-aside-1/`) played every part through both
> riffs. Listening to part of sitting 1, the listener pointed out that a song whose
> guitar plays single notes cannot be matched to candidates strumming chords: drive
> sounds different on several notes at once. No answers were recorded, and that build
> is never scored. In its place, each part is classified as strummed chords or single
> notes from its own clean recording, before any trial is built, and heard twice
> through the riff in its own style (below). The style rule was set after seeing the
> parts' measured shares, but without looking at any judge distance or answer. The
> listener has heard part of the set-aside sitting 1: the same parts and candidates,
> with other letters.
>
> **Built on 2026-10-06** from commit a06b27c (inputs `26e3d0e6…bfdb1`): 37 trials in two
> sittings at `~/ndsp-presets/runs/listening-check/`. Committed before sitting 1: the
> key's SHA-256 `f185d8d441ce3890f8fb678d95eac2c8272f56d4609d443960a01eaa4f052a4b`, and
> the phone pages' `6d8a5a6adde26d18971c06b1e576d97d502cdcd80b53cefbe90f3b056e9f5d7e`
> (sitting 1) and `ebaedefc7d4811ee8e948f717b4f109584947983859d92e4fe665149776b37a1`
> (sitting 2).
>
> **Played on a phone,** at the listener's request: `listening_check.py phone-page`
> builds one self-contained page per sitting from the listener's folder alone (never
> the key), each clip encoded as mono AAC at 160 kbps (to stay under a 30 MiB
> attachment), with tap-to-answer buttons that assemble the answer line.

Declared on 2026-10-05, before any trial is built. Revised on 2026-10-06 after a
second to eighth independent reviews: before the first build, and then, as amended
above, after it was set aside and before any answer.

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
    fresh plugin process; a trial plays the one in the part's style.
  - Each render must be non-silent and finite, and is bound by hash.
- **Cue:** each trial names the part as the session does (its track name) and says how
  it plays (the run's pace description). These describe the playing, nothing about
  tone.

## Trials

- **Style:** each part's clean recording is classified before any trial is built. In
  every active frame, notes are counted (the strongest fundamental from A1 to C#6 by
  its harmonic sum,
  its harmonics removed, repeated while one keeps a quarter of the first's strength);
  the part's chord share is the share of frames with three or more. The riffs measure
  0.909 (chords) and 0.026 (line), and a part plays through the riff whose share is
  nearer: chords at 0.47 or more. 9 parts play chords, 7 the line.
  - **Reported apart, 6 parts:** the 5 within 0.15 of the split (0.37 to 0.59: mixed
    or two-note parts), and any part of two-note shapes, whose frames hold two notes
    or more 90% of the time or more while its chord share falls on the line side:
    Sculptor's Request GTR 2, played in fourths (0.24, and two notes or more in every
    frame). An octave reads as part of the lower note, so double stops and power
    chords read as two notes, under the three-note mark.
- **Main trials:** 32: each part twice, once in each sitting, through its style's
  riff, with four candidates labelled A–D.
  - The letters are a shuffle drawn per trial from system randomness, so a part's two
    showings have fresh letters. There is no seed; the mapping is kept only in a
    private key, which only the scorer reads.
  - Whether a part's two picks name the same preset is reported.
- **Controls:** 4, two per sitting, one in each half, each through its style's riff
  (three chords, one line). They check
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
    is 1.7 to 3.7 times closer than its wrong ones.
  - No factory preset serves twice across the controls and the practice trial.
- **Practice:** one trial first, on the most exposed part left that is neither under
  test nor a control (Today's The Day ElecGtr10, -8.8 dB), with each amp's closest
  unused factory preset and one more clean one. The page marks it "Practice, not
  scored".
- **Sittings:** two, about 23 minutes: 19 trials in sitting 1 (with the practice), 18
  in sitting 2. Each holds every part once, in its own shuffled order. Controls are
  placed last, so their halves hold whatever else is inserted.
- **The page:** for each trial, the instrumental mix excerpt, then A–D through the
  trial's riff, all at one loudness.
  - It carries no amp, preset name, note or path.
  - It is built in a private folder; only the stripped page and letter-named clips go
    to the listener's folder (`listen/`), and a check fails the build if that folder
    names an amp, G1–G4, `.xml`, or any preset on trial by name.
  - Every clip gets fresh dither (one 16-bit step), so a part's two showings never
    match byte for byte.
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
  index, the factory-preset panels, every generated and factory preset, and every song
  excerpt and DI, against the hashes fixed in the inputs. Then it checks that the plugin still renders what the
  judge scored. It re-renders the first part's four candidates through its own DI, and every
  judge distance must be within 0.01 (log) of the inputs'. Fresh renders differ from
  the stored ones sample by sample (about 10% RMS on three parts tried), while the
  judge's distances agreed to three decimals.
- **Conduct:**
  - `build` prints the key's SHA-256; it is committed before sitting 1, and `score`
    refuses any other key. `score` also re-checks every clip against the key.
  - The listener is given only the `listen/` folder.
  - A build that fails leaves its folder, and `build` refuses a non-empty one. The
    folder may be moved aside and the build rerun only if nothing from it reached the
    listener.
  - Every clip, the song and the candidates alike, is mono, so one loudness means one
    loudness.
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
  - **Drawn by part:** a part's two trials offer the same four presets, so they are
    not independent. Each null draws the part's pair of picks from its distribution
    given whether the two picks agree: one preset counted twice when they agree (in
    proportion to the product of the two trials' weights), an ordered pair of distinct
    presets when they differ (in proportion to the first trial's weight for one and the
    second's for the other). A part with one answer draws once.
  - **It beats chance:** each draw is uniform over the four.
  - **It beats a song-blind taste:** each draw follows a taste fitted to the listener's
    own answers, without the song or the judge, separately for the parts heard through
    each riff (18 answers on chords, 14 on the line, so a taste that changes with the
    riff is modelled too): a conditional logit (ridge 0.5) over each preset's amp (PR12, SW50R, AC20), whether a drive pedal is on, the amp's volume
    and the highest drive level (both standardised over all 64 candidates), and, within
    the part, the volume's and the drive level's ranks and whether each is the part's
    lowest. The within-part features let it follow a taste for "the least gain of these
    four", which a straight line over the raw levels could not.
  - Why both: the judge's best is a PR12 on 11 of 16 parts, was validated only on the
    PR12, and is the least-gain candidate on 8. A listener who ignores the song and
    always picks a PR12, a preset without drive, or the least gain passes the chance
    test often, and the taste test rarely (table below).
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
- **Power and size,** simulated by `research/listening_check_power.py` with the scoring
  code's own functions, from the stored distances and features: 800 listeners each,
  2,000 draws per p, seeded, so both fits see identical listeners. How often each test
  passes under both band sets (the script's docstring defines each listener):

  | Listener | Chance test alone | Primary, taste fitted per riff (declared) | Primary, one fit over all answers |
  |---|---|---|---|
  | Picks at random | 0.04 | 0.01 | 0.02 |
  | Picks at random, the same preset both times | 0.05 | 0.01 | 0.01 |
  | Ignores the song, always a PR12 | 0.77 | 0.00 | 0.00 |
  | … a PR12 half the time | 0.28 | 0.02 | 0.02 |
  | Ignores the song, always no drive | 0.41 | 0.00 | 0.03 |
  | Ignores the song, always the least gain | 1.00 | 0.00 | 0.00 |
  | … the least gain half the time | 0.33 | 0.03 | 0.04 |
  | … the least gain 70% of the time | 0.54 | 0.03 | 0.05 |
  | Ignores the song, leans to low gain | 0.61 | 0.00 | 0.01 |
  | Ignores the song, the least gain on chords parts and a PR12 on line parts | 0.84 | 0.00 | 0.14 |
  | … the least gain on chords parts and random on line parts | 0.44 | 0.03 | 0.03 |
  | Picks the judge's best 20% of the time beyond chance | 0.35 | 0.11 | 0.15 |
  | … 30% | 0.57 | 0.19 | 0.26 |
  | … 40% | 0.80 | 0.37 | 0.47 |
  | … 60% | 0.99 | 0.71 | 0.80 |

  Now that a riff is tied to a part's style, fitting the taste per riff fits it within
  each style's 7 to 9 parts, and that costs power (0.37 against 0.47 at 40%). It is
  kept because it holds every taste tried to 0.03, where one fit lets a taste that
  changes with the style pass 0.14. The ear model assumes the same accuracy as before;
  the matched riffs are meant to make a real ear more accurate than that.
  The taste test costs power: a fail reads "not shown", never "the ear can't".
- **Reported, not deciding,** each under both band sets, over all 32 trials, per style,
  for the parts of a clear style and those whose style is unclear, and split at the median
  gap between the part's DI loudness and the riffs' (-23.7
  LUFS). The DIs span -32.0 to -10.7 LUFS, so through a riff some candidates sound
  cleaner, and some dirtier, than in the scored renders.
  - The share of the perfect-ear gain captured, in aggregate: Σc / Σ(best - mean), in
    log. Not a median of per-trial ratios, which is unstable where the best candidate
    is barely below the mean.
  - Σc split in two: the part carried by choosing the amp and whether a drive is on (the
    mean log d of the candidates sharing the pick's amp and drive state, less the mean
    of all four) and the part carried by the choice among those.
  - How often the pick is the judge's best (chance 25%; exact one-sided binomial p, a
    "can't tell" counting as a miss).
  - On candidate pairs the judge separates by more than 0.15 (log) that include the
    pick, the share where the pick is the closer one. Its randomization p, by the
    chance null, is for the net count: the pairs the pick wins less those it loses.
  - The median over trials of log(d(delivered) / d(G1)) and of log(d(delivered) /
    d(template+R)), where a "can't tell" delivers G1, the product's default.
  - Whether each part's two picks name the same preset, each control, the void
    sittings, and the "can't tell" count.

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
- **Two styles only:** the riffs are strummed chords and a single-note line. Parts in
  between (mixed, or double stops and power chords) get the nearer one, and are
  reported apart. The style measure was checked on the two riffs and on synthetic
  tones, not against a listener's labels. It reads two-note shapes as two notes, which
  is why they are reported apart. Its range starts at A1, so drop tunings to A1 read
  correctly; a single note below A1 would read as several.
- **Renders with R:** this tests the ear on what was scored, not the product page's
  full presets.
- **Blinding is procedural:** the public inputs name every preset, so a listener who
  rendered them could match the clips. The listener here does not.
- **The taste null is estimated from the same answers,** and covers only the features
  it is given. Every taste in the table passes at most 0.03. In review, tastes the features miss, for brightness or for
  the cleanest-sounding clip, passed at most 0.003, but a taste nobody simulated is not
  ruled out.
- **A song-swapped arm** (one of each part's trials played against another song)
  would control every taste exactly. Simulated in an earlier draft, it reached 0.33 at
  40% if picks against the wrong song are random, and 0.13 if they still partly follow
  the right part's best, against 0.37 here, so this check models the tastes instead.
- **Gain classes for controls** ignore the amps' input gain and the SW50R's input mode.
  The chosen controls' clean answers have the input gain at 0 or cut.
- **Which guitar is meant:** the cue names a track and how it plays, and every target
  is quieter than the rest of its mix (-1.1 to -8.1 dB). A listener who follows the
  wrong guitar loses power in the main trials; the controls are chosen so it cannot
  change their answer.
- **A control on a part under test:** Farthest Step GTR is both, so its control
  plays the same excerpt as two main trials, with factory presets, not G1–G4.

## Inputs, fixed before any trial

`research/listening_check.py inputs` wrote `docs/listening-check-inputs.json`: the
parts, cues, presets and their hashes, each candidate's taste class and features, each
part's DI loudness, the G1 rule's chance pass rate, the controls, the practice part,
the factory presets' hashes, the song excerpts' and DIs' hashes, and every candidate's
judge distance. Its SHA-256 is
`26e3d0e644ded41d52bdccf9b3d594919acc163b9f58b6702e27a9b6188bfdb1`. `build` refuses any
other file.
