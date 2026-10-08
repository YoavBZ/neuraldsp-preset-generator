# Synthetic DI-metric probe review

2026-10-08. Code/design review and targeted synthetic unit tests only. This report
is the only file written by this reviewer. No four-case numeric probe,
audio/array/model/catalog access, Git operations or child agents were used. Main
owns the declaration, implementation and tests. The explicitly permitted helper
unit-test command and outcome are recorded below.

**Current disposition: APPROVED for administrative declaration/freeze and commit.**
The final correction review below supersedes earlier change requests. No remaining
blocking findings for this bounded synthetic probe. This reviewer has not executed
the Torch probe or performed a Git operation.

## Design review — initial draft

Reviewed `docs/di-domain-metric-probe-plan.md`, draft first inspected at 4291 bytes.
The probe implementation and tests were not yet present at that inspection.

**Disposition: the bounded design is sound; final approval awaits code/tests.**
The four fixed pairs, observed default dtype, exact coefficient exports, original
reproduction, coefficient interventions and unchanged-function comparison can
distinguish window precision from FFT/reduction disagreement without accessing
real inputs. The stricter per-component gates are legitimate requirements of this
newly declared probe; they do not retrospectively change attempt 1's gate.

Implementation/review requirements:

1. **Preserve Torch accumulation order for the exact check.** The frozen function
   uses `loss = loss + spectral_convergence + log_l1` on each resolution, then
   divides once by five. Summing precomputed resolution totals or converting each
   term to a Python float before accumulation can change rounding. Keep the local
   Torch reference's computation, shapes, scalar dtypes and operation order equal
   to the frozen function. Use supplied float32 Torch tensors for its T32 windows;
   promote those coefficients to float64 only in the NumPy path. Do not monkeypatch
   `direc.mrstft` or change the global default dtype.
2. **Make every gate finite and absolute.** Require four correctly labeled cases,
   all five FFT sizes, all terms, and finite values before comparisons. Original
   reproduction means both independently computed score columns are within
   absolute 1e-12 of their committed values, and each row's original <=1e-8
   classification agrees. Do not trust a saved error/pass flag instead of
   recomputing it from scores. An unexpected original-artifact schema, missing
   case or nonfinite value is a failure, not a skipped row.
3. **Export enough evidence for reconstruction.** Save coefficient bits/dtype/shape
   and canonical little-endian byte hash for T32 and T64. Also retain NumPy-formula
   float64 coefficients losslessly, or explicitly define how independent
   verification reconstructs that third window. Preserve negative zero if present;
   numerical equality alone is weaker than the promised bit equality. Round-trip
   the exported T32 representation and use that decoded window in the shared-window
   intervention so the experiment checks the artifact later proposed for reuse.
4. **Pin only allowed files.** Code/declaration/tests/static review and committed
   failed-score text are allowed. Do not reuse the pilot runner's `PINNED`/
   `frozen_inputs` machinery: it reads model/average/catalog. Pin the relevant
   inert module initializers too, or otherwise verify imports have no extra
   application-side effects. Retain the untouched first failure and original
   authoritative code. Exact Torch/NumPy versions should be checked against the
   declared first environment, not merely recorded after computation.
5. **Retain failures and refuse overwrite.** Exclusive output creation must precede
   any output writing. Save useful provenance/windows/rows incrementally before a
   later gate or time-budget failure. An existing destination is a refusal and must
   never receive a replacement failure file. The cooperative fifteen-minute budget
   should be checked during preparation and between cases, including before the
   final success artifact; it is not a hard interruption of a library call.
6. **State the evidence's independence precisely.** Recomputing saved component
   comparisons, aggregates, hashes and gates independently verifies arithmetic and
   artifact consistency; it does not rerun FFTs from text summaries. The signed
   intervention residual is algebraically the shared-T32 residual:
   `(Torch_original - NumPy_original) - (NumPy_T32 - NumPy_original)
   = Torch_original - NumPy_T32`. Retain it for interpretation, but do not count it
   as another independent causal test. Shared NumPy64 coefficients provide the
   separate FFT/reduction control.

The plan's statement that success does not authorize another pilot is appropriate.
Keep explicit Torch64 results diagnostic and outside the required success gates.
No design finding requires loosening either 1e-12 reproduction or 1e-8 agreement.
If either is unattainable, retain that failure and review it separately.

## Final implementation and tests review

### First implementation snapshot — still in progress

Inspected the initial 9291-byte `learn/di_domain_metric_probe.py`; tests were still
absent. These findings refer to that snapshot and may be superseded by later edits.

**Changes needed before execution:**

- **P2: exported windows are not the intervention's input** (lines 145–156).
  The code writes coefficient bits but then uses `t.numpy().astype(float64)`
  directly. Add a validated decoder, round-trip the bits and canonical byte hash,
  and use decoded T32 coefficients for the NumPy intervention. Verify bit identity
  for default/explicit windows as well; `torch.equal`/`np.array_equal` do not
  distinguish signed zero. This makes the promise of exact *exported* coefficients
  testable before those artifacts are proposed for downstream use.
- **P2: original pass-pattern comparison trusts saved `absolute_error`**
  (lines 110–120), and source rows/schema/count are not validated before indexing
  (lines 132,169). Recompute the committed reference error from its finite scores,
  validate its error field and four rows, and reject missing/extra/nonfinite rows.
  Enforce five ordered FFT terms in each component report; equal empty/partial
  `terms` lists can currently satisfy `terms_agree`. Production construction is
  currently fixed, but the reusable success gate should enforce that contract.
- **P2: cooperative deadline is not checked after the final case**
  (lines 161–179). Add a check before the success artifact, and around window
  preparation. As written, an overrun in the fourth case can still report success.
- **P2: tie the copied NumPy path back to the unchanged one** (lines 164–169).
  Explicitly compare `numpy_np64.aggregate` with `original_numpy` at absolute
  1e-12, and test that the component sum reproduces the local aggregate within
  its declared rounding convention. Otherwise the two intervention paths have
  no explicit guard against a transcription error in `numpy_terms`.

**Clarifications:** versions are recorded but not checked against Torch 2.8.0 /
NumPy 2.0.2 (lines 133–138); either enforce those declared environment versions or
explicitly state that exact original-score reproduction is the environment gate.
The source guard includes the inert `learn/__init__.py`, correctly excludes the
old runner and real-input manifest, and preserves exclusive output refusal. It
does not yet pin this review/archive; add that if the final declaration promises
review pinning. Local Torch accumulation correctly preserves the authoritative
function's operation order (line 93).

This report does not approve execution or claim that any check has run or passed.
Final code/tests review remains pending.

### Stable implementation/tests review — supersedes the preliminary disposition

Reviewed the complete 201-line implementation, 85-line test file and draft
declaration. **Disposition: changes requested before approving the causal probe.**
The bounded access design is approved. Source imports are inert; the source guard
reads only the named code/declaration/static failed-score files. It does not call
the old runner or hash/read model, average or catalog. The original authoritative
code and original failure artifact still match the hashes in the initial audit.

The implementation correctly keeps the exact four original pairs, all five FFTs,
float64 signals, explicit CPU float32/float64 Hann windows, two Torch threads and
no-gradient metric work. Local Torch accumulation preserves the unchanged
function's order. Required component and aggregate gates use direct absolute
comparisons. Explicit Torch64 comparison is diagnostic, not a success gate. The
export contains lossless coefficient records for NumPy64, Torch32 and Torch64,
including the full 7936 coefficients for each window family.

#### Required corrections

1. **P2 — establish that the NumPy intervention changes only the window**
   (`learn/di_domain_metric_probe.py:110–120,164–169`). The probe compares the
   unchanged `P.mrstft_numpy` with original saved scores, but shared-window controls
   use the new `numpy_terms` implementation. It never checks that this copied
   NumPy implementation with its original NumPy64 windows reproduces
   `P.mrstft_numpy`. The signed-intervention gate cancels `original_numpy`
   algebraically and cannot supply that missing check. A transcription error
   could therefore be attributed to window precision. Add a finite, absolute
   <=1e-12 check of `row['numpy_np64']['aggregate']` against
   `row['original_numpy']` for each exact case, include it in required success,
   and add a negative unit test where all shared controls agree but this copied
   baseline differs by more than 1e-12. Keep the original values/tolerances.

2. **P2 — make the analytic fixture's declared accuracy effective**
   (`tests/test_di_domain_metric_probe.py:37–39`). `pytest.approx(expected,
   abs=1e-14)` retains its default relative tolerance. For the convergence term
   around 0.5, this permits errors around 5e-7, so these assertions do not enforce
   the stated absolute 1e-14 precision. Use `rel=0, abs=1e-14` for all three
   analytic assertions. This strengthens verification; it does not loosen the
   probe or alter its frozen signals.

These corrections are small and do not require running the four-case probe.

#### Additional bounded refinements

- Prefer decoding the serialized coefficient bits and validating their hashes
  before using the decoded T32 windows in the NumPy intervention. The current
  exporter is correct on inspection and its float32/float64 JSON round-trip tests
  pass, but actual probe execution uses live tensors rather than replaying the
  export. This is an artifact-reuse check, not evidence that today's coefficients
  differ. Default-versus-explicit equality should compare bytes if the final
  declaration promises *bitwise* equality; current `torch.equal` is numerical.
- Validate the failed-score artifact's four finite rows and recompute reference
  pass/fail from its score columns. Current archived JSON is correct and pinned;
  this is fail-closed schema protection, not an observed corruption. Similarly,
  require five ordered resolution records when evaluating saved probe results.
- Add a cooperative budget check after the final case and before result success.
  Current between-case checking is consistent with the draft's narrow wording,
  but allows the fourth case to exceed fifteen minutes and still report success.
  Do not describe it as a hard timeout. Retain completed case evidence first.
- Versions are recorded, not required to equal the first environment. The final
  declaration should either require Torch 2.8.0 / NumPy 2.0.2 or explicitly treat
  1e-12 original-score reproduction as the environment-equivalence requirement.
- Record actual input/STFT device/dtype rather than relying only on descriptive
  strings if these fields become machine-verified prerequisites.

#### Meaningful tests and execution evidence

Executed only the user-permitted targeted command:

```text
/Users/yoavbz/.codex/bin/neuraldsp-safe pytest tests/test_di_domain_metric_probe.py -q -p no:cacheprovider
8 passed in 0.66s
```

The tests exercise lossless bits including signed zero, bad-window rejection,
an independent rectangular-window DC/epsilon analytic expectation, sensitivity
to supplied windows, component mismatch despite equal aggregate, nonfinite
rejection, exact-versus-tolerant score checks, and draft refusal before any Git
subprocess. These are useful synthetic checks. The draft-refusal test does not
exercise the committed source guard or prove runtime access confinement by itself;
that conclusion here comes from static call-path inspection. No Torch probe,
asset hash/read, actual four-case score or coefficient intervention was executed.

The suite passing does not close the two corrections above. After their patch,
review the small diff and rerun this targeted suite before final approval. No
additional numeric experiment is needed for that review.

#### Reviewed snapshot SHA256

| File | SHA256 |
| --- | --- |
| learn/di_domain_metric_probe.py | f6ca3231a26c1ba58e5014ae84e98a7f5e1ceb261eaa4b5c508283dd845d090b |
| tests/test_di_domain_metric_probe.py | 0027cf428916878410b624a5ee52dbd58d95457d0349e15097a675e4c8d6306c |
| docs/di-domain-metric-probe-plan.md | 413661a953802c56af88222e3d8df4ce14f4e2498a1b6926c1f8ee139cc57ef4 |
| docs/di-domain-pilot-metric.json | 02f53d2521fe268c28b05ff4b00b806d8199028f5c5ed3764970fff5327513b7 |

Review approval, the final declaration and commitment must precede the separate
CPU Torch probe. A probe pass would authorize no pilot automatically.

### Final correction review — approved for administrative freeze and commit

2026-10-08. Re-read the complete current implementation, test definitions and draft
plan without running code/tests, Torch or Git. Both required corrections are closed:

- `case_checks` now requires `explicit_np64_matches_original` at absolute <=1e-12
  (`learn/di_domain_metric_probe.py:118`). Its result participates in the existing
  all-required-checks success gate. The test asserts failure of this check when
  the copied baseline and original differ by 2e-12
  (`tests/test_di_domain_metric_probe.py:75–77`). The draft plan explicitly declares
  this baseline-agreement requirement.
- All three independent analytic assertions now specify `rel=0, abs=1e-14`
  (`tests/test_di_domain_metric_probe.py:37–39`).

**Approved:** current code, tests and draft plan may be administratively declared,
frozen and committed before the separately scheduled synthetic probe. Replacing
the draft header with the declaration marker required by `guard()` is an expected
administrative step; retain the reviewed procedure and gates. No additional code
change is required by this review. The bounded refinements above remain nonblocking
observations, not new prerequisites.

Main reports **8 helper tests passed** after these changes. This reviewer verified
the source changes statically and did not rerun that updated suite. The earlier
8-pass execution in this report applies to the preceding snapshot. No claim is
made that the four-case Torch probe or its numerical hypothesis has passed.

Final inspected SHA256 values:

| File | SHA256 |
| --- | --- |
| learn/di_domain_metric_probe.py | 7e56ac6c856cea35e0e1b3f7370605879880c7a0369d1be6f8d044683cbc0f6f |
| tests/test_di_domain_metric_probe.py | 2df0f788d88408ec6b4e60e688e74bbea6768332e579bee2882f88eabe3b7cff |
| docs/di-domain-metric-probe-plan.md (draft) | a4c5a7e3aa69660cfce5f00deb36baea39a1331da2a553ca4e0d8b9c5c298448 |

`learn/direc.py`, `learn/di_domain_pilot.py` and the archived failed JSON still
match the previously recorded original hashes. The first pilot remains failed.
This approval covers the pre-execution review and freeze/commit readiness; it is
not a result verification or approval of another pilot.
