from common import *
U = raw_units()
print("cells", len(CELLS), "units", len(U))
dec = ["S", "K_S", "A", "menu_pick", "B", "C", "S-mics", "shrink-0.5", "shrink-0.25", "shrink-0.75", "B-blend", "C-blend"]
bad = {k: [m for m, v in u["d"].items() if not ok(v)] for k, u in U.items()}
bad = {k: v for k, v in bad.items() if v}
print("non-finite per direction:", bad)
keep = {k for k in U if k not in bad or set(bad[k]) <= {"3-C'+shrink-0.5", "dirs-avg"}}
print("kept", len(keep))
for c in ["A", "shrink-0.25", "shrink-0.5", "shrink-0.75", "S-mics", "B-blend", "C-blend", "3-C'", "3-C'+shrink-0.5"]:
    print(f"{c:16s} vs S", fmt(bw(logrows(U, c, "S", keep))))
for c in ["shrink-0.75", "shrink-0.5", "shrink-0.25", "S-mics", "3-C'", "3-C'+shrink-0.5"]:
    print(f"{c:16s} vs A", fmt(bw(logrows(U, c, "A", keep))))
print("3-C'+s0.5 vs 3-C'", fmt(bw(logrows(U, "3-C'+shrink-0.5", "3-C'", keep))))
