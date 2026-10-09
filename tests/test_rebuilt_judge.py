"""The judge through a rebuilt DI falls back to the recording as the activity mask only
when the rebuilt DI looks too quiet, and otherwise leaves the judge untouched."""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("pyloudnorm", reason="needs the analysis extra")

from analysis.aligned import aligned_distance  # noqa: E402
from learn.rebuilt_judge import LATENCY, rebuilt_distance  # noqa: E402

SR = 48000


def _part(seed=0, seconds=6.0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SR)) / SR
    di = np.zeros_like(t)
    start = 0.2
    while start < seconds - 0.4:
        length = rng.uniform(0.3, 0.6)
        idx = (t >= start) & (t < start + length)
        tt = t[idx] - start
        di[idx] += 0.2 * np.sin(2 * np.pi * rng.choice([110.0, 196.0, 329.6]) * tt) * np.exp(-tt * 3)
        start += length + rng.uniform(0.05, 0.2)
    return di


def _rig(di, drive):
    return np.tanh(drive * di)


def _pair(drive=4.0):
    di = _part()
    recording = _rig(di, 4.0)
    render = np.concatenate([np.zeros(LATENCY), _rig(di, drive)])[:len(di)]
    return di, recording, render


def test_unrefused_matches_the_judge():
    di, recording, render = _pair(drive=6.0)
    d, proxy = rebuilt_distance(recording, render, di, start_s=1.0, end_s=5.0)
    ref = aligned_distance(recording, render, di, lag=-LATENCY, render_latency=LATENCY,
                           start_s=1.0, end_s=5.0)
    assert not proxy and d.distance == ref.distance and d.distance is not None


def test_quiet_rebuilt_di_falls_back_to_the_recording():
    di, recording, render = _pair(drive=6.0)
    mostly_silent = di.copy()
    mostly_silent[int(1.2 * SR):] *= 1e-4        # the rebuilt DI 'plays' only at the start
    plain = aligned_distance(recording, render, mostly_silent, lag=-LATENCY,
                             render_latency=LATENCY, start_s=1.0, end_s=5.0)
    assert plain.distance is None
    d, proxy = rebuilt_distance(recording, render, mostly_silent, start_s=1.0, end_s=5.0)
    assert proxy and d.distance is not None


def test_other_refusals_are_not_rescued():
    di, recording, render = _pair()
    d, proxy = rebuilt_distance(recording, render[: SR // 2], di, start_s=1.0, end_s=5.0)
    assert d.distance is None and not proxy
