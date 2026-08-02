# Tone knowledge — Tone King Imperial MKII

Use this pack for vintage clean, edge-of-breakup, blues, classic-rock lead,
spring-reverb, and tremolo sounds. Recipes are starting points: stack the
layers that match the role, then adjust input gain, amp volume, cabinet balance,
and output gain for the actual guitar and arrangement.

The control roles below follow the Tone King Imperial MKII manual. Numeric
anchors come from aggregate distributions across the installed factory preset
library; no factory preset content ships with the pack.

## Value convention

- `fraction` controls use `0.0`–`1.0`.
- `metered` controls use the native value declared in the manifest, such as dB,
  milliseconds, seconds, or frequency.
- switches use `true` / `false`, or the plugin's own two labels — `"Active"` /
  `"Inactive"`, `"On"` / `"Off"` — which is what `show.py` displays for them.
- selectors accept their displayed member names, such as `"Lead Channel"`,
  `"Ribbon 121 E33"`, or `"1/8D"`.

All 94 writable controls are mapped to published Audio Unit parameters. The 159
additional numeric state fields are deliberately read-only `internal` values:
they remain available for inspection and lossless round-trip but recipes never
write them.

## Amp channels

The Rhythm channel has volume, bass, and treble controls. Start with
`amp/rhythm-clean`; raise `rhythmAmpVolume` toward the
`amp/rhythm-edge` setting when the part should respond to pick strength and the
guitar volume control. Keep bass conservative in a full arrangement and use
the cabinet or graphic EQ before making extreme amp-EQ moves.

The Lead channel has volume, tone, and Mid-Bite. Tone is the main high-frequency
contour. Mid-Bite is not merely a mid-EQ knob: increasing it tightens bass,
reduces the frequency extremes, adds gain, and creates an upper-mid emphasis.
Use `amp/lead-crunch` for controlled rhythm and `amp/lead-saturated` for a more
compressed, forward lead.

The attenuator offers 0, -3, -9, -15, -24, and -36 dB positions. HFC compensates
for high-frequency loss when attenuation is engaged and has no effect at 0 dB.
`amp/attenuated-lead` demonstrates the intended pairing. Treat attenuation as
part of the amp feel, then use output gain for final preset level matching.

The amp spring reverb and post-amp reverb are separate. `ampReverb` gives the
amp-style spring sound; the `reverb/*` layer supplies a later, more controllable
space. Tremolo is active when depth is above zero; speed and depth are both
normalized controls. `amp/tremolo-clean` provides a restrained vintage start.

## Practical anchors

These medians describe active factory-preset settings, not limits or targets:

| Context | Useful center |
|---|---|
| Rhythm channel | volume 0.42, bass 0.34, treble 0.55 |
| Lead channel | volume 0.57, tone 0.56, Mid-Bite 0.64 |
| Compressor on | compression 0.50, blend 0.87, volume 0 dB |
| Overdrive 1 on | overdrive 0.42, volume 0.50 |
| Overdrive 2 on | overdrive 0.34, volume 0.50 |
| Delay on | mix 0.14, feedback 0.14 |
| Post reverb on | mix 0.21, decay 2.18, HPF 395, LPF 4938 |
| Two-cab baseline | both levels -12 dB, position 0.50, distance 0.0 |

Input level changes how early either channel breaks up. Start with
`output/unity`; use `output/hot-pickup-pad` when a high-output guitar makes every
amp recipe too dirty, or `output/low-output-lift` when a quiet pickup does not
drive it enough. Match loudness last with `outputGain`, and use
`output/headroom` when stacked gain or ambience clips.

## Intent → which recipes to stack

| Intent | Suggested stack |
|---|---|
| Balanced clean rhythm | `amp/rhythm-clean` + `compressor/gentle-glue` + `cab/balanced-57-ribbon` + `reverb/compact-room` + `output/unity` |
| Tight country or funk clean | `amp/rhythm-clean` + `compressor/fast-snap` + `cab/bright-dynamics` + `delay/short-slap` + `output/unity` |
| Edge-of-breakup rhythm | `amp/rhythm-edge` + `drive1/off` + `eq/tight-low-end` + `cab/balanced-57-ribbon` + `reverb/compact-room` |
| Blues or restrained classic-rock lead | `amp/lead-crunch` + `drive1/clean-push` + `eq/lead-focus` + `cab/warm-ribbons` + `delay/mono-quarter` + `reverb/lead-space` |
| Saturated vintage lead | `amp/lead-saturated` + `drive2/saturated-lead` + `compressor/off` + `cab/warm-ribbons` + `delay/stereo-dotted-eighth` + `reverb/lead-space` + `output/headroom` |
| Vintage tremolo clean | `amp/tremolo-clean` + `compressor/gentle-glue` + `cab/single-57` + `delay/off` + `reverb/off` |
| Wide ambient clean | `amp/rhythm-clean` + `chorus/subtle-width` + `delay/stereo-dotted-eighth` + `reverb/ambient` + `output/headroom` |

Avoid stacking both overdrives by default. Add one source of gain, compensate
level, and only add the second if the musical role calls for another saturation
stage. Likewise, choose either amp spring or a prominent post reverb first; two
large ambience sources can obscure the pick attack quickly.

## Adjustment vocabulary

- **Cleaner / more dynamic:** lower channel volume or input gain; turn drives
  off; reduce compressor blend or compression.
- **More breakup:** raise channel volume or input gain; add
  `drive1/clean-push` before reaching for a high-gain drive recipe.
- **Tighter lead:** raise Mid-Bite gradually, trim the first EQ bands with
  `eq/tight-low-end`, or lower drive bass.
- **Brighter:** raise Rhythm treble or Lead tone moderately, move a cab mic
  position toward the brighter side by ear, or choose `cab/bright-dynamics`.
- **Darker / rounder:** lower tone or treble, choose `cab/warm-ribbons`, or add
  `eq/soft-top`.
- **More sustain:** add `compressor/sustain`, raise amp or drive gain, then
  re-check output headroom.
- **More space without losing attack:** increase delay before reverb, or raise
  reverb pre-delay while keeping the wet mix modest.
- **Less mud:** lower amp bass, reduce drive bass, increase delay/reverb high-pass
  filtering, and cut low EQ bands before reducing all ambience.

## Verification boundary

The manifest establishes writable mappings, kinds, ranges, and selector labels
against the running Audio Unit. The musical settings here are conservative
starting points supported by the manual and aggregate factory-preset behavior;
they are not transfer-function or distortion measurements.

**Nor can they be, yet.** This plugin produces no audio at all in a headless
render — `scripts/au_silence_check.swift` reports a peak of 0.0 for it and
0.55 for Morgan under identical code — so nothing here has been characterised by
listening to it. The cause is unconfirmed; see
[docs/measuring-against-the-plugin.md](../../docs/measuring-against-the-plugin.md).
Read that as "not established" rather than "not needed", and audition the result
with the target guitar, level-matched in context.
