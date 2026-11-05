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
    assert C.direction_value(None, "a", "b", 1, value) == pytest.approx(math.log(0.25))
    assert C.direction_value(None, "a", "b", 2, value) is None
    assert C.direction_value(None, "a", "b", 3, value) is None
    assert C.direction_value(None, "a", "b", 4, value) == 0
    assert C.direction_value(None, "a", "S", 1, value) == pytest.approx(math.log(0.5))


def test_a_row_moves_only_when_it_clears_zero_and_the_draws_agree():
    clear = {"mean": -0.1, "lo90": -0.2, "hi90": -0.01}
    assert C.moved(clear, [-0.1, -0.2, -0.05])
    assert not C.moved(clear, [-0.1, 0.02, -0.05])
    assert not C.moved({"mean": -0.1, "lo90": -0.2, "hi90": 0.01}, [-0.1, -0.2, -0.05])
    assert not C.moved({"mean": -0.1, "lo90": None, "hi90": None}, [-0.1, -0.2, -0.05])
    assert C.moved({"mean": 0.1, "lo90": 0.01, "hi90": 0.2}, [0.1, 0.2, 0.05])


def test_the_mean_row_keeps_directions_every_draw_holds():
    a = {1: ("d1", "u1", -0.2), 2: ("d1", "u2", 0.4)}
    b = {1: ("d1", "u1", -0.4)}
    assert C.mean_rows([a, b]) == {1: ("d1", "u1", pytest.approx(-0.3))}


def test_the_panel_read_must_be_counted_first():
    assert not C.panel_counted({"phase_5d_panel_reads": "1 (2026-11-01: RG, centres)"})
    assert C.panel_counted({"phase_5d_panel_reads": "2 (2026-11-06: RcT)"})
    assert not C.panel_counted({})


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
