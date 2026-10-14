"""Silence before the DI, cut off after the render: Tone King's start-up mute.

A fresh Tone King process renders exact zeros for the first 0.32-0.39 s, then
plays 4-45 dB low until about 1 s; Reset and neutral states have a second zero
run ending near 0.87 s (audit D-M1). Every one of the 258 committed Tone King
match-pipeline scoring renders started late, so the opening of the DI was never
heard, and a part whose notes sit in that opening rendered as silence.

`PrerolledRenderer` wraps any backend: it puts `seconds` of silence in front of
the DI, renders, and returns the audio from where the DI starts, so the caller
gets back exactly as many frames as it sent. The pre-roll is part of the render's
identity (`quality_mode`), so a cached render without it is never reused. The
plugin server's own warm-up is not used: research renders share it (D-M13).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping, Optional

from match.renderer import RenderError, Renderer

# audition.py uses 1.0 s for listening; scoring takes the audit's ≥1.5 s, past the
# 0.87 s second zero run and the ~1 s low stretch with margin.
TONEKING_PREROLL_S = 1.5


def silent_preroll(di, sample_rate: int, seconds: float):
    """`(padded, frames)`: `seconds` of zeros in front of `di`, along its first axis."""
    import numpy as np

    if not 0.0 <= seconds <= 10.0:
        raise ValueError("a pre-roll must be between 0 and 10 seconds")
    di = np.asarray(di)
    frames = round(seconds * sample_rate)
    if frames == 0:
        return di, 0
    silence = np.zeros((frames,) + di.shape[1:], dtype=di.dtype)
    return np.concatenate((silence, di), axis=0), frames


class PrerolledRenderer(Renderer):
    """`inner`, with `seconds` of silence rendered before every DI and cut off."""

    def __init__(self, inner, seconds: float = TONEKING_PREROLL_S):
        if not 0.0 < float(seconds) <= 10.0:
            raise ValueError("a pre-roll must be between 0 and 10 seconds")
        self.inner = inner
        self.seconds = float(seconds)
        self.renderer_id = getattr(inner, "renderer_id", "abstract")

    def metadata(self):
        base = self.inner.metadata()
        return replace(base, quality_mode=f"{base.quality_mode};preroll_s={self.seconds:g}")

    def basis_metadata(self):
        """The backend's own identity, for `invert._validate_basis_provenance`.

        An EQ basis measured without the pre-roll still describes this backend:
        the pre-roll is cut off and does not change what the equaliser does.
        """
        return self.inner.metadata()

    def _render(self, di, settings: Optional[Mapping]):
        import numpy as np

        sample_rate = self.inner.metadata().sample_rate
        padded, frames = silent_preroll(di, sample_rate, self.seconds)
        audio = np.asarray(self.inner.render(padded, settings).audio)
        wanted = np.asarray(di).shape[0]
        if audio.shape[0] < frames + wanted:
            raise RenderError(
                f"{self.renderer_id} returned {audio.shape[0]} frames for a "
                f"{frames + wanted}-frame pre-rolled DI, so the pre-roll cannot be "
                f"cut off cleanly"
            )
        return audio[frames:frames + wanted]

    def parameter_specs(self):
        return self.inner.parameter_specs()

    def eq_basis(self, signal_path: str, analysis_centres):
        return self.inner.eq_basis(signal_path, analysis_centres)

    def close(self) -> None:
        close = getattr(self.inner, "close", None)
        if close is not None:
            close()

    def __getattr__(self, name):
        # Only reached for attributes this wrapper does not define: `to_spec`,
        # `process_policy` and the like belong to the backend.
        if name == "inner":
            raise AttributeError(name)
        return getattr(self.inner, name)


def predates_preroll(recorded, current) -> bool:
    """Whether two render identities differ only by this pre-roll.

    A run recorded before Tone King renders were pre-rolled is refused like any
    other renderer change, but the refusal should say why.
    """
    recorded, current = dict(recorded or {}), dict(current or {})
    mode = str(current.get("quality_mode") or "")
    if ";preroll_s=" not in mode or ";preroll_s=" in str(recorded.get("quality_mode")):
        return False
    current["quality_mode"] = mode.split(";preroll_s=")[0]
    keys = set(recorded) & set(current)
    return bool(keys) and all(recorded[k] == current[k] for k in keys
                              if k in ("renderer_id", "plugin_version", "renderer_build",
                                       "sample_rate", "block_size", "quality_mode"))


def predates_isolate(recorded, current) -> bool:
    """Whether two render identities differ only in Morgan's per-render isolation
    (`isolate=auto` recorded, `isolate=true` now: match runs from before 0.7.110)."""
    recorded, current = dict(recorded or {}), dict(current or {})
    before = str(recorded.get("quality_mode") or "")
    now = str(current.get("quality_mode") or "")
    if "isolate=auto" not in before or "isolate=true" not in now:
        return False
    recorded["quality_mode"] = before.replace("isolate=auto", "isolate=true")
    keys = ("renderer_id", "plugin_version", "renderer_build", "sample_rate",
            "block_size", "quality_mode")
    return all(recorded.get(k) == current.get(k) for k in keys if k in recorded)
