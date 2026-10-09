"""(render, DI) pairs for the DI-rebuilding network, across Morgan's three amps
(`docs/di-recovery-plan.md`, Phase 1). No setting labels are kept: the network only
needs what was played (the DI) and what came out (the render).

Each pair:
- **DI.** An 8-s development DI window (2 s pre-roll, 6 s kept) from set 2's
  development bands or Guitar-TECHS P1, through a random pre-amp guitar EQ
  (±6 dB tilt over 100 Hz–10 kHz, one ±6 dB bell at 150 Hz–5 kHz, one octave wide).
  That EQ'd DI is the pair's DI.
- **Settings.** A factory preset of the amp, or its template, with R applied; the amp's
  knobs redrawn with probability 0.7 each, its switches with probability 0.3, input
  gain over ±12 dB, the drive pedals on with probability 0.25 each (knobs uniform), the
  compressor on with probability 0.5, EQ bands spike-and-slab, and both mic types
  redrawn. Drive is deliberately pushed: half the draws set the amp's gain knob
  (Volume) in its upper half, so crunch and high gain are well covered.

    python -m learn.render_pairs --amp sw50r --count 15000 --workers 4 \\
        --out ~/ndsp-presets/learn/direc/pairs-sw50r
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

SR = 48000
GAIN_KNOB = {"pr12": "pr12Amp/pr12Volume", "sw50r": "sw50rAmp/sw50rVolume", "ac20": "ac20Amp/ac20Volume"}


def pre_eq(x, rng):
    import numpy as np

    n = len(x)
    f = np.maximum(np.fft.rfftfreq(n, 1 / SR), 20)
    lf = np.log2(f / 1000)
    tilt = rng.uniform(-6, 6) * np.clip(lf / 3.32, -1, 1)
    fc, g = rng.uniform(math.log2(150), math.log2(5000)), rng.uniform(-6, 6)
    bell = g * np.exp(-0.5 * ((np.log2(f) - fc) / 0.5) ** 2)
    return np.fft.irfft(np.fft.rfft(x) * 10 ** ((tilt + bell) / 20), n)


def settings(amp, base_edits, pack, rng):
    """Edits dict {(module, key): stored} for one draw, from a base preset's edits."""
    e = dict(base_edits)
    prefix = f"{amp}Amp/"
    for path, spec in pack.parameters.items():
        if not spec.writable:
            continue
        module, _, key = path.rpartition("/")
        if path.startswith(prefix):
            if path.endswith(("Reverb", "Dwell")):
                continue
            if spec.kind == "rotation" and rng.random() < 0.7:
                e[(module, key)] = f"{rng.uniform(0, 1):.4f}"
            elif spec.kind == "switch" and rng.random() < 0.3:
                e[(module, key)] = rng.choice(("true", "false"))
        elif path.startswith(f"{amp}EQ/{amp}EQBand"):
            v = 0.0 if rng.random() < 0.5 else max(-12, min(12, rng.choice((-1, 1)) * rng.expovariate(1 / 3)))
            e[(module, key)] = f"{v:.3f}"
    if rng.random() < 0.5:
        m, _, k = GAIN_KNOB[amp].rpartition("/")
        e[(m, k)] = f"{rng.uniform(0.5, 1):.4f}"
    e[("parameters", "inputGain")] = f"{rng.uniform(-12, 12):.3f}"
    for pedal, knobs in (("drive1", ("drive1Drive", "drive1Tone", "drive1Level")),
                         ("drive2", ("drive2Gain", "drive2Bass", "drive2Treble", "drive2Level"))):
        on = rng.random() < 0.25
        e[(pedal, f"{pedal}Active")] = "true" if on else "false"
        if on:
            for k in knobs:
                lo = 0.2 if k.endswith("Level") else 0.0
                e[(pedal, k)] = f"{rng.uniform(lo, 1):.4f}"
    e[("compressor", "compressorActive")] = "true" if rng.random() < 0.5 else "false"
    for side in ("left", "right"):
        e[("cabParameters", f"{side}MicType")] = str(rng.randrange(10))
    return e


def work(job):
    import numpy as np
    import soundfile as sf

    import render_preset_panel as RP
    from analysis import io
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    out, amp, jobs, wid = job
    pack = load_pack("morgan")

    class R(AudioUnitRenderer):
        command = None

        def _state_command(self, settings):
            return self.command

    r = R("morgan", process_policy="reuse")
    menu = RP.candidates(argparse.Namespace(amp=amp, factory_dir=RP.FACTORY), pack, r)
    bases = []
    for name, (path, rule) in menu.items():
        if name == "template":
            continue
        select, edits = RP.preset_edits(path, pack, r, amp, True)
        bases.append((select, {(d["module"], d["key"]): d["value"] for d in edits}))
    cache = {}
    done = 0
    try:
        for n, j in enumerate(jobs):
            rng = random.Random(j["seed"])
            w = j["window"]
            if w["file"] not in cache:
                cache.clear()
                cache[w["file"]] = np.asarray(io.load(w["file"]).mono(), np.float64)
            a = int(w["start_s"] * SR)
            di = pre_eq(cache[w["file"]][a:a + 8 * SR], np.random.default_rng(j["seed"]))
            select, base = rng.choice(bases)
            e = settings(amp, base, pack, rng)
            r.command = {"selectAmp": select, "edits": [{"module": m, "key": k, "value": v}
                                                        for (m, k), v in e.items()]}
            if n == 0:
                r.render(di.astype(np.float32), {})                      # warm-up
            y = np.asarray(r.render(di.astype(np.float32), {}).audio, np.float64)
            y = y.mean(axis=1) if y.ndim == 2 else y
            y, d = y[2 * SR:], di[2 * SR:]
            peak = np.abs(y).max()
            if not np.isfinite(peak) or peak < 1e-4:
                continue
            sf.write(out / f"{j['id']}-out.flac", y / peak * 0.9, SR, subtype="PCM_16")
            sf.write(out / f"{j['id']}-di.flac", d / (np.abs(d).max() + 1e-9) * 0.9, SR, subtype="PCM_16")
            with open(out / f"index-w{wid}.jsonl", "a") as f:
                f.write(json.dumps({"id": j["id"], "amp": amp, "band": w["band"], "file": w["file"],
                                    "start_s": w["start_s"], "lufs": w["lufs"]}) + "\n")
            done += 1
            if (out / "STOP").exists():
                break
    finally:
        r.close()
    return done


def main():
    from learn.render_job import daemon

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--amp", choices=sorted(GAIN_KNOB), required=True)
    ap.add_argument("--windows", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/learn/poc/di-windows.json"))
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--count", type=int, default=15000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20261007)
    ap.add_argument("--max-ports", type=int, default=235000)
    args = ap.parse_args()
    out = args.out.expanduser()
    out.mkdir(parents=True, exist_ok=True)
    windows = [w for w in json.loads(args.windows.expanduser().read_text())["windows"] if w["lufs"] >= -40]
    by = {}
    for w in windows:
        by.setdefault(w["band"], []).append(w)
    rng = random.Random(args.seed)
    jobs = [{"id": f"{args.amp}{i:06d}", "seed": rng.randrange(2 ** 31),
             "window": rng.choice(by[rng.choice(sorted(by))])} for i in range(args.count)]
    done = set()
    for f in out.glob("index-w*.jsonl"):
        done |= {json.loads(line)["id"] for line in f.read_text().splitlines() if line}
    todo = [j for j in jobs if j["id"] not in done]
    pid0, ports0 = daemon()
    print(f"{args.amp}: {len(todo)} of {len(jobs)} to render; daemon {pid0} ports {ports0}", flush=True)
    if ports0 and ports0 > args.max_ports:
        raise SystemExit("licence daemon port count too high; reboot first")
    t0 = time.time()
    with ProcessPoolExecutor(args.workers) as pool:
        n = sum(pool.map(work, [(out, args.amp, todo[i::args.workers], i) for i in range(args.workers)]))
    pid1, ports1 = daemon()
    print(f"rendered {n} in {time.time() - t0:.0f}s; daemon {pid1} ports {ports1}", flush=True)


if __name__ == "__main__":
    main()
