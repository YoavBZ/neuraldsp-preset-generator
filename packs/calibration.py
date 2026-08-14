"""Declared signal paths shared by calibration and direct inversion.

Morgan gives every amp its own module prefix. Tone King puts two selectable
channels and one shared graphic EQ in a flat namespace. A tool that measures or
inverts those controls needs the same answer to "which selector makes this path
audible?", so that topology belongs to the pack rather than to either caller.

New packs declare ``calibration.signal_paths`` in their manifest. Morgan's
well-established module convention remains as a compatibility fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Dict, Mapping, Optional, Tuple


class CalibrationError(ValueError):
    """A pack does not provide a complete, valid signal path."""


@dataclass(frozen=True)
class SignalPath:
    name: str
    # Everything needed to render a neutral calibration point.
    settings: Mapping[str, Any]
    # Only the path-local settings that select this signal path. Direct inversion
    # writes these, not the neutral calibration settings that disable every effect.
    selection_settings: Mapping[str, Any]
    volume_control: Optional[str]
    eq_band_controls: Tuple[str, ...]
    eq_enable_controls: Tuple[str, ...]
    eq_hpf_control: Optional[str] = None
    eq_lpf_control: Optional[str] = None
    output_gain_control: Optional[str] = None


def signal_paths(pack) -> Dict[str, SignalPath]:
    """Return the pack's ordered, validated signal paths."""
    declared = pack.calibration.get("signal_paths") if pack.calibration else None
    if declared is not None:
        if not isinstance(declared, dict) or not declared:
            raise CalibrationError("calibration.signal_paths must be a non-empty object")
        output = pack.calibration.get("output_gain_control")
        common = pack.calibration.get("settings", {})
        if not isinstance(common, dict):
            raise CalibrationError("calibration.settings must be an object")
        paths = {
            str(name): _declared_path(pack, str(name), row, output, common)
            for name, row in declared.items()
        }
    else:
        paths = _legacy_amp_paths(pack)

    if not paths:
        raise CalibrationError(
            f"packs/{pack.pack_id} declares neither calibration.signal_paths "
            "nor an amp_modules topology that can be addressed"
        )
    return paths


def selected_signal_path(pack, values: Mapping) -> Optional[str]:
    """Which declared path ``values`` selects, or ``None`` when it does not say.

    Values may use tuple, bare top-level, canonical top-level, or module/path
    keys. Both expected and actual values go through the pack, so a stored enum
    index and its display label select the same path.
    """
    paths = signal_paths(pack)
    matches = []
    for name, path in paths.items():
        if not path.selection_settings:
            continue
        matched = True
        for control, expected in path.selection_settings.items():
            actual = _mapping_value(values, control)
            if actual is None:
                matched = False
                break
            spec = spec_for(pack, control)
            try:
                expected_stored = pack.to_stored(spec, expected, warnings=[])
                actual_stored = pack.to_stored(spec, actual, warnings=[])
            except ValueError:
                matched = False
                break
            if str(actual_stored) != str(expected_stored):
                matched = False
                break
        if matched:
            matches.append(name)
    if len(matches) == 1:
        return matches[0]
    if len(paths) == 1 and not next(iter(paths.values())).selection_settings:
        return next(iter(paths))
    return None


def eq_basis_settings(pack, path: SignalPath) -> Dict[str, Any]:
    """The complete neutral state used to measure one EQ basis.

    Keeping this beside the topology prevents the measurement command and the
    consumer's provenance check from independently reconstructing what "flat"
    meant. The returned values are human values; the renderer performs the normal
    pack translation when it writes them.
    """
    settings = dict(path.settings)
    for control in path.eq_enable_controls:
        settings[control] = True
    for control in path.eq_band_controls:
        settings[control] = 0.0
    for control, extreme in (
        (path.eq_hpf_control, "min"),
        (path.eq_lpf_control, "max"),
    ):
        if control is None:
            continue
        spec = spec_for(pack, control)
        value = spec.min if extreme == "min" else spec.max
        if value is None:
            raise CalibrationError(
                f"{path.name} EQ {extreme}imum control {control!r} has no "
                "declared range, so a flat calibration state cannot be reproduced"
            )
        settings[control] = float(value)
    return settings


def eq_basis_topology_sha256(pack, path: SignalPath) -> str:
    """Canonical identity of every topology fact that shapes an EQ basis."""

    def stored(settings: Mapping[str, Any]):
        output = []
        for control, value in sorted(settings.items()):
            spec = spec_for(pack, control)
            output.append([control, str(pack.to_stored(spec, value, warnings=[]))])
        return output

    document = {
        "schema": "eq-basis-topology-1",
        "pack": pack.pack_id,
        "signal_path": path.name,
        "flat_settings": stored(eq_basis_settings(pack, path)),
        "selection_settings": stored(path.selection_settings),
        "volume_control": path.volume_control,
        "eq_band_controls": list(path.eq_band_controls),
        "eq_enable_controls": list(path.eq_enable_controls),
        "eq_hpf_control": path.eq_hpf_control,
        "eq_lpf_control": path.eq_lpf_control,
        "output_gain_control": path.output_gain_control,
    }
    payload = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _declared_path(
    pack, name: str, row: Any, output: Any, common_settings: Mapping[str, Any]
) -> SignalPath:
    if not isinstance(row, dict):
        raise CalibrationError(f"calibration.signal_paths.{name} must be an object")
    local_settings = row.get("settings", {})
    if not isinstance(local_settings, dict):
        raise CalibrationError(
            f"calibration.signal_paths.{name}.settings must be an object"
        )
    selection_settings = row.get("selection_settings", {})
    if not isinstance(selection_settings, dict):
        raise CalibrationError(
            f"calibration.signal_paths.{name}.selection_settings must be an object"
        )
    overlap = set(local_settings) & set(selection_settings)
    if overlap:
        raise CalibrationError(
            f"calibration.signal_paths.{name} repeats "
            f"{', '.join(sorted(overlap))} in settings and selection_settings"
        )
    # Selection is part of a neutral calibration render, but remains distinct so
    # inversion never writes path-local setup values whose only purpose is to make
    # a measurement comparable.
    settings = {**common_settings, **local_settings, **selection_settings}
    for control, value in settings.items():
        spec = _spec(pack, control, f"{name} setting")
        try:
            pack.to_stored(spec, value, warnings=[])
        except ValueError as error:
            raise CalibrationError(
                f"{name} setting {control}={value!r} is invalid: {error}"
            ) from error

    volume = row.get("volume_control")
    bands = _control_list(row, "eq_band_controls", name)
    enables = _control_list(row, "eq_enable_controls", name)
    hpf = row.get("eq_hpf_control")
    lpf = row.get("eq_lpf_control")
    for control, purpose in (
        (volume, "volume control"),
        (output, "output gain control"),
        (hpf, "EQ high-pass control"),
        (lpf, "EQ low-pass control"),
    ):
        if control is not None:
            _spec(pack, control, f"{name} {purpose}")
    if output is not None:
        output_spec = _spec(pack, output, f"{name} output gain control")
        if str(output_spec.unit or "").casefold() != "db":
            raise CalibrationError(
                f"{name} output gain control {output!r} must declare unit 'db'; "
                "direct inversion adds a measured loudness difference to it"
            )
    for control in bands:
        _spec(pack, control, f"{name} EQ band")
    for control in enables:
        _spec(pack, control, f"{name} EQ enable control")

    return SignalPath(
        name=name,
        settings=dict(settings),
        selection_settings=dict(selection_settings),
        volume_control=volume,
        eq_band_controls=bands,
        eq_enable_controls=enables,
        eq_hpf_control=hpf,
        eq_lpf_control=lpf,
        output_gain_control=output,
    )


def _legacy_amp_paths(pack) -> Dict[str, SignalPath]:
    paths: Dict[str, SignalPath] = {}
    for amp in sorted(set(pack.amp_modules.values())):
        volume = f"{amp}Amp/{amp}Volume"
        bands = []
        for index in range(1, 32):
            control = f"{amp}EQ/{amp}EQBand{index}"
            if control not in pack.parameters:
                break
            bands.append(control)
        if volume not in pack.parameters and not bands:
            continue
        selection = {"/selectedAmp": _amp_name(pack, amp)}
        settings: Dict[str, Any] = dict(selection)
        if "parameters/gateActive" in pack.parameters:
            settings["parameters/gateActive"] = False
        output = _present(pack, "parameters/outputGain")
        if output is not None and str(
            pack.parameters[output].unit or ""
        ).casefold() != "db":
            raise CalibrationError(
                f"{amp} output gain control {output!r} must declare unit 'db'; "
                "direct inversion adds a measured loudness difference to it"
            )
        paths[amp] = SignalPath(
            name=amp,
            settings=settings,
            selection_settings=selection,
            volume_control=volume if volume in pack.parameters else None,
            eq_band_controls=tuple(bands),
            eq_enable_controls=tuple(control for control in (
                f"{amp}EQ/{amp}EQActive", "eqParameters/sectionActive"
            ) if control in pack.parameters),
            eq_hpf_control=_present(pack, f"{amp}EQ/{amp}EQHpf"),
            eq_lpf_control=_present(pack, f"{amp}EQ/{amp}EQLpf"),
            output_gain_control=output,
        )
    return paths


def _control_list(row: Mapping[str, Any], key: str, name: str) -> Tuple[str, ...]:
    controls = row.get(key, ())
    if not isinstance(controls, (list, tuple)):
        raise CalibrationError(f"calibration.signal_paths.{name}.{key} must be a list")
    result = tuple(controls)
    if any(not isinstance(control, str) or not control for control in result):
        raise CalibrationError(
            f"calibration.signal_paths.{name}.{key} must contain parameter paths"
        )
    if len(result) != len(set(result)):
        raise CalibrationError(
            f"calibration.signal_paths.{name}.{key} contains a duplicate control"
        )
    return result


def _amp_name(pack, amp: str) -> str:
    for display, prefix in pack.amp_modules.items():
        if prefix == amp:
            return display
    raise CalibrationError(
        f"{pack.pack_id} does not say which selectedAmp member selects {amp}"
    )


def _present(pack, path: str) -> Optional[str]:
    return path if path in pack.parameters else None


def _mapping_value(values: Mapping, path: str):
    module, _, key = path.rpartition("/")
    candidates = ((module, key), path, path.lstrip("/"))
    for candidate in candidates:
        if candidate in values:
            return values[candidate]
    return None


def _spec(pack, path: Any, purpose: str):
    if not isinstance(path, str) or not path:
        raise CalibrationError(f"{purpose} must be a non-empty parameter path")
    canonical = path if "/" in path else f"/{path}"
    spec = pack.parameters.get(canonical)
    if spec is None:
        raise CalibrationError(
            f"{purpose} {path!r} is not declared in packs/{pack.pack_id}/manifest.json"
        )
    if not spec.writable:
        raise CalibrationError(f"{purpose} {path!r} is read-only")
    return spec


def spec_for(pack, path: str):
    """The writable ParamSpec for a validated or caller-supplied path."""
    return _spec(pack, path, "signal-path control")
