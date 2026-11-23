"""LOUDAR's runs (`learn/loudar_run.py`, `docs/scratch-search-plan.md` section 13): the pure rules (the input length,
the three seeds, the two settings, the input refusal, the sets' keys, the checkpoint's globals, the cost stop, the
gate's reading) on the light CI runner (no numpy). With numpy: `loudar_gain`, `logmel` and `floored` equal the codec
row's; the pickle globals are listed without unpickling. The module imports nothing from this project, and no test
imports LOUDAR."""
import ast
import collections
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
    assert rel["opt_latent_params.operator_updates_per_step"] == 1 and pap["opt_latent_params.optimizer_operator.lr"] == 1e-4
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


def test_the_checkpoints_globals():
    allow, why = LR.globals_refusal(["torch._utils._rebuild_tensor_v2", "collections.OrderedDict",
                                     "torch.FloatStorage", "omegaconf.dictconfig.DictConfig",
                                     "omegaconf.base.ContainerMetadata", "builtins.dict"])
    assert why is None and allow == ["omegaconf.base.ContainerMetadata", "omegaconf.dictconfig.DictConfig"]
    _, why = LR.globals_refusal(["torch.FloatStorage", "typing.Any"])
    assert "typing.Any" in why and "stop and ask" in why
    _, why = LR.globals_refusal(["os.system"])
    assert why


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
    assert "collections.Counter" in LR.globals_refusal(got)[1]


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
    assert r["passed"] and r["direction"] == 6 and r["reproduction_db"] == pytest.approx(0.5)
    assert r["authors_gain_db"] == pytest.approx(3.0) and r["tolerance_fraction_of_gain"] == pytest.approx(1 / 3)
    d["ours"]["paper"] = [3.2] * 6
    assert LR.gate_reading(d)["setting"] == "paper"
    d["ours"] = {"released": [4.2] * 6}
    assert not LR.gate_reading(d)["reproduction_ok"] and not LR.gate_reading(d)["passed"]
    d["ours"] = {"released": [6.5, 6.5, 3, 3, 3, 3]}
    assert LR.gate_reading(d)["direction"] == 4 and not LR.gate_reading(d)["direction_ok"]
    d = {"distorted": [6.0] * 6, "authors": [3.0] * 6, "ours": {"released": [3.0] * 6}, "cut": [4.1] * 6,
         "from_full": [3.0] * 6}
    assert not LR.gate_reading(d)["length_ok"]
    with pytest.raises(SystemExit):
        LR.gate_reading({"distorted": [1], "authors": [1], "ours": {}})


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


def test_pickle_globals_of_a_real_torch_style_save(tmp_path):
    torch = pytest.importorskip("torch")
    p = tmp_path / "ck.pt"
    torch.save({"ema": collections.OrderedDict(w=torch.zeros(2))}, p)
    allow, why = LR.globals_refusal(LR.pickle_globals(p))
    assert why is None and allow == []
