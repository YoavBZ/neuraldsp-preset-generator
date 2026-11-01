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
