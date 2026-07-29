"""Cab mic catalog: resolve internal-mic names <-> selector indices.

The `*MicType` / `*RoomMicType` fields in the binary store an integer index
into the plugin's INTERNAL MICS dropdown. This lets specs/UI use names like
"Ribbon 121" instead of the raw index.
"""

from __future__ import annotations

import json
import pathlib
from typing import List, Optional

CATALOG_PATH = pathlib.Path(__file__).parent / "mic_catalog.json"


def load_mics() -> List[str]:
    return json.loads(CATALOG_PATH.read_text())["mics"]


def _norm(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


def mic_name_to_index(name: str) -> int:
    mics = load_mics()
    target = _norm(name)
    for i, m in enumerate(mics):
        if _norm(m) == target:
            return i
    raise KeyError(
        f"unknown mic {name!r}; known mics: {', '.join(mics)}"
    )


def mic_index_to_name(index: int) -> Optional[str]:
    mics = load_mics()
    if 0 <= index < len(mics):
        return mics[index]
    return None


def is_mic_key(key: str) -> bool:
    return key.endswith("MicType")
