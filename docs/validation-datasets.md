# Amp-recorded validation material, and the split between development and held-out

Everything measured so far rests on two songs played by one player: How Long and
Hotel California. Their DIs were the inputs to every benchmark and their
listening rounds informed every decision in `tone-matching-plan.md`, so results on
them cannot show that matching works in general, and every benchmark target was
the plugin's own render rather than an amplifier. This file declares a new set of
recordings — guitar parts recorded through an amp with a DI of the same take, most
of them with the rest of the band — and, before any matching or benchmark result
exists on them, which of them may be used to develop and tune the tools and which
are held out to test them. The declaration time is when this file reaches `main`
on GitHub. A second set, added after the first set's held-out sessions had been
used once, is declared the same way in [its own section](#the-second-set).

## Sources and terms

None of the audio is in this repository. The files live in
`~/ndsp-presets/references/datasets/`, and `validation-datasets.json` pins every one
by SHA-256. `scripts/validation_datasets.py` rebuilds that file from the audio: the
hashes, the pairing measurements below and the split draw.

- **Telefunken "Live From The Lab", Season 6** — Rebecca Haviland & Whiskey Heart,
  three songs recorded live in one room: "57 Chevy", "Bourbon", "Collide With Me".
  Two electric guitars per song, each captured by a TDP-1 DI and two microphones on
  its amp (M80, TF11), plus drums, bass (DI and amp), Leslie organ and vocals;
  24-bit/48 kHz. Terms: "for the sole purpose of allowing individuals an
  opportunity to utilize them for home studio use and for educational purposes
  only"; no commercial use; any non-commercial reuse must carry: *All audio files
  have been engineered and recorded by TELEFUNKEN Elektroakustik and are presented
  for educational and demonstrational purposes only.*
  ([terms](https://www.telefunken-elektroakustik.com/livefromthelab/))
- **Cambridge Music Technology "Mixing Secrets" library** — Chris Coltraine, "Heather
  Jane" and "That's How I Got To Memphis": electric guitars with a DI of the same
  take for most of them, two double-tracked, plus drums, bass and vocals;
  24-bit/44.1 kHz. Terms (each session's readme): "provided for educational purposes
  only, and the material contained in them should not be used for any commercial
  purpose without the express permission of the copyright holders"
  ([library](https://cambridge-mt.com/ms/mtk/)). Coltraine records largely on his
  own; whether his amp tracks are mic'd amps or amp simulators is not stated, so for
  Cambridge "amp track" means only "the guitar's processed track".
- **Guitar-TECHS, `P3_music`** (Zenodo record 14963133, CC BY 4.0) — twelve short
  guitar-solo excerpts by one player, a Sire T7 into an Orange CR-12, each recorded
  as a DI and an amp microphone at once; 24-bit/48 kHz; no band. The archive's
  published MD5 is `071ba80aecf00f4a31fbd167b3f22198`; it was unpacked and not kept.

## Which parts count

A part is a guitar recorded both as a DI and as an amp track. Both files are read
as mono (the mean of their channels) at their own sample rate, cut to 10 ms frames
of mean absolute amplitude, truncated to the shorter of the two, and z-scored. A
part is **usable** when both tests pass:

1. **the same take** — the whole-length correlation of the two envelopes, at its
   peak within ±20 ms, is 0.8 or more;
2. **kept in step** — in 20 s windows every 10 s, counting the windows whose amp
   envelope is within 30 dB of the loudest window, each window's own best lag
   within ±200 ms is within ±20 ms in at least 80% of them, and the median of those
   windows' correlations is at least 0.6.

The second test was added after a review found that whole-length agreement is
lifted by shared silences and a song's loudness arc — two Heather Jane parts pass
the first test while drifting between −30 and −120 ms in the middle of the song —
and before any match or benchmark touched any part. Every figure is in
`validation-datasets.json` (`lag_ms` is positive when the amp track is later).
Excluded: Heather Jane ElecGtr2 and its double (in step in 12% and 42% of windows)
and ElecGtr3 (0.65); Memphis ElecGtr2 and its double (0.54, 0.55) and ElecGtr1
(no DI). Cambridge's "Library of Mic Positions" electric-guitar set, suggested
during the search, has no DI and is not used.

## How a part is used

These hold for every use unless a test declared under the rule below states
otherwise before it runs.

- **Signals.** Every file is read as mono (the mean of its channels) and
  resampled to 48 kHz by the repository's loader (`analysis.io`), as every tool
  here does. Tracks are aligned at their first sample, as recorded; nothing is
  shifted by `lag_ms`, which is reported, not applied. A session's length is its
  part's DI length; shorter tracks are padded with silence to it and longer ones
  cut to it.
- **Lags.** `lag_ms` comes from 10-ms envelopes, so it is quantised to 10 ms. An
  analysis that needs a part's lag takes it from `validation-lags.json`
  (`scripts/record_part_lags.py`, read by `benchmark_recordings.lag_samples`): one lag
  per set-2 development part, measured on its 10-s validation crop. Candidates come
  from the cross-correlation of the amp track with all the part's SW50R panel renders;
  where a DI's buzz or pulse makes a comb of near-equal peaks, the judge chooses
  between them, and the choice stands only if a clear onset peak from the raw DI
  confirms it (the judge's preference is not independent evidence: every render
  shares the part's DI and amp track). Four are ambiguous and `lag_samples` withholds
  them unless asked: Passing Ships ElecGtr3 (a comb the judge cannot split, its
  onset between two of the peaks), Prodigal ElecGtr4 (a comb with no clear onset),
  Strangest Places (+37 samples; −37 is nearly as high) and Signs ElecGtr3 (72; 23 is
  nearly as high), whose pooled subsets land on both peaks. Of the
  39 others, the catalogue is off by 2.5 ms or more on 7, by up to 14 ms (Today's The
  Day ElecGtr10). Analyses declared before this file existed keep the lags they
  declared.
- **The reference** is the part's amp track: for Telefunken the M80 microphone; the
  TF11 is used only by a test that names it. For Cambridge and Guitar-TECHS, the
  one amp track.
- **The DI** is the part's own DI track, unedited.
- **The mix** of a session is the sum at unity gain of every track except the
  guitar DIs — so the bass DI is in it, and both microphones of every other guitar.
  It is a raw stand-in for a finished mix, not a mastered one; `mix` is its regime.
- **The backing** for a part is the mix without that part's own amp tracks (both
  microphones for Telefunken). A double-tracked part's double stays in it: it is
  another guitar in the arrangement.
- **An excerpt** is 10 s of the session, searched at 0.5 s steps; the DI, the mix and
  the backing use the same sample span. Whether a test uses a whole part or its
  excerpt is part of that test's declaration. The match tool picks an excerpt of its
  own unless told not to, and applies it to the reference only, so every use first
  cuts the reference, the DI and any mix or backing to the declared span — or keeps
  them whole — and then runs with `--excerpt 0`. The tool's own excerpt choice is
  never used.
  - **Crop rule 2**, declared on 2026-10-04 for every crop cut from then on, held-out
    ones included: the window where the part's DI plays in the most frames
    (2048-sample frames, hop 1024, within 40 dB of the DI's loudest), ties within 0.02
    broken by the reference's ungated mean square, then the earliest. Its crops go to
    `~/ndsp-presets/references/validation-crops-2`, with `"excerpt_rule":
    "di-activity"` in each record.
  - **The first rule** was the loudest 10 s of the mono reference by integrated
    loudness (`analysis.io.loudness_lufs`). Integrated loudness is gated, so a loud
    burst in a silent stretch won, and many crops barely held the part (audit D-M6).
    Analyses declared on its crops (`validation-crops`) keep them.
  - **Measured on the 57 usable development parts** (`scripts/measure_crop_rules.py`,
    `docs/validation-crop-rules.json`): the part plays in at least half of the window
    on 43 under the first rule and 56 under rule 2, and in at least 90% on 40 and 56.
    The exception is Prodigal ElecGtr4, which plays in at most 38.3% of any 10 s.
  - **Lags carry over.** A part's DI and amp track are cut at the same span, so its
    recorded lag (`docs/validation-lags.json`) holds for either crop.
- **The amp track where the DI is silent** is recorded per development part in
  `docs/validation-crop-rules.json` (`bleed_db`): its median level where the DI is
  more than 60 dB under its loudest, less its median where the DI plays, over the
  whole session. It mixes two things: bleed from the band, and the amp's own steady
  noise. Where the level follows the backing it is bleed (Blind Spots, Gym Hours GTR 2,
  Farthest Step, Lost Alive, Honey); where it does not, it is noise (Heather Jane
  ElecGtr1 at about −60, Fragments at −75).
  - Most Cambridge sessions read below −200 dB: digital silence between the takes.
  - The Telefunken live-room sessions mostly read −79 to −24 dB. The highest are Lost
    Alive, She's Gone, Honey, Hikikomori and Until I Get Back. Bloomlight reads as
    digital silence, and two parts (Bourbon GTR 1, Collide With Me GTR 1) have too few
    silent frames for a value.
  - A listener heard the backing in Blind Spots' amp track, at −46.
  - It is a measurement, not a flag: an analysis that leaves out bleed declares its
    own threshold, and checks which kind it is.
- **The regime.** The DI and the reference are the same performance, so a match
  against the amp track alone runs with `--reference-mode paired_di` and, unless a
  test says otherwise, `--loss-profile unpaired-v2`: a mic'd amp cannot be reached
  sample for sample by any plugin chain, so a waveform-residual profile would score
  microphone, cabinet and phase differences rather than tone. The match tool's
  pairing record (`paired-di-reference-1`) can only be made for its own renders, so
  such runs report the pairing as asserted, and a blind export from them needs
  `--allow-unpaired`.

A double-tracked part and its double are two takes of one guitar and setting:
they count as one tone. Guitar-TECHS is one player, guitar and amp setting
throughout, so its twelve excerpts are twelve performances of one tone.

## The split

`scripts/validation_datasets.py` draws it with `random.Random(20260927)`, in this
order, and the drawn items are held out:

```python
rng.choice(["57 Chevy", "Bourbon", "Collide With Me"])            # -> "57 Chevy"
rng.choice(["Heather Jane", "That's How I Got To Memphis"])       # -> "That's How I Got To Memphis"
sorted(rng.sample(["01", "02", ..., "12"], 4))                    # -> ["02", "06", "10", "11"]
```

| | development | held out |
|---|---|---|
| Telefunken | "Bourbon", "Collide With Me": 4 parts | "57 Chevy": 2 parts |
| Cambridge | "Heather Jane": ElecGtr1 and its double (one tone) | "That's How I Got To Memphis": ElecGtr3 and its double (one tone) |
| Guitar-TECHS | excerpts 01, 03, 04, 05, 07, 08, 09, 12 | excerpts 02, 06, 10, 11 |

That is 14 usable development parts and 8 held out. The unit held out is the
whole session — every file of "57 Chevy" and of "That's How I Got To Memphis",
including their drums, vocals and excluded guitars — and, for Guitar-TECHS, every
file numbered 02, 06, 10 or 11 (audio, MIDI and the two camera-microphone
recordings). What the held-out material can test is limited: "57 Chevy" shares the
band, room and very likely the rigs with the development songs, Memphis shares the
player with Heather Jane, and the held-out Guitar-TECHS excerpts are new
performances of a development tone. It tests new performances and settings more
than new equipment.

**Development** material may be used for anything: benchmarks, tuning, trying
ideas, listening. **Held-out** material is used only by a test declared in a
committed file before it runs — its command, what it measures and what each result
would mean — and by prospective listening under the same rule; each such use is
added to `held_out_uses` in `validation-datasets.json`. A held-out session used
once by such a test stays held out for the next declared one. A held-out session
used for anything else moves to development, and this file says so.

When this was declared, these recordings had been checked only for the pairing
above, their lengths and their levels. No match, benchmark or listening test had
touched them.

## The second set

The first set is three bands, one of them a solo player, and its held-out sessions
share their band, room or player with development ones. The second set adds 37
sessions from 21 bands, mostly rock, chosen to fit the amps the packs model: a
separate research session searched for multitracks with a DI and an amp track of
the same guitar, left metal out, downloaded each archive, checked its files and
tested every DI/amp pair. Its record, `validation-candidates.json`, stays beside
the audio. `validation-sources-2.json` lists what was taken from it: for each
session the source, artist, song, band (`group`), folder, archive URL and SHA-256,
and each guitar's DI and amp tracks, with any amp simulator or modeller track the
research paired with that DI (a name containing "sim", or a modeller's name such
as "Helix") listed apart as `simulated`. Two titles holding "/" are written with
" - " instead ("Sugar - Faith", "Hikikomori - Love Does"), since a part's ID is
`source/song/part`.

- **Cambridge Music Technology "Mixing Secrets" library** — 14 sessions by 12
  artists, 24-bit/44.1 kHz, on the terms quoted above. Many sessions name their
  guitar tracks by microphone (Mic1, Close, Far); some only as the amp or the
  guitar. What is a microphone on an amp and what is a processed track is still
  not stated.
- **Telefunken "Live From The Lab"**, later seasons — 23 sessions by 9 bands,
  24-bit at 48 kHz (17) or 96 kHz (6), on the terms quoted above, recorded live
  in Telefunken's room.
  The two songs credited to Moorea Masa & The Mood with Swatkins are grouped
  with Swatkins's own, so the players they share stay on one side of the split.

Everything in the sections above applies to the second set, except these rules:

- **Which parts count.** The same two tests, measured by
  `scripts/validation_datasets.py` from the audio, not taken from the research
  record. Two more rules leave a part out whatever its pairing, and its
  `excluded` field says which: a part named for the keyboard player ("Keys
  GTR"), which may be a keyboard through a guitar amp — the sessions do not say
  — and a part whose amp track is another part's too, since that track then
  carries two performances.
- **The reference.** A part's amp tracks are tried in the order of
  `AMP_PREFERENCE` in that script: the M80 microphone first, as in the first set,
  then a first or close microphone, then a track named as the amp or as the
  guitar alone, then the other Telefunken microphones, then a second or far
  microphone. The first that passes both pairing tests is the reference; when
  none does, the part is not usable. The others are alternates, used only by a
  test that names them.
- **The mix** is the session's `mix_tracks`, summed at unity gain: every WAV but
  electric guitar DIs (a part's or not), every part's alternates, click tracks
  and rendered mixes, each recognised by its name, and a part's simulator or
  modeller track when it is the same take as the part's DI (the first pairing
  test). So every part's guitar is heard once, through its reference. A guitar
  recorded only as a DI is left out; a guitar without a DI keeps all its
  tracks, a modeller playing another part among them; and the bass keeps its DI
  and its amp, as in the first set.
- **The backing** is the mix without the part's reference.
- **The instrumental mix and backing** are the mix and the backing without the
  session's `vocal_tracks` (mix tracks named "vox" or "vocal"). They are for
  listening, where loud singing over the first set's held-out parts made them
  hard to hear, and an audition plays them together or not at all, since
  singing in only one would give the reference away. A listening test that
  uses them says so in its declaration, and its manifest step passes
  `--instrumental` (`declared-listening-runner.md`). Live rooms put singing
  into the other microphones too, so it is quieter singing, not none.

The split holds out whole bands, so that all of a band's songs are on one side.
Players a band shares with another band, if any, are not tracked.
`scripts/validation_datasets.py` draws it with `random.Random(20261001)`, from
each source's band names sorted:

```python
rng.sample(sorted(cambridge_bands), 5)    # -> Boogie Snakes, Forkupines, Lights Off Clarity,
                                          #    The Maybe Next Years, Tim Taler
rng.sample(sorted(telefunken_bands), 3)   # -> Briana Maia, Catbite, Wild & Co
```

| | development | held out |
|---|---|---|
| Cambridge | 7 bands, 8 sessions: 23 usable parts of 48 | 5 bands, 6 sessions: 14 usable parts of 24 |
| Telefunken | 6 bands, 18 sessions: 20 usable parts of 26 | 3 bands, 5 sessions: 5 usable parts of 5 |

That is 43 usable development parts and 19 held out; as in the first set, a
double-tracked part and its double count as one tone. Every pairing figure is in
`validation-datasets.json`, where the second set's sessions carry `"set": 2`.

Every file of every session by a held-out band is held out. Development and
held-out material follow the rules of [the split](#the-split), and the first
set's held-out sessions stay held out. What the held-out Telefunken bands can
test is limited the way "57 Chevy" was: one room and often the same
microphones, so they test new players, guitars and amps more than a new room.

When this was declared, the second set had been checked only for the research
session's pairing tests and file checks and for this file's measurements. Its
mix and reference rules were chosen from track names and from which pairs the
research session found in step, not from listening. No match, benchmark or
listening test had touched it.
