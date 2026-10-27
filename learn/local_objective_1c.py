"""Experiment 1c (`docs/local-objective-plan.md`, amendment 3): a real separator in 1b's matched
design. Mega-53's electric-guitar head separates the same 30-s context step 3's htdemucs stem came
from; C′ (each part's fold) rebuilds its crop; Σ renders through that rebuild and is scored against
the same crop. Development only; estimates with 90% band-clustered intervals, no pass/fail bars.

    $MSST_PY -m learn.local_objective_1c separate [--no-wait]   # CPU; memory gate, may run beside renders
    .venv/bin/python -m learn.local_objective_1c blend         # optional add-on, zero renders
    $TORCH_PY -m learn.local_objective_1c rebuild --sep mega53  # CPU, zero renders; the 2a checks
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective render --di cprime_mega53 --shard i/3
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.local_objective score --di cprime_mega53,cprime@mega53 --workers 3
    .venv/bin/python -m learn.local_objective_1c report --sep mega53

MSST_PY is ~/ndsp-presets/tools/msst-venv/bin/python; TORCH_PY is
~/ndsp-presets/tools/demucs-venv/bin/python. Outputs go to ~/ndsp-presets/learn/local-objective/
(`sep/<separator>/`, `rebuilt-<separator>/`, `report-1c-<separator>.json`).

The context: step 3's stems are `learn/set3/stems` (set 3) and `learn/poc/stems` (sets 1–2), each
separated from `_work/contexts/<part>/mix_instrumental.wav` (about 30 s, crop − 10 s … crop + 10 s,
shifted inside the session) with the crop's 10 s cut at `crop_offset_in_context`; a set-3 context
that was not rebuilt exactly fell back to the 10-s crop. Mega-53 gets the same input and the same
cut (`context_plan`).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import re
import statistics
import subprocess
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import arm_a_levers as L  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import local_objective as LO  # noqa: E402

SR = 48000
CROP = 480_000
LAG_TOL = 3                      # samples: |GCC(Mega-53 crop, htdemucs crop)| (the plan's timing check)
BLEND_LAG_TOL = 1                # amendment 3a: the blend's |relative lag|, no shift (beyond: refused)
EDGE_FLOOR_DB = -100.0           # the edge bound's extent: where crop- and full-filtering differ by more
LINEUP_TOL = 1e-6                # the stem builders' line-up tolerance (context slice against the crop file)
# Amendment 3a: the gate is keyed on what loads. The pruned head peaked at 7.13–7.18 GB RSS in the
# screen (+ about 50%); 18 GB is for the full model (the identity check's 17.1 GB peak).
MEM_GATE_PRUNED_GB = 11.0
MEM_GATE_FULL_GB = 18.0
MEM_GATE_GB = MEM_GATE_PRUNED_GB
POLL_S = 60
TRAINING = (r"-m learn\.\S+\s+(train|fit)\b",     # MPS training jobs (song_soundspace, direc, train, ...)
            r"-m learn\.xlance_finetune gate\b")   # D_F5ft's MPS gate (ROADMAP (b)): trains steps on MPS
SUBSETS_1C = {**LO.SUBSETS, "without_armA": ("S", "nbr", "ks")}
# Amendment 3a: bleed and leak rows, on all of Σ, each with the share's numerator and denominator on
# the same cells. Bleed flags per part and half come from the bleed audit; "cell" drops a cell if
# either half is flagged (r4's rule, the bleed README's table), "dir" drops a direction (objective on
# half h, truth on the other) whose truth half is flagged (beside it).
BLEED_TABLE = PLUGIN_ROOT / "docs/audits/bleed-2026-10-16/bleed-table.json"
ROWS = {"all": ("all", None),
        "no_high": ("cell", {"high"}), "no_high_dir": ("dir", {"high"}),
        "no_moderate_or_high": ("cell", {"moderate", "high"}), "no_moderate_or_high_dir": ("dir", {"moderate", "high"}),
        "cambridge_only": ("source", "cambridge"),         # where 1b really is a perfect-separator cell
        "telefunken_only": ("source", "telefunken"),       # 3 bands: descriptive at most
        "without_musdb_train": ("bands_out", None)}        # htdemucs_6s trained on these bands' songs
CLEANEST_ROW = "cambridge_only"
BLEED_1B = {"no_high": 0.227, "no_moderate_or_high": 0.253, "cambridge_only": 0.273}   # audited 1b rows
DECLARED = "all"                 # the reading is on all of Σ; the subsets are descriptive


def out():
    return LO.OUT


def sep_dir(sep):
    return out() / "sep" / sep


# --- the context, as step 3's htdemucs stem was built ----------------------------------------------

def stems_root(stem_path):
    """`<root>/htdemucs_6s/<part>/instrumental_guitar.wav` -> <root> (set 3's or sets 1–2's)."""
    p = pathlib.Path(stem_path)
    if p.parents[1].name != "htdemucs_6s" or p.name != "instrumental_guitar.wav":
        raise ValueError(f"not a step-3 htdemucs stem: {p}")
    return p.parents[2]


def context_plan(slug, ctx, work, crop_dir):
    """The separator's input for a part, as `_work/separate_demucs.py` chose it: the stored
    instrumental context and the crop's offset in it, or (set 3, a context not rebuilt exactly)
    the 10-s crop at offset 0. -> {"input", "offset", "kind", "lineup"}; `lineup` is the crop file
    the context's crop slice must equal (`mix_instrumental.wav`, or set 3's recorded crop file)."""
    crop_file = (ctx.get("line_up_check") or {}).get("crop_file", "mix_instrumental.wav")
    lineup = pathlib.Path(crop_dir) / crop_file
    if ctx.get("context_rebuilt_exactly", True):
        return {"input": pathlib.Path(work) / "contexts" / slug / "mix_instrumental.wav",
                "offset": int(ctx["crop_offset_in_context"]), "kind": "context", "lineup": lineup}
    return {"input": lineup, "offset": 0, "kind": "crop10s_fallback", "lineup": lineup}


def part_plan(slug, part):
    root = stems_root(part["stem"])
    work = root / "_work"
    ctx = json.loads((work / "contexts.json").read_text())[slug]
    return context_plan(slug, ctx, work, part["crop"])


def parts():
    return {s: p for s, p in sorted(K.parts().items()) if s not in LO.EXCLUDED}


# --- the memory gate ---------------------------------------------------------------------------------

def available_gb(vm_stat_text):
    """Free + inactive + speculative pages from `vm_stat`, in GB."""
    m = re.search(r"page size of (\d+) bytes", vm_stat_text)
    page = int(m.group(1)) if m else 4096
    pages = 0
    for name in ("free", "inactive", "speculative"):
        m = re.search(rf"Pages {name}:\s+(\d+)\.", vm_stat_text)
        pages += int(m.group(1)) if m else 0
    return pages * page / 1e9


def is_training(cmd):
    from learn import ks_extend as X

    return X._is_python(cmd) and any(re.search(p, cmd) for p in TRAINING)


def mem_gate_gb(pruned):
    """Amendment 3a: about 11 GB for the pruned head, 18 GB for the full model."""
    return MEM_GATE_PRUNED_GB if pruned else MEM_GATE_FULL_GB


def prune_decision(identity):
    """Prune to the electric-guitar head only if the screen's identity check found it identical to
    the full model. identity: the parsed `identity.json`, or None."""
    return bool(identity) and identity.get("identical") is True


def separation_blockers(ps, own, avail_gb, min_gb=MEM_GATE_GB):
    """Why Mega-53 may not run now (empty: it may): an MPS training job, another separation, or
    less available memory than the gate. Renders are not blockers (amendment 3a): CPU torch at 4
    fixed threads is deterministic and offline renders are load-independent, so Mega-53 may run
    beside ks_extend; the swap-growth guard stays the backstop."""
    out_ = []
    rest = [(p, c) for p, c in ps if p not in own]
    tr = [p for p, c in rest if is_training(c)]
    if tr:
        out_.append(f"training processes {tr}")
    sp = LO.separating(rest)
    if sp:
        out_.append(f"another separation {sp}")
    if avail_gb is None or avail_gb < min_gb:
        out_.append(f"available memory {avail_gb} GB, under the {min_gb} GB gate")
    return out_


def _blockers(min_gb):
    from learn import ks_extend as X

    vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    return separation_blockers(X._ps(), {os.getpid(), os.getppid()}, available_gb(vm) if vm else None, min_gb)


def wait_idle(no_wait=False, min_gb=MEM_GATE_GB):
    while True:
        b = _blockers(min_gb)
        if not b:
            return
        if no_wait:
            raise SystemExit(f"the machine is not idle for Mega-53: {b}")
        print(time.strftime("%H:%M:%S"), "waiting:", b, flush=True)
        time.sleep(POLL_S)


# --- separation checks ------------------------------------------------------------------------------

def sep_problems(lag, lineup, n, lag_tol=LAG_TOL, lineup_tol=LINEUP_TOL, crop=CROP):
    """A separated crop is used only if it sits within `lag_tol` samples of step 3's htdemucs stem
    (GCC), its input's crop slice equals the crop file, and it is the crop's length."""
    p = []
    if lag is None or abs(lag) > lag_tol:
        p.append(f"GCC against the htdemucs stem is {lag} samples (limit ±{lag_tol})")
    if lineup is None or lineup >= lineup_tol:
        p.append(f"the input's crop slice differs from the crop file by {lineup}")
    if n != crop:
        p.append(f"crop length {n}, not {crop}")
    return p


def snr_db(stem, ref):
    """Gain-fitted SNR of `ref` explained by `stem` (the separator screen's sanity figure)."""
    import numpy as np

    s, r = np.asarray(stem, np.float64), np.asarray(ref, np.float64)
    a = np.dot(s, r) / (np.dot(s, s) + 1e-20)
    return float(10 * np.log10(np.sum(r ** 2) / (np.sum((r - a * s) ** 2) + 1e-20)))


def write_check(d, log, names):
    bad = {s: v["problems"] for s, v in log.items() if v.get("problems")}
    missing = [s for s in names if s not in log]
    K._atomic(d / "check.json", {"ok": not bad and not missing, "problems": bad, "missing": missing})
    return bad, missing


def sep_ok(sep):
    p = sep_dir(sep) / "check.json"
    return p.exists() and json.loads(p.read_text()).get("ok") is True


# --- commands ------------------------------------------------------------------------------------------

def cmd_separate(no_wait=False, min_gb=None):
    """Mega-53 (pruned to its electric-guitar head when the screen's identity check passed) on each
    part's context, CPU only. Pruning is decided first, then it waits for the memory gate (11 GB
    pruned, 18 GB full; amendment 3a) and for no training job or other separation; it may run
    beside renders. It stops (resumable) if a training job or separation starts between parts. Per part: the line-up check, the
    30-s stem and its crop, GCC against the htdemucs stem (±3 samples), and SNRs against
    reference.wav (descriptive)."""
    import numpy as np
    import soundfile as sf

    from learn import confirm_run as CR
    from learn import rank_margin as RM
    from learn import separator_screen as SCR

    ps = parts()
    d = sep_dir("mega53")
    (d / "full").mkdir(parents=True, exist_ok=True)
    (d / "crop").mkdir(parents=True, exist_ok=True)
    log_path = d / "log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}
    todo = [s for s in ps if not (s in log and LO.sep_crop_path("mega53", s).exists())]
    if todo:
        ident = SCR.out_dir() / "identity.json"                       # amendment 3a: prune first
        prune = prune_decision(json.loads(ident.read_text()) if ident.exists() else None)
        gate = mem_gate_gb(prune) if min_gb is None else min_gb
        print("pruned" if prune else "full model", "memory gate", gate, "GB", flush=True)
        wait_idle(no_wait, gate)
        sep = SCR.MsstSeparator(prune=prune)
        for slug in todo:
            b = _blockers(0.0)                                           # memory is ours now
            if b:
                raise SystemExit(f"stopped before {slug} (resumable): {b}")
            part, plan = ps[slug], part_plan(slug, ps[slug])
            x, sr = sf.read(str(plan["input"]), dtype="float32")
            assert sr == SR and x.ndim == 1, slug
            off = plan["offset"]
            crop_in, _ = sf.read(str(plan["lineup"]), dtype="float32")
            lineup = float(np.max(np.abs(x[off:off + CROP] - crop_in))) if len(crop_in) == CROP else None
            t = time.time()
            y = np.asarray(sep(x), np.float32)
            assert len(y) == len(x), slug
            crop = y[off:off + CROP]
            hd = CR.mono(part["stem"]).astype(np.float64)
            ref = CR.mono(part["crop"] / "reference.wav")
            lag = int(RM.gcc_lag(crop.astype(np.float64), hd))
            np.save(d / "full" / f"{slug}.npy", y)
            np.save(LO.sep_crop_path("mega53", slug), crop)
            row = {"input": str(plan["input"]), "kind": plan["kind"], "offset": off, "input_s": len(x) / SR,
                   "lineup_max_abs": lineup, "gcc_vs_htdemucs": lag,
                   "snr_db_vs_reference": {"mega53": snr_db(crop, ref), "htdemucs": snr_db(hd, ref)},
                   "level_above_6k_db_vs_htdemucs": SCR._band_db(crop.astype(np.float64), hd, 6000, 20000),
                   "wall_s": round(time.time() - t, 1), "peak_rss_mb": round(SCR.peak_rss_mb(), 1)}
            screen = SCR.out_dir() / "stems" / "mega53" / f"{slug}-real.npy"   # descriptive repeat
            if screen.exists():
                row["screen_repeat_max_abs"] = float(np.max(np.abs(np.load(screen)[off:off + CROP] - crop)))
            row["problems"] = sep_problems(lag, lineup, len(crop))
            log[slug] = row
            K._atomic(log_path, log)
            print(slug, {k: row[k] for k in ("gcc_vs_htdemucs", "snr_db_vs_reference", "wall_s", "problems")},
                  flush=True)
        K._atomic(d / "run.json", {**sep.info(), "pruned_by_identity": prune, "memory_gate_gb": gate})
    bad, missing = write_check(d, log, ps)
    if bad or missing:
        raise SystemExit(f"Mega-53 stems fail the checks: {bad or missing}")
    print("Mega-53: all 24 crops within ±3 samples of the htdemucs stems; line-ups exact")


def blend_problems(rel, tol=BLEND_LAG_TOL):
    """Amendment 3a: a blend needs |relative lag| <= 1 sample (no shift: both stems sit on the mix's
    timeline, and a ±1 GCC reading is most likely estimator jitter)."""
    return [] if rel is not None and abs(rel) <= tol else [f"relative lag {rel} (the blend allows ±{tol}, no shift)"]


def edge_bound(full, off, n=CROP, floor_db=EDGE_FLOOR_DB):
    """What filtering the high band on the crop instead of on the full stem changes: HP(x[crop])
    against HP(x)[crop] (HP = x − LP, `separator_screen.lowpass`). -> the largest difference in dB
    relative to the crop's peak, and how far from either end of the crop it exceeds `floor_db`
    (ms). The end transient sits inside half B, which ends at the crop's end (amendment 3a)."""
    import numpy as np

    from learn import separator_screen as SCR

    x = np.asarray(full, np.float64)
    c = x[off:off + n]
    a = (x - SCR.lowpass(x))[off:off + n]
    b = c - SCR.lowpass(c)
    d = np.abs(a - b)
    peak = float(np.max(np.abs(c))) or 1.0
    mx = float(d.max())
    over = np.nonzero(d > peak * 10 ** (floor_db / 20))[0]
    head, tail = over[over < n // 2], over[over >= n // 2]
    ext = max(int(head.max()) + 1 if len(head) else 0, n - int(tail.min()) if len(tail) else 0)
    return {"max_db": 20 * math.log10(mx / peak) if mx > 0 else -math.inf, "extent_ms": ext / SR * 1000}


def cmd_blend():
    """The optional crossover (zero renders): LP(Mega-53) + (htdemucs − LP(htdemucs)) at 6 kHz
    (`separator_screen.blend`'s filter). Mega-53's low band is filtered on its 30-s stem before the
    crop is cut; step 3's htdemucs stem exists only as the 10-s crop, so its high band is taken on
    the crop. The crop's end is half B's end, so that transient is inside the judged audio: each part
    logs the edge bound (`edge_bound`) on its Mega-53 stem as a proxy, and exactly on htdemucs where
    the screen kept a 30-s htdemucs stem. Amendment 3a: |relative lag| <= 1, no shift, else no blend."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import rank_margin as RM
    from learn import separator_screen as SCR

    if not sep_ok("mega53"):
        raise SystemExit("run `separate` first (its checks must pass)")
    ps = parts()
    mlog = json.loads((sep_dir("mega53") / "log.json").read_text())
    d = sep_dir("blend")
    (d / "crop").mkdir(parents=True, exist_ok=True)
    log = {}
    for slug, part in ps.items():
        off = mlog[slug]["offset"]
        mega30 = np.load(sep_dir("mega53") / "full" / f"{slug}.npy").astype(np.float64)
        hd = CR.mono(part["stem"]).astype(np.float64)
        rel = int(RM.gcc_lag(mega30[off:off + CROP], hd))
        row = {"relative_lag": rel, "problems": blend_problems(rel),
               "edge_bound_mega53_proxy": edge_bound(mega30, off)}
        hd30 = SCR.out_dir() / "stems" / "htdemucs" / f"{slug}-real.npy"
        if hd30.exists():
            row["edge_bound_htdemucs"] = edge_bound(np.load(hd30).astype(np.float64), off)
        if not row["problems"]:
            b = SCR.lowpass(mega30)[off:off + CROP] + (hd - SCR.lowpass(hd))
            np.save(LO.sep_crop_path("blend", slug), b.astype(np.float32))
        log[slug] = row
        print(slug, row, flush=True)
    K._atomic(d / "log.json", log)
    bad, missing = write_check(d, log, ps)
    if bad or missing:
        raise SystemExit(f"blend: not every part has one: {bad or missing}")


def cmd_rebuild(sep):
    """C′ rebuilds each part's separated crop exactly as 1b rebuilt reference.wav (amendment 2a's
    checks gate `render --di cprime_<sep>`)."""
    import numpy as np

    if not sep_ok(sep):
        raise SystemExit(f"{sep}: the separation checks have not passed")
    LO.rebuild_from(LO.SEP_DI[sep], lambda slug, part: np.load(LO.sep_crop_path(sep, slug)))


# --- the report -----------------------------------------------------------------------------------------

def band_means(rows):
    """rows {cell: (slug, band, cls, value)} -> {band: mean of its part means}."""
    pm = L.part_means([(s, b, v) for (s, b, _, v) in rows.values() if v is not None])
    by = {}
    for _, b, v in pm:
        by.setdefault(b, []).append(v)
    return {b: statistics.fmean(v) for b, v in by.items()}


def fieller(a, d, level=0.90):
    """The ratio mean(a) / mean(d) of paired band values, with Fieller's interval (t, n − 1 df), the
    analogue for a ratio of the band-clustered t interval. Unbounded when the denominator's own
    interval contains 0."""
    from scipy import stats

    n = len(a)
    if n < 3 or len(d) != n:
        return {"ratio": None, "lo90": None, "hi90": None, "bounded": False, "shape": None, "bands": n,
                "df": max(n - 1, 0)}
    ma, md = statistics.fmean(a), statistics.fmean(d)
    saa = statistics.variance(a) / n
    sdd = statistics.variance(d) / n
    sad = sum((x - ma) * (y - md) for x, y in zip(a, d)) / (n - 1) / n
    t = stats.t.ppf(0.5 + level / 2, n - 1)
    A, B, C = md * md - t * t * sdd, ma * md - t * t * sad, ma * ma - t * t * saa
    r = ma / md if md else None
    disc = B * B - A * C
    if A <= 0 or disc < 0:
        # A < 0 with disc > 0 is a two-ray set (the ratio is outside a finite gap); otherwise the
        # whole line. Both are reported as unbounded (amendment 3a).
        shape = "two rays" if A < 0 and disc > 0 else "whole line"
        return {"ratio": r, "lo90": None, "hi90": None, "bounded": False, "shape": shape, "bands": n, "df": n - 1}
    s = math.sqrt(disc)
    return {"ratio": r, "lo90": (B - s) / A, "hi90": (B + s) / A, "bounded": True, "shape": "interval",
            "bands": n, "df": n - 1}


def share(num_rows, den_rows, level=0.90):
    """The share of 1b's separator gain recovered: (sep − current) / (1b − current), on the cells
    with both, band-weighted, with Fieller's interval and the leave-one-band-out range."""
    common = {c for c in num_rows if c in den_rows}
    nb = band_means({c: num_rows[c] for c in common})
    db = band_means({c: den_rows[c] for c in common})
    bands = sorted(set(nb) & set(db))
    a, d = [nb[b] for b in bands], [db[b] for b in bands]
    out_ = fieller(a, d, level)
    lobo = []
    for i in range(len(bands)):
        da = statistics.fmean(d[:i] + d[i + 1:]) if len(d) > 1 else None
        if da:
            lobo.append(statistics.fmean(a[:i] + a[i + 1:]) / da)
    out_["leave_one_band_out"] = [min(lobo), max(lobo)] if lobo else None
    return out_


def reading_1c(diff, gain_1b, near=LO.NEAR_GAP_SHARE):
    """Amendment 3's reading of sep − current (cross-half, band-weighted, all of Σ; estimates
    only, on the instrumental context): 'above' if the 90% interval is above 0 (the separator
    recovers part of the separator's share: the product path is to switch, after a fresh-draw check
    run on full mixes with vocals for both separators); 'below' if under 0; 'near
    zero' if it contains 0 and its top recovers under a quarter of 1b's gain (this separator isn't
    better for this purpose); otherwise 'undecided'."""
    lo, hi = diff.get("lo90"), diff.get("hi90")
    if lo is None or hi is None:
        return "undecided"
    if lo > 0:
        return "above"
    if hi < 0:
        return "below"
    if gain_1b is not None and gain_1b > 0 and hi < near * gain_1b:
        return "near zero"
    return "undecided"


def kept_directions(row, slug, band, bt):
    """The directions (objective half) a row keeps for a cell. bt: the bleed table."""
    from learn import song_readout as R

    kind, arg = ROWS[row]
    if kind == "all":
        return LO.HALVES
    if kind == "source":
        return LO.HALVES if slug in bt and bt[slug]["source"] == arg else ()
    if kind == "bands_out":
        return () if band in R.MUSDB_TRAIN_BANDS else LO.HALVES
    if slug not in bt:
        return ()
    flag = {h: bt[slug]["halves"][h]["flag"] for h in LO.HALVES}
    if kind == "cell":
        return () if any(f in arg for f in flag.values()) else LO.HALVES
    return tuple(h for h in LO.HALVES if flag[LO.other(h)] not in arg)


def directions(obj, true):
    """Cross-half Spearman per direction: objective on half h against the truth on the other."""
    return {h: LO.rho(obj[h], true[LO.other(h)]) for h in LO.HALVES}


def row_rows(dirvals, ps, bt, row, name):
    """{cell: (slug, band, cls, mean over the row's kept directions)}; cells with none are left out."""
    out_ = {}
    for c, v in dirvals.items():
        if name not in v:
            continue
        p = ps[c[0]]
        keep = kept_directions(row, c[0], p["band"], bt)
        if keep:
            out_[c] = (c[0], p["band"], p["gain_class"], LO._mean(v[name][h] for h in keep))
    return out_


def row_report(dirvals, ceil, ps, bt, row, names=("sep", "current", "matched_1b")):
    """One bleed or leak row: each name's cross-half, the differences, the ceiling, and the share
    (sep − current) / (1b − current) on the same cells, with Fieller on this row's bands."""
    rr = {n: row_rows(dirvals, ps, bt, row, n) for n in names}
    out_ = {n: LO.agg(v) for n, v in rr.items()}
    cells = set(rr["current"])
    out_["ceiling"] = LO.agg({c: (c[0], ps[c[0]]["band"], ps[c[0]]["gain_class"], ceil[c]) for c in cells if c in ceil})
    for a in names:
        if a != "current":
            out_[f"{a}_minus_current"] = LO.agg(LO.paired(rr[a], rr["current"]))
    if "sep" in rr and "matched_1b" in rr:
        num, den = LO.paired(rr["sep"], rr["current"]), LO.paired(rr["matched_1b"], rr["current"])
        both = set(num) & set(den)
        out_["share_of_1b_gain"] = share({c: num[c] for c in both}, {c: den[c] for c in both})
        out_["sep_minus_matched_1b"] = LO.agg(LO.paired(rr["sep"], rr["matched_1b"]))
    return out_


def report_configs(sep):
    di = LO.SEP_DI[sep]
    cfgs = {"sep": (di, sep, "native", "own"), "sep_gcc": (di, sep, "gcc", "own"),
            "rebuild_only": (di, "stem", "native", "own"), "reference_only": ("cprime", sep, "native", "own"),
            "current": LO.CURRENT, "matched_1b": LO.MATCHED, "cprime_reference": ("cprime", "reference", "native", "own")}
    src = {"sep": di, "sep_gcc": di, "rebuild_only": di, "reference_only": f"cprime@{sep}", "current": "cprime",
           "matched_1b": LO.MATCHED_DI, "cprime_reference": "cprime"}
    return cfgs, src


REQUIRED = ("sep", "current", "matched_1b")
DIFFS = {"sep_minus_current": ("sep", "current"), "matched_1b_minus_current": ("matched_1b", "current"),
         "sep_minus_matched_1b": ("sep", "matched_1b"),
         "reference_only_minus_current": ("reference_only", "current"),
         "rebuild_only_minus_current": ("rebuild_only", "current"),
         "sep_minus_reference_only": ("sep", "reference_only")}
SCOPE = "on the instrumental context (the record's vocal tracks removed, as step 3's stems)"


def load_bleed_table(path=BLEED_TABLE):
    return json.loads(pathlib.Path(path).read_text())


def cell_directions(sig, cfgs, src, required):
    """Per cell (all of Σ): each named configuration's cross-half Spearman per direction, and the
    ceiling; a cell needs the measure DI's scores and every `required` name's. -> (dirvals, ceil)."""
    dirvals, ceil = {}, {}
    for c in sorted(sig):
        files = {d: out() / "scores" / d / c[0] / f"{c[1]}.json" for d in {"measure", *src.values()}}
        if not files["measure"].exists() or not all(files[src[n]].exists() for n in required):
            continue
        sc = {d: json.loads(f.read_text())["scores"] for d, f in files.items() if f.exists()}
        true = LO._vals(sc["measure"], LO.TRUE)
        ceil[c] = LO.ceiling(true)
        dirvals[c] = {n: directions(LO._vals(sc[src[n]], cfg), true) for n, cfg in cfgs.items() if src[n] in sc}
    return dirvals, ceil


def cmd_report(sep="mega53"):
    """Zero renders: the separator's matched cell against the truth (experiment 1's measure-DI
    scores), paired with today's objective and with 1b; the share of 1b's gain recovered; on all of
    Σ and its subsets, per band; the stems' SNRs; the renders; the reading."""
    meta, sig = LO.load_sigma()
    ps = K.parts()
    cfgs, src = report_configs(sep)
    per = {}
    for c, pts in sorted(sig.items()):
        files = {d: out() / "scores" / d / c[0] / f"{c[1]}.json" for d in {"measure", *src.values()}}
        if not files["measure"].exists() or not all(files[src[n]].exists() for n in REQUIRED):
            continue
        sc = {d: json.loads(f.read_text())["scores"] for d, f in files.items() if f.exists()}
        true = LO._vals(sc["measure"], LO.TRUE)
        per[c] = {name: {sub: LO.subset_measures(pts, LO._vals(sc[src[name]], cfg), true, srcs)
                         for sub, srcs in SUBSETS_1C.items()}
                  for name, cfg in cfgs.items() if src[name] in sc}

    def rows(name, sub, key):
        return {c: (c[0], ps[c[0]]["band"], ps[c[0]]["gain_class"], v[name][sub][key]) for c, v in per.items()
                if name in v}

    rep = {"sigma": meta["hash"], "separator": sep, "di": LO.SEP_DI[sep], "cells": len(per), "subsets": {}}
    for sub in SUBSETS_1C:
        r = {"ceiling": LO.agg(rows("current", sub, "ceiling"))}
        for name in cfgs:
            r[name] = {k: LO.agg(rows(name, sub, k)) for k in ("cross_half", "reliable_accuracy", "same_half")}
        for dn, (a, b) in DIFFS.items():
            r[dn] = {k: LO.agg(LO.paired(rows(a, sub, k), rows(b, sub, k))) for k in ("cross_half", "reliable_accuracy")}
        r["interaction"] = {k: LO.agg(LO.paired(LO.paired(rows("sep", sub, k), rows("reference_only", sub, k)),
                                                LO.paired(rows("rebuild_only", sub, k), rows("current", sub, k))))
                            for k in ("cross_half", "reliable_accuracy")}     # sep − ref only − rebuild only + current
        r["share_of_1b_gain"] = {k: share(LO.paired(rows("sep", sub, k), rows("current", sub, k)),
                                          LO.paired(rows("matched_1b", sub, k), rows("current", sub, k)))
                                 for k in ("cross_half", "reliable_accuracy")}
        rep["subsets"][sub] = r
    bt = load_bleed_table()
    dirvals, ceil = cell_directions(sig, cfgs, src, REQUIRED)
    rep["bleed_and_leak_rows"] = {row: row_report(dirvals, ceil, ps, bt, row) for row in ROWS}
    rep["cleanest_row"] = CLEANEST_ROW
    rep["scope"] = SCOPE
    bands = {}
    for c, v in per.items():
        bands.setdefault(ps[c[0]]["band"], {}).setdefault(c[0], []).append(
            tuple(v[n]["all"]["cross_half"] for n in ("sep", "current", "matched_1b")) + (v["current"]["all"]["ceiling"],))
    rep["per_band_cross_half"] = {}
    for b, pp in sorted(bands.items()):
        m = {k: LO._mean(LO._mean(t[j] for t in vals) for vals in pp.values())
             for j, k in enumerate(("sep", "current", "matched_1b", "ceiling"))}
        for k in ("sep", "matched_1b"):
            m[f"{k}_minus_current"] = None if m[k] is None or m["current"] is None else m[k] - m["current"]
        rep["per_band_cross_half"][b] = m
    slog = sep_dir(sep) / "log.json"
    if slog.exists():
        sl = json.loads(slog.read_text())
        mlog = json.loads((sep_dir("mega53") / "log.json").read_text()) if sep != "mega53" else sl
        snr = {s: v["snr_db_vs_reference"] for s, v in mlog.items() if "snr_db_vs_reference" in v}
        rep["stems"] = {"snr_db_vs_reference": snr,
                        "median_mega53": statistics.median(v["mega53"] for v in snr.values()) if snr else None,
                        "median_htdemucs": statistics.median(v["htdemucs"] for v in snr.values()) if snr else None,
                        "median_paired_gain": statistics.median(v["mega53"] - v["htdemucs"] for v in snr.values())
                        if snr else None,
                        "gcc_vs_htdemucs": {s: v.get("gcc_vs_htdemucs") for s, v in mlog.items()}}
    di = LO.SEP_DI[sep]
    renders = sum(json.loads(p.read_text())["renders"] for p in (out() / "renders" / di).glob("*/*.json"))
    rep["renders_used"] = renders
    rep["renders_expected"] = LO.expected_renders(meta["cells"], dis=(di,))
    devs = []
    for c in per:
        f = out() / "scores" / di / c[0] / f"{c[1]}.json"
        fv = json.loads(f.read_text()).get("flac_vs_float_S") or {}
        devs += [v for hv in fv.values() for v in hv.values()]
    rep["flac_vs_float_S"] = {"n": len(devs), "max": max(devs, default=None),
                              "over_tol": sum(v > LO.CHECK_TOL for v in devs)}
    why = LO.complete_1b(len(per), renders)
    a = rep["subsets"][DECLARED]
    gain = a["matched_1b_minus_current"]["cross_half"].get("band_weighted_mean")
    a["reading"] = reading_1c(a["sep_minus_current"]["cross_half"], gain) if why is None else f"refused: {why}"
    K._atomic(out() / f"report-1c-{sep}.json", rep)
    f = lambda s: f"{s['band_weighted_mean']:+.3f} [{s['lo90']:+.3f}, {s['hi90']:+.3f}]" if s.get("lo90") is not None else str(s.get("band_weighted_mean"))  # noqa: E731
    sh = a["share_of_1b_gain"]["cross_half"]
    print(f"{sep} matched cross-half:", f(a["sep"]["cross_half"]), "current:", f(a["current"]["cross_half"]),
          "1b:", f(a["matched_1b"]["cross_half"]), "ceiling:", f(a["ceiling"]))
    print(f"{sep} - current:", f(a["sep_minus_current"]["cross_half"]), "reading:", a["reading"])
    print("share of 1b's gain:", sh, SCOPE)
    for row, rr in rep["bleed_and_leak_rows"].items():
        print(f"  {row}: {sep} - current", f(rr["sep_minus_current"]), "1b - current", f(rr["matched_1b_minus_current"]),
              "share", rr["share_of_1b_gain"])
    print("renders used:", renders, "expected:", rep["renders_expected"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("separate", "blend", "rebuild", "report"))
    ap.add_argument("--sep", default="mega53", choices=LO.SEPARATORS)
    ap.add_argument("--no-wait", action="store_true", help="separate: exit instead of waiting for the gate")
    ap.add_argument("--min-free-gb", type=float, default=None,
                    help="separate: override the memory gate (default 11 GB pruned, 18 GB full)")
    a = ap.parse_args(argv)
    {"separate": lambda: cmd_separate(a.no_wait, a.min_free_gb), "blend": cmd_blend,
     "rebuild": lambda: cmd_rebuild(a.sep), "report": lambda: cmd_report(a.sep)}[a.cmd]()


if __name__ == "__main__":
    main()
