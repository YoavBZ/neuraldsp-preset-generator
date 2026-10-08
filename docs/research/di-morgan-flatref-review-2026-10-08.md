# Fresh fixed-render Morgan flatref design/code review

**Verdict: APPROVE this exact draft snapshot for administrative declaration and commit. No blocking findings.**

Reviewed 2026-10-08 on `codex/song-model-continuation`, HEAD `a5b96052bb16d6a3695b4040a9b3923ba90de645`. This is a fresh code/design review before declaration, commit and new diagnostic computation. Main owns code fixes, navigation, declaration and commit. The result archives and four new diagnostic files are currently uncommitted, as expected.

Approval covers the scientific content and implementation identified below. Replacing the draft status with declaration/approval metadata and a review link is an administrative change. Changes to inputs, code, timing, scoring, gates or procedure require review of the changed snapshot. This review does not itself execute or verify the new diagnostic.

## Prerequisite and provenance

- The archived original result is complete and passes the original standalone gate. The independent verification has status `VERIFIED_WITH_EVIDENCE_LIMITS`, 767 passing checks, no failures, twelve preparation rows, twelve replay rows and a passing independent screen. Its pinned revision is the current `a5b9605` revision. All twelve recorded checkpoint-replay byte comparisons pass with zero error and byte identity. The archived primary screen equals the independently derived screen, including the reported 72.17797505% median improvement over wet audio. These are checks of existing evidence, not fresh numerical replay.
- The archived prepare, render and inference JSON files are byte-identical to their original run reports. The archived verification JSON is byte-identical to its saved verification report. Preparation, inference and independent replay identities match the original path manifest in order; all twelve preparation QC records pass and all canonical-primary oracles are zero.
- All **35 inherited source/declaration/preset/coefficient pins** match their current file bytes and HEAD. They equal the independent verification's `source_pins`, the original infer provenance, and every recorded stage's provenance. This includes `scripts/_swift.py`. The independent verifier source hash also matches `verifier_sha256` in the archived verification. No original control source has changed.
- The new guard first rejects a draft, then calls `C.code_inputs()` for the inherited committed-source checks and checks each of its eight own dependencies against HEAD. It requires the successful original result and successful machine-readable independent verification, then byte equality of the archived original stage reports. Its source comparison is correct for this snapshot: the eight new pin names are disjoint from the 35 inherited names, so `set(pins) - set(OWN_PINS)` recovers exactly the original source set. Comparing the full new 43-entry mapping directly to old provenance would be wrong; this implementation correctly excludes the eight new entries.
- The prerequisite verification is an exact reviewed archive, pinned against HEAD before execution. Its current contents establish the complete independent checks described above; the guard's status/check-success predicate alone should not be treated as a general verifier for arbitrary replacement reports.

## Inputs, computation order and science

The hash manifest contains exactly **36 unique, syntactically valid SHA256 entries**, twelve each under the original `prepare`, `render` and `infer` directories. Its path set exactly equals the three stages crossed with all twelve original manifest slugs. `input_hashes()` rejects missing, duplicate, undeclared, escaping or changed artifacts before loading score arrays. I did not hash or open the actual array files; their declaration-time hashes are accepted under the review's stated scope.

The CLI checks the project helper environment and completes the declaration/committed-dependency/prerequisite guard before loading numerical assets. Imports of the new module and its C/P/R/V dependencies do not open experimental arrays, raw audio, checkpoints or the catalog. The manifest is used as fixed path/identity metadata; `R.frozen_inputs()` and `C.assets()` are never called. There is no model construction, inference, rendering, fitting, training, download or reserved-data path in this diagnostic.

`run()` requires complete original prepare/render coverage, checks all 36 file hashes, and verifies the frozen average's declared hash before loading it. The average identity agrees with the independently verified original asset: `9aa3c3bfefc2bc5ba21394be29876b5ef5e0120ad2f55f0b890e599ec3bee9a8`. The model is only an inherited manifest identity; its checkpoint is never accessed by this diagnostic.

The first loop loads only saved score DI/target, latency-corrected render `baseline`, and frozen `prediction`. It recomputes both arms' primary, canonical waveform L1 and raw-DI low-band scores: **12 × 2 × 3 = 72 scalar comparisons**, each finite and within absolute `1e-8` of the archived result. All twelve must finish successfully and `baseline-replay.json` must be saved before the second loop can call `canonical_target` or score flatref. A mismatch writes a failed replay report and raises; it cannot reach experimental scoring. Nonfinite replay scores also raise before experimental scoring.

The experimental stand-in is precisely `P.canonical_target(wet, average)`. Its inputs are the saved six-second wet baseline and frozen average. The target DI is supplied only to scoring, never to stand-in construction. The unchanged own smoothed spectrum, mean-dB removal, ±15 dB clamp and six-second FFT interpolation/EQ are inherited from the approved P implementation. There is no fitted target gain, delay, polarity or filter.

Every scoring call receives the same `windows` object from `V.load_windows(correction)`. That loader validates archive/raw-text hashes, all five FFT sizes and exact saved Torch32 coefficient bits, returning immutable coefficient arrays. There is no reconstructed-Hann fallback in this execution path. The NumPy primary retains center-three-second independent standard-deviation normalization to 0.1, and the diagnostic losses keep their original canonical/raw targets. The archived CPU metric and actual-helper NumPy preflights passed at `1e-8`; code and coefficient identities remain unchanged. The new mandatory 72-scalar replay checks the actual execution environment again against the saved real-panel scores before flatref scoring.

Timing is fixed by artifact reuse: the original renderer saved network input from wet offset `2*SR`, retaining raw latency, and baseline from `2*SR+52`, advancing exactly 52 samples to DI time. This diagnostic uses that baseline for both simple arms, preserves the saved prediction and canonical target, and applies no additional alignment, crop selection or rendering. It does not remeasure physical latency.

## Gate, outputs and failure handling

The primary comparison correctly uses `min(wet, flatref)` per take and computes each relative improvement before taking medians. All three primary losses must be finite, nonnegative real scalars, and both simple baselines must be positive. Inherited `C.compare()` enforces all twelve unique declared identities, six chords/six scales, QC validity and valid oracles. The new comparison then requires median improvement ≥10%, at least nine strict wins and strictly positive medians in both groups. The eight-ULP allowance is confined to the inclusive 10% boundary. The original median-only standalone gate is not silently reused as the complete new gate.

Each output row retains wet/net/flatref primary losses and all three score dictionaries; the chosen simple baseline is deterministically recoverable as their minimum. Per-take improvements, wins, both group medians and the final disposition are saved. Twelve stand-in waveforms are saved individually. Valid failures produce `FAIL`; invalid comparison data produce `INCONCLUSIVE`.

The output directory must resolve under project `tmp` and is created exclusively. Provenance records all 43 source pins, Python and NumPy/SciPy versions. Waveforms and JSON reports use exclusive creation; progress is retained incrementally inside the new directory. Exceptions during coefficient loading or the run preserve `failure.json`. A replay mismatch preserves its partial replay report. Earlier declaration/commit/prerequisite or directory-creation refusals occur before the run's failure handler; the declared external log is the evidence for those refusals. The plan supplies that log path, while the runner itself prints progress rather than opening the log. Existing result artifacts are preserved.

The 15-minute budget is cooperative and checked across both loops, including before experimental work and before final results. It cannot interrupt a running library call; the draft correctly states this limit.

The plan interprets this as a stronger standalone development baseline comparison on one fixed Morgan chain. It supports no native-transfer, shipping, multi-guitar, driven-chain or preset-ranking conclusion. Failure does not justify longer training by default. Fresh independent reconstruction of stand-ins, scores, coverage and gate remains required before decisions.

## Synthetic test evidence

Executed through the user-approved helper, with workers and pytest cache disabled:

```text
/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -n0 -p no:cacheprovider tests/test_di_morgan_flatref.py tests/test_di_morgan_control.py tests/test_di_domain_pilot.py tests/test_run_di_domain_pilot.py tests/test_di_domain_pilot_v2.py -q -rs
188 passed, 2 skipped in 2.40s
```

The helper disables Python bytecode writes. The two skips are existing optional Torch parity tests at `tests/test_di_domain_pilot.py:651`, because Torch is absent from the helper environment. No diagnostic, model replay or real-data metric was run. The new tests cover the stronger gate, invalid baselines, draft refusal, exact hash-manifest coverage and a final-take replay mismatch that prevents every flatref call. Existing synthetic tests cover inherited identity/QC/oracle gates, timing, coefficient validation/propagation, source pins, output exclusivity and prerequisite ordering. The new declared guard's complete happy/error paths are assessed here by code inspection and archive/pin comparisons; its direct new test covers draft refusal only.

`git diff --check` passed. The eight snapshot hashes below were captured twice and remained identical. All 35 inherited dependencies were checked unchanged from HEAD. Navigation changes remain main's work.

## Exact reviewed snapshot

| File | SHA256 |
| --- | --- |
| `docs/di-morgan-flatref-plan.md` | `8bd265ac44eb543490ce64be6fcf1d719699d20c4333082e14521e47ba7985f8` |
| `docs/di-morgan-flatref-inputs.sha256` | `404ad70b3274a373df539c33119657c4db4353ef81d59d6c7ed72f573c7ee5e9` |
| `learn/di_morgan_flatref.py` | `57e45bae65d169630d45c89a672490fd7c58e4bb9015f746092cf3304470d94c` |
| `tests/test_di_morgan_flatref.py` | `c7b59d340c522a34f637c742a3c22c72b6a3b651af02db122d73852f297a7a4d` |
| `docs/di-morgan-control.json` | `d4c300ba34377d01e8ea248ce18c00a9bd499b3dd7af09ecdcaf7d8c12459add` |
| `docs/di-morgan-control-verification.json` | `58f74aca051f27ab0996efeefa1016a7d963143bb56cb845578a3954a311581b` |
| `docs/di-morgan-control-prepare.json` | `0c778956c77976118241d163a7e98145daa5d2e8949b470972b9bac40562e615` |
| `docs/di-morgan-control-render.json` | `bce09a1ac61cb98d8ece960a808e203a36f7edf461c4509f9606a10ffae6eaeb` |

The 35 inherited pins are enumerated in the archived verification's `source_pins`. SHA256 of their lines formatted `hash + two spaces + relative path + newline`, sorted using `LC_ALL=C sort`, is `dac18ee616eee44b5ff6c586e44daf42f757fe59557958e4c3f6ee5f9f1c21ac`. The corresponding **43-entry draft execution pin set**, including the eight files above, has digest `b71af9c9d2238ca4d077c5d8f8aaf371e68527c084ad4769a928e4bb9e88c552`. Administrative declaration will necessarily change the draft plan hash and the latter aggregate.

The verifier source hash is `8ab45b7b5cf56a3535baa0ebf624fcb8ddcaff384f10632c761ba7896f3b7eb6`. Supporting archived preflight hashes are `9395a956e3c18f52d95a4f763288e834750e063e19deea3e086fa25c8e441044` (CPU metric) and `ec0b41827951406b035db01c45bfbdd8d5dc53b95d7d0aee64a0d362a8399f40` (helper NumPy replay); the latter records the former's hash.

## Access and evidence limits

Only this review file was authored in the repository. Reads were limited to source/tests, declarations/path/hash manifests, prior JSON/provenance and review documents. Synthetic tests used temporary fake arrays, models and renderers. No actual NPZ/NPY, raw audio, checkpoint, frozen average or dataset catalog was opened or hashed. No actual diagnostic, rendering, inference, training, network operation, Git write, child agent or pytest worker was started.

The old verification's evidence limits carry forward: full wet renders survive only for the first take/canary; the other eleven full-render hashes/peaks and wet pre-roll cannot be reconstructed; the host log lacks an independent parameter-command transcript; fixed slicing does not remeasure physical latency. This review checks the archived verification's consistency and source identities, and does not repeat its 767 numerical checks. The new diagnostic's real-array replay, flatref results and independent result verification remain future work after administrative declaration and commit.
