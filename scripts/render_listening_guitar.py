"""Render a Morgan listening alternative in a fresh Audio Unit process.

Use before building a comparison whenever the active amp may be AC20. The
private output record binds the exact DI, settings, audio and renderer policy.
No earlier audition or judgment is changed by a new render.
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


def _amp(settings, pack):
    selected = settings.get("/selectedAmp", settings.get("selectedAmp"))
    if selected is None:
        raise ValueError("Morgan settings need an explicit selectedAmp")
    stored = pack.to_stored(pack.parameters["/selectedAmp"], selected)
    return pack.parameters["/selectedAmp"].members[stored]


def _all_writable_settings(settings, pack, supported):
    """Preserve every supplied writable control, including non-search controls."""
    applied = {}
    for name, value in settings.items():
        if not isinstance(name, str) or not name or name == "/":
            raise ValueError(f"invalid setting path {name!r}")
        path = name.lstrip("/") if name in ("selectedAmp", "/selectedAmp") else name
        spec = pack.parameters.get("/selectedAmp" if path == "selectedAmp" else path)
        if spec is None or not spec.writable or (supported is not None and path not in supported):
            raise ValueError(f"unsupported or read-only setting {name!r}")
        if path in applied and applied[path] != value:
            raise ValueError(f"conflicting spellings for setting {path!r}")
        pack.to_stored(spec, value)
        applied[path] = value
    if "selectedAmp" not in applied:
        raise ValueError("effective settings omit selectedAmp")
    return applied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--di", required=True, type=pathlib.Path)
    parser.add_argument("--settings-json", required=True, type=pathlib.Path,
                        help="full effective Morgan settings as one JSON object")
    parser.add_argument("--settings-key", help="dot-separated object path within settings JSON, e.g. settings.ac20")
    parser.add_argument("--out", required=True, type=pathlib.Path,
                        help="new private WAV under runs/")
    args = parser.parse_args()
    di_path, settings_path, out = (p.expanduser().resolve() for p in
                                   (args.di, args.settings_json, args.out))
    if out.suffix.lower() != ".wav" or ROOT / "runs" not in out.parents:
        raise ValueError("--out must be a new private WAV under this project's runs/")
    sidecar = out.with_suffix(out.suffix + ".render.json")
    if out.exists() or sidecar.exists() or out in (di_path, settings_path):
        raise ValueError("output already exists or aliases an input")
    settings = json.loads(settings_path.read_text())
    if args.settings_key:
        for key in args.settings_key.split("."):
            if not isinstance(settings, dict) or key not in settings:
                raise ValueError(f"settings key {args.settings_key!r} is missing")
            settings = settings[key]
    if not isinstance(settings, dict):
        raise ValueError("settings JSON must be an object")
    from packs.loader import load_pack
    pack = load_pack("morgan")
    amp = _amp(settings, pack)
    from analysis import io
    from match.renderer import _hash_audio
    from match.renderer_au import AudioUnitRenderer

    di = io.load(di_path).mono()
    renderer = AudioUnitRenderer("morgan", process_policy="fresh")
    try:
        metadata = renderer.metadata()
        if "process=fresh" not in metadata.quality_mode:
            raise ValueError("renderer did not report a fresh process")
        mapped = _all_writable_settings(settings, pack, renderer_paths(renderer))
        if _amp(mapped, pack) != amp:
            raise ValueError("selected amp changed during settings validation")
        result = renderer.render(di, mapped, di_sha256=_hash_audio(di))
        out.parent.mkdir(parents=True, exist_ok=True)
        _write_audio(out, result.audio, metadata.sample_rate)
        record = {"schema": "listening-fresh-render-v1", "amp_model": amp,
                  "process_policy": "fresh", "pack": "morgan",
                  "audio": {"path": str(out), "sha256": _sha(out)},
                  "di": {"path": str(di_path), "sha256": _sha(di_path),
                         "audio_sha256": _hash_audio(di)},
                  "settings": {"path": str(settings_path), "sha256": _sha(settings_path),
                               "key": args.settings_key},
                  "applied_settings": mapped,
                  "renderer": metadata.as_dict()}
        _write_text(sidecar, json.dumps(record, indent=2, allow_nan=False) + "\n")
        print(json.dumps({"audio": str(out), "record": str(sidecar),
                          "amp_model": amp, "process_policy": "fresh"}))
    finally:
        renderer.close()


if __name__ == "__main__":
    guarded(main)
