# Set 6: MedleyDB as a held-out validation set, declared

Declared 2026-10-12, under set 5's rules ([validation-set5.md](validation-set5.md)), with
one addition. MedleyDB names no DI, so a declared **DI-role rule** says which track of a
same-take pair is the DI.

**Every band is held out, and the set is unused.** Nothing may train, tune or choose on
it, and nobody may listen to it, until a confirmation is declared in a committed file.
That use is then added to `held_out_uses`, which is empty.

**Scope.** As in set 5:

- clean and crunch parts are in scope;
- high-gain parts are report-only, set by each part's session-level gain class.

That makes Big Troubles and Purling Hiss report-only.

**The headline: MedleyDB gives few parts.** Only 5 of its 73 songs on disk give a kept
part, from 5 bands. In scope are **3 clean parts from 3 bands, and no crunch part**.

- Most same-take pairs in MedleyDB are not a DI and its amp track. They are two
  microphones on one amp, or duplicate files.
- **So set 6 adds nothing to the crunch side of the combined set-5 + MedleyDB stem test**
  ([set5-test-plan.md](set5-test-plan.md)). That test's plan should say so before any
  power calculation.

`docs/validation-set6.json` is the machine-readable declaration. It holds:

- the inventory's SHA-256;
- every song, with its provenance;
- every kept part, with its evidence pointers and crop hashes;
- every excluded part, and every same-take pair that did not establish a DI, with
  reasons.

`research/validation_set6.py declare` rebuilds the JSON from two sources alone: the
inventory (`~/ndsp-presets/references/datasets-medleydb/inventory.json`) and the crop
records (`~/ndsp-presets/references/validation-crops-set6/<slug>/record.json`).
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
- **Licence:** Creative Commons BY-NC-SA 4.0 (`LICENSE-V1.txt` in the dataset root).
  - Non-commercial research only.
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

## The DI-role rule (new in set 6)

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

## Kept

| part (song, DI → reference) | class | scope | branch | lag (48 kHz) | windows | notes |
|---|---|---|---|---|---|---|
| Aimee Norwich – Flying, RAW_05_02 → 05_01 | clean | in | clean | 26 | 19 | polarity −1 |
| Dahka Band – Soldier Man, RAW_04_01 → 04_02 | clean | in | clean | 23 | 31 | has_bleed |
| Steven Clark – Bounty, RAW_01_04 → 01_02 | clean | in | clean | 25 | 3 | thinnest evidence; DI plays in 80% of the crop |
| Big Troubles – Phantom, RAW_05_01 → 05_02 | high-gain | report-only | driven | 67 | 13 | DI crest 19 dB against 11 dB; onset unclear |
| Purling Hiss – Lolita, RAW_03_06 → 03_05 | high-gain | report-only | driven | 32 | 24 | polarity −1; has_bleed; DI labelled clean, amp distorted |

- **Counts:**
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
