"""B2's data (`learn/song_relabel.py`, docs/song-to-settings-soundspace-plan.md): the sensitivity
weights and the right-cab mask, the draws, anchors and probes, the record-like examples, the
mixture's parity with the bank, the sets, the repeat check and the disk and cap guards. Synthetic
inputs, plus the weights from the stored step-1.2 files where they exist."""

import json
import math
import random

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import knob_ceiling as K  # noqa: E402
from learn import song_diag as D  # noqa: E402
from learn import song_relabel as RL  # noqa: E402

INF = math.inf


def S_for(amp, right="true"):
    S = {("cabParameters", "leftCabActive"): "true", ("parameters", "outputGain"): "0"}
    for d in K.space(amp, S):
        S[(d.module, d.key)] = K.fmt(d.from_unit(0.5)) if d.kind in ("cont", "log") else d.values[0]
    S[("cabParameters", "rightCabActive")] = right
    return S


def label_x(amp, seed, right="true"):
    S = S_for(amp, right)
    x, lab = D.broad(K.space(amp, S), S, random.Random(seed))
    x[("cabParameters", "rightCabActive")] = right
    lab[RL.RIGHT_ACTIVE] = right
    return S, x, lab


# ------------------------------------------------------------------------------ the weights

def test_sens_medians_gate_right_cab_settings_by_the_base_switch():
    meta = [{"bases": {"S": {RL.RIGHT_ACTIVE: "true"}, "P0": {RL.RIGHT_ACTIVE: "false"}}}]
    res = [(0, {"amp": "pr12", "bases": {
        "S": {"delta": {"cabParameters/rightCabDistance": 0.3, "pr12Amp/pr12Bass": 0.4}},
        "P0": {"delta": {"cabParameters/rightCabDistance": 0.0, "pr12Amp/pr12Bass": 0.6}}}})]
    med = RL.sens_medians(meta, res)
    assert med["pr12"]["cabParameters/rightCabDistance"] == 0.3        # cab-off base left out
    assert med["pr12"]["pr12Amp/pr12Bass"] == pytest.approx(0.5)


def test_weight_table_divides_by_the_amp_mean_and_clips():
    med = {"a": 100.0, "b": 0.01, **{f"k{j}": 1.0 for j in range(8)}}
    t = RL.weight_table({"ac20": med})["ac20"]
    m = (100.0 + 0.01 + 8.0) / 10
    assert t["a"] == 4.0 and t["b"] == 0.25 and m > 4
    u = RL.weight_table({"pr12": {"a": 2.0, "b": 1.0, "c": 1.0}})["pr12"]
    assert u["a"] == pytest.approx(1.5) and u["b"] == pytest.approx(0.75)


def test_table_matches_plan_flags_any_difference():
    good = {a: dict(row) for a, row in RL.PLAN_TABLE.items()}
    assert RL.table_matches_plan(good) == []
    good["pr12"]["pr12Amp/pr12Treble"] = 2.3
    good["ac20"]["extra"] = 1.0
    bad = RL.table_matches_plan(good)
    assert {b[1] for b in bad} == {"pr12Amp/pr12Treble", "extra"}


def test_plan_table_has_37_settings_and_covers_every_space():
    assert sum(len(r) for r in RL.PLAN_TABLE.values()) == 37
    for amp in K.AMPS:
        names = {d.name for d in K.space(amp) if d.kind != "cat"}
        assert names == set(RL.PLAN_TABLE[amp]), amp


def test_weights_from_the_stored_step12_files_match_the_plan():
    if not (RL.DIAG / "sens.json").exists():
        pytest.skip("step 1.2's files are not on this machine")
    meta = json.loads((RL.DIAG / "sens.json").read_text())
    res = [(int(p.stem), json.loads(p.read_text())) for p in sorted((RL.DIAG / "sens").glob("*.json"))]
    assert RL.table_matches_plan(RL.weight_table(RL.sens_medians(meta, res))) == []


def test_label_weights_mask_the_right_cab_and_right_mic_when_off():
    from learn import song_model as M

    _, _, on = label_x("sw50r", 1, "true")
    _, _, off = label_x("sw50r", 1, "false")
    cw_on, sw_on, mic_on = RL.label_weights("sw50r", on, RL.PLAN_TABLE)
    cw_off, sw_off, mic_off = RL.label_weights("sw50r", off, RL.PLAN_TABLE)
    for n in RL.RIGHT_GATED:
        j = M.CONT.index(n)
        assert cw_on[j] == RL.PLAN_TABLE["sw50r"][n] and cw_off[j] == 0.0
    assert mic_on[M.CAT.index(RL.RIGHT_MIC)] == 1.0 and mic_off[M.CAT.index(RL.RIGHT_MIC)] == 0.0
    assert mic_off[M.CAT.index("cabParameters/leftMicType")] == 1.0          # mics keep B0's weight
    assert sw_on == sw_off                                                     # switches unaffected
    j = M.CONT.index("parameters/inputGain")
    assert cw_off[j] == cw_on[j] == 1.74
    assert all(cw_on[M.CONT.index(n)] == 0.0 for n in M.CONT if n not in on)   # other amps' settings


# ------------------------------------------------------------------------------ the relabel draw

def bank_examples(n_per=60, seed=0):
    rng = random.Random(seed)
    ex, i = [], 0
    for f in range(4):
        for a in K.AMPS:
            for c in RL.CLASSES:
                for k in range(n_per):
                    ex.append({"i": i, "fold": f, "amp": a, "class": c, "mode": "broad" if k % 2 else "jitter"})
                    i += 1
    ex.append({"i": RL.NEW_BASE, "fold": 0, "amp": "pr12", "class": "clean", "mode": "jitter"})
    rng.shuffle(ex)
    return ex


def test_cell_counts_round_250_over_6_cells():
    assert RL.cell_counts() == [42, 42, 42, 42, 41, 41]
    assert sum(RL.cell_counts()) == 250


def test_relabel_draw_is_seeded_balanced_and_bank_only():
    ex = bank_examples()
    a, b = RL.relabel_draw(ex), RL.relabel_draw(ex)
    assert a == b and len(a) == 1000 and len(set(a)) == 1000
    assert RL.NEW_BASE not in a
    by = {e["i"]: e for e in ex}
    for f in range(4):
        counts = {}
        for i in a:
            if by[i]["fold"] == f:
                counts[(by[i]["amp"], by[i]["class"])] = counts.get((by[i]["amp"], by[i]["class"]), 0) + 1
        assert sorted(counts.values()) == [41, 41, 42, 42, 42, 42]
        for cell, n in counts.items():
            modes = [by[i]["mode"] for i in a if by[i]["fold"] == f and (by[i]["amp"], by[i]["class"]) == cell]
            assert abs(modes.count("broad") - modes.count("jitter")) <= 1


def test_relabel_draw_alternation_passes_the_turn_when_a_mode_runs_out():
    ex = [{"i": i, "fold": f, "amp": a, "class": c, "mode": "broad" if i % 10 else "jitter"}
          for f in range(4) for a in K.AMPS for c in RL.CLASSES for i in [len(RL.CLASSES) * 1000 * f + 100 * K.AMPS.index(a)
                                                                           + 50 * RL.CLASSES.index(c) + k for k in range(50)]]
    got = RL.relabel_draw(ex)
    assert len(got) == 1000


# ------------------------------------------------------------------------------ anchors and probes

def test_anchor_comes_from_the_examples_own_fold_with_fallbacks():
    amp = "pr12"
    S, x, lab = label_x(amp, 3)
    dims = K.space(amp, S)
    near = {("pr12Amp", "pr12Volume"): x[("pr12Amp", "pr12Volume")]}
    far_other_fold = dict(x)                                     # identical to the label, but fold 1
    optima = {0: [(amp, "clean", {("pr12Amp", "pr12Volume"): "0"}), (amp, "clean", near),
                  (amp, "crunch", dict(x))],
              1: [(amp, "clean", far_other_fold)]}
    w = RL.label_weights(amp, lab, RL.PLAN_TABLE)
    a, tag = RL.anchor_for(x, S, dims, 0, amp, "clean", optima, w)
    assert tag == "" and a[("pr12Amp", "pr12Volume")] == x[("pr12Amp", "pr12Volume")]
    a, tag = RL.anchor_for(x, S, dims, 0, amp, "other", optima, w)
    assert tag == "other-class"
    a, tag = RL.anchor_for(x, S, dims, 2, amp, "clean", optima, w)
    assert a is None and tag == "none"


def test_probes_pull_toward_the_anchor_and_swap_only_what_they_name():
    amp = "sw50r"
    S, x, _ = label_x(amp, 5)
    dims = K.space(amp, S)
    _, anc, _ = label_x(amp, 6)
    anc[("cabParameters", "leftMicType")] = "9" if x[("cabParameters", "leftMicType")] != "9" else "8"
    anc[("sw50rAmp", "sw50rBright")] = "true" if x[("sw50rAmp", "sw50rBright")] == "false" else "false"
    p = RL.probes(x, S, dims, anc, random.Random(1))
    assert list(p) == ["S", "pull0.25", "pull0.5", "pull0.75", "pull1", "mics", "switches", "jitter0", "jitter1"]
    for d in dims:
        k = (d.module, d.key)
        if d.kind in ("cont", "log"):
            ul, ua = RL.unit_of(d, x), RL.unit_of(d, anc)
            assert RL.unit_of(d, p["pull0.5"]) == pytest.approx(ul + 0.5 * (ua - ul), abs=1e-5)
            assert p["pull1"][k] == anc[k]
            assert p["mics"][k] == x[k] and p["switches"][k] == x[k]
            assert p["pull0.5"]
        elif d.kind == "cat":
            assert p["pull1"][k] == x[k] and p["mics"][k] == anc[k] and p["switches"][k] == x[k]
        else:
            assert p["pull1"][k] == x[k] and p["mics"][k] == x[k] and p["switches"][k] == anc[k]
            assert p["jitter0"][k] == x[k]
    assert p == RL.probes(x, S, dims, anc, random.Random(1))


def test_probes_without_an_anchor_are_jitters_and_matching_switches_give_a_third_jitter():
    amp = "pr12"
    S, x, _ = label_x(amp, 7)
    dims = K.space(amp, S)
    p = RL.probes(x, S, dims, None, random.Random(2))
    assert sorted(p) == sorted(["S", "jitter_p0", "jitter_p1", "jitter_p2", "jitter_p3", "jitter0", "jitter1"])
    anc = dict(x)                                              # same switches as the label
    q = RL.probes(x, S, dims, anc, random.Random(2))
    assert "switches" not in q and "jitter2" in q


def test_probe_renders_skip_the_label_and_duplicates():
    amp = "pr12"
    S, x, _ = label_x(amp, 8)
    first, of = RL.probe_renders(x, {"S": S, "a": dict(x), "b": S, "c": {**S, ("parameters", "inputGain"): "3"}})
    assert set(first.values()) == {"S", "c"} and of["a"] == K.key(x)


def test_label_of_round_trips_a_bank_label():
    amp = "ac20"
    S = S_for(amp)
    x, lab = D.broad(K.space(amp, S), S, random.Random(4))
    got = RL.label_of(K.space(amp, S), x)
    for n, v in lab.items():
        assert got[n] == pytest.approx(v, abs=1e-5) if isinstance(v, float) else got[n] == v


# ------------------------------------------------------------------------------ record-like examples

def windows():
    w = []
    for f in range(4):
        for b in range(2):
            for k in range(5):
                w.append({"band": f"band{f}{b}", "fold": f, "path": f"/di/{f}{b}.wav", "start": k * 480000})
    w += [{"band": "Guitar-TECHS P1", "fold": "all", "path": f"/gt/{k}.wav", "start": 0} for k in range(5)]
    return w


def test_new_examples_are_single_fold_with_own_fold_centres_uniform_per_part():
    parts = {0: {"partA": [("pr12", "clean", f"/c/partA/pr12/K_S-{h}{k}.json") for h in "AB" for k in range(5)],
                 "partB": [("pr12", "clean", "/c/partB/pr12/K_S-A.json")]},
             1: {"partC": [("pr12", "crunch", "/c/partC/pr12/K_S-A.json")]}}
    back = [(f"band{f}0", f, f"/back/{f}.wav") for f in range(4)]
    tracks = {"/di/00.wav"}
    ex = RL.new_examples(windows(), back, parts, tracks, n=3000)
    assert ex == RL.new_examples(windows(), back, parts, tracks, n=3000)
    assert ex[0]["i"] == RL.NEW_BASE and len(ex) == 3000
    fold_of = {f"band{f}{b}": f for f in range(4) for b in range(2)}
    RL.assert_new_clean(ex, tracks, fold_of, parts)
    assert not any(e["window"]["path"] in tracks for e in ex)
    f0 = [e for e in ex if e["fold"] == 0 and e["amp"] == "pr12" and e["class"] == "clean"]
    share_b = sum("partB" in e["centre"] for e in f0) / len(f0)
    assert 0.35 < share_b < 0.65                                   # uniform per part, not per optimum
    other = [e for e in ex if e["fold"] == 1 and e["amp"] == "pr12" and e["class"] == "clean"]
    assert other and all(e["centre_fallback"] == "other-class" for e in other)
    none = [e for e in ex if e["fold"] == 2]
    assert none and all(e["centre"] == "S" and e["centre_fallback"] == "none" for e in none)
    assert all(e["backing"] == f"/back/{e['fold']}.wav" for e in ex)


def test_assert_new_clean_catches_a_cross_fold_centre_and_a_target_track():
    parts = {0: {"p": [("pr12", "clean", "/c/p/pr12/K_S-A.json")]}, 1: {"q": [("pr12", "clean", "/c/q/pr12/K_S-A.json")]}}
    e = {"i": RL.NEW_BASE, "fold": 0, "window": {"band": "b", "fold": 0, "path": "/x.wav"},
         "centre": "/c/q/pr12/K_S-A.json", "centre_fold": 0}
    with pytest.raises(AssertionError):
        RL.assert_new_clean([e], set(), {"b": 0}, parts)
    e["centre"] = "/c/p/pr12/K_S-A.json"
    RL.assert_new_clean([e], set(), {"b": 0}, parts)
    with pytest.raises(AssertionError):
        RL.assert_new_clean([e], {"/x.wav"}, {"b": 0}, parts)


def test_optima_by_part_reads_the_part_from_the_path():
    got = RL.optima_by_part({0: [("pr12", "clean", "/kc/cells/slugX/pr12/K_S-A.json")]})
    assert list(got[0]) == ["slugX"]


# ------------------------------------------------------------------------------ the mixture's parity

def test_mixture_with_matches_song_aug_mixture(tmp_path, monkeypatch):
    pytest.importorskip("pyloudnorm")
    sf = pytest.importorskip("soundfile")
    from learn import song_aug as A
    from learn import song_bank as B

    rng = np.random.default_rng(0)
    sr, n = 48000, 48000 * 2
    renders = {i: rng.normal(0, 0.1, n) for i in range(4)}
    (tmp_path / "renders").mkdir()
    for i in renders:
        (tmp_path / "renders" / f"{i:05d}.flac").write_bytes(b"")
    back = tmp_path / "back.wav"
    sf.write(str(back), rng.normal(0, 0.05, n).astype(np.float32), sr)
    monkeypatch.setattr(B, "OUT", tmp_path)
    monkeypatch.setattr(A, "load_render", lambda i: renders[i])
    for second in (False, True):
        e = {"i": 0, "fold": 1, "seed": 12345, "backing": str(back), "second_guitar": second}
        g1, m1, r1 = A.mixture(e, {1: [0, 1, 2, 3]}, [-3.0, 0.0, 4.0], -14.0)
        g2, m2, r2 = RL.mixture_with(e, renders[0], [0, 1, 2, 3], lambda j: renders[j], [-3.0, 0.0, 4.0], -14.0)
        assert np.array_equal(g1, g2) and np.array_equal(m1, m2) and r1.random() == r2.random()


# ------------------------------------------------------------------------------ the sets

def test_half_set_weights_sum_to_one_and_leave_out_S():
    d = {"S": 2.0, "pull0.25": 0.2, "pull1": 1.0, "mics": INF, "jitter0": 0.5}
    labels = {k: {"x": k} for k in d}
    s = RL.half_set(d, labels, {"x": "label"})
    assert not s["point"]
    names = [m["name"] for m in s["members"]]
    assert names[0] == "label" and "S" not in names and "mics" not in names
    w = [math.exp(m["logw"]) for m in s["members"]]
    assert sum(w) == pytest.approx(1.0)
    by = {m["name"]: m for m in s["members"]}
    assert by["pull0.25"]["r"] == pytest.approx(0.1)
    assert by["pull0.25"]["logw"] - by["label"]["logw"] == pytest.approx(-0.1 / RL.TAU)
    assert by["pull1"]["logw"] - by["label"]["logw"] == pytest.approx(-0.5 / RL.TAU)


def test_half_set_keeps_the_point_label_without_a_scale():
    for ds in (0.05, INF, None):
        s = RL.half_set({"S": ds, "pull1": 0.0}, {"pull1": {}}, {"x": 1})
        assert s["point"] and len(s["members"]) == 1 and s["members"][0]["logw"] == 0.0


def test_repeat_check_drops_silent_halves_and_fails_only_on_finite_misses():
    ok = RL.repeat_check([(1, {"A": 1e-7, "B": INF}), (2, {"A": 5e-4, "B": 0.0})])
    assert ok["ok"] and ok["silent_halves"] == [(1, "B")] and ok["checked_halves"] == 3
    bad = RL.repeat_check([(1, {"A": 6e-3, "B": 0.0})])              # amendment 4: tol 0.005
    assert not bad["ok"] and bad["failures"] == [(1, "A", 6e-3)]
    assert not RL.repeat_check([(1, {"A": INF, "B": INF})])["ok"]          # nothing checked


def test_relabel_map_reports_shares_and_the_pull_reach():
    sets = [{"A": {"point": False, "members": [{"name": "label", "r": 0.0}, {"name": "pull0.25", "r": 0.1},
                                               {"name": "pull0.5", "r": 0.2}, {"name": "pull1", "r": 0.9},
                                               {"name": "jitter_p1", "r": 0.3}]},
             "B": {"point": True, "members": []}}]
    m = RL.relabel_map(sets)
    assert m["mean_largest_pull_t"] == 0.5
    assert m["by_probe"]["pull"]["share_r_le_0.25"] == pytest.approx(2 / 3)
    assert "jitter" in m["by_probe"]


# ------------------------------------------------------------------------------ guards

def test_require_disk_needs_the_guard_plus_two_and_a_half_gb():
    assert RL.DISK_NEED_GB == 33.5
    assert RL.require_disk(free=33.5) == 33.5
    with pytest.raises(SystemExit):
        RL.require_disk(free=33.4)


def test_caps():
    RL.check_cap("relabel", 9000, 50)
    with pytest.raises(SystemExit):
        RL.check_cap("relabel", 9000, 51)
    with pytest.raises(SystemExit):
        RL.check_cap("new", 2500, 51)


def test_spent_sums_render_counts(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({"renders": 9}))
    (tmp_path / "b.json").write_text(json.dumps({"renders": 3}))
    assert RL.spent(tmp_path) == 12
