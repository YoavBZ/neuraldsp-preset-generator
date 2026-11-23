"""LOUDAR's runs (`learn/loudar_run.py`, `docs/scratch-search-plan.md` section 13): the pure rules (the input length,
the three seeds, the two settings, the input refusal, the sets' keys, the checkpoint's globals, the cost stop, the
gate's reading) on the light CI runner (no numpy). With numpy: `loudar_gain`, `logmel` and `floored` equal the codec
row's; the pickle globals are listed without unpickling. The module imports nothing from this project, and no test
imports LOUDAR."""
import ast
import collections
import json
import pathlib
import pickle
import zipfile

import pytest

from learn import codec_roundtrip as RT
from learn import loudar_run as LR

REPO = pathlib.Path(__file__).resolve().parents[1]
SRC = REPO / "learn" / "loudar_run.py"


def test_pad_len_equals_the_codec_rows():
    assert LR.pad_len(216000) == 218624 == 4096 * 53 + 1536
    for n in (1, 1536, 1537, 100000, 216000, 492000, 526080):
        assert LR.pad_len(n) == RT.pad_len(n)


def test_the_seeds():
    s = LR.seeds(0, 0)
    assert s == {"operator": 20261951, "run": 20261701, "decode": 20262201}
    assert LR.seeds(1, 3)["run"] == 20261701 + 1003
    every = [v for slot in (0, 1) for j in range(47) for v in LR.seeds(slot, j).values()]
    codec = {RT.seed_of(s, j) for s in (0, 1) for j in range(47)}
    assert len(every) == len(set(every)) and not set(every) & codec and min(every) > RT.RT_SEED + 46
    hits = [p.name for p in (REPO / "learn").glob("*.py") if "20261701" in p.read_text() and p != SRC]
    assert hits == []


def test_the_two_settings_differ_in_exactly_the_operators_fit():
    rel, pap = LR.flat(LR.tester_args("released")), LR.flat(LR.tester_args("paper"))
    assert set(rel) == set(pap)
    diff = {k for k in rel if rel[k] != pap[k]}
    assert diff == {"opt_latent_params.operator_updates_per_step", "opt_latent_params.optimizer_operator.lr",
                    "opt_latent_params.optimizer_operator.weight_decay"}
    assert rel["opt_latent_params.operator_updates_per_step"] == 1
    assert pap["opt_latent_params.optimizer_operator.lr"] == 1e-4
    assert rel["sampling_params.T"] == pap["sampling_params.T"] == 300 and rel["dps_params.zeta"] == 0.3
    assert rel["wandb.use"] is False and rel["dps_params.normalize_std_from_reference"] is False
    with pytest.raises(SystemExit):
        LR.tester_args("fast")


def test_the_input_refusal_and_the_sets():
    rec = {"parts": {"k": {"sha256": "S"}}}
    assert LR.input_refusal(rec, "k", "S", LR.CLIP) is None
    assert "in.json" in LR.input_refusal(rec, "k", "T", LR.CLIP)
    assert "samples" in LR.input_refusal(rec, "k", "S", LR.CLIP - 1)
    assert "non-finite" in LR.input_refusal(rec, "k", "S", LR.CLIP, finite=False)
    keys = ["bks__a", "goat__b", "panel__c", "bks__d"]
    assert LR.keys_for(keys, ["bks", "panel"]) == ["bks__a", "bks__d", "panel__c"]
    assert LR.keys_for(keys, ["goat"]) == ["goat__b"]


THIRTEEN = {"torch._utils._rebuild_tensor_v2", "torch.FloatStorage", "collections.OrderedDict",
            "omegaconf.base.ContainerMetadata", "omegaconf.base.Metadata", "omegaconf.dictconfig.DictConfig",
            "omegaconf.listconfig.ListConfig", "omegaconf.nodes.AnyNode", "builtins.dict", "builtins.list",
            "builtins.int", "collections.defaultdict", "typing.Any"}


def test_the_allowlist_is_the_pinned_thirteen():
    assert isinstance(LR.ALLOWED_GLOBALS, frozenset) and LR.ALLOWED_GLOBALS == THIRTEEN and len(THIRTEEN) == 13
    assert LR.globals_refusal(sorted(THIRTEEN)) is None
    assert LR.globals_refusal(["torch.FloatStorage", "typing.Any"]) is None
    for extra in ("posix.system", "builtins.eval", "collections.Counter", "builtins.str", "torch.load"):
        why = LR.globals_refusal(sorted(THIRTEEN) + [extra])
        assert extra in why and "stop and ask" in why
    d = json.loads((REPO / "docs/dev-test-ledger.json").read_text())
    e = next(t for t in d["tests"] if t.get("test_id") == "preset-ladder")
    assert set(e["phase_scratch_loudar_globals"]["allowlist"]) == set(LR.ALLOWED_GLOBALS)   # the ledger's pin
    assert e["phase_scratch_loudar_globals"]["torch"] == LR.TORCH_PIN == "2.10.0"
    assert e["phase_scratch_loudar_globals"]["omegaconf"] == LR.OMEGACONF_PIN == "2.3.1"
    assert e["phase_scratch_loudar_globals"]["revision"] == LR.LOUDAR_REVISION


def test_names_resolve_as_torch_resolves_them():
    assert LR.compat_name("__builtin__", "long") == "builtins.int"
    assert LR.compat_name("__builtin__", "dict") == "builtins.dict"
    assert LR.compat_name("__builtin__", "eval") == "builtins.eval"
    assert LR.compat_name("copy_reg", "_reconstructor") == "copyreg._reconstructor"
    assert LR.compat_name("omegaconf.nodes", "AnyNode") == "omegaconf.nodes.AnyNode"


def test_the_version_pins():
    assert LR.version_refusal("2.10.0", "2.3.1") is None and LR.version_refusal("2.10.0+cpu", "2.3.1") is None
    for t, o in (("2.11.0", "2.3.1"), ("2.10.0", "2.3.0"), ("2.9.1", "2.4.0")):
        assert "re-review" in LR.version_refusal(t, o)


def test_the_stand_in_for_defaultdict_returns_a_plain_dict():
    got = LR._defaultdict_as_dict(dict, extra=1)
    assert got == {} and type(got) is dict


def _zip(tmp_path, obj, protocol):
    p = tmp_path / f"ck{protocol}.pt"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("archive/data.pkl", pickle.dumps(obj, protocol=protocol))
    return p


@pytest.mark.parametrize("protocol", [2, 4])
def test_pickle_globals_lists_without_unpickling(tmp_path, protocol):
    p = _zip(tmp_path, {"ema": collections.OrderedDict(a=1), "c": collections.Counter()}, protocol)
    got = LR.pickle_globals(p)
    assert "collections.OrderedDict" in got and "collections.Counter" in got
    assert "collections.Counter" in LR.globals_refusal(got)


def test_the_listing_maps_python_2_names(tmp_path):
    p = tmp_path / "long.pt"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("archive/data.pkl", b"\x80\x02c__builtin__\nlong\nq\x00.")
    assert LR.pickle_globals(p) == ["builtins.int"] and LR.globals_refusal(LR.pickle_globals(p)) is None


def test_the_gates_projected_seconds_count_the_four_timing_and_check_runs():
    assert LR.CHECK_RUNS == {"full": 1, "cut": 3}
    assert LR.gate_seconds(100, 10) == (12 + 1) * 100 + (6 + 3) * 10      # 18 runs + the timed whole and cut clip,
    assert LR.gate_seconds(0, 1) == 9 and LR.gate_seconds(1, 0) == 13      # the seeded rerun, the zeros reference


def test_the_cost_stop():
    h = 3600
    got = LR.cost_fit(1 * h, 300)                     # 1 + 1.92 + 2 + 1.92 = 6.83 h: all three
    assert got["fits"] and got["goat"] and got["ld_stem_b"] and got["total_h"] == pytest.approx(1 + 70 * 300 / h)
    got = LR.cost_fit(1 * h, 400)                     # 1 + 2.56 + 2.67 = 6.22; + 2.56 > 8: GOAT, no ld-stem-b
    assert got["goat"] and not got["ld_stem_b"]
    got = LR.cost_fit(1 * h, 900)                     # 1 h + 23 x 15 min = 6.75 h; + GOAT 6 h > 8 h
    assert got["fits"] and not got["goat"] and not got["ld_stem_b"]
    got = LR.cost_fit(2 * h, 600)                     # 2 + 3.83 = 5.83; + 4 = 9.83 > 8
    assert got["fits"] and not got["goat"]
    assert not LR.cost_fit(7 * h, 600)["fits"]        # 7 + 3.83 > 8: stop and ask
    assert LR.cost_fit(0, 450)["window_10s_s"] == pytest.approx(1000)
    assert LR.COST_STOP_H == 8.0 and LR.THREADS == 4


def test_the_gates_reading():
    d = {"distorted": [6.0] * 6, "authors": [3.0] * 6, "ours": {"released": [3.5] * 6, "paper": [3.45] * 6},
         "cut": [3.9] * 6, "from_full": [3.5] * 6}
    r = LR.gate_reading(d)
    assert r["setting"] == "released"                 # within 0.1 dB: the released
    assert r["passed"] and r["direction_reported_only"] == 6 and r["reproduction_db"] == pytest.approx(0.5)
    assert r["authors_gain_db"] == pytest.approx(3.0) and r["tolerance_fraction_of_gain"] == pytest.approx(1 / 3)
    assert r["reproduction_per_clip_db"] == pytest.approx([0.5] * 6) and r["reproduction_clips_beyond"] == []
    d["ours"]["paper"] = [3.2] * 6
    assert LR.gate_reading(d)["setting"] == "paper"
    d["ours"] = {"released": [4.2] * 6}
    assert not LR.gate_reading(d)["reproduction_ok"] and not LR.gate_reading(d)["passed"]
    d["ours"] = {"released": [3.0, 3.0, 3.0, 3.0, 3.0, 4.1]}             # the mean within 1.0, one clip not: stop
    got = LR.gate_reading(d)
    assert abs(got["reproduction_db"]) < 1.0 and got["reproduction_clips_beyond"] == [5] and not got["passed"]
    d["ours"] = {"released": [6.5, 6.5, 3, 3, 3, 3]}                     # direction no longer gates (reported only)
    got = LR.gate_reading(d)
    assert got["direction_reported_only"] == 4 and "direction_ok" not in got
    assert got["reproduction_clips_beyond"] == [0, 1] and not got["passed"]
    d = {"distorted": [6.0] * 6, "authors": [3.0] * 6, "ours": {"released": [3.0] * 6}, "cut": [4.1] * 6,
         "from_full": [3.0] * 6}
    assert not LR.gate_reading(d)["length_ok"]
    with pytest.raises(SystemExit):
        LR.gate_reading({"distorted": [1], "authors": [1], "ours": {}})


# unit 0's stored gate record (2026-11-23, main bf484311): floored log-mel distances to the original, per example
STORED_GATE = {
    "distorted": [4.18130652801621, 3.608507853828278, 4.402654836795797, 3.949979938674983, 3.5138040133596466,
                  4.502753539148539],
    "authors": [6.287329154177563, 5.726776169342781, 5.849275764402504, 6.134666932501078, 6.05525566681113,
                6.351480810711831]}


def test_the_amended_gate_on_the_shape_of_the_stored_record():
    """The authors' own outputs fail the old direction check 6 of 6 (their gain is negative), so it cannot gate; a
    copy of ours that reproduces them clip by clip passes the amended rule."""
    d = dict(STORED_GATE, ours={"released": list(STORED_GATE["authors"])}, cut=[6.0] * 6, from_full=[5.5] * 6)
    r = LR.gate_reading(d)
    assert r["authors_direction_reported_only"] == 0 and r["authors_gain_db"] == pytest.approx(-2.041, abs=1e-3)
    assert r["tolerance_fraction_of_gain"] is None and r["passed"]


def test_the_environment_is_set_in_code(tmp_path, monkeypatch):
    for k in list(LR.ENV) + ["HF_HOME"]:
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(SystemExit, match="no Hugging Face cache"):
        LR.set_env(tmp_path)
    (tmp_path / "hf").mkdir()
    LR.set_env(tmp_path)
    import os

    assert os.environ["WANDB_MODE"] == "disabled" and os.environ["ENABLE_TORCH_COMPILE"] == "0"
    assert os.environ["TORCH_FORCE_WEIGHTS_ONLY_LOAD"] == "1" and os.environ["HF_HUB_OFFLINE"] == "1"
    monkeypatch.setenv("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
    with pytest.raises(SystemExit, match="weights_only=False"):
        LR.set_env(tmp_path)


def test_the_module_imports_nothing_from_the_project():
    tree = ast.parse(SRC.read_text())
    top = {a.name.split(".")[0] for n in tree.body if isinstance(n, ast.Import) for a in n.names} | \
        {n.module.split(".")[0] for n in tree.body if isinstance(n, ast.ImportFrom) and n.module}
    assert top <= {"__future__", "argparse", "hashlib", "json", "math", "os", "pathlib", "time"}
    every = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
        {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not every & {"learn", "research", "testing", "networks", "diff_params"}   # LOUDAR's only through build()
    unsafe = [k for k in ast.walk(tree) if isinstance(k, ast.keyword) and k.arg == "weights_only"
              and not (isinstance(k.value, ast.Constant) and k.value.value is True)]
    assert unsafe == []


# --- with numpy ----------------------------------------------------------------------------------------------------------

def test_loudar_gain_logmel_and_floored_equal_the_codec_rows():
    np = pytest.importorskip("numpy")
    from learn import scratch_codec as SC

    x = np.random.default_rng(5).standard_normal(LR.CLIP) * 0.05
    y = x + np.random.default_rng(6).standard_normal(LR.CLIP) * 0.01
    assert LR.loudar_gain(x) == RT.loudar_gain(x)
    for n in (256, 2048):
        assert np.array_equal(LR.logmel(x, n), SC.logmel(x, n))
        assert LR.floored(LR.logmel(x, n), LR.logmel(y, n)) == SC.floored(SC.logmel(x, n), SC.logmel(y, n))
    assert LR.gate_d(x, x) == pytest.approx(0, abs=1e-9)
    assert LR.gate_d(x, np.concatenate([y, np.zeros(10)])) == LR.gate_d(x, y)    # cut to the shorter


# --- with torch and omegaconf: hand-built pickles, never the checkpoint -----------------------------------------------------

def _torch():
    torch = pytest.importorskip("torch")
    pytest.importorskip("omegaconf")
    return torch


def _swap_pickle(tmp_path, torch, name, data):
    """A torch zip with its data.pkl replaced by hand-built bytes."""
    a = tmp_path / f"{name}-base.pt"
    torch.save({"x": 0}, a)
    with zipfile.ZipFile(a) as z:
        blobs = {n: z.read(n) for n in z.namelist()}
    out = tmp_path / f"{name}.pt"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
        for n, b in blobs.items():
            z.writestr(n, data if n.endswith("data.pkl") else b)
    return out


def test_an_extra_global_is_refused_at_the_listing_and_at_the_load(tmp_path):
    torch = _torch()
    import os

    for name, obj in (("system", os.system), ("eval", eval)):
        p = tmp_path / f"{name}.pt"
        torch.save({"ema": {"w": torch.zeros(1)}, "f": obj}, p)
        found = LR.pickle_globals(p)
        assert LR.globals_refusal(found)                                   # the listing stops it
        with pytest.raises(SystemExit, match="outside the pinned allowlist"):
            LR.safe_load(p)
        with pytest.raises(Exception, match="(?i)unsupported global|not an allowed global|weights only"):
            LR.guarded_load(p)                                             # and the load alone refuses it too


def test_a_defaultdict_of_dict_loads_as_a_plain_dict(tmp_path):
    torch = _torch()
    p = tmp_path / "dd.pt"
    torch.save({"ema": collections.OrderedDict(w=torch.ones(2)),
                "cfg": collections.defaultdict(dict, {"a": {"x": 1}, "b": {}})}, p)
    assert "collections.defaultdict" in LR.pickle_globals(p)
    state, _ = LR.safe_load(p)
    assert type(state["cfg"]) is dict and state["cfg"] == {"a": {"x": 1}, "b": {}}
    ema = LR.ema_only(state)
    assert list(ema) == ["w"] and torch.equal(ema["w"], torch.ones(2))


def test_a_defaultdict_whose_factory_is_not_allowed_is_refused(tmp_path):
    torch = _torch()
    p = tmp_path / "dd-str.pt"
    torch.save({"cfg": collections.defaultdict(str, {"a": "x"})}, p)
    assert "builtins.str" in LR.globals_refusal(LR.pickle_globals(p))
    with pytest.raises(Exception, match="(?i)unsupported global|not an allowed global|weights only"):
        LR.guarded_load(p)


def test_builtin_long_loads_as_int(tmp_path):
    torch = _torch()
    p = _swap_pickle(tmp_path, torch, "long", b"\x80\x02c__builtin__\nlong\nq\x00.")
    assert LR.pickle_globals(p) == ["builtins.int"]
    assert LR.safe_load(p)[0] is int


def test_a_reduce_on_typing_any_raises_and_runs_nothing(tmp_path):
    torch = _torch()
    p = _swap_pickle(tmp_path, torch, "any", b"\x80\x02ctyping\nAny\nq\x00)Rq\x01.")
    assert LR.pickle_globals(p) == ["typing.Any"]
    with pytest.raises(TypeError, match="Any cannot be instantiated"):
        LR.safe_load(p)


def test_only_a_dict_of_tensors_is_kept_as_ema():
    torch = _torch()
    assert LR.ema_only({"ema": {"w": torch.zeros(1)}, "cfg": {"x": 1}}) == {"w": torch.zeros(1)}
    for bad in ({"ema": {"w": 1.0}}, {"ema": []}, {"ema": {}}, {"cfg": {}}, []):
        with pytest.raises(SystemExit, match="dict of tensors"):
            LR.ema_only(bad)


def test_pickle_globals_of_a_real_torch_style_save(tmp_path):
    torch = _torch()
    p = tmp_path / "ck.pt"
    torch.save({"ema": collections.OrderedDict(w=torch.zeros(2))}, p)
    assert LR.globals_refusal(LR.pickle_globals(p)) is None
