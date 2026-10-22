"""The real-mix test (`learn/real_mix_test.py`, docs/real-mix-test-plan.md, amendment 1): the trusted
list (refused without it), the run set and counts, the checks (provenance, C′ networks, the
rebuild lag, the logged lag), the machine gates, the repeat check, a group's priming, the "as mixed"
fit, the units and the report's contrasts. Fakes and synthetic signals only."""

import json
import math
import random
import types

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import arm_a_levers as L  # noqa: E402
from learn import arm_a_mega53 as A  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import mix_previews as MP  # noqa: E402
from learn import real_mix_test as M  # noqa: E402

PY = "/x/.venv/bin/python"


# --- the parts ---------------------------------------------------------------------------------------

def test_parts_are_the_plans_17_in_9_bands():
    assert len(M.PARTS) == 17 and len({A.pool_band(s) for s in M.PARTS}) == 9
    assert set(M.UNMASTERED) <= set(M.PARTS) and len(M.UNMASTERED) == 6
    assert len({A.pool_band(s) for s in M.UNMASTERED}) == 4
    assert len(M.LAGGED) == 6 and len(M.FLIPPED) == 8 and len(M.XLANCE_FAILURES) == 2
    assert set(M.LAGGED) | set(M.FLIPPED) | set(M.XLANCE_FAILURES) | set(M.NO_COHERENT_GUITAR) <= set(M.PARTS)
    assert M.kinds("cambridge-Signs-ElecGtr3") == ("remix_mastered", "unmastered")
    assert M.kinds("cambridge-magilla-elecgtr1") == ("preview_mastered",)
    assert not any(s.startswith("telefunken-") for s in M.PARTS)


def test_constants_are_the_plans():
    assert M.REPEAT_SEED == 20261092 and M.REPEAT_N == 6 and M.REPEAT_TOL == 1e-3
    assert M.LAG_TOL == 3 and M.MAX_LAG == 4800 and M.IDENTITY_TOL == 1e-6
    assert M.COH_MIN == 0.1 and M.COH_BAND == (200.0, 5000.0) and M.CAP == 6_300
    assert A.PER_DIRECTION == 55 and LO.DISK_GUARD_GB == 31.0


# --- the trusted list ----------------------------------------------------------------------------------

def test_parse_trusted_json_and_text():
    j = json.dumps({"trusted": ["cambridge-magilla-elecgtr1", "cambridge-femme-elecgtr5:B"], "note": "review 1"})
    assert M.parse_trusted(j, "t.json") == [("cambridge-magilla-elecgtr1", None), ("cambridge-femme-elecgtr5", "B")]
    assert M.parse_trusted('["a", "b:A"]') == [("a", None), ("b", "A")]
    txt = "# trusted after review 1\ncambridge-magilla-elecgtr1   # clean\n\n  cambridge-femme-elecgtr5:A\n"
    assert M.parse_trusted(txt, "t.txt") == [("cambridge-magilla-elecgtr1", None), ("cambridge-femme-elecgtr5", "A")]
    for bad in ('{"parts": ["a"]}', '{"trusted": "a"}', '[1, 2]', "a:C", ":A", "{not json"):
        with pytest.raises(ValueError):
            M.parse_trusted(bad)


def test_every_command_refuses_without_a_trusted_list(tmp_path):
    with pytest.raises(SystemExit):
        M.read_trusted(None)
    with pytest.raises(SystemExit):
        M.read_trusted(tmp_path / "missing.json")
    (tmp_path / "bad.json").write_text('{"parts": []}')
    with pytest.raises(SystemExit):
        M.read_trusted(tmp_path / "bad.json")
    for cmd in ("inputs", "separate", "rebuild", "predict", "render", "smoke", "as-mixed", "report"):
        with pytest.raises(SystemExit):
            M.main([cmd])


def test_run_set_keeps_the_plans_parts_and_halves():
    entries = [("cambridge-magilla-elecgtr1", None), ("cambridge-femme-elecgtr5", "B"), ("telefunken-She's_Gone-GTR", None),
               ("cambridge-Drag_Me_Down-ElecGtr4", "A"), ("cambridge-femme-elecgtr5", "B")]
    run, outside = M.run_set(entries)
    assert run == {"cambridge-femme-elecgtr5": ["B"], "cambridge-magilla-elecgtr1": ["A", "B"]}
    assert outside == ["cambridge-Drag_Me_Down-ElecGtr4:A", "telefunken-She's_Gone-GTR"]
    dirs = M.run_dirs(run)
    assert len(dirs) == 3 * 1 + 3 * 2
    assert all(h == "B" for s, _, _, h in dirs if s == "cambridge-femme-elecgtr5")
    assert {(sh, h) for _, _, sh, h in dirs} <= set(K.DIRECTIONS)


def test_expected_renders_are_the_plans_on_all_17():
    dirs = M.run_dirs({s: ["A", "B"] for s in M.PARTS})
    e = M.expected_renders(dirs)
    assert len(dirs) == 102 and len(A.groups(dirs)) == 51
    assert e == {"priming": 51, "arm_A": 5_610, "D_real": 102, "D_unmastered": 36, "repeat_check": 12, "total": 5_811}
    assert e["total"] <= M.CAP


def test_repeat_groups_are_seeded():
    gs = A.groups(M.run_dirs({s: ["A", "B"] for s in M.PARTS}))
    r = M.repeat_groups(gs)
    assert r == sorted(random.Random(20261092).sample(sorted(gs), 6)) and r == M.repeat_groups(list(reversed(gs)))
    assert M.repeat_groups(gs[:4]) == sorted(gs[:4])


def test_state_refuses_another_trusted_list(tmp_path):
    t1, t2 = tmp_path / "t1.txt", tmp_path / "t2.txt"
    t1.write_text("cambridge-magilla-elecgtr1\n")
    t2.write_text("cambridge-femme-elecgtr5\n")
    args = types.SimpleNamespace(out=str(tmp_path / "run"), trusted=str(t1))
    with pytest.raises(SystemExit):
        M.state(args)                                                    # no inputs.json yet
    M._save(tmp_path / "run" / "inputs.json", {"ok": True, "trusted": {"sha256": LO.file_sha256(t1)}})
    root, rec = M.state(args)
    assert root == tmp_path / "run" and rec["ok"]
    with pytest.raises(SystemExit):
        M.state(types.SimpleNamespace(out=str(tmp_path / "run"), trusted=str(t2)))
    M._save(tmp_path / "run" / "inputs.json", {"ok": False, "problems": {"x": 1}, "trusted": {"sha256": LO.file_sha256(t1)}})
    with pytest.raises(SystemExit):
        M.state(args)


def test_inputs_limit_needs_a_scratch_out(tmp_path):
    t = tmp_path / "t.txt"
    t.write_text("cambridge-magilla-elecgtr1\n")
    with pytest.raises(SystemExit):
        M.cmd_inputs(types.SimpleNamespace(out=None, trusted=str(t), limit=1))
    t.write_text("telefunken-She's_Gone-GTR\n")
    with pytest.raises(SystemExit):                                      # no trusted part of the 17
        M.cmd_inputs(types.SimpleNamespace(out=str(tmp_path / "o"), trusted=str(t), limit=None))


# --- the checks -------------------------------------------------------------------------------------------

def test_provenance_problems():
    run = {"model": "mega53", "stem": "electric-guitar", "pruned": True, "threads": 4, "device": "cpu",
           "inference": {"chunk_size": 882000, "num_overlap": 2},
           "provenance": {"commit": "ea7e", "files": [{"sha256": "c628"}, {"sha256": "7e19"}]}}
    assert M.provenance_problems(run, dict(run, pruned_by_identity=True)) == []
    assert M.provenance_problems(dict(run, threads=2), run)
    assert M.provenance_problems(dict(run, provenance={"commit": "x", "files": []}), run)
    assert M.provenance_problems(None, run)


def test_network_checks():
    log = {"a": {"network": "/n/f0.pt", "network_sha256": "h0"}, "b": {"network": "/n/f1.pt", "network_sha256": "h1"}}
    path = {"a": "/n/f0.pt", "b": "/n/f2.pt"}
    sha = {"/n/f0.pt": "h0", "/n/f2.pt": "h1"}
    bad = M.network_problems(["a", "b", "c"], log, lambda s: path[s] if s in path else "/n/x", lambda p: sha.get(str(p)))
    assert set(bad) == {"b", "c"}
    assert M.network_problems(["a"], log, lambda s: "/n/f0.pt", lambda p: "other")
    real = {"a": dict(log["a"]), "b": {"network": "/n/f1.pt", "network_sha256": "zz"}}
    assert set(M.used_network_problems(real, log, ["a", "b"])) == {"b"}


def test_rebuild_lag_check_stops_or_logs():
    unity = {"p": {"gcc_vs_source": 0}, "q": {"gcc_vs_source": -54}, "cambridge-Passing_Ships-ElecGtr4": {"gcc_vs_source": -69},
             "r": {"gcc_vs_source": 0}}
    real = {"p": {"gcc_vs_source": 2}, "q": {"gcc_vs_source": 0}, "cambridge-Passing_Ships-ElecGtr4": {"gcc_vs_source": 40}}
    stop, logged = M.rebuild_lag_problems(real, unity, ["p", "q", "cambridge-Passing_Ships-ElecGtr4", "r"])
    assert set(stop) == {"q", "r"} and set(logged) == {"cambridge-Passing_Ships-ElecGtr4"}
    stop, _ = M.rebuild_lag_problems({"p": {"gcc_vs_source": -3}}, unity, ["p"])
    assert not stop


def test_logged_lag_and_the_mix_shift():
    rng = np.random.default_rng(1)
    a = rng.standard_normal(48_000)
    c = -0.5 * MP.shift(a, 7)                                             # the real mix delays and flips it
    real, unity = M.logged_lag(c, a), M.logged_lag(a, a)
    assert real["lag"] == -7 and real["r"] < 0 and real["snr_db"] > 30
    assert unity["lag"] == 0 and unity["r"] > 0
    delay, flipped = M.mix_shift(real, unity)
    assert delay == 7 and flipped
    assert np.allclose(-0.5 * MP.shift(a, delay), c)


def test_stored_problems():
    dirs = M.run_dirs({"p": ["A", "B"]})
    ok = M.stored_problems(dirs, lambda s, a: True, lambda s, a, sh: True, lambda s, a: True, lambda s: True)
    assert ok == []
    bad = M.stored_problems(dirs, lambda s, a: a != "pr12", lambda s, a, sh: sh == "A", lambda s, a: True, lambda s: False)
    assert "stage F S p pr12" in bad and sum(x.startswith("stage F M p") for x in bad) == 3
    assert "stage F Mega-53 rebuild p" in bad


# --- the machine ----------------------------------------------------------------------------------------

def test_render_gate_counts_jobs_and_servers():
    jobs = [(1, f"{PY} -m learn.real_mix_test render --trusted t --shard 0/3"),
            (2, f"{PY} -m learn.direct_stems render --shard 0/3")]
    assert M.render_blocker(jobs) is None
    three = jobs + [(3, f"{PY} -m learn.arm_a_mega53 search --stage F --shard 1/3")]
    assert "3 render processes" in M.render_blocker(three)
    assert M.render_blocker(three, own={3}) is None
    servers = [(10 + i, "/tmp/au-bounded-x/au_render_server_bounded --x") for i in range(3)]
    assert "render servers" in M.render_blocker(servers)
    assert M.render_blocker(servers, servers=False) is None
    beside = jobs + [(9, f"{PY} -m learn.real_mix_test separate --trusted t --device cpu")]
    assert "beside a separation" in M.render_blocker(beside)               # a separation lowers the cap to 2


def test_regexes_count_this_tests_renders_and_separation():
    import re

    for cmd in ("render --trusted t --shard 0/3", "smoke --trusted t --out x"):
        assert any(re.search(p, f"python -m learn.real_mix_test {cmd}") for p in LO.RENDERS), cmd
    for cmd in ("inputs", "predict", "report", "as-mixed", "rebuild", "separate"):
        assert not any(re.search(p, f"python -m learn.real_mix_test {cmd} --trusted t") for p in LO.RENDERS), cmd
    assert A._matches(f"{PY} -m learn.real_mix_test separate --trusted t --device cpu", A.SEPARATIONS)
    assert not A._matches(f"{PY} -m learn.real_mix_test rebuild --trusted t", A.SEPARATIONS)
    assert A._matches(f"{PY} -m learn.real_mix_test render --trusted t", A.RENDERS)


def test_separation_waits_for_an_idle_renderer_and_a_free_gpu():
    idle = [(5, "/bin/zsh")]
    assert M.sep_blockers(idle, set(), 20.0, "cpu") == []
    assert M.sep_blockers(idle, set(), 2.0, "cpu")                       # memory
    busy = [(1, f"{PY} -m learn.direct_stems render --shard 0/3")]
    assert any("not idle" in b for b in M.sep_blockers(busy, set(), 20.0, "cpu"))
    srv = [(2, "/tmp/d/au_render_server_bounded")]
    assert any("not idle" in b for b in M.sep_blockers(srv, set(), 20.0, "cpu"))
    gpu = [(3, f"{PY} -m learn.direct_stems train --arm Dstem --n full --device mps")]
    assert M.sep_blockers(gpu, set(), 20.0, "cpu") == [] and any("MPS" in b for b in M.sep_blockers(gpu, set(), 20.0, "mps"))
    assert M.mps_users(gpu, own={3}) == []


# --- renders --------------------------------------------------------------------------------------------

class FakeRR:
    def __init__(self):
        self.count, self.calls = 0, []

    def render(self, di32, sel, x):
        self.count += 1
        self.calls.append((di32, x))
        return np.full(10, 0.1)


def ctx_of(lag=5):
    di = np.full(10, 3.0, np.float32)
    return {"part": {"judge_lag": lag}, "sel": "sel", "S": {"s": 1}, "di": di.astype(np.float64), "di32": di, "ref": np.ones(10)}


def test_repeat_check_primes_and_stops_on_a_move():
    items = [("p|pr12", ctx_of(), {"A": 2.0, "B": 3.0}), ("q|ac20", ctx_of(), {"A": 2.0, "B": 3.0})]
    rr = FakeRR()
    r = M.repeat_check(rr, items, lambda ref, y, di, lag: {"A": 2.0, "B": 3.0 * math.exp(5e-4)})
    assert r["status"] == "done" and r["renders"] == 4 and r["primes"] == 2 and r["worst"] == pytest.approx(5e-4)
    r = M.repeat_check(FakeRR(), items, lambda ref, y, di, lag: {"A": 2.0 * math.exp(2e-3), "B": 3.0})
    assert r["status"] == "stopped"


def test_a_group_primes_once_through_the_rebuild_then_renders_d():
    rr, ran, kept, saved = FakeRR(), [], [], []
    ctx, rb32 = ctx_of(), np.full(10, 7.0, np.float32)
    rec = {"primes": 0, "renders": 0, "judge": {}, "status": "running"}
    dirs = [("p", "pr12", "A", "B"), ("p", "pr12", "B", "A")]
    d_todo = [("D_real", "A", {"x": 1}), ("D_real", "B", {"x": 2}), ("D_unm", "A", {"x": 3}), ("D_unm", "B", {"x": 4})]
    out = M.render_group(rr, ctx, rb32, dirs, d_todo, rec, run_dir=ran.append,
                         judge=lambda ref, y, di, lag: {"A": 1.0, "B": float(lag)},
                         keep=lambda a, s, y: kept.append((a, s)), save=lambda r: saved.append(dict(r)))
    assert ran == dirs and out["status"] == "done" and out["primes"] == 1 and out["renders"] == 5
    assert rr.calls[0][0] is rb32 and rr.calls[0][1] == ctx["S"]                 # the priming render: the rebuild at S
    assert all(c[0] is ctx["di32"] for c in rr.calls[1:])                        # D through the measure DI
    assert [c[1] for c in rr.calls[1:]] == [x for _, _, x in d_todo]
    assert set(out["judge"]) == {"D_real|A", "D_real|B", "D_unm|A", "D_unm|B"} and out["judge"]["D_real|A"]["B"] == 5.0
    assert len(kept) == 4


def test_a_resumed_group_primes_the_measure_di_and_skips_done_renders():
    rr = FakeRR()
    ctx = ctx_of()
    rec = {"primes": 1, "renders": 3, "judge": {"D_real|A": {"A": 1.0, "B": 1.0}}, "status": "running"}
    out = M.render_group(rr, ctx, np.zeros(10, np.float32), [], [("D_real", "A", {"x": 1}), ("D_real", "B", {"x": 2})],
                         rec, run_dir=None, judge=lambda *a: {"A": 1.0, "B": 2.0}, keep=lambda *a: None,
                         save=lambda r: None)
    assert rr.count == 2 and rr.calls[0] == (ctx["di32"], ctx["S"]) and rr.calls[1][1] == {"x": 2}
    assert out["primes"] == 2 and out["renders"] == 5 and out["status"] == "done"


def test_spent_left_and_the_priming_count(tmp_path):
    run = {"cambridge-magilla-elecgtr1": ["A", "B"], "cambridge-femme-elecgtr5": ["A", "B"]}
    dirs = M.run_dirs(run)
    reps = M.repeat_groups(A.groups(dirs))
    n, kept = M.left(tmp_path, dirs, reps)
    assert n == M.expected_renders(dirs)["total"] and kept == len(dirs) * 2 + 6   # femme has an unmastered mix
    M._save(M.m_path(tmp_path, "cambridge-magilla-elecgtr1", "pr12", "A"), {"status": "done", "renders": 55})
    M._save(M.group_path(tmp_path, "cambridge-femme-elecgtr5", "ac20"),
            {"status": "done", "renders": 7, "primes": 1, "judge": {}})
    M._save(tmp_path / "repeat.json", {"status": "done", "renders": 12, "primes": 6})
    assert M.spent(tmp_path) == 55 + 7 + 12
    n2, _ = M.left(tmp_path, dirs, reps)
    assert n2 == n - 55 - (2 * 55 + 1 + 4) - 12
    pc = M.primes_check(tmp_path, dirs, reps)
    assert pc["expected"] == 6 + 6 and pc["recorded"] == 1 + 6 and len(pc["groups_not_one"]) == 5


# --- "as mixed" -----------------------------------------------------------------------------------------

def lowpass(x, pole=0.9):
    from scipy import signal

    return signal.lfilter([1.0], [1.0, -pole], x)                       # one peak at tap 0: a clean lag


def test_the_mix_fit_finds_lag_and_eq_and_the_unity_control_is_flat():
    rng = np.random.default_rng(3)
    n = 3 * M.SR
    ref = rng.standard_normal(n)
    mix = -0.5 * MP.shift(lowpass(ref), 37) + 0.3 * rng.standard_normal(n)
    f = M.fit_mix(ref, mix, 0, n)
    assert f["lag"] == 37 and f["r"] < 0 and f["coherence"] > M.COH_MIN
    g = dict(zip(f["centres_hz"], f["gains_db"]))
    lo, hi = [v for c, v in g.items() if c < 500], [v for c, v in g.items() if c > 4000]
    assert min(lo) > max(hi) + 6                                          # the low-pass shows in the fitted EQ
    u = M.fit_mix(ref, ref + 0.3 * rng.standard_normal(n), 0, n)
    assert u["lag"] == 0 and M.flatness_db(u) < 0.5
    t = M.as_mixed_target(ref, f)
    assert abs(M.logged_lag(t, ref)["lag"]) == 37


def test_apply_eq():
    x = np.random.default_rng(4).standard_normal(4800)
    cen = M.third_octave_centres()
    assert np.allclose(M.apply_eq(x, cen, [0.0] * len(cen)), x)
    assert np.allclose(M.apply_eq(x, cen, [20 * math.log10(2)] * len(cen)), 2 * x)
    assert np.allclose(M.apply_eq(x, cen, [None] * len(cen)), x)
    assert cen[0] >= M.EQ_RANGE[0] and cen[-1] <= M.EQ_RANGE[1] and len(cen) == 25


def test_excluded_parts_by_the_declared_coherence():
    fits = {"p|A": {"coherence": 0.2}, "p|B": {"coherence": 0.05}, "q|A": {"coherence": 0.1}, "r|B": {"coherence": math.nan}}
    assert M.excluded_parts(fits) == ["p", "r"]


# --- units and the report -------------------------------------------------------------------------------

BANDS = [f"b{i}" for i in range(9)]


def toy_units(pen_m=0.05, pen_d=-0.02, seed=0):
    rng = random.Random(seed)
    dirs, vals, parts = [], {}, {}
    for i, b in enumerate(BANDS):
        slug = f"{b}-p"
        parts[slug] = {"band": b, "gain_class": "clean" if i % 2 else "crunch"}
        for amp in K.AMPS:
            for sh, h in K.DIRECTIONS:
                dirs.append((slug, amp, sh, h))
                s = 2 + rng.random()
                mu, du = s * math.exp(-0.05), s * math.exp(-0.03)
                vals[(slug, amp, sh)] = {"S": s, "M_unity": mu, "D_unity": du,
                                         "M_real": mu * math.exp(pen_m + 0.01 * rng.gauss(0, 1)),
                                         "D_real": du * math.exp(pen_d + 0.01 * rng.gauss(0, 1)),
                                         "D_unm": du * math.exp(0.01)}
    return dirs, parts, vals


def test_contrasts_read_the_paired_penalty():
    dirs, parts, vals = toy_units()
    value_of = lambda arm, u: vals[(u["slug"], u["amp"], u["search"])].get(arm)  # noqa: E731
    units = M.make_units(dirs, parts.get, value_of, M.FIXED)
    rep = M.report_from_units(units, M.make_units(dirs, parts.get, value_of, M.FIXED + ("D_unm",)), dirs)
    m, d = M._all(rep["contrasts"]["M_penalty"]), M._all(rep["contrasts"]["D_penalty"])
    assert m["band_weighted_mean"] == pytest.approx(0.05, abs=0.01) and m["bands"] == 9
    assert d["band_weighted_mean"] == pytest.approx(-0.02, abs=0.01)
    assert rep["readings"]["M_penalty"].startswith("real mixes hurt")
    assert rep["readings"]["D_penalty"].startswith("real mixes help")
    assert M._all(rep["contrasts"]["M_real_minus_S"])["band_weighted_mean"] == pytest.approx(0.0, abs=0.01)
    assert rep["complete"]["missing_arm_results"] == 0
    assert M._all(rep["unmastered"]["D_unmastered_minus_D_unity"])["band_weighted_mean"] == pytest.approx(0.01)
    c = rep["contrasts"]["M_penalty"]["rows"]["all"]
    assert set(c["per_amp"]) == set(K.AMPS) and set(c["per_class"]) == {"clean", "crunch"}
    assert len(c["all"]["leave_one_band_out"]) == 9 and "part_weighted" in c


def test_a_missing_or_refused_arm_drops_the_direction_everywhere():
    dirs, parts, vals = toy_units()
    vals[(dirs[0][0], dirs[0][1], dirs[0][2])]["D_real"] = math.inf
    del vals[(dirs[1][0], dirs[1][1], dirs[1][2])]["M_real"]
    units = M.make_units(dirs, parts.get, lambda arm, u: vals[(u["slug"], u["amp"], u["search"])].get(arm), M.FIXED)
    c = M.contrast(units, "M_real", "M_unity")
    assert c["directions"] == len(dirs) - 2 and c["missing"] == 1 and len(c["dropped"]) == 1


def test_row_filters_are_the_plans_subsets():
    f = M.row_filters()
    assert set(f) == set(M.ROWS)
    u = {"slug": "cambridge-wickerman-elecgtr1"}
    assert f["lagged"](u) and f["flipped"](u) and not f["xlance_failures"](u)
    assert f["xlance_failures"]({"slug": "cambridge-colour-me-red-elecgtr02"})


def test_penalty_reading():
    assert M.penalty_reading(None) == "incomplete"
    assert M.penalty_reading({"lo90": 0.01, "hi90": 0.2}).startswith("real mixes hurt")
    assert M.penalty_reading({"lo90": -0.2, "hi90": -0.01}).startswith("real mixes help")
    assert M.penalty_reading({"lo90": -0.1, "hi90": 0.1}).startswith("no penalty shown")


def test_per_part_rows_and_correlations():
    dirs, parts, vals = toy_units()
    units = M.make_units(dirs, parts.get, lambda arm, u: vals[(u["slug"], u["amp"], u["search"])].get(arm), M.FIXED)
    snr = {s: -0.1 * i for i, s in enumerate(sorted(parts))}
    rows, corr = M.per_part(units, snr, {s: 1.0 for s in parts}, {})
    assert len(rows) == 9 and rows["b0-p"]["M_penalty"] == pytest.approx(0.05, abs=0.02)
    assert corr["M_penalty~stem_snr_change_db"]["parts"] == 9
    assert corr["D_penalty~d_input_level_shift_lu"]["pearson_r"] is None              # no spread: no r


def test_unit_values_fall_back_to_s_and_count_refusals(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "s_path", lambda s, a: tmp_path / "S" / s / f"{a}.json")
    monkeypatch.setattr(A, "result_path", lambda st, arm, s, a, sh: tmp_path / "FM" / s / a / f"{sh}.json")
    u = {"slug": "p", "amp": "pr12", "search": "A", "held": "B"}
    M._save(A.s_path("p", "pr12"), {"status": "done", "judge": {"A": 4.0, "B": 5.0}})
    M._save(A.result_path("F", "M", "p", "pr12", "A"), {"status": "done", "fallback": "silent", "judge_shrunk": {"B": 1.0}})
    M._save(M.m_path(tmp_path, "p", "pr12", "A"), {"status": "done", "fallback": None, "judge_shrunk": {"B": 3.0}})
    M._save(M.group_path(tmp_path, "p", "pr12"), {"status": "done", "judge": {"D_real|A": {"A": 1.0, "B": math.inf}}})
    s4 = {"status": "done", "judge": {"D|A": {"A": 1.0, "B": 2.5}}}
    value_of, refused = M.unit_values(tmp_path, lambda s, a: s4)
    assert value_of("S", u) == 5.0 and value_of("M_unity", u) == 5.0 and value_of("M_real", u) == 3.0
    assert value_of("D_unity", u) == 2.5 and value_of("D_real", u) == 5.0 and refused["D_real"] == 1
    assert value_of("D_unm", u) is None


def test_knob_movement_halves_under_shrink():
    from tests.test_arm_a_mega53 import AMP, DIMS, S0, preset

    x = preset(7)
    shr = L.shrink(DIMS, S0, x, 0.5)
    assert M.knob_movement(DIMS, shr, S0) == pytest.approx(0.5 * M.knob_movement(DIMS, x, S0), rel=1e-3)
    assert M.knob_movement(DIMS, S0, S0) == 0.0 and AMP in K.AMPS


def test_bw_rows():
    r = M.bw_rows({"cambridge-magilla-elecgtr1": [0.1, 0.3], "cambridge-femme-elecgtr5": [0.0]}, A.pool_band)
    assert r["band_weighted_mean"] == pytest.approx(0.1) and r["bands"] == 2


# --- the ledger -----------------------------------------------------------------------------------------

def test_the_ledger_has_this_tests_entry():
    led = json.loads((M.PLUGIN_ROOT / "docs/dev-test-ledger.json").read_text())
    e = [t for t in led["tests"] if t["test_id"] == "real-mix-test"]
    assert len(e) == 1
    e = e[0]
    assert e["plan"] == "docs/real-mix-test-plan.md" and sorted(e["parts"]["candidates"]) == sorted(M.PARTS)
    assert e["held_out"] == "none touched" and "outcome" not in e
