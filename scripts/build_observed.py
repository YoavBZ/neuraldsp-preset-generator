"""
Summarise the values used across the user's own preset library.

Reads every preset this installation can see, works out which plugin each one
came from (from its file header), and writes one observed catalog per pack:
for every (module_path, key) seen, the values it actually holds and which
presets they came from. Nothing more — no inferred kind, unit or type, because
the manifest declares those and a second guess would only ever disagree.

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

    python scripts/build_observed.py [--data-dir DIR]
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

# The plugin's own modules live beside this script, so the root is always
# derivable from __file__ — no environment variable needed, nothing to go stale.
PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import add_data_dir_arg, die, guarded
from format.parser import parse_file           # noqa: E402
from format.structured import build            # noqa: E402
from packs import observed, paths              # noqa: E402
from packs.loader import detect_pack, list_packs, load_pack  # noqa: E402


@dataclass
class ParamStats:
    module_path: str
    key: str
    observed_values: List[str] = field(default_factory=list)
    seen_in: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Just the values seen, and where.

        Deliberately does NOT record a kind, unit or type: the manifest declares
        those, and a generated file that guesses them again is a second source of
        truth waiting to disagree with the first.
        """
        return {
            "key": self.key,
            "seen_in": self.seen_in,
            "observed_values": list(dict.fromkeys(self.observed_values)),
        }


def summarise(
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
    add_data_dir_arg(ap)
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
        sys.exit(2)

    grouped, unmatched = group_by_pack(presets)

    for path, reason in unmatched:
        print(f"skipped {path.name}: {reason}", file=sys.stderr)

    if not grouped:
        print("No presets matched a known pack; nothing written.", file=sys.stderr)
        sys.exit(2)

    warning = paths.data_root_warning()
    if warning:
        print(f"warning: {warning}\n", file=sys.stderr)
    elif paths.is_ephemeral_data_root():
        print(f"{paths.describe_roots()}\n")

    for pack_id, pack_presets in sorted(grouped.items()):
        catalog = summarise(pack_presets, load_pack(pack_id).display_name)
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
    guarded(main)
