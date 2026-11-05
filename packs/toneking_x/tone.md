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
  Lead holds the same value in both editions.
- **Output Gain has no fixed conversion.** X's value differs from the original's on all
  124 factory presets both editions hold: 4.8 dB higher on average, from 0.8 lower to
  13.8 higher (9.9 and 4.7 against 0 on the two baselines). The `output/*` recipes write
  the original's numbers, so `output/unity` on Vintage Trem is about 10 dB under the
  factory level. Level match by ear.
- **Chorus depth and rate look crossed.** Each key moves the control of its own name in
  both plugins, yet those 124 presets hold X's rate at the original's depth and X's depth
  at the original's rate. On the original the labels hold: a 440 Hz tone at rate 90%, depth
  20% wobbled at 6.7 Hz, and at rate 20%, depth 90% at 2.0 Hz (two renders, 2026-11-05). X
  rendered silence through our host, so its side is unmeasured: the conversion may have
  crossed the values, or X's knobs may be wired against their labels. The `chorus/*`
  recipes follow the labels. Copying a chorus from an original preset by hand may need
  the swap.
- **`match` and the listening page do not render this edition.** They need a preset for
  the original plugin; a preset made here can be read, edited and written only.
- **The EQ's on/off is `eqParameters/sectionActive`.** X has no second EQ switch, so the
  original's `eqActive` has no counterpart.
