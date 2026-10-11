"""The Tone King pre-roll (audit D-M1): silence rendered first, then cut off."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")

import numpy as np

from match.preroll import PrerolledRenderer, TONEKING_PREROLL_S, silent_preroll
from match.renderer import RenderError, RenderMetadata, Renderer

SR = 48000
MUTE_S = 0.87   # the longest zero run the audit measured (Reset and neutral states)


class MutedAtStart(Renderer):
    """A backend that plays its input back, but exact zeros for its first MUTE_S."""

    renderer_id = "muted-at-start"

    def __init__(self, short_by: int = 0):
        self.short_by = short_by
        self.seen = []
        self.closed = False

    def metadata(self):
        return RenderMetadata(renderer_id=self.renderer_id, sample_rate=SR,
                              block_size=512, quality_mode="standard")

    def _render(self, di, settings):
        self.seen.append(np.asarray(di).shape[0])
        out = np.array(di, dtype=np.float32, copy=True)
        out[: round(MUTE_S * SR)] = 0.0
        out = np.stack([out, out], axis=1)
        return out[: out.shape[0] - self.short_by]

    def parameter_specs(self):
        return {("", "ampType"): "spec"}

    def to_spec(self, settings=None, name="Matched"):
        return {"name": name}

    def close(self):
        self.closed = True


def _di(seconds: float = 3.0):
    t = np.arange(round(seconds * SR)) / SR
    return (0.3 * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32)


def test_the_opening_is_heard_and_the_length_is_kept():
    """The audit's check: the opening 50 ms is not exact zeros when the DI plays
    there. Without the pre-roll it is; with it the DI comes back sample for sample."""
    di = _di()
    bare = MutedAtStart().render(di).audio
    assert not np.any(bare[: round(0.05 * SR)]), "the fixture has to be the failing case"

    inner = MutedAtStart()
    audio = PrerolledRenderer(inner).render(di).audio
    assert audio.shape == (di.shape[0], 2)
    assert np.any(audio[: round(0.05 * SR)])
    np.testing.assert_array_equal(audio[:, 0], di)
    assert inner.seen == [di.shape[0] + round(TONEKING_PREROLL_S * SR)]


def test_the_preroll_is_part_of_the_renders_identity():
    """A cached render made without the pre-roll must not be reused for one with it."""
    wrapped = PrerolledRenderer(MutedAtStart())
    assert wrapped.metadata().quality_mode == "standard;preroll_s=1.5"
    di = _di(1.0)
    assert (wrapped.render(di).cache_key != MutedAtStart().render(di).cache_key)


def test_the_backend_still_answers_for_itself():
    inner = MutedAtStart()
    wrapped = PrerolledRenderer(inner)
    assert wrapped.parameter_specs() == inner.parameter_specs()
    assert wrapped.to_spec(name="X") == {"name": "X"}
    assert wrapped.renderer_id == "muted-at-start"
    wrapped.close()
    assert inner.closed


def test_a_short_render_is_an_error_not_a_shifted_one():
    with pytest.raises(RenderError):
        PrerolledRenderer(MutedAtStart(short_by=10)).render(_di(1.0))


def test_silent_preroll_pads_mono_and_multichannel():
    mono, frames = silent_preroll(np.ones(4, dtype=np.float32), 10, 0.3)
    assert frames == 3 and mono.tolist() == [0, 0, 0, 1, 1, 1, 1]
    stereo, _ = silent_preroll(np.ones((2, 2)), 10, 0.1)
    assert stereo.shape == (3, 2) and not stereo[0].any()
    with pytest.raises(ValueError):
        silent_preroll(np.ones(4), 10, 11.0)


def test_only_tone_king_match_renders_are_prerolled(monkeypatch):
    """`match_preset.py` wraps the plugin renderer for Tone King and nothing else."""
    import sys
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
    import match_preset
    from match import renderer_au

    class Fake(MutedAtStart):
        def __init__(self, pack_id, process_policy="reuse"):
            super().__init__()
            self.pack_id = pack_id

    monkeypatch.setattr(renderer_au, "AudioUnitRenderer", Fake)
    assert isinstance(match_preset._renderer("swift", "toneking"), PrerolledRenderer)
    assert isinstance(match_preset._renderer("swift", "morgan"), Fake)
    assert not isinstance(match_preset._renderer("synthetic", "toneking"),
                          PrerolledRenderer)
