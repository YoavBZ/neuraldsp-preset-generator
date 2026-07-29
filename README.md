# neuraldsp-preset-generator

A Claude Code skill that generates and edits **Neural DSP Morgan Amps Suite**
preset files (`.xml`, binary) — for personal interoperability with your own
licensed copy of the plugin.

Describe a song and a guitar role and get a preset; or point at a preset,
describe a change in plain English, and get a new one back.

> **You need your own copy of the plugin.** No Neural DSP code, audio, impulse
> responses, or factory presets are included here — see [NOTICE.md](NOTICE.md).
> The repo ships one example preset that this project generated
> (`samples/Example_Clean_PR12.xml`); everything else you'd want as a template
> comes from your own library.

## Modes

- **Generate** — describe a song + guitar role; the skill researches the tone
  and writes a new preset.
- **Edit** — point at an existing preset, describe the change in plain English,
  get a new preset back. The input is never overwritten.

## Layout

```
format/   — NDSP binary parser + writer (lossless) + value translation
schema/   — parameter catalog (kind/unit/ranges), generated from your presets
.claude/  — the skill: SKILL.md + scripts/ (apply_spec, show)
samples/  — presets. One generated example ships; add your own (git-ignored)
tests/    — round-trip, mutation, translation, and cab tests
knowledge/— notes on Morgan amps + tone references
docs/     — Morgan config reference (verification-checked)
```

## Quick start

```bash
# 1. Build the parameter schema. Required before the skill will run —
#    it's generated, not committed, because it echoes every string in
#    your presets (including absolute IR paths).
python -m schema.build_schema

# 2. Inspect a preset (stored + human values for every parameter):
python .claude/skills/morgan-preset-gen/scripts/show.py samples/Example_Clean_PR12.xml

# 3. Use the skill (from Claude Code in this repo):
#    /morgan-preset-gen generate --song "Wish You Were Here" --role lead
```

Step 1 works on a bare clone using the bundled example, but a schema built from
a single preset has near-empty `observed_min`/`observed_max` ranges, so you'll
get "outside observed range" warnings. To get useful ranges, add a few of your
own presets first and re-run it:

```bash
cp ~/Library/Audio/Presets/Neural\ DSP/Morgan*/User/*.xml samples/
python -m schema.build_schema
```

## Value convention

The plugin's knobs have no numbers — a knob is just a rotation. So:

- **Bare knobs** are written as **percent of rotation, 0–100** (noon = 50);
  stored in the file as `0.0–1.0`.
- **Metered controls** (gate, EQ, cutoffs, delay/reverb times, tempo,
  transpose) use their **native unit** (dB / Hz / ms / s / BPM / semitones).
- **Switches** are `true` / `false`; **selectors** (e.g. `selectedAmp`:
  `0`=AC20, `1`=PR12, `2`=SW50R) are integers.

Each parameter's `kind` and `unit` live in `schema/morgan_schema.json`;
`scripts/apply_spec.py` translates human values to the binary encoding, and
`scripts/show.py` prints both stored and human values for any preset.

## How it works

The `.xml` extension is a lie — the file is binary, with no public spec. Rather
than synthesize one, the writer **clones a known-good preset and mutates only
its printable string values**, preserving every wrapper byte and recomputing the
one length byte the plugin validates. That's why round-trip fidelity is tested
byte-for-byte, and why a template is always required.

All three amp modules (AC20 / PR12 / SW50R) exist in every preset file, so the
top-level `selectedAmp` key can reach any amp from any template.

## Tests

```bash
python -m pytest
```

Passes on a bare clone against the bundled example preset. Tests needing several
real presets — the IR-stripping encoding check in particular — skip with a note
until you add your own. Add presets to `samples/` and they're picked up
automatically.

## License and scope

MIT — see [LICENSE](LICENSE). Read [NOTICE.md](NOTICE.md) for scope, what is
deliberately excluded, and format credits.

Not affiliated with, endorsed by, or supported by Neural DSP.

<sub>Repo is `neuraldsp-preset-generator`; the Python package is
`morgan-preset-gen`, since the format work so far targets Morgan Amps Suite.</sub>
