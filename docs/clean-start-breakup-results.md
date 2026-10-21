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
breaking up on the open Em alone a week earlier (riff-library-plan.md, "Rebuilt").

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

## What changes

`generate` step 4 records the check beside the clean baselines, and says what it means:
on a part documented as fully clean, a SW50R or AC20 clean start may break up on hard
strums, and the report should say so. These are the factory presets' settings
(`Pedal Platform Clean`, `Low-Watt Americana`), not the amps' headroom: the skill's own
guidance that SW50R has the most headroom stands, and the amp is still chosen from
research. The baselines stay: they were chosen as closest to clean development recordings
([clean-baseline-results.md](clean-baseline-results.md)), and the blind check of starting
presets on real clean parts (block X, amps rotating PR12, SW50R and AC20) preferred the
clean start to the crunch start 4 of 5 times
([starting-preset-listening-results.md](starting-preset-listening-results.md)). That
those recordings carry slight breakup themselves is an inference, not measured.

Next, when render slots are free, cheapest first: the same check on the SW50R and AC20
baselines with their volume (or input) lowered, and with a compressor; only then a
screen of other factory presets.

## Also heard

Faint crackle as each chord fades, through all four presets, most clearly through PR12.
None is audible in the dry riff (heard in four variants: as shipped, without denoising,
with downstrokes only, and one untouched EGFxSet note), so it appears after the DI: in
the amp models, or a compressor raising the decays enough to expose something inaudible
dry. Untested. The test: a fading sine and one untouched note through the PR12 template,
with its compressor on and off.
