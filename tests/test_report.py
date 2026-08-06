"""The HTML report: self-contained, honest, and readable when there is nothing to say.

Most of what could go wrong here is a report that looks right and is not: a number
without the caveat that qualifies it, an unmeasured dimension shown as a zero, a
chart drawn from one candidate and captioned as if it were all of them. Those are
what these check.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy", reason="needs the analysis extra")

from analysis.fingerprint import Fingerprint
from match import report as R
from match.search import Candidate
from match.store import Run, Store, Trial


def printed(*, bands=None, dynamics=None) -> Fingerprint:
    """A Fingerprint with only the sections a chart reads, built by hand.

    Rendering audio for a layout test would make the layout test depend on the
    chain, which is how a report test ends up failing for a reason in the DSP.
    """
    centres = [100.0, 200.0, 400.0, 800.0, 1600.0, 3200.0]
    levels = bands if bands is not None else [-10.0, -8.0, -6.0, -7.0, -9.0, -14.0]
    return Fingerprint(
        source={"sha256": "a" * 64, "sample_rate": 48000},
        spectrum={"band_centres_hz": centres, "band_db": levels},
        dynamics=dynamics or {"crest_db": 12.0, "attack_ms": 8.0},
    )


def candidate(total: float, **dimensions) -> Candidate:
    objectives = {"total": total, **dimensions}
    return Candidate(values={("sw50rAmp", "sw50rVolume"): 70.0},
                     objectives=objectives, total=total)


def test_a_report_reaches_nothing_outside_itself():
    """It has to render a year later next to the store it came from, so no CDN, no
    `<img src>`, no script tag, no web font."""
    html = R.render_report(run_id="r", target=printed(),
                           shortlist=[candidate(0.4, timbre=0.4)],
                           caveats=["one thing to distrust"],
                           fingerprints={0: printed()})

    assert "<svg" in html, "the charts are inline SVG"
    for forbidden in ("http://", "https://", "<script", "src=", "@import",
                      "url("):
        assert forbidden not in html, forbidden
    assert html.startswith("<!doctype html>")
    assert html.rstrip().endswith("</html>")


def test_the_caveats_come_before_the_charts():
    """Not decoration and not a footnote: they are what the charts do not show, and a
    number presented without them is a measurement presented as a verdict."""
    html = R.render_report(run_id="r", target=printed(),
                           shortlist=[candidate(0.4, timbre=0.4)],
                           caveats=["the equaliser basis is not measured"],
                           fingerprints={0: printed()})

    assert html.index("What to distrust") < html.index("<svg")
    assert html.index("What to distrust") < html.index("Shortlist")
    assert "the equaliser basis is not measured" in html


def test_an_unmeasured_dimension_is_a_dash_not_a_zero():
    """A zero would say "perfect on this dimension" about a dimension nothing could
    measure, which is the one mistake the whole objective design exists to avoid.

    A dimension *nobody* measured is left out of the table entirely rather than shown
    as a column of dashes, so the case that matters is a dimension one side has and
    the other does not — which is the real situation: a reverb tail measurable in the
    target and not in a dry candidate.
    """
    html = R.render_report(
        run_id="r", target=printed(),
        shortlist=[candidate(0.4, timbre=0.4),
                   candidate(0.5, timbre=0.5, ambience=0.2)],
        seed_objectives={"total": 0.9, "timbre": 0.9, "ambience": 0.8})

    table = html.split("Objectives, per dimension")[1].split("</table>")[0]
    assert "ambience" in table
    assert "—" in table, "candidate #1 has no ambience, so it cannot be 0.000"
    assert "0.200" in table and "0.800" in table

    # And a dimension nobody measured is not a column at all.
    assert "spatial" not in table


def test_a_caveat_cannot_inject_markup():
    """Caveats come from `invert()` and the search, which build them from measured
    values — but a pack manifest supplies parameter names, and a report is a file
    someone opens in a browser."""
    html = R.render_report(run_id="<script>bad()</script>", target=printed(),
                           shortlist=[candidate(0.4)],
                           caveats=["<img onerror=bad()>"])

    assert "<script>bad()" not in html
    assert "<img onerror" not in html
    assert "&lt;script&gt;" in html


def test_a_run_with_nothing_to_report_says_so():
    """Every trial failed or came back silent. The report must not render an empty
    shortlist as a successful match with a blank table."""
    html = R.render_report(run_id="r", target=printed(), shortlist=[],
                           summary={"trials": 40, "failures": 40,
                                    "failure_rate": 1.0})

    assert "nothing to report" in html
    assert "Accounting" in html and "40" in html
    assert "<svg" not in html, "there is nothing to plot"


def test_no_caveats_is_reported_as_unusual_rather_than_as_success():
    html = R.render_report(run_id="r", target=printed(),
                           shortlist=[candidate(0.4)], caveats=[])
    assert "unusual" in html


def test_the_headline_has_no_grade():
    """There is no measured threshold that makes 0.39 "good": the loss profile's
    scales are tunable data, so a letter would invent a calibration nobody has done.
    """
    html = R.render_report(run_id="r", target=printed(),
                           shortlist=[candidate(0.394)],
                           seed_objectives={"total": 1.151})

    assert "0.394" in html
    assert "66% closer" in html, "the change is stated, the quality is not"
    for verdict in ("excellent", "good match", "grade", "score of A", "★"):
        assert verdict not in html.lower()


def test_the_shortlist_shows_what_each_candidate_changed():
    """The diff is the deliverable — a person reads the report to learn which knobs
    moved, not to admire a number."""
    seed = {("sw50rAmp", "sw50rVolume"): 50.0,
            ("sw50rAmp", "sw50rTreble"): 50.0,
            ("delay", "delayActive"): False}
    winner = Candidate(values={("sw50rAmp", "sw50rVolume"): 78.0,
                               ("sw50rAmp", "sw50rTreble"): 50.0,
                               ("delay", "delayActive"): True},
                       objectives={"total": 0.4}, total=0.4)
    html = R.render_report(run_id="r", target=printed(), shortlist=[winner],
                           seed=seed)

    assert "sw50rAmp/sw50rVolume" in html and "78" in html
    assert "delay/delayActive" in html and "on" in html
    assert "sw50rTreble" not in html.split("Shortlist")[1].split("</table>")[0], (
        "a control that did not move is not a change"
    )


def test_a_rounding_difference_is_not_reported_as_a_change():
    """A quantised knob can differ from the seed by 1e-16 through the normalised
    round trip, which is not a change anyone made."""
    seed = {("sw50rAmp", "sw50rVolume"): 50.0}
    same = Candidate(values={("sw50rAmp", "sw50rVolume"): 50.0000000001},
                     objectives={"total": 0.4}, total=0.4)
    html = R.render_report(run_id="r", target=printed(), shortlist=[same], seed=seed)
    assert "nothing moved from the seed" in html


def test_the_screen_table_distinguishes_frozen_from_unmeasurable():
    """"Moved the objective by 0.0" and "could not be measured at all" are different
    findings, and only one of them is a measurement."""
    import math

    html = R.render_report(
        run_id="r", target=printed(), shortlist=[candidate(0.4)],
        searched=["sw50rAmp/sw50rVolume"],
        frozen={"parameters/outputGain": 0.004,
                "parameters/gateThreshold": math.nan},
    )

    assert "0.0040" in html
    assert "not measured" in html
    assert "sw50rAmp/sw50rVolume" in html and "searched" in html


def test_the_convergence_chart_is_best_so_far_and_not_per_trial():
    """A per-trial trace of a stochastic optimiser is noise. Best-so-far is what
    shows whether it stopped improving — and a flat trace has to look flat."""
    trace = [{"total": 1.0}, {"total": 1.4}, {"total": 0.6}, {"total": 0.9}]
    html = R.render_report(run_id="r", target=printed(),
                           shortlist=[candidate(0.6)], convergence=trace)

    block = html.split("Convergence")[1]
    points = block.split("points='")[1].split("'")[0].split()
    ys = [float(p.split(",")[1]) for p in points]
    # Lower is closer, and y grows downwards in SVG, so best-so-far never rises.
    assert all(later >= earlier for earlier, later in zip(ys, ys[1:])), ys


def test_a_single_convergence_point_draws_no_chart():
    """One point is not a trajectory, and an axis with a dot on it invites reading a
    trend that is not there."""
    html = R.render_report(run_id="r", target=printed(),
                           shortlist=[candidate(0.4)],
                           convergence=[{"total": 0.4}])
    assert "Convergence" not in html


def test_the_accounting_keeps_the_failure_causes_apart():
    html = R.render_report(run_id="r", target=printed(), shortlist=[candidate(0.4)],
                           summary={"trials": 100, "failures": 3, "errors": 1,
                                    "silent": 2, "failure_rate": 0.03,
                                    "wall_ms": 1234.5, "renders": 96,
                                    "cache_hits": 4})
    block = html.split("Accounting")[1]
    for needle in ("100", "errors", "silent", "cache hits", "4"):
        assert needle in block, needle


def test_summarise_merges_the_store_and_the_search():
    """Kept out of `store.py` because only the search knows its cache hits — there is
    no column that records one."""
    with Store() as store:
        store.start_run(Run(run_id="r"))
        store.add_trial("r", Trial(params={}, objectives={"total": 0.5}))

        from match.search import SearchResult

        merged = R.summarise(store, "r", SearchResult(renders=9, cache_hits=2))
        assert merged["trials"] == 1
        assert merged["renders"] == 9 and merged["cache_hits"] == 2

        alone = R.summarise(store, "r")
        assert "cache_hits" not in alone


def test_convergence_comes_from_the_store_so_a_report_can_be_regenerated():
    """Which is the whole reason the objectives are a column: a finished run can be
    reported on again without repeating it."""
    with Store() as store:
        store.start_run(Run(run_id="r"))
        store.add_trial("r", Trial(params={}, objectives={"total": 0.9}))
        store.add_trial("r", Trial(params={}, error="died"))
        store.add_trial("r", Trial(params={}, objectives={"total": 0.4}))

        trace = R.convergence_from(store, "r")
        assert [point["total"] for point in trace] == [0.9, 0.4], (
            "the failed trial has no objectives to plot"
        )


def test_write_report_creates_its_directory(tmp_path):
    path = R.write_report(str(tmp_path / "runs" / "one" / "report.html"),
                          run_id="r", target=printed(),
                          shortlist=[candidate(0.4)])
    assert (tmp_path / "runs" / "one" / "report.html").exists()
    assert "<!doctype html>" in open(path, encoding="utf-8").read()


def test_a_report_cannot_be_written_where_it_cannot_be_written(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")
    with pytest.raises(R.ReportError):
        R.write_report(str(blocker / "report.html"), run_id="r", target=printed(),
                       shortlist=[candidate(0.4)])


def levelled(total: float, by_level, **dimensions) -> Candidate:
    entry = candidate(total, **dimensions)
    entry.by_level = dict(by_level)
    return entry


def test_the_headline_reports_the_spread_across_input_levels():
    """No test populated `by_level`, so the whole ±6 dB half of the report was
    untested — and deleting the paragraph that carries it changed nothing."""
    best = levelled(0.394, {0.0: 0.394, -6.0: 0.51, 6.0: 1.87}, timbre=0.4)
    html = R.render_report(run_id="r", target=printed(), shortlist=[best])

    assert "0.394" in html and "1.870" in html
    assert "±6 dB of input level" in html
    assert "ordered by the worse end" in html


def test_the_shortlist_shows_the_worst_level_beside_the_score():
    """Which is what it is ordered by, so a reader who sees only the score cannot tell
    why #1 is #1."""
    steady = levelled(0.50, {0.0: 0.50, -6.0: 0.51, 6.0: 0.52}, timbre=0.5)
    fragile = levelled(0.40, {0.0: 0.40, -6.0: 2.90, 6.0: 0.45}, timbre=0.4)
    html = R.render_report(run_id="r", target=printed(), shortlist=[steady, fragile])

    table = html.split("Shortlist</h2>")[1].split("</table>")[0]
    assert "0.520" in table, "the steady candidate's worst level"
    assert "2.900" in table, "and the fragile one's"


def test_a_candidate_never_re_rendered_shows_a_dash_not_a_zero():
    html = R.render_report(run_id="r", target=printed(),
                           shortlist=[candidate(0.4, timbre=0.4)])
    table = html.split("Shortlist</h2>")[1].split("</table>")[0]
    assert "—" in table
    assert "±6 dB of input level" not in html.split("Shortlist")[0], (
        "with nothing measured the headline must not claim a spread"
    )


def test_the_screen_table_shows_the_movement_for_searched_parameters_too():
    """It was measured for all of them and reported for none of the kept ones, so the
    column a reader would use to check the freeze decision was a dash on every row
    that mattered."""
    html = R.render_report(
        run_id="r", target=printed(), shortlist=[candidate(0.4, timbre=0.4)],
        searched=["sw50rAmp/sw50rVolume", "sw50rEQ/sw50rEQLpf"],
        frozen={"parameters/outputGain": 0.004},
        movement={"sw50rAmp/sw50rVolume": 1.8531, "sw50rEQ/sw50rEQLpf": 0.4952,
                  "parameters/outputGain": 0.004},
    )
    table = html.split("Sensitivity screen")[1].split("</table>")[0]
    assert "1.8531" in table and "0.4952" in table
    assert "0.0040" in table
    # And the two reasons for freezing are told apart in the table itself.
    assert "too small to matter" in table
