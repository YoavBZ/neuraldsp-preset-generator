"""How far is each stem from its amp track? Cheap CPU diagnostics, against per-part DI-alone effects."""
import json, math, pathlib, sys, collections
import numpy as np, soundfile as sf
from scipy import stats, signal

WT = "/Users/yoavbz/projects/neuraldsp-preset-generator/.claude/worktrees/bridge-cse_01TcpCZvuiya2xZxn5XRQ6PT"
sys.path.insert(0, WT); sys.path.insert(0, WT + "/research")
from learn import songs_check as SC
HERE = pathlib.Path(__file__).parent
P = json.load(open(HERE / "parts.json")); SCP = SC.parts()
d = json.load(open(HERE / "per_cell_None.json"))

def mono(p):
    x, sr = sf.read(str(p), dtype="float64"); return x.mean(1) if x.ndim == 2 else x

def frames_db(x, n=2048):
    k = len(x) // n
    e = (x[:k * n].reshape(k, n) ** 2).mean(1)
    return 10 * np.log10(e + 1e-12)

def logmel(x, n=4096):
    f, t, S = signal.stft(x, 48000, nperseg=n, noverlap=n * 3 // 4)
    S = np.abs(S) ** 2
    edges = np.geomspace(80, 12000, 33)
    B = np.stack([S[(f >= lo) & (f < hi)].sum(0) for lo, hi in zip(edges[:-1], edges[1:])])
    return 10 * np.log10(B + 1e-12)

rows = []
for slug in sorted({c.split("|")[0] for c in d}):
    st = mono(SCP[slug]["stem"]); ref = mono(pathlib.Path(P[slug]["crop"]) / "reference.wav")
    n = min(len(st), len(ref)); st, ref = st[:n], ref[:n]
    st, ref = st / np.sqrt((st ** 2).mean()), ref / np.sqrt((ref ** 2).mean())
    a, b = frames_db(st), frames_db(ref)
    env_r = float(np.corrcoef(a, b)[0, 1])
    quiet = b < b.max() - 30
    leak = float(np.mean(a[quiet]) - np.mean(a[~quiet])) if quiet.any() else float("nan")
    # spectral-envelope difference over frames where the reference plays
    A, Bm = logmel(st), logmel(ref)
    act = Bm.mean(0) > Bm.mean(0).max() - 30
    spec = float(np.mean(np.abs((A[:, act] - A[:, act].mean()) - (Bm[:, act] - Bm[:, act].mean()))))
    resid = float(10 * np.log10(np.mean((st - ref) ** 2) / np.mean(ref ** 2)))  # waveform residual (same timeline)
    cells = [v for c, v in d.items() if c.startswith(slug + "|")]
    f = lambda cfg: np.mean([v[cfg]["cross"] for v in cells])
    cur, dec, cref = f("cprime|stem|native|own"), f("measure|stem|native|own"), f("cprime|reference|native|own")
    ceil = np.mean([v["_ceiling"]["cross"] for v in cells])
    rows.append((slug, P[slug]["band"], env_r, leak, spec, resid, cur, dec, cref, ceil))
    print(f"{slug[:38]:38s} envr {env_r:.3f} quietfrac {quiet.mean():.2f} leak {leak:+6.1f} spec {spec:5.2f} resid {resid:+6.1f}dB | cur {cur:+.2f} dec {dec:+.2f} cref {cref:+.2f} ceil {ceil:+.2f}", flush=True)

R = np.array([r[2:] for r in rows])
names = ["env_r", "leak", "spec", "resid"]
for j, nm in enumerate(names):
    for k, tg in ((5, "decisive"), (5 + 1, "DI-alone"), (6, "C'/ref")):
        pass
for j, nm in enumerate(names):
    dec, cur, cref = R[:, 5], R[:, 4], R[:, 6]
    print(nm, "Spearman vs decisive %.2f  vs DI-alone(dec-cur) %.2f  vs current %.2f  vs ref-alone(cref-cur) %.2f" % (
        stats.spearmanr(R[:, j], dec).correlation, stats.spearmanr(R[:, j], dec - cur).correlation,
        stats.spearmanr(R[:, j], cur).correlation, stats.spearmanr(R[:, j], cref - cur).correlation))
