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
BPM`, or `1/64T`. `scripts/audit_manifest.py` normalizes those before comparing
them with a manifest.

**A display is not a unit.** Both plugins show a pan as a position out of 50 —
`50 L` on Morgan, `L 50` on Tone King — but Morgan *stores* -50..50 and Tone
King stores -1..1. Reading the range off the display gave Tone King's pan a
range fifty times too large, and the cab recipes built on it hard-panned both
cabs while asking for a gentle spread. Every value still wrote, still
round-tripped, and still looked reasonable in the file.

Worse, when the audit flagged the resulting mismatch, the *checker* was changed
to parse `L 50` as -50 so that it would agree — the tool was bent to fit the
claim instead of the claim being questioned. `numeric()` now refuses a pan
display outright and the caller falls back to writing past each end and reading
back what the plugin kept, which measures the stored unit instead of inferring
it. Compare at float32 precision when you do: these parameters are 32-bit, so a
value written as `1.0` comes back as `0.99999994` and exact equality would
report a disagreement no edit could fix.

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

The map mode is adaptive. For each numeric key it tries up to four distinct
values, preferring values observed in installed presets, and reads both the
plugin-retained state and published controls after every attempt. Its statuses
have precise meanings:

- `mapped`: every effective write moves the same one published control
- `state_only`: the plugin retains an alternate value but no published control
  moves
- `rejected`: the plugin restores the baseline for every alternate
- `no_op`: none of the candidates differs effectively from the baseline
- `ambiguous`: effective writes move different or multiple controls
- `unsupported` / `inconclusive`: the experiment cannot establish a result

Tone King has 94 mapped keys, 158 state-only keys, and one rejected key
(`tempo`) in its saved-preset manifest. State-only and rejected keys are marked
read-only `internal`; they remain in the manifest so parsing and round-trip
inspection stay complete.

Tone King stores switches as binary doubles `0` and `1`. Morgan stores switch
values as the text strings `false` and `true`. The pack's `switch_encoding`
selects the correct writable representation.

### Interpret missing mappings conservatively

A single write that moves nothing proves little. Use adaptive candidates and
separate state retention from control movement. Only classify a key as
state-only when at least one alternate survives plugin readback while no
published parameter moves. Treat rejected, no-op, ambiguous, unsupported, and
inconclusive outcomes separately rather than collapsing them into “unmapped.”

Compare the mapped controls with the complete published parameter list before
declaring coverage. A selector or numeric control that remains unresolved stays
out of recipes until its write path and meaning are established.

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

Compare the retained values at float32 precision on both paths — `probe_bounds`
and `BoundsChecker.check` measure the same quantity and must agree about what
"the same" means.

For selectors, use the mapped control's indexed `valueStrings`. The index order
is the stored integer-to-label mapping. Morgan's delay and tremolo note tables
are separate: both are ordered by note duration, but their index offsets differ.

A `switch` is a two-index selector: the plugin publishes both of its labels in
the same `valueStrings` array (`Inactive`/`Active`, `Off`/`On`). Declare them as
`members` and the audit checks them like any other selector. Without them a
switch asserts nothing and nothing about it is tested.

**Writing every index is weaker evidence than reading `valueStrings`.** Writing
the index a control already holds moves nothing and produces no label, so the
baseline member goes unread. `audit_manifest.py` reports those selectors as
partly verified with a count (`20 of 21 declared members produced a label`)
rather than as verified. It is not a failure — the members that answered did
agree — but it is not a completed check either, and it is the same blind spot
that hid three wrong `*EQHpf` maximums through a full audit. Close it by
probing the remainder from a different starting value.

An undeclared selector should remain untouched by recipes. Out-of-range enum
values can be remapped silently rather than rejected.

### A published bound is not always a published number

Tone King publishes every continuous control with raw `minValue`/`maxValue` of
`0`/`1`, whatever the parameter stores: `Delay Time L` publishes `0..1` and
displays `100.00 .. 1100.00`. The raw pair is the normalized control range and
says nothing about the stored unit — only `minString`/`maxString` do, subject to
the pan caveat above. Three of its controls (`delayHPF`, `delayLPF`,
`reverbPreDelay`) publish empty display strings, and reading `0..1` off their
raw bounds would have been a guess that happened to be right for two of them.

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

For a record-state plugin, create a disposable preset with `apply_spec.py` and
pass the resulting state directly:

```bash
/tmp/au_render aumf TKI2 NDSP --state /tmp/toneking-test.xml \
  /tmp/toneking-test.wav 0.005
```

Do not publish audible conclusions from a silent render. Confirm a nonzero peak
first; some Audio Units require host behavior that the minimal offline helper
does not provide.

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
  `audit_manifest.py` reports `CANNOT VERIFY` when neither its XML mapper nor
  record-state mapper supports the state format.
- Plugin-dependent audits are deliberate local checks, not CI tests.
  `tests/test_audit_manifest.py` covers the comparison logic that does not need
  an installed plugin.

## Evidence rules

- A mapped key/control relationship is established by a state write that moves
  exactly one control.
- A numeric range needs a mapped control and endpoint evidence at **both** ends.
  A control sitting at one end by default cannot supply evidence for that end by
  write-and-read: nothing moves and the state keeps the out-of-range number.
  `reverbPreDelay` is the worked example — it stays undeclared for that reason.
- A selector table needs the mapped control's indexed labels or an equivalent
  write-and-read experiment covering **every** declared member.
- Audible direction needs deterministic rendering at more than one input level.
- An unresolved value stays undeclared, read-only, or marked `needs_review`.

`packs/loader.py` still rejects arithmetically impossible values through
`UNIT_FLOOR`, such as negative frequency or zero tempo, without treating those
generic constraints as plugin-specific ranges.
