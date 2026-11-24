"""The from-scratch search's pure parts (`learn/scratch_search.py`, `docs/scratch-search-plan.md`): the subset, the
partners, the blank, the search-half guards, the shrink and the centre, the non-finite rule, the part's numbers, the
readings (B1's constant), B2's lever, OUTCOME_TABLE and the refusal stop (B5); step 1's loop against C2's own call.
Pure: runs on the light CI runner (no numpy). The last two tests need numpy and the stored data (skipped elsewhere):
the loop replays the stored C2 records' step-1 sequences exactly at zero renders (B3), and the blank leaves every
search-half evaluation unchanged when the held half is noise."""
import json
import math
import pathlib
import random

import pytest

from learn import scratch_search as S

REPO = pathlib.Path(__file__).resolve().parents[1]


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


PASS, CONST_I, FAIL, UND = _iv(-0.2, -0.3, -0.1), _iv(-0.02, -0.1, 0.06), _iv(0.0, -0.03, 0.03), _iv(-0.06, -0.2, 0.05)


# --- the readings -----------------------------------------------------------------------------------------------------------

def test_row_reading_codes_g_passing_with_i_not_passing_as_constant():
    assert S.row_reading(PASS, PASS)["reading"] == "passes"
    assert S.row_reading(PASS, UND)["reading"] == "constant"       # B1: I undecided
    assert S.row_reading(PASS, FAIL)["reading"] == "constant"      # B1: I fails
    assert S.row_reading(FAIL, PASS)["reading"] == "fails"
    assert S.row_reading(UND, PASS)["reading"] == "undecided"
    assert S.row_reading(UND, UND)["reading"] == "undecided"
    assert S.row_reading(None, PASS) is None


def test_number_reading_is_the_replays():
    from learn import note_replay as NR

    for row in (PASS, CONST_I, FAIL, UND, _iv(-0.09, -0.15, -0.03), _iv(-0.1, -0.2, -0.0001)):
        assert S.number_reading(row) == NR.number_reading(row)


def test_b2_lever_needs_all_three_conditions():
    assert S.b2_lever("undecided", "passes", -0.01, 0.0)
    assert not S.b2_lever("undecided", "passes", 0.01, -0.1)       # the panel's G mean above 0
    assert not S.b2_lever("undecided", "passes", -0.1, 0.02)       # the panel's I mean above 0
    assert not S.b2_lever("undecided", "undecided", -0.1, -0.1)    # BKS+GOAT not decided
    assert not S.b2_lever("undecided", "constant", -0.1, -0.1)
    assert not S.b2_lever("fails", "passes", -0.1, -0.1)           # (b) not undecided on the pool
    assert not S.b2_lever("undecided", "passes", None, -0.1)


def test_b_refined_reads_the_lever_from_the_report():
    rows = {"reading": {"reading": "undecided"}, "reading_bks_goat": {"reading": "passes"},
            "G": {"panel": {"mean": -0.01}}, "I": {"panel": {"mean": -0.02}}}
    assert S.b_refined("fs-stem", rows) == "undecided-b2"
    assert S.b_refined("fs-control", rows) == "undecided"
    rows["I"]["panel"]["mean"] = 0.03
    assert S.b_refined("fs-stem", rows) == "undecided"


# --- the outcome table ------------------------------------------------------------------------------------------------------

def test_table_guard_holds_and_no_path_reads_more_than_three_rows():
    S.table_guard()
    ps = S.paths()
    assert max(len(p) for p in ps) == 3                             # N1: the longest path
    assert all(len(S.table_hits(p)) == 1 for p in ps)


def test_the_cells():
    def code(**r):
        return S.outcome({{"b": "fs-stem", "c": "fs-both", "a": "fs-blur", "ctl": "fs-control"}[k]: v
                          for k, v in r.items()})
    assert code(b="passes", c="passes")["code"] == "F-both"
    assert code(b="passes", c="fails", a="passes")["code"] == "F-compound"
    assert code(b="passes", c="constant", a="undecided")["code"] == "F-dry"
    assert code(b="passes", c="undecided", a="constant")["code"] == "F-constant"
    assert code(b="fails", ctl="passes")["code"] == "F-stem"
    assert code(b="undecided", ctl="passes")["code"] == "F-undecided"
    assert code(b="undecided-b2", ctl="passes", c="passes")["code"] == "F-both"
    assert code(b="undecided-b2", ctl="passes", c="fails")["code"] == "F-undecided"
    assert code(b="undecided-b2", ctl="undecided")["code"] == "F-start"
    assert code(b="fails", ctl="fails")["code"] == "F-start"
    assert code(b="constant", ctl="undecided")["code"] == "F-start"
    # B1: a better constant never lands in F-stem
    got = code(b="constant", ctl="passes")
    assert got["code"] == "F-constant" and "row b" in got["reading"]
    assert code(b="fails", ctl="constant")["code"] == "F-constant"
    assert code(b="undecided-b2", ctl="passes", c="constant")["code"] == "F-constant"


def test_next_row_follows_the_coded_cells():
    assert S.next_row({}) == "fs-stem"
    assert S.next_row({"fs-stem": "passes"}) == "fs-both"
    assert S.next_row({"fs-stem": "passes", "fs-both": "passes"}) is None
    assert S.next_row({"fs-stem": "passes", "fs-both": "constant"}) == "fs-blur"
    for b in ("fails", "undecided", "undecided-b2", "constant"):
        assert S.next_row({"fs-stem": b}) == "fs-control"
    assert S.next_row({"fs-stem": "undecided-b2", "fs-control": "passes"}) == "fs-both"   # B2's lever
    assert S.next_row({"fs-stem": "undecided-b2", "fs-control": "fails"}) is None
    assert S.next_row({"fs-stem": "undecided", "fs-control": "passes"}) is None
    assert S.outcome({"fs-stem": "passes"})["next_row"] == "fs-both"


def test_a_stopped_row_stops_the_read():
    assert S.outcome({"fs-stem": "stopped"})["code"] == "stopped"


def test_no_row_stops_on_a_count_of_refusals():
    assert not hasattr(S, "REFUSAL_STOP") and S.REFUSAL_CONF == 0.90
    assert not S.stopped({"a": 1, "b": 2}) and not S.stopped({k: 1 for k in "abcdefgh"})
    o = S.outcome({"fs-stem": "stopped"})
    assert "pool lost the panel" in o["reading"] and "refusal count" not in o["reading"]


def test_the_pool_must_keep_the_panel():
    full = {"G": {"deciding_sets": ["bks", "goat", "panel"]}, "I": {"deciding_sets": ["bks", "goat", "panel"]}}
    assert S.pool_refusal(full) is None
    lost = {"G": {"deciding_sets": ["bks", "goat"]}, "I": {"deciding_sets": ["bks", "goat", "panel"]}}
    assert "G" in S.pool_refusal(lost) and "I" not in S.pool_refusal(lost).split(" is ")[0]
    assert S.pool_refusal({"G": {}, "I": {}})


def test_the_pool_falls_back_on_one_lost_panel_di_file():
    """The reason for `pool_refusal`: `full_controls_c3r.deciding_sets` drops the panel under 3 DI files."""
    from learn import full_controls_c3r as R

    assert list(R.deciding_sets(3)) == S.DECIDING
    assert list(R.deciding_sets(2)) == ["bks", "goat"]


def test_a_constant_on_the_path_is_noted():
    got = S.outcome({"fs-stem": "passes", "fs-both": "constant", "fs-blur": "passes"})
    assert got["code"] == "F-compound" and any("row c" in n for n in got["notes"])


def test_the_phases_are_new_and_named_as_declared():
    assert S.phase_answers("fs-stem") == "phase_fs_answers_stem"
    assert S.phase_answers("fs-control") == "phase_fs_answers_control"
    d = json.loads((REPO / "docs/dev-test-ledger.json").read_text())
    e = next(t for t in d["tests"] if t.get("test_id") == S.LEDGER_ID)
    declared = {S.PHASE, S.PHASE_DRAW, S.PHASE_OUTCOME} | {S.phase_answers(r) for r in S.ROWS}
    assert set(S.fs_keys(e)) <= declared


# --- the subset and the partners --------------------------------------------------------------------------------------------

def _replay_like():
    rng = random.Random(7)
    parts = []
    for d in range(8):                                    # BKS: 8 DI files, 5 parts each on rotating amps
        for u in range(5):
            parts.append({"pkey": f"bks__d{d}u{u}", "set": "bks", "amp": S.AMPS[(d + u) % 3], "cluster": f"d{d}",
                          "fold": d % 4, "cls": rng.choice(("clean", "crunch")), "title": None})
    for f in range(4):                                    # GOAT: 9 per fold and class
        for cls in ("clean", "crunch"):
            for j in range(9):
                parts.append({"pkey": f"goat__f{f}{cls}{j}", "set": "goat", "amp": S.AMPS[j % 3],
                              "cluster": f"item{f}{cls}{j}", "fold": f, "cls": cls, "title": None})
    for j, t in enumerate(["A"] * 3 + ["B"] * 2 + ["C"] * 2 + ["Drowning"] * 3):
        parts.append({"pkey": f"panel__{t}{j}", "set": "panel", "amp": S.AMPS[j % 3], "cluster": t, "fold": 0,
                      "cls": ("clean", "crunch")[j % 2], "title": t})
    return parts


def test_subset_draws_the_declared_47_once_by_seed():
    parts = _replay_like()
    keys = S.subset(parts)
    assert len(keys) == 47 and S.subset_shortfall(keys, parts) == []
    assert keys == S.subset(parts) and keys != S.subset(parts, seed=1)
    by = {p["pkey"]: p for p in parts}
    assert not any(by[k]["title"] == "Drowning" for k in keys)
    goat = [by[k] for k in keys if by[k]["set"] == "goat"]
    for f in range(4):
        for cls in ("clean", "crunch"):
            cell = [p for p in goat if p["fold"] == f and p["cls"] == cls]
            assert len(cell) == 3 and len({p["amp"] for p in cell}) == 3   # the amps rotate inside a cell
    bks = [by[k] for k in keys if by[k]["set"] == "bks"]
    assert all(sum(p["cluster"] == f"d{d}" for p in bks) == 2 for d in range(8))
    assert sorted(sum(p["amp"] == a for p in bks) for a in S.AMPS) == [5, 5, 6]


def _p(k, s="goat", amp="ac20", cls="clean", cluster=None, ids=None, rig=None):
    return {"pkey": k, "set": s, "amp": amp, "cls": cls, "cluster": cluster or k, "ids": ids or [["di", k]],
            "rig": rig or k}


def test_eligible_needs_amp_class_and_no_shared_cluster_identity_or_rig():
    p = _p("p")
    assert S.eligible(p, _p("q"))
    assert not S.eligible(p, _p("q", amp="pr12"))
    assert not S.eligible(p, _p("q", cls="crunch"))
    assert not S.eligible(p, _p("q", cluster="p"))
    assert not S.eligible(p, _p("q", ids=[["di", "p"]]))
    assert not S.eligible(p, _p("q", rig="p"))
    assert not S.eligible(p, p)


def test_partners_come_from_the_own_set_first_then_across():
    parts = [_p("p")] + [_p(f"g{i}") for i in range(2)] + [_p(f"b{i}", s="bks") for i in range(3)]
    pool, scope = S.partner_pool(parts[0], parts)
    assert scope == "across sets" and set(pool[:2]) == {"g0", "g1"} and set(pool[2:]) == {"b0", "b1", "b2"}
    parts += [_p("g2")]
    pool, scope = S.partner_pool(parts[0], parts)
    assert scope == "same set" and set(pool[:3]) == {"g0", "g1", "g2"}
    assert S.borrowed({"partners": pool}, set(pool)) == pool[:3]
    assert S.borrowed({"partners": pool}, set(pool) - {pool[0]}) == pool[1:4]      # a refused partner: the next
    assert S.borrowed({"partners": pool}, {pool[0], pool[1]}) is None


def test_with_partners_refuses_a_part_with_fewer_than_three():
    parts = [_p(f"g{i}") for i in range(4)] + [_p("lone", amp="pr12")]
    got, refused = S.with_partners(parts)
    assert refused == [("lone", 0)] and len(got) == 4 and all(len(p["partners"]) == 3 for p in got)


# --- the blank and the guards -----------------------------------------------------------------------------------------------

def test_the_blank_zeros_everything_outside_the_search_window():
    halves, sr = {"A": (1.0, 5.5), "B": (5.5, 10.0)}, 48000
    for h, (a, b) in halves.items():
        lo, hi = S.search_window(h, halves, sr)
        plan = S.blank_plan(480000, h, halves, sr)
        assert (lo, hi) == (int(a * sr), int(b * sr))
        assert plan == [(0, lo), (hi, 480000)]
        other = "B" if h == "A" else "A"
        olo, ohi = S.search_window(other, halves, sr)
        assert any(x <= olo and ohi <= y for x, y in plan)     # the held half lies wholly in the blank


def test_the_guards_read_the_search_value_and_the_peak_only():
    evals = [{"value": 2.0, "peak_dbfs": -20.0}, {"value": 1.0, "peak_dbfs": -70.0}, {"value": 1.5, "peak_dbfs": -30.0},
             {"value": math.inf, "peak_dbfs": -10.0}, {"value": None, "peak_dbfs": -10.0}]
    assert S.best_index(evals, -57.0) == 2                # the quiet one is under the bound
    assert S.best_index(evals, None) == 1
    assert S.usable(math.nan, -10.0, None) and S.usable(0.0, -10.0, None)
    assert S.usable(1.0, None, -57.0) and S.usable(1.0, -10.0, None) is None


def test_the_start_check():
    assert S.start_check(1.0, 1.0049)
    assert not S.start_check(1.0, 1.006)
    assert not S.start_check(math.inf, 1.0) and not S.start_check(1.0, None)


# --- the shrink, the centre, the non-finite rule, the numbers ----------------------------------------------------------------

def _specs():
    return [{"module": "m", "key": "k", "kind": "cont", "lo": 0.0, "hi": 10.0, "values": []},
            {"module": "m", "key": "sw", "kind": "switch", "values": ["false", "true"]},
            {"module": "m", "key": "mic", "kind": "cat", "values": ["1", "2", "3"]}]


def test_shrunk_moves_continuous_controls_halfway_to_cen_only():
    ans = {"m/k": "8", "m/sw": "true", "m/mic": "3", "x/y": "a"}
    cen = {"m/k": "2", "m/sw": "false", "m/mic": "1", "x/y": "b"}
    got = S.shrunk(ans, cen, _specs())
    assert float(got["m/k"]) == pytest.approx(5.0)
    assert got["m/sw"] == "true" and got["m/mic"] == "3" and got["x/y"] == "a"
    assert S.shrunk(cen, cen, _specs())["m/k"] == "2"


def test_centre_means_the_knobs_and_takes_the_most_common_switch():
    cen = {"m/k": "0", "m/sw": "false", "m/mic": "1", "x/y": "own"}
    answers = [({"m/k": "2", "m/sw": "true", "m/mic": "2", "x/y": "other"}, _specs()),
               ({"m/k": "4", "m/sw": "true", "m/mic": "3"}, _specs()),
               ({"m/k": "6", "m/sw": "false", "m/mic": "1"}, _specs())]
    got = S.centre(answers, cen)
    assert float(got["m/k"]) == pytest.approx(4.0) and got["m/sw"] == "true"
    assert got["m/mic"] == "1"                            # a three-way tie goes to Cen's
    assert got["x/y"] == "own"                            # an unsearched key is the part's own Cen's


def test_nonfinite_rule_gives_the_worst_finite_and_never_better_than_cen():
    held, rep = S.nonfinite_rule({"cen": 1.0, "answer": math.inf, "cp50": 0.8, "q": None})
    assert rep == ["answer", "q"] and held["answer"] == held["q"] == 1.0
    held, _ = S.nonfinite_rule({"cen": 1.0, "answer": None, "cp50": 1.4})
    assert held["answer"] == 1.4


def test_part_numbers():
    held = {"cen": 1.0, "answer": 0.8, "cp50": 0.9, "cp100": 0.85, "cp200": 0.8, "shrunk": 0.9, "centre": 0.95,
            "a": 1.0, "b": 0.9, "c": 1.1}
    got = S.part_numbers(held, ["a", "b", "c"])
    blind = (math.log(0.9) + math.log(1.1)) / 3
    assert got["G"] == pytest.approx(math.log(0.8)) and got["blind"] == pytest.approx(blind)
    assert got["I"] == pytest.approx(math.log(0.8) - blind)
    assert got["answer_less_centre"] == pytest.approx(math.log(0.8 / 0.95))


def test_moves():
    got = S.moves({"parameters/inputGain": "3", "drive2/drive2Active": "true"},
                  {"parameters/inputGain": "-1", "drive2/drive2Active": "false"})
    assert got["input_gain_db"] == 4.0 and got["drive2"] == {"answer": True, "cen": False}


# --- step 1's loop is C2's call ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("amp", S.AMPS)
def test_step1_replays_c2s_own_call_exactly(amp):
    from learn import full_controls as F
    from learn import knob_ceiling as K

    start = F.c1a_start({}, amp)
    dims = F.c1a_space(amp, start)
    names = [d.name for d in dims]

    def f0(x):                                             # a deterministic objective of the setting
        return 1.0 + (int(K.key(x), 16) % 10007) / 10007
    seq = []

    def rec(x):
        seq.append({nm: x.get(tuple(nm.rsplit("/", 1))) for nm in names})
        return f0(x)
    K.coord_search(dims, start, rec, S.BUDGET, F.SEED, cats="levels", canon=F.make_canon(amp))
    i = [0]

    def ev(x):
        assert {nm: x.get(tuple(nm.rsplit("/", 1))) for nm in names} == seq[i[0]]
        i[0] += 1
        return f0(x), -20.0, None
    evals, got_names, _ = S.step1_search(amp, start, ev, f0(start))
    assert got_names == names and len(evals) == len(seq) == i[0]
    i[0] = 0
    with pytest.raises(S.StartRefused):
        S.step1_search(amp, start, ev, f0(start) * 1.01)


# --- with numpy and the stored data -----------------------------------------------------------------------------------------

def _stored():
    pytest.importorskip("numpy")
    from learn import note_replay as NR

    if not NR.draw_path().exists():
        pytest.skip("no stored replay data")
    return NR, json.loads(NR.draw_path().read_text()), NR.Stored()


def test_the_loop_replays_every_stored_c2_step1_sequence_of_the_subset():
    """B3: with the clean reference, the true DI and a label start, the loop requests exactly the stored C2 record's
    step-1 settings in order and uses every stored evaluation (zero renders, `replaying`'s check)."""
    from learn import full_controls as F
    from learn import full_controls_c2 as C2
    from learn import local_objective as LO

    NR, rd, sd = _stored()
    by = {p["pkey"]: p for p in rd["parts"]}
    exact = 0
    for k in S.subset(rd["parts"]):
        p = by[k]
        o = sd.output((p["set"], p["unit"], p["amp"]))
        s1 = o["step1"]
        if o.get("block") == "c1a" or s1.get("continuation") or s1.get("start_gate") != "on":
            continue                                       # a continued record, or the gate off after a miss
        src = json.loads(open(o["source"]).read())
        start = F.c1a_start(src["best"]["settings"], p["amp"])
        assert LO.sdict(start) == s1["start_settings"]
        f = C2.replaying(s1["trials"], s1["searched_keys"], o["search"], lambda x: pytest.fail("past the record"))
        evals, names, _ = S.step1_search(p["amp"], start, lambda x: (f(x), None, None),
                                         s1["trials"][0]["judge"][o["search"]])
        assert names == s1["searched_keys"] and f.state["i"] == len(evals) == len(s1["trials"])
        # step 1's choice on the search half equals C2's constrained_index on the stored evaluations (peaks unknown)
        mine = S.best_index(evals, None)
        c2 = C2.constrained_index([{"judge": t["judge"], "replayed": True} for t in s1["trials"]], o["search"], None)
        assert mine == c2
        exact += 1
    assert exact == 40


def test_the_held_half_never_reaches_the_search():
    """With everything outside the search half zeros or noise, or the reference whole, every evaluation of a step-1 run
    on a stub renderer is the same; the held half on zeros reads inf."""
    NR, rd, sd = _stored()
    import numpy as np

    from analysis.aligned import SAMPLE_RATE

    from learn import full_controls as F
    from learn import knob_ceiling as K
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    keys = S.subset(rd["parts"])
    by = {p["pkey"]: p for p in rd["parts"]}
    picked = [next(k for k in keys if by[k]["search"] == h) for h in ("A", "B")]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    for k in picked:
        p = by[k]
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        ref = np.array(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64)
        dj = np.asarray(NR.di_section(prt), np.float64)[trim[0]:trim[1]]

        def blank(fill):
            r = ref.copy()
            for lo, hi in S.blank_plan(len(r), p["search"], K.R.HALVES, SAMPLE_RATE):
                r[lo:hi] = fill(hi - lo)
            return r
        refs = [blank(lambda n: 0.0), blank(lambda n: np.random.default_rng(1).normal(0, 0.3, n)), ref]

        def stub(x):
            return np.tanh(3 * 10 ** (float(x[("parameters", "inputGain")]) / 20) * dj) * 0.3
        start = F.c1a_start(p["menu"][0]["settings"], p["amp"])
        runs = []
        for r in refs:
            ev = (lambda rr: lambda x: (NR.half_distance(rr, stub(x), dj, p["lag"], p["search"]), -20.0, None))(r)
            runs.append(S.step1_search(p["amp"], start, ev, ev(start)[0], budget=20)[0])
        for a, b, c in zip(*runs):
            assert a["value"] == b["value"] == c["value"] and a["t"] == b["t"] == c["t"]
        assert NR.half_distance(refs[0], stub(start), dj, p["lag"], p["held"]) == math.inf


# --- the whole loop on a stub renderer (numpy, no data) -----------------------------------------------------------------------

class _Stub:
    """A renderer whose output is a function of the setting; `offset` per process (from the `made`-th renderer on)
    makes step 2's first evaluation miss step 1's best."""
    made = 0
    miss_from = None

    def __init__(self):
        import numpy as np
        self.np = np
        _Stub.made += 1
        self.off = 0.5 if _Stub.miss_from is not None and _Stub.made >= _Stub.miss_from else 0.0

    def render(self, di, sel, x):
        import hashlib as H
        aud = sorted(("/".join(k), v) for k, v in x.items()      # what sounds to the stub: the searched families
                     if k[0] in ("ac20Amp", "ac20EQ", "drive1", "drive2", "compressor") or k[1].endswith("MicType")
                     or k == ("parameters", "inputGain"))
        h = int(H.sha1(json.dumps(aud).encode()).hexdigest()[:6], 16)
        return self.np.full(len(di), 0.1 + 0.2 * h / 0xffffff + self.off)

    def close(self):
        pass


def _stub_cen(amp):
    """A complete enough preset for the stub: C1a's start from nothing, with the keys C1b's start would otherwise
    change audibly (a real Cen stores them)."""
    from learn import full_controls as F
    from learn import full_controls_c1b as C
    from learn import local_objective as LO

    cen = LO.sdict(F.c1a_start({}, amp))
    x0 = LO.sdict(C.plugin(C.c1b_start(cen, amp), amp))
    return {**cen, **{k: x0[k] for k in C.audible_change(C.c1b_start(cen, amp), cen, amp)}}


def _run(monkeypatch, miss_from=None, silent_final=False, budget=30):
    np = pytest.importorskip("numpy")
    from learn import audibility_measure as AM
    from learn import full_controls as F
    from learn import local_objective as LO
    from learn import note_replay as NR

    monkeypatch.setattr(NR, "half_distance", lambda ref, y, di, lag, half: 1.0 + float(np.mean(np.abs(y))))
    if silent_final:
        monkeypatch.setattr(AM, "fresh_render", lambda make, di, sel, xp, x: np.zeros(len(di)))
    _Stub.made, _Stub.miss_from = 0, miss_from
    amp = "ac20"
    cen = _stub_cen(amp)
    x32 = np.ones(48000 * 12, np.float32)
    y0 = _Stub().render(x32, "0", LO.tdict(LO.sdict(F.c1a_start(cen, amp))))
    _Stub.made = 0
    p = {"pkey": "stub", "amp": amp, "search": "A", "lag": 0, "cen": {"select": "0", "settings": cen},
         "start_ref": {"true": {"xlnoG": 1.0 + float(np.mean(np.abs(y0)))}}}
    lists = {amp: {"leftMicType": ["1", "2"], "rightMicType": ["3", "4"]}}
    return S.run_part(p, "true", "xlnoG", x32, np.zeros(len(x32)), _Stub, lists, log=lambda *a: None, budget=budget)


def test_run_part_end_to_end(monkeypatch):
    rec = _run(monkeypatch)
    assert "refused" not in rec and rec["step2"]["start_kind"] == "canonical" and rec["fallback"] is None
    assert rec["step1"]["evaluations"] <= 30 and set(rec["step1"]["checkpoints"]) <= {"50", "100", "200"}
    assert rec["renders"] <= 1 + 30 + 2 + 1 + 64 + 2


def test_run_part_step2_misses_twice_and_step1_stands(monkeypatch):
    rec = _run(monkeypatch, miss_from=2)                 # every process after step 1's renders differently
    assert rec["step2"]["start_kind"] == "refused" and set(rec["step2"]["first_start_miss"]) == {"canonical",
                                                                                                  "raw_after_miss"}
    assert rec["fallback"] is None and rec["answer"]["select"] == "0"
    assert [d["module"] + "/" + d["key"] for d in rec["searched_dims"]] == rec["step1"]["searched_keys"]   # step 1's


def test_run_part_final_unusable_falls_back_to_step1(monkeypatch):
    rec = _run(monkeypatch, silent_final=True)
    assert rec["final_fresh"]["unusable"] and rec["fallback"] == "step1"


def test_run_part_final_and_step2_unusable_fall_back_to_the_start(monkeypatch):
    from learn import local_objective as LO

    rec = _run(monkeypatch, miss_from=2, silent_final=True)
    assert rec["fallback"] == "start" and rec["searched_dims"] == []
    assert rec["answer"]["settings"] == rec["start_settings"] == LO.sdict(LO.tdict(rec["start_settings"]))


def test_run_part_refuses_a_start_off_the_replays_position_0(monkeypatch):
    np = pytest.importorskip("numpy")
    from learn import full_controls as F
    from learn import local_objective as LO
    from learn import note_replay as NR

    monkeypatch.setattr(NR, "half_distance", lambda ref, y, di, lag, half: 1.0 + float(np.mean(np.abs(y))))
    cen = _stub_cen("ac20")
    p = {"pkey": "stub", "amp": "ac20", "search": "A", "lag": 0, "cen": {"select": "0", "settings": cen},
         "start_ref": {"true": {"xlnoG": 9.0}}}
    rec = S.run_part(p, "true", "xlnoG", np.ones(48000 * 12, np.float32), np.zeros(48000 * 12), _Stub,
                     {"ac20": {"leftMicType": ["1"], "rightMicType": ["3"]}}, log=lambda *a: None, budget=10)
    assert "start" in rec["refused"]
