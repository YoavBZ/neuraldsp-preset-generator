# Fresh independent Morgan processing source/design review V3

Verdict: APPROVE

This is approval of the current whole source/design procedure, with no remaining
blocking findings. It is not permission to run any stage. Main must archive this
review, add the administrative DECLARED attestation above the frozen body, and
commit the reviewed sources/tests/body, exact pins and review together before
actual asset hashing/loading or plugin construction. No scientific body change
is approved by this report.

I independently read the complete current runner, test suite and plan, the
review brief, repair notes, live monitor, and archived V2 BLOCK. I inspected the
relevant immutable numerical, input, rendering, build, pack and format call
paths. The archived review established the questions to investigate; its repair
assessment and main's test count were not accepted as substitute evidence. The
monitor and brief contain stale V2 hashes/report ownership; this user's V3
instruction and the latest snapshot identify the scope and sole output here.

## Exact reviewed snapshot

| Item | SHA256 / revision |
| --- | --- |
| HEAD | `40e0ca3b48abfa47772897abfc44df97079cf372` |
| Runner | `5ec8c5ca44ccfa94012df14883c9c89ab2a2faa76545c1a025a6b33cf42e8050` |
| Tests | `fc181e489575e80840610c7f9f32aef079512779299719573912eecbee07f1e6` |
| Scientific body | `050981984da9f61237cf9afcbe41b697516f5edd20a4a80c86f2d018c0fcf28b` |
| Original48 input manifest | `1c6cde4a6bdaa5ceb71fd43e56a21049cffb2bbd023a359d8f7b44de4f6dc527` |
| Full draft plan | `14c60563ea7f65468f96ff25dc7233ed13b62cc7197c942e82b726ae6d5ea1a1` |
| Supplied snapshot JSON | `2dbf11f8154abc569c77af4f1bc4abb46a7378a92793e62b4c2a6db1358a2e79` |

Branch: `codex/song-model-continuation`. The scientific body digest covers the
UTF8 bytes AFTER `## Frozen design\n`, matching `T.design_bytes`; the full plan
hash is separate because later administrative declaration changes its preamble.
The input hash identifies the 48-line TEXT manifest, not independently observed
hashes of its NPZ assets. No actual NPZ was hashed or opened.

All **40 unique explicit pins** match current file bytes, with an exact set
comparison against the runner's SOURCE_FILES. All **38 existing tracked pins**
also match `git show HEAD:PATH`. Only runner/test pins differ from the archived
V2 snapshot; the original input-manifest digest is unchanged. The full map is
retained below. Runner/test/plan are still uncommitted drafts, consistent with
source review; the declaration/commit gate remains necessary.

## Error-preservation assessment

| Path | Independent evidence and judgment |
| --- | --- |
| Error carrier and serialization | Runner `:106`–`:117` copies evidence into structured snapshots. Each read record snapshots the error BEFORE attachment; subsequent exchange records snapshot earlier evidence. Current construction has no reference back to the owning exception/list. Probe A walks object ancestry before JSON serialization; Probe B checks the archive error carrier; Probe C checks explicit nonfinite rejection paths. Both new error families serialize without cycles. |
| Complete-line read, startup and normal exchanges | Runner `:535`–`:578` uses one monotonic deadline and unbuffered descriptor reads; exact partial hex and decoded diagnostic text are attached before transcript I/O. The inherited startup at renderer_au `:505` and exchange at `:549` call this override. Runner `:505`–`:530` retains event and logging error separately and re-raises the original timeout. Six Probe A cases traverse these actual boundaries using real OS pipes, including non-UTF8 partial bytes. The original TimeoutError/bytes/logging failures survive durable chain and outer records. V2 blocker 1 is repaired. |
| Shutdown and chain partial/fallback | Runner `:608`–`:632` always attempts backend close despite quit-log failure. Runner `:723`–`:750` separately attempts close, protocol-fallback, partial and cleanup diagnostics; an existing body error retains priority. Probe A uses the actual inherited backend close, forcing first-wait TimeoutExpired to verify quit, stdin close, kill and second wait. It independently rejects protocol-fallback or partial persistence and checks the surviving path and cleanup errors. Host/process/log state closes; no timeout is converted into success. |
| Archive/hash and diagnostic failures | Runner `:125`–`:165` attempts an fsynced per-member recovery after serialization/hash/identity failure, captures recovery outcomes and separate diagnostic/fallback errors on the original exception, and reaches the outer bare re-raise. Four Probe B cases cover serialization and hash failure with diagnostic-only or diagnostic-plus-fallback failure, through real chain cleanup. The exact original exception object reappears; its recovery arrays preserve NaN/Inf/signed-zero bytes. Partial and outer JSON retain original/recovery/diagnostic evidence. V2 blocker 2 is repaired. |
| No false PASS | Logging or save errors propagate out of the chain; cleanup-only errors also raise. Main `:960`–`:992` withdraws result/seal authority before attempting diagnostics independently. stage_report `:259`–`:271` rejects invalidation/failure/closure errors; barriers verify every sealed evidence file. The reproduced suite's `test_main_finalization_failures_withdraw_authority_before_bad_log` (`:669`) exercises both closure-write failure and final-deadline failure together with failing failure-log writes through production main/finish and temporary JSON/seals. `:514` tests overbudget final save. Both pass. Probe A/B check failed chains publish no result/seal; they do not independently run full main. |

The new explicit error-preservation wording at plan `:167`–`:172` is consistent
with these implemented paths. Successful error persistence is conditional on
some evidence destinations remaining writable. Total filesystem failure,
abrupt termination, and hostile/malformed self-referential objects supplied by
outside test code are not guarantees established by these probes. The runner's
own constructed records in the reviewed paths are acyclic and preserve raw
numerical returns separately from finite JSON diagnostics.

## Whole-procedure source/design judgment

The fixed question is answerable within its stated scope: frozen fold2 against
wet and each wet's OWN coherent flatref, at volume85/drive1/drive2 on all twelve
dependent development performances, with the existing targets, metrics and
gate. A pass is development coverage, with no native/song/multi-guitar/product
accuracy or training-necessity inference. Waveform changes are diagnostic and
do not establish physical nonlinearity. No post-data fit, subset, threshold or
rerun rescue is introduced.

The administrative guard (`:176`–`:231`) checks review/declaration, exact
source/test/body/input identities, dedicated committed review, committed plan,
explicit render_di authorization, and fixed model/average/template metadata
before any real binary asset access. Missing DRAFT approval fails first. The
40-file closure includes T/F/C/P/R/V, model architecture and spectrum helper,
renderer interface/AU implementation, Swift compiler/server/probe, pack and
format dependencies, package initializers and required saved metadata/window
bits. It does not recursively execute historical studies. Stage provenance and
barriers freeze HEAD/source/input identities across stages (`:234`–`:286`).

T.declared_hashes (`:148`–`:172`) restricts exact48 identities, and T.load_inputs
(`:239`–`:277`) opens only the original five waveform members. Baseline alone
adds original net_input (`:309`–`:325`); render stages alone add prepare.render_di
(`:479`–`:499`). Its finite native float64 length and exact sample AND byte
overlap are checked; signed-zero mismatch is rejected. There is no actual
raw/catalog/native/reserved fallback in the called paths. The declaration
metadata has twelve unique takes, six chords/six scales, fixed PR12 template,
the exact model/average constants, and persisted Torch32 windows. I inspected
these declarations without touching their binary assets.

The six stages and explicit interpreter split are enforced (`:250`–`:256`,
`:920`–`:954`). Preflight replays108; baseline repeats108 BEFORE model loading,
then exact12 prediction bytes/direct36 scores and the unchanged F gate
(`:329`–`:440`). There is no implicit interpreter switch. V.load_windows
decodes saved float32 coefficient bits; D.build_model/rebuild preserve CPU eval,
two threads, original float32 conversion, normalization and reconstruction.
P scoring preserves the common target, independent center-crop standardization,
MR-STFT, waveform L1 and lowband filtering; no delay/gain is fitted. Those
historical numerical results were not recomputed in this review.

RP.preset_edits preserves the source command plus R, including FX section on
and original compressor state. command_panel (`:443`–`:476`) keeps order and
all undeclared values, exact PR12 selection and .62 base volume, applying only
declared writable switch/rotation overrides. Swift starts each command from
startup state, selects the amp and applies edits; the subclass disables silent
retry/isolation rescue. Acknowledgements are command evidence, with no parameter
readback or physical52-sample latency claim.

New clean rendering retains warmup, first/end repeats and all12 on one host;
panel uses three separately constructed hosts. Full startup identity is checked
against sealed clean BEFORE each experimental warmup (`:690`–`:704`) and again
through all cases/repeats/scoring. The clean score barrier is durably sealed
before experimental construction. Full padded raw stereo, mono, trimmed returns,
inputs, commands, replies, partial bytes and errors are retained. Saved full
arrays prove the 96000 preroll and52-sample coordinate slices, including later
load-time rederivation (`:658`–`:679`, `:779`–`:787`). Repeat and clean/original
compatibility use the existing1dB active-band/RMS canary without relaxation.

All12/36 prediction returns are saved before any new validity/scoring gates
(`:818`–`:828`). Each available case receives a prediction identity and score
or error row, including first/last malformed and nonfinite predictions; errors
have INCONCLUSIVE priority over other cases' valid FAIL (`:790`–`:808`,
`:841`–`:888`). Target regeneration, oracle, metadata and coverage controls
remain mandatory. All three valid per-chain F gates must pass: median benefit
>=10%, >=9 strict wins, positive chord and scale medians. No pooled/subset rescue
is available. The reproduced suite exercises these barriers and priorities.

Finalization includes saving, hashing, close and post-publication checks in the
cooperative900-second budget (`:892`–`:992`). Results remain INITIAL with
independent_verified:false. Plan `:200`–`:226` correctly requires a FRESH task
AFTER primary completion, with its own preprocessing/architecture/scorer,
commands/slices/controls, full saved derivation and read-barrier BEFORE that
verifier reads primary new scores/predictions/flatrefs. It uses retained render
input copies and performs no rerender or failed-prerequisite rescue. There is
no inline executable or precommitted numerical verifier in the runner. A clean
primary PASS is only an operational prerequisite; a scientific conclusion waits
for independent comparison, with disagreement INCONCLUSIVE.

## Commands, results and boundaries

1. `/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -n0 -q tests/test_di_morgan_processing_control.py`
   — exit0, **76 passed in0.90s**. I read the whole suite before running it;
   generated temporary NPZ/NPY/JSON and committed source/parameter metadata only.
2. The exact independent doctest command below — exit0,
   **1 doctest item passed in0.32s**, covering six combined protocol failure
   cases, four combined archive/hash failure cases and one finite-JSON carrier
   case. Every asserted output appears below. These are independent synthetic
   probes of production paths, with external boundaries explicitly mocked.
3. A local Ruby JSON/Digest/Open3 check extracted SOURCE_FILES, required40
   unique entries/exact snapshot key equality, hashed each listed source or
   committed metadata file, compared all38 existing pins to
   `git show HEAD:PATH`, computed full-plan/body/input/snapshot digests, and
   checked `git rev-parse HEAD`. All checks passed. The exact40 map is below.
4. Read-only `cat`, `sed`, `nl -ba`, `rg`, `wc`, `git status --short`,
   `git branch --show-current`, `git rev-parse HEAD`, and Ruby selected-metadata
   inspection were used. Initial combined `cat` returned exit1 because no
   physical AGENTS.md exists here; user-supplied AGENTS instructions were applied.
   Some broad combined source output was truncated, then relevant sections were
   read in smaller ranges. No missing output was treated as reviewed evidence.

Only `tmp/di-morgan-processing-review-v3.md` was authored. No actual NPZ/model/
average/audio/native/raw/catalog/reserved asset hashing or loading, installed
plugin construction, Swift compilation, scientific stage execution, download,
code/test/plan edit, commit or child agent occurred. Test temporary files are
generated synthetic evidence. OS pipe reads and real backend shutdown CONTROL
FLOW were tested; subprocess creation and process OS actions were stand-ins.
Actual process reaping, plugin responses, inference, scientific accuracy,
physical latency and runtime asset identities were not tested. Installed
NumPy/SciPy/Torch and hardware remain a shared verification ecosystem; recorded
module paths/config do not establish retrospective runtime access or complete
dynamic-library/toolchain identity. Cooperative checks cannot interrupt every
native call/compile, and total evidence-write failure cannot promise recovery.
These are the plan's explicit limits, not an unconditional scientific PASS.

## Independent synthetic probes

These probes are this reviewer's own source tests. They use generated arrays,
temporary directories, ordinary OS pipes, and stand-ins at external boundaries.
They never construct an installed plugin, invoke a scientific stage against real
inputs, or open any actual study asset. They are review evidence, not an inline
scientific verifier or a proposed precommit verification requirement.

Run exactly:

`/Users/yoavbz/.codex/bin/neuraldsp-safe pytest -n0 -q --doctest-glob=di-morgan-processing-review-v3.md tmp/di-morgan-processing-review-v3.md`

```python
>>> import io, json, os, time, subprocess
>>> from pathlib import Path
>>> from tempfile import TemporaryDirectory
>>> from types import SimpleNamespace
>>> from unittest.mock import patch
>>> from contextlib import ExitStack
>>> import numpy as np
>>> from learn import di_morgan_processing_control as M
>>> from match.renderer_au import AudioUnitRenderer
>>> import research.render_preset_panel as RP
>>> def strict_json(path):
...     def bad_constant(value):
...         raise AssertionError('nonfinite JSON: ' + value)
...     return json.loads(Path(path).read_text(), parse_constant=bad_constant)
>>> def acyclic(value, ancestors=()):
...     if isinstance(value, (dict, list, tuple)):
...         assert id(value) not in ancestors, 'cycle in retained evidence'
...         for item in (value.values() if isinstance(value, dict) else value):
...             acyclic(item, (*ancestors, id(value)))
>>> def takes():
...     return [{'slug': f'v3-{i}', 'take': f'v3-take-{i}', 'content': 'chords' if i < 6 else 'scales'} for i in range(12)]
>>> def ctx():
...     return {'manifest': {'takes': takes(), 'preset': 'samples/Example_Clean_PR12.xml'}, 'pins': {}, 'hashes': {}, 'revision': 'synthetic'}
>>> def base_edits():
...     values = {key: '0.21' for overrides in M.OVERRIDES.values() for key in overrides}
...     values.update({'pr12Amp/pr12Volume': '0.62', 'drive1/drive1Active': 'false', 'drive2/drive2Active': 'false'})
...     return [{'module': k.rpartition('/')[0], 'key': k.rpartition('/')[2], 'value': v} for k, v in values.items()]

```

Probe A traverses production `render_chain`, inherited startup/exchange,
production complete-line reading, production protocol close, and the inherited
backend close implementation. Process creation is replaced; the fake process's
first wait raises TimeoutExpired, so the real close code must send quit, close
stdin, kill and wait again. The partial reply is supplied through an ordinary
OS pipe. Transcript writes fail after the normal request; startup logging fails
on its first read error. Independently reject either chain fallback or partial
JSON and require the surviving path plus the outer error record to retain the
original timeout, exact bytes and logging failures. No mock replaces the reader,
exchange, failure serializer, fallback writer or backend close code.

```python
>>> class CapturedInput(io.StringIO):
...     def close(self):
...         self.sent = self.getvalue()
...         super().close()
>>> class ProcessStandIn:
...     def __init__(self, stream):
...         self.stdout, self.stdin = stream, CapturedInput()
...         self.alive, self.kills, self.waits = True, 0, []
...     def poll(self):
...         return None if self.alive else -9
...     def wait(self, timeout=None):
...         self.waits.append(timeout)
...         if len(self.waits) == 1:
...             raise subprocess.TimeoutExpired('synthetic-only', timeout)
...         self.alive = False
...         return -9
...     def kill(self):
...         self.kills += 1
>>> class PipeBackend:
...     _ensure_server = AudioUnitRenderer._ensure_server
...     _exchange = AudioUnitRenderer._exchange
...     close = AudioUnitRenderer.close
...     def _au_triple(self):
...         return {'type': 'synthetic', 'subtype': 'synthetic', 'manufacturer': 'synthetic'}
>>> class PipeHost(M.ProtocolEvidence, PipeBackend):
...     def metadata(self):
...         self._ensure_server()
...         return SimpleNamespace(as_dict=lambda: {'plugin_version': 'synthetic'})
>>> def protocol_probe(root, startup, denied):
...     read_fd, write_fd = os.pipe()
...     stream = os.fdopen(read_fd, 'r')
...     partial = b'{"ready":\xff' if startup else b'{"ok":\xfe'
...     _ = os.write(write_fd, partial)
...     proc, host = ProcessStandIn(stream), PipeHost()
...     host._process = None if startup else proc
...     host._binary, host._workdir, host.settle_ms = root / 'never-executed', root, 0
...     host.started, host.reply_timeout_s = time.monotonic(), .03
...     host.transcript, host._log, host._owns_workdir = root / 'protocol.jsonl', None, False
...     actual_event, actual_write = M.event, M.write_json
...     def broken_event(path, record):
...         if record['event'] == 'request' and record.get('command') != {'quit': True}:
...             return actual_event(path, record)
...         raise PermissionError('V3 transcript rejected')
...     def selective_write(path, record):
...         if Path(path).name == denied:
...             raise OSError('V3 chain evidence rejected: ' + denied)
...         return actual_write(path, record)
...     def exchange_render(*args):
...         host._exchange({'synthetic_command': 3})
...         raise AssertionError('incomplete reply accepted')
...     before = time.monotonic()
...     try:
...         with ExitStack() as stack:
...             _ = stack.enter_context(patch.object(M, 'event', broken_event))
...             _ = stack.enter_context(patch.object(M, 'write_json', selective_write))
...             _ = stack.enter_context(patch.object(M.subprocess, 'Popen', return_value=proc))
...             _ = stack.enter_context(patch.object(RP, 'preset_edits', return_value=(1, base_edits())))
...             _ = stack.enter_context(patch.object(M, 'full_render', exchange_render))
...             try:
...                 M.render_chain(root / 'chain', 'clean', ctx(), {t['slug']: np.zeros(8) for t in takes()},
...                     host.started, host_factory=lambda *args: host,
...                     expected_identity={'plugin_version': 'synthetic'} if startup else None)
...             except TimeoutError as error:
...                 original = error
...                 assert 'complete protocol line' in str(error)
...             else:
...                 raise AssertionError('timeout was replaced or accepted')
...         assert time.monotonic() - before < .8
...         assert not proc.alive and proc.kills == 1 and proc.waits == [10, None]
...         assert proc.stdin.closed and '{"quit":true}' in proc.stdin.sent
...         assert host._process is None and host.evidence_closed and host._log is None
...         acyclic(host.protocol_evidence)
...         acyclic(original.processing_evidence)
...         error_record = M.failure(original)
...         assert error_record['type'] == 'TimeoutError'
...         actual_write(root / 'outer-error.json', {'error': error_record})
...         surviving = [name for name in ('protocol-fallback.json', 'partial.json') if name != denied]
...         for name in surviving:
...             value = strict_json(root / 'chain' / name)
...             text = json.dumps(value, allow_nan=False)
...             assert 'TimeoutError' in text and partial.hex() in text and 'V3 transcript rejected' in text
...         outer = strict_json(root / 'outer-error.json')
...         assert partial.hex() in json.dumps(outer, allow_nan=False)
...         if denied:
...             assert not (root / 'chain' / denied).exists()
...             assert 'V3 chain evidence rejected' in json.dumps(strict_json(root / 'chain' / 'cleanup-errors.json'))
...         assert not (root / 'chain' / 'result.json').exists() and not (root / 'chain' / 'seal.json').exists()
...         return 'startup' if startup else 'normal', denied or 'both paths saved', 'original/bytes/cleanup retained'
...     finally:
...         stream.close()
...         os.close(write_fd)
...         if host._log is not None:
...             host._log.close()
>>> for startup in (False, True):
...     for denied in (None, 'protocol-fallback.json', 'partial.json'):
...         with TemporaryDirectory(prefix='processing-review-v3-pipe-') as directory:
...             print(protocol_probe(Path(directory), startup, denied))
('normal', 'both paths saved', 'original/bytes/cleanup retained')
('normal', 'protocol-fallback.json', 'original/bytes/cleanup retained')
('normal', 'partial.json', 'original/bytes/cleanup retained')
('startup', 'both paths saved', 'original/bytes/cleanup retained')
('startup', 'protocol-fallback.json', 'original/bytes/cleanup retained')
('startup', 'partial.json', 'original/bytes/cleanup retained')

```

Probe B injects either initial archive serialization or subsequent hashing
failure. Both diagnostic-only and diagnostic-plus-fallback failure are checked.
Generated nonfinite and signed-zero array bytes must survive per-member recovery;
hash failures must leave the complete attempted archive readable. These errors
traverse real `render_chain` cleanup and its durable body-error persistence,
not just a hand-built serializer demonstration. The exact original exception
object must be re-raised. The outer record and chain partial must retain recovery
outcomes and each failed diagnostic path without cycles or nonfinite JSON.

```python
>>> def save_probe(root, operation, fallback_denied):
...     values = np.array([1., -0., np.nan, np.inf, -np.inf], dtype=np.float64)
...     original = OSError('V3 original ' + operation + ' error')
...     actual_write = M.write_json
...     host = SimpleNamespace(closed=False)
...     host.close = lambda: setattr(host, 'closed', True)
...     def diagnostic_write(path, record):
...         name = Path(path).name
...         if name.endswith('.save-failure.json'):
...             raise PermissionError('V3 diagnostic write rejected')
...         if fallback_denied and name.endswith('.save-fallback.json'):
...             raise OSError('V3 save fallback rejected')
...         return actual_write(path, record)
...     def render(host, out, label, *args):
...         M.save_arrays(out / 'synthetic-return.npz', returned=values)
...         raise AssertionError('failed archive accepted')
...     with ExitStack() as stack:
...         _ = stack.enter_context(patch.object(M, 'write_json', diagnostic_write))
...         _ = stack.enter_context(patch.object(RP, 'preset_edits', return_value=(1, base_edits())))
...         _ = stack.enter_context(patch.object(M, 'full_render', render))
...         if operation == 'hash':
...             _ = stack.enter_context(patch.object(M.R, 'sha', side_effect=original))
...         else:
...             _ = stack.enter_context(patch.object(np, 'savez_compressed', side_effect=original))
...         try:
...             M.render_chain(root / 'chain', 'clean', ctx(), {t['slug']: np.zeros(8) for t in takes()},
...                            time.monotonic(), host_factory=lambda *args: host)
...         except OSError as error:
...             assert error is original
...         else:
...             raise AssertionError('original archive error was replaced or accepted')
...     assert host.closed
...     archive = root / 'chain' / 'synthetic-return.npz'
...     assert archive.exists()
...     recovered = np.load(archive.with_name(archive.name + '.returned.recovery.npy'), allow_pickle=False)
...     assert recovered.tobytes() == values.tobytes()
...     if operation == 'hash':
...         with np.load(archive, allow_pickle=False) as saved:
...             assert saved['returned'].tobytes() == values.tobytes()
...     acyclic(original.processing_evidence)
...     record = strict_json(root / 'chain' / 'partial.json')['body_error']
...     assert record['type'] == 'OSError' and record['message'] == str(original)
...     evidence = record['processing_evidence'][0]
...     assert evidence['recovery'] == {'returned': 'saved'}
...     assert evidence['original_error'] == {'type': 'OSError', 'message': str(original)}
...     assert evidence['diagnostic_error']['type'] == 'PermissionError'
...     assert ('fallback_error' in evidence) == fallback_denied
...     if fallback_denied:
...         assert evidence['fallback_error']['message'] == 'V3 save fallback rejected'
...     else:
...         assert strict_json(archive.with_suffix('.save-fallback.json'))['recovery'] == {'returned': 'saved'}
...     actual_write(root / 'outer-error.json', {'error': M.failure(original)})
...     assert strict_json(root / 'outer-error.json')['error']['message'] == str(original)
...     assert not (root / 'chain' / 'result.json').exists()
...     return operation, fallback_denied, 'same original/recovery/diagnostics retained'
>>> for operation in ('archive', 'hash'):
...     for fallback_denied in (False, True):
...         with TemporaryDirectory(prefix='processing-review-v3-save-') as directory:
...             print(save_probe(Path(directory), operation, fallback_denied))
('archive', False, 'same original/recovery/diagnostics retained')
('archive', True, 'same original/recovery/diagnostics retained')
('hash', False, 'same original/recovery/diagnostics retained')
('hash', True, 'same original/recovery/diagnostics retained')

```

Probe C adds nonfinite diagnostic values to a carried error, serializes it through
the real writer, and requires explicit rejection paths. The carrier must remain
acyclic and preserve the original type/message; raw numerical evidence is never
coerced by this diagnostic serialization.

```python
>>> with TemporaryDirectory(prefix='processing-review-v3-json-') as directory:
...     error = TimeoutError('V3 original')
...     M.error_evidence(error, {'diagnostic': [float('nan'), {'value': float('inf')}]})
...     acyclic(error.processing_evidence)
...     path = Path(directory) / 'finite.json'
...     M.write_json(path, {'error': M.failure(error)})
...     saved = strict_json(path)
...     assert saved['error']['type'] == 'TimeoutError'
...     assert saved['error']['processing_evidence'][0]['diagnostic'] == [None, {'value': None}]
...     assert saved['nonfinite_diagnostic_fields'] == ['row.error.processing_evidence[0].diagnostic[0]', 'row.error.processing_evidence[0].diagnostic[1].value']
...     print('acyclic original evidence and finite JSON with exact rejected paths')
acyclic original evidence and finite JSON with exact rejected paths

```

## Exact40 verified source and metadata pins

All40 current bytes matched, and all38 existing tracked files also matched HEAD.
The final freeze check after the independent probes and report drafting again
confirmed all40 current pins, full plan, scientific body, input manifest, snapshot
and HEAD unchanged. No actual asset was included in either check.

```json
{
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
}
```

Final source/design verdict remains APPROVE. Main's administrative declaration
and commit are still required before stage execution; fresh numerical
verification remains a separately commissioned task after primary completion.
