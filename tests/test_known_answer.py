"""B1's pure parts (`learn/known_answer.py`, `docs/known-answer-b1-plan.md`)."""

import math
import random

import pytest

from learn import known_answer as M


def _r(start, disjoint=False, flags=()):
    return {"start_s": start, "disjoint": disjoint, "flags": list(flags)}


def test_eligible_prefers_clean_then_noisy_non_overlapping():
    clean = [_r(s, True) for s in (0, 10, 20, 30)]
    assert M.eligible(clean) == ([0, 10, 20, 30], False)
    rows = [_r(0, True), _r(5, flags=["hum"]), _r(10, flags=["hum", "hiss"]), _r(15, flags=["hum"]),
            _r(20, flags=["clipping"]), _r(30, flags=["hum"]), _r(40, flags=["bleed", "hum"])]
    starts, noisy = M.eligible(rows)
    assert noisy and starts == [0, 10, 30]                   # greedy, non-overlapping, hum/hiss only


def test_primary_di_rule():
    rows = {"b": [_r(0, True), _r(10, True)], "a": [_r(0, True), _r(10, True)], "c": [_r(0, flags=["hum"])]}
    assert M.primary_di(rows) == "a"
    rows["c"] = [_r(10 * k, True) for k in range(3)]
    assert M.primary_di(rows) == "c"
    noisy = {"g1": [_r(10 * k, flags=["hum"]) for k in range(6)], "g2": [_r(0, True)] + [_r(10 * k + 10, flags=["hum"]) for k in range(2)]}
    assert M.primary_di(noisy) == "g2"                        # clean sections first


def test_switch_point_rests_and_sides():
    hop = 0.1
    n_s = 100.0
    play = [True] * int(n_s / hop)
    for k in range(int(39.9 / hop), int(40.1 / hop) + 1):
        play[k] = False
    starts = [0.0, 10.0, 60.0, 80.0]
    b, rests = M.switch_point(starts, n_s, play, hop)
    assert b == 40.0 and rests                                # the nearest resting boundary
    b2, rests2 = M.switch_point(starts, n_s, [True] * len(play), hop)
    assert b2 == 50.0 and not rests2                          # the middle, crossfaded
    with pytest.raises(ValueError):
        M.switch_point([60.0, 65.0], n_s, play, hop)


def test_draw_sections():
    starts = [0.0, 10.0, 20.0, 60.0, 80.0]
    s = M.draw_sections(starts, 50.0, "x")
    assert s["s3"] + M.SEC_S <= 50.0 and s["s4"] >= 50.0
    assert len(set(s.values())) == 4 and s["s1"] < s["s2"]
    assert s == M.draw_sections(starts, 50.0, "x")
    with pytest.raises(ValueError):
        M.draw_sections([0.0, 60.0, 80.0], 50.0, "x")


def test_classes_amps_and_s_class():
    assert M.classes_for("clean") == ("clean", "crunch", "clean")
    assert M.classes_for("crunch") == ("crunch", "clean", "crunch")
    assert M.classes_for("edge") == ("edge", "crunch", "edge")
    assert M.s_class("edge") == "crunch" and M.s_class("clean") == "clean"
    for song in M.SONGS:
        a = M.draw_amps(song)
        assert a["P2"] != a["P1"] and a["Q"] != a["P1"]
    assert {v["cls"] for v in M.SONGS.values()} == {"clean", "edge", "crunch"}


def test_in_class_uses_the_scope_line():
    line = 0.05
    assert M.in_class("clean", {"class": "clean", "slope": 0.9}, line)
    assert M.in_class("crunch", {"class": "high-gain", "slope": 0.06}, line)
    assert not M.in_class("crunch", {"class": "high-gain", "slope": 0.01}, line)     # beyond crunch S
    assert not M.in_class("crunch", {"class": "clean", "slope": 0.9}, line)
    assert M.in_class("edge", {"class": "clean", "slope": 0.9}, line)
    assert M.in_class("edge", {"class": "crunch", "slope": 0.2}, line)
    assert not M.in_class("crunch", {"class": "crunch", "slope": None}, line)
    scan = {"S": {"class": "crunch", "slope": 0.05, "is_start": True}, "a": {"class": "clean", "slope": 0.8},
            "b": {"class": "high-gain", "slope": 0.0}, "c": {"class": "crunch", "slope": 0.3}}
    assert M.pools(scan, 0.05) == {"clean": ["a"], "crunch": ["c"]}


def test_role_amp_redraw():
    assert M.role_amp("pr12", ["pr12", "ac20"], "s", "P1") == "pr12"
    got = M.role_amp("pr12", ["ac20"], "s", "P1")
    assert got == "ac20"
    assert M.role_amp("pr12", [], "s", "P1") is None


class _Dim:
    def __init__(self, module, key, kind, lo=0.0, hi=1.0, values=()):
        self.module, self.key, self.kind, self.lo, self.hi, self.values = module, key, kind, lo, hi, values

    @property
    def name(self):
        return f"{self.module}/{self.key}"

    def to_unit(self, v):
        return (min(max(float(v), self.lo), self.hi) - self.lo) / (self.hi - self.lo)

    def from_unit(self, u):
        return self.lo + min(max(u, 0.0), 1.0) * (self.hi - self.lo)


def test_jitter_truth_and_edge_range():
    dims = [_Dim("parameters", "inputGain", "cont", -20, 12), _Dim("a", "t", "cont"), _Dim("a", "sw", "switch", values=("false", "true"))]
    base = {("parameters", "inputGain"): "-4", ("a", "t"): "0.95", ("a", "sw"): "true", ("x", "p"): "on"}
    fmt = lambda v: f"{v:.6g}"  # noqa: E731
    for seed in range(50):
        x = M.jitter_truth(random.Random(seed), dims, base, fmt)
        assert x[("a", "sw")] == "true" and x[("x", "p")] == "on"
        assert abs(dims[1].to_unit(x[("a", "t")]) - 0.95) <= 0.15 + 1e-9 and float(x[("a", "t")]) <= 1.0
        assert abs(dims[0].to_unit(x[("parameters", "inputGain")]) - 0.5) <= 0.15 + 1e-9
    x = M.jitter_truth(random.Random(0), dims, base, fmt, fixed={("parameters", "inputGain"): 0.25})
    assert math.isclose(dims[0].to_unit(x[("parameters", "inputGain")]), 0.25, abs_tol=1e-5)
    assert M.edge_gain_range([0.9, 0.1, 0.5]) == (0.1, 0.5)
    assert M.edge_gain_range([0.2, 0.4, 0.6, 0.8]) == (0.2, 0.5)
    with pytest.raises(ValueError):
        M.edge_gain_range([])


def test_backing_rules():
    files = ["01_Kick.wav", "09_ElecGtr1.wav", "10_ElecGtr1DI.wav", "11_ElecGtr1DT.wav", "12_ElecGtr1DTDI.wav",
             "08_Bass.wav", "19_LeadVox.wav", "VOX Chris M80.wav", "DRUM OH_TF51 Stereo Set.wav"]
    is_di = lambda f: "DI" in f and "Bass" not in f  # noqa: E731
    out = M.backing(files, {"09_ElecGtr1.wav"}, is_di, leaking=["DRUM OH_TF51 Stereo Set.wav"])
    assert out == ["01_Kick.wav", "11_ElecGtr1DT.wav", "08_Bass.wav", "19_LeadVox.wav", "VOX Chris M80.wav"]
    nov = M.backing(files, {"09_ElecGtr1.wav"}, is_di, vocals=False)
    assert "19_LeadVox.wav" not in nov and "VOX Chris M80.wav" not in nov
    nog = M.backing(files, {"09_ElecGtr1.wav"}, is_di, other_guitars=False)
    assert "11_ElecGtr1DT.wav" not in nog and "08_Bass.wav" in nog


def test_units_counts_and_shards():
    plan = {"songs": {s: {} for s in M.SONGS}}
    us = M.units(plan)
    a = [u for u in us if u[3] == "A"]
    o = [u for u in us if u[3] == "O"]
    assert len(a) == 3 * 8 + 10 and len(o) == 16
    assert M.items_for("apprehended") == [1, 2, 3, 4, 5] and 5 not in M.items_for("bourbon")
    assert M.expected_renders(plan) == (34 + 16) * 333 + 16 * 6
    gs = M.groups(plan)
    assert len(gs) == 16 * 3
    parts = [M.shard_groups(gs, (k, 3)) for k in range(3)]
    assert sorted(sum(parts, [])) == gs and all(len(p) == 16 for p in parts)
    assert M.truth_of("x", "s4") == "P2" and M.truth_of("x", "s3") == "P1"


def test_weighting_and_unit_log():
    rows = [("A", "s1", "u1", 0.1), ("A", "s1", "u1", 0.3), ("A", "s1", "u2", 0.0), ("A", "s2", "u1", -0.2),
            ("B", "s3", "u1", 0.05)]
    w = M.weighted(rows)
    # song s1: units (0.2, 0.0) -> 0.1; s2: -0.2; band A: -0.05; band B: 0.05
    assert math.isclose(w["mean"], 0.0, abs_tol=1e-12) and w["bands"] == 2
    r = {"held": "B", "output": "shrunk", "judge_shrunk": {"A": 1.0, "B": 0.5}}
    assert math.isclose(M.unit_log(r, {"A": 1.0, "B": 1.0}), math.log(0.5))
    assert M.unit_log({**r, "output": "S"}, {"A": 1.0, "B": 1.0}) == 0.0
    assert M.unit_log(r, {"A": 1.0, "B": math.inf}) is None


def test_b2_size():
    up, n = M.b2_songs(0.02, 3)
    assert math.isclose(up, 0.02 * math.sqrt(2 / 0.1026))
    assert n > 17
    up0, n0 = M.b2_songs(None, 1)
    assert up0 is None and 14 <= n0 <= 20                       # the 0.069 floor: about 17 songs
    assert M.b2_songs(0.001, 3)[1] == n0                       # a tiny SD falls back to the floor


def test_cprime_leak_assert():
    M.assert_cprime_unseen({"Eggy", "Zeno"})
    with pytest.raises(AssertionError):
        M.assert_cprime_unseen({"Eggy", "Chris Coltraine"})
    with pytest.raises(AssertionError):
        M.assert_cprime_unseen({"telefunken/Bourbon"})


def test_knob_errors():
    dims = [_Dim("p", "g", "cont", 0, 10), _Dim("a", "sw", "switch", values=("false", "true"))]
    e = M.knob_errors({"p/g": "5"}, {"p/g": "8", "a/sw": "true"}, {"p/g": "2"}, dims)
    assert set(e) == {"p/g"} and math.isclose(e["p/g"][0], 0.3) and math.isclose(e["p/g"][1], 0.6)
