"""EfficientAT's network, front end and input quantisation (`learn/eat_net.py`, `learn/eat_build.py`, `learn/eat_embed.py`)."""
import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

from learn import eat_build as EB
from learn import eat_embed as EE
from learn import eat_net as E


def test_widths_give_the_published_sizes():
    assert sum(p.numel() for p in E.network(1.0).parameters()) == pytest.approx(4.88e6, rel=0.002)
    assert sum(p.numel() for p in E.network(0.4).parameters()) == pytest.approx(0.983e6, rel=0.002)


def test_the_body_downsamples_by_32_in_both_axes():
    got, logits = E.maps(E.network(0.4).eval(), torch.zeros(2, 1, 128, 450))
    assert logits.shape == (2, 527)
    assert [got[q].shape[2:] for q in (1, 3, 6, 12, 15)] == [(64, 225), (32, 113), (16, 57), (8, 29), (4, 15)]
    assert sorted(got) == list(range(17))


def test_mel_banks_are_triangles_with_a_zero_nyquist_column():
    b = E.mel_banks(128)
    assert b.shape == (128, E.N_FFT // 2 + 1)
    assert b.min() == 0 and b.max() <= 1
    assert (b[:, -1] == 0).all()


def test_band_centres_rise_within_the_range():
    c = E.band_centres(128)
    assert (np.diff(c) > 0).all() and 0 < c[0] < 100 and 14000 < c[-1] < E.FMAX


def test_front_keeps_level_through_fixed_constants():
    t = np.arange(E.SR * 2) / E.SR
    y = 0.1 * np.sin(2 * np.pi * 1000 * t)[None].astype(np.float32)
    a, b = E.front(y), E.front(y * 10)
    assert a.shape == (1, 128, 200)
    peak = a[0, :, 100].argmax()
    assert float(b[0, peak, 100] - a[0, peak, 100]) == pytest.approx(2 * np.log(10) / 5, abs=0.01)


def test_quantisation_round_trips_within_half_a_step():
    x = np.linspace(-1.4, 3.5, 500).reshape(10, 50)
    assert np.abs(EB.dequant(EB.quant(x)) - x).max() <= 0.5 / EB.Q_SCALE + 1e-6


def test_stats_have_the_declared_sizes():
    net = E.network(1.0).eval()
    maps_, logits = E.maps(net, torch.zeros(2, 1, 128, 350))
    s = EE.stats_of(maps_, logits)
    assert s["g16"].shape == (2, 1920) and s["g1"].shape == (2, 32)
    assert s["f3"].shape == (2, 2 * 24 * 32) and s["f12"].shape == (2, 2 * 112 * 8) and s["f15"].shape == (2, 2 * 160 * 4)
    assert s["f5"].shape == (2, 2 * 40 * 16) and s["f11"].shape == (2, 2 * 112 * 8) and s["f13"].shape == (2, 2 * 160 * 4)
    assert s["logits"].shape == (2, 527)
    assert set(s) == set(EE.STATS)


def test_tuned_net_has_full_space_outputs_and_taps_its_blocks():
    from learn import eat_train as ET
    from learn import full_space as F
    from learn import song_model as SM

    net = ET.build(E.network(1.0)).eval()
    cond = torch.zeros(2, len(SM.AMPS) + len(SM.CLASSES) + 2)
    logpi, mu, ls, sw, cat, amp = net(torch.zeros(2, 1, 128, ET.FRAMES), cond)
    assert logpi.shape == (2, SM.K_MIX) and mu.shape == (2, SM.K_MIX, len(F.CONT)) and ls.shape == mu.shape
    assert sw.shape == (2, len(F.SW)) and len(cat) == len(F.CAT) and amp.shape == (2, len(F.AMPS))


def test_crop_keeps_the_last_frames():
    from learn import eat_train as ET

    x = np.arange(450)[None]
    assert ET.crop(x).shape == (1, ET.FRAMES) and ET.crop(x)[0, 0] == 100


def test_variants_are_stable_and_in_range():
    from learn import eat_train as ET

    v = [ET.variant_of(800001, e) for e in range(60)]
    assert v == [ET.variant_of(800001, e) for e in range(60)]
    assert set(v) == set(range(EB.WIDE_K))


def test_seeded_reads_each_seed_through_its_own_bank_and_joins_their_cuts():
    from learn import eat_render as ER

    class Bank:
        def __init__(self, n):
            self.n, self.mix_cut = n, {n: (n,)}

        def __call__(self, rep, seed, f, amp, cls):
            return (self.n, rep, seed, f, amp, cls)

    s = ER.Seeded({1: Bank(10), 2: Bank(20)}, "mix:pub")
    assert s("W", 2, "path", "ac20", "clean") == (20, "mix:pub", None, "path", "ac20", "clean")
    assert s.mix_cut == {10: (10,), 20: (20,)}
