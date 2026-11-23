"""The from-scratch search's `fs-codec` row, the codec ceiling (`learn/scratch_codec.py`, `docs/scratch-search-plan.md`
section 12): `FK_TABLE` and `fk_code` (every case ends in exactly one code; FK-above and FK-shut never both hold; "by a
heard size" only at -0.10; "not ruled out", never "licensed"), `park_code`, `park_lifts`, `covers`, the short answers'
refusals (another dry guitar, a count other than 50, a checkpoint other than "50", a refused part) and the refusal stop,
the full row's first-50 check, and every command's refusals (off main, without the declarations, without the build's
hash, without the passed checks, the `-full` commands without an FK-shut). A budget of 50 asks for exactly the first 50
settings of 200 on all 3 amps. Pure: runs on the light CI runner (no numpy). With numpy: the start read renders
`scratch_notes.first_evaluation`, the search path refuses a wrong dry guitar before any render, `score_row_part`
renders exactly Cen and cp50 for a short answer. With the stored data (skipped elsewhere): the read path on rows (b) and
(c) reproduces +0.141 [+0.102, +0.180] and +0.157 [+0.108, +0.206] at cp50, the final answers' +0.167 and the
compression of +0.026; the figures reproduce avg+mild's anchors; the input keeps `section_audio`'s samples exactly."""
import itertools
import json
import math
import pathlib

import pytest

from learn import note_transcribe as T
from learn import scratch_codec as SC
from learn import scratch_notes as SN
from learn import scratch_search as S

REPO = pathlib.Path(__file__).resolve().parents[1]


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


# --- the table ---------------------------------------------------------------------------------------------------------------

def test_fk_table_guard_and_its_words():
    SC.fk_table_guard()
    assert SC.FK_CODES == ("FK-clear", "FK-above", "FK-shut", "FK-undecided")
    text = {c: " ".join(r) for c, *r in SC.FK_TABLE}
    assert all("licens" not in t.lower() for t in text.values())
    assert "not ruled out" in text["FK-clear"] and "not ruled out" in text["FK-above"]
    assert {c: o for c, *_, o in SC.FK_TABLE} == {"FK-clear": "D_true", "FK-above": "D_blur", "FK-shut": "D_blur",
                                                   "FK-undecided": "D_true and D_blur"}
    assert "full row" in text["FK-shut"] and "parked, not closed" in text["FK-shut"]
    assert "undecided is not failed" in text["FK-undecided"]


def _reference(dt, db):
    """FK_TABLE as mutually exclusive predicates, written apart from `fk_code`'s order of evaluation."""
    clear = dt["hi90"] < 0.10 and dt["mean"] < 0.05
    above = not clear and db["hi90"] < 0 and db["mean"] <= -0.05
    shut = not clear and not above and db["lo90"] >= -0.05
    undecided = not (clear or above or shut)
    hits = [c for c, h in zip(SC.FK_CODES, (clear, above, shut, undecided)) if h]
    assert len(hits) == 1
    return hits[0]


IVS = [_iv(m, lo, hi) for m, lo, hi in itertools.product((-0.2, -0.12, -0.1, -0.07, -0.05, -0.02, 0.0, 0.03, 0.05, 0.08,
                                                          0.12), (-0.08, -0.04, -0.005), (0.02, 0.06, 0.1))]
IVS = [_iv(i["mean"], i["mean"] + i["lo90"], i["mean"] + i["hi90"]) for i in IVS]


def test_fk_code_every_case_ends_in_exactly_one_code():
    seen = set()
    for dt, db in itertools.product(IVS, IVS):
        got = SC.fk_code(dt, db)
        assert got["code"] == _reference(dt, db)
        assert got["compression"] == SC.COMPRESSION_NOTE
        assert ("caveat" in got) == (got["code"] in ("FK-above", "FK-shut"))
        seen.add(got["code"])
    assert seen == set(SC.FK_CODES)


def test_fk_above_and_fk_shut_never_both_hold():
    for db in IVS:
        h = SC.fk_holds(_iv(0.2, 0.1, 0.3), db)
        assert not (h["FK-above"] and h["FK-shut"])


def test_the_codes_boundaries():
    far = _iv(0.2, 0.15, 0.25)
    assert SC.fk_code(_iv(0.049, -0.02, 0.099), far)["code"] == "FK-clear"
    assert SC.fk_code(_iv(0.05, -0.02, 0.09), far)["code"] != "FK-clear"          # the mean must be under +0.05
    assert SC.fk_code(_iv(0.04, -0.02, 0.10), far)["code"] != "FK-clear"          # the upper end under +0.10
    above = SC.fk_code(far, _iv(-0.05, -0.09, -0.01))
    assert above["code"] == "FK-above" and not above["heard"] and "not by a heard size" in above["reading"]
    heard = SC.fk_code(far, _iv(-0.10, -0.15, -0.05))
    assert heard["code"] == "FK-above" and heard["heard"] and "not by a heard size" not in heard["reading"]
    assert SC.fk_code(far, _iv(-0.06, -0.09, 0.0))["code"] == "FK-undecided"     # the interval must be below zero
    assert SC.fk_code(far, _iv(-0.02, -0.05, 0.01))["code"] == "FK-shut"
    assert SC.fk_code(far, _iv(-0.03, -0.051, 0.01))["code"] == "FK-undecided"
    assert SC.MEASURE_CAVEAT in SC.fk_code(far, _iv(-0.02, -0.05, 0.01))["caveat"]
    for bad in (None, {"mean": 0.0}, _iv(float("nan"), 0, 1)):
        with pytest.raises(SystemExit):
            SC.fk_code(bad, far)


def test_park_code():
    assert SC.park_code({"G": "FK-shut", "G_shrunk": "FK-shut"})["park"]
    got = SC.park_code({"G": "FK-shut", "G_shrunk": "FK-clear"})
    assert got == dict(got, code="FK-clear", arm="G_shrunk", park=False) and "full row" in got["reading"]
    assert SC.park_code({"G": "FK-undecided", "G_shrunk": "FK-above"})["code"] == "FK-above"
    assert SC.park_code({"G": "FK-shut", "G_shrunk": "FK-undecided"})["code"] == "FK-undecided"
    with pytest.raises(SystemExit):
        SC.park_code({"G": "F-both"})


def test_park_lifts_and_best_arm():
    notes = {"a": 0.0, "b": 0.1, "c": None}
    codec = {"a": -0.05, "b": 0.05, "c": 0.0, "d": 0.0}
    got = SC.park_lifts(notes, codec)
    assert got["lifts"] and got["mean"] == pytest.approx(0.05) and got["parts"] == 2
    assert not SC.park_lifts({"a": 0.0}, {"a": -0.049})["lifts"]
    assert SC.park_lifts(notes, codec, summarise=lambda d: {"mean": 0.01})["lifts"] is False
    assert SC.park_lifts({}, codec) == {"lifts": False, "mean": None, "row": None, "parts": 0}
    assert SC.best_arm({"answer": -0.1, "shrunk": -0.2}) == "shrunk" and SC.best_arm({"answer": None}) is None


def test_covers():
    m = SC.covers("rt-m2l")
    assert "LOUDAR as released" in m["covers"] and "GuitarFlow as published" in m["does_not_cover"]
    assert "44.1 kHz" in m["does_not_cover"] and "LOUDAR download" in m["park_means"]
    d = SC.covers("rt-dac")
    assert "track 3" in d["covers"] and "fewer codebooks" in d["does_not_cover"]
    with pytest.raises(SystemExit):
        SC.covers("rt-id")


# --- the short answers ---------------------------------------------------------------------------------------------------------

def _rec(dry="D", n=50, used=50, cps=("50", "100", "200")):
    return {"select": "0", "dry_sha256": dry, "budget": 200, "budget_used": used, "step1_only": True,
            "step1": {"evaluations": n, "curve": [1.0] * n,
                      "checkpoints": {c: {"index": 3, "value": 0.9, "settings": {"amp/gain": "0.5"}} for c in cps}}}


def test_short_answer_and_its_refusals():
    a, why = SC.short_answer(_rec(), "D")
    assert why is None and a == {"select": "0", "cp50": {"amp/gain": "0.5"}, "borrowed": []}
    assert "dry" in SC.short_answer(_rec(dry="TRUE-DI"), "D")[1]
    assert "evaluations" in SC.short_answer(_rec(n=49), "D")[1]
    assert "evaluations" in SC.short_answer(_rec(n=200), "D")[1]
    assert "budget" in SC.short_answer(_rec(used=200), "D")[1]
    assert "checkpoint" in SC.short_answer(_rec(cps=("100", "200")), "D")[1]
    assert "search" in SC.short_answer({"refused": {"start": 1}}, "D")[1]
    for cp in ("100", "200"):                  # equal to "50" in a short record, refused as answers
        with pytest.raises(SystemExit, match="checkpoint '50' only"):
            SC.short_answer(_rec(), "D", checkpoint=cp)


def test_short_answers_stop_at_three():
    parts = [{"pkey": k} for k in "abcde"]
    recs = {k: _rec() for k in "abcde"}
    shas = {k: "D" for k in "abcde"}
    got, refused, stop = SC.short_answers(parts, recs, shas, lambda k: "s" + k)
    assert set(got) == set("abcde") and not refused and not stop and got["a"]["search_sha256"] == "sa"
    recs["a"], recs["b"] = _rec(n=10), {"refused": {"start": 1}}
    assert not SC.short_answers(parts, recs, shas, str)[2]
    shas["c"] = "OTHER"
    got, refused, stop = SC.short_answers(parts, recs, shas, str)
    assert stop and set(refused) == {"a", "b", "c"} and set(got) == {"d", "e"}


def test_the_full_rows_first_fifty_must_be_the_short_rows():
    short = {"a": {"step1": {"curve": [1.0 - i / 100 for i in range(50)]}}, "b": {"refused": {"start": 1}}}
    full = {"a": {"step1": {"curve": short["a"]["step1"]["curve"] + [0.4] * 150}}, "b": {"refused": {"start": 1}}}
    assert SC.first_fifty_refusal(full, short) is None
    assert "one row only" in SC.first_fifty_refusal({"a": full["a"], "b": {"step1": {"curve": []}}}, short)
    assert "not in both" in SC.first_fifty_refusal({"a": full["a"]}, short)
    full["a"]["step1"]["curve"][7] += 1e-9
    assert "first 50" in SC.first_fifty_refusal(full, short)


def test_g50_reads_a_nonfinite_cp50_as_cen():
    assert SC.g50({"cen": 2.0, "cp50": 1.0}) == (pytest.approx(math.log(0.5)), [])
    assert SC.g50({"cen": 2.0, "cp50": math.inf}) == (0.0, ["cp50"])
    assert SC.g50({"cen": 2.0, "cp50": None}) == (0.0, ["cp50"])


def test_the_pool_rule_on_all_three_numbers():
    ok = {"deciding_sets": ["bks", "goat", "panel"]}
    assert SC.deciding_refusal({"G50": ok, "D_true": ok, "D_blur": ok}) is None
    assert "D_blur" in SC.deciding_refusal({"G50": ok, "D_true": ok, "D_blur": {"deciding_sets": ["bks", "goat"]}})
    assert "G50" in SC.deciding_refusal({"G50": None, "D_true": ok, "D_blur": ok})


def test_the_musdb_train_part_is_the_big_troubles_panel_part():
    parts = [{"pkey": "p1", "set": "panel", "cluster": "panel|panel/Big Troubles/x"},
             {"pkey": "p2", "set": "panel", "cluster": "panel|panel/Aimee Norwich/y"},
             {"pkey": "p3", "set": "panel", "cluster": "panel|panel/The Laminar Flow/z"},
             {"pkey": "b1", "set": "bks", "cluster": "bks|set/Big Troubles"}]
    assert SC.musdb_train_keys(parts) == ["p1"]


def test_the_full_row_needs_a_short_fk_shut():
    assert "no short report" in SC.report_refusal(None, "rt-m2l", "A")
    rep = {"answers_sha256": "A", "fk": {"code": "FK-shut"}}
    assert SC.report_refusal(rep, "rt-m2l", "A") is None
    assert "other answers" in SC.report_refusal(rep, "rt-m2l", "B")
    for code in ("FK-clear", "FK-above", "FK-undecided", None):
        assert "not FK-shut" in SC.report_refusal(dict(rep, fk={"code": code}), "rt-m2l", "A")
    assert "not FK-shut" in SC.report_refusal(dict(rep, fk=None), "rt-m2l", "A")


def test_the_guards_pure_parts():
    assert SC.keys_refusal({"phase_scratch_codec": 1, "phase_fs": 2}, {"phase_scratch_codec": 1}) is None
    assert "phase_scratch_codec_dry" in SC.keys_refusal({"phase_scratch_codec_dry": 1}, {})
    assert SC.blob_refusal(SC.SCRATCH_SEARCH_BLOB) is None
    assert "an amendment first" in SC.blob_refusal("0" * 40)
    good = {k: {"passed": True} for k in SC.CHECK_SHA256}
    assert SC.check_refusal(good, dict(SC.CHECK_SHA256)) is None
    assert "has not run" in SC.check_refusal({"check-score": None, "check-search": {"passed": True}}, {})
    assert "not the one declared" in SC.check_refusal(good, dict(SC.CHECK_SHA256, **{"check-search": "x"}))
    assert SC.timing_stop({"rt-m2l": {"a": 0.0, "b": 2.0, "c": -1.0}}) == ({"rt-m2l": ["b"]}, False)
    assert SC.timing_stop({"rt-dac": {"a": 1.5, "b": 2.0, "c": None}})[1]


def test_the_phases_are_new_and_outside_the_other_rows_guards():
    keys = [SC.PHASE, SC.PHASE_DRY, SC.PHASE_OUTCOME] + [SC.phase_answers(n, f) for n in SC.SEARCHED
                                                         for f in (False, True)]
    assert keys == ["phase_scratch_codec", "phase_scratch_codec_dry", "phase_scratch_codec_outcome",
                    "phase_scratch_codec_answers_m2l", "phase_scratch_codec_answers_m2l_full",
                    "phase_scratch_codec_answers_dac", "phase_scratch_codec_answers_dac_full"]
    for k in keys:
        assert not k.startswith(tuple(p for ps in T.KEY_PREFIXES.values() for p in ps))
        assert not k.startswith(("phase_fs", "phase_scratch_notes", "phase_scratch_tone"))
    with pytest.raises(SystemExit):
        SC.phase_answers("rt-id")
    d = json.loads((REPO / "docs/dev-test-ledger.json").read_text())
    e = next(t for t in d["tests"] if t.get("test_id") == S.LEDGER_ID)
    assert set(SC.codec_keys(e)) <= set(keys)
    assert SC.PHASE in e                                                        # declared


def test_the_rows_paths_stay_under_codec():
    for p in (SC.in_json(), SC.rt_path("rt-m2l", "x"), SC.start_path("rt-id", "x"), SC.search_path("rt-dac", "x"),
              SC.search_path("rt-dac", "x", True), SC.answers_path("rt-m2l"), SC.score_path("rt-m2l", "x", True),
              SC.report_path("rt-dac", True), SC.build_path(), SC.check_dir()):
        assert p.relative_to(S.fs_dir() / "codec") and "fs-both" not in str(p) and "fs-stem" not in str(p)
    assert SC.answers_path("rt-m2l") != SC.answers_path("rt-m2l", True)


def test_a_budget_of_50_requests_the_first_50_settings_of_200():
    """`coord_search` uses its budget only as a cap: at 50 it asks for exactly the first 50 settings it asks for at
    200 (C2's call, a deterministic objective), on all 3 amps."""
    from learn import full_controls as F
    from learn import knob_ceiling as K

    for amp in S.AMPS:
        start = F.c1a_start({}, amp)
        dims = F.c1a_space(amp, start)
        seqs = {}
        for budget in (SC.BUDGET, S.BUDGET):
            seq = []

            def f(x):
                seq.append(K.key(x))
                return 1.0 + (int(K.key(x), 16) % 10007) / 10007
            K.coord_search(dims, start, f, budget, F.SEED, cats="levels", canon=F.make_canon(amp))
            seqs[budget] = seq
        assert len(seqs[SC.BUDGET]) == SC.BUDGET == 50
        assert seqs[SC.BUDGET] == seqs[S.BUDGET][:SC.BUDGET]


# --- every command's refusals ---------------------------------------------------------------------------------------------------

def _args(name="rt-m2l"):
    return type("A", (), {"name": name, "shard": (0, 1), "first": 0})()


BASE = {S.PHASE: "d", S.PHASE_DRAW: {"sha256": "x"}, SC.GATE: "F-both"}
ALL = dict(BASE, **{SC.PHASE: "d", SC.PHASE_DRY: {"sha256": "b"}},
           **{SC.phase_answers(n, f): {"sha256": "a"} for n in SC.SEARCHED for f in (False, True)})


def _main(monkeypatch, main, checks=True):
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    monkeypatch.setattr(SC, "code_refusal", lambda m: None)
    monkeypatch.setattr(SN, "check_result", lambda kind: {"passed": checks, "mismatches": [] if checks else [1]})
    monkeypatch.setattr(SC, "check_shas", lambda: dict(SC.CHECK_SHA256))


@pytest.mark.parametrize("cmd", sorted(SC.COMMANDS))
def test_every_command_refuses_off_main(monkeypatch, cmd):
    monkeypatch.setattr(S, "on_main", lambda: (None, "this checkout's learn/scratch_search.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        SC.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", sorted(SC.COMMANDS))
def test_every_command_refuses_off_mains_codec_code(monkeypatch, cmd):
    monkeypatch.setattr(S, "on_main", lambda: (dict(ALL), None))
    monkeypatch.setattr(SC, "code_refusal", lambda m: "this checkout's learn/scratch_codec.py differs from main's")
    with pytest.raises(SystemExit, match="scratch_codec.py differs"):
        SC.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", sorted(SC.COMMANDS))
def test_every_command_refuses_without_the_declarations(monkeypatch, cmd):
    _main(monkeypatch, dict(BASE))
    with pytest.raises(SystemExit, match="has no phase_scratch_codec"):
        SC.COMMANDS[cmd](_args())
    _main(monkeypatch, {S.PHASE: "d", S.PHASE_DRAW: {}, SC.PHASE: "d"})
    with pytest.raises(SystemExit, match="phase_scratch_both_outcome"):
        SC.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", sorted(SC.COMMANDS))
def test_every_command_refuses_without_the_passed_checks(monkeypatch, cmd):
    _main(monkeypatch, dict(ALL), checks=False)
    with pytest.raises(SystemExit, match="did not pass"):
        SC.COMMANDS[cmd](_args())
    _main(monkeypatch, dict(ALL))
    monkeypatch.setattr(SC, "check_shas", lambda: {"check-score": "x", "check-search": None})
    with pytest.raises(SystemExit, match="not the one declared"):
        SC.COMMANDS[cmd](_args())


RENDER_AND_LATER = ("start", "control", "search", "answers", "score", "read", "search-full", "answers-full",
                    "score-full", "read-full")


@pytest.mark.parametrize("cmd", RENDER_AND_LATER)
def test_every_later_command_refuses_without_the_builds_hash(monkeypatch, tmp_path, cmd):
    _main(monkeypatch, dict(BASE, **{SC.PHASE: "d"}))
    with pytest.raises(SystemExit, match="phase_scratch_codec_dry"):
        SC.COMMANDS[cmd](_args())
    (tmp_path / "build.json").write_text("{}")
    monkeypatch.setattr(SC, "build_path", lambda: tmp_path / "build.json")
    main = dict(BASE, **{SC.PHASE: "d", SC.PHASE_DRY: {"sha256": "0" * 64}})
    for name in SC.SEARCHED:
        main[SC.phase_answers(name)] = {"sha256": "a"}
        main[SC.phase_answers(name, True)] = {"sha256": "a"}
    _main(monkeypatch, main)
    with pytest.raises(SystemExit, match="phase_scratch_codec_dry"):
        SC.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", ("score", "read", "score-full", "read-full"))
def test_score_and_read_wait_for_the_answers_hash(monkeypatch, cmd):
    _main(monkeypatch, dict(BASE, **{SC.PHASE: "d", SC.PHASE_DRY: {"sha256": "b"}}))
    with pytest.raises(SystemExit, match="phase_scratch_codec_answers_m2l"):
        SC.COMMANDS[cmd](_args())


def _built(monkeypatch, tmp_path, reports=None):
    (tmp_path / "build.json").write_text(json.dumps({"names": {"rt-m2l": {}, "rt-id": {}}, "dropped": ["rt-dac"]}))
    monkeypatch.setattr(SC, "build_path", lambda: tmp_path / "build.json")
    main = dict(BASE, **{SC.PHASE: "d", SC.PHASE_DRY: {"sha256": S.file_sha(tmp_path / "build.json")}})
    for name in SC.SEARCHED:
        main[SC.phase_answers(name)] = {"sha256": "A"}
        main[SC.phase_answers(name, True)] = {"sha256": "F"}
    _main(monkeypatch, main)
    monkeypatch.setattr(SC, "report_path", lambda name, full=False: tmp_path / f"report-{name}{full}.json")
    for name, rep in (reports or {}).items():
        (tmp_path / f"report-{name}False.json").write_text(json.dumps(rep))
    return main


@pytest.mark.parametrize("cmd", ("search-full", "answers-full", "score-full", "read-full"))
def test_the_full_commands_refuse_without_an_fk_shut(monkeypatch, tmp_path, cmd):
    _built(monkeypatch, tmp_path)
    with pytest.raises(SystemExit, match="no short report"):
        SC.COMMANDS[cmd](_args())
    _built(monkeypatch, tmp_path, {"rt-m2l": {"answers_sha256": "A", "fk": {"code": "FK-undecided"}}})
    with pytest.raises(SystemExit, match="not FK-shut"):
        SC.COMMANDS[cmd](_args())
    _built(monkeypatch, tmp_path, {"rt-m2l": {"answers_sha256": "OTHER", "fk": {"code": "FK-shut"}}})
    with pytest.raises(SystemExit, match="other answers"):
        SC.COMMANDS[cmd](_args())


def test_a_dropped_or_unsearched_name_is_refused(monkeypatch, tmp_path):
    _built(monkeypatch, tmp_path)
    with pytest.raises(SystemExit, match="not in the build"):
        SC.cmd_search(_args("rt-dac"))
    with pytest.raises(SystemExit, match="one of"):
        SC.cmd_search(_args("rt-m2l-b"))
    with pytest.raises(SystemExit, match="one of"):
        SC.cmd_start(_args("rt-rs"))


def test_search_refuses_until_the_control_passed(monkeypatch, tmp_path):
    _built(monkeypatch, tmp_path)
    monkeypatch.setattr(SC, "check_dir", lambda: tmp_path / "check")
    with pytest.raises(SystemExit, match="the control has not run"):
        SC.cmd_search(_args())
    (tmp_path / "check").mkdir()
    (tmp_path / "check" / "result.json").write_text(json.dumps({"passed": False, "search": {"mismatches": [1]}}))
    with pytest.raises(SystemExit, match="the control did not pass"):
        SC.cmd_search(_args())


def test_the_module_edits_neither_shared_file_and_imports_no_numpy_at_its_top():
    import ast

    src = (REPO / "learn" / "scratch_codec.py").read_text()
    top = [n for n in ast.parse(src).body if isinstance(n, (ast.Import, ast.ImportFrom))]
    mods = {a.name for n in top if isinstance(n, ast.Import) for a in n.names} | \
        {n.module for n in top if isinstance(n, ast.ImportFrom)}
    assert "numpy" not in mods and "torch" not in mods
    assert "weights_only=False" not in src.replace("`weights_only=False`", "")


# --- with numpy (stubs) ---------------------------------------------------------------------------------------------------------

def _part(amp="ac20"):
    return {"pkey": "goat__x", "set": "goat", "unit": "u", "amp": amp, "lag": 0, "search": "A", "held": "B",
            "cen": {"select": "0", "settings": {}}, "start_ref": {"true": {"xlnoG": 2.0}}}


@pytest.mark.parametrize("amp", S.AMPS)
def test_the_start_read_renders_step_1s_exact_first_evaluation(monkeypatch, tmp_path, amp):
    np = pytest.importorskip("numpy")
    from learn import audibility_measure as AM
    from learn import note_replay as NR

    seen = []

    def fake(make, di, sel, xp, x):
        seen.append((xp, x))
        return np.zeros(len(di))
    monkeypatch.setattr(AM, "fresh_render", fake)
    monkeypatch.setattr(NR, "half_distance", lambda ref, y, di, lag, half: 1.0)
    p = _part(amp)
    v, used = SC.start_value(p, "rt-m2l", np.zeros(SC.SECTION, np.float32), None, None, tmp_path / "s.json", "D")
    assert (v, used) == (1.0, 2) and seen == [(SN.first_evaluation(p), SN.first_evaluation(p))]
    rec = json.loads((tmp_path / "s.json").read_text())
    assert rec["dry"] == "rt-m2l" and rec["dry_sha256"] == "D" and rec["start_read"] == pytest.approx(math.log(0.5))
    assert SC.start_value(p, "rt-m2l", None, None, None, tmp_path / "s.json", "D") == (1.0, 0)
    with pytest.raises(SystemExit, match="another dry guitar"):
        SC.start_value(p, "rt-m2l", None, None, None, tmp_path / "s.json", "E")


def test_the_search_path_refuses_a_wrong_dry_guitar_before_any_render(monkeypatch):
    np = pytest.importorskip("numpy")
    seen = {}

    def fake_run_part(*a, **k):
        seen.update(k)
        return {"renders": 51, "step1": {}}
    monkeypatch.setattr(S, "run_part", fake_run_part)
    x = np.linspace(-0.5, 0.5, 4800).astype(np.float32)
    with pytest.raises(SystemExit, match="not the declared one"):
        SC.short_search(_part(), "rt-m2l", x * 1.0001, S.npy_sha(x), None, None, None, 1.0)
    assert not seen
    rec = SC.short_search(_part(), "rt-m2l", x, S.npy_sha(x), None, None, None, 1.25)
    assert seen == {"budget": 50, "start_ref": 1.25, "dry_sha256": S.npy_sha(x), "step1_only": True}
    assert rec["budget_used"] == 50


def test_the_score_renders_exactly_cen_and_cp50_for_a_short_answer(monkeypatch):
    np = pytest.importorskip("numpy")
    from learn import audibility_measure as AM
    from learn import local_objective as LO
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    rendered = []

    def fake(make, di, sel, xp, x):
        rendered.append(x)
        return np.full(len(di), 0.1 * len(rendered))
    monkeypatch.setattr(AM, "fresh_render", fake)
    monkeypatch.setattr(NR, "di_section", lambda prt: np.zeros(SC.SECTION, np.float32))
    monkeypatch.setattr(NR, "half_distance", lambda ref, y, di, lag, half: 1.0 + float(y[0]))
    monkeypatch.setattr(P, "real_amp_track", lambda *a: np.zeros(SC.SECTION))
    sd = type("SD", (), {"units": {("goat", "u", "ac20"): {"prt": {"sd": 0, "track": 0, "start_s": 0}}},
                         "cen_judge": lambda self, k: {"A": 1.1, "B": 1.1}})()
    cen = {"amp/gain": "0.3"}
    p = dict(_part(), cen={"select": "0", "settings": cen})
    a, _ = SC.short_answer(_rec(), "D")
    rec, used = S.score_row_part(p, a, {p["pkey"]: a}, SC.ROW, "ANS", sd, None)
    assert rendered == [LO.tdict(cen), LO.tdict(a["cp50"])] and used == 4
    assert set(rec["held"]) == {"cen", "cp50"} and rec["scoring_control_ok"] and rec["borrowed"] == []
    assert SC.g50(rec["held"])[0] == pytest.approx(math.log(1.2 / 1.1))


def test_with_next_second_keeps_the_section_exactly():
    np = pytest.importorskip("numpy")
    sec = np.arange(10, dtype=np.float32)
    longer = np.arange(14, dtype=np.float32) + 0.5
    x, real = SC.with_next_second(sec, longer, n_next=6)
    assert np.array_equal(x[:10], sec) and list(x[10:]) == [10.5, 11.5, 12.5, 13.5, 0.0, 0.0] and real == 4
    x, real = SC.with_next_second(sec, sec, n_next=6)                     # the file ends with the section
    assert real == 0 and not x[10:].any() and len(x) == 16 and x.dtype == np.float32


def test_the_figures_on_known_signals():
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(3)
    x = rng.standard_normal(SC.SECTION) * 0.1
    same = SC.dry_figures(x, x)
    assert same["mel256"] == pytest.approx(0, abs=1e-9) and same["crest"] == pytest.approx(0, abs=1e-12)
    assert SC.dry_figures(x, 2 * x)["mel2048"] == pytest.approx(0, abs=1e-9)    # the level is removed
    assert SC.envelope_lag_ms(x, x) == 0.0
    y = np.concatenate([np.zeros(240), x[:-240]])                             # 5 ms late
    assert SC.envelope_lag_ms(x, y) == 5.0 and SC.waveform_lag(x, y) == 240
    assert set(SC.part_figures(x, x)) == {"whole", "A", "B"}


# --- with the stored data -------------------------------------------------------------------------------------------------------

def _stored():
    pytest.importorskip("numpy")
    from learn import note_replay as R

    need = [S.draw_path(), S.answers_path("fs-both"), S.answers_path("fs-stem"), R.draw_path()]
    if not all(p.exists() for p in need):
        pytest.skip("no stored from-scratch data")
    return R, json.loads(S.draw_path().read_text()), R.Stored()


def _rd(r):
    return tuple(round(r[k], 3) for k in ("mean", "lo90", "hi90"))


def test_the_read_path_on_rows_b_and_c_reproduces_the_checkpoints_separation():
    R, draw, sd = _stored()
    comp = {}
    for row in ("fs-stem", "fs-both"):
        ans = json.loads(S.answers_path(row).read_text())
        comp[row] = SC.comparator_g50(draw, ans, S.file_sha(S.answers_path(row)), lambda k, r=row: S.score_path(r, k))
    assert len(comp["fs-stem"][0]) == len(comp["fs-both"][0]) == 47
    d50 = SN.set_rows(sd, draw, SC.paired(comp["fs-both"][0], comp["fs-stem"][0]))
    assert _rd(d50["deciding_pool"]) == (0.141, 0.102, 0.180)
    assert _rd(d50["bks_goat"]["all"]) == (0.157, 0.108, 0.206)
    for row, want in (("fs-stem", -0.271), ("fs-both", -0.130)):
        assert round(SN.set_rows(sd, draw, comp[row][0])["deciding_pool"]["mean"], 3) == want
    da = SN.set_rows(sd, draw, SC.paired(comp["fs-both"][1], comp["fs-stem"][1]))
    assert _rd(da["deciding_pool"]) == (0.167, 0.110, 0.224)
    assert round(da["deciding_pool"]["mean"] - d50["deciding_pool"]["mean"], 3) == SC.COMPRESSION["compression"]
    rows = SC.read_short_rows(sd, draw, comp["fs-both"][0], comp)          # row (c) read as if it were a codec
    assert _rd(rows["D_true"]["deciding_pool"]) == (0.141, 0.102, 0.180)
    assert rows["D_blur"]["deciding_pool"]["mean"] == pytest.approx(0.0, abs=1e-12)
    assert SC.deciding_refusal({q: rows[q] for q in ("G50", "D_true", "D_blur")}) is None
    assert rows["beside"]["share_of_row_b_g50_kept"]["pool"] == pytest.approx(0.130 / 0.271, abs=0.01)   # 48%


def test_the_figures_reproduce_avg_milds_anchors():
    np = pytest.importorskip("numpy")
    R, draw, sd = _stored()
    blur = json.loads((R.replay_dir() / "blur.json").read_text())
    rby = {p["pkey"]: p for p in R.require_draw()["parts"]}
    got = {f: [] for f in ("mel256", "mel2048", "env5", "crest")}
    for p in draw["parts"]:
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        di32 = R.di_section(prt)
        am = np.asarray(R.load_dry("avg+mild", rby[p["pkey"]], di32, blur), np.float64)
        for f, v in SC.dry_figures(np.asarray(di32, np.float64), am).items():
            got[f].append(v)
    means = {f: round(sum(v) / len(v), 3) for f, v in got.items()}
    assert means == {"mel256": 2.486, "mel2048": 3.050, "env5": 1.995, "crest": -0.686}


def test_the_input_keeps_section_audios_samples_and_the_true_dis_offset():
    np = pytest.importorskip("numpy")
    R, draw, sd = _stored()
    from learn import confirm_run as CR
    from learn import pretrain_set as PS
    from learn import song_bank as SB

    avg = np.load(CR.AVERAGE)
    real, offs, seen = 0, [], set()
    for p in draw["parts"]:
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        sec = PS.section_audio(prt["di_path"], prt["start_s"])
        x, n = SC.with_next_second(sec, SC.longer_read(prt["di_path"], prt["start_s"]))
        assert len(x) == SC.IN_LEN and np.array_equal(x[:SC.SECTION], sec)
        real += n == SC.NEXT
        if p["set"] in ("bks", "goat") and p["section"] not in seen:
            seen.add(p["section"])
            offs.append(SC.balance_offset(SB.measure(sec), avg))
    assert real == 16                                  # the BKS files; GOAT's and the panel's end with the section
    assert round(sum(offs) / len(offs), 1) == 2.7 and round(max(offs), 1) == 7.1


def test_the_beside_readings_and_figure_summaries_run_on_the_stored_rows():
    R, draw, sd = _stored()
    comp = {}
    for row in ("fs-stem", "fs-both"):
        ans = json.loads(S.answers_path(row).read_text())
        comp[row] = SC.comparator_g50(draw, ans, S.file_sha(S.answers_path(row)), lambda k, r=row: S.score_path(r, k))
    keys = sorted(comp["fs-both"][0])
    figs = {"parts": {}}
    for i, k in enumerate(keys):
        fig = {f: 0.1 * i for f in ("mel256", "mel2048", "env5", "crest")}
        figs["parts"][k] = {"true": {"balance_offset": 1.0 + 0.01 * i},
                            "avg+mild": {"vs_true": {h: dict(fig) for h in ("whole", "A", "B")}, "balance_offset": 1.0},
                            "rt-dac": {"vs_true": {h: dict(fig, mel256=0.2 * i) for h in ("whole", "A", "B")},
                                       "before_measure": 0.5, "balance_offset": 2.0, "lag_ms": 0.0}}
    recs = {k: json.loads(S.search_path("fs-both", k).read_text()) for k in keys}
    rows = SC.read_short_rows(sd, draw, comp["fs-both"][0], comp, figs, {k: 0.1 for k in keys}, recs, "rt-dac")
    b = rows["beside"]
    assert b["without_musdb_train"]["left_out"] == SC.musdb_train_keys(draw["parts"])
    assert len(b["without_musdb_train"]["left_out"]) == 1
    assert b["without_musdb_train"]["D_blur"]["mean"] == pytest.approx(0.0, abs=1e-12)
    assert b["d_true_vs_figures_spearman"]["before_measure"] is None          # a constant figure has no rank
    assert b["start_read"]["mean"] == pytest.approx(0.1) and b["search_gain_vs_held_g50"]["pearson"] is not None
    summ = SC.figure_rows(sd, draw, figs["parts"], ["rt-dac"])
    assert summ["rt-dac"]["mel256_whole"]["less_avg_mild_pool"]["mean"] > 0
    assert summ["true"]["balance_offset"]["max"] == pytest.approx(1.0 + 0.01 * (len(keys) - 1))
