"""Fixed periodic phase challenge; DRAFT, execution only after reviewed commit.

Import reads no assets and imports no Torch. No fitting, training or rendering.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from learn import di_input_shift_control as U

T, P, R, V, F = U.T, U.P, U.R, U.V, U.F
PLAN = ROOT / "docs/di-phase-control-plan.md"
OUTPUT = "tmp/di-phase-control-20261008"
REVIEW = "docs/research/di-phase-control-review-2026-10-08.md"
VERIFIER = "docs/research/di-input-shift-control-independent-2026-10-08.py"
VERIFICATION = "docs/di-input-shift-control-verification.json.gz"
ARCHIVE = "docs/di-input-shift-control-verification-archive.json"
ARCHIVES = {name: "docs/di-input-shift-control-" + name for name in
            ("provenance.json", "inputs.json", "baseline-replay.json", "baseline-inference-replay.json")}
ARCHIVES["result.json"] = "docs/di-input-shift-control.json"
OWN_PINS = ("learn/di_phase_control.py", "tests/test_di_phase_control.py",
            "docs/di-phase-control-plan.md", REVIEW, VERIFIER, VERIFICATION, ARCHIVE,
            "docs/research/di-input-shift-control-verification-2026-10-08.md",
            "docs/di-input-shift-control-results.md", *ARCHIVES.values())
SCOPE = "fixed-periodic-phase-only-a-minus-0.9"
A = -0.9  # Chosen before study numerics; never swept or fitted.
N = 288000
CONFIG = {"a": A, "samples": N, "sample_rate": 48000,
          "formula": "(a+exp(-j*2*pi*k/N))/(1+a*exp(-j*2*pi*k/N))",
          "dc": 1.0, "nyquist": -1.0, "boundary": "periodic",
          "transform_dtype": "float64", "model_input_dtype": "<f4",
          "renderer_latency_samples": 52, "inverse_prediction": False,
          "control_tolerance": 1e-12, "quantized_inverse_tolerance": 1e-6}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def valid_sha(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def prior_metadata(reports, verified, archive, inherited, hashes, takes, verifier_sha):
    """Small scientific checks; pinned reports carry the remaining old metadata.

    Content references are inspected as metadata only, never followed/decoded.
    No recursive comparison of the inherited thousands of scalar fields.
    """
    require(verified.get("status") == "VERIFIED" and verified.get("scientific_disposition") == "PASS"
            and verified.get("failures") == [] and len(verified.get("checks", [])) == 21246
            and all(c.get("passed") is True for c in verified["checks"]), "prior verification must be VERIFIED PASS")
    require(verified.get("source_pins") == inherited and len(inherited) == 63
            and verified.get("input_artifacts") == hashes and verified.get("verifier_sha256") == verifier_sha,
            "prior exact63 sources/48 artifacts/verifier differ")
    require(archive.get("status") == "VERIFIED" and archive.get("scientific_disposition") == "PASS"
            and archive.get("final_comparison_checks") == 21246 and archive.get("final_failures") == 0
            and archive.get("payload_references") == 120 and archive.get("lossless_decompression_verified") is True
            and archive.get("verifier_sha256") == verifier_sha
            and archive.get("original_sha256") == verified["archive_storage_note"]["full_report_sha256"],
            "prior compact archive attestation differs")
    result = reports["result.json"]
    screen = U.compare(result["rows"], takes)
    independent = U.compare(verified["independent_rows"], takes)
    require(result.get("complete") is True and screen.get("passed") is True
            and independent.get("passed") is True and T.close(screen, result["screen"])
            and T.close(screen, independent) and T.close(independent, verified["independent_screen"]),
            "prior all60 coverage/five PASS screens required")
    independent_rows = {(r["offset"], r["slug"]): r for r in verified["independent_rows"]}
    for row in result["rows"]:
        require(row["prediction_file"] == f"{row['slug']}.offset-{row['offset']:+d}.npz",
                "prior exact prediction filename required")
        other = independent_rows[row["offset"], row["slug"]]
        require(all(abs(row[key][metric] - other[key][metric]) <= T.TOL
                    for key in T.ARMS.values() for metric in T.METRICS), "prior independent arm scores differ")
    require(reports["provenance.json"].get("pins") == inherited
            and reports["provenance.json"].get("input_artifacts") == hashes
            and result.get("input_artifacts") == hashes
            and reports["inputs.json"] == verified.get("inputs")
            and reports["inputs.json"].get("artifacts") == hashes, "prior input/provenance drift")
    for name, count in (("baseline-replay.json", 108), ("baseline-inference-replay.json", 36)):
        replay = reports[name]
        require(replay.get("complete") is True and replay.get("passed") is True
                and replay.get("scalar_count") == count and replay.get("absolute_tolerance") == T.TOL
                and T.coverage(replay.get("rows", []), takes) and replay["screen"].get("passed") is True,
                "prior complete replay barrier missing")
        for row in replay["rows"]:
            require(row.get("valid") is True and len(row["errors"]) == count // 12
                    and all(T.loss(v) and v <= T.TOL for v in row["errors"].values()), "prior replay invalid")
            if count == 36:
                require(row.get("byte_identical") is True
                        and row["raw_prediction_sha256"] == row["original_prediction_sha256_float32"]
                        and valid_sha(row["raw_prediction_sha256"]), "prior original prediction bytes differ")
    independent_baseline = verified["independent_baseline_inference_replay"]
    require(independent_baseline.get("passed") is True and independent_baseline.get("complete") is True
            and independent_baseline.get("scalar_count") == 36
            and T.coverage(independent_baseline.get("rows", []), takes), "prior independent original12 replay required")
    for primary, other in zip(reports["baseline-inference-replay.json"]["rows"], independent_baseline["rows"]):
        zero = next(r for r in result["rows"] if r["offset"] == 0 and r["slug"] == primary["slug"])
        require(other.get("byte_identical") is True
                and other.get("raw_prediction_sha256") == primary["raw_prediction_sha256"]
                == zero["raw_prediction_sha256"] == zero["corrected_prediction_sha256"],
                "prior independent original prediction bytes differ")
    rows = {r["prediction_file"]: r for r in result["rows"]}
    require(len(rows) == 60, "prior prediction filenames duplicate")
    checks = verified.get("prediction_byte_checks", [])
    require(len(checks) == 120 and {(c["file"], c["member"]) for c in checks}
            == {(f, m) for f in rows for m in ("raw", "corrected")}, "prior all120 member-byte coverage required")
    refs = verified["independent_prediction_archives"]
    require(set(refs) == set(rows), "prior all60 archive identities required")
    for c in checks:
        row, ref = rows[c["file"]], refs[c["file"]]
        sha = row[c["member"] + "_prediction_sha256"]
        identity = ref[c["member"] + "_identity"]
        require(c.get("byte_identical") is True and c["independent_sha256"] == c["primary_sha256"] == sha
                and valid_sha(sha) and c["dtype"] == "<f4" and c["samples"] == N
                and identity == {"dtype": "float32", "samples": N, "sha256": sha}, "prior member bytes differ")
        pointer = ref["npz_base64"]
        require(type(pointer) is dict and pointer.get("storage") == "full local JSON at original JSON pointer"
                and pointer.get("json_pointer") == "/independent_prediction_archives/" + c["file"] + "/npz_base64"
                and pointer.get("decoded_npz_sha256") == ref["npz_sha256"] == row["prediction_file_sha256"]
                and valid_sha(ref["npz_sha256"]) and valid_sha(pointer.get("base64_utf8_sha256")),
                "prior compact content reference differs")


def prior_reports(reports, verified, started):
    """Hash only prior report metadata; never open prior prediction NPZ payloads."""
    names = {str(Path(U.OUTPUT) / n) for n in ARCHIVES}
    names.update((str(Path(U.OUTPUT) / "progress.jsonl"), U.OUTPUT + ".log"))
    arrays = {str(Path(U.OUTPUT) / r["prediction_file"]) for r in reports["result.json"]["rows"]}
    snapshots = verified["primary_artifact_snapshots"]
    require(set(snapshots) == names | arrays and len(snapshots) == 67, "prior exact67 snapshots required")
    for row in reports["result.json"]["rows"]:
        require(snapshots[str(Path(U.OUTPUT) / row["prediction_file"])]["sha256"]
                == row["prediction_file_sha256"], "prior archive snapshot hash differs")
    for name in names:
        R.check_time(started)
        data = U.regular(ROOT / name).read_bytes()
        require(T.digest(data) == snapshots[name]["sha256"] and len(data) == snapshots[name]["size"],
                "prior primary metadata snapshot drift")
        if Path(name).name in ARCHIVES:
            require(data == U.regular(ROOT / ARCHIVES[Path(name).name]).read_bytes(), "prior original/archive metadata differ")


def guard(started):
    text = U.regular(PLAN).read_text()
    match = re.search(r"<!-- phase-approval\n(.*?)\nphase-approval -->", text, re.S)
    approval = json.loads(match[1]) if match else {}
    require("**Declared:" in text and approval.get("status") == "DECLARED"
            and approval.get("fresh_independent_review") is True and approval.get("scope") == SCOPE,
            "requires fresh independent review and committed declaration")
    R.check_time(started)
    context = U.guard(started)  # Exactly unchanged63 inherited pins; metadata only.
    correction, manifest, inherited, revision, original, verification, control, hashes, old_inputs = context
    require(len(inherited) == 63 and not set(inherited) & set(OWN_PINS)
            and len(set(OWN_PINS)) == len(OWN_PINS), "require63 inherited disjoint source pins")
    pins = dict(inherited)
    for name in OWN_PINS:
        R.check_time(started)
        data = U.regular(ROOT / name).read_bytes()
        require(data == T.subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT),
                "uncommitted phase dependency: " + name)
        pins[name] = T.digest(data)
    expected = {"source_sha256": pins[OWN_PINS[0]], "test_sha256": pins[OWN_PINS[1]],
                "review_sha256": pins[REVIEW], "design_sha256": T.digest(T.design_bytes(text)),
                "inputs_sha256": pins["docs/di-timing-sensitivity-inputs.sha256"]}
    require(all(approval.get(k) == v for k, v in expected.items())
            and "Verdict: APPROVE" in (ROOT / REVIEW).read_text(), "fresh review exact snapshot required")
    archive = T.read_json(ROOT / ARCHIVE)
    compressed = U.regular(ROOT / VERIFICATION).read_bytes()
    require(archive.get("tracked_report") == VERIFICATION
            and T.digest(compressed) == archive["tracked_gzip_sha256"]
            and len(compressed) == archive["tracked_gzip_size"], "compact compressed identity drift")
    payload = gzip.decompress(compressed)  # Contains metadata references, no decoding/following them.
    require(T.digest(payload) == archive["tracked_uncompressed_sha256"]
            and len(payload) == archive["tracked_uncompressed_size"], "compact uncompressed identity drift")
    verified = json.loads(payload)
    reports = {n: T.read_json(ROOT / name) for n, name in ARCHIVES.items()}
    prior_metadata(reports, verified, archive, inherited, hashes, manifest["takes"], pins[VERIFIER])
    prior_reports(reports, verified, started)
    require(R.LIMIT == 900 and reports["provenance.json"].get("prefix") == str(U.CPU_PREFIX)
            and reports["provenance.json"].get("thread_count") == 2
            and reports["provenance.json"].get("model") == manifest["model"]
            and reports["provenance.json"].get("packages")
            == {n: R.package_version(n) for n in ("numpy", "scipy", "torch")},
            "original CPU environment/model/two threads/900s budget required")
    U.recheck_sources(pins, revision, started)
    return correction, manifest, pins, revision, original, verification, control, hashes, old_inputs, reports["inputs.json"]


def coefficients():
    import numpy as np
    z = np.exp(-2j * np.pi * np.arange(N // 2 + 1, dtype=np.float64) / N)
    h = (A + z) / (1 + A * z)
    h[0], h[-1] = complex(1, 0), complex(-1, 0)
    return h


def transform(x, h):
    """Real finite periodic rFFT transform of the complete original six seconds."""
    import numpy as np
    x = np.asarray(x, dtype=np.float64)
    require(x.shape == (N,) and np.asarray(h).shape == (N // 2 + 1,), "phase shape mismatch")
    # Exact identity oracle, including float32 signed zero; not used by fixed H.
    if np.array_equal(h, np.ones(N // 2 + 1)):
        return x.copy()
    return np.fft.irfft(np.fft.rfft(x) * h, n=N)


def relative_error(actual, expected):
    import numpy as np
    denominator = float(np.linalg.norm(expected))
    require(T.loss(denominator) and denominator > 0, "finite positive normalization denominator required")
    value = float(np.linalg.norm(np.asarray(actual) - expected) / denominator)
    require(T.loss(value), "nonfinite relative error")
    return {"relative_l2": value, "denominator": denominator}


def construction(saved, h):
    """Use model-converted raw level before D.rebuild's own normalization.

    The inverse uses an independent time-domain periodic recurrence, not FFTs.
    Returned arrays are retained even if the subsequent control checks fail.
    """
    import numpy as np
    x = np.asarray(saved["net_input"], dtype="<f4").astype(np.float64)
    forward = transform(x, h)
    quantized = forward.astype("<f4")
    inverse = inverse_periodic(forward)
    inverse_quantized = inverse_periodic(quantized.astype(np.float64))
    return {"model_converted_input": x, "forward_float64": forward,
            "phase_input": quantized, "inverse_float64": inverse,
            "inverse_quantized_float64": inverse_quantized,
            "phase_wet": transform(saved["wet"], h), "phase_flatref": transform(saved["flatref"], h)}


def inverse_periodic(x):
    """Conjugate allpass via time reversal and a periodic direct-form recurrence.

    z[n+1] = (1-a*a)*x[n] - a*z[n]. Solve z[N]=z[0] from
    a zero-state pass, then filter with that periodic initial state. Reversing
    both ends implements the inverse on the finite periodic domain. No FFT.
    """
    import numpy as np
    from scipy.signal import lfilter
    x = np.asarray(x, dtype=np.float64)
    require(x.shape == (N,), "inverse shape mismatch")
    reverse = x[::-1]
    _, final = lfilter([A, 1.0], [1.0, A], reverse, zi=[0.0])
    initial = final / (1.0 - (-A)**N)
    restored, _ = lfilter([A, 1.0], [1.0, A], reverse, zi=initial)
    return restored[::-1].copy()


def replay(out, takes, loaded, windows, original, started):
    """Unchanged T scoring/gate with phase-owned durable replay evidence."""
    rows, evidence, count = [], [], 0
    previous = {r["slug"]: r for r in original["rows"]}

    def persist(complete):
        screen = F.compare(rows, takes)
        passed = (complete and T.coverage(evidence, takes) and count == 108
                  and all(r.get("valid") is True for r in evidence)
                  and all(v <= T.TOL for r in evidence for v in r["errors"].values())
                  and screen.get("passed") is True and T.close(screen, original["screen"]))
        report = {"complete": complete, "passed": passed, "scalar_count": count,
                  "absolute_tolerance": T.TOL, "rows": evidence, "screen": screen}
        # Exclusive snapshots retain every completed/failed attempt. The barrier
        # filename is created once, complete or incomplete, by the outer finally.
        return report

    complete = False
    try:
        for take in takes:
            item = {**T.identity(take), "valid": False}
            timeout = None
            try:
                row = T.scored_row(take, loaded[take["slug"]], windows,
                                   previous[take["slug"]], 0, started)
                item["scores"] = {key: row[key] for key in T.ARMS.values()}
                T.validate_row(row)
                errors = {f"{arm}.{m}": abs(row[key][m]-previous[take["slug"]][key][m])
                          for arm, key in T.ARMS.items() for m in T.METRICS}
                count += len(errors)
                rows.append(row)
                item.update(valid=True, errors=errors)
            except Exception as error:
                item["error"] = U.failure(error)
                if isinstance(error, TimeoutError):
                    timeout = error
            evidence.append(R.safe_rejected_row(item))
            R.write_new(out / f"baseline-replay-attempt-{len(evidence):02d}.json", persist(False))
            if timeout is not None:
                raise timeout
        complete = True
    finally:
        report = persist(complete)
        R.write_new(out / "baseline-replay.json", report)
    require(report["passed"], "original108 replay/screen mismatch before model load")
    return rows


def baseline_inference(out, takes, loaded, windows, zero, net, started, original):
    """Unchanged U inference/scoring with a complete phase-owned NPZ manifest."""
    import numpy as np
    rows, evidence, predictions, count = [], [], {}, 0
    archived = {r["slug"]: r for r in original["rows"]}
    for take, base in zip(takes, zero):
        name = take["slug"] + ".offset-+0.npz"
        item = {**T.identity(take), "offset": 0, "valid": False,
                "attempted_file": name, "returned": False}
        saved = loaded[take["slug"]]
        timeout = None
        try:
            raw = np.asarray(U.infer(net, saved["net_input"], started))
            corrected = raw.copy()
            item["returned"] = True
            item["archive"] = save_arrays(out / name, {"raw_prediction": raw,
                "offset": np.int64(0), "corrected_prediction": corrected})
            item.update(prediction_file=name, prediction_file_sha256=item["archive"]["sha256"],
                        raw_prediction_sha256=T.digest(raw.tobytes()),
                        corrected_prediction_sha256=T.digest(corrected.tobytes()),
                        original_prediction_sha256_float32=T.wave_hash(saved["net"], "<f4"))
            R.check_time(started)
            U.validate_prediction(raw, corrected, None)
            item["byte_identical"] = raw.dtype == saved["net"].dtype and raw.tobytes() == saved["net"].tobytes()
            row = U.score_row(take, saved, corrected, base, 0, windows, started)
            errors = {m: abs(row["network_scores"][m]-archived[take["slug"]]["network_scores"][m])
                      for m in T.METRICS}
            count += len(errors)
            item.update(scores=row["network_scores"], errors=errors)
            T.validate_row(row)
            item["valid"] = item["byte_identical"] and all(v <= T.TOL for v in errors.values())
            row["valid"] = item["valid"]
            rows.append(row)
            predictions[take["slug"]] = raw
        except Exception as error:
            item["error"] = U.failure(error)
            if isinstance(error, TimeoutError):
                timeout = error
        evidence.append(R.safe_rejected_row(item))
        R.progress(out, {"stage": "baseline-inference", **evidence[-1]})
        if timeout is not None:
            U.write_baseline(out, takes, evidence, rows, count, complete=False)
            raise timeout
    report = U.write_baseline(out, takes, evidence, rows, count, complete=True)
    require(report["passed"], "complete12 original byte/36-score/zero gate replay failed")
    return rows, predictions


def control_metrics(values, h):
    import numpy as np
    x, y = values["model_converted_input"], values["forward_float64"]
    require(np.isfinite(h).all() and h[0] == 1 + 0j and h[-1] == -1 + 0j, "finite H/exact real endpoints required")
    unit = float(np.max(np.abs(np.abs(h) - 1)))
    errors = {"inverse": relative_error(values["inverse_float64"], x),
              "norm": relative_error(np.linalg.norm(y), np.linalg.norm(x)),
              "std": relative_error(np.std(y), np.std(x)),
              "whole_rfft_magnitude": relative_error(np.abs(np.fft.rfft(y)), np.abs(np.fft.rfft(x))),
              "quantized_inverse": relative_error(values["inverse_quantized_float64"], x)}
    passed = T.loss(unit) and unit <= 1e-12 and all(
        e["relative_l2"] <= (1e-6 if name == "quantized_inverse" else 1e-12) for name, e in errors.items())
    return {"passed": passed, "unit_magnitude_max_deviation": unit, "errors": errors}


def save_arrays(path, values):
    import numpy as np
    # Save first, before validity, time or finite checks; preserve raw return dtype.
    arrays = {name: np.asarray(value) for name, value in values.items()}
    with path.open("xb") as handle:
        np.savez_compressed(handle, **arrays)
    return {"file": path.name, "sha256": R.sha(path),
            "members": {name: {"dtype": str(x.dtype), "shape": list(x.shape),
                                "sha256": T.digest(x.tobytes())} for name, x in arrays.items()}}


def controls(out, takes, loaded, started):
    config = dict(CONFIG)
    coefficient_file = None
    coefficient_attempt = {"attempted_file": "coefficients.npz", "constructed": False}
    rows, prepared = [], {}
    complete = False
    try:
        T.panel(takes)
        R.check_time(started)
        try:
            h = coefficients()  # Strictly after both saved replay barriers.
            coefficient_attempt["constructed"] = True
            config["coefficients"] = U.array_identity(h)
            coefficient_attempt["members"] = {"h": {"dtype": str(h.dtype),
                "shape": list(h.shape), "sha256": T.digest(h.tobytes())}}
            coefficient_file = save_arrays(out / coefficient_attempt["attempted_file"], {"h": h})
            coefficient_attempt["archive"] = coefficient_file
            R.check_time(started)
        except Exception as error:
            coefficient_attempt["error"] = U.failure(error)
            raise
        for take in takes:
            item = {**T.identity(take), "passed": False,
                    "attempted_file": take["slug"] + ".controls.npz"}
            try:
                R.check_time(started)
                values = construction(loaded[take["slug"]], h)
                item["archive"] = save_arrays(out / item["attempted_file"], values)
                prepared[take["slug"]] = values
                R.check_time(started)
                item.update(control_metrics(values, h))
            except TimeoutError as error:
                item["error"] = U.failure(error)
                rows.append(R.safe_rejected_row(item))
                raise
            except Exception as error:
                item["error"] = U.failure(error)
            rows.append(R.safe_rejected_row(item))
            R.progress(out, {"stage": "construction-controls", **rows[-1]})
        complete = True
    finally:
        passed = complete and T.coverage(rows, takes) and all(r["passed"] is True for r in rows)
        R.write_new(out / "construction-controls.json", {"complete": complete, "passed": passed,
                    "config": config, "coefficients_attempt": coefficient_attempt,
                    "coefficients_archive": coefficient_file, "rows": rows})
    require(passed, "all12 complete positive controls must PASS before any phase model call")
    return prepared


def compare(rows, takes, baseline):
    try:
        T.panel(takes)
        require(baseline.get("valid") is True and baseline.get("passed") is True, "baselinezero PASS prerequisite")
        require(T.coverage(rows, takes) and all(r.get("valid") is True for r in rows), "exactly12 valid phase cases")
        for row in rows:
            T.validate_row(row)
        return F.compare(rows, takes)  # Original8ulp/10%/9wins/positive group medians.
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        return {"valid": False, "passed": False, "disposition": "INCONCLUSIVE", "reason": str(error)}


def phase_predictions(out, takes, prepared, net, started, evidence):
    """Retain ALL12 model returns before prediction validity/scoring begins."""
    predictions = {}
    for take in takes:
        R.check_time(started)
        slug, item = take["slug"], {**T.identity(take), "returned": False,
                                    "attempted_file": take["slug"] + ".phase.npz"}
        values = {key: prepared[slug][key] for key in ("phase_input", "phase_wet", "phase_flatref")}
        timeout = None
        try:
            raw = U.infer(net, values["phase_input"], started)
            values["raw_prediction"] = raw
            predictions[slug] = raw
            item["returned"] = True
        except Exception as error:
            item["error"] = U.failure(error)
            if isinstance(error, TimeoutError):
                timeout = error
        evidence.append(item)  # Evidence survives save/hash/budget errors too.
        item["archive"] = save_arrays(out / item["attempted_file"], values)
        R.progress(out, {"stage": "phase-predictions", **item})
        if timeout is not None:
            raise timeout
        R.check_time(started)
    return predictions


def score_cases(out, takes, loaded, prepared, predictions, zero, windows, started, rows, evidence):
    previous = {r["slug"]: r for r in zero}
    for take, item in zip(takes, evidence):
        slug = take["slug"]
        base, saved = previous[slug], loaded[slug]
        row = {**T.identity(take), "valid": False, "prediction_evidence": item,
               "qc_valid": base["qc_valid"], "oracle": base["oracle"]}
        rows.append(row)
        try:
            R.check_time(started)
            require(item.get("returned") is True, "missing phase model return")
            raw = predictions[slug]
            U.validate_prediction(raw, raw, None)  # No inverse, gain, lag or dtype repair.
            for arm, key in T.ARMS.items():
                wave = raw if arm == "net" else prepared[slug]["phase_" + arm]
                row[key] = P.score_prediction(wave, saved["target"], saved["di"], windows=windows)
                row[arm] = row[key]["primary"]
                R.check_time(started)
            T.validate_row(row)
            row.update(valid=True, changes_from_zero=T.paired_changes(row, base))
        except TimeoutError as error:
            row.update(valid=False, error=U.failure(error))
            raise
        except Exception as error:
            row.update(valid=False, error=U.failure(error))
        rows[-1] = R.safe_rejected_row(row)
        R.progress(out, {"stage": "phase-cases", **rows[-1]})


def output_directory(requested):
    expected = ROOT / OUTPUT
    require(requested.absolute() == expected and expected.resolve() == expected,
            "only declared --out " + OUTPUT + " is allowed; no aliases")
    expected.mkdir(parents=True, exist_ok=False)
    return expected


def run(out, context, started, state):
    correction, manifest, pins, revision, original, verification, control, hashes, old_inputs, prior_inputs = context
    takes = manifest["takes"]
    R.write_new(out / "provenance.json", {"pins": pins, "git_revision": revision,
        "input_artifacts": hashes, "model": manifest["model"], "config": CONFIG,
        "scope": SCOPE, "prefix": sys.prefix, "python": sys.version, "thread_count": 2,
        "budget_seconds": 900, "started_unix": time.time(), "attribution": manifest["attribution"],
        "packages": {n: R.package_version(n) for n in ("numpy", "scipy", "torch")}})
    U.stability(manifest, pins, revision, hashes, started)
    windows = V.load_windows(correction)
    loaded, identities = U.load_inputs(takes, hashes, verification, control, old_inputs, started)
    require({"artifacts": hashes, "waveforms": identities} == prior_inputs, "prior original six-member input identity drift")
    R.write_new(out / "inputs.json", {"artifacts": hashes, "waveforms": identities})
    zero = replay(out, takes, loaded, windows, original, started)  # Saved108 PASS before model load.
    U.stability(manifest, pins, revision, hashes, started)
    net = U.load_model(manifest, started)
    zero, _ = baseline_inference(out, takes, loaded, windows, zero, net, started, original)
    # Saved12 byte-identical +36 scores +Fgate PASS before first phase construction.
    state["baseline_reused_no_new_score"] = zero
    baseline = F.compare(zero, takes)
    require(baseline.get("passed") is True, "baselinezero gate must PASS")
    U.stability(manifest, pins, revision, hashes, started)
    prepared = controls(out, takes, loaded, started)  # Saved ALL12 controls before phase calls.
    U.stability(manifest, pins, revision, hashes, started)
    predictions = phase_predictions(out, takes, prepared, net, started, state["prediction_evidence"])
    score_cases(out, takes, loaded, prepared, predictions, zero, windows, started, state["rows"], state["prediction_evidence"])
    U.stability(manifest, pins, revision, hashes, started)
    R.check_time(started)
    state["screen"] = compare(state["rows"], takes, baseline)
    state["complete"] = len(state["rows"]) == 12
    R.check_time(started)  # Aggregation is included in the budget.


def execute(out, started):
    state = {"complete": False, "rows": [], "prediction_evidence": [], "config": CONFIG,
             "screen": {"valid": False, "passed": False, "disposition": "INCONCLUSIVE"},
             "interpretation": "Artificial finite periodic phase challenge of dependent known-clean Morgan cases. No physical cabinet, native transfer, complete processing panel or product claim. Saved flatref transform is a declared simple arm; ideal magnitude correction commutes, but new flatref reconstruction and finite scoring-window equivalence are not established."}
    try:
        context = guard(started)
        run(out, context, started, state)
        R.check_time(started)
        state["elapsed_seconds"] = time.monotonic() - started
        R.write_new(out / "result.json", R.safe_rejected_row(state))
        R.check_time(started)  # Final successful saving is included too.
    except Exception as error:
        state["screen"] = {"valid": False, "passed": False, "disposition": "INCONCLUSIVE", "error": U.failure(error)}
        state["elapsed_seconds"] = time.monotonic() - started
        if (out / "result.json").exists():
            # Keep the provisional result when the post-save check expires.
            (out / "result.json").rename(out / "result-before-final-budget.json")
        R.write_new(out / "failure.json", {**U.failure(error), "disposition": "INCONCLUSIVE",
                                          "elapsed_seconds": time.monotonic() - started})
        R.write_new(out / "result.json", R.safe_rejected_row(state))
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    require(sys.prefix == str(U.CPU_PREFIX) and Path(sys.prefix).resolve() == U.CPU_PREFIX
            and sys.byteorder == "little", "requires explicit original CPU interpreter prefix " + str(U.CPU_PREFIX))
    started = time.monotonic()  # Before guards, all hashes, model access and scoring.
    out = output_directory(args.out)
    execute(out, started)


if __name__ == "__main__":
    main()
