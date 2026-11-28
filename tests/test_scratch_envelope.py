"""The spectral-envelope steps' core (`learn/scratch_envelope.py`, `docs/scratch-envelope-plan.md`): the names and
keys, the declared bands (20, bins 3-766, the edges), the units, XE_TABLE (each code on a grid, every interval case
ends in exactly one code, XE-anomaly on every malformed interval, the `then` field of amendment 3, the tightened labels
of amendment 4, the orchestrator's "window suffices; group undecided"), the terms (C_k + R_k = S, the passing sets),
S reproduced, the guards (every command refuses off main, without its hashes, with other code or keys, or without the
vc-own row's XW-closed or XW-part), the paths, the read body behind fakes, and the ledger entry. Made-up keys only. No
numpy: the light CI runner."""
import ast
import itertools
import json
import math
import pathlib
import subprocess
import sys

import pytest

from learn import envelope_build as EB
from learn import envelope_floors as EF
from learn import scratch_envelope as E
from learn import scratch_own as SO
from learn import scratch_search as S
from learn import scratch_voice as SV

REPO = pathlib.Path(__file__).resolve().parents[1]
SRC = (REPO / "learn" / "scratch_envelope.py").read_text()
LEDGER = json.loads((REPO / "docs" / "dev-test-ledger.json").read_text())
ENTRY = next(t for t in LEDGER["tests"] if t["test_id"] == "preset-ladder")


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


BETTER, MATCHES, WORSE, UNDECIDED = _iv(-0.3, -0.5, -0.15), _iv(0.0, -0.04, 0.04), _iv(0.3, 0.15, 0.5), \
    _iv(0.08, -0.05, 0.2)
READ = {"better": BETTER, "matches": MATCHES, "worse": WORSE, "undecided": UNDECIDED}
BAD = (None, {}, _iv(0.1, 0.2, 0.05), _iv(math.nan, -0.1, 0.1), _iv(0.0, -math.inf, 0.1),
       {"mean": 0.1, "lo90": None, "hi90": 0.2}, "x")
OK = {c: True for c in E.CHECKS}
K1, K2, K3 = "bks__fake1", "goat__fake2", "panel__fake3"          # made-up keys


def _args(**kw):
    return type("A", (), dict({"shard": (0, 3), "rerun": False, "combine": False}, **kw))()


def _ivs(**rd):
    """Intervals by reading, matches by default."""
    return {t: READ[rd.get(t, "matches")] for t in E.READ_TERMS}


# --- names, keys, imports ---------------------------------------------------------------------------------------------

def test_names_keys_and_counts():
    assert E.PHASE == "phase_scratch_envelope" and E.KEYS_TO_COME == ("phase_scratch_envelope_dry",
                                                                      "phase_scratch_envelope_outcome")
    assert E.LEDGER_ID == "preset-ladder" and E.PLAN == "docs/scratch-envelope-plan.md"
    assert E.BUILT == ("vt-part", "vt-group", "vt-win", "vt-mag", "vt-phase") and E.STORED == ("tr-di", "vc-own")
    assert E.DECIDING_SET == ("tr-di", "vc-own", "vt-part", "vt-group", "vt-win")
    assert E.READ_TERMS == ("C_part", "R_part", "C_group", "R_group", "C_win", "R_win")
    assert E.BESIDE_TERMS == ("C_mag", "R_mag", "C_phase", "R_phase")
    assert E.TERM_NAMES[0] == "S" and len(E.TERM_NAMES) == 11
    assert E.RENDERS == {"floors": 470, "repeat": 8} and sum(E.RENDERS.values()) == 478
    assert E.ID_TOL == 1e-12 and E.PROOF_TOL == 1e-9 and E.SEEN_S == (0.501, 0.399, 0.603)
    assert E.PROOFS == ("source_is_tr_di", "target_is_vc_own", "unity_is_source", "swap_is_target")
    assert (E.N_FFT, E.HOP, E.HALF, E.BINS) == (2048, 240, 1024, 1025) and E.CLAMP_DB == 20.0
    assert E.FLOOR_POWER == pytest.approx(1e-4) and E.LEAD_S == 0.002
    assert E.OWN_OPEN == ("XW-closed", "XW-part")
    assert E.UNIT_FILES == ("learn/envelope_build.py", "learn/envelope_floors.py")
    E.table_guard()


def test_no_unit_file_in_the_sound_gaps_lists():
    """The sound-gap core is pinned: no UNIT_FILES entry there; this module has its own guard."""
    for f in E.OWN_FILES:
        assert f not in SV.CODE_FILES and f not in SO.CODE_FILES
    assert set(E.PINNED) >= set(SV.CODE_FILES) | set(SO.CODE_FILES)


def test_the_modules_import_only_the_standard_library_and_learn_at_module_level():
    allowed = {"__future__", "argparse", "bisect", "json", "math", "pathlib", "statistics", "time", "learn"}
    for f in E.OWN_FILES:
        tree = ast.parse((REPO / f).read_text())
        mods = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                mods.add(node.module.split(".")[0])
        assert mods <= allowed, (f, mods - allowed)


def test_no_numpy_at_import():
    code = ("import sys; import learn.scratch_envelope, learn.envelope_build, learn.envelope_floors; "
            "print('numpy' in sys.modules, 'scipy' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["False", "False"]


def test_the_build_redefines_none_of_voice_builds_functions():
    mine = {n.name for n in ast.parse((REPO / "learn" / "envelope_build.py").read_text()).body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    theirs = {"own_windows", "window_gain", "own_gain", "edge_gain", "end_ramp", "chain", "through_gate",
              "padded_raw", "real_end", "span_mask", "support_check", "group_onsets", "same_bytes", "pad_samples",
              "code_identity", "code_refusal", "_save_once"}
    assert not mine & theirs


def test_the_cli_knows_its_commands():
    assert sorted(E.COMMANDS) == ["read"] and sorted(EB.COMMANDS) == ["build"] and sorted(EF.COMMANDS) == ["floor"]
    with pytest.raises(SystemExit):
        EF.main(["floor"])                                     # --shard is required
    with pytest.raises(SystemExit):
        EF.main(["floor", "--shard", "0/4"])
    with pytest.raises(SystemExit):
        EB.main(["build", "--shard", "0/9"])


# The brief's pinned files: this PR edits none of them
GUARDED = ("learn/scratch_voice.py", "learn/voice_build.py", "learn/voice_floors.py", "learn/voice_control.py",
           "learn/scratch_own.py", "learn/scratch_search.py", "learn/scratch_notes.py", "learn/scratch_exact.py",
           "learn/rederive_rows.py", "learn/scratch_loudar.py")


def test_the_pinned_files():
    assert set(GUARDED) <= set(E.PINNED) and E.CODE_FILES[:3] == E.OWN_FILES


def test_the_guarded_files_are_unchanged_against_the_base():
    base = subprocess.run(["git", "-C", str(REPO), "merge-base", "origin/main", "HEAD"], capture_output=True, text=True)
    if base.returncode:
        pytest.skip("no origin/main here")
    r = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", base.stdout.strip(), "HEAD", "--", *GUARDED])
    assert r.returncode == 0


# --- the bands and the units (amendment 1) ------------------------------------------------------------------------------

def test_the_declared_twenty_bands():
    bands = E.band_table()
    assert len(bands) == 20
    lo, hi = bands[0], bands[-1]
    assert (lo["bin_lo"], lo["bin_hi"]) == (3, 7) and lo["ks"] == [-12, -11, -10, -9, -8]
    assert round(lo["lo_hz"], 1) == 55.7 and round(lo["hi_hz"], 1) == 176.8
    assert round(lo["centres_hz"][0], 1) == 62.5 and round(lo["centres_hz"][-1], 1) == 157.5
    assert (hi["bin_lo"], hi["bin_hi"]) == (609, 766) and hi["ks"] == [12] and round(hi["hi_hz"], 2) == 17959.39
    assert all(b["bins"] >= E.MIN_BINS for b in bands)
    for a, b in zip(bands, bands[1:]):                               # contiguous: nothing left over
        assert b["bin_lo"] == a["bin_hi"] + 1 and b["lo_hz"] == pytest.approx(a["hi_hz"])
    assert sum(b["bins"] for b in bands) == 766 - 3 + 1
    assert [b["ks"] for b in bands[:2]] == [[-12, -11, -10, -9, -8], [-7, -6]]


def test_no_bin_sits_on_an_edge_and_the_rule_is_lo_inclusive():
    for b in E.band_table():
        for edge in (b["lo_hz"], b["hi_hz"]):
            assert all(abs(j * E.SR / E.N_FFT - edge) > 1e-6 for j in range(E.BINS))
        assert b["lo_hz"] <= b["bin_lo"] * E.SR / E.N_FFT < b["hi_hz"]
        assert b["bin_hi"] * E.SR / E.N_FFT < b["hi_hz"] <= (b["bin_hi"] + 1) * E.SR / E.N_FFT


def test_the_edge_bins():
    assert E.edge_bins() == [0, 1, 2] + list(range(767, 1025))
    of = E.band_of_bins()
    assert len(of) == E.BINS and of[3] == 0 and of[766] == 19 and of[767] == -1
    rows = E.band_rows()
    assert rows[0]["bins"] == "3-7" and rows[-1]["bins"] == "609-766" and len(rows) == 20


def test_a_short_top_band_merges_down():
    bands = E.band_table(rate=48000, n_fft=32)                     # coarse bins: 2 left at the top merge down
    assert all(b["bins"] >= E.MIN_BINS for b in bands)
    assert [k for b in bands for k in b["ks"]] == list(E.BAND_K)
    assert bands[-1]["ks"] == [9, 10, 11, 12] and bands[-1]["bins"] == 7


def test_frame_count_covers_every_sample():
    for L in (1, 239, 240, 241, 480, 496800):
        f = E.frame_count(L)
        assert (f - 1) * E.HOP <= L - 1 < f * E.HOP
        assert all(min(abs(t - E.HOP * i) for i in range(max(0, t // E.HOP - 1), min(f, t // E.HOP + 2))) < E.HOP
                   for t in (0, L - 1, L // 2))
    with pytest.raises(ValueError):
        E.frame_count(0)


def test_the_units():
    assert E.unit_ids("part", 5) == [0] * 5 and E.unit_ids("win", 4) == [0, 1, 2, 3]
    assert E.unit_ids("mag", 3) == [0, 1, 2]
    # onsets at 0.0102 s and 0.0252 s: bounds round((t - 0.002) * 48000) = 394 and 1114; centres 0, 240, ..., 1440
    u = E.unit_ids("group", 7, [0.0252, 0.0102])
    assert E.group_bounds([0.0252, 0.0102]) == [394, 1114]
    assert u == [0, 0, 1, 1, 1, 2, 2]                              # [.., 394) unit 0, [394, 1114) 1, the rest 2
    assert E.unit_ids("group", 4, [0.001]) == [0, 0, 0, 0]          # the bound at sample -48: unit 0 empty, dropped
    assert E.unit_ids("group", 3, []) == [0, 0, 0]                  # no onset: one unit
    assert E.unit_ids("group", 6, [0.0072]) == [0, 0, 1, 1, 1, 1]   # bound 250: centre 240 before it, 480 after
    assert E.unit_ids("group", 3, [0.0070]) == [0, 1, 1]            # bound exactly 240: that frame opens unit 1
    with pytest.raises(ValueError):
        E.unit_ids("bar", 3)


# --- the outcome table (pure) -----------------------------------------------------------------------------------------

def _oracle(ivs, checks):
    """XE_TABLE written out independently, the first that holds (amendments 3 and 4)."""
    rd = {t: (SV.reading(ivs.get(t)) or {}).get("reading") for t in E.READ_TERMS}
    if any(checks.get(c) is not True for c in E.CHECKS) or any(rd[t] is None for t in E.READ_TERMS):
        return "XE-anomaly"
    if any(rd[t] == "better" for t in E.READ_TERMS):
        return "XE-anomaly"
    if rd["C_part"] == "worse":
        return "XE-static"
    if rd["R_group"] == "matches":
        return "XE-group"
    if rd["R_win"] == "matches" and rd["R_group"] == "worse":
        return "XE-window"
    if rd["C_win"] == "worse" and rd["R_win"] == "worse":
        return "XE-split"
    if rd["R_win"] == "worse" and rd["C_win"] == "matches":
        return "XE-detail"
    return "XE-undecided"


def test_the_table_guard_refuses_a_changed_table(monkeypatch):
    E.table_guard()
    monkeypatch.setattr(E, "XE_CODES", E.XE_CODES[:-1])
    with pytest.raises(SystemExit, match="seven declared"):
        E.table_guard()
    monkeypatch.undo()
    monkeypatch.setattr(E, "REST_CODES", E.REST_CODES[1:])
    with pytest.raises(SystemExit, match="do not split"):
        E.table_guard()
    monkeypatch.undo()
    monkeypatch.setattr(E, "KEY_PREFIX", "phase_scratch_own_envelope")
    with pytest.raises(SystemExit, match="guarded prefix"):
        E.table_guard()
    monkeypatch.undo()
    monkeypatch.setattr(E, "MIN_BINS", 5)
    with pytest.raises(SystemExit, match="20 bands"):
        E.table_guard()
    monkeypatch.undo()
    monkeypatch.setattr(E, "RENDERS", {"floors": 470, "repeat": 4})
    with pytest.raises(SystemExit, match="478"):
        E.table_guard()


def test_each_declared_code_on_a_grid():
    want = [({}, "XE-group"),
            ({"C_part": "worse"}, "XE-static"),
            ({"R_win": "matches", "R_group": "worse"}, "XE-window"),
            ({"R_group": "worse", "C_win": "worse", "R_win": "worse"}, "XE-split"),
            ({"R_group": "worse", "C_win": "matches", "R_win": "worse"}, "XE-detail"),
            ({"R_group": "worse", "C_win": "undecided", "R_win": "worse"}, "XE-undecided"),
            ({"R_group": "undecided", "R_win": "undecided"}, "XE-undecided"),
            ({"C_win": "better"}, "XE-anomaly"),
            ({"R_part": "better"}, "XE-anomaly")]
    for rd, code in want:
        assert E.xe_code(_ivs(**rd), OK)["code"] == code, rd
    assert {code for _, code in want} == set(E.XE_DECLARED)


def test_every_interval_case_ends_in_exactly_one_code():
    reads = ("better", "matches", "worse", "undecided")
    seen = set()
    for combo in itertools.product(reads, repeat=len(E.READ_TERMS)):
        ivs = {t: READ[r] for t, r in zip(E.READ_TERMS, combo)}
        r = E.xe_code(ivs, OK)
        assert r["code"] == _oracle(ivs, OK) and r["code"] in E.XE_CODES
        assert isinstance(r["said"], str) and isinstance(r["decides"], str)
        assert "{" not in r["said"] + r["decides"]
        seen.add(r["code"])
    assert seen == set(E.XE_DECLARED)


@pytest.mark.parametrize("bad", BAD)
def test_a_malformed_interval_is_an_anomaly(bad):
    for t in E.READ_TERMS:
        ivs = dict(_ivs(), **{t: bad})
        r = E.xe_code(ivs, OK)
        assert r["code"] == "XE-anomaly" and t in r["fault"] and r["then"] is None
    r = E.xe_code({}, OK)
    assert r["code"] == "XE-anomaly" and r["then"] is None


def test_a_beside_term_never_changes_the_code():
    for bad in BAD + (BETTER, WORSE):
        ivs = dict(_ivs(), C_mag=bad, R_phase=bad)
        assert E.xe_code(ivs, OK)["code"] == "XE-group"


def test_a_failed_check_is_an_anomaly_with_no_then():
    for c in E.CHECKS:
        r = E.xe_code(_ivs(C_win="better"), dict(OK, **{c: False}))
        assert r["code"] == "XE-anomaly" and c in r["fault"] and r["then"] is None
        assert r["surprises"] == ["C_win reads better"]


def test_amendment_3_the_then_field():
    r = E.xe_code(_ivs(C_win="better", R_group="worse", R_win="matches"), OK)    # a surprise, no fault
    assert r["code"] == "XE-anomaly" and r["fault"] is None and r["then"] == "XE-window"
    assert r["anomaly"] == "C_win reads better" and "the rest of the table gives XE-window" in r["said"]
    r = E.xe_code(_ivs(C_part="worse", R_group="worse", C_win="worse", R_win="worse"), OK)
    assert r["code"] == "XE-static" and r["then"] == "XE-split" and r["surprises"] == ["C_part reads worse (closes)"]
    r = E.xe_code(_ivs(C_part="worse", R_part="better"), OK)
    assert r["code"] == "XE-anomaly" and r["then"] == "XE-group"
    assert r["surprises"] == ["R_part reads better", "C_part reads worse (closes)"]
    for rd in ({}, {"R_group": "worse", "C_win": "worse", "R_win": "worse"}):
        assert E.xe_code(_ivs(**rd), OK)["then"] is None                       # no surprise: no then


def test_amendment_4_the_tightened_labels():
    # XE-window needs R_group worse: R_group undecided goes to XE-undecided with the orchestrator's text
    r = E.xe_code(_ivs(R_group="undecided", R_win="matches"), OK)
    assert r["code"] == "XE-undecided" and E.WINDOW_GROUP_UNDECIDED in r["said"]
    assert r["flags"] == [E.WINDOW_GROUP_UNDECIDED]
    assert E.WINDOW_GROUP_UNDECIDED == "window suffices; group undecided"
    assert E.xe_code(_ivs(R_group="worse", R_win="matches"), OK)["code"] == "XE-window"
    # XE-detail needs C_win matches, not merely not worse
    assert E.xe_code(_ivs(R_group="worse", R_win="worse", C_win="matches"), OK)["code"] == "XE-detail"
    r = E.xe_code(_ivs(R_group="worse", R_win="worse", C_win="undecided"), OK)
    assert r["code"] == "XE-undecided" and E.WINDOW_GROUP_UNDECIDED not in r["said"]
    # XE-split: "buys about C_win, an estimate", never "at most"
    s = E.xe_code(_ivs(R_group="worse", R_win="worse", C_win="worse", C_group="undecided"), OK)
    assert s["code"] == "XE-split" and "about C_win" in s["said"] and "at most" not in s["said"]
    assert "C_group reads undecided" in s["said"]


def test_amendment_5_every_decides_carries_the_goal_wording():
    for code, _when, _said, decides in E.XE_TABLE:
        if code in ("XE-anomaly", "XE-undecided"):
            continue
        assert E.ORACLE in decides
    assert "oracle" in E.ORACLE and "not priced" in E.ORACLE and "its own go" in E.ORACLE and "concave" in E.ORACLE
    grp = next(r for r in E.XE_TABLE if r[0] == "XE-group")
    assert "not a bound on a bank" in grp[3] and "attacks and articulation" in grp[3]


def test_the_window_step_artefact_flag_is_beside():
    r = E.xe_code(_ivs(R_group="matches", R_win="worse"), OK)
    assert r["code"] == "XE-group" and r["flags"] == [E.WINDOW_ARTEFACT]


def test_the_undecided_row_names_the_intervals():
    r = E.xe_code(_ivs(R_group="undecided", R_win="undecided"), OK)
    assert "R_win -0.050 to +0.200" in r["decides"] and "R_group -0.050 to +0.200" in r["decides"]


# --- the terms ----------------------------------------------------------------------------------------------------------

def _floors(**over):
    d = {"tr-di": 2.0, "vc-own": 1.2, "vt-part": 1.99, "vt-group": 1.7, "vt-win": 1.4, "vt-mag": 1.5, "vt-phase": 1.9}
    d.update(over)
    return d


def test_c_plus_r_is_s_to_1e_12():
    t = E.part_terms(_floors())
    assert t["S"] == math.log(2.0 / 1.2)
    for s in E.STEPS:
        assert abs(t[f"C_{s}"] + t[f"R_{s}"] - t["S"]) <= E.ID_TOL
        assert E.identity_gap(t, s) <= E.ID_TOL
    assert E.part_terms({"tr-di": 2.0})["S"] is None


def test_one_passing_set_for_the_code_and_the_beside_steps_on_their_own():
    floors = {K1: _floors(), K2: _floors(**{"vt-group": None}), K3: _floors(**{"vt-mag": math.inf})}
    vals, refused, beside, gaps = E.term_values(floors)
    assert sorted(refused) == [K2] and "vt-group" in refused[K2]
    assert K2 not in vals["S"] and K2 not in vals["C_win"] and K2 in vals["C_mag"]      # a beside step on its own set
    assert sorted(beside["mag"]) == [K3] and K3 in vals["C_win"] and K3 not in vals["C_mag"]
    assert K3 in vals["C_phase"] and beside["phase"] == {}
    assert E.identity_holds(gaps)
    gaps["win"][K1] = 1e-9
    assert not E.identity_holds(gaps)
    assert not E.identity_holds({s: {} for s in E.STEPS})


def test_s_reproduces_from_the_stored_files():
    s = {"aaa": 0.5, "bbb": 0.4}
    iv = _iv(0.5011, 0.3991, 0.6031)
    r = E.s_reproduces(s, dict(s), iv, dict(iv))
    assert r["holds"] and r["per_part"] and r["stored"] and r["seen"]
    assert not E.s_reproduces(s, {"aaa": 0.5, "bbb": 0.41}, iv, dict(iv))["holds"]
    assert not E.s_reproduces(s, dict(s), iv, _iv(0.5, 0.39, 0.6))["holds"]
    assert not E.s_reproduces(s, dict(s), _iv(0.6, 0.5, 0.7), _iv(0.6, 0.5, 0.7))["holds"]
    assert not E.s_reproduces(s, None, iv, iv)["holds"]


def test_proof_failures():
    assert E.proof_failures({p: True for p in E.PROOFS}) == []
    assert E.proof_failures({"source_is_tr_di": True, "unity_is_source": 1}) == ["target_is_vc_own",
                                                                                "unity_is_source", "swap_is_target"]


# --- the guards: every command refuses ---------------------------------------------------------------------------------

COMMANDS = (("read", E.cmd_read, E.PHASES["read"]), ("build", EB.cmd_build, E.PHASES["build"]),
            ("floor", EF.cmd_floor, E.PHASES["floor"]))


@pytest.mark.parametrize("name,cmd,phases", COMMANDS)
def test_every_command_refuses_off_main(monkeypatch, name, cmd, phases):
    monkeypatch.setattr(S, "on_main", lambda: (None, "this checkout's learn/scratch_search.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        cmd(_args())


@pytest.mark.parametrize("name,cmd,phases", COMMANDS)
def test_every_command_refuses_without_its_hashes_on_main(monkeypatch, name, cmd, phases):
    from learn import note_replay as NRP

    main = {}
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    monkeypatch.setattr(NRP, "ledger_entry", lambda: main)
    monkeypatch.setattr(E, "pinned_identity", lambda: {f: True for f in E.CODE_FILES})
    for k in E.BASE + phases:
        with pytest.raises(SystemExit, match=f"has no {k}:"):
            cmd(_args())
        main[k] = {}
    with pytest.raises(SystemExit, match="run only under"):                         # the vc-own row's code
        cmd(_args())


@pytest.mark.parametrize("name,cmd,phases", COMMANDS)
def test_every_command_refuses_with_other_code_or_keys(monkeypatch, name, cmd, phases):
    from learn import note_replay as NRP

    main = {k: {} for k in E.BASE + phases}
    main[SO.PHASE_OUTCOME] = {"code": "XW-part"}
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    monkeypatch.setattr(NRP, "ledger_entry", lambda: main)
    monkeypatch.setattr(E, "pinned_identity", lambda: {E.MODULE: True, "learn/voice_build.py": False})
    with pytest.raises(SystemExit, match="voice_build.py.*differ from main's"):
        cmd(_args())
    monkeypatch.setattr(E, "pinned_identity", lambda: {f: True for f in E.CODE_FILES})
    for extra in ({"phase_scratch_envelope_dry": {"sha256": "a"}}, {"phase_scratch_own_answers": {"x": 1}},
                  {"phase_scratch_voice_waiver": {"x": 1}}):
        k = next(iter(extra))
        monkeypatch.setattr(NRP, "ledger_entry", lambda extra=extra: dict(main, **extra))
        with pytest.raises(SystemExit, match=f"{k}.*differ from main's"):
            cmd(_args())


def test_the_steps_run_only_under_xw_closed_or_xw_part():
    for c in E.OWN_OPEN:
        assert E.outcome_refusal({SO.PHASE_OUTCOME: {"code": c}}) is None
    for c in ("XW-anomaly", "XW-worse", "XW-level", "XW-undecided", None):
        assert E.outcome_refusal({SO.PHASE_OUTCOME: {"code": c}})
    assert E.outcome_refusal({}) and E.outcome_refusal(None)


def test_the_guards_run_before_numpy_or_any_render():
    code = ("import sys; from learn import scratch_envelope as E, envelope_floors as EF, envelope_build as EB\n"
            "def no(*a): raise SystemExit('refused')\n"
            "E.require_envelope = no\n"
            "EF.EnvelopeWorld.render = lambda *a: print('RENDERED')\n"
            "for f, argv in ((EF.main, ['floor', '--shard', '0/3']), (EB.main, ['build', '--shard', '0/3']), "
            "(E.main, ['read'])):\n"
            "    try:\n        f(argv)\n    except SystemExit as e:\n        print(e)\n"
            "print('numpy' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["refused", "refused", "refused", "False"]


def test_keys_refusal_reads_only_its_own_keys():
    assert E.keys_refusal({"phase_scratch_envelope": 1, "x": 1}, {"phase_scratch_envelope": 1}) is None
    assert "phase_scratch_envelope_dry" in E.keys_refusal({"phase_scratch_envelope_dry": 1}, {})


# --- paths --------------------------------------------------------------------------------------------------------------

def test_the_paths_sit_under_pf_fs_envelope(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "fs_dir", lambda: tmp_path / "fs")
    for f, folder in ((E.floor_path, "floors"), (E.first_path, "floors-first"), (E.repeat_path, "repeat"),
                      (E.part_path, "build-parts")):
        p = f("bks/fake1")
        assert p.parent.name == folder and p.parent.parent == tmp_path / "fs" / "envelope" and "bks__fake1" in p.name
    assert E.dry_path("vt-win", "bks/fake1").parent == tmp_path / "fs" / "envelope" / "dry" / "vt-win"
    with pytest.raises(ValueError):
        E.dry_path("vc-own", "bks/fake1")
    for p in (E.build_path(), E.rows_path(), E.report_path()):
        assert p.parent == tmp_path / "fs" / "envelope"
    assert SO.is_forbidden(E.floor_path("bks/fake1")) and SO.is_forbidden(E.dry_path("vt-mag", "bks/fake1"))


# --- the read (pure parts, fakes) ----------------------------------------------------------------------------------------

def test_floors_of_refuses_a_malformed_record():
    build = {"parts": {K1: {"guitars": {g: {"audio_sha256": g * 3} for g in E.BUILT}}}}
    stored = {K1: {"tr-di": {"held": 2.0}, "vc-own": {"held": 1.5}}}
    gs = {g: {"held": 1.7, "dry_sha256": g * 3} for g in E.BUILT}
    gs["vt-mag"] = {"held": None, "refused": "silent", "reran": True, "dry_sha256": "vt-mag" * 3}
    fl, why = E.floors_of(stored, {K1: {"guitars": gs}}, build)
    assert fl[K1]["vt-mag"] is None and fl[K1]["vt-win"] == 1.7 and fl[K1]["tr-di"] == 2.0
    assert why == {K1: {"vt-mag": "silent"}}
    bad = json.loads(json.dumps(gs))
    bad["vt-win"] = {"held": math.nan, "dry_sha256": "vt-win" * 3}
    with pytest.raises(SystemExit, match="malformed"):
        E.floors_of(stored, {K1: {"guitars": bad}}, build)
    bad["vt-win"] = {"held": 1.0, "dry_sha256": "other"}
    with pytest.raises(SystemExit, match="not rendered from the envelope build"):
        E.floors_of(stored, {K1: {"guitars": bad}}, build)
    with pytest.raises(SystemExit, match="sets"):
        E.floors_of(stored, {K1: {"guitars": dict(gs, **{"vc-own": {"held": 1.0}})}}, build)


def _fake_iv(vals, ks=None):
    xs = [v for k, v in vals.items() if v is not None and (ks is None or k in ks) and k.split("__")[0] in SV.DECIDING]
    if not xs:
        return None
    m = sum(xs) / len(xs)
    return _iv(m, m - 0.03, m + 0.03)


def test_read_body_with_the_code_s1_and_the_beside_figures():
    dec = [f"bks__fake{i}" for i in range(6)] + [f"goat__fake{i}" for i in range(6)]
    keys = dec + ["panel__fake0"]
    floors = {k: _floors(**{"vt-win": 1.21, "vt-group": 1.6}) for k in keys}
    floors["goat__fake5"]["vt-win"] = None                       # a refusal: drops from the code's set
    floors["bks__fake2"]["vt-phase"] = None                      # a beside refusal: the code's set keeps the part
    vals, refused, beside, gaps = E.term_values(floors)
    neg_d = {E.tag(k): 0.1 * i for i, k in enumerate(dec)}
    body = E.read_body(vals, refused, beside, gaps, _fake_iv, dec, [dec[:6], dec[6:]], OK, None, neg_d)
    assert body["passing_parts_on_the_40"] == 11 and body["refused"] == [E.tag("goat__fake5")]
    assert body["refused_beside"]["phase"] == [E.tag("bks__fake2")]
    assert set(body["terms"]) == set(E.TERM_NAMES)
    assert body["code"] == "XE-window" and body["then"] is None      # R_win ~0 matches, R_group worse
    assert body["label"] in (None, S.REFUSAL_SENSITIVE) and body["itt"] is not None
    assert all(v is None or v <= E.ID_TOL for v in body["identity_max_gap"].values())
    assert len(body["cluster_left_out"]["C_win"]) == 2 and set(body["largest_three"]) == set(E.READ_TERMS) | {"S"}
    assert all(len(t) == 12 for t in body["largest_three"]["C_win"]["tags"])
    assert body["ranks_with_minus_D_own"]["C_win"]["parts"] == 11
    text = json.dumps(body)
    assert all(k not in text for k in keys)


def test_the_error_summary():
    parts = {K1: {"error": {g: {"intent": {"median_abs_db": 0.5, "p90_abs_db": 1.0, "clamped_share": 0.01,
                                           "floored_share": 0.05},
                                "target": {"median_abs_db": 0.8, "p90_abs_db": 2.0}, "level_change_db": -0.2,
                                "spectral_convergence": 0.3} for g in E.BUILT}},
             K2: {"error": {}}}
    s = E.error_summary(parts, [K1, K2])
    assert s["vt-win"]["intent_median_abs_db"] == {"median": 0.5, "range": [0.5, 0.5]}
    assert s["vt-mag"]["spectral_convergence"]["median"] == 0.3 and "spectral_convergence" not in s["vt-part"]
    assert s["vt-group"]["clamped_share"] == 0.01 and s["vt-group"]["level_change_db"] == [-0.2, -0.2]


# --- the ledger -----------------------------------------------------------------------------------------------------------

def test_the_declaration_in_the_ledger():
    d = ENTRY[E.PHASE]
    ks = list(ENTRY)                              # appended in order; other tracks' keys may follow the declaration
    assert ks.index(E.PHASE) > ks.index(SO.PHASE_OUTCOME)
    later = {k for k in ks[ks.index(E.PHASE) + 1:] if k.startswith(E.KEY_PREFIX)}
    assert later <= set(E.KEYS_TO_COME) and d["keys_to_come"] == list(E.KEYS_TO_COME)
    assert d["plan"].startswith(E.PLAN) and (REPO / E.PLAN).exists()
    assert d["table"]["codes"] == list(E.XE_DECLARED) and d["table"]["XE-undecided"]["when"] == "anything else"
    assert d["proofs"]["names"] == list(E.PROOFS) and "stops the shard" in d["proofs"]["failure"]
    assert d["transform"]["bands"]["table"] == E.band_rows() and d["transform"]["bands"]["count"] == 20
    assert d["renders"]["floors"] == 470 and d["renders"]["repeat"] == 8 and d["renders"]["total"] == 478
    assert set(d["amendments"]) == {str(i) for i in range(1, 7)}
    assert "window suffices; group undecided" in json.dumps(d["orchestrator_calls"])
    assert "2026-11-28" in d["user_go"] and "Spectral steps first" in d["user_go"]
    for name in ("phase_scratch_envelope", "scratch_envelope", "envelope_build", "envelope_floors", "vt-", "XE-",
                 "C_part", "C_group", "C_win", "R_group", "R_win", "XE_TABLE", "fs/envelope"):
        assert name in d["grepped"], name
    for v in ("+0.501 [+0.399, +0.603]", "+0.028 [+0.020, +0.037]", "XW-part"):
        assert v in json.dumps(d["seen"]), v
    assert E.ORACLE in json.dumps(d["table"])


def test_the_plan_doc_holds_the_band_table():
    doc = (REPO / E.PLAN).read_text()
    for r in E.band_rows():
        assert f"| {r['band']} |" in doc and r["bins"] in doc
    for code in E.XE_DECLARED:
        assert code in doc
    assert "phase_scratch_envelope" in doc and "window suffices; group undecided" in doc
