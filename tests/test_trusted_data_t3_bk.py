import re

from learn import local_objective as LO
from learn import local_objective_1c as C
from learn import trusted_data_t3_bk as B


def ex(i=1, v=("k", "s", "vox"), n=("k", "s"), drawn=True, amp_tracks=()):
    return {"i": i, "band": "B", "section": f"s{i % 2}", "draw": {"vocals_drawn": drawn},
            "stems": {"v": list(v), "n": list(n)}, "amp_tracks": [{"track": t} for t in amp_tracks]}


def test_vocal_variant_follows_t2s_rule():
    x = ex()
    assert B.vocal_variant(x, ["k", "vox"], ["k"]) is True
    assert B.vocal_variant(x, ["k"], ["k"]) is False                      # no vocal stem passes: no vocals
    assert B.vocal_variant(ex(drawn=False), ["k", "vox"], ["k"]) is False


def test_backing_keeps_amp_track_stand_ins():
    x = ex(amp_tracks=("gtr2amp",))
    assert B.backing_of(x, ["k", "b", "vox"], ["k", "b"]) == ["k", "b", "vox", "gtr2amp"]


def test_entry_same_when_the_backing_does_not_change():
    x = ex()
    e = B.example_entry(x, ["k", "s", "vox"], ["k", "s"], [], "f5", "mps")
    assert e["same"] and e["left_out"] is None and e["vocals"]


def test_entry_changed_and_vocal_variant_change_counts_as_changed():
    x = ex(v=("k",), n=("k",))                                             # T2: no vocals passed
    e = B.example_entry(x, ["k", "vox"], ["k"], [], "f5", "cpu")
    assert not e["same"] and e["vocals"] and e["new"] == {"v": ["k", "vox"], "n": ["k"]}
    assert e["old"] == {"v": ["k"], "n": ["k"]}


def test_entry_unchanged_vocals_variant_not_drawn_is_same():
    x = ex(v=("k",), n=("k",), drawn=False)                               # vocals not drawn: only "n" is heard
    assert B.example_entry(x, ["k", "vox"], ["k"], [], "f5", "cpu")["same"]


def test_target_double_is_left_out():
    e = B.example_entry(ex(amp_tracks=("ElecGtr1DT",)), ["k"], ["k"], ["ElecGtr1DT"], "fs5", "mps")
    assert e["left_out"] and "ElecGtr1DT" in e["left_out"]


def entries():
    return [B.example_entry(ex(1), ["k", "s", "vox"], ["k", "s"], [], "f5", "mps"),            # same
            B.example_entry(ex(3), ["k", "s", "b", "vox"], ["k", "s", "b"], [], "f5", "mps"),  # changed, s1
            B.example_entry(ex(5), ["k", "s", "b", "vox"], ["k", "s", "b"], [], "f5", "cpu"),  # changed, s1
            B.example_entry(ex(2), ["k", "s", "b", "vox"], ["k", "s", "b"], [], "fs5", "cpu"),  # changed, s0
            B.example_entry(ex(4), ["k"], ["k"], ["dt"], "f5", "cpu")]                          # left out, s0


def test_control_takes_the_first_changed_kept_example_per_section():
    assert B.control_ids(entries()) == [2, 3]


def test_build_jobs_by_t3s_device_only_changed_and_kept():
    es = entries()
    assert B.build_jobs(es, "mps") == [3]
    assert B.build_jobs(es, "cpu") == [5, 2]


def test_files_reuse_t3_for_unchanged_examples(tmp_path):
    es = entries()
    mix, stem = B.files_for(es[0], tmp_path)
    assert "/t3/" in mix and mix.endswith("mix-t3.npz") and stem.endswith("xlance_g-t3.npz")
    mix, stem = B.files_for(es[1], tmp_path)
    assert f"/{B.OUT_DIR}/" in mix and mix.endswith("mix-bk.npz") and stem.endswith("xlance_g-bk.npz")


def test_summary_counts_per_band():
    s = B.summary(entries())["B"]
    assert s == {"examples": 5, "changed": 4, "left_out": 1, "stems_old": 2.0, "stems_new": 2.4}


def test_ledger_declares_the_arm():
    assert B.ledger_declared()


def test_machine_lists_see_the_builds_and_training():
    for cmd in ("control --device mps", "build --device cpu --order desc"):
        assert any(re.search(p, f"/x/python -u -m learn.trusted_data_t3_bk {cmd}") for p in LO.SEPARATIONS)
    assert not any(re.search(p, "/x/python -m learn.trusted_data_t3_bk plan") for p in LO.SEPARATIONS)
    assert any(re.search(p, "/x/python -m learn.trusted_data_t3_bk train --seed 20261042") for p in C.TRAINING)


SD = "/data/S"
FILES = ["01_Kick.wav", "02_Snare.wav", "03_BassDI.wav", "05_Vox.wav"]


def fixture_ctx():
    from types import SimpleNamespace

    di, other = f"{SD}/10_ElecGtr1DI.wav", f"{SD}/12_ElecGtr2DI.wav"
    inv = {d: {"session_dir": SD, "path": d, "mix": None, "vocals": None, "own": None} for d in (di, other)}
    ctx = SimpleNamespace(sections={"sec": {"di": di, "start_s": 0.0}}, inv=inv, ratios=None, eval_mix=None)
    scan = {SD: {"sources": ["11_ElecGtr1Amp.wav", "13_ElecGtr2Amp.wav", "14_ElecGtr3Amp.wav"],
                 "stems": {"01_Kick.wav": {"11_ElecGtr1Amp.wav": -20.0, "14_ElecGtr3Amp.wav": -50.0},   # the target leaks
                           "02_Snare.wav": {"14_ElecGtr3Amp.wav": -20.0},       # a guitar not replaced: kept
                           "03_BassDI.wav": {"11_ElecGtr1Amp.wav": -10.0},      # line-level: exempt
                           "05_Vox.wav": {"13_ElecGtr2Amp.wav": -30.0}}}}       # a rendered other guitar leaks
    return ctx, scan, {SD: list(FILES)}, di, other


def test_plans_stems_are_example_recipes(monkeypatch, tmp_path):
    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    ctx, scan, verified_stems, di, other = fixture_ctx()
    monkeypatch.setattr(T, "section_candidates", lambda *a: ([other], {other: 1.0}))
    meta = tmp_path / "b.json"
    meta.write_text('{"has_vocals": true}')
    monkeypatch.setattr(PS, "backing_path", lambda sid: tmp_path / "b.wav")
    monkeypatch.setattr(PS, "mix_params", lambda *a: (-3.0, True, 0.0, -14.0))
    monkeypatch.setattr(DS, "master_draw", lambda i: (False, None))
    act = {("doubles", di, 0.0): ()}
    x = T.example_recipe(ctx, {"i": 7, "section": "sec", "band": "B", "amp": "pr12", "base": "clean"}, set(),
                         verified_stems, act, takes=(scan, -35.0))
    assert [o["di"] for o in x["others"]] == [other]
    assert B.bk_stems(ctx, x, verified_stems, scan, -35.0) == (x["stems"]["v"], x["stems"]["n"])
    assert x["stems"]["v"] == ["02_Snare.wav", "03_BassDI.wav"]          # kick and vocals dropped, as the rule says
    lone = {**x, "others": []}                                           # the other guitar not replaced: vocals back
    assert B.bk_stems(ctx, lone, verified_stems, scan, -35.0)[0] == ["02_Snare.wav", "03_BassDI.wav", "05_Vox.wav"]


def test_row_current_by_backing_hash_and_legacy_plan():
    want = B.tracks_sha(["k", "s"])
    assert B.row_current({"i": 1, "backing_sha": want}, want, "any")
    assert not B.row_current({"i": 1, "backing_sha": B.tracks_sha(["k"])}, want, B.LEGACY_PLAN_SHA)
    assert B.row_current({"i": 1}, want, B.LEGACY_PLAN_SHA)                # tonight's rows, plan unchanged
    assert not B.row_current({"i": 1}, want, "a-new-plan")                  # re-planned: tonight's rows redo
    assert not B.row_current({"i": 1, "refused": "x", "backing_sha": want}, want, "any")
    assert not B.row_current(None, want, B.LEGACY_PLAN_SHA)


def ready_plan():
    es = entries()[:4]                                                     # 1 same; 3, 5, 2 changed
    return {"examples": es, "control": B.control_ids(es), "f5": [1, 3, 5], "fs5": [2]}


def built(p):
    ent = {e["i"]: e for e in p["examples"]}
    b = {e["i"]: {"i": e["i"], "backing_sha": B.tracks_sha(e["backing"])} for e in p["examples"] if not e["same"]}
    c = {i: {"i": i, "ok": True, "backing_sha": B.tracks_sha(ent[i]["backing_old"])} for i in p["control"]}
    return b, c


def refusals(p, b, c, exists=lambda i: True, tr=(1, 3, 5), es=(2,), f5_why=None):
    return B.train_refusals(p, b, c, exists, "plan-sha", list(tr), list(es), f5_why)


def test_train_may_run_when_everything_is_in_place():
    p = ready_plan()
    assert refusals(p, *built(p)) == []


def test_train_refuses_unbuilt_stale_or_missing_files():
    p = ready_plan()
    b, c = built(p)
    del b[3]
    assert refusals(p, b, c) == [(3, "not built from the plan's backing")]
    b, c = built(p)
    b[5]["backing_sha"] = B.tracks_sha(["old"])                            # made from another backing
    assert refusals(p, b, c) == [(5, "not built from the plan's backing")]
    b, c = built(p)
    assert refusals(p, b, c, exists=lambda i: i != 2) == [(2, "not built from the plan's backing")]


def test_train_refuses_refused_and_left_out():
    p = ready_plan()
    b, c = built(p)
    b[3]["refused"] = "no backing"
    assert refusals(p, b, c) == [(3, "refused: no backing")]
    p["examples"].append(entries()[4])                                     # the target-double example
    b, c = built(p)
    assert [w for i, w in refusals(p, b, c)] == ["left out: a target-double stand-in: ['dt']"]


def test_train_refuses_a_failed_or_stale_control():
    p = ready_plan()
    b, c = built(p)
    c[p["control"][0]]["ok"] = False
    assert refusals(p, b, c) == [(p["control"][0], "pipeline control not passed")]
    b, c = built(p)
    del c[p["control"][1]]
    assert refusals(p, b, c) == [(p["control"][1], "pipeline control not passed")]


def test_train_refuses_examples_other_than_the_plans_or_d_f5s():
    p = ready_plan()
    b, c = built(p)
    assert refusals(p, b, c, tr=(1, 3)) == [(None, "the F5/FS5 examples differ from this stage's plan")]
    assert refusals(p, b, c, f5_why="3 train examples, D_F5 had 4") == [
        (None, "not D_F5's examples: 3 train examples, D_F5 had 4")]


def test_real_runs_refuse_out_and_smoke_needs_out():
    import pytest

    with pytest.raises(SystemExit):
        B.main(["plan", "--smoke"])
