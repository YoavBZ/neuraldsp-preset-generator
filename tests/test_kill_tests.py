"""The kill tests' pieces: the band test, the activity gate, the aligned distance they
were declared under, the rule set every panel render gets, and the judge re-score's
verdict rule and its refusals."""

from __future__ import annotations

import json
import math
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "research"))

np = pytest.importorskip("numpy", reason="needs the analysis extra")
pytest.importorskip("pyloudnorm", reason="needs the analysis extra")

import kill_tests as K  # noqa: E402
import kill_tests_judge as J  # noqa: E402
import render_preset_panel as P  # noqa: E402

SR = 48000


def _notes(seconds=10.0, silent=None):
    t = np.arange(int(seconds * SR)) / SR
    di = 0.2 * np.sin(2 * np.pi * 110 * t) * (np.sin(2 * np.pi * 2 * t) > 0)
    if silent:
        di[int(silent[0] * SR): int(silent[1] * SR)] = 0.0
    return di


def test_the_band_test_is_exact_and_two_sided():
    rows = [{"band": b, "x": v} for b, v in (("a", -0.2), ("a", -0.4), ("b", -0.1), ("c", -0.3))]
    out = K.band_stat(rows, "x")
    assert out["band_median_log_ratio"] == pytest.approx(-0.3)
    assert out["bands"] == 3 and out["bands_better"] == 3 and out["parts_better"] == 4
    assert out["sign_flip_p_two_sided"] == pytest.approx(2 / 2 ** 3)
    assert out["gain"] == pytest.approx(1 - math.exp(-0.3), abs=1e-4)


def test_the_activity_gate_counts_where_the_di_plays():
    di = _notes(silent=(1.0, 5.5))
    assert K.active_fraction(di, 1.0, 5.5) < 0.05
    assert K.active_fraction(di, 5.5, 10.0) > 0.3


def test_alm_is_zero_for_the_same_audio_on_its_own_timeline():
    di = _notes()
    render = np.tanh(4 * di)
    shift = 480
    recording = np.concatenate([np.zeros(shift), render])[: len(render)]
    assert K.alm(recording, render, di, shift, 1.0, 9.0) == pytest.approx(0.0, abs=1e-6)
    louder = np.concatenate([np.zeros(shift), 1.5 * np.tanh(6 * di)])[: len(render)]
    assert K.alm(louder, render, di, shift, 1.0, 9.0) > 0.1


def test_every_panel_render_gets_the_rule_set():
    """The first panel played six presets pitch-shifted because R left transpose alone."""
    assert P.RULE_SET["parameters/transpose"] == 0
    assert P.RULE_SET["fxParameters/sectionActive"] is True
    for effect in ("reverb/reverbActive", "delay/delayActive"):
        assert P.RULE_SET[effect] is False


def test_a_panel_directory_is_resumed_only_under_its_own_configuration(tmp_path):
    config = {"amp": "sw50r", "format": "FLOAT"}
    assert P.check_out_dir(tmp_path, config) is None              # new: stamped
    assert P.check_out_dir(tmp_path, config) is None              # same: resumed
    assert "another configuration" in P.check_out_dir(tmp_path, {**config, "format": "PCM_24"})
    old = tmp_path / "old"
    (old / "part").mkdir(parents=True)
    (old / "part" / "x.wav").write_bytes(b"")                     # renders, no stamp
    assert "no record" in P.check_out_dir(old, config)


def test_the_judge_reads_alm_k3_as_declared_from_unrounded_rows():
    rows = [{"band": "a", "model": -0.2}, {"band": "b", "model": -0.1053606},
            {"band": "c", "model": -0.3}]
    k3 = {"model_vs_templateR": {"band_median_log_ratio": -0.1054, "parts_better": 3,
                                 "parts": 3},
          "model_better_than_shuffled": 2, "model_better_than_constant": 2, "parts": 3,
          "rows": rows}
    assert J.unrounded_band_median(rows, "model") == pytest.approx(-0.2)
    assert J.k3_alm_pass(k3)
    k3["model_better_than_constant"] = 1.5                # half a part short of a majority
    assert not J.k3_alm_pass(k3)
    # Rounded to four places, -0.10535 reads -0.1054 and would clear log 0.9 (-0.105361);
    # unrounded it does not.
    near = [{"band": b, "model": -0.10535} for b in "abc"]
    k3.update(rows=near, model_better_than_constant=2)
    k3["model_vs_templateR"]["band_median_log_ratio"] = -0.1054
    assert not J.k3_alm_pass(k3)


def _fixture(tmp_path, older_outputs):
    """A one-part panel, crops, lag table and K1-K3 outputs for the judge script."""
    part = "telefunken-Fragments-GTR"                     # any catalogued part name
    di = _notes()
    crops = tmp_path / "crops" / part
    crops.mkdir(parents=True)
    import soundfile as sf

    sf.write(crops / "di.wav", di, SR)
    sf.write(crops / "reference.wav", np.tanh(4 * di), SR)
    panel = tmp_path / "panel"
    panel.mkdir()
    render = panel / "r.wav"
    sf.write(render, np.tanh(4 * di), SR)
    index = {"rows": [{"part": part, "candidate": c, "file": str(render)}
                      for c in ("template+R", "factory:x")]}
    outputs = {}
    for name, body in (("k.json", {"panel": str(panel), "k1": {}, "k1_rows": {"alm": []},
                                   "k1_excluded": []}),
                       ("k3.json", {"panel": str(panel), "picks": {}, "shuffled_picks": {},
                                    "results": {"alm": {}}})):
        outputs[name] = tmp_path / name
        outputs[name].write_text(json.dumps(body))
    (panel / "index.json").write_text(json.dumps(index))
    if older_outputs:
        for path in outputs.values():
            os.utime(path, (1, 1))
    lags = tmp_path / "lags.json"
    lags.write_text(json.dumps({"panel": str(panel), "lags": {part: {"lag": 0}}}))
    return panel, tmp_path / "crops", lags, outputs


def _judge(panel, crops, lags, outputs, *extra):
    return subprocess.run(
        [sys.executable, str(ROOT / "research" / "kill_tests_judge.py"), "--panel-dir", str(panel),
         "--crops-dir", str(crops), "--lags", str(lags), "--k-json", str(outputs["k.json"]),
         "--k3-json", str(outputs["k3.json"]), "--workers", "1", *extra],
        capture_output=True, text=True)


def test_the_judge_refuses_outputs_older_than_the_panel(tmp_path):
    result = _judge(*_fixture(tmp_path, older_outputs=True))
    assert result.returncode != 0 and "older than the panel" in result.stderr + result.stdout


def test_the_judge_refuses_outputs_for_another_panel(tmp_path):
    panel, crops, lags, outputs = _fixture(tmp_path, older_outputs=False)
    body = json.loads(outputs["k3.json"].read_text())
    body["panel"] = str(tmp_path / "elsewhere")
    outputs["k3.json"].write_text(json.dumps(body))
    result = _judge(panel, crops, lags, outputs)
    assert result.returncode != 0 and "another panel" in result.stderr + result.stdout
