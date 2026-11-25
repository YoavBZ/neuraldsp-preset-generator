"""The rebuild's re-derivation, the rows (`learn/rederive_rows.py`, `docs/rederive-plan.md` section 7): the names and
gates, the carry, the guards (every command refuses off main, without its hashes, or with other code), the source of
the shared steps (called, never redefined or patched), the forbidden files, the splits' part sets, the codes with S1
and the null row's change. Synthetic keys. Pure tests run on the light CI runner (no numpy); the search's fake world
needs numpy (skipped elsewhere)."""
import ast
import json
import pathlib
import subprocess

import pytest

from learn import note_transcribe as NT
from learn import rederive_fit as RF
from learn import rederive_rows as RR
from learn import scratch_exact as SE
from learn import scratch_notes as SN
from learn import scratch_rederive as RD
from learn import scratch_search as S

REPO = pathlib.Path(__file__).resolve().parents[1]
SRC = (REPO / "learn" / "rederive_rows.py").read_text()
TREE = ast.parse(SRC)
GUARDED = tuple(NT.CODE_FILES) + ("learn/scratch_exact.py", "learn/scratch_search.py", "learn/scratch_notes.py",
                                  "learn/note_rebuild.py", "learn/scratch_rederive.py")


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


BELOW, SPANS, ABOVE = _iv(-0.3, -0.5, -0.1), _iv(0.05, -0.1, 0.2), _iv(0.3, 0.1, 0.5)


def _args(**kw):
    base = {"row": RR.NOW_ROW, "shard": (0, 1), "first": 0, "rerun": False, "stage": "1", "side": "bench"}
    return type("A", (), dict(base, **kw))()


# --- names, gates, the carry (pure) -----------------------------------------------------------------------------------

def test_names():
    assert RR.CODE_FILES[0] == RR.MODULE == "learn/rederive_rows.py" and set(RD.CODE_FILES) < set(RR.CODE_FILES)
    assert RR.ROWS == RD.ROWS and RR.REAL_DRY == "rf2" and RR.REAL_REF == "xlnoG" and RR.BASE == "xn-bank"
    assert set(RR.RUNG_CODES + RR.NULL_CODES + RR.BRIDGE_CODES) <= set(RD.XF_CODES)
    assert RR.FLOOR_ROWS == ("xf-fix", "xf-tuning", "xf-mutes", "xf-tilt", "xf-levels")
    assert sorted(RR.COMMANDS) == sorted(["check-score", "check-search", "floors", "floor-real", "null-build", "search",
                                          "answers", "score", "read", "read-real", "reproduce"])
    assert RR.MAX_SHARDS == 3 and RR.NULL_CHANGE == {"kind": "gain_db", "value": 0.01}
    assert RR.null_change_refusal(RR.NULL_CHANGE) is None


def test_the_carry_sources_are_rows_searched_before():
    order = (RR.BASE, RR.LIST_ROW, RR.NOW_ROW, RR.FIX_ROW) + RR.RUNG_ROWS
    for row, srcs in RR.CARRY_FROM.items():
        assert row not in srcs
        if row in order:
            assert all(order.index(s) < order.index(row) for s in srcs)
    assert RR.CARRY_FROM[RR.NULL_ROW] == (RR.BASE,) and RR.REAL_ROW not in RR.CARRY_FROM


def test_a_byte_identical_guitar_finds_its_source():
    shas = {"xn-bank": "x", "xn-list": "l", "xf-now": "n", "xf-fix": "f"}
    assert RR.carry_source("xf-now", "x", shas) == "xn-bank"
    assert RR.carry_source("xf-now", "l", shas) == "xn-list"
    assert RR.carry_source("xf-now", "n", shas) is None              # never itself
    assert RR.carry_source("xf-tilt", "n", shas) == "xf-now" and RR.carry_source("xf-tilt", "f", shas) == "xf-fix"
    assert RR.carry_source("xf-fix", "f", shas) is None and RR.carry_source("xf-fix", "z", shas) is None
    assert RR.carry_source("xf-now", None, {"xn-bank": None}) is None
    shas2 = dict(shas, **{"xn-list": "x"})                            # the first that matches, in order
    assert RR.carry_source("xf-now", "x", shas2) == "xn-bank"


def test_the_shard_rule():
    assert RR.shard_refusal((0, 1)) is None and RR.shard_refusal((2, 3)) is None
    for bad in ((0, 4), (3, 3), (-1, 2)):
        assert "at most 3" in RR.shard_refusal(bad)
    with pytest.raises(SystemExit, match="at most 3"):
        RR._guard_shard(_args(shard=(0, 4)))


def test_the_row_gates():
    now = {"sha256": "aa"}
    m = {RD.answers_key("xf-now"): now}
    assert RR.row_refusal("xf-now", {}) is None
    assert "only after stage 1" in RR.row_refusal("xf-fix", m, None)
    assert "XF-input" in RR.row_refusal("xf-fix", m, {"go_on": False, "code": "XF-input"})
    assert "refusal-sensitive" in RR.row_refusal("xf-fix", m, {"go_on": False, "code": None,
                                                               "label": "refusal-sensitive"})
    assert "not from main's" in RR.row_refusal("xf-fix", m, {"go_on": True, "answers_now_sha256": "bb"})
    assert RR.row_refusal("xf-fix", m, {"go_on": True, "answers_now_sha256": "aa"}) is None
    for code in RD.XF_CODES:
        mo = {RD.PHASE_BENCH_OUTCOME: {"code": code}}
        assert (RR.row_refusal("xf-mutes", mo) is None) == (code in ("XF-worse", "XF-part", "XF-undecided"))
        assert (RR.row_refusal("xf-null", mo) is None) == (code == "XF-part")
        assert (RR.row_refusal("fs-refit", mo) is None) == (code in ("XF-closed", "XF-part"))
        assert RR.row_refusal("fs-refit", {RD.PHASE_BENCH_OUTCOME: {"code": code, "bridge_user_go": True}}) is None
    assert "waits for the bench" in RR.row_refusal("fs-refit", {})
    assert "user's call" in RR.row_refusal("fs-refit", {RD.PHASE_BENCH_OUTCOME: {"code": "XF-input",
                                                                                 "bridge_user_go": "yes"}})
    assert "does not ask" in RR.row_refusal("xf-tilt", {}) and "unknown row" in RR.row_refusal("xn-list", {})


def test_the_null_change_must_be_declared():
    assert "not declared" in RR.null_change_refusal(None)
    assert "one of" in RR.null_change_refusal({"kind": "noise", "value": 1e-6})
    for v in (0, float("nan"), float("inf"), "0.01"):
        assert "finite, non-zero" in RR.null_change_refusal({"kind": "gain_db", "value": v})
    assert RR.null_change_refusal({"kind": "gain_db", "value": 0.01}) is None
    with pytest.raises(SystemExit, match="not declared"):
        RR.null_guitar([0.0], None)


def test_the_phases_each_command_reads():
    assert RR.bench_phases("xf-now") == (RD.PHASE_LADDER,)
    assert RR.bench_phases("xf-fix") == (RD.PHASE_LADDER, RD.PHASE_FROZEN, RD.answers_key("xf-now"))
    assert RR.bench_phases("xf-tilt") == (RD.PHASE_LADDER, RD.PHASE_FROZEN, RD.PHASE_BENCH_OUTCOME)
    assert RR.bench_phases("xf-null") == (RD.PHASE_LADDER, RD.PHASE_BENCH_OUTCOME)
    assert RR.row_phases("fs-refit") == (RD.PHASE_FROZEN, RD.PHASE_BENCH_OUTCOME, SE.PHASE_B2_ANSWERS)


# --- the read's parts and codes (pure) --------------------------------------------------------------------------------

def test_the_design_time_parts_by_rule():
    dec = ["bks__a|x", "bks__b|y", "goat__c|z", "goat__d|w"]
    tx = {"bks__a|x": None, "bks__b|y": 3.0, "goat__c|z": 10.0, "goat__d|w": 1.0}
    tl = {"bks__a|x": None, "bks__b|y": 2.0, "goat__c|z": -7.0, "goat__d|w": None}
    assert RR.design_time_parts(["bks__a|x"], tx, tl, dec) == ["bks__a|x", "goat__c|z"]
    assert RR.design_time_parts([], {}, {}, dec) == []                # no tilt anywhere: no tilt part
    assert RR.tilt_parts({"bks__b|y": True, "goat__c|z": True, "panel__e|v": True}, dec) == ["bks__b|y", "goat__c|z"]
    assert RR.contributions({"a": 1.0, "b": 2.0}, {"a"}) == {"a": 1.0, "b": 0.0}


def test_s1_the_passing_only_code_beside():
    code, cp, label = RR.with_passing(RD.xf_stage1, (SPANS,), None)
    assert code["code"] == "XF-input" and cp is None and label is None
    code, cp, label = RR.with_passing(RD.xf_stage1, (SPANS,), (SPANS,))
    assert cp["code"] == "XF-input" and label is None
    code, cp, label = RR.with_passing(RD.xf_stage1, (ABOVE,), (SPANS,))      # go on against XF-input
    assert code["go_on"] and cp["code"] == "XF-input" and label == S.REFUSAL_SENSITIVE
    code, cp, label = RR.with_passing(RD.xf_stage1, (ABOVE,), (None,))
    assert cp == {"code": None, "reading": S.NO_PASSING_INTERVAL} and label is None
    code, cp, label = RR.with_passing(RD.xf_read, (ABOVE, SPANS, BELOW), (ABOVE, ABOVE, BELOW))
    assert code["code"] == "XF-closed" and cp["code"] == "XF-part" and label == S.REFUSAL_SENSITIVE
    code, cp, label = RR.with_passing(RD.rf_code, (ABOVE, BELOW), (ABOVE, SPANS))
    assert code["code"] == "RF-closer" and cp["code"] == "RF-undecided" and label == S.REFUSAL_SENSITIVE
    assert RR.eff_code({"code": None, "go_on": True}) == RR.GO_ON and RR.eff_code(None) is None


def _fake_rows(monkeypatch):
    """`set_rows` stood in for: the mean of the values given, +-0.1; it records the keys it was asked for."""
    calls = []

    def fake(sd, draw, values, keys=None):
        vals = {k: v for k, v in values.items() if v is not None and (keys is None or k in keys)}
        calls.append(sorted(vals))
        if not vals:
            return None
        mean = sum(vals.values()) / len(vals)
        iv = _iv(mean, mean - 0.1, mean + 0.1)
        return {"bks_goat": {"all": iv, "clean": iv, "crunch": iv}, "deciding_pool": iv, "panel": iv,
                "bks": iv, "goat": iv, "leave_one_cluster_out": {}}
    monkeypatch.setattr(SN, "set_rows", fake)
    return calls


def test_the_splits_read_the_declared_part_sets(monkeypatch):
    calls = _fake_rows(monkeypatch)
    vals = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0, "p": 9.0}
    groups = {"deciding": ["a", "b", "c", "d"], "clusters": [["a"], ["b", "c"], ["d"]], "one_per_partner": ["a", "c"],
              "design_time": ["d"], "tilt": ["a", "b"], "rest": ["c", "d"]}
    s = RR.splits(None, None, vals, groups)
    assert s["the_40"]["mean"] == pytest.approx(19 / 5) and s["parts"] == 5
    assert [c["mean"] for c in s["cluster_left_out"]] == pytest.approx([3.0, 2.5, 2.0])
    assert s["cluster_left_out_range"] == pytest.approx([2.0, 3.0])
    assert s["one_per_partner"] == {"parts": 2, "iv": _iv(2.0, 1.9, 2.1)}
    assert s["without_design_time"]["iv"]["mean"] == pytest.approx(15 / 4)      # d (and only d) left out
    t = s["tilt_15_vs_25"]
    assert t["label"] == RR.SEEN_LABEL and t["tilt"]["mean"] == 1.5 and t["rest"]["mean"] == 3.5
    assert t["tilt_contribution"]["mean"] == pytest.approx(3 / 5)               # the others at 0, the mean of all
    assert ["a", "b", "c", "d", "p"] in calls
    short = RR.splits(None, None, vals, groups, full=False)
    assert "cluster_left_out" not in short and short["all_47"]["mean"] == pytest.approx(19 / 5)
    f = RR.figure(None, None, {"a": {"G": 1.0, "G_shrunk": 0.5, "G_cp50": 0.1, "G_cp100": 0.2, "G_cp200": 0.3}},
                  {"a": {"G": 0.0, "G_shrunk": 0.0, "G_cp50": 0.0, "G_cp100": 0.0, "G_cp200": 0.0}},
                  dict(groups, deciding=["a"], clusters=[["a"]]))
    assert set(f) == set(RR.ARMS) and f["answer"]["the_40"]["mean"] == 1.0 and f["shrunk"]["the_40"]["mean"] == 0.5
    assert "one_per_partner" in f["answer"] and "one_per_partner" not in f["cp50"]
    assert f["answer"]["reading"] == SN.paired_reading(f["answer"]["the_40"])


def test_the_seen_figures_are_the_declarations():
    assert RR.SEEN["D_list"] == (0.321, 0.180, 0.462) and RR.SEEN["b2_less_row_b"] == (0.274, 0.186, 0.361)
    assert RR._close(_iv(0.3211, 0.17974, 0.46244), RR.SEEN["D_list"])
    assert not RR._close(_iv(0.3216, 0.1797, 0.4624), RR.SEEN["D_list"]) and not RR._close(None, (0, 0, 0))


# --- the forbidden files (pure) ---------------------------------------------------------------------------------------

def test_the_search_never_opens_anything_scored(tmp_path):
    ex, rd = tmp_path / "fs" / "exact", tmp_path / "fs" / "rederive"
    for p in [ex / n for n in SE.SEARCH_FORBIDDEN] + [ex / d / "k.json" for d in SE.SEARCH_FORBIDDEN_DIRS] + [
            rd / "answers-xf-now.json", rd / "score" / "xf-now" / "k.json", rd / "score-rerun" / "xf-now" / "k.json",
            rd / "floors" / "k.json", rd / "floors-real" / "k.json", rd / "rows-stage1.json",
            rd / "report-stage1.json", rd / "reproduce.json"]:
        assert RR.is_forbidden(p), p
        with pytest.raises(SystemExit, match="never opens"):
            RR.search_open(p)
    for p in (ex / "build.json", ex / "records.json", ex / "record" / "k.npy", ex / "search" / "xn-bank" / "k.json",
              rd / "ladder.json", rd / "build-bench.json", rd / "build-real.json", rd / "build-null.json",
              rd / "stage1-go.json", rd / "dry" / "xf-now" / "k.npy", rd / "search" / "xf-now" / "k.json",
              rd / "checks" / "bench" / "check-score" / "result.json"):
        assert not RR.is_forbidden(p), p


def test_the_answers_path_of_every_row():
    """Public: `rederive_diag` reads each row's answers through it."""
    paths = {r: RR.answers_path(r) for r in RD.ROWS}
    assert set(paths) == {"xf-now", "xf-fix", "xf-null", "xf-tuning", "xf-mutes", "xf-tilt", "xf-levels", "fs-refit"}
    assert len(set(paths.values())) == len(paths)
    for r, p in paths.items():
        assert p == RD.rederive_dir() / f"answers-{r}.json" and RR.is_forbidden(p)    # never opened by a search
    for bad in ("xn-list", "fs-notes", ""):
        with pytest.raises(ValueError, match="unknown row"):
            RR.answers_path(bad)


def test_unit_3s_files_are_read_through_its_own_code():
    """`rederive_fit` (Unit 3, PR #625) is imported, never copied: its builds' rows, record paths and guitar paths."""
    assert RR.RF is RF and RR.BUILDS is RF.BUILDS and RR.BUILDS == {"bench": "xf-fix", "real": "fs-refit"}
    for kind, row in RF.BUILDS.items():
        assert RR.build_path(kind) == RF.build_record_path(kind)
        assert RR.guitar_path(row, "a/b") == RF.guitar_path(row, "a/b")
    assert RR.guitar_row("fs-refit") == RR.guitar_row("rf2") == "fs-refit" and RR.guitar_row("xf-fix") == "xf-fix"
    defined = {n.name for n in TREE.body if isinstance(n, ast.FunctionDef)}
    assert not defined & {"build_record_path", "frozen_path", "fit_dir", "freeze_body", "fit"}
    calls = _calls()
    assert {"RF.guitar_path", "RF.build_record_path", "RF.frozen_path"} <= calls


def test_the_paths_follow_stubs_of_unit_3s(monkeypatch, tmp_path):
    monkeypatch.setattr(RF, "guitar_path", lambda row, pk: tmp_path / "g" / row / pk)
    monkeypatch.setattr(RF, "build_record_path", lambda which: tmp_path / f"b-{which}.json")
    assert RR.guitar_path("xf-fix", "k") == tmp_path / "g" / "xf-fix" / "k"
    assert RR.guitar_path("fs-refit", "k") == tmp_path / "g" / "fs-refit" / "k"
    assert RR.build_path("real") == tmp_path / "b-real.json"


FROZEN = {"sha256": "f" * 64, "rule": {"candidate": "c03"}, "stop": 9,
          "build_bench": {"sha256": "b" * 64, "row": "xf-fix"}, "build_real": {"sha256": "r" * 64, "row": "fs-refit"}}


def test_the_frozen_key_as_freeze_prints_it():
    m = {RD.PHASE_FROZEN: FROZEN}
    assert RR.frozen_refusal(m, "bench", "b" * 64) is None and RR.frozen_refusal(m, "real", "r" * 64) is None
    assert "is not main's" in RR.frozen_refusal(m, "bench", "r" * 64)
    assert "has no build_real sha256" in RR.frozen_refusal({RD.PHASE_FROZEN: {"sha256": "f"}}, "real", "r" * 64)
    assert "has no build_bench" in RR.frozen_refusal({}, "bench", "b")
    bad = {RD.PHASE_FROZEN: dict(FROZEN, build_bench={"sha256": "b" * 64, "row": "fs-refit"})}
    assert "is for fs-refit" in RR.frozen_refusal(bad, "bench", "b" * 64)


def test_a_build_record_in_unit_3s_format():
    part = {"file_sha256": "1", "audio_sha256": "2", "values": {}, "pass_used": 3}
    bench = {"row": "xf-fix", "rule": "c03", "stop": 9, "parts": {"k1": part, "k2": part}}
    real = {"row": "fs-refit", "build": "rf2", "rule": "c03", "stop": 9, "parts": {"k1": part},
            "rule_off_is_x": {"held": 1, "of": 1}}
    assert RR.build_refusal(bench, "bench", FROZEN) is None and RR.build_refusal(real, "real", FROZEN) is None
    assert "is for fs-refit" in RR.build_refusal(dict(bench, row="fs-refit"), "bench", FROZEN)
    assert "frozen rule and stop" in RR.build_refusal(dict(bench, rule="today"), "bench", FROZEN)
    assert "frozen rule and stop" in RR.build_refusal(dict(bench, stop=8), "bench", FROZEN)
    assert "names no" in RR.build_refusal(dict(bench, parts={"k1": {"file_sha256": "1"}}), "bench", FROZEN)
    assert "names no" in RR.build_refusal(dict(bench, parts={}), "bench", FROZEN)
    assert "rule off" in RR.build_refusal(dict(real, rule_off_is_x={"held": 0, "of": 1}), "real", FROZEN)
    assert "rule off" in RR.build_refusal({k: v for k, v in real.items() if k != "rule_off_is_x"}, "real", FROZEN)
    w = {"bench": bench, "real": real, "ladder": {"parts": {"k1": {"files": {"xf-now": {"audio_sha256": "n"}}}}}}
    assert RR.file_entry("xf-fix", "k1", w) is part and RR.file_entry("fs-refit", "k1", w) is part
    assert RR.guitar_sha("xf-fix", "k1", w) == "2" and RR.guitar_sha("xf-now", "k1", w) == "n"
    assert RR.guitar_sha("xf-fix", "zz", w) is None and RR.guitar_sha("xf-null", "k1", w) is None


def test_the_paths():
    assert RR.rows_dir() == RD.rederive_dir()
    for row in RD.LADDER_WRITES:
        assert RR.guitar_path(row, "bks__k/1") == RD.dry_path(row, "bks__k/1")
    assert RR.guitar_path("xf-null", "k").parent.name == "xf-null"
    with pytest.raises(ValueError):
        RR.guitar_path("xn-list", "k")
    assert RR.search_path("xf-now", "a/b").name == "a__b.json" and RR.score_path("xf-now", "k").parent.name == "xf-now"
    for k in ("bench", "real"):
        assert RR.build_path(k) == RF.build_record_path(k)
    assert RR.check_dir("real", "check-score").parent.parent.name == "checks"
    for bad in (("x", "check-score"), ("bench", "score")):
        with pytest.raises(ValueError):
            RR.check_dir(*bad)
    assert RR.rows_dir() != SE.exact_dir() and RR.search_path("xn-bank", "k") != SE.search_path("xn-bank", "k")


# --- the source: the shared steps are called unchanged ----------------------------------------------------------------

def _calls():
    out = set()
    for node in ast.walk(TREE):
        f = getattr(node, "func", None)
        if isinstance(node, ast.Call) and isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            out.add(f"{node.func.value.id}.{node.func.attr}")
    return out


SHARED = ("S.search_row_part", "SE.start_reference", "SE.score_exact_part", "SN.start_reference", "S.score_row_part",
          "S.answer_parts", "SE.xn_answer_parts", "S.read_row_parts", "S.run_part", "SN.set_rows",
          "SN.paired_reading", "S.with_reruns", "S.itt_per", "SE.synthetic_part", "SE.load_record_blank",
          "S.load_ref_blank", "SE.one_per_partner", "SN.carry_candidates", "SE.dry_refusal")


def test_the_shared_steps_are_called():
    missing = [c for c in SHARED if c not in _calls()]
    assert not missing


def test_the_shared_steps_are_never_redefined_or_patched():
    names = {c.split(".")[1] for c in SHARED} - {"start_reference"}
    defined = {n.name for n in TREE.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    assert not names & defined
    assert "start_reference" not in defined and "score_exact_part" not in defined
    aliases = {"S", "SE", "SN", "RD", "RF", "NT", "NR", "R", "P", "AM", "CB", "LO", "C", "K"}
    for node in ast.walk(TREE):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(
            node, (ast.AugAssign, ast.AnnAssign)) else []
        for t in targets:
            assert not (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id in aliases), \
                ast.dump(t)
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
    assert mods <= {"__future__", "argparse", "json", "math", "pathlib", "time", "learn"}


def test_the_guarded_files_are_unchanged_against_the_base():
    """The per-PR check: none of the guarded files differs from the merge base with origin/main (skipped without git
    history)."""
    base = subprocess.run(["git", "-C", str(REPO), "merge-base", "origin/main", "HEAD"], capture_output=True, text=True)
    if base.returncode:
        pytest.skip("no origin/main here")
    r = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", base.stdout.strip(), "HEAD", "--", *GUARDED])
    assert r.returncode == 0


# --- the guards: every command refuses --------------------------------------------------------------------------------

CASES = [("check-score", {}), ("check-score", {"side": "real"}), ("check-search", {}), ("floors", {}),
         ("floor-real", {}), ("null-build", {}), ("read", {}), ("read", {"stage": "2"}), ("read", {"stage": "rungs"}),
         ("read-real", {}), ("reproduce", {})] + [
    (c, {"row": r}) for c in ("search", "answers", "score") for r in RD.ROWS]
BASE_KEYS = (S.PHASE, S.PHASE_DRAW, SE.PHASE_BANK, SE.PHASE, SE.PHASE_TARGETS)
READ_BASE = (SE.answers_key("xn-bank"), SE.answers_key("xn-list"), SE.PHASE_B2_ANSWERS, RD.PHASE_LADDER,
             RD.answers_key("xf-now"))


def _phases(cmd, kw):
    """The keys each command must find on main, in the order it asks for them."""
    row = kw.get("row")
    if cmd in ("check-score", "check-search"):
        return ()
    if cmd == "floors":
        return (RD.PHASE_LADDER, RD.PHASE_FROZEN, RD.answers_key("xf-now"))
    if cmd == "floor-real":
        return RR.REAL_PHASES
    if cmd == "null-build":
        return (RD.PHASE_LADDER, RD.PHASE_BENCH_OUTCOME)
    if cmd == "read":
        return READ_BASE + {"1": (), "2": (RD.PHASE_FROZEN, RD.answers_key("xf-fix")),
                            "rungs": (RD.PHASE_BENCH_OUTCOME,)}[kw.get("stage", "1")]
    if cmd == "read-real":
        return RR.REAL_PHASES + (RD.answers_key("fs-refit"), S.phase_answers("fs-stem"), S.phase_answers("fs-both"),
                                 SE.answers_key("xn-bank"), SE.answers_key("xn-list"))
    if cmd == "reproduce":
        return (SE.answers_key("xn-bank"), SE.answers_key("xn-list"), SE.PHASE_B2_ANSWERS, S.phase_answers("fs-stem"))
    return RR.row_phases(row) + ((RD.answers_key(row),) if cmd == "score" else ())


@pytest.mark.parametrize("cmd,kw", CASES)
def test_every_command_refuses_off_main(monkeypatch, cmd, kw):
    monkeypatch.setattr(S, "on_main", lambda: (None, "this checkout's learn/scratch_search.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        RR.COMMANDS[cmd](_args(**kw))


@pytest.mark.parametrize("cmd,kw", CASES)
def test_every_command_refuses_without_its_hashes_on_main(monkeypatch, cmd, kw):
    from learn import note_replay as NRP

    main = {k: {} for k in BASE_KEYS}
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    monkeypatch.setattr(NRP, "ledger_entry", lambda: main)
    monkeypatch.setattr(RD, "pinned_identity", lambda: {f: True for f in RD.CODE_FILES})
    with pytest.raises(SystemExit, match="has no phase_scratch_rederive:"):
        RR.COMMANDS[cmd](_args(**kw))
    main[RD.PHASE] = {}
    for k in _phases(cmd, kw):
        with pytest.raises(SystemExit, match=f"has no {k}:"):
            RR.COMMANDS[cmd](_args(**kw))
        main[k] = {}


@pytest.mark.parametrize("cmd,kw", CASES)
def test_every_command_refuses_with_other_code(monkeypatch, cmd, kw):
    from learn import note_replay as NRP

    main = {k: {} for k in BASE_KEYS + (RD.PHASE,) + _phases(cmd, kw)}
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    monkeypatch.setattr(NRP, "ledger_entry", lambda: main)
    monkeypatch.setattr(RD, "pinned_identity", lambda: {f: True for f in RD.CODE_FILES})
    monkeypatch.setattr(RR, "pinned_identity", lambda: {RR.MODULE: False})
    with pytest.raises(SystemExit, match="rederive_rows.py.*differ from main's"):
        RR.COMMANDS[cmd](_args(**kw))
    monkeypatch.setattr(RR, "pinned_identity", lambda: {RR.MODULE: True})
    monkeypatch.setattr(NT, "redo_on_main", lambda: ({}, "this checkout's note_rebuild.py differs from main's"))
    with pytest.raises(SystemExit, match="note_rebuild.py differs"):
        RR.COMMANDS[cmd](_args(**kw))
    monkeypatch.setattr(RD, "pinned_identity", lambda: {"learn/scratch_exact.py": False})
    with pytest.raises(SystemExit, match="scratch_exact.py.*differ from main's"):
        RR.COMMANDS[cmd](_args(**kw))


def test_the_cli():
    with pytest.raises(SystemExit):
        RR.main(["search"])                                       # needs --row
    with pytest.raises(SystemExit):
        RR.main(["search", "--row", "xf-now", "--shard", "0/4"])  # at most 3 shards
    with pytest.raises(SystemExit):
        RR.main(["read", "--stage", "3"])


# --- the bench search in a fake world (numpy; skipped on the light runner) --------------------------------------------

K1, K2 = "bks__set0__k1.wav@1.0#r.wav|ac20", "goat__item_0@2.0#r.wav|pr12"     # synthetic keys


def _bench_world(monkeypatch, tmp_path, now_same_as_x=True):
    """`cmd_search` on two made-up parts with every source but the files stood in for: part 1's xf-now guitar is X
    (byte-identical), part 2's is not. The forbidden files exist and must never be opened."""
    np = pytest.importorskip("numpy")
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import note_replay as NRP
    from learn import pipeline_fix as P

    ex, rd = tmp_path / "fs" / "exact", tmp_path / "fs" / "rederive"
    monkeypatch.setattr(SE, "exact_dir", lambda: ex)
    monkeypatch.setattr(RD, "rederive_dir", lambda: rd)
    rng = np.random.default_rng(0)
    X = {k: rng.standard_normal(4000).astype(np.float32) for k in (K1, K2)}
    now = {K1: X[K1] if now_same_as_x else X[K1] * 2, K2: X[K2] * 0.5}
    xs = {k: S.npy_sha(v) for k, v in X.items()}
    b2 = {"parts": {k: {"arms": {SE.BANK_ARM: {"sha256": xs[k]}}} for k in X}}
    lst = {k: S.npy_sha(v * 3) for k, v in X.items()}
    build = {"proofs_hold": True, "parts": {k: {"guitars": {"xn-list": {"sha256": lst[k]}}} for k in X}}
    P.save(SE.build_path(), build)
    lad = {"proofs_hold": True, "parts": {}}
    recs = {"lag_failed": [], "row_b_not_reproduced": [], "parts": {}}
    for k in X:
        p = RD.dry_path("xf-now", k)
        p.parent.mkdir(parents=True, exist_ok=True)
        np.save(p, now[k])
        lad["parts"][k] = {"files": {"xf-now": {"file_sha256": S.file_sha(p), "audio_sha256": S.npy_sha(now[k])}}}
        rp = SE.record_path(k)
        rp.parent.mkdir(parents=True, exist_ok=True)
        np.save(rp, X[k].astype(np.float64))
        recs["parts"][k] = {"file_sha256": S.file_sha(rp)}
        P.save(SE.search_path("xn-bank", k), {"part": k, "dry": "xn-bank", "dry_sha256": xs[k], "answer": {}})
    P.save(RD.ladder_path(), lad)
    P.save(SE.records_path(), recs)
    for side in ("bench", "real"):
        for kind in ("check-score", "check-search"):
            P.save(RR.check_dir(side, kind) / "result.json", {"passed": True})
    forbidden = [ex / "targets.json", ex / "floors.json", ex / "score" / "xn-bank" / f"{SE._f(K1)}.json",
                 rd / "answers-xf-now.json", rd / "score" / "xf-now" / f"{SE._f(K1)}.json", ex / "rows.json"]
    for f in forbidden:
        P.save(f, {"held": {"answer": 1.0}})
    m = {SE.PHASE_TARGETS: {"build_sha256": S.file_sha(SE.build_path()),
                            "records_sha256": S.file_sha(SE.records_path())},
         RD.PHASE_LADDER: {"sha256": S.file_sha(RD.ladder_path())}}
    monkeypatch.setattr(RR, "require_rows", lambda *ph: m)
    monkeypatch.setattr(SE, "bank_build", lambda mm: b2)
    monkeypatch.setattr(NT, "load_dry", lambda arm, k, b: X[k])
    draw = {"parts": [{"pkey": k, "set": k.split("__")[0], "lag": 7, "search": "A", "held": "B",
                       "cen": {"settings": {}, "select": {}}} for k in (K1, K2)]}
    monkeypatch.setattr(SE, "context", lambda: (draw, None))
    monkeypatch.setattr(SE, "disk_guard", lambda: None)
    monkeypatch.setattr(NRP, "no_separation_beside", lambda: None)
    monkeypatch.setattr(C, "mic_lists", lambda: {})
    monkeypatch.setattr(LO, "_wait_cap", lambda cap=3: None)
    monkeypatch.setattr(CB, "new_renderer", object())
    calls = {"start": [], "search": []}

    def start_ref(dry, p, x32, ref_blank, new_renderer, path, dry_sha):
        calls["start"].append((dry, p["pkey"], p["lag"], S.npy_sha(x32), dry_sha, path))
        return 0.5, 2

    def search(p, dry, ref_name, x32, ref_blank, new_renderer, lists, out, ledger, start_ref=None, dry_sha256=None):
        calls["search"].append({"part": p["pkey"], "lag": p["lag"], "dry": dry, "ref": ref_name,
                                "x_sha": S.npy_sha(x32), "start_ref": start_ref, "dry_sha256": dry_sha256,
                                "ledger": ledger, "out": out, "blank_zeros": float(np.abs(ref_blank).sum())})
        rec = {"part": p["pkey"], "dry": dry, "dry_sha256": dry_sha256, "renders": 10}
        P.save(out, rec)
        return rec
    monkeypatch.setattr(SE, "start_reference", start_ref)
    monkeypatch.setattr(S, "search_row_part", search)
    opened = []
    real_read_text, real_read_bytes, real_load = pathlib.Path.read_text, pathlib.Path.read_bytes, np.load
    monkeypatch.setattr(pathlib.Path, "read_text", lambda self, *a, **k: (opened.append(self),
                                                                         real_read_text(self, *a, **k))[1])
    monkeypatch.setattr(pathlib.Path, "read_bytes", lambda self: (opened.append(self), real_read_bytes(self))[1])
    monkeypatch.setattr(np, "load", lambda f, *a, **k: (opened.append(pathlib.Path(f)), real_load(f, *a, **k))[1])
    return {"X": X, "now": now, "xs": xs, "calls": calls, "opened": opened, "forbidden": forbidden, "m": m}


def test_a_byte_identical_guitar_carries_its_record_and_the_rest_search_unchanged(monkeypatch, tmp_path, capsys):
    w = _bench_world(monkeypatch, tmp_path)
    RR.cmd_search(_args(row="xf-now"))
    out1, src1 = RR.search_path("xf-now", K1), SE.search_path("xn-bank", K1)
    assert out1.read_bytes() == src1.read_bytes()                    # carried byte for byte
    assert [c["part"] for c in w["calls"]["search"]] == [K2]         # only the changed part searched
    c = w["calls"]["search"][0]
    assert c["lag"] == 0 and c["dry"] == "xf-now" and c["ref"] == SE.REF   # the exact world's part at lag 0
    assert c["x_sha"] == c["dry_sha256"] == S.npy_sha(w["now"][K2]) and c["start_ref"] == 0.5
    assert c["ledger"] == f"{RD.LEDGER_ID} {RD.PHASE}" and c["out"] == RR.search_path("xf-now", K2)
    assert w["calls"]["start"][0][:5] == ("xf-now", K2, 0, c["x_sha"], c["x_sha"])
    assert w["calls"]["start"][0][5] == RR.start_path("xf-now", K2)
    assert "1 carried" in capsys.readouterr().out


def test_the_search_opens_none_of_the_forbidden_files(monkeypatch, tmp_path):
    w = _bench_world(monkeypatch, tmp_path)
    RR.cmd_search(_args(row="xf-now"))
    assert w["opened"]
    bad = [p for p in w["opened"] if SE.is_forbidden(p) or RR.is_forbidden(p)]
    assert not bad
    assert not set(map(str, w["forbidden"])) & set(map(str, w["opened"]))


def test_a_carry_waits_for_its_source_and_a_rerun_takes_the_sources_rerun(monkeypatch, tmp_path):
    from learn import pipeline_fix as P

    w = _bench_world(monkeypatch, tmp_path)
    SE.search_path("xn-bank", K1).unlink()
    with pytest.raises(SystemExit, match="not there yet"):
        RR.cmd_search(_args(row="xf-now"))
    P.save(SE.search_path("xn-bank", K1), {"refused": {"start": 1}, "dry_sha256": w["xs"][K1]})
    RR.cmd_search(_args(row="xf-now"))
    P.save(S.rerun_path(SE.search_path("xn-bank", K1)), {"part": K1, "dry": "xn-bank", "again": True})
    RR.cmd_search(_args(row="xf-now", rerun=True))
    assert S.rerun_path(RR.search_path("xf-now", K1)).read_bytes() == \
        S.rerun_path(SE.search_path("xn-bank", K1)).read_bytes()


def test_a_guitar_that_is_not_the_declared_one_refuses(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    _bench_world(monkeypatch, tmp_path, now_same_as_x=False)
    np.save(RD.dry_path("xf-now", K2), np.zeros(10, np.float32))
    with pytest.raises(SystemExit, match="not the declared one"):
        RR.cmd_search(_args(row="xf-now"))


def test_the_ladder_must_be_mains(monkeypatch, tmp_path):
    w = _bench_world(monkeypatch, tmp_path)
    w["m"][RD.PHASE_LADDER] = {"sha256": "0" * 64}
    with pytest.raises(SystemExit, match="is not main's phase_scratch_rederive_ladder"):
        RR.cmd_search(_args(row="xf-now"))
    w["m"][RD.PHASE_LADDER] = {"ladder_sha256": S.file_sha(RD.ladder_path())}     # the old field name: refused
    with pytest.raises(SystemExit, match="has no sha256"):
        RR.cmd_search(_args(row="xf-now"))


def test_the_search_waits_for_its_checks(monkeypatch, tmp_path):
    _bench_world(monkeypatch, tmp_path)
    (RR.check_dir("bench", "check-search") / "result.json").write_text(json.dumps({"passed": False,
                                                                                   "mismatches": [1]}))
    with pytest.raises(SystemExit, match="bench search-check did not pass"):
        RR.cmd_search(_args(row="xf-now"))


def test_the_null_guitar_and_its_recomputation():
    np = pytest.importorskip("numpy")
    x = np.linspace(-0.5, 0.5, 101).astype(np.float32)
    y = RR.null_guitar(x, {"kind": "gain_db", "value": 0.01})
    assert y.dtype == np.float32 and S.npy_sha(y) != S.npy_sha(x)
    assert np.max(np.abs(y - x)) <= 0.5 * (10 ** (0.01 / 20) - 1) + 1e-7
    assert S.npy_sha(RR.null_guitar(x, {"kind": "gain_db", "value": 0.01})) == S.npy_sha(y)   # deterministic


def test_the_real_row_carries_build_2s_record_once_its_start_reference_repeats(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    from learn import pipeline_fix as P

    w = _bench_world(monkeypatch, tmp_path)
    nb = tmp_path / "fs" / "notes-b2"
    monkeypatch.setattr(SN, "build_dir", lambda name=None: nb if name == "b2" else tmp_path / "fs" / "notes")
    fit = tmp_path / "fs" / "rederive" / "stub-fit"                  # rederive_fit's paths stood in for
    monkeypatch.setattr(RF, "guitar_path", lambda row, pk: fit / "dry" / row / f"{SE._f(pk)}.npy")
    monkeypatch.setattr(RF, "build_record_path", lambda which: fit / f"build-{which}.json")
    monkeypatch.setattr(RF, "frozen_path", lambda: fit / "frozen.json")
    rf = {K1: w["X"][K1], K2: w["X"][K2] * 0.25}                     # part 1's rf2 is build 2's tr-di
    rb = {"plan": "p", "renders": 0, "row": "fs-refit", "build": "rf2", "rule": "c03", "stop": 9, "parts": {},
          "rule_off_is_x": {"held": 2, "of": 2}, "hits": []}
    for k, y in rf.items():
        p = RF.guitar_path("fs-refit", k)
        p.parent.mkdir(parents=True, exist_ok=True)
        np.save(p, y)
        rb["parts"][k] = {"file_sha256": S.file_sha(p), "audio_sha256": S.npy_sha(y), "values": {}, "pass_used": 2,
                          "end": "repeat", "reached": False, "identical_to_x": k == K1}
        P.save(SN.record_path("search", k, "b2"), {"part": k, "dry": "tr-di", "dry_sha256": w["xs"][k]})
        P.save(SN.record_path("start-ref", k, "b2"), {"render_sha256": "r-" + k})
    P.save(RF.build_record_path("real"), rb)
    P.save(RF.frozen_path(), {"rule": {"candidate": "c03"}})
    w["m"][RD.PHASE_FROZEN] = dict(FROZEN, sha256=S.file_sha(RF.frozen_path()),
                                   build_real={"sha256": S.file_sha(RF.build_record_path("real")), "row": "fs-refit"})
    w["m"][RD.PHASE_BENCH_OUTCOME] = {"code": "XF-closed"}
    monkeypatch.setattr(S, "load_ref_blank", lambda sd, p, ref: np.zeros(8))
    sref = []

    def start_ref(p, x32, ref_blank, new_renderer, path, dry_sha):
        sref.append(p["pkey"])
        P.save(path, {"dry_sha256": dry_sha, "value": 0.5, "render_sha256": "r-" + p["pkey"]})
        return 0.5, 2
    monkeypatch.setattr(SN, "start_reference", start_ref)
    RR.cmd_search(_args(row="fs-refit"))
    assert RR.search_path("fs-refit", K1).read_bytes() == SN.record_path("search", K1, "b2").read_bytes()
    assert [c["part"] for c in w["calls"]["search"]] == [K2] and sref == [K1, K2]
    c = w["calls"]["search"][0]
    assert c["lag"] == 7 and c["dry"] == "rf2" and c["ref"] == "xlnoG" and c["dry_sha256"] == S.npy_sha(rf[K2])
    bad = [p for p in w["opened"] if SE.is_forbidden(p) or RR.is_forbidden(p)]
    assert not bad
    for k in (K1, K2):                                                # a start reference that does not repeat stops
        RR.search_path("fs-refit", k).unlink()
        RR.start_path("fs-refit", k).unlink()
    P.save(SN.record_path("start-ref", K1, "b2"), {"render_sha256": "other"})
    with pytest.raises(SystemExit, match="does not repeat"):
        RR.cmd_search(_args(row="fs-refit"))


def test_the_bridge_waits_for_the_bench(monkeypatch, tmp_path):
    w = _bench_world(monkeypatch, tmp_path)
    w["m"][RD.PHASE_BENCH_OUTCOME] = {"code": "XF-undecided"}
    for cmd in ("search", "answers", "score"):
        with pytest.raises(SystemExit, match="user's call"):
            RR.COMMANDS[cmd](_args(row="fs-refit"))
    with pytest.raises(SystemExit, match="user's call"):
        RR.cmd_floor_real(_args())
    w["m"][RD.PHASE_BENCH_OUTCOME] = {"code": "XF-closed"}           # the bridge runs; no rung or null row
    for cmd in ("search", "answers", "score"):
        with pytest.raises(SystemExit, match="does not ask for the rung rows"):
            RR.COMMANDS[cmd](_args(row="xf-levels"))
    with pytest.raises(SystemExit, match="does not ask for the null row"):
        RR.cmd_null_build(_args())
    w["m"][RD.PHASE_BENCH_OUTCOME] = {"code": "XF-part"}
    monkeypatch.setattr(RR, "NULL_CHANGE", None)
    with pytest.raises(SystemExit, match="not declared"):
        RR.cmd_null_build(_args())
    with pytest.raises(SystemExit, match="only after stage 1"):
        RR.cmd_search(_args(row="xf-fix"))


def test_the_null_row_builds_and_searches_on_xf_part(monkeypatch, tmp_path):
    np = pytest.importorskip("numpy")
    w = _bench_world(monkeypatch, tmp_path)
    w["m"][RD.PHASE_BENCH_OUTCOME] = {"code": "XF-part"}
    (tmp_path / "b2.json").write_text("{}")
    monkeypatch.setattr(NT, "build_path", lambda name=None: tmp_path / "b2.json")
    RR.cmd_null_build(_args())
    rec = json.loads(RR.null_build_path().read_text())
    assert rec["change"] == RR.NULL_CHANGE and set(rec["parts"]) == {K1, K2}
    for k in (K1, K2):
        y = np.load(RR.guitar_path("xf-null", k))
        assert S.npy_sha(y) == rec["parts"][k]["files"]["xf-null"]["audio_sha256"] != w["xs"][k]
        assert np.allclose(y, w["X"][k] * 10 ** (0.01 / 20), atol=1e-7)
    with pytest.raises(SystemExit, match="never overwritten"):
        RR.cmd_null_build(_args())
    RR.cmd_search(_args(row="xf-null"))
    assert [c["part"] for c in w["calls"]["search"]] == [K1, K2]
    assert all(c["dry"] == "xf-null" and c["lag"] == 0 for c in w["calls"]["search"])
    monkeypatch.setattr(RR, "NULL_CHANGE", {"kind": "gain_db", "value": 0.02})
    with pytest.raises(SystemExit, match="another change"):
        RR.cmd_search(_args(row="xf-null", rerun=True))
