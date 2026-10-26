"""T3's F5 (`learn/trusted_data_t3.py`): the pure sets, membership, gain groups, readings and checks, with fakes.
No data files, no renders, no training."""

import math

import pytest

np = pytest.importorskip("numpy")

from learn import trusted_data as T  # noqa: E402
from learn import trusted_data_t3 as T3  # noqa: E402


# --- the sets -------------------------------------------------------------------------------------------------

def _secs():
    return {"A": [f"A@{k}" for k in range(6)], "B": [f"B@{k}" for k in range(5)], "C": ["C@0", "C@1"]}


def test_fs5_sections_add_two_per_band_outside_early_stopping():
    es = ["A@0", "B@0", "C@0"]
    fs, new = T3.fs5_sections(_secs(), es)
    assert fs == T3.fs5_sections(_secs(), es)[0]                     # seeded
    assert set(es) <= set(fs) and not set(new) & set(es)
    by = {}
    for s in new:
        by.setdefault(s.split("@")[0], []).append(s)
    assert {b: len(v) for b, v in by.items()} == {"A": 2, "B": 2, "C": 1}   # C has one left


def test_split_f5_partitions_t2s_examples():
    section_of = {i: f"S{i % 5}" for i in range(50)}
    tr, es = list(range(40)), list(range(40, 50))
    f5, fs = T3.split_f5(tr, es, section_of, ["S1", "S2"])
    assert set(f5) | set(fs) == set(range(50)) and not set(f5) & set(fs)
    assert all(section_of[i] not in ("S1", "S2") for i in f5)
    assert set(es) <= set(fs)


def test_positive_ids_seeded_subset():
    ids = list(range(1000, 5000))
    a = T3.positive_ids(ids)
    assert a == T3.positive_ids(list(reversed(ids))) and len(a) == T3.PC_N and set(a) <= set(ids)
    assert T3.positive_ids(ids[:10]) == ids[:10]


def test_drop_both():
    assert T3.drop_both([1, 2, 3, 4], {2}, {4}) == [1, 3]
    assert T3.drop_both([1, 2]) == [1, 2]


# --- V-real's membership --------------------------------------------------------------------------------------

def _tr(signs="pending ear", signs_mdi="pending ear", iwmf="verified"):
    v10 = [f"part{k}" for k in range(10)]
    return {"v_real": v10, "recovered_targets": list(T3.RECOVERED) + list(T3.NOT_ELIGIBLE),
            "targets": {"cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1": {"verdict": iwmf},
                        "cambridge-Signs-ElecGtr6": {"verdict": signs}},
            "measure_dis": {"cambridge-Signs-ElecGtr6": {"verdict": signs_mdi}}}


def test_membership_without_signs_is_v_real_11():
    vr = T3.vreal_membership(_tr())
    assert vr["name"] == "V-real-11" and vr["members"][-1] == "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1"
    assert not vr["recovered"]["cambridge-Signs-ElecGtr6"]["eligible"]
    assert "Nosso" in next(iter(vr["not_eligible"]))
    assert vr["v_real_10"] == vr["members"][:10]


def test_signs_joins_only_when_part8_cleared_its_di():
    assert T3.vreal_membership(_tr(signs="verified", signs_mdi="pending ear"))["name"] == "V-real-11"
    vr = T3.vreal_membership(_tr(signs="verified", signs_mdi="verified"))
    assert vr["name"] == "V-real-12" and "cambridge-Signs-ElecGtr6" in vr["members"]
    assert T3.vreal_membership(_tr(iwmf="excluded"))["name"] == "V-real-10"


# --- gain groups ---------------------------------------------------------------------------------------------

def test_gain_class_order():
    assert T3.gain_class("crunch", "high_gain", "clean") == ("crunch", "part A")
    assert T3.gain_class(None, "high_gain", "clean") == ("high-gain", "intake ear call")
    assert T3.gain_class(None, None, "clean") == ("clean", "classifier on the amp track")
    assert T3.gain_class() == (None, "unclassed")


def test_gain_group_unclassed_rule():
    assert T3.gain_group(None, True) == "high gain" and T3.gain_group(None, False) == "not high gain"
    assert T3.gain_group("high-gain", False) == "high gain" and T3.gain_group("crunch", True) == "not high gain"


def test_pool_table():
    rows = [{"band": "A", "status": "s1", "class": "high-gain", "group": "high gain"},
            {"band": "A", "status": "s1", "class": None, "group": "not high gain"},
            {"band": "B", "status": "s2", "class": "clean", "group": "not high gain"}]
    t, tot = T3.pool_table(rows)
    assert t["A"]["s1"]["sections"] == 2 and t["A"]["s1"]["by_class"] == {"high-gain": 1, "unclassed": 1}
    assert tot == {"s1": {"high gain": 1, "not high gain": 1}, "s2": {"not high gain": 1}}


# --- readings ---------------------------------------------------------------------------------------------------

def test_contrasts_hold_every_declared_f5_row():
    c = T3.contrasts()
    assert c[f"{T3.FULL} - {T3.CORE} (the gate)"] == ("D_F5", "D_core5")
    for s in T3.TRAIN_SEEDS:
        assert (f"D_F5:s{s}", f"D_core5:s{s}") in c.values()
    for row in (("D_F5", "S"), ("D_core5", "S"), ("D_F5", "constant"), ("D_core5", "D_SYN"),
                ("D_F5:nopull", "D_core5:nopull")):
        assert row in c.values()
    fams = [v for k, v in c.items() if k.startswith("family")]
    assert len(fams) == 5 and all(a == "D_F5" and b.startswith("D_F5:at-S:") for a, b in fams)
    names = {x for ab in c.values() for x in ab} - {"S", "D_SYN"}
    assert names <= set(T3.ANSWERS) and len(T3.ANSWERS) == 14


def test_rule_reading_and_gate_next():
    s = lambda m, lo, hi: {"band_weighted_mean": m, "lo90": lo, "hi90": hi}   # noqa: E731
    assert T3.rule_reading(s(-0.05, -0.08, -0.01)).startswith("shown")
    assert T3.rule_reading(s(-0.01, -0.04, 0.02)).startswith("leans better")
    assert T3.rule_reading(s(0.02, 0.01, 0.03)).startswith("worse")
    assert T3.rule_reading(s(0.01, -0.02, 0.04)).startswith("point at or above 0")
    assert T3.rule_reading(None) == "incomplete"
    assert T3.gate_next(s(-0.001, -0.03, 0.03)).startswith("point below 0: F20 runs")
    assert T3.gate_next(s(0.0, -0.03, 0.03)).startswith("at or above 0: stop")


def test_lufs_summary_and_runs_at_cap():
    errs = [{"abs_error_db": 1.0}, {"abs_error_db": 3.0, "clamped": True}, {"abs_error_db": None}]
    s = T3.lufs_summary(errs)
    assert s["n"] == 2 and s["mean_db"] == 2.0 and s["clamped"] == 1
    assert T3.lufs_summary([]) == {"n": 0}
    recs = [{"arm": "D_F5", "seed": 1, "best_epoch": 37}, {"arm": "D_F5", "seed": 2, "best_epoch": 20}, {}]
    assert T3.runs_at_cap(recs, 40) == ["D_F5 seed 1 (best epoch 37/40)"]


def test_f5_estimate():
    e = T3.f5_estimate(5000, 50, 200, 4100, 10)
    assert e["renders"] == 5250 and e["separations"] == 5050
    assert e["vreal_renders"] == 10 * 3 * (2 * 14 + 1)
    assert e["sep_h"][0] < e["sep_h"][1] and e["train_h"][0] < e["train_h"][1]


# --- the output-gain check -------------------------------------------------------------------------------------

def _tone(db, n=480_000):
    t = np.arange(n) / 48_000
    return 10 ** (db / 20) * np.sin(2 * np.pi * 220 * t)


def test_lufs_check_fits_the_stem_and_scores_the_amp_track():
    render, stem, ref = _tone(-30), _tone(-18), _tone(-18)
    c = T3.lufs_check(2.0, render, stem, ref, "A", "B")
    assert c["gain_db"] == pytest.approx(14.0, abs=0.05) and not c["clamped"]
    assert c["abs_error_db"] == pytest.approx(0.0, abs=0.05)
    c = T3.lufs_check(2.0, render, stem, _tone(-24), "A", "B")
    assert c["abs_error_db"] == pytest.approx(6.0, abs=0.05)
    c = T3.lufs_check(2.0, render, _tone(-1), ref, "A", "B")           # beyond +24 dB: clamped
    assert c["clamped"] and c["gain_db"] == 24.0
    assert T3.lufs_check(0.0, np.zeros(480_000), stem, ref, "A", "B")["abs_error_db"] is None


# --- the menu, the sets on disk, the CLI ---------------------------------------------------------------------

def test_check_menu():
    m = {"pr12": {"a": (1, {("x", "y"): "1"})}}
    T3.check_menu(m, {"pr12": {"a": (1, {("x", "y"): "1"})}})
    with pytest.raises(SystemExit):
        T3.check_menu(m, {"pr12": {"a": (1, {("x", "y"): "2"})}})
    with pytest.raises(SystemExit):
        T3.check_menu(m, {"pr12": {"b": (1, {})}})


def test_t3_sets_drop_refusals_from_both_twins(monkeypatch, tmp_path):
    rows = {"render": {1: {"i": 1}, 2: {"i": 2, "refused": "full twin: near-silent"}, 3: {"i": 3}, 4: {"i": 4},
                       5: {"i": 5}},
            "build": {1: {"i": 1}, 3: {"i": 3, "refused": "no backing"}, 4: {"i": 4}, 2: {"i": 2, "refused": "x"}}}
    monkeypatch.setattr(T, "rows_of", lambda root, stage, prefix: rows[prefix])
    f5, fs, bad, unbuilt = T3.t3_sets(tmp_path, {"f5": [1, 2, 3], "fs5": [4, 5]})
    assert f5 == [1] and fs == [4] and bad == {2, 3} and unbuilt == {5}


def test_positive_control_state(monkeypatch, tmp_path):
    rend = {1: {"positive": {"ok": True, "share_t2_target": 1.0}}, 2: {"positive": {"ok": True, "share_t2_target": 0.995}}}
    built = {1: {"positive": {"ok": True, "mix_share": 1.0, "stem_share": 0.999}},
             2: {"positive": {"ok": False, "mix_share": 1.0, "stem_share": 0.9}}}
    monkeypatch.setattr(T, "rows_of", lambda root, stage, prefix: rend if prefix == "render" else built)
    ok, s = T3.positive_control(tmp_path, {"positive_control": [1, 2]})
    assert not ok and s["render_ok"] == 2 and s["build_ok"] == 1 and s["min_stem_share"] == 0.9
    built[2]["positive"]["ok"] = True
    assert T3.positive_control(tmp_path, {"positive_control": [1, 2]})[0]


def test_files_of_reads_the_right_twin(tmp_path):
    m, s = T3.files_of(tmp_path, "D_core5", 1234)
    assert "/t2/" in m and m.endswith("mix-t2.npz") and s.endswith("xlance_g-t2.npz")
    m, s = T3.files_of(tmp_path, "D_F5", 1234)
    assert "/t3/" in m and m.endswith("mix-t3.npz") and s.endswith("xlance_g-t3.npz")


def test_cli_flags_are_scoped():
    with pytest.raises(SystemExit):
        T.main(["render", "--stage", "t3", "--dry"])
    with pytest.raises(SystemExit):
        T.main(["vreal-predict", "--drop-missing-crops"])
    with pytest.raises(SystemExit, match="--stage t3 runs"):
        T.main(["t1-read", "--stage", "t3"])


def test_real_runs_need_the_ledger_entry(monkeypatch):
    import argparse

    monkeypatch.setattr(T.V, "require_real", lambda a: None)
    T3.require_t3(argparse.Namespace(smoke=False, out=None))          # the entry is in docs/dev-test-ledger.json
    monkeypatch.setattr(T3, "LEDGER_ID", "no-such-entry")
    with pytest.raises(SystemExit, match="ledger"):
        T3.require_t3(argparse.Namespace(smoke=False, out=None))


def test_answer_sets_are_safe_judge_keys():
    assert all("|" not in a for a in T3.ANSWERS)
    assert len(set(T3.ANSWERS)) == len(T3.ANSWERS)
    assert math.isclose(len(T3.FAMILY_ARMS), 5)


def test_metal_counts_wait_for_the_ear():
    summary = {"sessions": {"S1": {"a.wav": {"band": "Peppermark", "verdict": ["pending ear", ["D1 to the ear"]]},
                                   "b.wav": {"band": "Peppermark", "verdict": ["excluded", ["D2 fails"]]}}}}
    by, src = T3.metal_counts({}, summary)
    assert by == {"Peppermark": {"pending ear": 1, "excluded": 1}} and "not yet" in src
    lists = {"x": {"band": "DGX", "verdict": "verified"}, "y": {"band": "DGX", "verdict": "pending ear"},
             "z": {"band": "Empty Signifier", "verdict": "verified"}}
    by, src = T3.metal_counts(lists, summary)
    assert by == {"DGX": {"verified": 1, "pending ear": 1}} and src == "T0's lists"


def test_ear_call_order():
    assert T3.ear_call({"tone_class": "crunch", "session_tone": "high_gain"}) == "crunch"
    assert T3.ear_call({"tone_class": None, "session_tone": "clean"}) == "clean"
    assert T3.ear_call({"no_tone_counts_as": "high_gain"}) == "high_gain"
    assert T3.ear_call({}) is None
