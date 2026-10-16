from common import *
from collections import Counter
MS = J(SSO / "armB" / "menu-S.json")
def Sof(slug, amp): return MS[amp][PS[slug]["gain_class"]]["settings"]
def u(d, x):
    v = x.get(d.name); v = d.lo if v is None else float(v)
    v = min(max(v, d.lo), d.hi); return (v - d.lo) / (d.hi - d.lo)
issues = Counter(); maxerr = Counter(); n = 0; missing = Counter(); moved = Counter()
def check(name, V, S, A, lam, cats_src, sw_src, A2=None):
    global n
    dims = K.space(name[1], {tuple(k.rsplit("/", 1)): v for k, v in S.items()})
    inside = {d.name for d in dims}
    for k in set(V) | set(S):
        if k not in inside and V.get(k) != S.get(k): issues[(name[0], "outside differs")] += 1
    for k in set(A) | set(S):
        if k not in inside and A.get(k) != S.get(k): issues[(name[0], "A differs from S outside")] += 1
    for d in dims:
        for src in (S, A): 
            if d.name not in src: missing[d.name] += 1
        if d.kind == "cat":
            if V.get(d.name) != cats_src.get(d.name): issues[(name[0], "mic")] += 1
        elif d.kind == "switch":
            if V.get(d.name) != sw_src.get(d.name): issues[(name[0], "switch")] += 1
        else:
            tgt = (u(d, A) + u(d, A2)) / 2 if A2 is not None else u(d, S) + lam * (u(d, A) - u(d, S))
            e = abs(u(d, V) - tgt); maxerr[name[0]] = max(maxerr[name[0]], e)
            if e > 2e-5: issues[(name[0], f"cont {d.name}")] += 1
            if abs(u(d, A) - u(d, S)) > 1e-9: moved[name[0]] += 1
    n += 1
for slug, amp, search, held in CELLS:
    S = Sof(slug, amp)
    A = J(SSO / "armA" / slug / amp / f"{search}-settings.json")
    A2 = J(SSO / "armA" / slug / amp / f"{held}-settings.json")
    P = J(SSO / "armB" / "predictions.json")["cells"][f"{slug}|{amp}|{search}"]
    B, C = P["B"]["settings"], P["constant"]["settings"]
    V = J(LV / "exp1" / slug / amp / f"{search}.json")["settings"]
    for lam in (0.25, 0.5, 0.75): check((f"shrink-{lam}", amp), V[f"shrink-{lam}"], S, A, lam, A, A)
    check(("S-mics", amp), V["S-mics"], S, A, 1.0, S, A)
    check(("dirs-avg", amp), V["dirs-avg"], S, A, None, A, A, A2)
    check(("B-blend", amp), V["B-blend"], S, B, 0.5, S, S)
    check(("C-blend", amp), V["C-blend"], S, C, 0.5, S, S)
    E = J(LV / "early" / "C'" / slug / amp / f"{search}.json")["settings"]
    M = J(LV / "replay" / "armA" / slug / amp / f"{search}-main.json")["settings"]
    if E != M: issues[("3-C'", "judged settings != replay main settings")] += 1
    L = J(LV / "early" / "lever-shrink-0.5" / slug / amp / f"{search}.json")["settings"]
    check(("3C+shrink-0.5", amp), L, S, E, 0.5, E, E)
print("checks", n); print("issues", dict(issues)); print("max unit err", dict(maxerr)); print("missing keys in S or A", dict(missing))
print("dims moved", dict(moved))
# do mics/switches of A differ from S, how often?
mic = sw = 0
for slug, amp, search, held in CELLS:
    S = Sof(slug, amp); A = J(SSO / "armA" / slug / amp / f"{search}-settings.json")
    dims = K.space(amp, {tuple(k.rsplit("/", 1)): v for k, v in S.items()})
    mic += any(A.get(d.name) != S.get(d.name) for d in dims if d.kind == "cat")
    sw += any(A.get(d.name) != S.get(d.name) for d in dims if d.kind == "switch")
print("A changes a mic on", mic, "/144; a switch on", sw)
