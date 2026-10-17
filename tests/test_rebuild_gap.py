"""The rebuild-gap study's pure parts (docs/rebuild-gap-plan.md): cells, knob families, alignment
and rotation, the probes and their checks, scoring configurations, the stopping rules and the
queue gates. No renders."""

import math

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import knob_ceiling as K  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import rebuild_gap as G  # noqa: E402

SR = 48000
PARTS = [f"p{i:02d}" for i in range(24)]


def _guitarish(n=SR * 4, seed=0):
    """Plucked-like test signal: decaying harmonic notes with onsets, plus a little noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k, start in enumerate(np.arange(0.1, n / SR - 0.4, 0.35)):
        f0 = 110 * 2 ** (rng.integers(0, 24) / 12)
        m = t >= start
        env = np.exp(-(t[m] - start) * 4)
        for h in range(1, 8):
            x[m] += env * np.sin(2 * np.pi * f0 * h * (t[m] - start) + rng.random() * 6) / h
    return x * 0.1 + rng.standard_normal(n) * 1e-4


# --- cells ---------------------------------------------------------------------------------------

def test_probe_cells_balanced_and_fixed():
    a = G.probe_cells(PARTS)
    assert a == G.probe_cells(PARTS)
    assert sorted(a) == PARTS
    for amp in K.AMPS:
        assert sum(v == amp for v in a.values()) == 8


def test_r2_cells_are_the_other_48():
    r1 = set(G.r1_cells(PARTS))
    r2 = set(G.r2_cells(PARTS))
    assert len(r1) == 24 and len(r2) == 48 and not r1 & r2
    assert r1 | r2 == {(s, a) for s in PARTS for a in K.AMPS}


# --- knob families -----------------------------------------------------------------------------------

def test_knob_family():
    assert G.knob_family("parameters/inputGain") == "input gain"
    assert G.knob_family("pr12Amp/pr12Volume") == "amp gain"
    assert G.knob_family("sw50rAmp/sw50rLevel") == "amp gain"
    assert G.knob_family("ac20Amp/ac20Power") == "amp gain"
    assert G.knob_family("sw50rAmp/sw50rMid") == "amp tone"
    assert G.knob_family("ac20Amp/ac20Bright") == "amp tone"
    assert G.knob_family("cabParameters/leftMicType") == "cab"


def test_pair_family():
    dims = K.space("sw50r")
    S = {LO._k(d): (d.values[0] if d.kind in ("cat", "switch") else K.fmt(d.from_unit(0.5))) for d in dims}
    x = dict(S)
    ig = next(d for d in dims if d.key == "inputGain")
    x[LO._k(ig)] = K.fmt(ig.from_unit(0.625))
    assert G.pair_family(dims, S, x) == "input gain"
    y = dict(x)
    mid = next(d for d in dims if d.key == "sw50rMid")
    y[LO._k(mid)] = K.fmt(mid.from_unit(0.625))
    assert G.pair_family(dims, S, y) == "mixed"
    assert G.pair_family(dims, S, dict(S)) is None


def test_concordance_is_cross_half():
    true = {"A": [1.0, 2.0, 3.0], "B": [1.0, 2.0, 3.0]}
    obj = {"A": [3.0, 2.0, 1.0], "B": [1.0, 2.0, 3.0]}       # right on B only
    pairs = [(0, 1), (0, 2), (1, 2)]
    c, n = G.concordance(pairs, obj, true)
    assert n == 3 and c == pytest.approx(0.5)              # A's truth read with B's objective, and vice versa


# --- alignment and rotation --------------------------------------------------------------------------

def test_shift():
    x = np.arange(1.0, 6.0)
    assert list(G.shift(x, 2)) == [0, 0, 1, 2, 3]
    assert list(G.shift(x, -2)) == [3, 4, 5, 0, 0]
    assert list(G.shift(x, 0)) == list(x)


def test_rotate():
    x = _guitarish()
    assert np.allclose(G.rotate(x, math.pi), -x, atol=1e-6 * np.abs(x).max() + 1e-3 * np.abs(x).max())
    back = G.rotate(G.rotate(x, 0.9), -0.9)
    mid = slice(SR // 2, -SR // 2)
    assert np.abs(back[mid] - x[mid]).max() < 0.02 * np.abs(x).max()


def test_align_finds_lag_and_rotation_near_judge_lag():
    t = _guitarish()
    r = G.rotate(G.shift(t, -37), 1.1)                    # r(n) = rotated t(n + 37): r lags t by −37
    ra, lag, phi, c = G.align(r, t, judge_lag=-30)
    assert lag == -37
    assert phi == pytest.approx(1.1, abs=0.05)
    assert c > 0.95
    rt = G.rotate(ra, -phi)
    mid = slice(SR // 2, -SR // 2)
    assert G.best_snr_db(rt[mid], t[mid]) > 20


def test_align_window_is_around_judge_lag():
    t = _guitarish()
    r = G.shift(t, -400)                                  # outside ±100 of judge_lag 0
    _, lag, _, _ = G.align(r, t, judge_lag=0)
    assert abs(lag) <= G.ALIGN_WINDOW


# --- probes -----------------------------------------------------------------------------------------

def test_band_masks_complementary():
    f = np.fft.rfftfreq(1024, 1 / SR)
    lo, mid, hi = G.band_masks(f)
    assert np.abs(lo + mid + hi - 1).max() < 1e-12
    i100, i1k, i8k = (np.argmin(np.abs(f - v)) for v in (100, 1000, 8000))
    assert lo[i100] == pytest.approx(1) and mid[i1k] == pytest.approx(1) and hi[i8k] == pytest.approx(1)


def test_stft_roundtrip():
    x = _guitarish(SR)
    _, _, Z = G.stft(x)
    assert np.abs(G.istft(Z, len(x)) - x).max() < 1e-9


def test_onset_weights_cover_onsets():
    x = _guitarish()
    w, pos = G.onset_weights(x)
    assert len(pos) >= 5 and 0 < w.mean() < 0.5
    assert w.min() >= 0 and w.max() <= 1


def test_build_probes_on_a_rotated_shifted_copy():
    t = _guitarish(seed=1)
    r = G.rotate(G.shift(t, -30), 2.0) * 0.7
    out, info = G.build_probes(r, t, "x", judge_lag=-25)
    assert info["lag"] == -30 and info["phi_deg"] == pytest.approx(math.degrees(2.0), abs=3)
    assert set(out) == {"reb", "rot", "t_rot", "mag", "phase", "low", "mid", "high", "onset", "sustain", "half", "noise"}
    mid = slice(SR // 2, -SR // 2)
    # r̃ is t up to gain: every mix of t and r̃ is close to t's waveform
    for p in ("rot", "low", "mid", "high", "onset", "sustain", "half", "phase"):
        assert G.best_snr_db(out[p][mid], t[mid]) > 15, p
    assert G.best_snr_db(out["t_rot"][mid], G.rotate(t, 2.0)[mid]) > 30
    assert info["mask_sum_max"] < 1e-12 and info["roundtrip_max"] < 1e-9
    for m in G.MIX_PROBES:
        assert G.mix_problems(out[m], t, out["rot"]) == [], m


def test_build_probes_dep_eq_with_average():
    t = _guitarish(seed=2)
    from learn.di_robustness import smoothed_spectrum

    avg = smoothed_spectrum(t)
    out, _ = G.build_probes(t * 0.5, t, "x", judge_lag=0, avg=avg)
    assert "dep_eq" in out and np.isfinite(out["dep_eq"]).all()


def test_calibrated_noise_matches_band_error():
    t = _guitarish(seed=3)
    rng = np.random.default_rng(0)
    r = t + 0.3 * G.rotate(t, 1.5) + 0.01 * rng.standard_normal(len(t))
    f, _, T = G.stft(t)
    _, _, R = G.stft(r)
    N, target, reached = G.calibrated_noise(T, R, f, np.random.default_rng(1))
    assert np.max(np.abs(np.array(target) - np.array(reached))) < G.NOISE_TOL_DB


def test_interp_endpoints_and_no_cancellation():
    t = _guitarish(seed=5)
    f, _, T = G.stft(t)
    _, _, R = G.stft(-t)
    assert np.allclose(G.interp(T, R, np.ones(len(f))), T)
    assert np.allclose(G.interp(T, R, np.zeros(len(f))), R)
    H = G.interp(T, R, np.full(len(f), 0.5))                 # opposite phases: magnitude kept
    assert np.allclose(np.abs(H), np.abs(T), rtol=1e-6, atol=1e-12)


def test_mix_problems_flags_cancellation():
    t = _guitarish(seed=4)
    assert G.mix_problems(t, t, t) == []
    assert G.mix_problems(t + (-0.98 * t), t, -t) != []          # a cancelling mix


def test_probe_problems():
    ok = {"abs_c": 0.8, "coh_80_2k": 0.6, "lag_minus_judge_lag": 5, "noise_target_db": [1.0], "noise_reached_db": [1.1],
          "roundtrip_max": 0.0, "mask_sum_max": 0.0}
    assert G.probe_problems({"rot": -22.9}, -22.9, ok) == []
    assert G.probe_problems({"rot": -23.0}, -22.9, ok)                      # 0.1 LU off
    assert G.probe_problems({"rot": -22.9}, -22.9, {**ok, "abs_c": 0.2})
    assert G.probe_problems({"rot": -22.9}, -22.9, {**ok, "lag_minus_judge_lag": 100})
    assert G.probe_problems({"rot": -22.9}, -22.9, {**ok, "noise_reached_db": [2.0]})


def test_rotation_choice():
    assert G.choose_rotation([{"A": 3.0}, {"A": 2.0}, {"A": 2.0}, {"A": math.inf}]) == 1
    assert G.choose_rotation([{"A": math.inf}] * 8) == 0
    x = _guitarish(SR)
    assert np.array_equal(G.with_rotation(x, 0), x)
    assert np.allclose(G.with_rotation(x, 4), -x, atol=1e-3 * np.abs(x).max())


def test_anchors():
    assert G.ANCHOR["reb"] is None and G.ANCHOR["rot"] == "reb" and G.ANCHOR["t_rot"] == "truth"
    for p in ("mag", "phase", "low", "mid", "high", "onset", "sustain", "half", "noise"):
        assert G.ANCHOR[p] == "rot"
    assert G.ANCHOR["dep_eq"] == "reb" and G.ANCHOR["dep_rot"] == "reb"
    assert set(G.ANCHOR) == set(G.PROBES)


# --- scoring -----------------------------------------------------------------------------------------

class FakeJudge:
    def __init__(self, refuse_own=False):
        self.calls, self.refuse_own = [], refuse_own

    def __call__(self, rec, y, mask, lag, a, b):
        self.calls.append((id(mask), lag))
        if self.refuse_own and len(self.calls) % 2 == 1:
            return None, "the DI pauses"
        return 1.0 + lag * 1e-3, None


def test_score_one_probe_configs():
    sig = {"di": np.ones(10), "measure": np.zeros(10), "reference": np.ones(10) * 2}
    j = FakeJudge()
    out = G.score_one(np.ones(10), "mag", sig, -40, j)
    assert set(out) == {"decl", "own"}
    decl = j.calls[:2]
    assert all(m == id(sig["measure"]) and lag == -40 for m, lag in decl)       # the truth's mask and lag
    own = j.calls[2:]
    assert all(m == id(sig["di"]) and lag == -40 for m, lag in own)


def test_score_one_arm_config_and_fallback():
    sig = {"di": np.ones(10), "reference": np.ones(10) * 2}
    j = FakeJudge(refuse_own=True)
    out = G.score_one(np.ones(10), "arm_rank", sig, -40, j)
    assert set(out) == {"decl"}
    assert all(lag == G.OBJ_LAG for _, lag in j.calls)                          # 1b's matched lag
    assert all(math.isfinite(v) for v in out["decl"].values())                  # the fallback answered


# --- rules -------------------------------------------------------------------------------------------

def _c(m, half):
    return {"band_weighted_mean": m, "lo90": m - half, "hi90": m + half}


def test_extension_rule_uses_projected_narrowing():
    assert G.extends(_c(0.10, 0.11), ratio=0.86)            # 0.10 > 0.86·0.11
    assert not G.extends(_c(0.05, 0.11), ratio=0.86)        # wouldn't exclude 0 even narrowed
    assert not G.extends(_c(0.20, 0.11), ratio=0.86)        # already decided
    assert not G.extends(_c(-0.10, 0.11), ratio=0.86)       # negative
    assert not G.extends(_c(0.10, 0.11), ratio=None)


def test_r2_list_adds_anchors_and_family_members():
    contr = {"mag": _c(0.10, 0.11), "phase": _c(-0.3, 0.1), "dep_eq": _c(0.0, 0.1)}
    assert G.r2_list(contr, {}, 0.86) == ["reb", "rot", "mag"]
    fam = {"onset-sustain": _c(-0.10, 0.11)}               # sustain beats onset, undecided but projected decided
    assert G.r2_list({}, fam, 0.86) == ["reb", "rot", "onset", "sustain"]
    assert G.r2_list({"t_rot": _c(0.10, 0.11)}, {}, 0.86) == ["t_rot"]


def test_tr2_due():
    assert G.tr2_due(_c(0.10, 0.11), 0.86)
    assert not G.tr2_due(_c(-0.10, 0.11), 0.86)


# --- the queue gates ------------------------------------------------------------------------------------

LOG_OLD = "2026-10-16 10:00 start pid 1, commit a\n2026-10-16 15:00 all done: report-D.json, report-F.json\n"


def test_gates_read_only_the_current_run():
    running = LOG_OLD + "2026-10-17 20:00 start pid 2, commit b\n2026-10-17 20:01 lane A: pid 3\n"
    assert not G.lane_a_done(running) and not G.lane_a_failed(running)
    assert not G.mega_ended([], running)
    assert G.lane_a_done(running + "x lane A done: ok\n")
    assert not G.lane_a_done(LOG_OLD + "x lane A done: old\n" + "y start pid 2\n")    # an earlier run's line
    for bad in ("x DECIDE-X FAILED\n", "x LANE A FAILED (exit 12; see the lane logs): stage F will not run\n"):
        assert G.lane_a_failed(running + bad) and not G.lane_a_done(running + bad)


def test_terminal_lines():
    run = "s start pid 2, commit b\n"
    for line in ("all done: report-D.json", "stage F not started (lane A failed)", "STAGE F: a shard failed",
                 "REPORT F FAILED", "DECIDE-X FAILED"):
        assert G.mega_ended([], run + f"t {line}\n"), line
    for line in ("STAGE D: a shard failed (see searchD-*.log)", "REPORT D FAILED", "REBUILD X FAILED: arm X"):
        assert not G.mega_ended([], run + f"t {line}\n"), line


def test_mega_processes_block_and_vanish():
    run = "s start pid 2, commit b\nt all done\n"
    ps = [(5, "/x/.venv/bin/python -u -m learn.arm_a_mega53 report --stage F")]
    assert not G.mega_ended(ps, run)
    assert G.mega_ended([(6, "zsh")], run)
    gone = "s start pid 2, commit b\nt stage D shard 2: 9\n"
    assert G.mega_vanished([], gone) and not G.mega_vanished(ps, gone)
    assert not G.mega_vanished([], "")                               # never started: not an alert


def test_render_count_sees_every_render_job():
    ps = [(1, "/v/bin/python -m learn.arm_a_mega53 search --stage D --shard 0/3"),
          (2, "/v/bin/python -m learn.rebuild_gap render --stage r1 --shard 1/3"),
          (3, "/v/bin/python -m learn.local_objective render --di x --shard 0/3"),
          (4, "/v/bin/python -m learn.rebuild_gap report --stage r1"),
          (5, "zsh -c python -m learn.rebuild_gap render")]
    assert G.render_count(ps) == 3
    assert any("rebuild_gap" in p for p in LO.RENDERS)                # other jobs' caps count ours


def test_within_part_assoc_band_weighted():
    from learn import rebuild_gap as G
    table = []
    for slug, band in (("a", "b1"), ("b", "b2"), ("c", "b3")):
        for i in range(5):
            table.append({"slug": slug, "band": band, "m": float(i), "fidelity": float(i) * 0.1})
    out = G.within_part_assoc(table, "m")
    assert out["bands"] == 3 and abs(out["band_weighted_mean"] - 1.0) < 1e-9


def test_tr2_due_is_plain_bool():
    import json
    from learn import rebuild_gap as G
    row = {"band_weighted_mean": 0.01, "lo90": -0.001, "hi90": 0.02, "bands": 14}
    v = G.tr2_due(row, 0.95)
    assert type(v) is bool
    json.dumps({"tr2_due": v})


def test_renders_used_counts_warm_ups_once_and_splits_stages(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(G, "OUT", tmp_path)

    def put(rel, obj):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj))

    # A cell's `renders` already includes its warm-up (49 = 48 settings + 1); a resumed cell has
    # two warm-ups and 50 renders. `warm_ups` must not be added again.
    put("renders/mag/p00/PR12.json", {"probe": "mag", "renders": 49, "warm_ups": 1})
    put("renders/mag/p01/AC20.json", {"probe": "mag", "renders": 50, "warm_ups": 2})
    put("renders/dep_rot/p02/SW50R.json", {"probe": "dep_rot", "renders": 0, "warm_ups": 0,
                                           "status": "same_as_reb"})
    put("renders/arm_rank/p00/PR12.json", {"probe": "arm_rank", "renders": 49, "warm_ups": 1})
    put("comparator/probe/p00-PR12.json", {})
    put("comparator/probe/p01-AC20.json", {})
    put("comparator/arm/p00-PR12.json", {})
    put("rotation/p00.json", {"renders": 9})
    u = G.renders_used()
    assert u["by_probe"] == {"mag": 99, "dep_rot": 0, "arm_rank": 49}
    assert u["comparator"] == 6 and u["rotation_choice"] == 9
    assert u["by_stage"] == {"r": 99 + 4 + 9, "tr": 49 + 2}
    assert u["total"] == 99 + 49 + 6 + 9
