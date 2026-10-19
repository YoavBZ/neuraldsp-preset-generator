import math

from learn import shrink_vs_snr as S


def unit(band, snr, d_best, d_half, d_s, slug=None):
    return {"stage": "F", "arm": "H", "slug": slug or band, "band": band, "cls": "clean", "snr": snr,
            "d": {1.0: d_best, 0.5: d_half, 0.0: d_s}}


def test_rule_and_thresholds():
    assert S.rule_f((1.0, 0.0, 1.0), 0.5) == 0.0
    assert S.rule_f((1.0, 0.0, 1.0), 1.0) == 1.0
    assert S.rule_f((-math.inf, 0.5, 0.5), -3.0) == 0.5
    assert S.thresholds([0.0, 2.0, math.inf]) == [-math.inf, 1.0, 1e9]


def test_fit_finds_an_snr_split_and_keeps_the_recipe_on_ties():
    units = [unit(f"lo{i}", 0.2, 2.0, 1.0, 1.5) for i in range(3)] + \
            [unit(f"hi{i}", math.inf, 1.0, 2.0, 3.0) for i in range(3)]
    rule, v = S.fit(units, (0.0, 0.5, 1.0))
    assert rule[1:] == (0.5, 1.0) and rule[0] > 0.2 and v < 0
    flat = [unit(f"b{i}", 0.2, 1.0, 1.0, 1.0) for i in range(3)]
    assert S.fit(flat, (0.0, 0.5, 1.0))[0] == (-math.inf, 0.5, 0.5)


def test_cross_validation_holds_each_band_out():
    units = [unit(f"lo{i}", 0.2, 2.0, 1.0, 1.5) for i in range(3)] + \
            [unit(f"hi{i}", math.inf, 1.0, 2.0, 3.0) for i in range(3)]
    gains, rules = S.cross_validate(units, (0.0, 0.5, 1.0))
    assert set(rules) == {u["band"] for u in units}
    assert all(g["f"] == (1.0 if g["band"].startswith("hi") else 0.5) for g in gains)
