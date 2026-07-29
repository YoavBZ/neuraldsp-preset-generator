# Tone references — Morgan Amps Suite

A growing crib sheet for mapping real-world guitar tones to Morgan parameters.
Add an entry whenever you research a tone — future runs benefit.

## The three amps

### PR12 (`pr12Amp`, `selectedAmp = "1"`)
- Real amp: **Morgan PR12** — Princeton-flavored 12-watt class A.
- Sweet spot: **clean** to **edge-of-breakup**. Beautiful sparkly cleans,
  light grit when pushed.
- Knobs: `pr12Volume`, `pr12Treble`, `pr12Bass`, `pr12Reverb`, `pr12Dwell`.
- Built-in spring reverb (`pr12Reverb` mix + `pr12Dwell` decay).
- Good fit for: country, blues cleans, soft rock, bedroom-volume tones.

### AC20 (`ac20Amp`, `selectedAmp = "0"`)
- Real amp: **Morgan AC20** — Vox AC15/AC30-flavored top-boost chime with
  bite.
- Sweet spot: **chimey clean** to **classic British crunch**.
- Knobs: `ac20Bright`, `ac20BassTreble`, `ac20Volume` (master), `ac20Cut`
  (treble cut, lower = darker), `ac20Power` (output mode).
- `ac20BassTreble = true` engages the cathode-follower tonestack — fuller
  mids and a more "AC30"-like response.
- Good fit for: jangle pop, British invasion, U2-ish edge tones, indie
  rock.

### SW50R (`sw50rAmp`, `selectedAmp = "2"`)
- Real amp: **Morgan SW50R** — Vox-style chime with master volume and
  more headroom; closer to AC30 territory but cleaner.
- Sweet spot: **loud cleans** through **classic rock break-up**.
- Knobs: `sw50rBright`, `sw50rTreble`, `sw50rMid`, `sw50rBass`,
  `sw50rTrebleBoost`, `sw50rLevel`, `sw50rVolume`, `sw50rInputMode`,
  `sw50rReverb`.
- `sw50rTrebleBoost = true` adds front-end gain stage (Rangemaster-ish);
  good for solo boost.
- `sw50rInputMode = true` toggles the bright/normal channel.
- Good fit for: AC/DC-style cleans, Brian May Red Special-ish lead,
  Queen rhythm, classic rock leads.

## Effects-section quick reference

The signal-chain modules visible in the schema (typical order):
- `compressor` — front-of-chain dynamics
- `drive1`, `drive2` — overdrive/distortion pedals
- `pedalParameters` — toggles for the pedal section
- `eqParameters` (with `pr12EQ`, `sw50rEQ`, `ac20EQ`) — per-amp post-EQ
- `cabParameters` — cab/mic selection
- `tremolo`, `delay`, `reverb` — time-based FX

Morgan Amps Suite has **no chorus, flanger, phaser or pitch effects**. The
modules listed above are the complete set — anything else will be rejected by
`apply_spec.py`, because the writer can only mutate parameters the template
already contains. The authoritative list is `packs/morgan/manifest.json`.

Values below are in the project convention: **knobs = percent of rotation
(0–100)**, metered controls in their native unit (Hz / ms / s / dB). See
`reference/preset-spec.md` for the value convention, and each parameter's
`kind` in `packs/morgan/manifest.json`.

When the user says...

- **"more reverb"** → raise `reverb/reverbMix` (~20–35% typical) and
  optionally `reverb/reverbDecay` (seconds). For amp-spring vibe, bump
  `<amp>Reverb` (knob %) instead.
- **"more delay"** → set `delay/delayActive=true`, raise `delay/delayMix`
  (~20–40%), set `delay/delayTime` (ms) or `delay/delaySync` +
  `delay/delaySyncNote`.
- **"tighter low end"** → drop `<amp>Bass` a few %, raise
  `reverb/reverbLowCut` and `delay/delayLowCut` (Hz).
- **"more presence/cut"** → raise `<amp>Treble` (%), push `pr12EQ` high
  bands (Band7–9, dB), or enable `sw50rTrebleBoost`.
- **"warmer"** → drop treble %, raise mids %, lower `reverb/reverbHighCut`
  and `delay/delayHighCut` (Hz).
- **"more break-up"** → raise the active amp's `Volume` knob (%); or
  enable a drive pedal in `drive1`.
- **"cleaner"** → lower amp `Volume` %, nudge `parameters/inputGain` (dB)
  only slightly, ensure no drive pedals active.

## Mapped tones (add entries here as you go)

### Example shape
```
- "Wish You Were Here" intro (Gilmour):
  - amp: SW50R (clean, slight edge) → selectedAmp: 2
  - sw50rVolume: 45%   (clean headroom)
  - sw50rTreble: 60%,  sw50rMid: 55%,  sw50rBass: 50%
  - delay: active, mix 30%, time ~480 ms, feedback 30%
  - reverb: active, mix 25%, decay 1.8 s, hall-ish
  - Source: <PG rig rundown URL>
```

_(Empty for now — populate as you generate presets.)_
