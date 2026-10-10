# Predict the sound, not the knobs: plan for the first test (development)

Declared 2026-10-10, before any data for it is generated. It is reviewed independently
before it runs.

## The idea

Sound to knobs is ill-posed: many settings sound alike, and a record mixes the rig with
the player, guitar, mic, room and mix. Knobs to sound is exact: the plugin computes it.
So a model predicts a **sound description** instead of knobs, and presets are chosen by
comparing it with descriptions the plugin computes.

1. **A preset's description `T(p)`:** what an *average guitar* sounds like through preset
   `p`. It is computed exactly, by rendering a fixed set of average-guitar DIs through `p`.
2. **The translator** maps the description of a *recording* (a specific player and guitar
   through some rig) to a predicted `T` for that rig. It is trained only on plugin
   renders.
3. **For a song:** describe its guitar, translate it, and pick the menu preset whose `T(p)`
   is nearest. That is one model pass and a lookup, with no per-song rendering and no DI
   rebuild.

This first test asks the riskiest question: can a translator trained on plugin renders
read **real recordings**? The large-scale model of every setting comes only after it
passes.

## The sound description `D(x)` (fixed here)

On mono audio, level-normalised, using the frames where it plays (within 40 dB of the
loudest frame):
- **Tone:** the long-term log-mel spectrum, 64 bands from 50 Hz to 16 kHz (2,048-sample
  frames, hop 512), mean-removed.
- **Texture:** each band's frame-to-frame standard deviation (64).
- **Dynamics:** crest factor, and the spread of frame RMS between the 90th and 10th
  percentiles (2).

That is 130 numbers, each standardised by the training set's mean and spread.

## The average guitar, and `T(p)`

- **The average guitar** `G`: 4 fixed DI windows from 4 different sets 1–2 development
  bands, chosen by the rule below. Each is re-equalised to the pinned K3 fold-2 average
  balance and set to −22.9 LUFS, as the measure does.
  - **The rule:** in the pool's band order, the first window, by sorted path, of the first
    4 bands that are not Guitar-TECHS.
- **`T(p)`:** the mean of `D` over the renders of `G` through `p`, for every menu preset
  of the three amps (111 presets, 444 renders). This uses the menu presets with the
  effects off, as in every measurement.

## Training data (development only)

- **DI windows** come from the existing development pools (`poc/di-windows.json`, 3,509
  windows from sets 1–2; `direc/set3-di-windows.json`, 1,484 from set 3). None is held
  out, as checked with `set3.is_held_out`.
- **Up to 12 windows per band, 28 bands:** about 330 windows, chosen with seed 20261011.
- **Each window is used as its own guitar** (its own balance), at −22.9 LUFS plus a
  uniform ±6 dB, and rendered through all 111 menu presets: about 37,000 renders.
  - Only the descriptors are stored, not the audio.
  - Each render also gets one augmented copy, with a random ±3 dB tilt, a ±4 dB bell at
    200 Hz–5 kHz, and noise 50–70 dB below, to stand in for mic and room.
- **The pair:** input `X = D(render)`, target `Y = T(p)`.

## Models (declared)

- **No-learning baseline:** `Ŷ = X`. The recording's own description is compared
  directly with `T(p)`. This is close to what failed before; the translator must beat it.
- **Primary translator:** ridge regression from `X` to `Y`, with the penalty chosen by
  leave-band-out cross-validation inside the training bands.
- **Secondary translator:** a small MLP (130 → 256 → 256 → 130, early stopping on
  training-band validation). It is reported, and doesn't gate.

## Evaluation (real recordings, leave-band-out)

**Test parts** (in scope: clean and crunch, each with fixed-level measure distances for
every menu preset on both halves):
- set 3's development clean and crunch parts (`rescore/distances.json`);
- sets 1–2's development stem parts (`songs-check/distances.json`).

**For each test part:**
- **Translator:** each test part's band is excluded from training, on both the DI side
  and the window side. A K-fold over bands, with K equal to the number of test bands, is
  acceptable if the folds exclude the part's band.
- **Input:** the real amp track's description on one half (1.0–5.5 s, or 5.5–10 s).
- **Pick:** the nearest `T(p)` within each amp's menu.
- **Score:** the fixed-level measure on the other half. Both directions are averaged per
  part-amp, as in the confirmation.

**Comparisons** (band-clustered 90% intervals):
1. translator against the no-learning baseline;
2. translator against the product's starting presets (clean or crunch baseline). Those
   were chosen on these parts, which biases the comparison against the translator;
3. translator against the current rebuilt-DI chooser's picks (stored);
4. the oracle, for headroom.

The separated stem as input is reported for the sets 1–2 parts, not gated.

## Decision rule (declared)

**Phase B (the every-setting knobs-to-sound model, beyond the menu) is worth starting if
both hold:**
- the primary translator beats the no-learning baseline, with its 90% interval below 0;
- its mean against the product's starting presets is below 0.

Otherwise the approach stops at this stage, with the result reported. Phase B gets its
own plan and review before it runs.

## Cost and safety

- **Rendering:** about 37,500 renders in 6 reused processes, about 3 hours. The licence
  service is checked first (about 170k ports now).
- **Storage:** descriptors only, a few MB.
- **CPU training:** minutes.
- **No held-out data is touched.**
