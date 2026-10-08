# Independent timing-sensitivity design/code review

Verdict: APPROVE

Reviewed 2026-10-08 on `codex/song-model-continuation`, HEAD `a697c0dc32899f427f0951700f633bb8b36e206e`. No blocking findings. Approval covers the exact source, tests, scientific body and input-identity manifest below for main's administrative declaration and commit. The current plan is intentionally DRAFT and must continue to refuse execution. This review neither declares the experiment nor verifies any new scientific result.

Only this review file was authored in the repository. I read source/tests and existing text metadata and ran the specified synthetic pytest module. I did not open or hash actual NPZ/NPY, audio, model/checkpoint, average, catalog, or coefficient-array assets. I did not decode the coefficient archive, execute a real study, render, infer, train, access the network, start another agent or pytest worker, or change Git state. Existing numerical reports were inspected as prior evidence; their numerical computations were not repeated.

## Exact reviewed snapshot

| Item | Bytes | SHA256 |
| --- | ---: | --- |
| `learn/di_timing_sensitivity.py` | 23313 | `53259e254d262c30c7524ba8e49887c8821455e5b7aaf48c06c39cd2a7458b78` |
| `tests/test_di_timing_sensitivity.py` | 31724 | `862cb14b08049c538b62bf699da7ce365f2f5807e0752c811b13a251d9c6f942` |
| Scientific body, bytes AFTER `## Frozen design\n` | 8872 | `c6e75c3b1d10aef7155a04fd0175fbd12a8dbe01b7f6065aaedd70ad553c0999` |
| `docs/di-timing-sensitivity-inputs.sha256` | 6084 | `1c6cde4a6bdaa5ceb71fd43e56a21049cffb2bbd023a359d8f7b44de4f6dc527` |
| Entire DRAFT `docs/di-timing-sensitivity-plan.md` | 10046 | `ce3ea15e8919195471f553b8f074e58c70f7d00b7edc5fe3150ce277cc0f662e` |

These hashes were captured twice and remained identical. The scientific-body hash uses the original file bytes after the first exact marker, excluding the marker itself, with no newline normalization. Replacing the administrative draft notice and filling the approval block will change the whole-plan hash. It must leave the reviewed scientific body unchanged. Source, test, scientific-body or input-manifest changes require fresh review. Main must archive this review, declare its exact hashes and commit the reviewed execution dependencies before real scoring.

## Scientific design and implementation

The question is correctly confined to a common POST-inference scoring-coordinate perturbation of twelve fixed, same-player, clean Morgan outputs. The runner reuses saved wet, network and flatref waves; it does not reconstruct flatref, access the average, create network inputs or invoke inference. The canonical target and raw DI stay fixed.

The offset tuple is exactly `(-128, -52, -16, -8, -3, -2, 0, 2, 3, 8, 16, 52, 128)`. `finite_shift` implements positive delay as `y[n] = x[n-offset]`, with zeros outside the finite source interval and no wrap. It shifts the entire six-second waveform before the unchanged scorer selects samples `[72000,216000)`. All three arms receive the same offset. Primary and canonical waveform L1 use that fixed three-second center. Raw low-band scoring still filters each entire six-second waveform before taking its center; the design correctly avoids claiming mathematical independence from finite edges. There is no offset search, fitted lag, per-arm alignment, selected best offset or revised native gate.

The mandatory replay barrier is substantive (`replay`, lines 307–334; `run`, lines 410–414). All twelve takes and three arms are scored at zero, with three diagnostics each: 108 old scalar comparisons at absolute tolerance `1e-8`. A complete replay report and reproduced passing original stronger screen are saved before any nonzero shift. A last-take numerical mismatch saves complete failed replay evidence and prevents every shift. Invalid baseline diagnostics also block shifts and retain error evidence. Zero rows later reuse those replay scores, without another scorer call.

Each offset uses unchanged `F.compare`, including the better same-offset simple arm, median relative improvement at least 10% with the inherited inclusive boundary allowance, at least nine strict wins and positive medians in both six-take groups. Zero PASS is a prerequisite. Robustness requires all four offsets `-3, -2, +2, +3` to pass. Valid failures at the eight wider offsets remain diagnostic only. Invalid coverage, identities, QC/oracles or any diagnostic score at any offset take INCONCLUSIVE priority over scientific FAIL. Successful completion retains 156 rows and thirteen screens; invalid cases remain represented and remaining cases continue unless the budget expires.

Paired changes use each arm's zero score and the better simple arm at the same fixed offset, including when its identity changes. The formulas retain signed primary changes, zero-relative changes, waveform-L1/raw-low-band changes and absolute/relative advantage changes. A zero arm-specific primary produces a null relative change, while positive simple denominators remain mandatory.

Nonblocking precision detail: `load_inputs` preserves the stored waveform dtypes and samples and makes the loaded arrays read-only. `finite_shift` calls inherited `_mono`, which promotes a float32 prediction to float64 for the temporary shifted buffer. This preserves every float32 sample exactly and matches the unchanged scorer's existing float64 conversion. Consequently the preservation promise applies to loaded saved arrays, not the temporary shifted-buffer dtype; it does not introduce a numerical perturbation beyond the declared shift. Current shift tests use float64 inputs, so they do not directly test this float32 detail.

## Guards and existing metadata evidence

The draft/declaration check precedes inherited guards, coefficient decoding and scientific-asset hashing/loading. `F.guard` is reused unchanged; its reachable guard path calls code/metadata checks, not `F.run`, `R.frozen_inputs`, `C.assets` or any numerical asset loader. Imports likewise perform no scientific-data reads.

There are exactly 43 inherited pins and ten own pins, with disjoint names, for 53 execution dependencies. The own set covers runner, tests, whole declared plan, 48-file manifest, fresh review, both previous independent verifier sources and the original flatref result/verification/provenance. Inherited and own files must equal HEAD bytes. Approval metadata identifies this source/test/body/manifest/review snapshot. As the draft explicitly states, the approval block is main's attestation of independent review, not cryptographic proof of reviewer independence.

I checked all 42 non-coefficient inherited files against their recorded hashes and HEAD. I deliberately did not read/hash the 43rd file, `docs/di-domain-metric-probe-windows.json.gz`, because it contains coefficient arrays. Its recorded pin and the future loader's exact-bit/hash/schema checks were inspected through metadata and source only. All reviewed original JSON archives and both verifier sources equal HEAD.

The archived flatref verification has exactly 1,215 passing checks, no failures, matching 43 source pins, twelve ordered independent score rows, a matching original screen and twelve recorded byte-identical flatref comparisons with zero error. Original, independent, prepared and independently prepared/predicted identities match the declared twelve takes in order. All twelve original raw-QC records are valid and primary oracles are finite, nonnegative and below `1e-6`. Original versus independent QC/oracle/score comparisons satisfy the runner's structural and absolute-`1e-8` checks; some floating fields differ below that tolerance, so general numeric byte equality is not claimed.

The archived original flatref result/provenance are byte-identical to the original saved JSON reports, match verification-recorded hashes and carry exactly the inherited 43-pin mapping. Original control prepare/render/infer reports also equal their saved JSON reports, and original infer provenance carries the expected 35-pin subset. The independently replayed prediction and target identity fields have the schemas used by the new loader.

| Supporting text/source identity | SHA256 |
| --- | --- |
| `docs/di-morgan-flatref.json` | `767e9345a556e0222f8909db6ccc8ba503c5acadd493962688bf95bb8f323d3e` |
| `docs/di-morgan-flatref-verification.json` | `c4d76098303fb09077f612900c53d278b1b7144d4989ebe4cbd328e5b091018f` |
| `docs/di-morgan-flatref-provenance.json` | `9a72af70399dff33b58e77c59dd900bb9b2aec735a154a3ae60c785f602cc34a` |
| Prior flatref independent verifier source | `663d983b8e110d68b628446c8a1490dbb579e594c310e5157ad30d0b9a77c241` |
| Prior control independent verifier source | `8ab45b7b5cf56a3535baa0ebf624fcb8ddcaff384f10632c761ba7896f3b7eb6` |

The input manifest is committed and contains exactly 48 unique valid SHA256 entries with the expected allowed paths. Its original36 subset equals both original result and independent verification identities. Its saved12 entries equal the independent verifier's recorded flatref file identities. These are metadata comparisons, not fresh actual-file hashes.

The future loader hashes all48 before the first array load, rechecks the current file immediately before opening it, rejects resolved path/symlink aliases, uses `allow_pickle=False` and accesses only `prepare.di`, `prepare.target`, `render.baseline`, `infer.prediction` and `flatref.flatref`. It checks finite active mono six-second arrays and prior target/prediction/flatref identities. It rechecks all artifacts after loading, before shifts and before final output. Source/metadata pins and HEAD are rechecked before loading, before shifts and before final output. The inherited coefficient loader has no formula fallback and validates the archived Torch32 bits.

Only exact `--out tmp/di-timing-sensitivity-20261008` is allowed, without abbreviated options. Prefix and guards precede exclusive output creation; existing or aliased outputs are refused. Provenance, input identities, replay, incremental progress and final screens stay inside that directory. Run exceptions retain INCONCLUSIVE failure evidence and prior files. The 15-minute cooperative timer begins before the guard and is checked during asset processing and around scoring/rows. Guard/output refusals precede the failure handler and require main's external stdout/stderr capture, as declared. A timeout cannot interrupt a stuck library call; main must monitor it.

## Synthetic test evidence

Executed once, through the approved helper, with bytecode/cache writes and workers disabled:

```text
PYTHONDONTWRITEBYTECODE=1 /Users/yoavbz/.codex/bin/neuraldsp-safe pytest -q -n0 -p no:cacheprovider tests/test_di_timing_sensitivity.py
87 passed in 4.18s
```

Main additionally reports its combined synthetic suite completed with 355 passed and two optional Torch skips in 7.80s, with source/tests/scientific body unchanged during this review. That broader result is main-reported evidence; I did not rerun it. Main's navigation/follow-up documentation edits do not expand this review into a future input-coordinate study.

Coverage is meaningful rather than just checking function return shapes:

- Full-length synthetic index checks for every declared offset establish sign, finite edges, input preservation and the fixed center; impulse tests reject wrap, and crop-first results are explicitly distinguished.
- The actual inherited scorer and standardization are exercised with only spectral computation mocked, checking both canonical center selection and whole-waveform low-band filtering before cropping.
- The pipeline test requires the persisted complete successful 108-scalar report at the first shift, independently constructs every shifted source index, asserts fixed target/raw-DI object identities and verifies 468 scoring calls, 432 nonzero arm shifts, 156 progress/result rows and no zero rescore. Its last-take mismatch branch proves that no shift can occur after replay failure.
- Gate tests cover the 10% boundary, wins and group restrictions, better-simple selection, four required offsets, wider diagnostic failures, zero prerequisite and invalid priority even when a small-offset gate also fails. The corrected test keeps zero passing while testing scientific FAIL; the separate zero-failure case correctly expects INCONCLUSIVE. Experiment rules are unchanged.
- Synthetic metadata tests reject declaration/review/hash/HEAD-content mismatches, incomplete prior checks, changed verifier/wave identities, malformed manifests, original36/saved12 mismatches, source drift and invalid QC/oracles.
- Synthetic NPZ fixtures assert the all48 hash barrier, immediate pre-load checks, exactly 48 loads/144 hash calls and restriction to the five allowed member names. Drift/symlink/target/prediction/flatref failures are exercised without real assets.
- Tests verify continued complete coverage after an invalid nonzero diagnostic, retained nonfinite field locations, exact/exclusive output refusal, helper-prefix/CLI refusal and retained provenance/replay/progress/failure after timeout or source drift.

The full pipeline uses mocked scoring/windows and synthetic buffers. It does not establish actual helper performance, real-file identity, real-score parity or the outcome of the planned sensitivity study. The declared-guard tests mock the inherited guard; its implementation and existing metadata were reviewed separately here. No real guard or coefficient loader was executed.

## Interpretation and review limits

This examines common saved-output scoring-coordinate sensitivity. It does not test network input-window sensitivity, altered amplifier processing, arm-specific timing errors, physical latency or native failure causation. Twelve reused same-player performances are dependent development cases, not independent population evidence, reserved validation or product confirmation. Neither robustness outcome authorizes changing the closed native alignment gate, rescuing the original native panel, longer training or shipping.

Inherited evidence limits remain: full original wet renders survive only for the first take/canary; the other eleven full-render hashes/peaks and pre-roll cannot be independently reconstructed in this scope. There is no separate plugin parameter-command transcript. Existing slicing/overlap evidence does not remeasure physical latency, and frozen predictions are inherited from prior independent replay. This review checks those records and implementation consistency; it does not repeat the prior 1,215 numerical checks or certify current scientific assets. Actual all48 hashing, 108-scalar replay, full sensitivity scoring and fresh independent result verification remain main's work after declaration and commit.
