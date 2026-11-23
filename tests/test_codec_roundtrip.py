"""The codec ceiling's round trips (`learn/codec_roundtrip.py`, `docs/scratch-search-plan.md` section 12): the pure
rules (Music2Latent's input length, the decode seeds, the venv split, the weight and input refusals) run on the light
CI runner (no numpy); with numpy, `rt-id` returns its input's section exactly, `loudar_gain` matches cases worked by
hand from LOUDAR's `compute_log_rms_gated_max`, and `rt-id` and `rt-rs` run end to end on files (no codec, no torch).
The module imports nothing from this project and parses as Python 3.9 (`dac-venv`)."""
import ast
import json
import math
import pathlib

import pytest

from learn import codec_roundtrip as RT

REPO = pathlib.Path(__file__).resolve().parents[1]
SRC = REPO / "learn" / "codec_roundtrip.py"


def test_pad_len_is_music2latents_input_length():
    assert RT.pad_len(540000) == 542208 and RT.pad_len(492000) == 493056
    for n in (1537, 4096 + 1536, 4096 + 1537, 100000, RT.IN_LEN, RT.SECTION):
        q = RT.pad_len(n)
        assert q >= n and (q - RT.M2L_EXTRA) % RT.M2L_HOP == 0 and q - RT.M2L_HOP < n
    assert RT.pad_len(4096 * 7 + 1536) == 4096 * 7 + 1536


def test_seed_of():
    assert RT.seed_of(0, 0) == RT.RT_SEED == 20261601
    assert RT.seed_of(1, 3) == 20261601 + 1003
    seeds = {RT.seed_of(s, j) for s in (0, 1) for j in range(47)}
    assert len(seeds) == 94 and min(seeds) > 20261412                 # above main's and the note reader's seeds


def test_the_seed_is_new():
    hits = [p.name for p in (REPO / "learn").glob("*.py") if "20261601" in p.read_text() and p != SRC]
    assert hits == []


def test_each_venv_runs_its_own_names():
    assert RT.venv_of(["rt-m2l", "rt-m2l-b", "rt-id"]) == "codec"
    assert RT.venv_of(["rt-dac", "rt-rs"]) == "dac"
    for bad in (["rt-m2l", "rt-dac"], ["rt-sony"], [], ["rt-id", "rt-rs"]):
        with pytest.raises(SystemExit):
            RT.venv_of(bad)


def test_weight_refusal():
    key = "m2l/autoencoder_inference_model_last.pth"
    sha = RT.DECLARED_SHA256[key]
    man = {"files": {key: {"sha256": sha, "size": 232976270}}}
    assert RT.weight_refusal(key, sha, man) is None
    assert "not in manifest.json" in RT.weight_refusal(key, sha, {"files": {}})
    assert "not the manifest's" in RT.weight_refusal(key, "0" * 64, man)
    other = {"files": {key: {"sha256": "1" * 64}}}
    assert "not the declared" in RT.weight_refusal(key, "1" * 64, other)    # the manifest itself must be the plan's
    yaml_key = "m2l/frontend_kwargs_last.yaml"                              # recorded at install, no declared value
    assert RT.weight_refusal(yaml_key, "2" * 64, {"files": {yaml_key: {"sha256": "2" * 64}}}) is None
    assert RT.DECLARED_SHA256["dac/weights_44khz_8kbps_0.0.1.pth"].startswith("a88eed82")


def test_input_refusal():
    rec = {"parts": {"k": {"sha256": "S"}}}
    assert RT.input_refusal(rec, "k", "S", RT.IN_LEN) is None
    assert "in.json" in RT.input_refusal(rec, "k", "T", RT.IN_LEN)
    assert "in.json" in RT.input_refusal(rec, "j", "S", RT.IN_LEN)
    assert "samples" in RT.input_refusal(rec, "k", "S", RT.SECTION)


def test_the_module_imports_nothing_from_the_project_and_parses_as_python_39():
    tree = ast.parse(SRC.read_text(), feature_version=(3, 9))
    top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    names = {a.name.split(".")[0] for n in top if isinstance(n, ast.Import) for a in n.names} | \
        {n.module.split(".")[0] for n in top if isinstance(n, ast.ImportFrom) and n.module}
    assert names <= {"__future__", "argparse", "hashlib", "json", "math", "os", "pathlib", "time"}
    every = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
        {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert "learn" not in every and "research" not in every
    unsafe = [k for k in ast.walk(tree) if isinstance(k, ast.keyword) and k.arg == "weights_only"
              and not (isinstance(k.value, ast.Constant) and k.value.value is True)]
    assert unsafe == []                                                     # never weights_only=False


def test_no_weight_is_loaded_unsafely(monkeypatch):
    monkeypatch.setenv("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
    with pytest.raises(SystemExit, match="weights_only=False"):
        RT.safe_torch()


# --- with numpy ----------------------------------------------------------------------------------------------------------

def test_rt_id_returns_the_section_exactly():
    np = pytest.importorskip("numpy")
    x = np.random.default_rng(1).standard_normal(RT.IN_LEN).astype(np.float32)
    y = RT.rt_identity(x)
    assert y.dtype == np.float32 and len(y) == RT.SECTION and np.array_equal(y, x[:RT.SECTION])
    with pytest.raises(SystemExit, match="fewer than"):
        RT.cut(x[:1000])


def test_loudar_gain_matches_a_case_worked_by_hand():
    """LOUDAR: seg 19,200, hop 4,800, `unfold` (no padding, the tail dropped), RMS floored at 1e-8, the loudest frame
    to -18 dB, linear gain 10 ** (gain / 20 + 1e-6)."""
    np = pytest.importorskip("numpy")
    x = np.zeros(28800 + 4799)                      # 3 whole frames; 4,799 tail samples dropped
    x[24000:28800] = 0.1                            # only in frame 3 (9,600 to 28,800): 4,800 samples of 0.1
    x[28800:] = 10.0                                # in the dropped tail: never read
    rms = math.sqrt(4800 * 0.01 / 19200)            # 0.05
    want = 10 ** ((-18 - 20 * math.log10(rms)) / 20 + 1e-6)
    assert RT.loudar_gain(x) == pytest.approx(want, rel=1e-12)
    x2 = np.zeros(19200)
    x2[:9600] = 0.2                                 # one frame, RMS 0.2 / sqrt(2)
    assert RT.loudar_gain(x2) == pytest.approx(10 ** ((-18 - 20 * math.log10(0.2 / math.sqrt(2))) / 20 + 1e-6))
    assert RT.loudar_gain(np.zeros(19200)) == pytest.approx(10 ** ((-18 + 160) / 20 + 1e-6))   # the 1e-8 floor
    with pytest.raises(ValueError):
        RT.loudar_gain(np.zeros(19199))
    y = np.random.default_rng(2).standard_normal(RT.SECTION) * 0.05
    g = RT.loudar_gain(y)
    fr = np.lib.stride_tricks.sliding_window_view(y * g, 19200)[::4800]
    assert 20 * math.log10(np.sqrt((fr ** 2).mean(1)).max()) == pytest.approx(-18 + 20e-6, abs=1e-9)


def _inputs(tmp_path, np, n=2):
    inp = tmp_path / "in"
    inp.mkdir()
    parts = {}
    for j in range(n):
        x = (np.random.default_rng(j).standard_normal(RT.IN_LEN) * 0.1).astype(np.float32)
        np.save(inp / f"part{j}.npy", x)
        parts[f"part{j}"] = {"sha256": RT.file_sha(inp / f"part{j}.npy")}
    (inp / "in.json").write_text(json.dumps({"parts": parts}))
    models = tmp_path / "models"
    models.mkdir()
    (models / "manifest.json").write_text(json.dumps({"files": {}}))
    return inp, models


def test_rt_id_and_rt_rs_end_to_end(tmp_path):
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    inp, models = _inputs(tmp_path, np)
    out = tmp_path / "out"
    RT.main(["--inp", str(inp), "--out", str(out), "--codecs", "rt-id", "--models", str(models)])
    RT.main(["--inp", str(inp), "--out", str(out), "--codecs", "rt-rs", "--models", str(models)])
    for j in range(2):
        x = np.load(inp / f"part{j}.npy")
        assert np.array_equal(np.load(out / "rt-id" / f"part{j}.npy"), x[:RT.SECTION])
        rs = np.load(out / "rt-rs" / f"part{j}.npy")
        assert rs.dtype == np.float32 and len(rs) == RT.SECTION and np.isfinite(rs).all()
    rec = json.loads((out / "roundtrip-codec.json").read_text())
    assert rec["venv"] == "codec" and rec["device"] == "cpu" and rec["threads"] == 4 and rec["seeds"] == {}
    assert rec["in_json_sha256"] == RT.file_sha(inp / "in.json") and set(rec["parts"]["rt-id"]) == {"part0", "part1"}
    with pytest.raises(SystemExit, match="never overwritten"):
        RT.main(["--inp", str(inp), "--out", str(out), "--codecs", "rt-id", "--models", str(models)])


def test_a_changed_input_is_refused(tmp_path):
    np = pytest.importorskip("numpy")
    inp, models = _inputs(tmp_path, np, n=1)
    np.save(inp / "part0.npy", np.zeros(RT.IN_LEN, np.float32))
    with pytest.raises(SystemExit, match="not the file in.json names"):
        RT.main(["--inp", str(inp), "--out", str(tmp_path / "out"), "--codecs", "rt-id", "--models", str(models)])


def test_hf_home_is_set_in_code(tmp_path):
    models = tmp_path / "models"
    env = {}
    with pytest.raises(SystemExit, match="no Hugging Face cache"):
        RT.set_hf_env(models, env)
    (models / "hf").mkdir(parents=True)
    assert RT.set_hf_env(models, env) == models / "hf"
    assert env == {"HF_HOME": str(models / "hf"), "HF_HUB_OFFLINE": "1"}
    assert RT.set_hf_env(models, dict(env))                                 # the same HF_HOME is accepted
    with pytest.raises(SystemExit, match="unset it"):
        RT.set_hf_env(models, {"HF_HOME": str(tmp_path / "elsewhere")})
