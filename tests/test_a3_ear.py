"""A3 by ear (`learn/a3_ear.py`): the candidates and the draw, the roles, the read and the declared rule, the page's
leaks and the launcher."""

import pathlib

from learn import a3_ear as A


def _units():
    out = [{"set": "panel", "unit": f"panel/s{i}/di@{i}.0#amp.wav", "cluster": f"panel/s{i}/di", "cls": "clean",
            "lag": 0} for i in range(5)]
    out += [{"set": "cap1", "unit": f"cap/u{i}#sw50r", "cluster": f"creator{i % 20}", "cls": "clean" if i % 2 else "crunch",
             "lag": -3} for i in range(60)]
    out += [{"set": "goat", "unit": "goat/x", "cluster": "it", "cls": "clean", "lag": 0},
            {"set": "cap1", "unit": "cap/nolag", "cluster": "creatorX", "cls": "clean", "lag": None}]
    return out


def _picks(units):
    picks = {u["unit"]: {"A": "pr12", "B": "sw50r"} for u in units}
    heads = {u["unit"]: {"A": "sw50r", "B": "sw50r"} for u in units}
    return picks, heads


def test_candidates_are_the_deciding_sets_lagged_directions_where_pick_and_head_differ():
    units = _units()
    c = A.candidates(units, *_picks(units))
    assert "it" not in c and "creatorX" not in c
    assert all(d["search"] == "A" and d["held"] == "B" and d["pick"] == "pr12" and d["head"] == "sw50r"
               for v in c.values() for d in v)
    assert len(c) == 25 and sum(len(v) for v in c.values()) == 65


def test_the_draw_takes_every_panel_di_then_one_direction_per_cap1_creator_seeded():
    units = _units()
    c = A.candidates(units, *_picks(units))
    items = A.draw(c)
    assert len(items) == A.N_ITEMS and len({it["cluster"] for it in items}) == A.N_ITEMS
    assert sum(it["set"] == "panel" for it in items) == 5
    assert A.draw(c) == items and len({it["slug"] for it in items}) == A.N_ITEMS


def _page():
    units = _units()
    items = A.draw(A.candidates(units, *_picks(units)))
    page = A.C4.page_order(items, seed=A.PAGE_SEED, cands=A.AMPS)
    for it in page:
        it["j0"] = {"pr12": 1.0, "sw50r": 1.2, "ac20": 2.0}
    return page


def _answer(page, order):
    got = {}
    for it in page:
        inv = {a: k for k, a in it["letters"].items()}
        got[it["id"]] = {"rank": {inv[a]: r for a, r in order.items()}}
    return got


def test_the_page_plays_the_three_amps_once_each_with_two_repeats():
    page = _page()
    assert len(page) == A.N_ITEMS + 2 and all(sorted(it["letters"].values()) == sorted(A.AMPS) for it in page)


def test_the_read_scores_the_pick_over_the_head_and_over_sw50r_on_differing_items():
    page = _page()
    rep = A.ear_read(page, _answer(page, {"pr12": 1, "sw50r": 2, "ac20": 3}))
    assert rep["read"] == A.N_ITEMS and rep["rows"]["pick over head"]["above"] == A.N_ITEMS
    assert rep["verdicts"]["pick over head"] == "above" and rep["outcome"] == "keep"
    assert rep["rows"]["head over sw50r"]["cards"] == 0                        # the head is the sw50r: nothing to read
    assert rep["rows"]["pick over head"]["j0_agrees"]["agree"] == A.N_ITEMS
    assert rep["ranked_first_alone"]["pick"] == A.N_ITEMS and len(rep["repeats"]) == 2


def test_the_rule_sends_the_ear_below_to_the_user_and_ties_count_half():
    page = _page()
    rep = A.ear_read(page, _answer(page, {"pr12": 3, "sw50r": 1, "ac20": 2}))
    assert rep["verdicts"]["pick over head"] == "below" and rep["outcome"] == "user"
    tie = A.ear_read(page, _answer(page, {"pr12": 1, "sw50r": 1, "ac20": 1}))
    assert tie["rows"]["pick over head"]["ties"] == A.N_ITEMS and tie["outcome"] == "keep"
    assert tie["ranked_first_alone"]["tied first"] == A.N_ITEMS
    assert A.outcome("undecided", "below", False) == "user" and A.outcome("below", "above", True) == "not read"


def test_too_few_answers_leave_the_page_unread():
    page = _page()
    got = _answer(page, {"pr12": 1, "sw50r": 2, "ac20": 3})
    first = [it["id"] for it in page if it["repeat_of"] is None]
    rep = A.ear_read(page, {k: v for k, v in got.items() if k in first[:A.MIN_READ - 1]})
    assert rep["page_failed"] and rep["outcome"] == "not read"


def test_the_page_names_no_amp():
    items = _page()
    assert A.leaks("a page with sw50r on it", items) == ["sw50r"]
    assert A.leaks("<h1>Which preset</h1>", items) == []


def test_the_launcher_draws_renders_in_three_shards_then_builds_the_page():
    s = (pathlib.Path(__file__).parents[1] / "logs" / "launch-a3.zsh").read_text()
    assert "setopt no_bg_nice" in s and "acquire_render_slot" in s
    assert s.index("a3-draw") < s.index("a3-render") < s.index("a3-page")
    assert "--shard ${k}/3" in s


def test_the_canary_refuses_a_clip_whose_judge_differs_from_the_stored_one():
    it = {"set": "cap1", "unit": "cap/u1#sw50r", "search": "A", "key": "cap/u1#sw50r|A", "slug": "s1"}
    stored = {("cap1", it["unit"], a): {"A": {"A": 1.0, "B": 2.0}, "B": {"A": 9.0, "B": 9.0}} for a in A.AMPS}
    recs = {"s1": {"cands": {a: {"judge": {"A": 1.0, "B": 2.0}} for a in A.AMPS}}}
    assert A.canary([it], recs, stored) == []
    recs["s1"]["cands"]["ac20"]["judge"]["B"] = 2.1
    assert len(A.canary([it], recs, stored)) == 1
    assert len(A.canary([it], recs, {})) == 6
