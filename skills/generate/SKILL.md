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
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch
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
  don't say and only one pack exists, use it and mention which.

Ask at most **one** clarifying question, and only if the answer would change the
amp choice. Otherwise pick sensible defaults and say what you assumed.

## 2. Research the tone

Use WebSearch and WebFetch to find how it was actually recorded. Good sources:
Premier Guitar rig rundowns, artist interviews, Guitar World tone breakdowns,
well-cited forum threads, video lesson notes.

Capture: the **amp character** (Vox / Marshall / Fender-ish? clean, edge, or
driven?), the **effects** (delay, reverb, modulation, drive pedals), and the
part's **place in the mix**. Keep the source links — you'll cite them.

If research turns up nothing solid, say so and design from the description
instead. Don't invent a rig rundown.

## 3. Map it to the plugin

Read `packs/<id>/tone.md` — it has the amps and their character, an
**intent → recipe stack** table, and the "when the user says X" mappings. Read
`packs/<id>/manifest.json` for what each parameter is, its unit, and its legal
range.

**Build from recipes, then adapt.** `packs/<id>/recipes.json` holds composable
layers — amp, compressor, drive, eq, cab, delay, reverb, output. Pick one per
layer from the intent table, concatenate their `parameters`, then **change what
the song needs**. Two rules:

- EQ recipes contain `{amp}` in module and key; substitute the live amp's prefix
  (`pr12` / `sw50r` / `ac20`). The EQ is per-amp and must match `selectedAmp`.
- A recipe value of `{"note": "1/4"}` needs a `bpm` added before it can be
  applied. Get the tempo from the user or the song.

Handing back an unmodified stack is a failure — it's a renamed factory preset.
The research in step 2 is what should move the values.

Choose the amp with the top-level `selectedAmp` parameter (module `""`), by
name: `{"module": "", "key": "selectedAmp", "value": "PR12"}`. All amp modules
exist in every preset, so **any template can produce any amp**.

For **note-timed delay** ("dotted eighth", "quarter-note slapback"), compute
milliseconds from the tempo with `packs/timing.py` and write `delay/delayTime`.
Don't use the sync-note selector — its mapping is unknown, and ms is exact. Same
for tremolo: use `tremoloRate` in Hz. See
[selectors-and-timing.md](../../reference/selectors-and-timing.md).

## 4. Pick a template

- Default to `samples/Example_Clean_PR12.xml` — IR-free, portable, ships with
  the repo.
- One of the user's own presets is a fine template too, especially if it already
  uses the amp you want. Run `show.py` on it first.
- Either way, **set `selectedAmp` explicitly** unless you have confirmed the
  template already has the value you want.

## 5. Write the spec, preview, apply

Build the spec JSON, then always `--dry-run` first and show the user the change
list before writing. See [preset-spec.md](../../reference/preset-spec.md).

Pass `--strip-irs` so the result is portable — see
[cab-and-irs.md](../../reference/cab-and-irs.md).

## 6. Install and report

Write the preset into the user's preset folder and tell them how to load it —
see [installing.md](../../reference/installing.md).

Then report:
- which **template** you cloned and which **amp** you selected
- what **research** the tone is based on, with links
- anything you set **outside a declared range**, and why
- any **unconfirmed selector** the tool warned about

## 7. Bank what you learned

If the research turned up something reusable, append an entry to
`packs/<id>/tone.md` under "Mapped tones" — amp, key settings, and the source
link. That file is append-only and makes the next run better.
