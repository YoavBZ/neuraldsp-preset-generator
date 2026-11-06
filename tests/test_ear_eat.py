"""The EfficientAT ear page's pure parts (`learn/ear_eat.py`)."""
import pytest

pytest.importorskip("numpy")

from learn import ear_eat as Q


def rows():
    out = []
    for a in Q.AMPS:
        for c in Q.CLASSES:
            for st in Q.SETS:
                for j in range(6):
                    out.append({"cell": (a, c), "set": st, "take": f"{a}{c}{st}{j}", "key": f"{a}{c}{st}{j}", "cluster": f"{st}{j % 4}"})
    return out


def test_one_part_of_each_set_per_cell_and_no_take_twice():
    got = Q.pick(rows())
    assert len(got) == len(Q.AMPS) * len(Q.CLASSES) * len(Q.SETS)
    assert len({r["take"] for r in got}) == len(got)
    assert all(sum(r["cell"] == c and r["set"] == s for r in got) == 1 for c in {r["cell"] for r in got} for s in Q.SETS)


def test_clusters_are_spread():
    got = Q.pick(rows())
    n = {}
    for r in got:
        n[r["cluster"]] = n.get(r["cluster"], 0) + 1
    assert max(n.values()) - min(n.values()) <= 1 and len(n) == 8


def test_a_shared_take_is_not_drawn_twice_across_cells():
    r = rows()
    for q in r:
        q["take"] = q["take"][-3:] + q["take"][-1]      # the same takes in every cell
    got = Q.pick(r)
    assert len({q["take"] for q in got}) == len(got)


def test_the_draw_is_stable():
    assert [r["key"] for r in Q.pick(rows())] == [r["key"] for r in Q.pick(rows())]


def test_unblind_needs_every_rank_and_rating():
    item = {"letters": dict(zip(Q.LETTERS, Q.CANDS))}
    ans = {"rank": dict(zip(Q.LETTERS, (1, 2, 3, 4, 5))), "close": {k: "close" for k in Q.LETTERS}}
    got = Q.unblind(item, ans)
    assert got["S"] == {"rank": 1, "close": 2} and got["label"]["rank"] == 5
    assert Q.unblind(item, {"rank": {"A": 1}, "close": {}}) is None


def test_rows_read_first_hearings_and_leave_out_of_scope_cards():
    items = [{"id": "i1", "repeat_of": None, "cluster": "x"}, {"id": "i2", "repeat_of": None, "cluster": "y"},
             {"id": "i3", "repeat_of": "i1", "cluster": "x"}]
    good = {c: {"rank": 5 - j, "close": min(j, 3)} for j, c in enumerate(Q.CANDS)}       # label first, S last
    bad = {c: {"rank": j + 1, "close": 0} for j, c in enumerate(Q.CANDS)}
    t = Q.share_rows(items, {"i1": good, "i2": good, "i3": bad})
    assert t["EW-mix over FTm"]["parts"] == 2
    assert t["EW-mix over FTm"]["share"]["share"] == 1.0
    assert Q.share_rows(items, {"i1": good, "i2": good, "i3": bad}, ["i2"])["FTm over S"]["parts"] == 1
    assert Q.table(items, {"i1": good, "i2": good})["label"]["firsts"] == 2


def test_chance_rarely_clears_and_a_sure_thing_does():
    clusters = [f"c{i}" for i in range(12)]
    got = Q.simulate(clusters, shares=(0.5, 0.95), pages=60, n=200)
    assert got["0.5"] < 0.2 and got["0.95"] > 0.8
