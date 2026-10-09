# Fixed Morgan processing coverage

**Declared: 2026-10-09, after fresh independent source/design approval.**

No actual study asset has been hashed or loaded before this declaration.
Execution starts only after this declaration and its exact reviewed sources are committed.

Main owns fresh review, declaration, commits, archive/navigation and execution.
The implementation worker owns only this draft, the new runner and its synthetic
tests. This study does not amend any frozen earlier study.

## Declaration procedure

Before any actual asset hashing/loading or plugin construction, main must obtain
fresh independent source review of the exact runner, test, frozen body and
original48 input-manifest SHA256s. Commit the scientific sources, tests, review,
explicit dependency hashes and declaration together. The review must contain
`Verdict: APPROVE` and the exact source/test/body/input hashes.

The frozen body begins at `## Frozen design` below; hash its following UTF8
bytes, exactly as `T.design_bytes` does. Declaration metadata belongs ABOVE that
heading. Add `**Declared:` and a `processing-approval` HTML comment containing
JSON with these exact fields:

- `status`: `DECLARED`; `fresh_independent_review`: true.
- `scope`: `fixed-pr12-processing-dependent-p2-development-only`.
- `source_sha256`, `test_sha256`, `design_sha256`: exact reviewed snapshot.
- `inputs_sha256`: exact `docs/di-timing-sensitivity-inputs.sha256` snapshot.
- `source_pins`: exact path → SHA256 map for the runner's explicit `SOURCE_FILES`.
  These are source/committed metadata pins, including the source preset and saved
  Hann bits; they are not observed hashes collected after audio access.
- `review`, `review_sha256`: dedicated committed
  `docs/research/di-morgan-processing-*.md` source review.
- `no_asset_access_before_declaration`: true, an explicit main attestation.
- `render_di_authorization`: exactly
  `prepare NPZ render_di only; float64[384000]; exact suffix di[288000]`.

The plan itself and source review are also required to match HEAD. They are
pinned in runtime provenance rather than in the self-referential `source_pins`
map. Every subsequent stage requires exactly the same pins, HEAD and original48
identities. A navigation-only commit before declaration is harmless; any HEAD
change during the attempt closes it.

<!-- processing-approval
{
  "source_sha256": "5ec8c5ca44ccfa94012df14883c9c89ab2a2faa76545c1a025a6b33cf42e8050",
  "test_sha256": "fc181e489575e80840610c7f9f32aef079512779299719573912eecbee07f1e6",
  "design_sha256": "050981984da9f61237cf9afcbe41b697516f5edd20a4a80c86f2d018c0fcf28b",
  "inputs_sha256": "1c6cde4a6bdaa5ceb71fd43e56a21049cffb2bbd023a359d8f7b44de4f6dc527",
  "source_pins": {
    "learn/di_morgan_processing_control.py": "5ec8c5ca44ccfa94012df14883c9c89ab2a2faa76545c1a025a6b33cf42e8050",
    "tests/test_di_morgan_processing_control.py": "fc181e489575e80840610c7f9f32aef079512779299719573912eecbee07f1e6",
    "learn/__init__.py": "950da993349f85949c8094f0787bcf1b56f149cf3a7a829f8b7986bea7c3525d",
    "learn/di_timing_sensitivity.py": "53259e254d262c30c7524ba8e49887c8821455e5b7aaf48c06c39cd2a7458b78",
    "learn/di_morgan_flatref.py": "57e45bae65d169630d45c89a672490fd7c58e4bb9015f746092cf3304470d94c",
    "learn/di_morgan_control.py": "b89a40f6aaa9318479b5de2af35a4e4e7a66d017a1d9c16a4fd62caea33d1428",
    "learn/di_domain_pilot.py": "338abb963b122f3bc6710e45253674829f2db2be585a0fd56164f36323088076",
    "learn/run_di_domain_pilot.py": "e2ba7db8935b4602f86658dba57c67a6918c6fa824852e8d118ed7632a36bb79",
    "learn/run_di_domain_pilot_v2.py": "397a8abd55a516047288b789db1375c21c5cbf89a1b3e10dbc3ae7eb56869d10",
    "learn/direc.py": "43b698ba69fc97d91b547e9948b9b0611dec7b01453eef43609e365a85885969",
    "learn/di_robustness.py": "072dfe5dfd1fc892eef1449ad6ab9d7a2725e2ddb701311714437d95aba27fb1",
    "research/__init__.py": "06419b6d174973c7245cbe10636040bf9f24c27a97e8d038aa8f8a6349eb65ff",
    "research/render_preset_panel.py": "0df8864f17e1c8c704fbc13ef5693b2978cdf4f01c238d0f12021c3f9d45f39b",
    "scripts/_cli.py": "33ce25338ac5a2f3713694e5bf7fee8182bd85f4a4cf06f684ec2cc9647a6428",
    "scripts/_swift.py": "f1211cc98ab82e269d676a96005b1cab7a873fbcb07e7b46538c63d7b3d17e96",
    "scripts/au_render_server.swift": "e1f9a375e7b331edc938e9f671fe20d27b49597da72c4d290d9e68ed2c578e3c",
    "scripts/au_probe.swift": "1f05a301e64a71496400d5a8129279dfd45f90cc08f6984fcca68b9f4cc78537",
    "match/__init__.py": "9ef6e8d3301c9c41de4ed497e5a4c9589c508d6c07034e65c658b6d8fdf702e6",
    "match/renderer.py": "fbb9a8250e4751cf578e02b7e06bb5f5ffad784cd3bfea97815890d92d3aaade",
    "match/renderer_au.py": "7a43e2741583dcfe91d16d359104f094f6ac4cb326c176d678a25311d4442887",
    "packs/__init__.py": "c27a532cf2419d4dd2f8c6a1db0646acf6d82621f9751bb6a0bc1de5bb292f96",
    "packs/loader.py": "afa9cf96387b1397dccf752862e8bf115f46ef7f3c30f6a8b7168fc5fd8670ba",
    "packs/morgan/manifest.json": "0d81b1540d76f66f5d75889d8615a2bc30007ab16b2482b461d9bb69d9a67ad0",
    "format/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "format/parser.py": "93586273c398f766cce82bb043923416a2a1fbec191d29b87797b395105b4e88",
    "format/structured.py": "00880b4373a5300c6a285652dc310fa21d9e1b6bc65bdb1feecebb91920b5279",
    "format/markers.py": "bd29491dd3fdeebd656d6bafce71d101570bd40c9a9b0848336c1d93fcbd76f7",
    "format/translate.py": "8dd3de2a011aa4d829cae050576eb6348c3fd76482cecb582de9ebfe90484dea",
    "format/writer.py": "0ba5e099478d993dc1a01361a2733cfc59079929c07311b3983797b63fc78ca5",
    "samples/Example_Clean_PR12.xml": "d57a78cb78e527db66748937c4b206df4cae0f9633cb87797b06344c6e895ac3",
    "docs/di-domain-pilot-inputs.json": "3220d15a5dfbfb40ee39462377e88104cc8c3a6f6cfcabb4aa2f7d80613e8930",
    "docs/di-domain-pilot-v2-inputs.json": "fe501e97053276208020e56a8bce8ba1689237795c3d232b18ceadc74b2421dc",
    "docs/di-domain-metric-probe-windows.json.gz": "41a9dae241f2090fc5a1e7f3b73f3b628741b05e1ad85811af750045dbca93bc",
    "docs/di-timing-sensitivity-inputs.sha256": "1c6cde4a6bdaa5ceb71fd43e56a21049cffb2bbd023a359d8f7b44de4f6dc527",
    "docs/di-timing-sensitivity-inputs.json": "7663c5271b282383276f2e5f9596f02d8d3f2838527a00dc6934f7721aecdbc5",
    "docs/di-morgan-flatref.json": "767e9345a556e0222f8909db6ccc8ba503c5acadd493962688bf95bb8f323d3e",
    "docs/di-morgan-flatref-verification.json": "c4d76098303fb09077f612900c53d278b1b7144d4989ebe4cbd328e5b091018f",
    "docs/di-morgan-control-verification.json": "58f74aca051f27ab0996efeefa1016a7d963143bb56cb845578a3954a311581b",
    "docs/di-morgan-control-prepare.json": "0c778956c77976118241d163a7e98145daa5d2e8949b470972b9bac40562e615",
    "docs/di-morgan-control-render.json": "bce09a1ac61cb98d8ece960a808e203a36f7edf461c4509f9606a10ffae6eaeb"
  },
  "status": "DECLARED",
  "fresh_independent_review": true,
  "scope": "fixed-pr12-processing-dependent-p2-development-only",
  "review": "docs/research/di-morgan-processing-review-2026-10-09.md",
  "review_sha256": "6a89305a1c26e87483444ef451e7c85c222217b1c1f2108b568294b2f536dd0c",
  "no_asset_access_before_declaration": true,
  "render_di_authorization": "prepare NPZ render_di only; float64[384000]; exact suffix di[288000]"
}
processing-approval -->

## Frozen design

### Question and limits

Does frozen fold2 DI recovery retain its benefit across three fixed actual PR12
processing changes, on ALL12 existing dependent P2 development performances?
The song-only, average-guitar target is unchanged. This is Morgan-domain coverage.
It provides no native, song, preset or product proof, no causal attribution and
no augmentation or training justification. Twelve performances from these
existing sources are not twelve independent players or guitars.

No sweep, fit, search, lag/gain fitting, model/preset updates, rejected native
subset, training, download, raw recording/catalog/native/reserved access, or
threshold/subset/rerun rescue. Any failure closes this attempt. Numerical or
coverage/drift/budget errors are INCONCLUSIVE with priority over valid scientific
FAIL. Valid complete failed F gates are FAIL. Every primary report is INITIAL,
with `independent_verified`:false. A primary clean PASS is an operational barrier
for panel rendering. No scientific decision or verified conclusion is made until
main commissions fresh independent recomputation after primary completion.
Primary/independent disagreement is INCONCLUSIVE.

### Fixed inputs and command changes

Original48 NPZ identities are exactly
`docs/di-timing-sensitivity-inputs.sha256`: twelve each of original prepare,
render, infer and flatref. Original six-second DI/target/wet/prediction/flatref,
plus original raw-latency `net_input` for baseline replay, are reused unchanged.
Only original prepare's NEW `render_di` member is authorized for render stages:
finite native float64 shape384000 (8 seconds), with exact sample AND float64 byte
equality `render_di[96000:] == saved_di`, shape288000. Save its overlap evidence
and render input copies. Baseline/preflight never access this member. Independent
verification uses those newly retained copies, not extra original member access.

Model and average identities are fixed to `docs/di-domain-pilot-inputs.json`:
fold2.pt SHA256 `16b2b734b49cc1cc2d7e547d96d3bb56208007c9cae0d0e33acb1c2a1cdd042b`,
average-fold2.npy SHA256 `9aa3c3bfefc2bc5ba21394be29876b5ef5e0120ad2f55f0b890e599ec3bee9a8`.
New average loading is only for per-wet coherent flatref and unchanged-target
regeneration/oracle. No other average/cache members are authorized.

Derive the full original command only in authorized rendering using
`RP.preset_edits(Example_Clean_PR12, morgan pack, renderer, pr12, True)`. Preserve
the entire ordered base command and all four commands. The original selectAmp is
1 (PR12). R includes the original compressor state, with FX section retained on;
all other amp/EQ/output gain/input amplitude/mic settings are the base values.

| Chain | Exact stored overrides of original base |
| --- | --- |
| clean | None; exact original command |
| volume85 | pr12Amp/pr12Volume=`0.85`; drive1/drive1Active=`false`; drive2/drive2Active=`false` |
| drive1 | drive1/drive1Active=`true`; drive1/drive1Drive=`0.65`; drive1/drive1Tone=`0.5`; drive1/drive1Level=`0.5`; drive2/drive2Active=`false` |
| drive2 | drive2/drive2Active=`true`; drive2/drive2Gain=`0.65`; drive2/drive2Bass=`0.5`; drive2/drive2Treble=`0.5`; drive2/drive2Level=`0.5`; drive1/drive1Active=`false` |

Original PR12 volume must be .62 and both pedals off. Drive chains retain that
volume. Require writable declared switch/rotation kinds and intrinsic normalized
rotation range0..1 (human0..100 via pack formatter). Only declared keys may differ;
redeclaring an already-false switch does not count as a changed key. Keep ordering
and all undeclared values byte-for-byte as command strings.

### Stages, access ordering and persistence

Exclusive fixed run: `tmp/di-morgan-processing-control-20261009`. No alternate
output paths or symlink aliases. CLI has exactly these six stage names and
requires `--run` explicitly. Each stage runs once; failed/closed attempts cannot
be resumed or overwritten. Main selects the already-installed interpreter; the
runner never switches its own interpreter or installs packages.

| Stage | Environment | Required work before next stage |
| --- | --- | --- |
| preflight | project .venv | Replay all108 original scalars using exactly persisted Torch32 Hann bits, original F gate and tolerance1e-8. No model/plugin/average. Save each attempt before raising. |
| baseline | original V.CPU_PREFIX | Require sealed preflight PASS. Replay all108 before model loading, then all12 original prediction bytes, direct36 scores and unchanged F gate. Retain raw returns before validation. No render_di access. |
| render-clean | project .venv | Require both baselines PASS with source/input/HEAD stability. Render only clean12 on one reused host. Retain warmup, first repeat, all12 returns and end-return repeat. |
| score-clean | original V.CPU_PREFIX | Save all12 new predictions before validation/scoring. Coherent flatref from each new wet and fixed average, unchanged original targets/DI, original F gate all12 primary PASS. New/original per-take 1dB compatibility, target regeneration <=1e-8, repeat and stable identity controls all PASS. This INITIAL clean PASS permits panel rendering. |
| render-panel | project .venv | Require durably sealed score-clean PASS before any experimental host. Three isolated new hosts, one per fixed chain, each reused12; full36 render coverage before scoring. Retain identical command/audio/transcript evidence and first/end repeats. |
| score-panel | original V.CPU_PREFIX | Require full36 sealed valid renders. Save ALL36 raw predictions before experiment validity/score gates. Same coherent flatref, target and F metrics. Per-chain F gate and complete-valid-all3 overall gate; INITIAL outcome awaits fresh independent verification. |

Render invalidity due to a scientific repeat control is recorded across all
chains before the render stage is closed INCONCLUSIVE; malformed returns,
exceptions, source/input/identity drift or budget errors close immediately.
No selective scientific panel subset is scored. Scoring catches per-case numeric
errors to retain full score coverage unless a timeout/inference exception prevents
completion. There is no rescue from the paired change diagnostic.
Prediction shape/dtype/finiteness validation occurs inside each case's error
path after the all-returns-saved barrier. Every available case gets an identity
and score/error row; an invalid return makes the whole panel INCONCLUSIVE even
if other valid cases fail their scientific gates.

Original model uses CPU eval, two Torch threads, original float32 conversion and
unchanged `D.rebuild`. Original raw52 input latency is retained. Render input is
unchanged8sec DI, zero-padded52, converted once to float32 at original amplitude1.
Swift full block-padded raw stereo is retained before validation; original
frame truncation follows. Save full float64 mono and trimmed full arrays. Derive
model input `full_mono[96000:384000]` and wet competitor
`full_mono[96052:384052]`. Later load-time proof rederives these exact slices from
retained full arrays. This is a declared52sample coordinate convention, not a
physical latency remeasurement.

Renderer subclass retains complete protocol request JSON BEFORE `_exchange`,
raw reply lines (including invalid JSON/error responses), after-return/error
records and finally-close/quit events, fsynced before subsequent operations.
Keep all WAVs, decoded full raw arrays, warmup/repeat arrays, returned mono,
commands, metadata and host stderr. No silent-output isolation retry/rescue.
Per-call timeout is capped60seconds, including startup replies; nominal render
timeout is30seconds plus twice input duration. Commands are only evidence of
application by protocol acknowledgement, never live parameter readback.
The complete reply line, not just initial pipe readiness, must arrive by a
single monotonic deadline. Read without buffered read-ahead; retain partial raw
bytes on expiry or EOF and stop the host. Logging failure cannot bypass shutdown.

The original1dB active-band/RMS `R.repeat_canary` remains unchanged for first/end
repeats and every clean/original wet comparison. Metadata/plugin identity must
remain stable across warmup, all cases, repeats and all chain hosts. The clean
render metadata must also agree with original saved metadata before panel work.
Before any panel warmup or experimental render, compare each host's full startup
identity against the sealed clean host identity and retain both. Also require
that identity for its warmup, all returned renders and score-stage metadata.

All stages have a cooperative900second budget including guard/loading/saving,
host close, hashing and finalization. Save returned
arrays even if already overbudget; check afterwards and close INCONCLUSIVE.
Saving/hash errors retain attempted NPZ plus per-member `.recovery.npy` files
where the filesystem still permits writes. Nonfinite rejected JSON fields become
null with explicit paths; NPZ preserves raw nonfinite values. Partial/error rows
and closed-attempt record survive failures. Total disk exhaustion or abrupt
process/machine termination cannot guarantee successful evidence writes.
Backend shutdown and partial-row persistence are attempted independently of
transcript/close failures, retaining the original failure and cleanup errors.
Keep protocol events, original read errors and partial raw bytes on the host
before transcript writes. Chain cleanup independently writes a protocol fallback
copy and includes it in partial evidence. A failed error log must not replace
the original timeout. Archive/hash errors retain recovery outcomes and separate
diagnostic/fallback-write errors on the original exception for outer persistence;
the original is re-raised even if both diagnostic paths fail.

Each stage writes provisional and pending reports first, then hashes/seals all
evidence and publishes its final report only within budget. A deadline crossed
during final publication withdraws the final barrier into provisional files.
Earlier stage files and full evidence coverage/hash seals are checked before
later-stage asset access. No final PASS is usable after a closed/error attempt.
On any post-publication failure, withdraw result/seal authority before fallible
diagnostic writes. Attempt invalidation, failure log and closure evidence
independently; prerequisite readers reject failure/invalidation/closure errors.

### Scoring and decision

Use original P numerical helpers: persisted Hann bits, MR-STFT primary,
canonical_waveform_l1 and raw_lowband; unchanged normalization/crop and original
DI target. Each chain's flatref is `P.canonical_target(its_own_new_wet, average)`.
Regenerate unchanged target from original DI, save complete regeneration and
flatref arrays, require target max absolute difference <=1e-8 and oracle<1e-6.

Use unchanged `F.compare` per chain: median improvement against better of wet
and coherent flatref >=10%, >=9 strict wins, positive median improvement for each
six-chord/six-scale group, with all12 identities/QC/oracles valid. Overall PASS
iff all36 are complete valid and all three gates PASS. Any invalidity has
INCONCLUSIVE priority; complete valid failure of any gate is FAIL.

Changes versus new clean and waveform differences are diagnostic only, with no
rescue threshold. Knob names/settings do not establish physical nonlinearity.

### Fresh independent verification after primary completion

Main dispatches a fresh-context verifier AFTER primary completion, as in the
preceding studies. It writes its own code in tmp at that time. There is no inline
verifier executable, subprocess, precommitted verifier asset or primary-score
verification dependency in this runner. Source review/declaration authorize the
primary procedure; the primary clean PASS may permit panel rendering.

The verifier independently implements scorer, preprocessing, architecture,
commands, slicing and canaries. It replays the original108 saved scores and
original12 model output bytes/direct36 scores, then derives all valid new cases,
including coherent flatrefs, target/oracle controls and all per-chain gates. No
rerender/plugin instantiation, imported project numerical helpers, raw/native/
catalog/reserved access or recursive prior-study checks. New render_di overlap
uses the retained authorized render-input copies. Invalid primary prerequisites
remain invalid; verification never computes through a failed prerequisite to
rescue a subset.

The verifier must durably persist its OWN complete numerical derivation, original
replays, new predictions/flatrefs/scores, command/slicing/canary controls and a
blind read-barrier record BEFORE THAT VERIFIER opens any primary numerical
results, predictions or flatrefs. Primary numerical results may already exist.
Only then compare primary returns, every metric, byte/member identity, coverage,
gate, drift/timeout/error record and source/input/runtime evidence. Save independent
NPZs and hashes; no waveform/base64 payloads in JSON. Main controls verifier
dispatch, exact evidence schema, fresh review and archive before any scientific
conclusion. The primary runner never claims independent verification.

### Provenance and verification limits

Explicit dependencies include F/C/V/R/P/T, model architecture/scientific helpers,
renderer interface/AU implementation, Swift compiler helper/server/probe,
pack loader/manifest, source preset, formatter/parser/writer and package initializers.
No recursive inherited hundreds-of-thousands checks/pins; no phase predictions
or actual phase archive are read. Original input metadata carries the needed
identities. Source/test/declaration review must examine this dependency closure.

Record Python/packages, CPU/platform, Torch two-thread/config, loaded shared
library module paths, NumPy configuration and thread environment at finalization.
Independent code still shares installed NumPy/SciPy/Torch and the CPU ecosystem;
agreement is not independent hardware/library validation. Module-path/config
capture cannot reconstruct all dynamically linked libraries, external tools,
server state or historical runtime access. No retrospective runtime audit is
claimed. Cooperative checks cannot forcibly interrupt every native call or
Swift compile; protocol waits have explicit timeouts. The later independently
commissioned verification has its own execution scope and budget.

Synthetic tests cover command exactness/base preservation/manifest kinds, six
environment/stage barriers, all12/36 coverage and invalid priority, group/win
gates, render_di overlap, full-array slicing, partial replays, return preservation
through malformed/nonfinite/schema/save/hash failures, no model before replay,
all predictions before validation/scoring, clean prerequisite before panel,
request-before-call/raw reply/error retention, finally-close, source/input/HEAD
drift, stage seals and final-save timeout. All inputs are generated synthetic
arrays or committed source/parameter metadata. No actual runner/study asset or
plugin execution is part of source verification.
