import math

import pytest

from learn import pipeline_fix as P
from learn import pipeline_review as PR


def test_t95_matches_the_reviews_seven_band_value_and_falls_back_to_the_normal():
    assert P.t95(6) == pytest.approx(PR.T_95[6], abs=1e-4)
    assert P.t95(200) == pytest.approx(1.6449)
    assert P.t95(0) is None


def test_clustered_averages_parts_then_clusters_with_a_t_interval():
    rows = [("b1", "p1", 1.0), ("b1", "p1", 3.0), ("b1", "p2", 0.0), ("b2", "p3", -1.0), ("b3", "p4", 0.0)]
    r = P.clustered(rows)
    means = [1.0, -1.0, 0.0]
    half = P.t95(2) * math.sqrt(sum((m - 0.0) ** 2 for m in means) / 2) / math.sqrt(3)
    assert r["mean"] == 0.0 and r["clusters"] == 3
    assert r["hi90"] == pytest.approx(half) and r["lo90"] == pytest.approx(-half)
    assert r["part_weighted"] == pytest.approx((2.0 + 0.0 - 1.0 + 0.0) / 4)
    assert r["clusters_negative"] == 1 and r["clusters_positive"] == 1
    assert r["leave_one_out"]["b1"] == pytest.approx(-0.5)


def test_clustered_of_nothing_is_empty():
    assert P.clustered([])["mean"] is None


def _dist(**presets):
    return {f"flat|{amp}|measfix_{h}": {p: [v] for p, v in presets.items()} for amp in PR.AMPS for h in "AB"}


def test_start_rules_drop_the_excluded_parts():
    files = [{"a": _dist(**{"factory:X": 1.0, "factory:Y": 2.0}),
              "b": _dist(**{"factory:X": 5.0, "factory:Y": 2.0}),
              "c": _dist(**{"factory:X": 5.0, "factory:Y": 2.0})}]
    pinned = {p: {"gain_class": "clean", "band": "B"} for p in "abc"}
    full = P.start_rules(files, pinned, set())
    assert full["clean"]["per_amp"]["pr12"][0] == "factory:Y"           # medians X 5, Y 2
    less = P.start_rules(files, pinned, {"b", "c"})
    assert less["clean"]["per_amp"]["pr12"] == ("factory:X", 1.0, 1)
    assert less["crunch"]["parts"] == 0


def test_s_prime_rows_reads_stored_distances_and_lists_what_needs_renders():
    choice = {c: {"presets": {a: "factory:S" for a in PR.AMPS}} for c in ("clean", "crunch")}
    rules = {"clean": {"per_amp": {a: ("factory:N" if a == "pr12" else "factory:S", 0, 1) for a in PR.AMPS}},
             "crunch": {"per_amp": {a: ("factory:S", 0, 1) for a in PR.AMPS}}}
    vreal = {"p": ("B1", "clean"), "q": ("B2", "crunch"), "r": ("B3", "clean")}
    files = [{"p": _dist(**{"factory:S": 2.0, "factory:N": 1.0})}]
    rows, missing = P.s_prime_rows(files, vreal, choice, rules)
    vals = [v for b, s, v in rows if s == "p"]
    assert vals.count(0.0) == 4 and sorted(vals)[:2] == [pytest.approx(math.log(0.5))] * 2
    assert all(v == 0.0 for _, s, v in rows if s == "q")
    assert missing == [("r", "pr12")]


def test_s_prime_rows_never_reads_t3s_own_crop_from_the_distance_files():
    slug = next(iter(PR.IN_GROUP_S))
    choice = {c: {"presets": {a: "factory:S" for a in PR.AMPS}} for c in ("clean", "crunch")}
    rules = {c: {"per_amp": {a: ("factory:N", 0, 1) for a in PR.AMPS}} for c in ("clean", "crunch")}
    files = [{slug: _dist(**{"factory:S": 2.0, "factory:N": 1.0})}]
    _, missing = P.s_prime_rows(files, {slug: ("B", "clean")}, choice, rules)
    assert len(missing) == 3


def test_double_status_compares_the_doubles_setting_with_the_label():
    lab = {PR.SWITCHES[k]: "false" for k in P.DOUBLE_SWITCHES}
    lab.update({PR.SWITCHES["drive2"]: "true", PR.SWITCHES["delay"]: "true", "x/knob": "0.5"})
    core = dict(lab, **{PR.SWITCHES["delay"]: "false", "x/knob": "0.6"})
    assert P.double_status({"others": [{"dt": False}], "core": core, "settings": lab}) is None
    st = P.double_status({"others": [{"dt": True}], "core": core, "settings": lab})
    assert st == {"switches_differ": ["delay"], "settings_differ": 2}


def test_auc_counts_ties_half_and_needs_both_classes():
    assert P.auc([0.9, 0.1], [True, False]) == 1.0
    assert P.auc([0.5, 0.5], [True, False]) == 0.5
    assert P.auc([0.2, 0.9, 0.4], [True, False, False]) == 0.0
    assert P.auc([0.2], [True]) is None


def test_cluster_boot_is_seeded_and_brackets_a_constant_statistic():
    items = list(range(20))
    clusters = [i % 5 for i in items]
    lo, hi = P.cluster_boot(items, lambda xs: 1.0, clusters, n=50)
    assert lo == hi == 1.0
    a = P.cluster_boot(items, lambda xs: sum(xs) / len(xs), clusters, n=200)
    assert a == P.cluster_boot(items, lambda xs: sum(xs) / len(xs), clusters, n=200)
    assert a[0] <= 9.5 <= a[1]


def test_real_runs_refuse_without_the_phase_in_the_ledger(monkeypatch):
    monkeypatch.setattr(P, "ledger_entry", lambda: {"test_id": P.LEDGER_ID})
    with pytest.raises(SystemExit):
        P.require("phase_1")


def test_session_of_a_section():
    assert P.session_of("cambridge/AdamBuckley_DragMeDown_Full/31_ElecGtr3DI.wav@130.0") == \
        "cambridge/AdamBuckley_DragMeDown_Full"


def test_recipe_split_holds_out_whole_songs_and_drops_dirty_examples():
    ns = P.NS_SESSIONS[0]
    kept = {1: {"section": f"{ns}/a.wav@0.0"}, 2: {"section": "s/Other_Full/a.wav@0.0"},
            3: {"section": f"{ns}/b.wav@5.0"}, 4: {"section": "s/Other_Full/a.wav@5.0"},
            5: {"section": "s/Other_Full/b.wav@0.0"}}
    sp = P.recipe_split(kept, tr_ids=[1, 2, 5], fs_ids=[3, 4], drop={5})
    assert sp["ns"] == [1, 3] and sp["train"] == [2] and sp["fs"] == [4]
    assert sp["dropped"] == {"train": 1, "fs": 0, "ns": 0}


def test_nested_subset_keeps_one_per_section_and_nests():
    sec = {i: f"s{i % 4}" for i in range(40)}
    a = P.nested_subset(list(range(40)), sec, 0.25)
    b = P.nested_subset(list(range(40)), sec, 0.5)
    c = P.nested_subset(list(range(40)), sec, 1.0)
    assert set(a) <= set(b) <= set(c) and len(c) == 40
    assert len(a) == 4 * 3 and len({sec[i] for i in a}) == 4
    assert len(P.nested_subset([0, 4], sec, 0.01)) == 1          # one section, at least one example


def test_gmm1d_fits_two_clusters_and_its_nll_is_lower_on_the_data():
    import numpy as np

    rng = np.random.default_rng(0)
    x = np.concatenate([rng.normal(0.2, 0.02, 200), rng.normal(0.8, 0.02, 200)])
    w, mu, sd = P.gmm1d(x)
    assert abs(sum(w) - 1) < 1e-9 and np.all(sd >= math.exp(-6) - 1e-12)
    assert P.gmm1d_nll(0.2, w, mu, sd) < P.gmm1d_nll(0.5, w, mu, sd)
    w1, mu1, sd1 = P.gmm1d([0.3])
    assert list(mu1) == [0.3]


def test_baseline_switch_rate_and_amp_frequency():
    import numpy as np

    from learn import full_space as F

    n, nk, ns, nc = 4, len(F.CONT), len(F.SW), len(F.CAT)
    Y = (np.zeros((n, nk), np.float32), np.zeros((n, nk), np.float32),
         np.array([[1.0] * ns, [1.0] * ns, [0.0] * ns, [1.0] * ns], np.float32), np.ones((n, ns), np.float32),
         np.zeros((n, nc), np.int64), np.ones((n, nc), np.float32), np.array([0, 0, 1, 2]))
    cells = [("pr12", "clean")] * n
    b = P.Baseline(Y, cells)
    assert b.sw[cells[0]][0] == (3 + 0.5) / (4 + 1)
    assert b.amp[0] == (2 + 0.5) / (4 + 1.5)
    out = b.losses(Y, cells)
    assert out["amp_n"] == 4 and out["sw_n"][0] == 4 and out["knob_n"].sum() == 0
    fam = P.family_means(out)
    assert fam["knob_marginal"] is None and fam["switch"] > 0
