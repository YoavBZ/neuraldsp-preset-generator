"""Separate window-corrected pilot. Metric + helper replay precede asset access.

No training, downloads, interpreter switching, or changes to frozen direc.py.
Stages preserve attempt 1 and refuse overwriting an existing stage directory.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from learn import run_di_domain_pilot as R
from learn import di_domain_pilot as P

PLAN = ROOT / "docs/di-domain-pilot-v2-plan.md"
INPUTS = ROOT / "docs/di-domain-pilot-v2-inputs.json"
PINNED = tuple(dict.fromkeys((*R.PINNED,
    "learn/run_di_domain_pilot_v2.py", "tests/test_di_domain_pilot_v2.py",
    "tests/test_di_domain_pilot.py", "tests/test_run_di_domain_pilot.py",
    "docs/di-domain-pilot-v2-plan.md", "docs/di-domain-pilot-v2-inputs.json",
    "docs/di-domain-metric-probe-windows.json.gz")))
CPU_PREFIX = Path("/Users/yoavbz/ndsp-presets/tools/learn-venv")
TOL = 1e-8


def code_inputs():
    """Code and declaration bytes only: no catalog, model or average reads."""
    if "**Declared:" not in PLAN.read_text():
        raise ValueError("attempt 2 must be declared and committed")
    pins = {}
    for name in PINNED:
        data = (ROOT / name).read_bytes()
        committed = subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT)
        if data != committed:
            raise ValueError(f"uncommitted attempt-2 dependency: {name}")
        pins[name] = hashlib.sha256(data).hexdigest()
    correction = json.loads(INPUTS.read_text())
    if (correction["schema"] != 2 or correction["tolerance"] != TOL
            or correction["original_inputs"] != "docs/di-domain-pilot-inputs.json"
            or correction["window_family"] != "torch32" or correction["window_dtype"] != "<f4"):
        raise ValueError("unexpected correction specification")
    if R.sha(ROOT / correction["original_inputs"]) != correction["original_inputs_sha256"]:
        raise ValueError("original scientific inputs changed")
    manifest = json.loads((ROOT / correction["original_inputs"]).read_text())
    return correction, manifest, pins


def load_windows(correction):
    """Decode losslessly saved IEEE float32 bits; no Hann reconstruction/fallback."""
    import numpy as np

    if correction["windows"] != "docs/di-domain-metric-probe-windows.json.gz":
        raise ValueError("unexpected window archive")
    blob = (ROOT / correction["windows"]).read_bytes()
    if hashlib.sha256(blob).hexdigest() != correction["windows_sha256"]:
        raise ValueError("window archive hash mismatch")
    raw = gzip.decompress(blob)
    if hashlib.sha256(raw).hexdigest() != correction["windows_raw_sha256"]:
        raise ValueError("window text hash mismatch")
    table = json.loads(raw)
    if set(table) != {str(n) for n in P.FFTS}:
        raise ValueError("window FFT coverage mismatch")
    result = {}
    for n in P.FFTS:
        row = table[str(n)]["torch32"]
        bits = row["bits"]
        if (row["dtype"] != "<f4" or len(bits) != n
                or any(type(v) is not int or not 0 <= v < 2**32 for v in bits)):
            raise ValueError("invalid window dtype/bits/length")
        data = np.asarray(bits, dtype="<u4").tobytes()
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("window coefficient hash mismatch")
        window = np.frombuffer(data, dtype="<f4").astype(np.float64)
        if not np.isfinite(window).all():
            raise ValueError("nonfinite coefficient")
        window.flags.writeable = False
        result[n] = window
    return result


def synthetic_cases():
    import numpy as np

    b = np.random.default_rng(20261008).normal(size=144000) * .1
    return b, [b.copy(), b*.5, np.roll(b, 52), np.zeros_like(b)]


def signal_hash(x):
    import numpy as np

    return hashlib.sha256(np.asarray(x, dtype="<f8").tobytes()).hexdigest()


def check_report(run, stage, pins):
    report = json.loads((run / stage / "result.json").read_text())
    provenance = json.loads((run / stage / "provenance.json").read_text())
    if report.get("passed") is not True or provenance.get("pins") != pins:
        raise ValueError(f"{stage} prerequisite failed or source pins changed")
    return report


def stage_directory(run, stage, pins, attribution):
    run = run.resolve()
    if not run.is_relative_to((ROOT / "tmp").resolve()):
        raise ValueError("attempt-2 output must stay under project tmp")
    if stage == "metric":
        run.mkdir(parents=True, exist_ok=False)
    else:
        check_report(run, "metric", pins)
        if stage != "numpy":
            check_report(run, "numpy", pins)
    out = run / stage
    out.mkdir(exist_ok=False)
    R.write_new(out / "provenance.json", {
        "pins": pins, "attribution": attribution, "python": sys.version,
        "prefix": sys.prefix,
        "packages": {n: R.package_version(n) for n in ("numpy", "scipy", "soundfile", "torch")},
    })
    return out


def metric(out, windows):
    import numpy as np
    import torch
    from learn.direc import mrstft

    started = time.monotonic()
    torch.set_num_threads(2)
    if torch.get_default_dtype() != torch.float32:
        raise ValueError("frozen Torch default dtype changed")
    for n, saved in windows.items():
        current = torch.hann_window(n, device="cpu").numpy().astype(np.float64)
        if not np.array_equal(saved, current):
            raise ValueError("live frozen Torch window differs from saved coefficient bits")
    b, predictions = synthetic_cases()
    rows = []
    for i, a in enumerate(predictions):
        R.check_time(started)
        score = P.mrstft_numpy(a, b, windows=windows)
        reference = float(mrstft(torch.from_numpy(a)[None], torch.from_numpy(b)[None]))
        rows.append({"case": i, "numpy": score, "torch": reference,
                     "absolute_error": abs(score-reference),
                     "prediction_sha256": signal_hash(a), "target_sha256": signal_hash(b)})
    R.check_time(started)
    passed = all(r["absolute_error"] <= TOL for r in rows) and rows[0]["numpy"] < 1e-6
    R.write_new(out / "result.json", {"passed": passed, "rows": rows,
                "torch_version": torch.__version__, "numpy_version": np.__version__,
                "tolerance": TOL, "default_dtype": str(torch.get_default_dtype())})
    if not passed:
        raise ValueError("attempt-2 synthetic metric parity failed")


def numpy_replay(out, run, windows):
    """Actual helper environment vs saved CPU Torch scores, before assets."""
    import numpy as np

    started = time.monotonic()
    reference = json.loads((run / "metric/result.json").read_text())
    rows = reference.get("rows", [])
    if len(rows) != 4 or [r["case"] for r in rows] != list(range(4)):
        raise ValueError("synthetic reference coverage mismatch")
    b, predictions = synthetic_cases()
    results = []
    for i, (a, prior) in enumerate(zip(predictions, rows)):
        R.check_time(started)
        if signal_hash(a) != prior["prediction_sha256"] or signal_hash(b) != prior["target_sha256"]:
            raise ValueError("helper synthetic signals differ from CPU reference")
        value = P.mrstft_numpy(a, b, windows=windows)
        target = prior["torch"]
        if not np.isfinite(target) or target < 0:
            raise ValueError("invalid Torch reference score")
        results.append({"case": i, "numpy": value, "torch": target,
                        "absolute_error": abs(value-target)})
    R.check_time(started)
    passed = all(r["absolute_error"] <= TOL for r in results) and results[0]["numpy"] < 1e-6
    R.write_new(out / "result.json", {"passed": passed, "rows": results,
                "numpy_version": np.__version__, "tolerance": TOL,
                "metric_result_sha256": R.sha(run / "metric/result.json")})
    if not passed:
        raise ValueError("actual helper NumPy parity failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("metric", "numpy", "native", "render", "infer"))
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    required_prefix = CPU_PREFIX if args.stage in ("metric", "infer") else ROOT / ".venv"
    if Path(sys.prefix).resolve() != required_prefix.resolve():
        raise ValueError(f"stage requires explicit environment {required_prefix}")
    correction, manifest, pins = code_inputs()
    windows = load_windows(correction)
    run = args.run.resolve()
    out = stage_directory(run, args.stage, pins, manifest["attribution"])
    try:
        if args.stage == "metric":
            metric(out, windows)
        elif args.stage == "numpy":
            numpy_replay(out, run, windows)
        else:
            # BOTH runtime metric prerequisites checked before this first asset access.
            manifest, takes, asset_pins = R.frozen_inputs()
            if args.stage != "native":
                old = json.loads((run / "native/assets.json").read_text())
                if old != asset_pins:
                    raise ValueError("assets changed since native stage")
            R.write_new(out / "assets.json", asset_pins)
            if args.stage == "native":
                R.native(out, manifest, takes, windows=windows)
            elif args.stage == "render":
                R.render(out, run, manifest, takes)
            else:
                R.infer(out, run, manifest, takes, windows=windows)
    except Exception as error:
        R.write_new(out / "failure.json", {"type": type(error).__name__, "message": str(error),
                    "attribution": manifest["attribution"]})
        raise


if __name__ == "__main__":
    main()
