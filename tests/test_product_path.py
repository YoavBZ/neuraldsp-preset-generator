"""The model path (`learn/product_path.py`): the window choice and the amp pick."""

import json

import pytest

from learn import product_path as PP


def test_the_pick_is_the_least_mean_cosine_distance():
    stem = [1.0, 0.0]
    feats = {"pr12": [[0.0, 1.0], [0.1, 1.0]], "sw50r": [[1.0, 0.1], [1.0, 0.0]], "ac20": [[1.0, 1.0], [1.0, 1.0]]}
    amp, dist = PP.pick_amp(stem, feats)
    assert amp == "sw50r" and dist["sw50r"] < dist["ac20"] < dist["pr12"]


def test_the_delay_rule_is_d1s():
    assert PP.delay_rule(0.5, (300.0, 305.0), 302.0, 250.0) == (False, None, None)
    on, ms, which = PP.delay_rule(0.8, (300.0, 305.0), 302.0, 250.0)
    assert on and ms == 302.0 and "peak" in which
    on, ms, which = PP.delay_rule(0.8, (300.0, 150.0), 302.0, 250.0)
    assert on and ms == 250.0 and "neighbours" in which


def test_candidates_stay_inside_the_part_and_clear_of_the_ends():
    assert PP.candidate_starts((0.0, 30.0), 30.0) == [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0,
                                                     14.0, 15.0, 16.0, 17.0, 18.0]
    assert PP.candidate_starts((100.0, 112.0), 300.0) == [100.0, 101.0, 102.0]
    assert PP.candidate_starts((0.0, 11.0), 11.0) == []


def test_select_window_takes_the_typical_steady_present_one():
    pytest.importorskip("numpy")                                       # medoid; the light CI runners have none
    rows = [{"start": 0.0, "steady": True, "present": True, "profile": [0.0, 0.0]},
            {"start": 1.0, "steady": True, "present": True, "profile": [1.0, 0.0]},
            {"start": 2.0, "steady": True, "present": True, "profile": [2.0, 0.0]},
            {"start": 3.0, "steady": False, "present": True, "profile": [1.0, 0.0]}]
    assert PP.select_window(rows) == (1.0, "steady and present")
    assert PP.select_window([{**r, "present": False} for r in rows])[1] == "steady only"
    assert PP.select_window([{**r, "steady": False} for r in rows])[1] == "none steady"


def test_steady_whole_catches_a_fade_and_a_late_entry():
    np = pytest.importorskip("numpy")
    from learn import pretrain_set as PS

    sr, rng = PS.SR, np.random.default_rng(0)
    x = rng.standard_normal(10 * sr) * 0.1
    assert PP.steady_whole(x, sr)[0]
    fade = x * np.concatenate([np.ones(7 * sr), np.full(3 * sr, 0.01)])           # the song ends at 7 s
    late = x * np.concatenate([np.full(sr, 0.01), np.ones(9 * sr)])               # the guitar enters at 1 s
    assert not PP.steady_whole(fade, sr)[0] and not PP.steady_whole(late, sr)[0]


def test_versions_and_the_centre_mask():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    rng = np.random.default_rng(1)
    n = 48000 * 2
    centre, panned = rng.standard_normal(n) * 0.1, rng.standard_normal(n) * 0.1
    x = np.stack([centre + panned, centre], 1)                                   # one part centred, one hard left
    assert np.allclose(PP.version_mix(x, "stem"), (x[:, 0] + x[:, 1]) / 2)
    assert np.allclose(PP.version_mix(x, "stem_S"), panned / 2)
    with pytest.raises(SystemExit):
        PP.version_mix(x, "stem_C")
    c = PP.centre_mix(centre, centre, 48000)                                     # a centred part passes
    inner = slice(8192, n - 8192)
    assert np.sum((c - centre)[inner] ** 2) / np.sum(centre[inner] ** 2) < 1e-3
    p = PP.centre_mix(panned, np.zeros(n), 48000)                                # a hard-panned part falls away
    assert np.sum(p[inner] ** 2) / np.sum((panned[inner] / 2) ** 2) < 1e-3
    with pytest.raises(SystemExit):
        PP.version_mix(x, "stem_X")


class _FakeXL:
    """X-LANCE's interface for the tests: `_f` on (channels, chunk) audio, here the identity; a call on mono audio."""

    def _f(self, a):
        return a

    def __call__(self, x):
        return x * 0.5


def _two_halves(x2):
    """A stand-in centre model on [2, samples]: the halves weighted unequally, so the mean shows both were read."""
    return [x2[0] * 0.5, x2[1] * 1.5]


def test_the_stereo_centre_version_separates_the_pair_then_takes_the_centre():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    assert "xlst_mdxc" in PP.VERSIONS and "xlst_mdxc" in PP.STEREO_VERSIONS
    rng = np.random.default_rng(2)
    n = 48000 * 12
    L, R = rng.standard_normal(n) * 0.1, rng.standard_normal(n) * 0.1
    from learn import separator_screen as SCR

    y = PP.StereoCentre(_FakeXL(), centre=lambda x2: np.stack(_two_halves(x2)))(np.stack([L, R], 1))
    rt = lambda c: SCR.to48(SCR.to44(c), n)              # noqa: E731  X-LANCE's 44.1-kHz round trip
    want = (0.5 * rt(L) + 1.5 * rt(R)) / 2               # X-LANCE kept both channels; the centre's two outputs averaged
    inner = slice(4800, n - 4800)                        # clear of the resamplers' edges
    assert y.shape == (n,) and np.sum((y - want)[inner] ** 2) / np.sum(want[inner] ** 2) < 1e-4
    with pytest.raises(SystemExit):
        PP.StereoCentre(lambda x: x)                     # another separator has no stereo pass
    with pytest.raises(SystemExit):
        PP.version_mix(np.stack([L, R], 1), "xlst_mdxc")


def test_load_stereo_keeps_both_channels_and_resamples_them_together(tmp_path):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    pytest.importorskip("scipy")
    t = np.arange(44100 * 3) / 44100
    x = np.stack([np.sin(2 * np.pi * 220 * t), np.sin(2 * np.pi * 330 * t) * 0.5], 1).astype(np.float32)
    sf.write(tmp_path / "s.wav", x, 44100, subtype="FLOAT")
    y = PP.load_stereo(tmp_path / "s.wav", 48000, 1.0, 1.0)
    assert y.shape == (48000, 2)
    assert abs(np.std(y[:, 0]) / np.std(y[:, 1]) - 2.0) < 0.02          # the channels stay apart
    assert PP.load_stereo(tmp_path / "s.wav", 48000, None, None).shape[0] == 48000 * 3
    sf.write(tmp_path / "m.wav", x[:, 0], 44100, subtype="FLOAT")
    m = PP.load_stereo(tmp_path / "m.wav", 48000, 0.0, 1.0)
    assert m.shape == (48000, 2) and np.allclose(m[:, 0], m[:, 1])        # a mono file on both


class _StereoOnlyXL(_FakeXL):
    """X-LANCE for the stereo version: its mono call must never run (neither the selector's span nor the window)."""

    def __call__(self, x):
        raise AssertionError("the mono separator ran for the stereo version")


def _song(tmp_path, np, sf):
    rng = np.random.default_rng(3)
    x = np.stack([rng.standard_normal(48000 * 20) * 0.1, rng.standard_normal(48000 * 20) * 0.05], 1).astype(np.float32)
    sf.write(tmp_path / "song.wav", x, 48000, subtype="FLOAT")
    return x


def _window(x, w, np):
    """The window's two channels as the stage reads them, padded past the song's end."""
    a = int(round(w["start_s"] * 48000))
    y = np.pad(x[a:a + 480000].astype(np.float64), ((0, max(0, 480000 - len(x[a:a + 480000]))), (0, 0)))
    return y[:, 0], y[:, 1]


@pytest.mark.parametrize("where", [["--start", "3"], ["--start", "15.5"], ["--part", "2", "18"]])
def test_separate_reads_the_pair_for_the_stereo_version(tmp_path, monkeypatch, where):
    """The stage end to end with stand-in models: the stem is the stereo pass's (the mono separator never runs, for the
    selector's span or the window; a window past the end is padded), the model's mix stays (L+R)/2, and the record
    names the version and the separator. The centre model is built lazily, here a stand-in."""
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    pytest.importorskip("scipy")
    pytest.importorskip("pyloudnorm")
    from learn import direct_stems as DS
    from learn import separator_screen as SCR
    from learn import stereo_side_screen as SSS

    x = _song(tmp_path, np, sf)
    monkeypatch.setattr(DS, "stem_separator", lambda name, device: _StereoOnlyXL())
    monkeypatch.setattr(SSS, "Centre", lambda: (lambda x2: np.stack(_two_halves(x2))))
    out = tmp_path / "w"
    PP.main(["separate", str(tmp_path / "song.wav"), "--out", str(out), "--version", "xlst_mdxc", "--device", "cpu",
             *where])
    w = json.loads((out / "window.json").read_text())
    z = np.load(out / "window.npz")
    L, R = _window(x, w, np)
    rt = lambda c: SCR.to48(SCR.to44(c), 480000)         # noqa: E731  X-LANCE's 44.1-kHz round trip
    want = (0.5 * rt(L) + 1.5 * rt(R)) / 2
    inner = slice(4800, 480000 - 4800)
    assert w["version"] == "xlst_mdxc" and "MDX23C" in w["separator"]
    assert z["stem"].shape == (480000,) and np.sum((z["stem"] - want)[inner] ** 2) / np.sum(want[inner] ** 2) < 1e-4
    assert np.allclose(z["mix"], (L + R) / 2, atol=1e-6) and np.allclose(z["sep_mix"], z["mix"])
    if where[0] == "--part":
        assert w["candidates"] > 1                       # the selector's span went through the stereo pass too


@pytest.mark.parametrize("where", [["--start", "3"], ["--start", "15.5"]])
def test_a_channel_version_still_separates_its_channel(tmp_path, monkeypatch, where):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    pytest.importorskip("scipy")
    pytest.importorskip("pyloudnorm")
    from learn import direct_stems as DS

    x = _song(tmp_path, np, sf)
    monkeypatch.setattr(DS, "stem_separator", lambda name, device: _FakeXL())
    out = tmp_path / "w"
    PP.main(["separate", str(tmp_path / "song.wav"), "--out", str(out), "--version", "stem_L", "--device", "cpu", *where])
    w = json.loads((out / "window.json").read_text())
    z = np.load(out / "window.npz")
    L, R = _window(x, w, np)
    assert "separator" not in w and np.allclose(z["sep_mix"], L, atol=1e-6) and np.allclose(z["stem"], 0.5 * L, atol=1e-6)
    assert np.allclose(z["mix"], (L + R) / 2, atol=1e-6)
