"""S4's pure parts: the best rule, the stop check, the crop and the curve's strata (no numpy)."""

import random

from learn import sep_s3 as S3
from learn import sep_s4_train as S4

EV0 = {"si_sdr_median": 7.0, "read": 0.100}


def test_a_new_best_needs_the_read_gain():
    best = {"si_sdr_median": 7.0, "read": 0.100}
    assert S4.is_better({"si_sdr_median": 7.0, "read": 0.098}, best, EV0)
    assert not S4.is_better({"si_sdr_median": 7.5, "read": 0.0985}, best, EV0)      # under the 0.002 gain
    assert not S4.is_better({"si_sdr_median": 7.5, "read": 0.101}, best, EV0)


def test_a_new_best_needs_a_median_no_lower_than_step_0():
    best = {"si_sdr_median": 7.2, "read": 0.090}
    assert S4.is_better({"si_sdr_median": 7.0, "read": 0.080}, best, EV0)           # at step 0's median
    assert not S4.is_better({"si_sdr_median": 6.99, "read": 0.050}, best, EV0)


def test_stop_reason():
    st = {"evals": [{"step": s} for s in (0, 1000, 2000)], "best_step": 0, "reloads": 0, "t_start": 0.0}
    assert S4.stop_reason(st, 3600.0) is None
    assert S4.stop_reason(st, 3600.0, user_stop=True) == "user"
    st["evals"] += [{"step": s} for s in (3000, 4000, 5000)]
    assert S4.stop_reason(st, 3600.0) == "patience"
    st["best_step"] = 5000
    assert S4.stop_reason(st, (S4.MAX_HOURS + 1) * 3600) == "hours"
    st["reloads"] = S4.MAX_RELOADS + 1
    assert S4.stop_reason(st, 3600.0) == "abort"


def test_crop_lands_where_the_target_plays():
    n, crop = 10_000, 1_000
    target = [0.0] * n
    for i in range(6_000, 7_500):
        target[i] = 1.0
    mix = [1.0] * n
    rng = random.Random(3)
    for _ in range(20):
        a = S4.crop_start(target, mix, rng, silent=False, crop=crop)
        assert 0 <= a <= n - crop
    hits = sum(5_000 < S4.crop_start(target, mix, random.Random(k), silent=False, crop=crop) < 7_500
               for k in range(40))
    assert hits >= 30


def test_a_silent_draw_crops_anywhere_in_range():
    rng = random.Random(5)
    starts = [S4.crop_start([0.0] * 5_000, [1.0] * 5_000, rng, silent=True, crop=1_000) for _ in range(50)]
    assert all(0 <= a < 4_000 for a in starts) and len(set(starts)) > 10


def test_the_curve_reads_the_non_doubles():
    metas = [{"stratum": s} for s in ("centred", "double", "off-centre", "double", "centred")]
    assert S4.non_double(metas) == [0, 2, 4]


def test_s4_reads_against_the_same_routed_comparators_as_s3():
    centre, side = {"target": [0.1]}, {"target": [0.6]}
    assert S3.routed(centre, "s4") == "xlst_mdxc" and S3.routed(side, "s4") == "steer_xlmdxc"
    assert S3.routed(side, "s3") == "steer_xlmdxc" and S3.routed(side, "a3") == "side"


def test_the_crop_is_the_models_chunk():
    assert S4.CROP == 130_560
