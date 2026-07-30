"""Where the code lives, and where the user's data lives.

These are two different places and conflating them loses data.

**Code** ships with the plugin. Its location is derived from this file, never
from an environment variable — the plugin's own modules are by definition inside
the install directory, so `__file__` is always right and can't go stale.

**Data** is the user's preset library and anything generated from it. When this
runs as an installed Claude Code plugin, the install directory is *ephemeral*:
it changes on every plugin update and the old one is eventually deleted. Writing
a preset library there would lose it on the next update. Claude Code provides
``${CLAUDE_PLUGIN_DATA}`` for exactly this, so data resolves, in order:

    1. an explicit --data-dir passed to a script
    2. $NDSP_PRESET_DATA          (set it once if you want a fixed location)
    3. $CLAUDE_PLUGIN_DATA        (set by Claude Code for installed plugins)
    4. the repo root              (correct when working in a git clone)

Skill instructions pass ``--data-dir "${CLAUDE_PLUGIN_DATA}"``, because the
placeholder is substituted in skill text before the model runs the command —
the environment variable itself is not guaranteed to reach a Bash subprocess.
"""

from __future__ import annotations

import os
import pathlib
from typing import List, Optional

#: Root of the plugin/repo: the directory containing `packs/`, `scripts/`, etc.
PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Presets that ship with the plugin. Read-only at runtime.
EXAMPLES_DIR = PLUGIN_ROOT / "samples"

_override: Optional[pathlib.Path] = None


def set_data_root(path: Optional[str | pathlib.Path]) -> None:
    """Pin the data root for this process (from a --data-dir flag)."""
    global _override
    _override = pathlib.Path(os.path.expanduser(str(path))).resolve() if path else None


def data_root() -> pathlib.Path:
    """Where the user's presets and generated catalogs live."""
    if _override is not None:
        return _override
    for var in ("NDSP_PRESET_DATA", "CLAUDE_PLUGIN_DATA"):
        value = os.environ.get(var)
        if value:
            return pathlib.Path(os.path.expanduser(value)).resolve()
    return PLUGIN_ROOT


def is_ephemeral_data_root() -> bool:
    """True when data would be written into the plugin's own directory.

    Harmless in a git clone. When actually installed as a plugin it means the
    next update will take the data with it, so callers warn.
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
            f"  Set NDSP_PRESET_DATA to a directory you control, or pass "
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
    return f"code: {PLUGIN_ROOT}\ndata: {data_root()}{marker}"
