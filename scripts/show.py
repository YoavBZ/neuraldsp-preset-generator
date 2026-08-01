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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import add_data_dir_arg, die, guarded, resolve_pack
from format.parser import parse_file
from format.structured import build
from format.translate import describe, from_binary
from packs import observed as observed_catalog
from packs import paths



def main() -> None:
    ap = argparse.ArgumentParser(description="Inspect a Neural DSP preset.")
    ap.add_argument("preset", help="path to .xml preset")
    ap.add_argument("--pack", help="plugin pack id (default: detect from the file)")
    ap.add_argument("--text", action="store_true", help="human-readable output")
    add_data_dir_arg(ap)
    args = ap.parse_args()
    paths.set_data_root(args.data_dir)

    path = pathlib.Path(os.path.expanduser(args.preset))
    if not path.exists():
        die(f"Preset not found: {path}")

    preset = build(parse_file(str(path)))

    pack = resolve_pack(args.pack, preset.file_header, path)

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
            if spec.needs_review:
                # The write path warns about a guessed kind; the read path was
                # silent, so `display` showed a human value computed through an
                # unverified mapping with nothing marking it as a guess.
                entry["guessed_kind"] = True
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

    # Where per-pack knowledge lives, so a skill can find it without having to
    # work out how the data root resolved.
    notes = paths.learned_tones_path(pack.pack_id)
    out["data_root"] = str(paths.data_root())
    # A bootstrapped pack has no tone.md, so report whether it is there rather
    # than handing back a path that does not resolve.
    tone = paths.PLUGIN_ROOT / "packs" / pack.pack_id / "tone.md"
    out["tone_knowledge"] = {"path": str(tone), "exists": tone.exists()}
    out["learned_notes"] = {"path": str(notes), "exists": notes.exists()}

    if preset.duplicates:
        out["duplicate_parameters"] = sorted(
            f"{m}/{k}" if m else k for m, k in set(preset.duplicates)
        )

    # Named in the file but carrying no value: real parameters of the plugin
    # that this preset does not store, so they can be neither read nor written.
    # Without this they are simply invisible.
    if preset.valueless:
        out["valueless_parameters"] = sorted(
            f"{m}/{k}" if m else k for m, k in set(preset.valueless)
        )

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
        flag = " (!)" if (p.get("unconfirmed_selector") or p.get("guessed_kind")) else ""
        print(f"    {label:<22} {p['display']:<22} {p['key']}{flag}")
    if out.get("observed"):
        print(f"\n  advisory: {out['observed']}")
    notes = out["learned_notes"]
    tone = out["tone_knowledge"]
    print(
        f"  tone knowledge: {tone['path']}"
        f"{'' if tone['exists'] else '  (none for this pack)'}"
    )
    print(
        f"  learned notes:  {notes['path']}"
        f"{'' if notes['exists'] else '  (none yet)'}"
    )
    if out.get("duplicate_parameters"):
        print(
            f"\n  (!) duplicate parameter path(s): "
            f"{', '.join(out['duplicate_parameters'])}\n"
            f"      A write to one of these reaches only the last occurrence."
        )
    if any(p.get("unconfirmed_selector") for p in out["parameters"]):
        print(
            f"\n  (!) selector whose member names are not yet confirmed — see "
            f"packs/{pack.pack_id}/manifest.json"
        )
    guessed = sum(1 for p in out["parameters"] if p.get("guessed_kind"))
    if guessed:
        print(
            f"\n  (!) {guessed} parameter(s) have a GUESSED kind, so the value "
            f"shown for them is\n      an interpretation, not a reading. See "
            f"packs/{pack.pack_id}/manifest.json"
        )


if __name__ == "__main__":
    guarded(main)
