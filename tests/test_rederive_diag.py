"""The re-derivation's diagnosis (`learn/rederive_diag.py`, `docs/rederive-plan.md` section 5): the names, the guards
(every command refuses off main, without its keys, with other code; `controls-real` until fs-refit's answers are
hashed), the paths (under PF/fs/rederive/ only, written once), the D_list reproduction rule, the trace's mapping, the
per-note comparison, the tracker figures and their Spearman table, the design-time parts, the control groups (gate
included) and the bench's `controls`. Synthetic keys; pure: runs on the light CI runner (no numpy). The last tests need
numpy, scipy, noisereduce and pyloudnorm: the trace byte-identical on a made-up part, J0's dry run against
`aligned_distance` itself, the figures and one part's diagnosis (skipped elsewhere)."""
import ast
import json
import math
import pathlib

import pytest

from learn import note_rebuild as NR
from learn import rederive_diag as D
from learn import scratch_exact as SE
from learn import scratch_rederive as RD
from learn import scratch_search as S

REPO = pathlib.Path(__file__).resolve().parents[1]


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


def _args(**kw):
    return type("A", (), dict(kw))()


# --- names, imports, guarded files ----------------------------------------------------------------------------------------

def test_names_and_constants():
    assert D.OWN_FILES == ("learn/rederive_diag.py", "analysis/aligned.py", "learn/knob_ceiling.py",
                           "learn/full_space.py", "learn/pipeline_fix.py")
    assert D.CODE_FILES[:5] == D.OWN_FILES and set(RD.CODE_FILES) <= set(D.CODE_FILES)
    assert len(set(D.CODE_FILES)) == len(D.CODE_FILES) and all((REPO / f).exists() for f in D.CODE_FILES)
    assert D.DIAG_ROWS == ("xn-list", "xf-now") and D.GUITARS == ("x", "xn-list", "xf-now")
    assert D.VALUES_OF == {"x": None, "xn-list": "in-F", "xf-now": "in-M"}
    assert D.DECLARED == {"d_list": _iv(0.321, 0.180, 0.462), "d_list_passing_only": _iv(0.285, 0.173, 0.396)}
    assert D.DESIGN_PARTS == ("sw50r-refused", "item_69")
    assert "gate" in D.GROUPS and D.GROUPS[:4] == ("drive", "tone", "cab", "effects")
    assert D.BENCH_ROWS == SE.ROWS + RD.BENCH_ROWS and D.REAL_PAIR == ("fs-refit", "b2")
    assert sorted(D.COMMANDS) == ["controls", "controls-real", "run"]
    assert "descriptive" in D.DESCRIPTIVE


def test_the_j0_constants_are_aligned_distances_defaults():
    import inspect

    a = pytest.importorskip("analysis.aligned")
    sig = inspect.signature(a.aligned_distance).parameters
    assert {k: sig[k].default for k in D.J0} == D.J0
    assert sig["di_floor_db"].default == D.FLOOR_DB


def test_the_module_imports_only_the_standard_library_at_module_level():
    tree = ast.parse((REPO / "learn" / "rederive_diag.py").read_text())
    mods = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module.split(".")[0])
    assert mods <= {"__future__", "argparse", "contextlib", "json", "math", "pathlib", "statistics", "time", "learn"}


def test_the_module_patches_no_guarded_code():
    """The trace wraps `note_end` only inside `traced` (restored after); nothing else in a guarded module is assigned."""
    src = (REPO / "learn" / "rederive_diag.py").read_text()
    tree = ast.parse(src)
    assigned = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name):
                    assigned.add(f"{t.value.id}.{t.attr}")
    assert assigned - {"self._bank", "self.calls"} == {"NR.note_end"}       # the proxy's own state apart
    for f in ("note_transcribe.py", "scratch_exact.py", "scratch_search.py", "scratch_notes.py", "note_rebuild.py",
              "scratch_rederive.py"):
        assert f"learn/{f}" in D.CODE_FILES


# --- the guards ----------------------------------------------------------------------------------------------------------------

MAIN_BEFORE = {S.PHASE: 1, S.PHASE_DRAW: {}, SE.PHASE_BANK: {}, SE.PHASE: {}, SE.PHASE_TARGETS: {}}
EXACT_ANSWERS = {SE.answers_key(r): {} for r in SE.ROWS}


@pytest.mark.parametrize("cmd", sorted(D.COMMANDS))
def test_every_command_refuses_off_main(monkeypatch, cmd):
    monkeypatch.setattr(S, "on_main", lambda: (None, "this checkout's learn/scratch_search.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        D.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", sorted(D.COMMANDS))
def test_every_command_refuses_without_the_declaration(monkeypatch, cmd):
    main = dict(MAIN_BEFORE, **EXACT_ANSWERS)
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    with pytest.raises(SystemExit, match="has no phase_scratch_rederive"):
        D.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", sorted(D.COMMANDS))
def test_every_command_refuses_with_other_code_or_keys(monkeypatch, cmd):
    from learn import note_replay as NRP

    main = dict(MAIN_BEFORE, **EXACT_ANSWERS, **{RD.PHASE: {}, RD.answers_key(RD.REAL_ROW): {},
                                                  SE.PHASE_B2_ANSWERS: {}})
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    monkeypatch.setattr(RD, "pinned_identity", lambda: {"learn/scratch_exact.py": False})
    with pytest.raises(SystemExit, match="scratch_exact.py.*differ from main's"):
        D.COMMANDS[cmd](_args())
    monkeypatch.setattr(RD, "pinned_identity", lambda: {f: True for f in RD.CODE_FILES})
    monkeypatch.setattr(NRP, "ledger_entry", lambda: dict(main, phase_scratch_rederive_ladder={}))
    with pytest.raises(SystemExit, match="phase_scratch_rederive_ladder"):
        D.COMMANDS[cmd](_args())
    monkeypatch.setattr(NRP, "ledger_entry", lambda: main)
    monkeypatch.setattr(D, "pinned_identity", lambda: {"learn/rederive_diag.py": False})
    with pytest.raises(SystemExit, match="rederive_diag.py.*differ from main's"):
        D.COMMANDS[cmd](_args())


def test_run_needs_the_exact_rows_answers(monkeypatch):
    main = dict(MAIN_BEFORE, **{RD.PHASE: {}})
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    with pytest.raises(SystemExit, match="has no phase_scratch_exact_answers_bank"):
        D.cmd_run(_args())


def test_controls_real_refuses_cleanly_until_the_refit_answers_are_hashed(monkeypatch, tmp_path):
    from learn import note_replay as NRP

    main = dict(MAIN_BEFORE, **EXACT_ANSWERS, **{RD.PHASE: {}, SE.PHASE_B2_ANSWERS: {}})
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    with pytest.raises(SystemExit, match="has no phase_scratch_rederive_answers_refit: merge it before running"):
        D.cmd_controls_real(_args())
    main[RD.answers_key(RD.REAL_ROW)] = {}                     # the key, but no hashed file behind it
    monkeypatch.setattr(RD, "pinned_identity", lambda: {f: True for f in RD.CODE_FILES})
    monkeypatch.setattr(D, "pinned_identity", lambda: {f: True for f in D.OWN_FILES})
    monkeypatch.setattr(NRP, "ledger_entry", lambda: main)
    monkeypatch.setattr(RD, "rederive_dir", lambda: tmp_path)
    with pytest.raises(SystemExit, match="has no answers-fs-refit.json"):          # Unit 4 merged: no file yet
        D.cmd_controls_real(_args())
    assert not D.controls_real_path().exists()
    f = tmp_path / "answers-fs-refit.json"
    f.write_text("{}")                                         # a file, but not the hashed one
    with pytest.raises(SystemExit, match="is not main's phase_scratch_rederive_answers_refit"):
        D.cmd_controls_real(_args())
    assert not D.controls_real_path().exists()


def test_the_outputs_are_never_overwritten(monkeypatch, tmp_path):
    monkeypatch.setattr(D, "require_diag", lambda *a: {})
    monkeypatch.setattr(RD, "rederive_dir", lambda: tmp_path)
    D.run_path().parent.mkdir(parents=True, exist_ok=True)
    D.run_path().write_text("{}")
    with pytest.raises(SystemExit, match="never overwritten"):
        D.cmd_run(_args())
    D.controls_real_path().parent.mkdir(parents=True, exist_ok=True)
    D.controls_real_path().write_text("{}")
    with pytest.raises(SystemExit, match="never overwritten"):
        D.cmd_controls_real(_args())


def test_run_stops_when_d_list_does_not_reproduce(monkeypatch, tmp_path):
    from learn import note_transcribe as NT

    monkeypatch.setattr(D, "require_diag", lambda *a: {})
    monkeypatch.setattr(RD, "rederive_dir", lambda: tmp_path)
    monkeypatch.setattr(NT, "redo_on_main", lambda: ({}, None))
    monkeypatch.setattr(SE, "context", lambda: ({"parts": []}, None))
    bad = {"reproduced": {"d_list": True, "d_list_passing_only": False}, "equals_stored_rows": True,
           "intervals": {}}
    monkeypatch.setattr(D, "d_list_read", lambda m, draw, sd: bad)
    with pytest.raises(SystemExit, match="does not reproduce"):
        D.cmd_run(_args())
    bad["reproduced"]["d_list_passing_only"] = True
    bad["equals_stored_rows"] = False
    with pytest.raises(SystemExit, match="does not reproduce"):
        D.cmd_run(_args())
    assert not D.run_path().exists()


def test_the_cli():
    with pytest.raises(SystemExit):
        D.main(["ladder"])


# --- paths --------------------------------------------------------------------------------------------------------------------

def test_every_output_sits_under_pf_fs_rederive_apart_from_the_ladders():
    root = RD.rederive_dir()
    outs = [D.run_path(), D.run_part_path("bks__k/1"), D.controls_real_path()] + \
        [D.controls_path(r) for r in D.BENCH_ROWS]
    for p in outs:
        assert root in p.parents and p.suffix == ".json"
    assert root.name == "rederive" and root.parent == S.fs_dir()
    assert D.run_part_path("bks__k/1").name == "bks__k__1.json"
    ladder = {RD.ladder_path(), RD.part_path("bks__k/1")} | {RD.dry_path(r, "bks__k/1") for r in RD.LADDER_WRITES}
    assert not set(outs) & ladder and len(set(outs)) == len(outs)
    assert all(RD.rederive_dir() / "dry" not in p.parents and RD.rederive_dir() / "ladder" not in p.parents
               for p in outs)
    with pytest.raises(ValueError):
        D.controls_path("fs-stem")


# --- the D_list rule ---------------------------------------------------------------------------------------------------------

def test_reproduced_rounds_to_three_places():
    want = D.DECLARED["d_list"]
    assert D.reproduced(_iv(0.321092185667447, 0.1797484538302176, 0.46243591750467644), want)
    assert D.reproduced(_iv(0.2846583204585031, 0.1733298915206224, 0.3959867493963838),
                        D.DECLARED["d_list_passing_only"])
    assert not D.reproduced(_iv(0.3216, 0.1797, 0.4624), want)
    assert not D.reproduced(_iv(0.321, 0.180, 0.463), want)
    for bad in (None, {}, _iv(math.nan, 0.18, 0.46), _iv(0.321, 0.5, 0.46)):
        assert not D.reproduced(bad, want)


def test_d_list_read_pairs_the_two_rows(monkeypatch, tmp_path):
    per_bank = {"a": {"G": -0.5}, "b": {"G": -0.2}, "c": {"G": -0.4}}
    per_list = {"a": {"G": -0.1}, "b": None, "c": {"G": -0.3}}
    rn = {"xn-bank": {"itt": per_bank, "per": per_bank, "refused": {}, "answers_sha256": "s1"},
          "xn-list": {"itt": dict(per_list, b={"G": 0.0, "cen_fallback": True}), "per": per_list,
                      "refused": {"b": {}}, "answers_sha256": "s2"}}
    monkeypatch.setattr(SE, "row_numbers", lambda m, draw, row: rn[row])
    seen = []

    def bg(sd, draw, vals, keys=None):
        seen.append(dict(vals))
        return {"bks_goat": {"all": _iv(sum(vals.values()) / len(vals), -1, 1)}}
    monkeypatch.setattr(SE, "_bg", bg)
    monkeypatch.setattr(SE, "rows_path", lambda: tmp_path / "rows.json")
    out = D.d_list_read({}, {}, None)
    assert out["per_part"] == pytest.approx({"a": 0.4, "b": 0.2, "c": 0.1})
    assert out["per_part_passing"] == pytest.approx({"a": 0.4, "c": 0.1}) and out["refused"] == ["b"]
    assert out["equals_stored_rows"] is None and out["reproduced"] == {"d_list": False, "d_list_passing_only": False}
    stored = {"rows": {"arms": {"answer": {"D": {"D_list": {"bks_goat": {"all": out["intervals"]["d_list"]}}}}}}}
    (tmp_path / "rows.json").write_text(json.dumps(stored))
    assert D.d_list_read({}, {}, None)["equals_stored_rows"] is True


# --- control groups ---------------------------------------------------------------------------------------------------------

def test_the_gate_is_its_own_group():
    ftg = {"parameters/gateThreshold": "other", "parameters/gateActive": "other", "cabParameters/x": "cab",
           "parameters/outputGain": "other", "weird/x": "nonsense"}.get
    assert D.group_of_name("parameters/gateThreshold", ftg) == "gate"
    assert D.group_of_name("parameters/gateActive", ftg) == "gate"
    assert D.group_of_name("cabParameters/x", ftg) == "cab"
    assert D.group_of_name("parameters/outputGain", ftg) == "other"
    assert D.group_of_name("weird/x", ftg) == "other"


def test_the_real_groups_cover_the_learned_controls():
    from learn import pipeline_fix as P

    assert D.control_group("parameters/gateThreshold") == "gate" == D.control_group("parameters/gateActive")
    assert D.control_group("cabParameters/leftMicType") == "cab"
    assert D.control_group("drive1/drive1Gain") == P.ftg_group("drive1/drive1Gain") == "drive"
    assert D.control_group("reverb/reverbMix") == "effects"
    try:
        from learn import full_space as F
    except Exception:                                  # the learned layout needs its pack: not on the light runner
        pytest.skip("full_space's layout is not available here")
    names = list(F.CONT) + list(F.SW) + list(F.CAT)
    got = {n: D.control_group(n) for n in names}
    assert set(got.values()) <= set(D.GROUPS) and "other" not in got.values()
    assert {n for n, g in got.items() if g == "gate"} == {"parameters/gateThreshold", "parameters/gateActive"}


class _Space:
    """A made-up `full_space`: two continuous dims, one switch, one category."""
    CONT = ["drive1/drive1Gain", "parameters/gateThreshold"]
    SW = ["parameters/gateActive"]
    CAT = ["cabParameters/leftMicType"]

    @staticmethod
    def encode(x, amp):
        c = [float(x.get(("drive1", "drive1Gain"), 0.0)), float(x.get(("parameters", "gateThreshold"), 0.0))]
        on = str(x.get(("parameters", "gateActive"), "false")) == "true"
        cm = [1.0, 1.0 if on else 0.0]
        s, sm = [float(on)], [1.0]
        k, km = [int(x.get(("cabParameters", "leftMicType"), 0))], [1.0]
        return c, cm, s, sm, k, km, 0


def test_group_distance_reads_only_what_sounds():
    a = {"drive1/drive1Gain": 0.25, "parameters/gateThreshold": 0.9, "parameters/gateActive": "false",
         "cabParameters/leftMicType": 2}
    b = dict(a, **{"drive1/drive1Gain": 0.75})
    g = D.group_distance(a, b, "amp-1", space=_Space)
    assert g["drive"] == {"cont": 1, "mean_abs_unit": 0.5, "switches": 0, "switches_differ": 0, "cats": 0,
                          "cats_differ": 0, "dims": 1, "distance": 0.5}
    assert g["gate"]["cont"] == 0 and g["gate"]["switches"] == 1 and g["gate"]["distance"] == 0.0  # gate off: no thr
    assert g["cab"]["cats"] == 1 and g["cab"]["distance"] == 0.0 and g["tone"]["distance"] is None
    c = dict(a, **{"parameters/gateActive": "true", "parameters/gateThreshold": 0.5, "cabParameters/leftMicType": 3})
    g2 = D.group_distance(a, c, "amp-1", space=_Space)
    assert g2["gate"]["cont"] == 1 and g2["gate"]["switches_differ"] == 1
    assert g2["gate"]["distance"] == pytest.approx((0.4 + 1.0) / 2) and g2["cab"]["cats_differ"] == 1


def test_per_part_distances_and_pairs(monkeypatch):
    monkeypatch.setattr(D, "group_distance", lambda a, b, amp: {g: {"distance": abs(a["v"] - b["v"])} for g in D.GROUPS})
    answers = {"a": {"select": 1, "answer": {"v": 0.5}}, "b": {"select": 2, "answer": {"v": 0.1}},
               "c": {"select": 1, "answer": None}, "d": {"select": 1, "answer": {"v": 0.0}}}
    against = {"a": {"select": 1, "settings": {"v": 0.25}}, "b": {"select": 1, "settings": {"v": 0.0}},
               "c": {"select": 1, "settings": {"v": 0.0}}}
    per, sel = D.per_part_distances(answers, against, {k: "amp" for k in "abcd"})
    assert sorted(per) == ["a"] and sel == ["b"] and per["a"]["cab"]["distance"] == 0.25
    old = {"a": {"cab": {"distance": 0.5}}, "z": {"cab": {"distance": 0.1}}}
    assert D.group_values(per, "cab") == {"a": 0.25}
    assert D.paired_group(per, old, "cab") == {"a": -0.25}
    assert D.group_values({"a": {"cab": {"distance": None}}}, "cab") == {}


def _controls_world(monkeypatch, tmp_path):
    draw = {"parts": [{"pkey": "bks__u1|amp-1", "amp": "amp-1", "set": "bks"},
                      {"pkey": "goat__u2|amp-2", "amp": "amp-2", "set": "goat"}]}
    targets = {"parts": {p["pkey"]: {"select": 1, "target": {"v": 0.0}} for p in draw["parts"]}}
    ans = {r: {"parts": {p["pkey"]: {"select": 1, "answer": {"v": 0.1 * (j + 1)}, "shrunk": {"v": 0.05}}
                         for p in draw["parts"]}} for j, r in enumerate(SE.ROWS)}
    for r in SE.ROWS:
        (tmp_path / f"answers-{r}.json").write_text(json.dumps(ans[r]))
    main = {SE.answers_key(r): {} for r in SE.ROWS}
    monkeypatch.setattr(D, "require_diag", lambda *a: main)
    monkeypatch.setattr(RD, "rederive_dir", lambda: tmp_path / "rd")
    monkeypatch.setattr(SE, "context", lambda: (draw, None))
    monkeypatch.setattr(SE, "require_targets", lambda m: targets)
    monkeypatch.setattr(SE, "targets_path", lambda: tmp_path / "answers-xn-bank.json")
    monkeypatch.setattr(SE, "answers_path", lambda row: tmp_path / f"answers-{row}.json")
    monkeypatch.setattr(SE, "require_answers", lambda m, row: json.loads((tmp_path / f"answers-{row}.json").read_text()))
    monkeypatch.setattr(D, "group_distance", lambda a, b, amp: {g: {"distance": abs(a["v"] - b["v"])} for g in D.GROUPS})
    monkeypatch.setattr(SE, "_bg", lambda sd, draw, vals, keys=None: {
        "bks_goat": {"all": _iv(sum(vals.values()) / len(vals), -1.0, 1.0)}, "pool_47": None, "per_set": None})
    return draw, main


def test_controls_writes_each_answered_row_once(monkeypatch, tmp_path, capsys):
    _controls_world(monkeypatch, tmp_path)
    D.cmd_controls(_args())
    out = capsys.readouterr().out
    for r in SE.ROWS:
        rec = json.loads(D.controls_path(r).read_text())
        assert rec["row"] == r and rec["answers_sha256"] == S.file_sha(tmp_path / f"answers-{r}.json")
        assert set(rec["per_part"]) == set(D.ARMS) and set(rec["rows"]["answer"]) == set(D.GROUPS)
    assert not any(D.controls_path(r).exists() for r in RD.BENCH_ROWS)
    assert "waiting for their answers on main: " + ", ".join(RD.BENCH_ROWS) in out
    lst = json.loads(D.controls_path("xn-list").read_text())
    assert lst["rows"]["answer"]["cab"]["bks_goat"]["all"]["mean"] == pytest.approx(0.4)
    assert "less xn-bank's" in out and "bks__" not in out and "goat__" not in out       # no part key leaves PF
    before = {r: S.file_sha(D.controls_path(r)) for r in SE.ROWS}
    D.cmd_controls(_args())                                         # a rerun reads its files, rewrites none
    assert before == {r: S.file_sha(D.controls_path(r)) for r in SE.ROWS}
    (tmp_path / "answers-xn-swap.json").write_text("{}")
    monkeypatch.setattr(SE, "require_answers", lambda m, row: {"parts": {}})
    with pytest.raises(SystemExit, match="other answers"):
        D.cmd_controls(_args())


def test_controls_refuses_a_hashed_bench_row_without_unit_4(monkeypatch, tmp_path):
    import sys

    _, main = _controls_world(monkeypatch, tmp_path)
    main[RD.answers_key("xf-now")] = {}
    monkeypatch.setitem(sys.modules, "learn.rederive_rows", None)       # not importable
    with pytest.raises(SystemExit, match="no learn/rederive_rows.py: merge Unit 4"):
        D.cmd_controls(_args())


# --- J0's refusal wording ------------------------------------------------------------------------------------------------------

def test_j0_refusal_in_aligned_distances_order_and_words():
    assert D.j0_refusal(7, 0.0) == "the DI plays in too few frames"
    assert D.j0_refusal(7, 0.9) == "the DI plays in too few frames"          # the frame count is checked first
    assert D.j0_refusal(8, 0.5) is None
    assert D.j0_refusal(8, 0.51) == "51% of the scored frames are pauses, over 50%"


# --- the trace's mapping (pure) --------------------------------------------------------------------------------------------

def _notes():
    return [{"on": 0.5, "off": 1.0, "pitch": 60}, {"on": 0.5, "off": 1.0, "pitch": 55},      # one chord
            {"on": 1.0, "off": 1.5, "pitch": 99},                                           # unplayable: skipped
            {"on": 2.0, "off": 2.5, "pitch": 62}]


def _trace(notes):
    """The calls `synthesise_redo` would make: placement in group order, pitch order inside a group, then render in
    index order; note 2 is skipped (no bank call)."""
    placed = [1, 0, 3]
    calls = [(6 - k, notes[k]["pitch"] - 40, 0.0, 1000 + k) for k in placed]
    ends = [{"on": notes[k]["on"], "off": notes[k]["off"], "end": 9.0, "kind": "sample", "fade": 0.15}
            for k in placed]
    ends += [{"on": notes[k]["on"], "off": notes[k]["off"], "end": notes[k]["off"] + 0.15 + k, "kind": "release",
              "fade": 0.15} for k in sorted(placed)]
    return calls, ends


def _pitch_of(c):
    return c[1] + 40


def test_match_trace_maps_every_call_to_its_note():
    notes = _notes()
    groups = [[0, 1], [2], [3]]
    assert D.placement_order(notes, groups) == [1, 0, 2, 3]
    calls, ends = _trace(notes)
    m = D.match_trace(notes, groups, calls, ends, _pitch_of)
    assert sorted(m) == [0, 1, 3]
    assert m[0]["fret"] == 20 and m[1]["fret"] == 15 and m[3]["string"] == 3 and m[1]["samples"] == 1001
    assert m[3]["end"] == pytest.approx(2.5 + 0.15 + 3) and m[0]["kind"] == "release"   # the render call's end


def test_match_trace_refuses_a_trace_that_does_not_fit():
    notes = _notes()
    groups = [[0, 1], [2], [3]]
    calls, ends = _trace(notes)
    with pytest.raises(ValueError, match="does not fit"):
        D.match_trace(notes, groups, calls, ends[:-1], _pitch_of)
    with pytest.raises(ValueError, match="matches no note"):
        D.match_trace(notes, groups, [(1, 1, 0.0, 10)] + calls[1:], ends, _pitch_of)
    bad = [dict(e) for e in ends]
    bad[-1]["on"] = 7.0
    with pytest.raises(ValueError, match="not its own"):
        D.match_trace(notes, groups, calls, bad, _pitch_of)


def test_the_trace_wraps_note_end_and_restores_it():
    orig = NR.note_end

    class Bank:
        def note(self, s, f, cents):
            return [0.0] * 5

        def ok(self, s, f):
            return True
    with D.traced(Bank()) as (proxy, ends):
        assert NR.note_end is not orig
        y = proxy.note(1, 2, 3.0)
        assert proxy.ok(1, 2) and len(y) == 5 and proxy.calls == [(1, 2, 3.0, 5)]
        got = NR.note_end(1.0, 1.2, "ring-soft", [1.1], 2.0, cut=False)
        assert got == orig(1.0, 1.2, "ring-soft", [1.1], 2.0, cut=False)
        assert ends == [{"on": 1.0, "off": 1.2, "end": got[0], "kind": "mute", "fade": NR.MUTE_FADE_S}]
    assert NR.note_end is orig
    with pytest.raises(RuntimeError):
        with D.traced(Bank()):
            raise RuntimeError("stop")
    assert NR.note_end is orig


# --- the per-note comparison, the figures and the tables (pure) --------------------------------------------------------------

def _row(played=True, s=1, f=5, end=1.0, kind="release", lv=0.0, early=-20.0, late=-30.0):
    return {"played": played, "string": s, "fret": f, "end": end, "kind": kind, "group_level_db": lv,
            "early_db": early, "late_db": late}


def test_note_compare():
    x = [_row(), _row(s=2), _row(kind="mute", end=2.0), _row(played=False), _row(late=None)]
    y = [_row(), _row(s=3), _row(kind="release", end=2.5, lv=2.0, late=-25.0), _row(), _row(early=-21.0)]
    c = D.note_compare(x, y)
    assert c["notes"] == 5 and c["played_x"] == 4 and c["played"] == 5 and c["both"] == 4
    assert c["source_changed"] == 1 and c["kind_changed"] == 1 and c["kind_changes"] == {"mute->release": 1}
    assert c["end_shift_abs_median_s"] == pytest.approx(0.0) and c["end_shift_median_s"] == pytest.approx(0.0)
    assert c["group_level_abs_median_db"] == 0.0 and c["early_median_db"] == pytest.approx(0.0)
    assert c["late_median_db"] == pytest.approx(0.0) and c["decay_median_db"] == pytest.approx(0.0)
    assert c["source_changed_share"] == 0.25 and c["kind_changed_share"] == 0.25
    with pytest.raises(ValueError):
        D.note_compare(x, y[:-1])


def _j0(pause, refused=None):
    return {h: {n: {"pauses": pause, "refused": refused} for n in ("1024", "2048", "4096")} for h in ("A", "B")}


def _rec(set_="bks", env=0.9, logmel=2.0, tilt=0.0, extra=1, missed=1, refused=None):
    fig = {"env_corr": env, "logmel": logmel, "crest_diff_db": -1.0, "peak_diff_db": 2.0,
           "tail_decay": {"diff_median_db": -3.0},
           "halves": {h: {"level_diff_db": -0.5, "env_corr": env, "logmel": logmel} for h in ("A", "B")}}
    notes = {"source_changed_share": 0.1, "kind_changed_share": 0.2, "end_shift_abs_median_s": 0.03,
             "early_median_db": -1.0, "late_median_db": 2.0}
    err = {"tuning_cents": 1.0, "tilt_db_s": tilt, "levels_median_db": 1.5,
           "mutes": {"extra": extra, "missed": missed}}
    g = {"figures": fig, "notes": notes, "j0": _j0(0.3, refused), "trace": {"identical": True}}
    return {"set": set_, "groups": 4, "guitars": {"x": {"j0": _j0(0.1)}, "xn-list": g, "xf-now": g},
            "errors": {"xn-list": err, "xf-now": err}}


def test_tracker_figures():
    f = D.tracker_figures(_rec(refused="x"), "xn-list")
    assert f["one_minus_env_corr"] == pytest.approx(0.1) and f["logmel_to_x"] == 2.0
    assert f["crest_diff_db_abs"] == 1.0 and f["peak_diff_db_abs"] == 2.0 and f["tail_decay_abs_median_db"] == 3.0
    assert f["pause_share_rise_max"] == pytest.approx(0.2) and f["j0_dry_refusals"] == 6
    assert f["mute_changes_per_group"] == 0.5 and f["late_level_abs_median_db"] == 2.0
    assert f["level_diff_db_abs_A"] == 0.5 and f["one_minus_env_corr_B"] == pytest.approx(0.1)
    rec = _rec()
    rec["guitars"]["xn-list"]["figures"]["env_corr"] = None
    assert D.tracker_figures(rec, "xn-list")["one_minus_env_corr"] is None


def test_the_spearman_table_and_the_summary():
    recs = {f"bks__k{i}": _rec(env=1 - 0.1 * i, tilt=float(i)) for i in range(5)}
    recs["panel__k9"] = _rec(set_="panel", env=0.1)
    d = {k: 0.1 * i for i, k in enumerate(sorted(recs))}
    keys = [k for k in sorted(recs) if recs[k]["set"] in RD.DECIDING]
    figs = {k: D.tracker_figures(recs[k], "xn-list") for k in recs}
    t = D.spearman_table(figs, d, keys)
    assert t["label"] == D.DESCRIPTIVE
    assert t["figures"]["one_minus_env_corr"] == {"rho": pytest.approx(1.0), "parts": 5}
    assert t["figures"]["tilt_change_abs_db_s"]["rho"] == pytest.approx(1.0)
    assert t["figures"]["logmel_to_x"]["rho"] is None                    # no spread
    s = D.summarise(recs, keys)
    assert s["xn-list"]["parts"] == 5 and s["xn-list"]["trace_identical"] == 5
    assert s["xn-list"]["figures"]["one_minus_env_corr"]["mean"] == pytest.approx(0.2)
    assert s["xn-list"]["j0_dry_refused_parts"] == {"A": {"x": 0, "xn-list": 0}, "B": {"x": 0, "xn-list": 0}}


def test_the_design_time_parts():
    parts = [{"pkey": "bks__u1|sw50r", "set": "bks", "unit": "bks/u1", "amp": "sw50r"},
             {"pkey": "bks__u2|sw50r", "set": "bks", "unit": "bks/u2", "amp": "sw50r"},
             {"pkey": "bks__u3|ac20", "set": "bks", "unit": "bks/u3", "amp": "ac20"},
             {"pkey": "goat__item_69|ac20", "set": "goat", "unit": "goat/item_69@15.0#amp_5", "amp": "ac20"},
             {"pkey": "goat__item_690|ac20", "set": "goat", "unit": "goat/item_690@15.0#amp_5", "amp": "ac20"}]
    got = D.design_parts(parts, ["bks__u2|sw50r", "bks__u3|ac20"])
    assert got == {"sw50r-refused": "bks__u2|sw50r", "item_69": "goat__item_69|ac20"}
    with pytest.raises(SystemExit, match="not one each"):
        D.design_parts(parts, ["bks__u3|ac20"])
    with pytest.raises(SystemExit, match="not one each"):
        D.design_parts(parts + [dict(parts[3], pkey="goat__item_69|pr12")], ["bks__u2|sw50r"])


def test_require_ladder(monkeypatch, tmp_path):
    monkeypatch.setattr(RD, "rederive_dir", lambda: tmp_path)
    with pytest.raises(SystemExit, match="no ladder.json"):
        D.require_ladder("b", "x")
    RD.part_path("bks__k1").parent.mkdir(parents=True)
    RD.part_path("bks__k1").write_text('{"T": 1}')
    lad = {"proofs_hold": True, "proofs": {"p": {"held": 1, "of": 1}}, "bank_build_sha256": "b",
           "exact_build_sha256": "x", "parts": {"bks__k1": {"record_sha256": S.file_sha(RD.part_path("bks__k1"))}}}
    RD.ladder_path().write_text(json.dumps(lad))
    got, recs = D.require_ladder("b", "x")
    assert recs == {"bks__k1": {"T": 1}}
    with pytest.raises(SystemExit, match="not made from these builds"):
        D.require_ladder("b", "other")
    RD.part_path("bks__k1").write_text('{"T": 2}')
    with pytest.raises(SystemExit, match="changed since"):
        D.require_ladder("b", "x")
    RD.ladder_path().write_text(json.dumps(dict(lad, proofs={"p": {"held": 0, "of": 1}})))
    with pytest.raises(SystemExit, match="did not hold"):
        D.require_ladder("b", "x")


# --- numpy: the trace on a made-up part, J0's dry run, the figures ----------------------------------------------------------

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


def _world(seconds=6.5, count=8, amp=False):
    """A made-up part: isolated notes, one chord, a DI with a mute and an uneven level per group."""
    np = _needs()
    SR = NR.SR
    step = (seconds - 1.0) / count
    notes = [{"on": 0.4 + step * k, "off": 0.4 + step * k + 0.6, "pitch": 52 + (k * 5) % 12, "bends": [],
              **({"amp": 0.4 + 0.1 * (k % 5)} if amp else {})} for k in range(count)]
    notes.append({"on": notes[2]["on"] + 0.01, "off": notes[2]["off"], "pitch": notes[2]["pitch"] + 7, "bends": []})
    n = int(seconds * SR)
    groups = len(NR.onset_groups(notes))
    di, _ = NR.synthesise_redo(notes, n, _bank(), 7.0, "ring-soft", mutes=[notes[3]["on"] + 0.3], tilt_db_s=-4.0,
                               group_gain_db=[(-1) ** k * 2.0 for k in range(groups)])
    di = di * (1 + 0.3 * np.random.default_rng(3).random(n))
    return notes, n, di


def _half(y):
    return 0.5 * y


@pytest.mark.parametrize("loud", [None, 1.0])
def test_the_traced_guitar_is_byte_identical_and_the_trace_is_the_synthesis(loud):
    np = _needs()
    notes, n, di = _world(amp=loud is not None)
    T, _ = RD.derive(notes, n, _bank(), di, "ring-soft", loud)
    for finish in (None, _half):
        y, tr = D.traced_compose(notes, n, _bank(), "ring-soft", finish, T, loud)
        want, _ = RD.compose(notes, n, _bank(), "ring-soft", finish, T, loud)
        assert tr["identical"] and y.tobytes() == want.tobytes() and S.npy_sha(y) == S.npy_sha(want)
        _, rep = NR.synthesise_redo(notes, n + int(round(NR.END_PAD_S * NR.SR)), _bank(), T["tuning"], "ring-soft",
                                    T["mutes"], T["tilt"], T["levels"])
        m = tr["notes"]
        assert len(m) == rep["played"] and tr["note_end_calls"] == 2 * tr["bank_calls"] == 2 * len(m)
        kinds = {}
        for k, t in m.items():
            kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
            assert NR.nominal_midi(t["string"], t["fret"]) - notes[k]["pitch"] in range(-2, 3)
            assert t["end"] > notes[k]["on"]
        assert kinds == rep["ends"] and "mute" in kinds
    assert NR.note_end.__name__ == "note_end"


def test_the_trace_on_a_fresh_bank_is_byte_identical():
    np = _needs()
    notes, n, di = _world()
    T, _ = RD.derive(notes, n, _bank(), di, "ring-soft")
    want, _ = RD.compose(notes, n, _bank(), "ring-soft", _half, T)
    fresh = NR.Bank(None, loader=_bank().loader)
    with D.traced(fresh) as (proxy, ends):
        y, _ = RD.compose(notes, n, proxy, "ring-soft", _half, T)
    assert y.tobytes() == want.tobytes() and len(ends) == 2 * len(proxy.calls) and np.isfinite(y).all()


def _window(np, quiet_a=False, burst_a=False, seed=1):
    """A 10-s trimmed window of noise; half A nearly silent, or silent but for one short burst."""
    SR = NR.SR
    rng = np.random.default_rng(seed)
    x = 0.1 * rng.standard_normal(int(10.0 * SR))
    if quiet_a or burst_a:
        x[int(0.5 * SR):int(5.4 * SR)] *= 1e-4
    if quiet_a:
        x[2 * SR:2 * SR + 3 * SR // 10] = 0.1 * rng.standard_normal(3 * SR // 10)
    if burst_a:
        x[int(3.0 * SR):int(3.0 * SR) + 240] = 0.1
    return x


def test_j0_dry_run_matches_the_pause_share_and_aligned_distances_refusal():
    np = _needs()
    from analysis import aligned as A

    from learn import knob_ceiling as K
    from learn import note_transcribe as NT

    for x in (_window(np), _window(np, quiet_a=True), _window(np, burst_a=True)):
        rec = 0.1 * np.random.default_rng(7).standard_normal(len(x))
        tab = D.j0_table(x)
        for h, (a, b) in K.R.HALVES.items():
            for nf in A.FRAME_SIZES:
                assert tab[h][str(nf)]["pauses"] == pytest.approx(NT.judge_pause_share(x, 0, h, nf), abs=1e-12)
            first = next((tab[h][str(nf)]["refused"] for nf in A.FRAME_SIZES if tab[h][str(nf)]["refused"]), None)
            got = A.aligned_distance(rec, rec, x, lag=0, render_latency=K.P.LATENCY, start_s=a, end_s=b)
            assert got.reason == first
    assert D.j0_table(_window(np, quiet_a=True))["A"]["2048"]["refused"].endswith("pauses, over 50%")
    assert D.j0_dry_run(np.zeros(1000), 0, "A", 2048)["refused"] == "the DI is silent"


def test_the_guitar_figures():
    np = _needs()
    notes, n, di = _world(seconds=11.0, count=13)
    T, _ = RD.derive(notes, n, _bank(), di, "ring-soft")
    X = np.asarray(np.asarray(RD.compose(notes, n, _bank(), "ring-soft", None, T)[0], np.float32), np.float64)
    trim = SE._trim()
    same = D.guitar_figures(X, X, notes, trim)
    assert same["identical_to_x"] and same["env_corr"] == pytest.approx(1.0) and same["logmel"] == pytest.approx(0)
    assert same["tail_decay"]["groups"] >= 3 and same["tail_decay"]["diff_median_db"] == pytest.approx(0)
    for h in ("A", "B"):
        v = same["halves"][h]
        assert v["level_diff_db"] == pytest.approx(0) and v["logmel"] == pytest.approx(0)
        assert all(b == pytest.approx(0, abs=1e-9) for b in v["bands_db"].values())
    y = X.copy()
    y[trim[0] + int(5.5 * NR.SR):] *= 0.5                           # half B 6 dB down
    fig = D.guitar_figures(X, y, notes, trim)
    assert fig["halves"]["B"]["level_diff_db"] == pytest.approx(-6.02, abs=0.01)
    assert fig["halves"]["A"]["level_diff_db"] == pytest.approx(0, abs=1e-9) and not fig["identical_to_x"]
    assert fig["halves"]["B"]["levels_diff_db"]["50"] == pytest.approx(-6.02, abs=0.05)
    short = D.guitar_figures(X[:int(6 * NR.SR)], X[:int(6 * NR.SR)], notes, trim)
    assert short["halves"]["B"]["logmel"] is None                     # under a second of half B: not read


def test_note_table_reads_the_trace_and_the_levels():
    np = _needs()
    notes, n, di = _world()
    T, _ = RD.derive(notes, n, _bank(), di, "ring-soft")
    y, tr = D.traced_compose(notes, n, _bank(), "ring-soft", None, T)
    tab = D.note_table(notes, tr["notes"], T, np.asarray(y, np.float64))
    assert len(tab) == len(notes) and sum(r["played"] for r in tab) == len(tr["notes"])
    gi = {k: g for g, grp in enumerate(NR.onset_groups(notes)) for k in grp}
    for k, r in enumerate(tab):
        assert r["group"] == gi[k] and r["group_level_db"] == pytest.approx(T["levels"][gi[k]])
        assert r["early_db"] is not None and (r["late_db"] is None) == ((notes[k]["on"] + 0.5) * NR.SR > n)
    same = D.note_compare(tab, tab)
    assert same["source_changed"] == 0 and same["kind_changed"] == 0 and same["decay_median_db"] == 0.0


def test_one_part_diagnosis_on_a_made_up_part(monkeypatch, tmp_path):
    """`part_diagnosis` with X, xn-list and xf-now composed from stored values: every trace byte-identical and equal
    to its stored hash; X against itself reads no difference; a wrong stored hash fails the part."""
    np = _needs()
    monkeypatch.setattr(RD, "rederive_dir", lambda: tmp_path)
    notes, n, di = _world(seconds=11.0, count=13)
    bank = _bank()
    T, _ = RD.derive(notes, n, bank, di, "ring-soft")
    X32 = np.asarray(RD.compose(notes, n, bank, "ring-soft", _half, T)[0], np.float32)
    RF, _ = RD.derive(notes, n, bank, np.asarray(X32, np.float64), "ring-soft")
    RM, _ = RD.derive(notes, n, bank, 3.0 * RD.unfinished(notes, n, bank, "ring-soft", T), "ring-soft")
    lrec = {"T": RD.values_json(T), "inputs": {"in-F": {"R": RD.values_json(RF)}, "in-M": {"R": RD.values_json(RM)}}}
    RD.part_path("bks__k1").parent.mkdir(parents=True)
    RD.part_path("bks__k1").write_text(json.dumps(lrec))
    want = {"x": S.npy_sha(X32), "xn-list": S.npy_sha(RD.compose(notes, n, bank, "ring-soft", _half, RF)[0]),
            "xf-now": S.npy_sha(RD.compose(notes, n, bank, "ring-soft", _half, RM)[0])}
    rec, ok = D.part_diagnosis("bks__k1", {"set": "bks"}, lrec, X32, notes, n, bank, "ring-soft", _half, None, want)
    assert ok and all(p["identical"] and p["stored_sha256_equal"] for p in rec["proofs"].values())
    assert rec["ladder_record_sha256"] == S.file_sha(RD.part_path("bks__k1"))
    assert rec["guitars"]["x"]["sha256"] == want["x"] and set(rec["errors"]) == set(D.DIAG_ROWS)
    for g in D.DIAG_ROWS:
        f = D.tracker_figures(rec, g)
        assert set(f) >= {"one_minus_env_corr", "logmel_to_x", "mute_changes_per_group", "j0_dry_refusals"}
        assert set(rec["guitars"][g]["j0"]) == {"A", "B"} and rec["guitars"][g]["notes"]["notes"] == len(notes)
    json.dumps(rec)                                                   # the record is JSON as it stands
    rec2, ok2 = D.part_diagnosis("bks__k1", {"set": "bks"}, lrec, X32, notes, n, bank, "ring-soft", _half, None,
                                 dict(want, **{"xf-now": "0" * 64}))
    assert not ok2 and not rec2["proofs"]["xf-now"]["stored_sha256_equal"] and rec2["proofs"]["xf-now"]["identical"]


def _ladder_rec(today, chain, now):
    """A made-up ladder part record: per form its today's-rule sha256 and its chain cells' sha256; `identical_to_now`
    as the merged ladder writes it (against in-M's xf-now in every form)."""
    return {"inputs": {u: {"value": {RD.TODAY: {"sha256": today[u]}},
                           "chain": {e: {"sha256": chain[u][e], "identical_to_now": chain[u][e] == now}
                                     for e in RD.CHAIN_CELLS}} for u in RD.INPUTS}}


def test_changed_parts_compare_each_form_with_its_own_todays_rule():
    recs = {}
    for i in range(3):
        today = {u: f"{u}-today-{i}" for u in RD.INPUTS}
        now = today["in-M"]
        chain = {u: {e: today[u] for e in RD.CHAIN_CELLS} for u in RD.INPUTS}   # no rung changes the guitar ...
        chain["in-F"]["tilt"] = f"in-F-tilt-{i}"                              # ... but tilt in in-F on every part
        if i == 0:
            chain["in-M"]["mutes"] = "in-M-mutes-0"                          # and mutes in in-M on one part
            chain["in-U"]["levels"] = "in-U-levels-0"
        recs[f"bks__k{i}"] = _ladder_rec(today, chain, now)
    got = D.changed_parts(recs, sorted(recs))
    f = got["forms"]
    assert f["in-F"]["tilt"] == {"changed": 3, "ladder_reported": 3, "parts": 3}
    assert f["in-F"]["tuning"]["changed"] == 0 and f["in-F"]["tuning"]["ladder_reported"] == 3   # the fault, shown
    assert f["in-U"]["levels"]["changed"] == 1 and f["in-U"]["mutes"] == {"changed": 0, "ladder_reported": 3,
                                                                           "parts": 3}
    assert {e: v["changed"] for e, v in f["in-M"].items()} == {"tuning": 0, "mutes": 1, "tilt": 0, "levels": 0}
    assert all(v["changed"] == v["ladder_reported"] for v in f["in-M"].values())      # in-M is unaffected
    assert "own today's-rule cell" in got["note"] and "not affected" in got["note"]
    assert D.changed_parts(recs, ["bks__k1"])["forms"]["in-M"]["mutes"]["changed"] == 0


def test_the_own_guard_pins_the_four_figure_modules(monkeypatch):
    calls = []

    class Done:
        def __init__(self, rc):
            self.returncode = rc
    monkeypatch.setattr(SE, "_git", lambda *a: calls.append(a[-1]) or Done(1 if a[-1] == "learn/full_space.py" else 0))
    got = D.pinned_identity()
    assert calls == list(D.OWN_FILES) and got["learn/full_space.py"] is False and sum(got.values()) == 4
    monkeypatch.setattr(RD, "require_rederive", lambda *a: {})
    with pytest.raises(SystemExit, match="full_space.py.*differ from main's"):
        D.require_diag()


def test_only_the_missing_module_reads_merge_unit_4(monkeypatch, tmp_path):
    """A missing rederive_rows refuses with the absent message; an error inside an existing one raises as it is."""
    import importlib.util
    import sys
    import types

    monkeypatch.setitem(sys.modules, "learn.rederive_rows", None)            # absent: find_spec gives None
    with pytest.raises(SystemExit, match="^absent$"):
        D.rows_answers_path("xf-now", "absent")
    real_find = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec",
                        lambda name, *a: object() if name == "learn.rederive_rows" else real_find(name, *a))
    broken = types.ModuleType("learn.rederive_rows")

    def answers_path(row):
        raise AttributeError("a real fault inside Unit 4")
    broken.answers_path = answers_path
    monkeypatch.setitem(sys.modules, "learn.rederive_rows", broken)
    with pytest.raises(AttributeError, match="a real fault inside Unit 4"):
        D.rows_answers_path("xf-now", "absent")
    monkeypatch.setitem(sys.modules, "learn.rederive_rows", types.ModuleType("learn.rederive_rows"))
    with pytest.raises(SystemExit, match="no answers_path"):
        D.rows_answers_path("xf-now", "absent")
    ok = types.ModuleType("learn.rederive_rows")
    ok.answers_path = lambda row: tmp_path / f"answers-{row}.json"
    monkeypatch.setitem(sys.modules, "learn.rederive_rows", ok)
    assert D.rows_answers_path("fs-refit", "absent") == tmp_path / "answers-fs-refit.json"


def test_an_import_error_inside_rederive_rows_is_not_hidden(monkeypatch, tmp_path):
    """The module exists but fails on import: its own error raises, not the merge-Unit-4 refusal."""
    import importlib
    import importlib.util

    real_find, real_import = importlib.util.find_spec, importlib.import_module
    monkeypatch.setattr(importlib.util, "find_spec",
                        lambda name, *a: object() if name == "learn.rederive_rows" else real_find(name, *a))

    def imp(name, *a):
        if name == "learn.rederive_rows":
            raise ImportError("numpy missing inside Unit 4")
        return real_import(name, *a)
    monkeypatch.setattr(importlib, "import_module", imp)
    with pytest.raises(ImportError, match="inside Unit 4"):
        D.rows_answers_path("fs-refit", "absent")
