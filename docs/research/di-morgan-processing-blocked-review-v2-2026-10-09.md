# Fresh independent Morgan processing source/design review v2

Verdict: BLOCK

This is a fresh independent source/design review of the corrected snapshot. I
read the complete runner, tests and scientific body, the prior five findings,
the review brief/repair notes/live monitor and the relevant immutable helper
call paths. I did not inherit another reviewer's reasoning or accept the repair
summary as evidence. The supplied monitor contains older hashes; the latest
snapshot and independently computed current bytes identify this review.

No actual data or study computation was begun by this reviewer. This report
authorizes no stage execution. Only this report was edited.

## Exact reviewed snapshot

- Branch: `codex/song-model-continuation`.
- HEAD: `40e0ca3b48abfa47772897abfc44df97079cf372`.
- Source SHA256: `babb9cab20e995ee4bb02abfcc3df82d831f7f06df376925596604b2527203df`.
- Test SHA256: `8da80d2d7286cbb654291ca9242ab839f7f10b72eb9aab8bb77156952780c49d`.
- Scientific body SHA256: `fc58df53f1178cde2d353a1e3125a78fc97be2e0465524a5b4541fa24f077fdd`.
- Original48 input-manifest SHA256: `1c6cde4a6bdaa5ceb71fd43e56a21049cffb2bbd023a359d8f7b44de4f6dc527`.
- Full draft plan SHA256: `e82f0f3da1d65d969563789bfe671896d78943d4d232e02d7eb3449e0bb28c38`.
- Supplied snapshot SHA256: `6c9bbc12f4df15861ee9d833fb656982dc29828e81c311aa1ed5162cc677e896`.

The body digest is of the UTF8 bytes AFTER `## Frozen design\n`, consistent with
`T.design_bytes`. The input digest identifies the text manifest; I did not open
or hash its 48 NPZ assets. All40 explicit file pins match the supplied map.
The runner/test/plan remain uncommitted draft additions, as expected at source
review. Declaration and commitment are still mandatory before any real access.

## Remaining blockers

### 1. Protocol diagnostic failure loses partial replies and replaces the recorded original error

**Medium priority.** In `learn/di_morgan_processing_control.py:532`, the reader
has the original protocol exception and partial raw bytes. If its transcript
write fails at `:536`, only the logging exception is retained on the host at
`:540`; the original protocol failure and partial bytes remain local. Then the
normal exchange handler's unprotected `event(...)` at `:494` can raise the same
logging error in place of the original timeout. `failure` at `:106` serializes
only the outer type/message, and `render_chain`'s partial record at `:698` stores
neither partial bytes nor the original protocol failure. Even
`protocol_logging_error` is omitted there.

Independent probe3 records the request successfully, then makes ONLY transcript
writes fail, while other paths remain writable. An ordinary real pipe stalls
after `b'{"ok":'`. Shutdown is attempted successfully. The caller receives
`OSError` rather than the original `TimeoutError`; the original is available
only in Python's exception context, not the durable error record. Neither the
original timeout nor the partial raw bytes appears in the available fallback
record, even when the host's logging-error attribute is included in that record.
A complete process traceback may retain the exception chain; it cannot recover
the partial raw bytes and does not satisfy the runner's retained protocol
evidence promise. The startup path shares the partial-byte-loss problem, though
its timeout does not pass through `_exchange`'s replacement handler.

This is a remaining gap in prior finding2's multiple-failure evidence handling,
not a recurrence of its backend-close bypass. It violates plan `:137`–`:147`
and `:163`–`:166` outside the stated total-write-failure limit. The attempt is
still invalid; this finding does not claim a false PASS or an unbounded read.

Retain the original protocol exception plus partial raw bytes on the host before
attempting transcript writes. Preserve/re-raise the original across exchange
diagnostic failure, and include both original and logging/close errors and raw
partial evidence in independently attempted chain/main fallback persistence.
Add a combined real-pipe timeout plus transcript-write-failure regression for
both startup and normal exchange, verifying saved evidence as well as shutdown.

### 2. Save-failure diagnostic errors replace the original archive/hash failure

**Medium priority.** `save_arrays` catches the original failure at runner `:134`
and independently attempts member recovery. However, its diagnostic write at
`:145` is unprotected. If that write fails, the bare re-raise at `:146` is never
reached. The caller and later `failure(...)` records identify the diagnostic
write error, without the original error or recovery outcomes.

Independent probe4 injects `OSError("original archive hash failure")`, allows
both the attempted NPZ and member recovery NPY to persist, then rejects only
the `.save-failure.json` write. The returned exception and outer saved record
say `PermissionError("save diagnostic rejected")`; the original hash failure
exists only in transient exception context. Other JSON paths remain writable.
The committed tests at `tests/test_di_morgan_processing_control.py:173` and
`:184` cover each first failure with successful diagnostic persistence, not
this combination.

This violates plan `:160`–`:166`'s original-error and cleanup-evidence contract.
Preserve/re-raise the original save/hash error, record diagnostic-write errors
separately, and expose original/recovery/cleanup information to an independent
fallback evidence path. Add a combined failure regression; retaining the raw
arrays alone is not evidence of which operation failed.

Both repairs are source-only. Do not run the study or tune any scientific rule
to resolve them. Archive this BLOCK and commission a fresh review of corrected
source/test/body hashes before declaration.

## Independent assessment of all five prior findings

| Prior finding | Corrected implementation and evidence | Assessment |
| --- | --- | --- |
| Clean-to-panel identity drift | Runner `:718`, `:729`, `:657`–`:661` passes sealed clean identity into every chain and compares full startup identity before commands/warmup. Warmup/cases/repeats remain checked at `:670`, `:675`, `:684`, `:688`; scoring checks all chain identities at `:797`–`:799`. Tests `:575`, `:587`, `:600`; independent probe2 traverses production render_stage and render_chain for each of three changed-host positions, changing renderer_build while plugin_version stays equal. | Repaired. Each changed host closes before its first render; expected/observed identity is saved. |
| Transcript failure skips close/partial evidence | Runner `:581`–`:599` independently attempts backend close despite quit/closed transcript failures. Chain `:690`–`:710` saves partial rows even if close fails and retains an existing body exception. Tests `:611`, `:623` check log-only failure and body/close combinations. | Original shutdown/partial bypass repaired. Remaining protocol/save error-preservation gaps are blockers1/2 above. |
| Post-publication errors leave usable PASS | Main `:925`–`:951` withdraws result and seal before diagnostic writes, attempts invalidation/failure/closure paths independently, and re-raises the original main error. Reader `:241`–`:246` rejects invalidation/failure/closure markers. Tests `:669` cover closure-write or final-deadline failure plus failure-log failure through production main/finish and real temporary JSON/seals. | Repaired for the original scenarios. Final deadline includes closure; lingering INITIAL reports cannot be consumed in those tested paths. |
| One invalid return aborts all score rows | Runner saves all returns/barrier at `:778`–`:788`, then validates inside each case at `:805`–`:809`, retains explicit error rows at `:838`–`:841`, and applies invalid priority at `:750`–`:768`. Tests `:645` cover first/last, nonfinite/shape, clean12/panel36, with other valid cases deliberately failing gates. | Repaired. Available cases receive complete12/36 identity and score/error accounting; timeout/inference exceptions still close early as declared. |
| Reply readiness timeout permits stalled partial line | Runner `:500`–`:531` reads unbuffered single bytes using one monotonic deadline; retains partial hex on expiry/EOF and closes. Inherited startup calls this override at renderer_au `:505`; normal exchange at `:549`. Tests `:708`, `:729`; independent probe1 uses both actual inherited entry points with ordinary OS pipes. | Complete-line deadline repaired for startup and normal exchanges. Partial evidence under transcript failure remains blocker1. |

## Scientific and access design assessment

The fixed scientific question is sound within its stated development scope:
clean plus volume85/drive1/drive2, all12 dependent performances per chain,
unchanged fold2 architecture/weights and average, original targets, identical
normalization/crops/windows/metrics, and each flatref constructed from its OWN
wet waveform. No lag/gain fit, posthoc subset, fitted competitor, training or
native/song/product claim is introduced. Waveform changes remain diagnostic;
the settings do not establish physical nonlinearity.

The declaration guard at runner `:157`–`:212` rejects a draft before asset
hash/load, requires exact committed40 dependency pins, review hash and exact
source/test/body/input attestations, pins plan/review and stage HEAD, and requires
explicit render_di authorization. The exact48 manifest parser and member-only
loader in T `:148`–`:172`, `:239`–`:277` do not discover extra assets. Runtime
original member access is the five waveform members plus baseline net_input;
only render stages call the new render_di loader (`:469`–`:480`). Its native
float64 length/finite/suffix AND byte checks are strict, including signed zero.
There is no raw/catalog/native/reserved fallback.

Execution environments are selected externally: helper .venv for preflight and
renders, original CPU environment for baseline/scores (`:231`–`:237`). No hidden
interpreter switching occurs. Replay108 precedes model loading (`:384`–`:385`),
then exact12 prediction bytes/direct36 scores and unchanged gate precede renders.
V.load_windows decodes saved Torch32 coefficients without reconstructing them;
P's scorer preserves original standardization, center crop and epsilon rules.
D.build_model/rebuild retain original CPU float32 preprocessing and two threads.

The executed local dependency closure is bounded to40 explicit files, including
the numerical helpers, package initializers, whole-preset/R command conversion,
renderer interface/AU implementation, Swift helper/server/probe, pack manifest,
parser/structured writer/formatter, source template and required committed
metadata. I inspected the relevant delegated paths, including Swift XML command
application and frame padding, source command R (FX section on), intrinsic knob
ranges and renderer build identity. Unexecuted training/catalog/search methods
are not prerequisites. No recursive prior-study pin/check expansion is needed.
Runtime versions/module paths/config are observations with the stated limits;
they do not establish an independent binary/hardware or historical runtime audit.

Full ordered template+R commands and exact declared overrides are retained at
`:424`–`:457`, `:662`–`:666`; compressor/base values are preserved. These establish
commands and acknowledgements, not parameter readback. The renderer intercepts
the output-delete boundary, saves decoded padded raw stereo and mono before
validation, retains WAVs/server logs/warmups/first/end repeats, and extracts
`[96000:384000]` and `[96052:384052]` (`:560`–`:573`, `:625`–`:646`). Later slice
loading proves the same bytes. This proves the declared preroll/52 coordinate
convention, not remeasured physical latency.

The exact original1dB active-band/RMS canary is used unchanged for first/end
repeatability and each new/old clean pair. Original metadata, target regeneration
<=1e-8, oracle<1e-6, source/input/HEAD stability, complete coverage and clean F
PASS are mandatory before panel execution. Earlier stage seal/evidence checks
occur before later actual asset access (`:255`–`:267`, `:894`–`:902`). ALL36 panel
predictions are saved before case validation/scoring. Per-chain gates preserve
the stronger frozen F rule: >=10% median improvement over the better coherent
simple arm, >=9 strict wins, positive median in both six-case groups. Overall
PASS requires all3 valid gates; invalidity outranks valid FAIL. No subset rescue.

The future verifier procedure is correctly separate: main dispatches a fresh
numerical verifier AFTER primary stops; that verifier must durably save its OWN
complete derivation/readback and blind barrier BEFORE IT READS primary new
numerical scores/predictions/flatrefs (plan `:194`–`:220`; future verifier brief
steps1–7 and access distinction). The primary runner never invokes an inline
verifier and never requires a precommitted verifier executable. Its reports stay
`verification_status: INITIAL`, `independent_verified: false` (`:848`, `:854`,
`:918`, `:922`). Clean PASS is operational only; independent comparison remains
mandatory before a scientific conclusion. Shared numerical ecosystem and lack
of retrospective runtime auditing are explicit limitations.

## Commands, results and limits

Exact regression command:

`/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -q tests/test_di_morgan_processing_control.py`

Result: **72 passed in 1.01s**, exit0. This is the corrected runner's source-only
suite, not the repository-wide suite or an actual scientific run. Meaningful
new regressions cover the five original findings; no unrelated historical tests
were repeated. Numerical/model/plugin calls are extensively mocked. Assertions
on production save/seal/main/compare code and real temporary artifacts are real;
they do not establish actual CPU output bytes or plugin behavior.

Exact independent probe command:

`/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -n0 -q --doctest-glob=di-morgan-processing-review-v2.md tmp/di-morgan-processing-review-v2.md`

The first invocation failed during collection/execution of setup because a
Markdown closing fence immediately followed a doctest. Only this reviewer-owned
report was repaired with blank lines. The next invocation **passed1 doctest
item in0.21s**, exit0, executing all four probe groups below. Probe1 returned
`(True, True, True)` for both startup and normal entry points; probe2 returned
`(True, True, True)` for all three panel positions; probe3 demonstrated an outer
OSError with an original TimeoutError context and absent durable timeout/partial
bytes; probe4 demonstrated a diagnostic PermissionError replacing the recorded
original archive hash failure while recovery survived. Final probe result after
explicitly checking missing partial-byte fallback is recorded below.

Read-only operations were `cat`/`sed`/`nl`/`rg`/`wc` on the above named source,
test, plan, task, notes, monitor, previous review and relevant helpers;
`git status --short`, `git rev-parse HEAD`, `git branch --show-current`; and
Ruby JSON/Digest checks of the snapshot's explicit pins and all four required
hashes. The combined initial local read reported no physical AGENTS.md (exit1);
the user's supplied instructions were applied. A selected committed-metadata
inspection accidentally printed historical check arrays and was output-truncated;
those old check lists were not executed or used as fresh verification evidence.
Only their committed prerequisite context was consulted.

No actual NPZ/model/average/native/catalog/raw/reserved/audio asset was opened or
hashed, no installed plugin constructed, no Swift compilation, stage execution,
download, commit, child agent or scientific-file edit occurred. Generated NPZs,
NPYs and JSONs existed only in temporary synthetic test directories. Real OS pipe
I/O was tested; actual process shutdown was a stand-in. No actual inference,
scientific accuracy, renderer output, physical latency, independence of installed
libraries/hardware or retrospective runtime access was verified. The verdict is
about source/design and the stated evidence contract only.

## Independent synthetic probes

These doctests use generated arrays, temporary files, ordinary OS pipes and
mocked external boundaries. They do not load actual assets or instantiate a
plugin. Execute with:

`/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -n0 -q --doctest-glob=di-morgan-processing-review-v2.md tmp/di-morgan-processing-review-v2.md`

```python
>>> import io, json, os, time
>>> from pathlib import Path
>>> from tempfile import TemporaryDirectory
>>> from types import SimpleNamespace
>>> from unittest.mock import patch
>>> from contextlib import ExitStack
>>> import numpy as np
>>> from learn import di_morgan_processing_control as M
>>> from match.renderer_au import AudioUnitRenderer
>>> def takes():
...     return [{"slug": f"review-{i}", "take": f"take-{i}", "content": "chords" if i < 6 else "scales"} for i in range(12)]
>>> def ctx():
...     return {"manifest": {"takes": takes(), "preset": "samples/Example_Clean_PR12.xml"}, "pins": {}, "hashes": {}, "revision": "synthetic"}

```

Probe 1 exercises the inherited startup and normal exchange entry points with
real OS pipes. Only process creation/compilation and shutdown are stand-ins.
The actual repaired complete-line reader and transcript persistence are used.

```python
>>> class PipeBackend:
...     _ensure_server = AudioUnitRenderer._ensure_server
...     _exchange = AudioUnitRenderer._exchange
...     def close(self):
...         self.stopped = True
...     def _au_triple(self):
...         return {"type": "synthetic", "subtype": "synthetic", "manufacturer": "synthetic"}
>>> class PipeHost(M.ProtocolEvidence, PipeBackend):
...     pass
>>> def pipe_entry(root, startup):
...     read_fd, write_fd = os.pipe()
...     stream = os.fdopen(read_fd, "r")
...     partial = b'{"ready":' if startup else b'{"ok":'
...     _ = os.write(write_fd, partial)
...     proc = SimpleNamespace(stdout=stream, stdin=io.StringIO(), poll=lambda: None)
...     host = PipeHost()
...     host._process = None if startup else proc
...     host._binary, host._workdir, host.settle_ms = root / "synthetic-never-executed", root, 0
...     host.started, host.reply_timeout_s, host.transcript = time.monotonic(), .02, root / "protocol.jsonl"
...     host.stopped, host._log = False, None
...     before = time.monotonic()
...     try:
...         with patch.object(M.subprocess, "Popen", return_value=proc):
...             try:
...                 host._ensure_server() if startup else host._exchange({"synthetic": True})
...             except TimeoutError as error:
...                 assert "complete protocol line" in str(error)
...             else:
...                 raise AssertionError("partial line accepted")
...         elapsed = time.monotonic() - before
...         events = [json.loads(line) for line in host.transcript.read_text().splitlines()]
...         rejection = next(e for e in events if e["event"] == "read-error")
...         return host.stopped, rejection["partial_raw_hex"] == partial.hex(), elapsed < .5
...     finally:
...         stream.close()
...         os.close(write_fd)
...         if host._log is not None:
...             host._log.close()
>>> for startup in (True, False):
...     with TemporaryDirectory(prefix="processing-review-pipe-") as directory:
...         print(pipe_entry(Path(directory), startup))
(True, True, True)
(True, True, True)

```

Probe 2 checks the repaired full render-stage to chain-stage identity path for
each of the three panel positions, using a full identity with several fields.
Earlier valid chains may finish; the changed host must close before its warmup.
No actual rendering, model, average or original input access occurs.

```python
>>> def startup_panel(root, bad_chain):
...     import research.render_preset_panel as RP
...     identity = {"plugin_version": "same", "renderer_build": "same", "quality_mode": "original"}
...     hosts, labels = [], []
...     base = {k: "0.21" for changes in M.OVERRIDES.values() for k in changes}
...     base.update({"pr12Amp/pr12Volume": "0.62", "drive1/drive1Active": "false", "drive2/drive2Active": "false"})
...     edits = [{"module": k.rpartition("/")[0], "key": k.rpartition("/")[2], "value": v} for k, v in base.items()]
...     def factory(out, started):
...         observed = {**identity, "renderer_build": "different"} if out.name == bad_chain else identity.copy()
...         h = SimpleNamespace(chain=out.name, closed=False, metadata=lambda: SimpleNamespace(as_dict=lambda: observed))
...         h.close = lambda: setattr(h, "closed", True)
...         hosts.append(h)
...         return h
...     actual_chain = M.render_chain
...     def chain(*args, **kwargs):
...         return actual_chain(*args, host_factory=factory, **kwargs)
...     def full(host, out, label, *args):
...         labels.append((host.chain, label))
...         return np.arange(10, dtype=np.float64), identity.copy()
...     with ExitStack() as stack:
...         replacements = {"PREROLL": 3, "N": 5, "LATENCY": 2, "check_time": lambda *a: None,
...             "recheck": lambda *a: None, "check_inputs": lambda *a: None,
...             "stage_report": lambda *a: {"chains": [{"identity": identity}]},
...             "load_render_di": lambda *a: {t["slug"]: np.arange(8, dtype=np.float64) for t in takes()},
...             "render_chain": chain, "full_render": full}
...         for name, value in replacements.items():
...             _ = stack.enter_context(patch.object(M, name, value))
...         _ = stack.enter_context(patch.object(RP, "preset_edits", lambda *a: (1, edits)))
...         _ = stack.enter_context(patch.object(M.R, "repeat_canary", lambda *a: {"passed": True}))
...         try:
...             M.render_stage(root, ctx(), {t["slug"]: {"di": np.arange(5, dtype=np.float64)} for t in takes()}, 0, M.EXPERIMENTS)
...         except ValueError as error:
...             assert "sealed clean identity" in str(error)
...         else:
...             raise AssertionError("identity drift accepted")
...     observed = json.loads((root / bad_chain / "startup-identity.json").read_text())
...     return all(h.closed for h in hosts), not any(c == bad_chain for c, label in labels), observed["observed"] != observed["expected"]
>>> for bad_chain in M.EXPERIMENTS:
...     with TemporaryDirectory(prefix="processing-review-identity-") as directory:
...         print(startup_panel(Path(directory), bad_chain))
(True, True, True)
(True, True, True)
(True, True, True)

```

Probe 3 tests a transcript becoming unwritable AFTER the request is durably
recorded. The inherited normal exchange waits on a stalled partial reply. The
reader encounters the original TimeoutError and attempts shutdown; subsequent
diagnostic logging also fails. Other evidence paths remain writable.

```python
>>> def double_protocol_failure(root):
...     read_fd, write_fd = os.pipe()
...     stream = os.fdopen(read_fd, "r")
...     _ = os.write(write_fd, b'{"ok":')
...     host = PipeHost()
...     host._process = SimpleNamespace(stdout=stream, stdin=io.StringIO(), poll=lambda: None)
...     host.started, host.reply_timeout_s, host.transcript = time.monotonic(), .02, root / "protocol.jsonl"
...     host.stopped = False
...     actual_event = M.event
...     def broken_transcript(path, row):
...         if row["event"] != "request" or row.get("command") == {"quit": True}:
...             raise OSError("transcript became unwritable")
...         actual_event(path, row)
...     try:
...         with patch.object(M, "event", broken_transcript):
...             try:
...                 host._exchange({"synthetic": True})
...             except Exception as error:
...                 recorded = M.failure(error)
...                 original_context = type(error.__context__).__name__
...             else:
...                 raise AssertionError("expected failure")
...         M.write_json(root / "outer-partial.json", {"body_error": recorded, "close_errors": host.evidence_close_errors,
...                      "protocol_logging_error": getattr(host, "protocol_logging_error", None)})
...         saved = json.loads((root / "outer-partial.json").read_text())
...         return saved["body_error"]["type"], original_context, host.stopped, "TimeoutError" in json.dumps(saved), "partial_raw_hex" in json.dumps(saved)
...     finally:
...         stream.close()
...         os.close(write_fd)
>>> with TemporaryDirectory(prefix="processing-review-errors-") as directory:
...     print(double_protocol_failure(Path(directory)))
('OSError', 'TimeoutError', True, False, False)

```

Probe 4 checks two simultaneous failures during return preservation: archive
hashing fails, recovery arrays succeed, then the diagnostic JSON fails. The
outer error record should still identify the original hash failure.

```python
>>> def double_save_failure(root):
...     actual_write = M.write_json
...     def bad_write(path, value):
...         if Path(path).name.endswith(".save-failure.json"):
...             raise PermissionError("save diagnostic rejected")
...         actual_write(path, value)
...     with patch.object(M.R, "sha", side_effect=OSError("original archive hash failure")), patch.object(M, "write_json", bad_write):
...         try:
...             M.save_arrays(root / "synthetic.npz", returned=np.arange(4, dtype=np.float64))
...         except Exception as error:
...             recorded = M.failure(error)
...             original_context = str(error.__context__)
...         else:
...             raise AssertionError("expected failure")
...     actual_write(root / "outer-partial.json", {"error": recorded})
...     return recorded["type"], original_context, (root / "synthetic.npz.returned.recovery.npy").exists(), "original archive hash failure" in (root / "outer-partial.json").read_text()
>>> with TemporaryDirectory(prefix="processing-review-save-") as directory:
...     print(double_save_failure(Path(directory)))
('PermissionError', 'original archive hash failure', True, False)

```


## Exact40 reviewed source and metadata pins

All40 match current bytes. The38 existing tracked pins also match HEAD via
`git show HEAD:PATH`; only the new runner and test are awaiting declaration
commit. The full plan is independently hashed above.

```json
{
  "learn/di_morgan_processing_control.py": "babb9cab20e995ee4bb02abfcc3df82d831f7f06df376925596604b2527203df",
  "tests/test_di_morgan_processing_control.py": "8da80d2d7286cbb654291ca9242ab839f7f10b72eb9aab8bb77156952780c49d",
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
}
```

## Final verification

After completing the report, the independent doctest command passed again:
**1 doctest item passed in0.21s**, exit0. This rerun was needed because probe3
was strengthened to assert missing partial-byte fallback explicitly. Its exact
output is `('OSError', 'TimeoutError', True, False, False)`. Probe3 uses
the production reader/exchange/close and failure serializer, then constructs an
outer JSON error record; it does not run full main. Probe2 runs both production
render_stage and render_chain, with rendering and external asset boundaries
replaced. Probe4 runs production save/recovery and failure serialization.

The40 pins, full-plan/body/input digests and HEAD were checked once more after
all probe execution. No reviewed source/test/plan changed. Final verdict remains
BLOCK for the two concrete evidence-preservation gaps above.
