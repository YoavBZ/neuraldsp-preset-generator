from common import *
import collections
bad = collections.Counter(); nr = []; same_as_A = 0; ks_dist = []
MS = J(SSO / "armB" / "menu-S.json")
for slug, amp, search, held in CELLS:
    a = J(SSO / "armA" / slug / amp / f"{search}.json")
    r = J(LV / "replay" / "armA" / slug / amp / f"{search}-main.json")
    st_ = a["stages"]["main"]; c = a["objective_curve"]
    if r["main_best"] != st_["best"]: bad["main_best != stored stage best"] += 1
    if r["main_renders"] != st_["renders"]: bad["renders"] += 1
    if min(c[:st_["renders"]]) != st_["best"]: bad["curve min != stage best"] += 1
    nr.append(st_["renders"])
    A = J(SSO / "armA" / slug / amp / f"{search}-settings.json")
    same_as_A += (r["settings"] == A)
    e = J(LV / "early" / "C'" / slug / amp / f"{search}.json")
    if e["held"] != held: bad["held"] += 1
print(dict(bad), "main renders: min", min(nr), "max", max(nr), "| 3-C' identical to full A on", same_as_A, "/144")
