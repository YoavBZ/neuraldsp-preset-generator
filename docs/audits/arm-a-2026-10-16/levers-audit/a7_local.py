from common import *
from scipy.stats import spearmanr
import numpy as np
from learn import arm_a_levers as L
nets = ("C'", "1z", "1a", "1b")
cells = sorted(p.stem for p in (LV / "local" / "C'").glob("*.json"))
traj = {(p.parent.name, p.stem): J(p)["trajectory"] for p in (LV / "replay" / "ks").glob("*/*.json")}
# sanity: first trajectory point of each direction is S and its true d equals the knob-ceiling menu start
for (slug, amp), t in traj.items():
    r = kc(slug, amp); s = r["menu"][r["start"]]
    firsts = [d for x, d in t if all(abs(math.log(d[h] / s[h])) < 0.005 for h in "AB")]
    assert firsts, (slug, amp)
draws = L.local_draw({k: [(L._settings_dict(x), d) for x, d in v] for k, v in traj.items()})
rows = {c: {} for c in (*nets, "E4")}; diag = []
for cell in cells:
    slug, amp = cell.rsplit("-", 1); band = PS[slug]["band"]
    pts = {n: J(LV / "local" / n / f"{cell}.json")["points"] for n in nets}
    # the stored points are the draw, in order
    assert [p["true"] for p in pts["C'"]] == [d for _, d in draws[(slug, amp)]]
    for c in rows:
        fs = []
        for h in "AB":
            true = [p["true"][h] for p in pts["C'"]]
            if c == "E4":
                o = [statistics.fmean(math.log(pts[n][i]["obj"][h]) for n in nets) for i in range(len(true))]
            else:
                o = [pts[c][i]["obj"][h] for i in range(len(true))]
            fs.append(spearmanr(o, true).correlation)
        rows[c][(slug, amp, "-")] = (band, statistics.fmean(fs))
    tA = [p["true"]["A"] for p in pts["C'"]]; tB = [p["true"]["B"] for p in pts["C'"]]
    oA = [p["obj"]["A"] for p in pts["C'"]]; oB = [p["obj"]["B"] for p in pts["C'"]]
    diag.append((cell[:30], len(tA), round(spearmanr(tA, tB).correlation, 2), round(spearmanr(oA, oB).correlation, 2),
                 round(float(np.std(np.log(tA))), 3), round(float(np.std(np.log(oA))), 3), round(rows["C'"][(slug, amp, "-")][1], 2)))
for c, r in rows.items(): print(c, "local fidelity", fmt(bw(r)))
print("cell, n, rho(trueA,trueB), rho(objA,objB), sd log true, sd log obj, C' local fid")
for d in diag: print(*d)
