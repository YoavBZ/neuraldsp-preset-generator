"""The short-time magnitude dose probe (`docs/dose-probe-plan.md`): on top of the leak-free EQ
(`cprime_eq`, the anchor), restore 25%, 50% or 100% of the true offset-removed short-time
magnitude in 2–8 kHz, the full-band true magnitude (one resynthesis, or Griffin–Lim), and a
time-shifted control, with the long-term balance held at the anchor's. An oracle: renders only, a
diagnostic. Development only; estimates with 90% band-clustered intervals, no pass/fail bars. The
cells, guards, comparator and scoring are the rebuild-gap study's stage TR; each render is scored as
it renders (both masks), so no probe audio and only the S FLACs are stored.

    .venv/bin/python -m learn.rebuild_dose build                     # zero renders: probes, checks, hashes
    .venv/bin/python -m learn.rebuild_dose slots                     # free render slots (the runner's count)
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.rebuild_tone render-dose --probe dose100 --shard i/3
    .venv/bin/python -m learn.rebuild_dose report                    # contrasts, readings, the R2 list
    .venv/bin/python -m learn.rebuild_dose clear --probe P --cell SLUG AMP   # amendment 2: clear a stop

The render entry is `learn.rebuild_tone render-dose`, so every job's `local_objective.RENDERS`
(whose `-m learn.rebuild_tone render` pattern predates this step) counts these processes.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import pathlib
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import knob_ceiling as K  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import rebuild_gap as G  # noqa: E402
from learn import rebuild_tone_train as RT  # noqa: E402

OUT = K.HOME / "learn/rebuild-dose"
TONE = K.HOME / "learn/rebuild-tone"
ANCHOR = "arm_cprime_eq"                      # the rebuild-tone step's stored arm: the anchor
ANCHOR_R2 = "anchor_eq"                       # the anchor rendered here, on the R2 cells only
DOSES = {"dose25": 0.25, "dose50": 0.5, "dose100": 1.0}
# R1's render order (amendment 1, item 5: the control second)
PROBES = ("dose100", "shift100", "full_gl", "full100", "dose50", "dose25")
EXTEND_ORDER = ("dose100", "full100", "full_gl", "dose50", "dose25")
COMPARATOR_ARM = "arm_rank"                   # `rebuild_gap.comparator` scores C′'s 1b rebuild under this name
EDGE = 2                                      # STFT frames at each end left untouched (amendment 1, item 2)
HOLD_EQ_ITERS = 2
GL_ITERS = G.MAG_ITERS                        # 8, stage R's `mag`
BOUND_DB = 12.0                               # the HF research's bound, measured at zero renders only
LUFS, LUFS_TOL, LAG_TOL = -22.9, 0.05, 3
LSD_TOL, LSD_X_MAX, PEAK_TOL_DB, ID_TOL, EST_TOL = 0.25, 1.0, 6.0, 1e-9, 1e-6
CAP = 3
YIELD = 75                                    # a render process's exit code when the machine is full
NEAR_SHARE = 0.25                             # "near 0": within a quarter of the remainder (declared)
SHAPE_BAND = 0.15                             # the dose shape: S50 within r50 ± 0.15 is proportional
# Amendment 2: the Σ-order repeat check, on the cell that stopped, with dose100 only: these Σ indices
# are rendered a second time right after their scored render
REPEAT_CELL = ("cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1", "pr12")
REPEAT_PROBE = "dose100"
REPEAT_IDX = tuple(range(1, 48, 5))           # 1, 6, …, 46


# --- the probes (pure) ---------------------------------------------------------------------------------

def truth_on(x, t, judge_lag):
    """The measure DI t on the rebuild x's timeline (`rebuild_gap.align`: r(n) ≈ t(n − k), so t is
    delayed by k). -> (t shifted, k, |c|, coherence 80 Hz–2 kHz), all of length min(len(x), len(t))."""
    import numpy as np

    n = min(len(x), len(t))
    x, t = np.asarray(x[:n], np.float64), np.asarray(t[:n], np.float64)
    _, lag, _, absc = G.align(x, t, judge_lag)
    tx = G.shift(t, lag)
    return tx, lag, absc, G.coherence(x, tx, *G.ALIGN_BAND)


def interior(nframes, edge=EDGE):
    import numpy as np

    m = np.zeros(nframes, bool)
    m[edge:max(edge, nframes - edge)] = True
    return m


def gain_field(X, T, f, edge=EDGE):
    """The short-time gain field (dB) moving X's magnitude to T's: inside the mask (E_st's mask of T
    and of X, interior frames), B − A minus each bin's mean over its masked frames, weighted to 2–8
    kHz with ⅓-octave raised-cosine edges; 0 elsewhere. -> (g, mask)."""
    import numpy as np

    A = 20 * np.log10(np.abs(X) + 1e-9)
    B = 20 * np.log10(np.abs(T) + 1e-9)
    ones = np.ones(len(f))
    m = (RT.st_mask_np(B, ones) > 0) & (RT.st_mask_np(A, ones) > 0) & interior(X.shape[1], edge)[None]
    d = np.where(m, B - A, 0.0)
    off = d.sum(1) / np.maximum(m.sum(1), 1)
    g = np.where(m, B - A - off[:, None], 0.0) * RT.st_weights(f)[:, None]
    return g, m


def hold(Y, X, inner):
    """Each bin's power over the interior frames scaled back to X's there; the edge frames are X."""
    import numpy as np

    c = np.sqrt((np.abs(X[:, inner]) ** 2).sum(1) / np.maximum((np.abs(Y[:, inner]) ** 2).sum(1), 1e-30))
    return np.where(inner[None], Y * c[:, None], X)


def finish(Y, X, inner, sx, n, iters=HOLD_EQ_ITERS):
    """The long-term hold (amendment 1): the STFT hold, one resynthesis, `eq_to` back to x's smoothed
    long-term spectrum (twice), −22.9 LUFS."""
    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to, to_lufs

    y = G.istft(hold(Y, X, inner), n)
    for _ in range(iters):
        y = eq_to(y, sx - smoothed_spectrum(y))
    return to_lufs(y, LUFS)


def build_probes(x, tx, names=None):
    """Every probe from the anchor x and the truth on its timeline tx (same length). -> ({name:
    array}, info). `anchor_eq` (R2's anchor) is x itself; `dose0` is the pipeline at dose 0 (a
    check: it must return x)."""
    import numpy as np

    from learn.di_robustness import smoothed_spectrum

    names = list(names) if names is not None else [*PROBES, "dose0"]
    n = len(x)
    x = np.asarray(x, np.float64)
    f, _, X = G.stft(x)
    _, _, T = G.stft(np.asarray(tx, np.float64))
    inner = interior(X.shape[1])
    sx = smoothed_spectrum(x)
    g, m = gain_field(X, T, f)
    out = {}
    for name in names:
        if name == ANCHOR_R2:
            out[name] = x.copy()
        elif name == "dose0":
            out[name] = finish(X, X, inner, sx, n)
        elif name in DOSES:
            out[name] = finish(X * 10 ** (DOSES[name] * g / 20), X, inner, sx, n)
        elif name == "shift100":
            out[name] = finish(X * 10 ** (np.roll(g, X.shape[1] // 2, axis=1) / 20), X, inner, sx, n)
        elif name == "full100":
            out[name] = finish(np.where(inner[None], np.abs(T) * np.exp(1j * np.angle(X)), X), X, inner, sx, n)
        elif name == "full_gl":
            Tm = np.where(inner[None], np.abs(T), np.abs(X))
            xg = G.consistent_mag(Tm, np.angle(X), n, GL_ITERS)
            _, _, Xg = G.stft(xg)
            out[name] = finish(np.where(inner[None], Xg[:, :X.shape[1]], X), X, inner, sx, n)
        elif name == "bound12":
            out[name] = finish(X * 10 ** (np.clip(g, -BOUND_DB, BOUND_DB) / 20), X, inner, sx, n)
        else:
            raise ValueError(name)
    w = RT.st_weights(f)[:, None] > 0
    gm = np.abs(g[m & w])
    info = {"gain_gt12_share": float(np.mean(gm > 12)) if gm.size else None,
            "gain_gt30_share": float(np.mean(gm > 30)) if gm.size else None,
            "gain_p95_db": float(np.percentile(gm, 95)) if gm.size else None,
            "gain_max_db": float(gm.max()) if gm.size else None, "frames": int(X.shape[1])}
    return out, info


def probe_hash(y):
    import numpy as np

    return hashlib.sha256(np.ascontiguousarray(np.asarray(y, np.float64)).tobytes()).hexdigest()


def peak_over_db(y, anchor, truth):
    """The probe's peak against the larger of the anchor's and the truth's (dB)."""
    import numpy as np

    ref = max(float(np.abs(anchor).max()), float(np.abs(truth).max()))
    return float(20 * np.log10(float(np.abs(y).max()) / ref)) if ref > 0 else math.inf


def crest_db(y):
    import numpy as np

    rms = float(np.sqrt(np.mean(np.asarray(y, np.float64) ** 2)))
    return float(20 * np.log10(float(np.abs(y).max()) / rms)) if rms > 0 else None


def probe_problems(name, m, anchor_m):
    """The build checks of one probe on one part (amendment 1). m and anchor_m: realised metrics
    {len, finite, gcc, lufs, lsd, lsd_vs_anchor, peak_over_db}. -> [problem]."""
    out = []
    if m["len"] != anchor_m["len"] or not m["finite"]:
        out.append(f"{name}: length {m['len']} (anchor {anchor_m['len']}) or non-finite")
    if abs(m["gcc"]) > LAG_TOL:
        out.append(f"{name}: GCC against the anchor {m['gcc']} samples")
    if not math.isfinite(m["lufs"]) or abs(m["lufs"] - LUFS) > LUFS_TOL:
        out.append(f"{name}: loudness {m['lufs']} LUFS")
    if abs(m["lsd"] - anchor_m["lsd"]) > LSD_TOL:
        out.append(f"{name}: LSD to the truth {m['lsd']:.3f} against the anchor's {anchor_m['lsd']:.3f}")
    if m["lsd_vs_anchor"] > LSD_X_MAX:
        out.append(f"{name}: LSD to the anchor {m['lsd_vs_anchor']:.3f} dB")
    if m["peak_over_db"] > PEAK_TOL_DB:
        out.append(f"{name}: peak {m['peak_over_db']:.1f} dB above max(anchor, truth)")
    return out


def alignment_problems(absc, coh):
    out = []
    if absc < G.MIN_ABS_C or coh < G.MIN_COH:
        out.append(f"alignment: |c| {absc:.3f} / coherence {coh:.3f} under {G.MIN_ABS_C} / {G.MIN_COH}")
    return out


# --- data access -----------------------------------------------------------------------------------------

def parts():
    return {s: p for s, p in K.parts().items() if s not in LO.EXCLUDED}


def anchor_di(slug):
    import numpy as np

    return np.load(TONE / "arms" / ANCHOR / f"{slug}.npy").astype(np.float64)


def inputs(slug, part=None):
    """(anchor x, truth t, truth on x's timeline, lag, |c|, coherence), x and t cut to one length."""
    import numpy as np

    part = part or K.parts()[slug]
    x = anchor_di(slug)
    t = np.asarray(K.measure_di(part), np.float64)
    tx, lag, absc, coh = truth_on(x, t, part["judge_lag"])
    n = len(tx)
    return x[:n], t[:n], tx, lag, absc, coh


def build_record():
    p = OUT / "arms" / "build.json"
    return json.loads(p.read_text()) if p.exists() else None


def build_ok():
    p = OUT / "arms" / "check.json"
    return p.exists() and bool(json.loads(p.read_text()).get("ok"))


def probe_for(slug, name, rec=None):
    """A probe rebuilt for rendering, refused unless its hash is the build's."""
    rec = rec or build_record()
    x, _, tx, *_ = inputs(slug)
    y = build_probes(x, tx, [name])[0][name]
    want = rec["parts"][slug]["hash"][name]
    got = probe_hash(y)
    if got != want:
        raise RuntimeError(f"{name} {slug}: hash {got[:12]} differs from the build's {want[:12]}")
    return y, x


# --- build (zero renders) ----------------------------------------------------------------------------------

def metrics(y, x, t, judge_lag):
    import numpy as np

    from learn import rank_margin as RM

    ya, *_ = G.align(y, t, judge_lag)
    n = min(len(ya), len(t))
    return {"len": len(y), "finite": bool(np.all(np.isfinite(y))), "gcc": int(RM.gcc_lag(y, x)), "lufs": LO.lufs(y),
            "est": RT.est(ya[:n], t[:n]), "lsd": G.lsd_db(ya[:n], t[:n]), "lsd_vs_anchor": G.lsd_db(y, x),
            "coh_1_3k": G.coherence(ya[:n], t[:n], 1000, 3000), "coh_3_8k": G.coherence(ya[:n], t[:n], 3000, 8000),
            "peak": float(np.abs(y).max()), "crest_db": crest_db(y)}


def cmd_build():
    """Every probe on every part: the checks, the realised metrics and the hashes (zero renders)."""
    import numpy as np

    diag = json.loads((TONE / "diag.json").read_text())["per_part"][ANCHOR]
    ps = parts()
    rec, bad = {"parts": {}}, {}
    for slug in sorted(ps):
        part = ps[slug]
        x, t, tx, lag, absc, coh = inputs(slug, part)
        probes, info = build_probes(x, tx, [*PROBES, "dose0", "bound12", ANCHOR_R2])
        am = metrics(x, x, t, part["judge_lag"])
        am["peak_over_db"] = 0.0
        row = {"lag": lag, "abs_c": absc, "coh_80_2k": coh, "gain": info, "anchor": am, "probes": {}, "hash": {}}
        probs = alignment_problems(absc, coh)
        if abs(am["est"] - diag[slug]["est"]) > EST_TOL:
            probs.append(f"anchor E_st {am['est']:.6f} differs from the rebuild-tone diagnostic's {diag[slug]['est']:.6f}")
        d0 = float(np.abs(probes["dose0"] - x).max())
        row["dose0_max_abs_diff"] = d0
        if d0 > ID_TOL:
            probs.append(f"dose 0 differs from the anchor by {d0:.2e}")
        for name, y in probes.items():
            if name in ("dose0", ANCHOR_R2):
                row["hash"][name] = probe_hash(y)
                continue
            m = metrics(y, x, t, part["judge_lag"])
            m["peak_over_db"] = peak_over_db(y, x, t)
            m["cut"] = 1 - m["est"] / am["est"] if am["est"] else None
            row["probes"][name] = m
            row["hash"][name] = probe_hash(y)
            if name != "bound12":
                probs += probe_problems(name, m, am)
        row["problems"] = probs
        rec["parts"][slug] = row
        if probs:
            bad[slug] = probs
        print(slug, {k: round(v["est"], 2) for k, v in row["probes"].items()}, "problems:", probs, flush=True)
    rec["medians"] = medians(rec)
    (OUT / "arms").mkdir(parents=True, exist_ok=True)
    K._atomic(OUT / "arms" / "build.json", rec)
    K._atomic(OUT / "arms" / "check.json", {"ok": not bad, "problems": bad})
    print(json.dumps(rec["medians"], indent=1))
    if bad:
        raise SystemExit(f"build checks failed: {bad}")
    print("BUILD DONE", flush=True)


def medians(rec):
    import numpy as np

    rows = rec["parts"].values()
    names = sorted({k for r in rows for k in r["probes"]})
    out = {"anchor": {"est": float(np.median([r["anchor"]["est"] for r in rows])),
                      "lsd": float(np.median([r["anchor"]["lsd"] for r in rows]))}}
    for nm in names:
        out[nm] = {k: float(np.median([r["probes"][nm][k] for r in rows])) for k in ("est", "cut", "lsd", "lsd_vs_anchor",
                                                                                         "peak_over_db", "crest_db")}
        out[nm]["cut_range"] = [float(min(r["probes"][nm]["cut"] for r in rows)), float(max(r["probes"][nm]["cut"] for r in rows))]
    return out


def cut_ratios(med):
    """r25, r50: the doses' median realised cuts over dose100's (the dose shape's reference)."""
    c = {k: med[k]["cut"] for k in DOSES if k in med}
    if not c.get("dose100"):
        return {}
    return {"dose25": c.get("dose25", 0) / c["dose100"], "dose50": c.get("dose50", 0) / c["dose100"]}


# --- the machine ------------------------------------------------------------------------------------------

DOSE_RENDER = r"-m learn\.rebuild_tone render-dose\b"


def busy(ps, me, own=(), cap=CAP):
    """The machine is full for this render process (pid `me`): `cap` or more other render processes,
    counting this step's own lanes only if their PID is lower (so lanes that start together don't all
    yield), or a separation running."""
    import re

    others = [(p, c) for p, c in ps if p not in own and p != me
              and (G._matches(c, G.FOREIGN_RENDERS) or G._matches(c, G.MY_RENDERS))]
    lower = sum(1 for p, c in others if re.search(DOSE_RENDER, c) and p < me)
    foreign = sum(1 for p, c in others if not re.search(DOSE_RENDER, c))
    return foreign + lower >= cap or bool(LO.separating(ps, own))


def cmd_slots():
    """The runner's count before launching a lane (this command matches no render pattern)."""
    ps = G._ps()
    n = G.render_count(ps, G._own())
    sep = LO.separating(ps, G._own())
    print(f"renders {n} separations {len(sep)} free {'yes' if n < CAP and not sep else 'no'}", flush=True)


@contextlib.contextmanager
def bound(out=None, arms=(*PROBES, ANCHOR_R2)):
    """The rebuild-gap machinery on this step's folder (or `out`), every probe an arm (1b's matched
    scoring)."""
    old = G.OUT, G.ARMS
    G.OUT, G.ARMS = pathlib.Path(out or OUT), tuple(dict.fromkeys((*arms, COMPARATOR_ARM, ANCHOR)))
    try:
        yield
    finally:
        G.OUT, G.ARMS = old


def stop_paths():
    return (OUT / "STOP.json", LO.stop_path())


def check_stop():
    for p in stop_paths():
        if p.exists():
            raise SystemExit(f"stopped: {p}: {p.read_text()}")


def breakage(rec_path, rec, why):
    K._atomic(rec_path, {**rec, "status": "check_failed", "why": why})
    K._atomic(OUT / "STOP.json", {"why": why, "slug": rec.get("slug"), "amp": rec.get("amp"), "probe": rec.get("probe"),
                                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    raise SystemExit(f"{why}: every shard stops; investigate, then delete {OUT / 'STOP.json'}")


def score_render(y, name, sig, aligned):
    """{"decl": 1b's matched score (reference.wav, −52, own mask, record fallback), "xmask": the same
    with the anchor as the activity mask}. sig: {"di", "anchor", "reference"}."""
    from learn.rebuilt_judge import _ACTIVITY

    with bound():
        out = {"decl": G.score_one(y, name, {"di": sig["di"], "reference": sig["reference"]}, None, aligned)["decl"]}
    rec, row = sig["reference"], {}
    for h, (a, b) in K.R.HALVES.items():
        d, why = aligned(rec, y, sig["anchor"], G.OBJ_LAG, a, b)
        if d is None and any(w in (why or "") for w in _ACTIVITY):
            d, _ = aligned(rec, y, LO.in_di_time(rec, G.OBJ_LAG), G.OBJ_LAG, a, b)
        row[h] = math.inf if d is None else d
    out["xmask"] = row
    return out


def stored_anchor(slug, amp, i):
    """The rebuild-tone step's stored anchor score at index i, or None where the anchor was never
    rendered (the R2 cells)."""
    p = TONE / "scores" / ANCHOR / slug / f"{amp}.json"
    return json.loads(p.read_text())["scores"][i]["decl"] if p.exists() else None


def comparators(rr, sel, slug, amp, points, aligned, x, ref):
    """Per cell, before its first probe render: C′'s 1b rebuild at S against 1b's stored score (stage
    TR's), and the anchor at S against the rebuild-tone step's stored score (warm-up and S each)."""
    with bound():
        c1 = G.comparator(rr, sel, slug, amp, points, aligned, arm=True)
    i = c1["index"]
    st = stored_anchor(slug, amp, i)
    if st is None:                                   # an R2 cell: anchor_eq's own S checks cover it
        return {"index": i, "renders": 2, "cprime_1b": c1, "anchor": None, "max_dev": c1["max_dev"]}
    x32 = x.astype("float32")
    rr.render(x32, sel, points[i]["x"])
    y = rr.render(x32, sel, points[i]["x"])
    with bound():
        s = G.score_one(y, ANCHOR, {"di": x, "reference": ref}, None, aligned)["decl"]
    devs = {h: LO.deviation(s[h], st[h]) for h in G.HALVES}
    return {"index": i, "renders": 4, "cprime_1b": c1, "anchor": {"devs": devs, "max_dev": max(devs.values())},
            "max_dev": max(c1["max_dev"], max(devs.values()))}


def _paths(name, slug, amp):
    return (OUT / "renders" / name / slug / f"{amp}.json", OUT / "scores" / name / slug / f"{amp}.json",
            OUT / "renders" / name / slug / amp / "S.flac")


def done(name, slug, amp):
    p = _paths(name, slug, amp)[0]
    return p.exists() and json.loads(p.read_text()).get("status") == "done"


def stage_cells(stage):
    return G.r1_cells() if stage == "r1" else G.r2_cells()


def cmd_render(shard, probe, stage="r1"):
    """One probe on this shard's cells: per (cell, probe) the yield check, the guards, the comparators
    (once per cell), the probe rebuilt and hash-checked, a warm-up and Σ's 48 settings, each scored as
    it renders (both masks); S against the warm-up and the S FLAC against float. Exit 75 on a full
    machine (the cell is redone later)."""
    import numpy as np

    from learn import arm_a_levers as L
    from learn import confirm_run as CR

    if probe not in (*PROBES, ANCHOR_R2):
        raise SystemExit(f"unknown probe {probe}")
    if not build_ok():
        raise SystemExit("the build checks have not passed")
    rec_b = build_record()
    meta, sig = LO.load_sigma()
    check_stop()
    cells = L._shard(stage_cells(stage), shard)
    ms, rr, guard, aligned = L.menu_S(), None, L.SwapGuard(), LO.judge_fns()
    own = G._own()
    ps = K.parts()
    try:
        for slug, amp in cells:
            rec_path, score_path, flac = _paths(probe, slug, amp)
            prev = json.loads(rec_path.read_text()) if rec_path.exists() else {}
            if prev.get("status") == "done":
                continue
            if prev.get("status") == "check_failed":
                raise SystemExit(f"{probe} {slug} {amp} failed a check: investigate before rendering it again")
            check_stop()
            guard.check()
            if busy(G._ps(), os.getpid(), own):
                print("YIELD", probe, slug, amp, flush=True)
                raise SystemExit(YIELD)
            if LO.disk_free_gb() - (len(sig[(slug, amp)]) + 5) * LO.MB_PER_RENDER / 1000 < LO.DISK_GUARD_GB:
                raise SystemExit("free disk below the 31 GB guard (resumable)")
            if rr is None:
                rr = K.Renderer()
                if rr.r.isolate is not True:
                    raise SystemExit("the renderer is not isolating renders")
                menu = rr.menu()
            part = ps[slug]
            sel, S = menu[amp][K.START[part["gain_class"]][amp]]
            if K.key(S) != K.key(ms[amp][part["gain_class"]][1]):
                raise SystemExit(f"{amp} {part['gain_class']}: the live S differs from arm B's stored copy")
            y_di, x = probe_for(slug, probe, rec_b)
            ref = CR.mono(part["crop"] / "reference.wav")
            rec = {"slug": slug, "amp": amp, "probe": probe, "sigma": meta["hash"], "stage": stage, "status": "running",
                   "renders": prev.get("renders", 0), "warm_ups": prev.get("warm_ups", 0) + 1,
                   "hash": rec_b["parts"][slug]["hash"][probe]}
            rec_path.parent.mkdir(parents=True, exist_ok=True)
            cp = OUT / "comparator" / f"{slug}-{amp}.json"
            n0 = rr.count
            if not cp.exists():
                comp = comparators(rr, sel, slug, amp, sig[(slug, amp)], aligned, x, ref)
                cp.parent.mkdir(parents=True, exist_ok=True)
                K._atomic(cp, comp)
                if comp["max_dev"] > G.CHECK_TOL:
                    breakage(rec_path, {**rec, "comparator": comp},
                             f"{slug} {amp}: a comparator at S moved {comp['max_dev']:.4f}")
            n1 = rr.count
            di32 = y_di.astype(np.float32)
            s_sig = {"di": y_di, "anchor": x, "reference": ref}
            K._atomic(rec_path, rec)

            def counted():                       # the record holds every render made so far
                rec["renders"] = prev.get("renders", 0) + rr.count - n1
                K._atomic(rec_path, rec)

            rr.render(di32, sel, S)              # amendment 2: the priming render (not scored, not stored)
            counted()
            warm = rr.render(di32, sel, S)
            counted()
            scores, checks, repeats = [], [], []
            for i, p in enumerate(sig[(slug, amp)]):
                y = rr.render(di32, sel, p["x"])
                counted()
                sc = score_render(y, probe, s_sig, aligned)
                scores.append(sc)
                if (slug, amp) == REPEAT_CELL and probe == REPEAT_PROBE and i in REPEAT_IDX:
                    y2 = rr.render(di32, sel, p["x"])
                    counted()
                    s2 = score_render(y2, probe, s_sig, aligned)
                    for h in G.HALVES:
                        dev = LO.deviation(sc["decl"][h], s2["decl"][h])
                        repeats.append([i, h, dev])
                        rec["sigma_repeats"] = repeats
                        if dev > G.CHECK_TOL:
                            breakage(rec_path, {**rec, "checks_float": checks},
                                     f"{probe} {slug} {amp}: Σ point {i} moved {dev:.4f} on its repeat, half {h}")
                if p.get("source") == "S":
                    w = score_render(warm, probe, s_sig, aligned)
                    for h in G.HALVES:
                        dev = LO.deviation(sc["decl"][h], w["decl"][h])
                        checks.append([i, "repeat_S", h, dev])
                        if dev > G.CHECK_TOL:
                            breakage(rec_path, {**rec, "checks_float": checks},
                                     f"{probe} {slug} {amp}: S moved {dev:.4f} from its warm-up on half {h}")
                    scale = LO.save_flac(flac, y)
                    fl = score_render(LO.load_flac(flac, scale), probe, s_sig, aligned)
                    fvf = {c: {h: LO.deviation(fl[c][h], sc[c][h]) for h in G.HALVES} for c in sc}
                    rec["S"] = {"index": i, "scores": sc, "flac_scale": scale, "flac_vs_float": fvf}
                    worst = max(v for c in fvf.values() for v in c.values())
                    if worst > G.CHECK_TOL:
                        breakage(rec_path, {**rec, "checks_float": checks},
                                 f"{probe} {slug} {amp}: the S FLAC scores {worst:.4f} from its float render")
            score_path.parent.mkdir(parents=True, exist_ok=True)
            K._atomic(score_path, {"scores": scores, "sigma": meta["hash"], "flac_vs_float_S": rec["S"]["flac_vs_float"]})
            rec.update(renders=prev.get("renders", 0) + rr.count - n1, comparator_renders=n1 - n0,
                       checks_float=checks, status="done")
            K._atomic(rec_path, rec)
            print(stage, probe, slug, amp, len(scores), "renders", rec["renders"], flush=True)
    finally:
        if rr is not None:
            rr.close()
    print(f"RENDER DONE {probe} {stage} {shard[0]}/{shard[1]}", flush=True)


# --- report ------------------------------------------------------------------------------------------------

def classify(c, q, side="upper"):
    """A contrast against the declared terms (plan, readings): 'above' / 'below' if its 90% interval
    excludes 0 on that side; 'near 0' if it contains 0 and its end on the side in question ('upper',
    'lower' or 'both') lies within q; otherwise 'undecided'."""
    m, lo, hi = (c or {}).get("band_weighted_mean"), (c or {}).get("lo90"), (c or {}).get("hi90")
    if m is None or lo is None or hi is None:
        return None
    if lo > 0:
        return "above"
    if hi < 0:
        return "below"
    near = {"upper": hi <= q, "lower": lo >= -q, "both": hi <= q and lo >= -q}[side]
    return "near 0" if near else "undecided"


def shape(s50, r50, band=SHAPE_BAND):
    """The dose shape from S50 (dose50's share of dose100's gain, point estimate) against r50 (its
    share of dose100's realised cut)."""
    if s50 is None or r50 is None:
        return None
    if s50 > r50 + band:
        return "concave"
    if s50 < r50 - band:
        return "convex"
    return "proportional"


def gate_cut(gains, cuts):
    """The cut that matters: the smallest realised median cut among the doses whose gain is at least
    half of dose100's (point estimates); None unless dose100's gain is positive."""
    g100 = gains.get("dose100")
    if g100 is None or g100 <= 0:
        return None
    ok = [cuts[d] for d in DOSES if gains.get(d) is not None and gains[d] >= 0.5 * g100 and d in cuts]
    return min(ok) if ok else None


def rows_for(cells, config="decl"):
    """Cell rows of every probe here, the anchor (the stored scores on R1's cells, this step's on R2's),
    the truth and C′ (1b); suffix ':rpa' for reliable-pair accuracy."""
    with bound(TONE, (ANCHOR,)):
        rows = G.cell_rows([ANCHOR], cells)
    with bound():
        mine = G.cell_rows([*PROBES, ANCHOR_R2], cells, config)
    for k, v in mine.items():
        base = k.split(":")[0]
        if base == ANCHOR_R2:
            tgt = ANCHOR + (k[len(base):])
            rows.setdefault(tgt, {}).update({c: r for c, r in v.items() if c not in rows.get(tgt, {})})
        elif base in PROBES:
            rows[k] = v
    return rows


def contrast(rows, a, b, cells, no_high=()):
    """a − b on `cells`, as the rebuild-tone report: band-weighted with its interval, LOBO, part-weighted,
    per amp and class, reliable-pair accuracy, the no-high-bleed row, truth − a, and against the anchor
    its share of the remainder (truth − anchor)."""
    from learn import local_objective_1c as C
    from learn import rebuild_tone as TN

    if a not in rows or b not in rows:
        return None
    ra = {k: v for k, v in rows[a].items() if k in cells}
    rb = {k: v for k, v in rows[b].items() if k in cells}
    d = LO.paired(ra, rb)
    if not d:
        return None
    out = TN.brief(LO.agg(d))
    if f"{a}:rpa" in rows and f"{b}:rpa" in rows:
        out["rpa"] = TN.brief(LO.agg(LO.paired({k: v for k, v in rows[f"{a}:rpa"].items() if k in cells},
                                               {k: v for k, v in rows[f"{b}:rpa"].items() if k in cells})))
    out["no_high_bleed"] = TN.brief(LO.agg({k: v for k, v in d.items() if k[0] not in no_high}))
    out["truth_minus_a"] = TN.brief(LO.agg(LO.paired({k: rows["truth"][k] for k in d}, ra)))
    if b in (ANCHOR, "cprime_ref"):
        gap = LO.paired({k: rows["truth"][k] for k in d}, rb)
        out["share_of_gap"] = C.share(d, gap)
    return out


PRIMARY = (("full_gl", ANCHOR), ("full100", ANCHOR), ("dose100", ANCHOR), ("dose50", ANCHOR), ("dose25", ANCHOR))
SECONDARY = (("dose100", "full100"), ("full_gl", "full100"), ("dose100", "dose50"), ("dose50", "dose25"),
             ("shift100", ANCHOR), ("dose100", "shift100"),
             *((p, "cprime_ref") for p in PROBES), (ANCHOR, "cprime_ref"))


def readings(r1, q):
    """The declared readings (plan) as labels; the write-up states them with the intervals."""
    g = lambda a, b: r1.get(f"{a}-{b}")  # noqa: E731
    sh = {k: (r1.get(f"{k}-{ANCHOR}") or {}).get("share_of_gap", {}) for k in ("full_gl", "full100", "dose100")}
    out = {"q": q,
           "1_full_gl": {"vs_anchor": classify(g("full_gl", ANCHOR), q, "upper"), "share": sh["full_gl"].get("ratio")},
           "2_consistency": {"full_gl-full100": classify(g("full_gl", "full100"), q, "upper"),
                             "full100_vs_anchor": classify(g("full100", ANCHOR), q, "upper")},
           "3_region": {"dose100-full100": classify(g("dose100", "full100"), q, "lower")},
           "5_control": {"shift100_vs_anchor": classify(g("shift100", ANCHOR), q, "upper"),
                         "dose100-shift100": classify(g("dose100", "shift100"), q, "upper")}}
    return out


def dose_shape(r1, rows, cells, med):
    """S25, S50 (shares of dose100's gain, Fieller), r25, r50, the shape and the gate cut; read only
    if dose100 − anchor is above 0."""
    from learn import local_objective_1c as C

    d100 = LO.paired({k: v for k, v in rows["dose100"].items() if k in cells}, {k: v for k, v in rows[ANCHOR].items() if k in cells})
    out = {"r": cut_ratios(med), "cuts": {d: med[d]["cut"] for d in DOSES if d in med}}
    gains = {}
    for d in DOSES:
        c = r1.get(f"{d}-{ANCHOR}")
        gains[d] = c.get("band_weighted_mean") if c else None
        if d != "dose100" and d in rows and c:                 # only complete (unrefused) doses
            dd = LO.paired({k: v for k, v in rows[d].items() if k in cells}, {k: v for k, v in rows[ANCHOR].items() if k in cells})
            out[f"S_{d}"] = C.share(dd, d100)
    out["gains"] = gains
    out["read"] = classify(r1.get(f"dose100-{ANCHOR}"), 0, "upper") == "above"
    s50 = (out.get("S_dose50") or {}).get("ratio")
    s25 = (out.get("S_dose25") or {}).get("ratio")
    out["shape_50"] = shape(s50, out["r"].get("dose50")) if out["read"] else None
    out["shape_25"] = shape(s25, out["r"].get("dose25")) if out["read"] else None
    out["shape"] = (out["shape_50"] if out["shape_50"] == out["shape_25"] else "undecided") if out["read"] else None
    nm = r1.get("dose100-dose50")
    out["non_monotone"] = bool(gains.get("dose50") is not None and gains.get("dose100") is not None
                               and gains["dose50"] > gains["dose100"])
    out["dose100_minus_dose50"] = classify(nm, 0, "upper") if nm else None
    out["gate_cut"] = gate_cut(gains, out["cuts"]) if out["read"] else None
    return out


def gain_vs_cut(rows, cells, rec):
    """Descriptive (plan, secondaries): per probe, the Spearman over parts of its gain against the
    anchor (part means over cells) and its realised E_st cut on that part (build.json)."""
    from scipy.stats import spearmanr

    out = {}
    for p in PROBES:
        if p not in rows or ANCHOR not in rows:
            continue
        d = LO.paired({k: v for k, v in rows[p].items() if k in cells}, {k: v for k, v in rows[ANCHOR].items() if k in cells})
        by = {}
        for (slug, _), (_, _, _, v) in d.items():
            by.setdefault(slug, []).append(v)
        pairs = [(sum(v) / len(v), rec["parts"][s]["probes"][p]["cut"]) for s, v in by.items() if s in rec["parts"]]
        if len(pairs) >= 3:
            r = spearmanr([a for a, _ in pairs], [b for _, b in pairs]).correlation
            out[p] = {"spearman": None if r != r else float(r), "parts": len(pairs)}
    return out


def extension(r1, ratio):
    """R1 → R2 (stage TR's rule): each probe in priority order whose contrast against the anchor is
    positive, contains 0 and would exclude it once narrowed; the control goes with dose100."""
    out = [p for p in EXTEND_ORDER if G.extends(r1.get(f"{p}-{ANCHOR}") or {}, ratio)]
    if "dose100" in out:
        out.insert(out.index("dose100") + 1, "shift100")
    return out


def renders_used():
    """Every render of this step: the cells' records (cleared ones too, amendment 2), the comparators,
    and renders made but never recorded (`unrecorded.json`: the first launch's 33)."""
    tot, by = 0, {}
    for p in [*(OUT / "renders").glob("*/*/*.json"), *(OUT / "cleared" / "renders").glob("*/*/*.json")]:
        r = json.loads(p.read_text())
        by[r["probe"]] = by.get(r["probe"], 0) + r.get("renders", 0)
        tot += r.get("renders", 0)
    comp = sum(json.loads(p.read_text()).get("renders", 0) for p in (OUT / "comparator").glob("*.json"))
    u = OUT / "unrecorded.json"
    unrec = json.loads(u.read_text())["renders"] if u.exists() else 0
    return {"by_probe": by, "comparator": comp, "unrecorded": unrec, "total": tot + comp + unrec}


def cmd_clear(probe, slug, amp):
    """Amendment 2, item 3: clear one cell's `check_failed` record after its investigation. The record
    moves to `cleared/` (its renders still count) and STOP.json is deleted; the cell then renders from
    scratch. Refuses any record that is not `check_failed`."""
    rec_path = _paths(probe, slug, amp)[0]
    rec = json.loads(rec_path.read_text()) if rec_path.exists() else {}
    if rec.get("status") != "check_failed":
        raise SystemExit(f"{probe} {slug} {amp}: no check_failed record to clear")
    dest = OUT / "cleared" / rec_path.relative_to(OUT)
    if dest.exists():
        raise SystemExit(f"{dest} exists: this cell was cleared before")
    dest.parent.mkdir(parents=True, exist_ok=True)
    K._atomic(dest, {**rec, "cleared": time.strftime("%Y-%m-%d %H:%M:%S")})
    rec_path.unlink()
    (OUT / "STOP.json").unlink(missing_ok=True)
    print(f"cleared {probe} {slug} {amp} -> {dest}", flush=True)


def cmd_report():
    from learn import rebuild_tone as TN

    r1 = G.r1_cells()
    every = sorted(set(r1) | set(G.r2_cells()))
    nh = set(TN.high_bleed())
    med = build_record()["medians"]
    out = {"no_high_bleed_parts": sorted(nh), "build_medians": med}
    for config in ("decl", "xmask"):
        rows = rows_for(every, config)
        blk = {"r1": {}, "all72": {}, "fidelity": {}}
        blk["refused"] = {}
        for a, b in (*PRIMARY, *SECONDARY):
            if not (TN.complete(rows, a, r1) and TN.complete(rows, b, r1)):
                blk["refused"][f"{a}-{b}"] = (f"{sum(c in rows.get(a, {}) for c in r1)} and "
                                              f"{sum(c in rows.get(b, {}) for c in r1)} of {len(r1)} cells scored")
                continue
            c = contrast(rows, a, b, set(r1), nh)
            if c:
                blk["r1"][f"{a}-{b}"] = c
            if TN.complete(rows, a, every) and TN.complete(rows, b, every):
                blk["all72"][f"{a}-{b}"] = contrast(rows, a, b, set(every), nh)
        for n in ("truth", "cprime_ref", ANCHOR, *PROBES):
            if n in rows:
                blk["fidelity"][n] = TN.brief(LO.agg({k: v for k, v in rows[n].items() if k in set(r1)}))
        rem = blk["r1"].get(f"{ANCHOR}-cprime_ref", {}).get("truth_minus_a", {}).get("band_weighted_mean")
        q = NEAR_SHARE * rem if rem else None
        blk["remainder"] = rem
        blk["readings"] = readings(blk["r1"], q) if q else None
        blk["dose_shape"] = dose_shape(blk["r1"], rows, set(r1), med) if f"dose100-{ANCHOR}" in blk["r1"] else None
        blk["gain_vs_cut"] = gain_vs_cut(rows, set(r1), build_record())
        out[config] = blk
    out["narrowing"] = G.narrowing_ratio()
    out["extend"] = extension(out["decl"]["r1"], out["narrowing"]["ratio"])
    out["renders"] = renders_used()
    K._atomic(OUT / "report.json", out)
    for k, v in out["decl"]["r1"].items():
        print(f"{k}: {v['band_weighted_mean']:+.3f} [{v['lo90']:+.3f}, {v['hi90']:+.3f}] "
              f"bands {v['bands_positive']}/{v['bands_negative']}", flush=True)
    if out["decl"]["refused"]:
        print("refused (incomplete):", json.dumps(out["decl"]["refused"]), flush=True)
    print("readings:", json.dumps(out["decl"]["readings"]), flush=True)
    print("extend:", ",".join(out["extend"]) or "none", flush=True)
    print("REPORT DONE", flush=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("slots")
    sub.add_parser("report")
    e = sub.add_parser("extend")
    e.add_argument("--with-anchor", action="store_true")
    c = sub.add_parser("clear")
    c.add_argument("--probe", required=True)
    c.add_argument("--cell", nargs=2, required=True, metavar=("SLUG", "AMP"))
    a = ap.parse_args(argv)
    if a.cmd == "build":
        cmd_build()
    elif a.cmd == "slots":
        cmd_slots()
    elif a.cmd == "report":
        cmd_report()
    elif a.cmd == "clear":
        cmd_clear(a.probe, *a.cell)
    elif a.cmd == "extend":
        ext = json.loads((OUT / "report.json").read_text())["extend"]
        print(" ".join(([ANCHOR_R2] if ext and a.with_anchor else []) + ext))


if __name__ == "__main__":
    main()
