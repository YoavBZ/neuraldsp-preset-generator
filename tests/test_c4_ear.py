"""C4 by ear (`learn/c4_ear.py`): the draw's items, the page order and letters, the tie-aware unblinding, the pairwise
shares and the declared rule, the cards, the player and the launcher."""

import pathlib

import pytest

from learn import c4_ear as C


def _items(n=18):
    return [{"unit": f"cap/u{i}#sw50r", "key": f"cap/u{i}#sw50r|sw50r", "amp": "sw50r", "cls": "clean" if i % 9 else "crunch",
             "cluster": f"lib/di{i % 10}.wav", "search": "A", "held": "B", "slug": f"cap__u{i}_sw50r"} for i in range(n)]


def test_the_page_order_hears_each_item_once_then_two_repeats_with_rotated_letters():
    items = C.page_order(_items())
    first = [it for it in items if it["repeat_of"] is None]
    reps = [it for it in items if it["repeat_of"]]
    assert len(first) == 18 and len(reps) == 2 and len(items) == 20
    assert all(sorted(it["letters"].values()) == sorted(C.CANDS) for it in items)
    by = {it["id"]: it for it in items}
    for r in reps:
        f = by[r["repeat_of"]]
        assert r["n"] - f["n"] >= C.GAP and all(r["letters"][k] != f["letters"][k] for k in C.LETTERS)
    assert C.page_order(_items()) == items                                       # seeded


def test_unblinding_allows_ties_and_needs_every_letter():
    it = {"letters": {"A": "S", "B": "adopted", "C": "FTm"}}
    h = C.unblind(it, {"rank": {"A": 2, "B": 1, "C": 1}})
    assert h["adopted"]["rank"] == 1 and h["FTm"]["rank"] == 1 and h["S"]["rank"] == 2
    assert C.pref(h, "adopted", "FTm") == 0.5 and C.pref(h, "adopted", "S") == 1.0 and C.pref(h, "S", "FTm") == 0.0
    assert C.unblind(it, {"rank": {"A": 1, "B": 2}}) is None


def test_the_rule_keeps_the_adopted_model_unless_the_ear_puts_it_below():
    assert C.outcome("above", "undecided", False) == "keep" and C.outcome("undecided", "above", False) == "keep"
    assert C.outcome("below", "above", False) == "user" and C.outcome("undecided", "below", False) == "user"
    assert C.outcome("below", "below", True) == "not read"


def test_the_read_counts_pairs_from_first_hearings_and_repeats_apart():
    items = C.page_order(_items())
    for it in items:
        it["j0"] = {"adopted": 1.0, "FTm": 1.2, "S": 2.0}
    got = {}
    for it in items:
        inv = {c: k for k, c in it["letters"].items()}
        got[it["id"]] = {"rank": {inv["adopted"]: 1, inv["FTm"]: 2, inv["S"]: 3}}
    rep = C.ear_read(items, got)
    assert rep["read"] == 18 and not rep["page_failed"] and rep["rows"]["adopted over FTm"]["above"] == 18
    assert rep["verdicts"]["adopted over FTm"] == "above" and rep["outcome"] == "keep"
    assert all(r["agree"] for r in rep["repeats"]) and len(rep["repeats"]) == 2
    assert rep["rows"]["adopted over S"]["j0_agrees"]["agree"] == 18


def test_the_cards_and_player_hold_three_letters_with_ties():
    html = C.cards(C.page_order(_items())[:1])
    assert html.count('data-r="3"') == 3 and 'data-k="C"' in html and 'data-k="D"' not in html
    js = C.player_js()
    assert "delete r[o]" not in js and '"D"' not in js and 'KEYS = ["ref", "A", "B", "C"]' in js


def test_the_page_names_no_unit_di_or_preset():
    items = _items(2)
    assert C.leaks("Recording 1 A B C Record", items) == []
    assert "cap/u0#sw50r" in C.leaks("x cap/u0#sw50r y", items) and "FTm" in C.leaks("FTm", items)


def test_the_launcher_runs_lags_inputs_items_answers_clips_page_on_slot_locks():
    t = (pathlib.Path(__file__).resolve().parents[1] / "logs" / "launch-c4.zsh").read_text()
    order = [t.index(x) for x in ("three lags", "run inputs", "run draw", "run answers", "three render", "run page")]
    assert order == sorted(order) and "acquire_render_slot" in t and "--capture-batch 3" in t and "train-ft" not in t
