"""N10's pure parts (`learn/reads_fresh.py`)."""

import pytest

np = pytest.importorskip("numpy")

from learn import reads_fresh as F  # noqa: E402


def test_a_label_is_averaged_over_its_fold_models():
    a = [{"amp": "ac20", "x_ans": np.array([0.0, 2.0]), "x_swap": np.array([1.0])}, {"amp": "pr12", "x_ans": np.array([1.0, 1.0]), "x_swap": None}]
    b = [{"amp": "ac20", "x_ans": np.array([2.0, 0.0]), "x_swap": np.array([3.0])}, {"amp": "pr12", "x_ans": np.array([3.0, 3.0]), "x_swap": None}]
    got = F.mean_folds([a, b], "x")
    assert got[0]["x_ans"].tolist() == [1.0, 1.0] and got[0]["x_swap"].tolist() == [2.0]
    assert got[1]["x_ans"].tolist() == [2.0, 2.0] and got[1]["x_swap"] is None


def test_the_set_reads_as_one_fold():
    assert {r["fold"] for r in F.one_fold([{"fold": 2}, {"fold": 3}])} == {0}


def test_the_primary_pairs_are_the_capture_rows():
    assert F.PAIRS[0] == ("C-cap", "C-ctl") and F.PAIRS[1] == ("M-cap", "M-ctl")


def test_the_decision_follows_the_two_pairs():
    assert F.decide("a lead", "undecided").startswith("train on both")
    assert F.decide("undecided", "a lead").startswith("the ridge")
    assert F.decide("a lead", "a cost to review").startswith("train on both")
    assert F.decide("a cost to review", "undecided").startswith("no new training: review")
    assert F.decide("undecided", "mixed") == "no new training on captures from this read"


def test_a_held_di_or_a_doubled_record_stops_the_ridge(monkeypatch):
    from learn import eat_read as ER
    from learn import pipeline_fix as P
    from learn import trusted_data_t3 as T3

    def rows(recs, by_unit, row0, label_of=None):
        return [{"i": row0 + j, "real": r["unit"], "amp": r["amp"], "cls": "clean", "label": {}} for j, r in enumerate(recs)]

    calls = []
    monkeypatch.setattr(P, "record_rows", rows)
    monkeypatch.setattr(T3, "encode_for", lambda arm: lambda label: (np.zeros(3), np.ones(3)))
    monkeypatch.setattr(ER, "fit_predict", lambda *a, **k: calls.append(k["held"]) or (np.zeros((1, 3)), None))
    brecs, bu = [{"unit": "b", "amp": "ac20"}], {"b": {"di": "bdi"}}
    grecs, gu = [{"unit": "g", "amp": "ac20"}], {"g": {"di": "gdi"}}
    caps, cu = [{"unit": "c", "amp": "ac20"}], {"c": {"di": "cdi"}}
    src = (brecs, bu, grecs, gu, caps, cu)
    held = [{"real": "h"}]
    got = F.ridge_answers(held, src, {"h": {"di": "new"}})
    assert set(got) == {"M-ctl", "M-ctl-25", "M-cap", "M-cap-25"} and calls == [1, 25, 1, 25]
    with pytest.raises(SystemExit, match="held DI"):
        F.ridge_answers(held, src, {"h": {"di": "cdi"}})
    with pytest.raises(SystemExit, match="one row per"):
        F.ridge_answers(held, (brecs * 2, bu, grecs, gu, caps, cu), {"h": {"di": "new"}})

