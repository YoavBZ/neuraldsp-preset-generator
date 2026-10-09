# Independent phase-control design/code review

Verdict: BLOCK

Reviewed on 2026-10-09 in fresh context, independently of the worker and main.
This verdict applies to the exact source, tests, and scientific body below.
The scientific question is reasonable, but four implementation/declaration gaps
must be resolved and freshly reviewed before declaration or study execution.
Passing synthetic tests does not resolve these gaps.

## Frozen snapshot

Repository: `/Users/yoavbz/projects/neuraldsp-preset-generator`.
Branch: `codex/song-model-continuation`.
HEAD: `46965737f0e0e094d958fd51466747a9fc7b5b44`.

| Item | SHA256 |
| --- | --- |
| `learn/di_phase_control.py` | `339fa29fb81e6b7dc4655fdd890c3250394136fcf37c5835004a322cc4c316b9` |
| `tests/test_di_phase_control.py` | `a5d6d912128867e7131f9671d4fb83c53aefe257b81adfca2e30f58f504c9e4d` |
| Whole `docs/di-phase-control-plan.md` | `0b3fa6419ef64ac93077eefdf187949309b311884e4e95043d1560803c27ac5d` |
| Scientific body after `## Frozen design\n` | `b48dce08a760d000400793874f79efbe19ee5a7e27752f92e6a076e585a1e693` |

All match `tmp/di-phase-review-snapshot.json`. The three proposed files are
untracked at this HEAD, as expected for the DRAFT review stage; that alone is
not a defect. The runner correctly requires a later committed declaration.

## Blocking findings

1. **P2 — The declared independent FFT implementation is absent.**
   `docs/di-phase-control-plan.md:147` explicitly requires an independent FFT
   implementation for the inverse. Forward processing at
   `learn/di_phase_control.py:216` and both inverses at lines 238–239 use the
   same `np.fft.rfft`/`np.fft.irfft` implementation. The inverse expression is
   independently written and avoids calling `transform`; that is a useful
   separation, but it is not an independent FFT implementation. The analytic
   sinusoid and periodized impulse tests provide additional independent
   mathematical oracles, and the conjugate inverse itself is correct. Those
   facts do not make the declaration accurate. Align implementation and design
   before execution: satisfy the declared independence or explicitly describe
   the shared FFT library and justify the resulting verification limits in a
   newly frozen, freshly reviewed scientific body. Add a test that checks the
   chosen independence contract. Do not describe a separate inverse expression
   as a separate FFT implementation.

2. **P2 — Baseline prediction archives do not meet the promised artifact schema.**
   The universal NPZ schema in `docs/di-phase-control-plan.md:214` requires file
   SHA256 plus member names, shapes, dtypes, and member byte SHA256; it also
   requires attempted filenames to survive saving/hashing failures. The phase
   runner calls unchanged `U.baseline_inference` at
   `learn/di_phase_control.py:398`. Its serializer,
   `learn/di_input_shift_control.py:250`, saves `raw_prediction`, scalar
   `offset`, and usually `corrected_prediction`. Its metadata at lines 256–261
   has no complete member manifest: raw/corrected shapes, corrected dtype, and
   offset member dtype/shape/byte identity are absent. The phase runner adds no
   supplemental manifest for these twelve successful NPZ references. Moreover,
   if saving or `R.sha(path)` fails, `prediction_evidence` never returns its
   filename metadata; the baseline item was initialized without an attempted
   filename at line 292. This is visible directly from source and also matches
   the committed prior result's legacy record schema.

   Preserve the inherited helper's numerical behavior, but add phase-owned
   evidence that supplies the declared member schema and records attempts
   before save/hash operations. Alternatively, any intentional legacy-schema
   exception must be explicit in a newly reviewed design. Add synthetic tests
   checking the actual baseline NPZ manifest and save/hash failure records;
   the current phase suite checks the new phase archive schema only.

3. **P2 — A timeout during the 108-scalar replay loses completed replay evidence.**
   `learn/di_phase_control.py:395` calls `T.replay` directly. In
   `learn/di_timing_sensitivity.py:307`, completed cases and their errors are
   held only in local lists. Lines 321–322 immediately re-raise `TimeoutError`;
   the only replay write is after the entire loop at line 330. For example,
   expiry while scoring take twelve loses the eleven completed cases and
   produces no `baseline-replay.json`. `Q.execute` preserves the general
   failure and an INCONCLUSIVE result, but has no access to those local replay
   rows, so it cannot preserve the partial barrier evidence. Later model work
   remains blocked; this finding concerns evidence retention, not a false PASS.

   Provide phase-owned durable partial replay evidence while keeping the
   inherited scoring, tolerances, and gate unchanged. A timeout must retain
   completed cases and a failed/incomplete barrier record. Test an actual
   mid/last-take timeout through the real replay path. The phase barrier test
   at `tests/test_di_phase_control.py:264` replaces the whole barrier with a
   raising stub, so it proves blocking but cannot detect this loss.

4. **P2 — Expiry after the final time check can still produce PASS.**
   `learn/di_phase_control.py:409` checks the budget before calling `compare`.
   Lines 410–411 then accept its screen, and `execute` at lines 426–428 records
   elapsed time and writes `result.json` without checking the budget again.
   Thus expiry during final aggregation/cleanup can leave a PASS screen even
   when the recorded elapsed time already exceeds 900 seconds. Final result
   saving also has no budget check afterward. This conflicts with the declared
   inclusion of saving in the cooperative budget and INCONCLUSIVE priority for
   any budget failure. Library calls need not be forcibly interrupted, but
   their completion must not turn an expired run into a successful panel.

   Add finalization checks that make an over-budget completion visibly
   INCONCLUSIVE while preserving written evidence. Add deterministic fake-clock
   tests for expiry during aggregation and final saving, not merely before
   guards or immediately after inference. This finding follows from source;
   the existing tests do not exercise these finalization cases.

## Scientific and operational checks that are sound

- The fixed `a=-0.9`, N=288000 response has the stated formula and exact real
  DC/Nyquist endpoints. It asks a bounded phase-dependence question. The plan
  accurately limits it to an artificial periodic transform and dependent
  development cases, with no causal-cabinet or native-transfer conclusion.
- Original full raw input is converted to little-endian float32 before promotion
  to float64. Forward output is converted back to float32 before unchanged
  `U.infer`/`D.rebuild` normalization. Both saved simple competitors are
  transformed coherently in float64. Target/raw DI remain fixed; no prediction
  inverse, fitted lag/gain, new flatref estimation, or coefficient selection
  occurs. The inherited loader enforces the original 52-sample overlap.
- Ordering is correctly encoded: saved 108-scalar replay before model load;
  saved twelve exact original predictions/direct 36 scores before construction;
  complete saved twelve-case controls before phase inference. A final-case
  failure cannot bypass these barriers. The controls' `finally` retains their
  partial report, unlike the inherited scalar replay timeout path above.
- Relative controls require finite positive denominators, check finite errors,
  and use aggregate spectral-magnitude L2 rather than pointwise relative errors
  at zero bins. The 1e-12 float64 and 1e-6 quantized inverse thresholds are
  implemented. Wrong inverse, nonunit transfer, quantization corruption,
  nonfinite values, and zero denominators have meaningful synthetic coverage.
- Phase returns are saved before prediction validation and the after-call time
  check. All twelve returns precede scoring. Inference exceptions preserve
  transformed arms; phase save failures stop subsequent calls and retain the
  attempted filename. Existing output is refused; file identity checks reject
  aliases, hardlinks, and symlinks. Import is inert with respect to Torch/assets.
- Coverage and identity checks enforce twelve unique takes and six per group.
  QC/oracles, baselinezero prerequisite, fixed-target scoring, paired changes,
  unchanged F gate, inclusive original eight-ulp 10% boundary, nine strict wins,
  and positive group medians are preserved. Invalid cases take INCONCLUSIVE
  priority; a valid gate miss remains scientific FAIL.
- Guard inspection supports exact committed declaration/source/test/review/body
  binding, 63 inherited plus 14 disjoint phase pins, original 48-artifact
  allowlist, six allowed waveform members, fixed checkpoint, CPU prefix/package
  constraints, two threads/eval, and repeated/final source/HEAD/asset checks.
  The DRAFT guard stops before inherited guards or asset access. No alternative
  environment, discovery, training, plugin, or network path was introduced.

## Prior archive evidence: container hashes versus member bytes

I inspected committed source and compact metadata only. I did not open/hash any
study NPZ, checkpoint, audio, full 359 MB verification report, or lossless local
archive, and did not decode/follow prediction payload references.

The prior verifier's `evidence` function at
`docs/research/di-input-shift-control-independent-2026-10-08.py:453` constructs
independent NPZ containers. Its primary comparison at lines 550–562 separately
checks the serialized container hash, saved schema/offset, and exact raw and
corrected array bytes. The committed compact report records 60 passing
`exact NPZ serialized bytes hash` checks and 120 passing member-byte checks.
Metadata joins found zero mismatches between each retained independent container
hash and the primary result's corresponding container hash, and zero mismatches
between independent raw/corrected identities and primary member hashes. The
independent rows' container hashes also agree. Therefore the phase guard's
container equality at `learn/di_phase_control.py:130` is supported by this
particular archived evidence; it is not inferred merely from matching member
bytes, and I found no container-identity blocker.

The compact report has 21246 checks, zero failures, 63 source pins, 48 original
artifact identities, and 67 primary snapshots. The compressed file's working
and HEAD bytes both hash to
`53ac147bc2ea2c4a3d54e63b4b52571791fe9b24ec64b28eca644c82abd34100`.
Its decompressed metadata hashes to
`30fa2e1554e5e7a4961c316032449a504169ff431a4400d4a23e1c745d0cf873`.
Both match the committed archive manifest. The verifier source hashes to
`4ad1bfcd4ff01cf2da2df505853e8c17073c1bb3600f143fac90edb11228a176`,
also matching that manifest. These are inherited attestations and metadata
consistency checks, not a fresh independent observation of archive payload bytes
or historical primary runtime calls. The runner appropriately avoids following
references or growing duplicate waveform payloads.

## Tests and review limits

All test execution used the user-owned `/Users/yoavbz/.codex/bin/neuraldsp-safe`
helper with `PYTHONDONTWRITEBYTECODE=1`, `pytest -q -p no:cacheprovider`.

- `tests/test_di_phase_control.py`: **55 passed, 1 skipped**, 0.86 s, exit 0.
  The optional Torch synthetic normalization test skipped because Torch is
  unavailable in this helper environment. No interpreter substitution occurred.
- Four targeted inherited tests: **11 passed**, 0.90 s, exit 0:
  `test_last_baseline_prediction_failure_retains_complete12_blocks_every_shift`,
  `test_all108_replay_failure_blocks_all_network_calls`,
  `test_baseline36_parity_is_direct_to_archive_not_accumulated_replay_tolerance`
  from `tests/test_di_input_shift_control.py`, and
  `test_bad_baseline_diagnostic_saves_failed_replay_and_never_shifts` from
  `tests/test_di_timing_sensitivity.py`.

The four blockers are source/design findings, not claims of failing existing
tests. No actual study inference/scoring, asset read/hash, download, plugin,
training, other agent, or Git write was performed. Only this review file was
created. Main owns subsequent repairs, new frozen snapshots, fresh review,
administrative archival/declaration, commit, and any eventual execution.

Final recheck: all four frozen hashes and HEAD still match the entry snapshot.
The final status also shows concurrent changes to `docs/README.md`,
`docs/ROADMAP.md`, `docs/di-recovery-plan.md`, and `learn/README.md`; this reviewer
did not edit those files. They do not alter the reviewed source/test/body bytes.
