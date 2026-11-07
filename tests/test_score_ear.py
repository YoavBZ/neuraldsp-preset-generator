"""N11's rows (`learn/score_ear.py`): pure parts."""
import math

import pytest

from learn import score_ear as E


def t90(_df):
    return 2.0


def card(i, ear, j0, cluster=None, page="p"):
    return {"page": page, "id": i, "cluster": cluster or i, "ear": {c: {"rank": r, "close": 3 - r} for c, r in ear.items()}, "j0": j0}


def test_spearman_handles_ties_and_refuses_no_spread():
    assert E.spearman([1, 2, 3], [10, 20, 30]) == pytest.approx(1.0)
    assert E.spearman([1, 2, 3], [30, 20, 10]) == pytest.approx(-1.0)
    assert E.spearman([1, 2, 3], [5, 5, 5]) is None
    assert E.ranks([2, 1, 2]) == [2.5, 1.0, 2.5]


def test_a_card_under_three_candidates_gives_no_order():
    c = card("a", {"S": 1, "m": 2}, {"S": 1.0, "m": 2.0})
    assert E.j0_rho(c) is None and E.s_last_rho(c) is None


def test_s_last_reads_the_order_without_any_score():
    c = card("a", {"S": 3, "x": 1, "y": 2}, {"S": 9.0, "x": 1.0, "y": 2.0})
    assert E.s_last_rho(c) == pytest.approx(math.sqrt(3) / 2)
    assert E.s_last_rho(c, ("S",)) is None


def test_mean_rank_leaves_the_card_out():
    a = card("a", {"x": 1, "y": 2, "z": 3}, {"x": 1.0, "y": 2.0, "z": 3.0})
    b = card("b", {"x": 3, "y": 2, "z": 1}, {"x": 1.0, "y": 2.0, "z": 3.0})
    pc = E.per_card([a, b])
    assert pc[0]["mean_rank"] == pytest.approx(-1.0) and pc[1]["mean_rank"] == pytest.approx(-1.0)


def test_a_sibling_card_lends_the_fixed_order_nothing():
    a = card("a", {"x": 1, "y": 2, "z": 3}, {"x": 1.0, "y": 2.0, "z": 3.0}, cluster="band")
    b = card("b", {"x": 1, "y": 2, "z": 3}, {"x": 1.0, "y": 2.0, "z": 3.0}, cluster="band")
    c = card("c", {"x": 3, "y": 2, "z": 1}, {"x": 1.0, "y": 2.0, "z": 3.0}, cluster="other")
    assert E.per_card([a, b, c])[0]["mean_rank"] == pytest.approx(-1.0)        # c alone, not b


def test_a_dropped_label_gives_its_place_back_to_the_ranks():
    a = card("a", {"label": 1, "x": 2, "y": 3, "z": 4}, {"label": 1.0, "x": 1.0, "y": 2.0, "z": 3.0})
    assert E.reranked(a, ["x", "y", "z"]) == {"x": 1.0, "y": 2.0, "z": 3.0}


def test_added_recomputes_the_fixed_order_at_each_deletion():
    cards = [card(str(i), {"x": 1 + (i % 3 == 0), "y": 2 - (i % 3 == 0), "z": 3}, {"x": 1.0, "y": 2.0, "z": 3.0}, cluster=f"b{i // 2}")
             for i in range(8)]
    r = E.added_row(cards, t90)
    want = E.added(cards)
    assert r["mean"] == pytest.approx(want) and r["clusters"] == 4 and r["df"] == 3
    th = [E.added([c for c in cards if c["cluster"] != f"b{k}"]) for k in range(4)]
    mt = sum(th) / 4
    assert r["se"] == pytest.approx(math.sqrt(3 / 4 * sum((x - mt) ** 2 for x in th)))


def test_interval_clusters_cards_of_one_band():
    pairs = [("a", 1.0), ("a", 1.0), ("b", 0.0), ("c", 0.5), (None, None)]
    r = E.interval([p for p in pairs if p[0]], t90)
    assert r["clusters"] == 3 and r["cards"] == 4 and r["mean"] == pytest.approx(0.625)
    assert r["lo"] < r["mean"] < r["hi"] and r["df"] == 2


def test_welch_takes_two_independent_rows():
    a = {"mean": 0.6, "se": 0.1, "df": 8}
    b = {"mean": 0.4, "se": 0.1, "df": 7}
    r = E.welch(a, b, t90)
    assert r["diff"] == pytest.approx(0.2) and r["hi"] - r["lo"] == pytest.approx(4 * math.sqrt(0.02))
    assert 14 < r["df"] < 16


def test_side_of_s_counts_only_real_agreement():
    c = card("a", {"S": 2, "x": 1, "y": 3}, {"S": 2.0, "x": 1.0, "y": 1.0})
    assert E.side_of_s([c]) == {"x": {"same": 1, "of": 1}, "y": {"same": 0, "of": 1}}


def test_pairs_leave_s_and_labels_out_and_sort_by_jos_gap():
    c = card("a", {"S": 4, "label": 1, "x": 2, "y": 3, "z": 5}, {"S": 9.0, "label": 1.0, "x": 2.0, "y": 8.0, "z": 3.0})
    got = E.pairs_of([c])
    assert [(r["a"], r["b"], r["agree"]) for r in got] == [("x", "y", True), ("z", "y", False), ("x", "z", True)]


def test_gap_bins_are_equal_count():
    pairs = [{"lnr": v, "agree": v > 0.5} for v in (1.0, 0.8, 0.4, 0.1)]
    got = E.gap_bins(pairs, 2)
    assert [b["agree"] for b in got] == [1.0, 0.0]


def test_claim_row_reads_models_only_against_s():
    c = card("a", {"S": 3, "label": 1, "x": 2}, {"S": 4.0, "label": 1.0, "x": 2.0})
    assert E.claim_pairs([c]) == [("a", pytest.approx(math.log(2)), 1)]


def test_page_rows_read_what_j0_adds():
    cards = [card(str(i), {"S": 3, "x": 1 + i % 2, "y": 2 - i % 2}, {"S": 9.0, "x": 1.0 + i % 2, "y": 2.0 - i % 2}) for i in range(4)]
    rows = E.page_rows(cards, t90)
    assert rows["j0"]["mean"] == pytest.approx(1.0)
    assert rows["j0_less_s_last"]["mean"] == pytest.approx(1 - math.sqrt(3) / 2)
    assert rows["j0_less_mean_rank"]["clusters"] == 4


def unit(i, band, cls, amp, di):
    return {"unit": f"u{i}", "player": band, "cls": cls, "amp": amp, "di": f"x/{di}.wav"}


def wide_units():
    out, n = [], 0
    for band, cls, amp, dis in (("Ale Lak", "crunch", "pr12", ("a1", "a2", "a3")), ("Dark Ride", "crunch", "ac20", ("d1", "d2", "d3")),
                                ("Renesans", "crunch", "sw50r", ("r1",)), ("Rebuild The Evil", "crunch", "sw50r", ("21_ElecGtr3DI", "23_ElecGtr4DI")),
                                ("Rebuild The Evil", "clean", "sw50r", ("23_ElecGtr4DI",)), ("Storm Of Particles", "clean", "pr12", ("s1", "s2", "s3")),
                                ("Cnoc An Tursa", "clean", "ac20", ("c1", "c2")), ("Death Of A Romantic", "clean", "ac20", ("o1",)),
                                ("The Long Wait", "clean", "pr12", ("l1",)), ("The Travelling Band", "clean", "ac20", ("t1",))):
        for di in dis:
            n += 1
            out.append(unit(n, band, cls, amp, di))
    return out


def test_the_draw_fills_every_slot_and_keeps_a_bands_dis_apart():
    cards, spares = E.draw_cards(wide_units())
    assert len(cards) == 14 and len(spares) == 2
    assert sum(u["cls"] == "crunch" for u in cards) == 6
    by = {}
    for u in cards:
        by.setdefault(u["player"], []).append(u)
    assert all(len({u["di"] for u in v}) == len(v) <= 2 for v in by.values())
    assert [u["player"] for u in spares] == ["Ale Lak", "Dark Ride"]
    assert all(u["di"] not in {c["di"] for c in cards if c["player"] == u["player"]} for u in spares)
    assert E.draw_cards(wide_units()) == (cards, spares)
    assert [E.di_stem(u) for u in cards if u["player"] == "Rebuild The Evil" and u["cls"] == "crunch"] == ["21_ElecGtr3DI"]


def test_the_page_order_repeats_one_of_each_class_and_never_a_spare():
    cards, spares = E.draw_cards(wide_units())
    items = E.page_order(cards, spares, E.CANDS, tuple("ABCDE"))
    again = [it for it in items if it["repeat_of"]]
    assert len(items) == 18 and len(again) == 2 and {it["cls"] for it in again} == {"clean", "crunch"}
    assert not any(it["spare"] for it in again)
    ids = {it["id"]: it for it in items}
    assert all(sorted(it["letters"].values()) == sorted(E.CANDS) for it in items)
    assert all(it["letters"][k] != ids[it["repeat_of"]]["letters"][k] for it in again for k in "ABCDE")


def test_a_spare_fills_only_for_a_crunch_card_out():
    items = [{"id": "a", "repeat_of": None, "spare": False, "cls": "crunch"}, {"id": "b", "repeat_of": None, "spare": False, "cls": "clean"},
             {"id": "d", "repeat_of": None, "spare": True, "cls": "crunch", "band": "Dark Ride"},
             {"id": "c", "repeat_of": None, "spare": True, "cls": "crunch", "band": "Ale Lak"},
             {"id": "e", "repeat_of": "a", "spare": False, "cls": "crunch"}]
    heard = {k: {"S": {"rank": 1}} for k in "abcde"}
    assert [it["id"] for it in E.filled(items, heard, set())] == ["a", "b"]
    assert [it["id"] for it in E.filled(items, heard, {"b"})] == ["a"]
    assert [it["id"] for it in E.filled(items, heard, {"a"})] == ["b", "c"]


def test_holm_steps_down():
    assert E.holm({"a": 0.01, "b": 0.04, "c": 0.5}) == {"a": 0.03, "b": 0.08, "c": 0.5}
    assert E.sign_p(3, 3) == pytest.approx(0.125)


def test_added_row_counts_only_clusters_with_a_value():
    good = [card(str(i), {"x": 1 + i % 2, "y": 2 - i % 2, "z": 3}, {"x": 1.0, "y": 2.0, "z": 3.0}, cluster=f"b{i}") for i in range(4)]
    two = [card("t", {"x": 1, "y": 2}, {"x": 1.0, "y": 2.0}, cluster="short")]
    assert E.added_row(good + two, t90)["clusters"] == 4


def test_the_failure_rule_counts_after_the_spares():
    assert E.failed(11) is False                                 # 3 unfilled
    assert E.failed(10) is True


def test_repeat_rhos_pair_by_page_position():
    rows = [{"heard": {"x": {"rank": 1}, "y": {"rank": 2}, "z": {"rank": 3}}, "repeat_of": None}, {"heard": None, "repeat_of": None},
            {"heard": {"x": {"rank": 2}, "y": {"rank": 1}, "z": {"rank": 3}}, "repeat_of": "i1"}, {"heard": None, "repeat_of": "i1"}]
    assert E.repeat_rhos(rows) == [pytest.approx(0.5)]
