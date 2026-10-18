"""The rebuild-tone step's torch side (docs/rebuild-tone-plan.md): the short-time treble loss, the
declared metric E_st, the selection rule, the seeds and the gate's crops. Needs torch (the
demucs-venv interpreter); skipped otherwise."""

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

from learn import rebuild_tone_train as RT  # noqa: E402

SR = 48000


def _notes(n=3 * SR, seed=0, treble_mod=0.0):
    """Decaying harmonic notes; `treble_mod` modulates the harmonics above 2 kHz over time (a
    short-time treble change that no fixed EQ can express)."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for start in np.arange(0.05, n / SR - 0.3, 0.3):
        f0 = 196 * 2 ** (rng.integers(0, 12) / 12)
        m = t >= start
        env = np.exp(-(t[m] - start) * 5)
        for h in range(1, 40):
            f = f0 * h
            if f > 16000:
                break
            g = 1.0 + (treble_mod * np.sin(2 * np.pi * 3 * t[m]) if f > 2000 else 0.0)
            x[m] += env * g * np.sin(2 * np.pi * f * (t[m] - start) + rng.random() * 6) / h
    return x * 0.1 + rng.standard_normal(n) * 1e-5


def _eq(x, lo, hi, db):
    """A fixed zero-phase gain of `db` between lo and hi Hz."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f >= lo) & (f <= hi)] *= 10 ** (db / 20)
    return np.fft.irfft(X, len(x))


def test_band_weights():
    f = np.array([100.0, 1000.0, 2000 * 2 ** (-1 / 6), 2000.0, 4000.0, 8000.0, 8000 * 2 ** (1 / 6), 12000.0])
    w = RT.st_weights(f)
    assert w[0] == 0 and w[1] == 0 and w[-1] == 0
    assert w[3] == 1 and w[4] == 1 and w[5] == 1
    assert abs(w[2] - 0.5) < 1e-9 and abs(w[6] - 0.5) < 1e-9


def test_est_zero_on_itself_and_blind_to_a_fixed_eq():
    x = _notes()
    assert RT.est(x, x) == pytest.approx(0, abs=1e-9)
    eqd = _eq(x, 2500, 6000, 6.0)                       # a fixed treble boost
    assert RT.est(eqd, x) < 0.3
    assert RT.est(_notes(treble_mod=0.8), x) > 1.0       # a short-time treble change is seen


def test_est_ignores_errors_below_two_khz():
    x = _notes()
    assert RT.est(_eq(x, 100, 1500, 6.0) + 0 * x, x) < 0.3


def _t(x):
    return torch.tensor(np.asarray(x, np.float32))[None, None]


def test_st_loss_gradient_and_invariance():
    x = _notes()
    y = _t(x)
    p = _t(_notes(treble_mod=0.8)).requires_grad_()
    loss = RT.st_loss(p, y)
    loss.backward()
    assert torch.isfinite(loss) and torch.isfinite(p.grad).all() and p.grad.abs().sum() > 0
    same = float(RT.st_loss(y.clone(), y))
    eq = float(RT.st_loss(_t(_eq(x, 2500, 6000, 6.0)), y))
    low = float(RT.st_loss(_t(_eq(x, 100, 1000, 6.0)), y))
    assert same < 0.02                                   # the smooth |·| floor (sqrt(eps) = 0.01 dB)
    assert eq < 0.3 * float(loss.detach()) and low < 0.3 * float(loss.detach())


def test_st_loss_batches_and_masks():
    x = np.stack([_notes(seed=0), _notes(seed=1)])
    y = torch.tensor(x, dtype=torch.float32)[:, None]
    silent = y.clone()
    silent[1] = 0
    v = RT.st_loss(silent, y)          # a silent (constant) output: the target's own short-time variation
    assert torch.isfinite(v) and float(v) > 1 and float(RT.st_loss(y.clone(), y)) < 0.02


def test_selection_rules():
    assert RT.better("stm", 6.0, 6.03) and not RT.better("stm", 6.0, 6.01) and RT.better("stm", 6.0, None)
    assert RT.better("rank", 0.6, 0.59) and not RT.better("rank", 0.6, 0.598)
    assert not RT.better("stm", None, 6.0)


def test_seeds_and_names():
    assert RT.SEEDS[0] == (0, 1)                         # stage T's own data and proxy streams
    assert RT.SEEDS[1][0] != 0 and RT.SEEDS[1][1] != 1
    assert RT.CONTROL_OF == {0: "stm", 1: "rank"}
    assert RT.net_path("stm_s0", 2).name == "fold2.pt" and "models-stm-s0-f2" in str(RT.net_path("stm_s0", 2))
    assert "rebuild-gap" in str(RT.net_path("rank_s0", 1)) and "rebuild-gap" in str(RT.net_path("ctl_tr", 1))
    assert set(RT.TRAINED_ARMS.values()) == {"stm_s0", "ctl_s0", "rank_s1", "ctl_s1"}


def test_gate_crops_disjoint_and_seeded():
    class Fake:
        va = np.arange(1000, 1400)

    vidx = np.arange(1000, 1096)
    a, b = RT.gate_crops(Fake, 0, vidx), RT.gate_crops(Fake, 0, vidx)
    assert len(a) == RT.GATE_CROPS and not set(a) & set(vidx) and np.array_equal(a, b)
    assert not np.array_equal(a, RT.gate_crops(Fake, 1, vidx))


def test_step_batch_depends_on_the_step_only():
    """A skipped step must not shift the data stream between an arm and its control: the batch of
    step k (rows and augmentation generator) is a function of (data seed, k) alone."""
    class Fake:
        tr = np.arange(5000)
        rng = None

    a, b = Fake(), Fake()
    for k in range(5):                       # arm: steps 0..4 drawn in order
        RT.step_batch(a, 0, k)
    ra = RT.step_batch(a, 0, 7)
    ga = a.rng.random()
    rb = RT.step_batch(b, 0, 7)              # control: jumps straight to step 7 (as after skips)
    assert np.array_equal(ra, rb) and b.rng.random() == ga
    assert not np.array_equal(RT.step_batch(a, 0, 8), ra) and not np.array_equal(RT.step_batch(a, 100, 7), ra)
