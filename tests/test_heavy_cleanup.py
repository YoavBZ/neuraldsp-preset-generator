import pytest

from learn import heavy_cleanup as H


def setting(**on):
    s = {"reverb/reverbActive": "false", "delay/delayActive": "false", "tremolo/tremoloActive": "false",
         "parameters/doublerActive": "false", "pr12Amp/pr12Reverb": "0", "sw50rAmp/sw50rReverb": "0.3",
         "cabParameters/leftRoomActive": "false", "cabParameters/leftCabActive": "true",
         "cabParameters/rightRoomActive": "true", "cabParameters/rightCabActive": "false", "pr12Amp/pr12Gain": "0.5"}
    s.update(on)
    return s


def test_switches_count_a_room_only_on_an_active_cab_and_the_rows_own_spring():
    assert H.switches(setting(), "pr12") == []                                    # sw50r's spring: another amp
    assert H.switches(setting(), "sw50r") == ["spring"]
    assert H.switches(setting(**{"cabParameters/leftRoomActive": "true"}), "ac20") == ["room"]
    assert H.switches(setting(**{"reverb/reverbActive": "true", "parameters/doublerActive": "true"}), "ac20") == ["reverb", "doubler"]


def test_the_dry_twin_changes_only_declared_keys():
    x = {tuple(k.split("/")): v for k, v in setting(**{"delay/delayActive": "true", "pr12Amp/pr12Reverb": "0.4"}).items()}
    y = H.dry(x, "pr12")
    assert y[("delay", "delayActive")] == "false" and y[("pr12Amp", "pr12Reverb")] == "0"
    assert y[("sw50rAmp", "sw50rReverb")] == "0.3"                                # the other amp's knob stays
    assert y[("cabParameters", "rightRoomActive")] == "false" and y[("pr12Amp", "pr12Gain")] == "0.5"
    H.check_dry(x, y, "pr12")
    with pytest.raises(SystemExit):
        H.check_dry(x, {**y, ("pr12Amp", "pr12Gain"): "0.6"}, "pr12")
    with pytest.raises(SystemExit):
        H.check_dry(x, {**y, ("new", "key"): "1"}, "pr12")
    with pytest.raises(SystemExit):                                                 # another amp's spring
        H.check_dry(x, {**y, ("sw50rAmp", "sw50rReverb"): "0"}, "pr12")
    with pytest.raises(SystemExit):                                                 # a dry key set on, not off
        H.check_dry(x, {**y, ("reverb", "reverbActive"): "true"}, "pr12")


def test_draw_is_disjoint_and_per_family():
    rows = []
    i = 0
    for fam, on in (("reverb", {"reverb/reverbActive": "true"}), ("delay", {"delay/delayActive": "true"}),
                    ("doubler", {"parameters/doublerActive": "true"}), ("tremolo", {"tremolo/tremoloActive": "true"}),
                    ("spring", {}), ("room", {"cabParameters/leftRoomActive": "true"}), ("none", {})):
        for _ in range(12):
            i += 1
            amp = "sw50r" if fam == "spring" else "pr12"
            rows.append({"i": i, "amp": amp, "settings": {**setting(**on), "cabParameters/rightRoomActive": "false"}})
    items = H.draw(rows)
    assert len(items) == 6 * H.PER_FAMILY + H.N_SAME + H.N_ON
    assert len({it["i"] for it in items}) == len(items)
    assert {it["family"] for it in items if it["kind"] == "dry"} == set(H.FAMILIES)
    assert items == H.draw(rows)                                                    # seeded


def test_margin_takes_the_worst_negative_shift_when_larger():
    assert H.margin([0.2, 1.0]) == 0.5
    assert H.margin([-0.8, 1.0]) == 0.8


def test_residual_is_minus_inf_when_identical_and_inf_on_unequal_lengths():
    np = pytest.importorskip("numpy")
    assert H.residual_db(np.ones(4), np.ones(4)) == float("-inf")
    assert H.residual_db(np.ones(4), np.ones(5)) == float("inf")


def test_isotonic_pools_violators_and_the_line_is_the_first_value_reaching_half():
    fit = H.isotonic([(0.0, 1, 1.0), (1.0, 0, 1.0), (2.0, 1, 1.0), (3.0, 1, 1.0)])
    assert fit == [(0.0, 0.5), (1.0, 0.5), (2.0, 1.0), (3.0, 1.0)]
    pts = [(-5.0, 1, "a"), (-2.0, 0, "a"), (-1.0, 0, "b"), (0.5, 1, "c"), (1.5, 1, "d")]
    assert H.line_of(pts) == 0.5                                                      # under the floor: not used
    assert H.line_of([(0.0, 0, "a"), (1.0, 0, "b")]) is None


def test_weights_are_one_over_the_cluster_count():
    assert [w for _, _, w in H.weighted([(0, 1, "a"), (1, 0, "a"), (2, 1, "b")])] == [0.5, 0.5, 1.0]
    third = [(0.0, 1, "a"), (0.0, 0, "a"), (0.0, 0, "a"), (0.0, 1, "b"), (0.0, 0, "b"), (0.0, 1, "b")]   # exactly one half
    assert H.isotonic(H.weighted(third)) == [(0.0, 0.5)]
    assert H.cluster_of("goat/item_10@240.0#amp_4") == "goat/item_10"
    assert H.cluster_of("set5/BKS_Bulldozer_Full/19_ElecGtr1aDI.wav@15.0#21_ElecGtr1cReamp.wav") == "set5/BKS_Bulldozer_Full/19_ElecGtr1aDI.wav"


def test_bins_merge_up_while_short_and_the_top_merges_down():
    pts = [(-2.5 + 0.01 * k, 0, f"c{k % 5}") for k in range(10)] + [(0.0 + 0.01 * k, 1, f"d{k % 5}") for k in range(10)] \
        + [(4.0, 1, "e0"), (4.1, 1, "e1")]
    bins = H.bins_of(pts)
    assert [(b["lo"], b["n"]) for b in bins] == [(-3.0, 10), (-1.0, 12)]               # [-1, 1) takes the short top
    assert H.bin_line(bins) == -1.0


def test_answer_points_a_page_verdict_wins_and_unsure_counts_heavy():
    nl = {"a@1": 0.0, "b@1": 1.0, "c@1": 2.0}
    pts = H.answer_points(nl, {"a@1": "unsure", "b@1": "keep"}, {"b@1": "out", "c@1": "keep"})
    assert sorted(pts) == [(0.0, 1, "a"), (1.0, 0, "b"), (2.0, 0, "c")]
    assert H.answer_points(nl, {"a@1": "unsure"}, {}, unsure_heavy=False) == []
    assert H.answer_points(nl, {}, {"c@1": "keep"}, ear_eat_keeps=False, eat_only={"c@1"}) == []


def test_boot_is_seeded():
    pts = [(float(k), int(k > 3), f"c{k}") for k in range(8)]
    assert H.boot_lines(pts, boot=50) == H.boot_lines(pts, boot=50)


def test_boot_draws_only_clusters_in_the_fit_and_a_cluster_drawn_twice_counts_twice():
    pts = [(float(k), int(k > 3), f"c{k}") for k in range(8)] + [(-9.0, 1, "under")]
    lines = H.boot_lines(pts, boot=200)
    assert lines == H.boot_lines([p for p in pts if p[2] != "under"], boot=200)
    one = [(0.0, 0, "a"), (1.0, 1, "b")]
    assert H.line_of([(x, y, f"{c}#{k}") for k, (x, y, c) in enumerate(one + one)]) == 1.0
