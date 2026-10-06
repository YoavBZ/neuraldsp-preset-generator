"""Render sampled PR12 settings through DI windows, in reused plugin processes.

    python -m learn.render_job --windows ~/ndsp-presets/learn/poc/di-windows.json \\
        --out ~/ndsp-presets/learn/poc/renders --count 12000 --workers 4

Each clip: one sampled setting through one 8-s DI window (bands drawn uniformly, then a
window within the band); the first 2 s are pre-roll and discarded, the last 6 s are kept
and stored as 16-bit FLAC at 48 kHz, peak-normalised (the gain is recorded; loudness is
normalised again before any feature, so it carries no label). A worker reuses one plugin
process, discards a warm-up render, and re-renders a canary every 200 clips. The licence
daemon's port count is logged; the job stops if it passes `--max-ports` or the daemon's
PID changes. The daemon itself is never touched.

Resumable: clips already listed in `index.jsonl` are skipped.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import random
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from learn import pr12  # noqa: E402

SR = 48000


def daemon():
    """(pid, ports) of PACE's licence daemon, or (None, None)."""
    try:
        pid = subprocess.run(["pgrep", "-f", "licenseDaemon.app"], capture_output=True,
                             text=True).stdout.split()[0]
        out = subprocess.run(["top", "-l", "1", "-pid", pid, "-stats", "pid,ports"],
                             capture_output=True, text=True).stdout.strip().splitlines()
        return int(pid), int(out[-1].split()[1].rstrip("+"))
    except Exception:
        return None, None


def plan(windows, count, seed):
    rng = random.Random(seed)
    factory = [pr12.from_state(s, pr12.template_state()) for s in pr12.factory_presets().values()]
    by_band = {}
    for w in windows:
        by_band.setdefault(w["band"], []).append(w)
    bands = sorted(by_band)
    jobs = []
    for i in range(count):
        w = rng.choice(by_band[rng.choice(bands)])
        source, s = pr12.sample(rng, factory)
        jobs.append({"id": f"c{i:06d}", "window": w, "source": source, "sample": s})
    return jobs


def work(job):
    import numpy as np
    import soundfile as sf

    from match.renderer_au import AudioUnitRenderer

    out_dir, jobs, wid = job
    template = pr12.template_state()
    from packs.loader import load_pack
    pack = load_pack("morgan")
    writable = {k for k, spec in pack.parameters.items()
                if spec.writable and spec.kind not in ("path", "string", "internal")}
    template = {k: v for k, v in template.items() if k in writable}

    class R(AudioUnitRenderer):
        command = None

        def _state_command(self, settings):
            return self.command

    renderer = R("morgan", process_policy="reuse")
    cache = {}

    def di_window(w):
        key = w["file"]
        if key not in cache:
            from analysis import io
            cache.clear()
            cache[key] = io.load(key).mono().astype(np.float32)
        x = cache[key]
        a = int(w["start_s"] * SR)
        return np.ascontiguousarray(x[a:a + int(8.0 * SR)])

    def render(j):
        w = j["window"]
        renderer.command = pr12.render_command(j["sample"], template,
                                               float(j["sample"]["parameters/inputGain"]))
        y = np.asarray(renderer.render(di_window(w), {}).audio, dtype=np.float32)
        if y.ndim == 2:
            y = y.mean(axis=1)
        return y[int(2.0 * SR):]

    rows = []
    t0 = time.time()
    try:
        if jobs:
            render(jobs[0])                                # warm-up, discarded
        canary = None
        for n, j in enumerate(jobs):
            y = render(j)
            peak = float(np.abs(y).max())
            if not np.isfinite(peak) or peak == 0.0:
                rows.append({"id": j["id"], "bad": "silent or non-finite"})
                continue
            gain = 0.9 / peak
            sf.write(out_dir / f"{j['id']}.flac", y * gain, SR, subtype="PCM_16")
            w = j["window"]
            eff = float(j["sample"]["parameters/inputGain"]) + (w["lufs"] - pr12.ASSUMED_LUFS)
            row = {"id": j["id"], "band": w["band"], "file": w["file"], "start_s": w["start_s"],
                   "lufs": w["lufs"], "source": j["source"], "gain": gain,
                   "effective_drive": eff, "sample": j["sample"], "worker": wid}
            rows.append(row)
            with open(out_dir / f"index-w{wid}.jsonl", "a") as f:
                f.write(json.dumps(row) + "\n")
            if canary is None:
                canary = (j, y)
            elif n % 200 == 0:
                again = render(canary[0])
                drift = float(20 * np.log10((np.std(again) + 1e-12) / (np.std(canary[1]) + 1e-12)))
                print(f"w{wid} {n}/{len(jobs)} {time.time() - t0:.0f}s canary drift {drift:+.3f} dB",
                      flush=True)
                if abs(drift) > 0.5:
                    raise RuntimeError(f"canary drifted {drift:+.2f} dB")
            stop = out_dir / "STOP"
            if stop.exists():
                break
    finally:
        renderer.close()
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--windows", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--count", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20261006)
    ap.add_argument("--max-ports", type=int, default=235000)
    args = ap.parse_args()
    out = args.out.expanduser()
    out.mkdir(parents=True, exist_ok=True)
    windows = json.loads(args.windows.expanduser().read_text())["windows"]
    jobs = plan(windows, args.count, args.seed)
    done = set()
    for f in out.glob("index-w*.jsonl"):
        done |= {json.loads(line)["id"] for line in f.read_text().splitlines() if line}
    todo = [j for j in jobs if j["id"] not in done]
    pid0, ports0 = daemon()
    print(f"{len(todo)} of {len(jobs)} to render; daemon pid {pid0} ports {ports0}", flush=True)
    if ports0 and ports0 > args.max_ports:
        raise SystemExit("licence daemon port count too high; reboot first")

    import threading

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
    chunks = [(out, todo[i::args.workers], i) for i in range(args.workers)]
    t0 = time.time()
    with ProcessPoolExecutor(args.workers) as pool:
        rows = [r for result in pool.map(work, chunks) for r in result]
    (out / "DONE").write_text("")
    pid1, ports1 = daemon()
    bad = [r for r in rows if "bad" in r]
    print(f"rendered {len(rows) - len(bad)} ({len(bad)} bad) in {time.time() - t0:.0f}s; "
          f"daemon pid {pid1} ports {ports1} (+{(ports1 or 0) - (ports0 or 0)})", flush=True)


if __name__ == "__main__":
    main()
