from common import *
from learn import arm_a_levers as L
MS = L.menu_S(); bad = 0
for slug, amp, search, held in CELLS:
    stored, x = L.stored_a(slug, amp, search)
    S = MS[amp][PS[slug]["gain_class"]][1]
    rep = L.replay_arm_a(amp, S, stored)
    m = L.replay_mismatches(rep, stored, x)
    E = L._settings(LV / "early" / "C'" / slug / amp / f"{search}.json")
    if m or rep["main_x"] != E: bad += 1; print(slug, amp, search, m)
    # main-stage best must be the min over the first 52 objective values and its settings the arg-min
    i = min(range(52), key=lambda j: stored["objective_curve"][j])
print("re-run replay mismatches:", bad)
