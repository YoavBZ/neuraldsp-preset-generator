from common import *
import random, collections
U = raw_units()
keep = {k for k, u in U.items() if ok(u["d"]["A"]) and ok(u["d"]["S-mics"])}
assert len(keep) == 142
CANDS = ["S", "C-blend", "B-blend", "menu_pick", "3-C'", "A", "S-mics", "shrink-0.5", "shrink-0.25", "shrink-0.75", "3-C'+shrink-0.5"]
for k in keep: U[k]["d"].setdefault("menu_pick", None)
# menu_pick from the readout's source (label-table flat), as the reports use
for k in keep:
    slug, amp, search = k
    p = J(SSO / "menupick" / slug / "result.json")[amp]["pick"][search]
    U[k]["d"]["menu_pick"] = J(H / "label-table" / slug / "menu.json")[amp][p]["flat"][U[k]["held"]]
def lr(c, keys=keep, ref="S"): return logrows(U, c, ref, keys)
if 0: print("== paired differences (band-weighted, 90% band t), part-weighted CI, bands better/worse, LOBO range")
for a, b in [("3-C'", "A"), ("shrink-0.5", "A"), ("shrink-0.75", "A"), ("3-C'+shrink-0.5", "S"), ("3-C'+shrink-0.5", "3-C'"),
             ("3-C'+shrink-0.5", "A"), ("3-C'+shrink-0.5", "shrink-0.5"), ("3-C'", "S"), ("A", "S"), ("shrink-0.5", "S"), ("shrink-0.75", "S")]:
    r = bw(lr(a, ref=b)); pc = r["part_ci"]
    bm = r["band_means"].values()
    print(f"{a:16s} - {b:11s} {fmt(r)}  part {pc[0]:+.3f} [{pc[1]:+.3f},{pc[2]:+.3f}]  bands -/+ {sum(v<0 for v in bm)}/{sum(v>0 for v in bm)}  LOBO [{min(r['lobo']):+.3f},{max(r['lobo']):+.3f}]")
print("\n== per direction (search half) vs S")
for c in CANDS[1:]:
    out = []
    for s in "AB":
        out.append(bw(lr(c, {k for k in keep if k[2] == s})))
    print(f"{c:16s} search A/held B {out[0]['mean']:+.3f} [{out[0]['lo']:+.3f},{out[0]['hi']:+.3f}]   search B/held A {out[1]['mean']:+.3f} [{out[1]['lo']:+.3f},{out[1]['hi']:+.3f}]")
print("\n== cross-fitted choice: pick the best mean on one direction, score it on the other")
for s, t in (("A", "B"), ("B", "A")):
    ms = {c: bw(lr(c, {k for k in keep if k[2] == s}))["mean"] for c in CANDS}
    best = min(ms, key=ms.get)
    r = bw(lr(best, {k for k in keep if k[2] == t}))
    print(f"chosen on search-{s}: {best} ({ms[best]:+.3f}); on search-{t}: {r['mean']:+.3f} [{r['lo']:+.3f},{r['hi']:+.3f}]")
print("\n== leave-one-band-out choice: best on 13 bands, scored on the 14th")
bands = sorted({U[k]["band"] for k in keep}); picks = collections.Counter(); held = []
for b in bands:
    tr = {k for k in keep if U[k]["band"] != b}; te = {k for k in keep if U[k]["band"] == b}
    ms = {c: bw(lr(c, tr))["mean"] for c in CANDS}
    best = min(ms, key=ms.get); picks[best] += 1
    held.append(bw(lr(best, te))["mean"])
print("picks", dict(picks)); m, lo, hi = tci(held); print(f"held-out band mean of the chosen {m:+.3f} [{lo:+.3f},{hi:+.3f}]")
for c in ("A", "3-C'", "shrink-0.5", "3-C'+shrink-0.5"):
    print(f"  (fixed {c}: {bw(lr(c))['mean']:+.3f})")
print("\n== band bootstrap: how often each candidate has the lowest band-weighted mean (2000 draws)")
rng = random.Random(1); per = {c: bw(lr(c))["band_means"] for c in CANDS}; wins = collections.Counter()
for _ in range(2000):
    bs = [rng.choice(bands) for _ in bands]
    wins[min(CANDS, key=lambda c: statistics.fmean(per[c][b] for b in bs))] += 1
print({c: round(v / 2000, 3) for c, v in wins.most_common()})
print("\n== refused directions scored as the worst (the 2 dropped: A, S-mics, 3-C' silent at volume 0)")
for worst in (math.log(2), None):
    rows = {}
    for c in ("A", "3-C'", "shrink-0.5", "3-C'+shrink-0.5", "shrink-0.75", "S-mics"):
        r = {}
        allk = keep | {k for k in U if k not in keep}
        mx = max(v for _, v in lr(c).values())
        for k in allk:
            x, y = U[k]["d"].get(c), U[k]["d"]["S"]
            r[k] = (U[k]["band"], math.log(x / y) if ok(x) else (worst if worst is not None else mx))
        rows[c] = bw(r)
    print("refused =", "log 2" if worst else "that candidate's worst observed", {c: f"{v['mean']:+.3f} [{v['lo']:+.3f},{v['hi']:+.3f}]" for c, v in rows.items()})
