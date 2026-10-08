# Development rank calibration: independently verified

Computed 2026-10-08 after the reviewed declaration/code were committed at `79136bf`.
All 57 calibration synthetic checks passed before execution. Actual computation
completed successfully through the approved helper. Independent recomputation agrees
on all 651,209 scalar fields with zero discrepancies (maximum rounding difference
4.44e-16), covering all 22 outer folds, 220 inner folds and 242 prior audits. The
reviewer derived results before opening production output and imported no project
code. Provenance, commit-before-run timing and exact archive decompression agree.

Evidence: [independent verification](set3-rank-calibration-verification.json).

Full audit: [losslessly compressed output](set3-rank-calibration.json.gz), with the
original retained at `tmp/set3-rank-calibration-20261008.json`. Compression only changes
storage; decompressing restores the exact experiment JSON. The log is
`tmp/set3-rank-calibration-20261008.log`.

## Result

Neither band set passes the predetermined follow-up heuristic. Calibration improves
on the B-trained prior-only constant, but does not show the required improvement on
the unrestricted net chooser with the same all-null fallback:

| Band set | Paired effect vs B-trained prior | Vs net with same fallback | Joint-win share | Follow-up |
|---|---:|---:|---:|---|
| recording | −0.208782 | 0.000000 | 0.121212 | no |
| union | −0.192638 | 0.000000 | 0.136364 | no |

Effects are medians of paired band-median log ratios; negative means smaller measured
distance. Joint wins require beating both comparators, with bands equally weighted
and every original part in the denominator. All 33 required comparisons are positive
and present. Calibration and the fair net baseline each use the same prior fallback
on one all-null part. The historical net without fallback remains incomplete and
descriptive; its missing part cannot supply a claimed learning gain.

Inner validation chooses alpha=0.5 for all 11 recording-band outer folds; union uses
0.5 on ten folds and 0.75 on one. Calibration agrees with net on 20 of 33 choices under
each band set, so median zero does not mean all choices or scores are identical. It
also has median zero versus the restricted alpha=1 endpoint. No blending benefit or
broader validation is established. Sign-flip sensitivity statistics versus net are
0.5/1.0, versus prior 0.023438/0.023438; overlapping folds and repeated development
use make these exploratory heuristics, not calibrated inference.

## Interpretation and next step

Close this particular blend. Do not tune its
grid/prior/features or select favorable subsets after results. This procedure did
not meet the declared development improvement criteria; it does not rule out all learned
ranking or justify more waveform training.

A separate [next question](set3-cross-amp-diagnostic-plan.md) is whether choosing across the existing three Morgan amp
menus helps the product's any-amp objective. Current research has mostly evaluated
each amp separately. That check needs its own declaration, positive controls and
independent review before computation. It does not require expanding knobs or
spending the reserved set. Keep the product and frozen network unchanged meanwhile.

Heavier-tone listening and fresh reserved confirmation remain required for any changed
method. No reserved scores/audio were read for this calibration experiment.
