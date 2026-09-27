# Real-amp validation recordings, and the split between development and held-out

Everything measured so far rests on two songs played by one player: How Long and
Hotel California. Their DIs were the inputs to every benchmark and their
listening rounds informed every decision in `tone-matching-plan.md`, so results on
them cannot show that matching works in general, and every benchmark target was
the plugin's own render rather than a real amplifier. This file declares a new
set of recordings — guitar parts recorded through real amps with a DI of the same
take, most of them with the rest of the band — and, before any matching or
benchmark result exists on them, which parts may be used to develop and tune the
tools and which are held out to test them. The declaration time is when this file
reaches `main` on GitHub.

## Sources

None of the audio is in this repository: the licences allow educational and
research use, not redistribution. The files live in
`~/ndsp-presets/references/datasets/`, and `validation-datasets.json` pins every
one of them by SHA-256 so a result can be tied to exactly these bytes.

- **Telefunken "Live From The Lab", Season 6** — Rebecca Haviland & Whiskey
  Heart, three songs recorded live: "57 Chevy", "Bourbon", "Collide With Me".
  Each has two electric guitars, each captured by a TDP-1 DI and two microphones
  on its amp (M80, TF11), plus drums, bass (DI and amp), Leslie organ and vocals.
  Terms: home-studio and educational use only, no commercial use, attribution to
  Telefunken ([livefromthelab](https://www.telefunken-elektroakustik.com/livefromthelab/)).
- **Cambridge Music Technology "Mixing Secrets" library** — Chris Coltraine,
  "Heather Jane" and "That's How I Got To Memphis": amp tracks with a DI of the
  same take for most electric guitars (two of them double-tracked), plus drums,
  bass and vocals. Terms: free for educational purposes, no commercial use
  ([cambridge-mt.com/ms](https://cambridge-mt.com/ms/mtk/)). Coltraine records
  largely on his own; whether his "amp" tracks are mic'd amps or amp simulators is
  not stated.
- **Guitar-TECHS, `P3_music`** (Zenodo record 14963133, CC BY 4.0) — twelve short
  guitar-solo excerpts, a Sire T7 into an Orange CR-12 set flat, recorded as a DI
  and a close amp mic simultaneously. No band.

## Which parts count

A part is a guitar recorded both as a DI and through an amp. It is **usable** when
the loudness envelopes of the DI and the amp track (10 ms frames, whole length)
correlate at 0.8 or more within ±20 ms — the same take, kept in step. This was
measured on every part and is recorded in `validation-datasets.json`; it is the
only thing looked at so far besides lengths and levels. It excludes Heather Jane's
ElecGtr3 (0.65), Memphis ElecGtr2 and its double (0.54, 0.55: they agree at the
start and end and not between, so one side was re-edited) and Memphis ElecGtr1
(no DI). Cambridge's "Library of Mic Positions" electric guitar set, suggested
during the search, has no DI and is not used.

For each usable part:

- **the reference** is its amp track — for Telefunken the M80 microphone, with the
  TF11 as an alternate; for Cambridge and Guitar-TECHS the one amp track
- **the DI** is its own DI track, unedited, which makes every part a paired reamp:
  `paired_di` is the true regime whenever the reference is the amp track alone
- **the mix** of a session is the sum at unity gain of every track except the
  guitar DIs, as recorded; **the backing** for a part is that mix without the
  part's own amp tracks
- **an excerpt**, where one is needed, is the loudest 10 s of the reference at
  0.5 s steps, chosen from the reference alone

A double-tracked part (Cambridge's `…DT`) is a second take of the same guitar and
setting, so a part and its double count as one tone, not two. Guitar-TECHS is one
player, guitar and amp setting throughout: its twelve excerpts are twelve
performances of one tone.

## The split

Drawn with Python's `random.Random(20260927)`: one Telefunken song
(`choice` of the three), then one Cambridge song (`choice` of the two), then four
of the twelve Guitar-TECHS excerpts (`sample`):

| | development | held out |
|---|---|---|
| Telefunken | "Bourbon", "Collide With Me" (4 parts) | "57 Chevy" (2 parts) |
| Cambridge | "Heather Jane" (4 parts, two tones) | "That's How I Got To Memphis" (2 parts, one tone) |
| Guitar-TECHS | excerpts 01, 03, 04, 05, 07, 08, 09, 12 | excerpts 02, 06, 10, 11 |

That is 16 development parts and 8 held out. The held-out Guitar-TECHS excerpts
are new performances of a tone the development set contains, so they test less
than the held-out songs do.

**Development** parts may be used for anything: benchmarks, tuning, trying ideas,
and listening. **Held-out** parts are not used for any of that. They are used only
by a test declared in a committed file before it runs — its command, what it
measures and what result would mean what — and by prospective listening under the
same rule. A held-out part used once for such a test stays held out for the next
declared one; a held-out part used for anything else moves to development, and
this file says so.

Until now these recordings have been checked only for the pairing above, their
lengths and their levels. No match, benchmark or listening test has touched any
of them.
