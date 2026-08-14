"""Declared signal paths shared by the real-plugin calibration commands.

The matching surface is not one topology. Morgan gives every amp its own module
prefix; Tone King puts two selectable channels and one shared graphic EQ in a
flat namespace. Calibration must know which selector makes a control audible,
so inferring paths from spelling alone would turn a rename into a plausible but
meaningless measurement.

New packs declare ``calibration.signal_paths`` in their manifest. Morgan's
well-established module convention remains as a compatibility fallback so its
manifest and committed measurements do not need a mechanical rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple


class CalibrationError(ValueError):
    """A pack does not provide a complete, valid measurement path."""


@dataclass(frozen=True)
class SignalPath:
    name: str
    settings: Mapping[str, Any]
    volume_control: Optional[str]
    eq_band_controls: Tuple[str, ...]
    eq_enable_controls: Tuple[str, ...]
    eq_hpf_control: Optional[str] = None
    eq_lpf_control: Optional[str] = None
    output_gain_control: Optional[str] = None


def signal_paths(pack) -> Dict[str, SignalPath]:
    """Return the pack's ordered, validated calibration paths."""
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
            "nor an amp_modules topology that can be measured"
        )
    return paths


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
    settings = {**common_settings, **local_settings}
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
    for control in bands:
        _spec(pack, control, f"{name} EQ band")
    for control in enables:
        _spec(pack, control, f"{name} EQ enable control")

    return SignalPath(
        name=name,
        settings=dict(settings),
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
        settings: Dict[str, Any] = {
            "/selectedAmp": _amp_name(pack, amp),
        }
        if "parameters/gateActive" in pack.parameters:
            settings["parameters/gateActive"] = False
        paths[amp] = SignalPath(
            name=amp,
            settings=settings,
            volume_control=volume if volume in pack.parameters else None,
            eq_band_controls=tuple(bands),
            eq_enable_controls=tuple(control for control in (
                f"{amp}EQ/{amp}EQActive", "eqParameters/sectionActive"
            ) if control in pack.parameters),
            eq_hpf_control=_present(pack, f"{amp}EQ/{amp}EQHpf"),
            eq_lpf_control=_present(pack, f"{amp}EQ/{amp}EQLpf"),
            output_gain_control=_present(pack, "parameters/outputGain"),
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
    return _spec(pack, path, "calibration control")
