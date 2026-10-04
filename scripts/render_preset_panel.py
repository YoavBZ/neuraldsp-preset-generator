#!/usr/bin/env python3
"""Render a panel of whole presets through every development part's own DI.

    python scripts/render_preset_panel.py --amp sw50r --out-dir ~/ndsp-presets/runs/kill/sw50r

The kill tests of `docs/supervised-model-plan.md` (§0) need one crossed set of
renders: every factory preset of one Morgan amp (from the plugin's own preset
folder, never `User/`) and the shipped template, each with the rule set R applied,
through the 10-second DI crop of each set-2 development part. R switches off what
the model will set by rule rather than estimate — delay, rack reverb, tremolo,
doubler, the gate, the amp's spring reverb and transpose — so no arm wins by
switching off time effects a dry amp track does not have, and none plays in another
key. The template is also rendered as
shipped, for reference.

A preset is sent as attribute edits of every writable parameter it stores (plus
`selectAmp`), so the plugin renders the preset itself, not the search space's view
of it. Each worker reuses one plugin process, renders a discarded warm-up per part,
and checks at the end that its first render repeats; outputs are float WAV
named by preset (integer PCM would clip hot presets), with an index of what was
rendered. Held-out parts are refused.
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

FACTORY = pathlib.Path("/Library/Audio/Presets/Neural DSP/Morgan Amps Suite")
TEMPLATES = {"sw50r": "samples/SW50R_Atlas_Topology.xml",
             "pr12": "samples/Example_Clean_PR12.xml",
             "ac20": "samples/AC20_Atlas_Topology.xml"}
AMP_NAMES = {"sw50r": "SW50R", "pr12": "PR12", "ac20": "AC20"}
SPRING = {"sw50r": "sw50rAmp/sw50rReverb", "pr12": "pr12Amp/pr12Reverb"}
# The FX section itself stays on: every effect in it is off under R, and switching
# the section off and then on again in one reused instance left it rendering
# silence for every later command (measured 2026-10-03, two factory presets in a row).
RULE_SET = {"reverb/reverbActive": False, "delay/delayActive": False,
            "tremolo/tremoloActive": False, "parameters/doublerActive": False,
            "parameters/gateActive": False, "fxParameters/sectionActive": True,
            "parameters/transpose": 0}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--amp", choices=sorted(TEMPLATES), required=True)
    ap.add_argument("--out-dir", type=pathlib.Path, required=True)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--crops-dir", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/references/validation-crops"))
    ap.add_argument("--factory-dir", type=pathlib.Path, default=FACTORY)
    return ap


def preset_edits(path: pathlib.Path, pack, renderer, amp: str, rule_set: bool):
    """(selectAmp index, [edits]) for a whole preset, with R applied on request."""
    from format.parser import parse
    from format.structured import build

    preset = build(parse(path.read_bytes()))
    edits, select = {}, None
    for parameter in preset.parameters:
        spec = pack.parameters.get(f"{parameter.module_path}/{parameter.key}")
        if spec is None or not spec.writable:
            continue
        if not parameter.module_path:
            # Top-level attributes are the preset's name and version, which are not
            # module controls; the amp choice is sent as the server's selectAmp.
            if parameter.key == "selectedAmp":
                select = int(float(parameter.value))
            continue
        edits[(parameter.module_path, parameter.key)] = parameter.value
    if rule_set:
        overrides = dict(RULE_SET)
        if amp in SPRING:
            overrides[SPRING[amp]] = 0.0
        for path_key, value in overrides.items():
            module, _, key = path_key.rpartition("/")
            spec = pack.parameters[path_key]
            edits[(module, key)] = renderer._stored(pack, spec, value)
    return select, [{"module": m, "key": k, "value": v} for (m, k), v in edits.items()]


def candidates(args, pack, renderer):
    """name -> (path, rule_set) for the panel: the amp's factory presets with R,
    the template with R, and the template as shipped."""
    from format.parser import parse
    from format.structured import build

    wanted = renderer._stored(pack, pack.parameters["/selectedAmp"], AMP_NAMES[args.amp])
    panel = {}
    for path in sorted(args.factory_dir.rglob("*.xml")):
        if "User" in path.relative_to(args.factory_dir).parts:
            continue
        preset = build(parse(path.read_bytes()))
        amp = preset.by_path.get(("", "selectedAmp"))
        if amp is not None and str(int(float(amp.value))) == str(int(float(wanted))):
            name = "factory:" + str(path.relative_to(args.factory_dir).with_suffix(""))
            panel[name] = (path, True)
    template = PLUGIN_ROOT / TEMPLATES[args.amp]
    panel["template+R"] = (template, True)
    panel["template"] = (template, False)
    return panel


def _slug(name: str) -> str:
    return hashlib.sha1(name.encode()).hexdigest()[:12]


def work(job):
    """Render every candidate through each of a worker's parts, in one process."""
    import numpy as np
    import soundfile as sf

    from analysis import io
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    args, parts = job
    pack = load_pack("morgan")

    class PanelRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edits = self.commands[settings["panel"]]
            command = {"edits": edits}
            if select is not None:
                command["selectAmp"] = select
            return command

    renderer = PanelRenderer("morgan", process_policy="reuse")
    panel = candidates(args, pack, renderer)
    PanelRenderer.commands = {name: preset_edits(path, pack, renderer, args.amp, rule)
                              for name, (path, rule) in panel.items()}
    rows, first = [], None
    try:
        for slug in parts:
            di = io.load(args.crops_dir.expanduser() / slug / "di.wav").mono().astype(np.float32)
            renderer.render(di, {"panel": "template+R"})          # warm-up, discarded
            out = args.out_dir / slug
            out.mkdir(parents=True, exist_ok=True)
            for name in panel:
                path = out / f"{_slug(name)}.wav"
                if not path.exists():
                    audio = np.asarray(renderer.render(di, {"panel": name}).audio)
                    # Float, not 24-bit PCM: presets with a hot output go past full
                    # scale, and integer PCM clipped 156 of the first panel's renders.
                    sf.write(path, audio, 48000, subtype="FLOAT")
                    if first is None:
                        first = (slug, name, audio)
                rows.append({"part": slug, "candidate": name, "file": str(path)})
        if first is not None:                      # the process still renders the same
            slug, name, audio = first
            di = io.load(args.crops_dir.expanduser() / slug / "di.wav").mono().astype(np.float32)
            again = np.asarray(renderer.render(di, {"panel": name}).audio)
            drift = float(20 * np.log10((np.std(again) + 1e-12) / (np.std(audio) + 1e-12)))
            rows.append({"canary": slug, "candidate": name, "rms_drift_db": round(drift, 3)})
    finally:
        renderer.close()
    return rows


def main() -> None:
    args = build_parser().parse_args()
    from analysis import require

    require("rendering a preset panel")
    sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
    from benchmark_recordings import CATALOG, development_parts

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    parts = development_parts(catalog, None, [2])
    if not parts:
        die("no set-2 development parts")
    slugs = ["-".join(piece.replace("/", "_").replace(" ", "_") for piece in part)
             for part in parts]
    missing = [s for s in slugs if not (args.crops_dir.expanduser() / s / "di.wav").exists()]
    if missing:
        die(f"crops missing for {', '.join(missing)}; run benchmark_recordings.py once")
    args.out_dir = args.out_dir.expanduser()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    # Renders already on disk are reused, so a directory rendered under another rule
    # set or format must not be resumed into.
    config = {"amp": args.amp, "rule_set": RULE_SET, "spring_off": SPRING.get(args.amp),
              "format": "FLOAT"}
    stamp = args.out_dir / "panel-config.json"
    if stamp.exists() and json.loads(stamp.read_text()) != config:
        die(f"{args.out_dir} holds renders made with another configuration; use a new "
            f"directory")
    stamp.write_text(json.dumps(config, indent=1))
    jobs = [(args, slugs[i::args.workers]) for i in range(args.workers)]
    with ProcessPoolExecutor(args.workers) as pool:
        rows = [row for result in pool.map(work, jobs) for row in result]
    index = {"amp": args.amp, "rule_set": RULE_SET, "spring_off": SPRING.get(args.amp),
             "parts": slugs, "rows": rows}
    (args.out_dir / "index.json").write_text(json.dumps(index, indent=1))
    canaries = [r for r in rows if "canary" in r]
    print(f"{len([r for r in rows if 'file' in r])} renders; canaries {canaries}")


if __name__ == "__main__":
    guarded(main)
