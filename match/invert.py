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
`scripts/measure_eq_basis.py` from real-plugin renders per signal path. Until that file
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

# How close a modulation has to be to a delay's repeat rate before the two stop
# being distinguishable. A floor rather than a pure percentage because at 2 Hz a
# 15% window is 0.3 Hz, which is finer than the AM detector's own resolution.
TREMOLO_RATE_TOLERANCE_HZ = 0.4


class InversionError(ValueError):
    """An inversion that cannot be performed at all — a missing band curve, or a
    pack that does not declare the parameter being set."""


@dataclass(frozen=True)
class MeasuredBasis:
    """A two-item basis result with aligned repeat noise as metadata.

    Iteration and indexing retain the historical ``(basis, note)`` contract, so
    backends and callers do not need a renderer-source change merely to carry the
    adjacent measurement.
    """

    basis: Any
    note: str
    band_noise_db: Optional[Mapping[float, float]] = None
    renderer_build: Optional[str] = None
    quality_mode: Optional[str] = None
    renderer_id: Optional[str] = None
    plugin_version: Optional[str] = None
    sample_rate: Optional[int] = None
    block_size: Optional[int] = None
    provenance_schema: Optional[str] = None
    signal_path_sha256: Optional[str] = None

    def __iter__(self):
        yield self.basis
        yield self.note

    def __getitem__(self, index):
        return (self.basis, self.note)[index]

    def __len__(self):
        return 2


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


def apply_to(seed: Mapping, calculated: Mapping[str, Any], space) -> Dict[Any, Any]:
    """Fold calculated values into a seed vector, keyed the way the space reads.

    Only paths the space knows. `invert()` emits `/selectedAmp` and the pack's own
    parameter paths, and a path the space excluded — a mic type whose members are
    unknown, say — must not come back in through here.

    Here rather than in each caller: `scripts/match_preset.py` and `match/benchmark.py`
    had the same five lines, character for character, which is one place for a fix to be
    applied and one place for it to be missed.
    """
    known = {dimension.path: (dimension.module, dimension.key)
             for dimension in space.dimensions}
    known["selectedAmp"] = ("", "selectedAmp")
    merged = dict(seed)
    for path, value in calculated.items():
        key = known.get(path) or known.get(path.lstrip("/"))
        if key is not None:
            merged[key] = value
    return merged


# --- spectral ---------------------------------------------------------------


def bell_basis(centres: Sequence[float], analysis_centres: Sequence[float],
               q: float = FALLBACK_Q):
    """Idealised per-band response curves: the fallback when nothing is measured.

    Row *i* is what 1 dB on band *i* does at each analysis frequency, under a
    textbook peaking filter. The real plugin's bands are not textbook — they
    interact, and their skirts are whatever its designers chose. This is the
    fallback used when the backend has no basis from `measure_eq_basis.py`, which
    is why using it leaves a caveat behind.
    """
    from analysis import require

    require("building a fallback EQ basis")
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


def measured_basis(pack_id: str, signal_path: str,
                   analysis_centres: Sequence[float],
                   expected_plugin_version: Optional[str] = None):
    """The measured basis for one signal path, or ``None`` if none can be used.

    `packs/<pack>/eq_basis.json` is written by `scripts/measure_eq_basis.py` from
    renders of the real plugin — row *i* is what 1 dB on band *i* does at each
    third-octave centre. Returned as `(basis, note)` so a caller can say where the
    numbers came from; the note carries the plugin version, because a basis
    measured on one version is not a fact about another.

    `expected_plugin_version` is supplied by a real backend. A committed basis
    measured on another plugin version is refused: using it would merge measured
    results across versions even though render caches correctly keep them apart.

    Returns `None` rather than raising for every ordinary absence — no file, a
    pack without this signal path, a schema this does not understand — because the
    fallback is a working answer with a caveat attached, and refusing to invert at
    all would be a worse one. A file that *is* present and does not line up with
    the analysis frequencies is the exception: that is a stale measurement rather
    than a missing one, and silently ignoring it would hide the staleness.
    """
    import pathlib

    import numpy as np

    path = (pathlib.Path(__file__).resolve().parents[1]
            / "packs" / pack_id / "eq_basis.json")
    if not path.is_file():
        return None
    document = _read_basis_document(path)
    if document is None:
        return None
    if document.get("schema") != "eq-basis-1":
        return None
    rows = (document.get("amps") or {}).get(signal_path)
    if not rows:
        return None

    # The matrix row order is the control order. Validate it against the topology
    # that will receive the solved gains, rather than trusting two independently
    # editable files to stay aligned. Older Morgan artifacts predate
    # ``band_controls``; their ordered centres provide the same guard.
    from packs.calibration import (
        CalibrationError,
        eq_basis_topology_sha256,
        signal_paths,
    )
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    try:
        declared_path = signal_paths(pack).get(signal_path)
    except CalibrationError as error:
        raise InversionError(str(error)) from error
    if declared_path is None:
        return None
    renderer_record = document.get("renderer") or {}
    recorded_schema = document.get("provenance_schema")
    recorded_build = str(renderer_record.get("renderer_build", "") or "")
    if recorded_schema == "eq-basis-provenance-1":
        provenance_schema = recorded_schema
    elif (recorded_schema == "legacy-morgan-au-render-server-1"
          and pack_id == "morgan"
          and recorded_build == "au_render_server-9ba52a85ccaf"):
        # The one committed pre-M5 artifact, named explicitly and tied to its exact
        # recorded host build. Missing provenance is never interpreted as legacy.
        provenance_schema = "legacy-morgan-au-render-server-1"
    else:
        raise InversionError(
            f"{path} has missing or unsupported calibration provenance schema "
            f"{recorded_schema!r}. Re-run scripts/measure_eq_basis.py --pack "
            f"{pack_id}."
        )

    current_topology = eq_basis_topology_sha256(pack, declared_path)
    recorded_topology = rows.get("signal_path_sha256")
    modern = provenance_schema == "eq-basis-provenance-1"
    if modern and not recorded_topology:
        raise InversionError(
            f"{path} does not record the calibration topology for {signal_path}. "
            f"Re-run scripts/measure_eq_basis.py --pack {pack_id}."
        )
    if recorded_topology and recorded_topology != current_topology:
        raise InversionError(
            f"{path} was measured with different {signal_path} calibration "
            f"settings or signal-path topology. Re-run "
            f"scripts/measure_eq_basis.py --pack {pack_id}."
        )
    declared_controls = tuple(declared_path.eq_band_controls)
    recorded_controls = tuple(rows.get("band_controls") or ())
    if recorded_controls and recorded_controls != declared_controls:
        raise InversionError(
            f"{path} records {signal_path} EQ rows in a different control order "
            f"from packs/{pack_id}/manifest.json. Re-run "
            f"scripts/measure_eq_basis.py --pack {pack_id}."
        )
    declared_centres = []
    for control in declared_controls:
        centre = pack.parameters[control].centre_hz
        if centre is None:
            raise InversionError(
                f"packs/{pack_id}/manifest.json gives {control} no centre_hz, so "
                f"the rows in {path} cannot be assigned safely"
            )
        declared_centres.append(float(centre))
    recorded_centres = [float(value)
                        for value in rows.get("band_centres_hz") or []]
    if recorded_centres != declared_centres:
        raise InversionError(
            f"{path} records {signal_path} EQ rows at {recorded_centres}, but the "
            f"manifest's ordered controls declare {declared_centres}. Re-run "
            f"scripts/measure_eq_basis.py --pack {pack_id}."
        )

    version = str((document.get("renderer") or {}).get(
        "plugin_version", "unknown"))
    if (expected_plugin_version is not None
            and version != str(expected_plugin_version)):
        raise InversionError(
            f"{path} was measured against plugin {version}, but this renderer is "
            f"running {expected_plugin_version}. Results from different plugin "
            f"versions must not be merged. Re-run "
            f"scripts/measure_eq_basis.py --pack {pack_id}."
        )

    available = [float(f) for f in document.get("analysis_centres_hz") or []]
    matrix = np.asarray(rows.get("basis_db_per_db") or [], dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != len(available):
        raise InversionError(
            f"{path} holds a {matrix.shape} basis for {signal_path} against "
            f"{len(available)} analysis centres. Re-run "
            f"scripts/measure_eq_basis.py --pack {pack_id}."
        )

    # Select the columns this fit is actually solving over. A fingerprint drops a
    # band it could not measure, so the requested frequencies are a subset of the
    # measured ones rather than the same list.
    index = {frequency: column for column, frequency in enumerate(available)}
    wanted = [float(f) for f in analysis_centres]
    missing = [f for f in wanted if f not in index]
    if missing:
        raise InversionError(
            f"{path} has no measurement at "
            f"{', '.join(f'{f:g}' for f in missing[:5])} Hz"
            f"{'…' if len(missing) > 5 else ''}, which this fit needs.\n"
            f"  The file was measured against a different analysis band set. "
            f"Re-run scripts/measure_eq_basis.py --pack {pack_id}."
        )

    note = (f"the band gains were fitted to this signal path's *measured* equaliser "
            f"({path.parent.name}/eq_basis.json, plugin {version}) rather than to "
            f"textbook filter shapes")
    if not (document.get("renderer") or {}).get("reproducible", False):
        note += (", measured on a reused plugin instance that does not repeat "
                 "itself exactly")
    noise = None
    repeat = rows.get("repeat_verification") or {}
    repeated = repeat.get("band_difference_db")
    if repeated is not None:
        if len(repeated) != len(available):
            raise InversionError(
                f"{path} records {len(repeated)} repeat differences against "
                f"{len(available)} analysis centres. Re-run "
                f"scripts/measure_eq_basis.py --pack {pack_id}."
            )
        noise = {frequency: max(0.0, float(repeated[index[frequency]]))
                 for frequency in wanted}
    return MeasuredBasis(
        matrix[:, [index[f] for f in wanted]], note, band_noise_db=noise,
        renderer_build=renderer_record.get("renderer_build"),
        quality_mode=renderer_record.get("quality_mode"),
        renderer_id=renderer_record.get("renderer_id"),
        plugin_version=renderer_record.get("plugin_version"),
        sample_rate=renderer_record.get("sample_rate"),
        block_size=renderer_record.get("block_size"),
        provenance_schema=provenance_schema,
        signal_path_sha256=recorded_topology,
    )


def measured_band_noise(pack_id: str, signal_path: str,
                        analysis_centres: Sequence[float],
                        expected_plugin_version: Optional[str] = None):
    """The basis run's repeat difference at each requested frequency.

    This deliberately is not ``RenderMetadata.band_noise_db``. That metadata field
    records the largest movement anywhere for provenance; an EQ decision needs to
    know *where* it happened. Tone King's five-sample reused-instance maximum is
    5.23 dB at 25 Hz while its measured 50 Hz-and-up maximum is about 0.065 dB.
    """
    found = measured_basis(
        pack_id, signal_path, analysis_centres,
        expected_plugin_version=expected_plugin_version,
    )
    return None if found is None else found.band_noise_db


def _read_basis_document(path):
    """Read one basis document; separated so stale-topology behavior is testable."""
    import json

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def fit_graphic_eq(band_delta_db: Mapping[float, float], centres: Sequence[float],
                   basis=None, bounds_db: Any = EQ_BOUNDS_DB,
                   module: str = "", pack_id: Optional[str] = None,
                   accounted_for=None,
                   band_controls: Optional[Sequence[str]] = None,
                   band_noise_db: Any = BAND_NOISE_FLOOR_DB) -> Inversion:
    """Solve the nine band gains that best flatten a measured band difference.

    `band_delta_db` is what `analysis.compare.band_delta()` produces: signed dB
    per third-octave centre, mean already removed, so this fits *shape* and leaves
    level to `output_level`.

    Bounded least squares, not a search. With nine unknowns, a smooth target and a
    fixed basis there is one answer and `scipy.optimize.lsq_linear` finds it.

    `accounted_for` is dB per frequency that something else in the chain is already
    contributing — in practice `fit_filters`' `filter_response_db`, so the bands fit
    what the corners leave rather than the same difference over again. Subtracting a
    modelled response replaced *deleting* the covered bands, which was wrong in
    three ways, all measured:

    - **A band whose neighbourhood was deleted went to the rail.** On a target with
      an LPF at 4 kHz — 23.7 dB short at 16 kHz — the 16 kHz band came out at
      *+10.59 dB*, a boost, because nothing constrained it any more.
    - **The residual described a subset.** `eq_residual_db` read 1.34 dB where the
      emitted gains scored 9.82 against everything measured, and `eq_requested_db`
      held 24 of 30 bands with nothing saying six were missing.
    - **A caller's own basis stopped fitting.** `basis` is sized to the full delta,
      so removing bands first made the shape check reject the measured basis M5 is
      going to supply — the only reason `basis` is a parameter at all.

    All three go away when every band stays in the fit and the target is the part
    nothing else is handling. `eq_requested_db` records that remainder and
    `eq_measured_db` the difference it came from, so a report can show both.
    """
    from analysis import require

    require("fitting a graphic EQ")
    import numpy as np
    from scipy.optimize import lsq_linear

    if not band_delta_db:
        return Inversion(caveats=[
            "no band difference was measured, so the equaliser is untouched"
        ])

    frequencies = np.array(sorted(band_delta_db), dtype=np.float64)
    measured = np.array([band_delta_db[f] for f in frequencies], dtype=np.float64)
    already = np.array([float((accounted_for or {}).get(float(f), 0.0))
                        for f in frequencies], dtype=np.float64)
    # What is left for the bands. Only the *shape* of the corner's response is
    # deducted: it attenuates, so its mean is negative, and subtracting that mean
    # too would ask the bands to make up a level difference `output_level` already
    # closed. `measured` arrives mean-free by `band_delta`'s own contract, so this
    # leaves it that way.
    target = measured - (already - already.mean())

    caveats: List[str] = []
    supplied_basis = basis is not None
    if basis is None:
        basis = bell_basis(centres, frequencies)
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

    # Decide whether the correction *as a whole* rises above what this renderer can
    # resolve between identical states. Graphic-EQ bands overlap: thresholding each
    # coefficient independently can throw away two sub-floor moves whose combined
    # response is audible. Resolution is decided inside 50 Hz..16 kHz, the same
    # guitar range the solve gives full weight, so one unstable 25 Hz bin cannot
    # suppress or activate a nine-control correction.
    gains = np.asarray(solved.x, dtype=np.float64)
    if isinstance(band_noise_db, Mapping):
        missing_noise = [float(f) for f in frequencies
                         if float(f) not in band_noise_db]
        if missing_noise:
            raise InversionError(
                "the renderer's EQ repeat measurement has no value at "
                + ", ".join(f"{f:g} Hz" for f in missing_noise[:5])
            )
        noise_by_frequency = np.asarray([
            max(0.0, float(band_noise_db[float(f)])) for f in frequencies
        ])
    else:
        noise_by_frequency = np.full(
            len(frequencies), max(0.0, float(band_noise_db)), dtype=np.float64
        )
    rounded = np.round(gains, 2)
    combined_effect = basis.T @ rounded
    guitar = (frequencies >= 50.0) & (frequencies <= 16000.0)
    compared = guitar if np.any(guitar) else np.ones(len(frequencies), dtype=bool)
    effect_bins = np.abs(combined_effect[compared])
    noise_bins = noise_by_frequency[compared]
    effect = float(np.max(effect_bins))
    noise = float(np.max(noise_bins))
    margin = float(np.max(effect_bins - noise_bins))
    resolvable = margin > 0.0
    emitted = rounded if resolvable else np.zeros_like(rounded)

    if band_controls is None:
        controls = [f"{module}EQ/{module}EQBand{index}"
                    for index in range(1, len(emitted) + 1)]
    else:
        controls = list(band_controls)
        if len(controls) != len(emitted):
            raise InversionError(
                f"{len(controls)} band controls were supplied for "
                f"{len(emitted)} solved gains"
            )
    values = {control: float(gain) for control, gain in zip(controls, emitted)}

    residual = _rms(basis.T @ emitted - target)

    if not supplied_basis and np.any(emitted):
        where = f"packs/{pack_id}/eq_basis.json" if pack_id else "the pack's eq_basis.json"
        caveats.append(
            f"nobody has measured this amp's equaliser yet ({where} does not "
            f"exist), so the band gains were worked out from textbook filter shapes. "
            f"The real bands overlap differently, so expect these to be a couple of "
            f"dB out and to spill into their neighbours."
        )
    if not np.any(emitted) and np.any(np.abs(target) > 0.0):
        caveats.append(
            f"the fitted correction solved at or below this renderer's "
            f"frequency-aligned identical-state variation in every guitar band "
            f"(up to {noise:g} dB there), so no band correction was written and "
            f"{residual:.2f} dB of difference remains"
        )
    return Inversion(
        values=values,
        caveats=caveats,
        # Three separate maxima over the guitar bands, not three terms of one
        # subtraction: the loudest part of the correction and the noisiest band
        # need not be the same band, which is the whole reason the comparison is
        # frequency-aligned. `eq_noise_margin_db` is the decision — the largest
        # effect-minus-noise at a single frequency — and it is what > 0 means.
        detail={"eq_residual_db": round(residual, 3),
                "eq_effect_max_db": round(effect, 6),
                "eq_noise_max_db": round(noise, 6),
                "eq_noise_margin_db": round(margin, 6),
                "eq_requested_db": {float(f): round(float(v), 2)
                                    for f, v in zip(frequencies, target)},
                "eq_measured_db": {float(f): round(float(v), 2)
                                   for f, v in zip(frequencies, measured)}},
    )


def _rms(array) -> float:
    import numpy as np

    return float(np.sqrt(np.mean(np.asarray(array, dtype=np.float64) ** 2)))


FILTER_MIN_DEFICIT_DB = 3.0   # how short the target has to be to call it a filter
FILTER_MIN_BANDS = 3          # over how many consecutive bands

# Above this, the measured roll-off is not the shape a corner makes, so the corner
# was fitted to something else. Chosen just above the worst fit that still recovers a
# real corner exactly on the synthetic chain — 1.51 dB, at a 2 kHz low-pass — and
# below where the fit visibly stops tracking: a 400 Hz high-pass scores 3.97 and
# comes back as 125.
FILTER_MAX_FIT_DB = 2.5

# The order this assumes the plugin's corners are. `analysis/refchain.py` builds
# second-order Butterworth sections, so the synthetic chain and this agree by
# construction — for the plugin it is the same class of assumption `bell_basis`
# makes about the bands, and M5's measurement replaces both.
FILTER_ORDER = 2


def filter_response_db(frequencies, hpf_hz: Optional[float] = None,
                       lpf_hz: Optional[float] = None):
    """What a corner pair does, in dB per frequency, under `FILTER_ORDER`.

    A Butterworth magnitude, which is where the whole "the corner is not the
    deficit" business is settled: a second-order high-pass at 100 Hz is 24 dB down
    at 25 Hz, so a −3.5 dB shortfall at the bottom is *not* evidence for a corner at
    the frequency the shortfall stops. Having the shape in closed form means the
    corner can be fitted to it and the remainder handed to the bands, instead of
    both of them guessing at the same difference.
    """
    import numpy as np

    f = np.asarray(frequencies, dtype=np.float64)
    out = np.zeros(len(f), dtype=np.float64)
    power = 2 * FILTER_ORDER
    if hpf_hz:
        ratio = (f / float(hpf_hz)) ** power
        out += 10.0 * np.log10(ratio / (1.0 + ratio))
    if lpf_hz:
        ratio = (f / float(lpf_hz)) ** power
        out += 10.0 * np.log10(1.0 / (1.0 + ratio))
    return out


def fit_filters(band_delta_db: Mapping[float, float], module: str = "",
                pack_id: str = "morgan", filter_controls=None,
                current_filters=(None, None)) -> Inversion:
    """Corner frequencies for the HPF and LPF, fitted to the measured roll-off.

    Only moves a corner when the evidence is one-sided: the target being short of
    low end across the *whole* bottom is a high-pass, whereas a dip at one
    frequency is a band gain and belongs to `fit_graphic_eq`. Anything ambiguous is
    left alone, because a wrongly-set corner removes range no band gain can put
    back. That gate is unchanged. What the corner is *set to* has been wrong twice.

    **First it was a constant.** The window edges were hardcoded at 100 Hz and
    6.3 kHz and the code took the boundary of its own window, so a deficit reaching
    100 Hz, 200 Hz or 500 Hz all produced exactly `EQHpf = 100.0`.

    **Then it was where the deficit stops**, which is not the same thing as the
    corner and is not close to it. A corner is already several dB down *at* itself
    and tens of dB down an octave away, so the frequency where a roll-off first
    becomes visible sits well above the corner that caused it: truth corners of
    4 kHz and 2 kHz came back as 6.3 kHz and 4 kHz, about an octave out every time.

    The corner is now chosen by fitting `filter_response_db` — a Butterworth
    magnitude — to the measured difference, weighted towards the range a guitar
    occupies and compared mean-free, because level is `output_level`'s job. When a
    template already has an audible corner, ``current_filters`` makes the fitted
    shape ``proposed - current`` rather than pretending the comparison started from
    an open filter. On the synthetic chain that recovers a low-pass *exactly*: 2 kHz,
    4 kHz and 8 kHz all come back as themselves, against 4 kHz, 6.3 kHz and 12.5 kHz
    before.

    A high-pass still lands low — 100/200/400 Hz recover as 80/125/125 — and the fit
    residual says why rather than leaving it to be discovered: the cab's own low-end
    roll-off is in the same measurement, so above about 200 Hz what is measured is
    not the shape of a high-pass at all. The residual crosses `FILTER_MAX_FIT_DB`
    exactly there (0.84 dB at 100 Hz, 2.43 at 200, 3.97 at 400) and a caveat says the
    corner is a rough placement for the search to improve on.

    Because the response is now in closed form, `invert()` subtracts it from the
    delta and the bands fit what is left. That replaces deleting the covered bands,
    which left the bands centred in the deleted region with nothing to fit and sent
    one to +10.6 dB on a target that was 23.7 dB *down* there.
    """
    from analysis import require

    require("fitting filter corners")
    import numpy as np

    if not band_delta_db:
        return Inversion(detail={"filter_response_db": {}})

    frequencies = np.array(sorted(band_delta_db), dtype=np.float64)
    delta = np.array([band_delta_db[f] for f in frequencies], dtype=np.float64)
    # The same weighting `fit_graphic_eq` uses, for the same reason: a third-octave
    # curve's extremes are the source's own filtering, not the amp's.
    weights = np.where((frequencies >= 50.0) & (frequencies <= 16000.0), 1.0, 0.15)

    short = delta < -FILTER_MIN_DEFICIT_DB
    long = delta > FILTER_MIN_DEFICIT_DB

    # Both ends of the passband, as counts of short bands inward from each edge.
    low_run = 0
    while low_run < len(short) and short[low_run]:
        low_run += 1
    high_run = 0
    while high_run < len(short) and short[len(short) - 1 - high_run]:
        high_run += 1
    low_rise = 0
    while low_rise < len(long) and long[low_rise]:
        low_rise += 1
    high_rise = 0
    while high_rise < len(long) and long[len(long) - 1 - high_rise]:
        high_rise += 1

    if low_run + high_run >= len(short):
        # Two maximal runs inward from opposite edges can only meet if every band is
        # short, so there is no passband to describe. Taking a corner from each end
        # anyway produced an `HPF 500 / LPF 1000` one-octave slot out of evidence
        # that says only "quieter everywhere" — a level difference, not a filter.
        return Inversion(caveats=[
            f"the target is more than {FILTER_MIN_DEFICIT_DB:.0f} dB short across "
            f"the whole spectrum, which is a level difference rather than a "
            f"roll-off, so the high-pass and low-pass were left alone"
        ], detail={"filter_response_db": {}})

    current_hpf, current_lpf = current_filters

    def candidates(path: str, current=None) -> List[Optional[float]]:
        """The corners the pack allows, on the analysis grid."""
        spec = declared(pack_id, path)
        low, high = float(spec.min), float(spec.max)
        inside = [float(f) for f in frequencies if low <= f <= high]
        # If the analysis grid has no centre inside the declared range there is
        # nothing to choose between, so the ends of the range are the only offer.
        offered = inside or [low, high]
        if current is not None and low <= float(current) <= high:
            offered.append(float(current))
        return sorted(set(offered))

    def cost_of(hpf_hz: Optional[float], lpf_hz: Optional[float]) -> float:
        proposed = filter_response_db(
            frequencies, hpf_hz=hpf_hz, lpf_hz=lpf_hz
        )
        baseline = filter_response_db(
            frequencies, hpf_hz=current_hpf, lpf_hz=current_lpf
        )
        error = (proposed - baseline) - delta
        error = error - np.average(error, weights=weights)
        return float(np.sqrt(np.average(error ** 2, weights=weights)))

    if filter_controls is None:
        hpf_path, lpf_path = (f"{module}EQ/{module}EQHpf",
                              f"{module}EQ/{module}EQLpf")
    else:
        hpf_path, lpf_path = filter_controls
    # Fitted together, not one at a time. Fitting each against the whole measurement
    # independently makes the *other* corner's roll-off look like unexplained error:
    # a target with a real 200 Hz high-pass and a real 4 kHz low-pass reported 7.6 dB
    # and 5.5 dB of misfit and said "not the shape a corner makes" about a difference
    # that was exactly two corners. Two lists of about fourteen grid points is under
    # 200 vector operations, so there is nothing to save by being clever.
    if hpf_path is None:
        hpf_options: List[Optional[float]] = [None]
    elif current_hpf is not None:
        hpf_options = (candidates(hpf_path, current_hpf)
                       if max(low_run, low_rise) >= FILTER_MIN_BANDS
                       else [float(current_hpf)])
    else:
        hpf_options = (candidates(hpf_path)
                       if low_run >= FILTER_MIN_BANDS else [None])

    if lpf_path is None:
        lpf_options: List[Optional[float]] = [None]
    elif current_lpf is not None:
        lpf_options = (candidates(lpf_path, current_lpf)
                       if max(high_run, high_rise) >= FILTER_MIN_BANDS
                       else [float(current_lpf)])
    else:
        lpf_options = (candidates(lpf_path)
                       if high_run >= FILTER_MIN_BANDS else [None])

    hpf = lpf = None
    best_cost = float("inf")
    for hpf_try in hpf_options:
        for lpf_try in lpf_options:
            cost = cost_of(hpf_try, lpf_try)
            if cost < best_cost:
                hpf, lpf, best_cost = hpf_try, lpf_try, cost

    values: Dict[str, Any] = {}
    if (hpf is not None and hpf_path is not None
            and (current_hpf is None or abs(hpf - float(current_hpf)) > 1e-9)):
        values[hpf_path] = round(float(hpf), 1)
    if (lpf is not None and lpf_path is not None
            and (current_lpf is None or abs(lpf - float(current_lpf)) > 1e-9)):
        values[lpf_path] = round(float(lpf), 1)

    caveats: List[str] = []
    if values and best_cost > FILTER_MAX_FIT_DB:
        caveats.append(
            f"the measured roll-off is not quite the shape a corner makes — the best "
            f"fit is still {best_cost:.1f} dB out — so the amp's own voicing or the "
            f"cabinet is part of what was measured. The corner is a rough placement "
            f"for the search to improve on, not a reading."
        )

    response = (
        filter_response_db(frequencies, hpf_hz=hpf, lpf_hz=lpf)
        - filter_response_db(
            frequencies, hpf_hz=current_hpf, lpf_hz=current_lpf
        )
    )
    # Nothing is said when no corner moves. A caveat is for distrusting something
    # that was written, and "the difference is not a roll-off at either end" is the
    # ordinary case — it fired on nearly every target, which is how a list of
    # caveats stops being read. `detail` records it instead.
    return Inversion(
        values=values,
        caveats=caveats,
        detail={"filter_response_db": {float(f): round(float(r), 2)
                                       for f, r in zip(frequencies, response)
                                       if abs(r) >= 0.05},
                "filter_fit_db": round(best_cost, 2) if values else None,
                "filter_deficit_bands": (int(low_run), int(high_run)),
                "filter_excess_bands": (int(low_rise), int(high_rise))},
    )


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

    if rt60 is None:
        # Not the same thing as an unconfident reading, and it used to get the same
        # sentence — "the notes decay at different rates" is a finding, and nothing
        # was found. The module header is explicit that an absent key means the
        # measurement was not supported, not that it came back zero.
        return Inversion(
            values={"reverb/reverbActive": False},
            caveats=["no decay tail was measured at all, so the reverb is left off"],
        )
    if confidence < min_confidence:
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
                     min_confidence: float = 0.75) -> Inversion:
    """Rate and depth from the amplitude-modulation spectrum.

    The confidence floor is high on purpose. A part strummed twice a second
    modulates its own envelope at 2 Hz and nothing in the audio distinguishes that
    from a 2 Hz tremolo — only the *purity* of the modulation does, which is what
    `am_confidence` measures. Switching a tremolo on because someone played in
    time would be an obvious, audible mistake.

    A modulation at a detected delay's own repeat rate is left to the echo, and
    that decision is deliberately conservative: a real 3 Hz tremolo over a 333 ms
    echo is indistinguishable by rate alone, and this declines on it. The cost of
    declining is a tremolo the search has to find; the cost of not declining was a
    full-depth tremolo written into a target that had none.
    """
    modulation = getattr(fingerprint, "modulation", {}) or {}
    time_fx = getattr(fingerprint, "time_fx", {}) or {}
    rate = modulation.get("am_rate_hz")
    confidence = float(modulation.get("am_confidence") or 0.0)

    if rate is None:
        return Inversion(
            values={"tremolo/tremoloActive": False},
            caveats=["no amplitude modulation was measured at all, so the tremolo "
                     "is left off"],
        )
    if confidence < min_confidence:
        return Inversion(
            values={"tremolo/tremoloActive": False},
            caveats=[
                f"the amplitude modulation was not a clean enough sine to be a "
                f"tremolo (confidence {confidence:.2f} against {min_confidence}); "
                f"more likely the rate the notes were played at"
            ],
        )

    # An echo modulates the envelope at its own repeat rate, and purely enough to
    # pass the confidence gate. Measured: a 420 ms delay produced a 2.1 Hz
    # modulation at confidence 0.81 against a 0.75 floor, so `invert()` wrote a
    # full-depth tremolo into a target that had none — and this was the one
    # inversion that emitted no caveat when it acted, so nothing said why.
    #
    # 1/T of a detected delay is exactly where those repeats land. The two cannot be
    # told apart from the rate, so this says that rather than claiming to know which
    # one it is; the check runs after the confidence gate so that a modulation which
    # was never tremolo-like is not attributed to an echo it has nothing to do with.
    delay_ms = time_fx.get("delay_ms")
    delay_confident = float(time_fx.get("delay_confidence") or 0.0) >= 0.15
    if delay_ms and delay_confident:
        repeat_hz = 1000.0 / float(delay_ms)
        tolerance = max(TREMOLO_RATE_TOLERANCE_HZ, 0.15 * repeat_hz)
        if abs(float(rate) - repeat_hz) <= tolerance:
            return Inversion(
                values={"tremolo/tremoloActive": False},
                caveats=[
                    f"the {float(rate):.1f} Hz amplitude modulation is within "
                    f"{tolerance:.1f} Hz of the {float(delay_ms):.0f} ms delay's own "
                    f"repeat rate ({repeat_hz:.1f} Hz). Nothing in the measurement "
                    f"separates the two, so the tremolo is left off and the echo is "
                    f"credited with it — if the reference really does have a tremolo "
                    f"at this rate, the search will have to find it."
                ],
                detail={"am_confidence": round(confidence, 3),
                        "am_indistinguishable_from": "delay repeats"},
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


def output_level(target, candidate, pack_id: str = "morgan",
                 control: str = "parameters/outputGain",
                 current_value: float = 0.0) -> Inversion:
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

    spec = declared(pack_id, control)
    if str(spec.unit or "").casefold() != "db":
        raise InversionError(
            f"{control} is the output-level control for {pack_id}, but it does not "
            "declare unit 'db'. A LUFS difference cannot be added to an unknown "
            "control scale."
        )
    low, high = float(spec.min), float(spec.max)

    difference = float(target_lufs) - float(candidate_lufs)
    before = float(current_value)
    wanted = before + difference
    clamped = min(max(wanted, float(low)), float(high))
    caveats: List[str] = []
    if abs(clamped - wanted) > 0.05:
        caveats.append(
            f"adding the {difference:+.1f} dB loudness correction to the current "
            f"{before:+.1f} dB output asks for {wanted:+.1f} dB, which exceeds the "
            f"control's {low:.0f}..{high:.0f} dB range; it was clamped to "
            f"{clamped:+.1f} dB and {wanted - clamped:+.1f} dB remains"
        )
    return Inversion(values={control: round(clamped, 2)},
                     caveats=caveats,
                     detail={
                         "lufs_difference_db": round(difference, 2),
                         "output_gain_before_db": round(before, 2),
                         "output_gain_after_db": round(clamped, 2),
                     })


# --- the whole pass ---------------------------------------------------------


def invert(target, candidate, amp: str = "sw50r", pack_id: str = "morgan",
           basis=None, basis_note: Optional[str] = None, renderer=None,
           current_settings: Optional[Mapping] = None) -> Inversion:
    """Every inversion above, in the order they depend on each other.

    Level first, because the band fit reads a mean-removed difference and a
    remaining level offset would otherwise be spread across nine band gains. Then
    the filters, which decide how much range there is to shape. Then the bands.
    Then the time effects, which are independent of all of it.
    """
    from analysis import require

    require("inverting a fingerprint")
    from analysis.compare import band_delta

    signal_path = _validated_signal_path(pack_id, amp)
    amp = signal_path.name

    result = Inversion(detail={"signal_path": amp})
    # Which signal path this is for. Without it `space.to_spec` cannot tell which
    # channel's controls matter and silently drops the calculated values. Preserve
    # the template's spelling when it already selects this path: stored enum ``1``
    # and display label ``Lead Channel`` are the same setting, not a change that
    # should incur prior/complexity cost or appear in the report.
    for control, value in signal_path.selection_settings.items():
        current = _setting_value(current_settings, control)
        if current is None or not _same_stored(pack_id, control, current, value):
            result.values[control] = value

    if signal_path.output_gain_control is not None:
        current_output = _setting_value(
            current_settings, signal_path.output_gain_control
        )
        if current_settings is not None and current_output is None:
            result.caveats.append(
                f"the template does not state {signal_path.output_gain_control}, so "
                "the loudness difference was left for the search instead of "
                "assuming the output knob starts at zero"
            )
        else:
            result.merge(output_level(
                target, candidate, pack_id=pack_id,
                control=signal_path.output_gain_control,
                current_value=0.0 if current_output is None else current_output,
            ))
            result.detail["output_gain"] = {
                "control": signal_path.output_gain_control,
                "mode": ("delta_from_template" if current_output is not None
                         else "delta_from_zero"),
                "baseline": (None if current_output is None
                             else float(current_output)),
            }
    else:
        result.caveats.append(
            f"{pack_id}'s {amp} signal path declares no output-gain control, so "
            "the measured loudness difference was left for the search"
        )

    spectral_moves: Optional[List[str]] = None
    rows = band_delta(target, candidate)
    delta = {float(row["centre_hz"]): float(row["delta_db"]) for row in rows}

    centres = _band_centres(pack_id, amp)
    if not delta:
        # Said once here rather than twice below. Both `fit_filters` and
        # `fit_graphic_eq` decline on an empty delta and their two sentences meant
        # the same thing, which is one sentence too many for a report someone reads.
        result.caveats.append(
            "no band difference could be measured between the two fingerprints, so "
            "the equaliser was left exactly as the template had it"
        )
    elif not centres:
        result.caveats.append(
            f"{pack_id} declares no graphic-EQ centres for {amp}, so no spectral "
            f"fit was attempted"
        )
    elif _unreadable_eq_gates(signal_path, current_settings, pack_id):
        # Nothing in the section is decidable without its gate. Whether a stored
        # band value was audible, whether a corner contributed, whether switching
        # the section on would expose values the render never contained — every one
        # of those turns on a control the template does not state. The alternative
        # is to guess "bypassed", overwrite nine bands with neutral zero and call it
        # a tidy-up, which is what this used to do.
        unreadable = _unreadable_eq_gates(signal_path, current_settings, pack_id)
        plural = len(unreadable) > 1
        result.caveats.append(
            f"the template does not state {', '.join(unreadable)}, so there is no "
            f"way to know whether its equaliser was in circuit for the render this "
            f"was measured against. Nothing in that section was touched — not the "
            f"bands, not the corners, not the "
            f"{'gates themselves' if plural else 'gate itself'} — because every one "
            f"of those decisions needs an answer this template does not give. Set "
            f"{'them' if plural else 'it'} in the template and run again to have the "
            f"equaliser inverted"
        )
    else:
        filters = fit_filters(
            delta, module=amp, pack_id=pack_id,
            filter_controls=(signal_path.eq_hpf_control,
                             signal_path.eq_lpf_control),
            current_filters=_current_filter_values(
                signal_path, current_settings, pack_id
            ),
        )
        result.merge(filters)

        # A measured basis is a property of the *backend*, not of the pack, so the
        # renderer is what answers for it. `eq_basis.json` describes the plugin;
        # the synthetic chain builds its own bands from `FALLBACK_Q`, and fitting
        # the plugin's overlap to the chain's audio makes the fit *worse* — which
        # is what two of `tests/test_invert.py`'s assertions measured the moment
        # this module tried to load the file by pack alone.
        #
        # Asked here rather than by the caller because the frequencies the basis
        # has to line up with are `sorted(delta)`, which only exists at this point.
        basis_noise = None
        if basis is None and renderer is not None:
            ask = getattr(renderer, "eq_basis", None)
            found = ask(amp, sorted(delta)) if ask is not None else None
            if found is not None:
                _validate_basis_provenance(found, renderer)
                basis, basis_note = found
                basis_noise = getattr(found, "band_noise_db", None)
                result.detail["eq_basis"] = {
                    "artifact": f"packs/{pack_id}/eq_basis.json",
                    "signal_path": amp,
                    "signal_path_sha256": getattr(
                        found, "signal_path_sha256", None
                    ),
                    "provenance_schema": getattr(
                        found, "provenance_schema", None
                    ),
                    "renderer_build": getattr(found, "renderer_build", None),
                }
        if basis is not None and basis_note:
            result.caveats.append(basis_note)

        # The bands must not re-correct what a filter corner just handled, so they
        # fit the difference minus the corners' modelled response. Subtracted rather
        # than deleted: removing the covered bands from the delta left the bands
        # centred in the removed region with nothing to fit against, and one came out
        # at +10.6 dB on a target that was 23.7 dB *down* there.
        spectral = fit_graphic_eq(
            delta, centres, basis=basis,
            bounds_db=_band_correction_bounds(
                signal_path, current_settings, pack_id
            ),
            module=amp, pack_id=pack_id,
            accounted_for=filters.detail.get("filter_response_db"),
            band_controls=signal_path.eq_band_controls,
            band_noise_db=_renderer_band_noise(
                renderer, measured=basis_noise
            ))
        spectral = _apply_band_corrections(
            spectral, signal_path, current_settings, pack_id,
            activates_eq=bool(filters.values),
        )
        result.merge(spectral)
        # `None` when the template was not supplied: the standalone-helper contract
        # writes absolute gains, where a non-zero value *is* the move.
        spectral_moves = spectral.detail.get("eq_bands_moved")
        unwritable = _unwritable_bands(signal_path, current_settings, pack_id)
        if unwritable:
            plural = len(unwritable) > 1
            result.caveats.append(
                f"the template does not state {', '.join(unwritable)}, so no "
                f"correction was fitted for {'them' if plural else 'it'} and this "
                f"pass leaves {'those bands' if plural else 'that band'} exactly as "
                f"the template had {'them' if plural else 'it'}"
            )
        moved = any(value for value in spectral.values.values())
        # Enable the EQ only when the inversion actually uses it. If every move is
        # below the renderer floor, omit the gates: omission preserves whether the
        # template's flat EQ was active or bypassed. Writing False here changed an
        # already-enabled Tone King template even though the report said the EQ was
        # left exactly as it was.
        if moved or filters.values:
            _neutralise_dormant_filters(
                result, signal_path, current_settings, pack_id
            )
            for control in signal_path.eq_enable_controls:
                result.values[control] = True

    band_moves = spectral_moves if spectral_moves is not None else [
        control for control in signal_path.eq_band_controls
        if result.values.get(control)
    ]
    if band_moves:
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

    unsupported = []
    if _declares_all(pack_id, (
        "delay/delayActive", "delay/delayTime", "delay/delayFeedback"
    )):
        result.merge(delay_settings(target, pack_id=pack_id))
    else:
        unsupported.append("delay")
    if _declares_all(pack_id, (
        "reverb/reverbActive", "reverb/reverbDecay", "reverb/reverbPreDelay"
    )):
        result.merge(reverb_settings(target, pack_id=pack_id))
    else:
        unsupported.append("reverb")
    if _declares_all(pack_id, (
        "tremolo/tremoloActive", "tremolo/tremoloRate", "tremolo/tremoloDepth"
    )):
        result.merge(tremolo_settings(target, pack_id=pack_id))
    else:
        unsupported.append("tremolo")
    if unsupported:
        result.caveats.append(
            f"{pack_id} does not map {', '.join(unsupported)} controls to the "
            "units these direct inversions require, so those sections were left "
            "exactly as the template had them for the search to hear"
        )
    return result


def _validated_signal_path(pack_id: str, requested: str):
    """The declared path, accepting its id, amp name, or selector display value."""
    from packs.calibration import CalibrationError, signal_paths
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    try:
        paths = signal_paths(pack)
    except CalibrationError as error:
        raise InversionError(str(error)) from error
    wanted = str(requested).casefold()
    for name, path in paths.items():
        aliases = {name.casefold()}
        for value in path.selection_settings.values():
            aliases.add(str(value).casefold())
        for display, prefix in pack.amp_modules.items():
            if prefix == name:
                aliases.add(display.casefold())
        if wanted in aliases:
            return path
    raise InversionError(
        f"{requested!r} is not a signal path in pack {pack_id!r}.\n"
        f"  Accepted: {', '.join(paths)}."
    )


def selected_signal_path(pack_id: str, values: Mapping) -> Optional[str]:
    """The path selected in a decoded template vector."""
    from packs.calibration import selected_signal_path as selected
    from packs.loader import load_pack

    return selected(load_pack(pack_id), values)


def resolve_signal_path(pack_id: str, requested: str) -> str:
    """Canonical path id for a CLI-supplied id, amp name, or selector label."""
    return _validated_signal_path(pack_id, requested).name


def signal_path_selection(pack_id: str, requested: str) -> Dict[str, Any]:
    """Settings that select a canonical or aliased path before it is rendered."""
    return dict(_validated_signal_path(pack_id, requested).selection_settings)


def _declares_all(pack_id: str, paths: Sequence[str]) -> bool:
    from packs.loader import load_pack

    declared_paths = load_pack(pack_id).parameters
    return all(path in declared_paths for path in paths)


def _renderer_band_noise(renderer, measured=None):
    """Frequency-aligned repeat variation, or a scalar fallback.

    Direct helper calls have no backend and retain the historical 0.3 dB floor.
    A real renderer is authoritative. A measured EQ basis can locate the variation
    by frequency; backends without that measurement retain their metadata maximum.
    """
    if renderer is None:
        return BAND_NOISE_FLOOR_DB
    if measured is not None:
        return measured
    metadata = getattr(renderer, "metadata", None)
    if metadata is None:
        return BAND_NOISE_FLOOR_DB
    return max(0.0, float(getattr(metadata(), "band_noise_db", 0.0) or 0.0))


def _validate_basis_provenance(found, renderer) -> None:
    """Refuse a modern calibration measured by another host build or mode.

    Older Morgan artifacts predate the full AudioUnitRenderer identity and retain
    their existing plugin-version guard. Modern artifacts record the Python/Swift
    host hash and every quality option that changes samples; both must match the
    backend asking to use the basis.
    """
    schema = getattr(found, "provenance_schema", None)
    if schema == "legacy-morgan-au-render-server-1":
        return
    if schema != "eq-basis-provenance-1":
        raise InversionError(
            "the measured EQ basis has missing or unsupported provenance schema "
            f"{schema!r}. Re-run scripts/measure_eq_basis.py with this renderer."
        )
    metadata = renderer.metadata()
    identity = (
        ("renderer id", "renderer_id"),
        ("plugin version", "plugin_version"),
        ("sample rate", "sample_rate"),
        ("block size", "block_size"),
        ("renderer build", "renderer_build"),
        ("quality mode", "quality_mode"),
    )
    missing = []
    mismatches = []
    for label, field_name in identity:
        recorded = getattr(found, field_name, None)
        current = getattr(metadata, field_name, None)
        if recorded is None or recorded == "":
            missing.append(label)
        elif str(recorded) != str(current):
            mismatches.append(f"{label} {recorded!r} vs {current!r}")
    if missing or mismatches:
        reasons = []
        if missing:
            reasons.append("missing " + ", ".join(missing))
        reasons.extend(mismatches)
        raise InversionError(
            "the measured EQ basis does not match this renderer ("
            + "; ".join(reasons)
            + "). Re-run scripts/measure_eq_basis.py with this renderer and its "
              "current options before inverting."
        )


def _setting_value(values: Optional[Mapping], path: str):
    """Read one human setting from any key spelling accepted by the search space."""
    if values is None:
        return None
    from match.space import _get

    module, _, key = path.rpartition("/")
    return _get(values, (module, key))


def _same_stored(pack_id: str, path: str, left, right) -> bool:
    """Whether two human/stored spellings represent the same plugin value."""
    from packs.calibration import spec_for
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    spec = spec_for(pack, path)
    try:
        return str(pack.to_stored(spec, left, warnings=[])) == str(
            pack.to_stored(spec, right, warnings=[])
        )
    except ValueError:
        return False


def _apply_band_corrections(
    correction: Inversion, signal_path, current_settings: Optional[Mapping],
    pack_id: str, activates_eq: bool = False,
) -> Inversion:
    """Turn fitted EQ deltas into absolute controls relative to the template.

    ``band_delta`` compares the target with the rendered template, so its solved
    gains are corrections. A +4 dB solve against a template band already at +2 dB
    means write +6 dB, not +4 dB. Zero means preserve the template and is omitted.
    Calls without template settings retain the historical absolute-result contract
    used by the standalone helpers and synthetic tests.
    """
    if current_settings is None:
        return correction

    from packs.calibration import spec_for
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    was_active = _eq_is_active(signal_path, current_settings, pack_id) is True
    baselines = _band_baselines(signal_path, current_settings, pack_id)
    values: Dict[str, Any] = {}
    caveats = list(correction.caveats)
    missing = []
    moved: List[str] = []
    has_correction = any(float(correction.values.get(control, 0.0) or 0.0) != 0.0
                         for control in signal_path.eq_band_controls)
    will_enable = has_correction or activates_eq
    for control in signal_path.eq_band_controls:
        change = float(correction.values.get(control, 0.0) or 0.0)
        # Enabling a bypassed EQ exposes every stored band at once. Emit neutral
        # zero for untouched bands so dormant template values cannot suddenly color
        # the sound. With an already-active EQ, zero remains "preserve this band".
        if change == 0.0 and (was_active or not will_enable):
            continue
        before = baselines.get(control)
        if before is None:
            missing.append(control)
            continue
        spec = spec_for(pack, control)
        wanted = float(before) + change
        clamped = min(max(wanted, float(spec.min)), float(spec.max))
        values[control] = round(clamped, 2)
        if values[control] != round(float(before), 2):
            moved.append(control)
        if abs(clamped - wanted) > 0.005:
            caveats.append(
                f"adding the {change:+.2f} dB correction to {control}'s current "
                f"{float(before):+.2f} dB asks for {wanted:+.2f} dB, outside its "
                f"{float(spec.min):g}..{float(spec.max):g} dB range; it was "
                f"clamped to {clamped:+.2f} dB"
            )
    if missing:
        caveats.append(
            f"the template does not state {', '.join(missing)}, so their fitted "
            f"corrections were left for the search rather than treated as absolute "
            f"EQ values. The fit residual describes the solution before they were "
            f"dropped"
        )
    if not was_active and will_enable:
        caveats.append(
            "the template's equaliser was bypassed, so its dormant band values "
            "were reset to neutral before the fitted correction enabled it"
        )
    detail = dict(correction.detail)
    detail["eq_bands_moved"] = list(moved)
    return Inversion(values=values, caveats=caveats, detail=detail)


def _band_correction_bounds(signal_path, current_settings, pack_id: str):
    """Per-band delta limits after accounting for each audible template value.

    A band whose audible value the template does not state gets no room at all.
    Solving for a correction that cannot then be written left `eq_residual_db`
    describing a solution nobody applied — the same class of defect as measuring
    the fit before the noise floor zeroed it. `lsq_linear` requires a strictly
    positive interval, and anything inside this one rounds to 0.00 dB.
    """
    if current_settings is None:
        return EQ_BOUNDS_DB

    from packs.calibration import spec_for
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    baselines = _band_baselines(signal_path, current_settings, pack_id)
    unwritable = _unwritable_bands(signal_path, current_settings, pack_id)
    lower = []
    upper = []
    for control in signal_path.eq_band_controls:
        if control in unwritable:
            lower.append(-1e-9)
            upper.append(1e-9)
            continue
        spec = spec_for(pack, control)
        baseline = baselines.get(control)
        baseline = 0.0 if baseline is None else float(baseline)
        lower.append(float(spec.min) - baseline)
        upper.append(float(spec.max) - baseline)
    return lower, upper


def _unwritable_bands(signal_path, current_settings, pack_id: str) -> Tuple[str, ...]:
    """Bands with no audible value to add a correction to.

    Only reachable with an audible equaliser: a bypassed one contributes nothing,
    so its baseline is a known zero rather than an unknown.
    """
    if current_settings is None:
        return ()
    baselines = _band_baselines(signal_path, current_settings, pack_id)
    return tuple(control for control in signal_path.eq_band_controls
                 if baselines.get(control) is None)


def _band_baselines(signal_path, current_settings, pack_id: str):
    """Audible band values: stored when enabled, neutral zero when bypassed.

    `None` for every band when the gate cannot be read, which makes them
    unwritable — a correction added to an unknown baseline is an unknown value.
    """
    active = _eq_is_active(signal_path, current_settings, pack_id)
    if active is None:
        return {control: None for control in signal_path.eq_band_controls}
    return {
        control: (_setting_value(current_settings, control) if active else 0.0)
        for control in signal_path.eq_band_controls
    }


def _current_filter_values(signal_path, current_settings, pack_id: str):
    """Audible HPF/LPF corners, or open filters when the EQ is bypassed.

    A stored corner behind a bypassed section contributes nothing to the candidate
    render. Treating it as the baseline would fit a transition from a filter that was
    never heard and can move the requested corner in the wrong direction.
    """
    # An unreadable gate means the corners' contribution is unknown too, so the fit
    # gets no baseline rather than a guessed-open one.
    if current_settings is None or _eq_is_active(
        signal_path, current_settings, pack_id
    ) is not True:
        return None, None

    def value(control):
        if control is None:
            return None
        found = _setting_value(current_settings, control)
        return None if found is None else float(found)

    return value(signal_path.eq_hpf_control), value(signal_path.eq_lpf_control)


def _neutralise_dormant_filters(result: Inversion, signal_path,
                                current_settings, pack_id: str) -> None:
    """Open untouched corners before enabling a previously bypassed EQ."""
    # Only a gate that is known to be off leaves dormant corners to neutralise.
    if current_settings is None or _eq_is_active(
        signal_path, current_settings, pack_id
    ) is not False:
        return
    from packs.calibration import spec_for
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    reset = []
    for control, edge in (
        (signal_path.eq_hpf_control, "min"),
        (signal_path.eq_lpf_control, "max"),
    ):
        if control is None or control in result.values:
            continue
        spec = spec_for(pack, control)
        opened = float(getattr(spec, edge))
        current = _setting_value(current_settings, control)
        if current is not None and abs(float(current) - opened) <= 1e-9:
            continue
        result.values[control] = opened
        reset.append(control)
    if reset:
        result.caveats.append(
            "the template's equaliser was bypassed, so its untouched dormant "
            f"filter values were opened before enabling it: {', '.join(reset)}"
        )


def _eq_is_active(signal_path, current_settings, pack_id: str) -> Optional[bool]:
    """Whether the path's declared gates put its EQ in circuit — or `None`.

    Three-valued on purpose. A gate the template does not state is *unknown*, not
    off, and the difference decides nine controls: reading absence as "bypassed"
    makes every stored band value a dormant one, which licenses overwriting all of
    them with neutral zero and switching the section on. If the equaliser was in
    fact audible, that silently discards the tone the template was carrying and
    reports it as a tidy-up.

    `Space.active` states the same rule for the same reason — a value nobody
    supplied is a value nobody knows — and this helper used to take the opposite
    reading of it. Neither committed pack can produce the case: Morgan and Tone
    King both declare their gates and both appear in any real preset. A pack that
    excludes one from the search space, or a preset that omits it, can.
    """
    if not signal_path.eq_enable_controls:
        return True
    from packs.calibration import spec_for
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    for control in signal_path.eq_enable_controls:
        value = _setting_value(current_settings, control)
        if value is None:
            return None
        spec = spec_for(pack, control)
        try:
            stored = str(pack.to_stored(spec, value, warnings=[])).casefold()
        except ValueError:
            # A value that will not translate is not a reading either.
            return None
        if stored not in {"1", "true"}:
            return False
    return True


def _unreadable_eq_gates(signal_path, current_settings, pack_id: str) -> List[str]:
    """The gates that made `_eq_is_active` unable to answer, for the caveat."""
    if current_settings is None:
        return []
    from packs.calibration import spec_for
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    unreadable = []
    for control in signal_path.eq_enable_controls:
        value = _setting_value(current_settings, control)
        if value is None:
            unreadable.append(control)
            continue
        try:
            pack.to_stored(spec_for(pack, control), value, warnings=[])
        except ValueError:
            unreadable.append(control)
    return unreadable


def _band_centres(pack_id: str, amp: str) -> List[float]:
    """The declared centres of one signal path's graphic EQ, in band order."""
    from packs.calibration import signal_paths
    from packs.loader import load_pack

    pack = load_pack(pack_id)
    path = signal_paths(pack).get(amp)
    if path is None:
        return []
    centres = []
    for control in path.eq_band_controls:
        spec = pack.parameters.get(control)
        if spec is None or spec.centre_hz is None:
            return []
        centres.append(float(spec.centre_hz))
    return centres
