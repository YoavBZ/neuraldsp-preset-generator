"""Shared plumbing for the four scripts.

Each of them had its own copy of "print an error and exit", its own broken-pipe
guard, and its own way of turning a preset's header into a pack — which meant the
same failure ("this preset is from a plugin we have no pack for") reached the
user in three different wordings depending on which script they happened to run.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
from typing import Optional

EXIT_ERROR = 2


def die(message: str) -> None:
    """Report a user-facing problem and stop. Never raises past the caller."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(EXIT_ERROR)


def guarded(main) -> None:
    """Run a script's main(), turning expected failures into clean exits.

    PackError carries a message written for the user, so it prints as-is rather
    than as a traceback. So do its siblings — `SpaceError`, `InversionError`,
    `ChainError`, `ProfileError`, `TimingError` — which is why this catches
    `ValueError`: they all derive from it, and enumerating five names here means a
    sixth module's error escapes as a traceback the day it is added.
    `AnalysisUnavailable` is caught by name for the same reason — it is the
    missing-extra install hint, which is a message, not a stack — but it is a
    `RuntimeError`, because a caller must not confuse "the library is not here" with
    "your value is wrong" and quietly fall back on a guess.

    BrokenPipeError just means the output was piped into something like `head`.

    OSError and a malformed JSON file are here for the same reason: a mistyped
    path is the most ordinary mistake there is, and a nine-frame
    `FileNotFoundError` traceback is not a message. These are the mistakes a
    person makes, not the ones the code makes.
    """
    import json

    from analysis import AnalysisUnavailable

    try:
        main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
    except json.JSONDecodeError as e:
        die(f"that file is not valid JSON: {e}")
    except IsADirectoryError as e:
        die(f"{e.filename} is a directory, not a file")
    except FileNotFoundError as e:
        die(f"no such file or directory: {e.filename}")
    except PermissionError as e:
        die(f"permission denied: {e.filename}")
    except OSError as e:
        # Anything else the filesystem refused, named rather than traced.
        where = f" ({e.filename})" if getattr(e, "filename", None) else ""
        die(f"{e.strerror or e}{where}")
    except ValueError as e:
        # Last, so `json.JSONDecodeError` — itself a ValueError — still gets its
        # own sentence above.
        die(str(e))
    except AnalysisUnavailable as e:
        die(str(e))
    except Exception as e:
        # A `RuntimeError` from a third-party reader, which is the one remaining way
        # an ordinary mistake reaches a person as a traceback. `soundfile` raises
        # `LibsndfileError(RuntimeError)` on a file that is not audio, so
        # `--reference pyproject.toml` printed fifteen frames ending in "Format not
        # recognised" — the answer, buried. Named types only: a `KeyError` or an
        # `AttributeError` is this code being wrong, and that should still be a
        # traceback, because it is a bug report rather than a user error.
        if type(e).__name__ in _LIBRARY_ERRORS:
            die(f"{e}")
        raise


# Third-party exception types that mean "your file is not what you said it was".
# Matched by name rather than imported, because importing `soundfile` here would put
# the analysis extra on the bare-clone path, which is the one thing `_cli` must not do.
_LIBRARY_ERRORS = frozenset({"LibsndfileError", "SoundFileError", "SoundFileRuntimeError"})


def _data_dir(text: str) -> str:
    """Reject an empty --data-dir at the argparse layer.

    `--data-dir ""` is easy to produce from an unset shell variable. Without
    this it would fall through to "no override" and write into the plugin
    directory — the one place the data root exists to keep data out of.
    """
    if not text.strip():
        raise argparse.ArgumentTypeError(
            "cannot be empty; omit --data-dir to use the default"
        )
    return text


def positive_float(text: str) -> float:
    """An argparse type for a duration or amplitude that has to be above zero.

    Caught here rather than downstream, where `--seconds 0` became
    "zero-size array to reduction operation maximum" and `--seconds -5` became
    "negative dimensions are not allowed" — numpy's words for the user's mistake.
    """
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number") from None
    if not value > 0.0:
        raise argparse.ArgumentTypeError(f"must be greater than zero, got {value:g}")
    return value


def positive_int(text: str) -> int:
    """Same, for counts. `--bench -3` produced a ZeroDivisionError."""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a whole number") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {value}")
    return value


def add_data_dir_arg(parser) -> None:
    """For scripts that read or write anything under the data root."""
    parser.add_argument(
        "--data-dir",
        type=_data_dir,
        help="where your presets and generated catalogs live (default: "
        "$NDSP_PRESET_DATA, else $CLAUDE_PLUGIN_DATA, else the repo root)",
    )


def add_pack_arg(parser) -> None:
    parser.add_argument(
        "--pack", help="plugin pack id (default: detect from the preset)"
    )


def resolve_pack(pack_id: Optional[str], file_header: str, source: pathlib.Path):
    """Load the pack for a preset: the one named, or the one it identifies as."""
    from packs.loader import detect_pack, load_pack

    if pack_id:
        return load_pack(pack_id)

    pack = detect_pack(file_header)
    if pack is None:
        from packs.loader import list_packs

        die(
            f"{source} identifies itself as {file_header!r}, which has no pack.\n"
            f"  Known packs: {', '.join(list_packs()) or 'none'}.\n"
            f"  Pass --pack <id> to force one, or draft a new pack with\n"
            f"  python scripts/bootstrap_pack.py --preset {source}"
        )
    return pack
