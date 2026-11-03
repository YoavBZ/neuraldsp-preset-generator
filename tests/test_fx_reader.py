import pytest

from learn import fx_reader as F


def test_lag_target_peaks_at_the_set_lag():
    np = pytest.importorskip("numpy")
    T = F.lag_target(np.log2([300.0, 60.0, 800.0]))
    assert T.shape == (3, F.LAGS)
    assert list(np.argmax(T, 1) + 1) == [30, 6, 80]           # lag k (10 ms each) sits at index k - 1
    assert np.allclose(T.sum(1), 1.0)


def test_prominence_and_lag_head():
    torch = pytest.importorskip("torch")
    a = torch.zeros(3, 2 * F.LAGS)
    assert torch.allclose(F.prominence(torch, a + 0.4), torch.zeros(3, 2, F.LAGS), atol=1e-6)   # flat: no prominence
    a[:, 29] = 1.0                                             # a bump at lag 30 in the first half
    p = F.prominence(torch, a)
    assert int(p[0, 0].argmax()) == 29 and float(p[0, 1].abs().max()) == 0.0
    m = F.net(torch, lag=True).eval()
    out = m(torch.zeros(3, 2, 96, 446), a)
    assert out.shape == (3, 2 + len(F.KNOBS) + F.LAGS)
    assert F.net(torch).eval()(torch.zeros(3, 2, 96, 446), a).shape == (3, 2 + len(F.KNOBS))
