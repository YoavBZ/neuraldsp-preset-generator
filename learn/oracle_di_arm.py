"""Arm A Mega-53, amendment 2 (docs/arm-a-mega53-plan.md): the oracle-DI arm XO on stage F.

Stage F's H with one change: the search renders through the part's true measure DI instead of
C′'s rebuild of the htdemucs full-mix stem. Same stem reference, recipe (52 renders, seed
20261013, shrink 0.5, fallback to S), judge. The search scores at the judge's lag for the true
DI (`part["judge_lag"]`; the stem is aligned with `reference.wav`, checked by `check`).

    .venv/bin/python -m learn.oracle_di_arm check                       # zero renders
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.oracle_di_arm search    # 6,993 renders, one process
    .venv/bin/python -m learn.oracle_di_arm report
"""

import argparse
import json
import math
import time

from learn import arm_a_mega53 as A
from learn import knob_ceiling as K

ARM = "XO"
OUT = A.OUT / "F-oracle"
STEM_LAG_TOL = 3                                 # samples, htdemucs crop against reference.wav
CAP = 7_100
K_S_CEILING = -0.293                             # K_S to a stop, stage D's parts (a different setting)
CONTRASTS = {"XO_minus_S": (ARM, "S"), "XO_minus_H": (ARM, "H"), "H_minus_S": ("H", "S"),
             "XO_unshrunk_minus_XO": (f"{ARM}_unshrunk", ARM)}
ROWS = ("all", "no_high_dir", "f_song")


def result_path(slug, amp, search):
    return OUT / ARM / slug / amp / f"{search}.json"


def prime_path(slug, amp):
    return OUT / ARM / slug / amp / "prime.json"


def expected_renders(n_dirs=A.N_DIRS["F"], n_groups=A.N_GROUPS["F"]):
    return n_groups + n_dirs * A.PER_DIRECTION


def spent():
    if not OUT.exists():
        return 0
    return sum(int((json.loads(p.read_text()) or {}).get("renders", 0) or 0) for p in OUT.rglob("*.json")
               if not p.name.startswith(("report", "check")))


def planned_left(dirs):
    todo = [d for d in dirs if not A._done(result_path(*d[:3]))]
    return len(todo) * A.PER_DIRECTION + len(A.groups(todo))


def cmd_check():
    """Zero renders: the htdemucs crops sit on reference.wav (GCC within ±3 samples) for every pool
    part, and the stage-F inputs passed."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import rank_margin as RM

    lags = {}
    for s in A.pool_slugs():
        ref = CR.mono(A.f_part(s)["crop"] / "reference.wav")
        lags[s] = RM.gcc_lag(np.load(A.sep_crop("htdemucs", s)).astype(np.float64), ref)
    bad = {s: v for s, v in lags.items() if abs(v) > STEM_LAG_TOL}
    ok = not bad and bool((A._load(A.fdir("inputs.json")) or {}).get("ok"))
    A._save(OUT / "check.json", {"ok": ok, "stem_vs_reference_gcc": lags, "bad": bad})
    print("oracle check:", "ok" if ok else bad)
    if not ok:
        raise SystemExit(1)


def cmd_search():
    """One process, group by group: a discarded priming render (true DI at S), then every direction
    of the group through the true DI. Resumable; stops on A's stop files, the cap, disk and swap."""
    if not (A._load(OUT / "check.json") or {}).get("ok"):
        raise SystemExit("run `check` first")
    A.require_heldout_ok()
    dirs = A.stage_dirs("F")
    if len(dirs) != A.N_DIRS["F"]:
        raise SystemExit(f"{len(dirs)} directions, not {A.N_DIRS['F']}")
    A.check_stop()
    why = A.cap_problem(spent(), planned_left(dirs), CAP)
    if why:
        raise SystemExit(why)
    by_group = {}
    for d in dirs:
        by_group.setdefault((d[0], d[1]), []).append(d)
    A.wait_render_gate()
    guard, ms = A.L.SwapGuard(), A.L.menu_S()
    rr = A.renderer()
    try:
        menu = rr.menu()
        for (slug, amp), ds in sorted(by_group.items()):
            todo = [d for d in ds if not A._done(result_path(*d[:3]))]
            if not todo:
                continue
            A.check_stop()
            guard.check()
            why = A.cap_problem(spent(), len(todo) * A.PER_DIRECTION + 1, CAP)
            if why:
                raise SystemExit(why)
            if not A.disk_ok(len(todo) + 1):
                raise SystemExit("free disk below the 31 GB guard (resumable)")
            ctx = A.group_ctx(menu, ms, "F", slug, amp)
            n0 = rr.count
            rr.render(ctx["di32"], ctx["sel"], ctx["S"])                 # priming render, discarded
            p = prime_path(slug, amp)
            w = A._load(p) or {"renders": 0}
            A._save(p, {"renders": w["renders"] + rr.count - n0})
            stem = A.arm_reference("F", "H", slug, ctx["part"])          # the htdemucs full-mix crop
            for s_, a_, search, held in todo:
                A.check_stop()
                A.run_direction(rr, ctx, "F", ARM, s_, a_, search, held, None, stem=stem, rb=ctx["di"],
                                lag=ctx["part"]["judge_lag"], path=result_path(s_, a_, search))
    finally:
        rr.close()
    print(f"oracle search: done; renders this process {rr.count}; spent {spent()}", flush=True)


def build_units():
    units = A.build_units("F", ("H", "M"))
    for u in units:
        d = du = None
        r = A._load(result_path(u["slug"], u["amp"], u["search"]))
        if r and r.get("status") == "done":
            d = u["d"]["S"] if r.get("fallback") else r["judge_shrunk"][u["held"]]
            du = r["judge_best"][u["held"]]
        u["d"][ARM], u["d"][f"{ARM}_unshrunk"], u["rec"][ARM] = d, du, r
    return units


def _all(c, row="all"):
    return ((c["rows"].get(row) or {}).get("all")) or {}


def report_from_units(units, bt, snr=None):
    filters = {r: A.row_filter(r, "F", bt, snr or {}) for r in ROWS}
    rep = {"directions": len(units), "contrasts": {}, "complete": A.complete(units, ("S", "H", "M", ARM), A.N_DIRS["F"])}
    for name, (a, b) in CONTRASTS.items():
        rep["contrasts"][name] = A.contrast(units, a, b, ROWS, filters)
    rep["share_of_ceiling"] = {}
    for name in ("XO_minus_S", "H_minus_S"):
        m = _all(rep["contrasts"][name]).get("band_weighted_mean")
        rep["share_of_ceiling"][name] = None if m is None else m / K_S_CEILING
    rep["fallbacks"] = sum(1 for u in units if (u["rec"].get(ARM) or {}).get("fallback"))
    rep["activity_fallback_total"] = sum((u["rec"].get(ARM) or {}).get("activity_fallback", 0) for u in units)
    return rep


def fmt(s):
    if not s or s.get("band_weighted_mean") is None:
        return "n/a"
    lo, hi = s.get("lo90"), s.get("hi90")
    return f"{s['band_weighted_mean']:+.3f}" + ("" if lo is None else f" [{lo:+.3f}, {hi:+.3f}]") + f" ({s['bands']} bands)"


def cmd_report():
    rep = report_from_units(build_units(), A.C.load_bleed_table())
    rep.update(renders_used=spent(), renders_expected=expected_renders(), cap=CAP,
               time=time.strftime("%Y-%m-%d %H:%M:%S"))
    A._save(OUT / "report.json", rep)
    if rep["complete"]:
        print(f"INCOMPLETE ({rep['complete']}): the figures below are partial")
    print(f"{rep['directions']} directions; complete: {rep['complete'] or 'yes'}; renders {rep['renders_used']} "
          f"(expected {rep['renders_expected']})")
    for name, c in rep["contrasts"].items():
        print(f"  {name:22s}", "  ".join(f"{r}: {fmt(_all(c, r))}" for r in ROWS))
    print("  share of the K_S gap (-0.293):", {k: None if v is None else round(v, 3)
                                                 for k, v in rep["share_of_ceiling"].items()})
    print("  fallbacks:", rep["fallbacks"], " activity fallbacks:", rep["activity_fallback_total"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("check", "search", "report"))
    a = ap.parse_args(argv)
    {"check": cmd_check, "search": cmd_search, "report": cmd_report}[a.cmd]()


if __name__ == "__main__":
    main()
