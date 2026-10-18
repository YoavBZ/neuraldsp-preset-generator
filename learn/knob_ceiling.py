"""How much closer do searched knobs get than the best menu preset? (`docs/knob-ceiling-plan.md`)
Development only, the true DI (the "average guitar" measure DI), no model.

    .venv/bin/python -m learn.knob_ceiling control            # positive control, 2 parts
    .venv/bin/python -m learn.knob_ceiling run --shard 0/6    # one of 6 render processes
    .venv/bin/python -m learn.knob_ceiling report
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import pathlib
import random
import shutil
import statistics
import sys
import tempfile
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
    return [Dim("parameters", "inputGain", "cont", -20.0, 12.0)] + AMP_DIMS[amp] + cab


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


def coord_search(dims, x0, f, budget, seed, step0=0.25, min_step=1 / 64, cats="once", gains=None,
                 pattern=True, canon=None):
    """Coordinate search with shrinking steps, deterministic for a seed.

    `x0`: {(module, key): stored string}, the whole preset; only `dims` move. `f(x)` returns
    the distance to minimise; it is called once per distinct setting and at most `budget`
    times (the start included). A sweep visits the dims in a seeded order and, per dim,
    tries: a continuous dim ± step (in unit space), a switch flipped, a categorical dim
    every other value. `cats`: "once" tries the categorical dims in the first sweep and once
    more when the step first falls below 1/8; "levels" skips them in the first sweep (so the
    knobs move first) and tries them in the first sweep at every step size after that. The
    best improving candidate is kept. A sweep with no improvement halves the step.
    Returns (best x, best value, trace), trace = [(evaluations so far, best value)].
    `gains`, if given, collects each dim's total improvement. With `pattern`, a sweep that
    improved is followed by Hooke–Jeeves pattern moves (below). `canon`, if given, maps a
    setting to its canonical form before it is cached or evaluated (e.g. an off pedal's knobs
    to fixed values), so a move that changes nothing audible costs nothing and can't win.
    """
    rng = random.Random(seed)
    cache = {}

    def ev(x):
        if canon is not None:
            x = canon(x)
        k = key(x)
        if k not in cache:
            if len(cache) >= budget:
                return None
            v = f(x)
            if v is None:                       # the caller's own budget is spent
                return None
            cache[k] = v
        return cache[k]

    x = dict(x0)
    best = ev(x)
    if best is None:
        return x, None, []
    trace = [(1, best)]
    step, cats_again = step0, True
    first = True
    sweep, cats_tried = 0, set()
    while len(cache) < budget and step >= min_step:
        sweep += 1
        new_level = sweep > 1 and step not in cats_tried
        if new_level:
            cats_tried.add(step)
        order = list(dims)
        rng.shuffle(order)
        improved = False
        sweep_start = dict(x)
        for d in order:
            k = (d.module, d.key)
            cur = x.get(k)
            if d.kind == "cat":
                if cats == "levels":
                    if not new_level:
                        continue
                elif not first and not (cats_again and step < 1 / 8):
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
                    if gains is not None:
                        gains[d.name] = gains.get(d.name, 0.0) + best - val
                    best, x[k], improved = val, v, True
            trace.append((len(cache), best))
            if len(cache) >= budget:
                break
        if improved and pattern and len(cache) < budget:
            # Hooke–Jeeves pattern move: keep going the way the whole sweep went (a valley
            # across the knobs, which single-knob moves can only zig-zag along), further
            # while it improves.
            end = dict(x)
            moved = {(d.module, d.key): d for d in dims if d.kind in ("cont", "log")
                     and (d.module, d.key) in x and (d.module, d.key) in sweep_start
                     and x[(d.module, d.key)] != sweep_start[(d.module, d.key)]}
            for mult in (1, 2, 3):              # the sweep's move, once, twice, three times more
                y = dict(end)
                for k, d in moved.items():
                    u = d.to_unit(end[k])
                    y[k] = fmt(d.from_unit(u + mult * (u - d.to_unit(sweep_start[k]))))
                if y == x:
                    break
                val = ev(y)
                if val is None or val >= best - 1e-12:
                    break
                best, x = val, y
                trace.append((len(cache), best))
        if first:
            first = False
        elif step < 1 / 8 and cats_again:
            cats_again = False
        if not improved:
            step /= 2
    return x, best, trace


SHARES = {"main": 0.35, "alts": 0.35, "restarts": 0.2}    # the rest is the final stage


def knob_search(dims, x0, f, budget, seed, shares=SHARES, n_alt=2, n_key=3, canon=None, gains=None):
    """The declared optimiser (plan, amendment 2): `coord_search` with mic restarts, each
    stage on a fixed share of the budget.

    1. **main** (35%): `coord_search`, mics after the knobs move, at every step size, with
       Hooke–Jeeves pattern moves. It records which continuous dims gave the most improvement
       (the `n_key` key dims).
    2. **alts** (35%): every other value of every mic, left and right interleaved, each set on
       the incumbent and followed by a quick re-tune of the key dims (an equal share each,
       steps 0.25 and 0.125). A wrong mic with the knobs compensating is a trap for a
       coordinate search: the right mic looks worse until the knobs follow it.
    3. **restarts** (20%): the `n_alt` best alternatives, each with every non-mic dim
       searched again from step 0.125.
    4. **final** (the rest): the full search again from the best so far.
    A stage with nothing to do (no mics: the EQ) passes its share on. Returns (best x, best
    value, trace, stages); every distinct setting is rendered once in all; `stages` records
    each stage's renders and best value. `gains`, if given, is the per-dim improvement so far
    (updated in place by the main stage): a continued search ranks its key dims over the whole
    run, not its own main stage alone (`learn/ks_extend.py`)."""
    cache, hist, stages = {}, [], {}
    state = {"limit": 0, "best": math.inf}

    def g(x):
        if canon is not None:
            x = canon(x)
        k = key(x)
        if k in cache:
            return cache[k]
        if len(cache) >= min(state["limit"], budget):
            return None
        cache[k] = v = f(x)
        state["best"] = min(state["best"], v)
        hist.append((len(cache), state["best"]))
        return v

    def mark(name, n0):
        stages[name] = {"renders": len(cache) - n0, "best": state["best"]}

    big = 10 ** 9
    cats = [d for d in dims if d.kind == "cat"]
    others = [d for d in dims if d.kind != "cat"]
    gains = {} if gains is None else gains
    n0 = len(cache)
    state["limit"] = max(1, round(budget * shares["main"]))
    x, best, _ = coord_search(dims, x0, g, big, seed, cats="levels", gains=gains, canon=canon)
    mark("main", n0)
    if best is None:
        return x, None, hist, stages
    if cats:
        key_dims = sorted((d for d in others if d.kind in ("cont", "log")),
                          key=lambda d: (-gains.get(d.name, 0.0), d.name))[:n_key]
        options = [[(d, v) for v in d.values if v != x.get((d.module, d.key))] for d in cats]
        order = [o for group in itertools.zip_longest(*options) for o in group if o is not None]
        stage_end = len(cache) + round(budget * shares["alts"])
        each = max(1, (stage_end - len(cache)) // max(1, len(order)))
        n0, alts = len(cache), []
        for d, v in order:
            y = dict(x)
            y[(d.module, d.key)] = v
            state["limit"] = min(stage_end, len(cache) + each)
            qx, qv, _ = coord_search(key_dims, y, g, big, seed + 5, step0=0.25, min_step=0.125, canon=canon)
            if qv is None:
                continue
            alts.append((qv, d.name, v, qx))
        mark("alts", n0)
        for val, _, _, y in alts:
            if val < best:
                best, x = val, y
        n0 = len(cache)
        stage_end = len(cache) + round(budget * shares["restarts"])
        per = max(1, (stage_end - len(cache)) // n_alt)
        for i, (_, _, _, y) in enumerate(sorted(alts, key=lambda a: (a[0], a[1], a[2]))[:n_alt]):
            state["limit"] = min(stage_end, len(cache) + per)
            bx, bv, _ = coord_search(others, y, g, big, seed + 10 + i, step0=0.125, canon=canon)
            if bv is not None and bv < best:
                best, x = bv, bx
        mark("restarts", n0)
    n0 = len(cache)
    state["limit"] = budget
    if len(cache) < budget:
        bx, bv, _ = coord_search(dims, x, g, big, seed + 99, step0=0.125, cats="levels", canon=canon)
        if bv is not None and bv < best:
            best, x = bv, bx
    mark("final", n0)
    return (canon(x) if canon is not None else x), best, hist, stages


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


PREROLL_S = 0.0            # amendment 3: replaced by `isolate`; kept for the cells rendered with 6 s

# DI files a renderer keeps in its work directory. `AudioUnitRenderer` writes each distinct DI
# once (~2 MB for a 10 s section) and keeps it until close; a render set that walks thousands of
# distinct DIs (`learn/pretrain_set.py`) grew each server's directory by ~750 MB in 15 minutes.
# The bound lives here, not in `match/renderer_au.py`, because any edit there changes the
# renderer build that Tone King's calibrations record (tests/test_calibration_schema.py).
DI_FILES_KEPT = 4


def keep_recent_dis(files, current, keep=DI_FILES_KEPT):
    """Mark `current` most recently used in the renderer's {digest: path} map, then delete the
    least recently used files beyond `keep`. An evicted DI that comes back is written again by
    `AudioUnitRenderer._di_file` with the same bytes under the same name."""
    digest = next(d for d, p in files.items() if p == current)
    files[digest] = files.pop(digest)
    while len(files) > keep:
        stale = files.pop(next(iter(files)))
        stale.unlink(missing_ok=True)


# The render server learn runs: a copy of `scripts/au_render_server.swift` whose decoded-DI cache
# keeps the 4 most recently used DIs instead of all of them (~1.85 MB of RAM per distinct DI held).
# It does not touch a separate ~1.1 MB-per-render growth both servers show (pretrain-set plan,
# amendment 2, item 3). Learn-owned for the same reason as
# DI_FILES_KEPT: the shipped server's bytes are part of the renderer build Tone King's
# measurements record. Renders are bit-identical to the shipped server's (pretrain-set plan,
# amendment 2).
BOUNDED_SERVER_SOURCE = pathlib.Path(__file__).resolve().parent / "au_render_server_bounded.swift"


def build_bounded_server(directory):
    """Compile the bounded server into `directory` the way `AudioUnitRenderer._compile` builds the
    shipped one (`scripts/_swift.compile_swift`, with its shared build cache) -> the binary."""
    if str(PLUGIN_ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
    from _swift import compile_swift
    from match.renderer_au import AudioUnitError

    output = pathlib.Path(directory) / BOUNDED_SERVER_SOURCE.stem
    built, error = compile_swift(BOUNDED_SERVER_SOURCE, output)
    if built is None or built.returncode != 0:
        raise AudioUnitError(f"could not build {BOUNDED_SERVER_SOURCE.name}:\n{error}")
    return output


def renderer_class():
    """Morgan's `AudioUnitRenderer` with the select/edits state command and bounded DI files."""
    from match.renderer_au import AudioUnitRenderer

    class _R(AudioUnitRenderer):
        def _state_command(self, settings):
            return {"selectAmp": settings["select"],
                    "edits": [{"module": m, "key": k, "value": v} for m, k, v in settings["edits"]]}

        def _di_file(self, di):
            path = super()._di_file(di)
            keep_recent_dis(self._di_files, path)
            return path

    return _R


class Renderer:
    """A reused plugin process; `render(di, select, edits)` with edits {(module, key): stored}."""

    def __init__(self):
        from packs.loader import load_pack

        self.pack = load_pack("morgan")
        # `isolate`: render resources are freed and rebuilt around every state write. Morgan's
        # `reset` (which the server calls before every render) leaves some state from the
        # previous render audible for 2-3 s, at the amp's hiss level (plan, amendment 3);
        # rebuilding clears it, at no measurable cost.
        # The bounded server (above), built into a directory this object owns and removes.
        self._bin_dir = pathlib.Path(tempfile.mkdtemp(prefix="au-bounded-"))
        try:
            binary = build_bounded_server(self._bin_dir)
            self.r = renderer_class()("morgan", process_policy="reuse", isolate=True, binary=binary)
        except BaseException:
            shutil.rmtree(self._bin_dir, ignore_errors=True)
            raise
        self.count = 0

    def menu(self):
        """amp -> {name: (select, {(module, key): stored})}."""
        return {amp: {n: (sel, {(e["module"], e["key"]): e["value"] for e in ed})
                      for n, (sel, ed) in m.items()} for amp, m in P.menus(self.pack, self.r).items()}

    def render(self, di32, select, edits):
        """One render; with PREROLL_S > 0, after that much silence, cut off (plan, amendment 3)."""
        import numpy as np

        self.count += 1
        edits = [[m, k, v] for (m, k), v in edits.items()]
        pre = int(PREROLL_S * P.SR)
        x = np.concatenate([np.zeros(pre, np.float32), di32])
        y = np.asarray(self.r.render(x, {"select": select, "edits": edits}).audio, np.float64)
        return y[pre:pre + len(di32)]

    def close(self):
        try:
            self.r.close()
        finally:
            shutil.rmtree(self._bin_dir, ignore_errors=True)


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

            x, _, _, stages = knob_search(dims, start, f, budgets[tag], seed + (tag == "EQ"))
            if tag != "EQ":                     # the first render repeats a stored menu render
                stored = menu_d[starts[tag][0]]
                dev = max(abs(math.log(evals[0][h] / stored[h])) for h in R.HALVES)
                res["repeat"][f"{tag}-{search}"] = dev
                if dev > REPEAT_TOL:
                    raise RuntimeError(f"repeat render moved by {dev:.4f} (log) on {tag}-{search}")
            run[tag] = summary(evals, search, held, dims, x, start)
            run[tag]["stages"] = stages
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


def run(shard, only=None):
    ps = parts()
    check_parts(ps)
    rr = Renderer()
    try:
        menu = rr.menu()
        for cls in IN_SCOPE:
            for amp in AMPS:
                assert START[cls][amp] in menu[amp], START[cls][amp]
        cache = {}
        todo = [c for c in cells() if only is None or f"{c[0]}:{c[1]}" in only]
        for slug, amp in todo[shard[0]::shard[1]]:
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
                     ("sw50rAmp", "sw50rMid"): 0.13},
           "ac20": {("ac20Amp", "ac20Volume"): 0.17, ("ac20Amp", "ac20Cut"): -0.21,
                    ("ac20Amp", "ac20Power"): 0.13}}
CONTROL_MIC = {"pr12": "leftMicType", "sw50r": "rightMicType", "ac20": "rightMicType"}
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


def control(cats="restart", budget=None, out_name="control", mismatch=False):
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
            for amp in AMPS:
                name = START[part["gain_class"]][amp]
                sel, x0 = menu[amp][name]
                dims = space(amp, x0)
                moves = {**PERTURB[amp], **PERTURB_ALL}
                target = perturbed(dims, x0, moves)
                mic = ("cabParameters", CONTROL_MIC[amp])
                target[mic] = str((int(x0[mic]) + 4) % 10)
                rr.render(di32, sel, x0)                                   # warm-up
                if mismatch:
                    # A recording no preset matches exactly: the target played with the
                    # part's own DI (not re-equalised), searched with the measure DI.
                    from learn.direc_check import to_lufs

                    raw = to_lufs(CR.mono(part["crop"] / "di.wav")).astype(np.float32)
                    rr.render(raw, sel, x0)
                    fake = rr.render(raw, sel, target)
                    reach = judge(fake, rr.render(di32, sel, target), di, 0)
                else:
                    fake = rr.render(di32, sel, target)
                    reach = {"A": 0.0, "B": 0.0}
                again = rr.render(di32, sel, target)
                rr.render(di32, sel, x0)
                again2 = rr.render(di32, sel, target)
                floor = judge(fake, again2, di, 0)
                evals = []

                def f(x):
                    d = judge(fake, rr.render(di32, sel, x), di, 0)
                    evals.append(d)
                    return d["A"]

                x, best, trace = (knob_search(dims, x0, f, budget or BUDGET["K_M"], SEED)[:3] if cats == "restart"
                                  else coord_search(dims, x0, f, budget or BUDGET["K_M"], SEED, cats=cats))
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
                    "renders": len(evals), "curve": curve, "at_limit": at_limit(dims, x, x0),
                    "target_settings": reach,
                    "vs_target_settings_held": (inc["B"] / reach["B"]) if reach["B"] else None,
                    "gap_closed_held": (evals[0]["B"] - inc["B"]) / (evals[0]["B"] - reach["B"])}
                print(slug, amp, round(inc["B"] / evals[0]["B"], 4), f"{cont_ok}/5", mic_ok,
                      "start", round(evals[0]["B"], 3), "found", round(inc["B"], 3), "target", round(reach["B"], 3),
                      flush=True)
    finally:
        rr.close()
    ok = control_passes(out)
    out["_pass"] = ok
    print("CONTROL PASSES" if ok else "CONTROL FAILS", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    out["_variant"] = {"cats": cats, "budget": budget or BUDGET["K_M"]}
    _atomic(OUT / f"{out_name}.json", out)


def control_passes(out):
    """Declared: every cell's held distance falls to ≤ 0.3 × the start's, and on at least 3 in
    4 cells at least 3 of the 5 moved settings land within 0.1 (0–1 scale) with the mic exact."""
    cs = [v for k, v in out.items() if not k.startswith("_")]
    return (all(c["ratio_held"] <= 0.3 for c in cs)
            and sum(c["settings_within_0.1"] >= 3 and c["mic_exact"] for c in cs) >= math.ceil(0.75 * len(cs)))


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
        return (f"the search found little from {what}: undecided (the search is a lower bound and "
                "can fall short of a reachable setting)")
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


# ---------------------------------------------------------------- cross-part check (amendment 4)

def _settings(path):
    return {tuple(k.rsplit("/", 1)): v for k, v in json.loads(path.read_text()).items()}


def cross(shard):
    """Every other part's best K_M and EQ settings (same amp, same direction) rendered through
    this part's measure DI and scored on both halves."""
    import numpy as np

    ps = parts()
    check_parts(ps)
    done = {(c["slug"], c["amp"]): c for c in
            (json.loads(p.read_text()) for p in sorted((OUT / "cells").glob("*/*/result.json")))}
    rr = Renderer()
    try:
        menu = rr.menu()
        todo = [(s, a) for s, a in cells() if (s, a) in done
                and any("skipped" not in done[(s, a)]["runs"][d] for d, _ in DIRECTIONS)]
        cache = {}
        for slug, amp in todo[shard[0]::shard[1]]:
            out_path = OUT / "cross" / slug / f"{amp}.json"
            if out_path.exists():
                continue
            part = ps[slug]
            if slug not in cache:
                cache.clear()
                cache[slug] = (measure_di(part), CR.mono(part["crop"] / "reference.wav"))
            di, ref = cache[slug]
            di32 = di.astype(np.float32)
            select = next(iter(menu[amp].values()))[0]
            rr.render(di32, select, next(iter(menu[amp].values()))[1])      # warm-up
            res = {}
            for search, held in DIRECTIONS:
                if "skipped" in done[(slug, amp)]["runs"][search]:
                    continue
                for tag in ("K_M", "EQ"):
                    for other, oamp in todo:
                        if oamp != amp or other == slug:
                            continue
                        f = OUT / "cells" / other / amp / f"{tag}-{search}.json"
                        if not f.exists():
                            continue
                        d = judge(ref, rr.render(di32, select, _settings(f)), di, part["judge_lag"])
                        res.setdefault(search, {}).setdefault(tag, {})[other] = d
            out_path.parent.mkdir(parents=True, exist_ok=True)
            _atomic(out_path, res)
            print(slug, amp, rr.count, flush=True)
    finally:
        rr.close()


def cross_rows(cell, cr):
    """Per cell: part-specific (own vs median of others) and generic (median of others vs M)
    held-half log ratios, averaged over the usable directions, for K_M and the EQ stage."""
    out = {}
    for search, held in DIRECTIONS:
        run = cell["runs"][search]
        if "skipped" in run or search not in cr:
            continue
        M_h = cell["menu"][run["M"]][held]
        for tag, name in (("K_M", "KM"), ("EQ", "EQ")):
            others = [v[held] for v in cr[search].get(tag, {}).values() if finite(v[held]) and v[held] > 0]
            own = run[tag]["held"]
            if not others or not finite(own, M_h):
                continue
            med = statistics.median(others)
            out.setdefault(f"{name}_part_specific", []).append(log_ratio(own, med))
            out.setdefault(f"{name}_generic", []).append(log_ratio(med, M_h))
    return {k: statistics.fmean(v) for k, v in out.items()}


def cross_report():
    rows = []
    for p in sorted((OUT / "cross").glob("*/*.json")):
        slug, amp = p.parent.name, p.stem
        cell = json.loads((OUT / "cells" / slug / amp / "result.json").read_text())
        r = cross_rows(cell, json.loads(p.read_text()))
        if r:
            rows.append((cell, r))
    out = {"cells": len(rows)}
    for group, keep in (("clean+crunch", IN_SCOPE), ("clean", ("clean",)), ("crunch", ("crunch",))):
        sel = [(c, r) for c, r in rows if c["gain_class"] in keep]
        if not sel:
            continue
        g = {k: CR.stats([(c["band"], r[k]) for c, r in sel if k in r]) for k in sel[0][1]}
        ps_, gen = g["KM_part_specific"], g["KM_generic"]
        g["reading"] = {
            "part_specific": ps_["band_weighted_mean"] <= -0.04 and ps_["bands_negative"] > ps_["bands"] / 2,
            "mostly_generic": ps_["band_weighted_mean"] > -0.04 and gen["band_weighted_mean"] <= -0.10}
        out[group] = g
    _atomic(OUT / "cross-result.json", out)
    for group, g in out.items():
        if not isinstance(g, dict):
            continue
        print(group, g["reading"])
        for k, s in g.items():
            if isinstance(s, dict) and "mean" in s:
                print(f"  {k:20s} mean {s['mean']:+.3f} band-w {s['band_weighted_mean']:+.3f} "
                      f"90% [{s['lo90']:+.3f}, {s['hi90']:+.3f}] bands− {s['bands_negative']}/{s['bands']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("control", "run", "report", "cross", "cross-report"))
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--cats", default="restart", choices=("once", "levels", "restart"))
    ap.add_argument("--budget", type=int)
    ap.add_argument("--name", default="control")
    ap.add_argument("--mismatch", action="store_true")
    ap.add_argument("--only", nargs="+", help="cells as part:amp (the smoke run)")
    a = ap.parse_args(argv)
    if a.step == "control":
        control(a.cats, a.budget, a.name, a.mismatch)
    elif a.step == "run":
        i, n = map(int, a.shard.split("/"))
        run((i, n), a.only)
    elif a.step == "cross":
        i, n = map(int, a.shard.split("/"))
        cross((i, n))
    elif a.step == "cross-report":
        cross_report()
    else:
        report()


if __name__ == "__main__":
    main()
