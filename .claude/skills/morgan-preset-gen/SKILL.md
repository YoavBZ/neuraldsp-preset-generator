---
name: morgan-preset-gen
description: |
  Generate or edit Neural DSP Morgan Amps Suite preset files (.xml binary)
  from a song name + guitar role, or from a free-language edit request
  against an existing preset.
---

# Morgan Amps Suite Preset Generator

This skill generates and edits binary `.xml` presets for **Neural DSP's
Morgan Amps Suite** plugin. The user owns a licensed copy; this is personal
interoperability — see `NOTICE.md` at the repo root.

## What you (the agent) need to know up-front

1. The file is **binary** despite its `.xml` extension. There is no public
   spec. We use a **template-based writer**: clone a known-good preset and
   mutate only the printable string values of its parameters. Wrapper bytes
   are preserved verbatim, so the plugin always loads the output.
2. The parameter set the writer can touch is whatever appears in the
   template preset(s) in `samples/`. The catalog of kinds/units/ranges is
   `schema/morgan_schema.json`, auto-built from `samples/`.
   **`schema/morgan_schema.json` is not in the repo** — it is generated,
   and it echoes every string in your presets (including absolute IR
   paths), so it is git-ignored. If it is missing, `apply_spec.py` and
   `show.py` will fail with `FileNotFoundError`. Build it first:
   ```bash
   python -m schema.build_schema
   ```
   That requires at least one preset in `samples/`. The repo ships
   `samples/Example_Clean_PR12.xml`, so this works on a fresh clone —
   but a schema built from one preset has very narrow `observed_min`/
   `observed_max` ranges, so expect out-of-range warnings until the user
   adds more of their own presets. Surface that to the user rather than
   silently ignoring the warnings.
3. **Never edit the binary by hand.** Always go through the helper scripts
   so the marker bytes stay intact.

## Modes

### `generate` — song + role → new preset

Inputs from the user:
- `--song "Hotel California"`  (free text)
- `--role lead | rhythm | clean | …`
- `--out path/to/new-preset.xml`

Your job:
1. **Research the tone.** Use WebSearch + WebFetch to look up the song's
   recorded guitar signal chain. Good sources: Premier Guitar rig
   rundowns, artist interviews, GuitarWorld tone breakdowns, well-cited
   forum threads, video lesson notes. Capture (a) the amp character
   (Vox/Marshall/Fender-ish? clean/edge/drive?), (b) the effects (delay,
   reverb, chorus, drive pedals), and (c) the role's place in the mix.
2. **Map to Morgan vocabulary** using `knowledge/tone-references.md`.
   Morgan Amps Suite has three amps:
   - **PR12** (`pr12Amp` module) — Princeton-flavored low-watt
     break-up, great for cleans and edge-of-breakup.
   - **SW50R** (`sw50rAmp` module) — Morgan SW50R, AC-style chime with
     more headroom and a master volume; good for cleans → mid-gain.
   - **AC20** (`ac20Amp` module) — AC15/AC30-flavored chime with bite.

   Pick the active amp by setting the **top-level** `selectedAmp` key
   (module = `""`). All three amp modules are always present in every
   preset file; `selectedAmp` just chooses which is live. Confirmed
   mapping:

   | value | amp   |
   |-------|-------|
   | `0`   | AC20  |
   | `1`   | PR12  |
   | `2`   | SW50R |

   So **any** template can produce **any** amp — set `selectedAmp`
   explicitly, then tweak that amp's knobs.
3. **Pick a template** from `samples/`.
   - Default to `samples/Example_Clean_PR12.xml`, the example shipped with
     this repo. It is IR-free and therefore portable, so it is the safe
     base for anything you generate.
   - If the user has their own presets in `samples/`, one of those is a
     fine template too — cloning one that already uses the amp you want
     saves you setting `selectedAmp`. Run `show.py` on it first to see
     which amp is selected and what the knobs are currently at.
   - Whichever you choose, set `selectedAmp` explicitly in the spec unless
     you have confirmed the template already has the value you want. Don't
     assume.
4. **Produce a spec JSON** with the parameter overrides you want. Values
   are **human values** — `apply_spec.py` translates them to the binary's
   stored encoding using each parameter's `kind` in `morgan_schema.json`.
   ```json
   {
     "name": "Hotel California Lead",
     "parameters": [
       {"module": "sw50rAmp", "key": "sw50rVolume", "value": 62},
       {"module": "delay",    "key": "delayActive", "value": true},
       {"module": "delay",    "key": "delayMix",    "value": 35},
       {"module": "delay",    "key": "delayTime",   "value": 480}
     ]
   }
   ```

   ### The value convention (important)

   The plugin's knobs have **no numbers on them** — a knob is just a
   rotation from fully left to fully right. So a bare knob's value is a
   **percent of rotation, 0–100** (noon = 50). Controls that *do* show
   numbers in the UI use those real units. Each parameter's `kind` (in
   `morgan_schema.json`) tells you which:

   | kind       | value you write            | example |
   |------------|----------------------------|---------|
   | `rotation` | percent **0–100**          | `62` (→ knob ~62% / ~2 o'clock) |
   | `fraction` | decimal **0.0–1.0**        | `0.30` (cab position/distance) |
   | `metered`  | the **native unit** below  | `-65` dB, `480` ms, `5000` Hz |
   | `switch`   | `true` / `false`           | `true` |
   | `enum`     | integer selector           | `selectedAmp: 1` |

   `metered` units (from each param's `unit` field): **dB** (gate, input/
   output, mic levels, EQ bands), **Hz** (HPF/LPF/cuts, tremolo rate),
   **ms** (delay time, pre-delay, doubler spread), **seconds** (reverb
   decay), **BPM** (tempo), **semitones** (transpose).

   Guidance:
   - There is **no universal default** per knob. Anchor on the
     `observed_values` for that exact knob in `morgan_schema.json` (real
     positions observed in the presets the schema was built from), and use
     **noon (50%)** as the neutral start for tone stacks (bass/mid/treble).
   - Choose the active amp with `selectedAmp` (`0`=AC20, `1`=PR12,
     `2`=SW50R) — see step 2.
   - Staying within `observed_min`/`observed_max` is safest; going outside
     is allowed but the tool will print a warning — surface it to the user.
   - Run `show.py` on any preset to see every parameter's `kind`, `stored`
     value, and `human`/`display` value — read this before editing.
   - Escape hatch: add `"raw": true` to an entry to write its `value` as
     the literal stored string (for IR file paths or any `unknown` kind).
5. **Apply the spec** (use `--strip-irs` so the preset is portable —
   see the Cab section):
   ```bash
   python .claude/skills/morgan-preset-gen/scripts/apply_spec.py \
     --template samples/Example_Clean_PR12.xml \
     --spec /tmp/spec.json \
     --strip-irs \
     --out path/to/new-preset.xml
   ```
6. **Validate** by re-parsing the output with `show.py` and confirming
   the values match the spec. Tell the user (a) which template you used,
   (b) what research you based the tone on (with links), (c) any
   parameters you set outside observed ranges.

### `edit` — existing preset + free-language ask → new preset

Inputs:
- `--in path/to/existing.xml`
- `--ask "more reverb, tighter low end"`
- `--out path/to/edited.xml`

Your job:
1. **Read the current state**:
   ```bash
   python .claude/skills/morgan-preset-gen/scripts/show.py path/to/existing.xml
   ```
2. **Interpret the ask** against the current values (which `show.py`
   gives you as percent / native units). Examples — all in human terms:
   - "more reverb" → raise `reverb/reverbMix` and/or the active amp's
     reverb knob (`pr12Reverb` / `sw50rReverb`) by ~10–15 percentage
     points (rotation, cap 100).
   - "tighter low end" → drop the active amp's bass knob a few points
     (`pr12Bass` / `sw50rBass`), and/or raise `reverb/reverbLowCut` and
     `delay/delayLowCut` (Hz).
   - "more presence" → raise the active amp's treble knob, or nudge the
     upper EQ bands (`pr12EQBand7..9`, in dB).
3. **Produce a spec** with only the parameters you're changing (the
   apply script clones the input file, so unspecified parameters stay
   exactly the same).
4. **Apply** using `--template <in>` (the input is the template) and
   `--out <out>`.
5. **Never overwrite the input.** Always emit a new file.

## Cab section (mics)

The cab has two slots (`left*` / `right*`). You can shape it via the spec:

- **Mic selection** — set `leftMicType` / `rightMicType` **by name**, e.g.
  `{"module": "cabParameters", "key": "rightMicType", "value": "Ribbon 121"}`.
  The full catalog is `schema/mic_catalog.json` (10 internal mics: Dynamic
  57, Dynamic 57 Off-Axis, Dynamic 409, Dynamic 421, Condenser 184,
  Condenser 414, Condenser 4006, Condenser U47, Ribbon 121, Ribbon 160). An
  integer index also works. `show.py` prints the mic name for each slot.
- **Placement** — `*CabPosition` / `*CabDistance` (`fraction`, 0–1),
  `*CabMicLevel` (dB), `*CabPan` (enum), `*CabPhase` / `*CabActive` /
  `*RoomActive` (switches), `*RoomMicLevel` (dB).
- **Custom IR paths** — presets that use a third-party impulse response
  store it as an **absolute path** that only exists on the machine it was
  saved on. Cloning such a preset carries that dead path (and the original
  author's home directory) into your output. **Always pass `--strip-irs`**
  (or `"stripIRs": true` in the spec) unless you know the template is
  IR-free: it clears the paths so the preset falls back to the internal
  `*MicType` mics, making it portable on any machine. Verified to produce
  byte-identical encoding to an IR-free preset's empty field.
  `samples/Example_Clean_PR12.xml` is already IR-free, so `--strip-irs` is
  a harmless no-op there — pass it anyway out of habit.

## Safety / sanity checks

Before declaring success, always:
- Run `python -m pytest tests/test_roundtrip.py` to confirm the format
  layer still passes. If it doesn't, do NOT ship the generated preset.
- Run `show.py` on your output and confirm the new values appear.
- If the user asks you to set a parameter that isn't in
  `morgan_schema.json`, refuse and explain — the template-based writer
  cannot invent new parameter slots.

## Files you'll touch

- `samples/*.xml` — templates (read-only; never write here)
- `schema/morgan_schema.json` — the catalog (read-only at run-time;
  generated, not in the repo — see point 2 above)
- `knowledge/tone-references.md` — append-only; if you learn something
  useful while researching, add a note here for next time.
- New preset files — write to wherever `--out` points.
