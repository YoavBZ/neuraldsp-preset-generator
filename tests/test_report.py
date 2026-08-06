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


def test_the_control_that_silences_the_signal_is_not_called_too_small_to_matter():
    """The caveat block and this table are in the same document, and they said opposite
    things about the same parameter: "one end of parameters/gateThreshold silences the
    signal entirely" above, `frozen — too small to matter` four sections below. `search`
    grew a separate branch for the muting case and the report kept its two-way `if`.
    """
    html = R.render_report(
        run_id="r", target=printed(), shortlist=[candidate(0.4, timbre=0.4)],
        searched=["sw50rAmp/sw50rVolume"],
        frozen={"parameters/gateThreshold": 0.0413, "delay/delayMix": 0.0009},
        movement={"sw50rAmp/sw50rVolume": 1.2},
        silences={"parameters/gateThreshold": 0.0},
    )
    table = html.split("Sensitivity screen")[1].split("</table>")[0]
    gate = [row for row in table.split("<tr>") if "gateThreshold" in row][0]

    assert "silences the signal" in gate, gate
    assert "too small to matter" not in gate, (
        "it moved the score by 0.0413, four times the floor; its size is not the reason"
    )
    # The real movement is still shown, because a reader checking the freeze decision
    # needs the number that was measured rather than a dash.
    assert "0.0413" in gate
    # And the genuinely inert one still gets the size reason.
    inert = [row for row in table.split("<tr>") if "delayMix" in row][0]
    assert "too small to matter" in inert


def test_the_screen_names_the_floor_it_actually_used():
    """`screen` raises its floor to the backend's own band noise. Classified against the
    0.01 constant instead, a parameter cut by the *floor* was reported as one of "the
    weakest 25% that did move it — a larger budget would search them". No budget will."""
    html = R.render_report(
        run_id="r", target=printed(), shortlist=[candidate(0.4, timbre=0.4)],
        searched=[], frozen={"sw50rEQ/sw50rEQBand8": 0.0208},
        movement={}, floor=0.0767,
    )
    section = html.split("Sensitivity screen")[1]
    assert "0.0767" in section, "the threshold the decision was made against"
    row = [r for r in section.split("<tr>") if "EQBand8" in r][0]
    assert "too small to matter" in row, (
        "0.0208 is under the floor this run used, however far over the constant it is"
    )


def test_a_value_the_backend_never_heard_is_marked_in_the_shortlist():
    """The caveat said twelve calculated values "have not been heard, only calculated";
    the shortlist table listed three of them under "changed from the starting point"
    with nothing to distinguish them from the changes that were rendered and scored."""
    html = R.render_report(
        run_id="r", target=printed(),
        shortlist=[Candidate(values={("pr12EQ", "pr12EQBand1"): 3.12,
                                     ("sw50rAmp", "sw50rVolume"): 70.0},
                             objectives={"total": 0.4, "timbre": 0.4}, total=0.4)],
        seed={("pr12EQ", "pr12EQBand1"): 0.0, ("sw50rAmp", "sw50rVolume"): 50.0},
        unheard=["pr12EQ/pr12EQBand1"],
    )
    table = html.split("Shortlist")[1].split("</table>")[0]
    band = [row for row in table.split("<br>") if "pr12EQBand1" in row][0]
    volume = [row for row in table.split("<br>") if "sw50rVolume" in row][0]

    assert "calculated, not heard" in band, band
    assert "calculated, not heard" not in volume, (
        "the volume was rendered and scored; marking it would be the opposite lie"
    )


def test_a_dimension_the_winner_made_worse_is_marked_and_named():
    """A weighted sum can improve while the two dimensions a player notices first get
    worse. Measured on a real run: "25% closer", with timbre 0.755 → 0.906 and level
    0.763 → 1.830, because dynamics and ambience improved by more. Nothing marked it."""
    html = R.render_report(
        run_id="r", target=printed(),
        shortlist=[candidate(0.853, timbre=0.906, dynamics=2.118,
                             ambience=0.023, level=1.830)],
        seed_objectives={"total": 1.130, "timbre": 0.755, "dynamics": 3.440,
                         "ambience": 0.934, "level": 0.763},
    )
    table = html.split("Objectives, per dimension")[1].split("</table>")[0]

    assert table.count("worse") == 2, (
        f"timbre and level got worse and nothing else did:\n{table}"
    )
    assert "further from the reference than the starting point was" in html
    assert "timbre" in html.split("further from the reference")[1][:200]
    # The dimensions that improved are not marked.
    for cell in table.split("<td"):
        if "2.118" in cell or "0.023" in cell:
            assert "worse" not in cell, cell


def test_the_objectives_table_shows_the_weights_the_headline_used():
    """`dynamics 3.440` sat next to `timbre 0.755` with no hint that dynamics counts 0.4
    and timbre 1.0, so the weighted sum above could not be checked against the only
    breakdown offered."""
    html = R.render_report(
        run_id="r", target=printed(),
        shortlist=[candidate(0.4, timbre=0.4, dynamics=1.0)],
        profile="unpaired-v1")
    table = html.split("Objectives, per dimension")[1].split("</table>")[0]

    from analysis.compare import load_profile

    weights = load_profile("unpaired-v1")["weights"]
    assert "weight" in table
    for name in ("timbre", "dynamics"):
        assert f"{weights[name]:.3f}" in table, f"{name}'s weight is missing"


def test_the_prior_columns_are_blank_for_the_starting_point():
    """They are distances from whatever the scoring evaluator was told the recipe was,
    and for the starting point that is the template itself — trivially 0.000 — while the
    candidates' are measured from the inverted seed. Printing both invites a comparison
    between two different origins."""
    html = R.render_report(
        run_id="r", target=printed(),
        shortlist=[candidate(0.4, timbre=0.4, prior_deviation=0.077,
                             complexity=0.196)],
        seed_objectives={"total": 1.1, "timbre": 0.9, "prior_deviation": 0.0,
                         "complexity": 0.0})
    table = html.split("Objectives, per dimension")[1].split("</table>")[0]
    row = [r for r in table.split("<tr>") if "starting point" in r][0]

    assert "0.000" not in row, f"0.000 against 0.077 is not a comparison:\n{row}"
    assert row.count("—") == 2
    assert "0.900" in row, "the dimensions that *are* comparable still show"


def test_a_dimension_that_is_always_zero_is_flagged_as_flattering():
    """`spatial` reads 0.000 on every run of the synthetic renderer — both sides are
    dual-mono — and because `scalar` renormalises over the dimensions it *can*
    measure, that guaranteed zero still counts and pulls the headline down. A real
    measurement, but not a discrimination, and the difference matters to a reader."""
    html = R.render_report(
        run_id="r", target=printed(),
        shortlist=[candidate(0.4, timbre=0.4, spatial=0.0),
                   candidate(0.5, timbre=0.5, spatial=0.0)])

    assert "reads 0.000 for every candidate" in html
    # And how much it costs, as a number rather than as "a little kinder". The comment
    # in the source knew the answer exactly and the sentence the user read hedged it —
    # `spatial` is weighted 0.2 against `timbre`'s 1.0, so of the 1.2 present here it is
    # 17%, and on a full run where every dimension measures it is 8% of 2.4.
    assert "17% of the total" in html, html.split("reads 0.000")[1][:400]
    assert "a little kinder" not in html, "the arithmetic was available all along"

    # A dimension that varies is not flagged, and neither is one that means
    # "unchanged" rather than "identical".
    varied = R.render_report(
        run_id="r", target=printed(),
        shortlist=[candidate(0.4, timbre=0.4, spatial=0.1),
                   candidate(0.5, timbre=0.5, spatial=0.0)])
    assert "reads 0.000 for every candidate" not in varied

    unchanged = R.render_report(
        run_id="r", target=printed(),
        shortlist=[candidate(0.4, timbre=0.4, prior_deviation=0.0, complexity=0.0)])
    assert "reads 0.000 for every candidate" not in unchanged
