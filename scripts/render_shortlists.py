#!/usr/bin/env python3
"""Render each development part's own shortlist of presets through the part's DI.

    python scripts/render_shortlists.py --manifest shortlists.json \\
        --out-dir ~/ndsp-presets/runs/shortlists/renders

`docs/song-only-shortlist-plan.md`. The manifest maps a part to its presets,
`{"parts": {part: {label: preset path}}}`; the presets may be on any Morgan amp.
Per part, one fresh plugin process, reused within the part as the panels were
(`render_preset_panel.py`): a discarded warm-up, the shipped template with R, every
listed preset with R, and the template with R again; then every listed preset again,
in reverse order (`<label>.repeat.wav`), so a render that depends on the one before it
shows. R is the panels' rule set: time effects, gate, doubler and transpose off, and
the spring reverb of the preset's own amp off. Float WAV, named by label, with an index
binding each render to its preset's hash and recording its peak. Held-out parts are
refused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded

TEMPLATE = "template+R"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=pathlib.Path, required=True)
    ap.add_argument("--out-dir", type=pathlib.Path, required=True)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    return ap


def _sha(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def amp_of(path: pathlib.Path, pack, renderer) -> str:
    """The Morgan amp a preset selects, as render_preset_panel's amp id."""
    from format.parser import parse
    from format.structured import build
    from render_preset_panel import AMP_NAMES

    stored = build(parse(path.read_bytes())).by_path.get(("", "selectedAmp"))
    if stored is None:
        raise ValueError(f"{path} selects no amp")
    spec = pack.parameters["/selectedAmp"]
    for amp, name in AMP_NAMES.items():
        if int(float(renderer._stored(pack, spec, name))) == int(float(stored.value)):
            return amp
    raise ValueError(f"{path} selects an amp outside {sorted(AMP_NAMES)}")


def work(job):
    """Render one worker's parts, each in its own fresh plugin process."""
    import numpy as np
    import soundfile as sf

    from analysis import io
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack
    from render_preset_panel import SUBTYPE, TEMPLATES, preset_edits

    crops, out_dir, parts = job
    pack = load_pack("morgan")

    class ShortlistRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edits = self.commands[settings["label"]]
            command = {"edits": edits}
            if select is not None:
                command["selectAmp"] = select
            return command

    rows = []
    for part, presets in parts:
        renderer = ShortlistRenderer("morgan", process_policy="reuse")
        try:
            listed = {TEMPLATE: PLUGIN_ROOT / TEMPLATES["pr12"]}
            listed.update({label: pathlib.Path(p).expanduser() for label, p in presets.items()})
            amps = {label: amp_of(path, pack, renderer) for label, path in listed.items()}
            ShortlistRenderer.commands = {
                label: preset_edits(path, pack, renderer, amps[label], True)
                for label, path in listed.items()}
            di = io.load(crops / part / "di.wav").mono().astype(np.float32)
            renderer.render(di, {"label": TEMPLATE})                 # warm-up, discarded
            out = out_dir / part
            out.mkdir(parents=True, exist_ok=True)
            first = None
            for label, path in listed.items():
                audio = np.asarray(renderer.render(di, {"label": label}).audio)
                file = out / f"{label}.wav"
                sf.write(file, audio, 48000, subtype=SUBTYPE)
                rows.append({"part": part, "label": label, "amp": amps[label],
                             "preset": str(path), "preset_sha256": _sha(path),
                             "file": str(file), "sha256": _sha(file),
                             "peak": float(np.abs(audio).max())})
                if first is None:
                    first = audio
            again = np.asarray(renderer.render(di, {"label": TEMPLATE}).audio)
            drift = float(20 * np.log10((np.std(again) + 1e-12) / (np.std(first) + 1e-12)))
            rows.append({"canary": part, "label": TEMPLATE, "rms_drift_db": round(drift, 3),
                         "identical": bool(np.array_equal(again, first))})
            for label in reversed([x for x in listed if x != TEMPLATE]):
                audio = np.asarray(renderer.render(di, {"label": label}).audio)
                file = out / f"{label}.repeat.wav"
                sf.write(file, audio, 48000, subtype=SUBTYPE)
                rows.append({"part": part, "label": label, "repeat": True,
                             "file": str(file), "sha256": _sha(file)})
        finally:
            renderer.close()
        print(f"{part}: {len(listed)} renders", flush=True)
    return rows


def main() -> None:
    args = build_parser().parse_args()
    from analysis import require

    require("rendering shortlists")
    from benchmark_recordings import CATALOG, development_parts

    manifest = json.loads(args.manifest.expanduser().read_text())["parts"]
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    development = {"-".join(x.replace("/", "_").replace(" ", "_") for x in p)
                   for p in development_parts(catalog)}
    outside = sorted(set(manifest) - development)
    if outside:
        die(f"not development parts: {', '.join(outside)}")
    clash = sorted(p for p, presets in manifest.items() if TEMPLATE in presets)
    if clash:
        die(f"{TEMPLATE!r} is reserved for the template, listed for {', '.join(clash)}")
    crops = args.crops_dir.expanduser()
    missing = [p for p in manifest if not (crops / p / "di.wav").exists()]
    if missing:
        die(f"no DI crop for {', '.join(missing)}")
    out_dir = args.out_dir.expanduser()
    if out_dir.exists() and any(out_dir.iterdir()):
        die(f"{out_dir} is not empty; renders are never mixed across runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = sorted(manifest.items())
    jobs = [(crops, out_dir, parts[i::args.workers]) for i in range(args.workers)]
    with ProcessPoolExecutor(args.workers) as pool:
        rows = [row for result in pool.map(work, jobs) for row in result]
    index = {"manifest": str(args.manifest), "manifest_sha256": _sha(args.manifest.expanduser()),
             "crops_dir": str(crops), "template": TEMPLATE, "rows": rows}
    (out_dir / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    canaries = [r for r in rows if "canary" in r]
    print(f"{len(rows) - len(canaries)} renders with repeats; canaries "
          f"{[(r['canary'], r['rms_drift_db'], r['identical']) for r in canaries]}")


if __name__ == "__main__":
    guarded(main)
