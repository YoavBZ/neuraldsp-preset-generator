"""Set the parameters that can be calculated, so the search only handles the rest.

A large part of what makes a preset wrong is not a search problem. A spectral
difference maps onto nine fixed-centre EQ bands by least squares; a delay time is
an autocorrelation lag; a reverb decay is a slope; a level is a subtraction. Each
of those is one calculation against a measured fingerprint, and doing them first
takes the dimensions out of the search rather than asking CMA-ES to rediscover
them a few hundred renders at a time.

Every function here returns **human values keyed by `module/key`**, ready for
`match/space.py` to merge and `apply_spec.py` to write, and every one of them can
decline. A `None`, or an absent key, means the reference did not support the
measurement — which is a different thing from a measurement of zero, and the
difference is the whole reason the fingerprint carries confidences.

The EQ fit wants a **measured** basis: `packs/<id>/eq_basis.json`, produced by
`scripts/measure_eq_basis.py` in M5 from eleven renders per amp. Until that file
exists the fit falls back to idealised bell curves at the declared `centre_hz`,
and `Inversion.caveats` says so in as many words. This repository does not
silently substitute a guess for a measurement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# The graphic EQ's declared limits, in dB. The fit is bounded to them because a
# solution outside them cannot be written.
EQ_BOUNDS_DB = (-12.0, 12.0)

# Q of the fallback bell curves. A graphic equaliser's bands overlap; this is the
# value `analysis/refchain.py` builds its own filters with, so the fallback and the
# synthetic chain at least agree with each other. It is not a measurement of
# Morgan, which is what the basis file will be.
FALLBACK_Q = 1.1

# Below this, a measured difference is not worth moving a control for. The plugin
# shows 0.23 dB of per-band variation between two renders of identical parameters,
# so a fit chasing tenths is fitting noise.
BAND_NOISE_FLOOR_DB = 0.3


class InversionError(ValueError):
    """An inversion that cannot be performed at all — a missing band curve."""


@dataclass
class Inversion:
    """What was calculated, what it was calculated from, and what to distrust."""

    values: Dict[str, Any] = field(default_factory=dict)
    caveats: List[str] = field(default_factory=list)
    detail: Dict[str, Any] = field(default_factory=dict)

    def merge(self, other: "Inversion") -> "Inversion":
        self.values.update(other.values)
        self.caveats.extend(other.caveats)
        self.detail.update(other.detail)
        return self

    def as_settings(self, supported: Optional[Any] = None) -> Dict[str, Any]:
        """The dict `refchain.render` and `space.to_spec` both accept.

        `supported` is a backend's `parameter_specs()` — keys it can actually be
        driven with. An inversion is computed against the *plugin's* parameters, and
        a backend may model fewer of them: the synthetic chain covers 45 of Morgan's
        132 and refuses anything else outright, which is correct of it but means a
        caller must not hand it a tremolo it has never heard of.

        Passing nothing returns everything, which is what `space.to_spec` wants —
        the preset writer supports every parameter the manifest declares.
        """
        if supported is None:
            return dict(self.values)

        keys = {key if isinstance(key, tuple) else tuple(key.split("/", 1))
                for key in supported}
        return {path: value for path, value in self.values.items()
                if tuple(path.split("/", 1)) in keys}

    def dropped_for(self, supported: Any) -> List[str]:
        """What `as_settings(supported)` left out, so a report can say so."""
        kept = set(self.as_settings(supported))
        return sorted(set(self.values) - kept)


# --- spectral ---------------------------------------------------------------


def bell_basis(centres: Sequence[float], analysis_centres: Sequence[float],
               q: float = FALLBACK_Q):
    """Idealised per-band response curves: the fallback when nothing is measured.

    Row *i* is what 1 dB on band *i* does at each analysis frequency, under a
    textbook peaking filter. The real plugin's bands are not textbook — they
    interact, and their skirts are whatever its designers chose — which is why
    `measure_eq_basis.py` exists and why using this leaves a caveat behind.
    """
    import numpy as np

    centres = np.asarray(centres, dtype=np.float64)
    frequencies = np.asarray(analysis_centres, dtype=np.float64)
    basis = np.zeros((len(centres), len(frequencies)))
    for row, centre in enumerate(centres):
        # A peaking filter's magnitude in dB, normalised to 1 dB of gain at the
        # centre, is well approximated in log-frequency by a bell of width 1/q
        # octaves. Good enough to invert a smooth difference; not good enough to
        # publish as the plugin's response.
        octaves = np.log2(np.maximum(frequencies, 1e-9) / centre)
        basis[row] = 1.0 / (1.0 + (2.0 * q * octaves) ** 2)
    return basis


def fit_graphic_eq(band_delta_db: Mapping[float, float], centres: Sequence[float],
                   basis=None, bounds_db: Tuple[float, float] = EQ_BOUNDS_DB,
                   module: str = "", key_format: str = "{module}EQBand{index}") -> Inversion:
    """Solve the nine band gains that best flatten a measured band difference.

    `band_delta_db` is what `analysis.compare.band_delta()` produces: signed dB
    per third-octave centre, mean already removed, so this fits *shape* and leaves
    level to `output_level`.

    Bounded least squares, not a search. With nine unknowns, a smooth target and a
    fixed basis there is one answer and `scipy.optimize.lsq_linear` finds it.
    """
    require_analysis()
    import numpy as np
    from scipy.optimize import lsq_linear

    if not band_delta_db:
        return Inversion(caveats=["no band difference was measured, so the EQ is untouched"])

    frequencies = np.array(sorted(band_delta_db), dtype=np.float64)
    target = np.array([band_delta_db[f] for f in frequencies], dtype=np.float64)

    caveats: List[str] = []
    if basis is None:
        basis = bell_basis(centres, frequencies)
        caveats.append(
            "no measured EQ basis for this pack (packs/<id>/eq_basis.json is "
            "absent), so the fit used idealised bell curves at the declared band "
            "centres — the gains are approximate and the plugin's real bands "
            "interact"
        )
    basis = np.asarray(basis, dtype=np.float64)
    if basis.shape != (len(centres), len(frequencies)):
        raise InversionError(
            f"basis is {basis.shape}; expected ({len(centres)}, {len(frequencies)}) "
            f"for {len(centres)} bands against {len(frequencies)} analysis bands"
        )

    # Weight the bands the guitar actually occupies. A third-octave curve's
    # extremes are dominated by the source's own filtering, and letting 25 Hz pull
    # on the fit moves 65 Hz to chase it.
    weights = np.where((frequencies >= 50.0) & (frequencies <= 16000.0), 1.0, 0.15)
    solved = lsq_linear(basis.T * weights[:, None], target * weights,
                        bounds=bounds_db, method="trf")

    gains = np.asarray(solved.x, dtype=np.float64)
    values: Dict[str, Any] = {}
    for index, gain in enumerate(gains, start=1):
        if abs(gain) < BAND_NOISE_FLOOR_DB:
            # Leave it alone rather than write a number below what the plugin can
            # resolve between two identical renders.
            gain = 0.0
        name = key_format.format(module=module, index=index)
        values[f"{module}EQ/{name}"] = round(float(gain), 2)

    residual = float(np.sqrt(np.mean((basis.T @ gains - target) ** 2)))
    return Inversion(
        values=values,
        caveats=caveats,
        detail={"eq_residual_db": round(residual, 3),
                "eq_requested_db": {float(f): round(float(v), 2)
                                    for f, v in zip(frequencies, target)}},
    )


def fit_filters(band_delta_db: Mapping[float, float], module: str = "",
                hpf_range: Tuple[float, float] = (20.0, 500.0),
                lpf_range: Tuple[float, float] = (1000.0, 20000.0)) -> Inversion:
    """Corner frequencies for the HPF and LPF, from where the difference runs out.

    Deliberately crude, and only moves a corner when the evidence is one-sided:
    the target being short of low end across the *whole* bottom is a high-pass, but
    a dip at one frequency is a band gain and belongs to `fit_graphic_eq`. Anything
    ambiguous is left where it is, because a wrongly-set corner removes range that
    no band gain can put back.
    """
    require_analysis()
    import numpy as np

    if not band_delta_db:
        return Inversion()

    frequencies = np.array(sorted(band_delta_db), dtype=np.float64)
    delta = np.array([band_delta_db[f] for f in frequencies], dtype=np.float64)

    values: Dict[str, Any] = {}
    caveats: List[str] = []

    low = delta[frequencies <= 100.0]
    if len(low) >= 3 and np.all(low < -3.0):
        # The candidate has too much bottom everywhere below 100 Hz.
        corner = float(np.clip(frequencies[frequencies <= 100.0].max(), *hpf_range))
        values[f"{module}EQ/{module}EQHpf"] = round(corner, 1)

    high = delta[frequencies >= 6300.0]
    if len(high) >= 3 and np.all(high < -3.0):
        corner = float(np.clip(frequencies[frequencies >= 6300.0].min(), *lpf_range))
        values[f"{module}EQ/{module}EQLpf"] = round(corner, 1)

    if not values:
        caveats.append("no one-sided band roll-off, so the HPF and LPF were left alone")
    return Inversion(values=values, caveats=caveats)


# --- time effects -----------------------------------------------------------


def delay_settings(fingerprint, pack_id: str = "morgan",
                   min_confidence: float = 0.15) -> Inversion:
    """Delay time, feedback and mix, straight off the fingerprint.

    Declines below `min_confidence`, which is the floor `compare._ambience` uses,
    so a reading the objective would not trust does not get written into a preset
    either. That is not a formality: the detector caps its confidence on combed
    material precisely because a repeated phrase and a tempo-synced delay are the
    same measurement.
    """
    time_fx = getattr(fingerprint, "time_fx", {}) or {}
    confidence = float(time_fx.get("delay_confidence") or 0.0)
    measured = time_fx.get("delay_ms")

    if measured is None or confidence < min_confidence:
        return Inversion(
            values={"delay/delayActive": False},
            caveats=[
                f"no delay was measured above confidence {min_confidence} "
                f"(got {confidence:.2f}), so the delay is switched off rather than "
                f"set to a guess"
            ],
        )

    from packs.loader import load_pack

    pack = load_pack(pack_id)
    spec = pack.parameters.get("delay/delayTime")
    low, high = (spec.min, spec.max) if spec else (16.0, 1500.0)
    time_ms = min(max(float(measured), float(low)), float(high))

    caveats: List[str] = []
    if time_ms != float(measured):
        caveats.append(
            f"the measured delay of {measured:.0f} ms is outside the plugin's "
            f"{low:.0f}-{high:.0f} ms range and was clamped to {time_ms:.0f} ms"
        )

    values: Dict[str, Any] = {
        "delay/delayActive": True,
        "delay/delayTime": round(time_ms, 1),
    }

    feedback = time_fx.get("delay_feedback_est")
    if feedback is not None:
        # A rotation is a percent.
        values["delay/delayFeedback"] = round(min(max(float(feedback), 0.0), 1.0) * 100.0, 1)
    else:
        caveats.append("the repeat count did not support a feedback estimate")

    # How loud the repeat is *is* the correlation height the confidence came from.
    values["delay/delayMix"] = round(min(max(confidence, 0.0), 1.0) * 100.0, 1)

    division = time_fx.get("delay_note_division")
    detail: Dict[str, Any] = {"delay_confidence": round(confidence, 3)}
    if division:
        detail["delay_note_division"] = division
        detail["bpm_est"] = time_fx.get("bpm_est")
    return Inversion(values=values, caveats=caveats, detail=detail)


def reverb_settings(fingerprint, pack_id: str = "morgan",
                    min_confidence: float = 0.3) -> Inversion:
    """Decay and pre-delay from the fingerprint's reverb estimates.

    Two separate confidences, so two separate decisions: a recording can support a
    decay slope and not a pre-delay, and `predelay_ms` abstains far more often
    than it answers by design.
    """
    time_fx = getattr(fingerprint, "time_fx", {}) or {}
    rt60 = time_fx.get("rt60_s")
    confidence = float(time_fx.get("rt60_confidence") or 0.0)

    if rt60 is None or confidence < min_confidence:
        return Inversion(
            values={"reverb/reverbActive": False},
            caveats=[
                f"reverb decay was not measurable above confidence "
                f"{min_confidence} (got {confidence:.2f}); release segments in "
                f"music disagree, so the reverb is left off"
            ],
        )

    from packs.loader import load_pack

    pack = load_pack(pack_id)
    values: Dict[str, Any] = {"reverb/reverbActive": True}
    caveats: List[str] = []

    decay = pack.parameters.get("reverb/reverbDecay")
    low, high = (decay.min, decay.max) if decay else (1.0, 60.0)

    if float(rt60) < float(low):
        # A decay faster than the shortest reverb the plugin can make is not a
        # room, it is the note ending. Clamping *up* into range is how "there is no
        # reverb here" becomes "reverb at its minimum": dry plucks measure a
        # confident 0.41 s and would have switched a 1 s reverb on.
        return Inversion(
            values={"reverb/reverbActive": False},
            caveats=[
                f"the measured decay of {rt60:.2f} s is shorter than the plugin's "
                f"shortest reverb ({low:.0f} s), so it is the notes decaying rather "
                f"than a room; the reverb is left off"
            ],
            detail={"rt60_measured_s": round(float(rt60), 3)},
        )

    clamped = min(float(rt60), float(high))
    values["reverb/reverbDecay"] = round(clamped, 2)
    if clamped != float(rt60):
        caveats.append(
            f"the measured RT60 of {rt60:.2f} s exceeds the plugin's {high:.0f} s "
            f"maximum and was clamped"
        )

    predelay = time_fx.get("predelay_ms")
    if predelay is not None:
        spec = pack.parameters.get("reverb/reverbPreDelay")
        pre_low, pre_high = (spec.min, spec.max) if spec else (1.0, 200.0)
        values["reverb/reverbPreDelay"] = round(
            min(max(float(predelay), float(pre_low)), float(pre_high)), 1)
    else:
        caveats.append(
            "no pre-delay was visible: the direct sound and the tail were not "
            "separated, which is the usual case"
        )

    return Inversion(values=values, caveats=caveats,
                     detail={"rt60_confidence": round(confidence, 3)})


def tremolo_settings(fingerprint, pack_id: str = "morgan",
                     min_confidence: float = 0.75) -> Inversion:
    """Rate and depth from the amplitude-modulation spectrum.

    The confidence floor is high on purpose. A part strummed twice a second
    modulates its own envelope at 2 Hz and nothing in the audio distinguishes that
    from a 2 Hz tremolo — only the *purity* of the modulation does, which is what
    `am_confidence` measures. Switching a tremolo on because someone played in
    time would be an obvious, audible mistake.
    """
    modulation = getattr(fingerprint, "modulation", {}) or {}
    rate = modulation.get("am_rate_hz")
    confidence = float(modulation.get("am_confidence") or 0.0)

    if rate is None or confidence < min_confidence:
        return Inversion(
            values={"tremolo/tremoloActive": False},
            caveats=[
                f"the amplitude modulation was not a clean enough sine to be a "
                f"tremolo (confidence {confidence:.2f} against {min_confidence}); "
                f"more likely the rate the notes were played at"
            ],
        )

    from packs.loader import load_pack

    pack = load_pack(pack_id)
    spec = pack.parameters.get("tremolo/tremoloRate")
    low, high = (spec.min, spec.max) if spec else (0.1, 10.0)
    values: Dict[str, Any] = {
        "tremolo/tremoloActive": True,
        "tremolo/tremoloRate": round(min(max(float(rate), float(low)), float(high)), 2),
    }
    depth = modulation.get("am_depth")
    if depth is not None:
        values["tremolo/tremoloDepth"] = round(min(max(float(depth), 0.0), 1.0) * 100.0, 1)
    return Inversion(values=values,
                     detail={"am_confidence": round(confidence, 3)})


# --- level ------------------------------------------------------------------


def output_level(target, candidate, pack_id: str = "morgan") -> Inversion:
    """The output gain that closes the loudness difference.

    The one inversion with no ambiguity in it at all: both sides report integrated
    loudness in the same units, and the difference is the gain. It is also the one
    most worth doing first, because a level difference otherwise leaks into every
    spectral comparison that has not had its mean removed.
    """
    target_lufs = (getattr(target, "source", {}) or {}).get("lufs_i")
    candidate_lufs = (getattr(candidate, "source", {}) or {}).get("lufs_i")

    if target_lufs is None or candidate_lufs is None:
        return Inversion(caveats=[
            "one side has no integrated loudness (too short, or silent), so the "
            "output level was left alone"
        ])

    from packs.loader import load_pack

    pack = load_pack(pack_id)
    spec = pack.parameters.get("parameters/outputGain")
    low, high = (spec.min, spec.max) if spec else (-24.0, 24.0)

    wanted = float(target_lufs) - float(candidate_lufs)
    clamped = min(max(wanted, float(low)), float(high))
    caveats: List[str] = []
    if abs(clamped - wanted) > 0.05:
        caveats.append(
            f"the loudness difference of {wanted:+.1f} dB exceeds the output "
            f"gain's {low:.0f}..{high:.0f} dB range; it was clamped to "
            f"{clamped:+.1f} dB and {wanted - clamped:+.1f} dB remains"
        )
    return Inversion(values={"parameters/outputGain": round(clamped, 2)},
                     caveats=caveats,
                     detail={"lufs_difference_db": round(wanted, 2)})


# --- the whole pass ---------------------------------------------------------


def invert(target, candidate, amp: str = "sw50r", pack_id: str = "morgan",
           basis=None) -> Inversion:
    """Every inversion above, in the order they depend on each other.

    Level first, because the band fit reads a mean-removed difference and a
    remaining level offset would otherwise be spread across nine band gains. Then
    the filters, which decide how much range there is to shape. Then the bands.
    Then the time effects, which are independent of all of it.
    """
    require_analysis()
    from analysis.compare import band_delta

    result = Inversion()
    result.merge(output_level(target, candidate, pack_id=pack_id))

    rows = band_delta(target, candidate)
    delta = {float(row["centre_hz"]): float(row["delta_db"]) for row in rows}

    result.merge(fit_filters(delta, module=amp))

    centres = _band_centres(pack_id, amp)
    if centres:
        result.merge(fit_graphic_eq(delta, centres, basis=basis, module=amp))
        result.values[f"{amp}EQ/{amp}EQActive"] = True
    else:
        result.caveats.append(
            f"{pack_id} declares no graphic-EQ centres for {amp}, so no spectral "
            f"fit was attempted"
        )

    result.merge(delay_settings(target, pack_id=pack_id))
    result.merge(reverb_settings(target, pack_id=pack_id))
    result.merge(tremolo_settings(target, pack_id=pack_id))
    return result


def _band_centres(pack_id: str, amp: str) -> List[float]:
    """The declared `centre_hz` of one amp's graphic EQ, in band order."""
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    centres = []
    for index in range(1, 10):
        spec = pack.parameters.get(f"{amp}EQ/{amp}EQBand{index}")
        if spec is None or spec.centre_hz is None:
            return []
        centres.append(float(spec.centre_hz))
    return centres


def require_analysis() -> None:
    from analysis import require

    require("parameter inversion")
