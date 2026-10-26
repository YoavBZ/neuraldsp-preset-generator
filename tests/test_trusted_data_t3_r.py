"""T3's F5 follow-up R (`learn/trusted_data_t3_r.py`): R0's statistics and readability rule, the heads written at S,
R1's answers rebuilt from F5's stored readout, the rows, the CLI and the chain. Fakes only: no data files, no renders,
no training."""

import argparse
import json
import math
import pathlib
import random
import re

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import direct_stems as DS  # noqa: E402
from learn import every_control as EC  # noqa: E402
from learn import full_space as F  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import trusted_data_t3 as T3  # noqa: E402
from learn import trusted_data_t3_r as R  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHAIN = ROOT / "docs" / "trusted-data-t3-r-chain.sh"


# --- the statistics -----------------------------------------------------------------------------------------------

def test_auc_ranks_and_ties():
    assert R.auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == 1.0
    assert R.auc([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]) == 0.0
    assert R.auc([0, 1, 0, 1], [0.5, 0.5, 0.5, 0.5]) == 0.5           # ties count half
    assert R.auc([1, 1, 1], [0.1, 0.2, 0.3]) is None                  # one class


def test_jackknife_auc_interval():
    rng = random.Random(1)
    y = [rng.random() < 0.5 for _ in range(240)]
    g = [k % 8 for k in range(240)]
    strong = R.jackknife_auc(y, [float(v) + rng.gauss(0, 0.5) for v in y], g)
    assert strong["sections"] == 8 and strong["lo"] < strong["point"] < strong["hi"] and strong["lo"] > 0.5
    noise = R.jackknife_auc(y, [rng.random() for _ in y], g)
    assert noise["lo"] < 0.5 and not R.readable("switch", noise)[0]
    one = R.jackknife_auc(y, [rng.random() for _ in y], [0] * len(y))
    assert one["lo"] is None and one["point"] is not None             # one section: no interval
    # a fold that leaves one class: no interval
    assert R.jackknife_auc([1, 1, 0, 0], [0.9, 0.8, 0.1, 0.2], ["a", "a", "b", "b"])["lo"] is None


def test_section_t_clusters_by_section():
    sec = {i: f"s{i % 4}" for i in range(40)}
    s = R.section_t({i: -0.1 + 0.01 * (i % 4) for i in range(40)}, sec)
    assert s["sections"] == 4 and s["point"] == pytest.approx(-0.085) and s["hi"] < 0
    assert R.section_t({0: 1.0, 4: 2.0}, sec)["lo"] is None           # one section
    assert R.section_t({}, sec)["point"] is None


@pytest.mark.parametrize("kind,s,ok", [
    ("switch", {"lo": 0.52, "hi": 0.7}, True), ("switch", {"lo": 0.45, "hi": 0.7}, False),
    ("switch", {"lo": 0.2, "hi": 0.4}, False),                        # below chance: the wrong direction
    ("continuous", {"lo": -0.1, "hi": -0.01}, True), ("continuous", {"lo": -0.1, "hi": 0.01}, False),
    ("continuous", {"lo": 0.01, "hi": 0.1}, False),
    ("accuracy", {"lo": 0.01, "hi": 0.2}, True), ("accuracy", {"lo": -0.01, "hi": 0.2}, False),
    ("accuracy", {"lo": None, "hi": None}, False)])
def test_readable_rule(kind, s, ok):
    assert R.readable(kind, s)[0] is ok


def test_family_of_name():
    assert R.family_of_name("pr12Amp/springOn") == "spring"
    assert R.family_of_name("reverb/reverbActive") == "time_effects"
    assert R.family_of_name("pr12Amp/pr12Reverb") == "spring"
    assert R.family_of_name("cabParameters/rightCabActive") == "today"
    assert {R.family_of_name(n) for n in F.CONT + F.SW + F.CAT} <= set(R.FAMILY_ORDER)


# --- R0's table on fakes ---------------------------------------------------------------------------------------------

def _fake_fs(n=180, secs=6, seed=3):
    """FS-like examples: reverb's switch and the PR12 bass knob are read; every other head is noise or the constant."""
    rng = random.Random(seed)
    D = F.by_name()
    jr, jb = F.SW.index("reverb/reverbActive"), F.CONT.index(next(c for c in F.CONT if D[c].module == "pr12Amp"))
    ex, info = {}, {}
    for i in range(n):
        amp = F.AMPS[i % 3]
        cm_, sm_, km_ = (m.astype(np.float32) for m in F.cell_masks(amp))
        c = np.array([rng.random() for _ in F.CONT], np.float32)
        s = np.array([float(rng.random() < 0.5) for _ in F.SW], np.float32)
        k = np.array([rng.randrange(10) for _ in F.CAT])
        a2 = np.full(len(F.CONT), 0.5)
        a2[jb] = c[jb]                                                 # read exactly
        swp = np.array([rng.random() for _ in F.SW])
        swp[jr] = 0.8 if s[jr] else 0.2
        ex[i] = {"a2": a2, "sw_p": swp, "mic_p": [np.full(10, 0.1) for _ in F.CAT],
                 "amp_p": np.eye(3)[F.AMPS.index(amp)], "c": c, "cm": cm_, "s": s, "sm": sm_, "k": k, "km": km_}
        info[i] = {"section": f"sec{i % secs}", "cell": (amp, "clean"), "amp": amp}
    const = {(a, "clean"): {"cont": np.full(len(F.CONT), 0.5), "sw": [False] * len(F.SW), "mics": [0, 0]}
             for a in F.AMPS}
    return ex, info, const, F.CONT[jb]


def test_r0_rows_cover_every_head_and_apply_the_rule():
    ex, info, const, knob = _fake_fs()
    rates = {n: 0.5 for n in F.SW}
    rows = R.r0_rows(ex, info, const, rates, "pr12")
    assert len(rows) == len(F.CONT) + len(F.SW) + len(F.CAT) + 1 == 116
    by = {r["name"]: r for r in rows}
    assert by["reverb/reverbActive"]["readable"] and by["reverb/reverbActive"]["point"] == 1.0
    assert by[knob]["readable"] and by[knob]["hi"] < 0
    assert by[R.AMP_NAME]["readable"] and by[R.AMP_NAME]["accuracy"] == 1.0
    assert by[R.AMP_NAME]["base_rate"] == pytest.approx(1 / 3)
    assert not by["cabParameters/leftMicType"]["readable"]             # argmax 0 == the constant's mode: no gain
    pr12_only = [r for r in rows if r["kind"] == "continuous" and F.by_name()[r["name"]].module == "pr12Amp"]
    assert all(r["n"] == 60 for r in pr12_only)                        # masked: only PR12 examples sound
    readable = {r["name"] for r in rows if r["readable"]}
    assert len(readable) <= 12                                         # noise heads mostly unreadable (~5% by chance)
    fam = R.by_family(rows)
    assert list(fam)[:2] == ["today", "amp_choice"] and sum(v["heads"] for v in fam.values()) == 116


def test_train_priors():
    lab = []
    for k in range(10):
        s = np.zeros(len(F.SW), np.float32)
        sm = np.ones(len(F.SW), np.float32)
        s[F.SW.index("reverb/reverbActive")] = float(k < 7)
        sm[F.SW.index("delay/delayActive")] = 0.0
        lab.append((None, None, s, sm, None, None))
    rates, maj = R.train_priors(lab, ["sw50r"] * 4 + ["pr12"] * 4 + ["ac20"] * 2)
    assert rates["reverb/reverbActive"] == pytest.approx(0.7) and rates["delay/delayActive"] is None
    assert maj == "pr12"                                               # a tie goes to AMPS' order


def test_unreadable_spring_switch_puts_the_whole_spring_at_S():
    rows = [{"name": n, "readable": True} for n in F.CONT + F.SW + F.CAT]
    for r in rows:
        if r["name"] in ("pr12Amp/springOn", "reverb/reverbMix", "cabParameters/leftMicType"):
            r["readable"] = False
    cont, sw, mics = R.unreadable_heads(rows)
    assert sw == ["pr12Amp/springOn"] and mics == ["cabParameters/leftMicType"]
    assert set(cont) == {"reverb/reverbMix", "pr12Amp/pr12Reverb", "pr12Amp/pr12Dwell"}


# --- R1's answer ------------------------------------------------------------------------------------------------------

def _S(amp="pr12"):
    """A stand-in for S: every table control neutral, sections on, both cabs on, time effects and springs off."""
    x = {c.path: c.neutral for c in EC.table("morgan") if c.neutral is not None}
    x[F.AMP] = EC.MORGAN_AMPS[amp]
    x[F.OUTPUT] = "3"
    for p in (("reverb", "reverbActive"), ("delay", "delayActive"), ("tremolo", "tremoloActive")):
        x[p] = "false"
    x[("pr12Amp", "pr12Reverb")] = "0"
    x[("sw50rAmp", "sw50rReverb")] = "0"
    x[("delay", "delaySync")] = "1"
    return x


def _readout(seed=5):
    rng = random.Random(seed)
    return {"a2": np.array([rng.random() for _ in F.CONT]), "sw_p": np.array([rng.random() for _ in F.SW]),
            "mics": [rng.randrange(10) for _ in F.CAT]}


def _time_rows():
    fam = {"time_effects", "spring"}
    return [{"name": n, "readable": R.family_of_name(n) not in fam} for n in F.CONT + F.SW + F.CAT]


@pytest.mark.parametrize("amp", F.AMPS)
def test_r_answer_with_time_effects_unreadable_is_f5s_family_at_S(amp):
    S = _S(amp)
    r = _readout()
    r["sw_p"][F.SW.index("reverb/reverbActive")] = 0.9                  # the head would turn reverb on
    med, b = np.full(len(F.CONT), 0.4), np.full(len(F.CONT), 0.6)
    un = R.unreadable_heads(_time_rows())
    x = R.r_answer(amp, S, r, med, b, un)
    assert x == T3.full_answer(amp, S, r, med, b, at_S=("time effects and spring",))
    assert x[("reverb", "reverbActive")] == "false"
    assert x != T3.full_answer(amp, S, r, med, b)


def test_r_answer_with_nothing_unreadable_is_f5s_answer():
    S, r = _S(), _readout()
    med, b = np.full(len(F.CONT), 0.4), np.full(len(F.CONT), 0.6)
    assert R.r_answer("pr12", S, r, med, b, ([], [], [])) == T3.full_answer("pr12", S, r, med, b)


def test_r_answer_today_and_mic_heads_at_S():
    S, r = _S(), _readout()
    S[("cabParameters", "leftMicType")] = "7"
    med, b = np.full(len(F.CONT), 0.4), np.ones(len(F.CONT))
    gain = "parameters/inputGain"
    x = R.r_answer("pr12", S, r, med, b, ([gain], [], ["cabParameters/leftMicType"]))
    assert x[("parameters", "inputGain")] == S[("parameters", "inputGain")]
    assert x[("cabParameters", "leftMicType")] == "7"
    y = T3.full_answer("pr12", S, r, med, b)
    assert y[("parameters", "inputGain")] != S[("parameters", "inputGain")]


def test_r_answer_level_at_S_under_a_readable_spring_switch_on():
    S, r = _S(), _readout()
    r["sw_p"][F.SW.index("pr12Amp/springOn")] = 0.9
    x = R.r_answer("pr12", S, r, np.zeros(len(F.CONT)), np.ones(len(F.CONT)), (["pr12Amp/pr12Reverb"], [], []))
    assert float(x[("pr12Amp", "pr12Reverb")]) == pytest.approx(F.SPRING_MIN)   # S's level 0: the least level


def test_r1_answers_rebuild_f5s_answer_or_refuse():
    S = _S()
    dirs = [("partA", "pr12", "A", "B"), ("partA", "pr12", "B", "A")]
    med = {("pr12", "clean"): np.full(len(F.CONT), 0.4)}
    table = {("pr12", "clean"): {"b": np.full(len(F.CONT), 0.5), "b_unconstrained": None, "examples": 9}}
    stored = {}
    for _, amp, sh, _ in dirs:
        r = _readout(seed=ord(sh))
        r["sw_p"][F.SW.index("delay/delayActive")] = 0.8
        diag = {"a2": [float(v) for v in r["a2"]], "sw_p": [float(v) for v in r["sw_p"]], "mics": r["mics"]}
        b, _ = DS.cell_b(table, ("pr12", "clean"), F.cell_masks("pr12")[0])
        stored[f"partA|pr12|{sh}"] = {"settings": LO.sdict(T3.full_answer(amp, S, R.stored_readout(diag), med[("pr12", "clean")], b)),
                                      "diag": diag}
    un = R.unreadable_heads(_time_rows())
    out, changed = R.r1_answers(dirs, {"partA": "clean"}, lambda a, c: S, stored, med, table, un, LO.sdict)
    assert set(out) == set(stored) and all(out[k]["held"] in ("A", "B") for k in out)
    assert all("delay/delayActive" in changed[k] for k in changed)
    assert all(out[k]["settings"]["delay/delayActive"] == "false" for k in out)
    stored["partA|pr12|A"]["settings"]["parameters/inputGain"] = "99"   # a stored answer that does not rebuild
    with pytest.raises(SystemExit, match="does not rebuild"):
        R.r1_answers(dirs, {"partA": "clean"}, lambda a, c: S, stored, med, table, un, LO.sdict)


# --- the rows, the cost, the CLI, the ledger ---------------------------------------------------------------------------

def test_r1_contrasts_hold_r1_the_time_row_and_every_f5_row():
    c = R.r1_contrasts()
    vals = list(c.values())
    assert vals[0] == (R.R_ARM, T3.CORE)
    for row in ((R.R_ARM, "S"), (R.R_ARM, T3.CONST), (R.R_ARM, T3.FULL), (R.R_ARM, R.TIME_ARM),
                (R.TIME_ARM, T3.CORE)):
        assert row in vals
    assert all(f"F5: {k}" in c and c[f"F5: {k}"] == v for k, v in T3.contrasts().items())
    assert R.TIME_ARM in T3.ANSWERS and "|" not in R.R_ARM
    names = {x for ab in vals for x in ab} - {"S", T3.D_SYN, R.R_ARM}
    assert names <= set(T3.ANSWERS)


def test_render_count_is_three_per_group():
    assert R.renders_needed(33) == 99                                   # 11 parts x 3 amps; 1 priming + 2 directions


def test_cli_scopes_shard():
    with pytest.raises(SystemExit):
        R.main(["r0", "--shard", "1/3"])
    with pytest.raises(SystemExit):
        R.main(["r2"])


def test_real_runs_need_the_ledger_amendment(monkeypatch):
    monkeypatch.setattr(R.V, "require_real", lambda a: None)
    R.require_r(argparse.Namespace(smoke=False, out=None))             # declared in docs/dev-test-ledger.json
    monkeypatch.setattr(R, "LEDGER_MARK", "no such declaration")
    with pytest.raises(SystemExit, match="ledger"):
        R.require_r(argparse.Namespace(smoke=False, out=None))


def test_outputs_stay_under_followup_r(tmp_path):
    assert R.out_dir(tmp_path) == tmp_path / "t3" / "followup-r"


def test_r1_render_counts_under_the_machine_cap():
    cmd = "/x/.venv/bin/python -u -m learn.trusted_data_t3_r r1-render --shard 0/3"
    assert any(re.search(p, cmd) for p in LO.RENDERS)
    assert not any(re.search(p, "/x/python -m learn.trusted_data_t3_r r1-report") for p in LO.RENDERS)


# --- the chain ----------------------------------------------------------------------------------------------------------

def _code_lines():
    return [ln.split("#", 1)[0].rstrip() for ln in CHAIN.read_text().splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def test_chain_never_waits_bare_on_caffeinate():
    lines = _code_lines()
    caf = [ln for ln in lines if "caffeinate" in ln]
    assert caf and all(ln.rstrip().endswith("&!") for ln in caf)     # disowned: no job for a wait to hang on
    waits = [m for ln in lines for m in re.findall(r"\bwait\b[^;&|]*", ln)]
    assert waits and all(re.fullmatch(r"wait \$\w+", w.strip()) for w in waits)   # only explicit pids


def test_chain_runs_r1_only_after_the_checks():
    text = CHAIN.read_text()
    assert "setopt no_bg_nice" in text and R.LEDGER_MARK in text
    assert text.index("r1-predict") < text.index("r1-render") < text.index("r1-report")
    assert "--shard $k/3" in text and "for k in 0 1 2" in text           # at most 3 render processes
    assert "r0" in text and "followup-r/r0.json" in text
