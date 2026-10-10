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
# Rebuilt DIs are low-passed here before rendering (docs/rebuilt-di-lowpass-results.md:
# a near miss, −0.049 against a −0.05 bar, 23 picks better and 5 worse; adopted by the
# user's decision on 2026-10-10 because it is free, consistent in direction, and removes
# content the network cannot rebuild).
LOWPASS_HZ = 3000


def lowpass(di, hz=LOWPASS_HZ, sample_rate=48000):
    """`di` through a zero-phase fourth-order Butterworth magnitude at `hz`, at −22.9 LUFS."""
    import numpy as np

    from learn.direc_check import to_lufs

    f = np.fft.rfftfreq(len(di), 1 / sample_rate)
    return to_lufs(np.fft.irfft(np.fft.rfft(di) / np.sqrt(1 + (f / hz) ** 8), len(di)))


def rebuilt_distance(recording, render, di, *, start_s, end_s, bands="recording"):
    """(AlignedDistance, used_proxy) for `render` (a preset through the rebuilt `di`)."""
    from analysis.aligned import aligned_distance

    kw = dict(lag=-LATENCY, render_latency=LATENCY, start_s=start_s, end_s=end_s, bands=bands)
    d = aligned_distance(recording, render, di, **kw)
    if d.distance is None and any(s in (d.reason or "") for s in _ACTIVITY):
        return aligned_distance(recording, render, recording, **kw), True
    return d, False
