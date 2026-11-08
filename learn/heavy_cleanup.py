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
    $MAIN -m learn.heavy_cleanup line                         # the declared line (+1.05 dB; superseded, Amendment 1)
    $MAIN -m learn.heavy_cleanup check-measure                # Amendment 1: W's stored flatness -> heavy/check/flatness.json
    $MAIN -m learn.heavy_cleanup check-page                   # the 50-card check page -> heavy/check/page.html, key.json
    $MAIN -m learn.heavy_cleanup check-answers STORED.json    # the plugin line -> heavy/check/verdicts.json
    $MAIN -m learn.heavy_cleanup real-flat-line               # for the record: GOAT's line on flatness
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys
import time
from fractions import Fraction

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

HEAVY_DIR = "heavy"
H1 = "phase_h1"
H2 = "phase_h2"
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


OFF = {**{p: "false" for p in TIME.values()}, **{(m, r): "false" for m, r, _ in ROOMS}, **{p: "0" for p in SPRING.values()}}


def dry_keys(amp):
    """Every (module, key) the dry twin on `amp` may change: the time effects, that amp's spring, the room mics."""
    return {*TIME.values(), *([SPRING[amp]] if amp in SPRING else []), *((m, r) for m, r, _ in ROOMS)}


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


def check_dry(x, y, amp):
    """Refuses a dry setting that differs from its twin outside `amp`'s declared keys, sets one to anything but off, or
    adds a key."""
    if set(y) != set(x):
        raise SystemExit("the dry setting's keys differ from the twin's")
    bad = sorted(f"{a}/{b}" for (a, b) in x if x[(a, b)] != y[(a, b)] and ((a, b) not in dry_keys(amp) or y[(a, b)] != OFF[(a, b)]))
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
    if not p.exists():
        raise SystemExit(f"{x['i']}: the DI {p} is missing")
    return p


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
        check_dry(xf, xs, amp)
        if xs == xf:
            raise SystemExit(f"{it['i']}: the dry twin changes nothing")
    di = B.measure(PS.section_audio(str(di_path(x)), start_of(x))).astype(np.float32)
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    y = AM.fresh_render(make, di, sel, xs, xs)
    return (y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]], LO.sdict(xs)


def cmd_pilot_render(args):
    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import trusted_data as T
    from learn import trusted_data_t3 as T3

    P.require(H1)
    k, n = args.shard
    plan = json.loads((heavy_dir() / "h1-plan.json").read_text())
    rp = heavy_dir() / "h1" / f"render-{k}of{n}.jsonl"
    done = {json.loads(l)["i"] for f in (heavy_dir() / "h1").glob("render-*.jsonl") for l in f.read_text().splitlines() if l.strip()}
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
    swap0 = DS.swap_mb()
    with open(rp, "a") as fh:
        for it in todo:
            g = DS._guards("h1-render", T.DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
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

    if len(a) != len(b):
        return math.inf
    e = float(np.sum((a - b) ** 2))
    return -math.inf if e == 0 else 10 * math.log10(e / float(np.sum(b ** 2)))


def measure(y, x):
    """The first read's meter: `gainmeasure` against the raw DI section, at the plugin's latency. -> dB or None."""
    import numpy as np

    from learn import pretrain_set as PS

    tools = str(PS.HOME / "references/datasets-set3/_tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
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
        x, r, tg = ex[it["i"]], rows[it["i"]], built[it["i"]]["target"]
        stored = G.read_flac(T.flac_path(root, "cc", it["i"], "target"), tg["scale"], tg["sha256"])
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


# --- the line (zero renders; after the keep-or-drop answers) -----------------------------------------------------

FLOOR_DB = -3.0                                      # recordings under this are not used: the line can't fall below it
BIN_DB = 2.0
BIN_MIN, BIN_CLUSTERS = 8, 4                         # a bin with fewer merges up; the top bin merges down
BOOT, BOOT_SEED = 2000, 20261108


def cluster_of(unit):
    """The DI: a BKS DI track, a GOAT item."""
    return unit.split("@", 1)[0]


def weighted(points):
    """[(db, heavy, cluster)] -> [(db, heavy, weight)], weight one over the cluster's count among them, exact, so a fit
    of exactly one half reads as one half."""
    n = {}
    for _, _, c in points:
        n[c] = n.get(c, 0) + 1
    return [(x, y, Fraction(1, n[c])) for x, y, c in points]


def isotonic(points):
    """A weighted non-decreasing fit of heavy on the measure (pool-adjacent-violators, equal measures pooled first).
    points: [(db, heavy 0/1, weight)] -> [(db, fitted)] by measure."""
    by = {}
    for x, y, w in points:
        a = by.setdefault(x, [Fraction(0), Fraction(0)])
        a[0] += w * y
        a[1] += w
    blocks = []                                      # [sum wy, sum w, [xs]]
    for x in sorted(by):
        blocks.append([by[x][0], by[x][1], [x]])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            b = blocks.pop()
            blocks[-1][0] += b[0]
            blocks[-1][1] += b[1]
            blocks[-1][2] += b[2]
    return [(x, float(b[0] / b[1])) for b in blocks for x in b[2]]


def floored(points, floor):
    return list(points) if floor is None else [p for p in points if p[0] >= floor]


def line_of(points, floor=FLOOR_DB):
    """The lowest measured value at which the fit reaches one half, or None. points: [(db, heavy, cluster)]; floor None
    uses every point."""
    fit = isotonic(weighted(floored(points, floor)))
    return next((x for x, f in fit if f >= 0.5), None)


def bins_of(points, floor=FLOOR_DB):
    """The binned form: 2 dB bins from the floor (or from the lowest point, rounded down to a bin, when floor is None),
    merged up while short (under BIN_MIN recordings or BIN_CLUSTERS clusters), the top merged down.
    -> [{lo, hi, n, clusters, share}] with the weighted share."""
    pts = floored(points, floor)
    if not pts:
        return []
    w = [q[2] for q in weighted(pts)]
    edges = [floor if floor is not None else BIN_DB * math.floor(min(x for x, _, _ in pts) / BIN_DB)]
    while edges[-1] <= max(x for x, _, _ in pts):
        edges.append(edges[-1] + BIN_DB)
    raw = [[lo, hi, [k for k, (x, _, _) in enumerate(pts) if lo <= x < hi]] for lo, hi in zip(edges, edges[1:])]

    def short(b):
        return len(b[2]) < BIN_MIN or len({pts[k][2] for k in b[2]}) < BIN_CLUSTERS

    out = []
    for b in raw:
        if out and short(out[-1]):
            out[-1][1], out[-1][2] = b[1], out[-1][2] + b[2]
        else:
            out.append(b)
    while len(out) > 1 and short(out[-1]):
        b = out.pop()
        out[-1][1], out[-1][2] = b[1], out[-1][2] + b[2]
    return [{"lo": lo, "hi": hi, "n": len(ks), "clusters": len({pts[k][2] for k in ks}),
             "share": float(sum(w[k] * pts[k][1] for k in ks) / sum(w[k] for k in ks)) if ks else None} for lo, hi, ks in out]


def bin_line(bins):
    return next((b["lo"] for b in bins if b["share"] is not None and b["share"] >= 0.5), None)


def boot_lines(points, boot=BOOT, seed=BOOT_SEED, floor=FLOOR_DB, each_one=False):
    """The line on cluster-bootstrap resamples of the fit's population (the clusters with a recording at or over the
    floor; a resampled cluster's recordings keep their own cluster, numbered apart). -> [line or None]."""
    rng = random.Random(seed)
    by = {}
    for p in floored(points, floor):
        by.setdefault(p[2], []).append(p)
    cs = sorted(by)
    out = []
    for _ in range(boot):
        pts = [(x, y, f"{c}#{k}" + (f"#{m}" if each_one else "")) for k, c in enumerate(rng.choice(cs) for _ in cs)
               for m, (x, y, _) in enumerate(by[c])]
        out.append(line_of(pts, floor))
    return out


def answer_points(nl, verdicts, marks, unsure_heavy=True, ear_eat_keeps=True, eat_only=frozenset()):
    """[(db, heavy, cluster)] from the page's verdicts and the earlier marks. A page verdict wins over a mark."""
    out = []
    for u, x in nl.items():
        if u in verdicts:
            v = verdicts[u]
            if v == "unsure" and not unsure_heavy:
                continue
            out.append((x, int(v != "keep"), cluster_of(u)))
        elif u in marks:
            if marks[u] == "keep" and u in eat_only and not ear_eat_keeps:
                continue
            out.append((x, int(marks[u] == "out"), cluster_of(u)))
    return out


def eat_only_keeps():
    """Units answered only on ear-eat's cards (their mark keep or out; `answer_points` drops only the keeps)."""
    from learn import ear_eat as EE
    from learn import pipeline_fix as P

    root = P.out_dir()
    pages = {}
    for u, v in json.loads((root / P.GOAT_DIR / "heavy.json").read_text())["verdicts"].items():
        pages.setdefault(u, set()).add("goat-heavy")
    for page, sub, name in (("ear-eat-1", "eat/ear", "answers.txt"), ("ear-eat-2", "eat/ear2", "answers.json")):
        answers = EE.stored_answers((root / sub / name).read_text())["answers"]
        for it in json.loads((root / sub / "key.json").read_text())["items"]:
            if it["id"] in answers:
                pages.setdefault(it["unit"], set()).add(page)
    return frozenset(u for u, ps in pages.items() if ps and ps <= {"ear-eat-1", "ear-eat-2"})


def cmd_line(_args):
    from learn import ear_eat as EE
    from learn import pipeline_fix as P
    from learn import scope_page as SP

    P.require(H2)
    d = SP.scope_dir()
    lst = json.loads((d / "list.json").read_text())
    ver = json.loads((d / "verdicts.json").read_text())["verdicts"]
    if set(ver) != set(lst["ask"]):
        raise SystemExit("verdicts.json is not from this list's asked recordings")
    nl, marks = dict(lst["nl"]), dict(lst["marks"])
    goat = {u["unit"]: u for u in P.goat_units()}
    heavy = json.loads((P.out_dir() / P.GOAT_DIR / "heavy.json").read_text())["verdicts"]
    extra = {u: v for u, v in heavy.items() if u not in nl}
    missing = [u for u in extra if u not in goat]
    if missing:
        raise SystemExit(f"goat-heavy units with no GOAT part: {missing}")
    bad = {u: v["verdict"] for u, v in heavy.items() if v["verdict"] not in ("keep", "heavy")}
    if bad:
        raise SystemExit(f"goat-heavy verdicts outside keep and heavy: {bad}")
    for u, v in extra.items():
        nl[u] = EE.nonlinear_db("goat", goat[u])
        marks[u] = "keep" if v["verdict"] == "keep" else "out"
    if any(v is None for v in nl.values()):
        raise SystemExit("a recording has no measure")
    eat = eat_only_keeps()
    main = answer_points(nl, ver, marks)
    rows = {"primary": main, "unsure_neither": answer_points(nl, ver, marks, unsure_heavy=False),
            "no_ear_eat_keeps": answer_points(nl, ver, marks, ear_eat_keeps=False, eat_only=eat)}
    boot = boot_lines(main)
    got = [b for b in boot if b is not None]
    got.sort()
    rep = {"phase": H2, "line_db": line_of(main), "bins": bins_of(main), "bin_line_db": bin_line(bins_of(main)),
           "boot": {"n": len(boot), "none_share": (len(boot) - len(got)) / len(boot), "interval_over": "resamples with a line",
                    "lo90": got[int(0.05 * len(got))] if got else None, "hi90": got[min(len(got) - 1, int(0.95 * len(got)))] if got else None},
           "beside": {k: {"line_db": line_of(v), "bin_line_db": bin_line(bins_of(v)), "n": len([p for p in v if p[0] >= FLOOR_DB])}
                      for k, v in rows.items() if k != "primary"},
           "n": len([p for p in main if p[0] >= FLOOR_DB]), "goat_heavy_measured": {u: nl[u] for u in extra},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    (heavy_dir() / "line.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("line_db", "bin_line_db", "boot", "beside", "n")}, indent=1))


# --- Amendment 1: flatness and the plugin check page (zero renders) ------------------------------------------------

H2A = "phase_h2a"
CHECK_DIR = "check"
CHECK_SEED = 20261110
BAND_PCTS = (50, 75, 90)                             # the check page's bands: the rows under their median, to the 75th,
                                                     # to the 90th, and over (a real line does not carry over: sources
                                                     # differ in scale)


def check_bands(flat_values):
    """((lo, hi), ...) by the given rows' own flatness percentiles (the page passes the doubler-free rows)."""
    import numpy as np

    v = list(flat_values)
    e = [float(np.percentile(v, q)) for q in BAND_PCTS]
    return ((None, e[0]), (e[0], e[1]), (e[1], e[2]), (e[2], None))
PER_BAND = 10
AMPS = ("ac20", "pr12", "sw50r")
FRAME, HOP = 4096, 2048                              # gainmeasure's frames


def flatness_db(amp, di):
    """How flat the amp's spectrum is, with each frame's own tone taken out: per Hann frame of 4096 (hop 2048), the
    power spectrum divided by its 1/3-octave moving average, then the flatness (geometric over arithmetic mean) over
    200-5000 Hz; 10 log10 of the median over the frames where both play (the DI within 30 dB of its loudest, the amp
    within 40 dB of its own, so a gated frame does not read flat). The amp side alone, as the ear hears it: the DI only
    picks the frames (subtracting the DI's own value made plugin rows read their section's DI, Amendment 1's review).
    Distortion fills the spectrum between a note's harmonics; an EQ, cab or room tilt does not move it. Mono, aligned,
    the amp at least as long as the DI. -> dB, or None for a silent amp, no shared frame or under one frame."""
    import numpy as np

    from learn import pretrain_set as PS

    if amp.ndim != 1 or di.ndim != 1 or len(amp) < len(di):
        raise ValueError("flatness_db: mono signals, the amp at least as long as the DI")
    n = (len(di) - FRAME) // HOP + 1
    if n < 1:
        return None
    idx = np.arange(FRAME)[None, :] + HOP * np.arange(n)[:, None]
    fa, fd = amp[idx], di[idx]

    def level(x):
        return 20 * np.log10(np.sqrt(np.mean(x ** 2, axis=1)) + 1e-12)

    rd, ra = level(fd), level(fa)
    act = (rd >= rd.max() - 30) & (ra >= ra.max() - 40)
    if ra.max() < -90 or not act.any():                  # a silent amp or no shared frame: no reading, never "flat"
        return None
    win = np.hanning(FRAME)
    f = np.fft.rfftfreq(FRAME, 1 / PS.SR)
    bins = np.where((f >= 200) & (f < 5000))[0]
    lo = np.searchsorted(f, f[bins] * 2 ** (-1 / 6))
    hi = np.searchsorted(f, f[bins] * 2 ** (1 / 6), side="right")
    M = np.zeros((len(f), len(bins)))                # each bin's 1/3-octave average, exact (no cumulative-sum loss)
    for k, (a, b) in enumerate(zip(lo, hi)):
        M[a:b, k] = 1.0 / (b - a)

    def flat(x):
        S = np.abs(np.fft.rfft(x[act] * win, axis=1)) ** 2 + 1e-20
        R = S[:, bins] / (S @ M)
        return float(10 * np.log10(np.median(np.exp(np.mean(np.log(R), axis=1)) / np.mean(R, axis=1))))

    return flat(fa)


def plugin_flatness(x, y):
    """A plugin row's flatness: its render, the plugin's latency trimmed, against the DI as it was fed to the plugin
    (`song_bank.measure`'s, as on the real side)."""
    import numpy as np

    from learn import pretrain_set as PS
    from learn import song_bank as B

    di = np.asarray(B.measure(PS.section_audio(str(di_path(x)), start_of(x))), np.float64)
    di = di[int(PS.TRIM_S * PS.SR):int((PS.TRIM_S + PS.SEC_S) * PS.SR)]
    n = min(len(y) - LATENCY, len(di))
    return flatness_db(y[LATENCY:LATENCY + n], di[:n])


def real_flatness(prt):
    """A real recording's flatness on `nonlinear_db`'s audio path."""
    import numpy as np

    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B

    trim = int(PS.TRIM_S * PS.SR)
    di = np.asarray(B.measure(PS.section_audio(prt["di_path"], prt["start_s"])), np.float64)[trim:]
    amp = np.asarray(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64)
    n = min(len(di), len(amp))
    return flatness_db(amp[:n], di[:n])


def song_of(unit_or_section):
    """A song: a GOAT item, or a session folder ("set/Song_Full")."""
    s = unit_or_section.split("@", 1)[0]
    return s if s.startswith("goat/") else "/".join(s.split("/")[:2])


def stored_target(i):
    from learn import direct_sound_gate as G
    from learn import trusted_data as T
    from learn import verify_tracks as V

    root = V.out_root(cc_args())
    tg = _built()[i]["target"]
    return G.read_flac(T.flac_path(root, "cc", i, "target"), tg["scale"], tg["sha256"])


_BUILT = {}


def _built():
    from learn import trusted_data as T
    from learn import verify_tracks as V

    if not _BUILT:
        _BUILT.update(T.rows_of(V.out_root(cc_args()), "cc", "render"))
    return _BUILT


def _flat_one(x):
    return int(x["i"]), plugin_flatness(x, stored_target(int(x["i"])))


def cmd_check_measure(_args):
    """Stored flatness of W's rows outside the heavy bands -> heavy/check/flatness.json."""
    from multiprocessing import Pool

    from learn import pipeline_fix as P

    P.require(H2A)
    rows = w_rows()
    with Pool(3) as pool:
        got = dict(pool.map(_flat_one, rows, chunksize=8))
    bad = [i for i, v in got.items() if v is None or not math.isfinite(v)]
    if bad:
        raise SystemExit(f"{len(bad)} rows have no flatness reading: {bad[:5]}")
    out = heavy_dir() / CHECK_DIR / "flatness.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"phase": H2A, "flatness_db": {str(i): v for i, v in sorted(got.items())},
                               "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
    print(f"CHECK MEASURE: {len(got)} rows -> {out}")


def no_doubler(rows):
    """Rows with the doubler off: the cards' and the line's population."""
    return [x for x in rows if not _on(x["settings"].get("/".join(TIME["doubler"])))]


def in_band(v, band):
    lo, hi = band
    return (lo is None or v >= lo) and (hi is None or v < hi)


def check_draw(rows, flat, bands, seed=CHECK_SEED):
    """PER_BAND rows a flatness band, songs round robin (each round one row a song, the band's least used amp first),
    no section twice. rows: [plan example]; flat: {i: dB}. -> [{i, band, amp, section}] in band order."""
    rng = random.Random(seed)
    used, out = set(), []
    for k, band in enumerate(bands):
        songs = {}
        for x in sorted(rows, key=lambda x: int(x["i"])):
            if in_band(flat[int(x["i"])], band):
                songs.setdefault(song_of(x["section"]), []).append(x)
        order = sorted(songs)
        rng.shuffle(order)
        for v in songs.values():
            rng.shuffle(v)
        got, amps = [], {a: 0 for a in AMPS}
        while len(got) < PER_BAND and any(songs[c] for c in order):
            for c in order:
                if len(got) >= PER_BAND:
                    break
                free = [x for x in songs[c] if x["section"] not in used]
                songs[c] = free
                if not free:
                    continue
                x = min(free, key=lambda x: amps.get(x["amp"], 0))
                free.remove(x)
                used.add(x["section"])
                amps[x["amp"]] = amps.get(x["amp"], 0) + 1
                got.append({"i": int(x["i"]), "band": k, "amp": x["amp"], "section": x["section"]})
        if len(got) < PER_BAND:
            raise SystemExit(f"band {band}: {len(got)} rows, {PER_BAND} needed")
        out += got
    return out


PAIRS = 5                                            # sections with two cards: their lowest- and highest-flatness rows


def pair_draw(rows, flat, bands, used, seed=CHECK_SEED + 2):
    """PAIRS sections not on the band cards, seeded among those whose rows span the bands (the lowest under the bands'
    median edge, the highest at or past their 90th-percentile edge), then the widest if too few; each gives its lowest-
    and highest-flatness rows, one section a song. -> [{i, band: "pair", amp, section, pair}]."""
    lo_edge, hi_edge = bands[0][1], bands[3][0]
    rng = random.Random(seed)
    by = {}
    for x in rows:
        by.setdefault(x["section"], []).append(x)
    ok = {sec: sorted(v, key=lambda x: flat[int(x["i"])]) for sec, v in sorted(by.items()) if sec not in used and len(v) >= 2}
    straddle = [sec for sec, v in ok.items() if flat[int(v[0]["i"])] < lo_edge and flat[int(v[-1]["i"])] >= hi_edge]
    rng.shuffle(straddle)
    rest = sorted((sec for sec in ok if sec not in straddle), key=lambda sec: flat[int(ok[sec][0]["i"])] - flat[int(ok[sec][-1]["i"])])
    out, songs = [], set()
    for sec in straddle + rest:
        if len(out) >= 2 * PAIRS:
            break
        if song_of(sec) in songs:
            continue
        songs.add(song_of(sec))
        for x in (ok[sec][0], ok[sec][-1]):
            out.append({"i": int(x["i"]), "band": "pair", "amp": x["amp"], "section": sec, "pair": len(out) // 2})
    if len(out) < 2 * PAIRS:
        raise SystemExit(f"{len(out) // 2} pair sections, {PAIRS} needed")
    return out


def check_item_id(i, seed=CHECK_SEED):
    import hashlib

    return "p" + hashlib.sha256(f"{seed}|{i}".encode()).hexdigest()[:12]


def cmd_check_page(_args):
    import hashlib

    from learn import build_data_review as BDR
    from learn import pipeline_fix as P
    from learn import scope_page as SP

    P.require(H2A)
    d = heavy_dir() / CHECK_DIR
    if (d / "key.json").exists():
        raise SystemExit(f"{d / 'key.json'} exists: a rebuild hides the listener's stored answers; move it aside first")
    flat = {int(k): v for k, v in json.loads((d / "flatness.json").read_text())["flatness_db"].items()}
    rows = no_doubler(w_rows())                      # the doubler reads less flat (Amendment 1): its rows are measured
    bands = check_bands(flat[int(x["i"])] for x in rows)  # doubler off and cut at the line, never carded
    drawn = check_draw(rows, flat, bands)
    drawn += pair_draw(rows, flat, bands, {it["section"] for it in drawn})
    order = list(drawn)
    random.Random(CHECK_SEED + 1).shuffle(order)
    items, clips = [], {}
    for it in order:
        cid = check_item_id(it["i"])
        y, gain, _, cut = BDR.level_clip(stored_target(it["i"]))
        clips[cid] = SP.encode(y, d / "aac-cache")
        items.append({"id": cid, **it, "flatness_db": flat[it["i"]], "song": song_of(it["section"]), "gain_db": gain, "peak_cut_db": cut})
    ids = [it["id"] for it in items]
    build = hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:12]
    page = SP.page_html(ids, clips, build).replace("<title>Keep Or Drop</title>", "<title>Keep Or Drop Two</title>")
    words = {song_of(it["section"]).split("/")[-1] for it in items} | {pathlib.Path(it["section"].split("@")[0]).name for it in items}
    shown = SP.leaks(page, sorted(words))
    if shown:
        raise SystemExit(f"the page names {shown}")
    (d / "page.html").write_text(page)
    (d / "key.json").write_text(json.dumps({"page": CHECK_DIR, "build": build, "seed": CHECK_SEED, "bands": bands, "items": items,
                                            "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
    print(f"CHECK PAGE DONE: {len(items)} cards, build {build}, {len(page) / 1e6:.1f} MB -> {d / 'page.html'}")


def check_read(items, got, pool, bands):
    """The check page's read. items: key.json's cards; got: {str(i): verdict}; pool: the doubler-free rows' sorted
    flatness; bands: the page's bands. -> the line on the band cards (each weighing one, songs resampled), the
    percentiles, the drop share per band, the pairs' read, and the undecided flags."""
    import bisect

    bandc = [it for it in items if it["band"] != "pair"]
    v = lambda it: got[str(it["i"])]
    pts = [(it["flatness_db"], int(v(it) != "keep"), it["song"]) for it in bandc]
    neither = [(it["flatness_db"], int(v(it) == "heavy"), it["song"]) for it in bandc if v(it) != "unsure"]
    pairs = {}
    for it in items:
        if it["band"] == "pair":
            pairs.setdefault(it["pair"], []).append((it["flatness_db"], int(v(it) != "keep")))
    split = [sorted(p) for p in pairs.values() if sum(y for _, y in p) == 1]
    card = lambda q: [(x, y, f"card{k}") for k, (x, y, _) in enumerate(q)]            # each card weighs one
    boot = boot_lines(pts, floor=None, each_one=True)                                   # songs resampled
    have = sorted(b for b in boot if b is not None)

    def pct(x):
        return None if x is None else 100.0 * bisect.bisect_left(pool, x) / len(pool)

    line = line_of(card(pts), None)
    lo90 = have[int(0.05 * len(have))] if have else None
    hi90 = have[min(len(have) - 1, int(0.95 * len(have)))] if have else None
    flatter = sum(1 for p in split if p[1][1] == 1)
    line_band = None if line is None else next(k for k, b in enumerate(bands) if in_band(line, b))
    undecided = [w for w, c in (("no line", line is None), ("the line falls in the lowest band", line_band == 0),
                                ("the pairs do not favour the flatter card", 2 * flatter <= len(split))) if c]
    return {"line_db": line, "line_pct": pct(line), "line_band": line_band,
            "boot": {"n": len(boot), "none_share": (len(boot) - len(have)) / len(boot), "interval_over": "resamples with a line",
                     "lo90": lo90, "hi90": hi90, "lo90_pct": pct(lo90), "hi90_pct": pct(hi90)},
            "unsure_neither_line_db": line_of(card(neither), None),
            "by_band": [{"band": b, "lo": lo, "hi": hi, "n": sum(1 for it in bandc if it["band"] == b),
                         "dropped": sum(1 for it in bandc if it["band"] == b and v(it) != "keep")} for b, (lo, hi) in enumerate(bands)],
            "percentile_of": f"the {len(pool)} doubler-free rows of W outside the heavy bands",
            "pairs": {"n": len(pairs), "split": len(split), "flatter_dropped": flatter,
                      "both_dropped": sum(1 for p in pairs.values() if sum(y for _, y in p) == 2)},
            "undecided": undecided}


def cmd_check_answers(args):
    from learn import ear_eat as EE
    from learn import pipeline_fix as P
    from learn import scope_page as SP

    P.require(H2A)
    d = heavy_dir() / CHECK_DIR
    key = json.loads((d / "key.json").read_text())
    ex = EE.stored_answers(pathlib.Path(args.stored).read_text())
    if ex.get("build") != key["build"]:
        raise SystemExit(f"{args.stored}: build {ex.get('build')}, this page's is {key['build']}")
    got = SP.unit_verdicts(ex["answers"], [{"id": it["id"], "unit": str(it["i"])} for it in key["items"]])
    flat = {int(k): v for k, v in json.loads((d / "flatness.json").read_text())["flatness_db"].items()}
    if any(flat[it["i"]] != it["flatness_db"] for it in key["items"]):
        raise SystemExit("flatness.json no longer matches the page's cards")
    pool = sorted(flat[int(x["i"])] for x in no_doubler(w_rows()))
    rep = {"phase": H2A, "build": key["build"], "verdicts": got, **check_read(key["items"], got, pool, [tuple(b) for b in key["bands"]]),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    (d / "verdicts.json").write_text(json.dumps(rep, indent=1))
    c = {}
    for v in got.values():
        c[v] = c.get(v, 0) + 1
    print(json.dumps({"heard": c, **{k: rep[k] for k in ("line_db", "line_pct", "line_band", "boot", "unsure_neither_line_db", "by_band", "pairs", "undecided")}}, indent=1))


def real_answers():
    """{unit: heavy 0/1} for every answered labelled GOAT and BKS recording and the goat-heavy page's: the page's
    verdicts over the earlier marks, "Not sure" as heavy."""
    from learn import pipeline_fix as P
    from learn import scope_page as SP

    d = SP.scope_dir()
    lst = json.loads((d / "list.json").read_text())
    ver = json.loads((d / "verdicts.json").read_text())["verdicts"]
    lab = {u: int(m == "out") for u, m in lst["marks"].items()}
    lab |= {u: int(v["verdict"] != "keep") for u, v in json.loads((P.out_dir() / P.GOAT_DIR / "heavy.json").read_text())["verdicts"].items()}
    lab |= {u: int(v != "keep") for u, v in ver.items()}
    return lab


def cmd_real_flat_line(_args):
    """For the record only: the real recordings' (in effect GOAT's) line on flatness, songs as clusters; no line
    carries across sources (Amendment 1), so nothing reads it. -> heavy/flat-line-real.json."""
    from multiprocessing import Pool

    from learn import pipeline_fix as P
    from learn import scope_page as SP

    P.require(H2A)
    lab = real_answers()
    parts = SP.labelled_parts()
    goat = {u["unit"]: u for u in P.goat_units()}
    jobs = [(u, parts.get(u) or {**goat[u], "source": "goat"}) for u in sorted(lab)]
    with Pool(3) as pool:
        flat = dict(zip([u for u, _ in jobs], pool.map(real_flatness, [p for _, p in jobs], chunksize=4)))
    pts = [(flat[u], lab[u], song_of(u)) for u in sorted(lab)]
    boot = boot_lines(pts, floor=None)
    have = sorted(b for b in boot if b is not None)
    line = line_of(pts, None)
    rep = {"phase": H2A, "line_db": line, "n": len(pts), "heavy": sum(lab.values()), "songs": len({c for _, _, c in pts}),
           "boot": {"n": len(boot), "none_share": (len(boot) - len(have)) / len(boot), "interval_over": "resamples with a line",
                    "lo90": have[int(0.05 * len(have))] if have else None, "hi90": have[min(len(have) - 1, int(0.95 * len(have)))] if have else None},
           "past": {"heavy": sum(1 for x, y, _ in pts if y and line is not None and x >= line),
                    "keep": sum(1 for x, y, _ in pts if not y and line is not None and x >= line)},
           "flatness_db": flat, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    (heavy_dir() / "flat-line-real.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("line_db", "n", "heavy", "songs", "boot", "past")}, indent=1))


def main(argv=None):
    from learn import cc_pool as CP

    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pilot-draw").set_defaults(fn=cmd_pilot_draw)
    s = sub.add_parser("pilot-render")
    s.add_argument("--shard", type=CP.parse_shard, default=(0, 1))
    s.set_defaults(fn=cmd_pilot_render)
    sub.add_parser("pilot-read").set_defaults(fn=cmd_pilot_read)
    sub.add_parser("line").set_defaults(fn=cmd_line)
    sub.add_parser("real-flat-line").set_defaults(fn=cmd_real_flat_line)
    sub.add_parser("check-measure").set_defaults(fn=cmd_check_measure)
    sub.add_parser("check-page").set_defaults(fn=cmd_check_page)
    a = sub.add_parser("check-answers")
    a.add_argument("stored")
    a.set_defaults(fn=cmd_check_answers)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
