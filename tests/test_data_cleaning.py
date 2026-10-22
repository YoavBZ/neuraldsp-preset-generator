"""learn/data_cleaning.py: the pure parts of the data-cleaning plan's steps 0 and 1."""

import json
import math
import pathlib
import re

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import data_cleaning as C  # noqa: E402

LEDGER = pathlib.Path(__file__).resolve().parents[1] / "docs" / "dev-test-ledger.json"


# --- names ---------------------------------------------------------------------------------------------

def test_double_track_naming_pairs_only_dt_partners():
    assert C.name_partner("ElecGtr01", "10_ElecGtr01DT.wav")
    assert C.name_partner("ElecGtr01DT", "08_ElecGtr01.wav")
    assert C.name_partner("ElecGtr2", "28_ElecGtr2DT.wav")
    assert not C.name_partner("ElecGtr01", "08_ElecGtr01.wav")          # its own track
    assert not C.name_partner("ElecGtr01", "12_ElecGtr02DT.wav")        # another part's double
    assert not C.name_partner("ElecGtr2", "30_ElecGtr3.wav")
    assert C.part_base("16_ElecGtr03Amp1.wav") == "ElecGtr03"


def test_track_classes_are_for_reporting():
    assert C.track_class("06_DrumsRoom.wav") == "drums"
    assert C.track_class("Close Rooms U47 Stereo Set.wav") == "drums"
    assert C.track_class("Bass Amp_M82.wav") == "bass"
    assert C.track_class("VOX GTR.04_01.wav") == "vocal"
    assert C.track_class("Leslie Top TF11 Stereo Set_02.wav") == "keys"
    assert C.track_class("28_ElecGtr2DT.wav") == "guitar"


# --- the rule --------------------------------------------------------------------------------------------

def test_removal_takes_the_largest_first_until_the_sum_is_at_most_the_threshold():
    removed, before, after = C.removal({"a": -20.0, "b": -33.0, "c": -45.0, "d": None})
    assert removed == ["a"] and before > -30 and after <= -30
    # two tracks just under the threshold sum above it: the larger leaves
    removed, _, after = C.removal({"x": -32.0, "y": -32.5})
    assert removed == ["x"] and after == pytest.approx(-32.5)
    # takes under the floor count as none
    assert C.removal({"x": -41.0, "y": -41.0})[0] == []
    # a same-part track with no amp reference is always removed
    assert C.removal({"x": math.inf, "y": -50.0})[0] == ["x"]
    assert C.removal({})[0] == [] and C.removal({"x": -30.0})[0] == []


def test_same_part_needs_a_candidate_and_pitch():
    assert C.same_part(0.9, 0.1, 0.5, True)                     # named double, same notes
    assert not C.same_part(0.5, 0.9, 0.5, True)                 # named, but other notes
    assert C.same_part(0.75, 0.65, 0.9, False)                  # onsets >= 0.6
    assert C.same_part(0.75, 0.3, 0.25, False)                  # follows the DI as well as the own amp
    assert not C.same_part(0.75, 0.2, 0.25, False)              # no candidate
    assert not C.same_part(None, 0.9, 0.5, True)


def test_track_take_uses_power_for_same_part_and_the_session_take_otherwise():
    sp = {"same_part": True, "power_db": {"A": -3.0, "B": -5.0}, "take_amp_db": -50.0}
    other = {"same_part": False, "power_db": {"A": -3.0, "B": -5.0}, "take_amp_db": -27.0}
    assert C.track_take(sp, True) == -3.0 and C.track_take(sp, False) == math.inf
    assert C.track_take(other, True) == -27.0 and C.track_take(other, False) is None


def test_a_section_row_decides_its_removals():
    row = {"source": {"kind": "amp"}, "tracks": {
        "dt": {"same_part": True, "power_db": {"A": -1.0, "B": None}, "take_amp_db": None},
        "room": {"same_part": False, "power_db": {"A": 3.0, "B": 2.0}, "take_amp_db": -22.0},
        "kick": {"same_part": False, "power_db": {"A": 0.0, "B": 0.0}, "take_amp_db": None}}}
    removed, _, after = C.section_decision(row)
    assert removed == ["dt", "room"] and after == -math.inf


def test_an_example_is_untrusted_only_if_its_own_variant_loses_a_track():
    assert C.touched(["vox"], ["kick", "vox"]) and not C.touched(["vox"], ["kick"])
    assert not C.touched([], ["kick"])


def test_route_drops_only_a_small_share():
    assert C.route(0.05) == "drop" and C.route(0.0501) == "rebuild"


def test_injection_verdict():
    good = [{"base": None, "inj": {-20.0: -21.0, -25.0: -26.0, -30.0: -31.5}, "others": {"k": None, "s": -38.0}}
            for _ in range(12)]
    assert C.injection_verdict(good)[0] == "OK"
    bad_at_30 = [dict(r, inj={-20.0: -21.0, -25.0: -26.0, -30.0: -34.0}) for r in good[:3]] + good[3:]
    v, shares, _, _ = C.injection_verdict(bad_at_30)
    assert v == "FAIL" and shares[-30.0] == pytest.approx(0.75)
    fp = [dict(r, others={"k": -29.0}) for r in good[:2]] + good[2:]
    assert C.injection_verdict(fp)[0] == "FAIL"                # 2 of 23 others at or above -30 dB
    base = [dict(r, base=-30.0) for r in good[:2]] + good[2:]
    assert C.injection_verdict(base)[0] == "FAIL"
    assert C.injection_verdict([])[0] == "FAIL"


# --- signals ----------------------------------------------------------------------------------------------

def _session(seconds=40.0, seed=0):
    """A "guitar" that never repeats (noise under a random, piecewise envelope: the nulls cannot follow it)
    and an unrelated backing track."""
    rng = np.random.default_rng(seed)
    n = int(seconds * C.AN_SR)
    seg = int(0.2 * C.AN_SR)
    env = np.repeat(rng.uniform(0.0, 1.0, n // seg + 1) ** 2, seg)[:n]
    src = (env * rng.standard_normal(n)).astype(np.float32)
    other = rng.standard_normal(n).astype(np.float32)
    return src, other


def test_the_take_estimator_reads_an_injected_path_and_not_an_unrelated_track():
    src, other = _session()
    idx, _ = C.band_bins()
    S = C.stft(src)[idx]
    reader = C.TakeReader(S, S)
    rng = np.random.default_rng(3)
    from scipy.signal import fftconvolve

    c = fftconvolve(src, C.room_ir(rng))[:len(src)].astype(np.float32)
    Cs = C.stft(c)[idx]
    unit = float(np.sum(np.abs(Cs[:, reader.counted]) ** 2)) / reader.ref
    ys = {"none": C.stft(other)[idx]}
    for L in (-15.0, -25.0):
        g = math.sqrt(10 ** (L / 10) / unit)
        ys[L] = C.stft(other + g * c)[idx]
    takes = reader.takes(ys)
    assert takes["none"] is None or takes["none"] < -35
    assert abs(takes[-15.0] - (-15.0)) < 3.0
    assert abs(takes[-25.0] - (-25.0)) < 3.0


def test_take_db_subtracts_the_nulls_and_needs_something_left():
    assert C.take_db(10.0, [0.0, 0.0], 1000.0) == pytest.approx(-20.0)
    assert C.take_db(10.0, [-10.0, -10.0], 1000.0) == pytest.approx(10 * math.log10(20 / 1000))
    assert C.take_db(-5.0, [-10.0], 1000.0) == pytest.approx(10 * math.log10(5 / 1000))
    assert C.take_db(5.0, [6.0], 1000.0) is None and C.take_db(5.0, [], 0.0) is None


def test_null_rolls_stay_inside_short_sessions():
    assert C.null_rolls(10_000) == [round(2 * C.AN_SR / C.HOP), -round(2 * C.AN_SR / C.HOP),
                                    round(3 * C.AN_SR / C.HOP), -round(3 * C.AN_SR / C.HOP)]
    assert all(abs(r) <= 25 for r in C.null_rolls(100))


def test_lagged_shifts_frames():
    S = np.arange(12, dtype=np.complex64).reshape(2, 6)
    X = C.lagged(S, (-1, 0, 2))
    assert np.array_equal(X[:, :, 1], S)
    assert np.array_equal(X[:, :5, 0], S[:, 1:]) and X[0, 5, 0] == 0
    assert np.array_equal(X[:, 2:, 2], S[:, :4]) and np.all(X[:, :2, 2] == 0)


def test_chroma_and_onsets_tell_same_notes_from_other_notes():
    sr, n = C.AN_SR, int(10 * C.AN_SR)
    t = np.arange(n) / sr
    gate = (np.floor(t * 2) % 2 == 0).astype(np.float32)        # 0.5-s on, 0.5-s off
    a = gate * np.sin(2 * np.pi * 220 * t)
    b = gate * (0.7 * np.sin(2 * np.pi * 220 * t + 1.0) + 0.1 * np.sin(2 * np.pi * 440 * t))
    c = gate * np.sin(2 * np.pi * 311.1 * t)                     # a tritone away
    ca, cb, cc = C.chroma(a), C.chroma(b), C.chroma(c)
    assert C.chroma_sim(ca, cb) > 0.9 and C.chroma_sim(ca, cc) < 0.3
    assert C.best_corr(C.onset_env(a), C.onset_env(b)) > 0.9
    assert C.chroma_sim((np.zeros((0, 12)), np.zeros(0)), cb) is None


# --- step 1 -----------------------------------------------------------------------------------------------

def test_the_rebuilt_backing_keeps_the_drawn_ratio():
    from learn import pretrain_set as PS

    lg, ratio, leak, target = -20.0, -8.0, 3.0, -14.0
    lb_old, lb_new = -18.0, -21.5
    gb, _, ga = PS.mix_gains_db(lg, lb_old, ratio, leak, target)
    gb2, _, ga2 = PS.mix_gains_db(lg, lb_new, ratio, leak, target)
    assert C.rebuilt_gain_db(gb, lb_old, lb_new, lg) == pytest.approx(gb2) and ga == pytest.approx(ga2)
    # the 40-dB lift cap of mix_gains_db
    gb3, _, _ = PS.mix_gains_db(lg, -75.0, ratio, leak, target)
    assert C.rebuilt_gain_db(gb, lb_old, -75.0, lg) == pytest.approx(gb3)


def test_assemble_matches_the_build():
    y, b = np.ones(4), np.full(4, 2.0)
    assert np.allclose(C.assemble(y, b, 0.0, 0.0), 3.0)
    assert np.allclose(C.assemble(y, b, -6.0206, 6.0206), (1 + 1.0) * 2.0, atol=1e-3)


def test_parity_needs_cells_and_lufs():
    stored = {"mA": np.full((2, 3), 10, np.uint8), "mB": np.full((2, 3), 10, np.uint8), "lufs": [-14.0, -15.0]}
    ok = C.parity({"A": stored["mA"], "B": stored["mB"] + 1}, {"A": -14.0, "B": -15.005}, stored)
    assert ok[0] and ok[1] == 1.0
    assert not C.parity({"A": stored["mA"], "B": stored["mB"] + 2}, {"A": -14.0, "B": -15.0}, stored)[0]
    assert not C.parity({"A": stored["mA"], "B": stored["mB"]}, {"A": -14.0, "B": -15.02}, stored)[0]


def test_section_interval_clusters_by_section():
    a = {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.5}
    b = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    sec = {1: "s1", 2: "s1", 3: "s2", 4: "s2"}
    m, lo, hi, k = C.section_interval(a, b, sec, set(a))
    assert k == 2 and m == pytest.approx((0.15 + 0.4) / 2) and lo < m < hi
    assert C.section_interval(a, b, {i: "s" for i in a}, set(a)) is None


# --- hygiene -----------------------------------------------------------------------------------------------

def test_the_ledger_has_the_entry_and_runs_need_it():
    assert f'"{C.LEDGER_ID}"' in LEDGER.read_text()
    entry = next(t for t in json.loads(LEDGER.read_text())["tests"] if t["test_id"] == C.LEDGER_ID)
    assert entry["plan"] == C.PLAN and (LEDGER.parent.parent / entry["plan"]).exists()


def test_smoke_flags_need_a_scratch_root():
    import argparse

    with pytest.raises(SystemExit):
        C.require_real(argparse.Namespace(smoke=True, out=None, limit=0))
    with pytest.raises(SystemExit):
        C.require_real(argparse.Namespace(smoke=False, out=None, limit=2))
    C.require_real(argparse.Namespace(smoke=True, out="/tmp/x", limit=2))


def test_only_the_pool_rebuild_renders():
    from learn import local_objective as LO

    for cmd in ("inject", "scan --shard 0/3", "lists", "rin-rebuild --device mps", "rin-read", "pool-candidates",
                "pool-status"):
        assert not any(re.search(p, f"python -m learn.data_cleaning {cmd}") for p in LO.RENDERS)
    assert any(re.search(p, "python -m learn.data_cleaning pool-rebuild --device mps") for p in LO.RENDERS)


# --- step 2's data: the candidate-driven pool rebuild ---------------------------------------------------------

def _scan_row(sid, di, tracks, variants=None, band="B"):
    return {"section": sid, "di": di, "band": band, "source": {"kind": "amp"}, "onset_own": 0.5,
            "variants": variants or {"v": list(tracks), "n": [t for t in tracks if "vox" not in t]},
            "tracks": tracks}


def _secs():
    ex = lambda i, part, vocals, tag=None, refused=False: {  # noqa: E731
        "i": i, "part": part, "band": "B", "early_stop": False, "split": "train", "tag": tag, "vocals": vocals,
        "refused": refused}
    return {"s1": [ex(1, "pilot", False), ex(2, "rest", True), ex(3, "rest", False, refused=True)],
            "s2": [ex(4, "rest", True), ex(1000001, "vsep", True)]}


def test_candidates_split_doubles_from_takes_and_count_examples():
    dt = {"same_part": True, "power_db": {"A": -2.0, "B": -3.0}, "take_amp_db": None, "chroma": 0.95,
          "onset": 0.4, "partner": True, "class": "guitar"}
    room = {"same_part": False, "power_db": {"A": 2.0, "B": 2.0}, "take_amp_db": -20.0, "chroma": 0.1,
            "onset": 0.2, "partner": False, "class": "drums"}
    vox = {"same_part": False, "power_db": {"A": 0.0, "B": 0.0}, "take_amp_db": -25.0, "chroma": 0.2,
           "onset": 0.1, "partner": False, "class": "vocal"}
    rows = {"s1": _scan_row("s1", "d1", {"dt": dt, "room": room}),
            "s2": _scan_row("s2", "d1", {"dt": dt, "room": dict(room, take_amp_db=-50.0), "vox": vox})}
    cands = C.candidates_from(rows, _secs())
    by = {(c["track"], c["kind"]): c for c in cands}
    assert by[("dt", "double")]["rebuild"] and by[("dt", "double")]["sections"] == ["s1", "s2"]
    assert by[("dt", "double")]["pool_examples"] == 3 and by[("dt", "double")]["r_in_examples"] == 1
    assert not by[("room", "take")]["rebuild"] and by[("room", "take")]["sections"] == ["s1"]
    assert by[("vox", "take")]["pool_examples"] == 1                   # only the with-vocals example of s2
    assert cands[0]["kind"] == "double" and by[("dt", "double")]["verdict"] is None


def test_the_plan_follows_the_switched_on_candidates_and_each_examples_variant():
    variants = {"s1": {"v": ["dt", "vox"], "n": ["dt"]}, "s2": {"v": ["dt", "vox"], "n": ["dt"]}}
    cands = [{"track": "dt", "sections": ["s1", "s2"], "rebuild": True},
             {"track": "vox", "sections": ["s2"], "rebuild": True},
             {"track": "room", "sections": ["s1"], "rebuild": False}]
    plan = C.example_plan(C.desired_removals(cands), _secs(), variants)
    assert plan == {1: ["dt"], 2: ["dt"], 4: ["dt", "vox"]}             # no refused, no V_sep example
    cands[0]["rebuild"] = False
    assert C.example_plan(C.desired_removals(cands), _secs(), variants) == {4: ["vox"]}


def test_pool_state_builds_and_unbuilds_the_difference():
    k = C.removal_key
    assert k(["a", "b"]) == k(["b", "a"]) != k(["a"])
    built = {(1, k(["dt"])): {"i": 1, "key": k(["dt"])}, (2, k(["dt"])): {"i": 2, "key": k(["dt"])},
             (5, k(["x"])): {"i": 5, "key": k(["x"]), "refused": "the original re-mix differs"}}
    to_build, current, stale = C.pool_state({1: ["dt"], 4: ["dt", "vox"], 5: ["x"]}, built)
    assert set(current) == {1} and to_build == {4: ["dt", "vox"]} and set(stale) == {2}
    # a candidate switched off: its rebuilds go stale and the examples read their originals again
    to_build, current, stale = C.pool_state({}, built)
    assert not to_build and not current and set(stale) == {1, 2}
    # a refused rebuild is not retried
    assert 5 not in C.pool_state({5: ["x"]}, built)[0]


def test_declared_constants():
    assert C.TAKE_DB == -30.0 and C.FLOOR_DB == -40.0 and C.CHROMA_MIN == 0.70 and C.ONSET_MIN == 0.60
    assert C.INJECT_DB == (-20.0, -25.0, -30.0) and C.INJECT_N == 12 and C.INJECT_SEED == 20261097
    assert C.DROP_MAX_SHARE == 0.05 and C.STEP_SEP == "xlance_g" and C.DISK_GUARD_GB == 31.0
    assert len(C.DEV_DIS) == 4
