"""The interface every backend renders through, and what a render is worth.

One protocol, several implementations: `SyntheticRenderer` (no plugin, exact),
and later the `pedalboard` host and the batched Swift server. Backend choice is
configuration, so the optimiser never learns which one it is talking to.

Two findings from M0 are encoded here rather than left as prose, because both
change what callers may assume:

**A cached render is not the same render.** Two renders of identical parameters
from one plugin instance differ by about -17 dB relative to the signal — in both
hosts, through `reset`, reallocation and warm-up alike. Only a fresh process is
bit-exact. So `RenderMetadata.reproducible` says whether this backend's output is
a function of its inputs at all, and the cache key exists to save time, not to
assert equivalence. Anything that gets *committed* as a measured fact must come
from a backend that says it is reproducible.

**The plugin version is part of the identity of a render.** Results from
different plugin versions are never merged, so the version is in the cache key
and not merely recorded alongside it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple

# How far apart two renders of identical parameters were measured to be, in dB
# relative to the signal, on a backend that reuses one plugin instance. Third-
# octave band levels moved by at most 0.23 dB across the same repeats, so a
# consumer reading a difference smaller than about 0.5 dB out of a reused
# instance is reading this instead of a parameter change.
REUSED_INSTANCE_RESIDUAL_DB = -17.0
REUSED_INSTANCE_BAND_NOISE_DB = 0.23


class RenderError(RuntimeError):
    """A backend could not produce audio. Never returned as silence."""


@dataclass(frozen=True)
class RenderMetadata:
    """What produced a render, and whether it can be trusted to repeat.

    `reproducible=False` is not a defect to be fixed by the caller — it is a
    measured property of hosting an Audio Unit in a reused instance. It travels
    with the audio so that a decision to commit a number can check it.
    """

    renderer_id: str
    sample_rate: int
    block_size: int
    plugin_version: str = "n/a"
    renderer_build: str = "n/a"
    quality_mode: str = "standard"
    reproducible: bool = False
    licensed: Optional[bool] = None
    band_noise_db: float = 0.0
    notes: Tuple[str, ...] = ()

    def as_dict(self) -> Dict[str, Any]:
        return {
            "renderer_id": self.renderer_id,
            "sample_rate": self.sample_rate,
            "block_size": self.block_size,
            "plugin_version": self.plugin_version,
            "renderer_build": self.renderer_build,
            "quality_mode": self.quality_mode,
            "reproducible": self.reproducible,
            "licensed": self.licensed,
            "band_noise_db": self.band_noise_db,
            "notes": list(self.notes),
        }


@dataclass
class RenderResult:
    """Audio, plus the metadata that says what it is."""

    audio: Any                      # np.ndarray, (frames, channels), float32
    metadata: RenderMetadata
    cache_key: Optional[str] = None
    settings: Mapping = field(default_factory=dict)

    @property
    def peak(self) -> float:
        import numpy as np

        return float(np.abs(np.asarray(self.audio)).max()) if len(self.audio) else 0.0

    @property
    def silent(self) -> bool:
        """Exact zeros. Worth its own name: the repository's rule is that a silent
        render is not evidence about a control, and Tone King produced exactly this
        from the Swift helpers for months."""
        return self.peak == 0.0


def canonical_settings(settings: Optional[Mapping]) -> str:
    """Parameters as canonical JSON, so the same settings always hash the same.

    Keys are normalised to `"module/key"` strings and sorted, because a caller may
    legitimately spell them as tuples or strings and those must not produce two
    different cache entries for one render.
    """
    normalised = {}
    for raw_key, value in (settings or {}).items():
        key = raw_key if isinstance(raw_key, str) else "/".join(str(part) for part in raw_key)
        if isinstance(value, bool):
            normalised[key] = value
        elif isinstance(value, (int, float)):
            # 40 and 40.0 are the same knob position, and float(40) is what the
            # value becomes on its way to the plugin either way.
            normalised[key] = round(float(value), 9)
        else:
            normalised[key] = value
    return json.dumps(normalised, sort_keys=True, separators=(",", ":"))


def cache_key(metadata: RenderMetadata, di_sha256: str,
              settings: Optional[Mapping]) -> str:
    """§6.3's content address for one render.

    Includes the plugin and renderer builds, so a plugin update invalidates every
    entry rather than silently serving audio the current plugin would not produce.
    """
    material = "␟".join([
        metadata.renderer_id,
        metadata.plugin_version,
        metadata.renderer_build,
        str(di_sha256),
        str(metadata.sample_rate),
        str(metadata.block_size),
        metadata.quality_mode,
        canonical_settings(settings),
    ])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class Renderer:
    """What every backend implements.

    Subclasses provide `metadata()` and `_render()`. `render()` is shared so that
    every backend hashes its inputs the same way and reports the same result type.
    """

    renderer_id = "abstract"

    def metadata(self) -> RenderMetadata:
        raise NotImplementedError

    def _render(self, di, settings: Optional[Mapping]):
        raise NotImplementedError

    def render(self, di, settings: Optional[Mapping] = None,
               di_sha256: Optional[str] = None) -> RenderResult:
        metadata = self.metadata()
        audio = self._render(di, settings)
        if audio is None:
            raise RenderError(f"{self.renderer_id} returned no audio")
        return RenderResult(
            audio=audio,
            metadata=metadata,
            cache_key=cache_key(metadata, di_sha256 or _hash_audio(di), settings),
            settings=dict(settings or {}),
        )

    def parameter_specs(self):
        """The `ParamSpec`s this backend can be driven with.

        `match/space.py` builds its search space from this, which is why it is on
        the protocol: a backend that cannot say what it accepts cannot be searched.
        """
        raise NotImplementedError


def _hash_audio(di) -> str:
    import numpy as np

    array = np.ascontiguousarray(np.asarray(di, dtype=np.float32))
    return hashlib.sha256(array.tobytes()).hexdigest()
