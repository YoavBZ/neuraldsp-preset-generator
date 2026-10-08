import copy
import math

import pytest

from learn import set3_diagnostic as D


def analyze(data, parts):
    # Independent fixture inventory, never inferred from potentially incomplete rows.
    names = [f"factory:p{i:02}" for i in range(len(parts))] + ["factory:constant", D.TEMPLATE]
    return D.analyze(data, parts, {amp: names for amp in D.AMPS})


def panel(n=11):
    """Each band needs its own preset; no constant can learn its unseen preference."""
    parts = [{"slug": f"part{i:02}", "band": f"band{i:02}", "split": "development"}
             for i in range(n)]
    names = [f"factory:p{i:02}" for i in range(n)]
    data = {}
    for i, part in enumerate(parts):
        a = {name: 2.0 for name in names}
        a[names[i]] = 0.1
        a["factory:constant"] = 1.0
        a[D.TEMPLATE] = 3.0
        b = dict(a)
        b[names[i]] = 0.2
        net = {name: 2.0 for name in a}
        net[D.TEMPLATE] = 0.1
        data[part["slug"]] = {f"{bs}|{amp}|{kind}": copy.deepcopy(scores)
                              for bs in D.BAND_SETS for amp in D.AMPS
                              for kind, scores in (("measure_A", a), ("measure_B", b), ("net_A", net))}
    return data, parts


def test_control_establishes_headroom_without_confusing_rebuilt_choices():
    data, parts = panel()
    result = analyze(data, parts)
    cell = result["cells"]["recording|sw50r"]
    assert cell["headroom_observed"]
    assert cell["comparisons"]["true_di_vs_constant"]["band_median_log_ratio"] == pytest.approx(math.log(.2))
    assert cell["comparisons"]["true_di_vs_constant"]["sign_flip_p_two_sided"] == 2 / 2048
    assert cell["joint_wins"]["true_di"]["share"] == 1
    assert cell["joint_wins"]["rebuilt_di"]["share"] == 0
    assert cell["selection_agreement"]["same"] == 0
    assert all(p["slug"] not in cell["constants_by_excluded_band"][p["band"]]["training_parts"]
               for p in parts)


def test_constant_really_excludes_every_part_of_the_evaluated_band():
    data, parts = panel(3)
    parts[1]["band"] = parts[0]["band"]
    cell = analyze(data, parts)["cells"]["recording|sw50r"]
    audit = cell["constants_by_excluded_band"]["band00"]
    assert audit["training_parts"] == ["part02"]
    assert audit["preset"] == "factory:p02"


def test_refused_rebuilt_selection_keeps_original_band_denominator():
    data, parts = panel(3)
    parts[1]["band"] = parts[0]["band"]
    for key in data["part01"]:
        if key.endswith("net_A"):
            data["part01"][key] = dict.fromkeys(data["part01"][key])
    cell = analyze(data, parts)["cells"]["recording|sw50r"]
    summary = cell["comparisons"]["true_di_vs_rebuilt_di"]
    assert summary["refused_parts"] == ["part01"]
    assert summary["scorable_parts"] == 2
    assert summary["band_weighted_win_share"] == .75  # (one of two + one of one) / two bands
    assert summary["numeric_summaries_descriptive_only"]
    assert cell["selection_agreement"]["original_denominator"] == 3


def test_null_training_score_excludes_candidate_not_a_training_part():
    data, parts = panel(3)
    data["part01"]["recording|sw50r|measure_A"]["factory:p01"] = None
    cell = analyze(data, parts)["cells"]["recording|sw50r"]
    audit = cell["constants_by_excluded_band"]["band00"]
    assert audit["training_parts"] == ["part01", "part02"]
    assert audit["excluded_candidates"]["factory:p01"] == ["part01"]
    assert "factory:p01" not in audit["eligible_medians_raw_A"]
    assert audit["preset"] == "factory:constant"


def test_zero_raw_score_can_be_selected_but_never_becomes_a_finite_log_ratio():
    assert D.best({"a": 0, "b": 1}) == "a"
    assert D.log_ratio(0, 1) is None
    data, parts = panel()
    data["part00"]["recording|sw50r|measure_B"]["factory:p00"] = 0
    cell = analyze(data, parts)["cells"]["recording|sw50r"]
    assert not cell["headroom_observed"]
    assert not cell["headroom_gates"]["no_required_refusals"]
    assert cell["joint_wins"]["true_di"]["by_band"]["band00"] == 1


@pytest.mark.parametrize("bad", [-1, float("inf"), float("nan"), True, "1"])
def test_malformed_non_null_distance_stops_the_diagnostic(bad):
    data, parts = panel(3)
    data["part00"]["recording|sw50r|measure_A"]["factory:p00"] = bad
    with pytest.raises(ValueError, match="invalid non-null"):
        analyze(data, parts)


def test_reserved_parts_and_missing_or_extra_slugs_are_rejected():
    data, parts = panel(3)
    held = copy.deepcopy(parts)
    held[0]["split"] = "held_out"
    with pytest.raises(ValueError, match="development"):
        analyze(data, held)
    with pytest.raises(ValueError, match="exactly"):
        analyze({**data, "reserved": {}}, parts)
    data.pop("part00")
    with pytest.raises(ValueError, match="exactly"):
        analyze(data, parts)


def test_missing_candidates_or_methods_stop_instead_of_changing_the_menu():
    data, parts = panel(3)
    missing = copy.deepcopy(data)
    missing["part00"]["recording|sw50r|net_A"].pop("factory:p00")
    with pytest.raises(ValueError, match="inconsistent"):
        analyze(missing, parts)
    data["part00"].pop("recording|sw50r|net_A")
    with pytest.raises(ValueError, match="missing menu"):
        analyze(data, parts)


def test_sign_flip_ties_and_extreme_but_valid_distances():
    assert D.sign_flip([-1, -1, -1]) == .25
    assert D.sign_flip([0, 0, 0]) == 1
    assert D.sign_flip([-1, 0, 1]) == 1
    assert math.isfinite(D.log_ratio(1e-300, 1e300))
    assert D.best({"z": 2, "a": 2, "bad": None}) == "a"


def test_missing_whole_band_has_no_sign_flip_p_value():
    rows = [{"part": "a", "band": "A", "B": {"x": 1, "y": 2}},
            {"part": "b", "band": "B", "B": {"x": None, "y": 2}}]
    report = D.summarize(rows, "x", "y")
    assert report["band_medians"]["B"] is None
    assert report["sign_flip_p_two_sided"] is None
    assert report["numeric_summaries_descriptive_only"]
    assert report["band_weighted_win_share"] == .5


def test_inclusive_constant_checks_template_as_a_fair_competitor():
    data, parts = panel(3)
    for slug, rows in data.items():
        for key, scores in rows.items():
            if key.endswith("measure_A"):
                scores[D.TEMPLATE] = .01
    cell = analyze(data, parts)["cells"]["recording|sw50r"]
    assert all(audit["preset"] == D.TEMPLATE
               for audit in cell["inclusive_constants_by_excluded_band"].values())
    assert all(audit["preset"] != D.TEMPLATE
               for audit in cell["constants_by_excluded_band"].values())
    assert not cell["headroom_observed"]


def test_headroom_is_not_itself_a_pipeline_gap():
    data, parts = panel()
    for rows in data.values():
        for bs in D.BAND_SETS:
            for amp in D.AMPS:
                rows[f"{bs}|{amp}|net_A"] = copy.deepcopy(rows[f"{bs}|{amp}|measure_A"])
    result = analyze(data, parts)
    assert result["routing"]["sw50r"]["headroom_observed_both_band_sets"]
    assert not result["routing"]["sw50r"]["pipeline_gap_observed_both_band_sets"]
    assert not result["cells"]["recording|sw50r"]["pipeline_gap_observed"]


def test_hindsight_with_a_refused_candidate_is_not_a_full_menu_bound():
    data, parts = panel(3)
    data["part00"]["recording|sw50r|measure_B"]["factory:p01"] = None
    cell = analyze(data, parts)["cells"]["recording|sw50r"]
    assert not cell["hindsight_full_menu_scorable"]
    assert cell["rows"][0]["hindsight_refused_candidates"] == ["factory:p01"]


@pytest.mark.parametrize("globally_missing", [True, False])
def test_inventory_catches_global_omission_and_cross_bandset_menu_change(globally_missing):
    data, parts = panel(3)
    for rows in data.values():
        for key, values in rows.items():
            if globally_missing or key.startswith("union|"):
                values.pop("factory:p00")
    with pytest.raises(ValueError, match="inconsistent"):
        analyze(data, parts)
