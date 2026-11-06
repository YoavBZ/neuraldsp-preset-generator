"""N9's pure parts (`learn/capture_train.py`)."""

import pytest

np = pytest.importorskip("numpy")

from learn import capture_train as C  # noqa: E402


def test_held_dis_are_the_folds_own():
    units = [{"di": "a", "fold": 0}, {"di": "b", "fold": 1}, {"di": "a", "fold": 1}]
    assert C.held_dis(units, 0) == {"a"} and C.held_dis(units, 1) == {"a", "b"}


def test_rows_on_a_held_di_leave():
    units = {"u": {"di": "a"}, "v": {"di": "b"}}
    recs = [{"unit": "u"}, {"unit": "v"}]
    assert C.keep_clear(recs, units, {"a"}) == [{"unit": "v"}]


def test_arms_take_about_the_same_updates():
    up = 590
    assert C.epochs_for(up, 610, 64) == 59
    e = C.epochs_for(up, 900, 64)
    assert abs(e * 15 - up) <= 15
    assert C.epochs_for(1, 900, 64) == 1


def test_the_jackknife_reads_a_cluster_it_can_drop():
    vals = {"a": 0.0, "b": 1.0, "c": 0.0, "d": 1.0}
    stat = lambda drop: float(np.mean([v for k, v in vals.items() if k != drop]))  # noqa: E731
    r = C.jackknife_t(stat, sorted(vals), lambda df: 2.0)
    assert r["point"] == 0.5 and r["lo"] < 0.2 and r["hi"] > 0.8 and r["clusters"] == 4


def test_the_reading():
    up, span, down = {"point": 0.1, "lo": 0.01, "hi": 0.2}, {"point": 0.0, "lo": -0.1, "hi": 0.1}, {"point": -0.1, "lo": -0.2, "hi": -0.01}
    good = {"drive": up, "tone": up, "cab": up}
    assert C.reading({"drive": up, "tone": span, "cab": span}, good) == "a lead"
    assert C.reading({"drive": down, "tone": span, "cab": span}, good) == "a cost to review"
    assert C.reading({"drive": up, "tone": down, "cab": span}, good) == "mixed"
    assert C.reading({"drive": span, "tone": span, "cab": span}, good) == "undecided"
    flat = {"drive": span, "tone": span, "cab": span}
    assert C.reading({"drive": up, "tone": span, "cab": span}, flat) == "moved spread"


def _sources():
    bks = [{"unit": f"b{i}"} for i in range(4)]
    goat = [{"unit": f"g{i}"} for i in range(6)]
    caps = [{"unit": f"c{i}"} for i in range(8)]
    bu = {r["unit"]: {"di": f"bdi{i}"} for i, r in enumerate(bks)}
    gu = {r["unit"]: {"di": f"di{i}"} for i, r in enumerate(goat)}
    cu = {r["unit"]: {"di": f"di{i % 4}", "fold": i % 2} for i, r in enumerate(caps)}
    return bks, bu, goat, gu, caps, cu


def test_a_models_rows_hold_out_its_fold_and_its_dis(monkeypatch):
    from learn import pipeline_fix as P

    def rows(recs, by_unit, row0, label_of=None):
        return [{"i": row0 + j, "real": r["unit"]} for j, r in enumerate(recs)]

    monkeypatch.setattr(P, "record_rows", rows)
    monkeypatch.setattr(P, "REAL_PER_EPOCH", 6)
    monkeypatch.setattr(P, "GOAT_PER_EPOCH", 6)
    monkeypatch.setattr(C, "CAP_PER_EPOCH", 6)
    src = _sources()
    cu, gu = src[5], src[3]
    cu["c1"]["di"] = "di0"                               # a DI shared across folds: c0 held at k=0 takes c1 with it
    for k, survivors in ((0, {"c3", "c5", "c7"}), (1, {"c2", "c6"})):
        ctl, c = C.rows_of("C-ctl", k, src)
        cap, d = C.rows_of("C-cap", k, src)
        new = cap[len(ctl):]
        assert cap[:len(ctl)] == ctl and c["goat"] == d["goat"] and c["capture"] == 0
        assert {r["real"] for r in new} == survivors and len(new) == 6
        assert all(r["i"] >= C.CAP_ROW0 for r in new)
        held = C.held_dis(list(cu.values()), k)
        units = {r["real"] for r in cap}
        assert not any(gu[u]["di"] in held for u in units if u in gu)
    assert C.rows_of("C-c39", 0, src)[0] == C.rows_of("C-ctl", 0, src)[0]


def test_steps_count_what_ran():
    assert C.steps(39, 906, 64) == 39 * 15


def test_every_step_needs_its_ledger_entry(monkeypatch):
    from learn import pipeline_fix as P

    def stop(key):
        raise SystemExit(f"no {key}")

    monkeypatch.setattr(P, "require", stop)
    a = type("A", (), {"arm": "C-cap", "fold": 0, "seed": C.SEEDS[0], "out": "x"})
    for cmd in (C.cmd_tune, C.cmd_read):
        with pytest.raises(SystemExit, match="phase_n9"):
            cmd(a)
