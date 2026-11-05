"""L1a's centre read, by the score (`docs/pipeline-fix-plan.md`, "The centre read, by the score"): do the first batch's
trusted capture labels move the centre? Reads BKS and the panel, so a counted panel read; picks no recipe.

    MAIN=.venv/bin/python
    PYTHONPATH=. $MAIN -m learn.capture_centres answers    # RcT and RcG_n on BKS's 40 units and the panel's 44 (zero renders)
    PYTHONPATH=. $MAIN -m learn.capture_centres distance   # RcT's setting distance from RcG (zero renders)
    # then pipeline_fix real-render and panel-render --names RcT,RcGn0,RcGn1,RcGn2 (504 renders a centre)
    PYTHONPATH=. $MAIN -m learn.capture_centres report     # captures/centre-read.json

RcT: Rc's rule on the trusted capture labels. RcG_n: Rc's rule on GOAT labels drawn to RcT's count per amp and class,
3 seeded draws. Each is one setting per amp and class, on all 3 amps. Rows RcT - RcG_n (the mean of the draws, and each),
RcT - S and RcG - S (stored); BKS by DI, the panel by capped band weights. No row reads as moved unless its interval
clears zero and RcT - RcG_n has the same sign on all 3 draws.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import time

SEED = 20261105
DRAWS = 3
DISTANCE_DRAWS = 200
RCT = "RcT"
GOAT_TAGS = tuple(f"RcGn{n}" for n in range(DRAWS))
TAGS = (RCT, *GOAT_TAGS)
OUT = "centre-read.json"


# --- pure ----------------------------------------------------------------------------------------------------------

def by_cell(recs, cls_of):
    """{(amp, class): [record]}, sorted by unit, of the labelled records."""
    out = {}
    for r in sorted((r for r in recs if r["label"] is not None), key=lambda r: r["unit"]):
        out.setdefault((r["amp"], cls_of(r)), []).append(r)
    return out


def draw_cells(cells, counts, draw, seed=SEED):
    """`cells` cut to `counts` records per cell, seeded per draw and cell; a cell short of its count keeps all it has."""
    out = {}
    for c, rs in cells.items():
        rng = random.Random(f"{seed}|{draw}|{c[0]}|{c[1]}")
        out[c] = rng.sample(rs, min(counts.get(c, 0), len(rs)))
    return out


def creator_draw(cells, creator_of, draw, seed=SEED):
    """`cells` resampled by creator, with replacement over all creators: a creator's records count once each time drawn."""
    names = sorted({creator_of(r) for rs in cells.values() for r in rs})
    rng = random.Random(f"{seed}|creators|{draw}")
    picks = [rng.choice(names) for _ in names]
    return {c: [r for n in picks for r in rs if creator_of(r) == n] for c, rs in cells.items()}


def direction_value(judge, a, b, u, value):
    """ln(d_a / d_b) on one BKS direction by `real-report`'s rule, None where it drops: `value(judge, tag, u)` gives
    None (not rendered), "refused" or the distance; S missing or refused drops it, a refused answer scores as S."""
    s_ = value(judge, "S", u)
    if s_ is None or s_ == "refused":
        return None
    vals = []
    for t in (a, b):
        v = value(judge, t, u)
        if v is None:
            return None
        vals.append(s_ if v == "refused" else v)
    return math.log(vals[0] / vals[1])


def moved(row, each):
    """The plan's rule: a row reads as moved only if its interval clears zero and the draws' means share its sign."""
    if row.get("lo90") is None or (row["lo90"] <= 0 <= row["hi90"]):
        return False
    return all((m > 0) == (row["mean"] > 0) and m != 0 for m in each)


def panel_counted(entry, need=2):
    """True once the ledger counts this panel read (`phase_5d_panel_reads` opens with the count)."""
    return int(str(entry.get("phase_5d_panel_reads", "0")).split()[0]) >= need


def quantiles(v, qs=(0.05, 0.5, 0.95)):
    """Nearest-rank quantiles of `v`."""
    s = sorted(v)
    return [s[min(len(s) - 1, int(q * len(s)))] for q in qs]


def cell_rms(dims, a, b, unit):
    """The rms gap between two settings over the continuous searched dims, in unit space."""
    gaps = [unit(d, a) - unit(d, b) for d in dims if d.kind in ("cont", "log")]
    return math.sqrt(statistics.fmean(x * x for x in gaps))


# --- the stored data ------------------------------------------------------------------------------------------------

def capture_cells():
    """(cells, unit records) of the trusted capture labels, through the one loader."""
    from learn import capture_labels as CL

    recs = CL.search_records()
    units = {u["unit"]: u for u in CL.units_of()}
    return by_cell(list(recs.values()), lambda r: units[r["unit"]]["cls"]), units


def goat_cells():
    from learn import pipeline_fix as P

    grecs, gunits, _ = P.goat_labels()
    return by_cell(grecs, lambda r: gunits[r["unit"]]["cls"])


def centre(cell, rs, ms):
    """Rc's rule on one cell's records. -> (select, settings dict)."""
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    amp, cls = cell
    sel, S = ms[amp][cls]
    return sel, P.rc_setting(K.space(amp, S), S, [LO.tdict(r["label"]) for r in rs])


def tag_cells():
    """{tag: {cell: [record]}} and RcT's counts."""
    cap, _ = capture_cells()
    goat = goat_cells()
    counts = {c: len(rs) for c, rs in cap.items()}
    short = {c: (n, len(goat.get(c, []))) for c, n in counts.items() if n > len(goat.get(c, []))}
    if short:
        raise SystemExit(f"GOAT has too few labels for {short}")
    out = {RCT: cap}
    for n, t in enumerate(GOAT_TAGS):
        out[t] = draw_cells(goat, counts, n)
    return out, counts


def require_read():
    from learn import capture_labels as CL
    from learn import pipeline_fix as P

    e = P.require("phase_l1a")
    CL.rest_may_run()
    return e


def cmd_answers(_args):
    """RcT and RcG_n as answers on BKS's units and the panel's, every answer on each of the three amps; written once.
    Refuses until the label page, the stage check and the scope page allow the rest and the ledger counts the panel read."""
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    e = require_read()
    if not panel_counted(e):
        raise SystemExit("phase_5d_panel_reads must count this read before its answers are written")
    bks = json.loads((P.out_dir() / P.REAL_DIR / "answers" / "S.json").read_text())["parts"]
    panel, _ = P.panel_lagged_units()
    cells, counts = tag_cells()
    ms = P.A_menu_S()
    for t, by in cells.items():
        made = {c: centre(c, rs, ms) for c, rs in by.items()}
        for sub, units in ((P.REAL_DIR, bks), (P.PANEL_DIR, panel)):
            p = P.out_dir() / sub / "answers" / f"{t}.json"
            if p.exists():
                raise SystemExit(f"{p} exists: the answers are written once")
            answers = {}
            for prt in units:
                for amp in P.AMPS3:
                    sel, st = made[(amp, prt["cls"])]
                    answers[P.real_key(prt, amp)] = {P.ANY_HALF: {"select": sel, "settings": LO.sdict(st)}}
            P.save(p, {"plan": P.PLAN, "ledger": f"{P.LEDGER_ID} phase_l1a", "tag": t,
                       "labels_used": {f"{a}|{c}": len(rs) for (a, c), rs in by.items()}, "answers": answers,
                       "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"CENTRES DONE: {sorted(TAGS)}, labels per cell {sorted((f'{a}|{c}', n) for (a, c), n in counts.items())}")


def cmd_distance(_args):
    """The zero-render row: per cell, RcT's rms gap from RcG (every GOAT label), against RcG_n's own gap over
    DISTANCE_DRAWS draws, and a creator bootstrap of RcT. -> captures/centre-distance.json."""
    from learn import arm_a_levers as L
    from learn import capture_labels as CL
    from learn import knob_ceiling as K
    from learn import pipeline_fix as P

    require_read()
    cap, units = capture_cells()
    goat = goat_cells()
    counts = {c: len(rs) for c, rs in cap.items()}
    ms = P.A_menu_S()
    rows = {}

    def creator(r):
        return units[r["unit"]]["creator"]

    boots = [creator_draw(cap, creator, n) for n in range(DISTANCE_DRAWS)]
    for c, rs in sorted(cap.items()):
        dims = K.space(c[0], ms[c[0]][c[1]][1])
        rcg = centre(c, goat[c], ms)[1]
        gap = lambda st: cell_rms(dims, st, rcg, L.unit)  # noqa: E731
        null = [gap(centre(c, draw_cells({c: goat[c]}, counts, n + DRAWS)[c], ms)[1]) for n in range(DISTANCE_DRAWS)]
        boot = [gap(centre(c, b[c], ms)[1]) for b in boots if b[c]]
        rows[f"{c[0]}|{c[1]}"] = {"labels": len(rs), "RcT": gap(centre(c, rs, ms)[1]), "RcGn_q05_50_95": quantiles(null),
                                  "creator_boot_q05_50_95": quantiles(boot), "boot_draws": len(boot)}
        print(c, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in rows[f"{c[0]}|{c[1]}"].items()}, flush=True)
    P.save(CL.root() / "centre-distance.json", {"plan": P.PLAN, "ledger": f"{P.LEDGER_ID} phase_l1a", "rows": rows,
                                                "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print("DISTANCE DONE")


def judges(sub, tags):
    from learn import pipeline_fix as P

    out = {}
    for t in tags:
        out[t] = {}
        for f in (P.out_dir() / sub / "judge" / t).glob("*.json"):
            r = json.loads(f.read_text())
            out[t][f"{r['unit']}|{r['amp']}"] = r["judge"]
    return out


def bks_reader(tags):
    """(rows of a, b -> [(DI, unit, value)]) on BKS's directions, `real-report`'s rule."""
    from learn import pipeline_fix as P

    parts = json.loads((P.out_dir() / P.REAL_DIR / "answers" / "S.json").read_text())["parts"]
    judge = judges(P.REAL_DIR, set(tags) | {"S"})
    lags = P.out_dir() / P.REAL_DIR / "lags"

    def ok(p_):
        f = lags / f"{p_['unit'].replace('/', '__')}.json"
        return not f.exists() or json.loads(f.read_text())["lag"] is not None

    dirs = [(p_, (p_["unit"], amp, sh, h)) for p_ in parts if ok(p_) for amp in P.AMPS3
            for sh, h in (("A", "B"), ("B", "A"))]

    def rows(a, b):
        return {u: (p_["di"], u[0], v) for p_, u in dirs
                if (v := direction_value(judge, a, b, u, P.vreal_value)) is not None}
    return rows


def panel_reader(tags):
    """(rows of a, b -> [(DI, unit, value)]) on the panel's directions, and the capped DI weights."""
    from learn import pipeline_fix as P

    units, _ = P.panel_lagged_units()
    halves = P.panel_halves(units)
    judge = judges(P.PANEL_DIR, set(tags))

    def rows(a, b):
        got, _ = P.panel_rows(a, b, units, halves, judge)
        return {(p_["unit"], amp): (p_["di"], p_["unit"], v) for p_, amp, v in got}
    return rows, P.panel_weights(units)


def mean_rows(per_draw):
    """Per direction, the mean over the draws, on the directions every draw holds."""
    keys = set.intersection(*(set(d) for d in per_draw))
    return {k: (per_draw[0][k][0], per_draw[0][k][1], statistics.fmean(d[k][2] for d in per_draw)) for k in keys}


def cmd_report(_args):
    """The rows on BKS (by DI) and the panel (capped band weights). -> captures/centre-read.json."""
    from learn import capture_labels as CL
    from learn import pipeline_fix as P

    require_read()
    tags = (*TAGS, "RcG", "S")
    bks = bks_reader(tags)
    pan, weights = panel_reader(tags)

    def stat_bks(rows):
        c = P.clustered(list(rows.values()))
        return {q: c.get(q) for q in ("mean", "lo90", "hi90", "clusters", "clusters_negative", "parts", "parts_negative")}

    def stat_panel(rows):
        di = [(d, v) for d, _, v in rows.values()]
        return P.weighted_clustered(di, {d: weights[d] for d, _ in di})

    rep = {"plan": P.PLAN, "ledger": f"{P.LEDGER_ID} phase_l1a", "sets": {}}
    for name, read, stat in (("bks", bks, stat_bks), ("panel", pan, stat_panel)):
        draws = [read(RCT, t) for t in GOAT_TAGS]
        each = [stat(d) for d in draws]
        row = stat(mean_rows(draws))
        rep["sets"][name] = {"RcT - RcG_n": {**row, "moved": moved(row, [e["mean"] for e in each])},
                             "each_draw": dict(zip(GOAT_TAGS, each)),
                             "RcT - S": stat(read(RCT, "S")), "RcG - S": stat(read("RcG", "S"))}
        for k, v in rep["sets"][name].items():
            if k != "each_draw":
                print(name, k, {q: (round(x, 4) if isinstance(x, float) else x) for q, x in v.items()}, flush=True)
    rep["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(CL.root() / OUT, rep)
    print("CENTRE READ DONE")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("answers", "distance", "report"))
    a = ap.parse_args(argv)
    {"answers": cmd_answers, "distance": cmd_distance, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
