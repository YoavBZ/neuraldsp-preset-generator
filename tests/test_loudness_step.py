"""LS, the loudness step (`learn/loudness_step.py`): the matched gain and its clamp, the settings copy, the read, and the
launcher."""

import pathlib

from learn import loudness_step as L


def test_the_matched_gain_closes_the_mean_gap_on_the_stock_dis():
    g, want, short = L.matched_gain(8.0, [-20.0, -22.0], [-25.0, -27.0])
    assert want == 5.0 and g == 13.0 and short == 0.0


def test_the_gain_is_clamped_to_the_control_and_the_shortfall_kept():
    g, want, short = L.matched_gain(20.0, [-10.0, -10.0], [-20.0, -20.0])
    assert g == 24.0 and want == 10.0 and short == 6.0
    g, _, short = L.matched_gain(-20.0, [-30.0], [-10.0])
    assert g == -24.0 and short == -16.0


def test_with_output_copies_the_settings():
    s = {"parameters/outputGain": 8.0, "pr12Amp/pr12Volume": 0.5}
    t = L.with_output(s, 3.5)
    assert t["parameters/outputGain"] == 3.5 and s["parameters/outputGain"] == 8.0 and t["pr12Amp/pr12Volume"] == 0.5


def _rec(i, s, u, m, g0=8.0, g=None, short=0.0):
    return {"set": "c4" if i % 2 else "a3", "cls": "clean" if i % 3 else "crunch", "amp": "sw50r", "g0": g0,
            "gain": g0 + (m - u) if g is None else g, "want": m - u, "short": short,
            "own": {"S": s, "unmatched": u, "matched": m}, "peaks": {"S": -3.0, "unmatched": 2.0, "matched": -2.0}}


def test_the_read_reports_gaps_clamps_linearity_and_peaks():
    recs = [_rec(i, -20.0, -26.0, -20.5) for i in range(6)] + [_rec(9, -18.0, -10.0, -14.0, g0=20.0, g=24.0, short=4.0)]
    recs[-1]["gain"] = 24.0
    recs[-1]["own"]["matched"] = recs[-1]["own"]["unmatched"] + 4.0
    rep = L.report(recs)
    assert rep["items"] == 7 and rep["clamped"] == 1 and rep["shortfalls (dB)"] == [4.0]
    assert rep["gap to S, unmatched (dB)"]["median"] == 6.0 and rep["gap to S, matched (dB)"]["median"] == 0.5
    assert rep["linearity"]["holds"] and rep["reading"] == "closer"
    assert rep["peaks over 0 dBFS"] == {"S": 0, "unmatched": 7, "matched": 0}


def test_a_broken_gain_shows_in_the_linearity_check():
    r = _rec(1, -20.0, -26.0, -20.0)
    r["gain"] = r["g0"] + 3.0                     # the control moved 3 dB but the level moved 6
    assert not L.report([r])["linearity"]["holds"]


def test_the_launcher_runs_the_table_then_three_shards_then_the_report():
    s = (pathlib.Path(__file__).parents[1] / "logs" / "launch-ls.zsh").read_text()
    assert "setopt no_bg_nice" in s and "acquire_render_slot" in s
    assert s.index("ls-draw") < s.index("ls-table") < s.index("ls-render") < s.index("ls-report")
    assert "--shard ${k}/3" in s
