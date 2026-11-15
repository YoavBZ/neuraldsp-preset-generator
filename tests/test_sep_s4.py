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


def test_paired_gain_lo90():
    base = [0.10 + 0.001 * (k % 7) for k in range(60)]
    better = [b - 0.01 for b in base]
    assert S4.paired_gain_lo90(base, better) > 0.009
    assert S4.paired_gain_lo90(base, base) == 0.0
    noisy = [b + (0.02 if k % 2 else -0.02) for k, b in enumerate(base)]      # no net gain
    assert S4.paired_gain_lo90(base, noisy) < 0


def test_step_0_picked_is_not_used():
    st = {"best_step": 0, "ev0": {"reads": [0.1, 0.2]}, "best": {"reads": [0.1, 0.2]}}
    assert S4.pick_verdict(st) == (False, None)


def test_a_pick_needs_a_decided_validation_read_gain():
    r0 = [0.10 + 0.002 * (k % 5) for k in range(40)]
    st = {"best_step": 3000, "ev0": {"reads": r0}, "best": {"reads": [r - 0.004 for r in r0]}}
    ok, lo = S4.pick_verdict(st)
    assert ok and lo > 0
    st["best"]["reads"] = [r + (0.03 if k % 2 else -0.032) for k, r in enumerate(r0)]
    assert not S4.pick_verdict(st)[0]


def _ci(lo, hi):
    return {"lo90": lo, "hi90": hi}


def test_s4_picker_choice_needs_a_decided_read_gain():
    win = _ci(1.0, 3.0)
    undecided, level = _ci(-0.5, 0.5), _ci(-0.01, 0.02)
    assert S3.trained_decision("s3", win, win, undecided, level) == "picker choice"
    assert S3.trained_decision("s4", win, win, undecided, level) == "not used"
    assert S3.trained_decision("s4", win, win, undecided, _ci(0.004, 0.02)) == "picker choice"
    assert S3.trained_decision("s4", win, win, _ci(0.2, 1.0), level) == "default"   # S3's default rule unchanged


def _ch(d3, d4, r3=None, r4=None):
    return S3.choose({"s3": d3, "s4": d4, "s3ens": "not used"}, {"s3": r3, "s4": r4})


def test_choose_one_qualifies_keeps_its_own_outcome():
    assert _ch("default", "not used", 0.1) == {"default": "s3", "picker": ["s3"]}
    assert _ch("not used", "picker choice", None, 0.1) == {"default": None, "picker": ["s4"]}
    assert _ch("not used", "not used") == {"default": None, "picker": []}


def test_choose_a_default_beats_a_picker_choice():
    assert _ch("picker choice", "default", 0.08, 0.10) == {"default": "s4", "picker": ["s4", "s3"]}
    assert _ch("default", "picker choice", 0.10, 0.08) == {"default": "s3", "picker": ["s3", "s4"]}


def test_choose_at_one_level_the_lower_read_wins():
    assert _ch("default", "default", 0.100, 0.099) == {"default": "s4", "picker": ["s4", "s3"]}
    assert _ch("default", "default", 0.100, 0.103) == {"default": "s3", "picker": ["s3", "s4"]}
    assert _ch("picker choice", "picker choice", 0.1, 0.096) == {"default": None, "picker": ["s4", "s3"]}
    assert _ch("default", "default", 0.1, 0.1)["default"] == "s3"                    # a tie keeps S3


def test_choose_three_candidates():
    d = {"s3": "picker choice", "s4": "default", "s3ens": "default"}
    assert S3.choose(d, {"s3": 0.08, "s4": 0.095, "s3ens": 0.090}) == {"default": "s3ens",
                                                                        "picker": ["s3ens", "s4", "s3"]}
    d = {"s3": "not used", "s4": "not used", "s3ens": "picker choice"}
    assert S3.choose(d, {"s3ens": 0.09}) == {"default": None, "picker": ["s3ens"]}


def test_s3ens_picker_choice_needs_a_decided_read_gain():
    win = _ci(1.0, 3.0)
    assert S3.trained_decision("s3ens", win, win, _ci(-0.5, 0.5), _ci(-0.01, 0.02)) == "not used"
    assert S3.trained_decision("s3ens", win, win, _ci(-0.5, 0.5), _ci(0.001, 0.02)) == "picker choice"
