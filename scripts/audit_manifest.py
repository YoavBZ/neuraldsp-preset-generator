"""
Re-derive every declared range and selector from the running plugin.

    python scripts/audit_manifest.py --pack morgan

This is NOT part of the test suite and cannot be: it needs macOS, a licensed
copy of the plugin, and the plugin installed as an Audio Unit. Run it
deliberately — after a plugin update, or before trusting a range you did not
measure yourself.

It reports four buckets, and the last two are the reason this exists:

  agrees       the manifest matches what the plugin publishes
  DISAGREES    the manifest is wrong, and every value written is wrong with it
  PARTLY       a selector's members agreed as far as they were asked, and the
               rest were never asked because the plugin already held them
  NOT MAPPED   the probe never moved this control, so nothing was checked

The last two are not "fine", and they are the same defect seen twice. Three
`*EQHpf` maximums were wrong by a factor of forty and sat in the manifest for a
full audit cycle because they already held their minimum value in the plugin's
default state: writing a low probe value changed nothing, no control moved, and
they dropped out of the comparison silently instead of being flagged. A
selector's baseline member goes unread for exactly the same reason, which is
why it is now counted apart from the ones that answered. A parameter missing
from the map is a parameter nobody checked, and a selector member that never
moved is a member nobody read. Probe those by hand:

    /tmp/au_probe aumf NMAS NDSP values pr12EQ/pr12EQHpf 5,20,100,500,900

See docs/measuring-against-the-plugin.md.
"""

from __future__ import annotations

import argparse
import collections
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
from format.parser import parse
from format.structured import build
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
        # Unreadable, not absent. Several real controls in both plugins publish
        # empty min/max strings; treating that as "no number" made it compare
        # unequal to any declared range and report a failure nothing could fix.
        return UNPARSEABLE
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
    # Pan is displayed as a POSITION OUT OF 50 with the side as a letter, and
    # that is not necessarily the unit the file stores. Morgan stores -50..50 and
    # Tone King stores -1..1, both displaying `L 50`/`50 L` at the same end. So
    # the display cannot establish the range for these, and pretending it can is
    # how a Tone King pan came to be declared 50x too large.
    #
    # This function previously converted the letter to a sign, which made the
    # audit agree with that wrong range — the checker was adjusted until it
    # matched the manifest instead of the manifest being questioned. Refuse
    # instead; the caller falls back to writing a value and reading it back,
    # which measures the stored unit rather than inferring it.
    if re.search(r"(^|\s)[lr]\s*[\d.]|[\d.]\s*[lr]$", lowered):
        return UNPARSEABLE
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
        #
        # Compared at float32 like probe_bounds, and for the same reason: this
        # measures the same physical quantity through a 32-bit parameter, so a
        # bound written as 1.0 can come back as 0.99999994. Exact `!=` was
        # latent here only because Morgan round-trips its bounds as decimal text
        # — the first pack whose state keeps binary doubles would have seen a
        # disagreement no manifest edit could fix.
        want = (float(spec.min), float(spec.max))
        for measured in ((low, high), (at_min, at_max)):
            if not all(_same_to_float32(a, b) for a, b in zip(measured, want)):
                return ("disagrees", measured[0], measured[1])
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
            return verify_via_state(pack, params, binary, pathlib.Path(tmp))
        checker = BoundsChecker(binary, pack.audio_unit)
        return compare(pack, params, revmap, checker)


def probe_bounds(probe, state, path, spec):
    """Measure a range by writing past both ends and reading back what stuck.

    Used where the plugin's own display cannot be compared to the stored value —
    a pan shows a position out of 50 whichever scale it is stored on, so the
    display establishes nothing. Writing past each end and reading the state the
    plugin kept measures the stored unit directly.

    Returns ("agrees"|"disagrees", low, high), or None if the write told us
    nothing.
    """
    from probe_state import edited

    if spec.min is None or spec.max is None:
        # Half a declared range cannot be probed from both ends. Reported as
        # unchecked rather than crashing on None arithmetic.
        return None
    key = path.lstrip("/")
    module, _, bare = key.rpartition("/")
    below = spec.min - abs(spec.min or 1) - 1
    above = spec.max + abs(spec.max or 1) + 1
    try:
        blobs = [edited(state, module, bare, f"{below:g}"),
                 edited(state, module, bare, f"{above:g}")]
    except (KeyError, ValueError):
        return None

    _, states = probe.apply_many_with_states(blobs)
    try:
        kept = [float(build(parse(st)).by_path[(module, bare)].value) for st in states]
    except (KeyError, ValueError):
        return None

    # Compare at the precision the plugin actually has. Its parameters are
    # float32, so a value written as 1.0 comes back as 0.99999994 — one ULP
    # below, not a different limit. Demanding double-exact equality would report
    # that as a disagreement forever, and no manifest edit could fix it.
    # The tolerance is far tighter than any real range error, which differs by
    # orders of magnitude rather than by an ULP.
    if all(_same_to_float32(k, want)
           for k, want in zip(kept, (float(spec.min), float(spec.max)))):
        return ("agrees", kept[0], kept[1])
    return ("disagrees", kept[0], kept[1])


def _same_to_float32(a: float, b: float) -> bool:
    import struct as _struct
    to32 = lambda x: _struct.unpack("<f", _struct.pack("<f", x))[0]
    return to32(a) == to32(b) or abs(a - b) <= 1e-6 * max(1.0, abs(b))


def verify_via_state(pack, params, binary, scratch) -> int:
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

    # Scratch goes in our own temp dir, never beside a caller-supplied binary:
    # apply_many_with_states rmtree's a subdirectory of the workdir, and a run
    # writes thousands of blob files into it.
    workdir = scratch
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
    nothing_declared = []
    unmapped_declared = []
    for path, spec in sorted(pack.parameters.items()):
        address = mapped.get(path.lstrip("/"))
        if address is None:
            # Members are not an enum-only assertion: a switch that names its
            # two labels asserts them just as hard, and must not fall through
            # into silence when no probe reached it.
            declares = (spec.min is not None or spec.max is not None
                        or bool(spec.members))
            if declares:
                # It asserts something and nothing tested it. Counting this as
                # silence is exactly how three wrong ranges survived a full pass.
                unmapped_declared.append((path, spec))
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
            if member_verdict is None:
                # Mapped, but the manifest asserts nothing about it, so nothing
                # was tested. The Morgan path keeps and prints this bucket; not
                # doing so here made the summary read cleaner while proving
                # strictly less — 53 of 94 parameters silently untested behind
                # a headline of "0 unchecked".
                nothing_declared.append((path, spec))
            continue
        lo = numeric(control["minString"], spec.unit)
        hi = numeric(control["maxString"], spec.unit)
        if lo is UNPARSEABLE or hi is UNPARSEABLE:
            # The display cannot be compared to what the file stores — a pan
            # shows a position out of 50 whichever scale it is stored on. Ask
            # the plugin instead: write past each end and read back what it
            # kept, which measures the stored unit rather than inferring it.
            verdict = probe_bounds(probe, state, path, spec)
            if verdict is None:
                unchecked += 1
            elif verdict[0] == "agrees":
                verified_ranges += 1
            else:
                disagrees += 1
                print(f"DISAGREES  {path}")
                print(f"           manifest {spec.min} .. {spec.max}")
                print(f"           plugin kept {verdict[1]} .. {verdict[2]} "
                      f"when written past both ends   ({control['displayName']})\n")
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
    if unmapped_declared:
        print(f"NOT CHECKED, BUT ASSERTS SOMETHING — {len(unmapped_declared)}:\n")
        for path, spec in unmapped_declared:
            what = (f"{spec.min} .. {spec.max}" if spec.min is not None
                    else f"{len(spec.members or {})} members")
            print(f"           {path}  ({spec.kind}, {what})")
        print("\n           These declare a fact no probe reached, so the audit "
              "proves nothing\n           for them. That is a failure, not a clean "
              "bill.\n")
    if nothing_declared:
        # Named, not just counted. A list of 53 was a statistic; a list short
        # enough to read is a to-do list, which is what this bucket should be.
        kinds = collections.Counter(spec.kind for _, spec in nothing_declared)
        count = len(nothing_declared)
        subject = ("1 mapped parameter declares" if count == 1
                   else f"{count} mapped parameters declare")
        named = ", ".join(path for path, _ in nothing_declared[:6])
        print(f"{subject} no range and no members, so nothing about\n"
              f"{'it' if count == 1 else 'them'} was tested "
              f"({', '.join(f'{n} {k}' for k, n in kinds.most_common())}): "
              f"{named}{'…' if count > 6 else ''}.\n"
              f"'verified' above counts only what the manifest actually asserts.")
    report_state_coverage(params, len(mapping_results), mapped, mapping_results)
    return 1 if (disagrees or unchecked or unmapped_declared) else 0


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

    A `switch` counts as a selector here. It is a two-index one whose labels the
    plugin publishes in the same array (`Inactive`/`Active`, `Off`/`On`), and
    declaring them is the only thing that gives the audit anything to check
    about a switch at all — 21 of them were previously "declares nothing".
    """
    if spec.kind not in ("enum", "switch") or not spec.members:
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
    its key mapping to a control.

    Returns one of:

      ("agrees", seen)            every declared member produced a label
      ("partial", seen, total)    only `seen` of them did — see below
      ("disagrees", wrong)        a label contradicts the manifest
      None                        no member produced a label at all
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
    if wrong:
        return ("disagrees", wrong)
    if seen < len(indices):
        # Evidence for `seen` members is not evidence for all of them. The
        # member that goes unseen is normally the plugin's *current* index —
        # writing it moves nothing, so there is no label to read — which is the
        # same "already at that value" hole that hid three wrong `*EQHpf`
        # maximums through a full audit. Not a failure (partial evidence is
        # still evidence), but it must not be counted as a completed check.
        return ("partial", seen, len(indices))
    return ("agrees", seen)


def compare(pack, params, revmap, checker) -> int:
    # A preset key is only mapped when writing it moved exactly one control.
    mapped = {}
    for row in revmap:
        if len(row["moved"]) == 1:
            mapped[f"{row['element']}/{row['key']}"] = row["moved"][0]["address"]

    verified, disagrees = [], []
    partly_verified = []       # checked, agreed, but not every member was seen
    nothing_declared = []      # mapped, but the manifest asserts nothing to test
    unchecked_declared = []    # asserts something, and we could NOT test it
    unchecked_bare = []        # asserts nothing and was not reached either

    def record(path, spec, control, verdict) -> None:
        """File one selector or range verdict into the bucket it belongs in.

        "partial" gets its own bucket rather than joining `verified`: a selector
        whose baseline index never moved was checked on the members that did
        move and on no others, and reporting that as a completed check is how
        an unexamined value passes for an examined one.
        """
        if verdict[0] == "agrees":
            verified.append((path, spec))
        elif verdict[0] == "partial":
            partly_verified.append((path, spec, verdict[1], verdict[2]))
        else:
            disagrees.append((path, spec, control, verdict[1],
                              verdict[2] if len(verdict) > 2 else ""))

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
            else:
                record(path, spec, None, verdict)
            continue

        if spec.kind == "enum":
            verdict = check_members(checker, lookup, spec)
            if verdict is None:
                (unchecked_declared if declares else unchecked_bare).append((path, spec))
            else:
                record(path, spec, params[address], verdict)
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
            # The display cannot be compared to what the file stores. Ask the
            # plugin instead: write past each end and read back what it kept.
            # That measures the stored unit rather than inferring it.
            verdict = checker.check(lookup, spec)
            if verdict is None:
                unchecked_declared.append((path, spec))
            else:
                record(path, spec, None, verdict)
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

    if partly_verified:
        print(f"PARTLY VERIFIED — {len(partly_verified)}:\n")
        for path, spec, seen, total in partly_verified:
            print(f"           {path}  ({seen} of {total} declared members "
                  f"produced a label)")
        print("\n           Every member that answered agreed with the manifest, but "
              "the rest\n           were not asked: writing the value a control "
              "already holds moves\n           nothing, so there is no label to read. "
              "That is evidence about\n           the members seen and about no "
              "others. Probe the remainder from a\n           different starting "
              "value with the `values` mode.\n")

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

    # The headline counts everything that was checked and did not disagree, then
    # splits it: a partial check is not a lesser kind of clean, it is a check
    # that did not finish, and burying it inside one number is what let a
    # selector with an unread member read as fully re-derived.
    agreed = len(verified) + len(partly_verified)
    complete = (f"{agreed} verified" if not partly_verified else
                f"{agreed} verified ({len(verified)} completely, "
                f"{len(partly_verified)} on partial evidence)")
    print(f"{complete}, {len(disagrees)} DISAGREE, "
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
