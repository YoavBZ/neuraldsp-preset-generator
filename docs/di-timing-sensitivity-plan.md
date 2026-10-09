# Fixed Morgan scoring-coordinate sensitivity

**Declared: 2026-10-08, before computation.** Fresh Kant review approves this exact
source, tests, scientific body and 48-file manifest. Independent synthetic module:
87 passed. Main combined suite: 355 passed, two optional Torch checks skipped.
[Review](research/di-timing-sensitivity-review-2026-10-08.md).
Only this administrative frontmatter replaces the approved draft; scientific body
below is unchanged. Commit the full reviewed snapshot before execution. Main owns
actual scoring and fresh independent numerical verification.

<!-- timing-approval
{"status":"DECLARED","fresh_independent_review":true,"scope":"common-post-inference-coordinate-only","review_sha256":"3a704bca2bdc7c17d01ddc5dbdecf00db875de04bd787a0d21e7d1d4b41eee73","source_sha256":"53259e254d262c30c7524ba8e49887c8821455e5b7aaf48c06c39cd2a7458b78","test_sha256":"862cb14b08049c538b62bf699da7ce365f2f5807e0752c811b13a251d9c6f942","design_sha256":"c6e75c3b1d10aef7155a04fd0175fbd12a8dbe01b7f6065aaedd70ad553c0999","inputs_sha256":"1c6cde4a6bdaa5ceb71fd43e56a21049cffb2bbd023a359d8f7b44de4f6dc527"}
timing-approval -->

The block is main's attestation, not automated proof of reviewer independence.
Changes to source, tests, scientific body or inputs require fresh review and a new declaration.

## Frozen design

### Question and limits

Is the already verified fixed clean Morgan network-versus-simple advantage
sensitive to a common post-inference scoring-coordinate error? The verified timing
control motivates fixed offsets: seven accepted tanh cases had errors of two to
three samples across three takes. This is not a new fit to those data. The original
native pilot stays closed; no tolerance changes, gate rescue, tuning or native
inference are permitted.

This shifts saved output waveforms only. It measures neither changing the network
input window nor changing amplifier processing. No inference about input timing,
native validity or native failure causation follows. The twelve same-player
performances are dependent development cases, not independent population evidence
or reserved validation. The gate is not product confirmation.

### Guards and inputs

Importing the runner reads no artifacts. Before coefficient decoding, asset hashes
or arrays, require main's committed declaration and fresh review attestation.
Call unchanged `F.guard()` for the 43 inherited committed source pins and old
successful controls. Pin the new runner/test/plan, new 48-file manifest, fresh
review, archived flatref result/verification/provenance and both prior independent
verifier sources. Every dependency must equal HEAD bytes. Git reads inside the
future guard establish committed identity; implementation does not run Git.

Require a complete passed original flatref result, all twelve valid original raw
QC/oracles (finite, nonnegative primary oracle <1e-6), successful independent
verification with exactly 1,215 passing checks and no failures, matching 43 source
pins/verifier identity, independent original scores/screen and all twelve verified
byte-identical flatref waveforms. Require byte equality of archived original
flatref result/provenance with its original saved reports, matching verification
hashes, and exactly the original 43 provenance pins. Validate ordered original
prepare/independent preparation/prediction coverage and QC/oracle consistency.

Main generated `docs/di-timing-sensitivity-inputs.sha256` after both previous
independent verifications as artifact identity metadata only. Parse exactly 48
unique allowed paths: the original 36 prepare/render/infer NPZs plus the twelve
saved flatref NPZs from `tmp/di-morgan-flatref-20261008`. Require the original36
subset to equal both original result and verification input identities; saved12
hashes must equal the independent verification's saved artifact identities. Reject
missing, extra, duplicate or escaping paths. Hash ALL48 before the first array
load, reject symlinks/aliases, and recheck each immediately before load. Recheck
all files after loading, before shifts and before final result; recheck all source
and metadata pins plus HEAD before loading, before shifts and before final result.

Access only `prepare.di`, `prepare.target`, `render.baseline` (already latency
corrected), `infer.prediction`, and saved `flatref.flatref`. Require finite active
mono six-second waveforms and independently verified target/prediction/flatref
byte identities. Preserve saved dtypes and all samples; do not read render_di or
net_input. No average load/hash, flatref recomputation, checkpoint/model/catalog,
raw audio, native/reserved arrays, rendering, inference or training. Decode exact
archived Torch32 window coefficients through `V.load_windows`; no formula fallback.

### Replay barrier and fixed offsets

First replay all **108** original scalars: twelve takes × three arms × primary,
canonical waveform L1 and raw-DI low-band diagnostic. Use unchanged
`P.score_prediction` and compare against `docs/di-morgan-flatref.json` at absolute
error ≤1e-8. Save a complete `baseline-replay.json` containing every replayed score,
error, the original stronger screen and pass status BEFORE any nonzero shift.
A last-take mismatch blocks every nonzero shift. Zero must reproduce the archived
screen and PASS; use replayed zero values without another scoring call. Invalid
baseline data stop with retained failure evidence; a numerical mismatch saves the
complete failed replay before stopping.

Offsets are EXACTLY **(-128, -52, -16, -8, -3, -2, 0, 2, 3, 8, 16, 52, 128)**
samples at the frozen 48 kHz rate. Shift the whole six-second waveform, without
cyclic wrap, using finite zero padding. Positive means delay:
`y[n] = x[n-offset]` when the source index exists, zero otherwise. Apply the SAME
offset independently to wet, net and flatref for each take. Canonical target and
raw DI remain fixed. The primary and waveform L1 center remains the original
three seconds, samples [72000,216000); even 128 samples of padding are far outside
it. Raw low-band scoring retains its original whole-six-second filtering before
center selection, including finite boundary context. Do not claim that filtering
is mathematically independent of the waveform edges.

No best-lag search, minimum over offsets, selected offset, fitting, optimization,
new crop, polarity correction or per-arm offset is allowed. Score every other
offset on all twelve takes and all three arms, with all three diagnostics.
Retain all 156 take/offset rows and all thirteen screens, including failures.

Report each take's changes from zero at every offset. For each arm save signed
primary absolute delta, relative delta divided by its zero primary (null only if
that primary is zero), and unnormalized changes in waveform L1 and raw low-band.
Also report changes in absolute advantage `simple-net` and relative advantage
`(simple-net)/simple`. Here `simple=min(wet,flatref)` at each SAME fixed offset;
the simple arm may differ from zero. These are paired changes, not fitted gains.

### Gate and disposition

Use unchanged `F.compare` at each fixed offset: better of wet/flatref, median
relative improvement ≥10% with its existing inclusive boundary allowance,
≥9 strict wins, positive group medians for both six-take groups. Require complete
identities/QC/oracles, finite nonnegative scores and positive simple denominators.

After the zero PASS prerequisite, robustness PASS requires EACH of **-3, -2, +2,
+3** to PASS the original stronger gate. A valid failure at any of these four is
robustness FAIL. All other nonzero offsets are DIAGNOSTIC ONLY; their valid FAIL
screens cannot fail robustness. Invalid coverage, scoring errors, nonfinite values,
replay/screen mismatch or source/input drift is INCONCLUSIVE with priority over
scientific failure, including at wide offsets. Never drop invalid cases. Retain
per-case error evidence and continue remaining cases unless the budget expires.

A FAIL does not demonstrate native causation. A PASS does not authorize an
alignment-gate change, native panel rescue, native claim, long training or shipping.
Neither outcome reopens or revises any original study.

### Execution and retained evidence

Only after main's fresh review, committed declaration and exact snapshot:

```sh
/Users/yoavbz/.codex/bin/neuraldsp-safe python-file learn/di_timing_sensitivity.py --out tmp/di-timing-sensitivity-20261008
```

Only `--out` is accepted (no abbreviation) and only that exact directory. Require
actual helper repo `.venv` prefix. Reject symlink aliases and all existing outputs,
including empty directories; create exclusively. All study writes stay inside
that directory. Prefix/guard/directory refusals occur before output creation;
main's harness captures their stdout/stderr. No subprocess computation or workers.

Save provenance (all source/input hashes, revision, versions, prefix, timing,
offsets, budget and attribution), `inputs.json` (file and loaded waveform identity),
complete replay, incremental `progress.jsonl`/stdout and `result.json` with all
rows, paired changes and thirteen screens. Run-level errors save `failure.json`
with INCONCLUSIVE and elapsed time while retaining prior evidence. A cooperative
15-minute budget starts before the guard; check during hashing/loading and
before/after every scoring call/row and before final output. It cannot interrupt a
stuck library call; main monitors execution. No partial PASS result on timeout.

Implementation tests use synthetic arrays/metadata and mocks only. Cover genuine
finite edges/sign/source indexing, fixed center and padding distance, original
scorer center behavior, last-take replay barrier, exact full coverage, gate boundaries
and wide diagnostic-only outcomes, invalid priority, guards and all48 hash ordering,
subset identities/drift, output exclusivity, progress/failure and budget retention.

```sh
/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -q -n0 -p no:cacheprovider tests/test_di_timing_sensitivity.py
```

No actual experiment during implementation. Main owns fresh independent result
verification before interpretation. Pedroza et al., Guitar-TECHS, CC BY 4.0,
https://zenodo.org/records/14963133.
