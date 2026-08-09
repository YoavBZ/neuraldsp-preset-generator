"""Build and query a measured response atlas.

An atlas is deliberately smaller than a search engine.  It samples the continuous
controls that are live in one fixed topology, stores the resulting fingerprints,
and answers two questions without another render:

* which sampled settings are nearest to a target; and
* which target features lie outside everything the sampled topology reached.

The renderer metadata and probe identity are part of the file.  In particular, an
atlas made by the reused Audio Unit backend says ``reproducible=False`` beside the
measurements rather than turning that fact into oral history.
"""

from __future__ import annotations

import json
import math
import pathlib
import statistics
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


SCHEMA = "response-atlas-1"

# A response atlas is about the amp/cab response, not every effect chain that can
# be placed around it.  Cab lanes, microphones, amp voicing switches and section
# switches stay exactly as the topology template chose them; these effect bypasses
# are the only choices normalized by the pilot.
TONE_EFFECT_BYPASSES = frozenset({
    "parameters/gateActive",
    "parameters/doublerActive",
    "compressor/compressorActive",
    "drive1/drive1Active",
    "drive2/drive2Active",
    "tremolo/tremoloActive",
    "reverb/reverbActive",
    "delay/delayActive",
})


class AtlasError(ValueError):
    """An atlas or atlas request that cannot be interpreted safely."""


@dataclass(frozen=True)
class AtlasMatch:
    index: int
    score: float
    settings: Dict[str, Any]
    objectives: Dict[str, Any]


def fixed_topology_seed(space, amp: str) -> Dict[Any, Any]:
    """A complete neutral seed with ``amp`` selected and effects frozen off."""
    from match.benchmark import centre_seed

    seed = centre_seed(space)
    selected = [int(index) for index, prefix in space.amp_by_index.items()
                if prefix == amp]
    if len(selected) != 1:
        available = ", ".join(sorted(set(space.amp_by_index.values()))) or "none"
        raise AtlasError(f"{amp!r} is not one amp in this space. Available: {available}")
    seed[("", "selectedAmp")] = selected[0]
    return seed


def tone_topology(values: Mapping, space, amp: str) -> Dict[Any, Any]:
    """Freeze a preset's topology and bypass non-tone effects for the atlas."""
    fixed = dict(values)
    prefix = space.amp_prefix(fixed)
    if prefix != amp:
        raise AtlasError(
            f"the topology selects {prefix or 'no recognised amp'}, not {amp}"
        )
    for dimension in space.dimensions:
        if dimension.path in TONE_EFFECT_BYPASSES:
            fixed[(dimension.module, dimension.key)] = False
    return fixed


def sampling_dimensions(space, fixed: Mapping,
                        supported: Optional[Iterable] = None):
    """Continuous, live dimensions accepted by this renderer."""
    paths = _supported_paths(supported)
    return [dimension for dimension in space.active(fixed)
            if dimension.continuous
            and (paths is None or dimension.path in paths)]


def latin_hypercube(dimensions: Sequence, samples: int,
                    seed: int) -> List[Dict[str, Any]]:
    """Deterministic Latin-hypercube overrides in human parameter units."""
    if samples < 1:
        raise AtlasError(f"samples must be at least 1, not {samples}")
    if not dimensions:
        raise AtlasError("this topology has no live continuous dimensions to sample")

    from analysis import require

    require("sampling a response atlas")
    import numpy as np

    rng = np.random.default_rng(seed)
    coordinates = np.empty((samples, len(dimensions)), dtype=np.float64)
    for column in range(len(dimensions)):
        # One point in each equal-width stratum, independently permuted per axis.
        coordinates[:, column] = (rng.permutation(samples) + rng.random(samples)) / samples

    rows: List[Dict[str, Any]] = []
    for vector in coordinates:
        values = {}
        for dimension, unit in zip(dimensions, vector):
            low, high = dimension.bounds()
            values[dimension.path] = dimension.quantise(low + float(unit) * (high - low))
        rows.append(values)
    return rows


def neutral_settings(fixed: Mapping, dimensions: Sequence) -> Dict[str, Any]:
    """The fixed topology with every sampled control at its range midpoint."""
    settings = {_path(key): value for key, value in fixed.items()}
    for dimension in dimensions:
        low, high = dimension.bounds()
        settings[dimension.path] = dimension.quantise((low + high) / 2.0)
    return settings


def build(renderer, space, probe_di, pack: str, amp: str, samples: int,
          seed: int, fixed: Optional[Mapping] = None, progress=None) -> Dict[str, Any]:
    """Render one fixed-topology Latin hypercube into an atlas document."""
    from analysis import io
    from analysis.fingerprint import fingerprint

    metadata = renderer.metadata()
    fixed = fixed_topology_seed(space, amp) if fixed is None else dict(fixed)
    if space.amp_prefix(fixed) != amp:
        raise AtlasError(f"fixed topology does not select requested amp {amp!r}")
    supported = renderer.parameter_specs()
    supported_paths = _supported_paths(supported) or set()
    fixed_render = {
        _path(key): value for key, value in fixed.items()
        if _path(key) in supported_paths
    }
    dimensions = sampling_dimensions(space, fixed, supported)
    rows = latin_hypercube(dimensions, samples, seed)

    entries = []
    for index, overrides in enumerate(rows):
        settings = dict(fixed_render)
        settings.update(overrides)
        rendered = renderer.render(probe_di, settings)
        if rendered.silent:
            raise AtlasError(
                f"sample {index} rendered digital silence; no atlas was written"
            )
        printed = fingerprint(
            io.from_samples(rendered.audio, rendered.metadata.sample_rate),
            regime="probe", excerpt_s=None,
        )
        entries.append({"settings": overrides, "fingerprint": printed.to_dict()})
        if progress is not None:
            progress(index + 1, samples)

    probe = io.from_samples(probe_di, metadata.sample_rate)
    document = {
        "schema": SCHEMA,
        "pack": pack,
        "amp": amp,
        "sample_count": samples,
        "latin_hypercube_seed": int(seed),
        "dimensions": [dimension.path for dimension in dimensions],
        "fixed_settings": fixed_render,
        "probe": {
            "sha256": probe.sha256,
            "sample_rate": probe.sample_rate,
            "channels": probe.channels,
            "duration_s": round(probe.duration_s, 4),
        },
        "renderer": metadata.as_dict(),
        "measurement_caveat": _measurement_caveat(metadata),
        "achievable_ranges": achievable_ranges(
            entry["fingerprint"] for entry in entries),
        "entries": entries,
    }
    validate(document)
    return document


def validate(document: Mapping[str, Any]) -> None:
    """Refuse a partial or ambiguously qualified atlas."""
    required = {
        "schema", "pack", "amp", "sample_count", "latin_hypercube_seed",
        "dimensions", "fixed_settings", "probe", "renderer",
        "measurement_caveat", "achievable_ranges", "entries",
    }
    allowed = required | {"build"}
    unknown = set(document) - allowed
    missing = required - set(document)
    if missing or unknown:
        raise AtlasError(
            f"atlas fields differ from {SCHEMA}: missing={sorted(missing)}, "
            f"unknown={sorted(unknown)}"
        )
    if document.get("schema") != SCHEMA:
        raise AtlasError(f"atlas schema {document.get('schema')!r}, expected {SCHEMA!r}")
    entries = document.get("entries")
    if not isinstance(entries, list) or len(entries) != document.get("sample_count"):
        raise AtlasError("sample_count does not equal the number of atlas entries")
    renderer = document.get("renderer")
    if not isinstance(renderer, Mapping) or "reproducible" not in renderer:
        raise AtlasError("atlas renderer metadata must state reproducible true or false")
    if not isinstance(renderer.get("reproducible"), bool):
        raise AtlasError("atlas renderer reproducible must be a JSON boolean")
    if renderer.get("reproducible") is False and not document.get("measurement_caveat"):
        raise AtlasError("a reproducible=False atlas must carry its measurement caveat")
    dimensions = document.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions or len(set(dimensions)) != len(dimensions):
        raise AtlasError("atlas dimensions must be a non-empty list of unique paths")
    ranges = document.get("achievable_ranges")
    if not isinstance(ranges, Mapping) or set(ranges) - set(_FEATURES):
        raise AtlasError("atlas achievable_ranges contains unknown response features")
    for name, bounds in ranges.items():
        if (not isinstance(bounds, Mapping) or set(bounds) != {"min", "max"}
                or not all(isinstance(bounds[key], (int, float)) for key in ("min", "max"))
                or not all(math.isfinite(float(bounds[key])) for key in ("min", "max"))
                or bounds["min"] > bounds["max"]):
            raise AtlasError(f"atlas achievable range {name!r} is not a finite min/max")
    for index, entry in enumerate(entries):
        if set(entry) != {"settings", "fingerprint"}:
            raise AtlasError(f"atlas entry {index} must contain settings and fingerprint")
        if set(entry["settings"]) != set(dimensions):
            raise AtlasError(f"atlas entry {index} does not set every sampled dimension")
        from analysis.fingerprint import Fingerprint

        Fingerprint.from_dict(entry["fingerprint"])
    if "build" in document and not isinstance(document["build"], Mapping):
        raise AtlasError("atlas build provenance must be an object")


def load(path) -> Dict[str, Any]:
    document = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    validate(document)
    return document


def nearest(document: Mapping[str, Any], target, profile: str = "unpaired-v1",
            limit: int = 1) -> List[AtlasMatch]:
    """Nearest stored fingerprints under the same named loss used by search."""
    if limit < 1:
        raise AtlasError(f"limit must be at least 1, not {limit}")
    validate(document)
    from analysis.compare import compare, scalar
    from analysis.fingerprint import Fingerprint

    matches = []
    for index, entry in enumerate(document["entries"]):
        objectives = compare(
            target, Fingerprint.from_dict(entry["fingerprint"]), profile=profile)
        score = scalar(objectives, profile)
        if score is None or not math.isfinite(score):
            continue
        settings = dict(document["fixed_settings"])
        settings.update(entry["settings"])
        matches.append(AtlasMatch(
            index=index, score=float(score), settings=settings,
            objectives=objectives.to_dict(),
        ))
    matches.sort(key=lambda match: (match.score, match.index))
    return matches[:limit]


def achievable_ranges(fingerprints: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Observed min/max for interpretable response features.

    These are ranges reached by this finite sample and probe, not mathematical
    bounds on the plugin.  The name is kept honest in the atlas caveat and CLI.
    """
    values: Dict[str, List[float]] = {name: [] for name in _FEATURES}
    for printed in fingerprints:
        for name, path in _FEATURES.items():
            value = _nested(printed, path)
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                values[name].append(float(value))
    return {
        name: {"min": min(rows), "max": max(rows)}
        for name, rows in values.items() if rows
    }


def outside_ranges(document: Mapping[str, Any], target) -> List[Dict[str, Any]]:
    """Target features below or above the finite atlas sample."""
    validate(document)
    printed = target.to_dict()
    outside = []
    for name, bounds in document["achievable_ranges"].items():
        value = _nested(printed, _FEATURES[name])
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            continue
        if value < bounds["min"]:
            outside.append({"feature": name, "direction": "below", "value": float(value),
                            "sampled_min": bounds["min"], "sampled_max": bounds["max"]})
        elif value > bounds["max"]:
            outside.append({"feature": name, "direction": "above", "value": float(value),
                            "sampled_min": bounds["min"], "sampled_max": bounds["max"]})
    return outside


def held_out(renderer, space, probe_di, document: Mapping[str, Any], samples: int,
             seed: int, profile: str = "unpaired-v1", progress=None) -> Dict[str, Any]:
    """Compare nearest-atlas initialization with the fixed neutral topology."""
    from analysis import io
    from analysis.compare import compare, scalar
    from analysis.fingerprint import fingerprint

    validate(document)
    fixed = dict(document["fixed_settings"])
    supported = renderer.parameter_specs()
    supported_paths = _supported_paths(supported) or set()
    fixed_render = {_path(key): value for key, value in fixed.items()
                    if _path(key) in supported_paths}
    dimensions = sampling_dimensions(space, fixed, supported)
    if [dimension.path for dimension in dimensions] != document["dimensions"]:
        raise AtlasError("held-out renderer exposes a different sampled dimension set")
    rows = latin_hypercube(dimensions, samples, seed)

    neutral = neutral_settings(fixed_render, dimensions)
    neutral_render = renderer.render(probe_di, neutral)
    if neutral_render.silent:
        raise AtlasError("the neutral held-out baseline rendered digital silence")
    neutral = fingerprint(
        io.from_samples(neutral_render.audio, neutral_render.metadata.sample_rate),
        regime="probe", excerpt_s=None,
    )

    outcomes = []
    for index, overrides in enumerate(rows):
        settings = dict(fixed_render)
        settings.update(overrides)
        rendered = renderer.render(probe_di, settings)
        if rendered.silent:
            raise AtlasError(f"held-out sample {index} rendered digital silence")
        target = fingerprint(
            io.from_samples(rendered.audio, rendered.metadata.sample_rate),
            regime="probe", excerpt_s=None,
        )
        matches = nearest(document, target, profile=profile, limit=1)
        if not matches:
            raise AtlasError(f"held-out sample {index} had no comparable atlas entry")
        neutral_score = scalar(compare(target, neutral, profile=profile), profile)
        if neutral_score is None:
            raise AtlasError(f"held-out sample {index} had no comparable neutral score")
        best = matches[0]
        outcomes.append({
            "index": index,
            "neutral_score": float(neutral_score),
            "atlas_score": best.score,
            "atlas_entry": best.index,
            "improvement_fraction": (
                0.0 if neutral_score == 0
                else float((neutral_score - best.score) / neutral_score)
            ),
        })
        if progress is not None:
            progress(index + 1, samples)

    neutral_scores = [row["neutral_score"] for row in outcomes]
    atlas_scores = [row["atlas_score"] for row in outcomes]
    wins = sum(a < n for a, n in zip(atlas_scores, neutral_scores))
    return {
        "samples": samples,
        "seed": int(seed),
        "profile": profile,
        "neutral_mean": statistics.fmean(neutral_scores),
        "atlas_mean": statistics.fmean(atlas_scores),
        "neutral_median": statistics.median(neutral_scores),
        "atlas_median": statistics.median(atlas_scores),
        "atlas_win_rate": wins / samples,
        "beats_neutral": statistics.fmean(atlas_scores) < statistics.fmean(neutral_scores),
        "outcomes": outcomes,
    }


def compare_scale(baseline: Mapping[str, Any],
                  candidate: Mapping[str, Any]) -> Dict[str, Any]:
    """Compare atlas densities only when their held-out experiment is identical.

    A lower score on a different probe, topology, plugin build, or held-out seed
    says nothing about scale.  Refusing those comparisons keeps the convenient
    command-line report from turning two merely similar runs into a learning
    curve.
    """
    validate(baseline)
    validate(candidate)
    for field in ("pack", "amp", "dimensions", "fixed_settings", "probe"):
        if baseline[field] != candidate[field]:
            raise AtlasError(f"cannot compare atlases with different {field}")
    for field in ("renderer_id", "plugin_version", "renderer_build",
                  "sample_rate", "quality_mode"):
        if baseline["renderer"].get(field) != candidate["renderer"].get(field):
            raise AtlasError(
                f"cannot compare atlases from different renderer {field}"
            )

    baseline_validation = _held_out_validation(baseline, "baseline")
    candidate_validation = _held_out_validation(candidate, "candidate")
    for field in ("samples", "seed", "profile"):
        if baseline_validation[field] != candidate_validation[field]:
            raise AtlasError(
                f"cannot compare atlases with different held-out {field}"
            )

    baseline_rows = baseline_validation["outcomes"]
    candidate_rows = candidate_validation["outcomes"]
    if [row["index"] for row in baseline_rows] != [
            row["index"] for row in candidate_rows]:
        raise AtlasError("cannot compare atlases with unaligned held-out targets")

    baseline_scores = [float(row["atlas_score"]) for row in baseline_rows]
    candidate_scores = [float(row["atlas_score"]) for row in candidate_rows]
    reductions = [
        (before - after) / before
        for before, after in zip(baseline_scores, candidate_scores)
        if before != 0.0
    ]
    baseline_mean = statistics.fmean(baseline_scores)
    candidate_mean = statistics.fmean(candidate_scores)
    return {
        "baseline_samples": baseline["sample_count"],
        "candidate_samples": candidate["sample_count"],
        "held_out_samples": baseline_validation["samples"],
        "held_out_seed": baseline_validation["seed"],
        "profile": baseline_validation["profile"],
        "baseline_atlas_mean": baseline_mean,
        "candidate_atlas_mean": candidate_mean,
        "baseline_atlas_median": statistics.median(baseline_scores),
        "candidate_atlas_median": statistics.median(candidate_scores),
        "mean_reduction_fraction": (
            None if baseline_mean == 0.0
            else (baseline_mean - candidate_mean) / baseline_mean
        ),
        "candidate_better_targets": sum(
            after < before
            for before, after in zip(baseline_scores, candidate_scores)
        ),
        "median_target_reduction_fraction": (
            statistics.median(reductions) if reductions else None
        ),
        "worst_target_reduction_fraction": min(reductions) if reductions else None,
        "baseline_measurement_caveat": baseline["measurement_caveat"],
        "candidate_measurement_caveat": candidate["measurement_caveat"],
    }


def _measurement_caveat(metadata) -> Optional[str]:
    if metadata.reproducible:
        return None
    return (
        f"renderer {metadata.renderer_id} reports reproducible=False; repeated renders "
        f"from its reused plugin instance vary by up to {metadata.band_noise_db:g} dB "
        f"per band. These are sampled observations, not bit-exact facts."
    )


def _held_out_validation(document: Mapping[str, Any], label: str) -> Mapping[str, Any]:
    build = document.get("build")
    validation = build.get("validation") if isinstance(build, Mapping) else None
    if not isinstance(validation, Mapping):
        raise AtlasError(f"{label} atlas has no held-out validation")
    required = {
        "samples", "seed", "profile", "neutral_mean", "atlas_mean",
        "neutral_median", "atlas_median", "atlas_win_rate", "beats_neutral",
        "outcomes",
    }
    if required - set(validation):
        raise AtlasError(f"{label} atlas has incomplete held-out validation")
    if (not isinstance(validation["samples"], int)
            or isinstance(validation["samples"], bool)
            or validation["samples"] < 1):
        raise AtlasError(f"{label} atlas has an invalid held-out sample count")
    if (not isinstance(validation["seed"], int)
            or isinstance(validation["seed"], bool)):
        raise AtlasError(f"{label} atlas has an invalid held-out seed")
    if not isinstance(validation["profile"], str) or not validation["profile"]:
        raise AtlasError(f"{label} atlas has an invalid held-out profile")
    rows = validation["outcomes"]
    if (not isinstance(rows, list) or not rows
            or len(rows) != validation["samples"]):
        raise AtlasError(f"{label} atlas has inconsistent held-out outcomes")
    for expected, row in enumerate(rows):
        if not isinstance(row, Mapping) or row.get("index") != expected:
            raise AtlasError(f"{label} atlas has unaligned held-out outcomes")
        for field in ("neutral_score", "atlas_score"):
            value = row.get(field)
            if (not isinstance(value, (int, float))
                    or not math.isfinite(float(value)) or value < 0):
                raise AtlasError(
                    f"{label} atlas held-out {field} is not finite and non-negative"
                )

    neutral = [float(row["neutral_score"]) for row in rows]
    scores = [float(row["atlas_score"]) for row in rows]
    expected_summaries = {
        "neutral_mean": statistics.fmean(neutral),
        "atlas_mean": statistics.fmean(scores),
        "neutral_median": statistics.median(neutral),
        "atlas_median": statistics.median(scores),
        "atlas_win_rate": sum(a < n for a, n in zip(scores, neutral)) / len(rows),
    }
    for field, expected in expected_summaries.items():
        actual = validation[field]
        if (not isinstance(actual, (int, float))
                or not math.isclose(float(actual), expected,
                                    rel_tol=1e-12, abs_tol=1e-12)):
            raise AtlasError(f"{label} atlas held-out {field} is inconsistent")
    expected_beats = (
        expected_summaries["atlas_mean"] < expected_summaries["neutral_mean"])
    if (not isinstance(validation["beats_neutral"], bool)
            or validation["beats_neutral"] != expected_beats):
        raise AtlasError(f"{label} atlas held-out beats_neutral is inconsistent")
    return validation


def _supported_paths(supported: Optional[Iterable]) -> Optional[set]:
    if supported is None:
        return None
    return {_path(key) for key in supported}


def _path(key) -> str:
    if isinstance(key, str):
        return key.lstrip("/")
    module, name = key
    return f"{module}/{name}" if module else str(name)


def _nested(document: Mapping[str, Any], path: Sequence[str]):
    value: Any = document
    for part in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


_FEATURES = {
    "spectral_tilt_db_per_decade": ("spectrum", "tilt_db_per_decade"),
    "brightness_centroid_hz": ("spectrum", "centroid_hz", "p50"),
    "high_frequency_rolloff_hz": ("spectrum", "rolloff85_hz", "p50"),
    "low_frequency_corner_hz": ("spectrum", "lf_corner_hz"),
    "high_frequency_corner_hz": ("spectrum", "hf_corner_hz"),
    "crest_db": ("dynamics", "crest_db"),
}
