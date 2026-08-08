---
name: generate
description: Create a Neural DSP amp-sim preset for a specific guitar tone — from a song, an artist, a part, or a description of the sound. Researches how the tone was actually recorded, maps it to the plugin's amps and effects, and writes a loadable preset file.
when_to_use: >-
  Use whenever someone asks for a guitar tone, preset or patch to be built, or
  describes a sound they want to get — even without naming a plugin or a file.
  Triggers when they name a song, artist, band, genre or era; ask how to get a
  sound or what settings to use; ask to make something sound like a reference;
  or say tone, preset, patch, amp sim, amp settings, rig, Neural DSP, or Morgan
  Amps Suite. For example — give me the clean tone from Hotel California; make
  a Gilmour-ish lead patch; I need a jangly rhythm sound; set me up for blues
  lead.
argument-hint: "[song or tone description] [rhythm|lead|clean]"
allowed-tools: Read, Glob, Grep, Bash, WebSearch, WebFetch
---

# Generate a preset

Turn a description of a tone into a loadable preset. Read
[preset-spec.md](../../reference/preset-spec.md) before writing anything — it
covers the value convention, the spec format, and the scripts.

## 1. Understand the ask

The user speaks in plain language, not flags. Extract:

- **the tone** — song, artist, era, or a bare description ("jangly", "creamy lead")
- **the role** — rhythm / lead / clean, if stated
- **the plugin** — which pack. Detect it from a template they point at; if they
  don't say, detect the pack from the template's own header rather than
  assuming — more than one pack exists now. If there is genuinely nothing to
  detect from, ask rather than picking.

Ask at most **one** clarifying question, and only if the answer would change the
amp choice. Otherwise pick sensible defaults and say what you assumed.

## 2. Research the tone

When the user supplies audio, measure it before choosing values:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/fingerprint.py" REFERENCE.wav \
  --regime separated_stem --text
```

Classify the reference conservatively: `isolated_stem` only for an original
multitrack stem, `separated_stem` for source-separated guitar, and `mix` for a
finished mix. Report the regime and its confidence together with the measured
level, spectral tilt and roll-off, dynamics, time effects, harmonic confidence,
and all caveats. Then follow the [match skill](../match/SKILL.md) when a template
is available. Measurement moves values; it does not identify the recorded rig.

Use WebSearch and WebFetch to find how it was actually recorded and choose the
topology. Good sources:
Premier Guitar rig rundowns, artist interviews, Guitar World tone breakdowns,
well-cited forum threads, video lesson notes.

Capture: the **amp character** (Vox / Marshall / Fender-ish? clean, edge, or
driven?), the **effects** (delay, reverb, modulation, drive pedals), and the
part's **place in the mix**. Keep the source links — you'll cite them.

If research turns up nothing solid, say so and design from the description
instead. Don't invent a rig rundown.

## 3. Map it to the plugin

Read `${CLAUDE_PLUGIN_ROOT}/packs/<id>/tone.md` — it has the amps and their character, an
**intent → recipe stack** table, and the "when the user says X" mappings. Read
`${CLAUDE_PLUGIN_ROOT}/packs/<id>/manifest.json` for what each parameter is, its unit, and its legal
range.

**Also read the learned notes**, if there are any. `show.py` reports their path
as `learned_notes` — that's where past runs recorded what actually worked, and it
beats generic guidance. It lives under the data root, so it survives plugin
updates.

**Not every pack has this knowledge.** `show.py` reports `tone_knowledge.exists`,
and a bootstrapped pack has no `recipes.json` at all. When either is missing,
say so plainly: you can still edit a template the user points at, but you cannot
map a tonal description onto controls nobody has characterised. Do not invent
the mapping — that is the guess this project exists to avoid.

**Build from recipes, then adapt.** `${CLAUDE_PLUGIN_ROOT}/packs/<id>/recipes.json` holds composable
layers — amp, compressor, drive, eq, cab, delay, reverb, output. Pick one per
layer from the intent table and pass them straight to the writer with `--recipe`;
it resolves `{amp}` and note divisions for you. Then put **what the song needs**
in a `--spec`, which is applied last and overrides the recipes.

Handing back an unmodified stack is a failure — it's a renamed factory preset.
The research in step 2 is what should move the values.

Select the amp or channel through the pack's `amp/*` recipe. Morgan uses
`selectedAmp`; Tone King uses its own channel selector. Do not hard-code one
pack's selector into another pack's spec.

For **note-timed delay** ("dotted eighth", "quarter-note slapback"), prefer a
pack recipe that already expresses the timing safely. Morgan recipes resolve
note divisions to milliseconds with `${CLAUDE_PLUGIN_ROOT}/packs/timing.py`;
Tone King recipes use its verified sync-note selectors. See
[selectors-and-timing.md](../../reference/selectors-and-timing.md).

## 4. Pick a template

- For Morgan, default to `${CLAUDE_PLUGIN_ROOT}/samples/Example_Clean_PR12.xml`
  — IR-free, portable, and shipped with the repo.
- For Tone King, require one of the user's own Tone King presets. No Tone King
  preset content ships in the repository.
- One of the user's own presets is a fine template too, especially if it already
  uses the amp you want. Run `show.py` on it first.
- Either way, select the intended amp or channel explicitly through an amp
  recipe unless the inspected template already has the required value.

## 5. Write the spec, preview, apply

Build the spec JSON, then always `--dry-run` first and show the user the change
list before writing. See [preset-spec.md](../../reference/preset-spec.md).

Pass `--strip-irs` so the result is portable — see
[cab-and-irs.md](../../reference/cab-and-irs.md).

## 6. Install and report

Write the preset into the user's preset folder and tell them how to load it —
see [installing.md](../../reference/installing.md).

Then report:
- which **template** you cloned and which **amp or channel** you selected
- what **research** the tone is based on, with links
- anything you set **outside a declared range**, and why
- any **unconfirmed selector** the tool warned about
- any **guessed kind** the tool warned about (draft packs): the value was written
  through a mapping nobody has checked, so ask the user to confirm it looks right
  in the plugin

## 7. Bank what you learned

Append an entry to the `learned_notes` path that `show.py` reports — creating
the file if it doesn't exist. Record:

- the **recipes you stacked** and the **values you changed**, with why
- what the user **pushed back on**, if they did. "Too dark, ended up at 45%" is
  worth more than a successful first try, because it's the thing generic
  guidance got wrong.
- the **source link** for the research

Keep the entry concise and actionable. The notes live under the data root, not
in the plugin directory: Claude Code replaces the plugin on update, and
anything written there would be lost.
