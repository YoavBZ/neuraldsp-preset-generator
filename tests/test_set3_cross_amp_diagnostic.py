"""Synthetic data only: no experimental scores/audio are opened."""
import copy
import json

import pytest

from learn import set3_cross_amp_diagnostic as C


def fixture():
    parts = [{"slug": f"band{i:02}-part{j}", "band": f"band{i:02}", "split": "development"}
             for i in range(11) for j in range(3)]
    metadata = {"parts": parts + [{"slug": "reserved-part", "band": "reserved", "split": "held_out"}],
                "held_out_bands": ["reserved"]}
    menus = {a: ["factory:shared", C.D.TEMPLATE] + [f"factory:p{k:02}" for k in range(n - 2)]
             for a, n in C.COUNTS.items()}
    scores = {}
    for p in parts:
        scores[p["slug"]] = {}
        for bs in C.D.BAND_SETS:
            for amp, names in menus.items():
                for kind in ("measure_A", "measure_B", "net_A"):
                    values = dict.fromkeys(names, 10.0)
                    values["factory:shared"] = {
                        "measure_A": {"pr12": 1.0, "sw50r": 3.0, "ac20": 4.0},
                        "measure_B": {"pr12": 2.0, "sw50r": 5.0, "ac20": 7.0},
                        "net_A": {"pr12": 1.2, "sw50r": 1.0, "ac20": .5},
                    }[kind][amp]
                    scores[p["slug"]][f"{bs}|{amp}|{kind}"] = values
    return scores, metadata, {"menus": menus}


def test_full_menu_preserves_same_preset_ids_across_amps_and_lexical_tuple_ties():
    scores, metadata, inventory = fixture()
    result = C.analyze(scores, metadata, inventory)
    assert len(result["candidate_inventory"]) == 111
    assert all((amp, "factory:shared") in result["candidate_inventory"] for amp in C.COUNTS)
    part = metadata["parts"][0]["slug"]
    flat = C.flatten(scores, part, "recording", "net_A", inventory["menus"])
    assert len(flat) == 111
    assert C.D.best({c: 0.0 for c in flat}) == min(flat)
    assert result["headroom_both_band_sets"]
    assert not result["net_improvement_both_band_sets"]
    assert result["fixed_net_pick_headroom_both_band_sets"]
    assert result["small_amp_selector_followup_supported"]
    row = result["cells"]["recording"]["rows"][0]
    assert row["picks"]["pooled_known_di"] == ("pr12", "factory:shared")
    assert row["picks"]["pooled_net"] == ("ac20", "factory:shared")
    assert row["picks"]["hindsight_amp_net"] == ("pr12", "factory:shared")


@pytest.mark.parametrize("damage", ["missing_candidate", "missing_part", "reserved_part", "invalid_score",
                                    "incomplete_inventory", "duplicate_inventory", "band_overlap"])
def test_validation_never_redefines_menu_or_excludes_bad_data(damage):
    scores, metadata, inventory = fixture()
    slug = metadata["parts"][0]["slug"]
    if damage == "missing_candidate":
        # Even a candidate missing everywhere cannot redefine the expected inventory.
        for cells in scores.values():
            for key, values in cells.items():
                if "|pr12|" in key:
                    values.pop("factory:shared")
    elif damage == "missing_part":
        scores.pop(slug)
    elif damage == "reserved_part":
        scores["reserved-part"] = copy.deepcopy(scores[slug])
    elif damage == "invalid_score":
        scores[slug]["recording|pr12|net_A"]["factory:shared"] = -1
    elif damage == "incomplete_inventory":
        inventory["menus"]["ac20"].pop()
    elif damage == "duplicate_inventory":
        inventory["menus"]["sw50r"][-1] = inventory["menus"]["sw50r"][0]
    else:
        metadata["held_out_bands"].append("band00")
    with pytest.raises(ValueError):
        C.analyze(scores, metadata, inventory)


def test_constants_exclude_the_whole_evaluated_band_and_templates_only_when_declared():
    scores, metadata, inventory = fixture()
    parts = C.R.select_parts(metadata)
    menus = inventory["menus"]
    names = sorted((a, n) for a in menus for n in menus[a])
    A = {p["slug"]: C.flatten(scores, p["slug"], "recording", "measure_A", menus) for p in parts}
    before = C.constants(parts, A, names, False)
    excluded = "band00"
    for p in parts:
        if p["band"] == excluded:
            A[p["slug"]] = dict.fromkeys(names, 1000.0)
    after = C.constants(parts, A, names, False)
    assert after[excluded] == before[excluded]
    assert len(after[excluded]["training_parts"]) == 30
    for slug in after[excluded]["training_parts"]:
        A[slug][("ac20", C.D.TEMPLATE)] = 0.0
    assert C.constants(parts, A, names, True)[excluded]["candidate"] == ("ac20", C.D.TEMPLATE)
    assert C.constants(parts, A, names, False)[excluded]["candidate"] == ("pr12", "factory:shared")
    # Null excludes only that candidate from fitting, without removing the part.
    A[after[excluded]["training_parts"][0]][("pr12", "factory:shared")] = None
    audit = C.constants(parts, A, names, False)[excluded]
    assert len(audit["training_parts"]) == 30
    assert ("pr12", "factory:shared") in [v["candidate"] for v in audit["excluded_candidates"]]


def test_primary_choices_are_invariant_to_evaluation_B_but_hindsight_may_change():
    scores, metadata, inventory = fixture()
    before = C.analyze(scores, metadata, inventory)
    changed = copy.deepcopy(scores)
    for cells in changed.values():
        for key, values in cells.items():
            if key.endswith("measure_B"):
                values["factory:shared"] = 100.0
                values[C.D.TEMPLATE] = .1
    after = C.analyze(changed, metadata, inventory)
    for bs in C.D.BAND_SETS:
        assert after["cells"][bs]["factory_constants_by_excluded_band"] == before["cells"][bs]["factory_constants_by_excluded_band"]
        for left, right in zip(before["cells"][bs]["rows"], after["cells"][bs]["rows"]):
            assert {m: c for m, c in left["picks"].items() if not m.startswith("hindsight")} == {
                m: c for m, c in right["picks"].items() if not m.startswith("hindsight")}
            assert right["picks"]["hindsight_menu_B"] != left["picks"]["hindsight_menu_B"]


def test_all_null_policies_share_exact_global_fallback_and_actual_amp_is_reported():
    scores, metadata, inventory = fixture()
    slug = metadata["parts"][0]["slug"]
    for bs in C.D.BAND_SETS:
        for amp in C.COUNTS:
            scores[slug][f"{bs}|{amp}|net_A"] = dict.fromkeys(inventory["menus"][amp])
    result = C.analyze(scores, metadata, inventory)
    for cell in result["cells"].values():
        row = next(r for r in cell["rows"] if r["part"] == slug)
        for method in ("pooled_net", "sw50r_net", "pr12_net", "ac20_net"):
            assert row["picks"][method] == row["picks"]["constant"] == ("pr12", "factory:shared")
            assert row["net_audits"][method]["fallback_used"]
            assert cell["fallback_parts"][method] == [slug]
        assert row["picks"]["pooled_net_historical"] is None
        assert cell["chosen_amp_counts"]["sw50r_net"]["pr12"] == 1


def test_ordinary_choices_do_not_require_a_trainable_constant_and_unavailable_fallback_stays_missing():
    candidate = ("sw50r", "factory:x")
    assert C.net_choice({candidate: 0.0}, None)["candidate"] == candidate
    audit = C.net_choice({candidate: None}, None)
    assert audit["candidate"] is None and audit["fallback_attempted"] and not audit["fallback_used"]
    scores, metadata, inventory = fixture()
    for cells in scores.values():
        for key, values in cells.items():
            if key.endswith("measure_A") or key.endswith("sw50r|net_A"):
                cells[key] = dict.fromkeys(values)
    result = C.analyze(scores, metadata, inventory)
    for cell in result["cells"].values():
        assert all(row["hindsight_amp_missing_policies"] == ["sw50r"] for row in cell["rows"])
        assert not cell["fixed_net_pick_headroom_observed"]
        assert not cell["hindsight_all_three_net_picks_raw_scorable"]
        assert len(cell["missing_selections"]["sw50r_net"]) == 33
        assert not cell["missing_selections"]["pooled_net"]


def test_refused_B_and_zero_B_are_distinct_in_hindsight_and_required_comparisons():
    scores, metadata, inventory = fixture()
    null_slug, zero_slug = [p["slug"] for p in metadata["parts"][:2]]
    for bs in C.D.BAND_SETS:
        scores[null_slug][f"{bs}|ac20|measure_B"]["factory:shared"] = None
        scores[zero_slug][f"{bs}|ac20|measure_B"]["factory:shared"] = 0.0
    result = C.analyze(scores, metadata, inventory)
    for cell in result["cells"].values():
        refused = next(r for r in cell["rows"] if r["part"] == null_slug)
        zero = next(r for r in cell["rows"] if r["part"] == zero_slug)
        assert refused["hindsight_amp_missing_policies"] == []
        assert refused["hindsight_amp_refused_B_policies"] == ["ac20"]
        assert zero["hindsight_amp_zero_B_policies"] == ["ac20"]
        assert zero["picks"]["hindsight_amp_net"] == ("ac20", "factory:shared")
        assert not cell["hindsight_full_menu_raw_scorable"]
        contrast = cell["comparisons"]["pooled_net_vs_sw50r_net"]
        assert contrast["required_parts"] == 33 and contrast["scorable_parts"] == 31
        assert contrast["refused_parts"] == [null_slug]
        assert contrast["nonpositive_log_parts"] == [zero_slug]
        assert contrast["raw_counts"]["win"] == 1
        assert contrast["raw_counts"]["refusal"] == 1
        assert not cell["net_improvement_gates"]["sw50r_net_complete_positive"]


def test_known_DI_headroom_cannot_authorize_selector_without_fixed_net_pick_headroom():
    scores, metadata, inventory = fixture()
    # Every amp's net picks its own bad template, whereas known DI picks PR12 shared.
    for cells in scores.values():
        for key, values in cells.items():
            if key.endswith("net_A"):
                values[C.D.TEMPLATE] = .01
    result = C.analyze(scores, metadata, inventory)
    assert result["headroom_both_band_sets"]
    assert not result["net_improvement_both_band_sets"]
    assert not result["fixed_net_pick_headroom_both_band_sets"]
    assert not result["small_amp_selector_followup_supported"]


def test_band_weighting_keeps_ties_refusals_and_zeros_in_original_denominators():
    rows = [{"part": "a", "band": "A", "B": {"x": 0.0, "y": 1.0}},
            {"part": "b", "band": "A", "B": {"x": None, "y": 1.0}},
            {"part": "c", "band": "A", "B": {"x": 1.0, "y": 1.0}},
            {"part": "d", "band": "B", "B": {"x": .5, "y": 1.0}}]
    report = C.comparison(rows, "x", "y")
    assert report["band_weighted_win_share"] == pytest.approx((1 / 3 + 1) / 2)
    assert report["raw_counts"] == {"win": 2, "loss": 0, "tie": 1, "refusal": 1}
    assert not C.margin_gates(report)["complete_positive"]


def test_net_improvement_requires_both_band_sets_and_all_declared_comparators():
    scores, metadata, inventory = fixture()
    for cells in scores.values():
        for key, values in cells.items():
            if key.endswith("measure_A"):
                values["factory:p00"] = .01  # global constant: poor B=10
            if "|pr12|net_A" in key:
                values["factory:shared"] = .001  # pooled net: PR12 B=2 vs SW50R B=5
    result = C.analyze(scores, metadata, inventory)
    assert result["net_improvement_both_band_sets"]
    for cell in result["cells"].values():
        assert cell["joint_wins"]["share"] == 1
        assert all(cell["net_improvement_gates"].values())
        assert cell["comparisons"]["pooled_net_vs_sw50r_net"]["raw_counts"]["win"] == 33
    for cells in scores.values():
        cells["union|pr12|net_A"]["factory:shared"] = 100
    result = C.analyze(scores, metadata, inventory)
    assert result["cells"]["recording"]["net_improvement_observed"]
    assert not result["cells"]["union"]["net_improvement_observed"]
    assert not result["net_improvement_both_band_sets"]


def test_execution_failure_preserves_new_report_and_refuses_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(C.R, "ROOT", tmp_path)
    def fail(report):
        raise ValueError("synthetic preflight failure")
    monkeypatch.setattr(C, "run", fail)
    out = tmp_path / "tmp/failure.json"
    with pytest.raises(ValueError, match="synthetic preflight"):
        C.execute(out)
    before = out.read_bytes()
    assert json.loads(before)["status"] == "execution_error"
    with pytest.raises(ValueError, match="new regular file"):
        C.execute(out)
    assert before == out.read_bytes()
