# Independent final phase-control design/code review

Verdict: APPROVE

Fresh independent review on 2026-10-09 of the frozen candidate, source and
synthetic tests only. I found no remaining blocking inconsistency with the
declared scientific or operational contract. This approves the exact runner,
tests, scientific body and execution barriers identified below. It does not
declare an experimental outcome or replace main's required administrative
declaration, archival and commitment before actual study access.

## Exact reviewed snapshot

Repository: `/Users/yoavbz/projects/neuraldsp-preset-generator`.
Branch: `codex/song-model-continuation`.
HEAD: `46965737f0e0e094d958fd51466747a9fc7b5b44`.

| Item | SHA256 |
| --- | --- |
| `learn/di_phase_control.py` | `73168186ce22e154eb0d62a11a946f937c8bbb43cb76ac105e3b061118d2c9e5` |
| `tests/test_di_phase_control.py` | `260a79acd750bbb4e0f39eb4df74c566ebbc7121a549fdda634b7f49a6f4c4cb` |
| Whole `docs/di-phase-control-plan.md` | `860144129d5fadad8a0a6c6855e207acaec64e8ebdf90f24a9445fa3f20361bb` |
| Scientific body after `## Frozen design\n` | `c353a6b7c0df9aed957b870bfcd0cd9ae862a44318b07f74e8f24c3cd6d5921a` |

All four match the current `tmp/di-phase-review-snapshot.json`. The reviewed
plan is DRAFT and the three candidate files are untracked at this HEAD, as
expected at this stage. Approval applies to these bytes; main may complete the
administration section while retaining the exact approved scientific body.
The later guard binds the declared body hash, source, tests, archived review,
inherited input identity and committed dependency bytes.

## Resolution of the preserved blockers

All four initial findings and the later coefficient failure finding are resolved.

1. **Independent inverse.** `inverse_periodic` at runner lines 246–261 uses
   SciPy `lfilter` on reversed input, without FFT calls. With numerator `[a,1]`
   and denominator `[1,a]`, its recurrence is
   `y[n]=a*x[n]+z[n]`, `z[n+1]=(1-a*a)*x[n]-a*z[n]`.
   The zero-state final value q gives periodic initial state
   `q/(1-(-a)**N)`. Reversing both ends realizes the inverse periodic response.
   This is a separate time-domain algorithm from the forward NumPy FFT.
   Analytic sinusoid and periodized impulse/delay tests check the forward
   transform independently; test lines 177–184 forbid FFT calls during inversion.
   The plan correctly limits this independence to algorithms sharing numerical
   hardware and floating-point infrastructure.
2. **Baseline NPZ schema and attempts.** The phase-owned baseline wrapper at
   lines 312–357 records each offset-zero attempted filename before inference,
   save or hash. Successful archives use `save_arrays` at lines 375–383, with
   file SHA256 and member names, shapes, dtypes and byte SHA256 for raw prediction,
   corrected prediction and scalar int64 offset. Tests at lines 209–239 inspect
   actual synthetic NPZ members and retain attempted filenames/errors on both
   saving and hashing failures. Numerical validation still uses unchanged U/T
   helpers and direct comparison with the original archived 36 network scalars.
3. **Partial 108-scalar replay.** Lines 264–309 save an exclusive snapshot after
   each attempted case and the complete or incomplete final barrier in `finally`.
   The real-wrapper test at lines 187–206 expires on take twelve and retains
   eleven completed cases/99 scalars, the twelfth timeout, twelve attempt
   snapshots and a failed incomplete barrier. Partial internal arm computations
   are not misrepresented as completed case scores. No model load follows failure.
4. **Final budget enforcement.** Lines 537–541 check after final stability and
   aggregation. Lines 551–563 check before and after successful result saving.
   If final saving crosses the deadline, the provisional result is preserved as
   `result-before-final-budget.json`; failure evidence and authoritative
   INCONCLUSIVE `result.json` follow. Fake-clock tests at lines 378–411 exercise
   aggregation and final-save expiry and retain all twelve rows. Cleanup cannot
   restore PASS after expiry.
5. **Coefficient construction/save/hash retention.** Lines 386–430 initialize
   `coefficients_attempt` before panel checking or coefficient work and enclose
   construction, identity generation, saving and hashing within the retained
   construction barrier. Member identity is recorded before file hashing.
   Construction/save/hash exceptions retain attempted filename, constructed
   status, specific error, configuration and an incomplete failed report;
   a full successful archive is retained when available. Tests at lines 273–297
   inject each failure. The hash-failure case opens the already written synthetic
   coefficient NPZ and verifies its retained member identity. No take construction
   follows these failures. The added last-control timeout test at lines 300–319
   also verifies the specific timeout and already saved twelfth controls archive.

The earlier BLOCK reports remain preserved at
`docs/research/di-phase-control-blocked-review-2026-10-09.md`, SHA256
`d9ab0c00442852d4581c842b5bbc71d180c6bdcbb5bd5031986a2e802612a92f`,
and `docs/research/di-phase-control-blocked-rereview-2026-10-09.md`, SHA256
`5cacce35740338c156588525d58d9bb3985ef73544009f677d8b83139fda2aeb`.

## Whole scientific and operational contract

- **Fixed scientific question.** Coefficient `a=-0.9`, N=288000, 48000 Hz,
  complex128 H and exact real DC +1/Nyquist -1 are unchanged. The formula and
  full-window periodic FFT implementation agree with the plan. No coefficient
  search, target selection, fitted gain/lag/polarity, prediction inversion or
  new flatref estimation appears in the execution path. The plan describes an
  artificial periodic phase challenge and its wraparound boundaries, without
  implying a causal cabinet or native transfer.
- **Input conversion and competitors.** Lines 234–243 convert the full original
  raw model input to little-endian float32, promote it to float64 for phase,
  and quantize the forward output back to float32 before unchanged U.infer /
  D.rebuild normalization. Raw amplitude reaches that original normalization.
  Both original saved simple arms receive the same forward H in float64.
  Target and raw DI remain fixed. The inherited loader enforces the unchanged
  52-sample overlap/dtype identity. Finite crop, context, filtering, STFT windows
  and quantization effects are explicitly acknowledged in the interpretation.
- **Construction controls.** Lines 219–225 and 360–372 require finite positive
  denominators and finite relative errors. Float64 inverse, norm, population
  standard deviation, aggregate whole-window spectral magnitude and unit
  magnitude tolerances remain 1e-12; quantized inverse remains 1e-6. Aggregate
  spectral L2 avoids meaningless pointwise ratios at empty bins. Synthetic tests
  reject wrong inverse, nonunit transfer, quantization corruption, zero denominator
  and nonfinite data. Actual constructed arrays are saved before control validity
  checks; last-case failure blocks the barrier just as first-case failure does.
- **Mandatory ordering.** Run lines 519–536 require saved complete108 PASS before
  model load, saved complete12 exact prediction/direct36-score PASS before any
  phase construction, and saved complete12 controls PASS before any phase model
  call. Each barrier raises on failure. Run-level ordering tests inspect saved
  barrier files; real wrapper/control tests exercise partial and last-case failures.
- **NPZ evidence and prediction failures.** The shared serializer supplies full
  file/member manifests for every successful new archive: baseline predictions,
  coefficients, seven-member controls and four-member phase outputs. Attempted
  filenames survive save/hash failures. Phase predictions at lines 447–471 save
  raw returns and three preconstructed arms before validation or after-call time
  checks. All twelve returns precede experimental scoring. No transformed-arm
  generation occurs after a model return. Inference exceptions retain the three
  arms and error metadata; save/hash failure stops further phase calls. Source
  inspection supports original dtype/shape retention for malformed arrays;
  executed tests directly exercise nonfinite returns, inference exceptions,
  saving failure and after-call expiry. No waveform/base64 payload is embedded
  in new JSON evidence.
- **Scoring and decision.** Lines 474–500 use unchanged P.score_prediction with
  original target/raw DI/windows, all three metrics and inherited QC/oracle.
  Paired changes retain wet/flatref absolute and relative degradation,
  waveform-L1/lowband differences and advantage changes. Lines 435–444 require
  exactly twelve unique valid identities with original six-per-group coverage
  and baselinezero PASS. Unchanged F.compare retains the inclusive original
  eight-ulp allowance at 10%, at least nine strict wins and positive group
  medians. Invalidity, missing coverage, timeout or drift takes INCONCLUSIVE
  priority; a valid experimental gate miss is scientific FAIL.
- **Declaration, source and prior evidence.** Guard lines 154–197 refuse DRAFT
  before inherited guards/assets, require committed byte equality and review
  approval, and add fourteen disjoint dependencies to unchanged U's 63 pins,
  yielding 77. Prior metadata checks require VERIFIED/PASS, all21246 checks,
  all60 unique cases, five passing screens, all120 raw/corrected byte checks,
  original12 exact predictions and both replay barriers. Nine scalar arm metrics
  per case are compared within 1e-8. Compact compressed/uncompressed identity,
  seven original report/log identities, five original/archive JSON equalities
  and 67 snapshot identities are checked without following prediction pointers
  or expanding inherited payloads. Synthetic guard tests use invented metadata
  and no prediction NPZ files, and exercise commit/body/review/hash/runtime drift.
- **Exact asset/model scope.** Inspection of unchanged U/T loaders supports the
  exact original48 NPZ allowlist and only six permitted waveform members:
  prepare di/target, render baseline/net_input, infer prediction and saved flatref.
  The original fold2 path and SHA256 are fixed. Original CPU prefix/packages,
  little endian, CPU eval and exactly two Torch threads are enforced. Source,
  HEAD, original48 and model identities are repeatedly checked before critical
  stages and after scoring. Regular-path checks reject aliases, symlinked
  ancestors and hardlinks. No broader inherited discovery, average loading,
  preparation, rendering or training entry point is called. Read-only Git diff
  confirmed U/T/F/P/D remain unchanged from HEAD.
- **Output, budget and cleanup.** Main accepts only the exact fixed CLI/output
  and exclusively creates that directory; aliases and preexisting output are
  refused. Import performs no Torch or study-asset access. The cooperative
  900-second clock starts before guards and covers hashing, loads, construction,
  inference, scoring and final saving. Completed native/library calls cannot be
  forcibly interrupted, but subsequent checks prevent an expired final PASS.
  Guard/run errors retain failure and authoritative INCONCLUSIVE result evidence.
  Failure cleanup may exceed the deadline; filesystem errors can prevent writes,
  so retention is claimed only for files actually written.

## Tests and inherited metadata evidence

All tests ran through the user-owned `/Users/yoavbz/.codex/bin/neuraldsp-safe`
with `PYTHONDONTWRITEBYTECODE=1`, `pytest -q -p no:cacheprovider`.

- `tests/test_di_phase_control.py`: **66 passed, 1 skipped**, 1.71 s, exit 0.
  The optional real-Torch synthetic normalization test skipped because Torch
  is unavailable in the helper environment. No interpreter substitution occurred.
- Ten targeted inherited test functions, including parametrizations:
  **26 passed**, 1.50 s, exit 0. From `tests/test_di_input_shift_control.py`:
  `test_all48_barriers_six_member_allowlist_and_exact52_overlap`,
  `test_input_drift_original52_and_activity_rejections`,
  `test_last_baseline_prediction_failure_retains_complete12_blocks_every_shift`,
  `test_all108_replay_failure_blocks_all_network_calls`,
  `test_baseline36_parity_is_direct_to_archive_not_accumulated_replay_tolerance`,
  `test_infer_boundary_full_raw_level_and_original_float32_conversion`,
  `test_model_loader_cpu_eval_weights_only_hash_before_load`, and
  `test_model_exact_path_hash_nonlink_and_budget`. From
  `tests/test_di_timing_sensitivity.py`:
  `test_actual_scorer_primary_and_l1_use_unchanged_center` and
  `test_unchanged_stronger_gate_boundaries_wins_groups_and_better_simple`.
  These use synthetic arrays/files and mocked model objects, with no actual
  study data or checkpoint access.

Fresh metadata-only inspection of the compact archived verification confirms
VERIFIED/PASS, 21246 checks with none failed, zero failures, 63 source pins,
48 artifact identities, 67 primary snapshots, 60 independent rows, 120 passing
prediction member checks and complete/passed independent36 replay. Fresh hashes
of the permitted compact metadata and verifier source match the archive manifest:

- Compressed metadata: `53ac147bc2ea2c4a3d54e63b4b52571791fe9b24ec64b28eca644c82abd34100`.
- Decompressed metadata: `30fa2e1554e5e7a4961c316032449a504169ff431a4400d4a23e1c745d0cf873`.
- Prior verifier source: `4ad1bfcd4ff01cf2da2df505853e8c17073c1bb3600f143fac90edb11228a176`.

These remain inherited attestations and metadata consistency evidence. I did
not repeat prior numerical verification or observe historical runtime access.

## Scope and limits

This review establishes design/code consistency and the stated synthetic
behavior. It establishes no phase-study numerical result. No actual study
audio/NPZ/checkpoint was read or hashed; no actual inference/scoring, network,
plugin, download, training, agent dispatch or Git write occurred. Synthetic
NPZ reads/writes happened only inside authorized pytest tests. I wrote only
`tmp/di-phase-control-review-final.md`.

The scientific limits remain one fixed artificial periodic challenge on twelve
dependent development takes from one player/guitar and one clean Morgan chain.
It cannot establish real cabinet/native transfer, native failure causation,
general processing diversity, preset ranking, song accuracy or product readiness.
Original full-render/plugin/physical-latency evidence limits carry forward.
Saved source/review/timestamps are not an independent retrospective access audit.
The optional real-Torch check remains unexecuted here; synthetic loader tests
cover CPU/eval/two-thread enforcement without loading actual weights.

Final source/test/whole-plan/scientific-body hashes and HEAD were rechecked and
match the entry snapshot. Existing changes to `docs/README.md`, `docs/ROADMAP.md`,
`docs/di-recovery-plan.md` and `learn/README.md` were not made by this reviewer.
Main owns archival, administrative DECLARED edits, helper commitment and any
subsequent actual run and independent numerical verification.
