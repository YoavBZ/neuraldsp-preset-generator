"""LS, the loudness step (`docs/full-controls-plan.md`, "LS in detail"; ledger `pipeline-fix` `phase_ls`): the generate
path's output gain. The model holds the output control at the factory start's (S's) value, but its other controls move the
level, and J0 removes level, so nothing pulls it back. LS sets the output so the preset plays at S's loudness on the class's
two stock DIs (the renders the amp pick already makes), clamped to the control's range, and checks the match on each
unit's own DI.

    .venv/bin/python -m learn.loudness_step ls-draw                     # the items (zero renders)
    .venv/bin/python -m learn.loudness_step ls-table                    # S on each amp and class through the stock DIs
    .venv/bin/python -m learn.loudness_step ls-render --shard 0/3       # each item's renders
    .venv/bin/python -m learn.loudness_step ls-report                   # the read (zero renders)

The pure parts (the gain, the clamp, the read) are unit-tested; the render commands are not.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time

PHASE = "phase_ls"
OUTPUT = "parameters/outputGain"
RANGE = (-24.0, 24.0)                # the manifest's (`full_space.OUTPUT_RANGE`)
LINEAR_TOL_DB = 0.05                 # the output control is a pure gain: unmatched + the change = matched, to this
EXCLUDE = frozenset({                # C4's 4 items the listener skipped as "Bad DI, only contains a single note" (F82)
    "cap/hqjhk6pt6jj_a2#ac20", "cap/gagthwmijw5_a2#sw50r", "cap/p4z4rx724ps#sw50r",
    "cap/1d1b3470-ea1e-4e67-84b0-f71fa149d32e#pr12"})


def ls_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "ls"


# --- the pure parts -----------------------------------------------------------------------------------------------------

def matched_gain(g0, s_stock, ans_stock, lo=RANGE[0], hi=RANGE[1]):
    """The output gain that brings the answer to S's loudness on the stock DIs: g0 plus the mean of S's LUFS less the
    answer's over the DIs, clamped. -> (gain, the change wanted, the shortfall in dB: 0 unless clamped)."""
    want = statistics.fmean(s_stock) - statistics.fmean(ans_stock)
    g = g0 + want
    c = min(hi, max(lo, g))
    return c, want, g - c


def with_output(settings, g):
    """A copy of JSON settings ({"module/key": v}) with the output gain set to g."""
    out = dict(settings)
    out[OUTPUT] = float(g)
    return out


def summary(xs):
    xs = sorted(xs)
    if not xs:
        return {"n": 0}
    q = lambda p: xs[min(len(xs) - 1, int(math.floor(p * (len(xs) - 1) + 0.5)))]   # noqa: E731
    return {"n": len(xs), "median": statistics.median(xs), "p90": q(0.9), "max": xs[-1], "min": xs[0]}


def report(recs):
    """The declared read. recs: per item {set, cls, amp, g0, gain, want, short, own: {S, unmatched, matched} LUFS,
    peaks: {S, unmatched, matched} dBFS}. -> the gaps to S on the unit's own DI, unmatched and matched, the clamps, the
    linearity check and the peaks."""
    gap_u = [abs(r["own"]["unmatched"] - r["own"]["S"]) for r in recs]
    gap_m = [abs(r["own"]["matched"] - r["own"]["S"]) for r in recs]
    lin = [abs((r["own"]["matched"] - r["own"]["unmatched"]) - (r["gain"] - r["g0"])) for r in recs]
    signed = [r["own"]["matched"] - r["own"]["S"] for r in recs]
    by = {}
    for k in ("cls", "amp", "set"):
        for v in sorted({r[k] for r in recs}):
            sub = [r for r in recs if r[k] == v]
            by[f"{k} {v}"] = {"n": len(sub), "matched gap median": statistics.median(
                abs(r["own"]["matched"] - r["own"]["S"]) for r in sub)}
    return {"items": len(recs),
            "gap to S, unmatched (dB)": summary(gap_u), "gap to S, matched (dB)": summary(gap_m),
            "matched - S, signed (dB)": summary(signed),
            "clamped": sum(r["short"] != 0 for r in recs), "shortfalls (dB)": sorted(r["short"] for r in recs if r["short"]),
            "linearity": {"max error (dB)": max(lin) if lin else None,
                          "holds": bool(lin) and max(lin) <= LINEAR_TOL_DB},
            "peaks over 0 dBFS": {k: sum(r["peaks"][k] > 0 for r in recs) for k in ("S", "unmatched", "matched")},
            "by": by,
            "reading": ("closer" if statistics.median(gap_m) < statistics.median(gap_u) else "not closer") if recs else None}


# --- the commands -------------------------------------------------------------------------------------------------------

def items():
    """C4's 18 less the 4 single-note DIs (the adopted model's answer on the forced amp) and A3's 18 (R-all's answer on the stock-DI pick's amp,
    the amp the generate path plays): {key, set, unit, cls, amp, prt, answer: {select, settings}}."""
    from learn import amp_di_compare_r as R
    from learn import pipeline_fix as P

    c4 = json.loads((P.out_dir() / "c4" / "plan.json").read_text())["items"]
    c4a = json.loads((P.out_dir() / "c4" / "answers.json").read_text())["answers"]
    a3 = json.loads((P.out_dir() / "a3" / "plan.json").read_text())["items"]
    a2a = json.loads((R.a2_dir() / "answers.json").read_text())["answers"]
    out = [{"key": f"c4|{it['key']}", "set": "c4", "unit": it["unit"], "cls": it["cls"], "amp": it["amp"], "prt": it["prt"],
            "answer": c4a[it["key"]]["adopted"]} for it in c4 if it["unit"] not in EXCLUDE]
    out += [{"key": f"a3|{it['key']}", "set": "a3", "unit": it["unit"], "cls": it["cls"], "amp": it["pick"], "prt": it["prt"],
             "answer": a2a[it["set"]][f"{it['unit']}|{it['pick']}"][it["search"]]} for it in a3]
    return out


def fname(key):
    import hashlib

    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _render(di32, sel, settings):
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import pretrain_set as PS

    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    st = LO.tdict(settings)
    return np.asarray(AM.fresh_render(CB.new_renderer, di32, sel, st, st), np.float64)[trim[0]:trim[1]]


def _level(y):
    import numpy as np

    from learn import song_aug as SA

    return SA.lufs(y), float(20 * np.log10(max(float(np.max(np.abs(y))), 1e-12)))


def cmd_draw(_args):
    from learn import pipeline_fix as P

    P.require(PHASE)
    p = ls_dir() / "plan.json"
    if p.exists():
        raise SystemExit(f"{p} exists: drawn once")
    its = items()
    P.save(p, {"phase": PHASE, "items": its, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"LS DRAW: {len(its)} items")


def cmd_table(_args):
    """S on each amp and class through each stock DI of the class -> ls/s-table.json {amp: {cls: [LUFS per DI]}}."""
    import numpy as np

    from learn import amp_di_compare as A1
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B

    P.require(PHASE)
    p = ls_dir() / "s-table.json"
    if p.exists():
        raise SystemExit(f"{p} exists")
    stock = json.loads((A1.a1_dir() / "plan.json").read_text())["stock"]
    ms = P.A_menu_S()
    LO._wait_cap()
    tab, n = {}, 0
    for cls, ss in sorted(stock.items()):
        dis = [B.measure(PS.section_audio(s["di_path"], s["start_s"])).astype(np.float32) for s in ss]
        for a in A1.AMPS:
            sel, S = ms[a][cls]
            tab.setdefault(a, {})[cls] = [_level(_render(d, sel, LO.sdict(S)))[0] for d in dis]
            n += 2 * len(dis)
    P.save(p, {"phase": PHASE, "table": tab, "stock": {c: [s["di"] for s in ss] for c, ss in stock.items()},
               "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"LS TABLE DONE: {n} renders")


def cmd_render(args):
    """Per item: the answer through the class's stock DIs (its LUFS), the matched gain, then S, the unmatched answer and
    the matched answer through the unit's own DI -> ls/items/<key>.json and a 5 s clip of S and the matched answer."""
    import numpy as np

    from learn import amp_di_compare as A1
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    P.require(PHASE)
    plan = json.loads((ls_dir() / "plan.json").read_text())["items"]
    tab = json.loads((ls_dir() / "s-table.json").read_text())["table"]
    stock = json.loads((A1.a1_dir() / "plan.json").read_text())["stock"]
    ms = P.A_menu_S()
    k, n = args.shard
    LO._wait_cap()
    d = ls_dir() / "items"
    renders, dis = 0, {}
    for it in plan[k::n]:
        out = d / f"{fname(it['key'])}.json"
        if out.exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        cls, a, ans = it["cls"], it["amp"], it["answer"]
        if cls not in dis:
            dis[cls] = [B.measure(PS.section_audio(s["di_path"], s["start_s"])).astype(np.float32) for s in stock[cls]]
        ans_stock = [_level(_render(x, ans["select"], ans["settings"]))[0] for x in dis[cls]]
        renders += 2 * len(dis[cls])
        g0 = float(ans["settings"][OUTPUT])
        g, want, short = matched_gain(g0, tab[a][cls], ans_stock)
        prt = it["prt"]
        own = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        sel, S = ms[a][cls]
        ys = {"S": _render(own, sel, LO.sdict(S)), "unmatched": _render(own, ans["select"], ans["settings"]),
              "matched": _render(own, ans["select"], with_output(ans["settings"], g))}
        renders += 6
        lv = {c: _level(y) for c, y in ys.items()}
        rec = {"key": it["key"], "set": it["set"], "unit": it["unit"], "cls": cls, "amp": a, "g0": g0, "gain": g,
               "want": want, "short": short, "ans_stock": ans_stock, "s_stock": tab[a][cls],
               "own": {c: v[0] for c, v in lv.items()}, "peaks": {c: v[1] for c, v in lv.items()}}
        d.mkdir(parents=True, exist_ok=True)
        L = int(5.0 * PS.SR)
        mono = {c: (np.mean(y, 1) if y.ndim == 2 else y)[:L].astype(np.float32) for c, y in ys.items() if c != "unmatched"}
        np.savez(d / f"{fname(it['key'])}.npz", **mono)
        P.save(out, rec)                                 # the resume marker, after its clip
        print(f"{it['set']} {cls}: renders so far {renders}", flush=True)
    print(f"LS RENDER DONE {k}/{n}: {renders} renders", flush=True)


def cmd_report(_args):
    from learn import pipeline_fix as P

    P.require(PHASE)
    plan = json.loads((ls_dir() / "plan.json").read_text())["items"]
    recs = []
    for it in plan:
        p = ls_dir() / "items" / f"{fname(it['key'])}.json"
        if not p.exists():
            raise SystemExit(f"no record for {it['key']}: every item renders first")
        recs.append(json.loads(p.read_text()))
    rep = {"phase": PHASE, **report(recs), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(ls_dir() / "report.json", rep)
    print(json.dumps({k: v for k, v in rep.items() if k != "by"}, indent=1))


def shard(s):
    a, b = s.split("/")
    return int(a), int(b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ls-draw").set_defaults(fn=cmd_draw)
    sub.add_parser("ls-table").set_defaults(fn=cmd_table)
    r = sub.add_parser("ls-render")
    r.add_argument("--shard", type=shard, default=(0, 1))
    r.set_defaults(fn=cmd_render)
    sub.add_parser("ls-report").set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
