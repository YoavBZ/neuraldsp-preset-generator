"""L1a's ear check (`learn/capture_ear.py`): pure parts."""
import random

from learn import capture_ear as C


def units():
    return [{"unit": f"cap/u{j}#a", "placebo": f"cap/p{j}#a", "amp": "ab"[j % 2], "cls": ("clean", "crunch")[j % 3 % 2],
             "creator": f"k{j % 8}", "held": "AB"[j % 2], "search": "BA"[j % 2]} for j in range(12)]


def test_letters_balance_over_the_first_hearings_and_a_repeat_moves_every_candidate():
    items = C.draw(units())
    assert items == C.draw(units()) and len(items) == 14
    first = [it for it in items if it["repeat_of"] is None]
    count = {}
    for it in first:
        for k, c in it["letters"].items():
            count[(k, c)] = count.get((k, c), 0) + 1
    assert set(count.values()) == {4} and len(count) == 9
    by = {it["id"]: it for it in items}
    rep = [it for it in items if it["repeat_of"]]
    assert len(rep) == 2
    for it in rep:
        a = by[it["repeat_of"]]
        assert all(a["letters"][k] != it["letters"][k] for k in C.LETTERS)
        assert it["n"] - a["n"] >= C.REPEAT_GAP


def test_unblind_needs_all_three_and_maps_letters():
    it = {"letters": {"A": "label", "B": "S", "C": "placebo"}}
    full = {"rank": {"A": 1, "B": 2, "C": 3}, "close": {"A": "very", "B": "some", "C": "far"}}
    got = C.unblind(it, full)
    assert got["label"] == {"rank": 1, "close": 3} and got["S"]["rank"] == 2
    assert C.unblind(it, {"rank": {"A": 1, "B": 2}, "close": full["close"]}) is None


def fake(seed=1, p=1.0):
    rng = random.Random(seed)
    items, heard = [], {}
    for j in range(12):
        i = f"i{j}"
        items.append({"id": i, "repeat_of": None, "unit": f"u{j}", "creator": f"k{j % 8}", "amp": "pr12", "cls": "clean",
                      "judge": {"S": 5.0, "label": 4.0, "placebo": 4.5}})
        up = rng.random() < p
        heard[i] = {"label": {"rank": 1 if up else 3, "close": 3}, "S": {"rank": 3 if up else 1, "close": 1},
                    "placebo": {"rank": 2, "close": 2}}
    return items, heard


def test_report_reads_pairwise_and_names_the_primary_branch():
    items, heard = fake(p=1.0)
    rep = C.report(items, heard)
    assert rep["primary"]["rank"]["share"] == 1.0 and rep["branch"] == "clear above"
    assert rep["label_vs_placebo"]["rank"]["share"] == 1.0 and rep["placebo_vs_S"]["rank"]["share"] == 1.0
    assert rep["primary"]["score"]["mean"] > 0            # plus: the score also puts the label closer
    items, heard = fake(p=0.0)
    assert C.report(items, heard)["branch"] == "clear below"


def test_chance_clears_rarely_at_the_declared_size():
    wide = 0
    for s in range(60):
        items, heard = fake(seed=s, p=0.5)
        lo, hi = C.boot_share([(it["creator"], float(heard[it["id"]]["label"]["rank"] == 1)) for it in items], n=400, seed=s)
        wide += lo > 0.5
    assert wide <= 8


def test_page_js_has_three_letters_only():
    js = C.page_js()
    assert '"D"' not in js and 'ear-vreal' not in js and 'KEYS = ["ref", "A", "B", "C"]' in js
