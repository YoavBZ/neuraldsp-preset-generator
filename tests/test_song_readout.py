"""Step 3's readout rules (`learn/song_readout.py`), on synthetic inputs; plus song_settings'
gap-closed computation and song_model.predict_settings' mapping, with everything faked."""

import contextlib
import json
import math
import pathlib
import sys
import types

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import song_readout as R  # noqa: E402


def U(slug, band, cls="clean", amp="pr12", search="A", **d):
    return {"slug": slug, "band": band, "cls": cls, "amp": amp, "search": search, "held": R.other(search),
            "d": d}


def ratio_units(values, arm="B", ks=0.5, cls_of=None, **extra):
    """One part per band, one direction: arm/S = exp(v), K_S/S = ks."""
    cls_of = cls_of or {}
    return [U(f"p{i}", f"b{i}", cls_of.get(i, "clean"), S=1.0, K_S=ks, **{arm: math.exp(v)}, **extra)
            for i, v in enumerate(values)]


# --- statistics -------------------------------------------------------------------------------

def test_bw_stats_weights_bands_not_parts():
    s = R.bw_stats([("x", -1.0), ("x", -1.0), ("x", -1.0), ("y", 1.0)])
    assert s["band_weighted_mean"] == pytest.approx(0.0)
    assert s["bands_negative"] == 1 and s["bands_positive"] == 1 and s["parts"] == 4
    assert s["lo90"] < 0 < s["hi90"]


def test_bw_stats_zero_band_is_not_better_and_one_band_has_no_interval():
    s = R.bw_stats([("x", 0.0), ("y", -0.1)])
    assert s["bands_negative"] == 1
    one = R.bw_stats([("x", -0.2), ("x", -0.4)])
    assert one["lo90"] is None and one["band_weighted_mean"] == pytest.approx(-0.3)
    assert R.bw_stats([])["band_weighted_mean"] is None


def test_part_rows_average_directions_and_amps():
    us = [U("p", "b", amp=a, search=s, B=math.exp(v), S=1.0) for a, s, v in
          (("pr12", "A", -0.1), ("pr12", "B", -0.3), ("sw50r", "A", 0.0), ("ac20", "B", -0.2))]
    (row,) = R.part_rows(us, R.log_vs("B", "S"))
    assert row[:2] == ("b", "clean") and row[2] == pytest.approx(-0.15)


def test_log_vs_skips_non_finite_and_missing():
    f = R.log_vs("B", "S")
    assert f(U("p", "b", B=math.inf, S=1.0)) is None
    assert f(U("p", "b", S=1.0)) is None


def test_drop_refused_drops_for_every_method_and_reports_which():
    us = [U("p", "b", S=1.0, K_S=0.9, B=math.inf), U("q", "c", S=1.0, K_S=0.9, B=0.8),
          {**U("r", "d", S=1.0), "skipped": True},
          U("s", "e", S=1.0, K_S=0.9, B=0.8, constant=math.inf)]       # a control: compared pairwise only
    kept, dropped = R.drop_refused(us)
    assert [u["slug"] for u in kept] == ["q", "s"]
    assert dropped[0][3] == ["B"] and dropped[1][3] == ["knob-ceiling skipped"]


def test_gym_half_b_left_out():
    us = [U(R.GYM, "Dom", search="A"), U(R.GYM, "Dom", search="B"), U("x", "y", search="A")]
    left = R.without_gym_half_b(us)
    assert [(u["slug"], u["held"]) for u in left] == [(R.GYM, "A"), ("x", "B")]


# --- arm B's positive control -----------------------------------------------------------------

def P(fold, i, S, target, pred, median, held="B"):
    return {"fold": fold, "target": i, "held": held, "d": {"S": S, "target": target, "pred": pred, "median": median}}


def good_fold(f, n=3):
    return [P(f, f"{f}-{j}", 2.0, 1.0, 1.2, 1.9) for j in range(n)]


def test_gap_closed_signs_and_zero():
    assert R.gap_closed(2.0, 1.5, 1.0) == pytest.approx(0.5)
    assert R.gap_closed(2.0, 1.0, 2.0) is None
    assert R.gap_closed(1.0, 0.9, 1.2) == pytest.approx(-0.5)        # negative denominator


def test_positive_control_passes_when_every_fold_passes():
    out = R.positive_control([u for f in R.FOLDS for u in good_fold(f)])
    assert out["passes"] and out["final"] and out["status"] == "passes"
    assert out["folds"][0]["kept"] == 3 and out["folds"][0]["gap_closed_ge_50"] == 3


def test_positive_control_gap_floor_is_inclusive_and_filters():
    us = [u for f in (1, 2, 3) for u in good_fold(f)]
    us += [P(0, "a", 1.1, 1.0, 1.0, 2.0),            # gap exactly 0.1: kept, closes 100%
           P(0, "b", 1.0, 0.901, 0.95, 2.0),         # gap 0.099: dropped
           P(0, "c", 1.0, 1.2, 0.5, 2.0)]            # negative gap: dropped, never divided
    out = R.positive_control(us)
    assert out["folds"][0]["kept"] == 1 and out["passes"]


def test_positive_control_two_thirds_exact_and_median_tie_not_closer():
    base = [u for f in (1, 2, 3) for u in good_fold(f)]
    two_of_three = [P(0, "a", 2.0, 1.0, 1.5, 1.9), P(0, "b", 2.0, 1.0, 1.4, 1.9), P(0, "c", 2.0, 1.0, 1.6, 1.9)]
    assert R.positive_control(base + two_of_three)["folds"][0]["passes"]          # 2 of 3 closes ≥ 50%
    one_of_three = [P(0, "a", 2.0, 1.0, 1.5, 1.9), P(0, "b", 2.0, 1.0, 1.51, 1.9), P(0, "c", 2.0, 1.0, 1.6, 1.9)]
    assert not R.positive_control(base + one_of_three)["folds"][0]["passes"]
    ties = [P(0, j, 2.0, 1.0, 1.2, 1.2) for j in "ab"] + [P(0, "c", 2.0, 1.0, 1.2, 1.9)]
    out = R.positive_control(base + ties)
    assert out["folds"][0]["closer_than_median"] == 1 and not out["passes"]


def test_positive_control_empty_or_missing_fold_fails_and_non_finite_dropped():
    us = [u for f in (1, 2, 3) for u in good_fold(f)]
    out = R.positive_control(us)
    assert out["folds"][0]["kept"] == 0 and not out["passes"]
    out = R.positive_control(us + good_fold(0) + [P(0, "inf", math.inf, 1.0, 1.0, 1.0)])
    assert out["folds"][0]["non_finite"] == 1 and out["passes"]


def test_positive_control_re_runs():
    bad = [u for f in (1, 2, 3) for u in good_fold(f)]
    first = R.positive_control(bad, attempt=1)
    assert not first["final"] and first["reruns_left"] == 2 and "re-run allowed" in first["status"]
    last = R.positive_control(bad, attempt=3)
    assert last["final"] and last["status"] == "fails after two re-runs"
    with pytest.raises(ValueError):
        R.positive_control(bad, attempt=4)


# --- the shuffled-input control and data limit -------------------------------------------------

def test_shuffled_control_threshold_and_band_share():
    def units(vals):
        return [U(f"p{i}", f"b{i}", B=math.exp(v), S=1.0, shuffled=[1.0, 1.0, 1.0]) for i, v in enumerate(vals)]

    s = R.shuffled_control(units([-0.05, -0.05, -0.05, -0.05, -0.05]))
    assert s["passes"]                                            # exactly −0.05, 5 of 5 bands
    assert not R.shuffled_control(units([-0.049] * 5))["passes"]
    assert R.shuffled_control(units([-0.2, -0.2, -0.2, 0.05, 0.05]))["passes"]       # 3 of 5 = 60%
    assert not R.shuffled_control(units([-0.3, -0.3, 0.0, 0.0]))["passes"]           # 2 of 4 = 50%; a 0 is not better


def test_shuffled_control_uses_the_geometric_mean():
    u = U("p", "b", B=1.0, shuffled=[math.e, 1 / math.e, 1.0])
    assert R.shuffled_control([u])["band_weighted_mean"] == pytest.approx(0.0)


def test_data_limit_is_strictly_more_than_003():
    def units(v):
        return [U(f"p{i}", f"b{i}", B=math.exp(v), B_half=1.0) for i in range(3)]

    assert not R.data_limit(units(-0.03))["data_limited"]
    assert R.data_limit(units(-0.031))["data_limited"]


# --- arm A's known-target control (amendment 2) -----------------------------------------------

def KT(S, target, measure, rebuilt):
    return {"S": {"B": S}, "target": {"B": target}, "measure_run": {"B": measure}, "rebuilt_run": {"B": rebuilt}}


def test_known_target_gap_mode_rows():
    good = [KT(2.0, 1.0, 1.0, 1.0)] * 6
    assert R.known_target_control(good)["row"] == 2
    # 4 of 6 measure-DI cells close ≥ 50% = 2/3: the set-up is right
    mixed = [KT(2.0, 1.0, 1.0, 2.0)] * 4 + [KT(2.0, 1.0, 1.8, 2.0)] * 2
    out = R.known_target_control(mixed)
    assert out["measure_closed"] == 4 and out["row"] == 3 and out["outcome"] == "fails"
    wrong = [KT(2.0, 1.0, 1.0, 1.0)] * 3 + [KT(2.0, 1.0, 1.8, 1.0)] * 3
    assert R.known_target_control(wrong)["outcome"] == "set-up wrong"


def test_known_target_shortfall_within_003_is_one_sided():
    # rebuilt closes half the gap on 3 of 6 only; its mean shortfall decides
    measure = [1.0] * 4 + [1.99] * 2

    def cells(bad):
        return [KT(2.0, 1.0, m, r) for m, r in zip(measure, [1.0] * 3 + [bad] * 3)]

    near = R.known_target_control(cells(1.6))
    assert near["rebuilt_closed"] == 3 and near["row"] == 2
    assert 0 < near["rebuilt_mean_shortfall"] - near["measure_mean_shortfall"] <= 0.03
    far = R.known_target_control(cells(1.8))
    assert far["rebuilt_mean_shortfall"] - far["measure_mean_shortfall"] > 0.03 and far["row"] == 3
    # rebuilt closes half the gap on only 5 of 9, but its mean shortfall is 0.055 *below* the
    # measure run's: not "within 0.03" literally, but read as passing (one-sided)
    measure = [1.0] * 6 + [2.99] * 3
    rebuilt = [1.0] * 5 + [2.01] * 4
    better = [KT(3.0, 1.0, m, r) for m, r in zip(measure, rebuilt)]
    out = R.known_target_control(better)
    assert out["rebuilt_closed"] == 5 and out["rebuilt_mean_shortfall"] < out["measure_mean_shortfall"] - 0.05
    assert out["outcome"] == "passes"


def test_known_target_negative_gaps_are_uninformative_not_divided():
    cells = [KT(1.0, 1.5, 0.9, 0.9)] * 7 + [KT(2.0, 1.0, 1.0, 1.0)] * 5     # 5 informative → shortfall mode
    out = R.known_target_control(cells)
    assert out["informative"] == 5 and out["mode"].startswith("mean shortfall")


def test_known_target_shortfall_mode_rows():
    def cells(m, r):
        return [KT(1.0, 1.05, 1.05 * math.exp(m), 1.05 * math.exp(r))] * 12        # gap < 0.1 everywhere

    assert R.known_target_control(cells(0.11, 0.0))["outcome"] == "set-up wrong"
    assert R.known_target_control(cells(0.10, 0.13))["outcome"] == "passes"         # within 0.03
    assert R.known_target_control(cells(-0.2, 0.0))["outcome"] == "passes"          # at or below 0
    assert R.known_target_control(cells(-0.2, 0.01))["outcome"] == "fails"


ARMA_CONTROL = pathlib.Path("~/ndsp-presets/learn/song-settings/armA-control").expanduser()


@pytest.mark.skipif(len(list(ARMA_CONTROL.glob("*-result.json"))) != 12, reason="the stored control results")
def test_known_target_reproduces_the_recorded_outcome():
    out = R.known_target_control([json.loads(p.read_text()) for p in sorted(ARMA_CONTROL.glob("*-result.json"))])
    assert out["informative"] == 9 and out["measure_closed"] == 9 and out["rebuilt_closed"] == 3
    assert out["rebuilt_mean_shortfall"] == pytest.approx(0.320, abs=5e-4)
    assert out["measure_mean_shortfall"] == pytest.approx(-0.062, abs=5e-4)
    assert out["row"] == 3 and out["outcome"] == "fails"


# --- each arm's pass rule ---------------------------------------------------------------------

def test_arm_rules_all_pass():
    out = R.arm_rules(ratio_units([-0.1] * 5, ks=math.exp(-0.2)), "B", controls_pass=True)
    assert out["passes"] and out["share_of_K_S_gain"] == pytest.approx(0.5)


def test_arm_rules_rule1_floor_and_ks_share():
    at_floor = R.arm_rules(ratio_units([-0.03] * 5, ks=math.exp(-0.075)), "B", True)
    assert at_floor["rules"]["1"]                                      # −0.03 and exactly 40% of −0.075
    short = R.arm_rules(ratio_units([-0.029] * 5, ks=math.exp(-0.05)), "B", True)
    assert not short["rules"]["1"]
    low_share = R.arm_rules(ratio_units([-0.05] * 5, ks=math.exp(-0.2)), "B", True)
    assert not low_share["rules"]["1"]                                 # 25% of K_S's gain


def test_arm_rules_rule2_band_share():
    assert R.arm_rules(ratio_units([-0.2, -0.2, -0.2, 0.01, 0.01], ks=math.exp(-0.3)), "B", True)["rules"]["2"]
    assert not R.arm_rules(ratio_units([-0.3, -0.3, 0.0, 0.01], ks=math.exp(-0.3)), "B", True)["rules"]["2"]


def test_arm_rules_rule3_harm_guard():
    cls = {3: "crunch", 4: "crunch"}
    ok = R.arm_rules(ratio_units([-0.3, -0.3, -0.3, 0.05, 0.05], ks=math.exp(-0.5), cls_of=cls), "B", True)
    assert ok["rules"]["3"]
    bad = R.arm_rules(ratio_units([-0.3, -0.3, -0.3, 0.051, 0.051], ks=math.exp(-0.5), cls_of=cls), "B", True)
    assert not bad["rules"]["3"] and bad["crunch"]["band_weighted_mean"] == pytest.approx(0.051)


def test_arm_rules_rule4_menu_pick_for_arm_a_only():
    us = ratio_units([-0.1] * 5, arm="A", ks=math.exp(-0.2), menu_pick=math.exp(-0.11))
    out = R.arm_rules(us, "A")
    assert out["rules"]["4"] and "5" not in out["rules"] and out["passes"]       # worse by exactly 0.01
    us = ratio_units([-0.1] * 5, arm="A", ks=math.exp(-0.2), menu_pick=math.exp(-0.111))
    assert not R.arm_rules(us, "A")["passes"]


def test_arm_rules_rule5_controls_for_arm_b():
    out = R.arm_rules(ratio_units([-0.1] * 5, ks=math.exp(-0.2)), "B", controls_pass=False)
    assert out["rules"]["5"] is False and not out["passes"] and "4" not in out["rules"]


# --- arm status: sensitivity and data limit -------------------------------------------------

POS_OK = {"passes": True, "final": True, "status": "passes"}


def b_units(vals, gym_b=None, half=None):
    us = []
    for i, v in enumerate(vals):
        for search in "AB":
            slug = R.GYM if i == 0 else f"p{i}"
            x = gym_b if (i == 0 and search == "A" and gym_b is not None) else v      # search A → held B
            us.append(U(slug, f"b{i}", search=search, S=1.0, K_S=math.exp(-0.2), B=math.exp(x),
                        shuffled=[1.0, 1.0, 1.0], B_half=math.exp(x) * (half or 1.0)))
    return us


def test_arm_status_passes_and_sensitivity_undecided():
    s = R.arm_status(b_units([-0.1] * 5), "B", positive=POS_OK, data_limited={"data_limited": False})
    assert s["status"] == "passes" and s["passes"]
    # Gym Hours' half-B cell is so bad that the declared reading fails; without it, it passes
    us = b_units([-0.1] * 5, gym_b=1.5)
    s = R.arm_status(us, "B", positive=POS_OK, data_limited={"data_limited": False})
    assert not s["declared"]["passes"] and s["without_gym_half_b"]["passes"]
    assert s["status"].startswith("undecided (amendment 3") and not s["passes"]


def test_arm_status_data_limit_readings():
    us = b_units([0.1] * 5)
    assert R.arm_status(us, "B", positive=POS_OK, data_limited={"data_limited": True})["status"] == \
        "undecided (data-limited)"
    assert R.arm_status(us, "B", positive=POS_OK, data_limited={"data_limited": False})["status"] == "failed"
    assert R.arm_status(us, "B", positive=POS_OK, data_limited=None)["status"] == "failed (data-limit check not run)"
    dl = R.data_limit(b_units([0.1] * 5, half=math.exp(0.05)))
    assert dl["data_limited"]


def test_arm_status_gate_and_failed_positive_control():
    us = ratio_units([-0.1] * 5, arm="A", ks=math.exp(-0.2), menu_pick=1.0)
    s = R.arm_status(us, "A", gate="known-target control fails")
    assert s["declared"]["passes"] and not s["passes"] and s["status"].startswith("failed (known-target")
    s = R.arm_status(b_units([-0.1] * 5), "B", positive={"passes": False}, data_limited={"data_limited": False})
    assert s["declared"]["rules"]["5"] is False and s["status"] == "failed"


# --- the readout ------------------------------------------------------------------------------

def st(passes, mean=None, status=None):
    return {"passes": passes, "status": status or ("passes" if passes else "failed"),
            "declared": {"vs_S": {"band_weighted_mean": mean}}}


KT_PASS = {"row": 2, "outcome": "passes"}
POS_FINAL_OK = {"passes": True, "final": True, "status": "passes"}


def test_readout_blocked_then_row1_then_row2():
    pos = {"passes": False, "final": False, "status": "fails; fix and re-run allowed (2 left)"}
    assert R.readout([], {"B": st(False)}, pos, KT_PASS)["row"] is None
    pos = {"passes": False, "final": True, "status": "fails after two re-runs"}
    assert R.readout([], {"A": st(True, -0.1), "B": st(False)}, pos, {"row": 1})["row"] == 1
    out = R.readout([], {"A": st(False), "B": st(True, -0.1)}, POS_FINAL_OK, {"row": 1, "outcome": "set-up wrong"})
    assert out["row"] == 2 and out["arm_B"] == "passes"


def test_readout_leader_tie_goes_to_the_cheapest():
    # A is best by mean, B is close and noisy against A → tied; B is cheaper, so B leads
    us = [U(f"p{i}", f"b{i}", S=1.0, A=math.exp(-0.12), B=math.exp(-0.12 + e))
          for i, e in enumerate((0.05, -0.04, 0.03, -0.02, 0.0))]
    out = R.readout(us, {"A": st(True, -0.12), "B": st(True, -0.118)}, POS_FINAL_OK, KT_PASS)
    assert out["row"] == 3 and out["best_mean"] == "A" and out["tied_with_best"] == ["B"] and out["leader"] == "B"


def test_readout_leader_clear_and_undecided_listed():
    us = [U(f"p{i}", f"b{i}", S=1.0, A=math.exp(-0.3 + e), B=math.exp(-0.05 + e))
          for i, e in enumerate((0.01, -0.01, 0.0, 0.02, -0.02))]
    out = R.readout(us, {"A": st(True, -0.3), "B": st(True, -0.05)}, POS_FINAL_OK, KT_PASS)
    assert out["leader"] == "A" and out["tied_with_best"] == []
    out = R.readout(us, {"A": st(False), "B": st(False, status="undecided (data-limited)")}, POS_FINAL_OK, KT_PASS)
    assert out["row"] == 4 and out["undecided"] == ["B"]


def test_single_answer_amp_takes_the_best_search_half_s():
    us = [{**U("p", "b", amp="pr12", B=math.exp(-0.5), S=1.0), "S_search": 2.0},
          {**U("p", "b", amp="sw50r", B=math.exp(-0.1), S=1.0), "S_search": 1.0}]
    (row,) = R.single_answer_rows(us, "B")
    assert row[2] == pytest.approx(-0.1)


# --- reading files: refusal and a full synthetic tree -----------------------------------------

PARTS = {f"p{i}": {"band": f"b{i}", "gain_class": "crunch" if i == 4 else "clean"} for i in range(5)}
PARTS[R.GYM] = {"band": "Dom", "gain_class": "clean"}
CELLS = [(s, a, sh, R.other(sh)) for s in sorted(PARTS) for a in ("pr12", "sw50r") for sh in "AB"]
CONTROL = [(f"p{i}", a) for i in range(3) for a in ("pr12", "sw50r")]


def _w(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def build_tree(tmp, half=True):
    root, kc, lt = tmp / "ss", tmp / "kc", tmp / "lt"
    for s, a in CONTROL:
        _w(root / "armA-control" / f"{s}-{a}-result.json",
           {"S": {"A": 2, "B": 2.0}, "target": {"A": 1, "B": 1.0}, "measure_run": {"A": 1, "B": 1.0},
            "rebuilt_run": {"A": 2, "B": 1.9}})
    targets = [{"i": i, "fold": i % 4} for i in range(8)]
    _w(root / "armB" / "control-targets.json", targets)
    _w(root / "armB" / "predictions.json", {"control": {str(i): {} for i in range(8)}, "cells": {}})
    for i in range(8):
        h = {"A": 2.0, "B": 2.0}
        _w(root / "armB" / "scores" / f"control-{i}.json",
           {"S": h, "target": {"A": 1.0, "B": 1.0}, "predA": {"A": 1.1, "B": 1.1}, "predB": {"A": 1.1, "B": 1.1},
            "median": {"A": 1.9, "B": 1.9}})
    for s, a, sh, held in CELLS:
        _w(kc / "cells" / s / a / "result.json",
           {"start": "S", "menu": {"S": {"A": 1.0, "B": 1.0}},
            "runs": {x: {"K_S": {"held": math.exp(-0.2), "curve": [[0, 1, math.exp(-0.1)]] * 150}} for x in "AB"}})
        _w(root / "armA" / s / a / f"{sh}.json", {"judge": {"A": 0.99, "B": 0.99}})
        _w(root / "menupick" / s / "result.json", {amp: {"pick": {"A": "m", "B": "m"}} for amp in ("pr12", "sw50r")})
        _w(lt / s / "menu.json", {amp: {"m": {"flat": {"A": 0.95, "B": 0.95}}} for amp in ("pr12", "sw50r")})
        cell = {"B": {"A": math.exp(-0.1), "B": math.exp(-0.1)}, "constant": {"A": 1.0, "B": 1.0},
                **{f"shuffled{j}": {"A": 1.0, "B": 1.0} for j in range(3)}}
        _w(root / "armB" / "scores" / f"cell-{s}_{a}_{sh}.json", cell)
        if half:
            _w(root / "armB" / "scores-half" / f"cell-{s}_{a}_{sh}.json", {"B": {"A": 1.0, "B": 1.0}})
    return root, kc, lt


def test_gather_refuses_on_missing_files(tmp_path):
    root, kc, lt = build_tree(tmp_path, half=False)
    data, missing = R.gather(root, kc, lt, CELLS, PARTS, CONTROL, half_bank=True)
    assert len(missing) == len(CELLS) and all("scores-half" in m for m in missing)
    (root / "armA" / "p0" / "pr12" / "A.json").unlink()
    _, missing = R.gather(root, kc, lt, CELLS, PARTS, CONTROL, half_bank=False)
    assert missing == [str(root / "armA" / "p0" / "pr12" / "A.json")]
    _, missing = R.gather(tmp_path / "empty", kc, lt, CELLS, PARTS, CONTROL)
    assert any("armA-control" in m for m in missing) and any("predictions.json" in m for m in missing)


def test_gather_and_assemble_end_to_end(tmp_path):
    root, kc, lt = build_tree(tmp_path)
    data, missing = R.gather(root, kc, lt, CELLS, PARTS, CONTROL)
    assert not missing and not data["run_c"]
    assert len(data["positive_units"]) == 16 and data["units"][0]["d"]["K_S@50"] == pytest.approx(math.exp(-0.1))
    rep = R.assemble(data)
    assert rep["known_target_control"]["outcome"] == "fails"
    assert rep["arms"]["A"]["status"].startswith("failed (known-target control fails)")
    assert rep["positive_control"]["passes"]
    assert rep["arms"]["B"]["shuffled_control"]["declared"]["passes"]
    assert rep["arms"]["B"]["status"] == "passes"
    assert rep["readout"]["row"] == 3 and rep["readout"]["leader"] == "B"
    assert "C" not in rep["arms"]
    json.dumps(rep)
    text = R.summary(rep)
    assert "Readout: row 3" in text and "Arm B: passes" in text


def test_report_cli_refuses_and_writes_nothing(tmp_path, monkeypatch, capsys):
    from learn import knob_ceiling as K
    from learn import song_settings as SS

    root, kc, lt = build_tree(tmp_path, half=False)
    monkeypatch.setattr(SS, "OUT", root)
    monkeypatch.setattr(K, "OUT", kc)
    monkeypatch.setattr(K, "HOME", tmp_path / "home")
    monkeypatch.setattr(K, "parts", lambda: PARTS)
    monkeypatch.setattr(SS, "cells", lambda: CELLS)
    monkeypatch.setattr(SS, "control_cells", lambda: CONTROL)
    assert R.main(["report", "--out", str(tmp_path / "out")]) == 2
    assert "refusing to run" in capsys.readouterr().err and not (tmp_path / "out").exists()


# --- song_settings' gap closed (control_search, with everything faked) ------------------------

def test_song_settings_control_search_gap_closed(tmp_path, monkeypatch):
    from learn import knob_ceiling as K
    from learn import song_settings as SS

    dist = {"T": 2.0, "S": 3.0, "M": 2.2, "R": 3.5}         # held-half B distances by settings id
    found = iter(["M", "R"])

    class FakeRenderer:
        def menu(self):
            return {"pr12": {K.START["clean"]["pr12"]: ("sel", {("m", "id"): "S"})}}

        def render(self, di, sel, x):
            return x[("m", "id")]

        def close(self):
            pass

    d = tmp_path / "armA-control"
    d.mkdir()
    np.save(d / "p-pr12-fake.npy", np.zeros(4))
    np.save(d / "p-pr12-rebuilt.npy", np.zeros(4))
    (d / "p-pr12-target.json").write_text(json.dumps({"m/id": "T"}))
    monkeypatch.setattr(SS, "OUT", tmp_path)
    monkeypatch.setattr(SS, "control_cells", lambda: [("p", "pr12")])
    monkeypatch.setattr(K, "parts", lambda: {"p": {"gain_class": "clean"}})
    monkeypatch.setattr(K, "Renderer", FakeRenderer)
    monkeypatch.setattr(K, "measure_di", lambda part: np.zeros(4))
    monkeypatch.setattr(K, "judge", lambda ref, y, di, lag: {"A": 9.0, "B": dist[y]})
    monkeypatch.setattr(K, "knob_search", lambda dims, x0, f, budget, seed: ({("m", "id"): next(found)}, 0, 0, 0))
    SS.control_search((0, 1))
    out = json.loads((d / "p-pr12-result.json").read_text())
    assert out["measure_run"]["gap_closed_B"] == pytest.approx((3.0 - 2.2) / (3.0 - 2.0))
    assert out["rebuilt_run"]["gap_closed_B"] == pytest.approx((3.0 - 3.5) / (3.0 - 2.0))
    assert out["measure_run"]["shortfall_B"] == pytest.approx(math.log(2.2 / 2.0))
    # the readout recomputes the same figures from the raw distances
    kt = R.known_target_control([out])
    assert kt["informative"] == 1


def test_song_settings_gap_closed_none_when_target_equals_start(tmp_path, monkeypatch):
    from learn import knob_ceiling as K
    from learn import song_settings as SS

    class FakeRenderer:
        def menu(self):
            return {"pr12": {K.START["clean"]["pr12"]: ("sel", {("m", "id"): "S"})}}

        def render(self, di, sel, x):
            return x[("m", "id")]

        def close(self):
            pass

    d = tmp_path / "armA-control"
    d.mkdir()
    for n in ("fake", "rebuilt"):
        np.save(d / f"p-pr12-{n}.npy", np.zeros(4))
    (d / "p-pr12-target.json").write_text(json.dumps({"m/id": "T"}))
    monkeypatch.setattr(SS, "OUT", tmp_path)
    monkeypatch.setattr(SS, "control_cells", lambda: [("p", "pr12")])
    monkeypatch.setattr(K, "parts", lambda: {"p": {"gain_class": "clean"}})
    monkeypatch.setattr(K, "Renderer", FakeRenderer)
    monkeypatch.setattr(K, "measure_di", lambda part: np.zeros(4))
    monkeypatch.setattr(K, "judge", lambda ref, y, di, lag: {"A": 1.0, "B": {"T": 2.0, "S": 2.0, "F": 1.5}[y]})
    monkeypatch.setattr(K, "knob_search", lambda dims, x0, f, budget, seed: ({("m", "id"): "F"}, 0, 0, 0))
    SS.control_search((0, 1))
    out = json.loads((d / "p-pr12-result.json").read_text())
    assert out["measure_run"]["gap_closed_B"] is None and out["rebuilt_run"]["gap_closed_B"] is None


# --- song_model.predict_settings' mapping (a numpy stand-in for torch) -----------------------

class _T(np.ndarray):
    def exp(self):
        return np.exp(np.asarray(self)).view(_T)

    def numpy(self):
        return np.asarray(self)


def _fake_torch():
    t = types.ModuleType("torch")
    t.tensor = lambda a: np.asarray(a).view(_T)
    t.no_grad = contextlib.nullcontext
    t.sigmoid = lambda x: 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=float)))
    return t


def test_predict_settings_mapping(monkeypatch):
    from learn import knob_ceiling as K
    from learn import song_model as M

    monkeypatch.setitem(sys.modules, "torch", _fake_torch())
    n = len(M.CONT)
    pi = np.array([0.1, 0.2, 0.6, 0.1])
    mu = np.full((M.K_MIX, n), 0.1)
    mu[2, :] = 0.75                                     # the heaviest component
    mu[1, :] = 0.95                                     # pulls the mixture mean away from it
    swl = np.zeros(len(M.SW))
    swl[M.SW.index("cabParameters/rightCabActive")] = 0.0      # sigmoid 0.5: not > 0.5 → off
    swl[M.SW.index("sw50rAmp/sw50rBright")] = 3.0
    cat = []
    for name in M.CAT:
        z = np.zeros(len(M.MICS))
        z[7 if name.endswith("leftMicType") else 3] = 5.0
        cat.append(z[None].view(_T))

    def net(x, c):
        return (np.log(pi)[None].view(_T), mu[None].view(_T), np.zeros((1, M.K_MIX, n)).view(_T),
                swl[None].view(_T), cat)

    S = {("parameters", "inputGain"): "0", ("cabParameters", "rightCabActive"): "true",
         ("cabParameters", "leftMicType"): "1", ("cabParameters", "leftCabActive"): "true", ("x", "kept"): "S"}
    x, diag = M.predict_settings(net, np.zeros((2, 96, 10)), [-20.0, -20.0], "pr12", "clean", S)
    assert x[("parameters", "inputGain")] == K.fmt(-20 + 0.75 * 32)
    assert x[("pr12Amp", "pr12Volume")] == K.fmt(0.75)
    assert x[("cabParameters", "rightCabMicLevel")] == K.fmt(-40 + 0.75 * 46)
    assert x[("cabParameters", "rightCabActive")] == "false"
    assert ("sw50rAmp", "sw50rBright") not in x                  # not in PR12's space
    assert x[("cabParameters", "leftMicType")] == "7" and x[("cabParameters", "rightMicType")] == "3"
    assert x[("x", "kept")] == "S"
    assert diag["top_weight"] == pytest.approx(0.6)
    mixture = 0.1 * 0.1 + 0.2 * 0.95 + 0.6 * 0.75 + 0.1 * 0.1
    assert diag["top_vs_mixture_mean"] == pytest.approx(abs(0.75 - mixture))

    # sw50r: its switch above threshold; a start with the left cab off leaves the left mic alone
    S2 = {**S, ("cabParameters", "leftCabActive"): "false"}
    x, _ = M.predict_settings(net, np.zeros((2, 96, 10)), [-20.0, -20.0], "sw50r", "crunch", S2)
    assert x[("sw50rAmp", "sw50rBright")] == "true"
    assert x[("cabParameters", "leftMicType")] == "1"
    assert ("cabParameters", "leftCabPosition") not in x
