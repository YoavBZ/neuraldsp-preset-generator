"""Render through an Audio Unit with a JUCE host instead of a bare CLI helper.

Two questions this answers, both from docs/tone-matching-plan.md:

1. How fast is an in-process host, against `scripts/au_render_server.swift`?
   A tone-matching search renders hundreds of candidates, so throughput picks
   the backend.
2. Does Tone King Imperial MKII produce audio here? `scripts/au_render.swift`
   and `scripts/au_silence_check.swift` both get exact zeros from it, cause
   unconfirmed, authorization suspected — see
   docs/measuring-against-the-plugin.md. `pedalboard` hosts plugins the way a
   DAW does rather than instantiating them from a headless CLI, so it is the
   cheapest available test of that explanation.

    python scripts/spike_pedalboard.py --plugin "Morgan Amps Suite" --parameters
    python scripts/spike_pedalboard.py --plugin "Tone King Imperial MKII" --bench 10

The excitation is the same seeded white noise `au_render.swift` generates, bit
for bit, so a render from either backend is comparable with the other.

Requires macOS, an installed and licensed plugin, and the `host` extra.
Nothing here is a measurement of the plugin's controls: it is a backend spike.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

COMPONENTS = pathlib.Path("/Library/Audio/Plug-Ins/Components")
SAMPLE_RATE = 48000.0
BUFFER_SIZE = 512


def _require_host():
    """Import the extra, or explain how to get it rather than tracebacking."""
    try:
        import numpy
        import pedalboard
    except ImportError:
        die(
            "this spike needs the host extra.\n"
            "  pip install -e '.[host]'"
        )
    return pedalboard, numpy


def excitation(numpy, seconds: float, amplitude: float):
    """The seeded white noise from scripts/au_render.swift, sample for sample.

    Same xorshift, same seed, same scaling. Two backends fed byte-identical
    input differ only by what they do to it, which is the only reason a
    cross-backend comparison means anything.
    """
    total = int(SAMPLE_RATE * seconds)
    mask = (1 << 64) - 1
    seed = 0x5EED1234ABCD0001
    out = numpy.empty(total, dtype=numpy.float32)
    for i in range(total):
        seed ^= (seed << 13) & mask
        seed ^= seed >> 7
        seed ^= (seed << 17) & mask
        out[i] = (float(seed >> 11) / float(1 << 53)) * 2.0 - 1.0
    out *= amplitude
    return numpy.stack([out, out])


def state_encoding(blob: bytes) -> str:
    """What kind of state document these bytes are: 'record', 'xml' or 'unknown'.

    The two plugins in this repository keep state in different encodings, and
    §11 of docs/tone-matching-plan.md is the reason this function exists: Morgan's
    live `jucePluginState` is an XML document while its *preset files* are the
    `morgan\\0` record format, and nothing converts between them. Handing a
    Morgan preset to `raw_state` therefore cannot work, and the failure to catch
    that is silent — the host takes the bytes and the plugin ignores them.

    Tone King keeps the same record format in both places, which is why the
    round-trip is meaningful there and not on Morgan.

    The parser is deliberately lenient (it reads any leading printable run as a
    header), so parsing alone proves nothing. A record document is one that
    yields parameters *and* a header a pack claims.
    """
    if not blob:
        return "unknown"
    if blob.lstrip()[:1] == b"<":
        return "xml"
    try:
        from format.parser import parse
        from format.structured import build
        from packs.loader import detect_pack

        preset = build(parse(blob))
    except Exception:
        return "unknown"
    if preset.parameters and detect_pack(preset.file_header) is not None:
        return "record"
    return "unknown"


def state_round_trip_diff(written: bytes, read_back: bytes):
    """Parameters the plugin did not keep, comparing what went in with what came out.

    Applying state and getting no error is not evidence that it was applied —
    that is the whole lesson of the pan range this repository got wrong. Reading
    the state back and comparing values is.

    Returns (checked, differences), where differences is a list of
    (module, key, written, read_back) for every parameter that moved.
    """
    from format.parser import parse
    from format.structured import build

    before = build(parse(written))
    after = build(parse(read_back))
    differences = []
    checked = 0
    for path, parameter in before.by_path.items():
        other = after.by_path.get(path)
        if other is None:
            differences.append((path[0], path[1], parameter.value, None))
            continue
        checked += 1
        if other.value != parameter.value:
            differences.append((path[0], path[1], parameter.value, other.value))
    return checked, differences


def find_plugin(name: str) -> str:
    """Accept a component name, a bare plugin name, or a full path."""
    candidate = pathlib.Path(name)
    if candidate.exists():
        return str(candidate)
    for suffix in (name, f"{name}.component"):
        path = COMPONENTS / suffix
        if path.exists():
            return str(path)
    installed = sorted(p.stem for p in COMPONENTS.glob("*.component"))
    die(
        f"no Audio Unit named {name!r} in {COMPONENTS}.\n"
        f"  Installed: {', '.join(installed) or 'none'}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Spike an Audio Unit through pedalboard's JUCE host.",
        epilog="A backend spike, not a measurement of the plugin.",
    )
    ap.add_argument("--plugin", required=True, help="component name or path")
    ap.add_argument("--parameters", action="store_true", help="list published parameters")
    ap.add_argument("--bench", type=int, default=0, metavar="N", help="time N renders")
    ap.add_argument("--out", type=pathlib.Path, help="write the render to a wav")
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--amplitude", type=float, default=0.25)
    ap.add_argument("--state", type=pathlib.Path,
                    help="apply this file as raw plugin state, then read it back "
                         "and report which parameters the plugin kept")
    ap.add_argument("--save-state", type=pathlib.Path, help="write the plugin's raw state out")
    args = ap.parse_args()

    pedalboard, numpy = _require_host()
    path = find_plugin(args.plugin)

    loaded = time.perf_counter()
    plugin = pedalboard.load_plugin(path)
    load_s = time.perf_counter() - loaded
    print(f"loaded {plugin.name!r} in {load_s * 1000:.0f} ms")

    raw = getattr(plugin, "raw_state", None)
    print(f"published parameters: {len(plugin.parameters)}   raw state: "
          f"{len(raw) if raw is not None else 'unavailable'} bytes")

    if args.state:
        blob = args.state.read_bytes()
        if not blob:
            die(f"{args.state} is empty")

        # Refuse the encoding mismatch instead of letting it pass silently. A
        # preset in the record format is not a state document for a plugin whose
        # state is XML, but assigning it raises nothing and changes nothing --
        # the render would then be of the default preset, reported as if it were
        # the generated one.
        incoming, current = state_encoding(blob), state_encoding(raw or b"")
        print(f"state encoding: {args.state.name} is {incoming}, "
              f"the plugin's own state is {current}")
        if current != "unknown" and incoming != "unknown" and incoming != current:
            die(
                f"{args.state} is a {incoming} document and this plugin keeps its "
                f"state as {current}. Nothing converts between them, so applying "
                f"it would be ignored rather than refused.\n"
                f"  A preset file is a state blob only for a record-state plugin "
                f"(Tone King). For Morgan, drive the render with parameter edits.\n"
                f"  See docs/measuring-against-the-plugin.md, "
                f"'Morgan's live state and its preset files are different encodings'."
            )
        try:
            plugin.raw_state = blob
        except Exception as e:  # the host rejects a state the plugin will not take
            die(f"the plugin refused {args.state} as raw state: {e}")
        print(f"applied {len(blob)} bytes of state from {args.state}")

        # And then check it took. This is the round trip the plan calls for: it
        # is what proves the backend can be driven by a generated parameter
        # vector rather than only rendering defaults.
        after = getattr(plugin, "raw_state", None)
        if incoming == "record" and state_encoding(after or b"") == "record":
            checked, differences = state_round_trip_diff(blob, after)
            print(f"round trip: {checked} parameters read back, "
                  f"{len(differences)} changed")
            for module, key, wanted, got in differences[:20]:
                where = f"{module}/{key}" if module else key
                print(f"  {where}: wrote {wanted!r}, plugin kept {got!r}")
            if len(differences) > 20:
                print(f"  ... and {len(differences) - 20} more")
        elif after is None:
            print("round trip: the host exposes no state to read back")
        else:
            print("round trip: not checked -- the state read back is "
                  f"{state_encoding(after or b'')}, not a parsable record")

    if args.save_state:
        # An empty file here would look like a successful capture and fail much
        # later, somewhere that has nothing to do with this script.
        if not raw:
            die(
                "this host exposes no raw state for the plugin, so there is "
                f"nothing to write to {args.save_state}."
            )
        args.save_state.write_bytes(raw)
        print(f"wrote {len(raw)} bytes to {args.save_state}")

    if args.parameters:
        for key, parameter in plugin.parameters.items():
            print(f"  {key:34} {parameter}")

    audio = excitation(numpy, args.seconds, args.amplitude)
    started = time.perf_counter()
    rendered = plugin(audio, SAMPLE_RATE, buffer_size=BUFFER_SIZE, reset=True)
    first_s = time.perf_counter() - started
    peak = float(numpy.abs(rendered).max())
    print(f"render: {first_s * 1000:.0f} ms for {args.seconds:.1f} s of audio, peak {peak:.7f}")
    if peak == 0.0:
        # The repository's rule: a silent render is not evidence about a control.
        print("  SILENT — this host gets no audio out of this plugin either")

    if args.out:
        with pedalboard.io.AudioFile(
            str(args.out), "w", SAMPLE_RATE, rendered.shape[0]
        ) as f:
            f.write(rendered)
        print(f"wrote {args.out}")

    if args.bench:
        # Reproducibility matters as much as speed: a search caches renders by
        # parameters, and a backend that answers differently each time cannot be
        # cached and cannot resolve small control changes.
        peaks, times, renders = [], [], []
        for _ in range(args.bench):
            started = time.perf_counter()
            out = plugin(audio, SAMPLE_RATE, buffer_size=BUFFER_SIZE, reset=True)
            times.append(time.perf_counter() - started)
            peaks.append(float(numpy.abs(out).max()))
            renders.append(out)
        mean = sum(times) / len(times)
        print(f"bench: {args.bench} renders, {mean * 1000:.0f} ms each, "
              f"{1 / mean:.2f} renders/s, peak spread {max(peaks) - min(peaks):.2e}")
        identical = all(numpy.array_equal(renders[0], r) for r in renders[1:])
        print(f"  every render bit-identical: {identical}")
        if not identical:
            reference = renders[0]
            worst = max(
                20 * numpy.log10(
                    numpy.sqrt(((r - reference) ** 2).mean())
                    / numpy.sqrt((reference**2).mean()) + 1e-30
                )
                for r in renders[1:]
            )
            print(f"  worst repeat differs by {worst:+.1f} dB relative to the signal")


if __name__ == "__main__":
    guarded(main)
