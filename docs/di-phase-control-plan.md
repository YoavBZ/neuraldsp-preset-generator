# Fixed periodic phase control of the frozen Morgan model

**Declared: 2026-10-09, before computation.** Fresh independent Planck review
approves the exact source, tests, scientific body and execution barriers below.
Synthetic suite: 66 passed, one expected optional Torch skip; 26 targeted inherited
checks also pass. [Approval](research/di-phase-control-review-2026-10-08.md).
Both preceding BLOCK reviews and their repairs are preserved in the research folder.
Only this administrative frontmatter replaces the approved DRAFT; the scientific
body is byte-identical. Commit this reviewed declaration before actual study access.
Main owns execution and fresh independent numerical verification.

<!-- phase-approval
{
  "status": "DECLARED",
  "fresh_independent_review": true,
  "scope": "fixed-periodic-phase-only-a-minus-0.9",
  "source_sha256": "73168186ce22e154eb0d62a11a946f937c8bbb43cb76ac105e3b061118d2c9e5",
  "test_sha256": "260a79acd750bbb4e0f39eb4df74c566ebbc7121a549fdda634b7f49a6f4c4cb",
  "design_sha256": "c353a6b7c0df9aed957b870bfcd0cd9ae862a44318b07f74e8f24c3cd6d5921a",
  "review_sha256": "bfb71cdf765bc9eb99b5109e417990e34ac013e6e7ce9fd704fe21846a887f2b",
  "inputs_sha256": "1c6cde4a6bdaa5ceb71fd43e56a21049cffb2bbd023a359d8f7b44de4f6dc527"
}
phase-approval -->

The design hash covers bytes after `## Frozen design\n`. The archived review and
source/test/input hashes bind the reviewed snapshot; this attestation is not an
independent retrospective audit of execution access. Changes require fresh review.

## Frozen design

This asks whether the existing learned advantage depends on phase processing of
the original clean Morgan inputs. It is a separate bounded challenge of the
original twelve known-clean cases: six chords, six scales, identical original
take identities. All closed native/reserved/timing/input-shift studies stay
closed. No new take selection, retuning, retraining, rerendering, noise/nonlinear
panel, catalog query, audio download, plugin access or checkpoint selection.

The single coefficient **a = -0.9 is chosen now, before study numerics**. It is
neither a sweep nor selected from outcomes. Use exactly N = 288000 samples, six
seconds at 48000 Hz. On discrete rFFT bins k = 0 through N/2 define:

```
H[k] = (a + exp(-j*2*pi*k/N)) / (1 + a*exp(-j*2*pi*k/N))
H[0] = +1 + 0j
H[N/2] = -1 + 0j
phase(x) = irfft(rfft(float64(x)) * H, n=N)
```

This is an **artificial finite periodic unit-magnitude transform**, not a causal
physical cabinet model. The boundaries wrap around the six-second array. Do not
substitute a streaming filter, padding rule, causal startup, approximate FIR,
different FFT length, coefficient, endpoint, or tolerance.

Convert the original full raw `net_input` to little-endian float32, exactly as
the unchanged `U.infer` / `D.rebuild` input conversion would. Promote that converted
input to float64 for phase processing. Convert the transformed input back to
little-endian float32 before frozen inference. Preserve its raw amplitude until
`D.rebuild` applies its unchanged normalization. The original renderer's 52-sample
latency remains in place; the unchanged saved overlap identity is required by
`U.load_inputs`. There is no new delay, inverse transformation of a prediction,
gain fit, polarity choice, lag fit, crop change or scoring change.

Transform both simple competitors coherently using the same H on their original
full six-second saved waveforms: original wet baseline and original saved flatref.
Keep both transformed simple arms in float64 for unchanged scoring. Target and
raw DI are fixed. Do not construct a new flatref or read any average. Phase
transformation and a fixed frequency-magnitude correction commute ideally on
the same discrete full-window representation. The transformed saved flatref is
a declared simple arm; it is not claimed to exactly reconstruct a newly executed
flatref estimation procedure. Finite context, the center scoring crop, reflected
STFT windows, bandpass boundary handling, standardization and float32 conversion
can change scores despite whole-window magnitude conservation.

### Sources and exact access scope

Reuse unchanged `learn/di_input_shift_control.py` (U),
`learn/di_timing_sensitivity.py` (T), `learn/di_morgan_flatref.py` (F),
`learn/di_domain_pilot.py` (P), and `learn/direc.py` (D).
`U.guard(started)` retains its exact 63 inherited source pins. The phase guard adds
14 disjoint committed dependencies: own runner/tests/plan, fresh phase review,
prior input-shift independent verifier, compact verification gzip, verification
archive manifest, verification report, results writeup, and the five original
result/provenance/input/replay metadata archives listed in `ARCHIVES`.

Verify the prior input-shift `VERIFIED` / scientific `PASS`, zero unresolved
failures, all 21246 final checks, all sixty unique cases, five passing screens,
all 120 exact raw/corrected byte comparisons, all twelve original exact predictions,
both replay barriers, original63 source/48 artifact identities and verifier hash.
Recompute its unchanged screen from archived scalar scores and independent scalar
rows, and compare only the nine arm-score scalars per case within absolute 1e-8.
Hash compressed and uncompressed compact verification metadata against its
pinned archive manifest. Check content-reference filenames/member identities and
hashes, without following pointers or decoding raw prediction payloads. Pin the
original and archived report metadata and verify all 67 snapshot identities as
metadata; hash the seven original report/progress/log files and require the five
original/archived JSON files to be byte-identical. Do not open the full 359 MB
verification report, its lossless local copy, or sixty prior prediction NPZs.
Do not recursively compare or re-embed thousands of inherited scalar metadata
fields as new evidence. The original inherited U.guard checks remain unchanged.

Exactly the original 48 NPZ identities are permitted for runtime waveform access:
original twelve each of prepare/render/infer/flatref. Only these six waveform
members may be loaded, through unchanged U/T helpers:

| Source | Allowed members |
| --- | --- |
| original prepare | `di`, `target` |
| original render | `baseline`, `net_input` |
| original infer | `prediction` |
| original flatref | `flatref` |

Only the original checkpoint is permitted:
`/Users/yoavbz/ndsp-presets/learn/direc/models-set3/fold2.pt`, SHA256
`16b2b734b49cc1cc2d7e547d96d3bb56208007c9cae0d0e33acb1c2a1cdd042b`.
No average, new flatref estimation, native/reserved/raw source recording, alternate
model, training asset, or additional waveform member may be read. Hashing the
48 original NPZ files and original checkpoint is permitted only during the
declared committed actual run. Paths must be exact regular unaliased nonlink
identities with link count one; reject hardlinks and symlinked ancestors. Recheck
HEAD, source bytes, 48 identities and checkpoint before and after critical stages
and after scoring. Changes invalidate the entire panel.

### Mandatory saved barriers and construction controls

The cooperative 900-second budget begins before guards and includes declaration
checking, all metadata/artifact hashing, loads, baseline inference, construction,
phase inference, saving, scoring and final drift checks. Check between operations;
an individual native/library call cannot be forcibly interrupted by this budget.
No interpreter switching or alternate execution environment.
Require the original recorded NumPy/SciPy/Torch package versions at the exact
original CPU prefix; record them without importing Torch during guard checks.

1. Load the exact archived Torch32 scoring windows. Load only the six allowed
   original members after all original48 identity checks. Match prior six-member
   waveform identities. Replay **all 108 original scalar scores**, absolute
   tolerance 1e-8, and original F gate using unchanged T scoring and gate helpers.
   A phase-owned replay wrapper saves each attempt snapshot and retains a failed/
   incomplete barrier on timeout, including all completed cases. Require a complete
   saved PASS in `baseline-replay.json` **before model load**.
2. Load the original model via U, CPU eval, exactly two Torch threads. Infer the
   original unshifted input on **all twelve** cases. Save original returned
   predictions using the original offset-zero filenames/stage records. A phase-
   owned wrapper uses unchanged U inference, validation, scoring and gate helpers;
   every successful NPZ gets a full member manifest, including scalar offset,
   and attempted filenames are recorded before saving/hashing. Require exact
   original float32 prediction bytes, all **36 original network scalar scores**
   within absolute 1e-8, and original F gate PASS. Require complete saved PASS
   in `baseline-inference-replay.json` **before any phase transform**.
3. Construct H once, save exact complex128 coefficient bytes/config. Perform
   **all twelve** actual known-construction controls before any phase model call.
   Save original model-converted input, forward float64, phase float32 input,
   independently inverted forward, independently inverted quantized forward,
   and transformed wet/flatref in each case's controls NPZ. The inverse uses an
   independent time-domain periodic recurrence through SciPy signal.lfilter,
   with no FFT calls. For the reversed input, a zero-state pass supplies final
   state zN; solve periodic z0=zN/(1-(-a)^N), run the recurrence again from z0,
   and reverse the result. Direct-form recurrence is
   z[n+1]=(1-a*a)*x[n]-a*z[n], y[n]=a*x[n]+z[n].
   This implements conjugate H on the periodic domain by time reversal. It
   separates the inverse algorithm from the NumPy forward FFT, but still shares
   the CPU, floating-point arithmetic and underlying numerical ecosystem.
   Require finite H, exact real endpoints, and maximum unit-magnitude deviation
   <= 1e-12. Require inverse relative L2 <= 1e-12; norm and population-standard-
   deviation relative differences <= 1e-12; full six-second rFFT magnitude
   relative L2 <= 1e-12. Each normalization denominator must explicitly be
   finite and > 0. Require inverse after phase-input float32 quantization
   relative L2 <= 1e-6. Retain per-take errors, denominators and forward/inverse
   identities. No fitted inverse or tolerance change. Save complete all12 PASS
   in `construction-controls.json` before proceeding. A failed last take blocks
   every phase model call exactly as a failed first take does.
4. Recheck stability. Perform exactly twelve phase predictions with unchanged
   U.infer in the original CPU environment. Immediately save each raw returned
   prediction and all three transformed input/simple waveforms before validation
   or the after-call time check. Finish retaining all twelve model returns before
   prediction validity and experimental scoring begin. Model exceptions retain
   transformed arms and error metadata. Do not discard nonfinite or wrong-shape
   returns. A saving failure or exhausted budget stops subsequent calls and
   invalidates the panel; preserve every file successfully written.
5. Validate and score all twelve using unchanged P.score_prediction, fixed
   target/raw DI/windows. Preserve full per-case three-metric arm scores and
   paired changes from the replayed zero case, including wet and flatref absolute
   and relative degradation, waveform-L1/lowband changes and advantage changes.
   Baseline scores, if shown, are labeled reused with no new score.

### Gate and decision

Require exactly twelve unique valid phase cases with original6+6 group identities,
inherited QC/oracles, complete barriers, construction controls, correct raw model
returns, finite valid scores, unchanged identities and an unexpired budget.
Any invalid/error/coverage/drift/budget failure has **INCONCLUSIVE priority**,
including when another case or a valid aggregate would otherwise FAIL or PASS.

After all prerequisites pass, use unchanged F.compare on the twelve phase rows:
median relative improvement over min(transformed wet, transformed saved flatref)
>= 10% using the original 8-ulp boundary allowance; at least nine strict wins;
positive medians in both six-chord and six-scale groups. Baselinezero PASS is a
prerequisite. Valid experimental gate miss is **FAIL**, otherwise **PASS**. No
posthoc rescue, lag/gain/subset/threshold/coefficient selection or additional run.

### Artifact schema and failure retention

Only CLI `--out tmp/di-phase-control-20261008` is accepted, exclusively creating
the exact nonaliased output folder. Existing output is never overwritten. Main
must also preserve an exclusive stdout log. Execution is callable only through
main after its exact prefix check and declaration guard; import loads no Torch
or study assets. The guard refuses DRAFT before inherited guards/assets. Guard
failures after output creation also save failure/result artifacts.

- `provenance.json`: HEAD, all inherited+own source hashes, original48 manifest,
  original model identity, exact transform config, CPU prefix/packages/two threads,
  budget, timing, scope and attribution.
- `inputs.json`: original48 identities plus six allowed member identities per take.
- `baseline-replay.json`: phase-owned complete108 replay using unchanged T
  scoring/gate definitions; `baseline-replay-attempt-NN.json` saves each attempt
  snapshot. Timeout retains all completed cases and an incomplete failed barrier.
- `baseline-inference-replay.json`, `*.offset-+0.npz`: unchanged U original12
  byte/36 score/gate replay evidence through the phase-owned serializer with full
  member manifests; offset-zero records are expected.
- `coefficients.npz`: exact `h` complex128 vector. Its bytes and config are hashed.
- `*.controls.npz`: `model_converted_input`, `forward_float64`, `phase_input`,
  `inverse_float64`, `inverse_quantized_float64`, `phase_wet`, `phase_flatref`.
- `construction-controls.json`: complete/passed, exact config and coefficient
  archive, all twelve per-take member identities, errors and denominators.
  `coefficients_attempt` records the attempted filename before construction,
  saving or hashing; constructed member identities precede file hashing.
  Coefficient creation/save/hash failures retain an incomplete failed barrier,
  attempted filename and error; a hash failure retains any already written NPZ.
  A successful file/member manifest is included when available.
- `*.phase.npz`: `phase_input`, `phase_wet`, `phase_flatref`, `raw_prediction`.
  Raw return is retained in original dtype/shape even when invalid. If inference
  raises without returning, save the three transformed arrays and error metadata.
- `progress.jsonl`: explicit baseline-inference, construction-controls,
  phase-predictions and phase-cases stage records.
- `result.json`: complete flag, twelve phase rows when scoring completed, raw
  prediction archive evidence, reused baseline rows, screen/disposition, elapsed
  time, config and limitations. No embedded/base64 waveform payloads. Every NPZ
  successful reference has file SHA256, member names, shapes, dtypes and member
  byte SHA256; attempted filenames remain in metadata if saving/hashing fails.
- `failure.json`: exception type/message, elapsed time, INCONCLUSIVE. Result is
  retained on guard, load, barrier, control, inference, save, scoring or drift
  errors. Check the budget after aggregation, before and after final successful
  result saving. If the post-save check expires, retain the provisional result as
  `result-before-final-budget.json`, and write failure plus authoritative
  INCONCLUSIVE `result.json`. Failure cleanup can run after the deadline and can
  never restore PASS. Disk failure can prevent a write; never claim unsaved bytes survived.

### Verification and future execution

Implementation verification is synthetic only through the user-owned helper:

```
PYTHONDONTWRITEBYTECODE=1 /Users/yoavbz/.codex/bin/neuraldsp-safe pytest -q -p no:cacheprovider tests/test_di_phase_control.py
```

Test independent sinusoid/impulse/periodic-delay oracles, full N unit magnitude,
identity exact float32 bytes including signed zero, independent inverse without
FFT calls, reversibility and conservation,
raw amplitude before normalization, original52 convention/coherent arms, deliberate
wrong inverse/nonunit/quantized failures, last-take barrier failures, all12 prediction
retention before validation, fixed target scoring, unchanged F gate, invalid priority,
drift, alias/hardlink/output refusal, partial108 replay timeout, baseline manifest
and save/hash failure attempts (including coefficient creation/save/hash),
expiry during aggregation/final saving, time limits
and saving/error preservation.
Optional Torch synthetic tests may skip in the helper environment, which lacks
Torch. Do not switch interpreters for actual execution or run DRAFT.

After fresh review, administrative declaration and commit only, main may execute:

```
PYTHONDONTWRITEBYTECODE=1 /Users/yoavbz/ndsp-presets/tools/learn-venv/bin/python learn/di_phase_control.py --out tmp/di-phase-control-20261008
```

This exact original CPU prefix is mandatory; helper Python is not an actual-run
substitute. Main owns execution and a later fresh independent numerical verifier.
This worker owns only runner, synthetic tests and this DRAFT plan; no staging,
commit, execution, actual audio/model hashing/loading/scoring or agent spawning.

A positive result supports only this one artificial phase challenge of dependent
development cases from one player/guitar and one known-clean Morgan chain. It
does not establish real cabinet/native transfer, native failure causation,
processing diversity generally, preset ranking, song accuracy or product readiness.
Original saved full-render, physical-latency and plugin transcript evidence limits
carry forward. Saved source/review/timestamps are not an independent retrospective
runtime-access audit. Future processing challenges require separate reviewed
declarations; no broader panel or training follows automatically.

Attribution: Pedroza et al., Guitar-TECHS, CC BY4.0,
https://zenodo.org/records/14963133.
