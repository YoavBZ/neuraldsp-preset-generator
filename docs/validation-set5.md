# Set 5: fresh held-out validation set, declared

Declared 2026-10-12, under set 4's rules ([validation-set4.md](validation-set4.md)).
Set 4's plan was committed before its data was fetched. Set 5 has no separate plan:
its candidate inventory (2026-10-11) was built first, with set 4's rules and
thresholds unchanged.

**Every band is held out, and the set is unused.** Nothing may train, tune or choose on
it, and nobody may listen to it, until a confirmation is declared in a committed file.
That use is then added to `held_out_uses`, which is empty.

**Scope.** Clean and crunch parts are in scope. High-gain parts are report-only: they
are listed and may be reported, but a set-5 decision never counts them. This follows
the project scope (no heavy metal). Each part carries a `scope` field ("in_scope" or
"report_only"), set by its session-level gain class. That makes all four Nova-One
Studio parts and Saturn Syndicate ElecGtr4 report-only.

`docs/validation-set5.json` is the machine-readable declaration. It holds:

- the inventory's SHA-256;
- every session, with its provenance and DIs;
- every kept part, with its evidence pointers and crop hashes;
- every excluded part, with its reasons.

`research/validation_set5.py declare` rebuilds the JSON from two sources alone: the
inventory (`~/ndsp-presets/references/datasets-set5/inventory.json`) and the crop
records (`~/ndsp-presets/references/validation-crops-set5/<slug>/record.json`).
`research/validation_set5.py crops` cut the crops.

The pairing scripts are in `tmp/set5/` on the main checkout. Their per-pair evidence is
in `~/ndsp-presets/references/datasets-set5/_tools/pairs/<session>.json`, and the
archive hashes and readmes are in `_tools/archives.json` and `_tools/hf_files.json`.
No audio is in git.

## What was done to it

- **Done:**
  - download, hashing and licence capture;
  - the same-take pairing tests, with every DI against every electric-guitar track of
    its session;
  - lags and polarity, from DI-to-amp cross-correlation;
  - set 3's gain classifier (`classify.py`, `gainmeasure.py`, the same bytes as set
    4's tools; hashes in the JSON);
  - the 10-s crops (crop rule 2, `di-activity`, 48 kHz mono);
  - on each crop, the onset cross-check and the crop-level gain class.
- **Not done:** no plugin ran, no render was made, nothing was scored (no judge, no
  `measure`, no `aligned_distance`), no network was run on it, nothing was listened
  to, and no tone or preset was compared.

## Sessions and provenance

There are 14 sessions by 12 bands. Seven bands have at least one kept part.

| band – song | source | kept | tones | clean | crunch | high-gain | excluded | mix on disk |
|---|---|---|---|---|---|---|---|---|
| Ronnie Jones – Why Don't You Stay | Cambridge direct | 9 | 9 | 8 | 1 | 0 | 1 | no |
| Hazael – A Mi Lado | Cambridge direct | 2 | 2 | 2 | 0 | 0 | 1 | yes |
| Hazael – Resistencia Para Un Nuevo Comenzar | Cambridge direct | 2 | 2 | 2 | 0 | 0 | 0 | yes |
| BKS – Too Much | Cambridge direct | 4 | 4 | 3 | 1 | 0 | 1 | no |
| BKS – Bulldozer | Cambridge direct | 5 | 5 | 1 | 4 | 0 | 2 | no |
| Saturn Syndicate – Never Leave The Night Alone | Cambridge via Wayback | 3 | 2 | 0 | 2 | 1 | 3 | no |
| Nova-One Studio – Four Graham | Cambridge direct | 4 | 4 | 0 | 0 | 4 | 1 | yes |
| The Ferryboat Men – The Winds Of Gypsy Moor | HF re-host | 1 | 1 | 0 | 1 | 0 | 2 | no |
| Fytakyte – Too Much | HF re-host | 1 | 1 | 0 | 1 | 0 | 1 | no |
| Chris Durban – Celebrate | Cambridge direct | 0 | 0 | | | | 1 | no |
| Peter White – Crazy Girl | Cambridge direct | 0 | 0 | | | | 5 | yes |
| Hannes Keseberg – You Know Better | Cambridge direct | 0 | 0 | | | | 1 | no |
| Jeff Hirata – Sunshine | HF re-host | 0 | 0 | | | | 8 | no |
| MOPP – Ukraina | HF re-host | 0 | 0 | | | | 1 | no |
| **total** | | **31** | **30** | **16** | **10** | **5** | **28** | |

- **Counts:** 59 parts were declared (one per DI), 31 kept and 28 excluded. The
  kept parts are 30 tones (Saturn Syndicate ElecGtr3DT counts with its original).
- **In scope:** 26 parts from 6 bands, 16 clean and 10 crunch. Report-only: 5
  high-gain parts.
- **Band strata,** the most common class over a band's tones, with ties going to the
  cleaner class as in set 3:
  - clean: Ronnie Jones and Hazael;
  - crunch: BKS, Saturn Syndicate, The Ferryboat Men and Fytakyte;
  - high-gain: Nova-One Studio (report-only).

  BKS is really mixed (4 clean, 5 crunch). These strata are description only, since
  there is no draw.
- **Publisher originals:** 10 Cambridge archives (`publisher_original: true`). Nine
  were fetched direct from `mtkdata.cambridgemusictechnology.co.uk`. Saturn Syndicate
  came from the Internet Archive capture `20241217203914` of the publisher's file
  (bytes as captured).
  - Each archive passed `unzip -t` and its length check, and was hashed (SHA-256 in
    the JSON). The zip was then deleted to save disk.
  - Before a crop was cut, each source WAV was checked against its archive member's
    byte length.
- **Hugging Face re-host:** 4 sessions, of which The Ferryboat Men and Fytakyte have
  kept parts. They come from `kwatcharasupat/mixing-secrets-rawstems`, pinned at
  revision `b482eb2e31aa15ff10489b3b23871a1e7a109198`. Only the electric-guitar files
  were fetched. Each file was checked against its LFS SHA-256 when fetched, and again
  before a crop was cut.
  - These are third-party copies, not the publisher's files: 48 kHz stereo FLAC with
    identical channels, renamed, and with tracks trimmed to different lengths.
  - Their lags were measured on the files as stored, and the crops are cut in the same
    coordinates.
  - The two kept re-host parts rest on one part per band.
- **Mix absent on 23 of 31 kept parts.** Six Cambridge archives were unpacked
  guitar-only for disk space: Ronnie Jones, both BKS songs, Saturn Syndicate, Chris
  Durban and Hannes Keseberg. The re-hosts were fetched guitar-only too.
  - Their crops are `di.wav` and `reference.wav` only, with `"mix_absent": true` in
    each record.
  - Hazael (both songs) and Nova-One were unpacked in full. Their crops also have
    `mix`, `backing`, `mix_instrumental` and `backing_instrumental`, built by set 4's
    mix rule. That rule takes every session WAV except the guitar DIs, the kept parts'
    alternate amp tracks, rendered mixes, click tracks and other DI-named guitar
    tracks.
  - A mix for the other sessions needs a re-download checked against the recorded
    archive SHA-256. None was made: the disk had 24 GiB free, under the 33 GB floor.

## Licences

- **Cambridge (all 10 archives):** each Readme says "provided for educational
  purposes only… should not be used for any commercial purpose without the express
  permission of the copyright holders". There is no other licence file.
- **BKS:** the band is gone from the current Cambridge library page, though it was on
  the 2017 page. The files are still served (`licence_extra`).
- **Saturn Syndicate:** the publisher's file, taken from an Internet Archive capture.
- **Hugging Face re-host:** the dataset card says "strictly … only for non-commercial
  research and educational purposes. No commercial use of any data derived from Mixing
  Secrets is permitted". The publisher's own terms (Cambridge, above) also apply.

## Rules

The rules are set 4's, unchanged (`rules` in the JSON):

- **Same take:** the waveform test passes, with 80% or more of 20-s windows in step
  and a median peak-to-sidelobe ratio of 2.0 or more.
- **Exclusions:**
  - fewer than 3 passing windows;
  - a clipped DI (10 or more flat-topped runs);
  - two lag clusters;
  - a modeller (Pod/GR4) as the reference;
  - an amp track that belongs to another DI.
- **Reference:** set 4's AMP_PREFERENCE among the amp tracks the names declare. When
  none of those passes, the passing track is used, and the part is marked
  `reference_not_name_declared`.
- **Crop:** crop rule 2 (`docs/validation-datasets.md`). The window is the 10 s where
  the DI plays in the most frames, with first-sample alignment, and the session
  length comes from the DI.
  - A crop is cut for every part whose reference passed a same-take test and is its
    own, not a modeller's, as set 4 did.
  - Some crops belong to parts the window rule then excluded: Saturn Syndicate
    ElecGtr1, 1DT and 2, Chris Durban ElecGtr3a and Nova-One ElecGtr03. These stay
    held out like everything else.
- **Lags:** `lag_samples` is the inventory's waveform lag converted to 48 kHz. It is
  never re-measured. `judge_lag_samples = lag_samples − 52`. The lag is positive when
  the amp track is later. The polarity is the waveform test's.
- **Gain class:** both levels are recorded, as in set 4.
  - `gain_class` is session-level: the part's whole session, amp against DI.
  - `gain_class_crop` is the same classifier on the crop.

  Prefer the session class. Crunch against high-gain stays an ordinal reading.
- **Split:** every band held out, with no draw and no folds. For band weighting, set
  3's amendment (4) is recommended: each band's parts weigh 1/n. A confirmation plan
  adopts or overrides it explicitly.

## Kept, with marks and notes

- **Pairing:** every kept part passes the waveform test, on 3–25 windows.
  - 21 parts also pass the envelope tests (`pairing_test: "envelope+waveform"`).
  - The thinnest evidence:
    - Ronnie Jones ElecGtr06 and 07 pass on 3 windows, and ElecGtr09 and 10 on 4;
    - BKS Too Much ElecGtr5a and Nova-One ElecGtr05 pass on 4;
    - Saturn Syndicate ElecGtr4 and BKS Bulldozer ElecGtr7a pass on 5.
- **References that are not the declared amp track** (`reference_not_name_declared`):
  - all four Nova-One parts, where the names do not match the waveforms (DI01 →
    ElecGtr02, DI02 → ElecGtr03, DI04 → ElecGtr08, DI05 → ElecGtr10);
  - Fytakyte ElecGtr2DI → ElecGtr6.
- **Reference choices to note:**
  - Ronnie Jones ElecGtr03 uses `ElecGtr03Dry`, with the main `ElecGtr03` as an
    alternate.
  - BKS Bulldozer ElecGtr7a uses Reamp2, because Reamp1 has two lag clusters.
  - BKS amp tracks are reamps.
- **Polarity −1** (`polarity_inverted`), on 12 parts:
  - Ronnie Jones ElecGtr03, 06 and 07;
  - Hazael A Mi Lado ElecGtr1;
  - BKS Too Much ElecGtr3a;
  - Saturn Syndicate ElecGtr4;
  - all four Nova-One parts;
  - The Ferryboat Men ElecGtr4DT;
  - Fytakyte ElecGtr2.
- **`amp_earlier_than_di`:** Hazael Resistencia ElecGtr1 and 2. The amp track is
  earlier than the DI, by 19 and 2 samples at 48 kHz.
- **`di_touches_full_scale`:** Nova-One ElecGtr01, with 4 flat-topped runs, under the
  10-run line.
- **`crop_di_plays_under_half`:** Ronnie Jones ElecGtr05. The DI plays in 22% of its
  crop's frames, which is rule 2's best 10 s for that DI. It is kept, as set 3 kept
  Prodigal ElecGtr4.
  - Four other crops are under 90%: Ronnie Jones ElecGtr03 (66%) and ElecGtr06 (71%),
    and Nova-One ElecGtr04 (68%) and 05 (64%).
- **Lags at 48 kHz:**

  | band – song | lag (samples) |
  |---|---|
  | Ronnie Jones | 41–48 |
  | Hazael – A Mi Lado | 61–69 |
  | Hazael – Resistencia | −19 and −2 |
  | BKS – Too Much | 147–177 (3.1–3.7 ms) |
  | BKS – Bulldozer | 26–36 |
  | Saturn Syndicate | 22–27 |
  | Nova-One | 16–22 |
  | The Ferryboat Men | 9 |
  | Fytakyte | 148 (3.1 ms) |

  None is over 5 ms.
- **Onset cross-check:** it agrees on 28 parts and is unclear on 3: Ronnie Jones
  ElecGtr03, and Nova-One ElecGtr04 and 05. It is a recorded cross-check only; the
  declared lag is unchanged.
- **Crop class against session class:** they agree on 29 of 31. BKS Bulldozer
  ElecGtr5a and Saturn Syndicate ElecGtr3 read high-gain on the crop and crunch over
  the session. They stay in scope under the session class.
- **`clean_vs_driven`:**
  - 11 parts are firm "clean";
  - 8 are firm "driven";
  - 12 are "uncertain", including all five BKS Bulldozer parts.

## Exclusions

Every declared part that is not kept is listed in the JSON, with its reasons.

- **One passing part lost to the crop rule.** Hazael A Mi Lado ElecGtr3 passed the
  same-take test (20 windows). But crop rule 2's window, where its DI plays most, has
  no measurable reference loudness ("reference has no measurable 10-second excerpt").
  - With no crop, the part is excluded, as set 4 would exclude it.
  - The failure is recorded in `validation-crops-set5/crops_failed.json`.
  - Nothing more of its audio was read.
- **Window rule:** Saturn Syndicate ElecGtr1 and 1DT pass on 2 windows, and ElecGtr2
  on 1.
- **Not their own take, or a modeller:**
  - BKS Too Much ElecGtr4a: its only passing amp track is ElecGtr2's reamp, so its DI
    looks like a copy of DI2.
  - BKS Bulldozer ElecGtr3a: the only passing reference is a Pod.
  - BKS Bulldozer ElecGtr6a: the only passing reference is a GR4, on 1 window, and it
    belongs to ElecGtr1.
- **Waveform test fails:**
  - Chris Durban ElecGtr3a: 79% of 14 windows in step, against the 80% needed.
  - Nova-One ElecGtr03 (DI03): an envelope-only match, at waveform null on 1 window.
- **No amp track passes the same-take tests:**
  - Ronnie Jones ElecGtr08;
  - all 5 Peter White DIs;
  - Hannes Keseberg ElecGtr2;
  - The Ferryboat Men ElecGtr3 and 4;
  - all 8 Jeff Hirata DIs;
  - Fytakyte ElecGtr3;
  - MOPP ElecGtr1.

  On the re-hosts, a global-offset diagnostic found no match either
  (`_tools/hf_offset_diagnostic.json`).

**Not parts (no DI):** guitar amp tracks named for no DI are listed in the JSON's
`unpaired`. Examples are Hazael A Mi Lado ElecGtr4–6 and Nova-One ElecGtr07 and 09.
In the full sessions they stay in the mix.

## Deviations from set 4

1. **No separate plan.** The inventory came first, under set 4's rules and
   thresholds.
2. **A scope field.** High-gain parts are report-only.
3. **Re-host material.** Two kept parts come from a third-party Hugging Face re-host
   at a pinned revision, not from the publisher.
4. **Crops cut by `research/validation_set5.py`,** not `build_validation_crops.build`.
   - That tool reads only WAVs, and needs a mix declaration for every session.
   - The set-5 code uses the same window function (`_window_by_di`) and the same
     fitting and float32 policy.
   - Where the mix is on disk, it applies set 4's mix rule.
5. **Two new marks,** `polarity_inverted` and `reference_not_name_declared`, and a
   crop mark, `crop_di_plays_under_half`. These are descriptive only.
6. **Unknown gain measures are null.** A gain measure with no window (NaN in the
   inventory) is written as JSON null in the crop records.

Resampling 44.1 → 48 kHz is as in sets 3 and 4. Gain thresholds were not recalibrated.

## Disclosure: what the building agent saw

- **Inventory fields and crop records:** pairing statistics, gain measures, clipping,
  lags, crop starts, DI activity and the onset cross-check, as set 4's builder did.
- **Crop failure:** the error text of Hazael A Mi Lado ElecGtr3's crop failure.
- **No other audio feature** was read, and no method result exists on set 5.

## Leakage guards

- **`learn/set5.py`:**
  - `is_held_out` and `refuse` cover every set-5 band, session key and crop slug.
  - They also cover any path under `~/ndsp-presets/references/datasets-set5/` or
    `validation-crops-set5/`, listed or not, failed sessions included.
  - `parts(scope=...)` selects in-scope or report-only parts.
- **`learn.set3`:**
  - `is_held_out` returns True for set-5 material.
  - `fold_for_band` raises on a set-5 band.
  - `training_dis` refuses any set-5 file, whatever band it is labelled with.
- **Tests:** `tests/test_set5.py`. The crop and rebuild tests are skipped on a machine
  without the data.

**Earlier sets.** Nova-One Studio appears in set 3's `not_obtained` list. It was never
fetched or used there. No set-5 band is in sets 1–4.
