"""How much closer do searched knobs get than the best menu preset? (`docs/knob-ceiling-plan.md`)
Development only, the true DI (the "average guitar" measure DI), no model.

    .venv/bin/python -m learn.knob_ceiling control            # positive control, 2 parts
    .venv/bin/python -m learn.knob_ceiling run --shard 0/6    # one of 6 render processes
    .venv/bin/python -m learn.knob_ceiling report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
import statistics
import sys
from dataclasses import dataclass

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import confirm_run as CR  # noqa: E402
from learn import phase2_set3 as P  # noqa: E402
from learn import rescore as R  # noqa: E402

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/knob-ceiling"
AMPS = ("pr12", "sw50r", "ac20")
IN_SCOPE = ("clean", "crunch")
# The product's starting presets (skills/generate/SKILL.md, step 4), made dry by the menu's rule.
START = {"clean": {"pr12": "factory:Artists/Mark Johnston/Royally Ambient",
                   "sw50r": "factory:Artists/Mark Johnston/Pedal Platform Clean",
                   "ac20": "factory:Artists/Royce Whittaker/Low-Watt Americana"},
         "crunch": {"pr12": "factory:Artists/Keyan Houshmand/Modern Metal (Pick Hard)",
                    "sw50r": "factory:Neural DSP/Hair Metal",
                    "ac20": "factory:Neural DSP/AC20 Mid-Gain Drive"}}
BUDGET = {"K_M": 200, "K_S": 150, "EQ": 100}      # renders per cell, per search half
DIRECTIONS = (("A", "B"), ("B", "A"))              # (search half, held half)
SEED = 20261013


@dataclass(frozen=True)
class Dim:
    """One searched setting, in the plugin's stored units. `kind`: cont, log (a frequency,
    searched on a log scale), switch or cat (`values`)."""
    module: str
    key: str
    kind: str
    lo: float = 0.0
    hi: float = 1.0
    values: tuple = ()

    @property
    def name(self):
        return f"{self.module}/{self.key}"

    def to_unit(self, stored):
        v = min(max(float(stored), self.lo), self.hi)
        if self.kind == "log":
            return math.log(v / self.lo) / math.log(self.hi / self.lo)
        return (v - self.lo) / (self.hi - self.lo)

    def from_unit(self, u):
        u = min(max(u, 0.0), 1.0)
        if self.kind == "log":
            return self.lo * (self.hi / self.lo) ** u
        return self.lo + u * (self.hi - self.lo)


def _rot(module, *keys):
    return [Dim(module, k, "cont") for k in keys]


def _sw(module, *keys):
    return [Dim(module, k, "switch", values=("false", "true")) for k in keys]


MICS = tuple(str(i) for i in range(10))           # the internal mics; 10 (custom IR) is never chosen
CAB = ([Dim("cabParameters", f"{s}MicType", "cat", values=MICS) for s in ("left", "right")]
       + [Dim("cabParameters", f"{s}Cab{k}", "cont") for s in ("left", "right") for k in ("Position", "Distance")]
       + [Dim("cabParameters", "rightCabMicLevel", "cont", -40.0, 6.0)]
       + _sw("cabParameters", "rightCabActive"))
AMP_DIMS = {"pr12": _rot("pr12Amp", "pr12Volume", "pr12Treble", "pr12Bass"),
            "sw50r": _rot("sw50rAmp", "sw50rVolume", "sw50rLevel", "sw50rTreble", "sw50rMid", "sw50rBass")
            + _sw("sw50rAmp", "sw50rBright", "sw50rTrebleBoost", "sw50rInputMode"),
            "ac20": _rot("ac20Amp", "ac20Volume", "ac20Cut", "ac20Power") + _sw("ac20Amp", "ac20Bright", "ac20BassTreble")}


def space(amp, start=None):
    """The main search (K): input gain, the amp's own knobs and switches, both mics. The left
    mic's settings are left out when the start has the left cab off (the search can't turn it
    on, so they can't change the sound)."""
    cab = CAB
    if start is not None and start.get(("cabParameters", "leftCabActive")) == "false":
        cab = [d for d in CAB if not d.key.startswith("left")]
    return [Dim("parameters", "inputGain", "cont", -24.0, 24.0)] + AMP_DIMS[amp] + cab


def eq_space(amp):
    """The second stage (EQ): the amp's 9-band EQ and its two filters."""
    m = f"{amp}EQ"
    return ([Dim(m, f"{amp}EQBand{i}", "cont", -12.0, 12.0) for i in range(1, 10)]
            + [Dim(m, f"{amp}EQHpf", "log", 20.0, 500.0), Dim(m, f"{amp}EQLpf", "log", 1000.0, 20000.0)])


EQ_NEUTRAL = {"band": "0", "hpf": "20", "lpf": "20000"}


def eq_start(edits, amp):
    """A preset's edits with its amp EQ active; an inactive EQ is first made flat, so that
    switching it on starts from (near) no change."""
    m, out = f"{amp}EQ", dict(edits)
    if out.get((m, f"{amp}EQActive")) != "true" or out.get(("eqParameters", "sectionActive")) != "true":
        for i in range(1, 10):
            out[(m, f"{amp}EQBand{i}")] = EQ_NEUTRAL["band"]
        out[(m, f"{amp}EQHpf")] = EQ_NEUTRAL["hpf"]
        out[(m, f"{amp}EQLpf")] = EQ_NEUTRAL["lpf"]
    out[(m, f"{amp}EQActive")] = "true"
    out[("eqParameters", "sectionActive")] = "true"
    return out


def fmt(x):
    return f"{x:.6g}"


def key(settings):
    return hashlib.sha1(json.dumps(sorted(settings.items())).encode()).hexdigest()[:16]


def coord_search(dims, x0, f, budget, seed, step0=0.25, min_step=1 / 64):
    """Coordinate search with shrinking steps, deterministic for a seed.

    `x0`: {(module, key): stored string}, the whole preset; only `dims` move. `f(x)` returns
    the distance to minimise; it is called once per distinct setting and at most `budget`
    times (the start included). A sweep visits the dims in a seeded order and, per dim,
    tries: a continuous dim ± step (in unit space), a switch flipped, a categorical dim
    every other value (in the first sweep, and once more when the step first falls below
    1/8). The best improving candidate is kept. A sweep with no improvement halves the step.
    Returns (best x, best value, trace), trace = [(evaluations so far, best value)].
    """
    rng = random.Random(seed)
    cache = {}

    def ev(x):
        k = key(x)
        if k not in cache:
            if len(cache) >= budget:
                return None
            cache[k] = f(x)
        return cache[k]

    x = dict(x0)
    best = ev(x)
    trace = [(1, best)]
    step, cats_again = step0, True
    first = True
    while len(cache) < budget and step >= min_step:
        order = list(dims)
        rng.shuffle(order)
        improved = False
        for d in order:
            k = (d.module, d.key)
            cur = x.get(k)
            if d.kind == "cat":
                if not first and not (cats_again and step < 1 / 8):
                    continue
                cands = [v for v in d.values if v != cur]
            elif d.kind == "switch":
                cands = [v for v in d.values if v != cur][:1]
            else:
                u = d.to_unit(cur if cur is not None else d.lo)
                cands = sorted({fmt(d.from_unit(u + s)) for s in (step, -step)} - {cur})
            got = []
            for v in cands:
                y = dict(x)
                y[k] = v
                val = ev(y)
                if val is None:
                    break
                got.append((val, v))
            if got:
                val, v = min(got)
                if val < best - 1e-12:
                    best, x[k], improved = val, v, True
            trace.append((len(cache), best))
            if len(cache) >= budget:
                break
        if first:
            first = False
        elif step < 1 / 8 and cats_again:
            cats_again = False
        if not improved:
            step /= 2
    return x, best, trace


def at_limit(dims, x, x0):
    """Continuous dims the search moved to the end of their range."""
    out = []
    for d in dims:
        k = (d.module, d.key)
        if d.kind in ("cont", "log") and k in x:
            u = d.to_unit(x[k])
            if (u <= 1e-6 or u >= 1 - 1e-6) and x[k] != x0.get(k):
                out.append(d.name)
    return out


def log_ratio(a, b):
    return math.log(a / b)


# ---------------------------------------------------------------- rendering (not unit-tested)

def parts():
    from learn import songs_check as SC

    ps = {s: p for s, p in SC.parts().items() if p["gain_class"] in IN_SCOPE}
    return ps


def measure_di(part):
    """`confirm_run.build_di("measfix", …)`, without importing torch."""
    import numpy as np

    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to, to_lufs

    avg = np.load(CR.AVERAGE)
    di = CR.mono(part["crop"] / "di.wav")
    own = smoothed_spectrum(di)
    return to_lufs(eq_to(di, avg - (own - own.mean())))


class Renderer:
    """A reused plugin process; `render(di, select, edits)` with edits {(module, key): stored}."""

    def __init__(self):
        from match.renderer_au import AudioUnitRenderer
        from packs.loader import load_pack

        class _R(AudioUnitRenderer):
            def _state_command(self, settings):
                return {"selectAmp": settings["select"],
                        "edits": [{"module": m, "key": k, "value": v} for m, k, v in settings["edits"]]}

        self.pack = load_pack("morgan")
        self.r = _R("morgan", process_policy="reuse")
        self.count = 0

    def menu(self):
        """amp -> {name: (select, {(module, key): stored})}."""
        return {amp: {n: (sel, {(e["module"], e["key"]): e["value"] for e in ed})
                      for n, (sel, ed) in m.items()} for amp, m in P.menus(self.pack, self.r).items()}

    def render(self, di32, select, edits):
        import numpy as np

        self.count += 1
        edits = [[m, k, v] for (m, k), v in edits.items()]
        return np.asarray(self.r.render(di32, {"select": select, "edits": edits}).audio, np.float64)

    def close(self):
        self.r.close()


def judge(ref, y, di, lag):
    from analysis.aligned import aligned_distance

    out = {}
    for h, (a, b) in R.HALVES.items():
        x = aligned_distance(ref, y, di, lag=lag, render_latency=P.LATENCY, start_s=a, end_s=b).distance
        out[h] = math.inf if x is None else x          # a refusal (silence) is the worst
    return out


def _atomic(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


REPEAT_TOL = 0.005        # |log ratio| between a search's first render and the stored menu render


def finite(*xs):
    return all(x is not None and math.isfinite(x) for x in xs)


def usable(menu_d, start_name, M, search, held):
    """A direction is searched only if the start and M are scored on both halves (plan,
    "Refusals")."""
    return finite(menu_d[start_name][search], menu_d[start_name][held], menu_d[M][search], menu_d[M][held])


def run_cell(rr, menu, amp, ref, di, lag, start_name, out_dir, budgets=BUDGET, seed=SEED):
    """One part × amp: the menu on both halves, then per direction K_M, K_S and EQ (from
    K_M's best). Every evaluation scores both halves; the search sees only its own half."""
    import numpy as np

    di32 = di.astype(np.float32)
    first = next(iter(menu[amp]))
    rr.render(di32, *menu[amp][first])                                  # warm-up per amp
    menu_d = {n: judge(ref, rr.render(di32, sel, ed), di, lag) for n, (sel, ed) in menu[amp].items()}
    select = menu[amp][start_name][0]
    res = {"menu": menu_d, "start": start_name, "runs": {}, "repeat": {}}
    for search, held in DIRECTIONS:
        finite_menu = [n for n in menu_d if finite(menu_d[n][search])]
        M = min(finite_menu, key=lambda n: menu_d[n][search]) if finite_menu else None
        if M is None or not usable(menu_d, start_name, M, search, held):
            res["runs"][search] = {"M": M, "skipped": "a half is refused for the start or M"}
            continue
        run = {"M": M}
        starts = {"K_M": (M, menu[amp][M][1]), "K_S": (start_name, menu[amp][start_name][1])}
        for tag in ("K_M", "K_S", "EQ"):
            dims = eq_space(amp) if tag == "EQ" else space(amp, starts[tag][1])
            start = eq_start(run["_kx"], amp) if tag == "EQ" else starts[tag][1]
            evals, keep = [], {"d": math.inf, "y": None}

            def f(x):
                y = rr.render(di32, select, x)
                d = judge(ref, y, di, lag)
                evals.append(d)
                if d[search] < keep["d"]:
                    keep.update(d=d[search], y=y)
                return d[search]

            x, _, _ = coord_search(dims, start, f, budgets[tag], seed + (tag == "EQ"))
            if tag != "EQ":                     # the first render repeats a stored menu render
                stored = menu_d[starts[tag][0]]
                dev = max(abs(math.log(evals[0][h] / stored[h])) for h in R.HALVES)
                res["repeat"][f"{tag}-{search}"] = dev
                if dev > REPEAT_TOL:
                    raise RuntimeError(f"repeat render moved by {dev:.4f} (log) on {tag}-{search}")
            run[tag] = summary(evals, search, held, dims, x, start)
            if tag == "K_M":
                run["_kx"] = x
            if out_dir is not None:
                save_best(out_dir, f"{tag}-{search}", keep["y"], x)
        del run["_kx"]
        res["runs"][search] = run
    return res


def summary(evals, search, held, dims, x, start):
    """The incumbent (best so far on the search half) after each render, on both halves, and
    every evaluation. The start is finite on the search half (`usable`), so there is always
    an incumbent."""
    inc, best, curve = evals[0], evals[0][search], []
    for i, d in enumerate(evals):
        if d[search] < best - 1e-12:
            best, inc = d[search], d
        curve.append((i + 1, inc[search], inc[held]))
    return {"search": inc[search], "held": inc[held], "start_search": evals[0][search],
            "start_held": evals[0][held], "renders": len(evals), "curve": curve,
            "evals": [(d["A"], d["B"]) for d in evals],
            "changed": {f"{m}/{k}": v for (m, k), v in x.items() if start.get((m, k)) != v},
            "at_limit": at_limit(dims, x, start)}


def save_best(out_dir, name, y, x):
    import numpy as np
    import soundfile as sf

    if y is not None:
        sf.write(out_dir / f"{name}.flac", y * (0.99 / max(np.abs(y).max(), 1e-12)), P.SR, subtype="PCM_24")
    (out_dir / f"{name}.json").write_text(json.dumps({f"{m}/{k}": v for (m, k), v in x.items()}, indent=0))


def check_parts(ps):
    """The declared development parts (plan, "Data")."""
    assert len(ps) == 25, len(ps)
    assert len({p["band"] for p in ps.values()}) == 15
    assert sum(p["gain_class"] == "clean" for p in ps.values()) == 20
    assert sum(p["gain_class"] == "crunch" for p in ps.values()) == 5
    from learn import set3
    from learn import songs_check as SC

    prep = json.loads(SC.PREP.read_text())          # built only from development sessions (asserted there)
    s3 = {p["slug"] for p in set3.parts("development")}
    for slug, p in ps.items():
        assert (p["set"] == 3 and slug in s3) or (p["set"] == 12 and slug in prep), slug


def cells():
    return [(slug, amp) for slug in sorted(parts()) for amp in AMPS]


def run(shard):
    ps = parts()
    check_parts(ps)
    rr = Renderer()
    try:
        menu = rr.menu()
        for cls in IN_SCOPE:
            for amp in AMPS:
                assert START[cls][amp] in menu[amp], START[cls][amp]
        cache = {}
        for slug, amp in cells()[shard[0]::shard[1]]:
            d = OUT / "cells" / slug / amp
            if (d / "result.json").exists():
                continue
            part = ps[slug]
            if slug not in cache:
                cache.clear()
                cache[slug] = (measure_di(part), CR.mono(part["crop"] / "reference.wav"))
            di, ref = cache[slug]
            d.mkdir(parents=True, exist_ok=True)
            res = run_cell(rr, menu, amp, ref, di, part["judge_lag"], START[part["gain_class"]][amp], d)
            res.update(slug=slug, amp=amp, band=part["band"], gain_class=part["gain_class"])
            _atomic(d / "result.json", res)
            print(slug, amp, rr.count, flush=True)
    finally:
        rr.close()


CONTROL_PARTS = 2
# Off the search grid (steps 0.25, 0.125, …): amp knobs, input gain (dB) and a cab position.
PERTURB = {"pr12": {("pr12Amp", "pr12Volume"): 0.17, ("pr12Amp", "pr12Treble"): -0.21,
                    ("pr12Amp", "pr12Bass"): 0.13},
           "sw50r": {("sw50rAmp", "sw50rVolume"): 0.17, ("sw50rAmp", "sw50rTreble"): -0.21,
                     ("sw50rAmp", "sw50rMid"): 0.13}}
PERTURB_ALL = {("parameters", "inputGain"): 5.3, ("cabParameters", "leftCabPosition"): 0.31}


def perturbed(dims, x0, moves):
    """x0 with each move applied, reflected inwards when it would leave the range."""
    by = {(d.module, d.key): d for d in dims}
    out = dict(x0)
    for k, dv in moves.items():
        d = by[k]
        v = float(x0[k]) + dv
        if not d.lo <= v <= d.hi:
            v = float(x0[k]) - dv
        out[k] = fmt(v)
    return out


def control():
    """The positive control (plan, "Controls"): a known preset with 5 settings and one mic
    moved is the "recording"; the search starts from the unmoved preset. Plus the repeat floor."""
    import numpy as np

    ps = parts()
    picks = [sorted(s for s in ps if ps[s]["gain_class"] == c and ps[s]["set"] == 12)[0] for c in IN_SCOPE]
    rr = Renderer()
    out = {}
    try:
        menu = rr.menu()
        for slug in picks[:CONTROL_PARTS]:
            part = ps[slug]
            di = measure_di(part)
            di32 = di.astype(np.float32)
            for amp in ("pr12", "sw50r"):
                name = START[part["gain_class"]][amp]
                sel, x0 = menu[amp][name]
                dims = space(amp, x0)
                moves = {**PERTURB[amp], **PERTURB_ALL}
                target = perturbed(dims, x0, moves)
                mic = ("cabParameters", "leftMicType")
                target[mic] = str((int(x0[mic]) + 4) % 10)
                rr.render(di32, sel, x0)                                   # warm-up
                fake = rr.render(di32, sel, target)
                again = rr.render(di32, sel, target)
                rr.render(di32, sel, x0)
                again2 = rr.render(di32, sel, target)
                floor = judge(fake, again2, di, 0)
                evals = []

                def f(x):
                    d = judge(fake, rr.render(di32, sel, x), di, 0)
                    evals.append(d)
                    return d["A"]

                x, best, trace = coord_search(dims, x0, f, BUDGET["K_M"], SEED)
                inc, bA = evals[0], evals[0]["A"]
                for d in evals:
                    if d["A"] < bA:
                        bA, inc = d["A"], d
                by = {(d.module, d.key): d for d in dims}
                rec = {f"{m}/{k}": {"start": x0[(m, k)], "target": target[(m, k)], "found": x[(m, k)],
                                    "unit_error": abs(by[(m, k)].to_unit(x[(m, k)]) - by[(m, k)].to_unit(target[(m, k)]))}
                       for (m, k) in moves}
                cont_ok = sum(v["unit_error"] <= 0.1 for v in rec.values())
                mic_ok = x[mic] == target[mic]
                curve = [(n, b) for n, b in trace]
                out[f"{slug}|{amp}"] = {
                    "repeat_identical": bool(np.array_equal(fake[P.SR:], again[P.SR:])),
                    "repeat_after_other_preset": floor, "start": evals[0], "best_A_search": bA,
                    "best_held_B": inc["B"], "ratio_held": inc["B"] / evals[0]["B"],
                    "recovered": rec, "mic": {"start": x0[mic], "target": target[mic], "found": x[mic]},
                    "settings_within_0.1": cont_ok, "mic_exact": mic_ok,
                    "renders": len(evals), "curve": curve, "at_limit": at_limit(dims, x, x0)}
                print(slug, amp, round(inc["B"] / evals[0]["B"], 4), f"{cont_ok}/5", mic_ok, flush=True)
    finally:
        rr.close()
    ok = control_passes(out)
    out["_pass"] = ok
    print("CONTROL PASSES" if ok else "CONTROL FAILS", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    _atomic(OUT / "control.json", out)


def control_passes(out):
    """Declared: every cell's held distance falls to ≤ 0.3 × the start's, and on at least 3 of
    4 cells at least 3 of the 5 moved settings land within 0.1 (0–1 scale) with the mic exact."""
    cs = [v for k, v in out.items() if not k.startswith("_")]
    return (all(c["ratio_held"] <= 0.3 for c in cs)
            and sum(c["settings_within_0.1"] >= 3 and c["mic_exact"] for c in cs) >= 3)


# ---------------------------------------------------------------- report

COMPARISONS = ("M_vs_S", "KM_vs_M", "KS_vs_S", "KS_vs_M", "EQ_vs_KM", "EQ_vs_M")
CHECKPOINTS = (25, 50, 100, 150, 200)


def _at(curve, n):
    """The incumbent (search, held) after n renders (the last, if the search stopped sooner)."""
    return curve[min(n, len(curve)) - 1][1:]


def cell_rows(res):
    """Per cell: cross-half log ratios, averaged over the usable directions, and in-sample
    ones. A comparison with a non-finite side in a direction drops that direction for it."""
    S = res["start"]
    cross, ins = {}, {}
    for search, held in DIRECTIONS:
        run = res["runs"][search]
        if "skipped" in run:
            continue
        m = res["menu"]
        s_h, s_s = m[S][held], m[S][search]
        M_h, M_s = m[run["M"]][held], m[run["M"]][search]
        K, KS, EQ = run["K_M"], run["K_S"], run["EQ"]
        pairs = {"M_vs_S": (M_h, s_h, M_s, s_s),
                 "KM_vs_M": (K["held"], M_h, K["search"], M_s),
                 "KS_vs_S": (KS["held"], s_h, KS["search"], s_s),
                 "KS_vs_M": (KS["held"], M_h, KS["search"], M_s),
                 "EQ_vs_KM": (EQ["held"], K["held"], EQ["search"], K["search"]),
                 "EQ_vs_M": (EQ["held"], M_h, EQ["search"], M_s)}
        if "curve" in K:
            for n in CHECKPOINTS:
                ks, kh = _at(K["curve"], n)
                pairs[f"KM@{n}_vs_M"] = (kh, M_h, ks, M_s)
        for name, (a, b, a2, b2) in pairs.items():
            if finite(a, b) and a > 0 and b > 0:
                cross.setdefault(name, []).append(log_ratio(a, b))
            if finite(a2, b2) and a2 > 0 and b2 > 0:
                ins.setdefault(name, []).append(log_ratio(a2, b2))
    return ({k: statistics.fmean(v) for k, v in cross.items()},
            {k: statistics.fmean(v) for k, v in ins.items()})


def best_amp_rows(cs):
    """Per part and direction, the amp a chooser would take: M's amp by M's search-half
    distance, K_M's by K_M's. Held-half log ratio K_M vs M, averaged over directions."""
    by = {}
    for c in cs:
        by.setdefault(c["slug"], []).append(c)
    rows = []
    for slug, group in by.items():
        xs = []
        for search, held in DIRECTIONS:
            ok = [c for c in group if "skipped" not in c["runs"][search]]
            if not ok:
                continue
            m = min(ok, key=lambda c: c["menu"][c["runs"][search]["M"]][search])
            k = min(ok, key=lambda c: c["runs"][search]["K_M"]["search"])
            a, b = k["runs"][search]["K_M"]["held"], m["menu"][m["runs"][search]["M"]][held]
            if finite(a, b):
                xs.append(log_ratio(a, b))
        if xs:
            rows.append((group[0]["band"], statistics.fmean(xs)))
    return rows


def reading(s, what="knobs"):
    """The declared reading (descriptive, not a gate). "A lot" is by the judge; it counts as
    real only after the listening check."""
    if s["band_weighted_mean"] >= -0.04 and s["mean"] >= -0.04:
        return f"{what} add little: the menu is near the ceiling"
    if s["band_weighted_mean"] <= -0.10 and s["bands_negative"] > s["bands"] / 2:
        return f"{what} add a lot by the judge (real only if the listening check agrees)"
    return "in between"


def _group(sel):
    rows = [(c, *cell_rows(c)) for c in sel]
    rows = [r for r in rows if r[1]]
    g = {"cells_used": len(rows), "cells_dropped": len(sel) - len(rows)}
    names = sorted({n for _, cr, _ in rows for n in cr})
    for name in names:
        g[name] = CR.stats([(c["band"], cr[name]) for c, cr, _ in rows if name in cr])
        g[name + " (in-sample)"] = CR.stats([(c["band"], ins[name]) for c, _, ins in rows if name in ins])
    return g


def report():
    cs = [json.loads(p.read_text()) for p in sorted((OUT / "cells").glob("*/*/result.json"))]
    out = {"cells": len(cs),
           "skipped_directions": [(c["slug"], c["amp"], s) for c in cs for s, _ in DIRECTIONS
                                  if "skipped" in c["runs"][s]],
           "repeat_max": max((v for c in cs for v in c.get("repeat", {}).values()), default=None)}
    for group, keep in (("clean+crunch", IN_SCOPE), ("clean", ("clean",)), ("crunch", ("crunch",))):
        sel = [c for c in cs if c["gain_class"] in keep]
        if not sel:
            continue
        g = _group(sel)
        if "KM_vs_M" in g:
            g["reading"] = reading(g["KM_vs_M"])
        if "EQ_vs_KM" in g:
            g["reading_eq"] = reading(g["EQ_vs_KM"], "the EQ")
        runs = [c["runs"][s] for c in sel for s, _ in DIRECTIONS if "skipped" not in c["runs"][s]]
        g["at_limit_share"] = statistics.fmean(bool(r["K_M"]["at_limit"]) for r in runs) if runs else None
        g["best_amp KM_vs_M"] = CR.stats(best_amp_rows(sel))
        g["per_amp"] = {amp: _group([c for c in sel if c["amp"] == amp]) for amp in AMPS}
        out[group] = g
    _atomic(OUT / "result.json", out)
    for group in ("clean+crunch", "clean", "crunch"):
        g = out.get(group)
        if not g:
            continue
        print(group, "—", g.get("reading"), "| EQ:", g.get("reading_eq"))
        for name, s in g.items():
            if isinstance(s, dict) and "mean" in s:
                print(f"  {name:28s} mean {s['mean']:+.3f} band-w {s['band_weighted_mean']:+.3f} "
                      f"90% [{s['lo90']:+.3f}, {s['hi90']:+.3f}] bands− {s['bands_negative']}/{s['bands']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("control", "run", "report"))
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args(argv)
    if a.step == "control":
        control()
    elif a.step == "run":
        i, n = map(int, a.shard.split("/"))
        run((i, n))
    else:
        report()


if __name__ == "__main__":
    main()
