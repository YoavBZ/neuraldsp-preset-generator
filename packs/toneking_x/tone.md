# Tone knowledge — Tone King Imperial MKII X

The instrument is the one in [`../toneking/tone.md`](../toneking/tone.md): read that for
the amp, the channels and the pedals. Recipe ids are the same, so anything it says about
`amp/rhythm-clean` or `dry/toneking` holds here. What differs is how values are written.

## Value convention

- Knobs are `rotation` controls, `0`–`100`, as the plugin displays them. The original
  pack writes the same knobs as `0.0`–`1.0`.
- Cab position and distance stay `fraction` controls, `0.0`–`1.0`.
- `metered` controls use the native unit in the manifest: dB, ms, Hz, BPM, semitones.
  Pan is −50..50 here (−1..1 in the original).
- Delay Sync replaces the original's two controls. Use `"Free"` for `delayTimeL`/`R`,
  `"DAW"` for the sync notes, `"Tap"` for a tap tempo.
- The channel is `ampParameters/ampChannel`, `"Rhythm"` or `"Lead"`.

## What does not carry over

- **Measurements were made on the original plugin.** The starting presets, drive curve
  and EQ basis have not been measured here. Every amp control on Vintage Trem and Squishy
  Lead holds the same value in both editions, but both presets store a higher Output
  Gain in X (9.9 and 4.7 dB against 0), so level match by ear.
- **`match` and the listening page do not render this edition.** They need a preset for
  the original plugin; a preset made here can be read, edited and written only.
- **The EQ's on/off is `eqParameters/sectionActive`.** X has no second EQ switch, so the
  original's `eqActive` has no counterpart.
