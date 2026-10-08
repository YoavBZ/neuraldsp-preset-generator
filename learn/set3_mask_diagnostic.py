"""Development activity-mask case study; docs/set3-mask-diagnostic-plan.md.

Run through neuraldsp-safe python-file only after independent review and commit.
Inputs are fixed. This entry point only reads saved development artifacts; it does
not import rendering, model, training, or plugin code. B is never rescored.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import statistics
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
DATA = Path.home() / "ndsp-presets/learn/direc/phase2-set3"
CROPS = Path.home() / "ndsp-presets/references/validation-crops-set3"
METADATA = ROOT / "docs/validation-set3.json"
INVENTORY = ROOT / "docs/set3-development-diagnostic-menus.json"
DIAGNOSTIC = ROOT / "tmp/set3-development-diagnostic-20261008.json"
PLAN = ROOT / "docs/set3-mask-diagnostic-plan.md"
TARGET = "cambridge-colour-me-red-elecgtr03"
AMP = "sw50r"
BAND_SETS = ("recording", "union")
VARIANTS = ("original", "known_di", "reference")
TEMPLATE = "template+R"
SR, LATENCY = 48000, 52
HALF_A = (1.0, 5.5)
TOLERANCE = 1e-6


def raw_valid(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and value >= 0)


def choose(scores):
    eligible = [name for name, value in scores.items() if raw_valid(value)]
    return min(eligible, key=lambda name: (scores[name], name)) if eligible else None


def select_parts(metadata):
    """Fix the panel by membership/slug, without consulting any outcomes."""
    all_parts = metadata["parts"]
    slugs = [p["slug"] for p in all_parts]
    if (len(set(slugs)) != len(slugs)
            or any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", s) for s in slugs)
            or any(p["split"] not in ("development", "held_out") for p in all_parts)):
        raise ValueError("invalid or duplicate declared part membership")
    development = sorted((p for p in all_parts if p["split"] == "development"),
                         key=lambda p: p["slug"])
    bands = {p["band"] for p in development}
    reserved_bands = {p["band"] for p in all_parts if p["split"] == "held_out"}
    reserved_bands.update(metadata["held_out_bands"])
    if len(development) != 33 or len(bands) != 11 or bands & reserved_bands:
        raise ValueError("expected exactly 33 development parts in 11 unreserved bands")
    first = {}
    for part in development:
        lag = part["judge_lag_samples"]
        if isinstance(lag, bool) or not isinstance(lag, int):
            raise ValueError(f"invalid declared judge lag: {part['slug']}")
        first.setdefault(part["band"], part)
    by_slug = {p["slug"]: p for p in development}
    if TARGET not in by_slug:
        raise ValueError("known target must be in the declared development split")
    selected = {p["slug"]: p for p in first.values()}
    selected[TARGET] = by_slug[TARGET]
    if len(selected) != 12:
        raise ValueError("fixed first-per-band plus target panel must have 12 parts")
    return development, [selected[s] for s in sorted(selected)]


def validate_scores(distances, development, inventory):
    """Inventory comes from the independent frozen metadata, never score keys."""
    names = inventory["menus"][AMP]
    if (len(names) != 45 or len(set(names)) != 45 or TEMPLATE not in names
            or any(n != TEMPLATE and not n.startswith("factory:") for n in names)):
        raise ValueError("expected the frozen SW50R 45-candidate inventory")
    if set(distances) != {p["slug"] for p in development}:
        raise ValueError("scores must exactly match development membership")
    for part in development:
        for bs in BAND_SETS:
            for kind in ("net_A", "measure_A", "measure_B"):
                scores = distances[part["slug"]].get(f"{bs}|{AMP}|{kind}")
                if not isinstance(scores, dict) or set(scores) != set(names):
                    raise ValueError(f"incomplete candidate menu: {part['slug']} {bs} {kind}")
                if any(v is not None and not raw_valid(v) for v in scores.values()):
                    raise ValueError(f"invalid raw distance: {part['slug']} {bs} {kind}")
    return sorted(names)


def frozen_constants(diagnostic, development, distances, names):
    """Read the full-33 leave-band-out constants; never estimate new constants."""
    if diagnostic["parts"] != 33 or diagnostic["bands"] != 11:
        raise ValueError("constants must come from the full 33-part diagnostic")
    bands = {p["band"] for p in development}
    part_bands = {p["slug"]: p["band"] for p in development}
    result = {}
    for bs in BAND_SETS:
        cell = diagnostic["cells"][f"{bs}|{AMP}"]
        if cell["parts"] != 33 or cell["bands"] != 11 or cell["menu_size"] != 45:
            raise ValueError("diagnostic cell inventory changed")
        rows = cell["rows"]
        if len(rows) != 33 or {r["part"] for r in rows} != set(part_bands):
            raise ValueError("diagnostic rows must exactly cover development")
        for row in rows:
            slug = row["part"]
            scores = distances[slug]
            cached_pick = choose(scores[f"{bs}|{AMP}|net_A"])
            cached_B = scores[f"{bs}|{AMP}|measure_B"].get(cached_pick)
            if (row["band"] != part_bands[slug]
                    or row["picks"]["rebuilt_di"] != cached_pick
                    or row["B"]["rebuilt_di"] != cached_B):
                raise ValueError(f"diagnostic original selection disagrees: {slug} {bs}")
        result[bs] = {}
        for label, field in (("constant", "constants_by_excluded_band"),
                             ("inclusive_constant", "inclusive_constants_by_excluded_band")):
            audits = cell[field]
            if set(audits) != bands:
                raise ValueError("constant exclusions must cover all development bands")
            for band, audit in audits.items():
                expected = {p["slug"] for p in development if p["band"] != band}
                if (set(audit["training_parts"]) != expected
                        or len(audit["training_parts"]) != len(expected)
                        or audit["preset"] not in names
                        or (label == "constant" and audit["preset"] == TEMPLATE)):
                    raise ValueError(f"invalid full-development constant: {bs} {band} {label}")
            result[bs][label] = audits
    return result


def known_di_proxy(measure_di, judge_lag_samples, length):
    """proxy[t] = measure_di[t - (judge_lag_samples + 52)], zero padded."""
    import numpy as np

    if isinstance(judge_lag_samples, bool) or not isinstance(judge_lag_samples, int):
        raise ValueError("judge lag must be an integer number of samples")
    source = np.asarray(measure_di, dtype=np.float64)
    if source.ndim != 1 or not len(source) or not np.all(np.isfinite(source)):
        raise ValueError("measure DI must be finite, nonempty mono")
    if length < 1:
        raise ValueError("proxy length must be positive")
    raw_lag = judge_lag_samples + LATENCY
    out = np.zeros(length, dtype=np.float64)
    lo, hi = max(0, raw_lag), min(length, len(source) + raw_lag)
    if hi > lo:
        out[lo:hi] = source[lo - raw_lag:hi - raw_lag]
    return out


def measure_A(recording, render, proxy, bs, distance_fn=None):
    """Only the third positional argument varies; all judge defaults stay frozen."""
    if distance_fn is None:
        from analysis.aligned import aligned_distance

        distance_fn = aligned_distance
    value = distance_fn(recording, render, proxy, lag=-LATENCY, render_latency=LATENCY,
                        sample_rate=SR, start_s=HALF_A[0], end_s=HALF_A[1], bands=bs).as_dict()
    if value["distance"] is not None and not raw_valid(value["distance"]):
        raise ValueError("aligned primitive returned an invalid distance")
    if value["distance"] is None and not value.get("reason"):
        raise ValueError("aligned refusal must have a reason")
    return value


def baseline_comparison(cached, measured, saved_B):
    if set(cached) != set(measured):
        raise ValueError("baseline candidate inventory differs")
    comparisons = {}
    for name in sorted(cached):
        expected, actual = cached[name], measured[name]["distance"]
        null_match = (expected is None) == (actual is None)
        delta = abs(actual - expected) if actual is not None and expected is not None else None
        comparisons[name] = {"cached": expected, "recomputed": actual,
                             "null_state_matches": null_match, "absolute_error": delta,
                             "matches": null_match and (delta is None or delta <= TOLERANCE),
                             "reason": measured[name].get("reason")}
    original = choose(cached)
    recomputed = choose({n: v["distance"] for n, v in measured.items()})
    return {"candidates": comparisons, "cached_pick": original, "recomputed_pick": recomputed,
            "cached_chosen_B": saved_B.get(original), "recomputed_chosen_B": saved_B.get(recomputed),
            "pick_matches_exactly": original == recomputed,
            "matches": original == recomputed and all(v["matches"] for v in comparisons.values())}


def require_baseline(baseline):
    failed = [f"{bs}:{slug}" for bs, parts in baseline.items()
              for slug, audit in parts.items() if not audit["matches"]]
    if failed:
        raise ValueError("original baseline reproduction disagreement: " + ", ".join(failed))


def paired(numerator, denominator):
    """Raw zero comparisons remain valid; nonpositive logs are reported separately."""
    if not raw_valid(numerator) or not raw_valid(denominator):
        return {"raw": None, "log_ratio": None, "ratio": None, "failure": "refusal"}
    raw = "win" if numerator < denominator else "loss" if numerator > denominator else "tie"
    if numerator <= 0 or denominator <= 0:
        return {"raw": raw, "log_ratio": None, "ratio": None, "failure": "nonpositive_log"}
    effect = math.log(numerator) - math.log(denominator)
    # Very large valid distances can have an unrepresentable ratio, but a valid log.
    try:
        ratio = math.exp(effect)
    except OverflowError:
        ratio = None
    return {"raw": raw, "log_ratio": effect, "ratio": ratio, "failure": None}


def summarize_pairs(rows, numerator, denominator):
    pairs = {r["part"]: paired(r["B"][numerator], r["B"][denominator]) for r in rows}
    band_medians = {}
    for band in sorted({r["band"] for r in rows}):
        values = [pairs[r["part"]]["log_ratio"] for r in rows if r["band"] == band
                  and pairs[r["part"]]["log_ratio"] is not None]
        band_medians[band] = statistics.median(values) if values else None
    effects = [p["log_ratio"] for p in pairs.values() if p["log_ratio"] is not None]
    available = [v for v in band_medians.values() if v is not None]
    return {"paired": pairs, "required_parts": len(rows), "scorable_log_parts": len(effects),
            "raw_counts": {kind: sum(p["raw"] == kind for p in pairs.values())
                           for kind in ("win", "loss", "tie")},
            "refused_parts": [s for s, p in pairs.items() if p["failure"] == "refusal"],
            "nonpositive_log_parts": [s for s, p in pairs.items() if p["failure"] == "nonpositive_log"],
            "median_log_ratio": statistics.median(effects) if effects else None,
            "band_medians": band_medians,
            "median_of_band_medians": statistics.median(available) if available else None,
            "descriptive_only": True}


def routing_gate(rows):
    """The target never contributes an improvement to the fixed control count."""
    target = next(r for r in rows if r["part"] == TARGET)
    controls = [r for r in rows if r["part"] != TARGET]
    changes = {r["part"]: paired(r["B"]["reference"], r["B"]["original"]) for r in controls}
    improved = [s for s, p in changes.items() if p["raw"] == "win"]
    worse = [s for s, p in changes.items() if p["raw"] == "loss"]
    new_missing = [r["part"] for r in controls
                   if r["picks"]["original"] is not None and r["picks"]["reference"] is None]
    missing_B = [r["part"] for r in controls
                 if not all(raw_valid(r["B"][v]) for v in ("original", "reference"))]
    gates = {"target_refusal_rescued": target["picks"]["original"] is None
             and target["picks"]["reference"] is not None,
             "target_rescued_B_raw_valid": raw_valid(target["B"]["reference"]),
             "all_11_control_B_pairs_raw_valid": len(controls) == 11 and not missing_B,
             "no_control_new_missing_selection": not new_missing,
             "at_least_three_improved_controls": len(improved) >= 3,
             "at_most_one_worse_control": len(worse) <= 1}
    return {"gates": gates, "eligible": all(gates.values()), "improved_controls": improved,
            "worse_controls": worse, "new_missing_control_selections": new_missing,
            "invalid_control_B_pairs": missing_B,
            "ties": [s for s, p in changes.items() if p["raw"] == "tie"],
            "unpaired_controls": [s for s, p in changes.items() if p["raw"] is None],
            "nonpositive_log_controls": [s for s, p in changes.items()
                                         if p["failure"] == "nonpositive_log"]}


def assemble(parts, distances, scored, constants):
    cells = {}
    for bs in BAND_SETS:
        rows = []
        for part in parts:
            slug, band = part["slug"], part["band"]
            b = distances[slug][f"{bs}|{AMP}|measure_B"]
            candidates = {v: scored[v][bs][slug] for v in VARIANTS}
            picks = {v: choose({n: d["distance"] for n, d in values.items()})
                     for v, values in candidates.items()}
            picks.update({label: audits[band]["preset"] for label, audits in constants[bs].items()})
            picks["template"] = TEMPLATE
            picks["true_di"] = choose(distances[slug][f"{bs}|{AMP}|measure_A"])
            rows.append({"part": slug, "band": band, "picks": picks,
                         "B": {label: b.get(name) for label, name in picks.items()},
                         "selection_changed": {v: picks[v] != picks["original"]
                                               for v in VARIANTS if v != "original"},
                         "candidate_A": candidates,
                         "refusals_A": {v: {n: d["reason"] for n, d in values.items()
                                            if d["distance"] is None} for v, values in candidates.items()},
                         "zero_A": {v: [n for n, d in values.items() if d["distance"] == 0]
                                    for v, values in candidates.items()},
                         "refused_saved_B_candidates": [n for n, d in b.items() if d is None],
                         "zero_saved_B_candidates": [n for n, d in b.items() if d == 0]})
        contrasts = [(v, base) for v in VARIANTS
                     for base in ("constant", "inclusive_constant", "template", "true_di")]
        contrasts += [("known_di", "original"), ("reference", "original"), ("reference", "known_di")]
        cells[bs] = {"rows": rows, "constants_from_full_33": constants[bs],
                     "comparisons": {f"{n}_vs_{d}": summarize_pairs(rows, n, d) for n, d in contrasts},
                     "gate": routing_gate(rows),
                     "missing_selections": {v: [r["part"] for r in rows if r["picks"][v] is None]
                                            for v in VARIANTS},
                     "known_di_target_refusal_rescued": any(
                         r["part"] == TARGET and r["picks"]["original"] is None
                         and r["picks"]["known_di"] is not None for r in rows)}
    return {"cells": cells, "reference_eligible_for_separately_declared_all_development_check":
            all(cell["gate"]["eligible"] for cell in cells.values())}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def note(report, message):
    report["log"].append({"at_utc": datetime.now(timezone.utc).isoformat(), "message": message})
    print(message, flush=True)


def source_json(path, report, label):
    regular_source(path, DATA if path.is_relative_to(DATA) else ROOT)
    raw = path.read_bytes()
    report["inputs"][label] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
    return json.loads(raw)


def regular_source(path, boundary):
    """Reject redirects outside the fixed split, including directory symlinks."""
    path, boundary = path.absolute(), boundary.absolute()
    if not path.is_relative_to(boundary) or path.resolve() != path:
        raise ValueError(f"source must stay in its fixed development location: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"missing required development source: {path}")
    return path


def asset_inventory(parts, names):
    assets, missing = {}, []
    for part in parts:
        slug = part["slug"]
        files = {"reference": CROPS / slug / "reference.wav",
                 "net_di": DATA / "net" / slug / "di.npy",
                 "measure_di": DATA / "measure" / slug / "di.npy",
                 "net_done": DATA / "net" / slug / "done",
                 "measure_done": DATA / "measure" / slug / "done"}
        for name in names:
            # Exactly research.render_preset_panel._slug, without importing its renderer imports.
            stem = hashlib.sha1(name.encode()).hexdigest()[:12]
            path = DATA / "net" / slug / AMP / f"{stem}.wav"
            if not path.exists() and not path.is_symlink():
                path = path.with_suffix(".flac")
            files[f"render:{name}"] = path
        assets[slug] = files
        for path in files.values():
            try:
                regular_source(path, CROPS if path.is_relative_to(CROPS) else DATA)
            except (OSError, ValueError) as exc:
                missing.append(str(exc))
    if missing:
        raise FileNotFoundError("incomplete fixed development sources:\n" + "\n".join(missing))
    return assets


def read_array(path):
    import numpy as np

    x = np.load(path, allow_pickle=False)
    if x.ndim != 1 or not len(x) or not np.all(np.isfinite(x)):
        raise ValueError(f"saved DI must be finite nonempty mono: {path}")
    return x


def read_audio(path):
    import numpy as np
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    if sr != SR or not len(x) or not np.all(np.isfinite(x)):
        raise ValueError(f"expected finite nonempty 48 kHz audio: {path}")
    return x.mean(axis=1)


def score_stage(parts, names, assets, variants, report):
    scored = {v: {bs: {} for bs in BAND_SETS} for v in variants}
    for part in parts:
        slug = part["slug"]
        note(report, f"scoring {','.join(variants)}: {slug}")
        files = assets[slug]
        ref = read_audio(files["reference"])
        proxies = {}
        if "original" in variants:
            proxies["original"] = read_array(files["net_di"])
        if "known_di" in variants:
            proxies["known_di"] = known_di_proxy(read_array(files["measure_di"]),
                                                part["judge_lag_samples"], len(ref))
        if "reference" in variants:
            proxies["reference"] = ref
        for variant in variants:
            for bs in BAND_SETS:
                scored[variant][bs][slug] = {}
        # Retain partial candidate results if a later file or score fails.
        report.setdefault("scored_A", {}).update(scored)
        for name in names:
            render = read_audio(files[f"render:{name}"])
            for variant in variants:
                for bs in BAND_SETS:
                    scored[variant][bs][slug][name] = measure_A(ref, render, proxies[variant], bs)
    return scored


def run(report):
    note(report, "validating fixed development metadata and provenance")
    metadata = source_json(METADATA, report, "metadata")
    development, selected = select_parts(metadata)
    distances = source_json(DATA / "distances.json", report, "distances")
    inventory = source_json(INVENTORY, report, "menu_inventory")
    diagnostic = source_json(DIAGNOSTIC, report, "full_development_diagnostic")
    names = validate_scores(distances, development, inventory)
    for label in ("metadata", "distances", "menu_inventory"):
        if diagnostic["inputs"][label] != report["inputs"][label]:
            raise ValueError(f"reviewed diagnostic source provenance changed: {label}")
    constants = frozen_constants(diagnostic, development, distances, names)
    code_paths = {"script": Path(__file__), "tests": ROOT / "tests/test_set3_mask_diagnostic.py",
                  "plan": PLAN, "aligned": ROOT / "analysis/aligned.py",
                  "analysis_io": ROOT / "analysis/io.py", "analysis_init": ROOT / "analysis/__init__.py",
                  "source_scoring": ROOT / "learn/phase2_set3.py",
                  "source_render_names": ROOT / "research/render_preset_panel.py",
                  "source_diagnostic_code": ROOT / "learn/set3_diagnostic.py"}
    for label, path in code_paths.items():
        report["inputs"][label] = {"path": str(path), "sha256": digest(path)}
    if diagnostic["inputs"]["script"] != report["inputs"]["source_diagnostic_code"]:
        raise ValueError("full-development diagnostic implementation changed")
    report["panel"] = [{"slug": p["slug"], "band": p["band"],
                        "judge_lag_samples": p["judge_lag_samples"],
                        "known_di_raw_shift_samples": p["judge_lag_samples"] + LATENCY}
                       for p in selected]
    report["candidate_inventory"] = names
    report["constants_from_full_33"] = constants
    assets = asset_inventory(selected, names)
    report["selected_sources"] = {slug: {label: {"path": str(path), "sha256": digest(path)}
                                        for label, path in files.items()} for slug, files in assets.items()}
    note(report, "reproducing ALL original A scores before either alternative")
    scored = score_stage(selected, names, assets, ("original",), report)
    baseline = {bs: {p["slug"]: baseline_comparison(
        distances[p["slug"]][f"{bs}|{AMP}|net_A"], scored["original"][bs][p["slug"]],
        distances[p["slug"]][f"{bs}|{AMP}|measure_B"]) for p in selected} for bs in BAND_SETS}
    report["original_baseline_comparisons"] = baseline
    require_baseline(baseline)
    note(report, "baseline reproduced; scoring known-DI and reference activity proxies")
    scored.update(score_stage(selected, names, assets, ("known_di", "reference"), report))
    report.update(assemble(selected, distances, scored, constants))
    # Changes during the run invalidate the report instead of becoming exclusions.
    for entry in report["inputs"].values():
        if digest(Path(entry["path"])) != entry["sha256"]:
            raise ValueError(f"source changed during execution: {entry['path']}")
    for files in report["selected_sources"].values():
        for entry in files.values():
            path = Path(entry["path"])
            regular_source(path, CROPS if path.is_relative_to(CROPS) else DATA)
            if digest(path) != entry["sha256"]:
                raise ValueError(f"selected source changed during execution: {path}")
    report["status"] = "complete"
    note(report, "completed descriptive fixed-panel diagnostic")


def output_path(value):
    path = Path(value).expanduser().absolute()
    boundary = (ROOT / "tmp").resolve()
    if (path.resolve() != path or not path.is_relative_to(boundary)
            or path == boundary or path.exists() or path.is_symlink()):
        raise ValueError("output must be a new regular file under project tmp/")
    return path


def execute(output):
    """Reserve output exclusively and preserve the failure log, including preflight errors."""
    output = output_path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"status": "running", "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "exploratory development mask case study; no generalization or product claim",
              "inputs": {}, "log": [], "runtime": {"python": sys.version, "executable": sys.executable},
              "configuration": {"amp": AMP, "band_sets": BAND_SETS, "half_A_seconds": HALF_A,
                                "chooser_lag_samples": -LATENCY, "render_latency": LATENCY,
                                "baseline_absolute_tolerance": TOLERANCE, "workers": 1,
                                "reference_proxy_source": "isolated amp-track reference.wav",
                                "proxy_dependent_cells": ["activity", "tails", "level offset",
                                                          "downstream band support", "residual centering"],
                                "B": "unchanged saved measure_B on [5.5,10) at original judge lag"},
              "limits": ["Independent review and commit are required before execution.",
                         "Known-DI proxy is an unavailable-input control.",
                         "Proxy changes activity, tails, offset cells, downstream band support and residual centering; rules stay fixed but selected bands may differ.",
                         "Rendered waveforms and lag stay fixed across proxies.",
                         "Reference activity can mistake effects, distortion or bleed for playing.",
                         "Reference proxy uses an isolated amp-track reference; transfer to mixes or separated stems is untested.",
                         "B is evaluated from saved original measure_B, not the modified primitive.",
                         "Eligibility requires raw-valid B for both choices on all 11 controls and the rescued target; zero is raw-valid but log-unscorable.",
                         "Available-case effects are descriptive; refusals and zeros remain explicit.",
                         "Passing only permits a separately declared all-development check.",
                         "No tuning, training or release follows this panel alone; fresh reserved confirmation and heavier-tone listening remain necessary."]}
    with output.open("x") as stream:
        try:
            for package in ("numpy", "scipy", "soundfile", "pyloudnorm"):
                report["runtime"][package] = importlib.metadata.version(package)
            run(report)
        except BaseException as exc:
            report["status"] = "execution_error"
            report["error"] = {"type": type(exc).__name__, "message": str(exc),
                               "traceback": traceback.format_exc()}
            note(report, f"execution failed; preserving report at {output}: {exc}")
            raise
        finally:
            report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new report path under project tmp/")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    execute(args.out)


if __name__ == "__main__":
    main()
