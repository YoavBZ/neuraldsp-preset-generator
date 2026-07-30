"""
Apply a HUMAN-valued parameter spec to a template preset.

    apply_spec.py --template IN.xml --spec SPEC.json --out OUT.xml [--strip-irs]

Values in the spec are HUMAN values, translated to the binary's stored encoding
using each parameter's `kind` in the pack manifest (packs/<id>/manifest.json):

    {
      "name": "Hotel California Lead",
      "parameters": [
        {"module": "",         "key": "selectedAmp",  "value": "SW50R"},
        {"module": "sw50rAmp", "key": "sw50rVolume",  "value": 62},
        {"module": "delay",    "key": "delayActive",  "value": true},
        {"module": "delay",    "key": "delayTime",    "value": 480}
      ]
    }

Knobs are percent of rotation (0-100); everything else uses the unit the plugin
shows. The full table lives in reference/preset-spec.md — one copy, so it cannot
drift from what the code does.

A time or rate value may be given as a note division instead of a number, so a
recipe stays correct at any tempo:

    {"module": "delay", "key": "delayTime", "value": {"note": "1/8 dotted",
                                                      "bpm": 120}}   -> 375 ms

Escape hatch: "raw": true writes the value as the literal stored string,
bypassing translation and validation. Use only for IR file paths.

Illegal values abort with a message and a non-zero exit; the output file is
only written once every override has been validated.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Optional

# The plugin's own modules live beside this script, so the root is always
# derivable from __file__ — no environment variable needed, nothing to go stale.
PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded, resolve_pack
from format.parser import parse_file
from format.structured import build, set_parameter
from format.translate import describe
from format.writer import write_file
from packs.loader import load_pack
from packs.recipes import (
    amp_prefix_for,
    load_recipes,
    resolve_value,
    selected_amp_in,
    stack,
)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Apply a human-valued parameter spec to a template preset."
    )
    ap.add_argument("--template", help="existing .xml preset to clone")
    ap.add_argument("--spec", help="JSON file with parameter overrides")
    ap.add_argument(
        "--recipe",
        action="append",
        default=[],
        metavar="LAYER/ID",
        help="stack a recipe from the pack, e.g. amp/sw50r-singing-lead. Repeatable; "
        "later recipes win, and --spec is applied last so it can override them.",
    )
    ap.add_argument(
        "--bpm",
        type=float,
        help="tempo for recipes that carry a note division (e.g. a quarter-note delay)",
    )
    ap.add_argument("--name", help="new preset name (overrides spec.name)")
    ap.add_argument("--out", help="output .xml path")
    ap.add_argument("--pack", help="plugin pack id (default: detect from the template)")
    ap.add_argument(
        "--strip-irs",
        action="store_true",
        help="clear custom IR paths so the preset uses internal mics (portable)",
    )
    ap.add_argument(
        "--allow-out-of-range",
        action="store_true",
        help="downgrade declared-range violations from an error to a warning",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="overwrite --out if it already exists",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print the before/after diff without writing --out",
    )
    ap.add_argument(
        "--list-recipes",
        action="store_true",
        help="print every available recipe with what it is for, and exit",
    )
    args = ap.parse_args()

    if args.list_recipes:
        list_recipes(args.pack)
        return

    run(args)


def list_recipes(pack_id: Optional[str]) -> None:
    """Print the recipe catalogue. The only other discovery path was guessing."""
    pack = load_pack(pack_id) if pack_id else load_pack()
    for layer, group in load_recipes(pack.pack_id).items():
        print(f"\n{layer}")
        width = max(len(rid) for rid in group)
        for rid, recipe in group.items():
            print(f"  {rid:<{width}}  {recipe.use_when}")


def run(args) -> None:
    if not args.template:
        die("--template is required (it is the preset the writer clones).")
    if not args.out:
        die("--out is required (where to write the result).")
    template = pathlib.Path(os.path.expanduser(args.template))
    out = pathlib.Path(os.path.expanduser(args.out))

    # --- guards ---------------------------------------------------------
    # These run for --dry-run too. A preview that reports success where the real
    # run would refuse to write is a preview that lies.
    if not template.exists():
        die(f"Template not found: {template}")
    if template.resolve() == out.resolve():
        die(
            f"--out is the same file as --template ({template}).\n"
            f"  Editing never overwrites its input; choose a different --out."
        )
    if out.exists() and not args.force:
        die(
            f"--out already exists: {out}\n"
            f"  Pass --force to overwrite it, or choose a different path."
        )

    if not args.spec and not args.recipe:
        die("Nothing to apply. Pass --spec, --recipe, or both.")

    spec = read_spec(pathlib.Path(args.spec)) if args.spec else {}
    tokens = parse_file(str(template))
    preset = build(tokens)

    pack = resolve_pack(args.pack, preset.file_header, template)

    # Recipes first, the hand-written spec last, so an explicit override always
    # beats a recipe default.
    entries = list(spec.get("parameters", []))
    if args.recipe:
        entries = stack(args.recipe, pack, _amp_prefix(args, spec, pack, preset)) + entries

    # --- name -----------------------------------------------------------
    changes: list[tuple[str, str, str]] = []
    new_name = args.name or spec.get("name")
    if new_name:
        before = preset.preset_name
        set_parameter(preset, "", "name", str(new_name))
        changes.append(("name", before, str(new_name)))

    # --- IR stripping ---------------------------------------------------
    if args.strip_irs or spec.get("stripIRs"):
        for key, before in strip_custom_irs(preset):
            changes.append((f"cabParameters/{key}", before, "(cleared)"))

    # --- parameter overrides --------------------------------------------
    warnings: list[str] = []
    for i, entry in enumerate(entries):
        module, key, human = read_entry(entry, i)
        param = preset.by_path.get((module, key))
        display = f"{module}/{key}" if module else key

        if param is None:
            die(
                f"{display} is not present in this template.\n"
                f"  The writer clones a template and mutates existing values; it "
                f"cannot add parameter slots.\n"
                f"  Run show.py on the template to see what it contains."
            )

        if entry.get("raw"):
            # `raw` skips translation and range checks, not the read-only guard:
            # bypassing validation on an IR path is the point, corrupting the
            # format-version field is not.
            spec_meta = pack.get(module, key)
            if spec_meta is not None and not spec_meta.writable:
                die(
                    f"{display} is marked read-only in the manifest and must not "
                    f"be written, with or without \"raw\"."
                )
            stored = str(human)
        else:
            spec_meta = pack.require(module, key)
            human = resolve_value(human, spec_meta, args.bpm)
            stored = pack.to_stored(
                spec_meta, human, args.allow_out_of_range, warnings
            )

        if stored != param.value:
            spec_meta = pack.get(module, key)
            changes.append(
                (display, render(spec_meta, param.value), render(spec_meta, stored))
            )
        set_parameter(preset, module, key, stored)

    # --- report ---------------------------------------------------------
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)

    if changes:
        width = max(len(path) for path, _, _ in changes)
        print(f"{len(changes)} change(s) against {template.name}:")
        for path, before, after in changes:
            print(f"  {path:<{width}}  {before}  ->  {after}")
    else:
        print(f"No changes against {template.name}.")

    if args.dry_run:
        print("\nDry run — nothing written.")
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    write_file(str(out), preset.tokens)
    print(f"\nWrote {out}")


def _amp_prefix(args, spec, pack, preset):
    """Module prefix for the amp the finished preset will use.

    Order matters and matches the order values are applied: an explicit --spec
    wins, then whichever amp the recipe stack selects, then the template's
    current amp. Getting this wrong is silent — an {amp}EQ recipe resolved
    against the wrong amp writes to a module the live amp doesn't use, so the EQ
    simply does nothing.
    """
    for entry in spec.get("parameters", []):
        if isinstance(entry, dict) and entry.get("key") == "selectedAmp" and "value" in entry:
            return amp_prefix_for(pack, entry["value"])

    selected = selected_amp_in(args.recipe, pack.pack_id)
    if selected is not None:
        return amp_prefix_for(pack, selected)

    param = preset.by_path.get(("", "selectedAmp"))
    return amp_prefix_for(pack, param.value) if param else None


def render(spec, stored: str) -> str:
    """Human form of a stored value, for the change list."""
    if spec is None:
        return repr(stored)
    name = spec.member_name(stored)
    if name:
        return name
    return describe(spec.kind, stored, spec.unit)



def read_spec(path: pathlib.Path) -> dict:
    if not path.exists():
        die(f"Spec file not found: {path}")
    try:
        spec = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        die(f"Spec file {path} is not valid JSON: {e}")
    if not isinstance(spec, dict):
        die(f"Spec file {path} must contain a JSON object, got {type(spec).__name__}.")
    params = spec.get("parameters", [])
    if not isinstance(params, list):
        die(f"Spec file {path}: 'parameters' must be a list.")
    return spec


def read_entry(entry, index: int):
    where = f"parameters[{index}]"
    if not isinstance(entry, dict):
        die(f"{where} must be an object with 'module', 'key' and 'value'.")
    missing = [f for f in ("module", "key", "value") if f not in entry]
    if missing:
        die(
            f"{where} is missing {', '.join(repr(m) for m in missing)}.\n"
            f"  Each entry needs: "
            f'{{"module": "delay", "key": "delayMix", "value": 35}}\n'
            f"  Top-level parameters use an empty module: "
            f'{{"module": "", "key": "selectedAmp", "value": "PR12"}}'
        )
    return entry["module"], entry["key"], entry["value"]


def strip_custom_irs(preset) -> list:
    """Clear custom IR file paths so the cab falls back to internal mics.

    A custom IR is an absolute path that only resolves on the machine that
    saved the preset. "No custom IR" is that field set to an empty string,
    byte-identical to how an IR-free preset stores it.
    """
    cleared = []
    for side in ("left", "right"):
        key = f"{side}ChosenIRFilePath"
        param = preset.by_path.get(("cabParameters", key))
        if param is not None and param.value != "":
            before = param.value
            set_parameter(preset, "cabParameters", key, "")
            cleared.append((key, before))
    return cleared



if __name__ == "__main__":
    guarded(main)
