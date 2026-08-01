# Tone knowledge — Morgan Amps Suite

How to choose settings for this plugin. The **recipes** in `recipes.json` are the
starting points; this file is how you decide which to reach for and how to adapt
them. Parameter facts (kinds, units, ranges, selector members) live in
`manifest.json`.

Values here follow the project convention: **knobs are percent of rotation
(0–100)**, metered controls in their native unit. See
`reference/preset-spec.md`.

## The three amps

### PR12 (`pr12Amp`, `selectedAmp: "PR12"`)
A **1960s blackface Fender Princeton**, rebuilt with a bigger power supply,
tightened low end and a 12″ speaker — so more bass, headroom and punch than a
real Princeton. 12W class AB, 2×6V6, three-spring tube reverb.

- **Reach for it:** clean rhythm, country, blues cleans. The default clean platform.
- **Range:** sparkly clean → edge-of-breakup. It's 12 watts; past ~55–60% volume
  it starts to sag and grit up, which is the point.
- **Knobs:** `pr12Volume`, `pr12Treble`, `pr12Bass`, `pr12Reverb`, `pr12Dwell`.
- **Dwell is the trick.** Morgan added it to the Princeton circuit specifically so
  you can run a high reverb mix without washing out. Want wet but defined? Raise
  `pr12Reverb`, keep `pr12Dwell` moderate.

### AC20 (`ac20Amp`, `selectedAmp: "AC20"`)
Built on the **Normal channel of a Vox AC30** — not Top Boost — and voiced
deliberately **darker** than a Vox, keeping the chime and growl without the
ice-pick top end. 20W.

- **Reach for it:** jangle pop, British invasion, indie rhythm, British crunch.
- **Range:** chimey clean → classic British crunch.
- **Knobs:** `ac20Volume`, `ac20Cut`, `ac20Bright`, `ac20BassTreble`, `ac20Power`.
- **`ac20Cut` runs backwards.** It's the Vox power-amp Cut: **higher = darker.**
  Don't reach for it expecting a treble control.

### SW50R (`sw50rAmp`, `selectedAmp: "SW50R"`)
The **Dumble Small Special** — a mid-60s blackface-flavoured voice with unusual
clarity and string-to-string definition. High headroom, parallel three-spring
tube reverb. 50W.

- **Reach for it:** smooth singing lead, blues lead, polished clean lead,
  high-headroom rhythm. **This is the amp for "singing lead".**
- **Range:** loud cleans → smooth break-up. It has far more headroom than the
  other two.
- **Knobs:** `sw50rVolume` (preamp gain — this is what breaks up),
  `sw50rLevel` (master, adds no gain), `sw50rTreble`, `sw50rMid`, `sw50rBass`,
  `sw50rReverb`, `sw50rBright`, `sw50rTrebleBoost`, `sw50rInputMode`.
- **Mids do the singing.** `sw50rMid` around 60–68% is where the sustained lead
  voice lives.

> Earlier notes in this repo called SW50R a Vox-style chime amp in AC30
> territory, good for Brian May and AC/DC. That was wrong, and it mattered — it
> pointed lead requests at the wrong amp. Corrected against
> [Morgan's own description](https://www.sweetwater.com/store/detail/SW50RHead--morgan-amps-sw50r-50-watt-high-headroom-tube-head-with-reverb).

## Intent → which recipes to stack

A preset is layers. Pick one recipe per layer, then adapt.

| Intent | amp | compressor | drive | eq | delay | reverb | output |
|---|---|---|---|---|---|---|---|
| Clean rhythm | `pr12-clean` | `subtle-clean-sustain` | `off` | `warm-clean-rhythm` | `off` | `spring-ambience` | `clean-rhythm` |
| Edge of breakup | `pr12-saggy-breakup` or `ac20-jangle` | `subtle-clean-sustain` | `drive1/solo-boost` | `natural-flat` | `off` | `small-room` | `edge-of-breakup` |
| Classic-rock crunch | `ac20-classic-rock-crunch` | `off` | `drive1/classic-rock-crunch-push` | `natural-flat` | `off` | `small-room` | `crunch-rhythm` |
| Singing lead | `sw50r-singing-lead` | `lead-smoothing` | `drive1/singing-lead-push` | `lead-focus` | `classic-lead` | `large-lead` | `lead` |
| Blues lead | `sw50r-singing-lead` or `pr12-saggy-breakup` | `lead-smoothing` | `drive2/thicker-blues-lead` | `lead-focus` | `classic-lead` | `spring-ambience` | `lead` |
| Wide stereo lead | `sw50r-singing-lead` | `lead-smoothing` | `drive1/solo-boost` | `lead-focus` | `big-stereo-lead` | `large-lead` | `big-stereo-lead` |
| Jangle / chime | `ac20-jangle` | `subtle-clean-sustain` | `off` | `natural-flat` | `subtle-slapback` | `spring-ambience` | `clean-rhythm` |
| Tremolo clean | `pr12-clean` | `subtle-clean-sustain` | `off` | `warm-clean-rhythm` | `off` | `spring-ambience` | `clean-rhythm` |

Cab: `single-mic-focused` is the safe default. Use `two-mic-fuller` for clean
rhythm that needs body, `two-mic-wide` for lead.

Tremolo clean also wants `tremolo/subtle-amp-pulse`. Don't enable tremolo unless
the part actually calls for it.

**These are starting points.** The whole value of the skill is adapting them to
the song — if you hand back an unmodified stack, you've just renamed a factory
preset.

## When the user says…

The graphic EQ bands are 65, 125, 250, 500 Hz, 1, 2, 4, 8, 16 kHz — `EQBand1`
through `EQBand9`, in dB. Naming the frequency beats naming the band number.

- **"more reverb"** → `reverb/reverbMix` up 10–15 points. For a spring-tank
  character use the amp's own reverb knob instead. If it gets washy, that's what
  `pr12Dwell` is for.
- **"tighter low end"** → drop the live amp's bass a few points, raise
  `reverbLowCut` and `delayLowCut` (Hz), and cut 125 Hz / 250 Hz (`EQBand2`,
  `EQBand3`) before you touch amp bass hard.
- **"more presence" / "needs to cut"** → push 1 kHz and 2 kHz (`EQBand5`,
  `EQBand6`) rather than raising treble globally. That's what `lead-focus` does.
- **"harsh" / "brittle"** → cut 4 kHz or 8 kHz (`EQBand7`, `EQBand8`), or lower
  `EQLpf`. On AC20, *raise* `ac20Cut`.
- **"warmer"** → drop treble, lower `reverbHighCut` and `delayHighCut`.
- **"muddy" / "woolly"** → cut 125/250 Hz, raise `EQHpf` to 80–90 Hz, and check
  you haven't got amp bass above ~55%.
- **"more break-up"** → raise the live amp's volume knob. On SW50R that's
  `sw50rVolume`, not `sw50rLevel`. Or engage `drive1`.
- **"cleaner"** → lower amp volume; on SW50R raise `sw50rLevel` and drop
  `sw50rVolume` to keep loudness with less grit.
- **"in time with the track"** → compute ms from tempo, don't use the sync
  selector. See `reference/selectors-and-timing.md`.

## Adjust for the guitar

The source doc was written around a Les Paul, which is a useful worked example
but not the universal case.

- **Humbuckers** (Les Paul, SG, 335): reduce low end before the post effects.
  `EQHpf` 80–90 Hz. Keep amp bass moderate on PR12 and SW50R or it goes muddy.
  Bridge-pickup lead often needs controlled highs — `EQLpf` 7000–8000 Hz.
  Neck-pickup lead: less bass, a little more 2 kHz.
- **Single coils** (Strat, Tele): less low end to fight, so `EQHpf` can sit
  lower (70–80 Hz). Watch 2–4 kHz instead — that's where they get shrill.
  Bridge-pickup Tele into AC20 usually wants `ac20Cut` up a bit.
- **Either way**, clean rhythm needs enough treble/presence not to go woolly.

## Settled: four switches that used to be guesses

These four were unresolved because the source doc and the stored key name
disagreed about what they do. They are now read off the running plugin — each
key was written into a preset document and handed to the plugin to see which
control it moved and what that control is called. See
[docs/measuring-against-the-plugin.md](../../docs/measuring-against-the-plugin.md).

| Control | What it actually is | `true` means |
|---|---|---|
| `sw50rTrebleBoost` | a tilt around 250 Hz — **despite being named Bass Emphasis** | brighter and tighter: −5.5 dB @ 60 Hz, +2.5 dB @ 400 Hz–4 kHz |
| `sw50rBright` | the real brightness switch | +5 dB @ 2.5 kHz, +8 dB @ 6.3 kHz, lows untouched |
| `sw50rInputMode` | the two input jacks | `Low` — the padded input. `false` is `High` |
| `ac20BassTreble` | **Bass Cut**, a two-position voicing switch | the `Treble` position: −15.6 dB @ 60 Hz. A big cut |
| `compressorRelease` | fast/slow release | Fast |

`sw50rTrebleBoost` is the cautionary one, and it took two measurements to get
right. The stored key says *treble boost*. The control the plugin publishes says
*Bass Emphasis* — the opposite — and reading that name alone led this repo to
document it as "ON thickens the low end", which is wrong. Rendering audio
through it settles it: ON **removes** low end and lifts the mids. The key name
happened to describe the sound better than the plugin's own control name did.

The lesson generalises past this switch: a name is a hypothesis. Two names
disagreeing is a signal to measure, not to pick the more authoritative-looking
one. Nothing shipped wrong here only because the recipes deliberately left all
of these alone rather than guess.

`ac20Cut`'s direction is settled by reasoning rather than measurement: it's the
Vox power-amp Cut, so **higher = darker**. Still worth a five-second
confirmation by ear.

## Mapped tones

Add an entry whenever you research a tone — future runs benefit. Record the amp,
the recipes you stacked, what you changed and why, and the source link.

```
- "Wish You Were Here" intro (Gilmour):
  - stack: amp/sw50r-smooth-clean-lead + eq/natural-flat + delay/classic-lead
           + reverb/large-lead
  - changed: sw50rMid 58 -> 52 (less push, it's a clean part),
             delayTime from 1/4 at 63 BPM = 952 ms
  - source: <PG rig rundown URL>
```

_(Empty for now — populate as you generate presets.)_
