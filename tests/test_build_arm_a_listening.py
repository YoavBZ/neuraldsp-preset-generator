import math
from collections import Counter

import pytest

from learn import build_arm_a_listening as M


def _rows():
    rows = []
    for b in range(14):
        for amp in ("pr12", "sw50r", "ac20"):
            for search, held in (("A", "B"), ("B", "A")):
                ratio = math.exp(0.01 if (b + len(amp)) % 5 == 0 else (-0.1 if search == "A" else 0.05))
                rows.append({"slug": f"part{b}", "band": f"band{b}", "cls": "clean", "amp": amp,
                             "search": search, "held": held, "d_S": 3.0, "d_armA": 3.0 * ratio})
    return rows


def test_eligible_keeps_audible_pairs_only():
    rows = _rows() + [{"slug": "x", "band": "x", "cls": "clean", "amp": "pr12", "search": "A", "held": "B",
                       "d_S": 3.0, "d_armA": math.inf}]
    pool = M.eligible(rows)
    assert pool and all(abs(r["log"]) >= 0.03 for r in pool)
    assert all(r["slug"] != "x" for r in pool)
    assert len(pool) == sum(abs(math.log(r["d_armA"] / r["d_S"])) >= 0.03 for r in _rows())


def test_draw_respects_bands_quota_and_seed():
    pool = M.eligible(_rows())
    trials = M.draw(pool)
    tests = [t for t in trials if t["kind"] == "test"]
    catch = [t for t in trials if t["kind"] == M.CATCH]
    assert len(tests) == 8 and len(catch) == 1
    assert Counter(t["amp"] for t in tests) == Counter(M.QUOTA)
    assert len({t["band"] for t in trials}) == 9                      # one per band, catch included
    assert trials.index(catch[0]) >= 1                                # never trial 1
    assert M.draw(list(reversed(pool))) == trials                     # input order does not matter
    assert M.draw(pool, seed=1) != trials


def test_draw_does_not_lower_the_bar():
    pool = [r for r in M.eligible(_rows()) if r["amp"] != "ac20"]
    with pytest.raises(SystemExit):
        M.draw(pool)


def test_letters_random_seeded_and_catch_same():
    trials = [{"kind": "test"}] * 40 + [{"kind": M.CATCH}]
    ls = M.letters(trials)
    assert ls[-1] == {"A": "S", "B": "S"}
    assert all(sorted(x.values()) == ["S", "armA"] for x in ls[:-1])
    pos = [x["A"] == "armA" for x in ls[:-1]]
    assert sum(pos) == 20                                             # balanced
    assert M.letters(trials, seed=1) != ls
    assert any(pos[i] == pos[i + 1] for i in range(39))              # not a strict alternation
    assert M.letters(trials) == ls


def test_parse_answers():
    assert M.parse_answers("1A 2b 3S 4?") == {"1": "A", "2": "B", "3": "S"}
    with pytest.raises(SystemExit):
        M.parse_answers("1C")


def test_clopper_pearson_known_values():
    lo, hi = M.clopper_pearson(0, 8)
    assert lo == 0 and hi == pytest.approx(1 - 0.05 ** (1 / 8), abs=1e-9)
    lo, hi = M.clopper_pearson(8, 8)
    assert hi == 1 and lo == pytest.approx(0.05 ** (1 / 8), abs=1e-9)
    lo, hi = M.clopper_pearson(4, 8)
    assert lo == pytest.approx(1 - hi, abs=1e-9) and lo == pytest.approx(0.192903, abs=1e-6)   # scipy beta.ppf(0.05, 4, 5)
    assert M.clopper_pearson(6, 8) == pytest.approx((0.400311, 0.953611), abs=1e-6)


def test_score_maps_letters_to_arms():
    key = {"trials": {
        "1": {"kind": "test", "slug": "p1", "amp": "pr12", "judge_log": -0.1, "letters": {"A": "armA", "B": "S"}},
        "2": {"kind": "test", "slug": "p2", "amp": "pr12", "judge_log": 0.1, "letters": {"A": "S", "B": "armA"}},
        "3": {"kind": M.CATCH, "slug": "p3", "amp": "ac20", "judge_log": -0.2, "letters": {"A": "S", "B": "S"}},
        "4": {"kind": "test", "slug": "p4", "amp": "sw50r", "judge_log": -0.05, "letters": {"A": "S", "B": "armA"}},
        "5": {"kind": "test", "slug": "p5", "amp": "ac20", "judge_log": -0.05, "letters": {"A": "S", "B": "armA"}},
    }}
    rep = M.score_key(key, M.parse_answers("1A 2B 3S 4S"))
    out = [r["outcome"] for r in rep["trials"]]
    assert out == ["armA", "armA", "same", "same", None]
    assert rep["armA_share"]["k"] == 2 and rep["armA_share"]["n"] == 2
    assert rep["armA_share_same_as_not"]["n"] == 3 and rep["same"] == 1
    assert rep["judge_agreement"] == {"agree": 1, "n": 2}               # trial 2: judge preferred S
    assert rep["per_amp"]["pr12"] == {"armA": 2, "S": 0, "same": 0, "unanswered": 0}
    assert rep["per_amp"]["ac20"]["unanswered"] == 1
    assert rep["catch"] == {"trial": 3, "outcome": "same"}
    assert M.score_key(key, M.parse_answers("3A"))["catch"]["outcome"] == "letter"
