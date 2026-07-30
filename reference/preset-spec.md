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
  the user's own presets by `python -m schema.build_schema`. This is what
  values are *typical* — a taste anchor, never a limit. Absent on a fresh
  clone; nothing breaks without it.
- `packs/<id>/tone.md` — musical knowledge for that plugin.

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

- `--strip-irs` — clear custom IR paths so the preset is portable. See
  [cab-and-irs.md](cab-and-irs.md). **Irreversible.**
- `--allow-out-of-range` — downgrade a declared-range violation to a warning.
  Use only when the user asks for something deliberately extreme, and say so.
- `--force` — overwrite an existing `--out`. Ask first.
- `--pack <id>` — force a pack instead of detecting it from the file header.

The tool refuses to write `--out` over `--template`, refuses to clobber an
existing file without `--force`, and validates every value before writing
anything — so a failed run leaves no partial output.

## Verify before you claim success

1. Re-run `show.py` on the output and confirm the new values are there.
2. Run `python -m pytest tests/test_roundtrip.py` — if the format layer is
   broken, do not ship the preset.
3. Tell the user where the file is and how to load it —
   see [installing.md](installing.md).
