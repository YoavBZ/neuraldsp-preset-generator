"""The knob-ceiling search's pure parts (`learn/knob_ceiling.py`)."""

import math

import pytest

pytest.importorskip("numpy")

from learn import knob_ceiling as K  # noqa: E402


def test_unit_mapping_round_trips():
    d = K.Dim("m", "k", "cont", -24.0, 24.0)
    assert d.to_unit("-24") == 0 and d.to_unit("24") == 1 and d.from_unit(0.5) == 0
    assert d.to_unit("99") == 1                      # clipped
    f = K.Dim("m", "hpf", "log", 20.0, 500.0)
    assert math.isclose(f.from_unit(f.to_unit("100")), 100.0)
    assert math.isclose(f.from_unit(0.5), math.sqrt(20 * 500))


def _problem():
    dims = [K.Dim("a", "x", "cont"), K.Dim("a", "y", "cont"),
            K.Dim("a", "sw", "switch", values=("false", "true")),
            K.Dim("a", "mic", "cat", values=tuple("0123456789"))]
    x0 = {("a", "x"): "0.1", ("a", "y"): "0.9", ("a", "sw"): "false", ("a", "mic"): "0", ("b", "keep"): "7"}

    def f(x):
        return ((float(x[("a", "x")]) - 0.62) ** 2 + (float(x[("a", "y")]) - 0.3) ** 2
                + (0.0 if x[("a", "sw")] == "true" else 0.5) + (0.0 if x[("a", "mic")] == "6" else 0.3))
    return dims, x0, f


def test_coord_search_finds_the_optimum_and_keeps_other_settings():
    dims, x0, f = _problem()
    x, best, trace = K.coord_search(dims, x0, f, budget=200, seed=1)
    assert x[("a", "sw")] == "true" and x[("a", "mic")] == "6"
    assert abs(float(x[("a", "x")]) - 0.62) < 0.02 and abs(float(x[("a", "y")]) - 0.3) < 0.02
    assert x[("b", "keep")] == "7"
    assert best == pytest.approx(f(x))
    assert [b for _, b in trace] == sorted((b for _, b in trace), reverse=True)


def test_coord_search_respects_the_budget_and_is_deterministic():
    dims, x0, f = _problem()
    calls = []

    def g(x):
        calls.append(1)
        return f(x)
    a = K.coord_search(dims, x0, g, budget=17, seed=3)
    assert len(calls) == 17
    b = K.coord_search(dims, x0, f, budget=17, seed=3)
    assert a[0] == b[0] and a[1] == b[1]


def test_coord_search_never_evaluates_a_setting_twice():
    dims, x0, f = _problem()
    seen = []

    def g(x):
        k = K.key(x)
        assert k not in seen
        seen.append(k)
        return f(x)
    K.coord_search(dims, x0, g, budget=150, seed=0)


def test_at_limit_flags_only_moved_extremes():
    d = [K.Dim("a", "x", "cont"), K.Dim("a", "y", "cont")]
    assert K.at_limit(d, {("a", "x"): "1", ("a", "y"): "0"}, {("a", "x"): "0.5", ("a", "y"): "0"}) == ["a/x"]


def test_eq_start_flattens_an_inactive_eq_and_keeps_an_active_one():
    off = {("pr12EQ", "pr12EQActive"): "false", ("pr12EQ", "pr12EQBand3"): "5",
           ("eqParameters", "sectionActive"): "true"}
    s = K.eq_start(off, "pr12")
    assert s[("pr12EQ", "pr12EQActive")] == "true" and s[("pr12EQ", "pr12EQBand3")] == "0"
    assert s[("pr12EQ", "pr12EQHpf")] == "20" and s[("pr12EQ", "pr12EQLpf")] == "20000"
    on = {**off, ("pr12EQ", "pr12EQActive"): "true"}
    assert K.eq_start(on, "pr12")[("pr12EQ", "pr12EQBand3")] == "5"


def test_spaces_hold_only_manifest_parameters():
    import json
    import pathlib

    params = json.loads((pathlib.Path(K.PLUGIN_ROOT) / "packs/morgan/manifest.json").read_text())["parameters"]
    for amp in K.AMPS:
        for d in K.space(amp) + K.eq_space(amp):
            spec = params[d.name]
            if "min" in spec:
                assert spec["min"] <= d.lo and d.hi <= spec["max"], d.name


def _cell(menu, runs):
    return {"start": "S", "menu": menu, "runs": runs}


def test_cell_rows_cross_half_uses_the_held_half():
    menu = {"S": {"A": 4.0, "B": 4.0}, "M": {"A": 2.0, "B": 3.0}}
    run = lambda: {"M": "M", "K_M": {"search": 1.0, "held": 1.5}, "K_S": {"search": 2.0, "held": 2.0},
                   "EQ": {"search": 1.0, "held": 1.5}}
    cross, ins = K.cell_rows(_cell(menu, {"A": run(), "B": run()}))
    # direction A→B: K_M held 1.5 vs M held 3.0; B→A: K_M held 1.5 vs M held 2.0
    assert cross["KM_vs_M"] == pytest.approx((math.log(0.5) + math.log(0.75)) / 2)
    assert ins["KM_vs_M"] == pytest.approx((math.log(1 / 2) + math.log(1 / 3)) / 2)
    assert cross["EQ_vs_KM"] == pytest.approx(0.0)


def test_reading_follows_the_declared_thresholds():
    s = lambda bw, m, neg, n: {"band_weighted_mean": bw, "mean": m, "bands_negative": neg, "bands": n}
    assert K.reading(s(-0.02, -0.03, 8, 15)).startswith("the search found little") and "undecided" in K.reading(s(-0.02, -0.03, 8, 15))
    assert K.reading(s(-0.12, -0.11, 9, 15)).startswith("knobs add a lot")
    assert K.reading(s(-0.12, -0.11, 6, 15)) == "in between"
    assert K.reading(s(-0.07, -0.07, 12, 15)) == "in between"


def test_reading_says_a_lot_only_by_the_judge():
    s = {"band_weighted_mean": -0.2, "mean": -0.2, "bands_negative": 10, "bands": 15}
    assert "by the judge" in K.reading(s) and "listening" in K.reading(s)


class _FakeRenderer:
    """Renders a preset as its settings; the judge below reads them back."""

    def render(self, di32, select, edits):
        return dict(edits)


def _fake_judge(refuse_half=None):
    def judge(ref, y, di, lag):
        v = 1.0 + abs(float(y[("pr12Amp", "pr12Volume")]) - 0.7) + abs(float(y.get(("parameters", "inputGain"), 0)) / 48)
        return {h: (math.inf if h == refuse_half else v * (1.1 if h == "B" else 1.0)) for h in ("A", "B")}
    return judge


def _fake_menu():
    base = {("pr12Amp", "pr12Volume"): "0.2", ("pr12Amp", "pr12Treble"): "0.5", ("pr12Amp", "pr12Bass"): "0.5",
            ("parameters", "inputGain"): "0", ("cabParameters", "leftMicType"): "0",
            ("cabParameters", "rightMicType"): "4", ("cabParameters", "leftCabActive"): "true"}
    return {"pr12": {"S": (1, dict(base)), "other": (1, {**base, ("pr12Amp", "pr12Volume"): "0.5"})}}


def test_run_cell_improves_on_the_menu_with_a_fake_renderer(monkeypatch):
    monkeypatch.setattr(K, "judge", _fake_judge())
    res = K.run_cell(_FakeRenderer(), _fake_menu(), "pr12", None, __import__("numpy").zeros(4), 0, "S", None,
                     budgets={"K_M": 40, "K_S": 30, "EQ": 10})
    cross, ins = K.cell_rows(res)
    assert res["runs"]["A"]["M"] == "other"
    assert cross["KM_vs_M"] < 0 and cross["M_vs_S"] < 0
    assert max(res["repeat"].values()) == 0
    assert "KM@25_vs_M" in cross


def test_run_cell_skips_a_refused_half_and_the_report_survives(monkeypatch):
    monkeypatch.setattr(K, "judge", _fake_judge(refuse_half="B"))
    res = K.run_cell(_FakeRenderer(), _fake_menu(), "pr12", None, __import__("numpy").zeros(4), 0, "S", None,
                     budgets={"K_M": 20, "K_S": 20, "EQ": 5})
    assert all("skipped" in r for r in res["runs"].values())
    assert K.cell_rows(res) == ({}, {})


def test_perturbed_reflects_inwards():
    d = [K.Dim("a", "x", "cont"), K.Dim("p", "g", "cont", -24.0, 24.0)]
    out = K.perturbed(d, {("a", "x"): "0.9", ("p", "g"): "0"}, {("a", "x"): 0.17, ("p", "g"): 5.3})
    assert float(out[("a", "x")]) == pytest.approx(0.73) and float(out[("p", "g")]) == pytest.approx(5.3)


def test_space_drops_an_inactive_left_cab():
    names = {d.name for d in K.space("pr12", {("cabParameters", "leftCabActive"): "false"})}
    assert "cabParameters/leftMicType" not in names and "cabParameters/rightMicType" in names
    assert "cabParameters/leftMicType" in {d.name for d in K.space("pr12")}


def test_control_passes_needs_every_cell_close_and_three_recovered():
    good = {"ratio_held": 0.2, "settings_within_0.1": 3, "mic_exact": True}
    assert K.control_passes({str(i): dict(good) for i in range(4)})
    assert not K.control_passes({**{str(i): dict(good) for i in range(3)}, "3": {**good, "ratio_held": 0.4}})
    assert not K.control_passes({**{str(i): dict(good) for i in range(2)},
                                 "2": {**good, "mic_exact": False}, "3": {**good, "settings_within_0.1": 2}})


def test_levels_policy_finds_a_mic_the_knobs_would_hide():
    # the wrong mic can be offset by x, so a mic chosen before x moves is a trap
    dims = [K.Dim("a", "x", "cont"), K.Dim("a", "mic", "cat", values=tuple("0123456789"))]
    x0 = {("a", "x"): "0.1", ("a", "mic"): "0"}

    def f(x):
        m = int(x[("a", "mic")])
        shift = {0: 0.0, 4: 0.0, 7: 0.3}.get(m, 0.6)
        return abs(float(x[("a", "x")]) + shift - 0.8) + (0.0 if m == 4 else 0.2)
    x, best, _ = K.coord_search(dims, x0, f, budget=120, seed=0, cats="levels")
    assert x[("a", "mic")] == "4" and best < 0.03
    _, again, _ = K.coord_search(dims, x0, f, budget=120, seed=0, cats="levels")
    assert again == best


def test_knob_search_keeps_the_budget_and_never_repeats():
    dims, x0, f = _problem()
    calls = []

    def g(x):
        calls.append(K.key(x))
        return f(x)
    x, best, hist, stages = K.knob_search(dims, x0, g, budget=120, seed=0)
    assert len(calls) <= 120 and len(set(calls)) == len(calls)
    assert best == pytest.approx(f(x)) and hist[-1][1] == pytest.approx(best)
    assert x[("a", "mic")] == "6" and x[("a", "sw")] == "true"


def test_knob_search_escapes_a_mic_trap_the_plain_search_falls_into():
    dims = [K.Dim("a", "x", "cont"), K.Dim("a", "y", "cont"), K.Dim("a", "mic", "cat", values=tuple("0123456789"))]
    x0 = {("a", "x"): "0.1", ("a", "y"): "0.5", ("a", "mic"): "0"}

    def f(x):
        m = int(x[("a", "mic")])
        shift = 0 if m == 4 else 0.1 * (1 + 0.2 * abs(m - 4))
        return abs(float(x[("a", "x")]) + shift - 0.8) + abs(float(x[("a", "y")]) - 0.3) + (0 if m == 4 else 0.05)
    plain = K.coord_search(dims, x0, f, 200, 0, cats="levels")
    new = K.knob_search(dims, x0, f, 200, 0)[:2]
    assert plain[0][("a", "mic")] != "4"
    assert new[0][("a", "mic")] == "4" and new[1] < plain[1]


def test_knob_search_reaches_both_mics_and_every_stage_on_a_real_space():
    dims = K.space("sw50r")
    x0 = {(d.module, d.key): (d.values[0] if d.values else "0.5") for d in dims}
    x0[("parameters", "inputGain")] = "0"
    tried = {"left": set(), "right": set()}

    def f(x):
        tried["left"].add(x[("cabParameters", "leftMicType")])
        tried["right"].add(x[("cabParameters", "rightMicType")])
        return sum(abs(float(x[(d.module, d.key)]) - 0.3) for d in dims if d.kind == "cont") \
            + (0 if x[("cabParameters", "rightMicType")] == "7" else 0.5)
    for budget in (150, 200):
        tried = {"left": set(), "right": set()}
        x, best, hist, stages = K.knob_search(dims, x0, f, budget, 0)
        assert len(tried["left"]) == 10 and len(tried["right"]) == 10
        assert set(stages) == {"main", "alts", "restarts", "final"}
        assert all(st["renders"] > 0 for st in stages.values()), stages
        assert sum(st["renders"] for st in stages.values()) <= budget
        assert x[("cabParameters", "rightMicType")] == "7"


def test_knob_search_without_mics_gives_the_rest_to_the_final_stage():
    dims = K.eq_space("pr12")
    x0 = K.eq_start({}, "pr12")
    _, _, _, stages = K.knob_search(dims, x0, lambda x: abs(float(x[("pr12EQ", "pr12EQBand3")]) - 4), 100, 0)
    assert set(stages) == {"main", "final"}


def test_cross_rows_separates_part_specific_from_generic():
    cell = {"menu": {"M": {"A": 4.0, "B": 4.0}},
            "runs": {"A": {"M": "M", "K_M": {"held": 2.0}, "EQ": {"held": 2.0}},
                     "B": {"M": "M", "K_M": {"held": 2.0}, "EQ": {"held": 2.0}}}}
    others = {"x": {"A": 3.0, "B": 3.0}, "y": {"A": 3.0, "B": 3.0}, "z": {"A": 9.0, "B": 9.0}}
    cr = {"A": {"K_M": others, "EQ": others}, "B": {"K_M": others, "EQ": others}}
    r = K.cross_rows(cell, cr)
    assert r["KM_part_specific"] == pytest.approx(math.log(2 / 3))
    assert r["KM_generic"] == pytest.approx(math.log(3 / 4))


def _bounded_renderer(workdir):
    """The learn-side Morgan renderer, never started: only its DI write path runs."""
    pytest.importorskip("soundfile")
    made = K.renderer_class()("morgan", process_policy="reuse", isolate=True, workdir=workdir)
    made._ensure_server = lambda: None
    return made


def test_distinct_dis_do_not_accumulate_on_disk(tmp_path):
    """A render set over thousands of distinct DIs (part C) keeps a bounded few files; a DI
    that returns after eviction is written again under the same name with the same samples.

    Not the same bytes: libsndfile stamps a FLOAT WAV's PEAK chunk with the write time, so a
    rewrite in a later second differs there. Nothing reads the bytes (the renderer keys DIs by
    the array's digest and the server by path, decoding the samples), so the rewrite here is
    forced into a later second, where a raw-byte comparison would fail every time."""
    import time

    import numpy as np
    import soundfile as sf

    made = _bounded_renderer(tmp_path)
    first = np.linspace(-0.5, 0.5, 4096, dtype=np.float32)
    path = made._di_file(first)
    written_in = int(time.time())
    info = sf.info(str(path))
    for n in range(K.DI_FILES_KEPT * 5):
        assert made._di_file(np.full(4096, n / 100.0, dtype=np.float32)).exists()
        assert len(list(tmp_path.glob("di-*.wav"))) <= K.DI_FILES_KEPT
        assert len(made._di_files) <= K.DI_FILES_KEPT
    assert not path.exists()
    while int(time.time()) <= written_in:
        time.sleep(0.02)
    again = made._di_file(first)
    assert again == path
    again_info = sf.info(str(again))
    assert (again_info.format, again_info.subtype, again_info.samplerate, again_info.channels,
            again_info.frames) == (info.format, info.subtype, info.samplerate, info.channels,
                                   info.frames)
    assert again_info.subtype == "FLOAT"
    assert np.array_equal(sf.read(str(again), dtype="float32", always_2d=True)[0][:, 0], first)


def test_a_di_in_use_is_never_the_one_evicted(tmp_path):
    """A search that keeps returning to its DI between a few others never rewrites it."""
    import numpy as np

    made = _bounded_renderer(tmp_path)
    di = np.zeros(2048, dtype=np.float32)
    path = made._di_file(di)
    stamp = path.stat().st_mtime_ns
    for n in range(K.DI_FILES_KEPT * 3):
        made._di_file(np.full(2048, (n + 1) / 100.0, dtype=np.float32))
        assert made._di_file(di) == path
    assert path.stat().st_mtime_ns == stamp


def test_close_removes_the_work_directory_it_made():
    import numpy as np

    pytest.importorskip("soundfile")
    made = K.renderer_class()("morgan", process_policy="reuse", isolate=True)
    made._ensure_server = lambda: None
    made._di_file(np.zeros(2048, dtype=np.float32))
    workdir = made._workdir
    assert workdir.name.startswith("au-render-") and any(workdir.iterdir())
    made.close()
    assert not workdir.exists()
