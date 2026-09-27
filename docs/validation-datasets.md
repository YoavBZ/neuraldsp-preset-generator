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
on GitHub.

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
- **An excerpt** is the loudest 10 s of the mono reference by integrated loudness
  (`analysis.io.loudness_lufs`), searched at 0.5 s steps; the DI, the mix and the
  backing use the same sample span. Whether a test uses a whole part or its excerpt
  is part of that test's declaration. The match tool picks an excerpt of its own
  unless told not to, and applies it to the reference only, so every use first
  cuts the reference, the DI and any mix or backing to the declared span — or
  keeps them whole — and then runs with `--excerpt 0`. The tool's own excerpt
  choice is never used.
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

Until now these recordings have been checked only for the pairing above, their
lengths and their levels. No match, benchmark or listening test has touched them.
