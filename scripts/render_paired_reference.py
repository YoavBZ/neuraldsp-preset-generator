#!/usr/bin/env python3
"""Render a known preset through an exact DI and record pairing provenance.

The output is validation evidence, not a searched result: ``--reference`` for a
later ``match_preset.py --reference-mode paired_di`` run and ``--probe-di`` must
name the WAV and DI recorded by the sidecar this command writes.

Needs the analysis and match extras:  pip install -e '.[analysis,match]'
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shlex
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded, renderer_paths


def _file_sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _output_path(value: pathlib.Path) -> pathlib.Path:
    path = value.expanduser().resolve()
    if path.suffix.lower() != ".wav":
        die("--out must end in .wav so the untouched float render is preserved")
    return path


def _protect_sources(sources, outputs, force: bool) -> None:
    resolved_sources = {path.resolve(): label for label, path in sources.items()}
    seen = {}
    for label, path in outputs.items():
        resolved = path.resolve()
        if resolved in resolved_sources:
            die(f"{label} output {path} aliases the {resolved_sources[resolved]} input")
        if resolved in seen:
            die(f"{label} output {path} aliases the {seen[resolved]} output")
        seen[resolved] = label
        if path.is_dir():
            die(f"{label} output {path} is a directory")
        if (path.exists() or path.is_symlink()) and not force:
            die(f"{path} already exists; choose another --out or pass --force")


def _settings(space, values, supported):
    from match.space import _get

    result = {}
    for dimension in space.active(values):
        value = _get(values, (dimension.module, dimension.key))
        if value is None:
            continue
        if supported is not None and dimension.path not in supported:
            continue
        result[dimension.path] = value
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", required=True, type=pathlib.Path,
                        help="known target preset to render")
    parser.add_argument("--probe-di", required=True, type=pathlib.Path,
                        help="exact dry performance to reamp")
    parser.add_argument("--out", required=True, type=pathlib.Path,
                        help="reference WAV to write")
    parser.add_argument("--provenance", type=pathlib.Path,
                        help="default: OUT.paired.json")
    parser.add_argument("--pack", required=True)
    parser.add_argument("--amp", help="optional signal path override")
    parser.add_argument("--renderer", choices=("synthetic", "swift"),
                        default="swift")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    preset = args.preset.expanduser().resolve()
    probe_path = args.probe_di.expanduser().resolve()
    if not preset.is_file():
        die(f"--preset does not exist at {preset}")
    if not probe_path.is_file():
        die(f"--probe-di does not exist at {probe_path}")
    output = _output_path(args.out)
    provenance = (args.provenance.expanduser().resolve()
                  if args.provenance is not None else
                  pathlib.Path(str(output) + ".paired.json"))
    _protect_sources(
        {"preset": preset, "probe DI": probe_path},
        {"reference": output, "provenance": provenance},
        args.force,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    provenance.parent.mkdir(parents=True, exist_ok=True)

    from analysis import io
    from match import invert
    from match import space as space_module
    from match.renderer import _hash_audio, canonical_settings
    from scripts.build_rab_audition import _write_audio, _write_text
    from scripts.match_preset import _renderer, _seed_from_template

    signal_path = None
    if args.amp is not None:
        signal_path = invert.resolve_signal_path(args.pack, args.amp)
    space = space_module.build(args.pack, amp=signal_path)
    values, _ = _seed_from_template(preset, space, args.pack)
    if signal_path is not None:
        values = invert.apply_to(
            values, invert.signal_path_selection(args.pack, signal_path), space,
        )

    renderer = _renderer(args.renderer, args.pack)
    try:
        metadata = renderer.metadata()
        probe = io.load(str(probe_path), target_rate=metadata.sample_rate)
        # match_preset.py canonicalises every supplied DI to channel-averaged mono.
        # Render and hash that exact signal here too, or a stereo source creates a
        # reference the later run cannot prove came from its own probe.
        probe_samples = probe.mono()
        probe_audio_sha = _hash_audio(probe_samples)
        settings = _settings(space, values, renderer_paths(renderer))
        if not settings:
            die("the preset has no settings this renderer can drive")
        rendered = renderer.render(
            probe_samples, settings, di_sha256=probe_audio_sha,
        )
        if rendered.silent:
            die("the known preset rendered silence; no paired reference was written")
    finally:
        close = getattr(renderer, "close", None)
        if close is not None:
            close()

    _write_audio(output, rendered.audio, metadata.sample_rate)
    document = {
        "schema": "paired-di-reference-1",
        "pack": args.pack,
        "signal_path": signal_path,
        "preset": {"path": str(preset), "sha256": _file_sha(preset)},
        "probe_di": {
            "path": str(probe_path),
            "sha256": _file_sha(probe_path),
            "audio_sha256": probe_audio_sha,
            "source_channels": probe.source_channels,
            "canonical_channels": 1,
        },
        "reference": {
            "path": str(output),
            "sha256": _file_sha(output),
            "audio_sha256": _hash_audio(rendered.audio),
            "sample_rate": metadata.sample_rate,
        },
        "settings": json.loads(canonical_settings(values)),
        "render_settings": json.loads(canonical_settings(settings)),
        "renderer": metadata.as_dict(),
        "invocation": [sys.executable, str(pathlib.Path(__file__).resolve()),
                       *sys.argv[1:]],
    }
    _write_text(provenance, json.dumps(document, indent=2) + "\n")
    print(f"wrote paired reference: {output}")
    print(f"pairing provenance: {provenance}")
    print("use these exact files with match_preset.py:")
    print(f"  --reference {shlex.quote(str(output))} --reference-mode paired_di \\")
    print(f"  --probe-di {shlex.quote(str(probe_path))} \\")
    print(f"  --paired-provenance {shlex.quote(str(provenance))}")


if __name__ == "__main__":
    guarded(main)
