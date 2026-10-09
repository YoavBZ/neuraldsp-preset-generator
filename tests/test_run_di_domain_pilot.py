"""Execution safety tests use only synthetic metadata and temporary directories."""
import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")

import json
import hashlib
import sys
from types import SimpleNamespace
import numpy as np
import pytest

from learn import run_di_domain_pilot as R


def test_draft_refuses_before_external_assets(tmp_path, monkeypatch):
    plan = tmp_path / "plan.md"
    plan.write_text("Draft; no execution allowed")
    monkeypatch.setattr(R, "PLAN", plan)
    monkeypatch.setattr(R, "sha", lambda _: pytest.fail("must not open model/average"))
    monkeypatch.setattr(R.subprocess, "check_output", lambda *a, **k: pytest.fail("no git needed"))
    with pytest.raises(ValueError, match="not approved"):
        R.frozen_inputs()


def test_json_outputs_exclusive_and_nonfinite_refused(tmp_path):
    out = tmp_path / "out.json"
    R.write_new(out, {"x": 1})
    with pytest.raises(FileExistsError):
        R.write_new(out, {"x": 2})
    assert json.loads(out.read_text()) == {"x": 1}
    with pytest.raises(ValueError):
        R.write_new(tmp_path / "bad.json", {"x": float("nan")})


def test_stage_outputs_and_prerequisites_are_exclusive(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "ROOT", tmp_path)
    run = tmp_path / "tmp" / "pilot"
    metric = R.stage_directory(run, "metric", {"x": "frozen"}, "credit")
    with pytest.raises(FileExistsError):
        R.stage_directory(run, "metric", {"x": "frozen"}, "credit")
    R.write_new(metric / "result.json", {"passed": True})
    native = R.stage_directory(run, "native", {"x": "frozen"}, "credit")
    assert native.exists()
    with pytest.raises(FileExistsError):
        R.stage_directory(run, "native", {"x": "frozen"}, "credit")
    with pytest.raises(ValueError, match="procedure changed"):
        R.stage_directory(run, "render", {"x": "changed"}, "credit")


def test_failed_metric_cannot_unlock_native(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "ROOT", tmp_path)
    run = tmp_path / "tmp" / "pilot"
    metric = R.stage_directory(run, "metric", {}, "credit")
    R.write_new(metric / "result.json", {"passed": False})
    with pytest.raises(ValueError, match="prerequisite failed"):
        R.stage_directory(run, "native", {}, "credit")
    assert not (run / "native").exists()


def test_output_cannot_escape_project_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="under project tmp"):
        R.stage_directory(tmp_path / "elsewhere", "metric", {}, "credit")
    assert not (tmp_path / "elsewhere").exists()


def test_stage_deadline(monkeypatch):
    monkeypatch.setattr(R.time, "monotonic", lambda: 1000)
    with pytest.raises(TimeoutError, match="partial evidence retained"):
        R.check_time(0)
    R.check_time(999)


@pytest.mark.parametrize("fault", ["duplicate", "missing", "wrong", "incomplete", "invalid"])
def test_stage_coverage_refuses_before_expensive_work(tmp_path, fault):
    expected = [{"slug": f"take-{i}"} for i in range(12)]
    report = {"complete": True, "valid": True, "rows": [dict(r) for r in expected]}
    if fault == "duplicate":
        report["rows"][-1] = report["rows"][0]
    elif fault == "missing":
        report["rows"].pop()
    elif fault == "wrong":
        report["rows"][-1]["slug"] = "not-declared"
    elif fault == "incomplete":
        report["complete"] = False
    else:
        report["valid"] = False
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="declared coverage"):
        R.require_report(path, "valid", expected)


def test_stage_coverage_accepts_all_exact_takes(tmp_path):
    takes = [{"slug": f"take-{i}"} for i in range(12)]
    report = {"complete": True, "valid": True, "rows": list(reversed(takes))}
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report))
    assert R.require_report(path, "valid", takes) == report


def test_committed_preflight_and_dirty_dependency_before_assets(tmp_path, monkeypatch):
    plan, inputs, dependency = (tmp_path / n for n in ("plan.md", "inputs.json", "parser.py"))
    plan.write_text("**Declared: synthetic fixture**")
    dependency.write_text("frozen parser")
    model, average, catalog = (tmp_path / n for n in ("fake.pt", "fake.npy", "catalog.json"))
    model.write_bytes(b"synthetic model bytes; never loaded")
    average.write_bytes(b"synthetic average bytes; never loaded")
    catalog.write_text("{}")
    manifest = {"model": {"path": str(model), "sha256": hashlib.sha256(model.read_bytes()).hexdigest()},
                "average": {"path": str(average), "sha256": hashlib.sha256(average.read_bytes()).hexdigest()},
                "catalog": str(catalog), "source_root": str(tmp_path / "P2-downloads"), "takes": []}
    inputs.write_text(json.dumps(manifest))
    committed = {p.name: p.read_bytes() for p in (plan, inputs, dependency)}
    monkeypatch.setattr(R, "ROOT", tmp_path)
    monkeypatch.setattr(R, "PLAN", plan)
    monkeypatch.setattr(R, "INPUTS", inputs)
    monkeypatch.setattr(R, "PINNED", tuple(committed))
    monkeypatch.setattr(R.P, "select_p2_crops", lambda *a: [])

    def git(args, **kwargs):
        return "synthetic-head\n" if args[1] == "rev-parse" else committed[args[-1].split(":")[1]]

    monkeypatch.setattr(R.subprocess, "check_output", git)
    actual, takes, provenance = R.frozen_inputs()
    assert actual == manifest and takes == [] and provenance["git_revision"] == "synthetic-head"
    dependency.write_text("dirty parser")
    monkeypatch.setattr(R, "sha", lambda _: pytest.fail("dirty source must refuse before assets"))
    with pytest.raises(ValueError, match="uncommitted frozen dependency: parser.py"):
        R.frozen_inputs()


def test_repeat_canary_accepts_phase_change_but_rejects_level_drift():
    rng = np.random.default_rng(24)
    first = rng.normal(size=R.P.SCORE) * 0.1
    assert R.repeat_canary(first, np.roll(first, 2))["passed"]
    result = R.repeat_canary(first, first * 2)
    assert not result["passed"] and result["rms_drift_db"] == pytest.approx(6.020599913)
    dc = R.repeat_canary(first, first + .15)
    assert abs(dc["rms_drift_db"]) > 1 and not dc["passed"]
    with pytest.raises(ValueError, match="invalid repeatability"):
        R.repeat_canary(first, np.zeros_like(first))


def test_repeat_canary_band_change_inactive_mask_and_inside_tolerance():
    t = np.arange(R.P.SCORE) / R.P.SR
    base = .1 * np.sin(2*np.pi*120*t) + .02 * np.sin(2*np.pi*1800*t)
    assert R.repeat_canary(base, base * 10**(.5/20))["passed"]
    assert not R.repeat_canary(base, base * 10**(1.01/20))["passed"]
    changed = .1 * np.sin(2*np.pi*120*t) + .03 * np.sin(2*np.pi*1800*t)
    result = R.repeat_canary(base, changed)
    assert abs(result["rms_drift_db"]) < 1 and not result["passed"]
    assert result["active_band_indices"] == [0, 4]
    added = base + .04 * np.sin(2*np.pi*3500*t)
    result = R.repeat_canary(base, added)
    assert result["passed"] and 5 not in result["active_band_indices"]
    assert len(result["first_band_power"]) == len(result["band_drift_db"]) == 6
    assert result["repeat_band_power"][5] > result["first_band_power"][5]


@pytest.mark.parametrize("source_stage", ["native", "prepare"])
@pytest.mark.parametrize("fail", [None, "host", "canary", "identity"])
def test_render_slices_level_and_closes_host_on_error(tmp_path, monkeypatch, source_stage, fail):
    run, output = tmp_path / "run", tmp_path / "render"
    source = run / source_stage
    source.mkdir(parents=True)
    output.mkdir()
    takes = [{"slug": f"take-{i}"} for i in range(12)]
    R.write_new(source / "result.json", {"complete": True, "valid": True, "rows": takes})
    monkeypatch.setattr(R.P, "SR", 10)
    monkeypatch.setattr(R.P, "SCORE", 60)
    di = np.arange(80, dtype=np.float64) / 1000 + 0.01
    inputs = [di + i / 100 for i in range(12)]
    for take, x in zip(takes, inputs):
        np.savez_compressed(source / f"{take['slug']}.npz", render_di=x)
    calls, closed, canaries, loaded = [], [], [], []
    identity = {"plugin_version": "synthetic", "band_noise_db": .23}
    real_load = np.load

    def load(path, **kwargs):
        loaded.append(path)
        assert kwargs == {"allow_pickle": False}
        return real_load(path, **kwargs)

    monkeypatch.setattr(np, "load", load)

    class FakeRenderer:
        def __init__(self, *args, **kwargs):
            assert args == ("morgan",)
            assert kwargs["process_policy"] == "reuse"
            assert kwargs["workdir"] == output / "au-host"

        def render(self, x, settings):
            assert settings == {} and x.dtype == np.float32
            assert self._state_command(settings) == {"selectAmp": 1, "edits": ["fixed"]}
            calls.append(x.copy())
            if fail == "host":
                raise RuntimeError("synthetic host failure")
            delayed = np.pad(x * 2, (52, 0))[:len(x)]
            return SimpleNamespace(audio=delayed, metadata=self.metadata())

        def close(self):
            closed.append(True)

        def metadata(self):
            value = dict(identity)
            if fail == "identity" and len(calls) == 3:
                value["plugin_version"] = "changed"
            return SimpleNamespace(as_dict=lambda: value)

    def preset_edits(path, pack, renderer, amp, original_gain):
        assert path == R.ROOT / "fixed.xml" and pack == "pack"
        assert isinstance(renderer, FakeRenderer) and amp == "pr12"
        assert original_gain is True
        return 1, ["fixed"]

    def load_pack(name):
        assert name == "morgan"
        return "pack"

    def canary(first, repeat):
        canaries.append((first.copy(), repeat.copy()))
        return {"passed": fail != "canary"}

    monkeypatch.setitem(sys.modules, "render_preset_panel", SimpleNamespace(
        preset_edits=preset_edits))
    monkeypatch.setitem(sys.modules, "match.renderer_au", SimpleNamespace(AudioUnitRenderer=FakeRenderer))
    monkeypatch.setitem(sys.modules, "packs.loader", SimpleNamespace(load_pack=load_pack))
    monkeypatch.setattr(R, "repeat_canary", canary)
    # Omit the keyword for native to preserve coverage of the existing caller.
    kwargs = {} if source_stage == "native" else {"source_stage": "prepare"}
    manifest = {"preset": "fixed.xml", "attribution": "credit"}
    if fail:
        error = RuntimeError if fail == "host" else ValueError
        message = "synthetic host failure" if fail == "host" else "repeatability control failed"
        with pytest.raises(error, match=message):
            R.render(output, run, manifest, takes, **kwargs)
        assert not (output / "result.json").exists()
        assert not (output / "take-0.npz").exists()
    else:
        R.render(output, run, manifest, takes, **kwargs)
        report = json.loads((output / "result.json").read_text())
        assert report["complete"] is True and report["attribution"] == "credit"
        assert [row["slug"] for row in report["rows"]] == [take["slug"] for take in takes]
        for take, x, row in zip(takes, inputs, report["rows"]):
            expected = np.pad(x.astype(np.float32)*2, (52, 0))[:132]
            with real_load(output / f"{take['slug']}.npz") as saved:
                np.testing.assert_array_equal(saved["net_input"], expected[20:80])
                np.testing.assert_array_equal(saved["baseline"], expected[72:132])
            assert row["renderer_metadata"] == identity
            assert row["render_peak"] == float(np.max(np.abs(expected)))
            assert row["render_hash"] == hashlib.sha256(expected.astype(np.float64).tobytes()).hexdigest()
        assert len(calls) == 14  # warm-up, twelve renders, one immediate canary
    assert closed == [True]
    count = 12 if fail is None else 1
    assert loaded == [source / f"{take['slug']}.npz" for take in takes[:count]]
    expected_calls = [inputs[0]] if fail == "host" else [inputs[0]] * 3
    if fail is None:
        expected_calls += inputs[1:]
    assert len(calls) == len(expected_calls)
    for actual, x in zip(calls, expected_calls):
        np.testing.assert_array_equal(actual, np.pad(x, (0, 52)).astype(np.float32))
    if fail == "host":
        assert canaries == [] and not (output / "repeatability.json").exists()
    else:
        expected = np.pad(di.astype(np.float32)*2, (52, 0))[:132].astype(np.float64)
        assert len(canaries) == 1
        for actual in canaries[0]:
            np.testing.assert_array_equal(actual, expected[72:132])
        with real_load(output / "repeatability-audio.npz") as saved:
            np.testing.assert_array_equal(saved["first"], expected)
            np.testing.assert_array_equal(saved["repeat"], expected)
        report = json.loads((output / "repeatability.json").read_text())
        assert report["passed"] is (fail != "canary")
        assert report["same_renderer_identity"] is (fail != "identity")
        assert report["first_renderer_metadata"] == identity
        repeat_identity = dict(identity, plugin_version="changed") if fail == "identity" else identity
        assert report["repeat_renderer_metadata"] == repeat_identity
    assert not (run / ("native" if source_stage == "prepare" else "prepare")).exists()


@pytest.mark.parametrize("stage", ["", "infer", "Prepare", "../native", "native/result.json", None, []])
def test_render_bad_source_stage_refuses_before_io(monkeypatch, stage):
    class NoPaths:
        def __truediv__(self, other):
            pytest.fail("path access before stage validation")

    monkeypatch.setattr(R, "require_report", lambda *a: pytest.fail("report access before validation"))
    monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("array access before validation"))
    monkeypatch.setitem(sys.modules, "render_preset_panel", None)
    monkeypatch.setitem(sys.modules, "match.renderer_au", None)
    monkeypatch.setitem(sys.modules, "packs.loader", None)
    with pytest.raises(ValueError, match="source_stage must be native or prepare"):
        R.render(NoPaths(), NoPaths(), {}, [], source_stage=stage)


def test_render_source_stage_is_keyword_only():
    with pytest.raises(TypeError):
        R.render(None, None, {}, [], "prepare")


@pytest.mark.parametrize("fault", ["missing-report", "duplicate", "missing", "wrong", "incomplete", "invalid"])
def test_prepare_requires_own_valid_coverage_before_renderer(tmp_path, monkeypatch, fault):
    takes = [{"slug": f"take-{i}"} for i in range(12)]
    report = {"complete": True, "valid": True, "rows": [dict(take) for take in takes]}
    (tmp_path / "native").mkdir()
    # A valid native report cannot substitute for prepare coverage.
    R.write_new(tmp_path / "native/result.json", report)
    (tmp_path / "prepare").mkdir()
    if fault == "duplicate":
        report["rows"][-1] = report["rows"][0]
    elif fault == "missing":
        report["rows"].pop()
    elif fault == "wrong":
        report["rows"][-1]["slug"] = "undeclared"
    elif fault == "incomplete":
        report["complete"] = False
    elif fault == "invalid":
        report["valid"] = False
    if fault != "missing-report":
        R.write_new(tmp_path / "prepare/result.json", report)
    monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("array access before coverage"))
    monkeypatch.setitem(sys.modules, "render_preset_panel", None)
    monkeypatch.setitem(sys.modules, "match.renderer_au", None)
    monkeypatch.setitem(sys.modules, "packs.loader", None)
    error = FileNotFoundError if fault == "missing-report" else ValueError
    message = "prepare/result.json" if fault == "missing-report" else "declared coverage"
    with pytest.raises(error, match=message):
        R.render(tmp_path / "unused", tmp_path, {}, takes, source_stage="prepare")
    assert not (tmp_path / "unused").exists()


def test_bad_prerequisite_never_imports_or_calls_renderer_or_model(tmp_path, monkeypatch):
    (tmp_path / "native").mkdir()
    (tmp_path / "render").mkdir()
    takes = [{"slug": f"take-{i}"} for i in range(12)]
    report = {"complete": False, "valid": False, "rows": takes}
    (tmp_path / "native/result.json").write_text(json.dumps(report))
    (tmp_path / "render/result.json").write_text(json.dumps(report))
    monkeypatch.setitem(sys.modules, "match.renderer_au", None)
    monkeypatch.setitem(sys.modules, "torch", None)
    with pytest.raises(ValueError, match="declared coverage"):
        R.render(tmp_path / "unused", tmp_path, {}, takes)
    with pytest.raises(ValueError, match="declared coverage"):
        R.infer(tmp_path / "unused", tmp_path, {}, takes)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), 0.0])
def test_native_rejected_loss_is_json_safe_and_other_takes_continue(tmp_path, monkeypatch, bad):
    run = tmp_path / "run"
    output = run / "native"
    output.mkdir(parents=True)
    average = tmp_path / "synthetic-average.npy"
    np.save(average, np.zeros(4))
    takes = [{"slug": f"take-{i}", "content": "chords" if i < 6 else "scales", "take": str(i),
              "di": "synthetic", "micamp": "synthetic", "start_frame": 123, "lag_samples": 37}
             for i in range(12)]
    monkeypatch.setattr(R.P, "CALIBRATION", 40)
    monkeypatch.setattr(R.P, "SCORE", 60)
    monkeypatch.setattr(R.P, "SR", 10)
    monkeypatch.setattr(R.P, "GUARD", 2)
    x = np.arange(100, dtype=np.float64) / 1000 + .01
    monkeypatch.setattr(R.P, "read_bounded", lambda *a: x.copy())
    monkeypatch.setattr(R.P, "calibrate", lambda *a: {"lag": 37})
    monkeypatch.setattr(R, "asdict", lambda x: dict(x))
    monkeypatch.setattr(R.P, "align_pair", lambda *a: (x.copy(), x.copy()*2))
    monkeypatch.setattr(R.P, "pair_qc", lambda *a: {"valid": True})
    monkeypatch.setattr(R.P, "canonical_target", lambda x, avg: x.copy())
    fitted = SimpleNamespace(taps=np.ones(256), intercept=.123)
    monkeypatch.setattr(R.P, "fit_calibration_fir", lambda wet, di: fitted)

    def predict(wet, model, **kwargs):
        assert model is fitted and len(wet) == 64
        assert kwargs == {"start_frame": 2, "frames": 60}
        return wet[2:-2].copy()

    monkeypatch.setattr(R.P, "predict_fir", predict)
    calls = []

    def scores(*args):
        index = len(calls)
        calls.append(index)
        primary = 0.0 if index % 4 == 3 else (bad if index == 0 else 1.0)
        return {"primary": primary, "canonical_waveform_l1": 0.1, "raw_lowband": 1.0}

    monkeypatch.setattr(R.P, "score_prediction", scores)
    R.native(output, {"average": {"path": str(average)}, "attribution": "credit"}, takes)
    report = json.loads((output / "result.json").read_text())
    assert report["complete"] and not report["valid"] and len(report["rows"]) == 12
    assert not report["rows"][0]["qc_valid"] and report["rows"][1]["qc_valid"]
    assert not (output / "take-0.npz").exists()
    if not np.isfinite(bad):
        assert report["rows"][0]["native_input_scores"]["primary"] is None
        assert report["rows"][0]["nonfinite_diagnostic_fields"]
    with np.load(output / "take-1.npz") as saved:
        assert saved["fir_intercept"] == .123
        np.testing.assert_array_equal(saved["fir_taps"], fitted.taps)
    assert len(calls) == 48
    with pytest.raises(ValueError, match="declared coverage"):
        R.render(run / "render", run, {}, takes)


@pytest.mark.parametrize("stage", ["native", "infer"])
def test_runner_invalid_windows_refused_before_assets_or_model(tmp_path, monkeypatch, stage):
    monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("asset access before validation"))
    monkeypatch.setattr(R, "require_report", lambda *a: pytest.fail("report access before validation"))
    monkeypatch.setitem(sys.modules, "torch", None)
    args = (tmp_path, {}, []) if stage == "native" else (tmp_path, tmp_path, {}, [])
    with pytest.raises(ValueError, match="window"):
        getattr(R, stage)(*args, windows={})


@pytest.mark.parametrize("explicit", [False, True])
def test_native_and_infer_all_arms_propagate_windows_without_torch(tmp_path, monkeypatch, explicit):
    run = tmp_path / "run"
    native, render, infer = (run / name for name in ("native", "render", "infer"))
    for directory in (native, render, infer):
        directory.mkdir(parents=True)
    average = tmp_path / "synthetic-average.npy"
    np.save(average, np.zeros(4))
    manifest = {"average": {"path": str(average)}, "model": {"path": "synthetic-model"},
                "attribution": "synthetic credit"}
    takes = [{"slug": f"take-{i}", "content": "chords" if i < 6 else "scales",
              "take": str(i), "di": "synthetic", "micamp": "synthetic",
              "start_frame": 123, "lag_samples": 0} for i in range(12)]
    monkeypatch.setattr(R.P, "CALIBRATION", 40)
    monkeypatch.setattr(R.P, "SCORE", 60)
    monkeypatch.setattr(R.P, "SR", 10)
    monkeypatch.setattr(R.P, "GUARD", 2)
    x = np.arange(100, dtype=float) / 1000 + .01
    monkeypatch.setattr(R.P, "read_bounded", lambda *a: x.copy())
    monkeypatch.setattr(R.P, "calibrate", lambda *a: {"lag": 0})
    monkeypatch.setattr(R, "asdict", dict)
    monkeypatch.setattr(R.P, "align_pair", lambda *a: (x.copy(), x * 2 + .02))
    monkeypatch.setattr(R.P, "pair_qc", lambda *a: {"valid": True})
    monkeypatch.setattr(R.P, "canonical_target", lambda a, avg: a**2)
    fir = SimpleNamespace(taps=np.ones(256), intercept=0.0)
    monkeypatch.setattr(R.P, "fit_calibration_fir", lambda *a: fir)
    monkeypatch.setattr(R.P, "predict_fir", lambda wet, model, **k: wet[2:-2] * 3)
    monkeypatch.setattr(R.P, "bandpass", lambda a: a)
    windows = {n: np.arange(n, dtype=np.float32) / n for n in R.P.FFTS} if explicit else None
    expected_kwargs = {} if windows is None else {"windows": windows}
    score_calls, fft_calls = [], []
    real_score = R.P.score_prediction

    def score(a, target, raw, **kwargs):
        assert kwargs.keys() == expected_kwargs.keys()
        if explicit:
            assert kwargs["windows"] is windows
        score_calls.append(a.copy())
        return real_score(a, target, raw, **kwargs)

    def fft(a, b, **kwargs):
        assert kwargs.keys() == expected_kwargs.keys()
        if explicit:
            assert kwargs["windows"] is windows
        fft_calls.append((a, b))
        return 0.0 if np.array_equal(a, b) else 1.0

    monkeypatch.setattr(R.P, "score_prediction", score)
    monkeypatch.setattr(R.P, "mrstft_numpy", fft)
    # Exercise explicit None as well as an actual mapping; default downstream
    # calls must still work with the existing no-keyword scorers.
    R.native(native, manifest, takes, windows=windows)
    report = json.loads((native / "result.json").read_text())
    assert report["complete"] and report["valid"]
    d, wet = x[40:], (x * 2 + .02)[40:]
    for i in range(12):
        for actual, expected in zip(score_calls[4*i:4*i+4], (wet, wet**2, wet*3, d**2)):
            np.testing.assert_array_equal(actual, expected)
    assert len(score_calls) == 48 and len(fft_calls) == 96

    morgan_input, baseline = d * 4 + .03, d * 5 + .04
    for take in takes:
        np.savez_compressed(render / f"{take['slug']}.npz", net_input=morgan_input, baseline=baseline)
    R.write_new(render / "result.json", {"complete": True, "rows": takes})
    loaded, rebuilt = [], []
    net = SimpleNamespace(cpu=lambda: net, load_state_dict=loaded.append, eval=lambda: None)

    def load(path, **kwargs):
        assert path == "synthetic-model"
        assert kwargs == {"map_location": "cpu", "weights_only": True}
        return "synthetic-state"

    def rebuild(model, a, **kwargs):
        assert model is net and a.dtype == np.float32 and kwargs == {"device": "cpu"}
        rebuilt.append(a.copy())
        return a.astype(np.float64) + .07

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(
        set_num_threads=lambda n: None, load=load, device=lambda d: d, __version__="synthetic"))
    fake_direc = SimpleNamespace(build_model=lambda: net, rebuild=rebuild)
    monkeypatch.setitem(sys.modules, "learn.direc", fake_direc)
    monkeypatch.setattr(sys.modules["learn"], "direc", fake_direc, raising=False)
    R.infer(infer, run, manifest, takes, windows=windows)
    assert loaded == ["synthetic-state"] and len(rebuilt) == 24
    for i in range(12):
        expected = (rebuilt[2*i].astype(float) + .07,
                    rebuilt[2*i+1].astype(float) + .07, baseline)
        for actual, wanted in zip(score_calls[48+3*i:48+3*i+3], expected):
            np.testing.assert_array_equal(actual, wanted)
    assert len(score_calls) == 84 and len(fft_calls) == 168
    final = json.loads((infer / "result.json").read_text())
    assert final["complete"] and len(final["rows"]) == 12
