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


def test_every_report_carries_the_no_prior_improvement_caveat():
    note = SL.NO_PRIOR_IMPROVEMENT_NOTE
    assert "no measure we hold showed LOUDAR improving on its input" in note and "FL-null" in note
    src = (REPO / "learn" / "scratch_loudar.py").read_text()
    assert src.count("caveat=NO_PRIOR_IMPROVEMENT_NOTE") == 2                   # the read and ld-rec's read
    d = json.loads((REPO / "docs/dev-test-ledger.json").read_text())
    e = next(t for t in d["tests"] if t.get("test_id") == S.LEDGER_ID)["phase_scratch_loudar_gate_amend"]
    assert e["facts"]["authors_farther_on"].startswith("6 of 6") and "J0" in e["statement"]
    assert "not the user's own answer" in e["decided_by"]


def test_the_bottleneck_rule():
    ns = " (timing and timbre not separated)"
    assert SL.NOT_SEPARATED == ns
    assert SL.bottleneck("FL-reach", "short")["bottleneck"] == "the stem" + ns
    assert SL.bottleneck("FL-above", None)["bottleneck"] == "the stem" + ns
    assert SL.bottleneck("FL-short", "at the bar")["bottleneck"] == "the prior's coverage, or memorisation" + ns
    assert SL.bottleneck("FL-short", "short")["bottleneck"] == "the generator or its operator" + ns
    assert SL.bottleneck("FL-null", None)["bottleneck"] == "generator against prior: not split" + ns
    src = (REPO / "learn" / "scratch_loudar.py").read_text()
    body = src[src.index("def cmd_read_rec("):src.index("def cmd_versus_notes(")]
    assert "endswith(NOT_SEPARATED)" in body and "bottleneck: {bn['bottleneck']}" in body
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


def test_the_1ms_timing_check_is_report_only():
    sets_of = {"b1": "bks", "b2": "bks", "p1": "panel", "g1": "goat", "g2": "goat", "g3": "goat"}
    jitter = {"b1": -33.0, "b2": 0.0, "p1": 7.0, "g1": 5.0, "g2": 5.0, "g3": 5.0}      # as on LOUDAR's clips
    offsets = {"ld-stem": dict(jitter), "ld-stem-b": dict(jitter), "stem-in": {"b1": 0, "b2": 1.0, "p1": 0}}
    assert SL.timing_report(offsets, sets_of) == {"ld-stem": ["b1", "p1"], "ld-stem-b": ["b1", "p1"], "stem-in": []}
    medians, stop = SL.placement_stop(offsets, sets_of)                    # GOAT is never counted
    assert medians == {"ld-stem": 0.0, "ld-stem-b": 0.0, "stem-in": 0.0} and not stop
    assert not hasattr(SL, "timing_stop") and SL.TIMING_NAMES_PREFIX == "ld-" and "di-cut" not in SL.PLACED


@pytest.mark.parametrize("name", ["ld-stem", "ld-stem-b", "ld-rec", "stem-in"])
@pytest.mark.parametrize("shift", [2.5, -2.5, 3.0, -9.0])
def test_the_placement_stop_on_either_side(name, shift):
    sets_of = {"b1": "bks", "b2": "bks", "p1": "panel"}
    ok = {"b1": 0.0, "b2": 1.0, "p1": -1.0}
    moved = {k: v + shift for k, v in ok.items()}
    medians, stop = SL.placement_stop({name: moved, "other": dict(ok)}, sets_of)
    assert stop and medians[name] == pytest.approx(shift)
    assert not SL.placement_stop({name: {k: v + (2.0 if shift > 0 else -2.0) for k, v in
                                         {"b1": 0.0, "b2": 0.0, "p1": 0.0}.items()}}, sets_of)[1]   # +-2.0: passes
    assert SL.placement_stop({name: {"g1": 0.0}}, {"g1": "goat"})[1]       # no deciding value at all: stop
    assert SL.PLACEMENT_MS == 2.0


def test_the_timing_caveat_and_the_lags_beside_g50():
    c = SL.TIMING_CAVEAT
    assert "timing and timbre together" in c and "FL-short or FL-null" in c and "never" in c
    src = (REPO / "learn" / "scratch_loudar.py").read_text()
    assert src.count("timing_caveat=TIMING_CAVEAT") == 2                    # the read and ld-rec's read
    figs = {"a": {"ld-stem": {"lag_ms": -11.0}, "stem-in": {"lag_ms": 0.0}}, "b": {"ld-stem": {"lag_ms": 1.0}}}
    got = SL.lags_beside_g50({"b": -0.2, "a": 0.1}, figs, ["ld-stem", "stem-in"])
    assert list(got) == ["a", "b"] and got["a"]["G50"] == 0.1
    assert got["a"]["lag_ms"] == {"ld-stem": -11.0, "stem-in": 0.0}
    assert got["b"]["lag_ms"] == {"ld-stem": 1.0, "stem-in": None}
    assert got["a"]["sub_within_1ms"] == {"ld-stem": None, "stem-in": None}       # no diagnostic: blank, not 0
    assert len(SL.TIMING_DIAGNOSTIC_SHA256) == len(SL.TIMING_DECISION_SHA256) == 64
    d = json.loads((REPO / "docs/dev-test-ledger.json").read_text())
    e = next(t for t in d["tests"] if t.get("test_id") == S.LEDGER_ID)["phase_scratch_loudar_timing_amend"]
    assert e["diagnostic"]["sha256"] == SL.TIMING_DIAGNOSTIC_SHA256
    assert e["decision_record"]["sha256"] == SL.TIMING_DECISION_SHA256 and "not the user's" in e["decided_by"]


def test_the_subwindow_fraction_beside_g50_and_its_spearman():
    sub = {"a": {"set": "bks", "ld-stem": {"sub_frac_within1": 0.25}, "stem-in": {"sub_frac_within1": 0.9}},
           "b": {"set": "panel", "ld-stem": {"sub_frac_within1": 0.5}},
           "c": {"set": "bks", "ld-stem": {"sub_frac_within1": 0.75}},
           "g": {"set": "goat", "ld-stem": {"sub_frac_within1": 0.0}}}
    got = SL.lags_beside_g50({"a": 0.1, "b": 0.0}, {}, ["ld-stem", "stem-in"], sub)
    assert got["a"]["sub_within_1ms"] == {"ld-stem": 0.25, "stem-in": 0.9}
    assert got["b"]["sub_within_1ms"] == {"ld-stem": 0.5, "stem-in": None}
    sets_of = {"a": "bks", "b": "panel", "c": "bks", "g": "goat"}
    d_true = {"a": 0.3, "b": 0.2, "c": 0.1, "g": 9.0}                            # GOAT never counted
    r = SL.d_true_vs_subwin(d_true, sub, sets_of, "ld-stem")
    assert r == {"name": "ld-stem", "n": 3, "rho": pytest.approx(-1.0), "reported_only": True}
    assert SL.d_true_vs_subwin(d_true, sub, sets_of, "ld-rec") == {
        "name": "ld-rec", "note": "no sub-window diagnostic for ld-rec", "reported_only": True}
    assert SL.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert SL.spearman([1, 2, 2, 3], [1, 3, 2, 4]) == pytest.approx(0.9486832980505138)   # scipy's, with ties
    assert SL.spearman([1, 2], [2, 1]) is None and SL.spearman([1, 1, 1], [1, 2, 3]) is None
    assert SL.ranks([3.0, 1.0, 3.0, 2.0]) == [3.5, 1.0, 3.5, 2.0]


def test_ld_rec_reads_no_subwindow_diagnostic_not_blanks(capsys):
    sub = {"a": {"set": "bks", "ld-stem-b": {"sub_frac_within1": 0.25}, "stem-in": {"sub_frac_within1": 1.0}},
           "b": {"set": "panel", "stem-in": {"sub_frac_within1": 0.5}}}
    got = SL.lags_beside_g50({"a": 0.1, "b": 0.0}, {}, ["ld-rec", "ld-stem-b", "stem-in"], sub)
    assert got["a"]["sub_within_1ms"] == {"ld-rec": "no sub-window diagnostic for ld-rec", "ld-stem-b": 0.25,
                                          "stem-in": 1.0}
    assert got["b"]["sub_within_1ms"]["ld-rec"] == SL.no_subwin("ld-rec")
    assert got["b"]["sub_within_1ms"]["ld-stem-b"] is None                  # held elsewhere, blank on this part
    SL.print_lags(got)
    out = capsys.readouterr().out
    assert out.count("no sub-window diagnostic for ld-rec") == 2 and "ld-stem-b 0.25" in out and "ld-stem-b -" in out
    r = SL.d_true_vs_subwin({"a": 0.3, "b": 0.1}, sub, {"a": "bks", "b": "panel"}, "ld-rec")
    assert r["note"] == "no sub-window diagnostic for ld-rec" and "rho" not in r and "n" not in r


def test_read_rec_checks_the_bottleneck_before_any_report(monkeypatch, tmp_path):
    from learn import note_replay as NR

    monkeypatch.setattr(SL, "loudar_dir", lambda: tmp_path)
    (tmp_path / "report.json").write_text(json.dumps({"goat": "short"}))
    (tmp_path / f"answers-{SL.REC}.json").write_text("{}")
    monkeypatch.setattr(SL, "require_loudar", lambda *a: {})
    monkeypatch.setattr(SL, "require_rec", lambda m: {})
    monkeypatch.setattr(S, "require_draw", lambda: {"parts": []})
    monkeypatch.setattr(NR, "Stored", lambda: None)
    iv = _iv(0.1, 0.05, 0.15)
    rows = {q: {"bp": iv} for q in ("D_null", "D_blur", "D_cut", "D_bar", "G50")}
    rows.update(G50_rows_b_c={"fs-both": {"bp": iv}}, lag_beside_g50={}, D_true_vs_subwin={})
    monkeypatch.setattr(SL, "read_body", lambda *a: (rows, {}, {}))
    monkeypatch.setattr(SL, "bottleneck", lambda code, goat: {"bottleneck": "the generator or its operator",
                                                               "next": "x"})
    with pytest.raises(SystemExit, match="timing and timbre are not separated"):
        SL.cmd_read_rec(None)
    assert not SL.report_path(True).exists() and SL.rows_path(True).exists()   # the rows first, never the report
    src = (REPO / "learn" / "scratch_loudar.py").read_text()
    body = src[src.index("def cmd_read_rec("):src.index("def cmd_versus_notes(")]
    assert body.index("endswith(NOT_SEPARATED)") < body.index("P.save(report_path(True)")


def test_the_timing_diagnostic_is_read_by_its_sha256(monkeypatch, tmp_path):
    monkeypatch.setattr(SL, "loudar_dir", lambda: tmp_path)
    with pytest.raises(SystemExit, match="copy it there first"):
        SL.subwin_of()
    (tmp_path / SL.TIMING_DIAGNOSTIC).write_text(json.dumps({"a": {"set": "bks"}}))
    with pytest.raises(SystemExit, match="not TIMING_DIAGNOSTIC_SHA256"):
        SL.subwin_of()
    monkeypatch.setattr(SL, "TIMING_DIAGNOSTIC_SHA256", S.file_sha(tmp_path / SL.TIMING_DIAGNOSTIC))
    assert SL.subwin_of() == {"a": {"set": "bks"}}
    src = (REPO / "learn" / "scratch_loudar.py").read_text()
    assert src.count("D_true against the sub-window fraction (descriptive, never decides)") == 2


def test_the_dry_key_binds_the_build_and_names_the_placement_evidence():
    d = json.loads((REPO / "docs/dev-test-ledger.json").read_text())
    e = next(t for t in d["tests"] if t.get("test_id") == S.LEDGER_ID)[SL.PHASE_DRY]
    assert len(e["sha256"]) == 64 and e["files_sha256"]["figures.json"] and e["files_sha256"]["timing-subwin.json"] \
        == SL.TIMING_DIAGNOSTIC_SHA256
    assert "stem-in" in e["placement_evidence"] and "21 of 23" in e["placement_evidence"]
    assert "never decide" in e["reported_only_additions"]


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
    pinned = {"phase_scratch_loudar_globals",        # the checkpoint's allowlist (learn/loudar_run.py's pin)
              "phase_scratch_loudar_gate_amend",     # the gate's amendment (the direction check removed)
              "phase_scratch_loudar_timing_amend",   # the timing check made report-only, the placement stop kept
              "phase_scratch_loudar_read_nits"}      # the reads' report-only nits; timing-subwin.json protected
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
