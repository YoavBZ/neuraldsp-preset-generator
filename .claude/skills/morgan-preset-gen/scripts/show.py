"""Print every parameter in a preset as JSON, with both the stored value and
a human-friendly value (percent / native unit), for the agent to read before
generating or editing."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from format.parser import parse_file
from format.structured import build
from format.translate import describe, from_binary
from schema.cab import is_mic_key, mic_index_to_name
from schema.loader import index_by_key, load_schema


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("preset", help="path to .xml preset")
    args = ap.parse_args()

    schema_idx = index_by_key(load_schema())
    tokens = parse_file(args.preset)
    preset = build(tokens)

    params = []
    for p in preset.parameters:
        meta = schema_idx.get((p.module_path, p.key))
        kind = meta["kind"] if meta else "unknown"
        unit = meta.get("unit") if meta else None
        entry = {
            "module": p.module_path,
            "key": p.key,
            "kind": kind,
            "stored": p.value,
            "human": from_binary(kind, p.value, unit),
            "display": describe(kind, p.value, unit),
        }
        if unit:
            entry["unit"] = unit
        if is_mic_key(p.key):
            try:
                name = mic_index_to_name(int(float(p.value)))
            except (ValueError, TypeError):
                name = None
            if name:
                entry["mic"] = name
                entry["display"] = name
        params.append(entry)

    out = {
        "file_header": preset.file_header,
        "name": preset.preset_name,
        "parameters": params,
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
