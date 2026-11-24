"""The exact-notes test (`learn/scratch_exact.py`, `docs/scratch-search-plan.md` section 15): the target (the partner
rule, T1's dims and the categorical rule), the lag check, the numbers and the bug rule, F1's Fieller share and its
shapes, G1, XN_TABLE (every case ends in exactly one code, first match in order, the anomaly and overshoot codes, the
undefined share), `xn-list`'s split, the score check's six settings, the answers without borrowed answers or a centre,
every refusal, and that the search opens neither `targets.json` nor `answers-fs-stem.json`. Synthetic keys; pure:
runs on the light CI runner (no numpy). The last tests need numpy and the stored data (skipped elsewhere)."""
import ast
import itertools
import json
import math
import pathlib

import pytest

from learn import note_transcribe as T
from learn import scratch_exact as X
from learn import scratch_search as S

REPO = pathlib.Path(__file__).resolve().parents[1]


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


def _args(**kw):
    base = {"shard": (0, 1), "first": 0, "rerun": False, "row": "xn-bank"}
    base.update(kw)
    return type("A", (), base)()


# --- names and keys -----------------------------------------------------------------------------------------------------------

def test_names_and_keys():
    assert [X.answers_key(r) for r in X.ROWS] == ["phase_scratch_exact_answers_bank", "phase_scratch_exact_answers_swap",
                                                  "phase_scratch_exact_answers_reread", "phase_scratch_exact_answers_list"]
    with pytest.raises(SystemExit, match="unknown row"):
        X.answers_key("fs-stem")
    assert [X.stage_of(r) for r in X.ROWS] == [1, 1, 2, 2]
    assert X.PHASE == X.KEY_PREFIX and X.PHASE_TARGETS.startswith(X.KEY_PREFIX)
    assert X.DECIDING == ("bks", "goat") and X.SMALL == 0.05 and X.BIG == 0.10


def test_the_key_prefix_is_outside_every_guarded_prefix():
    pre = [p for ps in T.KEY_PREFIXES.values() for p in ps]
    assert not X.KEY_PREFIX.startswith(tuple(pre)) and not X.KEY_PREFIX.startswith("phase_fs")
    assert not S.fs_keys({X.PHASE: 1}) and not T.guarded_keys({X.PHASE: 1}, pre)
    X.xn_table_guard()


# --- the target ---------------------------------------------------------------------------------------------------------------

def _p(pk, partners, cen, **kw):
    return dict({"pkey": pk, "partners": partners, "cen": {"settings": cen, "select": 0}, "lag": -64, "search": "A",
                 "held": "B"}, **kw)


def test_the_target_partner_is_the_first_whose_cen_differs():
    cen_of = {"a": {"m/k": "1"}, "b": {"m/k": "1"}, "c": {"m/k": "2"}, "d": {"m/k": "3"}}
    assert X.target_partner(_p("a", ["b", "c", "d"], cen_of["a"]), cen_of) == "c"
    assert X.target_partner(_p("a", ["d", "c"], cen_of["a"]), cen_of) == "d"
    assert X.target_partner(_p("a", ["b"], cen_of["a"]), cen_of) is None


def test_the_left_mic_needs_every_branch_to_keep_the_left_cab_on():
    on = {X.LEFT_CAB: "true", X.RIGHT_CAB: "false"}
    assert X.left_mic_on_every_branch(["m/x"], on)
    assert not X.left_mic_on_every_branch(["m/x", X.RIGHT_CAB], on)         # step 1 may switch the right cab on
    assert not X.left_mic_on_every_branch(["m/x"], {X.LEFT_CAB: "true", X.RIGHT_CAB: "true"})   # stage A may cut left
    assert not X.left_mic_on_every_branch(["m/x"], {X.LEFT_CAB: "false", X.RIGHT_CAB: "false"})


def test_t1s_dims_are_step_1_the_eq_and_the_left_room_once_each():
    cen = {X.LEFT_CAB: "true", X.RIGHT_CAB: "true"}
    got = X.always_searched(["p/gain", "eq/b1", X.RIGHT_CAB], ["eq/b1", "eq/b2"], cen)
    assert got == ["p/gain", "eq/b1", X.RIGHT_CAB, "eq/b2", *X.ROOM_KEYS]
    assert X.LEFT_MIC in X.always_searched(["p/gain"], [], {X.LEFT_CAB: "true", X.RIGHT_CAB: "false"})


def test_project_target_takes_the_partners_answer_on_the_dims_only():
    cen = {"a/x": "1", "a/y": "2", "a/z": "3", X.LEFT_MIC: "2"}
    ans = {"a/x": "9", "a/y": "2", "a/z": "7", "b/w": "5", X.LEFT_MIC: "4"}
    t, rep = X.project_target(ans, cen, ["a/x", "a/y", "a/q", X.LEFT_MIC], {X.LEFT_MIC: ["2", "3"]})
    assert t == {"a/x": "9", "a/y": "2", "a/z": "3", X.LEFT_MIC: "2"}           # a/z, b/w not projected
    assert rep["changed"] == ["a/x"]
    assert rep["dropped"] == {"a/q": "not in the partner's answer", X.LEFT_MIC: "not in the part's own value list"}
    t2, _ = X.project_target(ans, cen, [X.LEFT_MIC], {X.LEFT_MIC: ["2", "4"]})
    assert t2[X.LEFT_MIC] == "4"
    assert cen == {"a/x": "1", "a/y": "2", "a/z": "3", X.LEFT_MIC: "2"}       # Cen untouched


def test_on_grid_one_per_partner_coverage_and_the_synthetic_part():
    kinds = {"a/x": "cont", "a/y": "log", "a/s": "switch"}
    assert X.on_grid(["a/x", "a/y", "a/s"], kinds, {"a/x": "1", "a/y": "5", "a/s": "true"},
                     {"a/x": "1", "a/y": "2", "a/s": "true"}) == ["a/x"]
    assert X.one_per_partner({"p3": "q1", "p1": "q1", "p2": "q2"}) == ["p1", "p2"]
    assert X.coverage(["a/x", "a/y"], ["a/x"]) == {"covered": True, "missing": []}
    assert X.coverage(["a/x"], ["a/x", "c/m"]) == {"covered": False, "missing": ["c/m"]}
    p = _p("a", [], {})
    q = X.synthetic_part(p)
    assert q["lag"] == 0 and p["lag"] == -64 and {k: v for k, v in q.items() if k != "lag"} == \
        {k: v for k, v in p.items() if k != "lag"}


def test_the_lag_check():
    zero, pos = {"A": 0.0, "B": 0.0}, {"A": 0.01, "B": 0.02}
    assert X.lag_check(zero, pos, pos)
    assert not X.lag_check({"A": 0.0, "B": 1e-12}, pos, pos)                  # exactly 0 at lag 0
    assert not X.lag_check(zero, {"A": 0.0, "B": 0.02}, pos)                  # above 0 at lag -1
    assert not X.lag_check(zero, pos, {"A": math.inf, "B": 0.02})


# --- the numbers ----------------------------------------------------------------------------------------------------------------

def test_the_numbers_have_no_borrowed_answer_or_centre():
    held = {"cen": 2.0, "answer": 1.0, "cp50": 2.0, "cp100": 1.5, "cp200": 1.0, "shrunk": 4.0}
    n = X.xn_numbers(held)
    assert set(n) == set(X.FIELDS)
    assert n["G"] == pytest.approx(math.log(0.5)) and n["G_cp50"] == 0.0 and n["G_shrunk"] == pytest.approx(math.log(2))
    assert X.xn_numbers({"cen": 1.0, "answer": 1.0})["G_cp50"] is None
    assert set(X.FIELDS) == set(S.G_FIELDS)                     # S1's Cen fallback covers every field


def test_the_bug_rule():
    ok = {"cen": 1.0, "answer": 0.5, "cp50": math.inf, "shrunk": None}
    assert X.deciding_bug(ok) == {}                              # non-finite off the deciding settings: nonfinite_rule
    assert X.deciding_bug({"cen": 1.0, "answer": 0.0}) == {"answer": "zero"}
    assert X.deciding_bug({"cen": 1.0, "answer": 0.5, "cp100": 0.0}) == {"cp100": "zero"}
    assert X.deciding_bug({"cen": math.inf, "answer": math.nan}) == {"cen": "non-finite", "answer": "non-finite"}


# --- F1: the Fieller share -------------------------------------------------------------------------------------------------------

def _lin(mx, my, vx, vy, cxy, t=1.645):
    """An interval function for mean(y - r x) with a fixed covariance: the textbook Fieller case."""
    def iv(r):
        m = my - r * mx
        h = t * math.sqrt(max(0.0, vy - 2 * r * cxy + r * r * vx))
        return _iv(m, m - h, m + h)
    return iv


def test_fieller_matches_the_textbook_bounded_case():
    mx, my, vx, vy, c = 0.20, 0.10, 0.0016, 0.0009, 0.0004
    iv = _lin(mx, my, vx, vy, c)
    got = X.fieller_share(iv, iv_den := _iv(mx, mx - 1.645 * 0.04, mx + 1.645 * 0.04))
    assert iv_den["lo90"] > 0
    t2 = 1.645 ** 2                                           # the quadratic's roots, for the check only
    a, b, cc = mx * mx - t2 * vx, -2 * (mx * my - t2 * c), my * my - t2 * vy
    disc = math.sqrt(b * b - 4 * a * cc)
    lo, hi = sorted(((-b - disc) / (2 * a), (-b + disc) / (2 * a)))
    assert got["defined"] and got["shape"] == "bounded" and len(got["segments"]) == 1
    assert got["segments"][0]["lo"] == pytest.approx(lo, abs=1e-5)
    assert got["segments"][0]["hi"] == pytest.approx(hi, abs=1e-5)
    assert got["estimate"] == pytest.approx(0.5)
    naive = (my - 1.645 * 0.03) / (mx + 1.645 * 0.04), (my + 1.645 * 0.03) / (mx - 1.645 * 0.04)
    assert abs(got["segments"][0]["lo"] - naive[0]) > 1e-3       # never built from the two marginal intervals


def test_fieller_is_undefined_when_the_denominator_reaches_zero():
    iv = _lin(0.05, 0.02, 0.01, 0.01, 0.0)
    assert not X.fieller_share(iv, _iv(0.05, -0.01, 0.11))["defined"]
    assert not X.fieller_share(iv, _iv(0.05, 0.0, 0.11))["defined"]
    assert not X.fieller_share(iv, None)["defined"]
    assert X.fieller_share(iv, _iv(-0.2, -0.3, -0.1))["defined"]         # wholly below zero is defined


def test_fieller_seeds_at_the_estimate_outside_the_grid():
    """Review nit 2: a defined share wholly outside the grid is found from the point estimate (the mean is 0 there),
    never read as empty."""
    mx, my, vx, vy = 0.10, 1.0, 0.0001, 0.0004
    got = X.fieller_share(_lin(mx, my, vx, vy, 0.0), _iv(mx, 0.08, 0.12))
    t2 = 1.645 ** 2
    a, b, cc = mx * mx - t2 * vx, -2 * mx * my, my * my - t2 * vy
    disc = math.sqrt(b * b - 4 * a * cc)
    lo, hi = sorted(((-b - disc) / (2 * a), (-b + disc) / (2 * a)))
    assert lo > 4                                                  # wholly outside the declared grid
    assert got["shape"] == "bounded" and got["seeded_at_estimate"] and got["estimate"] == pytest.approx(10.0)
    assert got["segments"][0]["lo"] == pytest.approx(lo, abs=1e-5) and got["segments"][0]["hi"] == \
        pytest.approx(hi, abs=1e-5)
    neg = X.fieller_share(_lin(-mx, my, vx, vy, 0.0), _iv(-mx, -0.12, -0.08))
    assert neg["shape"] == "bounded" and neg["estimate"] == pytest.approx(-10.0) and neg["segments"][0]["hi"] < -4
    inside = X.fieller_share(_lin(0.20, 0.10, 0.0016, 0.0009, 0.0004), _iv(0.2, 0.13, 0.27))
    assert not inside["seeded_at_estimate"] and len(inside["segments"]) == 1   # found by the grid: no second piece


def test_fieller_reports_rays_and_the_whole_line():
    whole = X.fieller_share(lambda r: _iv(0.0, -1e9, 1e9), _iv(1.0, 0.5, 1.5))
    assert whole["shape"] == "the whole line" and whole["segments"] == [{"lo": None, "hi": None}]
    rays = X.fieller_share(lambda r: _iv(0.0, -1.0, 1.0) if abs(r) > 2 else _iv(5.0, 4.0, 6.0), _iv(1.0, 0.5, 1.5))
    assert rays["shape"] == "two rays" and rays["segments"][0]["lo"] is None and rays["segments"][1]["hi"] is None
    assert rays["segments"][0]["hi"] == pytest.approx(-2.0, abs=1e-5) and rays["segments"][1]["lo"] == \
        pytest.approx(2.0, abs=1e-5)
    one = X.fieller_share(lambda r: _iv(0.0, -1.0, 1.0) if r > 1 else _iv(5.0, 4.0, 6.0), _iv(1.0, 0.5, 1.5))
    assert one["shape"] == "a ray" and one["segments"][0]["hi"] is None
    far = X.fieller_share(lambda r: _iv(0.0, -1.0, 1.0) if 1 < r < 37 else _iv(5.0, 4.0, 6.0), _iv(1.0, 0.5, 1.5))
    assert far["shape"] == "bounded" and far["segments"][0]["hi"] == pytest.approx(37.0, abs=1e-5)   # past the grid
    empty = X.fieller_share(lambda r: _iv(5.0, 4.0, 6.0), _iv(1.0, 0.5, 1.5))
    assert empty["shape"] == "empty on the grid"
    pieces = X.fieller_share(lambda r: _iv(0.0, -1.0, 1.0) if 0 < r < 1 or 2 < r < 3 else _iv(5.0, 4.0, 6.0),
                             _iv(1.0, 0.5, 1.5))
    assert pieces["shape"] == "several pieces" and len(pieces["segments"]) == 2


# --- G1, XN_TABLE, the list split -----------------------------------------------------------------------------------------------

PASS = _iv(-0.2, -0.3, -0.1)


def test_gate_g1():
    assert X.gate(PASS, _iv(0.1, 0.02, 0.2))["holds"]
    assert not X.gate(PASS, _iv(0.1, 0.0, 0.2))["holds"]                     # D_swap must lie wholly above zero
    assert not X.gate(PASS, _iv(0.1, -0.01, 0.2))["holds"]
    assert not X.gate(_iv(-0.08, -0.15, -0.01), _iv(0.1, 0.02, 0.2))["holds"]   # xn-bank short of -0.10: undecided
    assert not X.gate(None, _iv(0.1, 0.02, 0.2))["holds"]
    assert not X.gate(PASS, None)["holds"]


IVS = {"above": _iv(0.1, 0.02, 0.2), "below": _iv(-0.1, -0.2, -0.02), "spans": _iv(0.0, -0.05, 0.05),
       "touch_lo": _iv(0.05, 0.0, 0.1), "touch_hi": _iv(-0.05, -0.1, 0.0), "none": None}


def _reference(g, ds, dg):
    """XN_TABLE as mutually exclusive predicates, written apart from `xn_code`'s order."""
    def above(i):
        return i is not None and i["lo90"] > 0

    def below(i):
        return i is not None and i["hi90"] < 0

    def spans(i):
        return i is not None and i["lo90"] <= 0 <= i["hi90"]
    if not g:
        return "XN-insensitive"
    if below(ds):
        return "XN-anomaly"
    if below(dg):
        return "XN-overshoot"
    if above(ds) and above(dg):
        return "XN-both"
    if above(ds):
        return "XN-reading"
    if spans(ds) and above(dg):
        return "XN-rest"
    return "XN-undecided"


def test_every_case_ends_in_exactly_one_code_first_match_in_order():
    seen = set()
    for g, ds, dg in itertools.product((True, False), IVS, IVS):
        got = X.xn_code(g, IVS[ds], IVS[dg])
        assert got["code"] == _reference(g, IVS[ds], IVS[dg]), (g, ds, dg)
        assert got["code"] in X.XN_CODES and got["reading"] and got["next"]
        seen.add(got["code"])
    assert seen == set(X.XN_CODES)


def test_the_codes_words_and_order():
    assert X.xn_code(False, IVS["below"], IVS["below"])["code"] == "XN-insensitive"     # the gate first
    assert X.xn_code(True, IVS["below"], IVS["below"])["code"] == "XN-anomaly"          # before the overshoot
    assert X.xn_code(True, IVS["above"], IVS["below"])["code"] == "XN-overshoot"        # before XN-reading
    r = X.xn_code(True, IVS["above"], IVS["spans"])
    assert r["code"] == "XN-reading" and "hi90 = 0.05" in r["reading"] and "xn-list says which" in r["next"]
    rest = X.xn_code(True, IVS["spans"], IVS["above"])
    assert rest["code"] == "XN-rest" and "hi90 = 0.05" in rest["reading"] and "no route licensed" in rest["next"]
    assert "share is undefined" in X.xn_code(False, None, None)["reading"]
    assert X.xn_code(True, IVS["above"], IVS["above"])["code"] == "XN-both"
    for c in ("XN-anomaly", "XN-overshoot"):
        assert next(t for t in X.XN_TABLE if t[0] == c)[3] == "audited before anything is said"


def test_the_table_guard():
    X.xn_table_guard()
    old = X.XN_TABLE
    try:
        X.XN_CODES = tuple(reversed(X.XN_CODES))
        with pytest.raises(SystemExit, match="seven declared"):
            X.xn_table_guard()
    finally:
        X.XN_CODES = tuple(c for c, *_ in old)


def test_the_list_split():
    s = X.list_split(IVS["above"], IVS["spans"])
    assert s["reading_proper_shown"] and not s["re_derivation_shown"]
    s = X.list_split(IVS["touch_lo"], IVS["above"])
    assert not s["reading_proper_shown"] and s["re_derivation_shown"]


# --- the checks, the answers, the refusals ------------------------------------------------------------------------------------

def test_the_score_check_reads_the_six_shared_settings():
    names = ("cen",) + X.SCORED
    held = {n: 0.1 + i for i, n in enumerate(names)}
    sha = {n: f"s{n}" for n in names}
    stored = {"k": {"held": dict(held, centre=9.0, q1=8.0), "render_sha256": dict(sha, centre="c", q1="q")}}
    assert X.score_check_verdict({"k": {"held": held, "render_sha256": sha}}, stored)["passed"]
    bad = X.score_check_verdict({"k": {"held": dict(held, cp50=0.0), "render_sha256": sha}}, stored)
    assert not bad["passed"] and bad["mismatches"] == [("k", "cp50")]
    miss = X.score_check_verdict({"k": {"held": {"cen": 0.1}, "render_sha256": {"cen": "scen"}}}, stored)
    assert not miss["passed"] and ("k", "answer", "missing") in miss["mismatches"]
    assert not X.score_check_verdict({}, stored)["passed"]


def _rec(ans, cps=None, dims=None, refused=None):
    if refused:
        return {"refused": refused}
    return {"answer": {"select": 0, "settings": ans}, "searched_dims": dims or [],
            "step1": {"checkpoints": {str(c): {"settings": dict(ans, cp=str(c))} for c in (cps or (50, 100, 200))}}}


def test_the_answers_hold_no_borrowed_answer_and_no_centre():
    dims = [{"module": "a", "key": "x", "kind": "cont", "lo": 0.0, "hi": 1.0}]
    draw = {"parts": [_p("a", [], {"a/x": "0.2"}), _p("b", [], {"a/x": "0.2"})]}
    recs = {"a": _rec({"a/x": "0.6"}, dims=dims), "b": _rec(None, refused={"start": {"value": 1}})}
    parts, refused = X.xn_answer_parts(draw, recs, lambda k: f"sha-{k}")
    assert set(parts) == {"a"} and refused == {"b": {"search": {"start": {"value": 1}}}}
    a = parts["a"]
    assert "borrowed" not in a and "centre" not in a
    assert a["cp50"]["cp"] == "50" and a["search_sha256"] == "sha-a"
    assert float(a["shrunk"]["a/x"]) == pytest.approx(0.4)


def test_the_answers_refuse_a_record_of_another_dry_guitar():
    recs = {"a": {"dry_sha256": "x"}, "b": {"refused": {}}}
    assert X.dry_refusal(recs, {"a": "x"}) is None
    assert "not the declared one" in X.dry_refusal(recs, {"a": "y"})
    assert "not the declared one" in X.dry_refusal(recs, {})


def test_stage_2_waits_for_a_holding_g1():
    for r in X.STAGES[1]:
        assert X.search_refusal(r, None) is None
    for r in X.STAGES[2]:
        assert "after `gate`" in X.search_refusal(r, None)
        assert "does not hold" in X.search_refusal(r, {"gate": {"holds": False}})
        assert X.search_refusal(r, {"gate": {"holds": True}}) is None


def test_phase_as_checks_are_enforced():
    """Review nit 1: a lag-check failure or an unreproduced row (b) score stops floor-read and the search."""
    assert X.phase_a_refusal([], []) is None
    assert "lag check fails on 1 part" in X.phase_a_refusal(["k"], [])
    assert "does not reproduce its stored score on 2 part" in X.phase_a_refusal([], ["a", "b"])
    both = X.phase_a_refusal(["k"], ["a"])
    assert "lag check" in both and "reproduce" in both and "to the user" in both


def _records_file(tmp_path, monkeypatch, body):
    p = tmp_path / "records.json"
    p.write_text(json.dumps(body))
    monkeypatch.setattr(X, "records_path", lambda: p)
    return {X.PHASE_TARGETS: {"records_sha256": S.file_sha(p)}}


def test_the_search_refuses_records_with_a_failed_phase_a_check(monkeypatch, tmp_path):
    m = _records_file(tmp_path, monkeypatch, {"parts": {}, "lag_failed": ["k"], "row_b_not_reproduced": []})
    with pytest.raises(SystemExit, match="lag check fails"):
        X.require_records(m)
    m = _records_file(tmp_path, monkeypatch, {"parts": {}})                # written before the checks existed
    with pytest.raises(SystemExit, match="holds no lag check"):
        X.require_records(m)
    m = _records_file(tmp_path, monkeypatch, {"parts": {"k": {}}, "lag_failed": [], "row_b_not_reproduced": []})
    assert X.require_records(m)["parts"] == {"k": {}}


def test_floor_read_refuses_before_writing_on_a_failed_check(monkeypatch, tmp_path):
    """floor-read reads every part's files, then refuses on a lag failure with nothing written."""
    monkeypatch.setattr(X, "exact_dir", lambda: tmp_path)
    monkeypatch.setattr(X, "require_exact", lambda *a: {})
    monkeypatch.setattr(X, "require_checks", lambda m=None: {})
    monkeypatch.setattr(X, "require_xbuild", lambda m, hashed=True: {})
    draw = {"parts": [_p("k1", [], {}), _p("k2", [], {})]}
    monkeypatch.setattr(X, "context", lambda: (draw, None))
    (tmp_path / "build.json").write_text("{}")
    bsha = S.file_sha(tmp_path / "build.json")
    for k in ("k1", "k2"):
        X.record_path(k).parent.mkdir(parents=True, exist_ok=True)
        X.record_path(k).write_bytes(b"rec" + k.encode())
        t = {"record_file_sha256": S.file_sha(X.record_path(k)), "build_sha256": bsha, "lag_ok": k == "k1"}
        for kind, body in (("target", t), ("floors", {}), ("floors-real", {"reproduces_row_b": True})):
            path = X.target_path(k) if kind == "target" else X.floor_path(kind, k)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(body))
    with pytest.raises(SystemExit, match="lag check fails on 1 part"):
        X.cmd_floor_read(_args())
    assert not X.targets_path().exists() and not X.records_path().exists() and not X.floors_path().exists()


def test_the_keys_and_field_refusals():
    assert X.keys_refusal({"phase_scratch_exact": 1, "phase_fs": 2}, {"phase_scratch_exact": 1}) is None
    assert "phase_scratch_exact_targets" in X.keys_refusal({"phase_scratch_exact_targets": {}}, {})
    m = {X.PHASE_TARGETS: {"records_sha256": "abc"}}
    assert X.field_refusal(m, X.PHASE_TARGETS, "records_sha256", "abc") is None
    assert "is not main's" in X.field_refusal(m, X.PHASE_TARGETS, "records_sha256", "abd")
    assert "has no build_sha256" in X.field_refusal(m, X.PHASE_TARGETS, "build_sha256", "abc")
    assert "has no" in X.field_refusal({}, X.PHASE_TARGETS, "records_sha256", "abc")


# --- the search sees neither the targets nor row (b)'s answers -----------------------------------------------------------------

def test_the_search_open_refuses_the_targets_and_row_bs_answers():
    base = pathlib.Path("/x/fs/exact")
    for bad in (base / "targets.json", base.parent / "answers-fs-stem.json", base / "target" / "k.json",
                base / "floors" / "k.json", base / "floors-real" / "k.json", base / "score" / "xn-bank" / "k.json",
                base / "floors.json", base / "rows.json", base / "report.json"):
        assert X.is_forbidden(bad), bad
        with pytest.raises(SystemExit, match="never opens"):
            X.search_open(bad)
    for ok in (base / "records.json", base / "record" / "k.npy", base / "build.json", base / "dry" / "xn-list" / "k.npy",
               base / "gate.json"):                     # stage 2 reads G1 (N1): no settings in it
        assert not X.is_forbidden(ok) and X.search_open(ok) == ok


def _reached(src, root="cmd_search"):
    tree = ast.parse(src)
    defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    seen, todo = set(), [root]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        todo += [n.id for n in ast.walk(defs[name]) if isinstance(n, ast.Name) and n.id in defs]
    return seen, {k: ast.get_source_segment(src, defs[k]) for k in seen}


def test_the_search_never_opens_targets_json_or_answers_fs_stem_json():
    """Every function `cmd_search` reaches in this module, found by walking the code: none names the targets, a target
    file, a floor, a score or any answers file (row (b)'s `answers-fs-stem.json` among them); the records and the dry
    guitars go through `search_open`."""
    names, srcs = _reached((REPO / "learn" / "scratch_exact.py").read_text())
    assert {"cmd_search", "load_guitar", "load_record_blank", "load_record", "require_records", "require_xbuild",
            "start_reference", "search_open"} <= names
    for nm, src in srcs.items():
        for bad in ("targets_path", "target_path", "floor_path", "floors_path", "score_path", "answers_path",
                    "require_targets", "require_answers", "answers-fs-stem", "targets.json"):
            assert bad not in src or nm == "search_open", (nm, bad)
    for nm in ("load_record", "load_guitar", "require_records", "require_xbuild"):
        assert "search_open(" in srcs[nm]


# --- the commands refuse ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", sorted(X.COMMANDS))
def test_every_command_refuses_off_main(monkeypatch, cmd):
    monkeypatch.setattr(S, "on_main", lambda: (None, "this checkout's learn/scratch_search.py differs from main's"))
    with pytest.raises(SystemExit, match="differs from main's"):
        X.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", sorted(X.COMMANDS))
def test_every_command_refuses_without_the_declaration_or_build_2(monkeypatch, cmd):
    main = {S.PHASE: 1, S.PHASE_DRAW: {}, S.phase_answers("fs-stem"): {}, X.PHASE_BANK: {}}
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    with pytest.raises(SystemExit, match="phase_scratch_exact"):
        X.COMMANDS[cmd](_args())
    del main[X.PHASE_BANK]
    main[X.PHASE] = {}
    with pytest.raises(SystemExit, match="phase_scratch_notes_dry_b2"):
        X.COMMANDS[cmd](_args())


@pytest.mark.parametrize("cmd", ["search", "answers", "score", "gate", "read"])
def test_the_rows_wait_for_the_targets_hash(monkeypatch, cmd):
    main = {S.PHASE: 1, S.PHASE_DRAW: {}, S.phase_answers("fs-stem"): {}, X.PHASE_BANK: {}, X.PHASE: {}}
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    with pytest.raises(SystemExit, match="phase_scratch_exact_targets"):
        X.COMMANDS[cmd](_args())


def test_score_waits_for_its_rows_answers_key(monkeypatch):
    main = {S.PHASE: 1, S.PHASE_DRAW: {}, S.phase_answers("fs-stem"): {}, X.PHASE_BANK: {}, X.PHASE: {},
            X.PHASE_TARGETS: {}}
    monkeypatch.setattr(S, "on_main", lambda: (main, None))
    with pytest.raises(SystemExit, match="phase_scratch_exact_answers_swap"):
        X.cmd_score(_args(row="xn-swap"))


def test_the_cli_needs_a_row_and_at_most_three_shards():
    with pytest.raises(SystemExit):
        X.main(["search"])
    with pytest.raises(SystemExit):
        X.main(["score", "--row", "xn-bank", "--shard", "0/4"])
    with pytest.raises(SystemExit):
        X.main(["search", "--row", "fs-stem"])


# --- on the stored data (numpy; skipped elsewhere) ------------------------------------------------------------------------

def _stored():
    from learn import pipeline_fix as P

    d = P.out_dir() / "fs"
    if not (d / "draw.json").exists() or not (d / "answers-fs-stem.json").exists():
        pytest.skip("the stored draw and row (b)'s answers are not here")
    return d


def test_t1_on_the_stored_draw():
    """At declaration (zero renders): 47 targets from 33 partners; T1's dims are step 1's searched keys (row (b)'s and
    row (c)'s records) plus the left room; the left mic type projects on no part (step 1 searches the right cab's
    switch on every amp); every target differs from Cen only on keys both rows (b) and (c) searched."""
    pytest.importorskip("numpy")
    d = _stored()
    from learn import full_controls_c1b as C

    draw = json.loads((d / "draw.json").read_text())
    ab = json.loads((d / "answers-fs-stem.json").read_text())
    lists = C.mic_lists()
    cen_of = {q["pkey"]: q["cen"]["settings"] for q in draw["parts"]}
    partner, left = {}, 0
    for p in draw["parts"]:
        q = X.target_partner(p, cen_of)
        partner[p["pkey"]] = q
        names, kinds, cats, s1 = X.target_dims(p, lists)
        left += X.LEFT_MIC in names
        for row in ("fs-stem", "fs-both"):
            r = json.loads((d / "search" / row / f"{p['pkey']}.json").read_text())
            assert s1 == r["step1"]["searched_keys"]
            _, rep = X.project_target(ab["parts"][q]["answer"], p["cen"]["settings"], names, cats)
            assert X.coverage([s["module"] + "/" + s["key"] for s in r["searched_dims"]], rep["changed"])["covered"]
    assert len(partner) == 47 and len(set(partner.values())) == 33 and left == 0
    assert sum(1 for k, q in partner.items() if partner.get(q) == k) == 18
