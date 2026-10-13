import itertools

import numpy as np

from learn import locator_truth as T


def _brute(hit, k, gap):
    n = len(hit)
    sets = [c for c in itertools.combinations(range(n), k)
            if all(b - a >= gap for a, b in zip(c, c[1:]))]
    if not sets:
        return None
    return sum(any(hit[i] for i in c) for c in sets) / len(sets)


def test_random_hit3_matches_enumeration():
    rng = np.random.default_rng(0)
    for n in (5, 12, 25, 40):
        for _ in range(5):
            hit = rng.random(n) < 0.2
            want = next(v for k in (3, 2, 1) if (v := _brute(hit, k, 10)) is not None)
            assert abs(T.random_hit3(hit) - want) < 1e-12


def test_random_hit3_edges():
    assert T.random_hit3(np.zeros(30, bool)) == 0.0
    assert T.random_hit3(np.ones(30, bool)) == 1.0


def test_window_sums():
    x = np.arange(250, dtype=float)
    starts = T._windows(250)
    assert starts[-1] == 150
    assert np.allclose(T._win_sum(x, starts), [x[s:s + 100].sum() for s in starts])


def test_electric_names():
    assert T._is_electric("21_ElecGtr1Mic1.wav")
    assert T._is_electric("GTR 1 Amp M 80.wav")
    assert not T._is_electric("20_ElecGtr1DI.wav")
    assert not T._is_electric("GTR 1 DI_TDP-1.wav")
    assert not T._is_electric("12_AcousticGtr.wav")
    assert not T._is_electric("18_BassDI.wav")
