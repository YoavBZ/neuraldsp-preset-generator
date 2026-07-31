# Open questions

What the manifest does **not** know, why, and exactly how to close each gap.

Close one, delete its section, and update the corresponding test.

---

## 1. A second preset format needs a value decoder

`format/parser.py` reads and rewrites any Neural DSP preset losslessly — that
generalises, and is now measured across **681 factory presets from four
plugins**, every one of which round-trips byte for byte.

`format/structured.py` does **not** generalise. It models one named key per
printable value, which is how Morgan, Archetype Nolly X and Archetype Plini X
are all encoded. Tone King Imperial MKII uses a later encoding:

- numbers are raw IEEE-754 doubles introduced by `01 09 04`, not text
- parameters are a flat list of `PARAM` records carrying `id` and `value`
  fields, so 259 parameters share 7 key names instead of having their own

The two are related: because the structured layer expects printable values, the
bytes of a double that happen to fall in ASCII get read as text. The exponent
bytes of `120.0` are `5e 40` — `^@` — which is how the first draft of this pack
ended up with a parameter named `^@presetNameProp`.

### What supporting it would take

A value decoder in `format/`, keyed off the marker byte, plus a structured layer
that can identify a parameter by a field inside a record rather than by its key.
That is a real change to the format layer, not a new pack, and nothing currently
needs it — the user owns Morgan and Tone King, and Morgan is fully supported.

Until then `bootstrap_pack.py` refuses both shapes with a diagnosis rather than
drafting a plausible-looking manifest that is silently wrong. That refusal is
covered by `test_binary_valued_format_is_refused_not_drafted` and
`test_record_shaped_format_is_refused_not_drafted`, both using synthetic
fixtures — factory presets are Neural DSP's content and are not committed. See
[NOTICE.md](../NOTICE.md).

---

## 2. Two selectors have no member names

`cabParameters/leftRoomMicType` and `cabParameters/rightRoomMicType`. The plugin
accepts 0, 1 and 2 and silently rewrites anything higher to 0 — that much is
measured — but this is one of the two controls that publishes no strings at all
(they appear in the Audio Unit as `R3` and `R6` with blank labels), so the names
cannot be read programmatically.

This is a small gap: the bound is known, so a wrong value can no longer be
written, and only the human-readable names are missing.

### How to measure

```bash
python scripts/probe.py --param cabParameters/leftRoomMicType --values 0-2 \
  --out-dir ~/Library/Audio/Presets/Neural\ DSP/Morgan\ Amps\ Suite/User
```

Load each, read the room mic control, write the three names into a new `enums`
table in `packs/morgan/manifest.json`, and point both parameters at it. Delete
the `needs_confirmation` flag and the note. Two tests need updating when you do:
`test_room_mics_are_a_different_control` and
`test_unconfirmed_selector_warns_but_writes` — the second uses this parameter
precisely because it is the last unknown selector left.

---

## Closed

All four of the original questions have been answered. Three were closed by
measuring against the running plugin rather than by reading the UI or listening
— both of which were the plan of record here, and neither of which turned out to
be necessary. The method, and its limits, are in
[measuring-against-the-plugin.md](measuring-against-the-plugin.md).

The fourth — *does the format layer generalise to a second plugin?* — was
answered by running it against 681 factory presets from four plugins. The answer
is "the byte layer does, the structured layer doesn't", which is why it left a
narrower question behind rather than disappearing. The factory presets were
there all along, in `/Library/Audio/Presets/Neural DSP/`, not the per-user
directory this repo had been looking in.

- **Eight metered parameters had no declared range.** All eight now have one,
  read from the plugin's published parameter info and confirmed from the other
  side by writing an absurd value and reading back what the plugin clamped it
  to. The same sweep caught four ranges that were already declared and *wrong*:
  the three `*EQLpf` minimums (1 kHz, not 20 Hz) and `tremoloRate` (0.15–15 Hz,
  not 0.05–5).
- **Three switches had unverified directions.** All three settled, and one was
  backwards: `sw50rTrebleBoost` moves the control the plugin publishes as *Bass
  Emphasis*. The config reference was right and the stored key name — the
  evidence this file argued was better — was wrong. No recipe had ever set it,
  so nothing shipped inverted.
- **Six selectors had no member names.** Three had full tables read out of the
  plugin (`delaySyncNote`, `tremoloSyncNote`, `delaySync`); the other three
  turned out not to be selectors at all (`ac20Power` is a knob, both `*CabPan`
  are signed numbers).
- **No pack had been bootstrapped from a second plugin.** Now done for three.
  Archetype Nolly X (170 parameters) and Archetype Plini X (141) draft cleanly,
  which is the claim this question was really asking about. Tone King is the
  counter-example, and is question 1 above.

## Why an undeclared range is not left as a guess in the meantime

A declared range with no source is indistinguishable from a measured one once
it is in the file, and it would silently overrule the user. Leaving the value
undeclared is honest about what is known; `UNIT_FLOOR` catches the
arithmetically impossible without pretending to know the plugin's limits.

That the `*EQLpf` and `tremoloRate` ranges were both wrong — one sourced to the
config reference, one to `observed-endpoints` — is the argument for this rule
rather than against it. A range is only as good as where it came from, which is
why `range_source` is required and why the test suite enforces it.
