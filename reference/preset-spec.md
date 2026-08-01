# Writing and applying a preset spec

Shared reference for the `generate` and `edit` skills.

## How writing works

The preset file is binary despite its `.xml` extension, and has no public
spec. So the writer **clones a known-good preset and mutates only the printable
string values of parameters it already contains**. Wrapper bytes are preserved
verbatim; the one length byte the plugin validates is recomputed.

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
| `switch`   | `true` / `false`            | `true`                           |
| `enum`     | integer **or member name**  | `"PR12"`, `"Ribbon 121"`, `2`    |
| `string`   | text, written verbatim      | a preset name                    |
| `path`     | absolute path, verbatim     | a custom IR file                 |

`metered` units: **dB** (gate, input/output, mic levels, EQ bands), **Hz**
(HPF/LPF/cuts, tremolo rate), **ms** (delay time, pre-delay, doubler spread),
**seconds** (reverb decay), **BPM** (tempo), **semitones** (transpose).

Prefer **member names over integers** for selectors — `"value": "SW50R"` reads
better than `"value": 2` and is checked against the manifest.

Six selectors have no member names yet, because the plugin never displays the
stored integer. For musical delay and tremolo you don't need them — compute
milliseconds or Hz instead. See
[selectors-and-timing.md](selectors-and-timing.md).

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

## Formats this tool cannot read

The byte-level parser and writer are plugin-agnostic and measured to be so:
every one of 681 factory presets across Morgan Amps Suite, Tone King Imperial
MKII, Archetype Nolly X and Archetype Plini X round-trips byte for byte.

The *structured* layer is narrower. It models one named key per printable value,
which is how Morgan, Nolly X and Plini X are encoded — those three draft cleanly
with `scripts/bootstrap_pack.py`. **Tone King Imperial MKII does not.** It uses a
later encoding:

- numbers are raw IEEE-754 doubles introduced by `01 09 04`, not text
- parameters are a flat list of `PARAM` records carrying `id` and `value`
  fields, so 259 parameters share 7 key names instead of having their own

The two interact badly. Because the structured layer expects printable values,
the bytes of a double that happen to land in ASCII get read as text: the
exponent bytes of `120.0` are `5e 40` — `^@` — which is how an early draft of a
Tone King pack ended up with a parameter named `^@presetNameProp`.

Supporting it needs a value decoder in `format/`, keyed off the marker byte,
plus a structured layer that can identify a parameter by a field inside a record
rather than by its key. That is a change to the format layer, not a new pack.
Nothing currently needs it, so `bootstrap_pack.py` refuses both shapes with a
diagnosis rather than drafting a manifest that looks plausible and is silently
wrong.
