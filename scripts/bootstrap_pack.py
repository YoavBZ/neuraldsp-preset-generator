"""
Draft a pack for a Neural DSP plugin this tool doesn't know yet.

Point it at one preset from the new plugin. It reads the plugin's own name out of
the file, infers what it safely can about each parameter, and writes a manifest
draft plus a list of the questions only you can answer.

    bootstrap_pack.py --preset ~/…/SomePreset.xml --pack-id gojira

What it can infer, and what it can't:

- **Names and structure** come straight from the file, so they are exact.
- **Kinds** are guessed from key names and observed values, the same heuristics
  that used to drive the old generated catalog. Good enough to start, wrong often
  enough that the draft is marked `needs_review` until a human confirms it.
- **Ranges** cannot be inferred at all. One preset shows one value; that says
  nothing about limits. They are left undeclared, which means unchecked.
- **Selector members** cannot be inferred either — the plugin never shows the
  stored integer. `scripts/probe.py` is how you find those out.

So this gets you from "no support at all" to "a draft to correct", which is the
part that was previously a code change.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded
from format.parser import parse_file
from format.structured import build
from packs.loader import PACKS_DIR, detect_pack

# Key-name patterns that reliably indicate a metered control and its unit. These
# are conventions across Neural DSP plugins, not facts about any one of them, so
# every result is flagged for review.
UNIT_HINTS = [
    (re.compile(r"(Hpf|Lpf|HighCut|LowCut|Rate)$"), "hz"),
    (re.compile(r"(EQBand\d+|MicLevel|Gain|Threshold)$"), "db"),
    (re.compile(r"(PreDelay|Spread|Time)$"), "ms"),
    (re.compile(r"Decay$"), "seconds"),
    (re.compile(r"Tempo$"), "bpm"),
    (re.compile(r"^transpose$"), "semitones"),
]
SELECTOR_HINTS = re.compile(r"(Type|Mode|Note|Pan|Power|Sync|selected[A-Z])")


def looks_numeric(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


def infer(key: str, values: list) -> dict:
    """Best guess at one parameter's kind, with an honest confidence marker."""
    unique = set(values)

    if unique <= {"true", "false"}:
        return {"kind": "switch"}

    if not all(looks_numeric(v) for v in unique):
        return {"kind": "path" if "Path" in key else "string"}

    for pattern, unit in UNIT_HINTS:
        if pattern.search(key):
            return {"kind": "metered", "unit": unit, "needs_review": True}

    if SELECTOR_HINTS.search(key) and all(float(v).is_integer() for v in unique):
        return {"kind": "enum", "members": None, "needs_confirmation": True}

    if all(0.0 <= float(v) <= 1.0 for v in unique):
        kind = "fraction" if re.search(r"(Position|Distance)$", key) else "rotation"
        return {"kind": kind, "needs_review": True}

    return {"kind": "metered", "needs_review": True, "note": "unit unknown"}


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Draft a pack manifest from one preset of an unknown plugin."
    )
    ap.add_argument("--preset", required=True, help="a preset from the new plugin")
    ap.add_argument("--pack-id", help="short id (default: the file's own header)")
    ap.add_argument("--display-name", help="the plugin's name as users know it")
    ap.add_argument("--force", action="store_true", help="overwrite an existing draft")
    args = ap.parse_args()

    preset_path = pathlib.Path(args.preset).expanduser()
    if not preset_path.exists():
        die(f"Preset not found: {preset_path}")

    preset = build(parse_file(str(preset_path)))
    header = preset.file_header
    if not header:
        die(f"{preset_path} has no plugin header — is it a Neural DSP preset?")

    existing = detect_pack(header)
    if existing is not None and not _is_draft(existing.pack_id):
        die(
            f"{preset_path.name} is already supported: it identifies as "
            f"{header!r}, which is pack {existing.pack_id!r}.\n"
            f"  Nothing to bootstrap — that pack has been reviewed. Add the "
            f"preset to your templates directory instead."
        )

    pack_id = args.pack_id or re.sub(r"[^a-z0-9]+", "-", header.lower()).strip("-")
    out_dir = PACKS_DIR / pack_id
    manifest_path = out_dir / "manifest.json"
    if manifest_path.exists() and not args.force:
        die(
            f"A draft pack for {header!r} already exists at {manifest_path}.\n"
            f"  Pass --force to redraft it — but note that redrafting discards "
            f"any ranges, selector members or corrections you have added."
        )

    by_key = collections.defaultdict(list)
    for param in preset.parameters:
        by_key[f"{param.module_path}/{param.key}"].append(param.value)

    parameters = collections.OrderedDict()
    for path in sorted(by_key):
        key = path.rpartition("/")[2]
        parameters[path] = infer(key, by_key[path])

    manifest = collections.OrderedDict([
        ("manifest_version", 1),
        ("pack_id", pack_id),
        ("display_name", args.display_name or header.title()),
        ("vendor", "Neural DSP"),
        ("file_header", header),
        ("draft", True),
        ("drafted_from", preset_path.name),
        ("description",
         f"DRAFT pack for {args.display_name or header}. Generated by "
         f"scripts/bootstrap_pack.py from one preset. Kinds are guesses; ranges "
         f"and selector members are absent because neither can be inferred from "
         f"a preset. Review before trusting."),
        ("parameters", parameters),
    ])

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    review = [p for p, e in parameters.items() if e.get("needs_review")]
    selectors = [p for p, e in parameters.items() if e.get("needs_confirmation")]
    report(pack_id, manifest_path, parameters, review, selectors, preset_path)


def report(pack_id, manifest_path, parameters, review, selectors, preset_path):
    print(f"Wrote {manifest_path}")
    print(f"  {len(parameters)} parameters from {preset_path.name}\n")

    kinds = collections.Counter(e["kind"] for e in parameters.values())
    print("  inferred kinds: " + ", ".join(f"{k}={n}" for k, n in sorted(kinds.items())))

    print("\nWhat this draft does NOT know — in the order worth fixing:\n")
    print("1. RANGES. None are declared, so every value is written unchecked.")
    print("   A preset shows one value, which says nothing about limits. Add")
    print("   `min`/`max` from the plugin's own UI as you learn them.")
    if selectors:
        print(f"\n2. SELECTORS ({len(selectors)}). The plugin never displays the stored")
        print("   integer, so these cannot be read off the screen:")
        for path in selectors[:8]:
            print(f"     {path}")
        if len(selectors) > 8:
            print(f"     … and {len(selectors) - 8} more")
        print("   Use: python scripts/probe.py --param <path> --values 0-7 \\")
        print(f"          --out-dir <your user preset folder> --pack {pack_id}")
    if review:
        print(f"\n3. GUESSED KINDS ({len(review)}). Marked `needs_review`. A wrong kind")
        print("   means a wrong value: a knob read as metered writes raw numbers")
        print("   where the plugin expects 0-1. Check these against the UI:")
        for path in review[:8]:
            print(f"     {path}")
        if len(review) > 8:
            print(f"     … and {len(review) - 8} more")

    print("\nThen: drop the preset in your templates directory, run")
    print(f"  python scripts/show.py {preset_path} --pack {pack_id} --text")
    print("and check the values look like what the plugin shows you.")
    print("\nRemove `\"draft\": true` from the manifest when you trust it.")


def _is_draft(pack_id: str) -> bool:
    """A drafted pack may be redrafted; a reviewed one may not be clobbered."""
    path = PACKS_DIR / pack_id / "manifest.json"
    try:
        return bool(json.loads(path.read_text()).get("draft"))
    except (OSError, json.JSONDecodeError):
        return False



if __name__ == "__main__":
    guarded(main)
