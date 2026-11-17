import pytest

from learn import learnable_targets as T


def _iv(r):
    return ({"lo90": -0.2, "hi90": -0.01} if r == "better" else
            {"lo90": 0.01, "hi90": 0.2} if r == "worse" else {"lo90": -0.1, "hi90": 0.1})


def _rows(**kw):
    return {T.S5_ROWS[k]: {"deciding_pool": _iv(v)} for k, v in kw.items()}


def test_the_outcome_table_holds_each_pair_once_as_declared():
    T.table_guard()
    want = {("better", "better"): "S5-adopt", ("better", "undecided"): "S5-user", ("better", "worse"): "S5-impossible",
            ("undecided", "better"): "S5-build", ("worse", "better"): "S5-build",
            ("undecided", "undecided"): "S5-level", ("worse", "undecided"): "S5-level",
            ("undecided", "worse"): "S5-worse", ("worse", "worse"): "S5-worse"}
    for g in T.READINGS:
        for o in T.READINGS:
            assert sum(g in gs and o in os_ for gs, os_, _, _ in T.S5_TABLE) == 1
            assert T.s5_cell(g, o)[0] == want[(g, o)]
    assert set(T.NOISE_CODES) == {"S5-adopt", "S5-build", "S5-worse"}


def test_the_outcome_reads_g_o_r_and_the_noise_rule():
    got = T.s5_outcome(_rows(G="undecided", O="undecided", R="better"))
    assert got["code"] == "S5-level" and got["sub"] == T.S5_LEVEL_SUB["better"] and got["fires"]
    got = T.s5_outcome(_rows(G="undecided", O="undecided", R="undecided"))
    assert got["sub"] == T.S5_LEVEL_SUB["not better"]
    got = T.s5_outcome(_rows(G="better", O="better", R="undecided", O2="better"))
    assert got["code"] == "S5-adopt" and got["fires"] and got["noise"]["holds"]
    got = T.s5_outcome(_rows(G="better", O="better", R="undecided", O2="undecided"))
    assert not got["fires"] and got["next"] == T.NOISE_HELD
    got = T.s5_outcome(_rows(G="worse", O="better", R="undecided"))               # O2 not rendered: the action is held
    assert got["code"] == "S5-build" and not got["fires"] and got["noise"]["O2"] is None
    got = T.s5_outcome(_rows(G="undecided", O="worse", R="undecided", O2="worse"))
    assert got["code"] == "S5-worse" and got["fires"]
    assert T.s5_outcome(_rows(G="better", O="undecided", R="worse"))["code"] == "S5-user"
    with pytest.raises(SystemExit):
        T.s5_outcome(_rows(G="better", O="worse", R="undecided"))                 # the impossible cell stops
    with pytest.raises(SystemExit):
        T.s5_outcome(_rows(G="better", R="undecided"))                            # a missing action row refuses


def test_the_guard_refuses_a_broken_table(monkeypatch):
    monkeypatch.setattr(T, "S5_TABLE", T.S5_TABLE[:-1])
    with pytest.raises(SystemExit):
        T.table_guard()
    monkeypatch.undo()
    monkeypatch.setattr(T, "S0_TABLE", T.S0_TABLE[1:])
    with pytest.raises(SystemExit):
        T.table_guard()


def test_stage_zeros_cell_takes_the_first_that_holds():
    ok, flat, rise = {"lo90": 0.01, "hi90": 0.03}, {"lo90": -0.002, "hi90": 0.014}, {"lo90": 0.001, "hi90": 0.02}
    assert T.s0_cell(False, True, ok, rise) == "S0-fail"
    assert T.s0_cell(True, False, ok, rise) == "S0-fail"
    assert T.s0_cell(True, True, {"lo90": 0.051, "hi90": 0.07}, rise) == "S0-overfit"
    assert T.s0_cell(True, True, ok, flat) == "S0-flat"
    assert T.s0_cell(True, True, ok, {"lo90": -0.03, "hi90": -0.01}) == "S0-flat"   # below zero is no rise
    assert T.s0_cell(True, True, ok, rise) == "S0-rise"
    with pytest.raises(SystemExit):
        T.s0_cell(True, True, ok, {"lo90": None})


def test_head_rule_is_the_three_declared_parts():
    assert [p for p, _ in T.HEAD_RULE] == ["written", "unwritten", "count"]
    assert "label's training mask" in T.HEAD_RULE[0][1] and "refuses" in T.HEAD_RULE[2][1]


def test_runs_are_the_nine_sets():
    assert len(T.RUNS) == 9 and T.run_split("all") == (None, False)
    assert T.run_split("fold2") == (2, False) and T.run_split("inner3") == (3, True)


def test_pick_margin_nearest_and_ties():
    inf = float("inf")
    ln_s = [1.00, 0.98, 1.02, 1.04, 0.90]
    ok = [True, True, True, True, False]
    assert T.pick(ln_s, ok, [5, 4, 1, 0, 0], 0.05) == 2          # 1.04 is outside 0.98 + 0.05; 0.90 is unusable
    assert T.pick(ln_s, ok, [5, 4, 1, 0, 0], 0.10) == 3
    assert T.pick(ln_s, ok, [1, 1, 1, 9, 0], 0.05) == 1          # a tie: the better search-half score
    assert T.pick([1.0, 1.0], [True, True], [2, 2]) == 0         # then the lower index (the label first)
    with pytest.raises(SystemExit):
        T.pick([inf], [False], [0])


def test_candidates_order_dedup_and_trials_on_the_start():
    out = {"label": {"a/x": "1", "a/y": "2"},
           "fresh": {"label": {"judge": {"A": 2.0, "B": 2.1}}},
           "step2": {"stage_b_settings": {"a/x": "1", "a/y": "2"}, "stage_b": {"judge": {"A": 2.0, "B": 2.0}},
                     "stage_a_settings": {"a/x": "1", "a/y": "3"}, "stage_a": {"judge": {"A": 2.2, "B": 2.2}}},
           "step1": {"start_settings": {"a/x": "0", "a/y": "3"},
                     "trials": [{"x": {"a/x": "1"}, "judge": {"A": 2.3, "B": 2.4}},
                                {"x": {"a/x": "5"}, "judge": {"A": 2.5, "B": 2.6}}]}}
    c = T.candidates(out)
    assert [(k, i) for k, i, _, _ in c] == [("label", 0), ("stage_a", 0), ("step1", 1)]   # B and trial 0 repeat
    assert c[0][3] == {"A": 2.0, "B": 2.1} and c[2][2] == {"a/x": "5", "a/y": "3"}
    assert T.usable({"A": 1.0, "B": 2.0}, "A", "B") and not T.usable({"A": 1.0, "B": float("inf")}, "A", "B")


def test_version_spread_pairs():
    a = {("s1", "clean", "v1", "pr12"): {"h": 0.1}, ("s1", "clean", "v2", "pr12"): {"h": 0.3},
         ("s2", "clean", "v1", "pr12"): {"h": 0.6}, ("s3", "crunch", "v1", "pr12"): {"h": 0.9},
         ("s1", "clean", "v1", "ac20"): {"h": 0.0}}
    sp = T.version_spread(a)
    assert sp["within_song"] == [pytest.approx(0.2)]
    assert sp["between_songs"] == [pytest.approx(0.5)]           # s1 and s2 on v1; s3 is another class
    assert T.rms({"h": 0.0, "g": 1.0}, {"h": 0.3}) == pytest.approx(0.3)


def test_distances_rows_and_counts():
    np = pytest.importorskip("numpy")
    C = np.array([[0.5, 0.5], [0.9, 0.1]])
    CM = np.array([[1, 1], [1, 0]], np.float32)
    S = np.array([[1.0], [0.0]])
    SM = np.ones((2, 1), np.float32)
    K = np.array([[2], [3]])
    KM = np.ones((2, 1), np.float32)
    cen = (np.array([0.5, 0.0]), np.array([1, 1], np.float32), np.array([1.0]), np.ones(1, np.float32),
           np.array([2]), np.ones(1, np.float32))
    w = (np.array([1, 1], np.float32), np.array([1], np.float32), np.array([0], np.float32))
    d = T.distances((C, CM, S, SM, K, KM), cen, w)
    assert d[0] == pytest.approx(0.25) and d[1] == pytest.approx(0.16 + 1.0)   # the silent head and the unwritten mic out
    lab = (np.array([0.2, 0.4], np.float32), np.array([1, 1], np.float32), np.array([1.0], np.float32),
           np.array([1], np.float32), np.array([4]), np.array([1], np.float32))
    cand = (np.array([0.9, 0.1], np.float32), np.array([1, 0], np.float32), np.array([0.0], np.float32),
            np.array([1], np.float32), np.array([3]), np.array([1], np.float32))
    row, cnt = T.target_row(lab, cand, w)
    assert list(row[0]) == pytest.approx([0.9, 0.1]) and list(row[2]) == [0.0] and list(row[4]) == [4]   # mic unwritten
    for i in (1, 3, 5):
        assert list(row[i]) == list(lab[i])                       # every mask is the label's
    assert cnt["cont"]["trained_silent_in_target"] == 1 and cnt["cont"]["sounding_untrained"] == 0
    hc = T.head_counts([(lab, 3), (row, 2)])
    assert list(hc[0]) == [5, 5] and list(hc[2]) == [5]
    assert T.rails([0.0, 0.5, 1.0], [1, 1, 0], [0, 1, 2]) == (1, 2)


def test_readout_sees_a_rise_and_a_flat():
    import random

    rng = random.Random(1)
    vals = []
    for cl in range(30):
        for h in range(4):
            lab = rng.gauss(0, 1)
            tgt = rng.gauss(0, 1)
            ans = 0.8 * tgt + 0.2 * rng.gauss(0, 1)              # the answers follow the targets
            vals.append((("pr12", "clean", f"h{h}"), cl, ans, lab, tgt))
    r = T.readout(vals, n_boot=300)
    assert r["diff"] > 0 and r["lo90"] > 0 and r["clusters"] == 30
    same = [(c, k, a, l_, l_) for c, k, a, l_, _ in vals]           # targets equal to labels: no difference
    r = T.readout(same, n_boot=300)
    assert r["diff"] == pytest.approx(0.0) and r["lo90"] <= 0 <= r["hi90"]
    assert T.readout([(("a", "c", "h"), 1, 0.1, 0.2, 0.3)])["values"] == 0     # a cell under MIN_CELL drops
