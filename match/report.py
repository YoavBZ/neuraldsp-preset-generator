"""One HTML file that says what a run did, and what not to believe about it.

Self-contained on purpose: inline SVG and inline CSS, no CDN, no JavaScript, no
`<img src>`. A report that needs the network to render is a report that stops
working the week the CDN changes, and this one has to be readable a year later
next to the store it was generated from.

There is one thing here worth stating outright, because it is the reason the file
exists rather than a print statement. **A number and a caveat carry equal weight.**
The objective is a weighted sum of proxies for hearing, chosen by hand, and it is
wrong in ways the caveats name — no measured EQ basis, a corner fitted to a
Butterworth the plugin may not use, a tremolo that cannot be told from an echo.
Presenting 0.394 without them would be presenting a measurement as a verdict, so
the caveats are at the top, in the reading order, not in a footnote.

No matplotlib. Every chart here is an axis, some polylines and some rectangles,
which is about forty lines of SVG generation against a plotting dependency and a
font stack — and `[analysis]` is already four packages.
"""

from __future__ import annotations

import html
import math
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# Deliberately dull. This is read for its numbers, and a report that looks like a
# dashboard invites reading the big number and skipping the caveats.
STYLE = """
:root { color-scheme: light dark; }
body { font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui,
       sans-serif; max-width: 60rem; margin: 2rem auto; padding: 0 1.25rem; }
h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
h2 { font-size: 1.15rem; margin-top: 2.25rem; border-bottom: 1px solid #8884;
     padding-bottom: 0.25rem; }
.sub { color: #6b7280; margin-top: 0; }
table { border-collapse: collapse; width: 100%; margin: 0.75rem 0; font-size: 0.92rem; }
th, td { text-align: left; padding: 0.3rem 0.6rem; border-bottom: 1px solid #8883; }
th { font-weight: 600; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
.caveats { background: #fff8e1; border-left: 4px solid #f59e0b; padding: 0.6rem 1rem;
           border-radius: 4px; }
@media (prefers-color-scheme: dark) {
  .caveats { background: #3b2f14; }
}
.caveats li { margin: 0.45rem 0; }
.headline { font-size: 2rem; font-variant-numeric: tabular-nums; }
.muted { color: #6b7280; }
figure { margin: 1rem 0; }
figcaption { color: #6b7280; font-size: 0.88rem; margin-top: 0.3rem; }
svg { max-width: 100%; height: auto; background: #ffffff08; border-radius: 4px; }
code { font-size: 0.9em; }
.pos { fill: #2563eb; } .neg { fill: #dc2626; }
"""


class ReportError(ValueError):
    """A report that cannot be written from what it was given."""


def render_report(
    *,
    run_id: str,
    target: Any,
    shortlist: Sequence[Any],
    caveats: Sequence[str] = (),
    seed: Optional[Mapping] = None,
    seed_objectives: Optional[Mapping[str, float]] = None,
    fingerprints: Optional[Mapping[int, Any]] = None,
    convergence: Sequence[Mapping[str, float]] = (),
    summary: Optional[Mapping[str, Any]] = None,
    frozen: Optional[Mapping[str, float]] = None,
    searched: Sequence[str] = (),
    profile: str = "unpaired-v1",
    reference: str = "the reference",
) -> str:
    """The whole report as one HTML string.

    `shortlist` is `match.search.Candidate`s in the order they should be read —
    already re-ranked. `fingerprints` maps a candidate's index to its `Fingerprint`
    so the spectrum overlay can be drawn; a candidate without one still appears in
    every table, because leaving it out would misreport the shortlist's length.
    """
    best = shortlist[0] if shortlist else None
    parts: List[str] = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>Tone match — {html.escape(run_id)}</title>",
        f"<style>{STYLE}</style></head><body>",
        f"<h1>Tone match — {html.escape(run_id)}</h1>",
        f"<p class='sub'>{html.escape(reference)} · loss profile "
        f"<code>{html.escape(profile)}</code> · "
        f"{time.strftime('%Y-%m-%d %H:%M')}</p>",
    ]

    parts.append(_headline(best, seed_objectives))
    parts.append(_caveats(caveats))
    parts.append(_shortlist(shortlist, seed))
    parts.append(_objectives_table(shortlist, seed_objectives))
    parts.append(_spectrum(target, fingerprints or {}, shortlist))
    parts.append(_band_bars(target, fingerprints or {}))
    parts.append(_envelopes(target, fingerprints or {}))
    parts.append(_convergence(convergence))
    parts.append(_screen(searched, frozen or {}))
    parts.append(_accounting(summary))
    parts.append("</body></html>")
    return "\n".join(part for part in parts if part)


def write_report(path: str, **kwargs) -> str:
    """Write the report and return the path, creating the directory if needed."""
    import pathlib

    destination = pathlib.Path(path)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render_report(**kwargs), encoding="utf-8")
    except OSError as e:
        raise ReportError(f"cannot write the report to {path}: {e}") from e
    return str(destination)


# --- sections ---------------------------------------------------------------


def _headline(best, seed_objectives: Optional[Mapping[str, float]]) -> str:
    """The one number, with what it was before it, and no interpretation.

    Deliberately not a grade. There is no measured threshold that says 0.39 is
    "good" — the scales in the loss profile are tunable data, so the same match
    scores differently under a different profile and a letter grade would be
    inventing a calibration nobody has done.
    """
    if best is None:
        return ("<h2>Result</h2><p>No candidate produced a comparable render, so "
                "there is nothing to report. Every trial either failed or came "
                "back silent — see the accounting at the foot of this page.</p>")
    before = (seed_objectives or {}).get("total")
    change = ""
    if before is not None and before > 0:
        change = (f" <span class='muted'>from {before:.3f}, "
                  f"{100.0 * (1.0 - best.total / before):.0f}% closer</span>")
    worst = ""
    if best.worst_level is not None and best.by_level:
        worst = (f"<p class='muted'>Across ±6 dB of input level the same settings "
                 f"score between {min(best.by_level.values()):.3f} and "
                 f"{best.worst_level:.3f}. The shortlist below is ordered by the "
                 f"worse end of that, not by the number above.</p>")
    return (f"<h2>Result</h2><p class='headline'>{best.total:.3f}</p>"
            f"<p>Weighted distance to the reference, lower is closer.{change}</p>"
            f"{worst}")


def _caveats(caveats: Sequence[str]) -> str:
    """Above the charts, because they are what the charts do not show."""
    if not caveats:
        return ("<h2>What to distrust</h2><p>Nothing was flagged, which is unusual "
                "enough to be worth a second look at the run itself.</p>")
    items = "".join(f"<li>{html.escape(text)}</li>" for text in caveats)
    return (f"<h2>What to distrust</h2><div class='caveats'><ul>{items}</ul></div>"
            f"<p class='muted'>These are not disclaimers. Each one names a place "
            f"where a number above rests on an assumption rather than a "
            f"measurement.</p>")


def _shortlist(shortlist: Sequence[Any], seed: Optional[Mapping]) -> str:
    """Each candidate and what it changed, so the diff is the deliverable."""
    if not shortlist:
        return ""
    rows = []
    for index, candidate in enumerate(shortlist, start=1):
        moved = _diff(seed, candidate.values)
        worst = ("—" if candidate.worst_level is None
                 else f"{candidate.worst_level:.3f}")
        listing = ("<span class='muted'>nothing moved from the seed</span>"
                   if not moved else
                   "<br>".join(f"<code>{html.escape(path)}</code> "
                               f"{html.escape(_show(was))} → "
                               f"{html.escape(_show(now))}"
                               for path, was, now in moved[:12]))
        more = (f"<br><span class='muted'>and {len(moved) - 12} more</span>"
                if len(moved) > 12 else "")
        rows.append(
            f"<tr><td class='n'>{index}</td><td class='n'>{candidate.total:.3f}</td>"
            f"<td class='n'>{worst}</td><td>{listing}{more}</td></tr>"
        )
    return (
        "<h2>Shortlist</h2>"
        "<p>Ordered by the worst score across ±6 dB of input level, which is not "
        "always the same order as the score at the reference level.</p>"
        "<table><tr><th class='n'>#</th><th class='n'>score</th>"
        "<th class='n'>worst ±6 dB</th><th>changed from the starting point</th></tr>"
        + "".join(rows) + "</table>"
    )


def _objectives_table(shortlist: Sequence[Any],
                      seed_objectives: Optional[Mapping[str, float]]) -> str:
    """Every dimension for every candidate, never collapsed.

    §2's D6 and §6.2 both insist on this: the scalar is one weighting, and a
    candidate that wins on it while losing badly on `ambience` is a different
    proposition from one that wins evenly. A dimension neither side could measure
    shows as `—` rather than as zero.
    """
    if not shortlist:
        return ""
    from analysis.compare import DIMENSIONS

    present = [name for name in DIMENSIONS
               if any(name in c.objectives for c in shortlist)
               or name in (seed_objectives or {})]
    if not present:
        return ""
    header = "".join(f"<th class='n'>{html.escape(name)}</th>" for name in present)
    rows = []
    if seed_objectives:
        cells = "".join(f"<td class='n'>{_num(seed_objectives.get(n))}</td>"
                        for n in present)
        rows.append(f"<tr><td>starting point</td>{cells}</tr>")
    for index, candidate in enumerate(shortlist, start=1):
        cells = "".join(f"<td class='n'>{_num(candidate.objectives.get(n))}</td>"
                        for n in present)
        rows.append(f"<tr><td>#{index}</td>{cells}</tr>")
    return (f"<h2>Objectives, per dimension</h2>"
            f"<table><tr><th></th>{header}</tr>{''.join(rows)}</table>"
            f"<p class='muted'>A dash is a dimension neither recording supported "
            f"measuring, not a zero. `prior_deviation` and `complexity` measure "
            f"distance from the starting point rather than from the reference, so "
            f"lower is more conservative rather than more accurate.</p>")


def _spectrum(target, fingerprints: Mapping[int, Any],
              shortlist: Sequence[Any]) -> str:
    """Long-term average spectrum: the reference against each candidate."""
    reference = _bands(target)
    if not reference:
        return ""
    series = [("reference", reference, "#111")]
    palette = ("#2563eb", "#059669", "#c026d3", "#ea580c", "#0891b2")
    for index in range(len(shortlist)):
        bands = _bands(fingerprints.get(index))
        if bands:
            series.append((f"#{index + 1}", bands, palette[index % len(palette)]))
    if len(series) == 1:
        return ""
    return _figure(
        _line_chart(series, y_label="dB", x_log=True),
        "Long-term average spectrum, third-octave. Level is not removed, so a "
        "vertical offset between two curves is a loudness difference and a "
        "difference in <em>shape</em> is what the equaliser is for.",
        "Spectrum",
    )


def _band_bars(target, fingerprints: Mapping[int, Any]) -> str:
    """Signed band difference for the best candidate: what is left to fix."""
    best = fingerprints.get(0)
    if best is None:
        return ""
    from analysis.compare import band_delta

    rows = band_delta(target, best)
    if not rows:
        return ""
    values = [(float(row["centre_hz"]), float(row["delta_db"])) for row in rows]
    return _figure(
        _bar_chart(values),
        "Where the best candidate still differs from the reference, in dB per "
        "third-octave band, mean removed. Blue is where the reference has more "
        "and red is where it has less — so a blue bar is a band the preset is "
        "short of.",
        "What is left",
    )


def _envelopes(target, fingerprints: Mapping[int, Any]) -> str:
    """Attack and decay, as the numbers rather than a waveform.

    An envelope overlay of two *different performances* would be a picture of two
    different performances, which is why the unpaired regime weights dynamics down
    in the first place. What survives being compared across performances is the
    statistics, so those are what is shown.
    """
    best = fingerprints.get(0)
    if best is None:
        return ""
    fields = [
        ("crest_db", "crest factor", "dB"),
        ("attack_ms", "median attack", "ms"),
        ("decay_db_per_s", "decay rate", "dB/s"),
        ("lra_lu", "loudness range", "LU"),
        ("rms_spread_db", "level spread", "dB"),
    ]
    rows = []
    for key, label, unit in fields:
        mine = (getattr(target, "dynamics", {}) or {}).get(key)
        theirs = (getattr(best, "dynamics", {}) or {}).get(key)
        if mine is None and theirs is None:
            continue
        rows.append(f"<tr><td>{html.escape(label)}</td>"
                    f"<td class='n'>{_num(mine, 2)}</td>"
                    f"<td class='n'>{_num(theirs, 2)}</td>"
                    f"<td class='muted'>{html.escape(unit)}</td></tr>")
    if not rows:
        return ""
    return ("<h2>Dynamics</h2><table><tr><th></th><th class='n'>reference</th>"
            "<th class='n'>best candidate</th><th></th></tr>"
            + "".join(rows) + "</table>"
            "<p class='muted'>Shown as statistics rather than as an envelope "
            "overlay: against a different performance an envelope picture is a "
            "picture of the performance, which is why the unpaired profile weights "
            "these down.</p>")


def _convergence(convergence: Sequence[Mapping[str, float]]) -> str:
    """Best-so-far per dimension, so a flat trace is visible as a flat trace."""
    if len(convergence) < 2:
        return ""
    from analysis.compare import DIMENSIONS

    names = [n for n in ("total",) + tuple(DIMENSIONS)
             if any(n in point for point in convergence)]
    palette = ("#111", "#2563eb", "#059669", "#c026d3", "#ea580c", "#0891b2",
               "#7c3aed", "#b45309", "#0d9488", "#be123c")
    series = []
    for index, name in enumerate(names):
        running = float("inf")
        points = []
        for step, point in enumerate(convergence):
            value = point.get(name)
            if value is not None:
                running = min(running, float(value))
            if math.isfinite(running):
                points.append((float(step + 1), running))
        if len(points) > 1:
            series.append((name, points, palette[index % len(palette)]))
    if not series:
        return ""
    return _figure(
        _line_chart(series, y_label="distance", x_log=False),
        "Best-so-far per dimension against render count. A trace that goes flat "
        "early is a dimension the search stopped being able to improve — which is "
        "either the answer or the limit of what these controls can do, and the "
        "chart does not distinguish them.",
        "Convergence",
    )


def _screen(searched: Sequence[str], frozen: Mapping[str, float]) -> str:
    """What the sensitivity screen decided, and on what evidence."""
    if not searched and not frozen:
        return ""
    rows = [f"<tr><td><code>{html.escape(path)}</code></td>"
            f"<td>searched</td><td class='n'>—</td></tr>" for path in searched]
    for path, movement in sorted(frozen.items(), key=lambda kv: -_safe(kv[1])):
        shown = ("not measured" if not math.isfinite(_safe(movement))
                 else f"{movement:.4f}")
        rows.append(f"<tr><td><code>{html.escape(path)}</code></td>"
                    f"<td>frozen</td><td class='n'>{shown}</td></tr>")
    return ("<h2>Sensitivity screen</h2>"
            "<p>Each parameter was rendered at both ends of its range with "
            "everything else at the starting point. A parameter that could not "
            "move the objective from one extreme to the other cannot matter at any "
            "setting in between, <em>on this material</em>.</p>"
            "<table><tr><th>parameter</th><th>decision</th>"
            "<th class='n'>objective movement</th></tr>"
            + "".join(rows) + "</table>")


def _accounting(summary: Optional[Mapping[str, Any]]) -> str:
    """The render count, the failures, and the wall time — separately.

    Never merged, per §M4's exit criterion. A run that hit its budget by failing a
    third of its renders is not the same run as one that spent all of them.
    """
    if not summary:
        return ""
    order = ("trials", "failures", "errors", "silent", "failure_rate", "wall_ms",
             "renders", "cache_hits")
    rows = []
    for key in order:
        if key not in summary:
            continue
        value = summary[key]
        shown = f"{value:.3f}" if isinstance(value, float) else str(value)
        rows.append(f"<tr><td>{html.escape(key.replace('_', ' '))}</td>"
                    f"<td class='n'>{html.escape(shown)}</td></tr>")
    extra = [k for k in summary if k not in order and k != "run_id"]
    for key in sorted(extra):
        rows.append(f"<tr><td>{html.escape(str(key))}</td>"
                    f"<td class='n'>{html.escape(str(summary[key]))}</td></tr>")
    return ("<h2>Accounting</h2><table>" + "".join(rows) + "</table>"
            "<p class='muted'>Failures count errors and silent renders together, "
            "because both mean no usable measurement came back; they are also "
            "listed apart, because the causes are different.</p>")


# --- charts, in SVG ---------------------------------------------------------

WIDTH, HEIGHT = 860, 300
PAD_LEFT, PAD_RIGHT, PAD_TOP, PAD_BOTTOM = 52, 90, 16, 34


def _figure(svg: str, caption: str, title: str) -> str:
    return (f"<h2>{html.escape(title)}</h2><figure>{svg}"
            f"<figcaption>{caption}</figcaption></figure>")


def _line_chart(series: Sequence[Tuple[str, Sequence[Tuple[float, float]], str]],
                y_label: str = "", x_log: bool = False) -> str:
    """Polylines with an axis. No dependency, no font metrics, no layout engine."""
    points = [point for _, data, _ in series for point in data]
    if not points:
        return ""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    if x_log:
        x_min, x_max = max(x_min, 1e-6), max(x_max, 1e-6)
    if y_max - y_min < 1e-9:
        y_min, y_max = y_min - 1.0, y_max + 1.0
    span = y_max - y_min
    y_min, y_max = y_min - 0.06 * span, y_max + 0.06 * span

    def to_x(value: float) -> float:
        if x_log:
            low, high = math.log10(x_min), math.log10(x_max)
            fraction = 0.0 if high <= low else (math.log10(max(value, 1e-6)) - low) / (high - low)
        else:
            fraction = 0.0 if x_max <= x_min else (value - x_min) / (x_max - x_min)
        return PAD_LEFT + fraction * (WIDTH - PAD_LEFT - PAD_RIGHT)

    def to_y(value: float) -> float:
        fraction = (value - y_min) / (y_max - y_min)
        return HEIGHT - PAD_BOTTOM - fraction * (HEIGHT - PAD_TOP - PAD_BOTTOM)

    body = [_axes(to_x, to_y, x_min, x_max, y_min, y_max, x_log, y_label)]
    for index, (label, data, colour) in enumerate(series):
        path = " ".join(f"{to_x(x):.1f},{to_y(y):.1f}" for x, y in data)
        body.append(f"<polyline fill='none' stroke='{colour}' stroke-width='1.8' "
                    f"points='{path}'/>")
        legend_y = PAD_TOP + 14 + index * 16
        body.append(f"<line x1='{WIDTH - PAD_RIGHT + 8}' y1='{legend_y - 4}' "
                    f"x2='{WIDTH - PAD_RIGHT + 26}' y2='{legend_y - 4}' "
                    f"stroke='{colour}' stroke-width='2.4'/>")
        body.append(f"<text x='{WIDTH - PAD_RIGHT + 30}' y='{legend_y}' "
                    f"font-size='11' fill='currentColor'>{html.escape(label)}</text>")
    return (f"<svg viewBox='0 0 {WIDTH} {HEIGHT}' role='img' width='{WIDTH}' "
            f"height='{HEIGHT}'>{''.join(body)}</svg>")


def _bar_chart(values: Sequence[Tuple[float, float]]) -> str:
    """Signed bars from a zero line, one per band."""
    if not values:
        return ""
    magnitude = max(abs(value) for _, value in values) or 1.0
    y_min, y_max = -magnitude * 1.15, magnitude * 1.15
    width = (WIDTH - PAD_LEFT - PAD_RIGHT) / max(1, len(values))

    def to_y(value: float) -> float:
        fraction = (value - y_min) / (y_max - y_min)
        return HEIGHT - PAD_BOTTOM - fraction * (HEIGHT - PAD_TOP - PAD_BOTTOM)

    zero = to_y(0.0)
    body = [f"<line x1='{PAD_LEFT}' y1='{zero:.1f}' x2='{WIDTH - PAD_RIGHT}' "
            f"y2='{zero:.1f}' stroke='#8888' stroke-width='1'/>"]
    for index, (centre, value) in enumerate(values):
        x = PAD_LEFT + index * width
        top = min(zero, to_y(value))
        height = abs(to_y(value) - zero)
        body.append(f"<rect x='{x:.1f}' y='{top:.1f}' width='{max(width - 1.5, 1):.1f}' "
                    f"height='{height:.1f}' class='{'pos' if value > 0 else 'neg'}'>"
                    f"<title>{centre:.0f} Hz: {value:+.2f} dB</title></rect>")
        if index % max(1, len(values) // 10) == 0:
            body.append(f"<text x='{x:.1f}' y='{HEIGHT - PAD_BOTTOM + 14}' "
                        f"font-size='10' fill='currentColor'>{_hz(centre)}</text>")
    for tick in (y_min * 0.85, 0.0, y_max * 0.85):
        body.append(f"<text x='{PAD_LEFT - 8}' y='{to_y(tick) + 4:.1f}' "
                    f"font-size='10' text-anchor='end' fill='currentColor'>"
                    f"{tick:+.1f}</text>")
    return (f"<svg viewBox='0 0 {WIDTH} {HEIGHT}' role='img' width='{WIDTH}' "
            f"height='{HEIGHT}'>{''.join(body)}</svg>")


def _axes(to_x, to_y, x_min, x_max, y_min, y_max, x_log: bool,
          y_label: str) -> str:
    body = [
        f"<line x1='{PAD_LEFT}' y1='{PAD_TOP}' x2='{PAD_LEFT}' "
        f"y2='{HEIGHT - PAD_BOTTOM}' stroke='#8888'/>",
        f"<line x1='{PAD_LEFT}' y1='{HEIGHT - PAD_BOTTOM}' "
        f"x2='{WIDTH - PAD_RIGHT}' y2='{HEIGHT - PAD_BOTTOM}' stroke='#8888'/>",
    ]
    for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
        value = y_min + fraction * (y_max - y_min)
        y = to_y(value)
        body.append(f"<line x1='{PAD_LEFT}' y1='{y:.1f}' x2='{WIDTH - PAD_RIGHT}' "
                    f"y2='{y:.1f}' stroke='#8882' stroke-dasharray='2 3'/>")
        body.append(f"<text x='{PAD_LEFT - 8}' y='{y + 4:.1f}' font-size='10' "
                    f"text-anchor='end' fill='currentColor'>{value:.1f}</text>")
    ticks = ([50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0, 10000.0]
             if x_log else
             [x_min + f * (x_max - x_min) for f in (0.0, 0.25, 0.5, 0.75, 1.0)])
    for value in ticks:
        if not x_min <= value <= x_max:
            continue
        body.append(f"<text x='{to_x(value):.1f}' y='{HEIGHT - PAD_BOTTOM + 14}' "
                    f"font-size='10' text-anchor='middle' fill='currentColor'>"
                    f"{_hz(value) if x_log else f'{value:.0f}'}</text>")
    if y_label:
        body.append(f"<text x='{PAD_LEFT - 40}' y='{PAD_TOP + 10}' font-size='10' "
                    f"fill='currentColor'>{html.escape(y_label)}</text>")
    return "".join(body)


# --- small helpers ----------------------------------------------------------


def _bands(printed) -> List[Tuple[float, float]]:
    if printed is None:
        return []
    spectrum = getattr(printed, "spectrum", {}) or {}
    centres = spectrum.get("band_centres_hz") or []
    levels = spectrum.get("band_db") or []
    return [(float(c), float(d)) for c, d in zip(centres, levels) if d is not None]


def _diff(seed: Optional[Mapping], values: Mapping) -> List[Tuple[str, Any, Any]]:
    """What a candidate changed, as (path, was, now), skipping what it did not.

    A quantised knob may differ from the seed by 1e-16 through the normalised
    round trip, which is not a change anyone made — so a numeric difference under
    the display precision is not reported as one.
    """
    if not seed:
        return []
    from match.space import _get as read

    changed = []
    for key, now in values.items():
        path = key if isinstance(key, str) else "/".join(str(part) for part in key)
        module, _, name = path.rpartition("/")
        was = read(seed, (module, name))
        if was is None:
            continue
        if isinstance(now, bool) or isinstance(was, bool):
            if bool(now) != bool(was):
                changed.append((path, was, now))
            continue
        try:
            if abs(float(now) - float(was)) > 0.005:
                changed.append((path, was, now))
        except (TypeError, ValueError):
            if now != was:
                changed.append((path, was, now))
    changed.sort(key=lambda row: row[0])
    return changed


def _show(value: Any) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _num(value: Optional[float], places: int = 3) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{places}f}"
    except (TypeError, ValueError):
        return html.escape(str(value))


def _hz(value: float) -> str:
    return f"{value / 1000:g}k" if value >= 1000 else f"{value:.0f}"


def _safe(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def summarise(store, run_id: str, result=None) -> Dict[str, Any]:
    """The store's own counts, plus the search's if there is one.

    Kept here rather than in `store.py` because it merges two sources: the store
    knows how many trials it holds, and only the search knows how many of those
    were cache hits, since there is no column that records one.
    """
    summary = dict(store.summary(run_id))
    if result is not None:
        summary["renders"] = result.renders
        summary["cache_hits"] = result.cache_hits
    return summary


def convergence_from(store, run_id: str) -> List[Dict[str, float]]:
    """Every trial's objectives in order, for the convergence chart.

    Read from the store rather than accumulated in memory, so a report can be
    regenerated from a finished run without repeating it — which is the whole
    reason the objectives are a column.
    """
    trace = []
    for trial in store.trials(run_id):
        if trial.objectives:
            trace.append({k: float(v) for k, v in trial.objectives.items()})
    return trace
