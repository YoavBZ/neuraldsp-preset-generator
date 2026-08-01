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
- **Nothing else.** Kinds are guessed from key names and marked `needs_review`.
  No ranges. No selector members. No idea which knob does what to the sound.

## What that means in practice

Editing an existing preset is reasonable: clone one, change a value you can see
in the plugin, and check the result by ear. Generating a preset from a
description is not — there is no tone vocabulary here to map a request onto, and
the amp's own controls have not been characterised.

Prefer the user's own presets as templates over the factory ones, and say
plainly that values are being set without a declared range behind them.

## Filling this in

The ranges cannot simply be copied from the plugin. It publishes 96 controls
with real ranges to its Audio Unit, but keeps its state as opaque bytes rather
than a document, so the write-a-key-and-see-what-moves probe that verified every
Morgan range does not work here — `scripts/audit_manifest.py --pack toneking`
says so and exits 3. Matching the two lists by name reaches 35 of 259, and name
matching is exactly the kind of evidence this project has repeatedly caught
itself trusting and being wrong about.

So: one parameter at a time, each with a `range_source` recording how it was
checked. `scripts/au_render.swift` and `scripts/spectrum_diff.py` work against
any installed plugin and will answer "what does this control do to the sound"
without needing the state probe at all. See
[docs/measuring-against-the-plugin.md](../../docs/measuring-against-the-plugin.md).
