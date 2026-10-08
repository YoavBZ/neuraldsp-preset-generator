# Independent phase-control design/code re-review

Verdict: BLOCK

Fresh independent source and synthetic review on 2026-10-09. The four findings
in the preserved first review are repaired in this snapshot. One remaining
failure-retention gap prevents approval of the whole declared procedure.
This is an evidence-schema finding, not a claim that the scientific gate can
incorrectly PASS. No study execution is approved by this report.

## Exact reviewed snapshot

Repository: `/Users/yoavbz/projects/neuraldsp-preset-generator`.
Branch: `codex/song-model-continuation`.
HEAD: `46965737f0e0e094d958fd51466747a9fc7b5b44`.

| Item | SHA256 |
| --- | --- |
| `learn/di_phase_control.py` | `37c6ed06e06d5fdbf11f626809e8f02ab55f1bc10eb35a6388923429eaf19701` |
| `tests/test_di_phase_control.py` | `2b39233b762c7f343d59a84b727b7822378aa806cd979e73dcf90993ec55624c` |
| Whole `docs/di-phase-control-plan.md` | `b9483b27e072d96ee6136999bfc4a673f7653d5613beb7e2387f7c959a4a45f2` |
| Scientific body after `## Frozen design\n` | `2a48950ef318235dc4b31fa4b2020b443c0d2d8b194eade9fd992005d09a834b` |

All four hashes match the NEW `tmp/di-phase-review-snapshot.json`. The runner,
tests and plan are untracked at this HEAD and the declaration is DRAFT, as
expected before administrative declaration and commitment. This review does not
treat those facts as defects. The older task's conjugate-FFT wording was assessed
against the current frozen plan's separate time-domain inverse requirement.

## Blocking finding

**P2 — Coefficient save/hash failures bypass the promised attempted-file and
construction-barrier evidence.**

At `learn/di_phase_control.py:388`–390, `controls` constructs its configuration
and calls `save_arrays(out / "coefficients.npz", {"h": h})`. That call is before
the `try` at line 393. The failed/incomplete construction report is written
only by the `finally` at lines 412–415. No coefficient attempt record is created
before the call or attached to the outer result state.

Consequently, if coefficient saving raises, or if saving succeeds and the
`R.sha(path)` at line 381 raises, execution exits `controls` without entering
its failure-retention block. There is no `construction-controls.json`, no
coefficient attempted filename in retained result metadata, and no returned
coefficient archive manifest. `execute` at lines 540–549 retains the generic
exception and INCONCLUSIVE result, but its state contains the constant CONFIG,
not this coefficient attempt/configuration record. A hash failure can leave a
successfully written coefficient NPZ on disk with no corresponding metadata.

This conflicts with `docs/di-phase-control-plan.md:229`–231: attempted NPZ
filenames must remain in metadata on saving/hashing failure. It also leaves the
construction-stage failure without the promised barrier/configuration evidence.
The disk-failure caveat at line 238 does not resolve a hash-only failure while
subsequent JSON writes still work. The source establishes this path; I did not
inject an additional test or modify the frozen tests.

Required repair: create coefficient attempt metadata before saving, and include
coefficient creation/save/hash in a failure-retaining block that can write an
incomplete, failed construction report even when no successful coefficient
manifest was returned. Retain the attempted filename and error; retain the full
member/file manifest when available. Preserve INCONCLUSIVE priority and block
all phase inference. Add synthetic coefficient-save and coefficient-hash failure
tests with functioning JSON writes. The hash-failure test should confirm that
the written NPZ remains and its attempt is recorded. No scientific coefficient,
gate, tolerance or original helper change is needed. Freeze and freshly review
the repaired snapshot before declaration/execution.

## Reassessment of the four earlier findings

1. **Independent inverse: repaired.** `inverse_periodic` at lines 246–261 uses
   two SciPy `lfilter` passes on reversed data and no FFT. For numerator
   `[a, 1]` and denominator `[1, a]`, the one-state direct-form recurrence is
   `y[n] = a*x[n] + z[n]`,
   `z[n+1] = (1-a*a)*x[n] - a*z[n]`.
   If a zero-state pass gives final state `q`, periodicity requires
   `z0 = q / (1 - (-a)**N)`. Reversal before and after filtering implements
   `H(z^-1)`, the inverse of this real unit-magnitude periodic allpass. The
   implementation and new plan agree. The no-FFT test at test lines 177–184
   actively forbids NumPy rFFT/irFFT during inversion. Analytic sinusoid and
   periodized impulse tests supply additional mathematical checks. Independence
   is algorithmic; the plan appropriately acknowledges shared numerical hardware
   and floating-point infrastructure.
2. **Baseline prediction schema: repaired for all twelve prediction archives.**
   The phase-owned `baseline_inference` at lines 312–357 records the offset-zero
   attempted filename before inference/save/hash, saves raw and corrected arrays
   plus scalar int64 offset, and uses `save_arrays` for file SHA256 and every
   member's dtype, shape and byte SHA256. Tests at lines 209–239 inspect actual
   synthetic archives and exercise save/hash failures. Exact float32 prediction
   bytes and direct 36 scalar errors remain prerequisites; the errors compare
   against `original["rows"]`, not against an already tolerance-shifted replay.
   This repair does not cover the separate coefficient path identified above.
3. **Partial 108-scalar replay: repaired.** Phase-owned `replay` at lines 264–308
   uses unchanged T scoring/validation and F gate definitions. It writes an
   exclusive attempt snapshot after each case and writes the final complete or
   incomplete barrier in `finally`. The real-wrapper last-take timeout test at
   lines 187–206 preserves eleven completed cases/99 scalars, the twelfth failure
   record, all twelve attempt snapshots, and an incomplete failed barrier.
   No model load follows a failed barrier. Partially computed internal arm
   scores of an interrupted T.scored_row call are not claimed as completed rows.
4. **Final budget expiry: repaired.** `run` at lines 523–526 checks after final
   aggregation. `execute` at lines 536–539 checks before and after successful
   result saving. Post-save expiry moves the provisional result to
   `result-before-final-budget.json` and attempts failure plus authoritative
   INCONCLUSIVE result writes. Tests at lines 329–362 exercise aggregation expiry
   and saving expiry, including preservation of the provisional result and all
   twelve rows. Failure cleanup may continue beyond the deadline without
   restoring PASS. Filesystem failures can still prevent cleanup writes, as
   the plan explicitly states.

## Whole-snapshot scientific and operational checks

- The fixed `a=-0.9`, N=288000, 48000-Hz periodic response has the stated formula,
  complex128 coefficients and exact DC +1/Nyquist -1 endpoints. No outcome-based
  coefficient or tolerance selection was found. The interpretation is limited
  to this artificial phase challenge of dependent development cases.
- Full raw model input is converted to little-endian float32, promoted to
  float64 for phase processing and converted back before unchanged U.infer /
  D.rebuild normalization. Both original saved simple arms receive the same
  forward transform in float64. Fixed target/raw DI and the original 52-sample
  overlap remain enforced. There is no inverse on a prediction, fitted lag/gain,
  new flatref construction or alternate target.
- Inverse, norm, population-standard-deviation and aggregate whole-window
  spectral-magnitude relative errors require finite positive denominators and
  finite errors. Thresholds remain 1e-12, with quantized inverse 1e-6. The tests
  meaningfully reject wrong inverse, nonunit response, corrupted quantization,
  zero denominator and nonfinite data. No pointwise spectral ratio at zero bins
  is used.
- The saved 108-scalar PASS precedes model load; complete twelve exact original
  predictions/direct 36-score PASS precedes phase construction; complete twelve
  construction controls PASS precedes phase inference. The run-level barrier
  tests patch the new phase-owned methods. The actual control test rejects a
  final-case failure while retaining all twelve control archives.
- All twelve phase returns precede experimental validation/scoring. Returned
  malformed/nonfinite arrays are saved before validation and after-call time
  checks. Transformed arms survive inference exceptions. Phase save/hash errors
  stop subsequent calls while their attempted filename remains in outer state.
- Exact twelve-case identities, six cases per group, inherited QC/oracle checks,
  baselinezero prerequisite, three unchanged metrics and paired changes are
  preserved. F.compare retains the original inclusive 10% boundary allowance,
  nine strict wins and positive group medians. Invalidity, drift and budget
  failure take INCONCLUSIVE priority; a valid gate miss remains scientific FAIL.
- The declaration guard binds committed runner/tests/review/scientific body and
  inherited inputs, and refuses DRAFT before inherited guards/assets. Its 14
  disjoint phase dependencies extend 63 inherited pins to 77. Synthetic guard
  tests verify 77 pins/48 artifacts and demonstrate that compact references are
  never followed. Read-only Git diff confirmed U/T/F/P/D are unchanged at HEAD.
- The inherited loader permits exactly the original 48 NPZ identities and six
  members per take. The fixed checkpoint, original CPU prefix/packages, two
  Torch threads/eval, repeated source/HEAD/model/artifact checks, exclusive output
  and alias/hardlink/symlink refusals remain encoded. Inherited guard traversal
  does not call the old broader asset-discovery/training/rendering entry points.
  Import remains inert with respect to study assets and Torch.
- The cooperative 900-second budget begins before guards and includes final
  saving. It cannot forcibly interrupt native/library calls; completed calls
  are followed by checks that prevent an expired successful final disposition.

## Inherited compact evidence

Only source and report metadata were inspected. The compact report records
VERIFIED/PASS, 21246 checks with zero failures, 63 source pins, 48 artifact
identities, 67 primary snapshots, 60 independent rows/archives and 120 passing
member-byte checks. Its independent baseline is complete/passed with 36 scalars.
Metadata joins found zero container-hash mismatches, zero member-hash mismatches,
and zero original zero-offset prediction-byte mismatches against the committed
primary metadata. These are inherited attestations, not fresh payload-byte or
historical runtime observations.

Compressed metadata SHA256:
`53ac147bc2ea2c4a3d54e63b4b52571791fe9b24ec64b28eca644c82abd34100`.
Decompressed compact metadata SHA256:
`30fa2e1554e5e7a4961c316032449a504169ff431a4400d4a23e1c745d0cf873`.
Prior independent verifier source SHA256:
`4ad1bfcd4ff01cf2da2df505853e8c17073c1bb3600f143fac90edb11228a176`.
All match the committed archive manifest. No full report, lossless payload
archive, prediction payload reference or actual waveform/model was opened.

## Test results and limits

All test execution used the original user-owned
`/Users/yoavbz/.codex/bin/neuraldsp-safe pytest`, with
`PYTHONDONTWRITEBYTECODE=1`, `-q -p no:cacheprovider`.

- `tests/test_di_phase_control.py`: **62 passed, 1 skipped**, 1.77 s, exit 0.
  The expected optional Torch normalization test skipped in the helper
  environment, which lacks Torch. No alternate interpreter was used.
- Five targeted inherited test functions, including parametrizations:
  **18 passed**, 0.90 s, exit 0. These were
  `test_all48_barriers_six_member_allowlist_and_exact52_overlap`,
  `test_input_drift_original52_and_activity_rejections`,
  `test_last_baseline_prediction_failure_retains_complete12_blocks_every_shift`,
  `test_all108_replay_failure_blocks_all_network_calls`, and
  `test_baseline36_parity_is_direct_to_archive_not_accumulated_replay_tolerance`
  from `tests/test_di_input_shift_control.py`. These verify the unchanged
  inherited paths; they do not substitute for failure tests of the new wrappers.

The blocker is a source/plan finding absent from the passing suite. No actual
study/model/NPZ/audio access or hashing, actual inference/scoring, network,
plugin, download, training, other agent or Git write was performed. Synthetic
NPZs were created/read only by the authorized pytest tests. This reviewer wrote
only `tmp/di-phase-control-rereview.md`. Main owns repairs, archival,
administration, commitment and any eventual declared execution.

Final source/test/whole-plan/scientific-body hashes and HEAD were rechecked and
still match the entry snapshot. The preserved earlier BLOCK review remains at
`docs/research/di-phase-control-blocked-review-2026-10-09.md`, SHA256
`d9ab0c00442852d4581c842b5bbc71d180c6bdcbb5bd5031986a2e802612a92f`.
