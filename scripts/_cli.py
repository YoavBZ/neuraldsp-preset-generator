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

# What to tell the user if they stop the run with Ctrl-C. Empty for a script where
# stopping costs nothing; set by a script that has written something worth knowing
# about, which is the case where exiting in total silence is wrong.
_INTERRUPT_NOTE: Optional[str] = None


def on_interrupt(note: str) -> None:
    """Register the sentence to print if this run is interrupted.

    A long search interrupted at 90% used to print nothing at all and leave a 176 KB
    store behind with every render in it. Not a traceback, so it cleared the bar the
    other error paths are held to — and it still left the user believing an hour was
    gone when the work was on disk and the next run would serve it from the cache.
    """
    global _INTERRUPT_NOTE
    _INTERRUPT_NOTE = note


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

    Nothing here imports `analysis`. It used to, for `AnalysisUnavailable`, and that put
    the analysis extra on the path of every script that calls `guarded` — including
    `show.py`, `apply_spec.py` and `bootstrap_pack.py`, which are the three that must run
    on a bare clone with nothing but the standard library. On a checkout without the
    extra installed, `bootstrap_pack.py` died with `ModuleNotFoundError: No module named
    'analysis'` from inside the handler written to stop tracebacks reaching people. CI
    did not see it because CI installs the package, which makes `analysis` importable
    from anywhere; matching by name is what the sibling `_LIBRARY_ERRORS` clause already
    does, and for the same reason.
    """
    import json

    try:
        main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
    except KeyboardInterrupt:
        if _INTERRUPT_NOTE:
            print(f"\nstopped. {_INTERRUPT_NOTE}", file=sys.stderr)
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


# Exception types whose message is written for the user rather than for a bug report,
# and which are not `ValueError` subclasses so the clause above does not reach them.
#
# `LibsndfileError` and friends mean "your file is not what you said it was": `soundfile`
# raises one on a file that is not audio, so `--reference pyproject.toml` printed fifteen
# frames ending in "Format not recognised" — the answer, buried.
#
# `AnalysisUnavailable` is the missing-extra install hint. It is a `RuntimeError` on
# purpose, so no caller can confuse "the library is not here" with "your value is wrong"
# and quietly fall back on a guess.
#
# Matched by name rather than imported, because importing either one here would put an
# optional dependency on the bare-clone path — which is the one thing `_cli` must not do,
# and which importing `analysis` for this list did for months.
_LIBRARY_ERRORS = frozenset({
    "LibsndfileError", "SoundFileError", "SoundFileRuntimeError",
    "AnalysisUnavailable",
})


def probe_di(path, seconds: float = 6.0):
    """The DI every candidate is rendered through, or a synthetic stand-in.

    Returns the samples and a caveat, which is `None` when a real DI was given. The
    stand-in is honest about being one: a search's answer is only as representative as
    the DI it was scored on, and noise bursts with gaps show attack and decay clearly
    and show a palm-muted chug not at all, so a preset matched on them may not hold up
    on the part someone actually plays.

    Shared because `match_preset.py` and `benchmark_match.py` had the same function with
    the same `gap=0.9, seed=13` constants. The production path owns the signal; tests
    verify that its samples remain identical to the original fixture.
    """
    if path is not None:
        from analysis import io

        return io.load(str(path)).mono(), None
    from analysis.probes import decaying_noise_bursts

    return (decaying_noise_bursts(seconds=seconds, gap=0.9, seed=13),
            "no --probe-di was given, so candidates were rendered through a "
            "synthetic decaying noise-burst sequence. It shows attack and decay "
            "clearly and shows "
            "sustained or palm-muted playing not at all — match against your own "
            "DI before trusting this on a real part.")


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
    import math

    if not math.isfinite(value):
        raise argparse.ArgumentTypeError(f"must be finite, got {text!r}")
    if not value > 0.0:
        raise argparse.ArgumentTypeError(f"must be greater than zero, got {value:g}")
    return value


def nonnegative_float(text: str) -> float:
    """An argparse type for durations where zero explicitly means "all"."""
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number") from None
    import math

    if not math.isfinite(value):
        raise argparse.ArgumentTypeError(f"must be finite, got {text!r}")
    if not value >= 0.0:
        raise argparse.ArgumentTypeError(f"must be zero or greater, got {value:g}")
    return value


def resolved_excerpt(requested: Optional[float], regime: str,
                     default: float = 20.0) -> Optional[float]:
    """One excerpt policy shared by preflight, comparison, and matching.

    A paired DI is sample-for-sample evidence, so its safe default is the complete
    performance. Other regimes default to a short active window. Explicit zero
    always means the full source.
    """
    if requested is None:
        return None if regime == "paired_di" else float(default)
    return None if float(requested) == 0.0 else float(requested)


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


def renderer_paths(renderer):
    """The parameter paths a renderer accepts, or ``None`` for unrestricted.

    Enumeration needs this answer before the search starts.  Otherwise a selector
    the backend later drops becomes several identical topologies that silently
    divide the budget.
    """
    from match.search import supported_keys

    return supported_keys(renderer)


def enumerable(space, supported=None):
    """Every supported discrete dimension, and how many positions it has.

    A switch has two. A selector has one per declared member — and a selector
    whose members are unknown is not here at all, because `space.build` already
    excluded it: a stored integer the plugin never displays cannot be chosen on
    purpose.
    """
    found = []
    for dimension in space.dimensions:
        if supported is not None and dimension.path not in supported:
            continue
        if dimension.switch:
            found.append((dimension.path, 2, "switch"))
        elif dimension.kind == "enum" and dimension.members:
            found.append((dimension.path, len(dimension.members), "selector"))
    return sorted(found)


def print_enumerable(space, pack_id: str, amp, supported=None) -> None:
    """What `--enumerate` accepts here, and what asking for it costs.

    The cost sentence uses this pack's own widest selector rather than a made-up
    example, because the number is the whole point: a control with eleven
    positions is eleven inner searches sharing one budget.
    """
    found = enumerable(space, supported=supported)
    if not found:
        print(f"{pack_id} declares no switches or selectors that can be enumerated"
              + (f" for {amp}" if amp else "") + ".")
        return
    where = f"{pack_id}/{amp}" if amp else pack_id
    print(f"{len(found)} enumerable controls in {where} — pass any of these to "
          f"--enumerate:\n")
    for path, positions, kind in found:
        print(f"  {path:<40} {positions:>3} positions  ({kind})")
    widest, positions, _ = max(found, key=lambda row: row[1])
    print(f"\nEach one multiplies the number of inner searches, and they share one "
          f"budget.\nTwo two-state switches is four searches; adding {widest} "
          f"({positions} positions)\nmakes it {4 * positions}.")


def enumerated(space, paths, budget: Optional[int], shortlist: int,
               supported=None, seed=None):
    """Split the requested paths into switches and selectors, and refuse the silly.

    Routed by the dimension's own kind rather than by asking the caller to know
    which flag a control belongs under: `search.topologies` takes the two apart
    and raises if one is passed as the other, and that is a distinction about this
    codebase rather than about the plugin.

    The budget check is here rather than inside the search because this is where
    it can still be acted on. `search()` reports afterwards that each variant got
    a thin share; a run that cannot afford one CMA-ES round *per variant* should
    be stopped before it spends an hour proving it.
    """
    if not paths:
        return None, None

    all_discrete = {path for path, _, _ in enumerable(space)}
    by_path = {
        path: (positions, kind)
        for path, positions, kind in enumerable(space, supported=supported)
    }
    switches, selectors, variants = [], [], 1
    for path in paths:
        if path in switches or path in selectors:
            die(f"{path!r} was passed to --enumerate more than once.\n"
                f"  Repeating one control duplicates every topology without "
                f"adding a choice, so remove the duplicate flag.")
        found = by_path.get(path)
        if found is None and path in all_discrete:
            die(f"{path!r} is a switch or selector, but this renderer cannot drive "
                f"it.\n  Choose a real-plugin renderer for that control, or run "
                f"the same command with --list-enumerable to see the "
                f"{len(by_path)} this backend supports.")
        if found is None:
            die(f"{path!r} is not a switch or selector this search can enumerate.\n"
                f"  Run the same command with --list-enumerable to see the "
                f"{len(by_path)} that are.")
        positions, kind = found
        (switches if kind == "switch" else selectors).append(path)
        variants *= positions

    # A first call can validate and route the paths before the reference is read
    # or a plugin is rendered.  The match CLI calls again with the post-inversion
    # seed, because that seed determines which continuous controls the screen will
    # actually charge for.
    if budget is None:
        return switches or None, selectors or None

    # One render per variant for its own starting point, 2N+1 for the screen, and
    # 2 per shortlisted candidate for the re-rank. Only what is left is searchable,
    # and it is split across the variants. `generation_size` is the granularity of
    # the whole search — below one round the optimiser cannot take a step — and it
    # is exposed by `match.search` for exactly this arithmetic rather than being
    # re-derived here.
    from match.search import generation_size

    active = space.active(seed) if seed is not None else space.dimensions
    screened = [
        dimension for dimension in active
        if not dimension.switch and dimension.kind != "enum"
        and (supported is None or dimension.path in supported)
    ]
    screen_cost = 2 * len(screened) + 1
    # An upper bound on what the screen leaves searchable: the real count is only
    # known after screening, and using it here would need the renders this check
    # exists to avoid spending.
    round_cost = generation_size(len(screened)) if screened else 1
    reserved = screen_cost + variants + 2 * shortlist
    per_variant = (budget - reserved) / max(variants, 1)
    if per_variant < round_cost:
        die(f"{variants} topologies do not fit in a {budget}-render budget.\n"
            f"  {reserved} renders are spent before any searching: {screen_cost} on "
            f"the screen, {variants} on one starting point per topology, "
            f"{2 * shortlist} on the ±6 dB re-rank. That leaves "
            f"{max(budget - reserved, 0)} to split {variants} ways — about "
            f"{max(per_variant, 0):.0f} each, against the {round_cost} one round "
            f"of the optimiser costs.\n"
            f"  Raise --budget to about {int(reserved + variants * round_cost)}, "
            f"or enumerate fewer controls. A topology with no search behind it is "
            f"its starting point scored once.")
    return switches or None, selectors or None
