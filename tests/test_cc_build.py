import json

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


def test_the_old_bleed_gate_is_for_dry_runs_only():
    assert C.BLEED_GATE is False and C.SUM_LOWER is True          # amendment 2 (the user, 2026-10-29)
    with pytest.raises(SystemExit, match="dry runs"):
        C.main(["plan", "--bleed-gate"])


def test_the_screen_no_longer_reads_hiss():
    assert C.screen_ok({"flags": []}) and C.screen_ok({"flags": ["hiss"]})
    for f in (["hum"], ["hiss", "hum"], ["bleed"], ["clipping"], ["dropout", "hiss"]):
        assert not C.screen_ok({"flags": f})


def test_part15_takes_the_unheard_d2_rejects_only():
    ok = {"D1": "ear", "D2": "fail", "D3": "pass"}
    ver = {"a": {"ear": None, "trains": False, "source": "released", "measures": ok, "band": "Hazael"},
           "b": {"ear": None, "trains": False, "source": "released", "measures": {**ok, "D1": "fail"}, "band": "Hazael"},
           "c": {"ear": None, "trains": False, "source": "released", "measures": ok, "band": "Peter White"},
           "d": {"ear": "clean", "trains": True, "source": "released", "measures": ok, "band": "BKS"},
           "e": {"ear": None, "trains": False, "source": "tier 1 (step 0)", "measures": ok, "band": "The Travelling Band"},
           "f": {"ear": None, "trains": False, "source": "released", "measures": {**ok, "D2": "pass"}, "band": "Hazael"},
           "g": {"ear": None, "trains": False, "source": "heavy", "measures": ok, "band": "Ale Lak"}}
    assert C.part15_dis(ver) == ["a", "e"]


def _page(path, build, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"page": "p", "part": 15, "build": build, "items": items}))


def test_part15_exports_from_either_build(tmp_path, monkeypatch):
    di = {"id": "ear-di1", "family": "di", "paths": {"di": "/s/d.wav"}, "start_s": 10.0}
    stem = {"id": "ear-st1", "family": "stem", "paths": {"stem": "/s/k.wav"}, "start_s": 0.0, "session_dir": "/s"}
    _page(tmp_path / "v1/items.json", "b1", [di])
    _page(tmp_path / "v2/items.json", "b2", [stem, di])
    monkeypatch.setattr(C, "PART15_V1_ITEMS", tmp_path / "v1/items.json")
    monkeypatch.setattr(C, "PART15_DIR", tmp_path / "v2")
    monkeypatch.setattr(C, "INTAKE", tmp_path)
    monkeypatch.setattr(C, "ear_parts", lambda: {})
    monkeypatch.setattr(C, "SPOT_ANSWERS", tmp_path / "v1/items.json")         # any existing file: part 13 answered

    def export(name, build, answers, t):
        (tmp_path / name).write_text(json.dumps({"part": 15, "build": build, "exported": t, "answers": answers}))
    export("ear-answers-part15.json", "b1", [{"id": "ear-di1", "verdict": "unsure"},
                                             {"id": "ear-st1", "verdict": "guitar"}], "2026-10-30T08:00")
    src = C.ear_sources()
    assert [i["id"] for i in src[0][2]] == ["ear-di1"]                       # v1: DI cards only
    assert C.spot_answers() == {}                                            # no stem card from v1
    export("ear-answers-part15-v2.json", "b2", [{"id": "ear-di1", "verdict": "clean"},
                                                {"id": "ear-st1", "verdict": "clean"}], "2026-10-30T09:00")
    assert C.spot_answers() == {"/s": "clean"}
    dis, _ = C.load_ear()
    assert C.ear_verdict(dis["/s/d.wav"]) == "clean"                         # the later export replaces 'unsure'
    export("ear-answers-part15-x.json", "zz", [], "2026-10-30T10:00")
    with pytest.raises(SystemExit, match="matches neither"):
        C.ear_sources()


def test_a_stand_in_heard_with_another_guitar_leaves_its_sections():
    class X:
        inv = {"d": {"session_dir": "/s"}}
        sections = {"s1": {"di": "d"}, "s2": {"di": "d"}}
    rows = [{"section": "s1", "band": "B"}, {"section": "s2", "band": "B"}]
    amp_of = {"s1": [{"track": "a.wav"}], "s2": [{"track": "b.wav"}]}
    kept, left = C.drop_heard_stand_ins(rows, amp_of, X, {("/s", "a.wav"): "other_guitar", ("/s", "b.wav"): "clean_amp"})
    assert [r["section"] for r in kept] == ["s2"] and left[0]["section"] == "s1"


QS = "cambridge/TheTravellingBand_Quicksand_Full/"


@pytest.mark.skipif(not (C.INTAKE / "summary.json").exists() or not C.EAR_PARTS[11][0].exists(),
                    reason="needs the local T0 lists and ear exports")
def test_quicksand_elecgtr2_is_admitted_and_elecgtr3_waits_for_the_ear():
    v = C.verdicts(alignment=False)
    assert v[QS + "19_ElecGtr2DI.wav"]["trains"] and v[QS + "16_ElecGtr1DI.wav"]["trains"]
    heard15 = any(C.INTAKE.glob(C.PART15_ANSWERS))                       # part 15 heard ElecGtr3 clean
    assert v[QS + "22_ElecGtr3DI.wav"]["trains"] == heard15
    assert (v[QS + "22_ElecGtr3DI.wav"]["ear"] == "clean") == heard15


def _w(fine, prom, corr=0.6, lag=None):
    return {"t": 0.0, "lag_ms": fine if lag is None else lag, "corr": corr, "fine_ms": fine, "prominence": prom}


def test_alignment_verdicts():
    assert C.align_verdict([_w(1.5, 200)] * 5, "amp")[0] == "aligned"
    assert C.align_verdict([_w(1.5, 200)] * 4 + [_w(-18.5, 67)], "amp")[0] == "drift"         # an edit
    assert C.align_verdict([_w(129.8, 200)] * 8, "amp")[:2] == ("offset", 129.8)              # SugarFaith ElecGtr8
    assert C.align_verdict([_w(1.0, 200)] * 2, "amp")[0] == "no match"                        # too few readings
    # GCC decides over a repeated riff's envelope match a bar away
    assert C.align_verdict([_w(0.8, 80, corr=0.2)] * 4 + [_w(0.8, 80, corr=0.4, lag=1900.0)], "amp")[0] == "aligned"
    # a driven amp: GCC weak, the envelopes decide at their 10-ms steps
    assert C.align_verdict([_w(-7.6, 5, corr=0.95, lag=0.0)] * 5, "amp")[0] == "aligned"
    assert C.align_verdict([_w(-7.6, 5, corr=0.95, lag=0.0)] * 4 + [_w(9.0, 5, corr=0.9, lag=60.0)], "amp")[0] == "drift"
    assert C.align_verdict([], "song")[0] == "unverified"                                     # no amp track: unread


def test_a_section_where_the_amp_track_is_silent_is_out(tmp_path):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    sr, n = 48000, 48000 * 40
    rng = np.random.default_rng(3)
    di = (0.1 * rng.standard_normal(n)).astype(np.float32)
    amp = di.copy()
    amp[20 * sr:32 * sr] = 0.0                                   # the amp track muted 20-32 s, the DI plays on
    sf.write(str(tmp_path / "01_ElecGtr1DI.wav"), di, sr)
    sf.write(str(tmp_path / "02_ElecGtr1.wav"), amp, sr)
    rec = {"path": str(tmp_path / "01_ElecGtr1DI.wav"), "session_dir": str(tmp_path), "part": "ElecGtr1",
           "own": ["02_ElecGtr1.wav"]}
    cache = {}
    assert C.amp_silent(rec, 21.0, cache) and not C.amp_silent(rec, 2.0, cache)
    assert not C.amp_silent({**rec, "own": []}, 21.0, {})       # no amp track: cannot be read, passes
