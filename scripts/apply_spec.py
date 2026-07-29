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

  rotation : percent of knob rotation, 0-100   (62 -> stored "0.62")
  fraction : 0.0-1.0 decimal (cab position/distance)
  metered  : native unit shown in the UI (dB / Hz / ms / s / BPM / semitones)
  switch   : true/false (or on/off)
  enum     : integer selector, or its member name ("PR12", "Ribbon 121")

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

REPO_ROOT = pathlib.Path(
    os.environ.get("CLAUDE_PLUGIN_ROOT") or pathlib.Path(__file__).resolve().parents[1]
)
sys.path.insert(0, str(REPO_ROOT))

from format.parser import parse_file
from format.structured import build, set_parameter
from format.translate import describe
from format.writer import write_file
from packs.loader import PackError, detect_pack, load_pack


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Apply a human-valued parameter spec to a template preset."
    )
    ap.add_argument("--template", required=True, help="existing .xml preset to clone")
    ap.add_argument("--spec", required=True, help="JSON file with parameter overrides")
    ap.add_argument("--name", help="new preset name (overrides spec.name)")
    ap.add_argument("--out", required=True, help="output .xml path")
    ap.add_argument("--pack", help="plugin pack id (default: detect from the template)")
    ap.add_argument(
        "--strip-irs",
        action="store_true",
        help="clear custom IR paths so the preset uses internal mics (portable). "
        "Irreversible: the cleared field stops being addressable.",
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
    args = ap.parse_args()

    try:
        run(args)
    except PackError as e:
        die(str(e))


def run(args) -> None:
    template = pathlib.Path(args.template)
    out = pathlib.Path(args.out)

    # --- guards ---------------------------------------------------------
    if not template.exists():
        die(f"Template not found: {template}")
    if not args.dry_run:
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

    spec = read_spec(pathlib.Path(args.spec))
    tokens = parse_file(str(template))
    preset = build(tokens)

    pack = resolve_pack(args.pack, preset.file_header, template)

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
    for i, entry in enumerate(spec.get("parameters", [])):
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
            stored = str(human)
        else:
            spec_meta = pack.require(module, key)
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


def render(spec, stored: str) -> str:
    """Human form of a stored value, for the change list."""
    if spec is None:
        return repr(stored)
    name = spec.member_name(stored)
    if name:
        return name
    return describe(spec.kind, stored, spec.unit)


def resolve_pack(requested, file_header, template):
    if requested:
        return load_pack(requested)
    pack = detect_pack(file_header)
    if pack is None:
        die(
            f"{template} identifies itself as {file_header!r}, which has no pack "
            f"in packs/.\n"
            f"  Pass --pack <id> to force one, or add a pack for this plugin."
        )
    return pack


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
    saved the preset. "No custom IR" is that field set to an empty string.

    This is one-way: an empty value's bytes merge into the neighbouring
    markers, so the key is no longer addressable in the output file.
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


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
