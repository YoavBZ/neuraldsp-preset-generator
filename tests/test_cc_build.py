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
    assert not C.screen_ok({}) and not C.screen_ok({"clean": False}) and C.screen_ok({"clean": True})   # no flags field


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
    # partial silence (the review: Hazael ElecGtr3 at 65 s and 75 s): the amp plays on 15% of the section, silent on
    # 85% of the DI's playing frames -> out; silent on under 30% of them -> kept
    assert C.amp_silent(rec, 18.5, cache)                       # 18.5-28.5 s: silent 20-28.5 s
    assert not C.amp_silent(rec, 11.0, cache)                   # 11-21 s: silent on the last 1 s only


def test_silent_amp_share():
    di = [True] * 10
    assert C.silent_amp_share(di, [[True] * 10]) == 0.0
    assert C.silent_amp_share(di, [[True] * 7 + [False] * 3]) == pytest.approx(0.3)
    assert C.silent_amp_share(di, [[False] * 10, [True] * 5 + [False] * 5]) == pytest.approx(0.5)   # any own amp plays
    assert C.silent_amp_share([False] * 10, [[False] * 10]) == 0.0                                 # no DI, no claim


def test_alignment_gate_fails_closed_without_rows():
    ver = {"a": {"trains": True}, "b": {"trains": True}, "c": {"trains": False}}
    C.gate_alignment(ver, {})
    assert not ver["a"]["trains"] and ver["a"]["align_hold"] and not ver["b"]["trains"]
    ver = {"a": {"trains": True}, "b": {"trains": True}}
    al = {"a": {"verdict": "aligned"}, "b": {"verdict": "drift", "lag_ms": 1.0, "spread_ms": 30.0, "readings": 5,
                                          "kind": "amp"}}
    C.gate_alignment(ver, al)
    assert ver["a"]["trains"] and not ver["b"]["trains"] and "drift" in ver["b"]["why"]


def test_aligned_only_within_a1s_range():
    assert C.align_verdict([_w(24.4, 200)] * 3, "amp")[0] == "aligned"
    assert C.align_verdict([_w(-0.25, 200)] * 3, "amp")[0] == "outside A1's range"     # the amp before its DI
    assert C.align_verdict([_w(0.05, 200)] * 3, "amp")[0] == "outside A1's range"
    assert C.align_verdict([_w(40.0, 200)] * 3, "amp")[0] == "outside A1's range"      # beyond a mic, under an offset
    assert C.align_verdict([_w(-7.6, 5, corr=0.95, lag=0.0)] * 3, "amp")[0] == "aligned"   # envelopes: 10-ms steps
    assert C.align_verdict([_w(-7.6, 5, corr=0.95, lag=40.0)] * 3, "amp")[0] == "outside A1's range"


def test_a_stale_alignment_file_refuses(tmp_path):
    (tmp_path / "alignment-0of1.json").write_text(json.dumps({"method": "old", "dis": {}}))
    with pytest.raises(SystemExit, match="another alignment method"):
        C.load_alignment(tmp_path)
    (tmp_path / "alignment-0of1.json").write_text(json.dumps({"method": C.align_method(), "dis": {}}))
    assert C.load_alignment(tmp_path) == {}


ELECGTR8 = "sets-1-2/Forkupines_SugarFaith_Full/38_ElecGtr8DI.wav"


def test_the_shift_takes_align_dis_sign_a_positive_lag_delays_the_di():
    np = pytest.importorskip("numpy")
    from learn import verify_tracks as V

    sr, lag = C.ALIGN_SR, C.shift_frames(C.DI_SHIFT_MS[ELECGTR8], C.ALIGN_SR)
    rng = np.random.default_rng(8)
    di = rng.standard_normal(sr * 10)
    amp = C.delayed(di, lag)[:len(di)]                        # the amp track runs `lag` behind its DI
    before, _ = V.gcc_lag_ms(di, amp, sr, max_ms=C.ALIGN_MAX_S * 1000.0)
    assert before == pytest.approx(C.DI_SHIFT_MS[ELECGTR8], abs=0.05)   # positive: the amp track later
    after, _ = V.gcc_lag_ms(C.delayed(di, lag)[:len(di)], amp, sr, max_ms=C.ALIGN_MAX_S * 1000.0)
    assert after == 0.0                                       # the delayed copy reads in time


def test_shift_frames_and_delay():
    np = pytest.importorskip("numpy")
    assert C.shift_frames(129.83, 44100) == 5726 and C.shift_frames(129.83, 48000) == 6232
    y = C.delayed(np.ones((3, 2)), 2)
    assert y.shape == (5, 2) and not y[:2].any() and y[2:].all()


def test_a_shifted_di_reads_its_copy_and_a_wrong_source_refuses():
    copies = {ELECGTR8: {"source": "/s/38_ElecGtr8DI.wav", "path": "/c/38_ElecGtr8DI+129.83ms.wav", "shift_ms": 129.83}}
    inv = {ELECGTR8: {"path": "/s/38_ElecGtr8DI.wav", "part": "ElecGtr8"}, "x": {"path": "/s/x.wav"}}
    out = C.apply_shifts(inv, copies)
    assert out[ELECGTR8]["path"] == "/c/38_ElecGtr8DI+129.83ms.wav" and out[ELECGTR8]["shift_ms"] == 129.83
    assert out[ELECGTR8]["path_original"] == "/s/38_ElecGtr8DI.wav" and out["x"] == inv["x"]
    secs = {f"{ELECGTR8}@220.0": {"di": ELECGTR8, "path": "/s/38_ElecGtr8DI.wav", "start_s": 220.0}}
    assert C.apply_shifts(secs, copies, di_of=lambda sid, s: s["di"])[f"{ELECGTR8}@220.0"]["path"].startswith("/c/")
    with pytest.raises(SystemExit, match="made from"):
        C.apply_shifts({ELECGTR8: {"path": "/elsewhere.wav"}}, copies)


def test_a_copy_that_does_not_match_its_record_is_not_read(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "shift_dir", lambda: tmp_path)
    assert C.shifted_copies() == {}
    copy = tmp_path / "c.wav"
    copy.write_bytes(b"audio")
    rec = {"source": "/s.wav", "path": str(copy), "shift_ms": 129.83, "sha256": C._sha_file(copy)}
    (tmp_path / "shifts.json").write_text(json.dumps({"dis": {ELECGTR8: rec}}))
    assert set(C.shifted_copies()) == {ELECGTR8}
    copy.write_bytes(b"changed")                               # the copy changed since `shift`
    assert C.shifted_copies() == {}
    (tmp_path / "shifts.json").write_text(json.dumps({"dis": {ELECGTR8: {**rec, "shift_ms": 100.0,
                                                                         "sha256": C._sha_file(copy)}}}))
    assert C.shifted_copies() == {}                           # made with another shift than today's


def test_a_shifted_di_trains_only_when_its_copy_reads_about_zero():
    def gate(a):
        ver = {ELECGTR8: {"trains": True, "why": "heard clean"}}
        C.gate_alignment(ver, {ELECGTR8: a})
        return ver[ELECGTR8]
    base = {"kind": "amp", "spread_ms": 0.0, "readings": 8}
    v = gate({**base, "verdict": "offset", "lag_ms": 129.83})                     # read on the source: held
    assert not v["trains"] and v["align_hold"] and "delayed copy" in v["why"]
    v = gate({**base, "verdict": "outside A1's range", "lag_ms": 0.0, "shift_ms": 129.83})
    assert v["trains"] and "in time after the declared +129.83 ms shift" in v["why"] and "heard clean" in v["why"]
    assert gate({**base, "verdict": "aligned", "lag_ms": 0.5, "shift_ms": 129.83})["trains"]
    assert not gate({**base, "verdict": "aligned", "lag_ms": 5.0, "shift_ms": 129.83})["trains"]      # not about 0
    assert not gate({**base, "verdict": "drift", "lag_ms": 0.0, "shift_ms": 129.83})["trains"]
    assert not gate({**base, "verdict": "outside A1's range", "lag_ms": 0.0, "shift_ms": 100.0})["trains"]


def test_shift_refuses_smoke_and_an_undeclared_shift(monkeypatch):
    import argparse

    with pytest.raises(SystemExit, match="no smoke run"):
        C.cmd_shift(argparse.Namespace(smoke=True, out="/tmp/x"))
    monkeypatch.setattr(C, "ledger_declared", lambda *a, **k: False)
    with pytest.raises(SystemExit, match="amendment_4"):
        C.cmd_shift(argparse.Namespace(smoke=False, out=None))


def test_the_ledger_declares_the_shift():
    assert C.ledger_declared(key=C.SHIFT_KEY, mark=C.SHIFT_MARK)
