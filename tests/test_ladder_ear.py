"""The ladder's ear check (`learn/ladder_ear.py`): the draw's filters and spread, the guards, the page order and letters,
the tie-aware unblinding, the pair rows with the sign test, A1 to A5, the declared outcome table, the player and the
power simulation."""

import random

import pytest

from learn import ladder_ear as E

AMPS = ("pr12", "sw50r", "ac20")


def _pool(seed=7):
    """A synthetic pool shaped like the ladder's: GOAT items on three players, BKS's 8 DI files on two songs (each unit on
    three amps), the panel's 12 windows on 5 DI files in 4 bands, cap1's 19 creators."""
    rng = random.Random(seed)
    out = []

    def part(set_, unit, amp, cls, cluster, **kw):
        out.append({"set": set_, "unit": unit, "amp": amp, "key": f"{unit}|{amp}", "cls": cls, "cluster": cluster,
                    "search": "A", "held": "B", "player": None, "item": None, "di_item": None, "band": None,
                    "slug": E.slug_of(set_, f"{unit}|{amp}"), "heard": False, **kw})

    for i in range(130):
        player = "GOAT player1" if i < 100 else "GOAT player2" if i < 125 else "GOAT player4"
        for j in range(1 + i % 2):
            part("goat", f"goat/item_{i}#{j}", rng.choice(AMPS), rng.choice(("clean", "crunch")), f"item_{i}",
                 player=player, item=f"item_{i}")
    for d in range(8):
        cls = "clean" if d < 4 else "crunch"
        for u in range(3 + d % 3):
            for a in AMPS:
                part("bks", f"set5/BKS_{'TooMuch' if d < 3 else 'Bulldozer'}/di{d}@{u}", a, cls, f"bks/di{d}.wav",
                     heard=u == 0)
    panel = [("Aimee", "aimee.wav", "clean", 3), ("Jen", "drowning.wav", "clean", 3), ("Jen", "waves.wav", "clean", 2),
             ("Big", "big.wav", "crunch", 1), ("Laminar", "laminar.wav", "crunch", 3)]
    for band, di, cls, n in panel:
        for w in range(n):
            part("panel", f"panel/{di}@{w}", AMPS[w % 3], cls, f"panel/{di}", band=band, heard=w == 0)
    for c in range(19):
        for u in range(6):
            part("cap1", f"cap/c{c}u{u}", AMPS[(c + u) % 3], ("clean", "crunch")[u % 2], f"creator{c}",
                 di_item=f"item_{rng.randrange(130)}")
    return out


@pytest.fixture(scope="module")
def drawn():
    return E.draw_sittings(_pool())


def _cards(d, s, role="cards"):
    return d["sittings"][s][role]


def test_the_draw_fills_both_sittings_with_the_declared_spread(drawn):
    for s in ("1", "2"):
        cards = _cards(drawn, s)
        assert len(cards) == 22 and E.sitting_refusal(cards) is None
        for set_, n in E.CARDS.items():
            got = [p for p in cards if p["set"] == set_]
            assert len(got) == n and sum(p["cls"] == "clean" for p in got) == n // 2
        amps = E._amps(cards)
        assert all(6 <= v <= 8 for v in amps.values()) and len(amps) == 3
        goat = [p for p in cards if p["set"] == "goat"]
        assert max(sum(p["player"] == pl for p in goat) for pl in {p["player"] for p in goat}) <= E.GOAT_PLAYER_MAX
        assert tuple(sorted(E._amps(goat).values(), reverse=True)) == E.GOAT_AMPS
        assert all(v <= E.BKS_AMP_MAX for v in E._amps([p for p in cards if p["set"] == "bks"]).values())
        cap = [p for p in cards if p["set"] == "cap1"]
        assert len(E._amps(cap)) == E.CAP1_AMPS and len({p["cluster"] for p in cap}) == 4
        for set_ in ("goat", "bks", "cap1"):
            cl = [p["cluster"] for p in cards if p["set"] == set_]
            assert len(cl) == len(set(cl))                                       # one card a cluster
    assert [len(_cards(drawn, s, "spares")) for s in ("1", "2")] == [7, 7]
    assert E.draw_sittings(_pool()) == drawn                                     # seeded


def test_the_first_sitting_hears_four_panel_bands_and_the_second_repeats_its_clusters(drawn):
    p1 = [p for p in _cards(drawn, "1") if p["set"] == "panel"]
    assert len({p["band"] for p in p1}) == 4
    p2 = [p for p in _cards(drawn, "2") if p["set"] == "panel"]
    assert len(p2) == 4 and not {p["unit"] for p in p1} & {p["unit"] for p in p2}


def test_no_unit_cluster_or_item_is_used_twice_across_the_sittings(drawn):
    every = [p for s in ("1", "2") for r in ("cards", "spares") for p in drawn["sittings"][s][r]]
    units = [p["unit"] for p in every]
    assert len(units) == len(set(units))
    for set_ in ("goat", "cap1"):
        cl = [p["cluster"] for p in every if p["set"] == set_]
        assert len(cl) == len(set(cl))
    s1 = {p["cluster"] for p in _cards(drawn, "1") if p["set"] == "bks"}
    s2 = {p["cluster"] for p in _cards(drawn, "2") if p["set"] == "bks"}
    assert len(s1) == len(s2) == 4 and not s1 & s2                              # BKS's other 4 DI files
    goat_items = {p["item"] for p in every if p["set"] == "goat"}
    assert not goat_items & {p["di_item"] for p in every if p["set"] == "cap1"}
    for s in ("1", "2"):
        bks_cards = {p["cluster"] for p in _cards(drawn, s) if p["set"] == "bks"}
        assert all(p["cluster"] in bks_cards for p in _cards(drawn, s, "spares") if p["set"] == "bks")


def test_a_bks_spare_falls_back_to_another_di_file_and_never_claims_it():
    pool = [p for p in _pool() if not (p["set"] == "bks" and p["cls"] == "crunch" and p["cluster"] != "bks/di7.wav"
                                       and not p["unit"].endswith("@0"))]
    d = E.draw_sittings(pool)                                                    # crunch DI files 4 to 6 hold one unit each
    s1 = [p for p in _cards(d, "1") if p["set"] == "bks" and p["cls"] == "crunch"]
    sp = [p for p in _cards(d, "1", "spares") if p["set"] == "bks" and p["cls"] == "crunch"]
    s2 = [p for p in _cards(d, "2") if p["set"] == "bks" and p["cls"] == "crunch"]
    assert len(s1) == 2 and len(sp) == 1
    assert len(s2) == 2 and not {p["cluster"] for p in s1} & {p["cluster"] for p in s2}   # the spare claimed no DI file


def test_bks_and_the_panel_take_fresh_units_first():
    d = E.draw_sittings(_pool())
    bks = [p for p in _cards(d, "1") if p["set"] == "bks"]
    assert not any(p["heard"] for p in bks)                                      # every BKS DI file has fresh units here


def test_the_second_sitting_may_run_short_but_the_first_may_not():
    short = [p for p in _cards(E.draw_sittings(_pool()), "1")]
    less = [p for p in short if p is not next(q for q in short if q["set"] == "cap1" and q["cls"] == "crunch")]
    assert E.sitting_refusal(less) is not None and E.sitting_refusal(less, strict=False) is None
    assert E.sitting_refusal(short + [short[0]], strict=False) is not None       # never over a quota


def test_the_pool_filters_activity_mild_crunch_and_heard_units():
    parts = [{"set": "goat", "unit": "g1", "cls": "clean", "held": "B"},
             {"set": "goat", "unit": "g2", "cls": "crunch", "held": "A"},
             {"set": "goat", "unit": "g3", "cls": "crunch", "held": "A"},
             {"set": "bks", "unit": "b1", "cls": "clean", "held": "A"},
             {"set": "panel", "unit": "p1", "cls": "crunch", "held": "A"},
             {"set": "cap1", "unit": "c1", "cls": "clean", "held": "A"}]
    cls_of = {p["unit"]: p["cls"] for p in parts}
    mild = E.mild_units({"goat": {"g1": None, "g2": -6.0, "g3": -2.0}, "bks": {"b1": None}, "cap1": {"c1": None}}, cls_of)
    assert mild["goat"] == {"g2"}                                                # at or under the crunch median, -4
    active = {"g1": {"A": 0.9, "B": 0.7}, "g2": {"A": 0.85}, "g3": {"A": 0.9}, "b1": {"A": 0.95}, "p1": {"A": 0.9},
              "c1": {"A": 0.9}}
    pool, out = E.eligible(parts, mild, active, heard={"b1", "c1"})
    assert [p["unit"] for p in pool] == ["g2", "b1", "p1"]
    assert out == {"not judgeable (activity)": 1, "crunch over the set's median": 1, "heard before (strict set)": 1}
    assert next(p for p in pool if p["unit"] == "b1")["heard"] is True           # BKS keeps heard units, last


def test_the_renders_refuse_a_draw_file_the_ledger_does_not_hold():
    assert "no phase_lear_draw" in E.draw_refusal({"phase_lear": "x"}, "ab" * 32)
    assert "not the ledger's" in E.draw_refusal({"phase_lear_draw": {"sha256": "cd" * 32}}, "ab" * 32)
    assert E.draw_refusal({"phase_lear_draw": {"sha256": "ab" * 32}}, "ab" * 32) is None


def test_the_guards():
    assert E.guard("Cen", 1.0, "h", "h") == "hash" and E.guard("M", 1.0, "h", "x") == "failed"
    assert E.guard("rc", 1.0, "h", None) == "failed"
    assert E.guard("S", 1.0, "h", None, 1.004) == "j0" and E.guard("S", 1.0, "h", None, 1.01) == "failed"
    assert E.guard("L", 1.0, "h", "h", 2.0) == "hash" and E.guard("L", 1.0, "h", "x", 1.002) == "j0"
    assert E.guard("L", 1.0, "h", "x", 1.2) == "failed" and E.guard("S", None, "h", None, 1.0) == "failed"


def test_identical_presets_share_a_letter_and_spares_replace_put_out_cards():
    assert E.groups_of({"S": "a", "Cen": "b", "M": "c", "rc": "b", "L": "d"}) == [("S",), ("Cen", "rc"), ("M",), ("L",)]
    cards = [{"key": "k1", "set": "goat", "cls": "clean"}, {"key": "k2", "set": "goat", "cls": "crunch"},
             {"key": "k3", "set": "bks", "cls": "clean"}]
    spares = [{"key": "s1", "set": "goat", "cls": "clean"}, {"key": "s2", "set": "goat", "cls": "crunch"},
              {"key": "s3", "set": "goat", "cls": "crunch"}]
    got, subs = E.substitute(cards, spares, bad={"k2", "k3", "s2"})
    assert [c["key"] for c in got] == ["k1", "s3"] and subs == [("k2", "s3"), ("k3", None)]


def _page_cards(n=22):
    return [{"key": f"k{i}", "set": "goat", "cls": ("clean", "crunch")[i % 2], "unit": f"goat/item_{i}#0", "cluster": f"item_{i}",
             "slug": f"slug{i:04d}",
             "amp": AMPS[i % 3], "held": "B", "groups": [("S",), ("Cen",), ("M",), ("rc",), ("L",)] if i % 5
             else [("S",), ("Cen", "rc"), ("M",), ("L",)]} for i in range(n)]


def test_the_page_order_hears_each_card_once_and_one_clean_and_one_crunch_again():
    items = E.page_order(_page_cards(), 1)
    first = [it for it in items if it["repeat_of"] is None]
    reps = [it for it in items if it["repeat_of"]]
    assert len(items) == 24 and len(first) == 22 and sorted(r["cls"] for r in reps) == ["clean", "crunch"]
    by = {it["id"]: it for it in items}
    for r in reps:
        f = by[r["repeat_of"]]
        assert r["n"] - f["n"] >= E.GAP and all(r["letters"][k] != f["letters"][k] for k in r["letters"])
    assert all(sorted(c for g in it["letters"].values() for c in g) == sorted(E.CANDS) for it in items)
    assert all(sorted(it["letters"]) in (list("ABCDE"), list("ABCD")) for it in items)
    assert E.page_order(_page_cards(), 1) == items and E.page_order(_page_cards(), 2) != items


def test_unblinding_allows_ties_shared_letters_and_takes_out_cant_judge():
    it = {"letters": {"A": ("S",), "B": ("Cen", "rc"), "C": ("M",), "D": ("L",)}}
    h = E.unblind(it, {"rank": {"A": 4, "B": 1, "C": 1, "D": 2}, "close": {"A": "far"}})
    assert h["Cen"]["rank"] == h["rc"]["rank"] == 1 and h["S"]["close"] == 0 and h["M"]["close"] is None
    assert E.pref(h, "M", "Cen") == 0.5 and E.pref(h, "L", "S") == 1.0 and E.pref(h, "S", "M") == 0.0
    assert E.unblind(it, {"rank": {"A": 1, "B": 1, "C": 1}}) is None
    assert E.unblind(it, {"rank": {"A": 5, "B": 1, "C": 1, "D": 1}}) is None    # ranks 1 to the letter count
    assert E.unblind(it, {"rank": {"A": 1, "B": 1, "C": 1, "D": 1}, "scope": True}) is None
    assert E.same_letter(it, "Cen", "rc") and not E.same_letter(it, "Cen", "M")


def test_the_sign_test():
    assert E.sign_p(3, 3) == pytest.approx(0.125) and E.sign_p(5, 5) == pytest.approx(1 / 32)
    assert E.sign_p(0, 0) == 1.0 and E.sign_p(0, 4) == 1.0


def _card(i, ranks, j0, cluster=None, letters=None):
    letters = letters or {L: (c,) for L, c in zip("ABCDE", E.CANDS)}
    heard = {c: {"rank": ranks[c], "close": None} for c in E.CANDS}
    return {"id": f"i{i}", "set": "goat", "cls": "clean", "amp": "pr12", "cluster": cluster or f"c{i}", "heard": heard,
            "j0": j0, "item": {"letters": letters, "repeat_of": None, "id": f"i{i}"}}


J0 = {"L": 0.6, "Cen": 0.9, "rc": 0.92, "M": 0.95, "S": 1.0}


def test_a_pair_heard_above_on_few_untied_cards_is_not_firmly_above():
    cards = [_card(i, {"L": 1, "Cen": 2, "rc": 2, "M": 2, "S": 2 if i >= 3 else 3}, J0) for i in range(22)]
    row = E.pair_row(cards, "Cen", "S")                                          # 19 ties, 3 above, none below
    assert (row["above"], row["ties"], row["below"]) == (3, 19, 0)
    assert row["reading"] == E.HEARD_ABOVE and row["firmly"] is None and row["sign_p_above"] == pytest.approx(0.125)
    cards = [_card(i, {"L": 1, "Cen": 2, "rc": 2, "M": 2, "S": 2 if i >= 8 else 3}, J0) for i in range(22)]
    row = E.pair_row(cards, "Cen", "S")
    assert row["firmly"] == "above" and row["j0_first_closer"] == 22 and row["j0_agrees_untied"] == 8


def test_a_pair_on_one_letter_is_left_out_and_counted():
    shared = {"A": ("S",), "B": ("Cen", "rc"), "C": ("M",), "D": ("L",)}
    cards = [_card(0, {"L": 1, "Cen": 2, "rc": 2, "M": 3, "S": 4}, J0, letters=shared)] + \
        [_card(i, {"L": 1, "Cen": 2, "rc": 3, "M": 4, "S": 5}, J0) for i in range(1, 6)]
    row = E.pair_row(cards, "rc", "Cen")
    assert row["cards"] == 5 and row["same_letter"] == 1 and row["below"] == 5


def _rows(**readings):
    rows = {f"{a} over {b}": {"reading": E.HEARD_ABOVE, "firmly": "above"} for a, b in E.KEY_PAIRS}
    rows["M over Cen"] = rows["rc over Cen"] = {"reading": E.NOT_KNOWN, "firmly": None}
    for k, (r, f) in readings.items():
        rows[k.replace("_", " ")] = {"reading": r, "firmly": f}
    return rows


def test_the_outcome_table_takes_the_first_row_that_holds():
    up, down, nk = (E.HEARD_ABOVE, "above"), (E.HEARD_BELOW, "below"), (E.NOT_KNOWN, None)
    assert E.outcome(17, _rows(), 0.9)["row"] == 1
    assert E.outcome([22, 17], _rows(), 0.9)["row"] == 1                        # each sitting at least 18
    o = E.outcome(22, _rows(Cen_over_S=down), 0.9)
    assert (o["letter"], o["row"], o["named"]) == ("b", 2, ["Cen over S"])
    assert E.outcome(22, _rows(Cen_over_S=(E.HEARD_BELOW, None)), 0.9)["letter"] != "b"   # below, not firmly
    assert E.outcome(22, _rows(), 0.45)["named"] == ["A1"]
    assert E.outcome(22, _rows(L_over_S=nk), 0.9)["row"] == 3
    o = E.outcome(22, _rows(rc_over_Cen=up), 0.9)
    assert (o["letter"], o["row"], o["named"]) == ("b", 4, ["rc over Cen"])
    assert E.outcome(22, _rows(M_over_Cen=(E.HEARD_ABOVE, None)), 0.9)["letter"] == "a"  # above, not firmly
    o = E.outcome(22, _rows(M_over_Cen=down), 0.9)
    assert (o["letter"], o["row"], o["M over Cen"]) == ("a", 5, E.HEARD_BELOW)
    o = E.outcome(22, _rows(Cen_over_S=nk), None)
    assert (o["letter"], o["row"], o["named"]) == ("c", 6, ["Cen over S"])
    with pytest.raises(SystemExit):
        E.outcome(22, {"L over S": {"reading": E.HEARD_ABOVE, "firmly": "above"}}, 0.9)


def test_heard_pair_agreement_and_the_order_within_a_card():
    cards = [_card(i, {"L": 1, "Cen": 2, "rc": 2, "M": 3, "S": 4}, J0) for i in range(4)]
    a1 = E.a1_rows(cards, drop=("L",))
    assert a1["pairs"] == 4 * 5 and a1["j0"]["mean"] == 1.0                     # Cen-rc tied by ear: left out
    assert a1["fixed"]["mean"] == 1.0 and a1["j0_less_fixed"]["mean"] == 0.0
    a2 = E.a2_rows(cards)
    assert a2["cards"] == 4 and a2["j0"]["mean"] == pytest.approx(0.975, abs=1e-3)
    flat = [_card(i, {c: 1 for c in E.CANDS}, J0) for i in range(3)]
    assert E.a2_rows(flat)["all_equal"] == 3
    a4 = E.a4_rows(cards)
    assert sum(r["pairs"] for r in a4.values()) == 40
    assert a4["under 0.05"]["ties"] == 4 and a4["0.15 and over"]["agreement"] == 1.0


def test_the_repeats_and_the_holm_correction():
    it0 = {"id": "i1", "repeat_of": None, "letters": {L: (c,) for L, c in zip("ABCDE", E.CANDS)}}
    it1 = {"id": "i9", "repeat_of": "i1", "letters": it0["letters"]}
    h0 = {c: {"rank": r, "close": None} for c, r in zip(E.CANDS, (5, 2, 3, 2, 1))}
    h1 = {c: {"rank": r, "close": None} for c, r in zip(E.CANDS, (5, 2, 3, 3, 1))}
    assert E.a5_rows([it0, it1], {"i1": h0, "i9": h1}) == [{"id": "i9", "repeat_of": "i1", "pairs": 10, "same": 8}]
    assert E.holm({"a": 0.01, "b": 0.04, "c": None}) == {"a": 0.02, "b": 0.04, "c": None}


def test_the_read_pools_sittings_and_reports_every_declared_pair():
    items = E.page_order(_page_cards(), 1)
    for it in items:
        it.update({"set": "goat", "j0": dict(J0)})
    order = {"L": 1, "Cen": 2, "rc": 2, "M": 3, "S": 4}
    got = {it["id"]: {"rank": {L: order[g[0]] for L, g in it["letters"].items()}} for it in items}
    rep = E.ear_read([(items, got)])
    assert rep["ranked"] == [22] and set(rep["rows"]) == {f"{a} over {b}" for a, b in E.KEY_PAIRS + E.BESIDE_PAIRS}
    assert rep["outcome"]["letter"] == "a" and rep["outcome"]["M over Cen"] == E.HEARD_BELOW
    assert rep["A5"] and all(r["same"] == r["pairs"] for r in rep["A5"])
    pooled = E.ear_read([(items, got), (items, got)])
    assert pooled["ranked"] == [22, 22] and pooled["rows"]["Cen over S"]["cards"] == 44


def test_the_player_takes_five_letters_the_mark_and_the_times():
    js = E.player_js()
    assert 'E: "E"' in js and 'e: "E"' in js and '"6": "E"' in js and "t_play" in js and "t_last" in js
    assert 'querySelector(".scope")' in js and "ladder-ear:" in js and "real-song-exam" not in js
    assert ".rank.n5" in E.CSS_EXTRA
    items = E.page_order(_page_cards(), 1)
    html = E.cards_html(items[:2], 24)
    assert "Can&#x27;t judge" in html or "Can't judge" in html
    assert 'class="rank n5"' in html or 'class="rank n4"' in html


def test_the_artifact_page_wraps_and_names_nothing():
    pytest.importorskip("numpy")
    items = E.page_order(_page_cards(), 1)[:12]
    clips = {f"{it['id']}-{k}": "AA==" for it in items for k in ["ref", *it["letters"]]}
    page, css, js = E.page_html(items, clips, "b0", 24)
    art = E.artifact_page(page, css, js, 1)
    assert "<title>Five Presets Check 1</title>" in art and 'window.claude.use("db")' in art
    assert E.page_leaks(page.split('<script id="clips"')[0], _page_cards()) == []
    assert E.page_leaks("xx u3|k zz", [{"unit": "u3|k", "key": "k3", "cluster": "c3", "slug": "s3"}]) == ["u3|k"]


def test_the_level_guard():
    assert E.level_refusal({"ref": -23.0, "S": -23.2, "M": -23.6, "L": None}) == ["L", "M"]


def test_the_simulated_reading_is_the_jackknife_t_and_the_coded_outcome():
    np = pytest.importorskip("numpy")
    from learn import pretrain_set as PS
    from learn import score_ear as SE

    rng = np.random.default_rng(1)
    x = E.sim_prefs(rng, 40, 22, 0.73, 0.2)
    r = E.sim_read(x)
    for d in range(5):
        iv = SE.interval([(f"c{i}", float(v)) for i, v in enumerate(x[d])], PS.t90)
        assert r["lo"][d] == pytest.approx(iv["lo"]) and r["hi"][d] == pytest.approx(iv["hi"])
    sims = {k: E.sim_read(E.sim_prefs(rng, 300, 22, s, t)) for k, s, t in (
        ("L over S", 0.8, 0.1), ("L over Cen", 0.75, 0.2), ("Cen over S", 0.6, 0.3), ("M over Cen", 0.6, 0.6),
        ("rc over Cen", 0.4, 0.5))}
    got = E.sim_outcome(sims)
    for d in range(300):
        rows = {k: {"reading": E.HEARD_ABOVE if v["above"][d] else E.HEARD_BELOW if v["below"][d] else E.NOT_KNOWN,
                    "firmly": "above" if v["firm_above"][d] else "below" if v["firm_below"][d] else None}
                for k, v in sims.items()}
        assert E.outcome(22, rows, None)["letter"] == got[d]


def test_the_power_tables_run_and_hold_the_null_near_its_level():
    pytest.importorskip("numpy")
    out = E.power_tables(draws=3000)
    null = next(r for r in out["one_pair"] if r["share"] == 0.5 and r["tie"] == 0.0)
    assert 0.02 < null["above_22"] < 0.10 and null["firm_above_22"] <= null["above_22"]
    strong = next(r for r in out["one_pair"] if r["share"] == 0.9)
    assert strong["above_22"] > 0.95
    assert out["ranges"]["declared_b"][1] >= out["ranges"]["first_b"][1] and out["ranges"]["forced_b"][1] >= \
        out["ranges"]["declared_b"][1]
