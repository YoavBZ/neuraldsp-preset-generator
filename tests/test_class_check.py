"""The class check's declared table, readings, leak guard and features (`learn/class_check.py`,
`docs/family-class-checks-plan.md` part B). The table tests are pure (light CI runner); the feature and classifier
tests skip without numpy or scikit-learn."""
import pytest

from learn import class_check as C


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


# --- the table -------------------------------------------------------------------------------------------------------------

def test_ck_table_is_whole_as_declared():
    C.table_guard()
    for g in C.G_READINGS:
        for r in C.R_READINGS:
            for lk in C.LEAK:
                for i in C.IN_READINGS:
                    code = C.ck_cell(g, r, lk, i)[0]
                    if g == "above" and r == "reads" and lk == "ok":
                        assert code == "CK-reads"
                    elif (g == "below" or r == "stop") and i == "not":
                        assert code == "CK-stop"
                    else:
                        assert code == "CK-between"


def test_the_guard_refuses_a_broken_table(monkeypatch):
    monkeypatch.setattr(C, "CK_TABLE", C.CK_TABLE[:-1])
    with pytest.raises(SystemExit):
        C.table_guard()


def test_a_leak_inflated_pass_is_between():
    assert C.ck_cell("above", "reads", "high", "not")[0] == "CK-between"
    assert C.ck_cell("above", "reads", "high", "above")[0] == "CK-between"


def test_a_stem_trained_pass_keeps_a_stop_open():
    assert C.ck_cell("below", "neither", "ok", "above")[0] == "CK-between"
    assert C.ck_cell("neither", "stop", "ok", "not")[0] == "CK-stop"


def test_redraw_is_offered_only_on_between():
    assert "redraw" in C.ck_cell("neither", "neither", "ok", "not")[1]
    assert all("redraw" not in C.ck_cell(*k)[1] for k in [("above", "reads", "ok", "not"), ("below", "stop", "ok",
                                                                                              "not")])


# --- the readings -----------------------------------------------------------------------------------------------------------

def test_g_reading():
    assert C.g_reading(_iv(0.9, 0.81, 0.95)) == "above"
    assert C.g_reading(_iv(0.7, 0.6, 0.79)) == "below"
    assert C.g_reading(_iv(0.8, 0.75, 0.85)) == "neither"
    assert C.g_reading(_iv(0.8, 0.80, 0.85)) == "neither"             # an end at the bar is not past it


@pytest.mark.parametrize("right,n,want", [(10, 12, "reads"), (9, 12, "neither"), (7, 12, "neither"),
                                          (6, 12, "stop"), (9, 11, "reads"), (8, 11, "neither"),
                                          (7, 11, "neither"), (6, 11, "stop"), (0, 11, "stop")])
def test_r_reading_for_12_and_11_clusters(right, n, want):
    assert C.r_reading(right, n) == want


def test_r_thresholds_as_declared():
    assert C.R_READS == {12: 10, 11: 9} and C.R_STOP == {12: 6, 11: 6} and C.R_DECIDING == "without Drowning"
    assert C.R_CLUSTERS[C.R_DECIDING] == 11


def test_leak_reading():
    assert C.leak_reading({"g_acc": 0.90, "r_acc": 0.80}, {"g_acc": 0.88, "r_acc": 0.80}) == "ok"
    assert C.leak_reading({"g_acc": 0.91, "r_acc": 0.80}, {"g_acc": 0.88, "r_acc": 0.80}) == "high"
    assert C.leak_reading({"g_acc": 0.80, "r_acc": 0.90}, {"g_acc": 0.88, "r_acc": 0.86}) == "high"
    assert C.leak_reading({"g_acc": None, "r_acc": 0.8}, {"g_acc": 0.9, "r_acc": 0.9}) == "high"


def test_clusters_right_a_tie_is_wrong():
    rows = [("a", True), ("a", False), ("b", True), ("b", True), ("b", False), ("c", False)]
    assert C.clusters_right(rows) == (1, 3)


def test_balanced():
    assert C.balanced([("clean", "clean"), ("clean", "crunch"), ("crunch", "crunch")]) == pytest.approx(0.75)


def _row(g, r_right, r_n=11, r_acc=0.8):
    return {"G": {"acc_clusters": g, "majority_share": 0.51}, "R units": {"acc_units": r_acc},
            f"R clusters {C.R_DECIDING}": {"right": r_right, "clusters": r_n}}


def test_outcome():
    good = _iv(0.9, 0.85, 0.95)
    rows = {"T-clean": _row(good, 10), "T-alone": _row(_iv(0.9, 0.82, 0.95), 9), "In-alone": _row(good, 10)}
    assert C.outcome(rows)["code"] == "CK-reads"
    rows["T-alone"] = _row(_iv(0.95, 0.9, 0.99), 9)                    # 0.05 above T-clean: the leak guard
    assert C.outcome(rows)["code"] == "CK-between"
    rows["T-alone"] = _row(_iv(0.7, 0.6, 0.78), 9)
    assert C.outcome(rows)["code"] == "CK-between"                    # In-alone above 0.80 keeps it open
    rows["In-alone"] = _row(_iv(0.8, 0.7, 0.9), 5)
    assert C.outcome(rows)["code"] == "CK-stop"
    rows["T-clean"] = _row(_iv(0.6, 0.45, 0.7), 5)                    # the control fails: no cell
    out = C.outcome(rows)
    assert out["code"] is None and out["control"] == "failed"


# --- the features and the classifier (numpy, scikit-learn) ----------------------------------------------------------------------

def test_features_are_level_free():
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(0)
    mel = rng.integers(40, 180, size=(96, 446)).astype(np.uint8)
    f = C.features(mel)
    assert f.shape == (197,) and np.all(np.isfinite(f))
    g = C.features((mel.astype(np.int16) + 20).astype(np.uint8))   # +10 dB on every cell
    assert np.allclose(f, g, atol=1e-6)


def test_features_active_frames():
    np = pytest.importorskip("numpy")
    mel = np.full((96, 446), 150, np.uint8)
    mel[:, :100] = 0                                               # silent frames, far below the loudest
    mel[:48, 100:] = 160
    f = C.features(mel)
    assert f[96:192].max() == pytest.approx(0.0, abs=1e-9)          # no spread over the active frames


def test_fit_predict_separable():
    np = pytest.importorskip("numpy")
    pytest.importorskip("sklearn")
    x = np.array([[0.0, 1.0], [0.1, 0.9], [1.0, 0.0], [0.9, 0.1]])
    y = ["clean", "clean", "crunch", "crunch"]
    assert C.fit_predict(x, y, [[0.05, 0.95], [0.95, 0.05]]) == ["clean", "crunch"]
