"""Known-DI control tests use synthetic data/fake model only."""
import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")

import json
import hashlib
import math
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from learn import di_morgan_control as C


def panel():
    return [{"slug": f"take-{i}", "content": "chords" if i < 6 else "scales",
             "take": str(i), "di": f"dry-{i}", "micamp": "FORBIDDEN",
             "start_frame": 123} for i in range(12)]


def windows():
    return {n: np.ones(n) for n in C.P.FFTS}


def rows(gain=.8):
    return [{**t, "qc_valid": True, "morgan_input": 2., "morgan_net": 2.*gain, "oracle": 0.}
            for t in panel()]


def test_original_morgan_control_gate_boundary_and_no_extra_win_rule():
    assert C.compare(rows(.9), panel())["passed"]
    assert not C.compare(rows(.90001), panel())["passed"]
    r = rows(1.)
    for v in r[:6]:
        v["morgan_net"] = .4
    result = C.compare(r, panel())
    assert result["passed"] and result["strict_wins"] == 6
    assert result["group_medians"]["scales"] == 0
    assert result["median_relative_improvement"] == pytest.approx(.4, rel=0, abs=1e-15)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "identity", "group", "qc", "zero", "nan", "bool", "oracle"])
def test_invalid_coverage_or_losses_are_inconclusive(fault):
    r, takes = rows(), panel()
    if fault == "missing": r.pop()
    elif fault == "duplicate": r[-1] = r[0]
    elif fault == "identity": r[0]["take"] = "other"
    elif fault == "group": takes[0]["content"] = "scales"
    elif fault == "qc": r[0]["qc_valid"] = False
    elif fault == "zero": r[0]["morgan_input"] = 0.
    elif fault == "nan": r[0]["morgan_net"] = float("nan")
    elif fault == "bool": r[0]["oracle"] = False
    else: r[0]["oracle"] = 1e-6
    result = C.compare(r, takes)
    assert not result["valid"] and not result["passed"] and result["disposition"] == "INCONCLUSIVE"


def test_draft_before_old_guard_or_assets(tmp_path, monkeypatch):
    path = tmp_path / "draft"
    path.write_text("Draft")
    monkeypatch.setattr(C, "PLAN", path)
    monkeypatch.setattr(C.V, "code_inputs", lambda: pytest.fail("draft must stop first"))
    with pytest.raises(ValueError, match="declared"):
        C.code_inputs()


def test_swift_helper_drift_refuses_before_assets_and_changes_prerequisite_pins(tmp_path, monkeypatch):
    assert "scripts/_swift.py" in C.OWN_PINS
    monkeypatch.setattr(C, "ROOT", tmp_path)
    monkeypatch.setattr(C.V, "ROOT", tmp_path)
    plan = tmp_path / "docs/di-morgan-control-plan.md"
    monkeypatch.setattr(C, "PLAN", plan)
    for name in C.OWN_PINS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("**Declared: synthetic fixture**" if path == plan else f"synthetic:{name}")
    committed = {name: (tmp_path / name).read_bytes() for name in C.OWN_PINS}
    monkeypatch.setattr(C.V, "code_inputs", lambda: ({}, {"attribution": "synthetic"}, {"parent": "frozen"}))
    monkeypatch.setattr(C.subprocess, "check_output", lambda args, **kwargs: committed[args[-1].split(":", 1)[1]])
    monkeypatch.setattr(C, "assets", lambda: pytest.fail("drift must stop before external assets/catalog"))
    _, _, old = C.code_inputs()
    assert old["scripts/_swift.py"] == hashlib.sha256(committed["scripts/_swift.py"]).hexdigest()
    run = tmp_path / "tmp" / "control"
    metric = C.V.stage_directory(run, "metric", old, "synthetic")
    C.R.write_new(metric / "result.json", {"passed": True})
    helper = tmp_path / "scripts/_swift.py"
    helper.write_text("synthetic changed compiler flags")
    monkeypatch.setattr(sys, "prefix", str(tmp_path / ".venv"))
    monkeypatch.setattr(sys, "argv", ["control", "prepare", "--run", str(run)])
    with pytest.raises(ValueError, match="uncommitted control dependency: scripts/_swift.py"):
        C.main()
    assert not (run / "prepare").exists()
    # Even a newly committed helper must not reuse old successful preflights.
    committed["scripts/_swift.py"] = helper.read_bytes()
    _, _, changed = C.code_inputs()
    assert changed["scripts/_swift.py"] != old["scripts/_swift.py"]
    with pytest.raises(ValueError, match="pins changed"):
        C.V.stage_directory(run, "numpy", changed, "synthetic")
    assert not (run / "numpy").exists()


@pytest.mark.parametrize("reject", [False, True])
def test_prepare_all_dry_takes_no_microphone_alignment(tmp_path, monkeypatch, reject):
    for key, value in (("SR", 10), ("GUARD", 2), ("CALIBRATION", 40), ("SCORE", 60), ("TOTAL", 100)):
        monkeypatch.setattr(C.P, key, value)
    avg = tmp_path / "synthetic-average.npy"
    np.save(avg, np.zeros(4))
    output = tmp_path / "prepare"
    output.mkdir()
    raw = np.arange(104, dtype=float) / 100 + .1
    reads, qc_calls, targets, scored = [], [], [], []
    takes = panel()
    def read(path, start):
        assert path.startswith("dry-") and start == 123
        reads.append(path)
        return raw.copy()
    def qc(x):
        np.testing.assert_array_equal(x, raw[2:102])
        qc_calls.append(1)
        return {"valid": not(reject and len(qc_calls) == 4)}
    def target(x, avg):
        np.testing.assert_array_equal(x, raw[42:102])
        targets.append(x)
        return x**2
    def score(a, b, di, *, windows):
        assert set(windows) == set(C.P.FFTS)
        np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(di, raw[42:102])
        scored.append(a)
        return {"primary": 0., "canonical_waveform_l1": 0., "raw_lowband": .5}
    monkeypatch.setattr(C.P, "read_bounded", read)
    monkeypatch.setattr(C.P, "waveform_qc", qc)
    monkeypatch.setattr(C.P, "canonical_target", target)
    monkeypatch.setattr(C.P, "score_prediction", score)
    monkeypatch.setattr(C.P, "calibrate", lambda *a: pytest.fail("no pairing/lag fitting"))
    C.prepare(output, {"average": {"path": str(avg)}, "attribution": "synthetic"}, takes, windows())
    report = json.loads((output / "result.json").read_text())
    assert report["complete"] and report["valid"] is (not reject)
    assert len(reads) == 12 and len(qc_calls) == 12
    assert len(targets) == len(scored) == (11 if reject else 12)
    if reject:
        assert not report["rows"][3]["qc_valid"] and not (output / "take-3.npz").exists()
    with np.load(output / "take-0.npz", allow_pickle=False) as saved:
        np.testing.assert_array_equal(saved["di"], raw[42:102])
        np.testing.assert_array_equal(saved["target"], raw[42:102]**2)
        np.testing.assert_array_equal(saved["render_di"], raw[22:102])


def test_invalid_prepare_cannot_load_torch_or_model(tmp_path, monkeypatch):
    (tmp_path / "prepare").mkdir()
    C.R.write_new(tmp_path / "prepare/result.json", {"complete": True, "valid": False, "rows": panel()})
    monkeypatch.setitem(sys.modules, "torch", None)
    with pytest.raises(ValueError, match="valid declared coverage"):
        C.infer(tmp_path, tmp_path, {}, panel(), windows())


def test_infer_exact_raw_render_input_one_prediction_per_take(tmp_path, monkeypatch):
    takes = panel()
    for name in ("prepare", "render", "infer"):
        (tmp_path / name).mkdir()
    prepared = [{**t, "oracle_scores": {"primary": 0.}} for t in takes]
    C.R.write_new(tmp_path / "prepare/result.json", {"complete": True, "valid": True, "rows": prepared})
    C.R.write_new(tmp_path / "render/result.json", {"complete": True, "rows": takes})
    di = np.arange(60, dtype=float) / 1000 + .01
    x, baseline = di*2, di*3
    for t in takes:
        np.savez_compressed(tmp_path / "prepare" / f"{t['slug']}.npz", di=di, target=di**2)
        np.savez_compressed(tmp_path / "render" / f"{t['slug']}.npz", net_input=x, baseline=baseline)
    calls, score_calls, loaded = [], [], []
    net = SimpleNamespace(cpu=lambda: net, load_state_dict=loaded.append, eval=lambda: None)
    def load(path, **kwargs):
        assert path == "synthetic-model" and kwargs == {"map_location": "cpu", "weights_only": True}
        return "frozen-state"
    def rebuild(model, supplied, **kwargs):
        assert model is net and kwargs == {"device": "cpu"}
        np.testing.assert_array_equal(supplied, x.astype(np.float32))
        calls.append(supplied.copy())
        return supplied.astype(float)+.1
    supplied_windows = windows()
    def score(a, target, raw, *, windows):
        assert windows is supplied_windows
        np.testing.assert_array_equal(target, di**2)
        np.testing.assert_array_equal(raw, di)
        score_calls.append(a.copy())
        return {"primary": 1. if len(score_calls)%2 else 2., "canonical_waveform_l1": .1, "raw_lowband": .2}
    fake_d = SimpleNamespace(build_model=lambda: net, rebuild=rebuild)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(set_num_threads=lambda n: None,
                        device=lambda d: d, load=load, __version__="synthetic"))
    monkeypatch.setitem(sys.modules, "learn.direc", fake_d)
    monkeypatch.setattr(sys.modules["learn"], "direc", fake_d, raising=False)
    monkeypatch.setattr(C.P, "score_prediction", score)
    C.infer(tmp_path / "infer", tmp_path, {"model": {"path": "synthetic-model"}, "attribution": "synthetic"}, takes, supplied_windows)
    assert loaded == ["frozen-state"] and len(calls) == 12 and len(score_calls) == 24
    for i in range(12):
        np.testing.assert_array_equal(score_calls[2*i], x.astype(np.float32).astype(float)+.1)
        np.testing.assert_array_equal(score_calls[2*i+1], baseline)
    report = json.loads((tmp_path / "infer/result.json").read_text())
    assert report["complete"] and report["screen"]["passed"]
    assert report["screen"]["median_relative_improvement"] == .5
