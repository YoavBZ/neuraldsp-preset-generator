"""Staged, bounded frozen-model P2 pilot; see docs/di-domain-pilot-plan.md.

metric and infer need the existing CPU torch environment. Native and render use
the project environment. No subprocess interpreter switching or package installs.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
from learn import di_domain_pilot as P

INPUTS = ROOT / "docs/di-domain-pilot-inputs.json"
PLAN = ROOT / "docs/di-domain-pilot-plan.md"
PINNED = (
    "docs/di-domain-pilot-inputs.json", "docs/di-domain-pilot-plan.md",
    "learn/di_domain_pilot.py", "learn/run_di_domain_pilot.py",
    "learn/direc.py", "learn/di_robustness.py", "research/render_preset_panel.py",
    "match/renderer_au.py", "samples/Example_Clean_PR12.xml",
    "match/renderer.py", "match/__init__.py", "learn/__init__.py",
    "packs/__init__.py", "packs/loader.py", "packs/morgan/manifest.json",
    "format/__init__.py", "format/parser.py", "format/structured.py",
    "format/markers.py", "format/translate.py", "format/writer.py",
    "scripts/au_render_server.swift", "scripts/au_probe.swift", "scripts/_cli.py",
)
LIMIT = 15 * 60


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_new(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def safe_rejected_row(row):
    """Keep invalid diagnostic locations without turning them into numeric scores."""
    fields = []

    def walk(value, path):
        if isinstance(value, float) and not math.isfinite(value):
            fields.append(path)
            return None
        if isinstance(value, dict):
            return {key: walk(v, f"{path}.{key}") for key, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [walk(v, f"{path}[{i}]") for i, v in enumerate(value)]
        return value

    cleaned = walk(row, "row")
    cleaned["nonfinite_diagnostic_fields"] = fields
    return cleaned


def frozen_inputs():
    """Fail before audio/model-array access on uncommitted procedure or input drift."""
    if "**Declared:" not in PLAN.read_text():
        raise ValueError("pilot declaration is not approved and committed")
    provenance = {}
    for name in PINNED:
        committed = subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        if current != committed:
            raise ValueError(f"uncommitted frozen dependency: {name}")
        provenance[name] = hashlib.sha256(current).hexdigest()
    manifest = json.loads(INPUTS.read_text())
    for key in ("model", "average"):
        if sha(manifest[key]["path"]) != manifest[key]["sha256"]:
            raise ValueError(f"changed pinned {key}")
    catalog = json.loads(Path(manifest["catalog"]).read_text())
    selected = P.select_p2_crops(catalog, manifest["source_root"])
    declared = []
    for row in manifest["takes"]:
        value = dict(row)
        for key in ("di", "micamp"):
            value[key] = str((Path(manifest["source_root"]) / value[key]).resolve())
        declared.append(value)
    if selected != declared:
        raise ValueError("catalog selection differs from committed path/time manifest")
    provenance["catalog"] = sha(manifest["catalog"])
    provenance["git_revision"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return manifest, selected, provenance


def stage_directory(run, stage, provenance, attribution):
    run = run.resolve()
    if not run.is_relative_to((ROOT / "tmp").resolve()):
        raise ValueError("pilot outputs must stay under project tmp")
    if stage == "metric":
        run.mkdir(parents=True, exist_ok=False)
    else:
        metric = json.loads((run / "metric/result.json").read_text())
        if metric["passed"] is not True:
            raise ValueError("synthetic torch/NumPy parity prerequisite failed")
        old = json.loads((run / "metric/provenance.json").read_text())
        if old["pins"] != provenance:
            raise ValueError("procedure changed since metric preflight")
    output = run / stage
    output.mkdir(exist_ok=False)
    write_new(output / "provenance.json", {
        "pins": provenance, "attribution": attribution,
        "python": sys.version, "started_unix": time.time(),
        "packages": {name: package_version(name) for name in ("numpy", "scipy", "soundfile", "torch")},
    })
    return output


def package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def check_time(start):
    if time.monotonic() - start > LIMIT:
        raise TimeoutError("15-minute stage budget exceeded; partial evidence retained")


def progress(output, value):
    with (output / "progress.jsonl").open("a") as f:
        f.write(json.dumps(value, allow_nan=False) + "\n")
    print(json.dumps(value, allow_nan=False), flush=True)


def require_report(path, flag, takes):
    report = json.loads(Path(path).read_text())
    slugs = [r["slug"] for r in report.get("rows", [])]
    if (report.get("complete") is not True or report.get(flag) is not True
            or len(slugs) != 12 or len(set(slugs)) != 12
            or set(slugs) != {r["slug"] for r in takes}):
        raise ValueError(f"complete, valid declared coverage required: {path}")
    return report


def repeat_canary(first, repeat):
    """Band/RMS drift, not sample identity: reused Morgan has measured variation."""
    import numpy as np

    a, b = np.asarray(first, np.float64), np.asarray(repeat, np.float64)
    if (a.shape != (P.SCORE,) or b.shape != a.shape
            or not np.isfinite(a).all() or not np.isfinite(b).all()
            or min(float(np.std(a)), float(np.std(b))) < 1e-5):
        raise ValueError("invalid repeatability canary audio")
    frequencies = np.fft.rfftfreq(P.SCORE, 1 / P.SR)
    window = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(P.SCORE) / P.SCORE)
    edges = (80, 160, 320, 640, 1280, 2560, 4000)
    powers = []
    for x in (a, b):
        spectrum = np.abs(np.fft.rfft(x * window)) ** 2
        powers.append([float(spectrum[(frequencies >= lo) &
                                     ((frequencies <= hi) if hi == edges[-1] else (frequencies < hi))].sum())
                       for lo, hi in zip(edges[:-1], edges[1:])])
    if max(powers[0]) <= 0:
        raise ValueError("repeatability canary has zero reference band power")
    active = [i for i, value in enumerate(powers[0]) if value >= max(powers[0]) * 1e-4]
    if not active:
        raise ValueError("repeatability canary has no active declared bands")
    rms_drift = float(20 * np.log10(np.sqrt(np.mean(b**2)) / np.sqrt(np.mean(a**2))))
    all_drift = [float(10 * np.log10(second / first)) if first > 0 and second > 0 else None
                 for first, second in zip(powers[0], powers[1])]
    drift = [all_drift[i] for i in active]
    return {"passed": abs(rms_drift) <= 1 and all(v is not None and abs(v) <= 1 for v in drift),
            "rms_drift_db": rms_drift, "active_band_indices": active,
            "band_drift_db": all_drift, "first_band_power": powers[0], "repeat_band_power": powers[1],
            "band_edges_hz": list(edges), "limit_db": 1,
            "waveform_max_absolute_difference": float(np.max(np.abs(a-b))),
            "waveform_relative_rms_difference": float(np.sqrt(np.mean((a-b)**2)/np.mean(a**2))),
            "first_hash": hashlib.sha256(a.tobytes()).hexdigest(),
            "repeat_hash": hashlib.sha256(b.tobytes()).hexdigest()}


def metric(output):
    import numpy as np
    import torch
    from learn.direc import mrstft

    torch.set_num_threads(2)
    rng = np.random.default_rng(20261008)
    b = rng.normal(size=3 * P.SR) * 0.1
    signals = [b.copy(), b * 0.5, np.roll(b, 52), np.zeros_like(b)]
    rows = []
    for a in signals:
        native = P.mrstft_numpy(a, b)
        reference = float(mrstft(torch.from_numpy(a)[None], torch.from_numpy(b)[None]))
        rows.append({"numpy": native, "torch": reference, "absolute_error": abs(native-reference)})
    passed = all(r["absolute_error"] <= 1e-8 for r in rows) and rows[0]["numpy"] < 1e-6
    write_new(output / "result.json", {"passed": passed, "rows": rows,
              "torch": torch.__version__, "numpy_version": np.__version__})
    if not passed:
        raise ValueError("synthetic metric parity failed")


def native(output, manifest, takes, *, windows=None):
    import numpy as np

    P._validate_windows(windows)
    window_args = {} if windows is None else {"windows": windows}
    started = time.monotonic()
    average = np.load(manifest["average"]["path"], allow_pickle=False)
    rows = []
    for take in takes:
        check_time(started)
        row = {k: take[k] for k in ("slug", "content", "take")}
        try:
            raw = P.read_bounded(take["di"], take["start_frame"])
            wet_raw = P.read_bounded(take["micamp"], take["start_frame"])
            row["excerpt_hashes"] = {
                "di_float64_mono": hashlib.sha256(raw.tobytes()).hexdigest(),
                "wet_float64_mono": hashlib.sha256(wet_raw.tobytes()).hexdigest(),
            }
            calibration = P.calibrate(raw, wet_raw, take["lag_samples"])
            di, wet = P.align_pair(raw, wet_raw, calibration)
            row["calibration"] = asdict(calibration)
            row["qc"] = P.pair_qc(di, wet)
            row["qc_valid"] = row["qc"]["valid"]
            if not row["qc_valid"]:
                raise ValueError("native pair QC failed")
            d, w = di[P.CALIBRATION:], wet[P.CALIBRATION:]
            target = P.canonical_target(d, average)
            flat = P.canonical_target(w, average)
            fir = P.fit_calibration_fir(wet[:P.CALIBRATION], di[:P.CALIBRATION])
            # Prediction context stays inside 4..10 s; no true outer audio is used.
            fir_prediction = P.predict_fir(np.pad(w, P.GUARD, mode="reflect"), fir,
                                           start_frame=P.GUARD, frames=P.SCORE)
            row["native_input_scores"] = P.score_prediction(w, target, d, **window_args)
            row["flatref_scores"] = P.score_prediction(flat, target, d, **window_args)
            row["fir_scores"] = P.score_prediction(fir_prediction, target, d, **window_args)
            oracle = P.canonical_target(d.copy(), average)
            row["oracle_scores"] = P.score_prediction(oracle, target, d, **window_args)
            row["oracle"] = row["oracle_scores"]["primary"]
            if row["oracle"] >= 1e-6:
                raise ValueError("target-processing metric oracle failed")
            for key in ("native_input_scores", "flatref_scores", "fir_scores", "oracle_scores"):
                if not all(np.isfinite(value) and value >= 0 for value in row[key].values()):
                    raise ValueError("invalid native preflight loss")
            if min(row["native_input_scores"]["primary"], row["flatref_scores"]["primary"],
                   row["native_input_scores"]["raw_lowband"]) <= 0:
                raise ValueError("native baseline denominator must be positive")
            with (output / f"{take['slug']}.npz").open("xb") as f:
                np.savez_compressed(f, di=d, wet=w, target=target, flatref=flat,
                                    fir=fir_prediction, render_di=di[2*P.SR:],
                                    fir_taps=fir.taps, fir_intercept=fir.intercept)
        except ValueError as error:
            row["error"] = str(error)
            row["qc_valid"] = False
            row = safe_rejected_row(row)
        rows.append(row)
        progress(output, row)
    check_time(started)
    valid = len(rows) == 12 and all(r["qc_valid"] for r in rows)
    write_new(output / "result.json", {"complete": True, "valid": valid, "rows": rows,
              "attribution": manifest["attribution"], "elapsed_seconds": time.monotonic()-started})


def render(output, run, manifest, takes):
    require_report(run / "native/result.json", "valid", takes)
    import numpy as np
    import render_preset_panel as RP
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    started = time.monotonic()

    class Renderer(AudioUnitRenderer):
        command = None

        def _state_command(self, settings):
            return self.command

    host = output / "au-host"
    host.mkdir(exist_ok=False)
    renderer = Renderer("morgan", process_policy="reuse", workdir=host)
    rows = []
    try:
        select, edits = RP.preset_edits(ROOT / manifest["preset"], load_pack("morgan"), renderer, "pr12", True)
        renderer.command = {"selectAmp": select, "edits": edits}
        for index, take in enumerate(takes):
            check_time(started)
            with np.load(run / "native" / f"{take['slug']}.npz", allow_pickle=False) as saved:
                # 2 s pre-roll + 6 s evaluation + fixed-latency guard.
                di = np.pad(saved["render_di"], (0, 52))
            if index == 0:
                renderer.render(di.astype(np.float32), {})
            rendered = renderer.render(di.astype(np.float32), {})
            renderer_identity = rendered.metadata.as_dict()
            y = np.asarray(rendered.audio, np.float64)
            y = y.mean(axis=1) if y.ndim == 2 else y
            if len(y) != len(di) or not np.isfinite(y).all():
                raise ValueError("invalid Morgan render")
            if index == 0:
                repeated = renderer.render(di.astype(np.float32), {})
                repeat_identity = repeated.metadata.as_dict()
                repeat = np.asarray(repeated.audio, np.float64)
                repeat = repeat.mean(axis=1) if repeat.ndim == 2 else repeat
                if repeat.shape != y.shape:
                    raise ValueError("Morgan repeatability shape changed")
                center = 2 * P.SR + 52
                canary = repeat_canary(y[center:center+P.SCORE], repeat[center:center+P.SCORE])
                canary["first_renderer_metadata"] = renderer_identity
                canary["repeat_renderer_metadata"] = repeat_identity
                canary["same_renderer_identity"] = renderer_identity == repeat_identity
                write_new(output / "repeatability.json", canary)
                with (output / "repeatability-audio.npz").open("xb") as f:
                    np.savez_compressed(f, first=y, repeat=repeat)
                if not canary["passed"] or not canary["same_renderer_identity"]:
                    raise ValueError("Morgan repeatability control failed")
            start = 2 * P.SR
            net_input, baseline = y[start:start+P.SCORE], y[start+52:start+52+P.SCORE]
            if float(np.std(net_input)) < 1e-5:
                raise ValueError("silent Morgan control")
            with (output / f"{take['slug']}.npz").open("xb") as f:
                np.savez_compressed(f, net_input=net_input, baseline=baseline)
            row = {"slug": take["slug"], "render_peak": float(np.max(np.abs(y))),
                   "render_hash": hashlib.sha256(y.tobytes()).hexdigest(),
                   "renderer_metadata": renderer_identity}
            rows.append(row)
            progress(output, row)
    finally:
        renderer.close()
    check_time(started)
    write_new(output / "result.json", {"complete": True, "rows": rows,
              "attribution": manifest["attribution"], "elapsed_seconds": time.monotonic()-started})


def infer(output, run, manifest, takes, *, windows=None):
    P._validate_windows(windows)
    window_args = {} if windows is None else {"windows": windows}
    require_report(run / "render/result.json", "complete", takes)
    native_report = require_report(run / "native/result.json", "valid", takes)
    import numpy as np
    import torch
    from learn import direc as D

    by_slug = {r["slug"]: r for r in native_report["rows"]}
    started = time.monotonic()
    torch.set_num_threads(2)
    net = D.build_model().cpu()
    net.load_state_dict(torch.load(manifest["model"]["path"], map_location="cpu", weights_only=True))
    net.eval()
    rows = []
    for take in takes:
        check_time(started)
        with np.load(run / "native" / f"{take['slug']}.npz", allow_pickle=False) as saved:
            di, wet, target = saved["di"], saved["wet"], saved["target"]
        with np.load(run / "render" / f"{take['slug']}.npz", allow_pickle=False) as saved:
            morgan_input, morgan_baseline = saved["net_input"], saved["baseline"]
        native_input = P.delay_samples(wet, 52)
        native_prediction = D.rebuild(net, native_input.astype(np.float32), device=torch.device("cpu"))
        morgan_prediction = D.rebuild(net, morgan_input.astype(np.float32), device=torch.device("cpu"))
        native_scores = P.score_prediction(native_prediction, target, di, **window_args)
        morgan_scores = P.score_prediction(morgan_prediction, target, di, **window_args)
        baseline_scores = P.score_prediction(morgan_baseline, target, di, **window_args)
        previous = by_slug[take["slug"]]
        row = {k: take[k] for k in ("slug", "content", "take")}
        row.update(qc_valid=True, native_net=native_scores["primary"],
                   native_input=previous["native_input_scores"]["primary"],
                   flatref=previous["flatref_scores"]["primary"],
                   morgan_net=morgan_scores["primary"], morgan_input=baseline_scores["primary"],
                   oracle=previous["oracle"], fir_native_raw_lowband=previous["fir_scores"]["raw_lowband"],
                   native_input_raw_lowband=previous["native_input_scores"]["raw_lowband"],
                   flatref_raw_lowband=previous["flatref_scores"]["raw_lowband"],
                   native_scores=native_scores, morgan_scores=morgan_scores, morgan_baseline_scores=baseline_scores)
        with (output / f"{take['slug']}.npz").open("xb") as f:
            np.savez_compressed(f, native_prediction=native_prediction, morgan_prediction=morgan_prediction)
        rows.append(row)
        progress(output, row)
    check_time(started)
    write_new(output / "result.json", {"complete": True, "rows": rows,
              "screen": P.compare_report(rows, takes), "attribution": manifest["attribution"],
              "elapsed_seconds": time.monotonic()-started, "torch_version": torch.__version__})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("metric", "native", "render", "infer"))
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    manifest, takes, provenance = frozen_inputs()
    output = stage_directory(args.run, args.stage, provenance, manifest["attribution"])
    try:
        if args.stage == "metric":
            metric(output)
        elif args.stage == "native":
            native(output, manifest, takes)
        elif args.stage == "render":
            render(output, args.run, manifest, takes)
        else:
            infer(output, args.run, manifest, takes)
    except Exception as error:
        write_new(output / "failure.json", {"type": type(error).__name__, "message": str(error),
                  "attribution": manifest["attribution"]})
        raise


if __name__ == "__main__":
    main()
