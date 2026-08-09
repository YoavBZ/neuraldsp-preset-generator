"""Predict a continuous warm start from a measured response atlas.

The model is intentionally small: one deterministic, multi-output ridge fit over
the atlas's numeric fingerprint leaves.  Training when the atlas is loaded takes
less than a second at the current scale and avoids a second committed artifact
whose coefficients could silently drift away from the measurements that justify
them.

Nearest-neighbour remains part of every prediction.  ``blend=0`` is exactly the
nearest stored settings, ``blend=1`` is the ridge proposal, and values between
them let the real-plugin benchmark decide how much learned movement is useful.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from match import atlas


DEFAULT_ALPHA = 0.01
MINIMUM_FEATURE_OVERLAP = 0.5


@dataclass(frozen=True)
class WarmStartPrediction:
    settings: Dict[str, Any]
    ridge_settings: Dict[str, Any]
    blend: float
    nearest_index: int
    nearest_score: float
    feature_overlap: float
    clipped_feature_fraction: float


class RidgeWarmStart:
    """A fitted fingerprint-to-parameter ridge regression for one atlas."""

    def __init__(self, document: Mapping[str, Any], space,
                 alpha: float = DEFAULT_ALPHA) -> None:
        from analysis import require

        require("training an atlas warm-start regressor")
        import numpy as np

        atlas.validate(document)
        if document["pack"] != space.pack_id:
            raise atlas.AtlasError(
                f"atlas pack {document['pack']!r} does not match space "
                f"{space.pack_id!r}"
            )
        if (not isinstance(alpha, (int, float)) or isinstance(alpha, bool)
                or not math.isfinite(float(alpha))):
            raise atlas.AtlasError("ridge alpha must be finite")
        if float(alpha) <= 0.0:
            raise atlas.AtlasError("ridge alpha must be greater than zero")
        if len(document["entries"]) < 2:
            raise atlas.AtlasError("a warm-start regressor needs at least two entries")

        dimensions = []
        for path in document["dimensions"]:
            module, separator, key = path.partition("/")
            if not separator:
                module, key = "", module
            dimensions.append(space.by_path(module, key))

        flattened = [_numeric_leaves(entry["fingerprint"])
                     for entry in document["entries"]]
        shared = sorted(set.intersection(*(set(row) for row in flattened)))
        if not shared:
            raise atlas.AtlasError("atlas fingerprints share no numeric features")
        raw = np.asarray([[row[path] for path in shared] for row in flattened],
                         dtype=np.float64)
        spread = np.std(raw, axis=0)
        variable = spread > 1e-9
        if not np.any(variable):
            raise atlas.AtlasError("atlas fingerprints have no variable features")
        features = tuple(path for path, keep in zip(shared, variable) if keep)
        raw = raw[:, variable]

        lows = np.asarray([dimension.bounds()[0] for dimension in dimensions],
                          dtype=np.float64)
        highs = np.asarray([dimension.bounds()[1] for dimension in dimensions],
                           dtype=np.float64)
        settings = np.asarray([
            [entry["settings"][dimension.path] for dimension in dimensions]
            for entry in document["entries"]
        ], dtype=np.float64)
        if not np.all(np.isfinite(settings)):
            raise atlas.AtlasError("atlas settings must be finite for regression")
        targets = (settings - lows) / (highs - lows)

        feature_mean = np.mean(raw, axis=0)
        feature_scale = np.std(raw, axis=0)
        standard = (raw - feature_mean) / feature_scale
        target_mean = np.mean(targets, axis=0)
        penalty = float(alpha) * np.eye(standard.shape[1], dtype=np.float64)
        coefficients = np.linalg.solve(
            standard.T @ standard + penalty,
            standard.T @ (targets - target_mean),
        )

        self.document = document
        self.space = space
        self.alpha = float(alpha)
        self.dimensions = tuple(dimensions)
        self.feature_paths = features
        self.feature_mean = feature_mean
        self.feature_scale = feature_scale
        self.feature_min = np.min(raw, axis=0)
        self.feature_max = np.max(raw, axis=0)
        self.target_mean = target_mean
        self.coefficients = coefficients
        self.lows = lows
        self.highs = highs
        # Retained for atlas-only diagnostics. Re-flattening one fingerprint for
        # every feature path made five-fold validation take 34 seconds instead
        # of reusing the matrix the fit had already built.
        self._feature_matrix = raw
        self._target_matrix = targets

    def predict(self, target, blend: float = 1.0,
                profile: str = "unpaired-v1",
                minimum_overlap: float = MINIMUM_FEATURE_OVERLAP,
                movable_paths: Optional[Sequence[str]] = None,
                ) -> WarmStartPrediction:
        """Predict settings, optionally blended back toward the nearest sample."""
        import numpy as np

        blend = _fraction(blend, "blend")
        minimum_overlap = _fraction(minimum_overlap, "minimum feature overlap")
        nearest = atlas.nearest(
            self.document, target, profile=profile, limit=1)
        if not nearest:
            raise atlas.AtlasError("atlas has no fingerprint comparable to the target")
        closest = nearest[0]

        leaves = _numeric_leaves(target.to_dict())
        present = np.asarray([path in leaves for path in self.feature_paths],
                             dtype=bool)
        overlap = float(np.mean(present))
        if overlap < minimum_overlap:
            raise atlas.AtlasError(
                f"target supplies {100 * overlap:.1f}% of the regressor features; "
                f"at least {100 * minimum_overlap:.1f}% are required"
            )
        raw = np.asarray([
            leaves.get(path, self.feature_mean[index])
            for index, path in enumerate(self.feature_paths)
        ], dtype=np.float64)
        outside = present & ((raw < self.feature_min) | (raw > self.feature_max))
        clipped_fraction = (
            float(np.sum(outside) / np.sum(present)) if np.any(present) else 0.0)
        raw = np.clip(raw, self.feature_min, self.feature_max)
        unit = self.target_mean + (
            (raw - self.feature_mean) / self.feature_scale) @ self.coefficients
        unit = np.clip(unit, 0.0, 1.0)

        ridge_settings = dict(self.document["fixed_settings"])
        for index, dimension in enumerate(self.dimensions):
            ridge_value = dimension.quantise(
                self.lows[index] + unit[index] * (self.highs[index] - self.lows[index]))
            ridge_settings[dimension.path] = ridge_value
        settings = self.blend_settings(
            ridge_settings, closest.index, blend, movable_paths=movable_paths)

        return WarmStartPrediction(
            settings=settings,
            ridge_settings=ridge_settings,
            blend=blend,
            nearest_index=closest.index,
            nearest_score=closest.score,
            feature_overlap=overlap,
            clipped_feature_fraction=clipped_fraction,
        )

    def blend_settings(self, ridge_settings: Mapping[str, Any],
                       nearest_index: int, blend: float,
                       movable_paths: Optional[Sequence[str]] = None,
                       ) -> Dict[str, Any]:
        """Blend one fitted proposal with its nearest measured atlas entry."""
        blend = _fraction(blend, "blend")
        if (not isinstance(nearest_index, int) or isinstance(nearest_index, bool)
                or not 0 <= nearest_index < len(self.document["entries"])):
            raise atlas.AtlasError("nearest atlas index is out of range")
        nearest = self.document["entries"][nearest_index]["settings"]
        if isinstance(movable_paths, (str, bytes, bytearray)):
            raise atlas.AtlasError("movable paths must be a sequence of full paths")
        movable = (None if movable_paths is None else frozenset(movable_paths))
        unknown = set() if movable is None else movable - {
            dimension.path for dimension in self.dimensions}
        if unknown:
            raise atlas.AtlasError(
                "movable paths are not atlas dimensions: " + ", ".join(sorted(unknown))
            )
        settings = dict(self.document["fixed_settings"])
        for dimension in self.dimensions:
            if dimension.path not in ridge_settings:
                raise atlas.AtlasError(
                    f"ridge proposal has no value for {dimension.path}"
                )
            nearest_value = float(nearest[dimension.path])
            ridge_value = float(ridge_settings[dimension.path])
            if movable is not None and dimension.path not in movable:
                ridge_value = nearest_value
            settings[dimension.path] = dimension.quantise(
                nearest_value + blend * (ridge_value - nearest_value))
        return settings

    def cross_validated_r2(self, folds: int = 5) -> Dict[str, float]:
        """Out-of-fold parameter learnability, using only atlas measurements."""
        import numpy as np

        count = len(self.document["entries"])
        if (not isinstance(folds, int) or isinstance(folds, bool)
                or folds < 2 or folds > count // 2):
            raise atlas.AtlasError(
                f"cross-validation folds must be from 2 to {count // 2}"
            )
        raw = self._feature_matrix
        targets = self._target_matrix
        predictions = np.empty_like(targets)
        indices = np.arange(count)
        for fold in range(folds):
            held_out = indices % folds == fold
            training = ~held_out
            mean = np.mean(raw[training], axis=0)
            scale = np.std(raw[training], axis=0)
            scale = np.where(scale > 1e-9, scale, 1.0)
            standard = (raw[training] - mean) / scale
            target_mean = np.mean(targets[training], axis=0)
            penalty = self.alpha * np.eye(standard.shape[1], dtype=np.float64)
            coefficients = np.linalg.solve(
                standard.T @ standard + penalty,
                standard.T @ (targets[training] - target_mean),
            )
            predictions[held_out] = target_mean + (
                (raw[held_out] - mean) / scale) @ coefficients

        residual = np.sum((targets - predictions) ** 2, axis=0)
        total = np.sum((targets - np.mean(targets, axis=0)) ** 2, axis=0)
        if not np.all(total > 1e-12):
            constants = [dimension.path for dimension, variance in
                         zip(self.dimensions, total) if variance <= 1e-12]
            raise atlas.AtlasError(
                "cannot cross-validate constant atlas dimensions: "
                + ", ".join(constants)
            )
        scores = 1.0 - residual / total
        if not np.all(np.isfinite(scores)):
            raise atlas.AtlasError("cross-validation produced a non-finite R2")
        return {dimension.path: float(score)
                for dimension, score in zip(self.dimensions, scores)}


def _numeric_leaves(value: Any, prefix: Tuple[str, ...] = ()) -> Dict[str, float]:
    leaves: Dict[str, float] = {}
    if isinstance(value, Mapping):
        for key, child in value.items():
            leaves.update(_numeric_leaves(child, prefix + (str(key),)))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            leaves.update(_numeric_leaves(child, prefix + (str(index),)))
    elif (isinstance(value, (int, float)) and not isinstance(value, bool)
          and math.isfinite(float(value))):
        leaves["/".join(prefix)] = float(value)
    return leaves


def _fraction(value: float, name: str) -> float:
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0):
        raise atlas.AtlasError(f"{name} must be a finite number from 0 to 1")
    return float(value)
