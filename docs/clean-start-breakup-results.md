# Do the clean starting presets stay clean? (2026-10-21)

The user heard the Hotel California "clean start" (the PR12 clean baseline, made dry)
break up on the open Em of the rebuilt `chords` riff. So the three clean baselines in
`generate` step 4, and the PR12 template, were checked on that riff: dry (`--recipe
dry/<amp>`, as `generate` makes them), at the riffs' level (-23.7 LUFS).

## By ear

One listener, the four presets in fresh plugin processes on one page
(`audition.py --riff chords`), not blind:

| start | heard |
|---|---|
| PR12 clean baseline (`Royally Ambient`) | clean; less bass, more treble than the template |
| PR12 template (`samples/Example_Clean_PR12.xml`) | clean; more bass, less treble |
| SW50R clean baseline (`Pedal Platform Clean`) | not clean |
| AC20 clean baseline (`Low-Watt Americana`) | not clean |

## Measured

THD (harmonics 2-10) of a 196 Hz sine at the riff's peak level (-4.6 dBFS), one
render per preset. A steady sine at the peak drives harder than a strummed chord, which
reaches its peak only on the attack, so these overstate what a chord gets; read them as
an order.

| start | THD |
|---|---|
| PR12 template | 4% |
| PR12 clean baseline | 20% |
| AC20 clean baseline | 22% |
| SW50R clean baseline | 34% |
| crunch start (Hotel California, PR12), for reference | 41% |

A second measure, the part of a render a 12-dB-quieter render cannot explain by a gain
per 50-ms window, did not separate the presets the way the ear did (both PR12 starts
read cleanest, but SW50R and AC20 sat near the crunch start without a compressor to
explain it), so it is not used.

## What changes

`generate` step 4 marks the SW50R and AC20 clean baselines as breaking up on a full
chord: for a part documented as fully clean it prefers PR12, and calls a SW50R or AC20
start edge of breakup. The baselines themselves stay: they were chosen because they
measured closest to real clean recordings, which can carry slight breakup
([clean-baseline-results.md](clean-baseline-results.md)), and the by-ear check behind the
clean starts covered PR12 only
([starting-preset-listening-results.md](starting-preset-listening-results.md)).

Next, when render slots are free: screen the factory SW50R and AC20 presets for ones
that stay clean on the chord riff, and put the closest few in front of the listener.

## Also heard

Faint crackle as each chord fades, through all four presets, most clearly through PR12.
The dry riff has none (heard in four variants: as shipped, without denoising, with
downstrokes only, and one untouched EGFxSet note), so it happens in the amp models. The
leading guess, crossover distortion of a push-pull power amp growing as the level falls,
is untested; the test is a fading sine and a single untouched note through the cleanest
PR12 preset.
