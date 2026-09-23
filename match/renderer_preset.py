"""Exact Tone King preset playback for private listening comparisons.

The calibrated AudioUnitRenderer keeps its measured source identity unchanged.
This subclass loads one pinned preset blob instead of the plugin's boot state,
and has its own build identity so neither its audio nor its code can be mistaken
for a calibration render. It deliberately accepts no per-render knob edits.
"""

from __future__ import annotations

import hashlib
import pathlib
from typing import Mapping, Optional

from format.parser import parse
from format.structured import build
from packs.loader import detect_pack

from .renderer_au import AudioUnitError, AudioUnitRenderer


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
    spec = detected.parameters["/ampType"]
    try:
        stored = detected.to_stored(spec, selectors[0].value)
        return spec.members[stored]
    except (ValueError, KeyError) as error:
        raise AudioUnitError("Tone King preset has an invalid ampType") from error


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
        super().__init__("toneking", process_policy="fresh", **kwargs)

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
