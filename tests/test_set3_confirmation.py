"""Synthetic checks of the confirmation's data boundary and baseline selection."""

import json
import math
import pathlib
import plistlib
import types

import pytest

from learn import set3_confirmation as C


def panel():
    # Raw medians pick B; per-part ratios to template would pick A.
    return {slug: {f"{bs}|sw50r|measure_A": values.copy() for bs in C.BAND_SETS}
            for slug, values in {
                "one": {"factory:A": 1.0, "factory:B": 2.0, "template+R": 100.0},
                "two": {"factory:A": 10.0, "factory:B": 3.0, "template+R": 1.0},
                "three": {"factory:A": 11.0, "factory:B": 4.0, "template+R": 1000.0},
            }.items()}


def test_constant_uses_raw_distances_not_ratios_or_half_b():
    distances = panel()
    constants = C.select_constants(distances, list(distances), {"sw50r": ["factory:A", "factory:B", "template+R"]})
    assert constants["recording"]["sw50r"] == {"preset": "factory:B", "median_raw_A": 3.0}
    # Deliberately poisoned half-B data cannot change the constant.
    distances["one"]["recording|sw50r|measure_B"] = {"A": 0.0, "B": math.nan}
    assert C.select_constants(distances, list(distances), {"sw50r": ["factory:A", "factory:B", "template+R"]}) == constants


def test_every_part_and_candidate_must_use_the_same_development_panel():
    distances = panel()
    with pytest.raises(ValueError, match="exactly"):
        C.select_constants(distances, ["one", "two"], {"sw50r": ["factory:A", "factory:B", "template+R"]})
    del distances["two"]["union|sw50r|measure_A"]["factory:B"]
    with pytest.raises(ValueError, match="menu mismatch"):
        C.select_constants(distances, list(distances), {"sw50r": ["factory:A", "factory:B", "template+R"]})


@pytest.mark.parametrize("bad", [None, math.nan, math.inf, -1, True])
def test_undefined_development_distances_stop_selection(bad):
    distances = panel()
    distances["one"]["recording|sw50r|measure_A"]["factory:B"] = bad
    with pytest.raises(ValueError, match="undefined"):
        C.select_constants(distances, list(distances), {"sw50r": ["factory:A", "factory:B", "template+R"]})


def test_band_set_constants_are_separate_and_ties_use_names():
    distances = panel()
    for row in distances.values():
        row["union|sw50r|measure_A"] = {"factory:A": 1.0, "factory:B": 1.0, "template+R": 4.0}
    constants = C.select_constants(distances, list(distances), {"sw50r": ["factory:B", "factory:A", "template+R"]})
    assert constants["union"]["sw50r"]["preset"] == "factory:A"
    assert constants["recording"]["sw50r"]["preset"] == "factory:B"


def test_unapproved_manifest_stops_before_audio_or_asset_reads(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"version": 1, "split": "held_out", "approved": False}))
    monkeypatch.setattr(C, "sha256", lambda _: pytest.fail("read asset before approval check"))
    monkeypatch.setattr(C, "menu_hashes", lambda _: pytest.fail("read menu before approval check"))
    with pytest.raises(ValueError, match="approval"):
        C.validate_manifest(path, model="unused", amps=["sw50r", "pr12"], parts=[], out="unused")


def test_approval_flag_does_not_replace_a_declared_plan(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"version": 1, "split": "held_out", "approved": True}))
    plan = tmp_path / "plan.md"
    plan.write_text("# DRAFT\n\n**declared:** _(approval pending)_\n")
    monkeypatch.setattr(C, "PLAN", plan)
    monkeypatch.setattr(C, "_require_committed", lambda _: None)
    with pytest.raises(ValueError, match="not been declared"):
        C.validate_manifest(path, model="unused", amps=[], parts=[], out="unused")


def test_declared_inputs_must_match_the_committed_bytes(tmp_path, monkeypatch):
    path = tmp_path / "input.json"
    path.write_text("changed")
    monkeypatch.setattr(C, "ROOT", tmp_path)

    class Result:
        returncode = 0
        stdout = b"original"

    monkeypatch.setattr(C.subprocess, "run", lambda *a, **k: Result())
    with pytest.raises(ValueError, match="not committed"):
        C._require_committed(path)


def confirmation_panel():
    names = ["factory:chosen", "factory:constant", "factory:unused", "template+R"]
    manifest = {"amps": ["sw50r"], "menus": {"sw50r": dict.fromkeys(names, "hash")},
                "constants": {bs: {"sw50r": {"preset": "factory:constant"}} for bs in C.BAND_SETS}}
    parts = [{"slug": f"part-{i}", "band": f"band-{i}"} for i in range(6)]
    distances = {p["slug"]: {key: value.copy() for bs in C.BAND_SETS for key, value in (
        (f"{bs}|sw50r|net_A", dict(zip(names, [0.1, 0.5, None, 1.0]))),
        (f"{bs}|sw50r|measure_B", dict(zip(names, [0.8, 1.0, None, 2.0]))),
    )} for p in parts}
    return distances, parts, manifest


def test_six_band_sign_flips_and_unselected_refusals():
    distances, parts, manifest = confirmation_panel()
    cell = C.summarize(distances, parts, manifest)["recording|sw50r"]
    assert cell["passed"]
    assert cell["joint_win_share"] == 1
    assert cell["net_vs_constant"]["sign_flip_p_two_sided"] == 2 / 64
    assert cell["net_vs_constant"]["band_median_log_ratio"] == pytest.approx(math.log(0.8))


@pytest.mark.parametrize("bad", [None, 0.0, math.inf, math.nan])
def test_required_refusals_prevent_a_pass_and_retain_denominators(bad):
    distances, parts, manifest = confirmation_panel()
    distances["part-0"]["recording|sw50r|measure_B"]["factory:chosen"] = bad
    cell = C.summarize(distances, parts, manifest)["recording|sw50r"]
    assert not cell["passed"]
    assert cell["parts"] == 6 and cell["refusals"] == 1
    assert cell["joint_win_share"] == pytest.approx(5 / 6)
    assert cell["numeric_summaries_descriptive_only"]


def test_gates_do_not_use_rounded_effect_sizes():
    distances, parts, manifest = confirmation_panel()
    for row in distances.values():
        row["recording|sw50r|measure_B"]["factory:chosen"] = math.exp(math.log(0.95) + 1e-7)
    cell = C.summarize(distances, parts, manifest)["recording|sw50r"]
    assert not cell["gates"]["constant_margin"]
    assert not cell["passed"]


def test_joint_win_share_weights_bands_not_number_of_parts():
    distances, parts, manifest = confirmation_panel()
    # Five winning bands, one losing band with eleven parts: 5/6, not 5/16.
    for i in range(10):
        slug = f"extra-{i}"
        parts.append({"slug": slug, "band": "band-0"})
        distances[slug] = {k: v.copy() for k, v in distances["part-0"].items()}
    for p in parts:
        if p["band"] == "band-0":
            distances[p["slug"]]["recording|sw50r|measure_B"]["factory:chosen"] = 3.0
    cell = C.summarize(distances, parts, manifest)["recording|sw50r"]
    assert cell["joint_win_share"] == pytest.approx(5 / 6)
    assert cell["parts"] == 16


def test_missing_execution_outputs_abort_instead_of_becoming_refusals():
    distances, parts, manifest = confirmation_panel()
    del distances["part-0"]
    with pytest.raises(ValueError, match="exactly"):
        C.summarize(distances, parts, manifest)
    distances, parts, manifest = confirmation_panel()
    del distances["part-0"]["recording|sw50r|net_A"]["factory:unused"]
    with pytest.raises(ValueError, match="inventory"):
        C.summarize(distances, parts, manifest)


def test_template_cannot_be_the_constant_even_if_it_wins_development():
    distances = panel()
    for row in distances.values():
        for bs in C.BAND_SETS:
            row[f"{bs}|sw50r|measure_A"]["template+R"] = 0
    constants = C.select_constants(distances, list(distances),
                                   {"sw50r": ["factory:A", "factory:B", "template+R"]})
    assert constants["recording"]["sw50r"]["preset"] == "factory:B"


def test_timing_sensitivity_cannot_rescue_a_failed_primary_or_be_omitted():
    passed = {f"{bs}|sw50r": {"passed": True} for bs in C.BAND_SETS}
    failed = {**passed, "union|sw50r": {"passed": False}}
    verdict = C.combined_verdict(passed, failed, ["sw50r"])["sw50r"]
    assert verdict["verdict_changed"] and not verdict["confirmed_amp_track_only"]
    assert not C.combined_verdict(failed, passed, ["sw50r"])["sw50r"]["confirmed_amp_track_only"]
    with pytest.raises(KeyError):
        C.combined_verdict(passed, {}, ["sw50r"])


@pytest.fixture
def frozen_inputs(tmp_path, monkeypatch):
    from learn import set3

    monkeypatch.setattr(C, "ROOT", tmp_path)
    monkeypatch.setattr(C, "CODE", ("compute.py",))
    monkeypatch.setattr(C, "source_inventory", lambda: C.CODE)
    monkeypatch.setattr(C, "runtime_provenance", lambda: {"synthetic_runtime": 1})
    monkeypatch.setattr(C, "PLAN", tmp_path / "plan.md")
    monkeypatch.setattr(C, "AVERAGE", tmp_path / "average.npy")
    monkeypatch.setattr(set3, "DECLARATION", tmp_path / "split.json")
    monkeypatch.setattr(set3, "slugs", lambda split: list(panel()) if split == "development" else ["reserved"])
    monkeypatch.setattr(C, "_require_committed", lambda _: None)
    menus = {"sw50r": {"factory:A": "hash-A", "factory:B": "hash-B", "template+R": "hash-T"}}
    monkeypatch.setattr(C, "menu_hashes", lambda _: menus)
    C.PLAN.write_text("# Confirmation\n\n**declared:** approved on a synthetic date\n")
    C.AVERAGE.write_bytes(b"synthetic average")
    set3.DECLARATION.write_text("synthetic split declaration")
    (tmp_path / "compute.py").write_text("# synthetic code\n")
    model, distances = tmp_path / "model.pt", tmp_path / "development.json"
    model.write_bytes(b"synthetic checkpoint")
    distances.write_text(json.dumps(panel()))
    out = tmp_path / "heldout-output"
    manifest = C.prepare(model=model, out=out, distances=distances, amps=("sw50r",))
    assert manifest["approved"] is False
    manifest["approved"] = True
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path, manifest, {"model": model, "amps": ["sw50r"], "parts": [{"slug": "reserved"}], "out": out}


def test_complete_synthetic_manifest_validates_without_audio(frozen_inputs):
    path, manifest, kwargs = frozen_inputs
    assert C.validate_manifest(path, **kwargs) == manifest


@pytest.mark.parametrize("target", ["model", "average", "code", "constant", "runtime"])
def test_frozen_input_changes_are_rejected(frozen_inputs, target, monkeypatch):
    path, manifest, kwargs = frozen_inputs
    if target == "code":
        (C.ROOT / "compute.py").write_text("changed")
    elif target == "runtime":
        monkeypatch.setattr(C, "runtime_provenance", lambda: {"synthetic_runtime": 2})
    elif target == "constant":
        manifest["constants"]["recording"]["sw50r"]["preset"] = "factory:A"
        path.write_text(json.dumps(manifest))
    else:
        pathlib.Path(manifest["assets"][target]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed|constants"):
        C.validate_manifest(path, **kwargs)


def test_runtime_inspection_reads_fake_bundle_without_instantiating_plugin(tmp_path, monkeypatch):
    pytest.importorskip("soundfile")
    from match.renderer_au import AudioUnitRenderer

    bundle = tmp_path / "Synthetic.component"
    (bundle / "Contents").mkdir(parents=True)
    (bundle / "Contents/Info.plist").write_bytes(plistlib.dumps({
        "CFBundleIdentifier": "synthetic", "CFBundleShortVersionString": "1", "CFBundleVersion": "2"}))
    (bundle / "Contents/binary").write_bytes(b"synthetic executable")
    monkeypatch.setattr(C, "COMPONENT", bundle)
    monkeypatch.setattr(C.importlib.metadata, "version", lambda name: "synthetic-version")
    monkeypatch.setattr(C.shutil, "which", lambda name: "/synthetic/swiftc")
    monkeypatch.setattr(C.platform, "platform", lambda: "synthetic-platform")
    monkeypatch.setattr(C.subprocess, "run", lambda *a, **k: types.SimpleNamespace(stdout="Swift synthetic", stderr=""))
    monkeypatch.setattr(AudioUnitRenderer, "_ensure_server", lambda *a: pytest.fail("plugin started"))
    provenance = C.runtime_provenance()
    assert provenance["audio_unit"]["identifier"] == "synthetic"
    assert provenance["audio_unit"]["files"]["Contents/binary"] == C.sha256(bundle / "Contents/binary")
    assert provenance["renderer"]["defaults"]["block_size"] == 512
    assert provenance["dependencies"]["torch"] == "synthetic-version"


def test_source_inventory_covers_transitive_sources_and_pack_config(monkeypatch):
    paths = ["match/renderer_au.py", "scripts/au_render_server.swift", "scripts/_swift.py",
             "analysis/io.py", "packs/morgan/manifest.json"]
    monkeypatch.setattr(C.subprocess, "run", lambda *a, **k:
                        types.SimpleNamespace(stdout=("\0".join(paths) + "\0").encode()))
    assert set(paths) <= set(C.source_inventory())
