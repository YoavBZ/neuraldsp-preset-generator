# Set 3: heavier-tone validation recordings, and its split

**Use recorded 2026-10-08:** the 27 reserved parts were used in the approved one-time
confirmation and its predetermined independent checks. Neither tested amp passed
([results](set3-heldout-confirmation-results.md)). This reserved split is spent and
remains excluded from training, tuning and new confirmations. The completed use is
recorded in [set3-heldout-use-ledger.json](set3-heldout-use-ledger.json). The original
manifest-pinned `validation-set3.json` snapshot, including its then-empty
`held_out_uses`, is preserved unchanged for provenance; the ledger adds the completed
use without rewriting that frozen input. Rules below describe the original split.

Sets 1 and 2 ([validation-datasets.md](validation-datasets.md)) are mostly clean and
crunch rock. Set 3 adds heavier tones: 27 sessions searched and downloaded for crunch and
high-gain guitar recorded both as a DI and as an amp track of the same take, catalogued in
`~/ndsp-presets/references/datasets-set3/catalog.json`. This file is Phase 0 S of
[di-recovery-plan.md](di-recovery-plan.md). It declares which parts count, which bands are
held out and the folds over the rest, before any match, model, judge or listening test
touches the parts. The declaration time is the commit that adds this file.

When this was declared, set 3 had been checked only for pairing (both tests below), clipping,
lag and the catalogue's gain measures. Its 10-s crops had been cut, and nothing else.
This declaration read only the catalogue's fields and the crop records. No plugin ran, no
render was made, and no match, model, judge or listening score exists on set 3.

`docs/validation-set3.json` is the machine-readable declaration. It holds the catalogue's
SHA-256, every kept part, every excluded part with its reasons, every session with its
split and fold, the counts and the draw. `research/validation_set3.py` rebuilds it from the
catalogue and the crop records alone. `learn/set3.py` loads it and returns parts by split
and fold, and the sessions a fold's network may train on.

## Which parts count

### The same-take test is the waveform test

This is a stated departure from the repository's rule. Sets 1 and 2 count a part as the
same take when the 10-ms *envelopes* of its DI and amp track agree, over the whole length
and in step in 20-s windows. Distortion defeats that test: a high-gain amp flattens the
envelope, so parts that are plainly the same take fail it. Of the catalogue's 77 usable
parts, only 14 pass the envelope test, and only 4 of those are crunch.

Set 3 therefore uses the waveform test (catalogue `rules.supplementary_pairing`, the
catalogue tools' `gcc.py`). It runs GCC-PHAT, 80 Hz–4 kHz, of the amp track against the
DI in the same 20-s windows every 10 s, counting the windows where both tracks are within
30 dB of their loudest. The peak is taken on the Hilbert envelope of the GCC curve, so an
inverted or phase-rotated amp track is handled, and its polarity is recorded.

- **Same take:** at least 80% of windows within ±1 ms of the median lag, and a median
  peak-to-sidelobe ratio of 2.0 or more.
- **Its null:** 254 windows of known different takes, tight metal doubles included, read
  a median ratio of 1.07 and a maximum of 1.37. Known same takes read 6–14.
- **Stricter where it matters:** it rejects one tightly played double (Cnoc An Tursa
  ElecGtr6) that the envelope test passes.
- **Its limit:** bleed of the same guitar into another take's microphone, at −14 dB or
  louder, would pass.

Every one of the 77 passes the waveform test. Parts that also pass the envelope test (10
of the 60 kept) are recorded as `pairing_test: "envelope+waveform"`, the rest as
`"waveform"`.

### Exclusions: 17 of 77, leaving 60 parts (53 tones)

A part and its double (`DT`) count as one tone, as in sets 1 and 2. Every excluded part
and its reasons are in the JSON's `excluded`.

- **Fewer than 3 passing windows of the waveform test: 10 parts.** A pass resting on one or
  two 20-s windows is too thin.
  - Colour Me Red ElecGtr04 (1 window; its amp track is also *earlier* than its DI);
  - Get Out Of Bed ElecGtr5 and ElecGtr6 (1 each);
  - Learning How To Fly ElecGtr1–3 (2 each);
  - Aureus Necrosis ElecGtr4 (2);
  - Bloodshed ElecGtr3, ElecGtr4 and ElecGtr4DT (1 each).

  The rule is applied whichever test the part passes, so four parts that also pass the
  envelope test are out: Colour Me Red ElecGtr04 and Bloodshed ElecGtr3, 4 and 4DT.
- **Clipped DIs: 4 parts.** The catalogue's line is 10 or more flat-topped runs at full
  scale, and the catalogue flags these as "DI clips":
  - Aureus Necrosis ElecGtr2 (503 runs);
  - Japan Song Gtr5 (239);
  - Wickerman ElecGtr5 (60) and ElecGtr6 (31).

  Omen ElecGtr2 (3 runs) and ElecGtr2DT (1) only touch full scale. They are kept and
  marked `di_touches_full_scale`.
- **Two lag clusters: 2 parts.** Femme (Wall Of Death) ElecGtr1 and ElecGtr2 have only 67%
  and 62% of windows within 0.25 ms of the median. That looks like a blend of two
  microphones, so they have no single lag.
- **No crop: 1 part.** EnDance Gtr6. Its DI also touches full scale.

Kept but marked (`marks` in the JSON), for an analysis to keep or drop by its own
declaration:

- **`effects_or_bleed`:** the catalogue reads a high non-linear share with little
  compression, which suggests effects, bleed or noise rather than gain. These are Big
  Trouble GTR and Southern Fried GTR (Crazy Swedes). Learning How To Fly ElecGtr1–3 carry
  the same flag but are already out.
- **`late_amp_track`:** the amp track is more than 5 ms after the DI, which suggests a far
  microphone, a reamp or latent processing. These are:
  - Wickerman ElecGtr4, 7 and 9 (about 8 ms);
  - Femme ElecGtr3 and 4 (about 12 ms);
  - both Renesans parts (6.3 ms).
- **`di_touches_full_scale`:** Omen ElecGtr2 and 2DT.

## Lags and polarity

- **`lag_samples`** is the waveform test's median lag, at 48 kHz, from the crop record
  (`lag.lag_samples`). It is positive when the amp track is later and is never applied.
- **`judge_lag_samples`** is `lag_samples − 52`, the judge's convention (the plugin's 52
  samples; [di-recovery-plan.md](di-recovery-plan.md)).
- **No render-based check.** Set 2's lags were checked against plugin renders
  (`record_part_lags.py`). That check needs renders, so it was not run here.
- **The onset cross-check** is recorded per part from the crop records (`onset_check`).
  It counts as clear when the runner-up is under 0.9, and as agreeing within 1 ms.
  - It agrees on 41 parts and is unclear on 12.
  - It disagrees on 7: Wickerman ElecGtr3, Burial Of Silence ElecGtr4, Femme ElecGtr3,
    The Forthcoming Turn ElecGtr2–4 and Aureus Necrosis ElecGtr3. The last four are
    held out.

  The declared lag stays the waveform lag. No lag is re-measured on a held-out part before
  the final test.
- **`polarity`** is the amp track's polarity relative to the DI: −1 on 34 of the 60 kept
  parts. Whether an analysis flips it is part of that analysis's declaration.

## Gain classes

- **`gain_class`** is the catalogue's session-level class, from the amp track against its
  DI (clean, crunch or high-gain). It is the class stratified on.
- **`gain_class_crop`** is the same measure on the 10-s crop. It reads high-gain far more
  often, because a 10-s window spans a narrow range of DI levels. Prefer the session class.
- **Crunch against high-gain is not calibrated.** It rests on the level slope alone,
  calibrated on five amp channels fed one test signal. Read it as an ordinal compression
  reading, not a validated class (catalogue `rules.gain_class`).

## The split

The split holds out whole bands, so all of a band's songs are on one side. There are 17
bands with kept parts.

**Eat The Feeder is development only.** Its "Today's The Day" is a set-2 development
session, and set 2's DIs already train the models. Its set-3 song, "Wickerman", therefore
cannot be held out.

**Balanced across gain classes by a seeded draw within strata.**

- **The strata.** Each band is put in the stratum of its most common session-level gain
  class over its kept tones, a double counting once. A tie goes to the cleaner class, the
  scarcer one in set 3; only Turbosauro ties (one clean tone, one high-gain), so it is clean.
  - clean: Diesel13, Dunning Kruger, Silona, Timo And The Timezone, Turbosauro;
  - crunch: Crazy Swedes, Eat The Feeder, Magician's Nephew, Silence Is Near, Szymon
    Skiba, Wall Of Death;
  - high-gain: Death Of A Romantic, Hollow Ground, Rebuild The Evil, Renesans, Scott
    Elliott, V.M.GY.
- **The draw.** Two bands are drawn from each stratum, leaving Eat The Feeder out of the
  draw. That holds out 6 of 17 bands, about a third.

`research/validation_set3.py` draws with one generator, `random.Random(20261007)`, in this
order:

```python
rng.sample(["Diesel13", "Dunning Kruger", "Silona", "Timo And The Timezone", "Turbosauro"], 2)
                                    # clean     -> Dunning Kruger, Silona
rng.sample(["Crazy Swedes", "Magician's Nephew", "Silence Is Near", "Szymon Skiba",
            "Wall Of Death"], 2)    # crunch    -> Crazy Swedes, Silence Is Near
rng.sample(["Death Of A Romantic", "Hollow Ground", "Rebuild The Evil", "Renesans",
            "Scott Elliott", "V.M.GY"], 2)
                                    # high-gain -> Scott Elliott, V.M.GY
```

**Held out: Crazy Swedes, Dunning Kruger, Scott Elliott, Silence Is Near, Silona, V.M.GY.**
The two largest bands, V.M.GY (11 parts) and Scott Elliott (6), both fell to the held-out
side. So the held-out side has 27 of the 60 parts (22 of 53 tones), although it has only a
third of the bands. The draw stands as drawn.

| | parts | tones | clean | crunch | high-gain |
|---|---|---|---|---|---|
| development (11 bands) | 33 | 31 | 5 | 11 | 17 |
| held out (6 bands) | 27 | 22 | 4 | 8 | 15 |

## Folds over the development bands

Set 3 uses four band folds in K3's style: a seeded shuffle of the sorted bands, dealt round
the folds. A part is only ever processed by a network that saw no DI from its band.

**Eat The Feeder keeps its K3 fold (2).** The plan's fold-k network leaves out K3 fold k's
bands from sets 1–2 and set 3's fold-k bands. If Eat The Feeder had a different set-3
fold, that network would train on its set-2 DIs and then process its set-3 parts.

The same generator continues after the held-out draw. It shuffles the ten other sorted
development bands and deals them round folds 0, 1, 3, 2: the pinned band's fold comes
last, so that fold receives fewer drawn bands.

| fold | bands | parts | clean | crunch | high-gain |
|---|---|---|---|---|---|
| 0 | Diesel13, Hollow Ground, Timo And The Timezone | 7 | 3 | 1 | 3 |
| 1 | Renesans, Turbosauro, Wall Of Death | 9 | 2 | 2 | 5 |
| 2 | Death Of A Romantic, Eat The Feeder, Rebuild The Evil | 12 | 0 | 4 | 8 |
| 3 | Magician's Nephew, Szymon Skiba | 5 | 0 | 4 | 1 |

Three sessions have no usable part: Cnoc An Tursa, Storm Of Particles and The Long Wait.
They are development and unfolded, so their DIs may train every fold's network.

The bands, with the kept parts per band:

| band | songs | stratum | side | kept | excluded |
|---|---|---|---|---|---|
| Crazy Swedes | Big Trouble, Flight #4, Southern Fried | crunch | held out | 3 | 0 |
| Death Of A Romantic | The Well | high-gain | fold 2 | 4 | 0 |
| Diesel13 | Colour Me Red | clean | fold 0 | 3 | 1 |
| Dunning Kruger | EnDance (Japan Song has no kept part) | clean | held out | 1 | 2 |
| Eat The Feeder | Wickerman | crunch | fold 2 | 6 | 2 |
| Hollow Ground | Ill Fate | high-gain | fold 0 | 3 | 0 |
| Magician's Nephew | Get Out Of Bed | crunch | fold 3 | 3 | 2 |
| Rebuild The Evil | Burial Of Silence | high-gain | fold 2 | 2 | 0 |
| Renesans | Less Than Nothing, Split Brow (Labor Of Hate has none) | high-gain | fold 1 | 2 | 0 |
| Scott Elliott | Aeternum Vale | high-gain | held out | 6 | 0 |
| Silence Is Near | The Forthcoming Turn | crunch | held out | 3 | 0 |
| Silona | Learning How To Fly | clean | held out | 3 | 3 |
| Szymon Skiba | Let's Dance | crunch | fold 3 | 2 | 0 |
| Timo And The Timezone | Just Don't Talk | clean | fold 0 | 1 | 0 |
| Turbosauro | Magilla | clean | fold 1 | 4 | 0 |
| V.M.GY | Aureus Necrosis, Bloodshed, Omen | high-gain | held out | 11 | 5 |
| Wall Of Death | Femme | crunch | fold 1 | 3 | 2 |

## How the split is used

**Development** material may be used for anything: training, renders, benchmarks, tuning
and listening. Fold k's parts are scored only by a network whose training saw no DI from
their bands (`learn.set3.training_sessions(k)`).

**Held-out** material is read once, at the end, by the Phase 2 test on real recordings.
That test, with its command, what it measures and what each result would mean, must be
declared in a committed file before it runs, and its use is added to `held_out_uses` in
`validation-set3.json`.

Until then, nothing reads a held-out band's audio. This covers:

- **training**, which never uses held-out audio: not its DIs, not renders made from them,
  not their average spectra;
- **choosing**, tuning, lag re-measurement and crop rebuilding;
- **listening**.

This covers every file of every session by a held-out band, including sessions and parts
not kept (Japan Song, the excluded V.M.GY and Silona parts). A held-out band used for
anything else moves to development, and this file says so.

## Sources, licences and what was not obtained

None of the audio is in this repository. The catalogue pins every session archive and file
by SHA-256. The JSON records each crop's DI and reference hashes and the catalogue's own
hash, `46e4ac3d…842f`.

- **Cambridge Music Technology "Mixing Secrets" library:** 21 sessions, 24-bit/44.1 kHz.
  Its terms, from each session's readme: "provided for educational purposes only, and the
  material contained in them should not be used for any commercial purpose without the
  express permission of the copyright holders" ([library](https://cambridge-mt.com/ms/mtk/)).
  Which amp tracks are microphones on an amp and which are processed tracks is not stated.
- **Telefunken "Live From The Lab", seasons 7 and 9:** Crazy Swedes and Renesans, 6
  sessions. Its terms: for home-studio and educational use only, no commercial use, and
  any non-commercial reuse must carry: *All audio files have been engineered and recorded
  by TELEFUNKEN Elektroakustik and are presented for educational and demonstrational
  purposes only.* ([terms](https://www.telefunken-elektroakustik.com/livefromthelab/))
- **ToneTwist AFx (Zenodo, CC BY-NC 4.0):** used only to calibrate the gain classes. It is
  not part of set 3.

**Not obtained.** The catalogue lists 52 heavy-genre sessions linked from
cambridge-mt.com/ms/mtk/ that sit on multitracks.cambridge-mt.com behind a Cloudflare
browser challenge and were not downloaded (JSON `not_obtained`). They include more by
V.M.GY, Daimon B, Serapis, Perpetual Escape and Jack Hutcheson.

Two entries on that list are in hand by other routes, so 50 are absent:

- Eat The Feeder's "Wickerman" came from its direct archive link, and is set 3's
  Wickerman.
- Eat The Feeder's "Today's The Day" is a set-2 session.

The heavy end of what exists is therefore under-sampled, and set 3 is what could be
fetched without a browser.

## Amendments

The declaration above stands as committed in c088b30. The held-out draw, the folds and the
exclusions are unchanged. What follows adds to it or tightens it, after an independent
review, before any match, model, judge or listening score on set 3.

### 2026-10-07 (1): leakage guards that fail closed

`learn/set3.py` gains three guards. Training code goes through them, and each raises
rather than guessing:

- **`fold_for_band(band)`** merges K3's folds (`learn.train.k3_folds`, sets 1–2) with set
  3's development folds.
  - It raises on a held-out band of any set, on an unknown band, and on a band whose two
    folds clash.
  - Guitar-TECHS P1 and set 3's three unfolded development bands (no kept part) are −1:
    every fold may train on them.
  - Eat The Feeder is 2 in both.
- **`is_held_out(x)`** takes a band, a set-3 session key or crop slug, or a path.
  - A path is matched by prefix on the dataset paths: absolute, with `~`, or relative to
    the dataset root. Anything under a held-out session's directory or a held-out part's
    crop directory is held out.
  - It knows sets 1–2 too (`validation-datasets.json`), so every training DI can be
    checked. Set 1 shares one directory between both sides (Guitar-TECHS P3_music); under
    it only the listed files are known.
  - It raises on any name or path it does not know.
- **`training_dis(test_fold)`** returns the DI files a network tested on `test_fold` may
  train on. These are set 2's development DIs and Guitar-TECHS P1's (as `learn.di_pool`
  takes them) plus every DI of set 3's development sessions, kept part or not. It drops:
  - bands in `test_fold`;
  - set-3 DIs with 10 or more flat-topped full-scale runs, by the catalogue's
    whole-session count. Of the development DIs, that drops Wickerman ElecGtr5 and 6.
  - Set 2's catalogue has no clipping count, so set 2's DIs are taken as `learn.di_pool`
    already takes them.

  It checks every file again with `is_held_out`.

The JSON gains fields that `research/validation_set3.py` now writes (schema
`validation-set3-2`). Rebuilt from the same catalogue and crop records, the earlier
content is identical, and these fields are added:

- `sessions[].dis`: every DI path with its clipping count;
- `parts[].level_slope` and `parts[].nonlinear_to_linear_db`: the catalogue's session-level
  gain measures;
- `parts[].crop.record_sha256` and `excluded[].crop_record_sha256`: the SHA-256 of each
  crop's `record.json`. The 60 kept parts' hashes equal those logged when the crops were
  built.

`tests/test_set3.py` rebuilds the JSON from the catalogue and compares it, everything but
`held_out_uses`. It is skipped on a machine without the catalogue.

### 2026-10-07 (2): lags and polarity

- **Held-out lags are never re-measured** for the confirmatory result. It uses
  `judge_lag_samples` as declared.
- **The waveform lag is primary for every part,** development and held out.
- **The onset lag is a declared sensitivity analysis for the 7 parts where it disagrees.**
  The same result is computed once more with those parts' judge lag set to
  `onset_check.onset_lag_samples − 52`:

  | part | side | waveform lag | onset lag |
  |---|---|---|---|
  | Wickerman ElecGtr3 | fold 2 | 35 | 148 |
  | Burial Of Silence ElecGtr4 | fold 2 | 15 | 268 |
  | Femme ElecGtr3 | fold 1 | 573 | 524 |
  | The Forthcoming Turn ElecGtr2 | held out | 74 | −16 |
  | The Forthcoming Turn ElecGtr3 | held out | 50 | −12 |
  | The Forthcoming Turn ElecGtr4 | held out | 65 | −72 |
  | Aureus Necrosis ElecGtr3 | held out | 27 | −28 |

  If pass or fail differs between the two, the result is reported as **not robust**.
  The onset lags are already recorded, so this needs no new measurement.
- **Development lags may be checked against renders later,** as set 2's were
  (`record_part_lags.py`), but only before any held-out result. A correction is recorded
  here as an amendment. No held-out part is checked.
- **Polarity is taken as the catalogue records it** (`polarity`, −1 on 34 of 60). It is
  not chosen per part by results.
  - **The judge ignores polarity.** `analysis/aligned.py` compares magnitude spectra: it
    computes `|rfft|²` mel spectra, frame energies for the DI mask and loudness
    normalisation. `estimate_lag` peaks on the cross-correlation's magnitude.
  - **Verified.** Flipping the recording, the render or the DI leaves `aligned_distance`
    unchanged, and `estimate_lag` gives the same lag
    (`tests/test_set3.py::test_judge_ignores_polarity`, synthetic signals).
  - **Where polarity can still matter:** a DI fed to the plugin. An amp's asymmetric
    clipping makes a render of the inverted DI differ from the inverted render. A method
    that rebuilds a DI from the amp track (the network, `flatref`) therefore uses the
    catalogue's polarity.

### 2026-10-07 (3): disclosure

**The dry run.** The declaring agent ran `research/validation_set3.py` once under an
earlier fold rule, then changed the rule and ran it again. The held-out draw was the same
in both runs.

- **The earlier rule:** `dev = sorted(all 11 development bands); rng.shuffle(dev);
  fold = index % 4`, with Eat The Feeder not pinned.
- **The dry run's folds:**

  | fold | bands | parts | clean | crunch | high-gain |
  |---|---|---|---|---|---|
  | 0 | Death Of A Romantic, Magician's Nephew, Szymon Skiba | 9 | 0 | 4 | 5 |
  | 1 | Diesel13, Hollow Ground, Renesans | 8 | 2 | 1 | 5 |
  | 2 | Timo And The Timezone, Turbosauro, Wall Of Death | 8 | 3 | 2 | 3 |
  | 3 | Eat The Feeder, Rebuild The Evil | 8 | 0 | 4 | 4 |

- **Why it changed.** The dry run put Eat The Feeder in fold 3, but K3 has it in fold 2.
  The fold-3 network, which processes its set-3 parts, would have trained on its set-2
  DIs; the fold-2 network, which processes its set-2 parts, on its set-3 DIs. The agent then printed `k3_folds()` and pinned the band. The new rule is less
  balanced (7/9/12/5 parts against 9/8/8/8); balance was not the reason.
- **What it saw in between:** these counts by fold and gain class, and a per-part listing
  of catalogue fields (gain classes, lags, onset checks, marks). No match, model, judge or
  listening score existed.
- **Where this comes from.** The earlier rule and its folds are recovered from the
  declaring agent's session transcript (the script's printed output). Running the earlier
  rule on the declared strata reproduces them exactly. They are not kept in `_tools/` or
  in git history, since the script was committed only in its final form.

**EnDance Gtr6's missing crop.**

- **The step:** the crop-building step (`_tools/build_crops.py`, calling
  `research/build_validation_crops.build` with rule `di-activity`) failed on it with:

  > `cambridge-endance-gtr6 CROP FAILED reference has no measurable 10-second excerpt`

  The error is logged in `/tmp/set3/crops.log` and `crops2.log`, two runs with the same
  error, and in `/tmp/set3/crops_made.json`.
- **What the error means:** it comes from `_window_by_di`. The 10-s window where the DI
  plays most (ties within 0.02 broken by the amp track's power) had an amp track with no
  measurable loudness: `loudness_lufs` returns None when the meter reads no finite
  loudness, as for digital silence or a signal wholly under its gate.
- **Not re-run:** Dunning Kruger is held out, and rebuilding a crop, even in a dry mode,
  reads its audio, which this declaration forbids.
- **Its DI:** it also touches full scale (9 runs, under the 10-run line).

### 2026-10-07 (4): gain classes and gates

- **Per-class results are descriptive only.** This covers the part's `gain_class` and the
  band stratum. No gate or claim is made per class.
- **Also reported, also descriptive:**
  - **the continuous level slope:** each part's result against `level_slope` (−0.24 to
    0.92), shown with Spearman's ρ over parts and over band medians;
  - **clean against driven:** the catalogue's `clean_vs_driven`, firm driven against the
    rest, with the three labels shown. Firm clean parts are too few to summarise alone:
    2 in development and 1 held out, against 21 and 20 driven and 10 and 6 uncertain.
- **Gates count parts weighted by band.** Each band's parts weigh 1/n, n being that
  band's parts in the material scored, so every band counts once.
  - So "closer than template+R and the constant on more than half the parts" means more
    than half the band-weighted total.
  - The band-median and sign-flip gates are per band already.
  - Without the weights, V.M.GY's 11 held-out parts would be 41% of the held-out count.
  - This applies to Phase 2 on development parts and to the held-out confirmation.
