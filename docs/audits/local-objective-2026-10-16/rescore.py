"""Re-score a few stored FLACs with the judge called directly, signals built here, mask shift by hand."""
import json, math, pathlib, sys
import numpy as np, soundfile as sf

WT = "/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT"
sys.path.insert(0, WT); sys.path.insert(0, WT + "/research")
from analysis.aligned import aligned_distance
from learn import knob_ceiling as K

ROOT = pathlib.Path.home() / "ndsp-presets/learn/local-objective"
PARTS = K.parts()
HALVES = K.R.HALVES
print("halves", HALVES)

def mono(p):
    x, sr = sf.read(str(p), dtype="float64"); assert sr == 48000, sr
    return x.mean(1) if x.ndim == 2 else x

def shift_to_di(rec, s):  # rec_di[t] = rec[t + s], zero padded
    out = np.zeros_like(rec)
    if s >= 0: out[:len(rec) - s] = rec[s:]
    else: out[-s:] = rec[:len(rec) + s]
    return out

worst = 0
for slug, amp, idxs in (("cambridge-Drag_Me_Down-ElecGtr4", "pr12", (0, 17, 40)), ("cambridge-Prodigal-ElecGtr5", "sw50r", (0, 25, 44)),
                        ("telefunken-Sculptor's_Request-GTR_2", "ac20", (3, 30, 47))):
    part = PARTS[slug]
    sigs = {"stem": mono(pathlib.Path.home() / "ndsp-presets/learn/set3/stems/htdemucs_6s" / slug / "instrumental_guitar.wav")
            if (pathlib.Path.home() / "ndsp-presets/learn/set3/stems/htdemucs_6s" / slug).exists()
            else mono(pathlib.Path.home() / "ndsp-presets/learn/poc/stems/htdemucs_6s" / slug / "instrumental_guitar.wav"),
            "reference": mono(part["crop"] / "reference.wav")}
    dis = {"cprime": np.load(pathlib.Path.home() / "ndsp-presets/learn/song-settings/rebuilt" / f"{slug}.npy"),
           "measure": K.measure_di(part)}
    jl = part["judge_lag"]
    for d in ("cprime", "measure"):
        rec = json.load(open(ROOT / "renders" / d / slug / f"{amp}.json"))
        sc = json.load(open(ROOT / "scores" / d / slug / f"{amp}.json"))
        for i in idxs:
            y, _ = sf.read(str(ROOT / "renders" / d / slug / amp / f"{i:02d}.flac"), dtype="float64")
            y = y * rec["scales"][i]
            for cfg, stored in sc["scores"][i].items():
                _, ref, lag, mask = cfg.split("|")
                native = -52 if d == "cprime" else jl
                other = jl if d == "cprime" else -52
                lg = {"native": native, "other": other, "zero": 0, "gcc": -52 - (sc["gcc_rebuild_vs_stem"] or 0)}[lag]
                R = sigs[ref]
                m = dis[d] if mask == "own" else shift_to_di(R, lg + 52)
                for h, (a, b) in HALVES.items():
                    r = aligned_distance(R, y, m, lag=lg, render_latency=52, start_s=a, end_s=b)
                    v = r.distance
                    if v is None and d == "cprime" and mask == "own":
                        v = aligned_distance(R, y, shift_to_di(R, lg + 52), lag=lg, render_latency=52, start_s=a, end_s=b).distance
                    v = math.inf if v is None else v
                    dv = 0 if (not math.isfinite(v) and not math.isfinite(stored[h])) else abs(math.log(v / stored[h]))
                    worst = max(worst, dv)
                    if dv > 1e-9: print("DIFF", slug, amp, d, i, cfg, h, v, stored[h], dv)
    print("done", slug, amp, "worst so far", worst, flush=True)
print("WORST", worst)
