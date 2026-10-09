"""Synthetic precision-probe contracts; no model/dataset files or Torch needed."""
import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")

import hashlib
import json
import math
import numpy as np
import pytest

from learn import di_domain_metric_probe as M


@pytest.mark.parametrize("dtype,integer", [("<f4", "<u4"), ("<f8", "<u8")])
def test_coefficient_bits_roundtrip_exactly(dtype, integer):
    x = np.array([0., -0., .1, 1., -1., np.finfo(dtype).tiny], dtype=dtype)
    record = json.loads(json.dumps(M.window_record(x, dtype)))
    restored = np.array(record["bits"], dtype=integer).view(dtype)
    assert restored.tobytes() == x.tobytes()
    assert record["sha256"] == hashlib.sha256(x.tobytes()).hexdigest()


def test_invalid_windows_refused():
    with pytest.raises(ValueError):
        M.window_record([float("nan")], "<f4")
    with pytest.raises(ValueError):
        M.window_record([1], "<i4")
    with pytest.raises(ValueError):
        M.numpy_terms(np.ones(512), np.ones(512), {256: np.ones(255)})
    with pytest.raises(ValueError):
        M.numpy_terms(np.ones(512), np.ones(512), {})


def test_explicit_rectangular_window_dc_terms_independently():
    n, count, epsilon = 256, 2048, 1e-6
    result = M.numpy_terms(np.ones(count)*.5, np.ones(count), {n: np.ones(n)})
    frames = count//(n//4) + 1
    expected_sc = n*.5*math.sqrt(frames) / (math.sqrt(frames*((n+epsilon)**2+(n//2)*epsilon**2))+epsilon)
    expected_log = math.log((n+epsilon)/(n*.5+epsilon))/(n//2+1)
    assert result["terms"][0]["spectral_convergence"] == pytest.approx(expected_sc, abs=1e-14, rel=0)
    assert result["terms"][0]["log_l1"] == pytest.approx(expected_log, abs=1e-14, rel=0)
    assert result["aggregate"] == pytest.approx(expected_sc+expected_log, abs=1e-14, rel=0)


def test_shared_window_is_an_intervention_not_ignored():
    x = np.random.default_rng(3).normal(size=2048)
    a, b = np.roll(x, 17), x
    first = M.numpy_terms(a,b,{256: np.ones(256)})
    second = M.numpy_terms(a,b,{256: np.hanning(256)})
    assert abs(first["aggregate"]-second["aggregate"]) > 1e-4
    assert M.numpy_terms(b,b,{256: np.ones(256)})["aggregate"] == 0


def fixture_terms(value):
    return {"aggregate": value, "terms": [{"fft": 256, "spectral_convergence": value,
            "log_l1": value, "total": value}]}


def test_component_gate_cannot_hide_cancellation_or_nonfinite():
    a, b = fixture_terms(1.), fixture_terms(1.)
    b["terms"][0]["log_l1"] += 2e-8
    assert not M.terms_agree(a,b)
    b = fixture_terms(1.)
    b["terms"][0]["fft"] = 512
    assert not M.terms_agree(a,b)
    assert not M.terms_agree(a,fixture_terms(float("nan")))
    assert M.terms_agree(fixture_terms(0),fixture_terms(1e-8))


def test_reproduction_and_exact_frozen_semantics_required():
    old = {"numpy": 1., "torch": 1.+3e-8, "absolute_error": 3e-8}
    row = {"original_numpy": old["numpy"], "original_torch": old["torch"],
           "numpy_t32": fixture_terms(old["torch"]), "torch_t32": fixture_terms(old["torch"]),
           "numpy_np64": fixture_terms(1.), "torch_np64": fixture_terms(1.)}
    assert all(M.case_checks(row,old).values())
    row["torch_t32"]["aggregate"] += 1e-12
    assert not M.case_checks(row,old)["explicit_t32_equals_frozen_exactly"]
    row["original_numpy"] += 2e-12
    assert not M.case_checks(row,old)["reproduced"]
    assert not M.case_checks(row,old)["explicit_np64_matches_original"]


def test_draft_guard_does_not_run_git_or_open_external_assets(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/di-domain-metric-probe-plan.md").write_text("Draft")
    monkeypatch.setattr(M, "ROOT", tmp_path)
    monkeypatch.setattr(M.subprocess, "check_output", lambda *a, **k: pytest.fail("draft must refuse first"))
    with pytest.raises(ValueError, match="not declared"):
        M.guard()
