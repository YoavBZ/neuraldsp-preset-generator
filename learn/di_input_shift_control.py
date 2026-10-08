"""Bounded model INPUT timing diagnostic; DRAFT until committed fresh review.

Imports read no assets and do not import Torch. Main alone declares execution.
Known finite shifts, original latency/model/scorer; no lag fitting or training.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from learn import di_timing_sensitivity as T

P, R, V, F = T.P, T.R, T.V, T.F
PLAN = ROOT / "docs/di-input-shift-control-plan.md"
OUTPUT = "tmp/di-input-shift-control-20261008"
REVIEW = "docs/research/di-input-shift-control-review-2026-10-08.md"
VERIFIER = "docs/research/di-timing-sensitivity-independent-2026-10-08.py"
ARCHIVES = {
    "result.json": "docs/di-timing-sensitivity.json",
    "provenance.json": "docs/di-timing-sensitivity-provenance.json",
    "inputs.json": "docs/di-timing-sensitivity-inputs.json",
    "baseline-replay.json": "docs/di-timing-sensitivity-baseline-replay.json",
}
VERIFICATION = "docs/di-timing-sensitivity-verification.json"
OWN_PINS = ("learn/di_input_shift_control.py", "tests/test_di_input_shift_control.py",
            "docs/di-input-shift-control-plan.md", REVIEW, VERIFIER, VERIFICATION,
            *ARCHIVES.values())
OFFSETS = (-3, -2, 0, 2, 3)
SMALL = (-3, -2, 2, 3)
SCOPE = "known-input-shift-and-truth-inverse-only"
MODEL_PATH = "/Users/yoavbz/ndsp-presets/learn/direc/models-set3/fold2.pt"
MODEL_SHA = "16b2b734b49cc1cc2d7e547d96d3bb56208007c9cae0d0e33acb1c2a1cdd042b"
CPU_PREFIX = Path("/Users/yoavbz/ndsp-presets/tools/learn-venv")


def regular(path):
    path = Path(path)
    if path.absolute() != path or path.resolve() != path or not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError(f"require regular unaliased nonlink file: {path}")
    return path


def prior_metadata(result, verified, provenance, inputs, replay, inherited, hashes, takes, verifier_sha):
    """Validate the complete archived T derivation without accessing any arrays."""
    checks = verified.get("checks", [])
    if (verified.get("status") != "VERIFIED" or verified.get("scientific_disposition") != "PASS"
            or verified.get("failures") != [] or len(checks) != 23734
            or any(c.get("passed") is not True for c in checks)
            or len(inherited) != 53 or verified.get("source_pins") != inherited
            or verified.get("verifier_sha256") != verifier_sha):
        raise ValueError("require VERIFIED PASS T prerequisite, all23734 checks and exact53 pins")
    derived = verified["derivation_payload"]
    screen = T.compare(result["rows"], takes)
    if (result.get("complete") is not True or len(result["rows"]) != 156
            or screen.get("passed") is not True or not T.close(result["screen"], screen)
            or not T.close(result["rows"], verified["independent_rows"])
            or not T.close(result["screen"], verified["independent_screen"])
            or not T.close(result["rows"], derived["rows"])
            or not T.close(result["screen"], derived["screen"])
            or not T.close(replay, derived["baseline"])
            or not T.close(replay, verified["independent_baseline_replay"])
            or replay.get("complete") is not True or replay.get("passed") is not True
            or replay.get("scalar_count") != 108 or replay.get("absolute_tolerance") != T.TOL
            or not T.coverage(replay["rows"], takes)
            or any(r.get("valid") is not True or len(r["errors"]) != 9
                   or any(not T.loss(v) or v > T.TOL for v in r["errors"].values()) for r in replay["rows"])):
        raise ValueError("complete T156 rows/screens/108 replay differ from independent derivation")
    if (provenance.get("pins") != inherited or provenance.get("input_artifacts") != hashes
            or result.get("input_artifacts") != hashes or verified.get("input_artifacts") != hashes
            or inputs != verified.get("inputs") or inputs.get("artifacts") != hashes):
        raise ValueError("T source/artifact/input identities changed")


def prior_reports(verified, started):
    """Exact snapshot allowlist; compare original reports to committed archives."""
    names = [str(Path(T.OUTPUT) / n) for n in (*ARCHIVES, "progress.jsonl")]
    names.append(T.OUTPUT + ".log")
    snapshots = verified["primary_artifact_snapshots"]
    if set(snapshots) != set(names):
        raise ValueError("unexpected T primary report snapshot coverage")
    blobs = {}
    for name in names:
        R.check_time(started)
        data = regular(ROOT / name).read_bytes()
        if T.digest(data) != snapshots[name]["sha256"] or len(data) != snapshots[name]["size"]:
            raise ValueError(f"T primary report snapshot changed: {name}")
        base = Path(name).name
        if base in ARCHIVES and data != (ROOT / ARCHIVES[base]).read_bytes():
            raise ValueError(f"T original/archive report bytes differ: {base}")
        blobs[name] = data
    rows = T.read_json(ROOT / ARCHIVES["result.json"])["rows"]
    for name in (str(Path(T.OUTPUT) / "progress.jsonl"), T.OUTPUT + ".log"):
        if [json.loads(line) for line in blobs[name].splitlines()] != rows:
            raise ValueError("T retained progress/stdout rows differ")
    R.check_time(started)


def guard(started):
    text = PLAN.read_text()
    match = re.search(r"<!-- input-shift-approval\n(.*?)\ninput-shift-approval -->", text, re.S)
    approval = json.loads(match[1]) if match else {}
    if ("**Declared:" not in text or approval.get("status") != "DECLARED"
            or approval.get("fresh_independent_review") is not True or approval.get("scope") != SCOPE):
        raise ValueError("requires fresh independent review and committed declaration")
    R.check_time(started)
    context = T.guard()  # Unchanged inherited declarations, prerequisites and exact48 manifest.
    correction, manifest, inherited, revision, original, verification, control, hashes = context
    R.check_time(started)
    if len(inherited) != 53 or set(inherited) & set(OWN_PINS) or len(set(OWN_PINS)) != len(OWN_PINS):
        raise ValueError("require53 inherited pins disjoint from own pins")
    pins = dict(inherited)
    for name in OWN_PINS:
        R.check_time(started)
        data = regular(ROOT / name).read_bytes()
        if data != T.subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT):
            raise ValueError(f"uncommitted input-shift dependency: {name}")
        pins[name] = T.digest(data)
    expected = {"review_sha256": pins[REVIEW], "source_sha256": pins[OWN_PINS[0]],
                "test_sha256": pins[OWN_PINS[1]], "design_sha256": T.digest(T.design_bytes(text)),
                "inputs_sha256": inherited["docs/di-timing-sensitivity-inputs.sha256"]}
    if any(approval.get(k) != v for k, v in expected.items()):
        raise ValueError("fresh review does not identify exact source/test/design/input snapshot")
    if "Verdict: APPROVE" not in (ROOT / REVIEW).read_text():
        raise ValueError("fresh independent review approval required")
    reports = {n: T.read_json(ROOT / a) for n, a in ARCHIVES.items()}
    verified = T.read_json(ROOT / VERIFICATION)
    prior_metadata(reports["result.json"], verified, reports["provenance.json"],
                   reports["inputs.json"], reports["baseline-replay.json"], inherited, hashes,
                   manifest["takes"], pins[VERIFIER])
    prior_reports(verified, started)
    if manifest["model"] != {"path": MODEL_PATH, "sha256": MODEL_SHA}:
        raise ValueError("only original fold2 model identity is allowed")
    recheck_sources(pins, revision, started)
    return (*context[:2], pins, revision, original, verification, control, hashes, reports["inputs.json"])


def recheck_sources(pins, revision, started):
    for name in pins:
        R.check_time(started)
        regular(ROOT / name)
    T.recheck_sources(pins, revision, started)
    R.check_time(started)


def check_artifacts(hashes, started):
    inodes = set()
    for name in hashes:
        R.check_time(started)
        stat = regular(ROOT / name).stat()
        inode = (stat.st_dev, stat.st_ino)
        if inode in inodes:
            raise ValueError("aliased artifact identity")
        inodes.add(inode)
    T.check_artifacts(hashes, started)
    R.check_time(started)


def check_model(manifest, started):
    R.check_time(started)
    if manifest["model"] != {"path": MODEL_PATH, "sha256": MODEL_SHA}:
        raise ValueError("only original fold2 model identity is allowed")
    path = regular(Path(MODEL_PATH))
    if R.sha(path) != MODEL_SHA:
        raise ValueError("original model hash drift")
    R.check_time(started)
    return dict(manifest["model"])


def array_identity(x):
    return {"dtype": str(x.dtype), "samples": len(x), "sha256": T.digest(x.tobytes())}


def load_inputs(takes, hashes, verification, control, old_inputs, started):
    import numpy as np

    check_artifacts(hashes, started)
    loaded, identities = T.load_inputs(takes, hashes, verification, control, started)
    if {"artifacts": hashes, "waveforms": identities} != old_inputs:
        raise ValueError("original five-member T input identities drift")
    for take in takes:
        slug = take["slug"]
        path = T.SOURCE / "render" / f"{slug}.npz"
        subset = {str(path.relative_to(ROOT)): hashes[str(path.relative_to(ROOT))]}
        check_artifacts(subset, started)
        with np.load(path, allow_pickle=False) as saved:
            x = saved["net_input"]  # Sole additional allowed member; original dtype and level.
        check_artifacts(subset, started)
        P._mono(x, P.SCORE)
        std = float(np.std(x))
        if x.dtype.kind != "f" or not T.loss(std) or std <= 0:
            raise ValueError("net_input must be finite active floating mono six seconds")
        wet = loaded[slug]["wet"]
        if x.dtype != wet.dtype or x[52:].tobytes() != wet[:-52].tobytes():
            raise ValueError("original52 net_input/baseline exact overlap/dtype mismatch")
        x.flags.writeable = False
        loaded[slug]["net_input"] = x
        identities[slug]["net_input"] = array_identity(x)
    check_artifacts(hashes, started)
    return loaded, identities


def load_model(manifest, started):
    check_model(manifest, started)  # Declaration/prefix and108 replay have already passed.
    import torch
    from learn import direc as D

    torch.set_num_threads(2)
    net = D.build_model().cpu()
    check_model(manifest, started)  # Immediately before torch.load, no interpreter switching.
    net.load_state_dict(torch.load(MODEL_PATH, map_location="cpu", weights_only=True))
    net.eval()
    R.check_time(started)
    if torch.get_num_threads() != 2 or net.training or any(p.device.type != "cpu" for p in net.parameters()):
        raise ValueError("require CPU eval and original two Torch threads")
    return net


def infer(net, x, started):
    """Shift is applied by the caller to the FULL raw-level input before rebuild."""
    import numpy as np
    import torch
    from learn import direc as D

    R.check_time(started)
    prediction = D.rebuild(net, np.asarray(x, dtype="<f4"), device=torch.device("cpu"))
    # Caller saves returned evidence before the after-call budget/validity check.
    return prediction


def prediction_evidence(out, take, offset, x, raw, original, started):
    """Save even malformed/nonfinite/byte-mismatching returned predictions."""
    import numpy as np

    raw = np.asarray(raw)
    corrected = None
    error = None
    try:
        # P._mono inside the unchanged T helper promotes to float64. Convert the
        # known inverse back explicitly: finite float32 samples survive exactly.
        corrected = raw.copy() if offset == 0 else T.finite_shift(raw, -offset).astype("<f4")
    except Exception as caught:
        error = caught
    path = out / f"{take['slug']}.offset-{offset:+d}.npz"
    values = {"raw_prediction": raw, "offset": np.int64(offset)}
    if corrected is not None:
        values["corrected_prediction"] = corrected
    with path.open("xb") as handle:
        np.savez_compressed(handle, **values)
    evidence = {"prediction_file": path.name, "prediction_file_sha256": R.sha(path),
                "imposed_offset": offset, "inverse_offset": -offset,
                "input": array_identity(x), "input_sha256_float32": T.wave_hash(x, "<f4"),
                "original_prediction_sha256_float32": T.wave_hash(original, "<f4"),
                "raw_prediction_dtype": str(raw.dtype), "raw_prediction_sha256": T.digest(raw.tobytes()),
                "corrected_prediction_sha256": None if corrected is None else T.digest(corrected.tobytes())}
    # Return evidence before validation: callers retain it even when checks fail.
    return raw, corrected, evidence, error


def validate_prediction(raw, corrected, error):
    import numpy as np

    if error is not None:
        raise error
    if raw.dtype != np.dtype("<f4") or corrected.dtype != np.dtype("<f4"):
        raise ValueError("original little-endian float32 prediction required")
    P._mono(raw, P.SCORE)
    P._mono(corrected, P.SCORE)


def score_row(take, saved, corrected, base, offset, windows, started):
    row = deepcopy(base)
    row.update(T.identity(take), offset=offset)
    R.check_time(started)
    row["network_scores"] = P.score_prediction(corrected, saved["target"], saved["di"], windows=windows)
    row["net"] = row["network_scores"]["primary"]
    R.check_time(started)
    return row


def baseline_inference(out, takes, loaded, windows, zero, net, started, original):
    rows, evidence, predictions, scalar_count = [], [], {}, 0
    archived = {r["slug"]: r for r in original["rows"]}
    for take, base in zip(takes, zero):
        item = {**T.identity(take), "offset": 0, "valid": False}
        saved = loaded[take["slug"]]
        try:
            raw = infer(net, saved["net_input"], started)
            raw, corrected, details, error = prediction_evidence(
                out, take, 0, saved["net_input"], raw, saved["net"], started)
            item.update(details)
            R.check_time(started)
            validate_prediction(raw, corrected, error)
            item["byte_identical"] = (raw.dtype == saved["net"].dtype
                                      and raw.tobytes() == saved["net"].tobytes())
            row = score_row(take, saved, corrected, base, 0, windows, started)
            errors = {m: abs(row["network_scores"][m]-archived[take["slug"]]["network_scores"][m])
                      for m in T.METRICS}
            scalar_count += len(errors)
            item.update(scores=row["network_scores"], errors=errors)
            T.validate_row(row)
            item["valid"] = item["byte_identical"] and all(v <= T.TOL for v in errors.values())
            row["valid"] = item["valid"]
            rows.append(row)
            predictions[take["slug"]] = (raw, corrected, details)
        except TimeoutError as error:
            item["error"] = failure(error)
            evidence.append(R.safe_rejected_row(item))
            write_baseline(out, takes, evidence, rows, scalar_count, complete=False)
            raise
        except Exception as error:
            item["error"] = failure(error)
        evidence.append(R.safe_rejected_row(item))
        R.progress(out, {"stage": "baseline-inference", **evidence[-1]})
    report = write_baseline(out, takes, evidence, rows, scalar_count, complete=True)
    if not report["passed"]:
        raise ValueError("complete12 original prediction byte/36-score/zero gate replay failed; all shifted inference blocked")
    return rows, predictions


def write_baseline(out, takes, evidence, rows, scalar_count, *, complete):
    screen = F.compare(rows, takes)
    passed = (complete and T.coverage(evidence, takes) and len(rows) == 12 and scalar_count == 36
              and all(r.get("valid") is True for r in evidence) and screen.get("passed") is True)
    report = {"complete": complete, "passed": passed, "scalar_count": scalar_count,
              "absolute_tolerance": T.TOL, "rows": evidence, "screen": screen}
    R.write_new(out / "baseline-inference-replay.json", report)
    return report


def compare(rows, takes):
    screens = []
    def invalid(reason):
        return {"valid": False, "passed": False, "disposition": "INCONCLUSIVE",
                "reason": reason, "offset_screens": screens}
    try:
        T.panel(takes)
        expected = {(offset, t["slug"]) for offset in OFFSETS for t in takes}
        actual = {(r["offset"], r["slug"]): r for r in rows}
        coverage = len(rows) == 60 and len(actual) == 60 and actual.keys() == expected
        for offset in OFFSETS:
            try:
                subset = [actual[offset, t["slug"]] for t in takes]
                for r, t in zip(subset, takes):
                    if type(r["offset"]) is not int or T.identity(r) != T.identity(t) or r.get("valid") is not True:
                        raise ValueError("invalid case identity/error")
                    T.validate_row(r)
                screen = F.compare(subset, takes)
            except (KeyError, TypeError, ValueError, OverflowError):
                screen = {"valid": False, "passed": False, "disposition": "INCONCLUSIVE"}
            screens.append({"offset": offset, "role": "prerequisite" if offset == 0 else "robustness", "screen": screen})
        if not coverage or any(s["screen"].get("valid") is not True for s in screens):
            return invalid("require all60 unique valid cases and five valid screens")
        if next(s["screen"] for s in screens if s["offset"] == 0).get("passed") is not True:
            return invalid("zero PASS prerequisite failed")
        passed = all(s["screen"]["passed"] for s in screens)
        return {"valid": True, "passed": passed, "disposition": "PASS" if passed else "FAIL",
                "offset_screens": screens, "required_small_offsets": list(SMALL)}
    except (KeyError, TypeError, ValueError, OverflowError):
        return invalid("invalid coverage/score/QC/oracle")


def output_directory(requested):
    expected = ROOT / OUTPUT
    if requested.absolute() != expected or expected.resolve() != expected:
        raise ValueError(f"only declared --out {OUTPUT} is allowed; no aliases")
    expected.mkdir(parents=True, exist_ok=False)
    return expected


def failure(error):
    return {"type": type(error).__name__, "message": str(error)}


def stability(manifest, pins, revision, hashes, started):
    recheck_sources(pins, revision, started)
    check_artifacts(hashes, started)
    check_model(manifest, started)


def run(out, context, started):
    correction, manifest, pins, revision, original, verification, control, hashes, old_inputs = context
    takes = manifest["takes"]
    R.write_new(out / "provenance.json", {"pins": pins, "git_revision": revision,
        "input_artifacts": hashes, "python": sys.version, "prefix": sys.prefix,
        "started_unix": time.time(), "budget_seconds": R.LIMIT, "scope": SCOPE,
        "offsets": list(OFFSETS), "attribution": manifest["attribution"], "thread_count": 2,
        "model": manifest["model"], "packages": {n: R.package_version(n) for n in ("numpy", "scipy", "torch")}})
    stability(manifest, pins, revision, hashes, started)
    windows = V.load_windows(correction)
    R.check_time(started)
    loaded, identities = load_inputs(takes, hashes, verification, control, old_inputs, started)
    R.write_new(out / "inputs.json", {"artifacts": hashes, "waveforms": identities})
    zero = T.replay(out, takes, loaded, windows, original, started)  # Complete108 PASS saved before any model inference.
    stability(manifest, pins, revision, hashes, started)
    net = load_model(manifest, started)
    zero, predictions = baseline_inference(out, takes, loaded, windows, zero, net, started, original)
    # Complete12 exact prediction/36 score PASS is now durable. No shifted call before this.
    stability(manifest, pins, revision, hashes, started)
    prior = {r["slug"]: r for r in zero}
    rows = []
    for offset in OFFSETS:
        for take in takes:
            R.check_time(started)
            saved, base = loaded[take["slug"]], prior[take["slug"]]
            source_path = str((T.SOURCE / "infer" / f"{take['slug']}.npz").relative_to(ROOT))
            row = {**T.identity(take), "offset": offset, "valid": False,
                   "qc_valid": base["qc_valid"], "oracle": base["oracle"],
                   "wet": base["wet"], "input_scores": deepcopy(base["input_scores"]),
                   "flatref": base["flatref"], "flatref_scores": deepcopy(base["flatref_scores"]),
                   "imposed_offset": offset, "inverse_offset": -offset,
                   "network_scores": None, "net": None, "changes_from_zero": None}
            try:
                if offset == 0:
                    raw, corrected, details = predictions[take["slug"]]
                    row = deepcopy(base)  # Reuse both prediction AND scores; no zero rescore.
                    row.update(details)
                else:
                    x = T.finite_shift(saved["net_input"], offset).astype(saved["net_input"].dtype)
                    row.update(input=array_identity(x), input_sha256_float32=T.wave_hash(x, "<f4"))
                    raw = infer(net, x, started)
                    raw, corrected, details, error = prediction_evidence(
                        out, take, offset, x, raw, saved["net"], started)
                    row.update(details)
                    R.check_time(started)
                    validate_prediction(raw, corrected, error)
                    scored = score_row(take, saved, corrected, base, offset, windows, started)
                    row.update(scored)
                T.validate_row(row)
                row.update(valid=True, changes_from_zero=T.paired_changes(row, base))
            except TimeoutError:
                raise
            except Exception as error:
                row.update(valid=False, error=failure(error))
                row = R.safe_rejected_row(row)
            row.update(original_prediction_file=source_path, original_prediction_file_sha256=hashes[source_path])
            rows.append(row)
            R.progress(out, {"stage": "cases", **row})
            R.check_time(started)
    screen = compare(rows, takes)
    try:
        stability(manifest, pins, revision, hashes, started)
    except Exception as error:
        screen.update(valid=False, passed=False, disposition="INCONCLUSIVE", stability_error=failure(error))
        R.write_new(out / "result.json", result(rows, screen, hashes, manifest, started))
        raise
    R.check_time(started)
    R.write_new(out / "result.json", result(rows, screen, hashes, manifest, started))


def result(rows, screen, hashes, manifest, started):
    return {"complete": len(rows) == 60, "rows": rows, "screen": screen, "input_artifacts": hashes,
            "elapsed_seconds": time.monotonic()-started, "attribution": manifest["attribution"],
            "interpretation": "Known input shifts with known inverse; finite padding/window normalization included. Dependent clean Morgan controls; no isolated stride cause, native or song product claim."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if sys.prefix != str(CPU_PREFIX) or Path(sys.prefix).resolve() != CPU_PREFIX or sys.byteorder != "little":
        raise ValueError(f"requires explicit original CPU interpreter prefix {CPU_PREFIX}")
    started = time.monotonic()  # Includes declaration, all hashing, load, model, scoring.
    context = guard(started)
    R.check_time(started)
    out = output_directory(args.out)
    try:
        run(out, context, started)
    except Exception as error:
        R.write_new(out / "failure.json", {**failure(error), "disposition": "INCONCLUSIVE",
                                          "elapsed_seconds": time.monotonic()-started})
        raise


if __name__ == "__main__":
    main()
