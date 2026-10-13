"""C′'s training-pair code, factored out of `learn.direc.fit` for EG-VAE-lite's E1
(`docs/egvae-lite-plan.md`, "E1 after review"), must give bit-identical pairs to the inline
closure it replaced, for the same rng.

`_inline_make` below is the closure as it stood in `fit` before the factoring (commit
c0a65b3), copied verbatim apart from taking its free variables as arguments. CPU only; small
synthetic batches, plus real cache rows and the real bleed pool when the data are present.

Runs under pytest (the torch half is skipped without torch) or directly with a torch venv:
`~/ndsp-presets/tools/learn-venv/bin/python tests/test_direc_make.py`.
"""

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from learn import direc as D  # noqa: E402

CLIP, CROP, SR, SPEC_N = D.CLIP, D.CROP, D.SR, D.SPEC_N
CACHE = pathlib.Path("~/ndsp-presets/learn/direc/cache").expanduser()


def _inline_make(X, Y, S, avg, bleed, rng, stack):
    """`fit`'s `make` before the factoring; `stack` replaces the final torch.tensor calls."""
    freqs = np.fft.rfftfreq(SPEC_N, 1 / SR)
    cfreq = np.fft.rfftfreq(CLIP, 1 / SR)

    def eq_curve(gain_bins):
        return np.interp(cfreq, freqs, gain_bins)

    def make(idx, train):
        xs, ys = [], []
        for i in idx:
            x = X[i].astype(np.float32) / 32767
            y = Y[i].astype(np.float32) / 32767
            own = S[i] - S[i].mean()
            g = np.clip(avg - own, -15, 15)
            Yf = np.fft.rfft(y) * 10 ** (eq_curve(g) / 20)
            y = np.fft.irfft(Yf, CLIP).astype(np.float32)
            if train:
                lf = np.log2(np.maximum(cfreq, 20) / 1000)
                tilt = rng.uniform(-3, 3) * np.clip(lf / 3.3, -1, 1)
                fc, gb = rng.uniform(np.log2(200), np.log2(6000)), rng.uniform(-4, 4)
                bell = gb * np.exp(-0.5 * ((np.log2(np.maximum(cfreq, 20)) - fc) / 0.5) ** 2)
                x = np.fft.irfft(np.fft.rfft(x) * 10 ** ((tilt + bell) / 20), CLIP).astype(np.float32)
                if rng.random() < 0.5 and bleed:
                    b = bleed[rng.integers(len(bleed))]
                    s = rng.integers(0, max(1, len(b) - CLIP))
                    seg = np.zeros(CLIP, np.float32)
                    seg[:len(b[s:s + CLIP])] = b[s:s + CLIP]
                    x = x + seg / (seg.std() + 1e-9) * x.std() * 10 ** (-rng.uniform(12, 30) / 20)
                if rng.random() < 0.5:
                    x = x + rng.standard_normal(CLIP).astype(np.float32) * x.std() * 10 ** (-rng.uniform(45, 75) / 20)
                a = rng.integers(0, CLIP - CROP)
            else:
                a = (CLIP - CROP) // 2
            x, y = x[a:a + CROP], y[a:a + CROP]
            xs.append(x / (x.std() + 1e-9) * 0.1)
            ys.append(y / (y.std() + 1e-9) * 0.1)
        return stack(xs), stack(ys)

    return make


def _factored_make_numpy(X, Y, S, avg, bleed, rng):
    """`batch_maker`'s loop body without the tensor conversion."""
    def make(idx, train):
        xs, ys = [], []
        for i in idx:
            x, y, a = D.make_clip(X[i], Y[i], S[i], avg, rng, train, bleed)
            x, y = x[a:a + CROP], y[a:a + CROP]
            xs.append(x / (x.std() + 1e-9) * 0.1)
            ys.append(y / (y.std() + 1e-9) * 0.1)
        return np.stack(xs), np.stack(ys)

    return make


def _synthetic(n=4, seed=123):
    r = np.random.default_rng(seed)
    X = (r.standard_normal((n, CLIP)) * 3000).astype(np.int16)
    Y = (r.standard_normal((n, CLIP)) * 3000).astype(np.int16)
    S = r.normal(-60, 10, (n, SPEC_N // 2 + 1)).astype(np.float32)
    avg = r.normal(0, 6, SPEC_N // 2 + 1)
    bleed = [r.standard_normal(CLIP // 2).astype(np.float32),        # shorter than a clip
             r.standard_normal(CLIP * 2).astype(np.float32)]
    return X, Y, S, avg, bleed


def _batches(X, Y, S, avg, bleed, seed, maker):
    make = maker(X, Y, S, avg, bleed, np.random.default_rng(seed))
    idx = list(range(len(X)))
    out = []
    for train in (True, True, False, True):     # several draws, so rng state carries over
        out.append(make(idx[::-1] if train else idx, train))
    return out


def _assert_same(a, b):
    for (xa, ya), (xb, yb) in zip(a, b):
        assert xa.dtype == xb.dtype and xa.shape == xb.shape
        assert np.array_equal(xa, xb) and np.array_equal(ya, yb)


def _inline_np(X, Y, S, avg, bleed, rng):
    return _inline_make(X, Y, S, avg, bleed, rng, np.stack)


def test_make_clip_matches_inline_synthetic():
    data = _synthetic()
    for seed in (0, 1, 7):
        _assert_same(_batches(*data, seed, _inline_np), _batches(*data, seed, _factored_make_numpy))
    # an empty bleed pool takes the `and bleed` branch
    X, Y, S, avg, _ = data
    _assert_same(_batches(X, Y, S, avg, [], 3, _inline_np), _batches(X, Y, S, avg, [], 3, _factored_make_numpy))


def test_batch_maker_tensors_match_inline():
    import pytest

    torch = pytest.importorskip("torch")
    X, Y, S, avg, bleed = _synthetic(3, seed=5)
    stack = lambda v: torch.tensor(np.stack(v), device="cpu").unsqueeze(1)  # noqa: E731
    a = _batches(X, Y, S, avg, bleed, 11, lambda *d: _inline_make(*d, stack))
    b = _batches(X, Y, S, avg, bleed, 11, lambda *d: D.batch_maker(*d, "cpu"))
    for (xa, ya), (xb, yb) in zip(a, b):
        assert xa.dtype == xb.dtype and xa.shape == xb.shape
        assert torch.equal(xa, xb) and torch.equal(ya, yb)


def _real_available():
    return (CACHE / "input.npy").exists() and (CACHE / "average-fold2.npy").exists() and D.CROPS.exists()


def test_make_clip_matches_inline_on_cache_rows_and_real_bleed():
    import pytest

    if not _real_available():
        pytest.skip("development data absent")
    import soundfile as sf

    from learn import train as TR

    # the bleed pool as `fit` built it inline
    fold = 2
    fold_of, band_of = TR.k3_folds()
    inline_bleed = []
    for part, b in band_of.items():
        if fold_of[b] != fold and (D.CROPS / part / "backing_instrumental.wav").exists():
            y, _ = sf.read(str(D.CROPS / part / "backing_instrumental.wav"), dtype="float32", always_2d=True)
            inline_bleed.append(y.mean(1))
    bleed = D.load_bleed(fold)
    assert len(bleed) == len(inline_bleed) > 0
    assert all(np.array_equal(a, b) for a, b in zip(bleed, inline_bleed))

    rows = [0, 17, 5000]
    Xm = np.load(CACHE / "input.npy", mmap_mode="r")
    Ym = np.load(CACHE / "di.npy", mmap_mode="r")
    Sm = np.load(CACHE / "di_spectrum.npy", mmap_mode="r")
    X, Y, S = (np.stack([np.asarray(A[i]) for i in rows]) for A in (Xm, Ym, Sm))
    avg = np.load(CACHE / "average-fold2.npy")
    assert len(json.loads((CACHE / "meta.json").read_text())) == len(Xm)
    for seed in (0, 2):
        _assert_same(_batches(X, Y, S, avg, bleed, seed, _inline_np),
                     _batches(X, Y, S, avg, bleed, seed, _factored_make_numpy))


if __name__ == "__main__":
    class _Skip(Exception):
        pass

    import types
    try:
        import pytest  # noqa: F401
    except ImportError:                     # a torch venv without pytest
        def _importorskip(name):
            try:
                return __import__(name)
            except ImportError:
                raise _Skip(name)

        def _skip(msg):
            raise _Skip(msg)

        sys.modules["pytest"] = types.SimpleNamespace(importorskip=_importorskip, skip=_skip)
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("PASS", name)
            except _Skip as e:
                print("SKIP", name, e)
