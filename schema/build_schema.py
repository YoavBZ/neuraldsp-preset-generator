"""
Summarise the values used across the user's own preset library.

Reads every preset this installation can see, works out which plugin each one
came from (from its file header), and writes one observed catalog per pack:
for every (module_path, key) seen, the values it actually holds, plus a
heuristically inferred type.

This output is **advisory**. It answers "what does this knob tend to sit at in
real presets?" — a taste anchor when choosing a value. It is NOT the contract:
what a parameter *is* and what values are *legal* live in the hand-curated
`packs/<id>/manifest.json`, which is committed and shared. This file is
generated from the user's own presets, echoes every string in them (including
absolute IR paths), and stays local.

Running this is optional. The tools work without it.

Presets are read from the bundled `samples/` directory and from
`<data root>/packs/<id>/templates/`. The catalog is written to
`<data root>/packs/<id>/observed.json` — see `packs.paths` for how the data root
is resolved, and pass `--data-dir` to override it.

    python -m schema.build_schema [--data-dir DIR]
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from format.parser import parse_file           # noqa: E402
from format.structured import build            # noqa: E402
from packs import observed, paths              # noqa: E402
from packs.loader import detect_pack, list_packs, load_pack  # noqa: E402


# Native-unit (metered) parameters, matched by key suffix. These are shown
# with real numbers in the plugin UI and stored in real units in the file.
# Everything NOT matched here that is a float within [0,1] is a bare rotation
# knob (no numbers on the dial) and is reasoned about as percent-of-rotation.
def _classify(module: str, key: str, ptype: str, values: List[str]):
    """Return (kind, unit). kind drives how human values translate to bytes."""
    if ptype == "bool":
        return "switch", None
    if ptype == "string":
        return ("path" if "Path" in key else "string"), None

    # Name-based metered controls (work for both int and float storage).
    if key.endswith(("Hpf", "Lpf", "HighCut", "LowCut")):
        return "metered", "hz"
    if key.endswith("EQBand1") or key[:-1].endswith("EQBand"):  # EQBand1..9
        return "metered", "db"
    if key in ("gateThreshold", "inputGain", "outputGain") or key.endswith("MicLevel"):
        return "metered", "db"
    if key.endswith("PreDelay") or key in ("doublerSpread", "delayTime"):
        return "metered", "ms"
    if key.endswith("Decay"):
        return "metered", "seconds"
    if key.endswith("Tempo"):
        return "metered", "bpm"
    if key == "transpose":
        return "metered", "semitones"
    if key.endswith("Rate"):
        return "metered", "hz"

    # Discrete selectors stored as integers.
    if key in ("selectedAmp", "delaySync") or key.endswith(
        ("Power", "SyncNote", "MicType", "Pan")
    ):
        return "enum", None

    # Cab mic placement: shown as 0.000–1.000 decimals in the UI, not knobs.
    if key.endswith(("Position", "Distance")):
        return "fraction", None

    nums = [float(v) for v in values if _looks_like_number(v)]
    if nums and all(0.0 <= n <= 1.0 for n in nums):
        return "rotation", None  # bare 0–1 knob → reason in percent

    # Anything else numeric that escaped the rules: do NOT guess a scale.
    return "unknown", None


@dataclass
class ParamStats:
    module_path: str
    key: str
    observed_values: List[str] = field(default_factory=list)
    seen_in: List[str] = field(default_factory=list)

    def infer_type(self) -> str:
        vals = set(self.observed_values)
        if vals <= {"true", "false"}:
            return "bool"
        if all(_looks_like_int(v) for v in vals):
            return "int"
        if all(_looks_like_number(v) for v in vals):
            return "float"
        return "string"

    def to_dict(self) -> Dict[str, Any]:
        t = self.infer_type()
        kind, unit = _classify(self.module_path, self.key, t, self.observed_values)
        d: Dict[str, Any] = {
            "module_path": self.module_path,
            "key": self.key,
            "type": t,
            "kind": kind,
            "seen_in": self.seen_in,
            "observed_values": list(dict.fromkeys(self.observed_values)),
        }
        if unit:
            d["unit"] = unit
        if t in ("int", "float"):
            nums = [float(v) for v in self.observed_values]
            d["observed_min"] = min(nums)
            d["observed_max"] = max(nums)
        return d


def _looks_like_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


def _looks_like_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def build_schema(
    sample_paths: List[pathlib.Path], plugin_name: str = "unknown"
) -> Dict[str, Any]:
    stats: Dict[Tuple[str, str], ParamStats] = {}
    presets_info: List[Dict[str, Any]] = []

    for path in sample_paths:
        tokens = parse_file(str(path))
        preset = build(tokens)
        presets_info.append({"file": path.name, "name": preset.preset_name})
        for param in preset.parameters:
            stats_key = (param.module_path, param.key)
            s = stats.setdefault(
                stats_key, ParamStats(module_path=param.module_path, key=param.key)
            )
            s.observed_values.append(param.value)
            if path.name not in s.seen_in:
                s.seen_in.append(path.name)

    by_module: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for s in stats.values():
        by_module[s.module_path].append(s.to_dict())

    return {
        "schema_version": 1,
        "plugin": plugin_name,
        "source_presets": presets_info,
        "modules": {
            module: sorted(params, key=lambda p: p["key"])
            for module, params in sorted(by_module.items())
        },
    }


def group_by_pack(
    preset_paths: List[pathlib.Path],
) -> Tuple[Dict[str, List[pathlib.Path]], List[Tuple[pathlib.Path, str]]]:
    """Route each preset to the pack whose plugin wrote it.

    Presets name their plugin in their first bytes, so a mixed library sorts
    itself out. Without this, a preset from one plugin would have its parameters
    merged into another plugin's catalog.
    """
    grouped: Dict[str, List[pathlib.Path]] = defaultdict(list)
    unmatched: List[Tuple[pathlib.Path, str]] = []

    for path in preset_paths:
        try:
            header = build(parse_file(str(path))).file_header
        except (OSError, UnicodeDecodeError, IndexError) as e:
            unmatched.append((path, f"could not be parsed ({type(e).__name__})"))
            continue
        pack = detect_pack(header)
        if pack is None:
            unmatched.append((path, f"header {header!r} matches no pack"))
        else:
            grouped[pack.pack_id].append(path)

    return grouped, unmatched


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Summarise the values used across your own preset library."
    )
    ap.add_argument(
        "--data-dir",
        help="where your presets and generated catalogs live (default: "
        "$NDSP_PRESET_DATA, else $CLAUDE_PLUGIN_DATA, else the repo root)",
    )
    args = ap.parse_args()
    paths.set_data_root(args.data_dir)

    pack_ids = list_packs()
    presets = paths.all_presets(pack_ids)
    if not presets:
        print(
            f"No presets found.\n\n{paths.describe_roots()}\n\n"
            f"Add your own presets to one of:\n"
            + "\n".join(f"  {paths.templates_dir(p)}" for p in pack_ids),
            file=sys.stderr,
        )
        sys.exit(1)

    grouped, unmatched = group_by_pack(presets)

    for path, reason in unmatched:
        print(f"skipped {path.name}: {reason}", file=sys.stderr)

    if not grouped:
        print("No presets matched a known pack; nothing written.", file=sys.stderr)
        sys.exit(1)

    warning = paths.data_root_warning()
    if warning:
        print(f"warning: {warning}\n", file=sys.stderr)
    elif paths.is_ephemeral_data_root():
        print(f"{paths.describe_roots()}\n")

    for pack_id, pack_presets in sorted(grouped.items()):
        catalog = build_schema(pack_presets, load_pack(pack_id).display_name)
        observed.save(pack_id, catalog)
        count = sum(len(p) for p in catalog["modules"].values())
        print(
            f"{pack_id}: wrote {paths.observed_path(pack_id)} "
            f"({len(catalog['modules'])} modules, {count} parameters "
            f"from {len(pack_presets)} preset(s))"
        )
        if len(pack_presets) < 3:
            print(
                f"  Note: built from {len(pack_presets)} preset(s), so these "
                f"values are a narrow sample. Add more of your own to "
                f"{paths.templates_dir(pack_id)} for better anchors."
            )


if __name__ == "__main__":
    main()
