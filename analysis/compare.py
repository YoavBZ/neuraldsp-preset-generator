"""Turn two fingerprints into named distances, and only then into one number.

`compare()` never returns a pre-collapsed scalar. "Closest timbre", "best
dynamics" and "best ambience" are genuinely different presets, and a single
score throws that choice away before anyone gets to make it — which is why the
optimiser returns a shortlist rather than a winner. Collapsing happens in
`scalar()`, from a named loss profile stored as JSON, so the weights that decide
which preset wins are tunable without touching this file.

Missing features drop out rather than counting as zero. A reference with no
measurable reverb must not make every candidate score perfectly on ambience.
"""

from __future__ import annotations

import json
import math
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .fingerprint import Fingerprint

PROFILE_PATH = pathlib.Path(__file__).with_name("loss_profiles.json")

DIMENSIONS = (
    "timbre", "dynamics", "ambience", "level",
    "harmonic", "spatial", "prior_deviation", "complexity",
)


class ProfileError(ValueError):
    """An unknown or malformed loss profile."""


@dataclass
class Objectives:
    """One distance per dimension, `None` where it could not be measured.

    Zero is identical. One is "wrong by the amount the profile calls one unit",
    which is set from what the plugin's own controls are worth — so a value near
    1 means about as wrong as flipping one switch.
    """

    values: Dict[str, Optional[float]] = field(default_factory=dict)
    detail: Dict[str, Dict[str, float]] = field(default_factory=dict)
    profile: str = "unpaired-v1"

    def __getitem__(self, key: str) -> Optional[float]:
        return self.values.get(key)

    def measured(self) -> Dict[str, float]:
        return {k: v for k, v in self.values.items() if v is not None}

    def to_dict(self) -> Dict[str, Any]:
        return {"profile": self.profile, "values": self.values, "detail": self.detail}


def load_profile(name: str = "unpaired-v1") -> Dict[str, Any]:
    """Read one named profile out of `loss_profiles.json`."""
    profiles = json.loads(PROFILE_PATH.read_text())
    if name not in profiles:
        available = ", ".join(k for k in profiles if not k.startswith("_"))
        raise ProfileError(f"unknown loss profile {name!r}. Available: {available}")
    profile = profiles[name]
    for required in ("weights", "scales"):
        if required not in profile:
            raise ProfileError(f"profile {name!r} has no {required!r}")
    return profile


def list_profiles() -> List[str]:
    return [k for k in json.loads(PROFILE_PATH.read_text()) if not k.startswith("_")]


# --- term helpers -----------------------------------------------------------


def _term(terms: Dict[str, float], name: str, a, b, scale: float) -> None:
    """Record |a - b| / scale, or nothing at all if either side is missing."""
    if a is None or b is None or scale in (None, 0):
        return
    try:
        difference = abs(float(a) - float(b))
    except (TypeError, ValueError):
        return
    if not math.isfinite(difference):
        return
    terms[name] = difference / float(scale)


def _percentile_term(terms, name, a: Optional[dict], b: Optional[dict], scale: float) -> None:
    if not isinstance(a, dict) or not isinstance(b, dict):
        return
    _term(terms, name, a.get("p50"), b.get("p50"), scale)


def _mean(terms: Dict[str, float]) -> Optional[float]:
    return float(sum(terms.values()) / len(terms)) if terms else None


# --- the dimensions ---------------------------------------------------------


def _timbre(target: Fingerprint, candidate: Fingerprint, scales) -> Dict[str, float]:
    """Spectral shape: the band curve, its slope, and the cepstral envelope.

    The band difference has its mean removed. A constant offset across every
    band is a level difference, which `level` already accounts for — counting it
    twice would make the optimiser chase output gain instead of tone.
    """
    terms: Dict[str, float] = {}
    a_centres = target.spectrum.get("band_centres_hz") or []
    b_centres = candidate.spectrum.get("band_centres_hz") or []
    a_db = target.spectrum.get("band_db") or []
    b_db = candidate.spectrum.get("band_db") or []
    shared = [c for c in a_centres if c in set(b_centres)]
    if shared and scales.get("band_db"):
        a_map = dict(zip(a_centres, a_db))
        b_map = dict(zip(b_centres, b_db))
        differences = [a_map[c] - b_map[c] for c in shared]
        offset = sum(differences) / len(differences)
        rms = math.sqrt(sum((d - offset) ** 2 for d in differences) / len(differences))
        terms["band_shape"] = rms / float(scales["band_db"])

    _term(terms, "tilt", target.spectrum.get("tilt_db_per_decade"),
          candidate.spectrum.get("tilt_db_per_decade"), scales.get("tilt_db_per_decade"))
    _percentile_term(terms, "centroid", target.spectrum.get("centroid_hz"),
                     candidate.spectrum.get("centroid_hz"), scales.get("centroid_hz"))
    _percentile_term(terms, "rolloff85", target.spectrum.get("rolloff85_hz"),
                     candidate.spectrum.get("rolloff85_hz"), scales.get("rolloff85_hz"))

    a_mfcc = target.cepstral.get("mfcc_mean") or []
    b_mfcc = candidate.cepstral.get("mfcc_mean") or []
    if a_mfcc and len(a_mfcc) == len(b_mfcc) and scales.get("mfcc"):
        # Skip the first coefficient: it is overall energy, not shape.
        distance = math.sqrt(sum((x - y) ** 2 for x, y in zip(a_mfcc[1:], b_mfcc[1:])))
        terms["mfcc"] = distance / float(scales["mfcc"])
    return terms


def _dynamics(target: Fingerprint, candidate: Fingerprint, scales) -> Dict[str, float]:
    terms: Dict[str, float] = {}
    _term(terms, "crest", target.dynamics.get("crest_db"),
          candidate.dynamics.get("crest_db"), scales.get("crest_db"))
    _term(terms, "attack", target.dynamics.get("attack_ms"),
          candidate.dynamics.get("attack_ms"), scales.get("attack_ms"))
    _term(terms, "decay", target.dynamics.get("decay_db_per_s"),
          candidate.dynamics.get("decay_db_per_s"), scales.get("decay_db_per_s"))
    _term(terms, "lra", target.dynamics.get("lra_lu"),
          candidate.dynamics.get("lra_lu"), scales.get("lra_lu"))

    a = target.dynamics.get("rms_percentiles_db") or {}
    b = candidate.dynamics.get("rms_percentiles_db") or {}
    if a.get("p90") is not None and b.get("p90") is not None and scales.get("rms_spread_db"):
        # The spread, not the level: how far the loud parts sit above the quiet
        # ones is compression behaviour, and the absolute level is not.
        a_spread = a["p90"] - a.get("p10", a["p90"])
        b_spread = b["p90"] - b.get("p10", b["p90"])
        terms["rms_spread"] = abs(a_spread - b_spread) / float(scales["rms_spread_db"])
    return terms


def _ambience(target: Fingerprint, candidate: Fingerprint, scales) -> Dict[str, float]:
    """Reverb and delay — but only where both sides actually measured them.

    A delay time that neither side is confident about would otherwise dominate
    this dimension with the difference between two guesses.
    """
    terms: Dict[str, float] = {}
    if (float(target.time_fx.get("rt60_confidence") or 0) >= 0.3
            and float(candidate.time_fx.get("rt60_confidence") or 0) >= 0.3):
        _term(terms, "rt60", target.time_fx.get("rt60_s"),
              candidate.time_fx.get("rt60_s"), scales.get("rt60_s"))

    target_has = float(target.time_fx.get("delay_confidence") or 0) >= 0.15
    candidate_has = float(candidate.time_fx.get("delay_confidence") or 0) >= 0.15
    if target_has and candidate_has:
        _term(terms, "delay_time", target.time_fx.get("delay_ms"),
              candidate.time_fx.get("delay_ms"), scales.get("delay_ms"))
        _term(terms, "delay_feedback", target.time_fx.get("delay_feedback_est"),
              candidate.time_fx.get("delay_feedback_est"), scales.get("delay_feedback"))
    elif target_has != candidate_has:
        # One has an echo and the other does not. That is a whole unit of wrong,
        # and it is the most common way a generated preset misses.
        terms["delay_present"] = 1.0

    # Modulation, scaled by how sure both sides are that it is an effect rather
    # than the rate someone happened to be strumming at.
    modulation_confidence = min(float(target.modulation.get("am_confidence") or 0.0),
                                float(candidate.modulation.get("am_confidence") or 0.0))
    if modulation_confidence > 0.0:
        modulation: Dict[str, float] = {}
        _term(modulation, "am_depth", target.modulation.get("am_depth"),
              candidate.modulation.get("am_depth"), scales.get("am_depth"))
        _term(modulation, "am_rate", target.modulation.get("am_rate_hz"),
              candidate.modulation.get("am_rate_hz"), scales.get("am_rate_hz"))
        terms.update({k: v * modulation_confidence for k, v in modulation.items()})
    return terms


def _level(target: Fingerprint, candidate: Fingerprint, scales) -> Dict[str, float]:
    terms: Dict[str, float] = {}
    _term(terms, "lufs", target.source.get("lufs_i"),
          candidate.source.get("lufs_i"), scales.get("lufs_i"))
    return terms


def _harmonic(target: Fingerprint, candidate: Fingerprint, scales) -> Dict[str, float]:
    """Distortion character, weighted down by how sure either side is.

    Both confidences multiply in: measured across a chord these numbers describe
    the chord, and a search should not chase them.
    """
    confidence = min(float(target.harmonic.get("confidence") or 0.0),
                     float(candidate.harmonic.get("confidence") or 0.0))
    if confidence < 0.4:
        return {}
    terms: Dict[str, float] = {}
    _term(terms, "hnr", target.harmonic.get("hnr_db"),
          candidate.harmonic.get("hnr_db"), scales.get("hnr_db"))
    _term(terms, "odd_even", target.harmonic.get("odd_even_ratio"),
          candidate.harmonic.get("odd_even_ratio"), scales.get("odd_even_ratio"))
    _term(terms, "fizz", target.harmonic.get("hf_residual_index"),
          candidate.harmonic.get("hf_residual_index"), scales.get("hf_residual_index"))
    return {name: value * confidence for name, value in terms.items()}


def _spatial(target: Fingerprint, candidate: Fingerprint, scales) -> Dict[str, float]:
    if int(target.source.get("channels") or 1) < 2 or int(candidate.source.get("channels") or 1) < 2:
        return {}
    terms: Dict[str, float] = {}
    _term(terms, "width", target.spatial.get("width"),
          candidate.spatial.get("width"), scales.get("width"))
    _term(terms, "correlation", target.spatial.get("correlation"),
          candidate.spatial.get("correlation"), scales.get("correlation"))
    return terms


# --- the entry points -------------------------------------------------------


def compare(target: Fingerprint, candidate: Fingerprint,
            profile: str = "unpaired-v1",
            prior_deviation: Optional[float] = None,
            complexity: Optional[float] = None) -> Objectives:
    """Distances per dimension, plus the terms each one was built from.

    `prior_deviation` and `complexity` are not properties of two recordings —
    they are how far the optimiser wandered from the recipe stack and how many
    controls it had to move. They are passed in by whoever knows them, and are
    part of the vector so the shortlist can prefer the simpler of two equals.
    """
    scales = load_profile(profile)["scales"]
    detail = {
        "timbre": _timbre(target, candidate, scales),
        "dynamics": _dynamics(target, candidate, scales),
        "ambience": _ambience(target, candidate, scales),
        "level": _level(target, candidate, scales),
        "harmonic": _harmonic(target, candidate, scales),
        "spatial": _spatial(target, candidate, scales),
    }
    values: Dict[str, Optional[float]] = {name: _mean(terms) for name, terms in detail.items()}
    values["prior_deviation"] = prior_deviation
    values["complexity"] = complexity
    return Objectives(values=values, detail=detail, profile=profile)


def scalar(objectives: Objectives, profile: Optional[str] = None) -> Optional[float]:
    """Collapse to one number, for an optimiser that needs one.

    Only the measured dimensions count, renormalised over their own weights:
    with no measurable reverb, ambience does not silently score zero and make
    every candidate look better than it is.
    """
    weights = load_profile(profile or objectives.profile)["weights"]
    total, used = 0.0, 0.0
    for name, value in objectives.values.items():
        if value is None:
            continue
        weight = float(weights.get(name, 0.0))
        if weight <= 0:
            continue
        total += weight * float(value)
        used += weight
    return None if used <= 0 else float(total / used)


def band_delta(target: Fingerprint, candidate: Fingerprint,
               remove_offset: bool = True) -> List[Dict[str, float]]:
    """Signed per-band difference, in dB — what the equaliser has to undo.

    This is the table a person reads and the input `match/invert.py` fits onto
    the plugin's nine fixed-centre bands.
    """
    a_centres = target.spectrum.get("band_centres_hz") or []
    b_map = dict(zip(candidate.spectrum.get("band_centres_hz") or [],
                     candidate.spectrum.get("band_db") or []))
    a_map = dict(zip(a_centres, target.spectrum.get("band_db") or []))

    shared = [c for c in a_centres if c in b_map]
    if not shared:
        return []
    differences = {c: a_map[c] - b_map[c] for c in shared}
    offset = sum(differences.values()) / len(differences) if remove_offset else 0.0
    return [
        {"centre_hz": float(c),
         "target_db": float(a_map[c]),
         "candidate_db": float(b_map[c]),
         "delta_db": float(differences[c] - offset)}
        for c in shared
    ]
