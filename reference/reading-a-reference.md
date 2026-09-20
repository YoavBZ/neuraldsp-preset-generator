# Reading a measured reference

Shared reference for the `generate` and `match` skills: how much a fingerprint is
worth, which parts of it to believe, and the two ways it is quietly wrong.

A fingerprint is always internally consistent. It will describe *something*
accurately. The failures are not noisy numbers — they are a confident,
well-formed description of the wrong thing.

## Measure the right twenty seconds

`--excerpt` does not find the guitar. It ranks windows by a **broadband**
activity gate, which answers "is there sound here" and nothing else. On a
mastered, continuously-playing track almost every frame passes, every window
scores the same, and the first one wins by default.

This is measured, not hypothetical. On a five-minute mastered ballad, 98% of
frames were active and 29,642 of about 30,255 candidate windows tied at the top,
so the "chosen" window was the bass intro. The guitar was four minutes later.

The tool now says so — `excerpt_policy: uninformative_activity`, with a caveat —
but the remedy is yours to apply:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/fingerprint.py" REFERENCE.wav \
  --regime mix --excerpt-start 264 --text
```

**Before using any numbers, check the excerpt plausibly contains a guitar.** Two
cheap tests, both reported in `--text`:

| | implausible | the dark jazz tone this threshold was set against |
|---|---|---|
| spectral centroid | below 250 Hz | 372 Hz |
| −6 dB extent | tops out below 500 Hz | 737 Hz |

A fingerprint that fails either is flagged, and the flag means *find a different
window*, not *this is a dark tone*. Even a neck-pickup jazz sound with the tone
rolled off carries harmonics well past 500 Hz; a bass, a pad, an intro or a fade
does not.

Prefer a section with **one stable tone**. Averaging a clean verse, a crunch
chorus and a lead break together produces a target that is none of them.

## What each regime is worth

`REGIMES` in `analysis/fingerprint.py` carries the confidence; it is not
decoration, and it should change how hard you push a value.

| regime | confidence | what you are actually measuring |
|---|---|---|
| `paired_di` | 1.00 | a reamp of the exact DI you have. Sample-for-sample evidence |
| `isolated_stem` | 0.85 | an original multitrack guitar track |
| `separated_stem` | 0.55 | source separation's guess at the guitar |
| `mix` | 0.35 | the guitar plus everything else, through a master chain |
| `probe` | 1.00 | a controlled render of a known chain, for validation |

Choose the most conservative regime the provenance actually supports. Two
recordings of the same song are not `paired_di`; two takes of the same part are
not either.

## Where a stem lies, and where a mix lies

The single most useful thing to know about an unisolated reference, and it comes
from comparing both kinds of the same master band by band:

> **A separated stem is trustworthy in the midrange and lies at both extremes.**
> It strips low end and rolls off the top.
> **A full mix is the opposite: its extremes are the rhythm section and the
> cymbals, not the guitar.**
> Where the two agree, believe it. Where they disagree, believe neither and fall
> back on what the amp and cab actually do.

Measured on one track, stem against mix, as deviation from each source's own peak:

| band | stem | mix | reading |
|---|---|---|---|
| 1.6–2.5 kHz | −2 | −5 | peak is **real**, both agree |
| 1 kHz | −6 | −9 | dip is **real**, both agree |
| 4 kHz | −9 | −10 | sits below the peak in both |
| 250 Hz | −42 | −5 | separation artifact; there is no hole |
| 6.3 kHz | −31 | −17 | the stem understated the top by ~10 dB |
| 63–160 Hz | −41 | −6 | bass and kick in the mix; **neither is usable** |

Practical consequences:

- **Never take amp bass or a high-pass from a mix.** Below roughly 250 Hz you are
  looking at the bass guitar and the kick.
- **A mix's high end is inflated** by cymbals and air. So if the *mix* is still
  20+ dB down at 4–6 kHz, the guitar alone is at least that dark — closing a
  low-pass on that evidence is safe in a way it is not on a stem.
- **On a stem, distrust the low end and the time effects.** A search fitting a
  stem will spend its budget on frequencies the separator removed, and will
  switch delay and reverb off because the tail was stripped.
- The midrange is what both agree on, and it is where the tone lives.

## Measurement moves values; it does not identify a rig

A fingerprint tells you where this recording sits. It does not tell you what amp
made it, and no amount of confidence changes that. Choose the topology — amp,
channel, drive stage, time effects — from research into how the part was
recorded, then let the measurement move the values inside it.

Corollary: a measured number that disagrees with a documented rig is usually the
arrangement, not a discovery. A 4.5 s reverb tail measured off a ballad with a
string section is the string section.

## Confidence is not a number to average

Every optional field carries its own confidence, and a missing measurement is not
zero. `delay_ms` at confidence 0.18 beside "no delay repeat was detected above
the noise" is **not** weak evidence of a 97 ms delay; it is no evidence of any
delay. Read the caveats as part of the measurement, not as a footer.

See also [preset-spec.md](preset-spec.md) for writing the values this produces.
