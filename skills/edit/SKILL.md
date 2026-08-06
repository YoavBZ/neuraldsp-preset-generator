---
name: edit
description: Change an existing Neural DSP amp-sim preset from a plain-English description of what should be different — "more reverb", "tighter low end", "too dark", "needs more bite". Reads the preset's current values, translates the ask into parameter changes, and writes a new preset without touching the original.
when_to_use: >-
  Use when a tone or preset already exists and someone wants it changed rather
  than built from scratch — any complaint or adjustment about how it currently
  sounds. For example — this is too boomy; make it brighter; too much gain; add
  some delay to my preset; tweak this patch; can you dial that back. Also
  triggers whenever they point at a .xml preset file and describe a change, or
  ask to fix, adjust, tweak, warm up, tighten or brighten a sound.
argument-hint: "[preset.xml] [what to change]"
allowed-tools: Read, Glob, Grep, Bash
---

# Edit a preset

Adjust an existing preset from a description of what should change. Read
[preset-spec.md](../../reference/preset-spec.md) before writing anything.

## 1. Read the current state first

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/show.py" PRESET.xml
```

Never edit blind. You need the current values to know what "more" means: a
change to a nearly dry effect is not the same move as a change to one already
near its limit. Note which amp or channel is live — Morgan reports
`selectedAmp`; Tone King reports its channel selector — and touch the controls
that belong to it.

## 2. Interpret the ask against those values

`${CLAUDE_PLUGIN_ROOT}/packs/<id>/tone.md` has the pack-specific adjustment
vocabulary and recipes. Use its exact parameter names and value convention;
Morgan rotation controls use 0–100 while Tone King fraction controls use
0.0–1.0. Typical translations are:

- **"more reverb"** → raise the post-reverb mix modestly, or the live amp's own
  reverb control for a spring-tank character
- **"tighter low end"** → lower the live amp's bass modestly, trim the lowest
  graphic-EQ bands, and/or raise ambience high-pass filtering
- **"more presence" / "more bite"** → raise the live amp's treble, or push the
  upper EQ bands (dB)
- **"warmer" / "too harsh"** → lower treble/tone, lower ambience low-pass
  filtering, or choose the pack's warmer cabinet recipe
- **"more break-up"** → raise the live amp's volume/gain knob, or engage a drive
- **"dotted eighth delay", "in time with the track"** → use the pack's verified
  timing recipe; Morgan can resolve milliseconds through
  `${CLAUDE_PLUGIN_ROOT}/packs/timing.py`, while Tone King exposes verified note
  selectors. See [selectors-and-timing.md](../../reference/selectors-and-timing.md)

Move in **proportionate steps**. A vague "a bit more" is about 5–10 points for a
rotation control or 0.05–0.10 for a fraction, not a near-full-range jump. If the
ask is genuinely ambiguous ("make it better"), ask what bothers them about the
current sound.

`show.py` reports a `learned_notes` path — read it if it exists. A correction the
user made before is the best available evidence about their taste.

## 2b. Record a correction

When the user rejects or adjusts what you produced, append it to that same
`learned_notes` file: what you set, what they wanted instead, and the preset it
applied to. That is the whole point of the file — a run that needed correcting
teaches more than one that didn't.

## 3. Change only what was asked

Put **only** the parameters you're changing in the spec. The apply script clones
the input, so everything unspecified stays byte-identical. Resist the urge to
"improve" things the user didn't mention.

## 4. Preview, then write

The input preset is the template:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/apply_spec.py" \
  --template PRESET.xml --spec /tmp/spec.json --out NEW.xml --dry-run
```

Show the user the change list, then drop `--dry-run`.

**Never overwrite the input.** The tool enforces this, but pick a clearly
different `--out` name anyway — an edit the user dislikes should always be
one step from undo.

Do **not** pass `--strip-irs` on an edit unless the user asks for portability:
if their preset uses a custom IR, stripping it swaps a third-party impulse
response for an internal mic, which is a real tonal change and an easy one to
miss. The field itself is reversible and the input preset is never overwritten,
so the original path is still readable from it — but you have to say what you
did, or the user hears a change they did not ask for and has nothing to point
at. See [cab-and-irs.md](../../reference/cab-and-irs.md).

## 5. Install and report

Write it where the plugin will see it — see
[installing.md](../../reference/installing.md) — then report what you changed
in **human terms** ("bass 40% → 34%, delay low cut 132 Hz → 180 Hz"), not stored
values, plus anything the tool warned about.

If the user comes back with another adjustment, edit the *new* file, and keep
the intermediate versions around until they're happy.
