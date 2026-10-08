# Independent attempt2 design/code review

**Verdict: APPROVE the exact snapshot identified below for declaration and commit. No blocking defects found.**

Reviewed 2026-10-08 on `codex/song-model-continuation`, HEAD `b60964f3cbb519d1b8a018a29a91b695ad541ee4`. This is a fresh independent design/code review before declaration or execution, not experiment result verification. The attempt2 plan is still marked draft. Approval covers its scientific content and the listed implementation; execution still requires the declared, committed sources and the mandatory runtime preflights. Substantive code, input, or procedure changes require another review.

## Findings and evidence

- **Actual Torch32 coefficients, no fallback:** `load_windows` reads only the fixed coefficient archive, checks its compressed and decompressed SHA256, requires exactly all five FFT sizes, decodes unsigned IEEE float32 bits with explicit little-endian dtype, checks each coefficient-byte hash and finiteness, then promotes losslessly to read-only float64 arrays. It never reconstructs Hann coefficients or falls back to the NumPy formula. Independently decoded the actual archive with Ruby's JSON/zlib/IEEE unpacking: all **7,936 Torch32 coefficients** have valid lengths, unsigned bits, finite float32 values, and matching per-window hashes. The decompressed archive hash also matches the independently verified probe's `artifact_sha256.windows.json`.
- **Tolerance and frozen reference:** `TOL` remains absolute **1e-8** and is checked against the correction manifest. Both preflights enforce it. `metric` checks the unchanged global Torch float32 default, compares live CPU default Hann coefficients with the saved coefficients, and compares corrected NumPy against unchanged `direc.mrstft` on the original seed, length, scale, identity/half-gain/roll52/zero cases. It records signal hashes and versions without changing Torch's default dtype or invoking a model. The live comparison is exact numerical equality after lossless promotion; signed zero is not distinguished by `np.array_equal`, which has no effect on these metric magnitudes.
- **Both preflights before asset bytes:** imports are inert with respect to experiment data. `code_inputs` reads source/declaration/window bytes and the original path manifest, checks committed source identity and the original manifest hash, and does not call the original asset loader. `main` requires the explicit CPU environment for metric/infer and project `.venv` for numpy/native/render. `stage_directory` checks passing metric and helper-NumPy reports with identical source pins before native/render/infer can reach `R.frozen_inputs`, the first catalog/model/average byte access. Helper replay independently regenerates all four synthetic signals, requires byte-identical hashes, and compares its own corrected NumPy scores against saved CPU Torch references rather than against itself. Failed/missing replay refuses before native assets.
- **Exclusive outputs and provenance:** metric exclusively creates the run under project `tmp`; every stage exclusively creates its own directory and JSON/array artifacts. Existing failed runs cannot be resumed through this interface. Pins cover both declarations/manifests, the archive, changed implementation/tests, frozen model/reference code, and original render/preset dependencies. Every stage checks its current source bytes against HEAD; later stages require matching metric/replay pins. Render/infer compare native asset provenance before proceeding. Missing prerequisites, changed sources, and existing outputs fail closed; stage exceptions retain failure JSON once dispatch begins.
- **Same coefficients across all arms:** the v2 runner supplies its loaded mapping to native and infer. Native passes it to aligned wet, flatref, FIR, and oracle; infer passes it to native network, Morgan network, and Morgan input baseline. `score_prediction` propagates it to both primary and raw-DI low-band MR-STFT. Mapping validation precedes FFT/filter work and native/infer asset/model work. Omitting the optional keyword preserves the original utility behavior. Synthetic orchestration tests exercise all 84 scorer calls and 168 primary/low-band calls over twelve mocked takes, including the default path.
- **Original scientific rules preserved:** the only changes to the original utility/runner are explicit-window validation and propagation. Selection, bounded reads, lag/polarity, calibration/score separation, QC thresholds, canonical target/EQ, normalization, FIR fit/intercept/support/reflected evaluation context, native +52 timing, Morgan pre-roll/latency, repeatability canary, frozen inference, coverage, and decision gates are unchanged. Static tracing and synthetic fixtures cover these dependencies. Native invalid coverage blocks rendering; incomplete render/native reports block model loading. The original strict wins/group medians, inclusive 10% roundoff treatment, oracle threshold, and control-dependent inconclusive disposition remain intact.
- **Frozen material preserved:** read-only comparison against archived implementation commit `8e5a91b` showed no differences in the original procedure, original input manifest, `learn/direc.py`, `learn/di_robustness.py`, or any other original `R.PINNED` dependency except the two explicitly reviewed utility/runner files. No final/reserved procedure was changed. Concurrent changes observed during review were only the permitted navigation files (`docs/README.md`, `docs/ROADMAP.md`, `docs/di-recovery-plan.md`, `learn/README.md`); all eight reviewed source/plan/test hashes stayed identical from initial capture to final check.

## Verification performed

```text
PYTHONDONTWRITEBYTECODE=1 /Users/yoavbz/.codex/bin/neuraldsp-safe pytest -n0 -p no:cacheprovider tests/test_di_domain_pilot.py tests/test_run_di_domain_pilot.py tests/test_di_domain_pilot_v2.py -q -rs
142 passed, 2 skipped in 2.20s
```

Both skips are the existing optional Torch parity parametrizations at `tests/test_di_domain_pilot.py:651`: Torch is unavailable in the approved helper environment. No pytest workers were used. Meaningful passing coverage includes analytic DC/impulse/explicit-window metrics; malformed-window refusal before computation; default-result identity; calibration/FIR isolation from evaluation and guard margins; fixed timing, filtering and EQ; QC/gate boundaries; complete declared coverage; renderer cleanup with a fake renderer; all-arm propagation with fake model inference; strict archive corruption/bit/hash/coverage refusal; exclusive outputs; changed-pin refusal; and absent/failed/malformed helper replay refusal before assets.

Also independently checked actual archive hashes/coefficients, source stability, unchanged frozen dependencies against `8e5a91b`, and `git diff --check` for the changed tracked source/tests (clean).

## Exact reviewed hashes (SHA256)

| File | SHA256 |
| --- | --- |
| `docs/di-domain-pilot-v2-plan.md` | `9b98b5936616bb417942b85adf3f03fee924331b3ce645f82a747abd573d6940` |
| `docs/di-domain-pilot-v2-inputs.json` | `fe501e97053276208020e56a8bce8ba1689237795c3d232b18ceadc74b2421dc` |
| `learn/run_di_domain_pilot_v2.py` | `397a8abd55a516047288b789db1375c21c5cbf89a1b3e10dbc3ae7eb56869d10` |
| `learn/di_domain_pilot.py` | `338abb963b122f3bc6710e45253674829f2db2be585a0fd56164f36323088076` |
| `learn/run_di_domain_pilot.py` | `729c87be7b85e8f62cc474469262085c0346d7a4363dff28480797ec6b433bbf` |
| `tests/test_di_domain_pilot_v2.py` | `c8b8ec0384fd73f09011e640feebf54414ed3253974fbb9dae6758009e3138f9` |
| `tests/test_di_domain_pilot.py` | `c8bc917e4097222df329cacd5e560702fbef78d6a756d99ea8ec109bc933d787` |
| `tests/test_run_di_domain_pilot.py` | `501bfd3e19607e49ae43b98acb706a87b22105cbef37e3c2accb472f0dd36184` |
| `docs/di-domain-pilot-plan.md` (unchanged) | `3fe8a65c46c216f360dbca8e472eaedaea4b261a85a4a47f924f7c74b9592465` |
| `docs/di-domain-pilot-inputs.json` (unchanged) | `3220d15a5dfbfb40ee39462377e88104cc8c3a6f6cfcabb4aa2f7d80613e8930` |
| `learn/direc.py` (unchanged) | `43b698ba69fc97d91b547e9948b9b0611dec7b01453eef43609e365a85885969` |
| `learn/di_robustness.py` (unchanged) | `072dfe5dfd1fc892eef1449ad6ab9d7a2725e2ddb701311714437d95aba27fb1` |
| `docs/di-domain-metric-probe-results.md` | `974757203c40796bdf82be8bef354808aa6b43fff78c7ba151c211450709b6a3` |
| `docs/di-domain-metric-probe-verification.json` | `e8303d458ffc91917c4ba373375570578f4a1be75b3ed501db3bb56a7c8bccbc` |
| `docs/di-domain-metric-probe-windows.json.gz` | `41a9dae241f2090fc5a1e7f3b73f3b628741b05e1ad85811af750045dbca93bc` |
| Decompressed coefficient JSON | `374cacf4a401139e681fc9c43088ff58d2c9e9c47748d73785b61fb9b7e915fc` |

## Limitations and scope

No actual experiment stage was run, including metric or helper replay. Live CPU Torch coefficient/parity checks remain mandatory at execution; this review does not claim they passed. Synthetic tests cover mocked stage calls and temporary synthetic arrays only. No recording, dataset catalog, checkpoint, average asset, actual experiment `.npy`/`.npz`, or reserved data was accessed. The permitted saved coefficient-bit archive was read. The independently verified synthetic-cause report was treated as prior evidence, not independently re-executed result verification.

This review does not establish native QC, renderer stability, inference correctness on real assets, recovery quality, or any experiment outcome. Post-execution independent recomputation remains required. The fifteen-minute budget is cooperative, and external monitoring remains necessary for stuck library calls. Prerequisite/loader failures occurring before the dispatch `try` fail closed but may not produce `failure.json`; this does not permit progression or overwrite evidence.

No git mutation, download, network operation, child review agent, model inference, real rendering, training, or resumption of the first failed run occurred. The only authored repository file is this review; implementation fixes belong to main.
