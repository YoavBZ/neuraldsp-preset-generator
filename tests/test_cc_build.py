import pytest

from learn import cc_build as C
from learn import cc_pool as CP
from learn import direct_stems as DS


def test_ear_verdict_rejects_on_any_processed_answer_and_lets_a_later_part_replace_unsure():
    assert C.ear_verdict([]) is None
    assert C.ear_verdict([(0, 1.0, "clean"), (0, 30.0, "processed")]) == "rejected"
    assert C.ear_verdict([(0, 1.0, "clean"), (1, 50.0, "hum")]) == "rejected"
    assert C.ear_verdict([(0, 1.0, "unsure"), (0, 30.0, "clean")]) == "unsure"          # no later part
    assert C.ear_verdict([(0, 1.0, "unsure"), (0, 30.0, "clean"), (1, 1.0, "clean")]) == "clean"
    assert C.ear_verdict([(0, 1.0, "unsure"), (1, 1.0, "unsure")]) == "unsure"         # the last part's unsure stays
    assert C.ear_verdict([(0, 1.0, "clean"), (0, 30.0, "clean")]) == "clean"


def test_admission_needs_the_ear_and_the_measures():
    ok = {"D1": "ear", "D2": "pass", "D3": "pass", "D4": "pass"}
    assert C.admit("clean", ok)[0]
    assert not C.admit("unsure", ok)[0]
    assert not C.admit(None, ok)[0]
    assert C.admit("clean", {**ok, "D2": "fail"})[0]          # D2 gates windows, not the DI (the audit)
    assert not C.admit("clean", {**ok, "D1": "fail"})[0]
    assert not C.admit("clean", None)[0]


def test_ear_class_needs_half_a_window_of_overlap_and_high_gain_wins():
    heard = [(100.0, "crunch", ""), (104.0, "high_gain", "")]
    assert C.ear_class(100.0, heard) == "high-gain"
    assert C.ear_class(96.0, heard) == "crunch"            # overlaps 100-110 by 6 s, 104-114 by 2 s
    assert C.ear_class(120.0, heard) is None
    assert C.ear_class(100.0, [(100.0, "unsure", ""), (100.0, "not_fit", "")]) is None


def test_section_status_is_t0s_rule():
    assert C.section_status("fail", "pass", True) == "excluded"
    assert C.section_status("pass", "silent", False) == "silent"
    assert C.section_status("pass", "fail", False) == "pending ear"
    assert C.section_status("pass", "fail", True) == "usable"
    assert C.section_status("pass", "pass", False) == "usable"
    assert C.section_status("pass", "fail", False, di_heard_clean=True) == "usable"     # D4 does not override the ear
    assert C.section_status("fail", "pass", True, di_heard_clean=True) == "excluded"    # D2 still gates the window


def test_fs_sections_never_take_more_than_half_a_band():
    by = {"A": [f"a{k}" for k in range(40)], "B": ["b0"], "C": ["c0", "c1", "c2"]}
    fs = C.fs_sections(by)
    assert fs == C.fs_sections(by)                          # seeded
    assert not any(s.startswith("b") for s in fs)           # one section: kept for training
    assert sum(s.startswith("c") for s in fs) == 1
    assert 3 <= sum(s.startswith("a") for s in fs) <= 20


def test_heavy_trim_caps_the_heavy_share():
    by = {"Storm Of Particles": [f"s{k}" for k in range(30)], "Ale Lak": [f"a{k}" for k in range(10)],
          "Forkupines": [f"f{k}" for k in range(60)]}
    kept, dropped = C.heavy_trim(by)
    n = sum(len(v) for v in kept.values())
    heavy = len(kept.get("Storm Of Particles", [])) + len(kept.get("Ale Lak", []))
    assert heavy / n <= C.HEAVY_MAX + 1e-12
    assert len(kept["Forkupines"]) == 60 and len(dropped) == 40 - heavy
    assert C.heavy_trim({"Forkupines": ["f0"]}) == ({"Forkupines": ["f0"]}, [])


def test_allocation_cycles_part_cs_way_and_ids_stay_under_part_cs_validation_ids():
    ex = C.allocate(["s1", "s0", "s2"], 7, C.CC_BASE)
    assert [i for i, _ in ex] == list(range(C.CC_BASE, C.CC_BASE + 7))
    secs = [s for _, s in ex]
    assert sorted(secs[:3]) == ["s0", "s1", "s2"] and sorted(secs[3:6]) == ["s0", "s1", "s2"]
    C.check_ids([C.CC_BASE, C.FS_BASE + 5000])
    with pytest.raises(SystemExit):
        C.check_ids([DS.VAL_BASE_ID])
    with pytest.raises(SystemExit):
        C.check_ids([C.CC_BASE - 1])
    assert C.FS_BASE + 10_000 < DS.VAL_BASE_ID


def test_the_pool_bars_v_real_and_decision_ds_bands():
    for band in CP.VREAL_BANDS:
        with pytest.raises(ValueError):
            CP.refuse_pool_band(band)
    assert set(C.HEAVY_OUT) == {"Death Of A Romantic", "Hollow Ground"}
    assert not set(C.HEAVY_BANDS) & set(C.HEAVY_OUT)


def test_ear_windows_reads_di_and_scope_cards():
    items = [{"id": "a", "family": "di", "paths": {"di": "/x/d.wav"}, "start_s": 10.0},
             {"id": "b", "family": "scope", "paths": {"di": "/x/d.wav", "amp": "/x/a.wav"}, "start_s": 10.0},
             {"id": "c", "family": "stem", "paths": {"stem": "/x/s.wav"}, "start_s": 0.0}]
    ans = {"a": {"verdict": "clean"}, "b": {"verdict": "crunch", "note": "n"}}
    dis, cls = C.ear_windows([(ans, items)])
    assert dis == {"/x/d.wav": [(0, 10.0, "clean")]}
    assert cls == {"/x/d.wav": [(10.0, "crunch", "n")]}


def test_ledger_declares_d_cc_before_any_render():
    assert C.ledger_declared()


def test_policy_flags_refuse_a_written_plan():
    for flag in ("--no-bleed-gate", "--sum-lower"):
        with pytest.raises(SystemExit, match="dry runs"):
            C.main(["plan", flag])


QS = "cambridge/TheTravellingBand_Quicksand_Full/"


@pytest.mark.skipif(not (C.INTAKE / "summary.json").exists() or not C.EAR_PARTS[11][0].exists(),
                    reason="needs the local T0 lists and ear exports")
def test_quicksand_elecgtr2_is_admitted_and_elecgtr3_waits_for_the_ear():
    v = C.verdicts()
    assert v[QS + "19_ElecGtr2DI.wav"]["trains"] and v[QS + "16_ElecGtr1DI.wav"]["trains"]
    assert not v[QS + "22_ElecGtr3DI.wav"]["trains"] and v[QS + "22_ElecGtr3DI.wav"]["ear"] is None
