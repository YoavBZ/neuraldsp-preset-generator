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


def test_real_runs_refuse_out_and_smoke_needs_out():
    import pytest

    with pytest.raises(SystemExit):
        B.main(["plan", "--smoke"])
