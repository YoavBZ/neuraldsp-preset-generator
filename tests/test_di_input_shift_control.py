"""Synthetic only: no real arrays, weights, audio, catalogs or study execution."""
import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")

from copy import deepcopy
import builtins
import importlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import numpy as np
import pytest

from learn import di_input_shift_control as U

T, P, R = U.T, U.P, U.R


def takes():
    return [{"slug": f"synthetic-{i}", "take": str(i),
             "content": "chords" if i < 6 else "scales"} for i in range(12)]


def scores(v):
    return dict(primary=v, canonical_waveform_l1=v/2, raw_lowband=v/3)


def row(take, offset=0, net=.8):
    return {**take, "offset": offset, "valid": True, "qc_valid": True, "oracle": 0.,
            "wet": 2., "flatref": 1., "net": net, "input_scores": scores(2.),
            "flatref_scores": scores(1.), "network_scores": scores(net)}


def rows(offsets=U.OFFSETS):
    return [row(t, o) for o in offsets for t in takes()]


def set_net(r, value):
    r["net"] = r["network_scores"]["primary"] = value


def read(path):
    return json.loads(path.read_text())


@pytest.fixture
def tree(tmp_path, monkeypatch):
    monkeypatch.setattr(U, "ROOT", tmp_path)
    monkeypatch.setattr(U, "PLAN", tmp_path / "docs/di-input-shift-control-plan.md")
    monkeypatch.setattr(T, "ROOT", tmp_path)
    monkeypatch.setattr(T, "SOURCE", tmp_path / "tmp/di-morgan-control-20261008")
    monkeypatch.setattr(T, "FLAT", tmp_path / "tmp/di-morgan-flatref-20261008")
    return tmp_path


def prior_bundle(inherited, hashes, identities):
    prior_rows = rows(T.OFFSETS)
    for r in prior_rows:
        r["changes_from_zero"] = T.paired_changes(r, row({k: r[k] for k in ("slug", "content", "take")}))
    result = {"complete": True, "rows": prior_rows, "screen": T.compare(prior_rows, takes()),
              "input_artifacts": hashes}
    zero = [row(t) for t in takes()]
    replay = {"complete": True, "passed": True, "scalar_count": 108, "absolute_tolerance": T.TOL,
              "rows": [{**t, "valid": True, "errors": {f"{a}.{m}": 0. for a in T.ARMS for m in T.METRICS},
                        "scores": {key: r[key] for key in T.ARMS.values()}} for t, r in zip(takes(), zero)],
              "screen": U.F.compare(zero, takes())}
    inputs = {"artifacts": hashes, "waveforms": identities}
    prov = {"pins": inherited, "input_artifacts": hashes}
    verified = {"status": "VERIFIED", "scientific_disposition": "PASS", "failures": [],
        "checks": [{"passed": True} for _ in range(23734)], "source_pins": inherited,
        "verifier_sha256": "a"*64, "independent_rows": deepcopy(prior_rows),
        "independent_screen": deepcopy(result["screen"]), "input_artifacts": hashes, "inputs": inputs,
        "independent_baseline_replay": deepcopy(replay),
        "derivation_payload": {"rows": deepcopy(prior_rows), "screen": deepcopy(result["screen"]),
                               "baseline": deepcopy(replay)}}
    return result, verified, prov, inputs, replay


@pytest.mark.parametrize("offset", U.OFFSETS)
def test_true_finite_delay_inverse_center_no_wrap(offset):
    x = np.arange(P.SCORE, dtype=np.float64)+1
    shifted = T.finite_shift(x, offset)
    indices = np.arange(len(x))-offset
    valid = (indices >= 0) & (indices < len(x))
    np.testing.assert_array_equal(shifted[valid], x[indices[valid]])
    assert not shifted[~valid].any()
    inverse = T.finite_shift(shifted, -offset)
    np.testing.assert_array_equal(inverse[72000:216000], x[72000:216000])
    if offset:
        assert not np.array_equal(shifted, np.roll(x, offset))
        lost = slice(0, abs(offset)) if offset < 0 else slice(-offset, None)
        assert not inverse[lost].any()  # Inverse restores center, never invents lost edges.
    np.testing.assert_array_equal(x, np.arange(P.SCORE)+1)


def test_import_has_no_torch_or_artifact_access(monkeypatch):
    imported = []
    real_import = builtins.__import__
    def importing(name, *a, **k):
        imported.append(name)
        assert name != "torch"
        return real_import(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", importing)
    monkeypatch.setattr(Path, "read_bytes", lambda *a: pytest.fail("import read bytes"))
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("import read text"))
    importlib.reload(U)
    assert "torch" not in imported


@pytest.mark.parametrize("offset", U.SMALL)
def test_float32_known_inverse_preserves_sample_bytes_and_padding(tmp_path, monkeypatch, offset):
    monkeypatch.setattr(P, "SCORE", 32)
    raw = np.resize(np.array([-.0, .0, np.nextafter(np.float32(0), np.float32(1)),
                              np.nextafter(np.float32(1), np.float32(2)), -.125, 123456.75], dtype="<f4"), 32)
    before = raw.tobytes()
    returned, corrected, evidence, error = U.prediction_evidence(
        tmp_path, takes()[0], offset, raw, raw, raw, time.monotonic())
    U.validate_prediction(returned, corrected, error)
    assert returned.dtype == corrected.dtype == np.dtype("<f4")
    indices = np.arange(len(raw))+offset
    valid = (indices >= 0) & (indices < len(raw))
    assert corrected[valid].tobytes() == raw[indices[valid]].tobytes()
    assert corrected[~valid].tobytes() == np.zeros(np.count_nonzero(~valid), dtype="<f4").tobytes()
    assert raw.tobytes() == before
    with np.load(tmp_path/evidence["prediction_file"], allow_pickle=False) as saved:
        assert saved["raw_prediction"].tobytes() == before
        assert saved["corrected_prediction"].dtype == np.dtype("<f4")
        assert saved["corrected_prediction"].tobytes() == corrected.tobytes()
    assert evidence["corrected_prediction_sha256"] == T.digest(corrected.tobytes())


def test_original_rebuild_full_input_before_normalization_optional_torch(tmp_path):
    torch = pytest.importorskip("torch")
    from learn import direc as D
    class Synthetic(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.seen = []
        def forward(self, x):
            self.seen.append(x.detach().cpu().numpy().copy())
            return x * .75 + .02
    # Large edge terms make finite-padding std effects measurable without real data.
    x = np.linspace(-.2, .3, P.SCORE, dtype=np.float64)
    x[-3:] = 5.
    shifted = T.finite_shift(x, 3)
    net = Synthetic().cpu().eval()
    predicted = U.infer(net, shifted, time.monotonic())
    f32 = shifted.astype("<f4")
    sc = f32.std()+1e-9
    np.testing.assert_array_equal(net.seen[0][0, 0], f32/sc*.1)
    assert net.seen[0].shape == (1, 1, P.SCORE)
    assert predicted.dtype == np.dtype("<f4")
    expected = (torch.tensor(f32/sc*.1)*.75+.02).numpy()/.1*sc
    np.testing.assert_array_equal(predicted, expected)
    wrong = T.finite_shift((x.astype("<f4")/(x.astype("<f4").std()+1e-9)*.1), 3)
    assert not np.array_equal(net.seen[0][0, 0], wrong)
    assert D.rebuild.__module__ == "learn.direc"


def test_infer_boundary_full_raw_level_and_original_float32_conversion(monkeypatch):
    from learn import direc as D
    fake_torch = SimpleNamespace(device=lambda name: name)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    x = np.linspace(-.27, .83, P.SCORE, dtype="<f4")
    x[-3:] = 17.
    shifted = T.finite_shift(x, 3).astype(x.dtype)
    called = []
    def network(net, full, *, device):
        assert net == "synthetic-network" and device == "cpu"
        assert full.dtype == np.dtype("<f4") and len(full) == P.SCORE
        assert full.tobytes() == shifted.tobytes()
        assert full.std() != x.std()  # Full finite padding is before rebuild's std.
        assert full.max() > .1       # Caller has not normalized or center-cropped it.
        called.append(1)
        return full.copy()
    monkeypatch.setattr(D, "rebuild", network)
    result = U.infer("synthetic-network", shifted, time.monotonic())
    assert called == [1] and result.tobytes() == shifted.tobytes()


@pytest.mark.parametrize("damage", [None, "threads", "device", "training"])
def test_model_loader_cpu_eval_weights_only_hash_before_load(monkeypatch, damage):
    from learn import direc as D
    events = []
    class Net:
        training = True
        def cpu(self): events.append("cpu"); return self
        def load_state_dict(self, state): assert state == "synthetic-state"; events.append("state")
        def eval(self): self.training = damage == "training"; events.append("eval"); return self
        def parameters(self): return [SimpleNamespace(device=SimpleNamespace(type="other" if damage == "device" else "cpu"))]
    def hash_check(*a): events.append("hash")
    def set_threads(n): assert n == 2; events.append("threads")
    def load(path, **kwargs):
        assert path == U.MODEL_PATH and kwargs == {"map_location": "cpu", "weights_only": True}
        assert events[-1] == "hash"
        events.append("load")
        return "synthetic-state"
    fake_torch = SimpleNamespace(set_num_threads=set_threads, get_num_threads=lambda: 1 if damage == "threads" else 2, load=load)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setattr(D, "build_model", Net)
    monkeypatch.setattr(U, "check_model", hash_check)
    if damage is None:
        assert not U.load_model({}, time.monotonic()).training
        assert events == ["hash", "threads", "cpu", "hash", "load", "state", "eval"]
    else:
        with pytest.raises(ValueError, match="CPU eval"): U.load_model({}, time.monotonic())


def test_original_scorer_fixed_center_and_known_inverse_keeps_unimposed_error(tmp_path):
    # No target fitting: a synthetic extra seven-sample error must remain after
    # correcting ONLY the imposed +3. Exercise the real scorer with synthetic windows.
    x = np.random.default_rng(19).normal(0, .05, P.SCORE).astype("<f4")
    raw = T.finite_shift(x, 10).astype("<f4")
    _, corrected, _, error = U.prediction_evidence(tmp_path, takes()[0], 3, x, raw, x, time.monotonic())
    assert error is None
    center = slice(72000, 216000)
    np.testing.assert_array_equal(corrected[center], x[71993:215993])
    assert not np.array_equal(corrected[center], x[center])
    windows = {n: np.hanning(n).astype("<f4") for n in P.FFTS}
    oracle = P.score_prediction(x, x, x, windows=windows)
    actual = P.score_prediction(corrected, x, x, windows=windows)
    assert oracle["primary"] < 1e-6
    assert actual["canonical_waveform_l1"] > oracle["canonical_waveform_l1"] + .05
    assert set(actual) == set(T.METRICS)


@pytest.mark.parametrize("damage", [None, "status", "disposition", "failures", "check_count", "check_fail",
    "pins", "verifier", "missing_row", "last_score", "last_change", "screen", "payload", "replay",
    "replay_nonfinite", "inputs", "artifacts", "prov"])
def test_prior_T_complete_metadata_23734_and_all156(damage):
    inherited = {f"pin-{i}": str(i) for i in range(53)}
    result, verified, prov, inputs, replay = prior_bundle(inherited, {"synthetic": "hash"}, {})
    if damage == "status": verified["status"] = "RUNNING"
    if damage == "disposition": verified["scientific_disposition"] = "FAIL"
    if damage == "failures": verified["failures"] = ["x"]
    if damage == "check_count": verified["checks"].pop()
    if damage == "check_fail": verified["checks"][-1]["passed"] = False
    if damage == "pins": verified["source_pins"] = {}
    if damage == "verifier": verified["verifier_sha256"] = "b"*64
    if damage == "missing_row": result["rows"].pop()
    if damage == "last_score": result["rows"][-1]["network_scores"]["raw_lowband"] += 2e-8
    if damage == "last_change": result["rows"][-1]["changes_from_zero"]["net"]["primary_absolute_change"] += 2e-8
    if damage == "screen": result["screen"]["passed"] = False
    if damage == "payload": verified["derivation_payload"]["rows"][-1]["net"] += .1
    if damage == "replay": replay["rows"][-1]["errors"]["net.primary"] = 2e-8
    if damage == "replay_nonfinite": replay["rows"][-1]["errors"]["net.primary"] = float("nan")
    if damage == "inputs": inputs = {"artifacts": {}}
    if damage == "artifacts": result["input_artifacts"] = {}
    if damage == "prov": prov = {"pins": {}}
    args = result, verified, prov, inputs, replay, inherited, {"synthetic": "hash"}, takes(), "a"*64
    if damage is None:
        U.prior_metadata(*args)
    else:
        with pytest.raises(ValueError): U.prior_metadata(*args)


@pytest.fixture
def guarded(tree, monkeypatch):
    names = ["docs/di-timing-sensitivity-inputs.sha256", *[f"source-{i}" for i in range(52)]]
    for name in (*names, *U.OWN_PINS):
        p = tree / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("synthetic "+name)
    inherited = {n: T.digest((tree/n).read_bytes()) for n in names}
    hashes = {f"synthetic-{i}.npz": "b"*64 for i in range(48)}
    result, verified, prov, inputs, replay = prior_bundle(inherited, hashes, {})
    blobs = {"result.json": result, "provenance.json": prov, "inputs.json": inputs, "baseline-replay.json": replay}
    primary = tree / T.OUTPUT
    primary.mkdir(parents=True)
    for name, archive in U.ARCHIVES.items():
        data = json.dumps(blobs[name]).encode()
        (tree/archive).write_bytes(data)
        (primary/name).write_bytes(data)
    progress = "".join(json.dumps(r)+"\n" for r in result["rows"])
    (primary/"progress.jsonl").write_text(progress)
    (tree/(T.OUTPUT+".log")).write_text(progress)
    paths = [primary/n for n in (*U.ARCHIVES, "progress.jsonl")] + [tree/(T.OUTPUT+".log")]
    verified["primary_artifact_snapshots"] = {str(p.relative_to(tree)): {
        "sha256": T.digest(p.read_bytes()), "size": p.stat().st_size} for p in paths}
    verified["verifier_sha256"] = T.digest((tree/U.VERIFIER).read_bytes())
    (tree/U.VERIFICATION).write_text(json.dumps(verified))
    (tree/U.REVIEW).write_text("Fresh synthetic independent review\nVerdict: APPROVE\n")
    body = "Synthetic frozen design\n"
    approval = {"status": "DECLARED", "fresh_independent_review": True, "scope": U.SCOPE,
                "design_sha256": T.digest(body.encode()), "inputs_sha256": inherited[names[0]]}
    for key, name in (("review_sha256", U.REVIEW), ("source_sha256", U.OWN_PINS[0]),
                      ("test_sha256", U.OWN_PINS[1])):
        approval[key] = T.digest((tree/name).read_bytes())
    U.PLAN.write_text("**Declared: synthetic**\n<!-- input-shift-approval\n"+json.dumps(approval)+
                      "\ninput-shift-approval -->\n\n## Frozen design\n"+body)
    committed = {n: (tree/n).read_bytes() for n in (*names, *U.OWN_PINS)}
    def git(args, **kw):
        if args == ["git", "rev-parse", "HEAD"]: return "revision\n"
        assert args[:2] == ["git", "show"]
        return committed[args[2].removeprefix("HEAD:")]
    monkeypatch.setattr(T.subprocess, "check_output", git)
    manifest = {"takes": takes(), "attribution": "synthetic", "model": {"path": U.MODEL_PATH, "sha256": U.MODEL_SHA}}
    context = ({}, manifest, inherited, "revision", {}, {}, {}, hashes)
    monkeypatch.setattr(T, "guard", lambda: context)
    return committed, context


def test_guard_is_metadata_only_committed_and_rechecks_drift(guarded, monkeypatch):
    monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("array load in guard"))
    monkeypatch.setattr(R, "sha", lambda *a: pytest.fail("asset hashing in guard"))
    context = U.guard(time.monotonic())
    assert len(context[2]) == 53+len(U.OWN_PINS) and len(context[7]) == 48
    (U.ROOT/U.OWN_PINS[0]).write_text("drift")
    with pytest.raises(ValueError, match="drift"): U.recheck_sources(context[2], context[3], time.monotonic())


def test_recheck_refuses_HEAD_change_and_budget_includes_guard(guarded, monkeypatch):
    context = U.guard(time.monotonic())
    monkeypatch.setattr(T.subprocess, "check_output", lambda *a, **k: "different-revision\n")
    with pytest.raises(ValueError, match="HEAD changed"): U.recheck_sources(context[2], context[3], time.monotonic())
    with pytest.raises(TimeoutError): U.guard(time.monotonic()-R.LIMIT-1)


@pytest.mark.parametrize("damage", ["draft", "uncommitted", "review", "source", "test", "design", "input",
                                    "verdict", "result_bytes", "progress_bytes", "input_bytes", "pin_count", "model"])
def test_guard_refusals(guarded, monkeypatch, damage):
    committed, context = guarded
    if damage == "draft":
        U.PLAN.write_text("DRAFT")
        monkeypatch.setattr(T, "guard", lambda: pytest.fail("inherited guard on DRAFT"))
    if damage == "uncommitted": (U.ROOT/U.OWN_PINS[1]).write_text("change")
    if damage in ("review", "source", "test", "design", "input"):
        key = {"review": "review_sha256", "source": "source_sha256", "test": "test_sha256",
               "design": "design_sha256", "input": "inputs_sha256"}[damage]
        U.PLAN.write_text(U.PLAN.read_text().replace('"'+key+'": "', '"'+key+'": "0'))
        committed[U.OWN_PINS[2]] = U.PLAN.read_bytes()
    if damage == "verdict":
        p = U.ROOT/U.REVIEW
        p.write_text("Verdict: REJECT")
        committed[U.REVIEW] = p.read_bytes()
        # Keep review hash consistent so the verdict is independently exercised.
        text = U.PLAN.read_text()
        old = json.loads(text.split("<!-- input-shift-approval\n")[1].split("\ninput-shift-approval")[0])
        newer = dict(old, review_sha256=T.digest(p.read_bytes()))
        U.PLAN.write_text(text.replace(json.dumps(old), json.dumps(newer)))
        committed[U.OWN_PINS[2]] = U.PLAN.read_bytes()
    if damage in ("result_bytes", "progress_bytes", "input_bytes"):
        name = {"result_bytes": "result.json", "progress_bytes": "progress.jsonl", "input_bytes": "inputs.json"}[damage]
        (U.ROOT/T.OUTPUT/name).write_bytes(b"drift")
    if damage == "pin_count": context[2].pop("source-51")
    if damage == "model": context[1]["model"] = {"path": "other", "sha256": "0"*64}
    with pytest.raises(ValueError): U.guard(time.monotonic())


@pytest.fixture
def synthetic_inputs(tree, monkeypatch):
    monkeypatch.setattr(P, "SCORE", 600)
    x = np.linspace(-.4, .5, P.SCORE+52, dtype=np.float64)
    identities, hashes, prepared, predicted, waves = {}, {}, [], [], []
    for t in takes():
        slug = t["slug"]
        arrays = {"di": x[:600]*.2, "target": x[:600]+1, "wet": x[52:],
                  "net": (x[:600]*.8).astype("<f4"), "flatref": x[:600]+2}
        identities[slug] = {k: U.array_identity(v) for k, v in arrays.items()}
        prepared.append({**t, "target_sha256": T.wave_hash(arrays["target"], "<f8")})
        predicted.append({**t, "prediction_sha256_float32": T.wave_hash(arrays["net"], "<f4")})
        waves.append({"slug": slug, "primary_sha256_float64": T.wave_hash(arrays["flatref"], "<f8")})
        for path, values in (
            (T.SOURCE/"prepare"/f"{slug}.npz", {"di": arrays["di"], "target": arrays["target"], "render_di": x}),
            (T.SOURCE/"render"/f"{slug}.npz", {"baseline": arrays["wet"], "net_input": x[:600], "forbidden": x}),
            (T.SOURCE/"infer"/f"{slug}.npz", {"prediction": arrays["net"]}),
            (T.FLAT/f"{slug}.npz", {"flatref": arrays["flatref"]}),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            np.savez(path, **values)
            hashes[str(path.relative_to(tree))] = R.sha(path)
    return hashes, {"waveform_comparison": waves}, {"preparation": prepared, "replay": predicted}, {
        "artifacts": hashes, "waveforms": identities}


def test_all48_barriers_six_member_allowlist_and_exact52_overlap(synthetic_inputs, monkeypatch):
    hashes, verified, control, old_inputs = synthetic_inputs
    real_sha, real_load, hashed, loaded_members = R.sha, np.load, [], []
    def sha(path):
        hashed.append(str(path.relative_to(U.ROOT)))
        return real_sha(path)
    class Restricted:
        def __init__(self, path): self.path, self.saved = path, real_load(path, allow_pickle=False)
        def __enter__(self): return self
        def __exit__(self, *a): self.saved.close()
        def __getitem__(self, member):
            allowed = {"prepare": {"di", "target"}, "render": {"baseline", "net_input"}, "infer": {"prediction"}}
            assert member in allowed.get(self.path.parent.name, {"flatref"})
            loaded_members.append(member)
            return self.saved[member]
    def load(path, *, allow_pickle):
        assert allow_pickle is False
        assert set(hashed[:48]) == set(hashes)
        assert hashed[-1] == str(path.relative_to(U.ROOT))
        return Restricted(path)
    monkeypatch.setattr(R, "sha", sha)
    monkeypatch.setattr(np, "load", load)
    loaded, identities = U.load_inputs(takes(), hashes, verified, control, old_inputs, time.monotonic())
    assert len(loaded_members) == 72 and set(loaded_members) == {"di", "target", "baseline", "prediction", "flatref", "net_input"}
    assert len(identities) == 12 and all(len(v) == 6 for v in identities.values())
    assert set(hashed[-48:]) == set(hashes)
    for s in loaded.values():
        assert all(not x.flags.writeable for x in s.values())
        assert s["net_input"][52:].tobytes() == s["wet"][:-52].tobytes()


@pytest.mark.parametrize("damage", ["last_hash", "symlink", "hardlink", "old_identity", "overlap", "dtype", "nan", "silent", "postload"])
def test_input_drift_original52_and_activity_rejections(synthetic_inputs, monkeypatch, damage):
    hashes, verified, control, old = synthetic_inputs
    path = T.SOURCE/"render"/f"{takes()[-1]['slug']}.npz"
    if damage == "last_hash": path.write_bytes(b"drift")
    if damage in ("symlink", "hardlink"):
        copy = path.with_suffix(".copy")
        path.rename(copy)
        if damage == "symlink": path.symlink_to(copy)
        else: path.hardlink_to(copy)
    if damage == "old_identity": old["waveforms"][takes()[-1]["slug"]]["di"]["sha256"] = "0"*64
    if damage in ("overlap", "dtype", "nan", "silent"):
        with np.load(path, allow_pickle=False) as z: x, baseline = z["net_input"], z["baseline"]
        if damage == "overlap": x[100] += .01
        if damage == "dtype": x = x.astype("<f4")
        if damage == "nan": x[100] = np.nan
        if damage == "silent": x[:] = 0
        np.savez(path, net_input=x, baseline=baseline)
        hashes[str(path.relative_to(U.ROOT))] = R.sha(path)
    if damage == "postload":
        real_load = np.load
        count = []
        class ChangeAfter:
            def __init__(self, path): self.path, self.saved = path, real_load(path, allow_pickle=False)
            def __enter__(self): return self.saved
            def __exit__(self, *a):
                self.saved.close()
                count.append(1)
                if len(count) == 49: self.path.write_bytes(b"after-load drift")
        monkeypatch.setattr(np, "load", lambda p, **kw: ChangeAfter(p))
    if damage in ("last_hash", "symlink", "hardlink"):
        monkeypatch.setattr(np, "load", lambda *a, **k: pytest.fail("loaded before all48 barrier"))
    with pytest.raises(ValueError): U.load_inputs(takes(), hashes, verified, control, old, time.monotonic())


@pytest.fixture
def pipeline(tree, monkeypatch):
    monkeypatch.setattr(P, "SCORE", 600)
    original_rows = [row(t) for t in takes()]
    original = {"complete": True, "rows": original_rows, "screen": U.F.compare(original_rows, takes())}
    x = np.linspace(-.4, .5, P.SCORE, dtype=np.float64)
    loaded = {t["slug"]: {"net_input": x.copy(), "net": (x*.8).astype("<f4"),
              "di": x*.2, "target": x+1, "wet": x+2, "flatref": x+3} for t in takes()}
    for saved in loaded.values():
        for wave in saved.values(): wave.flags.writeable = False
    out = tree/"output"
    out.mkdir()
    windows = {4: np.ones(4)}
    hashes = {str((T.SOURCE/"infer"/f"{t['slug']}.npz").relative_to(tree)): "f"*64 for t in takes()}
    context = ({}, {"takes": takes(), "model": {"path": U.MODEL_PATH, "sha256": U.MODEL_SHA},
                   "attribution": "synthetic"}, {}, "revision", original, {}, {}, hashes, {})
    monkeypatch.setattr(U, "stability", lambda *a: None)
    monkeypatch.setattr(U.V, "load_windows", lambda *a: windows)
    monkeypatch.setattr(U, "load_inputs", lambda *a: (loaded, {}))
    model_calls, infer_calls, score_calls = [], [], []
    def model(*a):
        assert read(out/"baseline-replay.json")["passed"]
        assert len(score_calls) == 36
        model_calls.append(1)
        return "synthetic-model"
    def infer(net, wave, started):
        assert net == "synthetic-model"
        assert read(out/"baseline-replay.json")["scalar_count"] == 108
        i = len(infer_calls)
        if i >= 12:
            report = read(out/"baseline-inference-replay.json")
            assert report["complete"] and report["passed"] and report["scalar_count"] == 36
            assert len(score_calls) >= 48
        infer_calls.append(wave.copy())
        return (wave*.8).astype("<f4")
    def scoring(wave, target, raw, *, windows):
        assert windows is pipeline_windows
        i = len(score_calls)
        take_index = i//3 if i < 36 else (i-36) % 12
        saved = loaded[takes()[take_index]["slug"]]
        assert target is saved["target"] and raw is saved["di"]
        arm = i % 3 if i < 36 else 1
        if i < 36: assert wave is saved[list(T.ARMS)[arm]]
        score_calls.append(wave.copy())
        return scores([2., .8, 1.][arm])
    pipeline_windows = windows
    monkeypatch.setattr(U, "load_model", model)
    monkeypatch.setattr(U, "infer", infer)
    monkeypatch.setattr(P, "score_prediction", scoring)
    return out, context, loaded, windows, model_calls, infer_calls, score_calls


def test_full_pipeline_two_barriers_60cases_known_inverse_fixed_competitors(pipeline):
    out, context, loaded, _, models, inference, scoring = pipeline
    U.run(out, context, time.monotonic())
    assert len(models) == 1 and len(inference) == 60 and len(scoring) == 96
    report = read(out/"result.json")
    assert report["complete"] and len(report["rows"]) == 60
    assert report["screen"]["disposition"] == "PASS" and len(report["screen"]["offset_screens"]) == 5
    progress = [json.loads(line) for line in (out/"progress.jsonl").read_text().splitlines()]
    baseline_progress = [r for r in progress if r["stage"] == "baseline-inference"]
    case_progress = [r for r in progress if r["stage"] == "cases"]
    assert len(progress) == 72 and len(baseline_progress) == 12 and len(case_progress) == 60
    assert case_progress == [dict(stage="cases", **r) for r in report["rows"]]
    assert len(list(out.glob("*.npz"))) == 60
    offset_order = [0]*12 + [v for o in U.OFFSETS if o for v in [o]*12]
    for i, (wave, offset) in enumerate(zip(inference, offset_order)):
        saved = loaded[takes()[i % 12]["slug"]]
        np.testing.assert_array_equal(wave, T.finite_shift(saved["net_input"], offset))
    for r in report["rows"]:
        saved = loaded[r["slug"]]
        assert r["wet"] == 2. and r["flatref"] == 1.
        assert r["changes_from_zero"]["wet"]["primary_absolute_change"] == 0.
        with np.load(out/r["prediction_file"], allow_pickle=False) as z:
            shifted = np.zeros_like(saved["net_input"])
            o = r["offset"]
            if o > 0: shifted[o:] = saved["net_input"][:-o]
            elif o < 0: shifted[:o] = saved["net_input"][-o:]
            else: shifted[:] = saved["net_input"]
            expected_raw = (shifted*.8).astype("<f4")
            np.testing.assert_array_equal(z["raw_prediction"], expected_raw)
            inverse_indices = np.arange(P.SCORE)+o
            good = (inverse_indices >= 0) & (inverse_indices < P.SCORE)
            corrected = np.zeros(P.SCORE, dtype="<f4")
            corrected[good] = expected_raw[inverse_indices[good]]
            np.testing.assert_array_equal(z["corrected_prediction"], corrected)
            assert r["inverse_offset"] == -o
        assert r["input_sha256_float32"] == T.wave_hash(shifted, "<f4")


@pytest.mark.parametrize("kind", ["bytes", "score", "exception", "nonfinite"])
def test_last_baseline_prediction_failure_retains_complete12_blocks_every_shift(pipeline, monkeypatch, kind):
    out, context, _, _, _, inference, scoring = pipeline
    real_infer, real_score = U.infer, P.score_prediction
    def infer(*a):
        raw = real_infer(*a)
        if len(inference) == 12:
            if kind == "bytes": raw[-1] = np.nextafter(raw[-1], np.float32(np.inf))
            if kind == "nonfinite": raw[1] = np.nan
            if kind == "exception": raise ValueError("last synthetic network error")
        return raw
    def score(*a, **k):
        s = real_score(*a, **k)
        if len(scoring) == 48 and kind == "score": s["raw_lowband"] += 2e-8
        return s
    monkeypatch.setattr(U, "infer", infer)
    monkeypatch.setattr(P, "score_prediction", score)
    with pytest.raises(ValueError, match="complete12"): U.run(out, context, time.monotonic())
    replay = read(out/"baseline-inference-replay.json")
    assert replay["complete"] and not replay["passed"] and len(replay["rows"]) == 12
    assert not replay["rows"][-1]["valid"] and len(inference) == 12
    assert len(list(out.glob("*.npz"))) == (11 if kind == "exception" else 12)
    if kind != "exception":
        with np.load(out/replay["rows"][-1]["prediction_file"], allow_pickle=False) as z:
            assert "raw_prediction" in z and "corrected_prediction" in z
            if kind == "nonfinite": assert np.isnan(z["raw_prediction"][1])
            if kind == "bytes": assert not replay["rows"][-1]["byte_identical"]
    assert not (out/"result.json").exists()


@pytest.mark.parametrize("damage", ["last_scalar", "last_nonfinite", "last_error"])
def test_all108_replay_failure_blocks_all_network_calls(pipeline, monkeypatch, damage):
    out, context, _, _, models, inference, scoring = pipeline
    real = P.score_prediction
    def score(*a, **k):
        s = real(*a, **k)
        if len(scoring) == 36:
            if damage == "last_scalar": s["raw_lowband"] += 2e-8
            if damage == "last_nonfinite": s["raw_lowband"] = float("nan")
            if damage == "last_error": raise ValueError("last scorer error")
        return s
    monkeypatch.setattr(P, "score_prediction", score)
    with pytest.raises(ValueError, match="original108"): U.run(out, context, time.monotonic())
    replay = read(out/"baseline-replay.json")
    assert replay["complete"] and not replay["passed"] and len(replay["rows"]) == 12
    assert not models and not inference and len(scoring) == 36


@pytest.mark.parametrize("damage", ["error", "nonfinite", "score_nan"])
def test_shifted_error_keeps_remaining_cases_and_inconclusive_priority(pipeline, monkeypatch, damage):
    out, context, _, _, _, inference, _ = pipeline
    real_infer, real_score = U.infer, P.score_prediction
    def infer(*a):
        raw = real_infer(*a)
        if len(inference) == 13:
            if damage == "error": raise ValueError("synthetic shifted failure")
            if damage == "nonfinite": raw[0] = np.inf
        return raw
    def score(*a, **k):
        s = real_score(*a, **k)
        if len(inference) == 13 and damage == "score_nan": s["raw_lowband"] = float("nan")
        return s
    monkeypatch.setattr(U, "infer", infer)
    monkeypatch.setattr(P, "score_prediction", score)
    # Pipeline scorer's take ordering needs to advance despite a missing score call.
    if damage in ("error", "nonfinite"):
        # Use the original scorer through the baseline barriers, then allow all later calls.
        def post_barrier_score(*a, **k):
            return real_score(*a, **k) if len(inference) <= 12 else scores(.8)
        monkeypatch.setattr(P, "score_prediction", post_barrier_score)
    U.run(out, context, time.monotonic())
    result = read(out/"result.json")
    assert len(inference) == 60 and len(result["rows"]) == 60
    assert result["screen"]["disposition"] == "INCONCLUSIVE" and len(result["screen"]["offset_screens"]) == 5
    assert sum(not r["valid"] for r in result["rows"]) == 1
    bad = next(r for r in result["rows"] if not r["valid"])
    if damage != "error":
        assert (out/bad["prediction_file"]).exists()
        with np.load(out/bad["prediction_file"], allow_pickle=False) as z: assert "raw_prediction" in z
    assert bad["input_sha256_float32"] and bad["original_prediction_file_sha256"] == "f"*64
    assert bad["wet"] == 2. and bad["flatref"] == 1. and bad["qc_valid"] is True
    if damage == "score_nan":
        assert bad["network_scores"]["raw_lowband"] is None
        assert "row.network_scores.raw_lowband" in bad["nonfinite_diagnostic_fields"]


def test_baseline36_parity_is_direct_to_archive_not_accumulated_replay_tolerance(pipeline, monkeypatch):
    out, context, _, _, _, inference, calls = pipeline
    real_score = P.score_prediction
    def score(*a, **k):
        s = real_score(*a, **k)
        i = len(calls)-1
        if i < 36 and i % 3 == 1: s["raw_lowband"] += .75*T.TOL
        elif i >= 36: s["raw_lowband"] += 1.5*T.TOL
        return s
    monkeypatch.setattr(P, "score_prediction", score)
    with pytest.raises(ValueError, match="complete12"): U.run(out, context, time.monotonic())
    assert read(out/"baseline-replay.json")["passed"]
    replay = read(out/"baseline-inference-replay.json")
    assert replay["complete"] and not replay["passed"] and replay["scalar_count"] == 36
    assert len(inference) == 12 and all(r["errors"]["raw_lowband"] > T.TOL for r in replay["rows"])


def test_gate_each_offset_stronger_simple_all_wins_groups_and_zero_prerequisite():
    r = rows()
    for v in r: set_net(v, .9)
    assert U.compare(r, takes())["passed"]
    for offset in U.SMALL:
        damaged = deepcopy(r)
        for v in damaged:
            if v["offset"] == offset: set_net(v, .90001)
        assert U.compare(damaged, takes())["disposition"] == "FAIL"
    for v in r:
        if v["offset"] == 0: set_net(v, 1.1)
    assert U.compare(r, takes())["disposition"] == "INCONCLUSIVE"
    for kind in ("wins", "group", "wet_only"):
        damaged = rows()
        for v in damaged:
            if v["offset"] != -3: continue
            if kind == "wins" and int(v["take"]) < 4: set_net(v, 1.)
            if kind == "group" and v["content"] == "scales": set_net(v, 1.)
            if kind == "wet_only": set_net(v, 1.1)
        screen = U.compare(damaged, takes())
        assert screen["disposition"] == "FAIL"


@pytest.mark.parametrize("damage", ["missing", "duplicate", "extra", "identity", "bool_offset", "nonfinite",
                                    "negative", "qc", "oracle", "zero_simple", "invalid", "metric"])
def test_exact60_coverage_and_invalid_overrides_scientific_fail(damage):
    r = rows()
    for v in r:
        if v["offset"] == -3: set_net(v, 4.)
    v = r[-1]
    if damage == "missing": r.pop()
    if damage == "duplicate": r[-1] = r[0]
    if damage == "extra": r.append(deepcopy(r[0]))
    if damage == "identity": v["take"] = "other"
    if damage == "bool_offset": r[24]["offset"] = False
    if damage == "nonfinite": v["network_scores"]["raw_lowband"] = float("nan")
    if damage == "negative": v["network_scores"]["raw_lowband"] = -1.
    if damage == "qc": v["qc_valid"] = False
    if damage == "oracle": v["oracle"] = 1e-6
    if damage == "zero_simple": v["flatref"] = v["flatref_scores"]["primary"] = 0.
    if damage == "invalid": v["valid"] = False
    if damage == "metric": v["network_scores"].pop("raw_lowband")
    result = U.compare(r, takes())
    assert result["disposition"] == "INCONCLUSIVE" and len(result["offset_screens"]) == 5


@pytest.mark.parametrize("damage", ["reuse", "alias", "other", "symlink"])
def test_output_fixed_exclusive_no_alias(tree, damage):
    expected = tree/U.OUTPUT
    requested = expected
    if damage == "reuse": expected.mkdir(parents=True)
    if damage == "alias": requested = expected.parent/"x"/".."/expected.name
    if damage == "other": requested = expected.with_name("other")
    if damage == "symlink":
        other = tree/"other"
        other.mkdir()
        expected.parent.mkdir(parents=True)
        expected.symlink_to(other, target_is_directory=True)
    with pytest.raises((ValueError, FileExistsError)): U.output_directory(requested)


def test_prefix_and_cli_reject_before_guard_and_output(tree, monkeypatch):
    monkeypatch.setattr(U, "guard", lambda *a: pytest.fail("guard reached"))
    monkeypatch.setattr(U, "output_directory", lambda *a: pytest.fail("output reached"))
    monkeypatch.setattr(sys, "prefix", str(tree/"wrong"))
    with pytest.raises(ValueError, match="explicit original CPU"): U.main(["--out", U.OUTPUT])
    for argv in (["--ou", U.OUTPUT], ["--out", U.OUTPUT, "--offset", "2"], []):
        with pytest.raises(SystemExit): U.main(argv)


@pytest.mark.parametrize("mode", ["timeout", "final_drift", "first_shift_drift"])
def test_main_failure_evidence_budget_and_stability_barriers(pipeline, monkeypatch, mode):
    out, context, _, _, _, inference, _ = pipeline
    monkeypatch.setattr(sys, "prefix", str(U.CPU_PREFIX))
    monkeypatch.setattr(U, "guard", lambda *a: context)
    monkeypatch.setattr(U, "output_directory", lambda *a: out)
    checks = []
    def stable(*a):
        checks.append(1)
        if (mode == "final_drift" and len(checks) == 4) or (mode == "first_shift_drift" and len(checks) == 3):
            raise ValueError("synthetic source/input/model/HEAD drift")
    monkeypatch.setattr(U, "stability", stable)
    real_time = R.check_time
    def budget(start):
        if len(inference) >= 14: real_time(time.monotonic()-R.LIMIT-1)
    if mode == "timeout": monkeypatch.setattr(R, "check_time", budget)
    with pytest.raises(TimeoutError if mode == "timeout" else ValueError): U.main(["--out", U.OUTPUT])
    assert read(out/"failure.json")["disposition"] == "INCONCLUSIVE"
    assert read(out/"baseline-replay.json")["passed"] and read(out/"baseline-inference-replay.json")["passed"]
    assert (out/"provenance.json").exists() and (out/"inputs.json").exists() and (out/"progress.jsonl").exists()
    if mode == "first_shift_drift": assert len(inference) == 12
    if mode == "final_drift":
        result = read(out/"result.json")
        assert len(result["rows"]) == 60 and result["screen"]["disposition"] == "INCONCLUSIVE"
    if mode == "timeout":
        assert len(inference) == 14 and len(list(out.glob("*.npz"))) == 14
        assert not (out/"result.json").exists()


def test_model_exact_path_hash_nonlink_and_budget(tree, monkeypatch):
    path = tree/"fold2.pt"
    path.write_bytes(b"synthetic-not-weights")
    monkeypatch.setattr(U, "MODEL_PATH", str(path))
    monkeypatch.setattr(U, "MODEL_SHA", R.sha(path))
    manifest = {"model": {"path": str(path), "sha256": U.MODEL_SHA}}
    assert U.check_model(manifest, time.monotonic()) == manifest["model"]
    with pytest.raises(TimeoutError): U.check_model(manifest, time.monotonic()-R.LIMIT-1)
    with pytest.raises(ValueError): U.check_model({"model": {"path": "average.npy", "sha256": "0"*64}}, time.monotonic())
    path.write_bytes(b"drift")
    with pytest.raises(ValueError, match="hash drift"): U.check_model(manifest, time.monotonic())
    path.unlink()
    other = tree/"other"
    other.write_bytes(b"synthetic-not-weights")
    path.symlink_to(other)
    with pytest.raises(ValueError, match="nonlink"): U.check_model(manifest, time.monotonic())
