import pytest

from learn import record_match_listening as M


def _rows():
    rows = []
    for i in range(10):
        rows.append({"slug": f"p{i}", "band": f"b{i // 2}", "cls": "clean" if i % 3 else "crunch",
                     "snr": 1.0 - i / 10, "flags": {"A": "low", "B": "low"}, "act": {"A": 1.0, "B": 1.0}})
    rows[0]["flags"]["B"] = "high"
    rows[3]["act"] = {"A": 0.5, "B": 0.7}
    rows[4]["act"] = {"A": 0.9, "B": 1.0}
    return rows


def _s_raw(rows):
    return {r["slug"]: {"pr12": {"A": 3.0, "B": 2.0}, "sw50r": {"A": 2.0, "B": 3.0}, "ac20": {"A": 2.5, "B": 2.5}}
            for r in rows}


def test_choose_applies_the_rule():
    rows = _rows()
    out = M.choose(rows, _s_raw(rows))
    slugs = [p["slug"] for p in out]
    assert "p0" not in slugs and "p3" not in slugs                    # bleed, inactive
    assert len(slugs) == 5 and len({p["band"] for p in out}) == 5      # one per band
    assert all(sum(p["cls"] == c for p in out) <= 3 for c in ("clean", "crunch"))
    p4 = next(p for p in out if p["slug"] == "p4")
    assert p4["held"] == "B" and p4["search"] == "A" and p4["amp"] == "sw50r"   # amp by the search half only
    assert M.choose(list(reversed(rows)), _s_raw(rows)) == out


def test_choose_refuses_too_few():
    rows = _rows()[:4]
    with pytest.raises(SystemExit):
        M.choose(rows, _s_raw(rows))


def test_draw_letters_and_repeat():
    parts = [{"slug": f"p{i}"} for i in range(5)]
    tr = M.draw(parts)
    assert len(tr) == 6 and sorted(t["slug"] for t in tr[:5]) == [f"p{i}" for i in range(5)]
    assert all(sorted(t["letters"].values()) == sorted(M.ARMS) for t in tr)
    src = tr[5]["repeat_of"]
    assert 1 <= src <= 4 and tr[src - 1]["slug"] == tr[5]["slug"]
    assert tr[src - 1]["letters"] != tr[5]["letters"]
    assert M.draw(parts) == tr and M.draw(parts, seed=1) != tr


def test_parse_answers():
    a = M.parse_answers("1 B>D>A>C very; 2 ?>?>?>? ?; 3 a>b>c>d not")
    assert a[1] == (["B", "D", "A", "C"], "very")
    assert a[2] == (None, None)
    assert a[3] == (["A", "B", "C", "D"], "not")
    assert M.parse_answers("4 A>A>B>C some")[4] == (None, "some")
    with pytest.raises(SystemExit):
        M.parse_answers("garbage")


def test_spearman_and_ranks():
    assert M.ranks([3.0, 1.0, 2.0, 2.0]) == [4.0, 1.0, 2.5, 2.5]
    assert M.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert M.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)


def test_score_maps_letters_to_arms():
    judge = {"S": 4.0, "H": 3.0, "D": 5.0, "C": 2.0}
    letters = {"A": "S", "B": "H", "C": "D", "D": "C"}
    key = {"trials": {"1": {"slug": "p", "repeat_of": None, "letters": letters, "judge_held": judge},
                      "2": {"slug": "p", "repeat_of": 1, "letters": {"A": "C", "B": "D", "C": "H", "D": "S"},
                            "judge_held": judge}}}
    rep = M.score_key(key, M.parse_answers("1 D>B>A>C very; 2 A>C>D>B some"))
    t1 = rep["trials"][0]
    assert t1["arm_ranks"] == {"C": 1, "H": 2, "S": 3, "D": 4}
    assert t1["rho"] == pytest.approx(1.0)                             # same order as the judge
    assert rep["beats_S"] == {"C": 1, "H": 1, "D": 0}
    assert rep["mean_rank"]["C"] == 1 and rep["answered"] == 1
    assert rep["repeat"]["rho"] == pytest.approx(1.0) and rep["repeat"]["same_close"] is False
    assert rep["close"] == {"very": 1, "some": 0, "not": 0}


def test_common_gains_one_loudness_without_clipping():
    t, g = M.common_gains([-25.0, -18.0], [0.2, 0.5])
    assert t == -20.0 and g[0] == pytest.approx(10 ** 0.25) and g[1] == pytest.approx(10 ** -0.1)
    t, g = M.common_gains([-25.0, -30.0], [0.9, 0.5])            # clip 1 would peak at 0.9*10^0.25
    assert t == pytest.approx(-25.0) and 0.9 * g[0] == pytest.approx(0.9) and 0.5 * g[1] <= 0.9
