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

## What a render costs

Measuring one control takes two renders. Matching a preset against a recording
would take hundreds, so the cost of a render decides what is affordable.
`--timings` breaks one down and writes the phases to stderr as JSON:

```bash
/tmp/au_render aumf NMAS NDSP sw50rAmp/sw50rBright true /tmp/on.wav 0.25 --timings
```

| Phase | Morgan, 2 s of audio |
|---|---|
| process spawn and Swift runtime start | 55 ms |
| `AUAudioUnit.instantiate` | 1250 ms |
| build the edited state document | 2 ms |
| write `fullState` | 176 ms |
| settle | 205 ms |
| set formats, `allocateRenderResources` | 5–17 ms |
| generate the excitation | 0.4 ms |
| `renderBlock`, all 188 blocks | 306 ms |
| write and close the wav | 4 ms |
| **wall clock** | **2030 ms** |

The plugin spends 306 ms processing audio and the harness spends the other
1.7 seconds getting to the point where it can — 5.6 times the cost of the work
itself, and instantiating is 62% of a render on its own. Two renders per amp per
control is fine at this price. A search is not.

### The 200 ms settle is not needed

The `usleep(200000)` after writing state was a guess, and `--settle` measures
it. The same state rendered at 0, 5, 10, 25, 50, 100, 200 and 400 ms produces
**byte-identical output at every value** — for a switch, and for a mic change
that reloads an impulse response:

```bash
for ms in 0 5 10 25 50 100 200 400; do
  /tmp/au_render aumf NMAS NDSP sw50rAmp/sw50rBright true /tmp/s_$ms.wav 0.25 --settle $ms
  /tmp/au_render aumf NMAS NDSP cabParameters/leftMicType 5 /tmp/m_$ms.wav 0.25 --settle $ms
done
shasum -a 256 /tmp/s_*.wav   # one hash for all eight
shasum -a 256 /tmp/m_*.wav   # one hash for all eight, different from the above
```

Writing `fullState` costs 176 ms and evidently does the work synchronously. The
default stays at 200 ms, because every measurement above was made with it and
0.2 s is nothing in a one-shot run; anything rendering in bulk should pass
`--settle 0`. Measured on Morgan's XML state path only.

## Render many parameter sets from one instance

`scripts/au_render_server.swift` pays the instantiate once. It allocates once,
then reads render commands as JSON lines on stdin and answers with the peak and
its own timings:

```bash
swiftc -swift-version 5 -O scripts/au_render_server.swift -o /tmp/au_render_server
printf '%s\n' \
  '{"out":"/tmp/a.wav","edits":[{"module":"sw50rAmp","key":"sw50rBright","value":"true"}],"selectAmp":2,"gateOff":true,"amplitude":0.25}' \
  '{"quit":true}' | /tmp/au_render_server aumf NMAS NDSP
```

| | renders/s | per render |
|---|---|---|
| `au_render`, one process per render | 0.50 | 2030 ms |
| `au_render_server`, 20 renders in one process | 2.67 | 375 ms |
| `au_render_server`, steady state after the first | 3.4 | 291 ms |
| four servers in parallel (6 performance cores) | 8.8 | — |

Every command re-edits the state the plugin had at startup, so a sequence of
renders does not depend on the order it was asked for. `edits` writes attributes
in the live XML state; `state` replaces the whole blob, which is what a
record-state plugin needs.

Both harnesses also take `--input` / `"input"`, a 48 kHz mono or stereo file
rendered in place of the generated excitation, with the amplitude argument
applied to it as a linear gain. Measuring a control still wants noise or a sine
— a recording only excites the frequencies it happens to contain — but a preset
can only be judged against a guitar.

### A second render in one instance is not the first

Renders from a **fresh process are exactly reproducible**: two processes, same
arguments, byte-identical wav files. That is what the measurements above rest
on, and it still holds.

Renders after the first **in the same instance are not**. Five identical
commands to one server produce five different files, differing from each other
by about −17 dB relative to the signal, correlated at 0.99, with no time offset
between them. None of the obvious explanations survives:

| Tried | Result |
|---|---|
| `reset()` before each render | no change |
| `deallocateRenderResources` and allocate again | no change |
| writing state to a deallocated instance, as the one-shot does (`"isolate"`) | no change |
| rendering and discarding 0.5, 1, 2, 4, 8 s first (`"warmup"`) | −17 to −26 dB, not converging |
| silence in instead of noise | silence out, so nothing is being *added* |

It is the plugin, not the harness: `pedalboard` renders Morgan with the same
−17.4 dB spread across repeats with `reset=True`. The variation is
signal-dependent internal state that only a new instance clears.

What it costs in practice is small, because these are broadband waveform
differences and not tonal ones. Across five repeats, third-octave band levels
move by at most:

| | 63 | 125 | 250 | 500 | 1k | 2k | 4k | 8k | 16k |
|---|---|---|---|---|---|---|---|---|---|
| one process per render | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| one instance, repeated | 0.20 | 0.08 | 0.23 | 0.18 | 0.10 | 0.23 | 0.19 | 0.16 | 0.20 |
| one instance, `"isolate"` | 0.02 | 0.08 | 0.16 | 0.07 | 0.06 | 0.06 | 0.03 | 0.00 | 0.00 |

against 1–5 dB for the control changes tabulated above. So: **measure published
facts one process per render**, where the answer is exact and repeatable, and
use the server where hundreds of renders matter more than the last 0.2 dB.
Anything reading a difference smaller than about 0.5 dB out of a reused instance
is reading its own noise.

## Hosting the plugin in-process

`scripts/spike_pedalboard.py` renders through `pedalboard`, which embeds a JUCE
host. It needs the `host` extra and, like everything else here, an installed and
licensed plugin:

```bash
pip install -e '.[host]'
python scripts/spike_pedalboard.py --plugin "Morgan Amps Suite" --bench 10
```

```
loaded 'Morgan Amps Suite' in 1876 ms
published parameters: 128   raw state: 5449 bytes
render: 229 ms for 2.0 s of audio, peak 0.5653260
bench: 10 renders, 232 ms each, 4.31 renders/s
```

Abridged: the script also prints the peak spread across the bench and whether
every render was bit-identical, which is how the non-reproducibility below was
found. The lines above are the throughput ones.

232 ms against the Swift server's 291 ms, with no wav round-trip and no
subprocess, and parameters arrive named, typed, and carrying their ranges and
display units instead of as attributes to be edited by regular expression.

### Driving it from a generated preset, and what has not been run yet

Renders above use the plugin's default state, which proves throughput and not
that the backend can be driven by a parameter vector. `--state` applies a file
as raw state, reads it back, and reports which parameters the plugin kept:

```bash
python scripts/spike_pedalboard.py --plugin "Tone King Imperial MKII" \
  --state /tmp/generated.xml
```

Two things make that less obvious than it sounds, and the script now enforces
both.

A preset file is a state blob **only for a record-state plugin**. Tone King keeps
the same `PARAM` record format in its presets and in its `jucePluginState`, so a
generated preset is a legal state document for it. Morgan does not: its state is
an XML document and its presets are the `morgan\0` record format, and nothing
converts between them — see the section below. Handing a Morgan preset to
`raw_state` raises nothing and changes nothing, so the render would be of the
default preset and reported as the generated one. The encoding is checked before
the write and the mismatch is refused.

And applying state without an error is not evidence that it was applied. The
values are read back and compared, for the same reason the pan range needed
writing past each end rather than reading the display: this repository has
already been wrong once about a write it did not verify.

**Not yet run against a plugin.** The comparison logic is tested without one
(`tests/test_spike_pedalboard.py`), but the round trip itself needs macOS and a
licence, and M5 depends on it. Until someone runs it, treat "the backend can be
driven by a generated preset" as untested for Tone King and as *impossible by
this path* for Morgan.

The two hosts agree. Fed byte-identical noise — the spike reimplements the
harness's seeded xorshift exactly — and the same default state, they differ by
**0.12 dB at worst in any third-octave band**. The waveforms correlate at 0.991
once a **57-sample (1.19 ms) offset** between them is removed, and what remains
is −17.8 dB: the same per-render variation the plugin shows against itself. A
render is portable between the two backends; a *sample-aligned* comparison
between them is not free.

## Tone King produces no audio in the Swift helpers

`scripts/au_render.swift` gets audio out of Morgan and **exact zeros** out of
Tone King Imperial MKII. So no acoustic work exists for that plugin — no switch
directions, no break-up curves, and not the EQ band ordering three of its
recipes assume. Those recipes say so rather than guessing.

`scripts/au_silence_check.swift` is the evidence, and it is deliberately
separate from the render harness so the harness cannot be the variable. It sets
no state, edits no document, touches no parameter: it instantiates, feeds noise
through the v2 `AudioUnitRender` path that `auval` uses, and reports the peak.

```bash
swiftc -swift-version 5 -O scripts/au_silence_check.swift -o /tmp/silence
/tmp/silence aumf NMAS NDSP     # Morgan    -> peak = 0.5546125
/tmp/silence aumf TKI2 NDSP     # Tone King -> peak = 0.0
```

Same code, same process, same input: one plugin makes sound and the other makes
none. It also prints bypass and latency (both 0 for both plugins), which
removes the two properties that would otherwise be the obvious explanation.

Beyond what that script reproduces, the silence also survived every variation
tried against the render harness: input amplitudes from 0.005 to 0.9, the AUv3
`renderBlock` path as well as the v2 one, mono and stereo stream formats, and
with and without a state blob applied. Those runs used throwaway instrumentation
rather than committed code — take them as weaker than the script above, which is
why the script exists.

`auval -v aumf TKI2 NDSP` passes, but that is weaker evidence than it looks: it
checks for NaNs and malformed output, not for non-silence.

**Do not read the silence as a measurement.** A control that appears to do
nothing here has not been shown to do nothing.

### It does produce audio in a JUCE host

`pedalboard` loads Audio Units the way a DAW does rather than instantiating one
from a headless CLI, and Tone King renders through it:

```bash
pip install -e '.[host]'
python scripts/spike_pedalboard.py --plugin "Tone King Imperial MKII" --bench 5
```

```
loaded 'Tone King Imperial MKII' in 4512 ms
published parameters: 96   raw state: 12741 bytes
render: 783 ms for 2.0 s of audio, peak 0.1640197
```

It is really processing, not passing through. Against the same white noise the
Swift helper uses, its output shows an amp-and-cab response — −26.6 dB at 8 kHz
and −51.5 dB at 16 kHz — and moving `rhythm_channel_treble` from 0.0 to 1.0
tilts the spectrum by about 2 dB across the mids.

The control that makes this worth anything: `au_silence_check` was re-run on the
same machine in the same session and still reports **peak = 0.0** for Tone King
and **0.5546125** for Morgan — the identical numbers recorded above. So the
silence is a property of the bare CLI instantiation, and **authorization is
ruled out**: a plugin that could not authorize would be silent in both hosts.

That unblocks acoustic work on Tone King, through that host, at a price — but
**the size of that price is unresolved and needs re-measuring.** The two figures
recorded from that session disagree, and not in the direction warm-up would
explain: the single render above took 783 ms, which is 1.28 renders/s, while the
`--bench 5` steady state was written down as about 0.38 renders/s. A steady state
slower than the first render is not something a warm cache does, so one of the two
is wrong and the notes do not say which. Treat "roughly eleven times Morgan's cost"
as the loose upper bound it is, and re-run `--bench` before any budget depends on
it.

Nothing in `packs/toneking/` has been measured acoustically yet. Its recipes
still say so, and they should keep saying so until someone actually renders the
comparisons — what changed is that this is now possible, not that it is done.

### Corrected in M5: it is the first allocation, not the instantiation

The conclusion above — "the silence is a property of the bare CLI instantiation"
— is wrong, and `pedalboard` was never needed to get audio out of this plugin.

Tone King renders silence on its **first allocation of render resources**, and
renders normally once they have been deallocated and reallocated. Both orderings
work, so the state write has nothing to do with it:

```bash
swiftc -swift-version 5 -O scripts/au_render_server.swift -o /tmp/au_render_server
python3 - <<'EOF'
import json, subprocess
import numpy as np, soundfile as sf
from tests import fixtures_audio as fx
sf.write('/tmp/tkdi.wav',
         np.asarray(fx.plucks(seconds=2.0, gap=0.9, seed=13), dtype=np.float32)[:, None],
         48000, subtype='FLOAT')
def run(**extra):
    cmd = dict(out='/tmp/tko.wav', input='/tmp/tkdi.wav', amplitude=1.0); cmd.update(extra)
    p = subprocess.run(['/tmp/au_render_server', 'aumf', 'TKI2', 'NDSP', '--settle', '0'],
                       input=json.dumps(cmd) + '\n{"quit":true}\n',
                       capture_output=True, text=True)
    return [json.loads(l) for l in p.stdout.strip().splitlines() if l.startswith('{')][-1]['peak']
print('plain  ', run())
print('realloc', run(realloc=True))
print('isolate', run(isolate=True))
EOF
```

```
plain   0.0
realloc 0.1525246
isolate 0.1525423
```

That is also why `au_silence_check.swift` still reports `peak = 0.0`: it
instantiates, allocates once and renders, which is exactly the path that is
silent. It remains correct evidence about that path and was never evidence about
the plugin.

The cost is one render of about 46 s while the plugin loads its impulse
responses, and 370 ms per render after that — Morgan's cost. `match/renderer_au.py`
turns this on by itself: if a first render comes back silent it restarts the
server with the resources cycled and tries once more, which is load-bearing,
because retrying inside the same instance stays silent.

Acoustic work on Tone King is therefore possible from the Swift harness, and
parameter writes measurably move the sound — `/rhythmAmpVolume`, `/cab1Level` and
`/ampReverb` each move a third-octave band by 11 to 13 dB. The recipes still say
nothing has been measured, and that is still true.

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
  It is not the only control sitting at an end of its range, though: `ampReverb`,
  `wahPosition` and `chorusMix` do too, and writing past that end is retained
  verbatim there as well. Their ranges stand because the plugin publishes a
  display string for them as a second source. One unmeasurable end is only fatal
  when nothing else covers it.
- A selector table needs the mapped control's indexed labels or an equivalent
  write-and-read experiment covering **every** declared member.
- Audible direction needs deterministic rendering at more than one input level.
- An unresolved value stays undeclared, read-only, or marked `needs_review`.

`packs/loader.py` still rejects arithmetically impossible values through
`UNIT_FLOOR`, such as negative frequency or zero tempo, without treating those
generic constraints as plugin-specific ranges.
