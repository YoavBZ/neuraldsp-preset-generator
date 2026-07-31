# Measuring against the plugin

Every range, selector table and switch direction in `packs/morgan/manifest.json`
that cites this file was read off Morgan Amps Suite while it was running. This
is the procedure, so the numbers can be re-derived rather than trusted.

None of it involves reading the UI or listening. Both were the plan of record in
`docs/open-questions.md`; both turned out to be unnecessary, and the UI would
have been the weaker source — it rounds, and it never shows the integer a
selector stores.

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
it to. Two independent measurements agreeing. This also caught four ranges that
were already declared and wrong — the three `*EQLpf` minimums (1 kHz, not 20 Hz)
and `tremoloRate` (0.15–15 Hz, not 0.05–5).

**Selector tables.** Write each index, read the label the plugin shows. The
sync-note tables are ordered by note *duration*, not grouped by kind, which is
why the indices look shuffled — and why delay's table and tremolo's are offset
by two rather than identical.

**Switch directions.** The stored key name is not evidence; the control it moves
is. `sw50rTrebleBoost` moves the control Morgan publishes as **SW50R Bass
Emphasis** — the opposite of what the manifest claimed, and SW50R has a separate
`sw50rBright` for actual brightness.

**Out-of-range selector values are silent.** Writing 19 to `tremoloSyncNote`
(valid: 0–18) does not fail and does not clamp to the top — the plugin stores 9.
An undeclared selector is not a harmless unknown.

## Limits of the method

- It reads what the plugin *publishes*. Two controls publish no strings at all
  (`R3`, `R6` — the room mic selectors), so their member names still need
  `scripts/probe.py` and a human reading the preset browser.
- It says nothing about how anything **sounds**. "Bass Emphasis" is the
  control's name, not a measurement of its curve.
- macOS only, and it needs the plugin licensed and installed. Unlicensed Neural
  DSP plugins fail to instantiate with `-1`.
