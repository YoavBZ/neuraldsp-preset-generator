"""The note-versions read (`learn/note_versions.py`, note-rebuild-plan 12m): the versions' notes, the instrument check's
rule, the readings, the guard, the code (exactly one for every combination), the recommendations and the summary on
made-up numbers. Pure: runs on the light CI runner (no numpy) except the distance's tests, which skip without it."""
import itertools

import pytest

from learn import note_rebuild as N
from learn import note_versions as NV


def _n(on, pitch, off=None, amp=1.0):
    return {"on": on, "off": on + 0.4 if off is None else off, "pitch": pitch, "amp": amp, "bends": []}


def _iv(m, lo, hi):
    return {"mean": m, "lo90": lo, "hi90": hi}


def test_the_declared_constants():
    assert NV.VERSIONS == ("nv-true", "nv-asis", "nv-hand", "nv-loud", "nv-loud2", "nv-hand-loud")
    assert NV.BIN_FLOOR_DB == 60.0 and NV.GHOST_STEPS_DB == (0.0, -6.0, -12.0, -20.0) and NV.GHOST_INTERVAL == 12
    assert (NV.NEAR_MEAN, NV.NEAR_HI, NV.SHORT_LO, NV.GUARD) == (0.25, 0.50, 0.50, 0.05)
    assert NV.CODES == ("NV-loud", "NV-short", "NV-none", "NV-undecided") and set(NV.RECOMMENDATION) == set(NV.CODES)
    assert N.LOUD_GAMMA == (1.0, 2.0) and N.SOFT_DB == -3.0
    assert (NV.DECIDING_RING, NV.BESIDE_RING) == ("ring-soft", "ring-on")


def test_hand_notes_drop_only_unpaired_notes_and_add_none():
    truth = [_n(0.0, 60), _n(0.5, 64), _n(1.0, 67)]
    est = [_n(0.01, 60, amp=0.7), _n(0.02, 72, amp=0.3), _n(0.52, 64), _n(0.53, 64), _n(1.5, 69)]
    hand = NV.hand_notes(est, truth)
    assert [(n["on"], n["pitch"], n["amp"]) for n in hand] == [(0.01, 60, 0.7), (0.52, 64, 1.0)]
    assert all(h in est for h in hand) and len(hand) <= len(truth)
    vn = NV.version_notes(truth, est)
    assert vn["nv-true"] == (truth, None) and vn["nv-asis"] == (est, None) and vn["nv-loud"][1] == 1.0
    assert vn["nv-loud2"][1] == 2.0 and vn["nv-hand-loud"] == (hand, 1.0)


def test_the_ladder_rule():
    assert NV.ladder_passes(1.0, [3.0, 2.0, 1.5, 1.1])
    assert not NV.ladder_passes(1.0, [3.0, 2.0, 2.0, 1.1])          # every step must go down
    assert not NV.ladder_passes(1.2, [3.0, 2.0, 1.5, 1.1])          # -20 dB below the plain rebuild
    assert NV.ladder_outcome({"a": True, "b": True}, {"r": True}) == (True, False)
    assert NV.ladder_outcome({"a": True, "b": True}, {"r": False}) == (True, True)   # the real set reported only
    assert NV.ladder_outcome({"a": True, "b": False}, {"r": True}) == (False, None)  # a list fails: stop
    g = NV.ghost_notes([_n(1.0, 60)])
    assert g == [{"on": 1.0, "off": 1.4, "pitch": 72, "amp": 1.0, "bends": []}]


def test_set_numbers_over_clusters():
    rows = [("a", {"C": 1.0}), ("a", {"C": 3.0}), ("b", {"C": 4.0}), ("c", {"C": 6.0}), ("d", {"C": None})]
    got = NV.set_numbers(rows, "C")
    assert got["clusters"] == 3 and got["mean"] == pytest.approx(4.0)
    h = NV.t90(2) * 2.0 / 3 ** 0.5
    assert got["lo90"] == pytest.approx(4.0 - h) and got["hi90"] == pytest.approx(4.0 + h)
    assert NV.set_numbers([("a", {"C": 1.0})], "C") == {"mean": 1.0, "lo90": None, "hi90": None, "clusters": 1}


def test_the_readings():
    C = _iv(2.0, 1.0, 3.0)
    assert NV.set_reading(_iv(2.0, -0.1, 4.1), _iv(0.1, 0.0, 0.2)) == "cost not shown"    # never a pass
    assert NV.set_reading(None, None) == "cost not shown"
    assert NV.set_reading(C, _iv(0.5, 0.2, 1.0)) == "near"
    assert NV.set_reading(C, _iv(0.5, 0.2, 1.01)) == "undecided"        # the upper end over half of C's mean
    assert NV.set_reading(C, _iv(0.51, 0.2, 0.9)) == "undecided"        # the mean over a quarter
    assert NV.set_reading(C, _iv(1.5, 1.01, 2.0)) == "short"
    assert NV.set_reading(_iv(-2.0, -3.0, -1.0), _iv(0.0, -0.1, 0.1)) != "near"            # extras cheaper: not near


def test_the_guard():
    ok = NV.chord_guard([{"chord": (10, 10, 12), "soft": (5, 4, 6)}, {"chord": (8, 7, 8), "soft": (0, 0, 0)}])
    assert ok["chord"]["asis"] == 0.9 and ok["chord"]["loud"] == 0.85 and ok["chord"]["holds"]
    assert not ok["soft"]["holds"] and not ok["holds"]                  # soft notes found 1/6 less often
    assert NV.chord_guard([])["holds"]
    notes = [_n(0, 48), _n(0, 52), _n(0, 55), _n(1, 50), _n(1, 53), _n(1, 57), _n(2, 60)]
    assert NV.chord_indices(notes) == [0, 1, 2, 3, 4, 5] and NV.chord_indices(notes[:5]) == []


def test_turned_down_share_and_soft_notes():
    truth = [_n(0.0, 48), _n(0.0, 52), _n(1.0, 55)]
    est = [_n(0.0, 48, amp=1.0), _n(0.0, 52, amp=0.5), _n(1.0, 55, amp=0.9), _n(1.0, 67, amp=0.3)]
    assert NV.soft_indices(est, truth, 1.0) == [1]                     # half the amplitude: -6 dB
    assert NV.turned_down_share(est, truth, 1.0) == pytest.approx(1 / 3)
    assert NV.turned_down_share([], truth, 1.0) is None


def _read(lists, real, goat_ok=True, guard=True, lists2=None, real2=None):
    return {1.0: {"lists": lists, "real": real, "goat_ok": goat_ok, "guard": guard},
            2.0: {"lists": lists2 or lists, "real": real2 or real, "goat_ok": goat_ok, "guard": guard}}


def test_nv_code_cases():
    assert NV.nv_code(_read("near", "cost not shown")) == {"code": "NV-loud", "gamma": 1.0}
    assert NV.nv_code(_read("near", "reported only")) == {"code": "NV-loud", "gamma": 1.0}
    assert NV.nv_code(_read("short", "short", lists2="near", real2="near")) == {"code": "NV-loud", "gamma": 2.0}
    assert NV.nv_code(_read("near", "near", guard=False))["code"] != "NV-loud"
    assert NV.nv_code(_read("near", "near", goat_ok=False))["code"] != "NV-loud"
    assert NV.nv_code(_read("near", "short"))["code"] == "NV-short"
    assert NV.nv_code(_read("cost not shown", "near"))["code"] == "NV-none"
    assert NV.nv_code(_read("undecided", "undecided"))["code"] == "NV-undecided"
    assert NV.nv_code(_read("cost not shown", "short"))["code"] == "NV-short"   # the first that holds


def test_nv_code_every_combination_ends_in_exactly_one_code():
    readings = ("near", "short", "undecided", "cost not shown")
    real = readings + ("reported only",)
    seen = set()
    for l1, l2, r1, r2, goat, guard in itertools.product(readings, readings, real, real, (True, False),
                                                          (True, False)):
        if "cost not shown" in (l1, l2) and l1 != l2:
            continue                                                      # C does not depend on gamma
        if ("reported only" in (r1, r2)) and r1 != r2:
            continue
        got = NV.nv_code(_read(l1, r1, goat, guard, l2, r2))
        assert got["code"] in NV.CODES
        if got["code"] == "NV-loud":
            assert got["gamma"] in N.LOUD_GAMMA and (l1 == "near" or l2 == "near")
            assert got["gamma"] == 1.0 or l1 != "near" or r1 not in ("near", "cost not shown", "reported only")
        if "cost not shown" == l1:
            assert got["code"] != "NV-loud"                               # "cost not shown" never yields NV-loud
        seen.add(got["code"])
    assert seen == set(NV.CODES)


def test_recommendations_and_other_gap():
    r = _read("near", "undecided", goat_ok=True, guard=True)
    code = NV.nv_code(_read("undecided", "undecided", lists2="near"))
    assert code["code"] == "NV-undecided"
    rec = NV.recommendation(code, _read("undecided", "undecided", lists2="near"))
    assert rec["adopt_gamma"] == 2.0 and "listening page" in rec["text"]
    assert NV.recommendation({"code": "NV-loud", "gamma": 1.0}, r)["adopt_gamma"] == 1.0
    assert NV.recommendation({"code": "NV-none", "gamma": None}, r)["adopt_gamma"] is None
    assert "no second" in NV.RECOMMENDATION["NV-short"]
    assert NV.other_gap(_iv(0.5, 0.1, 0.9), _iv(1.0, 0.4, 1.6))
    assert not NV.other_gap(_iv(2.0, 1.0, 3.0), _iv(1.0, 0.4, 1.6))
    assert not NV.other_gap(_iv(0.5, 0.1, 0.9), _iv(1.0, -0.4, 2.4))
    assert NV.goat_not_worse(_iv(0.1, -0.1, 0.3)) and not NV.goat_not_worse(_iv(0.3, 0.1, 0.5))


def _window(st, cluster, asis, hand, loud, loud2, true=None):
    d = {"nv-asis": asis, "nv-hand": hand, "nv-loud": loud, "nv-loud2": loud2}
    if true is not None:
        d["nv-true"] = true
    return {"set": st, "cluster": cluster, "d": {"ring-soft": d, "ring-on": d},
            "guard": {1.0: {"chord": (5, 5, 5), "soft": (2, 2, 2)}, 2.0: {"chord": (5, 5, 5), "soft": (2, 2, 2)}}}


def test_summarise_read_on_made_up_numbers():
    lists = [_window("lists", f"l{i}", 4.0 + 0.1 * i, 2.0, 2.2 + 0.01 * i, 2.1, 1.5) for i in range(10)]
    real = [_window("real", f"r{i}", 8.0 + 0.01 * i, 8.0, 8.0, 8.0, 7.0) for i in range(6)]
    goat = [_window("goat", f"g{i}", 5.0, 5.0, 5.0 - 0.01 * (i % 3), 5.0) for i in range(6)]
    for w in goat:
        w.pop("guard")
    got = NV.summarise_read(lists + real + goat, False)
    assert got["readings"][1.0]["lists"] == "near" and got["code"] == {"code": "NV-loud", "gamma": 1.0}
    assert got["numbers"]["ring-soft"]["lists"]["C"]["clusters"] == 10
    assert got["other_gap"]                                              # E clear of zero and larger than C
    assert NV.summarise_read(lists + real + goat, True)["readings"][1.0]["real"] == "reported only"


# --- the distance (numpy) -------------------------------------------------------------------------------------------------

def test_floored_logmel_floors_each_side_and_leaves_logmel_distance_alone():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    sr = 48000
    t = np.arange(3 * sr) / sr
    di = 0.3 * np.sin(2 * np.pi * 220 * t) * np.exp(-t)
    y = 0.3 * np.sin(2 * np.pi * 220 * t) * np.exp(-1.2 * t)
    before = N.logmel_distance(di, y)
    f = NV.floored_logmel(di, y)
    assert N.logmel_distance(di, y) == before and np.isfinite(f)
    assert NV.floored_logmel(di, y, bin_floor_db=1e9) == pytest.approx(before)    # no floor: the old distance
    ghost = 0.3 * np.sin(2 * np.pi * 440 * t) * np.exp(-t)
    loud, quiet = NV.floored_logmel(di, y + ghost), NV.floored_logmel(di, y + 0.1 * ghost)
    assert loud > quiet > f                                               # a ghost raises it; a quieter one less
