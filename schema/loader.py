"""Load morgan_schema.json and index parameters by (module_path, key)."""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = pathlib.Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "morgan_schema.json"


def load_schema(path: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    return json.loads((path or SCHEMA_PATH).read_text())


def index_by_key(schema: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for module, params in schema["modules"].items():
        for p in params:
            out[(module, p["key"])] = p
    return out
