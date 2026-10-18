"""The dose probe's pure parts (docs/dose-probe-plan.md): the truth's alignment onto the rebuild's
timeline, the gain field and the long-term hold, the probes' checks and hashes, the yield rule, the
render pattern other jobs count, the declared readings and the extension rule. No renders."""

import math
import pathlib
import re
import subprocess

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import local_objective as LO  # noqa: E402
from learn import rebuild_dose as RD  # noqa: E402
from learn import rebuild_gap as G  # noqa: E402
from learn import rebuild_tone_train as RT  # noqa: E402

SR = 48000
REPO = pathlib.Path(__file__).resolve().parents[1]


def _pair(n=SR * 3, seed=0):
    """x: notes with a steady treble noise (the rebuild's smeared short-time structure); t: the same
    notes with treble noise that decays with each note (the truth's structure)."""
    rng = np.random.default_rng(seed)
    tt = np.arange(n) / SR
    base, env = np.zeros(n), np.zeros(n)
    for start in np.arange(0.1, n / SR - 0.3, 0.35):
        f0 = 110 * 2 ** (rng.integers(0, 24) / 12)
        m = tt >= start
        e = np.exp(-(tt[m] - start) * 8)
        env[m] = np.maximum(env[m], e)
        for h in range(1, 8):
            base[m] += e * np.sin(2 * np.pi * f0 * h * (tt[m] - start)) / h
    from scipy.signal import butter, sosfilt

    hf = sosfilt(butter(4, [2500, 7000], btype="band", fs=SR, output="sos"), rng.standard_normal(n))
    x = 0.1 * base + 0.02 * hf * 0.5
    t = 0.1 * base + 0.02 * hf * env
    return x, t


# --- the truth on the rebuild's timeline ----------------------------------------------------------------

def test_truth_on_shifts_the_truth_onto_the_rebuilds_timeline():
    x, t = _pair()
    r = G.shift(x, 37)                                      # the rebuild lags by 37 samples: r(n) = x(n − 37)
    tr = G.shift(t, 37)
    tx, lag, absc, coh = RD.truth_on(r, t, judge_lag=30)
    assert lag == 37 and absc > 0.5 and coh > 0.3
    mid = slice(SR // 4, -SR // 4)
    assert np.allclose(tx[mid], tr[mid])


# --- the probes ------------------------------------------------------------------------------------------

def _built(names=None):
    from learn.direc_check import to_lufs

    x, t = _pair()
    x = to_lufs(x, RD.LUFS)
    return x, t, RD.build_probes(x, t, names)


def test_dose_zero_returns_the_anchor_and_doses_cut_est_in_order():
    x, t, (p, info) = _built(["dose0", "dose25", "dose50", "dose100", "shift100"])
    assert np.abs(p["dose0"] - x).max() < RD.ID_TOL
    e = {k: RT.est(v, t) for k, v in p.items()}
    assert e["dose100"] < e["dose50"] < e["dose25"] < e["dose0"]
    assert e["shift100"] > e["dose0"]                        # the right gains at the wrong times
    assert info["gain_gt12_share"] is not None and info["frames"] > 100


def test_the_hold_keeps_the_long_term_balance_level_and_timing():
    from learn import rank_margin as RM

    x, t, (p, _) = _built(["dose100", "full100", "full_gl"])
    for name, y in p.items():
        assert len(y) == len(x)
        assert G.lsd_db(y, x) < 0.5, name                  # the long-term spectrum is the anchor's
        assert abs(LO.lufs(y) - RD.LUFS) < RD.LUFS_TOL
        assert abs(int(RM.gcc_lag(y, x))) <= RD.LAG_TOL


def test_gain_field_masks_edges_and_band():
    x, t = _pair()
    f, _, X = G.stft(x)
    _, _, T = G.stft(t)
    g, m = RD.gain_field(X, T, f)
    assert not m[:, :RD.EDGE].any() and not m[:, -RD.EDGE:].any()
    assert np.all(g[f < 1500] == 0) and np.all(g[f > 10500] == 0)
    assert np.abs(g).max() > 3
    inner = RD.interior(X.shape[1])
    assert inner.sum() == X.shape[1] - 2 * RD.EDGE


def test_hold_scales_interior_frames_only():
    rng = np.random.default_rng(1)
    X = rng.standard_normal((5, 10)) + 1j * rng.standard_normal((5, 10))
    inner = RD.interior(10)
    Y = RD.hold(3 * X, X, inner)
    assert np.allclose(Y, X)                                    # a fixed gain is undone
    Y2 = RD.hold(np.where(inner[None], 3 * X, 100 * X), X, inner)
    assert np.allclose(Y2[:, ~inner], X[:, ~inner])             # the edge frames are X


def test_hash_is_reproducible_and_the_r2_anchor_is_the_anchor():
    x, t, (p, _) = _built(["dose50", RD.ANCHOR_R2])
    _, _, (q, _) = _built(["dose50"])
    assert RD.probe_hash(p["dose50"]) == RD.probe_hash(q["dose50"])
    assert RD.probe_hash(p[RD.ANCHOR_R2]) == RD.probe_hash(x)
    assert RD.probe_hash(p["dose50"]) != RD.probe_hash(x)


def test_probe_problems():
    a = {"len": 10, "finite": True, "gcc": 0, "lufs": -22.9, "lsd": 1.5, "lsd_vs_anchor": 0.0, "peak_over_db": 0.0}
    assert RD.probe_problems("p", dict(a, lsd_vs_anchor=0.1, peak_over_db=4.0), a) == []
    bad = dict(a, len=9, gcc=5, lufs=-22.0, lsd=1.9, lsd_vs_anchor=1.5, peak_over_db=7.0)
    assert len(RD.probe_problems("p", bad, a)) == 6


def test_peak_is_against_the_louder_of_anchor_and_truth():
    a, t, y = np.array([0.5, -1.0]), np.array([2.0, 0.0]), np.array([4.0, 0.0])
    assert RD.peak_over_db(y, a, t) == pytest.approx(20 * math.log10(2))


def test_alignment_problems():
    assert RD.alignment_problems(0.5, 0.5) == []
    assert RD.alignment_problems(0.2, 0.5) and RD.alignment_problems(0.5, 0.29)


# --- scoring ---------------------------------------------------------------------------------------------

class FakeJudge:
    def __init__(self, refuse=False):
        self.calls, self.refuse = [], refuse

    def __call__(self, rec, y, mask, lag, a, b):
        self.calls.append((mask[0], lag))
        if self.refuse and mask[0] in (7.0, 9.0):
            return None, "the DI pauses"
        return 1.0 + mask[0] * 1e-2, None


def test_score_render_declared_and_fixed_mask():
    sig = {"di": np.full(10, 7.0), "anchor": np.full(10, 9.0), "reference": np.full(10, 2.0)}
    j = FakeJudge()
    out = RD.score_render(np.ones(10), "dose100", sig, j)
    assert set(out) == {"decl", "xmask"}
    assert [m for m, _ in j.calls] == [7.0, 7.0, 9.0, 9.0]          # own mask, then the anchor's
    assert all(lag == G.OBJ_LAG for _, lag in j.calls)
    assert out["decl"]["A"] != out["xmask"]["A"]
    j2 = FakeJudge(refuse=True)
    out2 = RD.score_render(np.ones(10), "dose100", sig, j2)
    assert all(math.isfinite(v) for c in out2.values() for v in c.values())   # the record fallback


def test_bound_makes_every_probe_an_arm():
    out, arms = G.OUT, G.ARMS
    with RD.bound():
        assert G.OUT == RD.OUT
        assert all(G.is_arm(p) for p in (*RD.PROBES, RD.ANCHOR_R2, RD.COMPARATOR_ARM, RD.ANCHOR))
    assert G.OUT == out and G.ARMS == arms


# --- the machine ------------------------------------------------------------------------------------------

DOSE = "/v/.venv/bin/python -u -m learn.rebuild_tone render-dose --stage r1 --probe dose100 --shard {}/3"


def test_render_dose_is_counted_by_every_job():
    cmd = DOSE.format(0)
    assert any(re.search(p, cmd) for p in LO.RENDERS)
    assert re.search(r"-m learn\.rebuild_tone render\b", cmd)         # the pattern older checkouts carry
    assert LO.is_render_process(cmd)
    assert not LO.is_render_process("/v/.venv/bin/python -m learn.rebuild_dose slots")
    assert not LO.is_render_process("/v/.venv/bin/python -m learn.rebuild_dose build")


def test_busy_counts_foreign_jobs_and_lower_siblings_only():
    foreign = [(10, "/v/.venv/bin/python -u -m learn.pretrain_set render --n 1 --shard 0/3"),
               (11, "/v/.venv/bin/python -u -m learn.known_answer search --shard 1/3")]
    me = 50
    assert not RD.busy(foreign, me)
    assert RD.busy(foreign + [(12, "/v/.venv/bin/python -m learn.known_answer search --shard 2/3")], me)
    assert RD.busy(foreign + [(40, DOSE.format(1))], me)               # a lower-PID lane counts
    assert not RD.busy(foreign + [(60, DOSE.format(1))], me)           # a higher one doesn't
    assert not RD.busy([(40, DOSE.format(1)), (45, DOSE.format(2))], me)
    assert RD.busy([(9, "/v/.venv/bin/python -m learn.separate --x")], me)
    assert not RD.busy(foreign + [(me, DOSE.format(0))], me)           # itself


def test_rebuild_tone_has_the_render_dose_entry(monkeypatch):
    from learn import rebuild_tone as TN

    seen = []
    monkeypatch.setattr(RD, "cmd_render", lambda shard, probe, stage: seen.append((shard, probe, stage)))
    TN.main(["render-dose", "--probe", "dose50", "--shard", "2/3", "--stage", "r2"])
    assert seen == [((2, 3), "dose50", "r2")]


def test_runner_parses_and_ends_with_all_done():
    p = REPO / "learn" / "rebuild_dose_run.zsh"
    if subprocess.run(["which", "zsh"], capture_output=True).returncode == 0:
        assert subprocess.run(["zsh", "-n", str(p)], capture_output=True).returncode == 0
    text = p.read_text()
    assert text.count('log "all done') == 3
    assert "PROBES=(dose100 shift100 full_gl full100 dose50 dose25)" in text
    assert tuple(text.split("PROBES=(")[1].split(")")[0].split()) == RD.PROBES
    assert "setopt no_bg_nice" in text and "learn.rebuild_dose slots" in text


# --- the readings and the rules ----------------------------------------------------------------------------

def _c(m, half):
    return {"band_weighted_mean": m, "lo90": m - half, "hi90": m + half}


def test_classify():
    q = 0.04
    assert RD.classify(_c(0.10, 0.05), q) == "above"
    assert RD.classify(_c(-0.10, 0.05), q) == "below"
    assert RD.classify(_c(0.0, 0.03), q) == "near 0"
    assert RD.classify(_c(-0.05, 0.08), q, "upper") == "near 0"       # upper end +0.03
    assert RD.classify(_c(-0.05, 0.08), q, "lower") == "undecided"    # lower end −0.13
    assert RD.classify(_c(0.03, 0.05), q, "both") == "undecided"
    assert RD.classify({}, q) is None


def test_shape_against_the_cut_ratio():
    assert RD.shape(0.62, 0.62) == "proportional"
    assert RD.shape(0.80, 0.62) == "concave"
    assert RD.shape(0.40, 0.62) == "convex"
    assert RD.shape(None, 0.62) is None


def test_gate_cut():
    cuts = {"dose25": 0.15, "dose50": 0.29, "dose100": 0.47}
    assert RD.gate_cut({"dose25": 0.01, "dose50": 0.06, "dose100": 0.10}, cuts) == 0.29
    assert RD.gate_cut({"dose25": 0.06, "dose50": 0.07, "dose100": 0.10}, cuts) == 0.15
    assert RD.gate_cut({"dose25": 0.0, "dose50": 0.0, "dose100": -0.01}, cuts) is None


def test_cut_ratios():
    med = {"dose25": {"cut": 0.15}, "dose50": {"cut": 0.29}, "dose100": {"cut": 0.47}}
    r = RD.cut_ratios(med)
    assert r["dose25"] == pytest.approx(0.15 / 0.47) and r["dose50"] == pytest.approx(0.29 / 0.47)


def test_extension_order_and_control():
    ratio = 0.948
    r1 = {f"full_gl-{RD.ANCHOR}": _c(0.10, 0.105), f"dose100-{RD.ANCHOR}": _c(0.068, 0.07),
          f"dose50-{RD.ANCHOR}": _c(0.02, 0.10), f"full100-{RD.ANCHOR}": _c(0.20, 0.10)}
    assert RD.extension(r1, ratio) == ["dose100", "shift100", "full_gl"]
    assert RD.extension({}, ratio) == []


def test_readings_labels():
    r1 = {f"full_gl-{RD.ANCHOR}": {**_c(0.12, 0.05), "share_of_gap": {"ratio": 0.8}},
          "full_gl-full100": _c(0.0, 0.03), f"full100-{RD.ANCHOR}": _c(0.12, 0.05),
          "dose100-full100": _c(-0.02, 0.03), f"shift100-{RD.ANCHOR}": _c(-0.01, 0.03),
          "dose100-shift100": _c(0.10, 0.04)}
    r = RD.readings(r1, 0.04)
    assert r["1_full_gl"] == {"vs_anchor": "above", "share": 0.8}
    assert r["2_consistency"]["full_gl-full100"] == "near 0"
    assert r["3_region"]["dose100-full100"] == "undecided"             # lower end −0.05
    assert r["5_control"] == {"shift100_vs_anchor": "near 0", "dose100-shift100": "above"}
