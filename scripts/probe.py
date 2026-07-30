"""
Discover what a selector's integer values mean, without ever reading an integer.

The plugin's UI shows a selector's *label* ("1/8 dotted", "Ribbon 121") but never
the integer stored in the file. So the mapping can't be read off the screen. This
inverts the problem: write known integers into disposable presets, let the plugin
tell you what they display.

Each probe preset is named after the value it carries, so the plugin's own preset
browser labels it for you:

    probe delaySyncNote 00      <- load this, read the Sync Note control
    probe delaySyncNote 01
    ...

Usage:

    # Sweep a range and write one preset per value.
    probe.py --param delay/delaySyncNote --out-dir ~/…/User --values 0-15

    # Confirm an assumed ordinal mapping with a SINGLE load (preferred).
    probe.py --param delay/delaySyncNote --out-dir ~/…/User --values 3

Selectors in this format are index-based: the integer is the option's position in
the control, counting from 0. That is confirmed for the mic catalog (0 = the
first mic, 8 = the ninth). So the cheap path is:

  1. Read the control's options off the UI, in order. No integers involved.
  2. Write them into the manifest as `members`, indexed from 0.
  3. Run this with ONE value from the middle and load it. If the label matches
     what you predicted, the whole table is confirmed.

Probe presets are throwaway. Delete them when you're done.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

# The plugin's own modules live beside this script, so the root is always
# derivable from __file__ — no environment variable needed, nothing to go stale.
PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded, resolve_pack
from format.parser import parse_file
from format.structured import build, set_parameter
from format.writer import write_file



def main() -> None:
    ap = argparse.ArgumentParser(
        description="Write disposable presets that reveal what a selector's "
        "integer values display as in the plugin."
    )
    ap.add_argument(
        "--template",
        default=str(PLUGIN_ROOT / "samples" / "Example_Clean_PR12.xml"),
        help="preset to clone (default: the bundled example)",
    )
    ap.add_argument(
        "--param",
        required=True,
        metavar="MODULE/KEY",
        help="selector to probe, e.g. delay/delaySyncNote (top-level: /selectedAmp)",
    )
    ap.add_argument(
        "--values",
        default="0-15",
        help="values to write: '0-15', '0,3,7', or a single '3'. Default 0-15.",
    )
    ap.add_argument("--out-dir", required=True, help="where to write the probe presets")
    ap.add_argument("--pack", help="pack id (default: detect from the template)")
    ap.add_argument(
        "--force", action="store_true", help="overwrite existing probe presets"
    )
    args = ap.parse_args()
    run(args)


def run(args) -> None:
    template = pathlib.Path(os.path.expanduser(args.template))
    if not template.exists():
        die(f"Template not found: {template}")

    module, _, key = args.param.rpartition("/")
    values = parse_values(args.values)

    preset = build(parse_file(str(template)))
    pack = resolve_pack(args.pack, preset.file_header, template)

    if (module, key) not in preset.by_path:
        die(
            f"{args.param} is not present in {template.name}.\n"
            f"  Run show.py on the template to see what it contains.\n"
            f"  Top-level parameters are written with a leading slash, e.g. "
            f"/selectedAmp."
        )

    spec = pack.get(module, key)
    if spec is not None and spec.kind != "enum":
        die(
            f"{args.param} has kind {spec.kind!r}, not 'enum'. Probing only makes "
            f"sense for selectors; a {spec.kind} shows its value in the UI already."
        )

    out_dir = pathlib.Path(os.path.expanduser(args.out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    # Check the whole sweep before writing any of it. A half-written sweep is
    # worse than none: the user reads these by loading them in the plugin, so
    # leftover presets from an aborted run are actively misleading.
    if not args.force:
        clashes = [
            out_dir / f"probe {key} {value:02d}.xml"
            for value in values
            if (out_dir / f"probe {key} {value:02d}.xml").exists()
        ]
        if clashes:
            die(
                f"{len(clashes)} probe preset(s) already exist, starting with "
                f"{clashes[0].name}.\n"
                f"  Nothing was written. Pass --force to overwrite them, or "
                f"delete the previous sweep."
            )

    written = []
    for value in values:
        label = f"probe {key} {value:02d}"
        out = out_dir / f"{label}.xml"

        # Deliberately bypasses validation: the point is to explore values the
        # manifest does not yet describe.
        fresh = build(parse_file(str(template)))
        set_parameter(fresh, "", "name", label)
        set_parameter(fresh, module, key, str(value))
        write_file(str(out), fresh.tokens)
        written.append((value, out))

    print(f"Wrote {len(written)} probe preset(s) to {out_dir}\n")
    known = spec.members if spec is not None else None
    for value, out in written:
        predicted = f"  (predicted: {known[str(value)]})" if known and str(value) in known else ""
        print(f"  {value:>3}  {out.name}{predicted}")

    print(
        f"\nNow, in the plugin:\n"
        f"  1. Open the preset browser and load each 'probe {key} NN' preset.\n"
        f"  2. Read what the {spec.ui if spec and spec.ui else key} control shows.\n"
        f"  3. Tell me the label for each number — I'll write them into\n"
        f"     packs/{pack.pack_id}/manifest.json as this selector's members.\n"
        f"\nDelete the probe presets when you're done."
    )


def parse_values(text: str) -> list:
    text = text.strip()
    if "-" in text and "," not in text:
        lo, _, hi = text.partition("-")
        try:
            start, end = int(lo), int(hi)
        except ValueError:
            die(f"--values {text!r} is not a range like '0-15'.")
        if end < start:
            die(f"--values {text!r}: end is below start.")
        if end - start > 63:
            die(
                f"--values {text!r} spans {end - start + 1} presets. That's more "
                f"than anyone wants to load by hand — narrow it down, or read the "
                f"control's options off the UI and confirm with a single value."
            )
        return list(range(start, end + 1))
    try:
        return [int(part) for part in text.split(",") if part.strip()]
    except ValueError:
        die(f"--values {text!r} is not a number, list, or range.")



if __name__ == "__main__":
    guarded(main)
