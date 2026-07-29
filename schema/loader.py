"""Load the generated observed-value catalog and index it by (module, key).

Advisory data only — what values the user's own presets happen to use. The
authoritative contract (kinds, units, legal ranges, selector members) is the
committed pack manifest; see `packs.loader`.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = pathlib.Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "packs" / "morgan" / "observed.json"


def load_schema(path: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    path = path or SCHEMA_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"No observed-value catalog at {path}. It is generated from your own "
            f"presets and is optional — build it with `python -m schema.build_schema` "
            f"after adding presets to samples/."
        )
    return json.loads(path.read_text())


def index_by_key(schema: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for module, params in schema["modules"].items():
        for p in params:
            out[(module, p["key"])] = p
    return out
