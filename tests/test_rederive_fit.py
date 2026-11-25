"""The re-derivation's fit and builders (`learn/rederive_fit.py`, `docs/rederive-plan.md` section 6): the candidates and
the declared "simpler" total order, the secant step, the repeat tolerances, the cycle rule, the pass used, the safety
stop, the pick with its tie interval, the ledger body (part tags only), the guards and the refusals. Synthetic keys;
pure: runs on the light CI runner (no numpy). The last tests need numpy, scipy, noisereduce and pyloudnorm: on a
made-up note list with a stub bank each iterated candidate returns the planted values in its own domain, the veto adds
no mute, the rule off is `rebuild_redo` byte for byte, reruns are byte-identical, and the five commands run end to end
on three made-up parts in one process and in two shards with the combine, byte for byte (skipped elsewhere). The
interface Unit 4 reads (the build record, its per-part record, the freeze body) is pinned."""
import ast
import json
import math
import pathlib

import pytest

from learn import note_rebuild as NR
from learn import note_transcribe as NT
from learn import scratch_exact as SE
from learn import scratch_rederive as RD
from learn import scratch_search as S
from learn import rederive_fit as F

REPO = pathlib.Path(__file__).resolve().parents[1]


def _args(**kw):
    return type("A", (), dict(kw))()


def _v(tuning=0.0, mutes=(), tilt=0.0, levels=(0.0, 0.0)):
    return {"tuning": tuning, "mutes": list(mutes), "tilt": tilt, "levels": list(levels)}


# --- the candidates and the order ---------------------------------------------------------------------------------------------

def test_the_twelve_candidates_in_the_declared_simpler_order():
    assert F.ORDER == (
        "today",
        "unfinished/one/as-now", "unfinished/one/veto", "measured/one/as-now", "measured/one/veto",
        "finished/one/as-now", "finished/one/veto",
        "unfinished/iterated/as-now", "unfinished/iterated/veto", "measured/iterated/as-now",
        "measured/iterated/veto", "finished/iterated/as-now", "finished/iterated/veto")
    assert len(F.CANDIDATES) == RD.FIT["candidates"] == 12 and len(F.ITERATED) == 6
    keys = [F.simpler_key(c) for c in F.ORDER]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)              # a total order
    F.fit_guard()


def test_the_simpler_order_rule_by_rule():
    k = F.simpler_key
    assert all(k("today") < k(c) for c in F.CANDIDATES)                      # today's rule before all
    assert k("finished/one/veto") < k("unfinished/iterated/as-now")          # fewer passes first
    assert k("unfinished/one/veto") < k("measured/one/as-now") < k("finished/one/as-now")   # then the domain
    assert k("measured/iterated/as-now") < k("measured/iterated/veto")       # then mutes as now before the veto
    assert F.DOMAINS == ("unfinished", "measured", "finished") and F.MUTE_RULES == ("as-now", "veto")


def test_candidate_ids_parse_and_refuse():
    assert F.candidate("today") is None
    assert F.candidate("measured/iterated/veto") == {"domain": "measured", "passes": "iterated", "mutes": "veto"}
    assert F.iterated_of("finished/one/as-now") == "finished/iterated/as-now"
    for bad in ("measured", "raw/one/veto", "measured/two/veto", "measured/one/off", 3):
        with pytest.raises(ValueError):
            F.candidate(bad)


def test_the_fits_constants_are_the_declared_ones(monkeypatch):
    assert (F.TOL_TUNING, F.TOL_LEVEL, F.TOL_TILT) == (0.05, 0.01, 0.027)
    assert F.VETO_S == NR.MUTE_FADE_S == 0.030 and F.MAX_PASSES == 64
    assert F.TILT_LIMIT == NR.TILT_MAX_DB_S and F.LEVEL_LIMIT == NR.ORACLE_CLAMP_DB and F.TUNING_LIMIT == 50.0
    assert F.FIT is RD.FIT                                                   # imported, never redefined
    monkeypatch.setattr(F, "TOL_TILT", 0.03)
    with pytest.raises(SystemExit, match="tolerances"):
        F.fit_guard()


def test_the_module_imports_only_the_standard_library_at_module_level():
    tree = ast.parse((REPO / "learn" / "rederive_fit.py").read_text())
    mods = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module.split(".")[0])
    assert mods <= {"__future__", "argparse", "hashlib", "json", "math", "pathlib", "statistics", "time", "learn"}


def test_the_core_is_imported_not_redefined():
    tree = ast.parse((REPO / "learn" / "rederive_fit.py").read_text())
    defs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    assert not defs & {"derive", "compose", "input_form", "unfinished", "_synth", "values_json", "value_errors"}
    assert not any(isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "FIT" and not
                                                     isinstance(n.value, ast.Attribute) for t in n.targets)
                   for n in tree.body)


# --- the update rules -------------------------------------------------------------------------------------------------------------

def test_the_tuning_difference_wraps():
    assert F.wrap_cents(10.0) == 10.0 and F.wrap_cents(60.0) == -40.0 and F.wrap_cents(-55.0) == 45.0
    assert F.wrap_cents(-50.0) == -50.0 and F.wrap_cents(50.0) == -50.0


def test_the_secant_step():
    # a linear response E(V) = 0.1 V (the plain step closes 10% a pass): the secant lands on the root at once
    target = 1.0

    def d(v):
        return target - 0.1 * v
    v0 = 0.0
    v1 = v0 + d(v0)
    v2, how = F.secant(v1, v0, d(v1), d(v0), 0.027)
    assert how == "secant" and v2 == pytest.approx(10.0)
    assert F.secant(1.0, 1.0, 0.5, 0.7, 0.027) == (1.5, "plain")            # no change: the plain step
    assert F.secant(1.0, 0.99, 0.5, 0.7, 0.027) == (1.5, "plain")           # a change under the resolution
    assert F.secant(2.0, 1.0, 0.5, 0.3, 0.027) == (2.5, "plain")            # a slope not above zero
    assert F.secant(2.0, 1.0, 0.5, 0.5, 0.027) == (2.5, "plain")            # a zero slope
    assert F.secant(2.0, math.nan, 0.5, 0.3, 0.027)[1] == "plain"
    assert F.clamp(14.0, 12.0) == 12.0 and F.clamp(-60.0, 50.0) == -50.0


def test_the_repeat_tolerances():
    a = _v(0.0, [1.0, 2.0], 0.0, [0.0, -0.5])
    assert F.repeats(a, a)
    assert F.repeats(dict(a, tuning=0.0499), a) and not F.repeats(dict(a, tuning=0.05), a)       # moved under
    assert F.repeats(dict(a, tuning=-0.0499), a) and not F.repeats(dict(a, tuning=-0.05), a)
    assert F.repeats(dict(a, tilt=0.0269), a) and not F.repeats(dict(a, tilt=0.027), a)
    assert F.repeats(dict(a, levels=[0.0099, -0.5]), a) and not F.repeats(dict(a, levels=[0.01, -0.5]), a)
    assert not F.repeats(dict(a, mutes=[1.0, 2.0000001]), a)                 # the mute list must be identical
    assert not F.repeats(dict(a, mutes=[1.0]), a)
    with pytest.raises(ValueError, match="onset groups"):
        F.repeats(dict(a, levels=[0.0]), a)


def test_the_cycle_rule_matches_within_the_repeat_tolerances():
    A, B, C = _v(1.0), _v(2.0), _v(3.0)
    assert F.cycle_match([A, B, C, _v(2.02)], 3) == 1                       # pass 3 matches pass 1 (not its predecessor)
    assert F.cycle_match([A, B, C, _v(3.01)], 3) is None                    # its predecessor never counts
    assert F.cycle_match([A, B, C, _v(1.0)], 3) is None                     # pass 0 (today's rule) never counts
    assert F.cycle_match([A, B, C, B, _v(2.0)], 4) == 1                     # the earliest match
    assert F.cycle_match([A, B, C, _v(9.0), _v(2.06)], 4) is None           # outside the tolerance: no match


def _trace(res):
    return [{"pass": k, "values": _v(float(k)), "residual": r} for k, r in enumerate(res)]


def test_the_pass_used():
    t = _trace([None, 0.5, 0.3, 0.4, 0.3, 0.2, None])
    assert F.pass_used(t, {"kind": "today", "at": 0}, 10) == 0
    assert F.pass_used(t, {"kind": "one", "at": 1}, 10) == 1
    assert F.pass_used(t, {"kind": "repeat", "at": 6}, 6) == 6               # repeated at or before the stop: that pass
    assert F.pass_used(t, {"kind": "repeat", "at": 6}, 4) == 2               # after it: the lowest in 1..stop (a tie:
    assert F.pass_used(t, {"kind": "cycle", "at": 5, "matches": 3}, 6) == 4  # the earliest); a cycle: its members 3..4
    assert F.pass_used(t, {"kind": "cycle", "at": 5, "matches": 2}, 6) == 2  # members 2..4, a tie: the earliest
    assert F.pass_used(t, {"kind": "cycle", "at": 5, "matches": 1}, 6) == 2
    assert F.pass_used(t, {"kind": "cycle", "at": 5, "matches": 1}, 3) == 2  # cycled after the stop: 1..3
    assert F.pass_used(t, {"kind": "limit", "at": 6}, 5) == 5
    nf = _trace([None, None, 0.4])
    nf[1]["residual_nonfinite"] = True                                      # a non-finite residual counts as the largest
    assert F.pass_used(nf, {"kind": "limit", "at": 2}, 2) == 2
    with pytest.raises(ValueError, match="no residual"):
        F.pass_used(t, {"kind": "limit", "at": 6}, 6)                        # pass 6 was never measured
    with pytest.raises(ValueError, match="before the stop"):
        F.pass_used(t, {"kind": "limit", "at": 6}, 9)
    with pytest.raises(ValueError, match="not a pass count"):
        F.pass_used(t, {"kind": "limit", "at": 6}, 0)


def test_the_safety_stop_and_its_hits():
    ends = {"a": {"kind": "repeat", "at": 7}, "b": {"kind": "repeat", "at": 12}, "c": {"kind": "limit", "at": 64},
            "d": {"kind": "cycle", "at": 9, "matches": 3}, "e": {"kind": "cycle", "at": 20, "matches": 4}}
    stop, hits = F.safety_stop(ends)
    assert stop == 12 and hits == ["c", "e"]                                 # the largest repeat; the rest listed
    assert F.safety_stop({"a": {"kind": "limit", "at": 64}}) == (None, ["a"])
    assert not F.reached({"kind": "repeat", "at": 12}, 12) and F.reached({"kind": "repeat", "at": 13}, 12)
    assert not F.reached({"kind": "one", "at": 1}, 1) and not F.reached({"kind": "today", "at": 0}, 1)


def test_values_for_reads_each_rule_from_the_traces():
    tr = {c: {"trace": _trace([0.9, 0.5, 0.3, 0.4]), "end": {"kind": "limit", "at": 3}} for c in F.ITERATED}
    tr["measured/iterated/veto"]["end"] = {"kind": "repeat", "at": 3}
    assert F.values_for(tr, "today", 2) == (_v(0.0), 0, False)
    assert F.values_for(tr, "measured/one/veto", 2) == (_v(1.0), 1, False)
    assert F.values_for(tr, "measured/iterated/veto", 3) == (_v(3.0), 3, False)
    assert F.values_for(tr, "finished/iterated/as-now", 3) == (_v(2.0), 2, True)
    tr["unfinished/iterated/veto"]["trace"][0]["values"] = _v(0.5)
    with pytest.raises(ValueError, match="today's rule differs"):
        F.values_for(tr, "today", 2)


# --- the pick ---------------------------------------------------------------------------------------------------------------------

def _iv_from(half):
    def iv(vals):
        m = sum(vals.values()) / len(vals)
        return {"mean": m, "lo90": m - half, "hi90": m + half}
    return iv


def _dist(means):
    return {c: {"p1": means.get(c, 5.0) - 0.1, "p2": means.get(c, 5.0) + 0.1} for c in F.ORDER}


def test_the_pick_takes_the_lowest_when_nothing_ties():
    p = F.pick(_dist({"finished/iterated/veto": 1.0, "today": 3.0}), _iv_from(0.01))
    assert p["candidate"] == p["lowest"] == "finished/iterated/veto" and p["ties"] == []
    assert p["less_lowest"]["today"]["mean"] == pytest.approx(2.0) and not p["less_lowest"]["today"]["tie"]


def test_a_tie_goes_to_the_simpler():
    means = {"finished/iterated/veto": 1.0, "measured/one/veto": 1.05, "unfinished/iterated/as-now": 1.02}
    p = F.pick(_dist(means), _iv_from(0.06))
    assert p["lowest"] == "finished/iterated/veto"
    assert p["ties"] == ["measured/one/veto", "unfinished/iterated/as-now"] and p["candidate"] == "measured/one/veto"
    p = F.pick(_dist(dict(means, today=1.0)), _iv_from(0.001))              # an equal mean: the simpler is lowest
    assert p["lowest"] == p["candidate"] == "today"


def test_an_end_at_zero_ties_and_an_unusable_interval_refuses():
    def iv(vals):
        m = sum(vals.values()) / len(vals)
        return {"mean": m, "lo90": 0.0 if m > 0 else m - 1, "hi90": m + 1}
    p = F.pick(_dist({"finished/iterated/veto": 1.0}), iv)
    assert p["candidate"] == "today" and len(p["ties"]) == 12
    with pytest.raises(SystemExit, match="no usable interval"):
        F.pick(_dist({}), lambda vals: None)
    d = _dist({})
    d["today"] = {"p1": 1.0}
    with pytest.raises(SystemExit, match="different parts"):
        F.pick(d, _iv_from(0.1))


# --- the ledger body, the paths, the price ------------------------------------------------------------------------------------

KEY1, KEY2 = "bks__unit-1@0.0|amp-1", "goat__item-2@3.0|amp-2"


def _records():
    conv = {"stop": 9, "fits": 12, "ends": {}, "hits": [{"part": KEY1, "candidate": "measured/iterated/veto",
                                                         "end": {"kind": "limit", "at": 64}, "pass_used": 4}]}
    bench = {"stop": 9, "converge_sha256": "c" * 64, "pick": {"candidate": "measured/iterated/veto", "lowest":
                                                              "measured/iterated/veto", "ties": []},
             "parts_n": 2, "deciding_n": 2, "sets": {KEY1: "bks", KEY2: "goat"}}
    builds = {"bench": {"stop": 9, "rule": "measured/iterated/veto", "bench_sha256": "b" * 64, "parts_n": 2,
                        "hits": []},
              "real": {"stop": 9, "rule": "measured/iterated/veto", "bench_sha256": "b" * 64, "parts_n": 2,
                       "hits": [{"part": KEY2, "candidate": "measured/iterated/veto",
                                 "end": {"kind": "limit", "at": 9}, "pass_used": 3}],
                       "rule_off_is_x": {"held": 2, "of": 2}}}
    shas = {"converge": "c" * 64, "bench": "b" * 64, "build_bench": "d" * 64, "build_real": "e" * 64}
    return conv, bench, builds, shas


def test_the_freeze_body_holds_the_rule_the_stop_and_both_builds_and_no_part_keys():
    conv, bench, builds, shas = _records()
    body = F.freeze_body(conv, bench, builds, shas)
    assert body["rule"] == {"candidate": "measured/iterated/veto", "domain": "measured", "passes": "iterated",
                            "mutes": "veto"}
    assert body["stop"] == 9 and body["build_bench"]["sha256"] == "d" * 64 and body["build_real"]["sha256"] == "e" * 64
    assert body["converge"]["hits"] == [{"part": F.part_tag(KEY1), "set": "bks", "candidate": "measured/iterated/veto",
                                         "end": {"kind": "limit", "at": 64}, "pass_used": 4}]
    assert body["build_real"]["hits"][0]["part"] == F.part_tag(KEY2) and body["renders"] == 0
    text = json.dumps(body)
    assert KEY1 not in text and KEY2 not in text and "unit-1" not in text and "amp-2" not in text
    assert len(F.part_tag(KEY1)) == 12 and F.part_tag(KEY1) != F.part_tag(KEY2)


@pytest.mark.parametrize("broken", ["stop", "rule", "chain"])
def test_the_freeze_body_refuses_records_that_do_not_chain(broken):
    conv, bench, builds, shas = _records()
    if broken == "stop":
        builds["real"]["stop"] = 8
    elif broken == "rule":
        builds["bench"]["rule"] = "today"
    else:
        builds["bench"]["bench_sha256"] = "x" * 64
    with pytest.raises(SystemExit):
        F.freeze_body(conv, bench, builds, shas)


def test_the_paths_sit_beside_the_ladders():
    assert F.fit_dir() == RD.rederive_dir() / "fit"
    for row in (RD.FIX_ROW, RD.REAL_ROW):
        p = F.guitar_path(row, "bks__k/1")
        assert p.parent.name == row and p.parent.parent == RD.rederive_dir() / "dry" and p.name == "bks__k__1.npy"
    for row in ("xf-now", "xn-list", "rf2"):
        with pytest.raises(ValueError):
            F.guitar_path(row, "k")
    assert F.trace_path("a/b").parent.parent == F.fit_dir() and F.build_record_path("real").name == "build-real.json"
    with pytest.raises(ValueError):
        F.build_record_path("other")


def test_the_price_projects_the_wall():
    timing = {"k1": {c: {"seconds": 10.0, "passes": 5} for c in F.ITERATED}}
    timing["k1"]["finished/iterated/veto"] = {"seconds": 40.0, "passes": 10}
    out = F.price_body(timing, {"k1": 48000 * 4}, {f"k{i}": 48000 * 4 for i in range(47)}, 48000, {"k1": 2.0})
    work = (5 * 5 + 10) * 4
    assert out["seconds_per_pass_per_audio_s"] == pytest.approx(90.0 / work)
    assert out["passes_mean"] == pytest.approx(35 / 6)
    assert out["projected_hours_mean"] == pytest.approx(90.0 / work * 47 * 4 * 6 * (35 / 6) / 3600)
    assert out["projected_hours_worst"] == pytest.approx(90.0 / work * 47 * 4 * 6 * 64 / 3600)
    assert out["priced_fits"] == 6 and out["passes_max"] == 10
    lat = out["later"]                                                     # the costliest candidate's later runs
    assert lat["candidate"] == "finished/iterated/veto" and lat["fits_per_part"] == 4 == sum(F.LATER_FITS.values())
    assert lat["hours_mean"] == pytest.approx(1.0 * 47 * 4 * 4 * 10 / 3600)          # 40 s / (10 passes x 4 s)
    assert lat["hours_worst"] == pytest.approx(1.0 * 47 * 4 * 4 * 64 / 3600)
    assert lat["compose_hours"] == pytest.approx(0.5 * 47 * 4 * F.LATER_COMPOSES / 3600)
    assert lat["by_step_hours_mean"] == {"bench in-U and in-F": round(2 * 47 * 4 * 10 / 3600, 2),
                                         "build-bench": round(47 * 4 * 10 / 3600, 2),
                                         "build-real": round(47 * 4 * 10 / 3600, 2)}
    assert out["by_candidate"]["finished/iterated/veto"]["seconds_per_pass_per_audio_s"] == pytest.approx(1.0)


def test_the_end_summary():
    ends = {("k1", c): {"kind": "repeat", "at": 4} for c in F.ITERATED}
    ends[("k2", F.ITERATED[0])] = {"kind": "limit", "at": 64}
    s = F.end_summary(ends)
    assert s[F.ITERATED[0]] == {"fits": 2, "repeat": 1, "cycle": 0, "limit": 1, "repeat_at_median": 4,
                                "repeat_at_max": 4}


def test_the_interface_unit_4_reads_is_pinned():
    """The three key sets Unit 4 (`learn/rederive_rows.py`) is coded against: the build record, its per-part record
    and the freeze body. A rename here is a break there."""
    assert F.BUILD_PART_FIELDS == {
        "bench": ("file_sha256", "audio_sha256", "values", "pass_used", "end", "reached", "identical_to_now",
                  "identical_to_x"),
        "real": ("file_sha256", "audio_sha256", "values", "pass_used", "end", "reached", "identical_to_x")}
    assert F.BUILD_FIELDS == {
        "bench": ("plan", "renders", "row", "input", "rule", "stop", "bench_sha256", "parts_n", "hits",
                  "identical_to_now", "parts"),
        "real": ("plan", "renders", "row", "build", "input", "rule", "stop", "bench_sha256", "parts_n", "hits",
                 "rule_off_is_x", "identical_to_x", "parts")}
    assert F.FREEZE_FIELDS == ("plan", "renders", "rule", "stop", "max_passes", "fit", "choices", "converge", "bench",
                               "build_bench", "build_real")
    end = {"kind": "limit", "at": 9}
    for which in ("bench", "real"):
        rec = F.build_part_record(which, "f" * 64, "a" * 64, _v(), 3, end, True, False, True)
        assert tuple(rec) == F.BUILD_PART_FIELDS[which]
        per = {KEY2: {"record": rec, "rule_off_is_x": True}, KEY1: {"record": dict(rec, reached=False),
                                                                    "rule_off_is_x": True}}
        out = F.build_record(which, "measured/iterated/veto", 9, "b" * 64, per)
        assert tuple(out) == F.BUILD_FIELDS[which] and list(out["parts"]) == [KEY1, KEY2]
        assert out["row"] == {"bench": RD.FIX_ROW, "real": RD.REAL_ROW}[which] and out["parts_n"] == 2
        assert out["hits"] == [{"part": KEY2, "candidate": "measured/iterated/veto", "end": end, "pass_used": 3}]
    assert out["rule_off_is_x"] == {"held": 2, "of": 2} and out["build"] == RD.REAL_BUILD
    with pytest.raises(ValueError):
        F.build_part_record("other", "f", "a", _v(), 1, end, False, False)
    body = F.freeze_body(*_records())
    assert tuple(body) == F.FREEZE_FIELDS
    for sec, fields in F.FREEZE_SECTION_FIELDS.items():
        assert tuple(body[sec]) == fields, sec
    for sec in ("converge", "build_bench", "build_real"):
        assert all(tuple(h) == F.HIT_FIELDS for h in body[sec]["hits"])


def test_the_shards_take_fixed_slices_by_key():
    keys = [f"k{i:02d}" for i in range(47)]
    sl = [F.shard_keys(reversed(keys), (k, 3)) for k in range(3)]
    assert sorted(sum(sl, [])) == keys and not set(sl[0]) & set(sl[1]) and sl[0][:2] == ["k00", "k03"]
    assert F.shard_keys(keys, None) == keys and [len(x) for x in sl] == [16, 16, 15]
    assert F.shard_arg("1/4") == (1, 4) and F.shard_arg("7/8") == (7, 8)
    for bad in ("4/4", "0/9", "-1/2", "x", "1"):
        with pytest.raises(Exception):
            F.shard_arg(bad)
    assert F.run_mode(_args()) == "one" and F.run_mode(_args(shard=(0, 2))) == "shard"
    assert F.run_mode(_args(combine=True)) == "combine" and F.run_mode(_args(price=2), price_ok=True) == "price"
    with pytest.raises(SystemExit, match="converge's"):
        F.run_mode(_args(price=2))
    with pytest.raises(SystemExit, match="separate steps"):
        F.run_mode(_args(shard=(0, 2), combine=True))


def test_a_trace_must_be_of_the_ladders_input():
    want = {KEY1: "a" * 64, KEY2: "b" * 64}
    recs = {KEY1: {"part": KEY1, "input_sha256": "a" * 64}, KEY2: {"part": KEY2, "input_sha256": "b" * 64}}
    assert F.trace_refusal(recs, want) is None and F.trace_refusal({}, want) is None
    for bad in ({KEY2: {"part": KEY2, "input_sha256": "c" * 64}}, {KEY2: {"part": KEY1, "input_sha256": "b" * 64}},
                {KEY2: {"part": KEY2}}, {KEY3: {"part": KEY3, "input_sha256": "a" * 64}}):
        why = F.trace_refusal(dict(recs, **bad), want)
        assert "not of the ladder's in-M input" in why and KEY2 not in why and KEY3 not in why


# --- the guards and the CLI ---------------------------------------------------------------------------------------------------

MAIN = {S.PHASE: 1, S.PHASE_DRAW: {}, SE.PHASE_BANK: {}, SE.PHASE: {}, SE.PHASE_TARGETS: {}, RD.PHASE: {}}


@pytest.mark.parametrize("cmd", sorted(F.COMMANDS))
def test_every_command_refuses_off_main(monkeypatch, cmd):
    monkeypatch.setattr(S, "on_main", lambda: (None, "this checkout's learn/scratch_search.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        F.COMMANDS[cmd](_args(price=None))


@pytest.mark.parametrize("cmd", sorted(F.COMMANDS))
def test_every_command_refuses_without_the_ladders_hash_on_main(monkeypatch, cmd):
    monkeypatch.setattr(S, "on_main", lambda: (dict(MAIN), None))
    with pytest.raises(SystemExit, match="has no phase_scratch_rederive_ladder"):
        F.COMMANDS[cmd](_args(price=None))


@pytest.mark.parametrize("cmd", sorted(F.COMMANDS))
def test_every_command_refuses_with_this_module_off_main(monkeypatch, cmd):
    from learn import note_replay as NRP

    main = dict(MAIN, **{RD.PHASE_LADDER: {"sha256": "0" * 64}})
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    monkeypatch.setattr(RD, "pinned_identity", lambda: {f: True for f in RD.CODE_FILES})
    monkeypatch.setattr(NRP, "ledger_entry", lambda: main)
    monkeypatch.setattr(F, "own_identity", lambda: {"learn/rederive_fit.py": False})
    with pytest.raises(SystemExit, match="rederive_fit.py.*differ from main's"):
        F.COMMANDS[cmd](_args(price=None))


def test_the_cli():
    assert sorted(F.COMMANDS) == ["bench", "build-bench", "build-real", "converge", "freeze"]
    with pytest.raises(SystemExit):
        F.main(["ladder"])
    with pytest.raises(SystemExit):
        F.main(["bench", "--price", "2"])
    for argv in (["freeze", "--combine"], ["freeze", "--shard", "0/2"], ["bench", "--shard", "2/2"]):
        with pytest.raises(SystemExit):
            F.main(argv)
    assert F.SHARDED == ("converge", "bench", "build-bench", "build-real")
    assert F.CODE_FILES[0] == "learn/rederive_fit.py" and set(RD.CODE_FILES) <= set(F.CODE_FILES)


def test_converge_refuses_a_price_off_two_or_three_and_a_run_before_its_price(monkeypatch, tmp_path):
    monkeypatch.setattr(F, "require_fit", lambda *a: {})
    monkeypatch.setattr(RD, "rederive_dir", lambda: tmp_path)
    monkeypatch.setattr(F, "_main_parts", lambda m: [KEY1, KEY2])
    with pytest.raises(SystemExit, match="--price takes"):
        F.cmd_converge(_args(price=5))
    with pytest.raises(SystemExit, match="no price.json"):
        F.cmd_converge(_args(price=None))


def test_the_records_are_never_overwritten(monkeypatch, tmp_path):
    monkeypatch.setattr(F, "require_fit", lambda *a: {})
    monkeypatch.setattr(RD, "rederive_dir", lambda: tmp_path)
    for path, cmd in ((F.frozen_path, F.cmd_freeze), (F.bench_path, F.cmd_bench),
                      (lambda: F.build_record_path("bench"), F.cmd_build_bench),
                      (lambda: F.build_record_path("real"), F.cmd_build_real)):
        path().parent.mkdir(parents=True, exist_ok=True)
        path().write_text("{}")
        with pytest.raises(SystemExit, match="never overwritten"):
            cmd(_args(price=None))


# --- the fit on a made-up part (numpy; skipped on the light runner) -------------------------------------------------------------

def _needs():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    pytest.importorskip("noisereduce")
    pytest.importorskip("pyloudnorm")
    return np


_BANK = {}


def _bank():
    np = _needs()
    if "b" not in _BANK:
        SR = NR.SR

        def tone(midi, seconds=3.0, decay=1.2, seed=0):
            t = np.arange(int(seconds * SR)) / SR
            f0 = 440 * 2 ** ((midi - 69) / 12)
            y = sum(np.sin(2 * np.pi * h * f0 * t) / h for h in range(1, 6)) * np.exp(-t / decay)
            y = np.concatenate([np.zeros(int(0.01 * SR)), y])[:len(t)]
            return 0.3 * y / np.abs(y).max() + 1e-4 * np.random.default_rng(seed).standard_normal(len(t))
        _BANK["b"] = NR.Bank(None, loader=lambda s, f: (tone(NR.OPEN_STRINGS[s] + f, seed=s * 100 + f), SR))
    return _BANK["b"]


def _measure(x):
    """A stand-in for song_bank.measure: a fixed tilt EQ, then a fixed RMS."""
    np = _needs()
    import scipy.signal as ss

    y = ss.lfilter([1.0, -0.6], [1.0], np.asarray(x, np.float64))
    return 0.05 * y / (np.sqrt(np.mean(y ** 2)) + 1e-12)


def _finish(y):
    return 0.5 * _measure(y)


def _ringing_part(length_s=5.6, k=7):
    """Notes that ring on (no drop of their own), isolated enough for a tilt: a part whose drops are its mutes."""
    _needs()
    notes = [{"on": 0.3 + 0.75 * j, "off": 0.3 + 0.75 * j + 2.0, "pitch": 52 + (j * 5) % 12, "bends": []}
             for j in range(k)]
    return F.Part(notes, int(length_s * NR.SR), _bank(), "ring-soft", None, _finish, _measure)


def _planted(p, mutes):
    ok = F.usable_groups(p)
    lv = F.centred([(-1) ** j * 2.0 + 0.3 * j for j in range(len(ok))], ok)
    return {"tuning": 7.0, "mutes": list(mutes), "tilt": -4.0, "levels": lv}


def _close(V, T):
    return (abs(V["tuning"] - T["tuning"]) < F.TOL_TUNING and abs(V["tilt"] - T["tilt"]) < F.TOL_TILT
            and all(abs(a - b) < F.TOL_LEVEL for a, b in zip(V["levels"], T["levels"])))


@pytest.mark.parametrize("cid", F.ITERATED)
def test_each_iterated_candidate_returns_the_planted_values_in_its_own_domain(cid):
    """The input is the planted values' rebuild in the candidate's own domain; today's rule (pass 0) misses them; the
    fit returns them within the repeat tolerances, the mutes too (as now: with the detector's double reading, which
    changes no sample)."""
    np = _needs()
    p = _ringing_part()
    dom = F.candidate(cid)["domain"]
    for mutes in ([], [2.3]):
        T = _planted(p, mutes)
        u = F.rebuild_in(p, T, dom)
        f = F.fit(p, u, cid)
        V, R = f["values"], f["trace"][0]["values"]
        assert f["end"]["kind"] == "repeat" and f["pass_used"] == f["end"]["at"] <= 10
        assert not _close(R, T) and _close(V, T)
        if F.candidate(cid)["mutes"] == "veto" or not mutes:
            assert V["mutes"] == pytest.approx(T["mutes"], abs=1e-9)
        else:
            assert V["mutes"][0] == pytest.approx(2.3, abs=1e-9) and len(V["mutes"]) == 2
            y1 = F.rebuild_in(p, V, dom)
            y2 = F.rebuild_in(p, dict(V, mutes=T["mutes"]), dom)
            assert np.array_equal(y1, y2)                                    # the second mute cuts nothing


def test_the_veto_adds_no_mute_to_a_mute_free_list():
    _needs()
    p = _ringing_part(4.4, 5)
    T = _planted(p, [])
    for dom in F.DOMAINS:
        u = F.rebuild_in(p, T, dom)
        assert NR.mute_times(u) == []
        assert F.veto_members(p, [], [], T, dom) == []
        for passes in F.PASSES:
            f = F.fit(p, u, F.candidate_id(dom, passes, "veto"))
            assert all(t["values"]["mutes"] == [] for t in f["trace"])


def test_the_veto_keeps_only_drops_the_rebuild_does_not_make_itself():
    """Short notes whose releases the detector reads as drops: the rebuild makes them itself, so the veto keeps none
    (the planted list, no mutes) where today's rule and the as-now rule keep every one."""
    _needs()
    notes = [{"on": 0.3 + 1.0 * j, "off": 0.6 + 1.0 * j, "pitch": 52 + (j * 5) % 12, "bends": []} for j in range(4)]
    p = F.Part(notes, int(4.4 * NR.SR), _bank(), "ring-soft")
    T = {"tuning": -6.0, "mutes": [], "tilt": 0.0, "levels": F.centred([0.0, 1.0, -1.0, 0.5], F.usable_groups(p))}
    u = F.rebuild_in(p, T, "unfinished")
    drops = NR.mute_times(u)
    assert len(drops) >= 4
    assert F.veto_members(p, drops, [0.0] * len(drops), T, "unfinished") == [False] * len(drops)
    for passes in F.PASSES:
        assert F.fit(p, u, f"unfinished/{passes}/veto")["values"]["mutes"] == []
    assert F.fit(p, u, "today")["values"]["mutes"] == drops
    f = F.fit(p, u, "unfinished/iterated/as-now")
    assert len(f["values"]["mutes"]) == len(drops)
    assert all(abs(o) <= F.VETO_S + 1e-12 for t in f["trace"] for o in t["mute_offsets_s"])   # held within 30 ms


def test_the_usable_rule_is_oracle_gains_own_and_centred_is_its_span_gains():
    np = _needs()
    n = int(3.0 * NR.SR)
    notes = [{"on": -0.1, "off": 0.5, "pitch": 52, "bends": []}] + [
        {"on": 0.3 + 0.6 * j, "off": 0.8 + 0.6 * j, "pitch": 55 + j, "bends": []} for j in range(4)] + [
        {"on": 3.0 - 0.005, "off": 3.2, "pitch": 60, "bends": []}]
    p = F.Part(notes, n, _bank(), "ring-soft")
    ok = F.usable_groups(p)
    assert ok == [False, True, True, True, True, False]       # begun before the window; a span under 10 ms
    plain, _ = RD._synth(notes, n, p.bank, p.ring, 0.0, [], 0.0, None, None, NR.SR, last=False)
    di = plain[:n] * (1 + np.linspace(0, 1, n))
    g = NR.oracle_gains(notes, plain[:n], di)
    assert [x == 0.0 for x, k in zip(g, ok) if not k] == [True, True] and all(x != 0.0 for x, k in zip(g, ok) if k)
    lv = [3.0, 1.0, -2.0, 25.0, -30.0, 4.0]
    assert F.centred(lv, ok) == NR._span_gains(lv, ok, NR.ORACLE_CLAMP_DB) == [0.0, 1.5, -1.5, 20.0, -20.0, 0.0]


def test_the_rule_off_is_rebuild_redo_byte_for_byte():
    np = _needs()
    p = _ringing_part()
    T = _planted(p, [2.3])
    for kind in ("in-F", "in-M", "in-U"):
        u = np.asarray(F.rebuild_in(p, T, {"in-F": "finished", "in-M": "measured", "in-U": "unfinished"}[kind]),
                       np.float64)
        want, _ = NR.rebuild_redo("tr-di", p.notes, p.n, p.bank, u, p.ring, finish=p.finish)
        f = F.fit(p, u, F.TODAY)
        assert f["pass_used"] == 0 and len(f["trace"]) == 1
        assert S.npy_sha(F.guitar(p, f["values"])) == S.npy_sha(want)
        assert F.guitar(p, f["values"]).tobytes() == np.asarray(want, np.float32).tobytes()


def test_one_pass_is_the_iterated_fits_first_pass_and_the_stop_reads_the_long_trace():
    _needs()
    p = _ringing_part()
    u = F.rebuild_in(p, _planted(p, [2.3]), "measured")
    long = F.fit(p, u, "measured/iterated/veto", 64)
    one = F.fit(p, u, "measured/one/veto")
    assert one["end"] == {"kind": "one", "at": 1} and one["values"] == long["trace"][1]["values"]
    assert long["end"]["at"] >= 3
    short = F.fit(p, u, "measured/iterated/veto", 2)                        # a stop before the repeat
    assert short["end"] == {"kind": "limit", "at": 2} and short["reached"]
    k = F.pass_used(long["trace"], long["end"], 2)
    assert short["values"] == long["trace"][k]["values"] and short["pass_used"] == k
    assert [t["values"] for t in short["trace"]] == [t["values"] for t in long["trace"][:3]]
    assert short["trace"][2]["residual"] == pytest.approx(long["trace"][2]["residual"], abs=0)


def test_reruns_are_byte_identical():
    _needs()
    p = _ringing_part()
    u = F.rebuild_in(p, _planted(p, [2.3]), "finished")
    a = F.fit(p, u, "finished/iterated/veto")
    q = _ringing_part()
    b = F.fit(q, u, "finished/iterated/veto")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert F.guitar(p, a["values"]).tobytes() == F.guitar(q, b["values"]).tobytes()


# --- the commands end to end on two made-up parts -------------------------------------------------------------------------

KEY3 = "bks__unit-3@1.5|amp-1"


def _made_up_parts():
    """Three parts as `bench_parts` yields them: the true DI (a planted rebuild with noise), T = derive(DI), X =
    compose(T), the in-M input of T, xf-now (today's rule handed in-M)."""
    np = _needs()
    out = []
    for key, set_, mutes in ((KEY1, "bks", [2.3]), (KEY2, "goat", []), (KEY3, "bks", [1.6])):
        p = _ringing_part(4.4, 5)
        p.key, p.set = key, set_
        clean = F.rebuild_in(p, _planted(p, mutes), "unfinished")
        di = clean * (1 + 0.2 * np.random.default_rng(len(key)).random(p.n))
        di = np.asarray(np.asarray(di, np.float32), np.float64)
        T, _ = RD.derive(p.notes, p.n, p.bank, di, p.ring)
        p.di, p.T = di, T
        p.X = np.asarray(F.guitar(p, T), np.float64)
        p.x_sha = S.npy_sha(p.X)
        p.u = p.form("in-M")
        p.now_sha = S.npy_sha(F.guitar(p, F.fit(p, p.u, F.TODAY)["values"]))
        out.append(p)
    return out


def _fake_world(monkeypatch, root, parts):
    monkeypatch.setattr(F, "require_fit", lambda *a: {})
    monkeypatch.setattr(RD, "rederive_dir", lambda: root)
    monkeypatch.setattr(F, "bench_parts", lambda m, keys=None: (q for q in parts if keys is None or q.key in keys))
    monkeypatch.setattr(F, "_main_parts", lambda m: sorted(q.key for q in parts))
    monkeypatch.setattr(F, "_part_lengths", lambda m: {q.key: q.n for q in parts})
    monkeypatch.setattr(F, "ladder_inputs", lambda m: {q.key: S.npy_sha(q.u) for q in parts})

    def iv(vals):
        m = sum(vals.values()) / len(vals)
        return {"mean": m, "lo90": m - 1e-9, "hi90": m + 1e-9}
    monkeypatch.setattr(F, "_interval_40", lambda: iv)


def _tree(root):
    return {str(f.relative_to(root)): f.read_bytes() for f in sorted(root.rglob("*")) if f.is_file()}


def test_the_five_commands_one_process_and_in_shards_byte_for_byte(monkeypatch, tmp_path, capsys):
    """One process (no flag) and two shards with the combine write the same files byte for byte (price.json, a
    timing, aside); the combine refuses until every part is there."""
    np = _needs()
    parts = _made_up_parts()
    _fake_world(monkeypatch, tmp_path / "a", parts)
    F.cmd_converge(_args(price=2))
    price = json.loads(F.price_path().read_text())
    assert price["priced_parts"] == 2 and price["priced_fits"] == 12 and price["projected_hours_worst"] > 0
    assert price["later"]["candidate"] in F.ITERATED and price["later"]["compose_hours"] > 0
    out = capsys.readouterr().out
    assert "projected wall" in out and "the later runs for the costliest" in out
    with pytest.raises(SystemExit, match="never overwritten"):
        F.cmd_converge(_args(price=2))
    F.cmd_converge(_args())                                                   # the priced parts' traces are kept
    conv = json.loads(F.converge_path().read_text())
    assert conv["fits"] == 18 and isinstance(conv["stop"], int) and conv["stop"] >= 1 and conv["priced_parts"] == 2
    ends = {(q.key, c): json.loads(F.trace_path(q.key).read_text())["fits"][c]["end"] for q in parts
            for c in F.ITERATED}
    assert conv["stop"] == max(e["at"] for e in ends.values() if e["kind"] == "repeat")
    assert sorted((h["part"], h["candidate"]) for h in conv["hits"]) == sorted(
        f for f, e in ends.items() if F.reached(e, conv["stop"]))
    F.cmd_bench(_args())
    bench = json.loads(F.bench_path().read_text())
    rule = bench["pick"]["candidate"]
    assert rule in F.ORDER and bench["parts_n"] == 3 and bench["deciding_n"] == 3
    assert bench["summary"]["the_40"]["today"]["identical_to_now"] == 3
    assert set(bench["beside_forms"]) == {"in-U", "in-F"}
    F.cmd_build_bench(_args())
    bb = json.loads(F.build_record_path("bench").read_text())
    assert tuple(bb) == F.BUILD_FIELDS["bench"]
    for q in parts:
        y = np.load(F.guitar_path(RD.FIX_ROW, q.key))
        r = bb["parts"][q.key]
        assert tuple(r) == F.BUILD_PART_FIELDS["bench"] and y.dtype == np.float32
        assert r["audio_sha256"] == S.npy_sha(y) == bench["parts"][q.key]["picked_sha256"]
        assert r["file_sha256"] == S.file_sha(F.guitar_path(RD.FIX_ROW, q.key))
    F.cmd_build_real(_args())
    br = json.loads(F.build_record_path("real").read_text())
    assert tuple(br) == F.BUILD_FIELDS["real"] and all(tuple(r) == F.BUILD_PART_FIELDS["real"]
                                                       for r in br["parts"].values())
    assert br["rule_off_is_x"] == {"held": 3, "of": 3} and br["stop"] == conv["stop"] and br["rule"] == rule
    capsys.readouterr()
    F.cmd_freeze(_args())
    body = json.loads(capsys.readouterr().out)[RD.PHASE_FROZEN]
    assert body["sha256"] == S.file_sha(F.frozen_path()) and body["rule"]["candidate"] == rule
    assert tuple(body)[1:] == F.FREEZE_FIELDS
    assert body["build_bench"]["sha256"] == S.file_sha(F.build_record_path("bench"))
    assert body["build_real"]["sha256"] == S.file_sha(F.build_record_path("real"))
    assert all(k not in json.dumps(body) for k in (KEY1, KEY2, KEY3))
    with pytest.raises(SystemExit, match="never overwritten"):
        F.cmd_freeze(_args())

    # the same in two shards, from nothing
    _fake_world(monkeypatch, tmp_path / "b", _made_up_parts())
    F.cmd_converge(_args(price=2))
    F.cmd_converge(_args(shard=(1, 2)))                                       # its one part was priced: kept
    with pytest.raises(SystemExit, match="not traced yet"):
        F.cmd_converge(_args(combine=True))
    F.cmd_converge(_args(shard=(0, 2)))
    F.cmd_converge(_args(combine=True))
    F.cmd_bench(_args(shard=(0, 2)))
    assert "the pick waits" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="stage A is not there"):
        F.cmd_bench(_args(combine=True))
    F.cmd_bench(_args(shard=(1, 2)))                                           # every stage A there: its stage B too
    with pytest.raises(SystemExit, match="stage B is not there"):
        F.cmd_bench(_args(combine=True))
    F.cmd_bench(_args(shard=(0, 2)))
    F.cmd_bench(_args(combine=True))
    for which, cmd in (("bench", F.cmd_build_bench), ("real", F.cmd_build_real)):
        cmd(_args(shard=(1, 2)))
        with pytest.raises(SystemExit, match="run every shard first"):
            cmd(_args(combine=True))
        cmd(_args(shard=(0, 2)))
        cmd(_args(combine=True))
    F.cmd_freeze(_args())
    a, b = _tree(tmp_path / "a"), _tree(tmp_path / "b")
    a.pop("fit/price.json")
    b.pop("fit/price.json")
    assert sorted(a) == sorted(b) and len(a) >= 3 * 6 + 4
    assert [k for k in a if a[k] != b[k]] == []


def test_converge_refuses_a_kept_trace_of_another_input(monkeypatch, tmp_path):
    _needs()
    parts = _made_up_parts()
    _fake_world(monkeypatch, tmp_path, parts)
    F.cmd_converge(_args(price=2))                                           # traces the first two parts by key
    good = F.ladder_inputs({})
    monkeypatch.setattr(F, "ladder_inputs", lambda m: dict(good, **{KEY1: "0" * 64}))
    for args in (_args(), _args(shard=(0, 2))):                              # reused by a run: refused
        with pytest.raises(SystemExit, match="not of the ladder's in-M input"):
            F.cmd_converge(args)
    monkeypatch.setattr(F, "ladder_inputs", lambda m: good)
    F.cmd_converge(_args(shard=(0, 2)))
    F.cmd_converge(_args(shard=(1, 2)))
    monkeypatch.setattr(F, "ladder_inputs", lambda m: dict(good, **{KEY3: "0" * 64}))
    with pytest.raises(SystemExit, match="not of the ladder's in-M input"):  # and at the combine
        F.cmd_converge(_args(combine=True))
    assert not F.converge_path().exists()
    monkeypatch.setattr(F, "ladder_inputs", lambda m: good)
    F.cmd_converge(_args(combine=True))
    assert F.converge_path().exists()


def test_build_real_refuses_when_the_rule_off_is_not_x(monkeypatch, tmp_path):
    _needs()
    parts = _made_up_parts()[:2]
    _fake_world(monkeypatch, tmp_path, parts)
    F.cmd_converge(_args(price=2))
    F.cmd_converge(_args())
    F.cmd_bench(_args())
    parts[0].x_sha = "0" * 64
    with pytest.raises(SystemExit, match="rule off on the true DI is not X"):
        F.cmd_build_real(_args())
