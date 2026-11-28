"""The LOUDAR prior timing probe (`learn/prior_probe.py`, docs/prior-probe-plan.md; ledger `preset-ladder`
`phase_scratch_prior_probe`): the PP codes in their declared order, the tolerances and the calibration, the per-tensor
check, the clip check, the non-finite step, the error kinds, the projections, the timing arithmetic, the segment
rule, the idle rule, the file rule, the hours tally, the config and pin guards, the checkpoint refusal before torch,
JSON-only writes (`time` behind a fake runner), and the declaration in the ledger. Pure: no numpy or torch at import
(the light CI runner); every key and item below is made up."""
import ast
import json
import os
import pathlib
import subprocess
import sys

import pytest

from learn import prior_probe as P

REPO = pathlib.Path(__file__).resolve().parents[1]
LOUDAR_SRC = pathlib.Path("~/ndsp-presets/tools/loudar/src").expanduser()


def _entry():
    doc = json.loads((REPO / "docs" / "dev-test-ledger.json").read_text())
    return next(t for t in doc["tests"] if t["test_id"] == P.LEDGER_ID)


# --- imports ------------------------------------------------------------------------------------------------------------

BLOCK = ("import sys\n"
         "class B:\n"
         "    def find_spec(self, name, path=None, target=None):\n"
         "        if name.split('.')[0] in ('numpy', 'torch', 'scipy', 'soundfile', 'omegaconf', 'hydra'):\n"
         "            raise ImportError('blocked: ' + name)\n"
         "sys.meta_path.insert(0, B())\n")


@pytest.mark.parametrize("how", ["module", "script"])
def test_imports_with_numpy_and_torch_blocked(how):
    """As `-m learn.prior_probe` and as `$LV learn/prior_probe.py` (learn/ on sys.path): the module and its pure parts
    need neither numpy nor torch."""
    imp = "from learn import prior_probe as P\n" if how == "module" else "import prior_probe as P\n"
    code = BLOCK + imp + ("P.table_guard()\n"
                          "assert P.pp_code([], [], 0, [])[0] == 'PP-mps'\n"
                          "assert P.SEG_SHORT == 218624\n"
                          "assert P.tensor_check({'a': {'ref': 1.0, 'diff': 0.0}}, 1e-3)['pass']\n"
                          "assert 'numpy' not in sys.modules and 'torch' not in sys.modules\n"
                          "assert (P.LR.__name__ == 'learn.loudar_run') == (" + repr(how == "module") + ")\n"
                          "print('ok')\n")
    cwd = REPO if how == "module" else REPO / "learn"       # as a script, learn/ is the path and `learn` is not
    r = subprocess.run([sys.executable, "-c", code], cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "ok"


def test_top_level_imports_are_stdlib_and_loudar_run():
    if not hasattr(sys, "stdlib_module_names"):                 # Python 3.10+ (CI runs 3.10 to 3.13)
        pytest.skip("sys.stdlib_module_names needs Python 3.10")
    tree = ast.parse((REPO / "learn" / "prior_probe.py").read_text())
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module.split(".")[0])
        elif isinstance(node, ast.Try):
            for n in ast.walk(node):
                if isinstance(n, ast.Import):
                    names |= {a.name.split(".")[0] for a in n.names}
                elif isinstance(n, ast.ImportFrom):
                    names.add(n.module.split(".")[0])
    allowed = set(sys.stdlib_module_names) | {"learn", "loudar_run", "__future__"}
    assert names <= allowed, names - allowed


def test_no_model_is_ever_written_in_the_source():
    src = (REPO / "learn" / "prior_probe.py").read_text()
    assert "torch.save(" not in src and "save_checkpoint" not in src and "state_dict()" not in src
    assert src.count("torch.save = no_save") == 1
    tree = ast.parse(src)
    saves = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr in ("save", "savez", "write_bytes")]
    owners = set()
    for f in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if any(s in ast.walk(f) for s in saves):
            owners.add(f.name)
    assert owners == {"cmd_prep"}, owners                  # the segments only; everything else goes through write_json


# --- the codes ----------------------------------------------------------------------------------------------------------

def test_codes_are_declared_in_order():
    assert P.CODES == ("PP-anomaly", "PP-cpu-only", "PP-unstable", "PP-mps-fallback", "PP-mps")
    assert set(P.PP_TABLE) == set(P.CODES)
    P.table_guard()


def test_pp_code_first_that_holds():
    assert P.pp_code(["pin"], ["oom"], 3, ["clip"])[0] == "PP-anomaly"
    assert P.pp_code([], ["oom"], 3, ["clip"])[0] == "PP-cpu-only"
    assert P.pp_code([], [], 3, ["clip"])[0] == "PP-unstable"
    assert P.pp_code([], [], 0, ["clip"])[0] == "PP-mps-fallback"
    code, why = P.pp_code([], [], 0, [])
    assert code == "PP-mps" and why == []


def test_table_guard_catches_a_reordered_table(monkeypatch):
    monkeypatch.setattr(P, "CODES", ("PP-cpu-only", "PP-anomaly", "PP-unstable", "PP-mps-fallback", "PP-mps"))
    with pytest.raises(SystemExit):
        P.table_guard()


@pytest.mark.parametrize("tname,msg,kind", [
    ("RuntimeError", "MPS backend out of memory (MPS allocated: 20 GB)", "oom"),
    ("NotImplementedError", "The operator 'aten::_fft_r2c' is not currently implemented for the MPS device.",
     "unsupported"),
    ("RuntimeError", "The operator 'aten::foo' is not currently implemented for the MPS device", "unsupported"),
    ("RuntimeError", "shape mismatch", "other"),
    ("KeyError", "x", "other"),
])
def test_error_kind(tname, msg, kind):
    assert P.error_kind(tname, msg) == kind


def test_op_named():
    assert P.op_named("The operator 'aten::_fft_r2c' is not currently implemented") == "aten::_fft_r2c"
    assert P.op_named("no op here") is None


# --- the checks ---------------------------------------------------------------------------------------------------------

def _rows(n=10, ref=1.0, diff=1e-5, **extra):
    return {f"t{i}": dict({"ref": ref, "diff": diff}, **extra) for i in range(n)}


def test_tensor_check_passes_rounding():
    r = P.tensor_check(_rows(), 1e-3)
    assert r["pass"] and r["global_pass"] and not r["failing"] and r["tensors"] == 10


def test_a_broken_small_tensor_fails_though_the_global_figure_passes():
    rows = _rows(n=50, ref=200.0, diff=1e-3)
    rows["tiny"] = {"ref": 1.0, "diff": 0.9}               # 90% off; measured against the floor (about 2), still 45%
    r = P.tensor_check(rows, 1e-3)
    assert r["global_pass"] and r["global_err"] < 1e-3      # the global figure alone would pass it
    assert r["failing"] == ["tiny"] and not r["pass"] and r["worst_tensor"] == "tiny"


def test_a_near_zero_tensor_is_measured_against_the_floor():
    rows = _rows(n=10, ref=10.0, diff=1e-4)
    rows["zero"] = {"ref": 1e-9, "diff": 1e-6}             # rounding on a near-zero tensor: floor 0.1, error 1e-5
    r = P.tensor_check(rows, 1e-3)
    assert r["pass"] and r["floor"] == pytest.approx(P.PER_TENSOR_FLOOR * 10.0 * (10 / 11) ** 0.5)


def test_calibration_rescues_rounding_and_not_a_broken_op():
    rounding = _rows(n=10, ref=1.0, diff=2e-3, ref64=1.0, dev64=2e-3, cpu64=8e-4)    # within 3x the CPU's own error
    r = P.tensor_check(rounding, 1e-3)
    assert r["pass"] and r["global_how"] == "calibrated" and len(r["calibrated"]) == 10
    assert r["calibration"] == "allowed"
    broken = _rows(n=10, ref=1.0, diff=5e-3, ref64=1.0, dev64=5e-3, cpu64=1e-4)      # 50x the CPU's own error
    assert not P.tensor_check(broken, 1e-3)["pass"]
    no64 = _rows(n=10, ref=1.0, diff=5e-3)                                           # no reference: nothing calibrated
    r = P.tensor_check(no64, 1e-3)
    assert not r["pass"] and r["calibration"] == "no float64 reference"


def test_calibration_needs_a_reference_that_holds():
    """Fix 2: a calibrated pass only on a reference that itself holds; never for a tensor above the 0.1 cap."""
    wrong_ref = _rows(n=10, ref=1.0, diff=5e-3, ref64=1.0, dev64=4e-3, cpu64=2e-3)   # CPU 2e-3 off float64 globally
    r = P.tensor_check(wrong_ref, 1e-3)
    assert not r["pass"] and r["calibration"].startswith("refused") and r["global_how"] == "direct"
    assert r["calibrated"] == [] and len(r["failing"]) == 10
    fine = _rows(n=10, ref=1.0, diff=2e-3, ref64=1.0, dev64=2e-3, cpu64=8e-4)
    r = P.tensor_check(fine, 1e-3, ref_ok=False)                                     # the loss or the draws failed
    assert not r["pass"] and r["calibration"] == "refused: the reference does not hold"
    capped = _rows(n=400, ref=100.0, diff=1e-4, ref64=100.0, dev64=1e-4, cpu64=1e-4)
    capped["odd"] = {"ref": 1.0, "diff": 0.5, "ref64": 1.0, "dev64": 0.4, "cpu64": 0.3}  # 0.3 off: above the cap
    r = P.tensor_check(capped, 1e-3)
    assert r["calibration"] == "allowed" and r["global_err_cpu_f64"] < 1e-3          # the reference holds globally
    assert r["capped"] == ["odd"] and r["failing"] == ["odd"] and not r["pass"]


def test_reference_holds():
    good = _rows(n=10, ref=1.0, diff=1e-4, ref64=1.0, dev64=1e-4, cpu64=1e-5)
    h = P.reference_holds(0.5, 0.50001, good, True)
    assert h["holds"] and h["why"] == [] and h["grad_err_cpu_f64"] == pytest.approx(1e-5)
    assert not P.reference_holds(0.5, 0.501, good, True)["holds"]                    # the loss 2e-3 off
    bad = _rows(n=10, ref=1.0, diff=1e-4, ref64=1.0, dev64=1e-4, cpu64=5e-3)
    assert "global gradient" in P.reference_holds(0.5, 0.5, bad, True)["why"][0]
    assert "noise" in P.reference_holds(0.5, 0.5, good, False)["why"][0]
    assert not P.reference_holds(0.5, None, good, True)["holds"]
    assert not P.reference_holds(0.5, 0.5, _rows(), True)["holds"]                   # no float64 gradients


def test_encoder_verdict():
    assert P.encoder_verdict(5e-4, None)["how"] == "direct"
    assert P.encoder_verdict(2e-3, {"dev": 2e-3, "cpu": 8e-4})["how"] == "calibrated"
    r = P.encoder_verdict(2e-2, {"dev": 2e-2, "cpu": 2e-2})                         # the float64 encoder is off itself
    assert not r["pass"] and r["calibration"].startswith("refused")
    assert not P.encoder_verdict(2e-3, None)["pass"]


class _Fake:
    """Fake train_once/f64_reference/compare_runs for run 2: records the calls, latents as plain made-up lists."""

    def __init__(self, passes=True):
        self.calls, self.passes = [], passes

    def train(self, m, enc, dev, batch, enc_mode, clip_mode, shared=None, seed=None):
        self.calls.append(("train", dev, enc_mode, clip_mode, shared))
        return {"lat": ["lat", dev, enc_mode] if shared is None else shared, "t": "t", "z": "z"}

    def reference(self, m, batch, lat, t, z):
        self.calls.append(("reference", lat))
        return {"loss": 1.0, "grads": {}, "norm": 2.0}

    def compare(self, m, dev_r, cpu_r, ref):
        self.calls.append(("compare", dev_r["lat"], cpu_r["lat"]))
        return {"pass_network": self.passes, "pass_clip": True}


def test_run_two_feeds_the_cpu_the_mps_runs_own_latents():
    """Fix 1: the CPU reference and the float64 reference get the MPS run's own latents."""
    f = _Fake()
    rec, mode, fb, co = P.run_two(None, None, "batch", True, "native", f.train, f.reference, f.compare)
    mps_lat = ["lat", "mps", "mps"]
    assert f.calls == [("train", "mps", "mps", "native", None), ("train", "cpu", "cpu", "native", mps_lat),
                       ("reference", mps_lat), ("compare", mps_lat, mps_lat)]
    assert mode == "mps" and fb == [] and co == [] and rec["encoder"] == "mps"
    assert rec["float64_reference"] == {"loss": 1.0, "norm": 2.0}


def test_run_two_never_switches_the_encoder():
    """Fix 1: the encoder is judged only by its latent check; a run-2 miss is cpu-only, not the CPU-encoder fallback."""
    f = _Fake(passes=False)
    rec, mode, fb, co = P.run_two(None, None, "batch", True, "foreach_false", f.train, f.reference, f.compare)
    assert mode is None and fb == [] and len(co) == 1 and "mps encoder" in co[0]
    assert [c for c in f.calls if c[0] == "train" and c[1] == "mps"] == [("train", "mps", "mps", "foreach_false",
                                                                          None)]
    f = _Fake()                                                    # the latent check failed: the CPU encoder, declared
    rec, mode, fb, co = P.run_two(None, None, "batch", False, "native", f.train, f.reference, f.compare)
    assert mode == "cpu" and fb == [P.FALLBACK_NAMES[("encoder", "cpu")]] and co == []
    assert f.calls[0] == ("train", "mps", "cpu", "native", None)


def test_run_two_names_an_unsupported_op():
    def train(m, enc, dev, *a, **k):
        raise NotImplementedError("The operator 'aten::made_up' is not currently implemented for the MPS device.")
    rec, mode, fb, co = P.run_two(None, None, "batch", True, "native", train, None, None)
    assert mode is None and rec["error"]["op"] == "aten::made_up" and "aten::made_up" in co[0]


def test_missing_gradients():
    rows = _rows()
    rows["unused"] = {"none": "both"}
    assert P.tensor_check(rows, 1e-3)["pass"]
    rows["lost"] = {"none": "dev"}
    r = P.tensor_check(rows, 1e-3)
    assert not r["pass"] and r["none_one"] == ["lost"] and r["none_both"] == ["unused"]


def test_non_finite_norms_fail():
    rows = _rows()
    rows["t0"] = {"ref": 1.0, "diff": float("nan")}
    r = P.tensor_check(rows, 1e-3)
    assert not r["pass"] and r["why"] == "non-finite"


def test_scalar_check():
    assert P.scalar_check(1.00001, 1.0, 1e-4)["how"] == "direct"
    miss = P.scalar_check(1.001, 1.0, 1e-4)
    assert not miss["pass"] and "no float64" in miss["how"]
    ok = P.scalar_check(1.0002, 1.0, 1e-4, f64=1.0001)                    # 1e-4 against the CPU's 1e-4
    assert ok["pass"] and ok["how"] == "calibrated" and ok["calibration"] == "allowed"
    assert not P.scalar_check(1.0002, 1.0, 1e-4, f64=1.0001, ref_ok=False)["pass"]
    off = P.scalar_check(1.001, 1.0, 1e-4, f64=1.0005)                    # the CPU 5e-4 off float64: refused
    assert not off["pass"] and off["calibration"].startswith("refused")
    assert not P.scalar_check(1.01, 1.0, 1e-4, f64=1.0)["pass"]
    assert not P.scalar_check(float("nan"), 1.0, 1e-4)["pass"]


def test_clip_check():
    after = {"pass": True}
    r = P.clip_check(2.5, 2.5, 0, after)
    assert r["pass"] and r["scaled"] is True
    assert P.clip_check(0.5, 0.5, 0, after)["scaled"] is False
    assert not P.clip_check(2.5, 2.5, 3, after)["pass"]                    # non-finite gradients after the clip
    assert not P.clip_check(float("nan"), 2.5, 0, after)["pass"]
    assert not P.clip_check(2.5, 2.5, 0, {"pass": False})["pass"]
    assert not P.clip_check(2.6, 2.5, 0, after)["pass"]


def test_nonfinite_step_definition():
    assert not P.nonfinite_step(0.3, 1.2, True)
    assert P.nonfinite_step(float("nan"), 1.2, True)
    assert P.nonfinite_step(0.3, float("inf"), True)
    assert P.nonfinite_step(0.3, 1.2, False)
    assert P.nonfinite_step(None, 1.2, True)


def test_tolerances_are_the_plans():
    assert P.TOL["encoder"] == P.TOL["grad"] == P.TOL["clip_norm"] == 1e-3 and P.TOL["loss"] == 1e-4
    assert P.CALIB_MULT == 3.0 and P.MAX_NORM == 1.0


# --- timing arithmetic ---------------------------------------------------------------------------------------------------

def test_projections():
    pr = P.projections(2.0)
    assert pr["s_per_1000"] == 500.0 and pr["h_175000"] == pytest.approx(175000 / 2 / 3600)
    assert pr["audio_h_per_1000"] == pytest.approx(6.0889, abs=1e-4)      # the plan's 6.09 h
    assert P.projections(None)["h_per_1000"] is None


def test_block_rate_leaves_the_warm_up_out():
    secs = [5.0] * 20 + [0.5] * 180
    r = P.block_rate(secs, 20)
    assert r["steps"] == 180 and r["rate"] == pytest.approx(2.0) and r["warmup_mean_s"] == 5.0
    assert P.block_rate([1.0] * 10, 20)["rate"] is None


def test_cpu_rate_from_steps_two_to_five():
    assert P.cpu_rate([100.0, 2.0, 2.0, 2.0, 2.0]) == pytest.approx(0.5)
    assert P.cpu_rate([1.0, 2.0]) is None


def test_split_rate():
    assert P.split_rate(0.5, 0.2)["network_s"] == pytest.approx(0.3)
    assert P.split_rate(None, 0.2)["network_s"] is None


def test_the_seeds_stand_apart_from_loudar_runs():
    """The probe's seeds lie above every seed loudar_run gives (both slots, all 47 parts), and its file never names
    loudar_run's base seed (tests/test_loudar_run.py's rule)."""
    loudar = {v for slot in (0, 1) for j in range(47) for v in P.LR.seeds(slot, j).values()}
    ours = {P.SEED, P.CHECK_SEED, P.TIME_SEED} | {P.FIVE_SEED + k for k in range(P.FIVE)}
    assert min(ours) > max(loudar) and not ours & loudar and max(ours) == P.SEED + 300
    assert str(P.LR.LD_SEED) not in (REPO / "learn" / "prior_probe.py").read_text()


def test_batches_cycle_through_the_sixteen():
    assert P.batch_indices(0) == [0, 1] and P.batch_indices(7) == [14, 15] and P.batch_indices(8) == [0, 1]
    assert {i for k in range(8) for i in P.batch_indices(k)} == set(range(16))


# --- the segments -------------------------------------------------------------------------------------------------------

def _items(n=30):
    out = {f"fake_{i}": {"start_s": 20.0, "seconds": 60.0} for i in range(n)}
    out["fake_short"] = {"start_s": 55.0, "seconds": 60.0}
    out["fake_nowin"] = {"start_s": None, "seconds": 60.0, "out": "no window"}
    out["fake_fs"] = {"start_s": 10.0, "seconds": 60.0, "out": "DI near full scale"}
    out["fake_renders"] = {"start_s": 10.0, "seconds": 60.0, "out": "no clean/crunch render"}
    return out


def test_segment_rule():
    items = _items()
    drawn = {"fake_1", "fake_2"}
    a = P.segment_rule(items, drawn, ruled_out=("fake_3",))
    assert len(a) == 16 and a == P.segment_rule(items, drawn, ruled_out=("fake_3",))
    got = {s["item"] for s in a}
    assert not got & (drawn | {"fake_3", "fake_short", "fake_nowin", "fake_fs"})
    assert P.segment_rule(items, drawn, seed=1) != a
    with pytest.raises(SystemExit):
        P.segment_rule({k: v for k, v in list(items.items())[:5]}, set())


def test_the_ruled_out_item_and_left_out_bands_are_the_projects():
    from learn import note_transcribe as NT
    from learn import scratch_search as S

    assert P.GOAT_RULED_OUT == NT.RULED_OUT
    assert set(S.PANEL_LEFT_OUT) <= set(P.LEFT_OUT_BANDS)


def test_drawn_goat_items():
    parts = [{"set": "goat", "cluster": "goat|fake_9"}, {"set": "bks", "cluster": "bks|x/y.wav"},
             {"set": "goat", "cluster": "goat|fake_2"}, {"set": "goat", "cluster": "goat|fake_9"}]
    assert P.drawn_goat_items(parts) == ["fake_2", "fake_9"]


# --- idle and files -----------------------------------------------------------------------------------------------------

def test_idle_counts_leave_the_probe_out():
    m = {"render": {}, "torch": {101: "python learn/prior_probe.py time", 100: "zsh -c ... loudar-venv ..."}}
    r = P.idle_counts(m, {101, 100})
    assert r["idle"] and r["render"] == 0 and r["torch"] == 0
    m["torch"][555] = "demucs-venv/bin/python train"
    m["render"][777] = "au_render_server"
    r = P.idle_counts(m, {101, 100})
    assert not r["idle"] and r["torch"] == 1 and r["render"] == 1 and r["pids"]["torch"] == [555]


def test_torch_patterns_match_the_tools_venvs():
    import re

    hits = ["/u/ndsp-presets/tools/loudar-venv/bin/python learn/prior_probe.py check",
            "/u/ndsp-presets/tools/demucs-venv/bin/python -m x", "/u/ndsp-presets/tools/readerr/venv-a/bin/python",
            ".venv/bin/python -m learn.pretrain_set curve --n 40000"]
    for h in hits:
        assert any(re.search(p, h) for p in P.TORCH_PATTERNS), h
    assert not any(re.search(p, ".venv/bin/python -m learn.scratch_own score --shard 1/3") for p in P.TORCH_PATTERNS)


def test_open_event_class():
    home, data = "/home/fake", "/home/fake/data"
    roots = ("/home/fake/data/tools/venv", "/home/fake/data/tools/code", "/home/fake/repo")
    out, models = "/home/fake/data/pf/fs/prior-probe", "/home/fake/data/tools/models"
    roots = roots + (out, models)

    def c(path, mode="r", flags=0):
        return P.open_event_class(path, mode, flags, home, roots, out, models, data)
    assert c("/home/fake/data/tools/code/src/x.py") is None
    assert c("/home/fake/data/references/other/x.wav") == "read-outside"
    assert c("/home/fake/data/learn/some.json") == "read-outside"
    assert c("/home/fake/Music/made-up.flac") == "read-outside"
    assert c("/home/fake/.config/lib/settings") is None              # a library's config, not data
    assert c("/usr/lib/x.dylib") is None
    assert c(out + "/time-1.json", "w") is None
    assert c("/home/fake/data/tools/code/src/__pycache__/x.pyc", "wb") == "write-outside"
    assert c(models + "/hf/hub/x.lock", "w") is None
    assert c("/tmp/model.pt", "wb") == "weights-write"
    assert c(out + "/net.pt", "wb") == "weights-write"
    assert c("/home/fake/x.txt", None, os.O_WRONLY | os.O_CREAT) == "write-outside"


def test_probe_files_refusal():
    files = ["prep.json", "check.json", "time-20261201-010101.json", "segments/seg-00.npy", "segments/seg-01.npy"]
    assert P.probe_files_refusal(files, ["seg-00.npy", "seg-01.npy"]) == []
    assert P.probe_files_refusal(files + ["net.pt", "segments/extra.npy"], ["seg-00.npy", "seg-01.npy"]) == \
        ["net.pt", "segments/extra.npy"]


def test_write_json_writes_only_new_json(tmp_path):
    P.write_json(tmp_path / "a.json", {"x": 1})
    assert json.loads((tmp_path / "a.json").read_text()) == {"x": 1}
    with pytest.raises(SystemExit):
        P.write_json(tmp_path / "a.json", {"x": 2})
    with pytest.raises(SystemExit):
        P.write_json(tmp_path / "net.pt", {"x": 1})
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.json"]


def test_keys_refusal():
    main = {P.KEY: {"a": 1}, "phase_other": 1}
    assert P.keys_refusal({P.KEY: {"a": 1}}, main) is None
    assert "differ" in P.keys_refusal({P.KEY: {"a": 2}}, main)
    assert "no phase_scratch_prior_probe" in P.keys_refusal({P.KEY: {"a": 1}}, {"phase_other": 1})
    assert "differ" in P.keys_refusal({P.KEY: {"a": 1}, P.KEY + "_outcome": {}}, main)


# --- hours --------------------------------------------------------------------------------------------------------------

def _sec(di, band, start=0.0, **kw):
    s = {"di": di, "band": band, "path": f"/x/{di}", "start_s": start, "end_s": start + 10.0, "source": "lib",
         "set": 2, "training_ok": True, "clean": True, "disjoint": True, "split": "library"}
    s.update(kw)
    return s


def test_library_tally_counts_each_section_under_its_first_reason():
    secs = [_sec("fake/a.wav", "Fake Band"), _sec("fake/a.wav", "Fake Band", 10.0),
            _sec("fake/b.wav", "Fake Band", clean=False),
            _sec("fake/c.wav", "Drowning"), _sec("fake/d.wav", "Held Band"),
            _sec("fake/e.wav", "Fake Band"), _sec("fake/f.wav", "Fake Band"), _sec("fake/g.wav", "Fake Band"),
            _sec("fake/h.wav", "Fake Band", source="other", set=3), _sec("fake/i.wav", "Held Band", clean=False)]
    rules = {"left_out_bands": set(P.LEFT_OUT_BANDS), "held_bands": {"Held Band": ["V-real"]},
             "held_out": {"/x/fake/e.wav": "held"}, "reserve": {"fake/f.wav"}, "marked": {"fake/g.wav"},
             "hum": set(), "draw": {("fake/a.wav", 10.0)}}
    t = P.library_tally(secs, rules)
    ex = {k: v["sections"] for k, v in t["excluded"].items()}
    assert ex == {"untrusted": 2, "left-out band": 1, "held band": 1, "held out": 1, "reserve DI": 1,
                  "user DI mark": 1, "hum superset": 0, "draw section": 1}
    assert t["by_source"] == {"lib / 2": {"sections": 1, "hours": pytest.approx(10 / 3600)},
                              "other / 3": {"sections": 1, "hours": pytest.approx(10 / 3600)}}
    assert t["hours"] == pytest.approx(20 / 3600)
    assert t["held_band_reasons"] == {"V-real": pytest.approx(10 / 3600)}
    assert P.section_reasons(secs[9], rules) == ["untrusted", "held band"]


def test_goat_tally():
    items = {"fake_1": {"seconds": 3600.0, "tuning": "standard"}, "fake_2": {"seconds": 1800.0, "tuning": "drop"},
             "fake_3": {"seconds": 100.0}, "fake_4": {"seconds": 50.0, "out": "no window"},
             "fake_5": {"seconds": 20.0, "out": "DI near full scale"},
             "fake_6": {"seconds": 360.0, "out": "no clean/crunch render", "tuning": "standard"}}
    t = P.goat_tally(items, {"fake_3"}, ruled_out=("fake_2",))
    assert t["hours"] == pytest.approx(1.1) and t["items"] == 2
    assert {k: v["items"] for k, v in t["excluded"].items()} == {"ruled out": 1, "draw item": 1,
                                                                 "5C: no screened window": 1,
                                                                 "5C: DI near full scale": 1}
    assert t["by_tuning"] == {"standard": pytest.approx(1.1)}


def test_hours_names_its_inputs_and_the_uncounted():
    ins = P.hours_inputs("/d")
    assert set(ins) == {"library_manifest", "library_inventory", "di_scope_verdicts", "batch3_marks", "draw",
                        "goat_units", "egdb_manifest", "egfxset_clean"}
    assert "MedleyDB" in P.NOT_COUNTED and P.LIBRARY_ORDER[0] == "untrusted"


# --- config, pins, the checkpoint ----------------------------------------------------------------------------------------

def _cfg():
    c = {}
    for k, v in P.CONFIG_EXPECT.items():
        d = c
        parts = k.split(".")
        for p_ in parts[:-1]:
            d = d.setdefault(p_, {})
        d[parts[-1]] = v
    return c


def test_config_refusal():
    assert P.config_refusal(_cfg()) is None
    c = _cfg()
    c["diff_params"]["_target_"] = "diff_params.diffusion_latent.FM_to_EDM_wrapper"
    assert "FM_to_EDM_wrapper" in P.config_refusal(c)
    c = _cfg()
    c["exp"]["optimizer"]["lr"] = 1e-3
    assert "lr" in P.config_refusal(c)
    c = _cfg()
    c["exp"]["use_grad_clip"] = 1                      # a bool must be a bool
    assert P.config_refusal(c)
    c = _cfg()
    del c["dset"]["train"]["rms_normalize"]
    assert P.config_refusal(c)


def test_defaults_refusal():
    good = ["_self_", {"dset": "GuitarFx"}, {"network": "dit_M2L"}, {"diff_params": "FM_m2l"},
            {"tester": "only_unconditional_lincae_FM"}, {"exp": "GuitarFx"}, {"logging": "base_logging"},
            {"override hydra/job_logging": "custom"}]
    assert P.defaults_refusal(good) is None
    bad = [d if d != {"diff_params": "FM_m2l"} else {"diff_params": "FM_to_EDM_m2l"} for d in good]
    assert "diff_params" in P.defaults_refusal(bad)


FAKE_SRC = '''import x


class Trainer:
    def other(self):
        return 1

    @staticmethod
    def train_step(self):
        """doc"""
        return 2


def apply_RMS_normalization(x):
    return x
'''


def test_function_source():
    s, line = P.function_source(FAKE_SRC, "Trainer.train_step")
    assert line == 8 and s.splitlines()[0].strip() == "@staticmethod" and s.splitlines()[-1].strip() == "return 2"
    assert P.function_source(FAKE_SRC, "apply_RMS_normalization")[1] == 14
    with pytest.raises(KeyError):
        P.function_source(FAKE_SRC, "Trainer.update_ema")
    assert P.source_sha(FAKE_SRC, "Trainer.train_step") != P.source_sha(FAKE_SRC.replace("return 2", "return 3"),
                                                                       "Trainer.train_step")


def test_pin_refusals():
    files = {f: s for f, s in P.LOUDAR_FILES.items()}
    funcs = {k: s for k, s in P.LOUDAR_FUNCS.items()}
    assert P.pin_refusals(files, funcs) == []
    files["training/trainer.py"] = "0" * 64
    funcs[("diff_params/diffusion_latent.py", "FM.loss_fn")] = None
    bad = P.pin_refusals(files, funcs)
    assert len(bad) == 2 and any("trainer.py" in b for b in bad) and any("FM.loss_fn" in b for b in bad)


def test_the_pins_cover_the_amendments_functions():
    q = {q for _, q in P.LOUDAR_FUNCS}
    assert {"Trainer.train_step", "Trainer.update_ema", "FM.loss_fn", "FM.prepare_train_preconditioning"} <= q
    assert all(len(s) == 64 for s in list(P.LOUDAR_FILES.values()) + list(P.LOUDAR_FUNCS.values()))


@pytest.mark.skipif(not LOUDAR_SRC.is_dir(), reason="LOUDAR's code is not installed here")
def test_the_pins_are_the_installed_loudar():
    files, funcs = P.loudar_shas(LOUDAR_SRC)
    assert P.pin_refusals(files, funcs) == []


def test_checkpoint_refusal_before_torch(tmp_path, monkeypatch):
    f = tmp_path / "GuitarFx-175000.pt"
    f.write_bytes(b"not the checkpoint")
    assert "bytes" in P.checkpoint_refusal(f)
    monkeypatch.setattr(P.LR, "CHECKPOINT_SIZE", f.stat().st_size)
    assert "sha256" in P.checkpoint_refusal(f)
    assert "no checkpoint" in P.checkpoint_refusal(tmp_path / "missing.pt")


def test_checkpoint_path_is_the_pinned_revision():
    p = P.checkpoint_path("/m")
    assert p.parent.name == P.LR.LOUDAR_REVISION and p.name == P.LR.CHECKPOINT


def test_terms_record_m2l_as_apache():
    assert "Apache-2.0" in P.TERMS["m2l_autoencoder"] and "linear-cae 0.1.4" in P.TERMS["m2l_autoencoder"]
    assert "MIT" in P.TERMS["loudar_code"] and "CC BY-NC" in P.TERMS["goat"]


# --- time writes only JSON ------------------------------------------------------------------------------------------------

def _check_rec(**kw):
    r = {"anomaly": [], "cpu_only": [], "fallbacks": [], "config": {"encoder": "mps", "clip": "native"},
         "nonfinite_mps_five": 0, "five": {"cpu_rate": 0.1}}
    r.update(kw)
    return r


def test_check_refusal():
    assert P.check_refusal(_check_rec()) is None
    assert "anomaly" in P.check_refusal(_check_rec(anomaly=["pin"]))
    assert "cpu-only" in P.check_refusal(_check_rec(cpu_only=["grads"]))
    assert "no configuration" in P.check_refusal(_check_rec(config={"encoder": None, "clip": None}))
    assert "no check.json" in P.check_refusal(None)


def _block(idle=True, done=200, steps=200, samples=P.SEG, nonfinite=(), error=None, rate=2.0):
    secs = [1.0] * 20 + [1 / rate] * (done - 20) if done >= 20 else [1.0] * done
    return {"label": "long", "samples": samples, "steps": steps, "done": done, "idle": idle, "error": error,
            "nonfinite_steps": list(nonfinite), "rate": P.block_rate(secs, 20), "mps_driver_peak_bytes": 1,
            "mps_current_peak_bytes": 1}


def _time_rec(**kw):
    r = {"blocks": {"long": _block(**kw), "short": dict(_block(samples=P.SEG_SHORT, steps=100, done=100),
                                                        label="short")},
         "split": {}, "anomaly": [], "peak_rss_bytes": 1, "memsize_bytes": 2}
    return r


def test_time_writes_only_json(tmp_path, monkeypatch):
    d = P.probe_dir(tmp_path)
    (d / "segments").mkdir(parents=True)
    (d / "segments" / "seg-00.npy").write_bytes(b"\x93NUMPY fake")
    (d / "check.json").write_text(json.dumps(_check_rec()))
    before = {str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")}
    monkeypatch.setattr(P, "require_on_main", lambda: None)
    monkeypatch.setattr(P, "machine_state", lambda: {"render": 0, "torch": 0, "idle": True, "pids": {}})
    seen = {}

    def runner(a, check):
        seen["config"] = check["config"]
        return _time_rec()
    a = P.argparse.Namespace(data_dir=str(tmp_path), steps=200, code="/c", models="/m")
    P.cmd_time(a, runner=runner)
    new = {str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")} - before
    assert len(new) == 1 and all(n.endswith(".json") and "/time-" in n for n in new)
    assert seen["config"] == {"encoder": "mps", "clip": "native"}
    rec = json.loads((tmp_path / next(iter(new))).read_text())
    assert rec["check_sha256"] == P.file_sha(d / "check.json")
    monkeypatch.setattr(P, "machine_state", lambda: {"render": 0, "torch": 1, "idle": False, "pids": {"torch": [9]}})
    with pytest.raises(SystemExit):                                         # never two MPS jobs
        P.cmd_time(a, runner=runner)


def test_time_refuses_after_a_cpu_only_check(tmp_path, monkeypatch):
    d = P.probe_dir(tmp_path)
    d.mkdir(parents=True)
    (d / "check.json").write_text(json.dumps(_check_rec(cpu_only=["MPS gradients do not match"])))
    monkeypatch.setattr(P, "require_on_main", lambda: None)
    monkeypatch.setattr(P, "machine_state", lambda: {"render": 0, "torch": 0, "idle": True, "pids": {}})
    with pytest.raises(SystemExit):
        P.cmd_time(P.argparse.Namespace(data_dir=str(tmp_path), steps=200), runner=lambda a, c: {})
    assert sorted(p.name for p in d.iterdir()) == ["check.json"]


# --- read ---------------------------------------------------------------------------------------------------------------

def test_the_rate_comes_only_from_an_idle_block():
    busy, idle = ("time-1.json", _time_rec(idle=False, rate=1.0)), ("time-2.json", _time_rec(idle=True, rate=2.0))
    assert P.quoted_block([busy, idle])[0] == "time-2.json"
    assert P.quoted_block([busy]) is None
    assert P.quoted_block([("time-3.json", _time_rec(done=150))]) is None
    with pytest.raises(SystemExit):
        P.reading(_check_rec(), [busy])
    r = P.reading(_check_rec(), [busy, idle])
    assert r["code"] == "PP-mps" and r["quoted"] == "time-2.json" and r["rate"]["rate"] == pytest.approx(2.0)
    assert r["projections"]["h_175000"] == pytest.approx(175000 / 2 / 3600)
    assert r["blocks_labelled"]["time-1.json"]["long"] is False
    assert r["rate_note"] == P.RATE_NOTE and "resample" in P.RATE_NOTE


def test_reading_codes():
    idle = ("time-2.json", _time_rec())
    assert P.reading(_check_rec(fallbacks=["clip_grad_norm_ with foreach=False"]), [idle])["code"] == \
        "PP-mps-fallback"
    assert P.reading(_check_rec(nonfinite_mps_five=1), [idle])["code"] == "PP-unstable"
    assert P.reading(_check_rec(), [("time-2.json", _time_rec(nonfinite=(57,)))])["code"] == "PP-unstable"
    r = P.reading(_check_rec(cpu_only=["grads"], config={"encoder": None, "clip": None}), [])
    assert r["code"] == "PP-cpu-only" and r["cpu_rate"] == 0.1
    assert r["cpu_projections"]["s_per_1000"] == pytest.approx(10000)
    assert P.reading(_check_rec(anomaly=["pin"]), [])["code"] == "PP-anomaly"
    oom = _time_rec(done=37, error={"kind": "oom", "error": "MPS backend out of memory", "op": None})
    r = P.reading(_check_rec(), [("time-4.json", oom)])
    assert r["code"] == "PP-cpu-only" and "out of memory" in r["why"][0]
    anomalous = dict(_time_rec(), anomaly=["1 weights files opened for writing"])
    assert P.reading(_check_rec(), [("time-5.json", anomalous)])["code"] == "PP-anomaly"


# --- the declaration ----------------------------------------------------------------------------------------------------

def test_the_declaration_is_in_the_ledger():
    e = _entry()
    d = e[P.KEY]
    assert d["plan"].startswith(P.PLAN) and (REPO / P.PLAN).exists()
    assert d["codes"]["order"] == list(P.CODES)
    assert set(d["codes"]["table"]) == set(P.CODES)
    assert d["tolerances"]["relative"] == P.TOL and d["tolerances"]["calibration_multiple"] == P.CALIB_MULT
    assert d["tolerances"]["per_tensor_floor"] == P.PER_TENSOR_FLOOR
    assert d["tolerances"]["calibration_cap"] == P.CALIB_CAP == 0.1
    assert d["timing"]["resample"] == P.RATE_NOTE
    assert d["pins"]["files"] == P.LOUDAR_FILES
    assert d["pins"]["functions"] == {f"{f} {q}": s for (f, q), s in P.LOUDAR_FUNCS.items()}
    assert d["segments"]["seed"] == P.SEED and d["segments"]["n"] == P.N_SEGMENTS and d["segments"]["samples"] == P.SEG
    assert d["hours"]["library_order"] == list(P.LIBRARY_ORDER) and d["hours"]["goat_order"] == list(P.GOAT_ORDER)
    assert d["terms"] == P.TERMS
    ks = list(e)
    assert all(ks.index(k) > ks.index(P.KEY) for k in ks if k.startswith(P.KEY + "_"))


def test_the_name_is_free_of_loudars_prefix():
    from learn import scratch_loudar as SL

    assert not P.KEY.startswith(SL.KEY_PREFIX)
    assert not P.OUT_SUB.startswith("fs/loudar")
