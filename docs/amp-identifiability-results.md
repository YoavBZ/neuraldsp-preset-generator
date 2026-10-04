# Can the judge tell Morgan's amps apart? Recoverable, provisionally

Computed as declared in `docs/amp-identifiability-plan.md`, by
`scripts/amp_identifiability.py` at 4f263bf (rebased as ad25e15, unchanged). The rows
are in `docs/amp-identifiability.json`, without the per-pair distances, which stay
with the run. The `master` column is null on PR12 and AC20 rows: the run stored
SW50R's level there, fixed afterwards in f48b7fb.

**Checked independently.** A fresh-context reviewer re-ran the draws (all 1680 rows
matched) and worked out every target's exact chance of a correct guess from the
distance ranks. The exact values agree with the 200 draws to 0.0004 on average.

## Outcome: recoverable

| | |
|---|---|
| Median of band mean accuracies | **0.72** (chance 1/3); every band above chance, the lowest 0.61 |
| One-sided band sign-flip p | 1/2048, the smallest possible with 11 bands |
| Per amp | AC20 0.76, PR12 0.87, **SW50R 0.52** (gate 0.50) |
| Targets | 1680, none unscored; k 14–17 candidates per amp |

Reported, not deciding:

| Reading | median | SW50R |
|---|---|---|
| The judge's temporal part only | 0.81 | 0.67 |
| Compressor-on presets only (k 8–11) | 0.81 | 0.78 |

## How firm it is

- **The overall separation is solid.** Every band is above chance. Leaving out a band
  or a part barely moves anything. Most confusion runs between SW50R and AC20.
- **SW50R's pass is fragile.**
  - **Mostly one sound.** Three of Neil Zaza's four SW50R presets render identically,
    and the fourth differs by 0.035. All four are identified about 1% of the time and
    taken for AC20 99% of the time, closest to AC20's Default and Clean Canyon Chords.
    They account for about 71% of SW50R's confusion with AC20.
  - **One driven preset.** SW50R's most driven offered preset, Full Bodied Single
    Coils (volume 0.61), scores 0.06.
  - **The rest.** The other 13 SW50R presets score 0.48–0.95.
  - **Which presets are sampled.** Leaving out any one of SW50R's four best presets
    puts it at 0.49–0.50, which fails the gate. Resampling presets gives a 95% range
    of about 0.28–0.75, below 0.5 about 40% of the time.
  - **How the one sound is counted.** The declared weighting counts the Zaza sound
    four times; counting it once gives 0.62, and weighting by family gives 0.58.
  - **How many candidates are drawn.** At 8 candidates per amp, SW50R reads 0.46.
- **Preset settings move this judge about as much as the amp does.**
  - AC20's Default sits 2.58 from AC20's template. Swapping amps between the templates,
    which share mics, EQ and compressor, gives 2.10–2.87.
  - The amp is recovered because a close same-amp preset usually exists among about
    15, not because the amps are far apart.
  - On the templates alone, presets pick their own amp's template 91% of the time
    (AC20), 58% (PR12) and 45% (SW50R, tied with AC20's template).
- **The confounds named in the plan don't explain it.**
  - **Drive:** accuracy barely follows the volume gap (r = 0.10). Where drive is high,
    it pulls the amps together.
  - **Compressor:** it matters within SW50R (compressor-off presets 0.23 against
    compressor-on 0.70), but a differing compressor adds +0.065 log distance against
    −0.25 for the same amp.
  - **Mics, cabs, EQ:** setups are shared no more within an amp than across amps.
  - **What cannot be separated from "the amp":** the amp's built-in cab (the pack has
    no cab-model control), and shared default control values within an amp, which a
    search would remove.

## What it licenses

- **The precondition holds.** The next declared step would be the benchmark: "search
  each amp briefly, keep the judge's closest" against searching one amp, with a refit,
  before the matcher changes. It should report each amp separately, and expect clean,
  compressor-off SW50R voicings and driven ones to be taken for AC20 or PR12.
- **It is provisional.** Cross-amp distances, and SW50R and AC20 renders, are outside
  the range listening validated (clean-to-crunch PR12).
- **Renders only, same DI.** It needs a DI. The product's song-only use has none, and
  the judge does not apply there.
