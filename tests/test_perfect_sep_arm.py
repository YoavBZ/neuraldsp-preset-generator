"""Amendment 3's perfect-separation arms (`learn/perfect_sep_arm.py`): YT searches C′'s rebuild of the
true amp track against the true amp track; ZT the true DI against it. Everything else is stage F's
H. Fakes only."""

import math
import random

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import arm_a_mega53 as M  # noqa: E402
from learn import perfect_sep_arm as P  # noqa: E402
from tests.test_arm_a_mega53 import AMP, S0, toy_units  # noqa: E402


class FakeRR:
    def __init__(self):
        self.count, self.dis = 0, []

    def render(self, di32, sel, x):
        self.count += 1
        self.dis.append(di32)
        return np.full(M.SR, 0.1)

    def menu(self):
        return {}

    def close(self):
        pass


def test_search_inputs_use_the_true_amp_track(monkeypatch, tmp_path):
    ref, rb, di = np.ones(10), np.full(10, 2.0), np.full(10, 3.0)
    monkeypatch.setattr(P, "reference", lambda s: ref)
    monkeypatch.setattr(P, "REBUILT", tmp_path)
    np.save(tmp_path / "p.npy", rb)
    r, d = P.search_inputs("YT", {"di": di}, "p")
    assert r is ref and np.array_equal(d, rb)
    r, d = P.search_inputs("ZT", {"di": di}, "p")
    assert r is ref and d is di
    with pytest.raises(ValueError):
        P.search_inputs("H", {"di": di}, "p")


def test_search_primes_each_arm_and_scores_at_the_judge_lag(monkeypatch, tmp_path):
    ref, rb, di = np.ones(1000), np.full(1000, 2.0), np.full(1000, 3.0)
    part = {"judge_lag": 77}
    ctx = {"part": part, "sel": "sel", "S": S0, "S_stored": S0, "di": di, "di32": di.astype(np.float32), "ref": ref}
    dirs = [("p", AMP, "A", "B"), ("p", AMP, "B", "A")]
    monkeypatch.setattr(P, "OUT", tmp_path)
    monkeypatch.setattr(P, "reference", lambda s: ref)
    monkeypatch.setattr(P, "search_inputs", lambda arm, c, s: (ref, rb if arm == "YT" else di))
    M._save(tmp_path / "check.json", {"ok": True})
    for name, fn in {"require_heldout_ok": lambda: None, "stage_dirs": lambda st: dirs, "check_stop": lambda: None,
                     "wait_render_gate": lambda: None, "disk_ok": lambda n: True,
                     "group_ctx": lambda *a: ctx}.items():
        monkeypatch.setattr(M, name, fn)
    monkeypatch.setitem(M.N_DIRS, "F", 2)
    monkeypatch.setattr(M.L, "SwapGuard", lambda: type("G", (), {"check": lambda self: None})())
    monkeypatch.setattr(M.L, "menu_S", lambda: {})
    rr = FakeRR()
    monkeypatch.setattr(M, "renderer", lambda: rr)
    calls = []

    def fake_run(rr_, ctx_, stage, arm, slug, amp, search, held, xd, *, stem, rb, lag, path, s_lags):
        assert s_lags == (-52,)
        calls.append((arm, stem is ref, rb, lag, path))
        M._save(path, {"status": "done", "renders": 55})

    monkeypatch.setattr(M, "run_direction", fake_run)
    P.cmd_search(("YT", "ZT"), (0, 1))
    assert [c[0] for c in calls] == ["YT", "YT", "ZT", "ZT"]
    assert all(c[1] and c[3] == 77 for c in calls)                        # true amp track, judge lag
    assert np.array_equal(calls[0][2], rb) and calls[2][2] is di
    assert rr.count == 2                                                   # one priming render per arm
    assert np.array_equal(rr.dis[0], rb.astype(np.float32)) and np.array_equal(rr.dis[1], di.astype(np.float32))
    assert P.spent("YT") == 1 + 2 * 55 and calls[0][4] == tmp_path / "YT" / "p" / AMP / "A.json"
    rr2 = FakeRR()
    monkeypatch.setattr(M, "renderer", lambda: rr2)
    P.cmd_search(("YT", "ZT"), (0, 1))                                     # resumable: nothing left
    assert rr2.count == 0 and len(calls) == 4


def test_render_count_cap_and_gate():
    assert P.expected_renders() == 63 + 126 * 55 == 6_993 < P.CAP["YT"] == P.CAP["ZT"]
    assert M._matches("python -m learn.perfect_sep_arm search --arms YT --shard 0/3", M.RENDERS)
    assert not M._matches("python -m learn.perfect_sep_arm report", M.RENDERS)


def test_rebuild_problems_level_and_alignment():
    ok = {"lufs": -22.9, "gcc_vs_source": -52}
    log = {"a": ok, "b": {**ok, "lufs": -22.8}, "c": ok, "d": ok}
    h_lag = {"a": 0, "b": 0, "c": 1024, "d": 1024}
    h_log = {"c": {"gcc_vs_source": -53}, "d": {"gcc_vs_source": 0}}
    bad = P.rebuild_problems(log, ["a", "b", "c", "d", "e"], h_lag, {"c": 0, "d": 0}, h_log)
    assert set(bad) == {"b", "d", "e"}                                     # c passes through the chain (−52 vs −53)
    assert "loudness" in bad["b"][0] and bad["e"] == ["missing"]


def test_relevel_converges_on_a_gated_signal():
    pytest.importorskip("pyloudnorm")
    from learn import local_objective as LO

    rng = np.random.default_rng(1)
    x = rng.standard_normal(48000 * 10) * 0.05
    x[: 48000 * 4] *= 1e-3                                                 # quiet blocks near the absolute gate
    y, n = P.relevel(x)
    assert abs(LO.lufs(y) - M.LUFS_TARGET) <= M.LUFS_TOL and n >= 1


def toy_units_with_arms(zt=True):
    units = toy_units()
    rng = random.Random(9)
    for u in units:
        h = u["d"]["H"]
        u["d"]["XO"] = h * math.exp(0.02 + 0.02 * rng.gauss(0, 1))
        u["d"]["YT"] = h * math.exp(-0.05 + 0.02 * rng.gauss(0, 1))
        u["d"]["YT_unshrunk"] = u["d"]["YT"]
        u["rec"] = {"XO": {"status": "done"}, "YT": {"status": "done", "fallback": None, "activity_fallback": 0}}
        if zt:
            u["d"]["ZT"] = u["d"]["YT"] * math.exp(-0.1 + 0.02 * rng.gauss(0, 1))
            u["d"]["ZT_unshrunk"] = u["d"]["ZT"]
            u["rec"]["ZT"] = {"status": "done", "fallback": None, "activity_fallback": 0}
    return units


def test_report_primaries_and_shares():
    units = toy_units_with_arms()
    filt = {r: (lambda u: True) for r in P.ROWS}
    rep = P.report_from_units(units, {})
    assert rep["zt"]
    want = M.contrast(units, "YT", "H", P.ROWS, filt)["rows"]["all"]["all"]
    got = rep["contrasts"]["YT_minus_H"]["rows"]["all"]["all"]
    assert got["band_weighted_mean"] == pytest.approx(want["band_weighted_mean"]) and got["band_weighted_mean"] < 0
    assert rep["contrasts"]["YT_minus_XO"]["rows"]["all"]["all"]["band_weighted_mean"] < 0
    assert rep["contrasts"]["ZT_minus_YT"]["rows"]["all"]["all"]["band_weighted_mean"] < 0
    yt_s = rep["contrasts"]["YT_minus_S"]["rows"]["all"]["all"]["band_weighted_mean"]
    zt_s = rep["contrasts"]["ZT_minus_S"]["rows"]["all"]["all"]["band_weighted_mean"]
    sh = rep["share_of_ceiling"]["YT"]
    assert sh["vs_K_S"] == pytest.approx(yt_s / -0.293)
    assert 0 < sh["vs_ZT"]["ratio"] < 1 and sh["vs_ZT"]["ratio"] == pytest.approx(yt_s / zt_s, rel=0.05)


def test_report_without_zt_skips_its_contrasts():
    rep = P.report_from_units(toy_units_with_arms(zt=False), {})
    assert not rep["zt"] and "ZT_minus_S" not in rep["contrasts"] and "vs_ZT" not in rep["share_of_ceiling"]["YT"]
    assert rep["YT_fallbacks"] == 0


def test_run_direction_scores_s_at_the_extra_lags_without_renders(monkeypatch, tmp_path):
    ref, rb, di = np.ones(1000), np.full(1000, 2.0), np.full(1000, 3.0)
    ctx = {"part": {"judge_lag": 77}, "sel": "sel", "S": S0, "S_stored": S0, "di": di,
           "di32": di.astype(np.float32), "ref": ref}
    monkeypatch.setattr(M, "objective", lambda r, y, b, half, lag=M.OBJ_LAG: (1.0 + lag / 1000, False))
    monkeypatch.setattr(M.K, "judge", lambda r, y, d, lag: {"A": 1.0, "B": 2.0})
    monkeypatch.setattr(M, "save_kept_flac", lambda p, y: 1.0)
    monkeypatch.setattr(M.L, "main_stage", lambda dims, S, f, seed: (f(S), f(S), (S, 1.0, 2))[2])
    rr = FakeRR()
    path = tmp_path / "A.json"
    M.run_direction(rr, ctx, "F", "YT", "p", AMP, "A", "B", None, stem=ref, rb=rb, lag=77, path=path, s_lags=(-52,))
    rec = M._load(path)
    assert rec["renders"] == 5 and rec["s_lag_check"] == {"lag": 77, "value": 1.077, "at": {"-52": 0.948}}
    M.run_direction(rr, ctx, "F", "H", "p", AMP, "A", "B", None, stem=ref, rb=rb, path=path)
    assert "s_lag_check" not in M._load(path)                             # off by default


def test_contrasts_share_one_direction_set_when_zt_ran():
    units = toy_units_with_arms()
    units[0]["d"]["ZT"] = math.inf                                         # a refused ZT direction
    rep = P.report_from_units(units, {})
    n = {k: c["directions"] for k, c in rep["contrasts"].items()}
    assert len(set(n.values())) == 1 and n["YT_minus_H"] == len(units) - 1
    assert rep["contrasts"]["YT_minus_H"]["rows"]["no_lag_part"] is not None
