"""Map record-format preset keys to published Audio Unit controls.

The probe writes several valid values for each key, reloads the plugin state,
and compares both the Audio Unit parameter tree and the state returned by the
plugin. That distinguishes a consistent key/control mapping from an invalid
write, a quantized no-op, an accepted state-only key, or an ambiguous mapping.

    python3 scripts/probe_state.py --pack toneking --map
    python3 scripts/probe_state.py --pack toneking --values ampReverb 0,0.5,1

Candidate values come from installed presets when available. Presets supply
inputs only; the evidence is always the running plugin's response. No preset
content or source path is emitted or committed.

Requires macOS, an installed and licensed plugin, and ``swiftc``.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import pathlib
import shutil
import subprocess
import sys
import tempfile

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded
from _swift import compile_swift
from format.parser import parse
from format.structured import build, set_parameter
from format.writer import write
from packs.loader import load_pack

PROBE_SOURCE = PLUGIN_ROOT / "scripts" / "au_probe.swift"
EPSILON = 1e-9


class Probe:
    """One plugin instance's state read/write bridge through the Swift helper."""

    def __init__(
        self, au: dict, workdir: pathlib.Path, binary: pathlib.Path | None = None
    ):
        self.binary = binary or workdir / "au_probe"
        if binary is None:
            built, error = compile_swift(PROBE_SOURCE, self.binary)
            if built is None or built.returncode != 0:
                die(f"could not build au_probe.swift:\n{error}")
        self.au = au
        self.workdir = workdir

    def _run(self, mode: str, *args: str):
        result = subprocess.run(
            [
                str(self.binary),
                self.au["type"],
                self.au["subtype"],
                self.au["manufacturer"],
                mode,
                *args,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            die(f"the plugin would not answer ({mode}): {result.stderr.strip()}")
        return result

    def baseline_state(self) -> bytes:
        blob = self.workdir / "state.bin"
        self._run("dumpstate", str(blob))
        return blob.read_bytes()

    def _write_batch(self, blobs: list[bytes]) -> pathlib.Path:
        listing = self.workdir / "blobs.txt"
        paths = []
        for i, blob in enumerate(blobs):
            path = self.workdir / f"b{i}.bin"
            path.write_bytes(blob)
            paths.append(str(path))
        listing.write_text("\n".join(paths))
        return listing

    def apply_many(self, blobs: list[bytes]) -> list[dict]:
        """Apply a batch and return one ``{address: control}`` map per blob."""
        listing = self._write_batch(blobs)
        batches = json.loads(self._run("setstate", str(listing)).stdout)
        return [{r["address"]: r for r in rows} for rows in batches]

    def apply_many_with_states(self, blobs: list[bytes]):
        """Apply a batch and also capture the state retained after each write."""
        listing = self._write_batch(blobs)
        capture = self.workdir / "applied-states"
        if capture.exists():
            shutil.rmtree(capture)
        batches = json.loads(
            self._run("setstate", str(listing), str(capture)).stdout
        )
        controls = [{r["address"]: r for r in rows} for rows in batches]
        states = [(capture / f"{i}.bin").read_bytes() for i in range(len(blobs))]
        return controls, states

    def apply(self, blob: bytes) -> dict:
        return self.apply_many([blob])[0]


def parameter_path(module: str, key: str) -> str:
    return f"{module}/{key}" if module else key


def edited(state: bytes, module: str, key: str, value: str) -> bytes:
    """Return state with exactly one existing parameter value replaced."""
    preset = build(parse(state))
    set_parameter(preset, module, key, value)
    return write(preset.tokens)


def _number(value) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _same_number(left, right) -> bool:
    a, b = _number(left), _number(right)
    return a is not None and b is not None and abs(a - b) <= EPSILON


def _numeric_text(value) -> str | None:
    number = _number(value)
    if number is None:
        return None
    if number == int(number) and abs(number) < 2**53:
        return str(int(number))
    return repr(number)


def default_preset_dirs(display_name: str) -> list[pathlib.Path]:
    """Conventional Neural DSP preset roots for an installed plugin."""
    relative = pathlib.Path("Audio") / "Presets" / "Neural DSP" / display_name
    roots = [pathlib.Path("/Library") / relative, pathlib.Path.home() / "Library" / relative]
    return [root for root in roots if root.is_dir()]


def preset_files(roots: list[pathlib.Path]) -> list[pathlib.Path]:
    files = []
    for root in roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(root.rglob("*.xml"))
    return sorted(set(files))


def collect_observed_values(
    files: list[pathlib.Path], file_header: str
) -> tuple[dict[str, list[str]], int]:
    """Collect numeric candidate values without retaining preset identities."""
    observed: dict[str, list[str]] = {}
    accepted = 0
    for path in files:
        try:
            preset = build(parse(path.read_bytes()))
        except (OSError, UnicodeError, ValueError):
            continue
        if preset.file_header != file_header:
            continue
        accepted += 1
        for param in preset.parameters:
            if _number(param.value) is None:
                continue
            key = parameter_path(param.module_path, param.key)
            values = observed.setdefault(key, [])
            if not any(_same_number(param.value, prior) for prior in values):
                values.append(param.value)
    return observed, accepted


def candidate_values(param, spec, observed: list[str], maximum: int = 4) -> list[str]:
    """Choose diverse valid-looking values, preferring values from real presets."""
    current = _number(param.value)
    if current is None or maximum <= 0:
        return []

    pool: list[str] = []

    def add(value) -> None:
        text = _numeric_text(value)
        if text is None or _same_number(text, current):
            return
        if not any(_same_number(text, prior) for prior in pool):
            pool.append(text)

    # Extremes exercise switches and selectors well; the remaining observed
    # values are ordered by distance from baseline to avoid quantized no-ops.
    seen = sorted({_number(value) for value in observed if _number(value) is not None})
    if seen:
        add(seen[0])
        add(seen[-1])
        for value in sorted(seen, key=lambda item: abs(item - current), reverse=True):
            add(value)

    if spec is not None:
        if spec.kind == "switch":
            for value in (0, 1):
                add(value)
        elif spec.kind == "enum" and spec.members:
            for value in sorted(spec.members, key=int):
                add(value)
        elif spec.kind == "metered" and spec.min is not None and spec.max is not None:
            for value in (spec.min, spec.max, (spec.min + spec.max) / 2):
                add(value)
        elif spec.kind in ("rotation", "fraction"):
            for value in (0, 1, 0.5):
                add(value)

    # Guessed kinds may be wrong, so retain a small kind-agnostic fallback.
    for value in (0, 1, 0.5, -1, current + 1, current - 1):
        add(value)
    return pool[:maximum]


def moved_controls(before: dict, after: dict) -> list[dict]:
    moved = []
    for address, row in after.items():
        prior = before.get(address)
        if prior is None or abs(row["value"] - prior["value"]) <= EPSILON:
            continue
        moved.append(
            {
                "address": address,
                "name": row["name"],
                "from": prior["value"],
                "to": row["value"],
                "fromLabel": prior["label"],
                "toLabel": row["label"],
            }
        )
    return moved


def retained_value(state: bytes, module: str, key: str) -> str | None:
    try:
        return build(parse(state)).by_path[(module, key)].value
    except (KeyError, UnicodeError, ValueError):
        return None


def classify_attempt(was: str, wrote: str, kept: str | None, moved: list[dict]) -> str:
    """Classify one write from both returned state and published controls."""
    if kept is None:
        return "unsupported"
    if len(moved) > 1:
        return "ambiguous"
    if len(moved) == 1:
        return "mapped"
    if _same_number(kept, was):
        return "no_op" if _same_number(wrote, was) else "rejected"
    return "state_only"


def summarize_attempts(attempts: list[dict]) -> dict:
    """Combine attempts without turning lack of movement into a mapping claim."""
    addresses = {
        moved["address"]
        for attempt in attempts
        for moved in attempt["moved"]
    }
    if any(len(attempt["moved"]) > 1 for attempt in attempts) or len(addresses) > 1:
        return {"status": "ambiguous"}
    if len(addresses) == 1:
        address = next(iter(addresses))
        control = next(
            moved
            for attempt in attempts
            for moved in attempt["moved"]
            if moved["address"] == address
        )
        return {"status": "mapped", "address": address, "control": control["name"]}

    outcomes = {attempt["outcome"] for attempt in attempts}
    for status in ("state_only", "rejected", "no_op", "unsupported"):
        if outcomes == {status} or (status == "state_only" and status in outcomes):
            return {"status": status}
    return {"status": "inconclusive"}


def adaptive_probe(
    probe: Probe,
    state: bytes,
    preset,
    pack,
    observed: dict[str, list[str]] | None = None,
    maximum: int = 4,
    limit: int | None = None,
) -> list[dict]:
    """Probe each numeric key with several candidates in one plugin instance."""
    observed = observed or {}
    params = [param for param in preset.parameters if _number(param.value) is not None]
    if limit is not None:
        params = params[:limit]

    blobs = [state]
    scheduled: list[tuple[object, str, int, int]] = []
    rows: list[dict] = []
    for param in params:
        path = parameter_path(param.module_path, param.key)
        spec = pack.get(param.module_path, param.key)
        candidates = candidate_values(param, spec, observed.get(path, []), maximum)
        row = {"key": path, "was": param.value, "candidates": candidates, "attempts": []}
        rows.append(row)
        for candidate in candidates:
            before_index = len(blobs) - 1
            blobs.append(edited(state, param.module_path, param.key, candidate))
            after_index = len(blobs) - 1
            blobs.append(state)
            scheduled.append((param, candidate, before_index, after_index))

    controls, returned_states = probe.apply_many_with_states(blobs)
    by_key = {row["key"]: row for row in rows}
    for param, candidate, before_index, after_index in scheduled:
        path = parameter_path(param.module_path, param.key)
        was = retained_value(returned_states[before_index], param.module_path, param.key)
        kept = retained_value(returned_states[after_index], param.module_path, param.key)
        moved = moved_controls(controls[before_index], controls[after_index])
        outcome = classify_attempt(was or param.value, candidate, kept, moved)
        by_key[path]["attempts"].append(
            {"wrote": candidate, "kept": kept, "outcome": outcome, "moved": moved}
        )

    for row in rows:
        if not row["attempts"]:
            row.update(status="unsupported")
        else:
            row.update(summarize_attempts(row["attempts"]))
    return rows


def probe_values(probe: Probe, state: bytes, module: str, key: str, values: list[str]):
    """Write selected values and report control movement plus retained state."""
    blobs = [state]
    indices = []
    for raw in values:
        before_index = len(blobs) - 1
        blobs += [edited(state, module, key, raw), state]
        indices.append((raw, before_index, before_index + 1))
    controls, states = probe.apply_many_with_states(blobs)

    out = []
    for raw, before_index, after_index in indices:
        was = retained_value(states[before_index], module, key)
        kept = retained_value(states[after_index], module, key)
        moved = moved_controls(controls[before_index], controls[after_index])
        out.append(
            {
                "wrote": raw,
                "kept": kept,
                "outcome": classify_attempt(was or "", raw, kept, moved),
                "moved": moved,
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Map preset keys to controls for a record-format plugin."
    )
    ap.add_argument("--pack", required=True)
    actions = ap.add_mutually_exclusive_group(required=True)
    actions.add_argument("--map", action="store_true", help="adaptively map every numeric key")
    actions.add_argument("--values", nargs=2, metavar=("KEY", "V1,V2,..."))
    ap.add_argument("--preset-dir", action="append", type=pathlib.Path,
                    help="preset file or directory supplying valid candidate values")
    ap.add_argument("--attempts", type=int, default=4,
                    help="maximum values to try per key (default: 4)")
    ap.add_argument("--limit", type=int, help="stop after N numeric keys")
    ap.add_argument("--binary", type=pathlib.Path,
                    help="use an already-built au_probe helper")
    args = ap.parse_args()

    pack = load_pack(args.pack)
    if not pack.audio_unit:
        die(f"pack {args.pack!r} does not say which Audio Unit it describes.")
    if args.attempts < 1:
        die("--attempts must be at least 1.")
    if args.binary is not None and not args.binary.is_file():
        die(f"--binary does not exist: {args.binary}")

    with tempfile.TemporaryDirectory() as tmp:
        probe = Probe(pack.audio_unit, pathlib.Path(tmp), binary=args.binary)
        state = probe.baseline_state()
        preset = build(parse(state))
        print(
            f"state parses as {preset.file_header!r}: "
            f"{len(preset.parameters)} parameters\n",
            file=sys.stderr,
        )

        if args.values:
            key, raw = args.values
            module, _, bare = key.rpartition("/")
            json.dump(probe_values(probe, state, module, bare, raw.split(",")),
                      sys.stdout, indent=1)
            sys.stdout.write("\n")
            return

        roots = args.preset_dir or default_preset_dirs(pack.display_name)
        observed, count = collect_observed_values(preset_files(roots), pack.file_header)
        print(
            f"using candidate values from {count} compatible presets; "
            f"trying up to {args.attempts} values per key…",
            file=sys.stderr,
        )
        results = adaptive_probe(
            probe,
            state,
            preset,
            pack,
            observed=observed,
            maximum=args.attempts,
            limit=args.limit,
        )
        summary = dict(sorted(Counter(row["status"] for row in results).items()))
        json.dump(
            {"preset_count": count, "attempts_per_key": args.attempts,
             "summary": summary, "results": results},
            sys.stdout,
            indent=1,
        )
        sys.stdout.write("\n")


if __name__ == "__main__":
    guarded(main)
