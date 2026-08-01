"""
Re-derive every declared range and selector from the running plugin.

    python scripts/audit_manifest.py --pack morgan

This is NOT part of the test suite and cannot be: it needs macOS, a licensed
copy of the plugin, and the plugin installed as an Audio Unit. Run it
deliberately — after a plugin update, or before trusting a range you did not
measure yourself.

It reports three buckets, and the third is the reason this exists:

  agrees       the manifest matches what the plugin publishes
  DISAGREES    the manifest is wrong, and every value written is wrong with it
  NOT MAPPED   the probe never moved this control, so nothing was checked

The third bucket is not "fine". Three `*EQHpf` maximums were wrong by a factor
of forty and sat in the manifest for a full audit cycle because they already
held their minimum value in the plugin's default state: writing a low probe
value changed nothing, no control moved, and they dropped out of the comparison
silently instead of being flagged. A parameter missing from the map is a
parameter nobody checked. Probe those by hand:

    /tmp/au_probe aumf NMAS NDSP values pr12EQ/pr12EQHpf 5,20,100,500,900

See docs/measuring-against-the-plugin.md.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded
from packs.loader import load_pack

PROBE_SOURCE = PLUGIN_ROOT / "scripts" / "au_probe.swift"

# The plugin formats its own numbers, so the unit comes back attached and
# sometimes prefixed. Parse what it prints rather than assuming a scale.
NUMBER = re.compile(r"[-+]?[0-9]*\.?[0-9]+")


def numeric(shown: str):
    """The number the plugin displayed, in the units the manifest stores.

    The plugin formats for humans, not for comparison: a pan is `50 L` / `C` /
    `50 R` rather than a signed number, and a frequency may be in kHz. Undo both
    or the audit reports a disagreement that only exists in the display.
    """
    shown = (shown or "").strip()
    if shown == "C":
        return 0.0
    match = NUMBER.search(shown)
    if not match:
        return None
    value = float(match.group())
    if "kHz" in shown:
        value *= 1000
    if shown.endswith(" L"):
        value = -value
    return value


def build_probe(workdir: pathlib.Path) -> pathlib.Path:
    if shutil.which("swiftc") is None:
        die(
            "swiftc not found. The audit compiles scripts/au_probe.swift to talk "
            "to the plugin.\n  Install the Xcode command line tools: xcode-select --install"
        )
    binary = workdir / "au_probe"
    result = subprocess.run(
        ["swiftc", "-swift-version", "5", "-O", str(PROBE_SOURCE), "-o", str(binary)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        die(f"could not build {PROBE_SOURCE.name}:\n{result.stderr}")
    return binary


def run_probe(binary: pathlib.Path, au: dict, mode: str, *args: str):
    result = subprocess.run(
        [str(binary), au["type"], au["subtype"], au["manufacturer"], mode, *args],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        die(
            f"the plugin would not answer ({mode}): {result.stderr.strip()}\n"
            f"  An unlicensed or uninstalled Neural DSP plugin fails to "
            f"instantiate. Check it opens standalone first."
        )
    return json.loads(result.stdout)


class BoundsChecker:
    """Ask the plugin about a parameter the perturbation map never reached.

    `revmap` only maps a key whose probe value actually moves a control, so a
    key already holding that value silently drops out. Writing past each end of
    the declared range and reading back what the plugin kept works regardless,
    because clamping is visible even when nothing moved.
    """

    def __init__(self, binary: pathlib.Path, au: dict):
        self.binary = binary
        self.au = au

    def check(self, lookup: str, spec):
        if spec.kind != "metered" or spec.min is None or spec.max is None:
            return None
        below, above = spec.min - abs(spec.min or 1) - 1, spec.max + abs(spec.max or 1) + 1
        rows = run_probe(
            self.binary, self.au, "values", lookup,
            f"{below:g},{spec.min:g},{spec.max:g},{above:g}",
        )["results"]
        kept = {}
        for row in rows:
            try:
                kept[float(row["wrote"])] = float(row["keptInState"])
            except (TypeError, ValueError):
                return None
        # Writing past an end must come back as that end, and writing the end
        # itself must survive. Either failing means the declared range is wrong.
        low = kept.get(float(below))
        high = kept.get(float(above))
        if low is None or high is None:
            return None
        if (low, high) == (float(spec.min), float(spec.max)):
            return ("agrees", low, high)
        return ("disagrees", low, high)


def audit(pack_id: str) -> int:
    pack = load_pack(pack_id)
    if not pack.audio_unit:
        die(
            f"pack {pack_id!r} does not say which Audio Unit it describes.\n"
            f"  Add an `audio_unit` block (type/subtype/manufacturer) to its "
            f"manifest; find the triple with `auval -a`."
        )

    with tempfile.TemporaryDirectory() as tmp:
        binary = build_probe(pathlib.Path(tmp))
        print(f"Asking {pack.display_name} for its own parameter table…\n")
        params = {p["address"]: p for p in run_probe(binary, pack.audio_unit, "params")}
        revmap = run_probe(binary, pack.audio_unit, "revmap")
        checker = BoundsChecker(binary, pack.audio_unit)
        return compare(pack, params, revmap, checker)


def compare(pack, params, revmap, checker) -> int:

    # A preset key is only mapped when writing it moved exactly one control.
    mapped = {}
    for row in revmap:
        if len(row["moved"]) == 1:
            mapped[f"{row['element']}/{row['key']}"] = row["moved"][0]["address"]

    agrees, disagrees, unmapped = [], [], []
    for path, spec in sorted(pack.parameters.items()):
        if spec.kind not in ("metered", "enum", "rotation", "fraction"):
            continue
        # The manifest addresses the document root as a bare "/key"; the plugin
        # calls that element appModel.
        lookup = f"appModel/{path.lstrip('/')}" if path.startswith("/") else path
        address = mapped.get(lookup)
        if address is None:
            # Do not just report the hole — this is the hole the wrong *EQHpf
            # ranges hid in. Ask the plugin directly instead, by writing past
            # each declared end and reading back what it kept.
            verdict = checker.check(lookup, spec)
            if verdict is None:
                unmapped.append((path, spec))
            elif verdict[0] == "agrees":
                agrees.append((path, spec, None))
            else:
                disagrees.append((path, spec, None, verdict[1], verdict[2]))
            continue

        control = params[address]
        if spec.kind != "metered" or spec.min is None and spec.max is None:
            agrees.append((path, spec, control))
            continue
        lo, hi = numeric(control["minString"]), numeric(control["maxString"])
        if (spec.min, spec.max) == (lo, hi):
            agrees.append((path, spec, control))
        else:
            disagrees.append((path, spec, control, lo, hi))

    for path, spec, control, lo, hi in disagrees:
        print(f"DISAGREES  {path}")
        print(f"           manifest {spec.min} .. {spec.max} {spec.unit or ''}".rstrip())
        if control is not None:
            print(f"           plugin   {control['minString']} .. {control['maxString']}"
                  f"   ({control['displayName']})")
        else:
            print(f"           plugin   {lo} .. {hi}   (clamped a written value)")
        print(f"           source   {spec.range_source}\n")

    if unmapped:
        print(f"NOT CHECKED — neither the map nor a write probe reached these "
              f"{len(unmapped)}:\n")
        for path, spec in unmapped:
            declared = (f"{spec.min} .. {spec.max}"
                        if spec.min is not None or spec.max is not None else "no range")
            print(f"           {path}  ({spec.kind}, {declared})")
        print("\n           These have no declared range to test against, so "
              "there is nothing to\n"
              "           compare. That is expected for selectors whose members "
              "are unknown.\n")

    print(f"{len(agrees)} agree, {len(disagrees)} DISAGREE, {len(unmapped)} not checked.")
    if disagrees:
        print("\nA disagreement means every value written through that parameter is "
              "silently clamped\nor rejected by the plugin. Fix the manifest, and "
              "set `range_source` to say how.")
    return 1 if disagrees else 0


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Check a pack's declared facts against the installed plugin."
    )
    ap.add_argument("--pack", default="morgan", help="pack id (default: morgan)")
    args = ap.parse_args()
    raise SystemExit(audit(args.pack))


if __name__ == "__main__":
    guarded(main)
