import re

import pytest

from learn import cc_readout as R
from learn import full_space as F
from learn import local_objective as LO
from learn import trusted_data_t3 as T3


def test_answers_are_the_arm_and_its_time_effects_at_S():
    assert R.answer_arms("D_F5bk") == ("D_F5bk", "D_F5bk:at-S:time effects and spring")
    assert R.TIME_FAMILY in F.FAMILIES


def test_contrasts_primary_co_primary_and_descriptive():
    c = R.contrasts("D_F5bk")
    names = list(c)
    assert c[names[0]] == ("D_F5bk", T3.FULL) and "primary" in names[0]
    assert c[names[1]] == ("D_F5bk:at-S:time effects and spring", "D_F5:at-S:time effects and spring")
    assert "co-primary" in names[1]
    assert {c[n] for n in names[2:]} == {("D_F5bk", T3.CORE), ("D_F5bk", "S"), ("D_F5bk", T3.CONST)}
    assert all("descriptive" in n for n in names[2:])


def test_f5_rendered_the_family_answer_this_reads_against():
    assert f"{T3.FULL}:at-S:{R.TIME_FAMILY}" in T3.ANSWERS


def test_renders_per_arm():
    assert R.renders_needed(33) == 165


def test_d_cc_is_registered_with_its_own_constant_and_unknown_arms_refuse():
    assert not R.spec_of("D_CC")["constant_is_d_f5s"]
    with pytest.raises(SystemExit):
        R.spec_of("D_nope")
    assert R.spec_of("D_F5bk")["constant_is_d_f5s"]


def test_same_constant_compares_nan_as_equal():
    nan = float("nan")
    f5 = {"constant": {"a": [1.0, nan]}, "constant_answers": {"sw": [None, 1.0]}}
    assert R.same_constant({"a": [1.0, nan]}, {"sw": [None, 1.0]}, f5)
    assert not R.same_constant({"a": [1.0, 2.0]}, {"sw": [None, 1.0]}, f5)


def test_machine_lists_see_the_renders():
    assert any(re.search(p, "/x/python -u -m learn.cc_readout vreal-render --arm D_F5bk --shard 0/3")
               for p in LO.RENDERS)
    assert not any(re.search(p, "/x/python -m learn.cc_readout report --arm D_F5bk") for p in LO.RENDERS)
    assert any(re.search(p, "/x/python -u -m learn.cc_build render --shard 1/3") for p in LO.RENDERS)
    assert not any(re.search(p, "/x/python -m learn.cc_build plan --dry") for p in LO.RENDERS)
    assert any(re.search(p, "/x/python -m learn.cc_build build --device mps") for p in LO.SEPARATIONS)


def test_ledger_declares_the_readout():
    assert R.ledger_declared()


def test_shard_only_for_render():
    with pytest.raises(SystemExit):
        R.main(["report", "--arm", "D_F5bk", "--shard", "1/3"])


def test_followups_render_two_answers_and_read_them_against_stored_renders():
    assert R.followup_answers("D_CC") == ("D_CC:at-S:pedals", "D_CC:constant")
    assert R.followup_renders_needed(33) == 165
    assert R.seed_arms("D_CC") == ("D_CC:s20261042", "D_CC:s20261043")
    c = R.followup_contrasts("D_CC")
    assert set(c.values()) == {("D_CC:at-S:pedals", "D_CC"), ("D_CC:at-S:pedals", "D_F5:at-S:pedals"),
                               ("D_CC", "D_CC:constant"), ("D_CC:constant", T3.CONST)}
    assert all("descriptive" in n for n in c)
    assert R.PEDALS in F.FAMILIES and R.pedal_arm(T3.FULL) in T3.ANSWERS and T3.CONST in T3.ANSWERS
    assert {f"{T3.FULL}:s{s}" for s in T3.TRAIN_SEEDS} <= set(T3.ANSWERS)    # D_F5's stored per-seed answers


def test_drive_summary_counts_drives_per_selection():
    def ans(d1, d2, gain):
        return {"settings": {"drive1/drive1Active": d1, "drive2/drive2Active": d2, "parameters/inputGain": gain}}
    answers = {"x": {"a|pr12|A": ans("true", "false", "2"), "a|pr12|B": ans("true", "true", "4"),
                     "a|ac20|A": ans("false", "true", "0"), "b|pr12|A": ans("true", "true", "6")}}
    s = R.drive_summary(answers, {"a": "crunch", "b": "clean"})["x"]
    assert s["pr12 crunch"] == {"directions": 2, "drive1/drive1Active": 2, "drive2/drive2Active": 1,
                                "input_gain_median": 3.0}
    assert s["crunch"]["directions"] == 3 and s["crunch"]["drive2/drive2Active"] == 2
    assert s["all"]["directions"] == 4 and s["all"]["drive1/drive1Active"] == 3


def test_runaway_prone_counts_the_scans_pattern():
    def ans(on, fb):
        return {"settings": {"delay/delayActive": on, "delay/delayFeedback": fb}}
    assert R.runaway_prone({"a": ans("true", "0.8"), "b": ans("true", "0.75"), "c": ans("false", "0.9"),
                            "d": ans("true", "0.5")}) == 2


def test_followups_are_declared_for_d_cc_only(tmp_path):
    import argparse

    assert R.followup_declared()
    with pytest.raises(SystemExit, match="declared for"):
        R.require_followup(argparse.Namespace(arm="D_F5bk", smoke=True, out=str(tmp_path)))


def test_followup_render_is_a_render_and_takes_shards():
    assert any(re.search(p, "/x/python -u -m learn.cc_readout followup-render --arm D_CC --shard 0/3")
               for p in LO.RENDERS)
    for cmd in ("followup-predict", "followup-report"):
        assert not any(re.search(p, f"/x/python -m learn.cc_readout {cmd} --arm D_CC") for p in LO.RENDERS)
    with pytest.raises(SystemExit, match="--shard is for"):
        R.main(["followup-report", "--arm", "D_CC", "--shard", "1/3"])


def test_new_predictions_refuse_over_groups_rendered_from_other_ones(tmp_path):
    groups = tmp_path / "groups"
    prev = {"models": {"s0": "a"}, "fit_sha256": "f"}
    R.refuse_stale_groups(prev, {"s0": "b"}, "f", groups)  # nothing rendered yet: fine
    R.refuse_stale_groups(None, {"s0": "b"}, "f", groups)
    groups.mkdir()
    (groups / "x|AC20.json").write_text("{}")
    R.refuse_stale_groups(prev, {"s0": "a"}, "f", groups)  # same models and fit: a resume
    for models, fit in (({"s0": "b"}, "f"), ({"s0": "a"}, "g")):
        with pytest.raises(SystemExit, match="other models"):
            R.refuse_stale_groups(prev, models, fit, groups)
