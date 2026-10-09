"""The judge through a rebuilt DI, with the reference-proxy fallback.

A rebuilt DI aligned with its recording is judged at lag −52. When the judge refuses
the window because the rebuilt DI looks too quiet (too many pauses, or too few playing
frames), the recording itself stands in as the activity mask. On set-3 development it
rescued the one refused part and changed none of 11 control picks
(`docs/set3-mask-diagnostic-results.md`, adopted in `docs/codex-continuation-review.md`).
Untested on mixes, where the recording's activity includes other instruments.
"""

from __future__ import annotations

LATENCY = 52
_ACTIVITY = ("pauses", "plays in too few frames")


def rebuilt_distance(recording, render, di, *, start_s, end_s, bands="recording"):
    """(AlignedDistance, used_proxy) for `render` (a preset through the rebuilt `di`)."""
    from analysis.aligned import aligned_distance

    kw = dict(lag=-LATENCY, render_latency=LATENCY, start_s=start_s, end_s=end_s, bands=bands)
    d = aligned_distance(recording, render, di, **kw)
    if d.distance is None and any(s in (d.reason or "") for s in _ACTIVITY):
        return aligned_distance(recording, render, recording, **kw), True
    return d, False
