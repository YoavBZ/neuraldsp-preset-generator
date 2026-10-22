# Do the clean starting presets stay clean? (2026-10-21)

The user heard the Hotel California "clean start" (the PR12 clean baseline, made dry)
break up on the open Em of the rebuilt `chords` riff, played alone. So the three clean
baselines of `generate` step 4 and the PR12 template were checked on that riff: dry
(`--recipe dry/<amp>`, as `generate` makes them), at the riffs' level (-23.7 LUFS).

The riff is a hard case by design: assembled note by note, every chord equally loud, and
its open Em (six strings, four open) is the chord that broke the PR12 baseline up first.

## By ear

One listener, the four presets side by side on one page (`audition.py --riff chords`),
in fresh plugin processes, not blind:

| start | heard |
|---|---|
| PR12 template (`samples/Example_Clean_PR12.xml`) | clean; more bass, less treble |
| PR12 clean baseline (`Royally Ambient`) | clean beside the others; less bass, more treble |
| SW50R clean baseline (`Pedal Platform Clean`) | not clean |
| AC20 clean baseline (`Low-Watt Americana`) | not clean |

The PR12 baseline is borderline: clean beside two presets that break up more, but heard
breaking up on the open Em alone four days earlier (2026-10-17) (riff-library-plan.md, "Rebuilt").

## Measured

Two measures, one render or two per preset, in fresh processes:

| start | linearity residual | THD on a sine |
|---|---|---|
| PR12 template | -19.0 dB | 4% |
| PR12 clean baseline | -17.7 dB | 20% |
| AC20 clean baseline | -11.3 dB | 22% |
| SW50R clean baseline | -11.1 dB | 34% |
| crunch start (Hotel California, PR12), for reference | -9.6 dB | 41% |

- **Linearity residual:** the riff rendered at its level and 12 dB lower; what the loud
  render keeps after subtracting the quiet one scaled by its best gain per 50-ms window,
  relative to the loud render. Slow gain changes fit away; distortion at the riff's
  level is left. It groups the presets as the ear did (the two PR12 starts near -18 dB,
  SW50R and AC20 near -11 dB, 6 dB apart).
- **THD:** harmonics 2-10 of a 196 Hz sine at the riff's peak (-4.6 dBFS), measured after
  the cab and EQ, so a brighter preset reads higher. A steady sine at the peak drives
  harder than a strummed chord. It puts the PR12 baseline beside AC20 (0.9 dB apart)
  and only the template clearly clean.

Both PR12 presets run their compressor; the SW50R and AC20 baselines do not. A compressor
ahead of the amp tames chord attacks, so part of the split may be the compressor rather
than the amp.

## Turned down, or compressed (same evening)

The same linearity measure on the SW50R and AC20 clean baselines, dry, with their amp
volume lowered, or with a compressor in front (the PR12 baseline's settings: mix 59.7%,
compression 50.3%, level 66.7%), and then by ear on the chord riff (same listener, not
blind):

| start | linearity residual | heard |
|---|---|---|
| SW50R as shipped (`sw50rVolume` 35.2) | -11.1 dB | not clean |
| SW50R, volume 25 | -13.3 dB | |
| SW50R, volume 15 | -19.6 dB | clean |
| SW50R + compressor | -20.8 dB | clean |
| AC20 as shipped (`ac20Volume` 30) | -11.3 dB | not clean |
| AC20, volume 20 | -12.6 dB | |
| AC20, volume 10 | -20.5 dB | clean |
| AC20 + compressor | -17.3 dB | tiny cracks, almost clean |

So the breakup comes from the presets' volume: turned down, both play this riff clean, about
where the PR12 template sits (-19.0 dB). That says nothing about the amps' headroom (any amp
is clean turned down far enough; SW50R still broke up at 25), and knob positions do not
compare across amps. The compressor confound above is partly answered: SW50R with a
compressor and no volume change also played clean.

PR12 was swept the same way, for the next check (2026-10-22): `pr12Volume` 35, 25 and 15 read
-21.4, -26.6 and -30.5 dB against the shipped baseline's -17.7 and the template's -19.0 (one
render pair each, fresh processes, the chord riff). 35 is the highest of these that reaches
the template; the grid is coarse.

## What changes (0.7.117; superseded for SW50R in 0.7.119, see the end of this section)

`generate` step 4: on a part documented as fully clean, the SW50R start gets `sw50rVolume`
15 and the AC20 start `ac20Volume` 10, and the report says so (it plays quieter; `outputGain`
makes up the level). Volume rather than a compressor: it is the amp's own control, both
reached clean, and the compressed AC20 still cracked a little. The skill's headroom guidance
(SW50R has the most) was not tested here, and the amp is still chosen from research. Parts not documented as fully clean keep the presets
as they are.

The baselines themselves stay: they were chosen as closest to clean development recordings
([clean-baseline-results.md](clean-baseline-results.md)), and the blind check of starting
presets on real clean parts (block X, amps rotating PR12, SW50R and AC20) preferred the
clean start to the crunch start 4 of 5 times
([starting-preset-listening-results.md](starting-preset-listening-results.md)). Whether
the turned-down starts are also closer to real clean recordings is not tested: lower volume
shifts an amp's tone too.

Checked next by ear on real clean parts ([results](clean-start-volume-listening-results.md)):
AC20's turned-down start held, SW50R's was reverted, PR12 stays.

## Also heard: crackle on the decays

Faint crackle as each chord fades, heard first through all four presets, most clearly
through PR12. What it is not:

- **The riff:** none in the dry riff (four variants: as shipped, without denoising,
  downstrokes only, one untouched EGFxSet note).
- **Crossover distortion:** a 196 Hz sine fading from the riff's peak toward -60 dB over 6 s
  (measured in windows from -4 to -54 dB) through the PR12 template: THD falls steadily with level (4.2% to 0.1% with the compressor on, 18.5%
  to 0.0% off) and never rises as the level falls.
- **The compressor alone:** one untouched note through the PR12 template is clean with
  the compressor on and off.

Most likely, the PR12 clean baseline's own slight breakup as the chords ring down (one
listener, by ear, not blind; not measured on the decays). On the chord riff, re-heard, the
PR12 template was clean with its compressor on and off, and the PR12 baseline crackled a
little either way; the first hearing had heard some through all four presets, the
template included. The turned-down SW50R and AC20 starts had none. The two tests above ran
on the template, not the baseline.
