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
    o = {"di": "s/27_ElecGtr2DI.wav", "dt": False, "pan": 0.0}
    row = {"i": 1, "others": []}                                          # the render path's placement (rule 2)
    acc = T.place_other(row, 0.0, 1.0, -62.0, -20.0, "own amp track", o, "pr12", {})
    assert acc == 0.0 and row["refused"] == T.NEAR_SILENT and row["others"][0]["render_lufs"] == -62.0
    row = {"i": 2, "others": []}
    assert T.place_other(row, 0.0, 1.0, None, -20.0, "own amp track", o, "pr12", {}) == 0.0 and row["refused"]
    row = {"i": 3, "others": []}
    acc = T.place_other(row, 0.0, 1.0, -30.0, -20.0, "own amp track", o, "pr12", {})   # +10 dB, centre fold
    assert acc == pytest.approx(10 ** 0.5 * T.pan_fold(0.0)) and "refused" not in row
    assert row["others"][0]["gain_db"] == pytest.approx(10 + 20 * math.log10(T.pan_fold(0.0)))
    assert T.refusal_counts([{"refused": T.NEAR_SILENT}, {}, {"refused": T.NEAR_SILENT}, {"refused": "x"}]) == {
        T.NEAR_SILENT: 2, "x": 1}


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
    with pytest.raises(SystemExit, match="--subset is for t1-read"):
        T.main(["plan", "--subset", "rules"])


# --- rule 1, the user's decision (2026-10-25): amp tracks stand for active guitars that cannot be rendered ---------

def _rule1_ctx(sd, sids=("s/31_ElecGtr3DI.wav@55.0", "s/31_ElecGtr3DI.wav@15.0")):
    import types

    return types.SimpleNamespace(sections={sid: {"di": "s/31_ElecGtr3DI.wav", "start_s": float(sid.split("@")[1])}
                                           for sid in sids},
                                 inv={"s/31_ElecGtr3DI.wav": {"session_dir": sd}})


def _raw(bleed_db=None, share=1.0):
    """A stored reading whose one non-guitar source reads `bleed_db` (None: no take)."""
    real = 0.0 if bleed_db is None else 10 ** (bleed_db / 10)
    return {"silent": False, "sources": {"01_Kick.wav": {"real": real, "nulls": [0.0] * 4, "active_share": share}}}


def _bleed_file(root, sd, tracks):
    T._save(T.amp_bleed_path(root, sd), {"measure": T.AMP_BLEED_MEASURE, "session_dir": sd, "tracks": tracks})


def test_bleed_sources_are_the_non_guitar_tracks():
    files = ["01_Kick.wav", "16_Overheads.wav", "18_BassDI.wav", "22_AcousticGtr1.wav", "25_ElecGtr1.wav",
             "28_ElecGtr2DT.wav", "36_Synth1.wav", "43_LeadVox1.wav", "GTR 2 Amp_M81.wav"]
    assert T.bleed_sources(files) == ["01_Kick.wav", "16_Overheads.wav", "18_BassDI.wav", "36_Synth1.wav",
                                      "43_LeadVox1.wav"]


def test_raw_takes_are_not_clipped_and_untrustworthy_sources_are_unmeasurable():
    # an unrelated source reads slightly below 0 in both the real and the rolled readings; injected bleed at -28 dB
    # rides on that: the raw take reads it, while clipping both at 0 (the first fix) read it about 2 dB low
    t, why = T.source_take({"real": 10 ** -2.8 - 5e-4, "nulls": [-5e-4] * 4, "active_share": 0.9})
    assert why is None and t == pytest.approx(-28.0, abs=0.01)
    assert T.source_take({"real": -5e-4, "nulls": [-5e-4] * 4, "active_share": 0.9}) == (None, None)
    assert T.source_take({"real": 2.0, "nulls": [0.0] * 4, "active_share": 0.9})[0] == 0.0          # capped at 0 dB
    blow = T.source_take({"real": -0.53, "nulls": [-0.011, -256.7, -0.0065, 0.0], "active_share": 0.9})
    assert blow[1].startswith("blow-up")                     # Adam Buckley, AcousticGtr3 read in ElecGtr1 (1st pass)
    assert T.source_take({"real": 0.0, "nulls": [0.0, 1.2e-3, 0.0, 0.0], "active_share": 0.9})[1].startswith(
        "rolled readings spread")
    assert T.source_take({"real": 0.0, "nulls": [0.0] * 4, "active_share": 0.3})[1].startswith("source plays on 30%")
    r = {"silent": False, "sources": {"01_Kick.wav": _raw(-33.0)["sources"]["01_Kick.wav"],
                                      "43_LeadVox1.wav": {"real": 0.0, "nulls": [0.0] * 4, "active_share": 0.2}}}
    assert T.amp_status(r) == "unmeasurable"                # any unmeasurable source fails the track
    assert T.amp_reason(r).startswith("unmeasurable: 43_LeadVox1.wav source plays on 20%")


def test_amp_bleed_sums_takes_over_the_floor_on_a6s_line():
    assert T.AMP_BLEED_DB == -30.0
    total = T.amp_bleed_total({"kick": -35.0, "oh": -35.0, "bass": -45.0, "snare": None})
    assert total == pytest.approx(-31.99, abs=0.01)
    assert T.amp_bleed_total({"kick": -41.0, "bass": None}) is None                  # every take under -40 dB: none
    assert T.amp_status(_raw(-30.0)) == "fail" and T.amp_status(_raw(-30.1)) == "pass"
    assert T.amp_status(_raw(None)) == "pass" and T.amp_status({"silent": True}) == "silent"
    assert T.amp_status(None) == "not measured"
    assert T.amp_reason(_raw(-24.0)) == "bleed -24.0 dB, worst 01_Kick.wav -24.0"


def test_an_amp_only_active_guitar_is_added_to_the_backing(monkeypatch, tmp_path):
    blocked = {"s/31_ElecGtr3DI.wav@55.0": [{"part": "elecgtr1", "activity": 1.0, "why": "no DI",
                                             "amp_tracks": ["25_ElecGtr1.wav"]},
                                            {"part": "acousticgtr1", "activity": 0.6, "why": "no DI",
                                             "amp_tracks": ["22_AcousticGtr1.wav"]}],
               "s/31_ElecGtr3DI.wav@15.0": []}
    monkeypatch.setattr(T, "section_blocked", lambda ctx, sid, *a, **k: blocked[sid])
    _bleed_file(tmp_path, "/sess", {"25_ElecGtr1.wav": _raw(None), "22_AcousticGtr1.wav": _raw(-36.5)})
    rows = [{"i": 1, "section": "s/31_ElecGtr3DI.wav@55.0", "band": "X"},
            {"i": 2, "section": "s/31_ElecGtr3DI.wav@15.0", "band": "X"}]
    scan = {sid: {"source": {"kind": "amp"}, "tracks": {}, "removed": []} for sid in blocked}
    kept, left, amp_of = T.apply_rule1(_rule1_ctx("/sess"), tmp_path, rows, set(), {}, set(), {}, scan)
    assert [r["i"] for r in kept] == [1, 2] and left == []
    assert amp_of["s/31_ElecGtr3DI.wav@55.0"][0] == {"part": "elecgtr1", "track": "25_ElecGtr1.wav", "bleed_db": None}
    assert amp_of["s/31_ElecGtr3DI.wav@55.0"][1]["track"] == "22_AcousticGtr1.wav"    # acoustics follow the same path
    assert amp_of["s/31_ElecGtr3DI.wav@55.0"][1]["bleed_db"] == pytest.approx(-36.5)
    x = {"stems": {"v": ["16_Overheads.wav", "43_LeadVox1.wav"], "n": ["16_Overheads.wav"]},
         "amp_tracks": amp_of["s/31_ElecGtr3DI.wav@55.0"]}
    assert T.backing_tracks(x, False) == ["16_Overheads.wav", "25_ElecGtr1.wav", "22_AcousticGtr1.wav"]
    assert T.backing_tracks(x, True)[:2] == ["16_Overheads.wav", "43_LeadVox1.wav"]
    assert T.backing_tracks({"stems": {"v": [], "n": ["a.wav"]}}, False) == ["a.wav"]       # older recipes


def test_the_backing_sums_amp_tracks_with_the_stems_as_recorded(tmp_path):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    import types

    from learn import pretrain_set as PS

    rng = np.random.default_rng(3)
    n = 48000 * 30
    sf.write(str(tmp_path / "16_Overheads.wav"), (0.1 * rng.standard_normal(n)).astype(np.float32), 48000)
    sf.write(str(tmp_path / "25_ElecGtr1.wav"), (0.2 * rng.standard_normal((n, 2))).astype(np.float32), 48000)
    ctx = types.SimpleNamespace(sections={"s/31_ElecGtr3DI.wav@5.0": {"di": "s/31_ElecGtr3DI.wav", "start_s": 5.0}},
                                inv={"s/31_ElecGtr3DI.wav": {"session_dir": str(tmp_path)}})
    x = {"stems": {"v": ["16_Overheads.wav"], "n": ["16_Overheads.wav"]},
         "amp_tracks": [{"part": "elecgtr1", "track": "25_ElecGtr1.wav", "bleed_db": None}]}
    b = T.Stems(ctx).get("s/31_ElecGtr3DI.wav@5.0", T.backing_tracks(x, False))
    trim = int(PS.TRIM_S * PS.SR)
    want = (PS.section_audio(tmp_path / "16_Overheads.wav", 5.0) * T.pan_fold(0.0)      # mono: a centred source
            + PS.section_audio(tmp_path / "25_ElecGtr1.wav", 5.0))[trim:]           # stereo: folded on loading
    assert np.allclose(b, want)


def test_a_failing_or_unmeasurable_amp_track_leaves_the_example_out(monkeypatch, tmp_path, capsys):
    b = {"part": "elecgtr02", "activity": 0.9, "why": "no DI", "amp_tracks": ["18_ElecGtr02.wav"]}
    use, bad = T.resolve_blocked([b], {"18_ElecGtr02.wav": _raw(-24.0)})
    assert use == [] and bad[0]["amp_why"] == "amp track bleed at or above -30 dB"
    assert bad[0]["amp"] == [{"track": "18_ElecGtr02.wav", "status": "fail", "bleed_db": pytest.approx(-24.0),
                              "reason": "bleed -24.0 dB, worst 01_Kick.wav -24.0"}]
    two = {**b, "amp_tracks": ["11_ElecGtr2Mic1.wav", "12_ElecGtr2Mic2.wav"]}            # each track must pass
    assert T.resolve_blocked([two], {"11_ElecGtr2Mic1.wav": _raw(-40.0), "12_ElecGtr2Mic2.wav": _raw(-29.0)})[0] == []
    assert T.resolve_blocked([b], {"18_ElecGtr02.wav": _raw(-40.0, share=0.2)})[1][0]["amp_why"] == (
        "amp track bleed unmeasurable")
    assert T.resolve_blocked([{**b, "amp_tracks": []}], {})[1][0]["amp_why"] == "no amp track"
    assert T.resolve_blocked([b], {"18_ElecGtr02.wav": {"silent": True}})[1][0]["amp_why"] == "amp track silent"
    with pytest.raises(SystemExit):                                                   # never guessed: amp-bleed first
        T.resolve_blocked([b], {})
    blocked = {"s/31_ElecGtr3DI.wav@55.0": [b], "s/31_ElecGtr3DI.wav@15.0": []}
    monkeypatch.setattr(T, "section_blocked", lambda ctx, sid, *a, **k: blocked[sid])
    _bleed_file(tmp_path, "/sess", {"18_ElecGtr02.wav": _raw(-24.0)})
    rows = [{"i": 1, "section": "s/31_ElecGtr3DI.wav@55.0", "band": "X"},
            {"i": 2, "section": "s/31_ElecGtr3DI.wav@55.0", "band": "X"},
            {"i": 3, "section": "s/31_ElecGtr3DI.wav@15.0", "band": "X"}]
    kept, left, amp_of = T.apply_rule1(_rule1_ctx("/sess"), tmp_path, rows, set(), {}, set(), {}, {})
    assert [r["i"] for r in kept] == [3] and amp_of == {}
    assert left[0]["reason"] == T.LEFT_OUT_NO_AMP == "an active guitar has no usable amp track"
    assert left[0]["examples"] == 2 and left[0]["guitars"][0]["amp"][0]["bleed_db"] == pytest.approx(-24.0)
    T.print_left_out(left, T.LEFT_OUT_NO_AMP)
    out = capsys.readouterr().out
    assert "left out: 2 examples in 1 sections (an active guitar has no usable amp track)" in out
    assert "amp track bleed at or above -30 dB 2" in out
    _bleed_file(tmp_path, "/sess", {})                                               # a missing reading refuses
    with pytest.raises(SystemExit):
        T.apply_rule1(_rule1_ctx("/sess"), tmp_path, rows, set(), {}, set(), {}, {})


def test_an_amp_track_the_cleaning_scan_removed_never_comes_back(monkeypatch, tmp_path):
    amp = [{"part": "elecgtr2dt", "track": "28_ElecGtr2DT.wav", "bleed_db": None}]
    row = {"source": {"kind": "amp"}, "removed": [],
           "tracks": {"28_ElecGtr2DT.wav": {"same_part": True, "power_db": {"A": -9.0, "B": -12.0},
                                            "take_amp_db": None},
                      "01_Kick.wav": {"same_part": False, "power_db": {"A": -9.0}, "take_amp_db": -45.0}}}
    assert T.cleaning_clash(amp, row) == ["28_ElecGtr2DT.wav"]
    assert T.cleaning_clash(amp, {"source": {"kind": "amp"}, "removed": [], "tracks": {}}) == []
    assert T.cleaning_clash(amp, None) == ["no cleaning scan row"]
    assert T.cleaning_clash([], None) == []
    blocked = {"s/31_ElecGtr3DI.wav@55.0": [{"part": "elecgtr2dt", "activity": 0.9, "why": "window excluded",
                                             "amp_tracks": ["28_ElecGtr2DT.wav"]}]}
    monkeypatch.setattr(T, "section_blocked", lambda ctx, sid, *a, **k: blocked[sid])
    _bleed_file(tmp_path, "/sess", {"28_ElecGtr2DT.wav": _raw(None)})
    rows = [{"i": 1, "section": "s/31_ElecGtr3DI.wav@55.0", "band": "X"}]
    kept, left, amp_of = T.apply_rule1(_rule1_ctx("/sess", ("s/31_ElecGtr3DI.wav@55.0",)), tmp_path, rows, set(), {},
                                       set(), {}, {"s/31_ElecGtr3DI.wav@55.0": row})
    assert kept == [] and amp_of == {} and left[0]["reason"] == T.LEFT_OUT_OWN_TAKE


def test_more_active_guitars_than_the_cap_leave_the_example_out(monkeypatch):
    act = {f"s/{k}_ElecGtr{k}DI.wav": 0.5 for k in range(1, 7)}
    act["s/6_ElecGtr6DI.wav"] = 0.05                                                 # resting: not counted
    assert T.over_cap(sorted(act), act) == ["s/5_ElecGtr5DI.wav"]                   # 5 active, cap 4: the quietest
    assert T.over_cap(sorted(act)[:4], act) == []
    cands = {"a@5.0": (sorted(act), act), "b@5.0": (sorted(act)[:3], act)}
    monkeypatch.setattr(T, "section_candidates", lambda ctx, sid, *a, **k: cands[sid])
    rows = [{"i": 1, "section": "a@5.0", "band": "X"}, {"i": 2, "section": "a@5.0", "band": "X"},
            {"i": 3, "section": "b@5.0", "band": "X"}]
    kept, left = T.apply_cap(None, rows, set(), {}, set(), {})
    assert [r["i"] for r in kept] == [3]
    assert left == [{"section": "a@5.0", "band": "X", "reason": T.LEFT_OUT_CAP, "examples": 2,
                     "guitars": [{"part": "5_ElecGtr5DI.wav", "why": T.LEFT_OUT_CAP}]}]
    assert T.LEFT_OUT_CAP == "more active guitars than the cap"


def test_t2_plan_records_left_out_examples_once_with_their_reasons(monkeypatch, tmp_path, capsys):
    import types

    from learn import data_cleaning as DC
    from learn import direct_stems as DS

    sids = [f"s/31_ElecGtr3DI.wav@{k}.0" for k in range(10, 80, 10)]                # 7 sections, 2 bands
    band = {sid: ("A" if k < 4 else "B") for k, sid in enumerate(sids)}
    rows = [{"i": 10 * k + j, "section": sid, "band": band[sid]} for k, sid in enumerate(sids) for j in range(3)]
    ctx = _rule1_ctx("/sess", sids)
    ctx.pool = rows
    fail, amp_ok, clash, cap = sids[0], sids[1], sids[2], sids[4]
    blocked = {sid: [] for sid in sids}
    blocked[fail] = [{"part": "elecgtr1", "activity": 1.0, "why": "no DI", "amp_tracks": ["25_ElecGtr1.wav"]}]
    blocked[amp_ok] = [{"part": "elecgtr5", "activity": 1.0, "why": "no DI", "amp_tracks": ["34_ElecGtr5.wav"]}]
    blocked[clash] = [{"part": "elecgtr2dt", "activity": 1.0, "why": "no DI", "amp_tracks": ["28_ElecGtr2DT.wav"]}]
    _bleed_file(tmp_path, "/sess", {"25_ElecGtr1.wav": _raw(-22.0), "34_ElecGtr5.wav": _raw(-36.0),
                                    "28_ElecGtr2DT.wav": _raw(None)})
    scan = {sid: {"source": {"kind": "amp"}, "removed": [], "tracks": {}} for sid in sids}
    scan[clash]["removed"] = ["28_ElecGtr2DT.wav"]
    act = {f"d{k}": 0.5 for k in range(5)}
    monkeypatch.setattr(T, "load_lists", lambda root, smoke=False: {"dis": {}, "unusable_sections": [], "stems": {}})
    monkeypatch.setattr(DS, "Ctx", lambda quiet=True: ctx)
    monkeypatch.setattr(DC, "scan_rows", lambda root: scan)
    monkeypatch.setattr(T, "stage_rows", lambda ctx, tr, stage, limit=0: (list(rows), []))
    monkeypatch.setattr(T, "section_blocked", lambda ctx, sid, *a, **k: blocked[sid])
    monkeypatch.setattr(T, "section_candidates",
                        lambda ctx, sid, *a, **k: (sorted(act), act) if sid == cap else ([], {}))
    monkeypatch.setattr(T, "example_recipe", lambda ctx, r, *a: {
        "i": r["i"], "section": r["section"], "band": r["band"], "di": "s/31_ElecGtr3DI.wav", "others": [],
        "stems": {"v": ["16_Overheads.wav"], "n": ["16_Overheads.wav"]}, "amp_tracks": [dict(x) for x in a[5]]})
    monkeypatch.setattr(T, "N_PILOT", 3)
    T.main(["plan", "--stage", "t2", "--smoke", "--out", str(tmp_path)])
    plan = T._load(T.plan_path(tmp_path, "t2"))
    gone = {fail: T.LEFT_OUT_NO_AMP, clash: T.LEFT_OUT_OWN_TAKE, cap: T.LEFT_OUT_CAP}
    assert {x["section"]: x["reason"] for x in plan["left_out"]} == gone                 # records, not rows
    assert all(x["examples"] == 3 for x in plan["left_out"]) and plan["left_out_examples"] == 9
    used = {x["section"] for x in plan["examples"]}
    assert not used & set(gone) and not {r["section"] for r in rows if r["i"] in plan["pilot"]} & set(gone)
    for x in plan["examples"]:
        assert bool(x["amp_tracks"]) == (x["section"] == amp_ok)
    out = capsys.readouterr().out
    for rsn in gone.values():
        assert out.count(f"sections ({rsn})") == 1                                     # printed once


def test_measure_amp_bleed_reads_injected_bleed_back_and_ignores_a_unison_guitar(tmp_path):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    pytest.importorskip("scipy")
    from scipy.signal import resample_poly

    from learn import data_cleaning as DC

    sr, n = 48000, 48000 * 40
    rng = np.random.default_rng(11)
    env = np.repeat(rng.random(n // 4800) < 0.7, 4800)[:n].astype(np.float32)   # a part that plays most of the time
    oh = (0.1 * rng.standard_normal(n)).astype(np.float32)                      # a non-guitar source, always on
    leak = np.concatenate([np.zeros(48, np.float32), oh[:-48]])                 # a 1 ms path into the mic
    files = {"06_Overheads.wav": oh}
    for k, lev in enumerate((-25.0, -30.0, -33.0)):                            # a known copy at each level
        g = (0.3 * rng.standard_normal(n) * env).astype(np.float32)
        y24, l24 = (np.asarray(resample_poly(v, 1, 2), np.float32) for v in (g, leak))   # the estimator's 24 kHz
        idx, _ = DC.band_bins()
        Y, L = DC.stft(y24)[idx], DC.stft(l24)[idx]
        cnt = DC.counted_frames(Y)
        gain = math.sqrt(10 ** (lev / 10) * np.sum(np.abs(Y[:, cnt]) ** 2) / np.sum(np.abs(L[:, cnt]) ** 2))
        files[f"2{k}_ElecGtr{k + 1}.wav"] = g + gain * leak
    g5 = (0.3 * rng.standard_normal(n) * env[::-1]).astype(np.float32)
    files["25_ElecGtr5.wav"] = g5
    files["26_ElecGtr5DT.wav"] = 0.8 * np.concatenate([np.zeros(48, np.float32), g5[:-48]])   # locked double
    files["27_ElecGtr6.wav"] = np.zeros(n, np.float32)
    for name, x in files.items():
        sf.write(str(tmp_path / name), np.asarray(x, np.float32), sr)
    assert T.bleed_sources(sorted(files)) == ["06_Overheads.wav"]               # never another guitar track
    tracks = ["20_ElecGtr1.wav", "21_ElecGtr2.wav", "22_ElecGtr3.wav", "25_ElecGtr5.wav", "27_ElecGtr6.wav"]
    r = T.measure_amp_bleed(tmp_path, tracks, log=lambda *a: None)
    got = {t: T.track_bleed(r[t])["bleed_db"] for t in tracks[:3]}
    assert got["20_ElecGtr1.wav"] == pytest.approx(-25.0, abs=1.5)              # read back in the check's own roles
    assert got["21_ElecGtr2.wav"] == pytest.approx(-30.0, abs=1.5)
    assert got["22_ElecGtr3.wav"] == pytest.approx(-33.0, abs=2.0)
    assert [T.amp_status(r[t]) for t in tracks[:3]] == ["fail", "fail", "pass"]
    assert T.amp_status(r["25_ElecGtr5.wav"]) == "pass"                         # its unison double is not bleed
    assert set(r["25_ElecGtr5.wav"]["sources"]) == {"06_Overheads.wav"}
    assert T.amp_status(r["27_ElecGtr6.wav"]) == "silent"


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
    # Renesans: the inventory lists GTR 2's amp under GTR 1's DI; another part number stays its own part
    ren = ["GTR 1 Amp_M81.wav", "GTR 1 DI_TDP-1.wav", "GTR 2 Amp_M81.wav"]
    k = T.part_keys(ren, {"GTR 1 DI_TDP-1.wav": ["GTR 1 Amp_M81.wav", "GTR 2 Amp_M81.wav"]})
    assert k["GTR 1 Amp_M81.wav"] == k["GTR 1 DI_TDP-1.wav"] == "gtr1" and k["GTR 2 Amp_M81.wav"] == "gtr2"
    assert T.part_keys(["15_ElecGtrFar.wav", "16_ElecGtr1DI.wav"],
                       {"16_ElecGtr1DI.wav": ["15_ElecGtrFar.wav"]})["15_ElecGtrFar.wav"] == "elecgtr1"   # no number
    assert T.part_number("elecgtr02dt") == 2 and T.part_number("elecgtrfar") is None


# --- T2's additions (2026-10-25): the stem read, diagnostics (a) and (b), SES-ALL, the report fix ------------------

def _stem_per(shift):
    sec = {i: f"{b}{i % 3}" for i, b in zip(range(24), "ABCD" * 6)}
    band = {i: sec[i][0] for i in sec}
    syn = {i: 3.0 + shift + 0.1 * (i % 5) for i in sec}
    ses = {i: 3.0 + 0.1 * ((i + 2) % 5) for i in sec}
    cont = {"SYN": {i: 0.02 for i in sec}, "SES": {i: 0.03 for i in sec}}
    return {"SYN": syn, "SES": ses}, cont, band, sec


def test_the_t2_stem_read_is_section_clustered_and_only_a_ceiling_check():
    per, cont, band, sec = _stem_per(2.0)
    s = T.stem_read_summary(per, cont, band, sec, set(sec))
    assert len(s["bands"]) == 4 >= T.MIN_BANDS                        # 4 bands: still section-clustered (declared)
    assert s["primary"] == T.STEM_READ_PRIMARY and s["primary"].startswith("section-clustered")
    assert s["SYN - SES mel SNR (primary, section-clustered)"][3] == s["sections"] == 12
    assert s["SYN - SES mel SNR (band-clustered, beside)"][3] == 4
    assert s["per arm"]["SES"]["share below 0 dB"] == 0.0 and s["per arm"]["SYN"]["median"] is not None
    assert s["per arm"]["SYN"]["contamination"]["mean"] == pytest.approx(0.02)
    assert s["SYN - SES contamination (section-clustered)"][0] == pytest.approx(-0.01)
    assert s["reading"].startswith("SYN's stems read cleaner") and "ceiling" in s["reading"]
    assert T.stem_reading((0.1, -1.0, 1.2, 12)).startswith("no difference shown: SYN is not shown to be easier")
    for shift in (-2.0, 0.0):
        per, cont, band, sec = _stem_per(shift)
        assert "ceiling" in T.stem_read_summary(per, cont, band, sec, set(sec))["reading"]
    for iv in ((2.0, 1.0, 3.0, 12), (0.1, -1.0, 1.2, 12), (-2.0, -3.0, -1.0, 12)):
        r = T.stem_reading(iv)
        assert "ceiling" in r and ("not a realism certificate" in r or "not a realism verdict" in r)
        assert not re.search(r"\b(is|are) realistic\b|realism (is )?(shown|established|confirmed)", r)
    assert T.stem_reading(None) == "incomplete"


def test_playing_guitars_are_counted_as_rule_1_counts_and_split_as_declared():
    parts = {"elecgtr1": ["25_ElecGtr1.wav"], "elecgtr2": ["26_ElecGtr2.wav", "27_ElecGtr2DI.wav"],
             "elecgtr4": ["33_ElecGtr4DI.wav"], "acousticgtr1": ["22_AcousticGtr1.wav"]}
    act = {"25_ElecGtr1.wav": 0.5, "26_ElecGtr2.wav": 0.02, "27_ElecGtr2DI.wav": 0.4, "33_ElecGtr4DI.wav": 0.05,
           "22_AcousticGtr1.wav": 0.1}
    assert T.playing_parts(parts, act) == ["acousticgtr1", "elecgtr1", "elecgtr2"]   # any track; DI-only counts
    assert T.playing_count(parts, act) == 4 and T.playing_count({}, {}) == 1          # the target's part included
    assert T.DENSE_MIN == 5 and T.density(5) == "dense" and T.density(4) == "sparse"


def test_density_groups_compare_kept_with_left_out_candidates():
    cand = ([{"i": i, "section": "a@0", "band": "X"} for i in range(3)]
            + [{"i": 10 + i, "section": "b@0", "band": "Y"} for i in range(2)]
            + [{"i": 20, "section": "c@0", "band": "Y"}])
    left = [{"section": "b@0", "reason": T.LEFT_OUT_NO_AMP, "examples": 2},
            {"section": "c@0", "reason": T.LEFT_OUT_CAP, "examples": 1}]
    g = T.density_groups(cand, left, {"a@0": 2, "b@0": 4, "c@0": 7})
    assert g["kept"]["examples"] == 3 and g["kept"]["by count"] == {2: {"sections": 1, "examples": 3}}
    assert g[f"left out: {T.LEFT_OUT_NO_AMP}"]["mean"] == 4
    assert g["left out (all)"]["examples"] == 3 and g["left out (all)"]["mean"] == pytest.approx(5.0)
    assert g["left out (all)"]["share at least"] == {3: 1.0, 4: 1.0, 5: pytest.approx(1 / 3)}
    assert g["kept"]["share at least"][3] == 0.0
    assert set(g["by band"]) == {"kept | X", "left out | Y"}


def _cand():
    rows = []
    for b, n_sec in (("A", 6), ("B", 4), ("C", 3)):
        for s in range(n_sec):
            rows += [{"i": len(rows) + k, "section": f"{b}{s}@0", "band": b} for k in range(10)]
    return rows


def test_ses_all_draws_from_every_candidate_outside_early_stopping():
    cand = _cand()
    es_sections = ["A0@0", "B0@0"]
    d = T.ses_all_draw(cand, es_sections, n=60)
    assert len(d) == 60 and d == T.ses_all_draw(cand, es_sections, n=60)          # seeded
    assert not {r["section"] for r in d} & set(es_sections)
    assert {b: sum(1 for r in d if r["band"] == b) for b in "ABC"} == {"A": 27, "B": 17, "C": 16}   # by band
    assert T.SES_ALL_SEED == 20261104 and T.SES_ALL_SEED not in (T.PILOT_SEED, T.ES_SEED, T.EGGY_SEED, T.OTHER_SEED)
    pool = {r["i"] for r in cand}
    T.ses_all_guard(d, [0, 1], es_sections, {"Z"}, pool)
    with pytest.raises(SystemExit, match="early-stopping"):
        T.ses_all_guard(d + [cand[0]], [0], es_sections, {"Z"}, pool)
    with pytest.raises(SystemExit, match="bands of V-real"):
        T.ses_all_guard(d, [], es_sections, {"C"}, pool)
    with pytest.raises(SystemExit, match="outside the trusted pool"):
        T.ses_all_guard(d, [], es_sections, set(), pool - {d[0]["i"]})


def test_ses_all_trains_on_its_draw_and_early_stops_on_ses_set(tmp_path):
    import types

    plan = {"pilot": [1, 2], "es": [3, 4], "es_sections": ["s3"], "lists_sha256": "x", "examples": [],
            "syn_e": {"refused": "no Eggy DI is trusted"}}
    files = {i: (f"m{i}", f"s{i}") for i in range(1, 8)}
    assert T.t2_arms(tmp_path, plan) == ("SES", "SYN")
    with pytest.raises(SystemExit, match="plan-ses-all"):
        T.load_ses_all(tmp_path, plan)
    sa = {"train": [2, 5, 6], "t2_plan": T.plan_key(plan)}
    T._save(T.ses_all_path(tmp_path), sa)
    assert T.t2_arms(tmp_path, plan) == ("SES", "SYN", T.SES_ALL) and T.load_ses_all(tmp_path, plan) == sa
    with pytest.raises(SystemExit, match="another T2 plan"):
        T.load_ses_all(tmp_path, {**plan, "es": [3]})
    f = T.arm_files(tmp_path, plan, T.SES_ALL, files, sa)
    assert sorted(f) == [2, 3, 4, 5, 6] and f[5] == ("m5", "s5")
    ctx = types.SimpleNamespace(pool=[{"i": i, "band": "X"} for i in range(1, 8)])
    tr, es = T.arm_rows(ctx, plan, T.SES_ALL, f, refused={2, 4}, ses_all=sa)
    assert [r["i"] for r in tr] == [2, 5, 6]                       # SYN's refusals do not touch SES-ALL's training
    assert [r["i"] for r in es] == [3] and es[0]["early_stop"]     # the shared early-stopping refusals do


def test_ses_all_joins_the_contrasts_and_the_primary_does_not_wait_for_it():
    con = T.t2_contrasts(("SES", "SYN", T.CONST_ARM, T.SES_ALL))
    assert list(con)[0] == "SYN - SES"
    assert con["SES-ALL - SES"] == (T.SES_ALL, "SES") and con["SES-ALL - S"] == (T.SES_ALL, "S")
    assert "SES-ALL - SES" not in T.t2_contrasts(("SES", "SYN", T.CONST_ARM))
    arms = ("SES", "SYN", T.CONST_ARM, T.SES_ALL)
    assert T.primary_arms(arms) == ("SES", "SYN", T.CONST_ARM)
    units = [{"slug": "p", "amp": "pr12", "d": {"SES": 1.0, "SYN": 1.0, T.CONST_ARM: 1.0, T.SES_ALL: None}}]
    groups = {("p", "pr12"): {"status": "done"}}
    assert T.report_gaps(units, T.primary_arms(arms), groups, {"p"}, {"p"}, {}) == []
    assert T.report_gaps(units, (T.SES_ALL,), groups, {"p"}, {"p"}, {}) == ["1 directions have no SES-ALL value"]


def test_an_added_arm_is_read_from_its_own_record():
    g = {"status": "done", "judge": {"SES|A": {"B": 0.5}}}
    added = {"status": "done", "judge": {"SES-ALL|A": {"B": 0.4}}}
    assert T.group_value(g, added, "SES", "A", "B") == 0.5
    assert T.group_value(g, added, "SES-ALL", "A", "B") == 0.4
    assert T.group_value(g, {}, "SES-ALL", "A", "B") is None
    assert T.group_value({"status": "running"}, added, "SES-ALL", "A", "B") is None
    od = T.pathlib.Path("/x/vreal")
    assert T.added_group_path(od, "SES-ALL", "p", "pr12") == od / "groups-added" / "SES-ALL" / "p|pr12.json"


def test_vreal_playing_reads_the_crops_session(monkeypatch, tmp_path):
    from learn import arm_a_mega53 as A

    sess = tmp_path / "set3" / "Band_Song_Full"                    # set 3: base/<session>/, names carry the folder
    sess.mkdir(parents=True)
    names = ["01_Kick.wav", "10_ElecGtr1.wav", "11_ElecGtr1DI.wav", "12_ElecGtr2.wav", "13_ElecGtr2DI.wav",
             "14_ElecGtr3DI.wav", "15_ElecGtr4.wav", "16_ElecGtr4DI.wav"]
    for n in names:
        (sess / n).write_bytes(b"")
    rec = {"excerpt_start_s": 20.0, "excerpt_duration_s": 10.0, "part": "ElecGtr1",
           "removed_own_amp_tracks": ["Band_Song_Full/10_ElecGtr1.wav"]}
    cpart = {"part": "ElecGtr1", "di": "Band_Song_Full/11_ElecGtr1DI.wav"}
    mix = [f"Band_Song_Full/{n}" for n in ("01_Kick.wav", "12_ElecGtr2.wav", "15_ElecGtr4.wav")]
    monkeypatch.setattr(A, "f_part", lambda slug: {"crop": tmp_path / "crop"})
    monkeypatch.setattr(T.V, "crop_session", lambda crop: (rec, tmp_path / "set3", cpart, [], mix))
    act = {"12_ElecGtr2.wav": 0.9, "13_ElecGtr2DI.wav": 0.9, "14_ElecGtr3DI.wav": 0.5, "15_ElecGtr4.wav": 0.0,
           "16_ElecGtr4DI.wav": 0.0, "10_ElecGtr1.wav": 1.0, "11_ElecGtr1DI.wav": 1.0}
    seen = []

    def fake(path, start, files=None, dur_s=None):
        seen.append((path.parent, start, dur_s))
        return act[path.name]

    monkeypatch.setattr(T, "section_activity", fake)
    d = T.vreal_playing("p")
    assert d["playing_parts"] == ["elecgtr2", "elecgtr3"] and d["playing"] == 3 and d["density"] == "sparse"
    assert d["in_mix"] == {"elecgtr2": True, "elecgtr3": False, "elecgtr4": True}   # a DI-only part counts, as in plan
    assert {s for s in seen} == {(sess, 20.0, 10.0)}


def test_the_report_labels_t1s_old_read_superseded(monkeypatch, tmp_path, capsys):
    pytest.importorskip("numpy")
    from learn import arm_a_mega53 as A
    from learn import direct_stems as DS
    from learn import local_objective_1c as C
    from learn import perfect_sep_arm as P

    T._save(tmp_path / "t1" / "read.json", {"results": {"K - V_sep mel SNR (primary)": [1.62, -0.31, 3.56, 26]}})
    T._save(tmp_path / "t2" / "stem-read.json", {"results": {"reading": "no difference shown: ... ceiling ..."}})
    monkeypatch.setattr(T.V, "require_real", lambda args: None)
    monkeypatch.setattr(T.V, "out_root", lambda args: tmp_path)
    monkeypatch.setattr(T, "load_lists", lambda root, smoke=False: {"v_real": ["p"]})
    monkeypatch.setattr(P, "build_units", lambda: [{"slug": "p", "amp": "pr12", "search": "A", "held": "B",
                                                    "band": "X", "d": {"S": 1.0}}])
    monkeypatch.setattr(C, "load_bleed_table", lambda: {})
    monkeypatch.setattr(A, "row_filter", lambda row, stage, bt, snr: (lambda u: True))
    monkeypatch.setattr(DS, "step4_contrast", lambda *a, **k: {"rows": {}})
    monkeypatch.setattr(T, "vreal_playing", lambda s, files=None: {"playing": 2, "density": "sparse"})
    T.main(["report"])
    rep = T._load(tmp_path / "t2" / "report.json")
    assert "t1" not in rep and "superseded" in rep["t1 (superseded)"]["note"]
    assert rep["stem_read"]["reading"].startswith("no difference shown")
    assert rep["density"]["parts"] == {"p": {"playing": 2, "density": "sparse"}}
    out = capsys.readouterr().out
    assert "T1's 812-example read: superseded" in out and "T2-side stem read" in out


def test_the_new_commands_render_nothing_and_dry_is_for_plan_ses_all():
    from learn import local_objective as LO

    for cmd in ("t2-stem-read", "t2-density", "plan-ses-all", "plan-ses-all --dry",
                "train --arm SES-ALL --seed 20261042"):
        assert not any(re.search(p, f"python -m learn.trusted_data {cmd}") for p in LO.RENDERS)
    with pytest.raises(SystemExit, match="--dry is for plan-ses-all"):
        T.main(["report", "--dry"])


# --- the review of #292 (2026-10-25) --------------------------------------------------------------------------------

def test_vreal_render_adds_an_arm_on_its_own_and_never_into_an_unfinished_group():
    dirs = ["A", "B"]
    arms = ("SES", "SYN", T.CONST_ARM, T.SES_ALL)
    full = {"status": "done", "judge": {f"{a}|{d}": {} for a in ("SES", "SYN", T.CONST_ARM) for d in dirs}}
    assert T.render_todo({}, {}, ("SES", "SYN", T.CONST_ARM), dirs) is None          # T2's own first render
    with pytest.raises(SystemExit, match="not done by T2's chain"):
        T.render_todo({"status": "running", "slug": "p", "amp": "pr12"}, {}, arms, dirs)
    assert T.render_todo(full, {}, arms, dirs) == [T.SES_ALL]
    done = {"status": "done", "judge": {f"{T.SES_ALL}|{d}": {} for d in dirs}}
    assert T.render_todo(full, {T.SES_ALL: done}, arms, dirs) == []
    assert T.render_todo(full, {T.SES_ALL: {"status": "running"}}, arms, dirs) == [T.SES_ALL]
    assert T.render_todo(full, {}, ("SES", "SYN", T.CONST_ARM), dirs) == []


def test_fit_keeps_an_arm_fitted_on_the_same_models():
    runs = [{"seed": 20261042, "model_sha256": "a"}, {"seed": 20261043, "model_sha256": "b"}]
    assert T.fit_kept({"models": {"20261042": "a", "20261043": "b"}}, runs)
    assert not T.fit_kept({"models": {"20261042": "a", "20261043": "c"}}, runs)      # retrained: refit
    assert not T.fit_kept(None, runs) and not T.fit_kept({"models": {}}, runs)


def test_vreal_predict_keeps_stored_arms_and_refuses_other_models_or_directions():
    keys = {"p|pr12|A", "p|pr12|B"}
    preds = {a: {k: {"settings": {}} for k in keys} for a in ("SES", "SYN", T.CONST_ARM)}
    prev = {"smoke": False, "predictions": preds}                                    # T2's own: no models recorded
    assert T.kept_predictions(prev, keys, False, {"SES": {"1": "x"}}) == preds
    assert T.kept_predictions({}, keys, False, {}) == {} and T.kept_predictions(prev, keys, True, {}) == {}
    with pytest.raises(SystemExit, match="other V-real directions"):
        T.kept_predictions(prev, keys | {"q|pr12|A"}, False, {})
    added = {**prev, "predictions": {**preds, T.SES_ALL: preds["SES"]}, "models": {T.SES_ALL: {"1": "m"}}}
    assert T.SES_ALL in T.kept_predictions(added, keys, False, {T.SES_ALL: {"1": "m"}})
    with pytest.raises(SystemExit, match="other models"):
        T.kept_predictions(added, keys, False, {T.SES_ALL: {"1": "retrained"}})


def test_a_failing_density_diagnostic_is_recorded_not_fatal(monkeypatch, tmp_path, capsys):
    pytest.importorskip("numpy")
    from learn import arm_a_mega53 as A
    from learn import direct_stems as DS
    from learn import local_objective_1c as C
    from learn import perfect_sep_arm as P

    monkeypatch.setattr(T.V, "require_real", lambda args: None)
    monkeypatch.setattr(T.V, "out_root", lambda args: tmp_path)
    monkeypatch.setattr(T, "load_lists", lambda root, smoke=False: {"v_real": ["p"]})
    monkeypatch.setattr(P, "build_units", lambda: [{"slug": "p", "amp": "pr12", "search": "A", "held": "B",
                                                    "band": "X", "d": {"S": 1.0}}])
    monkeypatch.setattr(C, "load_bleed_table", lambda: {})
    monkeypatch.setattr(A, "row_filter", lambda row, stage, bt, snr: (lambda u: True))
    monkeypatch.setattr(DS, "step4_contrast", lambda *a, **k: {"rows": {}})

    def boom(s, files=None):
        raise SystemExit("p: no session files")

    monkeypatch.setattr(T, "vreal_playing", boom)
    T.main(["report"])
    rep = T._load(tmp_path / "t2" / "report.json")
    assert rep["density"]["error"] == "SystemExit: p: no session files" and rep["density"]["parts"] == {}
    assert "diagnostic (a) failed" in capsys.readouterr().out
