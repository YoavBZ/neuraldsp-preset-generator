# Tone knowledge — Tone King Imperial MKII

**There isn't any yet, and that is the honest state of this pack.**

Morgan's `tone.md` exists because someone measured that plugin, argued with the
source documentation, and got several things wrong before getting them right.
None of that work has been done here. This file exists so the tooling has
something to find, and so nobody mistakes silence for "nothing to say".

## What is actually known

- **The format.** 259 parameters read, edit and write correctly, and every one
  of the 135 factory presets round-trips byte for byte. This is the part that
  is solid — see [reference/preset-spec.md](../../reference/preset-spec.md).
- **The parameter names**, straight out of a preset, so they are exact.
- **94 parameters verified against the running plugin**, by writing each key
  into the plugin's own state and reading back which control moved. For those,
  the kind and the plugin's own control name are facts, and 29 carry a measured
  numeric range. This corrected 44 wrong kinds — twenty of them numeric 0/1
  switches that had been guessed as knobs — and confirms 12 selector tables
  from the mapped controls' published labels.
- **The other 161 numeric state keys were not reached by the one-value probe.**
  That is not proof that no control exists: a nudge can be rejected or be a
  no-op. Of those, 155 still have guessed kinds marked `needs_review`; writing
  through one warns, and `show.py` flags it on the way in.
- **Four unreached mode selectors still have unknown members.** And no idea
  which control does what to the sound.

## What that means in practice

Editing an existing preset is reasonable: clone one, change a value you can see
in the plugin, and check the result by ear. The 94 verified parameters can be
written with confidence in the *kind*; the rest warn. Generating a preset from a
description is still not viable — there is no tone vocabulary here to map a
request onto, and no control has been characterised acoustically.

Prefer the user's own presets as templates over the factory ones, and say
plainly that values are being set without a declared range behind them.

## Filling in the rest

Re-run the verification any time:

```bash
python scripts/audit_manifest.py --pack toneking
```

It maps keys to controls through the plugin's own state and checks every
declared range and mapped selector table. What it cannot give you is the member
table of an **unreached selector** or **what any control does to the sound** —
for the latter, `scripts/au_render.swift` and `scripts/spectrum_diff.py` work
against any installed plugin. See
[docs/measuring-against-the-plugin.md](../../docs/measuring-against-the-plugin.md).

Whatever you add, record a `range_source` saying how you checked. This project
has been wrong about a parameter more than once by reasoning from its name, and
the only thing that has ever settled it is a measurement.
