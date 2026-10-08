"""Known-DI Morgan control, independent of the closed native-pairing screen.

All twelve original P2 dry takes; no microphone audio or fitted alignment.
Separate declaration and exclusive outputs. No training or interpreter switching.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from learn import di_domain_pilot as P
from learn import run_di_domain_pilot as R
from learn import run_di_domain_pilot_v2 as V

PLAN = ROOT / "docs/di-morgan-control-plan.md"
OWN_PINS = ("docs/di-morgan-control-plan.md", "learn/di_morgan_control.py",
            "tests/test_di_morgan_control.py", "scripts/_swift.py")


def code_inputs():
    if "**Declared:" not in PLAN.read_text():
        raise ValueError("known-DI control must be declared and committed")
    correction, manifest, pins = V.code_inputs()
    for name in OWN_PINS:
        data = (ROOT / name).read_bytes()
        if data != subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT):
            raise ValueError(f"uncommitted control dependency: {name}")
        pins[name] = hashlib.sha256(data).hexdigest()
    return correction, manifest, pins


def assets():
    """Validate original panel; record observed asset hashes explicitly."""
    manifest, takes, pins = R.frozen_inputs()
    for key in ("model", "average"):
        observed = R.sha(manifest[key]["path"])
        if observed != manifest[key]["sha256"]:
            raise ValueError(f"changed pinned {key}")
        pins[key] = {"path": manifest[key]["path"], "sha256": observed}
    return manifest, takes, pins


def prepare(out, manifest, takes, windows):
    import numpy as np

    P._validate_windows(windows)
    started = time.monotonic()
    average = np.load(manifest["average"]["path"], allow_pickle=False)
    rows = []
    for take in takes:
        R.check_time(started)
        row = {k: take[k] for k in ("slug", "content", "take")}
        row["qc_valid"] = False
        try:
            raw = P.read_bounded(take["di"], take["start_frame"])
            row["di_excerpt_sha256"] = V.signal_hash(raw)
            di = raw[P.GUARD:P.GUARD+P.TOTAL]
            row["qc"] = P.waveform_qc(di)
            if row["qc"]["valid"] is not True:
                raise ValueError("raw DI QC failed")
            score_di = di[P.CALIBRATION:]
            target = P.canonical_target(score_di, average)
            row["oracle_scores"] = P.score_prediction(target, target.copy(), score_di, windows=windows)
            if row["oracle_scores"]["primary"] >= 1e-6:
                raise ValueError("canonical-target oracle failed")
            with (out / f"{take['slug']}.npz").open("xb") as f:
                np.savez_compressed(f, di=score_di, target=target, render_di=di[2*P.SR:])
            row["qc_valid"] = True
        except ValueError as error:
            row["error"] = str(error)
            row = R.safe_rejected_row(row)
        rows.append(row)
        R.progress(out, row)
    R.check_time(started)
    R.write_new(out / "result.json", {"complete": True,
        "valid": len(rows) == 12 and all(r["qc_valid"] for r in rows), "rows": rows,
        "attribution": manifest["attribution"], "elapsed_seconds": time.monotonic()-started})


def compare(rows, takes):
    """Original standalone Morgan control: all12, valid oracles, median >=10%."""
    def reject(reason):
        return {"valid": False, "passed": False, "disposition": "INCONCLUSIVE", "reason": reason}

    if len(rows) != 12 or len(takes) != 12:
        return reject("require all twelve declared takes")
    try:
        expected = {t["slug"]: (t["content"], t["take"]) for t in takes}
        actual = {r["slug"]: r for r in rows}
        if (len(expected) != 12 or len(actual) != 12 or set(actual) != set(expected)
                or len({t[1] for t in expected.values()}) != 12
                or any(sum(t[0] == g for t in expected.values()) != 6 for g in ("chords", "scales"))):
            return reject("coverage or group identity differs from declaration")
        ordered = [actual[t["slug"]] for t in takes]
        for row in ordered:
            if (row["content"], row["take"]) != expected[row["slug"]] or row["qc_valid"] is not True:
                return reject("invalid identity or raw-DI QC")
            for key in ("morgan_input", "morgan_net", "oracle"):
                value = row[key]
                if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
                    return reject("invalid scalar loss")
            if row["morgan_input"] <= 0 or row["oracle"] >= 1e-6:
                return reject("invalid baseline denominator or oracle")
    except (KeyError, TypeError, ValueError):
        return reject("missing score or identity fields")
    improvement = [(r["morgan_input"]-r["morgan_net"])/r["morgan_input"] for r in ordered]
    median = statistics.median(improvement)
    passed = median >= .1 - 8*math.ulp(.1)
    return {"valid": True, "passed": passed, "disposition": "PASS" if passed else "FAIL",
        "median_relative_improvement": median,
        "strict_wins": sum(v > 0 for v in improvement),
        "group_medians": {g: statistics.median(v for r, v in zip(ordered, improvement) if r["content"] == g)
                          for g in ("chords", "scales")},
        "per_take": [{"slug": r["slug"], "relative_improvement": v} for r, v in zip(ordered, improvement)]}


def infer(out, run, manifest, takes, windows):
    prepared = R.require_report(run / "prepare/result.json", "valid", takes)
    R.require_report(run / "render/result.json", "complete", takes)
    P._validate_windows(windows)
    import numpy as np
    import torch
    from learn import direc as D

    started = time.monotonic()
    torch.set_num_threads(2)
    net = D.build_model().cpu()
    net.load_state_dict(torch.load(manifest["model"]["path"], map_location="cpu", weights_only=True))
    net.eval()
    previous = {r["slug"]: r for r in prepared["rows"]}
    rows = []
    for take in takes:
        R.check_time(started)
        with np.load(run / "prepare" / f"{take['slug']}.npz", allow_pickle=False) as saved:
            di, target = saved["di"], saved["target"]
        with np.load(run / "render" / f"{take['slug']}.npz", allow_pickle=False) as saved:
            x, baseline = saved["net_input"], saved["baseline"]
        # Raw +52 render latency is retained, exactly as in frozen-model training.
        prediction = D.rebuild(net, x.astype(np.float32), device=torch.device("cpu"))
        predicted = P.score_prediction(prediction, target, di, windows=windows)
        original = P.score_prediction(baseline, target, di, windows=windows)
        row = {k: take[k] for k in ("slug", "content", "take")}
        row.update(qc_valid=True, morgan_input=original["primary"], morgan_net=predicted["primary"],
                   oracle=previous[take["slug"]]["oracle_scores"]["primary"],
                   network_scores=predicted, input_scores=original)
        if any(not math.isfinite(v) or v < 0 for scores in (predicted, original) for v in scores.values()):
            raise ValueError("nonfinite or negative inference score")
        if row["morgan_input"] <= 0:
            raise ValueError("zero baseline denominator")
        with (out / f"{take['slug']}.npz").open("xb") as f:
            np.savez_compressed(f, prediction=prediction)
        rows.append(row)
        R.progress(out, row)
    R.check_time(started)
    R.write_new(out / "result.json", {"complete": True, "rows": rows, "screen": compare(rows, takes),
        "attribution": manifest["attribution"], "elapsed_seconds": time.monotonic()-started,
        "torch_version": torch.__version__})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("metric", "numpy", "prepare", "render", "infer"))
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    prefix = V.CPU_PREFIX if args.stage in ("metric", "infer") else ROOT / ".venv"
    if Path(sys.prefix).resolve() != prefix.resolve():
        raise ValueError(f"stage requires explicit environment {prefix}")
    correction, manifest, pins = code_inputs()
    windows = V.load_windows(correction)
    run = args.run.resolve()
    out = V.stage_directory(run, args.stage, pins, manifest["attribution"])
    try:
        if args.stage == "metric":
            V.metric(out, windows)
        elif args.stage == "numpy":
            V.numpy_replay(out, run, windows)
        else:
            # Both runtime preflights passed before any external assets/catalog.
            manifest, takes, asset_pins = assets()
            if args.stage != "prepare":
                if asset_pins != json.loads((run / "prepare/assets.json").read_text()):
                    raise ValueError("assets changed since preparation")
            R.write_new(out / "assets.json", asset_pins)
            if args.stage == "prepare":
                prepare(out, manifest, takes, windows)
            elif args.stage == "render":
                R.render(out, run, manifest, takes, source_stage="prepare")
            else:
                infer(out, run, manifest, takes, windows)
    except Exception as error:
        R.write_new(out / "failure.json", {"type": type(error).__name__, "message": str(error),
                    "attribution": manifest["attribution"]})
        raise


if __name__ == "__main__":
    main()
