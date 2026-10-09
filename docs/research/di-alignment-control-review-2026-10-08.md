# Independent calibration correctness design/code review

Verdict: APPROVE

No blocking findings. Approval is for the exact scientific body, source, tests and prerequisite bytes identified below, followed by main's administrative declaration, archiving and commit. This is a fresh pre-execution review, not verification of an experimental result.

Reviewed on 2026-10-08 in `/Users/yoavbz/projects/neuraldsp-preset-generator`, branch `codex/song-model-continuation`, HEAD `3f68a25cd616acf5efbfdcd0032ce6c290fa370c`. The three reviewed files were new and untracked throughout review. Existing navigation edits belong to main. I changed no source, tests, declaration or Git state and spawned no child agent or pytest worker.

## Exact approval and administrative changes

The following hashes were independently captured twice and remained unchanged:

| Approval field / file | SHA256 |
| --- | --- |
| `design_sha256`: exact bytes after `## Frozen design\n` (10,244 bytes, including the following blank line) | `f43a29402976aa99469f90a745e315ff724da5524d2c59054c09f8f7db060f49` |
| `source_sha256`: `learn/di_alignment_control.py` | `dc0ea39b69095bd7406ed7d6908e31ee04b0a9a23e115995880bf4b9b6e62b77` |
| `test_sha256`: `tests/test_di_alignment_control.py` | `b543a668c35594f2900e8b74a30ad6268345afa7bddf502000584adf9281c45b` |
| Full draft `docs/di-alignment-control-plan.md`, for snapshot identification | `8777814c6c48dc8cdeadf1f8b8f16c366c9f2ebe8bb4d61c7fe437dc4cbc2cbb` |
| `docs/di-morgan-flatref-inputs.sha256` | `404ad70b3274a373df539c33119657c4db4353ef81d59d6c7ed72f573c7ee5e9` |
| `docs/di-morgan-control-prepare.json` | `0c778956c77976118241d163a7e98145daa5d2e8949b470972b9bac40562e615` |
| `docs/di-morgan-control-verification.json` | `58f74aca051f27ab0996efeefa1016a7d963143bb56cb845578a3954a311581b` |
| `docs/research/di-morgan-control-independent-2026-10-08.py` | `8ab45b7b5cf56a3535baa0ebf624fcb8ddcaff384f10632c761ba7896f3b7eb6` |

These are seven of the runner's eight additional pins. The eighth is this review archived at `docs/research/di-alignment-control-review-2026-10-08.md`; main must compute the archived file's final byte hash and use it as `review_sha256`. There is intentionally no recursive self-hash inside this report. All eight additional files, including the final full plan and review, must be committed before execution.

I approve replacing the administrative DRAFT/status/worker notices above the marker with the declaration, approval metadata and review link. The scientific suffix must remain byte-identical to the approved `design_sha256`, and the source and test hashes must remain the values above. Set `mean_interpretation` to `uncentered-input-exact-formula`. Main must bind these values and the archive hash in the declaration. Any changed scientific instruction, including one inserted above the marker, or changed dependency/input definition requires review of that changed snapshot.

The runtime checks all own and inherited dependency bytes against HEAD, then matches the declaration's review/source/test/body hashes. The full plan's committed-byte check covers the final administrative content, while excluding that content from the scientific hash avoids a declaration/review hash cycle. The review text check and main's attestation are not a machine proof of reviewer independence or a parser that verifies this report's hash table. That trust boundary is stated explicitly in the plan and is appropriate for the requested main-owned declaration process. This approval does not authorize arbitrary later edits accompanied by new hash values.

## Scientific validity and frozen calibrator

The question is well defined: apply unchanged `P.calibrate` to known transformations of all twelve saved raw six-second DIs, with 144 positive cases and twelve deliberately mismatched-performance negatives. This cannot rescue the failed native screen, tune its gates, establish native alignment, or establish model transfer. The correct imposed-lag catalog prior makes the positive study optimistic; it does not validate the original catalog priors. The twelve cyclic negatives assess these particular different performances, not a general false-acceptance rate or all possible wrong priors.

The source agrees with the exact formulas. Identity copies x; polarity negates it; lowpass uses the declared fourth-order 1200-Hz Butterworth SOS and zero-phase `sosfiltfilt` with odd padding and padlen 27. Tanh is exactly `tanh(3*x/std(x))*std(x)/3`, with NumPy population std over the complete six seconds and the original uncentered input. There is no demeaning or mean restoration. The plan correctly explains that uncentered input does not generally preserve the arithmetic output mean; there is no remaining contradictory mean-preservation claim in the reviewed plan or implementation. Its synthetic nonzero-mean test checks this distinction.

`construct` transforms the complete six seconds before taking the 193,024-sample prefix, shifting or padding. Both the global std and zero-phase filter intentionally depend on samples outside P's four-second slice. There is no scored interval and no pristine calibration/evaluation split claim. The mostly-zero ten-second buffers exist to satisfy P's unchanged API. The synthetic isolation test checks P's buffer boundary after construction; it correctly does not claim that changing later source samples cannot affect the full-six-second transform.

Finite slicing implements `wet[n+lag] = transformed_di[n]` for both lag signs without circular wrap. P's calibration interval starts at buffer sample 512; the prefix includes 512 samples on each side of its four-second interval. For every imposed shift, the samples needed for that interval lie inside the original prefix, so finite-shift padding cannot enter it. P itself ignores these guards during estimation, as disclosed. The signed truth errors use estimate minus imposed lag, with polarity truth -1 only in the polarity arm.

All12 identity/order/group requirements are preserved by the committed original manifest. Positives cover all four arms and three shifts for every take. Negatives choose NEXT within each original six-take content group, wrapping separately for chords and scales; both identities are retained. Negative truth lags/polarities and associated correctness errors are null. Zero is only the imposed construction shift and nominal catalog prior for negatives, not invented matching truth.

I compared `diagnose`/`predicates` directly with `P._gcc_phat`, `P.bandpass`, `P.Calibration` and `P.calibrate`. They use the same full four-second and two two-second estimates; filter the calibration slices independently; crop at the full estimate with the same sign convention; remove each cropped mean; and compute the same Pearson numerator and norm-product denominator, including zero-denominator correlation zero. The recorder preserves all raw estimates, denominator/correlation, derived fields and downstream predicates even when actual P rejects at an earlier confidence check.

Rejection inequalities and order are exact: all three sharpness values >10; all three separations >1.2; absolute full-minus-catalog lag <=16; three-estimate range <=8; finite absolute correlation >=0.5. No rounding allowance was introduced. The five original messages and first-rejection order match. The recorder then calls actual unchanged P on the same buffers/prior and checks acceptance, exact returned fields or the first ValueError/message. It shares the frozen numerical primitives, so this is a composition/parity check rather than independent FFT validation. Known-truth synthetic cases provide additional evidence for lag sign and polarity.

The gate has the requested strength: all 36 identity and all 36 polarity cases must be accepted correctly within one sample, any wrong accepted positive in any arm fails, and any accepted mismatch fails. Lowpass/tanh rejection alone does not fail. Exact declared coverage and identity/truth matching are required. Invalid/nonfinite evidence or P inconsistency yields INCONCLUSIVE before scientific FAIL. Counts/rates cover each arm and content, including all-content totals; wrong accepted positives and accepted negatives retain their full rows. Nonfinite scalars become null with field paths, rather than silently entering JSON or a PASS.

## Prerequisites, input access and retained evidence

The current archived original verification has `VERIFIED_WITH_EVIDENCE_LIMITS`, 767 passing checks, zero failures, twelve ordered independent preparation rows and matching source/verifier hashes. Both archived preparation and independent preparation have complete original identity coverage, valid QC and finite nonnegative primary oracles strictly below 1e-6. These were metadata checks, not recomputation of the old experiment. The prepare archive is byte-identical to the original saved `prepare/result.json`; the verification archive is byte-identical to `tmp/di-morgan-control-verification.json`. The original prepare provenance's complete pin mapping equals the current 35 inherited pins.

The archived verifier source matches its recorded SHA256. Inspection confirms it independently checked the bounded raw DI, full-ten-second QC, saved six-second raw `di`, canonical target and oracle, rather than merely copying primary flags. Its prior result limitations remain: full wet renders survive only for the first take/canary, parameter commands were not independently transcribed, and fixed slicing does not remeasure physical plugin latency. Those limitations do not supply additional evidence about this new calibration experiment. The reviewed runner appropriately requires preparation validity, not a model/flatref outcome, for this study's prerequisite.

Imports perform no experimental data reads. `guard` calls only `C.code_inputs()` for source/declaration/path metadata; it does not call `C.assets()`, `R.frozen_inputs()` or coefficient decoding. Declaration, exact committed dependencies, manifest identities, archived prerequisite semantics, original saved-prepare equality and inherited provenance checks all precede actual NPZ access. The guard fails closed while the reviewed files are DRAFT/untracked, as expected; I did not run the actual guard/diagnostic.

The existing hash manifest has exactly 36 unique valid entries, equal to the original twelve slugs crossed with prepare/render/infer. The new parser validates the entire metadata path set and selects exactly the twelve prepare entries. `load_inputs` checks path resolution and all twelve hashes before the first `np.load`, then rehashes each file immediately before its load. It accesses only `saved["di"]`, with pickle disabled and mono, finite, exact six-second validation. Render/infer NPZs are neither hashed nor loaded by this study. All additional prerequisite files already present are byte-identical to HEAD; all35 inherited dependencies are unchanged from HEAD and their verified hashes.

The CLI requires the actual project environment and its sole `--out` argument. The output must be the exact fixed project-tmp path, with aliases, symlinks and existing directories refused. File creation is exclusive; arrays/buffers are not saved. Provenance, input file/DI hashes, complete case declaration, environment/package versions, construction recipes/hashes, incremental progress and final evidence are retained in the declared directory. The runner prints progress; main's declared execution harness owns stdout/stderr capture, including guard/directory refusals before directory creation.

Per-case exceptions retain invalid case evidence and allow remaining cases to proceed within budget. Run-level failures after directory creation preserve `failure.json`; malformed hash metadata still retains provenance. The 15-minute timer starts before the guard, is checked throughout loading and before/after every case, and keeps progress when it expires. It is cooperative and cannot interrupt a stuck library call; main's monitoring responsibility is disclosed. Pre-directory guard/prefix/directory refusals intentionally rely on main's command capture, not another study output directory.

## Independent synthetic verification

Executed once through the required user-owned helper, serially with pytest's cache disabled:

```text
/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -n0 -p no:cacheprovider tests/test_di_alignment_control.py tests/test_di_domain_pilot.py tests/test_run_di_domain_pilot.py tests/test_di_morgan_control.py tests/test_di_domain_pilot_v2.py -q -rs
258 passed, 2 skipped in 4.31s
```

This includes all 80 new synthetic tests plus the relevant inherited contracts. The two skips are existing optional Torch parity tests at `tests/test_di_domain_pilot.py:651`, because Torch is absent in the helper environment. No plugin, training, checkpoint or inference was used. The helper disables Python bytecode writes. No optional full-repository expansion was performed. `git diff --check` passed.

Coverage includes actual frozen primitives on known positive lags/polarity and independent-noise/ambiguous-tone negatives; full-transform ordering and nonzero-mean semantics; finite prefix shifts and edge impulses; P buffer isolation; three-estimate recording; strict/inclusive confidence boundaries; all five actual rejection paths and downstream evidence; every returned Calibration field; nonfinite retention; strong positive/negative gates and invalid-coverage precedence; mocked declaration/commit/prerequisite failures before assets; the exact hash subset/all12 barrier/DI-only member access; exclusive output/prefix/CLI checks; complete progress, case errors, malformed manifests and cooperative deadline retention. Synthetic guard fixtures test mechanics; the real committed source and prerequisite metadata were separately inspected as described above.

## All 35 inherited pins

Each listed hash equals both current bytes and HEAD, the archive's `source_pins`, and original prepare provenance. Digest of the complete lines below sorted as `hash + two spaces + relative path + newline` is `dac18ee616eee44b5ff6c586e44daf42f757fe59557958e4c3f6ee5f9f1c21ac`.

```text
41a9dae241f2090fc5a1e7f3b73f3b628741b05e1ad85811af750045dbca93bc  docs/di-domain-metric-probe-windows.json.gz
3220d15a5dfbfb40ee39462377e88104cc8c3a6f6cfcabb4aa2f7d80613e8930  docs/di-domain-pilot-inputs.json
3fe8a65c46c216f360dbca8e472eaedaea4b261a85a4a47f924f7c74b9592465  docs/di-domain-pilot-plan.md
fe501e97053276208020e56a8bce8ba1689237795c3d232b18ceadc74b2421dc  docs/di-domain-pilot-v2-inputs.json
96b807d1a7b421bc18412ed8887ddf998588a2ba33caabe4dfb623cd140e262c  docs/di-domain-pilot-v2-plan.md
b07d77d97958866fa8d3b68e5d78e564ba8985c4f808a48b02b5ac3499003ff2  docs/di-morgan-control-plan.md
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  format/__init__.py
bd29491dd3fdeebd656d6bafce71d101570bd40c9a9b0848336c1d93fcbd76f7  format/markers.py
93586273c398f766cce82bb043923416a2a1fbec191d29b87797b395105b4e88  format/parser.py
00880b4373a5300c6a285652dc310fa21d9e1b6bc65bdb1feecebb91920b5279  format/structured.py
8dd3de2a011aa4d829cae050576eb6348c3fd76482cecb582de9ebfe90484dea  format/translate.py
0ba5e099478d993dc1a01361a2733cfc59079929c07311b3983797b63fc78ca5  format/writer.py
950da993349f85949c8094f0787bcf1b56f149cf3a7a829f8b7986bea7c3525d  learn/__init__.py
338abb963b122f3bc6710e45253674829f2db2be585a0fd56164f36323088076  learn/di_domain_pilot.py
b89a40f6aaa9318479b5de2af35a4e4e7a66d017a1d9c16a4fd62caea33d1428  learn/di_morgan_control.py
072dfe5dfd1fc892eef1449ad6ab9d7a2725e2ddb701311714437d95aba27fb1  learn/di_robustness.py
43b698ba69fc97d91b547e9948b9b0611dec7b01453eef43609e365a85885969  learn/direc.py
e2ba7db8935b4602f86658dba57c67a6918c6fa824852e8d118ed7632a36bb79  learn/run_di_domain_pilot.py
397a8abd55a516047288b789db1375c21c5cbf89a1b3e10dbc3ae7eb56869d10  learn/run_di_domain_pilot_v2.py
9ef6e8d3301c9c41de4ed497e5a4c9589c508d6c07034e65c658b6d8fdf702e6  match/__init__.py
fbb9a8250e4751cf578e02b7e06bb5f5ffad784cd3bfea97815890d92d3aaade  match/renderer.py
7a43e2741583dcfe91d16d359104f094f6ac4cb326c176d678a25311d4442887  match/renderer_au.py
c27a532cf2419d4dd2f8c6a1db0646acf6d82621f9751bb6a0bc1de5bb292f96  packs/__init__.py
afa9cf96387b1397dccf752862e8bf115f46ef7f3c30f6a8b7168fc5fd8670ba  packs/loader.py
0d81b1540d76f66f5d75889d8615a2bc30007ab16b2482b461d9bb69d9a67ad0  packs/morgan/manifest.json
0df8864f17e1c8c704fbc13ef5693b2978cdf4f01c238d0f12021c3f9d45f39b  research/render_preset_panel.py
d57a78cb78e527db66748937c4b206df4cae0f9633cb87797b06344c6e895ac3  samples/Example_Clean_PR12.xml
33ce25338ac5a2f3713694e5bf7fee8182bd85f4a4cf06f684ec2cc9647a6428  scripts/_cli.py
f1211cc98ab82e269d676a96005b1cab7a873fbcb07e7b46538c63d7b3d17e96  scripts/_swift.py
1f05a301e64a71496400d5a8129279dfd45f90cc08f6984fcca68b9f4cc78537  scripts/au_probe.swift
e1f9a375e7b331edc938e9f671fe20d27b49597da72c4d290d9e68ed2c578e3c  scripts/au_render_server.swift
c8bc917e4097222df329cacd5e560702fbef78d6a756d99ea8ec109bc933d787  tests/test_di_domain_pilot.py
c8b8ec0384fd73f09011e640feebf54414ed3253974fbb9dae6758009e3138f9  tests/test_di_domain_pilot_v2.py
01362758e3d4a1609edb755fef11fc5726d9b97e09e2334544a7576f7f5b5c56  tests/test_di_morgan_control.py
e4eba3bd950679d18d5b1df6c2c547d4003511cb85a226db125abc1e76c46dce  tests/test_run_di_domain_pilot.py
```

## Access and evidence limits

Only this review was authored in the repository; synthetic tests created their authorized temporary fixtures. Reads were limited to source/tests, declarations/path/hash manifests, original prerequisite JSON/provenance and earlier review/verification documents. No actual array/audio/catalog/checkpoint/average was opened or hashed, and no new-study result or input waveform hash was computed or inspected. No actual diagnostic, plugin execution, rendering, model inference, training, network operation or Git write occurred.

The actual twelve file hashes, loaded DI hashes, experimental behavior and scientific disposition remain unverified. Approval is for the exact frozen procedure and implementation, with the bounded interpretation above. Main owns archiving/hash attestation, declaration, commit and primary execution, followed by a fresh different result verifier before interpreting any result.
