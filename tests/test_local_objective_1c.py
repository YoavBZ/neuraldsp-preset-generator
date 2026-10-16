"""Experiment 1c (`learn/local_objective_1c.py` and its DIs in `learn/local_objective.py`;
docs/local-objective-plan.md, amendment 3): the separator DIs and score views, the context plan, the
memory gate, the separation checks, the share of 1b's gain (Fieller) and the reading. Fakes, plus one
check that the stored step-3 contexts resolve for all 24 parts (zero separations, zero renders)."""

import json
import math
import random

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import knob_ceiling as K  # noqa: E402
from learn import local_objective as M  # noqa: E402
from learn import local_objective_1c as C  # noqa: E402

DI = M.SEP_DI["mega53"]
VIEW = "cprime@mega53"


def fake_judge(log):
    def aligned(rec, y, mask, lag, a, b):
        log.append((rec, y, mask if isinstance(mask, str) else "array", lag, a))
        if isinstance(mask, str) and mask == "silent":
            return None, "the DI plays in too few frames"
        return 1.0 + 0.001 * lag + (0.5 if rec == "mega" else 0.0), None
    return aligned


# --- the DIs, views and scoring -------------------------------------------------------------------------

def test_sep_dis_configs_and_lags():
    assert M.SEP_DI == {"mega53": "cprime_mega53", "blend": "cprime_blend"}
    assert DI in M.REBUILT and DI in M.NO_STORED and M.REBUILD_SOURCE[DI] == "mega53"
    assert M.REBUILD_DIR[DI] == "rebuilt-mega53"
    assert M.configs(DI) == [(DI, "mega53", "native", "own"), (DI, "mega53", "gcc", "own"), (DI, "stem", "native", "own")]
    assert M.native_config(DI) == (DI, "mega53", "native", "own")
    assert M.lag_value("native", DI, 914) == -52 and M.lag_value("gcc", DI, 914, gcc=-53) == 1
    assert M.render_di(VIEW) == "cprime" and M.render_di(DI) == DI and M.render_di("measure") == "measure"
    assert M.configs(VIEW) == [("cprime", "mega53", "native", "own")]
    assert M.configs(M.MATCHED_DI) == [M.MATCHED, M.MATCHED_GCC]      # 1b unchanged
    assert len(M.configs("cprime")) == 16 and len(M.configs("measure")) == 12


def test_score_render_sep_di_and_view_keep_the_rebuild_semantics(monkeypatch):
    import numpy as np

    monkeypatch.setattr(M, "in_di_time", lambda rec, lag: np.zeros(3))
    log = []
    aligned = fake_judge(log)
    sig = {"di": "silent", "stem": "stem", "reference": "ref", "mega53": "mega"}
    out, fb = M.score_render("y", DI, sig, 914, aligned, gcc=-53)
    assert set(out) == {M.cname(c) for c in M.configs(DI)}
    assert fb[f"{DI}|mega53|native|own"] == 2                          # the C′ fallback applies
    assert out[f"{DI}|mega53|native|own"]["A"] == pytest.approx(1.0 - 0.052 + 0.5)
    assert out[f"{DI}|mega53|gcc|own"]["A"] == pytest.approx(1.0 + 0.001 + 0.5)
    assert out[f"{DI}|stem|native|own"]["A"] == pytest.approx(1.0 - 0.052)
    log.clear()
    out, fb = M.score_render("y", VIEW, sig, 914, aligned)
    assert list(out) == ["cprime|mega53|native|own"] and fb["cprime|mega53|native|own"] == 2
    assert {e[0] for e in log} == {"mega"} and {e[3] for e in log} == {-52}   # C′'s lag, not judge_lag


def test_render_checks_repeat_of_S_for_a_separator_rebuild(monkeypatch):
    calls = []

    def fake_score(y, di, sig, jl, aligned, gcc=None, only=None):
        calls.append(tuple(only))
        return {M.cname(next(iter(only))): {"A": y, "B": y}}, {}
    monkeypatch.setattr(M, "score_render", fake_score)
    s = {"source": "S", "true_stored": None, "obj_stored": None}
    out = M.render_checks(s, DI, 2.0, None, -36, None, warm=2.02)
    assert [(w, h) for w, h, _ in out] == [("repeat_S", "A"), ("repeat_S", "B")]
    assert calls[0] == ((DI, "mega53", "native", "own"),)


def test_render_refuses_sep_without_checks_and_views(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "OUT", tmp_path)
    monkeypatch.setattr(M, "load_sigma", lambda: ({"hash": M.SIGMA_HASH}, {}))
    with pytest.raises(SystemExit, match="pre-render checks"):
        M.cmd_render((0, 3), di_name=DI)
    with pytest.raises(SystemExit, match="score view"):
        M.cmd_render((0, 3), di_name=VIEW)
    (tmp_path / "rebuilt-mega53").mkdir()
    (tmp_path / "rebuilt-mega53" / "check.json").write_text(json.dumps({"ok": True}))
    assert M.rebuilds_ok(DI) and not M.rebuilds_ok("cprime_blend") and not M.matched_rebuilds_ok()


def test_part_signals_loads_the_separator_crop_and_rebuild(tmp_path, monkeypatch):
    import numpy as np

    from learn import confirm_run as CR
    from learn import song_settings as SS

    monkeypatch.setattr(M, "OUT", tmp_path)
    monkeypatch.setattr(K, "parts", lambda: {"p": {"crop": tmp_path}})
    monkeypatch.setattr(SS, "stem", lambda slug: np.full(4, 2.0))
    monkeypatch.setattr(SS, "OUT", tmp_path / "ss")
    monkeypatch.setattr(CR, "mono", lambda path: np.full(4, 3.0))
    (tmp_path / "sep" / "mega53" / "crop").mkdir(parents=True)
    np.save(tmp_path / "sep" / "mega53" / "crop" / "p.npy", np.full(4, 5.0, np.float32))
    (tmp_path / "rebuilt-mega53").mkdir()
    np.save(tmp_path / "rebuilt-mega53" / "p.npy", np.full(4, 7.0))
    (tmp_path / "ss" / "rebuilt").mkdir(parents=True)
    np.save(tmp_path / "ss" / "rebuilt" / "p.npy", np.full(4, 1.0))
    sig, _ = M.part_signals("p", DI)
    assert sig["di"][0] == 7.0 and sig["mega53"][0] == 5.0 and sig["mega53"].dtype == np.float64
    assert sig["stem"][0] == 2.0 and sig["reference"][0] == 3.0
    sig, _ = M.part_signals("p", VIEW)
    assert sig["di"][0] == 1.0 and sig["mega53"][0] == 5.0             # the view reads C′'s stem rebuild
    sig, _ = M.part_signals("p", "cprime")
    assert "mega53" not in sig


def test_separation_patterns_hold_renders():
    py = "/x/.venv/bin/python"
    assert M.is_separation(f"{py} -m learn.local_objective_1c separate")
    assert M.is_separation(f"{py} -m learn.separator_screen separate --row mega53")
    assert not M.is_separation(f"{py} -m learn.local_objective_1c report")
    assert not M.is_separation("zsh -c '.venv/bin/python -m learn.local_objective_1c separate'")
    assert M.separating([(1, f"{py} -m learn.local_objective_1c separate"), (2, "vim")], own={3}) == [1]


# --- the context and the memory gate ---------------------------------------------------------------------

def test_stems_root():
    assert str(C.stems_root("/a/set3/stems/htdemucs_6s/p/instrumental_guitar.wav")) == "/a/set3/stems"
    with pytest.raises(ValueError):
        C.stems_root("/a/set3/stems/htdemucs_6s-crop10s/p/instrumental_guitar.wav")


def test_context_plan():
    s3 = {"crop_offset_in_context": 636734, "context_rebuilt_exactly": True,
          "line_up_check": {"crop_file": "mix.wav", "max_abs_diff": 0.0}}
    p = C.context_plan("p", s3, "/w", "/crops/p")
    assert str(p["input"]) == "/w/contexts/p/mix_instrumental.wav" and p["offset"] == 636734
    assert p["kind"] == "context" and str(p["lineup"]) == "/crops/p/mix.wav"
    fb = C.context_plan("p", {**s3, "context_rebuilt_exactly": False}, "/w", "/crops/p")
    assert str(fb["input"]) == "/crops/p/mix.wav" and fb["offset"] == 0 and fb["kind"] == "crop10s_fallback"
    poc = {"crop_offset_in_context": 480000, "line_up_check": {"mix": {}, "mix_instrumental": {}}}
    q = C.context_plan("p", poc, "/w", "/crops/p")
    assert q["offset"] == 480000 and str(q["lineup"]) == "/crops/p/mix_instrumental.wav" and q["kind"] == "context"


def test_available_gb():
    text = ("Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages free:      1000.\n"
            "Pages active:     5000.\nPages inactive:    2000.\nPages speculative:   500.\n")
    assert C.available_gb(text) == pytest.approx(3500 * 16384 / 1e9)
    assert C.available_gb("Pages free: 10.\n") == pytest.approx(10 * 4096 / 1e9)


def test_separation_blockers():
    py = "/x/.venv/bin/python"
    ps = [(10, f"{py} -m learn.local_objective_1c separate"), (11, "vim notes"),
          (12, f"{py} -m learn.ks_extend run --shard 0/3"), (15, "/a/au_render_server --x")]
    assert C.separation_blockers(ps, own={10}, avail_gb=12.0) == []     # amendment 3a: renders don't block
    assert "memory" in C.separation_blockers(ps, own={10}, avail_gb=10.0)[0]
    assert C.separation_blockers(ps, own={10}, avail_gb=None)
    busy = ps + [(13, "/t/demucs-venv/bin/python -u -m learn.song_soundspace train --arm B2 --fold 3"),
                 (14, f"{py} -m learn.separator_screen separate --row mega53")]
    why = C.separation_blockers(busy, own={10}, avail_gb=20.0)
    assert len(why) == 2 and "[13]" in why[0] and "[14]" in why[1]
    assert not C.is_training(f"{py} -m learn.song_soundspace score-targets")
    assert C.is_training(f"{py} -m learn.direc fit --fold 1")


def test_memory_gate_is_keyed_on_pruning():
    assert C.MEM_GATE_GB == C.mem_gate_gb(True) == 11.0 and C.mem_gate_gb(False) == 18.0
    assert C.prune_decision({"identical": True, "max_abs_diff": 0.0})
    assert not C.prune_decision({"identical": False}) and not C.prune_decision(None)


def test_sep_problems():
    assert C.sep_problems(0, 0.0, C.CROP) == [] and C.sep_problems(-3, 5e-7, C.CROP) == []
    assert "GCC" in C.sep_problems(4, 0.0, C.CROP)[0] and "GCC" in C.sep_problems(None, 0.0, C.CROP)[0]
    assert "crop slice" in C.sep_problems(0, 1e-6, C.CROP)[0] and "crop slice" in C.sep_problems(0, None, C.CROP)[0]
    assert "length" in C.sep_problems(0, 0.0, 10)[0]


def test_snr_db():
    import numpy as np

    rng = np.random.default_rng(1)
    r = rng.standard_normal(48000)
    assert C.snr_db(0.5 * r, r) > 100                                  # gain-fitted
    assert abs(C.snr_db(rng.standard_normal(48000), r)) < 0.1          # unrelated: about 0 dB
    assert C.snr_db(r + rng.standard_normal(48000), r) == pytest.approx(3.0, abs=0.3)


def test_check_files(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "OUT", tmp_path)
    d = C.sep_dir("mega53")
    d.mkdir(parents=True)
    bad, missing = C.write_check(d, {"a": {"problems": []}, "b": {"problems": ["x"]}}, ["a", "b", "c"])
    assert bad == {"b": ["x"]} and missing == ["c"] and not C.sep_ok("mega53")
    C.write_check(d, {"a": {"problems": []}}, ["a"])
    assert C.sep_ok("mega53")
    with pytest.raises(SystemExit, match="separation checks"):
        C.cmd_rebuild("blend")


# --- the share of 1b's gain and the reading --------------------------------------------------------------

def test_fieller_matches_the_t_interval_with_a_fixed_denominator():
    from scipy import stats

    a = [0.10, 0.05, 0.20, 0.12, 0.08, 0.15]
    d = [0.25] * 6
    f = C.fieller(a, d)
    m = sum(a) / 6
    half = stats.t.ppf(0.95, 5) * (sum((x - m) ** 2 for x in a) / 5 / 6) ** 0.5
    assert f["bounded"] and f["ratio"] == pytest.approx(m / 0.25)
    assert f["lo90"] == pytest.approx((m - half) / 0.25) and f["hi90"] == pytest.approx((m + half) / 0.25)


def test_fieller_unbounded_and_short():
    rng = random.Random(4)
    d = [rng.gauss(0.0, 0.3) for _ in range(14)]
    a = [rng.gauss(0.1, 0.1) for _ in range(14)]
    assert not C.fieller(a, d)["bounded"] and C.fieller(a, d)["lo90"] is None
    assert C.fieller([0.1, 0.2], [0.2, 0.3])["ratio"] is None


def test_fieller_brackets_the_ratio_with_noise():
    rng = random.Random(7)
    d = [0.25 + rng.gauss(0, 0.1) for _ in range(14)]
    a = [0.5 * x + rng.gauss(0, 0.05) for x in d]
    f = C.fieller(a, d)
    assert f["bounded"] and f["lo90"] < f["ratio"] < f["hi90"] and f["lo90"] < 0.5 < f["hi90"]


def test_share_is_band_weighted_over_part_means():
    num, den = {}, {}
    for i, (band, parts) in enumerate((("b1", ("p1", "p2")), ("b2", ("p3",)), ("b3", ("p4",)), ("b4", ("p5",)))):
        for p in parts:
            for amp in ("pr12", "sw50r"):
                num[(p, amp)] = (p, band, "clean", 0.1 * (i + 1))
                den[(p, amp)] = (p, band, "clean", 0.2 * (i + 1))
    num[("p6", "pr12")] = ("p6", "b5", "clean", 5.0)                   # no denominator: left out
    s = C.share(num, den)
    assert s["bands"] == 4 and s["ratio"] == pytest.approx(0.5) and s["leave_one_band_out"] == pytest.approx([0.5, 0.5])
    assert C.band_means(num)["b1"] == pytest.approx(0.1)


def test_reading_1c():
    assert C.reading_1c({"lo90": 0.02, "hi90": 0.2}, 0.252) == "above"
    assert C.reading_1c({"lo90": -0.2, "hi90": -0.01}, 0.252) == "below"
    assert C.reading_1c({"lo90": -0.04, "hi90": 0.05}, 0.252) == "near zero"   # top under 0.063
    assert C.reading_1c({"lo90": -0.04, "hi90": 0.07}, 0.252) == "undecided"
    assert C.reading_1c({"lo90": -0.04, "hi90": 0.05}, None) == "undecided"
    assert C.reading_1c({"lo90": None, "hi90": None}, 0.252) == "undecided"


# --- the report on fakes ---------------------------------------------------------------------------------

def test_blend_lag_rule():
    assert C.blend_problems(0) == [] and C.blend_problems(1) == [] and C.blend_problems(-1) == []
    assert "±1" in C.blend_problems(2)[0] and C.blend_problems(None)


def test_edge_bound_is_confined_to_the_crop_ends():
    import numpy as np

    x = np.random.default_rng(5).standard_normal(48000 * 3)
    e = C.edge_bound(x, 48000, n=48000)
    assert e["max_db"] < 0 and 0 < e["extent_ms"] < 20                 # a few ms at the ends, not the middle
    assert C.edge_bound(x, 48000, n=48000, floor_db=0.0)["extent_ms"] == 0


def test_fieller_reports_shape_and_df():
    f = C.fieller([0.1, 0.05, 0.2, 0.12], [0.25, 0.2, 0.3, 0.22])
    assert f["shape"] == "interval" and f["df"] == 3
    rng = random.Random(4)
    g = C.fieller([rng.gauss(0.1, 0.1) for _ in range(14)], [rng.gauss(0.0, 0.3) for _ in range(14)])
    assert g["shape"] in ("two rays", "whole line") and g["df"] == 13


BT = {"cam": {"source": "cambridge", "halves": {"A": {"flag": "low"}, "B": {"flag": "low"}}},
      "tel": {"source": "telefunken", "halves": {"A": {"flag": "high"}, "B": {"flag": "low"}}},
      "mod": {"source": "telefunken", "halves": {"A": {"flag": "low"}, "B": {"flag": "moderate"}}}}


def test_kept_directions():
    H = ("A", "B")
    assert C.kept_directions("all", "tel", "x", BT) == H
    assert C.kept_directions("no_high", "tel", "x", BT) == () and C.kept_directions("no_high", "mod", "x", BT) == H
    assert C.kept_directions("no_high_dir", "tel", "x", BT) == ("A",)     # direction B is judged on half A
    assert C.kept_directions("no_moderate_or_high", "mod", "x", BT) == ()
    assert C.kept_directions("no_moderate_or_high_dir", "mod", "x", BT) == ("B",)
    assert C.kept_directions("cambridge_only", "cam", "x", BT) == H and C.kept_directions("cambridge_only", "tel", "x", BT) == ()
    assert C.kept_directions("telefunken_only", "mod", "x", BT) == H
    assert C.kept_directions("without_musdb_train", "cam", "Wall Of Death", BT) == ()
    assert C.kept_directions("without_musdb_train", "cam", "Diesel13", BT) == H
    assert C.kept_directions("no_high", "unknown", "x", BT) == ()


def test_row_report_pairs_numerator_and_denominator_on_the_same_cells():
    ps = {"cam": {"band": "b1", "gain_class": "clean"}, "tel": {"band": "b2", "gain_class": "clean"},
          "mod": {"band": "b3", "gain_class": "clean"}}
    dv = {("cam", "pr12"): {"sep": {"A": 0.5, "B": 0.5}, "current": {"A": 0.3, "B": 0.3}, "matched_1b": {"A": 0.7, "B": 0.7}},
          ("tel", "pr12"): {"sep": {"A": 0.9, "B": 0.1}, "current": {"A": 0.1, "B": 0.1}, "matched_1b": {"A": 0.2, "B": 0.2}},
          ("mod", "pr12"): {"current": {"A": 0.0, "B": 0.0}, "matched_1b": {"A": 0.4, "B": 0.4}}}
    ceil = {c: 0.9 for c in dv}
    r = C.row_report(dv, ceil, ps, BT, "no_high_dir")
    assert r["sep_minus_current"]["cells"] == 2                       # tel keeps direction A only: 0.9 − 0.1
    assert r["sep_minus_current"]["band_weighted_mean"] == pytest.approx((0.2 + 0.8) / 2)
    assert r["matched_1b_minus_current"]["cells"] == 3                 # its own row, on its cells
    assert r["share_of_1b_gain"]["bands"] == 2                         # the share: only cells with both
    assert r["share_of_1b_gain"]["ratio"] is None                     # under 3 bands: no Fieller
    c = C.row_report(dv, ceil, ps, BT, "no_high")
    assert c["current"]["cells"] == 2 and c["share_of_1b_gain"]["bands"] == 1


def test_stored_1b_rows_reproduce_the_bleed_audit():
    """The audited 1b figures (bleed README, r4): matched − current +0.252 on all of Σ, +0.227 without
    high bleed, +0.253 without moderate or high, +0.273 on Cambridge only (cell rule)."""
    try:
        meta, sig = M.load_sigma()
    except SystemExit:
        pytest.skip("Σ is not on this machine")
    cfgs = {"current": M.CURRENT, "matched_1b": M.MATCHED}
    src = {"current": "cprime", "matched_1b": M.MATCHED_DI}
    dv, ceil = C.cell_directions(sig, cfgs, src, tuple(cfgs))
    if len(dv) != 72:
        pytest.skip("experiment 1 and 1b scores are not all here")
    ps, bt = K.parts(), C.load_bleed_table()
    want = {"all": (0.252, 14), **{k: (v, n) for (k, v), n in zip(C.BLEED_1B.items(), (14, 12, 11))}}
    for row, (v, bands) in want.items():
        r = C.row_report(dv, ceil, ps, bt, row, names=("current", "matched_1b"))["matched_1b_minus_current"]
        assert round(r["band_weighted_mean"], 3) == pytest.approx(v) and r["bands"] == bands, row


def test_report_on_fake_scores(tmp_path, monkeypatch):
    """A perfect separator (its objective is the truth) reads above today's objective; the reading
    is refused on an incomplete set; the share and the decomposition are present."""
    monkeypatch.setattr(M, "OUT", tmp_path)
    rng = random.Random(3)
    srcs = ["S"] + ["nbr"] * 5 + ["ks"] * 4 + ["armA"] * 2
    ps, sig, cells = {}, {}, {}
    for i in range(8):
        slug = f"p{i}"
        ps[slug] = {"band": f"b{i % 6}", "gain_class": "clean"}
        for amp in ("pr12", "sw50r"):
            pts = [{"source": s, "key": f"{slug}{amp}{j}"} for j, s in enumerate(srcs)]
            sig[(slug, amp)] = pts
            cells[f"{slug}|{amp}"] = pts
            true = [{"A": 1 + j + rng.random(), "B": 1 + j + rng.random()} for j in range(len(srcs))]
            noisy = lambda s: [{h: t[h] + rng.gauss(0, s) for h in "AB"} for t in true]  # noqa: E731
            files = {"measure": {M.cname(M.TRUE): true}, "cprime": {M.cname(M.CURRENT): noisy(6.0),
                                                                    "cprime|reference|native|own": noisy(3.0)},
                     M.MATCHED_DI: {M.cname(M.MATCHED): noisy(1.5)},
                     DI: {f"{DI}|mega53|native|own": noisy(0.0), f"{DI}|mega53|gcc|own": noisy(0.5),
                          f"{DI}|stem|native|own": noisy(4.0)},
                     VIEW: {"cprime|mega53|native|own": noisy(3.0)}}
            for d, cfg in files.items():
                p = tmp_path / "scores" / d / slug / f"{amp}.json"
                p.parent.mkdir(parents=True, exist_ok=True)
                scores = [{c: v[j] for c, v in cfg.items()} for j in range(len(srcs))]
                extra = {"flac_vs_float_S": {f"{DI}|mega53|native|own": {"A": 1e-6, "B": 2e-6}}} if d == DI else {}
                p.write_text(json.dumps({"scores": scores, **extra}))
            r = tmp_path / "renders" / DI / slug / f"{amp}.json"
            r.parent.mkdir(parents=True, exist_ok=True)
            r.write_text(json.dumps({"renders": len(srcs) + 1}))
    monkeypatch.setattr(M, "load_sigma", lambda: ({"hash": M.SIGMA_HASH, "cells": cells}, sig))
    monkeypatch.setattr(K, "parts", lambda: ps)
    monkeypatch.setattr(C, "load_bleed_table", lambda: {
        f"p{i}": {"source": "cambridge" if i < 5 else "telefunken",
                  "halves": {"A": {"flag": "high" if i == 7 else "low"}, "B": {"flag": "low"}}} for i in range(8)})
    C.cmd_report("mega53")
    rep = json.loads((tmp_path / "report-1c-mega53.json").read_text())
    a = rep["subsets"]["all"]
    assert rep["cells"] == 16 and rep["renders_used"] == rep["renders_expected"] == 16 * 13
    assert a["sep"]["cross_half"]["band_weighted_mean"] == pytest.approx(a["ceiling"]["band_weighted_mean"])
    assert a["sep_minus_current"]["cross_half"]["band_weighted_mean"] > 0
    assert a["reading"].startswith("refused")                          # not 72 cells and 3,528 renders
    assert set(rep["subsets"]) == {"all", "neighbourhood", "ks", "armA", "without_armA"}
    assert {"ratio", "lo90", "hi90", "leave_one_band_out"} <= set(a["share_of_1b_gain"]["cross_half"])
    assert a["reference_only_minus_current"]["cross_half"]["cells"] == 16
    assert rep["flac_vs_float_S"] == {"n": 32, "max": 2e-6, "over_tol": 0}
    assert len(rep["per_band_cross_half"]) == 6
    rows = rep["bleed_and_leak_rows"]
    assert set(rows) == set(C.ROWS) and rows["no_high"]["sep_minus_current"]["cells"] == 14
    assert rows["cambridge_only"]["current"]["cells"] == 10 and rows["telefunken_only"]["current"]["cells"] == 6
    assert rows["all"]["sep_minus_current"]["band_weighted_mean"] == pytest.approx(
        a["sep_minus_current"]["cross_half"]["band_weighted_mean"])
    assert "interaction" in a and rep["scope"].startswith("on the instrumental context")


# --- the stored contexts (zero separations) --------------------------------------------------------------

def test_stored_contexts_resolve_for_all_24_parts():
    sf = pytest.importorskip("soundfile")
    try:
        ps = C.parts()
    except (FileNotFoundError, KeyError):
        pytest.skip("step 3's parts are not on this machine")
    if len(ps) != 24:
        pytest.skip("step 3's parts are not all here")
    kinds = set()
    for slug, part in ps.items():
        plan = C.part_plan(slug, part)
        if not plan["input"].exists():
            pytest.skip("the stored contexts are not on this machine")
        info = sf.info(str(plan["input"]))
        assert info.samplerate == C.SR and info.channels == 1, slug
        assert plan["offset"] + C.CROP <= info.frames, slug
        assert plan["lineup"].exists(), slug
        kinds.add(plan["kind"])
    assert kinds == {"context"}                                       # every step-3 stem used its context
