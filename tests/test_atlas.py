"""The M7 response atlas stays deterministic, qualified, and queryable."""

from __future__ import annotations

import json
import pathlib
import shlex
import subprocess
import sys

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

from analysis.fingerprint import Fingerprint
from match import atlas
from match import space as space_module
from match.renderer_synth import SyntheticRenderer
from scripts import build_response_atlas as atlas_builder
from scripts.match_preset import _seed_from_template


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _printed(tilt: float) -> dict:
    return Fingerprint(
        source={"regime": "probe", "channels": 1, "lufs_i": -18.0},
        spectrum={
            "band_centres_hz": [100.0, 1000.0, 10000.0],
            "band_db": [-4.0, 0.0, float(tilt)],
            "tilt_db_per_decade": float(tilt),
            "centroid_hz": {"p50": 1000.0 + 10.0 * tilt},
            "rolloff85_hz": {"p50": 5000.0 + 10.0 * tilt},
            "lf_corner_hz": 80.0,
            "hf_corner_hz": 12000.0,
        },
        dynamics={"crest_db": 10.0},
    ).to_dict()


def _document() -> dict:
    return {
        "schema": atlas.SCHEMA,
        "pack": "morgan",
        "amp": "pr12",
        "sample_count": 2,
        "latin_hypercube_seed": 17,
        "dimensions": ["pr12Amp/pr12Treble"],
        "fixed_settings": {"selectedAmp": 1},
        "probe": {"sha256": "abc", "sample_rate": 48000,
                  "channels": 1, "duration_s": 1.0},
        "renderer": SyntheticRenderer().metadata().as_dict(),
        "measurement_caveat": None,
        "achievable_ranges": atlas.achievable_ranges([_printed(-8), _printed(8)]),
        "entries": [
            {"settings": {"pr12Amp/pr12Treble": 20.0},
             "fingerprint": _printed(-8)},
            {"settings": {"pr12Amp/pr12Treble": 80.0},
             "fingerprint": _printed(8)},
        ],
    }


def test_pr12_topology_selects_pr12_and_only_samples_live_continuous_controls():
    space = space_module.build("morgan", amp="pr12")
    values, _ = _seed_from_template(
        ROOT / "samples" / "Example_Clean_PR12.xml", space, "morgan")
    fixed = atlas.tone_topology(values, space, "pr12")
    dimensions = atlas.sampling_dimensions(space, fixed)

    assert fixed[("", "selectedAmp")] in (1, "1")
    assert len(dimensions) == 26
    assert "pr12Amp/pr12Volume" in {dimension.path for dimension in dimensions}
    assert "cabParameters/rightCabDistance" in {
        dimension.path for dimension in dimensions}
    assert all(d.continuous for d in dimensions)
    assert not any("sw50r" in d.path or "Active" in d.path for d in dimensions)
    assert all(fixed.get(tuple(path.split("/"))) is False
               for path in atlas.TONE_EFFECT_BYPASSES)


def test_latin_hypercube_is_deterministic_and_covers_every_stratum():
    space = space_module.build("morgan", amp="pr12")
    dimension = space.by_path("pr12Amp", "pr12Treble")
    first = atlas.latin_hypercube([dimension], 8, 7)
    second = atlas.latin_hypercube([dimension], 8, 7)

    assert first == second
    # Rotation controls quantise to 0.5%, much finer than an eighth of the range.
    strata = {min(7, int(row[dimension.path] / 12.5)) for row in first}
    assert strata == set(range(8))


def test_neutral_baseline_centres_sampled_controls_but_keeps_the_topology():
    space = space_module.build("morgan", amp="pr12")
    fixed = {
        "selectedAmp": 1,
        "pr12EQ/pr12EQActive": True,
        "pr12Amp/pr12Treble": 87.0,
        "pr12EQ/pr12EQBand1": -9.0,
    }
    dimensions = [
        space.by_path("pr12Amp", "pr12Treble"),
        space.by_path("pr12EQ", "pr12EQBand1"),
    ]

    neutral = atlas.neutral_settings(fixed, dimensions)

    assert neutral["selectedAmp"] == 1
    assert neutral["pr12EQ/pr12EQActive"] is True
    assert neutral["pr12Amp/pr12Treble"] == 50.0
    assert neutral["pr12EQ/pr12EQBand1"] == 0.0


def test_nearest_returns_combined_fixed_and_sampled_settings():
    document = _document()
    target = Fingerprint.from_dict(_printed(8))

    match = atlas.nearest(document, target)[0]

    assert match.index == 1
    assert match.score == pytest.approx(0.0)
    assert match.settings == {
        "selectedAmp": 1,
        "pr12Amp/pr12Treble": 80.0,
    }


def test_achievability_reports_a_target_outside_the_sampled_range():
    document = _document()
    target = Fingerprint.from_dict(_printed(12))

    outside = atlas.outside_ranges(document, target)

    tilt = next(row for row in outside
                if row["feature"] == "spectral_tilt_db_per_decade")
    assert tilt == {
        "feature": "spectral_tilt_db_per_decade",
        "direction": "above",
        "value": 12.0,
        "sampled_min": -8.0,
        "sampled_max": 8.0,
    }
    assert atlas.uncomparable_features(document, target) == []


def test_a_feature_neither_side_measured_is_named_rather_than_called_inside():
    """`outside_ranges` skips it silently; the reader has to be told which."""
    document = _document()
    del document["achievable_ranges"]["crest_db"]
    printed = _printed(0)
    printed["spectrum"]["lf_corner_hz"] = None
    target = Fingerprint.from_dict(printed)

    assert atlas.outside_ranges(document, target) == []
    assert atlas.uncomparable_features(document, target) == [
        "crest_db", "low_frequency_corner_hz"]


def test_scale_comparison_requires_one_identical_held_out_experiment():
    baseline = _document()
    candidate = _document()
    baseline["build"] = {"validation": {
        "samples": 2, "seed": 29, "profile": "unpaired-v1",
        "neutral_mean": 2.0, "atlas_mean": 1.5,
        "neutral_median": 2.0, "atlas_median": 1.5,
        "atlas_win_rate": 0.5, "beats_neutral": True,
        "outcomes": [
            {"index": 0, "neutral_score": 2.0, "atlas_score": 1.0},
            {"index": 1, "neutral_score": 2.0, "atlas_score": 2.0},
        ],
    }}
    candidate["build"] = {"validation": {
        "samples": 2, "seed": 29, "profile": "unpaired-v1",
        "neutral_mean": 2.0, "atlas_mean": 1.0,
        "neutral_median": 2.0, "atlas_median": 1.0,
        "atlas_win_rate": 1.0, "beats_neutral": True,
        "outcomes": [
            {"index": 0, "neutral_score": 2.0, "atlas_score": 0.5},
            {"index": 1, "neutral_score": 2.0, "atlas_score": 1.5},
        ],
    }}

    comparison = atlas.compare_scale(baseline, candidate)

    assert comparison["mean_reduction_fraction"] == pytest.approx(1 / 3)
    assert comparison["candidate_better_targets"] == 2
    assert comparison["median_target_reduction_fraction"] == pytest.approx(0.375)

    candidate["build"]["validation"]["seed"] = 30
    with pytest.raises(atlas.AtlasError, match="different held-out seed"):
        atlas.compare_scale(baseline, candidate)


def test_nonreproducible_measurements_cannot_lose_their_caveat():
    document = _document()
    document["renderer"] = dict(document["renderer"], reproducible=False)
    with pytest.raises(atlas.AtlasError, match="must carry its measurement caveat"):
        atlas.validate(document)


def test_achievable_ranges_refuse_unknown_or_backwards_bounds():
    document = _document()
    document["achievable_ranges"]["brightness_centroid_hz"] = {
        "min": 2000.0, "max": 1000.0,
    }
    with pytest.raises(atlas.AtlasError, match="not a finite min/max"):
        atlas.validate(document)

    document = _document()
    document["achievable_ranges"]["marketing_warmth"] = {"min": 0.0, "max": 1.0}
    with pytest.raises(atlas.AtlasError, match="unknown response features"):
        atlas.validate(document)


def test_build_provenance_is_allowed_and_survives_load(tmp_path):
    document = _document()
    document["build"] = {"command": "python scripts/build_response_atlas.py"}
    path = tmp_path / "atlas.json"
    path.write_text(json.dumps(document))

    assert atlas.load(path)["build"]["command"].startswith("python ")


def test_python_provenance_is_portable_without_rewriting_external_interpreters(
        monkeypatch):
    monkeypatch.setattr(
        atlas_builder.sys, "executable", str(ROOT / ".venv" / "bin" / "python"))
    assert atlas_builder._portable_executable() == ".venv/bin/python"

    external = pathlib.Path("/opt/hostedtoolcache/Python/3.13/bin/python")
    monkeypatch.setattr(atlas_builder.sys, "executable", str(external))
    assert atlas_builder._portable_executable() == str(external)


def test_committed_pr12_atlases_are_valid_qualified_and_record_exact_provenance():
    expected = {
        "response_atlas_pr12_pilot.json": 128,
        "response_atlas_pr12_1024.json": 1024,
    }
    documents = {}
    for filename, samples in expected.items():
        path = ROOT / "packs" / "morgan" / filename
        document = atlas.load(path)
        documents[samples] = document

        assert document["sample_count"] == samples
        assert len(document["dimensions"]) == 26
        assert document["renderer"]["plugin_version"] == "1.1.1"
        assert document["renderer"]["reproducible"] is False
        assert "reproducible=False" in document["measurement_caveat"]
        validation = document["build"]["validation"]
        assert validation["samples"] == 24
        assert validation["beats_neutral"] is True
        command = shlex.split(document["build"]["command"])
        assert command[0] == document["build"]["python_executable"]
        assert document["build"]["python_executable"] == ".venv/bin/python"
        assert command[command.index("--out") + 1] == str(path.relative_to(ROOT))

    comparison = atlas.compare_scale(documents[128], documents[1024])
    assert comparison["candidate_better_targets"] == 23
    assert comparison["mean_reduction_fraction"] == pytest.approx(0.2836220902)
    package_data = (ROOT / "pyproject.toml").read_text().split(
        "[tool.setuptools.package-data]", 1)[1].split("\n[", 1)[0]
    assert '"*/response_atlas_*.json"' in package_data


def test_dry_run_is_plugin_free_and_names_the_render_arithmetic(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_response_atlas.py"),
         "--renderer", "swift", "--samples", "16", "--held-out", "4",
         "--template", str(ROOT / "samples" / "Example_Clean_PR12.xml"),
         "--out", str(tmp_path / "atlas.json"), "--dry-run"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "26 continuous dimensions" in result.stdout
    assert "21 renders total" in result.stdout
    assert "--dry-run" in result.stdout
    assert not (tmp_path / "atlas.json").exists()


def test_compare_cli_reproduces_the_committed_scale_result_without_a_plugin():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "compare_response_atlases.py"),
         "--baseline", str(ROOT / "packs" / "morgan" /
                             "response_atlas_pr12_pilot.json"),
         "--candidate", str(ROOT / "packs" / "morgan" /
                              "response_atlas_pr12_1024.json")],
        cwd=ROOT, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "reproducible=False" in result.stdout
    assert "mean: 0.814 -> 0.583 (28.4% lower)" in result.stdout
    assert "candidate better on 23/24 targets" in result.stdout


def test_query_cli_writes_ranked_specs_without_a_plugin(tmp_path):
    atlas_path = tmp_path / "atlas.json"
    atlas_path.write_text(json.dumps(_document()))
    from tests.fixtures_audio import harmonic_note, write_wav

    reference = tmp_path / "reference.wav"
    write_wav(reference, harmonic_note(seconds=1.2))
    out = tmp_path / "out"

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "query_response_atlas.py"),
         "--atlas", str(atlas_path), "--reference", str(reference),
         "--reference-mode", "probe", "--limit", "2", "--out-dir", str(out)],
        cwd=ROOT, capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "2 stored responses" in result.stdout
    assert "entry" in result.stdout
    specs = [json.loads((out / f"atlas-{rank}.json").read_text())
             for rank in (1, 2)]
    assert all(spec["parameters"][0] == {
        "module": "", "key": "selectedAmp", "value": 1,
    } for spec in specs)


def test_query_refuses_a_waveform_residual_the_atlas_does_not_store(tmp_path):
    atlas_path = tmp_path / "atlas.json"
    atlas_path.write_text(json.dumps(_document()))
    from tests.fixtures_audio import harmonic_note, write_wav

    reference = tmp_path / "reference.wav"
    write_wav(reference, harmonic_note(seconds=1.2))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "query_response_atlas.py"),
         "--atlas", str(atlas_path), "--reference", str(reference),
         "--loss-profile", "paired-v1", "--out-dir", str(tmp_path / "out")],
        cwd=ROOT, capture_output=True, text=True,
    )

    assert result.returncode == 2
    assert "stores fingerprints rather than waveforms" in result.stderr
