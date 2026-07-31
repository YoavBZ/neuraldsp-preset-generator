# Open questions

What the manifest does **not** know, why, and exactly how to close each gap.

Everything here needs the plugin running on a machine with a screen and audio
output. No amount of static analysis substitutes — these are measurements, not
deductions. Until they land, the affected values are written unchecked or with a
warning, which is why they are tracked here rather than left implicit.

Close one, delete its section, and update the corresponding test.

---

## 1. Eight metered parameters have no declared range

`UNIT_FLOOR` in `packs/loader.py` rejects values that are impossible in the unit
(a negative frequency, a zero tempo). It says nothing about the plugin's actual
limits, so `outputGain 1e6` still writes. The set is pinned in
`tests/test_pack.py::UNDECLARED_RANGES` — shrinking it is the goal.

| parameter | unit | value in `samples/Example_Clean_PR12.xml` |
|---|---|---|
| `parameters/inputGain` | dB | `0.0` |
| `parameters/outputGain` | dB | `5.0` |
| `parameters/gateThreshold` | dB | `-72.0` |
| `delay/delayTempo` | BPM | `120.0` |
| `cabParameters/leftCabMicLevel` | dB | `0.0` |
| `cabParameters/leftRoomMicLevel` | dB | `-6.0` |
| `cabParameters/rightCabMicLevel` | dB | `5.0` |
| `cabParameters/rightRoomMicLevel` | dB | `-6.0` |

### How to measure

**Option A — read the UI.** Load the example preset (the on-screen numbers
should match the table above, which confirms you have the right control), drag
each control to each extreme, note both numbers.

**Option B — let the plugin answer in writing.** Same inversion `probe.py` uses:
write a preset carrying an absurd value, load it, re-save it. The plugin clamps
to its real limit and stores that number, which can then be read straight out of
the binary — no transcription step, and it catches limits the UI rounds off.

> **Turn your monitoring volume down before loading the gain probes.** A gain
> stage clamped to its maximum is exactly as loud as that sounds.

Record the result as `min`/`max` on the parameter in `packs/morgan/manifest.json`
with a `range_source` saying how it was obtained, then delete the entry from
`UNDECLARED_RANGES`. `test_every_other_metered_parameter_has_a_sourced_range`
enforces the source.

---

## 2. Three switches whose direction is unverified

The stored key names are the plugin authors' own labels, so they are decent
evidence — but `docs/morgan-config-reference.md` contradicts one of them, and a
switch documented backwards sends every recipe that touches it the wrong way.

| parameter | claim to verify | value in the example |
|---|---|---|
| `sw50rAmp/sw50rTrebleBoost` | ON = brighter, **not** thicker | `true` |
| `sw50rAmp/sw50rInputMode` | which state is the bright channel | `false` |
| `ac20Amp/ac20BassTreble` | ON = fuller mids, more AC30-like | `true` |

`sw50rTrebleBoost` is the one that matters. The config reference calls it
`bassEmphasis` and advises it for a thicker lead — the opposite direction. If the
reference is right, the lead recipes are inverted.

### How to measure

Load the example preset, set `selectedAmp` to the relevant amp, flip the switch,
listen. One sentence per switch settles it. Update the parameter's `note` in the
manifest with what was heard.

---

## 3. Six selectors have no member names

The plugin displays a selector's **label** but never the integer stored in the
file, so the mapping cannot be read off the screen. Writing these still works,
with a warning that the value is unverified.

- `delay/delaySyncNote`
- `delay/delaySync`
- `tremolo/tremoloSyncNote`
- `ac20Amp/ac20Power`
- `cabParameters/leftCabPan`
- `cabParameters/rightCabPan`

Musical timing does **not** depend on this: `packs/timing.py` converts a note
division to milliseconds or Hz, so a dotted-eighth delay is reachable through
`delayTime` with no selector involved. That is why this sits below the ranges in
priority.

### How to measure

**Cheap:** selectors are index-based — confirmed for the mic catalog, which
resolves correctly against the shared `enums` block. So the control's options,
read top to bottom in order, *are* the table. Write them as `members` and confirm
the whole thing with a single probe.

**Empirical:** `probe.py` writes disposable presets named after the value they
carry, so the plugin's own browser labels them:

```bash
python scripts/probe.py --param delay/delaySyncNote --values 0-15 \
  --out-dir ~/Library/Audio/Presets/Neural\ DSP/Morgan\ Amps\ Suite/User
```

Load `probe delaySyncNote 07`, read the control, and you have learned what 7
means — reading labels only, never integers. Delete them afterwards.

See [reference/selectors-and-timing.md](../reference/selectors-and-timing.md).

---

## 4. No pack has been bootstrapped from a second plugin

`scripts/bootstrap_pack.py` drafts a pack from one preset of an unknown plugin,
and the format layer is meant to be plugin-agnostic. Neither claim has been
tested against a format nobody curated by hand.

### How to test

Save a preset from any other Neural DSP plugin at its factory defaults, then:

```bash
python scripts/bootstrap_pack.py --preset ~/path/to/ThatPreset.xml \
  --display-name "Archetype Gojira"
```

A failure here is more informative than a success — it is the only evidence
available about whether the parser generalises.

**Do not commit the source preset.** It is Neural DSP's factory content; the
generated manifest is parameter names and guessed kinds, and is fine to keep. See
[NOTICE.md](../NOTICE.md).

---

## Why these are not guesses in the meantime

A declared range with no source is indistinguishable from a measured one once
it is in the file, and it would silently overrule the user. Leaving the value
undeclared is honest about what is known; `UNIT_FLOOR` catches the arithmetically
impossible without pretending to know the plugin's limits.
