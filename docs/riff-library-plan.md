# Riffs in the part's style and register: plan

Declared 2026-10-15, before any riff is cut. Roadmap, product steps (parked: "riffs in
the part's style and register").

## Why

The listening page plays each candidate preset through a shipped clean DI riff, since the
user never gives a DI. Two riffs ship, both low on the neck: a strummed G–D–Em–C
progression and an A-scale line. Two lessons say that is not enough:
- **Style.** The listener could not judge a single-note part through strummed chords
  ([listening check](listening-check-results.md)).
- **Register.** In the Cut It Out run a high lead heard through the low riff favoured the
  wrong preset; through a line in the part's register it flipped
  ([reading a reference](../reference/reading-a-reference.md)).

A cloud research pass (`docs/research/di-riffs-and-part-classifier-2026-10.md` on the
researcher's branch, verified locally where it matters) found the material is already
on disk: Guitar-TECHS (Zenodo 14963133, CC BY 4.0, licence read from the record),
players P1 and P2, has chords moving chromatically up the neck to the 12th fret and
scales in every key, with per-string MIDI. Part P3 stays unused: it is validation
material (`research/build_riffs.py`). No download is needed.

## What ships

Six riffs, each about 10 s, from P1's direct input (the player the two current riffs
come from), cut, faded and levelled as `research/build_riffs.py` does now (-23.7 LUFS,
24-bit FLAC, every cut and source hash in `riffs.json`, whose schema version goes up):

| name | style | register | made of (from the MIDI; the builder confirms) |
|---|---|---|---|
| `chords` (existing) | strummed chords | low | G–D–Em–C, `Set4` voicings (median about D3); rebuilt 2026-10-17 from EGFxSet open chords (median G3), see "Rebuilt" |
| `chords-mid` | strummed chords | mid | the same progression in `Set2` voicings (median about E4; `Set3` measures low); D is the exact `Set2` strum at 55.9 s (the non-exact mid D strums carry an A#); rebuilt 2026-10-17 from EGFxSet four-string voicings at frets 5-10 (median F4) |
| `chords-high` | strummed chords | high | the same progression on the top three strings (`Set1`, frets 10–13; medians about B4–C5) |
| `line` (existing) | single-note line | low | the A scale from its start (median A3) |
| `line-mid` | single-note line | mid | a mid position of a scale (e.g. A, about 65–75 s) |
| `line-high` | single-note line | high | the top positions of a scale (e.g. A, about 140–150 s; median about C#5) |

**Register** is the median MIDI pitch of all notes in the cut, chords and lines alike,
allowing for a stray tracking note: **low below C4, mid C4 to A4, high above A4**
(contiguous). The builder prints each chosen strum's notes and each cell's median and source before any audio is cut,
and refuses a cell whose median falls outside its bucket. A cell P1 cannot fill exactly
(mid D has no exact triad) uses the builder's non-exact fallback, or P2, recorded in
`riffs.json`. The two existing riffs are not re-encoded: the builder checks their stored
hashes and leaves them as they are.

Not filled: power chords and riffs, and arpeggios (no shippable source; the research's
cheapest fix is the user recording a few and releasing them CC0).

## How `generate` uses them

Step 5b picks **at most two** riffs per page, without any new analysis tool:
- a part research documents as rhythm or chords: `chords` (low), plus `chords-mid` or
  `chords-high` only if research places it there;
- a lead, solo or melody: `line-mid`, plus `line-high` (or `line`) only if research
  places it there;
- unknown style (mixed parts, arpeggios, power-chord riffs): `chords` + `line`, as now.

`audition.py` keeps its default of the two existing riffs (a `default` flag in
`riffs.json`), so a page never renders six riffs unasked; `--riff` takes the new names.
Step 5b's text ("two short guitar riffs", the render-time note) is updated.

No automatic chord or register detection ships now: no open tool is proven on separated
guitar stems (the research's finding). That stays parked behind a cheap local check
(ear labels against Basic Pitch), which needs a pip install.

## Docs that change

`NOTICE.md` and `README.md` ("two guitar riffs", "part P1"), the builder's docstring
(and its attribution if P2 is used), `generate` step 5b, and the roadmap's parked reason
("needs a download" is wrong: the material is on disk).

## Checks

- Unit tests: `riffs.json` lists every riff with style, register and the default flag;
  each riff's median pitch from its own MIDI cut falls in its declared bucket (one stray
  note allowed); levels within 0.1 LU of the target; the two existing riffs' hashes
  unchanged.
- `test_skills.py` runs the documented `audition.py --riff …` commands.
- One check page (6 riffs through 2 presets, 12 renders in fresh processes), run with
  the ML session's go (given 2026-10-15) and outside 03:00–04:15, for the user to hear
  each riff is clean and in its register.

## As built (2026-10-15)

- `line-high` is the E scale from 143.5 s (median D5): no 10-s window of the A scale
  reached high (the best, from about 145 s, would run past the file). A scan of every
  key's MIDI chose it.
- `chords-high` measures A#4, one semitone above the edge: two short tracked notes in
  the Em strum (C#4, D4) pull the median down; in the audio they sit about 30 dB below
  the chord tones (transcription artefacts), and without them it is B4.
- Each riff's median pitch and note range are recorded in `riffs.json` and tested.

## Checked by ear (2026-10-17)

The check page (6 riffs through an edge-of-breakup and a crunch preset) confirmed every
register. The lines and `chords-high` sounded clean; `chords` and `chords-mid` did not:
clicks and low crackle through the edge-of-breakup preset, hidden by the crunch.

## Rebuilt (2026-10-17)

What the noises were, each found by measurement and confirmed or ruled out by ear:

- **Clicks** in two `chords-mid` strums (G, D): broadband impulses in P1's recordings.
  Swapping in other P1 strums removed them.
- **Crackle** left in both riffs: fret buzz in P1's low voicings, periodic with the
  note pitch (absent from the `Set1` top-string voicings, which is why `chords-high` is
  clean). P1 also carries a 60 Hz mains spike train, but after the amp it sits about
  30 dB under the decay, so it was not the cause. P2's takes buzz less but carry about
  20 dB more hiss; by ear neither player was good enough.
- So both riffs are now assembled from **EGFxSet**'s Clean set (Zenodo 7044411, CC BY
  4.0): a Stratocaster, every string and fret recorded on its own, middle pickup (the
  quietest of its five). Low: open G, D, Em, C. Mid: four-string voicings at frets 5-10.
  Each step below answered something heard on a check page:
  - strings 25 ms apart (12 ms sounded too fast for a strum);
  - noisereduce, non-stationary, above 3 kHz only (hiss under crunch; the decays lose
    16-19 dB of hiss, the attack about 1 dB of top, the level nothing; stationary mode
    took 9 dB off the low notes);
  - a down-up strum per chord (the upstroke 1.25 s in, 3 dB softer) and a 150 ms mute
    before the next (a crunch amp crackles as a chord rings down to near silence);
  - every note retuned to equal temperament (the separate recordings disagree by up to
    15 cents; the octaves in both Em voicings beat, heard as "shaky" and a rumble
    under drive);
  - every chord equally loud (the open Em, six strings with four open, broke up the
    edge-of-breakup preset first).
- Heard and accepted on 2026-10-17 through both presets. On the build machine the build
  reproduces the approved audio sample for sample (noisereduce and scipy versions can
  change that elsewhere; a riff matching its record is never re-encoded) (`chords-mid` with even chords was not re-heard; its
  chords were within 0.4 dB of each other already). The Hotel California "clean start"
  preset used for the checks is really edge of breakup, which is where the remaining
  low-Em breakup came from.

## Limits

`chords-high` and the lines are one player and one guitar (P1's bridge pickup on an
Ibanez PF-300, which leans dark); `chords` and `chords-mid` are one Strat, assembled
note by note, so the strings do not interact as in a played chord. Under a crunch preset
some hiss is still audible. The riffs are not the song's part; this only reduces two
known mismatches.
