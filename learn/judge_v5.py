"""The combined judge (docs/pipeline-fix-plan.md; ledger `pipeline-fix`, key `phase_judge_v5`; for one listener,
checked on a fresh page). J5 = J0 + w_c x |C|: the judge as it is (J0, `analysis.aligned.aligned_distance`) plus a
carry-over part C for what time effects (reverb, delay, spring) add.

C, per window: on the judge's own middle-frame cells (2048 samples; the floored, level-matched log-mel levels it
scores, its scored bands), per band, the render's excess over the reference (X - R, dB) and the reference's decay
depth (its peak over the last 1.5 s minus its level now, dB), each with the reference's level partialled out (the
mean in 12 quantile bins of R taken away). The band's slope is excess on depth: positive where the render carries
energy on after the reference's notes fall. The bands' slopes are averaged with weights by the reference's mean
power in each. C is the antisymmetric mean: (slope(ref -> render) - slope(render -> ref)) / 2, so swapping the two
flips its sign; the judge uses |C|.

w_c is fitted in-sample on the judge-ear pages' 33 rated items (`judge_v4.screen_items`) by the highest
cross-group gamma over W_C_GRID, ties to the smaller, and frozen before any fresh render:

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    PYTHONPATH=. $MAIN -m learn.judge_v5 screen

The fresh page (the verdict): a verified clean chord DI through S clean on AC20 and S crunch on PR12, 15 items per
preset (14 kept renders each; the two anchors are offline shelves of S's render):

    $MAIN -m learn.judge_v5 plan                    # zero renders: the items and the jobs' settings
    $MAIN -u -m learn.judge_v5 render --shard k/3   # 28 kept renders, each in its own fresh primed process (56)
    $MAIN -m learn.judge_v5 measure                 # zero renders: J0 and J5 per item, the catches
    $MAIN -m learn.judge_v5 page                    # the blind page and its key (private/, outside the page)
    $MAIN -m learn.judge_v5 score --answers FILE    # the declared reading
"""

from __future__ import annotations

import argparse
import time

import hashlib
import json
import pathlib
import random

from learn import judge_ear as JE
from learn import judge_v4 as V

V5_KEY = "phase_judge_v5"
W_C_GRID = list(range(0, 41))
DEPTH_S = 1.5
LEVEL_BINS = 12
MID_FFT = 2048


# --- the carry-over part --------------------------------------------------------------------------------------------

def _partial(level, y, nb=LEVEL_BINS):
    """y with its mean in each of `nb` quantile bins of `level` taken away."""
    import numpy as np

    q = np.quantile(level, np.linspace(0, 1, nb + 1))
    idx = np.clip(np.searchsorted(q, level, side="right") - 1, 0, nb - 1)
    means = np.array([y[idx == i].mean() if np.any(idx == i) else 0.0 for i in range(nb)])
    return y - means[idx]


def depth(r, n):
    """Per frame, the band's peak over the last `n` frames (itself included) minus its level now (dB)."""
    import numpy as np
    from numpy.lib.stride_tricks import sliding_window_view

    padded = np.concatenate([np.full(n - 1, -np.inf), r])
    return sliding_window_view(padded, n).max(axis=1) - r


def slope(R, X, hop, sr=48000):
    """The power-weighted mean over bands of the slope of (X - R) on R's decay depth, R's level partialled out.
    R, X: frames x bands (dB)."""
    import numpy as np

    n = max(1, int(round(DEPTH_S * sr / hop)))
    s, w = [], []
    for k in range(R.shape[1]):
        r, x = R[:, k], X[:, k]
        ex = _partial(r, x - r)
        dd = _partial(r, depth(r, n))
        s.append(float(np.sum(ex * dd) / (np.sum(dd * dd) + 1e-9)))
        w.append(float(np.mean(10 ** (r / 10))))
    w = np.asarray(w)
    return float(np.sum(w * np.asarray(s)) / np.sum(w))


def mid(c):
    return next(f for f in c["frames"] if f["n_fft"] == MID_FFT)


def carry(c_fwd, c_bwd, sr=48000):
    """C from the cells of (ref -> render) and (render -> ref) on one window."""
    f, b = mid(c_fwd), mid(c_bwd)
    fw = slope(f["R"][:, f["bins"]], f["X"][:, f["bins"]], f["hop"], sr)
    bw = slope(b["R"][:, b["bins"]], b["X"][:, b["bins"]], b["hop"], sr)
    return (fw - bw) / 2


def window(ref, ren, di, *, latency=52, start_s, end_s):
    """{j0, carry} on one window, or None where the judge would refuse either direction."""
    cf = V.cells(ref, ren, di, render_latency=latency, start_s=start_s, end_s=end_s)
    cb = V.cells(ren, ref, di, render_latency=latency, start_s=start_s, end_s=end_s)
    if cf is None or cb is None:
        return None
    return {"j0": V.j0(cf), "carry": carry(cf, cb, cf["sr"])}


def j5(halves, w_c):
    """The mean over halves of J0 + w_c |C|; None (a refusal) where any half refused."""
    if any(h is None for h in halves):
        return None
    return sum(h["j0"] + w_c * abs(h["carry"]) for h in halves) / len(halves)


def fit(items, value):
    """W_C_GRID's w_c with the highest cross-group gamma, ties to the smaller."""
    best = None
    for w in W_C_GRID:
        g = V.cross_group_gamma(items, lambda it: value(it, w))
        if best is None or g > best[1]:
            best = (w, g)
    return best


# --- the in-sample screen ---------------------------------------------------------------------------------------------

def require_v5():
    e = JE.require()
    if V5_KEY not in e:
        raise SystemExit(f"ledger entry pipeline-fix has no {V5_KEY}: declare the combined judge first")
    return e


def screen_audio():
    import numpy as np

    d = JE.out_dir()
    plan = JE.load(d / "plan.json")
    audio = JE.anchor_audio()
    for p in plan["pairs"]:
        if p["pair"] not in audio:
            audio[p["pair"]] = (np.load(JE.render_path(JE.DATA, f"{p['cls']}-S")),
                                np.load(JE.render_path(JE.DATA, JE.job_of(p))))
    di = np.asarray(np.load(d / "di.npy"), np.float64)
    lo, hi = JE.trim()
    return audio, di[lo:hi]


def cmd_screen(args):
    require_v5()
    import numpy as np

    from learn import knob_ceiling as K

    audio, di = screen_audio()
    items = V.screen_items()
    for it in items:
        s, o = (np.asarray(a, np.float64) for a in audio[it["item"]])
        it["halves"] = {h: window(s, o, di, latency=K.P.LATENCY, start_s=a, end_s=b)
                        for h, (a, b) in K.R.HALVES.items()}
        hv = list(it["halves"].values())
        print(f"{it['item']:26s} ear {it['ear']:.1f}  j0 {np.mean([h['j0'] for h in hv]):.3f}  "
              f"C {np.mean([h['carry'] for h in hv]):+.3f}", flush=True)

    def val(it, w):
        return j5(list(it["halves"].values()), w)

    w_c, g = fit(items, val)
    d = JE.out_dir()
    rec = JE.load(d / "score-recheck.json")
    distinct = {(x["heard"], x["quiet"]) for x in rec["inversions"]}
    within = {(x["heard"], x["quiet"]) for x in rec["inversions"] if x["both_halves"] and x["same_preset"]}
    by = {it["item"]: it for it in items}
    out = {}
    for name, f in {"J0": lambda it: val(it, 0), "J5": lambda it: val(it, w_c)}.items():
        left = {k for k in distinct if f(by[k[0]]) < f(by[k[1]])}
        out[name] = {"gamma": V.cross_group_gamma(items, f), "inversions_left": len(left), "of": len(distinct),
                     "within_left": len(left & within), "within_of": len(within)}
        print(f"{name}: in-sample gamma {out[name]['gamma']:+.3f}  F45 inversions left {len(left)}/{len(distinct)}  "
              f"within-preset both-halves left {len(left & within)}/{len(within)}")
    print(f"w_c {w_c} (in-sample gamma {g:+.3f})")
    JE.save(d / "v5-screen.json", {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "w_c": w_c, "results": out,
                                   "items": items})


# --- the fresh page ---------------------------------------------------------------------------------------------------

DATA = JE.DATA
OUT = "learn/trusted-data/judge-v5"
PAGE = "listening/judge-v5"
PAGE_NAME = "judge-v5"
PAGE_SEED = 20261105
BOOT_SEED = 20261106
BOOT_N = 2000
DI_REL = "references/datasets/cambridge/TheTravellingBand_Quicksand_Full/16_ElecGtr1DI.wav"
DI_START_S = 125.0
PRESETS = (("clean", "ac20"), ("crunch", "pr12"))
TONE = {"ac20": ("ac20Amp", "ac20Cut"), "pr12": ("pr12Amp", "pr12Treble")}
DRIVE = (4.0, 10.0)
TONE_STEPS = (0.30, 0.70)
MIXES = (0.15, 0.40)
DECAY_LONG = "3"
DELAY_SHORT = "300"
SHELVES = (("high", 6), ("low", -6))
GROUPS = ("drive", "tone", "cab", "reverb", "reverb-decay", "delay", "delay-time", "combined", "anchor")
CATCH = "catch"
NOTE = "Please listen on headphones (not phone or laptop speakers), at a comfortable level."
FORBIDDEN = ("drive", "tone", "cab", "reverb", "delay", "combined", "anchor", "shelf", "clean", "crunch", "ac20",
             "pr12", "treble", "cut", "mic", "inputgain", "preset", "step")


def out_dir(root=DATA):
    return pathlib.Path(root) / OUT


def page_dir(root=DATA):
    return pathlib.Path(root) / PAGE


def key_path(root=DATA):
    return page_dir(root) / "private" / "page-key.json"


def render_path(job, root=DATA):
    return out_dir(root) / "renders" / f"{job}.npy"


def require_frozen():
    """Renders and the reading refuse unless the ledger declares phase_judge_v5 and freezes w_c and the code."""
    from learn import pipeline_fix as P

    e = require_v5()
    fz = P.require(V5_KEY + "_frozen")[V5_KEY + "_frozen"]
    scr = JE.load(JE.out_dir() / "v5-screen.json")
    if f"w_c {scr['w_c']}" not in fz:
        raise SystemExit("the ledger's frozen w_c differs from v5-screen.json")
    if JE.file_sha256(pathlib.Path(__file__)) not in fz:
        raise SystemExit("learn/judge_v5.py differs from the frozen code (its sha256 is not in the ledger)")
    return e, scr["w_c"]


def unit_move(d, stored, du):
    """`stored` moved by `du` in unit range, up or down where up would pass the top, clipped. -> stored string."""
    from learn import knob_ceiling as K

    u = d.to_unit(float(stored))
    v = u + du if u + du <= 1.0 else u - du
    return K.fmt(d.from_unit(min(max(v, 0.0), 1.0)))


def jobs_for(amp, S, defaults):
    """The kept renders of one preset: {job: settings}. S: {(module, key): stored}."""
    from learn import full_space as F
    from learn import knob_ceiling as K

    def drive(x, db):
        p = ("parameters", "inputGain")
        d = F.dims()[p]
        x[p] = K.fmt(min(max(float(S[p]) + db, d.lo), d.hi))

    def tone(x, du):
        x[TONE[amp]] = unit_move(F.dims()[TONE[amp]], S[TONE[amp]], du)

    def effect(x, g, mix):
        x.update({k: v for k, v in defaults.items() if k[0] == g})
        if g == "delay":
            x.update(JE.FREE_DELAY)
        x[JE.EFFECT_SWITCH[g]] = "true"
        x[(g, f"{g}Mix")] = K.fmt(mix)

    out = {"S": dict(S), "S2": dict(S)}
    for name, f in (("drive-small", lambda x: drive(x, DRIVE[0])), ("drive-large", lambda x: drive(x, DRIVE[1])),
                    ("tone-small", lambda x: tone(x, TONE_STEPS[0])), ("tone-large", lambda x: tone(x, TONE_STEPS[1])),
                    ("cab", lambda x: x.__setitem__(("cabParameters", "leftMicType"),
                                                    K.MICS[(K.MICS.index(str(S[("cabParameters", "leftMicType")]))
                                                            + 1) % len(K.MICS)])),
                    ("reverb-small", lambda x: effect(x, "reverb", MIXES[0])),
                    ("reverb-large", lambda x: effect(x, "reverb", MIXES[1])),
                    ("reverb-decay", lambda x: (effect(x, "reverb", MIXES[1]),
                                                x.__setitem__(("reverb", "reverbDecay"), DECAY_LONG))),
                    ("delay-small", lambda x: effect(x, "delay", MIXES[0])),
                    ("delay-large", lambda x: effect(x, "delay", MIXES[1])),
                    ("delay-time", lambda x: (effect(x, "delay", MIXES[1]),
                                              x.__setitem__(("delay", "delayTime"), DELAY_SHORT))),
                    ("combined", lambda x: (drive(x, DRIVE[0]), tone(x, TONE_STEPS[0]),
                                            effect(x, "reverb", MIXES[0])))):
        x = dict(S)
        f(x)
        out[name] = x
    return out


def items_for(cls):
    """The 15 items of one preset: [{item, cls, group, ref, alt, shelf}]; ref/alt are job names."""
    j = lambda n: f"{cls}-{n}"
    out = [{"item": j(n), "cls": cls, "group": g, "ref": j(r), "alt": j(n), "shelf": None} for n, g, r in (
        ("drive-small", "drive", "S"), ("drive-large", "drive", "S"), ("tone-small", "tone", "S"),
        ("tone-large", "tone", "S"), ("cab", "cab", "S"), ("reverb-small", "reverb", "S"),
        ("reverb-large", "reverb", "S"), ("reverb-decay", "reverb-decay", "reverb-large"),
        ("delay-small", "delay", "S"), ("delay-large", "delay", "S"), ("delay-time", "delay-time", "delay-large"),
        ("combined", "combined", "S"))]
    out += [{"item": j(f"anchor-{k}{db:+d}"), "cls": cls, "group": "anchor", "ref": j("S"), "alt": j("S"),
             "shelf": [k, db]} for k, db in SHELVES]
    out.append({"item": j(CATCH), "cls": cls, "group": CATCH, "ref": j("S"), "alt": j("S2"), "shelf": None})
    return out


def di_audio(root=DATA):
    """F44's DI rule on this DI: (start - 0.25 s)..(start + 10 s), mono, soxr VHQ to 48 kHz, one gain putting the
    10 s at -22.9 LUFS."""
    import numpy as np
    import pyloudnorm
    import soundfile as sf
    import soxr

    path = pathlib.Path(root) / DI_REL
    sr = sf.info(str(path)).samplerate
    x, _ = sf.read(str(path), start=int(round((DI_START_S - JE.TRIM_S) * sr)),
                   frames=int(round((JE.SEC_S + JE.TRIM_S) * sr)), dtype="float64", always_2d=True)
    x = x.mean(axis=1)
    if sr != JE.SR:
        x = soxr.resample(x, sr, JE.SR, quality="VHQ")
    n = int(round((JE.SEC_S + JE.TRIM_S) * JE.SR))
    x = np.pad(x, (0, max(0, n - len(x))))[:n]
    lufs = pyloudnorm.Meter(JE.SR).integrated_loudness(x[int(JE.TRIM_S * JE.SR):])
    return (x * 10 ** ((JE.DI_LUFS - lufs) / 20)).astype(np.float32)


def cmd_plan(args):
    require_v5()
    from learn import arm_a_mega53 as A
    from learn import full_space as F

    p = out_dir() / "plan.json"
    if p.exists() and not args.force:
        raise SystemExit(f"{p} exists (--force to rebuild it)")
    ms = A.L.menu_S()
    defaults = JE.plugin_defaults()
    presets, jobs, items = [], {}, []
    for cls, amp in PRESETS:
        sel, S = ms[amp][cls]
        presets.append({"cls": cls, "amp": amp, "select": sel, "S": JE.sdict(S)})
        for name, x in jobs_for(amp, S, defaults).items():
            changes = {f"{k[0]}/{k[1]}": [S.get(k), x[k]] for k in sorted(x) if S.get(k) != x[k]}
            if name not in ("S", "S2"):
                if not changes:
                    raise SystemExit(f"{cls}-{name}: equals S")
                snd = F.sounding(x, amp)
                mute = [k for k in changes if tuple(k.rsplit("/", 1)) in snd and not snd[tuple(k.rsplit("/", 1))]]
                if mute:
                    raise SystemExit(f"{cls}-{name}: changed controls that do not sound: {mute}")
            jobs[f"{cls}-{name}"] = {"cls": cls, "amp": amp, "select": sel, "settings": JE.sdict(x),
                                     "changes": changes}
        items += items_for(cls)
    plan = {"page": PAGE_NAME, "ledger_key": V5_KEY, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "presets": presets, "jobs": jobs, "items": items,
            "defaults": {"file": str(JE.DEFAULT_PRESET), "sha256": JE.file_sha256(JE.DEFAULT_PRESET),
                         "values": JE.sdict(defaults)},
            "di": {"path": str(DATA / DI_REL), "start_s": DI_START_S, "sec_s": JE.SEC_S, "trim_s": JE.TRIM_S,
                   "lufs": JE.DI_LUFS},
            "renders_declared": 2 * len(jobs)}
    JE.save(p, plan)
    for name, jb in jobs.items():
        print(f"{name:22s} " + ("; ".join(f"{k} {a} -> {b}" for k, (a, b) in jb["changes"].items()) or "(S)"))
    print(f"PLAN DONE: {len(items)} items, {len(jobs)} kept renders ({plan['renders_declared']} with priming) -> {p}")


def cmd_render(args):
    """One shard of the kept renders, each in its own fresh primed process (`AM.fresh_render`), mono, trimmed."""
    require_frozen()
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    plan = JE.load(out_dir() / "plan.json")
    if not plan:
        raise SystemExit("run `plan` first")
    ms = A.L.menu_S()
    for pr in plan["presets"]:
        if K.key(JE.tdict(pr["S"])) != K.key(ms[pr["amp"]][pr["cls"]][1]):
            raise SystemExit(f"{pr['amp']} {pr['cls']}: the plan's S differs from the stored copy")
    di32 = di_audio()
    di_rec = {"path": str(DATA / DI_REL), "file_sha256": JE.file_sha256(DATA / DI_REL),
              "audio_sha256": AM.audio_sha(di32), "samples": len(di32), "start_s": DI_START_S}
    dp = out_dir() / "di.json"
    old = JE.load(dp)
    if old and old["audio_sha256"] != di_rec["audio_sha256"]:
        raise SystemExit(f"{dp}: another DI was rendered before")
    if not old:
        JE.save_npy(out_dir() / "di.npy", di32)
        JE.save(dp, di_rec)
    k, n = args.shard
    mine = [(j, jb) for i, (j, jb) in enumerate(sorted(plan["jobs"].items())) if i % n == k]
    lo, hi = JE.trim()
    LO._wait_cap()
    rr = CB.new_renderer()
    try:
        menu = rr.menu()
    finally:
        rr.close()
    for cls, amp in PRESETS:
        if K.key(dict(menu[amp][K.START[cls][amp]][1])) != K.key(ms[amp][cls][1]):
            raise SystemExit(f"{amp} {cls}: the live S differs from the stored copy")
    renders = 0
    for job, jb in mine:
        jp = out_dir() / "renders" / f"{job}.json"
        st = JE.tdict(jb["settings"])
        rec = JE.load(jp)
        if rec:
            if rec["settings_key"] != K.key(st):
                raise SystemExit(f"{jp}: rendered from other settings")
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        t0 = time.time()
        y = AM.fresh_render(CB.new_renderer, di32, jb["select"], st, st)
        renders += 2
        y = (y.mean(axis=1) if y.ndim == 2 else y)[lo:hi]
        JE.save_npy(render_path(job), np.asarray(y, np.float64))
        JE.save(jp, {"job": job, "select": jb["select"], "settings_key": K.key(st),
                     "render_sha256": AM.audio_sha(y), "samples": len(y), "peak": float(np.max(np.abs(y))),
                     "secs": round(time.time() - t0, 1), "renders": 2, "di_audio_sha256": di_rec["audio_sha256"],
                     "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{job}: {time.time() - t0:.0f} s; renders so far {renders}", flush=True)
    print(f"JUDGE-V5 RENDER DONE {k}/{n}: {renders} renders")


def item_audio(it, y):
    """(reference, other) for an item from the renders {job: array}; an anchor shelves S's render offline."""
    ref = y[it["ref"]]
    if it["shelf"]:
        return ref, JE.shelve(ref, it["shelf"][0], it["shelf"][1])
    return ref, y[it["alt"]]


def cmd_measure(args):
    """J0 and J5 per item on both halves (zero renders) -> measure.json; catches must score 0 or be bit-identical."""
    _, w_c = require_frozen()
    import numpy as np

    from learn import knob_ceiling as K

    plan = JE.load(out_dir() / "plan.json")
    recs = {j: JE.load(out_dir() / "renders" / f"{j}.json") for j in plan["jobs"]}
    missing = [j for j, r in recs.items() if not r]
    if missing:
        raise SystemExit(f"renders missing: {missing}")
    di = np.asarray(np.load(out_dir() / "di.npy"), np.float64)
    lo, hi = JE.trim()
    di = di[lo:hi]
    y = {j: np.load(render_path(j)) for j in recs}
    res, bad = {}, []
    for it in plan["items"]:
        a, b = item_audio(it, y)
        hv = {h: window(a, b, di, latency=K.P.LATENCY, start_s=s0, end_s=s1) for h, (s0, s1) in K.R.HALVES.items()}
        if any(v is None for v in hv.values()):
            raise SystemExit(f"{it['item']}: the judge refuses a half")
        identical = not it["shelf"] and recs[it["ref"]]["render_sha256"] == recs[it["alt"]]["render_sha256"]
        res[it["item"]] = {**it, "halves": hv, "j0": j5(list(hv.values()), 0), "j5": j5(list(hv.values()), w_c),
                           "identical": identical}
        if it["group"] == CATCH and not (identical or all(v["j0"] == 0 for v in hv.values())):
            bad.append(it["item"])
    out = {"page": PAGE_NAME, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "w_c": w_c, "items": res,
           "render_sha256": {j: r["render_sha256"] for j, r in recs.items()},
           "renders": sum(r["renders"] for r in recs.values())}
    JE.save(out_dir() / ("measure-refused.json" if bad else "measure.json"), out)
    if bad:
        raise SystemExit(f"catches not 0 and not bit-identical: {bad}")
    for it in plan["items"]:
        r = res[it["item"]]
        print(f"{it['item']:26s} J0 {r['j0']:.3f}  C {np.mean([h['carry'] for h in r['halves'].values()]):+.3f}  "
              f"J5 {r['j5']:.3f}")
    print(f"MEASURE DONE: {len(res)} items; {out['renders']} renders")


def page_order(ids, seed=PAGE_SEED):
    rng = random.Random(seed)
    order = sorted(ids)
    rng.shuffle(order)
    return [{"page_id": f"p{n + 1:02d}", "item": i, "a": rng.choice(("ref", "alt"))} for n, i in enumerate(order)]


def cmd_page(args):
    require_frozen()
    import numpy as np

    from learn import audibility_measure as AM

    plan = JE.load(out_dir() / "plan.json")
    meas = JE.load(out_dir() / "measure.json")
    if not meas:
        raise SystemExit("run `measure` first")
    kp = key_path()
    if kp.exists() and not args.force:
        raise SystemExit(f"{kp} exists: a rebuild hides the listener's stored answers (--force)")
    by = {it["item"]: it for it in plan["items"]}
    y = {}
    for j in plan["jobs"]:
        y[j] = np.load(render_path(j))
        if AM.audio_sha(y[j]) != meas["render_sha256"][j]:
            raise SystemExit(f"{j}: its render is not the one `measure` judged")
    order = page_order(list(by))
    clips, key_items = {}, []
    for o in order:
        it = by[o["item"]]
        ref, alt = item_audio(it, y)
        a, b = (ref, alt) if o["a"] == "ref" else (alt, ref)
        clips[o["page_id"] + "-1"], clips[o["page_id"] + "-2"] = AM.pair_clips(a, b, out_dir() / "page-cache")
        key_items.append({**o, **it})
    build = hashlib.sha256((json.dumps(key_items, sort_keys=True) + str(PAGE_SEED)).encode()).hexdigest()[:12]
    page = JE.page_html([o["page_id"] for o in order], clips, build, NOTE)
    bad = JE.leaks(page, FORBIDDEN)
    if bad:
        raise SystemExit(f"the page names {bad}: not blind")
    JE.save(kp, {"page": PAGE_NAME, "build": build, "seed": PAGE_SEED, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "clip_rule": "audibility_measure.pair_clips: each clip -23 LUFS on its own, common true-peak cut, "
                              "10-ms fades, AAC 256 kbps",
                 "render_sha256": meas["render_sha256"], "items": key_items})
    page_dir().mkdir(parents=True, exist_ok=True)
    out = page_dir() / "index.html"
    out.write_text(page)
    print(f"PAGE DONE: {len(order)} items, {out.stat().st_size / 1e6:.1f} MB -> {out}; build {build}; key {kp}")


def boot_gamma_diff(items, f_new, f_old, n=BOOT_N, seed=BOOT_SEED):
    """gamma(f_new) - gamma(f_old) and its 90% percentile interval from resampling the group x preset clusters."""
    import numpy as np

    cl = sorted({(it["group"], it["cls"]) for it in items})
    by = {c: [it for it in items if (it["group"], it["cls"]) == c] for c in cl}
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n):
        pick = [cl[i] for i in rng.integers(0, len(cl), len(cl))]
        its = [it for c in pick for it in by[c]]
        d = V.cross_group_gamma(its, f_new) - V.cross_group_gamma(its, f_old)
        if d == d:
            diffs.append(d)
    point = V.cross_group_gamma(items, f_new) - V.cross_group_gamma(items, f_old)
    lo, hi = np.percentile(diffs, [5, 95])
    return point, float(lo), float(hi), len(cl), len(diffs)


def inversions(items, f):
    """F44's rule: (heard clearly/very, quiet same/barely) from different groups with the heard one strictly below."""
    loud = [it for it in items if it["ear"] >= 2]
    quiet = [it for it in items if it["ear"] <= 1]
    return [(p["item"], q["item"]) for p in loud for q in quiet if p["group"] != q["group"] and f(p) < f(q)]


def cmd_score(args):
    require_frozen()
    key = JE.load(key_path())
    meas = JE.load(out_dir() / "measure.json")
    if not key or not meas:
        raise SystemExit("run `page` first")
    ans = JE.parse_answers(pathlib.Path(args.answers).read_text(), key["build"])
    rows = []
    for it in key["items"]:
        a = ans.get(it["page_id"], {})
        m = meas["items"][it["item"]]
        rows.append({"item": it["item"], "cls": it["cls"], "group": it["group"], "rating": a.get("rating"),
                     "conf": a.get("conf"), "j0": m["j0"], "j5": m["j5"],
                     "ear": V.RATING[a["rating"]] if a.get("rating") else None})
    for r in rows:
        if r["group"] == CATCH and r["ear"] is not None and r["ear"] >= 2:
            print(f"CAVEAT: the catch {r['item']} (identical audio) was rated {r['rating']}")
    items = [r for r in rows if r["group"] != CATCH and r["ear"] is not None]
    J0, J5 = (lambda it: it["j0"]), (lambda it: it["j5"])
    point, lo, hi, ncl, nb = boot_gamma_diff(items, J5, J0)
    eff = [r for r in items if r["group"] in ("reverb", "reverb-decay", "delay", "delay-time")]
    td = [r for r in items if r["group"] in ("drive", "tone")]
    res = {"gamma": {"J0": V.cross_group_gamma(items, J0), "J5": V.cross_group_gamma(items, J5)},
           "diff": point, "interval90": [lo, hi], "clusters": ncl, "resamples_kept": nb,
           "verdict": "adopt" if lo > 0 else "undecided",
           "gamma_effects": {"J0": V.cross_group_gamma(eff, J0), "J5": V.cross_group_gamma(eff, J5)},
           "gamma_tone_drive": {"J0": V.cross_group_gamma(td, J0), "J5": V.cross_group_gamma(td, J5)},
           "inversions": {"J0": inversions(items, J0), "J5": inversions(items, J5)}}
    fx = {"reverb", "reverb-decay", "delay", "delay-time"}
    by = {r["item"]: r for r in items}
    res["tonal_trigger"] = [x for x in res["inversions"]["J5"]
                            if by[x[1]]["group"] in ("tone", "drive") and by[x[0]]["group"] in fx]
    JE.save(out_dir() / "score.json", {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "build": key["build"],
                                       "w_c": meas["w_c"], "rows": rows, "result": res})
    for r in sorted(rows, key=lambda r: (r["group"], r["cls"], r["item"])):
        print(f"{r['item']:26s} J0 {r['j0']:.3f}  J5 {r['j5']:.3f}  ear {r['rating']}{', ' + r['conf'] if r['conf'] else ''}")
    print(f"gamma J0 {res['gamma']['J0']:+.3f}  J5 {res['gamma']['J5']:+.3f}  diff {point:+.3f} "
          f"[{lo:+.3f}, {hi:+.3f}] ({ncl} clusters) -> {res['verdict']}")
    print(f"inversions J0 {len(res['inversions']['J0'])}, J5 {len(res['inversions']['J5'])}; "
          f"tonal-revision trigger: {len(res['tonal_trigger'])}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="judge_v5", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["screen", "plan", "render", "measure", "page", "score"])
    ap.add_argument("--shard", type=JE.parse_shard, default=(0, 1))
    ap.add_argument("--answers")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    {"screen": cmd_screen, "plan": cmd_plan, "render": cmd_render, "measure": cmd_measure, "page": cmd_page,
     "score": cmd_score}[args.cmd](args)

if __name__ == "__main__":
    main()
