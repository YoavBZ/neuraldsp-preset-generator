"""N2 (`docs/pipeline-fix-plan.md`, ledger `phase_night2`): search v2 on the BKS replicate pairs.

    $MAIN -m learn.night2 search --shard k/n                # v2 on the replicate pairs, one amp each
    $MAIN -m learn.night2 report                            # replicate rms and held gain, v2 against the stored labels
    $MAIN -m learn.night2 hold                              # N1's FTh: FT's answers, controls outside the search at S
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import re
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

PHASE = "phase_night2"
OUT = "night2"
SEED = 20261108
LIMIT = 44                            # evaluations a search at most, S included
FLOOR = 0.005                         # the least log gain a move must bring
STEPS = (0.25, 0.125)
MICS_KEPT = 4                         # candidate mics per side, each amp's commonest in GOAT's labels
BOOT_N = 5000
DRIVE = ("inputGain", "pr12Volume", "sw50rVolume", "sw50rLevel", "ac20Volume", "ac20Power")


# --- pure functions (unit-tested) ------------------------------------------------------------------------------------

def group(key):
    """A searched control's group: drive, tone, mic or cab."""
    if key in DRIVE:
        return "drive"
    if key.endswith("MicType"):
        return "mic"
    return "tone" if key.startswith(("pr12", "sw50r", "ac20")) else "cab"


def unit_of(d, v):
    """A stored value in [0, 1] on dim d (log dims log-spaced, clipped)."""
    v = min(max(float(v), d.lo), d.hi)
    return math.log(v / d.lo) / math.log(d.hi / d.lo) if d.kind == "log" else (v - d.lo) / (d.hi - d.lo)


def replicate_pairs(recs, seed=SEED):
    """Near-replicates: half B of a section at t and half A of the same rig's section at t + 5 share 4 of 4.5 s. One amp per
    section pair, balanced and seeded. recs: [{unit, rig, amp, search, ...}]. -> [(record, record)]."""
    def start(u):
        return float(re.search(r"@([0-9.]+)#", u).group(1))

    by = {}
    for r in recs:
        by.setdefault((r["rig"], r["amp"]), {})[(start(r["unit"]), r["search"])] = r
    sections = {}
    for (rig, amp), got in by.items():
        for (t, h), r in got.items():
            if h == "B" and (t + 5.0, "A") in got:
                sections.setdefault((rig, t), {})[amp] = (r, got[(t + 5.0, "A")])
    rng = random.Random(f"{seed}|pairs")
    out, count = [], {}
    keys = sorted(sections)
    rng.shuffle(keys)
    for k in keys:
        amps = sorted(sections[k], key=lambda a: (count.get(a, 0), a))
        a = amps[0]
        count[a] = count.get(a, 0) + 1
        out.append(sections[k][a])
    return out


def order_dims(dims):
    """v2's order: drive, tone, then cab; the mics apart."""
    rank = {"drive": 0, "tone": 1, "cab": 2}
    main = [d for d in dims if group(d.key) != "mic"]
    return sorted(main, key=lambda d: (rank[group(d.key)], d.key)), [d for d in dims if group(d.key) == "mic"]


def search_v2(dims, x0, f, mics, fmt, limit=LIMIT, floor=FLOOR, steps=STEPS):
    """Search v2: from x0, drive and tone at the first step, then a short mic list, the knobs of drive and tone at the finer
    step, then cab at the first step, until `limit` evaluations. A move stays only if it brings a log gain of `floor` or
    more; a silent render never does. f(x) -> distance, inf when silent. mics: {key: [candidate values]}.
    -> (best x, best value, evaluations)."""
    main, mic = order_dims(dims)
    x, best, n = dict(x0), f(dict(x0)), 1
    seen = {tuple(sorted(x.items()))}

    def trial(k, v):
        nonlocal x, best, n
        y = dict(x)
        y[k] = v
        t = tuple(sorted(y.items()))
        if t in seen or n >= limit:
            return
        seen.add(t)
        val = f(y)
        n += 1
        if math.isfinite(val) and val > 0 and math.log(best / val) >= floor:
            x, best = y, val

    def sweep(ds, step, switches=True):
        for d in ds:
            k = (d.module, d.key)
            if d.kind == "switch":
                for v in d.values if switches else ():
                    if v != x.get(k):
                        trial(k, v)
                continue
            u = unit_of(d, x.get(k, d.lo))
            for s in (step, -step):
                w = min(1.0, max(0.0, u + s))
                if w != u:
                    trial(k, fmt(d.from_unit(w)))

    near = [d for d in main if group(d.key) in ("drive", "tone")]
    cab = [d for d in main if group(d.key) == "cab"]
    sweep(near, steps[0])
    for d in mic:
        k = (d.module, d.key)
        for v in mics.get(d.key, []):
            if v != x.get(k):
                trial(k, v)
    sweep(near, steps[1], False)
    sweep(cab, steps[0])
    return x, best, n


def boot_mean(rows, n=BOOT_N, seed=SEED):
    """Mean of cluster means with a 90% percentile interval over clusters resampled. rows: [(cluster, x)]."""
    by = {}
    for c, x in rows:
        by.setdefault(c, []).append(x)
    means = [sum(v) / len(v) for v in by.values()]
    rng = random.Random(f"{seed}|boot")
    d = sorted(sum(rng.choices(means, k=len(means))) / len(means) for _ in range(n))
    return {"mean": sum(means) / len(means), "lo90": d[int(0.05 * n)], "hi90": d[int(0.95 * n) - 1], "clusters": len(means)}


# --- the commands ----------------------------------------------------------------------------------------------------

def root():
    from learn import pipeline_fix as P

    return P.out_dir() / OUT


def mic_lists(recs):
    """Each amp's commonest mics per side in GOAT's labels. -> {amp: {key: [values]}}."""
    from collections import Counter

    c = {}
    for r in recs:
        for k, v in r["label"].items():
            if k.endswith("MicType"):
                c.setdefault(r["amp"], {}).setdefault(k.rsplit("/", 1)[1], Counter())[v] += 1
    return {a: {k: [v for v, _ in n.most_common(MICS_KEPT)] for k, n in d.items()} for a, d in c.items()}


def cmd_search(args):
    """N2: v2 on both members of each replicate pair, from S on the stored lag, S's first evaluation checked against the
    stored render. -> night2/search/<unit>|<amp>.json."""
    import numpy as np

    from learn import arm_a_levers as L
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    P.require(PHASE)
    recs, by_unit, _ = P.real_labels(2)
    pairs = replicate_pairs(recs)
    todo = sorted({(r["unit"], r["amp"]) for p in pairs for r in p})
    grecs, _, _ = P.goat_labels()
    mics = mic_lists(grecs)
    k, n = (int(x) for x in args.shard.split("/"))
    mine = [t for j, t in enumerate(todo) if j % n == k]
    rec_of = {(r["unit"], r["amp"]): r for r in recs}
    ms = L.menu_S()
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    for u, amp in mine:
        path = root() / "search" / f"{u.replace('/', '__')}|{amp}.json"
        if path.exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        r, prt = rec_of[(u, amp)], by_unit[u]
        sel, S = ms[amp][prt["cls"]]
        dims = K.space(amp, S)
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        seen, order = {}, []
        rr = CB.new_renderer()
        try:
            rr.render(di32, sel, LO.tdict(LO.sdict(S)))           # the discarded priming render
            renders += 1

            def f(x):
                y = np.asarray(rr.render(di32, sel, LO.tdict(LO.sdict(x))), np.float64)[trim[0]:trim[1]]
                j = K.judge(ref, y, di, r["lag"])
                if not order and AM.audio_sha(y) != r["s_render_sha256"]:
                    raise SystemExit(f"{u} {amp}: S's first evaluation is not the stored render")
                order.append(1)
                seen[K.key(x)] = j
                return j[r["search"]]

            x, best, evals = search_v2(dims, S, f, mics[amp], K.fmt)
            renders += evals
        finally:
            rr.close()
        P.save(path, {"unit": u, "amp": amp, "rig": r["rig"], "di": r["di"], "search": r["search"], "held": r["held"],
                      "cls": r["cls"], "evaluations": evals, "label": LO.sdict(x), "judge": seen[K.key(x)],
                      "s_judge": r["s_judge"], "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{u[-50:]}|{amp}: renders so far {renders}", flush=True)
    print(f"NIGHT2-SEARCH DONE {k}/{n}: {renders} renders")


def rms(diffs):
    return math.sqrt(sum(d * d for d in diffs) / len(diffs)) if diffs else None


def cmd_report(_args):
    """N2's reads: replicate rms by group, v1 (stored) and v2, on the same pairs; the held-half gain of each."""
    from learn import arm_a_levers as L
    from learn import knob_ceiling as K
    from learn import pipeline_fix as P

    P.require(PHASE)
    recs, _, _ = P.real_labels(2)
    pairs = replicate_pairs(recs)
    ms = L.menu_S()
    v2 = {}
    for q in (root() / "search").glob("*.json"):
        d = json.loads(q.read_text())
        v2[(d["unit"], d["amp"])] = d
    want = {(r["unit"], r["amp"]) for p in pairs for r in p}
    if want - set(v2):
        raise SystemExit(f"{len(want - set(v2))} of {len(want)} directions have no v2 search yet")
    diffs = {"v1": {}, "v2": {}}
    for a, b in pairs:
        if (a["unit"], a["amp"]) not in v2 or (b["unit"], b["amp"]) not in v2:
            continue
        S = ms[a["amp"]][a["cls"]][1]
        for d in K.space(a["amp"], S):
            if d.kind not in ("cont", "log"):
                continue
            k = f"{d.module}/{d.key}"
            for tag, (x, y) in (("v1", (a["label"], b["label"])), ("v2", (v2[(a["unit"], a["amp"])]["label"], v2[(b["unit"], b["amp"])]["label"]))):
                if k in x and k in y:
                    diffs[tag].setdefault(group(d.key), []).append(unit_of(d, x[k]) - unit_of(d, y[k]))
    gain = {"v1": [], "v2": [], "v2_minus_v1": []}
    silent, moved = 0, {"v1": [], "v2": []}
    for a, b in pairs:
        for r in (a, b):
            d = v2[(r["unit"], r["amp"])]
            S = ms[r["amp"]][r["cls"]][1]
            for dim in K.space(r["amp"], S):
                k = (dim.module, dim.key)
                if dim.kind in ("cont", "log") and k in S:
                    q = f"{dim.module}/{dim.key}"
                    u0 = unit_of(dim, S[k])
                    moved["v1"].append((unit_of(dim, r["label"][q]) - u0) ** 2)
                    moved["v2"].append((unit_of(dim, d["label"][q]) - u0) ** 2)
            s = r["s_judge"][r["held"]]
            if not (math.isfinite(r["best"]["judge"][r["held"]]) and math.isfinite(d["judge"][r["held"]])):
                silent += 1
                continue
            g1, g2 = math.log(s / r["best"]["judge"][r["held"]]), math.log(s / d["judge"][r["held"]])
            gain["v1"].append((r["rig"], g1))
            gain["v2"].append((r["rig"], g2))
            gain["v2_minus_v1"].append((r["rig"], g2 - g1))
    adopted = (rms(diffs["v2"]["drive"]) < rms(diffs["v1"]["drive"]) and rms(diffs["v2"]["tone"]) < rms(diffs["v1"]["tone"])
               and boot_mean(gain["v2_minus_v1"])["hi90"] >= 0)
    out = {"replicate_rms": {t: {g: rms(v) for g, v in d.items()} for t, d in diffs.items()},
           "held_gain": {t: boot_mean(v) for t, v in gain.items() if v}, "pairs": len(pairs), "silent_held": silent,
           "moved_from_S_rms": {t: rms(v) for t, v in moved.items()}, "adopted": adopted,
           "evaluations": sum(d["evaluations"] for d in v2.values()) / max(1, len(v2)),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(root() / "report.json", out)
    print(json.dumps(out, indent=1))


def cmd_hold(_args):
    """FTh, N1's isolation: FT's stored answers with every control outside `K.space` held at S (no training, no audio read).
    -> {real,goat}/answers/P2b-fth.json."""
    from learn import arm_a_levers as L
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    P.require(PHASE)
    ms = L.menu_S()
    for d in (P.REAL_DIR, P.GOAT_DIR):
        a = json.loads((P.out_dir() / d / "answers" / f"{P.FT_BASE}.json").read_text())
        cls = ({p["unit"]: p["cls"] for p in a["parts"]} if d == P.REAL_DIR else {u["unit"]: u["cls"] for u in P.goat_units()})
        out = {}
        for key, by in a["answers"].items():
            unit, amp = key.rsplit("|", 1)
            S = ms[amp][cls[unit]][1]
            out[key] = {h: {"select": v["select"], "settings": LO.sdict(P.hold_outside_space(LO.tdict(v["settings"]), S, amp))}
                        for h, v in by.items()}
        P.save(P.out_dir() / d / "answers" / f"{P.FTH_TAG}.json", {**a, "ledger": f"{P.LEDGER_ID} {PHASE}", "tag": P.FTH_TAG, "answers": out,
                                                                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{d}: {len(out)} answers held")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("--shard", default="0/1")
    sub.add_parser("report")
    sub.add_parser("hold")
    args = ap.parse_args(argv)
    {"search": cmd_search, "report": cmd_report, "hold": cmd_hold}[args.cmd](args)


if __name__ == "__main__":
    main()
