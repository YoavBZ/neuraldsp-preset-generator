"""Arm A Mega-53, amendment 3 (docs/arm-a-mega53-plan.md): what perfect separation is worth to arm
A on stage F's fresh full mixes.

YT (Y_target) is stage F's H with the separated stem replaced by the part's true amp track
(`reference.wav`) in both places a product uses it: the search's reference, and the input C′
rebuilds the search DI from (C′'s rebuild of `reference.wav`, as experiment 1b rebuilt it). ZT, the
optional fourth cell, renders through the true measure DI and scores against the true amp track
(the full ceiling of the 2×2 {DI: rebuilt, true} × {target: stem, true}, with arm A's recipe).
Unchanged from H: the 52-render search (seed 20261013), shrink 0.5, the fallback to S, the judge
(held half, true DI against `reference.wav`). Both arms score the search at the judge's lag
(`part["judge_lag"]`, amendment 2's convention); `check` measures what that costs.

    $TORCH_PY -m learn.perfect_sep_arm rebuild [--arms YG]                    # C′ on reference.wav (or G), 21 parts
    .venv/bin/python -m learn.perfect_sep_arm check                           # zero renders
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.perfect_sep_arm search --arms YT[,ZT] --shard i/3
    .venv/bin/python -m learn.perfect_sep_arm report

TORCH_PY is ~/ndsp-presets/tools/demucs-venv/bin/python.

YG (docs/separation-finetune-plan.md, Step 1) is YT with the class-oracle stem G in place of the
amp track: the sum of every electric-guitar track in the part's context
(`learn.separation_ceiling`, stored crops), in both places a product uses the stem. Its rebuild
is C′'s rebuild of G, with 1b's gates. It reads YG − M (decides the class fine-tune), YT − YG
(prices route B) and the share (YG − M) / (YT − M), on the directions where S, H, M, YT and YG
all score.
"""

import argparse
import json
import math
import time

from learn import arm_a_mega53 as A
from learn import knob_ceiling as K
from learn import oracle_di_arm as O

OUT = A.OUT / "F-perfect-sep"
ARMS = ("YT", "ZT", "YG")
REBUILT = A.fdir("rebuilt", "ref")
REBUILT_G = A.fdir("rebuilt", "class-oracle")
G_CROPS = K.HOME / "learn/separation-finetune/G/crop"
LAG_TOL = 3                                      # samples: the rebuild against its source and H's rebuild
CAP = {"YT": 7_100, "ZT": 7_100, "YG": 7_100}
K_S_CEILING = O.K_S_CEILING                      # −0.293, stage D's parts (a different setting)
RECORD_MATCH_C = -0.45                           # record-match check 1's ceiling C − S, 5 parts (context)
LAG_PART = "cambridge-wickerman-elecgtr7"        # judge lag +329: the lag check's largest shift
ROWS = (*O.ROWS, "no_lag_part")                  # all (declared), no high bleed, F-song, without LAG_PART
CONTRASTS = {"YT_minus_S": ("YT", "S"), "YT_minus_H": ("YT", "H"), "YT_minus_XO": ("YT", "XO"),
             "XO_minus_S": ("XO", "S"), "H_minus_S": ("H", "S"),
             "YT_unshrunk_minus_YT": ("YT_unshrunk", "YT")}
CONTRASTS_ZT = {"ZT_minus_S": ("ZT", "S"), "ZT_minus_YT": ("ZT", "YT"), "ZT_minus_XO": ("ZT", "XO"),
                "ZT_unshrunk_minus_ZT": ("ZT_unshrunk", "ZT")}
SHARE_ARMS = ("H", "XO", "YT")
CONTRASTS_YG = {"YG_minus_M": ("YG", "M"), "YT_minus_YG": ("YT", "YG"), "YG_minus_H": ("YG", "H"),
                "YG_minus_S": ("YG", "S"), "YT_minus_M": ("YT", "M"), "YG_unshrunk_minus_YG": ("YG_unshrunk", "YG")}
YG_FIXED = ("S", "H", "M", "YT", "YG")                # Step 1's fixed direction set
YG_STEP2_POINT = -0.032                               # Step 1: YG − M at or below this, upper bound below 0


def result_path(arm, slug, amp, search):
    return OUT / arm / slug / amp / f"{search}.json"


def prime_path(arm, slug, amp):
    return OUT / arm / slug / amp / "prime.json"


def expected_renders(n_dirs=A.N_DIRS["F"], n_groups=A.N_GROUPS["F"]):
    return n_groups + n_dirs * A.PER_DIRECTION                       # per arm: 63 + 126 × 55 = 6,993


def spent(arm):
    d = OUT / arm
    if not d.exists():
        return 0
    return sum(int((json.loads(p.read_text()) or {}).get("renders", 0) or 0) for p in d.rglob("*.json"))


def planned_left(arm, dirs):
    todo = [d for d in dirs if not A._done(result_path(arm, *d[:3]))]
    return len(todo) * A.PER_DIRECTION + len(A.groups(todo))


def reference(slug):
    """The true amp track: the YT/ZT search reference, and the source of YT's rebuild."""
    from learn import confirm_run as CR

    return CR.mono(A.f_part(slug)["crop"] / "reference.wav")


def g_crop(slug):
    """The class-oracle stem G's crop (`learn.separation_ceiling measure`)."""
    import numpy as np

    return np.load(G_CROPS / f"{slug}.npy").astype(np.float64)


def search_inputs(arm, ctx, slug):
    """-> (reference, search DI) for an arm: YT the rebuild of the amp track, ZT the true DI, YG the
    class-oracle stem G and its rebuild."""
    import numpy as np

    if arm == "YG":
        return g_crop(slug), np.load(REBUILT_G / f"{slug}.npy")
    if arm == "YT":
        return reference(slug), np.load(REBUILT / f"{slug}.npy")
    if arm == "ZT":
        return reference(slug), ctx["di"]
    raise ValueError(arm)


def rebuild_problems(log, slugs, h_lag, stem_lag, h_log, src_lag=None):
    """{slug: [why]}, 1b's gates (amendment 2a) on stage F: the level (−22.9 ± 0.05 LUFS) and the
    alignment with H's stem rebuild, GCC within ±3 samples. Where that GCC is not usable (a
    bleed-heavy stem), the alignment is checked through the chain instead: the rebuild's lag on
    reference.wav must equal H's rebuild's lag on its stem plus the stem's lag on reference.wav
    (amendment 2's check), within ±3. The rebuild's GCC on its own source is a diagnostic only: it
    reads 0 or about −52 by part, as 1b's and 1c's did. src_lag (YG): the source's own lag on
    reference.wav, added to the chain (0 for YT, whose source is reference.wav)."""
    out = {}
    for s in slugs:
        r, p = log.get(s), []
        if not r:
            out[s] = ["missing"]
            continue
        if not (A._num(r.get("lufs")) and abs(r["lufs"] - A.LUFS_TARGET) <= A.LUFS_TOL):
            p.append(f"loudness {r.get('lufs')}")
        if abs(h_lag.get(s, 99)) > LAG_TOL:
            chain = None
            if s in stem_lag and s in h_log:
                chain = (r.get("gcc_vs_source", 99) + (src_lag or {}).get(s, 0)
                         - (h_log[s].get("gcc_vs_source", 99) + stem_lag[s]))
            if chain is None or abs(chain) > LAG_TOL:
                p.append(f"GCC against H's rebuild {h_lag.get(s)}, through the chain {chain}")
        if p:
            out[s] = p
    return out


def relevel(y, target=A.LUFS_TARGET, tol=A.LUFS_TOL, tries=3):
    """The recipe's level step again until it lands within the tolerance (one gain pass misses
    when quiet blocks cross the meter's absolute gate). -> (y, passes)."""
    from learn import local_objective as LO
    from learn.direc_check import to_lufs

    n = 0
    while n < tries and abs(LO.lufs(y) - target) > tol:
        y, n = to_lufs(y, target), n + 1
    return y, n


def cmd_rebuild(arm="YT"):
    """C′'s rebuild of each pool part's reference.wav (YT) or class-oracle stem G (YG)
    (`arm_a_mega53.rebuild_parts`, the stage-F rebuild recipe: the fold's C′, the leak assertion,
    re-EQ, −22.9 LUFS)."""
    import numpy as np

    from learn import rank_margin as RM

    A.require_heldout_ok()
    A.wait_separation_gate(A.REBUILD_MIN_GB)
    slugs = A.pool_slugs()
    from learn import local_objective as LO

    out_dir, source = (REBUILT_G, g_crop) if arm == "YG" else (REBUILT, reference)
    src_lag = {s: int(RM.gcc_lag(g_crop(s), reference(s))) for s in slugs} if arm == "YG" else None
    log = A.rebuild_parts(slugs, A.f_part, source, out_dir)
    h_lag = {}
    for s in slugs:
        if s not in log:
            continue
        y, n_ = relevel(np.load(out_dir / f"{s}.npy"))
        if n_:
            np.save(out_dir / f"{s}.npy", y)
            log[s].update(lufs=LO.lufs(y), relevel_passes=log[s].get("relevel_passes", 0) + n_)
            A._save(out_dir / "rebuild-log.json", log)
        h = np.load(A.rebuilt_path("F", "H", s))
        n = min(len(y), len(h))
        h_lag[s] = int(RM.gcc_lag(y[:n], h[:n]))
    stem_lag = (A._load(O.OUT / "check.json") or {}).get("stem_vs_reference_gcc") or {}
    h_log = A._load(A.fdir("rebuilt", "htdemucs", "rebuild-log.json")) or {}
    bad = rebuild_problems(log, slugs, h_lag, stem_lag, h_log, src_lag)
    A._save(out_dir / "check.json", {"ok": not bad, "problems": bad, "gcc_vs_h_rebuild": h_lag, "source_vs_reference_gcc": src_lag,
                                     "gcc_vs_reference": {s: log[s].get("gcc_vs_source") for s in log}})
    if bad:
        raise SystemExit(f"{arm} rebuilds fail their checks: {bad}")
    print(f"{arm} rebuilds: {len(log)} pass")


def cmd_check():
    """Zero renders. The reference rebuilds passed; stage F's inputs passed; and the lag check: each
    stored S render (its kept FLAC, restored) re-judged at the judge lag reproduces the stored judge
    within 0.005, and re-judged at −52 shows how much a shift of (judge_lag + 52) samples moves a
    held-half distance (YT's rebuild sits aligned with reference.wav, where −52 is aligned)."""
    import statistics

    import numpy as np
    import soundfile as sf

    probs = []
    if not (A._load(REBUILT / "check.json") or {}).get("ok"):
        probs.append("reference rebuilds have not passed (run `rebuild`)")
    if not (A._load(A.fdir("inputs.json")) or {}).get("ok"):
        probs.append("stage F's inputs have not passed")
    rows = []
    for s in A.pool_slugs():
        part, ref = A.f_part(s), reference(s)
        di = K.measure_di(part)
        for amp in K.AMPS:
            r = A._load(A.s_path(s, amp))
            y, _ = sf.read(str(A.s_path(s, amp).with_suffix(".flac")))
            y = np.concatenate([np.zeros(int(A.TRIM_S * A.SR)), y * r["kept_flac_scale"]])
            j0, j1 = K.judge(ref, y, di, part["judge_lag"]), K.judge(ref, y, di, A.OBJ_LAG)
            rows.append({"slug": s, "amp": amp, "judge_lag": part["judge_lag"],
                         "repro": max(abs(math.log(j0[h] / r["judge"][h])) for h in j0),
                         "shift": {h: math.log(j1[h] / j0[h]) for h in j0}})
    repro = max(r["repro"] for r in rows)
    if repro > A.TOL:
        probs.append(f"stored S judges reproduce only within {repro:.4f}")
    shifts = [abs(v) for r in rows for v in r["shift"].values()]
    lag = {"repro_max": repro, "median_abs_log": statistics.median(shifts), "max_abs_log": max(shifts),
           "over_0.01": sorted({(r["slug"], r["amp"]) for r in rows if max(map(abs, r["shift"].values())) > 0.01})}
    A._save(OUT / "check.json", {"ok": not probs, "problems": probs, "lag": lag, "rows": rows})
    print("perfect-sep check:", "ok" if not probs else probs, {k: v for k, v in lag.items() if k != "over_0.01"},
          "shift > 0.01:", lag["over_0.01"])
    if probs:
        raise SystemExit(1)


MIN_FREE_GB_FLOOR = 10.0                                              # the override can lower the guard, not remove it


def cmd_search(arms, shard, min_free_gb=None):
    """One process per shard of (part, amp) groups, arm by arm within a group: a discarded priming
    render (the arm's search DI at S) after the process start and every DI or amp change, then the
    group's directions. Resumable; stops on A's stop files, the caps, the disk and swap guards.
    `min_free_gb` overrides the disk guard for this run only (default: LO.DISK_GUARD_GB, 31 GB)."""
    guard_gb = A.LO.DISK_GUARD_GB if min_free_gb is None else float(min_free_gb)
    if guard_gb < MIN_FREE_GB_FLOOR:
        raise SystemExit(f"--min-free-gb {guard_gb:g} is below the {MIN_FREE_GB_FLOOR:g} GB floor")
    if guard_gb != A.LO.DISK_GUARD_GB:
        print(f"disk guard overridden for this run: {guard_gb:g} GB (default {A.LO.DISK_GUARD_GB:g} GB)", flush=True)
    if not (A._load(OUT / "check.json") or {}).get("ok"):
        raise SystemExit("run `check` first")
    if "YG" in arms and not (A._load(REBUILT_G / "check.json") or {}).get("ok"):
        raise SystemExit("run `rebuild --arms YG` first (its checks must pass)")
    A.require_heldout_ok()
    dirs = A.stage_dirs("F")
    if len(dirs) != A.N_DIRS["F"]:
        raise SystemExit(f"{len(dirs)} directions, not {A.N_DIRS['F']}")
    A.check_stop()
    for arm in arms:
        why = A.cap_problem(spent(arm), planned_left(arm, dirs), CAP[arm])
        if why:
            raise SystemExit(f"{arm}: {why}")
    by_group = {}
    for d in dirs:
        by_group.setdefault((d[0], d[1]), []).append(d)
    mine = A.L._shard(sorted(by_group), shard)
    A.wait_render_gate()
    guard, ms = A.L.SwapGuard(), A.L.menu_S()
    rr = A.renderer()
    try:
        menu = rr.menu()
        for slug, amp in mine:
            ctx = None
            for arm in arms:
                todo = [d for d in by_group[(slug, amp)] if not A._done(result_path(arm, *d[:3]))]
                if not todo:
                    continue
                A.check_stop()
                guard.check()
                why = A.cap_problem(spent(arm), len(todo) * A.PER_DIRECTION + 1, CAP[arm])
                if why:
                    raise SystemExit(f"{arm}: {why}")
                if not A.disk_ok(len(todo) + 1, guard=guard_gb):
                    raise SystemExit(f"free disk below the {guard_gb:g} GB guard (resumable)")
                ctx = ctx or A.group_ctx(menu, ms, "F", slug, amp)
                ref, rb = search_inputs(arm, ctx, slug)
                n0 = rr.count
                rr.render(rb.astype("float32"), ctx["sel"], ctx["S"])            # priming render, discarded
                p = prime_path(arm, slug, amp)
                w = A._load(p) or {"renders": 0}
                A._save(p, {"renders": w["renders"] + rr.count - n0})
                for s_, a_, search, held in todo:
                    A.check_stop()
                    A.run_direction(rr, ctx, "F", arm, s_, a_, search, held, None, stem=ref, rb=rb,
                                    lag=ctx["part"]["judge_lag"], path=result_path(arm, s_, a_, search),
                                    s_lags=(A.OBJ_LAG,))
    finally:
        rr.close()
    print(f"perfect-sep search {arms} shard {shard[0]}/{shard[1]}: done; renders this process {rr.count}; "
          f"spent {({a: spent(a) for a in arms})}", flush=True)


def build_units():
    units = O.build_units()                                           # S, H, M and XO (amendment 2)
    for u in units:
        for arm in ARMS:
            d = du = None
            r = A._load(result_path(arm, u["slug"], u["amp"], u["search"]))
            if r and r.get("status") == "done":
                d = u["d"]["S"] if r.get("fallback") else r["judge_shrunk"][u["held"]]
                du = r["judge_best"][u["held"]]
            u["d"][arm], u["d"][f"{arm}_unshrunk"], u["rec"][arm] = d, du, r
    return units


def has_arm(units, arm):
    return bool(units) and all((u["rec"].get(arm) or {}).get("status") == "done" for u in units)


def contrast(units, a, b, filters, zt=False):
    """a − b on the directions where S, H, M, XO, YT (and ZT, when it ran) all score, so every
    contrast reads the same fixed set (A.contrast keeps only S, H and M)."""
    kept, dropped = A.units_for(units, tuple(dict.fromkeys((*A.BASE, "XO", "YT", *(("ZT",) if zt else ()), a, b))))
    out = {"directions": len(kept), "dropped": [list(d) for d in dropped], "rows": {}}
    for row in ROWS:
        sel = [u for u in kept if filters[row](u)]
        out["rows"][row] = A.L.effects(sel, a, b) if sel else None
    return out


def shares(units, rep, zt):
    """Each arm's share of the gap to a ceiling: (arm − S) / (ceiling − S). With ZT, ZT is the
    matched stage-F ceiling (Fieller 90%, `local_objective_1c.share`); K_S's −0.293 and the
    record-match C's −0.45 are scales from other settings, descriptive."""
    from learn import local_objective_1c as C

    out = {}
    for arm in SHARE_ARMS + (("ZT",) if zt else ()):
        m = O._all(rep["contrasts"].get(f"{arm}_minus_S") or {}).get("band_weighted_mean")
        out[arm] = {"vs_K_S": None if m is None else m / K_S_CEILING,
                    "vs_record_match_C": None if m is None else m / RECORD_MATCH_C}
        if zt and arm != "ZT":
            kept, _ = A.units_for(units, tuple(dict.fromkeys((*A.BASE, "XO", "YT", "ZT"))))
            out[arm]["vs_ZT"] = C.share(A.log_rows(kept, arm, "S"), A.log_rows(kept, "ZT", "S"))
    return out


def contrast_yg(units, a, b, filters):
    """a − b on Step 1's fixed set: the directions where S, H, M, YT and YG all score."""
    kept, dropped = A.units_for(units, tuple(dict.fromkeys((*YG_FIXED, a, b))))
    out = {"directions": len(kept), "dropped": [list(d) for d in dropped], "rows": {}}
    for row in ROWS:
        sel = [u for u in kept if filters[row](u)]
        out["rows"][row] = A.L.effects(sel, a, b) if sel else None
    return out


def yg_reading(c):
    """Step 1's declared reading of YG − M (all row, band-weighted, 90% band-clustered t)."""
    e = O._all(c, "all") or {}
    m, hi = e.get("band_weighted_mean"), e.get("hi90")
    if m is None or hi is None:
        return "incomplete"
    return "step_2" if m <= YG_STEP2_POINT and hi < 0 else "no_fine_tune"


def report_yg(units, filters):
    from learn import local_objective_1c as C

    out = {"contrasts": {k: contrast_yg(units, a, b, filters) for k, (a, b) in CONTRASTS_YG.items()}}
    kept, _ = A.units_for(units, YG_FIXED)
    out["share_YG_minus_M_over_YT_minus_M"] = C.share(A.log_rows(kept, "YG", "M"), A.log_rows(kept, "YT", "M"))
    out["decision_A1"] = yg_reading(out["contrasts"]["YG_minus_M"])
    ty = O._all(out["contrasts"]["YT_minus_YG"], "all") or {}
    out["route_B_to_user"] = bool(ty.get("band_weighted_mean") is not None and ty["band_weighted_mean"] <= YG_STEP2_POINT
                                  and ty.get("hi90") is not None and ty["hi90"] < 0)
    out["fallbacks"] = sum(1 for u in units if (u["rec"].get("YG") or {}).get("fallback"))
    out["activity_fallbacks"] = sum((u["rec"].get("YG") or {}).get("activity_fallback", 0) for u in units)
    return out


def report_from_units(units, bt, snr=None):
    filters = {r: A.row_filter(r, "F", bt, snr or {}) for r in ROWS if r != "no_lag_part"}
    filters["no_lag_part"] = lambda u: u["slug"] != LAG_PART
    zt = has_arm(units, "ZT")
    rep = {"directions": len(units), "zt": zt, "contrasts": {},
           "complete": A.complete(units, ("S", "H", "M", "XO", "YT") + (("ZT",) if zt else ()), A.N_DIRS["F"])}
    for name, (a, b) in {**CONTRASTS, **(CONTRASTS_ZT if zt else {})}.items():
        rep["contrasts"][name] = contrast(units, a, b, filters, zt)
    rep["share_of_ceiling"] = shares(units, rep, zt)
    if has_arm(units, "YG"):
        rep["YG"] = report_yg(units, filters)
    for arm in [a for a in (ARMS if zt else ("YT",)) if a != "YG" or "YG" in rep]:   # no partial-YG figures
        sh = [abs(math.log(at / c["value"])) for u in units for c in [(u["rec"].get(arm) or {}).get("s_lag_check")]
              if c for at in c["at"].values() if A._num(at) and A._num(c["value"]) and at > 0 and c["value"] > 0]
        rep[f"{arm}_s_lag_shift"] = ({"n": len(sh), "median_abs_log": sorted(sh)[len(sh) // 2], "max_abs_log": max(sh)}
                                     if sh else None)
        rep[f"{arm}_fallbacks"] = sum(1 for u in units if (u["rec"].get(arm) or {}).get("fallback"))
        rep[f"{arm}_activity_fallbacks"] = sum((u["rec"].get(arm) or {}).get("activity_fallback", 0) for u in units)
    return rep


def cmd_report():
    rep = report_from_units(build_units(), A.C.load_bleed_table())
    rep.update(renders_used={a: spent(a) for a in ARMS}, renders_expected_per_arm=expected_renders(), cap=CAP,
               time=time.strftime("%Y-%m-%d %H:%M:%S"))
    A._save(OUT / "report.json", rep)
    if rep["complete"]:
        print(f"INCOMPLETE ({rep['complete']}): the figures below are partial")
    print(f"{rep['directions']} directions; renders {rep['renders_used']} (expected {rep['renders_expected_per_arm']} per arm)")
    for name, c in rep["contrasts"].items():
        print(f"  {name:22s}", "  ".join(f"{r}: {O.fmt(O._all(c, r))}" for r in ROWS))
    print("  shares:", json.dumps(rep["share_of_ceiling"], default=str))
    print("  fallbacks:", {k: v for k, v in rep.items() if "fallback" in k})
    if "YG" in rep:
        for name, c in rep["YG"]["contrasts"].items():
            print(f"  {name:22s}", "  ".join(f"{r}: {O.fmt(O._all(c, r))}" for r in ROWS))
        print("  share (YG − M)/(YT − M):", json.dumps(rep["YG"]["share_YG_minus_M_over_YT_minus_M"], default=str))
        print("  decision A1:", rep["YG"]["decision_A1"], " route B to the user:", rep["YG"]["route_B_to_user"],
              " YG fallbacks:", rep["YG"]["fallbacks"], rep["YG"]["activity_fallbacks"])


def parse_shard(s):
    i, n = (int(x) for x in s.split("/"))
    if not 0 <= i < n:
        raise argparse.ArgumentTypeError(s)
    return i, n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("rebuild", "check", "search", "report"))
    ap.add_argument("--arms", default="YT")
    ap.add_argument("--shard", type=parse_shard, default=(0, 1))
    ap.add_argument("--min-free-gb", type=float, default=None,
                    help="search only: override the 31 GB free-disk guard for this run (logged)")
    a = ap.parse_args(argv)
    arms = tuple(x for x in a.arms.split(",") if x)
    if any(x not in ARMS for x in arms):
        raise SystemExit(f"arms must be among {ARMS}")
    if a.cmd == "search":
        cmd_search(arms, a.shard, a.min_free_gb)
    elif a.cmd == "rebuild":
        if len(arms) != 1 or arms[0] not in ("YT", "YG"):
            raise SystemExit("rebuild takes one arm: YT or YG")
        cmd_rebuild(arms[0])
    else:
        {"check": cmd_check, "report": cmd_report}[a.cmd]()


if __name__ == "__main__":
    main()
