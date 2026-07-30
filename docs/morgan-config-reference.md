<!--
========================================================================
VERIFICATION STATUS — read before trusting this document
========================================================================
Verified 2026-05-29 against the 3 real Morgan presets in samples/ and
the parser-derived parameter catalog (132 params). This file is a MUSICAL
CONTROL REFERENCE, not the binary file format.

RECONCILED as of the pack refactor. This document is now a SOURCE, not a
reference the tools read:
  - Section 21's validation ranges -> packs/morgan/manifest.json (see each
    parameter's `range_source`).
  - Section 15's nine EQ band centres -> manifest `centre_hz`, so band advice
    can name frequencies instead of band numbers.
  - Sections 6-19's templates -> packs/morgan/recipes.json, converted to binary
    key names and the project's percent scale. tests/test_recipes.py proves
    every key exists and every value survives translation, so the 0-10 scale
    and the renames cannot silently leak through.
  - Section 20's intent table and 20.2/20.3 guidance -> packs/morgan/tone.md.
  - Fields that could NOT be translated are listed with reasons in
    recipes.json under `not_translated`. Read that before assuming a template
    here was absorbed whole.

Prefer the pack files. This document is kept for provenance and for the prose
reasoning in sections 20 and 27.

ACCURATE (use as guidance):
  - PR12 amp controls map 1:1 (volume/treble/bass/reverb/dwell).
  - OD1/OD2, compressor, tremolo, delay, reverb control sets are correct
    in spirit; tone-shaping advice (Sections 20, 27) is solid.

CORRECTED BY RESEARCH (2026-07-30), and the doc was right where this repo
was wrong:
  - SW50R is based on the Dumble Small Special, so this doc's
    "Dumble-style singing lead" is correct. Earlier notes in this repo
    called it a Vox-style chime amp, which sent lead requests to the wrong
    amp.
  - AC20 is built on the AC30 NORMAL channel, voiced darker than a Vox --
    not top-boost.
  - PR12's Dwell is a reverb-decay control Morgan added to the Princeton
    circuit so a high reverb mix does not wash out.
  - `cut` higher = darker is correct (it is the Vox power-amp Cut).

MUST TRANSLATE before writing to the binary:
  - SCALE: this doc's 0–10 knob scale is NOT used by the project. The
    plugin knobs have no numbers; the project convention is PERCENT of
    rotation (0–100), stored as 0.0–1.0. Reinterpret any 0–10 value here
    as x*10 percent (doc 3.6 -> 36% -> stored "0.36"). Metered controls
    (dB/Hz/ms/s/BPM/semitones) use native units. The authoritative
    kind+unit for every parameter is in packs/morgan/manifest.json, and
    format/translate.py performs the human->binary mapping.
  - NAMES differ: doc hpfHz/lpfHz -> binary delayLowCut/delayHighCut;
    doc comp -> compressorCompression; od1/od2 -> drive1/drive2; etc.

KNOWN ERRORS / CONFLICTS in this doc vs the binary:
  - gateThreshold: doc says 0–10 knob; binary stores dB (~ -80..-70).
  - AC20: doc's `powerLevel` and `standby` do NOT exist in the binary
    (binary: ac20Power[int], ac20Cut, ac20Volume, ac20Bright,
    ac20BassTreble). Doc `bassCut` is probably `ac20BassTreble`.
  - SW50R: doc says `bassEmphasis`; binary has `sw50rTrebleBoost`
    (bass vs treble — a real conflict). Doc power/standby absent.
  - CAB: doc's slots[]/micId model does NOT match the binary, which uses
    dual left/right cabs. Mic selection = leftMicType/rightMicType integer
    index into the 10-mic catalog (manifest `enums.internalMic`). Custom IR =
    *ChosenIRFilePath string; "no custom IR" is that field set to an empty
    string (use apply_spec.py --strip-irs for portable factory-mic presets).

CONFIRMED (user-verified 2026-05-29):
  - selectedAmp integer -> amp:  "0" = AC20,  "1" = PR12,  "2" = SW50R.
    (Verified by loading presets with each value in the plugin. Those
     presets are not part of this repo.)

Authoritative source for stored keys/scales: packs/morgan/manifest.json.
========================================================================
-->

# Morgan Amps Suite Configuration Reference

Developer-oriented configuration guide for generating presets for the Neural DSP Morgan Amps Suite plugin.

This document normalizes the plugin controls into a preset-generator-friendly model. It uses practical UI values rather than undocumented internal plugin serialization values. Most amp and pedal knobs are represented as `0.0–10.0`, EQ bands are represented in dB, delay/reverb filter controls use Hz, delay/reverb time controls use ms/seconds or synchronized note values, and switches are represented as booleans or explicit enums.

> Important: this is a control/value reference for generating human-readable preset definitions or intermediate preset objects. It is not a reverse-engineered Neural DSP preset file format specification.

---

## 1. Signal Chain

The practical signal chain is:

```text
GLOBAL INPUT
  -> PRE FX: Compressor -> OD1 -> OD2 -> Tremolo
  -> AMP: AC20 | PR12 | SW50R
  -> CAB / IR
  -> GRAPHIC EQ
  -> POST FX: Delay -> Reverb
  -> GLOBAL OUTPUT
```

Recommended generator order:

1. Start from a full neutral/default preset object.
2. Select the amp model based on the requested tone.
3. Apply guitar-role intent: clean rhythm, edge-of-breakup, crunch rhythm, lead, ambient, etc.
4. Apply song/artist flavor.
5. Apply guitar-specific adjustments, especially for a Gibson Les Paul.
6. Level-match output last.

---

## 2. Canonical Preset Object

Use this as the normalized intermediate schema for your generator.

```ts
interface MorganPreset {
  metadata: PresetMetadata;
  global: GlobalConfig;
  preFx: PreFxConfig;
  amp: AmpConfig;
  cab: CabConfig;
  eq: EqConfig;
  postFx: PostFxConfig;
  guitarNotes?: GuitarNotes;
}
```

### 2.1 Metadata

```ts
interface PresetMetadata {
  presetName: string;
  song?: string;
  artist?: string;
  part?: 'intro' | 'verse' | 'chorus' | 'solo' | 'outro' | 'rhythm' | 'lead' | 'clean' | 'general';
  style?: string;
  targetGuitar?: string;
  notes?: string;
}
```

Example:

```json
{
  "presetName": "Hotel California - Clean Rhythm Base",
  "song": "Hotel California",
  "artist": "Eagles",
  "part": "rhythm",
  "style": "classic-rock clean rhythm",
  "targetGuitar": "Gibson Les Paul into Focusrite Scarlett Solo"
}
```

---

## 3. Value Conventions

### 3.1 Knobs

Most plugin knobs should be represented as decimal values:

```ts
type Knob = number; // practical UI range: 0.0 to 10.0
```

Recommended generator precision:

```text
Use one decimal place for knob values unless a more exact value is intentionally needed.
Example: 4.8, 5.0, 6.2
```

### 3.2 dB Values

```ts
type Db = number;
```

Examples:

```text
INPUT 0.0 dB
OUTPUT -3.0 dB
EQ 2 kHz +1.5 dB
MIC LEVEL -4.0 dB
```

### 3.3 Switches

Use booleans in machine-readable objects and `ON/OFF` in display output.

```ts
type Switch = boolean;
```

Display mapping:

```text
true  -> ON
false -> OFF
```

### 3.4 Note Values

Use strings for synchronized note values.

```ts
type NoteValue =
  | '1/64T' | '1/64' | '1/64D'
  | '1/32T' | '1/32' | '1/32D'
  | '1/16T' | '1/16' | '1/16D'
  | '1/8T'  | '1/8'  | '1/8D'
  | '1/4T'  | '1/4'  | '1/4D'
  | '1/2T'  | '1/2'  | '1/2D'
  | '1/1T'  | '1/1'  | '1/1D';
```

Not every module supports every value. Tremolo supports a smaller synchronized range than delay.

---

## 4. Global Configuration

Global controls affect the full rig before and after the amp chain.

```ts
interface GlobalConfig {
  inputDb: Db;              // usually 0.0 dB
  gateEnabled: boolean;
  gateThreshold?: Knob;     // practical 0.0 to 10.0 when enabled
  transposeSemitones: number; // -12 to +12; 0 = bypass/no transposition
  inputMode: 'MONO' | 'STEREO';
  doublerEnabled: boolean;
  doublerSpreadMs?: number; // 3 to 20 ms when enabled
  outputDb: Db;             // usually -4.0 to 0.0 dB after level matching
}
```

### Default for Gibson Les Paul + Focusrite Scarlett Solo

```yaml
global:
  inputDb: 0.0
  gateEnabled: false
  gateThreshold: 2.0
  transposeSemitones: 0
  inputMode: MONO
  doublerEnabled: false
  doublerSpreadMs: 8
  outputDb: -3.0
```

### Generator Rules

- Use `inputMode: MONO` for a single guitar into a Scarlett Solo.
- Keep `transposeSemitones: 0` unless the user requests a key change.
- Keep `doublerEnabled: false` for realistic practice tones.
- Use doubler only for a wider recorded/stereo feel.
- Use gate only when drive/noise requires it.
- Level-match with `outputDb`; do not use output as a tone-shaping control.

---

## 5. Pre FX Configuration

Pre-FX chain:

```text
Compressor -> OD1 -> OD2 -> Tremolo
```

```ts
interface PreFxConfig {
  compressor: CompressorConfig;
  od1: Overdrive1Config;
  od2: Overdrive2Config;
  tremolo: TremoloConfig;
}
```

---

## 6. Compressor

Use the compressor for sustain, pick control, and tighter clean parts.

```ts
interface CompressorConfig {
  enabled: boolean;
  comp: Knob;                    // 0.0 to 10.0
  releaseMode: 'FAST' | 'SLOW';
  level: Knob;                   // 0.0 to 10.0
  mix: Knob;                     // 0.0 to 10.0
}
```

### Common Compressor Templates

#### Subtle Clean Sustain

```yaml
compressor:
  enabled: true
  comp: 2.5
  releaseMode: SLOW
  level: 5.0
  mix: 4.0
```

#### Country / Funk / Tight Clean

```yaml
compressor:
  enabled: true
  comp: 5.5
  releaseMode: FAST
  level: 5.2
  mix: 6.5
```

#### Lead Smoothing

```yaml
compressor:
  enabled: true
  comp: 2.2
  releaseMode: SLOW
  level: 5.0
  mix: 3.5
```

### Generator Rules

- Clean rhythm: `comp 2.0–3.5`, `releaseMode SLOW`, `mix 3.5–4.5`.
- Funk/country: `comp 5.0–6.0`, `releaseMode FAST`, `mix 5.5–7.0`.
- Lead: subtle compression only; avoid flattening dynamics.
- High-gain/crunch rhythm: compressor often off unless the part needs tight attack.

---

## 7. OD1

OD1 is the simpler overdrive and is useful as a solo boost, edge-of-breakup push, and classic-rock crunch enhancer.

```ts
interface Overdrive1Config {
  enabled: boolean;
  drive: Knob; // 0.0 to 10.0
  level: Knob; // 0.0 to 10.0
  tone: Knob;  // 0.0 to 10.0
}
```

### Common OD1 Templates

#### Solo Boost into Clean / Edge Amp

```yaml
od1:
  enabled: true
  drive: 2.0
  level: 6.5
  tone: 5.0
```

#### Classic-Rock Crunch Push

```yaml
od1:
  enabled: true
  drive: 4.0
  level: 6.0
  tone: 5.5
```

#### Eagles / Joe Walsh-Style Singing Lead Push

```yaml
od1:
  enabled: true
  drive: 2.8
  level: 6.3
  tone: 5.2
```

### Generator Rules

- Prefer OD1 for vintage classic-rock lead and crunch.
- For lead sustain without too much fizz, keep `drive` around `2.0–3.2` and raise `level` around `6.0–6.8`.
- For rhythm crunch, raise `drive` to `3.5–4.5` but avoid excessive level boosts.
- For Les Paul bridge pickup, avoid too much `tone` above `6.0` unless the preset is too dark.

---

## 8. OD2

OD2 is thicker and more flexible than OD1 because it includes Bass and Treble controls.

```ts
interface Overdrive2Config {
  enabled: boolean;
  gain: Knob;   // 0.0 to 10.0
  level: Knob;  // 0.0 to 10.0
  bass: Knob;   // 0.0 to 10.0
  treble: Knob; // 0.0 to 10.0
}
```

### Common OD2 Templates

#### Thicker Blues Lead

```yaml
od2:
  enabled: true
  gain: 3.5
  level: 5.8
  bass: 5.5
  treble: 4.8
```

#### Heavier Classic-Rock Lead

```yaml
od2:
  enabled: true
  gain: 5.2
  level: 5.5
  bass: 5.0
  treble: 5.8
```

### Generator Rules

- Prefer OD2 when the requested tone needs more thickness than OD1.
- Avoid stacking OD1 and OD2 by default. Stack only for intentionally saturated lead presets.
- For Les Paul neck pickup, reduce `bass` slightly if the tone gets muddy.
- For bridge pickup lead, keep `treble` around `4.8–5.8` and shape brightness later with EQ/LPF.

---

## 9. Tremolo

Use tremolo for pulsing vintage clean tones or song-specific rhythmic movement.

```ts
interface TremoloConfig {
  enabled: boolean;
  syncMode: 'FREE' | 'NOTE';
  rateHz?: number;       // 0.05 to 5.0 Hz when syncMode is FREE
  rateNote?: NoteValue;  // typical tremolo synced range: 1/64T to 1/4
  depth: Knob;           // 0.0 to 10.0
  level: Knob;           // 0.0 to 10.0
}
```

### Common Tremolo Templates

#### Subtle Amp-Like Pulse

```yaml
tremolo:
  enabled: true
  syncMode: FREE
  rateHz: 2.1
  depth: 2.5
  level: 5.0
```

#### Song-Tempo Tremolo

```yaml
tremolo:
  enabled: true
  syncMode: NOTE
  rateNote: 1/8
  depth: 5.0
  level: 5.0
```

### Generator Rules

- Keep tremolo off unless the song/part clearly needs it.
- Use `FREE` for vintage feel.
- Use `NOTE` for tempo-locked rhythmic parts.
- Keep `level` at `5.0` unless tremolo changes perceived loudness too much.

---

## 10. Amp Configuration

The suite includes three amp models:

```ts
type AmpModel = 'AC20' | 'PR12' | 'SW50R';

type AmpConfig = Ac20AmpConfig | Pr12AmpConfig | Sw50rAmpConfig;
```

### Amp Selection Heuristics

| Amp | Best For | General Tone Role |
|---|---|---|
| `AC20` | Vox-like jangle, British crunch, chime, classic-rock rhythm | Bright, immediate, mid-forward |
| `PR12` | Fender-style clean, clean rhythm, blues clean, Eagles rhythm | Clear, sparkly, familiar clean platform |
| `SW50R` | Dumble-style clean lead, smooth lead, warm high-headroom platform | Smooth, rounded, singing sustain |

---

## 11. AC20 Amp

```ts
interface Ac20AmpConfig {
  model: 'AC20';
  power: boolean;
  standby: boolean;
  powerLevel: Knob; // 0.0 to 10.0
  cut: Knob;        // 0.0 to 10.0; higher = darker / more high cut
  volume: Knob;     // 0.0 to 10.0
  bright: boolean;
  bassCut: boolean;
}
```

### AC20 Templates

#### Jangle / Light Crunch

```yaml
amp:
  model: AC20
  power: true
  standby: true
  powerLevel: 5.0
  volume: 4.5
  cut: 4.5
  bright: true
  bassCut: true
```

#### Vox-Style Singing Lead

```yaml
amp:
  model: AC20
  power: true
  standby: true
  powerLevel: 6.5
  volume: 6.5
  cut: 4.0
  bright: true
  bassCut: false
```

#### Classic-Rock Crunch

```yaml
amp:
  model: AC20
  power: true
  standby: true
  powerLevel: 5.8
  volume: 5.4
  cut: 4.2
  bright: true
  bassCut: true
```

### AC20 Generator Rules

- Increase `volume` for amp breakup.
- Increase `cut` to reduce brightness; decrease `cut` for more chime.
- Use `bright: true` for jangle and presence.
- Use `bassCut: true` to tighten Les Paul low end.
- Disable `bassCut` for thicker lead tones.

---

## 12. PR12 Amp

```ts
interface Pr12AmpConfig {
  model: 'PR12';
  power: boolean;
  standby: boolean;
  dwell: Knob;  // 0.0 to 10.0
  reverb: Knob; // 0.0 to 10.0
  bass: Knob;   // 0.0 to 10.0
  treble: Knob; // 0.0 to 10.0
  volume: Knob; // 0.0 to 10.0
}
```

### PR12 Templates

#### Fender Clean / Eagles Rhythm / Blues Clean

```yaml
amp:
  model: PR12
  power: true
  standby: true
  volume: 3.6
  bass: 4.8
  treble: 6.2
  reverb: 2.4
  dwell: 3.6
```

#### Saggy Blues Breakup

```yaml
amp:
  model: PR12
  power: true
  standby: true
  volume: 5.8
  bass: 4.2
  treble: 5.8
  reverb: 2.0
  dwell: 3.0
```

### PR12 Generator Rules

- Use PR12 as the default for clean classic-rock rhythm.
- Keep `volume` around `3.0–4.2` for clean rhythm.
- Raise `volume` to around `5.5–6.2` for breakup.
- For Les Paul, keep `bass` around `4.2–5.2` to avoid mud.
- Use `treble 5.5–6.5` for clean articulation.
- Keep amp reverb moderate if post reverb is also enabled.

---

## 13. SW50R Amp

SW50R is the smooth, Dumble-style platform. It is useful for singing lead, polished clean lead, and warm high-headroom rhythm.

```ts
interface Sw50rAmpConfig {
  model: 'SW50R';
  power: boolean;
  standby: boolean;
  inputMode: 'DEFAULT' | '-6_DB';
  volume: Knob;       // 0.0 to 10.0
  level: Knob;        // 0.0 to 10.0
  bass: Knob;         // 0.0 to 10.0
  mid: Knob;          // 0.0 to 10.0
  treble: Knob;       // 0.0 to 10.0
  reverb: Knob;       // 0.0 to 10.0
  bright: boolean;
  bassEmphasis: boolean;
}
```

### SW50R Templates

#### Smooth Clean Lead Platform

```yaml
amp:
  model: SW50R
  power: true
  standby: true
  inputMode: DEFAULT
  volume: 3.8
  level: 5.0
  bass: 4.8
  mid: 5.8
  treble: 5.2
  bright: false
  bassEmphasis: false
  reverb: 2.0
```

#### Dumble-Style Singing Blues Lead

```yaml
amp:
  model: SW50R
  power: true
  standby: true
  inputMode: DEFAULT
  volume: 5.2
  level: 5.0
  bass: 4.5
  mid: 6.5
  treble: 5.0
  bright: false
  bassEmphasis: true
  reverb: 1.8
```

#### Cleaner High-Headroom Rhythm

```yaml
amp:
  model: SW50R
  power: true
  standby: true
  inputMode: -6_DB
  volume: 4.5
  level: 5.5
  bass: 5.0
  mid: 5.0
  treble: 5.8
  bright: true
  bassEmphasis: false
  reverb: 1.5
```

### SW50R Generator Rules

- Use SW50R for smooth lead tones and polished clean lead.
- Use `inputMode: -6_DB` for cleaner high-headroom sounds.
- Use `bassEmphasis: true` for thicker lead, but avoid it for already-boomy Les Paul neck tones.
- Use `mid 6.0–6.8` for singing lead sustain.
- Use `bright: false` for warmer leads, `bright: true` for articulate clean rhythm.

---

## 14. Cab / IR Configuration

The cab section can use factory microphones or custom IRs. A practical generator should support both.

```ts
interface CabConfig {
  bypassed: boolean;
  slots: CabSlotConfig[];
}

type CabSlotConfig = FactoryMicSlot | CustomIrSlot;

interface FactoryMicSlot {
  enabled: boolean;
  sourceType: 'FACTORY_MIC';
  micId: 'MIC_1' | 'MIC_2' | 'MIC_3' | 'MIC_4' | 'MIC_5' | 'MIC_6';
  position: number; // practical 0.000 to 1.000
  distance: number; // practical 0.000 to 1.000
  levelDb: Db;
  pan: PanValue;
  phase: 'NORMAL' | 'INVERTED';
  roomSendEnabled: boolean;
  roomSendLevelDb?: Db;
}

interface CustomIrSlot {
  enabled: boolean;
  sourceType: 'CUSTOM_IR';
  irPathOrName: string;
  levelDb: Db;
  pan: PanValue;
  phase: 'NORMAL' | 'INVERTED';
  roomSendEnabled: boolean;
  roomSendLevelDb?: Db;
}

type PanValue = 'C' | `L${number}` | `R${number}` | number;
```

### Common Cab Recipes

#### Bright Focused Classic Rock

```yaml
cab:
  bypassed: false
  slots:
    - enabled: true
      sourceType: FACTORY_MIC
      micId: MIC_2
      position: 0.45
      distance: 0.20
      levelDb: 0.0
      pan: C
      phase: NORMAL
      roomSendEnabled: false
```

#### Fuller Clean Rhythm

```yaml
cab:
  bypassed: false
  slots:
    - enabled: true
      sourceType: FACTORY_MIC
      micId: MIC_2
      position: 0.55
      distance: 0.25
      levelDb: -1.0
      pan: C
      phase: NORMAL
      roomSendEnabled: true
      roomSendLevelDb: -12.0
    - enabled: true
      sourceType: FACTORY_MIC
      micId: MIC_4
      position: 0.70
      distance: 0.35
      levelDb: -4.0
      pan: C
      phase: NORMAL
      roomSendEnabled: true
      roomSendLevelDb: -15.0
```

#### Wider Stereo Practice Sound

```yaml
cab:
  bypassed: false
  slots:
    - enabled: true
      sourceType: FACTORY_MIC
      micId: MIC_2
      position: 0.48
      distance: 0.20
      levelDb: -1.0
      pan: L25
      phase: NORMAL
      roomSendEnabled: false
    - enabled: true
      sourceType: FACTORY_MIC
      micId: MIC_5
      position: 0.68
      distance: 0.35
      levelDb: -3.0
      pan: R25
      phase: NORMAL
      roomSendEnabled: false
```

### Cab Generator Rules

- Use `MIC_2` as a reliable main mic for classic rock.
- Add `MIC_4` or `MIC_5` lower in level for fullness or width.
- Keep one-mic presets centered unless the user wants stereo width.
- Use `phase: NORMAL` unless the user reports phase cancellation or a custom IR requires inversion.
- For custom IRs, do not rely on position/distance controls.

---

## 15. Graphic EQ Configuration

The EQ is a 9-band graphic EQ. Each band supports approximately `-12.0 dB` to `+12.0 dB`.

```ts
interface EqConfig {
  enabled: boolean;
  bandsDb: {
    hz65: Db;
    hz125: Db;
    hz250: Db;
    hz500: Db;
    hz1000: Db;
    hz2000: Db;
    hz4000: Db;
    hz8000: Db;
    hz16000: Db;
  };
  hpfHz?: number | 'OFF';
  lpfHz?: number | 'OFF';
}
```

### EQ Templates

#### Natural / Mostly Flat

```yaml
eq:
  enabled: true
  bandsDb:
    hz65: -1.5
    hz125: -0.5
    hz250: 0.0
    hz500: 0.0
    hz1000: 0.0
    hz2000: 0.5
    hz4000: 0.5
    hz8000: 0.0
    hz16000: -1.0
  hpfHz: 80
  lpfHz: 9000
```

#### Classic-Rock Lead Focus

```yaml
eq:
  enabled: true
  bandsDb:
    hz65: -2.0
    hz125: -1.0
    hz250: -0.5
    hz500: 0.5
    hz1000: 1.5
    hz2000: 2.0
    hz4000: 1.0
    hz8000: -0.5
    hz16000: -2.0
  hpfHz: 90
  lpfHz: 7500
```

#### Warm Clean Rhythm

```yaml
eq:
  enabled: true
  bandsDb:
    hz65: -1.0
    hz125: 0.5
    hz250: 0.5
    hz500: 0.0
    hz1000: -0.5
    hz2000: 0.0
    hz4000: 0.5
    hz8000: -0.5
    hz16000: -2.0
  hpfHz: 75
  lpfHz: 8500
```

### EQ Generator Rules

- Use HPF around `75–90 Hz` for most Les Paul presets.
- Use LPF around `7200–9000 Hz` for classic rock.
- For lead, push `1 kHz` and `2 kHz` rather than simply increasing treble everywhere.
- For harshness, reduce `4 kHz`, `8 kHz`, or lower the LPF.
- For muddiness, reduce `125 Hz` and `250 Hz` before cutting amp bass too aggressively.

---

## 16. Post FX Configuration

Post-FX chain:

```text
Delay -> Reverb
```

```ts
interface PostFxConfig {
  delay: DelayConfig;
  reverb: ReverbConfig;
}
```

---

## 17. Delay

```ts
interface DelayConfig {
  enabled: boolean;
  mix: Knob;                     // 0.0 to 10.0
  syncMode: 'FREE' | 'DAW_APP' | 'TAP';
  timeMs?: number;               // 16 to 1500 ms when unsynced
  timeNote?: NoteValue;          // 1/64T to 1/1D when synced
  pingPong: boolean;
  feedback: Knob;                // 0.0 to 10.0
  hpfHz: number;                 // 60 to 500 Hz
  lpfHz: number;                 // 1000 to 5000 Hz
  tapeDrive: Knob;               // 0.0 to 10.0
  width: Knob;                   // 0.0 to 10.0
}
```

### Delay Templates

#### Subtle Slapback

```yaml
delay:
  enabled: true
  syncMode: FREE
  timeMs: 115
  mix: 1.8
  feedback: 1.5
  pingPong: false
  hpfHz: 150
  lpfHz: 4200
  tapeDrive: 2.0
  width: 2.0
```

#### Hotel California / Classic Lead Delay

```yaml
delay:
  enabled: true
  syncMode: DAW_APP
  timeNote: 1/4
  mix: 2.6
  feedback: 3.2
  pingPong: false
  hpfHz: 180
  lpfHz: 3600
  tapeDrive: 2.5
  width: 4.0
```

#### Big Stereo Lead

```yaml
delay:
  enabled: true
  syncMode: DAW_APP
  timeNote: 1/4D
  mix: 3.2
  feedback: 4.0
  pingPong: true
  hpfHz: 220
  lpfHz: 3300
  tapeDrive: 3.0
  width: 7.0
```

### Delay Generator Rules

- Keep delay off for tight dry rhythm unless the song needs slapback.
- For classic lead, use `1/4` or `1/4D` with `mix 2.2–3.2`.
- For mono/practice realism, keep `pingPong: false` and `width 2.0–4.0`.
- For stereo lead ambience, enable `pingPong` and use `width 6.0–8.0`.
- Use delay HPF/LPF to keep repeats behind the dry guitar.

---

## 18. Reverb

```ts
interface ReverbConfig {
  enabled: boolean;
  mix: Knob;        // 0.0 to 10.0
  preDelayMs: number; // 1 to 200 ms
  decaySec: number;   // 1 to 60 seconds
  hpfHz: number;      // 50 to 700 Hz
  lpfHz: number;      // 1000 to 10000 Hz
}
```

### Reverb Templates

#### Small Room / Always-On

```yaml
reverb:
  enabled: true
  mix: 1.5
  preDelayMs: 20
  decaySec: 1.8
  hpfHz: 150
  lpfHz: 6500
```

#### Classic Clean Spring-ish Ambience

```yaml
reverb:
  enabled: true
  mix: 2.5
  preDelayMs: 35
  decaySec: 2.8
  hpfHz: 180
  lpfHz: 6000
```

#### Large Lead Ambience

```yaml
reverb:
  enabled: true
  mix: 3.2
  preDelayMs: 60
  decaySec: 4.5
  hpfHz: 220
  lpfHz: 5500
```

### Reverb Generator Rules

- Clean rhythm: `mix 1.5–2.5`, `decay 1.8–2.8s`.
- Lead: `mix 2.2–3.4`, `decay 2.8–4.5s`.
- Keep reverb lower when amp reverb is already active.
- Use higher HPF for lead reverb to avoid muddy low-end ambience.

---

## 19. Guitar Notes

These fields are not plugin controls, but they make generated presets more useful.

```ts
interface GuitarNotes {
  pickup?: 'bridge' | 'middle' | 'neck';
  guitarVolume?: number; // 0 to 10
  guitarTone?: number;   // 0 to 10
  playingNotes?: string[];
}
```

Example:

```yaml
guitarNotes:
  pickup: bridge
  guitarVolume: 10
  guitarTone: 8
  playingNotes:
    - Pick closer to the bridge for more attack.
    - Roll tone down slightly if the bridge pickup is harsh.
```

---

## 20. Preset Generator Strategy

### 20.1 Tone Intent Mapping

| Intent | Amp | Pre FX | EQ | Post FX |
|---|---|---|---|---|
| Clean rhythm | PR12 | subtle compressor, drives off | warm clean or natural | small room or spring-ish reverb |
| Edge of breakup | PR12 or AC20 | optional OD1 drive `1.5–2.5` | natural with mild low cut | light reverb |
| Classic-rock crunch | AC20 | OD1 drive `2.2–4.2` | mild mids, controlled highs | usually reverb only |
| Singing classic-rock lead | SW50R | OD1 drive `2.5–3.2` | lead-focus mids | quarter-note delay + medium reverb |
| Blues lead | SW50R or PR12 | OD2 or OD1 depending thickness | mid boost, low cleanup | medium reverb, optional delay |
| Wide stereo lead | SW50R | OD1/OD2 as needed | lead-focus mids | ping-pong delay + larger reverb |
| Tremolo clean | PR12 | compressor optional, tremolo on | warm clean | reverb |

### 20.2 Les Paul Adjustments

For a Gibson Les Paul:

- Reduce excess low end before it reaches the post effects.
- Prefer HPF `80–90 Hz` for most presets.
- Avoid excessive amp bass on PR12 and SW50R.
- Bridge pickup lead often needs controlled highs: LPF `7000–8000 Hz` and moderate `4 kHz/8 kHz`.
- Neck pickup lead may need less bass and slightly more `2 kHz` presence.
- Clean rhythm usually benefits from enough treble/presence to avoid becoming woolly.

### 20.3 Output Level Rules

Use the following starting output values:

| Preset Type | Output Starting Point |
|---|---:|
| Clean rhythm | `-3.0 dB` |
| Edge of breakup | `-3.5 dB` |
| Crunch rhythm | `-4.0 dB` |
| Lead with OD/delay/reverb | `-3.5 dB` |
| Big stereo lead | `-4.5 dB` |

Then level-match by ear or metering.

---

## 21. Validation Rules

Your generator should validate at least the following:

```ts
const validationRules = {
  knob: { min: 0.0, max: 10.0 },
  eqBandDb: { min: -12.0, max: 12.0 },
  transposeSemitones: { min: -12, max: 12 },
  doublerSpreadMs: { min: 3, max: 20 },
  tremoloRateHz: { min: 0.05, max: 5.0 },
  delayTimeMs: { min: 16, max: 1500 },
  delayHpfHz: { min: 60, max: 500 },
  delayLpfHz: { min: 1000, max: 5000 },
  reverbPreDelayMs: { min: 1, max: 200 },
  reverbDecaySec: { min: 1, max: 60 },
  reverbHpfHz: { min: 50, max: 700 },
  reverbLpfHz: { min: 1000, max: 10000 },
  cabPosition: { min: 0.0, max: 1.0 },
  cabDistance: { min: 0.0, max: 1.0 }
};
```

### Cross-Field Rules

- If `delay.syncMode === 'FREE'`, require `timeMs` and ignore `timeNote`.
- If `delay.syncMode === 'DAW_APP'` or `TAP`, require `timeNote` and ignore `timeMs`.
- If `tremolo.syncMode === 'FREE'`, require `rateHz` and ignore `rateNote`.
- If `tremolo.syncMode === 'NOTE'`, require `rateNote` and ignore `rateHz`.
- If `global.doublerEnabled === false`, `doublerSpreadMs` can be omitted or kept as a remembered value.
- If `cab.bypassed === true`, generator should skip cab slot validation except for structure.
- For `CUSTOM_IR`, do not require `position` or `distance`.
- For `FACTORY_MIC`, require `micId`, `position`, and `distance`.

---

## 22. Display Format for Generated Presets

Use this format when printing a preset for manual entry into the plugin.

```text
Preset: <Song / Part / Guitar Role>

GLOBAL
INPUT <x.x> dB
GATE ON/OFF
GATE THRESHOLD <x.x>    # only if gate is on
TRANSPOSE <n>
INPUT MODE MONO/STEREO
DOUBLER ON/OFF
DOUBLER SPREAD <n> ms   # only if doubler is on
OUTPUT <x.x> dB

PRE FX
CMP ON/OFF
COMP <x.x>
RELEASE FAST/SLOW
LEVEL <x.x>
MIX <x.x>

OD1 ON/OFF
DRIVE <x.x>
LEVEL <x.x>
TONE <x.x>

OD2 ON/OFF
GAIN <x.x>
LEVEL <x.x>
BASS <x.x>
TREBLE <x.x>

TRM ON/OFF
SYNC FREE/NOTE
RATE <Hz or note>
DEPTH <x.x>
LEVEL <x.x>

AMP
AMP AC20/PR12/SW50R
<amp-specific controls>

CAB
MIC <n> ON/OFF
POSITION <0.00>
DISTANCE <0.00>
MIC LEVEL <x.x> dB
PAN C/Lxx/Rxx
PHASE NORMAL/INVERTED
ROOM SEND ON/OFF
ROOM SEND LEVEL <x.x> dB

EQ
EQ ON/OFF
65 Hz <x.x> dB
125 Hz <x.x> dB
250 Hz <x.x> dB
500 Hz <x.x> dB
1 kHz <x.x> dB
2 kHz <x.x> dB
4 kHz <x.x> dB
8 kHz <x.x> dB
16 kHz <x.x> dB
HPF <Hz/OFF>
LPF <Hz/OFF>

POST FX
DLY ON/OFF
SYNC FREE/DAW_APP/TAP
TIME <ms or note>
MIX <x.x>
FEEDBACK <x.x>
PING-PONG ON/OFF
HPF <Hz>
LPF <Hz>
TAPE DRIVE <x.x>
WIDTH <x.x>

RVB ON/OFF
MIX <x.x>
PRE DELAY <ms>
DECAY <seconds>
HPF <Hz>
LPF <Hz>

GUITAR NOTES
Pickup: <bridge/middle/neck>
Guitar volume: <0-10>
Guitar tone: <0-10>
Playing notes:
- <note>
```

---

## 23. Complete Starter Presets

### 23.1 Eagles / Clean Rhythm / Hotel California Clean-ish Base

```yaml
metadata:
  presetName: Eagles - Hotel California - Clean Rhythm Base
  artist: Eagles
  song: Hotel California
  part: rhythm
  style: clean classic-rock rhythm
  targetGuitar: Gibson Les Paul + Focusrite Scarlett Solo

global:
  inputDb: 0.0
  gateEnabled: false
  transposeSemitones: 0
  inputMode: MONO
  doublerEnabled: false
  outputDb: -3.0

preFx:
  compressor:
    enabled: true
    comp: 2.8
    releaseMode: SLOW
    level: 5.0
    mix: 4.2
  od1:
    enabled: false
    drive: 0.0
    level: 5.0
    tone: 5.0
  od2:
    enabled: false
    gain: 0.0
    level: 5.0
    bass: 5.0
    treble: 5.0
  tremolo:
    enabled: false
    syncMode: FREE
    rateHz: 2.1
    depth: 0.0
    level: 5.0

amp:
  model: PR12
  power: true
  standby: true
  volume: 3.6
  bass: 4.8
  treble: 6.2
  reverb: 2.4
  dwell: 3.6

cab:
  bypassed: false
  slots:
    - enabled: true
      sourceType: FACTORY_MIC
      micId: MIC_2
      position: 0.48
      distance: 0.22
      levelDb: 0.0
      pan: C
      phase: NORMAL
      roomSendEnabled: false
    - enabled: true
      sourceType: FACTORY_MIC
      micId: MIC_4
      position: 0.68
      distance: 0.35
      levelDb: -4.5
      pan: C
      phase: NORMAL
      roomSendEnabled: false

eq:
  enabled: true
  bandsDb:
    hz65: -1.5
    hz125: -0.5
    hz250: -0.5
    hz500: 0.0
    hz1000: 0.3
    hz2000: 0.8
    hz4000: 0.8
    hz8000: -0.3
    hz16000: -2.0
  hpfHz: 80
  lpfHz: 8500

postFx:
  delay:
    enabled: true
    syncMode: FREE
    timeMs: 115
    mix: 1.4
    feedback: 1.2
    pingPong: false
    hpfHz: 180
    lpfHz: 4000
    tapeDrive: 1.5
    width: 2.0
  reverb:
    enabled: true
    mix: 1.8
    preDelayMs: 25
    decaySec: 2.2
    hpfHz: 170
    lpfHz: 6500

guitarNotes:
  pickup: bridge
  guitarVolume: 10
  guitarTone: 8
  playingNotes:
    - Keep picking clean and controlled.
    - Reduce guitar tone slightly if the bridge pickup sounds too sharp.
```

---

### 23.2 Joe Walsh / Eagles-Style Singing Lead

```yaml
metadata:
  presetName: Joe Walsh - Eagles-Style Singing Lead
  artist: Eagles / Joe Walsh style
  part: lead
  style: singing classic-rock lead
  targetGuitar: Gibson Les Paul + Focusrite Scarlett Solo

global:
  inputDb: 0.0
  gateEnabled: false
  transposeSemitones: 0
  inputMode: MONO
  doublerEnabled: false
  outputDb: -3.5

preFx:
  compressor:
    enabled: true
    comp: 2.2
    releaseMode: SLOW
    level: 5.0
    mix: 3.5
  od1:
    enabled: true
    drive: 2.8
    level: 6.3
    tone: 5.2
  od2:
    enabled: false
    gain: 0.0
    level: 5.0
    bass: 5.0
    treble: 5.0
  tremolo:
    enabled: false
    syncMode: FREE
    rateHz: 2.1
    depth: 0.0
    level: 5.0

amp:
  model: SW50R
  power: true
  standby: true
  inputMode: DEFAULT
  volume: 4.8
  level: 5.0
  bass: 4.5
  mid: 6.2
  treble: 5.0
  bright: false
  bassEmphasis: true
  reverb: 1.8

cab:
  bypassed: false
  slots:
    - enabled: true
      sourceType: FACTORY_MIC
      micId: MIC_2
      position: 0.50
      distance: 0.20
      levelDb: 0.0
      pan: C
      phase: NORMAL
      roomSendEnabled: false
    - enabled: true
      sourceType: FACTORY_MIC
      micId: MIC_5
      position: 0.72
      distance: 0.32
      levelDb: -5.0
      pan: C
      phase: NORMAL
      roomSendEnabled: false

eq:
  enabled: true
  bandsDb:
    hz65: -2.5
    hz125: -1.0
    hz250: -0.5
    hz500: 0.5
    hz1000: 1.3
    hz2000: 2.0
    hz4000: 0.8
    hz8000: -0.8
    hz16000: -2.5
  hpfHz: 90
  lpfHz: 7200

postFx:
  delay:
    enabled: true
    syncMode: DAW_APP
    timeNote: 1/4
    mix: 2.4
    feedback: 3.0
    pingPong: false
    hpfHz: 200
    lpfHz: 3600
    tapeDrive: 2.3
    width: 3.5
  reverb:
    enabled: true
    mix: 2.2
    preDelayMs: 45
    decaySec: 3.0
    hpfHz: 220
    lpfHz: 6000

guitarNotes:
  pickup: bridge
  guitarVolume: 10
  guitarTone: 7.5
  playingNotes:
    - Use controlled vibrato and sustain notes fully.
    - Avoid over-picking; let the OD1 and SW50R provide sustain.
```

---

### 23.3 AC20 Classic-Rock Crunch

```yaml
metadata:
  presetName: AC20 Classic-Rock Crunch
  part: rhythm
  style: British-flavored classic-rock crunch
  targetGuitar: Gibson Les Paul + Focusrite Scarlett Solo

global:
  inputDb: 0.0
  gateEnabled: false
  transposeSemitones: 0
  inputMode: MONO
  doublerEnabled: false
  outputDb: -4.0

preFx:
  compressor:
    enabled: false
    comp: 0.0
    releaseMode: SLOW
    level: 5.0
    mix: 0.0
  od1:
    enabled: true
    drive: 2.2
    level: 6.0
    tone: 5.4
  od2:
    enabled: false
    gain: 0.0
    level: 5.0
    bass: 5.0
    treble: 5.0
  tremolo:
    enabled: false
    syncMode: FREE
    rateHz: 2.1
    depth: 0.0
    level: 5.0

amp:
  model: AC20
  power: true
  standby: true
  powerLevel: 5.8
  volume: 5.4
  cut: 4.2
  bright: true
  bassCut: true

cab:
  bypassed: false
  slots:
    - enabled: true
      sourceType: FACTORY_MIC
      micId: MIC_2
      position: 0.44
      distance: 0.18
      levelDb: 0.0
      pan: C
      phase: NORMAL
      roomSendEnabled: false
    - enabled: true
      sourceType: FACTORY_MIC
      micId: MIC_4
      position: 0.65
      distance: 0.28
      levelDb: -4.0
      pan: C
      phase: NORMAL
      roomSendEnabled: false

eq:
  enabled: true
  bandsDb:
    hz65: -2.0
    hz125: -1.0
    hz250: -0.5
    hz500: 0.3
    hz1000: 0.8
    hz2000: 1.2
    hz4000: 0.8
    hz8000: -0.5
    hz16000: -2.0
  hpfHz: 90
  lpfHz: 8000

postFx:
  delay:
    enabled: false
    syncMode: FREE
    timeMs: 115
    mix: 0.0
    feedback: 0.0
    pingPong: false
    hpfHz: 180
    lpfHz: 4000
    tapeDrive: 0.0
    width: 0.0
  reverb:
    enabled: true
    mix: 1.7
    preDelayMs: 25
    decaySec: 2.0
    hpfHz: 170
    lpfHz: 6500

guitarNotes:
  pickup: bridge
  guitarVolume: 10
  guitarTone: 8
  playingNotes:
    - Keep palm muting controlled to avoid blurry multi-string distortion.
    - Reduce OD1 drive slightly if chords lose clarity.
```

---

## 24. Minimal Default Preset Object

Use this as a safe base before applying tone-specific changes.

```yaml
metadata:
  presetName: Morgan Default Base
  part: general
  style: neutral base

global:
  inputDb: 0.0
  gateEnabled: false
  gateThreshold: 2.0
  transposeSemitones: 0
  inputMode: MONO
  doublerEnabled: false
  doublerSpreadMs: 8
  outputDb: -3.0

preFx:
  compressor:
    enabled: false
    comp: 0.0
    releaseMode: SLOW
    level: 5.0
    mix: 0.0
  od1:
    enabled: false
    drive: 0.0
    level: 5.0
    tone: 5.0
  od2:
    enabled: false
    gain: 0.0
    level: 5.0
    bass: 5.0
    treble: 5.0
  tremolo:
    enabled: false
    syncMode: FREE
    rateHz: 2.1
    depth: 0.0
    level: 5.0

amp:
  model: PR12
  power: true
  standby: true
  volume: 3.6
  bass: 4.8
  treble: 6.0
  reverb: 2.0
  dwell: 3.5

cab:
  bypassed: false
  slots:
    - enabled: true
      sourceType: FACTORY_MIC
      micId: MIC_2
      position: 0.50
      distance: 0.22
      levelDb: 0.0
      pan: C
      phase: NORMAL
      roomSendEnabled: false

eq:
  enabled: true
  bandsDb:
    hz65: -1.5
    hz125: -0.5
    hz250: 0.0
    hz500: 0.0
    hz1000: 0.0
    hz2000: 0.5
    hz4000: 0.5
    hz8000: 0.0
    hz16000: -1.0
  hpfHz: 80
  lpfHz: 9000

postFx:
  delay:
    enabled: false
    syncMode: FREE
    timeMs: 115
    mix: 0.0
    feedback: 0.0
    pingPong: false
    hpfHz: 180
    lpfHz: 4000
    tapeDrive: 0.0
    width: 0.0
  reverb:
    enabled: true
    mix: 1.5
    preDelayMs: 20
    decaySec: 1.8
    hpfHz: 150
    lpfHz: 6500
```

---

## 25. Generator Prompt Template

Use this as the input contract for song-specific generation.

```text
Generate a Morgan Amps Suite preset.

Required:
- Song or artist/style reference
- Guitar role: clean rhythm / crunch rhythm / lead / solo / intro / etc.

Optional:
- Guitar pickup
- Desired realism: practice / recording / stereo wide
- Backing track context
- Whether the tone should cut through or sit behind vocals
- Whether delay/reverb should be subtle or obvious

Output:
- Full MorganPreset object
- Manual-entry display format
- Short guitar notes
- Level-matching suggestion
```

---

## 26. Practical Generation Defaults

When information is missing, use these defaults:

```yaml
defaults:
  guitar: Gibson Les Paul
  interface: Focusrite Scarlett Solo
  inputMode: MONO
  transposeSemitones: 0
  doublerEnabled: false
  gateEnabled: false
  cabMainMic: MIC_2
  eqHpfHz: 80
  eqLpfHz: 8500
  outputDb: -3.0
  cleanAmp: PR12
  leadAmp: SW50R
  crunchAmp: AC20
```

---

## 27. Common Fixes

| Problem | First Fix | Second Fix |
|---|---|---|
| Tone is too muddy | Lower `125 Hz` / `250 Hz`; raise HPF to `90 Hz` | Reduce amp bass or disable bass emphasis |
| Tone is too harsh | Lower `4 kHz` / `8 kHz`; lower LPF | Reduce OD tone/treble or increase AC20 cut |
| Lead does not sustain | Raise OD1 level/drive slightly | Add subtle compressor or raise amp volume |
| Chords blur together | Lower drive/gain | Tighten bass with HPF and reduce low EQ bands |
| Backing track buries guitar | Boost `1 kHz` and `2 kHz` | Increase output only after EQ is right |
| Delay is too obvious | Lower delay mix/feedback | Lower delay LPF to darken repeats |
| Reverb clouds the tone | Lower reverb mix/decay | Raise reverb HPF |
| Single notes sound thin | Add mids around `1–2 kHz` | Use SW50R with bass emphasis carefully |

---

## 28. Naming Recommendations

Use deterministic names so presets are easy to search and regenerate.

```text
<Artist> - <Song> - <Part> - Morgan <Amp>
```

Examples:

```text
Eagles - Hotel California - Clean Rhythm - Morgan PR12
Eagles - Hotel California - Solo - Morgan SW50R
AC20 - Classic Rock Crunch - Morgan AC20
```

For generated variants:

```text
<Artist> - <Song> - <Part> - <Amp> - v<major>.<minor>
```

Example:

```text
Eagles - How Long - Lead - AC20 - v1.0
```
