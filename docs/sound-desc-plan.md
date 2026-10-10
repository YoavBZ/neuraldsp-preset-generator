# Predict the sound, not the knobs: plan v2 for the first test (development)

Declared 2026-10-10.
- **v1** (commit ec8ca48) was reviewed (`tmp/sound-desc-plan-review.md`, local), and its
  required changes are folded in here.
- **The reviewer's ceiling scripts** read the test parts' stored audio. That use is
  recorded; it chose nothing.
- **Nothing has been rendered for this plan.**

## The idea (unchanged)

Sound to knobs is ill-posed: sound-alike settings, and a record that mixes the rig with
the player, guitar, mic, room and mix. Knobs to sound is exact, because the plugin
computes it. So a model predicts a **sound description**, and presets are chosen by
comparing it with descriptions computed through the plugin.

## What v1 got wrong, and the fix

**The measure** plays the take's DI, re-equalised to an average balance and set to
exactly −22.9 LUFS, into each preset. It asks which preset then sounds like the
**record**. So the best preset reproduces the record's coloration: the guitar's
brightness, the drive and the mic.

**v1's training pairs taught the translator to strip those out:** each guitar at its own
balance, ±6 dB of level and EQ augmentation, all with the same label.

**v2 trains on DIs treated the measure's way** (average balance, −22.9 LUFS exactly).
The translator learns to remove only what the specific notes and playing contribute.
Augmentation is noise only, 50–70 dB down. The v1 design (own balance, ±6 dB) can run as
a secondary arm that doesn't gate.

## Test parts (pinned)

The development clean and crunch parts with fixed-level measure distances on both
halves for every menu preset: **35 parts in 15 bands** (Honey's measure is refused).
- clean: 22 parts in 10 bands;
- crunch: 13 parts in 6 bands.

The slug list is committed in `docs/sound-desc-test-parts.json` before stage 0 runs.
Band exclusion uses the **merged band name** across both window pools; Eat The Feeder is
in both. It is asserted in code.

## Stage 0: can any sound description track the judge? (no renders; runs first)

**The same-notes ceiling:**
- For each test part and half, describe the real amp track, and describe the stored
  measure render of every menu preset (the same take's DI, the measure's way).
- Pick the preset whose description is nearest. Score it with the measure on the other
  half.
- This is what a **perfect** translator could reach with that description. The v1
  descriptor's ceiling was about −0.028 against the shipped presets, and about 0 on clean.

**Candidate descriptions, declared here, each standardised by the stored renders'
spread:**
1. **`D130`,** v1's: the long-term log-mel tone (64), per-band frame standard deviation
   (64), crest factor and RMS spread.
2. **`Dlevel`,** level-conditioned: frames split into three loudness terciles, the
   mean-removed log-mel per tercile (192). This captures how tone changes with how hard
   the player digs in: drive and compression.
3. **`Dpct`,** per-band 10th, 50th and 90th percentiles of the frame log-mel,
   mean-removed (192).
4. **`Dall`:** 2 and 3 together, plus the dynamics pair (386).

**The pick metric:** Euclidean distance on standardised dimensions, within each amp's
menu. The activity gate is frames within 40 dB of the loudest; 25 and 30 dB are reported
as a sensitivity check.

**Selection without forking the test:**
- The test bands are split by sorted name, alternating, into design bands (8) and verify
  bands (7).
- The description with the best design-band ceiling, against the leave-band-out product
  baseline, is chosen.
- **It passes if,** on the verify bands, its ceiling against the leave-band-out product
  baseline has a mean of −0.04 or lower and more part-amp wins than losses.
- **If none passes:** stop. Report that descriptor matching doesn't track the judge well
  enough for a translator to help, and propose a learned metric instead (a declared
  alternative, not run tonight).

**Also reported for each description:**
- the no-learning pick: the nearest `T(p)` (below) to the real amp track's description;
- a centroid baseline: the nearest average of the stored measure renders of other bands'
  parts through `p`, which is what failed before.

## The average guitar `G` and `T(p)`

- **`G`:** 4 DI windows from non-test bands: Ale Lak, John Morgan Kimock, Bernard Purdie
  Tribute All-Stars and Cnoc An Tursa. Each is the first window by sorted path and start,
  re-equalised to the pinned average and at −22.9 LUFS.
- **`T(p)`:** the mean description over `G`'s renders through `p`: 111 presets, 444
  renders.

## Stage 1 (only if stage 0 passes): the translator

**Data:**
- **Windows:** up to 12 per band from both development pools (seed 20261011), dropping
  windows below −40 LUFS. All test bands are excluded at training time, per fold.
- **Each window,** re-equalised to the pinned average and at −22.9 LUFS, is rendered
  through all 111 menu presets.
- **The descriptor** is the chosen one, on 4.5-s segments to match the test halves (two
  per render). A noise-only augmented copy is added.
- **Audio is kept** for 5% of the renders, for review.

**Models:**
- **Primary: ridge,** from the render description to `T(p)`.
  - Penalties: 0.1, 1, 10, 100, 1,000.
  - Chosen by mean squared error under 5-fold leave-band-out cross-validation inside the
    training bands.
  - Standardisation is fitted inside each fold.
- **Secondary:** an MLP (two hidden layers of 256), and a bias-only model. Both are
  reported, and don't gate.

**Positive control:** the translator on the test parts' own stored measure renders, where
its picks should approach the same-notes ceiling.

**Off-manifold check:** the distance of each real-recording description from its nearest
training description, against renders' own distances. Also reported: a pick histogram per
amp.

**Gates (clean and crunch pooled, band-clustered 90% intervals, choosing on one half and
scoring the other):**
1. **The translator against the better of no-learning and centroid.**
   - **Helps:** the interval lies below 0, and the share of the gap to the same-notes
     ceiling that it closes is reported.
   - **Futile:** the lower bound is above −0.02.
   - **Inconclusive:** anything else.
2. **The translator against the leave-band-out product baseline**, reported pooled and
   for crunch, the stratum where a fixed preset left room.
   - **Helps:** the interval lies below 0.
   - **Futile:** the lower bound is above −0.03.
   - **Inconclusive:** anything else.

**Phase B** (the every-setting knobs-to-sound model, beyond the menu) gets its own plan
if gate 1 helps and gate 2 is not futile.

**Also reported:**
- each stratum alone;
- the stored rebuilt-DI chooser;
- the oracle;
- drive bias;
- the judge's tonal and temporal parts.

## Cost and safety

- **Stage 0:** CPU only, plus the 444 renders for `T(p)`.
- **Stage 1:** about 330 windows × 111, about 37,000 renders in 6 reused processes,
  about 2.5 hours, with the licence service checked first. It stores descriptors only,
  plus 5% of the audio.
- **No held-out data.**
- **The reviewer re-checks this plan before stage 0 runs.**

## Amendments after the v2 review (2026-10-10, before stage 0 runs)

Review: `tmp/sound-desc-plan-v2-review.md`, local. Verdict: approve with these required
changes, all applied here. **They replace the matching v2 text above.**

1. **Selection and the bar (replaces the design/verify split).** The split was lopsided:
   crunch was almost all in the verify bands, which pre-passed the bar, and the choice
   rested on clean parts, where every ceiling is near 0.
   - **Leave-one-band-out over all 15 test bands:** for each band, the description with
     the best ceiling mean on the other 14 bands (standardised on those bands' renders
     only) is applied to that band's parts.
   - **Crunch decides:** the result on crunch parts must have a mean of −0.04 or lower,
     with more wins than losses. Clean is reported separately. If clean misses and crunch
     passes, any product claim is crunch-only.
   - **If the chosen procedure fails on crunch, stop.** Other descriptions cannot rescue
     it.
   - **Note for the ledger:** the −0.04 bar was set after the v1 per-stratum ceiling
     figures were seen.
   - The description carried into stage 1 is the one with the best ceiling over all 15
     bands.
2. **Stage-0 definitions.**
   - **Means** are part-weighted over part-amp cells, each averaged over both scoring
     directions.
   - **Wins and losses** count cells below or above 0; |x| ≤ 1e-9 is a tie.
   - **Standardisation** is fitted on the selecting bands' renders only.
   - **The centroid baseline** is the mean description over every other band's test
     parts (any class) of the stored render through `p`.
3. **Gate 2's baseline:** per amp and gain class, the factory preset with the lowest
   median (over both halves) over other bands' parts of the same class. **Crunch decides
   gate 2** and Phase B's "not futile" condition; the pooled result is reported. In gate
   1, "the better of" no-learning and centroid means the one with the better pooled mean.
4. **Folds:** 15 folds, each holding out one test band and training on the windows of the
   other bands. Each 6-s window gives two overlapping 4.5-s segments (0–4.5 s and
   1.5–6.0 s). `T(p)` also uses 4.5-s segments.
5. **The positive control's minimum:** on the test parts' own stored renders, the
   translator must be at least as good as the centroid baseline. If it isn't, a "futile"
   gate-1 result is reported as inconclusive.
6. **Recommended, adopted:** `G` takes each band's first window with activity of at least
   0.9. Also reported: null inputs (raw DI, noise) in the off-manifold check, and the
   cross-amp pick.

## Stage 0 result and a gate amendment (2026-10-11, before any stage-1 result)

**Stage 0 passes**, independently reproduced (`tmp/sound-desc-stage0-review.md`, local).
- **Crunch:** the leave-one-band-out ceiling is −0.129 (−0.177 to −0.080), 34 / 1 / 4.
  D130 was chosen in all 15 folds.
- **Clean:** +0.002, no headroom.
- **No learning, on crunch:** −0.048. Centroid: −0.050.
- **Predictable:** the reviewer notes the pass was predictable (the bar was set after
  the v1 figures were seen), so stage 1 is the real test.

**Amendment to gate 1:** it is decided on **crunch**, like gate 2; the pooled result is
reported.
- **Why:** clean parts, 66 of 105 cells, have no headroom even for a perfect translator.
  A pooled gate would mostly measure noise.
- **Timing:** this is declared while stage-1 training data is still rendering, before any
  translator has been fitted or scored.

**"The better of":** no-learning or centroid, whichever has the better crunch mean.
`learn/sound_desc_eval.py` is updated to match.
