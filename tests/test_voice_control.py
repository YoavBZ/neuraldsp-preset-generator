"""The unclaimed-groups control of the sound-gap test (`learn/voice_control.py`, `docs/scratch-voice-plan.md`): the
names and keys, XC_TABLE (every interval case ends in exactly one code, malformed ones included, first match in order;
coverage-sensitive and its force), the term arithmetic on one passing set of four guitars (Ux = Ubx - Urx), the drop
helpers, the spend gate under each code, the floors on the control's own world behind fakes (its own 8 repeat renders,
writes only under `PF/fs/voice/control/` while the main test's `repeat/` records exist, carries naming their source,
a repeat mismatch stops, no render before the guards), the read behind fakes, and the builder on a synthetic bank
(numpy behind `importorskip`): no flags gives byte-identical guitars, with flags the bytes outside the dropped spans
are unchanged and the kept grouping holds, a failing proof writes nothing. Synthetic keys only."""
import ast
import hashlib
import itertools
import json
import math
import pathlib
import random
import subprocess
import sys

import pytest

from learn import note_rebuild as NR
from learn import scratch_search as S
from learn import scratch_voice as V
from learn import voice_build as VB
from learn import voice_control as VC
from learn import voice_floors as VF

REPO = pathlib.Path(__file__).resolve().parents[1]
SR = NR.SR


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


BETTER, MATCHES, WORSE, UNDECIDED = _iv(-0.3, -0.5, -0.1), _iv(0.0, -0.05, 0.05), _iv(0.3, 0.1, 0.5), \
    _iv(0.08, -0.05, 0.2)
READ = {"better": BETTER, "matches": MATCHES, "worse": WORSE, "undecided": UNDECIDED}
BAD = (None, {}, _iv(0.1, 0.2, 0.05), _iv(math.nan, -0.1, 0.1), _iv(0.0, -math.inf, 0.1),
       {"mean": 0.1, "lo90": None, "hi90": 0.2}, "x")
OK = {c: True for c in VC.CHECKS}


def _h(*a):
    return hashlib.sha256("|".join(a).encode()).hexdigest()


def _args(**kw):
    return type("A", (), dict({"rerun": False}, **kw))()


# --- names, keys, imports ----------------------------------------------------------------------------------------------

def test_names_keys_and_counts():
    assert VC.PHASE == V.PHASE_CONTROL == "phase_scratch_voice_control"
    assert VC.PHASE_DRY == "phase_scratch_voice_control_dry" and VC.PHASE_DRY not in V.KEYS_TO_COME
    assert VC.PHASE_OUTCOME == V.PHASE_CONTROL_OUTCOME and VC.PHASE_WAIVER == V.PHASE_WAIVER
    assert VC.BUILT == ("tr-uc", "vc-uc") and VC.STORED == ("tr-di", "vc-own") and VC.PARENT == {
        "tr-uc": "tr-di", "vc-uc": "vc-own"}
    assert VC.FOUR == ("tr-di", "vc-own", "tr-uc", "vc-uc")
    assert VC.TERMS == (("S", "tr-di", "vc-own"), ("Sx", "tr-uc", "vc-uc"), ("Ubx", "tr-di", "tr-uc"),
                        ("Urx", "vc-own", "vc-uc"))
    assert VC.TERM_NAMES == ("S", "Sx", "Ux", "Ubx", "Urx") and VC.READ_TERMS == ("Sx", "Ux", "Ubx", "Urx")
    assert VC.RENDERS == {"ceiling_no_carry": 188, "repeat": 8, "ceiling_with_repeat": 196, "carried_parts_seen": 12,
                          "expected": 148}
    assert VC.RENDERS["ceiling_no_carry"] == V.CONTROL_RENDERS                  # note 3: 148 against the pinned 188
    assert VC.ID_TOL == 1e-12 and VC.SEEN_S == (0.501, 0.399, 0.603) and VC.TIMING_S == 0.05
    assert VC.MODULE in V.UNIT_FILES and VC.MODULE in V.CODE_FILES and VC.PLAN == V.PLAN
    assert VC.PROOFS == ("flags_are_builds", "rule_off_is_stored", "trace_holds", "outside_dropped_same",
                         "gate_outside_same", "synth_inside_gate", "drop_is_additive")
    VC.table_guard()


def test_the_paths_sit_under_the_control_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "voice_dir", lambda: tmp_path)
    for f, folder in ((VC.floor_path, "floors"), (VC.first_path, "floors-first"), (VC.repeat_path, "repeat"),
                      (VC.part_path, "build-parts")):
        p = f("bks/k/1")
        assert p.parent.name == folder and p.parent.parent == tmp_path / "control" and "bks__k__1" in p.name
        assert p != {"floors": V.floor_path, "repeat": V.repeat_path}.get(folder, lambda k: None)("bks/k/1")
    assert VC.dry_path("tr-uc", "a/b").parent == tmp_path / "control" / "dry" / "tr-uc"
    with pytest.raises(ValueError):
        VC.dry_path("vc-own", "a/b")
    assert VC.build_path() == tmp_path / "control" / "build.json" != V.build_path()


def test_the_module_imports_only_the_standard_library_and_learn_at_module_level():
    tree = ast.parse((REPO / "learn" / "voice_control.py").read_text())
    mods = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module.split(".")[0])
    assert mods <= {"__future__", "argparse", "json", "math", "pathlib", "time", "learn"}


def test_no_numpy_at_import():
    code = "import sys; import learn.voice_control; print('numpy' in sys.modules, 'scipy' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["False", "False"]


def test_it_redefines_none_of_voice_builds_functions():
    tree = ast.parse((REPO / "learn" / "voice_control.py").read_text())
    mine = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    theirs = {n.name for n in ast.parse((REPO / "learn" / "voice_build.py").read_text()).body
              if isinstance(n, ast.FunctionDef)}
    gate_chain = {"own_windows", "window_gain", "own_gain", "edge_gain", "end_ramp", "chain", "through_gate",
                  "padded_raw", "real_end", "span_mask", "support_check", "group_onsets", "same_bytes"}
    assert gate_chain <= theirs and not mine & gate_chain


def test_the_table_guard_refuses_a_changed_table(monkeypatch):
    monkeypatch.setattr(VC, "XC_CODES", VC.XC_CODES[:-1])
    with pytest.raises(SystemExit, match="five declared"):
        VC.table_guard()
    monkeypatch.undo()
    monkeypatch.setattr(V, "CONTROL_CODES", ("XC-stands",))
    with pytest.raises(SystemExit, match="spend gate"):
        VC.table_guard()


def test_the_cli_knows_build_floor_and_read():
    assert sorted(VC.COMMANDS) == ["build", "floor", "read"]
    with pytest.raises(SystemExit):
        VC.main(["floor"])                                     # --shard is required
    with pytest.raises(SystemExit):
        VC.main(["floor", "--shard", "0/4"])
    with pytest.raises(SystemExit):
        VC.main(["build", "--shard", "0/9"])


# --- the outcome table (pure) -----------------------------------------------------------------------------------------

def _oracle(ivs, checks):
    """XC_TABLE written out independently, the first that holds."""
    rd = {t: (V.reading(ivs.get(t)) or {}).get("reading") for t in VC.READ_TERMS}
    if (any(checks.get(c) is not True for c in VC.CHECKS) or any(rd[t] is None for t in VC.READ_TERMS)
            or rd["Urx"] == "worse"):
        return "XC-anomaly"
    if rd["Ux"] in ("matches", "better"):
        return "XC-stands"
    if rd["Ux"] == "worse":
        return "XC-part" if rd["Sx"] == "worse" else "XC-notes"
    return "XC-undecided"


def test_every_interval_case_ends_in_exactly_one_code():
    cases = list(READ.values()) + list(BAD)
    seen = set()
    for combo in itertools.product(cases, repeat=len(VC.READ_TERMS)):
        ivs = dict(zip(VC.READ_TERMS, combo))
        got = VC.xc_code(ivs, OK)
        assert got["code"] in VC.XC_CODES and got["code"] == _oracle(ivs, OK)
        assert sum(got["code"] == c for c in VC.XC_CODES) == 1
        seen.add(got["code"])
    assert seen == set(VC.XC_CODES)


def test_each_code_as_declared():
    base = {"Sx": WORSE, "Ux": MATCHES, "Ubx": MATCHES, "Urx": MATCHES}
    assert VC.xc_code(base, OK)["code"] == "XC-stands"
    assert VC.xc_code(dict(base, Ux=BETTER), OK)["code"] == "XC-stands"
    assert VC.xc_code(dict(base, Ux=WORSE), OK)["code"] == "XC-part"
    for s in (MATCHES, BETTER, UNDECIDED):
        assert VC.xc_code(dict(base, Ux=WORSE, Sx=s), OK)["code"] == "XC-notes"
    assert VC.xc_code(dict(base, Ux=UNDECIDED), OK)["code"] == "XC-undecided"
    a = VC.xc_code(dict(base, Urx=WORSE), OK)                       # amendment 5
    assert a["code"] == "XC-anomaly" and "Urx reads worse" in a["anomaly"]
    assert VC.xc_code(dict(base, Urx=BETTER), OK)["code"] == "XC-stands"   # the drop removed real playing: allowed
    for c in VC.CHECKS:
        got = VC.xc_code(base, dict(OK, **{c: False}))
        assert got["code"] == "XC-anomaly" and c in got["anomaly"]
    assert VC.xc_code(base, {})["code"] == "XC-anomaly"
    assert VC.xc_code({}, OK)["code"] == "XC-anomaly"
    part = VC.xc_code(dict(base, Ux=WORSE), OK)
    assert "Sx as the lower figure and S as the upper" in part["next"]          # amendment 4
    assert "upper bound" in VC.xc_code(base, OK)["next"]                         # note 6
    assert VC.PHASE_WAIVER in VC.xc_code(dict(base, Ux=WORSE, Sx=MATCHES), OK)["next"]


def test_coverage_sensitive_is_set_when_the_clean_subset_differs_and_forces_under_part_and_notes():
    base = {"Sx": WORSE, "Ux": WORSE, "Ubx": WORSE, "Urx": MATCHES}
    same = VC.xc_read(base, OK, base)
    assert same["code"] == "XC-part" and same["coverage_label"] is None and same["gate"] == "open"
    assert not same["forced"]
    part = VC.xc_read(base, OK, dict(base, Ux=MATCHES))
    assert part["code"] == "XC-part" and part["with_clean_subset"] == "XC-stands"
    assert part["coverage_label"] == "coverage-sensitive" and part["forced"] and part["gate"] == "waiver"
    assert part["next"].startswith(VC.FORCED_NEXT)
    notes = VC.xc_read(dict(base, Sx=MATCHES), OK, dict(base, Ux=UNDECIDED))
    assert notes["code"] == "XC-notes" and notes["forced"] and notes["gate"] == "waiver"
    stands = VC.xc_read(dict(base, Ux=MATCHES), OK, base)          # labelled, but no force outside part and notes
    assert stands["coverage_label"] == "coverage-sensitive" and not stands["forced"] and stands["gate"] == "open"
    empty = VC.xc_read(base, OK, {t: None for t in VC.READ_TERMS})
    assert empty["with_clean_subset"] == "XC-anomaly" and empty["coverage_label"] == "coverage-sensitive"
    anom = VC.xc_read(dict(base, Urx=WORSE), OK, base)
    assert anom["code"] == "XC-anomaly" and anom["gate"] == "shut"


# --- the spend gate ---------------------------------------------------------------------------------------------------

def _waiver(code, kinds=tuple(V.SPEND_KINDS), date="2026-11-29", **kw):
    return {V.PHASE_WAIVER: dict({"user_words": "go", "date": date, "answers_code": code, "spend_kinds": list(kinds)},
                                 **kw)}


def test_the_gate_opens_only_on_a_declared_code_and_stays_shut_under_anomaly():
    for xv in V.SPEND_CODES:
        m = {V.PHASE_OUTCOME: {"code": xv}}
        for kind in V.SPEND_KINDS:
            def gate(ctl, extra=None):
                return V.spend_refusal(dict(m, **{V.PHASE_CONTROL_OUTCOME: dict(ctl, date="2026-11-28")},
                                            **(extra or {})), kind)
            for c in ("XC-stands", "XC-undecided", "XC-part"):
                assert gate({"code": c, "coverage_label": None}) is None and VC.gate_state(c) == "open"
            for c in ("XC-stands", "XC-undecided"):                  # the key is required only on forced codes
                assert gate({"code": c}) is None
            for c in VC.COVERAGE_FORCED:                              # #658's review, binding fix 1: never fail open
                assert "no coverage_label" in gate({"code": c})
                assert "no coverage_label" in gate({"code": c}, _waiver(c))
                assert "no coverage_label" in gate({"code": c, "coverage_label": "x"}, _waiver(c))
            assert "stays shut" in gate({"code": "XC-anomaly"})
            assert "stays shut" in gate({"code": "XC-anomaly"}, _waiver("XC-anomaly"))
            assert VC.gate_state("XC-anomaly") == "shut"
            notes = {"code": "XC-notes", "coverage_label": None}
            assert V.PHASE_WAIVER in gate(notes) and gate(notes, _waiver("XC-notes")) is None
            cs = {"code": "XC-part", "coverage_label": "coverage-sensitive"}
            assert "coverage-sensitive" in gate(cs) and gate(cs, _waiver("XC-part")) is None
            assert gate({"code": "XC-stands", "coverage_label": "coverage-sensitive"}) is None
            assert "not a declared" in gate({"code": "XV-both"}) and "not a declared" in gate({"code": "x"},
                                                                                               _waiver("x"))
            assert VC.gate_state("x") == "shut"


def test_the_waiver_is_scoped_to_its_code_date_and_spend_kinds():
    for xv in V.SPEND_CODES:
        m = {V.PHASE_OUTCOME: {"code": xv}}
        for c, lab in (("XC-notes", None), ("XC-part", "coverage-sensitive")):
            ctl = {V.PHASE_CONTROL_OUTCOME: {"code": c, "coverage_label": lab, "date": "2026-11-28"}}
            for kind in V.SPEND_KINDS:
                def gate(w):
                    return V.spend_refusal(dict(m, **ctl, **w), kind)
                assert gate(_waiver(c)) is None
                assert gate(_waiver(c, date="2026-11-28")) is None               # the same day counts
                assert "predates" in gate(_waiver(c, date="2026-11-27"))
                assert "YYYY-MM-DD" in gate(_waiver(c, date="28 Nov 2026"))
                assert "YYYY-MM-DD" in gate(_waiver(c, date=None))
                other = "XC-part" if c == "XC-notes" else "XC-notes"
                assert "answers" in gate(_waiver(other))                         # it answers another code
                assert "answers" in gate(_waiver(None))
                rest = [k for k in V.SPEND_KINDS if k != kind]
                assert "does not cover" in gate(_waiver(c, kinds=rest))          # scoped to its spend kinds
                assert gate(_waiver(c, kinds=[kind])) is None
                assert "spend_kinds" in gate(_waiver(c, kinds=[]))
                assert "spend_kinds" in gate(_waiver(c, kinds=[kind, "training"]))
                assert "spend_kinds" in gate(_waiver(c, spend_kinds=kind))       # a string, not a list
                assert "user's words" in gate(_waiver(c, user_words=""))
                assert gate({V.PHASE_WAIVER: {"user_words": "go", "date": "2026-11-29"}})   # the old unscoped form
            nodate = {V.PHASE_CONTROL_OUTCOME: {"code": c, "coverage_label": lab}}
            assert "YYYY-MM-DD" in V.spend_refusal(dict(m, **nodate, **_waiver(c)), "search-row")
    assert V.WAIVER_FIELDS == ("user_words", "date", "answers_code", "spend_kinds")
    assert V.CONTROL_OUTCOME_FIELDS == ("code", "coverage_label", "date")
    assert V.iso_date("2026-11-28") == "2026-11-28" and V.iso_date("2026-13-01") is None and V.iso_date(20261128) is None


# --- the term arithmetic (pure) ---------------------------------------------------------------------------------------

def test_ux_is_ubx_less_urx_to_1e_12_and_s_less_sx():
    rng = random.Random(28)
    for _ in range(500):
        d = {g: math.exp(rng.uniform(-1, 3)) for g in VC.FOUR}
        t = VC.part_terms(d)
        assert abs(t["Ux"] - (t["Ubx"] - t["Urx"])) <= 1e-12
        assert t["Ux"] == t["S"] - t["Sx"] and t["S"] == math.log(d["tr-di"] / d["vc-own"])
        assert VC.identity_gap(t) <= VC.ID_TOL


def test_one_passing_set_over_the_four_guitars():
    good = {g: 1.0 + i for i, g in enumerate(VC.FOUR)}
    floors = {"a": good, "b": dict(good, **{"vc-uc": None}), "c": dict(good, **{"tr-di": math.inf}),
              "d": dict(good, **{"tr-uc": 0.0})}
    vals, refused, gaps = VC.term_values(floors)
    assert sorted(refused) == ["b", "c", "d"] and "vc-uc" in refused["b"] and "tr-di" in refused["c"]
    for t in VC.TERM_NAMES:
        assert sorted(vals[t]) == ["a"]                                  # a refused part drops from every term
    assert VC.identity_holds(gaps) and not VC.identity_holds({}) and not VC.identity_holds({"a": 1e-9})
    assert not VC.identity_holds({"a": None})


def test_zero_where_carried():
    d = {"tr-di": 2.0, "vc-own": 1.5, "tr-uc": 2.0, "vc-uc": 1.5}       # carried: the parents' floors exactly
    vals, _, _ = VC.term_values({"k": d, "m": dict(d, **{"tr-uc": 2.1})})
    assert vals["Ux"]["k"] == vals["Ubx"]["k"] == vals["Urx"]["k"] == 0.0
    assert VC.zero_where_carried(vals, ["k"]) and not VC.zero_where_carried(vals, ["k", "m"])


def test_s_reproduces_from_the_stored_files():
    iv = _iv(0.5012, 0.3991, 0.6029)
    s = {"aaa": 0.4, "bbb": 0.6}
    assert VC.s_reproduces(s, dict(s), iv, dict(iv))["holds"]
    assert not VC.s_reproduces(s, dict(s, aaa=0.41), iv, dict(iv))["holds"]
    assert not VC.s_reproduces(s, {"aaa": 0.4}, iv, dict(iv))["holds"]
    assert not VC.s_reproduces(s, dict(s), iv, dict(iv, mean=0.5013))["holds"]
    off = _iv(0.52, 0.41, 0.62)
    r = VC.s_reproduces(s, dict(s), off, dict(off))
    assert r["per_part"] and r["stored"] and not r["seen"] and not r["holds"]
    assert not VC.s_reproduces(s, None, iv, iv)["holds"]


# --- the drop (pure) --------------------------------------------------------------------------------------------------

def test_the_drop_helpers():
    notes = [{"on": 0.5}, {"on": 1.0}, {"on": 1.02}, {"on": 2.0}]
    groups = NR.onset_groups(notes)
    assert groups == [[0], [1, 2], [3]]
    gidx = VC.dropped_groups([False, True, False])
    assert gidx == [1] and VC.dropped_notes(groups, gidx) == [1, 2] and VC.dropped_notes(groups, []) == []
    lv = VC.drop_levels([1.5, -2.0, 0.25], gidx)
    assert lv[0] == 1.5 and lv[1] == -math.inf and lv[2] == 0.25 and 10 ** (lv[1] / 20) == 0.0
    assert VC.only_levels([1.5, -2.0, 0.25], gidx) == [-math.inf, -2.0, -math.inf]
    with pytest.raises(ValueError):
        VC.drop_levels([0.0], [3])
    trace = [{"played": True, "end": 0.9, "end_kind": "repluck", "string": 1}, {"played": True, "end": 1.5,
             "end_kind": "release", "string": 2}, {"played": False, "why": "no free string"},
             {"played": True, "end": 2.4, "end_kind": "release", "string": 1}]
    mk = VC.marked_trace(trace, [1, 2])
    assert mk[0] is trace[0] and mk[3] is trace[3] and mk[2] is trace[2]            # skipped stays as it is
    assert mk[1]["played"] is False and mk[1]["dropped"] and mk[1]["end"] == 1.5
    assert VC.played_count(trace) == 3 and VC.played_count(mk) == 2
    only = VC.only_trace(trace, [1, 2])
    assert [t["played"] for t in only] == [False, True, False, False]
    # a record holds group indices, never -inf
    json.dumps({"groups": gidx, "notes": VC.dropped_notes(groups, gidx)}, allow_nan=False)


def test_kept_notes_cut_by_a_dropped_pluck():
    notes = [{"on": 0.5}, {"on": 1.0}, {"on": 1.5}, {"on": 2.0}]
    trace = [{"played": True, "string": 1, "end_kind": "repluck"}, {"played": True, "string": 1, "end_kind": "repluck"},
             {"played": True, "string": 2, "end_kind": "release"}, {"played": True, "string": 1, "end_kind": "mute"}]
    assert VC.cut_by_dropped(notes, trace, [1]) == 1              # note 0 ends at note 1's pluck
    assert VC.cut_by_dropped(notes, trace, [3]) == 1              # note 1 ends at dropped note 3's pluck
    trace[1]["end_kind"] = "mute"                                 # ... unless it ends some other way first
    assert VC.cut_by_dropped(notes, trace, [3]) == 0
    assert VC.cut_by_dropped(notes, trace, [2]) == 0              # another string's note cuts nothing
    assert VC.cut_by_dropped(notes, trace, []) == 0 and VC.cut_by_dropped(notes, trace, [0, 1]) == 0


def test_coverage_clean_is_an_exactly_unchanged_weight():
    assert VC.coverage_clean({"uncovered_weight": 0.25}, {"uncovered_weight": 0.25})
    assert not VC.coverage_clean({"uncovered_weight": 0.25}, {"uncovered_weight": 0.2500001})
    assert not VC.coverage_clean({}, {})


def test_the_coverage_membership_and_build_body():
    keys = ["bks/a", "bks/b", "goat/c", "panel/d"]

    def rec(k, clean, carried, groups):
        return {"set": k.split("/")[0], "coverage_clean": clean, "carried": carried, "code": {"x": 1},
                "proofs": {p: True for p in VC.PROOFS}, "checks": {c: True for c in VC.BUILD_CHECKS},
                "dropped": {"groups_n": groups, "groups_all": 5, "notes_n": groups, "played_notes_n": groups},
                "cut_by_dropped": 0, "timing": {"rise_within_50ms": 0},
                **{f: None for f in VC.PART_FIELDS if f not in ("set", "coverage_clean", "carried", "code", "proofs",
                                                                 "checks", "dropped", "cut_by_dropped", "timing")}}
    per = {"bks/a": rec("bks/a", True, True, 0), "bks/b": rec("bks/b", False, False, 2),
           "goat/c": rec("goat/c", True, False, 1), "panel/d": rec("panel/d", True, True, 0)}
    cov = VC.coverage_sets(per, keys)
    assert cov["clean"] == ["bks/a", "goat/c", "panel/d"] and cov["clean_deciding_n"] == 2
    assert cov["clean_deciding_carried_n"] == 1 and cov["clean_deciding_with_drops_n"] == 1
    assert cov["moved_deciding_n"] == 1 and cov["deciding_n"] == 3
    body = VC.combine_body(per, keys, "v" * 64)
    assert body["proofs_hold"] is False                           # four parts, not the 47
    assert body["dropped"]["the_40"]["groups"] == 3 and body["dropped"]["all_47"]["carried"] == 2
    dry = VC.dry_body(dict(body, scratch_readerr_blob_sha="a", played_trace_sha256="b"), "s" * 64)
    text = json.dumps(dry)
    assert all(k not in text for k in keys) and "clean" not in dry["coverage"]
    per["goat/c"] = dict(per["goat/c"], code={"x": 2})
    with pytest.raises(SystemExit, match="different scratch_readerr"):
        VC.combine_body(per, keys, "v" * 64)


# --- the floors on the control's own world (fakes, no numpy) ----------------------------------------------------------

def _parts(n=6):
    sets = ["bks", "goat", "panel"]
    return [{"pkey": f"{sets[i % 3]}/part-{i:02d}|u{i}", "set": sets[i % 3], "lag": 0, "held": "A"}
            for i in range(n)]


class Fake(VC.ControlRuns):
    """The control's guitars and paths (VC.ControlRuns, as ControlWorld carries them) on made-up renders: `carry`
    {pkey} makes both guitars byte-identical to their parents; `refuse` {(pkey, guitar): times}."""

    def __init__(self, parts, carry=(), refuse=None, stored_off=None):
        self.parts, self.check_keys = parts, V.check_parts(parts)
        self.stored = {p["pkey"]: {"tr-di": {"held": 2.0, "audio_sha256": _h("b", p["pkey"])},
                                   "vc-own": {"held": 1.5, "audio_sha256": _h("o", p["pkey"])}} for p in parts}
        self.shas = {"build": "B" * 64, "floors": "F" * 64, "answers": "A" * 64, "voice_rows": "R" * 64}
        self.carry, self.refuse, self.stored_off = set(carry), dict(refuse or {}), dict(stored_off or {})
        self.calls, self.logs, self.caps, self.t = [], [], 0, 0.0

    def render(self, pk, g):
        self.calls.append((pk, g))
        if self.refuse.get((pk, g), 0) > 0:
            self.refuse[(pk, g)] -= 1
            return math.inf, _h("silent", g), True
        if g in VC.STORED:
            h, sha = self.stored_off.get((pk, g), (self.stored[pk][g]["held"], self.stored[pk][g]["audio_sha256"]))
            return h, sha, True
        return {"tr-uc": 2.2, "vc-uc": 1.4}[g], _h("r", g, pk), True

    def dry_shas(self, pk):
        out = {g: _h("d", g, pk) for g in VC.FOUR}
        if pk in self.carry:
            out.update({"tr-uc": out["tr-di"], "vc-uc": out["vc-own"]})
        return out

    def free_gb(self):
        return 100.0

    def wait_cap(self):
        self.caps += 1

    def clock(self):
        return self.t

    def sleep(self, s):
        self.t += s

    def now(self):
        return "2026-11-28 00:00:00"

    def log(self, msg):
        self.logs.append(msg)


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "voice_dir", lambda: tmp_path)
    return tmp_path


def _old_records(parts):
    """The main test's records as they sit on disk: repeat/ (held) and floors/."""
    olds = []
    for k in V.check_parts(parts):
        VF.write_once(V.repeat_path(k), {"holds": True, "tag": V.tag(k)}, V.tag(k))
        olds.append(V.repeat_path(k))
    for p in parts:
        VF.write_once(V.floor_path(p["pkey"]), {"guitars": {}}, V.tag(p["pkey"]))
        olds.append(V.floor_path(p["pkey"]))
    return {q: q.read_bytes() for q in olds}


def _shard_all(w, rerun=False):
    return sum(VF.run_floor(_args(shard=(k, 3), rerun=rerun), w) for k in range(3))


def test_the_control_does_its_own_repeat_and_writes_only_under_control(world):
    parts = _parts(6)
    old = _old_records(parts)
    carry = {parts[1]["pkey"], parts[5]["pkey"]}
    w = Fake(parts, carry=carry)
    total = _shard_all(w)
    ck = V.check_parts(parts)
    rep_calls = w.calls[:4]
    assert rep_calls == [(k, g) for k in ck for g in VC.STORED]             # its own repeat, 8 renders
    assert total == 8 + (len(parts) - len(carry)) * 2 * 2
    assert {q: q.read_bytes() for q in old} == old                          # the main test's records untouched
    new = [q for q in world.rglob("*.json") if q not in old]
    assert new and all(q.relative_to(world).parts[0] == "control" for q in new)
    for k in ck:
        r = json.loads(VC.repeat_path(k).read_text())
        assert r["holds"] is True and r["renders"] == 4 and sorted(r["guitars"]) == sorted(VC.STORED)
        assert r["plan"] == VC.PLAN
    for p in parts:
        r = json.loads(VC.floor_path(p["pkey"]).read_text())
        assert sorted(r["guitars"]) == sorted(VC.BUILT) and "voice_rows_sha256" in r
        if p["pkey"] in carry:                                              # carries name their source
            assert r["guitars"]["tr-uc"]["carried_from"] == "tr-di" and r["guitars"]["vc-uc"]["carried_from"] == "vc-own"
            assert r["guitars"]["tr-uc"]["held"] == 2.0 and r["guitars"]["vc-uc"]["held"] == 1.5 and r["renders"] == 0
        else:
            assert all(x["carried_from"] is None for x in r["guitars"].values()) and r["renders"] == 4
    assert any("VOICE CONTROL FLOORS" in m for m in w.logs)
    text = "\n".join(q.read_text() for q in new) + "\n".join(w.logs)
    assert all(p["pkey"] not in text and "part-" not in text for p in parts)


def test_a_control_repeat_mismatch_stops_everything(world):
    parts = _parts(6)
    _old_records(parts)                                       # the main test's held records do not stand in
    k0 = V.check_parts(parts)[0]
    w = Fake(parts, stored_off={(k0, "vc-own"): (1.5000001, _h("o", k0))})
    with pytest.raises(SystemExit, match="REPEAT MISMATCH"):
        VF.run_floor(_args(shard=(0, 3)), w)
    assert w.calls == [(k0, "tr-di"), (k0, "vc-own")]
    assert not (world / "control" / "floors").exists()
    w2 = Fake(parts)
    with pytest.raises(SystemExit, match="REPEAT MISMATCH"):
        VF.run_floor(_args(shard=(1, 3)), w2)
    assert w2.calls == [] and w2.caps == 0


def test_the_other_shards_wait_for_the_controls_own_repeat(world):
    parts = _parts(6)
    _old_records(parts)
    w = Fake(parts)
    with pytest.raises(SystemExit, match="did not finish"):
        VF.run_floor(_args(shard=(1, 3)), w)
    assert w.calls == [] and w.caps == 0


def test_the_control_rerun_reruns_only_the_refused(world):
    parts = _parts(6)
    k = parts[4]["pkey"]
    w = Fake(parts, refuse={(k, "vc-uc"): 1})
    _shard_all(w)
    assert not VC.floor_path(k).exists() and VC.first_path(k).exists()
    w.calls.clear()
    _shard_all(w, rerun=True)
    assert w.calls == [(k, "vc-uc")]
    r = json.loads(VC.floor_path(k).read_text())
    assert r["guitars"]["vc-uc"]["reran"] is True and r["guitars"]["vc-uc"]["refused"] is None
    recs = {p["pkey"]: json.loads(VC.floor_path(p["pkey"]).read_text()) for p in parts}
    assert V.pending_reruns(recs) == []


def test_the_world_defaults_are_the_main_tests():
    plain = object()
    assert VF.w_order(plain) == VF.ORDER and VF.w_stored(plain) == VF.STORED == VF.w_repeat(plain)
    assert VF.w_floor_path(plain, "a/b") == V.floor_path("a/b") and VF.w_repeat_path(plain, "a/b") == V.repeat_path(
        "a/b") and VF.w_first_path(plain, "a/b") == VF.first_path("a/b")
    assert VF.w_sha_fields(plain) == VF.SHA_FIELDS and VF.w_plan(plain) == VF.PLAN
    f = Fake(_parts(3))
    assert VF.w_order(f) == VC.BUILT and VF.w_stored(f) == VF.w_repeat(f) == VC.STORED
    assert VF.w_floor_path(f, "a/b") == VC.floor_path("a/b") and VF.w_repeat_path(f, "a/b") == VC.repeat_path("a/b")


def test_no_render_before_the_guards(monkeypatch, world):
    calls = []
    monkeypatch.setattr(VC.ControlWorld, "render", lambda self, pk, g: calls.append((pk, g)))
    with pytest.raises(SystemExit, match="one render process a shard"):
        VC.cmd_floor(_args(shard=(0, 2)))
    monkeypatch.setattr(V, "require_voice", lambda *a: (_ for _ in ()).throw(SystemExit("differ from main's")))
    with pytest.raises(SystemExit, match="differ from main's"):
        VC.cmd_floor(_args(shard=(0, 3)))
    asked = []
    monkeypatch.setattr(V, "require_voice", lambda *a: asked.append(a) or {V.PHASE_OUTCOME: {"code": "XV-notes"}})
    with pytest.raises(SystemExit, match="runs only under"):
        VC.cmd_floor(_args(shard=(0, 3)))
    assert asked[0] == (V.PHASE_DRY, V.PHASE_OUTCOME, VC.PHASE, VC.PHASE_DRY)
    monkeypatch.setattr(V, "require_voice", lambda *a: {V.PHASE_OUTCOME: {"code": "XV-both"}})
    with pytest.raises(SystemExit, match="no control build.json"):
        VC.cmd_floor(_args(shard=(0, 3)))
    with pytest.raises(SystemExit, match="no control build.json"):
        VC.cmd_read(_args())
    assert calls == []


def test_guards_run_before_numpy_or_any_render():
    code = ("import sys; from learn import scratch_voice as V, voice_control as VC\n"
            "def no(*a): raise SystemExit('refused')\n"
            "V.require_voice = no\n"
            "VC.ControlWorld.render = lambda *a: print('RENDERED')\n"
            "for argv in (['floor', '--shard', '0/3'], ['build', '--shard', '0/3'], ['read']):\n"
            "    try:\n        VC.main(argv)\n    except SystemExit as e:\n        print(e)\n"
            "print('numpy' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["refused", "refused", "refused", "False"]


# --- the read (pure parts, fakes) -------------------------------------------------------------------------------------

def test_floors_of_refuses_a_malformed_record():
    build = {"parts": {"k": {"guitars": {g: {"audio_sha256": _h(g)} for g in VC.BUILT}}}}
    stored = {"k": {"tr-di": {"held": 2.0}, "vc-own": {"held": 1.5}}}
    ok = {"k": {"guitars": {"tr-uc": {"held": 2.1, "dry_sha256": _h("tr-uc")},
                            "vc-uc": {"held": None, "refused": "silent", "reran": True, "dry_sha256": _h("vc-uc")}}}}
    fl, why = VC.floors_of(stored, ok, build)
    assert fl["k"] == {"tr-di": 2.0, "vc-own": 1.5, "tr-uc": 2.1, "vc-uc": None} and why == {"k": {"vc-uc": "silent"}}
    bad = json.loads(json.dumps(ok))
    bad["k"]["guitars"]["vc-uc"] = {"held": math.nan, "dry_sha256": _h("vc-uc")}
    with pytest.raises(SystemExit, match="malformed"):
        VC.floors_of(stored, bad, build)
    bad["k"]["guitars"]["vc-uc"] = {"held": 1.0, "dry_sha256": "other"}
    with pytest.raises(SystemExit, match="not rendered from the control build"):
        VC.floors_of(stored, bad, build)
    with pytest.raises(SystemExit, match="sets"):
        VC.floors_of(stored, {"k": {"guitars": dict(ok["k"]["guitars"], **{"vc-own": {"held": 1.0}})}}, build)


def test_own_floors_take_only_the_hashed_records():
    rows = {"floors_sha256": {V.tag("k"): "s1"}}
    rec = {"guitars": {"vc-own": {"held": 1.5, "audio_sha256": "a", "refused": None}}}
    assert VC.own_floors(rows, {"k": (rec, "s1")}) == {"k": {"held": 1.5, "audio_sha256": "a"}}
    with pytest.raises(SystemExit, match="not the one rows.json hashed"):
        VC.own_floors(rows, {"k": (rec, "s2")})
    with pytest.raises(SystemExit, match="refused or not finite"):
        VC.own_floors(rows, {"k": ({"guitars": {"vc-own": {"held": None, "refused": "x"}}}, "s1")})


def test_the_control_runs_only_under_xv_sound_or_xv_both():
    assert VC.outcome_refusal({V.PHASE_OUTCOME: {"code": "XV-both"}}) is None
    assert VC.outcome_refusal({V.PHASE_OUTCOME: {"code": "XV-sound"}}) is None
    for c in ("XV-notes", "XV-undecided", "XV-anomaly", None):
        assert VC.outcome_refusal({V.PHASE_OUTCOME: {"code": c}})
    assert VC.outcome_refusal({})


def _fake_iv(vals, ks=None):
    xs = [v for k, v in vals.items() if v is not None and (ks is None or k in ks) and k.split("/")[0] in V.DECIDING]
    if not xs:
        return None
    m = sum(xs) / len(xs)
    return _iv(m, m - 0.03, m + 0.03)


def test_read_body_on_one_passing_set_with_both_coverage_subsets():
    dec = [f"bks/p{i}" for i in range(6)] + [f"goat/p{i}" for i in range(6)]
    keys = dec + ["panel/p0"]
    floors = {}
    for i, k in enumerate(keys):
        moved = i % 3 == 0                                      # the coverage-moved parts: the drop moves vc-uc
        floors[k] = {"tr-di": 2.0, "vc-own": 1.2, "tr-uc": 1.6, "vc-uc": 1.6 if moved else 1.2}
    floors["goat/p5"]["tr-uc"] = None                           # a refusal: drops from every term
    vals, refused, gaps = VC.term_values(floors)
    clean = [k for i, k in enumerate(keys) if i % 3 != 0]
    body = VC.read_body(vals, refused, gaps, _fake_iv, dec, [dec[:6], dec[6:]], clean, OK)
    assert body["passing_parts_on_the_40"] == 11 and body["refused"] == [V.tag("goat/p5")]
    assert set(body["terms"]) == set(VC.TERM_NAMES)
    assert body["code"] in VC.XC_CODES and body["xc"]["with_clean_subset"] in VC.XC_CODES
    cs = body["coverage_subsets"]
    assert cs["clean"]["parts"] + cs["moved"]["parts"] == 11
    assert cs["clean"]["terms"]["Urx"]["mean"] == 0.0                # Urx 0 where the coverage did not move
    assert body["label"] == "refusal-sensitive" or body["itt"] is not None
    assert body["identity_max_gap"] <= VC.ID_TOL
    assert len(body["cluster_left_out"]["Ux"]) == 2 and set(body["largest_three"]) == set(VC.READ_TERMS)
    assert all(len(t) == 12 for t in body["largest_three"]["Ux"]["tags"])


# --- the ledger ---------------------------------------------------------------------------------------------------------

def test_the_declaration_in_the_ledger():
    doc = json.loads((REPO / "docs" / "dev-test-ledger.json").read_text())
    e = next(t for t in doc["tests"] if t["test_id"] == V.LEDGER_ID)
    d = e[VC.PHASE]
    ks = list(e)                                                                  # appended in order
    assert d["plan"].startswith(V.PLAN) and set(ks[ks.index(VC.PHASE) + 1:]) <= {VC.PHASE_DRY, VC.PHASE_OUTCOME}
    if VC.PHASE_DRY in e:                                                        # the build's hash PR
        h = e[VC.PHASE_DRY]
        assert len(h["sha256"]) == 64 and h["proofs_hold"] is True and h["parts"] == V.PARTS
        assert set(h["proofs"]) == set(VC.PROOFS) and all(v == "47 of 47" for v in h["proofs"].values())
    assert tuple(d["table"]["codes"]) == VC.XC_DECLARED and d["table"]["last_row"] == "anything else"
    assert tuple(d["proofs"])[:-1] == VC.PROOFS and d["hash_key"] == VC.PHASE_DRY and "stops" in d["proofs"]
    assert d["renders"]["expected"] == 148 and d["renders"]["ceiling_no_carry"] == V.CONTROL_RENDERS == 188
    assert d["renders"]["ceiling_with_repeat"] == 196
    assert set(d["terms"]) >= {"Sx", "Ux", "Ubx", "Urx"} and "Sc" not in d["terms"]
    for name in ("Sx", "Ux", "Ubx", "Urx", "tr-uc", "vc-uc", "XC-", "voice_control", "fs/voice/control"):
        assert name in d["grepped"], name
    assert d["seen"]["label"] and d["seen"]["definitions"]["mergeable"] and d["seen"]["definitions"]["re-sourced"]
    assert d["seen"]["definitions"]["window state"] and d["seen"]["definitions"]["fade-in"]
    assert set(d["amendments"]) == {str(i) for i in range(1, 9)}
    assert d["outcome_fields"] == ["code", "coverage_label"] and "XC-anomaly" in d["spend_gate"]
    fx = d["review_fixes"]                                                       # #658's review, appended
    assert fx["outcome_fields"] == list(V.CONTROL_OUTCOME_FIELDS) and fx["waiver_fields"] == list(V.WAIVER_FIELDS)
    assert "coverage_label" in fx["coverage_label_required"] and "answers_code" in fx["waiver_scope"]
    assert "rms_ratio_db" in fx["level_step_db"]
    assert "50 ms" in d["limits"]["timing"] and "coverage-sensitive" in d["coverage_sensitive"]


# --- the builder on a synthetic bank (numpy) --------------------------------------------------------------------------

class _Bank:
    """A stand-in bank: each sample a decaying tone with `prepare_sample`'s 2-ms fade-in, its length by its place."""

    def ok(self, s, f):
        return True

    def own_cents(self, s, f):
        return 0.0

    def note(self, s, f, cents):
        import numpy as np

        k = int(SR * (0.5 + 0.1 * ((s + f) % 4)))
        t = np.arange(k) / SR
        y = np.sin(2 * np.pi * (110.0 * (1 + s) + 7.0 * f) * t) * np.exp(-3.0 * t)
        m = int(NR.NOTE_FADE_IN_S * SR)
        y[:m] *= np.linspace(0.0, 1.0, m)
        return y


NOTES = [{"on": 0.3, "off": 0.9, "pitch": 52, "bends": []}, {"on": 1.2, "off": 1.4, "pitch": 60, "bends": []},
         {"on": 1.21, "off": 2.0, "pitch": 64, "bends": []}, {"on": 2.2, "off": 2.6, "pitch": 57, "bends": []}]


def _synthetic(monkeypatch, tmp_path, unclaimed=(1,)):
    """One part on the stand-in bank, its sound-gap build record made by the same rules: `song_bank.measure` and the
    finish stood in by fixed linear maps; the true DI's rise curve stood in so the groups `unclaimed` have no 3-dB
    rise within +-20 ms and the others do. -> (Part, draw part, raw_l, pad, vb, stored report, identity)."""
    np = pytest.importorskip("numpy")
    for m in ("scipy", "pyloudnorm", "noisereduce"):
        pytest.importorskip(m)
    from learn import rederive_fit as RF
    from learn import scratch_readerr as RX
    from learn import song_bank as SB

    monkeypatch.setattr(V, "voice_dir", lambda: tmp_path / "voice")
    monkeypatch.setattr(SB, "measure", lambda x: np.asarray(x, np.float64) * 0.5)
    rng = np.random.default_rng(11)
    n = int(3.0 * SR)
    length = n + VB.pad_samples()
    raw_l = np.asarray((rng.standard_normal(length) * 0.05).astype(np.float32), np.float64)
    di = np.asarray(np.asarray(SB.measure(np.asarray(raw_l[:n], np.float32)), np.float32), np.float64)
    notes = [dict(x) for x in NOTES]
    onsets = VB.group_onsets(notes)
    hop = 48
    curve = np.zeros(n // hop + 1)
    for gi, t in enumerate(onsets):
        if gi not in unclaimed:
            curve[int(t * SR) // hop] = 10.0
    monkeypatch.setattr(NR, "rise_curve", lambda x, rate=SR: (curve.copy(), hop))

    def finish(y):
        k = np.fft.rfft(SB.measure(y))
        return np.fft.irfft(k * np.linspace(1.0, 0.4, len(k)), len(y))
    T = {"tuning": 0.0, "mutes": [1.7], "tilt": 0.0, "levels": [0.5, -1.0, 0.25]}
    p = RF.Part(notes, n, _Bank(), "ring-soft", None, finish, None, SR, "bks/fake-file.wav", "bks", di, None, T)
    x32 = RF.guitar(p, T)
    p.X, p.x_sha = np.asarray(x32, np.float64), S.npy_sha(x32)
    trace, rep = RX.played_trace(notes, length, p.bank, 0.0, "ring-soft", T["mutes"], SR)
    pad = {"real": VB.pad_samples(), "zeros": 0, "first_n_equal": True}
    own, _ = VB.through_gate(raw_l, VB.own_gain(notes, trace, length, SR, None), finish, n)
    levels_db = NR.frame_levels_db(di, V.COVER["frame"], V.COVER["hop"]).tolist()
    w0, s0 = V.played_windows(notes, trace, n)
    vb = {"unclaimed": V.unclaimed_groups(onsets, curve.tolist(), hop), "cover": V.cover_figures(levels_db, w0, s0, "A"),
          "trace_report": json.loads(json.dumps(rep)), "guitars": {"vc-own": {"audio_sha256": S.npy_sha(own)}},
          "pad": dict(pad)}
    ident = {"scratch_readerr_blob_sha": "a" * 40, "played_trace_sha256": "b" * 64}
    return p, {"held": "A"}, raw_l, pad, vb, rep, ident


def test_no_flags_gives_byte_identical_guitars(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    p, dp, raw_l, pad, vb, rep, ident = _synthetic(monkeypatch, tmp_path, unclaimed=())
    rec = VC.part_record(p, dp, raw_l, pad, vb, rep, ident)
    assert tuple(rec) == VC.PART_FIELDS and all(rec["proofs"][k] is True for k in VC.PROOFS)
    assert rec["dropped"]["groups"] == [] and rec["carried"] is True and rec["coverage_clean"] is True
    assert rec["guitars"]["tr-uc"]["audio_sha256"] == p.x_sha
    assert rec["guitars"]["vc-uc"]["audio_sha256"] == vb["guitars"]["vc-own"]["audio_sha256"]
    assert np.load(VC.dry_path("tr-uc", p.key)).tobytes() == np.asarray(p.X, np.float32).tobytes()
    assert rec["level_step_db"] == {"tr-uc": 0.0, "vc-uc": 0.0}
    assert all(rec["outside_change"][g]["identical"] for g in VC.BUILT)


def test_with_flags_only_the_dropped_spans_change_and_the_kept_grouping_holds(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    from learn import scratch_readerr as RX
    from learn import scratch_rederive as RD

    p, dp, raw_l, pad, vb, rep, ident = _synthetic(monkeypatch, tmp_path, unclaimed=(1,))
    groups_before = NR.onset_groups(p.notes)
    rec = VC.part_record(p, dp, raw_l, pad, vb, rep, ident)
    assert all(rec["proofs"][k] is True for k in VC.PROOFS)
    assert rec["dropped"]["groups"] == [1] and rec["dropped"]["notes"] == [1, 2] and rec["dropped"]["played_notes_n"] == 2
    assert rec["carried"] is False and rec["guitars"]["tr-uc"]["audio_sha256"] != p.x_sha
    assert NR.onset_groups(p.notes) == groups_before and p.notes == NOTES        # the note list is never edited
    json.dumps(rec, allow_nan=False)                                             # indices, never -inf
    # the bytes outside the dropped spans before the hiss removal, checked here directly
    length = p.n + VB.pad_samples()
    trace, _ = RX.played_trace(p.notes, length, p.bank, 0.0, "ring-soft", p.T["mutes"], SR)
    lv = p.T["levels"]
    full, _ = RD._synth(p.notes, p.n, p.bank, p.ring, 0.0, p.T["mutes"], 0.0, lv, None, SR, last=True)
    kept, krep = RD._synth(p.notes, p.n, p.bank, p.ring, 0.0, p.T["mutes"], 0.0, VC.drop_levels(lv, [1]), None, SR,
                           last=True)
    mask = VB.span_mask(VB.own_windows(p.notes, VC.only_trace(trace, [1, 2])), length)
    assert mask.any() and np.array_equal(full[~mask], kept[~mask]) and not np.array_equal(full, kept)
    assert RX.trace_equals_report(krep, rep)                                    # the kept placement and ends hold
    marked = VC.marked_trace(trace, [1, 2])
    assert [t for k, t in enumerate(marked) if k not in (1, 2)] == [t for k, t in enumerate(trace) if k not in (1, 2)]
    g_own = VB.own_gain(p.notes, trace, length)
    g_uc = VB.own_gain(p.notes, marked, length)
    assert np.all(g_uc <= g_own) and np.array_equal(g_uc[~mask], g_own[~mask]) and (g_uc[mask] < g_own[mask]).any()
    assert rec["additive_ratio"] <= VC.DROP_ADD_TOL and rec["support"]["inside"]
    assert rec["outside_change"]["tr-uc"]["samples"] > 0 and rec["cover_after"]["frames"] == rec["cover_before"][
        "frames"]
    with pytest.raises(SystemExit, match="record exists"):
        VC.part_record(p, dp, raw_l, pad, vb, rep, ident)


@pytest.mark.parametrize("broken", ["flags", "vc-own", "report", "x", "pad", "cover", "gate"])
def test_a_failing_proof_stops_before_anything_is_written(monkeypatch, tmp_path, broken):
    np = pytest.importorskip("numpy")
    p, dp, raw_l, pad, vb, rep, ident = _synthetic(monkeypatch, tmp_path, unclaimed=(1,))
    vb = json.loads(json.dumps(vb))
    if broken == "flags":
        vb["unclaimed"]["flags"] = [False, False, False]
    elif broken == "vc-own":
        vb["guitars"]["vc-own"]["audio_sha256"] = "0" * 64
    elif broken == "report":
        rep = dict(rep, played=rep["played"] + 1)
    elif broken == "x":
        p.x_sha = "0" * 64
    elif broken == "pad":
        vb["pad"]["real"] -= 1
    elif broken == "cover":
        vb["cover"]["uncovered_weight"] += 1.0
    elif broken == "gate":                                       # vc-uc's gate above vc-own's somewhere
        real = VB.own_gain

        def own_gain(notes, trace, length, rate=SR, end=None):
            g = real(notes, trace, length, rate, end)
            return g + 1e-9 if any(t.get("dropped") for t in trace) else g
        monkeypatch.setattr(VB, "own_gain", own_gain)
    with pytest.raises(SystemExit) as e:
        VC.part_record(p, dp, raw_l, pad, vb, rep, ident)
    assert "fake-file" not in str(e.value) and V.tag(p.key) in str(e.value)
    if broken == "gate":
        assert "gate_outside_same" in str(e.value)
    assert not VC.part_path(p.key).exists() and not any(VC.dry_path(g, p.key).exists() for g in VC.BUILT)


def test_drop_is_additive_on_the_synthesis():
    np = pytest.importorskip("numpy")
    from learn import scratch_rederive as RD

    notes = [dict(x) for x in NOTES]
    n = int(3.0 * SR)
    lv = [0.5, -1.0, 0.25]
    full, _ = RD._synth(notes, n, _Bank(), "ring-soft", 0.0, [], 0.0, lv, None, SR, last=True)
    for g in ([0], [1], [0, 2]):
        kept, _ = RD._synth(notes, n, _Bank(), "ring-soft", 0.0, [], 0.0, VC.drop_levels(lv, g), None, SR, last=True)
        only, _ = RD._synth(notes, n, _Bank(), "ring-soft", 0.0, [], 0.0, VC.only_levels(lv, g), None, SR, last=True)
        assert VC.additive_ratio(full, kept, only) <= VC.DROP_ADD_TOL
        assert VC.additive_ratio(full, kept, np.zeros_like(only)) > VC.DROP_ADD_TOL
