"""Shared plumbing for the four scripts.

Each of them had its own copy of "print an error and exit", its own broken-pipe
guard, and its own way of turning a preset's header into a pack — which meant the
same failure ("this preset is from a plugin we have no pack for") reached the
user in three different wordings depending on which script they happened to run.
"""

from __future__ import annotations

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
    than as a traceback. BrokenPipeError just means the output was piped into
    something like `head`.
    """
    from packs.loader import PackError

    try:
        main()
    except PackError as e:
        die(str(e))
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)


def add_data_dir_arg(parser) -> None:
    """For scripts that read or write anything under the data root."""
    parser.add_argument(
        "--data-dir",
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
