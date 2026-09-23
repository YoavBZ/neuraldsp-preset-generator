"""Render a Morgan or Tone King listening alternative in a fresh AU process.

Use before building a comparison whenever the active amp may be AC20. The
private output record binds the exact DI, settings, audio and renderer policy.
No earlier audition or judgment is changed by a new render.

Supply either a full effective settings JSON object or a plugin preset.
Morgan's preset path reads every declared writable control, not just search
dimensions. Tone King's preset is loaded as the exact state blob, preserving
even absent-value and opaque records; settings JSON is supported only for Morgan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _cli import guarded, renderer_paths
from build_rab_audition import _write_audio, _write_text


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _selector(pack):
    name = "selectedAmp" if pack.pack_id == "morgan" else "ampType"
    return pack.parameters["/" + name]


def _amp(settings, pack):
    selector = _selector(pack)
    selected = settings.get(selector.path, settings.get("/" + selector.path))
    if selected is None:
        raise ValueError(f"{pack.display_name} settings need an explicit {selector.path}")
    stored = pack.to_stored(selector, selected)
    return selector.members[stored]


def _all_writable_settings(settings, pack, supported, *, warnings=None):
    """Preserve every supplied writable control, including non-search controls."""
    applied = {}
    for name, value in settings.items():
        if not isinstance(name, str) or not name or name == "/":
            raise ValueError(f"invalid setting path {name!r}")
        path = name[1:] if name.startswith("/") else name
        if not path or path.startswith("/"):
            raise ValueError(f"invalid setting path {name!r}")
        spec = pack.parameters.get("/" + path if "/" not in path else path)
        if spec is None or not spec.writable or (supported is not None and path not in supported):
            raise ValueError(f"unsupported or read-only setting {name!r}")
        if path in applied and applied[path] != value:
            raise ValueError(f"conflicting spellings for setting {path!r}")
        pack.to_stored(spec, value, warnings=warnings)
        applied[path] = value
    selector = _selector(pack).path
    if selector not in applied:
        raise ValueError(f"effective settings omit {selector}")
    return applied


def _settings_from_preset(path, pack, supported, *, warnings=None):
    """Read a complete Morgan preset before applying knob edits."""
    if pack.pack_id != "morgan":
        raise ValueError("only Morgan presets are converted to knob edits")
    from format.parser import parse_file
    from format.structured import build
    from format.translate import from_binary
    from packs.loader import detect_pack

    preset = build(parse_file(str(path)))
    detected = detect_pack(preset.file_header)
    if detected is None or detected.pack_id != pack.pack_id:
        raise ValueError(f"{path} is not a {pack.display_name} preset")
    values = {}
    for parameter in preset.parameters:
        spec = pack.get(parameter.module_path, parameter.key)
        name = f"{parameter.module_path}/{parameter.key}" if parameter.module_path else parameter.key
        if spec is None:
            raise ValueError(f"preset contains an undeclared control: {name}")
        if not spec.writable:
            continue
        if supported is not None and name not in supported:
            raise ValueError(f"preset control cannot be rendered: {name}")
        value = from_binary(spec.kind, parameter.value, spec.unit)
        if name in values and values[name] != value:
            raise ValueError(f"preset states conflicting values for {name}")
        values[name] = value
    selector = _selector(pack).path
    if selector not in values:
        raise ValueError(f"{pack.display_name} preset omits {selector}")
    required = {spec.path for spec in pack.parameters.values() if spec.writable}
    missing = sorted(required - values.keys())
    if missing:
        names = ", ".join(missing[:5])
        suffix = f" (and {len(missing) - 5} more)" if len(missing) > 5 else ""
        raise ValueError(f"preset omits {len(missing)} writable control(s): {names}{suffix}; "
                         "rendering it would substitute plugin defaults")
    # Opaque enums read from this exact preset are preserved as stored. Their
    # musical meaning is still unknown; keep the warning in the render record.
    return _all_writable_settings(values, pack, supported,
                                  warnings=[] if warnings is None else warnings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", choices=("morgan", "toneking"), default="morgan")
    parser.add_argument("--di", required=True, type=pathlib.Path)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--settings-json", type=pathlib.Path,
                             help="full effective Morgan settings as one JSON object")
    input_group.add_argument("--preset", type=pathlib.Path,
                             help="Morgan: apply all writable controls; Tone King: replay the exact preset state")
    parser.add_argument("--settings-key", help="dot-separated object path within settings JSON, e.g. settings.ac20")
    parser.add_argument("--out", required=True, type=pathlib.Path,
                        help="new private WAV under runs/")
    args = parser.parse_args()
    di_path = args.di.expanduser().resolve()
    source_path = (args.settings_json or args.preset).expanduser().resolve()
    out = args.out.expanduser().resolve()
    if args.settings_key and args.preset:
        raise ValueError("--settings-key applies only to --settings-json")
    if args.pack == "toneking" and args.settings_json:
        raise ValueError("Tone King needs --preset to preserve its opaque state")
    if out.suffix.lower() != ".wav" or ROOT / "runs" not in out.parents:
        raise ValueError("--out must be a new private WAV under this project's runs/")
    sidecar = out.with_suffix(out.suffix + ".render.json")
    if out.exists() or sidecar.exists() or out in (di_path, source_path):
        raise ValueError("output already exists or aliases an input")
    if not source_path.is_file():
        raise ValueError(f"input settings or preset does not exist: {source_path}")
    settings = None
    if args.settings_json:
        settings = json.loads(source_path.read_text())
        if args.settings_key:
            for key in args.settings_key.split("."):
                if not isinstance(settings, dict) or key not in settings:
                    raise ValueError(f"settings key {args.settings_key!r} is missing")
                settings = settings[key]
        if not isinstance(settings, dict):
            raise ValueError("settings JSON must be an object")
    from packs.loader import load_pack
    pack = load_pack(args.pack)
    from analysis import io
    from match.renderer import _hash_audio
    from match.renderer_au import AudioUnitRenderer
    from match.renderer_preset import ToneKingPresetRenderer

    exact_state = args.pack == "toneking" and args.preset is not None
    source_sha = _sha(source_path)
    di_sha = _sha(di_path)
    source_warnings = []
    if exact_state:
        from match.renderer_preset import toneking_channel
        amp = toneking_channel(source_path.read_bytes())
        mapped = {}  # The untouched blob is applied; no knobs are edited.
    else:
        mapped = (_settings_from_preset(source_path, pack, None,
                                        warnings=source_warnings) if args.preset
                  else _all_writable_settings(settings, pack, None))
        amp = _amp(mapped, pack)
    di = io.load(di_path).mono()
    renderer = (ToneKingPresetRenderer(source_path, process_policy="fresh") if exact_state
                else AudioUnitRenderer(args.pack, process_policy="fresh"))
    try:
        metadata = renderer.metadata()
        if "process=fresh" not in metadata.quality_mode:
            raise ValueError("renderer did not report a fresh process")
        supported = renderer_paths(renderer)
        if supported is not None and not exact_state:
            unsupported = sorted(set(mapped) - supported)
            if unsupported:
                raise ValueError(f"preset control cannot be rendered: {unsupported[0]}")
        render_settings = {} if exact_state else mapped
        result = renderer.render(di, render_settings, di_sha256=_hash_audio(di))
        if result.silent:
            raise ValueError("the preset rendered silence; no listening alternative was written")
        if _sha(source_path) != source_sha or _sha(di_path) != di_sha:
            raise ValueError("the preset/settings or DI changed during rendering")
        out.parent.mkdir(parents=True, exist_ok=True)
        _write_audio(out, result.audio, metadata.sample_rate)
        record = {"schema": "listening-fresh-render-v1", "amp_model": amp,
                  "process_policy": "fresh", "pack": args.pack,
                  "audio": {"path": str(out), "sha256": _sha(out)},
                  "di": {"path": str(di_path), "sha256": di_sha,
                         "audio_sha256": _hash_audio(di)},
                  "settings": ({"path": str(source_path), "sha256": source_sha,
                                "key": args.settings_key} if args.settings_json else None),
                  "preset": ({"path": str(source_path), "sha256": source_sha}
                             if args.preset else None),
                  "state_source": "exact_preset_blob" if exact_state else "plugin_base_with_edits",
                  "applied_settings": mapped,
                  "source_warnings": source_warnings,
                  "renderer": metadata.as_dict()}
        _write_text(sidecar, json.dumps(record, indent=2, allow_nan=False) + "\n")
        print(json.dumps({"audio": str(out), "record": str(sidecar),
                          "amp_model": amp, "process_policy": "fresh"}))
    finally:
        renderer.close()


if __name__ == "__main__":
    guarded(main)
