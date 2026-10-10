# Judge v2: a fixed band set: plan

Declared 2026-10-10, before any v2 re-scoring. It follows the user's decision in the
[closeness review](closeness-review-2026-10-10.md): add a judge version beside the current
one, and adopt it only if the heavy-tone [listening check](heavy-listening-plan.md) agrees.

## Why

- **The current judge is treble-deaf on bass-heavy parts.** It chooses its scored bands
  from the recording's own long-term spectrum (within 30 dB of its loudest band). On a
  dominant low end, the treble drops out of scoring: Ill Fate 1–3 score 7–12 of 64
  bands, and their winners are about 40 dB too bright above 2.5 kHz. Elsewhere, excess
  fizz is nearly free.
- **The first attempt didn't fix it.** The `weighting="hearing"` option still chose bands
  per window, and its A-weighting turned treble down
  ([re-score review](fixed-level-rescore-results.md)).

## The change

`bands="fixed"` in `analysis.aligned.aligned_distance` scores the same mel bands for every
part and candidate: centres from 80 Hz to 10 kHz (55 of 64 bands), with no hearing
weighting. Everything else is unchanged: alignment, level removal, the DI activity mask,
and the recording-derived per-frame floor.

On Ill Fate 1 (SW50R), it scores 55 bands instead of 8. Its winner changes from a bright
lead preset to a dark one, with rank agreement −0.18 against the current judge.

## Re-scoring (reported, no gate)

`learn/rescore.py --judges fixed` on the standing comparisons, under the fixed-level
protocol. Reported beside the current judge:
- the 3 kHz cut against the uncut rebuilt DI, and each against the leave-band-out fixed
  preset;
- the oracle, and the fixed preset against the clean template;
- how many picks change between the two judges.

## Adoption

The listening check decides it. Block 2 (clear heavy pairs) must reach at least 8 of 10
for the judge to stand on heavy material. Block 1 says whether the ear weights the tonal
or the temporal part. Judge v2 is adopted if:
- its picks agree with the listener at least as often as the current judge's, on the
  trials where the two judges disagree;
- and, where no trial separates them, the listening result doesn't contradict it.

Otherwise the current judge stays. This is written before the listener's answers are
seen.
