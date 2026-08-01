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
import subprocess
import sys
import tempfile

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded
from _swift import compile_swift
from packs.loader import load_pack

PROBE_SOURCE = PLUGIN_ROOT / "scripts" / "au_probe.swift"

# The plugin formats its own numbers, so the unit comes back attached and
# sometimes prefixed. Parse what it prints rather than assuming a scale.
NUMBER = re.compile(r"[-+]?[0-9]*\.?[0-9]+")


UNPARSEABLE = object()   # distinct from None, which means "no number here"


def numeric(shown: str, unit: str = None):
    """The number the plugin displayed, in the units the manifest stores.

    The plugin formats for humans, not for comparison: a pan is `50 L` / `C` /
    `50 R` rather than signed, a frequency may be in kHz, a time may be in
    seconds, and a large number may carry a thousands separator. Undo all of
    that, or the audit reports a disagreement that only exists in the display.

    Rescaling needs the parameter's own unit, not just the display: `delayTime`
    stores milliseconds and may be shown as `1.50 s`, while `reverbDecay` stores
    seconds and is shown as `1.00 s`. Converting both would break the second —
    it did, and the audit caught it.

    Returns UNPARSEABLE when there is a value but this cannot read it (`-inf
    dB`), so the caller can report "not checked" instead of a false failure.
    """
    shown = (shown or "").strip()
    if not shown:
        return None
    if shown == "C":                      # a centred pan is not "0"
        return 0.0
    if "inf" in shown.lower() or "nan" in shown.lower():
        return UNPARSEABLE

    match = NUMBER.search(shown.replace(",", ""))
    if not match:
        return None
    value = float(match.group())

    lowered = shown.lower()
    if "khz" in lowered and unit == "hz":
        value *= 1000
    elif unit == "ms" and re.search(r"\d\s*(s|sec|secs)\b", lowered):
        # Seconds shown for a parameter stored in milliseconds. delayTime tops
        # out at 1500 ms, exactly where a plugin tends to switch its display.
        value *= 1000
    # Pan: the sign is a letter, and the two plugins put it on opposite sides.
    # Morgan writes "50 L", Tone King writes "L 50". Handling only one of them
    # reported a correctly declared -50..50 pan as a disagreement.
    if lowered.endswith(" l") or re.match(r"^l\s*[\d.]", lowered):
        value = -value
    return value


def build_probe(workdir: pathlib.Path) -> pathlib.Path:
    binary = workdir / "au_probe"
    result, error = compile_swift(PROBE_SOURCE, binary)
    if result is None or result.returncode != 0:
        die(f"could not build {PROBE_SOURCE.name}:\n{error}")
    return binary


class StateNotADocument(Exception):
    """The plugin keeps its state as opaque bytes, so keys cannot be written."""


def run_probe(binary: pathlib.Path, au: dict, mode: str, *args: str):
    result = subprocess.run(
        [str(binary), au["type"], au["subtype"], au["manufacturer"], mode, *args],
        capture_output=True, text=True,
    )
    if "STATE_IS_NOT_A_DOCUMENT" in result.stderr:
        raise StateNotADocument()
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
        # Index by the exact string written. The probe echoes `wrote` verbatim,
        # so comparing floats would miss as soon as a bound needs more digits
        # than "%g" prints — and a miss here is silent.
        wrote = [f"{v:g}" for v in (below, spec.min, spec.max, above)]
        rows = run_probe(self.binary, self.au, "values", lookup, ",".join(wrote))["results"]
        kept = {}
        for row in rows:
            try:
                kept[row["wrote"]] = float(row["keptInState"])
            except (TypeError, ValueError):
                return None

        try:
            low, high = kept[wrote[0]], kept[wrote[3]]
            at_min, at_max = kept[wrote[1]], kept[wrote[2]]
        except KeyError:
            return None
        # Writing past an end must come back as that end, AND writing the end
        # itself must survive unchanged. The second half was previously written
        # and then thrown away, which left half the check unmade.
        if (low, high) != (float(spec.min), float(spec.max)):
            return ("disagrees", low, high)
        if (at_min, at_max) != (float(spec.min), float(spec.max)):
            return ("disagrees", at_min, at_max)
        return ("agrees", low, high)


def audit(pack_id: str, binary_path: pathlib.Path | None = None) -> int:
    pack = load_pack(pack_id)
    if not pack.audio_unit:
        die(
            f"pack {pack_id!r} does not say which Audio Unit it describes.\n"
            f"  Add an `audio_unit` block (type/subtype/manufacturer) to its "
            f"manifest; find the triple with `auval -a`."
        )

    with tempfile.TemporaryDirectory() as tmp:
        binary = binary_path or build_probe(pathlib.Path(tmp))
        print(f"Asking {pack.display_name} for its own parameter table…\n")
        params = {p["address"]: p for p in run_probe(binary, pack.audio_unit, "params")}
        try:
            revmap = run_probe(binary, pack.audio_unit, "revmap")
        except StateNotADocument:
            return verify_via_state(pack, params, binary)
        checker = BoundsChecker(binary, pack.audio_unit)
        return compare(pack, params, revmap, checker)


def verify_via_state(pack, params, binary) -> int:
    """Fall back to the state probe for a plugin that keeps no XML document.

    `au_probe`'s revmap edits an attribute in the plugin's state document, which
    only exists for plugins that store state as text. Tone King stores the same
    binary record format its presets use — but `format/` parses that, so the
    same experiment runs with the halves swapped and the mapping is just as
    verified. See scripts/probe_state.py.
    """
    from probe_state import (
        Probe,
        adaptive_probe,
        collect_observed_values,
        default_preset_dirs,
        preset_files,
    )
    from format.parser import parse
    from format.structured import build

    workdir = binary.parent
    probe = Probe(pack.audio_unit, workdir, binary=binary)
    state = probe.baseline_state()
    try:
        preset = build(parse(state))
    except Exception:
        return cannot_verify(pack, params)
    if not preset.parameters:
        return cannot_verify(pack, params)

    print(f"  state is a {preset.file_header!r} preset document with "
          f"{len(preset.parameters)} parameters; probing it directly.\n")

    roots = default_preset_dirs(pack.display_name)
    observed, preset_count = collect_observed_values(
        preset_files(roots), pack.file_header
    )
    print(
        f"  adaptive mapping uses valid candidates from {preset_count} installed "
        f"presets.\n"
    )
    mapping_results = adaptive_probe(
        probe, state, preset, pack, observed=observed, maximum=4
    )
    mapped = {
        row["key"]: row["address"]
        for row in mapping_results
        if row["status"] == "mapped"
    }

    verified_ranges = verified_selectors = disagrees = unchecked = 0
    for path, spec in sorted(pack.parameters.items()):
        address = mapped.get(path.lstrip("/"))
        if address is None:
            continue
        control = params[address]

        member_verdict = published_members(spec, control)
        if member_verdict is not None:
            if member_verdict[0] == "agrees":
                verified_selectors += 1
            elif member_verdict[0] == "unchecked":
                unchecked += 1
                print(f"NOT CHECKED {path}: the manifest declares selector members "
                      f"but the Audio Unit publishes no valueStrings.\n")
            else:
                disagrees += 1
                print(f"DISAGREES  {path}")
                for detail in member_verdict[1]:
                    print(f"           {detail}")
                print()

        if spec.min is None and spec.max is None:
            continue
        lo = numeric(control["minString"], spec.unit)
        hi = numeric(control["maxString"], spec.unit)
        if lo is UNPARSEABLE or hi is UNPARSEABLE:
            unchecked += 1
            continue
        if (spec.min, spec.max) == (lo, hi):
            verified_ranges += 1
        else:
            disagrees += 1
            print(f"DISAGREES  {path}")
            print(f"           manifest {spec.min} .. {spec.max}")
            print(f"           plugin   {control['minString']} .. {control['maxString']}"
                  f"   ({control['displayName']})\n")

    print(
        f"{len(mapped)} of {len(mapping_results)} numeric state keys map to "
        f"exactly one control."
    )
    print(f"{verified_ranges} declared ranges and {verified_selectors} selectors "
          f"verified, {disagrees} DISAGREE, {unchecked} unchecked.")
    report_state_coverage(params, len(mapping_results), mapped, mapping_results)
    return 1 if (disagrees or unchecked) else 0


def report_state_coverage(params, target_count, mapped, results=None) -> None:
    """Report missing state mappings without turning no movement into absence."""
    not_reached = target_count - len(mapped)
    if results:
        print(
            f"{not_reached} numeric state keys did not produce one consistent "
            f"control mapping under adaptive probing."
        )
    else:
        print(
            f"{not_reached} numeric state keys were not reached. A single nudge that "
            f"moves nothing\ndoes not prove a key has no Audio Unit control: the value "
            f"may have been a no-op\nor rejected by a discrete/quantized parameter."
        )
    mapped_controls = set(mapped.values())
    missing = [p["displayName"] for a, p in params.items() if a not in mapped_controls]
    print(
        f"{len(mapped_controls)} of {len(params)} published Audio Unit controls were "
        f"reached."
    )
    if missing:
        print("Published controls not reached: " + ", ".join(sorted(missing)) + ".")
    if results:
        from collections import Counter

        counts = Counter(row["status"] for row in results)
        detail = ", ".join(f"{name}={counts[name]}" for name in sorted(counts))
        print("Adaptive state-key outcomes: " + detail + ".")


def published_members(spec, control):
    """Compare a declared enum with the Audio Unit's indexed labels.

    Once the state experiment has mapped a preset key to this exact control,
    ``valueStrings`` is stronger evidence than writing each index: Audio Unit
    publishes the index order and labels together, including the baseline
    value that a movement-only probe would otherwise skip.
    """
    if spec.kind != "enum" or not spec.members:
        return None
    labels = control.get("valueStrings")
    if not labels:
        return ("unchecked", [])
    actual = {str(i): label for i, label in enumerate(labels)}
    wrong = []
    for index in sorted(set(spec.members) | set(actual), key=int):
        declared = spec.members.get(index)
        published = actual.get(index)
        if declared != published:
            wrong.append(
                f"{index}: manifest {declared!r}, plugin {published!r}"
            )
    return ("disagrees", wrong) if wrong else ("agrees", [])


def cannot_verify(pack, params) -> int:
    """Neither probe works: the state is neither a document nor a preset."""
    declared = sum(
        1 for s in pack.parameters.values()
        if s.min is not None or s.max is not None
    )
    print(f"CANNOT VERIFY {pack.display_name}.\n")
    print(f"  The plugin answers and publishes {len(params)} controls with real")
    print(f"  ranges, but it keeps its state as opaque bytes rather than a")
    print(f"  document, so a preset key cannot be written into it and no key can")
    print(f"  be tied to a control by experiment.\n")
    print(f"  {len(pack.parameters)} parameters in the pack, {declared} with a declared range.")
    print(f"  Matching the two lists by name is a guess; do not bulk-import ranges")
    print(f"  that way. Read `au_probe params` alongside the plugin UI and fill")
    print(f"  them in one at a time, each with a range_source saying how.\n")
    print(f"  See docs/measuring-against-the-plugin.md.")
    return 3


def check_members(checker, lookup, spec):
    """Verify a selector's declared member names against the plugin's labels.

    The script claims to re-derive ranges *and selectors*; without this it only
    ever did ranges, and every enum was counted as agreeing on the strength of
    its key mapping to a control. Returns (verdict, detail).
    """
    if spec.kind != "enum" or not spec.members:
        return None
    indices = sorted(spec.members, key=int)
    try:
        rows = run_probe(
            checker.binary, checker.au, "values", lookup, ",".join(indices)
        )["results"]
    except (StateNotADocument, KeyError, json.JSONDecodeError):
        return None

    wrong = []
    seen = 0
    for row in rows:
        moved = row.get("moved") or []
        if not moved:
            # The plugin was already on this value, so nothing moved and there
            # is no label to read. Not a failure — just no evidence.
            continue
        seen += 1
        label = (moved[0].get("label") or "").strip()
        declared = spec.members.get(row["wrote"], "")
        if label and label.lower() != declared.lower():
            wrong.append(f"{row['wrote']}: manifest {declared!r}, plugin {label!r}")
    if not seen:
        return None
    return ("disagrees", wrong) if wrong else ("agrees", seen)


def compare(pack, params, revmap, checker) -> int:
    # A preset key is only mapped when writing it moved exactly one control.
    mapped = {}
    for row in revmap:
        if len(row["moved"]) == 1:
            mapped[f"{row['element']}/{row['key']}"] = row["moved"][0]["address"]

    verified, disagrees = [], []
    nothing_declared = []      # mapped, but the manifest asserts nothing to test
    unchecked_declared = []    # asserts something, and we could NOT test it
    unchecked_bare = []        # asserts nothing and was not reached either

    for path, spec in sorted(pack.parameters.items()):
        if spec.kind not in ("metered", "enum", "rotation", "fraction"):
            continue
        lookup = f"appModel/{path.lstrip('/')}" if path.startswith("/") else path
        declares = (
            spec.min is not None or spec.max is not None
            or (spec.kind == "enum" and spec.members)
        )
        address = mapped.get(lookup)

        if address is None:
            verdict = checker.check(lookup, spec) or check_members(checker, lookup, spec)
            if verdict is None:
                (unchecked_declared if declares else unchecked_bare).append((path, spec))
            elif verdict[0] == "agrees":
                verified.append((path, spec))
            else:
                disagrees.append((path, spec, None, verdict[1], verdict[2] if len(verdict) > 2 else ""))
            continue

        if spec.kind == "enum":
            verdict = check_members(checker, lookup, spec)
            if verdict is None:
                (unchecked_declared if declares else unchecked_bare).append((path, spec))
            elif verdict[0] == "agrees":
                verified.append((path, spec))
            else:
                disagrees.append((path, spec, params[address], verdict[1], ""))
            continue

        if not declares:
            # A rotation or fraction declares no bounds, so mapping it to a
            # control proves only that the key exists. Counting it as "agrees"
            # inflated the number that gets read as the audit's result.
            nothing_declared.append((path, spec))
            continue

        control = params[address]
        lo = numeric(control["minString"], spec.unit)
        hi = numeric(control["maxString"], spec.unit)
        if lo is UNPARSEABLE or hi is UNPARSEABLE:
            unchecked_declared.append((path, spec))
        elif (spec.min, spec.max) == (lo, hi):
            verified.append((path, spec))
        else:
            disagrees.append((path, spec, control, lo, hi))

    for path, spec, control, lo, hi in disagrees:
        print(f"DISAGREES  {path}")
        if spec.kind == "enum":
            print(f"           declared members do not match the plugin's labels:")
            for line in (lo if isinstance(lo, list) else [str(lo)]):
                print(f"             {line}")
        else:
            print(f"           manifest {spec.min} .. {spec.max} {spec.unit or ''}".rstrip())
            if control is not None:
                print(f"           plugin   {control['minString']} .. {control['maxString']}"
                      f"   ({control['displayName']})")
            else:
                print(f"           plugin   {lo} .. {hi}   (clamped a written value)")
            print(f"           source   {spec.range_source}")
        print()

    if unchecked_declared:
        print(f"NOT CHECKED, BUT ASSERTS SOMETHING — {len(unchecked_declared)}:\n")
        for path, spec in unchecked_declared:
            what = (f"{spec.min} .. {spec.max}" if spec.min is not None or spec.max is not None
                    else f"{len(spec.members or {})} members")
            print(f"           {path}  ({spec.kind}, {what})")
        print("\n           These declare a fact the plugin was not asked about, so"
              "\n           the audit proves nothing for them. That is a failure, not"
              "\n           a clean bill: it is exactly how three wrong ranges survived"
              "\n           a full pass. Probe each by hand with the `values` mode.\n")

    print(f"{len(verified)} verified, {len(disagrees)} DISAGREE, "
          f"{len(unchecked_declared)} unchecked, "
          f"{len(nothing_declared)} declare nothing to check.")
    if nothing_declared and not (disagrees or unchecked_declared):
        print(f"\n{len(nothing_declared)} parameters map to a control but declare no range or "
              f"members,\nso nothing about them was tested. That is expected for knobs stored "
              f"0-1.")
    if disagrees:
        print("\nA disagreement means every value written through that parameter is "
              "silently clamped\nor rejected by the plugin. Fix the manifest, and "
              "set `range_source` to say how.")
    return 1 if (disagrees or unchecked_declared) else 0


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Check a pack's declared facts against the installed plugin."
    )
    ap.add_argument("--pack", default="morgan", help="pack id (default: morgan)")
    ap.add_argument("--binary", type=pathlib.Path,
                    help="use an already-built au_probe helper")
    args = ap.parse_args()
    if args.binary is not None and not args.binary.is_file():
        die(f"--binary does not exist: {args.binary}")
    raise SystemExit(audit(args.pack, args.binary))


if __name__ == "__main__":
    guarded(main)
