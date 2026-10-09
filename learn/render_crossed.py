"""Crossed renders for the tone encoder (`docs/tone-encoder-plan.md`): each sampled
setting is heard through several players, and each player through several settings.

The plan is made of blocks. A block is one amp, 8 sampled settings and 7 DI windows,
one window from each of 7 different bands (drawn from set 2's 13 development bands and
Guitar-TECHS P1, `learn/di_pool.py`). Every setting in the block is rendered through
every window of the block, so the same setting through different DIs gives positives,
and different settings through the same DI give hard negatives.

- **PR12** settings come from `learn/pr12.py`'s sampler (half coverage, half jittered
  factory presets); **SW50R and AC20** from `learn/render_pairs.py`'s (factory base
  with R, knobs redrawn).
- Half of a block's windows go through `render_pairs.pre_eq` (a mild guitar EQ, seeded
  by block and window, so every setting of the block hears the same EQ'd DI).
- An 8-s window: 2 s of pre-roll is discarded, 6 s kept, mono, 16-bit FLAC at 48 kHz,
  peak-normalised (the gain is recorded).

The licence daemon's port count is checked at the start and watched; workers stop if it
passes `--max-ports` or the daemon's PID changes. The daemon itself is never touched.
Resumable: clips already listed in an `index-w*.jsonl` are skipped.

    python -m learn.render_crossed --out ~/ndsp-presets/learn/tone-encoder/renders --workers 3
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import random
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

SR = 48000
BLOCKS = {"pr12": 175, "sw50r": 63, "ac20": 62}
SETTINGS_PER_BLOCK = 8
WINDOWS_PER_BLOCK = 7


def plan(windows, seed):
    """[block] with amp, setting seeds and windows. Settings are drawn in the worker
    from their seed (the samplers need the plugin's pack)."""
    from learn import set3

    by = {}
    for w in windows:
        if w["lufs"] < -40:
            continue
        assert not set3.is_held_out(w["file"]), w["file"]
        by.setdefault(w["band"], []).append(w)
    bands = sorted(by)
    rng = random.Random(seed)
    blocks = []
    for amp, n in BLOCKS.items():
        for b in range(n):
            chosen = rng.sample(bands, WINDOWS_PER_BLOCK)
            blocks.append({
                "block": f"{amp}-b{b:03d}", "amp": amp,
                "settings": [rng.randrange(2 ** 31) for _ in range(SETTINGS_PER_BLOCK)],
                "windows": [dict(rng.choice(by[band]), preeq=rng.random() < 0.5,
                                 eq_seed=rng.randrange(2 ** 31)) for band in chosen]})
    return blocks


def commands(amp, seeds, pack, r):
    """(source, server command) for each setting seed of a block."""
    from learn import pr12

    out = []
    if amp == "pr12":
        if "pr12" not in _BASES:
            template = pr12.template_state()
            writable = {k for k, spec in pack.parameters.items()
                        if spec.writable and spec.kind not in ("path", "string", "internal")}
            _BASES["pr12"] = ({k: v for k, v in template.items() if k in writable},
                              [pr12.from_state(s, template) for s in pr12.factory_presets().values()])
        template, factory = _BASES["pr12"]
        for sd in seeds:
            rng = random.Random(sd)
            source, s = pr12.sample(rng, factory)
            out.append((source, pr12.render_command(s, template, float(s["parameters/inputGain"]))))
        return out
    return [("sampled", c) for c in _other_amp_commands(amp, seeds, pack, r)]


_BASES = {}


def _other_amp_commands(amp, seeds, pack, r):
    import render_preset_panel as RP

    from learn import render_pairs as RPR

    if amp not in _BASES:
        menu = RP.candidates(argparse.Namespace(amp=amp, factory_dir=RP.FACTORY), pack, r)
        bases = []
        for name, (path, rule) in menu.items():
            if name == "template":
                continue
            select, edits = RP.preset_edits(path, pack, r, amp, True)
            bases.append((select, {(d["module"], d["key"]): d["value"] for d in edits}))
        _BASES[amp] = bases
    out = []
    for sd in seeds:
        rng = random.Random(sd)
        select, base = rng.choice(_BASES[amp])
        e = RPR.settings(amp, base, pack, rng)
        out.append({"selectAmp": select,
                    "edits": [{"module": m, "key": k, "value": v} for (m, k), v in e.items()]})
    return out


def work(job):
    import numpy as np
    import soundfile as sf

    from analysis import io
    from match.renderer_au import AudioUnitRenderer

    from learn import render_pairs as RPR

    out, blocks, done, wid = job

    class R(AudioUnitRenderer):
        command = None

        def _state_command(self, settings):
            return self.command

    from packs.loader import load_pack

    pack = load_pack("morgan")
    r = R("morgan", process_policy="reuse")
    cache = {}
    n_done, canary, n = 0, None, 0
    t0 = time.time()
    try:
        for blk in blocks:
            cmds = commands(blk["amp"], blk["settings"], pack, r)
            for wi, w in enumerate(blk["windows"]):
                if w["file"] not in cache:
                    cache.clear()
                    cache[w["file"]] = np.asarray(io.load(w["file"]).mono(), np.float64)
                a = int(w["start_s"] * SR)
                di = cache[w["file"]][a:a + 8 * SR]
                if w["preeq"]:
                    di = RPR.pre_eq(di, np.random.default_rng(w["eq_seed"]))
                di = di.astype(np.float32)
                for si, (source, cmd) in enumerate(cmds):
                    cid = f"{blk['block']}-s{si}-w{wi}"
                    if cid in done:
                        continue
                    r.command = cmd
                    if n == 0:
                        r.render(di, {})                                  # warm-up
                    y = np.asarray(r.render(di, {}).audio, np.float64)
                    y = (y.mean(axis=1) if y.ndim == 2 else y)[2 * SR:]
                    n += 1
                    peak = float(np.abs(y).max())
                    row = {"id": cid, "block": blk["block"], "amp": blk["amp"], "setting": si,
                           "window": wi, "band": w["band"], "file": w["file"], "start_s": w["start_s"],
                           "lufs": w["lufs"], "preeq": w["preeq"], "source": source}
                    if not np.isfinite(peak) or peak < 1e-5:
                        row["bad"] = "silent or non-finite"
                    else:
                        row["gain"] = 0.9 / peak
                        sf.write(out / f"{cid}.flac", (y * row["gain"]).astype(np.float32), SR,
                                 subtype="PCM_16")
                        n_done += 1
                        if canary is None:
                            canary = (cmd, di, float(np.std(y)))
                        elif n % 300 == 0:
                            r.command = canary[0]
                            again = np.asarray(r.render(canary[1], {}).audio, np.float64)
                            again = (again.mean(axis=1) if again.ndim == 2 else again)[2 * SR:]
                            drift = 20 * np.log10((np.std(again) + 1e-12) / (canary[2] + 1e-12))
                            print(f"w{wid} {n} {time.time() - t0:.0f}s canary {drift:+.3f} dB", flush=True)
                            if abs(drift) > 0.5:
                                raise RuntimeError(f"canary drifted {drift:+.2f} dB")
                    with open(out / f"index-w{wid}.jsonl", "a") as f:
                        f.write(json.dumps(row) + "\n")
                    if (out / "STOP").exists():
                        return n_done
    finally:
        r.close()
    return n_done


def main():
    from learn.render_job import daemon

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--windows", type=pathlib.Path,
                    default=pathlib.Path("~/ndsp-presets/learn/poc/di-windows.json"))
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20261008)
    ap.add_argument("--max-ports", type=int, default=235000)
    args = ap.parse_args()
    assert args.workers <= 3
    out = args.out.expanduser()
    out.mkdir(parents=True, exist_ok=True)
    blocks = plan(json.loads(args.windows.expanduser().read_text())["windows"], args.seed)
    (out / "plan.json").write_text(json.dumps(blocks))
    done = set()
    for f in out.glob("index-w*.jsonl"):
        done |= {json.loads(line)["id"] for line in f.read_text().splitlines() if line}
    total = len(blocks) * SETTINGS_PER_BLOCK * WINDOWS_PER_BLOCK
    pid0, ports0 = daemon()
    print(f"{total - len(done)} of {total} to render; daemon {pid0} ports {ports0}", flush=True)
    if ports0 and ports0 > args.max_ports:
        raise SystemExit("licence daemon port count too high; reboot first")

    def watchdog():
        while not (out / "DONE").exists():
            pid, ports = daemon()
            with open(out / "daemon.log", "a") as f:
                f.write(f"{time.time():.0f} {pid} {ports}\n")
            if pid != pid0 or (ports and ports > args.max_ports):
                (out / "STOP").write_text(f"daemon pid {pid} ports {ports}\n")
                print("watchdog: stopping workers", flush=True)
                return
            time.sleep(30)

    (out / "DONE").unlink(missing_ok=True)
    threading.Thread(target=watchdog, daemon=True).start()
    rng = random.Random(1)
    order = blocks[:]
    rng.shuffle(order)                     # mix amps across workers and over time
    t0 = time.time()
    with ProcessPoolExecutor(args.workers) as pool:
        n = sum(pool.map(work, [(out, order[i::args.workers], done, i) for i in range(args.workers)]))
    (out / "DONE").write_text("")
    pid1, ports1 = daemon()
    print(f"rendered {n} in {time.time() - t0:.0f}s; daemon {pid1} ports {ports1}", flush=True)


if __name__ == "__main__":
    main()
