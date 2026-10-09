# Fixed Morgan scoring-coordinate sensitivity

2026-10-08. **PASS, independently verified with zero mismatches.**
The reviewed procedure, code, tests and input identities were committed at
`25b3439` before experimental array access. All 108 earlier scalar scores replayed
within the unchanged absolute 1e-8 tolerance before any nonzero shift. All 156
take/offset rows and thirteen screens completed in 39.54 seconds, without exceptions.

Verified results (rounded percentages):

| Common output offset (samples) | Role | Median improvement over better simple arm | Strict wins | Screen |
| --- | --- | ---: | ---: | --- |
| -128 | Diagnostic only | 56.72% | 12/12 | PASS |
| -52 | Diagnostic only | 56.62% | 12/12 | PASS |
| -16 | Diagnostic only | 57.70% | 12/12 | PASS |
| -8 | Diagnostic only | 57.83% | 12/12 | PASS |
| -3 | Required robustness | 57.84% | 12/12 | PASS |
| -2 | Required robustness | 57.84% | 12/12 | PASS |
| 0 | Replayed prerequisite | 57.83% | 12/12 | PASS |
| +2 | Required robustness | 57.81% | 12/12 | PASS |
| +3 | Required robustness | 57.80% | 12/12 | PASS |
| +8 | Diagnostic only | 57.74% | 12/12 | PASS |
| +16 | Diagnostic only | 57.59% | 12/12 | PASS |
| +52 | Diagnostic only | 57.04% | 12/12 | PASS |
| +128 | Diagnostic only | 57.11% | 12/12 | PASS |

All group medians are positive. Only the four offsets -3, -2, +2 and +3 decide
robustness after the zero PASS prerequisite. Wider offsets are diagnostics only;
none was selected or fitted. At each offset the simple competitor is the better
of wet-as-DI and the saved tone-corrected stand-in, at that same offset.

Fresh-context Mendel independently derived and persisted all 108 baseline scalars,
156 rows with paired changes and thirteen screens before opening primary numerical
outputs. **23,734 checks pass, with zero unresolved failures.** The maximum primary
comparison discrepancy is **1.78e-15**; including inherited prerequisite comparisons,
the maximum is **8.26e-12**, both below the unchanged absolute 1e-8 tolerance.
All 53 source pins, 48 input identities and primary artifacts remained stable.
No project numerical functions were imported or called by the verifier.

The established clean Morgan advantage survives the declared common two/three-sample
output-coordinate perturbations on this panel. Their median improvements remain
57.797–57.842%, with twelve wins at each required offset. This narrows the scoring
concern; it does not establish native timing validity or explain earlier failures.

## Evidence and limits

- [Frozen procedure](di-timing-sensitivity-plan.md) and
  [independent design/code review](research/di-timing-sensitivity-review-2026-10-08.md).
- [Full scores, paired changes and screens](di-timing-sensitivity.json).
- [Mandatory 108-scalar replay](di-timing-sensitivity-baseline-replay.json).
- [Source/environment provenance](di-timing-sensitivity-provenance.json).
- [Artifact and loaded waveform identities](di-timing-sensitivity-inputs.json),
  [committed 48-file identity manifest](di-timing-sensitivity-inputs.sha256).
- [Independent numerical verification](EVIDENCE-OUTSIDE-GIT.md),
  [report](research/di-timing-sensitivity-verification-2026-10-08.md) and
  [implementation](research/di-timing-sensitivity-independent-2026-10-08.py).
- Original output: `tmp/di-timing-sensitivity-20261008/`; log:
  `tmp/di-timing-sensitivity-20261008.log`.

This shifts the three saved output arms equally while keeping their targets fixed.
It does not change audio entering the network or measure input-window sensitivity,
arm-specific timing errors, native-chain transfer, native failure causation, preset
ranking or real-song accuracy. Twelve reused same-player performances are dependent
development cases, not independent population evidence or reserved validation.

Original render evidence limits persist: eleven full wet outputs were not retained,
no separate plugin-parameter command transcript exists, and fixed slicing does not
remeasure physical latency. Predictions and six-second QC/oracle identities are
inherited verified evidence. No model, average, raw/native/reserved audio, inference,
rendering or training was accessed. Guard/review/revision evidence and main's
attestation are not an independent access audit.

Next: separately implement and review a known input-shift control, with original
prediction-byte replay before shifted inference. This distinguishes model-input
sensitivity from the output-coordinate scoring question now checked. No threshold
changes, native-panel rescue, repeated spent confirmation or longer training follows
from this scoring-coordinate result.

Pedroza et al., Guitar-TECHS, CC BY4.0, https://zenodo.org/records/14963133.
