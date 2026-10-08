"""Synthetic only: no original NPZ, checkpoint or study computation."""
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
import pytest

from learn import di_phase_control as Q


def panel():
    return [{"slug": "synthetic-" + str(i), "take": str(i),
             "content": "chords" if i < 6 else "scales"} for i in range(12)]


def score(value):
    return dict.fromkeys(Q.T.METRICS, value)


def rows():
    return [{**t, "valid": True, "qc_valid": True, "oracle": 0.0,
             "wet": 2.0, "flatref": 1.0, "net": .8,
             "input_scores": score(2.0), "flatref_scores": score(1.0),
             "network_scores": score(.8)} for t in panel()]


@pytest.fixture
def small(monkeypatch):
    monkeypatch.setattr(Q, "N", 1024)


def synthetic(n):
    t = np.arange(n)
    return (.31 + .2 * np.cos(2 * np.pi * 7 * t / n)
            + .07 * np.sin(2 * np.pi * 97 * t / n)).astype("<f4")


def loaded():
    return {t["slug"]: {"net_input": synthetic(Q.N).astype(np.float64),
                        "wet": np.roll(synthetic(Q.N), -52).astype(np.float64),
                        "flatref": synthetic(Q.N).astype(np.float64) * 1.7}
            for t in panel()}


def test_full_size_fixed_coefficients_and_complex_sinusoid_oracle():
    assert Q.A == -.9 and Q.N == 288000 and Q.CONFIG["renderer_latency_samples"] == 52
    h = Q.coefficients()
    assert h.dtype == np.complex128 and h.shape == (144001,)
    assert h[0] == 1 + 0j and h[-1] == -1 + 0j
    assert np.max(np.abs(np.abs(h) - 1)) <= 1e-12
    n = np.arange(Q.N)
    # Independent analytic response at selected discrete complex modes.
    for k in (1, 307, 23971, Q.N // 2):
        omega = 2 * np.pi * k / Q.N
        response = complex(-.9 + np.cos(omega), -np.sin(omega)) / complex(1 - .9 * np.cos(omega), .9 * np.sin(omega))
        analytic = np.real(response * np.exp(1j * omega * n))
        actual = Q.transform(np.cos(omega * n), h)
        np.testing.assert_allclose(actual, analytic, atol=2e-10, rtol=0)


def test_independent_periodic_impulse_and_delay(small):
    n, a = Q.N, -.9
    impulse = np.zeros(n)
    impulse[0] = 1
    # Periodized causal first-order impulse, derived without FFT division.
    expected = np.zeros(n)
    expected[0] = a
    for lag in range(1, n + 1):
        expected[lag % n] += (1 - a*a) * (-a)**(lag - 1)
    got = Q.transform(impulse, Q.coefficients())
    np.testing.assert_allclose(got, expected, atol=2e-15, rtol=0)
    np.testing.assert_allclose(Q.transform(np.roll(impulse, 52), Q.coefficients()), np.roll(got, 52), atol=2e-15, rtol=0)
    assert not np.allclose(got, impulse)


def test_identity_exact_float32_bytes_and_source_untouched(small):
    x = synthetic(Q.N)
    x[0], x[1] = -0.0, np.nextafter(np.float32(0), np.float32(1))
    original = x.tobytes()
    result = Q.transform(x.astype(np.float64), np.ones(Q.N // 2 + 1, dtype=complex)).astype("<f4")
    assert result.tobytes() == original and x.tobytes() == original


def test_reversibility_raw_amplitude_and_coherent_simple_arms(small):
    saved = next(iter(loaded().values()))
    saved["net_input"] *= 13.7  # Amplitude must reach phase transform before D normalization.
    before = {k: x.tobytes() for k, x in saved.items()}
    values = Q.construction(saved, Q.coefficients())
    report = Q.control_metrics(values, Q.coefficients())
    assert report["passed"] is True
    x = saved["net_input"].astype("<f4").astype(np.float64)
    assert values["model_converted_input"].tobytes() == x.tobytes()
    assert np.std(values["forward_float64"]) > 1
    for key in ("wet", "flatref"):
        expected = np.fft.irfft(np.fft.rfft(saved[key]) * Q.coefficients(), n=Q.N)
        assert values["phase_" + key].dtype == np.float64
        np.testing.assert_array_equal(values["phase_" + key], expected)
    assert all(saved[k].tobytes() == v for k, v in before.items())
    assert values["phase_input"].dtype == np.dtype("<f4")
    assert all(np.isfinite(v["denominator"]) and v["denominator"] > 0 for v in report["errors"].values())


@pytest.mark.parametrize("broken_last", [False, True])
def test_original52_overlap_checked_by_unchanged_loader(tmp_path, monkeypatch, small, broken_last):
    takes = panel()
    old = {t["slug"]: {"wet": synthetic(Q.N).astype(np.float64)} for t in takes}
    identities = {t["slug"]: {} for t in takes}
    source = tmp_path / "synthetic-source"
    (source / "render").mkdir(parents=True)
    hashes = {}
    for t in takes:
        x = np.concatenate((np.zeros(52), old[t["slug"]]["wet"][:-52]))
        if broken_last and t == takes[-1]:
            x[-1] += .00001
        path = source / "render" / (t["slug"] + ".npz")
        np.savez(path, net_input=x)
        hashes[str(path.relative_to(tmp_path))] = Q.T.digest(path.read_bytes())
    monkeypatch.setattr(Q.U, "ROOT", tmp_path)
    monkeypatch.setattr(Q.T, "SOURCE", source)
    monkeypatch.setattr(Q.P, "SCORE", Q.N)
    monkeypatch.setattr(Q.U, "check_artifacts", lambda *a: None)
    monkeypatch.setattr(Q.T, "load_inputs", lambda *a: (old, identities))
    old_inputs = {"artifacts": hashes, "waveforms": deepcopy(identities)}
    if broken_last:
        with pytest.raises(ValueError, match="original52"):
            Q.U.load_inputs(takes, hashes, {}, {}, old_inputs, time.monotonic())
    else:
        result, _ = Q.U.load_inputs(takes, hashes, {}, {}, old_inputs, time.monotonic())
        assert result[takes[-1]["slug"]]["net_input"][52:].tobytes() == old[takes[-1]["slug"]]["wet"][:-52].tobytes()


def test_optional_torch_synthetic_raw_normalization_and_latency():
    torch = pytest.importorskip("torch")
    # Identity toy, no actual checkpoint or trained model, original U.infer/D.rebuild.
    class Recorder(torch.nn.Module):
        def forward(self, x):
            self.seen = x.detach().cpu().numpy().copy()
            return x
    net = Recorder().cpu().eval()
    raw = np.zeros(288000, dtype="<f4")
    raw[52] = .71
    raw[1052] = -.19
    expected = raw / (raw.std() + 1e-9) * .1
    prediction = Q.U.infer(net, raw, time.monotonic())
    np.testing.assert_array_equal(net.seen[0, 0], expected)
    assert prediction.dtype == np.dtype("<f4")
    assert np.argmax(prediction) == 52 and np.argmin(prediction) == 1052
    np.testing.assert_allclose(prediction, raw, atol=1e-7, rtol=1e-6)


@pytest.mark.parametrize("defect", ["wrong_inverse", "nonunit", "quantization", "zero_denominator", "nonfinite"])
def test_positive_controls_can_fail(small, defect):
    h = Q.coefficients()
    values = Q.construction(next(iter(loaded().values())), h)
    if defect == "wrong_inverse":
        values["inverse_float64"] = values["forward_float64"].copy()
    elif defect == "nonunit":
        h[17] *= 1.001
    elif defect == "quantization":
        values["inverse_quantized_float64"] *= 1.0001
    elif defect == "zero_denominator":
        values["model_converted_input"][:] = 0
    else:
        values["forward_float64"][5] = np.nan
    if defect in ("zero_denominator", "nonfinite"):
        with pytest.raises(ValueError):
            Q.control_metrics(values, h)
    else:
        assert Q.control_metrics(values, h)["passed"] is False


def test_time_domain_inverse_uses_no_fft_calls(monkeypatch, small):
    x = synthetic(Q.N).astype(np.float64)
    forward = Q.transform(x, Q.coefficients())
    def no_fft(*a, **k):
        pytest.fail("inverse called the forward FFT implementation")
    monkeypatch.setattr(np.fft, "rfft", no_fft)
    monkeypatch.setattr(np.fft, "irfft", no_fft)
    np.testing.assert_allclose(Q.inverse_periodic(forward), x, atol=2e-14, rtol=0)


def test_real_replay_last_take_timeout_retains_completed_cases(tmp_path, monkeypatch):
    original_rows = rows()
    source = {t["slug"]: {**{a: np.ones(8) for a in Q.T.ARMS},
                           "target": np.ones(8), "di": np.ones(8)} for t in panel()}
    calls = []
    def scorer(*a, **k):
        calls.append(1)
        if len(calls) == 34:
            raise TimeoutError("last take expired")
        return original_rows[(len(calls)-1)//3][list(Q.T.ARMS.values())[(len(calls)-1)%3]]
    monkeypatch.setattr(Q.P, "score_prediction", scorer)
    with pytest.raises(TimeoutError):
        Q.replay(tmp_path, panel(), source, {}, {"rows": original_rows,
                 "screen": Q.F.compare(original_rows, panel())}, time.monotonic())
    report = json.loads((tmp_path / "baseline-replay.json").read_text())
    assert not report["complete"] and not report["passed"]
    assert report["scalar_count"] == 99 and len(report["rows"]) == 12
    assert all(r["valid"] for r in report["rows"][:-1])
    assert report["rows"][-1]["error"]["type"] == "TimeoutError"
    assert len(list(tmp_path.glob("baseline-replay-attempt-*.json"))) == 12


@pytest.mark.parametrize("defect", [None, "save", "hash"])
def test_real_baseline_manifest_and_failure_attempts(tmp_path, monkeypatch, small, defect):
    original_rows = rows()
    source = {t["slug"]: {"net_input": synthetic(Q.N), "net": synthetic(Q.N),
                           "target": synthetic(Q.N), "di": synthetic(Q.N)} for t in panel()}
    monkeypatch.setattr(Q.U, "infer", lambda *a: synthetic(Q.N))
    monkeypatch.setattr(Q.P, "SCORE", Q.N)
    monkeypatch.setattr(Q.P, "score_prediction", lambda *a, **k: score(.8))
    if defect == "save":
        monkeypatch.setattr(np, "savez_compressed", lambda *a, **k: (_ for _ in ()).throw(OSError("save failed")))
    elif defect == "hash":
        monkeypatch.setattr(Q.R, "sha", lambda *a: (_ for _ in ()).throw(OSError("hash failed")))
    args = (tmp_path, panel(), source, {}, original_rows, None, time.monotonic(), {"rows": original_rows})
    if defect:
        with pytest.raises(ValueError, match="complete12"):
            Q.baseline_inference(*args)
    else:
        Q.baseline_inference(*args)
    report = json.loads((tmp_path / "baseline-inference-replay.json").read_text())
    assert len(report["rows"]) == 12
    assert all(r["attempted_file"] == r["slug"] + ".offset-+0.npz" and r["returned"] for r in report["rows"])
    if defect:
        assert not report["passed"] and all(r["error"]["type"] == "OSError" for r in report["rows"])
    else:
        assert report["passed"]
        for r in report["rows"]:
            with np.load(tmp_path / r["attempted_file"], allow_pickle=False) as saved:
                assert set(saved.files) == set(r["archive"]["members"]) == {"offset", "raw_prediction", "corrected_prediction"}
                for name in saved.files:
                    v = saved[name]
                    assert r["archive"]["members"][name] == {"dtype": str(v.dtype), "shape": list(v.shape), "sha256": Q.T.digest(v.tobytes())}


def test_last_take_control_failure_persisted_blocks_return(tmp_path, monkeypatch, small):
    original = Q.construction
    calls = []
    def fail_last(saved, h):
        calls.append(True)
        values = original(saved, h)
        if len(calls) == 12:
            values["inverse_float64"] = np.roll(values["inverse_float64"], 1)
        return values
    monkeypatch.setattr(Q, "construction", fail_last)
    with pytest.raises(ValueError, match="all12"):
        Q.controls(tmp_path, panel(), loaded(), time.monotonic())
    report = json.loads((tmp_path / "construction-controls.json").read_text())
    assert report["complete"] is True and report["passed"] is False
    assert len(report["rows"]) == 12 and report["rows"][-1]["passed"] is False
    assert all(r["passed"] is True for r in report["rows"][:-1])
    assert report["rows"][-1]["errors"]["inverse"]["relative_l2"] > 1e-12
    assert len(list(tmp_path.glob("*.controls.npz"))) == 12


def test_controls_save_before_validity_error(tmp_path, monkeypatch, small):
    def broken(*args):
        raise ValueError("bad inverse")
    monkeypatch.setattr(Q, "control_metrics", broken)
    with pytest.raises(ValueError):
        Q.controls(tmp_path, panel(), loaded(), time.monotonic())
    report = json.loads((tmp_path / "construction-controls.json").read_text())
    assert len(report["rows"]) == 12
    assert all("archive" in r and "error" in r for r in report["rows"])


@pytest.mark.parametrize("defect", ["construct", "save", "hash"])
def test_coefficient_failures_keep_attempt_and_failed_barrier(tmp_path, monkeypatch, small, defect):
    def broken(*a, **k):
        raise OSError("synthetic coefficient " + defect + " failure")
    if defect == "construct":
        monkeypatch.setattr(Q, "coefficients", broken)
    elif defect == "save":
        monkeypatch.setattr(Q, "save_arrays", broken)
    else:
        monkeypatch.setattr(Q.R, "sha", broken)
    monkeypatch.setattr(Q, "construction", lambda *a: pytest.fail("take construction reached after coefficient failure"))
    with pytest.raises(OSError):
        Q.controls(tmp_path, panel(), loaded(), time.monotonic())
    report = json.loads((tmp_path / "construction-controls.json").read_text())
    attempt = report["coefficients_attempt"]
    assert not report["complete"] and not report["passed"] and report["rows"] == []
    assert attempt["attempted_file"] == "coefficients.npz" and attempt["error"]["type"] == "OSError"
    assert report["coefficients_archive"] is None
    assert attempt["constructed"] is (defect != "construct")
    if defect == "hash":
        with np.load(tmp_path / "coefficients.npz", allow_pickle=False) as saved:
            h = saved["h"]
            assert attempt["members"]["h"] == {"dtype": str(h.dtype), "shape": list(h.shape), "sha256": Q.T.digest(h.tobytes())}
    else:
        assert not (tmp_path / "coefficients.npz").exists()


def test_last_control_timeout_keeps_error_and_saved_array(tmp_path, monkeypatch, small):
    real = Q.construction
    count = [0]
    expired = [False]
    def timed(saved, h):
        values = real(saved, h)
        count[0] += 1
        expired[0] = count[0] == 12
        return values
    def budget(*a):
        if expired[0]:
            raise TimeoutError("last control timed out")
    monkeypatch.setattr(Q, "construction", timed)
    monkeypatch.setattr(Q.R, "check_time", budget)
    with pytest.raises(TimeoutError):
        Q.controls(tmp_path, panel(), loaded(), time.monotonic())
    report = json.loads((tmp_path / "construction-controls.json").read_text())
    assert not report["complete"] and not report["passed"] and len(report["rows"]) == 12
    assert report["rows"][-1]["error"]["type"] == "TimeoutError"
    assert "archive" in report["rows"][-1] and len(list(tmp_path.glob("*.controls.npz"))) == 12


def fake_run_environment(monkeypatch, tmp_path):
    events = []
    takes = panel()
    original_rows = rows()
    context = ({}, {"takes": takes, "model": {}, "attribution": "synthetic"}, {}, "revision", {}, {}, {}, {}, {},
               {"artifacts": {}, "waveforms": {}})
    monkeypatch.setattr(Q.U, "stability", lambda *a: events.append("stability"))
    monkeypatch.setattr(Q.V, "load_windows", lambda *a: {})
    monkeypatch.setattr(Q.U, "load_inputs", lambda *a: ({}, {}))
    def replay(*args):
        Q.R.write_new(tmp_path / "baseline-replay.json", {"passed": True})
        events.append("saved108")
        return original_rows
    def model(*args):
        assert json.loads((tmp_path / "baseline-replay.json").read_text())["passed"] is True
        events.append("model")
        return object()
    def baseline(*args):
        assert events[-1] == "model"
        for i in range(12):
            events.append("baseline" + str(i))
        Q.R.write_new(tmp_path / "baseline-inference-replay.json", {"passed": True})
        events.append("saved36bytes")
        return original_rows, {}
    def controls(*args):
        assert events[-2:] == ["saved36bytes", "stability"]
        assert json.loads((tmp_path / "baseline-inference-replay.json").read_text())["passed"] is True
        events.append("controls12")
        Q.R.write_new(tmp_path / "construction-controls.json", {"passed": True})
        return {}
    def predictions(*args):
        assert "controls12" in events
        assert json.loads((tmp_path / "construction-controls.json").read_text())["passed"] is True
        events.append("phase12")
        return {}
    def cases(*args):
        assert "phase12" in events
        args[-2].extend(original_rows)
    monkeypatch.setattr(Q, "replay", replay)
    monkeypatch.setattr(Q.U, "load_model", model)
    monkeypatch.setattr(Q, "baseline_inference", baseline)
    monkeypatch.setattr(Q, "controls", controls)
    monkeypatch.setattr(Q, "phase_predictions", predictions)
    monkeypatch.setattr(Q, "score_cases", cases)
    return events, context


def test_run_barriers_saved_in_order(tmp_path, monkeypatch):
    events, context = fake_run_environment(monkeypatch, tmp_path)
    state = {"rows": [], "prediction_evidence": []}
    Q.run(tmp_path, context, time.monotonic(), state)
    assert events.index("saved108") < events.index("model") < events.index("baseline11")
    assert events.index("baseline11") < events.index("saved36bytes") < events.index("controls12") < events.index("phase12")
    assert state["screen"]["passed"] is True


def test_budget_expiry_during_final_aggregation(tmp_path, monkeypatch):
    _, context = fake_run_environment(monkeypatch, tmp_path)
    now = [0.0]
    monkeypatch.setattr(Q.time, "monotonic", lambda: now[0])
    old_compare = Q.compare
    def late(*args):
        result = old_compare(*args)
        now[0] = 901.0
        return result
    monkeypatch.setattr(Q, "compare", late)
    with pytest.raises(TimeoutError):
        Q.run(tmp_path, context, 0.0, {"rows": [], "prediction_evidence": []})


def test_budget_expiry_during_final_save_preserves_provisional_result(tmp_path, monkeypatch):
    now = [0.0]
    monkeypatch.setattr(Q.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(Q, "guard", lambda *a: None)
    def valid_run(out, context, started, state):
        state.update(complete=True, rows=rows(), screen=Q.F.compare(rows(), panel()))
    monkeypatch.setattr(Q, "run", valid_run)
    original_write = Q.R.write_new
    def slow_save(path, value):
        original_write(path, value)
        if path.name == "result.json":
            now[0] = 901.0
    monkeypatch.setattr(Q.R, "write_new", slow_save)
    with pytest.raises(TimeoutError):
        Q.execute(tmp_path, 0.0)
    final = json.loads((tmp_path / "result.json").read_text())
    provisional = json.loads((tmp_path / "result-before-final-budget.json").read_text())
    assert final["screen"]["disposition"] == "INCONCLUSIVE" and final["elapsed_seconds"] > 900
    assert len(final["rows"]) == 12 and provisional["screen"]["passed"]
    assert json.loads((tmp_path / "failure.json").read_text())["type"] == "TimeoutError"


@pytest.mark.parametrize("barrier", ["replay", "baseline_inference", "controls"])
def test_failed_last_take_barrier_blocks_all_later_stages(tmp_path, monkeypatch, barrier):
    events, context = fake_run_environment(monkeypatch, tmp_path)
    def fail(*args):
        raise ValueError("last take failed")
    owner = Q
    monkeypatch.setattr(owner, barrier, fail)
    with pytest.raises(ValueError):
        Q.run(tmp_path, context, time.monotonic(), {"rows": [], "prediction_evidence": []})
    assert "phase12" not in events
    if barrier == "replay":
        assert "model" not in events
    if barrier != "controls":
        assert "controls12" not in events


def test_prediction_returns_all_saved_before_any_validation(tmp_path, monkeypatch, small):
    prepared = {t["slug"]: Q.construction(next(iter(loaded().values())), Q.coefficients()) for t in panel()}
    calls = []
    def infer(net, x, started):
        calls.append(x.copy())
        raw = synthetic(Q.N)
        if len(calls) == 1:
            raw[13] = np.nan
        return raw
    monkeypatch.setattr(Q.U, "infer", infer)
    evidence = []
    predicted = Q.phase_predictions(tmp_path, panel(), prepared, object(), time.monotonic(), evidence)
    assert len(calls) == len(predicted) == len(evidence) == 12
    with np.load(tmp_path / "synthetic-0.phase.npz", allow_pickle=False) as saved:
        assert set(saved.files) == {"raw_prediction", "phase_input", "phase_wet", "phase_flatref"}
        assert np.isnan(saved["raw_prediction"][13])
    assert all(e["archive"]["members"]["raw_prediction"]["dtype"] == "float32" for e in evidence)


def test_return_saved_before_after_call_timeout(tmp_path, monkeypatch, small):
    prepared = {t["slug"]: {k: synthetic(Q.N) for k in ("phase_input", "phase_wet", "phase_flatref")} for t in panel()}
    expired = [False]
    def infer(*a):
        expired[0] = True
        return np.full(Q.N, np.inf, dtype="<f4")
    def budget(*a):
        if expired[0]:
            raise TimeoutError("900 seconds")
    monkeypatch.setattr(Q.U, "infer", infer)
    monkeypatch.setattr(Q.R, "check_time", budget)
    evidence = []
    with pytest.raises(TimeoutError):
        Q.phase_predictions(tmp_path, panel(), prepared, None, time.monotonic(), evidence)
    assert evidence[0]["returned"] is True and "archive" in evidence[0]
    with np.load(tmp_path / "synthetic-0.phase.npz") as saved:
        assert np.isinf(saved["raw_prediction"]).all()


def test_inference_exception_keeps_transformed_arms_and_continues(tmp_path, monkeypatch, small):
    prepared = {t["slug"]: {k: synthetic(Q.N) for k in ("phase_input", "phase_wet", "phase_flatref")} for t in panel()}
    def fail(*args):
        raise RuntimeError("model failed")
    monkeypatch.setattr(Q.U, "infer", fail)
    evidence = []
    assert Q.phase_predictions(tmp_path, panel(), prepared, None, time.monotonic(), evidence) == {}
    assert len(evidence) == 12 and all("error" in e for e in evidence)
    with np.load(tmp_path / "synthetic-11.phase.npz") as saved:
        assert set(saved.files) == {"phase_input", "phase_wet", "phase_flatref"}


def test_saving_failure_stops_further_calls_preserves_return_metadata(tmp_path, monkeypatch, small):
    prepared = {t["slug"]: {k: synthetic(Q.N) for k in ("phase_input", "phase_wet", "phase_flatref")} for t in panel()}
    calls = []
    monkeypatch.setattr(Q.U, "infer", lambda *a: calls.append(1) or synthetic(Q.N))
    def failed_save(*a):
        raise OSError("disk full")
    monkeypatch.setattr(Q, "save_arrays", failed_save)
    evidence = []
    with pytest.raises(OSError):
        Q.phase_predictions(tmp_path, panel(), prepared, None, time.monotonic(), evidence)
    assert calls == [1] and evidence[0]["returned"] is True


def test_scoring_uses_fixed_targets_no_inverse_and_reports_degradation(tmp_path, monkeypatch, small):
    original_rows = rows()
    takes = panel()
    source = {t["slug"]: {"target": synthetic(Q.N), "di": synthetic(Q.N) * 3} for t in takes}
    prepared = {t["slug"]: {"phase_wet": synthetic(Q.N) * 5, "phase_flatref": synthetic(Q.N) * 7} for t in takes}
    predictions = {t["slug"]: synthetic(Q.N) * 11 for t in takes}
    monkeypatch.setattr(Q.U, "validate_prediction", lambda raw, same, error: require_same(raw, same))
    calls = []
    def scorer(wave, target, di, *, windows):
        i = len(calls) // 3
        slug = takes[i]["slug"]
        assert target is source[slug]["target"] and di is source[slug]["di"]
        arm = list(Q.T.ARMS)[len(calls) % 3]
        assert wave is (predictions[slug] if arm == "net" else prepared[slug]["phase_" + arm])
        calls.append(arm)
        return score({"wet": 3., "flatref": 2., "net": 1.5}[arm])
    monkeypatch.setattr(Q.P, "score_prediction", scorer)
    result = []
    Q.score_cases(tmp_path, takes, source, prepared, predictions, original_rows, {}, time.monotonic(), result,
                  [{**t, "returned": True} for t in takes])
    assert len(calls) == 36 and all(r["valid"] for r in result)
    assert result[-1]["changes_from_zero"]["wet"]["primary_absolute_change"] == 1
    assert result[-1]["changes_from_zero"]["flatref"]["primary_relative_change"] == 1


def require_same(raw, same):
    assert raw is same


@pytest.mark.parametrize("defect", ["missing", "duplicate", "nonfinite", "qc", "baseline", "group", "wins", "median"])
def test_frozen_gate_coverage_invalid_priority_and_fail(defect):
    r, takes = rows(), panel()
    baseline = Q.F.compare(rows(), takes)
    if defect == "missing":
        r.pop()
    elif defect == "duplicate":
        r[-1] = deepcopy(r[0])
    elif defect == "nonfinite":
        r[-1].update(net=float("nan"), valid=False)
    elif defect == "qc":
        r[-1]["qc_valid"] = False
    elif defect == "baseline":
        baseline["passed"] = False
    else:
        for i, row in enumerate(r):
            loss = (1.01 if i < 6 else .1) if defect == "group" else (1.01 if i < 4 else .1) if defect == "wins" else .95
            row.update(net=loss, network_scores=score(loss))
    screen = Q.compare(r, takes, baseline)
    assert screen["disposition"] == ("FAIL" if defect in ("group", "wins", "median") else "INCONCLUSIVE")


def test_gate_boundary_uses_original_allowance():
    r = rows()
    for row in r:
        row.update(net=.9, network_scores=score(.9))
    assert Q.compare(r, panel(), Q.F.compare(rows(), panel()))["passed"] is True


def test_no_aliases_hardlinks_or_overwriting(tmp_path, monkeypatch):
    p = tmp_path / "normal"
    p.write_text("metadata")
    assert Q.U.regular(p) == p
    symlink = tmp_path / "symlink"
    symlink.symlink_to(p)
    with pytest.raises(ValueError):
        Q.U.regular(symlink)
    hard = tmp_path / "hard"
    os.link(p, hard)
    with pytest.raises(ValueError):
        Q.U.regular(p)
    monkeypatch.setattr(Q, "ROOT", tmp_path)
    monkeypatch.setattr(Q, "OUTPUT", "output")
    expected = tmp_path / "output"
    with pytest.raises(ValueError):
        Q.output_directory(tmp_path / "other")
    assert Q.output_directory(expected) == expected
    with pytest.raises(FileExistsError):
        Q.output_directory(expected)


def test_source_and_head_drift_checks(tmp_path, monkeypatch):
    p = tmp_path / "source"
    p.write_bytes(b"pinned")
    monkeypatch.setattr(Q.T, "ROOT", tmp_path)
    monkeypatch.setattr(Q.T.subprocess, "check_output", lambda *a, **k: "head\n")
    Q.T.recheck_sources({"source": Q.T.digest(b"pinned")}, "head", time.monotonic())
    with pytest.raises(ValueError, match="HEAD"):
        Q.T.recheck_sources({"source": Q.T.digest(b"pinned")}, "changed", time.monotonic())
    p.write_bytes(b"drift")
    with pytest.raises(ValueError, match="drift"):
        Q.T.recheck_sources({"source": Q.T.digest(b"pinned")}, "head", time.monotonic())


def prerequisite_fixture():
    """Entirely invented metadata, never read from an original study artifact."""
    takes = panel()
    pins = {"synthetic-source-" + str(i): Q.T.digest(str(i).encode()) for i in range(63)}
    artifacts = {"synthetic-artifact-" + str(i): Q.T.digest(str(i).encode()) for i in range(48)}
    source_rows = []
    refs, checks = {}, []
    for offset in Q.U.OFFSETS:
        for row in rows():
            filename = f"{row['slug']}.offset-{offset:+d}.npz"
            sha = Q.T.digest(filename.encode())
            source_rows.append({**row, "offset": offset, "prediction_file": filename,
                                "prediction_file_sha256": sha, "raw_prediction_sha256": sha,
                                "corrected_prediction_sha256": sha})
            identity = {"dtype": "float32", "samples": Q.N, "sha256": sha}
            refs[filename] = {"npz_sha256": sha, "raw_identity": identity, "corrected_identity": identity,
                              "npz_base64": {"storage": "full local JSON at original JSON pointer",
                                             "json_pointer": "/independent_prediction_archives/" + filename + "/npz_base64",
                                             "decoded_npz_sha256": sha, "base64_utf8_sha256": sha}}
            for member in ("raw", "corrected"):
                checks.append({"file": filename, "member": member, "byte_identical": True,
                               "independent_sha256": sha, "primary_sha256": sha, "dtype": "<f4", "samples": Q.N})
    screen = Q.U.compare(source_rows, takes)
    verifier_sha = "a" * 64
    reports = {"result.json": {"complete": True, "rows": source_rows, "screen": screen, "input_artifacts": artifacts},
               "provenance.json": {"pins": pins, "input_artifacts": artifacts, "prefix": str(Q.U.CPU_PREFIX),
                                   "thread_count": 2, "model": {}, "packages": dict.fromkeys(("numpy", "scipy", "torch"), "synthetic")},
               "inputs.json": {"artifacts": artifacts, "waveforms": {}}}
    for name, count in (("baseline-replay.json", 108), ("baseline-inference-replay.json", 36)):
        report_rows = [{**t, "valid": True, "errors": dict.fromkeys(range(count // 12), 0.0)} for t in takes]
        if count == 36:
            for r in report_rows:
                sha = Q.T.digest(f"{r['slug']}.offset-+0.npz".encode())
                r.update(byte_identical=True, raw_prediction_sha256=sha, original_prediction_sha256_float32=sha)
        reports[name] = {"complete": True, "passed": True, "scalar_count": count,
                         "absolute_tolerance": Q.T.TOL, "screen": Q.F.compare(rows(), takes), "rows": report_rows}
    verified = {"status": "VERIFIED", "scientific_disposition": "PASS", "failures": [],
                "checks": [{"passed": True}] * 21246, "source_pins": pins, "input_artifacts": artifacts,
                "verifier_sha256": verifier_sha, "archive_storage_note": {"full_report_sha256": "b" * 64},
                "independent_rows": deepcopy(source_rows), "independent_screen": deepcopy(screen),
                "inputs": deepcopy(reports["inputs.json"]), "prediction_byte_checks": checks,
                "independent_prediction_archives": refs,
                "independent_baseline_inference_replay": deepcopy(reports["baseline-inference-replay.json"])}
    archive = {"status": "VERIFIED", "scientific_disposition": "PASS", "final_comparison_checks": 21246,
               "final_failures": 0, "payload_references": 120, "lossless_decompression_verified": True,
               "verifier_sha256": verifier_sha, "original_sha256": "b" * 64}
    return reports, verified, archive, pins, artifacts, takes, verifier_sha


def test_synthetic_prior_compact_metadata_pass():
    Q.prior_metadata(*prerequisite_fixture())


@pytest.mark.parametrize("defect", ["failure", "check", "coverage", "score", "byte", "reference", "replay", "independent_zero", "pins"])
def test_synthetic_prior_metadata_rejects_concrete_corruption(defect):
    args = prerequisite_fixture()
    reports, verified = args[:2]
    if defect == "failure":
        verified["failures"] = ["unresolved"]
    elif defect == "check":
        verified["checks"] = verified["checks"][:-1]
    elif defect == "coverage":
        verified["independent_rows"].pop()
    elif defect == "score":
        verified["independent_rows"][-1]["flatref_scores"]["raw_lowband"] += 1e-5
    elif defect == "byte":
        verified["prediction_byte_checks"][-1]["byte_identical"] = False
    elif defect == "reference":
        name = next(iter(verified["independent_prediction_archives"]))
        verified["independent_prediction_archives"][name]["npz_base64"]["decoded_npz_sha256"] = "c" * 64
    elif defect == "replay":
        reports["baseline-replay.json"]["rows"][-1]["errors"][0] = 1.1e-8
    elif defect == "independent_zero":
        verified["independent_baseline_inference_replay"]["rows"][-1]["byte_identical"] = False
    else:
        verified["source_pins"] = {}
    with pytest.raises(ValueError):
        Q.prior_metadata(*args)


def synthetic_guard_files(tmp_path, monkeypatch):
    reports, verified, archive, pins, hashes, takes, verifier_sha = prerequisite_fixture()
    monkeypatch.setattr(Q, "ROOT", tmp_path)
    monkeypatch.setattr(Q, "PLAN", tmp_path / "docs/di-phase-control-plan.md")
    def put(name, data):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    for name in Q.OWN_PINS:
        put(name, name.encode())
    put(Q.REVIEW, b"Verdict: APPROVE")
    put(Q.VERIFIER, b"synthetic verifier source")
    new_verifier_sha = Q.T.digest(b"synthetic verifier source")
    verified["verifier_sha256"] = archive["verifier_sha256"] = new_verifier_sha
    snapshots = {}
    for name, archive_name in Q.ARCHIVES.items():
        data = json.dumps(reports[name]).encode()
        put(archive_name, data)
        primary = str(Path(Q.U.OUTPUT) / name)
        put(primary, data)
        snapshots[primary] = {"sha256": Q.T.digest(data), "size": len(data)}
    for name in (str(Path(Q.U.OUTPUT) / "progress.jsonl"), Q.U.OUTPUT + ".log"):
        put(name, b"synthetic progress")
        snapshots[name] = {"sha256": Q.T.digest(b"synthetic progress"), "size": len(b"synthetic progress")}
    for row in reports["result.json"]["rows"]:
        snapshots[str(Path(Q.U.OUTPUT) / row["prediction_file"])] = {"sha256": row["prediction_file_sha256"], "size": 123}
    verified["primary_artifact_snapshots"] = snapshots
    payload = json.dumps(verified).encode()
    compressed = gzip.compress(payload)
    archive.update(tracked_report=Q.VERIFICATION, tracked_gzip_sha256=Q.T.digest(compressed), tracked_gzip_size=len(compressed),
                   tracked_uncompressed_sha256=Q.T.digest(payload), tracked_uncompressed_size=len(payload))
    put(Q.VERIFICATION, compressed)
    put(Q.ARCHIVE, json.dumps(archive).encode())
    pins["docs/di-timing-sensitivity-inputs.sha256"] = pins.pop("synthetic-source-0")
    # Updated inherited pins must agree in the synthetic compact and provenance.
    verified["source_pins"] = pins
    reports["provenance.json"]["pins"] = pins
    data = json.dumps(reports["provenance.json"]).encode()
    primary = str(Path(Q.U.OUTPUT) / "provenance.json")
    put(Q.ARCHIVES["provenance.json"], data)
    put(primary, data)
    verified["primary_artifact_snapshots"][primary] = {"sha256": Q.T.digest(data), "size": len(data)}
    payload = json.dumps(verified).encode()
    compressed = gzip.compress(payload)
    archive.update(tracked_gzip_sha256=Q.T.digest(compressed), tracked_gzip_size=len(compressed),
                   tracked_uncompressed_sha256=Q.T.digest(payload), tracked_uncompressed_size=len(payload))
    put(Q.VERIFICATION, compressed)
    put(Q.ARCHIVE, json.dumps(archive).encode())
    body = "\nSynthetic frozen body.\n"
    approval = {"status": "DECLARED", "fresh_independent_review": True, "scope": Q.SCOPE,
                "source_sha256": Q.T.digest((tmp_path / Q.OWN_PINS[0]).read_bytes()),
                "test_sha256": Q.T.digest((tmp_path / Q.OWN_PINS[1]).read_bytes()),
                "review_sha256": Q.T.digest(b"Verdict: APPROVE"), "design_sha256": Q.T.digest(body.encode()),
                "inputs_sha256": pins["docs/di-timing-sensitivity-inputs.sha256"]}
    Q.PLAN.write_text("**Declared: synthetic**\n<!-- phase-approval\n" + json.dumps(approval)
                      + "\nphase-approval -->\n## Frozen design\n" + body)
    context = ({}, {"takes": takes, "model": {}}, pins, "revision", {}, {}, {}, hashes, {})
    monkeypatch.setattr(Q.U, "guard", lambda *a: context)
    monkeypatch.setattr(Q.U, "recheck_sources", lambda *a: None)
    monkeypatch.setattr(Q.T.subprocess, "check_output", lambda args, **k: (tmp_path / args[-1].split("HEAD:", 1)[1]).read_bytes())
    monkeypatch.setattr(Q.R, "package_version", lambda *a: "synthetic")
    return approval


def test_reviewed_committed_guard_metadata_only(tmp_path, monkeypatch):
    synthetic_guard_files(tmp_path, monkeypatch)
    context = Q.guard(time.monotonic())
    assert len(context[2]) == 77
    assert len(context[7]) == 48
    # No prior prediction NPZ exists; compact references are never followed.
    assert not list(tmp_path.rglob("*.npz"))


@pytest.mark.parametrize("defect", ["dirty_source", "design", "review", "hardlink", "compressed", "runtime"])
def test_guard_rejects_snapshot_drift(tmp_path, monkeypatch, defect):
    synthetic_guard_files(tmp_path, monkeypatch)
    if defect == "dirty_source":
        original = Q.T.subprocess.check_output
        monkeypatch.setattr(Q.T.subprocess, "check_output", lambda args, **k:
                            b"different committed source" if args[-1] == "HEAD:" + Q.OWN_PINS[0] else original(args, **k))
    elif defect in ("design", "review"):
        data = Q.PLAN.read_text()
        if defect == "design":
            data += "body changed\n"
        else:
            data = data.replace('"fresh_independent_review": true', '"fresh_independent_review": false')
        Q.PLAN.write_text(data)
    elif defect == "hardlink":
        os.link(tmp_path / Q.OWN_PINS[0], tmp_path / "source-alias")
    elif defect == "compressed":
        p = tmp_path / Q.VERIFICATION
        p.write_bytes(p.read_bytes() + b"drift")
    else:
        monkeypatch.setattr(Q.R, "package_version", lambda *a: "changed")
    with pytest.raises(ValueError):
        Q.guard(time.monotonic())


def test_draft_refused_before_inherited_guard_or_assets(monkeypatch):
    class Plan:
        def read_text(self):
            return "DRAFT\n## Frozen design\nbody"
    monkeypatch.setattr(Q.U, "regular", lambda p: Plan())
    monkeypatch.setattr(Q.U, "guard", lambda *a: pytest.fail("inherited guard reached"))
    with pytest.raises(ValueError, match="fresh independent"):
        Q.guard(time.monotonic())


def test_guard_failure_uniformly_preserved(tmp_path, monkeypatch):
    def fail(*a):
        raise ValueError("guard drift")
    monkeypatch.setattr(Q, "guard", fail)
    with pytest.raises(ValueError):
        Q.execute(tmp_path, time.monotonic())
    assert json.loads((tmp_path / "failure.json").read_text())["disposition"] == "INCONCLUSIVE"
    assert json.loads((tmp_path / "result.json").read_text())["screen"]["disposition"] == "INCONCLUSIVE"


def test_budget_includes_guards(tmp_path, monkeypatch):
    assert Q.R.LIMIT == 900
    monkeypatch.setattr(Q, "guard", lambda started: Q.R.check_time(started))
    with pytest.raises(TimeoutError):
        Q.execute(tmp_path, time.monotonic() - 901)
    assert json.loads((tmp_path / "failure.json").read_text())["type"] == "TimeoutError"


def test_exact_cpu_prefix_and_cli_only(monkeypatch):
    monkeypatch.setattr(Q.sys, "prefix", "/unapproved")
    monkeypatch.setattr(Q, "guard", lambda *a: pytest.fail("assets reached"))
    with pytest.raises(ValueError, match="CPU interpreter"):
        Q.main(["--out", Q.OUTPUT])
    for extra in (["--a", "-.8"], ["--outp", Q.OUTPUT]):
        with pytest.raises(SystemExit):
            Q.main(["--out", Q.OUTPUT, *extra])


def test_import_has_no_asset_or_torch_access(monkeypatch):
    # Remove the complete project import chain, including attributes used by
    # `from learn import ...`; prove a fresh chain, rather than a cached import.
    import importlib
    import builtins
    import learn
    import types
    for name in list(sys.modules):
        if name.startswith("learn."):
            monkeypatch.delitem(sys.modules, name)
    for name, value in list(vars(learn).items()):
        if isinstance(value, types.ModuleType) and value.__name__.startswith("learn."):
            monkeypatch.delattr(learn, name)
    original = builtins.__import__
    def forbidden_import(name, *args, **kwargs):
        assert name != "torch"
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", forbidden_import)
    monkeypatch.setattr(Path, "read_bytes", lambda *a: pytest.fail("asset read"))
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("asset read"))
    monkeypatch.setattr(builtins, "open", lambda *a, **k: pytest.fail("asset open"))
    monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("NPZ load"))
    imported = importlib.import_module("learn.di_phase_control")
    assert imported.A == -.9 and imported.N == 288000
