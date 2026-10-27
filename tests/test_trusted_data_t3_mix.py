"""ROADMAP step (a), D_F5mix (`learn/trusted_data_t3_mix.py`): the drift check in place of T0's lists hash, the mix
input (D_mix's zeroing, unaugmented), the paired FS5 read and its stop rule, the rows, the CLI and the chain. Fakes
only: no data files, no renders, no training."""

import argparse
import pathlib
import random
import re

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import direct_stems as DS  # noqa: E402
from learn import full_space as F  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import trusted_data as T  # noqa: E402
from learn import trusted_data_t3 as T3  # noqa: E402
from learn import trusted_data_t3_mix as M  # noqa: E402
from learn import trusted_data_t3_r as R  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHAIN = ROOT / "docs" / "trusted-data-t3-mix-chain.sh"


# --- the drift check -------------------------------------------------------------------------------------------------

def _lists(verified=("a", "b", "c"), unusable=()):
    return {"dis": {d: {"verdict": "verified" if d in verified else "excluded"} for d in ("a", "b", "c", "d")},
            "unusable_sections": list(unusable)}


T2_EX = [{"i": 1, "di": "a", "section": "s1", "others": [{"di": "b"}]},
         {"i": 2, "di": "b", "section": "s2", "others": []},
         {"i": 3, "di": "c", "section": "s3", "others": [{"di": "a"}, {"di": "c"}]}]
FROZEN = ["p1", "p2", "p3"]


def test_drift_ok_when_lists_only_add():
    d = M.lists_drift([1, 2, 3], FROZEN, T2_EX, _lists(), FROZEN + ["signs6"])
    assert d["ok"] and d["stale"] == [] and d["vreal_lost"] == [] and d["vreal_added"] == ["signs6"]


@pytest.mark.parametrize("tr,why", [
    (_lists(verified=("b", "c")), "the target's DI is no longer verified"),
    (_lists(unusable=("s1",)), "the section is no longer usable"),
    (_lists(verified=("a", "c")), "an other guitar's DI is no longer verified")])
def test_drift_refuses_an_example_no_longer_trusted(tr, why):
    d = M.lists_drift([1], FROZEN, T2_EX, tr, FROZEN)
    assert not d["ok"] and d["stale"] == [(1, why)]


def test_drift_refuses_a_lost_vreal_member_and_an_unknown_example():
    d = M.lists_drift([1, 9], FROZEN, T2_EX, _lists(), ["p1", "p3"])
    assert not d["ok"] and d["vreal_lost"] == ["p2"] and d["stale"] == [(9, "not in T2's plan")]


def test_drift_ignores_examples_not_asked_for():
    assert M.lists_drift([2], FROZEN, T2_EX, _lists(verified=("b",)), FROZEN)["ok"]   # 1 and 3 dropped by F5


def test_canon_compares_nan_equal():
    assert M.canon({"x": [float("nan"), 1.0]}) == M.canon({"x": [float("nan"), 1.0]})
    assert M.canon({"x": [0.5]}) != M.canon({"x": [0.25]})


# --- the input: D_mix's zeroing, unaugmented ----------------------------------------------------------------------------

def test_model_input_dmix_zeroes_the_stem_and_its_loudness():
    rng = np.random.default_rng(0)
    s8, m8 = (rng.integers(40, 200, size=(96, 446)).astype(np.uint8) for _ in range(2))
    x, c = DS.model_input(s8, m8, -15.0, -11.0, "B", "pr12", "clean", M.INPUT_ARM)
    assert np.all(x[0] == 0) and np.any(x[1] != 0)
    assert c[-2] == 0 and c[-1] != 0
    xs, cs = DS.model_input(s8, m8, -15.0, -11.0, "B", "pr12", "clean", T.MODEL_ARM)    # D_F5's: the mirror
    assert np.all(xs[1] == 0) and np.any(xs[0] != 0) and cs[-1] == 0
    assert not np.array_equal(x[1], xs[0])                              # the mix, not the stem


def test_torch_checks(tmp_path):
    """The torch-dependent checks (`tests/torch_checks_t3_mix.py`; run there with the torch venv's python, which has
    no pytest)."""
    pytest.importorskip("torch")
    from tests import torch_checks_t3_mix as TC

    TC.check_arm_data_inputs_unaugmented(tmp_path)
    TC.check_net_reads_the_input(tmp_path)
    TC.check_train_refuses_another_arm_or_seed()


def test_same_examples_compares_dropped_ids_and_counts():
    ref = {"dropped": [5, 3], "train": 10, "early_stop": 4}
    assert M.same_examples(ref, [3, 5], 10, 4) is None
    assert "dropped ids differ" in M.same_examples(ref, [3, 6], 10, 4)
    assert "dropped ids differ" in M.same_examples(ref, [3], 10, 4)
    assert "examples" in M.same_examples(ref, [3, 5], 11, 4)
    assert "dropped ids differ" in M.same_examples({}, [1], 10, 4)


# --- the paired FS5 read ------------------------------------------------------------------------------------------------

def _fake_pair(n=240, secs=8, seed=5):
    """Two arms on the same FS-like examples: arm a reads reverb's switch, a PR12 knob, the amp and the left mic;
    arm b reads nothing (noise or the constant)."""
    rng = random.Random(seed)
    D = F.by_name()
    jr = F.SW.index("reverb/reverbActive")
    jb = F.CONT.index(next(c for c in F.CONT if D[c].module == "pr12Amp"))
    ex_a, ex_b, info = {}, {}, {}
    for i in range(n):
        amp = F.AMPS[i % 3]
        cm_, sm_, km_ = (m.astype(np.float32) for m in F.cell_masks(amp))
        c = np.array([rng.random() for _ in F.CONT], np.float32)
        s = np.array([float(rng.random() < 0.5) for _ in F.SW], np.float32)
        k = np.array([rng.randrange(10) for _ in F.CAT])
        lab = {"c": c, "cm": cm_, "s": s, "sm": sm_, "k": k, "km": km_}
        a2a, a2b = np.full(len(F.CONT), 0.5), np.full(len(F.CONT), 0.5)
        a2a[jb] = c[jb]
        swa, swb = np.array([rng.random() for _ in F.SW]), np.array([rng.random() for _ in F.SW])
        swa[jr] = 0.8 if s[jr] else 0.2
        mica = [np.eye(10)[k[0]], np.full(10, 0.1)]
        ex_a[i] = {"a2": a2a, "sw_p": swa, "mic_p": mica, "amp_p": np.eye(3)[F.AMPS.index(amp)], **lab}
        ex_b[i] = {"a2": a2b, "sw_p": swb, "mic_p": [np.full(10, 0.1) for _ in F.CAT],
                   "amp_p": np.eye(3)[(F.AMPS.index(amp) + 1) % 3], **lab}
        info[i] = {"section": f"sec{i % secs}", "cell": (amp, "clean"), "amp": amp}
    return ex_a, ex_b, info, F.CONT[jb]


def test_auc_step_and_jackknife():
    rng = random.Random(2)
    y = [rng.random() < 0.5 for _ in range(240)]
    g = [k % 8 for k in range(240)]
    good = [float(v) + rng.gauss(0, 0.5) for v in y]
    s = M.auc_step(y, good, [rng.random() for _ in y], g)
    assert s["sections"] == 8 and s["lo"] > 0 and M.favours("above", s) == "a"
    same = M.auc_step(y, good, good, g)
    assert same["point"] == 0 and same["lo"] == pytest.approx(0) and M.favours("above", same) is None
    assert M.auc_step([1, 1, 0, 0], [0.9, 0.8, 0.1, 0.2], [0.1, 0.2, 0.3, 0.4], ["a", "a", "b", "b"])["lo"] is None
    assert M.jackknife(lambda drop: 1.0, ["x"])["lo"] is None          # one section: no interval


@pytest.mark.parametrize("better,s,who", [
    ("below", {"lo": -0.2, "hi": -0.01}, "a"), ("below", {"lo": 0.01, "hi": 0.2}, "b"),
    ("below", {"lo": -0.1, "hi": 0.1}, None), ("above", {"lo": 0.01, "hi": 0.2}, "a"),
    ("above", {"lo": -0.2, "hi": -0.01}, "b"), ("above", {"lo": None, "hi": None}, None)])
def test_favours(better, s, who):
    assert M.favours(better, s) == who


def test_paired_rows_cover_every_head_and_find_what_arm_a_reads():
    ex_a, ex_b, info, knob = _fake_pair()
    rows = M.paired_rows(ex_a, ex_b, info)
    assert len(rows) == len(F.CONT) + len(F.SW) + len(F.CAT) + 1 == 116
    by = {r["name"]: r for r in rows}
    assert by["reverb/reverbActive"]["favours"] == "a" and by["reverb/reverbActive"]["kind"] == "switch"
    assert by[knob]["favours"] == "a" and by[knob]["hi"] < 0
    assert by[R.AMP_NAME]["favours"] == "a" and by[R.AMP_NAME]["point"] == pytest.approx(1.0)
    assert by["cabParameters/leftMicType"]["favours"] == "a"
    assert sum(r["favours"] == "b" for r in rows) <= 12                  # noise heads mostly hold 0
    flipped = {r["name"]: r for r in M.paired_rows(ex_b, ex_a, info)}
    assert flipped["reverb/reverbActive"]["favours"] == "b"


def test_paired_rows_refuse_different_examples_or_labels():
    ex_a, ex_b, info, _ = _fake_pair(n=24)
    with pytest.raises(SystemExit, match="examples differ"):
        M.paired_rows(ex_a, {i: v for i, v in ex_b.items() if i}, info)
    ex_b[0] = {**ex_b[0], "s": 1 - ex_b[0]["s"]}
    with pytest.raises(SystemExit, match="labels differ"):
        M.summary_rows(ex_a, ex_b, info)


def test_summary_rows_and_their_directions():
    ex_a, ex_b, info, _ = _fake_pair()
    s = M.summary_rows(ex_a, ex_b, info)
    assert list(s) == list(M.SUMMARY)
    assert s["knobs"]["better"] == "below" and s["knobs"]["point"] < 0
    assert s["switches"]["point"] > 0 and s["switches"]["n"] == len(F.SW) and s["switches"]["left_out"] == []
    assert s["switches"]["lo"] is not None
    assert s["amp choice"]["favours"] == "a" and s["mics"]["point"] > 0
    assert all(v["sections"] == 8 for v in s.values())
    same = M.summary_rows(ex_a, ex_a, info)
    assert all(v["point"] == pytest.approx(0) for v in same.values()) and not any(map(M.reliably_worse, same.values()))
    worse = M.summary_rows(ex_b, ex_a, info)
    assert M.reliably_worse(worse["amp choice"])


def test_summary_switches_drop_a_switch_undefined_in_a_fold_and_keep_the_interval():
    ex_a, ex_b, info, _ = _fake_pair()
    j = F.SW.index("delay/delayActive")
    for i in ex_a:                                   # scored in sec0 and sec1 only; sec1 holds one class
        sec = info[i]["section"]
        sm = np.array(ex_a[i]["sm"])
        sm[j] = 1.0 if sec in ("sec0", "sec1") else 0.0
        sw = np.array(ex_a[i]["s"])
        if sec == "sec1":
            sw[j] = 1.0
        for ex in (ex_a, ex_b):
            ex[i] = {**ex[i], "sm": sm, "s": sw}
    s = M.summary_rows(ex_a, ex_b, info)["switches"]
    assert s["left_out"] == ["delay/delayActive"] and s["n"] == len(F.SW) - 1
    assert s["lo"] is not None and s["hi"] is not None                  # the row keeps its interval


# --- the rows, the outputs, the CLI ----------------------------------------------------------------------------------------

def test_contrasts_put_the_unconfounded_input_first():
    c = M.contrasts()
    assert next(iter(c.values())) == (M.MIX_ARM, M.NOAUG_ARM)          # both unaugmented: only the input differs
    assert set(c.values()) >= {(M.MIX_ARM, T3.FULL), (M.NOAUG_ARM, T3.FULL), (M.MIX_ARM, T3.CORE), (M.MIX_ARM, "S"),
                               (M.MIX_ARM, T3.CONST), (T3.FULL, T3.CORE), (R.R_ARM, T3.CORE)}
    assert M.PAIRS["the input"] == (M.MIX_ARM, M.NOAUG_ARM) and list(M.PAIRS)[0] == "the input"
    assert M.INPUT_OF == {M.MIX_ARM: "Dmix", M.NOAUG_ARM: "Dstem"}


def test_render_count_is_five_per_group():
    assert M.renders_needed(33) == 165                                  # 11 parts x 3 amps; 1 priming + 2 arms x 2


def test_outputs_stay_outside_t3(tmp_path):
    assert M.out_dir(tmp_path) == tmp_path / "t3-mix"
    assert M.run_path(tmp_path, M.NOAUG_ARM, 20261042) == tmp_path / "t3-mix" / "runs" / "D_F5-noaug-20261042.json"
    assert "t3" not in M.out_dir(tmp_path).relative_to(tmp_path).parts


def test_cli_scopes_shard_arm_and_seed():
    for argv in (["r0", "--shard", "1/3"], ["train"], ["train", "--seed", "20261042"], ["train", "--arm", "D_F5mix"],
                 ["train", "--arm", "D_F5", "--seed", "20261042"], ["fit", "--seed", "20261042"],
                 ["r0", "--arm", "D_F5mix"], ["r2"]):
        with pytest.raises(SystemExit):
            M.main(argv)


def test_real_runs_need_the_ledger_amendment(monkeypatch):
    monkeypatch.setattr(M.V, "require_real", lambda a: None)
    M.require_mix(argparse.Namespace(smoke=False, out=None))           # declared in docs/dev-test-ledger.json
    monkeypatch.setattr(M, "LEDGER_MARK", "no such declaration")
    with pytest.raises(SystemExit, match="ledger"):
        M.require_mix(argparse.Namespace(smoke=False, out=None))


def test_vreal_render_counts_under_the_machine_cap():
    cmd = "/x/.venv/bin/python -u -m learn.trusted_data_t3_mix vreal-render --shard 0/3"
    assert any(re.search(p, cmd) for p in LO.RENDERS)
    for other in ("report", "r0", "train --seed 20261042", "vreal-predict"):
        assert not any(re.search(p, f"/x/python -m learn.trusted_data_t3_mix {other}") for p in LO.RENDERS)


def test_fs_tensors_default_stays_d_stem():
    import inspect

    assert inspect.signature(T3.fs_tensors).parameters["model_arm"].default is None
    assert T.MODEL_ARM == "Dstem" and M.INPUT_ARM == "Dmix" and "Dmix" not in DS.STEM_ARMS


# --- the chain -------------------------------------------------------------------------------------------------------------

def _code_lines():
    return [ln.split("#", 1)[0].rstrip() for ln in CHAIN.read_text().splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def test_chain_never_waits_bare_on_caffeinate():
    lines = _code_lines()
    caf = [ln for ln in lines if "caffeinate" in ln]
    assert caf and all(ln.rstrip().endswith("&!") for ln in caf)     # disowned: no job for a wait to hang on
    waits = [m for ln in lines for m in re.findall(r"\bwait\b[^;&|]*", ln)]
    assert waits and all(re.fullmatch(r"wait \$\w+", w.strip()) for w in waits)   # only explicit pids


def test_chain_order_and_no_stop_rule():
    text = CHAIN.read_text()
    assert "setopt no_bg_nice" in text and M.LEDGER_MARK in text and "NOT launched" in text
    assert "PENDING THE USER'S YES" in text
    order = [" check ", "train --arm", " fit ", " r0 ", "vreal-predict", "vreal-render --shard", " report "]
    pos = [text.index(f"${{TM[@]}}{o}" if o.startswith(" ") else o) for o in order]
    assert pos == sorted(pos)
    assert "VREAL: RUN" not in text and "exit 0" not in text             # V-real runs whatever FS5 shows
    assert "for arm in D_F5mix D_F5-noaug" in text
    assert "--shard $k/3" in text and "for k in 0 1 2" in text           # at most 3 render processes
    assert "for seed in 20261042 20261043" in text
    assert len(re.findall(r"\$TORCH_PY", text)) == 4                  # train, fit, r0, vreal-predict
