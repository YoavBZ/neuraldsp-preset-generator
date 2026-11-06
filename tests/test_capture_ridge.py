"""N9b's pure parts (`learn/capture_ridge.py`)."""

import pytest

np = pytest.importorskip("numpy")

from learn import capture_ridge as C  # noqa: E402


def test_each_labelled_record_counts_once_and_a_units_amps_all_stay():
    rows = [{"real": "a", "amp": "ac20", "i": 1}, {"real": "a", "amp": "pr12", "i": 2}, {"real": "a", "amp": "ac20", "i": 3}]
    assert [r["i"] for r in C.unique_rows(rows)] == [1, 2]


def test_a_fit_gets_one_row_per_record_and_no_held_unit(monkeypatch):
    from learn import eat_read as ER
    from learn import pipeline_fix as P
    from learn import trusted_data_t3 as T3

    bks = [{"unit": f"b{i}", "amp": a} for i in range(2) for a in ("ac20", "pr12")]
    goat = [{"unit": f"g{i}", "amp": "ac20"} for i in range(6)]
    caps = [{"unit": f"c{i}", "amp": "ac20", "rig": f"r{i}"} for i in range(8)]
    bu = {f"b{i}": {"di": f"bdi{i}", "section": "s", "band": "b", "cls": "clean"} for i in range(2)}
    gu = {f"g{i}": {"di": f"di{i}", "section": "s", "band": "b", "cls": "clean"} for i in range(6)}
    cu = {f"c{i}": {"di": f"di{i % 4}", "fold": i % 2, "section": "s", "band": "b", "cls": "clean"} for i in range(8)}

    def rows(recs, by_unit, row0, label_of=None):
        return [{"i": row0 + j, "real": r["unit"], "amp": r["amp"], "cls": "clean", "label": {"n": j}} for j, r in enumerate(recs)]

    seen = []

    def fit(rows_tr, clusters, units_tr, rows_te, units_te, Y, rep, pcs, held=1):
        seen.append((list(units_tr), list(clusters), list(units_te), rep, pcs, held))
        return np.zeros((len(rows_te), 3)), None

    monkeypatch.setattr(P, "record_rows", rows)
    monkeypatch.setattr(P, "REAL_PER_EPOCH", 6)
    monkeypatch.setattr(P, "GOAT_PER_EPOCH", 6)
    monkeypatch.setattr(C.CT, "CAP_PER_EPOCH", 6)
    monkeypatch.setattr(ER, "fit_predict", fit)
    monkeypatch.setattr(T3, "encode_for", lambda arm: lambda label: (np.zeros(3), np.ones(3)))
    src = (bks, bu, goat, gu, caps, cu)
    held = [r for r in caps if cu[r["unit"]]["fold"] == 0]
    got = C.fold_answers(0, src, held, cu)
    assert len(got) == len(held) and all({"M-ctl_ans", "M-cap_ans", "M-ctl-25_ans", "M-cap-25_ans"} <= set(v) for v in got.values())
    assert [s_[5] for s_ in seen] == [1, 25, 1, 25] and all(s_[3:5] == ("mel", C.PCS) for s_ in seen)
    assert seen[0][0].count("b0") == 2                      # both of a BKS unit's amps
    assert not set(seen[2][0]) & {r["unit"] for r in held}
    assert not set(seen[2][1]) & {cu[r["unit"]]["di"] for r in held}


def test_answers_join_by_recording_and_amp_or_refuse():
    rows = [{"rec": "r", "amp": "ac20"}]
    key = lambda r: (r["rec"], r["amp"])  # noqa: E731
    assert C.join_answers(rows, key, {("r", "ac20"): {"M-cap_ans": 1}})[0]["M-cap_ans"] == 1
    with pytest.raises(SystemExit, match="no answer"):
        C.join_answers(rows, key, {})


def test_the_arms_are_n9s_rows():
    assert set(C.ARMS.values()) <= set(C.CT.ARMS)
