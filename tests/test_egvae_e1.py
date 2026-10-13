"""EG-VAE-lite E1 mapper (`learn/egvae_e1.py`): crop-start conversion, windowed stitching,
the per-cell seed averaging, and (with torch) the model's shapes and relative positions.

Runs under pytest (the torch half is skipped without torch) or directly with the learn venv,
which has torch but no pytest: `~/ndsp-presets/tools/learn-venv/bin/python tests/test_egvae_e1.py`.
"""

import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from learn import egvae_e1 as E  # noqa: E402


def test_crop_frame():
    assert E.crop_frame(0) == 0
    assert E.crop_frame(72000) == 129                    # C′'s centred validation crop
    # C′'s largest random start (CLIP − CROP − 1) still leaves a full crop in 517 frames
    assert E.crop_frame(6 * 48000 - 3 * 48000 - 1) + E.CROP_FRAMES <= E.FRAMES
    # the same instant: frame × 512 at 44.1 kHz is within half a hop of the 48-kHz start
    for a in (1531, 5251, 81116, 139786):
        assert abs(E.crop_frame(a) * 512 - a * 44100 / 48000) <= 256
    # 3 s at 44.1 kHz is 258.4 frames
    assert E.CROP_FRAMES == int(3 * 44100 / 512)


def test_random_crops():
    """Each example gets its own start in 0..259, the same for recording and target, and every
    start is reachable."""
    n = 6
    X = np.broadcast_to(np.arange(E.FRAMES, dtype=np.int16), (n, 9, E.FRAMES)).copy()
    Y = X[:, :4].copy() + 1
    X[:, :, :] += np.arange(n, dtype=np.int16)[:, None, None] * 1000
    rng = np.random.default_rng(0)
    seen = set()
    for _ in range(400):
        ix = rng.choice(n, 4, replace=False)
        x, y = E.random_crops(X, Y, ix, rng)
        assert x.shape == (4, 9, E.CROP_FRAMES) and y.shape == (4, 4, E.CROP_FRAMES)
        for j, i in enumerate(ix):
            s0 = int(x[j, 0, 0]) - 1000 * int(i)
            assert 0 <= s0 <= E.FRAMES - E.CROP_FRAMES
            np.testing.assert_array_equal(x[j, 3], np.arange(s0, s0 + E.CROP_FRAMES) + 1000 * int(i))
            np.testing.assert_array_equal(y[j, 2], np.arange(s0, s0 + E.CROP_FRAMES) + 1)
            seen.add(s0)
    assert min(seen) == 0 and max(seen) == E.FRAMES - E.CROP_FRAMES and len(seen) > 200


def test_window_starts_cover():
    for n in (100, 258, 259, 517, 861, 1000):
        s = E.window_starts(n, 258, 129)
        assert s[0] == 0 and min(n, s[-1] + 258) == n
        assert all(b - a <= 129 for a, b in zip(s, s[1:]))


def test_stitch_reproduces_consistent_windows():
    """Windows that agree with one global array stitch back to exactly that array (so every
    frame gets positive weight)."""
    for n in (100, 258, 259, 517, 861):
        g = np.random.default_rng(n).standard_normal((4, n, 7))
        seen = []

        def fn(s, L):
            seen.append((s, L))
            return g[:, s:s + L]

        out = E.stitch(n, 258, 129, fn)
        assert out.shape == g.shape
        np.testing.assert_allclose(out, g, atol=1e-12)
        assert seen[-1][0] + seen[-1][1] == n


def test_stitch_crossfades():
    """Two windows that disagree: the first's value at the start, the second's at the end,
    a linear blend through the overlap."""
    n = 387                                              # windows at 0 and 129

    def fn(s, L):
        return np.full((1, L, 1), 0.0 if s == 0 else 1.0)

    out = E.stitch(n, 258, 129, fn)[0, :, 0]
    assert np.all(out[:129] == 0) and np.all(out[258:] == 1)
    assert np.all(np.diff(out[129:258]) > 0)


def test_cell_ratio_matches_set5_averaging():
    per = {"E1": [2.0, 4.0], "Cp0": [1.0, 2.0], "Cp1": [4.0, 8.0], "base": [2.0, 2.0]}
    want = np.mean([np.mean([math.log(2 / 1), math.log(2 / 4)]), np.mean([math.log(4 / 2), math.log(4 / 8)])])
    assert math.isclose(E.cell_ratio(per, "E1", ("Cp0", "Cp1")), want)
    assert math.isclose(E.cell_ratio(per, ("Cp0", "Cp1"), "base"), np.mean(
        [np.mean([math.log(1 / 2), math.log(4 / 2)]), np.mean([math.log(2 / 2), math.log(8 / 2)])]))
    assert E.cell_ratio({**per, "E1": [None, 4.0]}, "E1", "base") is None


def _torch():
    import pytest

    return pytest.importorskip("torch")


def test_model_shapes_and_size():
    torch = _torch()
    torch.manual_seed(0)
    net = E.build_model().eval()
    n = sum(q.numel() for q in net.parameters())
    assert 10e6 <= n <= 20e6, n
    x = torch.randint(0, 1024, (2, 9, 258))
    with torch.no_grad():
        lg = net(x)
    assert lg.shape == (2, 4, 258, 1024)
    loss, per = E.ce_loss(lg, torch.randint(0, 1024, (2, 4, 258)))
    assert len(per) == 4 and math.isclose(float(loss), sum(float(p) for p in per), rel_tol=1e-5)
    assert math.isclose(float(loss), 4 * math.log(1024), rel_tol=0.2)


def test_rope_attention_is_relative():
    """Rotary positions: q·k after rotation depends only on the position difference."""
    torch = _torch()
    torch.manual_seed(0)
    q, k = torch.randn(64), torch.randn(64)
    rq, rk = E._rope(q.expand(40, 64)), E._rope(k.expand(40, 64))
    s = rq @ rk.T                                         # (40, 40): position i against j
    for off in (-5, 0, 3, 17):
        d = torch.diagonal(s, off)
        assert torch.allclose(d, d[0].expand_as(d), atol=1e-3)


def test_mps_check_passes_on_identical_devices():
    torch = _torch()
    torch.manual_seed(0)
    cfg = {**E.CFG, "layers": 1, "d": 64, "heads": 4, "ff": 128}
    state = E.build_model(cfg).state_dict()
    x, y = torch.randint(0, 1024, (2, 9, 258)), torch.randint(0, 1024, (2, 4, 258))
    r = E.mps_check(state, x, y, cfg, devices=("cpu", "cpu"))
    assert r["ok"] and r["logits_rel"] == 0 and r["worst_cos"] > 0.99999


def test_attention_dropout_off():
    assert E.CFG["attn_dropout"] == 0.0 and E.CFG["dropout"] == 0.1


def test_train_resume_is_identical(tmp_path=None):
    """Tiny CPU run on synthetic codes: 4 steps straight equal 2 steps, a resume, and 2 more
    (weights, optimiser-driven, rng states restored); checkpoints written atomically."""
    import tempfile

    torch = _torch()
    tmp = pathlib.Path(tmp_path or tempfile.mkdtemp())
    r = np.random.default_rng(1)
    data = (r.integers(0, 1024, (10, 9, E.FRAMES)).astype(np.int16),
            r.integers(0, 1024, (10, 4, E.FRAMES)).astype(np.int16),
            r.integers(0, 1024, (3, 9, E.CROP_FRAMES)).astype(np.int16),
            r.integers(0, 1024, (3, 4, E.CROP_FRAMES)).astype(np.int16), np.arange(3))
    cfg = {**E.CFG, "layers": 1, "d": 32, "heads": 2, "ff": 64, "batch": 4, "warmup": 2,
           "max_steps": 4, "eval_every": 2, "patience": 99}
    old = E.load_data
    E.load_data = lambda partial=False: data
    try:
        E.train(out=tmp / "a", device="cpu", cfg=cfg)
        E.train(out=tmp / "b", device="cpu", cfg=cfg, max_steps=2)
        (tmp / "b/DONE").unlink()
        E.train(out=tmp / "b", device="cpu", cfg=cfg)
    finally:
        E.load_data = old
    a, b = (torch.load(tmp / k / "last.pt", weights_only=False) for k in ("a", "b"))
    assert a["step"] == b["step"] == 4
    for k in a["model"]:
        assert torch.equal(a["model"][k], b["model"][k]), k
    assert not list(tmp.glob("*/*.tmp"))


def test_map_codes_shapes():
    torch = _torch()
    torch.manual_seed(0)
    cfg = {**E.CFG, "layers": 1, "d": 64, "heads": 4, "ff": 128}
    net = E.build_model(cfg).eval()
    for n in (200, 517, 861):
        out = E.map_codes(net, np.random.default_rng(0).integers(0, 1024, (9, n)))
        assert out.shape == (4, n) and out.dtype == np.int16 and out.min() >= 0 and out.max() < 1024


if __name__ == "__main__":                  # the learn venv: torch, no pytest
    import types

    try:
        import pytest  # noqa: F401
    except ImportError:
        sys.modules["pytest"] = types.SimpleNamespace(importorskip=__import__)
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
