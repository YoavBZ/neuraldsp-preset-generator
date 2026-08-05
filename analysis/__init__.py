"""Measure what a recording sounds like, in a form two recordings can be
compared in.

Everything above this package — `show.py`, `apply_spec.py`, `format/`, `packs/`
— works with the standard library alone, and that is deliberate: the preset
tools have to run on a bare clone. Measuring audio does not fit in the standard
library, so it lives here, behind the `analysis` extra, and nothing outside this
package imports it at module scope.

    pip install -e '.[analysis]'

The unit of exchange is `Fingerprint` (see `fingerprint.py`): a description of a
sound that is playing-invariant where it can be, so the same schema describes a
separated stem of a 1976 master and a two-second render of white noise. Every
field is optional and most carry a confidence, because a feature that cannot be
measured from the material at hand must say so rather than return a number.
"""

from __future__ import annotations

FINGERPRINT_VERSION = 1

# The canonical analysis format. 48 kHz matches what the render harnesses
# produce (scripts/au_render.swift), so a render is never resampled before it is
# measured. Channel count is preserved at ingest and folded per feature, because
# width and inter-channel correlation are features in their own right — see
# `io.load` and `Audio.mono`, which are where that actually happens. A
# `CHANNELS_PRESERVED = True` constant used to sit here asserting it; nothing
# read it, so it asserted nothing.
SAMPLE_RATE = 48000

_INSTALL_HINT = (
    "the analysis extra is not installed.\n"
    "  pip install -e '.[analysis]'"
)


def require(feature: str = "audio analysis"):
    """Import the third-party stack, or explain how to get it.

    Every entry point calls this before touching numpy, so a missing extra
    produces one line a person can act on instead of an ImportError traceback
    from six frames down.
    """
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
        import soundfile  # noqa: F401
    except ImportError as e:
        raise AnalysisUnavailable(f"{feature} needs {_INSTALL_HINT}\n  ({e})") from e


class AnalysisUnavailable(RuntimeError):
    """Raised when the extra is absent. Callers print it and exit; they do not
    catch it to fall back on a guess."""
