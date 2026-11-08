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
    assert H.line_of([(0.0, 0, "a")] + [(0.0, 1, "b")] * 6) == 0.0             # exactly one half; floats gave 0.4999...
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
    a, b = [(1.0, 1, "a")], [(1.0, 0, "b")] * 3
    assert H.line_of([(x, y, f"{c}#{k}") for k, g in enumerate([a, b, b]) for x, y, c in g]) is None   # two copies of b
    assert H.line_of(a + b + b) == 1.0                                                                 # merged, it would read


def test_flatness_rises_with_drive_on_two_notes_and_ignores_a_tone_change():
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(0)
    t = np.arange(48000 * 2) / 48000

    def note(f0):
        return sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, int(5000 / f0) + 1))

    di = 0.1 * (note(220) + note(293.7)) + 1e-4 * rng.standard_normal(len(t))
    got = [H.flatness_db(np.tanh(g * di), di) for g in (2, 4, 8, 16)]               # more drive, flatter
    assert got == sorted(got) and got[-1] > got[0] + 3
    tilt = np.convolve(np.tanh(2 * di), [0.6, 0.3, 0.1], mode="same")                   # a tone change only
    assert abs(H.flatness_db(tilt, di) - got[0]) < 0.5


def test_check_draw_fills_bands_round_robin_with_no_section_twice():
    rows, i = [], 0
    for band_v in (10.0, 20.0, 24.0, 30.0):
        for a in H.AMPS:
            for k in range(8):
                i += 1
                rows.append({"i": i, "amp": a, "section": f"s{(i + 1) // 2}@0", "v": band_v})   # pairs share a section
    flat = {r["i"]: r["v"] for r in rows}
    got = H.check_draw(rows, flat, ((None, 18.0), (18.0, 22.0), (22.0, 26.0), (26.0, None)))
    assert len(got) == 4 * H.PER_BAND and len({g["section"] for g in got}) == len(got)
    assert [sum(1 for g in got if g["band"] == k) for k in range(4)] == [H.PER_BAND] * 4
    assert got == H.check_draw(rows, flat, ((None, 18.0), (18.0, 22.0), (22.0, 26.0), (26.0, None)))
    assert H.song_of("cambridge/TheTravellingBand_Quicksand_Full/16_ElecGtr1DI.wav@40.0") == "cambridge/TheTravellingBand_Quicksand_Full"
    assert H.song_of("goat/item_10@240.0#amp_4") == "goat/item_10"


def test_pairs_straddle_the_line_one_section_a_song_off_the_band_cards():
    rows, flat = [], {}
    for k in range(8):
        for m, v in enumerate((2.0, 9.0)):
            i = 10 * k + m
            rows.append({"i": i, "amp": "pr12", "section": f"set/S{k}_Full/x.wav@0"})
            flat[i] = v
    got = H.pair_draw(rows, flat, ((None, 5.0), (5.0, 6.0), (6.0, 7.0), (7.0, None)), {"set/S0_Full/x.wav@0"})
    assert len(got) == 2 * H.PAIRS and "set/S0_Full/x.wav@0" not in {g["section"] for g in got}
    assert len({H.song_of(g["section"]) for g in got}) == H.PAIRS
    assert all(flat[got[2 * k]["i"]] < 5.0 and flat[got[2 * k + 1]["i"]] >= 7.0 for k in range(H.PAIRS))
    np = pytest.importorskip("numpy")
    b = H.check_bands(x for x in range(101))                                         # a generator, read once
    assert [round(x, 1) for x in (b[0][1], b[1][1], b[2][1])] == [50.0, 75.0, 90.0]


def test_no_doubler_keeps_only_rows_with_the_doubler_off():
    rows = [{"i": 1, "settings": setting()}, {"i": 2, "settings": setting(**{"parameters/doublerActive": "true"})}]
    assert [x["i"] for x in H.no_doubler(rows)] == [1]


def _cards():
    items = [{"i": k, "band": k // 2, "flatness_db": -6.0 + k * 0.5, "song": f"s{k % 3}"} for k in range(8)]
    items += [{"i": 100, "band": "pair", "pair": 0, "flatness_db": -6.0, "song": "p0"},
              {"i": 101, "band": "pair", "pair": 0, "flatness_db": -3.0, "song": "p0"},
              {"i": 102, "band": "pair", "pair": 1, "flatness_db": -4.0, "song": "p1"},   # in the fit, it would pull the line to -4.0
              {"i": 103, "band": "pair", "pair": 1, "flatness_db": -2.9, "song": "p1"}]
    return items


BANDS = ((None, -5.0), (-5.0, -4.0), (-4.0, -3.0), (-3.0, None))


def test_check_read_fits_band_cards_only_and_reads_the_pairs():
    items = _cards()
    got = {str(it["i"]): ("keep" if it["flatness_db"] < -3.9 else "heavy") for it in items if it["band"] != "pair"}
    got |= {"100": "keep", "101": "heavy", "102": "heavy", "103": "heavy"}
    pool = sorted(-7.0 + 0.1 * k for k in range(50))
    r = H.check_read(items, got, pool, BANDS)
    assert r["line_db"] == -3.5 and r["line_band"] == 2                            # the pairs stay out (else -4.0)
    assert r["line_pct"] == 100.0 * sum(1 for x in pool if x < -3.5) / len(pool)   # strictly below
    assert r["pairs"] == {"n": 2, "split": 1, "flatter_dropped": 1, "both_dropped": 1}
    assert r["undecided"] == []
    assert [b["dropped"] for b in r["by_band"]] == [0, 0, 1, 2] and [b["n"] for b in r["by_band"]] == [2, 2, 2, 2]
    got |= {"100": "heavy", "101": "keep"}                                          # the less flat card dropped
    assert H.check_read(items, got, pool, BANDS)["undecided"] == ["the pairs do not favour the flatter card"]
    low = H.check_read(items, {**got, **{str(k): "heavy" for k in range(8)}}, pool, BANDS)
    assert low["line_band"] == 0 and "the line falls in the lowest band" in low["undecided"]


def test_check_read_counts_unsure_as_dropped_but_not_in_the_neither_fit():
    items = [it for it in _cards() if it["band"] != "pair"]
    got = {str(it["i"]): "keep" for it in items}
    got["7"] = "unsure"
    got["6"] = "heavy"
    r = H.check_read(items, got, [0.0], BANDS)
    assert r["line_db"] == -3.0 and r["unsure_neither_line_db"] == -3.0
    got["6"] = "unsure"
    r = H.check_read(items, got, [0.0], BANDS)
    assert r["line_db"] == -3.0 and r["unsure_neither_line_db"] is None              # not counted heavy
    got["5"] = "heavy"
    r = H.check_read(items, got, [0.0], BANDS)
    assert r["line_db"] == -3.5 and r["unsure_neither_line_db"] == -3.5              # not counted keep (else None)
    assert H.check_read(items, {str(it["i"]): "keep" for it in items}, [0.0], BANDS)["undecided"][0] == "no line"


def test_flatness_refuses_bad_shapes_and_gives_no_reading_for_silence():
    np = pytest.importorskip("numpy")
    di = np.random.default_rng(0).standard_normal(48000)
    assert H.flatness_db(np.zeros(48000), di) is None
    assert H.flatness_db(di[:100], di[:100]) is None
    with pytest.raises(ValueError):
        H.flatness_db(di[:20000], di)
    with pytest.raises(ValueError):
        H.flatness_db(np.stack([di, di], axis=1), di)


def test_draw_rounds_over_a_songs_sections_and_never_reuses_one_across_bands():
    rows, flat, i = [], {}, 0
    for song in ("A", "B"):
        for sec in range(24):
            for j, a in enumerate(H.AMPS):
                i += 1
                rows.append({"i": i, "amp": a, "section": f"set/{song}_Full/{sec}.wav@0"})
                flat[i] = (10.0, 20.0, 24.0, 30.0)[(sec + j) % 4]                  # each section in 3 bands
    got = H.check_draw(rows, flat, ((None, 18.0), (18.0, 22.0), (22.0, 26.0), (26.0, None)))
    assert len({g["section"] for g in got}) == len(got) == 40
    for k in range(4):
        band = [g for g in got if g["band"] == k]
        songs = [H.song_of(g["section"]) for g in band]
        assert abs(songs.count("set/A_Full") - songs.count("set/B_Full")) <= 1
        amps = [g["amp"] for g in band]
        assert max(amps.count(a) for a in H.AMPS) - min(amps.count(a) for a in H.AMPS) <= 1



def test_pairs_fall_back_to_the_widest_sections():
    rows, flat = [], {}
    for k, (lo, hi) in enumerate(((1.0, 2.0), (1.0, 5.0), (1.0, 4.0), (1.0, 3.0), (1.0, 6.0), (1.0, 1.5))):
        for m, v in enumerate((lo, hi)):
            i = 10 * k + m
            rows.append({"i": i, "amp": "pr12", "section": f"set/S{k}_Full/x.wav@0"})
            flat[i] = v
    got = H.pair_draw(rows, flat, ((None, 0.0), (0.0, 50.0), (50.0, 60.0), (60.0, None)), set())   # none straddles
    assert sorted({g["section"] for g in got}) == [f"set/S{k}_Full/x.wav@0" for k in (0, 1, 2, 3, 4)]


def test_check_page_refuses_when_its_key_exists(tmp_path, monkeypatch):
    (tmp_path / H.CHECK_DIR).mkdir()
    (tmp_path / H.CHECK_DIR / "key.json").write_text("{}")
    monkeypatch.setattr(H, "heavy_dir", lambda: tmp_path)
    with pytest.raises(SystemExit, match="exists"):
        H.cmd_check_page(None)


def test_nodoubler_changes_the_doubler_alone_and_refuses_where_it_is_off():
    x = {tuple(k.split("/")): v for k, v in setting(**{"parameters/doublerActive": "true", "reverb/reverbActive": "true"}).items()}
    y = H.nodoubler(x)
    assert y[("parameters", "doublerActive")] == "false" and [k for k in x if x[k] != y[k]] == [("parameters", "doublerActive")]
    with pytest.raises(SystemExit):
        H.nodoubler(y)
    rows = [{"i": 1, "settings": setting()}, {"i": 2, "settings": setting(**{"parameters/doublerActive": "true"})}]
    assert [x["i"] for x in H.doubler_rows(rows)] == [2]


# --- H4: the exclusions file ----------------------------------------------------------------------------------------

def _rows(n, band="b", doubler=()):
    return [{"i": i, "band": band, "settings": setting(**({"parameters/doublerActive": "true"} if i in doubler else {}))}
            for i in range(n)]


def test_out_list_cuts_at_or_past_the_threshold_by_the_right_value_and_takes_the_heavy_bands():
    rows = _rows(5, doubler={3, 4}) + [{"i": 9, "band": H.HEAVY_BANDS[0], "settings": setting()}]
    stored = {0: -5.0, 1: -4.0, 2: -3.0, 3: -1.0, 4: -9.0}          # doubler rows: their stored value is not read
    nodbl = {3: -6.0, 4: -4.0}
    got = H.out_list(rows, stored, nodbl, -4.0)
    assert got["ids"] == [1, 2, 4, 9] and got["n"] == 4 and got["of"] == 6 and got["left"] == 2
    assert got["by_source"] == {"heavy_band": 1, "stored": 2, "doubler_off": 1} and got["threshold"] == -4.0
    with pytest.raises(SystemExit, match="no flatness"):
        H.out_list(rows, stored, {3: -6.0}, -4.0)                    # a doubler row with no doubler-off value
    with pytest.raises(SystemExit, match="no flatness"):
        H.out_list(rows, {0: -5.0}, nodbl, -4.0)
    with pytest.raises(SystemExit, match="no flatness"):
        H.out_list(rows, {**stored, 1: float("nan")}, nodbl, -4.0)


def test_the_five_lists_share_one_rule_and_refuse_a_missing_value():
    w, ns = _rows(4, doubler={1}), [dict(r, i=r["i"] + 100) for r in _rows(3, doubler={0})]
    wf, wn = {0: -5.0, 2: -3.9, 3: -3.0}, {1: -4.2}
    nf, nn = {101: -4.1, 102: -3.5}, {100: -2.0}
    L = H.h4_lists(w, ns, wf, wn, nf, nn, ["u2", "u1"], -4.3, -3.6)
    assert L["real_out"]["ids"] == ["u1", "u2"] and L["real_out"]["n"] == 2
    assert L["plugin_out_full"]["ids"] == [1, 2, 3] and L["plugin_out_gentle"]["ids"] == [3]
    assert L["ns_out_full"]["ids"] == [100, 101, 102] and L["ns_out_gentle"]["ids"] == [100, 102]
    for bad in ((["u1", "u1"], -4.3, -3.6), ([], -4.3, -3.6), (["u1"], float("nan"), -3.6)):
        with pytest.raises(SystemExit):
            H.h4_lists(w, ns, wf, wn, nf, nn, *bad)


def test_doubler_off_records_must_be_one_doubler_off_render_of_a_doubler_row(tmp_path):
    import json

    f = tmp_path / "ns-doubler-0of1.jsonl"
    rec = lambda i, v=-4.0, **kw: json.dumps({"i": i, "kind": "nodoubler", "flatness_db": v,   # noqa: E731
                                             "settings": setting(), **kw})
    f.write_text(rec(1) + "\n" + rec(2, -3.0) + "\n\n")
    assert H.read_jsonl_values([f], {1, 2, 3}) == {1: -4.0, 2: -3.0}
    for body, want in ((rec(5), {1}), (rec(1) + "\n" + rec(1), {1}), (rec(1, kind="dry"), {1}),
                       (rec(1, None), {1}), (rec(1, settings=setting(**{"parameters/doublerActive": "true"})), {1})):
        f.write_text(body)
        with pytest.raises(SystemExit):
            H.read_jsonl_values([f], want)


def _h4_world(tmp_path, monkeypatch, ns_doubler=True):
    """Synthetic W (rows 0-5, rows 4-5 doubler, row 6 a heavy band), NS (10-12, 12 doubler) and every input file."""
    import json

    from learn import bakeoff as B
    from learn import pipeline_fix as P
    from learn import scope_page as SP

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "require", lambda key: {})
    hd = tmp_path / "heavy"
    (hd / "check").mkdir(parents=True)
    (hd / "h2").mkdir()
    (hd / "h4").mkdir()
    ex = {r["i"]: r for r in _rows(6, doubler={4, 5}) + [{"i": 6, "band": H.HEAVY_BANDS[1], "settings": setting()}]
          + [dict(r, i=r["i"] + 10) for r in _rows(3, doubler={2})]}
    monkeypatch.setattr(H, "cc_examples", lambda: ex)
    monkeypatch.setattr(B, "plugin_set", lambda: ([{"i": i} for i in range(7)], None))
    (tmp_path / "runs").mkdir()
    for sd in P.SEEDS:
        (tmp_path / "runs" / f"P2b-wide24-{sd}.json").write_text(json.dumps({"held": "ns", "held_ids": [10, 11, 12],
                                                                              "train_ids": list(range(7))}))
    flat = {0: -6.0, 1: -5.0, 2: -4.0, 3: -3.0, 4: -9.0, 5: -9.0}
    (hd / "check" / "flatness.json").write_text(json.dumps({"flatness_db": {str(k): v for k, v in flat.items()}}))
    edge = H.check_bands([flat[i] for i in range(4)])[1][1]
    (hd / "check" / "key.json").write_text(json.dumps({"bands": [[None, -5.0], [-5.0, edge], [edge, None], [0, None]]}))
    (hd / "check" / "verdicts.json").write_text(json.dumps({"line_db": -4.5}))
    rec = lambda i, v: json.dumps({"i": i, "kind": "nodoubler", "flatness_db": v, "settings": setting()})  # noqa: E731
    (hd / "h2" / "doubler-0of1.jsonl").write_text(rec(4, -4.4) + "\n" + rec(5, -2.0) + "\n")
    (hd / "h4" / "ns-flatness.json").write_text(json.dumps({"flatness_db": {"10": -4.0, "11": -6.0, "12": -9.0}}))
    if ns_doubler:
        (hd / "h4" / "ns-doubler-0of1.jsonl").write_text(rec(12, -4.0) + "\n")
    monkeypatch.setattr(SP, "scope_dir", lambda: tmp_path / "scope")
    (tmp_path / "scope").mkdir()
    (tmp_path / "scope" / "verdicts.json").write_text(json.dumps({"out": ["goat/x@1#amp_1", "s/A/d@0#t"]}))
    return hd, edge


def test_h4_exclusions_writes_the_lists_once_and_they_load_through_the_pin(tmp_path, monkeypatch, capsys):
    pytest.importorskip("numpy")
    import json

    from learn import direct_stems as DS
    from learn import pipeline_fix as P

    hd, edge = _h4_world(tmp_path, monkeypatch)
    H.cmd_h4_exclusions(None)
    out = hd / H.H4_FILE
    doc = json.loads(out.read_text())
    assert doc["plugin_out_full"]["ids"] == [2, 3, 4, 5, 6] and doc["plugin_out_full"]["threshold"] == -4.5
    assert doc["plugin_out_gentle"]["ids"] == [i for i in (2, 3) if [-4.0, -3.0][i - 2] >= edge] + [5, 6]
    assert doc["ns_out_full"]["ids"] == [10, 12] and doc["real_out"]["n"] == 2
    assert doc["lists_sha256"] == P.h4_lists_sha(doc) and len(doc["inputs_sha256"]) == 7
    sha = DS.hashlib_file(out)
    assert sha in capsys.readouterr().out
    pin = {P.H4: {}, P.H4_EXCL: {"path": "heavy/h4-exclusions.json", "sha256": sha}}
    monkeypatch.setattr(P, "require", lambda key: pin)
    ex = P.h4_exclusions()
    assert ex["plugin_out"]["full"] == {2, 3, 4, 5, 6} and ex["ns_out"]["full"] == {10, 12}
    assert ex["real_out"] == {"goat/x@1#amp_1", "s/A/d@0#t"}
    with pytest.raises(SystemExit, match="written once"):
        H.cmd_h4_exclusions(None)


def test_h4_exclusions_refuse_before_ns_is_measured_or_on_a_moved_edge(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    import json

    hd, _ = _h4_world(tmp_path, monkeypatch, ns_doubler=False)
    with pytest.raises(SystemExit, match="ns-doubler"):
        H.cmd_h4_exclusions(None)
    (hd / "h4" / "ns-doubler-0of1.jsonl").write_text("")
    with pytest.raises(SystemExit, match="no flatness"):            # NS's doubler row has no doubler-off value
        H.cmd_h4_exclusions(None)
    (hd / "h4" / "ns-doubler-0of1.jsonl").write_text(json.dumps({"i": 12, "kind": "nodoubler", "flatness_db": -4.0,
                                                                "settings": setting()}) + "\n")
    key = json.loads((hd / "check" / "key.json").read_text())
    key["bands"][1][1] += 0.01
    (hd / "check" / "key.json").write_text(json.dumps(key))
    with pytest.raises(SystemExit, match="75th"):
        H.cmd_h4_exclusions(None)
    assert not (hd / H.H4_FILE).exists()


def test_ns_is_ws_held_set_on_both_seeds(tmp_path, monkeypatch):
    import json

    from learn import pipeline_fix as P

    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    (tmp_path / "runs").mkdir()
    for sd, held in zip(P.SEEDS, ([3, 4], [3, 4])):
        (tmp_path / "runs" / f"P2b-wide24-{sd}.json").write_text(json.dumps({"held": "ns", "held_ids": held,
                                                                              "train_ids": [1, 2]}))
    assert H.ns_ids() == [3, 4]
    (tmp_path / "runs" / f"P2b-wide24-{P.SEEDS[1]}.json").write_text(json.dumps({"held": "ns", "held_ids": [3],
                                                                                 "train_ids": [1, 2]}))
    with pytest.raises(SystemExit, match="one NS"):
        H.ns_ids()
