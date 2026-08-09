"""The atlas regressor stays deterministic, bounded, and honestly benchmarked."""

from __future__ import annotations

import json
import pathlib
import shlex

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("scipy", reason="needs the analysis extra")

from analysis.fingerprint import Fingerprint
from match import atlas
from match import space as space_module
from match.regressor import RidgeWarmStart
from match.renderer_synth import SyntheticRenderer
from scripts import benchmark_warm_start


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
    renderer = SyntheticRenderer().metadata().as_dict()
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
        "renderer": renderer,
        "measurement_caveat": None,
        "achievable_ranges": atlas.achievable_ranges([_printed(-8), _printed(8)]),
        "entries": [
            {"settings": {"pr12Amp/pr12Treble": 20.0},
             "fingerprint": _printed(-8)},
            {"settings": {"pr12Amp/pr12Treble": 80.0},
             "fingerprint": _printed(8)},
        ],
    }


def test_blend_zero_is_exact_nearest_and_blend_one_is_the_ridge_proposal():
    document = _document()
    space = space_module.build("morgan", amp="pr12")
    model = RidgeWarmStart(document, space)

    prediction = model.predict(Fingerprint.from_dict(_printed(0)), blend=0.0)

    assert prediction.nearest_index == 0
    assert prediction.settings == {
        "selectedAmp": 1,
        "pr12Amp/pr12Treble": 20.0,
    }
    assert prediction.ridge_settings["pr12Amp/pr12Treble"] == pytest.approx(50.0)
    assert model.blend_settings(
        prediction.ridge_settings, prediction.nearest_index, 1.0,
    ) == prediction.ridge_settings
    assert prediction.feature_overlap == 1.0
    assert prediction.clipped_feature_fraction == 0.0


def test_unreliable_controls_can_be_frozen_at_the_measured_nearest_point():
    document = _document()
    space = space_module.build("morgan", amp="pr12")
    model = RidgeWarmStart(document, space)
    prediction = model.predict(Fingerprint.from_dict(_printed(0)), blend=1.0)

    frozen = model.blend_settings(
        prediction.ridge_settings, prediction.nearest_index, 1.0,
        movable_paths=(),
    )

    assert frozen["pr12Amp/pr12Treble"] == 20.0
    with pytest.raises(atlas.AtlasError, match="not atlas dimensions"):
        model.blend_settings(
            prediction.ridge_settings, prediction.nearest_index, 1.0,
            movable_paths=("not/a/control",),
        )


def test_prediction_clips_features_and_parameters_to_measured_legal_bounds():
    document = _document()
    space = space_module.build("morgan", amp="pr12")
    model = RidgeWarmStart(document, space)

    prediction = model.predict(Fingerprint.from_dict(_printed(100)), blend=1.0)

    low, high = model.dimensions[0].bounds()
    value = prediction.settings["pr12Amp/pr12Treble"]
    assert low <= value <= high
    assert prediction.clipped_feature_fraction > 0.0


@pytest.mark.parametrize("alpha", [0.0, -1.0, float("inf"), float("nan")])
def test_regressor_rejects_invalid_penalties(alpha):
    with pytest.raises(atlas.AtlasError, match="alpha"):
        RidgeWarmStart(
            _document(), space_module.build("morgan", amp="pr12"), alpha=alpha)


def test_regressor_rejects_boolean_alpha_and_a_bare_movable_path():
    space = space_module.build("morgan", amp="pr12")
    with pytest.raises(atlas.AtlasError, match="alpha"):
        RidgeWarmStart(_document(), space, alpha=True)

    model = RidgeWarmStart(_document(), space)
    prediction = model.predict(Fingerprint.from_dict(_printed(0)))
    with pytest.raises(atlas.AtlasError, match="sequence of full paths"):
        model.blend_settings(
            prediction.ridge_settings, prediction.nearest_index, 1.0,
            movable_paths="pr12Amp/pr12Treble",
        )


def test_benchmark_defaults_to_distinct_unseen_tuning_and_test_seeds():
    parser = benchmark_warm_start.build_parser()
    args = parser.parse_args(["--atlas", "atlas.json", "--out", "result.json"])

    assert args.renderer is None
    assert args.tune_seed == 31
    assert args.test_seed == 43
    assert args.tune_seed != args.test_seed
    space = space_module.build("morgan", amp="pr12")
    dimensions = [space.by_path("pr12Amp", "pr12Treble")]
    tune = atlas.latin_hypercube(
        dimensions, 4, args.tune_seed)
    test = atlas.latin_hypercube(
        dimensions, 4, args.test_seed)
    assert not ({benchmark_warm_start._row_key(row) for row in tune} &
                {benchmark_warm_start._row_key(row) for row in test})


def test_candidate_order_is_balanced_across_reused_plugin_targets():
    blends = (0.0, 0.25, 0.5)

    assert benchmark_warm_start._rotated(blends, 0) == (0.0, 0.25, 0.5)
    assert benchmark_warm_start._rotated(blends, 1) == (0.25, 0.5, 0.0)
    assert benchmark_warm_start._rotated(blends, 2) == (0.5, 0.0, 0.25)
    assert benchmark_warm_start._rotated(blends, 3) == blends


def test_benchmark_refuses_a_renderer_that_does_not_match_the_atlas():
    document = _document()
    metadata = SyntheticRenderer().metadata()
    benchmark_warm_start._require_matching_renderer(document, metadata)

    document["renderer"] = dict(document["renderer"], plugin_version="different")
    with pytest.raises(atlas.AtlasError, match="plugin_version"):
        benchmark_warm_start._require_matching_renderer(document, metadata)


def test_nonreproducible_benchmark_result_requires_a_caveat():
    document = {
        "schema": benchmark_warm_start.SCHEMA,
        "renderer": {"reproducible": False},
        "measurement_caveat": "",
        "tuning": {"seed": 31, "selected_blend": 0.5},
        "testing": {"seed": 43, "selected": {"blend": 0.5}},
    }

    with pytest.raises(atlas.AtlasError, match="must carry"):
        benchmark_warm_start._validate_result(document)


def test_committed_benchmark_records_the_negative_gate_and_exact_command():
    path = ROOT / "packs" / "morgan" / "warm_start_benchmark_pr12.json"
    document = json.loads(path.read_text())

    benchmark_warm_start._validate_result(document)
    assert document["renderer"]["plugin_version"] == "1.1.1"
    assert document["renderer"]["reproducible"] is False
    assert "reproducible=False" in document["measurement_caveat"]
    assert document["model"]["minimum_cv_r2"] == 0.7
    assert len(document["model"]["movable_paths"]) == 9
    assert document["tuning"]["selected_blend"] == 0.0
    assert document["tuning"]["summaries"]["0"]["mean"] == pytest.approx(
        0.5629853647)
    assert document["tuning"]["summaries"]["0.25"]["mean"] == pytest.approx(
        0.5746641015)
    assert document["testing"]["nearest"]["mean"] == pytest.approx(0.6213143499)
    assert document["testing"]["beats_nearest"] is False

    command = shlex.split(document["build"]["command"])
    assert command[0] == document["build"]["python_executable"]
    assert command[command.index("--out") + 1] == str(path.relative_to(ROOT))
    package_data = (ROOT / "pyproject.toml").read_text().split(
        "[tool.setuptools.package-data]", 1)[1].split("\n[", 1)[0]
    assert '"*/warm_start_benchmark_*.json"' in package_data
