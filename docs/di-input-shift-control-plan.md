# Known input timing shifts in the frozen clean Morgan control

**Declared: 2026-10-08, before computation.** Fresh Hilbert review approves this
exact source, tests, scientific body and unchanged 48-file identity manifest.
Independent synthetic suite: 93 passed, one expected optional Torch skip.
[Review](research/di-input-shift-control-review-2026-10-08.md).
Only this administrative frontmatter replaces the approved draft. The scientific
body remains byte identical. Commit the reviewed snapshot before execution.
Main owns actual execution and fresh independent numerical verification.

<!-- input-shift-approval
{"status":"DECLARED","fresh_independent_review":true,"scope":"known-input-shift-and-truth-inverse-only","review_sha256":"5cf47462f87e909aad0b016fbb672ad8dd479b99897b34aa8d4203f678a6e428","source_sha256":"6ecc61a9e6d3a2327f01709a43139ab48ce807d56debcd477f05a7fd20762219","test_sha256":"7486ea56aeb2e1349a6ab3ea4a61d999d2657d4f19d4c68170adc324f8a811fb","design_sha256":"7736e42b6f88e65bc82b780c0462913011af27db074dc5d9ef92075f5a595589","inputs_sha256":"1c6cde4a6bdaa5ceb71fd43e56a21049cffb2bbd023a359d8f7b44de4f6dc527"}
input-shift-approval -->

The design hash covers bytes after `## Frozen design\n`; the inputs hash identifies
the existing unchanged manifest. Main's attestation is not automated proof of
reviewer independence. The archived review and execution dependencies must be committed.
Changing source, tests, design or prerequisites requires fresh review/declaration.

## Frozen design

### Question and interpretation

Does the original frozen clean Morgan learned-versus-strong-simple advantage
survive known small shifts at model INPUT, after reversing the imposed truth shift
on the prediction? The preceding common OUTPUT-coordinate diagnostic did not test
this question. The qualitative rationale is in `tmp/di-input-shift-scope.md`.

Use the original twelve fixed dependent development takes, six chords and six
scales. Offsets are EXACTLY **(-3, -2, 0, 2, 3)** samples at the original 48 kHz.
Positive means delay, `shift(x,k)[n]=x[n-k]`, with finite zero padding over the
complete six seconds. Shift each original `render.net_input` before unchanged
`D.rebuild`. Preserve the original raw level, dtype and 52-sample render latency.
Convert the full shifted input to little-endian float32 exactly as original
`C.infer` on the original little-endian CPU host. Rebuild uses its original
whole-window standard deviation, six-second window and overlap behavior.

Correct each returned prediction using `finite_shift(raw_prediction, -offset)`
and explicitly convert that inverse to `<f4`, because the unchanged finite-shift
helper promotes through `P._mono`. The conversion preserves every retained
float32 sample exactly, including signed zeros; padding is float32 zero.
This is the known imposed inverse, never a lag fit or selected offset. Target and
raw DI stay original. Wet and saved flatref competitors stay fixed at every
offset. All original center scoring windows and whole-waveform low-band filtering
remain unchanged. Finite padding and normalization/context effects are included.
The check cannot isolate an encoder-stride cause, establish native causation or
validate song/product transfer. No average access, new flatref, render, training,
native gate change, 52-sample latency change, lag search or minimum across offsets.

### Committed guards and inherited evidence

Importing the runner must not access Torch, coefficients, study arrays or models.
Main requires the exact explicit CPU prefix
`/Users/yoavbz/ndsp-presets/tools/learn-venv` before the guard. Start the cooperative
900-second budget before the guard, including metadata, hashes, load and scoring.
Check it throughout new guard loops, around inherited guards and coefficients,
through hashing/loading, before and after model calls and every score/case.
A stuck library call cannot be interrupted cooperatively; main monitors the job.

Use unchanged `T.guard()` for all 53 inherited committed pins, old T/F sources,
prerequisites and the exact original 48-file manifest. Own pins must be disjoint:
new runner, test, plan and fresh review; archived T result, verification,
provenance, inputs and baseline replay; archived T independent verifier source.
All these bytes must equal HEAD, and all dependency paths must be regular,
unaliased files. The guard uses read-only Git operations during future execution.

Require T verification status VERIFIED, scientific disposition PASS, empty
failures, exactly 23,734 passing checks, exact matching 53 source pins and archived
verifier SHA256. Require complete T156 rows, every paired change and all thirteen
screens to match the independently derived rows/screen and derivation payload at
the unchanged absolute tolerance 1e-8. Revalidate T coverage and gates. Require
complete passed T108 replay matching the independent replay/payload, all errors
finite nonnegative within tolerance, all twelve identities, and unchanged source,
artifact and input identity dictionaries. Compare original T reports with their
committed archives byte for byte. Hash all six original report/progress/log paths
against the exact `primary_artifact_snapshots` keys, hashes and byte sizes; verify
progress and stdout contain exactly the retained156 rows. No new guitar scoring
is part of this metadata prerequisite check.

### Input and model access

Reuse unchanged `T.load_inputs` for its five existing members and independent
identities: `prepare.di`, `prepare.target`, `render.baseline`, `infer.prediction`,
`flatref.flatref`. Require those loaded dtype/length/byte identities to equal the
archived T inputs exactly. Sole additional access is `render.net_input` in each
of the same twelve render archives. Exactly six allowed member names across the
same48 files; do not access `render_di` or discover other archives.

Hash ALL48 before the first array load. Recheck each immediately before load,
all after inherited loading, each new render access before and after load, all
after new loading, again after108 replay before any new inference, before the first
shifted inference and finally. Reject symlinks, lexical aliases, hardlinks and
duplicate inode identities. New input must be finite active floating mono six
seconds. Preserve its raw samples/dtype, record bytes/dtype/length and float32
conversion hashes. Require dtype equality and exact original overlap bytes
`net_input[52:] == baseline[:-52]`. Renderer source defines
`net_input=y[start:start+SCORE]` and `baseline=y[start+52:start+52+SCORE]`;
the overlap checks this original convention without fitting or full renders.

Model access is ONLY the original manifest identity:
`/Users/yoavbz/ndsp-presets/learn/direc/models-set3/fold2.pt`, SHA256
`16b2b734b49cc1cc2d7e547d96d3bb56208007c9cae0d0e33acb1c2a1cdd042b`.
Require a regular unaliased nonlink file and observed hash after declaration,
before Torch load, before the first shifted inference and finally. No average,
catalog, raw/native/reserved audio, alternate checkpoint or model discovery.
Use original `D.build_model().cpu()`, `torch.load(weights_only=True,
map_location="cpu")`, `eval()`, and two Torch threads. Check actual thread count,
eval state and CPU parameters. No embedded interpreter switching or workers.

### Two positive-control barriers

First run unchanged `T.replay` using the unchanged `P.score_prediction` and exact
archived Torch32 windows through `V.load_windows`. Recompute all108 prior scalars
on all12 takes and three arms. Save complete PASS `baseline-replay.json` before
model loading/inference. Original stronger screen must reproduce and PASS at
absolute 1e-8. A last-take mismatch blocks every model call.

Then recompute ALL12 unshifted predictions before any nonzero input inference.
Save each returned raw and zero-corrected prediction before checking validity,
exact original float32 bytes or score parity. Require all12 original prediction
bytes exactly, all36 network scalar scores within absolute 1e-8, original valid
QC/oracles and the unchanged stronger zero screen PASS. Persist complete
`baseline-inference-replay.json` with every identity, saved prediction identity,
byte comparison, three scores/errors, complete/scalar count/pass status and gate.
Continue through all12 after ordinary failures; retain complete failed evidence
whenever possible. Timeout preserves partial replay and returned predictions.
A last-take error or mismatch blocks ALL48 nonzero inferences. Neither byte
equality nor tolerance may be relaxed. Both positive controls are mandatory.
The36 score errors compare directly with the original archived scalars, rather
than allowing the108 replay tolerance to accumulate with inference tolerance.

Reuse the recomputed unshifted predictions and scores for offset0 with no rescore.
After both barriers, recheck model, all48 artifacts, source pins and HEAD before
the first shift. Run every take at all four nonzero offsets. Save every returned
raw/corrected float32 prediction in an exclusive per-case NPZ, plus imposed offset;
if a malformed/nonfinite raw prediction prevents correction, retain raw evidence
and the error. Network exceptions retain the case error. Report raw and corrected
byte hashes, saved NPZ hash, original saved prediction hash, raw-level shifted
input identity and exact float32 conversion hash. Retain every case's three
network metrics, fixed wet/flatref metrics, inherited QC/oracle and per-take
changes from zero using unchanged `T.paired_changes`. Never discard a saved
prediction merely because its bytes or scores disagree with the archive.

### Gates and evidence

Exactly60 take/offset cases and five screens are required. Apply unchanged
`F.compare` separately at each offset with original fixed wet/flatref competitors,
QC and oracle: better simple competitor, median relative advantage >=10% with its
original inclusive allowance, >=9 strict wins and positive medians in both groups.
Zero PASS is a prerequisite. Robustness PASS requires EACH of the four nonzero
screens PASS. Any valid nonzero failure is FAIL. Invalid/nonfinite score,
coverage/error, model/source/input/HEAD drift or failed positive control makes the
diagnostic INCONCLUSIVE with priority. Continue other cases after case errors
unless the budget expires. A final stability failure retains all60 cases and five
screens in an INCONCLUSIVE result plus failure evidence. Timeout never yields PASS.

The sole CLI argument is `--out tmp/di-input-shift-control-20261008`, with no
abbreviation or other option. Reject existing output (even empty), other paths
and aliases; create exclusively. Prefix/declaration/output refusals occur before
study writes and main captures stdout/stderr externally. All study writes stay
inside the fixed output. No external communications or network calls.

Save provenance with source pins, HEAD, versions, prefix, original model identity,
two threads, offsets, budget/timing and attribution; inputs; both replay barriers;
60 prediction NPZs when calls return; incremental `progress.jsonl` and stdout
(stage-tagged12 baseline entries plus60 case entries on success); complete result
with all60 cases/five screens. Run exceptions retain `failure.json` with
INCONCLUSIVE, error type/message and elapsed time along with previous evidence.

Main must use the explicit CPU interpreter for a future run with narrowly scoped
escalation, after fresh review/declaration/commit. This draft supplies no execution
authorization and does not switch environments internally.

Synthetic verification during implementation uses only:

```sh
/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -q -n0 -p no:cacheprovider tests/test_di_input_shift_control.py
```

Tests cover genuine finite shift sign/inverse/edges, full input before unchanged
rebuild normalization (synthetic Torch module optionally when available), exact
member/48-hash barriers, original52 overlap and identities, both last-take barriers,
fixed target/competitors and known inverse,60 coverage/five unchanged gates,
invalid priority, committed guard/review/prior T metadata, drift, prefix/output,
progress and budget/failure retention. Unavailable Torch means an expected optional
helper skip; it does not authorize an interpreter workaround or an actual run.

Neither outcome authorizes native-gate changes, reopening the stopped panel,
training or product claims. Main owns fresh independent numerical verification
before interpretation. Pedroza et al., Guitar-TECHS, CC BY 4.0,
https://zenodo.org/records/14963133.
