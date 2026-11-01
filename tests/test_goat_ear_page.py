"""5C's ear page's pure parts (`learn/goat_ear_page.py`)."""
from learn import goat_ear_page as G


def test_flagged_is_outside_either_range():
    ref = {"hi_db": (-30.0, -10.0), "lo_db": (-5.0, 5.0)}
    assert not G.flagged({"hi_db": -20.0, "lo_db": 0.0}, ref)
    assert G.flagged({"hi_db": -35.0, "lo_db": 0.0}, ref)
    assert G.flagged({"hi_db": -20.0, "lo_db": 6.0}, ref)


def test_pick_keeps_every_flagged_unit_and_fills_the_sample():
    units = [f"u{j}" for j in range(40)]
    flags = {u: j % 10 == 0 for j, u in enumerate(units)}
    got = G.pick(units, flags, 12)
    assert len(got) == 12 and {u for u in units if flags[u]} <= set(got)
    assert G.pick(units, flags, 12) == got
    assert sorted(G.pick(units, flags)) == sorted(units)


def test_heavy_page_asks_the_heavy_question_and_exports_as_its_own_page():
    items = [{"id": "heavy-a", "unit": "u"}]
    page = G.page_html(items, {"heavy-a-1": "", "heavy-a-2": ""}, "b1", 1, 1, 1, G.HEAVY)
    assert '"page": "goat-heavy"' in page and 'data-v="keep"' in page and 'data-v="heavy"' in page
    assert 'data-v="amp"' not in page
    ear = G.page_html(items, {"heavy-a-1": "", "heavy-a-2": ""}, "b1", 1, 1, 1)
    assert '"page": "goat-ear"' in ear and 'data-v="amp"' in ear


def test_firmly_driven_follows_the_classifier_split():
    import pathlib

    import pytest

    from learn import pretrain_set as PS

    if not (pathlib.Path(PS.HOME) / "references/datasets-set3/_tools/classify.py").exists():
        pytest.skip("the pool's classifier is not on this machine")
    assert G.firmly_driven({"nonlinear_to_linear_db": 0.5, "level_slope": 0.2})
    assert not G.firmly_driven({"nonlinear_to_linear_db": -1.0, "level_slope": 0.2})
    assert not G.firmly_driven({})
