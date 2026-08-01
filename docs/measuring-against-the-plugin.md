# Measuring against the plugin

This guide describes how to verify manifest facts against an installed Neural
DSP Audio Unit. Use it to establish parameter mappings, ranges, selector
members, switch directions, and audible behavior.

The committed results live in each pack:

- `manifest.json`: stored keys, kinds, units, ranges, selector members, and UI
  names
- `tone.md`: musical interpretation and usage guidance
- `recipes.json`: legal starting-point settings

Do not copy facts into those files from parameter names or a single preset.
Record the measurement in `range_source` or the parameter note.

## Requirements

- macOS
- the plugin installed, licensed, and able to open standalone
- Xcode command-line tools with a Swift compiler that matches the installed SDK
- Python 3.10 or newer

An unlicensed or unavailable Neural DSP Audio Unit normally fails to instantiate
with `-1`.

## Inspect the published Audio Unit parameters

An Audio Unit publishes control names, normalized bounds, display strings,
units, and discrete value labels. Inspect the component directly:

```bash
auval -v aumf NMAS NDSP
swiftc -swift-version 5 -O scripts/au_probe.swift -o /tmp/au_probe
/tmp/au_probe aumf NMAS NDSP params
```

Morgan Amps Suite uses component `aumf NMAS NDSP`. Tone King Imperial MKII uses
`aumf TKI2 NDSP`. The pack's `audio_unit` object is the authoritative component
identifier.

Display strings are the plugin's own formatting, such as `-24.0 dB`, `40.0
BPM`, `1/64T`, `50 L`, or `L 50`. `scripts/audit_manifest.py` normalizes these
forms before comparing them with a manifest.

## Map stored keys to controls

The parameter list alone does not establish which preset key controls which
Audio Unit parameter. Establish that relationship by changing one stored key,
loading the state, and observing the published control that moves.

### XML-state plugins

Morgan's `jucePluginState` contains an editable XML document whose attribute
names match its preset keys. Run the reverse map:

```bash
/tmp/au_probe aumf NMAS NDSP revmap
```

Probe selected values when a key needs closer inspection:

```bash
/tmp/au_probe aumf NMAS NDSP values delay/delaySyncNote 0,1,2,3
/tmp/au_probe aumf NMAS NDSP values parameters/outputGain -99,0,99
```

Each result includes the moved control, the label displayed by the plugin, and
the value retained in plugin state. Values beyond a numeric range reveal the
plugin's clamped endpoints.

Morgan currently maps 123 preset keys to exactly one published control.

### Preset-state plugins

Tone King's `jucePluginState` is the same binary `PARAM` record format as its
presets. The Python format layer edits the record and the Swift helper performs
Audio Unit state I/O:

```bash
python3 scripts/probe_state.py --pack toneking --map
python3 scripts/probe_state.py --pack toneking --values ampReverb 0,0.5,1
```

Tone King currently maps 94 of 255 numeric state keys to exactly one control.
Those mappings cover 94 of its 96 published controls; the other two are the
host-only Preset Previous and Preset Next actions.

Tone King stores switches as binary doubles `0` and `1`. Morgan stores switch
values as the text strings `false` and `true`. The pack's `switch_encoding`
selects the correct writable representation.

### Interpret missing mappings conservatively

A key is mapped only when the attempted value changes exactly one control. No
movement is inconclusive: the value may already be active, may be invalid for a
discrete parameter, or may be quantized into a no-op.

For an unreached key:

1. Try a known-valid alternate value from another real preset.
2. Try endpoints and interior values appropriate to the declared kind.
3. Compare the mapped control set with the complete published parameter list.
4. Keep the kind marked `needs_review` until the mapping is observed.

Do not describe an unreached key as having no Audio Unit control unless the UI
or another independent observation establishes that absence.

## Verify ranges and selector members

Run the pack audit:

```bash
python3 scripts/audit_manifest.py --pack morgan
python3 scripts/audit_manifest.py --pack toneking
```

The audit rebuilds the Swift helper, reads the parameter table, maps stored keys,
and checks declared facts. It exits nonzero when a declaration disagrees or
cannot be checked.

For numeric ranges, confirm both sources:

- the minimum and maximum display strings published by the mapped control
- values retained in state after writes below and above the declared endpoints

For selectors, use the mapped control's indexed `valueStrings`. The index order
is the stored integer-to-label mapping. Morgan's delay and tremolo note tables
are separate: both are ordered by note duration, but their index offsets differ.

An undeclared selector should remain untouched by recipes. Out-of-range enum
values can be remapped silently rather than rejected.

## Measure audible behavior

Parameter mapping identifies a control but does not establish what it does to
the sound. Render deterministic audio through the plugin:

```bash
swiftc -swift-version 5 -O scripts/au_render.swift -o /tmp/au_render
for level in 0.005 0.25; do
  /tmp/au_render aumf NMAS NDSP sw50rAmp/sw50rTrebleBoost false /tmp/off.wav $level
  /tmp/au_render aumf NMAS NDSP sw50rAmp/sw50rTrebleBoost true  /tmp/on.wav  $level
  python3 scripts/spectrum_diff.py /tmp/off.wav /tmp/on.wav
done
```

Use identical seeded input for both states. Repeat at widely separated input
levels: a spectral difference that persists across levels indicates filtering;
a difference that grows with level may be saturation. Ensure the amp that owns
the tested control is selected and active.

Current Morgan measurements:

| Control change | Measured effect |
|---|---|
| `sw50rTrebleBoost` off → on | −5.5 dB at 60 Hz; +2.5 dB from 400 Hz to 4 kHz |
| `sw50rBright` off → on | +5 dB at 2.5 kHz; +8 dB at 6.3 kHz; lows unchanged |
| `ac20BassTreble` off → on | −15.6 dB at 60 Hz; about −1 dB at 6.3 kHz |
| `ac20Cut` 0 → 100% | +11 dB at 2.5 kHz; +19 dB at 6.3 kHz |
| `sw50rMid` 0 → 100% | about +7.5 dB broadband; another +2 dB at 1.6–2.5 kHz |
| `sw50rTreble` 0 → 100% | −3.4 dB at 59 Hz; +7.2 dB at 2.5 kHz |
| `*CabPosition` 0 → 1 | +1.4 dB in the low mids; −1.1 dB at 6.3 kHz |

These figures establish direction and rough magnitude for preset decisions.
They are not full transfer functions.

## Measure distortion

Use a sine wave and measure harmonics added by the plugin:

```bash
/tmp/au_render aumf NMAS NDSP pr12Amp/pr12Volume 0.6 /tmp/v60.wav 0.05 sine:222.65625
python3 scripts/spectrum_diff.py --thd 222.65625 /tmp/v60.wav
```

The test frequency must lie on an analysis-bin center. With a 4096-point window
at 48 kHz, bins are 11.71875 Hz apart. `spectrum_diff.py` rejects an off-center
fundamental and reports the nearest valid value.

Distortion depends on both the control position and input level. For PR12,
approximately 5% distortion occurs around 66% volume at the reference input and
around 28% when the input is three times stronger. Treat breakup positions as
input-dependent ranges, and check rendered peak level so output clipping is not
misidentified as plugin distortion.

## Method limits

- Audio Unit metadata covers only published controls.
- Controls with no display strings require state writes, UI inspection, or
  audio measurement.
- Spectral results depend on the excitation, operating point, and nonlinear
  state of the model.
- The state-mapping method requires a decoded, editable state representation.
  `audit_manifest.py` reports `CANNOT VERIFY` for unsupported state formats.
- Plugin-dependent audits are deliberate local checks, not CI tests.
  `tests/test_audit_manifest.py` covers the comparison logic that does not need
  an installed plugin.

## Evidence rules

- A mapped key/control relationship is established by a state write that moves
  exactly one control.
- A numeric range needs a mapped control and endpoint evidence.
- A selector table needs the mapped control's indexed labels or an equivalent
  write-and-read experiment.
- Audible direction needs deterministic rendering at more than one input level.
- An unverified value stays undeclared or marked `needs_review`.

`packs/loader.py` still rejects arithmetically impossible values through
`UNIT_FLOOR`, such as negative frequency or zero tempo, without treating those
generic constraints as plugin-specific ranges.
