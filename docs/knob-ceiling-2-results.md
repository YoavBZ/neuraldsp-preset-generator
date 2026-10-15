# Knob ceiling 2: pedals and time effects: results (ML plan step 2, 2026-10-15)

Run under the [plan](knob-ceiling-2-plan.md) and its amendment 1 (each effect searched on its
own). Morgan only; Tone King stays deferred to an amendment. Development data, the true DI (the
measure DI), no model. Every searched number is a lower bound.

- **Scope:** 24 scored parts, 14 bands, both directions: 48 cells in each stage.
- **Renders:**
  - stage 1: 200 per cell;
  - stage 2: up to 97 per cell (actual 70–97, by amp);
  - the ablation and the realistic control.
- **Repeat check:** at most 5.2e-5 (log), against the 0.005 limit.
- **Data:** `~/ndsp-presets/learn/knob-ceiling-2/` (`result.json`, `control.json`,
  `stage1/`, `stage2/`).

## Stage 1: pedals and wider input gain (judge only)

Held-half log ratios, clean and crunch together (n = 24 parts, 14 bands), with 90%
band-clustered intervals.

| Comparison | Mean [90%] | Band-weighted | Bands better |
|---|---|---|---|
| **(e) stage 1 vs knob ceiling's EQ stage** | **−0.023** [−0.033, −0.013] | −0.028 | 13/14 |
| (f) stage 1 vs the best menu preset M | −0.341 [−0.458, −0.224] | −0.377 | 14/14 |
| stage 1 vs K_M (knobs from M) | −0.101 [−0.152, −0.050] | −0.126 | 13/14 |

- **Reading (e): "little" (≥ −0.04), so undecided by the declared rule.**
  - The gain is small but consistent: 23 of 24 parts are better, every leave-one-band-out mean
    lies between −0.019 and −0.027, and clean (−0.022) and crunch (−0.027) agree.
  - The zero-cost baseline (−0.002) covered only 50 more renders, against stage 1's 200, so
    part of (e) may simply be more search. The ablation below puts about half of it on the
    pedals.
- **Where it comes from (ablation):**
  - **Pedals:** resetting them to the start costs +0.010 [0.005, 0.016] (crunch +0.025, clean
    +0.006). So the pedals carry about half of (e), mostly on crunch. One cell (First Offering
    GTR 1, direction B) was refused by the judge after the reset and is dropped (47 cells).
  - **Input gain:** clamping it to −20 dB costs +0.001, so the wider range adds nothing. Only
    5 of 48 cells went below −20 dB.
  - **Pedals switched on, of 48 cells:** compressor 27, drive 1 10, drive 2 12.
- **Realistic control** (6 cells: a known setting with 5 moved knobs, one pedal switched on):
  - **Gap closed:** 0.67–1.03, median about 0.93.
  - **Shortfall:** −0.04 to 0.73. The loose cells were all Drag Me Down: SW50R 0.73 (where the
    search never switched drive 1 back on), PR12 0.22, AC20 0.10.
  - So stage 1's lower bound is usually close, but on some cells it is loose by a lot.

## Stage 2: time effects

- **Wet cells:** 14 of 48 beat dry by the 0.005 margin on the search half: reverb 5, delay 5,
  amp spring 3, tremolo 1.
- **Judge, held half,** stage 2 against stage 1: −0.010 [−0.022, +0.002], with 7 parts better,
  2 worse and 15 tied. The total is small because most cells stay dry; on some delay cells the
  judge's held gain is large (Prodigal −0.10 and −0.12, Blind Spots −0.15 and −0.09, log).

### Listening (one listener, blind, 8 trials, held half)

Answers: `1B 2B 3B 4B 5B 7A 8B`. Trial 6 had no answer: the listener heard another guitar in the
record (see the note below).

| Trial | Why chosen | Effect | Judge held gain (wet − dry) | Picked |
|---|---|---|---|---|
| 1 | reverb or delay | reverb | −0.001 | dry |
| 2 | top | reverb | −0.178 | **wet** |
| 3 | random | reverb | −0.012 | dry |
| 4 | top | delay | −0.592 | **wet** |
| 5 | random | reverb | +0.044 | dry |
| 6 | reverb or delay | delay | +0.310 | no answer |
| 7 | top | delay | −0.542 | **wet** |
| 8 | top | spring | −0.019 | **wet** |

(The column is the raw judge-distance difference, wet − dry, on the held half; negative means
wet is closer.)

- **The declared reading:** wet on 4 of the 7 answered trials. Had trial 6 been answered wet,
  that would be 5 of 8, "undecided"; otherwise "they don't".
- **The rule asked the wrong question,** which the user pointed out (2026-10-15). It asked
  whether judge-searched effects help across the board. But where an effect barely changes the
  sound, the two versions are near-identical, and a dry pick there is no evidence against
  effects. The right question is whether an effect helps when the judge says it clearly does.
- **The reading used (the user's, accepted as evidence):**
  - On the 3 trials with a clear judge gain (2, 4, 7: held −0.18 to −0.59), the listener picked
    wet every time.
  - On the near-ties (1, 3, 8) and the judge loss (5), the picks split, as expected when the
    two versions sound alike.
  - So the ear agrees with the judge where the judge's gain is clear.
- **A layout caveat:** the wet letter alternated with the trial number (A on odd trials, B on
  even), and 6 of 7 answers were B.
  - Picking by position would give the same answers except on trial 7, where wet was A and was
    picked.
  - The listener replayed every clip several times, especially close pairs, and trusts the
    picks; the user accepts them.
  - The builder's letter rule (least-used letter first) caused the alternation. Later pages draw
    each trial's letter at random.
- **Off is a correct answer.** Many records have no time effect (most references here are dry
  stems), so there an effect can't bring the sound closer, and leaving it off is right. A dry
  result is never read as a failure of the search or of a model; only an effect that is on
  without a clear gain, or off where the record clearly has one, counts as an error.
- **Decision:** effects stay in the search and are kept only when they clearly help. The keep
  margin of 0.005 (search half, log) lets near-ties through; trials 3 and 8 passed it by a
  hair. A higher margin is to be declared before its next use. Later listening pages (random
  letters) can refine it.

### Note: trial 6's record

The listener heard another guitar in Gym Hours GTR 1's record, and the lead seemed to be
missing. An audit found the following:
- **The files are right.** The record is bit-identical to the session's "GTR 1 Amp M80" track,
  and the DI to "GTR 1 DI". Their notes match: pitch-class similarity 0.94–1.00 per 0.5 s.
- **GTR 2 bleeds into the GTR 1 mic:**
  - 13–17 dB down in half A;
  - 3–6 dB down from 7 s, that is, in half B.
- **The "missing lead"** is GTR 2's higher line, which correctly isn't part of this record.
- **Step 3** carries a declared sensitivity check for this part (song-settings amendment 3).

The same audit checked the 5 parts with a low DI–record envelope correlation. All five are
fine: their record envelopes are nearly flat from compression, and notes and onsets match.

## Stated limits

- Judge-only for stage 1. One listener for stage 2.
- Within-part, one take, development data.
- Effects weren't combined.
- Tempo-locked delay is out of reach.
- Tone King not yet searched.
