"""T3's F5 (`learn/trusted_data_t3.py`): the pure sets, membership, gain groups, readings and checks, with fakes.
No data files, no renders, no training."""

import json
import math
import pathlib

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
    monkeypatch.setattr(T, "rows_of", lambda root, stage, prefix: rend if prefix == "pc-render" else built)
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
    # part 9's DI-only DIs: the playing style heard on the DI card, before the session's tone; can't tell -> None
    assert T3.ear_call({"style_class": "clean_crunch", "session_tone": "high_gain"}) == "clean_crunch"
    assert T3.ear_call({"tone_class": "high_gain", "style_class": "clean_crunch"}) == "high_gain"
    assert T3.gain_group(T3.gain_class(None, T3.ear_call({"style_class": "clean_crunch"}))[0], False) == "not high gain"
    assert T3.gain_group(T3.gain_class(None, T3.ear_call({"style_class": "high_gain"}))[0], False) == "high gain"
    assert T3.ear_call({"style_class": None, "no_tone_counts_as": None}) is None
    # part 9 (DI only): can't tell or no answer falls to the DI-only rule, high gain
    assert T3.ear_call({"style_class": None, "session_tone": None, "no_tone_counts_as": "high_gain"}) == "high_gain"
    assert T3.ear_call({"style_class": "clean_crunch", "no_tone_counts_as": "high_gain"}) == "clean_crunch"


def test_intake_lines_name_each_admitted_band_correctly(tmp_path):
    tr = {"intake_admitted": ["cambridge-new/Strobe_Maya_Full/23_ElecGtrDI2.wav",
                              "cambridge-new/EmptySignifier_Change_Full/20_ElecGtr2DI.wav"],
          "intake_dis": {"cambridge-new/Strobe_Maya_Full/23_ElecGtrDI2.wav": {
                             "band": "Strobe", "verdict": "verified", "style_class": "clean_crunch", "heard": []},
                         "cambridge-new/EmptySignifier_Change_Full/20_ElecGtr2DI.wav": {
                             "band": "Empty Signifier", "verdict": "verified", "tone_class": "high_gain", "heard": []}}}
    lines = T3._intake_lines(tr, tmp_path)
    s = next(x for x in lines if "Strobe" in x)
    assert "clean_crunch (not high gain; from the playing style on its DI card)" in s
    assert "PR #296" not in s and "ElecGtr1" not in s
    tr["intake_dis"]["cambridge-new/Strobe_Maya_Full/23_ElecGtrDI2.wav"].update(style_class=None,
                                                                                no_tone_counts_as="high_gain")
    s = next(x for x in T3._intake_lines(tr, tmp_path) if "Strobe" in x)
    assert "high_gain (high gain; from the DI-only rule)" in s
    e = next(x for x in lines if "Empty Signifier" in x)
    assert "high_gain (high gain; from its amp track's tone card)" in e and "PR #296" in e


# --- V-real's new crops (vreal-crops) ---------------------------------------------------------------------------

IWMF1 = "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1"


def _tr_recut(**over):
    rc = {"crop_window_s": [90.0, 100.0], "recovered": True, "verdict": "verified", "heard": {"90.0": True}}
    rc.update(over)
    return {"recovered_targets": [IWMF1], "targets": {IWMF1: {"verdict": "verified", "recheck": rc}}}


def test_recut_window_needs_the_ear_verified_recheck():
    assert T3.recut_window(_tr_recut(), IWMF1) == ([90.0, 100.0], "ear-verified re-cut window")
    assert T3.recut_window(_tr_recut(heard={}), IWMF1)[0] is None
    assert T3.recut_window(_tr_recut(verdict="pending ear"), IWMF1)[0] is None
    assert T3.recut_window(_tr_recut(), "someone-else")[0] is None


def test_vreal_parts_reads_t3_crops_and_drops_only_on_the_rules():
    members = ["f1", "f2", IWMF1]
    built = {IWMF1: {"status": "built", "band": "Atlantis Bound", "gain_class": "clean"}}
    parts, dropped = T3.vreal_parts(members, ["f1", "f2", "f3"], built)
    assert parts["f1"] == {"kind": "stagef"} and parts[IWMF1]["kind"] == "t3" and not dropped
    assert T3.crop_jobs(members, ["f1", "f2"]) == [IWMF1]
    parts, dropped = T3.vreal_parts(members, ["f1", "f2"], {IWMF1: {"status": "dropped", "why": "x"}})
    assert IWMF1 not in parts and dropped[0][0] == IWMF1                # a crop that did not build: dropped
    with pytest.raises(SystemExit, match="vreal-crops"):
        T3.vreal_parts(members, ["f1", "f2"], {})                       # never attempted: refused
    parts, dropped = T3.vreal_parts(members, ["f1", "f2"], {}, drop_missing=True)
    assert IWMF1 not in parts and "drop-missing-crops" in dropped[0][1]  # the opt-in escape


def test_t3_units_carry_the_groups_own_s(tmp_path):
    parts = {"f1": {"kind": "stagef"}, IWMF1: {"kind": "t3", "band": "Atlantis Bound", "gain_class": "clean"}}
    (tmp_path / f"{IWMF1}|pr12.json").write_text(json.dumps(
        {"status": "done", "judge": {"S|A": {"A": 0.1, "B": 0.2}, "S|B": {"A": 0.3, "B": 0.4}}}))
    units = T3.t3_units(parts, tmp_path)
    assert len(units) == 6 and {u["slug"] for u in units} == {IWMF1}
    d = {(u["amp"], u["search"]): u["d"]["S"] for u in units}
    assert d[("pr12", "A")] == 0.2 and d[("pr12", "B")] == 0.3 and d[("ac20", "A")] is None
    assert all(u["cls"] == "clean" and u["band"] == "Atlantis Bound" for u in units)


def test_cmd_vreal_crops_cuts_separates_and_records(monkeypatch, tmp_path):
    import argparse
    import sys

    import soundfile as sf

    from learn import arm_a_mega53 as A
    from learn import direct_stems as DS

    sys.path.insert(0, str(T.V.PLUGIN_ROOT / "research"))
    import build_validation_crops as BVC

    old_crop = tmp_path / "old-crop"
    old_crop.mkdir()
    (old_crop / "record.json").write_text(json.dumps({"source": "cambridge", "song": "It Was My Fault For Waiting",
                                                      "part": "ElecGtr1", "verified_source_sha256": {"di.wav": "d", "amp.wav": "a"}}))
    plan = {"vreal": {"members": ["f1", IWMF1], "recovered": {IWMF1: {"window_s": [90.0, 100.0]}}}}
    calls = {}

    def fake_build(cat, root, source, song, part, out, *, rule, start_s):
        calls["args"] = (source, song, part, rule, start_s)
        out.mkdir(parents=True)
        sf.write(out / "mix.wav", np.full(480_000, 0.1, np.float32), 48_000, subtype="FLOAT")
        (out / "record.json").write_text("{}")
        return {"verified_source_sha256": {"di.wav": "d", "amp.wav": "a"}, "di_activity": 0.9, "reference_lufs": -20.0}

    monkeypatch.setattr(T3, "require_t3", lambda a: None)
    monkeypatch.setattr(T3, "load_plan", lambda root, smoke=False: plan)
    monkeypatch.setattr(T, "load_lists", lambda root, smoke=False: _tr_recut())
    monkeypatch.setattr(T.V, "out_root", lambda a: tmp_path)
    monkeypatch.setattr(A, "pool_slugs", lambda: ["f1"])
    monkeypatch.setattr(A, "lt_parts", lambda: {IWMF1: {"band": "Atlantis Bound", "gain_class": "clean",
                                                        "judge_lag": -43, "crop": str(old_crop)}})
    monkeypatch.setattr(BVC, "build", fake_build)
    monkeypatch.setattr(DS, "stem_separator", lambda sep, dev: (lambda x: x * 0.5))
    args = argparse.Namespace(smoke=False, out=None, device="cpu")
    T3.cmd_vreal_crops(args)
    man = json.loads(T3.crops_manifest_path(tmp_path).read_text())
    e = man["crops"][IWMF1]
    assert e["status"] == "built" and e["judge_lag"] == -43 and e["window_s"] == [90.0, 100.0]
    assert calls["args"] == ("cambridge", "It Was My Fault For Waiting", "ElecGtr1", "window", 90.0)
    assert np.allclose(T3.crop_stem({"stem": e["stem"]}), 0.05)
    assert "f1" not in man["crops"]                                      # stage F's crops are never cut again
    T3.cmd_vreal_crops(args)                                             # kept on a rerun (hash-checked)
    plan["vreal"]["recovered"][IWMF1]["window_s"] = [125.5, 135.5]
    T3.crops_manifest_path(tmp_path).unlink()
    import shutil
    shutil.rmtree(T3.crops_root(tmp_path))
    T3.cmd_vreal_crops(args)                                             # not the frozen window: dropped
    e = json.loads(T3.crops_manifest_path(tmp_path).read_text())["crops"][IWMF1]
    assert e["status"] == "dropped" and "frozen" in e["why"]


def test_vreal_crops_is_t3s():
    with pytest.raises(SystemExit, match="t3"):
        T.main(["vreal-crops"])


# --- the review's fixes: the rendered setting, the device rule, the merge partners, the shared FS5 -------------

class _Primer:
    def __init__(self):
        self.calls, self.renders = [], 0

    def render(self, key, di, sel, x):
        self.calls.append(dict(x))
        self.renders += 1
        return np.zeros((48_000 * 11, 2))


def _fake_twin(monkeypatch):
    from learn import full_space as F
    from learn import knob_ceiling as K

    core = {("parameters", "inputGain"): "1", ("reverb", "reverbActive"): "false", ("delay", "delaySync"): "1"}
    full = F.full_settings(core, {("reverb", "reverbActive"): "true", ("reverb", "reverbMix"): "0.4"})
    monkeypatch.setattr(T3, "full_twin", lambda i, menus: ("pr12", "wide", "clean", 1, full, core, None, 1))

    class M:
        dried = {"pr12": {K.START["clean"]["pr12"]: (1, dict(core))}}
    return M(), core, full


@pytest.mark.parametrize("kind", ["full", "positive"])
def test_render_example_saves_exactly_the_rendered_setting(monkeypatch, kind):
    from learn import local_objective as LO

    menus, core, full = _fake_twin(monkeypatch)
    pr = _Primer()
    x = {"i": 7, "amp": "pr12", "set": "F5"}
    row, y, _ = T3.render_example(x, menus, pr, "sec", None, {f"{a}/{b}": v for (a, b), v in core.items()}, kind,
                                  (12_000, 12_000 + 480_000))
    assert row["settings"] == LO.sdict(pr.calls[-1]) and row["kind"] == kind
    assert (pr.calls[-1] == full) == (kind == "full")
    assert y.shape == (480_000,)
    with pytest.raises(SystemExit, match="core draw"):
        T3.render_example(x, menus, pr, "sec", None, {"parameters/inputGain": "2"}, kind, (0, 10))


def test_control_move_is_a_sounding_new_control():
    from learn import every_control as EC
    from learn import full_space as F

    x = {c.path: c.neutral for c in EC.table("morgan") if c.neutral is not None}
    y = T3.control_move(x, "sw50r")
    assert {p for p in y if y[p] != x.get(p)} <= {("sw50rEQ", "sw50rEQActive"), ("sw50rEQ", "sw50rEQBand5")}
    assert ("sw50rEQ", "sw50rEQBand5") in F.new_paths()
    assert EC.mask(y, "morgan", amp="sw50r")[("sw50rEQ", "sw50rEQBand5")]


def test_positive_control_builds_on_t2s_device():
    dev = {1: "mps", 2: "cpu", 3: "mps", 4: None}
    rend = {1: {}, 2: {}, 3: {}, 4: {}}
    assert T3.pc_todo([1, 2, 3, 4, 5], rend, {3: {}}, dev, "mps") == [1]
    assert T3.pc_todo([1, 2, 3, 4, 5], rend, {}, dev, "cpu") == [2]


def test_target_features_match_part_cs_store():
    from learn import pretrain_set as PS
    from learn import song_aug as SA

    y = 0.1 * np.sin(2 * np.pi * 330 * np.arange(480_000) / 48_000)
    mels, halves = T3.target_features(y)
    h = PS.halves_mel(y)
    assert np.array_equal(mels["gA"], h["A"]) and np.array_equal(mels["gB"], h["B"])
    assert halves["lufs_A"] == pytest.approx(float(SA.lufs(y[PS.half_slices()["A"]])))


def test_shared_fs():
    rows = [{"i": 1}, {"i": 2}]
    assert T3.shared_fs({"D_core5": rows, "D_F5": list(rows)}) == [1, 2]
    with pytest.raises(SystemExit, match="FS5"):
        T3.shared_fs({"D_core5": rows, "D_F5": rows[:1]})


def test_train_data_parity_partners_from_each_arms_own_renders(monkeypatch, tmp_path):
    """Both arms train on the same examples with the same merge partners; each arm's partner mels and its rows'
    half loudness come from its own render family (part C's core renders for D_core5, the full twins for D_F5)."""
    from learn import direct_stems as DS
    from learn import every_control as EC
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pretrain_set as PS

    setting = {c.path: c.neutral for c in EC.table("morgan") if c.neutral is not None}
    ids = list(range(10, 22))
    pool = [{"i": i, "section": f"S{i % 4}", "band": "B", "amp": "pr12", "base": ("clean", "crunch")[i % 2],
             "label": {"parameters/inputGain": 0.5}, "lufs_A": -20.0, "lufs_B": -21.0} for i in ids]
    rend = {i: {"i": i, "settings": LO.sdict(setting),
                "target": {"lufs_A": -14.0 - i / 100, "lufs_B": -15.0 - i / 100}} for i in ids}
    rows = {"render": rend, "build": {i: {"i": i} for i in ids}}
    monkeypatch.setattr(T, "rows_of", lambda root, stage, prefix: rows[prefix] if stage == "t3" else {})
    plan = {"f5": ids[:9], "fs5": ids[9:]}

    class Ctx:
        pass
    ctx = Ctx()
    ctx.pool = pool
    core = T3.arm_rows(tmp_path, ctx, plan, "D_core5")
    full = T3.arm_rows(tmp_path, ctx, plan, "D_F5")
    for a, b in zip(core, full):
        assert [r["i"] for r in a] == [r["i"] for r in b] and [r["section"] for r in a] == [r["section"] for r in b]
    assert all(r["lufs_A"] == -20.0 for r in core[0])
    assert all(r["lufs_A"] == rend[r["i"]]["target"]["lufs_A"] for r in full[0])

    def npz(path, **arrays):
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, **arrays)

    u8 = lambda v: np.full((96, 446), v, np.uint8)     # noqa: E731
    files = {}
    for i in ids:
        for arm in ("D_core5", "D_F5"):
            m, s = T3.files_of(tmp_path, arm, i)
            npz(pathlib.Path(m), mA=u8(1), mB=u8(1), lufs=[-20.0, -20.0], gain_db=0.0, mastered=False)
            npz(pathlib.Path(s), sA=u8(2), sB=u8(2), lufs=[-22.0, -22.0])
            files[(arm, i)] = (m, s)
        npz(tmp_path / "partc" / f"{i}.npz", gA=u8(10), gB=u8(11))
        npz(T3.tgt_path(tmp_path, i), gA=u8(20), gB=u8(21), lufs=[-14.0, -15.0])
    monkeypatch.setattr(PS, "example_path", lambda i: tmp_path / "partc" / f"{i}.npz")
    data = {}
    for arm, (tr, es) in (("D_core5", core), ("D_F5", full)):
        rws = tr + es
        data[arm] = T.ArmData(rws, {r["i"]: files[(arm, r["i"])] for r in rws}, aug=True,
                              encode=T3.encode_for(arm), partner_path=T3.partner_path(tmp_path, arm))
    a, b = data["D_core5"], data["D_F5"]
    assert a.cands == b.cands and a.gpos == b.gpos and a.cands
    assert (a.G[:, 0] == 10).all() and (b.G[:, 0] == 20).all() and (b.G[:, 1] == 21).all()
    assert len(b.Y) == 7 and b.Y[0].shape[1] == len(F.CONT) and len(a.Y) == 6
    # the same partner draws (augmentation is seeded by example and epoch, not by arm)
    rng_a, rng_b = DS.aug_rng(ids[0], 3), DS.aug_rng(ids[0], 3)
    pa = DS.merge_partner(rng_a, a.cands[core[0][0]["base"]], core[0][0]["section"])
    pb = DS.merge_partner(rng_b, b.cands[full[0][0]["base"]], full[0][0]["section"])
    assert pa == pb
