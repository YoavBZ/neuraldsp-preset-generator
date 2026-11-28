"""The `vc-own` search row `fs-own` (`learn/scratch_own.py`, `docs/scratch-own-plan.md`): the outcome table (every
interval case, malformed ones included, ends in exactly one XW code), the control's gate, the forbidden files, the
guards (every command refuses off main, without its hashes, or with other code), the shared steps (called, never
redefined or patched), and in a fake world: the row mirrors `rederive_rows`' fs-refit exactly (amendment 10), refuses
a guitar that is not build.json's, never opens a forbidden file, and the read holds every beside figure with part keys
only as 12-hex tags. Synthetic keys. Pure tests run on the light CI runner (no numpy); the fake world of the search
needs numpy (skipped elsewhere)."""
import ast
import itertools
import json
import math
import pathlib
import subprocess

import pytest

from learn import rederive_rows as RR
from learn import scratch_exact as SE
from learn import scratch_loudar as SL
from learn import scratch_notes as SN
from learn import scratch_own as O
from learn import scratch_rederive as RD
from learn import scratch_search as S
from learn import scratch_voice as SV

REPO = pathlib.Path(__file__).resolve().parents[1]
SRC = (REPO / "learn" / "scratch_own.py").read_text()
TREE = ast.parse(SRC)
LEDGER = json.loads((REPO / "docs" / "dev-test-ledger.json").read_text())
ENTRY = next(t for t in LEDGER["tests"] if t["test_id"] == "preset-ladder")
K1, K2 = "bks__set0__k1.wav@1.0#r.wav|ac20", "goat__item_0@2.0#r.wav|pr12"     # synthetic keys


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


BETTER, MATCHES, WORSE = _iv(-0.3, -0.5, -0.15), _iv(0.0, -0.04, 0.04), _iv(0.3, 0.15, 0.5)
UNDECIDED = _iv(-0.02, -0.2, 0.15)
OK = {"checks_passed": True, "reproduces": True}


def _args(**kw):
    return type("A", (), dict({"shard": (0, 1), "rerun": False}, **kw))()


# --- names and the declaration ----------------------------------------------------------------------------------------

def test_names():
    assert (O.ROW, O.DRY, O.REF, O.COMPARATOR, O.STEM_ROW, O.BOTH_ROW) == ("fs-own", "vc-own", "xlnoG", "b2",
                                                                         "fs-stem", "fs-both")
    assert O.PHASE == "phase_scratch_own" and O.KEYS_TO_COME == ("phase_scratch_own_answers",
                                                                 "phase_scratch_own_outcome")
    assert O.LEDGER_ID == "preset-ladder" and O.CONTROL_OUTCOME == "phase_scratch_voice_control_outcome"
    assert O.XW_DECLARED == ("XW-anomaly", "XW-worse", "XW-closed", "XW-part", "XW-level", "XW-undecided")
    assert O.XC_DECLARED == ("XC-anomaly", "XC-stands", "XC-part", "XC-notes", "XC-undecided")
    assert O.own_dir() == S.fs_dir() / "own" and O.MAX_SHARDS == 3


def test_the_deferred_steps_reserve_no_name():
    for name in ("vt-", "XE-", "XE_", "envelope_build", "scratch_envelope", "phase_scratch_envelope", "XO-", "XO_"):
        assert name not in SRC, name
    assert "phase_scratch_own_go" not in SRC and "user_words" not in SRC      # no word of its own (2026-11-28)


def test_the_declaration_is_in_the_ledger():
    d = ENTRY[O.PHASE]
    assert d["table"]["codes"] == list(O.XW_DECLARED)
    assert d["keys_to_come"] == list(O.KEYS_TO_COME)
    assert d["gate"]["stop"] == list(O.XC_STOP) and d["gate"]["proceed"] == list(O.XC_PROCEED)
    assert d["plan"].startswith(O.PLAN) and (REPO / O.PLAN).exists()
    assert list(ENTRY)[-1] == O.PHASE or list(ENTRY).index(O.PHASE) > list(ENTRY).index("phase_scratch_voice_outcome")
    for k in O.KEYS_TO_COME:
        assert k not in ENTRY


def test_the_seen_figures_are_the_declarations():
    seen = ENTRY[O.PHASE]["seen"]
    assert O.SEEN["b2_less_row_b"] == (0.274, 0.186, 0.361)
    assert O.SEEN_BESIDE["loudar_less_b2_cp50_bp"] == (0.002, -0.116, 0.121)     # amendment 9, under bp_rows
    assert O.SEEN_BESIDE["b2_less_row_b_cp50"] == (0.230, 0.147, 0.314)
    assert O.SEEN_BESIDE["b2_less_row_b_shrunk"] == (0.143, 0.075, 0.212)
    text = json.dumps(seen)
    for v in ("+0.274 [+0.186, +0.361]", "+0.002 [-0.116, +0.121]", "-0.005 [-0.103, +0.092]",
              "+0.230 [+0.147, +0.314]", "+0.143 [+0.075, +0.212]", "+0.321 [+0.261, +0.380]"):
        assert v in text, v


# --- the outcome table (pure) -----------------------------------------------------------------------------------------

def test_the_table_guard_holds_and_refuses(monkeypatch):
    O.table_guard()
    monkeypatch.setattr(O, "XW_CODES", O.XW_CODES[::-1])
    with pytest.raises(SystemExit, match="six declared"):
        O.table_guard()
    monkeypatch.setattr(O, "XW_CODES", O.XW_DECLARED)
    monkeypatch.setattr(O, "XC_PROCEED", ("XC-stands", "XC-undecided"))
    with pytest.raises(SystemExit, match="stop, wait and proceed"):
        O.table_guard()
    monkeypatch.setattr(O, "XC_PROCEED", ("XC-stands", "XC-part", "XC-undecided", "XC-anomaly"))
    with pytest.raises(SystemExit, match="stop, wait and proceed"):
        O.table_guard()
    monkeypatch.setattr(O, "XC_PROCEED", ("XC-stands", "XC-part", "XC-undecided"))
    O.table_guard()
    monkeypatch.setattr(SV, "COVERAGE_FORCED", ("XC-part",))      # the spend gate reads the codes otherwise
    with pytest.raises(SystemExit, match="as scratch_voice's spend gate declares them"):
        O.table_guard()
    monkeypatch.setattr(SV, "COVERAGE_FORCED", ("XC-part", "XC-notes"))
    monkeypatch.setattr(SV, "CONTROL_SHUT", ("XC-anomaly", "XC-notes"))
    with pytest.raises(SystemExit, match="as scratch_voice's spend gate declares them"):
        O.table_guard()
    monkeypatch.setattr(SV, "CONTROL_SHUT", ("XC-anomaly",))
    monkeypatch.setattr(O, "KEY_PREFIX", "phase_scratch_voice_own")
    with pytest.raises(SystemExit, match="guarded prefix"):
        O.table_guard()


def test_each_declared_code_on_a_grid():
    want = [((BETTER, MATCHES), "XW-closed"), ((BETTER, WORSE), "XW-part"), ((BETTER, UNDECIDED), "XW-part"),
            ((WORSE, WORSE), "XW-worse"), ((WORSE, MATCHES), "XW-worse"), ((MATCHES, WORSE), "XW-level"),
            ((MATCHES, MATCHES), "XW-level"), ((UNDECIDED, WORSE), "XW-undecided"),
            ((BETTER, BETTER), "XW-anomaly"), ((WORSE, BETTER), "XW-anomaly")]
    for (d, c), code in want:
        assert O.xw_code(d, c, OK)["code"] == code, (d, c)
    assert {code for _, code in want} == set(O.XW_DECLARED)


def test_every_interval_case_ends_in_exactly_one_code():
    vals = (-0.4, -0.12, -0.08, -0.03, 0.0, 0.03, 0.08, 0.12, 0.4)
    ivs = [_iv(m, lo, hi) for m, lo, hi in itertools.product(vals, repeat=3) if lo <= m <= hi]
    seen = set()
    for d in ivs:
        for c in ivs[::7]:
            r = O.xw_code(d, c, OK)
            assert r["code"] in O.XW_CODES and isinstance(r["said"], str) and isinstance(r["decides"], str)
            assert "{" not in r["said"] + r["decides"]
            seen.add(r["code"])
    assert seen == set(O.XW_DECLARED)


@pytest.mark.parametrize("bad", [None, {}, {"mean": 0.1}, _iv(None, 0, 1), _iv(float("nan"), 0, 1),
                                 _iv(0.1, 0.3, 0.2), _iv(0.1, float("inf"), 0.5), "x", _iv("a", 0, 1)])
def test_a_malformed_interval_is_an_anomaly(bad):
    """Amendment 1: no usable interval or reading for D_own, -D_own or C_own is XW-anomaly."""
    assert O.xw_code(bad, MATCHES, OK)["code"] == "XW-anomaly"
    assert O.xw_code(BETTER, bad, OK)["code"] == "XW-anomaly"
    assert O.xw_code(bad, bad, OK)["anomaly"]


def test_a_failed_check_or_reproduction_is_an_anomaly():
    for c in O.CHECKS:
        r = O.xw_code(BETTER, MATCHES, dict(OK, **{c: False}))
        assert r["code"] == "XW-anomaly" and c in r["anomaly"]
    assert O.xw_code(BETTER, MATCHES, {})["code"] == "XW-anomaly"
    assert O.xw_code(BETTER, BETTER, OK)["anomaly"] == "C_own reads better"


def test_minus_d_own_reads_the_gain_both_ways():
    assert O.neg(_iv(0.02, -0.03, 0.08)) == _iv(-0.02, -0.08, 0.03)
    assert O.neg({"mean": 1}) is None
    r = O.xw_code(_iv(0.02, -0.03, 0.08), WORSE, OK)
    assert r["code"] == "XW-level" and r["readings"]["minus_D_own"]["reading"] == "matches"
    assert O.xw_code(_iv(-0.06, -0.2, 0.05), WORSE, OK)["code"] == "XW-undecided"   # a heard-size gain not ruled out


def test_the_words_follow_the_reviews_notes():
    r = O.xw_code(UNDECIDED, MATCHES, OK)
    assert r["code"] == "XW-undecided" and "a heard-size loss against the true DI is ruled out" in r["said"]
    assert "-0.200 to +0.150" in r["decides"]
    assert "audit" in O.xw_code(None, None, OK)["said"]
    assert O.xw_code(WORSE, WORSE, OK)["said"].startswith("if the audit finds no fault")
    assert "undecided" in O.xw_code(BETTER, UNDECIDED, OK)["said"]
    level = O.xw_code(MATCHES, WORSE, OK)["decides"]
    assert "N, K and F" in level and "vc-fin" in level and "2.6k" in level
    assert "-D_own" in O.xw_code(BETTER, WORSE, OK)["decides"]


def test_the_shrunk_arm_is_beside():
    a = O.arm_codes({"answer": (BETTER, MATCHES), "shrunk": (BETTER, WORSE), "cp50": (None, None)}, OK)
    assert a["codes"] == {"answer": "XW-closed", "shrunk": "XW-part", "cp50": "XW-anomaly"}
    assert a["label"] == O.SHRUNK_SENSITIVE
    assert O.arm_codes({"answer": (BETTER, MATCHES), "shrunk": (BETTER, MATCHES)}, OK)["label"] is None


def test_s1_the_passing_only_code_beside():
    D = {n: {arm: {"the_40": iv} for arm in O.ARMS} for n, iv in (("D_own", BETTER), ("C_own", MATCHES))}
    code, cp, label, arms = O.read_codes(D, None, OK)
    assert code["code"] == "XW-closed" and cp is None and label is None and arms["label"] is None
    code, cp, label, _ = O.read_codes(D, {"D_own": BETTER, "C_own": WORSE}, OK)
    assert cp["code"] == "XW-part" and label == S.REFUSAL_SENSITIVE
    _, cp, label, _ = O.read_codes(D, {"D_own": None, "C_own": WORSE}, OK)
    assert cp["code"] is None and label is None


# --- the control's gate (pure) ----------------------------------------------------------------------------------------

def _ctl(code, label=None, **kw):
    return {O.CONTROL_OUTCOME: dict({"code": code, "coverage_label": label}, **kw)}


def test_the_control_gate():
    assert O.control_gate({})[0] == "absent" and "control's audited outcome first" in O.control_gate({})[1]
    assert O.control_gate({O.CONTROL_OUTCOME: {"code": None}})[0] == "absent"
    assert O.control_gate(_ctl("XC-anomaly")) == ("stop", O.control_gate(_ctl("XC-anomaly"))[1])
    assert "construction is off" in O.control_gate(_ctl("XC-anomaly"))[1]
    assert O.control_gate(_ctl("XC-other"))[0] == "stop"
    assert O.control_gate(_ctl("XC-notes")) == ("wait", None)
    assert O.control_gate(_ctl("XC-part", "coverage-sensitive")) == ("wait", None)
    for code in ("XC-stands", "XC-part", "XC-undecided"):
        assert O.control_gate(_ctl(code)) == ("proceed", None)
    assert O.control_gate(_ctl("XC-stands", "coverage-sensitive")) == ("proceed", None)
    assert O.control_gate(_ctl("XC-undecided", "coverage-sensitive")) == ("proceed", None)


def _no_label(code):
    return {O.CONTROL_OUTCOME: {"code": code}}


def test_a_missing_coverage_label_fails_closed():
    """As `spend_refusal` since #658: under XC-part or XC-notes the outcome must carry `coverage_label` (None or
    coverage-sensitive), else the row stops; the other codes do not need it."""
    for code in ("XC-part", "XC-notes"):
        state, why = O.control_gate(_no_label(code))
        assert state == "stop" and "fails closed" in why and "coverage_label" in why
        state, why = O.control_gate(_ctl(code, "coverage-clean"))
        assert state == "stop" and "fails closed" in why
    for code in ("XC-stands", "XC-undecided"):
        assert O.control_gate(_no_label(code)) == ("proceed", None)
    assert O.control_gate(_no_label("XC-anomaly"))[0] == "stop"


def test_the_spend_gate_fails_closed_the_same_way():
    """The row's own check and main's `spend_refusal` agree on a missing label: both shut (with or without a waiver
    answering the code)."""
    for code in ("XC-part", "XC-notes"):
        m = dict({SV.PHASE_OUTCOME: {"code": "XV-both"}, O.CONTROL_OUTCOME: {"code": code, "date": "2026-11-29"}},
                 **_waiver(code))
        assert SV.spend_refusal(m, "search-row") and O.control_gate(m)[0] == "stop"


def test_xc_anomaly_stops_before_the_spend_gate(monkeypatch):
    monkeypatch.setattr(SV, "require_spend", lambda kind: pytest.fail("the spend gate was asked"))
    for m in ({}, _ctl("XC-anomaly"), _ctl("XC-other"), _no_label("XC-part"), _no_label("XC-notes")):
        with pytest.raises(SystemExit):
            O.require_row_spend(m)


def test_every_other_code_relies_on_require_spend(monkeypatch):
    asked = []
    for code, lab in (("XC-stands", None), ("XC-part", None), ("XC-undecided", None), ("XC-notes", None),
                      ("XC-part", "coverage-sensitive")):
        m = _ctl(code, lab)
        monkeypatch.setattr(SV, "require_spend", lambda kind, m=m: (asked.append(kind), m)[1])
        assert O.require_row_spend(m) is m
    assert asked == ["search-row"] * 5

    def refuse(kind):
        raise SystemExit("XC-notes: to the user before any sound-route spend")
    monkeypatch.setattr(SV, "require_spend", refuse)
    with pytest.raises(SystemExit, match="before any sound-route spend"):
        O.require_row_spend(_ctl("XC-notes"))
    monkeypatch.setattr(SV, "require_spend", lambda kind: _ctl("XC-anomaly"))   # main moved under the check
    with pytest.raises(SystemExit, match="construction is off"):
        O.require_row_spend(_ctl("XC-stands"))


def _waiver(code, date="2026-11-29", kinds=("search-row",)):
    return {SV.PHASE_WAIVER: {"answers_code": code, "date": date, "spend_kinds": list(kinds),
                              "user_words": "yes, run fs-own"}}


def test_the_spend_gate_reads_the_waiver_for_this_row(monkeypatch):
    """With the control's tightened gate (#658) on this checkout: under XC-notes and a coverage-sensitive XC-part the
    row runs only with the waiver answering that code, dated on or after the control's outcome, spend_kinds holding
    "search-row"; skipped until #658 is merged here."""
    if not hasattr(SV, "CONTROL_WAIVER_ONLY"):
        pytest.skip("the control's spend gate (#658) is not merged here yet")
    base = {SV.PHASE_OUTCOME: {"code": "XV-both"}}
    for code, lab in (("XC-notes", None), ("XC-part", "coverage-sensitive")):
        ctl = {SV.PHASE_CONTROL_OUTCOME: {"code": code, "coverage_label": lab, "date": "2026-11-29"}}
        for m, opens in ((dict(base, **ctl), False), (dict(base, **ctl, **_waiver(code)), True),
                         (dict(base, **ctl, **_waiver("XC-stands")), False),
                         (dict(base, **ctl, **_waiver(code, kinds=("synthesis",))), False),
                         (dict(base, **ctl, **_waiver(code, date="2026-11-01")), False)):
            monkeypatch.setattr(SV, "on_main", lambda m=m: (m, None))
            if opens:
                assert O.require_row_spend(m) is m
            else:
                with pytest.raises(SystemExit):
                    O.require_row_spend(m)
    m = dict(base, **{SV.PHASE_CONTROL_OUTCOME: {"code": "XC-stands", "coverage_label": None, "date": "2026-11-29"}})
    monkeypatch.setattr(SV, "on_main", lambda: (m, None))
    assert O.require_row_spend(m) is m


# --- the forbidden files, the shard rule, the carry, the keys (pure) --------------------------------------------------

FS = pathlib.PurePath("/x/PF/fs")


@pytest.mark.parametrize("p", [
    FS / "voice" / "repeat" / "k.json", FS / "rederive" / "floor-repeat" / "k.json", FS / "outcome.json",
    FS / "voice" / "control" / "build.json", FS / "voice" / "control" / "dry" / "tr-uc" / "k.npy",
    FS / "voice" / "control" / "floors-first" / "k.json", FS / "envelope" / "dry" / "k.npy", FS / "envelope" / "x.json",
    FS / "own" / "answers.json", FS / "own" / "rows.json", FS / "own" / "report.json", FS / "own" / "reproduce.json",
    FS / "own" / "score" / "k.json", FS / "own" / "score-rerun" / "k.json", FS / "voice" / "floors" / "k.json",
    FS / "voice" / "rows.json", FS / "voice" / "report.json", FS / "exact" / "targets.json",
    FS / "answers-fs-stem.json", FS / "score" / "fs-stem" / "k.json", FS / "notes-b2" / "answers.json",
    FS / "notes-b2" / "score" / "k.json", FS / "rederive" / "answers-fs-refit.json", FS / "loudar" / "rows.json",
    FS / "voice" / "repeat-rerun" / "k.json"])
def test_the_search_never_opens_anything_scored(p):
    assert O.is_forbidden(p)
    with pytest.raises(SystemExit, match="never opens it"):
        O.search_open(p)


@pytest.mark.parametrize("p", [FS / "voice" / "build.json", FS / "voice" / "dry" / "vc-own" / "k.npy",
                               FS / "own" / "search" / "k.json", FS / "own" / "start-ref" / "k.json",
                               FS / "own" / "search-rerun" / "k.json", FS / "own" / "checks" / "check-score" /
                               "result.json", FS / "draw.json", FS / "rederive" / "fit" / "build-real.json"])
def test_the_search_opens_its_own_inputs(p):
    assert not O.is_forbidden(p)


def test_the_shard_rule_and_the_cli():
    assert O.shard_refusal((0, 3)) is None and O.shard_refusal((3, 3)) and O.shard_refusal((0, 4))
    with pytest.raises(SystemExit):
        O.main(["search", "--shard", "0/4"])
    with pytest.raises(SystemExit):
        O.main(["answers", "--shard", "0/3"])
    with pytest.raises(SystemExit):
        O.main(["read", "--rerun"])
    with pytest.raises(SystemExit):
        O.main(["floors"])


def test_no_carry():
    s = {"true": "a", "tr-di": "b", "avg+mild": "c", "rf2": "d"}
    assert O.carry_hit("e", s) is None and O.carry_hit(None, {"true": None}) is None
    assert [O.carry_hit(v, s) for v in "abcd"] == ["true", "tr-di", "avg+mild", "rf2"]


def test_own_keys_only():
    a = {"phase_scratch_own": 1, "phase_x": 2}
    assert O.keys_refusal(a, {"phase_scratch_own": 1}) is None
    assert "phase_scratch_own_answers" in O.keys_refusal(a, {"phase_scratch_own": 1, "phase_scratch_own_answers": 2})


def test_the_rank_beside_never_fails():
    assert O.rank_beside({K1: 0.1}, None, [K1])["rho"] == O.NOT_COMPUTABLE
    keys = [f"k{i}" for i in range(5)]
    by = {O.tag(k): float(i) for i, k in enumerate(keys)}
    r = O.rank_beside({k: float(i) for i, k in enumerate(keys)}, by, keys)
    assert r["rho"] == pytest.approx(1.0) and r["parts"] == 5


# --- the source: shared steps, imports, guarded files -----------------------------------------------------------------

def _calls():
    out = set()
    for node in ast.walk(TREE):
        f = getattr(node, "func", None)
        if isinstance(node, ast.Call) and isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            out.add(f"{node.func.value.id}.{node.func.attr}")
    return out


SHARED = ("SN.start_reference", "S.search_row_part", "S.answer_parts", "SN.deciding_stop", "S.score_row_part",
          "S.read_row_parts", "S.run_part", "S.with_reruns", "S.rerun_refusal", "S.rerun_path", "S.load_ref_blank",
          "SN.set_rows", "SN.paired_reading", "SN.paired_values", "S.itt_per", "SL.bp_rows", "SL.g50_of",
          "SE.share", "SE.dry_refusal", "SN.score_check_verdict", "SN.search_check_verdict", "SE.disk_guard",
          "SV.require_spend", "RR.real_numbers", "RR.with_passing", "SE.one_per_partner")


def test_the_shared_steps_are_called():
    assert not [c for c in SHARED if c not in _calls()]


def test_the_shared_steps_are_never_redefined_or_patched():
    names = {c.split(".")[1] for c in SHARED}
    defined = {n.name for n in TREE.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    assert not names & defined
    aliases = {"S", "SE", "SN", "SV", "SL", "RR", "RD", "NT", "R", "P", "CB", "LO", "C"}
    for node in ast.walk(TREE):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(
            node, (ast.AugAssign, ast.AnnAssign)) else []
        for t in targets:
            assert not (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id in aliases)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in ("setattr", "exec", "eval")
    assert "monkeypatch" not in SRC and "global " not in SRC


def test_the_module_imports_only_the_standard_library_at_module_level():
    mods = set()
    for node in TREE.body:
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module.split(".")[0])
    assert mods <= {"__future__", "argparse", "json", "math", "pathlib", "statistics", "time", "learn"}


# Amendment 11's pinned files (the control's edits to scratch_voice.py and voice_floors.py are on main since #658)
GUARDED = ("learn/scratch_search.py", "learn/scratch_notes.py", "learn/scratch_exact.py", "learn/rederive_rows.py",
           "learn/scratch_loudar.py", "learn/voice_build.py", "learn/scratch_voice.py", "learn/voice_floors.py")


def test_the_pinned_files():
    assert set(GUARDED) <= set(O.PINNED) and len(set(GUARDED)) == 8   # amendment 11's list, every one pinned
    assert O.CODE_FILES[0] == O.MODULE


def test_the_guarded_files_are_unchanged_against_the_base():
    """The per-PR check: none of the guarded files differs from the merge base with origin/main (skipped without git
    history)."""
    base = subprocess.run(["git", "-C", str(REPO), "merge-base", "origin/main", "HEAD"], capture_output=True, text=True)
    if base.returncode:
        pytest.skip("no origin/main here")
    r = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", base.stdout.strip(), "HEAD", "--", *GUARDED])
    assert r.returncode == 0


# --- the guards: every command refuses --------------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", sorted(O.COMMANDS))
def test_every_command_refuses_off_main(monkeypatch, cmd):
    monkeypatch.setattr(S, "on_main", lambda: (None, "this checkout's learn/scratch_search.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        O.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", sorted(O.COMMANDS))
def test_every_command_refuses_without_its_hashes_on_main(monkeypatch, cmd):
    from learn import note_replay as NRP

    main = {}
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    monkeypatch.setattr(NRP, "ledger_entry", lambda: main)
    monkeypatch.setattr(O, "pinned_identity", lambda: {f: True for f in O.CODE_FILES})
    for k in O.BASE + O.PHASES[cmd]:
        with pytest.raises(SystemExit, match=f"has no {k}:"):
            O.COMMANDS[cmd](_args())
        main[k] = {}


@pytest.mark.parametrize("cmd", sorted(O.COMMANDS))
def test_every_command_refuses_with_other_code_or_keys(monkeypatch, cmd):
    from learn import note_replay as NRP

    main = {k: {} for k in O.BASE + O.PHASES[cmd]}
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    monkeypatch.setattr(NRP, "ledger_entry", lambda: main)
    monkeypatch.setattr(O, "pinned_identity", lambda: {O.MODULE: True, "learn/scratch_voice.py": False})
    with pytest.raises(SystemExit, match="scratch_voice.py.*differ from main's"):
        O.COMMANDS[cmd](_args())
    monkeypatch.setattr(O, "pinned_identity", lambda: {f: True for f in O.CODE_FILES})
    monkeypatch.setattr(NRP, "ledger_entry", lambda: dict(main, phase_scratch_own_answers={"sha256": "a"}))
    with pytest.raises(SystemExit, match="phase_scratch_own_answers.*differ from main's"):
        O.COMMANDS[cmd](_args())
    monkeypatch.setattr(NRP, "ledger_entry", lambda: dict(main, phase_scratch_voice_waiver={"x": 1}))
    with pytest.raises(SystemExit, match="phase_scratch_voice_waiver.*differ from main's"):
        O.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", O.RENDER_COMMANDS)
def test_every_render_command_refuses_without_the_controls_outcome(monkeypatch, cmd):
    main = {k: {} for k in O.BASE + O.PHASES[cmd]}
    monkeypatch.setattr(O, "require_own", lambda *ph: main)
    monkeypatch.setattr(SV, "require_spend", lambda kind: pytest.fail("the spend gate was asked"))
    with pytest.raises(SystemExit, match="control's audited outcome first"):
        O.COMMANDS[cmd](_args())
    main.update(_ctl("XC-anomaly"))
    with pytest.raises(SystemExit, match="construction is off"):
        O.COMMANDS[cmd](_args())


# --- the fake world (numpy; skipped on the light runner) --------------------------------------------------------------

def _world(monkeypatch, tmp_path):
    """Both rows in one made-up world: two parts (one BKS, one GOAT), build 2's tr-di X, fs-refit's rf2 (X / 2) in
    rederive_fit's format, the voice build's vc-own (X / 4) in voice_build's, every source but the files stood in for.
    The shared steps record what they are handed; the forbidden files exist and must never be opened."""
    np = pytest.importorskip("numpy")
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import note_replay as NRP
    from learn import pipeline_fix as P
    from learn import rederive_fit as RF

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path / "PF")
    rng = np.random.default_rng(0)
    X = {k: rng.standard_normal(4000).astype(np.float32) for k in (K1, K2)}
    xs = {k: S.npy_sha(v) for k, v in X.items()}
    rf = {k: (v * 0.5).astype(np.float32) for k, v in X.items()}
    own = {k: (v * 0.25).astype(np.float32) for k, v in X.items()}
    b2 = {"parts": {k: {"arms": {SE.BANK_ARM: {"sha256": xs[k]}}} for k in X}}
    rb = {"row": "fs-refit", "parts": {}}
    vb = {"proofs_hold": True, "parts": {}}
    for k in X:
        p = RF.guitar_path("fs-refit", k)
        p.parent.mkdir(parents=True, exist_ok=True)
        np.save(p, rf[k])
        rb["parts"][k] = {"file_sha256": S.file_sha(p), "audio_sha256": S.npy_sha(rf[k])}
        q = SV.dry_path(SV.OWN, k)
        q.parent.mkdir(parents=True, exist_ok=True)
        np.save(q, own[k])
        vb["parts"][k] = {"guitars": {SV.OWN: {"file_sha256": S.file_sha(q), "audio_sha256": S.npy_sha(own[k])},
                                      SV.AVG_MILD: {"audio_sha256": "am-" + k}}}
    P.save(RF.build_record_path("real"), rb)
    P.save(SV.build_path(), vb)
    draw = {"replay_draw_sha256": "rd", "parts": [
        {"pkey": k, "set": k.split("__")[0], "unit": "u" + k[:4], "amp": k[-4:], "lag": 7, "search": "A",
         "held": "B", "cluster": f"x|c{j}", "partners": [], "cen": {"settings": {"c": 0.5}, "select": {}},
         "start_ref": {SV.AVG_MILD: {O.REF: 0.4}}} for j, k in enumerate((K1, K2))]}
    P.save(S.draw_path(), draw)
    units = {(p["set"], p["unit"], p["amp"]): {"prt": {"di_path": "d"}} for p in draw["parts"]}
    sd = type("SD", (), {"units": units})()
    m = {SV.PHASE_DRY: {"sha256": S.file_sha(SV.build_path())}, **_ctl("XC-stands")}
    for kind in ("check-score", "check-search"):                  # both rows' checks passed
        P.save(RR.check_dir("real", kind) / "result.json", {"passed": True})
        P.save(O.check_dir(kind) / "result.json", {"passed": True})
    forbidden = [O.answers_path(), O.rows_path(), S.score_path("fs-stem", K1), SV.rows_path(), SV.floor_path(K1),
                 SV.repeat_path(K1), S.fs_dir() / "outcome.json", SV.voice_dir() / "control" / "rows.json",
                 S.fs_dir() / "envelope" / "x.json", RR.answers_path("fs-refit"), SN.answers_path("b2")]
    for f in forbidden:
        P.save(f, {"held": {"answer": 1.0}})
    calls = {"start": [], "search": [], "answer_parts": [], "deciding_stop": [], "score": [], "run_part": [],
             "nosep": 0, "wait": 0, "disk": 0, "rerun_path": 0, "rerun_refusal": 0, "spend": 0}
    monkeypatch.setattr(RR, "require_rows", lambda *ph: m)
    monkeypatch.setattr(RR, "row_refusal", lambda row, mm, stage1=None: None)
    monkeypatch.setattr(RR, "fit_build", lambda mm, kind: rb)
    monkeypatch.setattr(RR, "carry_record", lambda sha: {"carried": []})
    monkeypatch.setattr(O, "require_own", lambda *ph: m)
    monkeypatch.setattr(O, "require_row_spend", lambda mm: (calls.__setitem__("spend", calls["spend"] + 1), mm)[1])
    monkeypatch.setattr(O, "searched_world", lambda mm: {"b2": b2, "rf2": rb})
    monkeypatch.setattr(SE, "bank_build", lambda mm: b2)
    monkeypatch.setattr(SE, "context", lambda: (draw, sd))
    monkeypatch.setattr(NRP, "di_section", lambda prt: np.ones(16, np.float32))

    def count(name, fn=None):
        def f(*a, **k):
            calls[name] += 1
            return fn(*a, **k) if fn else None
        return f
    monkeypatch.setattr(SE, "disk_guard", count("disk"))
    monkeypatch.setattr(NRP, "no_separation_beside", count("nosep"))
    monkeypatch.setattr(LO, "_wait_cap", count("wait"))
    monkeypatch.setattr(S, "rerun_path", count("rerun_path", S.rerun_path))
    monkeypatch.setattr(S, "rerun_refusal", count("rerun_refusal", S.rerun_refusal))
    monkeypatch.setattr(C, "mic_lists", lambda: {"lists": 1})
    monkeypatch.setattr(CB, "new_renderer", object())
    monkeypatch.setattr(S, "load_ref_blank", lambda sd_, p, ref: np.full(8, 0.5))
    w = {"X": X, "xs": xs, "rf": rf, "own": own, "m": m, "b2": b2, "rb": rb, "vb": vb, "draw": draw, "sd": sd,
         "calls": calls, "forbidden": forbidden, "refuse_first": set()}

    def start_ref(p, x32, ref_blank, new_renderer, path, dry_sha):
        calls["start"].append({"p": p, "x": S.npy_sha(x32), "blank": float(np.sum(ref_blank)),
                               "renderer": new_renderer is CB.new_renderer, "path": path, "dry_sha": dry_sha})
        P.save(path, {"dry_sha256": dry_sha, "value": 0.5})
        return 0.5, 2

    def search(p, dry, ref_name, x32, ref_blank, new_renderer, lists, out, ledger, start_ref=None, dry_sha256=None):
        calls["search"].append({"p": p, "dry": dry, "ref": ref_name, "x": S.npy_sha(x32),
                                "blank": float(np.sum(ref_blank)), "renderer": new_renderer is CB.new_renderer,
                                "lists": lists, "out": out, "ledger": ledger, "start_ref": start_ref,
                                "dry_sha256": dry_sha256})
        rec = {"part": p["pkey"], "dry": dry, "dry_sha256": dry_sha256, "renders": 10}
        if p["pkey"] in w["refuse_first"] and "-rerun" not in out.parent.name:
            rec["refused"] = {"search": "a technical refusal"}
        P.save(out, rec)
        return rec

    def answer_parts(draw_, recs, search_sha):
        calls["answer_parts"].append({"draw": draw_, "recs": recs, "shas": {k: search_sha(k) for k in recs}})
        return {k: {"answer": {"a": 1.0}, "select": {}, "borrowed": []} for k in recs if "refused" not in recs[k]}, {}

    def deciding_stop(refused, sets_of, deciding=SN.DECIDING):
        calls["deciding_stop"].append({"refused": refused, "sets_of": sets_of, "deciding": deciding})
        return [], [], False

    def score(p, a, ans_parts, row, answers_sha, sd_, new_renderer):
        calls["score"].append({"p": p, "a": a, "ans_parts": ans_parts, "row": row, "answers_sha": answers_sha,
                               "sd": sd_ is sd, "renderer": new_renderer is CB.new_renderer})
        return {"scoring_control_ok": True, "distinct_renders": 3, "held": {"cen": 1.0},
                "render_sha256": {"cen": "r"}}, 6
    monkeypatch.setattr(SN, "start_reference", start_ref)
    monkeypatch.setattr(S, "search_row_part", search)
    monkeypatch.setattr(S, "answer_parts", answer_parts)
    monkeypatch.setattr(SN, "deciding_stop", deciding_stop)
    monkeypatch.setattr(S, "score_row_part", score)
    opened = []
    real_rt, real_rb, real_load = pathlib.Path.read_text, pathlib.Path.read_bytes, np.load
    monkeypatch.setattr(pathlib.Path, "read_text", lambda self, *a, **k: (opened.append(self),
                                                                         real_rt(self, *a, **k))[1])
    monkeypatch.setattr(pathlib.Path, "read_bytes", lambda self: (opened.append(self), real_rb(self))[1])
    monkeypatch.setattr(np, "load", lambda f, *a, **k: (opened.append(pathlib.Path(f)), real_load(f, *a, **k))[1])
    w["opened"] = opened
    return w


def _take(w, *names):
    """The calls recorded so far, then cleared."""
    out = {n: list(w["calls"][n]) for n in names}
    for n in names:
        w["calls"][n].clear()
    return out


def _counts(w):
    return {n: w["calls"][n] for n in ("nosep", "wait", "disk", "rerun_path", "rerun_refusal")}


def _strip(call, *allowed):
    return {k: v for k, v in call.items() if k not in allowed}


def test_the_row_mirrors_fs_refit_exactly(monkeypatch, tmp_path):
    """Amendment 10: search, answers and score hand the shared steps the same arguments as `rederive_rows`'
    `_search_real`, `cmd_answers` and `cmd_score` for fs-refit; only the guitar, its sha256, the name and the paths
    differ. Both call the separation check, the wait cap, the disk guard, the rerun paths and `rerun_refusal`."""
    w = _world(monkeypatch, tmp_path)
    w["refuse_first"] = {K2}

    def delta(fn):
        c0 = _counts(w)
        fn()
        return {k: v - c0[k] for k, v in _counts(w).items()}
    d_rr = delta(lambda: RR.cmd_search(_args(row="fs-refit")))
    theirs = _take(w, "start", "search")
    d_own = delta(lambda: O.cmd_search(_args()))
    mine = _take(w, "start", "search")
    assert d_own == d_rr and (d_own["nosep"], d_own["wait"], d_own["disk"]) == (1, 1, 2)
    assert len(mine["search"]) == len(theirs["search"]) == 2 and len(mine["start"]) == 2
    name_path = ("x", "dry_sha256", "dry", "ledger", "out")
    for a, b in zip(mine["search"], theirs["search"]):
        assert _strip(a, *name_path) == _strip(b, *name_path)
        assert a["x"] == a["dry_sha256"] == S.npy_sha(w["own"][a["p"]["pkey"]])
        assert b["x"] == b["dry_sha256"] == S.npy_sha(w["rf"][b["p"]["pkey"]])
        assert (a["dry"], a["ledger"], a["out"]) == ("vc-own", "preset-ladder phase_scratch_own",
                                                     O.search_path(a["p"]["pkey"]))
        assert (b["dry"], b["ledger"]) == ("rf2", "preset-ladder phase_scratch_rederive")
    for a, b in zip(mine["start"], theirs["start"]):
        assert _strip(a, "x", "dry_sha", "path") == _strip(b, "x", "dry_sha", "path")
        assert a["path"] == O.start_path(a["p"]["pkey"]) and a["x"] == a["dry_sha"]

    d_rr = delta(lambda: RR.cmd_search(_args(row="fs-refit", rerun=True)))   # S1: the refused part once more
    theirs = _take(w, "start", "search")
    d_own = delta(lambda: O.cmd_search(_args(rerun=True)))
    mine = _take(w, "start", "search")
    assert d_own == d_rr and d_own["rerun_path"] > 0
    assert [x["p"]["pkey"] for x in mine["search"]] == [x["p"]["pkey"] for x in theirs["search"]] == [K2]
    assert mine["search"][0]["out"] == S.rerun_path(O.search_path(K2))
    assert mine["start"][0]["path"] == S.rerun_path(O.start_path(K2))
    assert _strip(mine["search"][0], *name_path) == _strip(theirs["search"][0], *name_path)
    searched = list(w["opened"])
    assert searched and not [p for p in searched if O.is_forbidden(p)]

    for f in (O.answers_path(), RR.answers_path("fs-refit")):        # the world's forbidden stand-ins
        f.unlink()
    d_rr = delta(lambda: RR.cmd_answers(_args(row="fs-refit")))
    theirs = _take(w, "answer_parts", "deciding_stop")
    d_own = delta(lambda: O.cmd_answers(_args()))
    mine = _take(w, "answer_parts", "deciding_stop")
    assert d_own == d_rr and d_own["rerun_refusal"] == 1
    a, b = mine["answer_parts"][0], theirs["answer_parts"][0]
    assert a["draw"] is b["draw"] and sorted(a["recs"]) == sorted(b["recs"])
    for k in a["recs"]:
        assert _strip(a["recs"][k], "dry", "dry_sha256") == _strip(b["recs"][k], "dry", "dry_sha256")
        assert a["recs"][k]["dry_sha256"] == S.npy_sha(w["own"][k])
    assert a["shas"][K2] == S.file_sha(S.rerun_path(O.search_path(K2)))   # the passing rerun's record
    assert mine["deciding_stop"] == theirs["deciding_stop"]
    ans = json.loads(O.answers_path().read_text())
    assert ans["dry"] == "vc-own" and ans["ref"] == "xlnoG@-3" and ans["reruns"] == {K2: "rerun passed"}
    assert ans["build_sha256"] == w["m"][SV.PHASE_DRY]["sha256"]

    w["m"][RD.answers_key("fs-refit")] = {"sha256": S.file_sha(RR.answers_path("fs-refit"))}
    w["m"][O.PHASE_ANSWERS] = {"sha256": S.file_sha(O.answers_path())}
    d_rr = delta(lambda: RR.cmd_score(_args(row="fs-refit")))
    theirs = _take(w, "score")
    d_own = delta(lambda: O.cmd_score(_args()))
    mine = _take(w, "score")
    assert d_own == d_rr and (d_own["nosep"], d_own["wait"], d_own["disk"]) == (1, 1, 2)
    assert len(mine["score"]) == len(theirs["score"]) == 2
    for a, b in zip(mine["score"], theirs["score"]):
        assert _strip(a, "row", "answers_sha") == _strip(b, "row", "answers_sha")
        assert (a["row"], a["answers_sha"]) == ("fs-own", S.file_sha(O.answers_path()))
    assert w["calls"]["spend"] == 3                                     # every render command: the gate first


def test_the_checks_mirror_fs_refits(monkeypatch, tmp_path):
    """check-score and check-search hand `score_row_part` and `run_part` what `rederive_rows`' `--for real` checks
    hand them, and pass when row (c)'s stored records repeat."""
    np = pytest.importorskip("numpy")
    from learn import note_replay as NRP
    from learn import pipeline_fix as P

    w = _world(monkeypatch, tmp_path)
    for kind in ("check-score", "check-search"):
        (RR.check_dir("real", kind) / "result.json").unlink()
        (O.check_dir(kind) / "result.json").unlink()
    ans_c = {"parts": {k: {"answer": {"a": 2.0}, "select": {}, "borrowed": []} for k in (K1, K2)}}
    P.save(S.answers_path("fs-both"), ans_c)
    monkeypatch.setattr(SN, "comparator_answers", lambda: ans_c)
    stored = {"scoring_control_ok": True, "distinct_renders": 3, "held": {"cen": 1.0}, "render_sha256": {"cen": "r"}}
    rec_c = {"step1": {"curve": [1.0, 0.9], "start": {"render_sha256": "s"}}, "renders": 12}
    for k in (K1, K2):
        P.save(S.score_path("fs-both", k), stored)
        P.save(S.search_path("fs-both", k), rec_c)
    P.save(NRP.replay_dir() / "blur.json", {"draw_sha256": "rd", "parts": {k: {"sha256": {SV.AVG_MILD: "am-" + k}}
                                                                            for k in (K1, K2)}})
    monkeypatch.setattr(NRP, "require_draw", lambda: w["draw"])
    monkeypatch.setattr(NRP, "load_dry", lambda dry, p, di32, blur: np.full(16, 0.25, np.float32))

    def run_part(p, dry, ref_name, x32, ref_blank, new_renderer, lists, **kw):
        w["calls"]["run_part"].append({"p": p, "dry": dry, "ref": ref_name, "x": S.npy_sha(x32),
                                       "blank": float(np.sum(ref_blank)), "lists": lists, **kw})
        return dict(rec_c)
    monkeypatch.setattr(S, "run_part", run_part)
    RR.cmd_check_score(_args(side="real"))
    RR.cmd_check_search(_args(side="real"))
    theirs = _take(w, "score", "run_part")
    O.cmd_check_score(_args())
    O.cmd_check_search(_args())
    mine = _take(w, "score", "run_part")
    assert mine == theirs and len(mine["score"]) == 2 and len(mine["run_part"]) == 2
    assert mine["run_part"][0]["budget"] == SN.CHECK_BUDGET and mine["run_part"][0]["step1_only"] is True
    for kind in ("check-score", "check-search"):
        r = json.loads((O.check_dir(kind) / "result.json").read_text())
        assert r["passed"] is True and r["mismatches"] == []
    with pytest.raises(SystemExit, match="never overwritten"):
        O.cmd_check_score(_args())


def test_the_search_refuses_a_guitar_that_is_not_build_jsons(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    w = _world(monkeypatch, tmp_path)
    np.save(SV.dry_path(SV.OWN, K1), np.zeros(10, np.float32))
    with pytest.raises(SystemExit, match="vc-own's file is not the one build.json declares"):
        O.cmd_search(_args())
    assert not w["calls"]["search"] and not w["calls"]["start"]


def test_the_search_refuses_samples_that_are_not_build_jsons(monkeypatch, tmp_path):
    from learn import pipeline_fix as P

    w = _world(monkeypatch, tmp_path)
    w["vb"]["parts"][K1]["guitars"][SV.OWN]["audio_sha256"] = "0" * 64
    P.save(SV.build_path(), w["vb"])
    w["m"][SV.PHASE_DRY] = {"sha256": S.file_sha(SV.build_path())}
    with pytest.raises(SystemExit, match="not build.json's audio_sha256"):
        O.cmd_search(_args())
    w["m"][SV.PHASE_DRY] = {"sha256": "1" * 64}
    with pytest.raises(SystemExit, match="is not main's phase_scratch_voice_dry"):
        O.cmd_search(_args())
    assert not w["calls"]["search"]


def test_a_searched_guitars_audio_stops_the_row(monkeypatch, tmp_path):
    w = _world(monkeypatch, tmp_path)
    w["rb"]["parts"][K1]["audio_sha256"] = S.npy_sha(w["own"][K1])     # vc-own is rf2's audio byte for byte
    with pytest.raises(SystemExit, match="no carry"):
        O.cmd_search(_args())
    assert not w["calls"]["search"]
    w["rb"]["parts"][K1]["audio_sha256"] = "x"
    w["b2"]["parts"][K1]["arms"][SE.BANK_ARM]["sha256"] = S.npy_sha(w["own"][K1])
    with pytest.raises(SystemExit, match="tr-di's audio"):
        O.cmd_search(_args())


def test_the_search_waits_for_its_checks_and_opens_nothing_scored(monkeypatch, tmp_path):
    w = _world(monkeypatch, tmp_path)
    (O.check_dir("check-search") / "result.json").write_text(json.dumps({"passed": False, "mismatches": [1]}))
    with pytest.raises(SystemExit, match="fs-own's search-check did not pass"):
        O.cmd_search(_args())
    (O.check_dir("check-search") / "result.json").write_text(json.dumps({"passed": True}))
    O.cmd_search(_args())
    assert w["opened"]
    assert not [p for p in w["opened"] if O.is_forbidden(p)]
    assert not set(map(str, w["forbidden"])) & set(map(str, w["opened"]))


def test_the_answers_wait_for_reruns_and_are_written_once(monkeypatch, tmp_path):
    w = _world(monkeypatch, tmp_path)
    O.answers_path().unlink()                                          # the world's stand-in forbidden file
    w["refuse_first"] = {K1}
    O.cmd_search(_args())
    with pytest.raises(SystemExit, match="not yet rerun once"):
        O.cmd_answers(_args())
    O.cmd_search(_args(rerun=True))
    O.cmd_answers(_args())
    with pytest.raises(SystemExit, match="never overwritten"):
        O.cmd_answers(_args())


def test_a_record_of_another_guitar_refuses_the_answers(monkeypatch, tmp_path):
    from learn import pipeline_fix as P

    w = _world(monkeypatch, tmp_path)
    O.answers_path().unlink()
    O.cmd_search(_args())
    P.save(O.search_path(K1), {"part": K1, "dry": "vc-own", "dry_sha256": w["xs"][K1]})
    with pytest.raises(SystemExit, match="not the declared one"):
        O.cmd_answers(_args())
    P.save(O.search_path(K1), {"part": K1, "dry": "tr-di", "dry_sha256": S.npy_sha(w["own"][K1])})
    with pytest.raises(SystemExit, match="no carry"):
        O.cmd_answers(_args())


# --- the read in a fake world (pure: set_rows and the stored rows stood in for) ---------------------------------------

def _fake_iv(vals, keys=None):
    xs = [v for k, v in vals.items() if v is not None and (keys is None or k in keys)]
    if not xs:
        return None
    m = sum(xs) / len(xs)
    return {"mean": m, "lo90": m - 0.05, "hi90": m + 0.05}


def test_the_read_holds_every_beside_figure_and_tags_only(monkeypatch, tmp_path):
    from learn import pipeline_fix as P

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path / "PF")
    keys = [f"bks__s{i}__u{i}.wav@1.0#r.wav|ac20" for i in range(6)] + \
        [f"goat__item_{i}@2.0#r.wav|pr12" for i in range(6)] + [f"panel__p{i}@3.0#r.wav|sw50r" for i in range(3)]
    draw = {"parts": [{"pkey": k, "set": k.split("__")[0], "cluster": f"x|c{i % 4}"} for i, k in enumerate(keys)]}
    monkeypatch.setattr(SE, "context", lambda: (draw, None))

    def set_rows(sd, draw_, values, keys_=None):
        iv = _fake_iv(values, keys_)
        if iv is None:
            return None
        by = {s: _fake_iv({k: v for k, v in values.items() if k.split("__")[0] == s}, keys_) for s in S.SETS}
        return dict({"bks_goat": {"all": iv, "clean": iv, "crunch": iv}, "deciding_pool": iv, "panel": by["panel"]},
                    **{s: by[s] for s in S.SETS})
    monkeypatch.setattr(SN, "set_rows", set_rows)
    monkeypatch.setattr(SL, "bp_rows", lambda sd, draw_, v: {"bp": _fake_iv(v), "bks": _fake_iv(v),
                                                              "panel": _fake_iv(v)})
    monkeypatch.setattr(SE, "share", lambda sd, draw_, num, den, keys=None: {"share": 0.4})
    monkeypatch.setattr(SE, "require_targets", lambda m: {"parts": {k: {"partner": k[:6]} for k in keys}})
    monkeypatch.setattr(SL, "g50_of", lambda draw_, name, m: ({k: 0.05 for k in keys}, {}, {}, []))

    def nums(g, refused=()):
        per = {k: {f: g + (0.01 * i if f == "G" else 0.0) for f in S.G_FIELDS} for i, k in enumerate(keys)}
        return {"per": per, "itt": per, "refused": {k: {"search": "x"} for k in refused}, "replaced": {},
                "control_misses": [], "answers_sha256": "a"}
    rows = {"b2": nums(0.01), "fs-stem": nums(-0.26), "fs-both": nums(-0.3)}
    monkeypatch.setattr(RR, "real_numbers", lambda m, draw_, sd, row: rows[row])
    monkeypatch.setattr(O, "own_numbers", lambda m, draw_, sd: nums(-0.2, refused=(keys[0],)))
    monkeypatch.setattr(O, "reproduce", lambda m, draw_, sd: {"holds": True, "exact": {}, "seen": {}})
    monkeypatch.setattr(O, "check_results", lambda: {"check-score": {"passed": True}, "check-search": {"passed": True}})
    per_s = {O.tag(k): 0.5 + i for i, k in enumerate(keys)}
    monkeypatch.setattr(O, "_hashed_rows", lambda m, path, phase, field: (
        ({"S": per_s} if phase == SV.PHASE_OUTCOME else {"Ux": per_s}), None))
    m = _ctl("XC-stands")
    monkeypatch.setattr(O, "require_own", lambda *ph: m)
    O.cmd_read(_args())
    rep = json.loads(O.report_path().read_text())
    rws = json.loads(O.rows_path().read_text())
    assert rep["code"] == "XW-part" and rep["xw"]["code"] == "XW-part"     # D_own -0.21 better, C_own +0.06 not matches
    D = rep["rows"]["D"]
    assert set(D) == {"D_own", "C_own", "vs_row_c", "b2_less_row_b"}
    for arm in O.ARMS:
        assert D["D_own"][arm]["the_40"] and arm in rep["arms"]["codes"]
    a = D["D_own"]["answer"]
    for f in ("the_40", "clean", "crunch", "all_47", "panel", "cluster_left_out", "cluster_left_out_range",
              "largest_three", "one_per_partner"):
        assert a.get(f) is not None, f
    assert len(a["cluster_left_out"]) == 4 and len(a["largest_three"]["tags"]) == 3
    r = rep["rows"]
    assert r["loudar"]["bp"] and r["loudar"]["parts"] == 9 and r["loudar"]["part_weighted_mean"] is not None
    assert r["loudar"]["reading"] and r["loudar"]["minus_reading"] and "passing_only" in r["loudar"]
    assert r["share_recovered"] == {"share": 0.4} and "-D_own" in r["share_label"]
    assert isinstance(r["ranks"]["S"]["rho"], float) and isinstance(r["ranks"]["Ux"]["rho"], float)
    assert r["passing_only"]["D_own"] and rep["passing_only"]["code"] and "shrunk_label" in rep
    assert rep["refusals"]["fs-own"]["refused"] == {O.tag(keys[0]): {"search": "x"}}
    assert rws["rows"]["D"] == rep["rows"]["D"] and "code" not in rws             # the rows saved before the code
    text = O.rows_path().read_text() + O.report_path().read_text()
    for k in keys:
        assert k not in text and k.split("@")[0] not in text
    with pytest.raises(SystemExit, match="never overwritten"):
        O.cmd_read(_args())


def test_the_read_refuses_under_xc_anomaly(monkeypatch):
    monkeypatch.setattr(O, "require_own", lambda *ph: _ctl("XC-anomaly"))
    with pytest.raises(SystemExit, match="construction is off"):
        O.cmd_read(_args())
    monkeypatch.setattr(O, "require_own", lambda *ph: {})
    with pytest.raises(SystemExit, match="audited outcome first"):
        O.cmd_answers(_args())


def test_the_loudar_rows_read_both_ways(monkeypatch):
    monkeypatch.setattr(SL, "bp_rows", lambda sd, draw, v: {"bp": _fake_iv(v)})
    sets = {"a": "bks", "b": "panel", "c": "goat"}
    r = O.loudar_rows(None, None, {"a": -0.3, "b": -0.25, "c": 9.0}, {"a": 0.0, "b": 0.0, "c": 0.0}, sets)
    assert r["parts"] == 2 and r["reading"] == "better" and "sits above" in r["said"]
    assert math.isclose(r["part_weighted_mean"], -0.275)
    r = O.loudar_rows(None, None, {"a": 0.0}, {"a": 0.0}, sets)
    assert r["reading"] == "matches" and r["minus_reading"] == "matches" and "not shown" in r["said"]


def test_a_stored_rows_file_is_read_only_at_mains_hash(tmp_path):
    p = tmp_path / "rows.json"
    assert O._hashed_rows({}, p, "phase_x", "rows_sha256")[0] is None
    p.write_text(json.dumps({"rows": {"per_part": {"S": {"abc": 1.0}}}}))
    assert "is not main's" in O._hashed_rows({}, p, "phase_x", "rows_sha256")[1]
    assert O._hashed_rows({"phase_x": {"rows_sha256": "0"}}, p, "phase_x", "rows_sha256")[0] is None
    got, why = O._hashed_rows({"phase_x": {"rows_sha256": S.file_sha(p)}}, p, "phase_x", "rows_sha256")
    assert got == {"S": {"abc": 1.0}} and why is None
