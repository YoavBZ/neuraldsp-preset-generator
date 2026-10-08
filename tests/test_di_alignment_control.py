"""Synthetic/mock evidence only. Never open real assets or numerical reports."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.signal import butter, sosfiltfilt

from learn import di_alignment_control as A


def panel():
    return [{"slug": f"take-{i}", "content": "chords" if i < 6 else "scales", "take": str(i)}
            for i in range(12)]


@pytest.fixture(scope="module")
def noise():
    return np.random.default_rng(20261008).normal(0, .03, A.P.SCORE) + .004


def passing_rows():
    return [{**c, "valid": True, "consistent": True, "accepted": c["positive"],
             "nonfinite_diagnostic_fields": [],
             "actual_fields": {"lag": c["truth_lag"], "polarity": c["truth_polarity"]}
             if c["positive"] else None} for c in A.cases(panel())]


def test_exact_panel_and_next_different_take_within_group():
    takes = panel()[::2] + panel()[1::2]  # Deliberately interleave groups/order.
    cases = A.cases(takes)
    assert len(cases) == len({c["case_id"] for c in cases}) == 156
    for c in cases[:144]:
        assert c["positive"] and c["pair"] == A.identity(c)
        assert c["truth_lag"] == c["catalog_lag"] == c["imposed_lag"]
        assert c["truth_polarity"] == (-1 if c["arm"] == "polarity" else 1)
    for c in cases[144:]:
        group = [t for t in takes if t["content"] == c["content"]]
        index = next(i for i, t in enumerate(group) if t["slug"] == c["slug"])
        assert c["pair"] == group[(index+1) % 6]
        assert c["pair"]["take"] != c["take"]
        assert c["truth_lag"] is c["truth_polarity"] is None
        assert c["catalog_lag"] == c["imposed_lag"] == 0


@pytest.mark.parametrize("damage", ["missing", "duplicate", "take", "content", "path"])
def test_invalid_panel(damage):
    takes = panel()
    if damage == "missing": takes.pop()
    if damage == "duplicate": takes[-1] = takes[0]
    if damage == "take": takes[-1]["take"] = takes[0]["take"]
    if damage == "content": takes[-1]["content"] = "other"
    if damage == "path": takes[-1]["slug"] = "../escape"
    with pytest.raises(ValueError):
        A.cases(takes)


@pytest.mark.parametrize("lag", [-128, 0, 128])
@pytest.mark.parametrize("arm,polarity", [("identity", 1), ("polarity", -1)])
def test_known_lags_sign_polarity_edges_and_actual_fields(noise, lag, arm, polarity):
    di, wet, recipe = A.construct(noise, noise, arm, lag)
    result = A.diagnose(di, wet, lag)
    assert result["valid"] and result["consistent"] and result["accepted"]
    assert result["actual_fields"]["lag"] == lag
    assert result["actual_fields"]["polarity"] == polarity
    assert [e["lag"] for e in result["estimates"]] == [lag]*3
    g, n, used = A.P.GUARD, A.P.CALIBRATION, recipe["prefix_samples"]
    np.testing.assert_array_equal(wet[g+lag:g+lag+n], polarity*di[g:g+n])
    assert not np.any(di[used:]) and not np.any(wet[used:])
    assert recipe["di_prefix_sha256"] == A.signal_hash(noise[:used])
    assert recipe["wet_prefix_sha256"] == A.signal_hash(wet[:used])
    assert A.P.calibrate(di, wet, lag) == A.P.Calibration(**result["actual_fields"])


@pytest.mark.parametrize("lag", [-128, 0, 128])
def test_finite_shift_has_no_circular_wrap(lag):
    x = np.arange(1000, dtype=float) + 1
    y = A.finite_shift(x, lag)
    for n in range(len(x)):
        assert y[n] == (x[n-lag] if 0 <= n-lag < len(x) else 0)
    if lag:
        assert not np.array_equal(y, np.roll(x, lag))
    for edge in (-1000, 1000, -1001, 1001):
        assert not A.finite_shift(x, edge).any()
    impulses = np.zeros(1000)
    impulses[0], impulses[-1] = 3., 7.
    y = A.finite_shift(impulses, lag)
    assert y.sum() == (3. if lag > 0 else 7. if lag < 0 else 10.)


@pytest.mark.parametrize("arm", ["lowpass", "tanh"])
def test_transform_complete_six_seconds_before_crop_shift_padding(noise, arm):
    x = noise.copy()
    used = A.P.CALIBRATION + 2*A.P.GUARD
    x[used:] *= 20  # Global std and filter boundary context must be retained.
    if arm == "lowpass":
        sos = butter(4, 1200, btype="lowpass", fs=48000, output="sos")
        expected = sosfiltfilt(sos, x, padtype="odd", padlen=27)
        wrong = sosfiltfilt(sos, x[:used], padtype="odd", padlen=27)
    else:
        expected = np.tanh(3*x/np.std(x))*np.std(x)/3
        wrong = np.tanh(3*x[:used]/np.std(x[:used]))*np.std(x[:used])/3
        assert expected.mean() != pytest.approx(x.mean(), abs=1e-5)
    actual = A.transform(x, arm)
    np.testing.assert_array_equal(actual, expected)
    assert not np.array_equal(actual[:used], wrong)
    _, wet, _ = A.construct(x, x, arm, -128)
    np.testing.assert_array_equal(wet[:used], A.finite_shift(expected[:used], -128))
    result = A.diagnose(*A.construct(x, x, arm, -128)[:2], -128)
    assert result["valid"] and result["consistent"]  # Acceptance is diagnostic.


def test_calibrator_and_recorder_ignore_buffer_after_first_four_seconds(noise):
    di, wet, _ = A.construct(noise, noise, "polarity", 128)
    before = A.diagnose(di, wet, 128)
    end = A.P.GUARD+A.P.CALIBRATION
    di[end:] = np.nan
    wet[end:] = np.inf
    di[:A.P.GUARD] = np.nan
    wet[:A.P.GUARD] = -np.inf
    assert A.diagnose(di, wet, 128) == before
    assert A.P.calibrate(di, wet, 128) == A.P.Calibration(**before["actual_fields"])


def test_real_primitives_on_independent_noise_and_ambiguous_tone(noise):
    other = np.random.default_rng(77).normal(0, .03, A.P.SCORE)
    result = A.diagnose(*A.construct(noise, other, "mismatch", 0)[:2], 0)
    assert result["valid"] and result["consistent"] and not result["accepted"]
    assert len(result["estimates"]) == 3 and len(result["gates"]) == 5
    assert result["calibrate_first_error"] is not None
    t = np.arange(A.P.SCORE)/A.P.SR
    periodic = .04*np.sin(2*np.pi*1000*t)
    result = A.diagnose(*A.construct(periodic, periodic, "identity", 128)[:2], 128)
    assert result["consistent"] and not result["accepted"]


def test_evidence_truth_errors_and_mismatch_has_no_invented_truth(noise):
    cases = A.cases(panel())
    positive = next(c for c in cases if c["arm"] == "polarity" and c["imposed_lag"] == -128)
    row = A.evaluate(positive, noise, noise)
    assert row["estimate_lag_errors"] == [0, 0, 0]
    assert row["accepted_lag_error"] == 0
    assert row["estimated_polarity_correct"] and row["accepted_polarity_correct"]
    assert row["nonfinite_diagnostic_fields"] == []
    other = np.random.default_rng(23).normal(0, .03, A.P.SCORE)
    row = A.evaluate(cases[-1], noise, other)
    assert row["estimate_lag_errors"] is row["accepted_lag_error"] is None
    assert row["estimated_polarity_correct"] is row["accepted_polarity_correct"] is None
    assert row["pair"]["take"] != row["take"]


@pytest.mark.parametrize("value,passed", [(10., False), (np.nextafter(10., np.inf), True)])
def test_strict_sharpness_boundary(value, passed):
    estimates = [(0, value, 2.), (0, 20., 2.), (0, 20., 2.)]
    gates, error = A.predicates(estimates, .5, 0)
    assert gates["sharpness"][0] == passed
    assert error == (None if passed else A.ERRORS[0])


@pytest.mark.parametrize("value,passed", [(1.2, False), (np.nextafter(1.2, np.inf), True)])
def test_strict_separation_boundary(value, passed):
    estimates = [(0, 20., 2.), (0, 20., value), (0, 20., 2.)]
    gates, error = A.predicates(estimates, .5, 0)
    assert gates["peak_separation"][1] == passed
    assert error == (None if passed else A.ERRORS[1])


@pytest.mark.parametrize("prior,half,correlation,error", [
    (16, 8, .5, None), (17, 8, .5, A.ERRORS[2]), (0, 9, .5, A.ERRORS[3]),
    (0, 8, -.5, None), (0, 8, np.nextafter(.5, 0), A.ERRORS[4]),
    (0, 8, -np.nextafter(.5, 0), A.ERRORS[4]), (0, 0, float("nan"), A.ERRORS[4]),
])
def test_inclusive_prior_range_correlation_boundaries(prior, half, correlation, error):
    assert A.predicates([(0, 20., 2.), (half, 20., 2.), (0, 20., 2.)], correlation, prior)[1] == error


@pytest.mark.parametrize("failure", range(5))
def test_every_original_rejection_matches_actual_and_keeps_downstream(noise, monkeypatch, failure):
    estimates = [(0, 20., 2.), (0, 20., 2.), (0, 20., 2.)]
    if failure == 0: estimates[1] = (0, 10., 1.)
    if failure == 1: estimates[2] = (0, 20., 1.2)
    if failure == 3: estimates[2] = (9, 20., 2.)
    if failure == 4: estimates[0] = (512, 20., 2.)
    prior = 17 if failure == 2 else estimates[0][0]
    calls = []
    def gcc(*args):
        value = estimates[len(calls) % 3]
        calls.append(value)
        return value
    monkeypatch.setattr(A.P, "_gcc_phat", gcc)
    # For correlation rejection avoid half disagreement and construct orthogonal
    # deterministic bandpass returns. Other cases still use real filtering.
    if failure == 4:
        estimates[:] = [(0, 20., 2.)]*3
        prior = 0
        sequence = iter([np.tile([1., -1.], A.P.CALIBRATION//2),
                         np.tile([1., 1., -1., -1.], A.P.CALIBRATION//4)]*2)
        monkeypatch.setattr(A.P, "bandpass", lambda x: next(sequence))
    di, wet, _ = A.construct(noise, noise, "identity", 0)
    row = A.diagnose(di, wet, prior)
    assert row["valid"] and row["consistent"] and not row["accepted"]
    assert row["calibrate_first_error"] == row["predicted_first_error"] == A.ERRORS[failure]
    assert len(calls) == 6 and len(row["estimates"]) == 3
    assert "correlation" in row and "absolute_correlation_at_least_half" in row["gates"]


@pytest.mark.parametrize("damage", ["lag", "polarity", "correlation", "sharpness", "half_lags",
                                    "half_sharpness", "peak_separation", "half_peak_separation", "reject"])
def test_actual_consistency_checks_all_returned_fields(noise, monkeypatch, damage):
    di, wet, _ = A.construct(noise, noise, "identity", 0)
    original = A.P.calibrate
    def changed(*args):
        if damage == "reject": raise ValueError("unexpected rejection")
        value = original(*args)
        old = getattr(value, damage)
        return replace(value, **{damage: tuple(v+1 for v in old) if isinstance(old, tuple) else old+1})
    monkeypatch.setattr(A.P, "calibrate", changed)
    assert not A.diagnose(di, wet, 0)["consistent"]


def test_nonfinite_estimates_retained_and_inconclusive(noise, monkeypatch):
    monkeypatch.setattr(A.P, "_gcc_phat", lambda *a: (0, float("nan"), 2.))
    case = A.cases(panel())[0]
    row = A.evaluate(case, noise, noise)
    assert not row["valid"] and row["nonfinite_diagnostic_fields"]
    rows = passing_rows()
    rows[0] = row
    assert A.compare(rows, panel())["disposition"] == "INCONCLUSIVE"


def test_gate_required_arms_processing_rejection_wrong_accept_and_negative_details():
    rows = passing_rows()
    result = A.compare(rows, panel())
    assert result["disposition"] == "PASS"
    assert result["counts_by_arm_content"]["identity"]["all"] == {
        "total": 36, "accepted": 36, "rejected": 0, "acceptance_rate": 1.}
    for r in rows:
        if r["arm"] in ("lowpass", "tanh"):
            r["accepted"], r["actual_fields"] = False, None
    assert A.compare(rows, panel())["passed"]
    rows[0]["accepted"], rows[0]["actual_fields"] = False, None
    assert A.compare(rows, panel())["disposition"] == "FAIL"
    rows = passing_rows()
    rows[0]["actual_fields"]["lag"] += 1  # Inclusive truth-error boundary.
    assert A.compare(rows, panel())["passed"]
    rows[0]["actual_fields"]["lag"] += 1
    assert len(A.compare(rows, panel())["wrong_accepted_positives"]) == 1
    rows = passing_rows()
    rows[6]["actual_fields"]["polarity"] = -1  # Processing acceptance can fail.
    assert A.compare(rows, panel())["disposition"] == "FAIL"
    rows = passing_rows()
    rows[-1]["accepted"] = True
    rows[-1]["actual_fields"] = {"lag": 0, "polarity": 1}
    assert A.compare(rows, panel())["accepted_mismatch_negatives"] == [rows[-1]]


@pytest.mark.parametrize("damage", ["missing", "duplicate", "truth", "pair", "consistent", "valid", "nonfinite", "fields", "unflagged_nonfinite"])
def test_inconclusive_precedes_scientific_fail(damage):
    rows = passing_rows()
    rows[1]["accepted"], rows[1]["actual_fields"] = False, None
    if damage == "missing": rows.pop()
    if damage == "duplicate": rows[-1] = rows[0]
    if damage == "truth": rows[0]["truth_lag"] += 1
    if damage == "pair": rows[-1]["pair"] = rows[0]["pair"]
    if damage == "consistent": rows[0]["consistent"] = False
    if damage == "valid": rows[0]["valid"] = False
    if damage == "nonfinite": rows[0]["nonfinite_diagnostic_fields"] = ["row.estimates[0].sharpness"]
    if damage == "fields": rows[0]["actual_fields"]["lag"] = float("nan")
    if damage == "unflagged_nonfinite": rows[0]["actual_fields"]["correlation"] = float("nan")
    assert A.compare(rows, panel())["disposition"] == "INCONCLUSIVE"


@pytest.fixture
def guarded_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "ROOT", tmp_path)
    monkeypatch.setattr(A, "PLAN", tmp_path / "docs/di-alignment-control-plan.md")
    monkeypatch.setattr(A, "SOURCE", tmp_path / "tmp/di-morgan-control-20261008")
    monkeypatch.setattr(A, "HASHES", tmp_path / "docs/di-morgan-flatref-inputs.sha256")
    inherited = {f"source-{i}": A.digest(str(i).encode()) for i in range(35)}
    monkeypatch.setattr(A.C, "code_inputs", lambda: ({}, {"takes": panel(), "attribution": "synthetic"}, inherited))
    for name in A.OWN_PINS:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("synthetic source")
    (tmp_path / A.REVIEW).write_text("Verdict: APPROVE\nSynthetic mocked review")
    prep_rows = [{**t, "qc_valid": True, "qc": {"valid": True}, "oracle_scores": {"primary": 0.}} for t in panel()]
    prep = {"complete": True, "valid": True, "rows": prep_rows}
    verify = {"status": "VERIFIED_WITH_EVIDENCE_LIMITS", "failures": [],
              "checks": [{"passed": True}], "source_pins": inherited,
              "verifier_sha256": A.digest((tmp_path / A.VERIFIER).read_bytes()), "preparation": prep_rows}
    (tmp_path / "docs/di-morgan-control-prepare.json").write_text(json.dumps(prep))
    (tmp_path / "docs/di-morgan-control-verification.json").write_text(json.dumps(verify))
    (A.SOURCE / "prepare").mkdir(parents=True)
    (A.SOURCE / "prepare/result.json").write_text(json.dumps(prep))
    (A.SOURCE / "prepare/provenance.json").write_text(json.dumps({"pins": inherited}))
    body = "## Frozen design\nSynthetic scientific body\n"
    approval = {"status": "DECLARED", "fresh_independent_review": True,
                "mean_interpretation": "uncentered-input-exact-formula",
                "review_sha256": A.digest((tmp_path / A.REVIEW).read_bytes()),
                "source_sha256": A.digest((tmp_path / "learn/di_alignment_control.py").read_bytes()),
                "test_sha256": A.digest((tmp_path / "tests/test_di_alignment_control.py").read_bytes()),
                "design_sha256": A.digest(A.design_bytes(body))}
    A.PLAN.write_text("**Declared: synthetic**\n<!-- alignment-approval\n" + json.dumps(approval)
                      + "\nalignment-approval -->\n" + body)
    committed = {n: (tmp_path / n).read_bytes() for n in A.OWN_PINS}
    def git_read(args, **kwargs):
        if args[1] == "show": return committed[args[2].removeprefix("HEAD:")]
        assert args == ["git", "rev-parse", "HEAD"]
        return "synthetic-revision\n"
    monkeypatch.setattr(A.subprocess, "check_output", git_read)
    return tmp_path


def test_complete_committed_guard_with_only_mock_metadata(guarded_tree):
    manifest, pins, revision = A.guard()
    assert len(manifest["takes"]) == 12 and len(pins) == 35+len(A.OWN_PINS)
    assert revision == "synthetic-revision"


@pytest.mark.parametrize("damage", ["draft", "uncommitted", "review", "prepare", "verify", "sources", "provenance", "saved"])
def test_guard_refusal_precedes_all_asset_and_output_access(guarded_tree, monkeypatch, damage):
    if damage == "draft":
        A.PLAN.write_text("DRAFT")
    elif damage == "uncommitted":
        (A.ROOT / "learn/di_alignment_control.py").write_text("changed")
    elif damage == "review":
        # Keep committed bytes, but return a new plan attestation with wrong review digest.
        original = A.digest
        monkeypatch.setattr(A, "digest", lambda data: "wrong" if data == (A.ROOT / A.REVIEW).read_bytes() else original(data))
    elif damage in ("prepare", "verify", "sources"):
        name = "docs/di-morgan-control-prepare.json" if damage == "prepare" else "docs/di-morgan-control-verification.json"
        data = A.read_json(A.ROOT / name)
        if damage == "prepare": data["rows"][0]["oracle_scores"]["primary"] = 1e-6
        if damage == "verify": data["checks"][0]["passed"] = False
        if damage == "sources": data["source_pins"] = {}
        # Mock git attests this bad prerequisite as committed: test semantic checks.
        blob = json.dumps(data).encode()
        (A.ROOT / name).write_bytes(blob)
        original = A.subprocess.check_output
        monkeypatch.setattr(A.subprocess, "check_output", lambda args, **kw: blob if args[-1] == f"HEAD:{name}" else original(args, **kw))
    elif damage == "provenance":
        (A.SOURCE / "prepare/provenance.json").write_text('{"pins": {}}')
    elif damage == "saved":
        (A.SOURCE / "prepare/result.json").write_text("changed")
    monkeypatch.setattr(A, "load_inputs", lambda *a: pytest.fail("assets reached"))
    monkeypatch.setattr(A, "output_directory", lambda *a: pytest.fail("output reached"))
    monkeypatch.setattr(A.sys, "prefix", str(A.ROOT / ".venv"))
    with pytest.raises(ValueError):
        A.main(["--out", A.OUTPUT])


def make_hashes():
    lines = []
    for stage in ("prepare", "render", "infer"):
        for t in panel():
            path = A.SOURCE / stage / f"{t['slug']}.npz"
            if stage == "prepare": path.write_bytes(f"synthetic-{t['slug']}".encode())
            sha = A.R.sha(path) if stage == "prepare" else "a"*64
            lines.append(f"{sha}  {path.relative_to(A.ROOT)}")
    A.HASHES.write_text("\n".join(lines)+"\n")
    return lines


def test_hash_subset_all12_barrier_and_only_di_loaded(guarded_tree, monkeypatch, noise):
    make_hashes()
    hashes = A.declared_hashes(panel())
    assert len(hashes) == 12 and all("/prepare/" in n for n in hashes)
    original = A.R.sha
    reads, loads = [], []
    def sha(path):
        assert Path(path).parent.name == "prepare"
        reads.append(str(path))
        return original(path)
    class Saved:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def __getitem__(self, key):
            assert key == "di"
            return noise
    def load(path, *, allow_pickle):
        assert len(set(reads)) == 12 and allow_pickle is False
        assert Path(path).parent.name == "prepare"
        loads.append(str(path))
        return Saved()
    monkeypatch.setattr(A.R, "sha", sha)
    monkeypatch.setattr(np, "load", load)
    loaded = A.load_inputs(panel(), hashes, A.time.monotonic())
    assert len(loaded) == len(loads) == 12


@pytest.mark.parametrize("damage", ["missing", "duplicate", "unknown", "syntax", "digest", "changed", "symlink"])
def test_manifest_and_changed_inputs_fail_before_np_load(guarded_tree, monkeypatch, damage):
    lines = make_hashes()
    if damage == "missing": lines.pop()
    if damage == "duplicate": lines.append(lines[0])
    if damage == "unknown": lines[-1] = "a"*64+"  ../escape.npz"
    if damage == "syntax": lines[-1] = "a"*64+" wrong-separator"
    if damage == "digest": lines[-1] = "z"*64+"  "+lines[-1].split("  ")[1]
    A.HASHES.write_text("\n".join(lines)+"\n")
    monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("loaded before validation"))
    with pytest.raises(ValueError):
        hashes = A.declared_hashes(panel())
        path = A.SOURCE / "prepare/take-0.npz"
        if damage == "changed": path.write_bytes(b"changed")
        if damage == "symlink":
            path.unlink()
            path.symlink_to(A.SOURCE / "prepare/take-1.npz")
        A.load_inputs(panel(), hashes, A.time.monotonic())


def test_exact_exclusive_output_and_alias_refusal(guarded_tree):
    out = A.output_directory(A.ROOT / A.OUTPUT)
    assert out == A.ROOT / A.OUTPUT
    with pytest.raises(FileExistsError): A.output_directory(out)
    with pytest.raises(ValueError): A.output_directory(A.ROOT / "tmp/other")
    with pytest.raises(ValueError): A.output_directory(A.ROOT / "tmp/../tmp" / out.name)
    out.rmdir()
    other = A.ROOT / "synthetic-output"
    other.mkdir()
    out.symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError): A.output_directory(out)


def test_only_cli_option_and_prefix_before_guard(monkeypatch):
    monkeypatch.setattr(A, "guard", lambda: pytest.fail("guard before prefix/CLI validation"))
    monkeypatch.setattr(A.sys, "prefix", "/synthetic/wrong-prefix")
    with pytest.raises(ValueError, match="helper environment"): A.main(["--out", A.OUTPUT])
    with pytest.raises(SystemExit): A.main(["--out", A.OUTPUT, "--data", "other.npz"])
    with pytest.raises(SystemExit): A.main(["--o", A.OUTPUT])


@pytest.mark.parametrize("failure", [False, True])
def test_all156_progress_result_coverage_and_case_failure_retention(guarded_tree, monkeypatch, failure):
    out = A.output_directory(A.ROOT / A.OUTPUT)
    monkeypatch.setattr(A, "declared_hashes", lambda takes: {"synthetic": "hash"})
    monkeypatch.setattr(A, "load_inputs", lambda *a: {t["slug"]: np.arange(3.) for t in panel()})
    expected = {r["case_id"]: r for r in passing_rows()}
    calls = []
    def evaluate(case, *args):
        calls.append(case["case_id"])
        if failure and len(calls) == 10: raise ValueError("synthetic case failure")
        return deepcopy(expected[case["case_id"]])
    monkeypatch.setattr(A, "evaluate", evaluate)
    A.run(out, {"takes": panel(), "attribution": "synthetic"}, {}, "synthetic", A.time.monotonic())
    result = A.read_json(out / "result.json")
    progress = [json.loads(s) for s in (out / "progress.jsonl").read_text().splitlines()]
    assert result["complete"] and len(calls) == 156 and result["rows"] == progress
    assert result["screen"]["disposition"] == ("INCONCLUSIVE" if failure else "PASS")
    assert not list(out.glob("*.npz"))


def test_cooperative_budget_failure_preserves_partial_progress(guarded_tree, monkeypatch):
    monkeypatch.setattr(A.sys, "prefix", str(A.ROOT / ".venv"))
    monkeypatch.setattr(A, "guard", lambda: ({"takes": panel(), "attribution": "synthetic"}, {}, "synthetic"))
    monkeypatch.setattr(A, "declared_hashes", lambda takes: {})
    monkeypatch.setattr(A, "load_inputs", lambda *a: {t["slug"]: np.arange(3.) for t in panel()})
    row = passing_rows()[0]
    monkeypatch.setattr(A, "evaluate", lambda *a: row)
    checks = []
    def check(start):
        checks.append(start)
        if len(checks) == 2: raise TimeoutError("15-minute synthetic budget exceeded")
    monkeypatch.setattr(A.R, "check_time", check)
    with pytest.raises(TimeoutError): A.main(["--out", str(A.ROOT / A.OUTPUT)])
    out = A.ROOT / A.OUTPUT
    assert len((out / "progress.jsonl").read_text().splitlines()) == 1
    assert A.read_json(out / "failure.json")["disposition"] == "INCONCLUSIVE"
    assert not (out / "result.json").exists()


def test_manifest_failure_preserves_provenance_before_assets(guarded_tree, monkeypatch):
    monkeypatch.setattr(A.sys, "prefix", str(A.ROOT / ".venv"))
    monkeypatch.setattr(A, "load_inputs", lambda *a: pytest.fail("assets reached"))
    # The synthetic fixture's hash-manifest placeholder is intentionally invalid.
    with pytest.raises(ValueError, match="artifact hash syntax"):
        A.main(["--out", str(A.ROOT / A.OUTPUT)])
    out = A.ROOT / A.OUTPUT
    assert len(A.read_json(out / "provenance.json")["pins"]) == 35+len(A.OWN_PINS)
    assert A.read_json(out / "failure.json")["disposition"] == "INCONCLUSIVE"


def test_actual_budget_inclusive_boundary(monkeypatch):
    monkeypatch.setattr(A.R.time, "monotonic", lambda: 900.)
    A.R.check_time(0.)
    monkeypatch.setattr(A.R.time, "monotonic", lambda: np.nextafter(900., np.inf))
    with pytest.raises(TimeoutError): A.R.check_time(0.)
