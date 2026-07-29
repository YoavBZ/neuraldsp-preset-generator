"""
Apply a HUMAN-valued parameter spec to a template preset.

Reads:
  --template  path to an existing .xml preset to use as the byte template
  --spec      path to a JSON file with parameter overrides
  --name      new preset name (top-level "name" field)
  --out       output .xml path

Spec JSON format — values are HUMAN values, translated to the binary's
stored encoding via each parameter's `kind` in schema/morgan_schema.json:

    {
      "name": "Hotel California Lead",
      "parameters": [
        {"module": "pr12Amp", "key": "pr12Volume", "value": 62},
        {"module": "delay",   "key": "delayMix",    "value": 35},
        {"module": "delay",   "key": "delayActive", "value": true},
        {"module": "delay",   "key": "delayTime",   "value": 480},
        {"module": "",        "key": "selectedAmp", "value": 1}
      ]
    }

Value meaning depends on the parameter's kind:
  - rotation : percent of knob rotation, 0–100   (62 -> stored "0.62")
  - fraction : 0.0–1.0 decimal (cab position/distance)
  - metered  : native unit shown in the UI (dB / Hz / ms / s / BPM / semitones)
  - switch   : true/false (or on/off)
  - enum     : integer selector (e.g. selectedAmp 0=AC20,1=PR12,2=SW50R)

Escape hatch: add "raw": true to an entry to write its "value" as the literal
stored string, bypassing translation (use for IR file paths / unknown kinds).

Unknown (module,key) pairs and out-of-range values are reported; out-of-range
metered values warn but proceed, structural/kind errors abort.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from format.parser import parse_file
from format.structured import build, set_parameter
from format.translate import to_binary
from format.writer import write_file
from schema.cab import is_mic_key, mic_name_to_index
from schema.loader import index_by_key, load_schema


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True, help="existing .xml preset to clone")
    ap.add_argument("--spec", required=True, help="JSON file with parameter overrides")
    ap.add_argument("--name", help="new preset name (overrides spec.name)")
    ap.add_argument("--out", required=True, help="output .xml path")
    ap.add_argument(
        "--strip-irs",
        action="store_true",
        help="clear custom IR paths so the preset uses factory mics (portable). "
        "Recommended for generated presets cloned from IR-using templates.",
    )
    args = ap.parse_args()

    spec = json.loads(pathlib.Path(args.spec).read_text())
    schema_idx = index_by_key(load_schema())
    tokens = parse_file(args.template)
    preset = build(tokens)

    new_name = args.name or spec.get("name")
    if new_name:
        set_parameter(preset, "", "name", new_name)

    if args.strip_irs or spec.get("stripIRs"):
        stripped = strip_custom_irs(preset)
        if stripped:
            print(f"Stripped custom IR path(s): {', '.join(stripped)} "
                  f"(now using factory mics)")

    unknown = []
    warnings = []
    applied = 0
    for entry in spec.get("parameters", []):
        module_path = entry["module"]
        key = entry["key"]
        human = entry["value"]

        if (module_path, key) not in preset.by_path:
            unknown.append(f"{module_path}/{key}")
            continue

        if entry.get("raw"):
            stored = str(human)
        elif is_mic_key(key) and isinstance(human, str):
            # Allow specifying a mic by name, e.g. "Ribbon 121".
            try:
                stored = str(mic_name_to_index(human))
            except KeyError as e:
                print(f"Error on {module_path}/{key}: {e}", file=sys.stderr)
                sys.exit(2)
        else:
            meta = schema_idx.get((module_path, key))
            if meta is None:
                unknown.append(f"{module_path}/{key} (not in schema)")
                continue
            try:
                stored = to_binary(meta["kind"], human, meta.get("unit"))
            except ValueError as e:
                print(f"Error on {module_path}/{key}: {e}", file=sys.stderr)
                sys.exit(2)
            _range_check(meta, stored, module_path, key, warnings)

        set_parameter(preset, module_path, key, stored)
        applied += 1

    if unknown:
        print(
            f"Refused: {len(unknown)} unknown parameter(s) for this template: "
            f"{unknown[:10]}{'...' if len(unknown) > 10 else ''}",
            file=sys.stderr,
        )
        sys.exit(2)

    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)

    write_file(args.out, preset.tokens)
    print(f"Wrote {args.out} (applied {applied} parameter override(s))")


def strip_custom_irs(preset) -> list:
    """Clear any custom IR file paths so the cab falls back to factory mics.

    A custom IR is stored as a string value in `<side>ChosenIRFilePath`.
    "No custom IR" is that field set to an empty string (verified against the
    factory Default preset: bytes `...Path\\x00\\x01\\x02\\x05\\x00...`).
    """
    cleared = []
    for side in ("left", "right"):
        key = f"{side}ChosenIRFilePath"
        if ("cabParameters", key) in preset.by_path:
            if preset.by_path[("cabParameters", key)].value != "":
                set_parameter(preset, "cabParameters", key, "")
                cleared.append(key)
    return cleared


def _range_check(meta, stored, module_path, key, warnings) -> None:
    if meta["type"] not in ("int", "float"):
        return
    try:
        v = float(stored)
    except ValueError:
        return
    lo, hi = meta.get("observed_min"), meta.get("observed_max")
    if lo is not None and hi is not None and not (lo <= v <= hi):
        warnings.append(
            f"{module_path}/{key}={stored} is outside observed range "
            f"[{lo}, {hi}] (allowed, but unverified)"
        )


if __name__ == "__main__":
    main()
