"""Frozen calibration diagnostic on constructed pairs; importing reads no assets.

The CLI remains locked until main declares and commits an independently reviewed
snapshot. No native audio, catalog, model, average, scoring or rendering is used.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from learn import di_morgan_control as C
from learn import di_domain_pilot as P
from learn import run_di_domain_pilot as R

PLAN = ROOT / "docs/di-alignment-control-plan.md"
SOURCE = ROOT / "tmp/di-morgan-control-20261008"
OUTPUT = "tmp/di-alignment-control-20261008"
HASHES = ROOT / "docs/di-morgan-flatref-inputs.sha256"
REVIEW = "docs/research/di-alignment-control-review-2026-10-08.md"
VERIFIER = "docs/research/di-morgan-control-independent-2026-10-08.py"
OWN_PINS = (
    "learn/di_alignment_control.py", "tests/test_di_alignment_control.py",
    "docs/di-alignment-control-plan.md", "docs/di-morgan-flatref-inputs.sha256",
    "docs/di-morgan-control-prepare.json", "docs/di-morgan-control-verification.json",
    VERIFIER, REVIEW,
)
ARMS = ("identity", "polarity", "lowpass", "tanh")
SHIFTS = (-128, 0, 128)
ERRORS = (
    "calibration GCC-PHAT peak sharpness must exceed 10",
    "ambiguous GCC-PHAT peak: separation must exceed 1.2",
    "calibration/catalog lag mismatch",
    "calibration half-lag disagreement",
    "calibration filtered correlation below 0.5",
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def design_bytes(text):
    """Administrative approval block is outside the reviewed scientific body."""
    return text.split("## Frozen design\n", 1)[1].encode()


def guard():
    """All declaration, source and prerequisite checks precede any NPZ access."""
    text = PLAN.read_text()
    match = re.search(r"<!-- alignment-approval\n(.*?)\nalignment-approval -->", text, re.S)
    approval = json.loads(match[1]) if match else {}
    if ("**Declared:" not in text or approval.get("status") != "DECLARED"
            or approval.get("fresh_independent_review") is not True
            or approval.get("mean_interpretation") != "uncentered-input-exact-formula"):
        raise ValueError("requires fresh independent review and committed declaration")
    _, manifest, inherited = C.code_inputs()
    if len(inherited) != 35 or set(inherited) & set(OWN_PINS):
        raise ValueError("expected exactly 35 disjoint inherited source pins")
    pins = dict(inherited)
    for name in OWN_PINS:
        data = (ROOT / name).read_bytes()
        if data != subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT):
            raise ValueError(f"uncommitted alignment dependency: {name}")
        pins[name] = digest(data)
    expected = {
        "review_sha256": pins[REVIEW],
        "source_sha256": pins["learn/di_alignment_control.py"],
        "test_sha256": pins["tests/test_di_alignment_control.py"],
        "design_sha256": digest(design_bytes(text)),
    }
    if any(approval.get(k) != v for k, v in expected.items()):
        raise ValueError("fresh review does not identify this exact snapshot")
    if "Verdict: APPROVE" not in (ROOT / REVIEW).read_text():
        raise ValueError("fresh independent review approval required")
    takes = manifest["takes"]
    cases(takes)  # Strict identity and group coverage before prerequisite/asset reads.
    prepare = read_json(ROOT / "docs/di-morgan-control-prepare.json")
    verification = read_json(ROOT / "docs/di-morgan-control-verification.json")
    prerequisite(prepare, verification, takes, inherited, pins[VERIFIER])
    if (SOURCE / "prepare/result.json").read_bytes() != (ROOT / "docs/di-morgan-control-prepare.json").read_bytes():
        raise ValueError("frozen prepare report changed")
    if read_json(SOURCE / "prepare/provenance.json").get("pins") != inherited:
        raise ValueError("prepare source pins changed")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return manifest, pins, revision


def identity(row):
    return {k: row[k] for k in ("slug", "content", "take")}


def prerequisite(prepare, verification, takes, inherited, verifier_hash):
    def coverage(rows):
        return (len(rows) == 12 and [identity(r) for r in rows] == [identity(t) for t in takes])

    if (prepare.get("complete") is not True or prepare.get("valid") is not True
            or not coverage(prepare.get("rows", []))):
        raise ValueError("all twelve frozen valid prepare rows required")
    for row in prepare["rows"]:
        oracle = row["oracle_scores"]["primary"]
        if (row.get("qc_valid") is not True or row["qc"].get("valid") is not True
                or type(oracle) not in (int, float) or not math.isfinite(oracle)
                or not 0 <= oracle < 1e-6):
            raise ValueError("frozen prepare QC/oracle prerequisite failed")
    checks = verification.get("checks", [])
    if (verification.get("status") != "VERIFIED_WITH_EVIDENCE_LIMITS"
            or verification.get("failures") != [] or not checks
            or any(c.get("passed") is not True for c in checks)
            or verification.get("source_pins") != inherited
            or verification.get("verifier_sha256") != verifier_hash
            or not coverage(verification.get("preparation", []))):
        raise ValueError("successful independent preparation verification required")
    for row in verification["preparation"]:
        oracle = row["oracle_scores"]["primary"]
        if (row["qc"].get("valid") is not True or type(oracle) not in (int, float)
                or not math.isfinite(oracle) or not 0 <= oracle < 1e-6):
            raise ValueError("independent prepare QC/oracle prerequisite failed")


def cases(takes):
    """Original manifest order, including cyclic NEXT within each six-take group."""
    if (len(takes) != 12 or len({t["slug"] for t in takes}) != 12
            or len({t["take"] for t in takes}) != 12
            or any(t["content"] not in ("chords", "scales") for t in takes)
            or any(sum(t["content"] == g for t in takes) != 6 for g in ("chords", "scales"))
            or any(not re.fullmatch(r"[a-zA-Z0-9_-]+", t["slug"]) for t in takes)):
        raise ValueError("require twelve distinct declared takes, six per content group")
    rows = []
    for t in takes:
        for arm in ARMS:
            for lag in SHIFTS:
                rows.append({**identity(t), "case_id": f"{t['slug']}:{arm}:{lag}",
                             "pair": identity(t), "arm": arm, "positive": True,
                             "imposed_lag": lag, "catalog_lag": lag,
                             "truth_lag": lag, "truth_polarity": -1 if arm == "polarity" else 1})
    for t in takes:
        group = [v for v in takes if v["content"] == t["content"]]
        other = group[(group.index(t) + 1) % 6]
        rows.append({**identity(t), "case_id": f"{t['slug']}:mismatch:0",
                     "pair": identity(other), "arm": "mismatch", "positive": False,
                     "imposed_lag": 0, "catalog_lag": 0,
                     "truth_lag": None, "truth_polarity": None})
    return rows


def transform(di6, arm):
    """Transform complete six seconds BEFORE cropping, shifting or padding."""
    import numpy as np
    from scipy.signal import butter, sosfiltfilt

    x = P._mono(di6, P.SCORE)
    std = float(np.std(x))
    if not math.isfinite(std) or std <= 0:
        raise ValueError("nonfinite or silent six-second DI")
    if arm in ("identity", "mismatch"):
        y = x.copy()
    elif arm == "polarity":
        y = -x
    elif arm == "lowpass":
        y = sosfiltfilt(butter(4, 1200, btype="lowpass", fs=P.SR, output="sos"),
                       x, padtype="odd", padlen=27)
    elif arm == "tanh":
        y = np.tanh(3*x/std)*std/3  # Deliberately no demeaning or mean restoration.
    else:
        raise ValueError("undeclared transform")
    return P._mono(y, P.SCORE)


def finite_shift(x, lag):
    import numpy as np

    P._integer(lag, "imposed lag")
    y = np.zeros_like(x)
    if lag == 0:
        y[:] = x
    elif 0 < lag < len(x):
        y[lag:] = x[:-lag]
    elif -len(x) < lag < 0:
        y[:lag] = x[-lag:]
    return y


def construct(di6, other6, arm, lag):
    """Compact prefixes determine the ten-second buffers exactly; no cyclic wrap."""
    import numpy as np

    if lag not in SHIFTS:
        raise ValueError("undeclared imposed lag")
    di6 = P._mono(di6, P.SCORE)
    transformed = transform(other6, arm)
    used = P.CALIBRATION + 2*P.GUARD
    if used > P.SCORE:
        raise ValueError("six seconds cannot supply calibration and both guards")
    di = np.zeros(P.TOTAL + 2*P.GUARD, dtype=np.float64)
    wet = np.zeros_like(di)
    di[:used] = di6[:used]
    wet[:used] = finite_shift(transformed[:used], lag)
    if min(float(np.std(di[P.GUARD:P.GUARD+P.CALIBRATION])),
           float(np.std(wet[P.GUARD:P.GUARD+P.CALIBRATION]))) <= 0:
        raise ValueError("silent constructed calibration interval")
    return di, wet, {"origin": P.GUARD, "prefix_samples": used,
                     "total_samples": len(di), "dtype": "<f8",
                     "di_prefix_sha256": signal_hash(di[:used]),
                     "wet_prefix_sha256": signal_hash(wet[:used]),
                     "transformed_di6_sha256": signal_hash(transformed),
                     "tail": "zeros after prefix_samples"}


def signal_hash(x):
    import numpy as np

    return digest(np.asarray(x, dtype="<f8").tobytes())


def predicates(estimates, correlation, catalog_lag):
    """Exact frozen inequalities and error order; no tolerance at confidence gates."""
    lags, sharpness, separation = zip(*estimates)
    sharp = [not (s <= 10) for s in sharpness]
    separate = [not (s <= 1.2) for s in separation]
    catalog_error = abs(lags[0] - catalog_lag)
    lag_range = max(lags) - min(lags)
    gates = {"sharpness": sharp, "peak_separation": separate,
             "catalog_within_16": catalog_error <= 16, "lag_range_within_8": lag_range <= 8,
             "absolute_correlation_at_least_half": math.isfinite(correlation) and abs(correlation) >= .5}
    passed = [all(sharp), all(separate), gates["catalog_within_16"],
              gates["lag_range_within_8"], gates["absolute_correlation_at_least_half"]]
    return gates, next((e for ok, e in zip(passed, ERRORS) if not ok), None)


def diagnose(di_guarded, wet_guarded, catalog_lag):
    """Record even downstream predicates that the real calibrator never reaches."""
    import numpy as np

    count = P.TOTAL + 2*P.GUARD
    if len(di_guarded) != count or len(wet_guarded) != count:
        raise ValueError("expected ten seconds plus both guards")
    P._integer(catalog_lag, "catalog_lag")
    if abs(catalog_lag) > P.GUARD:
        raise ValueError("catalog lag outside +/-512")
    di = P._mono(di_guarded[P.GUARD:P.GUARD+P.CALIBRATION], P.CALIBRATION)
    wet = P._mono(wet_guarded[P.GUARD:P.GUARD+P.CALIBRATION], P.CALIBRATION)
    half = P.CALIBRATION // 2
    estimates = [P._gcc_phat(di, wet)]
    estimates += [P._gcc_phat(di[s:s+half], wet[s:s+half]) for s in (0, half)]
    lag = estimates[0][0]
    a, b = P.bandpass(di), P.bandpass(wet)
    if lag > 0:
        a, b = a[:-lag], b[lag:]
    elif lag < 0:
        a, b = a[-lag:], b[:lag]
    a, b = a-a.mean(), b-b.mean()
    denominator = float(np.linalg.norm(a)*np.linalg.norm(b))
    correlation = float(a @ b / denominator) if denominator else 0.0
    gates, first_error = predicates(estimates, correlation, catalog_lag)
    lags, sharpness, separation = zip(*estimates)
    derived = asdict(P.Calibration(lag, 1 if correlation >= 0 else -1, correlation,
                                  sharpness[0], tuple(lags[1:]), tuple(sharpness[1:]),
                                  separation[0], tuple(separation[1:])))
    actual, error, error_type = None, None, None
    try:
        actual = asdict(P.calibrate(di_guarded, wet_guarded, catalog_lag))
    except Exception as exc:
        error, error_type = str(exc), type(exc).__name__
    accepted = actual is not None
    consistent = (accepted and first_error is None and actual == derived
                  or not accepted and first_error is not None and error_type == "ValueError" and error == first_error)
    finite = all(math.isfinite(v) for est in estimates for v in est) and all(
        math.isfinite(v) for v in (correlation, denominator))
    return {"valid": bool(finite), "consistent": bool(consistent), "accepted": accepted,
            "estimates": [{"interval": label, "lag": est[0], "sharpness": est[1],
                           "peak_separation": est[2]}
                          for label, est in zip(("full", "first_half", "second_half"), estimates)],
            "correlation": correlation, "correlation_denominator": denominator,
            "catalog_error": abs(lag-catalog_lag), "lag_range": max(lags)-min(lags),
            "gates": gates, "derived_fields": derived, "predicted_first_error": first_error,
            "actual_fields": actual, "calibrate_first_error": error, "calibrate_error_type": error_type}


def evaluate(case, di6, other6):
    di, wet, construction = construct(di6, other6, case["arm"], case["imposed_lag"])
    row = {**case, "construction": construction, **diagnose(di, wet, case["catalog_lag"])}
    positive = case["positive"]
    row["estimate_lag_errors"] = ([e["lag"]-case["truth_lag"] for e in row["estimates"]]
                                  if positive else None)
    row["estimated_polarity_correct"] = (row["derived_fields"]["polarity"] == case["truth_polarity"]
                                          if positive else None)
    actual = row["actual_fields"]
    row["accepted_lag_error"] = actual["lag"]-case["truth_lag"] if positive and actual else None
    row["accepted_polarity_correct"] = actual["polarity"] == case["truth_polarity"] if positive and actual else None
    return R.safe_rejected_row(row)


def compare(rows, takes):
    def invalid(reason):
        return {"valid": False, "passed": False, "disposition": "INCONCLUSIVE", "reason": reason}

    def finite(value):
        if isinstance(value, float):
            return math.isfinite(value)
        if isinstance(value, dict):
            return all(finite(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return all(finite(v) for v in value)
        return True

    try:
        expected = {c["case_id"]: c for c in cases(takes)}
        actual = {r["case_id"]: r for r in rows}
        if len(rows) != 156 or len(actual) != 156 or actual.keys() != expected.keys():
            return invalid("require exactly all 144 positives and 12 negatives")
        for key, row in actual.items():
            if any(row.get(k) != v for k, v in expected[key].items()):
                return invalid("case identity/truth differs from declaration")
            if (row.get("valid") is not True or row.get("consistent") is not True
                    or row.get("nonfinite_diagnostic_fields") != [] or not finite(row)
                    or type(row["accepted"]) is not bool):
                return invalid("nonfinite/invalid diagnostics or actual calibrate inconsistency")
            if row["accepted"]:
                fields = row["actual_fields"]
                if (type(fields["lag"]) is not int or type(fields["polarity"]) is not int
                        or fields["polarity"] not in (-1, 1)):
                    return invalid("invalid actual accepted calibration")
        ordered = [actual[k] for k in expected]
        wrong = [r for r in ordered if r["positive"] and r["accepted"] and
                 (abs(r["actual_fields"]["lag"]-r["truth_lag"]) > 1
                  or r["actual_fields"]["polarity"] != r["truth_polarity"])]
        negatives = [r for r in ordered if not r["positive"] and r["accepted"]]
        required = {arm: sum(r["accepted"] for r in ordered if r["arm"] == arm)
                    for arm in ("identity", "polarity")}
        passed = all(v == 36 for v in required.values()) and not wrong and not negatives
        counts = {}
        for arm in (*ARMS, "mismatch"):
            counts[arm] = {}
            for content in ("all", "chords", "scales"):
                subset = [r for r in ordered if r["arm"] == arm and
                          (content == "all" or r["content"] == content)]
                accepted = sum(r["accepted"] for r in subset)
                counts[arm][content] = {"total": len(subset), "accepted": accepted,
                                        "rejected": len(subset)-accepted,
                                        "acceptance_rate": accepted/len(subset)}
        return {"valid": True, "passed": passed, "disposition": "PASS" if passed else "FAIL",
                "counts_by_arm_content": counts, "wrong_accepted_positives": wrong,
                "accepted_mismatch_negatives": negatives,
                "required_positive_acceptance": required,
                "interpretation": "Optimistic correct-prior constructed-pair calibration only; no native alignment or model-transfer conclusion."}
    except (KeyError, TypeError, ValueError):
        return invalid("missing or malformed case evidence")


def declared_hashes(takes):
    """Parse all 36 metadata entries; return ONLY the exact 12 prepare entries."""
    cases(takes)
    expected = {str((SOURCE / stage / f"{t['slug']}.npz").relative_to(ROOT))
                for stage in ("prepare", "render", "infer") for t in takes}
    observed = {}
    for line in HASHES.read_text().splitlines():
        parts = line.split("  ")
        if len(parts) != 2:
            raise ValueError("invalid artifact hash syntax")
        sha, name = parts
        if name not in expected or name in observed or not re.fullmatch(r"[a-f0-9]{64}", sha):
            raise ValueError("invalid, duplicate or undeclared artifact hash")
        observed[name] = sha
    if set(observed) != expected or len(observed) != 36:
        raise ValueError("require exactly the existing 36-artifact manifest")
    selected = {name: observed[name] for name in sorted(observed)
                if Path(name).parent == SOURCE.relative_to(ROOT) / "prepare"}
    if len(selected) != 12:
        raise ValueError("require exactly twelve prepare input hashes")
    return selected


def load_inputs(takes, hashes, started):
    import numpy as np

    # Hash ALL twelve before any load; never hash render/infer/native assets.
    for name, sha in hashes.items():
        R.check_time(started)
        path = ROOT / name
        if path.resolve() != path or R.sha(path) != sha:
            raise ValueError(f"changed or linked verified prepare artifact: {name}")
    loaded = {}
    for take in takes:
        R.check_time(started)
        path = SOURCE / "prepare" / f"{take['slug']}.npz"
        # Recheck immediately before the read as well as at the all12 barrier.
        if R.sha(path) != hashes[str(path.relative_to(ROOT))]:
            raise ValueError("prepare artifact changed before load")
        with np.load(path, allow_pickle=False) as saved:
            x = P._mono(saved["di"], P.SCORE).copy()  # No other NPZ member accessed.
        if float(np.std(x)) <= 0:
            raise ValueError("silent saved DI")
        loaded[take["slug"]] = x
    return loaded


def output_directory(requested):
    expected = ROOT / OUTPUT
    # Reject aliases/symlinks, escapes and reused outputs, including empty ones.
    if requested.absolute() != expected or expected.resolve() != expected:
        raise ValueError(f"only declared --out {OUTPUT} is allowed; no symlink aliases")
    expected.mkdir(parents=True, exist_ok=False)
    return expected


def run(out, manifest, pins, revision, started):
    takes = manifest["takes"]
    plan = cases(takes)
    hashes = {}
    try:
        hashes = declared_hashes(takes)
    finally:
        # Retain source/environment evidence even if hash metadata is malformed.
        R.write_new(out / "provenance.json", {"pins": pins, "git_revision": revision,
            "declared_input_artifacts": hashes, "python": sys.version, "prefix": sys.prefix,
            "started_unix": time.time(), "budget_seconds": R.LIMIT,
            "packages": {n: R.package_version(n) for n in ("numpy", "scipy")},
            "attribution": manifest["attribution"], "cases": plan})
    loaded = load_inputs(takes, hashes, started)
    R.write_new(out / "inputs.json", {"artifacts": hashes,
        "di6_sha256": {slug: signal_hash(x) for slug, x in loaded.items()}})
    rows = []
    for case in plan:
        R.check_time(started)
        try:
            row = evaluate(case, loaded[case["slug"]], loaded[case["pair"]["slug"]])
        except Exception as error:
            row = {**case, "valid": False, "consistent": False, "accepted": False,
                   "case_error": {"type": type(error).__name__, "message": str(error)}}
        rows.append(row)
        R.progress(out, row)
        R.check_time(started)
    R.write_new(out / "result.json", {"complete": True, "rows": rows,
        "screen": compare(rows, takes), "elapsed_seconds": time.monotonic()-started,
        "attribution": manifest["attribution"]})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        raise ValueError("use actual project helper environment")
    started = time.monotonic()
    manifest, pins, revision = guard()
    out = output_directory(args.out)
    try:
        run(out, manifest, pins, revision, started)
    except Exception as error:
        R.write_new(out / "failure.json", {"type": type(error).__name__, "message": str(error),
            "disposition": "INCONCLUSIVE", "elapsed_seconds": time.monotonic()-started})
        raise


if __name__ == "__main__":
    main()
