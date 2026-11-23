"""The from-scratch search's `fs-loudar` row, LOUDAR's second test (`learn/scratch_loudar.py`, plan doc
section 13): `FL_TABLE` and `fl_code` (every case ends in exactly one code; FL-above and FL-reach never hold with
FL-short; the deciding number switches to D_bar exactly when D_cut's upper end is above +0.05; FL-above needs G50's
upper end below zero; FL-reach says when the bar is itself level with Cen), the bottleneck rule, the slot rule
(fs-notes' report and an "ok" ear verdict), the span for every stored lag, the timing check, the pool rule, the
refusal stop on the 23, and every command's refusals. Pure: the light CI runner (no numpy). With numpy and the
stored data (skipped elsewhere): `bp_rows` reproduces the comparators on BKS and the panel, and prep's clip is the
blanked reference's span."""
import itertools
import json
import pathlib

import pytest

from learn import note_transcribe as T
from learn import scratch_codec as SC
from learn import scratch_loudar as SL
from learn import scratch_notes as SN
from learn import scratch_search as S

REPO = pathlib.Path(__file__).resolve().parents[1]


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


G_BELOW, G_LEVEL = _iv(-0.2, -0.3, -0.1), _iv(-0.1, -0.3, 0.1)
NULL_OK = _iv(-0.15, -0.25, -0.06)                 # LOUDAR readably better than its input
CUT_FREE = _iv(0.0, -0.02, 0.03)


def _reference(d_null, d_blur, d_cut, d_bar, g50):
    """FL_TABLE as mutually exclusive predicates, written apart from `fl_code`'s order."""
    d = d_bar if d_cut["hi90"] > 0.05 else d_blur
    null = d_null["lo90"] >= -0.05
    above = not null and d["hi90"] < 0 and d["mean"] <= -0.05 and g50["hi90"] < 0
    reach = not (null or above) and d["hi90"] < 0.10 and d["mean"] < 0.05
    short = not (null or above or reach) and d["lo90"] > 0 and d["mean"] >= 0.05
    und = not (null or above or reach or short)
    hits = [c for c, h in zip(SL.FL_CODES, (null, above, reach, short, und)) if h]
    assert len(hits) == 1
    return hits[0]


IVS = [_iv(m, m + lo, m + hi) for m, lo, hi in itertools.product((-0.2, -0.1, -0.06, -0.04, 0.0, 0.04, 0.06, 0.12),
                                                                 (-0.08, -0.03), (0.03, 0.08))]


def test_fl_table_guard():
    SL.fl_table_guard()
    assert SL.FL_CODES == ("FL-null", "FL-above", "FL-reach", "FL-short", "FL-undecided")


def test_fl_code_every_case_ends_in_exactly_one_code():
    seen = set()
    for d_null, d, d_cut, g50 in itertools.product(IVS[::3], IVS, (CUT_FREE, _iv(0.06, 0.02, 0.1)),
                                                   (G_BELOW, G_LEVEL)):
        got = SL.fl_code(d_null, d, d_cut, d, g50, G_LEVEL)
        assert got["code"] == _reference(d_null, d, d_cut, d, g50)
        seen.add(got["code"])
    assert seen == set(SL.FL_CODES)


def test_the_deciding_number_switches_to_d_bar_exactly_on_the_cuts_cost():
    blur, bar = _iv(0.08, 0.04, 0.12), _iv(-0.12, -0.18, -0.06)
    assert SL.fl_code(NULL_OK, blur, _iv(0.02, -0.01, 0.05), bar, G_BELOW, G_LEVEL)["number"] == "D_blur"
    got = SL.fl_code(NULL_OK, blur, _iv(0.02, -0.01, 0.0501), bar, G_BELOW, G_LEVEL)
    assert got["number"] == "D_bar" and got["code"] == "FL-above" and got["heard"]


def test_fl_above_needs_g50_below_zero_and_fl_reach_names_a_level_bar():
    d = _iv(-0.08, -0.12, -0.03)
    assert SL.fl_code(NULL_OK, d, CUT_FREE, d, G_BELOW, G_LEVEL)["code"] == "FL-above"
    got = SL.fl_code(NULL_OK, d, CUT_FREE, d, G_LEVEL, G_LEVEL)         # G50's upper end not below zero
    assert got["code"] == "FL-reach" and "G50(ld-stem)" in got["gate"]
    assert "level with a bar that is itself level with Cen here" in got["reading"]
    assert "itself level" not in SL.fl_code(NULL_OK, _iv(0.0, -0.04, 0.05), CUT_FREE, d, G_LEVEL,
                                            G_BELOW)["reading"]
    assert "not by a heard size" in SL.fl_code(NULL_OK, d, CUT_FREE, d, G_BELOW, G_LEVEL)["reading"]


def test_fl_null_comes_first_and_the_rest():
    assert SL.fl_code(_iv(0.0, -0.04, 0.04), G_BELOW, CUT_FREE, G_BELOW, G_BELOW, G_LEVEL)["code"] == "FL-null"
    assert SL.fl_code(NULL_OK, _iv(0.08, 0.03, 0.13), CUT_FREE, G_BELOW, G_BELOW, G_LEVEL)["code"] == "FL-short"
    assert SL.fl_code(NULL_OK, _iv(0.04, -0.01, 0.11), CUT_FREE, G_BELOW, G_BELOW, G_LEVEL)["code"] == \
        "FL-undecided"
    with pytest.raises(SystemExit):
        SL.fl_code(None, G_BELOW, CUT_FREE, G_BELOW, G_BELOW, G_LEVEL)


def test_the_bottleneck_rule():
    assert SL.bottleneck("FL-reach", "short")["bottleneck"] == "the stem"
    assert SL.bottleneck("FL-above", None)["bottleneck"] == "the stem"
    assert SL.bottleneck("FL-short", "at the bar")["bottleneck"] == "the prior's coverage, or memorisation"
    assert SL.bottleneck("FL-short", "short")["bottleneck"] == "the generator or its operator"
    assert SL.bottleneck("FL-null", None)["bottleneck"] == "generator against prior: not split"
    with pytest.raises(SystemExit):
        SL.bottleneck("F-both", None)
    assert SL.goat_reading(None) is None
    assert SL.goat_reading(_iv(0.0, -0.05, 0.05)) == "at the bar"
    assert SL.goat_reading(_iv(0.06, 0.0, 0.12)) == "short"


def test_the_slot_rule():
    # waiting: no report while fs-notes may still run (the verdict missing, unreadable, "ok", or one that goes to the
    # user: "ask" and "incomplete" are not a fault, fs-notes may still run after them)
    for ear in (None, {}, "ok", {"verdict": None}, {"verdict": "ok"}, {"verdict": "ask"}, {"verdict": "incomplete"}):
        assert "renders wait" in SL.slots_refusal(False, ear)
    # path 1: fs-notes' report exists, whatever the verdict
    for ear in (None, {"verdict": "ok"}, {"verdict": "ask"}, {"verdict": "fault-content"}):
        assert SL.slots_refusal(True, ear) is None
    # path 2: no report, but a fault verdict is recorded: fs-notes will not run
    assert SL.OPEN_VERDICTS == ("fault-content", "fault-signal")
    for v in SL.OPEN_VERDICTS:
        assert SL.slots_refusal(False, {"verdict": v}) is None
    assert SL.rec_refusal(None) and SL.rec_refusal({"fl": {"code": "FL-reach"}})
    assert SL.rec_refusal({"fl": {"code": "FL-short"}}) is None and SL.rec_refusal({"fl": {"code": "FL-null"}}) is None


@pytest.mark.parametrize("half", ["A", "B"])
def test_the_span_for_every_stored_lag(half):
    a, b = SL.half_samples(half)
    assert b - a == SL.CLIP
    for lag in range(-81, 92):
        lo, hi, c0, c1 = SL.span({"search": half, "lag": lag})
        assert 0 <= lo < hi <= SL.SECTION and hi - lo == c1 - c0 and 0 <= c0 < c1 <= SL.CLIP
        assert lo == max(0, a - lag - SL.LATENCY + SL.TRIM_N)
    assert SL.HALVES == {"A": (1.0, 5.5), "B": (5.5, 10.0)}


def test_the_halves_and_latency_are_mains():
    from learn import knob_ceiling as K
    from learn import pretrain_set as PS

    assert SL.HALVES == dict(K.R.HALVES) == dict(PS.HALVES)
    assert SL.LATENCY == K.P.LATENCY and SL.TRIM_N == int(PS.TRIM_S * PS.SR) and SL.SECTION == 492000


def test_the_timing_check_counts_deciding_parts():
    sets_of = {"b1": "bks", "b2": "bks", "p1": "panel", "g1": "goat", "g2": "goat", "g3": "goat"}
    off = {"ld-stem": {"b1": 2.0, "b2": 0.0, "p1": 1.5, "g1": 5.0, "g2": 5.0, "g3": 5.0}}
    assert SL.timing_stop(off, sets_of) == ({"ld-stem": ["b1", "p1"]}, False)       # GOAT never stops it
    off["ld-stem"]["b2"] = None
    assert SL.timing_stop(off, sets_of)[1]


def test_the_timing_check_stops_on_ld_names_only_and_reports_stem_in_beside():
    sets_of = {"b1": "bks", "b2": "bks", "p1": "panel"}
    late = {"b1": 3.0, "b2": -2.0, "p1": 4.0}
    beyond, stop = SL.timing_stop({"stem-in": dict(late), "ld-stem": {"b1": 0.0, "b2": 0.0, "p1": 0.0}}, sets_of)
    assert not stop and beyond == {"stem-in": ["b1", "b2", "p1"], "ld-stem": []}     # reported, never a stop
    for name in ("ld-stem", "ld-stem-b", "ld-rec"):
        assert SL.timing_stop({name: dict(late)}, sets_of)[1]
    assert SL.TIMING_NAMES_PREFIX == "ld-" and "di-cut" not in SL.PLACED


def test_the_pool_rule_and_the_refusal_stop():
    ok = {"bks": {"mean": 0.0}, "panel": {"mean": 0.0, "clusters": 3}, "bp": _iv(0.0, -0.1, 0.1)}
    assert SL.pool_refusal(ok) is None
    assert "panel" in SL.pool_refusal(dict(ok, panel={"mean": 0.0, "clusters": 2}))
    assert "bks" in SL.pool_refusal(dict(ok, bks={"mean": None}))
    assert "pooled" in SL.pool_refusal(dict(ok, bp=None))
    sets_of = {"b1": "bks", "b2": "bks", "p1": "panel", "g1": "goat", "g2": "goat", "g3": "goat"}
    assert SL.deciding_stop({"g1": 1, "g2": 1, "g3": 1}, sets_of) == ([], ["g1", "g2", "g3"], False)
    assert SL.deciding_stop({"b1": 1, "b2": 1, "p1": 1}, sets_of)[2]


def test_the_notes_comparisons_width_on_bks():
    parts = [{"set": "bks", "cluster": f"bks|set5/BKS_{s}_Full/{i}_x.wav"} for s, i in (("A", 1), ("A", 2), ("B", 3))]
    assert SL.notes_width(parts + [{"set": "goat", "cluster": "goat|g"}]) == {"parts": 3, "songs": 2}


def test_the_phases_are_new_and_outside_the_other_rows_guards():
    keys = [SL.PHASE, SL.PHASE_DRY, SL.PHASE_DRY_REC, SL.PHASE_OUTCOME] + [SL.phase_answers(n) for n in SL.SHORT]
    assert keys[4:] == ["phase_scratch_loudar_answers_stem", "phase_scratch_loudar_answers_cut",
                        "phase_scratch_loudar_answers_in", "phase_scratch_loudar_answers_rec"]
    for k in keys:
        assert not k.startswith(tuple(p for ps in T.KEY_PREFIXES.values() for p in ps))
        assert not k.startswith(("phase_fs", "phase_scratch_notes", "phase_scratch_tone", "phase_scratch_codec"))
    with pytest.raises(SystemExit):
        SL.phase_answers("ld-stem-b")
    d = json.loads((REPO / "docs/dev-test-ledger.json").read_text())
    e = next(t for t in d["tests"] if t.get("test_id") == S.LEDGER_ID)
    pinned = {"phase_scratch_loudar_globals"}        # the checkpoint's allowlist (learn/loudar_run.py's pin)
    assert set(SL.loudar_keys(e)) <= set(keys) | pinned and SL.PHASE in e


def test_the_module_edits_no_shared_file_and_imports_no_numpy_at_its_top():
    import ast

    src = (REPO / "learn" / "scratch_loudar.py").read_text()
    top = [n for n in ast.parse(src).body if isinstance(n, (ast.Import, ast.ImportFrom))]
    mods = {a.name for n in top if isinstance(n, ast.Import) for a in n.names} | \
        {n.module for n in top if isinstance(n, ast.ImportFrom)}
    assert not mods & {"numpy", "torch"}
    assert SL.CODE_FILES == ("learn/scratch_loudar.py", "learn/loudar_run.py", "learn/scratch_codec.py",
                             "learn/codec_roundtrip.py")


# --- every command's refusals ----------------------------------------------------------------------------------------------

def _args(name="ld-stem"):
    return type("A", (), {"name": name, "shard": (0, 1), "first": 0})()


BASE = {S.PHASE: "d", S.PHASE_DRAW: {"sha256": "x"}, SC.GATE: "F-both", SC.PHASE_OUTCOME: {"code": {}}}
ALL = dict(BASE, **{SL.PHASE: "d", SL.PHASE_DRY: {"sha256": "b"}, SL.PHASE_DRY_REC: {"sha256": "r"}},
           **{SL.phase_answers(n): {"sha256": "a"} for n in SL.SHORT})


def _main(monkeypatch, main, checks=True):
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    monkeypatch.setattr(SL, "code_refusal", lambda m: None)
    monkeypatch.setattr(SN, "check_result", lambda kind: {"passed": checks, "mismatches": [] if checks else [1]})
    monkeypatch.setattr(SC, "check_shas", lambda: dict(SC.CHECK_SHA256))


@pytest.mark.parametrize("cmd", sorted(SL.COMMANDS))
def test_every_command_refuses_off_main(monkeypatch, cmd):
    monkeypatch.setattr(S, "on_main", lambda: (None, "this checkout's learn/scratch_search.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        SL.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", sorted(SL.COMMANDS))
def test_every_command_refuses_without_the_declarations(monkeypatch, cmd):
    _main(monkeypatch, dict(BASE))
    with pytest.raises(SystemExit, match="has no phase_scratch_loudar"):
        SL.COMMANDS[cmd](_args())
    _main(monkeypatch, {S.PHASE: "d", S.PHASE_DRAW: {}, SC.GATE: "F-both", SL.PHASE: "d"})
    with pytest.raises(SystemExit, match="phase_scratch_codec_outcome"):
        SL.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", sorted(SL.COMMANDS))
def test_every_command_refuses_off_mains_code_or_without_the_checks(monkeypatch, cmd):
    _main(monkeypatch, dict(ALL))
    monkeypatch.setattr(SL, "code_refusal", lambda m: "this checkout's learn/scratch_loudar.py differs from main's")
    with pytest.raises(SystemExit, match="scratch_loudar.py differs"):
        SL.COMMANDS[cmd](_args())
    _main(monkeypatch, dict(ALL), checks=False)
    with pytest.raises(SystemExit, match="did not pass"):
        SL.COMMANDS[cmd](_args())


LATER = ("build-rec", "start", "control", "search", "answers", "score", "read", "read-rec", "versus-notes")


@pytest.mark.parametrize("cmd", LATER)
def test_every_later_command_refuses_without_the_builds_hash(monkeypatch, tmp_path, cmd):
    _main(monkeypatch, dict(BASE, **{SL.PHASE: "d"}))
    with pytest.raises(SystemExit, match="phase_scratch_loudar"):
        SL.COMMANDS[cmd](_args())


def _built(monkeypatch, tmp_path, report_ok=True, ear="ok", control=None):
    (tmp_path / "build.json").write_text(json.dumps({"names": {"ld-stem": {}, "di-cut": {}, "stem-in": {}}}))
    monkeypatch.setattr(SL, "build_path", lambda rec=False: tmp_path / ("build-rec.json" if rec else "build.json"))
    main = dict(ALL, **{SL.PHASE_DRY: {"sha256": S.file_sha(tmp_path / "build.json")}})
    _main(monkeypatch, main)
    (tmp_path / "notes-report.json").write_text("{}")
    monkeypatch.setattr(SN, "report_path", lambda: tmp_path / ("notes-report.json" if report_ok else "none.json"))
    monkeypatch.setattr(SL, "note_rebuild_main", lambda: {T.PHASE_EAR: {"verdict": ear}})
    monkeypatch.setattr(SL, "check_dir", lambda: tmp_path / "check")
    monkeypatch.setattr(SL, "report_path", lambda rec=False: tmp_path / ("report-rec.json" if rec else "report.json"))
    if control is not None:
        (tmp_path / "check").mkdir(exist_ok=True)
        (tmp_path / "check" / "result.json").write_text(json.dumps(control))
    return main


@pytest.mark.parametrize("cmd", SL.RENDER_COMMANDS)
def test_every_render_command_waits_for_fs_notes(monkeypatch, tmp_path, cmd):
    for ear in ("ok", None, "ask", "incomplete"):     # no report, fs-notes may still run: wait
        _built(monkeypatch, tmp_path, report_ok=False, ear=ear)
        with pytest.raises(SystemExit, match="fs-notes may still run"):
            SL.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", SL.RENDER_COMMANDS)
@pytest.mark.parametrize("report_ok, ear", [(True, "ok"), (True, "ask"), (False, "fault-content"),
                                            (False, "fault-signal")])
def test_every_render_command_passes_the_slot_gate_on_either_path(monkeypatch, tmp_path, cmd, report_ok, ear):
    _built(monkeypatch, tmp_path, report_ok=report_ok, ear=ear)
    with pytest.raises(SystemExit) as e:    # past the gate, a later guard stops it (the draw's hash is a stand-in)
        SL.COMMANDS[cmd](_args())
    assert "fs-notes may still run" not in str(e.value)


def test_search_waits_for_the_control(monkeypatch, tmp_path):
    _built(monkeypatch, tmp_path)
    with pytest.raises(SystemExit, match="the control has not run"):
        SL.cmd_search(_args())
    _built(monkeypatch, tmp_path, control={"passed": False, "search": {}})
    with pytest.raises(SystemExit, match="the control did not pass"):
        SL.cmd_search(_args())


@pytest.mark.parametrize("cmd", ["build-rec", "start", "search", "answers", "score"])
def test_ld_rec_waits_for_a_fail(monkeypatch, tmp_path, cmd):
    _built(monkeypatch, tmp_path, control={"passed": True})
    (tmp_path / "report.json").write_text(json.dumps({"fl": {"code": "FL-reach"}}))
    with pytest.raises(SystemExit, match="ld-rec does not run"):
        SL.COMMANDS[cmd](_args("ld-rec"))


def test_a_name_outside_the_build_or_the_row_is_refused(monkeypatch, tmp_path):
    _built(monkeypatch, tmp_path, control={"passed": True})
    with pytest.raises(SystemExit, match="not in the build"):
        SL.cmd_start(_args("ld-stem-b"))
    with pytest.raises(SystemExit, match="one of"):
        SL.cmd_search(_args("ld-stem-b"))


# --- with numpy --------------------------------------------------------------------------------------------------------------

def test_place_puts_the_clip_on_the_dis_timeline():
    np = pytest.importorskip("numpy")
    clip = np.arange(SL.CLIP, dtype=np.float32) + 1
    for half, lag in (("A", -81), ("A", 91), ("B", -81), ("B", 91), ("B", 0)):
        p = {"search": half, "lag": lag}
        y = SL.place(clip, p)
        lo, hi, c0, c1 = SL.span(p)
        assert y.dtype == np.float32 and len(y) == SL.SECTION and not y[:lo].any() and not y[hi:].any()
        assert np.array_equal(y[lo:hi], clip[c0:c1])


def _stored():
    pytest.importorskip("numpy")
    from learn import note_replay as R

    need = [S.draw_path(), S.answers_path("fs-both"), S.answers_path("fs-stem"), SC.answers_path("rt-m2l"),
            SC.answers_path("rt-dac"), R.draw_path()]
    if not all(p.exists() for p in need):
        pytest.skip("no stored from-scratch data")
    return R, json.loads(S.draw_path().read_text()), R.Stored()


def _rd(r):
    return tuple(round(r[k], 3) for k in ("mean", "lo90", "hi90"))


def test_bp_rows_reproduces_the_comparators_on_bks_and_the_panel():
    R, draw, sd = _stored()
    g = {}
    for row in ("fs-stem", "fs-both"):
        ans = json.loads(S.answers_path(row).read_text())
        g[row] = SC.comparator_g50(draw, ans, S.file_sha(S.answers_path(row)), lambda k, r=row: S.score_path(r, k))[0]
    for name in ("rt-m2l", "rt-dac"):
        ans = json.loads(SC.answers_path(name).read_text())
        g[name] = SC.codec_g50(draw, ans, S.file_sha(SC.answers_path(name)), lambda k, n=name: SC.score_path(n, k))[0]
    assert _rd(SL.bp_rows(sd, draw, SC.paired(g["fs-both"], g["fs-stem"]))["bp"]) == (0.125, 0.076, 0.173)
    assert _rd(SL.bp_rows(sd, draw, SC.paired(g["rt-m2l"], g["fs-stem"]))["bp"]) == (0.012, -0.006, 0.030)
    assert _rd(SL.bp_rows(sd, draw, SC.paired(g["rt-dac"], g["fs-stem"]))["bp"]) == (0.000, -0.017, 0.017)
    assert round(SL.bp_rows(sd, draw, g["fs-stem"])["bp"]["mean"], 3) == -0.242
    assert round(SL.bp_rows(sd, draw, g["fs-both"])["bp"]["mean"], 3) == -0.118
    bc = SL.bp_rows(sd, draw, g["fs-both"])
    assert bc["panel"]["clusters"] == 3 and SL.pool_refusal(bc) is None
    assert bc["bp"]["hi90"] >= 0                       # the bar is itself level with Cen on BKS+panel
    assert SL.notes_width(draw["parts"]) == {"parts": 16, "songs": 2}


def test_preps_clip_is_the_blanked_references_span():
    np = pytest.importorskip("numpy")
    R, draw, sd = _stored()
    for p in [q for q in draw["parts"] if q["set"] in SL.DECIDING][:3]:
        a, b = SL.half_samples(p["search"])
        stem = np.asarray(R.load_stem(SL.REF, p), np.float64)
        blank = S.load_ref_blank(sd, p, SL.REF)
        assert np.array_equal(stem[a:b], blank[a:b]) and not blank[:a].any() and not blank[b:].any()
        assert len(stem[a:b]) == SL.CLIP
