"""C3's pure parts (`learn/full_controls_c3.py`, docs/full-controls-plan.md "C3 in detail"): the label sources, the masks,
the per-control hold and its tags, the families, the pooled interval, the adoption and the replacement rule, and the
wiring of C3's names into `pipeline_fix`."""

import json
import math

import pytest

pytest.importorskip("numpy")

from learn import full_controls_c3 as X  # noqa: E402
from learn import pipeline_fix as P  # noqa: E402

AMP = "ac20"
KS = {("parameters", "inputGain"), ("ac20Amp", "ac20Volume"), ("cabParameters", "rightCabActive"),
      ("cabParameters", "leftMicType")}
NEW = {("ac20EQ", "ac20EQBand1"), ("ac20EQ", "ac20EQHpf"), ("drive1", "drive1Active"), ("drive1", "drive1Drive"),
       ("compressor", "compressorMix"), ("parameters", "gateActive"), ("parameters", "gateThreshold"),
       ("cabParameters", "leftCabActive"), ("cabParameters", "leftRoomMicLevel"), ("cabParameters", "rightCabPhase")}
UNION = {AMP: set(NEW)}


# --- families -------------------------------------------------------------------------------------------------------

def test_family_partition():
    fam = {k: X.family_of(k, AMP) for k in NEW}
    assert fam[("ac20EQ", "ac20EQBand1")] == "eq" and fam[("ac20EQ", "ac20EQHpf")] == "eq"
    assert fam[("drive1", "drive1Active")] == "pedals" and fam[("compressor", "compressorMix")] == "pedals"
    assert fam[("parameters", "gateActive")] == "gate" and fam[("parameters", "gateThreshold")] == "gate"
    assert {fam[k] for k in NEW if k[0] == "cabParameters"} == {"cab"}
    assert set(fam.values()) == set(X.FAMILIES)


def test_family_refuses_other_keys():
    for k in (("reverb", "reverbMix"), ("parameters", "doublerActive"), ("ac20EQ", "ac20EQActive")):
        with pytest.raises(SystemExit):
            X.family_of(k, AMP)


def test_tags_match_pipeline_fix():
    assert X.ALL_TAGS == P.C3_TAGS
    assert X.TAGS["C3-ftm"] == () and set(X.TAGS["C3-core"]) == set(X.FAMILIES)
    assert {X.TAGS[t] for t in X.FAMILY_TAG.values()} == {(f,) for f in X.FAMILIES}


# --- the label sources and the masks --------------------------------------------------------------------------------

def test_mask_keys_by_kind():
    c2 = X.mask_keys("c2", AMP, KS, searched=X.names_of(NEW))
    assert KS <= c2 and ("ac20EQ", "ac20EQBand1") in c2
    assert ("parameters", "gateActive") not in c2 and ("parameters", "gateThreshold") in c2   # the switch masked
    assert X.eq_active(AMP) not in X.mask_keys("c2", AMP, KS | {X.eq_active(AMP)}, searched=["ac20EQ/ac20EQActive"])
    assert X.mask_keys("stored", AMP, KS) == KS
    c1b = X.mask_keys("c1b", AMP, KS, c1a=["parameters/inputGain", "drive1/drive1Drive"],
                      stage_a=["cabParameters/leftRoomActive"], stage_b=["cabParameters/leftMicType", "ac20EQ/ac20EQBand2"])
    assert c1b == {("parameters", "inputGain"), ("drive1", "drive1Drive"), ("cabParameters", "leftRoomActive"),
                   ("cabParameters", "leftMicType"), ("ac20EQ", "ac20EQBand2")}
    with pytest.raises(ValueError):
        X.mask_keys("other", AMP, KS)


def c1b_rec(label=True, held=3.0, effect=None):
    return {"label": {"a/b": "1"} if label else None, "effect_kept": effect,
            "fresh": {"final": {"judge": {"A": 2.9, "B": held}}}, "rooms_keys": ["cabParameters/leftRoomActive"],
            "mics_eq_keys": ["cabParameters/leftMicType"], "searched_keys": ["reverb/reverbMix"]}


def test_c1b_usable():
    assert X.c1b_usable(c1b_rec())
    assert not X.c1b_usable(c1b_rec(held=math.inf))          # F70's failed record: infinite on the held half
    assert not X.c1b_usable(c1b_rec(label=False))
    assert not X.c1b_usable(c1b_rec(effect="delay"))
    assert not X.c1b_usable(None)


def test_choose_source():
    stored = {"label": {"s/t": "0"}}
    c2 = X.choose_source({"label": {"x/y": "1"}, "searched_keys": ["drive1/drive1Drive"]}, "goat", stored=stored)
    assert c2["kind"] == "c2" and c2["searched"] == ["drive1/drive1Drive"]
    fb = {"label": None}
    s = X.choose_source(fb, "c1a", c1b=c1b_rec(), c1a={"searched_keys": ["parameters/inputGain"]}, stored=stored)
    assert s["kind"] == "c1b" and s["c1a"] == ["parameters/inputGain"]
    assert "searched" not in s                                # never C1b's searched_keys (every effect knob)
    assert X.choose_source(fb, "c1a", c1b=c1b_rec(held=math.inf), stored=stored)["kind"] == "stored"
    assert X.choose_source(fb, "bks2", c1b=c1b_rec(), stored=stored) == {"kind": "stored", "label": stored["label"]}
    with pytest.raises(SystemExit):
        X.choose_source(None, "goat", stored=stored)
    with pytest.raises(SystemExit):
        X.choose_source(fb, "goat", stored={"label": None})


def test_head_masks_and_mask_rows():
    import numpy as np

    from learn import full_space as FS

    keys = {("parameters", "inputGain"), ("ac20EQ", "ac20EQBand1"), ("drive1", "drive1Active")}
    c, s, k = X.head_masks(keys)
    D = FS.by_name()
    assert c.sum() == sum((D[n].module, D[n].key) in keys for n in FS.CONT) and s.sum() == 1 and k.sum() == 0
    n = 3
    Y = [np.zeros((n, len(FS.CONT))), np.ones((n, len(FS.CONT))), np.zeros((n, len(FS.SW))), np.ones((n, len(FS.SW))),
         np.zeros((n, len(FS.CAT))), np.ones((n, len(FS.CAT))), np.zeros(n, np.int64)]
    rows = [{"real": "u", "amp": AMP, "cls": "clean"}, {"i": 1, "amp": AMP, "cls": "clean"},
            {"real": "v", "amp": AMP, "cls": "crunch"}]
    ms = {AMP: {"clean": ("sel", {}), "crunch": ("sel", {})}}
    X.mask_rows(Y, rows, ms, lambda u, a, S: keys if u == "u" else set())
    assert Y[1][0].sum() == c.sum() and Y[3][0].sum() == 1 and Y[6][0] == -100
    assert Y[1][1].sum() == len(FS.CONT) and Y[6][1] == 0           # a plugin row is untouched
    assert Y[1][2].sum() == 0 and Y[3][2].sum() == 0 and Y[6][2] == -100


def test_keys_fn_and_label_fn_refuse_unknown_rows():
    src = {("u", AMP): {"kind": "c2", "label": {"parameters/inputGain": "0"}, "searched": ["drive1/drive1Drive"]}}
    with pytest.raises(SystemExit):
        X.keys_fn(src)("w", AMP, {})
    with pytest.raises(SystemExit):
        X.label_fn(src)({"unit": "w", "amp": AMP})
    lab = X.label_fn(src)({"unit": "u", "amp": AMP})
    assert lab["amp"] == AMP and lab["settings"] == {"parameters/inputGain": "0"}


def test_trained_union_and_counts():
    st = {"records": [{"key": "a", "amp": AMP}, {"key": "b", "amp": AMP}, {"key": "c", "amp": "pr12"}],
          "outputs": {"a": {"label": {}, "searched_keys": ["drive1/drive1Drive"]},
                      "b": {"label": None, "searched_keys": ["compressor/compressorMix"]}}}
    assert X.trained_union(st) == {AMP: {("drive1", "drive1Drive")}}
    assert X.source_counts({1: {"block": "goat", "kind": "c2"}, 2: {"block": "c1a", "kind": "c1b"},
                            3: {"block": "goat", "kind": "c2"}}) == {"c1a:c1b": 1, "goat:c2": 2}


def test_c2_state_refuses_until_complete(tmp_path, monkeypatch):
    rp = tmp_path / "records.json"
    recs = [{"key": f"k{j}"} for j in range(X.N_C2)]
    rp.write_text(json.dumps({"records": recs}))
    paths = [tmp_path / f"o{j}.json" for j in range(X.N_C2)]
    monkeypatch.setattr(X, "c2_files", lambda: (rp, list(zip(recs, paths))))
    for p in paths[:10]:
        p.write_text(json.dumps({"label": None}))
    with pytest.raises(SystemExit, match="10 of 520"):
        X.c2_state()
    assert X.c2_state(partial=True)["written"] == 10
    for p in paths[10:]:
        p.write_text(json.dumps({"label": None}))
    a = X.c2_state()
    assert a["written"] == X.N_C2
    paths[3].write_text(json.dumps({"label": {"x/y": "1"}}))
    assert X.c2_state()["sha256"] != a["sha256"]              # any output's change moves the sha


# --- the per-control hold ---------------------------------------------------------------------------------------------

def S_():
    return {("parameters", "inputGain"): "0", ("ac20Amp", "ac20Volume"): "0.5", ("cabParameters", "rightCabActive"): "true",
            ("cabParameters", "leftMicType"): "1", ("ac20EQ", "ac20EQActive"): "true", ("ac20EQ", "ac20EQBand1"): "0",
            ("ac20EQ", "ac20EQHpf"): "20", ("drive1", "drive1Active"): "false", ("drive1", "drive1Drive"): "0.5",
            ("compressor", "compressorMix"): "1", ("parameters", "gateActive"): "false",
            ("parameters", "gateThreshold"): "-80", ("cabParameters", "leftCabActive"): "true",
            ("cabParameters", "leftRoomMicLevel"): "-6", ("cabParameters", "rightCabPhase"): "false",
            ("parameters", "doublerActive"): "false", ("reverb", "reverbActive"): "false"}


def X_():
    x = {k: "ANS" for k in S_()}
    x[("reverb", "reverbActive")] = "true"
    x[("parameters", "doublerActive")] = "true"
    x[("ac20EQ", "ac20EQActive")] = "false"
    x[("parameters", "gateActive")] = "false"
    return x


def test_hold_keys_core_is_kspace():
    w, f = X.hold_keys(AMP, S_(), UNION, X.TAGS["C3-core"], kspace=KS)
    assert w == KS and f == {X.eq_active(AMP): "true"}


def test_hold_keys_full_and_families():
    w, f = X.hold_keys(AMP, S_(), UNION, (), kspace=KS)
    assert w == (KS | NEW) - {("parameters", "gateActive")}
    assert f == {X.eq_active(AMP): "true", ("parameters", "gateActive"): "true"}
    for fam in X.FAMILIES:
        w1, f1 = X.hold_keys(AMP, S_(), UNION, (fam,), kspace=KS)
        assert not any(X.family_of(k, AMP) == fam for k in w1 - KS)
        assert (("parameters", "gateActive") in f1) == (fam != "gate")
    with pytest.raises(SystemExit):
        X.hold_keys(AMP, S_(), UNION, ("effects",), kspace=KS)


def test_hold_outside_space_default_and_c3(monkeypatch):
    from learn import full_space as FS
    from learn import knob_ceiling as K

    class D:
        def __init__(self, m, k):
            self.module, self.key = m, k

    monkeypatch.setattr(K, "space", lambda amp, S: [D(*k) for k in sorted(KS)])
    monkeypatch.setattr(X, "kspace_keys", lambda amp, S: set(KS))
    S, x = S_(), X_()
    base = FS.sections_on(dict(S))
    ftm = P.hold_outside_space(x, S, AMP)
    assert all(ftm[k] == "ANS" for k in KS) and all(ftm[k] == base[k] for k in ftm if k not in KS)
    core = P.hold_outside_space(x, S, AMP, X.hold_spec(UNION, X.TAGS["C3-core"]))
    assert core == ftm                                       # the all-new-at-S tag equals FTm's hold
    for tag, fams in X.TAGS.items():
        hold = X.hold_spec(UNION, fams)
        y = P.hold_outside_space(x, S, AMP, hold)
        w, f = hold(AMP, S)
        assert all(y[k] == base[k] for k in y if k not in w and k not in f)   # no untrained key off S
        assert y[("reverb", "reverbActive")] == "false" and y[("parameters", "doublerActive")] == "false"
        assert y[X.eq_active(AMP)] == "true"
        assert y[("parameters", "gateActive")] == ("false" if "gate" in fams else "true")
    full = P.hold_outside_space(x, S, AMP, X.hold_spec(UNION, ()))
    assert full[("drive1", "drive1Drive")] == "ANS" and full[("parameters", "gateThreshold")] == "ANS"
    eqS = P.hold_outside_space(x, S, AMP, X.hold_spec(UNION, ("eq",)))
    assert eqS[("ac20EQ", "ac20EQBand1")] == "0" and eqS[("drive1", "drive1Drive")] == "ANS"


def test_at_S_of():
    assert X.at_S_of("C3-pedalsS") == ("pedals",)
    assert X.at_S_of(X.ADOPT_TAG, {"at_S": ["eq", "gate"]}) == ("eq", "gate")
    with pytest.raises(SystemExit):
        X.at_S_of(X.ADOPT_TAG)
    with pytest.raises(SystemExit):
        X.at_S_of("P2b-ftm")


# --- the rows -------------------------------------------------------------------------------------------------------

def row(mean, half, clusters):
    return {"mean": mean, "lo90": mean - half, "hi90": mean + half, "clusters": clusters}


def test_pooled_equal_weights():
    b, g = row(-0.02, 0.01, 8), row(0.01, 0.004, 126)
    p = X.pooled(b, g)
    assert p["mean"] == pytest.approx(-0.005)
    sb = 0.01 / P.t95(7)
    sg = 0.004 / P.t95(125)
    se = math.sqrt(sb ** 2 + sg ** 2) / 2
    df = (sb ** 2 + sg ** 2) ** 2 / (sb ** 4 / 7 + sg ** 4 / 125)
    assert p["df"] == pytest.approx(df)
    assert p["hi90"] - p["mean"] == pytest.approx(P.t95(int(df)) * se)
    assert X.pooled(b, {"mean": 0.0, "lo90": None, "hi90": None, "clusters": 1}) is None


def test_shown_worse_and_adoption():
    assert X.shown_worse(row(0.02, 0.01, 8)) and not X.shown_worse(row(0.005, 0.01, 8))
    assert not X.shown_worse(None) and not X.shown_worse({"lo90": None})
    ok, worse = row(-0.001, 0.01, 8), row(0.03, 0.01, 8)
    b = {X.row_name("C3-ftm", X.FAMILY_TAG[f]): ok for f in X.FAMILIES}
    g = {X.row_name("C3-ftm", X.FAMILY_TAG[f]): row(-0.001, 0.003, 126) for f in X.FAMILIES}
    for n in X.COMPARISONS:
        b[n], g[n] = ok, row(-0.001, 0.003, 126)
    a = X.adoption(b, g)
    assert a["adopted"] == list(X.FAMILIES) and a["at_S"] == [] and a["config_tag"] == "C3-ftm"
    assert set(a["comparisons"]) == set(X.COMPARISONS) and not a["core_shown_worse"]
    assert all(a["comparisons"][n]["pooled"]["mean"] == pytest.approx(-0.001) for n in X.COMPARISONS)
    g[X.row_name("C3-core", X.FTM_TAG)] = row(0.01, 0.003, 126)   # C3 core worse than FTm on GOAT: the isolation run
    assert X.adoption(b, g)["core_shown_worse"]
    g[X.row_name("C3-core", X.FTM_TAG)] = row(-0.001, 0.003, 126)
    b[X.row_name("C3-ftm", "C3-gateS")] = worse                 # shown worse on BKS alone: back at S
    a = X.adoption(b, g)
    assert a["at_S"] == ["gate"] and a["config_tag"] == "C3-gateS"
    b[X.row_name("C3-ftm", "C3-cabS")] = worse
    a = X.adoption(b, g)
    assert a["at_S"] == ["gate", "cab"] and a["config_tag"] == X.ADOPT_TAG
    with pytest.raises(SystemExit):
        X.adoption({}, g)
    del b["C3-ftm - S"]
    with pytest.raises(SystemExit, match="C3-ftm - S"):
        X.adoption(b, g)


def test_config_tag():
    assert X.config_tag([]) == "C3-ftm" and X.config_tag(X.FAMILIES) == "C3-core"
    assert X.config_tag(["eq"]) == "C3-eqS" and X.config_tag(["eq", "pedals"]) == X.ADOPT_TAG


def test_replacement():
    n = X.row_name("C3-ftm", X.FTM_TAG)
    r = X.replacement({n: row(0.0, 0.01, 8)}, {n: row(0.001, 0.003, 126)}, "C3-ftm")
    assert r["replaces_ftm"]                                   # undecided: replaces
    r = X.replacement({n: row(0.0, 0.01, 8)}, {n: row(0.01, 0.003, 126)}, "C3-ftm")
    assert not r["replaces_ftm"] and r["shown_worse"]
    with pytest.raises(SystemExit):
        X.replacement({}, {}, "C3-ftm")


def test_report_pairs():
    pairs = X.report_pairs().split(",")
    assert "C3-ftm:P2b-ftm" in pairs and "C3-ftm:S" in pairs and "C3-core:P2b-ftm" in pairs
    assert {f"C3-ftm:{t}" for t in X.FAMILY_TAG.values()} <= set(pairs)
    for t in X.TAGS:                                          # every configuration the adoption can name has its FTm row
        if t != "C3-ftm":
            assert f"{t}:P2b-ftm" in pairs or t == "C3-core" and "C3-core:P2b-ftm" in pairs


def test_gate_rows_and_spread():
    labs = {"c2:goat": [{"parameters/gateActive": "true", "parameters/gateThreshold": "-80"},
                        {"parameters/gateActive": "true", "parameters/gateThreshold": "-56"},
                        {"parameters/gateActive": "false", "parameters/gateThreshold": "-80"}, None]}
    r = X.gate_rows(labs)["c2:goat"]
    assert (r["labels"], r["gate_on"], r["gate_off"]) == (3, 2, 1)
    t = r["threshold_where_on"]
    assert t["n"] == 2 and t["at_minus_80"] == 1 and t["moved_from_minus_80"] == 1 and t["min"] == -80.0
    assert X.spread([]) is None


# The shape of a stored judge file (real/judge/P2b-ftm/..19_ElecGtr1aDI.wav@15.0#21_ElecGtr1cReamp.wav|ac20.json, its
# values as stored): "judge" is {search half: {half: value}}.
JUDGE_FILE = {"unit": "set5/BKS_Bulldozer_Full/19_ElecGtr1aDI.wav@15.0#21_ElecGtr1cReamp.wav", "amp": "ac20",
              "tag": "P2b-ftm", "lag": -64,
              "judge": {"A": {"A": 4.608276525688598, "B": 5.056316872084529},
                        "B": {"A": 4.196592669221414, "B": 4.671852325355218}}}


def test_amp_rows_on_a_judge_file_shape():
    u = JUDGE_FILE["unit"]
    judge = {(u, "ac20"): JUDGE_FILE["judge"],
             (u, "pr12"): {"A": {"A": 4.0, "B": 6.0}, "B": {"A": 3.0, "B": 5.0}},
             (u, "sw50r"): {"A": {"A": 5.0, "B": 7.0}, "B": {"A": 4.5, "B": 4.4}}}
    amps = ("ac20", "pr12", "sw50r")
    amp_p = {f"{u}|ac20": {"A": [0.7, 0.2, 0.1], "B": [0.1, 0.2, 0.7]}}
    rows = X.amp_rows([{"unit": u, "di": "d1"}], amp_p, judge, amps, amps)
    assert len(rows) == 2
    held_A = {a: judge[(u, a)]["A"]["B"] for a in amps}       # search half A's answers, judged on B
    want = math.log(held_A["ac20"]) - sum(math.log(v) for v in held_A.values()) / 3
    assert rows[0] == ("d1", u, pytest.approx(want))
    held_B = {a: judge[(u, a)]["B"]["A"] for a in amps}
    want = math.log(held_B["sw50r"]) - sum(math.log(v) for v in held_B.values()) / 3
    assert rows[1] == ("d1", u, pytest.approx(want))
    assert X.amp_rows([{"unit": u, "di": "d1"}], {}, judge, amps, amps) == []


def test_amp_value():
    v = X.amp_value({"ac20": 2.0, "pr12": 3.0, "sw50r": 4.0}, "ac20")
    assert v == pytest.approx(math.log(2.0) - (math.log(2.0) + math.log(3.0) + math.log(4.0)) / 3)
    assert X.amp_value({"ac20": 2.0, "pr12": math.inf, "sw50r": None}, "ac20") is None
    assert X.amp_value({"ac20": 2.0, "pr12": 3.0}, "sw50r") is None


# --- the wiring in pipeline_fix --------------------------------------------------------------------------------------

def test_names_and_phases():
    assert P.model_base("C3-core") == X.C3_BASE and P.model_base(P.FTS_TAG) == P.FTM_BASE
    assert P.model_base("P2b-ftmc") == "P2b-ftmc"
    assert P.ft_name(2, base=X.C3_BASE) == "C3-ftm-k2"
    assert P.ft_name(1, True, P.FT_LR, 300, X.C3_BASE) == "C3-ftm-k1-inner-cap300"
    assert P.ft_name(None, base=X.C3_BASE) == "C3-ftm"
    for t in P.C3_TAGS:
        assert P.read_phase(t) == "phase_c3"
    assert P.report_phase({"C3-ftm", "P2b-ftm", "S"}) == "phase_c3"
    assert "phase_c3".startswith(P.ARM_FOLD_PHASES)
    assert P.answer_hold("P2b-ftm") is None


def test_ft_read_check_covers_c3_runs():
    rec = {"test": "C3-ftm-k0", "seed": 1, "inner": False, "models": {"best": "a", "final": "a"},
           "model_sha256": {"best": "h", "final": "h"}, "E": 5, "epochs_run": 5}
    P.ft_read_check(rec)
    with pytest.raises(SystemExit):
        P.ft_read_check(dict(rec, inner=True))
    with pytest.raises(SystemExit):
        P.ft_read_check(dict(rec, E=4))


def test_read_check_compares_c2_sha(monkeypatch):
    monkeypatch.setattr(X, "c2_sha", lambda: "abc")
    X.read_check({"test": "C3-ftm-k0", "seed": 1, "c3": {"c2_sha256": "abc"}})
    with pytest.raises(SystemExit):
        X.read_check({"test": "C3-ftm-k0", "seed": 1, "c3": {"c2_sha256": "xyz"}})
    with pytest.raises(SystemExit):
        X.read_check({"test": "C3-ftm-k0", "seed": 1})


def test_head_means():
    import numpy as np

    from learn import full_space as FS

    h = {"knob_sum": np.arange(len(FS.CONT), dtype=float), "knob_n": np.ones(len(FS.CONT)),
         "sw_sum": np.zeros(len(FS.SW)), "sw_n": np.zeros(len(FS.SW)), "mic_sum": np.ones(len(FS.CAT)) * 2,
         "mic_n": np.ones(len(FS.CAT)) * 4}
    m = P.head_means(h)
    assert m["knob"][FS.CONT[3]] == 3.0 and m["switch"][FS.SW[0]] is None and m["mic"][FS.CAT[0]] == 0.5


def test_renders_registered():
    import re

    from learn import local_objective as LO

    for cmd in ("-u -m learn.full_controls_c3 c3-recheck", "-u -m learn.pipeline_fix real-render --names C3-ftm --shard 0/3",
                "-u -m learn.pipeline_fix goat-render --names C3-ftm --shard 1/3", "-u -m learn.score_ear h4-render --tags C3-ftm"):
        assert any(re.search(p, f"python {cmd}") for p in LO.RENDERS), cmd
    for cmd in ("c3-check", "c3-gate x.json", "c3-adopt", "c3-n12 x.json", "c3-amp x.json"):
        assert not any(re.search(p, f"python -m learn.full_controls_c3 {cmd}") for p in LO.RENDERS), cmd
    assert not any(re.search(p, "python -m learn.pipeline_fix real-report --pairs a:b") for p in LO.RENDERS)


# --- C3i, the isolation of C3's core (phase_c3i) ----------------------------------------------------------------------

def test_c3i_is_read_through_c3s_paths_with_ftms_hold_and_its_own_runs():
    from learn import full_controls_c3 as X
    from learn import pipeline_fix as P
    assert P.C3I_TAG == X.C3I_TAG and P.C3_READ == P.C3_TAGS | {X.C3I_TAG, X.C3B_TAG} and X.C3I_TAG not in X.ALL_TAGS
    assert P.model_base(X.C3I_TAG) == X.C3I_BASE != X.C3_BASE and X.C3I_BASE != P.FTM_BASE
    assert P.read_phase(X.C3I_TAG) == "phase_c3i" and P.answer_hold(X.C3I_TAG) is None   # FTm's hold: K.space
    assert P.report_phase({X.C3I_TAG, "C3-core", "P2b-ftm"}) == "phase_c3i"


def test_c3i_pairs_and_its_declared_readings():
    from learn import full_controls_c3 as X
    assert X.c3i_pairs() == "C3i:P2b-ftm,C3-core:C3i,C3i:S"
    def j(lo, hi, where="goat"):
        r = {"bks": {"lo90": -1, "hi90": 1}, "goat": {"lo90": -1, "hi90": 1}, "pooled": {"lo90": -1, "hi90": 1}}
        r[where] = {"lo90": lo, "hi90": hi}
        return r
    W, B, U = j(0.01, 0.05), j(-0.05, -0.01), j(-0.01, 0.01)
    S = dict(j(0.01, 0.05), bks={"lo90": -0.05, "hi90": -0.01})
    assert [X.direction(r) for r in (W, B, U, S)] == ["worse", "better", "undecided", "split"]
    got = {(a, b): X.c3i_reading(ra, rb) for a, ra in (("W", W), ("B", B), ("U", U)) for b, rb in (("W", W), ("B", B), ("U", U))}
    assert got == {("W", "U"): "labels", ("W", "B"): "labels", ("W", "W"): "both", ("U", "W"): "objective",
                   ("B", "W"): "objective", ("U", "U"): "neither", ("U", "B"): "neither", ("B", "U"): "neither",
                   ("B", "B"): "neither"}
    assert X.c3i_reading(S, U) == X.c3i_reading(U, S) == "split"


def test_c3i_rows_judge_each_pair_on_both_sets(tmp_path, monkeypatch):
    from learn import full_controls_c3 as X
    from learn import pipeline_fix as P
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "require", lambda phase: {})
    monkeypatch.setattr(X, "c2_sha", lambda: "sha")

    def row(m, lo, hi):
        return {"mean": m, "lo90": lo, "hi90": hi, "clusters": 8}
    rows = {"C3i - P2b-ftm": row(0.03, 0.01, 0.05), "C3-core - C3i": row(0.0, -0.02, 0.02), "C3i - S": row(-0.1, -0.2, 0.0)}
    for d in (P.REAL_DIR, P.GOAT_DIR):
        (tmp_path / d).mkdir()
        (tmp_path / d / "report-c3i.json").write_text(json.dumps({"rows": rows}))
    X.cmd_c3i(None)
    rec = json.loads((tmp_path / X.OUT / "c3i.json").read_text())
    assert rec["reading"] == "labels" and set(rec["rows"]) == set(rows) and rec["phase"] == "phase_c3i"
    assert rec["follow_up"] is False and rec["directions"]["C3i - P2b-ftm"] == "worse"
    (tmp_path / P.GOAT_DIR / "report-c3i.json").write_text(json.dumps({"rows": {"C3i - S": rows["C3i - S"]}}))
    with pytest.raises(SystemExit):
        X.cmd_c3i(None)


def test_c3i_launchers_train_with_c3i_and_read_after_c2r():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1] / "logs"
    t, r = (root / "launch-c3i-train.zsh").read_text(), (root / "launch-c3i-read.zsh").read_text()
    assert "--masked --c3i" in t and "--c3 " not in t.replace("--c3i", "")
    assert "c2r.log" in r and "c3i-train.log" in r and "--names ${TAG}" in r and "c3i-rows" in r
    for x in (t, r):                                    # a stop by recorded PIDs reads only this launch's
        assert "mv ${PIDS} ${PIDS}." in x and x.index("mv ${PIDS}") < x.index('echo "launcher $$" >> ${PIDS}')


# --- C3b, the amp head on real rows (phase_c3b) -----------------------------------------------------------------------

def _lab(s, h, pk=-6.0, half=("A", "B")):
    return {"label": {}, "search": half[0], "held": half[1], "best": {"judge": {half[0]: s, half[1]: h}, "peak_dbfs": pk}}


def test_c3b_reads_through_c3s_paths_with_its_own_runs_and_the_adopted_hold(tmp_path, monkeypatch):
    assert P.C3B_TAG == X.C3B_TAG and P.C3B_TAG in P.C3_READ and X.C3B_TAG not in X.ALL_TAGS
    assert P.model_base(X.C3B_TAG) == X.C3B_BASE not in (X.C3_BASE, X.C3I_BASE, P.FTM_BASE)
    assert P.read_phase(X.C3B_TAG) == "phase_c3b"
    (tmp_path / "decision.json").write_text(json.dumps({"tag": "C3-cabS"}))
    monkeypatch.setattr(X, "c3_dir", lambda: tmp_path)
    monkeypatch.setattr(X, "hold_for", lambda tag: ("hold", tag))
    assert P.answer_hold(X.C3B_TAG) == ("hold", "C3-cabS")


def test_c3b_labels_its_real_rows_and_refuses_a_row_with_none():
    np = pytest.importorskip("numpy")
    from learn import full_space as F
    Y = [None] * 6 + [np.full(4, 7)]
    rows = [{"i": 0}, {"real": "u1"}, {"real": "u2"}, {"i": 3}]
    assert X.amp_label_rows(Y, rows, {"u1": "ac20", "u2": "pr12"}) == 2
    assert list(Y[6]) == [7, F.AMPS.index("ac20"), F.AMPS.index("pr12"), 7]           # plugin rows keep their own
    with pytest.raises(SystemExit):
        X.amp_label_rows(Y, rows, {"u1": "ac20"})


def test_c3b_usable_labels_argmin_and_stage1_rows():
    assert X.usable_pair(_lab(3.0, 4.0)) == (3.0, 4.0)
    assert X.usable_pair(_lab(3.0, 4.0, pk=-58.0)) is None and X.usable_pair(dict(_lab(3.0, 4.0), label=None)) is None
    assert X.label_argmin({"sw50r": (3.0, 4.0), "ac20": (3.0, 5.0), "pr12": (2.0, 6.0)}) == "pr12"
    ul = {"d1@1#t": {"pr12": _lab(2.0, 4.0), "sw50r": _lab(3.0, 2.0), "ac20": _lab(4.0, 3.0)}}
    rows = X.stage1_rows(ul, {"C3b": {"d1@1#t": "sw50r"}, "W": {"d1@1#t": "pr12"}}, lambda u: u.split("@")[0])
    blind = (math.log(4) + math.log(2) + math.log(3)) / 3
    assert rows["C3b"] == [("d1", "d1@1#t", pytest.approx(math.log(2) - blind))]
    assert rows["label"] == [("d1", "d1@1#t", pytest.approx(math.log(4) - blind))]      # the search argmin: pr12
    assert rows["C3b - W"] == [("d1", "d1@1#t", pytest.approx(math.log(2) - math.log(4)))]
    assert X.head_pick({"d1@1#t|pr12": {"A": [0.1, 0.7, 0.2]}}, "d1@1#t", "A", ("pr12", "sw50r", "ac20")) == "sw50r"
    better = {"bks": {"lo90": -0.05, "hi90": -0.01}, "goat": {"lo90": -0.1, "hi90": 0.1}, "pooled": {"lo90": -0.1, "hi90": 0.1}}
    assert X.stage1_reading(better) == "learns" and X.stage1_reading({"bks": {"lo90": -1, "hi90": 1}}) == "undecided"


def test_c3b_amp_labels_cover_every_real_training_unit():
    if not (P.out_dir() / "c2b" / "report.json").exists():
        pytest.skip("no stored data")
    lab = X.amp_labels()
    goat = {r["unit"] for r in P.goat_labels()[0]}
    bks = {r["unit"] for r in P.real_labels(2)[0]}
    assert goat <= set(lab) and bks <= set(lab) and len(goat) == 214 and len(bks) == 102
    rep = json.loads((P.out_dir() / "c2b" / "report.json").read_text())["labels"]
    assert all(lab[u] == rep[u]["amp"] for u in goat)


def test_c3b_launchers_train_with_c3b_and_read_at_zero_renders():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1] / "logs"
    t, r = (root / "launch-c3b-train.zsh").read_text(), (root / "launch-c3b-read.zsh").read_text()
    assert "--masked --c3b" in t and "--c3i" not in t and "mv ${PIDS} ${PIDS}." in t
    assert "c3b-train.log" in r and "c3b-rows" in r and "real-render" not in r and "goat-render" not in r and "h4-render" not in r
