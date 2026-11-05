"""L1a's centre read, its pure parts (`learn/capture_centres.py`)."""

import math

import pytest

from learn import capture_centres as C


def _recs(amp, cls, n, off=0):
    return [{"unit": f"u{amp}{cls}{i + off:03d}", "amp": amp, "cls": cls, "label": {"i": i}} for i in range(n)]


def test_cells_keep_labelled_records_in_unit_order():
    recs = _recs("ac20", "clean", 3)[::-1] + [{"unit": "x", "amp": "ac20", "cls": "clean", "label": None}]
    cells = C.by_cell(recs, lambda r: r["cls"])
    assert [r["unit"] for r in cells[("ac20", "clean")]] == [f"uac20clean{i:03d}" for i in range(3)]


def test_draws_match_the_count_are_seeded_and_differ_by_draw():
    cells = {("ac20", "clean"): _recs("ac20", "clean", 40), ("pr12", "crunch"): _recs("pr12", "crunch", 5)}
    counts = {("ac20", "clean"): 12, ("pr12", "crunch"): 9}
    a, b, c = C.draw_cells(cells, counts, 0), C.draw_cells(cells, counts, 0), C.draw_cells(cells, counts, 1)
    assert a == b and a != c
    assert len(a[("ac20", "clean")]) == 12 and len({r["unit"] for r in a[("ac20", "clean")]}) == 12
    assert len(a[("pr12", "crunch")]) == 5


def test_a_creator_draw_takes_whole_creators():
    cells = {("ac20", "clean"): _recs("ac20", "clean", 12)}
    who = lambda r: int(r["unit"][-3:]) // 3  # noqa: E731
    d = C.creator_draw(cells, who, 7)[("ac20", "clean")]
    names = {who(r) for r in d}
    assert all(sum(who(r) == n for r in d) % 3 == 0 for n in names)
    assert C.creator_draw(cells, who, 7) == C.creator_draw(cells, who, 7)


def test_a_direction_follows_the_report_rule():
    table = {("S", 1): 2.0, ("a", 1): 1.0, ("b", 1): 4.0, ("S", 2): "refused", ("S", 4): 3.0, ("a", 4): "refused", ("b", 4): 3.0}
    value = lambda j, t, u: table.get((t, u))  # noqa: E731
    v, st = C.direction_value(None, "a", "b", 1, value)
    assert v == pytest.approx(math.log(0.25)) and st == "ok"
    assert C.direction_value(None, "a", "b", 2, value) == (None, "base_dropped")
    assert C.direction_value(None, "a", "b", 3, value) == (None, "missing")
    assert C.direction_value(None, "a", "b", 4, value) == (0, "refused")
    assert C.direction_value(None, "a", "S", 1, value)[0] == pytest.approx(math.log(0.5))


def test_a_row_moves_only_when_it_clears_zero_and_the_draws_agree():
    clear = {"mean": -0.1, "lo90": -0.2, "hi90": -0.01}
    assert C.moved(clear, [-0.1, -0.2, -0.05])
    assert not C.moved(clear, [-0.1, 0.02, -0.05])
    assert not C.moved({"mean": -0.1, "lo90": -0.2, "hi90": 0.01}, [-0.1, -0.2, -0.05])
    assert not C.moved({"mean": -0.1, "lo90": None, "hi90": None}, [-0.1, -0.2, -0.05])
    assert C.moved({"mean": 0.1, "lo90": 0.01, "hi90": 0.2}, [0.1, 0.2, 0.05])
    assert C.moved({"mean": -0.15, "lo90": -0.2, "hi90": -0.1}, [0.02, 0.03, 0.01])   # RcT - S beside draws of the other sign


def test_the_mean_row_keeps_directions_every_draw_holds():
    a = {1: ("d1", "u1", -0.2), 2: ("d1", "u2", 0.4)}
    b = {1: ("d1", "u1", -0.4)}
    assert C.mean_rows([a, b]) == {1: ("d1", "u1", pytest.approx(-0.3))}


def test_the_panel_read_must_be_counted_first():
    assert not C.panel_counted({"phase_5d_panel_reads": "1 (2026-11-01: RG, centres)"})
    assert C.panel_counted({"phase_5d_panel_reads": "2 (2026-11-06: RcT)"})
    assert not C.panel_counted({})
    assert not C.panel_counted({"phase_5d_panel_reads": "2 (2026-11-06: another read)"})


def test_quantiles_and_the_setting_distance():
    assert C.quantiles(list(range(100))) == [5, 50, 95]

    class D:
        def __init__(self, kind, v):
            self.kind, self.v = kind, v

    dims = [D("cont", 0), D("log", 1), D("switch", 2)]
    a, b = [0.0, 0.4, 0.9], [0.3, 0.0, 0.1]
    assert C.cell_rms(dims, a, b, lambda d, x: x[d.v]) == pytest.approx(math.sqrt((0.09 + 0.16) / 2))


def test_every_command_refuses_before_the_rest_may_run(monkeypatch):
    from learn import capture_labels as CL
    from learn import pipeline_fix as P

    monkeypatch.setattr(P, "require", lambda key: {})

    def stop():
        raise SystemExit("the rest waits for the scope page")

    monkeypatch.setattr(CL, "rest_may_run", stop)
    for cmd in (C.cmd_answers, C.cmd_distance, C.cmd_report):
        with pytest.raises(SystemExit, match="scope page"):
            cmd(None)


def test_the_null_draws_with_replacement_apart_from_the_read():
    rs = list(range(30))
    a, b = C.replace_draw(rs, 30, "x"), C.replace_draw(rs, 30, "y")
    assert a == C.replace_draw(rs, 30, "x") and a != b and len(set(a)) < 30
    assert not set(C.null_draws()) & set(range(C.DRAWS)) and len(C.null_draws()) == C.DISTANCE_DRAWS


class _Dim:
    def __init__(self, module, key, kind):
        self.module, self.key, self.kind = module, key, kind


def test_categorical_gaps_are_counted():
    dims = [_Dim("m", "a", "cont"), _Dim("m", "b", "switch"), _Dim("m", "c", "switch")]
    assert C.cell_cats(dims, {("m", "b"): 1, ("m", "c"): 2}, {("m", "b"): 1, ("m", "c"): 3}) == 1


def test_a_missing_render_stops_the_report():
    with pytest.raises(SystemExit, match="1 renders missing"):
        C.counted(lambda a, b: ({}, {"missing": 1}), "RcT", "S")


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Made-up files and stubs for everything outside this module: 2 BKS units, 2 panel units, 3 amps."""
    import json

    from learn import capture_labels as CL
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    root = tmp_path / "pf"
    for d in ("real/answers", "panel/answers", "captures"):
        (root / d).mkdir(parents=True)
    cls = "clean"
    bks = [{"unit": f"bks/u{i}", "di": f"d{i % 2}", "cls": cls, "rig": "r"} for i in range(2)]
    panel = [{"unit": f"pan/u{i}", "di": f"pd{i}", "cls": cls, "band": "b"} for i in range(2)]
    (root / "real/answers/S.json").write_text(json.dumps({"parts": bks}))
    monkeypatch.setattr(P, "out_dir", lambda *a: root)
    monkeypatch.setattr(CL, "root", lambda: root / "captures")
    monkeypatch.setattr(CL, "rest_may_run", lambda: None)
    monkeypatch.setattr(P, "require", lambda key: {"phase_5d_panel_reads": "2 (RcT)"})
    monkeypatch.setattr(P, "panel_lagged_units", lambda: (panel, {}))
    monkeypatch.setattr(P, "A_menu_S", lambda: {a: {cls: (f"sel-{a}", {"s": 1})} for a in P.AMPS3})
    monkeypatch.setattr(K, "space", lambda amp, S: [])
    monkeypatch.setattr(LO, "tdict", lambda x: x)
    monkeypatch.setattr(LO, "sdict", lambda x: x)
    monkeypatch.setattr(P, "rc_setting", lambda dims, S, labels: {"n": len(labels)})
    cap = {(a, cls): [{"unit": f"cap{a}{i}", "amp": a, "label": {"i": i}} for i in range(4)] for a in P.AMPS3}
    goat = {(a, cls): [{"unit": f"g{a}{i}", "amp": a, "label": {"i": i}} for i in range(9)] for a in P.AMPS3}
    monkeypatch.setattr(C, "capture_cells", lambda: (cap, {}))
    monkeypatch.setattr(C, "goat_cells", lambda: goat)
    return {"root": root, "P": P, "bks": bks, "panel": panel}


def test_answers_carry_a_centre_on_every_direction_and_are_written_once(world):
    import json

    P, root = world["P"], world["root"]
    C.cmd_answers(None)
    for sub, units in (("real", world["bks"]), ("panel", world["panel"])):
        for t in C.TAGS:
            a = json.loads((root / sub / "answers" / f"{t}.json").read_text())["answers"]
            assert len(a) == len(units) * 3
            one = a[P.real_key(units[0], "ac20")][P.ANY_HALF]
            assert one == {"select": "sel-ac20", "settings": {"n": 4}}
    with pytest.raises(SystemExit, match="written once"):
        C.cmd_answers(None)


def test_answers_refuse_until_the_panel_read_is_counted(world, monkeypatch):
    P = world["P"]
    monkeypatch.setattr(P, "require", lambda key: {"phase_5d_panel_reads": "1 (2026-11-01)"})
    with pytest.raises(SystemExit, match="phase_5d_panel_reads"):
        C.cmd_answers(None)
    assert not (world["root"] / "panel/answers/RcT.json").exists()


def _judged(root, sub, tag, unit, amp, judge):
    import json

    d = root / sub / "judge" / tag
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{unit.replace('/', '__')}|{amp}.json").write_text(json.dumps({"unit": unit, "amp": amp, "judge": judge}))


def test_the_bks_reader_keeps_the_sign_and_counts_a_missing_render(world):
    P, root = world["P"], world["root"]
    unit = world["bks"][0]["unit"]
    for t, d in (("S", 2.0), ("RcT", 1.0), ("RcG", 4.0)):
        for amp in P.AMPS3:
            for u in (p["unit"] for p in world["bks"]):
                if not (t == "RcT" and u != unit):
                    _judged(root, "real", t, u, amp, {P.ANY_HALF: {"A": d, "B": d}})
    rows, cnt = C.bks_reader(("RcT", "RcG"))("RcT", "RcG")
    assert cnt == {"directions": 12, "missing": 6, "base_dropped": 0, "refused": 0}
    assert len(rows) == 6 and all(v[2] == pytest.approx(math.log(0.25)) for v in rows.values())


def test_the_panel_reader_keeps_the_sign_and_counts_a_missing_render(world, monkeypatch):
    P, root = world["P"], world["root"]
    units = world["panel"]
    monkeypatch.setattr(P, "panel_halves", lambda us: {u["unit"]: "A" for u in us})
    for t, d in (("RcT", 1.0), ("RcG", 4.0)):
        for u in units:
            for amp in P.AMPS3:
                if not (t == "RcT" and u is units[1] and amp == "ac20"):
                    _judged(root, "panel", t, u["unit"], amp, {P.ANY_HALF: {"B": d}})
    read, weights = C.panel_reader(("RcT", "RcG"))
    rows, cnt = read("RcT", "RcG")
    assert cnt["missing"] == 1 and cnt["directions"] == 6 and cnt["base_dropped"] == 0
    assert len(rows) == 5 and all(v[2] == pytest.approx(math.log(0.25)) for v in rows.values())
    assert set(weights) == {"pd0", "pd1"}


def _judge_all(world, values):
    """Every tag judged on both sets: {tag: distance}."""
    P, root = world["P"], world["root"]
    for t, d in values.items():
        for amp in P.AMPS3:
            for u in world["bks"]:
                _judged(root, "real", t, u["unit"], amp, {P.ANY_HALF: {"A": d, "B": d}})
            if t != "S":
                for u in world["panel"]:
                    _judged(root, "panel", t, u["unit"], amp, {P.ANY_HALF: {"B": d}})
    for u in world["panel"]:
        for amp in P.AMPS3:
            _judged(root, "panel", "S", u["unit"], amp, {P.ANY_HALF: {"B": values["S"]}})


VALUES = {"S": 2.0, "RcG": 3.0, "RcT": 1.0, "RcGn0": 4.0, "RcGn1": 4.0, "RcGn2": 4.0}


def test_the_report_reads_every_row_with_its_sign(world, monkeypatch):
    import json

    P, root = world["P"], world["root"]
    monkeypatch.setattr(P, "panel_halves", lambda us: {u["unit"]: "A" for u in us})
    _judge_all(world, VALUES)
    C.cmd_report(None)
    rep = json.loads((root / "captures" / C.OUT).read_text())
    assert "search recipe" in rep["confounds"][0]
    for name, directions in (("bks", 12), ("panel", 6)):
        r = rep["sets"][name]
        assert r["RcT - RcG_n"]["mean"] == pytest.approx(math.log(0.25))
        assert r["RcT - RcG_n"]["moved"] and r["RcT - RcG_n"]["directions_held"] == directions
        assert r["RcT - S"]["mean"] == pytest.approx(math.log(0.5)) and r["RcT - S"]["directions"] == directions
        assert r["RcG - S"]["mean"] == pytest.approx(math.log(1.5))
        assert r["each_draw"]["RcGn1"]["mean"] == pytest.approx(math.log(0.25))


def test_a_dead_shard_stops_the_report(world, monkeypatch):
    P, root = world["P"], world["root"]
    monkeypatch.setattr(P, "panel_halves", lambda us: {u["unit"]: "A" for u in us})
    _judge_all(world, VALUES)
    gone = next((root / "panel/judge/RcGn2").glob("*.json"))
    gone.unlink()
    with pytest.raises(SystemExit, match="renders missing"):
        C.cmd_report(None)
    assert not (root / "captures" / C.OUT).exists()


def test_a_unit_with_no_lag_stays_out_of_the_bks_directions(world):
    import json

    P, root = world["P"], world["root"]
    _judge_all(world, VALUES)
    d = root / "real/lags"
    d.mkdir()
    (d / f"{world['bks'][0]['unit'].replace('/', '__')}.json").write_text(json.dumps({"lag": None}))
    rows, cnt = C.bks_reader(("RcT", "RcG"))("RcT", "RcG")
    assert cnt["directions"] == 6 and cnt["missing"] == 0 and len(rows) == 6


def test_the_panel_row_uses_the_capped_weights(world, monkeypatch):
    import json

    P, root = world["P"], world["root"]
    monkeypatch.setattr(P, "panel_halves", lambda us: {u["unit"]: "A" for u in us})
    monkeypatch.setattr(P, "panel_weights", lambda us: {"pd0": 3.0, "pd1": 1.0})
    _judge_all(world, VALUES)
    for f in (root / "panel/judge/RcT").glob("pan__u1*.json"):
        r = json.loads(f.read_text())
        r["judge"][P.ANY_HALF]["B"] = 2.0
        f.write_text(json.dumps(r))
    C.cmd_report(None)
    rep = json.loads((root / "captures" / C.OUT).read_text())
    want = (3 * math.log(0.5) + 1 * math.log(1.0)) / 4
    assert rep["sets"]["panel"]["RcT - S"]["mean"] == pytest.approx(want)


def test_the_distance_null_is_two_separate_draws_on_their_own_counts(world, monkeypatch):
    import json

    from learn import arm_a_levers as L
    from learn import knob_ceiling as K

    P, root = world["P"], world["root"]
    monkeypatch.setattr(C, "DISTANCE_DRAWS", 5)
    monkeypatch.setattr(K, "space", lambda amp, S: [_Dim("m", "a", "cont")])
    monkeypatch.setattr(L, "unit", lambda d, x: x["v"])
    monkeypatch.setattr(P, "rc_setting", lambda dims, S, labels: {
        "v": sum(x["i"] for x in labels) / len(labels) / 10 if labels else 0.0})
    cap, _ = C.capture_cells()
    monkeypatch.setattr(C, "capture_cells", lambda: (cap, {r["unit"]: {"creator": r["unit"][-1]} for rs in cap.values() for r in rs}))
    calls, real = [], C.replace_draw
    monkeypatch.setattr(C, "replace_draw", lambda rs, n, name, seed=C.SEED: calls.append((n, name)) or real(rs, n, name, seed))
    C.cmd_distance(None)
    rep = json.loads((root / "captures/centre-distance.json").read_text())
    assert len(rep["rows"]) == 3 and all(len(r["goat_null_q05_50_95"]) == 3 for r in rep["rows"].values())
    assert len(calls) == 3 * 5 * 2 and len({n for _, n in calls}) == len(calls)
    assert {n for n, name in calls if name.startswith("null-a")} == {4}
    assert {n for n, name in calls if name.startswith("null-b")} == {9}
    assert {int(name.split("|")[1]) for _, name in calls} == set(range(C.DRAWS, C.DRAWS + 5))
