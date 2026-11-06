"""The frozen reads' small parts (`learn/eat_read.py`), on made-up statistics."""
import pytest

np = pytest.importorskip("numpy")

from learn import eat_read as R


def test_the_declared_family_is_42_contrasts_and_no_pair_twice():
    f = R.family_of()
    assert len(f) == 42 and len(set(f)) == 42
    assert {q[2] for q in f} == set(R.GROUP_NAMES)
    assert all(not q[3] for q in f)


def test_each_candidate_meets_its_two_references():
    f = R.family_of()
    for c in ("E-top", "E-mid", "E-mix"):
        assert {q[1] for q in f if q[0] == c} == {"FTM", "M-pcs"}
    for c in ("PE-top", "PE-mid", "PE-mix"):
        assert {q[1] for q in f if q[0] == c} == {"W", "P-pcs"}


def test_the_same_count_mel_readers_meet_the_models():
    f = R.family_of()
    assert {q[1] for q in f if q[0] == "M-pcs"} == {"FTM"} and {q[1] for q in f if q[0] == "P-pcs"} == {"W"}


def test_candidates_carry_the_chosen_mid_and_their_training_set():
    c = R.candidates("f6")
    assert c["E-mid"] == ("f6", "ridge", "real") and c["PE-mix"] == ("mix:f6", "ridge", "plugin")
    assert c["PE-top"][0] == "top"


def test_top_reads_the_last_layer():
    assert R.stat_of("top") == "g16" and R.stat_of("f6") == "f6"


def test_scaling_leaves_a_dead_channel_finite():
    v = R.scaled(np.array([[2.0, 0.0]]), np.array([2.0, 0.0]))
    assert v[0, 0] == 1.0 and np.isfinite(v).all()


def test_merged_joins_answers_and_refuses_other_rows():
    a = [{"rec": 1, "x_ans": 1}, {"rec": 2, "x_ans": 2}]
    b = [{"rec": 1, "y_ans": 3}, {"rec": 2, "y_ans": 4}]
    got = R.merged([a, b])
    assert got[1] == {"rec": 2, "x_ans": 2, "y_ans": 4}
    with pytest.raises(SystemExit):
        R.merged([a, [{"rec": 9, "y_ans": 3}, {"rec": 2, "y_ans": 4}]])


def fake_split():
    rows = [{"i": i} for i in range(8)]
    folds = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    sess = {(i, k): ("a" if (i + k) % 2 == 0 else "b") for i in range(8) for k in range(4)}
    return rows, folds, sess, {"a": 0, "b": 1}


def test_held_rows_read_held_sessions_and_training_leaves_them_out():
    rows, folds, sess, sfold = fake_split()
    tr, trf, te, tef = R.backed_files(rows, folds, sess, sfold, 0)
    assert te == [0, 1, 2, 3] and tr == [4, 5, 6, 7]
    assert all(sfold[sess[key]] == 0 for _, key in tef)
    assert all(sfold[sess[key]] != 0 for fs in trf for _, key in fs)
    assert all(len(fs) == R.TRAIN_VARIANTS for fs in trf)


def test_a_row_with_no_eligible_backing_is_left_out():
    rows, folds, sess, sfold = fake_split()
    sess = {q: "a" for q in sess}
    tr, _, te, _ = R.backed_files(rows, folds, sess, sfold, 1)      # no session is held in fold 1
    assert tr == [0, 1, 2, 3] and te == []
    tr, _, te, _ = R.backed_files(rows, folds, sess, sfold, 0)      # every session is held in fold 0
    assert tr == [] and te == [0, 1, 2, 3]


def test_clean_files_hold_a_whole_fold():
    rows, folds, _, _ = fake_split()
    tr, trf, te, tef = R.clean_files(rows, folds, 1)
    assert tr == [0, 1, 2, 3] and te == [4, 5, 6, 7]
    assert trf[0] == [("clean", (0, -1))] and tef[0] == ("clean", (4, -1))


def test_auc_is_one_when_positives_score_higher_and_a_half_on_ties():
    assert R.auc(np.array([3.0, 2.0, 1.0, 0.0]), np.array([1, 1, -1, -1])) == 1.0
    assert R.auc(np.zeros(4), np.array([1, 1, -1, -1])) == 0.5


def test_a_level_matched_copy_is_at_the_reference_level():
    from learn import eat_judge as J

    ref = np.ones(100)
    lufs = lambda y: 20 * np.log10(np.abs(y).mean())    # noqa: E731
    assert lufs(J.level_matched(ref, 0.1 * ref, lufs)) == pytest.approx(0.0, abs=1e-9)


def test_deep_distance_is_in_units_of_each_dimensions_sd():
    from learn import eat_judge as J

    assert J.distance(np.array([1.0, 2.0]), np.array([3.0, 2.0]), np.array([2.0, 1.0])) == pytest.approx(0.5)
    assert J.distance(np.zeros(2), np.zeros(2), np.zeros(2)) == 0.0


def test_block_pca_keeps_each_blocks_own_components():
    x = np.random.default_rng(0).normal(size=(50, 6)) * np.array([9.0, 9.0, 9.0, 0.1, 0.1, 0.1])
    m, c = R.block_pca(x, 3, 2)
    assert c.shape == (4, 6)
    assert np.allclose(c[:2, 3:], 0.0) and np.allclose(c[2:, :3], 0.0)
    assert np.allclose(np.linalg.norm(c, axis=1), 1.0)
    assert np.allclose(m, x.mean(0))


def test_block_pca_takes_several_blocks():
    x = np.random.default_rng(1).normal(size=(40, 9))
    _, c = R.block_pca(x, (3, 6), 2)
    assert c.shape == (6, 9)
    assert np.allclose(c[:2, 3:], 0.0) and np.allclose(c[2:4, :3], 0.0) and np.allclose(c[2:4, 6:], 0.0) and np.allclose(c[4:, :6], 0.0)


def test_tuned_family_is_24_contrasts():
    f = R.tuned_family()
    assert len(f) == 24 and len(set(f)) == 24
    assert {q[1] for q in f} == {"E-mix", "W-pcs"}


def test_by_seed_averages_answers_and_passes_a_missing_swap_on():
    rows = [{"X-1_ans": np.array([1.0]), "X-2_ans": np.array([3.0]), "X-1_swap": np.array([0.0]), "X-2_swap": None}]
    R.by_seed(rows, ["X"], (1, 2), lambda q: q)
    assert rows[0]["X_ans"][0] == 2.0 and rows[0]["X_swap"] is None
