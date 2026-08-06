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

Production packs target **Morgan Amps Suite** and **Tone King Imperial MKII**.
Both packs have verified writable Audio Unit mappings, ranges, selector tables,
tone guidance, and composable recipes. Both Neural DSP preset encodings are
handled. Other plugins are supported by adding a pack — see [Packs](#packs).

## Requirements

- **Python 3.10 or later** on your `PATH` as `python` — the skills call it to read
  and write presets. Check with `python --version`.
- **Your own licensed copy** of the Neural DSP plugin. Nothing here works without
  at least one preset from it, and no plugin content ships in this repo.

## Install

As a plugin, from this repo's own marketplace:

```
/plugin marketplace add YoavBZ/neuraldsp-preset-generator
/plugin install neuraldsp-preset-generator@yoavbz-tone-tools
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
[Where your data lives](#where-your-data-lives). `build_observed.py` warns when
it is about to write a catalog somewhere that will be wiped.

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
reference/       — shared detail, loaded on demand (spec format, cab/IRs,
                   selectors/timing, installing)
scripts/         — show.py (inspect), apply_spec.py (write), probe.py (discover
                   selectors), au_probe.swift (ask the running plugin directly),
                   au_render.swift + spectrum_diff.py (measure what a control
                   does to the sound), au_render_server.swift (render many
                   parameter sets from one instance), spike_pedalboard.py
                   (render through a JUCE host instead),
                   fingerprint.py + compare_audio.py (measure a recording, and
                   what a preset would have to change to match it),
                   match_preset.py (match a reference recording with a preset,
                   and say what not to believe about it),
                   benchmark_match.py (recover 50 random parameter vectors
                   three ways, to check the pipeline beats its baselines),
                   audit_manifest.py (re-check every
                   declared fact against the plugin), bootstrap_pack.py
                   (support a new plugin),
                   build_observed.py (optional taste anchors)
packs/           — one directory per Neural DSP plugin (see below)
format/          — NDSP binary parser + writer (lossless) + value translation
analysis/        — measure audio into a comparable fingerprint, plus a synthetic
                   amp chain to measure against (optional extra, never needed to
                   read or write a preset)
match/           — turn a measured sound into preset parameters: the Renderer
                   protocol, the synthetic backend, the conditional search space
                   built from a manifest, the inversions that calculate what does
                   not need searching for, the four-stage search that spends a
                   render budget on the rest, a sqlite3 store so no render is
                   paid for twice, a self-contained HTML report, and the
                   benchmark that decides whether any of it beat the baselines.
                   Building the space, writing a spec and reading the store need
                   no dependencies; rendering, fitting and searching need the
                   analysis extra
samples/         — the bundled example preset
tests/           — round-trip, mutation, translation, cab, pack-contract,
                   record-encoding, audit, recipe, path, CLI and
                   plugin-metadata tests, plus audio-analysis, synthetic-chain,
                   renderer, search-space, inversion, search, store, report,
                   benchmark and bare-clone tests
docs/            — maintainer procedures for measuring ranges, selectors,
                   mappings and audible behavior against a plugin, and the
                   design plan for reference-guided tone matching
```

## Packs

A **pack** is everything the tool knows about one Neural DSP plugin:

```
packs/<id>/
  manifest.json   committed — the contract: every parameter's kind, and
                  whatever else has been established for it — unit, declared
                  range, selector members, EQ band centres, UI name. A pack
                  carries what was measured, not a full set
  recipes.json    committed — composable tone recipes, one layer at a time
                  (Morgan 40, Tone King 39)
  tone.md         committed — amps, intent -> recipe table, tone vocabulary
  observed.json   git-ignored, optional — what values YOUR presets use
  templates/      git-ignored — your own presets
  learned-tones.md  git-ignored — what past runs learned, including your
                    corrections. Read before generating, appended after.
```

The last three live under the **data root**, not in the plugin directory, so a
plugin update can't take them with it.

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

Recipe values use the same kinds, names, and units as the pack manifest.
The recipe tests for both production packs assert that every key exists and
every value survives translation, so a stale name, invalid selector, read-only
field, or out-of-range setting fails the suite.

Tone King recipes use its flat record-state keys and can be stacked the same
way:

```bash
python scripts/apply_spec.py --template ~/…/ToneKingTemplate.xml \
  --pack toneking --recipe amp/lead-crunch \
  --recipe cab/balanced-57-ribbon --recipe delay/mono-quarter \
  --recipe reverb/lead-space --recipe output/unity \
  --name "Focused Lead" --out focused-lead.xml --dry-run
```

### Adding a pack for another plugin

You need one preset from that plugin — the writer clones, it never synthesises.
Then:

```bash
python scripts/bootstrap_pack.py --preset ~/…/SomePreset.xml \
  --display-name "Archetype Gojira"
```

It reads the plugin's own name out of the file, drafts a manifest covering every
parameter, and prints what it *couldn't* work out. That last part is the point:

- **Ranges cannot be inferred.** One preset shows one value, which says nothing
  about limits. They are left undeclared — meaning unchecked — until you add them.
- **Selector members cannot be inferred** either, because the plugin never
  displays the stored integer. `scripts/probe.py` is how you find those.
- **Kinds are guessed** from key names and are marked `needs_review`. A wrong
  kind writes a wrong value, so `apply_spec.py` warns every time it writes one
  through — the warning goes away when you confirm the kind and drop the flag.

The draft is immediately loadable, so `show.py` and `apply_spec.py` work against
it right away — correct it against the plugin's UI as you go, and drop
`"draft": true` when you trust it. The format layer is plugin-agnostic; only the
pack is per-plugin.

## Value convention

The human value depends on the manifest kind:

- **Rotation knobs** are **percent of rotation, 0–100** (noon = 50), stored as
  `0.0–1.0`.
- **Fraction controls** use their normalized value directly, `0.0–1.0`.
- **Metered controls** (gate, EQ, cutoffs, delay/reverb times, tempo, transpose)
  use their **native unit** (dB / Hz / ms / s / BPM / semitones).
- **Switches** are `true`/`false`, or the plugin's own label where the pack
  declares one (`"Active"`, `"Off"`); **selectors** take a member name
  (`"PR12"`, `"Ribbon 121"`) or an integer.

Every parameter's `kind` and `unit` live in `packs/<id>/manifest.json`.
The full table, with what to write for each kind, is in
[reference/preset-spec.md](reference/preset-spec.md).

## Musical timing without the sync selector

A "dotted eighth delay" is just arithmetic, so it doesn't need the plugin's
sync-note selector:

```python
from packs.timing import note_ms
note_ms(120, "1/8 dotted")   # 375.0  ms  -> write to delay/delayTime
```

Both sync-note tables are declared in the manifest and can be set by name
(`"1/8D"`), so the selector is available when you do want host-tempo sync. They
are ordered by note *duration* rather than grouped by kind, and delay's table
and tremolo's are offset by two — which is exactly why they are measured and
written down rather than guessed.

Two selectors still have no member names: `leftRoomMicType` and
`rightRoomMicType`. The plugin publishes no labels for them and has no control
for them anywhere in its UI, so there is nothing to read. Writing them works,
with a warning, but there is no reason to.

`scripts/au_probe.swift` reads whatever the plugin does publish, directly. For
anything it cannot, `scripts/probe.py` inverts the problem: it writes disposable
presets **named after the value they carry**, so the plugin's own preset browser
labels them. See
[reference/selectors-and-timing.md](reference/selectors-and-timing.md).

## Where your data lives

Two different things, in two different places:

- **Code and committed data** ship with the plugin: the pack manifests, the
  recipes, the bundled example preset. Located from the code itself, never from
  an environment variable.
- **Your preset library and anything generated from it** live under a *data
  root*, resolved in this order:

  1. `--data-dir`, on the two scripts that read or write it (`show.py`,
     `build_observed.py`)
  2. `$NDSP_PRESET_DATA`
  3. `$CLAUDE_PLUGIN_DATA` (set by Claude Code for installed plugins)
  4. the repo root — correct when working in a clone

Your presets go in `<data root>/packs/<pack>/templates/`, and generated catalogs
in `<data root>/packs/<pack>/observed.json`. Neither is ever committed.

## Optional: taste anchors from your own library

```bash
mkdir -p "$NDSP_PRESET_DATA/packs/morgan/templates"
cp ~/Library/Audio/Presets/Neural\ DSP/Morgan*/User/*.xml \
   "$NDSP_PRESET_DATA/packs/morgan/templates/"
python scripts/build_observed.py
```

This writes `observed.json` per pack, which `show.py` folds in as advisory "what
does this knob usually sit at" context. Nothing requires it. Presets are routed
to the right pack by the plugin name in their own first bytes, so a mixed library
sorts itself out.

## Optional: measure a recording

The preset tools never listen to anything — they go from a description to a
recipe stack to preset bytes, and nothing in that path can tell whether the
result got closer to the record. `analysis/` is the beginning of closing that
loop: it measures audio into a **fingerprint**, so two sounds can be compared as
numbers instead of adjectives.

```bash
pip install -e '.[analysis]'
python scripts/fingerprint.py song-excerpt.wav --regime mix --text
python scripts/compare_audio.py song-excerpt.wav my-render.wav
```

The comparison prints a per-band difference — what the candidate would have to
change to match the target — plus named distances for timbre, dynamics,
ambience, level, harmonic character and stereo width. It reports what it could
*not* measure just as plainly: a fingerprint of a chord says it found no
sustained note to judge distortion from, and a match against a full mix says the
guitar was never isolated.

Nothing above this is affected. `show.py` and `apply_spec.py` still run on a bare
clone with no dependencies at all, and a test enforces it.

## Optional: match a recording

With `[match]` as well, the loop closes: given a recording you like and a preset
to start from, `match_preset.py` measures the reference, calculates what can be
calculated, searches the rest on a render budget you set, and writes a spec plus
a report.

```bash
pip install -e '.[analysis,match]'
python scripts/match_preset.py \
  --template samples/Example_Clean_PR12.xml \
  --reference song-excerpt.wav --reference-mode mix \
  --budget 300 --out-dir runs/hotel-california-001
```

It writes `match-1.json` — a spec `apply_spec.py` turns into a preset, so the
winner goes through the same validated path as a hand-authored one — and
`report.html`, one self-contained file. **Read the report before trusting the
number**: it opens with the caveats rather than the charts, and each one names a
place where a figure rests on an assumption instead of a measurement.

The backend is a Python approximation of the plugin's topology, not the plugin.
Every number this produces is a number about that approximation until the real
backend exists (M5, which needs macOS and a licence). If you have that machine,
[docs/handoff-to-macos.md](docs/handoff-to-macos.md) is the run-book:
what to run, in what order, and what should happen.

The generate and edit skills do not use any of this yet — see
[docs/tone-matching-plan.md](docs/tone-matching-plan.md) for what it is for.

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
the values of parameters it already contains**, preserving every wrapper byte.
For a text value it recomputes the one length byte the plugin validates; for a
binary one it re-encodes in place at a fixed width. That's why round-trip
fidelity is tested byte-for-byte, and why a template is always required.

All three Morgan amp modules (AC20 / PR12 / SW50R) exist in every preset file,
so the top-level `selectedAmp` key can reach any amp from any template.

## Tests

```bash
pip install -e ".[dev]"                  # the preset tools
pip install -e ".[dev,analysis]"         # and the audio measurement
pip install -e ".[dev,analysis,match]"   # and the synthetic renderer
python -m pytest
```

Two more extras exist and neither is needed for the tests. `match` resolves to
`analysis` today, so the second line is already enough to run everything. `host`
adds `pedalboard` for `scripts/spike_pedalboard.py`, which needs macOS and a
licensed plugin and is never run by CI.

Passes on a bare clone against the bundled example preset: the IR-stripping
check synthesises the preset it needs rather than requiring one of yours. The
audio tests skip without the `analysis` extra and synthesise every signal they
measure, so no audio is committed either. CI runs both installs, and one test
asserts that the preset tools still import and run with numpy made unavailable.

```bash
claude plugin validate ./.claude-plugin/plugin.json --strict   # manifest + skills
claude plugin validate ./.claude-plugin/marketplace.json --strict
```

Point it at `plugin.json` explicitly: with a `marketplace.json` present, a bare
`.` resolves to the marketplace manifest and the skills go unchecked.

## License and scope

MIT — see [LICENSE](LICENSE). Read [NOTICE.md](NOTICE.md) for scope, what is
deliberately excluded, and format credits.

Not affiliated with, endorsed by, or supported by Neural DSP.
