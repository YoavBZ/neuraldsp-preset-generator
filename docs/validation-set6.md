# Set 6: MedleyDB as a held-out validation set, declared

Declared 2026-10-12, under set 5's rules ([validation-set5.md](validation-set5.md)), with
one addition. MedleyDB names no DI, so a declared **DI-role rule** says which track of a
same-take pair is the DI.

**Status after amendment 1 (2026-10-13): set 6 is unusable for DI-based tests.**

- **It holds no DI part.** No DI-role rule kept most real DIs with at most 10% false
  accepts on development data (amendment 1, below).
- **All 7 parts of the first declaration are excluded.** Their crops stay on disk, held
  out and superseded.
- **Steven Clark – Bounty** is excluded on a second ground too: MedleyDB labels both its
  tracks "electric bass".
- **At most a song-only use** (the released mixes, with no DI) can be declared later. It
  needs its own crop rule.
- **35 of the 73 songs are in MUSDB18's train subset** (section "MUSDB18 overlap"). HTDemucs
  was trained on that subset, so a stem-based test must exclude or report those songs.

The sections after the amendment describe the first declaration. Where they speak of kept
parts, those parts are now excluded.

**Every band is held out, and the set is unused.** Nothing may train, tune or choose on
it, and nobody may listen to it, until a confirmation is declared in a committed file.
That use is then added to `held_out_uses`, which is empty.

## Amendment 1 (2026-10-13): the DI-role rule, calibrated on development data

The declaration below (commit f1918cc) was rejected in review: its DI-role rule had never
been tested on known pairs. This amendment calibrates a DI-role rule on **development data
only**, and fixes the outcome **before anything is applied to MedleyDB**. It is committed on
its own, ahead of the commit that applies it.

**What was measured.** `research/set6_di_role_calibration.py` takes every development
session of sets 1–2 and set 3 (Cambridge, Telefunken, Guitar-TECHS P3; no held-out session
or part is opened). Within each session it tests every pair of the catalogued guitar tracks
(the DIs and every amp track of each part). It applies set 4's waveform same-take test,
unchanged, as MedleyDB's pairs had it. The roles come from the session track names.

- **Positives:** a DI against an amp track. There are 177 same-take pairs: 95 clean, 39
  crunch, 43 high-gain (set 3's classifier, DI → amp).
- **Negatives:** two amp tracks of one part (two microphones on one cab, close/far,
  Amp1/Amp2), amp tracks of two parts, and DI against DI. There are 66 same-take pairs:
  54 from one part, 7 from two parts, 5 DI–DI.
- **Bands:** 30 in all, 18 of them with negatives.

The cues, measured on each orientation of each pair (x as the DI candidate) over the frames
where both tracks play:

- the coherence at 0.2–2 kHz;
- the linear transfer x → y (H1), as roll-off: 6–10 kHz against 0.5–2 kHz;
- the power ratio over the same bands;
- set 3's gain measures: the 1-s crest drop and the level slope;
- the per-track 5–10 kHz share (the first declaration's clean cue).

The lag is not used to orient a pair.

**What separates, and what does not:**

- **Two microphones close on one cab are near-linear.** 34 of the 54 one-part pairs have a
  coherence of 0.967–0.997. The rest are lower:
  - distant or differently placed mics, and two of Renesans' amp pairs, read 0.68–0.89;
  - two amps on one DI (Ale Lak, Eat The Feeder, Renesans) read 0.38–0.58.
- **Driven DI → amp pairs are not.** Crunch pairs read 0.13–0.67 (median 0.40), and
  high-gain pairs 0.04–0.54 (median 0.34).
- **Clean DI → amp pairs overlap the mic pairs.** They read 0.37–0.99 (median 0.78).
  - The DI is often the **darker** track. The median per-track 5–10 kHz share is −41 dB
    for DIs and −28 dB for amp tracks. "A DI has no speaker roll-off, so it is brighter"
    is false on development data.
  - No single cue finds more than 45% of clean DIs at a 10% clean false-accept rate.
- **Two amps fed from one DI** (Eat The Feeder's Amp1/Amp2, and its cross-part amp
  tracks) are non-linear to each other, so they look like a DI → amp pair.

**Rule families and their development results.** Thresholds were fitted by a grid,
maximising right-DI accepts with false accepts at most 10%. Each figure is leave-one-band-out:
each band is scored with thresholds fitted on the other 29.

| rule | clean | crunch | high-gain | all DIs | false accepts (all negatives) | of which two-mic, one part |
|---|---|---|---|---|---|---|
| as first declared (lag orientation, crest ≥ 3 dB / HF advantage ≥ 6 dB; not fitted) | 18/95 (19%) | 22/39 (56%) | 16/43 (37%) | 56/177 (32%) | 3/66 (5%) | 3/54 |
| driven: coherence 0.05–0.7 and crest drop ≥ 1 dB, DI = the larger crest drop | 13/95 (14%) | 34/39 (87%) | 37/43 (86%) | 84/177 (47%) | **8/66 (12%)** | 4/54 (7%) |
| two-branch: the driven rule, plus a clean branch (coherence ≤ c or H1 roll-off ≤ t, DI = lower level slope) | 65/95 (68%) | 37/39 | 40/43 | 142/177 (80%) | **27/66 (41%)** | 23/54 (43%) |

Notes on the table:

- **The two-branch row's thresholds** are those fitted by the grid. No clean branch passes
  the bar together with the driven rule. The lowest-false-accept clean branch finds only
  27/95 clean DIs, and even that (fitted on all bands) has 8/66 false accepts.
- **The driven rule** chose the same thresholds in 27 of 30 folds: coherence 0.05–0.7,
  crest drop ≥ 1 dB.
  - 6 of its 8 false accepts are Eat The Feeder's two-amp rig. The others are one DI–DI
    pair (Hikikomori) and one close/far mic pair (The Travelling Band).
  - 12 positives were accepted with the wrong track as the DI.
- **The first declaration's rule** on whole development tracks keeps 32% of real DIs. The
  review measured 14% on the 10-s crops.

**The bar, and the verdict.**

- **The bar:** a DI-role rule may establish set-6 DIs only if two things hold, both
  leave-one-band-out on development data:
  - it false-accepts at most 10% of all development negatives (two microphones, two amps,
    DI–DI, since MedleyDB holds all three kinds);
  - it keeps most real DIs of the class it is used for.
- **The verdict: no rule above meets it.**
  - Clean DIs cannot be established at all.
  - The driven rule keeps 87% of crunch DIs and 86% of high-gain DIs. But its false-accept
    rate is 12%, over the bar, and a two-amp rig passes it wholesale.
  - The rule as first declared has a low false-accept rate. But it keeps only a third of
    real DIs, and it is not principled: its lag premise is contradicted by labelled DIs.

**So set 6 is declared unusable for DI-based tests.** It holds no DI part.

- **What the next commit does:**
  - every previously kept or excluded part is excluded, with this amendment as the reason;
  - the 7 crops already cut stay on disk, held out and superseded;
  - MedleyDB stays held out and unused;
  - at most a song-only use (the released mixes, no DI) can be declared later, with its
    own crop rule.
- **The failed rules are not applied to MedleyDB.** A future rule (for example a driven-only
  rule, calibrated on more development negatives) can then still be tested on it with no
  look at its output.
- **Steven Clark – Bounty, RAW_01_04 → 01_02:** MedleyDB labels both tracks "electric bass".
  It is excluded on that ground as well.

**Disclosure.**

- **Set-6 role statistics have been seen** by both the building agent and the reviewer:
  every same-take pair's lags, crests, 5–10 kHz shares and gain classes, the first rule's
  outcomes, and the fact that the first rule's thresholds were fixed after 4 songs.
  BigTroubles_Phantom is among those 4, and it later gave a kept part.
- **No tone information was seen.** Nothing was rendered, scored, separated or listened
  to, on any set.
- **The development calibration** (cues, rule families, grid) was designed by the building
  agent after that viewing. The 10% bar was set after the development table was seen. Of
  the two readings (two-mic pairs only, 7%; all negatives, 12%), the stricter one was
  taken.

The calibration summary is `docs/validation-set6-di-calibration.json`, built by
`research/set6_di_role_calibration.py evaluate`. The per-pair evidence is in
`~/ndsp-presets/references/datasets-medleydb/_tools/di_role_calibration/`
(`dev_pairs.json`, `dev_tracks.json`).

**Scope** (first declaration). As in set 5:

- clean and crunch parts are in scope;
- high-gain parts are report-only, set by each part's session-level gain class.

**The first headline (superseded): MedleyDB gave few parts.** Only 5 of its 73 songs on
disk gave a kept part, from 5 bands: 3 clean parts from 3 bands, and no crunch part.
Amendment 1 excludes all of them.

- Most same-take pairs in MedleyDB are not a DI and its amp track. They are two
  microphones on one amp, or duplicate files.
- **So set 6 adds nothing to the combined set-5 + MedleyDB stem test, on either the clean
  or the crunch side** ([set5-test-plan.md](set5-test-plan.md)). That test's plan should
  say so before any power calculation.

`docs/validation-set6.json` (schema `validation-set6-2`) is the machine-readable
declaration. It holds:

- the inventory's SHA-256;
- every song, with its provenance and its MUSDB18 mark;
- the amendment;
- every part of the first declaration, now excluded, with its reasons and its superseded
  crop's hash;
- every same-take pair that did not establish a DI, with reasons.

`research/validation_set6.py declare` rebuilds the JSON from the inventory
(`~/ndsp-presets/references/datasets-medleydb/inventory.json`), the crop records
(`~/ndsp-presets/references/validation-crops-set6/<slug>/record.json`), and the MUSDB18
lists (`datasets-medleydb/_tools/musdb18/`).
`research/validation_set6.py crops` cut the crops.

The pairing and inventory scripts are in `tmp/set6/` on the main checkout (`pair.py`,
`build_inventory.py`). Their per-pair evidence is in
`~/ndsp-presets/references/datasets-medleydb/_tools/pairs/<song>.json`. No audio is in git.

## What was done to it

- **Done:**
  - extraction and hashing, and licence capture;
  - the same-take tests on every pair of electric-guitar raw tracks of a song (1,568
    pairs);
  - lags and polarity;
  - the DI-role cues: each track's 1-s crest and its 5–10 kHz share;
  - set 3's gain classifier (`classify.py`, `gainmeasure.py`, the same bytes as sets 4
    and 5; hashes in the JSON);
  - the 10-s crops (crop rule 2, 48 kHz mono), with the same 10 s of the song's mix;
  - on each crop, the onset cross-check and the crop-level gain class.
- **Not done:**
  - no plugin ran, and no render was made;
  - nothing was scored: no judge, no `measure`, no `aligned_distance`;
  - no network was run on it, and no source separation;
  - nothing was listened to, and no tone or preset was compared.

## Source, provenance and licence

- **Data:** MedleyDB audio V1 (Zenodo record 1649325) and V2 (record 1715175). Access is
  restricted and was granted to the user for non-commercial research.
  - Metadata comes from `github.com/marl/medleydb` at commit `537bb7b`
    (`Metadata/*.yaml`, `ERRATA.md`).
- **Licence:** Creative Commons BY-NC-SA 4.0, the same text for both records.
  - V1's `LICENSE.txt` is captured as `LICENSE-V1.txt` in the dataset root (MD5
    `071086fd72dc543a4a680a747874bd16`).
  - V2's `LICENSE.txt` has the same MD5 in Zenodo's file listing, recorded when the
    archive was fetched. That listing is restricted now (403), so V2's copy was not
    captured.
  - Both record pages state CC BY-NC-SA 4.0 (checked 2026-10-13). The JSON records this in
    `licence_texts`.
  - Non-commercial research only. Validating an openly distributed, non-commercial plugin
    is non-commercial research, and no MedleyDB audio or derived audio is distributed.
  - Nothing is republished, and no audio is in git.
- **Archives:** each archive was streamed from Zenodo.
  - Its whole-file SHA-256 and MD5 are in `MedleyDB_V*.tar.gz.checksums`. The MD5 was
    checked against Zenodo's by the user.
  - Only each song's mix and its electric-guitar raw tracks were extracted, and the
    archive was not kept.
- **Extracted files:** `_tools/files.json` holds the SHA-256 of every extracted file.
  Each crop's sources were checked against it before cutting.
- **Selection:** `eguitar_songs.json` lists the songs whose metadata has an
  electric-guitar raw track.
  - 73 of its 166 songs are in the V1/V2 audio releases, and are on disk.
  - The others are metadata only.
- **Mix:** each song's raw tracks and its mix have the same length, so they share one
  timeline.
  - `AimeeNorwich_Child_MIX.wav` is an M4A file in the archive. That song has one guitar
    track, so no part needs it.
- **Origin** (MedleyDB's `origin` field), over the 73 songs:

  | origin | songs |
  |---|---|
  | Weathervane Music (released bands' sessions) | 24 |
  | Dolan Studio (NYU) | 21 |
  | Music Delta (a commercial multitrack library) | 15 |
  | Independent Artist | 13 |

  Three kept parts are Weathervane (Big Troubles, Purling Hiss, Steven Clark). The other
  two are Dolan Studio (Dahka Band) and Independent Artist (Aimee Norwich).
- **Bands:** MedleyDB's artist names, with two read as one band each:
  - "Music Delta Multitracks" and "Music Delta" are one band, "Music Delta";
  - "Sweat" and "SWEAT" are one band, "SWEAT".
- **No band from an earlier set.** Every MedleyDB artist and song title was checked
  against sets 1–5 and development: every `docs/*.json` catalogue, the
  `~/ndsp-presets/references` catalogues and inventories, and the crop folders. There is
  no match. `tests/test_set6.py` checks the bands.

## MUSDB18 overlap (separator training data)

MUSDB18 (and MUSDB18-HQ) takes 46 of its 150 songs from MedleyDB, all of them in its
**train** subset. HTDemucs, the separator used across `learn/`, was trained on MUSDB18-HQ's
train subset. A separated stem of such a song is therefore an optimistic test.

**Which songs.** 35 of set 6's 73 songs are in MUSDB18. Each one carries a
`separator_trained_on` block in the JSON (the MUSDB18 name, its subset, and whether it is
on MUSDB's validation list). Every one of the 35 is in **train**.

- AClassicEducation_NightOwl, AimeeNorwich_Child, AlexanderRoss_GoodbyeBolero (on the
  validation list), AlexanderRoss_VelvetCurtain, Auctioneer_OurFutureFaces,
  AvaLuna_Waterduct, BigTroubles_Phantom, CelestialShore_DieForUs,
  ClaraBerryAndWooldog_AirTraffic, Creepoid_OldTree, FacesOnFilm_WaitingForGa,
  HopAlong_SisterCities, InvisibleFamiliars_DisturbingWildlife, Lushlife_ToynbeeSuite;
- Meaxic_TakeAStep (on the validation list), Meaxic_YouListen;
- 12 Music Delta songs: 80sRock, Beatles, Britpop, Country2, Disco, Gospel, Grunge,
  Hendrix, Punk, Reggae, Rock, Rockabilly;
- PortStWillow_StayEven, SecretMountains_HighHorse, Snowmine_Curfews, StevenClark_Bounty,
  TheDistricts_Vermont, TheScarletBrand_LesFleursDuMal, TheSoSoGlos_Emergency.

None of the V2 songs is in MUSDB18. That includes Dahka Band, the SWEAT songs and Dead
Milkmen.

**Sources.** Copies are in `datasets-medleydb/_tools/musdb18/`, with SHA-256 in the JSON:

- sigsep's `tracklist.csv`, the 150 songs and their source;
- `musdb/configs/mus.yaml`, with the validation list;
- the test subset, read as the 50 track names under `submissions/*/test/` of
  `sigsep/sigsep-mus-2018`. Train is the other 100.

**MUSDB18's test subset holds Cambridge songs used by earlier sets.** It includes BKS, Forkupines and
Hollow Ground (Cambridge sessions in sets 1–5). Those songs are not set 6's, and are not
marked here. A stem-based test on them is not trained-on, but they are public benchmark
songs.

## The DI-role rule (first declaration; failed calibration, amendment 1)

MedleyDB's raw tracks are labelled only by instrument ("clean electric guitar",
"distorted electric guitar"), never as DI or microphone. A same-take pair can be:

- a DI and its amp track;
- two microphones on one amp;
- two copies of one file.

The rule was fixed on 2026-10-12, after the pairing statistics of 4 songs were seen
(AlexanderRoss_GoodbyeBolero, BigTroubles_Phantom, MusicDelta_Rock, Snowmine_Curfews), and
before any crop was cut. Its thresholds did not change after that.

1. **Orientation:** the earlier track of a pair is the DI candidate.
2. **An acoustic path:** the amp track is 3 samples to 5 ms later.
   - A lag of 2 samples or less means no acoustic path between them, so a DI and a
     microphone cannot be told apart.
   - A lag over 5 ms means a distant microphone. Set 5 flagged lags over 5 ms; none of its
     kept parts had one.
3. **The pair's reading must fit a DI.** One of two branches:
   - **Driven branch:** the pair reads crunch or high-gain (DI → amp), and the DI's 1-s
     crest is at least 3 dB above the amp track's. A DI is the peakier, uncompressed
     track.
   - **Clean branch:** the pair reads clean, and the DI's 5–10 kHz share (against
     0.2–4 kHz) is at least 6 dB above the amp track's, since a DI has no speaker roll-off.
     A pair whose two tracks are both labelled "distorted electric guitar" only is
     refused here: a linear pair there is two microphones.
4. **Reference:** among a DI's passing amp tracks, the closest one (smallest lag) is the
   reference, then the higher peak-to-sidelobe ratio. This is set 4's "Close" preference,
   read from the lag. The others are alternates.

**Duplicate files** are named as such. They are pairs at lag 0 with a non-linear share of
−50 dB or less. They fail rule 2 anyway.

**The clean branch is the weaker evidence.**

- All three in-scope parts rest on it.
- On two of them, the DI's crest is not above the amp track's: Steven Clark is −2.4 dB and
  Aimee Norwich is −0.1 dB.
- A bright close microphone against a dark one could pass it.

Each part's `di_role` field records its branch and cues. A confirmation plan should report
the in-scope result with this caveat.

## Rules

The rules are set 5's, unchanged (`rules` in the JSON), plus the DI-role rule:

- **Same take:** the waveform test passes, with 80% or more of 20-s windows in step and a
  median peak-to-sidelobe ratio of 2.0 or more.
  - Every pair of electric-guitar raw tracks of a song is tested, across MedleyDB stems
    too.
  - A pair that passes the envelope test only is not used.
- **Exclusions:**
  - fewer than 3 passing windows;
  - a clipped DI (10 or more flat-topped runs);
  - two lag clusters;
  - an amp track that is also another DI's.
- **Crop:** crop rule 2 (`docs/validation-datasets.md`). The window is the 10 s where the
  DI plays most, with first-sample alignment, and the session length comes from the DI.
  - Each crop has `di.wav`, `reference.wav` and `mix.wav`, all 48 kHz mono float32.
  - `mix.wav` is the same 10 s of the song's released mix (mono mean, resampled), for a
    test from a separated stem.
  - Only the guitar raw tracks were extracted, so there is no stem-sum mix or backing.
  - A crop was cut for every part whose DI role was established, as set 5 did, including
    the 2 parts then excluded.
- **Lags:** `lag_samples` is the inventory's waveform lag converted to 48 kHz. It is never
  re-measured. `judge_lag_samples = lag_samples − 52`. The lag is positive when the amp
  track is later.
- **Gain class:** both levels are recorded, as in set 5. `gain_class` is the
  session-level class and `gain_class_crop` is the crop's. They agree on all 5 kept parts.
- **Split:** every band is held out, with no draw and no folds. For band weighting, set
  3's amendment (4) is recommended (each band's parts weigh 1/n). Here each band has one
  part.

## Kept (first declaration; all excluded by amendment 1)

| part (song, DI → reference) | class | scope | branch | lag (48 kHz) | windows | notes |
|---|---|---|---|---|---|---|
| Aimee Norwich – Flying, RAW_05_02 → 05_01 | clean | in | clean | 26 | 19 | polarity −1 |
| Dahka Band – Soldier Man, RAW_04_01 → 04_02 | clean | in | clean | 23 | 31 | has_bleed |
| Steven Clark – Bounty, RAW_01_04 → 01_02 | clean | in | clean | 25 | 3 | both tracks labelled electric bass by MedleyDB; thinnest evidence |
| Big Troubles – Phantom, RAW_05_01 → 05_02 | high-gain | report-only | driven | 67 | 13 | DI crest 19 dB against 11 dB; onset unclear |
| Purling Hiss – Lolita, RAW_03_06 → 03_05 | high-gain | report-only | driven | 32 | 24 | polarity −1; has_bleed; DI labelled clean, amp distorted |

Corrections from the review, recorded although every part above is now excluded:

- **Steven Clark:** both of its tracks are labelled "electric bass". The first declaration
  did not disclose this.
- **Dahka Band:** its HF advantage was 6.21 dB against the 6.0 threshold, a 0.2-dB margin.
  Its per-track 1-s crest is lower on the "DI" (14.95 dB against 17.08 dB). It belongs
  with Steven Clark and Aimee Norwich among the parts whose DI crest is not above the amp
  track's.

- **Counts** (first declaration):
  - 7 parts declared (one per established DI): 5 kept and 2 excluded;
  - in scope: 3 clean parts from 3 bands (Aimee Norwich, Dahka Band, Steven Clark);
  - no crunch part;
  - report-only: 2 high-gain parts.
- **Big Troubles RAW_05_01** has an alternate amp track, RAW_05_04 (112 samples at 44.1
  kHz).
- **Onset cross-check:** it agrees on 4 parts and is unclear on Big Troubles (runner-up
  0.995). It is a cross-check only; the declared lag is unchanged.
- **`has_bleed`:** MedleyDB tags Dahka Band and Purling Hiss as having bleed. Those parts
  carry the mark.

## Exclusions

**Songs (68 of 73) with no kept part:**

- **One electric-guitar raw track, so no pair (17):**
  - AimeeNorwich_Child, ChrisJacoby, ClaraBerryAndWooldog, EthanHein, LizNelson;
  - five Music Delta songs (80sRock, Disco, Hendrix, Punk, Reggae);
  - the three Tabla Breakbeat Science songs;
  - three Sasquatch Connection songs (BoomBoxing, HolyClamsBatman, ThanksALatte);
  - The Kitchenettes.
- **No same-take pair (16):** the guitar tracks are separate performances.
  - AClassicEducation, AlexanderRoss_VelvetCurtain, FacesOnFilm, InvisibleFamiliars,
    Meaxic_TakeAStep, TheScarletBrand, Cayetana and MidnightBlue_StarsAreScreaming;
  - eight Music Delta songs.
- **Same-take pairs, but no DI established (34):** 232 pairs in all, each with its reason
  in `role_failures`.

  | reason | pairs |
  |---|---|
  | lag 0–2 samples (no acoustic path) | 82 |
  | clean, with too small an HF advantage | 62 |
  | duplicate files | 41 |
  | driven, with too small a crest drop | 20 |
  | envelope-only | 16 |
  | linear pair on distorted-only tracks | 6 |
  | distant microphone (over 5 ms) | 5 |

  - The six SWEAT songs, Fruit Cathedral, Trevor and the Soundwaves, Plasma and
    Meaxic_YouListen are mostly duplicates and zero-lag pairs.
  - MedleyDB's errata lists MusicDelta_Country2 RAW_03_01 and RAW_04_01 as duplicates.
    The test found them identical too.

**Parts excluded (2):**

- **BigTroubles RAW_03_08 → 03_09:** two lag clusters (60% of windows within 0.25 ms).
- **DeadMilkmen RAW_09_02 → 13_01:** two lag clusters (67%). It is a cross-stem pair, and
  13_01 also pairs with RAW_10_02. RAW_10_02 failed the driven branch, because it has no
  1-s crest window.

**Not parts:** the 362 guitar raw tracks that are neither an established DI nor its amp
track are listed in the JSON's `unpaired`.

## Deviations from set 5

1. **The DI-role rule** (above), because MedleyDB names no DI.
2. **Every pair is tested,** not every DI against every amp track, since no track is
   named a DI.
3. **The crop mix is the released mix.** `mix.wav` is MedleyDB's `<Song>_MIX.wav`, not a
   stem sum, and there is no backing.
4. **Source checks use `_tools/files.json`.** That is the SHA-256 of each extracted file,
   recorded after extraction from MD5-verified archives. There is no per-file publisher
   hash.
5. **New marks:** `has_bleed` and `cross_stem`, plus a `di_role` block for each part.
   They are descriptive only.

Resampling 44.1 → 48 kHz is as in sets 3–5. Gain thresholds were not recalibrated.

## Disclosure: what the building agent saw

- **Pairing statistics, gain measures, clipping, lags, crop starts, DI activity, the
  onset cross-check, and the DI-role cues** (1-s crest, 5–10 kHz share, frame-level
  spread). These were seen for every same-take pair of every song.
  - The rule's thresholds were fixed after 4 songs. Seeing the rest changed only the
    name of one failure reason ("duplicate raw tracks"), which changes no outcome.
- **File metadata:** frame counts, to check that the raws and the mix share a timeline.
- **No other audio feature** was read, and no method result exists on set 6.

## Leakage guards

- **`learn/set6.py`:**
  - `is_held_out` and `refuse` cover every MedleyDB band, session key and crop slug;
  - they also cover any path under `~/ndsp-presets/references/datasets-medleydb/` or
    `validation-crops-set6/`, listed or not;
  - `parts(scope=...)` selects in-scope or report-only parts.
- **`learn.set3`:**
  - `is_held_out` returns True for set-6 material;
  - `fold_for_band` raises on a set-6 band;
  - `training_dis` refuses any set-6 file.
- **Tests:** `tests/test_set6.py`. The crop and rebuild tests are skipped on a machine
  without the data.
