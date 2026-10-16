from common import *
from scipy.stats import spearmanr
from learn import arm_a_levers as L
import collections
traj = {(p.parent.name, p.stem): J(p)["trajectory"] for p in (LV / "replay" / "ks").glob("*/*.json")}
draws = L.local_draw({k: [(L._settings_dict(x), d) for x, d in v] for k, v in traj.items()})
MS = L.menu_S(); tally = collections.defaultdict(list)
for (slug, amp), dr in sorted(draws.items()):
    pts = J(LV / "local" / "C'" / f"{slug}-{amp}.json")["points"]
    S = MS[amp][PS[slug]["gain_class"]][1]
    for d in K.space(amp, S):
        if d.kind not in ("cont",): continue
        xs = [L.unit(d, x) for x, _ in dr]
        if len(set(xs)) < 4: continue
        for h in "AB":
            keep = [i for i in range(len(xs)) if ok(pts[i]["obj"][h]) and ok(pts[i]["true"][h])]
            rt = spearmanr([xs[i] for i in keep], [pts[i]["true"][h] for i in keep]).correlation
            ro = spearmanr([xs[i] for i in keep], [pts[i]["obj"][h] for i in keep]).correlation
            tally[d.key].append((rt, ro))
for k, v in sorted(tally.items()):
    agree = sum((a > 0) == (b > 0) for a, b in v if abs(a) > 0.3)
    strong = sum(abs(a) > 0.3 for a, b in v)
    print(f"{k:22s} n={len(v):2d} mean rho(dim,true) {statistics.fmean(a for a,b in v):+.2f} mean rho(dim,obj) {statistics.fmean(b for a,b in v):+.2f}  sign agrees where |rho_true|>0.3: {agree}/{strong}")
