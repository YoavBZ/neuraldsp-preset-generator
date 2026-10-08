# Fresh independent known-DI Morgan control review

**Verdict: REQUEST CHANGES. One concrete blocker; this snapshot is not approved for declaration/commit/execution.**

Reviewed 2026-10-08 on `codex/song-model-continuation`, HEAD `2baf2e3f86cce31d01057ed4f8e5690e409749e6`. This is a fresh design/code review before declaration and computation, not result verification. Main owns implementation fixes and navigation documents.

## Blocking finding

**[P1] Pin the Swift build helper used by the actual render path.** Location: `learn/di_morgan_control.py:25–38` (effective dependency set inherited from `learn/run_di_domain_pilot_v2.py:24–28` and `learn/run_di_domain_pilot.py:26–36`).

`scripts/_swift.py` is absent from the union of all 34 pinned dependencies. However, rendering with a new exclusive `au-host` directory calls `AudioUnitRenderer._ensure_server` (`match/renderer_au.py:480–494`), which calls `_compile`; `_compile` imports and executes `_swift.compile_swift` (`match/renderer_au.py:615–621`). This helper selects compiler flags, SDKs and cached executables and copies/builds the executable that hosts the plugin. It is an active transitive dependency, not an unused optional import.

Consequently, an uncommitted change to that helper, or a change between the metric/replay and render stages, does not change the checked pin mapping and is not rejected before assets/rendering. The renderer's own build identity also omits this helper (`match/renderer_au.py:690–715`), so its metadata does not repair the omission. For example, changing `FLAGS` in `_swift.py` changes build behavior while every current source guard still accepts the run. This violates the requested all-transitive-dependencies freeze and the plan's requirement to pin code before every stage. The omission is inherited from the prior runner; prior approval does not satisfy this explicit requirement in the new control.

Required fix: include `scripts/_swift.py` in the control's committed-source/provenance pins (adding it to `OWN_PINS` is sufficient and avoids changing the closed pilot). Add a synthetic regression showing that helper drift fails before asset/catalog access and that its hash participates in the prerequisite pin comparison. Re-review the changed exact snapshot before administrative declaration and commit. No experiment is needed to fix or verify this guard.

Observed helper SHA256: `f1211cc98ab82e269d676a96005b1cab7a873fbcb07e7b46538c63d7b3d17e96`.

## Requirements checked

- **Separate scientific question and complete panel:** the new entry point obtains the original manifest/catalog selection through `R.frozen_inputs`, including all twelve original DIs, six chords and six scales. It never filters by the three passing native rows or reads a native result. `prepare` reads only each declared `di`; microphone paths and catalog lag metadata are used only in the inherited metadata-selection consistency check, never to read microphone audio or fit/apply alignment. Preparation strips the guards directly.
- **Original source timing, level and target:** `P.read_bounded` reads exactly ten seconds plus 512 samples on each side at 48 kHz, float64, averaging channels. Raw 0–4 and 4–10 seconds receive the original separate waveform QC. The six-second target uses the unchanged frozen-average/own mean-removed smoothed spectrum, ±15-dB clamp and FFT EQ. `render_di=di[2*SR:]` preserves original amplitude over seconds 2–10.
- **Original Morgan chain and timing:** the only shared renderer change is the validated keyword-only `source_stage`, defaulting to `native`. The new caller uses `prepare` and requires its own complete valid twelve-row report. Shared PR12+R edits, one reused host, discarded first warm-up, immediate repeat canary, original RMS/band gates, saved canary waves/metadata and `finally` cleanup remain intact. The renderer pads 52 samples; network input retains raw latency and the input-as-DI baseline advances exactly 52 samples. There is no new normalization or fitted timing in rendering.
- **Metric and actual helper replay before assets:** `main` checks explicit environments and committed code/declarations/manifests, loads coefficient bytes, and calls `V.stage_directory` before `assets`. All prepare/render/infer dispatches require passing metric and helper replay reports with matching pins. Metric retains the four original synthetic cases, default Torch32 Hann coefficients, absolute 1e-8 gate and identity <1e-6. Replay regenerates byte-identical signals and compares against saved Torch scores. This ordering is correct, subject to the missing dependency above.
- **Exact coefficients throughout:** explicit saved Torch32 windows reach the preparation oracle and both inference arms, including their raw-DI low-band diagnostics. Independent Ruby decoding confirmed all five FFT sizes, all 7,936 finite coefficient values and all per-window byte hashes; decompressed archive SHA256 is `374cacf4a401139e681fc9c43088ff58d2c9e9c47748d73785b61fb9b7e915fc`. No new metric/replay stage was run.
- **Frozen inference and standalone gate:** the unchanged fold2 model and average paths/hashes come from the original manifest. `assets` explicitly records observed model/average hashes after matching the declarations. Inference loads CPU weights with `weights_only=True`, calls unchanged `D.rebuild` on float32 six-second render input, and scores the same canonical target using the original independent center-three-second std normalization, waveform L1 and raw-DI low-band diagnostic. `rebuild` supplies `torch.no_grad`. The gate requires complete identities/QC/oracles and positive finite baseline losses, then median Morgan improvement ≥10%, allowing only eight `ulp(0.1)` at the boundary. Strict wins and group medians are diagnostics only.
- **Isolation and failures:** inherited run/stage/output creation is exclusive under project `tmp`; both preflight pin comparisons precede assets. New preparation/render/infer use their own stages and preserve progress/partial outputs. Dispatch exceptions write failure JSON. Pre-dispatch prerequisite errors fail closed without necessarily creating failure JSON, as in the reviewed prior runner. No fake successful native report is produced.
- **Interpretation:** the plan keeps the native screen closed and explicitly excludes native-transfer/product/preset-ranking claims, long training, fitting, replacement takes and reserved material. Fresh independent post-run recomputation of preparation, scores, coverage/gate and predictions from the pinned model/saved inputs remains mandatory. Passing this design review cannot substitute for that verification.

## Synthetic verification

Executed only the authorized synthetic helper suite, with pytest workers and cache output disabled:

```text
PYTHONDONTWRITEBYTECODE=1 /Users/yoavbz/.codex/bin/neuraldsp-safe pytest -n0 -p no:cacheprovider tests/test_di_morgan_control.py tests/test_run_di_domain_pilot.py tests/test_di_domain_pilot_v2.py tests/test_di_domain_pilot.py -q -rs
177 passed, 2 skipped in 2.33s
```

Both skips are the existing optional Torch parity cases at `tests/test_di_domain_pilot.py:651`, because Torch is absent from the helper environment. Mandatory runtime CPU metric and actual-helper replay remain outstanding. Passing tests cover synthetic preparation and inference, all twelve identities, gate boundaries/inconclusive cases, fixed timing/level, both renderer source stages, failed canary/identity/host cleanup, invalid preparation coverage before renderer imports, coefficient guards and prerequisite/exclusive-output behavior. They do not currently catch the missing Swift-helper pin.

`git diff --check` passed. The five requested snapshot hashes and HEAD were unchanged between initial capture and final check. Concurrent changes appeared only in the permitted navigation files. Existing shared P/V scientific sources and manifests retain the hashes below.

## Exact reviewed SHA256 hashes

| File | SHA256 |
| --- | --- |
| `docs/di-morgan-control-plan.md` | `5625dad502347036a188272c7a7c08e66add4904ef0a6b080a690e73c3063f68` |
| `learn/di_morgan_control.py` | `be95e7ae896e283908ad66deb419cf71a7ac9ee733279da353ea10963b3e2814` |
| `tests/test_di_morgan_control.py` | `dddcb9c4469d95dd8424b731cbbdc4c87878233198d3948bc77348d39108558a` |
| `learn/run_di_domain_pilot.py` | `e2ba7db8935b4602f86658dba57c67a6918c6fa824852e8d118ed7632a36bb79` |
| `tests/test_run_di_domain_pilot.py` | `e4eba3bd950679d18d5b1df6c2c547d4003511cb85a226db125abc1e76c46dce` |
| `learn/di_domain_pilot.py` | `338abb963b122f3bc6710e45253674829f2db2be585a0fd56164f36323088076` |
| `learn/run_di_domain_pilot_v2.py` | `397a8abd55a516047288b789db1375c21c5cbf89a1b3e10dbc3ae7eb56869d10` |
| `tests/test_di_domain_pilot.py` | `c8bc917e4097222df329cacd5e560702fbef78d6a756d99ea8ec109bc933d787` |
| `tests/test_di_domain_pilot_v2.py` | `c8b8ec0384fd73f09011e640feebf54414ed3253974fbb9dae6758009e3138f9` |
| `docs/di-domain-pilot-plan.md` | `3fe8a65c46c216f360dbca8e472eaedaea4b261a85a4a47f924f7c74b9592465` |
| `docs/di-domain-pilot-inputs.json` | `3220d15a5dfbfb40ee39462377e88104cc8c3a6f6cfcabb4aa2f7d80613e8930` |
| `docs/di-domain-pilot-v2-inputs.json` | `fe501e97053276208020e56a8bce8ba1689237795c3d232b18ceadc74b2421dc` |
| `docs/di-domain-metric-probe-windows.json.gz` | `41a9dae241f2090fc5a1e7f3b73f3b628741b05e1ad85811af750045dbca93bc` |

The union of current R/V/control pin names has 34 entries. SHA256 of sorted lines formatted as `sha256 + two spaces + relative path + newline` is `e88de027d8cc5365d14b2e8b867266a0e856024bb749ec3ae9b338f61d932f88`. This identifies the effective source set and does not cure its missing dependency.

## Access and review limits

Read only repository source, tests, declarations, path manifests, the saved coefficient archive, and prior closed-result/independent-verification documentation. No actual dataset catalog, audio, checkpoint, frozen-average asset, reserved material or experiment array was accessed. Synthetic tests used temporary fake data/models/renderers only. No experiment stage, actual rendering/inference, training, download, network operation, child review agent or Git write occurred. The only authored repository file is this review.

After the pin fix and fresh approval of its exact changed snapshot, only administrative declaration and commit should follow this review. Both execution preflights and fresh independent result recomputation remain required later.

## Final re-review after Swift-helper pin fix — 2026-10-08

**Final verdict: APPROVE the exact corrected snapshot below for administrative declaration and commit. No remaining blockers found. This verdict supersedes the initial REQUEST CHANGES above; the initial finding and evidence are retained.**

Branch remains `codex/song-model-continuation`, HEAD `2baf2e3f86cce31d01057ed4f8e5690e409749e6`. Before appending this section, the review file was byte-identical to main's preserved `tmp/di-morgan-control-review-first.md`. That preserved copy was not modified.

Re-read the complete corrected control implementation and tests. `OWN_PINS` now includes `scripts/_swift.py`, so `C.code_inputs` checks its current bytes against HEAD and includes its observed SHA256 in every stage's source provenance before dispatch or asset access. Inherited prerequisite pin comparisons therefore also reject helper changes between stages. The single blocking omission is resolved without changing the closed pilot or renderer behavior.

The new `test_swift_helper_drift_refuses_before_assets_and_changes_prerequisite_pins` exercises the real control pin loop, `C.main` refusal and `V.stage_directory` prerequisite comparison against synthetic files and mocked Git bytes. It verifies the recorded helper hash, rejects a dirty helper before `assets` or creation of `prepare/`, then simulates committing the changed helper and confirms that the previously passing metric provenance cannot unlock the NumPy stage. The fixture neither compiles Swift nor accesses actual experiment material.

Verified the full effective pin set against the first review: removing the newly added Swift-helper entry and substituting the two original control implementation/test hashes reproduces the exact previous 34-entry digest `e88de027d8cc5365d14b2e8b867266a0e856024bb749ec3ae9b338f61d932f88`. Thus every other previously pinned source, declaration, manifest, preset and coefficient archive is unchanged. The five requested snapshot hashes and helper hash were captured again for this re-review. The science remains the original all-twelve known-DI Morgan control, with no microphone alignment, original gain/timing, frozen fold2/average/PR12+R, exact Torch32 scoring and standalone median ≥10% gate. The plan remains draft. Main's navigation edits are outside these frozen scientific dependencies.

### Re-review test evidence

```text
PYTHONDONTWRITEBYTECODE=1 /Users/yoavbz/.codex/bin/neuraldsp-safe pytest -n0 -p no:cacheprovider tests/test_di_morgan_control.py tests/test_run_di_domain_pilot.py tests/test_di_domain_pilot_v2.py tests/test_di_domain_pilot.py -q -rs
178 passed, 2 skipped in 2.35s
```

The two skips remain the optional Torch parity cases at `tests/test_di_domain_pilot.py:651` because Torch is unavailable in the helper environment. `git diff --check` passed. This is synthetic verification only; neither runtime preflight nor any actual control stage was executed.

### Exact approved corrected snapshot (SHA256)

| File | SHA256 |
| --- | --- |
| `docs/di-morgan-control-plan.md` | `5625dad502347036a188272c7a7c08e66add4904ef0a6b080a690e73c3063f68` |
| `learn/di_morgan_control.py` | `b89a40f6aaa9318479b5de2af35a4e4e7a66d017a1d9c16a4fd62caea33d1428` |
| `tests/test_di_morgan_control.py` | `01362758e3d4a1609edb755fef11fc5726d9b97e09e2334544a7576f7f5b5c56` |
| `learn/run_di_domain_pilot.py` | `e2ba7db8935b4602f86658dba57c67a6918c6fa824852e8d118ed7632a36bb79` |
| `tests/test_run_di_domain_pilot.py` | `e4eba3bd950679d18d5b1df6c2c547d4003511cb85a226db125abc1e76c46dce` |
| `scripts/_swift.py` | `f1211cc98ab82e269d676a96005b1cab7a873fbcb07e7b46538c63d7b3d17e96` |

The corrected effective R/V/control dependency set has **35 entries**. SHA256 of sorted lines formatted as `sha256 + two spaces + relative path + newline` is **`c71185a3faef59d9de7496e8bfa0f668bcb178787e98d9dfd3659961b4535b04`**. The unchanged supporting hashes in the first review still apply.

Approval covers the listed draft's scientific content and implementation, followed by replacing its draft status with administrative declaration/approval metadata and committing those reviewed sources. Substantive changes to code, inputs, metrics, timing, selection, gates or procedure require another review. No actual stage execution is authorized by this review. Both mandatory runtime metric/helper replay checks must precede assets at later execution, and fresh independent result recomputation remains mandatory before any verified conclusion, including reproduction of predictions from the pinned model and saved render inputs if inference runs. No long training, shipping or native-transfer claim follows from this approval.

Only this review file was authored during re-review. No actual catalog, audio, checkpoint, average asset, reserved material or experiment arrays were accessed; no actual rendering/inference, experiment stages, downloads, child agents or Git writes occurred.
