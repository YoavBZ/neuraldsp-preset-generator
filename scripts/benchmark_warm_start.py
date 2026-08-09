#!/usr/bin/env python3
"""Tune and test a warm-start regressor against nearest-atlas lookup.

    python scripts/benchmark_warm_start.py \
      --atlas packs/morgan/response_atlas_pr12_1024.json \
      --renderer swift --tune-samples 12 --tune-seed 31 \
      --test-samples 24 --test-seed 43 --seconds 4 \
      --out runs/morgan-pr12-warm-start.json

The ridge blend is chosen on the tuning targets, then compared with nearest
lookup on a separate test set.  Rendered fingerprint distance is the gate;
parameter recovery is reported separately because plugin parameters are not
identifiable from output audio.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import shlex
import statistics
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(SCRIPT_ROOT))

from _cli import guarded, positive_float, positive_int, probe_di
from benchmark_match import _backend_caveat, _renderer
from build_response_atlas import _portable_executable

SCHEMA = "warm-start-benchmark-1"
DEFAULT_BLENDS = (0.0, 0.25, 0.5, 0.75, 1.0)
RENDERER_ID_TO_CLI = {"synthetic": "synthetic", "swift": "swift"}
RENDERER_IDENTITY_FIELDS = (
    "renderer_id", "plugin_version", "renderer_build", "sample_rate",
    "block_size", "quality_mode", "reproducible", "band_noise_db",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--atlas", required=True, type=pathlib.Path,
                        help="response atlas used to train and find nearest starts")
    parser.add_argument(
        "--renderer", choices=("synthetic", "swift"),
        help="render backend; defaults to the backend recorded by the atlas")
    parser.add_argument("--tune-samples", type=positive_int, default=12,
                        help="targets used only to select the blend (default: 12)")
    parser.add_argument("--tune-seed", type=int, default=31,
                        help="tuning Latin-hypercube seed (default: 31)")
    parser.add_argument("--test-samples", type=positive_int, default=24,
                        help="fresh targets used for the final gate (default: 24)")
    parser.add_argument("--test-seed", type=int, default=43,
                        help="test Latin-hypercube seed (default: 43)")
    parser.add_argument("--seconds", type=positive_float, default=4.0,
                        help="synthetic probe length when no DI is given (default: 4)")
    parser.add_argument("--probe-di", type=pathlib.Path,
                        help="DI used by the atlas; omitted for its synthetic probe")
    parser.add_argument("--loss-profile", default="unpaired-v1",
                        help="fingerprint distance used for the gate")
    parser.add_argument("--alpha", type=positive_float, default=0.01,
                        help="ridge penalty selected by cross-validation (default: .01)")
    parser.add_argument("--minimum-cv-r2", type=float, default=0.7,
                        help="move only controls at or above this atlas-only "
                             "out-of-fold R2 (default: .7)")
    parser.add_argument("--cv-folds", type=positive_int, default=5,
                        help="folds used to estimate control learnability (default: 5)")
    parser.add_argument("--blend", type=float, action="append", default=None,
                        help="ridge fraction from 0 (nearest) to 1 (ridge); repeat")
    parser.add_argument("--out", required=True, type=pathlib.Path,
                        help="benchmark JSON destination")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    blends = _validated_blends(
        DEFAULT_BLENDS if args.blend is None else tuple(args.blend))
    if args.tune_seed == args.test_seed:
        raise ValueError("--tune-seed and --test-seed must differ")
    if (not math.isfinite(args.minimum_cv_r2)
            or args.minimum_cv_r2 > 1.0):
        raise ValueError("--minimum-cv-r2 must be finite and no greater than 1")

    from analysis import io, require

    require("benchmarking an atlas warm start")
    from match import atlas
    from match import space as space_module
    from match.regressor import RidgeWarmStart

    atlas_document = atlas.load(args.atlas)
    prior_seeds = {int(atlas_document["latin_hypercube_seed"])}
    validation = atlas_document.get("build", {}).get("validation", {})
    if isinstance(validation, dict) and isinstance(validation.get("seed"), int):
        prior_seeds.add(validation["seed"])
    reused = prior_seeds & {args.tune_seed, args.test_seed}
    if reused:
        raise atlas.AtlasError(
            "tuning and testing seeds must not reuse prior atlas seeds: "
            + ", ".join(str(seed) for seed in sorted(reused))
        )
    space = space_module.build(atlas_document["pack"], amp=atlas_document["amp"])
    model = RidgeWarmStart(atlas_document, space, alpha=args.alpha)
    control_cv_r2 = model.cross_validated_r2(folds=args.cv_folds)
    movable_paths = tuple(path for path in atlas_document["dimensions"]
                          if control_cv_r2[path] >= args.minimum_cv_r2)
    if not movable_paths:
        raise atlas.AtlasError(
            "no atlas control meets --minimum-cv-r2; lower the threshold"
        )
    dimensions = atlas.sampling_dimensions(
        space, atlas_document["fixed_settings"])
    if [dimension.path for dimension in dimensions] != atlas_document["dimensions"]:
        raise atlas.AtlasError("current pack exposes a different atlas dimension set")

    renderer_name = args.renderer or RENDERER_ID_TO_CLI.get(
        atlas_document["renderer"].get("renderer_id"))
    if renderer_name is None:
        raise atlas.AtlasError(
            "the atlas renderer has no known CLI backend; pass --renderer explicitly"
        )
    renderer = _renderer(renderer_name, atlas_document["pack"])
    try:
        metadata = renderer.metadata()
        _require_matching_renderer(atlas_document, metadata)
        caveat = _backend_caveat(metadata)
        if caveat:
            print(f"CAUTION: {caveat}.\n", flush=True)

        di, probe_caveat = probe_di(args.probe_di, args.seconds)
        probe = io.from_samples(di, metadata.sample_rate)
        if probe.sha256 != atlas_document["probe"]["sha256"]:
            raise atlas.AtlasError(
                "benchmark probe does not match the atlas probe; use its exact "
                "--probe-di and duration"
            )
        _require_supported_dimensions(renderer, atlas_document["dimensions"])

        tune_rows = atlas.latin_hypercube(
            dimensions, args.tune_samples, args.tune_seed)
        test_rows = atlas.latin_hypercube(
            dimensions, args.test_samples, args.test_seed)
        if {_row_key(row) for row in tune_rows} & {
                _row_key(row) for row in test_rows}:
            raise atlas.AtlasError("tuning and testing contain an identical target")
    except BaseException:
        _close_renderer(renderer)
        raise
    started = time.time()
    completed = 0
    tune_renders = args.tune_samples * (1 + len(blends))

    def progress(phase: str, done: int, total: int, renders_per_target: int) -> None:
        nonlocal completed
        completed += renders_per_target
        elapsed = time.time() - started
        total_renders = tune_renders + args.test_samples * (
            2 if selected_blend == 0.0 else 3)
        rate = elapsed / completed
        remaining = max(0.0, rate * (total_renders - completed))
        print(f"  {phase} target {done}/{total} — {elapsed:.0f}s elapsed, "
              f"about {remaining:.0f}s left", file=sys.stderr, flush=True)

    selected_blend = 0.0
    try:
        tune_outcomes = _evaluate(
            renderer, di, atlas_document, model, dimensions, tune_rows, blends,
            args.loss_profile, movable_paths,
            progress=lambda done, total: progress(
                "tune", done, total, 1 + len(blends)),
        )
        tune_summaries = _summaries(tune_outcomes, blends)
        selected_blend = min(
            tune_summaries.values(), key=lambda row: (row["mean"], row["blend"])
        )["blend"]

        test_blends = ((0.0,) if selected_blend == 0.0
                       else (0.0, selected_blend))
        test_outcomes = _evaluate(
            renderer, di, atlas_document, model, dimensions, test_rows,
            test_blends, args.loss_profile,
            movable_paths,
            progress=lambda done, total: progress(
                "test", done, total, 1 + len(test_blends)),
        )
        test_summaries = _summaries(test_outcomes, test_blends)
    finally:
        _close_renderer(renderer)

    baseline = test_summaries[_blend_key(0.0)]
    selected = test_summaries[_blend_key(selected_blend)]
    reduction = (0.0 if baseline["mean"] == 0.0 else
                 (baseline["mean"] - selected["mean"]) / baseline["mean"])
    document_out = {
        "schema": SCHEMA,
        "atlas": {
            "path": str(args.atlas),
            "sha256": hashlib.sha256(args.atlas.read_bytes()).hexdigest(),
            "sample_count": atlas_document["sample_count"],
            "pack": atlas_document["pack"],
            "amp": atlas_document["amp"],
        },
        "renderer": metadata.as_dict(),
        "measurement_caveat": caveat,
        "probe": atlas_document["probe"],
        "probe_caveat": probe_caveat,
        "model": {
            "kind": "standardized-multi-output-ridge",
            "alpha": args.alpha,
            "feature_count": len(model.feature_paths),
            "parameter_count": len(model.dimensions),
            "input_clipping": "atlas feature min/max",
            "output_clipping": "manifest parameter bounds",
            "cv_folds": args.cv_folds,
            "minimum_cv_r2": args.minimum_cv_r2,
            "control_cv_r2": control_cv_r2,
            "movable_paths": list(movable_paths),
            "frozen_at_nearest_count": len(model.dimensions) - len(movable_paths),
        },
        "tuning": {
            "samples": args.tune_samples,
            "seed": args.tune_seed,
            "loss_profile": args.loss_profile,
            "blends": list(blends),
            "summaries": tune_summaries,
            "selected_blend": selected_blend,
            "outcomes": tune_outcomes,
        },
        "testing": {
            "samples": args.test_samples,
            "seed": args.test_seed,
            "loss_profile": args.loss_profile,
            "nearest": baseline,
            "selected": selected,
            "mean_reduction_fraction": reduction,
            "beats_nearest": selected_blend > 0.0 and selected["mean"] < baseline["mean"],
            "outcomes": test_outcomes,
        },
        "build": {
            "command": " ".join(shlex.quote(arg) for arg in [
                _portable_executable(), *sys.argv]),
            "python_executable": _portable_executable(),
            "argv": list(sys.argv),
        },
    }
    _validate_result(document_out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document_out, indent=2) + "\n", encoding="utf-8")

    print(f"\nwrote {args.out} in {time.time() - started:.0f}s")
    print("  tuning:")
    _print_summaries(tune_summaries, args.tune_samples)
    print(f"  selected blend {selected_blend:g} on tuning targets")
    print("  fresh test:")
    _print_summaries(test_summaries, args.test_samples)
    print(f"  mean change vs nearest: {reduction:+.1%}")
    if caveat:
        print(f"  CAUTION: {caveat}.")


def _evaluate(renderer, di, atlas_document, model, dimensions, rows, blends,
              loss_profile, movable_paths, progress):
    from analysis import io
    from analysis.compare import compare, scalar
    from analysis.fingerprint import fingerprint
    from match import atlas

    outcomes = []
    for index, overrides in enumerate(rows):
        target_settings = dict(atlas_document["fixed_settings"])
        target_settings.update(overrides)
        rendered = renderer.render(di, target_settings)
        if rendered.silent:
            raise atlas.AtlasError(f"held-out target {index} rendered silence")
        target = fingerprint(
            io.from_samples(rendered.audio, rendered.metadata.sample_rate),
            regime="probe", excerpt_s=None,
        )
        prediction = model.predict(target, blend=1.0, profile=loss_profile)
        scores = {}
        parameter_mae = {}
        candidate_order = _rotated(blends, index)
        for blend in candidate_order:
            settings = model.blend_settings(
                prediction.ridge_settings, prediction.nearest_index, blend,
                movable_paths=movable_paths)
            candidate = renderer.render(di, settings)
            if candidate.silent:
                raise atlas.AtlasError(
                    f"held-out target {index}, blend {blend:g} rendered silence"
                )
            printed = fingerprint(
                io.from_samples(candidate.audio, candidate.metadata.sample_rate),
                regime="probe", excerpt_s=None,
            )
            score = scalar(compare(target, printed, profile=loss_profile), loss_profile)
            if score is None or not math.isfinite(score):
                raise atlas.AtlasError(
                    f"held-out target {index}, blend {blend:g} was not comparable"
                )
            key = _blend_key(blend)
            scores[key] = float(score)
            parameter_mae[key] = statistics.fmean(
                abs(float(settings[dimension.path]) - float(overrides[dimension.path]))
                / (dimension.bounds()[1] - dimension.bounds()[0])
                for dimension in dimensions
            )
        outcomes.append({
            "index": index,
            "nearest_atlas_entry": prediction.nearest_index,
            "nearest_stored_score": prediction.nearest_score,
            "feature_overlap": prediction.feature_overlap,
            "clipped_feature_fraction": prediction.clipped_feature_fraction,
            "candidate_order": list(candidate_order),
            "scores": scores,
            "parameter_mae": parameter_mae,
        })
        progress(index + 1, len(rows))
    return outcomes


def _summaries(outcomes, blends):
    baseline = [row["scores"][_blend_key(0.0)] for row in outcomes]
    summaries = {}
    for blend in blends:
        key = _blend_key(blend)
        scores = [row["scores"][key] for row in outcomes]
        maes = [row["parameter_mae"][key] for row in outcomes]
        wins = sum(score < nearest for score, nearest in zip(scores, baseline))
        summaries[key] = {
            "blend": float(blend),
            "mean": statistics.fmean(scores),
            "median": statistics.median(scores),
            "parameter_mae": statistics.fmean(maes),
            "wins_vs_nearest": wins,
            "win_rate_vs_nearest": wins / len(scores),
        }
    return summaries


def _validated_blends(blends):
    if not blends:
        raise ValueError("at least one --blend is required")
    if any(not isinstance(value, (int, float)) or isinstance(value, bool)
           or not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0
           for value in blends):
        raise ValueError("every --blend must be a finite number from 0 to 1")
    values = tuple(float(value) for value in blends)
    if len(set(values)) != len(values):
        raise ValueError("--blend values must be unique")
    if 0.0 not in values:
        raise ValueError("--blend 0 is required as the nearest baseline")
    return values


def _require_matching_renderer(atlas_document, metadata) -> None:
    from match import atlas

    current = metadata.as_dict()
    recorded = atlas_document["renderer"]
    differences = [field for field in RENDERER_IDENTITY_FIELDS
                   if current.get(field) != recorded.get(field)]
    if differences:
        raise atlas.AtlasError(
            "benchmark renderer does not match atlas renderer: "
            + ", ".join(differences)
        )


def _require_supported_dimensions(renderer, dimensions) -> None:
    from match import atlas

    supported = renderer.parameter_specs()
    supported_paths = {
        path if isinstance(path, str) else "/".join(part for part in path if part)
        for path in supported
    }
    missing = [path for path in dimensions if path not in supported_paths]
    if missing:
        raise atlas.AtlasError(
            "renderer cannot drive atlas dimensions: " + ", ".join(missing)
        )


def _close_renderer(renderer) -> None:
    close = getattr(renderer, "close", None)
    if close is not None:
        close()


def _validate_result(document) -> None:
    from match import atlas

    if document.get("schema") != SCHEMA:
        raise atlas.AtlasError("warm-start benchmark has the wrong schema")
    renderer = document.get("renderer", {})
    if renderer.get("reproducible") is False and not document.get(
            "measurement_caveat"):
        raise atlas.AtlasError(
            "a reproducible=False benchmark must carry its measurement caveat"
        )
    if document["tuning"]["seed"] == document["testing"]["seed"]:
        raise atlas.AtlasError("tuning and testing must use different seeds")
    if document["tuning"]["selected_blend"] != document["testing"]["selected"]["blend"]:
        raise atlas.AtlasError("test result does not evaluate the selected blend")


def _print_summaries(summaries, samples):
    for row in summaries.values():
        label = "nearest" if row["blend"] == 0.0 else f"blend {row['blend']:g}"
        print(f"    {label:10} mean {row['mean']:.3f}, "
              f"median {row['median']:.3f}, parameter MAE "
              f"{row['parameter_mae']:.3f}, wins "
              f"{row['wins_vs_nearest']}/{samples}")


def _blend_key(value: float) -> str:
    return format(float(value), "g")


def _row_key(row) -> tuple:
    return tuple(sorted(row.items()))


def _rotated(values, offset: int) -> tuple:
    values = tuple(values)
    if not values:
        return ()
    offset %= len(values)
    return values[offset:] + values[:offset]


if __name__ == "__main__":
    guarded(main)
