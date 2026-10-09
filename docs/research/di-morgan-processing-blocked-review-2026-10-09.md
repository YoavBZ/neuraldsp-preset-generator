# Independent source/design review: fixed Morgan processing coverage

Verdict: BLOCK

Fresh review in this task, without inherited agent context. No scientific execution
is authorized by this report. Sources/tests/plan were read only. The reviewer owns
only this report. Findings below require repair and a fresh review of the repaired
snapshot before declaration or actual computation.

## Exact reviewed snapshot

- Branch: `codex/song-model-continuation`.
- HEAD: `40e0ca3b48abfa47772897abfc44df97079cf372`.
- Runner SHA256: `ad3e575897c9d0b439ca030aea8cb74adb6cb5d7501ce8a1c569fa4e5eb68f8a`.
- Tests SHA256: `e73ff5d7f391272c4a9884b1654806c35b340059ec88392bae88cca23bcf1b2a`.
- Scientific body SHA256: `16ec87c46126303fdc8699f336861ec78d7d65c60120ca58bb004e92dd48457e`.
- Original48 input-manifest SHA256: `1c6cde4a6bdaa5ceb71fd43e56a21049cffb2bbd023a359d8f7b44de4f6dc527`.
- Full DRAFT plan SHA256: `54790725f2c7c18f4ad79c5aa6af2a3af49c691f6bb2b86ad7baf67f52720b52`.

All 40 explicit source/committed-metadata pins in
`tmp/di-morgan-processing-review-snapshot.json` matched their declared SHA256s.
The scientific body was independently hashed as the UTF8 bytes following
`## Frozen design\n`. The input-manifest digest is of the committed text manifest;
this reviewer did **not** hash or open its 48 actual assets.

## Required repairs

### 1. Panel hosts can silently use a different identity from the clean control

**High priority.** `learn/di_morgan_processing_control.py:663`–`:668` compares
identities only among the three hosts returned by the current render stage.
`score_stage` obtains the sealed clean identity at `:734`, but compares metadata
only in the `chain == "clean"` branch at `:746`–`:753`. `barriers` at `:247`–`:259`
checks files, pins, inputs and HEAD, without comparing renderer identities.

An external plugin update after clean scoring can therefore give every panel host
the same new version, pass all current panel identity checks, and produce a panel
PASS against a clean control rendered by the old version. This violates the
all-host identity stability requirement at plan `:142`–`:145`. The production
render and score functions both accept this synthetic scenario (probe A below).
This was independently identified before main's subsequent integration note.

Require every panel host's complete renderer identity to equal the sealed clean
identity. Establish that comparison at startup/before its experimental renders,
retain the observed mismatch, and close INCONCLUSIVE on drift. Add a regression
where all panel hosts agree with each other but differ from clean; retain the
existing within-host and within-panel checks.

### 2. A transcript write failure can skip host shutdown and partial evidence

**High priority.** `ProtocolEvidence.close` writes its quit-request event at
`:551`–`:553` **before** entering the `try/finally` that calls backend close at
`:554`–`:561`. If this event write/fsync raises, backend close is never invoked.
The inherited destructor calls the same failing override, so it is not a reliable
backstop. `render_chain` also writes `partial.json` only after successful
`host.close()` at `:646`–`:648`.

Probe B injects a transcript-only I/O error while other paths remain writable;
the synthetic backend's close is never called. This is not the plan's excluded
case of total disk exhaustion. A logging failure must not leave a live AU host,
and a close failure must not prevent independent attempts to save partial rows.
Use nested cleanup/failure-preservation paths so backend shutdown and partial
evidence are attempted regardless of transcript or close errors. The attempt
must still close INCONCLUSIVE and preserve the original errors.

### 3. Failure logging can prevent withdrawal of an already published PASS

**High priority.** After `finish` publishes the final result/seal, closure saving
at `:849`–`:850` or the last deadline check at `:851` can fail. In the exception
handler, `event(out / "failures.jsonl", ...)` at `:857` runs **before** the PASS
withdrawal at `:859`–`:861` and before attempted closed-attempt persistence.
If the failure-log write also raises, those safeguards are skipped.

Probe C runs only a fully mocked synthetic dispatch with real temporary JSON/seal
writes. Injecting errors on `closed.json` and `failures.jsonl` leaves a sealed,
consumable `result.json` saying PASS, no `closed.json`, and no failure record.
`stage_report` accepts it. Other filesystem paths remain writable. This violates
the plan's final-save/error requirements at `:147`–`:160`.

Invalidate the published authority before fallible diagnostic writes; attempt
withdrawal, failure evidence and closure independently even when another cleanup
operation fails. Test this through main's exception path, including a final
deadline failure plus a failure-log error. Do not treat a lingering INITIAL PASS
as authoritative after failed finalization.

### 4. One nonfinite prediction prevents all per-case scoring/error coverage

**Medium priority.** `score_stage` saves all 12/36 predictions correctly, but the
global validation loop at `:724`–`:725` raises before the per-case exception
handling at `:736`–`:774`. A nonfinite prediction in the first case leaves zero
score/error rows for all 36 cases, despite all inference returns being available.
Probe D reproduces exactly that state. The frozen test at
`tests/test_di_morgan_processing_control.py:287`–`:303` intentionally stops at
this first validation boundary and therefore does not verify the declared
continued coverage requirement.

Plan `:119`–`:121` requires per-case numeric errors to retain full score coverage,
with timeout/inference exceptions as the stated reasons completion can fail.
After the all-predictions-saved barrier, validate inside each case's error path,
retain an explicit invalid identity/error row for each rejected return, process
the other available cases, and retain INCONCLUSIVE priority. Do not score invalid
values or rescue a scientific subset. Add first/last-case nonfinite/schema cases
with complete 12/36 row accounting and invalid-over-FAIL priority.

### 5. The reply timeout bounds readiness, not receipt of a complete reply line

**Medium priority.** The override at `:492`–`:517` delegates to
`match/renderer_au.py:556`–`:597`. That implementation waits for the descriptor
to become readable, then calls blocking `readline()` without a remaining deadline.
The wrapper logs that line only after `readline()` completes. A partial reply
followed by a stalled host bypasses both the effective 60-second cap and the
cooperative budget, since neither can run while that read blocks.

Probe E uses an ordinary synthetic OS pipe, no process or plugin: a 0.01-second
timeout successfully returns only after a delayed newline more than 0.1 seconds
later. Existing protocol tests use complete `StringIO` lines and do not exercise
this path. Plan `:138`–`:139` explicitly promises bounded protocol replies, unlike
its acknowledged inability to interrupt arbitrary native computation/compilation.

Read a complete line under a single monotonic deadline; preserve partial raw
bytes/text on expiry, stop/close the host, and close the attempt INCONCLUSIVE.
Add partial-line and startup-line timeout regressions with synthetic pipes.

## Design and source assessment

The scientific comparison itself is appropriately fixed: all twelve dependent
development performances, three specified PR12 changes, unchanged fold2 model,
original targets/windows/scorer, a coherent flatref constructed from each arm's
own wet signal and the frozen average, and the unchanged stronger F gate per
chain. `compare` checks complete unique identities, positive denominators,
finite metrics/oracles, nine strict wins and both groups, with invalidity taking
priority over valid FAIL. There is no lag/gain fit, learned rescue, subset gate,
or native/song/product/training conclusion in this runner.

The reviewed guard rejects DRAFT before actual assets, requires committed exact
runner/test/body/review/input and dependency pins, pins HEAD between stages, and
requires original48 identities. Imports and the executed numerical/rendering/
formatting/build call graph were inspected; the explicit 40-file closure covers
the relevant local dependencies without recursive historical pin growth.
Committed earlier report metadata records 1215 and 767 verification checks with
empty failure lists and complete twelve-case original reports; those are context,
not a fresh replay of their actual data.

Original108 replay precedes model loading; baseline checks original prediction
bytes and direct36 metrics. Interpreter selection is explicit. The render-only
loader restricts new member access to `render_di`, validates float64 length,
finite values and exact suffix/sample bytes. Whole ordered template+R commands
retain FX/compressor/base values and only specified overrides. Full WAVs,
block-padded decoded raw stereo/mono, truncated full returns, warmups, first/end
repeats and fixed52 slicing evidence are retained. Protocol request/reply/error
logging, recovery arrays, per-file seals and final-save deadline checks are
substantive safeguards, subject to the failure-path defects above.

The corrected verifier workflow is appropriate: fresh separate task after
primary completion; its own complete durable derivation before that verifier
reads primary numerical results/predictions/flatrefs. No inline executable or
precommitted verifier is required. Primary reports remain INITIAL; sealed clean
PASS is only an operational panel prerequisite. Final scientific conclusions
still require independent recomputation, with disagreement INCONCLUSIVE.

## Commands, results and evidence limits

The exact command for frozen tests was:

`/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -q tests/test_di_morgan_processing_control.py`

Result: **53 passed in 0.81s**, exit 0. These include meaningful malformed-return,
save/hash failure, partial replay, exact overlap/slicing, all-return-before-score,
invalid priority, gate boundary, host-close-on-render-error, drift, seal and
final-save-budget tests. Their backend/numerical stage paths are heavily mocked;
they do not establish cross-stage plugin identity, cleanup under logging errors,
main finalization under multiple errors, complete invalid-prediction row coverage,
or partial protocol-line deadlines. The independent probes below target those
specific gaps rather than expanding to an unchanged repository-wide test suite.

Read-only commands included `pwd`, `git status --short`,
`git branch --show-current`, `git rev-parse HEAD`, `rg` import/function/test
searches, `cat`/`sed`/`nl`/`tail` source/task/plan/monitor reads, `shasum -a 256`
of the runner/tests/plan/input-manifest text, and Ruby JSON/Digest verification of
the exact snapshot's 40 source pins/body and selected committed report metadata.
An initial Ruby check used unsupported `filter_map` and exited 1; the corrected
`map ... compact` check exited 0 with 40 checked, zero mismatches and the body
digest above. Initial discovery also reported absent `.agents`, `.codex` and
physical `AGENTS.md`; the user-supplied AGENTS instructions were followed.

No actual NPZ/model/average/raw recording/catalog/native/reserved/audio was
hashed or loaded. No plugin was instantiated, Swift helper compiled, actual stage
run, asset downloaded, source edited, commit made or agent spawned. The probes
use generated arrays, temporary synthetic files and mocked external boundaries;
the pipe probe uses only two OS pipe descriptors and a short-lived thread.
No actual numerical result, CPU inference reproducibility, AU behavior, physical
latency, dynamic library independence or historical runtime access is verified.

## Reproducible independent synthetic probes

These doctests are embedded in the sole reviewer-owned file. Execute through the
approved helper, without creating or changing a source/test/plan file:

`/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -n0 -q --doctest-glob=di-morgan-processing-review.md tmp/di-morgan-processing-review.md`

The expected outputs describe the **current defects**, not acceptance criteria
for a repaired runner. Any fixture that touches a production external boundary
has that boundary replaced before invocation.

```python
>>> import json, os, threading, time
>>> from pathlib import Path
>>> from tempfile import TemporaryDirectory
>>> from types import SimpleNamespace
>>> from unittest.mock import patch
>>> from contextlib import ExitStack
>>> import numpy as np
>>> from learn import di_morgan_processing_control as M
>>> def review_panel():
...     return [{"slug": f"review-{i}", "take": f"take-{i}", "content": "chords" if i < 6 else "scales"} for i in range(12)]
>>> def review_row(take):
...     row = {**take, "valid": True, "qc_valid": True, "oracle": 0., "wet": 1., "flatref": .9, "net": .7}
...     for arm, key in M.T.ARMS.items():
...         row[key] = {metric: row[arm] for metric in M.T.METRICS}
...     return row
>>> def review_context():
...     takes = review_panel()
...     return {"manifest": {"takes": takes}, "original": {"rows": [review_row(t) for t in takes]}, "pins": {}, "hashes": {}, "revision": "synthetic"}

```

Probe A: production render and score stages accept uniformly changed panel
identity relative to clean. Numerical calls here are deliberate mocks: the
finding is missing identity enforcement, not a numerical/model claim.

```python
>>> def probe_identity(directory):
...     ctx = review_context()
...     clean = {"plugin_version": "old-clean"}
...     changed = {"plugin_version": "new-panel"}
...     loaded = {t["slug"]: {"di": np.arange(5, dtype=np.float64), "target": np.arange(5, dtype=np.float64), "wet": np.ones(5)} for t in review_panel()}
...     def score(wave, target, *args, **kwargs):
...         value = 0. if np.array_equal(wave, target) else .7 if wave.dtype == np.float32 else .9
...         return {metric: value for metric in M.T.METRICS}
...     with ExitStack() as stack:
...         replacements = {"N": 5, "check_time": lambda *a: None, "recheck": lambda *a: None, "check_inputs": lambda *a: None,
...             "load_render_di": lambda *a: {}, "render_chain": lambda out, chain, *a: {"identity": changed, "valid": True, "chain": chain, "rows": review_panel()},
...             "load_model": lambda *a: object(), "load_slices": lambda *a: (np.ones(5), np.ones(5)),
...             "infer": lambda *a: np.full(5, .7, dtype=np.float32), "pinned_asset": lambda *a: None,
...             "read_json": lambda *a: {"rows": [{**t, "renderer_metadata": clean} for t in review_panel()]},
...             "stage_report": lambda *a: {"chains": [{"identity": clean}], "rows": [review_row(t) for t in review_panel()]}}
...         for name, value in replacements.items():
...             _ = stack.enter_context(patch.object(M, name, value))
...         _ = stack.enter_context(patch.object(M.P, "canonical_target", lambda wave, avg: wave.copy()))
...         _ = stack.enter_context(patch.object(M.P, "score_prediction", score))
...         def synthetic_average(path, **kwargs):
...             assert str(path) == M.AVERAGE["path"]
...             return np.zeros(2049)
...         _ = stack.enter_context(patch.object(np, "load", synthetic_average))
...         rendered = M.render_stage(directory, ctx, {}, 0, M.EXPERIMENTS)
...         scored = M.score_stage(directory, directory, "score-panel", ctx, loaded, {}, 0, M.EXPERIMENTS)
...     return rendered["passed"], scored["passed"], changed == clean
>>> with TemporaryDirectory(prefix="morgan-review-a-") as temporary:
...     print(probe_identity(Path(temporary)))
(True, True, False)

```

Probe B: a quit-event write error bypasses backend shutdown.

```python
>>> class ReviewBackend:
...     def close(self):
...         self.backend_closed = True
>>> class ReviewCloseHost(M.ProtocolEvidence, ReviewBackend):
...     pass
>>> host = ReviewCloseHost()
>>> host.backend_closed, host._process, host.transcript = False, SimpleNamespace(poll=lambda: None), Path("unused-synthetic-transcript")
>>> with patch.object(M, "event", side_effect=OSError("transcript-only failure")):
...     try:
...         host.close()
...     except OSError as error:
...         print(str(error), host.backend_closed)
transcript-only failure False

```

Probe C: synthetic main dispatch leaves a consumable PASS after closure and
failure-log writes fail. No real stage computation or prerequisite asset access.

```python
>>> def probe_finalization(root):
...     run = root / "attempt"
...     run.mkdir()
...     actual_write = M.write_json
...     def injected_write(path, value):
...         if Path(path).name == "closed.json":
...             raise OSError("closure-only failure")
...         return actual_write(path, value)
...     with ExitStack() as stack:
...         replacements = {"ROOT": root, "OUTPUT": "attempt", "require_environment": lambda *a: None,
...             "guard": lambda *a: {**review_context(), "correction": {}}, "barriers": lambda *a: None,
...             "recheck": lambda *a: None, "check_inputs": lambda *a: None, "load_original": lambda *a, **k: {},
...             "score_stage": lambda *a: {"complete": True, "passed": True, "disposition": "PASS"},
...             "runtime": lambda: {}, "write_json": injected_write,
...             "event": lambda *a: (_ for _ in ()).throw(OSError("failure-log-only failure"))}
...         for name, value in replacements.items():
...             _ = stack.enter_context(patch.object(M, name, value))
...         _ = stack.enter_context(patch.object(M.V, "load_windows", lambda *a: {}))
...         try:
...             M.main(["score-panel", "--run", str(run)])
...         except OSError as error:
...             assert str(error) == "failure-log-only failure"
...         accepted = M.stage_report(run, "score-panel")["disposition"]
...     (root / "still-writable.txt").write_text("other paths remain writable")
...     return accepted, (run / "closed.json").exists(), (run / "score-panel" / "seal.json").exists()
>>> with TemporaryDirectory(prefix="morgan-review-c-") as temporary:
...     print(probe_finalization(Path(temporary).resolve()))
('PASS', False, True)

```

Probe D: all36 predictions saved, one nonfinite return among 35 finite returns,
zero score/error rows. Both the first-case and last-case variants reproduce it.

```python
>>> def probe_invalid_coverage(directory, bad_index):
...     returns = iter([np.full(5, np.nan if i == bad_index else .7, dtype=np.float32) for i in range(36)])
...     with ExitStack() as stack:
...         replacements = {"N": 5, "check_time": lambda *a: None, "load_model": lambda *a: object(),
...             "load_slices": lambda *a: (np.ones(5), np.ones(5)),
...             "infer": lambda *a: next(returns)}
...         for name, value in replacements.items():
...             _ = stack.enter_context(patch.object(M, name, value))
...         _ = stack.enter_context(patch.object(M, "pinned_asset", side_effect=AssertionError("unexpected external asset boundary")))
...         try:
...             M.score_stage(directory, directory, "score-panel", review_context(), {}, {}, 0, M.EXPERIMENTS)
...         except ValueError as error:
...             assert str(error) == "nonfinite waveform"
...     return len(list(directory.glob("*.prediction.npz"))), len(list(directory.glob("score-*.json")))
>>> for bad_index in (0, 35):
...     with TemporaryDirectory(prefix="morgan-review-d-") as temporary:
...         print(probe_invalid_coverage(Path(temporary), bad_index))
(36, 0)
(36, 0)

```

Probe E: real inherited pipe-reading methods exceed the effective timeout after
initial readiness. No renderer object, child process, plugin or actual audio.

```python
>>> from match.renderer_au import AudioUnitRenderer
>>> def probe_partial_reply(directory):
...     permit_finish = threading.Event()
...     class PipeBackend:
...         _readline = AudioUnitRenderer._readline
...         def _reply_arrives(self, stream, timeout):
...             ready = AudioUnitRenderer._reply_arrives(self, stream, timeout)
...             permit_finish.set()
...             return ready
...     class PipeHost(M.ProtocolEvidence, PipeBackend):
...         pass
...     read_fd, write_fd = os.pipe()
...     stream = os.fdopen(read_fd, "r")
...     _ = os.write(write_fd, b'{"ok":')
...     def finish_line():
...         permit_finish.wait()
...         time.sleep(.15)
...         _ = os.write(write_fd, b'true}\n')
...         os.close(write_fd)
...     writer = threading.Thread(target=finish_line)
...     writer.start()
...     reader = PipeHost()
...     reader._process = SimpleNamespace(stdout=stream, poll=lambda: None)
...     reader.started, reader.reply_timeout_s, reader.transcript = time.monotonic(), .01, directory / "pipe.jsonl"
...     before = time.monotonic()
...     try:
...         reply = reader._readline(timeout=.01)
...         elapsed = time.monotonic() - before
...     finally:
...         writer.join(timeout=1)
...         stream.close()
...     return reply["ok"], elapsed > .1
>>> with TemporaryDirectory(prefix="morgan-review-e-") as temporary:
...     print(probe_partial_reply(Path(temporary)))
(True, True)

```

Independent probe execution results: initial **1 doctest item passed in 0.30s**;
after strengthening probe D to one invalid return among 35 valid returns at both
the first and last positions, **1 doctest item passed in 0.31s**. Both runs exited
0, covering all five probes and their setup. Observed outputs were respectively
`(True, True, False)`, `transcript-only failure False`, `('PASS', False, True)`,
`(36, 0)` for first/last invalid returns and `(True, True)`. This confirms the five
failure scenarios; it does not approve the current implementation.

Final read-only snapshot check: all 40 source/metadata pins still matched, both
full-plan and body hashes matched the supplied snapshot, and HEAD remained
`40e0ca3b48abfa47772897abfc44df97079cf372`. Source/test/plan files were not edited.
