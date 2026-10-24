"""The trusted-data plan's verification standard and T0 (`learn/verify_tracks.py`): the pure rules and the signal
measures on synthetic audio. No data files, no renders."""

import json
import math
import re

import pytest

from learn import verify_tracks as V


# --- statuses ---------------------------------------------------------------------------------------------------

def test_a1_lag_rule():
    assert V.a1_status(0.17) == "pass"                     # magilla's lag, the smallest real amp
    assert V.a1_status(0.0) == "fail"                      # Prodigal's
    assert V.a1_status(0.05) == "fail"
    assert V.a1_status(19.5) == "pass"                     # Drag Me Down's long path
    assert V.a1_status(30.5) == "fail"
    assert V.a1_status(-1.08) == "ear"                     # a recording offset goes to the ear
    assert V.a1_status(float("nan")) == "fail" and V.a1_status(None) == "fail"


def test_a2_half_and_part_rules():
    assert V.a2_half_status(6.2, 100, 46) == "ear"         # colour-me-red elecgtr03 half A: between fail and pass
    assert V.a2_half_status(12.0, 100, 46) == "pass"       # the plan's 12 dB pass is kept
    assert V.a2_half_status(0.4, 171, 255) == "fail"       # Prodigal ElecGtr5 half B
    assert V.a2_half_status(-3.9, 171, 10) == "ear"        # Quicksand ElecGtr2: a fail needs the 17-bin gate too
    assert V.a2_half_status(-19.0, 40, 1) == "ear"         # Adam Buckley ElecGtr5's DI: one coherent bin
    assert V.a2_half_status(3.2, 17, 17) == "fail"
    assert V.a2_half_status(None, 0, 0) == "ear"
    assert V.a2_half_status(25.0, V.A2_MIN_BINS - 1, 300) == "ear"   # too few bins to pass
    assert V.a2_part(["pass", "ear"]) == "pass"
    assert V.a2_part(["pass", "fail"]) == "fail"
    assert V.a2_part(["ear", "ear"]) == "ear"


def test_combine_part_is_strict():
    assert V.combine_part(["pass", "pass"]) == "pass"
    assert V.combine_part(["pass", "ear"]) == "ear"
    assert V.combine_part(["pass", "fail", "ear"]) == "fail"
    assert V.combine_part([]) == "fail" and V.combine_part([None]) == "fail"


def test_a3_a4_a5_a6():
    assert V.a3_status([-5.5, -8.4]) == "pass"
    assert V.a3_status([-80.5, -5.0]) == "fail"            # either direction finding a linear copy fails it
    assert V.a3_status([None, None]) == "fail"
    assert V.a4_status(0.94, False) == "pass" and V.a4_status(0.951, False) == "fail"
    assert V.a4_status(0.2, True) == "fail"
    assert V.a5_half_status(0.4, 0.99, 0.9) == "fail"      # the DI plays under half the frames
    assert V.a5_half_status(0.9, 0.81, 0.10) == "pass"     # chroma alone
    assert V.a5_half_status(0.9, 0.70, 0.36) == "pass"     # onsets alone
    assert V.a5_half_status(0.9, 0.70, 0.29) == "fail"     # Today's The Day ElecGtr07 half A
    assert V.a6_half_status({"flag": "low", "bleed_db": -30.1}) == "pass"
    assert V.a6_half_status({"flag": "moderate", "bleed_db": -21.3}) == "fail"
    assert V.a6_half_status({"flag": "silent", "bleed_db": -99}) == "fail"
    assert V.a6_half_status(None) == "fail"
    assert V.a6_mix_status([None, -35.0]) == "pass" and V.a6_mix_status([-35.0, -12.0]) == "fail"


def test_dis_rules():
    assert V.d3_status("GTR 1 DI TDP-1.1-Norm_01-01.wav") == "pass"
    assert V.d3_status("cambridge/X/17_ElecGtr5DI.wav") == "pass"
    assert V.d3_status("Pedal Board.wav") == "fail"
    assert V.d3_status("GTR Line Out.wav") == "fail"
    assert V.d2_status(["hum"]) == "fail" and V.d2_status(["clipping"]) == "fail"
    assert V.d2_status(["hiss", "bleed"]) == "pass"        # shown, not excluded
    assert V.di_verdict({"D1": "pass", "D2": "pass", "D3": "pass"}) == ("verified", [])
    v, why = V.di_verdict({"D1": "ear", "D2": "pass", "D3": "pass"})
    assert v == "pending ear" and why == ["D1 to the ear"]                  # queued, pending until heard
    assert V.di_verdict({"D1": None, "D2": "pass", "D3": "pass"})[0] == "pending ear"   # DI-only
    assert V.di_verdict({"D1": "pass", "D2": "pass", "D3": "pass", "D4": "fail"})[0] == "pending ear"   # never excluded
    assert V.di_verdict({"D1": "fail", "D2": "pass", "D3": "pass"})[0] == "excluded"
    assert V.di_verdict({"D1": None, "D2": "fail", "D3": "pass"})[0] == "excluded"


def _ok(**kw):
    st = {m: "pass" for m in ("A1", "A2", "A3", "A4", "A5", "A6")}
    st.update(kw)
    return st


def test_target_verdict():
    assert V.target_verdict(_ok(), True, None) == ("verified", [])
    assert V.target_verdict(_ok(A6="fail"), True, True)[0] == "excluded"
    assert V.target_verdict(_ok(A2="ear"), True, None)[0] == "pending ear"
    assert V.target_verdict(_ok(A2="ear"), True, True) == ("verified", [])
    assert V.target_verdict(_ok(A2="ear"), True, False)[0] == "excluded"
    assert V.target_verdict(_ok(), None, None)[0] == "pending ear"
    assert V.target_verdict(_ok(), False, True)[0] == "excluded"
    assert V.target_verdict(_ok(A5="fail"), True, True) == ("excluded", ["A5 fails"])   # a measured fail stands
    assert V.target_verdict(_ok(), True, True, in_mix=True)[0] == "excluded"       # A6's mix clause unread
    assert V.target_verdict(_ok(A6mix="pass"), True, True, in_mix=True) == ("verified", [])


def _cal_rows(known=None, fails=None, negs=None):
    rows = [{"name": s, "kind": "known", "status": {"A1": "pass", "A2": "ear", "A3": "pass", "A4": "pass"}}
            for s in V.KNOWN_AMPS]
    rows += [{"name": s, "kind": "fail", "status": {"A1": "fail", "A2": "fail", "A3": "pass", "A4": "pass"}}
             for s in V.KNOWN_FAILS]
    rows += [{"name": "n|copy", "kind": "copy", "status": {"A1": "fail", "A2": "fail", "A3": "fail", "A4": "fail"}},
             {"name": "n|eq", "kind": "eq", "status": {"A1": "pass", "A2": "pass", "A3": "fail", "A4": "pass"}},
             {"name": "n|cab_off_clean", "kind": "cab_off_clean",
              "status": {"A1": "pass", "A2": "fail", "A3": "pass", "A4": "pass"}},
             {"name": "n|cab_off_crunch", "kind": "cab_off_crunch",
              "status": {"A1": "pass", "A2": "ear", "A3": "pass", "A4": "pass"}},
             {"name": "n|cab_off_clean_sw50r", "kind": "cab_off_clean_sw50r",
              "status": {"A1": "pass", "A2": "fail", "A3": "pass", "A4": "pass"}},
             {"name": "n|cab_off_clean_ac20", "kind": "cab_off_clean_ac20",
              "status": {"A1": "pass", "A2": "fail", "A3": "pass", "A4": "pass"}}]
    for r in rows:
        r["status"].update((known or {}).get(r["name"], {}))
        r["status"].update((fails or {}).get(r["name"], {}))
        r["status"].update((negs or {}).get(r["kind"], {}))
    return rows


def test_calibration_verdict():
    assert V.calibration_verdict(_cal_rows()) == ("OK", [])
    v, p = V.calibration_verdict(_cal_rows(known={V.KNOWN_AMPS[0]: {"A2": "fail"}}))
    assert v == "FAIL" and V.KNOWN_AMPS[0] in p[0]
    v, p = V.calibration_verdict(_cal_rows(fails={V.KNOWN_FAILS[0]: {"A1": "pass", "A2": "ear"}}))
    assert v == "FAIL"
    v, p = V.calibration_verdict(_cal_rows(negs={"eq": {"A3": "pass", "A1": "fail"}}))
    assert v == "FAIL"                                     # the EQ'd DI must fail A3, not another measure
    v, p = V.calibration_verdict(_cal_rows(negs={"cab_off_crunch": {"A2": "pass"}}))
    assert v == "OK"                                       # the crunch cab-off is beside, not declared
    v, p = V.calibration_verdict([r for r in _cal_rows() if r["kind"] != "cab_off_clean"])
    assert v == "FAIL" and any("cab_off_clean" in x for x in p)
    v, p = V.calibration_verdict(_cal_rows(negs={"cab_off_clean_ac20": {"A2": "ear"}}))
    assert v == "FAIL"                                     # a fresh cab-off negative must fail A2 too
    assert set(V.NEG_RENDERS) <= set(V.NEG_KINDS) and V.NEG_MUST_FAIL["cab_off_clean_sw50r"] == ("A2",)


def test_threshold_moves_are_recorded_against_the_constants():
    moves = {m["threshold"]: m for m in V.THRESHOLD_MOVES}
    assert "12" in moves["A2"]["plan"] and str(V.A2_PASS_DB) in moves["A2"]["now"] and str(V.A2_FAIL_DB) in moves["A2"]["now"]
    assert V.A2_PASS_DB == 12.0                                       # the plan's pass, kept (review of #281)
    assert moves["A2_MIN_BINS"]["now"] == V.A2_MIN_BINS
    assert V.A3_MAX_DB == -40.0 and V.A4_MAX_CORR == 0.95 and V.A6_BLEED_DB == -30.0      # the plan's, unmoved
    assert (V.LAG_MIN_MS, V.LAG_MAX_MS) == (0.1, 30.0)
    assert set(V.KNOWN_AMPS).isdisjoint(V.KNOWN_FAILS) and len(V.KNOWN_AMPS) == 11 and len(V.KNOWN_FAILS) == 2
    assert not set(V.KNOWN_DROPPED) & set(V.KNOWN_AMPS) and not set(V.NEG_SOURCES) & set(V.KNOWN_DROPPED)
    assert set(V.KNOWN_EAR_REJECTED) <= set(V.KNOWN_DROPPED) and len(V.KNOWN_EAR_REJECTED) == 7
    assert "known amps" in moves and moves["known amps"]["now"] == 11
    th = V.thresholds()
    assert th["A2"]["pass_db"] == V.A2_PASS_DB and th["A2"]["fail_db"] == V.A2_FAIL_DB and th["A3"]["max_db"] == V.A3_MAX_DB


def test_known_amps_come_from_the_target_vs_di_measurements():
    meas = json.loads(V.TVD_MEASURES.read_text())
    assert tuple(sorted(V.known_amps_from(meas))) == tuple(sorted(V.KNOWN_AMPS))
    toy = {"sample_rate": 48000, "parts": {
        "amp": {"halves": {"A": {"lag": 24, "hf_drop_H": -15.0}, "B": {"lag": 24, "hf_drop_H": -13.0}}},
        "flat": {"halves": {"A": {"lag": 24, "hf_drop_H": -2.0}, "B": {"lag": 24, "hf_drop_H": -13.0}}},
        "zero": {"halves": {"A": {"lag": 0, "hf_drop_H": -20.0}, "B": {"lag": 0, "hf_drop_H": -20.0}}},
        "one": {"halves": {"A": {"lag": 24, "hf_drop_H": -20.0}}}}}
    assert V.known_amps_from(toy, dropped=(), fails=()) == ("amp",)


def test_only_the_negatives_render():
    from learn import local_objective as LO

    for cmd in ("calibrate", "targets", "dis --shard 0/3", "inject-strict", "stem-scan --shard 1/3", "lists", "reread"):
        assert not any(re.search(p, f"python -m learn.verify_tracks {cmd}") for p in LO.RENDERS)
    assert any(re.search(p, "python -u -m learn.verify_tracks negatives") for p in LO.RENDERS)


# --- ear answers, the stem floor, the level prior -----------------------------------------------------------------

def test_ear_reading():
    clean = {("s", "A"): "clean", ("s", "B"): "clean", ("t", "A"): "clean", ("u", "A"): "bleed"}
    assert V.ear_clean_of("s", clean) is True
    assert V.ear_clean_of("t", clean) is None              # half B not heard
    assert V.ear_clean_of("u", clean) is False
    assert V.ear_amp_of("s", {"s": "amp"}) is True
    assert V.ear_amp_of("s", {"s": "same_di"}) is False
    assert V.ear_amp_of("s", {"s": "unsure"}) is None and V.ear_amp_of("x", {}) is None


def _inj_row(session, base, inj):
    return {"session": session, "deciding": True,
            "targets": {f"t{k}": {"room": k == 0, "base": base, "inj": inj} for k in range(5)}}


def test_strict_floor():
    from learn import data_cleaning as DC

    good = {-35.0: -35.5, -40.0: -41.0}
    rows = [_inj_row(s, -50.0, good) for s in DC.INJECT_DECIDING]
    assert V.strict_floor(rows) == -40.0
    rows = [_inj_row(s, -50.0, {-35.0: -36.0, -40.0: -46.0}) for s in DC.INJECT_DECIDING]
    assert V.strict_floor(rows) == -35.0                   # -40 not read back
    rows = [_inj_row(s, -38.0, good) for s in DC.INJECT_DECIDING]
    assert V.strict_floor(rows) == -30.0                   # the uninjected tracks read too high at either level
    assert V.strict_floor(rows[:2]) == -30.0               # a deciding session missing
    assert V.stem_pass({"g1": -45.0, "g2": None}, -30.0) and not V.stem_pass({"g1": -29.0}, -30.0)


def test_rederive_prior(tmp_path):
    pytest.importorskip("numpy")                           # prior_summary
    def part(slug, band, c0, rows):
        (tmp_path / f"{slug}.json").write_text(json.dumps({"slug": slug, "band": band, "crop_start_s": c0, "rows": rows}))

    part("a", "A", 20.0, [{"start_s": 0.0, "passes": True, "snr_db": -5.0},
                          {"start_s": 20.0, "passes": True, "snr_db": -9.0},
                          {"start_s": 40.0, "passes": False, "snr_db": -1.0}])
    part("b", "B", 0.0, [{"start_s": 0.0, "passes": True, "snr_db": -7.0}])
    part("c", "C", 0.0, [{"start_s": 0.0, "passes": True, "snr_db": -20.0}])
    vals, counts = V.rederive_prior(tmp_path, {"b"}, {"a": 20.0})
    assert vals == {"A": [-5.0], "B": [-7.0]} and counts == {"a": 1, "b": 1}          # c fails; a loses its crop
    s = V.prior_summary(vals)
    assert s["n"] == 2 and s["median"] == -6.0


# --- signals (synthetic) ------------------------------------------------------------------------------------------

def _noise(n, seed=0):
    np = pytest.importorskip("numpy")
    return np.random.default_rng(seed).standard_normal(n)


def test_gcc_lag_finds_a_band_limited_delay():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    x = _noise(48000)
    y = np.concatenate([np.zeros(24), x[:-24]])           # 0.5 ms
    lag, prom = V.gcc_lag_ms(x, y, 48000)
    assert abs(lag - 0.5) < 1e-9 and prom > 10
    lag, _ = V.gcc_lag_ms(y, x, 48000)
    assert abs(lag + 0.5) < 1e-9


def test_cab_drop_sees_a_rolloff_and_a_flat_copy():
    np = pytest.importorskip("numpy")
    ss = pytest.importorskip("scipy.signal")
    x = _noise(48000 * 4)
    b, a = ss.butter(6, 4000, fs=48000)
    cab = ss.lfilter(b, a, x)
    d = V.cab_drop(x, cab, 48000)
    assert d["n_hi"] > V.A2_MIN_BINS and d["drop_db"] > 30
    flat = V.cab_drop(x, 0.3 * x, 48000)
    assert abs(flat["drop_db"]) < 0.5
    sat = V.cab_drop(x, np.tanh(30 * x), 48000)           # heavy distortion: incoherent highs, the ear decides
    assert V.a2_half_status(sat["drop_db"], sat["n_lo"], sat["n_hi"]) in ("ear", "fail")


def test_linear_residuals_catch_an_eqd_copy_not_a_nonlinear_path():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    sr = 48000
    rng = np.random.default_rng(1)
    t = np.arange(sr * 10) / sr
    x = np.sin(2 * np.pi * 110 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * t)) + 0.05 * rng.standard_normal(len(t))
    eq = V.neg_eq(x, sr)
    lag, _ = V.gcc_lag_ms(x[sr:], eq[sr:], sr)
    r = V.linear_residuals(x, eq, sr, lag)
    assert V.a3_status(list(r.values())) == "fail" and max(r.values()) < -60
    nl = np.tanh(8 * x)
    r = V.linear_residuals(x, nl, sr, 0.0)
    assert V.a3_status(list(r.values())) == "pass"


def test_copy_correlation():
    np = pytest.importorskip("numpy")
    x = _noise(48000, 2)
    c = V.max_copy_corr(x, {"own": np.concatenate([np.zeros(10), x[:-10]]), "other": _noise(48000, 3),
                            "silent": np.zeros(48000)}, 48000)
    assert c["own"] > 0.99 and c["other"] < 0.1 and c["silent"] is None


def test_pair_status_on_constructed_cases():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    sr = 48000
    rng = np.random.default_rng(4)
    t = np.arange(sr * 10) / sr
    x = np.sin(2 * np.pi * 196 * t) * np.abs(np.sin(2 * np.pi * 1.3 * t)) + 0.02 * rng.standard_normal(len(t))
    copy = V.pair_status(V.measure_pair(x, x.copy()), 1.0, False)
    assert copy["A1"] == "fail" and copy["A3"] == "fail" and copy["A4"] == "fail"
    eq = V.pair_status(V.measure_pair(x, V.neg_eq(x, sr)), 0.5, False)
    assert eq["A1"] == "pass" and eq["A3"] == "fail"


def test_pan_free_helpers_and_names():
    assert V.is_di_name("GTR 1 DI TDP-1.1-Norm_01-01.wav") and V.is_di_name("19_ElecGtr2DI.wav")
    assert not V.is_di_name("17_ElecGtr2Close.wav") and not V.is_di_name("Bass DI_TDA-1.wav")
    assert V.guitar_sources(["01_Kick.wav", "17_ElecGtr2Close.wav", "19_ElecGtr2DI.wav", "04_Bass.wav"]) == \
        ["17_ElecGtr2Close.wav", "19_ElecGtr2DI.wav"]
    assert math.isclose(V.margins([{"kind": "known", "v": 3.0}, {"kind": "fail", "v": 1.0}], "m", lambda r: r["v"],
                                  lambda r: True)["others_max"], 1.0)


# --- the review's additions: unreadable lags, D1 over sections, processed DIs ------------------------------------

def test_a1_unreadable_lag_goes_to_the_ear():
    assert V.a1_status(0.6, prominence=24.0) == "pass"            # the weakest known amp's half reads 24
    assert V.a1_status(35.0, prominence=5.8) == "ear"             # a high-gain pair: no linear path to time
    assert V.a1_status(0.0, prominence=274.0) == "fail"           # Prodigal ElecGtr5: a clear zero-lag path
    assert V.A1_PROM_MIN == 12.0


def _half(lag, prom, drop, n_hi, n_lo=171):
    return {"lag_ms": lag, "lag_prominence": prom, "a2": {"drop_db": drop, "n_lo": n_lo, "n_hi": n_hi}}


def test_d1_over_sections_reads_medians():
    hs = [_half(19.8, 76, 9.0, 4), _half(19.8, 63, 9.7, 14), _half(19.6, 45, 6.0, 25), _half(19.8, 70, 4.5, 23)]
    d = V.d1_status(hs)                                            # Adam Buckley ElecGtr3: a roll-off under 12 dB
    assert d["A1"] == "pass" and d["A2"] == "ear" and d["status"] == "ear"
    d = V.d1_status([_half(0.6, 80, 20.0, 40), _half(0.6, 90, 18.0, 30)])
    assert d["status"] == "pass"
    d = V.d1_status([_half(35.0, 5.8, None, 0), _half(-1.5, 4.9, None, 0)])
    assert d["status"] == "ear" and d["A1"] == "ear" and d["A2"] == "ear"
    d = V.d1_status([_half(0.0, 108, 0.0, 339), _half(0.0, 645, 0.0, 342)])        # Prodigal ElecGtr3's DI
    assert d["status"] == "fail"


def test_d2_hum_suspect_and_d4_rule():
    assert V.d2_status([], hum_suspect=True) == "fail" and V.d2_status(["hiss"], hum_suspect=False) == "pass"
    assert V.d4_status(12.2, 0.35) == "pass"                      # magilla elecgtr1's DI
    assert V.d4_status(5.4, -6.2) == "fail"                       # Strangest Places: driven
    assert V.d4_status(9.97, -0.29) == "fail"                     # brightness does not rise with level
    assert V.d4_status(None, 0.5) == "fail"
    assert V.ear_di_verdict({"A": "clean", "B": "clean"}) is True
    assert V.ear_di_verdict({"A": "clean", "B": "other_guitar"}) is False
    assert V.ear_di_verdict({}) is None


def test_d4_agreement_counts():
    ear = {"a": False, "b": False, "c": True, "d": True, "e": None}
    meas = {"a": "fail", "b": "pass", "c": "pass", "d": "fail", "e": "fail"}
    g = V.d4_agreement(ear, meas)
    assert g["heard"] == 4 and g["agree"] == 2 and g["processed_missed"] == ["b"] and g["clean_flagged"] == ["d"]


def test_di_processing_tells_a_plucked_di_from_a_driven_one():
    np = pytest.importorskip("numpy")
    sr = 48000
    rng = np.random.default_rng(5)

    def pluck(f0, a, n):                                           # Karplus-Strong: a transient, then a decay
        period = int(sr / f0)
        buf = rng.uniform(-1, 1, period) * a
        out = np.zeros(n)
        for i in range(n):
            out[i] = buf[i % period]
            buf[i % period] = 0.5 * (buf[i % period] + buf[(i + 1) % period]) * 0.996
        return out

    clean = np.concatenate([pluck(110 * 2 ** (rng.integers(0, 12) / 12), 0.2 + 0.8 * rng.random(), int(0.4 * sr))
                            for _ in range(14)])
    driven = np.tanh(25 * clean / np.max(np.abs(clean)))
    c, d = V.di_processing(clean), V.di_processing(driven)
    assert V.d4_status(c["crest_db"], c["bright_slope"]) == "pass"
    assert V.d4_status(d["crest_db"], d["bright_slope"]) == "fail"
    assert c["crest_db"] > d["crest_db"]


def test_other_takes_must_be_electric():
    assert V.is_electric_take("15_ElecGtr1DTAmp.wav") and V.is_electric_take("GTR 2 Amp M80.wav")
    assert not V.is_electric_take("30_AcousticGtr.wav") and not V.is_electric_take("04_Bass.wav")


def test_ear_answers_split_di_and_target(tmp_path, monkeypatch):
    lst = tmp_path / "listening"
    (lst / "data-review-1").mkdir(parents=True)
    (lst / "target-vs-di-check").mkdir(parents=True)
    (lst / "data-review-1" / "items.json").write_text(json.dumps({"items": [
        {"id": "amp-1", "section": "amp", "slug": "s", "half": "A"},
        {"id": "amp-2", "section": "amp", "slug": "s", "half": "B"}]}))
    (lst / "target-vs-di-check" / "items.json").write_text(json.dumps({"items": [
        {"id": "tvd-1", "section": "tvd", "private": {"slug": "s", "half": "A"}}]}))
    monkeypatch.setattr(V, "HOME", tmp_path)
    s1 = tmp_path / "s1.json"
    s1.write_text(json.dumps({"page": "data-review-1", "sitting": 1, "answers": [
        {"id": "amp-1", "verdict": "clean"}, {"id": "amp-2", "verdict": "other"}]}))
    tv = tmp_path / "tv.json"
    tv.write_text(json.dumps({"page": "target-vs-di-check", "answers": [{"id": "tvd-1", "verdict": "amp"},
                                                                        {"id": "tvd-1", "verdict": "same_di"}]}))
    e = V.ear_answers([tv], [s1])
    assert e["target_clean"] == {} and e["target_amp"] == {"s": ["amp", "same_di"]}
    assert e["crop_di"] == {"s": {"A": ["clean"], "B": ["other"]}}
    assert V.ear_amp_of("s", e["target_amp"]) is False                 # any "not amp" wins
    assert V.ear_di_verdict(e["crop_di"]["s"]) is False
    with pytest.raises(SystemExit):
        V.ear_answers([s1], [])                                        # a DI-verdict export is not a target verdict
    with pytest.raises(SystemExit):
        V.ear_answers([], [tv])
    reg = {"ear-x": {"kind": "target", "family": "target", "key": "t", "half": "B", "start_s": 4.0, "dur_s": 6.0},
           "ear-y": {"kind": "di_flagged", "family": "di", "key": "d", "start_s": 30.0, "dur_s": 10.0},
           "ear-z": {"kind": "di_amp", "family": "di_amp", "key": "d", "start_s": 30.0, "dur_s": 10.0}}
    q = tmp_path / "q.json"
    q.write_text(json.dumps({"page": V.EAR_PAGE, "answers": [{"id": "ear-x", "verdict": "clean_amp"},
                                                             {"id": "ear-y", "verdict": "clean"},
                                                             {"id": "ear-z", "verdict": "amp"}]}))
    e = V.ear_answers([q], [], reg)
    assert e["target_clean"] == {("t", "B"): ["clean"]} and e["target_amp"] == {"t": ["amp"]}
    assert e["di_windows"] == {"d": [(30.0, 40.0, "clean")]} and e["di_pairs"] == {"d": ["amp"]}
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"page": V.EAR_PAGE, "answers": [{"id": "ear-x", "verdict": "clean"}]}))
    with pytest.raises(SystemExit):
        V.ear_answers([bad], [], reg)                                  # not a target verdict


def test_merge_ear_lets_a_negative_win():
    assert V.merge_ear(["clean", "clean"], "clean") is True
    assert V.merge_ear(["clean", "processed"], "clean") is False
    assert V.merge_ear(["clean", "unsure"], "clean") is None
    assert V.merge_ear([], "clean") is None and V.merge_ear([None], "amp") is None
    assert V.ear_clean_of("s", {("s", "A"): ["clean"], ("s", "B"): ["clean", "bleed"]}) is False


def test_d4_rule_search_and_leave_one_out():
    pytest.importorskip("numpy")                           # d4_fit's grid
    rows = [(False, 6.0, 0.5), (False, 7.0, -0.6), (False, 9.5, 0.4), (True, 11.0, 0.5), (True, 10.0, 0.3),
            (True, 12.0, 0.9), (True, 7.5, 1.0)]
    c, s_, caught, flagged = V.d4_fit(rows)
    assert caught >= 2 and flagged <= 1
    ok, n = V.d4_loo(rows)
    assert n == len(rows) and 0 <= ok <= n


def test_load_shards_refuses_gaps(tmp_path):
    (tmp_path / "t0").mkdir()
    for k in (0, 2):
        (tmp_path / "t0" / f"dis-{k}of3.json").write_text(json.dumps(
            {"shard": [k, 3], "complete": k == 0, "thresholds": V.thresholds(), "rows": {f"di:{k}": {}}}))
    rows, probs = V.load_shards(tmp_path, "dis", "rows", lambda d: d.get("thresholds") == V.thresholds())
    assert set(rows) == {"di:0", "di:2"}
    assert any("missing" in p for p in probs) and any("incomplete" in p for p in probs)
    rows, probs = V.load_shards(tmp_path, "stems", "sessions", lambda d: True)
    assert probs == ["no stems shard"]


def test_sample_passed_and_overlaps():
    def row(band, crests):
        return {"datasets": ["training pool"], "band": band, "amp_tracks": [], "di": "d", "hum_suspect": False,
                "sections": [{"section": f"s{k}", "start_s": 10.0 * k, "D1": None, "D2": {"flags": []},
                              "D4": {"crest_db": c, "bright_slope": 0.5, "frames": 90}} for k, c in enumerate(crests)]}
    rows = {"a": row("X", [11, 12]), "b": row("X", [6, 12]), "c": row("Y", [11])}
    s = V.sample_passed(rows)
    assert set(s) == {"a", "c"} and s == V.sample_passed(rows)
    assert V.overlaps(0, 10, 9.9, 20) and not V.overlaps(0, 10, 10, 20)
    assert V.section_ear(10.0, [(12.0, 18.0, "clean"), (40.0, 46.0, "processed")]) is True


def test_d1_and_d2_read_every_window_but_d2_excludes_only_on_own_sections():
    def sec(sid, own, flags, crest, halves=None):
        return {"section": sid, "start_s": 0.0, "own": own, "D2": {"flags": flags},
                "D1": {"halves": halves} if halves else None,
                "D4": {"crest_db": crest, "bright_slope": 0.5, "frames": 90 if crest else 0}}
    good = {"A": _half(0.6, 80, 20.0, 40), "B": _half(0.6, 80, 19.0, 40)}
    row = {"di": "x/ElecGtr1DI.wav", "amp_tracks": ["amp"], "hum_suspect": False,
           "sections": [sec("own1", True, [], 11.0, good), sec("other1", False, ["dropout"], 11.0, good),
                        sec("other2", False, [], None)]}
    rs = V.di_row_status(row)
    assert rs["status"] == {"D1": "pass", "D2": "pass", "D3": "pass"}                 # a window's drop-out stays local
    assert rs["d2_sections"]["other1"] == "fail" and rs["d4_sections"]["other2"] == "silent"
    row["sections"][0]["D2"]["flags"] = ["hum"]
    assert V.di_row_status(row)["status"]["D2"] == "fail"


def test_a2_slope_fails_only_bleed_clean_halves_with_no_roll_off():
    fail = V.A2_SLOPE_FAIL
    assert math.isclose(fail, -V.A2_FAIL_DB / 2)                     # A2's fail line over its two octaves
    assert V.a2_slope_fails(0.9, -99.0)                               # the clean cab-off negative
    assert not V.a2_slope_fails(-10.5, -90.0)                         # the flattest bleed-clean known amp
    assert not V.a2_slope_fails(12.6, -28.6)                          # Sculptor's Request GTR 2: its top is bleed
    assert not V.a2_slope_fails(5.0, None) and not V.a2_slope_fails(None, -90.0)


def test_pair_status_uses_the_slope_only_where_the_coherent_a2_is_unsure():
    def half(drop, n_hi, rel):
        return {"lag_ms": 1.06, "lag_prominence": 50.0, "a2": {"drop_db": drop, "n_lo": 150, "n_hi": n_hi},
                "slope": {"target": -11.0, "di": -12.0, "rel": rel}}
    m = {"halves": {"A": half(-2.0, 12, 0.9), "B": half(-2.8, 7, 0.9)}, "a3": {"A>B": -13.9, "B>A": -13.8}}
    clean = {"A": -99.0, "B": -99.0}
    assert V.pair_status(m)["A2"] == "ear"                            # no bleed reading: no opinion
    assert V.pair_status(m, bleed=clean)["A2"] == "fail"              # the stored cab-off negative's readings
    m["halves"]["A"] = half(20.0, 40, 0.9)                            # a coherent pass is not overridden
    assert V.pair_status(m, bleed=clean)["A2"] == "fail"              # ... but half B still fails
    m["halves"]["B"] = half(20.0, 40, 0.9)
    assert V.pair_status(m, bleed=clean)["A2"] == "pass"


def test_hf_slope_reads_a_cab_like_roll_off():
    np = pytest.importorskip("numpy")
    ss = pytest.importorskip("scipy.signal")
    x = np.random.default_rng(7).standard_normal(48000 * 4)
    b, a = ss.butter(4, 5000, fs=48000)
    cab = ss.lfilter(b, a, x)
    r = V.rel_hf_slope(x, cab)
    assert r["rel"] < -15 and abs(V.rel_hf_slope(x, 0.5 * x)["rel"]) < 0.5
    assert V.hf_slope(np.zeros(48000)) is None


# --- `lists` end to end on synthetic T0 records (the 2026-10-23 review of the ear's round trip) -----------------

def _sec(sid, t0, crest=12.0, own=True, d1=True):
    return {"section": sid, "start_s": t0, "own": own, "D2": {"flags": []},
            "D1": {"halves": {"A": _half(2.0, 50, 20.0, 50, 50), "B": _half(2.0, 50, 20.0, 50, 50)},
                   "amp_track": "05_Gtr.wav"} if d1 else None,
            "D4": {"crest_db": crest, "bright_slope": 0.5, "frames": 50}}


def _di(di, band, secs, ds=("training pool",)):
    return {"di": di, "band": band, "datasets": list(ds), "amp_tracks": ["05_Gtr.wav"], "hum_suspect": False,
            "path": f"/x/{band}_Full/{di}.wav", "sections": secs}


class _Lists:
    """Fake T0 records under a scratch root, and `lists` run on them (smoke unless real=True)."""

    def __init__(self, tmp_path, monkeypatch, dis, crops=None, stems=None):
        from learn import pretrain_set as PS

        self.root = tmp_path / "root"
        (self.root / "t0").mkdir(parents=True)
        (self.root / "t0" / "targets.json").write_text(json.dumps({"thresholds": V.thresholds(), "complete": True,
                                                                   "parts": {}}))
        rows = {f"di:{r['di']}": r for r in dis} | {f"crop:{k}": c for k, c in (crops or {}).items()}
        (self.root / "t0" / "dis-0of1.json").write_text(json.dumps(
            {"shard": [0, 1], "complete": True, "thresholds": V.thresholds(), "rows": rows}))
        (self.root / "t0" / "stems-0of1.json").write_text(json.dumps(
            {"shard": [0, 1], "complete": True, "floor_db": V.STEM_TAKE_DB, "sessions": stems or {}}))
        monkeypatch.setattr(PS, "ratio_values", lambda: {})
        monkeypatch.setattr(PS, "SECTIONS_MS", tmp_path / "no-sections")
        monkeypatch.setattr(V, "HOME", tmp_path / "home")
        monkeypatch.setattr(V, "OUT", self.root)
        self.tmp, self.n = tmp_path, 0

    def run(self, ear=(), ear_di=(), real=False, drop=False):
        import types

        V.cmd_lists(types.SimpleNamespace(smoke=not real, out=None if real else str(self.root), ear=list(ear),
                                          ear_di=list(ear_di), drop_ear=drop))
        t0 = self.root / "t0"
        return json.loads((t0 / "verified.json").read_text()), json.loads((t0 / "ear-queue.json").read_text())

    def export(self, answers, part=3, exported="2026-10-24T08:00:00Z", page=V.EAR_PAGE):
        """answers: (id, verdict, note) or (id, verdict, note, t); t None marks a card never touched."""
        self.n += 1
        p = self.tmp / f"export-{self.n}.json"
        p.write_text(json.dumps({"page": page, "part": part, "build": "b1", "exported": exported, "answers": [
            {"id": a[0], "verdict": a[1], "note": a[2], **({"t": a[3]} if len(a) > 3 else {})} for a in answers]}))
        return str(p)


def _ids(q, kind, key):
    return {x["start_s"]: x["id"] for x in q["queue"] if x["kind"] == kind and x["key"] == key}


def test_lists_refuses_to_drop_an_earlier_export_and_a_real_run_needs_sitting_1(tmp_path, monkeypatch):
    pytest.importorskip("numpy")                           # lists -> prior_summary
    env = _Lists(tmp_path, monkeypatch, [_di("x", "B1", [_sec("x1", 10.0, crest=6.0), _sec("x2", 40.0)])])
    rec, q = env.run()
    p1 = env.export([(_ids(q, "di_flagged", "x")[10.0], "processed", "")])
    rec, _ = env.run([p1])
    assert rec["dis"]["x"]["verdict"] == "excluded" and rec["ear_exports"][0]["sha256"]
    p2 = env.export([], part=4)
    with pytest.raises(SystemExit, match="drop"):
        env.run([p2])                                             # part 3's answers would be lost
    rec, _ = env.run([p1, p2])
    assert rec["dis"]["x"]["verdict"] == "excluded"
    rec, _ = env.run([p2], drop=True)                             # on purpose only
    assert rec["dis"]["x"]["verdict"] != "excluded"
    later = env.export([(_ids(q, "di_flagged", "x")[10.0], "clean", "")], exported="2026-10-24T09:00:00Z")
    rec, _ = env.run([p2, later])                                 # a later export of part 3 replaces the earlier one
    assert rec["dis"]["x"]["verdict"] == "verified"
    with pytest.raises(SystemExit, match="ear-di"):
        env.run([p2, later], real=True)


def test_dropped_exports_by_hash_or_by_later_touches_of_every_card():
    old = {"ear_exports": [{"path": "/a.json", "sha256": "1", "page": V.EAR_PAGE, "part": 1, "build": "b",
                            "exported": "2026-10-24T08:00", "answered": {"x": "08:00", "y": "07:00"}},
                           {"path": "/s1.json", "sha256": "2", "page": "data-review-1", "part": None, "build": None,
                            "exported": None, "answered": None}]}
    s1 = {"path": "/elsewhere/s1.json", "sha256": "2", "page": "data-review-1", "answered": None}
    assert V.dropped_exports(old, [s1]) == ["/a.json"]
    other_browser = {"path": "/a2.json", "sha256": "3", "page": V.EAR_PAGE, "part": 1, "build": "b",
                     "exported": "2026-10-24T09:00", "answered": {"z": "09:00"}}
    assert V.dropped_exports(old, [s1, other_browser]) == ["/a.json"]          # a later file that lacks x and y
    same_browser = dict(other_browser, sha256="4", answered={"x": "08:00", "y": "08:30", "z": "09:00"})
    assert V.dropped_exports(old, [s1, same_browser]) == [] and V.dropped_exports(None, [s1]) == []
    assert V.dropped_exports({"ear_exports": [dict(old["ear_exports"][0], answered=None)]}, [same_browser]) == ["/a.json"]


def test_an_export_from_another_browser_never_erases_an_answer(tmp_path, monkeypatch):
    pytest.importorskip("numpy")                           # lists -> prior_summary
    env = _Lists(tmp_path, monkeypatch, [_di("x", "B1", [_sec("x1", 10.0, crest=6.0), _sec("x2", 40.0)])])
    _, q = env.run()
    iid = _ids(q, "di_flagged", "x")[10.0]
    phone = env.export([(iid, "processed", "", "2026-10-24T08:00:00Z")])
    laptop = env.export([(iid, None, "", None)], exported="2026-10-24T10:00:00Z")   # the card untouched there
    rec, _ = env.run([phone, laptop])
    assert rec["dis"]["x"]["verdict"] == "excluded"
    with pytest.raises(SystemExit, match="drop"):
        env.run([laptop])                                     # the laptop's file does not hold the phone's answer
    taken_back = env.export([(iid, None, "", "2026-10-24T11:00:00Z")], exported="2026-10-24T11:00:00Z")
    rec, _ = env.run([phone, laptop, taken_back])             # a later touch that clears the answer does stand
    assert rec["dis"]["x"]["verdict"] != "excluded"


def test_unsure_on_a_sampled_di_keeps_it_pending(tmp_path, monkeypatch):
    pytest.importorskip("numpy")                           # lists -> prior_summary
    env = _Lists(tmp_path, monkeypatch, [_di("s", "B1", [_sec("s1", 10.0), _sec("s2", 20.0)])])
    rec, q = env.run()
    (t, iid), = _ids(q, "di_sample", "s").items()
    rec, q = env.run([env.export([(iid, "unsure", "")])])
    assert rec["dis"]["s"]["verdict"] == "pending ear" and "s" not in rec["training_dis"]
    assert _ids(q, "di_sample", "s") == {t: iid}                  # still asked
    rec, q = env.run([env.export([(iid, "clean", "")], exported="2026-10-24T09:00:00Z")], drop=True)
    assert rec["dis"]["s"]["verdict"] == "verified" and rec["training_dis"] == ["s"]


def test_a_clean_window_clears_only_the_flagged_section_it_covers(tmp_path, monkeypatch):
    pytest.importorskip("numpy")                           # lists -> prior_summary
    env = _Lists(tmp_path, monkeypatch, [_di("x", "B1", [_sec("x1", 30.0, crest=6.0),
                                                         _sec("x@35.0", 35.0, crest=6.0, own=False),
                                                         _sec("x3", 60.0)])])
    rec, q = env.run()
    fl = _ids(q, "di_flagged", "x")
    assert sorted(fl) == [30.0, 35.0]
    assert rec["dis"]["x"]["verdict"] == "pending ear"           # the DI waits while a flagged window is unheard
    assert set(rec["dis"]["x"]["sections"].values()) == {"pending ear"} and rec["training_dis"] == []
    rec, q = env.run([env.export([(fl[30.0], "clean", "")])])
    assert rec["dis"]["x"]["sections"]["x@35.0"] == "pending ear" and 35.0 in _ids(q, "di_flagged", "x")
    assert rec["dis"]["x"]["verdict"] == "pending ear"
    rec, q = env.run([env.export([(fl[30.0], "clean", ""), (fl[35.0], "clean", "")], exported="2026-10-24T09:00Z")])
    assert rec["dis"]["x"]["verdict"] == "verified"
    assert set(rec["dis"]["x"]["sections"].values()) == {"usable"} and q["queue"] == []


def test_notes_are_kept_and_a_retracted_answer_clears(tmp_path):
    reg = {"ear-y": {"kind": "di_flagged", "family": "di", "key": "d", "start_s": 30.0, "dur_s": 10.0},
           "ear-z": {"kind": "di_flagged", "family": "di", "key": "e", "start_s": 30.0, "dur_s": 10.0}}

    def ex(name, ans, exported):                                  # the page stamps every touched card with its time
        p = tmp_path / name
        p.write_text(json.dumps({"page": V.EAR_PAGE, "part": 3, "build": "b1", "exported": exported,
                                 "answers": [{"id": i, "verdict": v, "note": n, "t": exported} for i, v, n in ans]}))
        return p
    half = ex("half.json", [("ear-y", "processed", ""), ("ear-z", "clean", "")], "2026-10-24T08:00")
    final = ex("final.json", [("ear-y", "clean", "the crunch is the pick"), ("ear-z", None, "not sure any more")],
               "2026-10-24T09:00")
    e = V.ear_answers([final, half], [], reg)                     # the later export wins whatever the order
    assert e["di_windows"] == {"d": [(30.0, 40.0, "clean")]} and e["superseded"] == 2
    assert [(n["id"], n["verdict"], n["note"]) for n in e["notes"]] == [
        ("ear-y", "clean", "the crunch is the pick"), ("ear-z", None, "not sure any more")]


def test_sample_redraws_past_a_di_the_measures_exclude():
    rows = {"p": _di("p", "B", [_sec("p1", 10.0)]), "q": _di("q", "B", [_sec("q1", 10.0)]),
            "r": _di("r", "C", [_sec("r1", 10.0)])}
    before = V.sample_passed(rows)
    bad = next(d for d in before if rows[d]["band"] == "B")
    rows[bad]["hum_suspect"] = True                                # D2 fails: the draw would hear nothing for B
    after = V.sample_passed(rows)
    assert set(after) == ({"p", "q"} - {bad}) | {"r"} and after["r"] == before["r"]


def test_a_measure_di_heard_processed_on_another_window_excludes_its_crop(tmp_path, monkeypatch):
    pytest.importorskip("numpy")                           # lists -> prior_summary
    crop = {"window_s": 100.0, "di_file": "/x/B1_Full/x.wav", "inventory_di": "x", "di_name": "x.wav",
            "d2": {"flags": []}, "d4": {"crest_db": 12.0, "bright_slope": 0.5}}
    env = _Lists(tmp_path, monkeypatch, [_di("x", "B1", [_sec("x1", 10.0, crest=6.0)])], {"Song-x": crop})
    rec, q = env.run()
    assert rec["measure_dis"]["Song-x"]["verdict"] == "pending ear"          # unheard: every DI is heard first
    rec, _ = env.run([env.export([(_ids(q, "di_flagged", "x")[10.0], "processed", "")])])
    assert rec["measure_dis"]["Song-x"]["verdict"] == "excluded"


def test_an_unheard_measure_di_waits_and_counts_once_its_file_is_heard_clean(tmp_path, monkeypatch):
    pytest.importorskip("numpy")                           # lists -> prior_summary
    crop = {"window_s": 100.0, "di_file": "/x/B1_Full/x.wav", "inventory_di": "x", "di_name": "x.wav",
            "d2": {"flags": []}, "d4": {"crest_db": 12.0, "bright_slope": 0.5}}
    env = _Lists(tmp_path, monkeypatch, [_di("x", "B1", [_sec("x1", 10.0)])], {"Song-x": crop})
    rec, q = env.run()                       # (its card is queued with its target's; this fake has no target)
    md = rec["measure_dis"]["Song-x"]
    assert md["verdict"] == "pending ear" and md["why"][0].startswith("unheard")
    (sid,) = _ids(q, "di_sample", "x").values()                    # the same DI file heard clean on another window
    rec, _ = env.run([env.export([(sid, "clean", "")])])
    assert rec["measure_dis"]["Song-x"]["verdict"] == "verified"


def test_calibration_ok_needs_todays_negatives_and_known_amps(tmp_path):
    (tmp_path / "calibration").mkdir()
    rec = {"verdict": "OK", "smoke": False, "thresholds": V.thresholds(), "negatives": V.NEG_DECLARED,
           "must_fail": {k: list(v) for k, v in V.NEG_MUST_FAIL.items()}, "known_amps": {"parts": list(V.KNOWN_AMPS)}}
    (tmp_path / "calibration" / "calibration.json").write_text(json.dumps(rec))
    assert V.calibration_ok(tmp_path)[0]
    rec["must_fail"] = {"copy": ["A1"]}                            # an OK from before a negative was added
    (tmp_path / "calibration" / "calibration.json").write_text(json.dumps(rec))
    assert not V.calibration_ok(tmp_path)[0]


def test_a_quiet_window_is_retired_and_holds_no_di_back(tmp_path, monkeypatch):
    pytest.importorskip("numpy")                           # lists -> prior_summary
    env = _Lists(tmp_path, monkeypatch, [_di("x", "B1", [_sec("x1", 10.0), _sec("x@40.0", 40.0, crest=6.0, own=False)])])
    rec, q = env.run()
    (t, iid), = _ids(q, "di_flagged", "x").items()
    assert rec["dis"]["x"]["verdict"] == "pending ear"
    (env.root / "t0" / "quiet-items.json").write_text(json.dumps({"items": {iid: {"key": "x", "start_s": t, "share": 0.0}}}))
    rec, q = env.run()
    assert rec["dis"]["x"]["sections"]["x@40.0"] == "silent"
    assert rec["dis"]["x"]["why"] == ["sampled for the ear (D4 passed)"]   # only its own sample is left to hear
    reg = json.loads((env.root / "t0" / "ear-items.json").read_text())
    assert "quiet" in reg[iid]["retired"] and [i["kind"] for i in q["queue"]] == ["di_sample"]


def test_every_di_is_heard_before_it_counts(tmp_path, monkeypatch):
    pytest.importorskip("numpy")                           # lists -> prior_summary
    env = _Lists(tmp_path, monkeypatch, [_di("p", "B1", [_sec("p1", 10.0)]), _di("q", "B1", [_sec("q1", 20.0)])])
    rec, q = env.run()
    samples = {x["key"]: x for x in q["queue"] if x["kind"] == "di_sample"}
    assert set(samples) == {"p", "q"} and rec["training_dis"] == []        # the band's draw and the other DI
    assert {rec["dis"][d]["verdict"] for d in "pq"} == {"pending ear"}
    rec, q = env.run([env.export([(samples["p"]["id"], "clean", ""), (samples["q"]["id"], "clean", "")])])
    assert rec["training_dis"] == ["p", "q"] and q["queue"] == []


def test_a_sessions_stems_count_once_its_spot_check_is_heard_clean(tmp_path, monkeypatch):
    pytest.importorskip("numpy")                           # lists -> prior_summary
    sd = "/x/B1_Full"
    stems = {sd: {"stems": {"01_Kick.wav": {"pass": True, "takes_db": {"g": -45.0}},
                            "02_Vox.wav": {"pass": True, "takes_db": {"g": -31.0}},
                            "03_Room.wav": {"pass": False, "takes_db": {"g": -25.0}}}}}
    monkeypatch.setattr(V, "stem_activity", lambda path, times: {t: 0.8 if t == 20.0 else 0.0 for t in times})
    env = _Lists(tmp_path, monkeypatch, [_di("x", "B1", [_sec("x1", 10.0), _sec("x2", 20.0)])], stems=stems)
    rec, q = env.run()
    (item,) = [x for x in q["queue"] if x["kind"] == "stem"]
    assert item["key"] == f"{sd}|02_Vox.wav" and item["start_s"] == 20.0     # nearest the floor, where it plays
    assert rec["stems"] == {}                                                 # waits for the ear
    rec, q = env.run([env.export([(item["id"], "clean", "")])])
    assert rec["stems"] == {sd: ["01_Kick.wav", "02_Vox.wav"]} and rec["stem_checks"][sd]["heard"] is True
    rec, q = env.run([env.export([(item["id"], "guitar", "")], exported="2026-10-24T09:00:00Z")], drop=True)
    assert rec["stems"] == {}                                                 # a guitar heard: the session's stems held
    stored = json.loads((env.root / "t0" / V.STEM_CHECK_FILE).read_text())["sessions"][sd]
    assert stored["stem"] == "02_Vox.wav"                                     # the choice is kept between runs


def test_a_note_from_another_browser_is_flagged_not_silent(tmp_path):
    reg = {"ear-y": {"kind": "di_flagged", "family": "di", "key": "d", "start_s": 30.0, "dur_s": 10.0}}

    def ex(name, ans):
        p = tmp_path / name
        p.write_text(json.dumps({"page": V.EAR_PAGE, "part": 3, "build": "b1", "exported": ans[-1],
                                 "answers": [{"id": "ear-y", "verdict": ans[0], "note": ans[1], "t": ans[2]}]}))
        return p
    phone = ex("phone.json", ("processed", "", "2026-10-24T08:00"))
    laptop = ex("laptop.json", (None, "pick noise?", "2026-10-24T09:00"))
    e = V.ear_answers([phone, laptop], [], reg)
    assert e["cleared"] == [{"id": "ear-y", "verdict": "processed", "file": str(phone), "by": str(laptop),
                             "note": "pick noise?"}]
