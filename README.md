# neuraldsp-preset-generator

A Claude Code plugin that generates and edits **Neural DSP** amp-sim preset
files (`.xml`, binary) — for personal interoperability with your own licensed
copy of the plugin.

Describe a song and a guitar role and get a preset; or point at a preset,
describe a change in plain English, and get a new one back.

> **You need your own copy of the plugin.** No Neural DSP code, audio, impulse
> responses, or factory presets are included here — see [NOTICE.md](NOTICE.md).
> The repo ships one example preset that this project generated
> (`samples/Example_Clean_PR12.xml`); everything else you'd want as a template
> comes from your own library.

Format support so far targets **Morgan Amps Suite**. Other Neural DSP plugins
are supported by adding a pack — see [Packs](#packs).

## Install

```bash
git clone https://github.com/YoavBZ/neuraldsp-preset-generator
claude --plugin-dir ./neuraldsp-preset-generator
```

Then:

```
/neuraldsp-preset-generator:generate  Hotel California, clean rhythm
/neuraldsp-preset-generator:edit      my-preset.xml  more reverb, tighter low end
```

You don't have to use the slash commands — just describing what you want
("give me a jangly rhythm tone for Morgan") triggers the right skill.

## The two skills

- **`generate`** — describe a song, artist, or sound; the skill researches how
  the tone was recorded, maps it to the plugin's amps and effects, writes a
  preset, and puts it where the plugin will find it.
- **`edit`** — point at an existing preset, describe the change in plain
  English, get a new preset back. The input is never overwritten.

Both preview their changes before writing:

```
4 change(s) against Example_Clean_PR12.xml:
  name                  Example Clean PR12  ->  Hotel California Lead
  selectedAmp           PR12  ->  SW50R
  sw50rAmp/sw50rVolume  27.4%  ->  62%
  delay/delayTime       420 ms  ->  480 ms
```

## Layout

```
.claude-plugin/  — plugin manifest
skills/          — generate/ and edit/, the two entry points
reference/       — shared detail, loaded on demand (spec format, cab/IRs, installing)
scripts/         — show.py (inspect) and apply_spec.py (write)
packs/           — one directory per Neural DSP plugin (see below)
format/          — NDSP binary parser + writer (lossless) + value translation
schema/          — builds the optional observed-value catalog from your presets
samples/         — presets. One generated example ships; add your own (git-ignored)
tests/           — round-trip, mutation, translation, cab, and pack-contract tests
docs/            — Morgan config reference (musical, not yet fully reconciled)
```

## Packs

A **pack** is everything the tool knows about one Neural DSP plugin:

```
packs/morgan/
  manifest.json   committed — the contract: every parameter's kind, unit,
                  declared range, selector members, UI name
  tone.md         committed — musical knowledge for this plugin
  observed.json   git-ignored, optional — what values YOUR presets use
  templates/      git-ignored — your own presets
```

The distinction that matters: **`manifest.json` says what is *legal*;
`observed.json` says what is *typical*.** The first is a shared, hand-curated
fact table with no plugin content in it. The second is generated from your
library, echoes absolute IR paths, and stays local.

Because the manifest ships, `show.py` and `apply_spec.py` work on a fresh clone
with **no build step**.

Presets identify their plugin in their first bytes (`morgan`), so the right pack
is selected automatically for any preset you point at.

### Adding a pack for another plugin

You need one preset from that plugin as a template — the writer clones, it never
synthesises. Drop it in `samples/`, run `python -m schema.build_schema` to see
what parameters it has, and write a `packs/<id>/manifest.json` against it. The
format layer is plugin-agnostic; only the manifest is per-plugin.

## Value convention

The plugin's knobs have no numbers — a knob is just a rotation. So:

- **Bare knobs** are **percent of rotation, 0–100** (noon = 50); stored as `0.0–1.0`.
- **Metered controls** (gate, EQ, cutoffs, delay/reverb times, tempo, transpose)
  use their **native unit** (dB / Hz / ms / s / BPM / semitones).
- **Switches** are `true`/`false`; **selectors** take a member name
  (`"PR12"`, `"Ribbon 121"`) or an integer.

Every parameter's `kind` and `unit` live in `packs/<id>/manifest.json`.

## Optional: taste anchors from your own library

```bash
cp ~/Library/Audio/Presets/Neural\ DSP/Morgan*/User/*.xml samples/
python -m schema.build_schema
```

This writes `packs/morgan/observed.json`, which `show.py` folds in as advisory
"what does this knob usually sit at" context. Nothing requires it.

## How it works

The `.xml` extension is a lie — the file is binary, with no public spec. Rather
than synthesize one, the writer **clones a known-good preset and mutates only
its printable string values**, preserving every wrapper byte and recomputing the
one length byte the plugin validates. That's why round-trip fidelity is tested
byte-for-byte, and why a template is always required.

All three Morgan amp modules (AC20 / PR12 / SW50R) exist in every preset file,
so the top-level `selectedAmp` key can reach any amp from any template.

## Tests

```bash
pip install -e ".[dev]"
python -m pytest
```

Passes on a bare clone against the bundled example preset. Tests needing several
real presets — the IR-stripping encoding check in particular — skip with a note
until you add your own.

`claude plugin validate . --strict` checks the plugin manifest and skill
frontmatter.

## License and scope

MIT — see [LICENSE](LICENSE). Read [NOTICE.md](NOTICE.md) for scope, what is
deliberately excluded, and format credits.

Not affiliated with, endorsed by, or supported by Neural DSP.
