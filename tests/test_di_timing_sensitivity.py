"""Synthetic evidence only: never load/hash any real study asset or score report."""
import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")

from copy import deepcopy
import json
from pathlib import Path
import time

import numpy as np
import pytest

from learn import di_timing_sensitivity as T


def panel():
    return [{"slug": f"take-{i}", "content": "chords" if i < 6 else "scales", "take": str(i)}
            for i in range(12)]


def score(primary):
    return {"primary": primary, "canonical_waveform_l1": primary/2, "raw_lowband": primary/3}


def row(take, offset=0, net=.8):
    return {**take, "offset": offset, "valid": True, "qc_valid": True, "oracle": 0.,
            "wet": 2., "net": net, "flatref": 1., "input_scores": score(2.),
            "network_scores": score(net), "flatref_scores": score(1.)}


def rows():
    return [row(t, offset) for offset in T.OFFSETS for t in panel()]


def set_primary(r, arm, value):
    r[arm] = r[T.ARMS[arm]]["primary"] = value


def paths(takes):
    return [T.SOURCE / stage / f"{t['slug']}.npz"
            for stage in ("prepare", "render", "infer") for t in takes] + [
                T.FLAT / f"{t['slug']}.npz" for t in takes]


def metadata(takes, hashes):
    original_rows = []
    for t in takes:
        r = row(t)
        for k in ("offset", "valid"):
            r.pop(k)
        original_rows.append(r)
    old = {n: h for n, h in hashes.items() if "/di-morgan-control-" in n}
    original = {"complete": True, "rows": original_rows, "screen": T.F.compare(original_rows, takes),
                "input_artifacts": old}
    qc = {"valid": True, "reasons": [], "metrics": {"synthetic": 1.}}
    prepare = {"complete": True, "valid": True, "rows": [
        {**t, "qc_valid": True, "qc": deepcopy(qc), "oracle_scores": score(0.)} for t in takes]}
    control = {"verifier_sha256": "b"*64, "preparation": [
        {**t, "qc": deepcopy(qc), "oracle_scores": score(0.), "target_sha256": "c"*64} for t in takes],
        "replay": [{**t, "prediction_sha256_float32": "d"*64} for t in takes]}
    independent = [{**r, "flatref_waveform_sha256_float64": "e"*64} for r in original_rows]
    verification = {"status": "VERIFIED_WITH_EVIDENCE_LIMITS", "failures": [],
        "checks": [{"passed": True} for _ in range(1215)], "source_pins": {},
        "verifier_sha256": "a"*64, "independent_screen": deepcopy(original["screen"]),
        "independent_rows": independent, "input_artifacts": old,
        "primary_artifact_hashes": {Path(n).name: h for n, h in hashes.items() if "/di-morgan-flatref-" in n},
        "waveform_comparison": [{"slug": t["slug"], "byte_identical": True,
            "max_absolute_error": 0., "npz_sha256": hashes[str((T.FLAT / f"{t['slug']}.npz").relative_to(T.ROOT))],
            "primary_sha256_float64": "e"*64} for t in takes]}
    return original, verification, prepare, control


@pytest.fixture
def tree(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "ROOT", tmp_path)
    monkeypatch.setattr(T, "PLAN", tmp_path / "docs/di-timing-sensitivity-plan.md")
    monkeypatch.setattr(T, "HASHES", tmp_path / "docs/di-timing-sensitivity-inputs.sha256")
    monkeypatch.setattr(T, "SOURCE", tmp_path / "tmp/di-morgan-control-20261008")
    monkeypatch.setattr(T, "FLAT", tmp_path / "tmp/di-morgan-flatref-20261008")
    hashes = {str(p.relative_to(tmp_path)): T.digest(str(p).encode()) for p in paths(panel())}
    T.HASHES.parent.mkdir(parents=True)
    T.HASHES.write_text("".join(f"{h}  {n}\n" for n, h in hashes.items()))
    return hashes


@pytest.mark.parametrize("offset", T.OFFSETS)
def test_finite_shift_real_index_sign_edges_and_original_center(offset):
    x = np.arange(T.P.SCORE, dtype=float)+1
    before = x.copy()
    y = T.finite_shift(x, offset)
    indices = np.arange(len(x))-offset
    valid = (indices >= 0) & (indices < len(x))
    np.testing.assert_array_equal(y[valid], x[indices[valid]])
    assert not y[~valid].any()
    np.testing.assert_array_equal(x, before)
    center = np.arange(72000, 216000)
    assert valid[center].all()  # Finite padding never enters this fixed center.
    np.testing.assert_array_equal(y[center], x[center-offset])
    if offset:
        assert not np.array_equal(y, np.roll(x, offset))
        # Cropping first loses real context at one end of the scored center.
        cropped = x[center]
        wrong = np.zeros_like(cropped)
        if offset > 0: wrong[offset:] = cropped[:-offset]
        else: wrong[:offset] = cropped[-offset:]
        assert not np.array_equal(y[center], wrong)
    else:
        assert not np.shares_memory(y, x)


@pytest.mark.parametrize("offset", [-128, 128, -T.P.SCORE, T.P.SCORE])
def test_impulses_cannot_wrap_and_full_length_shifts_are_zero(offset):
    x = np.zeros(T.P.SCORE)
    x[0], x[-1] = 3., 7.
    y = T.finite_shift(x, offset)
    if abs(offset) == len(x):
        assert not y.any()
    else:
        assert y.sum() == (3. if offset > 0 else 7.)
        assert y[offset if offset > 0 else len(x)-1+offset] == y.sum()


@pytest.mark.parametrize("bad", [True, 2., "2"])
def test_shift_rejects_noninteger_offset(bad):
    with pytest.raises(ValueError):
        T.finite_shift(np.ones(T.P.SCORE), bad)


def test_actual_scorer_primary_and_l1_use_unchanged_center(monkeypatch):
    # Real score_prediction and standardization; mock only expensive spectral work.
    x = np.random.default_rng(23).normal(size=T.P.SCORE)
    target = np.random.default_rng(24).normal(size=T.P.SCORE)
    raw = x*.2
    windows = {n: np.ones(n) for n in T.P.FFTS}  # Synthetic coefficients, no archive access.
    observed = []
    def spectral(a, b, *, windows):
        observed.append((a.copy(), b.copy(), windows))
        return float(np.mean((a-b)**2))
    monkeypatch.setattr(T.P, "mrstft_numpy", spectral)
    shifted = T.finite_shift(x, 128)
    result = T.P.score_prediction(shifted, target, raw, windows=windows)
    p, y = T.P.standardize(x[72000-128:216000-128]), T.P.standardize(target[72000:216000])
    np.testing.assert_array_equal(observed[0][0], p)
    np.testing.assert_array_equal(observed[0][1], y)
    assert observed[0][2] is windows and observed[1][2] is windows
    assert result["canonical_waveform_l1"] == float(np.mean(np.abs(p-y)))
    # Full-waveform filtering stays in the original low-band diagnostic.
    np.testing.assert_array_equal(observed[1][0], T.P.standardize(T.P.bandpass(shifted)[72000:216000]))
    np.testing.assert_array_equal(observed[1][1], T.P.standardize(T.P.bandpass(raw)[72000:216000]))


def test_four_small_gate_wide_diagnostic_only_and_zero_prerequisite():
    r = rows()
    for v in r:
        if v["offset"] not in (*T.SMALL, 0): set_primary(v, "net", 3.)
    result = T.compare(r, panel())
    assert result["disposition"] == "PASS"
    assert len(result["offset_screens"]) == 13
    assert [v["offset"] for v in result["offset_screens"]] == list(T.OFFSETS)
    assert sum(v["role"] == "diagnostic_only" and not v["screen"]["passed"]
               for v in result["offset_screens"]) == 8
    for offset in T.SMALL:
        damaged = deepcopy(r)
        for v in damaged:
            if v["offset"] == offset: set_primary(v, "net", 1.)
        assert T.compare(damaged, panel())["disposition"] == "FAIL"
    for v in r:
        if v["offset"] == 0: set_primary(v, "net", 1.)
    assert T.compare(r, panel())["disposition"] == "INCONCLUSIVE"


def test_unchanged_stronger_gate_boundaries_wins_groups_and_better_simple():
    r = rows()
    for v in r: set_primary(v, "net", .9)
    assert T.compare(r, panel())["passed"]
    for v in r:
        if v["offset"] != 0: set_primary(v, "net", .90001)
    assert T.compare(r, panel())["disposition"] == "FAIL"
    for v in r:
        if v["offset"] != 0: set_primary(v, "net", 1.1)  # Wet advantage alone is insufficient.
    assert T.compare(r, panel())["disposition"] == "FAIL"
    r = rows()
    for v in r:
        if int(v["take"]) < 4 and v["offset"] == -3: set_primary(v, "net", 1.)
    screen = next(s["screen"] for s in T.compare(r, panel())["offset_screens"] if s["offset"] == -3)
    assert screen["strict_wins"] == 8 and not screen["passed"]
    r = rows()
    for v in r:
        if v["content"] == "scales" and v["offset"] == 3: set_primary(v, "net", 1.)
    screen = next(s["screen"] for s in T.compare(r, panel())["offset_screens"] if s["offset"] == 3)
    assert screen["group_medians"]["scales"] == 0. and not screen["passed"]


@pytest.mark.parametrize("damage", ["missing", "duplicate", "extra", "identity", "offset_bool", "invalid",
                                    "nan_diagnostic", "negative_diagnostic", "bad_keys", "scalar",
                                    "qc", "oracle", "zero_simple", "bool_loss"])
def test_inconclusive_has_priority_even_when_small_offset_fails(damage):
    r = rows()
    for v in r:
        if v["offset"] == -2: set_primary(v, "net", 4.)
    v = r[-1]  # Wide offset invalids also make the whole result inconclusive.
    if damage == "missing": r.pop()
    if damage == "duplicate": r[-1] = r[0]
    if damage == "extra": r.append(deepcopy(r[0]))
    if damage == "identity": v["content"] = "chords"
    if damage == "offset_bool": r[72]["offset"] = False
    if damage == "invalid": v["valid"] = False
    if damage == "nan_diagnostic": v["flatref_scores"]["raw_lowband"] = float("nan")
    if damage == "negative_diagnostic": v["network_scores"]["canonical_waveform_l1"] = -1.
    if damage == "bad_keys": v["input_scores"]["extra"] = .2
    if damage == "scalar": v["net"] += 1.
    if damage == "qc": v["qc_valid"] = False
    if damage == "oracle": v["oracle"] = 1e-6
    if damage == "zero_simple": set_primary(v, "flatref", 0.)
    if damage == "bool_loss": set_primary(v, "wet", True)
    result = T.compare(r, panel())
    assert result["disposition"] == "INCONCLUSIVE"
    if damage not in ("missing", "duplicate", "extra", "offset_bool"):
        assert len(result["offset_screens"]) == 13


def test_paired_changes_use_same_fixed_offset_simple_and_zero_denominator_null():
    base, shifted = row(panel()[0]), row(panel()[0], 2)
    set_primary(shifted, "wet", .5)
    set_primary(shifted, "net", .4)
    delta = T.paired_changes(shifted, base)
    assert delta["wet"]["primary_absolute_change"] == -1.5
    assert delta["wet"]["primary_relative_change"] == -.75
    assert delta["advantage"]["primary_absolute_change"] == pytest.approx(-.1)
    assert delta["advantage"]["primary_relative_change"] == pytest.approx(0.)
    for arm in T.ARMS:
        assert delta[arm]["raw_lowband_change"] == 0.
    set_primary(base, "net", 0.)
    assert T.paired_changes(shifted, base)["net"]["primary_relative_change"] is None


def test_manifest_metadata_requires_exact_original36_plus_saved12(tree):
    original, verified, _, _ = metadata(panel(), tree)
    assert T.declared_hashes(panel(), original, verified) == tree
    lines = T.HASHES.read_text().splitlines()
    for broken in (lines[:-1], lines+[lines[0]], lines[:-1]+["0"*64+"  ../escape.npz"],
                   lines[:-1]+["x"*64+"  "+next(iter(tree))]):
        T.HASHES.write_text("\n".join(broken)+"\n")
        with pytest.raises(ValueError): T.declared_hashes(panel(), original, verified)
    T.HASHES.write_text("\n".join(lines)+"\n")
    original["input_artifacts"][next(iter(original["input_artifacts"]))] = "0"*64
    with pytest.raises(ValueError, match="original36"): T.declared_hashes(panel(), original, verified)
    original, verified, _, _ = metadata(panel(), tree)
    verified["primary_artifact_hashes"]["take-11.npz"] = "0"*64
    with pytest.raises(ValueError, match="saved12"): T.declared_hashes(panel(), original, verified)


@pytest.mark.parametrize("damage", ["complete", "screen", "count", "failed_check", "failures", "pins",
                                    "verifier", "wave_identity", "wave_missing", "qc", "oracle",
                                    "prior_qc", "prior_missing", "score", "control_verifier"])
def test_prerequisite_rejects_invalid_metadata_before_assets(tree, damage):
    original, verified, prepare, control = metadata(panel(), tree)
    inherited = {"synthetic": "f"*64}
    verified["source_pins"] = inherited.copy()
    pins = {T.VERIFIER: "a"*64, T.CONTROL_VERIFIER: "b"*64}
    T.prerequisite(original, verified, prepare, control, panel(), inherited, pins)
    if damage == "complete": original["complete"] = False
    if damage == "screen": original["screen"]["strict_wins"] = 11
    if damage == "count": verified["checks"].pop()
    if damage == "failed_check": verified["checks"][-1]["passed"] = False
    if damage == "failures": verified["failures"] = ["failure"]
    if damage == "pins": verified["source_pins"] = {}
    if damage == "verifier": verified["verifier_sha256"] = "0"*64
    if damage == "wave_identity": verified["waveform_comparison"][-1]["byte_identical"] = False
    if damage == "wave_missing": verified["waveform_comparison"].pop()
    if damage == "qc": original["rows"][-1]["qc_valid"] = False
    if damage == "oracle": prepare["rows"][-1]["oracle_scores"]["primary"] = 1e-6
    if damage == "prior_qc": control["preparation"][-1]["qc"]["valid"] = False
    if damage == "prior_missing": control["replay"].pop()
    if damage == "score": verified["independent_rows"][-1]["net"] += .1
    if damage == "control_verifier": control["verifier_sha256"] = "0"*64
    with pytest.raises(ValueError):
        T.prerequisite(original, verified, prepare, control, panel(), inherited, pins)


@pytest.fixture
def guarded(tree, monkeypatch):
    original, verified, prepare, control = metadata(panel(), tree)
    inherited_names = ["docs/di-morgan-control-prepare.json", "docs/di-morgan-control-verification.json"]
    inherited_names += [f"source-{i}" for i in range(41)]
    for name in (*inherited_names, *T.OWN_PINS):
        p = T.ROOT / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists(): p.write_text("synthetic "+name)
    def write(name, value):
        (T.ROOT / name).write_text(json.dumps(value))
    control["verifier_sha256"] = T.digest((T.ROOT / T.CONTROL_VERIFIER).read_bytes())
    write("docs/di-morgan-control-prepare.json", prepare)
    write("docs/di-morgan-control-verification.json", control)
    inherited = {n: T.digest((T.ROOT / n).read_bytes()) for n in inherited_names}
    verified.update(source_pins=inherited, verifier_sha256=T.digest((T.ROOT / T.VERIFIER).read_bytes()))
    write("docs/di-morgan-flatref.json", original)
    write("docs/di-morgan-flatref-provenance.json", {"pins": inherited})
    T.FLAT.mkdir(parents=True)
    for saved, archive in (("result.json", "docs/di-morgan-flatref.json"),
                           ("provenance.json", "docs/di-morgan-flatref-provenance.json")):
        blob = (T.ROOT / archive).read_bytes()
        (T.FLAT / saved).write_bytes(blob)
        verified["primary_artifact_hashes"][saved] = T.digest(blob)
    write("docs/di-morgan-flatref-verification.json", verified)
    (T.ROOT / T.REVIEW).write_text("Fresh synthetic review\nVerdict: APPROVE\n")
    body = "Synthetic scientific body\n"
    approval = {"status": "DECLARED", "fresh_independent_review": True,
                "scope": "common-post-inference-coordinate-only", "design_sha256": T.digest(body.encode())}
    for key, name in (("review_sha256", T.REVIEW), ("source_sha256", "learn/di_timing_sensitivity.py"),
                      ("test_sha256", "tests/test_di_timing_sensitivity.py"),
                      ("inputs_sha256", "docs/di-timing-sensitivity-inputs.sha256")):
        approval[key] = T.digest((T.ROOT / name).read_bytes())
    T.PLAN.write_text("**Declared: synthetic**\n<!-- timing-approval\n"+json.dumps(approval)+
                      "\ntiming-approval -->\n\n## Frozen design\n"+body)
    committed = {n: (T.ROOT / n).read_bytes() for n in (*inherited_names, *T.OWN_PINS)}
    manifest = {"takes": panel(), "attribution": "synthetic"}
    monkeypatch.setattr(T.F, "guard", lambda: ({}, manifest, inherited.copy(), {}))
    def git(args, **kwargs):
        if args == ["git", "rev-parse", "HEAD"]: return "synthetic-revision\n"
        assert args[:2] == ["git", "show"]
        return committed[args[2].removeprefix("HEAD:")]
    monkeypatch.setattr(T.subprocess, "check_output", git)
    return committed


def test_draft_stops_before_inherited_guard_hashing_or_loading(tree, monkeypatch):
    T.PLAN.write_text("DRAFT")
    monkeypatch.setattr(T.F, "guard", lambda: pytest.fail("inherited guard reached"))
    monkeypatch.setattr(T.R, "sha", lambda *a: pytest.fail("asset hashing reached"))
    monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("array load reached"))
    with pytest.raises(ValueError, match="fresh independent review"): T.guard()


def test_declared_guard_uses_metadata_only_and_rechecks_sources(guarded, monkeypatch):
    monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("array load during guard"))
    monkeypatch.setattr(T.R, "sha", lambda *a: pytest.fail("asset hash during guard"))
    context = T.guard()
    assert len(context[2]) == 43+len(T.OWN_PINS) and len(context[-1]) == 48
    T.recheck_sources(context[2], context[3], time.monotonic())
    (T.ROOT / "learn/di_timing_sensitivity.py").write_text("changed")
    with pytest.raises(ValueError, match="drift"): T.recheck_sources(context[2], context[3], time.monotonic())


@pytest.mark.parametrize("damage", ["uncommitted", "review_hash", "test_hash", "source_hash", "body",
                                    "input_hash", "review_verdict", "result_bytes", "provenance_bytes",
                                    "provenance_pins", "inherited_count"])
def test_guard_refuses_unreviewed_uncommitted_or_changed_prerequisites(guarded, monkeypatch, damage):
    def edit_approval(key):
        T.PLAN.write_text(T.PLAN.read_text().replace('"'+key+'": "', '"'+key+'": "0'))
        guarded["docs/di-timing-sensitivity-plan.md"] = T.PLAN.read_bytes()
    if damage == "uncommitted": (T.ROOT / "learn/di_timing_sensitivity.py").write_text("changed")
    if damage in ("review_hash", "test_hash", "source_hash", "input_hash"):
        edit_approval({"review_hash": "review_sha256", "test_hash": "test_sha256",
                       "source_hash": "source_sha256", "input_hash": "inputs_sha256"}[damage])
    if damage == "body":
        T.PLAN.write_text(T.PLAN.read_text()+"changed body")
        guarded["docs/di-timing-sensitivity-plan.md"] = T.PLAN.read_bytes()
    if damage == "review_verdict":
        (T.ROOT / T.REVIEW).write_text("Verdict: REJECT")
        guarded[T.REVIEW] = (T.ROOT / T.REVIEW).read_bytes()
    if damage == "result_bytes": (T.FLAT / "result.json").write_text("changed")
    if damage == "provenance_bytes": (T.FLAT / "provenance.json").write_text("changed")
    if damage == "provenance_pins":
        p = T.ROOT / "docs/di-morgan-flatref-provenance.json"
        p.write_text(json.dumps({"pins": {}}))
        (T.FLAT / "provenance.json").write_bytes(p.read_bytes())
        guarded["docs/di-morgan-flatref-provenance.json"] = p.read_bytes()
        v = T.ROOT / "docs/di-morgan-flatref-verification.json"
        obj = json.loads(v.read_text())
        obj["primary_artifact_hashes"]["provenance.json"] = T.digest(p.read_bytes())
        v.write_text(json.dumps(obj))
        guarded["docs/di-morgan-flatref-verification.json"] = v.read_bytes()
    if damage == "inherited_count":
        monkeypatch.setattr(T.F, "guard", lambda: ({}, {}, {}, {}))
    with pytest.raises(ValueError): T.guard()


@pytest.fixture
def synthetic_inputs(tree):
    x = np.linspace(-.4, .5, T.P.SCORE)
    for t in panel():
        slug = t["slug"]
        for path, values in (
            (T.SOURCE / "prepare" / f"{slug}.npz", {"di": x, "target": x+1, "render_di": x}),
            (T.SOURCE / "render" / f"{slug}.npz", {"baseline": x+2, "net_input": x}),
            (T.SOURCE / "infer" / f"{slug}.npz", {"prediction": (x+3).astype(np.float32)}),
            (T.FLAT / f"{slug}.npz", {"flatref": x+4}),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            np.savez(path, **values)
    hashes = {str(p.relative_to(T.ROOT)): T.R.sha(p) for p in paths(panel())}
    original, verified, _, control = metadata(panel(), hashes)
    for p in control["preparation"]: p["target_sha256"] = T.wave_hash(x+1, "<f8")
    for p in control["replay"]: p["prediction_sha256_float32"] = T.wave_hash((x+3).astype(np.float32), "<f4")
    for w in verified["waveform_comparison"]: w["primary_sha256_float64"] = T.wave_hash(x+4, "<f8")
    return hashes, original, verified, control


def test_all48_hash_barrier_preload_recheck_and_member_restriction(synthetic_inputs, monkeypatch):
    hashes, _, verified, control = synthetic_inputs
    original_sha, original_load, hashed, loads, members = T.R.sha, np.load, [], [], []
    def sha(path):
        hashed.append(str(Path(path).relative_to(T.ROOT)))
        return original_sha(path)
    class Restricted:
        def __init__(self, path): self.path, self.saved = path, original_load(path, allow_pickle=False)
        def __enter__(self): return self
        def __exit__(self, *args): self.saved.close()
        def __getitem__(self, member):
            allowed = {"prepare": {"di", "target"}, "render": {"baseline"}, "infer": {"prediction"}}
            assert member in allowed.get(self.path.parent.name, {"flatref"})
            members.append(member)
            return self.saved[member]
    def load(path, *, allow_pickle):
        assert allow_pickle is False
        assert set(hashed[:48]) == set(hashes) and len(hashed) >= 49
        assert hashed[-1] == str(path.relative_to(T.ROOT))
        loads.append(path)
        return Restricted(path)
    monkeypatch.setattr(T.R, "sha", sha)
    monkeypatch.setattr(np, "load", load)
    loaded, identities = T.load_inputs(panel(), hashes, verified, control, time.monotonic())
    assert len(loads) == 48 and len(hashed) == 144 and len(members) == 60
    assert len(identities) == 12 and all(len(v) == 5 for v in identities.values())
    assert all(not x.flags.writeable for v in loaded.values() for x in v.values())


@pytest.mark.parametrize("damage", ["last_hash", "symlink", "target_identity", "net_identity", "flat_identity", "between_hash_load"])
def test_input_drift_and_identity_refusals(synthetic_inputs, monkeypatch, damage):
    hashes, _, verified, control = synthetic_inputs
    last = T.ROOT / list(hashes)[-1]
    if damage == "last_hash": last.write_bytes(b"changed")
    if damage == "symlink":
        copy = last.with_suffix(".copy")
        copy.write_bytes(last.read_bytes())
        last.unlink()
        last.symlink_to(copy)
    if damage == "target_identity": control["preparation"][-1]["target_sha256"] = "0"*64
    if damage == "net_identity": control["replay"][-1]["prediction_sha256_float32"] = "0"*64
    if damage == "flat_identity": verified["waveform_comparison"][-1]["primary_sha256_float64"] = "0"*64
    if damage == "between_hash_load":
        original_sha, count = T.R.sha, []
        def sha(path):
            count.append(path)
            if len(count) == 49: return "0"*64
            return original_sha(path)
        monkeypatch.setattr(T.R, "sha", sha)
    if damage in ("last_hash", "symlink", "between_hash_load"):
        monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("load before all48 checks passed"))
    with pytest.raises(ValueError):
        T.load_inputs(panel(), hashes, verified, control, time.monotonic())


@pytest.fixture
def pipeline(tree, monkeypatch):
    original, verified, _, control = metadata(panel(), tree)
    # Real shifts on short synthetic buffers only; full-size shifts tested above.
    x = np.linspace(-.4, .5, 600)
    loaded = {t["slug"]: {"di": x, "target": x+1, "wet": x+2, "net": x+3, "flatref": x+4}
              for t in panel()}
    monkeypatch.setattr(T.P, "SCORE", 600)
    monkeypatch.setattr(T, "recheck_sources", lambda *a: None)
    monkeypatch.setattr(T, "check_artifacts", lambda *a: None)
    windows = {4: np.ones(4)}
    monkeypatch.setattr(T.V, "load_windows", lambda *a: windows)
    monkeypatch.setattr(T, "load_inputs", lambda *a: (loaded, {"synthetic": "identity"}))
    monkeypatch.setattr(T.R, "progress", lambda out, value: append_progress(out, value))
    out = T.ROOT / "output"
    out.mkdir()
    context = ({}, {"takes": panel(), "attribution": "synthetic"}, {}, "revision",
               original, verified, control, tree)
    return out, context, loaded, windows


def append_progress(out, value):
    with (out / "progress.jsonl").open("a") as f: f.write(json.dumps(value)+"\n")


@pytest.mark.parametrize("mismatch", [False, True])
def test_complete108_barrier_common_shift_fixed_targets_and_no_zero_rescore(pipeline, monkeypatch, mismatch):
    out, context, loaded, windows = pipeline
    calls, shifted = [], []
    original_shift = T.finite_shift
    def shift(x, offset):
        replay = json.loads((out / "baseline-replay.json").read_text())
        assert replay["complete"] and replay["passed"] and replay["scalar_count"] == 108
        assert len(calls) >= 36 and offset != 0
        shifted.append(offset)
        return original_shift(x, offset)
    def scoring(wave, target, raw, *, windows):
        assert windows is pipeline[3]
        index = len(calls)
        if index < 36:
            take_index, arm_index = divmod(index, 3)
            saved = loaded[panel()[take_index]["slug"]]
            assert wave is saved[list(T.ARMS)[arm_index]]
        else:
            shifted_index = index-36
            offset_index, within = divmod(shifted_index, 36)
            take_index, arm_index = divmod(within, 3)
            offset = [v for v in T.OFFSETS if v][offset_index]
            saved = loaded[panel()[take_index]["slug"]]
            source = saved[list(T.ARMS)[arm_index]]
            n = np.arange(len(source))-offset
            expected = np.zeros_like(source)
            valid = (n >= 0) & (n < len(source))
            expected[valid] = source[n[valid]]
            np.testing.assert_array_equal(wave, expected)
        assert target is saved["target"] and raw is saved["di"]
        calls.append((take_index, arm_index))
        return score([2., .8, 1.][arm_index])
    monkeypatch.setattr(T, "finite_shift", shift)
    monkeypatch.setattr(T.P, "score_prediction", scoring)
    if mismatch:
        context[4]["rows"][-1]["flatref_scores"]["raw_lowband"] += .01
        with pytest.raises(ValueError, match="original108"): T.run(out, context, time.monotonic())
        assert len(calls) == 36 and not shifted
        replay = json.loads((out / "baseline-replay.json").read_text())
        assert replay["complete"] and not replay["passed"] and replay["scalar_count"] == 108
        assert len(replay["rows"]) == 12
        assert not (out / "result.json").exists()
    else:
        T.run(out, context, time.monotonic())
        assert len(calls) == 468 and len(shifted) == 432
        result = json.loads((out / "result.json").read_text())
        progress = [json.loads(line) for line in (out / "progress.jsonl").read_text().splitlines()]
        assert result["rows"] == progress and len(progress) == 156
        assert result["screen"]["disposition"] == "PASS"
        assert all("changes_from_zero" in r for r in progress)
        assert all(all(r["changes_from_zero"][a]["primary_absolute_change"] == 0. for a in T.ARMS)
                   for r in progress if r["offset"] == 0)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.])
def test_bad_baseline_diagnostic_saves_failed_replay_and_never_shifts(pipeline, monkeypatch, bad):
    out, context, _, _ = pipeline
    count = []
    def scoring(*a, **k):
        i = len(count)
        count.append(i)
        s = score([2., .8, 1.][i % 3])
        if i == 35: s["raw_lowband"] = bad
        return s
    monkeypatch.setattr(T.P, "score_prediction", scoring)
    monkeypatch.setattr(T, "finite_shift", lambda *a: pytest.fail("shift after invalid baseline"))
    with pytest.raises(ValueError, match="original108"): T.run(out, context, time.monotonic())
    replay = json.loads((out / "baseline-replay.json").read_text())
    assert len(count) == 36 and len(replay["rows"]) == 12 and not replay["passed"]
    assert replay["rows"][-1]["valid"] is False and "error" in replay["rows"][-1]


def test_nonzero_invalid_diagnostic_retains_all_rows_and_thirteen_screens(pipeline, monkeypatch):
    out, context, _, _ = pipeline
    count = []
    def scoring(*a, **k):
        i = len(count)
        count.append(i)
        s = score([2., .8, 1.][i % 3])
        if i == 40: s["raw_lowband"] = float("nan")
        return s
    monkeypatch.setattr(T.P, "score_prediction", scoring)
    T.run(out, context, time.monotonic())
    result = json.loads((out / "result.json").read_text())
    assert len(count) == 468 and len(result["rows"]) == 156
    assert result["screen"]["disposition"] == "INCONCLUSIVE"
    assert len(result["screen"]["offset_screens"]) == 13
    bad = [r for r in result["rows"] if not r["valid"]]
    assert len(bad) == 1 and bad[0]["nonfinite_diagnostic_fields"]


@pytest.mark.parametrize("damage", ["reuse", "alias", "other", "symlink"])
def test_output_exclusive_fixed_path_refuses_aliases(tree, damage):
    expected = T.ROOT / T.OUTPUT
    requested = expected
    if damage == "reuse": expected.mkdir(parents=True)
    if damage == "alias": requested = expected.parent / "other" / ".." / expected.name
    if damage == "other": requested = expected.with_name("other")
    if damage == "symlink":
        target = T.ROOT / "elsewhere"
        target.mkdir()
        expected.parent.mkdir(parents=True)
        expected.symlink_to(target, target_is_directory=True)
    with pytest.raises((ValueError, FileExistsError)): T.output_directory(requested)


@pytest.mark.parametrize("mode", ["timeout", "drift"])
def test_main_retains_provenance_replay_progress_and_failure(pipeline, monkeypatch, mode):
    out, context, _, _ = pipeline
    monkeypatch.setattr(T.sys, "prefix", str(T.ROOT / ".venv"))
    monkeypatch.setattr(T, "guard", lambda: context)
    monkeypatch.setattr(T, "output_directory", lambda *a: out)
    calls = []
    def scoring(*a, **k):
        i = len(calls)
        calls.append(i)
        return score([2., .8, 1.][i % 3])
    monkeypatch.setattr(T.P, "score_prediction", scoring)
    real_check = T.R.check_time
    def budget(start):
        if len(calls) >= 42: real_check(time.monotonic()-T.R.LIMIT-1)
    if mode == "timeout": monkeypatch.setattr(T.R, "check_time", budget)
    else:
        checks = []
        def drift(*a):
            checks.append(1)
            if len(checks) == 3: raise ValueError("source drift")
        monkeypatch.setattr(T, "recheck_sources", drift)
    with pytest.raises(TimeoutError if mode == "timeout" else ValueError):
        T.main(["--out", T.OUTPUT])
    failure = json.loads((out / "failure.json").read_text())
    assert failure["disposition"] == "INCONCLUSIVE" and failure["elapsed_seconds"] >= 0
    assert (out / "provenance.json").exists() and (out / "inputs.json").exists()
    assert json.loads((out / "baseline-replay.json").read_text())["passed"]
    assert (out / "progress.jsonl").exists() and not (out / "result.json").exists()


def test_main_prefix_and_cli_refusal_before_guard_or_output(tree, monkeypatch):
    monkeypatch.setattr(T, "guard", lambda: pytest.fail("guard reached"))
    monkeypatch.setattr(T, "output_directory", lambda *a: pytest.fail("output reached"))
    monkeypatch.setattr(T.sys, "prefix", str(T.ROOT / "wrong"))
    with pytest.raises(ValueError, match="helper"): T.main(["--out", T.OUTPUT])
    with pytest.raises(SystemExit): T.main(["--ou", T.OUTPUT])
    with pytest.raises(SystemExit): T.main(["--out", T.OUTPUT, "--offset", "2"])
