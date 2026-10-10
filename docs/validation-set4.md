# Set 4: fresh held-out confirmation set, declared

Declared 2026-10-10 under [validation-set4-plan.md](validation-set4-plan.md), committed
before this file. **Every band is held out, and the set is unused.** Nothing may train,
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
byte-identical. No audio is in git.

## What was done to it

- **Done:** the pairing tests, gain measures, clipping and lags for each declared part,
  then the 10-s crops (rule `di-activity`, 48 kHz).
- **Not done:** no plugin ran, no render was made, no preset was scored, no network was
  run on it and nothing was listened to.

## Counts

21 parts were declared by name. 13 are kept (9 tones; a `DT` double counts with its
original), and 8 are excluded. Gain class is the session-level `gain_class`. Every kept
part reads firm "driven" (`clean_vs_driven`).

| band – song | kept | tones | high-gain | crunch | excluded |
|---|---|---|---|---|---|
| Decypher – Unseen | 4 | 2 | 4 | 0 | 0 |
| Last Legacy – Who's Who In Hell | 2 | 2 | 0 | 2 | 0 |
| Lead Inc – The Inner Circle | 3 | 3 | 1 | 2 | 0 |
| The Black Crown – Flames | 2 | 1 | 2 | 0 | 0 |
| Tholas P. – Such Fine People | 2 | 1 | 2 | 0 | 8 |
| **total** | **13** | **9** | **9** | **4** | **8** |

- **Band strata** (the most common class over a band's tones, as set 3): four bands are
  high-gain and Last Legacy is crunch. There is no clean part. These counts are
  description only, since there is no draw.
- **The crunch parts sit near the boundary.** All four have a level slope of 0.115–0.133,
  just above the 0.1 high-gain line. Their catalogue reason is "level slope near a class
  boundary".
- **The crop class reads high-gain on 12 of 13,** as set 3 found: a 10-s crop dilutes the
  slope. Prefer the session class.
- **The bands are fairly even now:** 4, 3, 2, 2 and 2 parts. Tholas P. lost 8 of its 10.
- **What this can confirm:** see the plan's power section. With 5 bands, only
  oracle-sized effects. A band sign-flip test can reach p < 0.1 only if all five bands
  agree.

## Exclusions (all Tholas P.)

The rules are set 3's, unchanged.

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

Crops were cut for ElecGtr06–09 before the window rule excluded them, as set 3 did for
its excluded parts. They stay held out like everything else.

**Not parts (no DI):** Tholas P. ElecGtr02 and 02DT, Last Legacy ElecGtr03–07, and The
Black Crown ElecGtr2 and 3 (JSON `unpaired`). They stay in each session's mix.

**Reported differently from set 3.** Set 3's JSON listed in `excluded` only parts its
catalogue already called usable. Set 4 lists all 21 declared parts, so ElecGtr01, 01DT,
04 and 05 appear with their pairing failure. The rules are the same.

## Kept, with marks and notes

- **Pairing:** every kept part passes the waveform test on 19–31 windows. None passes the
  envelope test, which distortion defeats, as in set 3, so each is recorded as
  `pairing_test: "waveform"`.
- **References:** the reference is Mic1 for Decypher and Lead Inc. The other
  microphones are alternates, and are left out of the mix as set 3 did.
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
- **Polarity −1:** both Last Legacy parts and Lead Inc ElecGtr1 and 2.
- **Onset cross-check:** it agrees on 11 parts and is unclear on 2 (Decypher ElecGtr01DT,
  Lead Inc ElecGtr3). It disagrees on none.
- **Lags:** the declared lag is the waveform lag, never re-measured. `judge_lag_samples`
  is `lag_samples − 52`.

## Deviations from set 3

These are the ones the plan stated:

1. parts declared by hand from file names;
2. Decypher's `ElecGtr02DIMic1/2` taken as microphones. The mix rule takes DIs from the
   declared parts, so those are mixed as amp tracks;
3. no split, folds or draw.

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

- all five are Cambridge "educational purposes only", no commercial use;
- Lead Inc is also CC BY-NC-SA 3.0;
- Tholas P. is also "All rights reserved", with mix-upload terms.
