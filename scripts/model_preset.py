#!/usr/bin/env python3
"""Generate a Morgan preset from a song with the trained model (generate's model path, behind its flag).

    python scripts/model_preset.py --song SONG.mp3 --cls clean|crunch [--start S] \
        --work WORK_DIR --out OUT.xml [--name NAME]

Runs the model path's four stages (`learn/product_path.py`), each in the environment it needs:
  separate  the song's 10-s window and its separated guitar (msst-venv);
  answers   the adopted model's settings on each of the three amps (torch);
  render    each amp's answer through the class's two stock DIs, 12 renders (the main venv);
  pick      the amp whose renders sound closest to the song's guitar, and the output gain that plays it
            at the factory start's loudness (torch).
Then it writes the picked settings onto that amp's factory starting preset. Time effects stay off: the
generate skill adds the song research's effects afterwards with apply_spec.

`--delay-reader` (off by default; the real-song test's third arm, a candidate) adds product_path's `delay` stage
(the main venv, zero renders): when it hears a delay it switches the delay on at the time it read, with the song
research's mix and feedback (`--delay-mix` and `--delay-feedback`, 0-1, together) or a declared 0.30/0.30 default.
When it hears none, the delay is left as research sets it.

Only on a machine with the model's data (`~/ndsp-presets`) and its environments. Interpreters can be
set with NDSP_MSST_PY, NDSP_TORCH_PY and NDSP_MAIN_PY. A stage whose output exists is not run again,
so a stopped run resumes with the same command; `--write-only` writes from an existing WORK_DIR.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _cli import die, guarded
from format.parser import parse_file
from format.structured import build, set_parameter
from format.writer import write_file

DATA = pathlib.Path("~/ndsp-presets").expanduser()
TOOLS = DATA / "tools"
FACTORY = pathlib.Path("/Library/Audio/Presets/Neural DSP/Morgan Amps Suite")
ADOPTED = DATA / "learn/trusted-data/pipeline-fix/adopted-model.json"
STAGES = (("separate", "msst", "window.json"), ("answers", "torch", "answers.json"),
          ("render", "main", "renders.json"), ("pick", "torch", "preset.json"))


def main_python() -> pathlib.Path:
    """The main venv's interpreter: the nearest `.venv` at or above the plugin root."""
    for d in (PLUGIN_ROOT, *PLUGIN_ROOT.parents):
        p = d / ".venv/bin/python"
        if p.exists():
            return p
    die("No main .venv found at or above the plugin root (an installed copy has none): set NDSP_MAIN_PY to the "
        "repository's .venv/bin/python.")


def interpreters() -> dict:
    return {"msst": pathlib.Path(os.environ.get("NDSP_MSST_PY", TOOLS / "msst-venv/bin/python")),
            "torch": pathlib.Path(os.environ.get("NDSP_TORCH_PY", TOOLS / "demucs-venv/bin/python")),
            "main": pathlib.Path(os.environ["NDSP_MAIN_PY"]) if "NDSP_MAIN_PY" in os.environ else main_python()}


def stage_args(stage: str, args) -> list:
    """The stages run from the plugin root, so `run` resolves --song and --work first."""
    if stage == "separate":
        out = [str(args.song), "--out", str(args.work)]
        return out + (["--start", str(args.start)] if args.start is not None else [])
    if stage == "answers":
        return [str(args.work), "--cls", args.cls]
    return [str(args.work)]


def delay_args(args) -> list:
    out = [str(args.work)]
    if args.delay_mix is not None:
        out += ["--mix", str(args.delay_mix), "--feedback", str(args.delay_feedback), "--source", args.delay_source]
    return out


def run_delay(args, py) -> None:
    """The delay stage, after the pick. An existing delay.json must hold the same mix and feedback."""
    p = args.work / "delay.json"
    if p.exists():
        d = json.loads(p.read_text())
        if args.delay_mix is not None and (abs(d["mix"] - args.delay_mix) > 1e-9
                                           or abs(d["feedback"] - args.delay_feedback) > 1e-9):
            die(f"{p} was read with another mix and feedback; remove it or use a new --work.")
        return
    cmd = [str(py["main"]), "-m", "learn.product_path", "delay", *delay_args(args)]
    print(f"[delay] {' '.join(cmd)}", flush=True)
    if subprocess.run(cmd, cwd=PLUGIN_ROOT).returncode != 0:
        die("The delay stage failed; fix it and run the same command again to resume.")


def run_stages(args) -> None:
    py = interpreters()
    for name, p in py.items():
        if not p.exists():
            die(f"The {name} interpreter is missing: {p}")
    done = args.work / "window.json"
    if done.exists():                     # a resumed run must be the same song and window
        w = json.loads(done.read_text())
        if pathlib.Path(w["song"]) != args.song or (
                args.start is not None and abs(float(w["start_s"]) - args.start) > 1e-6):
            die(f"{args.work} holds another song or window ({w['song']} at {w['start_s']} s); use a new --work.")
    ans = args.work / "answers.json"
    if ans.exists() and json.loads(ans.read_text())["cls"] != args.cls:
        die(f"{args.work} was answered for another class; use a new --work.")
    for stage, env, marker in STAGES:
        if (args.work / marker).exists():
            continue
        cmd = [str(py[env]), "-m", "learn.product_path", stage, *stage_args(stage, args)]
        print(f"[{stage}] {' '.join(cmd)}", flush=True)
        if subprocess.run(cmd, cwd=PLUGIN_ROOT).returncode != 0:
            die(f"The {stage} stage failed; fix it and run the same command again to resume.")
    if args.delay_reader:
        run_delay(args, py)


def template_for(amp: str, cls: str) -> pathlib.Path:
    from learn.knob_ceiling import START       # the factory starts the model's answers are edits of

    p = FACTORY / f"{START[cls][amp].removeprefix('factory:')}.xml"
    if not p.exists():
        die(f"The factory starting preset is missing: {p}")
    return p


def write_preset(result: dict, out: pathlib.Path, name, template=None) -> list:
    """The picked settings (stored values) onto the amp's factory start. -> [(path, before, after)] changed."""
    template = template or template_for(result["amp"], result["cls"])
    preset = build(parse_file(str(template)))
    amp = preset.by_path.get(("", "selectedAmp"))
    if amp is None or int(float(amp.value)) != int(result["select"]):
        die(f"{template.name} plays amp {amp and amp.value}, the model's answer amp {result['select']}.")
    changes = []
    for path, value in sorted(result["settings"].items()):
        module, _, key = path.rpartition("/")
        param = preset.by_path.get((module, key))
        if param is None:
            die(f"{path} is not in {template.name}; the answer and the start disagree.")
        stored = str(value)
        if stored != param.value:
            changes.append((path, param.value, stored))
            set_parameter(preset, module, key, stored)
    if name:
        key = next((k for k in ("name", "presetNameProp") if ("", k) in preset.by_path), None)
        if key:
            set_parameter(preset, "", key, str(name))
    out.parent.mkdir(parents=True, exist_ok=True)
    write_file(str(out), preset.tokens)
    return changes


def delay_line(d: dict) -> str:
    if not d["on"]:
        return f"Delay reader: heard none (vote {d['vote']:.2f}); the delay is left to the song research"
    return (f"Delay reader: on (vote {d['vote']:.2f}), {d['time_ms']:.0f} ms ({d['time_from']}), mix {d['mix']:.2f} "
            f"and feedback {d['feedback']:.2f} from {d['mix_feedback_from']}")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--song", help="the song file (any format the separator reads)")
    ap.add_argument("--cls", choices=("clean", "crunch"), help="the part's class, from the song research")
    ap.add_argument("--start", type=float, default=None,
                    help="where the part starts, in seconds; without it the window where the guitar is most exposed")
    ap.add_argument("--work", type=pathlib.Path, required=True, help="a folder for the stages' files")
    ap.add_argument("--out", type=pathlib.Path, required=True, help="the preset to write")
    ap.add_argument("--name", help="the preset's name")
    ap.add_argument("--delay-reader", action="store_true",
                    help="also read the delay from the song (a candidate; the real-song test's third arm)")
    ap.add_argument("--delay-mix", type=float, help="the delay mix from the song research, 0-1 (with --delay-feedback)")
    ap.add_argument("--delay-feedback", type=float, help="the delay feedback from the song research, 0-1 (with --delay-mix)")
    ap.add_argument("--delay-source", default="the song research", help="where the delay mix and feedback came from")
    ap.add_argument("--force", action="store_true", help="overwrite --out")
    ap.add_argument("--write-only", action="store_true", help="write from WORK_DIR/preset.json, run nothing")
    return ap


def run(args) -> None:
    args.work = args.work.expanduser().resolve()      # the stages run from the plugin root, not the caller's folder
    out = args.out.expanduser().resolve()
    if args.song:
        args.song = pathlib.Path(args.song).expanduser().resolve()
    if out.exists() and not args.force:
        die(f"--out already exists: {out}\n  Pass --force to overwrite it, or choose a different path.")
    if (args.delay_mix is None) != (args.delay_feedback is None):
        die("Pass --delay-mix and --delay-feedback together (the song research's pair), or neither for the default.")
    if args.delay_mix is not None and not args.delay_reader:
        die("--delay-mix and --delay-feedback go with --delay-reader.")
    if not args.write_only:
        if not args.song or not args.cls:
            die("--song and --cls are required unless --write-only.")
        if not ADOPTED.exists():
            die(f"The model path needs the model's data ({ADOPTED}); use the research path instead.")
        args.work.mkdir(parents=True, exist_ok=True)
        run_stages(args)
    result = json.loads((args.work / "preset.json").read_text())
    window = json.loads((args.work / "window.json").read_text())
    delay = None
    if args.delay_reader:
        p = args.work / "delay.json"
        if not p.exists():
            die(f"--delay-reader: {p} is missing; run without --write-only first.")
        delay = json.loads(p.read_text())
        if delay["amp"] != result["amp"]:
            die(f"{p} was read for {delay['amp']}, the pick is {result['amp']}.")
        result = {**result, "settings": {**result["settings"], **delay["settings"]}}
    changes = write_preset(result, out, args.name)
    g = result["output_gain"]
    print(f"\nAmp: {result['amp']} ({result['cls']}); distances "
          + ", ".join(f"{a} {d:.4f}" for a, d in sorted(result["distances"].items(), key=lambda kv: kv[1])))
    print(f"Window: {window['start_s']:.1f} s ({'given' if window['chosen_by'] == 'given' else 'most exposed guitar'})")
    print(f"Output gain: {g['from']:+.1f} -> {g['to']:+.1f} dB" + (f" (clamped, {g['shortfall']:+.1f} dB short)"
                                                                   if g["shortfall"] else ""))
    if delay is not None:
        print(delay_line(delay))
    print(f"{len(changes)} value(s) changed against {template_for(result['amp'], result['cls']).name}")
    print(f"Wrote {out}")


def main() -> None:
    guarded(lambda: run(build_parser().parse_args()))


if __name__ == "__main__":
    main()
