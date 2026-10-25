"""The trusted-data plan's self-built mixes, T1 and T2 (`learn/trusted_data.py`): the pure recipe and readings. No
data files, no renders, no training."""

import math
import re

import pytest

from learn import trusted_data as T


def test_pan_fold_constant_power_mono():
    assert math.isclose(T.pan_fold(0.0), math.sqrt(0.5), rel_tol=1e-12)
    assert math.isclose(T.pan_fold(1.0), 0.5, abs_tol=1e-12) and math.isclose(T.pan_fold(-1.0), 0.5, abs_tol=1e-12)
    assert math.isclose(T.pan_fold(0.3), T.pan_fold(-0.3), rel_tol=1e-12)
    assert T.pan_fold(5.0) == T.pan_fold(1.0)


def test_pans_and_draws_are_deterministic():
    assert T.target_pan(7) == T.target_pan(7) and -1 <= T.target_pan(7) <= 1
    assert T.other_pan(7, "x/DT.wav", True) == -T.target_pan(7)
    assert T.other_pan(7, "x/a.wav", False) == T.other_pan(7, "x/a.wav", False)
    assert T.other_pan(7, "x/a.wav", False) != T.other_pan(7, "x/b.wav", False)
    d = T.other_draw(7, "x/a.wav")
    assert d == T.other_draw(7, "x/a.wav") and d["amp"] in ("pr12", "sw50r", "ac20") and d["base"] in ("clean", "crunch")


def test_pick_others():
    cands = ["s/18_ElecGtr2DTDI.wav", "s/16_ElecGtr2DI.wav", "s/20_ElecGtr3DI.wav", "s/22_ElecGtr4DI.wav",
             "s/24_ElecGtr5DI.wav", "s/26_ElecGtr6DI.wav", "s/28_ElecGtr7DI.wav"]
    act = {c: 0.5 for c in cands}
    act["s/20_ElecGtr3DI.wav"] = 0.05                      # not playing
    act["s/28_ElecGtr7DI.wav"] = 0.9
    out = T.pick_others("s/16_ElecGtr2DI.wav", "ElecGtr2", cands, act)
    names = [o["di"] for o in out]
    assert "s/16_ElecGtr2DI.wav" not in names and "s/20_ElecGtr3DI.wav" not in names
    assert names[0] == "s/28_ElecGtr7DI.wav" and len(out) == T.MAX_OTHERS
    assert {o["di"]: o["dt"] for o in out}["s/18_ElecGtr2DTDI.wav"] is True
    assert sum(o["dt"] for o in out) == 1


def test_other_level_fallbacks():
    assert T.other_level(-20.0, [-30.0], [-25.0]) == (-20.0, "own amp track")
    assert T.other_level(None, [-30.0, -20.0, -22.0], [-25.0]) == (-22.0, "session amp median")
    assert T.other_level(None, [], [-25.0, -27.0]) == (-26.0, "stems median")
    assert T.other_level(None, [], []) == (None, "none")


def _rows(n_by_band):
    out, i = [], 0
    for b, n in n_by_band.items():
        for k in range(n):
            out.append({"i": i, "band": b, "section": f"{b}@{k // 10}"})
            i += 1
    return out


def test_stratified_by_band():
    rows = _rows({"A": 600, "B": 300, "C": 100})
    pick = T.stratified_by_band(rows, 100, 1)
    assert len(pick) == 100 and pick == T.stratified_by_band(rows, 100, 1)
    c = {b: sum(1 for r in pick if r["band"] == b) for b in "ABC"}
    assert c == {"A": 60, "B": 30, "C": 10}
    with pytest.raises(SystemExit):
        T.stratified_by_band(rows, 2000, 1)


def test_es_sections_one_per_band_at_least():
    by = {"A": {f"A{k}" for k in range(100)}, "B": {"B0", "B1"}}
    es = T.es_sections(by)
    assert sum(s.startswith("A") for s in es) == 5 and sum(s.startswith("B") for s in es) == 1
    assert es == T.es_sections(by)


def test_eggy_swap():
    kept, out, eg = T.eggy_swap(list(range(30)), [{"i": 1000 + k} for k in range(40)])
    assert len(out) == len(eg) == 10 and len(kept) == 20 and not set(kept) & set(out)
    assert (kept, out, eg) == T.eggy_swap(list(range(30)), [{"i": 1000 + k} for k in range(40)])
    with pytest.raises(SystemExit):
        T.eggy_swap(list(range(30)), [{"i": 1000}])


def test_ratio_bins():
    assert T.ratio_bin(-20.0) == "< -15" and T.ratio_bin(-12.0) == "-15 to -10"
    assert T.ratio_bin(-7.0) == "-10 to -5" and T.ratio_bin(-1.0) == ">= -5"


def test_mel_snr_and_contamination():
    np = pytest.importorskip("numpy")
    from learn import pretrain_set as PS

    rng = np.random.default_rng(0)
    ref_db = -60 + 20 * rng.random((96, 200))
    ref = PS.quant(ref_db)
    assert T.mel_snr(ref, ref) > 60 and T.contamination(ref, ref) == 0.0
    louder = PS.quant(ref_db + 6.0)                        # a level offset is aligned away
    assert T.mel_snr(louder, ref) > 30
    dirty = PS.quant(10 * np.log10(10 ** (ref_db / 10) + 10 ** ((-55 + 10 * rng.random((96, 200))) / 10)))
    assert T.mel_snr(dirty, ref) < T.mel_snr(louder, ref)
    assert T.contamination(dirty, ref) > 0.1


def test_reading_rule():
    assert T.reading((-0.01, -0.05, 0.03)).startswith("tie")
    assert T.reading((-0.05, -0.09, -0.01)).startswith("SYN better")
    assert T.reading((0.06, 0.01, 0.11)).startswith("SES better")
    assert T.reading(None) == "incomplete"
    assert T.union_refused({1}, [2, 1], ()) == {1, 2}


def test_seeds_and_arms():
    assert (T.PILOT_SEED, T.ES_SEED) == (20261099, 20261100)          # the plan's
    assert len({T.PILOT_SEED, T.ES_SEED, T.EGGY_SEED, T.OTHER_SEED}) == 4
    assert T.ARMS == ("SES", "SYN", "SYN-E") and T.TRAIN_SEEDS == (20261042, 20261043)
    assert set(T.K_OUT_BANDS) == {"John Morgan Kimock", "Swatkins"}


def test_only_the_render_commands_render():
    from learn import local_objective as LO

    for cmd in ("plan --stage t1", "build --stage t2 --device mps", "t1-read", "train --arm SYN --seed 20261042",
                "fit", "e-on-k", "vreal-predict", "report"):
        assert not any(re.search(p, f"python -m learn.trusted_data {cmd}") for p in LO.RENDERS)
    for cmd in ("render --stage t1 --shard 0/3", "vreal-render --shard 2/3"):
        assert any(re.search(p, f"python -u -m learn.trusted_data {cmd}") for p in LO.RENDERS)


def test_verified_dis_and_unusable_sections():
    tr = {"dis": {"a": {"verdict": "verified"}, "b": {"verdict": "pending ear"}, "c": {"verdict": "excluded"}},
          "unusable_sections": ["b@10.0", "a@20.0"]}
    assert T.verified_dis(tr) == {"a"} and T.unusable(tr) == {"b@10.0", "a@20.0"}
    tr["dis"]["a"]["sections"] = {"a@10.0": "usable", "a@20.0": "pending ear"}
    assert T.windows_of(tr) == {"a": {"a@10.0": "usable", "a@20.0": "pending ear"}, "b": {}, "c": {}}


def test_a_stale_plan_is_refused(tmp_path):
    (tmp_path / "t0").mkdir()
    (tmp_path / "t0" / "verified.json").write_text("{}")
    plan = {"lists_sha256": T.lists_sha(tmp_path)}
    T.check_lists(tmp_path, plan)
    (tmp_path / "t0" / "verified.json").write_text('{"changed": 1}')
    with pytest.raises(SystemExit):
        T.check_lists(tmp_path, plan)
    with pytest.raises(SystemExit):
        T.check_lists(tmp_path, {})


# --- the 2026-10-23 review's fixes -------------------------------------------------------------------------------

def test_a_pitch_confirmed_double_takes_the_targets_settings_and_silent_own_amps_leave_a_part_out():
    cands = ["s/04_ElecGtr04DI.wav", "s/05_ElecGtr05DI.wav"]
    out = T.pick_others("s/01_ElecGtr01DI.wav", "ElecGtr01", cands, {c: 0.5 for c in cands},
                        doubles={"s/04_ElecGtr04DI.wav"})
    assert {o["di"]: o["dt"] for o in out} == {"s/04_ElecGtr04DI.wav": True, "s/05_ElecGtr05DI.wav": False}
    assert T.other_level(None, [-30.0], [-25.0], has_own=True) == (None, "own amp tracks silent here")
    assert T.other_level(None, [-30.0], [-25.0], has_own=False) == (-30.0, "session amp median")


def test_stems_fold_once_as_centred_sources(tmp_path):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    pytest.importorskip("scipy")
    import types

    from learn import pretrain_set as PS

    n = int(round((PS.SEC_S + PS.TRIM_S + 2) * PS.SR))
    s = 0.1 * np.sin(2 * np.pi * 330 * np.arange(n) / PS.SR)
    sf.write(str(tmp_path / "mono.wav"), s, PS.SR)                                 # a centred source, one channel
    g = T.pan_fold(0.0)
    sf.write(str(tmp_path / "stereo.wav"), np.stack([s * g, s * g], 1), PS.SR)     # the same source panned centre
    ctx = types.SimpleNamespace(sections={"x": {"di": "d", "start_s": 0.5}}, inv={"d": {"session_dir": str(tmp_path)}})
    st = T.Stems(ctx)
    a, b = st.get("x", ["mono.wav"]), st.get("x", ["stereo.wav"])
    assert np.allclose(a, b, atol=1e-4) and np.isclose(np.abs(a).max(), 0.1 * g, rtol=0.02)


def test_empty_backing_is_refused():
    np = pytest.importorskip("numpy")
    pytest.importorskip("pyloudnorm")
    y = 0.1 * np.sin(2 * np.pi * 220 * np.arange(48000 * 3) / 48000)
    assert T.empty_backing_ok(y, -30.0) and not T.empty_backing_ok(y, -70.0)


def test_a_refused_t2_example_is_dropped_not_unbuilt(tmp_path):
    import json

    rows = tmp_path / "t2" / "rows"
    rows.mkdir(parents=True)
    (rows / "render-0.jsonl").write_text("\n".join(json.dumps({"i": i}) for i in (1, 2, 3)) + "\n")
    (rows / "build-0.jsonl").write_text(json.dumps({"i": 1}) + "\n" + json.dumps({"i": 2, "refused": "x"}) + "\n")
    bad, unbuilt = T.t2_refused(tmp_path, {"pilot": [1, 2], "es": [3]}, {1: {}, 2: {}, 3: {}})
    assert bad == {2, 3} and unbuilt == {3}                        # 2 is dropped for every arm; 3 is not built yet


def test_stale_rows_and_the_lists_hash(tmp_path, monkeypatch):
    import json

    old = {"examples": [{"i": 1, "others": [{"di": "a"}]}, {"i": 2, "others": []}]}
    new = {"examples": [{"i": 1, "others": []}, {"i": 2, "others": []}, {"i": 3, "others": []}]}
    assert T.stale_rows(old, new, {1: {}, 2: {}}) == [1] and T.stale_rows(None, new, {1: {}}) == []
    (tmp_path / "t0").mkdir()
    (tmp_path / "t0" / "verified.json").write_text(json.dumps({"dis": {"a": 1}, "time": "10:00"}))
    h = T.lists_sha(tmp_path)
    (tmp_path / "t0" / "verified.json").write_text(json.dumps({"dis": {"a": 1}, "time": "11:00"}))
    assert T.lists_sha(tmp_path) == h                              # a rerun that changes no verdict keeps the hash
    (tmp_path / "t0" / "verified.json").write_text(json.dumps({"dis": {"a": 2}, "time": "11:00"}))
    assert T.lists_sha(tmp_path) != h


def test_t2_reading_waits_for_every_direction_and_flags_refusals():
    units = [{"slug": "p", "amp": "pr12", "d": {"SES": 1.0, "SYN": 1.0}},
             {"slug": "q", "amp": "pr12", "d": {"SES": 1.0, "SYN": None}}]
    groups = {("p", "pr12"): {"status": "done"}, ("q", "pr12"): {"status": "done"}}
    gaps = T.report_gaps(units, ("SES", "SYN"), groups, {"p", "q"}, {"p", "q"}, {"SES": 0, "SYN": 0})
    assert len(gaps) == 1 and "SYN" in gaps[0]
    units[1]["d"]["SYN"] = 1.0
    assert T.report_gaps(units, ("SES", "SYN"), groups, {"p", "q"}, {"p", "q"}, {"SES": 0, "SYN": 0}) == []
    assert T.report_gaps(units, ("SES", "SYN"), groups, {"p"}, {"p", "q"}, {"SES": 0, "SYN": 1})


def test_section_activity_reads_against_the_files_playing_level(tmp_path):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    rng = np.random.default_rng(3)
    x = np.concatenate([0.3 * rng.standard_normal(48000 * 20), 1e-4 * rng.standard_normal(48000 * 20)])
    p = tmp_path / "di.wav"
    sf.write(str(p), x.astype(np.float32), 48000)
    files = {}
    assert T.section_activity(p, 5.0, files=files) > 0.9            # playing
    assert T.section_activity(p, 25.0, files=files) < 0.05          # a resting floor, 70 dB down


def test_the_song_blind_constant_joins_t2s_v_real_contrasts():
    pytest.importorskip("numpy")
    from learn import direct_sound_gate as G
    from learn import song_model as SM

    con = T.t2_contrasts(("SES", "SYN", T.CONST_ARM))
    assert list(con)[0] == "SYN - SES" and con["SYN - constant"] == ("SYN", "constant")
    assert con["constant - S"] == ("constant", "S") and "SYN-E - SYN" not in con
    assert "SES - constant" not in T.t2_contrasts(("SES", "SYN"))

    def label(vol, mic):
        return {"pr12Amp/pr12Volume": vol, "cabParameters/rightCabActive": "true",
                "cabParameters/rightCabPosition": 0.3, "cabParameters/rightMicType": mic,
                "cabParameters/leftMicType": "2", "sw50rAmp/sw50rBright": "false"}
    rows = [{"amp": "pr12", "base": "clean", "label": label(v, m)} for v, m in ((0.2, "3"), (0.4, "3"), (0.9, "7"))]
    c = G.const_from_json(T.constant_arm(rows)["constant"])[("pr12", "clean")]
    assert c["cont"][SM.CONT.index("pr12Amp/pr12Volume")] == pytest.approx(0.4)
    assert c["mics"][SM.CAT.index("cabParameters/rightMicType")] == 3


# --- the T1 audit's fixes (2026-10-25) ----------------------------------------------------------------------------

ADAM = ["22_AcousticGtr1.wav", "25_ElecGtr1.wav", "26_ElecGtr2.wav", "27_ElecGtr2DI.wav", "28_ElecGtr2DT.wav",
        "29_ElecGtr2DTDI.wav", "30_ElecGtr3.wav", "31_ElecGtr3DI.wav", "36_Synth1.wav", "18_BassDI.wav",
        "99_ElecGtr9.wav"]


def test_the_sessions_other_guitar_parts_include_parts_with_no_di():
    mix = [f for f in ADAM if not f.endswith("DI.wav") and f != "99_ElecGtr9.wav"]   # 99 is not in the mix list
    parts = T.session_guitar_parts(ADAM, mix, "s/31_ElecGtr3DI.wav", own=["30_ElecGtr3.wav"])
    assert parts == {"acousticgtr1": ["22_AcousticGtr1.wav"], "elecgtr1": ["25_ElecGtr1.wav"],
                     "elecgtr2": ["26_ElecGtr2.wav", "27_ElecGtr2DI.wav"],
                     "elecgtr2dt": ["28_ElecGtr2DT.wav", "29_ElecGtr2DTDI.wav"]}
    assert "elecgtr9" in T.session_guitar_parts(ADAM, None, "s/31_ElecGtr3DI.wav")     # no mix list: every file


def test_an_active_guitar_that_cannot_be_rendered_leaves_the_example_out():
    parts = {"elecgtr1": ["25_ElecGtr1.wav"], "elecgtr2": ["26_ElecGtr2.wav", "27_ElecGtr2DI.wav"],
             "elecgtr4": ["32_ElecGtr4.wav", "33_ElecGtr4DI.wav"], "elecgtr5": ["34_ElecGtr5.wav", "35_ElecGtr5DI.wav"]}
    act = {"25_ElecGtr1.wav": 1.0, "26_ElecGtr2.wav": 0.8, "27_ElecGtr2DI.wav": 0.78, "32_ElecGtr4.wav": 1.0,
           "33_ElecGtr4DI.wav": 0.02, "34_ElecGtr5.wav": 0.0, "35_ElecGtr5DI.wav": 0.0}
    ren = {"elecgtr2": None, "elecgtr4": "window excluded", "elecgtr5": "window silent"}
    b = T.blocked_parts(parts, act, ren)
    # ElecGtr1 has no DI; ElecGtr4's amp track plays while its window is excluded (the amp track counts); ElecGtr2 can
    # be rendered and ElecGtr5 is silent
    assert [(x["part"], x["why"]) for x in b] == [("elecgtr1", "no DI"), ("elecgtr4", "window excluded")]
    assert [x["part"] for x in T.blocked_parts(parts, act, ren, scope="di")] == ["elecgtr4"]
    assert T.blocked_parts(parts, {k: 0.05 for k in act}, ren) == []
    assert T.LEFT_OUT_ACTIVE == "an active guitar cannot be rendered"


def test_left_out_examples_are_counted_with_their_reason(monkeypatch, capsys):
    blocked = {"a@55.0": [{"part": "elecgtr1", "activity": 1.0, "why": "no DI"}], "a@15.0": []}
    monkeypatch.setattr(T, "section_blocked", lambda ctx, sid, *a, **k: blocked[sid])
    rows = [{"i": 1, "section": "a@55.0", "band": "X"}, {"i": 2, "section": "a@55.0", "band": "X"},
            {"i": 3, "section": "a@15.0", "band": "X"}]
    kept, left = T.leave_out_blocked(None, rows, set(), {}, set(), {})
    assert [r["i"] for r in kept] == [3]
    assert left == [{"section": "a@55.0", "band": "X", "reason": T.LEFT_OUT_ACTIVE, "examples": 2,
                     "guitars": blocked["a@55.0"]}]
    T.print_left_out(left)
    assert "left out: 2 examples in 1 sections" in capsys.readouterr().out


def test_section_blocked_reads_amp_tracks_and_t0s_windows(tmp_path):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    import types

    rng = np.random.default_rng(5)
    play = (0.2 * rng.standard_normal(48000 * 40)).astype(np.float32)
    rest = np.concatenate([play[:48000 * 20], 1e-5 * rng.standard_normal(48000 * 20)]).astype(np.float32)
    for name, x in (("31_ElecGtr3DI.wav", play), ("25_ElecGtr1.wav", play), ("26_ElecGtr2.wav", play),
                    ("27_ElecGtr2DI.wav", play), ("32_ElecGtr4.wav", rest), ("33_ElecGtr4DI.wav", rest)):
        sf.write(str(tmp_path / name), x, 48000)
    inv = {f"s/{n}": {"path": str(tmp_path / n), "session_dir": str(tmp_path), "own": []}
           for n in ("31_ElecGtr3DI.wav", "27_ElecGtr2DI.wav", "33_ElecGtr4DI.wav")}
    ctx = types.SimpleNamespace(sections={"s/31_ElecGtr3DI.wav@25.0": {"di": "s/31_ElecGtr3DI.wav", "start_s": 25.0},
                                          "s/31_ElecGtr3DI.wav@5.0": {"di": "s/31_ElecGtr3DI.wav", "start_s": 5.0}},
                                inv=inv)
    ver = {"s/27_ElecGtr2DI.wav", "s/33_ElecGtr4DI.wav"}
    wins = {"s/27_ElecGtr2DI.wav": {"s/27_ElecGtr2DI.wav@25.0": "usable", "s/27_ElecGtr2DI.wav@5.0": "usable"},
            "s/33_ElecGtr4DI.wav": {"s/33_ElecGtr4DI.wav@25.0": "silent", "s/33_ElecGtr4DI.wav@5.0": "excluded"}}
    b25 = T.section_blocked(ctx, "s/31_ElecGtr3DI.wav@25.0", ver, wins, set(), {})
    assert [(x["part"], x["why"]) for x in b25] == [("elecgtr1", "no DI")]        # ElecGtr4 rests at 25 s
    b5 = T.section_blocked(ctx, "s/31_ElecGtr3DI.wav@5.0", ver, wins, set(), {})
    assert [(x["part"], x["why"]) for x in b5] == [("elecgtr1", "no DI"), ("elecgtr4", "window excluded")]
    b5di = T.section_blocked(ctx, "s/31_ElecGtr3DI.wav@5.0", ver, wins, {"s/27_ElecGtr2DI.wav@5.0"}, {}, scope="di")
    assert [(x["part"], x["why"]) for x in b5di] == [("elecgtr2", "window in T0's unusable sections"),
                                                      ("elecgtr4", "window excluded")]


def test_a_near_silent_render_is_refused_not_lifted():
    assert T.RENDER_FLOOR_LUFS == -50.0
    assert T.near_silent(-50.5) == T.NEAR_SILENT == "near-silent render (gate or low output)"
    assert T.near_silent(None) == T.NEAR_SILENT and T.near_silent(-49.0) is None
    rows = {1: {"others": [{"di": "a", "render_lufs": -30.0}, {"di": "b", "render_lufs": -62.0}]},
            2: {"others": [{"di": "a", "left_out": "silent render"}]},
            3: {"others": [{"di": "a", "render_lufs": -46.0}, {"di": "c", "left_out": "no level"}]},
            4: {"refused": T.NEAR_SILENT, "others": [{"di": "a", "refused": T.NEAR_SILENT, "render_lufs": None}]}}
    assert T.rule2_examples(rows) == [1, 2, 4]
    src = __import__("inspect").getsource(T.cmd_render)                 # the render path refuses through the rows
    assert "near_silent(ly)" in src and '"left_out": "silent render"' not in src


def test_t1_reads_section_clustered_under_three_bands_and_keys_on_it():
    band_iv, sec_iv = (1.63, 0.12, 3.14, 2), (1.62, -0.31, 3.56, 26)            # T1 as run (2026-10-25)
    label, iv = T.primary_interval(band_iv, sec_iv, 2)
    assert label.startswith("section-clustered") and iv == sec_iv
    assert T.primary_interval(band_iv, sec_iv, 3) == ("band-clustered", band_iv)
    assert T.t1_reading(iv).startswith("no difference shown")
    assert T.t1_reading((1.0, 0.2, 1.8, 26)).startswith("K's stems are cleaner")
    assert T.t1_reading((-1.0, -1.8, -0.2, 26)).startswith("K's stems are less clean")
    assert T.t1_reading(None) == "incomplete"


def test_t1_summary_reports_medians_tails_and_bands():
    per = {"K": {1: 5.0, 2: -1.0, 3: 4.0, 4: 2.0, 5: 3.0, 6: -2.0},
           "V_sep": {1: 1.0, 2: 1.0, 3: 3.0, 4: 2.0, 5: 3.5, 6: 1.0}}
    band_of = {1: "A", 2: "A", 3: "A", 4: "B", 5: "B", 6: "B"}
    section_of = {1: "a1", 2: "a1", 3: "a2", 4: "b1", 5: "b2", 6: "b2"}
    s = T.t1_summary(per, band_of, section_of, set(per["K"]))
    assert s["examples"] == 6 and s["bands"] == ["A", "B"] and s["sections"] == 4
    assert s["primary"].startswith("section-clustered")
    assert s["K - V_sep mel SNR (primary)"] == s["K - V_sep mel SNR (section-clustered)"]
    assert s["K - V_sep median"] == pytest.approx(-0.25) and s["K - V_sep mean"] == pytest.approx(-0.5 / 6)
    assert s["per arm"]["K"]["share below 0 dB"] == pytest.approx(2 / 6)
    assert s["per arm"]["V_sep"]["share below 0 dB"] == 0.0
    assert s["per band"]["A"] == {"n": 3, "mean": pytest.approx(1.0), "median": pytest.approx(1.0)}
    assert s["reading"] == T.t1_reading(s["K - V_sep mel SNR (primary)"])


def test_subset_is_only_for_t1_read():
    with pytest.raises(SystemExit):
        T.main(["plan", "--subset", "rules"])


# --- rule 1, the user's decision (2026-10-25): amp tracks stand for active guitars that cannot be rendered ---------

def _rule1_ctx(sd):
    import types

    return types.SimpleNamespace(sections={"s/31_ElecGtr3DI.wav@55.0": {"di": "s/31_ElecGtr3DI.wav", "start_s": 55.0},
                                           "s/31_ElecGtr3DI.wav@15.0": {"di": "s/31_ElecGtr3DI.wav", "start_s": 15.0}},
                                 inv={"s/31_ElecGtr3DI.wav": {"session_dir": sd}})


def _bleed_file(root, sd, tracks):
    T._save(T.amp_bleed_path(root, sd), {"measure": T.AMP_BLEED_MEASURE, "session_dir": sd, "tracks": tracks})


def test_bleed_sources_are_the_non_guitar_tracks():
    files = ["01_Kick.wav", "16_Overheads.wav", "18_BassDI.wav", "22_AcousticGtr1.wav", "25_ElecGtr1.wav",
             "28_ElecGtr2DT.wav", "36_Synth1.wav", "43_LeadVox1.wav", "GTR 2 Amp_M81.wav"]
    assert T.bleed_sources(files) == ["01_Kick.wav", "16_Overheads.wav", "18_BassDI.wav", "36_Synth1.wav",
                                      "43_LeadVox1.wav"]


def test_amp_bleed_sums_takes_over_the_floor_on_a6s_line():
    assert T.AMP_BLEED_DB == -30.0
    total = T.amp_bleed_total({"kick": -35.0, "oh": -35.0, "bass": -45.0, "snare": None})
    assert total == pytest.approx(-31.99, abs=0.01)
    assert T.amp_bleed_total({"kick": -41.0, "bass": None}) is None                  # every take under -40 dB: none
    assert T.amp_status({"bleed_db": -30.0}) == "fail" and T.amp_status({"bleed_db": -30.1}) == "pass"
    assert T.amp_status({"bleed_db": None}) == "pass" and T.amp_status({"silent": True}) == "silent"
    assert T.amp_status(None) == "not measured"


def test_a_sparse_sources_blown_up_readings_are_no_take():
    # Adam Buckley, AcousticGtr3 read in ElecGtr1 (2026-10-25): held-out readings far below 0; unclipped, the null at
    # -1.15e9 read as a take of the whole track (0 dB)
    assert T.amp_take_db(-2.38e6, [-4.91e4, -1.15e9, -2.91e4, 0.0], 4.48e6) is None
    assert T.amp_take_db(1500.0, [1230.0, 967.0, 775.0, 2670.0], 4.48e6) == pytest.approx(-47.0, abs=0.1)  # Kick1
    assert T.amp_take_db(5e6, [0.0], 4.48e6) == 0.0                                  # never above the track


def test_an_amp_only_active_guitar_is_added_to_the_backing(monkeypatch, tmp_path):
    blocked = {"s/31_ElecGtr3DI.wav@55.0": [{"part": "elecgtr1", "activity": 1.0, "why": "no DI",
                                             "amp_tracks": ["25_ElecGtr1.wav"]},
                                            {"part": "acousticgtr1", "activity": 0.6, "why": "no DI",
                                             "amp_tracks": ["22_AcousticGtr1.wav"]}],
               "s/31_ElecGtr3DI.wav@15.0": []}
    monkeypatch.setattr(T, "section_blocked", lambda ctx, sid, *a, **k: blocked[sid])
    _bleed_file(tmp_path, "/sess", {"25_ElecGtr1.wav": {"bleed_db": None, "takes": {}, "silent": False},
                                    "22_AcousticGtr1.wav": {"bleed_db": -36.5, "takes": {}, "silent": False}})
    rows = [{"i": 1, "section": "s/31_ElecGtr3DI.wav@55.0", "band": "X"},
            {"i": 2, "section": "s/31_ElecGtr3DI.wav@15.0", "band": "X"}]
    kept, left, amp_of = T.apply_rule1(_rule1_ctx("/sess"), tmp_path, rows, set(), {}, set(), {})
    assert [r["i"] for r in kept] == [1, 2] and left == []
    assert amp_of == {"s/31_ElecGtr3DI.wav@55.0": [
        {"part": "elecgtr1", "track": "25_ElecGtr1.wav", "bleed_db": None},
        {"part": "acousticgtr1", "track": "22_AcousticGtr1.wav", "bleed_db": -36.5}]}   # acoustics follow the same path
    x = {"stems": {"v": ["16_Overheads.wav", "43_LeadVox1.wav"], "n": ["16_Overheads.wav"]},
         "amp_tracks": amp_of["s/31_ElecGtr3DI.wav@55.0"]}
    assert T.backing_tracks(x, False) == ["16_Overheads.wav", "25_ElecGtr1.wav", "22_AcousticGtr1.wav"]
    assert T.backing_tracks(x, True)[:2] == ["16_Overheads.wav", "43_LeadVox1.wav"]
    assert T.backing_tracks({"stems": {"v": [], "n": ["a.wav"]}}, False) == ["a.wav"]       # older recipes
    src = __import__("inspect").getsource(T.cmd_build)                    # the build sums them with the stems
    assert "backing_tracks(x, voc)" in src
    assert "apply_rule1(" in __import__("inspect").getsource(T.cmd_plan)


def test_a_failing_bleed_check_leaves_the_example_out(monkeypatch, tmp_path, capsys):
    b = {"part": "elecgtr02", "activity": 0.9, "why": "no DI", "amp_tracks": ["18_ElecGtr02.wav"]}
    use, bad = T.resolve_blocked([b], {"18_ElecGtr02.wav": {"bleed_db": -24.0, "silent": False}})
    assert use == [] and bad[0]["amp_why"] == "amp track bleed at or above -30 dB"
    assert bad[0]["amp"] == [{"track": "18_ElecGtr02.wav", "status": "fail", "bleed_db": -24.0}]
    two = {**b, "amp_tracks": ["11_ElecGtr2Mic1.wav", "12_ElecGtr2Mic2.wav"]}            # each track must pass
    assert T.resolve_blocked([two], {"11_ElecGtr2Mic1.wav": {"bleed_db": -40.0},
                                     "12_ElecGtr2Mic2.wav": {"bleed_db": -29.0}})[0] == []
    assert T.resolve_blocked([{**b, "amp_tracks": []}], {})[1][0]["amp_why"] == "no amp track"
    assert T.resolve_blocked([b], {"18_ElecGtr02.wav": {"silent": True}})[1][0]["amp_why"] == "amp track silent"
    with pytest.raises(SystemExit):                                                   # never guessed: amp-bleed first
        T.resolve_blocked([b], {})
    blocked = {"s/31_ElecGtr3DI.wav@55.0": [b], "s/31_ElecGtr3DI.wav@15.0": []}
    monkeypatch.setattr(T, "section_blocked", lambda ctx, sid, *a, **k: blocked[sid])
    _bleed_file(tmp_path, "/sess", {"18_ElecGtr02.wav": {"bleed_db": -24.0, "takes": {"kick": -24.0}, "silent": False}})
    rows = [{"i": 1, "section": "s/31_ElecGtr3DI.wav@55.0", "band": "X"},
            {"i": 2, "section": "s/31_ElecGtr3DI.wav@55.0", "band": "X"},
            {"i": 3, "section": "s/31_ElecGtr3DI.wav@15.0", "band": "X"}]
    kept, left, amp_of = T.apply_rule1(_rule1_ctx("/sess"), tmp_path, rows, set(), {}, set(), {})
    assert [r["i"] for r in kept] == [3] and amp_of == {}
    assert left[0]["reason"] == T.LEFT_OUT_NO_AMP == "an active guitar has no usable amp track"
    assert left[0]["examples"] == 2 and left[0]["guitars"][0]["amp"][0]["bleed_db"] == -24.0      # the value is kept
    T.print_left_out(left, T.LEFT_OUT_NO_AMP)
    out = capsys.readouterr().out
    assert "left out: 2 examples in 1 sections (an active guitar has no usable amp track)" in out
    assert "amp track bleed at or above -30 dB 2" in out
    _bleed_file(tmp_path, "/sess", {})                                               # a missing reading refuses
    with pytest.raises(SystemExit):
        T.apply_rule1(_rule1_ctx("/sess"), tmp_path, rows, set(), {}, set(), {})


def test_measure_amp_bleed_reads_other_instruments_in_the_amp_track(tmp_path):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    pytest.importorskip("scipy")
    sr, n = 48000, 48000 * 40
    rng = np.random.default_rng(11)
    env = np.repeat(rng.random(n // 4800) < 0.7, 4800)[:n]                  # a part that plays most of the time
    kick = (rng.standard_normal(n) * np.repeat(rng.random(n // 2400) < 0.3, 2400)[:n]).astype(np.float32)
    g1 = (0.3 * rng.standard_normal(n) * env).astype(np.float32)
    g2 = (0.3 * rng.standard_normal(n) * env[::-1]).astype(np.float32)
    leak = np.concatenate([np.zeros(48), kick[:-48]])                       # a 1 ms path into the mic
    gain = 10 ** (-12 / 20) * np.sqrt(np.mean(g1 ** 2) / np.mean(leak ** 2))
    unison = 0.8 * np.concatenate([np.zeros(48), g2[:-48]])                 # another guitar locked to ElecGtr2
    files = {"01_Kick.wav": kick, "25_ElecGtr1.wav": g1 + gain * leak, "26_ElecGtr2.wav": g2,
             "27_ElecGtr2DI.wav": g2, "28_ElecGtr3.wav": np.zeros(n, np.float32), "30_ElecGtr2DT.wav": unison}
    for name, x in files.items():
        sf.write(str(tmp_path / name), np.asarray(x, np.float32), sr)
    assert T.bleed_sources(sorted(files)) == ["01_Kick.wav"]                  # never another guitar track
    r = T.measure_amp_bleed(tmp_path, ["25_ElecGtr1.wav", "26_ElecGtr2.wav", "28_ElecGtr3.wav"], log=lambda *a: None)
    assert T.amp_status(r["25_ElecGtr1.wav"]) == "fail" and -20.0 < r["25_ElecGtr1.wav"]["bleed_db"] < -6.0
    # a unison guitar (its double, at -2 dB and 1 ms) is musical similarity, not bleed: it must not fail the track
    assert T.amp_status(r["26_ElecGtr2.wav"]) == "pass" and set(r["26_ElecGtr2.wav"]["takes"]) == {"01_Kick.wav"}
    assert T.amp_status(r["28_ElecGtr3.wav"]) == "silent"


def test_an_inventory_dis_own_amp_tracks_are_its_part():
    files = ["12_ElecGtr1a_Amp1.wav", "13_ElecGtr1b_Amp2.wav", "14_ElecGtr1c_DI.wav", "18_ElecGtr3a_Amp.wav",
             "19_ElecGtr3b_DI.wav", "20_ElecGtr3.wav", "21_ElecGtr3DI.wav", "01_Kick.wav"]
    owners = {"14_ElecGtr1c_DI.wav": ["12_ElecGtr1a_Amp1.wav", "13_ElecGtr1b_Amp2.wav"],
              "19_ElecGtr3b_DI.wav": ["18_ElecGtr3a_Amp.wav"], "21_ElecGtr3DI.wav": ["20_ElecGtr3.wav"]}
    keys = T.part_keys(files, owners)
    assert keys["12_ElecGtr1a_Amp1.wav"] == keys["13_ElecGtr1b_Amp2.wav"] == keys["14_ElecGtr1c_DI.wav"]
    assert keys["18_ElecGtr3a_Amp.wav"] == keys["19_ElecGtr3b_DI.wav"] != keys["20_ElecGtr3.wav"]
    assert "01_Kick.wav" not in keys
    assert T.part_keys(files)["12_ElecGtr1a_Amp1.wav"] == "elecgtr1a"                 # the name key alone splits them
    parts = T.session_guitar_parts(files, None, "s/21_ElecGtr3DI.wav", own=["20_ElecGtr3.wav"], owners=owners)
    assert parts == {"elecgtr1c": ["12_ElecGtr1a_Amp1.wav", "13_ElecGtr1b_Amp2.wav", "14_ElecGtr1c_DI.wav"],
                     "elecgtr3b": ["18_ElecGtr3a_Amp.wav", "19_ElecGtr3b_DI.wav"]}
