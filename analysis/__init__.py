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
# `io.load` and `Audio.mono`, which are where that actually happens.
SAMPLE_RATE = 48000

#: What the extra actually is, spelled out for the case where `.[analysis]` means
#: nothing because there is no editable checkout to resolve `.` against.
_ANALYSIS_PACKAGES = ("numpy>=1.24", "scipy>=1.10", "soundfile>=0.12",
                      "pyloudnorm>=0.1")


def _install_hint() -> str:
    """How to get the extra, phrased for how this copy is actually running.

    `pip install -e '.[analysis]'` is the right answer in a clone and a dead end
    from an installed plugin: `.` is a cache directory that the next plugin
    update replaces, and the user may have no checkout at all. The installed
    branch names the packages directly and names the interpreter that needs
    them, because "which Python?" is otherwise a guess — this repo ships
    stdlib-only tools that run on any 3.10+, so the interpreter that runs
    `show.py` fine is not necessarily the one carrying numpy.
    """
    import pathlib
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    if ".claude/plugins" in root.as_posix():
        packages = " ".join(f"'{spec}'" for spec in _ANALYSIS_PACKAGES)
        return (
            "the analysis extra, which is not installed.\n"
            f"  {sys.executable} -m pip install {packages}\n"
            "  (this copy is an installed plugin, so there is no editable "
            "checkout to install from;\n"
            "   install into the interpreter above, not into the plugin "
            "directory, which updates replace)"
        )
    return (
        "the analysis extra, which is not installed.\n"
        "  pip install -e '.[analysis]'"
    )


def require(feature: str = "audio analysis"):
    """Import the third-party stack, or explain how to get it.

    Every entry point calls this before touching numpy, so a missing extra
    produces one line a person can act on instead of an ImportError traceback
    from six frames down.

    `pyloudnorm` is checked here with the rest, and that matters more than it
    looks. It used to be caught at its two call sites and turned into `None`,
    which in this schema means "the recording could not support the measurement".
    A missing library is not a property of the recording: the effect was that
    `lufs_i` and `lra_lu` went absent with no caveat, and `normalise()` quietly
    stopped normalising, so every "spectral features are loudness-normalised"
    guarantee in the package silently lapsed.
    """
    try:
        import numpy  # noqa: F401
        import pyloudnorm  # noqa: F401
        import scipy  # noqa: F401
        import soundfile  # noqa: F401
    except ImportError as e:
        raise AnalysisUnavailable(f"{feature} needs {_install_hint()}\n  ({e})") from e


class AnalysisUnavailable(RuntimeError):
    """Raised when the extra is absent. Callers print it and exit; they do not
    catch it to fall back on a guess."""
