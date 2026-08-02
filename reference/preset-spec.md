# Writing and applying a preset spec

Shared reference for the `generate` and `edit` skills.

## How writing works

The preset file is binary despite its `.xml` extension, and has no public
spec. So the writer **clones a known-good preset and mutates only the values of
parameters it already contains**. Wrapper bytes are preserved verbatim. A text
value's one length byte is recomputed; a binary value is re-encoded in place at
its fixed width. Both encodings are described under
[The second preset encoding](#the-second-preset-encoding).

Consequences you must design around:

- **A template is always required.** You cannot synthesise a preset from nothing.
- **You cannot add parameters.** If a key isn't already in the template, the
  tool refuses. It cannot invent a parameter slot.
- **Never edit the binary by hand.** Always go through the scripts below.

## The value convention

The plugin's knobs have no numbers on them — a knob is just a rotation. So:

| kind       | you write                   | example                          |
|------------|-----------------------------|----------------------------------|
| `rotation` | percent **0–100** (noon=50) | `62` → knob at ~2 o'clock        |
| `fraction` | decimal **0.0–1.0**         | `0.30` (cab position/distance)   |
| `metered`  | the **native unit**         | `-65` dB, `480` ms, `5000` Hz    |
| `switch`   | `true` / `false`, or its label | `true`, `"Active"`, `"Off"`   |
| `enum`     | integer **or member name**  | `"PR12"`, `"Ribbon 121"`, `2`    |
| `string`   | text, written verbatim      | a preset name                    |
| `path`     | absolute path, verbatim     | a custom IR file                 |
| `internal` | nothing; always read-only   | retained state with no writable control |

`metered` units: **dB** (gate, input/output, mic levels, EQ bands), **Hz**
(HPF/LPF/cuts, tremolo rate), **ms** (delay time, pre-delay, doubler spread),
**seconds** (reverb decay), **BPM** (tempo), **semitones** (transpose).

Prefer **member names over integers** for selectors — `"value": "SW50R"` reads
better than `"value": 2` and is checked against the manifest. A `switch` may
also declare the two labels the plugin publishes for it (Tone King's do:
`Inactive`/`Active`, `Off`/`On`); where it does, either the label or a plain
boolean is accepted, and the audit re-derives the labels from the plugin.

An `internal` entry remains in the manifest so a preset can be inspected and
round-tripped without dropping state. It is never a generation target:
`apply_spec.py` rejects writes to it before value translation.

Two selectors have no member names — `leftRoomMicType` and `rightRoomMicType`,
which the plugin neither labels nor exposes a control for. Everything else,
including both sync-note tables, can be set by name. For musical delay and
tremolo you still don't need the selector — compute milliseconds or Hz instead.
See [selectors-and-timing.md](selectors-and-timing.md).

## Where the facts live

- `packs/<id>/manifest.json` — **the contract.** Committed and hand-curated:
  every parameter's kind, unit, declared range, selector members, UI name.
  This is what values are *legal*. Consult it before choosing a value.
- `packs/<id>/observed.json` — **advisory, optional, local.** Generated from
  the user's own presets by `python scripts/build_observed.py`. This is what
  values are *typical* — a taste anchor, never a limit. Absent on a fresh
  clone; nothing breaks without it.
- `packs/<id>/recipes.json` — **composable starting points.** Committed. Tone
  recipes grouped by layer (amp, compressor, drive1, drive2, tremolo, eq, cab,
  delay, reverb, output). Stack one per layer, then adapt.
- `packs/<id>/tone.md` — the decision layer: amps and their character, an
  intent → recipe-stack table, and the "when the user says X" vocabulary.

### Stacking recipes

Pass them to the writer directly — don't hand-assemble them:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/apply_spec.py" \
  --template TEMPLATE.xml \
  --recipe amp/sw50r-singing-lead --recipe compressor/lead-smoothing \
  --recipe eq/lead-focus --recipe delay/classic-lead \
  --bpm 96 --out OUT.xml --dry-run
```

`--recipe` is repeatable and order matters: later recipes win, and a `--spec` is
applied last so your own values always override a recipe default. Combine both
freely — recipes for the starting point, a spec for what the song actually needs.

Two things the writer handles for you, which you must not do by hand:

- **`{amp}` resolution.** EQ recipes target `{amp}EQ`; the writer substitutes the
  amp the stack selects (or the template's current one). The graphic EQ is
  per-amp, so an EQ recipe on the wrong amp does nothing audible.
- **Note divisions.** A recipe value of `{"note": "1/4"}` becomes milliseconds
  once `--bpm` is known. A hand-written spec can also carry its own
  `{"note": "1/4", "bpm": 96}`, which beats `--bpm`.

## The spec file

```json
{
  "name": "Hotel California Lead",
  "parameters": [
    {"module": "",         "key": "selectedAmp", "value": "SW50R"},
    {"module": "sw50rAmp", "key": "sw50rVolume", "value": 62},
    {"module": "delay",    "key": "delayActive", "value": true},
    {"module": "delay",    "key": "delayTime",   "value": 480}
  ]
}
```

- `module` is the flat module name (`pr12Amp`, `delay`, `cabParameters`).
  Top-level parameters use an **empty string**.
- Include **only what you're changing.** Everything else is inherited from the
  template unchanged.
- Escape hatch: `"raw": true` writes the value as the literal stored string,
  skipping translation and validation. Only for IR file paths.

## Inspect a preset

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/show.py" PRESET.xml          # JSON, for you
python "${CLAUDE_PLUGIN_ROOT}/scripts/show.py" PRESET.xml --text   # for the user
```

Prints every parameter with its `kind`, stored value, human value, UI label,
declared range, and selector member name. **Read this before editing anything.**

## Apply a spec

Always preview first:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/apply_spec.py" \
  --template TEMPLATE.xml --spec /tmp/spec.json --out OUT.xml --dry-run
```

`--dry-run` prints a human-readable change list (`sw50rVolume 27.4% → 62%`)
and writes nothing. Show it to the user, then drop `--dry-run` to write.

Other flags:

- `--strip-irs` — clear custom IR paths so the preset uses internal mics and is
  portable on any machine. Reversible, but it changes the sound — see
  [cab-and-irs.md](cab-and-irs.md).
- `--allow-out-of-range` — downgrade a declared-range violation to a warning.
  Use only when the user asks for something deliberately extreme, and say so.
- `--force` — overwrite an existing `--out`. Ask first.
- `--pack <id>` — force a pack instead of detecting it from the file header.
- `--recipe LAYER/ID`, `--bpm N` — see [Stacking recipes](#stacking-recipes).
- `--name` — set the preset name without putting it in a spec.

`/version` is marked read-only in the manifest and the writer refuses it, with
or without the `raw` escape hatch.

The tool refuses to write `--out` over `--template`, refuses to clobber an
existing file without `--force`, and validates every value before writing
anything — so a failed run leaves no partial output.

## Verify before you claim success

1. Re-run `show.py` on the output and confirm the new values are there.
2. Run `python -m pytest tests/test_roundtrip.py` — if the format layer is
   broken, do not ship the preset.
3. Tell the user where the file is and how to load it —
   see [installing.md](installing.md).

## The second preset encoding

The byte-level parser and writer are plugin-agnostic, and measured to be so:
every one of 681 presets across Morgan Amps Suite, Tone King Imperial MKII,
Archetype Nolly X and Archetype Plini X round-trips byte for byte.

Two encodings exist above that layer.

**Named keys with text values** — Morgan, Nolly X, Plini X. Every parameter has
its own key and its value is a printable string behind a `0x01 <len+2> 0x05`
marker.

**PARAM records with binary values** — Tone King Imperial MKII:

```
PARAM  id -> "ampType"   value -> 0x01 0x09 0x04 <8-byte little-endian double>
```

The key says nothing about which control it is; the parameter's identity is the
`id` field inside the record. Both are read, edited and written. Three details
were each a bug before they were understood:

- **A payload byte can be printable.** The exponent bytes of `120.0` are
  `5e 40` — `^@` — so a text-only parser reads them as the start of the next
  key. That is where the parameter `^@presetNameProp` came from.
- **The record list is introduced by `0x01 <count+1>`,** and when that count is
  printable it glues to the first marker: 101 records produces `fPARAM`. Exactly
  one record per preset was affected — the first.
- **The value field is optional.** `PARAM {id: drive1Treble}` with no value is
  legal. Those are listed on `Preset.valueless` rather than given an invented
  value, because there is nothing to read and the writer cannot add a field.

A third marker, `0x01 <LEN> 0x06`, holds an 8-byte identifier (`presetUIDProp`).
It is preserved byte for byte, rendered as hex, and refuses to be written —
nothing here knows what its bytes mean.

`bootstrap_pack.py` still refuses two shapes, because it would get them wrong
silently: a binary width other than 8 bytes, and a record layout that is not
`PARAM {id, value}`.

### Verifying a plugin whose state is a preset

Tone King keeps its Audio Unit state in this same record format rather than as a
document. `scripts/probe_state.py` edits that state through `format/`, applies
multiple candidates per numeric key, and reads back both retained state and the
published control tree. `audit_manifest.py` selects this mapper automatically.

Of the 255 numeric keys in the plugin's **live state**, 94 map consistently to
one published control, 158 retain alternate state without moving a published
control, `tempo` rejects its observed alternates, and 2 (`/5`, `/6`) are
bulk-recall flags that move dozens of controls at once. A **saved preset**
carries 253 of these — the last two exist only in the live state, which is why
the two counts differ. The mappings reach every published control
except the host-only Preset Previous/Next actions and tie 33 selector label
tables to their stored indices — 12 enums plus the two-label table each of the
21 switches publishes. Every mapped control's declared range is re-derived from
the plugin except `reverbPreDelay`, whose lower end no write can establish
because the control already sits on it. The 159 state-only or rejected fields are
`internal` and read-only: they remain in the manifest for inspection and
lossless round-trip, but generated specs cannot write them. See
[../docs/measuring-against-the-plugin.md](../docs/measuring-against-the-plugin.md).
