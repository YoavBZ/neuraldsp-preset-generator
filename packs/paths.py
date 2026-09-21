"""Where the code lives, and where the user's data lives.

These are two different places and conflating them loses data.

**Code** ships with the plugin. Its location is derived from this file, never
from an environment variable — the plugin's own modules are by definition inside
the install directory, so `__file__` is always right and can't go stale.

**Data** is the user's preset library and anything generated from it. When this
runs as an installed Claude Code plugin, the install directory is *ephemeral*:
it changes on every plugin update and the old one is eventually deleted. Writing
a preset library there would lose it on the next update. So data resolves, in
order:

    1. an explicit --data-dir passed to a script
    2. $NDSP_PRESET_DATA          (set it once if you want a fixed location)
    3. $CLAUDE_PLUGIN_DATA        (when the host sets it)
    4. ~/ndsp-presets             (when running from an installed plugin)
    5. the repo root              (correct when working in a git clone)

Rule 4 exists because rule 3 cannot be relied on. ``$CLAUDE_PLUGIN_DATA`` was
documented here as "set by Claude Code for installed plugins" and treated as the
answer for the installed case; it is not always set, and when it is absent the
chain used to fall through to the install directory. Nothing failed loudly — the
preset library and the learned notes were simply written somewhere an update
deletes, and read back from there as "none yet" on the next run. A silent wrong
answer about where the user's data lives is worse than any of the alternatives,
so the installed case now has a durable default of its own rather than borrowing
the code directory. ``~/ndsp-presets`` is what the README has always told people
to export, which means an existing library is picked up with no configuration.

Only the scripts that read or write under the data root take ``--data-dir``:
``show.py`` and ``build_observed.py``. ``apply_spec.py`` and ``probe.py`` take
explicit input and output paths, so the flag would be inert for them.
"""

from __future__ import annotations

import os
import pathlib
from typing import List, Optional

#: Root of the plugin/repo: the directory containing `packs/`, `scripts/`, etc.
PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Presets that ship with the plugin. Read-only at runtime.
EXAMPLES_DIR = PLUGIN_ROOT / "samples"

#: Where an installed plugin keeps data when nothing else is configured. Not a
#: module-level path: `~` is expanded per call so a test can redirect HOME, and
#: so a long-lived process picks up a changed environment rather than a value
#: frozen at import.
INSTALLED_DATA_DIR = "~/ndsp-presets"

_override: Optional[pathlib.Path] = None


def _expand(value: str) -> pathlib.Path:
    return pathlib.Path(os.path.expanduser(value)).resolve()


def set_data_root(path: Optional[str | pathlib.Path]) -> None:
    """Pin the data root for this process (from a --data-dir flag).

    None clears the override. An empty string is a mistake, not a request to
    clear: it would silently fall back to the plugin directory, which is the
    one place data must not go.
    """
    global _override
    if path is None:
        _override = None
        return
    text = str(path).strip()
    if not text:
        raise ValueError("--data-dir cannot be empty; omit it to use the default")
    _override = pathlib.Path(os.path.expanduser(text)).resolve()


def _resolve() -> tuple:
    """The data root and the name of the rule that produced it.

    One function so the two can never disagree. They were going to be two, and
    a reported origin that does not match the path actually used would be worse
    than reporting nothing: the whole point of naming the rule is that someone
    reading "learned notes: none yet" can tell a fresh install from a
    misresolved root.
    """
    if _override is not None:
        return _override, "--data-dir"
    for var in ("NDSP_PRESET_DATA", "CLAUDE_PLUGIN_DATA"):
        value = os.environ.get(var)
        if value:
            return _expand(value), f"${var}"
    if looks_installed():
        return _expand(INSTALLED_DATA_DIR), "installed-plugin default"
    return PLUGIN_ROOT, "repo root"


def data_root() -> pathlib.Path:
    """Where the user's presets and generated catalogs live."""
    return _resolve()[0]


def data_root_origin() -> str:
    """Which rule chose the data root, for a script to print beside the path.

    `show.py` reporting `learned_notes.exists: false` is ambiguous on its own —
    it means either "no run has recorded anything yet" or "the root resolved
    somewhere that is not where your notes are". Naming the rule separates them
    without the reader having to know the resolution order.
    """
    return _resolve()[1]


def is_ephemeral_data_root() -> bool:
    """True when data would be written into the plugin's own directory.

    Harmless in a git clone, which is the ordinary way to reach it. An installed
    plugin no longer falls through to here on its own — it has its own default —
    so the remaining way to hit this while installed is to point ``--data-dir``
    at the install directory on purpose, which callers still warn about.
    """
    return data_root() == PLUGIN_ROOT


def looks_installed() -> bool:
    """True when we appear to be running from an installed plugin copy.

    Claude Code installs plugins under a cache directory and replaces that
    directory on update, so writing data there really does lose it. In a git
    clone the same "data root == plugin root" situation is fine, which is why
    the warning distinguishes the two.
    """
    return ".claude/plugins" in PLUGIN_ROOT.as_posix()


def data_root_warning() -> Optional[str]:
    """A warning to print before writing data, or None when the location is safe."""
    if not is_ephemeral_data_root():
        return None
    if looks_installed():
        return (
            f"Writing into the installed plugin directory ({PLUGIN_ROOT}).\n"
            f"  Claude Code replaces that directory when the plugin updates, so "
            f"anything written there will be lost.\n"
            f"  Set NDSP_PRESET_DATA to a directory you control, omit "
            f"--data-dir to use {INSTALLED_DATA_DIR}, or pass a different "
            f"--data-dir, to keep your preset library and catalogs."
        )
    return None


def templates_dir(pack_id: str) -> pathlib.Path:
    """The user's own presets for one plugin — their template library."""
    return data_root() / "packs" / pack_id / "templates"


def learned_tones_path(pack_id: str) -> pathlib.Path:
    """Where notes learned while generating are appended.

    Deliberately under the data root, not beside the pack's committed tone.md:
    the plugin directory is replaced on update, and losing accumulated taste
    notes is exactly the failure the data root exists to prevent.
    """
    return data_root() / "packs" / pack_id / "learned-tones.md"


def response_atlases(pack_id: str) -> List[pathlib.Path]:
    """Response atlases committed for one pack, newest-largest last.

    These ship with the code rather than living under the data root: they are
    measurements of the *plugin*, identical for every user, and building one
    costs hours of renders. `learned-tones.md` is the opposite — one person's
    taste — which is why the two live in different places.

    Discovery matters more than it looks. An atlas nothing points at is research
    that never reaches the product: `query_response_atlas.py` turns one into
    starting specs without opening the plugin, and until `show.py` reported
    these, an agent following the skills had no way to learn one existed.
    """
    directory = PLUGIN_ROOT / "packs" / pack_id
    if not directory.is_dir():
        return []
    return sorted(directory.glob("response_atlas_*.json"))


def observed_path(pack_id: str) -> pathlib.Path:
    """Generated observed-value catalog for one plugin. Never committed."""
    return data_root() / "packs" / pack_id / "observed.json"


def bundled_presets() -> List[pathlib.Path]:
    """Presets shipped with the plugin, plus anything dropped alongside them."""
    if not EXAMPLES_DIR.is_dir():
        return []
    return sorted(EXAMPLES_DIR.glob("*.xml"))


def user_presets(pack_id: str) -> List[pathlib.Path]:
    """The user's presets for one pack."""
    directory = templates_dir(pack_id)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.xml"))


def all_presets(pack_ids: Optional[List[str]] = None) -> List[pathlib.Path]:
    """Every preset this installation can see, de-duplicated, order-stable."""
    found: List[pathlib.Path] = list(bundled_presets())
    for pack_id in pack_ids or []:
        found.extend(user_presets(pack_id))

    seen = set()
    unique = []
    for path in found:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def describe_roots() -> str:
    """One-line summary for a script's output, so the user knows where it looked."""
    marker = " (same as the plugin directory)" if is_ephemeral_data_root() else ""
    return (f"code: {PLUGIN_ROOT}\n"
            f"data: {data_root()}{marker} [{data_root_origin()}]")
