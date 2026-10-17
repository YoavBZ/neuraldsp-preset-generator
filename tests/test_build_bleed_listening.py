from collections import Counter

import pytest

from learn import build_bleed_listening as M


def test_draw_has_the_declared_trials():
    trials = M.draw()
    assert len(trials) == 6
    assert Counter(t["kind"] for t in trials) == {"high": 3, "low": 2, M.REPEAT: 1}
    assert {(t["slug"], t["held"]) for t in trials if t["kind"] == "high"} == set(M.HIGH)
    assert {t["slug"] for t in trials if t["kind"] == "low"} == set(M.LOW)
    rep = next(i for i, t in enumerate(trials) if t["kind"] == M.REPEAT)
    src = next(i for i, t in enumerate(trials) if t["kind"] == "low" and t["slug"] == trials[rep]["slug"])
    assert trials[src]["held"] == trials[rep]["held"]
    assert rep > 0 and abs(rep - src) > 1
    assert M.draw() == trials                                         # seeded
    assert any(M.draw(seed=s) != trials for s in range(1, 5))


def test_letters_balanced_and_repeat_identical():
    for seed in range(20):
        trials = M.draw(seed=seed)
        ls = M.letters(trials, seed=seed)
        for t, l in zip(trials, ls):
            assert sorted(l) == ["A", "B"]
            if t["kind"] == M.REPEAT:
                assert l == {"A": "original", "B": "original"}
            else:
                assert sorted(l.values()) == ["cleaned", "original"]
        on_a = sum(l["A"] == "cleaned" for l in ls)
        assert on_a in (2, 3)
    assert M.letters(M.draw()) == M.letters(M.draw())


def test_parse_answers():
    got = M.parse_answers("1A-no 2n-little 3Both-lot 4b-a-lot 5?-no 6A-?")
    assert got == {"1": ("A", "no"), "2": ("N", "little"), "3": ("Both", "lot"), "4": ("B", "lot"),
                   "5": (None, "no"), "6": ("A", None)}
    assert M.parse_answers("1A-a lot") == {"1": ("A", "lot")}
    with pytest.raises(SystemExit):
        M.parse_answers("1C-no")
    with pytest.raises(SystemExit):
        M.parse_answers("1A")


def _key():
    trials = [{"slug": "h1", "held": "B", "kind": "high"}, {"slug": "c1", "held": "A", "kind": "low"},
              {"slug": "h2", "held": "A", "kind": "high"}, {"slug": "c1", "held": "A", "kind": M.REPEAT}]
    ls = [{"A": "original", "B": "cleaned"}, {"A": "cleaned", "B": "original"},
          {"A": "cleaned", "B": "original"}, {"A": "original", "B": "original"}]
    return {"trials": {str(i): {**t, "letters": l, "bleed_removed_db": -10.0}
                       for i, (t, l) in enumerate(zip(trials, ls), 1)}}


def test_scoring_maps_letters_to_roles():
    rep = M.score_key(_key(), M.parse_answers("1A-no 2N-little 3A-lot 4B-no"))
    rows = {r["trial"]: r for r in rep["trials"]}
    assert rows[1]["leak_names"] == "original"
    assert rows[2]["leak_names"] == "neither"
    assert rows[3]["leak_names"] == "cleaned"
    assert rows[4]["leak_names"] == "a letter"
    assert rep["high"]["leak"] == {"original": 1, "cleaned": 1, "both": 0, "neither": 0, "unanswered": 0}
    assert rep["high"]["damage"] == {"no": 1, "little": 0, "lot": 1, "unanswered": 0}
    assert rep["low"]["leak"]["neither"] == 1 and rep["low"]["damage"]["little"] == 1
    assert rep["repeat"] == {"repeat_trial": 4, "control_trial": 2,
                             "repeat": {"leak": "a letter", "damage": "no"},
                             "control": {"leak": "neither", "damage": "little"}}


def test_scoring_unanswered_and_both():
    rep = M.score_key(_key(), M.parse_answers("1Both-no"))
    assert rep["trials"][0]["leak_names"] == "both"
    assert rep["high"]["leak"]["unanswered"] == 1
    assert rep["low"]["damage"]["unanswered"] == 1
    assert rep["repeat"]["repeat"] == {"leak": None, "damage": None}
