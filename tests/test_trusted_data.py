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


def test_stems_fold_like_a_centred_guitar():
    np = pytest.importorskip("numpy")
    pytest.importorskip("pyloudnorm")
    t = np.arange(48000 * 3) / 48000
    y = 0.1 * np.sin(2 * np.pi * 220 * t)
    other = 0.1 * np.sin(2 * np.pi * 330 * t) * T.pan_fold(0.0)    # a centred other guitar, folded
    stem = 0.1 * np.sin(2 * np.pi * 330 * t)                        # the same source as a (centred) stem, raw
    from learn import direct_stems as DS

    x = {"i": 1, "draw": {"ratio_db": -6.0, "leak_db": -99.0, "target_lufs": -20.0, "mastered": DS.master_draw(1)[0]}}
    _, _, lb_other = T.self_built_mix(y, other, np.zeros_like(y), x)
    _, _, lb_stem = T.self_built_mix(y, np.zeros_like(y), stem, x)
    assert abs(lb_other - lb_stem) < 0.05                          # both centred sources fold alike


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
