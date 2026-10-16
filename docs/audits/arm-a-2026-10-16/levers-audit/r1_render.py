"""<= 40 Morgan renders, one process, CPU: reproduce stored judges and the 3-C' objective."""
from common import *
import random, numpy as np
from learn import arm_a_levers as L
from learn import confirm_run as CR
CAP = 40
U = raw_units()
keep = sorted(k for k, u in U.items() if ok(u["d"]["A"]) and ok(u["d"]["S-mics"]))
pick = random.Random(99).sample(keep, 5)
rr = K.Renderer(); guard = L.SwapGuard(); out = []
def R(*a):
    if rr.count >= CAP: raise SystemExit("cap")
    guard.check(); return rr.render(*a)
try:
    menu = rr.menu()
    for slug, amp, search in pick:
        held = U[(slug, amp, search)]["held"]; part = PS[slug]
        di = K.measure_di(part); di32 = di.astype(np.float32); ref = CR.mono(part["crop"] / "reference.wav")
        sel, S = menu[amp][K.START[part["gain_class"]][amp]]
        rb = np.load(SSO / "rebuilt" / f"{slug}.npy"); stem = SS.stem(slug)
        R(di32, sel, S)                                                    # warm-up
        x3 = L._settings(LV / "early" / "C'" / slug / amp / f"{search}.json")
        main_best = J(LV / "replay" / "armA" / slug / amp / f"{search}-main.json")["main_best"]
        ctr = {"fallback": 0}
        obj = SS.rebuilt_objective(stem, R(rb.astype(np.float32), sel, x3), rb, search, ctr)
        rec = {"dir": (slug, amp, search), "3C_obj_search_half": (obj, main_best, math.log(obj / main_best))}
        for tag, path, name in (("3-C'", LV / "early" / "C'", None), ("3C+s0.5", LV / "early" / "lever-shrink-0.5", None),
                                ("shrink-0.5", LV / "exp1", "shrink-0.5")):
            f = J(path / slug / amp / f"{search}.json")
            x = L._settings_dict(f["settings"][name] if name else f["settings"])
            j = K.judge(ref, R(di32, sel, x), di, part["judge_lag"])
            st = f["judge"][name] if name else f["judge"]
            rec[tag] = {h: (j[h], st[h], math.log(j[h] / st[h]) if ok(j[h]) and ok(st[h]) else None) for h in "AB"}
        out.append(rec); print(rec, rr.count, flush=True)
finally:
    rr.close()
print("renders", rr.count)
J  # noqa
import json; open("r1_out.json", "w").write(json.dumps(out, indent=1, default=str))
