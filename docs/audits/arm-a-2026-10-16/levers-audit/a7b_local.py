from common import *
from scipy.stats import spearmanr
import numpy as np
nets = ("C'", "1z", "1a", "1b")
cells = sorted(p.stem for p in (LV / "local" / "C'").glob("*.json"))
def sp(o, t, mode):
    pairs = [(a, b) for a, b in zip(o, t) if math.isfinite(a) and ok(b)] if mode == "pairwise" else list(zip(o, t))
    return spearmanr(*zip(*pairs)).correlation, len(pairs)
for mode in ("pairwise", "inf-as-worst"):
    rows = {c: {} for c in (*nets, "E4")}; info = []
    for cell in cells:
        slug, amp = cell.rsplit("-", 1); band = PS[slug]["band"]
        pts = {n: J(LV / "local" / n / f"{cell}.json")["points"] for n in nets}
        for c in rows:
            fs = []
            for h in "AB":
                true = [p["true"][h] for p in pts["C'"]]
                if c == "E4":
                    o = [statistics.fmean(math.log(pts[n][i]["obj"][h]) for n in nets) if all(ok(pts[n][i]["obj"][h]) for n in nets) else math.inf for i in range(len(true))]
                else:
                    o = [pts[c][i]["obj"][h] for i in range(len(true))]
                r, m = sp(o, true, mode); fs.append(r)
                if c == "C'": info.append((cell[:28], h, m, sum(not ok(x) for x in true), sum(not math.isfinite(x) for x in o), round(r, 2)))
            rows[c][(slug, amp, "-")] = (band, statistics.fmean(fs))
    print(mode, {c: round(bw(r)["mean"], 3) for c, r in rows.items()})
    if mode == "pairwise":
        for c, r in rows.items(): print(" ", c, fmt(bw(r)), "band means", {b[:6]: round(v, 3) for b, v in bw(r)["band_means"].items()})
        print("cell half n_finite n_true_inf n_obj_inf rho")
        for i in info: print(" ", *i)
