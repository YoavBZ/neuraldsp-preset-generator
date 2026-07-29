"""Cab mic catalog: resolve internal-mic names <-> selector indices.

The `*MicType` / `*RoomMicType` fields in the binary store an integer index
into the plugin's INTERNAL MICS dropdown. This lets specs and output use names
like "Ribbon 121" instead of a bare index.

The catalog itself lives in the pack manifest (`packs/<id>/manifest.json`,
under `enums.internalMic`) so there is one source of truth for every selector
in the plugin, not a separate file for this one.
"""

from __future__ import annotations

from typing import List, Optional

from packs.loader import load_pack

MIC_ENUM = "internalMic"


def _mic_members(pack_id: str = "morgan") -> dict:
    spec = load_pack(pack_id).get("cabParameters", "leftMicType")
    if spec is None or not spec.members:
        raise KeyError(f"pack {pack_id!r} declares no {MIC_ENUM} catalog")
    return spec.members


def load_mics(pack_id: str = "morgan") -> List[str]:
    members = _mic_members(pack_id)
    return [members[str(i)] for i in range(len(members))]


def _norm(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


def mic_name_to_index(name: str, pack_id: str = "morgan") -> int:
    mics = load_mics(pack_id)
    target = _norm(name)
    for i, m in enumerate(mics):
        if _norm(m) == target:
            return i
    raise KeyError(f"unknown mic {name!r}; known mics: {', '.join(mics)}")


def mic_index_to_name(index: int, pack_id: str = "morgan") -> Optional[str]:
    mics = load_mics(pack_id)
    if 0 <= index < len(mics):
        return mics[index]
    return None


def is_mic_key(key: str) -> bool:
    return key.endswith("MicType")
