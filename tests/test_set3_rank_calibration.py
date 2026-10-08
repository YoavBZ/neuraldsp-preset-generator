"""Synthetic calibration checks only; never open real scores, audio, or arrays."""
import copy
import itertools
import json
import math
from pathlib import Path

import pytest

from learn import set3_rank_calibration as R


P0, P1 = "factory:p00", "factory:p01"


def fixture():
    names = [f"factory:p{i:02}" for i in range(44)] + [R.TEMPLATE]
    parts = [{"slug": f"part-{i:02}", "band": f"band-{i // 3:02}", "split": "development"}
             for i in range(33)]
    metadata = {"parts": parts + [{"slug": "reserved", "band": "reserved", "split": "held_out"}],
                "held_out_bands": ["reserved"]}
    data = {}
    for part in parts:
        a = dict.fromkeys(names, 4.0)
        a.update({P0: 1.0, P1: 2.0})
        net = dict.fromkeys(names, 4.0)
        net.update({P0: 2.0, P1: .5})
        data[part["slug"]] = {f"{bs}|sw50r|{kind}": dict(values)
                              for bs in R.BAND_SETS
                              for kind, values in (("measure_A", a), ("measure_B", a), ("net_A", net))}
    # These are independently supplied archived constants, not refitted from data.
    cells = {}
    for bs in R.BAND_SETS:
        audits = {}
        for method in ("constant", "inclusive_constant"):
            candidates = names if method == "inclusive_constant" else names[:-1]
            audits[method] = {band: {"preset": P0,
                                    "training_parts": [p["slug"] for p in parts if p["band"] != band],
                                    "eligible_medians_raw_A": {n: 1.0 if n == P0 else 2.0 for n in candidates},
                                    "excluded_candidates": {}}
                              for band in sorted({p["band"] for p in parts})}
        cells[f"{bs}|sw50r"] = {"parts": 33, "bands": 11, "menu_size": 45,
                                "rows": [{"part": p["slug"], "band": p["band"],
                                          "picks": {"constant": P0, "inclusive_constant": P0}} for p in parts],
                                "constants_by_excluded_band": audits["constant"],
                                "inclusive_constants_by_excluded_band": audits["inclusive_constant"]}
    diagnostic = {"parts": 33, "bands": 11, "cells": cells}
    return data, metadata, {"menus": {"sw50r": names}}, diagnostic


def one_cell(data, metadata, inventory, diagnostic, bs="recording"):
    parts = R.select_parts(metadata)
    names = R.validate_scores(data, parts, inventory)
    constants = R.frozen_constants(diagnostic, parts, names)
    return R.cell(data, parts, bs, names, constants[bs])


def training_inputs(data, parts, bs="recording"):
    labels = {p["slug"]: data[p["slug"]][f"{bs}|sw50r|measure_B"] for p in parts}
    features = {p["slug"]: data[p["slug"]][f"{bs}|sw50r|net_A"] for p in parts}
    return labels, features


def test_all_33_parts_both_bandsets_and_every_nested_training_slug():
    data, metadata, inventory, diagnostic = fixture()
    result = R.analyze(data, metadata, inventory, diagnostic)
    parts = R.select_parts(metadata)
    assert set(result["cells"]) == {"recording|sw50r", "union|sw50r"}
    assert result["parts"] == 33 and result["bands"] == 11
    for cell in result["cells"].values():
        assert len(cell["rows"]) == 33
        assert cell["selected_alpha_fold_counts"]["0"] == 11
        for outer_band, outer in cell["outer_folds"].items():
            expected_outer = {p["slug"] for p in parts if p["band"] != outer_band}
            assert set(outer["training_parts"]) == expected_outer
            assert set(outer["prior"]["training_parts"]) == expected_outer
            assert len(outer["training_bands"]) == 10
            for inner_band, inner in outer["inner_folds"].items():
                expected_inner = {p["slug"] for p in parts if p["band"] not in (outer_band, inner_band)}
                assert set(inner["prior"]["training_parts"]) == expected_inner
                assert len(inner["prior"]["training_bands"]) == 9
                assert set(inner["evaluation_parts"]) == {
                    p["slug"] for p in parts if p["band"] == inner_band}
                for alpha in R.ALPHAS:
                    report = inner["alphas"][str(alpha)]
                    assert report["required_parts"] == 3
                    assert report["positive_parts"] == 3
                    assert report["mean_log_B"] is not None
                    assert all("prediction" in r and "chosen_B" in r for r in report["rows"])
            for loss in outer["alpha_losses"].values():
                assert loss["required_parts"] == loss["positive_parts"] == 30
                assert loss["required_bands"] == 10
                assert len(loss["band_mean_log_B"]) == 10
        assert not cell["followup_justified"]  # calibration ties the prior
        assert cell["selection_agreement"]["prior"]["same"] == 33
    assert not result["followup_justified_both_band_sets"]
    assert result["next_step"] == "close this fixed blend"
    json.dumps(result, allow_nan=False)


def test_outer_excluded_B_changes_leave_entire_fit_alpha_and_picks_invariant():
    args = fixture()
    data, metadata, inventory, diagnostic = args
    original = one_cell(*args)
    changed = copy.deepcopy(data)
    for part in R.select_parts(metadata):
        if part["band"] == "band-00":
            changed[part["slug"]]["recording|sw50r|measure_B"] = {
                n: 0.0 if i % 3 == 0 else None if i % 3 == 1 else 1e250
                for i, n in enumerate(inventory["menus"]["sw50r"])}
    altered = one_cell(changed, metadata, inventory, diagnostic)
    assert original["outer_folds"]["band-00"] == altered["outer_folds"]["band-00"]
    old_rows = [r for r in original["rows"] if r["band"] == "band-00"]
    new_rows = [r for r in altered["rows"] if r["band"] == "band-00"]
    assert [r["predictions"] for r in old_rows] == [r["predictions"] for r in new_rows]
    assert [r["B"] for r in old_rows] != [r["B"] for r in new_rows]


def test_inner_excluded_B_can_change_tuning_but_not_inner_fit_or_fixed_alpha_predictions():
    data, metadata, inventory, _ = fixture()
    parts = R.select_parts(metadata)[3:12]  # three training bands; no outer labels
    labels, features = training_inputs(data, parts)
    names = inventory["menus"]["sw50r"]
    original = R.fit_outer(parts, labels, features, names)
    changed = copy.deepcopy(labels)
    for part in parts[:3]:
        changed[part["slug"]].update({P0: 1000.0, P1: .001})
    altered = R.fit_outer(parts, changed, features, names)
    before, after = original["inner_folds"]["band-01"], altered["inner_folds"]["band-01"]
    assert before["prior"] == after["prior"]
    for alpha in R.ALPHAS:
        assert [r["prediction"] for r in before["alphas"][str(alpha)]["rows"]] == [
            r["prediction"] for r in after["alphas"][str(alpha)]["rows"]]
    assert original["selected_alpha"] == 0
    assert altered["selected_alpha"] != original["selected_alpha"]
    assert before["alphas"]["0"]["mean_log_B"] != after["alphas"]["0"]["mean_log_B"]


def test_outer_net_is_accessed_only_after_tuning_and_B_after_outer_picks(monkeypatch):
    data, metadata, inventory, diagnostic = fixture()
    target = "part-00"
    events = []

    class Watched(dict):
        def __getitem__(self, key):
            if key == "recording|sw50r|net_A":
                events.append("target_net")
            if key == "recording|sw50r|measure_B":
                events.append("target_B")
            return super().__getitem__(key)

    data[target] = Watched(data[target])
    original_fit = R.fit_outer

    def fit(parts, *args):
        if "band-00" not in {p["band"] for p in parts}:
            assert not events
            value = original_fit(parts, *args)
            events.append("target_fit_done")
            return value
        return original_fit(parts, *args)

    monkeypatch.setattr(R, "fit_outer", fit)
    parts = R.select_parts(metadata)
    names = inventory["menus"]["sw50r"]
    constants = R.frozen_constants(diagnostic, parts, names)["recording"]
    R.cell(data, parts, "recording", names, constants)
    assert events.index("target_fit_done") < events.index("target_net") < events.index("target_B")


def test_prior_centers_full_positive_menu_and_weights_bands_equally():
    parts = [{"slug": s, "band": b} for s, b in (("a", "A"), ("b", "A"), ("c", "B"))]
    names = [P0, P1, R.TEMPLATE]
    labels = {"a": {P0: 1., P1: 1., R.TEMPLATE: 100.},
              "b": {P0: 1., P1: 1., R.TEMPLATE: 100.},
              "c": {P0: math.exp(4), P1: 1., R.TEMPLATE: 100.}}
    prior = R.fit_prior(parts, labels, names)
    assert prior["part_labels"]["c"]["median_log_B"] == pytest.approx(4)
    # P1 is centered to 0 in A and -4 in B: equal band mean is -2, not -4/3.
    assert prior["priors"][P1] == pytest.approx(-2)
    labels["a"][R.TEMPLATE] = None
    second = R.fit_prior(parts, labels, names)
    assert R.TEMPLATE not in second["priors"]
    assert second["part_labels"]["c"]["median_log_B"] == pytest.approx(4)
    assert second["priors"][P1] == pytest.approx(-2)
    assert second["training_parts"] == ["a", "b", "c"]


@pytest.mark.parametrize("bad,reason", [(None, "missing_label"), (0, "nonpositive_label")])
def test_prior_eligibility_requires_every_training_part_and_reports_null_vs_zero(bad, reason):
    names = [P0, P1, R.TEMPLATE]
    parts = [{"slug": s, "band": s} for s in ("a", "b")]
    labels = {"a": {P0: bad, P1: 2, R.TEMPLATE: 3}, "b": dict.fromkeys(names, 1)}
    prior = R.fit_prior(parts, labels, names)
    assert prior["eligible_candidates"] == [P1, R.TEMPLATE]
    assert prior["excluded_candidates"][P0]["parts"] == {"a": reason}
    assert prior["training_parts"] == ["a", "b"]
    field = "missing_labels" if bad is None else "zero_labels"
    assert prior["part_labels"]["a"][field] == [P0]
    assert R.predict(prior, {P0: .0001, P1: 1, R.TEMPLATE: 2}, 1)["preset"] == P1
    assert R.net_prediction({P0: .0001, P1: 1, R.TEMPLATE: 2}, prior, True)["preset"] == P0


def test_empty_and_completely_missing_prior_never_invent_a_preset():
    names = [P0, P1]
    empty = R.fit_prior([], {}, names)
    missing = R.fit_prior([{"slug": "s", "band": "b"}], {"s": dict.fromkeys(names)}, names)
    for prior in (empty, missing):
        assert not prior["trainable"]
        for alpha in R.ALPHAS:
            prediction = R.predict(prior, dict.fromkeys(names), alpha)
            assert prediction["preset"] is None
            assert prediction["missing_reason"] == "no_complete_prior_candidate"
            assert not prediction["fallback"]
        assert R.net_prediction({P0: 0, P1: 1}, prior, True)["preset"] == P0
        assert R.net_prediction(dict.fromkeys(names), prior, True)["preset"] is None


def test_null_fallback_zero_refusal_partial_nulls_and_lexicographic_ties():
    prior = {"priors": {P0: -2, P1: -1}}
    for alpha in R.ALPHAS:
        prediction = R.predict(prior, {P0: None, P1: None, R.TEMPLATE: None}, alpha)
        assert prediction["preset"] == P0
        assert prediction["fallback"]
    scores = {P0: 1, P1: 2, R.TEMPLATE: 0}  # zero even outside prior eligibility
    assert R.predict(prior, scores, 0)["preset"] == P0
    for alpha in R.ALPHAS[1:]:
        prediction = R.predict(prior, scores, alpha)
        assert prediction["preset"] is None
        assert prediction["missing_reason"] == "zero_raw_net_log_unscorable"
        assert prediction["zero_net_candidates"] == [R.TEMPLATE]
    assert R.net_prediction(scores, prior, True)["preset"] == R.TEMPLATE
    choice = R.predict(prior, {P0: None, P1: 2, R.TEMPLATE: .001}, 1)
    assert choice["preset"] == P1
    assert choice["excluded_missing_net_candidates"] == [P0]
    assert choice["excluded_prior_candidates"] == [R.TEMPLATE]
    assert R.predict(prior, {P0: None, P1: None, R.TEMPLATE: 1}, 1)["missing_reason"] == (
        "no_positive_net_for_prior_candidates")
    tied = {"priors": {P1: 0, P0: 0}}
    for alpha in R.ALPHAS:
        assert R.predict(tied, {P1: 1, P0: 1}, alpha)["preset"] == P0
    assert R.net_prediction({P1: 0, P0: 0}, prior, False)["preset"] == P0
    with pytest.raises(ValueError, match="fixed grid"):
        R.predict(prior, scores, .1)


def test_global_minimum_tolerance_tie_rule_is_order_invariant():
    losses = {"0": {"eligible": True, "mean_log_B": 1.8e-12},
              "0.25": {"eligible": True, "mean_log_B": .9e-12},
              "0.5": {"eligible": True, "mean_log_B": 0.},
              "0.75": {"eligible": False, "mean_log_B": None},
              "1": {"eligible": True, "mean_log_B": 1.}}
    for order in itertools.permutations(losses):
        assert R.choose_alpha({k: losses[k] for k in order}) == .25
    assert R.choose_alpha({str(a): {"eligible": True, "mean_log_B": 0} for a in R.ALPHAS}) == 0
    assert R.choose_alpha({str(a): {"eligible": False, "mean_log_B": None} for a in R.ALPHAS}) is None


def test_alpha_loss_requires_all_parts_not_just_one_per_band_and_weights_bands():
    names = [P0, P1]
    training = [{"slug": "t", "band": "T"}]
    evaluation = [{"slug": "e1", "band": "E"}, {"slug": "e2", "band": "E"}]
    labels = {"t": {P0: 1, P1: 2}, "e1": {P0: 1, P1: 2}, "e2": {P0: None, P1: 2}}
    features = {s: {P0: 1, P1: 2} for s in labels}
    inner = R.inner_fold(training, evaluation, labels, features, names)
    assert not inner["alphas"]["0"]["complete"]
    assert inner["alphas"]["0"]["positive_parts"] == 1
    assert inner["alphas"]["0"]["mean_log_B"] is None
    labels["e2"][P0] = 0
    assert R.inner_fold(training, evaluation, labels, features, names)["alphas"]["0"]["rows"][1][
        "evaluation_reason"] == "zero_chosen_B"
    # Single complete candidate fixes picks, so independent expected loss is simple.
    parts = [{"slug": "a", "band": "A"}, {"slug": "b", "band": "A"}, {"slug": "c", "band": "C"}]
    labels = {"a": {P0: 1}, "b": {P0: 1}, "c": {P0: math.exp(6)}}
    features = {s: {P0: 1} for s in labels}
    fitted = R.fit_outer(parts, labels, features, [P0])
    assert fitted["alpha_losses"]["0"]["mean_log_B"] == pytest.approx(3)
    assert fitted["alpha_losses"]["0"]["required_parts"] == 3


def test_failed_tuning_keeps_independent_outer_prior_and_all_comparators():
    data, metadata, inventory, diagnostic = fixture()
    # Alpha=0 chooses P0 in the fold evaluating this zero; positive alphas hit raw zero.
    data["part-03"]["recording|sw50r|measure_B"][P0] = 0
    data["part-03"]["recording|sw50r|net_A"][R.TEMPLATE] = 0
    cell = one_cell(data, metadata, inventory, diagnostic)
    fold = cell["outer_folds"]["band-00"]
    assert fold["selected_alpha"] is None and not fold["trainable"]
    assert fold["prior"]["trainable"]
    assert fold["prior"]["training_parts"] == fold["training_parts"]
    assert not any(v["eligible"] for v in fold["alpha_losses"].values())
    for row in cell["rows"][:3]:
        assert row["picks"]["calibration"] is None
        assert row["predictions"]["calibration"]["missing_reason"] == "no_eligible_alpha"
        assert all(row["picks"][m] is not None for m in R.METHODS if m != "calibration")
        assert row["picks"]["prior"] == P1
    assert not cell["followup_justified"]


def test_untrainable_prior_still_allows_raw_net_but_cannot_fallback():
    data, metadata, inventory, diagnostic = fixture()
    data["part-03"]["recording|sw50r|measure_B"] = dict.fromkeys(inventory["menus"]["sw50r"])
    data["part-01"]["recording|sw50r|net_A"] = dict.fromkeys(inventory["menus"]["sw50r"])
    cell = one_cell(data, metadata, inventory, diagnostic)
    assert not cell["outer_folds"]["band-00"]["prior"]["trainable"]
    row = cell["rows"][0]
    assert row["picks"]["net"] == row["picks"]["historical_net"] == P1
    assert row["picks"]["calibration"] is None and row["picks"]["prior"] is None
    assert cell["rows"][1]["picks"]["net"] is None
    assert cell["rows"][1]["predictions"]["net"]["fallback_attempted"]
    assert not cell["rows"][1]["predictions"]["net"]["fallback"]


def test_restricted_endpoint_fallback_comparison_and_historical_difference():
    data, metadata, inventory, diagnostic = fixture()
    data["part-00"]["recording|sw50r|net_A"] = dict.fromkeys(inventory["menus"]["sw50r"])
    cell = one_cell(data, metadata, inventory, diagnostic)
    row = cell["rows"][0]
    for m in ("calibration", "prior", "net", "restricted_net"):
        assert row["picks"][m] == P0
        assert row["predictions"][m]["fallback"]
        assert cell["fallback_counts"][m] == 1
    assert row["picks"]["historical_net"] is None
    summary = cell["comparisons"]["calibration_vs_restricted_net"]
    assert summary["scorable_parts"] == 33
    assert len(summary["paired_log_ratios"]) == 33
    assert cell["fallback_required_parts"] == 33


def test_frozen_A_constants_are_read_without_refitting():
    data, metadata, inventory, diagnostic = fixture()
    for menus in data.values():
        for bs in R.BAND_SETS:
            menus[f"{bs}|sw50r|measure_A"][R.TEMPLATE] = .0001
    cell = one_cell(data, metadata, inventory, diagnostic)
    assert all(r["picks"]["constant"] == r["picks"]["inclusive_constant"] == P0 for r in cell["rows"])
    assert all(r["picks"]["true_di"] == R.TEMPLATE for r in cell["rows"])


@pytest.mark.parametrize("mutation", ["unknown", "duplicate", "reserved-band", "short", "reband"])
def test_membership_is_never_silently_dropped(mutation):
    _, metadata, _, _ = fixture()
    if mutation == "unknown":
        metadata["parts"][0]["split"] = "unknown"
    elif mutation == "duplicate":
        metadata["parts"].append(copy.deepcopy(metadata["parts"][0]))
    elif mutation == "reserved-band":
        metadata["parts"][0]["band"] = "reserved"
    elif mutation == "short":
        metadata["parts"].pop(0)
    else:
        metadata["parts"][0]["band"] = "new-band"
    with pytest.raises(ValueError):
        R.select_parts(metadata)


@pytest.mark.parametrize("mutation", ["missing-slug", "reserved-slug", "global-candidate", "extra-candidate",
                                      "changed-union", "missing-kind", "bad-inventory"])
def test_exact_membership_and_candidate_inventory(mutation):
    data, metadata, inventory, _ = fixture()
    if mutation == "missing-slug":
        data.pop("part-00")
    elif mutation == "reserved-slug":
        data["reserved"] = copy.deepcopy(data["part-00"])
    elif mutation == "global-candidate":
        for menus in data.values():
            for scores in menus.values():
                scores.pop(P0)
    elif mutation == "extra-candidate":
        data["part-00"]["recording|sw50r|net_A"]["factory:extra"] = 1
    elif mutation == "changed-union":
        data["part-00"]["union|sw50r|measure_B"].pop(P0)
    elif mutation == "missing-kind":
        data["part-00"].pop("recording|sw50r|measure_B")
    else:
        inventory["menus"]["sw50r"][0] = "factory:unknown"
    with pytest.raises(ValueError):
        R.validate_scores(data, R.select_parts(metadata), inventory)


@pytest.mark.parametrize("bad", [-1, float("inf"), float("nan"), True, "1"])
def test_malformed_nonnull_scores_are_errors(bad):
    data, metadata, inventory, _ = fixture()
    data["part-00"]["recording|sw50r|measure_B"][P0] = bad
    with pytest.raises(ValueError, match="invalid non-null"):
        R.validate_scores(data, R.select_parts(metadata), inventory)


@pytest.mark.parametrize("mutation", ["membership", "training", "pick", "candidates", "size"])
def test_archived_constant_scope_and_exclusions_are_checked(mutation):
    _, metadata, inventory, diagnostic = fixture()
    cell = diagnostic["cells"]["recording|sw50r"]
    if mutation == "membership":
        cell["rows"][0]["band"] = "unknown"
    elif mutation == "training":
        cell["constants_by_excluded_band"]["band-00"]["training_parts"].append("part-00")
    elif mutation == "pick":
        cell["inclusive_constants_by_excluded_band"]["band-00"]["preset"] = P1
    elif mutation == "candidates":
        cell["constants_by_excluded_band"]["band-00"]["eligible_medians_raw_A"].pop(P1)
    else:
        cell["menu_size"] = 44
    with pytest.raises(ValueError):
        R.frozen_constants(diagnostic, R.select_parts(metadata), inventory["menus"]["sw50r"])


def metric_rows():
    return [{"part": f"p-{i}", "band": f"b-{i}",
             "picks": {m: m for m in R.METHODS},
             "predictions": {m: {"fallback": False} for m in R.METHODS},
             "B": {m: 1. if m == "calibration" else 2. for m in R.METHODS}}
            for i in range(11)]


def test_metrics_signflip_joint_denominators_and_missing_zero_cases():
    rows = metric_rows()
    rows[0]["B"]["calibration"] = None
    rows[1]["B"]["calibration"] = 0.
    # Unequal bands: one raw zero win plus a refusal out of two in band b-0.
    rows[1]["band"] = "b-0"
    summary = R.summarize(rows, "prior")
    assert summary["required_parts"] == 11
    assert summary["scorable_parts"] == 9
    assert summary["refused_parts"] == ["p-0"]
    assert summary["nonpositive_log_parts"] == ["p-1"]
    assert summary["band_weighted_win_share"] == .95
    assert summary["band_required_parts"]["b-0"] == 2
    assert summary["numeric_summaries_descriptive_only"]
    assert summary["sign_flip_p_two_sided"] is None
    cell = R.report_cell(rows, {}, {}, [])
    assert cell["joint_wins"]["by_band"]["b-0"] == .5
    assert cell["joint_wins"]["counts_by_band"]["b-0"] == {"wins": 1, "required_parts": 2}
    assert not cell["followup_justified"]
    assert not cell["followup_gates"]["prior_complete_positive"]
    assert R.D.sign_flip([-1] * 11) == 2 / 2048
    assert R.D.sign_flip([0] * 11) == 1
    assert R.D.sign_flip([1e-14] * 11) == 1  # exact diagnostic tail tolerance
    assert math.isfinite(R.D.log_ratio(1e-300, 1e300))


def test_complete_main_gates_and_restricted_endpoint_claim_are_distinct():
    rows = metric_rows()
    for row in rows:
        row["B"]["restricted_net"] = 1.
    cell = R.report_cell(rows, {}, {}, [])
    assert cell["followup_justified"]
    assert not cell["blending_benefit_observed"]
    assert cell["comparisons"]["calibration_vs_prior"]["sign_flip_p_two_sided"] == 2 / 2048
    assert cell["comparisons"]["calibration_vs_prior"]["band_median_log_ratio"] == pytest.approx(math.log(.5))
    for row in rows:
        row["B"]["restricted_net"] = 1.1
    assert R.report_cell(rows, {}, {}, [])["blending_benefit_observed"]
    rows[0]["B"]["restricted_net"] = None
    assert not R.report_cell(rows, {}, {}, [])["blending_benefit_observed"]


def provenance_fixture():
    inputs = {k: {"path": f"/synthetic/{k}", "sha256": k} for k in
              ("metadata", "distances", "menu_inventory", "script", "plan")}
    verification = {"verified": True, "comparison": {"mismatch_count": 0}, "parts": 33, "bands": 11,
                    "menu_counts": {"sw50r": 45}, "inputs": copy.deepcopy(inputs),
                    "production_report": {"sha256": "frozen"}}
    diagnostic = {"inputs": copy.deepcopy(inputs)}
    report = {"inputs": {"full_development_diagnostic": {"sha256": "frozen"},
                         "source_diagnostic_code": inputs["script"], "source_diagnostic_plan": inputs["plan"],
                         **{k: inputs[k] for k in ("metadata", "distances", "menu_inventory")}}}
    return report, diagnostic, verification


@pytest.mark.parametrize("mutation", ["none", "distance", "inventory", "metadata", "archive", "code", "plan",
                                      "unverified", "mismatch", "diagnostic"])
def test_provenance_rejects_changed_sources_or_unverified_archive(mutation):
    report, diagnostic, verification = provenance_fixture()
    field = {"distance": "distances", "inventory": "menu_inventory", "metadata": "metadata",
             "archive": "full_development_diagnostic", "code": "source_diagnostic_code",
             "plan": "source_diagnostic_plan"}.get(mutation)
    if field:
        report["inputs"][field]["sha256"] = "changed"
    elif mutation == "unverified":
        verification["verified"] = False
    elif mutation == "mismatch":
        verification["comparison"]["mismatch_count"] = 1
    elif mutation == "diagnostic":
        diagnostic["inputs"]["distances"]["path"] = "/reserved/distances.json"
    if mutation == "none":
        R.validate_provenance(report, diagnostic, verification)
    else:
        with pytest.raises(ValueError):
            R.validate_provenance(report, diagnostic, verification)


def test_failure_is_retained_and_output_cannot_be_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "ROOT", tmp_path)

    def fail(report):
        R.note(report, "synthetic preflight")
        raise ValueError("synthetic provenance failure")

    monkeypatch.setattr(R, "run", fail)
    output = tmp_path / "tmp/failure.json"
    with pytest.raises(ValueError, match="synthetic provenance"):
        R.execute(output)
    result = json.loads(output.read_text())
    assert result["status"] == "execution_error"
    assert result["error"]["type"] == "ValueError"
    assert "synthetic provenance failure" in result["error"]["traceback"]
    assert result["log"][0]["message"] == "synthetic preflight"
    saved = output.read_bytes()
    with pytest.raises(ValueError, match="new regular file"):
        R.execute(output)
    assert saved == output.read_bytes()
    with pytest.raises(ValueError, match="new regular file"):
        R.execute(tmp_path / "outside.json")
    (tmp_path / "tmp/link").symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="new regular file"):
        R.execute(tmp_path / "tmp/link/new.json")


def test_output_open_is_exclusive_even_if_path_check_races(tmp_path, monkeypatch):
    output = tmp_path / "exists.json"
    output.write_text("original")
    monkeypatch.setattr(R, "output_path", lambda _: output)
    monkeypatch.setattr(R, "run", lambda _: pytest.fail("must not run"))
    with pytest.raises(FileExistsError):
        R.execute(output)
    assert output.read_text() == "original"


def test_json_loader_hashes_exact_bytes_and_rejects_duplicate_keys(tmp_path):
    path = tmp_path / "synthetic.json"
    path.write_text('{"a":null,"b":0}')
    report = {"inputs": {}}
    assert R.source_json(path, report, "synthetic") == {"a": None, "b": 0}
    assert report["inputs"]["synthetic"]["sha256"] == R.digest(path)
    path.write_text('{"a":1,"a":2}')
    with pytest.raises(ValueError, match="duplicate JSON key"):
        R.source_json(path, report, "synthetic")


def test_import_has_no_source_reads(monkeypatch):
    import importlib

    def forbidden(*args, **kwargs):
        pytest.fail("import must never open data")

    with monkeypatch.context() as context:
        context.setattr(Path, "read_bytes", forbidden)
        context.setattr(Path, "read_text", forbidden)
        context.setattr(Path, "open", forbidden)
        importlib.reload(R)


def test_blend_uses_declared_log_scores_without_epsilons():
    prior = {"priors": {P0: -2., P1: 1.}}
    values = {P0: math.exp(4), P1: math.exp(-2)}
    choice = R.predict(prior, values, .25)
    assert choice["selection_scores"][P0] == pytest.approx(-.5)
    assert choice["selection_scores"][P1] == pytest.approx(.25)
    assert choice["preset"] == P0
    assert R.predict(prior, values, .5)["preset"] == P1
    extreme = R.predict(prior, {P0: 1e-300, P1: 1e300}, .5)
    assert all(math.isfinite(v) for v in extreme["selection_scores"].values())


@pytest.mark.parametrize("bad_provenance,changed_during_run", [(False, False), (True, False), (False, True)])
def test_run_reads_only_fixed_json_sources_checks_provenance_and_hashes_code(
        monkeypatch, bad_provenance, changed_during_run):
    data, metadata, inventory, diagnostic = fixture()
    paths = {"metadata": R.METADATA, "distances": R.DISTANCES, "menu_inventory": R.INVENTORY,
             "full_development_diagnostic": R.DIAGNOSTIC, "independent_verification": R.VERIFICATION}
    inputs = {k: {"path": str(p), "sha256": str(p)} for k, p in paths.items()}
    original_inputs = {k: copy.deepcopy(inputs[k]) for k in ("metadata", "distances", "menu_inventory")}
    original_inputs.update({"script": {"path": str(R.ROOT / "learn/set3_diagnostic.py"),
                                        "sha256": str(R.ROOT / "learn/set3_diagnostic.py")},
                            "plan": {"path": str(R.ROOT / "docs/set3-development-diagnostic-plan.md"),
                                      "sha256": str(R.ROOT / "docs/set3-development-diagnostic-plan.md")}})
    diagnostic["inputs"] = copy.deepcopy(original_inputs)
    verification = {"verified": True, "comparison": {"mismatch_count": 0}, "parts": 33, "bands": 11,
                    "menu_counts": {"sw50r": 45}, "inputs": original_inputs,
                    "production_report": {"sha256": str(R.DIAGNOSTIC)}}
    if bad_provenance:
        verification["inputs"]["distances"]["sha256"] = "wrong"
    sources = {"metadata": metadata, "distances": data, "menu_inventory": inventory,
               "full_development_diagnostic": diagnostic, "independent_verification": verification}
    loaded, analyzed, hashed = [], [], []

    def source(path, report, label):
        assert path == paths[label]
        loaded.append(label)
        report["inputs"][label] = copy.deepcopy(inputs[label])
        return sources[label]

    def analyze(*args):
        analyzed.append(True)
        assert args == (data, metadata, inventory, diagnostic)
        return {"synthetic": True}

    def digest(path):
        hashed.append(path)
        return "changed" if changed_during_run and path == R.DISTANCES else str(path)

    monkeypatch.setattr(R, "source_json", source)
    monkeypatch.setattr(R, "digest", digest)
    monkeypatch.setattr(R, "analyze", analyze)
    report = {"inputs": {}, "log": []}
    if bad_provenance or changed_during_run:
        with pytest.raises(ValueError, match="provenance changed|source changed"):
            R.run(report)
        assert bool(analyzed) == changed_during_run
    else:
        R.run(report)
        assert report["status"] == "complete" and report["synthetic"]
    assert set(loaded) == set(paths)
    assert R.PLAN in hashed
    assert R.ROOT / "learn/set3_rank_calibration.py" in hashed
    assert R.ROOT / "tests/test_set3_rank_calibration.py" in hashed
