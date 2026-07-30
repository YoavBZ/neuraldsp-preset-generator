"""The generated observed-value catalog: what the user's own presets actually use.

Advisory only. It answers "what does this knob tend to sit at in real presets?",
which is a useful anchor when choosing a value. It never says what is *legal* —
that is the committed manifest's job (`packs.loader`).

Optional: absent on a fresh clone, and every tool works without it.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from packs.paths import observed_path


def load(pack_id: str) -> Dict[str, Any]:
    """Read a pack's observed catalog, or an empty dict if there isn't one."""
    path = observed_path(pack_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        # Advisory data: a corrupt catalog must never break a preset write.
        return {}


def save(pack_id: str, catalog: Dict[str, Any]) -> None:
    path = observed_path(pack_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, indent=2) + "\n")


def index(pack_id: str) -> Dict[Tuple[str, str], List[str]]:
    """(module, key) -> the values seen for it across the user's presets."""
    catalog = load(pack_id)
    return {
        (module, param["key"]): param.get("observed_values", [])
        for module, params in catalog.get("modules", {}).items()
        for param in params
    }


def summary(pack_id: str) -> Optional[str]:
    """One line describing the catalog, or None when there isn't one."""
    catalog = load(pack_id)
    if not catalog:
        return None
    presets = catalog.get("source_presets", [])
    count = sum(len(p) for p in catalog.get("modules", {}).values())
    return f"{count} parameters observed across {len(presets)} preset(s)"
