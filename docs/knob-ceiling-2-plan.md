# Knob ceiling 2: pedals and time effects (Tone King to follow): plan (ML plan 2026-10, step 2)

Declared 2026-10-14, before any render. Revised the same day after an independent review
(`tmp/knob-ceiling-2-plan-review.md`, local): approved with changes, all folded in below. It is
step 2 of [`research/ml-plan-2026-10.md`](research/ml-plan-2026-10.md). Development data, the
true DI (the measure DI), no model.

## Why

Knob ceiling ([results](knob-ceiling-results.md)) searched the amp knobs, input gain and mics,
then the EQ, on Morgan. It left out the pedals, the time effects and Tone King, and input gain
hit its −20 dB floor in 47 of 144 runs (the plugin allows −24). This step measures what the
pedals and the time effects add, with the same machinery.

**Deviations from the ML plan's step 2,** dated 2026-10-14:
- **Tone King (its stage 3) is deferred to an amendment.**
  - Neither existing renderer can search it. `AudioUnitRenderer`'s record-state path edits the
    plugin's boot state, not a dry preset. `ToneKingPresetRenderer` plays a preset but refuses
    edits.
  - Tone King also stores switches as "0"/"1", which `knob_search`'s switch dims can't flip.
  - It needs its own renderer, a check against the stored start distances
    (`tk-baseline/distances-dev.json`, within 0.005 log), and its own search space. All of that
    is declared before it renders.
- **Stage 1 continues from knob ceiling's EQ-stage best,** rather than searching the EQ jointly
  from scratch. The ML plan's "the EQ is searched together with the core knobs" is read as
  "the EQ stays in the searched space", which it does. The staging question (joint against
  staged) is not answered here.

## Shared

- **Parts:** knob ceiling's 24 scored parts (Honey is refused by the judge), 14 bands, asserted in
  code. Cross-half, both directions.
- **Code:** `learn/knob_ceiling.py`'s `knob_search`, `judge` and `Renderer` (with `isolate=True`).
  The new code is in `learn/knob_ceiling2.py`, with tests. `knob_search` gains one option,
  `canon`: a function applied to every setting before it is cached or rendered. Settings that make
  no sound (the knobs of an effect or pedal that is off) are set to fixed values, so trying them
  costs nothing and can't win on noise. With `canon=None` it is unchanged, which a test checks.
- **Rendering:**
  - Morgan, reused processes, `isolate=True`;
  - **4 processes** while step 1 trains;
  - paused 03:00–04:15 by step 1's watchdog;
  - `setopt no_bg_nice`;
  - a disk guard stops if free space falls below 31 GB.
- **The repeat check:** each search's first render repeats a stored distance. It stops above
  0.005 (log).
- **Statistics:**
  - **Per cell:** part × direction, with each direction's own best amp. The cell's number is the
    held-half log ratio.
  - **Per part:** the mean of its two directions. The amp can differ between directions; that is
    stated.
  - **Reported:** band-weighted and part-weighted means, a 90% band-clustered t-interval
    (`confirm_run.stats`), bands better, leave-one-band-out, and clean and crunch separately.
  - **Seeds:** 20261014 for stage 1, 20261015 for stage 2.
- **Reading** (knob ceiling's rules, descriptive; every searched number is a lower bound):
  - **"a lot":** band-weighted ≤ −0.10 with most bands better;
  - **"little":** ≥ −0.04, read as undecided;
  - **otherwise:** in between.
  - For these increments, convergence and the repeat floor are reported beside the reading.
- **Judge-only:** stage 1 is read by the judge only, which is stated. The listening guard covers
  stage 2.
- **Ledger:** `knob-ceiling-2`, entered before any render.

## Stage 1: pedals and wider input gain (about 9.6k renders, plus about 0.4k of controls)

- **Cell:** each part's best amp, chosen per direction **on the search half**: the amp whose knob
  ceiling EQ-stage result is lowest on that direction's search half.
- **Start:** knob ceiling's EQ-stage best for that amp and direction
  (`cells/<part>/<amp>/EQ-<search>.json`).
  - **Off pedals get neutral knobs:** a pedal that is off has its knobs set to declared neutral
    values. That doesn't change the sound, since it is off.
  - **The neutral values:**
    - compressor: compression 0.4, level 0.5, mix 0.5;
    - drive 1: drive 0.3, level 0.5, tone 0.5;
    - drive 2: gain 0.3, level 0.5, bass 0.5, treble 0.5.
  - So a pedal switched on starts from these values, not from the factory's leftovers.
- **Search space:** the core knobs (input gain now −24 to +12 dB, the amp's knobs and switches,
  cab positions and distances, the right mic's level and switch), the amp's 9-band EQ and filters,
  and the pedals:
  - compressor: on/off, compression, level, mix, release;
  - drive 1: on/off, drive, level, tone;
  - drive 2: on/off, gain, level, bass, treble.
  - **The mics are held** (knob ceiling already searched them), so `knob_search` has no
    categorical dim and runs its main and final stages only.
  - The section switches are held on.
  - `canon` sets an off pedal's knobs to the neutral values.
- **Budget:** 200 renders per direction.
- **Readings:**
  - **(e):** the stage-1 result against its start, knob ceiling's EQ stage;
  - **(f):** stage 1 against M, same amp and direction.

  Also reported:
  - which pedals end up on;
  - the share below −20 dB input gain;
  - at-limit shares;
  - the convergence.
- **Where the gain comes from (ablation, about 0.2k renders):** stage 1's best is rendered twice
  more, per cell:
  - once with the pedals reset to the start's;
  - once with input gain clamped to −20 dB.
- **The zero-cost baseline:** knob ceiling's EQ stage gained a median −0.002 on the held half
  between renders 50 and 100, so extra renders alone add little.
- **The realistic control, re-run on stage 1's space** (6 cells, as in knob ceiling's amendment
  2):
  - **The "recording":** the start with 5 settings moved, played with the raw DI. Two pedal
    knobs plus 3 core settings, with one pedal switched on.
  - **The search:** from the start, scored with the measure DI.
  - **Reported:** the gap closed and the shortfall. Descriptive; it states how loose stage 1's
    lower bound is.

## Stage 2: time effects (about 4.8k renders)

- **Start:** stage 1's best per cell and direction, with every time effect off (as in all
  starts). Sync is forced free: `delay/delaySync` "0", `tremolo/tremoloSync` "false".
- **The declared "on" values** (`canon` sets an off effect's knobs to these):
  - **reverb:** mix 0.2, decay 1.8 s, pre-delay 20 ms, low cut 100 Hz, high cut 6 kHz;
  - **delay:** mix 0.2, feedback 0.25, time 350 ms, low cut 100 Hz, high cut 4 kHz;
  - **tremolo:** depth 0.4, rate 4 Hz;
  - **the amp's spring:** `pr12Reverb` 0.2 with `pr12Dwell` 0.5, or `sw50rReverb` 0.2; AC20 has
    none.
- **Search space:** each effect's on/off switch and, while it is on, its knobs.
  - **Log scales:** decay 1–6 s, delay time 60–800 ms, tremolo rate 1–10 Hz, the cuts.
  - **Not searched:**
    - the doubler: the judge and the listening page fold stereo to mono, which makes it a comb
      filter;
    - tremolo level and delay tape drive, held at the start's values.
  - Tempo-locked delay times aren't offered: the search can't know the song's tempo, and
    listening decides.
- **Budget:** 100 renders per direction.
- **The margin:** "wet" counts as different from "dry" only if stage 2's best beats stage 1's on
  the search half by at least **0.005** (log). Otherwise the cell's stage-2 result is dry.
- **Listening decides; the judge barely hears effects.** The blind page has its own builder
  (`learn/build_effects_listening.py`), held half, record vs dry vs wet.
  - **Cells, among those whose stage-2 result is wet:**
    - the 4 largest judge gains, each in the direction with the larger held gain;
    - 2 drawn with `random.Random(20261015).sample(sorted(remaining), 2)`, direction A→B;
    - 2 that turned on a reverb or delay, if not already chosen.
  - The wet option's letter is balanced as in knob ceiling's sitting 2.
  - **The claim tested** is "judge-searched effects help the match". Most references are dry
    stems.
  - **The reading:**
    - wet chosen on at least 7 of 8 trials: judge-searched effects help;
    - 5 or 6 of 8 is chance about 36% of the time, so it is reported as undecided;
    - 4 or fewer: they don't.

## Order

1. This plan, after review, and the ledger entry.
2. The code and tests.
3. Message the product session.
4. Stage 1 and its ablation, with its realistic control alongside (it gates nothing).
5. Stage 2, then the listening page (the user answers).
6. An audit of the results, then `docs/knob-ceiling-2-results.md`.

## Budget

| Item | Renders |
|---|---|
| Stage 1 | 24 × 2 × 200 = 9.6k |
| Stage 1's ablation | about 0.1k |
| Stage 1's realistic control | 6 × about 200 = 1.2k |
| Stage 2 | 24 × 2 × 100 = 4.8k |
| **Total** | **≈ 15.7k** |

The running total with knob ceiling's 70k is about 86k, against the 200k limit. Tone King's
amendment adds about 4.8–7.2k.

## Stated limits

- **Knob ceiling's limits:** the true DI, development only, within-part, one take.
- **Stage 1's gain is incremental over knob ceiling's EQ stage,** and judge-only.
- **The judge barely hears time effects,** so stage 2 rests on one listener.
- **Tempo-locked delay and tremolo phase are out of reach** of this search.

## Amendment 1 (2026-10-15): stage 2 searches each effect on its own

Made after stage 2's first cells (8 are kept in `stage2-v0-discarded/`). Those cells showed only a search-coverage defect, not a
reading, and they are discarded (`stage2-v0-discarded/`).

- **The defect:** with every effect off at the start, `canon` makes an off effect's knobs free
  no-ops, so the only real moves were the 4 on/off switches. Switching an effect on at its
  declared value scored slightly worse than dry everywhere. So no effect's knobs (e.g. a lower
  mix) were ever explored, and each search ended after 4–5 renders.
- **The fix:** each effect (reverb, delay, tremolo, and the spring where the amp has one) is
  switched on alone, at its declared "on" values, and its knobs are searched by `knob_search`,
  24 renders each (seed 20261015 + the effect's index).
  - **The cell's result:** the best of dry and each effect's best, on the search half.
  - **Wet** only if it beats dry by 0.005 (log), as before.
  - Effects aren't combined. This is stated as a limit.
- **The budget:** 1 + 24 × 4 = 97 renders per direction (73 on AC20), about 4.3k in all.
- **Unchanged:** the listening page and its reading.

## Amendment (2026-10-15): no 03:00–04:15 pause

The "nothing runs 03:00–04:15" rule (ML plan section 5) has no reason behind it. It began as a
one-night request from the ML session on 2026-10-10, to keep the product session's renders clear
of an evaluation. The product session then carried it into its plans, and the ML plan copied it
from there. No backup or system job uses that window. The user asked for the pause to be dropped
if it wasn't required, so the watchdog is stopped, and from now on jobs run through the night.
Fold 0 was paused once (2026-10-15, 03:00–04:15), with no effect on the recipe.
