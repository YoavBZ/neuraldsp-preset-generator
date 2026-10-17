import numpy as np, torch, json, pathlib, sys, time
torch.set_num_threads(1)
from learn import confirm_run as CR, direc as D, song_settings as SS, knob_ceiling as K
from learn.direc_check import eq_to, to_lufs
ps, fo = K.parts(), SS.folds()
avg = {f: np.load(SS.MODELS / "cache" / f"average-fold{f}.npy") for f in range(4)}
OUT = pathlib.Path.home() / "ndsp-presets/learn/local-objective/rebuilt-ref"
parts = sorted(p.stem for p in OUT.glob("*.npy"))
nets = {}
for slug in parts:
    f = fo[ps[slug]["band"]]
    stored = np.load(OUT / f"{slug}.npy")
    ref = CR.mono(ps[slug]["crop"] / "reference.wav").astype(np.float32)
    stem_rb = np.load(SS.OUT / "rebuilt" / f"{slug}.npy")
    res = {}
    for g in (f, (f + 1) % 4):
        if g not in nets: nets[g] = D.load_model(SS.cprime(g)).eval()
        t = time.time()
        x = D.rebuild(nets[g], ref, device=torch.device("cpu")).astype(np.float64)
        y = to_lufs(eq_to(x, avg[2] - avg[g]))
        n = min(len(y), len(stored))
        res[g] = (float(np.max(np.abs(y[:n] - stored[:n]))), float(np.corrcoef(y[:n], stored[:n])[0, 1]), round(time.time() - t, 1))
    n = min(len(stored), len(stem_rb))
    print(slug, "own fold", f, res, "corr stored vs stem-rebuild", round(float(np.corrcoef(stored[:n], stem_rb[:n])[0, 1]), 4), flush=True)
