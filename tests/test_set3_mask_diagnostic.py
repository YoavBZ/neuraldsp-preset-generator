"""Synthetic checks only: never read the real development inputs or audio."""
import copy
import json
import math
from types import SimpleNamespace

import pytest

from learn import set3_mask_diagnostic as D


def synthetic_inputs():
    parts = [{"slug": f"band{i:02}-{suffix}", "band": f"band{i:02}",
              "split": "development", "judge_lag_samples": -49}
             for i in range(11) for suffix in ("a", "b", "c")]
    parts[2]["slug"] = D.TARGET
    metadata = {"parts": list(reversed(parts)) + [
        {"slug": "reserved-part", "band": "reserved", "split": "held_out"}],
        "held_out_bands": ["reserved"]}
    names = [f"factory:p{i:02}" for i in range(44)] + [D.TEMPLATE]
    distances = {}
    for p in parts:
        net = dict.fromkeys(names, 3.0)
        net[names[0]] = 1.0
        if p["slug"] == D.TARGET:
            net = dict.fromkeys(names)
        b = dict.fromkeys(names, 10.0)
        b[names[1]], b[names[2]] = 5.0, 20.0
        distances[p["slug"]] = {
            f"{bs}|sw50r|{kind}": copy.deepcopy(values)
            for bs in D.BAND_SETS
            for kind, values in (("net_A", net), ("measure_A", dict.fromkeys(names, 2.0)),
                                 ("measure_B", b))}
    diagnostic = {"parts": 33, "bands": 11, "cells": {}}
    for bs in D.BAND_SETS:
        constants = {band: {"preset": "factory:p43",
                            "training_parts": [p["slug"] for p in parts if p["band"] != band],
                            "eligible_medians_raw_A": {"factory:p43": 123.0}}
                     for band in {p["band"] for p in parts}}
        inclusive = copy.deepcopy(constants)
        for audit in inclusive.values():
            audit["preset"] = D.TEMPLATE
        diagnostic["cells"][f"{bs}|sw50r"] = {
            "parts": 33, "bands": 11, "menu_size": 45,
            "constants_by_excluded_band": constants,
            "inclusive_constants_by_excluded_band": inclusive,
            "rows": [{"part": p["slug"], "band": p["band"],
                      "picks": {"rebuilt_di": None if p["slug"] == D.TARGET else names[0]},
                      "B": {"rebuilt_di": None if p["slug"] == D.TARGET else 10.0}}
                     for p in parts]}
    return metadata, distances, {"menus": {"sw50r": names}}, diagnostic


def distance(value, reason=None):
    return {"distance": value, "reason": reason if value is None else None,
            "tonal": value, "temporal": value, "offset_db": 0.0,
            "frames": 10, "bands": 64, "lag_samples": -52}


def scored_fixture(parts, distances, names):
    scored = {v: {bs: {} for bs in D.BAND_SETS} for v in D.VARIANTS}
    controls = sorted(p["slug"] for p in parts if p["slug"] != D.TARGET)
    for bs in D.BAND_SETS:
        for p in parts:
            slug = p["slug"]
            original = distances[slug][f"{bs}|sw50r|net_A"]
            scored["original"][bs][slug] = {n: distance(v, "synthetic refusal")
                                                for n, v in original.items()}
            for variant in ("known_di", "reference"):
                pick = names[1] if slug == D.TARGET or slug in controls[:3] else names[0]
                values = {n: distance(5.0) for n in names}
                values[pick] = distance(0.5)
                scored[variant][bs][slug] = values
    return scored


def test_fixed_panel_is_first_slug_in_each_band_plus_target_regardless_of_order():
    metadata, _, _, _ = synthetic_inputs()
    development, selected = D.select_parts(metadata)
    assert len(development) == 33
    assert [p["slug"] for p in selected] == sorted(
        [f"band{i:02}-a" for i in range(11)] + [D.TARGET])
    assert all(p["split"] == "development" for p in selected)
    metadata["parts"].reverse()
    assert D.select_parts(metadata) == (development, selected)


@pytest.mark.parametrize("change", ["missing_target", "duplicate", "band_overlap", "target_first",
                                   "invalid_slug", "lag_bool", "unexpected_split", "missing_part"])
def test_panel_membership_failures_are_execution_errors(change):
    metadata, _, _, _ = synthetic_inputs()
    target = next(p for p in metadata["parts"] if p["slug"] == D.TARGET)
    if change == "missing_target":
        target["slug"] = "no-target"
    elif change == "duplicate":
        metadata["parts"].append(copy.deepcopy(target))
    elif change == "band_overlap":
        metadata["held_out_bands"].append(target["band"])
    elif change == "target_first":
        for p in metadata["parts"]:
            if p["band"] == target["band"] and p is not target:
                p["slug"] = "z-" + p["slug"]
    elif change == "invalid_slug":
        target["slug"] = "../reserved"
    elif change == "lag_bool":
        target["judge_lag_samples"] = True
    elif change == "unexpected_split":
        target["split"] = "unknown"
    else:
        metadata["parts"].remove(target)
    with pytest.raises(ValueError):
        D.select_parts(metadata)


@pytest.mark.parametrize("judge_lag,length,expected", [
    (-50, 6, [0, 0, 1, 2, 3, 4]),  # raw lag +2, delay into reference time
    (-54, 6, [3, 4, 0, 0, 0, 0]),  # raw lag -2, advance into reference time
    (-52, 6, [1, 2, 3, 4, 0, 0]),
    (-50, 3, [0, 0, 1]),
    (100, 4, [0, 0, 0, 0]),
    (-100, 4, [0, 0, 0, 0]),
])
def test_known_di_shift_direction_and_both_zero_padded_edges(judge_lag, length, expected):
    np = pytest.importorskip("numpy")
    source = np.array([1.0, 2.0, 3.0, 4.0])
    result = D.known_di_proxy(source, judge_lag, length)
    assert result.tolist() == expected
    assert source.tolist() == [1, 2, 3, 4]


def test_known_di_rejects_malformed_signals_or_lags():
    pytest.importorskip("numpy")
    for source, lag in (([], -52), ([float("nan")], -52), ([[1]], -52), ([1], True)):
        with pytest.raises(ValueError):
            D.known_di_proxy(source, lag, 4)


def test_inventory_is_independent_of_score_rows_and_requires_all_45_everywhere():
    metadata, scores, inventory, _ = synthetic_inputs()
    parts, _ = D.select_parts(metadata)
    assert len(D.validate_scores(scores, parts, inventory)) == 45
    for missing_kind in ("net_A", "measure_A", "measure_B"):
        bad = copy.deepcopy(scores)
        bad[parts[0]["slug"]][f"union|sw50r|{missing_kind}"].pop("factory:p43")
        with pytest.raises(ValueError, match="incomplete candidate"):
            D.validate_scores(bad, parts, inventory)
    bad = copy.deepcopy(scores)
    for rows in bad.values():
        for values in rows.values():
            values.pop("factory:p43")
    with pytest.raises(ValueError, match="incomplete candidate"):
        D.validate_scores(bad, parts, inventory)
    inventory["menus"]["sw50r"].pop()
    with pytest.raises(ValueError, match="45-candidate"):
        D.validate_scores(scores, parts, inventory)


@pytest.mark.parametrize("bad", [True, -0.1, "1", math.nan, math.inf])
def test_invalid_non_null_scores_are_errors(bad):
    metadata, scores, inventory, _ = synthetic_inputs()
    parts, _ = D.select_parts(metadata)
    scores[parts[0]["slug"]]["recording|sw50r|net_A"]["factory:p00"] = bad
    with pytest.raises(ValueError, match="invalid raw"):
        D.validate_scores(scores, parts, inventory)


def test_reserved_or_missing_score_membership_is_never_excluded_silently():
    metadata, scores, inventory, _ = synthetic_inputs()
    parts, _ = D.select_parts(metadata)
    scores["reserved-part"] = {}
    with pytest.raises(ValueError, match="exactly match development"):
        D.validate_scores(scores, parts, inventory)
    del scores["reserved-part"]
    scores.pop(parts[0]["slug"])
    with pytest.raises(ValueError, match="exactly match development"):
        D.validate_scores(scores, parts, inventory)


def test_primitive_receives_unchanged_waveforms_and_only_fixed_judge_options():
    recording, render, proxy = object(), object(), object()

    def primitive(a, b, c, **kwargs):
        assert (a, b, c) == (recording, render, proxy)
        assert kwargs == {"lag": -52, "render_latency": 52, "sample_rate": 48000,
                          "start_s": 1.0, "end_s": 5.5, "bands": "union"}
        return SimpleNamespace(as_dict=lambda: distance(None, "the DI plays in too few frames"))

    assert D.measure_A(recording, render, proxy, "union", primitive)["reason"] == "the DI plays in too few frames"


def test_baseline_requires_absolute_tolerance_exact_nulls_and_exact_choice():
    cached = {"a": 2.0, "b": 3.0, "c": None}
    measured = {n: distance(v, "synthetic refusal") for n, v in cached.items()}
    measured["a"]["distance"] += 0.9e-6
    audit = D.baseline_comparison(cached, measured, {"a": 7.0, "b": 8.0, "c": None})
    assert audit["matches"] and audit["cached_chosen_B"] == 7.0
    measured["a"]["distance"] = 2.0 + 1.1e-6
    assert not D.baseline_comparison(cached, measured, {})["matches"]
    measured["a"]["distance"] = 2.0
    measured["c"] = distance(0.0)
    audit = D.baseline_comparison(cached, measured, {})
    assert not audit["candidates"]["c"]["null_state_matches"]
    assert not audit["matches"]
    # Tolerable numeric changes can still change a near-tied chooser: reject those.
    cached = {"a": 2.0, "b": 2.0}
    measured = {"a": distance(2.0 + .1e-6), "b": distance(2.0)}
    audit = D.baseline_comparison(cached, measured, {})
    assert all(x["matches"] for x in audit["candidates"].values())
    assert not audit["pick_matches_exactly"] and not audit["matches"]
    with pytest.raises(ValueError, match="reproduction disagreement"):
        D.require_baseline({"union": {"control": audit}})


def test_lexical_tie_break_zero_selection_and_separate_null_log_failures():
    assert D.choose({"z": 0.0, "a": 0.0, "refused": None}) == "a"
    assert D.choose({"a": None}) is None
    assert D.paired(0, 1) == {"raw": "win", "log_ratio": None, "ratio": None,
                              "failure": "nonpositive_log"}
    assert D.paired(None, 0)["failure"] == "refusal"
    assert D.paired(0, 0)["raw"] == "tie"
    assert D.paired(1e300, 1e-300)["log_ratio"] == pytest.approx(600 * math.log(10))
    assert D.paired(1e300, 1e-300)["ratio"] is None
    rows = [{"part": "a", "band": "A", "B": {"x": None, "y": 1}},
            {"part": "b", "band": "B", "B": {"x": 0, "y": 1}},
            {"part": "c", "band": "C", "B": {"x": 1, "y": 1}}]
    summary = D.summarize_pairs(rows, "x", "y")
    assert summary["required_parts"] == 3 and summary["scorable_log_parts"] == 1
    assert summary["refused_parts"] == ["a"] and summary["nonpositive_log_parts"] == ["b"]
    assert summary["raw_counts"] == {"win": 1, "loss": 0, "tie": 1}
    assert summary["band_medians"] == {"A": None, "B": None, "C": 0.0}


def test_constants_are_copied_from_full_33_without_refitting_on_the_selected_panel():
    metadata, scores, inventory, diagnostic = synthetic_inputs()
    parts, selected = D.select_parts(metadata)
    frozen = D.frozen_constants(diagnostic, parts, scores, inventory["menus"]["sw50r"])
    for bs in D.BAND_SETS:
        for band, audit in frozen[bs]["constant"].items():
            assert audit["preset"] == "factory:p43"  # A ties would choose p00 if refitted
            assert audit["eligible_medians_raw_A"] == {"factory:p43": 123.0}
            assert set(audit["training_parts"]) == {p["slug"] for p in parts if p["band"] != band}
            assert len(audit["training_parts"]) > len(selected)
    diagnostic["cells"]["union|sw50r"]["constants_by_excluded_band"]["band00"]["training_parts"].append(D.TARGET)
    with pytest.raises(ValueError, match="invalid full-development constant"):
        D.frozen_constants(diagnostic, parts, scores, inventory["menus"]["sw50r"])


def test_full_diagnostic_cached_original_pick_must_agree_exactly():
    metadata, scores, inventory, diagnostic = synthetic_inputs()
    parts, _ = D.select_parts(metadata)
    diagnostic["cells"]["recording|sw50r"]["rows"][0]["picks"]["rebuilt_di"] = "factory:p01"
    with pytest.raises(ValueError, match="original selection disagrees"):
        D.frozen_constants(diagnostic, parts, scores, inventory["menus"]["sw50r"])


def test_complete_report_has_saved_B_all_picks_refusals_constants_and_paired_effects():
    metadata, scores, inventory, diagnostic = synthetic_inputs()
    development, selected = D.select_parts(metadata)
    names = inventory["menus"]["sw50r"]
    constants = D.frozen_constants(diagnostic, development, scores, names)
    scored = scored_fixture(selected, scores, names)
    result = D.assemble(selected, scores, scored, constants)
    assert result["reference_eligible_for_separately_declared_all_development_check"]
    for bs in D.BAND_SETS:
        cell = result["cells"][bs]
        assert len(cell["rows"]) == 12
        assert len(cell["gate"]["improved_controls"]) == 3
        target = next(r for r in cell["rows"] if r["part"] == D.TARGET)
        assert target["B"]["original"] is None and target["B"]["reference"] == 5.0
        assert len(target["refusals_A"]["original"]) == 45
        assert cell["known_di_target_refusal_rescued"]
        summary = cell["comparisons"]["reference_vs_original"]
        assert summary["refused_parts"] == [D.TARGET]
        assert summary["raw_counts"] == {"win": 3, "loss": 0, "tie": 8}
        assert summary["scorable_log_parts"] == 11
        for row in cell["rows"]:
            saved_B = scores[row["part"]][f"{bs}|sw50r|measure_B"]
            assert row["B"] == {v: saved_B.get(n) for v, n in row["picks"].items()}
    # One band set failing cannot borrow improvements from the other.
    for part in selected:
        if part["slug"] != D.TARGET:
            scored["reference"]["union"][part["slug"]] = copy.deepcopy(
                scored["original"]["union"][part["slug"]])
    assert not D.assemble(selected, scores, scored, constants)[
        "reference_eligible_for_separately_declared_all_development_check"]


def gate_rows(improved=3, worse=1):
    rows = [{"part": D.TARGET, "picks": {"original": None, "reference": "p"},
             "B": {"original": None, "reference": 1.0}}]
    rows += [{"part": f"control-{i}", "picks": {"original": "o", "reference": "p"},
              "B": {"original": 10.0, "reference": 5.0 if i < improved else
                    20.0 if i < improved + worse else 10.0}} for i in range(11)]
    return rows


def test_exact_gate_three_improved_at_most_one_worse_target_rescue_and_no_new_missing():
    assert D.routing_gate(gate_rows(3, 1))["eligible"]
    assert not D.routing_gate(gate_rows(2, 1))["eligible"]
    assert not D.routing_gate(gate_rows(3, 2))["eligible"]
    rows = gate_rows(3, 1)
    rows[0]["picks"]["reference"] = None
    assert not D.routing_gate(rows)["eligible"]
    rows = gate_rows(3, 1)
    rows[-1]["picks"]["reference"] = None
    rows[-1]["B"]["reference"] = None
    gate = D.routing_gate(rows)
    assert gate["new_missing_control_selections"] == ["control-10"]
    assert not gate["eligible"]
    rows = gate_rows(2, 1)
    # A previously missing control becoming scorable is not a paired improvement.
    rows[-1]["picks"]["original"] = None
    rows[-1]["B"]["original"] = None
    assert not D.routing_gate(rows)["eligible"]


@pytest.mark.parametrize("role", ["original", "reference"])
def test_gate_fails_for_any_control_missing_B_even_when_three_other_controls_improve(role):
    rows = gate_rows(3, 1)
    rows[-1]["B"][role] = None
    gate = D.routing_gate(rows)
    assert gate["invalid_control_B_pairs"] == ["control-10"]
    assert not gate["gates"]["all_11_control_B_pairs_raw_valid"]
    assert not gate["eligible"]


def test_gate_requires_target_B_and_all_11_controls_but_accepts_zero_raw_B():
    rows = gate_rows(3, 1)
    rows[0]["B"]["reference"] = None
    assert not D.routing_gate(rows)["gates"]["target_rescued_B_raw_valid"]
    assert not D.routing_gate(rows)["eligible"]
    rows[0]["B"]["reference"] = 0.0
    rows[-1]["B"] = {"original": 0.0, "reference": 0.0}
    gate = D.routing_gate(rows)
    assert gate["eligible"]
    assert gate["nonpositive_log_controls"] == ["control-10"]
    assert D.paired(rows[0]["B"]["reference"], 1.0)["failure"] == "nonpositive_log"
    assert not D.routing_gate(rows[:-1])["eligible"]


@pytest.mark.parametrize("mismatch", [False, True])
def test_run_scores_all_original_cells_and_checks_them_before_any_variant(monkeypatch, mismatch):
    metadata, scores, inventory, diagnostic = synthetic_inputs()
    _, selected = D.select_parts(metadata)
    names = inventory["menus"]["sw50r"]
    scored = scored_fixture(selected, scores, names)
    diagnostic["inputs"] = {
        "metadata": {"path": str(D.METADATA), "sha256": "synthetic"},
        "distances": {"path": str(D.DATA / "distances.json"), "sha256": "synthetic"},
        "menu_inventory": {"path": str(D.INVENTORY), "sha256": "synthetic"},
        "script": {"path": str(D.ROOT / "learn/set3_diagnostic.py"), "sha256": "synthetic"}}

    def source(path, report, label):
        report["inputs"][label] = {"path": str(path), "sha256": "synthetic"}
        return {"metadata": metadata, "distances": scores, "menu_inventory": inventory,
                "full_development_diagnostic": diagnostic}[label]

    def stage(parts, candidate_names, assets, variants, report):
        assert len(parts) == 12 and len(candidate_names) == 45
        calls.append(variants)
        if variants != ("original",):
            assert all(a["matches"] for parts in report["original_baseline_comparisons"].values()
                       for a in parts.values())
        return {v: scored[v] for v in variants}

    if mismatch:
        # Last panel cell: even an all-null target must be checked, not excluded.
        scored["original"]["union"][D.TARGET][names[0]] = distance(0.0)
    calls = []
    monkeypatch.setattr(D, "source_json", source)
    monkeypatch.setattr(D, "digest", lambda _: "synthetic")
    monkeypatch.setattr(D, "asset_inventory", lambda parts, names: {p["slug"]: {} for p in parts})
    monkeypatch.setattr(D, "score_stage", stage)
    report = {"inputs": {}, "log": []}
    if mismatch:
        with pytest.raises(ValueError, match="baseline reproduction disagreement"):
            D.run(report)
        assert calls == [("original",)]
        assert len(report["original_baseline_comparisons"]["union"]) == 12
    else:
        D.run(report)
        assert calls == [("original",), ("known_di", "reference")]
        assert report["status"] == "complete"


def test_missing_file_fails_before_audio_and_leaves_an_exclusive_error_report(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "ROOT", tmp_path)
    monkeypatch.setattr(D.importlib.metadata, "version", lambda _: "synthetic")

    def missing(report):
        D.note(report, "synthetic preflight")
        D.asset_inventory([{"slug": "only-synthetic"}], ["factory:synthetic", D.TEMPLATE])

    monkeypatch.setattr(D, "DATA", tmp_path / "data")
    monkeypatch.setattr(D, "CROPS", tmp_path / "crops")
    monkeypatch.setattr(D, "run", missing)
    monkeypatch.setattr(D, "read_audio", lambda _: pytest.fail("must preflight before audio"))
    output = tmp_path / "tmp/error.json"
    with pytest.raises(FileNotFoundError, match="incomplete fixed development sources"):
        D.execute(output)
    report = json.loads(output.read_text())
    assert report["status"] == "execution_error"
    assert "synthetic preflight" in [e["message"] for e in report["log"]]
    assert "net/only-synthetic/di.npy" in report["error"]["message"]
    original = output.read_bytes()
    with pytest.raises(ValueError, match="new regular file"):
        D.execute(output)
    assert output.read_bytes() == original


def test_assets_use_only_selected_net_renders_and_saved_di_with_flac_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "DATA", tmp_path / "data")
    monkeypatch.setattr(D, "CROPS", tmp_path / "crops")
    slug, name = "synthetic", "factory:synthetic"
    paths = [D.CROPS / slug / "reference.wav", D.DATA / "net" / slug / "di.npy",
             D.DATA / "net" / slug / "done", D.DATA / "measure" / slug / "di.npy",
             D.DATA / "measure" / slug / "done"]
    import hashlib

    render = D.DATA / "net" / slug / "sw50r" / (hashlib.sha1(name.encode()).hexdigest()[:12] + ".flac")
    for path in paths + [render]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    assets = D.asset_inventory([{"slug": slug}], [name])
    assert assets[slug][f"render:{name}"] == render
    assert len(assets[slug]) == 6
    assert not any("heldout" in str(p) for p in assets[slug].values())
    # A symlink cannot redirect this entry point to other data.
    render.unlink()
    render.symlink_to(paths[0])
    with pytest.raises(FileNotFoundError, match="fixed development location"):
        D.asset_inventory([{"slug": slug}], [name])


def test_output_cannot_escape_tmp_or_overwrite_via_symlink(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "ROOT", tmp_path)
    (tmp_path / "tmp").mkdir()
    for path in (tmp_path / "elsewhere.json", tmp_path / "tmp/../escape.json"):
        with pytest.raises(ValueError):
            D.output_path(path)
    (tmp_path / "tmp/link").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        D.output_path(tmp_path / "tmp/link/escape.json")
    assert D.output_path(tmp_path / "tmp/new.json") == tmp_path / "tmp/new.json"
