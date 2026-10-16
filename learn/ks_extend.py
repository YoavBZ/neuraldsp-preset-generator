"""The knob-search ceiling, searched to a stop (`docs/ks-ceiling-extend-plan.md`, amendment 1).
Development only, the true DI (the measure DI), no model.

K_S plus iterated 150-evaluation rounds: a K_S direction is continued from its stored final
settings by rounds of `knob_ceiling.knob_search` (the same space and search-half objective) until
its search-half curve is flat (or the 600 guard). Directions run in 6 seeded batches of 24, one
per part; after batch 2 and each later batch, batches stop once h, the 90% half-width of the
error from the directions not yet run (search half), is at most 0.01.

    .venv/bin/python -m learn.ks_extend check                        # zero renders
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.ks_extend run --shard 0/3 --after PID ...
    .venv/bin/python -m learn.ks_extend report                       # zero renders

The pure parts (the stopping rule, the continuation, its resume, the replay prior, the batch
design and rule, the process checks, the curves and the report) are unit-tested with fake
objectives; `run` renders and is not, like the other step modules.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import re
import statistics
import subprocess
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import arm_a_levers as A  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import song_readout as R  # noqa: E402

OUT = K.HOME / "learn/ks-ceiling-extend"
KC2 = K.HOME / "learn/knob-ceiling-2"

SEED = K.SEED + 1                  # round r (1, 2, ...) searches with SEED + r - 1
ROUND = K.BUDGET["K_S"]            # evaluations per round: the stored search's own budget
CHUNK = 50                         # renders between checks
WINDOW = 150                       # the rule's window: one round's worth of renders
MIN_GAIN = 0.005                   # log, search half
GUARD = 600                        # extra renders per direction, at most
MAX_ROUNDS = 40                    # a safety net; GUARD or "exhausted" ends a direction first
REPEAT_TOL = K.REPEAT_TOL          # the first render repeats the stored final, within 0.005 log
CHECKPOINTS = tuple(range(0, GUARD + 1, CHUNK))   # extra renders; 0 is the stored 150
STEP3_DROPPED = {("telefunken-Gym_Hours-GTR_1", "pr12", "A"),        # the step-3 readout's drops
                 ("telefunken-Sculptor's_Request-GTR_1", "pr12", "B")}
KC2_TAIL = {"stage1": 50, "stage2": 12}   # the knob-ceiling-2 tail windows (a quarter; half of 24)
TERMINAL = ("done", "repeat_failed")      # a direction's finished states

# Amendment 1 (2026-10-16, before any render): seeded batches and the search-half precision rule.
BATCH_SEED = 20261016
N_BATCHES = 6                    # 3 amps × 2 halves: one direction per part per batch
MIN_BATCHES = 2                  # h needs within-part degrees of freedom
H_MAX = 0.01                     # stop adding batches when h ≤ this (search half)
Z90 = 1.645
CAP = 3                          # render processes machine-wide, this one included
AFTER = r"-m learn\.song_relabel\b"
RENDERS = (r"-m learn\.song_relabel (render-new|probe)\b", r"-m learn\.ks_extend run\b")


# --- the stopping rule ------------------------------------------------------------------------------

def stop_reason(best_at, chunk=CHUNK, window=WINDOW, min_gain=MIN_GAIN, guard=GUARD):
    """best_at[i]: the best search-half value after i·chunk extra renders (best_at[0] is the
    stored search's). Called at a chunk end. -> "flat", "guard" or None.

    Flat: at least `window` extra renders, and the best improved by less than `min_gain` (log)
    over the last `window`. Guard: `guard` extra renders. Flat is reported first when both hold."""
    n = (len(best_at) - 1) * chunk
    w = window // chunk
    if n >= window and math.log(best_at[-1 - w] / best_at[-1]) < min_gain:
        return "flat"
    if n >= guard:
        return "guard"
    return None


def would_stop(curve, chunk=CHUNK, window=WINDOW, min_gain=MIN_GAIN):
    """The rule applied to a stored incumbent curve (search half, curve[i] after i + 1 renders):
    the first chunk end n ≥ window where it reads flat, or None. The start (render 1) stands in
    for render 0."""
    c = [curve[0], *curve]
    for n in range(window, len(curve) + 1, chunk):
        if math.log(c[n - window] / c[n]) < min_gain:
            return n
    return None


# --- the continuation ---------------------------------------------------------------------------------

class _Stop(Exception):
    pass


class RepeatFailed(RuntimeError):
    """The first render (the stored final, again) moved by more than the tolerance."""

    def __init__(self, dev):
        super().__init__(f"the repeat render moved by {dev:.4f} (log)")
        self.dev = dev


class Resume:
    """A render function that first returns a saved log's values, checking each setting's key, so a
    restarted direction replays its own earlier renders with zero renders and continues live."""

    def __init__(self, render, saved=()):
        self.render, self.saved, self.i, self.live = render, list(saved), 0, 0

    def __call__(self, x):
        i, self.i = self.i, self.i + 1
        if i < len(self.saved):
            k, a, b = self.saved[i]
            if k != K.key(x):
                raise RuntimeError(f"resume diverged at render {i + 1}")
            return {"A": a, "B": b}
        self.live += 1
        return self.render(x)


def _dev(d, ref):
    """The largest |log ratio| over the halves; a half finite in one and not the other is inf."""
    out = 0.0
    for h in "AB":
        a, b = d[h], ref[h]
        if A.finite_pos(a) and A.finite_pos(b):
            out = max(out, abs(math.log(a / b)))
        elif A.finite_pos(a) != A.finite_pos(b):
            return math.inf
    return out


def extend(dims, x0, render, search, held, start, lookup=None, gains=None, seed=SEED, round_budget=ROUND,
           chunk=CHUNK, window=WINDOW, min_gain=MIN_GAIN, guard=GUARD, max_rounds=MAX_ROUNDS,
           repeat_tol=REPEAT_TOL, on_chunk=None):
    """Continue a search from `x0` (its stored final) by rounds of `knob_search`.

    render(x) -> {"A": d, "B": d}, one render (a non-finite value is a refusal). `start`: the stored
    final's {"A", "B"}, the incumbent at extra render 0. `lookup`: {key: {"A", "B"}}, the stored
    search's evaluations; a setting found there (or rendered earlier in this continuation) is
    returned without a render. It still uses one of its round's evaluations, as it would in
    `knob_search`'s own cache. `x0` itself is always rendered first: the repeat check. `gains`: the
    per-dim improvement of the stored search's main stage, carried through the rounds.

    The incumbent is the best on the search half (strict, as `knob_ceiling.summary`). After every
    `chunk` renders the rule (`stop_reason`) is checked on the search half only. -> dict."""
    table = dict(lookup or {})
    k0 = K.key(x0)
    table.pop(k0, None)
    gains = {} if gains is None else gains
    inc = {"x": dict(x0), "d": dict(start), "key": k0}
    log, chunks, rounds = [], [[0, start[search], start[held], k0]], []
    st = {"stop": None, "repeat_dev": None}

    def snapshot():
        n = len(log)
        return {"log": log, "chunks": chunks, "renders": n, "rounds": len(rounds), "round_stages": rounds,
                "stop": st["stop"], "repeat_dev": st["repeat_dev"],
                "final": {"renders": n, "search": inc["d"][search], "held": inc["d"][held], "key": inc["key"]},
                "x": inc["x"]}

    def f(x):
        k = K.key(x)
        if k in table:
            return table[k][search]
        d = render(x)
        table[k] = d
        log.append([k, d["A"], d["B"]])
        n = len(log)
        if n == 1:
            assert k == k0, "the first render must be the stored final"
            st["repeat_dev"] = _dev(d, start)
            if st["repeat_dev"] > repeat_tol:
                raise RepeatFailed(st["repeat_dev"])
        elif A.finite_pos(d[search]) and d[search] < inc["d"][search] - 1e-12:
            inc.update(x=dict(x), d=d, key=k)
        if n % chunk == 0:
            chunks.append([n, inc["d"][search], inc["d"][held], inc["key"]])
            st["stop"] = stop_reason([c[1] for c in chunks], chunk, window, min_gain, guard)
            if on_chunk is not None:
                on_chunk(snapshot())
            if st["stop"]:
                raise _Stop
        return d[search]

    try:
        while True:
            if len(rounds) >= max_rounds:
                st["stop"] = "max_rounds"
                break
            before = len(log)
            _, _, _, stages = K.knob_search(dims, inc["x"], f, round_budget, seed + len(rounds), gains=gains)
            rounds.append({"seed": seed + len(rounds), "stages": stages, "renders": len(log) - before})
            if len(log) == before:
                st["stop"] = "exhausted"
                break
    except _Stop:
        rounds.append({"seed": seed + len(rounds), "stages": None, "renders": None, "stopped_in_round": True})
    return snapshot()


def replay(amp, S, evals, search):
    """The stored K_S search replayed with zero renders (as `arm_a_levers.replay_ks`), also
    returning its main stage's per-dim gains. -> (lookup {key: {"A", "B"}}, final x, gains)."""
    i = "AB".index(search)
    rep = A.Replay([e[i] for e in evals])
    gains = {}
    x, _, _, _ = K.knob_search(K.space(amp, S), S, rep, A.BUDGET, K.SEED, gains=gains)
    lookup = {}
    for xs, e in zip(rep.xs, evals):
        lookup.setdefault(K.key(xs), {"A": e[0], "B": e[1]})
    return lookup, x, gains


# --- curves and the report (pure) ----------------------------------------------------------------

def incumbent_curve(evals, search, held):
    """[(search, held)] of the incumbent after each evaluation (strict improvement on the search
    half), as `knob_ceiling.summary`. evals: [(A, B)]."""
    i, j = "AB".index(search), "AB".index(held)
    inc, out = evals[0], []
    for e in evals:
        if A.finite_pos(e[i]) and e[i] < inc[i] - 1e-12:
            inc = e
        out.append((inc[i], inc[j]))
    return out


def tail(curve, window):
    """(Δ search, Δ held): log ratio of the incumbent at the end against `window` renders before
    (the start, if shorter). Negative: still improving. Non-finite held gives None for it."""
    a, b = curve[max(0, len(curve) - 1 - window)], curve[-1]
    ds = math.log(b[0] / a[0])
    dh = math.log(b[1] / a[1]) if A.finite_pos(a[1]) and A.finite_pos(b[1]) else None
    return ds, dh


def at_extra(res, n):
    """A direction's incumbent (search, held) after n extra renders; after its stop, the final."""
    for c in res["chunks"]:
        if c[0] == n:
            return c[1], c[2]
    if n >= res["final"]["renders"]:
        return res["final"]["search"], res["final"]["held"]
    raise KeyError(n)


def _log(a, b):
    return math.log(a / b) if A.finite_pos(a) and A.finite_pos(b) else None


# --- amendment 1: the seeded batches and the precision rule ---------------------------------------

def design(parts, seed=BATCH_SEED, n=N_BATCHES):
    """parts: {slug: gain_class} (the scored parts). -> n batches of (slug, amp, search, held), one
    direction per part, in seeded order. Within each class (clean, then crunch) the sorted parts are
    shuffled with random.Random(seed) and given offsets o = 0, 1, ..., n − 1, 0, ... in that order;
    batch b runs, per part, combination c = (o + b) mod n: amp AMPS[c % 3], search half "AB"[c % 2].
    The n batches cover every direction once; a part's consecutive batches change amp and half."""
    assert n == len(K.AMPS) * len(K.DIRECTIONS)
    order = []
    for cls in K.IN_SCOPE:
        ps = sorted(s for s, c in parts.items() if c == cls)
        random.Random(seed).shuffle(ps)
        order += [(s, i % n) for i, s in enumerate(ps)]
    out = []
    for b in range(n):
        batch = []
        for s, o in order:
            c = (o + b) % n
            search = "AB"[c % 2]
            batch.append((s, K.AMPS[c % 3], search, "B" if search == "A" else "A"))
        out.append(batch)
    return out


def search_gain(res):
    """The search-half extension gain of a finished direction, log(final / stored final)."""
    return math.log(res["final"]["search"] / res["chunks"][0][1])


def precision_h(g, k, bands, n=N_BATCHES, z=Z90):
    """The 90% half-width of the error from the directions not yet run (amendment 1).

    g: {slug: [search-half extension gains of its run directions]}; k: complete batches; bands:
    {slug: band} over every part in the design. s² is the within-part variance, pooled (n_p − 1
    degrees of freedom per part); h = z · sqrt(s²/k · (1 − k/n) · Σ_band 1/n_band / B²).
    -> h, or None with no within-part degrees of freedom."""
    ss, df = 0.0, 0
    for v in g.values():
        if len(v) > 1:
            m = statistics.fmean(v)
            ss += sum((x - m) ** 2 for x in v)
            df += len(v) - 1
    if df == 0:
        return None
    nb = {}
    for b in bands.values():
        nb[b] = nb.get(b, 0) + 1
    return z * math.sqrt(ss / df / k * (1 - k / n) * sum(1 / x for x in nb.values()) / len(nb) ** 2)


def walk(batches, results, bands, h_max=H_MAX, min_batches=MIN_BATCHES):
    """The batch rule, from the stored direction files (search half only; deterministic, so every
    process reaches the same answer). results: {(slug, amp, search): result}.
    -> {"history": [{"batches": k, "h", "decision"}], "next": the batch to run or finish (None:
    stopped), "stopped_after": k or None}."""
    hist = []
    for k in range(1, len(batches) + 1):
        if not all(results.get(d[:3], {}).get("status") in TERMINAL for d in batches[k - 1]):
            return {"history": hist, "next": k - 1, "stopped_after": None}
        g = {}
        for batch in batches[:k]:
            for s, a, se, _ in batch:
                r = results[(s, a, se)]
                if r["status"] == "done":
                    g.setdefault(s, []).append(search_gain(r))
        h = precision_h(g, k, bands) if k >= min_batches else None
        stop = h is not None and h <= h_max
        hist.append({"batches": k, "h": h, "decision": "stop" if stop else "continue"})
        if stop:
            return {"history": hist, "next": None, "stopped_after": k}
    return {"history": hist, "next": None, "stopped_after": len(batches)}


# --- the report (pure) ---------------------------------------------------------------------------------

def _held_points(res, checkpoints):
    return [at_extra(res, n)[1] for n in checkpoints] + [res["final"]["held"]]


def refused(results, checkpoints=CHECKPOINTS):
    """Amendment 1: run directions whose incumbent held half is refused (non-finite) at any reported
    point; they leave every point, as step 3's rule does."""
    return {key for key, r in results.items()
            if not all(A.finite_pos(v) for v in _held_points(r, checkpoints))}


def estimate_rows(base, results, n=None):
    """Per part: the mean over its directions of log(K_S@150 held / S held), plus the mean over its
    run directions of log(held after n extra renders / K_S@150 held) (n None: at the stop). base:
    {(slug, amp, search): {"slug", "band", "cls", "S_held", "ks_held"}}; results: the run
    directions, {(slug, amp, search): result}. A part with no run direction is left out.
    -> ([(band, cls, value)], parts left out)."""
    by, gain = {}, {}
    for key, b in base.items():
        by.setdefault(b["slug"], (b["band"], b["cls"], []))[2].append(math.log(b["ks_held"] / b["S_held"]))
    for key, r in results.items():
        held = r["final"]["held"] if n is None else at_extra(r, n)[1]
        gain.setdefault(key[0], []).append(math.log(held / r["chunks"][0][2]))
    rows, out = [], []
    for slug in sorted(by):
        band, cls, v = by[slug]
        if slug not in gain:
            out.append(slug)
            continue
        rows.append((band, cls, statistics.fmean(v) + statistics.fmean(gain[slug])))
    return rows, out


def _bw3(rows):
    return {"all": R.bw(rows), "clean": R.bw(rows, ("clean",)), "crunch": R.bw(rows, ("crunch",))}


def _by_reason(units, f):
    out = {}
    for reason in ("all", "flat", "guard", "other"):
        sel = [u for u in units if reason == "all" or u["r"]["stop"] == reason
               or (reason == "other" and u["r"]["stop"] not in ("flat", "guard"))]
        s = R.bw(R.part_rows(sel, f))
        s["directions"] = len(sel)
        out[reason] = s
    return out


def summarise(base, results, walked=None, checkpoints=CHECKPOINTS, guard=GUARD):
    """base: every direction's stored figures (see `estimate_rows`); results: every direction file
    written, {(slug, amp, search): result}. -> the report (plan, "What is reported")."""
    done = {k: r for k, r in results.items() if r.get("status") == "done"}
    failed = sorted(k for k, r in results.items() if r.get("status") == "repeat_failed")
    drop = refused(done, checkpoints)
    run = {k: r for k, r in done.items() if k not in drop}
    keep = {k: b for k, b in base.items() if k not in drop}
    step3 = {k: b for k, b in keep.items() if k not in STEP3_DROPPED}
    run3 = {k: r for k, r in run.items() if k not in STEP3_DROPPED}
    out = {"directions_run": len(run), "dropped_refused_held": sorted(drop), "repeat_failed": failed,
           "estimate": {}, "estimate_step3_142": {}}
    for n in checkpoints:
        rows, left = estimate_rows(keep, run, n)
        out["estimate"][str(150 + n)] = {**_bw3(rows), "still_running": sum(r["final"]["renders"] > n
                                                                            for r in run.values()),
                                         "parts_left_out": left}
        out["estimate_step3_142"][str(150 + n)] = R.bw(estimate_rows(step3, run3, n)[0])
    rows, left = estimate_rows(keep, run, None)
    out["estimate_at_stop"] = {**_bw3(rows), "parts_left_out": left}
    out["estimate_at_stop_step3_142"] = R.bw(estimate_rows(step3, run3, None)[0])
    units = []
    for k, r in run.items():
        units.append({"slug": k[0], "band": base[k]["band"], "cls": base[k]["cls"], "r": r,
                      "S_held": base[k]["S_held"]})
    out["extension_gain_held"] = _by_reason(units, lambda u: math.log(u["r"]["final"]["held"] / u["r"]["chunks"][0][2]))
    out["extension_gain_search"] = _by_reason(units, lambda u: search_gain(u["r"]))
    out["run_directions_at_stop_vs_S"] = _by_reason(units, lambda u: math.log(u["r"]["final"]["held"] / u["S_held"]))
    ren = sorted(r["renders"] for r in done.values())
    n_flat = sum(r["stop"] == "flat" for r in done.values())
    n_guard = sum(r["stop"] == "guard" for r in done.values())
    out["headline"] = {"directions_finished": len(done), "converged_by_the_declared_rule": n_flat,
                       "hit_guard": n_guard, "guard_share": n_guard / len(done) if done else None}
    out["renders"] = {
        "total": sum(ren), "min": ren[0] if ren else None, "median": statistics.median(ren) if ren else None,
        "max": ren[-1] if ren else None,
        "quartiles": statistics.quantiles(ren, n=4) if len(ren) > 1 else None,
        "stops": {s: sum(r["stop"] == s for r in done.values()) for s in sorted({r["stop"] for r in done.values()})},
        "guard": guard,
        "warm_ups": sum(bool(r.get("warm_up")) for r in results.values())}
    out["repeat_max"] = max((r["repeat_dev"] for r in done.values()), default=None)
    if walked is not None:
        out["batches"] = walked
    return out


def ks_tail_rows(cells, window=50):
    """Zero renders: the stored K_S curves' tails. cells: knob-ceiling result.json dicts. ->
    units with the tail changes (search, held), and the rule's retrospective stop (None: still
    improving at 150)."""
    out = []
    for c in cells:
        for search, held in K.DIRECTIONS:
            run = c["runs"][search]
            if "skipped" in run:
                continue
            curve = [(s, h) for _, s, h in run["K_S"]["curve"]]
            ds, dh = tail(curve, window)
            out.append({"slug": c["slug"], "band": c["band"], "cls": c["gain_class"], "amp": c["amp"],
                        "search": search, "d_search": ds, "d_held": dh,
                        "rule_stop": would_stop([s for s, _ in curve])})
    return out


def kc2_stage1_rows(results, window=KC2_TAIL["stage1"]):
    """Zero renders: knob ceiling 2's stage 1 (200 renders a cell) — tails and the rule."""
    out = []
    for r in results:
        curve = incumbent_curve(r["evals"], r["search_half"], r["held_half"])
        ds, dh = tail(curve, window)
        out.append({"slug": r["slug"], "band": r["band"], "cls": r["gain_class"], "amp": r["amp"],
                    "search": r["search_half"], "d_search": ds, "d_held": dh,
                    "rule_stop": would_stop([s for s, _ in curve])})
    return out


def stage2_choice(r, budget=None, margin=None):
    """Stage 2's choice for a cell, recomputed with each effect cut at `budget` renders (None: as
    run). -> (effect or "dry", search, held), as `knob_ceiling2.stage2` decides it."""
    from learn import knob_ceiling2 as K2

    margin = K2.WET_MARGIN if margin is None else margin
    s, h = "AB".index(r["search_half"]), "AB".index(r["held_half"])
    dry = ("dry", r["start_search"], r["start_held"])
    best = dry
    for name, e in r["per_effect"].items():
        ev = e["evals"][:budget] if budget else e["evals"]
        inc = min(ev, key=lambda x: x[s])
        if inc[s] < best[1]:
            best = (name, inc[s], inc[h])
    wet = best[0] != "dry" and math.log(best[1] / dry[1]) <= -margin
    return best if wet else dry


def kc2_stage2_rows(results, window=KC2_TAIL["stage2"]):
    """Zero renders: stage 2's effect searches (24 renders each) — each effect's tail, and each
    cell's choice with every effect cut to its first 12 renders against as run."""
    effects, cells = [], []
    for r in results:
        for name, e in r["per_effect"].items():
            curve = incumbent_curve(e["evals"], r["search_half"], r["held_half"])
            ds, dh = tail(curve, window)
            effects.append({"slug": r["slug"], "band": r["band"], "cls": r["gain_class"], "effect": name,
                            "renders": len(e["evals"]), "d_search": ds, "d_held": dh})
        full, half = stage2_choice(r), stage2_choice(r, window)
        cells.append({"slug": r["slug"], "band": r["band"], "cls": r["gain_class"], "amp": r["amp"],
                      "search": r["search_half"], "choice": full[0], "choice_half": half[0],
                      "matches_stored": full[0] == (r["effects_on"][0] if r["wet"] else "dry")
                      and math.isclose(full[2], r["held"], rel_tol=1e-12),
                      "d_held": _log(full[2], half[2])})
    return effects, cells


def tail_summary(rows):
    """Median and mean of the tails, the held tail band-weighted with its interval, and the rule."""
    ds = [r["d_search"] for r in rows]
    dh = [r["d_held"] for r in rows if r["d_held"] is not None]
    out = {"n": len(rows),
           "search": {"median": statistics.median(ds), "mean": statistics.fmean(ds),
                      "share_improving_by_min_gain": sum(d <= -MIN_GAIN for d in ds) / len(ds)},
           "held": {"median": statistics.median(dh), "mean": statistics.fmean(dh),
                    "bw": R.bw(R.part_rows(rows, lambda u: u["d_held"]))}}
    if rows and "rule_stop" in rows[0]:
        out["rule_flat_by_budget"] = sum(r["rule_stop"] is not None for r in rows)
    return out


# --- processes: the queue and the cap (amendment 1) -----------------------------------------------

def _ps():
    """[(pid, command)] for every process."""
    s = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout
    out = []
    for line in s.splitlines():
        pid, _, cmd = line.strip().partition(" ")
        if pid.isdigit():
            out.append((int(pid), cmd.strip()))
    return out


def _is_python(cmd):
    """The command's program is a python interpreter (not a shell wrapper that mentions one)."""
    first = cmd.split(" ", 1)[0] if cmd else ""
    return "python" in os.path.basename(first).lower()


def is_render_process(cmd):
    """A render process counted against the 3-process cap: a python running a module in RENDERS."""
    return _is_python(cmd) and any(re.search(p, cmd) for p in RENDERS)


def queue_pids(pids, ps):
    """Of the --after pids, those still running learn.song_relabel (a reused pid doesn't count)."""
    cmds = dict(ps)
    return [p for p in pids if p in cmds and _is_python(cmds[p]) and re.search(AFTER, cmds[p])]


def others_rendering(ps, own=()):
    """Render processes other than `own` (this process and its parent)."""
    return [p for p, c in ps if p not in own and is_render_process(c)]


def _wait_after(pids):
    while queue_pids(pids, _ps()):
        time.sleep(60)


def _wait_cap(cap=CAP):
    own = {os.getpid(), os.getppid()}
    while len(others_rendering(_ps(), own)) >= cap:
        time.sleep(60)


def check_saved(saved, meta):
    """Amendment 1: a direction resumes only under the rule, seed and round it started with."""
    bad = [k for k in ("rule", "seed") if saved.get(k) != meta[k]]
    if bad:
        raise SystemExit(f"{saved.get('slug')} {saved.get('amp')} {saved.get('search_half')}: saved "
                         f"{', '.join(bad)} differ from the code; not resuming")


# --- data access and commands (render only in `run`) ------------------------------------------------

def directions():
    """(slug, amp, search, held) for every knob-ceiling K_S direction (Honey's are skipped there)."""
    out = []
    for slug, amp in K.cells():
        p = K.OUT / "cells" / slug / amp / "result.json"
        if not p.exists():
            continue
        c = json.loads(p.read_text())
        for search, held in K.DIRECTIONS:
            if "skipped" not in c["runs"][search]:
                out.append((slug, amp, search, held))
    return out


def scored_parts():
    """{slug: (band, gain_class)} for the parts with K_S directions (24: Honey has none)."""
    ps = K.parts()
    return {s: (ps[s]["band"], ps[s]["gain_class"]) for s in sorted({d[0] for d in directions()})}


def the_design():
    sp = scored_parts()
    b = design({s: c for s, (_, c) in sp.items()})
    assert sorted(d for batch in b for d in batch) == sorted(directions())
    return b


def base_figures():
    """Every direction's stored S and K_S held distances (zero renders)."""
    sp, out = scored_parts(), {}
    for slug, amp, search, held in directions():
        c = json.loads((K.OUT / "cells" / slug / amp / "result.json").read_text())
        out[(slug, amp, search)] = {"slug": slug, "band": sp[slug][0], "cls": sp[slug][1],
                                    "S_held": c["menu"][c["start"]][held],
                                    "ks_held": c["runs"][search]["K_S"]["held"]}
    return out


def _paths(slug, amp, search):
    d = OUT / "cells" / slug / amp
    return d / f"{search}.json", d / f"{search}-settings.json"


def stored_results():
    out = {}
    for p in sorted((OUT / "cells").glob("*/*/[AB].json")):
        r = json.loads(p.read_text())
        out[(r["slug"], r["amp"], r["search_half"])] = r
    return out


def _kc_cells():
    return [json.loads(p.read_text()) for p in sorted((K.OUT / "cells").glob("*/*/result.json"))]


def cmd_check():
    """Zero renders: every K_S direction replays (the continuation's start and prior), the design,
    the stored K_S tails, and knob ceiling 2's stage-1 and stage-2 tails."""
    ms, ps = A.menu_S(), K.parts()
    dirs = directions()
    bad = []
    for slug, amp, search, _ in dirs:
        c = json.loads((K.OUT / "cells" / slug / amp / "result.json").read_text())
        S = ms[amp][ps[slug]["gain_class"]][1]
        _, x, _ = replay(amp, S, c["runs"][search]["K_S"]["evals"], search)
        st = A._settings(K.OUT / "cells" / slug / amp / f"K_S-{search}.json")
        if x != st:
            bad.append([slug, amp, search])
    s1 = [json.loads(p.read_text()) for p in sorted((KC2 / "stage1").glob("*/[AB].json"))]
    s2 = [json.loads(p.read_text()) for p in sorted((KC2 / "stage2").glob("*/[AB].json"))]
    eff, cells = kc2_stage2_rows(s2)
    out = {"directions": len(dirs), "replay_mismatches": bad,
           "design": [[list(d) for d in batch] for batch in the_design()],
           "K_S_tail_50": tail_summary(ks_tail_rows([c for c in _kc_cells() if c["slug"] in ps])),
           "kc2_stage1_tail_50": tail_summary(kc2_stage1_rows(s1)),
           "kc2_stage2_effect_tail_12": {
               "n": len(eff), "full_budget": sum(e["renders"] == 24 for e in eff),
               "search_median": statistics.median(e["d_search"] for e in eff),
               "share_improving_by_min_gain": sum(e["d_search"] <= -MIN_GAIN for e in eff) / len(eff)},
           "kc2_stage2_choice_half_vs_full": {
               "cells": len(cells), "choice_changed": sum(c["choice"] != c["choice_half"] for c in cells),
               "stored_choice_reproduced": sum(c["matches_stored"] for c in cells),
               "held_full_vs_half": R.bw(R.part_rows(cells, lambda u: u["d_held"]))}}
    OUT.mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "check.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "design"}, indent=1, default=str))
    if bad:
        print(f"{len(bad)} replay mismatch(es): `run` will refuse to start (amendment 1)")


def _run_direction(rr, menu, ps, slug, amp, search, held, warm):
    import numpy as np

    from learn import confirm_run as CR

    out, out_x = _paths(slug, amp, search)
    saved = json.loads(out.read_text()) if out.exists() else None
    meta = {"slug": slug, "amp": amp, "search_half": search, "held_half": held,
            "seed": SEED, "rule": {"chunk": CHUNK, "window": WINDOW, "min_gain": MIN_GAIN,
                                   "guard": GUARD, "round": ROUND}}
    if saved:
        check_saved(saved, meta)
    part = ps[slug]
    c = json.loads((K.OUT / "cells" / slug / amp / "result.json").read_text())
    assert c["start"] == K.START[part["gain_class"]][amp], (slug, amp)
    sel, S = menu[amp][c["start"]]
    ks = c["runs"][search]["K_S"]
    lookup, xr, gains = replay(amp, S, ks["evals"], search)
    x0 = A._settings(K.OUT / "cells" / slug / amp / f"K_S-{search}.json")
    if xr != x0:
        raise SystemExit(f"replay mismatch on {slug} {amp} {search}: stopping the run (amendment 1)")
    di = K.measure_di(part)
    di32, ref = di.astype(np.float32), CR.mono(part["crop"] / "reference.wav")
    first = (slug, amp) not in warm
    if first:
        rr.render(di32, sel, S)                                        # warm-up, counted
        warm.add((slug, amp))
    meta.update(band=part["band"], gain_class=part["gain_class"], S_held=c["menu"][c["start"]][held],
                S_search=c["menu"][c["start"]][search], warm_up=first or bool(saved and saved.get("warm_up")))

    def render(x):
        return K.judge(ref, rr.render(di32, sel, x), di, part["judge_lag"])

    def save(snap, status="running"):
        A._save(out, {**meta, **{k: v for k, v in snap.items() if k != "x"}, "status": status})

    try:
        res = extend(K.space(amp, S), x0, Resume(render, saved["log"] if saved else ()), search, held,
                     {search: ks["search"], held: ks["held"]}, lookup=lookup, gains=gains, on_chunk=save)
    except RepeatFailed as e:
        A._save(out, {**meta, "status": "repeat_failed", "repeat_dev": e.dev})
        print(slug, amp, search, "repeat_failed", round(e.dev, 5), flush=True)
        return
    out_x.write_text(json.dumps({f"{m}/{k}": v for (m, k), v in res["x"].items()}, indent=0))
    save(res, "done")
    print(slug, amp, search, res["stop"], res["renders"], rr.count, flush=True)


def cmd_run(shard, after=(), no_wait=False):
    """Amendment 1: the batches in order. This process runs its share (i::n, in seeded order) of the
    current batch, waits until every direction of the batch is finished, applies the batch rule
    (deterministic: every process agrees), and goes on or exits."""
    if not after and not no_wait:
        raise SystemExit("--after is empty: pass the relabel pids, or --no-wait to start now")
    if after:
        _wait_after(after)
    ps, batches, bands = K.parts(), the_design(), {s: b for s, (b, _) in scored_parts().items()}
    rr, guard, warm = None, A.SwapGuard(), set()
    try:
        while True:
            w = walk(batches, stored_results(), bands)
            if w["next"] is None:
                print("batch rule:", w["history"][-1] if w["history"] else None, flush=True)
                return
            batch = batches[w["next"]]
            for slug, amp, search, held in batch[shard[0]::shard[1]]:
                r = stored_results().get((slug, amp, search))
                if r is not None and r.get("status") in TERMINAL:
                    continue
                guard.check()
                _wait_cap()
                if rr is None:
                    rr = K.Renderer()
                    menu = rr.menu()
                _run_direction(rr, menu, ps, slug, amp, search, held, warm)
            while not all(stored_results().get(d[:3], {}).get("status") in TERMINAL for d in batch):
                time.sleep(60)                                     # the barrier
    finally:
        if rr is not None:
            rr.close()


def cmd_report():
    batches, bands = the_design(), {s: b for s, (b, _) in scored_parts().items()}
    results = stored_results()
    w = walk(batches, results, bands)
    out = summarise(base_figures(), results, w)
    out["complete"] = w["next"] is None
    K._atomic(OUT / "report.json", out)
    h = out["headline"]
    print(f"finished {h['directions_finished']}, converged by the declared rule {h['converged_by_the_declared_rule']}, "
          f"hit the 600 guard {h['hit_guard']} ({(h['guard_share'] or 0):.0%}) | complete: {out['complete']}")
    print("batches:", w["history"])
    for n, g in out["estimate"].items():
        s = g["all"]
        if s["band_weighted_mean"] is not None:
            print(f"  at {n:>4}: {s['band_weighted_mean']:+.3f} [{s['lo90']:+.3f}, {s['hi90']:+.3f}] "
                  f"bands− {s['bands_negative']}/{s['bands']}, still running {g['still_running']}")
    s = out["estimate_at_stop"]["all"]
    if s["band_weighted_mean"] is not None:
        print(f"  at stop: {s['band_weighted_mean']:+.3f} [{s['lo90']:+.3f}, {s['hi90']:+.3f}]")
    for name in ("extension_gain_held", "extension_gain_search"):
        for reason, s in out[name].items():
            if s["band_weighted_mean"] is not None:
                print(f"  {name} [{reason}, {s['directions']} dirs]: {s['band_weighted_mean']:+.3f} "
                      f"[{s['lo90']}, {s['hi90']}]")
    print("  renders:", out["renders"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("check", "run", "report"))
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--after", type=int, nargs="*", default=[], help="relabel pids to wait for")
    ap.add_argument("--no-wait", action="store_true", help="start without an --after list")
    a = ap.parse_args(argv)
    if a.step == "check":
        cmd_check()
    elif a.step == "run":
        i, n = map(int, a.shard.split("/"))
        cmd_run((i, n), a.after, a.no_wait)
    else:
        cmd_report()


if __name__ == "__main__":
    main()
