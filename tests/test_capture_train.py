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
    up, span, down = {"lo": 0.01, "hi": 0.2}, {"lo": -0.1, "hi": 0.1}, {"lo": -0.2, "hi": -0.01}
    assert C.reading({"drive": up, "tone": span, "cab": span}) == "the rows help"
    assert C.reading({"drive": down, "tone": span, "cab": span}) == "the rows cost"
    assert C.reading({"drive": up, "tone": down, "cab": span}) == "mixed"
    assert C.reading({"drive": span, "tone": span, "cab": span}) == "undecided"
    assert C.reading({"a": span}) == "undecided"


def test_every_step_needs_its_ledger_entry(monkeypatch):
    from learn import pipeline_fix as P

    def stop(key):
        raise SystemExit(f"no {key}")

    monkeypatch.setattr(P, "require", stop)
    a = type("A", (), {"arm": "C-cap", "fold": 0, "seed": C.SEEDS[0], "out": "x"})
    for cmd in (C.cmd_tune, C.cmd_read):
        with pytest.raises(SystemExit, match="phase_n9"):
            cmd(a)
