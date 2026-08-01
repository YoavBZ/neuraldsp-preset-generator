# Measuring against the plugin

Every range, selector table and switch direction in `packs/morgan/manifest.json`
that cites this file was read off Morgan Amps Suite while it was running. This
is the procedure, so the numbers can be re-derived rather than trusted.

Reading the UI and listening were the plan of record. Neither was needed for the
ranges, the selector tables, or identifying which control a key moves — and the
UI would have been the weaker source for those, since it rounds and never shows
the integer a selector stores. The UI is still the only way to see that a
parameter has no control at all, and rendering audio is the only way to learn
which way a control moves the sound. Both are used below.

## The two things the plugin will tell you

An Audio Unit publishes a parameter list, and Morgan fills it in properly:

```bash
auval -v aumf NMAS NDSP
```

For every one of its 128 controls that prints a name, a type, and the minimum,
default and maximum **as the plugin formats them** — `-24.0 dB`, `40.0 BPM`,
`1/64T`. That is the range, in the unit, from the plugin itself.

Second, the plugin's state is readable and writable. `AUAudioUnit.fullState`
carries a `jucePluginState` blob:

```
"VC2!" <uint32 length> <?xml … ?><appModel selectedAmp="0" …>
```

The document inside uses **exactly the key names a saved preset uses**
(`sw50rTrebleBoost`, `leftCabPan`). So state can be edited and handed back, and
the plugin's response read out — which is what turns a name into a measurement.

`scripts/au_probe.swift` does both. Build and run it:

```bash
swiftc -swift-version 5 -O scripts/au_probe.swift -o /tmp/au_probe
/tmp/au_probe aumf NMAS NDSP params
```

## Why writing beats reading

The obvious experiment — move a control, see which key changes — **does not
work**. Setting a parameter through the AU parameter tree does not reach the
plugin's own state until it processes audio, so the document comes back
unchanged for all 128 controls.

Run it backwards instead. Write a value into the document, hand it to the
plugin, and see which published control moved:

```bash
/tmp/au_probe aumf NMAS NDSP revmap        # every key, one at a time
```

This is the better experiment anyway, because it exercises the exact path a
generated preset takes: *this key, written to a file, moves that control*. It
maps 123 preset keys to exactly one control each, with no ambiguity to resolve.

For one key at a time, with chosen values:

```bash
/tmp/au_probe aumf NMAS NDSP values delay/delaySyncNote 0,1,2,3
/tmp/au_probe aumf NMAS NDSP values parameters/outputGain -99,0,99
```

Each result reports three things: the control that moved, the label the plugin
shows for it, and **the value the plugin kept in its state**. The last one is
where limits appear — write 99 to `outputGain` and the plugin stores 24.

## What this settled

**Ranges.** Read from the published parameter info, then confirmed from the
other side by writing an absurd value and reading back what the plugin clamped
it to. Two independent measurements agreeing. This also caught **seven** ranges
that were already declared and wrong: the three `*EQLpf` minimums (1 kHz, not
20 Hz), the three `*EQHpf` maximums (500 Hz, not 20 kHz), and `tremoloRate`
(0.15–15 Hz, not 0.05–5).

The high-pass trio nearly escaped, and how is worth recording. `revmap` only
maps a parameter whose probe value actually **moves** the control; those three
already sat at their minimum in the plugin's default state, so writing a low
value changed nothing, no control moved, and they were quietly absent from the
audit table rather than flagged. **A parameter missing from the map is not a
parameter that passed.** Diff the mapped set against the manifest and probe the
remainder by hand.

**Selector tables.** Write each index, read the label the plugin shows. The
sync-note tables are ordered by note *duration*, not grouped by kind, which is
why the indices look shuffled — and why delay's table and tremolo's are offset
by two rather than identical.

**Switch directions.** Which control a key moves — see below for what that
control then does to the sound, which is not the same question.
`sw50rTrebleBoost` moves the control Morgan publishes as **SW50R Bass
Emphasis**, and SW50R has a separate `sw50rBright` for actual brightness.

**Out-of-range selector values are silent, and not consistently so.** Writing 19
to `tremoloSyncNote` (valid: 0–18) neither fails nor clamps to the top — the
plugin stores 9. Writing 3 to a room mic selector (valid: 0–2) stores 0. Two
controls, two different behaviours, one observation each: assume neither rule
generalises, and declare the members. An undeclared selector is not a harmless
unknown.

## Measuring what a control does to the sound

Everything above identifies controls. It says nothing about what they *do* —
and on this plugin, the names actively mislead.

`scripts/au_render.swift` renders audio through the plugin offline; nothing
reaches an output device. `scripts/spectrum_diff.py` compares two renders band
by band, using Goertzel rather than an FFT so it runs on a stock Python.

```bash
swiftc -swift-version 5 -O scripts/au_render.swift -o /tmp/au_render
for level in 0.005 0.25; do
  /tmp/au_render aumf NMAS NDSP sw50rAmp/sw50rTrebleBoost false /tmp/off.wav $level
  /tmp/au_render aumf NMAS NDSP sw50rAmp/sw50rTrebleBoost true  /tmp/on.wav  $level
  python3 scripts/spectrum_diff.py /tmp/off.wav /tmp/on.wav
done
```

Both levels, every time — that is what the second bullet below means in
practice. The reported frequencies are the analyser's actual bin centres, which
land within a few percent of the round numbers quoted in this repo's notes.

Three things make the result trustworthy, and all three were needed:

- **Seed the noise.** Both states must see byte-identical input, or you are
  comparing two noise realisations and small differences mean nothing.
- **Run it at two levels far apart.** This is a non-linear amp model. A
  difference that survives a 50× change in input level is a filter; one that
  only appears when loud is the amp saturating.
- **Select the amp that owns the control.** The first `ac20BassTreble` run
  returned a difference of exactly `0.00 dB` in every band, because the harness
  had left SW50R live and the AC20's switch was out of circuit. An exact zero is
  a useful signal: it means the control was not in the path at all.

| switch | ON does | so |
|---|---|---|
| `sw50rTrebleBoost` | −5.5 dB @ 60 Hz, +2.5 dB @ 400 Hz–4 kHz | brighter, tighter |
| `sw50rBright` | +5 dB @ 2.5 kHz, +8 dB @ 6.3 kHz | air, lows untouched |
| `ac20BassTreble` | −15.6 dB @ 60 Hz, −1 dB @ 6.3 kHz | a big bass cut |
| `ac20Cut` 0→100% | +11 dB @ 2.5 kHz, +19 dB @ 6.3 kHz | presence, **not** a cut |

**The name is a hypothesis, not evidence — including the plugin's own.** Two
cases, both of which this repo got wrong by reasoning:

- `sw50rTrebleBoost` moves a control published as *Bass Emphasis*. The names
  contradict each other; this repo picked the plugin's as the more authoritative
  and documented the switch as thickening the low end. It does the opposite.
- `ac20Cut` was "settled by reasoning" and stated in capitals as *higher =
  darker*, on the strength of three sources that agreed: the config reference,
  the control's name, and Morgan's description of the Vox circuit it is named
  after. Higher is **brighter**. Three agreeing arguments were three
  restatements of one name.

Agreement between name-based arguments is not corroboration. Render the audio.

## Limits of the method

- It reads what the plugin *publishes*. Two controls publish no strings at all
  (`R3`, `R6` — the room mic selectors), so nothing here can name their options.
  They also have no control anywhere in the UI, so there is nothing to read.
- The spectral numbers are one measurement of a non-linear system with one
  excitation. They are solid on **direction and rough magnitude**, which is what
  a tone decision needs; they are not a datasheet frequency response.
- macOS only, and it needs the plugin licensed and installed. Unlicensed Neural
  DSP plugins fail to instantiate with `-1`.

## Why an undeclared range beats a guessed one

Every metered parameter in the Morgan pack now has a measured range, so this is
a rule for the next pack rather than a description of this one.

A declared range with no source is indistinguishable from a measured one once it
is in the file, and it would silently overrule the user. Leaving the value
undeclared is honest about what is known; `UNIT_FLOOR` in `packs/loader.py`
catches the arithmetically impossible — a negative frequency, a zero tempo —
without pretending to know the plugin's limits.

That seven already-declared ranges turned out to be wrong — `tremoloRate` sourced
to the config reference, the `*EQLpf` and `*EQHpf` bounds to `observed-endpoints` — is the
argument for this rule rather than against it. A range is only as good as where
it came from, which is why `range_source` is required and why
`test_every_other_metered_parameter_has_a_sourced_range` enforces it.
