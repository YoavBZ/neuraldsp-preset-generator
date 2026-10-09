# Frozen timing-confidence control

2026-10-08. **FAIL, independently verified with zero mismatches.**
The exact procedure, code, tests and review were committed at `3ae9976` before
accessing the twelve saved raw-DI arrays. All 156 declared constructed cases
completed in 10.78 seconds, with complete valid primary coverage and no exceptions.

Verified counts:

| Constructed arm | Accepted | Rejected |
| --- | ---: | ---: |
| Identity with known delay | 36 | 0 |
| Reversed polarity with known delay | 36 | 0 |
| Zero-phase lowpass with known delay | 30 | 6 |
| Memoryless tanh distortion with known delay | 16 | 20 |
| Different performance | 0 | 12 |

The gate fails because seven accepted tanh-distorted cases have full-estimate
lag error greater than the declared one-sample tolerance. Six errors are +3 samples
and one is +2, across three scale performances (Bb, C, Db); polarity is correct
throughout. The errors are estimate minus imposed truth. Lowpass/tanh rejection
alone does not fail the gate. Every identity and polarity case was accepted;
every mismatched-performance case was rejected. Every rejection first failed the
sharpness requirement. The method's confidence rules therefore do not guarantee
the declared one-sample timing accuracy under this constructed distortion.
This does not establish that timing caused any earlier model or native-pair failure.

Fresh-context Schrodinger independently derived all 156 cases before reading
primary numerical evidence. **All 856 checks pass**, with zero failures or
mismatches; the maximum float discrepancy is **3.56e-14** against the fixed absolute
1e-8 comparison tolerance. Every hash, identity, integer lag, polarity, confidence
predicate, returned field, first-error reason and gate agrees. Progress matches
the result exactly, and captured stdout matches progress bytes.

## Evidence

- [Frozen procedure](di-alignment-control-plan.md) and
  [independent design/code review](research/di-alignment-control-review-2026-10-08.md).
- [Full result](EVIDENCE-OUTSIDE-GIT.md).
- [Independent numerical verification](EVIDENCE-OUTSIDE-GIT.md),
  [report](research/di-alignment-control-verification-2026-10-08.md) and
  [implementation](research/di-alignment-control-independent-2026-10-08.py).
- [Source/environment/case provenance](di-alignment-control-provenance.json).
- [Input artifact and loaded DI identities](di-alignment-control-inputs.json).
- Original run: `tmp/di-alignment-control-20261008/`; log:
  `tmp/di-alignment-control-20261008.log`.

All estimates, confidence predicates, first rejection reasons, returned fields,
known-truth errors and construction hashes are retained. All 43 source pins and
twelve input file hashes remained unchanged during verification. Actual P was
checked through its saved evidence rather than rerun; numerical libraries are
shared, but no project numerical functions were called by the independent verifier.

This uses twelve performances from one guitar/player; 156 transformations are not
156 independent recordings. Positive priors are deliberately correct, and the
twelve negatives do not establish a general false-acceptance rate. No native
microphone audio, model/average, inference, rendering, training or reserved material
was accessed. The native pilot remains closed; its thresholds are not changed.
No native alignment, neural transfer, preset-ranking or product claim follows.
Commit-before-first-access is supported by the guard, revision and timing evidence,
and main's attestation; there is no independent access audit. Original preparation
QC/oracles are inherited verified evidence.

Next: separately review a fixed-render score-sensitivity control at declared
positive and negative offsets. It will test whether two/three-sample coordinate
errors change the previously verified learned-versus-simple result. This measures
post-inference score sensitivity only. It will not select a best lag, alter native
calibration rules, reopen the failed panel or justify longer training.

Pedroza et al., Guitar-TECHS, CC BY4.0, https://zenodo.org/records/14963133.
