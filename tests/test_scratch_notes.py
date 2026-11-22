"""The from-scratch search's `fs-notes` row (`learn/scratch_notes.py`, `docs/scratch-search-plan.md` section 10):
`paired_reading`, FN_TABLE and `fn_code` (every case ends in exactly one code, with the absolute conditions), the lean
recommendations, the bottleneck rule, the checks' verdicts, the dry-guitar check, the refusal stop on the 40, every
refusal; and the refactor of `learn/scratch_search.py`: rows (b) and (c) resolve and refuse as before, the outcome
table is unchanged, a short budget requests the same first settings. Pure: runs on the light CI runner (no numpy). The
last tests need numpy and the stored data (skipped elsewhere): the shared read path reproduces row (c)'s rows file,
`paired` reproduces (c) less (b) on the pool, and row (c)'s bar on BKS+GOAT."""
import itertools
import json
import math
import pathlib

import pytest

from learn import note_transcribe as T
from learn import scratch_notes as SN
from learn import scratch_search as S

REPO = pathlib.Path(__file__).resolve().parents[1]


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


# --- the paired reading ------------------------------------------------------------------------------------------------------

def test_paired_reading():
    r = SN.paired_reading
    assert r(_iv(-0.12, -0.2, -0.01))["reading"] == "better"
    assert r(_iv(-0.09, -0.2, -0.01))["reading"] == "matches"               # decided, short of -0.10
    assert r(_iv(0.04, -0.03, 0.099))["reading"] == "matches"
    assert r(_iv(0.05, -0.03, 0.09))["reading"] == "undecided"              # the mean must be under +0.05
    assert r(_iv(0.04, -0.03, 0.10))["reading"] == "undecided"              # the upper end must be under +0.10
    assert r(_iv(0.10, 0.01, 0.19))["reading"] == "worse"
    assert r(_iv(0.12, -0.01, 0.25))["reading"] == "undecided"              # not clear of zero
    assert r(_iv(0.09, 0.01, 0.17))["reading"] == "undecided"
    assert r(_iv(0.0, -0.05, 0.05)) == {"reading": "matches", "level_not_readable": True}
    assert not r(_iv(0.0, -0.06, 0.05))["level_not_readable"]
    assert r(None) is None and r({"mean": 0.0}) is None


# --- FN_TABLE ----------------------------------------------------------------------------------------------------------------

READING_IV = {"better": _iv(-0.15, -0.25, -0.05), "matches": _iv(0.0, -0.06, 0.06),
              "worse": _iv(0.15, 0.05, 0.25), "undecided": _iv(0.06, -0.02, 0.14), None: None}
G_BELOW = _iv(-0.15, -0.25, -0.05)          # hi90 < 0 and number_reading "passes"
G_FAILS = _iv(0.02, -0.02, 0.06)            # number_reading "fails", hi90 >= 0
G_MID = _iv(-0.06, -0.12, 0.0)              # hi90 = 0: not below zero, number_reading "undecided"


def _arms(d, g):
    """d, g: {arm: (all, clean, crunch)} of reading names and G rows."""
    return {a: {"D": dict(zip(SN.SUBSETS, (READING_IV[x] for x in d[a]))), "G": dict(zip(SN.SUBSETS, g[a]))}
            for a in SN.ARMS}


def _reference(arms):
    """FN_TABLE written as mutually exclusive predicates, independently of `fn_code`'s order of evaluation."""
    rd = {a: {s: (SN.paired_reading(arms[a]["D"][s]) or {}).get("reading") for s in SN.SUBSETS} for a in SN.ARMS}
    ok = {"matches", "better"}

    def below(g):
        return g is not None and g["hi90"] < 0
    match = any(rd[a]["all"] in ok and rd[a]["clean"] in ok and below(arms[a]["G"]["all"])
                and S.number_reading(arms[a]["G"]["clean"]) != "fails" for a in SN.ARMS)
    crunch = not match and any(rd[a]["crunch"] in ok and below(arms[a]["G"]["crunch"]) for a in SN.ARMS)
    worse = not match and not crunch and all(rd[a]["all"] == "worse" for a in SN.ARMS)
    clean_worse = not (match or crunch or worse) and all(rd[a]["clean"] == "worse" for a in SN.ARMS)
    undecided = not (match or crunch or worse or clean_worse)
    hits = [c for c, h in zip(SN.FN_CODES, (match, crunch, worse, clean_worse, undecided)) if h]
    assert len(hits) == 1
    return hits[0]


def test_fn_table_guard():
    SN.fn_table_guard()
    assert SN.FN_CODES == ("FN-match", "FN-crunch", "FN-worse", "FN-clean-worse", "FN-undecided")


def test_fn_code_every_case_ends_in_exactly_one_code():
    readings = ("better", "matches", "worse", "undecided")
    gs = (G_BELOW, G_FAILS, G_MID)
    per_arm = list(itertools.product(itertools.product(readings, repeat=3), itertools.product(gs, repeat=3)))
    seen = set()
    for (da, ga), (db, gb) in itertools.product(per_arm[::7], per_arm[::5]):
        arms = _arms({"answer": da, "shrunk": db}, {"answer": ga, "shrunk": gb})
        got = SN.fn_code(arms)
        assert got["code"] in SN.FN_CODES and got["code"] == _reference(arms)
        assert got["licence"] == SN.FN_LICENCE[got["code"]]
        seen.add(got["code"])
    assert seen == set(SN.FN_CODES)                                          # every code is reachable


def test_fn_match_needs_the_arms_own_g():
    good = ("matches", "matches", "matches")
    arms = _arms({"answer": good, "shrunk": ("undecided",) * 3}, {"answer": (G_BELOW, G_BELOW, G_BELOW),
                                                                  "shrunk": (G_MID,) * 3})
    assert SN.fn_code(arms)["code"] == "FN-match" and SN.fn_code(arms)["arm"] == "answer"
    arms["answer"]["G"]["all"] = G_MID                                       # B2: the row does not beat Cen on the 40
    assert SN.fn_code(arms)["code"] != "FN-match"
    arms["answer"]["G"]["all"] = G_BELOW
    arms["answer"]["G"]["clean"] = G_FAILS                                   # its own G on clean reads fails
    assert SN.fn_code(arms)["code"] != "FN-match"


def test_the_same_arm_throughout_a_row():
    arms = _arms({"answer": ("matches", "undecided", "undecided"), "shrunk": ("undecided", "matches", "undecided")},
                 {"answer": (G_BELOW,) * 3, "shrunk": (G_BELOW,) * 3})
    assert SN.fn_code(arms)["code"] == "FN-undecided"                        # no single arm matches on 40 and clean


def test_fn_crunch_words_clean_from_its_reading():
    for clean, words in (("worse", "worse"), ("undecided", "undecided"),
                         ("matches", "matches, but the row does not beat Cen there")):
        arms = _arms({"answer": ("undecided", clean, "matches"), "shrunk": ("undecided",) * 3},
                     {"answer": (G_MID, G_FAILS, G_BELOW), "shrunk": (G_MID,) * 3})
        got = SN.fn_code(arms)
        assert got["code"] == "FN-crunch" and got["clean"] == words
    arms = _arms({"answer": ("undecided", "undecided", "matches"), "shrunk": ("undecided",) * 3},
                 {"answer": (G_MID, G_MID, G_MID), "shrunk": (G_MID,) * 3})
    assert SN.fn_code(arms)["code"] == "FN-undecided"                        # crunch's own G not below zero


def test_fn_worse_and_clean_worse_need_both_arms():
    arms = _arms({"answer": ("worse", "worse", "worse"), "shrunk": ("worse", "undecided", "worse")},
                 {"answer": (G_FAILS,) * 3, "shrunk": (G_FAILS,) * 3})
    assert SN.fn_code(arms)["code"] == "FN-worse"
    arms["shrunk"]["D"]["all"] = READING_IV["undecided"]
    assert SN.fn_code(arms)["code"] == "FN-undecided"
    arms["shrunk"]["D"]["clean"] = READING_IV["worse"]
    got = SN.fn_code(arms)
    assert got["code"] == "FN-clean-worse" and got["lean"][0] in ("lean-go", "lean-stop")


def test_lean_go_and_lean_stop():
    arms = _arms({"answer": ("undecided",) * 3, "shrunk": ("undecided",) * 3},
                 {"answer": (G_BELOW,) * 3, "shrunk": (G_BELOW,) * 3})
    arms["answer"]["D"]["all"] = _iv(0.04, -0.03, 0.11)                       # Q4's case: lean-go
    assert SN.fn_code(arms)["lean"] == ("lean-go", "answer")
    arms["answer"]["G"]["all"] = G_MID                                       # its own G not below zero
    arms["shrunk"]["D"]["all"] = _iv(0.06, -0.02, 0.14)
    assert SN.fn_code(arms)["lean"] == ("lean-stop", None)
    assert "never \"fails\"" in SN.FN_LICENCE["FN-undecided"] and "row (c)'s bar" in SN.FN_LICENCE["FN-undecided"]


# --- the bottleneck, the split ----------------------------------------------------------------------------------------------

def test_median_split():
    lower, upper = SN.median_split({"a": 0.9, "b": 0.5, "c": 0.7, "d": None, "e": 0.7})
    assert lower == ["b", "c"] and upper == ["e", "a"]


def test_bottleneck():
    up, low = _iv(0.12, 0.02, 0.22), _iv(0.14, 0.04, 0.24)
    assert SN.bottleneck(up, low)[0] == ["the synthesis"]
    up, low = _iv(0.02, -0.03, 0.07), _iv(0.20, 0.12, 0.28)
    names, d = SN.bottleneck(up, low)
    assert names == ["the transcriber"] and d["mean"] == pytest.approx(0.18)
    assert d["lo90"] == pytest.approx(0.18 - math.hypot(0.05, 0.08))
    assert SN.bottleneck(_iv(0.12, -0.01, 0.25), _iv(0.20, -0.1, 0.5))[0] == ["not separable by these figures"]
    assert SN.bottleneck(_iv(0.12, 0.02, 0.22), _iv(0.30, 0.25, 0.35))[0] == ["the synthesis", "the transcriber"]
    assert SN.bottleneck(None, None)[0] == ["not separable by these figures"]


# --- the checks and the guards ------------------------------------------------------------------------------------------------

def test_check_parts_are_the_first_bks_and_goat_by_key():
    parts = [{"pkey": k, "set": s} for k, s in (("goat__b", "goat"), ("bks__z", "bks"), ("bks__a", "bks"),
                                                 ("goat__a", "goat"), ("panel__a", "panel"))]
    assert SN.check_parts(parts) == ["bks__a", "goat__a"]


def test_score_check_verdict():
    rec = {"held": {"cen": 1.0, "answer": 0.8}, "render_sha256": {"cen": "a", "answer": "b"}}
    assert SN.score_check_verdict({"p": rec}, {"p": json.loads(json.dumps(rec))})["passed"]
    off = json.loads(json.dumps(rec))
    off["held"]["answer"] = 0.8000001
    assert SN.score_check_verdict({"p": off}, {"p": rec})["mismatches"] == [("p", "answer")]
    off = json.loads(json.dumps(rec))
    off["render_sha256"]["cen"] = "x"
    assert not SN.score_check_verdict({"p": off}, {"p": rec})["passed"]
    assert not SN.score_check_verdict({}, {"p": rec})["passed"]


def test_search_check_verdict():
    stored = {"step1": {"curve": [1.0, 0.9, 0.95, 0.8], "start": {"render_sha256": "s"}}}
    ok = {"step1": {"curve": [1.0, 0.9, 0.95], "start": {"render_sha256": "s"}}}
    assert SN.search_check_verdict({"p": ok}, {"p": stored})["passed"]
    bad = {"step1": {"curve": [1.0, 0.9, 0.9500001], "start": {"render_sha256": "s"}}}
    assert SN.search_check_verdict({"p": bad}, {"p": stored})["mismatches"] == [("p", "curve")]
    assert not SN.search_check_verdict({"p": {"refused": {"start": 1}}}, {"p": stored})["passed"]
    assert not SN.search_check_verdict({"p": dict(ok, step1=dict(ok["step1"], start={"render_sha256": "t"}))},
                                       {"p": stored})["passed"]


def test_answers_refuse_a_search_record_with_another_dry_guitar():
    build = {"a": {"arms": {"tr-di": {"sha256": "A"}}}, "b": {"arms": {"tr-di": {"sha256": "B"}}}}
    recs = {"a": {"dry_sha256": "A", "answer": {}}, "b": {"refused": {"content": ["ring-kept"]}}}
    assert SN.dry_refusal(recs, build, "BUILD", {"sha256": "BUILD"}) is None
    assert "phase_scratch_notes_dry" in SN.dry_refusal(recs, build, "BUILD", {"sha256": "OTHER"})
    assert "phase_scratch_notes_dry" in SN.dry_refusal(recs, build, "BUILD", None)
    recs["a"]["dry_sha256"] = "TRUE-DI"
    assert "not the hashed build's tr-di" in SN.dry_refusal(recs, build, "BUILD", {"sha256": "BUILD"})
    del recs["a"]["dry_sha256"]
    assert SN.dry_refusal(recs, build, "BUILD", {"sha256": "BUILD"})


def test_the_build_must_come_from_the_hashed_notes_and_install():
    nr = {T.PHASE_NOTES: {"sha256": "N"}, T.PHASE_INSTALL: {"lock_sha256": "L", "model_sha256": "M"}}
    build = {"transcribe_sha256": "N", "pair": ["L", "M"]}
    assert SN.redo_hash_refusal(nr, build, "N", ("L", "M")) is None
    assert "phase_nr_1_redo_notes" in SN.redo_hash_refusal(nr, build, "N2", ("L", "M"))
    assert "another transcription" in SN.redo_hash_refusal(nr, dict(build, transcribe_sha256="X"), "N", ("L", "M"))
    assert "names no install" in SN.redo_hash_refusal({T.PHASE_NOTES: {"sha256": "N"}}, build, "N", ("L", "M"))
    assert "another lock" in SN.redo_hash_refusal(nr, build, "N", ("L", "M2"))
    assert "another install" in SN.redo_hash_refusal(nr, dict(build, pair=["L", "X"]), "N", ("L", "M"))


@pytest.mark.parametrize("amp", S.AMPS)
def test_the_start_reference_renders_step_1s_exact_first_evaluation(amp):
    from learn import full_controls as F
    from learn import local_objective as LO

    p = {"amp": amp, "cen": {"settings": {}}}
    first = []

    def ev(x):
        first.append(x)
        return 1.0, -20.0, None
    S.step1_search(amp, F.c1a_start({}, amp), ev, 1.0, budget=1)
    assert LO.tdict(LO.sdict(first[0])) == SN.first_evaluation(p)


def test_the_ear_check_gates_answers_score_and_read():
    assert "not recorded" in SN.ear_refusal({})
    assert "not recorded" in SN.ear_refusal({T.PHASE_EAR: "ok"})
    for v in ("fault-content", "fault-signal", "ask", "incomplete"):
        assert v in SN.ear_refusal({T.PHASE_EAR: {"verdict": v}})
    assert SN.ear_refusal({T.PHASE_EAR: {"verdict": "ok"}}) is None
    heard = {T.PHASE_EAR: {"verdict": "ok", "dry_build_sha256": "B"}}
    assert SN.ear_refusal(heard, "B") is None
    assert "another build" in SN.ear_refusal(heard, "B2")
    assert "another build" in SN.ear_refusal({T.PHASE_EAR: {"verdict": "ok"}}, "B")


def test_the_build_stop_rule_refuses_on_any_failing_ear_item():
    assert SN.build_refusal({"stopped": False, "ear_failing": []}) is None
    assert "3 or more" in SN.build_refusal({"stopped": True, "ear_failing": []})
    assert "item_23" in SN.build_refusal({"stopped": False, "ear_failing": ["item_23"]})


def test_require_build_refuses_a_search_when_an_ear_item_fails(monkeypatch):
    build = {"stopped": False, "ear_failing": ["item_46"], "parts": {}}
    monkeypatch.setattr(T, "require_file_hash", lambda entry, phase, path: build)
    monkeypatch.setattr(T, "load_manifest", lambda: {"lock_sha256": "L", "model_sha256": "M"})
    monkeypatch.setattr(T.NR, "file_sha", lambda path: "N")
    monkeypatch.setattr(SN, "redo_hash_refusal", lambda *a: None)
    with pytest.raises(SystemExit, match="ear items fail a content check"):
        SN.require_build({})
    build["ear_failing"] = []
    assert SN.require_build({}) is build


def test_main_must_hold_the_installs_gate_and_calibration():
    rec = {"lock_sha256": "L", "model_sha256": "M", "gate_sha256": "G", "calibration_sha256": "C"}
    assert T.install_record_refusal(rec, "G", "C", ("L", "M")) is None
    assert "names no install" in T.install_record_refusal(None, "G", "C", ("L", "M"))
    assert "another lock" in T.install_record_refusal(rec, "G", "C", ("L", "X"))
    assert "install-gate.json" in T.install_record_refusal(rec, "G2", "C", ("L", "M"))
    assert "calibration.json" in T.install_record_refusal(rec, "G", "C2", ("L", "M"))


def _build_part(ring_db, bent, chord):
    return {"arms": {"tr-di": {"figures": {"ring-kept": {"late_median_db": ring_db}}}}, "bent_share": bent,
            "chord_share": chord}


def test_the_three_figures_beside_the_bottleneck():
    parts = {"a": _build_part(-1.0, 0.0, 0.5), "b": _build_part(-4.0, 0.2, 0.1), "c": _build_part(None, 0.1, 0.0),
             "d": _build_part(-2.0, 0.3, 0.9)}
    figs = SN.part_figures(parts, ["a", "b", "c", "d"])
    assert set(figs) == set(SN.FIGURES) == {"ring_kept_db", "bent_share", "chord_share"}
    assert figs["ring_kept_db"] == {"a": -1.0, "b": -4.0, "c": None, "d": -2.0}
    assert figs["chord_share"]["d"] == 0.9 and SN.part_figures({}, ["x"])["bent_share"] == {"x": None}
    d = {"a": 0.0, "b": 0.3, "c": 0.1, "d": 0.2}
    got = SN.by_figure(d, figs["ring_kept_db"])                           # c carries no figure: left out
    assert got["parts"] == 3 and got["lower"] == ["b"] and got["upper"] == ["d", "a"]
    assert got["lower_mean"] == pytest.approx(0.3) and got["upper_mean"] == pytest.approx(0.1)
    assert got["spearman"] == pytest.approx(-1.0)                          # less late level, larger D_notes
    assert SN.by_figure(d, figs["bent_share"])["spearman"] == pytest.approx(0.8)


def test_spearman_and_share_of():
    assert SN.spearman([(1, 1), (2, 2), (3, 3)]) == pytest.approx(1.0)
    assert SN.spearman([(1, 3), (2, 2), (3, 1)]) == pytest.approx(-1.0)
    assert SN.spearman([(1, 1), (1, 2), (2, 3)]) == pytest.approx(math.sqrt(3) / 2)       # ties at their mean rank
    assert SN.spearman([(1, 1), (2, 2)]) is None and SN.spearman([(1, 1), (1, 2), (1, 3)]) is None
    assert SN.share_of({"mean": -0.1}, {"mean": -0.2}) == pytest.approx(0.5)
    for a, b in ((None, {"mean": -0.2}), ({"mean": -0.1}, None), ({"mean": None}, {"mean": -0.2}),
                 ({"mean": -0.1}, {"mean": 0.0})):
        assert SN.share_of(a, b) is None


def test_the_dry_guitar_is_hashed_from_the_audio_handed_to_the_search(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    x = np.linspace(-0.5, 0.5, 4800).astype(np.float32)
    np.save(tmp_path / "x.npy", x)
    assert S.npy_sha(np.load(tmp_path / "x.npy")) == T.NR.file_sha(tmp_path / "x.npy")   # the build's own hash
    seen = {}

    def fake_run_part(*a, **k):
        seen.update(k)
        return {"renders": 0}
    monkeypatch.setattr(S, "run_part", fake_run_part)
    p = {"pkey": "goat__x"}
    with pytest.raises(SystemExit, match="not the declared one"):
        S.search_row_part(p, "tr-di", "xlnoG", x * 1.0001, None, None, None, tmp_path / "r.json", "l",
                          dry_sha256=S.npy_sha(x))
    assert not seen and not (tmp_path / "r.json").exists()                  # refused before any render
    rec = S.search_row_part(p, "tr-di", "xlnoG", x, None, None, None, tmp_path / "r.json", "l",
                            dry_sha256=S.npy_sha(x))
    assert seen["dry_sha256"] == S.npy_sha(x) and rec["ledger"] == "l"
    seen.clear()
    S.search_row_part(p, "true", "xlnoG", x, None, None, None, tmp_path / "s.json", "l")    # rows (b), (c): as before
    assert seen["dry_sha256"] is None


def test_the_start_reference_refuses_a_priming_other_than_sx1_start(monkeypatch, tmp_path):
    pytest.importorskip("numpy")
    p = {"pkey": "x", "amp": "ac20", "cen": {"settings": {}, "select": "0"}, "lag": 0, "search": "A"}
    monkeypatch.setattr(SN, "first_evaluation", lambda p: {("other", "key"): "1"})
    with pytest.raises(SystemExit, match="priming"):
        SN.start_reference(p, [0.0], None, lambda: pytest.fail("rendered"), tmp_path / "s.json", "D")
    (tmp_path / "s.json").write_text(json.dumps({"dry_sha256": "D", "value": 1.25}))
    assert SN.start_reference(p, [0.0], None, None, tmp_path / "s.json", "D") == (1.25, 0)    # reused: no renders
    with pytest.raises(SystemExit, match="another dry guitar"):
        SN.start_reference(p, [0.0], None, None, tmp_path / "s.json", "E")


def test_the_refusal_stop_counts_the_forty():
    sets_of = {"b1": "bks", "b2": "bks", "g1": "goat", "p1": "panel", "p2": "panel", "p3": "panel"}
    assert SN.deciding_stop({"b1": 1, "p1": 1, "p2": 1, "p3": 1}, sets_of) == (["b1"], ["p1", "p2", "p3"], False)
    assert SN.deciding_stop({"b1": 1, "b2": 1, "g1": 1}, sets_of)[2]


def test_paired_values_and_checks_passed():
    new = {"a": {"G": -0.1}, "b": None, "c": {"G": 0.2}}
    old = {"a": {"G": -0.3}, "b": {"G": 0.0}, "c": None}
    assert SN.paired_values(new, old, "G") == {"a": pytest.approx(0.2)}
    assert "score-check has not run" in SN.checks_passed(None, {"passed": True})
    assert "search-check did not pass" in SN.checks_passed({"passed": True}, {"passed": False})
    assert SN.checks_passed({"passed": True}, {"passed": True}) is None


def test_the_rows_paths():
    assert SN.check_dir("check-score").name == "check-score" and SN.check_dir("check-search").parent.name == "notes"
    with pytest.raises(ValueError):
        SN.check_dir("score")
    for p in (SN.search_path("x"), SN.score_path("x"), SN.answers_path(), SN.check_dir("check-score")):
        assert "fs-both" not in str(p) and p.relative_to(S.fs_dir() / "notes")


@pytest.mark.parametrize("cmd", sorted(SN.COMMANDS))
def test_every_command_refuses_off_main(monkeypatch, cmd):
    monkeypatch.setattr(T, "redo_on_main", lambda: ({}, "this checkout's learn/scratch_notes.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        SN.COMMANDS[cmd](type("A", (), {"shard": (0, 1), "first": 0})())


@pytest.mark.parametrize("cmd", sorted(SN.COMMANDS))
def test_every_command_refuses_without_row_cs_outcome_or_the_declarations(monkeypatch, cmd):
    main = {"note-rebuild": {T.PHASE: "d"}, "preset-ladder": {SN.PHASE: "d"}}
    monkeypatch.setattr(T, "redo_on_main", lambda: (main, None))
    with pytest.raises(SystemExit, match="phase_scratch_both_outcome"):
        SN.COMMANDS[cmd](type("A", (), {"shard": (0, 1), "first": 0})())
    main["preset-ladder"] = {SN.GATE: "F-both"}
    with pytest.raises(SystemExit, match="phase_scratch_notes"):
        SN.COMMANDS[cmd](type("A", (), {"shard": (0, 1), "first": 0})())


@pytest.mark.parametrize("cmd, needs", [("search", "phase_nr_1_redo_install"), ("answers", "phase_nr_1_redo_install"),
                                        ("score", "phase_nr_1_redo_install"), ("read", "phase_nr_1_redo_install")])
def test_the_row_waits_for_the_install_notes_and_build(monkeypatch, cmd, needs):
    main = {"note-rebuild": {T.PHASE: "d"}, "preset-ladder": {SN.PHASE: "d", SN.GATE: "F-both"}}
    monkeypatch.setattr(T, "redo_on_main", lambda: (main, None))
    with pytest.raises(SystemExit, match=needs):
        SN.COMMANDS[cmd](type("A", (), {"shard": (0, 1), "first": 0})())
    main["note-rebuild"].update({T.PHASE_INSTALL: {}, T.PHASE_NOTES: {}, T.PHASE_EAR: {"verdict": "ok"}})
    with pytest.raises(SystemExit, match="phase_scratch_notes_dry"):
        SN.COMMANDS[cmd](type("A", (), {"shard": (0, 1), "first": 0})())


def test_answers_score_and_read_refuse_without_the_ear_verdict(monkeypatch):
    main = {"note-rebuild": {T.PHASE: "d", T.PHASE_INSTALL: {}, T.PHASE_NOTES: {}, T.PHASE_EAR: {"verdict": "ask"}},
            "preset-ladder": {SN.PHASE: "d", SN.GATE: "F-both", SN.PHASE_DRY: {}, SN.PHASE_ANSWERS: {}}}
    monkeypatch.setattr(T, "redo_on_main", lambda: (main, None))
    for cmd in ("answers", "score", "read"):
        with pytest.raises(SystemExit, match="reads ask"):
            SN.COMMANDS[cmd](type("A", (), {"shard": (0, 1), "first": 0})())


def test_search_refuses_until_both_checks_passed(monkeypatch):
    main = {"note-rebuild": {T.PHASE: "d", T.PHASE_INSTALL: {}, T.PHASE_NOTES: {}},
            "preset-ladder": {SN.PHASE: "d", SN.GATE: "F-both", SN.PHASE_DRY: {}}}
    monkeypatch.setattr(T, "redo_on_main", lambda: (main, None))
    monkeypatch.setattr(SN, "check_result", lambda kind: None)
    with pytest.raises(SystemExit, match="score-check has not run"):
        SN.cmd_search(type("A", (), {"shard": (0, 1), "first": 0})())
    monkeypatch.setattr(SN, "check_result", lambda kind: {"passed": kind == "check-score", "mismatches": [1]})
    with pytest.raises(SystemExit, match="search-check did not pass"):
        SN.cmd_search(type("A", (), {"shard": (0, 1), "first": 0})())


# --- the refactor: rows (b) and (c) as before ---------------------------------------------------------------------------------

def test_rows_b_and_c_resolve_as_before():
    assert S.ROWS == {"fs-stem": ("true", "xlnoG"), "fs-both": ("avg+mild", "xlnoG"),
                      "fs-blur": ("avg+mild", "clean"), "fs-control": ("true", "clean")}
    assert [S.phase_answers(r) for r in S.ROWS] == ["phase_fs_answers_stem", "phase_fs_answers_both",
                                                     "phase_fs_answers_blur", "phase_fs_answers_control"]
    with pytest.raises(SystemExit, match="unknown row"):
        S.phase_answers(SN.ROW)                                            # the new row is not one of S's rows
    assert S.DECIDING == ["bks", "goat", "panel"] and S.REFUSAL_STOP == 3
    assert S.next_row({"fs-stem": "passes", "fs-both": "passes"}) is None


def test_the_outcome_table_is_unchanged():
    S.table_guard()
    assert len(S.paths()) == 32
    P_, K_, F_, U_, U2_ = ("passes",), ("constant",), ("fails",), ("undecided",), ("undecided-b2",)
    NOT_P, B_NOT_P, NONE = ("constant", "fails", "undecided"), ("constant", "fails", "undecided", "undecided-b2"), (None,)
    assert S.OUTCOME_TABLE == (
        (P_, NONE, P_, NONE, "F-both", None),
        (P_, NONE, NOT_P, P_, "F-compound", None),
        (P_, NONE, NOT_P, ("fails", "undecided"), "F-dry", None),
        (P_, NONE, NOT_P, K_, "F-constant", "fs-blur"),
        (F_, P_, NONE, NONE, "F-stem", None),
        (U_, P_, NONE, NONE, "F-undecided", None),
        (U2_, P_, P_, NONE, "F-both", None),
        (U2_, P_, ("fails", "undecided"), NONE, "F-undecided", None),
        (U2_, P_, K_, NONE, "F-constant", "fs-both"),
        (K_, P_, NONE, NONE, "F-constant", "fs-stem"),
        (B_NOT_P, ("fails", "undecided"), NONE, NONE, "F-start", None),
        (B_NOT_P, K_, NONE, NONE, "F-constant", "fs-control"))


def test_the_refactored_commands_still_refuse_off_main(monkeypatch, tmp_path):
    (tmp_path / "draw.json").write_text("{}")
    monkeypatch.setattr(S, "draw_path", lambda: tmp_path / "draw.json")
    monkeypatch.setattr(S, "on_main", lambda: (None, "this checkout's learn/scratch_search.py differs from main's"))
    for cmd in ("search", "answers", "score", "read"):
        with pytest.raises(SystemExit, match="differs from main's"):
            S.COMMANDS[cmd](type("A", (), {"row": "fs-both", "shard": (0, 1), "first": 0})())


def test_a_short_budget_requests_the_same_first_settings():
    """The search check's premise: `coord_search` at a budget of 10 asks for exactly the first 10 settings it asks
    for at 200 (C2's call, a deterministic objective)."""
    from learn import full_controls as F
    from learn import knob_ceiling as K

    for amp in S.AMPS:
        start = F.c1a_start({}, amp)
        dims = F.c1a_space(amp, start)
        seqs = {}
        for budget in (SN.CHECK_BUDGET, S.BUDGET):
            seq = []

            def f(x):
                seq.append(K.key(x))
                return 1.0 + (int(K.key(x), 16) % 10007) / 10007
            K.coord_search(dims, start, f, budget, F.SEED, cats="levels", canon=F.make_canon(amp))
            seqs[budget] = seq
        assert len(seqs[SN.CHECK_BUDGET]) == SN.CHECK_BUDGET
        assert seqs[SN.CHECK_BUDGET] == seqs[S.BUDGET][:SN.CHECK_BUDGET]


# --- with numpy and the stored data -------------------------------------------------------------------------------------------

def _stored():
    pytest.importorskip("numpy")
    from learn import note_replay as R

    need = [S.draw_path(), S.answers_path("fs-both"), S.rows_path("fs-both"), S.rows_path("fs-stem"), R.draw_path()]
    if not all(p.exists() for p in need):
        pytest.skip("no stored from-scratch data")
    draw = json.loads(S.draw_path().read_text())
    return R, draw, R.Stored(), {p["pkey"]: p for p in json.loads(R.draw_path().read_text())["parts"]}


def _jsonable(x):
    return json.loads(json.dumps(x, default=str))


def test_the_shared_read_path_reproduces_row_cs_rows_file():
    R, draw, sd, rby = _stored()
    ans = json.loads(S.answers_path("fs-both").read_text())
    sha = S.file_sha(S.answers_path("fs-both"))
    per, refused, replaced, ctl = S.read_row_parts(draw, ans, sha, lambda k: S.score_path("fs-both", k), sd, rby)
    got = _jsonable(dict(S.report_body("fs-both", "c", sha, per, refused, replaced, ctl),
                         rows=S.summarise_row(sd, draw, per)))
    want = json.loads(S.rows_path("fs-both").read_text())
    got.pop("time"), want.pop("time")
    assert got == want


def test_paired_reproduces_c_less_b_and_row_cs_bar():
    R, draw, sd, rby = _stored()
    per = {r: json.loads(S.rows_path(r).read_text())["parts"] for r in ("fs-both", "fs-stem")}
    d = SN.paired_values(per["fs-both"], per["fs-stem"], "G")
    pool = SN.set_rows(sd, draw, d)["deciding_pool"]
    assert (round(pool["mean"], 3), round(pool["lo90"], 3), round(pool["hi90"], 3)) == (0.167, 0.110, 0.224)
    g = SN.set_rows(sd, draw, {k: v["G"] for k, v in per["fs-both"].items() if v})["bks_goat"]["all"]
    assert (round(g["mean"], 3), round(g["lo90"], 3), round(g["hi90"], 3)) == (-0.087, -0.155, -0.018)
    gs = SN.set_rows(sd, draw, {k: v["G_shrunk"] for k, v in per["fs-both"].items() if v})["bks_goat"]["all"]
    assert (round(gs["mean"], 3), round(gs["lo90"], 3), round(gs["hi90"], 3)) == (-0.148, -0.201, -0.095)
    assert sum(v["G"] >= 0.10 for v in per["fs-both"].values() if v) == 8


def test_rows_b_and_c_are_read_and_refuse_a_rerun():
    R, draw, sd, rby = _stored()
    got = S.read_so_far()
    assert got == {"fs-stem": "passes", "fs-both": "passes"} and S.next_row(got) is None
    assert S.outcome(got)["code"] == "F-both"
