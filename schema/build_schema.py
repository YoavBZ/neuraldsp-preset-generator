"""
Infer a parameter schema from the user's own preset samples.

Reads every `.xml` in `samples/`, parses each, and produces
`schema/morgan_schema.json`. The schema records, for every (module_path, key)
seen:
  - inferred type: bool, int, float, string, enum
  - observed values across samples (min/max for numeric, set for enum/string)
  - the source preset(s) the parameter was seen in

The schema is the LLM's contract: when generating or editing presets, the
agent picks values that respect each parameter's observed range and type.

Run as a module:
    python -m schema.build_schema
"""

from __future__ import annotations

import json
import pathlib
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from format.parser import parse_file  # noqa: E402
from format.structured import build   # noqa: E402

SAMPLES_DIR = REPO_ROOT / "samples"
OUTPUT_PATH = REPO_ROOT / "schema" / "morgan_schema.json"


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


def build_schema(sample_paths: List[pathlib.Path]) -> Dict[str, Any]:
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
        "plugin": "Morgan Amps Suite",
        "source_presets": presets_info,
        "modules": {
            module: sorted(params, key=lambda p: p["key"])
            for module, params in sorted(by_module.items())
        },
    }


def main() -> None:
    samples = sorted(SAMPLES_DIR.glob("*.xml"))
    if not samples:
        print(f"No samples in {SAMPLES_DIR}. Drop some .xml presets there.")
        sys.exit(1)

    schema = build_schema(samples)
    OUTPUT_PATH.write_text(json.dumps(schema, indent=2))
    print(f"Wrote {OUTPUT_PATH} ({len(schema['modules'])} modules, "
          f"{sum(len(p) for p in schema['modules'].values())} parameters)")


if __name__ == "__main__":
    main()
