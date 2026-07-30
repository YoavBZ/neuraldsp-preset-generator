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

## Requirements

- **Python 3.10 or later** on your `PATH` as `python` — the skills call it to read
  and write presets. Check with `python --version`.
- **Your own licensed copy** of the Neural DSP plugin. Nothing here works without
  at least one preset from it, and no plugin content ships in this repo.

## Install

As a plugin, from this repo's own marketplace:

```
/plugin marketplace add YoavBZ/neuraldsp-preset-generator
/plugin install neuraldsp-preset-generator@yoavbz-plugins
```

Or from a clone, which is also the way to develop it:

```bash
git clone https://github.com/YoavBZ/neuraldsp-preset-generator
claude --plugin-dir ./neuraldsp-preset-generator
```

If you install it as a plugin, **set `NDSP_PRESET_DATA`** to a directory you
control:

```bash
export NDSP_PRESET_DATA=~/ndsp-presets
```

Claude Code replaces a plugin's directory when the plugin updates, so your
preset library and generated catalogs need to live outside it. See
[Where your data lives](#where-your-data-lives). The tools warn you if they're
about to write somewhere that will be wiped.

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
scripts/         — show.py (inspect), apply_spec.py (write), probe.py (discover
                   selectors), build_observed.py (optional taste anchors)
packs/           — one directory per Neural DSP plugin (see below)
format/          — NDSP binary parser + writer (lossless) + value translation
samples/         — the bundled example preset
tests/           — round-trip, mutation, translation, cab, and pack-contract tests
docs/            — Morgan config reference (musical, not yet fully reconciled)
```

## Packs

A **pack** is everything the tool knows about one Neural DSP plugin:

```
packs/morgan/
  manifest.json   committed — the contract: every parameter's kind, unit,
                  declared range, selector members, EQ band centres, UI name
  recipes.json    committed — 40 composable tone recipes, one layer at a time
  tone.md         committed — amps, intent -> recipe table, tone vocabulary
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

### Recipes are composable, and the translation is tested

A preset is built by stacking layers — amp + compressor + drive + EQ + cab +
delay + reverb + output staging — then adapting the values to the song:

```bash
python scripts/apply_spec.py --template samples/Example_Clean_PR12.xml \
  --recipe amp/sw50r-singing-lead --recipe eq/lead-focus \
  --recipe delay/classic-lead --recipe reverb/large-lead \
  --bpm 96 --name "Singing Lead" --out lead.xml --dry-run
```

The EQ is per-amp, so EQ recipes are written against `{amp}EQ` and resolved to
whichever amp the stack selects — get that wrong and the EQ silently does
nothing, which is why it's done in code rather than by hand. Delay recipes carry
a note division rather than a fixed time, so `--bpm 96` turns a quarter note into
625 ms with no sync selector involved.

The
recipes were translated out of `docs/morgan-config-reference.md`, which uses a
0–10 knob scale, its own parameter names, and a cab model that doesn't match the
binary. Rather than trust that transcription, `tests/test_recipes.py` asserts
every recipe key exists in the manifest and every value survives translation, so
a knob left on the 0–10 scale or a stale `od1Drive` name fails the suite.
Anything that *couldn't* be translated is listed with a reason under
`not_translated`.

### Adding a pack for another plugin

You need one preset from that plugin as a template — the writer clones, it never
synthesises. Drop it in `<data root>/packs/<id>/templates/`, run
`python scripts/build_observed.py` to see what parameters it has, and write a `packs/<id>/manifest.json` against it. The
format layer is plugin-agnostic; only the manifest is per-plugin.

## Value convention

The plugin's knobs have no numbers — a knob is just a rotation. So:

- **Bare knobs** are **percent of rotation, 0–100** (noon = 50); stored as `0.0–1.0`.
- **Metered controls** (gate, EQ, cutoffs, delay/reverb times, tempo, transpose)
  use their **native unit** (dB / Hz / ms / s / BPM / semitones).
- **Switches** are `true`/`false`; **selectors** take a member name
  (`"PR12"`, `"Ribbon 121"`) or an integer.

Every parameter's `kind` and `unit` live in `packs/<id>/manifest.json`.

## Musical timing without the sync selector

A "dotted eighth delay" is just arithmetic, so it doesn't need the plugin's
sync-note selector:

```python
from packs.timing import note_ms
note_ms(120, "1/8 dotted")   # 375.0  ms  -> write to delay/delayTime
```

This matters because the plugin's UI shows a selector's *label* but never the
integer stored in the file, so six selectors (`delaySyncNote`,
`tremoloSyncNote`, `delaySync`, `ac20Power`, both `CabPan`) have no member names
yet — the mapping can't be read off the screen. Writing them still works, with a
warning that the value is unverified.

To fill one in, `scripts/probe.py` inverts the problem: it writes disposable
presets **named after the value they carry**, so the plugin's own preset browser
labels them.

```bash
python scripts/probe.py --param delay/delaySyncNote --values 0-15 \
  --out-dir ~/Library/Audio/Presets/Neural\ DSP/Morgan\ Amps\ Suite/User
```

Load `probe delaySyncNote 07`, read the control, and you've learned what 7 means
— reading labels only, never integers. Selectors are index-based (confirmed for
the mic catalog), so the cheaper path is to read the control's options in order,
write them as `members`, and confirm the whole table with a single probe. See
[reference/selectors-and-timing.md](reference/selectors-and-timing.md).

## Where your data lives

Two different things, in two different places:

- **Code and committed data** ship with the plugin: the pack manifests, the
  recipes, the bundled example preset. Located from the code itself, never from
  an environment variable.
- **Your preset library and anything generated from it** live under a *data
  root*, resolved in this order:

  1. `--data-dir` passed to a script
  2. `$NDSP_PRESET_DATA`
  3. `$CLAUDE_PLUGIN_DATA` (set by Claude Code for installed plugins)
  4. the repo root — correct when working in a clone

Your presets go in `<data root>/packs/<pack>/templates/`, and generated catalogs
in `<data root>/packs/<pack>/observed.json`. Neither is ever committed.

## Optional: taste anchors from your own library

```bash
cp ~/Library/Audio/Presets/Neural\ DSP/Morgan*/User/*.xml \
   "$NDSP_PRESET_DATA/packs/morgan/templates/"
python scripts/build_observed.py
```

This writes `observed.json` per pack, which `show.py` folds in as advisory "what
does this knob usually sit at" context. Nothing requires it. Presets are routed
to the right pack by the plugin name in their own first bytes, so a mixed library
sorts itself out.

## Fewer permission prompts

The skills run `scripts/show.py` and `scripts/apply_spec.py` through Bash, so
Claude asks before each run. The plugin deliberately does **not** pre-approve
Bash for itself — a plugin granting itself shell access is worth avoiding. If you
want fewer prompts, opt in yourself in `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": ["Bash(python *scripts/show.py *)"]
  }
}
```

`show.py` only reads. Leaving `apply_spec.py` to prompt is the point: that's the
one that writes a file.

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
