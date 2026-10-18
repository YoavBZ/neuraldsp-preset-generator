"""The rebuild-tone step's pure parts (docs/rebuild-tone-plan.md): binding stage TR's machinery,
the leak-free curve's exclusions, the EQ arm, the gate rule, pooling, the extension rule and the
no-high-bleed row. No renders."""

import math

import numpy as np
import pytest

from learn import local_objective as LO
from learn import rebuild_gap as G
from learn import rebuild_tone as RT

SR = 48000


def test_bound_restores():
    out, arms = G.OUT, G.ARMS
    with RT.bound():
        assert G.OUT == RT.OUT and set(RT.ARMS) <= set(G.ARMS)
        assert all(G.is_arm(a) for a in RT.ARMS) and G.is_arm(RT.COMPARATOR_ARM) and not G.is_arm("arm_ctl")
    assert G.OUT == out and G.ARMS == arms
    with pytest.raises(ValueError):
        with RT.bound(RT.TR_OUT, RT.TR_ARMS):
            assert G.OUT == RT.TR_OUT
            raise ValueError
    assert G.OUT == out and G.ARMS == arms


def test_arm_comparator_scores_as_an_arm_under_bound():
    """`rebuild_gap.comparator` scores C′'s rebuild at S as "arm_rank" with no "measure" signal; under
    `bound()` that must take the arm path (1b's configuration), not the probe path (review item 1)."""
    import inspect

    assert '"arm_rank"' in inspect.getsource(G.comparator) and RT.COMPARATOR_ARM == "arm_rank"
    seen = []

    def aligned(rec, y, mask, lag, a, b):
        seen.append(lag)
        return 0.5, None

    sig = {"di": np.zeros(10), "reference": np.zeros(10)}
    with RT.bound():
        s = G.score_one(np.zeros(10), "arm_rank", sig, 914, aligned)["decl"]
    assert s == {h: 0.5 for h in G.HALVES} and set(seen) == {G.OBJ_LAG}


def test_render_pattern_is_visible_to_other_jobs():
    import re

    cmd = "/x/.venv/bin/python -u -m learn.rebuild_tone render --stage tr1 --arms arm_stm --shard 0/3"
    assert any(re.search(p, cmd) for p in LO.RENDERS)


def test_own_di():
    rec = {"excluded_guitar_dis": ["23_ElecGtr1DI.wav", "25_ElecGtr2DI.wav"],
           "verified_source_sha256": {"25_ElecGtr2DI.wav": "a", "24_ElecGtr2.wav": "b", "01_Kick.wav": "c"}}
    assert RT.own_di(rec) == "25_ElecGtr2DI.wav"
    assert RT.own_di({}) is None


def test_excluded_files():
    files = {"/d/Doom - Blind Spots LFTL/GTR DI_TDP-1.wav": "Doom",
             "/d/Doom - Measurements LFTL/GTR DI_TDP-1.wav": "Doom",
             "/d/MR1003_Zeno_Full/25_ElecGtr2DI.wav": "Zeno",
             "/d/MR1003_Zeno_Full/23_ElecGtr1DI.wav": "Zeno",
             "/d/Other/GTR DI_TDP-1.wav": "Other",
             "/d/Eggy/x.wav": "Eggy", "/d/Eggy/y.wav": "Eggy"}
    tests = [("Doom", "Blind Spots", "GTR DI_TDP-1.wav"),        # a folder names the song: only it
             ("Zeno", "Signs", "25_ElecGtr2DI.wav"),               # no folder names it: the same-named file
             ("Eggy", "Fragments", None)]                          # no DI name: the whole band
    out = RT.excluded_files(files, tests)
    assert out == {"/d/Doom - Blind Spots LFTL/GTR DI_TDP-1.wav", "/d/MR1003_Zeno_Full/25_ElecGtr2DI.wav",
                   "/d/Eggy/x.wav", "/d/Eggy/y.wav"}


def test_curve_from_is_the_power_average_mean_removed():
    S = np.array([[0.0, 10.0, 20.0], [10.0, 10.0, 0.0], [99.0, 99.0, 99.0]])
    c = RT.curve_from(S, np.array([True, True, False]))
    ref = 10 * np.log10((10 ** (S[:2] / 10)).mean(0))
    assert np.allclose(c, ref - ref.mean()) and abs(c.mean()) < 1e-9


def _noise(n=SR * 4, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X *= 1 / np.sqrt(np.maximum(f, 50) / 50)                       # pink-ish
    return np.fft.irfft(X, n) * 0.05


def test_dep_eq_follows_the_curve_at_the_level():
    from learn import direc as D
    from learn.di_robustness import smoothed_spectrum

    x = _noise()
    fr = np.fft.rfftfreq(D.SPEC_N, 1 / D.SR)
    curve = -6 * np.log2(np.maximum(fr, 50) / 1000) / 3            # a tilt
    curve -= curve.mean()
    y = RT.dep_eq(x, curve)
    assert LO.lufs(y) == pytest.approx(-22.9, abs=0.01)
    own = smoothed_spectrum(y)
    m = (fr >= 100) & (fr <= 8000)
    d = (own - own.mean())[m] - curve[m]
    assert np.std(d) < 1.0
    probs, g, lu = RT.eq_problems(y, x)
    assert probs == [] and g == 0


def test_eq_problems_flags_shift_and_level():
    x = _noise()
    y = RT.dep_eq(x, np.zeros(2049))
    probs, g, _ = RT.eq_problems(np.roll(y, 40), x)
    assert abs(g) == 40 and any("GCC" in p for p in probs)
    probs, _, _ = RT.eq_problems(y * 2, x)
    assert any("loudness" in p for p in probs)


def _crop_rows(vals, band_of):
    return {(0, i): {"band": band_of(i), "recording": f"r{i % 7}", "est": v, "lsd": 1.0, "coh_1_3k": 0.4,
                     "coh_3_8k": 0.01} for i, v in enumerate(vals)}


def test_gate_contrast_and_rule():
    rng = np.random.default_rng(0)
    a = _crop_rows(6 + rng.normal(0, 0.1, 100), lambda i: f"b{i % 5}")
    lower = _crop_rows(5.5 + rng.normal(0, 0.1, 100), lambda i: f"b{i % 5}")
    c = RT.gate_contrast(lower, a, "est")
    assert c["band_weighted_mean"] < -0.3 and c["hi90"] < 0 and c["bands"] == 5 and c["crops"] == 100
    assert RT.gate_contrast(lower, a, "est", "recording")["bands"] == 7
    gate = {"contrasts": {"stm_s0-cprime": {"est": {"band": c}}}}
    assert RT.render_stm(gate)
    assert RT.render_stm({"contrasts": {"stm_s0-cprime": {"est": {"band": {**c, "hi90": 0.01}}}}})   # direction rule
    assert not RT.render_stm({"contrasts": {"stm_s0-cprime": {"est": {"band": {**c, "band_weighted_mean": 0.01}}}}})
    assert not RT.render_stm({})


def test_pooled():
    a = {("s", "PR12"): ("s", "b", "clean", 0.2), ("t", "PR12"): ("t", "b", "clean", None)}
    b = {("s", "PR12"): ("s", "b", "clean", 0.6), ("t", "PR12"): ("t", "b", "clean", 0.1)}
    assert RT.pooled(a, b) == {("s", "PR12"): ("s", "b", "clean", 0.4)}


def test_extension_rule():
    ratio = 0.948
    meets = {"band_weighted_mean": 0.10, "lo90": -0.002, "hi90": 0.202}       # 0.10 > 0.948 * 0.102
    misses = {"band_weighted_mean": 0.075, "lo90": -0.031, "hi90": 0.181}
    decided = {"band_weighted_mean": 0.2, "lo90": 0.05, "hi90": 0.35}
    rep = {"r1": {"arm_stm-cprime_ref": misses, "arm_stm-arm_ctl_stm": meets,
                  "arm_stm_eq-arm_cprime_eq": decided, "arm_cprime_eq-cprime_ref": misses,
                  "arm_rank_s1-cprime_ref": meets}}
    assert RT.extension(rep, ratio) == ["stm", "seed"]
    assert RT.extension({"r1": {}}, ratio) == []
    rep["r1"]["arm_cprime_eq-cprime_ref"] = meets
    assert RT.extension(rep, ratio) == ["stm", "eq", "seed"]                  # the declared priority order
    assert RT.j2_arms("eq", ["arm_cprime_eq", "arm_rank_s1"]) == ["arm_cprime_eq"]   # only arms rendered at J1


def test_groups_cover_the_declared_contrasts():
    for g, cs in RT.EXTEND_ON.items():
        for a, b in cs:
            assert a in RT.GROUPS[g] and (b in RT.GROUPS[g] or b == "cprime_ref")
    assert {a for g in RT.GROUPS.values() for a in g} == set(RT.ARMS)
    assert not set(RT.ARMS) & set(RT.TR_ARMS)
    for a, b in (*RT.PRIMARY, *RT.SEED_PRIMARY, *RT.SECONDARY):
        for n in (a, b):
            assert n in RT.ARMS or n in RT.TR_ARMS or n in ("cprime_ref", "rank_pooled", "ctl_pooled")


def test_high_bleed_rule(monkeypatch):
    from learn import knob_ceiling as K

    monkeypatch.setattr(K, "parts", lambda: {"a": {}, "b": {}, "c": {}})
    monkeypatch.setattr(LO, "EXCLUDED", set())
    table = {"a": {"halves": {"A": {"flag": "low"}, "B": {"flag": "high"}}},
             "b": {"halves": {"A": {"flag": "low"}, "B": {"flag": "moderate"}}}}
    assert RT.high_bleed(table) == ["a", "c"]


def test_renders_used_counts_warm_ups_once(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(RT, "OUT", tmp_path)
    d = tmp_path / "renders" / "arm_stm" / "s"
    d.mkdir(parents=True)
    (d / "PR12.json").write_text(json.dumps({"probe": "arm_stm", "renders": 49, "warm_ups": 1}))
    c = tmp_path / "comparator" / "arm"
    c.mkdir(parents=True)
    (c / "s-PR12.json").write_text("{}")
    assert RT.renders_used() == {"by_arm": {"arm_stm": 49}, "comparator": 2, "total": 51}
    assert not math.isnan(RT.renders_used()["total"])
