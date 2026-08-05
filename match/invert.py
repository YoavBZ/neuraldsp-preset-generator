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

# Q of the fallback bell curves. A graphic equaliser's bands overlap; this matches
# the value `analysis/refchain.py` builds its own filters with, so the fallback and
# the synthetic chain agree — but refchain hardcodes its own 1.1 rather than reading
# this, so the agreement is a coincidence that a test pins rather than a guarantee.
# It is not a measurement of Morgan, which is what the basis file will be.
FALLBACK_Q = 1.1

# Below this, a measured difference is not worth moving a control for. The plugin
# shows 0.23 dB of per-band variation between two renders of identical parameters,
# so a fit chasing tenths is fitting noise.
BAND_NOISE_FLOOR_DB = 0.3


class InversionError(ValueError):
    """An inversion that cannot be performed at all — a missing band curve, or a
    pack that does not declare the parameter being set."""


def declared(pack_id: str, path: str):
    """The pack's spec for a parameter, refusing a pack that does not declare it.

    Every inversion here writes Morgan's parameter *paths* — `delay/delayTime`,
    `reverb/reverbDecay`, `parameters/outputGain`. `pack_id` used to be threaded
    through and then ignored: called with `toneking` these functions emitted
    Morgan's paths clamped to Morgan's ranges, so `reverb/reverbDecay` came out at
    30 s against Tone King's declared 0.5–8 s, for a parameter Tone King does not
    have. Silently. An argument that quietly does nothing is worse than one that
    is absent, so it now refuses.

    This also removes five copies of "look up the spec, else a hardcoded fallback
    range" — one of which had already drifted, offering `tremoloRate` a fallback of
    0.1–10 Hz against a manifest that declares 0.15–15.
    """
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    spec = pack.parameters.get(path)
    if spec is None:
        raise InversionError(
            f"pack {pack_id!r} does not declare {path}.\n"
            f"  These inversions write Morgan's parameter paths, so they only apply "
            f"to a pack that shares them. Supporting another pack means mapping its "
            f"own names, which no manifest field states."
        )
    if spec.min is None or spec.max is None:
        raise InversionError(
            f"{pack_id} declares {path} with no range, so a measurement cannot be "
            f"clamped into it. Establish the range first — see "
            f"docs/measuring-against-the-plugin.md."
        )
    return spec


@dataclass
class Inversion:
    """What was calculated, what it was calculated from, and what to distrust."""

    values: Dict[str, Any] = field(default_factory=dict)
    caveats: List[str] = field(default_factory=list)
    detail: Dict[str, Any] = field(default_factory=dict)

    def merge(self, other: "Inversion") -> None:
        """Fold another inversion's values, caveats and detail into this one.

        Returns nothing on purpose. It used to return `self`, which every one of the
        six call sites discarded and which bought only the misreading that
        `a.merge(b)` leaves `a` alone.
        """
        self.values.update(other.values)
        self.caveats.extend(other.caveats)
        self.detail.update(other.detail)

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
    interact, and their skirts are whatever its designers chose. Measuring them is
    M5 work (`scripts/measure_eq_basis.py` does not exist yet), which is why using
    this leaves a caveat behind.
    """
    require_analysis()
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
                   module: str = "", pack_id: Optional[str] = None) -> Inversion:
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
        where = f"packs/{pack_id}/eq_basis.json" if pack_id else "the pack's eq_basis.json"
        caveats.append(
            f"nobody has measured this amp's equaliser yet ({where} does not "
            f"exist), so the band gains were worked out from textbook filter shapes. "
            f"The real bands overlap differently, so expect these to be a couple of "
            f"dB out and to spill into their neighbours."
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

    # Zero the bands below what the plugin can resolve between two identical
    # renders, and do it *in the array*, so the residual below describes the
    # solution that was actually written. Rebinding the loop variable instead left
    # `eq_residual_db` measuring the pre-floor fit: on a small difference where
    # eight of nine bands were zeroed it reported 0.077 dB against an actual
    # 0.204, and in the all-zeroed case it reported 0.0 for a correction that had
    # been thrown away entirely — while the plan calls this "the number to watch".
    emitted = np.where(np.abs(np.asarray(solved.x, dtype=np.float64))
                       < BAND_NOISE_FLOOR_DB, 0.0,
                       np.asarray(solved.x, dtype=np.float64))
    emitted = np.round(emitted, 2)

    values: Dict[str, Any] = {}
    for index, gain in enumerate(emitted, start=1):
        values[f"{module}EQ/{module}EQBand{index}"] = float(gain)

    residual = float(np.sqrt(np.mean((basis.T @ emitted - target) ** 2)))
    caveats = list(caveats)
    if not np.any(emitted) and np.any(np.abs(target) > BAND_NOISE_FLOOR_DB):
        caveats.append(
            f"every band solved below {BAND_NOISE_FLOOR_DB} dB, which is the "
            f"plugin's own variation between two identical renders, so the "
            f"equaliser was left flat and {residual:.2f} dB of difference remains"
        )
    return Inversion(
        values=values,
        caveats=caveats,
        detail={"eq_residual_db": round(residual, 3),
                "eq_requested_db": {float(f): round(float(v), 2)
                                    for f, v in zip(frequencies, target)}},
    )


FILTER_MIN_DEFICIT_DB = 3.0   # how short the target has to be to call it a filter
FILTER_MIN_BANDS = 3          # over how many consecutive bands


def fit_filters(band_delta_db: Mapping[float, float], module: str = "",
                pack_id: str = "morgan") -> Inversion:
    """Corner frequencies for the HPF and LPF, from where the difference runs out.

    Only moves a corner when the evidence is one-sided: the target being short of
    low end across the *whole* bottom is a high-pass, whereas a dip at one
    frequency is a band gain and belongs to `fit_graphic_eq`. Anything ambiguous is
    left alone, because a wrongly-set corner removes range no band gain can put
    back.

    Two things this got wrong, both measured:

    **The corners were constants.** The window edges were hardcoded at 100 Hz and
    6.3 kHz and the code then took the boundary of its own window, so a deficit
    reaching 100 Hz, 200 Hz or 500 Hz all produced exactly `EQHpf = 100.0`. The
    corner is now where the deficit actually *stops* — the top of the contiguous
    run of short bands from the bottom — which is what the docstring always claimed.
    The `hpf_range`/`lpf_range` arguments are gone; the declared range comes from
    the pack.

    **It handed the same difference to the band fit.** Both ran on one delta, so a
    flat −3.5 dB low end set `EQHpf` *and* `Band1 = −4.6 dB`. Scored through
    `refchain`'s own filter that is −24.6 dB applied at 25 Hz for −3.5 dB requested
    — precisely the over-correction the paragraph above warns about.
    `Inversion.detail["filtered_hz"]` now names the bands this accounted for, and
    `invert()` removes them from the delta before fitting bands.
    """
    require_analysis()
    import numpy as np

    if not band_delta_db:
        return Inversion(caveats=[
            "no band difference was measured, so the high-pass and low-pass were "
            "left alone"
        ])

    frequencies = np.array(sorted(band_delta_db), dtype=np.float64)
    delta = np.array([band_delta_db[f] for f in frequencies], dtype=np.float64)

    values: Dict[str, Any] = {}
    caveats: List[str] = []
    handled: List[float] = []

    short = delta < -FILTER_MIN_DEFICIT_DB

    # High pass: the run of short bands starting at the very bottom.
    run = 0
    while run < len(short) and short[run]:
        run += 1
    if run >= FILTER_MIN_BANDS:
        spec = declared(pack_id, f"{module}EQ/{module}EQHpf")
        corner = float(np.clip(frequencies[run - 1], float(spec.min), float(spec.max)))
        values[f"{module}EQ/{module}EQHpf"] = round(corner, 1)
        handled.extend(float(f) for f in frequencies[:run])

    # Low pass: the run of short bands ending at the very top.
    run = 0
    while run < len(short) and short[len(short) - 1 - run]:
        run += 1
    if run >= FILTER_MIN_BANDS:
        spec = declared(pack_id, f"{module}EQ/{module}EQLpf")
        corner = float(np.clip(frequencies[len(short) - run], float(spec.min), float(spec.max)))
        values[f"{module}EQ/{module}EQLpf"] = round(corner, 1)
        handled.extend(float(f) for f in frequencies[len(short) - run:])

    if not values:
        caveats.append(
            f"the difference is not a roll-off at either end — no run of "
            f"{FILTER_MIN_BANDS} bands is more than {FILTER_MIN_DEFICIT_DB:.0f} dB "
            f"short — so the high-pass and low-pass were left alone and the bands "
            f"carry the whole correction"
        )
    return Inversion(values=values, caveats=caveats,
                     detail={"filtered_hz": sorted(set(handled))})


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

    spec = declared(pack_id, "delay/delayTime")
    low, high = float(spec.min), float(spec.max)
    time_ms = min(max(float(measured), low), high)

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

    # `delayMix` is deliberately not set. It used to be written as the detection
    # confidence times 100, so a confidence of 0.95 asked the plugin for 95% wet.
    # The confidence is a normalised autocorrelation height, and nothing establishes
    # that a correlation height equals a wet-mix percentage — they are not even the
    # same kind of quantity. Setting a control from a number that happens to share
    # its range is exactly the guessing this project refuses, so the mix is left for
    # the search, which can hear the result.
    caveats.append(
        "the delay's wet level is left for the search: how loud a repeat is cannot "
        "be read off the measurement that found it"
    )

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
                f"the reverb tail could not be measured reliably (confidence "
                f"{confidence:.2f} against {min_confidence}): the notes decay at "
                f"different rates, which is what music does and a room does not, so "
                f"the reverb is left off"
            ],
        )

    values: Dict[str, Any] = {"reverb/reverbActive": True}
    caveats: List[str] = []

    decay = declared(pack_id, "reverb/reverbDecay")
    low, high = float(decay.min), float(decay.max)

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
        spec = declared(pack_id, "reverb/reverbPreDelay")
        pre_low, pre_high = float(spec.min), float(spec.max)
        clamped_pre = min(max(float(predelay), pre_low), pre_high)
        values["reverb/reverbPreDelay"] = round(clamped_pre, 1)
        if abs(clamped_pre - float(predelay)) > 0.05:
            caveats.append(
                f"the measured pre-delay of {float(predelay):.1f} ms is outside the "
                f"plugin's {pre_low:.0f}-{pre_high:.0f} ms range and was clamped to "
                f"{clamped_pre:.1f} ms"
            )
    else:
        caveats.append(
            "no pre-delay was visible: the direct sound and the tail were not "
            "separated, which is the usual case"
        )

    return Inversion(values=values, caveats=caveats,
                     detail={"rt60_confidence": round(confidence, 3)})


def tremolo_settings(fingerprint, pack_id: str = "morgan",
                     min_confidence: float = 0.75,
                     allow_with_delay: bool = False) -> Inversion:
    """Rate and depth from the amplitude-modulation spectrum.

    The confidence floor is high on purpose. A part strummed twice a second
    modulates its own envelope at 2 Hz and nothing in the audio distinguishes that
    from a 2 Hz tremolo — only the *purity* of the modulation does, which is what
    `am_confidence` measures. Switching a tremolo on because someone played in
    time would be an obvious, audible mistake.
    """
    modulation = getattr(fingerprint, "modulation", {}) or {}
    time_fx = getattr(fingerprint, "time_fx", {}) or {}
    rate = modulation.get("am_rate_hz")
    confidence = float(modulation.get("am_confidence") or 0.0)

    # An echo modulates the envelope at its own repeat rate, and purely enough to
    # pass the confidence gate. Measured: a 420 ms delay produced a 2.1 Hz
    # modulation at confidence 0.81 against a 0.75 floor, so `invert()` wrote a
    # full-depth tremolo into a target that had none — and this was the one
    # inversion that emitted no caveat when it acted, so nothing said why.
    #
    # 1/T of a detected delay is exactly where those repeats land, so a modulation
    # that coincides with it is attributed to the echo rather than to a tremolo.
    delay_ms = time_fx.get("delay_ms")
    delay_confident = float(time_fx.get("delay_confidence") or 0.0) >= 0.15
    if (rate is not None and delay_ms and delay_confident and not allow_with_delay):
        repeat_hz = 1000.0 / float(delay_ms)
        if abs(float(rate) - repeat_hz) <= max(0.4, 0.15 * repeat_hz):
            return Inversion(
                values={"tremolo/tremoloActive": False},
                caveats=[
                    f"the {float(rate):.1f} Hz amplitude modulation matches the "
                    f"{float(delay_ms):.0f} ms delay's own repeat rate "
                    f"({repeat_hz:.1f} Hz), so it is the echo rather than a tremolo; "
                    f"the tremolo is left off"
                ],
                detail={"am_confidence": round(confidence, 3),
                        "am_attributed_to": "delay repeats"},
            )

    if rate is None or confidence < min_confidence:
        return Inversion(
            values={"tremolo/tremoloActive": False},
            caveats=[
                f"the amplitude modulation was not a clean enough sine to be a "
                f"tremolo (confidence {confidence:.2f} against {min_confidence}); "
                f"more likely the rate the notes were played at"
            ],
        )

    spec = declared(pack_id, "tremolo/tremoloRate")
    low, high = float(spec.min), float(spec.max)
    clamped = min(max(float(rate), low), high)

    caveats = [
        f"a tremolo was set from a {clamped:.2f} Hz amplitude modulation measured at "
        f"confidence {confidence:.2f}. Nothing in a recording separates a tremolo "
        f"from a part played at that rate except how pure the modulation is, so "
        f"check this one by ear."
    ]
    if abs(clamped - float(rate)) > 0.005:
        caveats.append(
            f"the measured rate of {float(rate):.2f} Hz is outside the plugin's "
            f"{low:.2f}-{high:.2f} Hz range and was clamped to {clamped:.2f} Hz"
        )

    values: Dict[str, Any] = {
        "tremolo/tremoloActive": True,
        "tremolo/tremoloRate": round(clamped, 2),
    }
    depth = modulation.get("am_depth")
    if depth is not None:
        values["tremolo/tremoloDepth"] = round(min(max(float(depth), 0.0), 1.0) * 100.0, 1)
    else:
        caveats.append("the modulation depth could not be estimated, so it is left alone")
    return Inversion(values=values, caveats=caveats,
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

    spec = declared(pack_id, "parameters/outputGain")
    low, high = float(spec.min), float(spec.max)

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

    amp = _validated_amp(pack_id, amp)

    result = Inversion()
    # Which amp this is for. Without it `space.to_spec` cannot tell which of the
    # three amps' controls matter and silently dropped every one of them — a
    # 14-value inversion came out as a 4-parameter spec.
    result.values["/selectedAmp"] = _amp_display_name(pack_id, amp)

    result.merge(output_level(target, candidate, pack_id=pack_id))

    rows = band_delta(target, candidate)
    delta = {float(row["centre_hz"]): float(row["delta_db"]) for row in rows}

    filters = fit_filters(delta, module=amp, pack_id=pack_id)
    result.merge(filters)

    # The bands must not re-correct what a filter corner just handled.
    for centre in filters.detail.get("filtered_hz", []):
        delta.pop(float(centre), None)

    centres = _band_centres(pack_id, amp)
    if centres:
        spectral = fit_graphic_eq(delta, centres, basis=basis, module=amp,
                                  pack_id=pack_id)
        result.merge(spectral)
        moved = any(value for value in spectral.values.values())
        if moved or filters.values:
            result.values[f"{amp}EQ/{amp}EQActive"] = True
        else:
            # Switching the equaliser on to do nothing is a change with no reason.
            result.values[f"{amp}EQ/{amp}EQActive"] = False
    else:
        result.caveats.append(
            f"{pack_id} declares no graphic-EQ centres for {amp}, so no spectral "
            f"fit was attempted"
        )

    if any("EQBand" in path and value for path, value in result.values.items()):
        # Level was computed against the candidate as it was, and the band gains
        # just changed how loud it will be. One pass cannot close both: the fit
        # needs a mean-removed difference to work on, and the loudness it leaves
        # behind is only knowable after rendering. Measured on the M3 exit-criterion
        # target, this leaves about 3 dB. A second pass, or the search, closes it.
        result.caveats.append(
            "the output level was matched before the equaliser was set, and the "
            "band gains change how loud the result is — expect a couple of dB of "
            "level left over, which one more pass or the search will take out"
        )

    result.merge(delay_settings(target, pack_id=pack_id))
    result.merge(reverb_settings(target, pack_id=pack_id))
    result.merge(tremolo_settings(target, pack_id=pack_id))
    return result


def _validated_amp(pack_id: str, amp: str) -> str:
    """The module prefix, refusing anything the pack does not have.

    An unrecognised `amp` used to produce a caveat blaming the manifest —
    "morgan declares no graphic-EQ centres for SW50R" — for a pack that declares
    them perfectly well. `SW50R` is not a hypothetical typo either: it is the exact
    spelling `amp_modules` is keyed by and that `Space.amp_prefix` accepts.
    """
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    prefixes = set(pack.amp_modules.values())
    if amp in prefixes:
        return amp
    if amp in pack.amp_modules:                      # a display name
        return pack.amp_modules[amp]
    raise InversionError(
        f"{amp!r} is not an amp in pack {pack_id!r}.\n"
        f"  Accepted: {', '.join(sorted(prefixes))} "
        f"(or {', '.join(sorted(pack.amp_modules))})."
    )


def _amp_display_name(pack_id: str, prefix: str) -> str:
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    for name, module_prefix in pack.amp_modules.items():
        if module_prefix == prefix:
            return name
    return prefix


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
