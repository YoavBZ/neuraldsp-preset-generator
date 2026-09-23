"""Exact Tone King preset playback for private listening comparisons.

The calibrated AudioUnitRenderer keeps its measured source identity unchanged.
This subclass loads one pinned preset blob instead of the plugin's boot state,
and has its own build identity so neither its audio nor its code can be mistaken
for a calibration render. It deliberately accepts no per-render knob edits.
"""

from __future__ import annotations

import hashlib
import math
import pathlib
import subprocess
from typing import Mapping, Optional

from format.parser import parse
from format.structured import build
from packs.loader import detect_pack

from .renderer_au import AudioUnitError, AudioUnitRenderer, PROBE_SOURCE


def toneking_channel(blob: bytes) -> str:
    """Read the channel from an intact Tone King preset, without rewriting it."""
    preset = build(parse(blob))
    detected = detect_pack(preset.file_header)
    if detected is None or detected.pack_id != "toneking":
        raise AudioUnitError("state template is not a Tone King preset")
    selectors = [parameter for parameter in preset.parameters
                 if not parameter.module_path and parameter.key == "ampType"]
    if len(selectors) != 1 or ("", "ampType") in preset.valueless:
        raise AudioUnitError("Tone King preset needs exactly one valued ampType")
    try:
        value = float(selectors[0].value)
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError("fractional selector")
        return detected.parameters["/ampType"].members[str(int(value))]
    except (TypeError, ValueError, KeyError) as error:
        raise AudioUnitError("Tone King preset has an invalid ampType") from error


def complete_toneking_state(blob: bytes) -> tuple[int, int]:
    """Check every declared slot is present, including genuinely valueless ones."""
    preset = build(parse(blob))
    detected = detect_pack(preset.file_header)
    if detected is None or detected.pack_id != "toneking":
        raise AudioUnitError("state template is not a Tone King preset")
    supplied = {(p.module_path, p.key) for p in preset.parameters}
    valueless = set(preset.valueless)
    if (len(supplied) != len(preset.parameters) or
            len(valueless) != len(preset.valueless) or
            supplied & valueless):
        raise AudioUnitError("Tone King preset repeats a state slot")
    present = {f"/{key}" for module, key in supplied | valueless if not module}
    missing = set(detected.parameters) - present
    if missing:
        raise AudioUnitError(
            f"Tone King preset omits {len(missing)} declared state slot(s); "
            f"first missing: {sorted(missing)[0]}")
    return len(supplied), len(valueless)


class ToneKingPresetRenderer(AudioUnitRenderer):
    """Render a pinned Tone King state byte-for-byte through a fresh AU process."""

    def __init__(self, state_template: pathlib.Path, **kwargs):
        policy = kwargs.pop("process_policy", "fresh")
        if policy != "fresh":
            raise AudioUnitError("exact Tone King preset playback requires process_policy=fresh")
        try:
            blob = pathlib.Path(state_template).read_bytes()
        except OSError as error:
            raise AudioUnitError(f"could not read state template: {error}") from error
        self.channel = toneking_channel(blob)
        self._preset_blob = blob
        self._preset_sha256 = hashlib.sha256(blob).hexdigest()
        self.state_preflight = None
        super().__init__("toneking", process_policy="fresh", **kwargs)

    def verify_preset_state(self) -> dict:
        """Ask a disposable plugin instance what it retained after this state write.

        The renderer's own fresh instance receives the same pinned bytes. This
        cross-instance round trip is a plugin-backed preflight, not an assertion
        that the render server exposes its live state after every render.
        """
        if self.state_preflight is not None:
            return self.state_preflight
        valued_count, valueless_count = complete_toneking_state(self._preset_blob)
        requested = build(parse(self._preset_blob))
        supplied = {(p.module_path, p.key): p.value for p in requested.parameters}
        valueless = set(requested.valueless)

        binary = self._workdir / "au_probe"
        if not binary.exists():
            self._compile(PROBE_SOURCE, binary)
        state_path = self._workdir / "preset-preflight.bin"
        listing = self._workdir / "preset-preflight-list.txt"
        capture = self._workdir / "preset-preflight-readback"
        state_path.write_bytes(self._preset_blob)
        listing.write_text(str(state_path) + "\n")
        triple = self._au_triple()
        try:
            result = subprocess.run(
                [str(binary), triple["type"], triple["subtype"],
                 triple["manufacturer"], "setstate", str(listing), str(capture)],
                capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired as error:
            raise AudioUnitError("Tone King preset preflight timed out") from error
        retained_path = capture / "0.bin"
        if result.returncode != 0 or not retained_path.is_file():
            raise AudioUnitError(
                f"Tone King plugin did not return an applied state "
                f"(exit {result.returncode}): {result.stderr.strip()}")
        retained_blob = retained_path.read_bytes()
        if toneking_channel(retained_blob) != self.channel:
            raise AudioUnitError("Tone King plugin retained a different amp channel")
        retained = build(parse(retained_blob))
        actual = {(p.module_path, p.key): p.value for p in retained.parameters}
        if not valueless.issubset(set(retained.valueless)):
            raise AudioUnitError("Tone King plugin changed a valueless state slot")
        max_delta = 0.0
        pack = self._pack()
        for key, expected in supplied.items():
            observed = actual.get(key)
            if observed is None:
                raise AudioUnitError(f"Tone King plugin discarded preset control {key[1]}")
            spec = pack.get(*key)
            if spec is None or spec.kind not in ("rotation", "fraction", "metered"):
                if expected != observed:
                    raise AudioUnitError(f"Tone King plugin changed preset control {key[1]}")
                continue
            try:
                before, after = float(expected), float(observed)
            except (TypeError, ValueError):
                raise AudioUnitError(f"Tone King plugin returned nonnumeric {key[1]}") from None
            if not math.isfinite(before) or not math.isfinite(after):
                raise AudioUnitError(f"Tone King plugin returned non-finite {key[1]}")
            max_delta = max(max_delta, abs(before - after))
            if not math.isclose(before, after, rel_tol=1e-7, abs_tol=1e-5):
                raise AudioUnitError(
                    f"Tone King plugin changed preset control {key[1]} "
                    "during state application")
        self.state_preflight = {
            "schema": "toneking-state-preflight-v1",
            "method": "separate disposable plugin instance; applied-state readback",
            "source_sha256": self._preset_sha256,
            "retained_sha256": hashlib.sha256(retained_blob).hexdigest(),
            "compared_valued_controls": valued_count,
            "compared_valueless_controls": valueless_count,
            "max_numeric_delta": max_delta,
        }
        return self.state_preflight

    def _render(self, di, settings: Optional[Mapping]):
        self.verify_preset_state()
        return super()._render(di, settings)

    def _base_state_blob(self) -> bytes:
        return self._preset_blob

    def _state_command(self, settings: Optional[Mapping]):
        if self._xml_state is not False:
            raise AudioUnitError("exact Tone King preset playback requires record-state AU support")
        return self._record_command(settings)

    def _record_command(self, settings: Optional[Mapping]):
        if settings:
            raise AudioUnitError("exact preset playback does not accept knob edits")
        path = self._workdir / f"state-{self._render_index}.bin"
        path.write_bytes(self._preset_blob)
        return {"state": str(path)}

    def _quality_identity(self) -> str:
        return super()._quality_identity() + f";state_template_sha256={self._preset_sha256}"

    def _renderer_build(self) -> str:
        digest = hashlib.sha256()
        digest.update(super()._renderer_build().encode("utf-8"))
        digest.update(pathlib.Path(__file__).read_bytes())
        return f"audio-unit-preset-renderer-{digest.hexdigest()[:12]}"
