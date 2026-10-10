# Set 4: fresh held-out confirmation set, declared

Declared 2026-10-10 under [validation-set4-plan.md](validation-set4-plan.md), committed
before this file, and extended the same day by the plan's amendment 1 (four Internet
Archive sessions, committed before they were downloaded). **Every band is held out, and
the set is unused.** Nothing may train,
tune or choose on it, and nobody listens to it, until a confirmation is declared in a
committed file. That use is then added to `held_out_uses`.

`docs/validation-set4.json` is the machine-readable declaration. It holds:

- the catalogue's SHA-256;
- every kept part, with its crop hashes;
- every excluded part, with its reasons;
- every session with its DIs.

`research/validation_set4.py` rebuilds it from the catalogue
(`~/ndsp-presets/references/datasets-set4/catalog.json`) and the crop records
(`~/ndsp-presets/references/validation-crops-set4/<slug>/record.json`) alone. The tools
that built those are in `~/ndsp-presets/references/datasets-set4/_tools/`. They are set
3's, copied with paths changed: `gcc.py`, `gainmeasure.py` and `classify.py` are
byte-identical. For amendment 1 they gained only the four sessions' entries, a record of
deleted archives, and a crop step that leaves existing crops alone. The first five
sessions' measures and crop records are byte-for-byte as first built. No audio is in git.

## What was done to it

- **Done:** the pairing tests, gain measures, clipping and lags for each declared part,
  then the 10-s crops (rule `di-activity`, 48 kHz).
- **Not done:** no plugin ran, no render was made, no preset was scored, no network was
  run on it and nothing was listened to.

## Counts

52 parts were declared by name (21, then 31 by amendment 1). 35 are kept (24 tones; a
`DT` double counts with its original), and 17 are excluded. Gain class is the
session-level `gain_class`.

| band – song | route | kept | tones | high-gain | crunch | clean | excluded |
|---|---|---|---|---|---|---|---|
| Decypher – Unseen | direct | 4 | 2 | 4 | 0 | 0 | 0 |
| Last Legacy – Who's Who In Hell | direct | 2 | 2 | 0 | 2 | 0 | 0 |
| Lead Inc – The Inner Circle | direct | 3 | 3 | 1 | 2 | 0 | 0 |
| The Black Crown – Flames | direct | 2 | 1 | 2 | 0 | 0 | 0 |
| Tholas P. – Such Fine People | direct | 2 | 1 | 2 | 0 | 0 | 8 |
| Umbriferous – Sandcastles (Illusion) | Wayback | 10 | 5 | 4 | 6 | 0 | 1 |
| The Bright Star Alliance – Error 404 | Wayback | 7 | 5 | 6 | 1 | 0 | 0 |
| Sonnet & Alcohol – Back To The Nineties | Wayback | 2 | 2 | 0 | 0 | 2 | 0 |
| The Laminar Flow – Headspace | Wayback | 3 | 3 | 2 | 1 | 0 | 8 |
| **total** | | **35** | **24** | **21** | **12** | **2** | **17** |

- **Band strata** (the most common class over a band's tones, as set 3):
  - high-gain: Decypher, The Black Crown, Tholas P., The Bright Star Alliance and The
    Laminar Flow;
  - crunch: Last Legacy, Lead Inc and Umbriferous;
  - clean: Sonnet & Alcohol.

  These counts are description only, since there is no draw.
- **Sonnet & Alcohol reads clean, firmly.** Both parts are firm "clean" on
  `clean_vs_driven` (level slope 1.23 and 0.73; non-linear share −19.9 and −8.7 dB). The
  crunch-or-high-gain rule of amendment 1 covers The Laminar Flow only, so they are kept
  under set 3's rule, as declared. A heavy-only confirmation would drop them by its own
  declaration.
- **The Laminar Flow's added rule excluded nothing.** All 11 of its parts classify crunch
  or high-gain. Its 8 exclusions are set 3's window rule (below).
- **`clean_vs_driven`:** 30 kept parts are firm "driven", 2 firm "clean" (Sonnet &
  Alcohol) and 3 "uncertain" (all The Laminar Flow kept parts: non-linear share −1.5 to
  −2.6 dB, under the 0 dB "driven" line).
- **Crunch against high-gain stays an ordinal reading.** Several parts sit near the 0.1
  level-slope line: the four crunch parts of the first five (0.115–0.133), The Bright
  Star Alliance ElecGtr3 (0.090) and ElecGtr4 (0.134), and The Laminar Flow ElecGtr07
  (0.068) and ElecGtr08 (0.089).
- **The crop class agrees with the session class on 27 of 35.** Prefer the session class,
  as set 3 found. The Bright Star Alliance ElecGtr2's crop reads clean against a
  high-gain session.
- **The bands are uneven again:** Umbriferous has 10 parts and The Bright Star Alliance
  7; six bands have 2 or 3. With amendment (4)'s 1/n weighting each band counts once.
- **What this can confirm:** see the plan's power section. With 9 bands, an effect near
  set 3's observed −0.143 has very roughly 60–70% power; the realistic −0.072 stays near
  15%. A band sign-flip test has 512 sign patterns, so p < 0.1 no longer needs every band
  to agree. A confirmation plan must redo the power calculation for its own measure.

## Exclusions

The rules are set 3's, unchanged. Set 4's JSON lists every declared part that is not
kept, with its reasons.

### Tholas P. (8)

- **ElecGtr01: fails both same-take tests.** The waveform test has 3 windows, 33% in step,
  with a ratio of 1.03 (null). The amp track is 50.7 s long against a 140.1-s DI, so it
  is a different take or an edit.
- **ElecGtr01DT: the waveform test is at null over 3 windows** (ratio 1.07), although the
  envelope tests pass. This is set 3's "not the same take" rule. Its amp track is also
  50.7 s long.
- **ElecGtr04 and ElecGtr05: fails both same-take tests,** with no 20-s window where both
  tracks play.
  - Both tracks of each part play only about 4 s, at 132–139 s of a 139.7-s file, which
    is after the last full 20-s test window.
  - The windowed tests therefore see nothing, and set 3's rule leaves the part
    unpaired.
  - A 4-s part could not fill a 10-s crop in any case.
- **ElecGtr06, 07 and 08: the waveform test passes on 2 windows,** fewer than 3.
- **ElecGtr09: the waveform test passes on 1 window.** It passes the envelope tests too.
  Set 3 applies the 3-window rule whichever test passes.

### The Laminar Flow (8)

- **ElecGtr02, 03 and 11: the waveform test passes on 1 window;** ElecGtr04, 05, 09 and
  10 on 2. All are fewer than 3. These are short or sparse parts: each passing window is
  in step, but there are too few windows where both tracks play.
  - ElecGtr02, 09, 10 and 11 pass the envelope tests (their Mic1, or Mic2 for ElecGtr02).
    Set 3 applies the 3-window rule whichever test passes.
- **ElecGtr06: fails the waveform test.** It passes the envelope tests on all three
  microphones, but its single waveform window has a ratio of 1.60, under 2.0 (not at
  the 1.4 null line, so it is not ruled a different take).

### Umbriferous (1)

- **ElecGtr6: the waveform test passes on 1 window,** fewer than 3. Its DI is 102.9 s
  long.

Crops were cut for every part a pairing test accepted before the window rule excluded it,
as set 3 did. They stay held out like everything else.

**Not parts (no DI):** Tholas P. ElecGtr02 and 02DT, Last Legacy ElecGtr03–07, The Black
Crown ElecGtr2 and 3, and The Laminar Flow `ElecGtr01DTMic1–3` (JSON `unpaired`). They
stay in each session's mix.

**Reported differently from set 3.** Set 3's JSON listed in `excluded` only parts its
catalogue already called usable. Set 4 lists all 52 declared parts, so Tholas P.
ElecGtr01, 01DT, 04 and 05 appear with their pairing failure. The rules are the same.

## Kept, with marks and notes

- **Pairing:** every kept part passes the waveform test, on 3–31 windows.
  - The first five sessions' kept parts pass on 19–31 windows and none passes the envelope
    test, which distortion defeats, as in set 3.
  - Of amendment 1's 22 kept parts, 9 also pass the envelope tests (`pairing_test:
    "envelope+waveform"`): Umbriferous ElecGtr1–3 and their DTs, both Sonnet & Alcohol
    parts and The Bright Star Alliance ElecGtr3.
  - The thinnest evidence: The Laminar Flow ElecGtr07 and 08 pass on exactly 3 windows,
    The Bright Star Alliance ElecGtr5 and 5DT on 4.
- **References:** the reference is Mic1 for Decypher, Lead Inc and the three kept Laminar
  Flow parts. The other microphones are alternates, and are left out of the mix as set 3
  did.
- **`di_touches_full_scale`:** all four Decypher parts, with 1, 1, 5 and 6 flat-topped
  runs, under the 10-run line.
- **`amp_earlier_than_di`:** both Last Legacy parts. The amp track is 1 sample (0.02 ms)
  earlier than the DI.
  - A lag this close to zero means no acoustic path: a reamp with latency compensation,
    or a simulator.
  - The readme does not say which. They are kept, as set 3 keeps marked parts. A
    confirmation decides by its own declaration whether to drop them.
- **`late_amp_track`:** Lead Inc ElecGtr3, 7.1 ms (339 samples at 48 kHz). All four of
  its microphones sit within 0.2 ms of each other, so this is latency or a reamp, not a
  far microphone. Its onset check is unclear.
- **Amendment 1's sessions carry no mark.** Their lags are 10–20 samples at 48 kHz
  (Umbriferous), 24–40 (Sonnet & Alcohol), 26–29 (The Laminar Flow) and 98–152 (The
  Bright Star Alliance, 2.0–3.2 ms). None is over 5 ms or earlier than the DI, and no DI
  touches full scale.
- **Polarity −1:** both Last Legacy parts, Lead Inc ElecGtr1 and 2, Sonnet & Alcohol
  ElecGtr1, six of the seven Bright Star Alliance parts (all but ElecGtr5) and all three
  kept Laminar Flow parts.
- **Onset cross-check:** it agrees on 30 parts, is unclear on 3 (Decypher ElecGtr01DT,
  Lead Inc ElecGtr3, The Bright Star Alliance ElecGtr1) and disagrees on 2 (Umbriferous
  ElecGtr4DT and 5DT). It is a recorded cross-check only; the declared lag is unchanged.
- **Lags:** the declared lag is the waveform lag, never re-measured. `judge_lag_samples`
  is `lag_samples − 52`.

## Deviations from set 3

These are the ones the plan stated:

1. parts declared by hand from file names;
2. Decypher's `ElecGtr02DIMic1/2` taken as microphones. The mix rule takes DIs from the
   declared parts, so those are mixed as amp tracks;
3. no split, folds or draw;
4. amendment 1: four sessions from Internet Archive copies of the publisher's files, and
   The Laminar Flow kept to crunch or high-gain parts (it excluded none).

Resampling 44.1 → 48 kHz for the crops is the same as set 3's. Gain thresholds were not
recalibrated. Nothing else changed.

## Disclosure: what the building agent saw

- **Catalogue fields and crop records:** per-part pairing statistics, gain measures,
  clipping, lags and crop starts, as set 3's builder did.
- **Signal levels of four Tholas P. tracks:** to explain why ElecGtr04 and 05 had no
  test window, the agent printed, for `33/34_ElecGtr04(DI)` and `35/36_ElecGtr05(DI)`:
  - where the samples were non-zero;
  - the seconds above −60 dBFS.

  It read no other audio feature.
- **Amendment 1:** the same, and nothing more. No signal level or other audio feature of
  the four new sessions was read beyond the catalogue fields and crop records.
- **No method result exists on set 4.**

## Leakage guards

- **`learn/set4.py`:** `is_held_out` and `refuse` cover every set-4 band, session key and
  crop slug. They also cover any path under `~/ndsp-presets/references/datasets-set4/`
  or `validation-crops-set4/`, listed or not.
- **`learn.set3`:** `is_held_out` returns True for set-4 material, `fold_for_band` raises
  on a set-4 band, and `training_dis` refuses any set-4 file, whatever band it is
  labelled with.
- **Tests:** `tests/test_set4.py`. The rebuild test is skipped on a machine without the
  catalogue.

## Licences

The licences are in the plan and the JSON's `licences`. In short:

- all nine are Cambridge "educational purposes only", no commercial use; amendment 1's
  four came through the Internet Archive (URLs, capture times and hashes in the plan);
- Lead Inc is also CC BY-NC-SA 3.0;
- Tholas P. is also "All rights reserved", with mix-upload terms.
