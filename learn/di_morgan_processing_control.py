"""DRAFT: fixed PR12 processing coverage on twelve dependent development DIs.

Import performs no asset access, model loading or plugin construction. Execution
requires fresh source review and a committed declaration. Outcomes are INITIAL;
main commissions fresh independent recomputation after primary completion.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import selectors
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from learn import di_timing_sensitivity as T

P, F, R, V = T.P, T.F, T.R, T.V
PLAN = "docs/di-morgan-processing-control-plan.md"
OUTPUT = "tmp/di-morgan-processing-control-20261009"
STAGES = ("preflight", "baseline", "render-clean", "score-clean", "render-panel", "score-panel")
EXPERIMENTS = ("volume85", "drive1", "drive2")
SCOPE = "fixed-pr12-processing-dependent-p2-development-only"
LIMIT = 900
PREROLL, N, LATENCY = 96000, 288000, 52
MODEL = {"path": "/Users/yoavbz/ndsp-presets/learn/direc/models-set3/fold2.pt",
         "sha256": "16b2b734b49cc1cc2d7e547d96d3bb56208007c9cae0d0e33acb1c2a1cdd042b"}
AVERAGE = {"path": "/Users/yoavbz/ndsp-presets/learn/direc/cache/average-fold2.npy",
           "sha256": "9aa3c3bfefc2bc5ba21394be29876b5ef5e0120ad2f55f0b890e599ec3bee9a8"}
# Explicit executed dependency closure, not inherited historical pin chains.
SOURCE_FILES = (
    "learn/di_morgan_processing_control.py", "tests/test_di_morgan_processing_control.py",
    "learn/__init__.py", "learn/di_timing_sensitivity.py", "learn/di_morgan_flatref.py",
    "learn/di_morgan_control.py", "learn/di_domain_pilot.py", "learn/run_di_domain_pilot.py",
    "learn/run_di_domain_pilot_v2.py", "learn/direc.py", "learn/di_robustness.py",
    "research/__init__.py", "research/render_preset_panel.py", "scripts/_cli.py", "scripts/_swift.py",
    "scripts/au_render_server.swift", "scripts/au_probe.swift",
    "match/__init__.py", "match/renderer.py", "match/renderer_au.py",
    "packs/__init__.py", "packs/loader.py", "packs/morgan/manifest.json",
    "format/__init__.py", "format/parser.py", "format/structured.py", "format/markers.py",
    "format/translate.py", "format/writer.py", "samples/Example_Clean_PR12.xml",
    "docs/di-domain-pilot-inputs.json", "docs/di-domain-pilot-v2-inputs.json",
    "docs/di-domain-metric-probe-windows.json.gz", "docs/di-timing-sensitivity-inputs.sha256",
    "docs/di-timing-sensitivity-inputs.json", "docs/di-morgan-flatref.json",
    "docs/di-morgan-flatref-verification.json", "docs/di-morgan-control-verification.json",
    "docs/di-morgan-control-prepare.json", "docs/di-morgan-control-render.json",
)
OVERRIDES = {
    "clean": {},
    "volume85": {"pr12Amp/pr12Volume": "0.85", "drive1/drive1Active": "false",
                 "drive2/drive2Active": "false"},
    "drive1": {"drive1/drive1Active": "true", "drive1/drive1Drive": "0.65",
               "drive1/drive1Tone": "0.5", "drive1/drive1Level": "0.5",
               "drive2/drive2Active": "false"},
    "drive2": {"drive2/drive2Active": "true", "drive2/drive2Gain": "0.65",
               "drive2/drive2Bass": "0.5", "drive2/drive2Treble": "0.5",
               "drive2/drive2Level": "0.5", "drive1/drive1Active": "false"},
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path and path.is_file()
            and path.stat().st_nlink == 1, f"regular unaliased file required: {path}")
    return path


def read_json(path):
    return json.loads(regular(path).read_text())


def write_json(path, value):
    """Exclusive, finite JSON; flush before the next external operation."""
    payload = json.dumps(R.safe_rejected_row(value), allow_nan=False, indent=2) + "\n"
    with Path(path).open("x") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def event(path, value):
    with Path(path).open("a") as handle:
        handle.write(json.dumps(R.safe_rejected_row(value), allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def failure(error):
    record = {"type": type(error).__name__, "message": str(error)}
    if getattr(error, "processing_evidence", None):
        record["processing_evidence"] = deepcopy(error.processing_evidence)
    return record


def error_evidence(error, record):
    """Carry original failure evidence through independent fallback writes."""
    if not hasattr(error, "processing_evidence"):
        error.processing_evidence = []
    error.processing_evidence.append(deepcopy(record))


def check_time(started):
    if time.monotonic() - started >= LIMIT:
        raise TimeoutError("900 second cooperative stage budget exhausted")


def save_arrays(path, **values):
    """Persist returns BEFORE checking shape, dtype, finiteness or file hashes.

    Serialization/hash failures leave both the attempted file and an fsynced
    recovery .npy for each serializable member. No evidence file is overwritten.
    """
    import numpy as np
    path = Path(path)
    try:
        with path.open("xb") as handle:
            np.savez_compressed(handle, **values)
            handle.flush()
            os.fsync(handle.fileno())
        sha = R.sha(path)
        result = {"file": path.name, "sha256": sha,
                  "members": {k: {"shape": list(np.asarray(v).shape), "dtype": str(np.asarray(v).dtype),
                                  "sha256": digest(np.asarray(v).tobytes())} for k, v in values.items()}}
        write_json(path.with_suffix(".identity.json"), result)
        return result
    except Exception as error:
        recovery = {}
        for key, value in values.items():
            try:
                with path.with_name(path.name + "." + key + ".recovery.npy").open("xb") as handle:
                    np.save(handle, value, allow_pickle=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                recovery[key] = "saved"
            except Exception as second:
                recovery[key] = failure(second)
        record = {"archive": str(path), "original_error": failure(error), "recovery": recovery}
        try:
            write_json(path.with_suffix(".save-failure.json"), record)
        except Exception as diagnostic_error:
            record["diagnostic_error"] = failure(diagnostic_error)
            try:
                write_json(path.with_suffix(".save-fallback.json"), record)
            except Exception as fallback_error:
                record["fallback_error"] = failure(fallback_error)
        error_evidence(error, record)
        raise


def committed(name):
    path = regular(ROOT / name)
    data = path.read_bytes()
    require(data == subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT),
            "uncommitted dependency: " + name)
    return digest(data)


def guard(started):
    """Metadata only. DRAFT rejects before any binary asset is hashed/read."""
    text = regular(ROOT / PLAN).read_text()
    block = re.search(r"<!-- processing-approval\n(.*?)\nprocessing-approval -->", text, re.S)
    approval = json.loads(block[1]) if block else {}
    require("**Declared:" in text and approval.get("status") == "DECLARED"
            and approval.get("fresh_independent_review") is True and approval.get("scope") == SCOPE,
            "fresh independent review and committed declaration required")
    require(approval.get("render_di_authorization") == "prepare NPZ render_di only; float64[384000]; exact suffix di[288000]"
            and approval.get("no_asset_access_before_declaration") is True,
            "explicit new render_di authorization and declaration attestation required")
    check_time(started)
    pins = {}
    for name in SOURCE_FILES:
        check_time(started)
        pins[name] = committed(name)
    require(approval.get("source_pins") == pins, "explicit exact dependency pins required")
    design_sha = digest(T.design_bytes(text))
    require(approval.get("source_sha256") == pins[SOURCE_FILES[0]]
            and approval.get("test_sha256") == pins[SOURCE_FILES[1]]
            and approval.get("design_sha256") == design_sha, "fresh review snapshot mismatch")
    name = approval.get("review", "")
    require(re.fullmatch(r"docs/research/di-morgan-processing-[a-zA-Z0-9_-]+\.md", name)
            is not None and name not in pins, "dedicated fresh review path required")
    pins[name] = committed(name)
    require(pins[name] == approval.get("review_sha256"), "review hash mismatch")
    inputs_sha = pins["docs/di-timing-sensitivity-inputs.sha256"]
    require(approval.get("inputs_sha256") == inputs_sha, "reviewed original48 manifest required")
    review = regular(ROOT / approval["review"]).read_text()
    require("Verdict: APPROVE" in review and all(v in review for v in
            (pins[SOURCE_FILES[0]], pins[SOURCE_FILES[1]], design_sha, inputs_sha)),
            "review must attest exact source/test/frozen body/input hashes")
    pins[PLAN] = committed(PLAN)
    manifest = read_json(ROOT / "docs/di-domain-pilot-inputs.json")
    require(manifest["model"] == MODEL and manifest["average"] == AVERAGE
            and manifest["preset"] == "samples/Example_Clean_PR12.xml", "frozen fold2/template identity drift")
    T.panel(manifest["takes"])
    correction = read_json(ROOT / "docs/di-domain-pilot-v2-inputs.json")
    require(correction["schema"] == 2 and correction["tolerance"] == T.TOL
            and correction["window_family"] == "torch32" and correction["window_dtype"] == "<f4"
            and correction["original_inputs"] == "docs/di-domain-pilot-inputs.json"
            and correction["original_inputs_sha256"] == pins[correction["original_inputs"]],
            "original persisted window declaration drift")
    original = read_json(ROOT / "docs/di-morgan-flatref.json")
    verification = read_json(ROOT / "docs/di-morgan-flatref-verification.json")
    control = read_json(ROOT / "docs/di-morgan-control-verification.json")
    require(original.get("complete") is True and F.compare(original["rows"], manifest["takes"])["passed"]
            and verification.get("status") == "VERIFIED_WITH_EVIDENCE_LIMITS"
            and verification.get("failures") == [] and control.get("failures") == [],
            "verified original flatref prerequisite required")
    hashes = T.declared_hashes(manifest["takes"], original, verification)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return {"pins": pins, "revision": revision, "approval": approval, "manifest": manifest,
            "correction": correction, "original": original, "verification": verification,
            "control": control, "hashes": hashes,
            "old_inputs": read_json(ROOT / "docs/di-timing-sensitivity-inputs.json")}


def recheck(context, started):
    for name, sha in context["pins"].items():
        check_time(started)
        require(digest(regular(ROOT / name).read_bytes()) == sha, "source drift: " + name)
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            == context["revision"], "HEAD drift")
    check_time(started)


def check_inputs(context, started):
    for name, sha in context["hashes"].items():
        check_time(started)
        require(R.sha(regular(ROOT / name)) == sha, "original artifact drift: " + name)
    check_time(started)


def expected_prefix(stage):
    return V.CPU_PREFIX if stage in ("baseline", "score-clean", "score-panel") else ROOT / ".venv"


def require_environment(stage):
    require(Path(sys.prefix).resolve() == expected_prefix(stage).resolve(),
            f"{stage} requires explicit environment {expected_prefix(stage)}")


def stage_report(run, stage):
    require(not any((run / stage / name).exists() for name in
                    ("invalidated.json", "failures.jsonl"))
            and not (run / "closure-errors.jsonl").exists(), "failed prerequisite finalization: " + stage)
    if (run / "closed.json").exists():
        require(read_json(run / "closed.json").get("disposition") != "INCONCLUSIVE",
                "attempt closed with error")
    report = read_json(run / stage / "result.json")
    require(report.get("complete") is True and report.get("passed") is True
            and report.get("disposition") == "PASS", "successful prerequisite required: " + stage)
    require(R.sha(regular(run / stage / "result.json")) == read_json(run / stage / "seal.json")["result_sha256"],
            "prerequisite report drift: " + stage)
    return report


def barriers(run, stage, context):
    """Check all preceding stages and retained evidence before any stage assets."""
    require(not (run / "closed.json").exists(), "attempt closed; no rerun or rescue")
    for previous in STAGES[:STAGES.index(stage)]:
        stage_report(run, previous)
        provenance = read_json(run / previous / "provenance.json")
        require(provenance["pins"] == context["pins"] and provenance["revision"] == context["revision"]
                and provenance["input_artifacts"] == context["hashes"], "stage source/input/HEAD drift")
        seal = read_json(run / previous / "seal.json")
        actual = {str(p.relative_to(run / previous)) for p in (run / previous).rglob("*") if p.is_file()}
        require(actual == set(seal["files"]) | {"seal.json"}, "stage evidence coverage drift")
        for name, sha in seal["files"].items():
            require(R.sha(regular(run / previous / name)) == sha, "retained stage evidence drift: " + name)


def runtime():
    import numpy as np
    import scipy
    value = {"python": sys.version, "prefix": sys.prefix, "machine": platform.machine(),
             "processor": platform.processor(), "platform": platform.platform(),
             "packages": {k: R.package_version(k) for k in ("numpy", "scipy", "soundfile", "torch")},
             "thread_environment": {k: os.environ.get(k) for k in
                                    ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")},
             "shared_libraries": sorted({str(m.__file__) for m in tuple(sys.modules.values())
                                         if getattr(m, "__file__", None) and
                                         str(m.__file__).endswith((".so", ".dylib"))}),
             "numpy_config": str(np.__config__.CONFIG) if hasattr(np.__config__, "CONFIG") else "unavailable",
             "scipy_version": scipy.__version__,
             "limits": "Observed module paths/config only; no retrospective process/runtime audit."}
    if "torch" in sys.modules:
        torch = sys.modules["torch"]
        value.update(torch_threads=torch.get_num_threads(), torch_config=torch.__config__.show())
    return value


def load_original(context, started, *, model_input=False):
    """Only original five waveform members, plus net_input in CPU stages."""
    import numpy as np
    check_inputs(context, started)
    loaded, identities = T.load_inputs(context["manifest"]["takes"], context["hashes"],
                                       context["verification"], context["control"], started)
    require({"artifacts": context["hashes"], "waveforms": identities} == context["old_inputs"],
            "original waveform identities drift")
    if model_input:
        for take in context["manifest"]["takes"]:
            check_time(started)
            with np.load(T.SOURCE / "render" / (take["slug"] + ".npz"), allow_pickle=False) as saved:
                x = saved["net_input"]
            require(x.dtype == np.dtype("float64"), "original net_input float64 required")
            P._mono(x, N)
            loaded[take["slug"]]["net_input"] = x
    check_inputs(context, started)
    return loaded


def replay(out, context, loaded, windows, started):
    """All108 exact-window scalar replays; every partial/failed row is durable."""
    takes = context["manifest"]["takes"]
    previous = {r["slug"]: r for r in context["original"]["rows"]}
    rows, attempts = [], []
    try:
        for take in takes:
            item = {**T.identity(take), "valid": False}
            try:
                check_time(started)
                row = T.scored_row(take, loaded[take["slug"]], windows, previous[take["slug"]], 0, started)
                item["scores"] = {key: row[key] for key in T.ARMS.values()}
                T.validate_row(row)
                errors = {f"{arm}.{metric}": abs(row[key][metric] - previous[take["slug"]][key][metric])
                          for arm, key in T.ARMS.items() for metric in T.METRICS}
                item.update(errors=errors, valid=all(v <= T.TOL for v in errors.values()))
                rows.append(row)
            except Exception as error:
                item["error"] = failure(error)
                raise
            finally:
                attempts.append(item)
                write_json(out / f"replay-attempt-{len(attempts):02d}.json", item)
        screen = F.compare(rows, takes)
        passed = (len(attempts) == 12 and all(r["valid"] for r in attempts)
                  and screen["passed"] and T.close(screen, context["original"]["screen"]))
    finally:
        report = {"complete": len(attempts) == 12, "passed": locals().get("passed", False),
                  "scalar_count": sum(len(r.get("errors", {})) for r in attempts), "rows": attempts,
                  "screen": locals().get("screen"), "absolute_tolerance": T.TOL}
        write_json(out / "scalar-replay.json", report)
    require(report["passed"], "original all108 score/gate replay failed")
    return rows


def pinned_asset(spec, started):
    check_time(started)
    require(R.sha(regular(Path(spec["path"]))) == spec["sha256"], "pinned model/average drift")
    check_time(started)


def load_model(started):
    pinned_asset(MODEL, started)
    import torch
    from learn import direc as D
    torch.set_num_threads(2)
    net = D.build_model().cpu()
    pinned_asset(MODEL, started)
    net.load_state_dict(torch.load(MODEL["path"], map_location="cpu", weights_only=True))
    pinned_asset(MODEL, started)
    net.eval()
    require(torch.get_num_threads() == 2 and not net.training
            and all(p.device.type == "cpu" for p in net.parameters()), "original CPU eval/two threads required")
    check_time(started)
    return net


def infer(net, x, started):
    import numpy as np
    import torch
    from learn import direc as D
    check_time(started)
    # Caller persists the returned value before any after-call check.
    return D.rebuild(net, np.asarray(x, dtype="<f4"), device=torch.device("cpu"))


def validate_prediction(raw):
    import numpy as np
    require(raw.dtype == np.dtype("<f4"), "original little endian float32 prediction required")
    P._mono(raw, N)


def baseline(out, context, loaded, windows, started):
    import numpy as np
    zero = replay(out, context, loaded, windows, started)  # BEFORE model access.
    net = load_model(started)
    rows, attempts = [], []
    try:
        for take, base in zip(context["manifest"]["takes"], zero):
            slug = take["slug"]
            item = {**T.identity(take), "valid": False, "returned": False}
            try:
                raw = np.asarray(infer(net, loaded[slug]["net_input"], started))
                item["returned"] = True
                item["archive"] = save_arrays(out / (slug + ".prediction.npz"), raw_prediction=raw)
                check_time(started)
                validate_prediction(raw)
                item["byte_identical"] = raw.dtype == loaded[slug]["net"].dtype and raw.tobytes() == loaded[slug]["net"].tobytes()
                require(item["byte_identical"], "original prediction bytes differ")
                scores = P.score_prediction(raw, loaded[slug]["target"], loaded[slug]["di"], windows=windows)
                item["scores"] = scores
                item["errors"] = {k: abs(scores[k] - base["network_scores"][k]) for k in T.METRICS}
                row = {**base, "network_scores": scores, "net": scores["primary"]}
                T.validate_row(row)
                item["valid"] = all(v <= T.TOL for v in item["errors"].values())
                rows.append(row)
            except Exception as error:
                item["error"] = failure(error)
                raise
            finally:
                attempts.append(item)
                write_json(out / f"inference-attempt-{len(attempts):02d}.json", item)
        screen = F.compare(rows, context["manifest"]["takes"])
        passed = all(r["valid"] for r in attempts) and screen["passed"] and T.close(screen, context["original"]["screen"])
    finally:
        report = {"complete": len(attempts) == 12, "passed": locals().get("passed", False),
                  "scalar_count": sum(len(r.get("errors", {})) for r in attempts),
                  "rows": attempts, "screen": locals().get("screen"), "absolute_tolerance": T.TOL}
        write_json(out / "prediction-replay.json", report)
    require(report["passed"] and report["scalar_count"] == 36, "original bytes/direct36/F gate failed")
    pinned_asset(MODEL, started)
    return {"complete": True, "passed": True, "disposition": "PASS", "scalar_count": 108, "prediction_scalar_count": 36}


def command_panel(base, pack):
    """Only exact predeclared stored overrides, with unchanged order/base."""
    require(set(base) == {"selectAmp", "edits"} and type(base["selectAmp"]) is int
            and base["selectAmp"] == 1
            and pack.parameters["/selectedAmp"].members["1"] == "PR12", "original PR12 selector required")
    keys = [e["module"] + "/" + e["key"] for e in base["edits"]]
    require(len(keys) == len(set(keys)), "duplicate command parameter")
    original = dict(zip(keys, (e["value"] for e in base["edits"])))
    require(float(original["pr12Amp/pr12Volume"]) == .62
            and original["drive1/drive1Active"] == original["drive2/drive2Active"] == "false",
            "original .62 volume and both pedals off required")
    commands = {}
    for chain, overrides in OVERRIDES.items():
        command = deepcopy(base)
        for path_key, value in overrides.items():
            require(path_key in original, "override missing from full base command")
            spec = pack.parameters[path_key]
            require(spec.writable, "override must be writable")
            if path_key.endswith("Active"):
                require(spec.kind == "switch" and value in ("true", "false"), "declared switch kind required")
            else:
                require(spec.kind == "rotation" and 0 <= float(value) <= 1, "declared normalized rotation required")
                # Rotation's 0..100 human range is intrinsic in format.translate;
                # the manifest intentionally has no metered min/max for knobs.
                require(pack.to_stored(spec, 100 * float(value)) == value,
                        "stored rotation must obey declared formatter/range")
            command["edits"][keys.index(path_key)]["value"] = value
        changed = {keys[i] for i, (a, b) in enumerate(zip(base["edits"], command["edits"])) if a != b}
        require(changed <= set(overrides), "undeclared command difference")
        require(all(dict(zip(keys, (e["value"] for e in command["edits"])))[k] == v for k, v in overrides.items()),
                "exact stored overrides required")
        commands[chain] = command
    require(commands["clean"] == base, "clean must be exactly original command")
    return commands


def validate_render_di(render_di, saved_di):
    import numpy as np
    require(render_di.dtype == np.dtype("float64") and render_di.shape == (PREROLL + N,)
            and np.isfinite(render_di).all(), "finite float64 render_di[384000] required")
    require(saved_di.shape == (N,) and np.array_equal(render_di[PREROLL:], saved_di), "render_di exact saved-DI overlap required")
    # Signed-zero/IEEE-byte proof in addition to equality.
    require(render_di[PREROLL:].tobytes() == np.asarray(saved_di, dtype="float64").tobytes(), "render_di overlap bytes differ")


def load_render_di(context, loaded, started):
    import numpy as np
    check_inputs(context, started)
    result = {}
    for take in context["manifest"]["takes"]:
        check_time(started)
        with np.load(T.SOURCE / "prepare" / (take["slug"] + ".npz"), allow_pickle=False) as saved:
            x = saved["render_di"]  # First/only NEW original member access, render stages only.
        validate_render_di(x, loaded[take["slug"]]["di"])
        result[take["slug"]] = x
    check_inputs(context, started)
    return result


class ProtocolEvidence:
    """Mixin logs real protocol boundaries, including malformed/error replies."""

    def protocol_event(self, record, original_error=None):
        # Keep each event before fallible transcript I/O. Chain cleanup writes
        # this independent copy even if the transcript alone becomes unwritable.
        if not hasattr(self, "protocol_evidence"):
            self.protocol_evidence = []
        self.protocol_evidence.append(record)
        try:
            event(self.transcript, record)
        except Exception as logging_error:
            logging = {"event": "transcript-write-error", "error": failure(logging_error)}
            self.protocol_evidence.append(logging)
            if original_error is None:
                error_evidence(logging_error, {"protocol_record": record})
                raise
            error_evidence(original_error, {"protocol_record": record, "logging_error": failure(logging_error)})

    def _exchange(self, command, timeout=None):
        check_time(self.started)
        effective = min(60.0, self.reply_timeout_s if timeout is None else timeout,
                        max(.001, LIMIT - (time.monotonic() - self.started)))
        self.protocol_event({"event": "request", "command": command, "timeout": effective})
        try:
            reply = super()._exchange(command, timeout=effective)
        except Exception as error:
            self.protocol_event({"event": "exchange-error", "error": failure(error)}, original_error=error)
            raise
        self.protocol_event({"event": "exchange-return", "reply": reply})
        # Preserve any output written even when backend later rejects its WAV.
        return reply

    def _readline(self, timeout=None):
        # Read single bytes without TextIO buffering/read-ahead. Readiness alone
        # does not bound readline(): a stalled partial line must also expire.
        stream = self._process.stdout
        partial = bytearray()
        try:
            check_time(self.started)
            effective = min(60.0, self.reply_timeout_s if timeout is None else timeout,
                            max(.001, LIMIT - (time.monotonic() - self.started)))
            deadline = time.monotonic() + effective
            try:
                descriptor = stream.fileno()
            except (AttributeError, OSError, ValueError):
                require(isinstance(stream, io.StringIO), "protocol pipe descriptor required")
                partial.extend(stream.readline().encode("utf8"))  # Synthetic in-memory tests only.
            else:
                with selectors.DefaultSelector() as selector:
                    selector.register(descriptor, selectors.EVENT_READ)
                    while not partial.endswith(b"\n"):
                        remaining = deadline - time.monotonic()
                        if remaining <= 0 or not selector.select(remaining):
                            raise TimeoutError("complete protocol line deadline exhausted")
                        chunk = os.read(descriptor, 1)
                        if not chunk:
                            raise ValueError("protocol EOF before complete reply line")
                        partial.extend(chunk)
            require(partial.endswith(b"\n"), "protocol EOF before complete reply line")
            self.protocol_event({"event": "protocol-line", "raw": partial.decode("utf8"),
                                 "raw_hex": partial.hex()})
            check_time(self.started)
            require(time.monotonic() <= deadline, "complete protocol line exceeded deadline")
            return json.loads(partial)
        except Exception as error:
            # Even transcript failure must not bypass shutdown. Outer cleanup
            # retries independent evidence paths and preserves the original error.
            record = {"event": "read-error", "error": failure(error), "partial_raw_hex": partial.hex(),
                      "partial_raw": partial.decode("utf8", errors="backslashreplace")}
            error_evidence(error, {"protocol_read": record})
            self.protocol_event(record, original_error=error)
            try:
                self.close()
            except Exception:
                pass  # close errors remain on self and outer partial evidence.
            raise

    def _one_render(self, di, settings, frames):
        # Backend deletes its output in finally, even on errors. Intercept unlink
        # by implementing this small stable command boundary explicitly instead.
        out_path = self._workdir / f"render-{self._render_index}.wav"
        self._render_index += 1
        command = {"out": str(out_path), "input": str(self._di_file(di)), "amplitude": self.amplitude}
        require(self.settle_ms == 0 and self.warmup_s == 0 and not self.isolate,
                "original renderer defaults changed")
        command.update(self._state_command(settings))
        self._exchange(command, timeout=min(60., self.reply_timeout_s + 2 * frames / P.SR))
        # WAV survives decode/shape/rate errors; decoded full raw also saved first.
        return self._read_render(out_path, frames)

    def _read_render(self, path, frames):
        import numpy as np
        import soundfile as sf
        raw, rate = sf.read(str(path), dtype="float32", always_2d=True)
        save_arrays(path.with_suffix(".decoded.npz"), raw_stereo=raw, sample_rate=np.asarray(rate))
        mono = raw.astype(np.float64).mean(axis=1) if raw.ndim == 2 else raw.astype(np.float64)
        save_arrays(path.with_suffix(".decoded-mono.npz"), raw_full_mono=mono)
        check_time(self.started)
        # The Swift host pads to whole blocks. Keep that entire return above,
        # then apply the backend's original exact frame truncation.
        require(rate == P.SR and raw.ndim == 2 and raw.shape[1] == 2
                and frames <= len(raw) < frames + self.block_size
                and np.isfinite(raw).all(), "invalid full stereo render")
        return np.ascontiguousarray(raw[:frames], dtype=np.float32)

    def close(self):
        if getattr(self, "evidence_closed", False):
            return
        # Backend close sends quit directly, outside _exchange; retain that too.
        errors = []
        process = self._process
        try:
            if process is not None and process.poll() is None:
                self.protocol_event({"event": "request", "command": {"quit": True}, "reply_expected": False})
        except Exception as error:
            errors.append(error)
        try:
            super().close()  # Always attempted, even when logging failed.
            self.evidence_closed = True
        except Exception as error:
            errors.append(error)
        self.evidence_close_errors = [failure(error) for error in errors]
        try:
            self.protocol_event({"event": "closed", "backend_closed": getattr(self, "evidence_closed", False),
                                 "errors": self.evidence_close_errors})
        except Exception as error:
            errors.append(error)
            self.evidence_close_errors = [failure(e) for e in errors]
        if errors:
            raise errors[0]


def make_host(out, started):
    from match.renderer_au import AudioUnitRenderer

    class Host(ProtocolEvidence, AudioUnitRenderer):
        def _state_command(self, settings):
            return self.command

        def _render(self, di, settings):
            # Original auto-isolation behavior could retry a silent warmup.
            # A silent return closes this attempt; no hidden render rescue.
            self._ensure_server()
            raw = self._one_render(di, settings, len(di))
            self._isolate_decided = True
            require(float(abs(raw).max()) > 0, "silent render; no retry")
            return raw

    directory = out / "au-host"
    directory.mkdir(exist_ok=False)
    host = Host("morgan", process_policy="reuse", workdir=directory, reply_timeout_s=30.)
    host.started, host.transcript = started, out / "protocol.jsonl"
    return host


def full_render(host, out, label, x, started):
    import numpy as np
    check_time(started)
    returned = host.render(np.pad(x, (0, LATENCY)).astype("<f4"), {})
    raw = np.asarray(returned.audio)
    archive = save_arrays(out / (label + ".full.npz"), raw_stereo=raw)
    # Even malformed/nonfinite audio is archived before downmix/validation.
    mono = raw.astype(np.float64).mean(axis=1) if raw.ndim == 2 else raw.astype(np.float64)
    mono_archive = save_arrays(out / (label + ".mono.npz"), full_mono=mono)
    metadata = returned.metadata.as_dict()
    write_json(out / (label + ".metadata.json"), {"renderer": metadata, "stereo": archive, "mono": mono_archive})
    check_time(started)
    require(raw.dtype == np.dtype("float32") and raw.shape == (PREROLL + N + LATENCY, 2), "full stereo shape/dtype mismatch")
    require(np.isfinite(mono).all() and float(np.std(mono)) >= 1e-5, "nonfinite/silent render")
    require(metadata["sample_rate"] == P.SR and metadata["plugin_version"] not in ("unknown", "n/a", ""), "invalid plugin identity")
    return mono, metadata


def slices(full):
    import numpy as np
    require(full.shape == (PREROLL + N + LATENCY,) and np.isfinite(full).all(), "full mono length/finite mismatch")
    return full[PREROLL:PREROLL + N].copy(), full[PREROLL + LATENCY:PREROLL + LATENCY + N].copy()


def render_chain(out, chain, context, render_di, started, host_factory=make_host, expected_identity=None):
    import numpy as np
    import research.render_preset_panel as RP
    from packs.loader import load_pack
    out.mkdir(exist_ok=False)
    host = host_factory(out, started)
    rows, repeats, identity = [], {}, None
    try:
        if expected_identity is not None:
            observed = host.metadata().as_dict()  # Startup only, before warmup/experimental render.
            write_json(out / "startup-identity.json", {"expected": expected_identity, "observed": observed})
            require(observed == expected_identity, "panel host differs from sealed clean identity")
        select, edits = RP.preset_edits(ROOT / context["manifest"]["preset"], load_pack("morgan"), host, "pr12", True)
        base = {"selectAmp": select, "edits": edits}
        commands = command_panel(base, load_pack("morgan"))
        write_json(out / "commands.json", {"original_full_command": base, "commands": commands,
                                           "claim": "Command application only; no parameter readback or latency remeasurement."})
        host.command = commands[chain]
        takes = context["manifest"]["takes"]
        first_slug = takes[0]["slug"]
        _, identity = full_render(host, out, "warmup", render_di[first_slug], started)
        require(expected_identity is None or identity == expected_identity,
                "panel warmup differs from sealed clean identity")
        for index, take in enumerate(takes):
            slug = take["slug"]
            full, metadata = full_render(host, out, slug, render_di[slug], started)
            require(metadata == identity, "renderer metadata/plugin identity drift")
            x, wet = slices(full)
            evidence = save_arrays(out / (slug + ".slices.npz"), net_input=x, wet=wet)
            rows.append({**T.identity(take), "chain": chain, "slices": evidence, "renderer": metadata})
            write_json(out / f"case-{index + 1:02d}.json", rows[-1])
            if index == 0:
                first = wet
                again, meta = full_render(host, out, "first-repeat", render_di[slug], started)
                repeats["first"] = R.repeat_canary(first, slices(again)[1])
                require(meta == identity, "first repeat identity drift")
        again, meta = full_render(host, out, "end-return-repeat", render_di[first_slug], started)
        repeats["end"] = R.repeat_canary(first, slices(again)[1])
        write_json(out / "repeat-canaries.json", {"repeats": repeats, "identity_stable": meta == identity})
        require(meta == identity, "end repeat identity drift")
        check_time(started)
    finally:
        body_error = sys.exc_info()[1]
        cleanup_errors = []
        try:
            host.close()  # Retained server stderr, WAVs and transcripts survive failure.
        except Exception as error:
            cleanup_errors.append(error)
        # Independent of both transcript and partial-row paths. In-memory events
        # include original timeout/partial bytes and all logging/close failures.
        try:
            write_json(out / "protocol-fallback.json", {"events": getattr(host, "protocol_evidence", [])})
        except Exception as error:
            cleanup_errors.append(error)
        try:
            write_json(out / "partial.json", {"rows": rows, "repeats": repeats,
                       "body_error": failure(body_error) if body_error else None,
                       "cleanup_errors": [failure(e) for e in cleanup_errors],
                       "protocol_close_errors": getattr(host, "evidence_close_errors", []),
                       "protocol_evidence": getattr(host, "protocol_evidence", [])})
        except Exception as error:
            cleanup_errors.append(error)
        if cleanup_errors:
            try:
                write_json(out / "cleanup-errors.json", {"errors": [failure(e) for e in cleanup_errors]})
            except Exception:
                pass
            if body_error is None:
                raise cleanup_errors[0]
    check_time(started)
    require(len(rows) == 12, "all twelve renders required")
    return {"chain": chain, "rows": rows, "repeats": repeats, "identity": identity,
            "valid": all(r["passed"] for r in repeats.values())}


def render_stage(out, context, loaded, started, chains):
    expected = None if chains == ("clean",) else stage_report(out.parent, "render-clean")["chains"][0]["identity"]
    inputs = load_render_di(context, loaded, started)
    for slug, x in inputs.items():
        save_arrays(out / (slug + ".render-input.npz"), render_di=x, saved_di=loaded[slug]["di"])
    write_json(out / "render-di-overlap.json", {"passed": True, "case_count": 12,
               "dtype": "float64", "shape": [PREROLL + N], "suffix_start": PREROLL,
               "suffix_samples": N, "equality": "exact float64 bytes"})
    results = []
    for chain in chains:
        recheck(context, started)
        check_inputs(context, started)
        results.append(render_chain(out / chain, chain, context, inputs, started, expected_identity=expected))
        require(expected is None or results[-1]["identity"] == expected,
                "panel host differs from sealed clean identity")
    require(len({r["identity"]["plugin_version"] for r in results}) == 1
            and all(r["identity"] == results[0]["identity"] for r in results), "chain host identity drift")
    passed = all(r["valid"] for r in results)
    return {"complete": True, "passed": passed, "disposition": "PASS" if passed else "INCONCLUSIVE", "chains": results,
            "case_count": len(chains) * 12}


def load_slices(run, render_stage_name, chain, slug):
    import numpy as np
    directory = run / render_stage_name / chain
    with np.load(directory / (slug + ".mono.npz"), allow_pickle=False) as saved:
        full = saved["full_mono"]
    x, wet = slices(full)
    with np.load(directory / (slug + ".slices.npz"), allow_pickle=False) as saved:
        require(x.tobytes() == saved["net_input"].tobytes() and wet.tobytes() == saved["wet"].tobytes(), "exact full-array slicing proof failed")
    return x, wet


def compare(rows, takes, chains=EXPERIMENTS):
    """INCONCLUSIVE overrides a valid FAIL; no subset/pooled rescue."""
    screens = []
    try:
        T.panel(takes)
        expected = {(c, t["slug"]) for c in chains for t in takes}
        actual = {(r["chain"], r["slug"]): r for r in rows}
        require(len(rows) == len(expected) == len(actual) and set(actual) == expected, "complete unique chain/take coverage required")
        for chain in chains:
            subset = [actual[chain, t["slug"]] for t in takes]
            for row, take in zip(subset, takes):
                require(row.get("valid") is True and T.identity(row) == T.identity(take), "invalid chain score/identity")
                T.validate_row(row)
            screens.append({"chain": chain, "screen": F.compare(subset, takes)})
        require(all(s["screen"].get("valid") is True for s in screens), "invalid per-chain gate")
        passed = all(s["screen"]["passed"] for s in screens)
        return {"valid": True, "passed": passed, "disposition": "PASS" if passed else "FAIL", "chains": screens}
    except (ValueError, KeyError, TypeError, OverflowError) as error:
        return {"valid": False, "passed": False, "disposition": "INCONCLUSIVE", "reason": str(error), "chains": screens}


def score_stage(out, run, stage, context, loaded, windows, started, chains):
    import numpy as np
    takes = context["manifest"]["takes"]
    rendering = "render-clean" if chains == ("clean",) else "render-panel"
    # Render-panel full36 and score-clean prerequisites were sealed by barriers.
    net = load_model(started)
    predictions, waves, cases = {}, {}, []
    for chain in chains:
        for take in takes:
            slug, key = take["slug"], (chain, take["slug"])
            x, wet = load_slices(run, rendering, chain, slug)
            raw = np.asarray(infer(net, x, started))
            save_arrays(out / f"{chain}.{slug}.prediction.npz", raw_prediction=raw)
            predictions[key], waves[key] = raw, wet
            cases.append({**T.identity(take), "chain": chain})
            # NO prediction/score validity gates until ALL12/36 returns are saved.
            check_time(started)
    write_json(out / "all-predictions-saved.json", {"complete": True, "case_count": len(cases), "cases": cases})
    pinned_asset(AVERAGE, started)
    average = np.load(AVERAGE["path"], allow_pickle=False)
    pinned_asset(AVERAGE, started)
    require(average.shape == (2049,) and np.isfinite(average).all(), "invalid frozen average")
    original = {r["slug"]: r for r in context["original"]["rows"]}
    clean_rows = {} if chains == ("clean",) else {r["slug"]: r for r in stage_report(run, "score-clean")["rows"]}
    original_render = {r["slug"]: r["renderer_metadata"] for r in
                       read_json(ROOT / "docs/di-morgan-control-render.json")["rows"]}
    clean_identity = stage_report(run, "render-clean")["chains"][0]["identity"]
    require(all(c["identity"] == clean_identity for c in stage_report(run, rendering)["chains"]),
            "scored panel identity differs from sealed clean identity")
    rows, controls = [], []
    for case in cases:
        chain, slug = case["chain"], case["slug"]
        row = {**case, "valid": False}
        try:
            check_time(started)
            saved, wet, raw = loaded[slug], waves[chain, slug], predictions[chain, slug]
            row["prediction_identity"] = {"dtype": str(raw.dtype), "shape": list(raw.shape),
                                           "sha256": digest(raw.tobytes())}
            validate_prediction(raw)
            regenerated = P.canonical_target(saved["di"], average)
            flatref = P.canonical_target(wet, average)
            save_arrays(out / f"{chain}.{slug}.construction.npz", regenerated_target=regenerated, flatref=flatref)
            require(float(np.max(np.abs(regenerated - saved["target"]))) <= T.TOL, "unchanged target regeneration drift")
            if chain == "clean":
                canary = R.repeat_canary(wet, saved["wet"])
                controls.append({"slug": slug, "original_repeat_canary": canary,
                                 "original_metadata": original_render[slug], "new_metadata": clean_identity,
                                 "metadata_stable": clean_identity == original_render[slug]})
                write_json(out / (slug + ".clean-control.json"), controls[-1])
                require(canary["passed"] and controls[-1]["metadata_stable"],
                        "new clean/original canary or metadata failed; no tuning")
            row.update(qc_valid=original[slug]["qc_valid"],
                       oracle=P.score_prediction(regenerated, saved["target"], saved["di"], windows=windows)["primary"])
            for arm, values in (("wet", wet), ("net", raw), ("flatref", flatref)):
                scores = P.score_prediction(values, saved["target"], saved["di"], windows=windows)
                row[T.ARMS[arm]], row[arm] = scores, scores["primary"]
            T.validate_row(row)
            if chain != "clean":
                row["changes_from_new_clean"] = T.paired_changes(row, clean_rows[slug])
                _, clean_wet = load_slices(run, "render-clean", "clean", slug)
                row["waveform_change_diagnostic"] = {"max_abs": float(np.max(np.abs(wet-clean_wet))),
                                                      "claim": "Waveform change only; no physical nonlinearity claim."}
            row["valid"] = True
        except TimeoutError as error:
            row["error"] = failure(error)
            write_json(out / f"score-{len(rows) + 1:02d}.json", row)
            raise
        except Exception as error:
            row["error"] = failure(error)
        rows.append(R.safe_rejected_row(row))
        write_json(out / f"score-{len(rows):02d}.json", row)
        check_time(started)
    screen = compare(rows, takes, chains)
    pinned_asset(MODEL, started)
    pinned_asset(AVERAGE, started)
    return {"complete": True, "passed": screen["passed"], "disposition": screen["disposition"],
            "screen": screen, "rows": rows, "clean_controls": controls,
            "verification_status": "INITIAL", "independent_verified": False,
            "conclusion": "Pending fresh independent recomputation commissioned by main after primary completion. Morgan development coverage only; dependent DIs, no native/song/preset/product proof or training justification."}


def finish(out, result, context, started):
    """PASS exists only after timed guard, final save, hashing and runtime record."""
    result = {**result, "verification_status": "INITIAL", "independent_verified": False}
    recheck(context, started)
    check_inputs(context, started)
    write_json(out / "runtime.json", runtime())
    write_json(out / "provisional.json", result)
    check_time(started)
    # Final report is first staged under a provisional name. If saving/hashing
    # exceeds budget it is retained; no final PASS barrier can be consumed.
    write_json(out / "result.pending.json", result)
    files = {str(p.relative_to(out)): R.sha(regular(p)) for p in out.rglob("*") if p.is_file()}
    check_time(started)
    pending_sha = files.pop("result.pending.json")
    files["result.json"] = pending_sha
    write_json(out / "seal.pending.json", {"files": files, "result_sha256": pending_sha})
    check_time(started)
    (out / "seal.pending.json").rename(out / "seal.json")
    (out / "result.pending.json").rename(out / "result.json")
    # A deadline crossed during final renames invalidates the barrier explicitly.
    try:
        check_time(started)
    except TimeoutError:
        (out / "result.json").rename(out / "overbudget-result.provisional.json")
        (out / "seal.json").rename(out / "overbudget-seal.provisional.json")
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args(argv)
    started = time.monotonic()  # Includes declaration guard and finalization.
    run = args.run.absolute()
    require(run == ROOT / OUTPUT and run.resolve() == run, "only fixed exclusive run path allowed")
    out = run / args.stage
    try:
        require_environment(args.stage)
        context = guard(started)
        if args.stage == "preflight":
            run.mkdir(parents=True, exist_ok=False)
        barriers(run, args.stage, context)
        check_time(started)
        out.mkdir(exist_ok=False)
        write_json(out / "provenance.json", {"pins": context["pins"], "revision": context["revision"],
                   "input_artifacts": context["hashes"], "prefix": sys.prefix,
                   "scope": SCOPE, "stage_budget_seconds": LIMIT, "started_unix": time.time()})
        recheck(context, started)
        check_inputs(context, started)
        loaded = load_original(context, started, model_input=args.stage == "baseline")
        windows = V.load_windows(context["correction"])
        if args.stage == "preflight":
            replay(out, context, loaded, windows, started)
            result = {"complete": True, "passed": True, "disposition": "PASS", "scalar_count": 108}
        elif args.stage == "baseline":
            result = baseline(out, context, loaded, windows, started)
        elif args.stage.startswith("render-"):
            chains = ("clean",) if args.stage == "render-clean" else EXPERIMENTS
            result = render_stage(out, context, loaded, started, chains)
        else:
            chains = ("clean",) if args.stage == "score-clean" else EXPERIMENTS
            result = score_stage(out, run, args.stage, context, loaded, windows, started, chains)
        finish(out, result, context, started)
        if not result["passed"] or args.stage == "score-panel":
            write_json(run / "closed.json", {"stage": args.stage, "disposition": result["disposition"],
                                            "verification_status": "INITIAL", "independent_verified": False})
        check_time(started)
    except Exception as error:
        record = {"stage": args.stage, "disposition": "INCONCLUSIVE", "error": failure(error),
                  "elapsed_seconds": time.monotonic() - started, "verification_status": "INITIAL",
                  "independent_verified": False}
        cleanup_errors = []
        # Withdraw authority BEFORE fallible diagnostics; each path is attempted
        # independently. stage_report also rejects error markers/closed attempts.
        if out.is_dir():
            for name in ("result", "seal"):
                try:
                    if (out / (name + ".json")).exists():
                        (out / (name + ".json")).rename(out / (name + ".failed-provisional.json"))
                except Exception as second:
                    cleanup_errors.append(failure(second))
        actions = []
        if out.is_dir():
            actions += [lambda: write_json(out / "invalidated.json", record),
                        lambda: event(out / "failures.jsonl", record)]
        if run.is_dir():
            if not (run / "closed.json").exists():
                actions.append(lambda: write_json(run / "closed.json", record))
            actions.append(lambda: event(run / "closure-errors.jsonl", record))
        for action in actions:
            try:
                action()
            except Exception as second:
                cleanup_errors.append(failure(second))
        if cleanup_errors and run.is_dir():
            try:
                write_json(run / "cleanup-errors.json", {"original": record, "errors": cleanup_errors})
            except Exception:
                pass  # Total evidence-write failure cannot be guaranteed recoverable.
        raise


if __name__ == "__main__":
    main()
