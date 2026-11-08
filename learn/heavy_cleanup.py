"""Too-heavy recordings out of W's plugin rows and the test sets (`docs/heavy-cleanup-plan.md`, the user's yes of
2026-11-08; ledger `pipeline-fix`, `phase_h1` on). H1 here: does the dry path change only what it should? Each row is
rendered again with its time effects, spring and room mics off (the dry twin), in its own new plugin process with one
discarded priming render of the same setting and a 0.25 s trim, as `cc_build.render_target` renders D_CC's targets;
15 rows are rendered again as stored, which must reproduce the stored target. Outputs go to `PF/heavy/`; D_CC's
stored targets are read, never written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    $MAIN -m learn.heavy_cleanup pilot-draw                   # zero renders: H1's 75 rows -> heavy/h1-plan.json
    $MAIN -u -m learn.heavy_cleanup pilot-render --shard k/3  # 150 renders with their priming renders
    $MAIN -m learn.heavy_cleanup pilot-read                   # zero renders: shifts by family, the margin, the checks
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

HEAVY_DIR = "heavy"
H1 = "phase_h1"
SEED = 20261108
HEAVY_BANDS = ("Ale Lak", "Storm Of Particles")      # out by the proposal the user approved
TIME = {"reverb": ("reverb", "reverbActive"), "delay": ("delay", "delayActive"),
        "tremolo": ("tremolo", "tremoloActive"), "doubler": ("parameters", "doublerActive")}
SPRING = {"pr12": ("pr12Amp", "pr12Reverb"), "sw50r": ("sw50rAmp", "sw50rReverb")}   # full_space.SPRING
ROOMS = (("cabParameters", "leftRoomActive", "leftCabActive"), ("cabParameters", "rightRoomActive", "rightCabActive"))
FAMILIES = ("reverb", "delay", "doubler", "tremolo", "spring", "room")
PER_FAMILY = 10                                      # single-switch rows rendered dry, per family
N_SAME = 10                                          # rows with no switch on, rendered again as stored
N_ON = 5                                             # rows with a switch on, rendered again as stored
RESIDUAL_DB = -90.0                                  # a render again as stored: bit-identical, or a residual under this
MARGIN_DB = 0.5                                      # the least margin m
LATENCY = 52                                         # the meter's lag on plugin renders (PS.LATENCY)


def dry_keys():
    """Every (module, key) the dry twin may change."""
    return ({*TIME.values()} | {*SPRING.values()} | {(m, r) for m, r, _ in ROOMS})


def _on(v):
    return str(v).lower() == "true"


def switches(s, amp):
    """The dry switches on in a stored setting ("module/key" form): time effects, the amp's spring above 0, a room mic
    on an active cab. -> [family]."""
    out = [f for f, (m, k) in TIME.items() if _on(s.get(f"{m}/{k}"))]
    if amp in SPRING and float(s.get("/".join(SPRING[amp])) or 0) > 0:
        out.append("spring")
    if any(_on(s.get(f"{m}/{r}")) and _on(s.get(f"{m}/{c}")) for m, r, c in ROOMS):
        out.append("room")
    return out


def dry(x, amp):
    """The dry twin of a plugin setting ({(module, key): value}) on `amp`: time effects off, that amp's spring at 0, both
    room mics off, nothing else changed (the other amps' knobs stay). Only keys the setting holds are set."""
    y = dict(x)
    for p in TIME.values():
        if p in y:
            y[p] = "false"
    if amp in SPRING and SPRING[amp] in y:
        y[SPRING[amp]] = "0"
    for m, r, _ in ROOMS:
        if (m, r) in y:
            y[(m, r)] = "false"
    return y


def check_dry(x, y):
    """Refuses a dry setting that differs from its twin outside the declared keys, or that adds a key."""
    if set(y) != set(x):
        raise SystemExit("the dry setting's keys differ from the twin's")
    bad = sorted(f"{a}/{b}" for (a, b) in x if x[(a, b)] != y[(a, b)] and (a, b) not in dry_keys())
    if bad:
        raise SystemExit(f"the dry setting changes undeclared keys: {bad}")


def heavy_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / HEAVY_DIR


def cc_args():
    return argparse.Namespace(out=None, smoke=False)


def cc_examples():
    from learn import cc_build as CB

    return {int(x["i"]): x for x in CB.load_plan(cc_args())["examples"]}


def w_rows():
    """W's training rows outside the heavy bands, with their plan entries. -> [plan example]."""
    from learn import bakeoff as B

    rows, _ = B.plugin_set()
    ex = cc_examples()
    return [ex[int(r["i"])] for r in rows if r["band"] not in HEAVY_BANDS]


def draw(rows, seed=SEED):
    """H1's rows: PER_FAMILY single-switch rows per family, N_SAME with no switch, N_ON with any switch, disjoint,
    drawn in that order from rows sorted by id. -> [{i, kind, family}]."""
    rng = random.Random(seed)
    rows = sorted(rows, key=lambda x: int(x["i"]))
    sw = {int(x["i"]): switches(x["settings"], x["amp"]) for x in rows}
    out, used = [], set()
    for f in FAMILIES:
        pool = [i for i, s in sw.items() if s == [f]]
        if len(pool) < PER_FAMILY:
            raise SystemExit(f"{f}: {len(pool)} single-switch rows, {PER_FAMILY} needed")
        for i in rng.sample(pool, PER_FAMILY):
            out.append({"i": i, "kind": "dry", "family": f})
            used.add(i)
    for kind, n, pick in (("same", N_SAME, lambda s: not s), ("same", N_ON, bool)):
        pool = [i for i, s in sw.items() if pick(s) and i not in used]
        for i in rng.sample(pool, n):
            out.append({"i": i, "kind": kind, "family": "+".join(sw[i]) or "none"})
            used.add(i)
    return out


def di_path(x):
    """The example's DI file: its session folder and the DI's path inside it."""
    sd = pathlib.Path(x["session_dir"])
    tail = x["di"].split("/", 2)[2]
    p = sd / tail
    if p.exists():
        return p
    hits = sorted(sd.rglob(pathlib.Path(tail).name))
    if len(hits) != 1:
        raise SystemExit(f"{x['i']}: the DI {tail} is not found once under {sd}")
    return hits[0]


def start_of(x):
    return float(x["section"].rsplit("@", 1)[1])


def cmd_pilot_draw(_args):
    from learn import pipeline_fix as P

    P.require(H1)
    rows = w_rows()
    items = draw(rows)
    out = heavy_dir() / "h1-plan.json"
    if out.exists():
        raise SystemExit(f"{out} exists: H1's draw is fixed")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"phase": H1, "seed": SEED, "rows": len(rows), "items": items,
                               "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
    by = {}
    for it in items:
        by[it["kind"]] = by.get(it["kind"], 0) + 1
    print(f"H1 DRAW: {len(items)} rows of {len(rows)} ({by}) -> {out}")


def render_one(x, it, menus, make):
    """One row in its own new process: its full twin (checked against the plan), dry or as stored, one priming render of
    the same setting. -> (trimmed mono render, setting rendered as "module/key")."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data_t3 as T3

    amp, _, base, sel, xf, _, _, _ = T3.full_twin(it["i"], menus)
    if amp != x["amp"] or base != x["base"] or LO.sdict(xf) != x["settings"]:
        raise SystemExit(f"{it['i']}: the full twin differs from the plan's draw")
    xs = xf
    if it["kind"] == "dry":
        xs = dry(xf, amp)
        check_dry(xf, xs)
        if xs == xf:
            raise SystemExit(f"{it['i']}: the dry twin changes nothing")
    di = B.measure(PS.section_audio(str(di_path(x)), start_of(x))).astype(np.float32)
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    y = AM.fresh_render(make, di, sel, xs, xs)
    return (y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]], LO.sdict(xs)


def cmd_pilot_render(args):
    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import trusted_data as T
    from learn import trusted_data_t3 as T3

    P.require(H1)
    k, n = args.shard
    plan = json.loads((heavy_dir() / "h1-plan.json").read_text())
    rp = heavy_dir() / "h1" / f"render-{k}of{n}.jsonl"
    done = {json.loads(l)["i"] for l in rp.read_text().splitlines()} if rp.exists() else set()
    todo = [it for j, it in enumerate(plan["items"]) if j % n == k and it["i"] not in done]
    if not todo:
        print(f"H1 RENDER DONE {k}/{n} (nothing to do)")
        return
    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"free disk below {T.DISK_GUARD_GB:.0f} GB")
    cc = CB.load_plan(cc_args())
    ex = {int(x["i"]): x for x in cc["examples"]}
    menus = T3.Menus()
    menus.gate_u = cc["gate_cap"]["unit"]
    LO._wait_cap()
    rr = CB.new_renderer()
    try:
        T3.check_menu(rr.menu(), menus.dried)
        if abs(CB.F_gate(menus) - cc["gate_cap"]["unit"]) > 1e-12:
            raise SystemExit("the factory gate thresholds changed since D_CC's plan")
    finally:
        rr.close()
    rp.parent.mkdir(parents=True, exist_ok=True)
    renders = 0
    with open(rp, "a") as fh:
        for it in todo:
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"free disk below {T.DISK_GUARD_GB:.0f} GB")
            y, st = render_one(ex[it["i"]], it, menus, CB.new_renderer)
            renders += 2
            f = heavy_dir() / "h1" / "audio" / f"{it['i']:07d}-{it['kind']}.flac"
            sc, sha = G.write_flac(f, y, PS.SR)
            fh.write(json.dumps({**it, "file": f.name, "scale": sc, "sha256": sha, "settings": st}) + "\n")
            fh.flush()
            print(f"{it['kind']} {it['family']} {it['i']}: renders {renders}", flush=True)
    print(f"H1 RENDER DONE {k}/{n}: {renders} renders (priming included)")


def residual_db(a, b):
    """10 log10 of the residual's energy against b's. -inf when identical."""
    import numpy as np

    n = min(len(a), len(b))
    e = float(np.sum((a[:n] - b[:n]) ** 2))
    return -math.inf if e == 0 else 10 * math.log10(e / float(np.sum(b[:n] ** 2)))


def measure(y, x):
    """The first read's meter: `gainmeasure` against the raw DI section, at the plugin's latency. -> dB or None."""
    import numpy as np

    from learn import pretrain_set as PS

    sys.path.insert(0, str(PS.HOME / "references/datasets-set3/_tools"))
    import gainmeasure as GM

    di = np.asarray(PS.section_audio(str(di_path(x)), start_of(x)), np.float64)
    di = di[int(PS.TRIM_S * PS.SR):int((PS.TRIM_S + PS.SEC_S) * PS.SR)]
    m = GM.measures(y, di, PS.SR, lag=LATENCY)
    return None if not m else float(m["nonlinear_to_linear_db"])


def margin(shifts, least=MARGIN_DB):
    """m: the least margin, or the worst negative shift if larger in size."""
    worst = min(shifts) if shifts else 0.0
    return max(least, -worst)


def cmd_pilot_read(_args):
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import pipeline_fix as P
    from learn import trusted_data as T
    from learn import verify_tracks as V

    P.require(H1)
    plan = json.loads((heavy_dir() / "h1-plan.json").read_text())
    rows = {}
    for f in sorted((heavy_dir() / "h1").glob("render-*.jsonl")):
        for l in f.read_text().splitlines():
            r = json.loads(l)
            rows[r["i"]] = r
    missing = [it["i"] for it in plan["items"] if it["i"] not in rows]
    if missing:
        raise SystemExit(f"{len(missing)} of H1's rows are not rendered")
    ex = cc_examples()
    root = V.out_root(cc_args())
    built = T.rows_of(root, "cc", "render")
    out, checks = [], []
    for it in plan["items"]:
        x, r, b = ex[it["i"]], rows[it["i"]], built[it["i"]]["target"]
        stored = G.read_flac(T.flac_path(root, "cc", it["i"], "target"), b["scale"], b["sha256"])
        new = G.read_flac(heavy_dir() / "h1" / "audio" / r["file"], r["scale"], r["sha256"])
        if it["kind"] == "same":
            res = residual_db(new, stored)
            checks.append({"i": it["i"], "family": it["family"], "identical": bool(np.array_equal(new, stored)),
                           "residual_db": res, "ok": res < RESIDUAL_DB})
        else:
            a, b = measure(stored, x), measure(new, x)
            out.append({"i": it["i"], "family": it["family"], "amp": x["amp"], "base": x["base"], "stored_db": a, "dry_db": b,
                        "shift_db": None if a is None or b is None else a - b})
    shifts = [o["shift_db"] for o in out if o["shift_db"] is not None]
    fam = {}
    for f in FAMILIES:
        v = sorted(o["shift_db"] for o in out if o["family"] == f and o["shift_db"] is not None)
        fam[f] = {"n": len(v), "median": float(np.median(v)) if v else None, "min": v[0] if v else None, "max": v[-1] if v else None}
    rep = {"phase": H1, "families": fam, "worst_shift_db": min(shifts) if shifts else None, "margin_db": margin(shifts),
           "unmeasured": [o["i"] for o in out if o["shift_db"] is None], "checks_ok": all(c["ok"] for c in checks),
           "checks": checks, "rows": out}
    (heavy_dir() / "h1-read.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("families", "worst_shift_db", "margin_db", "unmeasured", "checks_ok")}, indent=1))
    if not rep["checks_ok"]:
        raise SystemExit("a render again as stored did not reproduce its target: H2 stops")


def main(argv=None):
    from learn import cc_pool as CP

    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pilot-draw").set_defaults(fn=cmd_pilot_draw)
    s = sub.add_parser("pilot-render")
    s.add_argument("--shard", type=CP.parse_shard, default=(0, 1))
    s.set_defaults(fn=cmd_pilot_render)
    sub.add_parser("pilot-read").set_defaults(fn=cmd_pilot_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
