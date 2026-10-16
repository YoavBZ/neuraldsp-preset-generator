from common import *
from scipy.stats import spearmanr
f3 = sorted(s for s in PS if s != "telefunken-Honey-GTR" and FOLDS[PS[s]["band"]] == 3)
U = raw_units()
def obj(net, slug, amp, h):
    if net == "C'":
        return {n: v[h] for n, v in J(SSO / "menupick" / slug / "result.json")[amp]["scores"].items()}
    r = J(LV / "exp2" / net / f"{slug}.json"); assert r["delta"] == 0
    for v in r["menu"][amp]["scores"].values(): assert set(v) == {"-52"}
    return {n: v["-52"][h] for n, v in r["menu"][amp]["scores"].items()}
def ens(slug, amp, h):
    ms = [obj(n, slug, amp, h) for n in ("C'", "1z", "1a", "1b")]
    names = set.intersection(*[set(m) for m in ms])
    return {n: (statistics.fmean(math.log(m[n]) for m in ms) if all(ok(m[n]) for m in ms) else math.inf) for n in names}
rows = {c: {} for c in ("C'", "1z", "1a", "1b", "E4")}; npres = []; fb = {}
for slug in f3:
    for amp in K.AMPS:
        menu = kc(slug, amp)["menu"]
        for search, held in K.DIRECTIONS:
            k = (slug, amp, search)
            if k not in U or not all(ok(U[k]["d"].get(m)) for m in ("S", "A")): continue   # the 142
            for c in rows:
                o = ens(slug, amp, search) if c == "E4" else obj(c, slug, amp, search)
                names = [n for n in o if n in menu and math.isfinite(o[n]) and ok(menu[n][search])]
                npres.append(len(names))
                rows[c][k] = (PS[slug]["band"], spearmanr([o[n] for n in names], [menu[n][search] for n in names]).correlation)
for c, r in rows.items():
    b = bw(r); print(c, "fidelity", fmt(b), "part-CI", tuple(round(x, 3) for x in b["part_ci"]))
for c in ("1z", "1a", "1b", "E4"):
    d = {k: (rows[c][k][0], rows[c][k][1] - rows["C'"][k][1]) for k in rows[c]}
    b = bw(d); print(c, "- C'", fmt(b), "part-CI", tuple(round(x, 3) for x in b["part_ci"]), "LOBO", [round(x, 3) for x in b["lobo"]])
print("presets per fidelity: min", min(npres), "max", max(npres), "menu sizes", {a: len(kc(f3[0], a)["menu"]) for a in K.AMPS})
for net in ("1z", "1a", "1b"):
    print(net, "fallbacks", sum(J(LV / "exp2" / net / f"{s}.json")["menu"][a]["fallback"] for s in f3 for a in K.AMPS))
print("C' fallbacks", sum(J(SSO / "menupick" / s / "result.json")[a]["fallback"] for s in f3 for a in K.AMPS))
print("repeat", {p.stem[:20]: round(max(J(p)["dev"].values()), 5) for p in (LV / "exp2" / "repeat").glob("*.json")})
