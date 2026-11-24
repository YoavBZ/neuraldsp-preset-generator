"""S1 (`phase_scratch_refusal_reports`): refusals are reports, never a row stop. The pure helpers in
`learn/scratch_search.py` (the Clopper-Pearson share, `refusal_report`, the intent-to-treat read at Cen, the
passing-only read, `refusal_label`, `refused_audit`, the rerun-once records), the no-stop rule in every row that
imported REFUSAL_STOP, and the stored readings of rows (b) and (c) and both codec rows unchanged (each refused 0).
Pure: the light CI runner (no numpy); the stored-data tests skip where the data is absent."""
import ast
import hashlib
import json
import pathlib

import pytest

from learn import note_transcribe as NT
from learn import scratch_codec as SC
from learn import scratch_loudar as SL
from learn import scratch_notes as SN
from learn import scratch_search as S
from learn import scratch_tone as T

REPO = pathlib.Path(__file__).resolve().parents[1]
DECISION_SHA256 = "2e598bca0ee1ea06435d2d0ebe74da3ff03a2c10c1fdb488f33533e08e45ddb2"   # bar-conversion.md


def _iv(values):
    """A plain normal 90% interval of a list (for the synthetic row only)."""
    n = len(values)
    m = sum(values) / n
    sd = (sum((v - m) ** 2 for v in values) / (n - 1)) ** 0.5
    return {"mean": m, "lo90": m - 1.645 * sd / n ** 0.5, "hi90": m + 1.645 * sd / n ** 0.5}


def test_no_module_keeps_a_refusal_stop():
    for mod in (S, SC, SN, T, SL, NT):
        assert not hasattr(mod, "REFUSAL_STOP"), mod.__name__
    assert not S.stopped({k: {"search": "x"} for k in "abcdefghij"})
    assert SN.deciding_stop({"a": 1, "b": 1, "c": 1, "d": 1}, {k: "bks" for k in "abcd"})[2] is False
    assert SL.deciding_stop({"a": 1, "b": 1, "c": 1}, {k: "bks" for k in "abc"})[2] is False
    assert SN.build_refusal({"stopped": True, "ear_failing": []}) is None
    three = {f"b{i}": {"failed": ["ring-kept"]} for i in range(4)}
    assert NT.refusal_count(three, {k: "bks" for k in three})[2] is False          # cmd_build builds on
    src = (REPO / "learn" / "scratch_notes.py").read_text()
    assert '"refused": {"content"' not in src and 'rec["content_label"]' in src     # a content check is a label
    assert src.count('content_labels') == 3                              # into answers.json and report.json
    assert "D_refused_as_cen" not in src and "and k not in refused})" in src
    assert "spath = S.rerun_path(spath)" in src                            # the rerun's own start reference
    for mod in ("scratch_search", "scratch_notes"):                        # the audit gets Cen's start value
        text = (REPO / "learn" / f"{mod}.py").read_text()
        call = text[text.index('refused_audit(draw["parts"]'):][:260]
        assert "start=" in call, mod


def test_the_clopper_pearson_interval():
    assert S.clopper_pearson(0, 10) == (0.0, pytest.approx(0.2588655508930522))           # scipy's beta.ppf
    assert S.clopper_pearson(3, 23) == (pytest.approx(0.03651529972590258), pytest.approx(0.30363770155746167))
    assert S.clopper_pearson(4, 47) == (pytest.approx(0.029593795086135966), pytest.approx(0.18426498527352642))
    assert S.clopper_pearson(10, 10) == (pytest.approx(0.7411344491069477), 1.0)
    assert S.clopper_pearson(0, 0) == (None, None)


def test_the_refusal_report():
    sets_of = {"b1": "bks", "b2": "bks", "g1": "goat", "g2": "goat", "p1": "panel"}
    r = S.refusal_report({"b1": {"search": {"start": 1}}, "p1": {"search": {"content": ["ring-kept"]}}}, sets_of,
                         ["bks", "goat"])
    assert r["stops"] is False and r["deciding"] == ["bks", "goat"]
    assert r["per_set"]["bks"]["refused"] == 1 and r["per_set"]["bks"]["share"] == 0.5
    assert r["pooled"]["refused"] == 1 and r["pooled"]["parts"] == 4 and r["pooled"]["keys"] == ["b1"]
    assert r["pooled"]["lo90"] == pytest.approx(S.clopper_pearson(1, 4)[0])
    assert r["kinds"] == {"b1": {"kind": "technical", "reasons": ["start"]},          # unwrapped from "search"
                          "p1": {"kind": "content", "reasons": ["content"]}}
    assert S.refusal_kind({"scoring_control": 1}) == "technical" and S.refusal_kind("x") == "technical"
    assert S.refusal_reasons({"borrowed": "few"}) == {"borrowed": "few"} and S.refusal_reasons("x") == {"search": "x"}


def test_a_synthetic_row_with_four_refusals_reads_on_at_cen():
    keys = [f"k{i:02d}" for i in range(47)]
    per = {k: {"G": -0.30 + 0.01 * (i % 7), "G_shrunk": -0.2, "I": -0.25, "blind": 0.1} for i, k in enumerate(keys)}
    refused = {k: {"search": "start-check miss"} for k in keys[:4]}
    for k in refused:
        per[k] = None
    assert not S.stopped(refused)
    itt = S.itt_per(per, refused)
    assert all(itt[k] == dict({f: 0.0 for f in S.G_FIELDS}, cen_fallback=True) for k in refused)
    assert itt[keys[5]] is per[keys[5]] and "I" not in itt[keys[0]]       # I needs the partners: not at Cen
    assert "G_centre" not in itt[keys[0]] and "G_centre" not in S.G_FIELDS  # the row's centre is no part's fallback
    g_itt = [v["G"] for v in itt.values()]
    g_pass = [v["G"] for k, v in S.passing_only(per, refused).items() if v is not None]
    assert len(g_itt) == 47 and len(g_pass) == 43
    a, b = S.number_reading(_iv(g_itt)), S.number_reading(_iv(g_pass))
    assert a == b == "passes" and S.refusal_label(a, b) is None
    tight = {k: {"G": -0.10} for k in keys}
    for k in keys[:12]:
        tight[k] = None
    tref = {k: {"search": "x"} for k in keys[:12]}
    ti = [v["G"] for v in S.itt_per(tight, tref).values()]
    tp = [v["G"] for v in tight.values() if v is not None]
    tp[0] -= 0.01                                                          # some spread
    ti[20] -= 0.01
    c1, c2 = S.number_reading(_iv(ti)), S.number_reading(_iv(tp))
    assert c1 != c2 and S.refusal_label(c1, c2) == "refusal-sensitive"
    assert S.itt_values({"a": 0.2, "b": None, "c": None}, {"b": 1}) == {"a": 0.2, "b": 0.0, "c": None}
    none = S.passing_code(lambda: {"code": "x"}, False)
    assert none == {"code": None, "reading": "no passing-only interval"} and S.passing_code(lambda: {"code": "x"},
                                                                                            True) == {"code": "x"}
    assert S.refusal_label("passes", None) is None                         # nothing to compare: said, not labelled
    assert S.itt_per({"a": {"G": 1.0}}, {}) == {"a": {"G": 1.0}}


def test_the_refused_audit():
    parts = [{"pkey": f"p{i}", "set": "bks" if i < 3 else "goat", "amp": "ac20", "cls": "clean", "unit": f"u{i}"}
             for i in range(6)]
    a = S.refused_audit(parts, {"p0": 1, "p1": 1}, band={"u0": "low", "u1": "low", "u2": "high"},
                        start={f"p{i}": float(i) for i in range(6)}, values={f"p{i}": (0.0 if i < 2 else -0.2)
                                                                            for i in range(6)})
    assert a["refused"] == ["p0", "p1"]
    assert a["before_held"]["set"] == {"refused": {"bks": 2}, "rest": {"bks": 1, "goat": 3}}
    assert a["before_held"]["band"]["refused"] == {"low": 2}
    assert a["before_held"]["cen_start"]["diff"] == pytest.approx(0.5 - 3.5)
    assert a["after_scoring"]["diff"] == pytest.approx(0.2) and a["after_scoring"]["n"] == [2, 4]
    assert S.mean_diff([1.0], [1.0, 2.0])["diff"] is None


def test_a_technical_refusal_is_rerun_once_then_cen(tmp_path):
    d = tmp_path / "search"
    d.mkdir()
    for k, rec in {"ok": {"answer": 1}, "tech": {"refused": {"start": 1}}, "again": {"refused": {"start": 1}},
                   "later": {"refused": {"start": 1}}, "label": {"refused": {"content": ["ring-kept"]}}}.items():
        (d / f"{k}.json").write_text(json.dumps(rec))
    rr = tmp_path / "search-rerun"
    rr.mkdir()
    (rr / "tech.json").write_text(json.dumps({"answer": 2}))
    (rr / "again.json").write_text(json.dumps({"refused": {"start": 2}}))
    assert S.rerun_path(d / "tech.json") == rr / "tech.json"
    recs, used, status = S.with_reruns(["ok", "tech", "again", "later", "label"], lambda k: d / f"{k}.json")
    assert recs["tech"] == {"answer": 2} and used["tech"] == rr / "tech.json"
    assert status == {"tech": "rerun passed", "again": "rerun refused", "later": "rerun pending"}
    assert "rerun" in S.rerun_refusal(status) and "later" in S.rerun_refusal(status)
    assert S.rerun_refusal({"tech": "rerun passed", "again": "rerun refused"}) is None
    assert not S.refused_record({"scoring_control_ok": True}, "score") and S.refused_record({}, "search") is False


def test_the_scoring_control_miss_waits_for_its_rerun():
    for mod, fn in ((S, "read_row_parts"), (SC, "codec_g50")):
        body = ast.get_source_segment((REPO / "learn" / f"{mod.__name__.split('.')[-1]}.py").read_text(),
                                      next(n for n in ast.parse((REPO / "learn" / f"{mod.__name__.split('.')[-1]}"
                                                                 ".py").read_text()).body
                                           if isinstance(n, ast.FunctionDef) and n.name == fn))
        assert "rerun_path(sp)" in body and "not yet rerun once in a fresh process" in body


def test_the_shared_search_and_score_path_is_unchanged():
    """`scratch_codec.SCRATCH_SEARCH_BLOB` is re-pinned by this amendment: every function of scratch_search.py that
    fs-notes' two checks ran through (search_row_part, score_row_part and the other 58) has the source it had at
    blob 2420043a; only the refusal path and the new helpers changed."""
    changed = {"outcome", "stopped", "cmd_answers", "cmd_score", "read_row_parts", "report_body", "cmd_read",
               "_binom_cdf", "clopper_pearson", "itt_per", "itt_values", "mean_diff", "passing_only", "refusal_kind",
               "refusal_label", "refusal_report", "refused_audit", "refused_record", "rerun_path", "rerun_refusal",
               "with_reruns", "refusal_reasons", "passing_code"}
    text = (REPO / "learn" / "scratch_search.py").read_text()
    lines = text.splitlines()
    parts = sorted((n.name, "\n".join(lines[n.lineno - 1:n.end_lineno])) for n in ast.parse(text).body
                   if isinstance(n, ast.FunctionDef) and n.name not in changed)
    h = hashlib.sha256()
    for name, src in parts:
        h.update(name.encode() + b"\0" + src.encode() + b"\0")
    assert len(parts) == 60 and {"search_row_part", "score_row_part"} <= {n for n, _ in parts}
    assert h.hexdigest() == "7a6b360417e79491d2ae86a6515ec4ad592cfb31d5c5d0400514b426a1618e91"


def test_the_pin_is_this_checkouts_blob():
    data = (REPO / "learn" / "scratch_search.py").read_bytes()
    assert hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() == SC.SCRATCH_SEARCH_BLOB


def test_the_ledger_key():
    d = json.loads((REPO / "docs/dev-test-ledger.json").read_text())
    e = next(t for t in d["tests"] if t.get("test_id") == S.LEDGER_ID)["phase_scratch_refusal_reports"]
    assert e["decision_record"]["sha256"] == DECISION_SHA256 and "not the user's" in e["decided_by"]
    assert e["scratch_search_blob"]["from"] == "2420043a4483a482925bed5b87e54692619a305d"
    assert e["scratch_search_blob"]["to"] == SC.SCRATCH_SEARCH_BLOB


# --- the stored readings, unchanged (each of these rows refused 0 parts); skipped where the data is absent ----------

def _fs():
    try:
        d = S.fs_dir()
    except Exception:                                                    # noqa: BLE001 (no data root on CI)
        return None
    return d if (d / "report-fs-stem.json").exists() else None


@pytest.mark.parametrize("row", ["fs-stem", "fs-both"])
def test_rows_b_and_c_read_as_stored(row):
    d = _fs()
    if d is None:
        pytest.skip("no stored rows here")
    rep = json.loads((d / f"report-{row}.json").read_text())
    assert rep["refused"] == {} and rep["stopped"] is False
    assert S.itt_per(rep["parts"], rep["refused"]) == rep["parts"] == S.passing_only(rep["parts"], rep["refused"])
    rows = rep["rows"]
    assert S.row_reading(rows["G"]["deciding_pool"], rows["I"]["deciding_pool"]) == rows["reading"]
    assert S.refusal_label(rows["reading"]["reading"], rows["reading"]["reading"]) is None


@pytest.mark.parametrize("name", ["rt-m2l", "rt-dac"])
def test_both_codec_rows_read_as_stored(name):
    d = _fs()
    if d is None or not (d / "codec" / f"report-{name}.json").exists():
        pytest.skip("no stored codec rows here")
    rep = json.loads((d / "codec" / f"report-{name}.json").read_text())
    assert rep["refused"] == {} and rep["stopped"] is False
    assert S.itt_values(rep["parts"], rep["refused"]) == rep["parts"]
    rows = rep["rows"]
    assert SC.fk_code(rows["D_true"]["deciding_pool"], rows["D_blur"]["deciding_pool"])["code"] == rep["fk"]["code"]
    assert rep["fk"]["code"] == "FK-clear"


@pytest.mark.parametrize("row", ["fs-stem", "fs-both"])
def test_rows_b_and_c_resummarise_unchanged(row):
    pytest.importorskip("numpy")
    d = _fs()
    if d is None:
        pytest.skip("no stored rows here")
    from learn import note_replay as NR

    try:
        sd = NR.Stored()
    except (SystemExit, FileNotFoundError):
        pytest.skip("no stored C3r state here")
    rep = json.loads((d / f"report-{row}.json").read_text())
    draw = json.loads(S.draw_path().read_text())                      # not require_draw: no main guard
    got = S.summarise_row(sd, draw, S.itt_per(rep["parts"], rep["refused"]))
    for q in ("G", "I"):
        assert got[q]["deciding_pool"] == pytest.approx(rep["rows"][q]["deciding_pool"])
