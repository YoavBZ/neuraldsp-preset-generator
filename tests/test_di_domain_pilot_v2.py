"""Synthetic guards for attempt 2; no recording/model/catalog access."""
import gzip
import hashlib
import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from learn import run_di_domain_pilot_v2 as V


def test_draft_refuses_before_any_assets(tmp_path, monkeypatch):
    plan = tmp_path / "draft"
    plan.write_text("Draft")
    monkeypatch.setattr(V, "PLAN", plan)
    monkeypatch.setattr(V.R, "frozen_inputs", lambda: pytest.fail("no assets"))
    monkeypatch.setattr(V.subprocess, "check_output", lambda *a, **k: pytest.fail("no git needed"))
    with pytest.raises(ValueError, match="declared"):
        V.code_inputs()


def test_window_archive_bits_hashes_and_strictness(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "ROOT", tmp_path)
    monkeypatch.setattr(V.P, "FFTS", (4, 8))
    archive = tmp_path / "docs/di-domain-metric-probe-windows.json.gz"
    archive.parent.mkdir()

    def correction(table):
        raw = json.dumps(table).encode()
        blob = gzip.compress(raw)
        archive.write_bytes(blob)
        return {"windows": str(archive.relative_to(tmp_path)),
                "windows_sha256": hashlib.sha256(blob).hexdigest(),
                "windows_raw_sha256": hashlib.sha256(raw).hexdigest()}

    def row(n):
        x = np.linspace(0, 1, n, dtype="<f4")
        return {"torch32": {"dtype": "<f4", "bits": x.view("<u4").tolist(),
                            "sha256": hashlib.sha256(x.tobytes()).hexdigest()}}

    table = {str(n): row(n) for n in (4, 8)}
    config = correction(table)
    loaded = V.load_windows(config)
    assert set(loaded) == {4, 8}
    assert loaded[4].dtype == np.float64 and not loaded[4].flags.writeable
    assert np.array_equal(loaded[4], np.linspace(0, 1, 4, dtype="<f4"))
    config["windows_sha256"] = "wrong"
    with pytest.raises(ValueError, match="archive hash"):
        V.load_windows(config)
    table["4"]["torch32"]["bits"][0] = True
    with pytest.raises(ValueError, match="bits"):
        V.load_windows(correction(table))
    table["4"] = row(4)
    table["4"]["torch32"]["sha256"] = "wrong"
    with pytest.raises(ValueError, match="coefficient hash"):
        V.load_windows(correction(table))
    table["4"] = row(4)
    table["4"]["torch32"]["bits"] = [0x7fc00000] * 4
    table["4"]["torch32"]["sha256"] = hashlib.sha256(np.full(4, 0x7fc00000, dtype="<u4").tobytes()).hexdigest()
    with pytest.raises(ValueError, match="nonfinite"):
        V.load_windows(correction(table))
    table["4"] = row(4)
    table["16"] = row(16)
    with pytest.raises(ValueError, match="coverage"):
        V.load_windows(correction(table))


def test_prerequisite_order_and_exclusive_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "ROOT", tmp_path)
    run = tmp_path / "tmp" / "v2"
    pins = {"code": "frozen"}
    metric = V.stage_directory(run, "metric", pins, "synthetic")
    V.R.write_new(metric / "result.json", {"passed": True})
    with pytest.raises(FileNotFoundError):
        V.stage_directory(run, "native", pins, "synthetic")
    assert not (run / "native").exists()
    replay = V.stage_directory(run, "numpy", pins, "synthetic")
    V.R.write_new(replay / "result.json", {"passed": False})
    with pytest.raises(ValueError, match="numpy prerequisite"):
        V.stage_directory(run, "native", pins, "synthetic")
    with pytest.raises(ValueError, match="pins changed"):
        V.stage_directory(run, "numpy", {"code": "changed"}, "synthetic")
    with pytest.raises(FileExistsError):
        V.stage_directory(run, "metric", pins, "synthetic")
    with pytest.raises(ValueError, match="under project tmp"):
        V.stage_directory(tmp_path / "outside", "metric", pins, "synthetic")


def test_helper_replay_uses_reference_not_self_and_saves_failure(tmp_path, monkeypatch):
    run = tmp_path / "run"
    (run / "metric").mkdir(parents=True)
    out = run / "numpy"
    out.mkdir()
    b = np.arange(12, dtype=float)
    predictions = [b, b*.5, b+1, b*0]
    monkeypatch.setattr(V, "synthetic_cases", lambda: (b, predictions))
    scores = iter([0., 1., 2., 3.])
    monkeypatch.setattr(V.P, "mrstft_numpy", lambda *a, **k: next(scores))
    rows = [{"case": i, "torch": float(i), "prediction_sha256": V.signal_hash(a),
             "target_sha256": V.signal_hash(b)} for i, a in enumerate(predictions)]
    rows[-1]["torch"] = 4.
    (run / "metric/result.json").write_text(json.dumps({"passed": True, "rows": rows}))
    with pytest.raises(ValueError, match="helper NumPy parity"):
        V.numpy_replay(out, run, {})
    report = json.loads((out / "result.json").read_text())
    assert report["passed"] is False and report["rows"][-1]["absolute_error"] == 1.


@pytest.mark.parametrize("fault", ["missing", "signal", "nonfinite"])
def test_helper_replay_rejects_bad_reference(tmp_path, monkeypatch, fault):
    (tmp_path / "metric").mkdir()
    b = np.ones(12)
    monkeypatch.setattr(V, "synthetic_cases", lambda: (b, [b]*4))
    monkeypatch.setattr(V.P, "mrstft_numpy", lambda *a, **k: 0.)
    rows = [{"case": i, "torch": 0., "prediction_sha256": V.signal_hash(b),
             "target_sha256": V.signal_hash(b)} for i in range(4)]
    if fault == "missing":
        rows.pop()
    elif fault == "signal":
        rows[0]["target_sha256"] = "wrong"
    else:
        rows[0]["torch"] = float("nan")
    (tmp_path / "metric/result.json").write_text(json.dumps({"rows": rows}))
    with pytest.raises(ValueError):
        V.numpy_replay(tmp_path, tmp_path, {})


def test_main_refuses_before_asset_access_if_replay_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "prefix", str(tmp_path / ".venv"))
    run = tmp_path / "tmp" / "run"
    out = V.stage_directory(run, "metric", {}, "test")
    V.R.write_new(out / "result.json", {"passed": True})
    monkeypatch.setattr(V, "code_inputs", lambda: ({}, {"attribution": "test"}, {}))
    monkeypatch.setattr(V, "load_windows", lambda _: {})
    monkeypatch.setattr(V.R, "frozen_inputs", lambda: pytest.fail("asset preflight must wait"))
    monkeypatch.setattr(sys, "argv", ["v2", "native", "--run", str(run)])
    with pytest.raises(FileNotFoundError):
        V.main()
    assert not (run / "native").exists()
