"""learn/direct_sound_gate.py: the pure parts of amendment 6's sound gate."""

import math
import random
import re
import types

import pytest

np = pytest.importorskip("numpy")

from learn import direct_sound_gate as G  # noqa: E402
from learn import direct_stems as DS  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import pretrain_set as PS  # noqa: E402
from learn import song_model as SM  # noqa: E402


# --- the decision ---------------------------------------------------------------------------------------

def _per(band_means, n=5, spread=0.01):
    per, band_of, k = {}, {}, 0
    for b, m in band_means.items():
        for j in range(n):
            per[k] = m + spread * (j - (n - 1) / 2)
            band_of[k] = b
            k += 1
    return per, band_of


def test_gate_ok_only_when_the_interval_lies_below_zero():
    per, band_of = _per({"a": -0.10, "b": -0.08, "c": -0.12, "d": -0.09})
    iv = G.band_interval(per, band_of)
    assert iv[3] == 4 and iv[2] < 0 and G.gate_decision(iv) == "OK"
    per, band_of = _per({"a": -0.10, "b": +0.08, "c": -0.12, "d": +0.05})
    iv = G.band_interval(per, band_of)
    assert iv[1] < 0 < iv[2] and G.gate_decision(iv) == "STOP"
    per, band_of = _per({"a": +0.10, "b": +0.08, "c": +0.12, "d": +0.09})
    assert G.gate_decision(G.band_interval(per, band_of)) == "STOP"


def test_gate_stops_without_a_usable_interval():
    assert G.gate_decision(None) == "STOP"
    per, band_of = _per({"a": -0.5})
    assert G.gate_decision(G.band_interval(per, band_of)) == "STOP"           # one band: no interval
    assert G.gate_decision((-0.1, -0.2, math.inf, 4)) == "STOP"


def test_the_interval_is_band_weighted_with_3_df():
    per = {0: -0.1, 1: -0.1, 2: -0.1, 3: -0.2, 4: 0.0, 5: -0.3}
    band_of = {0: "a", 1: "a", 2: "a", 3: "b", 4: "c", 5: "d"}
    m, lo, hi, n = G.band_interval(per, band_of)
    means = [-0.1, -0.2, 0.0, -0.3]
    sd = float(np.std(means, ddof=1))
    assert n == 4 and m == pytest.approx(-0.15)
    assert hi - m == pytest.approx(2.353 * sd / 2)


def test_half_logratio_clips_and_handles_refusals():
    assert G.half_logratio(1.0, 2.0) == (pytest.approx(math.log(0.5)), False)
    assert G.half_logratio(None, None) == (None, False)
    assert G.half_logratio(math.inf, 2.0) == (G.CLIP, True)                   # D silent: worst
    assert G.half_logratio(2.0, None) == (-G.CLIP, True)                      # the constant silent
    assert G.half_logratio(0.0, 2.0) == (-G.CLIP, True)                       # identical to the truth
    assert G.half_logratio(0.0, 0.0) == (0.0, False)
    assert G.half_logratio(1000.0, 1.0) == (G.CLIP, True)


def test_example_logratio_means_the_scorable_halves():
    v, h, c = G.example_logratio({"A": 1.0, "B": 4.0}, {"A": 2.0, "B": 2.0})
    assert h == 2 and c == 0 and v == pytest.approx(0.5 * (math.log(0.5) + math.log(2.0)))
    v, h, _ = G.example_logratio({"A": None, "B": 1.0}, {"A": None, "B": 2.0})
    assert h == 1 and v == pytest.approx(math.log(0.5))
    assert G.example_logratio({"A": None, "B": None}, {"A": None, "B": None})[0] is None


def test_report_table_reads_d_minus_constant():
    ids = list(range(16))
    band_of = {i: "abcd"[i % 4] for i in ids}
    rows = {"constant": {i: {"judge": {"A": 2.0, "B": 2.0}} for i in ids},
            "D": {i: {"judge": {"A": 1.0 + 0.01 * i, "B": 1.5}} for i in ids},
            "D0": {i: {"judge": {"A": 3.0, "B": 3.0}} for i in ids}}
    tab = G.report_table(rows, ids, band_of, {i: "clean" for i in ids}, {i: "pr12" for i in ids})
    assert tab["decision"] == "OK" and tab["deciding"][2] < 0
    assert tab["contrasts"]["D0-constant"][0] > 0 and tab["counts"]["D-constant"]["closer_share"] == 1.0
    rows["D"] = {i: {"judge": {"A": 2.0, "B": 2.0}} for i in ids}                  # a tie
    assert G.report_table(rows, ids, band_of, {i: "c" for i in ids}, {i: "a" for i in ids})["decision"] == "STOP"


def test_completeness_needs_every_arm_except_after_a_refused_truth():
    rbw = {"truth": {1: {}, 2: {"refused": "x"}}, "constant": {1: {}}, "D": {1: {}}}
    assert G.completeness([1, 2], rbw) == []
    assert G.completeness([1, 2, 3], rbw) == ["truth: 1 examples have no render row",
                                              "constant: 1 examples have no render row",
                                              "D: 1 examples have no render row"]


# --- preset assembly: S with the labelled dims replaced -------------------------------------------------

def _menu():
    """A stand-in plugin menu: per amp, the START presets and a few factory ones; every labelled dim
    present in S (as the real menu's S), the left cab off in one S."""
    rng = random.Random(7)
    menu = {}
    for amp in K.AMPS:
        m = {}
        names = {K.START[c][amp] for c in ("clean", "crunch")} | {f"factory:x{j}" for j in range(3)}
        for name in sorted(names):
            S = {("parameters", "outputGain"): "0", ("cabParameters", "leftCabActive"): "true"}
            for d in K.space(amp, None):
                if d.kind in ("cont", "log"):
                    S[(d.module, d.key)] = K.fmt(d.from_unit(rng.random()))
                else:
                    S[(d.module, d.key)] = rng.choice(d.values)
            m[name] = (f"sel-{amp}", S)
        menu[amp] = m
    left_off = K.START["crunch"]["ac20"]
    menu["ac20"][left_off][1][("cabParameters", "leftCabActive")] = "false"
    return menu


def test_the_label_as_the_answer_assembles_the_truth():
    menu = _menu()
    seen = set()
    for i in range(300):
        rng, amp, mode, base = PS.plan_example(i)
        sel, x, label, _ = PS.settings_for(rng, amp, mode, base, menu, K.START, K.space, K.fmt)
        S = menu[amp][K.START[base][amp]][1]
        cont, sw, mics = G.complete(*G.label_answer(label, SM.encode), *G._masks(amp, S))
        assert DS.settings_from(amp, S, cont, sw, mics) == x
        seen.add((amp, base, mode))
    assert len(seen) == 18                                                          # every amp x class x mode


def test_an_answer_missing_a_labelled_dim_is_refused():
    S = _menu()["pr12"][K.START["clean"]["pr12"]][1]
    cm, swm, km = G._masks("pr12", S)
    cont = np.where(cm, 0.5, np.nan)
    cont[int(np.argmax(cm))] = np.nan
    with pytest.raises(SystemExit):
        G.complete(cont, [False] * len(swm), [0] * len(km), cm, swm, km)
    with pytest.raises(SystemExit):
        G.complete(np.where(cm, 0.5, np.nan), [None] * len(swm), [0] * len(km), cm, swm, km) if swm.any() else \
            G.complete(np.where(cm, 0.5, np.nan), [False] * len(swm), [None] * len(km), cm, swm, km)


# --- the constant ---------------------------------------------------------------------------------------

def _label(right_active, pos, mic_r, vol, bright="false"):
    return {"pr12Amp/pr12Volume": vol, "cabParameters/rightCabActive": right_active,
            "cabParameters/rightCabPosition": pos, "cabParameters/rightMicType": mic_r,
            "cabParameters/leftMicType": "2", "sw50rAmp/sw50rBright": bright}


def test_constant_answers_take_medians_majorities_and_modes_over_audible_labels():
    rows = [{"amp": "pr12", "base": "clean", "label": _label("true", 0.2, "3", 0.1)},
            {"amp": "pr12", "base": "clean", "label": _label("true", 0.4, "3", 0.2)},
            {"amp": "pr12", "base": "clean", "label": _label("false", 0.9, "7", 0.9, "true")},
            {"amp": "pr12", "base": "clean", "label": _label("false", 0.9, "7", 0.8, "true")},
            {"amp": "pr12", "base": "clean", "label": _label("false", 0.9, "7", 0.7, "true")}]
    c = G.constant_answers(rows, G.encode_audible, len(SM.CONT), len(SM.SW), len(SM.CAT))[("pr12", "clean")]
    j = SM.CONT.index
    assert c["cont"][j("pr12Amp/pr12Volume")] == pytest.approx(0.7)
    assert c["cont"][j("cabParameters/rightCabPosition")] == pytest.approx(0.3)   # the 2 audible labels only
    assert c["sw"][SM.SW.index("cabParameters/rightCabActive")] is False             # 2 of 5 true
    assert c["sw"][SM.SW.index("sw50rAmp/sw50rBright")] is True                      # 3 of 5 true
    assert c["mics"][SM.CAT.index("cabParameters/rightMicType")] == 3                 # audible labels only
    assert c["mics"][SM.CAT.index("cabParameters/leftMicType")] == 2
    assert math.isnan(c["cont"][j("cabParameters/leftCabPosition")])                  # never labelled


def test_the_fallback_mask_matches_amendment_5s_when_present():
    if not hasattr(DS, "encode_audible"):
        pytest.skip("amendment 5's readout is not merged")
    lab = _label("false", 0.9, "7", 0.3)
    a, b = G._silent(SM.encode(lab), SM.CONT, SM.SW, SM.CAT), DS.encode_audible(lab)
    assert all(np.array_equal(np.asarray(x), np.asarray(y)) for x, y in zip(a, b))


def test_same_constant_flags_a_difference():
    a = {("pr12", "clean"): np.array([0.5, np.nan])}
    assert G.same_constant(a, {("pr12", "clean"): np.array([0.5, np.nan])}, a) == []
    assert G.same_constant(a, {("pr12", "clean"): np.array([0.5 + 1e-6, np.nan])}, a) == ["('pr12', 'clean'): differs"]
    assert G.same_constant(a, {("pr12", "clean"): np.array([0.5, 0.1])}, a) == ["('pr12', 'clean'): differs"]
    assert G.same_constant(a, {}, a) == ["('pr12', 'clean'): missing"]


def test_const_json_round_trips():
    c = {("ac20", "crunch"): {"cont": np.array([0.25, np.nan]), "sw": [True, None], "mics": [None, 4]}}
    back = G.const_from_json(G.const_json(c))[("ac20", "crunch")]
    assert back["cont"][0] == 0.25 and math.isnan(back["cont"][1]) and back["sw"] == [True, None] and back["mics"] == [None, 4]


# --- D's answer -----------------------------------------------------------------------------------------

def _o(sw_logit, mic_logits):
    return (np.zeros(2), np.zeros((2, 3)), np.zeros((2, 3)), np.array([sw_logit]), [np.asarray(mic_logits, float)])


def test_switches_vote_over_6_outputs_and_a_tie_reads_false():
    six = [_o(+1, (0, 1)), _o(+1, (0, 1)), _o(+1, (0, 1)), _o(-1, (5, 0)), _o(-1, (0, 1)), _o(-1, (0, 1))]
    sw, mics = G.ensemble_votes(six)
    assert sw == [False] and mics == [1]
    sw, _ = G.ensemble_votes(six[:3] + [_o(+1, (0, 1))] + six[4:])
    assert sw == [True]


def test_model_answers_average_seeds_and_halves_then_pull():
    api = types.SimpleNamespace(
        median_answers=lambda outs, who: (None, {1: np.array([0.6, 0.2, 0.9])}),
        cell_b=lambda table, cell, mask: (np.array(table[cell]), 0),
        pull=lambda a, c, b: c + b * (a - c))
    outs = [[_o(+1, (0, 1)), _o(+1, (0, 1))] for _ in range(3)]                      # 3 seeds x 2 halves of example 1
    ans = G.model_answers(outs, [1, 1], api, {("pr12", "clean"): [0.5, 1.0, 0.0]},
                          {("pr12", "clean"): np.array([0.4, 0.4, 0.4])}, {1: ("pr12", "clean")}, lambda c: None)
    assert np.allclose(ans[1]["cont"], [0.5, 0.2, 0.4]) and np.allclose(ans[1]["a1a2"], [0.6, 0.2, 0.9])
    assert ans[1]["sw"] == [True] and ans[1]["mics"] == [1]


def test_a5_api_needs_every_function():
    assert G.a5_api(types.SimpleNamespace()) is None
    full = types.SimpleNamespace(**{n: object() for n in G.A5_NAMES})
    assert G.a5_api(full) is full


# --- the set, shards, counts, resumability ---------------------------------------------------------------

def _rows(n_sec=9, per=7):
    rows, i = [], 0
    for s in range(n_sec):
        for j in range(per):
            rows.append({"i": 1_000_000 + i, "section": f"s{s}", "amp": ("pr12", "ac20")[j % 2], "band": f"b{s % 4}",
                         "base": "clean"})
            i += 1
    return rows


def test_r_in_drops_tags_and_refusals_and_lists_pending():
    vsep = [{"i": i} for i in range(6)]
    tag = {0: "musdb18-train"}
    mix = {1: {}, 2: {"refused": "x"}, 3: {}, 4: {}}
    stem = {1: {}, 3: {"refused": "y"}}
    rows, pending = G.r_in(vsep, tag, mix, stem)
    assert [r["i"] for r in rows] == [1] and pending == [4, 5]


def test_shards_take_whole_sections_cover_everything_and_are_deterministic():
    rows = _rows()
    parts = [G.shard_rows(rows, k) for k in range(3)]
    assert sorted(r["i"] for p in parts for r in p) == sorted(r["i"] for r in rows)
    secs = [{r["section"] for r in p} for p in parts]
    assert not (secs[0] & secs[1]) and not (secs[1] & secs[2]) and not (secs[0] & secs[2])
    assert [r["i"] for r in G.shard_rows(list(reversed(rows)), 1)] == [r["i"] for r in parts[1]]
    for p in parts:                                                                  # render order: groups contiguous
        keys = [(r["section"], r["amp"]) for r in p]
        assert keys == sorted(keys)


def test_render_counts_prime_once_per_group_and_skip_what_is_done():
    rows = _rows()                                                                   # 9 sections x 2 amps = 18 groups
    assert G.pass_renders(rows, ("truth", "constant")) == 2 * len(rows) + 18
    done = {(r["i"], "truth") for r in rows} | {(r["i"], "constant") for r in rows if r["section"] != "s0"}
    s0 = [r for r in rows if r["section"] == "s0"]
    assert G.pass_renders(rows, ("truth", "constant"), done) == len(s0) + 2
    plan = G.planned_renders(rows)
    assert plan == {"truth+constant": 2 * len(rows) + 18, "D": len(rows) + 18, "D0": len(rows) + 18}


def test_todo_rows_resume_where_a_shard_stopped():
    rows = _rows(2, 2)
    done = {(rows[0]["i"], "truth"), (rows[0]["i"], "constant"), (rows[1]["i"], "truth")}
    todo = G.todo_rows(rows, ("truth", "constant"), done)
    assert [(r["i"], w) for r, w in todo] == [(rows[1]["i"], ["constant"]), (rows[2]["i"], ["truth", "constant"]),
                                              (rows[3]["i"], ["truth", "constant"])]


def test_gate_rows_read_every_shard_and_skip_a_torn_line(tmp_path):
    p0, p1 = G.rows_path(tmp_path, "D", 0, 3), G.rows_path(tmp_path, "D", 1, 3)
    p0.parent.mkdir(parents=True)
    p0.write_text('{"i": 1, "judge": {"A": 1.0}}\n{"i": 2, "judge": {"A": 2.0}}\n{"i": 3, "jud')
    p1.write_text('{"i": 4, "judge": {"A": 4.0}}\n')
    got = G.gate_rows(tmp_path, "D")
    assert sorted(got) == [1, 2, 4] and got[4]["judge"]["A"] == 4.0
    assert G.gate_rows(tmp_path, "D0") == {}


def test_parse_what_keeps_the_render_order():
    assert G.parse_what("constant,truth") == ("truth", "constant")
    assert G.parse_what("D0,D") == ("D", "D0")
    for bad in ("", "truth,truth", "E"):
        with pytest.raises(Exception):
            G.parse_what(bad)


def test_audit_sample_is_fixed():
    ids = list(range(1000, 2407))
    a = G.audit_ids(ids)
    assert len(a) == G.AUDIT_N and a == G.audit_ids(list(reversed(ids)))


def test_gate_render_counts_against_the_machine_cap():
    from learn import local_objective as LO

    assert any(re.search(p, "python -m learn.direct_sound_gate gate-render --what D --shard 0/3") for p in LO.RENDERS)
    assert not any(re.search(p, "python -m learn.direct_sound_gate gate-report") for p in LO.RENDERS)
    assert not any(re.search(p, "python -m learn.direct_sound_gate gate-predict") for p in LO.RENDERS)


def test_truth_flac_round_trips_without_clipping(tmp_path):
    pytest.importorskip("soundfile")
    y = np.sin(np.linspace(0, 200, 48_000)) * 1.7
    assert G.pow2_scale(y) == 2.0 and G.pow2_scale(y / 4) == 1.0
    p = tmp_path / "t.flac"
    s, sha = G.write_flac(p, y, 48_000)
    back = G.read_flac(p, s, sha)
    assert np.max(np.abs(back - y)) < 2 * 2.0 / 2 ** 23
    with pytest.raises(SystemExit):
        G.read_flac(p, s, "0" * 64)


def test_step3_verdict_passes_only_a_real_current_gate_ok(tmp_path):
    (tmp_path / "gate").mkdir()
    (tmp_path / "full").mkdir()
    ro = tmp_path / "full" / "readout.json"
    ro.write_text('{"readout_rule": "amendment 5"}')
    sha = DS.hashlib_file(ro)
    assert G.step3_verdict(tmp_path)[0] is False                                   # no report

    def rep(**kw):
        DS._save(tmp_path / "gate" / "report.json", {"decision": "OK", "smoke": False, "readout_sha256": sha, **kw})

    rep()
    assert G.step3_verdict(tmp_path) == (True, "GATE OK (amendment 6)")
    rep(decision="STOP")
    assert G.step3_verdict(tmp_path) == (False, "GATE STOP")
    rep(decision="INCOMPLETE")
    assert G.step3_verdict(tmp_path)[0] is False
    rep(smoke=True)
    assert G.step3_verdict(tmp_path)[0] is False
    rep()
    ro.write_text('{"readout_rule": "amendment 5", "changed": 1}')
    assert G.step3_verdict(tmp_path)[0] is False
