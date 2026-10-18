"""The rebuild-tone step (`docs/rebuild-tone-plan.md`): does lowering C′'s short-time magnitude error
above 2 kHz raise rendered ranking, beside a leak-free long-term EQ and a second seed of the
rebuild-gap study's `rank`? Development only; estimates with 90% band-clustered intervals, no
pass/fail bars. The renders, scores and cells are the rebuild-gap study's stage TR, unchanged
(`learn/rebuild_gap.py`, bound to this step's folder and arms).

    .venv/bin/python -m learn.rebuild_tone gate-report                  # zero renders: the gate's contrasts
    .venv/bin/python -m learn.rebuild_tone curve                        # the leak-free average curve
    .venv/bin/python -m learn.rebuild_tone eq --arm arm_cprime_eq       # C′'s rebuild through it
    .venv/bin/python -m learn.rebuild_tone diag                         # zero renders, descriptive (24 parts)
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.rebuild_tone render --stage tr1 --arms arm_stm,arm_ctl_stm --shard i/3
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.rebuild_tone score --workers 3
    .venv/bin/python -m learn.rebuild_tone report                       # the contrasts + the extension list

The torch side (the loss, the fine-tunes, the gate's measurements, the rebuilds) is
`learn/rebuild_tone_train.py`.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import pathlib
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import knob_ceiling as K  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import rebuild_gap as G  # noqa: E402
from learn import rebuild_tone_train as RT  # noqa: E402

OUT = K.HOME / "learn/rebuild-tone"
TR_OUT = K.HOME / "learn/rebuild-gap"
ARMS = ("arm_stm", "arm_ctl_stm", "arm_stm_eq", "arm_ctl_stm_eq", "arm_cprime_eq", "arm_rank_s1", "arm_ctl_s1")
TR_ARMS = ("arm_rank", "arm_ctl")                    # stage TR's (seed 0), read from the rebuild-gap folder
# J2's groups, in the declared priority order (the disk guard may stop a later one)
GROUPS = {"stm": ("arm_stm", "arm_ctl_stm"), "eq": ("arm_stm_eq", "arm_ctl_stm_eq", "arm_cprime_eq"),
          "seed": ("arm_rank_s1", "arm_ctl_s1")}
EQ_SOURCE = {"arm_stm_eq": "arm_stm", "arm_ctl_stm_eq": "arm_ctl_stm", "arm_cprime_eq": "cprime_ref"}
COMPARATOR_ARM = "arm_rank"                          # `rebuild_gap.comparator` scores the arm comparator under this name
# The declared contrasts (a − b). Primaries first; each group's extension contrasts below.
PRIMARY = (("arm_stm", "cprime_ref"), ("arm_stm", "arm_ctl_stm"), ("arm_stm_eq", "arm_cprime_eq"))
SEED_PRIMARY = (("arm_rank_s1", "cprime_ref"), ("rank_pooled", "cprime_ref"), ("arm_rank_s1", "arm_ctl_s1"),
                ("rank_pooled", "ctl_pooled"))
SECONDARY = (("arm_cprime_eq", "cprime_ref"), ("arm_stm_eq", "arm_ctl_stm_eq"), ("arm_ctl_stm_eq", "arm_cprime_eq"),
             ("arm_stm_eq", "cprime_ref"), ("arm_ctl_stm", "cprime_ref"),
             ("arm_ctl_s1", "cprime_ref"), ("arm_stm", "arm_rank"), ("arm_stm_eq", "arm_rank"),
             ("arm_rank_s1", "arm_rank"))
EXTEND_ON = {"stm": (("arm_stm", "cprime_ref"), ("arm_stm", "arm_ctl_stm")),
             "eq": (("arm_stm_eq", "arm_cprime_eq"), ("arm_cprime_eq", "cprime_ref")),
             "seed": (("arm_rank_s1", "cprime_ref"),)}
# The gate (zero renders, held-out training-fold bands): contrasts of networks on E_st and the rest
GATE_CONTRASTS = (("stm_s0", "cprime"), ("stm_s0", "ctl_s0"), ("ctl_s0", "cprime"), ("rank_s0", "cprime"),
                  ("ctl_tr", "cprime"), ("rank_s1", "cprime"), ("ctl_s1", "cprime"), ("rank_s1", "ctl_s1"))
GATE_METRICS = ("est", "lsd", "coh_1_3k", "coh_3_8k")
CURVE_FOLD = 2                                       # as average-fold2.npy: rows from bands outside K3 fold 2
LAG_TOL, LUFS, LUFS_TOL = 3, -22.9, 0.05


@contextlib.contextmanager
def bound(out=OUT, arms=ARMS):
    """Run the rebuild-gap study's stage-TR machinery on this step's folder and arms. The arm
    comparator's name stays an arm too (`rebuild_gap.comparator` scores it as `arm_rank`)."""
    old = G.OUT, G.ARMS
    G.OUT, G.ARMS = pathlib.Path(out), tuple(dict.fromkeys((*arms, COMPARATOR_ARM)))
    try:
        yield
    finally:
        G.OUT, G.ARMS = old


# --- the gate (zero renders) -----------------------------------------------------------------------------

def gate_contrast(rows_a, rows_b, metric, cluster="band"):
    """Crop-paired a − b on `metric` (rows: {row id: {band, recording, metric...}}), band-clustered
    (or recording-clustered) as `song_readout.bw_stats`."""
    from learn import song_readout as SRD

    d = [(ra[cluster], ra[metric] - rows_b[i][metric]) for i, ra in rows_a.items()
         if i in rows_b and ra.get(metric) is not None and rows_b[i].get(metric) is not None]
    out = SRD.bw_stats(d)
    lobo = out.pop("leave_one_band_out", [])
    out["lobo"] = [min(lobo), max(lobo)] if lobo else None
    out["crops"] = len(d)
    return out


def gate_rows(res, name):
    """Every fold's crops of network `name`, keyed (fold, row)."""
    out = {}
    for f in range(4):
        e = res.get(f"{name}|{f}")
        if e:
            out.update({(f, r["row"]): r for r in e["rows"]})
    return out


def render_stm(gate):
    """The declared gate (amendment 1, a direction rule): `stm`'s arms render if its band-weighted E_st
    on the held-out band crops is below C′'s (the estimate below 0; the interval is reported, not
    required)."""
    c = gate.get("contrasts", {}).get("stm_s0-cprime", {}).get("est", {}).get("band")
    return bool(c and c.get("band_weighted_mean") is not None and c["band_weighted_mean"] < 0)


def cmd_gate_report():
    res = json.loads((OUT / "gate-crops.json").read_text())
    names = sorted({k.split("|")[0] for k in res})
    rows = {n: gate_rows(res, n) for n in names}
    out = {"means": {n: {m: statistics.fmean(r[m] for r in rows[n].values() if r.get(m) is not None) for m in GATE_METRICS}
                     for n in names},
           "crops": {n: len(rows[n]) for n in names}, "contrasts": {}}
    for a, b in GATE_CONTRASTS:
        if a in rows and b in rows:
            out["contrasts"][f"{a}-{b}"] = {m: {c: gate_contrast(rows[a], rows[b], m, c) for c in ("band", "recording")}
                                            for m in GATE_METRICS}
    out["render_stm"] = render_stm(out)
    K._atomic(OUT / "gate.json", out)
    for k, v in out["contrasts"].items():
        e = v["est"]["band"]
        print(f"{k}: E_st {e['band_weighted_mean']:+.3f} [{e['lo90']:+.3f}, {e['hi90']:+.3f}] dB, "
              f"LSD {v['lsd']['band']['band_weighted_mean']:+.3f}", flush=True)
    print("render stm:", out["render_stm"], flush=True)
    return out


# --- the leak-free average curve and the EQ arms (zero renders) --------------------------------------------

def _norm(text):
    return "".join(ch for ch in text.lower() if ch.isalnum())


def own_di(record):
    """The part's own DI file name: the guitar DI its crop record verified (one of its session's
    guitar DIs)."""
    dis = set(record.get("excluded_guitar_dis") or ())
    own = [n for n in (record.get("verified_source_sha256") or {}) if n in dis]
    return own[0] if len(own) == 1 else None


def test_recordings(parts):
    """[(band, song, DI file name or None)] of the 24 parts, from their crop records. A part whose own
    DI can't be named excludes its whole band (None)."""
    out = []
    for slug, p in sorted(parts.items()):
        rp = pathlib.Path(p["crop"]) / "record.json"
        rec = json.loads(rp.read_text()) if rp.exists() else {}
        out.append((p["band"], rec.get("song", ""), own_di(rec)))
    return out


def excluded_files(files, tests):
    """The cache's DI recordings that are a test part's own recording. Per part: the band's files
    with the part's DI file name, in a session folder naming its song; where no folder of the band
    names the song (e.g. Zeno's `MR1003_Zeno_Full`), every same-named file of the band
    (conservative); with no DI name, every file of the band. files: {path: band}."""
    out = set()
    for band, song, name in tests:
        same_band = [f for f, b in files.items() if b == band]
        if name is None:
            out.update(same_band)
            continue
        cand = [f for f in same_band if pathlib.Path(f).name == pathlib.Path(name).name]
        named = [f for f in cand if _norm(song) and _norm(song) in _norm(pathlib.Path(f).parent.name)]
        out.update(named or cand)
    return out


def curve_from(spectra, keep):
    """The power-averaged, mean-removed long-term spectrum of the kept rows (as `direc.fold_average`)."""
    import numpy as np

    s = spectra[keep]
    avg = 10 * np.log10((10 ** (s / 10)).mean(0) + 1e-20)
    return avg - avg.mean()


def cmd_curve():
    import numpy as np

    from learn import direc as D
    from learn import train as TR

    cache = K.HOME / "learn/direc/cache"
    meta = json.loads((cache / "meta.json").read_text())
    S = np.load(cache / "di_spectrum.npy")
    files = RT.recordings()
    ps = {s: p for s, p in K.parts().items() if s not in LO.EXCLUDED}
    tests = test_recordings(ps)
    out_files = excluded_files({files[m["id"]]: m["band"] for m in meta}, tests)
    fold_of, _ = TR.k3_folds()
    out_fold = np.array([fold_of.get(m["band"], -1) != CURVE_FOLD for m in meta])
    ex = np.array([files[m["id"]] in out_files for m in meta])
    cached = {m["band"] for m in meta}
    for band, song, name in tests:                   # every test part with cache rows in its band drops a file
        if band in cached and not any(m["band"] == band and files[m["id"]] in out_files for m in meta):
            raise SystemExit(f"no recording of {band}/{song} ({name}) found in the cache: check the matching")
    keep = out_fold & ~ex
    avg = curve_from(S, keep)
    ref = np.load(cache / f"average-fold{CURVE_FOLD}.npy")
    fr = np.fft.rfftfreq(D.SPEC_N, 1 / D.SR)
    m = (fr >= 80) & (fr <= 8000)
    d = avg[m] - ref[m]
    info = {"rows_kept": int(keep.sum()), "rows_outside_fold2": int(out_fold.sum()), "rows_excluded": int((out_fold & ex).sum()),
            "recordings_excluded": sorted({files[mm["id"]] for mm, e in zip(meta, ex) if e}),
            "parts_without_di_name": sorted(f"{b}/{s}" for b, s, n in tests if n is None),
            "rms_db_vs_average_fold2_80_8k": float(np.sqrt(np.mean((d - d.mean()) ** 2))),
            "max_abs_db_vs_average_fold2_80_8k": float(np.abs(d - d.mean()).max())}
    OUT.mkdir(parents=True, exist_ok=True)
    np.save(OUT / "curve.npy", avg)
    K._atomic(OUT / "curve.json", info)
    print({k: v for k, v in info.items() if k != "recordings_excluded"}, len(info["recordings_excluded"]), "recordings out")


def dep_eq(x, curve):
    """The rebuild-gap study's `dep_eq` on a rebuild's own timeline: EQ'd by curve − its own
    mean-removed long-term shape (±15 dB, zero-phase), at −22.9 LUFS."""
    import numpy as np

    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to, to_lufs

    own = smoothed_spectrum(np.asarray(x, np.float64))
    return to_lufs(eq_to(np.asarray(x, np.float64), curve - (own - own.mean())), LUFS)


def eq_problems(y, src):
    """2a's checks for an EQ arm: the same length, within 3 samples of its source (GCC) and at
    −22.9 ± 0.05 LUFS."""
    import numpy as np

    from learn import rank_margin as RM

    out = []
    if len(y) != len(src) or not np.all(np.isfinite(y)):
        out.append("length or non-finite")
    g = int(RM.gcc_lag(y, src))
    if abs(g) > LAG_TOL:
        out.append(f"GCC against its source {g} samples")
    lu = LO.lufs(y)
    if not math.isfinite(lu) or abs(lu - LUFS) > LUFS_TOL:
        out.append(f"loudness {lu} LUFS")
    return out, g, lu


def source_rebuild(name, slug):
    import numpy as np

    if name == "cprime_ref":
        return np.load(LO.OUT / "rebuilt-ref" / f"{slug}.npy")
    return np.load(OUT / "arms" / name / f"{slug}.npy")


def cmd_eq(arm):
    import numpy as np

    src = EQ_SOURCE[arm]
    if src != "cprime_ref" and not json.loads((OUT / "arms" / src / "check.json").read_text()).get("ok"):
        raise SystemExit(f"{src} has not passed its checks")
    curve = np.load(OUT / "curve.npy")
    d = OUT / "arms" / arm
    d.mkdir(parents=True, exist_ok=True)
    log, bad = {}, {}
    for slug in sorted(s for s in K.parts() if s not in LO.EXCLUDED):
        x = source_rebuild(src, slug)
        y = dep_eq(x, curve)
        np.save(d / f"{slug}.npy", y)
        probs, g, lu = eq_problems(y, x)
        log[slug] = {"source": src, "gcc_vs_source": g, "lufs": lu, "problems": probs}
        if probs:
            bad[slug] = probs
    K._atomic(d / "rebuild-log.json", log)
    K._atomic(d / "check.json", {"ok": not bad, "problems": bad, "missing": []})
    write_arms_check()
    if bad:
        raise SystemExit(f"{arm} fails the checks: {bad}")
    print(f"{arm}: all 24 pass")


def write_arms_check():
    """arms/check.json (which the render command reads): ok only if every built arm's checks passed."""
    ok = {}
    for a in ARMS:
        p = OUT / "arms" / a / "check.json"
        if p.exists():
            ok[a] = bool(json.loads(p.read_text()).get("ok"))
    K._atomic(OUT / "arms" / "check.json", {"ok": bool(ok) and all(ok.values()), "arms": ok})


# --- the 24 parts' rebuilds against the truth (zero renders, descriptive) ------------------------------------

DIAG_SOURCES = {"cprime_ref": None, "arm_rank": TR_OUT, "arm_ctl": TR_OUT, **{a: OUT for a in ARMS}}


def cmd_diag():
    """Each rebuild of the amp track against the measure DI (aligned as stage R, its own rotation
    kept): E_st, LSD and coherence per part; medians and paired differences against C′,
    band-clustered. Descriptive: it selects, stops and gates nothing."""
    import numpy as np

    from learn import song_readout as SRD

    ps = K.parts()
    res = {}
    for name, root in DIAG_SOURCES.items():
        for slug in sorted(s for s in ps if s not in LO.EXCLUDED):
            p = (LO.OUT / "rebuilt-ref" / f"{slug}.npy") if root is None else (root / "arms" / name / f"{slug}.npy")
            if not p.exists():
                continue
            t = K.measure_di(ps[slug])
            x, *_ = G.align(np.load(p), t, ps[slug]["judge_lag"])
            n = min(len(x), len(t))
            res.setdefault(name, {})[slug] = {"est": RT.est(x[:n], t[:n]), "lsd": G.lsd_db(x[:n], t[:n]),
                                             "coh_1_3k": G.coherence(x[:n], t[:n], 1000, 3000),
                                             "coh_3_8k": G.coherence(x[:n], t[:n], 3000, 8000)}
    out = {"per_part": res, "medians": {}, "vs_cprime": {}}
    for name, rows in res.items():
        out["medians"][name] = {m: float(np.median([r[m] for r in rows.values()])) for m in GATE_METRICS}
        if name != "cprime_ref" and "cprime_ref" in res:
            out["vs_cprime"][name] = {}
            for m in GATE_METRICS:
                d = [(ps[s]["band"], r[m] - res["cprime_ref"][s][m]) for s, r in rows.items() if s in res["cprime_ref"]]
                st = SRD.bw_stats(d)
                st.pop("leave_one_band_out", None)
                st["parts_lower"] = sum(v < 0 for _, v in d)
                out["vs_cprime"][name][m] = st
    K._atomic(OUT / "diag.json", out)
    print(json.dumps(out["medians"], indent=1))


# --- renders and scores (stage TR's, bound to this step) ------------------------------------------------------

def cmd_render(shard, stage, arms):
    bad = [a for a in arms if a not in ARMS]
    if not arms:
        raise SystemExit("no arms to render")
    if bad:
        raise SystemExit(f"unknown arms {bad}")
    with bound():
        G.cmd_render(shard, stage, ",".join(arms))


def _score(args):
    with bound(args[3], ARMS):
        return G._score_cell(args)


def cmd_score(workers=3):
    from concurrent.futures import ProcessPoolExecutor

    meta, sig = LO.load_sigma()
    with bound():
        todo = [(a, s, amp, str(OUT)) for a in ARMS for (s, amp) in sorted(sig)
                if G._done(a, s, amp) and not (OUT / "scores" / a / s / f"{amp}.json").exists()]
    with ProcessPoolExecutor(workers) as ex:
        for p, s, a in ex.map(_score, todo):
            print("scored", p, s, a, flush=True)


# --- report ------------------------------------------------------------------------------------------------------

def high_bleed(table=None):
    """Parts left out of the no-high-bleed row: a half flagged high, or no bleed record
    (`local_objective_1c`'s cell rule)."""
    from learn import local_objective_1c as C

    bt = table if table is not None else C.load_bleed_table()
    ps = [s for s in K.parts() if s not in LO.EXCLUDED]
    return sorted(s for s in ps if s not in bt or any(h.get("flag") == "high" for h in bt[s]["halves"].values()))


def brief(a):
    keys = ("band_weighted_mean", "lo90", "hi90", "bands", "bands_positive", "bands_negative", "cells",
            "part_weighted", "per_amp", "per_class")
    out = {k: a.get(k) for k in keys}
    lobo = a.get("leave_one_band_out") or []
    out["lobo"] = [min(lobo), max(lobo)] if lobo else None
    return out


def pooled(rows_a, rows_b):
    """Per cell, the mean of two arms' values (the two seeds), where both exist."""
    return {k: (*rows_a[k][:3], (rows_a[k][3] + rows_b[k][3]) / 2) for k in rows_a
            if k in rows_b and rows_a[k][3] is not None and rows_b[k][3] is not None}


def all_rows(cells):
    """Cell rows (cross-half and reliable-pair accuracy) of every arm here and stage TR's two, plus the
    truth, C′ and the seed-pooled rows."""
    with bound(TR_OUT, TR_ARMS):
        rows = G.cell_rows(list(TR_ARMS), cells)
    with bound():
        mine = G.cell_rows(list(ARMS), cells)
    rows.update({k: v for k, v in mine.items() if k.split(":")[0] in ARMS})
    for sfx in ("", ":rpa"):
        if f"arm_rank{sfx}" in rows and f"arm_rank_s1{sfx}" in rows:
            rows[f"rank_pooled{sfx}"] = pooled(rows[f"arm_rank{sfx}"], rows[f"arm_rank_s1{sfx}"])
        if f"arm_ctl{sfx}" in rows and f"arm_ctl_s1{sfx}" in rows:
            rows[f"ctl_pooled{sfx}"] = pooled(rows[f"arm_ctl{sfx}"], rows[f"arm_ctl_s1{sfx}"])
    return rows


def contrast(rows, a, b, cells, no_high=()):
    """a − b on `cells`: band-weighted with its interval, LOBO, part-weighted, per amp and class,
    reliable-pair accuracy, the no-high-bleed row, the share of C′'s gap and truth − a."""
    from learn import local_objective_1c as C

    if a not in rows or b not in rows:
        return None
    ra = {k: v for k, v in rows[a].items() if k in cells}
    rb = {k: v for k, v in rows[b].items() if k in cells}
    d = LO.paired(ra, rb)
    if not d:
        return None
    out = brief(LO.agg(d))
    out["rpa"] = brief(LO.agg(LO.paired({k: v for k, v in rows[f"{a}:rpa"].items() if k in cells},
                                        {k: v for k, v in rows[f"{b}:rpa"].items() if k in cells})))
    out["no_high_bleed"] = brief(LO.agg({k: v for k, v in d.items() if k[0] not in no_high}))
    if b == "cprime_ref":
        gap = LO.paired({k: rows["truth"][k] for k in d}, rb)
        out["share_of_gap"] = C.share(d, gap)
    out["truth_minus_a"] = brief(LO.agg(LO.paired({k: rows["truth"][k] for k in d}, ra)))
    return out


def complete(rows, name, cells):
    return name in rows and all(c in rows[name] for c in cells)


def extension(report, ratio):
    """A group renders on the other 48 cells if one of its declared contrasts meets stage TR's rule
    (positive, its J1 interval containing 0, the interval narrowed by the stored ratio excluding 0).
    In GROUPS' priority order."""
    out = []
    for g, cs in EXTEND_ON.items():
        if any(G.extends(report.get("r1", {}).get(f"{a}-{b}") or {}, ratio) for a, b in cs):
            out.append(g)
    return [g for g in GROUPS if g in out]


def j2_arms(group, rendered):
    """The arms a group renders at J2: those of the group that rendered at J1."""
    return [a for a in GROUPS[group] if a in rendered]


def training_summary():
    """Each fine-tune's kept step, steps run, skipped steps and recoveries (a fold whose best is step 0
    is C′, and its control too)."""
    out = {}
    for p in sorted(OUT.glob("models-*-s*-f*/result.json")):
        r = json.loads(p.read_text())
        out[p.parent.name] = {k: r.get(k) for k in ("best_step", "best", "steps_run", "skipped", "recoveries", "minutes")}
        out[p.parent.name]["step0"] = r.get("step0")
    return out


def renders_used():
    """Renders here: each record's `renders` (its warm-up included) plus 2 per comparator file."""
    tot, by = 0, {}
    for p in (OUT / "renders").glob("*/*/*.json"):
        r = json.loads(p.read_text())
        by[r["probe"]] = by.get(r["probe"], 0) + r.get("renders", 0)
        tot += r.get("renders", 0)
    comp = 2 * len(list((OUT / "comparator").glob("*/*.json")))
    return {"by_arm": by, "comparator": comp, "total": tot + comp}


def cmd_report():
    r1 = G.r1_cells()
    every = sorted(set(r1) | set(G.r2_cells()))
    rows = all_rows(every)
    nh = set(high_bleed())
    out = {"r1": {}, "all72": {}, "fidelity": {}, "no_high_bleed_parts": sorted(nh)}
    for a, b in (*PRIMARY, *SEED_PRIMARY, *SECONDARY):
        c = contrast(rows, a, b, set(r1), nh)
        if c:
            out["r1"][f"{a}-{b}"] = c
        if complete(rows, a, every) and complete(rows, b, every):
            out["all72"][f"{a}-{b}"] = contrast(rows, a, b, set(every), nh)
    for n in ("truth", "cprime_ref", *TR_ARMS, *ARMS, "rank_pooled", "ctl_pooled"):
        if n in rows:
            out["fidelity"][n] = brief(LO.agg({k: v for k, v in rows[n].items() if k in set(r1)}))
    out["narrowing"] = G.narrowing_ratio()
    out["extend"] = extension(out, out["narrowing"]["ratio"])
    out["j1_arms"] = [a for a in ARMS if complete(rows, a, r1)]
    out["j2_arms"] = {g: j2_arms(g, out["j1_arms"]) for g in out["extend"]}
    out["training"] = training_summary()
    out["renders"] = renders_used()
    K._atomic(OUT / "report.json", out)
    for k, v in out["r1"].items():
        print(f"{k}: {v['band_weighted_mean']:+.3f} [{v['lo90']:+.3f}, {v['hi90']:+.3f}] "
              f"bands {v['bands_positive']}/{v['bands_negative']}", flush=True)
    print("extend:", out["extend"], flush=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gate-report")
    sub.add_parser("curve")
    e = sub.add_parser("eq")
    e.add_argument("--arm", choices=tuple(EQ_SOURCE), required=True)
    sub.add_parser("diag")
    r = sub.add_parser("render")
    r.add_argument("--shard", default="0/1")
    r.add_argument("--stage", default="tr1", choices=("tr1", "tr2"))
    r.add_argument("--arms", required=True)
    s = sub.add_parser("score")
    s.add_argument("--workers", type=int, default=3)
    sub.add_parser("report")
    sub.add_parser("arms-check")
    j = sub.add_parser("j2-arms")
    j.add_argument("--group", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "gate-report":
        cmd_gate_report()
    elif a.cmd == "curve":
        cmd_curve()
    elif a.cmd == "eq":
        cmd_eq(a.arm)
    elif a.cmd == "diag":
        cmd_diag()
    elif a.cmd == "render":
        i, n = a.shard.split("/")
        cmd_render((int(i), int(n)), a.stage, [x for x in a.arms.split(",") if x])
    elif a.cmd == "score":
        cmd_score(a.workers)
    elif a.cmd == "report":
        cmd_report()
    elif a.cmd == "arms-check":
        write_arms_check()
    elif a.cmd == "j2-arms":
        print(",".join(json.loads((OUT / "report.json").read_text())["j2_arms"][a.group]))


if __name__ == "__main__":
    main()
