"""The rebuild-gap study's torch side (docs/rebuild-gap-plan.md): the proxy amp bank, its distance,
the proxy local set, stage T's terms and rules. Needs torch (the demucs-venv interpreter); skipped
otherwise."""

import math

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from learn import rebuild_gap_train as T  # noqa: E402

SR = 48000


def _sig(n=SR, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * 110 * h * t + rng.random()) / h for h in range(1, 6)) * np.exp(-t * 2)
    return torch.tensor(x * 0.1 + rng.standard_normal(n) * 1e-3, dtype=torch.float32)


def test_proxy_shapes_and_gradient():
    x = T.norm_rms(torch.stack([_sig(), _sig(seed=1)])).requires_grad_()
    th = torch.rand(2, T.N_KNOBS)
    y = T.proxy(x, th)
    assert y.shape == x.shape and torch.isfinite(y).all()
    y.pow(2).mean().backward()
    assert torch.isfinite(x.grad).all() and x.grad.abs().sum() > 0


def test_gain_knob_drives_harder():
    x = T.norm_rms(_sig()[None])
    lo = T.proxy(x, torch.tensor([[0.0, 0.5, 0.0, 0.5, 0.5, 0.5, 0.5]]))
    hi = T.proxy(x, torch.tensor([[1.0, 0.5, 0.0, 0.5, 0.5, 0.5, 0.5]]))
    crest = lambda y: float(y.abs().max() / y.pow(2).mean().sqrt())  # noqa: E731
    assert crest(hi) < crest(lo)                                   # clipping lowers the crest factor


def test_distance_properties():
    x = T.norm_rms(_sig()[None])
    A = T.logmel(T.proxy(x, torch.full((1, 7), 0.5)))
    assert float(T.distance(A, A)) < 0.02
    assert float(T.distance(A + 6.0, A)) < 0.02                     # a level offset is removed
    B = T.logmel(T.proxy(x, torch.tensor([[0.5, 0.5, 0.5, 1.0, 0.0, 1.0, 0.0]])))
    assert float(T.distance(B, A)) > 0.5


def test_logmel_refuses_other_devices():
    class Fake:
        class device:
            type = "mps"
    with pytest.raises(AssertionError):
        T.logmel(Fake())


def test_local_set():
    rng = np.random.default_rng(0)
    star, c = T.local_set(rng)
    assert star.shape == (7,) and c.shape == (15, 7)
    assert (c >= 0).all() and (c <= 1).all()
    S = c[0]
    assert np.sum(np.abs(S - star) > 1e-12) <= 3
    for k in range(7):
        assert np.allclose(np.delete(c[1 + 2 * k], k), np.delete(S, k))


def test_pearson():
    a = torch.tensor([[1.0, 2.0, 3.0, 4.0]])
    assert float(T.pearson(a, 2 * a + 1)) == pytest.approx(1.0, abs=1e-6)
    assert float(T.pearson(a, -a)) == pytest.approx(-1.0, abs=1e-6)


def test_proxy_terms_finite_with_gradient():
    rng = np.random.default_rng(0)
    y = torch.stack([_sig(int(1.6 * SR), s) for s in range(4)])[:, None]
    p = (y + 0.02 * torch.randn_like(y)).requires_grad_()
    rank, match = T.proxy_terms(p, y, rng, k=4, crops=2, sub=int(0.5 * SR))
    assert math.isfinite(float(rank)) and math.isfinite(float(match))
    (rank + match).backward()
    assert torch.isfinite(p.grad).all() and p.grad.abs().sum() > 0


def test_proxy_fidelity_of_the_truth_is_one():
    t = _sig(SR, 3).numpy()
    rng = np.random.default_rng(0)
    assert T.proxy_fidelity(t, t, rng, draws=3) == pytest.approx(1.0)
    noisy = t + np.random.default_rng(1).standard_normal(len(t)) * 0.05
    assert T.proxy_fidelity(noisy, t, np.random.default_rng(0), draws=3) < 1.0


def test_proxy_fidelity_many_matches_single():
    t = _sig(SR, 3).numpy()
    noisy = t + np.random.default_rng(1).standard_normal(len(t)) * 0.05
    many = T.proxy_fidelity_many({"t": t, "noisy": noisy}, t, np.random.default_rng(0), draws=3)
    assert many["t"] == pytest.approx(1.0)
    assert many["noisy"] == pytest.approx(T.proxy_fidelity(noisy, t, np.random.default_rng(0), draws=3))


def test_schedule_and_rules():
    assert T.schedule(0) == pytest.approx(T.LR / T.WARMUP)
    assert T.schedule(T.WARMUP) == pytest.approx(T.LR)
    assert T.schedule(T.MAX_STEPS) == pytest.approx(T.LR_END)
    assert T.is_best(0.5, None) and T.is_best(0.506, 0.5) and not T.is_best(0.504, 0.5)
    assert not T.should_stop(1000, 0)                               # under the minimum
    assert T.should_stop(1500, 0) and not T.should_stop(1750, 500)
    assert T.should_stop(T.MAX_STEPS, T.MAX_STEPS - 1)


def test_validation_bands_are_training_fold_bands():
    from learn import train as TR

    fold_of, _ = TR.k3_folds()
    for f, bands in T.VAL_BANDS.items():
        assert all(fold_of[b] != f for b in bands)
