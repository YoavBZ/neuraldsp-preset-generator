"""Synthetic flatref diagnostic tests; no real run artifacts opened."""
import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")

import json
import hashlib

import numpy as np
import pytest
from learn import di_morgan_flatref as F


def panel():
    return [{"slug": f"take-{i}", "content": "chords" if i < 6 else "scales", "take": str(i)}
            for i in range(12)]


def rows(net=.8):
    return [{**t, "qc_valid": True, "oracle": 0., "wet": 10., "flatref": 1., "net": net} for t in panel()]


def test_stronger_gate_uses_better_simple_baseline_and_original_criteria():
    assert F.compare(rows(.9), panel())["passed"]
    assert not F.compare(rows(.9001), panel())["passed"]
    assert not F.compare(rows(2.), panel())["passed"]  # Large wet gain is insufficient.
    r = rows(.2)
    for row in r[6:]: row["net"] = 1.
    result = F.compare(r, panel())
    assert result["median_relative_improvement"] == .4 and not result["passed"]
    r = rows(.8)
    for row in r[:4]: row["net"] = 1.
    result = F.compare(r, panel())
    assert result["median_relative_improvement"] == pytest.approx(.2)
    assert result["strict_wins"] == 8 and not result["passed"]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1., 0., False])
def test_even_unused_bad_baseline_is_rejected(bad):
    r = rows()
    r[0]["wet"] = bad
    assert F.compare(r, panel())["disposition"] == "INCONCLUSIVE"


def test_draft_stops_before_original_sources_or_array_access(tmp_path, monkeypatch):
    plan = tmp_path / "draft"
    plan.write_text("Draft")
    monkeypatch.setattr(F, "PLAN", plan)
    monkeypatch.setattr(F.C, "code_inputs", lambda: pytest.fail("must stop first"))
    with pytest.raises(ValueError, match="verified prerequisite"):
        F.guard()


def test_artifact_manifest_exact_coverage_hash_and_path_refusal(tmp_path, monkeypatch):
    source = tmp_path / "tmp/control"
    manifest = tmp_path / "hashes"
    monkeypatch.setattr(F, "ROOT", tmp_path)
    monkeypatch.setattr(F, "SOURCE", source)
    monkeypatch.setattr(F, "HASHES", manifest)
    lines = []
    for stage in ("prepare", "render", "infer"):
        (source / stage).mkdir(parents=True)
        for t in panel():
            path = source / stage / f"{t['slug']}.npz"
            path.write_bytes(f"synthetic-{stage}-{t['slug']}".encode())
            lines.append(f"{F.R.sha(path)}  {path.relative_to(tmp_path)}")
    manifest.write_text("\n".join(lines)+"\n")
    assert len(F.input_hashes(panel())) == 36
    manifest.write_text("\n".join(lines[:-1])+"\n")
    with pytest.raises(ValueError, match="all 36"):
        F.input_hashes(panel())
    manifest.write_text("\n".join(lines+[lines[0]])+"\n")
    with pytest.raises(ValueError, match="duplicate"):
        F.input_hashes(panel())
    manifest.write_text("\n".join(lines[:-1]+["0"*64+"  ../outside.npz"])+"\n")
    with pytest.raises(ValueError, match="undeclared"):
        F.input_hashes(panel())
    manifest.write_text("\n".join(lines)+"\n")
    (source / "prepare/take-0.npz").write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed verified"):
        F.input_hashes(panel())


@pytest.mark.parametrize("mismatch", [False, True])
def test_complete_replay_precedes_any_experimental_flatref(tmp_path, monkeypatch, mismatch):
    source, output = tmp_path / "source", tmp_path / "output"
    output.mkdir()
    takes = panel()
    for stage in ("prepare", "render", "infer"):
        (source / stage).mkdir(parents=True)
    for t in takes:
        x = np.arange(12, dtype=float) / 10
        np.savez_compressed(source / "prepare" / f"{t['slug']}.npz", di=x, target=x+1)
        np.savez_compressed(source / "render" / f"{t['slug']}.npz", baseline=x+2)
        np.savez_compressed(source / "infer" / f"{t['slug']}.npz", prediction=x+3)
    avg = tmp_path / "synthetic-average.npy"
    np.save(avg, np.zeros(4))
    manifest = {"average": {"path": str(avg), "sha256": F.R.sha(avg)}, "attribution": "synthetic"}
    monkeypatch.setattr(F, "SOURCE", source)
    monkeypatch.setattr(F.R, "require_report", lambda *a: None)
    monkeypatch.setattr(F, "input_hashes", lambda *a: {"synthetic": "frozen"})
    calls = []
    table = {4: np.ones(4)}
    score = {"primary": 2., "canonical_waveform_l1": .1, "raw_lowband": .2}
    old = {"rows": [{**t, "oracle": 0., "input_scores": dict(score), "network_scores": dict(score)} for t in takes]}
    if mismatch: old["rows"][-1]["network_scores"]["primary"] = 3.
    def scoring(a, target, raw, *, windows):
        assert windows is table
        calls.append("score")
        return dict(score)
    def canonical(wet, average):
        replay = json.loads((output / "baseline-replay.json").read_text())
        assert replay["passed"] and len(replay["rows"]) == 12
        assert calls.count("score") >= 24
        calls.append("flatref")
        return wet+1
    monkeypatch.setattr(F.P, "score_prediction", scoring)
    monkeypatch.setattr(F.P, "canonical_target", canonical)
    if mismatch:
        with pytest.raises(ValueError, match="replay failed"):
            F.run(output, manifest, takes, table, old)
        assert calls.count("score") == 24 and "flatref" not in calls
        assert not (output / "result.json").exists()
    else:
        F.run(output, manifest, takes, table, old)
        assert calls.count("score") == 36 and calls.count("flatref") == 12
        result = json.loads((output / "result.json").read_text())
        assert result["complete"] and result["screen"]["valid"] and not result["screen"]["passed"]
