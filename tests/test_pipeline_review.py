import math

import pytest

from learn import pipeline_review as P


def test_switch_values_read_as_bools():
    assert P.on("true") and P.on("True") and P.on(1) and P.on(True) and P.on("1.0")
    assert not P.on("false") and not P.on(0) and not P.on(None) and not P.on("0")


def test_quantiles_interpolate_and_handle_empty():
    q = P.quantiles([1, 2, 3, 4, 5])
    assert q == {"0.1": 1.4, "0.5": 3, "0.9": pytest.approx(4.6)}
    assert P.quantiles([]) == {"0.1": None, "0.5": None, "0.9": None}


def test_section_parts_split_on_the_last_at():
    assert P.section_parts("sets-1-2/A_Full/30_ElecGtr4DI.wav@145.0") == ("sets-1-2/A_Full/30_ElecGtr4DI.wav", 145.0)


def test_early_stop_overlap_counts_session_di_and_time():
    train = ["s/X/a.wav@0.0", "s/X/a.wav@20.0", "s/Y/b.wav@0.0"]
    es = ["s/X/a.wav@5.0",      # same DI, overlaps the 0-10 s section
          "s/X/a.wav@40.0",     # same DI, no overlap
          "s/X/c.wav@0.0",      # same session only
          "s/Z/d.wav@0.0"]      # nothing shared
    assert P.es_overlap(train, es) == {"es_sections": 4, "share_session": 3, "share_di": 2, "overlap_in_time": 1}


def test_band_weighted_averages_parts_then_bands():
    rows = [("b1", "p1", 1.0), ("b1", "p1", 3.0),     # p1 = 2
            ("b1", "p2", 0.0),                        # p2 = 0 -> b1 = 1
            ("b2", "p3", -1.0)]                       # b2 = -1
    r = P.band_weighted(rows)
    assert r["band_weighted_mean"] == 0.0
    assert r["bands"] == 2 and r["bands_worse"] == 1 and r["bands_better"] == 1
    assert r["per_part"] == {"p1": 2.0, "p2": 0.0, "p3": -1.0}
    assert r["lo90"] is None                          # no t value stored for 1 df


def test_band_weighted_interval_with_seven_bands_matches_the_t_rule():
    rows = [(f"b{i}", f"p{i}", float(i)) for i in range(7)]
    r = P.band_weighted(rows)
    half = P.T_95[6] * math.sqrt(sum((i - 3) ** 2 for i in range(7)) / 6) / math.sqrt(7)
    assert r["band_weighted_mean"] == 3.0
    assert r["hi90"] - 3.0 == pytest.approx(half) and 3.0 - r["lo90"] == pytest.approx(half)


def test_mismatch_share_compares_switch_states():
    assert P.mismatch_share([("true", "false"), ("true", True), ("false", "0")]) == (1, 3)


def test_every_check_is_named_after_its_step():
    assert all(k == f.__name__.split("_")[0] and k[0] == "s" and k[1:].isdigit() for k, f in P.CHECKS.items())


def test_missing_data_is_reported_not_raised(tmp_path):
    out = P.run(tmp_path, only=["s16"])
    assert out["checks"]["s16_stem"]["step"] == 16 and "missing" in out["checks"]["s16_stem"]


def test_every_check_reports_missing_on_an_empty_data_root(tmp_path):
    out = P.run(tmp_path)["checks"]
    assert len(out) == len(P.CHECKS)
    assert all("missing" in v for v in out.values()), [k for k, v in out.items() if "missing" not in v]


def test_band_weighted_reports_parts_and_leave_one_band_out():
    r = P.band_weighted([("b1", "p1", 1.0), ("b1", "p2", -1.0), ("b2", "p3", 2.0), ("b3", "p4", 3.0)])
    assert r["parts"] == 4 and r["parts_worse"] == 3
    assert r["leave_one_band_out"] == {"b1": 2.5, "b2": 1.5, "b3": 1.0}


def test_pick_start_takes_the_lowest_median_of_half_means_with_ties_by_name():
    def part(a, b):
        return {"flat|pr12|measfix_A": a, "flat|pr12|measfix_B": b}
    files = [{"x": part({"factory:B": [2.0, 0, 0], "factory:A": [2.0, 0, 0], "template:T": [0.1, 0, 0]},
                        {"factory:B": [4.0, 0, 0], "factory:A": [4.0, 0, 0], "template:T": [0.1, 0, 0]})},
             {"y": part({"factory:B": [1.0, 0, 0], "factory:A": [1.0, 0, 0], "factory:C": [0.0, 0, 0]},
                        {"factory:B": [1.0, 0, 0], "factory:A": [1.0, 0, 0], "factory:C": [0.0, 0, 0]})}]
    best, med, n = P.pick_start(files, ["x", "y", "z"], "pr12")
    assert (best, med, n) == ("factory:A", 2.0, 2)      # C lacks part x, the template is not a candidate, A < B by name
    assert P.pick_start(files, ["z"], "pr12") == (None, None, 0)
