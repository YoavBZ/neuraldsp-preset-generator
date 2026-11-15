"""S1 Amendment 3 and S3's pure parts: steering, the hint, the training draw and the crop rule (no numpy)."""

import math
import random

from learn import sep_s0 as S0
from learn import sep_s3 as S3
from learn import sep_s3_train as TR


def test_theta_matches_the_pan_law():
    for p in (-1.0, -0.4, 0.0, 0.3, 1.0):
        gl, gr = S0.pan(p)
        assert math.isclose(math.cos(S3.theta(p)), gl) and math.isclose(math.sin(S3.theta(p)), gr)


def test_steering_centres_the_hinted_source():
    for p in (-0.9, -0.5, 0.0, 0.7, 1.0):
        gl, gr = S0.pan(p)
        L, R = S3.rotate(gl, gr, S3.steer_phi(p))
        assert math.isclose(L, R, abs_tol=1e-12) and L > 0


def test_a_source_on_the_far_side_turns_anti_phase():
    gl, gr = S0.pan(-1.0)                       # hard left, steered to hard right's centre
    L, R = S3.rotate(gl, gr, S3.steer_phi(1.0))
    assert math.isclose(L, -R, abs_tol=1e-12)


def test_rotation_is_undone_exactly():
    L, R = S3.rotate(0.3, -0.8, 0.61)
    L2, R2 = S3.rotate(L, R, -0.61)
    assert math.isclose(L2, 0.3) and math.isclose(R2, -0.8)


def test_coarse_hint():
    assert S3.coarse(0.1) == 0.0 and S3.coarse(-0.24) == 0.0
    assert S3.coarse(0.25) == S3.HINT_SIDE and S3.coarse(-0.9) == -S3.HINT_SIDE


def test_hint_of_takes_the_first_copy():
    meta = {"target": [0.8, -0.7]}
    assert S3.hint_of(meta) == S3.HINT_SIDE and S3.hint_of(meta, exact=True) == 0.8


def test_steered_stem_level_is_the_rotated_back_mean():
    phi = S3.steer_phi(0.7)
    m = 0.5                                     # a centred steered source [m, m]
    L, R = S3.rotate(m, m, -phi)
    assert math.isclose(S3.steered_stem(m, phi), (L + R) / 2)


def test_draw_layout_strata_and_apartness():
    rng = random.Random(1)
    seen = {}
    for _ in range(4000):
        lay = TR.draw_layout(rng)
        seen[lay["stratum"]] = seen.get(lay["stratum"], 0) + 1
        t = lay["target"]
        assert all(-1 <= p <= 1 for p in t + [lay["others"], lay["amp"]])
        if lay["stratum"] == "double":
            assert len(t) == 2 and t[0] * t[1] < 0 and 8 <= lay["offset_ms"] <= 30 and -4 <= lay["db2"] <= 0
        else:
            assert len(t) == 1
        if lay["stratum"] == "split":
            assert abs(t[0]) <= 0.15 and lay["partner"] * lay["others"] < 0
        if lay["stratum"] == "off-centre":
            assert abs(t[0]) >= 0.35
    for name, w in TR.STRATA_P:
        assert abs(seen[name] / 4000 - w) < 0.03


def test_pick_crop_finds_the_active_part():
    n, crop, pre = 400, 50, 20
    target = [0.0] * 200 + [1.0] * 200          # the target plays in the second half only
    mix = [1.0] * n
    a = TR.pick_crop(target, mix, random.Random(3), n_try=40, crop=crop, pre=pre, active_db=10.0)
    assert a >= 200 and a + crop <= n


def test_hint_from_jitters_around_the_coarse_hint():
    rng = random.Random(5)
    for _ in range(200):
        h = TR.hint_from({"target": [0.6]}, rng)
        assert abs(h - S3.HINT_SIDE) <= TR.HINT_JITTER


def test_steered_pan():
    assert math.isclose(S3.steered_pan(0.7, 0.7), 0.0, abs_tol=1e-12)
    assert math.isclose(S3.steered_pan(0.0, 0.0), 0.0, abs_tol=1e-12)
    assert S3.steered_pan(0.4, 0.7) < 0 < S3.steered_pan(1.0, 0.7)


def test_hint_for_each_option():
    meta = {"target": [0.5]}
    assert S3.hint_for(meta, "steer_mdxc") == S3.HINT_SIDE
    assert S3.hint_for(meta, "steer_mdxc_h1") == S3.HINT_H1
    assert S3.hint_for(meta, "steer_mdxc_exact") == 0.5
    assert S3.hint_for({"target": [0.1]}, "steer_mdxc_h1") == 0.0


def test_the_bands_are_disjoint():
    assert not set(S3.TRAIN_BANDS) & set(S3.HELD_BANDS)
    assert S3.VAL_BAND in S3.TRAIN_BANDS


def test_routed_comparator():
    assert S3.routed({"target": [0.1]}) == "xlst_mdxc" and S3.routed({"target": [-0.6]}) == "side"


def test_s3_reads_a_side_hint_against_steer_xlmdxc():
    assert S3.routed({"target": [0.1]}, "s3") == "xlst_mdxc"
    assert S3.routed({"target": [-0.6]}, "s3") == "steer_xlmdxc"


def test_s3_decision():
    up, flat, down = {"lo90": 0.2, "hi90": 1.0}, {"lo90": -0.3, "hi90": 0.4}, {"lo90": -1.0, "hi90": -0.1}
    assert S3.s3_decision(up, up, up, flat) == "default"
    assert S3.s3_decision(up, up, flat, flat) == "picker choice"
    assert S3.s3_decision(up, up, up, down) == "not used"
    assert S3.s3_decision(up, flat, up, up) == "not used"
    assert S3.s3_decision(up, {"lo90": None, "hi90": None}, up, up) == "not read"


def test_s3_decision_clearly_worse_is_not_a_picker_choice():
    up, flat, down = {"lo90": 0.2, "hi90": 1.0}, {"lo90": -0.3, "hi90": 0.4}, {"lo90": -1.0, "hi90": -0.1}
    assert S3.s3_decision(up, up, down, flat) == "not used"


def test_the_weaker_cell_decides_the_centre_hint():
    assert min("default", "picker choice", key=S3.ORDER.index) == "picker choice"


# --- Amendment 3d: the checkpoint, chosen with the read ------------------------------------------------------------------

def _ev(step, med, read):
    return {"step": step, "si_sdr_median": med, "read": read}


RUN = [_ev(0, -6.78, 0.1923), _ev(1000, 5.75, 0.1364), _ev(2000, 5.89, 0.1318), _ev(3000, 6.07, 0.1377),
       _ev(4000, 6.14, 0.1369), _ev(5000, 6.63, 0.1364), _ev(6000, 6.58, 0.1191)]


R0 = 0.1923


def test_pick_takes_the_lowest_read_within_the_bar():
    assert TR.pick_step(RUN, {5000, 6000}, R0) == 6000        # 0.05 dB under the best, the read 0.017 lower


def test_pick_ignores_a_checkpoint_more_than_the_bar_below_the_best():
    assert TR.pick_step(RUN, {2000, 5000}, R0) == 5000        # 2000 reads better but is 0.74 dB under


def test_pick_counts_only_kept_weights():
    assert TR.pick_step(RUN, {5000}, R0) == 5000
    assert TR.pick_step(RUN, {1000, 3000}, R0) is None


def test_pick_needs_a_read_no_worse_than_step_0():
    evals = [_ev(0, 1.0, 0.10), _ev(1000, 1.05, 0.12), _ev(2000, 0.5, 0.05)]
    assert TR.pick_step(evals, {1000, 2000}, 0.10) is None
    assert TR.pick_step(evals, {0, 1000}, 0.10) == 0


def test_an_ineligible_evaluation_doesnt_set_the_window():
    # the review's case: a higher median with a read worse than step 0's must not shut the others out
    assert TR.pick_step(RUN + [_ev(7000, 6.90, 0.20)], {5000, 6000, 7000}, R0) == 6000


def test_the_window_is_strict():
    evals = [_ev(0, 0.0, 0.2), _ev(1000, 3.0, 0.15), _ev(2000, 2.75, 0.1)]
    assert TR.pick_step(evals, {1000, 2000}, 0.2, min_gain=0.25) == 1000    # exactly the bar under: beaten


def test_pick_breaks_a_read_tie_by_the_earlier_step():
    evals = [_ev(0, 0.0, 0.2), _ev(1000, 3.0, 0.1), _ev(2000, 3.05, 0.1)]
    assert TR.pick_step(evals, {1000, 2000}, 0.2) == 1000


def test_candidates_add_best_only_where_no_file_is_kept():
    assert TR.candidates({}, 5000, "best") == {5000: "best"}
    assert TR.candidates({6000: "k6"}, 5000, "best") == {6000: "k6", 5000: "best"}
    assert TR.candidates({5000: "k5"}, 5000, "best") == {5000: "k5"}


def test_stop_reason():
    t0 = 1_000_000.0
    st = {"best_step": 5000, "t_start": t0, "evals": RUN, "reloads": 0}
    more = lambda n: {**st, "evals": RUN + [_ev(7000 + 1000 * j, 6.0, 0.12) for j in range(n)]}
    assert TR.stop_reason(st, t0 + 3600) is None
    assert TR.stop_reason(more(3), t0 + 3600) is None                       # 4 after the best
    assert TR.stop_reason(more(4), t0 + 3600) == "patience"                 # 5 after the best
    assert TR.stop_reason({**st, "reloads": TR.MAX_RELOADS}, t0 + 3600) is None
    assert TR.stop_reason({**st, "reloads": TR.MAX_RELOADS + 1}, t0 + 3600) == "abort"
    assert TR.stop_reason(st, t0 + TR.MAX_HOURS * 3600) is None
    assert TR.stop_reason(st, t0 + (TR.MAX_HOURS + 0.1) * 3600) == "hours"
    assert TR.stop_reason(st, t0 + 3600, user_stop=True) == "user"
