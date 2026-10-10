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
