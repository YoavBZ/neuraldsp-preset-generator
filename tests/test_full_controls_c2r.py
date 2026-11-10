"""C2r (docs/full-controls-plan.md, "C2r and C3r in detail"): learn/full_controls_c2r.py."""
import argparse
import json
import math
import re

import pytest

pytest.importorskip("numpy")

from learn import full_controls as F  # noqa: E402
from learn import full_controls_c2 as X  # noqa: E402
from learn import full_controls_c2r as R  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import pipeline_fix as P  # noqa: E402
from tests import test_full_controls_c2 as T2  # noqa: E402


# --- records, order, costs -------------------------------------------------------------------------------------------

def _cap_unit(u, di="goat/item_1", creator="cr", fold=0):
    return {"unit": u, "di": di, "creator": creator, "fold": fold, "cls": "clean"}


def test_cap1_records_take_the_stored_label_and_cluster_by_di_with_the_creator_beside():
    labelled = [{"unit": "cap/a#pr12", "amp": "pr12", "cls": "clean"}]
    units = {"cap/a#pr12": _cap_unit("cap/a#pr12", creator="x", fold=2)}
    (r,) = R.cap1_records(labelled, units, {"cap/a#pr12"}, lambda k: f"/s/{k}")
    assert (r["set"], r["block"], r["key"], r["cluster"], r["creator"], r["fold_stored"], r["real_out"]) == (
        "cap1", "cap1", "cap/a#pr12|pr12", "goat/item_1", "x", 2, True)
    assert r["source"] == "/s/cap/a#pr12|pr12"
    left = R.cap1_left_out([{"unit": "cap/a#pr12", "amp": "pr12", "label": {}},
                            {"unit": "cap/b#ac20", "amp": "ac20", "label": None, "why": "the one-window lag rule"}],
                           {r["key"]})
    assert left == [{"key": "cap/b#ac20|ac20", "block": "cap1", "why": "the one-window lag rule"}]


def test_n12_block_is_c2s_c1a_block_with_the_di_cluster_and_its_c1b_record():
    c1a = [{"set": "n12", "key": "cap/a#sw50r|sw50r", "unit": "cap/a#sw50r", "amp": "sw50r", "cls": "clean",
            "cluster": "player", "source": "/s", "prt": {}, "real_out": False, "budget": 100},
           {"set": "n12", "key": "cap/b#ac20|ac20", "unit": "cap/b#ac20", "amp": "ac20", "cls": "clean",
            "cluster": "player", "source": "/s", "prt": {}, "real_out": False, "budget": 300}]
    outs = {"cap/a#sw50r|sw50r": {"_path": "/o/a", "label": {}}, "cap/b#ac20|ac20": {"_path": "/o/b", "label": None}}
    units = {"cap/a#sw50r": _cap_unit("cap/a#sw50r", di="lib/d1", creator="y", fold=3)}
    recs, left = R.n12_block(c1a, outs, units, lambda k: f"/c1b/{k}")
    (r,) = recs
    assert (r["block"], r["set"], r["cluster"], r["creator"], r["fold_stored"], r["c1a_output"], r["c1a_budget"]) == (
        "n12", "n12", "lib/d1", "y", 3, "/o/a", 100)
    assert r["c1b_record"] == "/c1b/cap/a#sw50r|sw50r"
    assert left == [{"key": "cap/b#ac20|ac20", "block": "n12", "why": "C1a label fell back"}]


def test_high_bleed_leaves_unmeasured_units_in():
    assert R.high_bleed({"bleed_db": -18.0}, -18.35) and not R.high_bleed({"bleed_db": -20.0}, -18.35)
    assert not R.high_bleed({"bleed_db": None}, -18.35) and not R.high_bleed({}, -18.35)


def test_panel_amps_keep_the_ceiling_amp_and_balance_each_class_by_seed():
    amps = ["pr12", "sw50r", "ac20"]
    units = [{"unit": f"u{i}", "cls": "clean"} for i in range(7)] + [{"unit": f"v{i}", "cls": "crunch"} for i in range(4)]
    got = R.panel_amps(units, {"u0": "ac20", "u1": "ac20"}, amps)
    assert got["u0"] == got["u1"] == "ac20"
    clean = [got[f"u{i}"] for i in range(7)]
    assert sorted(clean.count(a) for a in amps) == [2, 2, 3]
    crunch = [got[f"v{i}"] for i in range(4)]
    assert sorted(crunch.count(a) for a in amps) == [1, 1, 2]
    assert R.panel_amps(units, {"u0": "ac20", "u1": "ac20"}, amps) == got                  # seeded
    assert R.panel_amps(units, {}, amps, seed=1) != R.panel_amps(units, {}, amps, seed=2)  # the order is the seed's


def test_panel_records_leave_every_unit_on_a_high_bleed_track_out_and_take_step_0s_source(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    units = [{"unit": "panel/B a/x@1#t1.wav", "di": "panel/B a/x", "band": "B a", "cls": "clean", "fold": 1,
              "bleed_db": -30.0, "amp_file": "t1"},
             {"unit": "panel/B a/x@1#t2.wav", "di": "panel/B a/x", "band": "B a", "cls": "clean", "fold": 1,
              "bleed_db": -10.0, "amp_file": "t2"},
             {"unit": "panel/B a/x@9#t2.wav", "di": "panel/B a/x", "band": "B a", "cls": "clean", "fold": 2,
              "bleed_db": None, "amp_file": "t2"},                                # unmeasured, but on t2's track
             {"unit": "panel/C/y@2#t.wav", "di": "panel/C/y", "band": "C", "cls": "crunch", "fold": 2,
              "bleed_db": None, "amp_file": "t3"}]
    recs, left = R.panel_records(units, {u["unit"]: "A" for u in units}, {"panel/C/y@2#t.wav": "sw50r"},
                                 ["pr12", "sw50r", "ac20"], set(), -18.35)
    assert [r["unit"] for r in recs] == ["panel/B a/x@1#t1.wav", "panel/C/y@2#t.wav"]
    assert [x["key"] for x in left] == ["panel/B a/x@1#t2.wav", "panel/B a/x@9#t2.wav"]
    assert "unmeasured" in left[1]["why"] and "unmeasured" not in left[0]["why"]
    c = recs[1]
    assert (c["amp"], c["ceiling_amp"], c["band"], c["cluster"], c["search"]) == ("sw50r", "sw50r", "C", "panel/C/y", "A")
    assert c["source"] == str(tmp_path / "panel" / "search-c2r" / "step0" / "panel__C__y@2#t.wav|sw50r.json")
    assert " " not in R.out_path(recs[0]).name                                          # the panel's own file names


def test_bleed_tracks_judge_a_track_by_its_worst_measured_window_and_a_wider_unit_list():
    units = [{"amp_file": "a", "bleed_db": -20.0}, {"amp_file": "a", "bleed_db": -18.0}, {"amp_file": "b",
                                                                                         "bleed_db": None}]
    assert R.bleed_tracks(units, -18.35) == {"a": -18.0}
    keep = [{"unit": "u", "amp_file": "b", "cls": "clean", "di": "d", "band": "x", "fold": 0, "bleed_db": None}]
    every = keep + [{"unit": "v", "amp_file": "b", "bleed_db": -5.0}]                   # a window outside the read set
    recs, left = R.panel_records(keep, {"u": "A"}, {}, ["pr12"], set(), -18.35, every=every)
    assert recs == [] and left[0]["key"] == "u"


def test_the_order_is_cap1_then_n12_then_the_panel_in_every_shard():
    recs = [{"block": b, "key": f"{b}{i}"} for b in ("panel", "n12", "cap1") for i in range(3)]
    for k in range(3):
        assert [r["block"] for r in R.shard_records(recs, k, 3)] == ["cap1", "n12", "panel"]


def test_renders_upper_is_c2s_per_record_cost_plus_step_0_on_the_panel():
    recs = [{"block": "cap1"}, {"block": "n12", "c1a_budget": 100}, {"block": "n12", "c1a_budget": 300},
            {"block": "panel"}]
    assert R.renders_upper(recs[:1]) == 268
    assert R.renders_upper(recs[1:2]) == 169 and R.renders_upper(recs[2:3]) == 67
    assert R.renders_upper(recs[3:]) == 268 + 53 == 321
    assert R.renders_upper(recs) == 268 + 169 + 67 + 321


def test_known_keys_are_c2s_on_the_captures_and_none_on_the_panel():
    keys, why = R.known({"set": "cap1", "amp": "pr12"})
    assert keys == X.known_keys("pr12") and "NAM captures" in why
    keys, why = R.known({"set": "panel", "amp": "pr12"})
    assert keys == {} and "real recordings" in why


def test_ceiling_check_compares_settings_and_judges_exactly():
    s0 = {"search": "A", "lag": 5, "evaluations": 52, "best": {"settings": {"a": "1"}, "judge": {"A": 1.0, "B": 2.0}}}
    c = {"search": "A", "lag": 5, "evaluations": 52, "best": {"settings": {"a": "1"}, "judge": {"A": 1.0, "B": 2.0}}}
    assert R.ceiling_check(s0, c) == {"same_half_and_lag": True, "same_settings": True, "same_judge": True,
                                      "evaluations": [52, 52]}
    c2 = dict(c, best={"settings": {"a": "2"}, "judge": {"A": 1.0, "B": 2.0}})
    assert R.ceiling_check(s0, c2)["same_settings"] is False and R.ceiling_check(s0, None) is None


def test_the_search_is_a_render_command_and_the_rest_are_not():
    assert any(re.search(p, "python -u -m learn.full_controls_c2r c2r-search --shard 0/3") for p in LO.RENDERS)
    for cmd in ("c2r-draw", "c2r-report", "c2r-ceiling-check"):
        assert not any(re.search(p, f"python -m learn.full_controls_c2r {cmd}") for p in LO.RENDERS)


# --- the search on a stub renderer: C2's loop with C2r's shard ------------------------------------------------------------

def _c2r_plan(tmp_path, rows):
    (tmp_path / "c2r").mkdir(exist_ok=True)
    (tmp_path / "c2r" / "records.json").write_text(json.dumps({"records": rows, "left_out": []}))


def test_c2r_runs_a_capture_record_through_c2s_recipe(tmp_path, monkeypatch, capsys):
    (row,), calls = T2._stub(tmp_path, monkeypatch)
    cap = dict(row, set="cap1", block="cap1", creator="cr", fold_stored=1)
    _c2r_plan(tmp_path, [cap])
    R.cmd_search(argparse.Namespace(shard=(0, 1)))
    out = R.out_path(cap)
    assert out.parent == tmp_path / "captures" / "search-c2r"
    r = json.loads(out.read_text())
    assert r["ledger"].endswith(R.PHASE) and r["label"] is not None and r["creator"] == "cr"
    assert r["known_keys"] == X.known_keys("pr12") and "NAM captures" in r["known_why"]
    assert r["step1"]["evaluations"] > 1 and r["step2"]["start_kind"] == "canonical"
    assert re.search(r"C2R-SEARCH DONE 0/1: (\d+) renders", capsys.readouterr().out)


def _panel_stub(tmp_path, monkeypatch, sha_ok=True, silent=False, ceiling=None):
    """A panel record on the C2 stub: its 5D lag record (S's sha and judges), and step 0 through the stub renderer."""
    np = pytest.importorskip("numpy")
    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM

    (row,), calls = T2._stub(tmp_path, monkeypatch)
    S = T2.full_start("pr12")
    unit = "panel/B a/x@1#t.wav"
    prt = {"unit": unit, "di": "panel/B a/x", "band": "B a", "cls": "clean", "fold": 0, "lag": 0, "rig": "r",
           "di_path": "", "start_s": 0.0, "sd": "", "track": ""}
    rec = {"set": "panel", "block": "panel", "key": f"{unit}|pr12", "unit": unit, "amp": "pr12", "cls": "clean",
           "cluster": prt["di"], "band": "B a", "fold_stored": 0, "search": "A", "ceiling_amp": ceiling,
           "prt": prt, "real_out": False}
    rec["source"] = str(R.step0_path(rec))
    v0 = T2._value(S)
    s_sha = AM.audio_sha(np.full(4, v0)) if sha_ok else "other"
    lags = tmp_path / "panel" / "lags"
    lags.mkdir(parents=True, exist_ok=True)
    (lags / f"{P.panel_fname(unit)}.json").write_text(json.dumps(
        {"unit": unit, "lag": 0, "status": "ok", "phase": "phase_5d",
         "s": {"pr12": {"judge": {"A": v0 * (1.0 if sha_ok else 1.5), "B": v0 + 0.5}, "render_sha256": s_sha}}}))
    if silent:
        monkeypatch.setattr(A, "peak_dbfs", lambda y, trim_s=0.0: -80.0)
    _c2r_plan(tmp_path, [rec])
    return rec, calls


def test_c2r_runs_the_panels_step_0_then_c2s_recipe_from_its_best(tmp_path, monkeypatch, capsys):
    rec, calls = _panel_stub(tmp_path, monkeypatch)
    R.cmd_search(argparse.Namespace(shard=(0, 1)))
    s0 = json.loads(R.step0_path(rec).read_text())
    assert s0["evaluations"] <= R.STEP0_EVALS and s0["s_first"]["verdict"] == "ok" and s0["label"] is not None
    assert s0["select"] == 0 and s0["search"] == "A" and s0["held"] == "B" and s0["ledger"].endswith(R.PHASE)
    r = json.loads(R.out_path(rec).read_text())
    assert r["known_keys"] == {} and r["step0"] == rec["source"] and r["band"] == "B a"
    assert r["source_best_judge"] == s0["best"]["judge"]                       # step 1 starts from step 0's best
    assert r["step1"]["start"]["value"] == pytest.approx(s0["best"]["judge"]["A"])
    total = int(re.search(r"C2R-SEARCH DONE 0/1: (\d+) renders", capsys.readouterr().out).group(1))
    want = (1 + s0["evaluations"]) + (1 + r["step1"]["evaluations"]) + (1 + len(r["step2"]["trace"])) + 2
    assert total == want == calls["n"]
    R.cmd_search(argparse.Namespace(shard=(0, 1)))                              # resume: skipped, no step 0 again
    assert calls["n"] == want


def test_c2r_refuses_a_panel_record_whose_step_0_misses_s(tmp_path, monkeypatch, capsys):
    rec, calls = _panel_stub(tmp_path, monkeypatch, sha_ok=False)
    R.cmd_search(argparse.Namespace(shard=(0, 1)))
    s0 = json.loads(R.step0_path(rec).read_text())
    assert s0["label"] is None and s0["refused"]["tol"] == F.START_TOL
    r = json.loads(R.out_path(rec).read_text())
    assert r["label"] is None and r["fallback_stage"] == "step0" and "refused" in r
    assert calls["n"] == 2                                                      # the priming render and S


def test_c2r_writes_no_label_when_step_0_falls_back_silent(tmp_path, monkeypatch):
    rec, _ = _panel_stub(tmp_path, monkeypatch, silent=True)
    R.cmd_search(argparse.Namespace(shard=(0, 1)))
    s0 = json.loads(R.step0_path(rec).read_text())
    assert s0["label"] is None and s0["best"]["fallback"].startswith("silent")
    r = json.loads(R.out_path(rec).read_text())
    assert r["label"] is None and r["fallback_stage"] == "step0" and "step 1" not in json.dumps(r.get("step1", ""))


def test_c2r_checks_step_0_against_a_ceiling_record_on_its_amp(tmp_path, monkeypatch):
    rec, _ = _panel_stub(tmp_path, monkeypatch, ceiling="pr12")
    cdir = tmp_path / "panel" / "ceiling"
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / f"{P.panel_fname(rec['key'])}.json").write_text(json.dumps(
        {"search": "A", "lag": 0, "evaluations": 3, "best": {"settings": {"x": "1"}, "judge": {"A": 1.0, "B": 1.0}}}))
    R.cmd_search(argparse.Namespace(shard=(0, 1)))
    cc = json.loads(R.step0_path(rec).read_text())["ceiling_check"]
    assert cc["same_half_and_lag"] is True and cc["same_settings"] is False


def test_c2_runs_unchanged_with_its_own_shard(tmp_path, monkeypatch, capsys):
    (row,), calls = T2._stub(tmp_path, monkeypatch)
    X.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(T2._out(tmp_path, row).read_text())
    assert r["ledger"].endswith(X.PHASE) and r["known_why"] == X.KNOWN_WHY and "step0" not in r
    assert "creator" not in r and math.isfinite(r["step1"]["start"]["value"])
    assert "C2-SEARCH DONE 0/1" in capsys.readouterr().out
