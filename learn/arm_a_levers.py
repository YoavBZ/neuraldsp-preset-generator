"""Arm A's levers (`docs/arm-a-levers-plan.md`). Development only; estimates, not bars.

    .venv/bin/python -m learn.arm_a_levers replay                        # zero renders
    .venv/bin/python -m learn.arm_a_levers repeat-check                  # 12 renders
    .venv/bin/python -m learn.arm_a_levers judge-variants --shard 0/3    # experiment 1
    .venv/bin/python -m learn.arm_a_levers judge-early --shard 0/3       # 3-C' (replayed main stage)
    .venv/bin/python -m learn.arm_a_levers report-1
    $TORCH_PY        -m learn.arm_a_levers rebuild --folds 3             # 1z, 1a, 1b rebuild the stems
    .venv/bin/python -m learn.arm_a_levers screen --folds 3 --shard 0/3  # experiment 2
    .venv/bin/python -m learn.arm_a_levers report-2
    .venv/bin/python -m learn.arm_a_levers local --shard 0/3             # 2b, only on a tie
    .venv/bin/python -m learn.arm_a_levers report-2b
    .venv/bin/python -m learn.arm_a_levers judge-early --lever NAME      # descriptive, after report-1
    .venv/bin/python -m learn.arm_a_levers early-search --folds 3 --shard 0/3   # 3-W, if not C'
    .venv/bin/python -m learn.arm_a_levers report-3

The pure functions (variants, the main stage and replays, fidelity, ensembles, the tie rule) are
unit-tested; the commands that render are not, like the other step modules.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import statistics
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import knob_ceiling as K  # noqa: E402
from learn import song_readout as R  # noqa: E402

OUT = K.HOME / "learn/song-settings/levers"
SS_OUT = K.HOME / "learn/song-settings"
SEED = 20261013                  # arm A's and K_S's search seed
REPEAT_SEED = 20261024
LOCAL_SEED = 20261025
LOCAL_N = 40
BUDGET = 150
OBJ_LAG = -52                    # rebuilt_distance's default (−LATENCY): a rebuild aligned with its recording
REPEAT_TOL = K.REPEAT_TOL        # 0.005, log
SWAP_GROWTH_MB = 256.0           # the separator screen's guard

EXP1_ORDER = ("S", "C-blend", "B-blend", "menu_pick", "A", "S-mics", "shrink-0.5", "shrink-0.25", "shrink-0.75")
EXP1_RENDERED = ("shrink-0.25", "shrink-0.5", "shrink-0.75", "S-mics", "dirs-avg", "B-blend", "C-blend")
REPORTED_ONLY = ("dirs-avg",)
NETS = ("C'", "1z", "1a", "1b")
ENSEMBLES = {"E4": ("C'", "1z", "1a", "1b")}
EXP2_ORDER = ("C'", "1z", "1a", "1b", "E4")
EXP3_ORDER = ("S", "3-C'", "A", "3-W")
LEVERS = ("S-mics", "shrink-0.5", "shrink-0.25", "shrink-0.75")
CAPS = {"exp1": 1_100, "exp2": 1_800, "exp2b": 2_500, "early": 450, "3a": 6_400, "3b": 8_300}


# --- variants (experiment 1) --------------------------------------------------------------------


def _save(path, obj):
    """K._atomic, creating the folder first."""
    path.parent.mkdir(parents=True, exist_ok=True)
    K._atomic(path, obj)

def _k(d):
    return (d.module, d.key)


def unit(d, x):
    """A dim's unit value in preset x; a missing key counts as `lo`, as `coord_search` does."""
    v = x.get(_k(d))
    return d.to_unit(v if v is not None else d.lo)


def check_outside(dims, S, *xs):
    """Every source equals S outside the searched space (the plan builds only inside it)."""
    inside = {_k(d) for d in dims}
    for x in xs:
        diff = sorted(k for k in set(S) | set(x) if k not in inside and x.get(k) != S.get(k))
        if diff:
            raise ValueError(f"a source differs from S outside the searched space: {diff[:3]}")


def _copy(out, k, src):
    if k in src:
        out[k] = src[k]
    else:
        out.pop(k, None)


def build(dims, S, cont, cats_from, switches_from, sources=()):
    """S with the searched dims replaced: continuous dims from `cont` ({key: unit value}), kept as
    S's (or a source's) stored string where the value equals it; mics from `cats_from`, switches
    from `switches_from`, whole."""
    out = dict(S)
    for d in dims:
        k = _k(d)
        if d.kind in ("cont", "log"):
            u = cont[k]
            for src in (S, *sources):
                if math.isclose(unit(d, src), u, rel_tol=0.0, abs_tol=1e-12):
                    _copy(out, k, src)
                    break
            else:
                out[k] = K.fmt(d.from_unit(u))
        elif d.kind == "cat":
            _copy(out, k, cats_from)
        else:
            _copy(out, k, switches_from)
    return out


def _cont(dims):
    return [d for d in dims if d.kind in ("cont", "log")]


def shrink(dims, S, A, lam):
    check_outside(dims, S, A)
    return build(dims, S, {_k(d): unit(d, S) + lam * (unit(d, A) - unit(d, S)) for d in _cont(dims)}, A, A, (A,))


def s_mics(dims, S, A):
    check_outside(dims, S, A)
    return build(dims, S, {_k(d): unit(d, A) for d in _cont(dims)}, S, A, (A,))


def dirs_avg(dims, S, A, A2):
    check_outside(dims, S, A, A2)
    return build(dims, S, {_k(d): (unit(d, A) + unit(d, A2)) / 2 for d in _cont(dims)}, A, A, (A, A2))


def blend(dims, S, P, w=0.5):
    check_outside(dims, S, P)
    return build(dims, S, {_k(d): unit(d, S) + w * (unit(d, P) - unit(d, S)) for d in _cont(dims)}, S, S, (P,))


def variants(dims, S, A, A2, B, C):
    """Experiment 1's seven rendered variants (the plan's table)."""
    return {"shrink-0.25": shrink(dims, S, A, 0.25), "shrink-0.5": shrink(dims, S, A, 0.5),
            "shrink-0.75": shrink(dims, S, A, 0.75), "S-mics": s_mics(dims, S, A),
            "dirs-avg": dirs_avg(dims, S, A, A2), "B-blend": blend(dims, S, B), "C-blend": blend(dims, S, C)}


def lever(name, dims, S, A):
    """A one-search lever applied to some A (experiment 3's descriptive combination)."""
    if name == "S-mics":
        return s_mics(dims, S, A)
    if name.startswith("shrink-"):
        return shrink(dims, S, A, float(name.split("-")[1]))
    raise ValueError(name)


# --- the main stage and the zero-render replays ---------------------------------------------------

def main_stage(dims, x0, f, seed=SEED, budget=BUDGET, shares=K.SHARES):
    """`knob_search`'s main stage alone: `coord_search` (mics after the knobs, Hooke–Jeeves) under
    the limit round(budget × main share) = 52, every distinct setting evaluated once.
    -> (best x, best value, evaluations)."""
    cache = {}
    limit = max(1, round(budget * shares["main"]))

    def g(x):
        k = K.key(x)
        if k in cache:
            return cache[k]
        if len(cache) >= min(limit, budget):
            return None
        cache[k] = v = f(x)
        return v

    x, best, _ = K.coord_search(dims, x0, g, 10 ** 9, seed, cats="levels", gains={})
    return x, best, len(cache)


class Replay:
    """An objective that returns stored values in evaluation order and records each setting."""

    def __init__(self, values):
        self.values, self.i, self.xs = list(values), 0, []

    def __call__(self, x):
        if self.i >= len(self.values):
            raise RuntimeError("the replay ran past the stored values")
        v = self.values[self.i]
        self.i += 1
        self.xs.append(dict(x))
        return v


def replay_arm_a(amp, S, stored):
    """Arm A's stored search replayed with zero renders: the full `knob_search` and the main stage
    alone, both from the stored `objective_curve`. -> dict."""
    dims = K.space(amp, S)
    full = Replay(stored["objective_curve"])
    x, best, _, stages = K.knob_search(dims, S, full, BUDGET, SEED)
    main = Replay(stored["objective_curve"])
    mx, mbest, mn = main_stage(dims, S, main)
    return {"x": x, "best": best, "stages": stages, "used": full.i, "main_x": mx, "main_best": mbest,
            "main_renders": mn}


def replay_mismatches(rep, stored, stored_x):
    """What a replay fails to reproduce (empty: exact)."""
    bad = []
    if any(rep["x"].get(k) != stored_x.get(k) for k in set(rep["x"]) | set(stored_x)):
        bad.append("final settings")
    if rep["best"] != stored["objective_best"]:
        bad.append("objective_best")
    if rep["used"] != len(stored["objective_curve"]):
        bad.append("curve length")
    for s, v in stored["stages"].items():
        if rep["stages"].get(s) != v:
            bad.append(f"stage {s}")
    if rep["main_best"] != stored["stages"]["main"]["best"] or rep["main_renders"] != stored["stages"]["main"]["renders"]:
        bad.append("main stage")
    return bad


def replay_ks(amp, S, evals, search):
    """A stored K_S run replayed: [(setting, {"A": d, "B": d})] in evaluation order, and the final x."""
    i = "AB".index(search)
    rep = Replay([e[i] for e in evals])
    x, _, _, _ = K.knob_search(K.space(amp, S), S, rep, BUDGET, K.SEED)
    return [(xs, {"A": e[0], "B": e[1]}) for xs, e in zip(rep.xs, evals)], x


def local_draw(trajectories, n=LOCAL_N, seed=LOCAL_SEED):
    """Experiment 2b's settings: per (part, amp), both directions' K_S trajectories pooled and
    deduplicated, `n` drawn by one generator over the sorted cells. trajectories: {(slug, amp):
    [(setting, d), ...]} -> {(slug, amp): [(setting, d), ...]}."""
    rng = random.Random(seed)
    out = {}
    for cell in sorted(trajectories):
        uniq = {}
        for x, d in trajectories[cell]:
            uniq.setdefault(K.key(x), (x, d))
        keys = sorted(uniq)
        out[cell] = [uniq[k] for k in rng.sample(keys, min(n, len(keys)))]
    return out


# --- objectives and fidelity (experiment 2) ------------------------------------------------------

def finite_pos(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


def ensemble_objective(members):
    """members: [{name: distance}] -> {name: mean log distance}; any member non-finite makes the
    preset inf."""
    names = set(members[0]).intersection(*members[1:])
    return {n: (statistics.fmean(math.log(m[n]) for m in members) if all(finite_pos(m[n]) for m in members)
                else math.inf) for n in sorted(names)}


def rank_fidelity(obj, true):
    """Spearman over the presets where both are finite (pairwise); None with fewer than 3."""
    from scipy.stats import spearmanr

    names = [n for n in sorted(set(obj) & set(true))
             if isinstance(obj[n], (int, float)) and math.isfinite(obj[n]) and finite_pos(true[n])]
    if len(names) < 3:
        return None
    r = spearmanr([obj[n] for n in names], [true[n] for n in names]).correlation
    return None if r is None or not math.isfinite(r) else float(r)


def objective_lag(delta):
    """The rebuilt objective's lag for a rebuild lagging C′'s by `delta` samples (GCC): the
    recording then sits `delta` earlier against it."""
    return OBJ_LAG - delta


def pick(obj):
    """The menu pick: the lowest finite objective (name order breaks ties)."""
    ok = [n for n in sorted(obj) if math.isfinite(obj[n])]
    return min(ok, key=lambda n: (obj[n], n)) if ok else None


# --- statistics and the decision ------------------------------------------------------------------

def part_means(rows):
    """rows: (slug, band, value) -> [(slug, band, mean over the part)]."""
    by = {}
    for s, b, v in rows:
        by.setdefault((s, b), []).append(v)
    return [(s, b, statistics.fmean(v)) for (s, b), v in sorted(by.items())]


def part_interval(rows):
    """Mean of the part means with a t interval on the parts (parts − 1 df)."""
    from scipy import stats

    pm = [v for _, _, v in part_means(rows)]
    m = statistics.fmean(pm)
    if len(pm) < 2:
        return m, None, None
    half = stats.t.ppf(0.95, len(pm) - 1) * statistics.stdev(pm) / math.sqrt(len(pm))
    return m, m - half, m + half


def interval(rows, wider=False):
    """The band-weighted mean and its 90% band-clustered interval; with `wider` (the fold-3 steps)
    the interval is the wider of that and the part interval."""
    s = R.bw_stats([(b, v) for _, b, v in part_means(rows)])
    lo, hi = s["lo90"], s["hi90"]
    if wider:
        _, plo, phi = part_interval(rows)
        if plo is not None and (lo is None or (phi - plo) > (hi - lo)):   # the wider one, not the union
            lo, hi = plo, phi
    return s["band_weighted_mean"], lo, hi


def choose(values, order, lower=True, wider=False):
    """values: {candidate: {unit key: (slug, band, value)}}. The best band-weighted mean (lowest
    if `lower`); a candidate whose paired difference with the best has a 90% interval containing
    0 is a tie; of the best and its ties, the first in `order` is chosen. Only candidates in
    `order` that have values compete. -> dict."""
    cands = [c for c in order if values.get(c)]
    means = {c: interval(list(values[c].values()), wider)[0] for c in cands}
    best = min(cands, key=lambda c: (means[c] if lower else -means[c], order.index(c)))
    diffs, tied = {}, []
    for c in cands:
        if c == best:
            continue
        common = sorted(set(values[c]) & set(values[best]))
        rows = [(values[c][k][0], values[c][k][1], values[c][k][2] - values[best][k][2]) for k in common]
        m, lo, hi = interval(rows, wider)
        diffs[c] = {"mean": m, "lo90": lo, "hi90": hi, "units": len(rows)}
        if lo is None or hi is None or lo <= 0 <= hi:
            tied.append(c)
    chosen = min([best, *tied], key=order.index)
    return {"means": means, "best": best, "tied_with_best": tied, "chosen": chosen, "diff_vs_best": diffs}


def drop(units, methods):
    """The readout's refused-half rule over these candidates too (`song_readout.drop_refused`)."""
    return R.drop_refused(units, methods=tuple(R.DECISION_METHODS) + tuple(methods))


def log_rows(units, cand, ref="S"):
    """{(slug, amp, search): (slug, band, log(d_cand / d_ref))} where both are finite."""
    out = {}
    for u in units:
        x, y = u["d"].get(cand), u["d"].get(ref)
        if finite_pos(x) and finite_pos(y):
            out[(u["slug"], u["amp"], u["search"])] = (u["slug"], u["band"], math.log(x / y))
    return out


def effects(units, cand, ref):
    """The plan's reported figures for cand against ref (only the pooled mean decides)."""
    from learn import confirm_run as CR

    f = R.log_vs(cand, ref)
    rows = R.part_rows(units, f)
    out = {"all": R.bw(rows), "per_amp": {a: R.bw(R.part_rows([u for u in units if u["amp"] == a], f))
                                          for a in sorted({u["amp"] for u in units})},
           "per_class": {c: R.bw(rows, (c,)) for c in ("clean", "crunch")}}
    if len({b for b, _, _ in rows}) > 1:
        out["part_weighted"] = CR.stats([(b, v) for b, _, v in rows])
    return out


# --- data access (no renders) ----------------------------------------------------------------------

def _settings(path):
    d = json.loads(pathlib.Path(path).read_text())
    d = d.get("settings", d) if isinstance(d.get("settings"), dict) else d   # replay files nest them
    return {tuple(k.rsplit("/", 1)): v for k, v in d.items()}


def menu_S():
    """amp -> class -> (select, S) from arm B's stored copy of the menu's starting presets."""
    ms = json.loads((SS_OUT / "armB" / "menu-S.json").read_text())
    return {a: {c: (v["select"], {tuple(k.rsplit("/", 1)): s for k, s in v["settings"].items()})
                for c, v in m.items()} for a, m in ms.items()}


def stored_a(slug, amp, search):
    d = SS_OUT / "armA" / slug / amp
    return json.loads((d / f"{search}.json").read_text()), _settings(d / f"{search}-settings.json")


def predictions(slug, amp, search):
    c = json.loads((SS_OUT / "armB" / "predictions.json").read_text())["cells"][f"{slug}|{amp}|{search}"]
    return {k: {tuple(n.rsplit("/", 1)): v for n, v in c[k]["settings"].items()} for k in ("B", "constant")}


def gathered_units():
    """The readout's units (before the drop), as `song_readout.report` gathers them."""
    from learn import song_settings as SS

    data, missing = R.gather(SS_OUT, K.OUT, K.HOME / "learn/label-table", SS.cells(), K.parts(),
                             SS.control_cells(), True)
    if missing:
        raise SystemExit(f"{len(missing)} stored file(s) missing, e.g. {missing[:3]}")
    return data["units"]


def fold_of(slug):
    from learn import song_settings as SS

    return SS.folds()[K.parts()[slug]["band"]]


STEP_DIRS = {"exp2b": ["local"], "3a": ["early/W"], "3b": ["early/W"], "early": ["early/C'", "early/lever-*"]}


def spent(step):
    """Renders already recorded under a step's outputs (review 2026-10-16: some steps write
    under other folders than their name)."""
    roots = []
    for d in STEP_DIRS.get(step, [step]):
        roots += list(OUT.glob(d)) if "*" in d else [OUT / d]
    return sum(json.loads(p.read_text()).get("renders", 0) for r in roots for p in r.rglob("*.json")
               if not p.name.startswith("report"))


def check_cap(step, planned):
    if spent(step) + planned > CAPS[step]:
        raise SystemExit(f"{step}: {spent(step)} spent + {planned} planned exceeds the hard cap {CAPS[step]}")


def swap_used_mb():
    try:
        s = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout
        return float(s.split("used =")[1].split()[0].rstrip("M"))
    except Exception:
        return None


class SwapGuard:
    def __init__(self):
        self.swap0 = swap_used_mb()

    def check(self):
        s = swap_used_mb()
        if self.swap0 is not None and s is not None and s - self.swap0 > SWAP_GROWTH_MB:
            raise SystemExit(f"swap grew by {s - self.swap0:.0f} MB: stopping")


def _shard(xs, shard):
    return xs[shard[0]::shard[1]]


def _shard_cells(cells, shard):
    """Cells sharded by (part, amp), so both directions share one process and one warm-up
    (review 2026-10-16: sharding by direction doubled the warm-ups and raced on shared files)."""
    groups = sorted({(c[0], c[1]) for c in cells})
    mine = set(_shard(groups, shard))
    return [c for c in cells if (c[0], c[1]) in mine]


# --- commands ----------------------------------------------------------------------------------------

def cmd_replay():
    """Zero renders: replay every stored arm A search (writes the main-stage settings) and the
    fold-3 K_S trajectories (for 2b); stops on any mismatch."""
    from learn import song_settings as SS

    ms, ps = menu_S(), K.parts()
    bad = []
    for slug, amp, search, _ in SS.cells():
        stored, x = stored_a(slug, amp, search)
        S = ms[amp][ps[slug]["gain_class"]][1]
        rep = replay_arm_a(amp, S, stored)
        m = replay_mismatches(rep, stored, x)
        if m:
            bad.append((slug, amp, search, m))
            continue
        _save(OUT / "replay" / "armA" / slug / amp / f"{search}-main.json",
                  {"settings": {f"{a}/{b}": v for (a, b), v in rep["main_x"].items()}, "main_best": rep["main_best"],
                   "main_renders": rep["main_renders"], "renders": 0})
    for slug in sorted(s for s in ps if s != "telefunken-Honey-GTR" and fold_of(s) == 3):
        for amp in K.AMPS:
            r = json.loads((K.OUT / "cells" / slug / amp / "result.json").read_text())
            S = ms[amp][ps[slug]["gain_class"]][1]
            traj = []
            for search, run in r["runs"].items():
                if "K_S" not in run:
                    continue
                t, x = replay_ks(amp, S, run["K_S"]["evals"], search)
                st = _settings(K.OUT / "cells" / slug / amp / f"K_S-{search}.json")
                if any(x.get(k) != st.get(k) for k in set(x) | set(st)):
                    bad.append((slug, amp, f"K_S-{search}", ["final settings"]))
                traj += [({f"{a}/{b}": v for (a, b), v in s.items()}, d) for s, d in t]
            if not any(b[0] == slug and b[1] == amp for b in bad):   # never save a failed replay
                _save(OUT / "replay" / "ks" / slug / f"{amp}.json", {"trajectory": traj, "renders": 0})
    print("replay mismatches:", bad or "none")
    if bad:
        raise SystemExit(1)


def _part_audio(part):
    import numpy as np

    from learn import confirm_run as CR

    di = K.measure_di(part)
    return di, di.astype(np.float32), CR.mono(part["crop"] / "reference.wav")


def cmd_repeat_check():
    """6 directions by random.Random(20261024): A and S re-rendered, within 0.005 of the stored d."""
    from learn import song_settings as SS

    out = OUT / "exp1" / "repeat.json"
    if out.exists():
        print(json.loads(out.read_text()))
        return
    check_cap("exp1", 12 + 6)
    ps = K.parts()
    cells = random.Random(REPEAT_SEED).sample(sorted(SS.cells()), 6)
    rr, res = K.Renderer(), {"cells": [list(c) for c in cells], "dev": {}}
    try:
        menu = rr.menu()
        for slug, amp, search, held in cells:
            part = ps[slug]
            di, di32, ref = _part_audio(part)
            sel, S = menu[amp][K.START[part["gain_class"]][amp]]
            rr.render(di32, sel, S)
            stored, x = stored_a(slug, amp, search)
            kc = json.loads((K.OUT / "cells" / slug / amp / "result.json").read_text())
            for name, xx, ref_d in (("A", x, stored["judge"]), ("S", S, kc["menu"][kc["start"]])):
                j = K.judge(ref, rr.render(di32, sel, xx), di, part["judge_lag"])
                res["dev"][f"{slug}|{amp}|{search}|{name}"] = max(abs(math.log(j[h] / ref_d[h])) for h in "AB"
                                                                 if finite_pos(j[h]) and finite_pos(ref_d[h]))
        res["renders"] = rr.count
    finally:
        rr.close()
    _save(out, res)
    worst = max(res["dev"].values())
    print("repeat check, worst |log|:", round(worst, 6))
    if worst > REPEAT_TOL:
        raise SystemExit("repeat renders moved beyond 0.005: stop and investigate")


def cmd_judge_variants(shard):
    """Experiment 1: each direction's variants rendered once through the measure DI."""
    from learn import song_settings as SS

    if not (OUT / "exp1" / "repeat.json").exists():
        raise SystemExit("run repeat-check first")
    ps = K.parts()
    todo = [c for c in _shard_cells(sorted(SS.cells()), shard)
            if not (OUT / "exp1" / c[0] / c[1] / f"{c[2]}.json").exists()]
    check_cap("exp1", len(todo) * 7)
    rr, guard = K.Renderer(), SwapGuard()
    try:
        menu = rr.menu()
        warm = set()
        for slug, amp, search, held in todo:
            guard.check()
            part = ps[slug]
            di, di32, ref = _part_audio(part)
            sel, S = menu[amp][K.START[part["gain_class"]][amp]]
            n_warm = rr.count
            if (slug, amp) not in warm:
                rr.render(di32, sel, S)
                warm.add((slug, amp))
            n_warm = rr.count - n_warm                                   # recorded with the direction
            _, A = stored_a(slug, amp, search)
            _, A2 = stored_a(slug, amp, held)
            P = predictions(slug, amp, search)
            vs = variants(K.space(amp, S), S, A, A2, P["B"], P["constant"])
            n0, res = rr.count - n_warm, {}
            cfile = OUT / "exp1" / slug / amp / "C-blend.json"           # the same in both directions
            for name, x in vs.items():
                if name == "C-blend" and cfile.exists() and json.loads(cfile.read_text())["key"] == K.key(x):
                    res[name] = json.loads(cfile.read_text())["judge"]
                    continue
                res[name] = K.judge(ref, rr.render(di32, sel, x), di, part["judge_lag"])
                if name == "C-blend":
                    _save(cfile, {"key": K.key(x), "judge": res[name], "renders": 0})
            _save(OUT / "exp1" / slug / amp / f"{search}.json",
                      {"judge": res, "held": held, "renders": rr.count - n0,
                       "settings": {n: {f"{a}/{b}": v for (a, b), v in x.items()} for n, x in vs.items()}})
            print(slug, amp, search, {n: round(v[held], 3) for n, v in res.items()}, rr.count, flush=True)
    finally:
        rr.close()


def cmd_judge_early(shard, lever_name=None):
    """3-C′: the replayed main-stage settings judged once per direction (or, with `lever_name`,
    experiment 1's lever applied to them; descriptive)."""
    from learn import song_settings as SS

    ps = K.parts()
    tag = "C'" if lever_name is None else f"lever-{lever_name}"
    todo = [c for c in _shard_cells(sorted(SS.cells()), shard)
            if not (OUT / "early" / tag / c[0] / c[1] / f"{c[2]}.json").exists()]
    check_cap("early", len(todo) + 72)
    rr, guard = K.Renderer(), SwapGuard()
    try:
        menu = rr.menu()
        warm = set()
        for slug, amp, search, held in todo:
            guard.check()
            part = ps[slug]
            di, di32, ref = _part_audio(part)
            sel, S = menu[amp][K.START[part["gain_class"]][amp]]
            x = _settings(OUT / "replay" / "armA" / slug / amp / f"{search}-main.json")
            if lever_name is not None:
                x = lever(lever_name, K.space(amp, S), S, x)
            n0 = rr.count
            if (slug, amp) not in warm:
                rr.render(di32, sel, S)
                warm.add((slug, amp))
            j = K.judge(ref, rr.render(di32, sel, x), di, part["judge_lag"])
            _save(OUT / "early" / tag / slug / amp / f"{search}.json",
                      {"judge": j, "held": held, "renders": rr.count - n0,
                       "settings": {f"{a}/{b}": v for (a, b), v in x.items()}})
            print(tag, slug, amp, search, round(j[held], 4), flush=True)
    finally:
        rr.close()


def _held_from(step_dir, u, name=None):
    p = step_dir / u["slug"] / u["amp"] / f"{u['search']}.json"
    if not p.exists():
        return None
    r = json.loads(p.read_text())
    j = r["judge"][name] if name else r["judge"]
    return j[u["held"]]


def cmd_report_1():
    """Experiment 1's figures and choice (dirs-avg reported beside its in-sample comparator)."""
    units = gathered_units()
    for u in units:
        for v in EXP1_RENDERED:
            u["d"][v] = _held_from(OUT / "exp1", u, v)
        a2, _ = stored_a(u["slug"], u["amp"], u["held"])
        u["d"]["A_other_insample"] = a2["judge"][u["held"]]
    units, dropped = drop(units, tuple(v for v in EXP1_RENDERED if v not in REPORTED_ONLY))
    rep = {"directions": len(units), "dropped": [list(d) for d in dropped],
           "vs_S": {c: effects(units, c, "S") for c in (*EXP1_ORDER[1:], *REPORTED_ONLY, "A_other_insample")},
           "vs_A": {c: effects(units, c, "A") for c in (*EXP1_ORDER, *REPORTED_ONLY) if c != "A"},
           "choice": choose({c: log_rows(units, c) for c in EXP1_ORDER}, EXP1_ORDER)}
    _save(OUT / "exp1" / "report.json", rep)
    ch = rep["choice"]
    for c in EXP1_ORDER[1:]:
        s = rep["vs_S"][c]["all"]
        print(f"{c:12s} vs S {s['band_weighted_mean']:+.3f} [{s['lo90']:+.3f}, {s['hi90']:+.3f}]")
    s = rep["vs_S"]["dirs-avg"]["all"]
    t = rep["vs_S"]["A_other_insample"]["all"]
    print(f"dirs-avg (in-sample, not eligible) {s['band_weighted_mean']:+.3f}; A' in-sample comparator {t['band_weighted_mean']:+.3f}")
    print("best", ch["best"], "ties", ch["tied_with_best"], "chosen", ch["chosen"])


def _net_path(net, fold):
    from learn import di_fine_structure as DF
    from learn import song_settings as SS

    return SS.cprime(fold) if net == "C'" else DF.net_path(net, fold)


def _rebuilt(net, slug):
    import numpy as np

    return np.load(SS_OUT / "rebuilt" / f"{slug}.npy") if net == "C'" else np.load(OUT / "rebuilt" / net / f"{slug}.npy")


def cmd_rebuild(folds, nets):
    """The nets rebuild the folds' stems (CPU), as `song_settings.rebuild_all` does with C′, with
    experiment 4's leak assertion per net × part and the GCC lag against C′'s rebuild (TORCH)."""
    import numpy as np
    import torch

    from learn import di_fine_structure as DF
    from learn import direc as D
    from learn import rank_margin as RM
    from learn import song_settings as SS
    from learn.direc_check import eq_to, to_lufs

    ps = K.parts()
    avg = {f: np.load(SS.MODELS / "cache" / f"average-fold{f}.npy") for f in range(4)}
    log_path = OUT / "rebuilt" / "rebuild-log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}
    for net in ("C'", *nets):
        for f in folds:
            path = _net_path(net, f)
            if not SS.net_ready(path):
                raise SystemExit(f"{path} is not final (no DONE marker)")
            cfg = json.loads((path.parent / "config.json").read_text()) if (path.parent / "config.json").exists() else {}
            caches = [pathlib.Path(c) for c in cfg.get("caches", [DF.MODELS / c for c in DF.CACHES])]
            pool = DF.train_pool_bands(f, caches)
            model = None
            for slug in sorted(s for s in ps if s != "telefunken-Honey-GTR" and fold_of(s) == f):
                DF.assert_no_leak(ps[slug]["band"], cfg.get("fold", f), f, pool)
                if net == "C'":
                    continue                                            # stored rebuild; leak asserted only
                out = OUT / "rebuilt" / net / f"{slug}.npy"
                if out.exists():
                    continue
                model = model or D.load_model(path).eval()
                x = D.rebuild(model, SS.stem(slug).astype(np.float32), device=torch.device("cpu")).astype(np.float64)
                y = to_lufs(eq_to(x, avg[2] - avg[f]))
                out.parent.mkdir(parents=True, exist_ok=True)
                np.save(out, y)
                lag = int(RM.gcc_lag(y, _rebuilt("C'", slug)))
                log[f"{net}|{slug}"] = {"fold": f, "network": str(path), "gcc_lag_vs_cprime": lag}
                _save(log_path, log)
                print(net, slug, "fold", f, "lag vs C'", lag, flush=True)


def _delta(net, slug):
    if net == "C'":
        return 0
    return json.loads((OUT / "rebuilt" / "rebuild-log.json").read_text())[f"{net}|{slug}"]["gcc_lag_vs_cprime"]


def _score(stem_x, y, rebuilt, lag, counter):
    from learn.rebuilt_judge import rebuilt_distance

    out = {}
    for h, (a, b) in K.R.HALVES.items():
        d, proxy = rebuilt_distance(stem_x, y, rebuilt, start_s=a, end_s=b, lag=lag)
        counter["fallback"] += int(proxy)
        out[h] = math.inf if d.distance is None else d.distance
    return out


def cmd_screen(folds, nets, shard):
    """Experiment 2: every menu preset through each net's rebuild, scored on both halves at lag
    −52 and at the net's own alignment; plus 3 C′ repeat renders per part."""
    import numpy as np

    from learn import song_settings as SS

    ps = K.parts()
    slugs = _shard(sorted(s for s in ps if s != "telefunken-Honey-GTR" and fold_of(s) in folds), shard)
    rr, guard = K.Renderer(), SwapGuard()
    try:
        menu = rr.menu()
        for slug in slugs:
            stem_x = SS.stem(slug)
            todo = [n for n in nets if not (OUT / "exp2" / n / f"{slug}.json").exists()]
            check_cap("exp2" if list(folds) == [3] else "3b", len(todo) * 114 + 6)
            rp = OUT / "exp2" / "repeat" / f"{slug}.json"
            if not rp.exists():                                         # C′ repeat: 3 presets
                stored = json.loads((SS_OUT / "menupick" / slug / "result.json").read_text())
                rng = random.Random(f"{REPEAT_SEED}|{slug}")             # random.Random('20261024|<part>')
                cr = _rebuilt("C'", slug)
                n0, dev = rr.count, {}
                for amp in K.AMPS:
                    rr.render(cr.astype(np.float32), *next(iter(menu[amp].values())))
                for amp, name in rng.sample([(a, n) for a in K.AMPS for n in sorted(menu[a])], 3):
                    s = _score(stem_x, rr.render(cr.astype(np.float32), *menu[amp][name]), cr, OBJ_LAG, {"fallback": 0})
                    dev[f"{amp}|{name}"] = max(abs(math.log(s[h] / stored[amp]["scores"][name][h])) for h in "AB"
                                               if finite_pos(s[h]) and finite_pos(stored[amp]["scores"][name][h]))
                _save(rp, {"dev": dev, "renders": rr.count - n0})
                if max(dev.values()) > REPEAT_TOL:
                    raise SystemExit(f"C' repeat moved beyond 0.005 on {slug}: stop and investigate")
            for net in todo:
                guard.check()
                rb = _rebuilt(net, slug)
                r32 = rb.astype(np.float32)
                delta = _delta(net, slug)
                n0, res = rr.count, {}
                for amp, m in menu.items():
                    rr.render(r32, *next(iter(m.values())))
                    counter = {"fallback": 0}
                    scores = {}
                    for name, (sel, ed) in m.items():
                        y = rr.render(r32, sel, ed)
                        scores[name] = {"-52": _score(stem_x, y, rb, OBJ_LAG, counter)}
                        if delta:
                            scores[name]["own"] = _score(stem_x, y, rb, objective_lag(delta), counter)
                    res[amp] = {"scores": scores, "fallback": counter["fallback"]}
                _save(OUT / "exp2" / net / f"{slug}.json", {"delta": delta, "menu": res, "renders": rr.count - n0})
                print(net, slug, rr.count, flush=True)
    finally:
        rr.close()


def menu_objective(net, slug, amp, half):
    """{preset: rebuilt objective on `half`} at the net's deciding lag (C′: the stored menu pick)."""
    if net == "C'":
        return {n: v[half] for n, v in json.loads((SS_OUT / "menupick" / slug / "result.json").read_text())[amp]["scores"].items()}
    r = json.loads((OUT / "exp2" / net / f"{slug}.json").read_text())
    return {n: (v["own"] if "own" in v else v["-52"])[half] for n, v in r["menu"][amp]["scores"].items()}


def candidate_objective(cand, slug, amp, half):
    """Single nets as stored (distance); an ensemble as the mean log over its members."""
    if cand in ENSEMBLES:
        return ensemble_objective([menu_objective(n, slug, amp, half) for n in ENSEMBLES[cand]])
    return menu_objective(cand, slug, amp, half)


def screen_rows(units, cand):
    """Per direction: fidelity, the pick's held log ratio against S, and pick regret."""
    out = {"fidelity": {}, "pick_vs_S": {}, "regret": {}}
    for u in units:
        k = (u["slug"], u["amp"], u["search"])
        kc = json.loads((K.OUT / "cells" / u["slug"] / u["amp"] / "result.json").read_text())["menu"]
        obj = candidate_objective(cand, u["slug"], u["amp"], u["search"])
        f = rank_fidelity(obj, {n: v[u["search"]] for n, v in kc.items()})
        if f is not None:
            out["fidelity"][k] = (u["slug"], u["band"], f)
        p = pick(obj)
        held = {n: v[u["held"]] for n, v in kc.items() if finite_pos(v[u["held"]])}
        if p in held and finite_pos(u["d"].get("S")):
            out["pick_vs_S"][k] = (u["slug"], u["band"], math.log(held[p] / u["d"]["S"]))
            out["regret"][k] = (u["slug"], u["band"], math.log(held[p] / min(held.values())))
    return out


def cmd_report_2(folds=(3,)):
    units, _ = drop(gathered_units(), ())
    units = [u for u in units if fold_of(u["slug"]) in folds]
    rows = {c: screen_rows(units, c) for c in EXP2_ORDER if all((OUT / "exp2" / n).exists() or n == "C'"
                                                                 for n in ENSEMBLES.get(c, (c,)))}
    ch = choose({c: r["fidelity"] for c, r in rows.items()}, EXP2_ORDER, lower=False, wider=True)
    rep = {"choice": ch, "tie": bool(ch["tied_with_best"]),
           "fidelity_vs_C'": {c: dict(zip(("mean", "lo90", "hi90"), interval(
               [(r["fidelity"][k][0], r["fidelity"][k][1], r["fidelity"][k][2] - rows["C'"]["fidelity"][k][2])
                for k in r["fidelity"] if k in rows["C'"]["fidelity"]], wider=True))) for c, r in rows.items() if c != "C'"},
           "pick_vs_S": {c: dict(zip(("mean", "lo90", "hi90"), interval(list(r["pick_vs_S"].values()), True))) for c, r in rows.items()},
           "regret": {c: dict(zip(("mean", "lo90", "hi90"), interval(list(r["regret"].values()), True))) for c, r in rows.items()},
           "leave_one_band_out": {c: R.bw_stats([(b, v) for _, b, v in part_means(list(r["fidelity"].values()))])["leave_one_band_out"]
                                  for c, r in rows.items()}}
    for c in rep["fidelity_vs_C'"]:
        rep["fidelity_vs_C'"][c]["expected_A_gain_descriptive"] = -0.26 * rep["fidelity_vs_C'"][c]["mean"]
    _save(OUT / "exp2" / "report.json", rep)
    for c in rows:
        print(f"{c:3s} fidelity {ch['means'][c]:+.3f}  pick vs S {rep['pick_vs_S'][c]['mean']:+.3f}")
    print("best", ch["best"], "ties", ch["tied_with_best"], "chosen", ch["chosen"],
          "-> 2b runs" if rep["tie"] else "-> no 2b")


def cmd_local(shard):
    """2b (only on experiment 2's tie): 40 replayed K_S settings per fold-3 (part, amp) through
    each tied candidate's member nets, scored on both halves at each net's deciding lag."""
    import numpy as np

    from learn import song_settings as SS

    rep = json.loads((OUT / "exp2" / "report.json").read_text())
    if not rep["tie"]:
        raise SystemExit("experiment 2 left no tie: 2b does not run")
    tied = [rep["choice"]["best"], *rep["choice"]["tied_with_best"]]
    nets = sorted({n for c in tied for n in ENSEMBLES.get(c, (c,))}, key=NETS.index)
    ps = K.parts()
    traj = {(p.parent.name, p.stem): [(_settings_dict(x), d) for x, d in json.loads(p.read_text())["trajectory"]]
            for p in sorted((OUT / "replay" / "ks").glob("*/*.json"))}
    draws = local_draw(traj)
    cells = _shard(sorted(draws), shard)
    check_cap("exp2b", len(cells) * len(nets) * (LOCAL_N + 1))
    rr, guard = K.Renderer(), SwapGuard()
    try:
        menu = rr.menu()
        for slug, amp in cells:
            stem_x = SS.stem(slug)
            sel = menu[amp][K.START[ps[slug]["gain_class"]][amp]][0]
            for net in nets:
                out = OUT / "local" / net / f"{slug}-{amp}.json"
                if out.exists():
                    continue
                guard.check()
                rb = _rebuilt(net, slug)
                r32 = rb.astype(np.float32)
                lag = objective_lag(_delta(net, slug))
                n0, counter, res = rr.count, {"fallback": 0}, []
                rr.render(r32, sel, draws[(slug, amp)][0][0])
                for x, d in draws[(slug, amp)]:
                    res.append({"obj": _score(stem_x, rr.render(r32, sel, x), rb, lag, counter), "true": d})
                _save(out, {"points": res, "fallback": counter["fallback"], "renders": rr.count - n0})
                print(net, slug, amp, rr.count, flush=True)
    finally:
        rr.close()


def _settings_dict(x):
    return {tuple(k.rsplit("/", 1)): v for k, v in x.items()}


def cmd_report_2b():
    rep2 = json.loads((OUT / "exp2" / "report.json").read_text())
    tied = [rep2["choice"]["best"], *rep2["choice"]["tied_with_best"]]
    order = tuple(c for c in EXP2_ORDER if c in tied)
    ps = K.parts()
    vals = {}
    for c in order:
        rows = {}
        for p in sorted((OUT / "local" / ENSEMBLES.get(c, (c,))[0]).glob("*.json")):
            slug, amp = p.stem.rsplit("-", 1)
            pts = {n: json.loads((OUT / "local" / n / p.name).read_text())["points"] for n in ENSEMBLES.get(c, (c,))}
            fs = []
            for h in "AB":
                objs = [{i: q["obj"][h] for i, q in enumerate(pts[n])} for n in pts]
                obj = ensemble_objective(objs) if len(objs) > 1 else objs[0]
                f = rank_fidelity(obj, {i: q["true"][h] for i, q in enumerate(next(iter(pts.values())))})
                if f is not None:
                    fs.append(f)
            if fs:
                rows[(slug, amp)] = (slug, ps[slug]["band"], statistics.fmean(fs))
        vals[c] = rows
    ch = choose(vals, order, lower=False, wider=True)
    _save(OUT / "exp2b" / "report.json", {"choice": ch})
    print("local fidelity:", {c: round(v, 3) for c, v in ch["means"].items()}, "chosen", ch["chosen"])


def chosen_objective():
    p2b = OUT / "exp2b" / "report.json"
    return json.loads((p2b if p2b.exists() else OUT / "exp2" / "report.json").read_text())["choice"]["chosen"]


def cmd_early_search(folds, shard):
    """3-W: a live main-stage search (52 renders × members) with the chosen objective, from S,
    seed 20261013; the best judged once through the measure DI."""
    import numpy as np

    from learn import song_settings as SS

    cand = chosen_objective()
    if cand == "C'":
        print("experiment 2 chose C': 3-W does not run (3-C' is the replay)")
        return
    members = ENSEMBLES.get(cand, (cand,))
    ps = K.parts()
    step = "3a" if list(folds) == [3] else "3b"
    todo = [c for c in _shard(sorted(c for c in SS.cells() if fold_of(c[0]) in folds), shard)
            if not (OUT / "early" / "W" / c[0] / c[1] / f"{c[2]}.json").exists()]
    check_cap(step, len(todo) * (53 * len(members) + 1))
    rr, guard = K.Renderer(), SwapGuard()
    try:
        menu = rr.menu()
        for slug, amp, search, held in todo:
            guard.check()
            part = ps[slug]
            di, di32, ref = _part_audio(part)
            stem_x = SS.stem(slug)
            sel, S = menu[amp][K.START[part["gain_class"]][amp]]
            rbs = {n: _rebuilt(n, slug) for n in members}
            lags = {n: objective_lag(_delta(n, slug)) for n in members}
            n0, counter = rr.count, {"fallback": 0}
            for n in members:
                rr.render(rbs[n].astype(np.float32), sel, S)                  # warm-up

            def f(x):
                ds = [_score(stem_x, rr.render(rbs[n].astype(np.float32), sel, x), rbs[n], lags[n], counter)[search]
                      for n in members]
                return math.exp(statistics.fmean(math.log(d) for d in ds)) if all(finite_pos(d) for d in ds) else math.inf

            x, best, n_eval = main_stage(K.space(amp, S), S, f)
            j = K.judge(ref, rr.render(di32, sel, x), di, part["judge_lag"])
            _save(OUT / "early" / "W" / slug / amp / f"{search}.json",
                      {"objective": cand, "objective_best": best, "evaluations": n_eval, "judge": j, "held": held,
                       "fallback": counter["fallback"], "renders": rr.count - n0,
                       "settings": {f"{a}/{b}": v for (a, b), v in x.items()}})
            print(cand, slug, amp, search, round(j[held], 4), rr.count, flush=True)
    finally:
        rr.close()


def cmd_report_3():
    units = gathered_units()
    for u in units:
        u["d"]["3-C'"] = _held_from(OUT / "early" / "C'", u)
        u["d"]["3-W"] = _held_from(OUT / "early" / "W", u)
        for lv in LEVERS:
            u["d"][f"lever-{lv}"] = _held_from(OUT / "early" / f"lever-{lv}", u)
    base, _ = drop([u for u in units], ("3-C'",))
    rep = {"3-C'": {"vs_S": effects(base, "3-C'", "S"), "vs_A": effects(base, "3-C'", "A"),
                    "choice": choose({c: log_rows(base, c) for c in ("S", "3-C'", "A")}, ("S", "3-C'", "A"))},
           "levers_on_3-C'_descriptive": {lv: effects([u for u in base if u["d"].get(f"lever-{lv}")], f"lever-{lv}", "3-C'")
                                          for lv in LEVERS if any(u["d"].get(f"lever-{lv}") for u in base)}}
    w = [u for u in base if u["d"].get("3-W") is not None]
    if w:
        f3 = [u for u in w if fold_of(u["slug"]) == 3]
        f3, _ = drop(f3, ("3-C'", "3-W"))
        rep["3a"] = {"vs_S": effects(f3, "3-W", "S"), "vs_3-C'": effects(f3, "3-W", "3-C'"),
                     "choice": choose({c: log_rows(f3, c) for c in EXP3_ORDER}, EXP3_ORDER, wider=True)}
        rep["3b_runs"] = rep["3a"]["choice"]["chosen"] == "3-W"
        if len({u["slug"] for u in w}) > len({u["slug"] for u in f3}):
            allw, _ = drop(w, ("3-C'", "3-W"))
            rep["3b"] = {"vs_S": effects(allw, "3-W", "S"), "vs_3-C'": effects(allw, "3-W", "3-C'"),
                         "choice": choose({c: log_rows(allw, c) for c in EXP3_ORDER}, EXP3_ORDER)}
    _save(OUT / "early" / "report.json", rep)
    c = rep["3-C'"]
    s = c["vs_S"]["all"]
    print(f"3-C' vs S {s['band_weighted_mean']:+.3f} [{s['lo90']:+.3f}, {s['hi90']:+.3f}]; chosen {c['choice']['chosen']}")
    if "3a" in rep:
        print("3a chosen", rep["3a"]["choice"]["chosen"], "-> 3b runs" if rep["3b_runs"] else "-> no 3b")


def _folds(s):
    return [int(x) for x in s.split(",")]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("replay", "repeat-check", "judge-variants", "judge-early", "report-1", "rebuild",
                                    "screen", "report-2", "local", "report-2b", "early-search", "report-3"))
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--folds", default="3")
    ap.add_argument("--nets", default="1z,1a,1b", help="rebuild/screen: the nets besides C'")
    ap.add_argument("--lever", default=None, choices=LEVERS)
    a = ap.parse_args(argv)
    sh = tuple(int(x) for x in a.shard.split("/"))
    nets = [n for n in a.nets.split(",") if n]
    fo = _folds(a.folds)
    {"replay": cmd_replay, "repeat-check": cmd_repeat_check,
     "judge-variants": lambda: cmd_judge_variants(sh), "judge-early": lambda: cmd_judge_early(sh, a.lever),
     "report-1": cmd_report_1, "rebuild": lambda: cmd_rebuild(fo, nets), "screen": lambda: cmd_screen(fo, nets, sh),
     "report-2": lambda: cmd_report_2(tuple(fo)), "local": lambda: cmd_local(sh), "report-2b": cmd_report_2b,
     "early-search": lambda: cmd_early_search(fo, sh), "report-3": cmd_report_3}[a.cmd]()


if __name__ == "__main__":
    main()
