"""The renderer protocol: what identifies a render, and what it is worth.

No plugin is involved. What is checked here is the bookkeeping that decides
whether two renders may be treated as the same render — which is the part M0
proved cannot be assumed.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")

import numpy as np

from match.renderer import (
    REUSED_INSTANCE_BAND_NOISE_DB,
    RenderError,
    RenderMetadata,
    Renderer,
    RenderResult,
    cache_key,
    canonical_settings,
)
from match.renderer_synth import SyntheticRenderer


def meta(**overrides) -> RenderMetadata:
    base = dict(renderer_id="test", sample_rate=48000, block_size=512,
                plugin_version="1.0.0", renderer_build="b1")
    base.update(overrides)
    return RenderMetadata(**base)


# --- what identifies a render ------------------------------------------------


def test_the_same_settings_hash_the_same_however_they_are_spelled():
    """A caller may spell keys as tuples or as "module/key", and 40 or 40.0.

    None of those is a different render, and treating them as different ones would
    quietly halve the cache hit rate and make two trials look distinct.
    """
    a = cache_key(meta(), "di-sha", {("delay", "delayTime"): 420})
    b = cache_key(meta(), "di-sha", {"delay/delayTime": 420.0})
    assert a == b

    # Order must not matter either.
    first = canonical_settings({"a/x": 1.0, "b/y": 2.0})
    second = canonical_settings({"b/y": 2.0, "a/x": 1.0})
    assert first == second


def test_booleans_are_not_confused_with_numbers():
    """A switch is not a knob at zero. `True == 1` in Python, and a cache that
    collapsed them would serve an effect-on render for an effect-off request."""
    on = canonical_settings({"delay/delayActive": True})
    one = canonical_settings({"delay/delayActive": 1.0})
    assert on != one


def test_a_different_plugin_version_is_a_different_render():
    """§3.9: results from different plugin versions are never merged.

    In the key rather than beside it, so a plugin update invalidates every entry
    instead of silently serving audio the installed plugin would not produce.
    """
    old = cache_key(meta(plugin_version="1.0.0"), "di", {"a/b": 1})
    new = cache_key(meta(plugin_version="1.1.0"), "di", {"a/b": 1})
    assert old != new


@pytest.mark.parametrize("field, value", [
    ("renderer_id", "other"),
    ("renderer_build", "b2"),
    ("sample_rate", 44100),
    ("block_size", 1024),
    ("quality_mode", "preview"),
])
def test_everything_the_key_is_specified_to_cover_changes_it(field, value):
    """§6.3 names eight components. Each one has to actually move the hash."""
    assert cache_key(meta(), "di", {"a/b": 1}) != cache_key(meta(**{field: value}), "di", {"a/b": 1})


def test_the_di_and_the_parameters_change_the_key():
    assert cache_key(meta(), "di-one", {"a/b": 1}) != cache_key(meta(), "di-two", {"a/b": 1})
    assert cache_key(meta(), "di", {"a/b": 1}) != cache_key(meta(), "di", {"a/b": 2})


# --- what a render is worth --------------------------------------------------


def test_a_backend_must_declare_whether_it_repeats_itself():
    """M0's first finding, as a field rather than a footnote.

    Two renders of identical parameters from one plugin instance differ by about
    -17 dB relative to the signal. A caller deciding whether to commit a number as
    a measured fact needs to be able to ask.
    """
    assert RenderMetadata(renderer_id="x", sample_rate=48000,
                          block_size=512).reproducible is False, (
        "the default must be the pessimistic one: a real host does not repeat"
    )
    assert SyntheticRenderer().metadata().reproducible is True


def test_a_backend_answers_whether_a_band_difference_is_above_its_own_noise():
    """M4's sensitivity screen needs a floor, and on a real host it is measured.

    This replaces an assertion that compared one module literal with another
    (`0.23 < 0.5`), which exercised nothing. The behaviour that matters is that a
    reused-instance backend refuses to resolve a difference smaller than the spread
    it shows against itself, and the synthetic one resolves anything.
    """
    reused = meta(band_noise_db=REUSED_INSTANCE_BAND_NOISE_DB)
    assert not reused.resolves_band_difference(0.1)
    assert not reused.resolves_band_difference(-0.2)
    assert reused.resolves_band_difference(0.5)
    assert reused.resolves_band_difference(-1.4)   # the smallest change M0 measured

    exact = SyntheticRenderer().metadata()
    assert exact.band_noise_db == 0.0
    assert exact.resolves_band_difference(0.01)


def test_metadata_survives_a_round_trip_into_the_store():
    """`store.py` writes this as JSON, so every field has to be plain data."""
    import json

    data = SyntheticRenderer().metadata().as_dict()
    assert json.loads(json.dumps(data)) == data
    assert data["reproducible"] is True


def test_silence_is_named_rather_than_returned_as_a_number():
    """The repository's standing rule: a silent render is not evidence.

    Tone King returned exact zeros from the Swift helpers for months, and a caller
    that only looked at the audio would have taken those as measurements.
    """
    silent = RenderResult(audio=np.zeros((100, 2), dtype=np.float32), metadata=meta())
    assert silent.silent and silent.peak == 0.0

    loud = RenderResult(audio=np.full((100, 2), 0.5, dtype=np.float32), metadata=meta())
    assert not loud.silent and loud.peak == pytest.approx(0.5)


def test_a_backend_that_produces_nothing_raises_instead_of_returning_none():
    class Broken(Renderer):
        renderer_id = "broken"

        def metadata(self):
            return meta(renderer_id="broken")

        def _render(self, di, settings):
            return None

    with pytest.raises(RenderError, match="no audio"):
        Broken().render(np.zeros(1000, dtype=np.float32))


def test_the_protocol_is_implementable_without_a_plugin():
    """What `match/space.py` and the M4 tests are written against."""
    class Doubler(Renderer):
        renderer_id = "doubler"

        def metadata(self):
            return meta(renderer_id="doubler", reproducible=True)

        def _render(self, di, settings):
            gain = float((settings or {}).get("gain", 1.0))
            mono = np.asarray(di, dtype=np.float32) * gain
            return np.column_stack([mono, mono])

    result = Doubler().render(np.full(1000, 0.25, dtype=np.float32), {"gain": 2.0})
    assert result.peak == pytest.approx(0.5)
    assert result.metadata.renderer_id == "doubler"
    assert result.cache_key and len(result.cache_key) == 64
    assert result.settings == {"gain": 2.0}


def test_the_same_audio_hashes_the_same_without_being_told():
    """A caller that does not supply a DI hash gets one from the samples, so the
    cache still works — just without knowing the file it came from."""
    di = np.linspace(-1, 1, 4096, dtype=np.float32)
    renderer = SyntheticRenderer()
    first = renderer.render(di, {"delay/delayActive": False})
    second = renderer.render(di, {"delay/delayActive": False})
    assert first.cache_key == second.cache_key

    other = renderer.render(di * 0.5, {"delay/delayActive": False})
    assert other.cache_key != first.cache_key
