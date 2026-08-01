"""
Map preset keys to plugin controls for a plugin whose state is a preset.

    python scripts/probe_state.py --pack toneking --map
    python scripts/probe_state.py --pack toneking --values ampReverb 0,0.5,1

`scripts/au_probe.swift` can already do this for a plugin that keeps its state
as an XML document — it edits one attribute, hands the document back, and reads
which control moved. Tone King does not: its state is the same binary record
format its presets use, so that probe reported CANNOT VERIFY and its whole pack
shipped with no declared ranges.

But `format/` parses that format, and the state round-trips through it byte for
byte. So the same experiment works with the halves swapped: Swift does the Audio
Unit I/O (`dumpstate` / `setstate`) and Python does the format work, reusing the
tokenizer that 681 real presets are tested against rather than growing a second
copy of it in Swift.

The experiment is the one that matters: write a value into the preset document,
hand it to the plugin, and see which control moves. It tests the path a
generated preset actually takes.

Needs macOS, the plugin licensed and installed, and `swiftc`. Not a CI test.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded
from format.parser import parse
from format.structured import build, set_parameter
from format.writer import write
from packs.loader import load_pack

PROBE_SOURCE = PLUGIN_ROOT / "scripts" / "au_probe.swift"


class Probe:
    """One plugin instance's worth of state read/write, via the Swift helper."""

    def __init__(
        self, au: dict, workdir: pathlib.Path, binary: pathlib.Path | None = None
    ):
        self.binary = binary or workdir / "au_probe"
        if binary is None:
            if shutil.which("swiftc") is None:
                die("swiftc not found. Install the Xcode command line tools.")
            built = subprocess.run(
                ["swiftc", "-swift-version", "5", "-O", str(PROBE_SOURCE),
                 "-o", str(self.binary)],
                capture_output=True, text=True,
            )
            if built.returncode != 0:
                die(f"could not build au_probe.swift:\n{built.stderr}")
        self.au = au
        self.workdir = workdir

    def _run(self, mode: str, *args: str):
        result = subprocess.run(
            [str(self.binary), self.au["type"], self.au["subtype"],
             self.au["manufacturer"], mode, *args],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            die(f"the plugin would not answer ({mode}): {result.stderr.strip()}")
        return result

    def baseline_state(self) -> bytes:
        blob = self.workdir / "state.bin"
        self._run("dumpstate", str(blob))
        return blob.read_bytes()

    def apply_many(self, blobs: list) -> list:
        """Hand the plugin each blob in turn; return one {address: row} per blob.

        One process for the whole batch. Each instantiation costs a second or
        two, so a per-blob process would turn a mapping run into twenty minutes
        of mostly plugin startup.
        """
        listing = self.workdir / "blobs.txt"
        paths = []
        for i, blob in enumerate(blobs):
            path = self.workdir / f"b{i}.bin"
            path.write_bytes(blob)
            paths.append(str(path))
        listing.write_text("\n".join(paths))
        batches = json.loads(self._run("setstate", str(listing)).stdout)
        return [{r["address"]: r for r in rows} for rows in batches]

    def apply(self, blob: bytes) -> dict:
        return self.apply_many([blob])[0]


def edited(state: bytes, module: str, key: str, value: str) -> bytes:
    """The state blob with one parameter changed, everything else byte-identical."""
    preset = build(parse(state))
    set_parameter(preset, module, key, value)
    return write(preset.tokens)


def probe_values(probe: Probe, state: bytes, module: str, key: str, values: list):
    """Write each value and report which control moved, and to what."""
    # Interleave the baseline between writes so each comparison is against a
    # freshly reset plugin, and send the whole sequence as one batch.
    blobs = [state]
    for raw in values:
        blobs += [edited(state, module, key, raw), state]
    results = probe.apply_many(blobs)

    out = []
    for i, raw in enumerate(values):
        before, after = results[i * 2], results[i * 2 + 1]
        moved = [
            {"address": a, "name": r["name"], "label": r["label"],
             "from": before[a]["label"]}
            for a, r in after.items()
            if abs(r["value"] - before[a]["value"]) > 1e-9
        ]
        out.append({"wrote": raw, "moved": moved})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Map preset keys to controls for a record-format plugin."
    )
    ap.add_argument("--pack", required=True)
    ap.add_argument("--map", action="store_true",
                    help="map every key in the state to the control it moves")
    ap.add_argument("--values", nargs=2, metavar=("KEY", "V1,V2,..."),
                    help="write these values to one key and report what moved")
    ap.add_argument("--limit", type=int, help="stop after N keys (for a quick look)")
    args = ap.parse_args()

    pack = load_pack(args.pack)
    if not pack.audio_unit:
        die(f"pack {args.pack!r} does not say which Audio Unit it describes.")

    with tempfile.TemporaryDirectory() as tmp:
        probe = Probe(pack.audio_unit, pathlib.Path(tmp))
        state = probe.baseline_state()
        preset = build(parse(state))
        print(f"state parses as {preset.file_header!r}: "
              f"{len(preset.parameters)} parameters\n", file=sys.stderr)

        if args.values:
            key, raw = args.values
            module, _, bare = key.rpartition("/")
            rows = probe_values(probe, state, module, bare, raw.split(","))
            json.dump(rows, sys.stdout, indent=1)
            return

        # Perturb each parameter in turn. A value is nudged rather than set to a
        # constant: writing the value a key already holds moves nothing and the
        # key would drop out of the map unnoticed — the exact hole that let three
        # wrong ranges survive a full audit on the other plugin.
        params = preset.parameters[:args.limit] if args.limit else preset.parameters
        targets, blobs = [], [state]
        for param in params:
            try:
                current = float(param.value)
            except ValueError:
                continue
            target = f"{current + 1 if current <= 0.5 else current - 1:g}"
            targets.append((param, target))
            blobs += [edited(state, param.module_path, param.key, target), state]

        print(f"probing {len(targets)} parameters in one instantiation…",
              file=sys.stderr)
        results = probe.apply_many(blobs)

        mapping = []
        for i, (param, target) in enumerate(targets):
            before, after = results[i * 2], results[i * 2 + 1]
            moved = [
                {"address": a, "name": r["name"], "label": r["label"]}
                for a, r in after.items()
                if abs(r["value"] - before[a]["value"]) > 1e-9
            ]
            mapping.append({
                "key": f"{param.module_path}/{param.key}" if param.module_path else param.key,
                "wrote": target, "was": param.value, "moved": moved,
            })
        json.dump(mapping, sys.stdout, indent=1)


if __name__ == "__main__":
    guarded(main)
