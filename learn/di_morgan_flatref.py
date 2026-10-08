"""Fixed saved-render net versus simple-DI baseline diagnostic; no inference.

Only after independent verification and committed declaration/input hashes.
Replay all original baseline scores before computing any new flatref score.
"""
from __future__ import annotations

import argparse
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
from learn import run_di_domain_pilot_v2 as V

PLAN = ROOT / "docs/di-morgan-flatref-plan.md"
SOURCE = ROOT / "tmp/di-morgan-control-20261008"
HASHES = ROOT / "docs/di-morgan-flatref-inputs.sha256"
OWN_PINS = ("docs/di-morgan-flatref-plan.md", "docs/di-morgan-flatref-inputs.sha256",
            "learn/di_morgan_flatref.py", "tests/test_di_morgan_flatref.py",
            "docs/di-morgan-control.json", "docs/di-morgan-control-verification.json",
            "docs/di-morgan-control-prepare.json", "docs/di-morgan-control-render.json")


def guard():
    if "**Declared:" not in PLAN.read_text():
        raise ValueError("flatref diagnostic requires verified prerequisite and committed declaration")
    correction, manifest, pins = C.code_inputs()
    for name in OWN_PINS:
        data = (ROOT / name).read_bytes()
        if data != subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT):
            raise ValueError(f"uncommitted flatref dependency: {name}")
        pins[name] = hashlib.sha256(data).hexdigest()
    original = json.loads((ROOT / "docs/di-morgan-control.json").read_text())
    if original.get("complete") is not True or original["screen"].get("passed") is not True:
        raise ValueError("verified successful original control required")
    verification = json.loads((ROOT / "docs/di-morgan-control-verification.json").read_text())
    if (verification.get("status") != "VERIFIED_WITH_EVIDENCE_LIMITS"
            or verification.get("failures") != [] or not verification.get("checks")
            or any(c.get("passed") is not True for c in verification["checks"])
            or verification["independent_screen"].get("passed") is not True):
        raise ValueError("successful independent prerequisite verification required")
    for stage in ("prepare", "render"):
        if (SOURCE / stage / "result.json").read_bytes() != (ROOT / f"docs/di-morgan-control-{stage}.json").read_bytes():
            raise ValueError(f"verified {stage} report changed")
    if (SOURCE / "infer/result.json").read_bytes() != (ROOT / "docs/di-morgan-control.json").read_bytes():
        raise ValueError("primary control result changed")
    provenance = json.loads((SOURCE / "infer/provenance.json").read_text())
    original_names = set(pins)-set(OWN_PINS)
    if provenance["pins"] != {n: pins[n] for n in original_names}:
        raise ValueError("source definitions differ from original control")
    return correction, manifest, pins, original


def input_hashes(takes):
    """Require exactly the 36 declared score-array files, no arbitrary paths."""
    expected = {str((SOURCE / stage / f"{t['slug']}.npz").relative_to(ROOT))
                for stage in ("prepare", "render", "infer") for t in takes}
    observed = {}
    for line in HASHES.read_text().splitlines():
        digest, name = line.split("  ", 1)
        if name not in expected or name in observed or not re.fullmatch("[a-f0-9]{64}", digest):
            raise ValueError("invalid, duplicate or undeclared artifact hash")
        path = (ROOT / name).resolve()
        if not path.is_relative_to(SOURCE.resolve()):
            raise ValueError("artifact path escapes declared source")
        if R.sha(path) != digest:
            raise ValueError(f"changed verified artifact: {name}")
        observed[name] = digest
    if set(observed) != expected or len(expected) != 36:
        raise ValueError("require all 36 verified array artifacts")
    return observed


def compare(rows, takes):
    translated = []
    for row in rows:
        try:
            for key in ("wet", "net", "flatref"):
                value = row[key]
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise ValueError("invalid loss")
            if min(row["wet"], row["flatref"]) <= 0:
                raise ValueError("zero simple baseline")
            translated.append({**row, "morgan_input": min(row["wet"], row["flatref"]), "morgan_net": row["net"]})
        except (KeyError, TypeError, ValueError):
            return {"valid": False, "passed": False, "disposition": "INCONCLUSIVE", "reason": "invalid baseline/net loss"}
    result = C.compare(translated, takes)
    if result["valid"]:
        result["passed"] = (result["passed"] and result["strict_wins"] >= 9
                            and all(v > 0 for v in result["group_medians"].values()))
        result["disposition"] = "PASS" if result["passed"] else "FAIL"
    return result


def run(out, manifest, takes, windows, original):
    import numpy as np

    started = time.monotonic()
    R.require_report(SOURCE / "prepare/result.json", "valid", takes)
    R.require_report(SOURCE / "render/result.json", "complete", takes)
    artifacts = input_hashes(takes)
    if R.sha(manifest["average"]["path"]) != manifest["average"]["sha256"]:
        raise ValueError("changed frozen average")
    average = np.load(manifest["average"]["path"], allow_pickle=False)
    previous = {r["slug"]: r for r in original["rows"]}
    loaded, replay = [], []
    # COMPLETE replay first, never interleave experimental flatref computation.
    for take in takes:
        R.check_time(started)
        with np.load(SOURCE / "prepare" / f"{take['slug']}.npz", allow_pickle=False) as saved:
            di, target = saved["di"], saved["target"]
        with np.load(SOURCE / "render" / f"{take['slug']}.npz", allow_pickle=False) as saved:
            wet = saved["baseline"]
        with np.load(SOURCE / "infer" / f"{take['slug']}.npz", allow_pickle=False) as saved:
            net = saved["prediction"]
        scores = {"input_scores": P.score_prediction(wet, target, di, windows=windows),
                  "network_scores": P.score_prediction(net, target, di, windows=windows)}
        errors = {}
        for arm, values in scores.items():
            for key, value in values.items():
                expected = previous[take["slug"]][arm][key]
                if not math.isfinite(expected) or not math.isfinite(value):
                    raise ValueError("nonfinite replay score")
                errors[f"{arm}.{key}"] = abs(value-expected)
        replay.append({"slug": take["slug"], "errors": errors})
        if any(v > 1e-8 for v in errors.values()):
            R.write_new(out / "baseline-replay.json", {"passed": False, "rows": replay})
            raise ValueError("original-score replay failed before experimental scoring")
        loaded.append((take, di, target, wet, scores))
    R.write_new(out / "baseline-replay.json", {"passed": True, "rows": replay})
    rows = []
    for take, di, target, wet, scores in loaded:
        R.check_time(started)
        flatref = P.canonical_target(wet, average)
        flat_scores = P.score_prediction(flatref, target, di, windows=windows)
        row = {k: take[k] for k in ("slug", "content", "take")}
        row.update(qc_valid=True, oracle=previous[take["slug"]]["oracle"],
                   wet=scores["input_scores"]["primary"], net=scores["network_scores"]["primary"],
                   flatref=flat_scores["primary"], flatref_scores=flat_scores, **scores)
        with (out / f"{take['slug']}.npz").open("xb") as f:
            np.savez_compressed(f, flatref=flatref)
        rows.append(row)
        R.progress(out, row)
    R.check_time(started)
    R.write_new(out / "result.json", {"complete": True, "rows": rows, "screen": compare(rows, takes),
        "attribution": manifest["attribution"], "input_artifacts": artifacts,
        "elapsed_seconds": time.monotonic()-started})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        raise ValueError("use actual project helper environment")
    correction, manifest, pins, original = guard()
    out = args.out.resolve()
    if not out.is_relative_to((ROOT / "tmp").resolve()):
        raise ValueError("output must remain under project tmp")
    out.mkdir(parents=True, exist_ok=False)
    R.write_new(out / "provenance.json", {"pins": pins, "python": sys.version,
        "packages": {n: R.package_version(n) for n in ("numpy", "scipy")}})
    try:
        takes = []
        for declared in manifest["takes"]:
            take = dict(declared)
            take["di"] = str(Path(manifest["source_root"]) / take["di"])
            takes.append(take)
        run(out, manifest, takes, V.load_windows(correction), original)
    except Exception as error:
        R.write_new(out / "failure.json", {"type": type(error).__name__, "message": str(error)})
        raise


if __name__ == "__main__":
    main()
