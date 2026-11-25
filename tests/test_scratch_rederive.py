"""The rebuild's re-derivation on the exact bench (`learn/scratch_rederive.py`, `docs/rederive-plan.md`): the names and
keys (outside every guarded prefix), the cells, the value errors, the bench table read in two stages and the real-song
table (every interval case ends in exactly one code, fallbacks included, first match in order), the fit's declared
constants, the guards and the refusals. Synthetic keys; pure: runs on the light CI runner (no numpy). The last tests
need numpy, scipy, noisereduce and pyloudnorm: `derive`, `compose`, `input_form` and the cells against `rebuild_redo`
with a made-up bank (skipped elsewhere)."""
import ast
import itertools
import json
import math
import pathlib

import pytest

from learn import note_rebuild as NR
from learn import note_transcribe as NT
from learn import scratch_exact as SE
from learn import scratch_rederive as RD
from learn import scratch_search as S

REPO = pathlib.Path(__file__).resolve().parents[1]


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


BELOW, SPANS, ABOVE = _iv(-0.3, -0.5, -0.1), _iv(0.05, -0.1, 0.2), _iv(0.3, 0.1, 0.5)
EDGE_LO, EDGE_HI = _iv(0.1, 0.0, 0.2), _iv(-0.1, -0.2, 0.0)      # an end at exactly zero spans it
BAD = (None, {}, _iv(0.1, 0.2, 0.05), _iv(math.nan, -0.1, 0.1), _iv(0.0, -math.inf, 0.1), {"mean": 0.1, "lo90": None,
                                                                                           "hi90": 0.2}, "x")
CASES = (BELOW, SPANS, ABOVE, EDGE_LO, EDGE_HI) + BAD


# --- names and keys -----------------------------------------------------------------------------------------------------------

def test_names_and_keys():
    assert RD.PHASE == RD.KEY_PREFIX == "phase_scratch_rederive"
    assert [RD.answers_key(r) for r in RD.ROWS] == [
        "phase_scratch_rederive_answers_now", "phase_scratch_rederive_answers_fix",
        "phase_scratch_rederive_answers_null",
        "phase_scratch_rederive_answers_tuning", "phase_scratch_rederive_answers_mutes",
        "phase_scratch_rederive_answers_tilt", "phase_scratch_rederive_answers_levels",
        "phase_scratch_rederive_answers_refit"]
    with pytest.raises(SystemExit, match="unknown row"):
        RD.answers_key("xn-list")
    assert all(k.startswith(RD.KEY_PREFIX + "_") for k in RD.KEYS_TO_COME) and len(set(RD.KEYS_TO_COME)) == 12
    assert RD.ELEMENTS == ("tuning", "mutes", "tilt", "levels") and RD.INPUTS == ("in-F", "in-M", "in-U")
    assert RD.DECIDING_INPUT == "in-M" and RD.DECIDING == ("bks", "goat") and (RD.SMALL, RD.BIG) == (0.05, 0.10)
    assert RD.RUNG_ROWS == ("xf-tuning", "xf-mutes", "xf-tilt", "xf-levels")
    assert RD.LADDER_WRITES == ("xf-now",) + RD.RUNG_ROWS and RD.REAL_ROW == "fs-refit" and RD.REAL_BUILD == "rf2"
    assert RD.STAGE_1 == ("xf-now",) and RD.STAGE_2 == ("xf-fix",)


def test_the_key_prefix_is_outside_every_guarded_prefix():
    pre = [p for ps in NT.KEY_PREFIXES.values() for p in ps]
    for k in (RD.PHASE,) + RD.KEYS_TO_COME:
        assert not k.startswith(tuple(pre)) and not k.startswith(SE.KEY_PREFIX) and not k.startswith("phase_fs")
        assert not k.startswith("phase_scratch_readerr")
        assert not S.fs_keys({k: 1}) and not NT.guarded_keys({k: 1}, pre)
        assert SE.keys_refusal({k: 1}, {}) is None                   # scratch_exact's guard never sees these keys
    RD.tables_guard()


def test_the_pinned_files_hold_scratch_exacts_and_the_redos():
    assert set(SE.CODE_FILES) <= set(RD.PINNED) and set(NT.CODE_FILES) <= set(RD.PINNED)
    assert "learn/scratch_exact.py" in RD.PINNED and "learn/song_bank.py" in RD.PINNED
    assert {"learn/di_robustness.py", "learn/direc_check.py", "learn/confirm_run.py"} <= set(RD.PINNED)
    assert RD.CODE_FILES[0] == "learn/scratch_rederive.py" and len(set(RD.CODE_FILES)) == len(RD.CODE_FILES)
    for f in RD.CODE_FILES:
        assert (REPO / f).exists(), f


def test_the_module_imports_only_the_standard_library_at_module_level():
    tree = ast.parse((REPO / "learn" / "scratch_rederive.py").read_text())
    mods = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module.split(".")[0])
    assert mods <= {"__future__", "argparse", "itertools", "json", "math", "pathlib", "statistics", "time", "learn"}


# --- the cells ----------------------------------------------------------------------------------------------------------------

T0 = {"tuning": 3.0, "mutes": [1.0, 2.0], "tilt": 5.0, "levels": [0.5, -0.5, 1.0]}
R0 = {"tuning": 1.0, "mutes": [1.0, 2.5, 3.0], "tilt": -2.0, "levels": [0.0, 0.0, 2.0]}


def test_the_sixteen_value_cells():
    assert len(RD.VALUE_CELLS) == len(set(RD.VALUE_CELLS)) == 16
    assert RD.VALUE_CELLS[0] == RD.TODAY == "RRRR" and RD.VALUE_CELLS[-1] == RD.TRUE == "TTTT"
    assert RD.cell_true("TRRT") == ("tuning", "levels") and RD.cell_true(RD.TODAY) == ()
    assert RD.cell_values(T0, R0, RD.TODAY) == R0 and RD.cell_values(T0, R0, RD.TRUE) == T0
    v = RD.cell_values(T0, R0, "RTRR")
    assert v == {"tuning": 1.0, "mutes": [1.0, 2.0], "tilt": -2.0, "levels": [0.0, 0.0, 2.0]}
    with pytest.raises(ValueError):
        RD.cell_true("RRR")
    seen = {tuple(RD.cell_true(c)) for c in RD.VALUE_CELLS}
    assert len(seen) == 16                                           # every subset of the four elements once


def test_a_chain_cell_gives_one_element_only():
    assert RD.CHAIN_CELLS == RD.ELEMENTS
    for e in RD.ELEMENTS:
        assert RD.chain_fixed(T0, e) == {e: T0[e]}
    with pytest.raises(ValueError):
        RD.chain_fixed(T0, "finish")


def test_values_keys_and_json():
    assert RD.values_key(T0) == RD.values_key(json.loads(json.dumps(RD.values_json(T0))))
    assert RD.values_key(T0) != RD.values_key(R0)
    assert RD.values_key(dict(T0, mutes=(1.0, 2.0))) == RD.values_key(T0)


def test_mute_errors_match_within_30_ms():
    assert RD.MUTE_MATCH_S == NR.MUTE_FADE_S == 0.030
    e = RD.mute_errors([1.0, 2.0, 4.0], [1.02, 2.5, 3.0, 4.03])
    assert e == {"true": 3, "got": 4, "extra": 2, "missed": 1, "identical": False}
    assert RD.mute_errors([1.0], [1.0])["identical"] and RD.mute_errors([], []) == {
        "true": 0, "got": 0, "extra": 0, "missed": 0, "identical": True}
    two = RD.mute_errors([1.0], [0.99, 1.01])                          # not one-to-one: both count as found
    assert two["extra"] == 0 and two["missed"] == 0


def test_value_errors():
    e = RD.value_errors(T0, R0)
    assert e["tuning_cents"] == 2.0 and e["tilt_db_s"] == 7.0 and e["tilt_part"] and not e["identical"]
    assert e["levels_db"] == [0.5, 0.5, 1.0] and e["levels_median_db"] == 0.5
    assert e["mutes"]["extra"] == 2 and e["mutes"]["missed"] == 1
    z = RD.value_errors(dict(T0, tilt=0.0), dict(T0, tilt=0.0))
    assert z["identical"] and not z["tilt_part"] and z["tuning_cents"] == 0.0
    with pytest.raises(ValueError, match="onset groups"):
        RD.value_errors(T0, dict(R0, levels=[0.0]))


# --- the bench table, two stages -------------------------------------------------------------------------------------------

def test_the_tables_are_the_declared_ones():
    assert RD.XF_CODES == ("XF-anomaly", "XF-input", "XF-worse", "XF-closed", "XF-part", "XF-undecided", "XF-other")
    assert RD.RF_CODES == ("RF-anomaly", "RF-closer", "RF-worse", "RF-undecided", "RF-other")
    RD.tables_guard()


def test_the_tables_guard_refuses_a_broken_table(monkeypatch):
    monkeypatch.setattr(RD, "XF_CODES", RD.XF_CODES[1:])
    with pytest.raises(SystemExit, match="XF_TABLE"):
        RD.tables_guard()
    monkeypatch.undo()
    monkeypatch.setattr(RD, "RF_CODES", RD.RF_CODES[::-1])
    with pytest.raises(SystemExit, match="RF_TABLE"):
        RD.tables_guard()
    monkeypatch.undo()
    monkeypatch.setattr(RD, "XF_TABLE", tuple((c, (2,) if c == "XF-input" else s, *r) for c, s, *r in RD.XF_TABLE))
    with pytest.raises(SystemExit, match="stages"):
        RD.tables_guard()
    monkeypatch.undo()
    monkeypatch.setattr(RD, "KEY_PREFIX", "phase_scratch_exact_rederive")
    with pytest.raises(SystemExit, match="guarded prefix"):
        RD.tables_guard()


def test_stage_1_reads_xf_now_only():
    assert RD.xf_stage1(BELOW)["code"] == "XF-anomaly"
    s = RD.xf_stage1(SPANS)
    assert s["code"] == "XF-input" and "hi90 = 0.2" in s["reading"] and "xf-fix does not run" in s["next"]
    assert RD.xf_stage1(EDGE_LO)["code"] == "XF-input" and RD.xf_stage1(EDGE_HI)["code"] == "XF-input"
    go = RD.xf_stage1(ABOVE)
    assert go["code"] is None and go["go_on"] and go["next"] == RD.GO_ON
    for bad in BAD:
        assert RD.xf_stage1(bad)["code"] == "XF-other"


def test_stage_2_only_after_stage_1_went_on():
    for d_now in (BELOW, SPANS) + BAD:
        with pytest.raises(SystemExit, match="stage 1 went on"):
            RD.xf_stage2(d_now, SPANS, BELOW)
    assert RD.xf_stage2(ABOVE, BELOW, BELOW)["code"] == "XF-anomaly"       # D_fix below zero first
    assert RD.xf_stage2(ABOVE, ABOVE, ABOVE)["code"] == "XF-worse"
    c = RD.xf_stage2(ABOVE, SPANS, BELOW)
    assert c["code"] == "XF-closed" and "hi90 = 0.2" in c["reading"] and c["next"] == "the bridge runs"
    assert RD.xf_stage2(ABOVE, ABOVE, BELOW)["code"] == "XF-part"
    assert RD.xf_stage2(ABOVE, ABOVE, SPANS)["code"] == "XF-undecided"
    assert RD.xf_stage2(ABOVE, SPANS, SPANS)["code"] == "XF-undecided"
    for bad in BAD:
        assert RD.xf_stage2(ABOVE, bad, BELOW)["code"] == "XF-other"
        assert RD.xf_stage2(ABOVE, SPANS, bad)["code"] == "XF-other"


def test_every_bench_case_ends_in_exactly_one_code():
    """Every combination of D_now, D_fix and the gain (below, spanning, above, an end at zero, and every malformed
    form) ends in exactly one declared code: stage 1's when it ends there (D_fix and the gain unread), else stage
    2's; the first row that holds, in the table's order."""
    stage1 = {c for c, s, *_ in RD.XF_TABLE if 1 in s}
    stage2 = {c for c, s, *_ in RD.XF_TABLE if 2 in s}
    seen = set()
    for d_now, d_fix, gain in itertools.product(CASES, repeat=3):
        r = RD.xf_read(d_now, d_fix, gain)
        assert r["code"] in RD.XF_CODES
        seen.add(r["code"])
        s1 = RD.xf_stage1(d_now)
        if not s1["go_on"]:
            assert r == s1 and r["code"] in stage1 and r["stage"] == 1
            assert RD.xf_read(d_now) == s1                           # stage 1 needs neither D_fix nor the gain
        else:
            assert r["code"] in stage2 and r["stage"] == 2
            holds = [c for c, ok in (
                ("XF-anomaly", RD.wholly_below(d_fix)), ("XF-worse", RD.wholly_above(gain)),
                ("XF-closed", RD.wholly_below(gain) and RD.spans_zero(d_fix)),
                ("XF-part", RD.wholly_below(gain) and RD.wholly_above(d_fix)), ("XF-undecided", RD.spans_zero(gain)))
                     if ok and RD.iv_ok(d_fix) and RD.iv_ok(gain)]
            assert r["code"] == (holds[0] if holds else "XF-other")
    assert seen == set(RD.XF_CODES)


# --- the real-song table -----------------------------------------------------------------------------------------------------

def test_the_real_table():
    assert RD.rf_code(BELOW, BELOW)["code"] == "RF-anomaly"                # beats row (b): first
    assert RD.rf_code(ABOVE, BELOW)["code"] == "RF-closer"
    assert RD.rf_code(ABOVE, ABOVE)["code"] == "RF-worse"
    u = RD.rf_code(ABOVE, SPANS)
    assert u["code"] == "RF-undecided" and not u["level_not_readable"] and "hi90 = 0.2" in u["next"]
    lv = RD.rf_code(ABOVE, _iv(0.0, -0.04, 0.05))
    assert lv["code"] == "RF-undecided" and lv["level_not_readable"] and "level, not readable" in lv["reading"]
    assert RD.rf_code(SPANS, EDGE_LO)["code"] == "RF-undecided"
    for bad in BAD:
        assert RD.rf_code(bad, BELOW)["code"] == "RF-other" and RD.rf_code(ABOVE, bad)["code"] == "RF-other"


def test_every_real_case_ends_in_exactly_one_code():
    seen = set()
    for d_vs_b, d_real in itertools.product(CASES, repeat=2):
        r = RD.rf_code(d_vs_b, d_real)
        seen.add(r["code"])
        ok = RD.iv_ok(d_vs_b) and RD.iv_ok(d_real)
        holds = [c for c, h in (("RF-anomaly", RD.wholly_below(d_vs_b)), ("RF-closer", RD.wholly_below(d_real)),
                                ("RF-worse", RD.wholly_above(d_real)), ("RF-undecided", RD.spans_zero(d_real)))
                 if h and ok]
        assert r["code"] == (holds[0] if holds else "RF-other")
    assert seen == set(RD.RF_CODES)


def test_the_interval_shapes_are_exclusive_on_usable_intervals():
    for iv in (BELOW, SPANS, ABOVE, EDGE_LO, EDGE_HI):
        assert RD.iv_ok(iv) and [RD.wholly_below(iv), RD.spans_zero(iv), RD.wholly_above(iv)].count(True) == 1
    for bad in BAD:
        assert not RD.iv_ok(bad) and not (RD.wholly_below(bad) or RD.spans_zero(bad) or RD.wholly_above(bad))


# --- the fit's declared constants --------------------------------------------------------------------------------------------

def test_the_fits_tolerances_trace_to_the_code():
    f = RD.FIT
    assert f["candidates"] == len(f["domains"]) * len(f["passes"]) * len(f["mutes"]) == 12
    assert f["domains"] == ("unfinished", "measured", "finished") and f["passes"] == ("one", "iterated")
    assert f["mutes"] == ("as-now", "veto") and f["mute_veto_s"] == NR.MUTE_FADE_S == 0.030
    assert f["repeat_tuning_cents"] == 0.1 / 2                       # Bank.note keys on round(cents, 1)
    span = (sum(NR.TILT_LATE) - sum(NR.TILT_EARLY)) / 2
    assert span == pytest.approx(0.375) and f["repeat_tilt_db_s"] == round(0.01 / span, 3)
    assert f["repeat_level_db"] == 0.01 and f["max_passes"] == 64 and f["cycle_match"] == "within the repeat tolerances"
    assert "within the repeat tolerances" in f["cycle"] and "build-real" in f["safety_stop"]      # amendment 5
    assert f["simpler"].startswith("today's rule first") and "in-M" in f["deciding_measure"]


# --- the summary (pure) ------------------------------------------------------------------------------------------------------

def _rec(logmel, same_now, tilt_err):
    cell = {"logmel_to_x": logmel, "identical_to_x": False, "identical_to_now": True}
    errs = {"tuning_cents": 1.0, "tilt_db_s": tilt_err, "tilt_part": tilt_err > 0, "levels_db": [1.0, 2.0],
            "mutes": {"true": 2, "got": 3, "extra": 1, "missed": 0}, "identical": False}
    return {"errors": errs, "value": {c: dict(cell, identical_to_x=c == RD.TRUE) for c in RD.VALUE_CELLS},
            "chain": {e: dict(cell, identical_to_now=same_now) for e in RD.CHAIN_CELLS}}


def test_the_ladder_summary_counts():
    parts = {"bks__k1": {"inputs": {u: _rec(2.0, False, 4.0) for u in RD.INPUTS}},
             "goat__k2": {"inputs": {u: _rec(4.0, True, 0.0) for u in RD.INPUTS}}}
    s = RD.ladder_summary(parts, sorted(parts))["in-M"]
    assert s["today_logmel_to_x_mean"] == 3.0 and s["tilt_parts"] == 1 and s["tilt_error_mean_db_s"] == 4.0
    assert s["level_error_median_db"] == 1.5 and (s["mutes_extra"], s["mutes_missed"]) == (2, 0)
    assert s["value_cells"][RD.TRUE]["identical_to_x"] == 2 and s["value_cells"][RD.TODAY]["identical_to_x"] == 0
    assert all(s["chain_cells"][e]["changed_from_today"] == 1 for e in RD.CHAIN_CELLS)


# --- the guards and the refusals ---------------------------------------------------------------------------------------------

def test_the_keys_refusal_covers_both_prefixes():
    assert RD.keys_refusal({"phase_scratch_rederive": 1, "phase_fs": 2}, {"phase_scratch_rederive": 1}) is None
    assert "phase_scratch_rederive_ladder" in RD.keys_refusal({"phase_scratch_rederive_ladder": {}}, {})
    assert "phase_scratch_exact_outcome" in RD.keys_refusal({}, {"phase_scratch_exact_outcome": {}})


def _args(**kw):
    return type("A", (), dict(kw))()


@pytest.mark.parametrize("cmd", sorted(RD.COMMANDS))
def test_every_command_refuses_off_main(monkeypatch, cmd):
    monkeypatch.setattr(S, "on_main", lambda: (None, "this checkout's learn/scratch_search.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        RD.COMMANDS[cmd](_args())


MAIN_BEFORE = {S.PHASE: 1, S.PHASE_DRAW: {}, SE.PHASE_BANK: {}, SE.PHASE: {}, SE.PHASE_TARGETS: {}}


@pytest.mark.parametrize("cmd", sorted(RD.COMMANDS))
def test_every_command_refuses_without_the_declaration_or_the_bench(monkeypatch, cmd):
    main = dict(MAIN_BEFORE)
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    with pytest.raises(SystemExit, match="has no phase_scratch_rederive"):
        RD.COMMANDS[cmd](_args())
    main[RD.PHASE] = {}
    del main[SE.PHASE_TARGETS]
    with pytest.raises(SystemExit, match="has no phase_scratch_exact_targets"):
        RD.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", sorted(RD.COMMANDS))
def test_every_command_refuses_with_other_code_or_keys(monkeypatch, cmd):
    from learn import note_replay as NRP

    main = dict(MAIN_BEFORE, **{RD.PHASE: {}})
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    monkeypatch.setattr(RD, "pinned_identity", lambda: {"learn/scratch_exact.py": False, "learn/x.py": True})
    with pytest.raises(SystemExit, match="scratch_exact.py.*differ from main's"):
        RD.COMMANDS[cmd](_args())
    monkeypatch.setattr(RD, "pinned_identity", lambda: {f: True for f in RD.CODE_FILES})
    monkeypatch.setattr(NRP, "ledger_entry", lambda: dict(main, phase_scratch_rederive_ladder={}))
    with pytest.raises(SystemExit, match="phase_scratch_rederive_ladder"):
        RD.COMMANDS[cmd](_args())


def test_the_ladder_never_overwrites_its_record(monkeypatch, tmp_path):
    monkeypatch.setattr(RD, "require_rederive", lambda *a: {})
    monkeypatch.setattr(RD, "rederive_dir", lambda: tmp_path)
    RD.ladder_path().write_text("{}")
    with pytest.raises(SystemExit, match="never overwritten"):
        RD.cmd_ladder(_args())


def test_the_paths_sit_apart_from_the_exact_tests():
    for row in RD.LADDER_WRITES:
        p = RD.dry_path(row, "bks__k/1")
        assert p.parent.parent.parent == RD.rederive_dir() and p.name == "bks__k__1.npy" and p.parent.name == row
    assert RD.rederive_dir().name == "rederive" and RD.rederive_dir().parent == S.fs_dir()
    assert RD.rederive_dir() != SE.exact_dir()
    for row in ("xf-fix", "xn-list", "fs-refit"):
        with pytest.raises(ValueError):
            RD.dry_path(row, "k")


def test_the_cli_knows_only_the_ladder():
    assert sorted(RD.COMMANDS) == ["ladder"]
    with pytest.raises(SystemExit):
        RD.main(["converge"])


# --- derive, compose, input_form against rebuild_redo (numpy; skipped on the light runner) ------------------------------------

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


def _world(amp=False):
    """A made-up part: eight notes, isolated enough for a tilt, a DI with a mute and an uneven level per group."""
    np = _needs()
    SR = NR.SR
    notes = [{"on": 0.4 + 0.75 * k, "off": 0.4 + 0.75 * k + 0.6, "pitch": 52 + (k * 5) % 12, "bends": [],
              **({"amp": 0.4 + 0.1 * (k % 5)} if amp else {})} for k in range(8)]
    n = int(6.5 * SR)
    di, _ = NR.synthesise_redo(notes, n, _bank(), 7.0, "ring-soft", mutes=[2.0], tilt_db_s=-4.0,
                               group_gain_db=[(-1) ** k * 2.0 for k in range(8)])
    di = di * (1 + 0.3 * np.random.default_rng(3).random(n))
    return notes, n, di


def _half(y):
    return 0.5 * y


def _sha(np, y):
    return __import__("hashlib").sha256(np.ascontiguousarray(y, np.float64).tobytes()).hexdigest()


@pytest.mark.parametrize("loud", [None, 1.0])
def test_derive_then_compose_is_rebuild_redo_byte_for_byte(loud):
    np = _needs()
    notes, n, di = _world(amp=loud is not None)
    for finish in (None, _half):
        want, _ = NR.rebuild_redo("tr-di", notes, n, _bank(), di, "ring-soft", finish=finish, loud=loud)
        v, rep = RD.derive(notes, n, _bank(), di, "ring-soft", loud)
        got, crep = RD.compose(notes, n, _bank(), "ring-soft", finish, v, loud)
        assert _sha(np, got) == _sha(np, want) and rep["given"] == []
        assert v["tuning"] == NR.global_tuning_cents(di) and v["mutes"] == NR.mute_times(di)
        assert len(v["levels"]) == len(NR.onset_groups(notes)) and crep["lufs"] == NR.ASSUMED_LUFS


def test_given_values_are_kept_and_the_later_ones_rederived():
    _needs()
    notes, n, di = _world()
    R, _ = RD.derive(notes, n, _bank(), di, "ring-soft")
    T = {"tuning": R["tuning"] + 3.0, "mutes": [1.1], "tilt": 2.5, "levels": [0.3 * k for k in range(len(R["levels"]))]}
    every, rep = RD.derive(notes, n, _bank(), di, "ring-soft", fixed=T)
    assert every == T and rep == {"tilt": None, "given": list(sorted(RD.ELEMENTS))}
    c = {e: RD.derive(notes, n, _bank(), di, "ring-soft", fixed=RD.chain_fixed(T, e))[0] for e in RD.CHAIN_CELLS}
    assert c["levels"] == RD.cell_values(T, R, "RRRT")               # the last element: its value cell
    assert c["tilt"]["tuning"] == R["tuning"] and c["tilt"]["mutes"] == R["mutes"] and c["tilt"]["tilt"] == 2.5
    assert c["tilt"]["levels"] != R["levels"]                         # re-derived after the true tilt
    assert c["tuning"]["tuning"] == T["tuning"] and c["tuning"]["mutes"] == R["mutes"]
    assert c["mutes"]["mutes"] == [1.1] and c["mutes"]["tuning"] == R["tuning"]
    with pytest.raises(ValueError, match="unknown elements"):
        RD.derive(notes, n, _bank(), di, "ring-soft", fixed={"finish": 1})


def test_the_three_input_forms():
    np = _needs()
    notes, n, di = _world()
    T, _ = RD.derive(notes, n, _bank(), di, "ring-soft")
    raw = RD.unfinished(notes, n, _bank(), "ring-soft", T)
    y, _ = NR.synthesise_redo(notes, n + int(round(NR.END_PAD_S * NR.SR)), _bank(), T["tuning"], "ring-soft",
                              T["mutes"], T["tilt"], T["levels"])
    assert _sha(np, raw) == _sha(np, NR.denoise_above(y)[:n]) and len(raw) == n
    f = RD.input_form("in-F", notes, n, _bank(), "ring-soft", T, di, _half)
    x, _ = NR.rebuild_redo("tr-di", notes, n, _bank(), di, "ring-soft", finish=_half)
    assert f.dtype == np.float64 and _sha(np, f) == _sha(np, np.asarray(np.asarray(x, np.float32), np.float64))
    m = RD.input_form("in-M", notes, n, _bank(), "ring-soft", T, di, _half, measure=lambda a: 3.0 * a, raw=raw)
    assert _sha(np, m) == _sha(np, np.asarray(np.asarray(3.0 * raw, np.float32), np.float64))
    assert m.dtype == np.float64 and np.array_equal(m, m.astype(np.float32))      # di_section's float32 rounding
    assert not np.array_equal(m, 3.0 * raw)                                     # ... is applied, not skipped
    u = RD.input_form("in-U", notes, n, _bank(), "ring-soft", T, di, raw=raw)
    assert np.sqrt(np.mean(u ** 2)) == pytest.approx(np.sqrt(np.mean(di ** 2)), rel=1e-9)
    k = np.sqrt(np.mean(di ** 2)) / (np.sqrt(np.mean(raw ** 2)) + 1e-12)
    assert _sha(np, u) == _sha(np, raw * k)                           # unfinished: only the level moves
    with pytest.raises(ValueError):
        RD.input_form("in-X", notes, n, _bank(), "ring-soft", T, di)


def test_the_cells_and_the_two_identities_on_a_made_up_part():
    """The ladder's proofs in miniature: T from the DI composes the DI's own rebuild (X); today's rule handed X (in-F)
    is `rebuild_redo` handed X; the all-true cell is X in every input form; today's cell is `rebuild_redo` on that
    form."""
    np = _needs()
    notes, n, di = _world()
    T, _ = RD.derive(notes, n, _bank(), di, "ring-soft")
    X, _ = NR.rebuild_redo("tr-di", notes, n, _bank(), di, "ring-soft", finish=_half)
    X32 = np.asarray(X, np.float32)
    f = RD.input_form("in-F", notes, n, _bank(), "ring-soft", T, di, _half)
    assert S.npy_sha(f) == S.npy_sha(X32)
    raw = RD.unfinished(notes, n, _bank(), "ring-soft", T)
    for u in (f, RD.input_form("in-U", notes, n, _bank(), "ring-soft", T, di, raw=raw)):
        L = RD.cells(notes, n, _bank(), "ring-soft", _half, T, u)
        assert sorted(L["value"]) == sorted(RD.VALUE_CELLS) and sorted(L["chain"]) == sorted(RD.CHAIN_CELLS)
        assert S.npy_sha(L["value"][RD.TRUE][0]) == S.npy_sha(X32)
        today, _ = NR.rebuild_redo("tr-di", notes, n, _bank(), u, "ring-soft", finish=_half)
        assert S.npy_sha(L["value"][RD.TODAY][0]) == S.npy_sha(today)
        assert S.npy_sha(L["chain"]["levels"][0]) == S.npy_sha(L["value"]["RRRT"][0])
        assert L["value"][RD.TODAY][1] == L["R"] and 1 <= L["distinct"] <= 16 + 3
        every = list(L["value"].values()) + list(L["chain"].values())
        assert all(y.dtype == np.float32 and len(y) == n for y, _v in every)


def test_a_guitar_is_written_once(tmp_path):
    np = _needs()
    y = np.linspace(-0.5, 0.5, 1000).astype(np.float32)
    p = tmp_path / "xf-now" / "k.npy"
    sha = RD._write_once(p, y)
    assert sha == S.npy_sha(y) == S.file_sha(p)
    assert RD._write_once(p, y) == sha                                 # a rerun after a stop: the same samples
    with pytest.raises(SystemExit, match="never overwritten"):
        RD._write_once(p, y * 2)


def _fake_ladder_world(monkeypatch, tmp_path, list_ok=True):
    """`cmd_ladder` on one made-up part, every data source and guard stood in for: the true DI, X (its own rebuild,
    as build 2 made it), `xn-list` (today's rule handed X), a stand-in measure step."""
    np = _needs()
    from learn import note_fixes as NF
    from learn import song_bank as SB

    notes, n, di = _world()
    bank = _bank()
    key = "bks__unit-1@0.0|amp-1"
    X32 = np.asarray(NR.rebuild_redo("tr-di", notes, n, bank, di, "ring-soft", finish=_half)[0], np.float32)
    L32 = np.asarray(NR.rebuild_redo("tr-di", notes, n, bank, np.asarray(X32, np.float64), "ring-soft",
                                     finish=_half)[0], np.float32)
    b2 = {"fixes": ["F1"], "ring_variant": "ring-soft", "loud_gamma": None,
          "parts": {key: {"arms": {"tr-di": {"sha256": S.npy_sha(X32)}}}}}
    xb = {"fixes": ["F1"], "ring_variant": "ring-soft", "loud_gamma": None,
          "parts": {key: {"notes": len(notes), "guitars": {"xn-list": {"sha256": S.npy_sha(L32 if list_ok else X32)},
                                                           "xn-swap": {"sha256": S.npy_sha(di)}}}}}
    (tmp_path / "b2.json").write_text(json.dumps(b2))
    (tmp_path / "xb.json").write_text(json.dumps(xb))
    monkeypatch.setattr(RD, "require_rederive", lambda *a: {})
    monkeypatch.setattr(RD, "rederive_dir", lambda: tmp_path / "rd")
    monkeypatch.setattr(RD, "pinned_identity", lambda: {f: True for f in RD.CODE_FILES})
    monkeypatch.setattr(NT, "redo_on_main", lambda: ({}, None))
    monkeypatch.setattr(SE, "bank_build", lambda m: b2)
    monkeypatch.setattr(SE, "require_xbuild", lambda m: xb)
    monkeypatch.setattr(SE, "build_path", lambda: tmp_path / "xb.json")
    monkeypatch.setattr(NT, "build_path", lambda name=None: tmp_path / "b2.json")
    monkeypatch.setattr(NT, "_dev_context", lambda: (None, None, None, None))
    monkeypatch.setattr(NT, "install_pair", lambda m: ("lock", "model"))
    monkeypatch.setattr(NT, "load_manifest", lambda: {})
    monkeypatch.setattr(NT, "ear_items_file", lambda name=None: None)
    monkeypatch.setattr(NT, "build_todo", lambda pair, ear: [("part", key, {"set": "bks"}, {"events": []}, di, _half)])
    monkeypatch.setattr(NT, "load_dry", lambda arm, k, build: X32)
    monkeypatch.setattr(NT, "timed_notes", lambda rec, d: ([dict(x) for x in notes], {}))
    monkeypatch.setattr(NF, "apply_fixes", lambda ns, fixes, d: (ns, {}))
    monkeypatch.setattr(NR, "load_notes_doc", lambda: None)
    monkeypatch.setattr(NR, "Bank", lambda doc, excl=None: bank)
    monkeypatch.setattr(SB, "measure", lambda x: 2.0 * np.asarray(x, np.float64))
    from learn import confirm_run as CR

    (tmp_path / "average.npy").write_bytes(b"made-up average")
    monkeypatch.setattr(CR, "AVERAGE", tmp_path / "average.npy")
    return key


def test_the_ladder_on_a_made_up_part(monkeypatch, tmp_path, capsys):
    np = _needs()
    key = _fake_ladder_world(monkeypatch, tmp_path)
    RD.cmd_ladder(_args())
    out = capsys.readouterr().out
    assert "in-F is X 1 of 1" in out and "is xn-list 1 of 1" in out and "rebuild_redo's 1 of 1" in out
    lad = json.loads(RD.ladder_path().read_text())
    assert lad["proofs_hold"] and lad["deciding_parts"] == 1 and lad["renders"] == 0
    assert lad["average_sha256"] == S.file_sha(tmp_path / "average.npy")       # the measure step's average file
    assert lad["proofs"] == {p: {"held": 1, "of": 1} for p in ("in_f_is_x", "today_on_in_f_is_xn_list",
                                                               "xf_now_is_rebuild_redo")}
    rec = json.loads(RD.part_path(key).read_text())
    assert lad["parts"][key]["record_sha256"] == S.file_sha(RD.part_path(key))
    assert sorted(rec["files"]) == sorted(RD.LADDER_WRITES)
    for row, f in rec["files"].items():
        y = np.load(RD.dry_path(row, key))
        assert y.dtype == np.float32 and S.file_sha(RD.dry_path(row, key)) == f["file_sha256"] == S.npy_sha(y)
    m = rec["inputs"]["in-M"]
    assert m["value"][RD.TODAY]["identical_to_now"] and m["value"][RD.TRUE]["identical_to_x"]
    assert rec["files"]["xf-now"]["audio_sha256"] == m["value"][RD.TODAY]["sha256"]
    assert all(rec["files"][f"xf-{e}"]["audio_sha256"] == m["chain"][e]["sha256"] for e in RD.CHAIN_CELLS)
    assert rec["inputs"]["in-F"]["value"][RD.TRUE]["identical_to_x"]
    assert set(lad["summary"]["the_40"]) == set(RD.INPUTS) and set(lad["summary"]["all_47"]) == set(RD.INPUTS)
    with pytest.raises(SystemExit, match="never overwritten"):
        RD.cmd_ladder(_args())


def test_the_ladder_writes_nothing_for_a_part_whose_proof_fails(monkeypatch, tmp_path, capsys):
    _needs()
    key = _fake_ladder_world(monkeypatch, tmp_path, list_ok=False)
    with pytest.raises(SystemExit, match="proofs do not hold"):
        RD.cmd_ladder(_args())
    assert "PROOF FAILED" in capsys.readouterr().out
    assert not RD.ladder_path().exists() and not RD.part_path(key).exists()
    assert not any(RD.dry_path(r, key).exists() for r in RD.LADDER_WRITES)
