"""
Print every parameter in a preset, with its stored value and a human value.

    show.py PRESET.xml            # JSON, for the agent to read
    show.py PRESET.xml --text     # grouped, for a person to read

Kinds, units, selector member names and declared ranges come from the pack
manifest, which is committed — so this works on a fresh clone with no build
step. If a generated observed-value catalog exists (packs/<id>/observed.json,
built from your own presets), typical values are folded in as advisory
anchors: what the knob tends to sit at, never what it is allowed to be.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

# The plugin's own modules live beside this script, so the root is always
# derivable from __file__ — no environment variable needed, nothing to go stale.
PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from format.parser import parse_file
from format.structured import build
from format.translate import describe, from_binary
from packs import observed as observed_catalog
from packs import paths
from packs.loader import PackError, detect_pack, load_pack


def main() -> None:
    ap = argparse.ArgumentParser(description="Inspect a Neural DSP preset.")
    ap.add_argument("preset", help="path to .xml preset")
    ap.add_argument("--pack", help="plugin pack id (default: detect from the file)")
    ap.add_argument("--text", action="store_true", help="human-readable output")
    ap.add_argument(
        "--data-dir",
        help="where your presets and generated catalogs live (default: "
        "$NDSP_PRESET_DATA, else $CLAUDE_PLUGIN_DATA, else the repo root)",
    )
    args = ap.parse_args()
    paths.set_data_root(args.data_dir)

    path = pathlib.Path(args.preset)
    if not path.exists():
        print(f"error: preset not found: {path}", file=sys.stderr)
        sys.exit(2)

    preset = build(parse_file(str(path)))

    try:
        pack = load_pack(args.pack) if args.pack else detect_pack(preset.file_header)
    except PackError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)
    if pack is None:
        print(
            f"error: {path} identifies itself as {preset.file_header!r}, which has "
            f"no pack in packs/.\n  Pass --pack <id> to force one.",
            file=sys.stderr,
        )
        sys.exit(2)

    observed = observed_catalog.index(pack.pack_id)

    params = []
    for p in preset.parameters:
        spec = pack.get(p.module_path, p.key)
        kind = spec.kind if spec else "unknown"
        unit = spec.unit if spec else None

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
        if spec:
            if spec.ui:
                entry["ui"] = spec.ui
            if spec.min is not None or spec.max is not None:
                entry["range"] = [spec.min, spec.max]
            if not spec.writable:
                entry["writable"] = False
            if spec.needs_confirmation:
                entry["unconfirmed_selector"] = True
            name = spec.member_name(p.value)
            if name:
                entry["member"] = name
                entry["display"] = name
        seen = observed.get((p.module_path, p.key))
        if seen:
            entry["observed_values"] = seen
        params.append(entry)

    out = {
        "file": str(path),
        "pack": pack.pack_id,
        "plugin": pack.display_name,
        "file_header": preset.file_header,
        "name": preset.preset_name,
        "parameters": params,
    }

    note = observed_catalog.summary(pack.pack_id)
    if note:
        out["observed"] = note

    if args.text:
        print_text(out, pack)
    else:
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")


def print_text(out: dict, pack) -> None:
    print(f"{out['name']}   [{out['plugin']}]")
    print(f"{out['file']}\n")
    current = None
    for p in out["parameters"]:
        if p["module"] != current:
            current = p["module"]
            print(f"  {current or '(top level)'}")
        label = p.get("ui") or p["key"]
        flag = " (!)" if p.get("unconfirmed_selector") else ""
        print(f"    {label:<22} {p['display']:<22} {p['key']}{flag}")
    if out.get("observed"):
        print(f"\n  advisory: {out['observed']}")
    if any(p.get("unconfirmed_selector") for p in out["parameters"]):
        print(
            f"\n  (!) selector whose member names are not yet confirmed — see "
            f"packs/{pack.pack_id}/manifest.json"
        )


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # Piped into `head`, `less`, etc. Exit quietly instead of dumping a
        # traceback over the user's output.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
