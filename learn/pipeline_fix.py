"""The pipeline fix plan's tests and its common retrain recipe (docs/pipeline-fix-plan.md; ledger `pipeline-fix`).

The plan closes each finding of the pipeline review (docs/ml-pipeline-review.md). This module holds its tests, named
after the review's (P1-P7), and the recipe every retrain in the plan shares. Outputs go to
`~/ndsp-presets/learn/trusted-data/pipeline-fix/` only; every other stage's folder is read, never written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MAIN -m learn.pipeline_fix p5                  # zero renders: S re-picked without V-real's parts
    $MAIN -m learn.pipeline_fix dirty-doubles       # zero renders: which DT doubles differ from their target's label
    $TORCH_PY -m learn.pipeline_fix p6              # inference only: D_CC on FS_CC, the coin against the class
    $MAIN -u -m learn.pipeline_fix render-doubles --control     # phase 1b: the positive control first
    $MAIN -u -m learn.pipeline_fix render-doubles --shard k/3   # phase 1b: the doubles re-rendered (renders)
    $MSST -m learn.pipeline_fix build-doubles --device mps      # phase 1b: their mixes and stems
    $MAIN -m learn.pipeline_fix build-inputs --shard k/3        # P2a's and P2b's features (zero renders)
    $TORCH_PY -m learn.pipeline_fix p1 --rung a|d               # P1: memorise 200 examples (minutes of MPS)
    $TORCH_PY -m learn.pipeline_fix train --rung a [--frac F | --sections F | --fold k | --aug]   # the ladder
    $MAIN -m learn.pipeline_fix build-dfix-real --shard k/n     # D_fix: the real rows in backings (zero renders)
    $MAIN -m learn.pipeline_fix build-dfix-real --reads-only    # ... and the read units with no row (read 2's inputs)
    $TORCH_PY -m learn.pipeline_fix train --dfix --rung b [--real-fold k] --seed S      # D_fix, D_fix_k
    $TORCH_PY -m learn.pipeline_fix train --dfix --dfix-share p33 --rung b [--real-fold k] --seed S   # D_p (F39)
    $MAIN -m learn.pipeline_fix sound-recheck --names TAG [--n 20]   # stored renders rendered again, hashes compared
    $TORCH_PY -m learn.pipeline_fix dfix-vreal-predict --which best      # read 3's answers on V-real (zero renders)
    $MAIN -u -m learn.pipeline_fix dfix-vreal-render --shard k/3         # read 3's renders (hashes in the ledger first)
    $MAIN -m learn.pipeline_fix dfix-vreal-report --label dfix-vreal     # read 3's rows (zero renders)
    $TORCH_PY -m learn.pipeline_fix ft-vreal-predict          # FT on V-real (after phase_ft_carry; zero renders)
    $MAIN -u -m learn.pipeline_fix ft-vreal-render --shard k/3    # FT's V-real renders (hashes in the ledger first)
    $MAIN -m learn.pipeline_fix ft-vreal-report --label ft-vreal  # FT's V-real rows (zero renders)
    $MAIN -m learn.pipeline_fix ft-groups                     # FT's BKS answers split by control group (zero renders)
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
import time

from learn import pipeline_review as PR

DATA = PR.DATA
REPO = PR.REPO
OUT = "learn/trusted-data/pipeline-fix"
LEDGER_ID = "pipeline-fix"
PLAN = "docs/pipeline-fix-plan.md"
VREAL_BANDS = frozenset(b for b, _ in PR.VREAL.values())

# t(0.95, df): the 90% two-sided interval's t value, df 1-30 (beyond 30 the normal's 1.645 is within 2%).
T_95 = {1: 6.3138, 2: 2.92, 3: 2.3534, 4: 2.1318, 5: 2.015, 6: 1.9432, 7: 1.8946, 8: 1.8595, 9: 1.8331, 10: 1.8125,
        11: 1.7959, 12: 1.7823, 13: 1.7709, 14: 1.7613, 15: 1.7531, 16: 1.7459, 17: 1.7396, 18: 1.7341,
        19: 1.7291, 20: 1.7247, 21: 1.7207, 22: 1.7171, 23: 1.7139, 24: 1.7109, 25: 1.7081, 26: 1.7056,
        27: 1.7033, 28: 1.7011, 29: 1.6991, 30: 1.6973}


def t95(df):
    return T_95.get(df, 1.6449) if df >= 1 else None


# --- pure helpers (tested in tests/test_pipeline_fix.py) -------------------------------------------------------

def clustered(rows):
    """rows: [(cluster, part, value)] -> parts averaged within a cluster, then the mean of cluster means, with the
    90% cluster t interval (df = clusters - 1), the part-weighted mean, and leave-one-cluster-out means. The
    review's `band_weighted` rule with t for any df."""
    by_part = {}
    for c, p, v in rows:
        by_part.setdefault((c, p), []).append(v)
    if not by_part:
        return {"mean": None, "lo90": None, "hi90": None, "clusters": 0, "parts": 0}
    by_c = {}
    for (c, _), vs in by_part.items():
        by_c.setdefault(c, []).append(statistics.fmean(vs))
    means = {c: statistics.fmean(v) for c, v in by_c.items()}
    m = statistics.fmean(means.values())
    g = len(means)
    half = t95(g - 1) * statistics.stdev(means.values()) / math.sqrt(g) if g > 1 else None
    parts = {p: statistics.fmean(vs) for (_, p), vs in sorted(by_part.items())}
    return {"mean": m, "lo90": None if half is None else m - half, "hi90": None if half is None else m + half,
            "clusters": g, "clusters_negative": sum(v < 0 for v in means.values()),
            "clusters_positive": sum(v > 0 for v in means.values()),
            "part_weighted": statistics.fmean(parts.values()), "parts": len(parts),
            "parts_negative": sum(v < 0 for v in parts.values()),
            "leave_one_out": {c: statistics.fmean(v for k, v in means.items() if k != c) for c in sorted(means)}
            if g > 1 else {}, "per_cluster": dict(sorted(means.items())), "per_part": parts}


def start_rules(files, pinned, exclude):
    """The start rule (`pipeline_review.pick_start`) per class and amp on the pinned development parts of that class,
    less `exclude` (slugs). -> {cls: {"parts": n, "per_amp": {amp: (preset, median, parts used)}}}."""
    out = {}
    for cls in ("clean", "crunch"):
        parts = sorted(p for p, v in pinned.items() if v["gain_class"] == cls and p not in exclude)
        out[cls] = {"parts": len(parts),
                    "per_amp": {amp: PR.pick_start(files, parts, amp) for amp in PR.AMPS}}
    return out


def s_prime_rows(files, vreal, choice, rules):
    """S' - S on V-real per (part, amp, half) for every V-real part whose class's pick changed for that amp, from the
    stored `flat` distances: ln(d_S' / d_S). A part with no stored distance for both presets on its V-real clip is
    listed as missing (it needs renders). -> (rows [(band, slug, value)] with 0 where S' = S, missing [(slug, amp)])."""
    rows, missing = [], []
    for slug, (band, cls) in sorted(vreal.items()):
        for amp in PR.AMPS:
            s = choice[cls]["presets"][amp]
            sp = rules[cls]["per_amp"][amp][0]
            if sp is None or sp == s:
                rows += [(band, slug, 0.0), (band, slug, 0.0)]
                continue
            # T3's own crop of It Was My Fault ElecGtr1 (90-100 s) is not the clip the distance files hold (12.5-22.5 s)
            src = None if slug in PR.IN_GROUP_S else next((f[slug] for f in files if slug in f), None)
            got = []
            for h in ("A", "B"):
                d = (src or {}).get(f"flat|{amp}|measfix_{h}", {})
                if s in d and sp in d:
                    got.append(math.log(d[sp][0] / d[s][0]))
            if len(got) == 2:
                rows += [(band, slug, v) for v in got]
            else:
                missing.append((slug, amp))
    return rows, missing


# --- I/O ------------------------------------------------------------------------------------------------------------

def out_dir(root=DATA):
    return pathlib.Path(root) / OUT


def save(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=False, default=str) + "\n")
    tmp.replace(path)


def ledger_entry():
    d = json.loads((REPO / "docs" / "dev-test-ledger.json").read_text())
    return next((t for t in d["tests"] if t["test_id"] == LEDGER_ID), None)


def require(phase_key):
    """Real runs refuse unless the ledger's `pipeline-fix` entry declares this phase."""
    e = ledger_entry()
    if not e or phase_key not in e:
        raise SystemExit(f"the ledger's {LEDGER_ID} entry has no {phase_key}: declare it before running")
    return e


# --- P5: S's home advantage (zero renders) ---------------------------------------------------------------------------

def cmd_p5(args):
    """Both start rules re-run without V-real's parts (then without V-real's bands); S' - S on V-real from the stored
    distances where the pick changed."""
    require("phase_1")
    root = pathlib.Path(args.data_dir)
    choice = {c: PR._json(REPO / f"docs/{c}-baseline-choice.json") for c in ("clean", "crunch")}
    pinned = PR._json(REPO / "docs/sound-desc-test-parts.json")["parts"]
    files = [PR._json(root / f"learn/direc/{n}/distances.json") for n in ("rescore", "songs-check")]
    full = start_rules(files, pinned, set())
    for cls in full:
        for amp, (best, _, n) in full[cls]["per_amp"].items():
            if best != choice[cls]["presets"][amp] or n != choice[cls]["parts_used"][amp]:
                raise SystemExit(f"{cls} {amp}: the rule does not reproduce the stored choice")
    variants = {"without V-real's parts": set(PR.VREAL),
                "without V-real's bands": {p for p, v in pinned.items() if v["band"] in VREAL_BANDS}}
    out = {"plan": PLAN, "test": "P5 (review step 36)", "ledger": f"{LEDGER_ID} phase_1",
           "rule": "pipeline_review.pick_start on docs/sound-desc-test-parts.json; reproduces both stored choices",
           "variants": {}}
    for name, excl in variants.items():
        rules = start_rules(files, pinned, excl)
        rows, missing = s_prime_rows(files, PR.VREAL, choice, rules)
        per_class = {cls: clustered([r for r in rows if PR.VREAL[r[1]][1] == cls]) for cls in ("clean", "crunch")}
        miss = set(missing)
        stored = [r for r in rows if not any((r[1], a) in miss for a in PR.AMPS)]
        v = {"excluded": len(excl & set(pinned)),
             "picks": {cls: {"parts": r["parts"], "per_amp": {
                 amp: {"S": choice[cls]["presets"][amp], "picked": b, "median": m, "parts_used": n,
                       "changed": b is not None and b != choice[cls]["presets"][amp]}
                 for amp, (b, m, n) in r["per_amp"].items()}} for cls, r in rules.items()},
             "s_prime_minus_s_on_vreal": clustered(rows) if not missing else None,
             "per_class": per_class if not missing else None,
             "missing_need_renders": [f"{s}|{a}" for s, a in missing],
             "partial_without_missing_parts": {
                 "parts_left_out": sorted({sl for sl, _ in missing}), "all": clustered(stored),
                 "per_class": {cls: clustered([r for r in stored if PR.VREAL[r[1]][1] == cls])
                               for cls in ("clean", "crunch")}} if missing else None}
        out["variants"][name] = v
        print(f"== {name}: {v['excluded']} pinned parts left out")
        for cls, r in v["picks"].items():
            for amp, p in r["per_amp"].items():
                print(f"  {cls:6s} {amp:6s} parts {p['parts_used']:2d}  {'CHANGED' if p['changed'] else 'same   '} "
                      f"{p['picked']}")
        if missing:
            print(f"  S' - S cannot be read from stored distances for {len(missing)} (part, amp): {missing}")
            pp = v["partial_without_missing_parts"]
            for nm, c in [("all", pp["all"])] + sorted(pp["per_class"].items()):
                if c["mean"] is not None:
                    iv = "" if c["lo90"] is None else f" [{c['lo90']:+.4f}, {c['hi90']:+.4f}]"
                    print(f"  partial S' - S ({nm}, without {pp['parts_left_out']}): {c['mean']:+.4f}{iv} "
                          f"({c['clusters']} bands, {c['clusters_positive']} worse; part-weighted "
                          f"{c['part_weighted']:+.4f}, {c['parts']} parts)")
        else:
            c = v["s_prime_minus_s_on_vreal"]
            print(f"  S' - S on V-real-11: {c['mean']:+.4f} [{c['lo90']:+.4f}, {c['hi90']:+.4f}] "
                  f"({c['clusters']} bands; part-weighted {c['part_weighted']:+.4f})")
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save(out_dir(root) / "p5.json", out)
    print("P5 DONE")


# --- the dirty-double list (zero renders) ----------------------------------------------------------------------------

DOUBLE_SWITCHES = ("drive1", "drive2", "compressor", "reverb", "delay", "tremolo", "doubler", "gate")


def double_status(x):
    """How an example's DT doubles sit against its label: None without a DT double, else the switches (the review's
    eight) whose state differs between the double's render setting (the plan's `core`) and the target's label
    (`settings`), and how many stored settings differ in all."""
    if not any(o.get("dt") for o in x.get("others", [])):
        return None
    core, lab = x["core"], x["settings"]
    sw = [k for k in DOUBLE_SWITCHES if PR.on(core.get(PR.SWITCHES[k])) != PR.on(lab.get(PR.SWITCHES[k]))]
    return {"switches_differ": sw, "settings_differ": sum(core.get(k) != v for k, v in lab.items())}


def cmd_dirty_doubles(args):
    require("phase_1")
    root = pathlib.Path(args.data_dir)
    d = PR.Data(root)
    kept = d.cc_kept()
    st = {i: double_status(x) for i, x in kept.items()}
    with_dt = {i: s for i, s in st.items() if s is not None}
    by_switch = {k: sum(k in s["switches_differ"] for s in with_dt.values()) for k in DOUBLE_SWITCHES}
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_1", "kept": len(kept), "with_dt_double": len(with_dt),
           "any_switch_differs": sum(bool(s["switches_differ"]) for s in with_dt.values()),
           "pedal_switch_differs": sum(any(k in s["switches_differ"] for k in ("drive1", "drive2", "compressor"))
                                       for s in with_dt.values()),
           "by_switch": by_switch,
           "settings_differ": PR.quantiles([s["settings_differ"] for s in with_dt.values()]),
           "by_set": {n: sum(kept[i]["set"] == n for i in with_dt) for n in ("train", "fs")},
           "examples": {str(i): s for i, s in sorted(with_dt.items())},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    save(out_dir(root) / "dirty-doubles.json", out)
    print(f"{out['with_dt_double']} of {out['kept']} kept examples have a DT double; a switch differs in "
          f"{out['any_switch_differs']}, a pedal switch in {out['pedal_switch_differs']}; by switch {by_switch}; "
          f"stored settings differing {out['settings_differ']}")
    print("DIRTY-DOUBLES DONE")


# --- P6 and P7: D_CC's stored models, inference only ----------------------------------------------------------------

def auc(scores, labels):
    """Mann-Whitney AUC (ties count half); None without both classes."""
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for q in neg:
            wins += 1.0 if p > q else 0.5 if p == q else 0.0
    return wins / (len(pos) * len(neg))


def cluster_boot(items, stat, clusters, n=1000, seed=20261031):
    """A 90% percentile interval of stat(items) resampling whole clusters (items' cluster ids in `clusters`)."""
    import random

    rng = random.Random(seed)
    ids = sorted(set(clusters))
    by = {c: [it for it, k in zip(items, clusters) if k == c] for c in ids}
    vals = []
    for _ in range(n):
        pick = [it for _ in ids for it in by[rng.choice(ids)]]
        v = stat(pick)
        if v is not None:
            vals.append(v)
    if len(vals) < n // 2:
        return None, None
    vals.sort()
    return vals[int(0.05 * (len(vals) - 1))], vals[int(0.95 * (len(vals) - 1))]


def _dcc():
    """D_CC's two stored models, its fit (constant and pull), and its FS_CC rows and feature files."""
    import argparse as ap

    from learn import cc_readout as CR
    from learn import direct_stems as DS
    from learn import verify_tracks as V

    args = ap.Namespace(arm="D_CC", out=None, smoke=False)
    spec = CR.spec_of("D_CC")
    root = V.out_root(args)
    fit = CR.load_fit(root, "D_CC")
    nets, recs = CR.load_models(root, "D_CC", spec)
    if fit["model"]["models"] != CR.model_shas(recs):
        raise SystemExit("D_CC: the fit was made with other models")
    tr_rows, fs_rows, files = spec["fit_rows"](root, DS.Ctx(quiet=True), None)
    return root, spec, fit, nets, recs, tr_rows, fs_rows, files


def sw_index(path):
    from learn import full_space as F

    D = F.by_name()
    module, key = path.split("/")
    return next(j for j, n in enumerate(F.SW) if (D[n].module, D[n].key) == (module, key))


def fs_readouts(nets, rows, files, cls_key):
    """Per FS row, the pooled readout over both halves with the class input taken from row[cls_key]."""
    from learn import full_space as F
    from learn import trusted_data_t3 as T3

    enc = T3.encode_for(T3.FULL)
    rr = [dict(r, base=r[cls_key]) for r in rows]
    X, C, Y, who = T3.fs_tensors(rr, files, lambda lab: enc(lab)[:6])
    outs = F.run_nets(nets, X, C)
    per = {}
    for n, i in enumerate(who):
        per.setdefault(i, []).append(F.readout([o[n] for o in outs]))
    labels = {}
    for n, i in enumerate(who):
        labels[i] = tuple(z[n] for z in Y)
    return per, labels


def cmd_p6(args):
    """P6 (review step 5), FS half: D_CC's knob error on FS_CC with the coin it was trained on as the class input,
    against the section's class (as V-real feeds it). Inference only; V-real is not read."""
    import numpy as np

    require("phase_1")
    root, spec, fit_, nets, recs, tr_rows, fs_rows, files = _dcc()
    ex = {x["i"]: x for x in json.loads((root / "cc/plan.json").read_text())["examples"]}
    fs = [dict(r, cls=ex[r["i"]]["cls"]) for r in fs_rows]
    per_b, lab = fs_readouts(nets, fs, files, "base")
    per_c, _ = fs_readouts(nets, fs, files, "cls")
    rows, n_differ = [], 0
    for r in fs:
        c, cmask = lab[r["i"]][0], lab[r["i"]][1] > 0
        if not cmask.any() or r["base"] == r["cls"]:
            continue
        n_differ += 1
        e = [float(np.mean(np.mean([np.abs(q["a2"] - c) for q in per[r["i"]]], axis=0)[cmask]))
             for per in (per_b, per_c)]
        rows.append((r["band"], r["section"], e[1] - e[0]))
    row = clustered(rows)
    out = {"plan": PLAN, "test": "P6 (review step 5), FS half", "ledger": f"{LEDGER_ID} phase_1",
           "models": CR_models(recs), "fs_examples": len(fs), "coin_differs_from_section_class": n_differ,
           "knob_error_section_class_minus_coin": {k: row.get(k) for k in (
               "mean", "lo90", "hi90", "clusters", "clusters_negative", "clusters_positive", "part_weighted",
               "parts", "leave_one_out")},
           "reading": "knob error in unit range: the unpulled seed-mean medians over each example's sounding knobs, "
                      "both halves; sections are the parts, bands the clusters. Positive: the model reads worse when "
                      "told the section's class than the coin it was trained on",
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    save(out_dir() / "p6.json", out)
    k = out["knob_error_section_class_minus_coin"]
    print(f"FS_CC: {n_differ} of {len(fs)} examples whose coin differs from the section's class; knob error, the "
          f"section's class - the coin: {k['mean']:+.4f} [{k['lo90']:+.4f}, {k['hi90']:+.4f}] ({k['clusters']} bands, "
          f"{k['clusters_positive']} worse)")
    print("P6 DONE")


def CR_models(recs):
    return {str(r["seed"]): r["model_sha256"] for r in recs}


# --- P2's inputs (zero renders): the target at its level in the mix, and the target in its backing alone ---------------

RUNG_KINDS = {"a": "tgtl-cc", "b": "mixb-cc", "c": "mix-cc", "d": "xlance_g-cc"}   # the feature file of each rung
DT_KINDS = {"c": "mix-ccdt", "d": "xlance_g-ccdt"}  # rungs c and d of a doubled example: its re-rendered doubles


OWN_KINDS = ("a", "b")                              # rungs whose features this plan builds (pipeline-fix/inputs/)


def input_path(root, i, kind):
    return out_dir(root) / "inputs" / f"{i // 1000:04d}" / f"{i:07d}-{kind}.npz"


def rung_path(croot, rung, doubled=frozenset(), root=DATA):
    """i -> the feature file rung `rung` reads for example i: this plan's own inputs for P2a and P2b, D_CC's stored
    mix and stem for P2c and P2d, the doubles fix's files for a doubled example."""
    from learn import trusted_data as T

    def f(i):
        if rung in OWN_KINDS:
            return input_path(root, i, RUNG_KINDS[rung])
        if rung in DT_KINDS and i in doubled:
            return dt_ex(root, i, DT_KINDS[rung])
        return T.ex_path(croot, "cc", i, RUNG_KINDS[rung])
    return f


def rung_mixes(y, others, stems, x, gains, master):
    """The rungs' audio from one example's stored parts: (a) the target at its gain in the mix, (b) the target and the
    non-guitar backing at the mix's gains with no other guitar (rendered or recorded), mastered as the mix was, and
    (c) the full mix rebuilt (a parity check against the stored mix). `master(sig)` applies the example's mastering
    draw (identity when the draw was unmastered). gains: {gb, ga} as stored."""
    ga, gb = 10 ** (gains["ga"] / 20), 10 ** (gains["gb"] / 20)
    a = y * ga
    b = master((y + stems * gb) * ga)
    c = master((y + (others + stems) * gb) * ga)
    return a, b, c


def cmd_build_inputs(args):
    """P2a's and P2b's features for every kept D_CC example (CPU, zero renders): the stored target and other-guitar
    FLACs, the session's non-guitar stems at the stored gains; the stored mix rebuilt first as a parity check."""
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import song_aug as SA
    from learn import trusted_data as T

    require("phase_2")
    a = argparse.Namespace(out=None, smoke=False)
    root = CB.V.out_root(a)
    plan = CB.load_plan(a)
    tr, fs, _, unbuilt = CB.sets(root, plan)
    if unbuilt:
        raise SystemExit("D_CC's build is not finished")
    ex = {x["i"]: x for x in plan["examples"]}
    rend, built = T.rows_of(root, CB.STAGE, "render"), T.rows_of(root, CB.STAGE, "build")
    ctx = CB.ctx_for(a)
    stems = T.Stems(ctx)
    k, n = args.shard
    todo = sorted((i for i in tr + fs if i % n == k), key=lambda i: (ex[i]["section"], i))   # the stems cache by section
    dt_rows, dt_new = {}, {}
    if args.doubled:                               # after phase 1b: P2b of the doubled examples from their new mix
        for f in sorted((dt_root() / "rows").glob("build-*.jsonl")):
            dt_rows.update({r["i"]: r for r in DS.read_jsonl(f) if not r.get("refused")})
        for f in sorted((dt_root() / "rows").glob("render-*.jsonl")):
            dt_new.update({r["i"]: r for r in DS.read_jsonl(f)})
    parity = []
    t0 = time.time()
    for m, i in enumerate(todo):
        pa, pb = (input_path(DATA, i, RUNG_KINDS[r]) for r in OWN_KINDS)
        redo = args.doubled and i in dt_rows
        if pa.exists() and pb.exists() and not redo:
            continue
        if args.doubled and not redo:
            continue
        x, rw, bw = ex[i], rend[i], built[i]
        y = G.read_flac(T.flac_path(root, CB.STAGE, i, "target"), rw["target"]["scale"], rw["target"]["sha256"])
        if redo:                                   # P2c's new mix: the re-rendered doubles and their recomputed gains
            nw, bw = dt_new[i], dt_rows[i]
            oth = G.read_flac(dt_flac(DATA, i), nw["others_file"]["scale"], nw["others_file"]["sha256"])
            if abs(bw["gains_db"]["ga"] - built[i]["gains_db"]["ga"]) > 1e-9:
                raise SystemExit(f"{i}: the overall gain changed with the new doubles")
        else:
            oth = G.read_flac(T.flac_path(root, CB.STAGE, i, "others"), rw["others_file"]["scale"],
                              rw["others_file"]["sha256"])
        voc = x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"]
        full = stems.get(x["section"], T.backing_tracks(x, voc))
        bare = stems.get(x["section"], list(x["stems"]["v" if voc else "n"]))   # no recorded stand-in guitar
        standins = full - bare

        def master(sig, i=i, x=x):
            mastered, mrng = DS.master_draw(i)
            return SA.compress(sig, mrng) if mastered else sig

        sa, sb, sc = rung_mixes(np.asarray(y, np.float64), np.asarray(oth, np.float64) + standins, bare, x,
                                bw["gains_db"], master)
        mm, ml, _ = DS.half_features(sc)
        stored = np.load(dt_ex(DATA, i, "mix-ccdt") if redo else T.ex_path(root, CB.STAGE, i, "mix-cc"))
        dev = max(int(np.max(np.abs(mm[h].astype(int) - stored[f"m{h}"].astype(int)))) for h in "AB")
        parity.append(dev)
        if dev > 1:
            raise SystemExit(f"{i}: the rebuilt mix differs from the stored one by {dev} grid steps")
        fa, la, _ = DS.half_features(sa)
        fb, lb, _ = DS.half_features(sb)
        DS._save_npz(pa, sA=fa["A"], sB=fa["B"], lufs=[la["A"], la["B"]])
        DS._save_npz(pb, sA=fb["A"], sB=fb["B"], lufs=[lb["A"], lb["B"]])
        if m % 100 == 0:
            print(f"inputs {m + 1}/{len(todo)}: {(time.time() - t0) / (m + 1):.2f} s per example; parity max "
                  f"{max(parity)} grid steps", flush=True)
    print(f"BUILD-INPUTS DONE {k}/{n}: {len(parity)} built; the rebuilt mix within {max(parity or [0])} grid steps "
          "of the stored one")


# --- the common recipe (written in phase 1; P1 and the rungs run it) -------------------------------------------------

NS_SESSIONS = ("cambridge/AdamBuckley_DragMeDown_Full", "sets-1-2/TheMaybeNextYears_OneFlipFlop_Full")
SUBSET_N = 300                     # the fixed training subset read in eval mode each epoch
SUBSET_SEED = 20261031
P1_N = 200
CURVE_SEED = 20261032              # the learning curve's nested draw within sections
SEEDS = (20261042, 20261043)


def session_of(section):
    """'set/Session_Full/file.wav@start' -> 'set/Session_Full'."""
    return section.split("@")[0].rsplit("/", 1)[0]


def runaway_ids():
    """D_CC's 64 runaway targets (the 2026-10-30 scan's clear and likely tiers, `cc_drive_page.RUNAWAY`)."""
    from learn import cc_drive_page as CD

    return set(CD.RUNAWAY)


def recipe_split(kept, tr_ids, fs_ids, drop):
    """The recipe's sets from D_CC's kept examples: NS = every kept example of the held-out songs; training = D_CC's
    training examples of the other songs; FS = FS_CC's of the other songs; `drop` (runaway and dirty) out of all.
    -> {"train", "ns", "fs": sorted ids, "dropped": {set: count}}."""
    held = lambda i: session_of(kept[i]["section"]) in NS_SESSIONS   # noqa: E731
    out = {"ns": sorted(i for i in tr_ids + fs_ids if held(i) and i not in drop),
           "train": sorted(i for i in tr_ids if not held(i) and i not in drop),
           "fs": sorted(i for i in fs_ids if not held(i) and i not in drop)}
    out["dropped"] = {"train": sum(1 for i in tr_ids if not held(i) and i in drop),
                      "fs": sum(1 for i in fs_ids if not held(i) and i in drop),
                      "ns": sum(1 for i in tr_ids + fs_ids if held(i) and i in drop)}
    return out


def nested_subset(ids, section_of, frac, seed=CURVE_SEED):
    """A fraction of `ids` drawn within each section (at least one per section), nested across fractions: each
    section's examples in one seeded order, the first ceil(frac * n) kept."""
    import random

    by = {}
    for i in sorted(ids):
        by.setdefault(section_of[i], []).append(i)
    out = []
    for sec, xs in sorted(by.items()):
        rng = random.Random(f"{seed}|{sec}")
        xs = list(xs)
        rng.shuffle(xs)
        out += xs[:max(1, math.ceil(frac * len(xs)))]
    return sorted(out)


PC_MODES = ("factory", "start")      # 5B.2's arm P: the draws centred on a factory preset or on S
PC_SEED = 20261045                  # its size control's draw (not the fold seed)


def preset_centred(ids, kept, sized=False, seed=PC_SEED):
    """5B.2's arm P: the training examples drawn around a preset (`PC_MODES`; the uniform "wide" draws out). With
    `sized`, its size control instead: in each section as many examples as arm P keeps there, drawn at random from all
    of that section's examples (every mode), so the two sets match section by section."""
    import random

    if not sized:
        return sorted(i for i in ids if kept[i]["mode"] in PC_MODES)
    by = {}
    for i in sorted(ids):
        by.setdefault(kept[i]["section"], []).append(i)
    out = []
    for sec, xs in sorted(by.items()):
        n = sum(kept[i]["mode"] in PC_MODES for i in xs)
        out += random.Random(f"{seed}|{sec}").sample(xs, n)
    return sorted(out)


def gmm1d(x, k=4, iters=200, lo=math.exp(-6), hi=math.exp(1)):
    """A 1-D k-component Gaussian mixture fitted by EM, sigmas clamped to the network's range [e^-6, e^1]
    (`full_space.build_net`). Fewer than k points: one component per point. -> (weights, means, sigmas)."""
    import numpy as np

    x = np.asarray(x, np.float64)
    if len(x) == 0:
        return np.array([1.0]), np.array([0.5]), np.array([hi])
    if len(x) < k:
        return np.full(len(x), 1 / len(x)), x.copy(), np.full(len(x), max(lo, 0.05))
    mu = np.quantile(x, (np.arange(k) + 0.5) / k)
    sd = np.full(k, max(float(np.std(x)), 0.05))
    w = np.full(k, 1 / k)
    for _ in range(iters):
        lp = np.log(w)[None] - 0.5 * ((x[:, None] - mu[None]) / sd[None]) ** 2 - np.log(sd)[None]
        lp -= lp.max(axis=1, keepdims=True)
        r = np.exp(lp)
        r /= r.sum(axis=1, keepdims=True)
        n = r.sum(axis=0) + 1e-12
        w = n / n.sum()
        mu = (r * x[:, None]).sum(axis=0) / n
        sd = np.clip(np.sqrt((r * (x[:, None] - mu[None]) ** 2).sum(axis=0) / n), lo, hi)
    return w, mu, sd


def gmm1d_nll(v, w, mu, sd):
    import numpy as np

    lp = np.log(w) - 0.5 * ((v - mu) / sd) ** 2 - np.log(sd) - 0.5 * math.log(2 * math.pi)
    m = lp.max()
    return float(-(m + np.log(np.exp(lp - m).sum())))


class Baseline:
    """The label-marginal baseline in the loss's units, fitted on training labels per (amp, section class): each knob a
    4-component 1-D mixture, each switch its on-rate, each mic its frequencies (add-half smoothing), the amp its
    overall frequencies. `losses(Y, cells)` gives the per-head sums and counts `head_losses` gives for a model."""

    def __init__(self, Y, cells):
        import numpy as np

        from learn import full_space as F

        c, cm, s, sm, k, km, a = Y
        nm = len(F.MICS)
        self.knob, self.sw, self.mic = {}, {}, {}
        for cell in sorted(set(cells)):
            ix = np.array([n for n, z in enumerate(cells) if z == cell])
            self.knob[cell] = [gmm1d(c[ix, j][cm[ix, j] > 0]) for j in range(c.shape[1])]
            self.sw[cell] = [(float(s[ix, j][sm[ix, j] > 0].sum()) + 0.5) / (float((sm[ix, j] > 0).sum()) + 1.0)
                             for j in range(s.shape[1])]
            self.mic[cell] = []
            for j in range(k.shape[1]):
                cnt = np.bincount(k[ix, j][km[ix, j] > 0], minlength=nm)[:nm].astype(np.float64)
                self.mic[cell].append((cnt + 0.5) / (cnt.sum() + 0.5 * nm))
        amps = np.bincount(a, minlength=3).astype(np.float64)
        self.amp = (amps + 0.5) / (amps.sum() + 1.5)

    def losses(self, Y, cells):
        import numpy as np

        c, cm, s, sm, k, km, a = Y
        n, nk = c.shape
        out = {"knob_sum": np.zeros(nk), "knob_n": np.zeros(nk), "sw_sum": np.zeros(s.shape[1]),
               "sw_n": np.zeros(s.shape[1]), "mic_sum": np.zeros(k.shape[1]), "mic_n": np.zeros(k.shape[1]),
               "amp_sum": 0.0, "amp_n": 0, "joint": []}
        for e in range(n):
            cell = cells[e]
            per = []
            for j in range(nk):
                if cm[e, j] > 0:
                    v = gmm1d_nll(c[e, j], *self.knob[cell][j])
                    out["knob_sum"][j] += v
                    out["knob_n"][j] += 1
                    per.append(v)
            out["joint"].append(sum(per) / max(1, len(per)))
            for j in range(s.shape[1]):
                if sm[e, j] > 0:
                    p = min(max(self.sw[cell][j], 1e-6), 1 - 1e-6)
                    out["sw_sum"][j] += -math.log(p if s[e, j] > 0.5 else 1 - p)
                    out["sw_n"][j] += 1
            for j in range(k.shape[1]):
                if km[e, j] > 0:
                    out["mic_sum"][j] += -math.log(float(self.mic[cell][j][k[e, j]]))
                    out["mic_n"][j] += 1
            out["amp_sum"] += -math.log(float(self.amp[a[e]]))
            out["amp_n"] += 1
        return out


def family_means(h):
    """Per-family means of head-loss sums: the knobs' joint NLL per example (the loss's own term), the knobs' marginal
    NLL, switch BCE, mic CE and amp CE, each averaged over labelled (sounding) cases."""
    import numpy as np

    def m(s, n):
        n = np.asarray(n, np.float64)
        return float(np.sum(s) / np.sum(n)) if np.sum(n) else None

    return {"knob_joint": float(np.mean(h["joint"])) if len(h["joint"]) else None,
            "knob_marginal": m(h["knob_sum"], h["knob_n"]), "switch": m(h["sw_sum"], h["sw_n"]),
            "mic": m(h["mic_sum"], h["mic_n"]), "amp": h["amp_sum"] / h["amp_n"] if h["amp_n"] else None}


def head_losses(net, data, idx, dev, batch=64):
    """A model's per-head loss sums and counts on rows `idx` (eval mode, the fixed half): the knob mixture's joint NLL
    per example (normalised by its sounding knobs, as `full_space.loss_fn`) and each knob's marginal NLL under the
    same mixture, each switch's BCE, each mic's CE, the amp head's CE."""
    import numpy as np
    import torch
    import torch.nn.functional as TF

    from learn import full_space as F

    net.eval()
    nk, ns, nc = len(F.CONT), len(F.SW), len(F.CAT)
    out = {"knob_sum": np.zeros(nk), "knob_n": np.zeros(nk), "sw_sum": np.zeros(ns), "sw_n": np.zeros(ns),
           "mic_sum": np.zeros(nc), "mic_n": np.zeros(nc), "amp_sum": 0.0, "amp_n": 0, "joint": [], "total": []}
    with torch.no_grad():
        for j in range(0, len(idx), batch):
            x, cv, y = data.batch(idx[j:j + batch], -1, dev)
            o = net(x, cv)
            c, cm, s, sm, k, km, a = y
            logpi, mu, ls, swl, catl, ampl = o
            out["total"].append(float(F.loss_fn(o, *y)) * len(x))
            z = (c.unsqueeze(1) - mu) / ls.exp()
            lp = -0.5 * z ** 2 - ls - 0.5 * math.log(2 * math.pi)                      # [B, K, n]
            marg = -torch.logsumexp(logpi.unsqueeze(-1) + lp, dim=1)                     # [B, n]
            joint = -torch.logsumexp(logpi + (lp * cm.unsqueeze(1)).sum(-1), dim=-1) / cm.sum(-1).clamp(min=1)
            out["knob_sum"] += (marg * cm).sum(0).cpu().numpy()
            out["knob_n"] += cm.sum(0).cpu().numpy()
            out["joint"] += joint.cpu().numpy().tolist()
            bce = TF.binary_cross_entropy_with_logits(swl, s, reduction="none") * sm
            out["sw_sum"] += bce.sum(0).cpu().numpy()
            out["sw_n"] += sm.sum(0).cpu().numpy()
            for q in range(nc):
                ce = TF.cross_entropy(catl[q], k[:, q], reduction="none") * km[:, q]
                out["mic_sum"][q] += float(ce.sum())
                out["mic_n"][q] += float(km[:, q].sum())
            out["amp_sum"] += float(TF.cross_entropy(ampl, a, reduction="sum"))
            out["amp_n"] += len(x)
    out["total"] = sum(out["total"]) / max(1, len(idx))
    return out


def rung_rows(kept, rend, ids):
    """Training/reading rows of D_CC examples: the label from the render row's settings (as `cc_build.arm_rows`), the
    section's class for the class input."""
    from learn import full_space as F

    out = []
    for i in ids:
        x = kept[i]
        st = {tuple(k.rsplit("/", 1)): v for k, v in rend[i]["settings"].items()}
        out.append({"i": i, "section": x["section"], "band": x["band"], "amp": x["amp"], "cls": x["cls"],
                    "base": x["base"], "label": F.label_of(st, x["amp"])})
    return out


class RungData:
    """One rung's input in memory (uint8 halves) and the full space's labels. Every rung is fed the same way: its
    input in channel 0, channel 1 and its loudness slot zeroed (D_stem's layout), the section's class as the class
    input; in training one half per example per epoch with dropouts and darkening (D_stem's p 0.3 each, no merge and
    no separator failure, which need a second signal); eval reads the fixed half."""

    def __init__(self, rows, path_of, aug=False):
        import numpy as np

        from learn import direct_stems as DS
        from learn import trusted_data_t3 as T3

        self.rows, self.aug, n = rows, aug, len(rows)
        self.X = np.zeros((n, 2, 96, 446), np.uint8)
        self.L = np.zeros((n, 2), np.float32)
        for j, r in enumerate(rows):
            d = np.load(path_of(r["i"]))
            a, b = ("mA", "mB") if "mA" in d.files else ("sA", "sB")
            self.X[j, 0], self.X[j, 1], self.L[j] = d[a], d[b], d["lufs"]
        enc = T3.encode_for(T3.FULL)
        self.Y = [np.stack(z) for z in zip(*(enc(r["label"]) for r in rows))]
        self.centres = DS.mel_centres_hz()
        self.applied = {}

    def batch(self, idx, epoch, dev):
        import numpy as np
        import torch

        from learn import direct_stems as DS
        from learn import pretrain_set as PS
        from learn import song_model as SM

        idx = np.asarray(idx)
        X, C, H = [], [], []
        for j in idx:
            r = self.rows[int(j)]
            h = DS.half_of(r["i"], epoch)
            x = PS.dequant(self.X[j, h])
            if self.aug and epoch >= 0:
                rng = DS.aug_rng(r["i"], epoch)
                u = rng.random(2)
                if u[0] < DS.P_DROP:
                    x = DS.dropouts(x, rng)
                    self.applied["drop"] = self.applied.get("drop", 0) + 1
                if u[1] < DS.P_DARK:
                    x = DS.darken(x, rng, self.centres)
                    self.applied["dark"] = self.applied.get("dark", 0) + 1
            X.append(np.stack([x, x]))
            C.append(SM.cond_vec(r["amp"], r["cls"], [float(self.L[j, h]), 0.0]))
            H.append(h == 0)
        x = SM.norm_feat(np.stack(X))
        PS.mask_half_a(x, np.array(H))
        c = np.stack(C)
        DS.zero_inputs(x, c, "Dstem")
        y = [torch.tensor(z[idx], device=dev) for z in self.Y]
        return torch.tensor(x, device=dev), torch.tensor(c, device=dev), y


def epoch_order(rng, tr, data, epoch):
    """`fit`'s epoch order: the seeded permutation of `tr`, then the data's own per-epoch filter if it has one (the
    share amendment's `DfixData.epoch_keep`), so the RNG stream is the same with or without the filter."""
    order = rng.permutation(tr)
    keep = getattr(data, "epoch_keep", None)
    return order if keep is None else keep(order, epoch)


def fit(data, tr, watch, track, seed, dev, log, epochs, every=1, patience=None, min_gain=1e-4, init=None, lr=None,
        smooth=1):
    """D_CC's optimiser (Adam 1e-3, batch 64, gradients scaled to norm 5; `direct_stems.train_arm`) with the eval-mode
    diagnostics: every `every` epochs (and at the last) the summed loss on each `watch` set {name: idx} and its family
    means. The checkpoint with the lowest `track` loss is kept beside the final one. With `patience` (P1 and FT's inner
    run) it stops once `track` has not improved by min_gain for that many checks; otherwise it runs the full `epochs`.
    FT: `init` a start state, `lr` the rate, `smooth` the trailing moving average of `track` over that many checks
    (the first checks average what exists), and `track` None keeps no best (the final state is returned as best).
    -> (net at its final state, final state, best state, best epoch, best value)."""
    import numpy as np
    import torch

    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import pretrain_set as PS

    torch.manual_seed(seed)
    net = F.build_net()
    if init is not None:
        net.load_state_dict(init)
    net = net.to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=PS.LR if lr is None else lr)
    rng = np.random.default_rng(seed)
    best, bad, best_state, best_ep, steps, seen = math.inf, 0, None, None, 0, []
    for epoch in range(epochs):
        net.train()
        t0 = time.time()
        order = epoch_order(rng, tr, data, epoch)
        tl, skipped = [], 0
        for j in range(0, len(order), PS.BATCH):
            x, c, y = data.batch(order[j:j + PS.BATCH], epoch, dev)
            loss = F.loss_fn(net(x, c), *y)
            opt.zero_grad()
            loss.backward()
            g = DS.grad_norm(net.parameters())
            steps += 1
            if torch.isfinite(g) and torch.isfinite(loss):
                for q in net.parameters():
                    if q.grad is not None:
                        q.grad.mul_(min(1.0, 5.0 / (float(g) + 1e-9)))
                opt.step()
                tl.append(float(loss.detach()))
            else:
                skipped += 1
        if skipped > PS.MAX_SKIP_SHARE * max(1, -(-len(order) // PS.BATCH)):
            raise PS.StepsSkipped(f"epoch {epoch}: {skipped} steps non-finite")
        last = epoch == epochs - 1
        if epoch % every and not last:
            continue
        rec = {"epoch": epoch, "steps": steps, "train_mode_loss": sum(tl) / max(1, len(tl)),
               "seconds": round(time.time() - t0, 2)}
        for name, idx in watch.items():
            h = head_losses(net, data, idx, dev)
            rec[name] = {"total": h["total"], **family_means(h)}
        if track is not None:
            seen.append(rec[track]["total"])
            v = sum(seen[-smooth:]) / len(seen[-smooth:])
            if smooth > 1:
                rec[f"{track}_smoothed"] = v
        log.append(rec)
        print(json.dumps(rec), flush=True)
        if track is None:
            continue
        if math.isfinite(v) and v < best - min_gain:
            best, bad, best_ep = v, 0, epoch
            best_state = {k: t.detach().cpu().clone() for k, t in net.state_dict().items()}
        else:
            bad += 1
            if patience is not None and bad >= patience:
                break
    final = {k: t.detach().cpu().clone() for k, t in net.state_dict().items()}
    if track is None:
        net.eval()
        return net, final, final, log[-1]["epoch"], None
    if best_state is None:
        raise PS.StepsSkipped("no finite watched loss")
    net.eval()
    return net, final, best_state, best_ep, best


def head_table(h, base):
    """Per head: the model's mean loss, the baseline's, and their difference, on one set."""
    import numpy as np

    from learn import full_space as F

    def rows(names, ms, mn, bs, bn):
        out = {}
        for j, nme in enumerate(names):
            if mn[j] > 0:
                out[nme] = {"n": int(mn[j]), "model": float(ms[j] / mn[j]), "baseline": float(bs[j] / bn[j]),
                            "model_minus_baseline": float(ms[j] / mn[j] - bs[j] / bn[j])}
        return out

    return {"knobs": rows(F.CONT, h["knob_sum"], h["knob_n"], base["knob_sum"], base["knob_n"]),
            "switches": rows(F.SW, h["sw_sum"], h["sw_n"], base["sw_sum"], base["sw_n"]),
            "mics": rows(F.CAT, h["mic_sum"], h["mic_n"], base["mic_sum"], base["mic_n"]),
            "amp": {"model": h["amp_sum"] / max(1, h["amp_n"]), "baseline": base["amp_sum"] / max(1, base["amp_n"])},
            "families": {"model": family_means(h), "baseline": family_means(base)},
            "knobs_below_baseline": int(sum(np.asarray(h["knob_sum"]) / np.maximum(h["knob_n"], 1)
                                            < np.asarray(base["knob_sum"]) / np.maximum(base["knob_n"], 1))),
            "switches_below_baseline": int(sum(np.asarray(h["sw_sum"]) / np.maximum(h["sw_n"], 1)
                                               < np.asarray(base["sw_sum"]) / np.maximum(base["sw_n"], 1)))}


def doubles_mode(root=DATA):
    """'fixed' when phase 1b built every doubled example's re-rendered doubles (a refused build drops that example),
    else 'dropped': every doubled example out of every rung (the plan's fallback)."""
    dd = json.loads((out_dir(root) / "dirty-doubles.json").read_text())
    want = {int(i) for i in dd["examples"]}
    from learn import direct_stems as DS

    seen = set()
    for f in sorted((dt_root(root) / "rows").glob("build-*.jsonl")):
        seen |= {r["i"] for r in DS.read_jsonl(f)}
    return ("fixed" if want <= seen else "dropped"), want


def recipe_inputs(root=DATA, pin=None):
    """D_CC's kept examples, render rows and the recipe's split, the same examples for every rung: the runaway
    examples out; the doubled examples kept with their re-rendered doubles (phase 1b) or, failing that, out."""
    from learn import cc_build as CB
    from learn import trusted_data as T

    a = argparse.Namespace(out=None, smoke=False)
    croot = CB.V.out_root(a)
    plan = CB.load_plan(a)
    tr, fs, _, unbuilt = CB.sets(croot, plan)
    if unbuilt:
        raise SystemExit("D_CC's build is not finished")
    kept = {x["i"]: x for x in plan["examples"] if x["i"] in set(tr) | set(fs)}
    rend = T.rows_of(croot, CB.STAGE, "render")
    mode, doubled = doubles_mode(root)
    if pin is not None:                            # the ledger pins the ladder's example set (phase_3_doubles)
        mode = pin
    refused_dt = doubled - doubled_ids(root) if mode == "fixed" else set()
    drop = runaway_ids() | (doubled if mode == "dropped" else refused_dt)
    return croot, kept, rend, recipe_split(kept, tr, fs, drop), {
        "runaway": len(runaway_ids() & set(kept)), "doubles": mode, "doubled": len(doubled & set(kept)),
        "doubled_dropped": len((doubled if mode == "dropped" else refused_dt) & set(kept))}


def device():
    import os

    import torch

    return torch.device("cpu" if os.environ.get("DS_DEVICE") == "cpu" or not torch.backends.mps.is_available()
                        else "mps")


def cmd_p1(args):
    """P1 (review steps 20-24): D_CC's network memorising P1_N fixed training examples on one input (no augmentation,
    no early stopping) until its eval-mode loss on them stops falling; per-head losses against the label-marginal
    baseline on the same examples."""
    import numpy as np
    import torch

    require("phase_2")
    croot, kept, rend, sp, dropped = recipe_inputs()
    _, doubled = doubles_mode()
    rng = np.random.default_rng(SUBSET_SEED)
    pool = [i for i in sp["train"] if i not in doubled]     # the same 200 whether or not phase 1b has run
    ids = sorted(int(i) for i in rng.choice(pool, P1_N, replace=False))
    rows = rung_rows(kept, rend, ids)
    data = RungData(rows, rung_path(croot, args.rung), aug=False)
    cells = [(r["amp"], r["cls"]) for r in rows]
    base = Baseline(data.Y, cells)
    bl = base.losses(data.Y, cells)
    dev = device()
    torch.set_num_threads(2)
    idx = np.arange(len(rows))
    log = []
    t0 = time.time()
    net, final, state, best_ep, best = fit(data, idx, {"memorised": idx}, "memorised", SEEDS[0], dev, log,
                                           epochs=args.epochs, every=10, patience=10, min_gain=0.01)
    net.load_state_dict(state)
    h = head_losses(net, data, idx, dev)
    name = f"P1-{args.rung}"
    od = out_dir() / "runs"
    od.mkdir(parents=True, exist_ok=True)
    torch.save(state, od / f"{name}.pt")
    rec = {"plan": PLAN, "test": "P1 (review steps 20-24)", "ledger": f"{LEDGER_ID} phase_2", "rung": args.rung,
           "input": RUNG_KINDS[args.rung], "examples": ids, "epochs_run": log[-1]["epoch"] + 1, "best_epoch": best_ep,
           "steps": log[-1]["steps"], "minutes": round((time.time() - t0) / 60, 1), "device": str(dev),
           "baseline_families": family_means(bl), "heads": head_table(h, bl), "log": log,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    save(od / f"{name}.json", rec)
    t = rec["heads"]
    print(f"P1 {args.rung}: best epoch {best_ep}; families model {t['families']['model']} baseline "
          f"{t['families']['baseline']}; knobs below baseline {t['knobs_below_baseline']} of {len(t['knobs'])}, "
          f"switches {t['switches_below_baseline']} of {len(t['switches'])}")
    print("P1 DONE")


FOLDS = {0: ("Forkupines",), 1: ("BKS",), 2: ("The Travelling Band", "Ale Lak", "Dunning Kruger"),
         3: ("Hazael", "Storm Of Particles"), 4: ("The Maybe Next Years", "Adam Buckley")}   # new songs by k-fold
SECTIONS_SEED = 20261034


def run_name(rung, frac=1.0, aug=False, fold=None, sections=1.0):
    return (f"P2{rung}" + ("-aug" if aug else "") + ("" if frac >= 1.0 else f"-f{round(frac * 100)}")
            + ("" if sections >= 1.0 else f"-s{round(sections * 100)}") + ("" if fold is None else f"-k{fold}"))


def section_share(ids, section_of, share, seed=SECTIONS_SEED):
    """Every example of a seeded `share` of the sections (fewer performances, all their settings)."""
    import random

    secs = sorted({section_of[i] for i in ids})
    random.Random(seed).shuffle(secs)
    keep = set(secs[:max(1, round(share * len(secs)))])
    return sorted(i for i in ids if section_of[i] in keep)


def fold_split(kept, ids, fold, folds=FOLDS):
    """(training ids, held-out ids) of one k-fold: the held-out bands' examples against every other kept example."""
    out_bands = set(folds[fold])
    return (sorted(i for i in ids if kept[i]["band"] not in out_bands),
            sorted(i for i in ids if kept[i]["band"] in out_bands))


def doubled_ids(root=DATA):
    """The doubled examples whose re-rendered doubles are built (cc-dt/'s build rows, not refused)."""
    from learn import direct_stems as DS

    out = set()
    for f in sorted((dt_root(root) / "rows").glob("build-*.jsonl")):
        out |= {r["i"] for r in DS.read_jsonl(f) if not r.get("refused")}
    return out


def arm_data(rows, croot, rung, doubled, rend, aug):
    """The rung's data: `RungData` (no augmentation, the ladder), or for P2d-aug D_CC's own data class with its full
    augmentation (`trusted_data.ArmData`), the class key set to the section's class everywhere it is read."""
    from learn import cc_build as CB
    from learn import trusted_data as T
    from learn import trusted_data_t3 as T3

    if not aug:
        return RungData(rows, rung_path(croot, rung, doubled), aug=False)
    if rung != "d":
        raise SystemExit("--aug is P2d-aug's: D_CC's augmentation acts on the stem")
    rr = [dict(r, base=r["cls"], split="train", early_stop=r.get("held", False),
               lufs_A=rend[r["i"]]["target"]["lufs_A"], lufs_B=rend[r["i"]]["target"]["lufs_B"]) for r in rows]
    files = {r["i"]: (str(rung_path(croot, "c", doubled)(r["i"])), str(rung_path(croot, "d", doubled)(r["i"])))
             for r in rr}
    return T.ArmData(rr, files, aug=True, encode=T3.encode_for(T3.FULL), partner_path=lambda i: CB.tgt_path(croot, i))


def plugin_rows(kept, sp, args, rows_of):
    """`cmd_train`'s plugin rows before any real row: the training ids (k-fold, nested fraction, section share, arm P
    as flagged), the held set and its name, and their rows (`rows_of(ids)`; training first, then held, flagged
    `held`). -> (tr, held, held_name, rows)."""
    sec = {i: kept[i]["section"] for i in kept}
    if args.fold is not None:
        tr, held = fold_split(kept, sp["train"] + sp["fs"] + sp["ns"], args.fold)
        held_name = f"fold{args.fold}"
    else:
        tr, held, held_name = sp["train"], sp["ns"], "ns"
    if args.frac < 1.0:
        tr = nested_subset(tr, sec, args.frac)
    if args.sections < 1.0:
        tr = section_share(tr, sec, args.sections)
    if args.pc or args.pcsz:
        if args.rung != "a" or args.fold is not None or args.frac < 1.0 or args.sections < 1.0 or args.aug:
            raise SystemExit("--pc/--pcsz are 5B.2's arm P on P2a's own training set")
        require("phase_5b2")
        tr = preset_centred(tr, kept, sized=bool(args.pcsz))
    return tr, held, held_name, rows_of(tr) + [dict(r, held=True) for r in rows_of(held)]


def with_rows(tr, rows, extra):
    """Training rows `extra` placed after the training rows and before the held ones (`--real-fold`'s layout).
    -> (training ids, rows)."""
    return tr + [r["i"] for r in extra], rows[:len(tr)] + list(extra) + rows[len(tr):]


def cmd_train(args):
    """One model of the ladder (demucs-venv): the common recipe on rung `--rung`'s input for the declared number of
    epochs, the eval-mode diagnostics at every checkpoint (a fixed training subset and the held-out set, per family),
    the final and the held-out-best checkpoints kept, each with its per-head table against the label-marginal
    baseline. `--frac`: a nested share of the training examples within sections; `--sections`: a share of the
    sections with all their examples; `--fold k`: new songs by k-fold (all kept examples of the other folds' bands;
    the final checkpoint is the one read); `--aug`: P2d-aug; `--dfix [--real-fold k]`: D_fix (P2b-wide24's recipe
    plus the real rows in backings, `DfixData`; `dfix_refusal` takes every other combination)."""
    why = dfix_refusal(args)
    if why:
        raise SystemExit(why)
    import numpy as np
    import torch

    from learn import direct_stems as DS

    e = require("phase_3")
    length = e["phase_3_length"]
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    name = run_name(args.rung, args.frac, args.aug, args.fold, args.sections) + ("-bk8" if args.backings else "") \
        + ("-dd" if args.dd else "") + (f"-wide{WIDE_K}" if args.wide else "") + ("-pc" if args.pc else "") \
        + ("-pcsz" if args.pcsz else "") + ("" if args.real_fold is None else f"-real{args.real_fold}" + ("s2" if args.stage == 2 else ""))
    if args.goat or args.goat_shuffle:                 # 5C: its own names, so no 5B.2 run is ever taken for one
        name = goat_run_name(name, args.real_fold, args.stage, args.goat_shuffle)
    if args.dfix:                                      # D_fix: its own names (`dfix_refusal` took every other flag)
        name = dfix_run_name(args.real_fold, args.dfix_share)
    od = out_dir() / "runs"
    rp = od / f"{name}-{args.seed}.json"
    if rp.exists():
        print(f"{rp.name} exists: nothing to do")
        return
    if args.seed not in SEEDS:
        raise SystemExit(f"--seed in {SEEDS}")
    tr, held, held_name, rows = plugin_rows(kept, sp, args, lambda ids: rung_rows(kept, rend, ids))
    doubled = doubled_ids() if dropped["doubles"] == "fixed" else frozenset()
    real_held, dfix_info = [], None
    if args.dfix:
        require("phase_dfix")
        share = dfix_share_of(name)
        if share < 1:
            require("phase_dfix_share")
        rrows, real_held, dfix_info = dfix_real_rows(args.real_fold)
        plugin_tr = tr
        tr, rows = with_rows(tr, rows, rrows)
        rows = rows + [dict(r, held=True) for r in real_held]     # the held fold's real rows: a diagnostic, last
        data = DfixData(rows, rung_path(croot, "b", doubled), set(plugin_tr), {r["i"] for r in rrows}, share)
        if share < 1:                                  # the known answer: D_fix's own inputs, by its stored hash
            ref = dfix_run_name(args.real_fold)
            want = json.loads((od / f"{ref}-{args.seed}.json").read_text())["dfix"]["inputs_sha256"]
            if data.inputs_sha256 != want:
                raise SystemExit(f"{name}: real-row inputs differ from {ref}'s "
                                 f"({data.inputs_sha256[:8]} vs {want[:8]})")
        dfix_info.update(fold=args.real_fold, plugin_train=len(plugin_tr), inputs_sha256=data.inputs_sha256,
                         target_lufs=data.target_lufs, share=share)
    elif args.wide:
        if args.rung != "b" or args.aug or args.backings:
            raise SystemExit("--wide is phase 5A's test on P2b")
        require("phase_5a")
        data = WideData(rows, rung_path(croot, "b", doubled), set(tr))
    elif args.backings:
        if args.rung != "b" or args.aug:
            raise SystemExit("--backings is the backing-variety test on P2b")
        require("phase_3_backings")
        data = BackingData(rows, rung_path(croot, "b", doubled), set(tr))
    elif args.dd:
        if args.rung != "a":
            raise SystemExit("--dd is step 18's isolated test on P2a")
        require("phase_3_isolated")
        data = RungData(rows, rung_path(croot, "a", doubled), aug=True)
    elif args.real_fold is not None:
        if args.rung != "a" or args.aug or args.fold is not None or args.frac < 1.0 or args.sections < 1.0:
            raise SystemExit("--real-fold is 5B.2's arm R on P2a's own training set")
        rrows, rpaths, real_fold_of = real_rows(args.real_fold, p2a_median_lufs(tr), stage=max(1, args.stage))
        if not rrows:
            raise SystemExit("no labelled real rows: run real-search first")
        if args.goat or args.goat_shuffle:
            require("phase_5c")
            grows, gpaths = goat_rows(args.real_fold, p2a_median_lufs(tr), shuffle=args.goat_shuffle)
            if not grows:
                raise SystemExit("no labelled GOAT rows: run goat-search first")
            if set(gpaths) & set(rpaths):
                raise SystemExit("GOAT and BKS row ids collide")
            rrows, rpaths = rrows + grows, {**rpaths, **gpaths}
        base_path = rung_path(croot, "a", doubled)
        rows = rows[:len(tr)] + rrows + rows[len(tr):]
        tr = tr + [r["i"] for r in rrows]
        data = RungData(rows, lambda i: rpaths[i] if i in rpaths else base_path(i), aug=False)
    else:
        data = arm_data(rows, croot, args.rung, doubled, rend, args.aug)
    ti, hi = np.arange(len(tr)), np.arange(len(tr), len(rows) - len(real_held))
    rh = np.arange(len(rows) - len(real_held), len(rows))
    sub = np.sort(np.random.default_rng(SUBSET_SEED).choice(ti, min(SUBSET_N, len(ti)), replace=False))
    cells = [(r["amp"], r["cls"]) for r in rows]
    base = Baseline([z[ti] for z in data.Y], [cells[j] for j in ti])
    bl = {"train_subset": base.losses([z[sub] for z in data.Y], [cells[j] for j in sub]),
          held_name: base.losses([z[hi] for z in data.Y], [cells[j] for j in hi])}
    dev = device()
    torch.set_num_threads(2)
    log = []
    t0 = time.time()
    watch = {"train_subset": sub, held_name: hi}
    if len(rh):                                        # D_fix_k: the held fold's real loss, logged, never for choosing
        watch["real_held"] = rh
    if args.dfix and dfix_share_of(name) < 1:          # the share amendment: plugin and real training rows' loss apart
        rset = {r["i"] for r in rows if "real" in r and not r.get("held")}
        rt = np.array([j for j in ti if rows[j]["i"] in rset])
        pt = np.array([j for j in ti if rows[j]["i"] not in rset])
        g = np.random.default_rng(SUBSET_SEED)
        watch["train_plugin"] = np.sort(g.choice(pt, min(SUBSET_N, len(pt)), replace=False))
        watch["train_real"] = np.sort(g.choice(rt, min(SUBSET_N, len(rt)), replace=False))
    net, final, best_state, best_ep, best = fit(data, ti, watch, held_name, args.seed,
                                                dev, log, epochs=int(length["epochs"]), every=int(length["every"]))
    heads = {}
    od.mkdir(parents=True, exist_ok=True)
    for which, st in (("final", final), ("best", best_state)):
        net.load_state_dict(st)
        heads[which] = {k: head_table(head_losses(net, data, idx, dev), bl[k])
                        for k, idx in (("train_subset", sub), (held_name, hi))}
        torch.save(st, od / f"{name}-{args.seed}-{which}.pt")
    phase = (dfix_phase(name) if args.dfix else "phase_5c" if (args.goat or args.goat_shuffle)
             else "phase_5b2" if (args.pc or args.pcsz or args.real_fold is not None) else "phase_3")
    save(rp, {"plan": PLAN, "test": name, "ledger": f"{LEDGER_ID} {phase}", "rung": args.rung,
              "input": RUNG_KINDS[args.rung], "aug": bool(args.aug), "frac": args.frac, "sections": args.sections,
              "fold": args.fold, "held": held_name, "seed": args.seed, "train": len(tr), "held_n": len(held),
              "train_ids": tr, "held_ids": held, "dropped": dropped, "split_dropped": sp["dropped"],
              "epochs_run": log[-1]["epoch"] + 1, "best_epoch": best_ep, "best_held_loss": best,
              "steps": log[-1]["steps"], "minutes": round((time.time() - t0) / 60, 1), "device": str(dev),
              "length": length, "augmentations_applied": data.applied, "flags": {"dd": bool(args.dd),
              "backings": bool(args.backings), "aug": bool(args.aug), "wide": bool(args.wide),
              "pc": bool(args.pc), "pcsz": bool(args.pcsz), "real_fold": args.real_fold, "dfix": bool(args.dfix),
              "dfix_share": args.dfix_share,
              "goat": bool(args.goat), "stage": args.stage},
              "dfix": dfix_info, "backing_variants": getattr(data, "counts", None),
              "baseline_families": {k: family_means(v) for k, v in bl.items()}, "heads": heads, "log": log,
              "models": {w: f"{name}-{args.seed}-{w}.pt" for w in ("final", "best")},
              "model_sha256": {w: DS.hashlib_file(od / f"{name}-{args.seed}-{w}.pt") for w in ("final", "best")},
              "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    for which in ("final", "best"):
        h = heads[which][held_name]
        print(f"{which}: {held_name} families model {h['families']['model']} baseline {h['families']['baseline']}; "
              f"knobs below baseline {h['knobs_below_baseline']} of {len(h['knobs'])}, switches "
              f"{h['switches_below_baseline']} of {len(h['switches'])}")
    print(f"TRAIN DONE {name} {args.seed}: best checkpoint epoch {best_ep} of {log[-1]['epoch'] + 1}; "
          f"{round((time.time() - t0) / 60, 1)} min")


# --- the doubles fix (review step 12): DT doubles re-rendered with the target's full setting --------------------------

DT_STAGE = "cc-dt"                 # pipeline-fix/cc-dt/: the re-rendered others, their mixes and stems


def dt_root(root=DATA):
    return out_dir(root) / DT_STAGE


def dt_flac(root, i):
    return dt_root(root) / "audio" / f"{i // 1000:04d}" / f"{i:07d}-others.flac"


def dt_ex(root, i, kind):
    return dt_root(root) / "ex" / f"{i // 1000:04d}" / f"{i:07d}-{kind}.npz"


def other_jobs(x, cores, menu, new):
    """An example's other-guitar render jobs as `cc_build.cmd_render` makes them, except that with `new` a DT double
    takes the target's full setting (`full_twin`'s select and setting) instead of its core one.
    -> [(di, amp, other, select, setting, fresh)]: `fresh` renders in its own primed process (a double carrying the
    target's time effects; Morgan's time effects run on across renders in one process)."""
    from learn import trusted_data as T

    out = []
    for o in x["others"]:
        if o["dt"]:
            amp, _, _, sel, xf, core, _, _ = cores
            out.append((o["di"], amp, o, sel, xf if new else core, bool(new)))
        else:
            amp, sel, st = T.other_settings(x["i"], o["di"], menu)
            out.append((o["di"], amp, o, sel, st, False))
    return out


def cmd_render_doubles(args):
    """One shard of sections: for each kept example with a DT double, every other guitar re-rendered as `cc_build`
    rendered it, the DT doubles with the target's full setting, each in its own primed process; the others' sum
    written to cc-dt/. First, in shard 0, a positive control: CONTROL_N doubled examples re-rendered the old way
    must reproduce their stored others to within the FLAC's quantisation (`--control`, run alone first; the shards
    refuse until it passes)."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T
    from learn import trusted_data_t3 as T3

    require("phase_1b")
    a = argparse.Namespace(out=None, smoke=False)
    croot = CB.V.out_root(a)
    plan = CB.load_plan(a)
    dd = json.loads((out_dir() / "dirty-doubles.json").read_text())
    todo_ids = sorted(int(i) for i in dd["examples"])
    ex = {x["i"]: x for x in plan["examples"]}
    rend = T.rows_of(croot, CB.STAGE, "render")
    k, n = args.shard
    secs = sorted({ex[i]["section"] for i in todo_ids})
    mine = [s for j, s in enumerate(secs) if j % n == k]
    rp = dt_root() / "rows" / f"render-{k}of{n}.jsonl"
    done = {r["i"] for r in DS.read_jsonl(rp)} if rp.exists() else set()
    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"free disk below {T.DISK_GUARD_GB:.0f} GB")
    ctx = CB.ctx_for(a)
    menus = T3.Menus()
    menus.gate_u = plan["gate_cap"]["unit"]
    LO._wait_cap()
    rr = CB.new_renderer()
    try:
        T3.check_menu(rr.menu(), menus.dried)
        menu = rr.menu()
    finally:
        rr.close()
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    swap0 = DS.swap_mb()
    renders = 0

    by_sec = {}
    for x in plan["examples"]:
        by_sec.setdefault(x["section"], []).append(x)

    def rendered(sid):
        """The section's examples `cc_build.cmd_render` rendered other guitars for (its target not refused)."""
        return [x for x in by_sec[sid] if x["i"] in rend and not str(rend[x["i"]].get("refused") or "").startswith("target:")]

    def others_of(xs, sec, new):
        """{i: (others sum, rows)} for the examples xs of one section, `cc_build.cmd_render`'s job order (one shared
        process, sorted by (DI, amp, i), primed on a (section|DI, amp) change; an example's jobs stop at its first
        refusal); with `new`, each DT double with the full setting in its own primed process after them."""
        nonlocal renders
        stems = sorted({s for x in by_sec[sec["id"]] for s in x["stems"]["v"]})     # as the original render's
        levels = T.section_levels(ctx, sec, [o for x in by_sec[sec["id"]] for o in x["others"]], stems)
        acc = {x["i"]: np.zeros(trim[1] - trim[0]) for x in xs}
        rows = {x["i"]: {"i": x["i"], "others": []} for x in xs}
        jobs = []
        for x in xs:
            for di_id, amp, o, sel, st, fresh in other_jobs(x, T3.full_twin(x["i"], menus), menu, new):
                jobs.append((di_id, amp, x["i"], o, sel, st, fresh))
        jobs.sort(key=lambda j: (j[6], j[0], j[1], j[2]))
        di_cache = {}

        def di_of(di_id):
            if di_id not in di_cache:
                di_cache[di_id] = B.measure(PS.section_audio(ctx.inv[di_id]["path"], sec["start_s"])).astype(np.float32)
            return di_cache[di_id]

        shared = [j for j in jobs if not j[6]]
        if shared:
            rr = CB.new_renderer()
            try:
                primer = DS.Primer(rr)
                for di_id, amp, i, o, sel, st, _ in shared:
                    if rows[i].get("refused"):
                        continue
                    lv, src = levels[di_id]
                    if lv is None:
                        rows[i]["others"].append({"di": di_id, "left_out": "no level"})
                        continue
                    y = primer.render((f"{sec['id']}|{di_id}", amp), di_of(di_id), sel, st)
                    y = (y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]]
                    acc[i] = T.place_other(rows[i], acc[i], y, T.lufs_or_none(y), lv, src, o, amp, LO.sdict(st))
                renders += primer.renders
            finally:
                rr.close()
        for di_id, amp, i, o, sel, st, _ in (j for j in jobs if j[6]):
            if rows[i].get("refused"):
                continue
            lv, src = levels[di_id]
            if lv is None:
                rows[i]["others"].append({"di": di_id, "left_out": "no level"})
                continue
            y = AM.fresh_render(CB.new_renderer, di_of(di_id), sel, st, st)
            renders += 2
            y = (y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]]
            acc[i] = T.place_other(rows[i], acc[i], y, T.lufs_or_none(y), lv, src, o, amp, LO.sdict(st))
        return acc, rows

    control = []
    cp = dt_root() / "control.json"
    if not args.control:
        if not cp.exists() or not all(c["ok"] for c in json.loads(cp.read_text())["examples"]):
            raise SystemExit("run `render-doubles --control` first; the shards render only after it passes")
    elif not cp.exists():
        pick = todo_ids[:: max(1, len(todo_ids) // CONTROL_N)][:CONTROL_N]
        for sid in sorted({ex[i]["section"] for i in pick}):
            xs = rendered(sid)                                   # the section's whole original job list, replayed
            sec = dict(ctx.sections[sid], id=sid)
            acc, rows = others_of(xs, sec, new=False)
            for x in xs:
                rw = rend[x["i"]]
                if rw.get("refused") or not rw.get("others_file"):
                    continue
                old = G.read_flac(T.flac_path(croot, CB.STAGE, x["i"], "others"), rw["others_file"]["scale"],
                                  rw["others_file"]["sha256"])
                step = float(rw["others_file"]["scale"]) / 2 ** 23
                dev = float(np.max(np.abs(acc[x["i"]] - old)))
                control.append({"i": x["i"], "section": sid, "max_abs_dev": dev, "flac_step": step, "ok": dev <= step})
                print(f"control {x['i']}: max |re-render - stored| {dev:.3g} (FLAC step {step:.3g})", flush=True)
        save(dt_root() / "control.json", {"examples": control, "renders": renders,
                                          "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        if not all(c["ok"] for c in control):
            raise SystemExit("the old render path does not reproduce the stored others: stop")
        print("CONTROL PASSED")
        return
    else:
        print(f"the control is stored: {cp}")
        return
    rp.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(rp, "a") as fh:
        for m, sid in enumerate(mine):
            g = DS._guards("pipeline-fix-doubles", T.DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            xs = [ex[i] for i in todo_ids if ex[i]["section"] == sid and i not in done]
            if not xs:
                continue
            sec = dict(ctx.sections[sid], id=sid)
            acc, rows = others_of(xs, sec, new=True)
            for x in xs:
                rw = rows[x["i"]]
                if not rw.get("refused"):
                    sc, sha = G.write_flac(dt_flac(DATA, x["i"]), acc[x["i"]], PS.SR)
                    rw["others_file"] = {"scale": sc, "sha256": sha}
                rw["renders_so_far"] = renders
                fh.write(json.dumps(rw) + "\n")
            fh.flush()
            print(f"section {m + 1}/{len(mine)}: {len(xs)} examples; renders {renders}; "
                  f"{(time.time() - t0) / (m + 1):.0f} s per section", flush=True)
    print(f"RENDER-DOUBLES DONE {k}/{n}: {renders} renders")


CONTROL_N = 4


def cmd_build_doubles(args):
    """The doubled examples' new mixes and X-LANCE stems (msst-venv), `cc_build.cmd_build`'s recipe on the new
    others: features `mix-ccdt` and `xlance_g-ccdt` under cc-dt/."""
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import trusted_data as T

    require("phase_1b")
    a = argparse.Namespace(out=None, smoke=False)
    croot = CB.V.out_root(a)
    plan = CB.load_plan(a)
    ex = {x["i"]: x for x in plan["examples"]}
    rend = T.rows_of(croot, CB.STAGE, "render")
    new = {}
    for f in sorted((dt_root() / "rows").glob("render-*.jsonl")):
        for r in DS.read_jsonl(f):
            new[r["i"]] = r
    bp = dt_root() / "rows" / f"build-{args.device}-{__import__('os').getpid()}.jsonl"
    built = set()
    for f in sorted((dt_root() / "rows").glob("build-*.jsonl")):
        built |= {r["i"] for r in DS.read_jsonl(f)}
    todo = sorted((i for i in new if i not in built), key=lambda i: (ex[i]["section"], i), reverse=args.desc)
    print(f"build-doubles: {len(todo)} to build on {args.device}", flush=True)
    ctx = CB.ctx_for(a)
    sep = DS.stem_separator(T.SEP, args.device)
    stems = T.Stems(ctx)
    swap0 = DS.swap_mb()
    t0 = time.time()
    with open(bp, "a") as fh:
        for m, i in enumerate(todo):
            g = DS._guards("pipeline-fix-build", T.DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            if dt_ex(DATA, i, "xlance_g-ccdt").exists():
                continue
            x, rw, nw = ex[i], rend[i], new[i]
            base = {"i": i, "section": x["section"], "band": x["band"]}
            if nw.get("refused"):
                fh.write(json.dumps({**base, "refused": nw["refused"]}) + "\n")
                continue
            y = G.read_flac(T.flac_path(croot, CB.STAGE, i, "target"), rw["target"]["scale"], rw["target"]["sha256"])
            oth = G.read_flac(dt_flac(DATA, i), nw["others_file"]["scale"], nw["others_file"]["sha256"])
            voc = x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"]
            st = stems.get(x["section"], T.backing_tracks(x, voc))
            mix, gains, lb = T.self_built_mix(np.asarray(y, np.float64), np.asarray(oth, np.float64), st, x)
            if not T.empty_backing_ok(y, lb):
                fh.write(json.dumps({**base, "refused": "no backing: the drawn ratio cannot be met"}) + "\n")
                continue
            s_ = np.asarray(sep(mix), np.float64)
            if len(s_) != len(mix) or not np.isfinite(s_).all():
                raise SystemExit(f"{i}: bad stem")
            mm, ml, _ = DS.half_features(mix)
            sm, sl, floor = DS.half_features(s_)
            DS._save_npz(dt_ex(DATA, i, "mix-ccdt"), mA=mm["A"], mB=mm["B"], lufs=[ml["A"], ml["B"]],
                         gain_db=gains["ga"], mastered=x["draw"]["mastered"])
            DS._save_npz(dt_ex(DATA, i, "xlance_g-ccdt"), sA=sm["A"], sB=sm["B"], lufs=[sl["A"], sl["B"]])
            fh.write(json.dumps({**base, "gains_db": gains, "lufs_backing": lb, "floor_share": floor,
                                 "snr_audio_db": DS.snr_db(s_, y * 10 ** (gains["ga"] / 20)),
                                 "device": args.device}) + "\n")
            fh.flush()
            if m % 25 == 0:
                print(f"build {m + 1}/{len(todo)}: {(time.time() - t0) / (m + 1):.1f} s per example", flush=True)
    print(f"BUILD-DOUBLES DONE ({args.device})")


# --- P2's reads: by knob on every FS and NS example, by sound on a fixed sample -------------------------------------

SAMPLE_N = 60                      # per read set (FS, NS)
SAMPLE_SEED = 20261033


def knob_rows(ans, lab, const, cell_of):
    """Per knob: the error of the answer and of the constant on every example where it sounds (unit range).
    ans {i: unit vector}; lab {i: (cont, mask)}; const {cell: unit vector}. -> {j: [(i, err_model, err_const)]}."""
    import numpy as np

    out = {}
    for i, a in ans.items():
        c, m = lab[i]
        k = np.asarray(const[cell_of[i]], np.float64)
        for j in np.flatnonzero(np.asarray(m) > 0):
            out.setdefault(int(j), []).append((i, abs(float(a[j]) - float(c[j])), abs(float(k[j]) - float(c[j]))))
    return out


def readable(rows, cluster_of):
    """R0's reading for one head from (i, model error, constant error) rows: the mean of (model - constant) with a
    90% interval clustered by `cluster_of[i]`; readable when the interval is below 0, worse when above."""
    c = clustered([(cluster_of[i], str(i), em - ec) for i, em, ec in rows])
    c["readable"] = c["hi90"] is not None and c["hi90"] < 0
    c["worse"] = c["lo90"] is not None and c["lo90"] > 0
    return {k: c[k] for k in ("mean", "lo90", "hi90", "clusters", "readable", "worse")}


def read_inputs(data):
    """Both halves of every row of a `RungData` as model inputs (eval: no augmentation), D_stem's layout.
    -> (X [2n, 2, 96, frames], C [2n, ...], who [2n] example ids)."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_model as SM

    X, C, H, who = [], [], [], []
    for j, r in enumerate(data.rows):
        for h in (0, 1):
            x = PS.dequant(data.X[j, h])
            X.append(np.stack([x, x]))
            C.append(SM.cond_vec(r["amp"], r["cls"], [float(data.L[j, h]), 0.0]))
            H.append(h == 0)
            who.append(r["i"])
    x = SM.norm_feat(np.stack(X))
    PS.mask_half_a(x, np.array(H))
    c = np.stack(C)
    DS.zero_inputs(x, c, "Dstem")
    return x.astype(np.float32), c, who


def load_run(name, seed, which):
    import torch

    from learn import direct_stems as DS
    from learn import full_space as F

    rec = json.loads((out_dir() / "runs" / f"{name}-{seed}.json").read_text())
    p = out_dir() / "runs" / rec["models"][which]
    if DS.hashlib_file(p) != rec["model_sha256"][which]:
        raise SystemExit(f"{p.name}: the model changed since its run")
    net = F.build_net()
    net.load_state_dict(torch.load(p, map_location="cpu"))
    net.eval()
    return net, rec


def constant_of(rows):
    """The constant per (amp, section class) from training rows' labels (`direct_sound_gate.constant_answers`, its
    cell key set to the section's class)."""
    from learn import direct_sound_gate as G
    from learn import full_space as F
    from learn import trusted_data_t3 as T3

    enc = T3.encode_for(T3.FULL)
    return G.constant_answers([dict(r, base=r["cls"]) for r in rows], lambda lab: enc(lab)[:6], len(F.CONT),
                              len(F.SW), len(F.CAT))


def split_e(ex, info, const, key_of):
    """The by-knob E (mean |error| over the sounding knobs) of the model minus the constant's, per group of
    `key_of(i)`, clustered by section (zero renders; steps 7 and 15)."""
    import numpy as np

    out = {}
    for g in sorted({key_of(i) for i in ex}, key=str):
        d = {}
        for i, e in ex.items():
            if key_of(i) != g:
                continue
            c0 = np.asarray(const[info[i]["cell"]]["cont"], np.float64)
            m = (np.asarray(e["cm"]) > 0) & np.isfinite(c0)
            if m.any():
                y = np.asarray(e["c"], np.float64)
                d[i] = float(np.mean(np.abs(e["a2"] - y)[m]) - np.mean(np.abs(c0 - y)[m]))
        out[str(g)] = clustered([(info[i]["section"], str(i), v) for i, v in d.items()])
        out[str(g)] = {k: out[str(g)][k] for k in ("mean", "lo90", "hi90", "clusters", "parts")}
    return out


def per_example_e(ex, info, const, kx):
    """{i: [band, section, E - constant]} over each example's sounding knobs (the k-fold's pooled row)."""
    import numpy as np

    out = {}
    for i, e in ex.items():
        c0 = np.asarray(const[info[i]["cell"]]["cont"], np.float64)
        m = (np.asarray(e["cm"]) > 0) & np.isfinite(c0)
        if m.any():
            y = np.asarray(e["c"], np.float64)
            out[str(i)] = [kx[i]["band"], kx[i]["section"],
                           float(np.mean(np.abs(e["a2"] - y)[m]) - np.mean(np.abs(c0 - y)[m]))]
    return out


def cmd_kfold_report(args):
    """The new-song k-fold (P2a, final checkpoints): every kept example read by the fold that held its band out; the
    pooled E - constant clustered by band (9 bands), each fold's training and held-out size and readable heads.
    Zero renders. -> reads/kfold-<name>.json."""
    e = require("phase_3")
    rows, folds = [], {}
    for f in sorted(FOLDS):
        rd = json.loads((out_dir() / "reads" / f"{args.name}-k{f}-final.json").read_text())
        run = json.loads((out_dir() / "runs" / f"{args.name}-k{f}-{SEEDS[0]}.json").read_text())
        st = rd["sets"][f"fold{f}"]
        folds[f] = {"bands": list(FOLDS[f]), "train": run["train"], "held": run["held_n"],
                    "readable": st["readable"], "e_minus_constant": st["e_minus_constant_all"]}
        rows += [(b, sec, v) for b, sec, v in st["per_example"].values()]
    c = clustered(rows)
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_3", "name": args.name, "folds": folds,
           "pooled": {k: c.get(k) for k in ("mean", "lo90", "hi90", "clusters", "clusters_negative", "per_cluster",
                                            "leave_one_out", "part_weighted", "parts")},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    save(out_dir() / "reads" / f"kfold-{args.name}.json", out)
    print(f"pooled over {c['clusters']} bands: E - constant {c['mean']:+.4f} [{c['lo90']:+.4f}, {c['hi90']:+.4f}], "
          f"{c['clusters_negative']} of {c['clusters']} bands better")
    for f, v in folds.items():
        print(f"  fold {f} {v['bands']}: train {v['train']}, held {v['held']}, readable {v['readable']}, "
              f"E - constant {v['e_minus_constant']['mean']:+.4f}")


def cmd_read(args):
    """The by-knob read of one model (`--name`, both seeds where both ran, `--which` final|best): R0's rule on FS and
    the held-out set (NS or the fold), against the constant of its own training labels; the family table; E split by
    draw mode and by mastering. Zero renders. -> reads/<name>-<which>.json."""
    import numpy as np

    from learn import full_space as F
    from learn import trusted_data_t3_r as R

    e = require("phase_3")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    nets, recs = [], []
    for sd in SEEDS:
        if (out_dir() / "runs" / f"{args.name}-{sd}.json").exists():
            n, r = load_run(args.name, sd, args.which)
            nets.append(n)
            recs.append(r)
    if not nets:
        raise SystemExit(f"{args.name}: no run")
    rec = recs[0]
    tr_rows = rung_rows(kept, rend, rec["train_ids"])
    const = constant_of(tr_rows)
    train_rates = {}
    doubled = doubled_ids() if dropped["doubles"] == "fixed" else frozenset()
    sets = {rec["held"]: rec["held_ids"]}
    if rec["fold"] is None:
        sets["fs"] = sp["fs"]
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_3", "name": args.name, "which": args.which,
           "seeds": [r["seed"] for r in recs], "sets": {}}
    amps = [r["amp"] for r in tr_rows]
    majority_amp = max(F.AMPS, key=lambda a: (amps.count(a), a))
    for set_name, ids in sets.items():
        rows = rung_rows(kept, rend, ids)
        data = RungData(rows, rung_path(croot, rec["rung"], doubled), aug=False)
        X, C, who = read_inputs(data)
        outs = F.run_nets(nets, X, C)
        Y = [np.repeat(data.Y[q], 2, axis=0) for q in range(6)]            # each row's two halves, as `who`
        ex = R.per_example(outs, who, Y)
        info = {r["i"]: {"section": r["section"], "cell": (r["amp"], r["cls"]), "amp": r["amp"]} for r in rows}
        r0 = R.r0_rows(ex, info, const, train_rates, majority_amp)
        fam = R.by_family(r0)
        kx = {r["i"]: kept[r["i"]] for r in rows}
        out["sets"][set_name] = {
            "examples": len(rows), "sections": len({r["section"] for r in rows}),
            "readable": {k: sum(1 for z in r0 if z["kind"] == k and z["readable"]) for k in CHANCE_KINDS},
            "heads": {k: sum(1 for z in r0 if z["kind"] == k) for k in CHANCE_KINDS},
            "worse_knobs": sum(1 for z in r0 if z["kind"] == "continuous" and z["lo"] is not None and z["lo"] > 0),
            "knob_e_median": {"model": float(np.median([z["e_model"] for z in r0 if z["kind"] == "continuous"
                                                         and z["e_model"] is not None])),
                              "constant": float(np.median([z["e_constant"] for z in r0 if z["kind"] == "continuous"
                                                            and z["e_constant"] is not None]))},
            "families": fam, "rows": r0,
            "e_minus_constant_by_mode": split_e(ex, info, const, lambda i: kx[i]["mode"]),
            "e_minus_constant_by_mastered": split_e(ex, info, const, lambda i: kx[i]["draw"]["mastered"]),
            "e_minus_constant_all": split_e(ex, info, const, lambda i: "all")["all"],
            "per_example": per_example_e(ex, info, const, kx)}
        s_ = out["sets"][set_name]
        print(f"{args.name} ({args.which}, seeds {out['seeds']}) on {set_name} ({len(rows)} examples): readable "
              f"{s_['readable']} of {s_['heads']}; knobs worse {s_['worse_knobs']}; knob E median model "
              f"{s_['knob_e_median']['model']:.4f} vs constant {s_['knob_e_median']['constant']:.4f}; E - constant "
              f"{s_['e_minus_constant_all']['mean']:+.4f} [{s_['e_minus_constant_all']['lo90']}, "
              f"{s_['e_minus_constant_all']['hi90']}]", flush=True)
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save(out_dir() / "reads" / f"{args.name}-{args.which}.json", out)
    print("READ DONE")


CHANCE_KINDS = ("continuous", "switch", "accuracy")


# --- P2's by-sound read: answers rendered through each example's own measure DI, judged against its target ----------

SOUND_DIR = "sound"


def cmd_sample(args):
    """The by-sound sample (zero renders): for FS and NS each, 120 examples in a fixed order spread over sections
    (`draw_sample`); the read uses the first 60 and grows to 120 while the locating rows stay undecided."""
    e = require("phase_3")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    sec = {i: kept[i]["section"] for i in kept}
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_3", "seed": SAMPLE_SEED, "first": SAMPLE_N,
           "order": {k: draw_order(sp[k], sec) for k in ("fs", "ns")}, "doubles": dropped["doubles"],
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    p = out_dir() / SOUND_DIR / "sample.json"
    if p.exists() and json.loads(p.read_text())["order"] != out["order"]:
        raise SystemExit("a different sample is already stored: the sample is drawn once")
    save(p, out)
    print({k: len(v) for k, v in out["order"].items()}, "SAMPLE DONE")


def draw_order(ids, section_of, n=2 * SAMPLE_N, seed=SAMPLE_SEED):
    """`draw_sample`'s round-robin order, kept in draw order (the first SAMPLE_N are the first read)."""
    import random

    by = {}
    for i in sorted(ids):
        by.setdefault(section_of[i], []).append(i)
    rng = random.Random(seed)
    secs = sorted(by)
    rng.shuffle(secs)
    for x in secs:
        random.Random(f"{seed}|{x}").shuffle(by[x])
    out = []
    while len(out) < n and any(by[x] for x in secs):
        for x in secs:
            if by[x] and len(out) < n:
                out.append(by[x].pop(0))
    return out


def sample_ids(n_each):
    d = json.loads((out_dir() / SOUND_DIR / "sample.json").read_text())
    return {k: v[:n_each] for k, v in d["order"].items()}


def cmd_answers(args):
    """One model's plain answers on the sample (zero renders): seeds and halves pooled (`trusted_data_t3_r.
    per_example`), each knob its median, a switch on above 0.5, each mic its argmax (`full_space.answer_settings`), on
    the example's own amp and the section class's S. With `--name S` or `--name constant`, those answers (the
    constant from the ladder's training labels). -> sound/answers/<name>-<which>.json."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import trusted_data_t3 as T3
    from learn import trusted_data_t3_r as R

    e = require("phase_3")
    if args.amp_shift or args.mastered or args.readout in ("sws", "nc"):
        require("phase_3_isolated")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    ids = sorted(set(sum(sample_ids(2 * SAMPLE_N).values(), [])))
    ms = A.L.menu_S()
    rows = rung_rows(kept, rend, ids)
    out = {}
    if args.name in ("truth", "truth-on-S-select"):
        # positive controls: the label's own setting on its own select must reproduce the stored target render; on
        # the class start preset's select (where answers are written) it must too, the full setting being written
        menus = T3.Menus()
        from learn import cc_build as CB

        menus.gate_u = CB.load_plan(argparse.Namespace(out=None, smoke=False))["gate_cap"]["unit"]
        for r in rows:
            amp, _, _, sel_own, xf, _, _, _ = T3.full_twin(r["i"], menus)
            if LO.sdict(xf) != rend[r["i"]]["settings"]:
                raise SystemExit(f"{r['i']}: the full twin differs from the rendered label")
            sel = sel_own if args.name == "truth" else ms[r["amp"]][r["cls"]][0]
            out[str(r["i"])] = {"select": sel, "settings": rend[r["i"]]["settings"]}
        tag = args.name
    elif args.name in ("S", "constant"):
        const = constant_of(rung_rows(kept, rend, sp["train"]))
        for r in rows:
            amp = shifted_amp(r["amp"], args.amp_shift)
            sel, S = ms[amp][r["cls"]]
            x = dict(S) if args.name == "S" else T3.constant_full(amp, S, const[(amp, r["cls"])])
            out[str(r["i"])] = {"select": sel, "settings": LO.sdict(x)}
        tag = args.name + amp_tag(args.amp_shift)
    else:
        nets, rec = [], None
        seeds = [int(z) for z in args.seeds.split(",")]
        for sd in seeds:
            if not (out_dir() / "runs" / f"{args.name}-{sd}.json").exists():
                raise SystemExit(f"{args.name}-{sd}: no run")
            n, rec = load_run(args.name, sd, args.which)
            nets.append(n)
        doubled = doubled_ids() if dropped["doubles"] == "fixed" else frozenset()
        srows = [dict(r, amp=shifted_amp(r["amp"], args.amp_shift)) for r in rows]   # told (and rendered on) this amp
        path_of = rung_path(croot, args.input_rung or rec["rung"], doubled)   # D_fix: the stems beside (`--input-rung d`)
        if args.mastered:
            if rec["rung"] != "a":
                raise SystemExit("--mastered is step 15's isolated test on P2a")
            path_of = mastered_inputs(croot, kept, rend, ids)
        data = RungData(srows, path_of, aug=False)
        X, C, who = read_inputs(data)
        outs = F.run_nets(nets, X, C)
        Y = [np.repeat(data.Y[q], 2, axis=0) for q in range(6)]
        ex = R.per_example(outs, who, Y)
        pull = fit_knob_pull(nets, croot, kept, rend, sp, rec) if args.readout == "pulled" else None
        sw_rule = switch_rule(args, nets, croot, kept, rend, sp, rec) if args.readout in ("sws", "nc") else None
        for r in srows:
            e = ex[r["i"]]
            sel, S = ms[r["amp"]][r["cls"]]
            mics = [int(np.argmax(m)) for m in e["mic_p"]]
            cont, swp = e["a2"], np.array(e["sw_p"], np.float64)
            if pull is not None:                   # D_CC's readout: each knob pulled toward the constant
                med, table = pull
                cell = (r["amp"], r["cls"])
                b, _ = DS.cell_b(table, cell, F.cell_masks(r["amp"])[0])
                cont = DS.pull(e["a2"], med[cell], b)
            if sw_rule is not None:
                swp = sw_rule(swp, r["amp"], r["cls"], S)
            x = F.answer_settings(r["amp"], S, cont, swp, mics)
            out[str(r["i"])] = {"select": sel, "settings": LO.sdict(x)}
        tag = (f"{args.name}-{args.which}" + ("" if seeds == [SEEDS[0]] else "-x" + "+".join(map(str, seeds)))
               + ("" if args.readout == "plain" else f"-{args.readout}") + ("-mast" if args.mastered else "")
               + amp_tag(args.amp_shift) + (f"-on{args.input_rung}" if args.input_rung else ""))
    save(out_dir() / SOUND_DIR / "answers" / f"{tag}.json", {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_3",
                                                            "name": tag, "answers": out, "nc_fit": dict(NC_FIT),
                                                            "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"ANSWERS DONE {tag}: {len(out)} examples")


def shifted_amp(amp, k):
    """The amp k places on in AMPS (the amp-mismatch test tells and renders a wrong amp)."""
    from learn import full_space as F

    return F.AMPS[(F.AMPS.index(amp) + int(k)) % len(F.AMPS)]


def amp_tag(k):
    return f"-amp+{k}" if k else ""


def mastered_inputs(croot, kept, rend, ids):
    """Step 15's isolated test: P2a's input (the target at its gain in its mix) through the mastering compressor with
    each example's own drawn parameters, whether or not its mix was drawn mastered. Built in memory into
    inputs/<i>-tgtl-mast.npz. -> i -> path."""
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import song_aug as SA
    from learn import trusted_data as T

    built = T.rows_of(croot, CB.STAGE, "build")
    for i in ids:
        p = input_path(DATA, i, "tgtl-mast")
        if p.exists():
            continue
        rw = rend[i]
        y = np.asarray(G.read_flac(T.flac_path(croot, CB.STAGE, i, "target"), rw["target"]["scale"],
                                   rw["target"]["sha256"]), np.float64) * 10 ** (built[i]["gains_db"]["ga"] / 20)
        _, mrng = DS.master_draw(i)
        f, lu, _ = DS.half_features(SA.compress(y, mrng))
        DS._save_npz(p, sA=f["A"], sB=f["B"], lufs=[lu["A"], lu["B"]])
    return lambda i: input_path(DATA, i, "tgtl-mast")


def s_switch_state(S, amp, name):
    """S's own on/off for one switch head (the springs' derived switch from S's level); None if S does not store it."""
    from learn import full_space as F

    d = F.by_name()[name]
    if d.key == F.SPRING_KEY:
        a = next(a for a, q in F.SPRING.items() if q[0] == d.module)
        return F.spring_on(S, a) if a == amp else None
    v = S.get((d.module, d.key))
    return None if v is None else F._truthy(v)


NC_DELTAS = (0.0, 0.05, 0.10, 0.15, 0.20)
NC_FIT = {}                         # the near-chance rule's fitted delta, saved with its answers


def switch_rule(args, nets, croot, kept, rend, sp, rec):
    """Step 27's readouts, fitted on FS: "sws" keeps S's state for every switch R0 did not find readable on FS (the
    model's own read, `reads/<name>-<which>.json`); "nc" (F20's near-chance rule) gives a switch whose probability
    lies within δ of 0.5 the constant's majority, δ the candidate with the best FS switch agreement (ties to the
    smaller). -> f(sw_p, amp, cls, S) -> sw_p."""
    import numpy as np

    from learn import full_space as F

    if args.readout == "sws":
        rd = json.loads((out_dir() / "reads" / f"{args.name}-{args.which}.json").read_text())
        if sorted(rd["seeds"]) != sorted(int(z) for z in args.seeds.split(",")):
            raise SystemExit(f"the stored read is of seeds {rd['seeds']}, the answers of {args.seeds}: re-read first")
        r0 = rd["sets"]["fs"]["rows"]
        unread = {r["name"] for r in r0 if r["kind"] == "switch" and not r["readable"]}

        def f(swp, amp, cls, S):
            out = swp.copy()
            for j, n in enumerate(F.SW):
                if n in unread:
                    st = s_switch_state(S, amp, n)
                    if st is not None:
                        out[j] = 1.0 if st else 0.0
            return out
        return f
    const = constant_of(rung_rows(kept, rend, rec["train_ids"]))
    ex, rows = fs_examples(nets, croot, kept, rend, sp, rec)
    cell = {r["i"]: (r["amp"], r["cls"]) for r in rows}

    def decide(p, maj, d):
        return (bool(maj) if maj is not None and abs(p - 0.5) < d else p > 0.5)

    best = None
    for d in NC_DELTAS:
        hits = n = 0
        for i, e in ex.items():
            maj = const[cell[i]]["sw"]
            for j in np.flatnonzero(np.asarray(e["sm"]) > 0):
                hits += decide(float(e["sw_p"][j]), maj[j], d) == (float(e["s"][j]) > 0.5)
                n += 1
        if best is None or hits / n > best[1] + 1e-12:
            best = (d, hits / n)
    delta = best[0]
    print(f"near-chance rule: δ = {delta} (FS switch agreement {best[1]:.4f})", flush=True)
    NC_FIT.update(delta=delta, fs_agreement=best[1])

    def g(swp, amp, cls, S):
        maj = const[(amp, cls)]["sw"]
        return np.array([(1.0 if decide(float(p), maj[j], delta) else 0.0) for j, p in enumerate(swp)])
    return g


def fs_examples(nets, croot, kept, rend, sp, rec):
    """A ladder model's per-example readout on FS (`trusted_data_t3_r.per_example`) and FS's rows."""
    import numpy as np

    from learn import full_space as F
    from learn import trusted_data_t3_r as R

    rows = rung_rows(kept, rend, sp["fs"])
    data = RungData(rows, rung_path(croot, rec["rung"]), aug=False)
    X, C, who = read_inputs(data)
    return R.per_example(F.run_nets(nets, X, C), who, [np.repeat(data.Y[q], 2, axis=0) for q in range(6)]), rows


def fit_knob_pull(nets, croot, kept, rend, sp, rec):
    """D_CC's readout pull (`direct_stems.fit_pull_table`, as `cc_readout.cmd_fit`) fitted on FS for a ladder model:
    per (amp, section class) and knob, b in [0, 1] minimising the knob error of constant + b (answer - constant),
    the constant being the run's own training labels' medians. -> (medians, table)."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import trusted_data_t3 as T3
    from learn import trusted_data_t3_r as R

    enc = T3.encode_for(T3.FULL)
    med = DS.label_medians([dict(r, base=r["cls"]) for r in rung_rows(kept, rend, rec["train_ids"])],
                           lambda lab: enc(lab)[:6])
    rows = rung_rows(kept, rend, sp["fs"])
    data = RungData(rows, rung_path(croot, rec["rung"]), aug=False)
    X, C, who = read_inputs(data)
    ex = R.per_example(F.run_nets(nets, X, C), who, [np.repeat(data.Y[q], 2, axis=0) for q in range(6)])
    ans = {i: e["a2"] for i, e in ex.items()}
    lab = {i: (e["c"], e["cm"]) for i, e in ex.items()}
    cell_of = {r["i"]: (r["amp"], r["cls"]) for r in rows}
    return med, DS.fit_pull_table(ans, lab, cell_of, med)


def cmd_sound_render(args):
    """One shard of the sample's renders for the answer sets named in `--names` (comma-separated tags): each answer
    through the example's own measure DI in its own primed process (`audibility_measure.fresh_render`, as the targets
    were rendered), trimmed as the targets, judged against the stored target render on both halves. isolate=True; at
    most 3 render processes; the 31 GB guard. -> sound/judge/<tag>/<i>.json (a done example is kept)."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    e = require("phase_3_sound")
    a = argparse.Namespace(out=None, smoke=False)
    croot = CB.V.out_root(a)
    plan = CB.load_plan(a)
    ex = {x["i"]: x for x in plan["examples"]}
    rend = T.rows_of(croot, CB.STAGE, "render")
    ctx = CB.ctx_for(a)
    n_each = int(e.get("sample_n", SAMPLE_N))
    ids = sorted(set(sum(sample_ids(n_each).values(), [])))
    k, n = args.shard
    mine = [i for j, i in enumerate(sorted(ids, key=lambda i: (ex[i]["section"], i))) if j % n == k]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    renders = 0
    LO._wait_cap()
    for tag in args.names.split(","):
        ans = json.loads((out_dir() / SOUND_DIR / "answers" / f"{tag}.json").read_text())["answers"]
        asha = answers_sha(ans)
        gd = out_dir() / SOUND_DIR / "judge" / tag
        di_cache = {}
        for i in mine:
            gp = gd / f"{i}.json"
            if gp.exists():
                old = json.loads(gp.read_text()).get("answers_sha256")
                if old is not None and old != asha:
                    raise SystemExit(f"{gp}: rendered from other answers; move sound/judge/{tag} aside first")
                continue
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            x = ex[i]
            if x["section"] not in di_cache:
                sec = ctx.sections[x["section"]]
                d = B.measure(PS.section_audio(sec["path"], sec["start_s"])).astype(np.float32)
                di_cache = {x["section"]: d}
            di = di_cache[x["section"]]
            rw = rend[i]
            tgt = np.asarray(G.read_flac(T.flac_path(croot, CB.STAGE, i, "target"), rw["target"]["scale"],
                                         rw["target"]["sha256"]), np.float64)
            st = LO.tdict(ans[str(i)]["settings"])
            y = AM.fresh_render(CB.new_renderer, di, ans[str(i)]["select"], st, st)
            renders += 2
            y = (y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]]
            j = K.judge(tgt, np.asarray(y, np.float64), np.asarray(di, np.float64)[trim[0]:trim[1]], 0)
            save(gp, {"i": i, "tag": tag, "judge": j, "render_sha256": AM.audio_sha(y), "answers_sha256": asha,
                      "settings_sha256": answers_sha(ans[str(i)])})
        print(f"{tag}: shard {k}/{n} done; renders so far {renders}", flush=True)
    print(f"SOUND-RENDER DONE {k}/{n}: {renders} renders")


def cmd_sound_recheck(args):
    """The share amendment's check on stored renders (`phase_dfix_share`): `--n` seeded judged examples of each tag in
    `--names` rendered again exactly as `sound-render` renders them, their audio hashes compared with the stored ones.
    -> sound/recheck-<tag>.json; refuses (after saving) on any mismatch."""
    import random

    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    require("phase_dfix_share")
    a = argparse.Namespace(out=None, smoke=False)
    plan = CB.load_plan(a)
    ex = {x["i"]: x for x in plan["examples"]}
    ctx = CB.ctx_for(a)
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    bad = 0
    for tag in args.names.split(","):
        ans = json.loads((out_dir() / SOUND_DIR / "answers" / f"{tag}.json").read_text())["answers"]
        gd = out_dir() / SOUND_DIR / "judge" / tag
        done = sorted(int(q.stem) for q in gd.glob("*.json"))
        pick = sorted(random.Random(f"{DFIX_SEED}|recheck|{tag}").sample(done, min(args.n, len(done))))
        rows = []
        for i in pick:
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            old = json.loads((gd / f"{i}.json").read_text())
            if old.get("answers_sha256") != answers_sha(ans):
                raise SystemExit(f"{gd / f'{i}.json'}: rendered from other answers than {tag}.json holds now")
            sec = ctx.sections[ex[i]["section"]]
            di = B.measure(PS.section_audio(sec["path"], sec["start_s"])).astype(np.float32)
            st = LO.tdict(ans[str(i)]["settings"])
            y = AM.fresh_render(CB.new_renderer, di, ans[str(i)]["select"], st, st)
            y = (y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]]
            new = AM.audio_sha(y)
            rows.append({"i": i, "stored": old["render_sha256"], "new": new, "same": new == old["render_sha256"]})
        miss = [r_["i"] for r_ in rows if not r_["same"]]
        bad += len(miss)
        save(out_dir() / SOUND_DIR / f"recheck-{tag}.json", {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_dfix_share",
                                                              "tag": tag, "rows": rows, "mismatched": miss,
                                                              "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"SOUND-RECHECK {tag}: {len(rows) - len(miss)} of {len(rows)} renders identical", flush=True)
    if bad:
        raise SystemExit(f"SOUND-RECHECK: {bad} renders differ from the stored ones")
    print("SOUND-RECHECK DONE")


def log_ratio(ja, jb):
    """The mean over both halves of ln(d_a / d_b); None when either is missing or not finite."""
    v = []
    for h in ("A", "B"):
        x, y = (ja or {}).get(h), (jb or {}).get(h)
        if x is None or y is None or not (math.isfinite(x) and math.isfinite(y)) or x <= 0 or y <= 0:
            return None
        v.append(math.log(x / y))
    return sum(v) / len(v)


def cmd_sound_report(args):
    """The by-sound rows on the sample: each tag in `--names` against S and the constant, and the paired locating rows
    between consecutive tags (`--names` in ladder order). FS band-clustered; NS section-clustered (2 bands)."""
    from learn import cc_build as CB

    e = require("phase_3_sound")
    a = argparse.Namespace(out=None, smoke=False)
    ex = {x["i"]: x for x in CB.load_plan(a)["examples"]}
    n_each = int(e.get("sample_n", SAMPLE_N))
    ids = sample_ids(n_each)
    tags = args.names.split(",")

    def judge(tag, i):
        p = out_dir() / SOUND_DIR / "judge" / tag / f"{i}.json"
        return json.loads(p.read_text())["judge"] if p.exists() else None

    pairs = [(t, "S") for t in tags] + [(t, "constant") for t in tags] + list(zip(tags, tags[1:]))
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {'phase_5b2' if args.by_mode else 'phase_3_sound'}", "sample_n": n_each,
           "rows": {}}
    groups = [(set_name, None, sids) for set_name, sids in ids.items()]
    if args.by_mode:                                   # 5B.2's arm P: each set split by the example's draw mode
        groups += [(f"{set_name}-{m}", m, [i for i in sids if ex[i]["mode"] == m])
                   for set_name, sids in ids.items() for m in ("factory", "start", "wide")]
    for set_name, mode, sids in groups:
        for ta, tb in pairs:
            rows, missing, refused = [], 0, 0
            for i in sids:
                ja, jb = judge(ta, i), judge(tb, i)
                if ja is None or jb is None:
                    missing += 1
                    continue
                if any(not math.isfinite(z[h]) for z in (ja, jb) for h in ("A", "B")):
                    refused += 1                   # a judge refusal (a silent render): listed, never dropped quietly
                    continue
                v = log_ratio(ja, jb)
                cl = ex[i]["band"] if set_name.startswith("fs") else ex[i]["section"]
                rows.append((cl, ex[i]["section"], v))
            c = clustered(rows)
            key = f"{ta} - {tb}"
            out["rows"].setdefault(key, {})[set_name] = {
                **{k: c.get(k) for k in ("mean", "lo90", "hi90", "clusters", "clusters_negative", "clusters_positive",
                                         "part_weighted", "parts")},
                "clustered_by": "band" if set_name.startswith("fs") else "section (NS is 2 bands)", "missing": missing,
                "judge_refused": refused}
            r = out["rows"][key][set_name]
            if r["mean"] is not None:
                iv = "" if r["lo90"] is None else f" [{r['lo90']:+.4f}, {r['hi90']:+.4f}]"
                print(f"  {key:40s} {set_name}: {r['mean']:+.4f}{iv} ({r['clusters']} {r['clustered_by'].split()[0]}s, "
                      f"{r['clusters_negative']} better){' MISSING ' + str(missing) if missing else ''}"
                      f"{' REFUSED ' + str(refused) if refused else ''}")
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if not args.label or args.label == "p4":
        raise SystemExit("--label names the sound report (report-<label>.json); report.json is the ladder's, kept")
    save(out_dir() / SOUND_DIR / f"report-{args.label}.json", out)
    print("SOUND-REPORT DONE")


# --- the backing-variety test (F17): the same targets in many backings, zero renders ----------------------------------

BACKINGS_K = 8
BACKINGS_SEED = 20261035


def backing_draws(train_ids, kept, k=BACKINGS_K, seed=BACKINGS_SEED, secs=None):
    """For each training example, k backing sections drawn from `secs` (default: the training examples' sections) of
    other songs, each with a vocal flag (p 0.5; it selects the vocal stems where the section has them).
    -> {i: [(section, vocals)]}."""
    import random

    secs = sorted(secs if secs is not None else {kept[i]["section"] for i in train_ids})
    by_song = {}
    for x in secs:
        by_song.setdefault(session_of(x), []).append(x)
    out = {}
    for i in sorted(train_ids):
        rng = random.Random(f"{seed}|{i}")
        own = session_of(kept[i]["section"])
        pool = [x for x in secs if session_of(x) != own]
        out[i] = [(rng.choice(pool), rng.random() < 0.5) for _ in range(k)]
    return out


def backing_path(i, k, root=DATA):
    return input_path(root, i, f"mixb-k{k}")


BACKING_FLOOR_LUFS = -50.0           # a bare backing quieter than this is silent: out of the pool, no variants


def bare_tracks(x, vocals):
    """A section's non-guitar stems (no stand-in) in one vocal variant (`trusted_data.backing_tracks` less the amp
    tracks)."""
    has_v = x["stems"]["v"] != x["stems"]["n"]
    return list(x["stems"]["v" if (vocals and has_v) else "n"])


def cmd_build_backings(args):
    """The backing-variety test's inputs (CPU, zero renders). Each training example's stored target in BACKINGS_K other
    songs' non-guitar backings, built so that only the backing's source changes from its P2b input: P2b's own overall
    gain (stored `ga`), and a backing gain that gives the new bare backing the loudness its own bare backing had in P2b
    (stored `gb` + LUFS(own bare backing) - LUFS(new bare backing)); its own mastering draw. Sections whose bare backing
    is silent (below BACKING_FLOOR_LUFS) leave the pool, and an example whose own bare backing is silent gets no
    variant (both counted). A first pass measures every training section's bare-backing loudness once
    (`backings/levels.json`); then one shard of backing sections, each section's audio read once."""
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_aug as SA
    from learn import trusted_data as T

    e = require("phase_3_backings")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    a = argparse.Namespace(out=None, smoke=False)
    ctx = CB.ctx_for(a)
    stems = T.Stems(ctx)
    built = T.rows_of(croot, CB.STAGE, "build")
    one = {}
    for x in kept.values():
        one.setdefault(x["section"], x)
    lp = out_dir() / "inputs" / "backings-levels.json"
    if not lp.exists():
        if args.shard != (0, 1):
            raise SystemExit("run build-backings --shard 0/1 --levels-only first")
        lv = {}
        for sec in sorted({kept[i]["section"] for i in sp["train"]}):
            lv[sec] = {str(v): float(SA.lufs(stems.get(sec, bare_tracks(one[sec], v)))) for v in (False, True)}
        save(lp, {"rule": f"bare backing LUFS per vocal variant; below {BACKING_FLOOR_LUFS} is silent", "levels": lv})
        if args.levels_only:
            print(f"LEVELS DONE: {len(lv)} sections")
            return
    lv = json.loads(lp.read_text())["levels"]
    silent = sorted(x for x, v in lv.items() if min(v.values()) < BACKING_FLOOR_LUFS)
    train = [i for i in sp["train"] if kept[i]["section"] not in silent]
    no_var = sorted(set(sp["train"]) - set(train))
    pool_secs = [x for x in sorted(lv) if x not in silent]
    draws = backing_draws(train, kept, secs=pool_secs)
    jobs = {}
    for i, ds_ in draws.items():
        for k, (sec, voc) in enumerate(ds_):
            jobs.setdefault(sec, []).append((i, k, voc))
    kk, n = args.shard
    mine = [x for j, x in enumerate(sorted(jobs)) if j % n == kk]
    t0, done = time.time(), 0
    for m, sec in enumerate(mine):
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        backs = {v: stems.get(sec, bare_tracks(one[sec], v)) for v in (False, True)}
        for i, k, voc in jobs[sec]:
            p = backing_path(i, k)
            if p.exists():
                continue
            x, rw, bw = kept[i], rend[i], built[i]
            own_voc = bool(x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"])
            y = np.asarray(G.read_flac(T.flac_path(croot, CB.STAGE, i, "target"), rw["target"]["scale"],
                                       rw["target"]["sha256"]), np.float64)
            gb = bw["gains_db"]["gb"] + lv[x["section"]][str(own_voc)] - lv[sec][str(voc)]
            ga = bw["gains_db"]["ga"]
            mix = (y + backs[voc] * 10 ** (gb / 20)) * 10 ** (ga / 20)
            mastered, mrng = DS.master_draw(i)
            if mastered:
                mix = SA.compress(mix, mrng)
            f, lu, _ = DS.half_features(mix)
            DS._save_npz(p, sA=f["A"], sB=f["B"], lufs=[lu["A"], lu["B"]], backing=sec, vocals=bool(voc),
                         gains=[gb, ga])
            done += 1
        if m % 10 == 0:
            print(f"backing section {m + 1}/{len(mine)}: {done} built; {(time.time() - t0) / max(1, done):.2f} s each",
                  flush=True)
    save(out_dir() / "inputs" / "backings-pool.json", {"silent_sections": silent, "examples_without_variants": no_var,
                                                       "pool_sections": len(pool_secs), "train": len(sp["train"])})
    print(f"BUILD-BACKINGS DONE {kk}/{n}: {done} built; {len(silent)} silent sections out of the pool; "
          f"{len(no_var)} examples without variants")


class BackingData(RungData):
    """P2b's data with the backing-variety test's variants: in training each example shows, per epoch, its own P2b
    input or one of its BACKINGS_K variants (a seeded draw per (i, epoch)); eval reads its own P2b input."""

    def __init__(self, rows, path_of, train_ids):
        import numpy as np

        super().__init__(rows, path_of, aug=False)
        pool = json.loads((out_dir() / "inputs" / "backings-pool.json").read_text())
        without = set(pool["examples_without_variants"])
        complete = {i for i in train_ids if all(backing_path(i, k).exists() for k in range(BACKINGS_K))}
        if set(train_ids) - complete != without & set(train_ids):
            raise SystemExit(f"the backing build is incomplete: {len(set(train_ids) - complete - without)} training "
                             "examples lack variant files")
        self.counts = {"with_variants": len(complete), "without_variants": len(without & set(train_ids))}
        self.V = {}
        for j, r in enumerate(rows):
            if r["i"] in complete:
                arr = np.zeros((BACKINGS_K, 2, 96, 446), np.uint8)
                lu = np.zeros((BACKINGS_K, 2), np.float32)
                for k in range(BACKINGS_K):
                    d = np.load(backing_path(r["i"], k))
                    arr[k, 0], arr[k, 1], lu[k] = d["sA"], d["sB"], d["lufs"]
                self.V[j] = (arr, lu)

    def batch(self, idx, epoch, dev):
        import random

        import numpy as np

        if epoch < 0:
            return super().batch(idx, epoch, dev)
        saved = {}
        for j in np.asarray(idx):
            j = int(j)
            if j in self.V:
                v = random.Random(f"{BACKINGS_SEED}|{self.rows[j]['i']}|{epoch}").randrange(BACKINGS_K + 1)
                if v:
                    saved[j] = (self.X[j].copy(), self.L[j].copy())
                    self.X[j], self.L[j] = self.V[j][0][v - 1], self.V[j][1][v - 1]
        try:
            return super().batch(idx, epoch, dev)
        finally:
            for j, (x, lu) in saved.items():
                self.X[j], self.L[j] = x, lu


# --- phase 5A: backing variety at scale (zero renders) ----------------------------------------------------------------

WIDE_K = 24
WIDE_SEED = 20261037
WIDE_WINDOWS = 20                   # at most this many active windows per extra session
WIDE_ACTIVE_LUFS = -33.0            # a window's bare backing (no vocals) must be at least this loud (the training
                                    # sections' bare backings span -32.8 to -12.7: the review, 2026-10-31)
WIDE_MIN_STEMS = 2                  # a session gives backings only with at least this many non-vocal stems
WIDE_EXCLUDE_BANDS = frozenset(b for b, _ in PR.VREAL.values())


def bare_backing(sd, tracks, start_s):
    """A session's tracks summed at its balance at `start_s`, folded to mono as a centred source and trimmed as the
    sections are (`trusted_data.Stems.get`'s rule)."""
    import numpy as np
    import soundfile as sf

    from learn import pretrain_set as PS
    from learn import trusted_data as T

    sess = pathlib.Path(sd)
    b = np.zeros(int(round((PS.SEC_S + PS.TRIM_S) * PS.SR)))
    for t in tracks:
        fold = T.pan_fold(0.0) if sf.info(str(sess / t)).channels == 1 else 1.0
        b += PS.section_audio(sess / t, start_s) * fold
    return b[int(PS.TRIM_S * PS.SR):]


def wide_pool_path():
    return out_dir() / "inputs" / "backings-wide-pool.json"


def cmd_wide_pool(args):
    """Phase 5A's backing pool (zero renders): the ladder's training sections' bare backings, plus up to WIDE_WINDOWS
    active 10-s windows (bare backing at least WIDE_ACTIVE_LUFS) from every other session whose stems were heard clean,
    outside V-real's bands and the two NS songs, with at least WIDE_MIN_STEMS non-vocal stems. An extra session's stems
    are its heard-clean session-wide list (`trusted_data.stems_for` without takes: the stems the spot-check covered,
    the strictest rule). The training sections keep P2b's own stems, as P2b-bk8 does, which may carry that song's
    other guitars. Every entry's bare loudness is measured for both vocal variants. A pool is never overwritten once
    variants are built from it. -> inputs/backings-wide-pool.json."""
    import numpy as np
    import soundfile as sf

    from learn import cc_build as CB
    from learn import song_aug as SA
    from learn import trusted_data as T

    e = require("phase_5a")
    if wide_pool_path().exists() and any((DATA / "inputs").glob("*-mixbw-k*.npz")):
        raise SystemExit("variants are built from the stored pool: move them aside before rebuilding it")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    a = argparse.Namespace(out=None, smoke=False)
    plan = CB.load_plan(a)
    inv = CB.cc_inventory()
    tr = T.load_lists(croot)
    ver = CB._ver(a)
    verified = CB.verified_stems(tr, ver, inv)
    scan, floor = CB.merged_takes()
    levels = json.loads((out_dir() / "inputs" / "backings-levels.json").read_text())["levels"]
    one = {}
    for x in kept.values():
        one.setdefault(x["section"], x)
    entries = []
    for sec in sorted(levels):                               # the training sections (P2b-bk8's pool)
        x = one[sec]
        has_v = x["stems"]["v"] != x["stems"]["n"]
        entries.append({"id": sec, "session": session_of(sec), "sd": None, "kind": "training",
                        "tracks": {"n": list(x["stems"]["n"]), "v": list(x["stems"]["v" if has_v else "n"])},
                        "start_s": None, "lufs": levels[sec]})
    used = {pathlib.Path(x["session_dir"]).name for x in kept.values()}
    ns = {s_.split("/")[-1] for s_ in NS_SESSIONS}
    by_sd = {}
    for r in inv.values():
        if r.get("session_dir"):
            by_sd.setdefault(r["session_dir"], r)
    skipped = {}
    for sd in plan["verified_stems_sessions"]:
        name = pathlib.Path(sd).name
        rec = by_sd.get(sd)
        if name in used or name in ns or rec is None:
            skipped[name] = "a ladder song or NS" if rec is not None else "no inventory record"
            continue
        if rec.get("band") in WIDE_EXCLUDE_BANDS:
            skipped[name] = "a V-real band"
            continue
        st = scan.get(sd)
        if not st:
            skipped[name] = "no stem scan"
            continue
        withv, nov = T.stems_for(rec, verified, sd)
        if len(nov) < WIDE_MIN_STEMS:
            skipped[name] = f"{len(nov)} heard-clean non-vocal stems (fewer than {WIDE_MIN_STEMS})"
            continue
        dur = max(sf.info(str(pathlib.Path(sd) / t)).duration for t in nov)
        starts = [5.0 + 10.0 * k for k in range(int((dur - 16.0) // 10.0) + 1)]
        active = []
        for s0 in starts:
            ln = float(SA.lufs(bare_backing(sd, nov, s0)))
            if ln >= WIDE_ACTIVE_LUFS:
                active.append((s0, ln))
        if not active:
            skipped[name] = "no active window"
            continue
        m_ = min(WIDE_WINDOWS, len(active))             # every active window when there are at most WIDE_WINDOWS
        pick = [active[round(j * (len(active) - 1) / max(1, m_ - 1))] for j in range(m_)]
        pick = sorted({p[0]: p for p in pick}.values())
        for s0, ln in pick:
            lv = ln if withv == nov else float(SA.lufs(bare_backing(sd, withv, s0)))
            entries.append({"id": f"{name}@{s0:.1f}", "session": name, "sd": sd, "kind": "extra",
                            "tracks": {"n": nov, "v": withv}, "start_s": s0,
                            "lufs": {"False": ln, "True": lv}})
        print(f"{name}: {len(pick)} windows ({len(active)} active); {len(nov)} stems, vocals "
              f"{len(withv) - len(nov)}", flush=True)
    save(wide_pool_path(), {"rule": cmd_wide_pool.__doc__, "entries": entries, "sha256": pool_sha(entries), "skipped": skipped,
                            "sessions": sorted({e_["session"] for e_ in entries}),
                            "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"WIDE POOL DONE: {len(entries)} entries from {len({e_['session'] for e_ in entries})} sessions; "
          f"skipped {skipped}")


def wide_draws(train_ids, kept, entries, k=WIDE_K, seed=WIDE_SEED):
    """For each training example, k pool entries: a session drawn uniformly among the pool's sessions other than the
    example's own song, then one of its entries, and a vocal flag (p 0.5). -> {i: [(entry index, vocals)]}."""
    import random

    by_s = {}
    for j, e_ in enumerate(entries):
        by_s.setdefault(e_["session"], []).append(j)
    out = {}
    for i in sorted(train_ids):
        rng = random.Random(f"{seed}|{i}")
        own = pathlib.Path(session_of(kept[i]["section"])).name
        sess = sorted(x for x in by_s if x != own and x != session_of(kept[i]["section"]))
        out[i] = [(rng.choice(by_s[rng.choice(sess)]), rng.random() < 0.5) for _ in range(k)]
    return out


def pool_sha(entries):
    import hashlib

    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


def wide_path(i, k, root=DATA):
    return input_path(root, i, f"mixbw-k{k}")


def cmd_build_wide(args):
    """Phase 5A's inputs (CPU, zero renders): each training example's stored target in WIDE_K pool backings, exactly as
    `build-backings` builds its variants (P2b's own overall gain; a backing gain that gives the new bare backing its own
    bare backing's P2b loudness; its own mastering draw). One shard of pool entries, each entry's audio read once."""
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_aug as SA
    from learn import trusted_data as T

    e = require("phase_5a")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    a = argparse.Namespace(out=None, smoke=False)
    ctx = CB.ctx_for(a)
    stems = T.Stems(ctx)
    built = T.rows_of(croot, CB.STAGE, "build")
    pool = json.loads(wide_pool_path().read_text())["entries"]
    psha = pool_sha(pool)
    own_lv = json.loads((out_dir() / "inputs" / "backings-levels.json").read_text())["levels"]
    draws = wide_draws(sp["train"], kept, pool)
    jobs = {}
    for i, ds_ in draws.items():
        for k, (j, voc) in enumerate(ds_):
            jobs.setdefault(j, []).append((i, k, voc))
    kk, n = args.shard
    mine = [j for q, j in enumerate(sorted(jobs)) if q % n == kk]
    t0, done = time.time(), 0
    for m, j in enumerate(mine):
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        ent = pool[j]
        if ent["kind"] == "training":
            backs = {v: stems.get(ent["id"], ent["tracks"]["v" if v else "n"]) for v in (False, True)}
        else:
            backs = {v: bare_backing(ent["sd"], ent["tracks"]["v" if v else "n"], ent["start_s"]) for v in (False, True)}
        for i, k, voc in jobs[j]:
            p = wide_path(i, k)
            if p.exists():
                if str(np.load(p)["pool_sha256"]) != psha:
                    raise SystemExit(f"{p}: built from another pool")
                continue
            x, rw, bw = kept[i], rend[i], built[i]
            own_voc = bool(x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"])
            y = np.asarray(G.read_flac(T.flac_path(croot, CB.STAGE, i, "target"), rw["target"]["scale"],
                                       rw["target"]["sha256"]), np.float64)
            gb = bw["gains_db"]["gb"] + own_lv[x["section"]][str(own_voc)] - ent["lufs"][str(bool(voc))]
            ga = bw["gains_db"]["ga"]
            mix = (y + backs[bool(voc)] * 10 ** (gb / 20)) * 10 ** (ga / 20)
            mastered, mrng = DS.master_draw(i)
            if mastered:
                mix = SA.compress(mix, mrng)
            f, lu, _ = DS.half_features(mix)
            DS._save_npz(p, sA=f["A"], sB=f["B"], lufs=[lu["A"], lu["B"]], backing=ent["id"], vocals=bool(voc),
                         gains=[gb, ga], pool_sha256=psha)
            done += 1
        if m % 20 == 0:
            print(f"pool entry {m + 1}/{len(mine)}: {done} built; {(time.time() - t0) / max(1, done):.2f} s each",
                  flush=True)
    print(f"BUILD-WIDE DONE {kk}/{n}: {done} built")


class WideData(RungData):
    """P2b's data with phase 5A's variants: per epoch each training example shows its own P2b input or one of its
    WIDE_K pool variants (a seeded draw per (i, epoch)); eval reads its own P2b input. Refuses an incomplete build."""

    def __init__(self, rows, path_of, train_ids):
        import numpy as np

        super().__init__(rows, path_of, aug=False)
        missing = [i for i in train_ids if not all(wide_path(i, k).exists() for k in range(WIDE_K))]
        if missing:
            raise SystemExit(f"phase 5A's build is incomplete: {len(missing)} training examples lack variants")
        psha = pool_sha(json.loads(wide_pool_path().read_text())["entries"])
        self.V = {}
        for j, r in enumerate(rows):
            if r["i"] in train_ids:
                arr = np.zeros((WIDE_K, 2, 96, 446), np.uint8)
                lu = np.zeros((WIDE_K, 2), np.float32)
                for k in range(WIDE_K):
                    d = np.load(wide_path(r["i"], k))
                    if str(d["pool_sha256"]) != psha:
                        raise SystemExit(f"{wide_path(r['i'], k)}: built from another pool")
                    arr[k, 0], arr[k, 1], lu[k] = d["sA"], d["sB"], d["lufs"]
                self.V[j] = (arr, lu)
        self.counts = {"with_variants": len(self.V), "variants": WIDE_K}

    def batch(self, idx, epoch, dev):
        import random

        import numpy as np

        if epoch < 0:
            return super().batch(idx, epoch, dev)
        saved = {}
        for j in np.asarray(idx):
            j = int(j)
            if j in self.V:
                v = random.Random(f"{WIDE_SEED}|{self.rows[j]['i']}|{epoch}").randrange(WIDE_K + 1)
                if v:
                    saved[j] = (self.X[j].copy(), self.L[j].copy())
                    self.X[j], self.L[j] = self.V[j][0][v - 1], self.V[j][1][v - 1]
        try:
            return RungData.batch(self, idx, epoch, dev)
        finally:
            for j, (x, lu) in saved.items():
                self.X[j], self.L[j] = x, lu


# --- phase 5B.1: the clean-input model on real reamped amp tracks (an isolated transfer read) ------------------------

REAL_DIR = "real"
REAL_N = 40                         # (section, reamp track) units read, round-robin over the reamp rigs
REAL_SEED = 20261038
AMPS3 = ("pr12", "sw50r", "ac20")


def real_amp_track(sd, track, start_s):
    """A section of one reamped amp track, folded to mono as a centred source, trimmed as the sections are
    (`bare_backing`'s rule)."""
    return bare_backing(sd, [track], start_s)


def real_parts(kept, sp, inv, n=REAL_N, seed=REAL_SEED):
    """5B.1's units: (section, reamp track) for every ladder training or FS section whose DI has reamped amp tracks
    among its own tracks ('Reamp' in the name: the DI re-played through a real amp and mic after the session, so no
    other instrument can be in it). n of them in round-robin order over the rigs (song and track), each rig's own
    units shuffled. -> [{unit, section, track, rig, set, di, band, cls, sd, start_s, di_path}]."""
    units = {}
    for kind in ("train", "fs"):
        for i in sp[kind]:
            x = kept[i]
            for t in inv[x["di"]].get("own") or []:
                if "Reamp" in t:
                    u = f"{x['section']}#{t}"
                    units.setdefault(u, {
                        "unit": u, "section": x["section"], "track": t, "rig": f"{session_of(x['section'])}/{t}",
                        "set": kind, "di": x["di"], "band": x["band"], "cls": x["cls"], "sd": x["session_dir"],
                        "start_s": float(x["section"].split("@")[1]), "di_path": inv[x["di"]]["path"]})
    order = draw_order(sorted(units), {u: units[u]["rig"] for u in units}, n=n, seed=seed)
    return [units[u] for u in order]


def sc_cont(S, amp, a2, const):
    """5B.1b's continuous readout: where S stores a sounding control and the constant is finite, S's unit value plus
    the model's deviation from its labels' constant, clipped to [0, 1]; elsewhere the model's own value."""
    import numpy as np

    from learn import full_space as F

    s_c, s_cm = F.encode(S, amp)[:2]
    a2, const = np.asarray(a2, np.float64), np.asarray(const, np.float64)
    out = a2.copy()
    ok = (s_cm > 0) & np.isfinite(const) & np.isfinite(a2)
    out[ok] = np.clip(s_c[ok] + a2[ok] - const[ok], 0.0, 1.0)
    return out


def real_shift_answers():
    """5B.1b's control (zero renders): S plus the shared shift, one answer per (unit, amp) for both halves. The shift
    is the mean of P2a-Sc - S in unit space on S's sounding continuous controls, over both halves of every unit of
    the same (amp, class) from other DIs (leave-own-DI-out), added to S, clipped to [0, 1]; switches and mics at S's.
    -> real/answers/S-shift.json."""
    import numpy as np

    from learn import full_space as F
    from learn import local_objective as LO

    d = out_dir() / REAL_DIR / "answers"
    sc = json.loads((d / "P2a-Sc.json").read_text())
    s_ans = json.loads((d / "S.json").read_text())["answers"]
    parts = sc["parts"]
    dev = {}
    for prt in parts:
        for amp in AMPS3:
            key = real_key(prt, amp)
            s_c, s_cm = F.encode(LO.tdict(s_ans[key][ANY_HALF]["settings"]), amp)[:2]
            for half in ("A", "B"):
                q = F.encode(LO.tdict(sc["answers"][key][half]["settings"]), amp)[0]
                dev.setdefault((amp, prt["cls"]), []).append((prt["di"], np.where(s_cm > 0, q - s_c, np.nan)))
    out = {}
    for prt in parts:
        for amp in AMPS3:
            key = real_key(prt, amp)
            S = LO.tdict(s_ans[key][ANY_HALF]["settings"])
            s_c, s_cm, s_sw, s_swm, s_k, s_km, _ = F.encode(S, amp)
            others = [v for di, v in dev[(amp, prt["cls"])] if di != prt["di"]]
            shift = np.nanmean(np.stack(others), axis=0)
            c = np.where((s_cm > 0) & np.isfinite(shift), np.clip(s_c + shift, 0.0, 1.0), np.nan)
            sw = [float(v) if m else None for v, m in zip(s_sw, s_swm)]
            mics = [int(v) if m else None for v, m in zip(s_k, s_km)]
            out[key] = {ANY_HALF: {"select": s_ans[key][ANY_HALF]["select"],
                                   "settings": LO.sdict(F.answer_settings(amp, S, c, sw, mics))}}
    save(d / "S-shift.json", {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_5b1b", "tag": "S-shift", "parts": parts,
                              "rule": real_shift_answers.__doc__, "answers": out,
                              "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"S-SHIFT DONE: {len(out)} answers")


def real_key(prt, amp):
    return f"{prt['unit']}|{amp}"


def cmd_real_predict(args):
    """5B.1's answers (zero renders): P2a (both seeds, NS-best, pooled) reads each unit's reamped amp track, brought
    to the median half loudness of its training inputs, on each search half, told the section's class and each
    forced amp; the plain readout on the class's S. Beside it S and the constant of P2a's training labels. With
    `--names P2a-Sc` (5B.1b, ledger phase_5b1b) only the S-centred answer: each sounding continuous control of S at
    S's value plus P2a's deviation from its labels' constant, clipped to the unit interval (`sc_cont`); switches and
    mics at S's. -> real/answers/<tag>.json, keyed '<section>#<track>|<amp>' -> {half or ANY_HALF: {select,
    settings}}."""
    from learn import arm_a_mega53 as A
    from learn import cc_build as CB
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import trusted_data_t3 as T3

    e = require("phase_5b1")
    if args.names in ("Rc", "Rcs2"):
        return real_rc_answers(2 if args.names == "Rcs2" else 1)
    if args.names == "RigO":
        return real_rigo_answers()
    if args.names == "RcM":
        return real_rcm_answers()
    if args.names in ("P2a-pc", "P2a-pcsz", "P2a-real", "P2a-reals2", "P2a-pc-Sc", "P2a-goat", "P2a-goatshuf") \
            or args.names in DFIX_READS or args.names in (FT_BASE, FTM_BASE):
        return real_predict_5b2(args.names)
    if args.names == "S-shift":
        require("phase_5b1b")
        return real_shift_answers()
    only_sc = args.names == "P2a-Sc"
    if only_sc:
        require("phase_5b1b")
    elif args.names:
        raise SystemExit("real-predict writes 5B.1's answers, or with --names P2a-Sc / S-shift only 5B.1b's")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    parts = real_parts(kept, sp, CB.cc_inventory())
    nets, recs = [], []
    for sd in SEEDS:
        n, r_ = load_run("P2a", sd, "best")
        nets.append(n)
        recs.append(r_)
    if any(r_["train_ids"] != recs[0]["train_ids"] for r_ in recs):
        raise SystemExit("5B.1 reads P2a, both seeds on one training set")
    target = p2a_median_lufs(recs[0]["train_ids"])
    const = constant_of(rung_rows(kept, rend, recs[0]["train_ids"]))
    ms = A.L.menu_S()
    out = {"P2a-Sc": {}} if only_sc else {"P2a": {}, "constant": {}, "S": {}}
    for prt in parts:
        ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        g = DE.inference_gain_db(ref, target)
        for amp in AMPS3:
            sel, S = ms[amp][prt["cls"]]
            key = real_key(prt, amp)
            for search in ("A", "B"):
                s8, _, ls, _ = DS.step4_half(ref, ref, search, g)
                x, c = DS.model_input(s8, s8, ls, ls, search, amp, prt["cls"], "Dstem")
                r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
                if only_sc:
                    s_c, _, s_sw, s_swm, s_k, s_km, _ = F.encode(dict(S), amp)
                    sw = [float(v) if m else None for v, m in zip(s_sw, s_swm)]
                    mics = [int(v) if m else None for v, m in zip(s_k, s_km)]
                    out["P2a-Sc"].setdefault(key, {})[search] = {"select": sel, "settings": LO.sdict(
                        F.answer_settings(amp, S, sc_cont(dict(S), amp, r["a2"], const[(amp, prt["cls"])]["cont"]),
                                          sw, mics))}
                    continue
                out["P2a"].setdefault(key, {})[search] = {"select": sel, "settings": LO.sdict(
                    F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"]))}
            if only_sc:
                continue
            out["constant"][key] = {ANY_HALF: {"select": sel, "settings": LO.sdict(
                T3.constant_full(amp, S, const[(amp, prt["cls"])]))}}
            out["S"][key] = {ANY_HALF: {"select": sel, "settings": LO.sdict(S)}}
    for t, a in out.items():
        save(out_dir() / REAL_DIR / "answers" / f"{t}.json", {
            "plan": PLAN, "ledger": f"{LEDGER_ID} {'phase_5b1b' if only_sc else 'phase_5b1'}", "tag": t,
            "parts": parts, "input_lufs": target,
            "models": [r_["model_sha256"]["best"] for r_ in recs], "answers": a,
            "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"REAL PREDICT DONE: {len(parts)} units on {len({p_['rig'] for p_ in parts})} rigs; inputs at "
          f"{target:.2f} LUFS")


def read_phase(name):
    """The ledger phase a read-2 model tag answers under: FT's, a D_fix family member's, 5C's or 5B.2's."""
    if name == FT_BASE:
        return "phase_ft"
    if name == FTM_BASE:
        return "phase_night2"
    if name.startswith("P2b-dfix"):
        return dfix_phase(name)
    return "phase_5c" if name.startswith("P2a-goat") else "phase_5b2"


def real_predict_5b2(name):
    """5B.2's answers on 5B.1's 40 units (zero renders), read exactly as P2a's in 5B.1 (plain readout, both seeds
    NS-best pooled, the input at the model's own training inputs' median loudness): arm P's `P2a-pc` with its labels'
    constant (`P2a-pc-constant`); arm R's `P2a-real`, each unit read by the fold models that never saw its DI's real
    tracks. -> real/answers/<tag>.json."""
    from learn import cc_build as CB
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import trusted_data_t3 as T3

    e = require(read_phase(name))
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    inv = CB.cc_inventory()
    parts = real_parts(kept, sp, inv)
    if name.startswith("P2a-real"):
        folds = real_folds(parts, stage_units(kept, sp, inv, 1) + stage_units(kept, sp, inv, 2))
        sfx = "s2" if name.endswith("s2") else ""
        names = {p_["unit"]: f"P2a-real{folds[p_['di']]}{sfx}" for p_ in parts}
    elif name.startswith("P2a-goat"):                   # 5C: RG and RGshuf, each BKS unit by its DI's fold model
        folds = real_folds(parts, stage_units(kept, sp, inv, 1) + stage_units(kept, sp, inv, 2))
        names = {p_["unit"]: f"{name}{folds[p_['di']]}" for p_ in parts}
    elif name in (FT_BASE, FTM_BASE):                   # FT's read 2: each BKS unit by its DI's FT_k
        folds = real_folds(parts, stage_units(kept, sp, inv, 1) + stage_units(kept, sp, inv, 2))
        names = {p_["unit"]: ft_name(folds[p_["di"]], base=name) for p_ in parts}
    elif name.startswith("P2b-dfix"):                   # D_fix's read 2: each BKS unit by its DI's fold model only
        if name not in DFIX_READS:
            raise SystemExit(f"--names {sorted(DFIX_READS)} (each read by its fold models: an all-labels run saw every"
                         " BKS unit)")
        folds = real_folds(parts, stage_units(kept, sp, inv, 1) + stage_units(kept, sp, inv, 2))
        names = {p_["unit"]: dfix_fold_name(name, folds[p_["di"]]) for p_ in parts}
    else:
        names = {p_["unit"]: name.removesuffix("-Sc") for p_ in parts}
    models = {}
    for nm in sorted(set(names.values())):
        nets, recs = zip(*(load_run(nm, sd, "best") for sd in SEEDS))
        for r_ in recs:
            ft_read_check(r_)
        own = [i for i in recs[0]["train_ids"] if i < REAL_ROW0]
        if any([i for i in r_["train_ids"] if i < REAL_ROW0] != own for r_ in recs):
            raise SystemExit(f"{nm}: the seeds trained on different sets")
        models[nm] = (list(nets), [r_["model_sha256"]["best"] for r_ in recs], model_input_lufs(recs[0]),
                      constant_of(rung_rows(kept, rend, own)))
    ms = A_menu_S()
    out = {name: {}, f"{name}-constant": {}} if name == "P2a-pc" else {name: {}}
    for prt in parts:
        nets, _, target, const = models[names[prt["unit"]]]
        ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        g = DE.inference_gain_db(ref, target)
        backed = dfix_backed(prt["unit"]) if name in (*DFIX_BASES, FT_BASE, FTM_BASE) else None
        for amp in AMPS3:
            sel, S = ms[amp][prt["cls"]]
            key = real_key(prt, amp)
            for search in ("A", "B"):
                if backed is not None:                   # D_fix's primary: the unit's own section's backed input
                    s8, ls = backed[search]
                else:
                    s8, _, ls, _ = DS.step4_half(ref, ref, search, g)
                x, c = DS.model_input(s8, s8, ls, ls, search, amp, prt["cls"], "Dstem")
                r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
                if name.endswith("-Sc"):                 # 5B.1b's S-centred readout on this model's own constant
                    s_c, _, s_sw, s_swm, s_k, s_km, _ = F.encode(dict(S), amp)
                    sw = [float(v) if m else None for v, m in zip(s_sw, s_swm)]
                    mics = [int(v) if m else None for v, m in zip(s_k, s_km)]
                    st = F.answer_settings(amp, S, sc_cont(dict(S), amp, r["a2"], const[(amp, prt["cls"])]["cont"]),
                                           sw, mics)
                else:
                    st = F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"])
                    if name == FTM_BASE:
                        st = hold_outside_space(st, S, amp)
                out[name].setdefault(key, {})[search] = {"select": sel, "settings": LO.sdict(st)}
            if name == "P2a-pc":
                out[f"{name}-constant"][key] = {ANY_HALF: {"select": sel, "settings": LO.sdict(
                    T3.constant_full(amp, S, const[(amp, prt["cls"])]))}}
    for t, a in out.items():
        save(out_dir() / REAL_DIR / "answers" / f"{t}.json", {
            "plan": PLAN, "ledger": f"{LEDGER_ID} {read_phase(name)}",
            "tag": t, "parts": parts, "input": "backed (variant 0)" if name in (*DFIX_BASES, FT_BASE, FTM_BASE) else "clean", "models": {nm: {"sha256": m[1], "input_lufs": m[2]} for nm, m in models.items()},
            "unit_model": names, "answers": a, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"REAL PREDICT 5B.2 DONE: {name} on {len(parts)} units")


def rc_setting(dims, S, labels):
    """5B.2's Rc for one (amp, class): S moved by the mean of `labels`' unit deviations from S on every continuous
    searched dim (clipped to [0, 1]), each switch and mic at the labels' most common value (S's on a tie that includes
    it, else the first in sorted order); S's own value with no labels."""
    from collections import Counter

    from learn import arm_a_levers as L

    if not labels:
        return dict(S)
    cont, cats = {}, dict(S)
    for d in dims:
        k = (d.module, d.key)
        if d.kind in ("cont", "log"):
            cont[k] = min(1.0, max(0.0, L.unit(d, S) + statistics.fmean(L.unit(d, x) - L.unit(d, S) for x in labels)))
        else:
            c = Counter(x.get(k) for x in labels)
            top = max(c.values())
            tied = sorted((v for v in c if c[v] == top), key=str)
            v = S.get(k) if S.get(k) in tied else tied[0]
            if v is None:
                cats.pop(k, None)
            else:
                cats[k] = v
    return L.build(dims, S, cont, cats, cats)


def rc_records(recs, by_unit, folds, prt, amp):
    """The labelled records Rc averages for unit `prt` on `amp`: same amp and class, DI outside the unit's fold
    (exactly the labels its fold's models trained on)."""
    f = folds[prt["di"]]
    return [r for r in recs if r["amp"] == amp and by_unit[r["unit"]]["cls"] == prt["cls"]
            and folds[by_unit[r["unit"]]["di"]] != f]


def real_rc_answers(stage=1):
    """5B.2's Rc on 5B.1's 40 units (zero renders): per unit and amp, `rc_setting` from the labels arm R's fold model
    for that unit trained on (labels of search stages up to `stage` from the other folds' DIs, same amp and class).
    -> real/answers/Rc[s2].json."""
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    e = require("phase_5b2")
    recs, by_unit, folds = real_labels(stage)
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    parts = real_parts(kept, sp, CB.cc_inventory())
    ms = A_menu_S()
    tag = "Rc" + ("s2" if stage == 2 else "")
    out, used = {}, {}
    for prt in parts:
        for amp in AMPS3:
            sel, S = ms[amp][prt["cls"]]
            labels = [LO.tdict(r["label"]) for r in rc_records(recs, by_unit, folds, prt, amp)]
            key = real_key(prt, amp)
            out[key] = {ANY_HALF: {"select": sel, "settings": LO.sdict(rc_setting(K.space(amp, S), S, labels))}}
            used[key] = len(labels)
    save(out_dir() / REAL_DIR / "answers" / f"{tag}.json", {
        "plan": PLAN, "ledger": f"{LEDGER_ID} phase_5b2", "tag": tag, "parts": parts, "labels_used": used,
        "answers": out, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"REAL RC DONE: {tag} on {len(parts)} units; labels per answer {min(used.values())}-{max(used.values())}")


def rigo_records(recs, by_unit, prt, amp):
    """The labelled records RigO averages for unit `prt` on `amp`: the same rig (one reamp track of one DI, so one real
    amp setting) and amp, from windows that do not overlap the unit's section (sections are 10 s and start 5 s apart,
    so a neighbour's search half can hold this unit's held half)."""
    from learn import pretrain_set as PS

    return [r for r in recs if r["amp"] == amp and r["rig"] == prt["rig"]
            and abs(by_unit[r["unit"]]["start_s"] - prt["start_s"]) >= PS.SEC_S]


def real_rigo_answers():
    """5B.2's recording oracle on 5B.1's 40 units (zero renders): per unit and amp, `rc_setting` from the labels of
    the unit's own recording's other windows (`rigo_records`, search stages 1 and 2). It knows the real amp's answers
    on the same track, which no product can, so it bounds what reading a track can add over a centre. A unit with no
    such window gets no answer. -> real/answers/RigO.json."""
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    e = require("phase_5b2_rigo")
    recs, by_unit, folds = real_labels(2)
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    parts = real_parts(kept, sp, CB.cc_inventory())
    ms = A_menu_S()
    out, used = {}, {}
    for prt in parts:
        for amp in AMPS3:
            sel, S = ms[amp][prt["cls"]]
            labels = [LO.tdict(r["label"]) for r in rigo_records(recs, by_unit, prt, amp)]
            if labels:
                key = real_key(prt, amp)
                out[key] = {ANY_HALF: {"select": sel, "settings": LO.sdict(rc_setting(K.space(amp, S), S, labels))}}
                used[key] = len(labels)
    save(out_dir() / REAL_DIR / "answers" / "RigO.json", {
        "plan": PLAN, "ledger": f"{LEDGER_ID} phase_5b2_rigo", "tag": "RigO", "parts": parts, "labels_used": used,
        "answers": out, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"REAL RIGO DONE: {len(out)} of {3 * len(parts)} directions; labels per answer "
          f"{min(used.values())}-{max(used.values())}")


RCM_SEED = 20261046                 # RcM's draws


def real_rcm_answers():
    """RigO's count-matched control (zero renders): on each direction RigO answers, Rc's rule on as many labels as
    RigO used, drawn at random (seeded per direction) from Rcs2's pool for that unit (the other folds' DIs, same amp
    and class), so a RigO gain is not just a noisier centre's luck. -> real/answers/RcM.json."""
    import random

    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    e = require("phase_5b2_rigo")
    recs, by_unit, folds = real_labels(2)
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    parts = real_parts(kept, sp, CB.cc_inventory())
    rigo = json.loads((out_dir() / REAL_DIR / "answers" / "RigO.json").read_text())["labels_used"]
    ms = A_menu_S()
    out, used = {}, {}
    for prt in parts:
        for amp in AMPS3:
            key = real_key(prt, amp)
            if key not in rigo:
                continue
            sel, S = ms[amp][prt["cls"]]
            pool = rc_records(recs, by_unit, folds, prt, amp)
            pick = random.Random(f"{RCM_SEED}|{key}").sample(pool, min(rigo[key], len(pool)))
            labels = [LO.tdict(r["label"]) for r in pick]
            out[key] = {ANY_HALF: {"select": sel, "settings": LO.sdict(rc_setting(K.space(amp, S), S, labels))}}
            used[key] = len(labels)
    save(out_dir() / REAL_DIR / "answers" / "RcM.json", {
        "plan": PLAN, "ledger": f"{LEDGER_ID} phase_5b2_rigo", "tag": "RcM", "parts": parts, "labels_used": used,
        "answers": out, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"REAL RCM DONE: {len(out)} directions; labels per answer {min(used.values())}-{max(used.values())}; "
          f"matched {sum(used[k] == rigo[k] for k in used)} of {len(used)}")


def A_menu_S():
    from learn import arm_a_mega53 as A

    return A.L.menu_S()


def cmd_real_render(args):
    """5B.1's renders for one shard of units: S on each amp first (each in its own primed process; the stored S must
    equal the live menu's), the judge lag estimated once per unit from those three renders pooled
    (`analysis.aligned.estimate_lag`: samples the recording lags the render, the judge's own convention), then every
    answer of `--names` through the section's measure DI in its own primed process, rendered over the whole section
    and trimmed as the by-sound read trims, judged against the unit's reamped track on both halves.
    -> real/judge/<tag>/<unit>|<amp>.json."""
    import numpy as np

    from analysis.aligned import estimate_lag
    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    e = require("phase_5b1")
    tags = ["S"] + [t for t in args.names.split(",") if t and t != "S"]
    bad = ftg_unhashed(tags, e)
    if bad:
        raise SystemExit(f"renders refuse until the answers' hashes are in the ledger: {bad}")
    ans = {t: json.loads((out_dir() / REAL_DIR / "answers" / f"{t}.json").read_text()) for t in tags}
    parts = ans["S"]["parts"]
    k, n = args.shard
    mine = [p_ for j, p_ in enumerate(parts) if j % n == k]
    lag_dir = out_dir() / REAL_DIR / "lags"
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    rr = CB.new_renderer()
    try:
        menu = rr.menu()
    finally:
        rr.close()
    for amp, by_cls in A.L.menu_S().items():          # the stored S must equal the live one (cc_readout's check)
        for cls, (_, S) in by_cls.items():
            if K.key(dict(menu[amp][K.START[cls][amp]][1])) != K.key(S):
                raise SystemExit(f"{amp} {cls}: the live S differs from the stored copy")
    renders, skipped = 0, 0

    def render(di32, a):
        st = LO.tdict(a["settings"])
        y = AM.fresh_render(CB.new_renderer, di32, a["select"], st, st)
        return np.asarray(y, np.float64)[trim[0]:trim[1]]

    def fname(key):
        return key.replace("/", "__")

    for prt in mine:
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        lp = lag_dir / f"{fname(prt['unit'])}.json"
        s_y = {}
        if not lp.exists():
            for amp in AMPS3:
                s_y[amp] = render(di32, ans["S"]["answers"][real_key(prt, amp)][ANY_HALF])
                renders += 2
            try:
                save(lp, {"unit": prt["unit"], "lag": int(estimate_lag(ref, list(s_y.values()))), "status": "ok"})
            except ValueError as err:
                save(lp, {"unit": prt["unit"], "lag": None, "status": f"no lag: {err}"})
        lag = json.loads(lp.read_text())["lag"]
        if lag is None:
            print(f"{prt['unit'][-60:]}: no lag; not read", flush=True)
            continue
        for t in tags:
            asha = answers_sha(ans[t]["answers"])
            for amp in AMPS3:
                key = real_key(prt, amp)
                if key not in ans[t]["answers"]:          # RigO, RcM: no window of its own recording outside the unit
                    skipped += 1
                    continue
                gp = out_dir() / REAL_DIR / "judge" / t / f"{fname(key)}.json"
                if gp.exists():
                    if json.loads(gp.read_text()).get("answers_sha256") != asha:
                        raise SystemExit(f"{gp}: rendered from other answers")
                    continue
                rec = {"unit": prt["unit"], "amp": amp, "tag": t, "lag": lag, "answers_sha256": asha, "judge": {},
                       "render_sha256": {}}
                for search, a in sorted(ans[t]["answers"][key].items()):
                    if t == "S" and amp in s_y:
                        y = s_y[amp]
                    else:
                        y = render(di32, a)
                        renders += 2
                    rec["judge"][search] = K.judge(ref, y, di, lag)
                    rec["render_sha256"][search] = AM.audio_sha(y)
                save(gp, rec)
        print(f"{prt['unit'][-60:]}: lag {lag}; renders so far {renders}", flush=True)
    print(f"REAL-RENDER DONE {k}/{n}: {renders} renders"
          + (f"; {skipped} directions with no answer" if skipped else ""))


SEARCH_DIR = "search"               # 5B.2: real/search/<unit>|<amp>.json


def search_halves(parts):
    """5B.2: each unit's searched half, A and B alternating by unit order within each DI."""
    out, seen = {}, {}
    for p_ in parts:
        j = seen.get(p_["di"], 0)
        seen[p_["di"]] = j + 1
        out[p_["unit"]] = "AB"[j % 2]
    return out


def stage_units(kept, sp, inv, stage):
    """5B.2's units: stage 1 is 5B.1's 40 read units, stage 2 every other reamped unit (65)."""
    read = real_parts(kept, sp, inv)
    if stage == 1:
        return read
    ids = {p_["unit"] for p_ in read}
    return [p_ for p_ in real_parts(kept, sp, inv, n=10 ** 6) if p_["unit"] not in ids]


def cmd_real_search(args):
    """5B.2's searches (stage `--stage`, one shard of units): per unit and forced amp, arm A's main stage (`K.space`,
    52 evaluations, seed 20261013) from the class's S with the section's true (measure) DI, scored by the judge's
    distance to the reamped track on the unit's search half at the unit's lag. Each direction in its own process: one
    discarded priming render of S, then the search, so its first evaluation (S) sits where 5B.1's fresh S render sat
    and must be bit-identical to it (stage 1; stage 2's S renders and lag are made here first, as 5B.1 made them).
    Stage 1 (read): the best setting and the setting shrunk 0.5 toward S are then each rendered fresh (5B.1's way) and
    judged on both halves; the held half is the read. Stage 2 (labels only): the best's in-process render. The
    best's in-process judge (both halves) is saved beside; the search sees the search half alone.
    -> real/search/<unit>|<amp>.json."""
    import numpy as np

    from analysis.aligned import estimate_lag
    from learn import arm_a_levers as L
    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    e = require("phase_5b2")
    if args.stage not in (1, 2):
        raise SystemExit("--stage 1 or 2")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    parts = stage_units(kept, sp, CB.cc_inventory(), args.stage)
    halves = search_halves(parts)
    k, n = args.shard
    mine = [p_ for j, p_ in enumerate(parts) if j % n == k]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    ms = L.menu_S()
    LO._wait_cap()
    rr = CB.new_renderer()
    try:
        menu = rr.menu()
    finally:
        rr.close()
    for amp, by_cls in ms.items():
        for cls, (_, S) in by_cls.items():
            if K.key(dict(menu[amp][K.START[cls][amp]][1])) != K.key(S):
                raise SystemExit(f"{amp} {cls}: the live S differs from the stored copy")
    sdir, ldir = out_dir() / REAL_DIR / SEARCH_DIR, out_dir() / REAL_DIR / "lags"
    s_judge = out_dir() / REAL_DIR / "judge" / "S"
    renders = 0

    def sorted_x(x):                                   # edits in 5B.1's order (`sdict` sorts the keys)
        return LO.tdict(LO.sdict(x))

    def fresh(di32, sel, x):
        xs = sorted_x(x)
        y = AM.fresh_render(CB.new_renderer, di32, sel, xs, xs)
        return np.asarray(y, np.float64)[trim[0]:trim[1]]

    def fname(key):
        return key.replace("/", "__")

    for prt in mine:
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        search = halves[prt["unit"]]
        held = "B" if search == "A" else "A"
        lp = ldir / f"{fname(prt['unit'])}.json"
        s_ref = {}                                     # amp -> (S's fresh judge, its render sha)
        if args.stage == 1:
            if not lp.exists():
                raise SystemExit(f"{lp.name}: stage 1 reads 5B.1's stored lag")
            for amp in AMPS3:
                g = json.loads((s_judge / f"{fname(real_key(prt, amp))}.json").read_text())
                s_ref[amp] = (g["judge"][ANY_HALF], g["render_sha256"][ANY_HALF])
        else:                                          # S's fresh renders give the lag, S's judge and its sha
            rec = json.loads(lp.read_text()) if lp.exists() else None
            if rec is not None and rec.get("phase") != "phase_5b2":
                raise SystemExit(f"{lp.name}: a stage 2 unit has a lag from another phase")
            if rec is None or "s" not in rec:
                ys = {}
                for amp in AMPS3:
                    sel, S = ms[amp][prt["cls"]]
                    ys[amp] = fresh(di32, sel, S)
                    renders += 2
                try:
                    lag, status = int(estimate_lag(ref, list(ys.values()))), "ok"
                except ValueError as err:
                    lag, status = None, f"no lag: {err}"
                save(lp, {"unit": prt["unit"], "lag": lag, "status": status, "phase": "phase_5b2",
                          "s": {amp: {"judge": None if lag is None else K.judge(ref, ys[amp], di, lag),
                                      "render_sha256": AM.audio_sha(ys[amp])} for amp in AMPS3}})
            rec = json.loads(lp.read_text())
            s_ref = {amp: (v["judge"], v["render_sha256"]) for amp, v in rec["s"].items()}
        lag = json.loads(lp.read_text())["lag"]
        if lag is None:
            print(f"{prt['unit'][-60:]}: no lag; not searched", flush=True)
            continue
        for amp in AMPS3:
            key = real_key(prt, amp)
            path = sdir / f"{fname(key)}.json"
            if path.exists():
                continue
            sel, S = ms[amp][prt["cls"]]
            dims = K.space(amp, S)
            s_j, s_sha = s_ref[amp]
            curve, first, seen = [], {}, {}
            rr = CB.new_renderer()
            try:
                rr.render(di32, sel, sorted_x(S))      # the discarded priming render, as `fresh_render`'s
                renders += 1

                def f(x):
                    y = np.asarray(rr.render(di32, sel, sorted_x(x)), np.float64)[trim[0]:trim[1]]
                    j = K.judge(ref, y, di, lag)
                    if not curve:
                        first.update(sha=AM.audio_sha(y), value=j[search])
                        if first["sha"] != s_sha:
                            raise SystemExit(f"{key}: S's first evaluation is not bit-identical to its fresh render")
                    # the held half is kept for the record only; the search sees the search half alone
                    seen[K.key(x)] = {"judge": j, "peak_dbfs": A.peak_dbfs(y, trim_s=0.0), "render_sha256":
                                      AM.audio_sha(y)}
                    curve.append(j[search])
                    return j[search]

                best_x, best_v, evals = L.main_stage(dims, S, f, seed=L.SEED)
                renders += evals
            finally:
                rr.close()
            inproc = seen[K.key(best_x)]
            out = {"best_in_process": inproc}
            if args.stage == 1:                        # stage 1 is read: best and shrunk rendered fresh, as 5B.1
                for name, x in (("best", best_x), ("shrunk", L.shrink(dims, S, best_x, A.SHRINK))):
                    y = fresh(di32, sel, x)
                    renders += 2
                    out[name] = {"judge": K.judge(ref, y, di, lag), "peak_dbfs": A.peak_dbfs(y, trim_s=0.0),
                                 "render_sha256": AM.audio_sha(y), "settings": LO.sdict(x)}
            else:                                      # stage 2 gives labels only: the in-process render of the best
                out["best"] = dict(inproc, settings=LO.sdict(best_x))
            for name in ("best", "shrunk"):
                if name in out:
                    out[name]["fallback"] = A.fallback_reason(out[name]["peak_dbfs"], out[name]["judge"][search])
            save(path, {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_5b2", "stage": args.stage, "unit": prt["unit"],
                        "rig": prt["rig"], "di": prt["di"], "cls": prt["cls"], "amp": amp, "select": sel,
                        "search": search, "held": held, "lag": lag, "s_judge": s_j, "s_render_sha256": s_sha,
                        "s_first": first, "curve": curve, "evaluations": evals, "best_search_value": best_v,
                        **out, "label": None if out["best"]["fallback"] else out["best"]["settings"],
                        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            print(f"{key[-70:]}: {search}->{held} S {s_j[held]:.3f} best {out['best']['judge'][held]:.3f}"
                  + (f" shrunk {out['shrunk']['judge'][held]:.3f}" if "shrunk" in out else "")
                  + f"; renders so far {renders}", flush=True)
    print(f"REAL-SEARCH DONE stage {args.stage} {k}/{n}: {renders} renders")


# --- 5C: GOAT's capture renders (phase_5c) ----------------------------------------------------------------------------

GOAT_ZIP = pathlib.Path("~/ndsp-presets/references/datasets-goat/_zips/GOAT.zip").expanduser()
GOAT_DIR = "goat"                   # under out_dir(): sections/, units.json, search/, lags/
GOAT_SEED = 20261047                # the render and window draws


def goat_member(item, name):
    """A metadata path ('GOAT/item_0/item_0.wav') as the zip stores it ('GOAT/data/item_0/item_0.wav')."""
    return f"GOAT/data/{item}/{name.rsplit('/', 1)[-1]}"


def goat_window(rows, item, track=None, min_start_s=1.0):
    """5C's window for one GOAT item: among the DI's 10-s grid sections that pass the pool's activity rule
    (`clean_di.passes`) and its screens (`clean_di.section_flags`: hum, hiss, clipping, drop-outs) with no clip run or
    hard cut either, from `min_start_s` on, one drawn at random (seed GOAT_SEED with the item). -> start in seconds,
    or None."""
    import random

    from learn import clean_di as CD

    ok = [r["start_s"] for r in rows if r["passes_activity"] and r["start_s"] >= min_start_s
          and not (r.get("clip_runs") or r.get("dropouts") or r.get("hard_cuts"))
          and not CD.section_flags(r, track or {})[0]]
    return random.Random(f"{GOAT_SEED}|{item}").choice(sorted(ok)) if ok else None


def goat_renders(item, ok, k=None):
    """5C's renders for one GOAT item: of its clean/crunch renders `ok`, up to k (GOAT_PER_ITEM) in a seeded order
    (seed GOAT_SEED with the item). -> sorted render numbers."""
    import random

    k = GOAT_PER_ITEM if k is None else k
    return sorted(random.Random(f"{GOAT_SEED}|renders|{item}").sample(sorted(ok), min(k, len(ok))))


def goat_assign(items, folds=None):
    """5C's folds (by item: an item's renders share a fold) and forced amps (by unit, a third each), both from a
    seeded order. items: {item: [unit, ...]}. -> ({item: fold}, {unit: amp})."""
    import random

    folds = REAL_FOLDS if folds is None else folds
    order = sorted(items)
    random.Random(f"{GOAT_SEED}|folds").shuffle(order)
    fold = {it: j % folds for j, it in enumerate(order)}
    units = sorted(u for us in items.values() for u in us)
    random.Random(f"{GOAT_SEED}|amps").shuffle(units)
    return fold, {u: AMPS3[j % len(AMPS3)] for j, u in enumerate(units)}


GOAT_PER_ITEM = 2                   # the pilot's renders per item (clean/crunch only)


def cmd_goat_sections(args):
    """5C's data (zero renders): per GOAT item, the pool's DI measures (`clean_di.measure_di`, the item's own mains
    vote) and one window (`goat_window`); each of its 5 renders checked for length, rate and clipping in the window,
    classed by the pool's classifier against the DI on the window (`classify` on `gainmeasure`, as
    `trusted_data_t3._amp_track_class`; high gain is out) and its whole-item lag to the DI measured
    (`estimate_lag`, the render against the DI); up to GOAT_PER_ITEM clean/crunch renders kept (`goat_renders`);
    folds by item and forced amps by unit (`goat_assign`). The window cut from the DI and each kept render, as
    section files (TRIM_S lead, the pipeline's rate), read straight from the zip. -> goat/sections/*.wav,
    goat/units.json."""
    import io
    import sys
    import zipfile

    import numpy as np
    import soundfile as sf

    from analysis.aligned import estimate_lag
    from learn import clean_di as CD
    from learn import pretrain_set as PS

    require("phase_5c")
    sys.path.insert(0, str(PS.HOME / "references/datasets-set3/_tools"))
    import classify as C
    import gainmeasure as GM

    gd = out_dir() / GOAT_DIR
    sec = gd / "sections"
    sec.mkdir(parents=True, exist_ok=True)
    n = int(round((PS.SEC_S + PS.TRIM_S) * PS.SR))
    trim = int(PS.TRIM_S * PS.SR)
    units, out, by_item = [], {}, {}
    with zipfile.ZipFile(GOAT_ZIP) as z:
        meta = goat_items_from(z)
        for m in meta:
            item = m["item"]
            x, sr = sf.read(io.BytesIO(z.read(goat_member(item, m["di_audio_path"]))), dtype="float64", always_2d=True)
            x = x.mean(1)
            f, fs = CD.floor_spectrum(CD.resample(x, sr, CD.SR))
            votes = {k: [v] for k, v in ({mm: CD.line_count(f, fs, mm) for mm in CD.MAINS} if fs is not None
                                         else {}).items()}
            track, rows = CD.measure_di(x, sr, CD.session_mains(votes))
            start = goat_window(rows, item, track)
            rec = {"item": item, "player": m["player"], "guitar": m["guitar_brand"], "tuning": m["tuning_class"],
                   "seconds": track["seconds"], "start_s": start, "di_near_fs": track["near_fs"],
                   "hum_rel_db": track["hum_rel_db"], "renders": {}}
            out[item] = rec
            if start is None or track["near_fs"]:
                rec["out"] = "no window" if start is None else "DI near full scale"
                print(f"{item}: {rec['out']}", flush=True)
                continue
            lo, hi = max(0, int(round((start - PS.TRIM_S) * sr))), int(round((start + PS.SEC_S) * sr))
            dsec = CD.resample(x[lo:hi], sr, PS.SR)[:n]
            if len(dsec) < n:
                rec["out"] = "window runs past the end"
                continue
            d48 = CD.resample(x, sr, PS.SR)
            secs, ok = {}, []
            for j in range(1, 6):
                a, sra = sf.read(io.BytesIO(z.read(goat_member(item, m[f"amp_audio_path_{j}"]))), dtype="float64",
                                 always_2d=True)
                a = a.mean(1)
                r = rec["renders"][j] = {}
                if sra != sr or len(a) != len(x):
                    r["out"] = "not the DI's length and rate"
                    continue
                if len(CD.clip_runs(a[lo:hi], peak=float(np.max(np.abs(a))))):  # flat tops at the render's own peak
                    r["out"] = "clips in the window"
                    continue
                asec = CD.resample(a[lo:hi], sr, PS.SR)[:n]
                gm = GM.measures(np.asarray(asec[trim:], np.float64), np.asarray(dsec[trim:], np.float64), PS.SR)
                r["class"] = C.classify(gm)[0] if gm else None
                r["gain_measures"] = gm
                try:
                    r["item_lag"] = int(estimate_lag(CD.resample(a, sr, PS.SR), [d48]))
                except ValueError as err:
                    r["item_lag"], r["out"] = None, f"no item lag: {err}"
                    continue
                if r["class"] in ("clean", "crunch"):
                    ok.append(j)
                    secs[j] = asec
                else:
                    r["out"] = f"class {r['class']}"
            keep = goat_renders(item, ok)
            if not keep:
                rec["out"] = "no clean/crunch render"
                print(f"{item}: {rec['out']}", flush=True)
                continue
            dp = sec / f"{item}.di.wav"
            sf.write(dp, dsec.astype(np.float32), PS.SR, subtype="FLOAT")
            for j in keep:
                ap = sec / f"{item}.amp{j}.wav"
                sf.write(ap, secs[j].astype(np.float32), PS.SR, subtype="FLOAT")
                u = f"goat/{item}@{start}#amp_{j}"
                units.append({"unit": u, "section": f"goat/{item}@{start}", "track": ap.name,
                              "rig": f"goat/{item}#amp_{j}", "set": "goat", "di": f"goat/{item}",
                              "band": f"GOAT {m['player']}", "cls": rec["renders"][j]["class"], "sd": str(sec),
                              "start_s": PS.TRIM_S, "di_path": str(dp), "item": item, "render": j, "window_s": start,
                              "item_lag": rec["renders"][j]["item_lag"]})
                by_item.setdefault(item, []).append(u)
            print(f"{item}: window {start}; kept {keep} of clean/crunch {ok}", flush=True)
    fold, amp = goat_assign(by_item)
    for u in units:
        u["fold"], u["amp"] = fold[u["item"]], amp[u["unit"]]
    save(gd / "units.json", {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_5c", "zip": str(GOAT_ZIP), "units": units,
                             "items": out, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    cnt = {}
    for u in units:
        cnt[(u["amp"], u["cls"])] = cnt.get((u["amp"], u["cls"]), 0) + 1
    print(f"GOAT-SECTIONS DONE: {len(units)} units from {len(by_item)} of {len(meta)} items; by amp and class {cnt}")


GOAT_ROW0 = 4_000_000               # 5C's GOAT training rows: ids from here (apart from BKS's REAL_ROW0 rows)
GOAT_PER_EPOCH = 300                # GOAT rows per epoch in every fold (its labelled units cycled)
GOAT_LAG_TOL = 72                    # the one-window lag rule's tolerance (samples; 14, 5B.2's LAG_TOL, until the lag diagnostic)


def goat_units():
    """5C's units (`goat-sections`): [{unit, item, render, rig, di, cls, amp, fold, item_lag, sd, track, ...}]."""
    return json.loads((out_dir() / GOAT_DIR / "units.json").read_text())["units"]


def goat_halves(units):
    """5C: each unit's searched half, A and B alternating over the units in sorted order (most items give one or two
    units, so 5B.2's per-DI alternation would search half A almost everywhere)."""
    return {u: "AB"[j % 2] for j, u in enumerate(sorted(p_["unit"] for p_ in units))}


def goat_lag_refused(lags, item_lags, tol=None):
    """5C's one-window lag rule: units whose judge lag minus their whole-item DI-to-render lag sits more than `tol`
    samples from the median of that difference over all units. lags, item_lags: {unit: samples or None}.
    -> set of units (a unit with no lag is refused too)."""
    import statistics

    tol = GOAT_LAG_TOL if tol is None else tol
    d = {u: lags[u] - item_lags[u] for u in lags if lags[u] is not None and item_lags.get(u) is not None}
    if not d:
        return set(lags)
    m = statistics.median(d.values())
    return {u for u in lags if u not in d or abs(d[u] - m) > tol}


def goat_heard(units, verdicts):
    """5C's ear gate: every kept unit must have the user's verdict before any GOAT render; only "amp" passes
    ("unsure" and every other verdict are out). verdicts: {unit: {"verdict": ...}} (goat/ear.json).
    -> (units passed, units without a verdict)."""
    missing = [u for u in units if u not in verdicts]
    return {u for u in units if (verdicts.get(u) or {}).get("verdict") == "amp"}, missing


GOAT_MIN_PER_CELL = 30             # trusted units per amp and class, or the pilot stops at the data stage


def goat_short_cells(parts, minimum=None):
    """5C's minimum: amp-and-class cells with fewer than `minimum` units among `parts` (the trusted units: ear-passed,
    less the heavy check, less the lag rule). parts: [{amp, cls}]. -> {(amp, cls): count} of the short cells, every
    amp and class of AMPS3 x (clean, crunch) counted."""
    minimum = GOAT_MIN_PER_CELL if minimum is None else minimum
    n = {(a, c): 0 for a in AMPS3 for c in ("clean", "crunch")}
    for p_ in parts:
        n[(p_["amp"], p_["cls"])] += 1
    return {k: v for k, v in n.items() if v < minimum}


def goat_heavy_out(candidates, verdicts):
    """5C's heavy check (amendment of 2026-11-01): the firmly driven units the ear passed are heard again against the
    pool's clean/crunch scope; only "keep" stays in. candidates: the units on the heavy page (goat/heavy-key.json);
    verdicts: goat/heavy.json's. -> (units out, candidates without a verdict)."""
    missing = [u for u in candidates if u not in verdicts]
    return {u for u in candidates if (verdicts.get(u) or {}).get("verdict") != "keep"}, missing


def goat_ear_passed(units):
    """`goat_heard` on goat/ear.json, less `goat_heavy_out` on goat/heavy.json; refuses while any kept unit is
    unheard on either page. -> set of units passed."""
    gd = out_dir() / GOAT_DIR
    p = gd / "ear.json"
    ok, missing = goat_heard(units, json.loads(p.read_text())["verdicts"] if p.exists() else {})
    if missing:
        raise SystemExit(f"{len(missing)} GOAT units are not yet heard: every kept unit is heard before any render")
    k = gd / "heavy-key.json"
    if not k.exists():
        raise SystemExit("the heavy check is not built yet (`learn.goat_ear_page heavy`)")
    from learn import goat_ear_page as G

    key = json.loads(k.read_text())
    cand = [it["unit"] for it in key["items"]]
    if sorted(cand) != G.heavy_candidates():
        raise SystemExit("the heavy page's units are not the current firmly driven passed units: rebuild it")
    h = gd / "heavy.json"
    hv = json.loads(h.read_text()) if h.exists() else {"build": key["build"], "verdicts": {}}
    if hv.get("build") != key["build"]:
        raise SystemExit("goat/heavy.json is not from the heavy page's build")
    out, missing = goat_heavy_out(cand, hv["verdicts"])
    if missing:
        raise SystemExit(f"{len(missing)} heavy-check units are not yet heard")
    return ok - out


def goat_labels():
    """5C's labelled GOAT records (goat/search) of the units the ear passed, after the one-window lag rule, with
    their units. -> (records, {unit: unit record}, refused units)."""
    units = {p_["unit"]: p_ for p_ in goat_units()}
    heard = goat_ear_passed(units)
    recs = [json.loads(p_.read_text()) for p_ in sorted((out_dir() / GOAT_DIR / SEARCH_DIR).glob("*.json"))]
    recs = [r for r in recs if r["unit"] in heard]
    _, off = goat_lags_refused(units, heard)
    return [r for r in recs if r["label"] is not None and r["unit"] not in off], units, off


def goat_fold_records(recs, units, fold, n=None, shuffle=False):
    """5C's GOAT training records for model `fold`: the labelled units of the other GOAT folds (with `shuffle`,
    RGshuf's: their labels permuted among those units only, `goat_shuffled`), cycled to GOAT_PER_EPOCH (a fold's
    models never see their own GOAT items or their labels)."""
    tr = [r for r in recs if units[r["unit"]]["fold"] != fold]
    if shuffle:
        tr = goat_shuffled(tr, units, seed=f"{GOAT_SEED}|{fold}")
    return cycled(tr, GOAT_PER_EPOCH if n is None else n)


def goat_shuffled(recs, units, seed=GOAT_SEED):
    """RGshuf's records: the GOAT labels permuted across units within amp and class (seeded), every other field
    kept. -> new records."""
    import random

    out = [dict(r) for r in recs]
    groups = {}
    for j, r in enumerate(out):
        groups.setdefault((r["amp"], units[r["unit"]]["cls"]), []).append(j)
    rng = random.Random(f"{seed}|shuffle")
    for key in sorted(groups):
        idx = groups[key]
        perm = idx[:]
        rng.shuffle(perm)
        labels = [recs[j]["label"] for j in perm]
        for j, lab in zip(idx, labels):
            out[j]["label"] = lab
    return out


def goat_run_name(base, real_fold, stage, shuffle):
    """5C's run names: RG `P2a-goat{k}`, RGshuf `P2a-goatshuf{k}`, only on P2a-reals2's own recipe (the base name it
    would otherwise take), so no 5B.2 run is ever reused for one."""
    if real_fold is None or stage != 2 or base != f"P2a-real{real_fold}s2":
        raise SystemExit("--goat is 5C's RG: P2a-reals2's recipe (--rung a --real-fold k --stage 2) plus GOAT rows")
    return f"P2a-goat{'shuf' if shuffle else ''}{real_fold}"


def goat_input_path(unit):
    return out_dir() / GOAT_DIR / "inputs" / f"{unit.replace('/', '__')}.npz"


def goat_rows(fold, target, shuffle=False):
    """5C's GOAT training rows for model `fold` (`goat_fold_records`; RGshuf's labels with `shuffle`): input the
    render's section at `target` LUFS (5B.1's path, both halves; cached), label the search's best setting
    (`F.label_of`); ids from GOAT_ROW0. -> (rows, {id: input path})."""
    import numpy as np

    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO

    recs, units, _ = goat_labels()
    rows, paths = [], {}
    for j, rec in enumerate(goat_fold_records(recs, units, fold, shuffle=shuffle)):
        prt = units[rec["unit"]]
        ip = goat_input_path(prt["unit"])
        if not ip.exists():
            ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            g = DE.inference_gain_db(ref, target)
            (sa, _, la, _), (sb, _, lb, _) = (DS.step4_half(ref, ref, h, g) for h in ("A", "B"))
            ip.parent.mkdir(parents=True, exist_ok=True)
            np.savez(ip, sA=sa, sB=sb, lufs=np.array([la, lb], np.float32), target=np.float64(target))
        if float(np.load(ip)["target"]) != float(target):
            raise SystemExit(f"{ip.name}: built for another input loudness")
        i = GOAT_ROW0 + j
        rows.append({"i": i, "section": prt["section"], "band": prt["band"], "amp": rec["amp"], "cls": prt["cls"],
                     "base": prt["cls"], "label": F.label_of(LO.tdict(rec["label"]), rec["amp"]), "real": rec["unit"]})
        paths[i] = ip
    return rows, paths


def cmd_goat_search(args):
    """5C's label searches (one shard of GOAT units): `search_units` on the units the ear passed. With `--lags-only`
    (run first, over every shard) the S renders and lags alone; the search pass then refuses, before searching, the
    units the one-window lag rule (`goat_lag_refused`) refuses. -> goat/search/<unit>|<amp>.json, goat/lags/<unit>.json."""
    require("phase_5c")
    parts = sorted(goat_units(), key=lambda p_: p_["unit"])
    halves = goat_halves(parts)
    heard = goat_ear_passed([p_["unit"] for p_ in parts])     # before any render; only "amp" units go on
    parts = [p_ for p_ in parts if p_["unit"] in heard]
    k, n = args.shard
    mine = [p_ for j, p_ in enumerate(parts) if j % n == k]
    refused = set()
    if not args.lags_only:                             # the lag rule over every unit, before any search
        ldir = out_dir() / GOAT_DIR / "lags"
        lp_ = {p_["unit"]: ldir / f"{p_['unit'].replace('/', '__')}.json" for p_ in parts}
        missing = [u for u, q in lp_.items() if not q.exists()]
        if missing:
            raise SystemExit(f"{len(missing)} units have no lag: run goat-search --lags-only first")
        _, refused = goat_lags_refused({p_["unit"]: p_ for p_ in parts}, [p_["unit"] for p_ in parts])
        short = goat_short_cells([p_ for p_ in parts if p_["unit"] not in refused])
        if short:
            raise SystemExit(f"under {GOAT_MIN_PER_CELL} trusted units in {short}: the pilot stops at the data stage")
    renders = search_units(mine, out_dir() / GOAT_DIR, "phase_5c", halves, refused, args.lags_only)
    print(f"GOAT-SEARCH{' LAGS' if args.lags_only else ''} DONE {k}/{n}: {renders} renders")


def search_units(mine, root, phase, halves, refused, lags_only, quiet=False, searcher=None):
    """5C's labels, for GOAT's units and L1a's captures alike (`root` holds search/ and lags/), as 5B.2's stage 2
    (`cmd_real_search`), per unit on its forced amp only: three fresh S renders (one per amp, the class's S) give the
    judge lag, S's judge and its sha (saved, so the search resumes); then one discarded priming render and arm A's main
    stage (`K.space`, 52 evaluations, seed 20261013) from S with the unit's DI, scored by the judge's distance to the
    render on the unit's search half (`halves`); S's first evaluation must be bit-identical to its fresh render; the
    label is the best's in-process render. With `lags_only`, the S renders and lags alone. Units in `refused` are
    recorded, not searched. With `quiet`, the log names units and render counts only, no judge figure. `searcher(dims, S, f,
    amp)` -> (best x, best value, evaluations) replaces the main stage (N2's v2). -> renders made."""
    import numpy as np

    from analysis.aligned import estimate_lag
    from learn import arm_a_levers as L
    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    ms = L.menu_S()
    LO._wait_cap()
    rr = CB.new_renderer()
    try:
        menu = rr.menu()
    finally:
        rr.close()
    for amp, by_cls in ms.items():
        for cls, (_, S) in by_cls.items():
            if K.key(dict(menu[amp][K.START[cls][amp]][1])) != K.key(S):
                raise SystemExit(f"{amp} {cls}: the live S differs from the stored copy")
    sdir, ldir = root / SEARCH_DIR, root / "lags"
    renders = 0

    def sorted_x(x):                                   # edits in 5B.1's order (`sdict` sorts the keys)
        return LO.tdict(LO.sdict(x))

    def fresh(di32, sel, x):
        xs = sorted_x(x)
        y = AM.fresh_render(CB.new_renderer, di32, sel, xs, xs)
        return np.asarray(y, np.float64)[trim[0]:trim[1]]

    def fname(key):
        return key.replace("/", "__")

    for prt in mine:
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        amp = prt["amp"]
        key = real_key(prt, amp)
        path = sdir / f"{fname(key)}.json"
        if path.exists() or (lags_only and (ldir / f"{fname(prt['unit'])}.json").exists()):
            continue
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        search = halves[prt["unit"]]
        held = "B" if search == "A" else "A"
        lp = ldir / f"{fname(prt['unit'])}.json"
        rec = json.loads(lp.read_text()) if lp.exists() else None
        if rec is not None and rec.get("phase") != phase:
            raise SystemExit(f"{lp.name}: a unit has a lag from another phase")
        if rec is None:
            ys = {}
            for a in AMPS3:
                sel_a, S_a = ms[a][prt["cls"]]
                ys[a] = fresh(di32, sel_a, S_a)
                renders += 2
            try:
                lag, status = int(estimate_lag(ref, list(ys.values()))), "ok"
            except ValueError as err:
                lag, status = None, f"no lag: {err}"
            save(lp, {"unit": prt["unit"], "lag": lag, "status": status, "phase": phase,
                      "item_lag": prt["item_lag"],
                      "s": {a: {"judge": None if lag is None else K.judge(ref, ys[a], di, lag),
                                "render_sha256": AM.audio_sha(ys[a])} for a in AMPS3}})
            rec = json.loads(lp.read_text())
        lag = rec["lag"]
        if lags_only:
            print(f"{prt['unit'][-60:]}: lag {lag} (item {prt['item_lag']}); renders so far {renders}", flush=True)
            continue
        if lag is None or prt["unit"] in refused:
            save(path, {"plan": PLAN, "ledger": f"{LEDGER_ID} {phase}", "unit": prt["unit"], "rig": prt["rig"],
                        "di": prt["di"], "item": prt["item"], "fold": prt["fold"], "cls": prt["cls"], "amp": amp,
                        "lag": lag, "item_lag": prt["item_lag"], "label": None,
                        "why": rec["status"] if lag is None else "the one-window lag rule",
                        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            print(f"{prt['unit'][-60:]}: refused ({'no lag' if lag is None else 'lag rule'}); not searched",
                  flush=True)
            continue
        s_j, s_sha = rec["s"][amp]["judge"], rec["s"][amp]["render_sha256"]
        sel, S = ms[amp][prt["cls"]]
        dims = K.space(amp, S)
        curve, first, seen = [], {}, {}
        rr = CB.new_renderer()
        try:
            rr.render(di32, sel, sorted_x(S))          # the discarded priming render, as `fresh_render`'s
            renders += 1

            def f(x):
                y = np.asarray(rr.render(di32, sel, sorted_x(x)), np.float64)[trim[0]:trim[1]]
                j = K.judge(ref, y, di, lag)
                if not curve:
                    first.update(sha=AM.audio_sha(y), value=j[search])
                    if first["sha"] != s_sha:
                        raise SystemExit(f"{key}: S's first evaluation is not bit-identical to its fresh render")
                seen[K.key(x)] = {"judge": j, "peak_dbfs": A.peak_dbfs(y, trim_s=0.0), "render_sha256":
                                  AM.audio_sha(y)}
                curve.append(j[search])
                return j[search]

            best_x, best_v, evals = (searcher(dims, S, f, amp) if searcher else L.main_stage(dims, S, f, seed=L.SEED))
            renders += evals
        finally:
            rr.close()
        best = dict(seen[K.key(best_x)], settings=LO.sdict(best_x))
        best["fallback"] = A.fallback_reason(best["peak_dbfs"], best["judge"][search])
        save(path, {"plan": PLAN, "ledger": f"{LEDGER_ID} {phase}", "unit": prt["unit"], "rig": prt["rig"],
                    "di": prt["di"], "item": prt["item"], "fold": prt["fold"], "cls": prt["cls"], "amp": amp,
                    "select": sel, "search": search, "held": held, "lag": lag, "item_lag": prt["item_lag"],
                    "s_judge": s_j, "s_render_sha256": s_sha, "s_first": first, "curve": curve, "evaluations": evals,
                    "best_search_value": best_v, "best": best,
                    "label": None if best["fallback"] else best["settings"],
                    "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{key[-70:]}: renders so far {renders}" if quiet else f"{key[-70:]}: {search}->{held} S {s_j[held]:.3f} best "
              f"{best['judge'][held]:.3f}; renders so far {renders}", flush=True)
    return renders


GOAT_STOP_BOUND_SHARE = 0.5         # the staged stop: more than this share of labels with inputGain at a bound


def cmd_goat_stage_check(args):
    require("phase_5c")
    stage_check(out_dir() / GOAT_DIR, "phase_5c")


def stage_read(root, phase, keep=None):
    """5C's staged stop, for GOAT and L1a alike (zero renders): the in-process best's held-half log ratio to S, clustered
    by each record's `item` (L1a's are creators; `clustered`), and the share of labels whose inputGain sits at a bound of `K.space`, over the search records
    (of the units in `keep`, if given). Stop when the held-half interval's upper end is at or above 0 (the searches do
    not decidedly beat S where they did not search) or the bound share exceeds GOAT_STOP_BOUND_SHARE (the captures' input
    calibration would set the labels). -> the record."""
    from learn import arm_a_levers as L
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    ms = L.menu_S()
    recs = [json.loads(p_.read_text()) for p_ in sorted((root / SEARCH_DIR).glob("*.json"))]
    if keep is not None:
        recs = [r for r in recs if r["unit"] in keep]
    lab = [r for r in recs if r["label"] is not None]
    rows = [(r["item"], r["unit"], math.log(r["best"]["judge"][r["held"]] / r["s_judge"][r["held"]])) for r in lab
            if r["s_judge"][r["held"]] and r["best"]["judge"][r["held"]] > 0]
    at = []
    for r in lab:
        S = ms[r["amp"]][r["cls"]][1]
        d = next(d for d in K.space(r["amp"], S) if d.key == "inputGain")
        u = L.unit(d, LO.tdict(r["label"]))
        at.append(u <= 1e-6 or u >= 1 - 1e-6)
    c = clustered(rows) if rows else {}
    share = sum(at) / len(at) if at else None
    stop = bool(rows) and (c["hi90"] >= 0 or share > GOAT_STOP_BOUND_SHARE)
    return {"plan": PLAN, "ledger": f"{LEDGER_ID} {phase}", "searched": len(recs), "labelled": len(lab),
            "held_best_minus_S": {q: c.get(q) for q in ("mean", "lo90", "hi90", "clusters")},
            "input_gain_at_bound_share": share, "stop": stop, "time": time.strftime("%Y-%m-%d %H:%M:%S")}


def stage_check(root, phase, keep=None):
    """`stage_read`, saved and printed. -> root/stage-check.json."""
    out = stage_read(root, phase, keep)
    save(root / "stage-check.json", out)
    h = out["held_best_minus_S"]
    print(f"STAGE CHECK: {out['labelled']} labels; held best - S {h['mean']} [{h['lo90']}, {h['hi90']}];"
          f" inputGain at a bound {out['input_gain_at_bound_share']}; {'STOP' if out['stop'] else 'go on'}")
    return out


def goat_lags_refused(units, heard, tol=None):
    """The one-window lag rule over every heard unit's lag (goat/lags), so every caller (the search, the labels, the
    stage check, the reads) refuses the same units whatever has been searched yet. units: {unit: unit record}.
    -> ({unit: lag}, refused units)."""
    ldir = out_dir() / GOAT_DIR / "lags"
    lags = {u: json.loads((ldir / f"{u.replace('/', '__')}.json").read_text())["lag"] for u in heard}
    return lags, goat_lag_refused(lags, {u: units[u]["item_lag"] for u in heard}, tol)


def goat_read_units(tol=None):
    """5C's read units: the GOAT units the ear passed with a lag the one-window rule keeps (goat/lags); `tol` other
    than GOAT_LAG_TOL only to report a read on a narrower set (the main-mode units at 14)."""
    units = {p_["unit"]: p_ for p_ in goat_units()}
    heard = goat_ear_passed(units)
    lags, off = goat_lags_refused(units, heard, tol)
    return [dict(units[u], lag=lags[u]) for u in sorted(heard) if u not in off]


def centre_records(brecs, by_unit, folds, grecs, gunits, k):
    """5C's centres' labels for model k: RcBG on exactly the lists model k trains on (`real_rows`' `fold_records`
    and `goat_rows`' `goat_fold_records`, each cycled to its rows per epoch), RcGk on its GOAT list alone, RcG on every
    GOAT label."""
    gk = goat_fold_records(grecs, gunits, k)
    return {"RcBG": fold_records(brecs, by_unit, folds, k) + gk, "RcGk": gk, "RcG": grecs}


def cmd_goat_centres(args):
    """5C's centres (zero renders), each by Rc's rule (`rc_setting`) on the class's S. RcBG: on exactly model k's
    training labels, BKS's (`fold_records`) and GOAT's (`goat_fold_records`), each cycled to its rows per epoch, so
    each label weighs by its share of an epoch; same amp and class. RcGk: model k's training GOAT labels alone. RcG:
    every GOAT label (BKS units only). Model k is the BKS unit's DI fold, or the GOAT unit's item fold.
    -> real/answers/{RcBG,RcG}.json (BKS's 40 units), goat/answers/{RcBG,RcGk}.json (the trusted GOAT units)."""
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    e = require("phase_5c")
    brecs, by_unit, folds = real_labels(2)
    grecs, gunits, _ = goat_labels()
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    parts = real_parts(kept, sp, CB.cc_inventory())
    ms = A_menu_S()
    src = {k: centre_records(brecs, by_unit, folds, grecs, gunits, k) for k in range(REAL_FOLDS)}

    def cls_of(r):
        return (by_unit[r["unit"]] if r["unit"] in by_unit else gunits[r["unit"]])["cls"]

    def centre(recs, amp, cls, S):
        labels = [LO.tdict(r["label"]) for r in recs if r["amp"] == amp and cls_of(r) == cls]
        return LO.sdict(rc_setting(K.space(amp, S), S, labels)), len(labels)

    out = {"bks": {"RcBG": {}, "RcG": {}}, "goat": {"RcBG": {}, "RcGk": {}}}
    used = {t: {} for t in ("RcBG", "RcG", "goat-RcBG", "goat-RcGk")}
    for prt in parts:
        k = folds[prt["di"]]
        for amp in AMPS3:
            sel, S = ms[amp][prt["cls"]]
            key = real_key(prt, amp)
            for t in ("RcBG", "RcG"):
                recs = src[k][t]
                st, n = centre(recs, amp, prt["cls"], S)
                out["bks"][t][key] = {ANY_HALF: {"select": sel, "settings": st}}
                used[t][key] = n
    for prt in goat_read_units():
        k, amp = prt["fold"], prt["amp"]
        sel, S = ms[amp][prt["cls"]]
        key = real_key(prt, amp)
        for t in ("RcBG", "RcGk"):
            recs = src[k][t]
            st, n = centre(recs, amp, prt["cls"], S)
            out["goat"][t][key] = {ANY_HALF: {"select": sel, "settings": st}}
            used[f"goat-{t}"][key] = n
    for t, a in out["bks"].items():
        save(out_dir() / REAL_DIR / "answers" / f"{t}.json", {
            "plan": PLAN, "ledger": f"{LEDGER_ID} phase_5c", "tag": t, "parts": parts, "labels_used": used[t],
            "answers": a, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    for t, a in out["goat"].items():
        save(out_dir() / GOAT_DIR / "answers" / f"{t}.json", {
            "plan": PLAN, "ledger": f"{LEDGER_ID} phase_5c", "tag": t, "labels_used": used[f"goat-{t}"],
            "answers": a, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print("GOAT CENTRES DONE: " + "; ".join(f"{t} {len(v)} answers, labels {min(v.values())}-{max(v.values())}"
                                            for t, v in used.items() if v))


def goat_predict(name):
    """RG's (or RGshuf's) answers on the trusted GOAT units (zero renders): each unit read by model `name` + its
    item fold, both seeds pooled at the models' own training inputs' median loudness, per search half, on its
    forced amp, as `real_predict_5b2` reads BKS's units. -> goat/answers/<name>.json."""
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO

    e = require(read_phase(name))
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    units = goat_read_units()
    models = {}
    for k in sorted({p_["fold"] for p_ in units}):
        nm = (ft_name(k, base=name) if name in (FT_BASE, FTM_BASE) else dfix_fold_name(name, k) if name in DFIX_BASES
              else f"{name}{k}")
        nets, recs = zip(*(load_run(nm, sd, "best") for sd in SEEDS))
        for r_ in recs:
            ft_read_check(r_)
        models[k] = (list(nets), [r_["model_sha256"]["best"] for r_ in recs], model_input_lufs(recs[0]))
    ms = A_menu_S()
    out = {}
    for prt in units:
        nets, _, target = models[prt["fold"]]
        ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        g = DE.inference_gain_db(ref, target)
        amp = prt["amp"]
        sel, S = ms[amp][prt["cls"]]
        backed = dfix_backed(prt["unit"]) if name in (*DFIX_BASES, FT_BASE, FTM_BASE) else None   # D_fix, FT: pool-backed
        for search in ("A", "B"):
            if backed is not None:
                s8, ls = backed[search]
            else:
                s8, _, ls, _ = DS.step4_half(ref, ref, search, g)
            x, c = DS.model_input(s8, s8, ls, ls, search, amp, prt["cls"], "Dstem")
            r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
            st = F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"])
            if name == FTM_BASE:
                st = hold_outside_space(st, S, amp)
            out.setdefault(real_key(prt, amp), {})[search] = {"select": sel, "settings": LO.sdict(st)}
    save(out_dir() / GOAT_DIR / "answers" / f"{name}.json", {
        "plan": PLAN, "ledger": f"{LEDGER_ID} {read_phase(name)}",
        "tag": name,
        "models": {k: {"sha256": m[1], "input_lufs": m[2]} for k, m in models.items()}, "answers": out,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"GOAT PREDICT DONE: {name} on {len(units)} units")


def cmd_goat_predict(args):
    if args.names not in ("P2a-goat", "P2a-goatshuf", *DFIX_BASES, FT_BASE, FTM_BASE):
        raise SystemExit(f"--names P2a-goat, P2a-goatshuf, {FT_BASE} or one of {', '.join(DFIX_BASES)} (fold models)")
    goat_predict(args.names)


def cmd_goat_render(args):
    """5C's read renders on the trusted GOAT units (one shard): each answer of `--names` (goat/answers) through the
    unit's DI in its own primed process (`fresh_render`), over the whole section, trimmed, judged against the render
    on both halves at the unit's lag. -> goat/judge/<tag>/<unit>|<amp>.json."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    require("phase_5c")
    tags = [t for t in args.names.split(",") if t]
    ans = {t: json.loads((out_dir() / GOAT_DIR / "answers" / f"{t}.json").read_text())["answers"] for t in tags}
    units = goat_read_units()
    k, n = args.shard
    mine = [p_ for j, p_ in enumerate(units) if j % n == k]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    for prt in mine:
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        key = real_key(prt, prt["amp"])
        for t in tags:
            if key not in ans[t]:
                continue
            gp = out_dir() / GOAT_DIR / "judge" / t / f"{key.replace('/', '__')}.json"
            asha = answers_sha({key: ans[t][key]})
            if gp.exists():
                if json.loads(gp.read_text()).get("answers_sha256") != asha:
                    raise SystemExit(f"{gp}: rendered from other answers")
                continue
            rec = {"unit": prt["unit"], "amp": prt["amp"], "tag": t, "lag": prt["lag"], "answers_sha256": asha,
                   "judge": {}, "render_sha256": {}}
            for search, a in sorted(ans[t][key].items()):
                st = LO.tdict(a["settings"])
                y = np.asarray(AM.fresh_render(CB.new_renderer, di32, a["select"], st, st), np.float64)[trim[0]:trim[1]]
                renders += 2
                rec["judge"][search] = K.judge(ref, y, di, prt["lag"])
                rec["render_sha256"][search] = AM.audio_sha(y)
            save(gp, rec)
        print(f"{prt['unit'][-60:]}: renders so far {renders}", flush=True)
    print(f"GOAT-RENDER DONE {k}/{n}: {renders} renders")


def cmd_goat_report(args):
    """5C's read A (zero renders): for each pair in `--pairs`, ln(d_a / d_b) on the held half per (unit, search half)
    on the trusted GOAT units (a model's answer for the search half, a centre's for any half; a missing or non-finite
    judge drops the direction, counted), clustered by item (an item's renders share its playing), with the 4-fold
    interval beside (a fold's units share models). -> goat/report-<label>.json."""
    require("phase_5c")
    units = {p_["unit"]: p_ for p_ in goat_read_units(args.lag_tol)}
    tags = {t for pair in args.pairs.split(",") for t in pair.split(":")}
    judge = {}
    for t in tags:
        judge[t] = {}
        for p_ in (out_dir() / GOAT_DIR / "judge" / t).glob("*.json"):
            r = json.loads(p_.read_text())
            judge[t][f"{r['unit']}|{r['amp']}"] = r["judge"]
    if "S" in tags:                                    # S's judges live in the search records
        judge["S"] = {f"{r['unit']}|{r['amp']}": {ANY_HALF: r["s_judge"]} for r in goat_labels()[0]}
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_5c", "units": len(units),
           "lag_tol": GOAT_LAG_TOL if args.lag_tol is None else args.lag_tol, "rows": {}}
    keep = ("mean", "lo90", "hi90", "clusters", "clusters_negative", "part_weighted", "parts", "parts_negative")
    for pair in args.pairs.split(","):
        a, b = pair.split(":")
        rows, missing = [], 0
        for u, prt in sorted(units.items()):
            for sh, h in (("A", "B"), ("B", "A")):
                vals = [vreal_value(judge, t, (u, prt["amp"], sh, h)) for t in (a, b)]
                if any(v is None or v == "refused" for v in vals):
                    missing += 1
                    continue
                rows.append((prt["item"], u, math.log(vals[0] / vals[1]), prt["fold"]))
        c = clustered([r[:3] for r in rows])
        f = clustered([(r[3], r[1], r[2]) for r in rows])
        out["rows"][f"{a} - {b}"] = {**{q: c.get(q) for q in keep}, "missing": missing,
                                     "per_item": c.get("per_cluster"),
                                     "by_fold": {q: f.get(q) for q in keep + ("per_cluster",)}}
        if c["mean"] is not None:
            print(f"{a} - {b}: {c['mean']:+.4f} [{c['lo90']:+.4f}, {c['hi90']:+.4f}] by item ({c['clusters']} items, "
                  f"{c['clusters_negative']} better); by fold {f['mean']:+.4f} [{f['lo90']:+.4f}, {f['hi90']:+.4f}]; "
                  f"missing {missing}")
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save(out_dir() / GOAT_DIR / f"report-{args.label or 'goat'}.json", out)
    print("GOAT-REPORT DONE")


def goat_items_from(z):
    import csv
    import io

    return list(csv.DictReader(io.StringIO(z.read("GOAT/metadata.csv").decode())))


REAL_ROW0 = 3_000_000               # 5B.2's real rows: ids from here (no D_CC example id reaches it)
REAL_PER_EPOCH = 300                # every fold shows this many real rows per epoch (its labelled rows cycled)
REAL_FOLDS = 4
REAL_FOLD_SEED = 20261039


def real_folds(read_parts, all_parts, k=REAL_FOLDS, seed=REAL_FOLD_SEED):
    """5B.2's folds: the DIs in pairs (k folds), the pairing that makes the folds' read-unit counts most equal (the
    smallest range, then the smallest spread of all units), ties broken by a seeded order. -> {di: fold}."""
    import itertools
    import random

    dis = sorted({p_["di"] for p_ in all_parts})
    if len(dis) != 2 * k:
        raise SystemExit(f"{len(dis)} DIs: 5B.2's folds pair 8")
    nr = {d: sum(p_["di"] == d for p_ in read_parts) for d in dis}
    na = {d: sum(p_["di"] == d for p_ in all_parts) for d in dis}

    def pairings(xs):
        if not xs:
            yield []
            return
        a = xs[0]
        for j in range(1, len(xs)):
            for rest in pairings(xs[1:j] + xs[j + 1:]):
                yield [(a, xs[j])] + rest

    cands = list(pairings(dis))
    random.Random(seed).shuffle(cands)

    def score(pr):
        r = [nr[a] + nr[b] for a, b in pr]
        t = [na[a] + na[b] for a, b in pr]
        return (max(r) - min(r), max(t) - min(t))

    best = min(cands, key=score)
    return {d: f for f, pr in enumerate(sorted(best)) for d in pr}


def real_input_path(unit):
    return out_dir() / REAL_DIR / "inputs" / f"{unit.replace('/', '__')}.npz"


def real_labels(stage):
    """5B.2's labelled search records of stages up to `stage`, with their units and the folds. -> (records, {unit:
    part}, {di: fold})."""
    from learn import cc_build as CB

    e = require("phase_5b2")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    inv = CB.cc_inventory()
    allp = stage_units(kept, sp, inv, 1) + stage_units(kept, sp, inv, 2)
    folds = real_folds(stage_units(kept, sp, inv, 1), allp)
    recs = [json.loads(p_.read_text()) for p_ in sorted((out_dir() / REAL_DIR / SEARCH_DIR).glob("*.json"))]
    off = lag_refused(recs)
    return ([r for r in recs if r["stage"] <= stage and r["label"] is not None and r["unit"] not in off],
            {p_["unit"]: p_ for p_ in allp}, folds)


LAG_TOL = 14                        # samples (0.3 ms at 48 kHz: pooled renders' agreement, `estimate_lag`)


def lag_refused(recs):
    """Units whose judge lag is more than LAG_TOL samples from the median lag of their recording's windows (one rig,
    every search stage): either the estimate locked onto another peak or the track's alignment changes within that
    window, so the unit's lag is not trusted and its labels are refused. -> set of units."""
    import statistics

    lags = {}
    for r in recs:
        if r["lag"] is not None:
            lags.setdefault(r["rig"], {})[r["unit"]] = r["lag"]
    return {u for units in lags.values() for u, lag in units.items()
            if abs(lag - statistics.median(units.values())) > LAG_TOL}


def cycled(items, n):
    """`items` repeated in order until there are n of them (every item k or k+1 times)."""
    return [items[j % len(items)] for j in range(n)] if items else []


def real_rows(fold, target, stage=1):
    """5B.2's arm R training rows for fold `fold`: the labelled (unit, amp) records of search stages up to `stage`
    whose DI is outside the fold, cycled to REAL_PER_EPOCH rows (the same real share in every fold); input the reamped
    section brought to `target` LUFS (5B.1's path, both halves; cached), label the search's best setting
    (`F.label_of`). -> (rows, {id: input path}, {di: fold})."""
    recs, by_unit, folds = real_labels(stage)
    rows, paths = real_rows_for(fold_records(recs, by_unit, folds, fold), by_unit, target)
    return rows, paths, folds


def fold_records(recs, by_unit, folds, fold):
    """Arm R's training records for fold `fold`: the labelled records whose DI is outside the fold, cycled to
    REAL_PER_EPOCH (a fold's models never see their own DIs' real tracks)."""
    return cycled([r for r in recs if folds[by_unit[r["unit"]]["di"]] != fold], REAL_PER_EPOCH)


def real_rows_for(recs, by_unit, target):
    """Training or reading rows for labelled search records (one row per record, ids from REAL_ROW0), their inputs
    cached. -> (rows, {id: input path})."""
    import numpy as np

    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO

    rows, paths = [], {}
    for j, rec in enumerate(recs):
        prt = by_unit[rec["unit"]]
        ip = real_input_path(prt["unit"])
        if not ip.exists():
            ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            g = DE.inference_gain_db(ref, target)
            (sa, _, la, _), (sb, _, lb, _) = (DS.step4_half(ref, ref, h, g) for h in ("A", "B"))
            ip.parent.mkdir(parents=True, exist_ok=True)
            np.savez(ip, sA=sa, sB=sb, lufs=np.array([la, lb], np.float32), target=np.float64(target))
        if float(np.load(ip)["target"]) != float(target):
            raise SystemExit(f"{ip.name}: built for another input loudness")
        i = REAL_ROW0 + j
        rows.append({"i": i, "section": prt["section"], "band": prt["band"], "amp": rec["amp"], "cls": prt["cls"],
                     "base": prt["cls"], "label": F.label_of(LO.tdict(rec["label"]), rec["amp"]),
                     "real": rec["unit"]})
        paths[i] = ip
    return rows, paths


def ceiling_rows(recs):
    """5B.2's ceiling rows from stored search records: ln(d / d_S) on the held half for the best and the shrunk
    setting, as 5B.1's rule (S refused drops the direction; a refused answer is scored as S). -> {name: [(di, unit,
    v)]}, {name: [(rig, unit, v)]}, the counts."""
    by_di, by_rig, cnt = {"best": [], "shrunk": []}, {"best": [], "shrunk": []}, {"s_dropped": 0, "refused_as_S": 0}
    for r in recs:
        s = r["s_judge"][r["held"]]
        if not (s is not None and math.isfinite(s) and s > 0):
            cnt["s_dropped"] += 1
            continue
        for nm in ("best", "shrunk"):
            d = r[nm]["judge"][r["held"]]
            if not (math.isfinite(d) and d > 0):
                cnt["refused_as_S"] += 1
                d = s
            v = math.log(d / s)
            by_di[nm].append((r["di"], r["unit"], v))
            by_rig[nm].append((r["rig"], r["unit"], v))
    return by_di, by_rig, cnt


def cmd_real_ceiling(args):
    """5B.2's ceiling read (zero renders): best - S and shrunk - S on the held half, clustered by DI, by rig beside,
    part-weighted beside, for search stage `--stage` (stage 1 decides whether stage 2 runs). The search-half values are
    reported apart (selected on, so optimistic). Each `--names` tag's share of the ceiling, paired on its directions,
    with a 90% interval resampling DIs and its distance from the best beside; with `--within` only the directions
    that tag's answers cover. -> real/report-ceiling-<stage>[-within-<tag>].json."""
    require("phase_5b2")
    recs = [json.loads(p_.read_text()) for p_ in sorted((out_dir() / REAL_DIR / SEARCH_DIR).glob("*.json"))]
    recs = [r for r in recs if r["stage"] == args.stage]
    if args.within:
        cover = json.loads((out_dir() / REAL_DIR / "answers" / f"{args.within}.json").read_text())["answers"]
        recs = [r for r in recs if f"{r['unit']}|{r['amp']}" in cover]
    by_di, by_rig, cnt = ceiling_rows(recs)
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_5b2", "stage": args.stage, "directions": len(recs),
           "units": len({r["unit"] for r in recs}), "counts": cnt,
           "labels": sum(r["label"] is not None for r in recs),
           "s_first_bit_identical": sum(bool(r["s_first"]) and r["s_first"]["sha"] == r["s_render_sha256"]
                                        for r in recs),
           "rows": {nm: {"by_di": clustered(by_di[nm]), "by_rig": clustered(by_rig[nm])} for nm in by_di},
           "search_half_best_minus_S": statistics.fmean(
               math.log(r["best_search_value"] / r["s_judge"][r["search"]]) for r in recs
               if r["s_judge"][r["search"]] and math.isfinite(r["best_search_value"])) if recs else None,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    for t in [t for t in args.names.split(",") if t]:      # paired on the ceiling's directions: a model's share of it
        rows, best_rows = [], []
        for r in recs:
            gp = out_dir() / REAL_DIR / "judge" / t / f"{(r['unit'] + '|' + r['amp']).replace('/', '__')}.json"
            if not gp.exists():
                continue
            j = json.loads(gp.read_text())["judge"]
            d = (j.get(r["search"]) or j.get(ANY_HALF) or {}).get(r["held"])
            s_ = r["s_judge"][r["held"]]
            b_ = r["best"]["judge"][r["held"]]
            if d is None or not (s_ and math.isfinite(s_)):
                continue
            d = d if math.isfinite(d) and d > 0 else s_
            b_ = b_ if math.isfinite(b_) and b_ > 0 else s_
            rows.append((r["di"], r["unit"], math.log(d / s_)))
            best_rows.append((r["di"], r["unit"], math.log(b_ / s_)))
        if rows:
            c, cb = clustered(rows), clustered(best_rows)
            sh = share_recovered([(a[0], a[1], -a[2], -b[2]) for a, b in zip(rows, best_rows)])
            tb = clustered([(a[0], a[1], a[2] - b[2]) for a, b in zip(rows, best_rows)])
            out.setdefault("share_of_ceiling", {})[t] = {
                "tag_minus_S": {q: c.get(q) for q in ("mean", "lo90", "hi90", "clusters")},
                "best_minus_S": cb["mean"], "share": c["mean"] / cb["mean"] if cb["mean"] else None,
                "share_lo90": sh[1], "share_hi90": sh[2],
                "tag_minus_best": {q: tb.get(q) for q in ("mean", "lo90", "hi90")}, "directions": len(rows)}
    if args.within:
        out["within"] = args.within
    tail = f"-within-{args.within}" if args.within else ""
    save(out_dir() / REAL_DIR / f"report-ceiling-{args.stage}{tail}.json", out)
    for nm, r_ in out["rows"].items():
        d = r_["by_di"]
        print(f"{nm} - S (held half): {d['mean']:+.3f} [{d['lo90']:+.3f}, {d['hi90']:+.3f}] by DI, "
              f"{d['clusters_negative']} of {d['clusters']} better; by rig {r_['by_rig']['mean']:+.3f}; "
              f"part-weighted {d['part_weighted']:+.3f}")
    print(f"CEILING DONE stage {args.stage}: {out['directions']} directions, {out['labels']} labels, {cnt}")


def cmd_real_heads(args):
    """5B.2's zero-render reads by head (eval mode, the fixed half), both seeds' NS-best checkpoints. `--names R`: each
    fold's arm R model against P2a on that fold's own DIs' real labels (search stages up to `--stage`, never trained
    on by that fold), and on NS and FS (the guard for plugin skill). `--names P`: P2a-pc, P2a-pcsz and P2a on FS and NS,
    split by the example's draw mode. -> real/heads-<names>[s2].json."""
    import numpy as np
    import torch

    e = require("phase_5b2")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    doubled = doubled_ids() if dropped["doubles"] == "fixed" else frozenset()
    base_path = rung_path(croot, "a", doubled)
    dev = device()

    def fam(name, sd, data, idx):
        net, _ = load_run(name, sd, "best")
        net.to(dev)
        with torch.no_grad():
            return family_means(head_losses(net, data, np.asarray(idx), dev))

    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {'phase_5c' if args.names == 'G' else 'phase_5b2'}",
           "names": args.names, "rows": {}}
    if args.names in ("R", "G"):                       # G: 5C's RG against P2a-reals2 and P2a (its guard)
        stage = 2 if args.names == "G" else max(1, args.stage)
        recs, by_unit, folds = real_labels(stage)
        sfx = "s2" if stage == 2 else ""
        plug = {k: rung_rows(kept, rend, sp[k]) for k in ("ns", "fs")}
        plug_data = {k: RungData(v, base_path) for k, v in plug.items()}
        target = p2a_median_lufs(sp["train"])
        for k in range(REAL_FOLDS):
            mine = [r for r in recs if folds[by_unit[r["unit"]]["di"]] == k]
            rows, paths = real_rows_for(mine, by_unit, target)
            data = RungData(rows, lambda i: paths[i])
            for sd in SEEDS:
                row = {"fold": k, "seed": sd, "real_rows": len(rows)}
                names = (f"P2a-goat{k}", f"P2a-real{k}s2", "P2a") if args.names == "G" else (f"P2a-real{k}{sfx}", "P2a")
                for nm in names:
                    row[nm] = {"real": fam(nm, sd, data, range(len(rows))),
                               **{q: fam(nm, sd, plug_data[q], range(len(plug[q]))) for q in plug}}
                out["rows"][f"fold{k}-{sd}"] = row
                kj = {nm: {q: round(row[nm][q]["knob_joint"], 4) for q in ("real", "ns", "fs")} for nm in names}
                print(f"fold {k} seed {sd}: knob joint (own DIs' real labels, NS, FS) {kj}", flush=True)
    elif args.names == "P":
        for q in ("ns", "fs"):
            for mode in ("factory", "start", "wide"):
                ids = [i for i in sp[q] if kept[i]["mode"] == mode]
                rows = rung_rows(kept, rend, ids)
                data = RungData(rows, base_path)
                for sd in SEEDS:
                    out["rows"][f"{q}-{mode}-{sd}"] = {nm: fam(nm, sd, data, range(len(rows)))
                                                      for nm in ("P2a-pc", "P2a-pcsz", "P2a")}
                print(f"{q} {mode}: done", flush=True)
    else:
        raise SystemExit("--names R, G or P")
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save(out_dir() / REAL_DIR / f"heads-{args.names}{'s2' if args.stage == 2 and args.names != 'G' else ''}.json", out)
    print("REAL-HEADS DONE")


ARM_FOLD_PHASES = ("phase_5b2", "phase_5c", "phase_dfix", "phase_ft", "phase_ft_groups", "phase_night2")    # real-report's phases whose models share 5B.2's DI folds


def report_phase(tags):
    """real-report's ledger phase for the tags it reads."""
    return ("phase_ft_groups" if any(t.startswith("FTg-") for t in tags) else "phase_night2" if tags & {FTM_BASE, FTH_TAG} else "phase_ft" if FT_BASE in tags else "phase_dfix" if tags & DFIX_READS else "phase_5c" if tags & {"P2a-goat", "P2a-goatshuf", "RcBG", "RcG"}
            else "phase_5b2_rigo" if tags & {"RigO", "RcM"}
            else "phase_5b2" if any(t.startswith(("P2a-pc", "P2a-real", "Rc")) for t in tags)
            else "phase_5b1b" if any(t in ("P2a-Sc", "S-shift") for t in tags) else "phase_5b1")


def cmd_real_report(args):
    """5B.1's rows: for each pair in `--pairs`, ln(d_a / d_b) on the held half per (unit, amp, search), with S
    refused dropping the direction and a refused answer scored as S (the V-real rule); clustered by DI (the
    performance: rigs sharing a DI share its sections and its S and constant renders), parts the units; by rig beside;
    part-weighted beside; the lag refusals counted apart from the missing; with `--within` only the directions that
    tag's answers cover. -> real/report-<label>.json."""
    e = require("phase_5b1")
    tags = {t for pair in args.pairs.split(",") for t in pair.split(":")} | {"S"}
    bad = ftg_unhashed(sorted(tags), e)
    if bad:
        raise SystemExit(f"the answers' hashes are not the ledger's: {bad}")
    parts = json.loads((out_dir() / REAL_DIR / "answers" / "S.json").read_text())["parts"]
    judge = {}
    for t in tags:
        judge[t] = {}
        for p_ in (out_dir() / REAL_DIR / "judge" / t).glob("*.json"):
            r = json.loads(p_.read_text())
            judge[t][f"{r['unit']}|{r['amp']}"] = r["judge"]
    no_lag = [p_["unit"] for p_ in parts if (out_dir() / REAL_DIR / "lags" / f"{p_['unit'].replace('/', '__')}.json")
              .exists() and json.loads((out_dir() / REAL_DIR / "lags" / f"{p_['unit'].replace('/', '__')}.json")
                                       .read_text())["lag"] is None]
    meta = {p_["unit"]: p_ for p_ in parts}
    phase = report_phase(tags)
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {phase}", "units": len(parts), "no_lag": no_lag, "rows": {}}
    units = [(p_["unit"], amp, sh, h) for p_ in parts for amp in AMPS3 for sh, h in (("A", "B"), ("B", "A"))]
    if args.within:                                    # only the directions `--within`'s answers cover (RigO's)
        cover = json.loads((out_dir() / REAL_DIR / "answers" / f"{args.within}.json").read_text())["answers"]
        units = [u for u in units if f"{u[0]}|{u[1]}" in cover]
        out["within"] = args.within
    fold_of = None
    if phase.startswith(ARM_FOLD_PHASES):              # arm R's (and RG's) folds: the DIs that share a pair of models
        from learn import cc_build as CB

        e = require("phase_5b2")
        _, kept, _, sp, _ = recipe_inputs(pin=e.get("phase_3_doubles"))
        inv = CB.cc_inventory()
        s1 = stage_units(kept, sp, inv, 1)
        fold_of = real_folds(s1, s1 + stage_units(kept, sp, inv, 2))
    for pair in args.pairs.split(","):
        a, b = pair.split(":")
        rows, cnt = [], {"directions": len(units), "base_dropped": 0, "missing": 0, "refused_scored_as_S": 0}
        for u in units:
            if u[0] in no_lag:
                continue
            s_ = vreal_value(judge, "S", u)
            if s_ is None:
                cnt["missing"] += 1
                continue
            if s_ == "refused":
                cnt["base_dropped"] += 1
                continue
            vals = []
            for t in (a, b):
                v = vreal_value(judge, t, u)
                if v is None:
                    cnt["missing"] += 1
                    break
                if v == "refused":
                    cnt["refused_scored_as_S"] += 1
                    v = s_
                vals.append(v)
            if len(vals) == 2:
                rows.append((meta[u[0]]["di"], u[0], math.log(vals[0] / vals[1]), meta[u[0]]["rig"]))
        keep = ("mean", "lo90", "hi90", "clusters", "clusters_negative", "part_weighted", "parts", "parts_negative")
        c = clustered([r[:3] for r in rows])
        by_rig = clustered([(r[3], r[1], r[2]) for r in rows])
        out["rows"][f"{a} - {b}"] = {**{q: c.get(q) for q in keep}, **cnt,
                                     "per_di": c.get("per_cluster"), "by_rig": {q: by_rig.get(q) for q in keep}}
        if fold_of is not None:
            by_fold = clustered([(fold_of[meta[r[1]]["di"]], r[1], r[2]) for r in rows])
            out["rows"][f"{a} - {b}"]["by_fold"] = {q: by_fold.get(q) for q in keep + ("per_cluster",)}
        r_ = out["rows"][f"{a} - {b}"]
        if r_["mean"] is not None:
            iv = "" if r_["lo90"] is None else f" [{r_['lo90']:+.4f}, {r_['hi90']:+.4f}]"
            print(f"{a} - {b}: {r_['mean']:+.4f}{iv} ({r_['clusters']} DIs, {r_['clusters_negative']} better; "
                  f"{r_['parts_negative']} of {r_['parts']} units better); missing {cnt['missing']}, S dropped "
                  f"{cnt['base_dropped']}, refused {cnt['refused_scored_as_S']}")
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save(out_dir() / REAL_DIR / f"report-{args.label or 'real'}.json", out)
    print("REAL-REPORT DONE")


# --- stored derived reads (the audit: every quoted number reproducible) ---------------------------------------------

def share_recovered(rows, n=4000, seed=20261036):
    """The share of a loss a fix recovers: rows [(cluster, part, recovered, lost)] per example (recovered = before -
    after, lost = before - reference). Each is averaged by the log's `clustered` rule (parts within clusters, then
    clusters) and the share is their ratio; its 90% interval resamples whole clusters. -> (share, lo, hi)."""
    import random

    def ratio(rs):
        a = clustered([(c, p, x) for c, p, x, _ in rs])["mean"]
        b = clustered([(c, p, y) for c, p, _, y in rs])["mean"]
        return a / b
    pt = ratio(rows)
    cl = sorted({r[0] for r in rows})
    rng = random.Random(seed)
    bs = []
    for _ in range(n):
        pick = []
        for k, c in enumerate(rng.choice(cl) for _ in cl):
            pick += [(f"{c}#{k}", p, x, y) for cc, p, x, y in rows if cc == c]
        try:
            bs.append(ratio(pick))
        except ZeroDivisionError:
            pass
    bs.sort()
    return pt, bs[int(0.05 * (len(bs) - 1))], bs[int(0.95 * (len(bs) - 1))]


def cmd_share(args):
    """F24's share of P2a - P2b that a backing-trained P2b recovers, by sound on the sample, FS by band and NS by
    section (the log's rows). `--name` is the model (default P2b-bk8; phase 5A's P2b-wide24); `--seeds` lists answer
    tags' seeds to pool (default its first seed alone): each example's log ratio against S is the mean over those
    seeds' answers (phase_5a_seed2's pooling, no ensemble render). -> sound/share-backings.json (P2b-bk8) or
    sound/share-<name>[-x<seeds>].json. Zero renders. With `--against` (a tag), also the per-seed and seed-pooled
    paired rows <name> - <against>, clustered as the sound report."""
    from learn import cc_build as CB

    name = args.name or "P2b-bk8"
    require("phase_5a" if name == "P2b-wide24" else "phase_3_backings")
    seeds = [int(z) for z in args.seeds.split(",")]
    tags = [f"{name}-best" + ("" if sd == SEEDS[0] else f"-x{sd}") for sd in seeds]
    if len(seeds) > 1:
        require("phase_5a_seed2")
    ex = {x["i"]: x for x in CB.load_plan(argparse.Namespace(out=None, smoke=False))["examples"]}
    ids = sample_ids(SAMPLE_N)

    def j(t, i):
        return json.loads((out_dir() / SOUND_DIR / "judge" / t / f"{i}.json").read_text())["judge"]

    def model(i, base="S"):
        return statistics.fmean(log_ratio(j(t, i), j(base, i)) for t in tags)

    out = {"model": name, "tags": tags, "rule": "share = clustered(P2b - <model>) / clustered(P2b - P2a), each by "
           "sound against S per example (the model's value the mean over its seeds' answers); parts are sections, "
           "clusters bands (FS) or sections (NS); 90% interval by resampling clusters"}
    for st, key in (("fs", "band"), ("ns", "section")):
        rows = []
        for i in ids[st]:
            a, b = (log_ratio(j(t, i), j("S", i)) for t in ("P2a-best", "P2b-best"))
            rows.append((ex[i][key], ex[i]["section"], b - model(i), b - a))
        pt, lo, hi = share_recovered(rows)
        out[st] = {"share": pt, "lo90": lo, "hi90": hi, "examples": len(rows)}
        print(f"{st}: share recovered {pt:.3f} [{lo:.3f}, {hi:.3f}]")
        if args.against:
            for lab, ts in [(t, [t]) for t in tags] + ([("pooled", tags)] if len(tags) > 1 else []):
                c = clustered([(ex[i][key], ex[i]["section"], statistics.fmean(
                    log_ratio(j(t, i), j(args.against, i)) for t in ts)) for i in ids[st]])
                out.setdefault("paired", {}).setdefault(f"{lab} - {args.against}", {})[st] = {
                    q: c.get(q) for q in ("mean", "lo90", "hi90", "clusters", "clusters_negative", "parts",
                                          "parts_negative", "part_weighted")}
                print(f"  {lab} - {args.against} {st}: {c['mean']:+.4f} [{c['lo90']:+.4f}, {c['hi90']:+.4f}] "
                      f"({c['clusters_negative']} of {c['clusters']} better)")
    suffix = "" if len(seeds) == 1 and seeds[0] == SEEDS[0] else "-x" + "+".join(map(str, seeds))
    save(out_dir() / SOUND_DIR / ("share-backings.json" if name == "P2b-bk8" and not suffix
                                  else f"share-{name}{suffix}.json"), out)


def setting_gap(dims, x, y):
    """How far setting x sits from setting y over `dims`: the rms of their unit differences on the continuous (and
    log) dims, and the share of the other dims (switches, mics) on which they agree (None with none). -> (rms, share)."""
    from learn import arm_a_levers as L

    cont = [(L.unit(d, x) - L.unit(d, y)) ** 2 for d in dims if d.kind in ("cont", "log")]
    cats = [x.get((d.module, d.key)) == y.get((d.module, d.key)) for d in dims if d.kind not in ("cont", "log")]
    return (statistics.fmean(cont) ** 0.5 if cont else None), (statistics.fmean(cats) if cats else None)


def cmd_real_setting_audit(args):
    """F34's setting-space audit (zero renders): on every (unit, amp) of 5B.1's units with a search label, each
    answer of `--names` (each half's answer where a model reads per half; S and Rc answer once) against the unit's own
    label: the rms unit distance over `K.space`'s continuous dims and the share of its switches and mics that agree,
    averaged over answers; beside, each name's distance from Rc's answer (does it move off the centre?). Labels of
    search stages up to `--stage`; with `--within` only the (unit, amp) that tag's answers cover.
    -> real/setting-audit[-s2][-within-<tag>].json."""
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    require("phase_5b2")
    stage = max(1, args.stage)
    sfx = "s2" if stage == 2 else ""
    recs, by_unit, folds = real_labels(stage)
    lab = {(r["unit"], r["amp"]): LO.tdict(r["label"]) for r in recs}
    names = [t for t in (args.names or "P2a-real,Rc,P2a,P2a-Sc").split(",") if t]
    rc = "Rc" + sfx
    d = out_dir() / REAL_DIR / "answers"
    ans = {t: json.loads((d / f"{t}.json").read_text())["answers"] for t in set(names) | {rc}}
    cover = json.loads((d / f"{args.within}.json").read_text())["answers"] if args.within else None
    ms = A_menu_S()
    gaps = {t: [] for t in names + ["S"]}
    to_rc = {t: [] for t in names}
    for key in sorted(ans[rc]):
        unit, amp = key.rsplit("|", 1)
        if (unit, amp) not in lab or (cover is not None and key not in cover):
            continue
        y = lab[(unit, amp)]
        S = ms[amp][by_unit[unit]["cls"]][1]
        dims = K.space(amp, S)
        c = LO.tdict(ans[rc][key][ANY_HALF]["settings"])
        for t in names:
            for a in ans[t][key].values():
                x = LO.tdict(a["settings"])
                gaps[t].append(setting_gap(dims, x, y))
                to_rc[t].append(setting_gap(dims, x, c)[0])
        gaps["S"].append(setting_gap(dims, S, y))

    def mean(v):
        v = [z for z in v if z is not None]
        return statistics.fmean(v) if v else None
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_5b2", "stage": stage, "labels": len(lab), "within": args.within,
           "to_own_label": {t: {"answers": len(g), "rms_unit": mean([a for a, _ in g]),
                                "switch_mic_agree": mean([b for _, b in g])} for t, g in gaps.items()},
           "to_rc_rms_unit": {t: mean(v) for t, v in to_rc.items()}, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    tail = ("-s2" if sfx else "") + (f"-within-{args.within}" if args.within else "")
    save(out_dir() / REAL_DIR / f"setting-audit{tail}.json", out)
    for t, g in out["to_own_label"].items():
        print(f"{t}: to its own label rms {g['rms_unit']:.3f}, switches and mics agree {g['switch_mic_agree']:.3f}"
              + (f"; from {rc} {out['to_rc_rms_unit'][t]:.3f}" if t in out["to_rc_rms_unit"] else ""))
    print("REAL-SETTING-AUDIT DONE")


def cmd_prior_edges(args):
    """F27: where the presets the true-DI search found for V-real-10's parts (arm A's ZT `settings.best`, both halves)
    sit within the ladder's training labels: for every today's-space continuous control that sounds in the searched
    preset, its percentile among the training labels of the same (amp, part class) where it sounds; beside it the same
    for the NS labels (the reference) and for S. Stored to prior-edges.json. Zero renders."""
    import bisect
    import glob

    from learn import arm_a_mega53 as A
    from learn import full_space as F

    e = require("phase_4")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    today = [j for j, nme in enumerate(F.CONT) if nme in F.TODAY]

    def enc(settings, amp):
        x = {tuple(k.rsplit("/", 1)): v for k, v in settings.items()}
        c, cm, *_ = F.encode(x, amp)
        return c, cm
    train = {}
    for i in sp["train"]:
        c, cm = enc(rend[i]["settings"], kept[i]["amp"])
        for j in today:
            if cm[j] > 0:
                train.setdefault((kept[i]["amp"], kept[i]["cls"], j), []).append(float(c[j]))
    for v in train.values():
        v.sort()

    def pct(cell, j, val):
        """Mid-rank percentile: the labels strictly below plus half the labels tied with the value, over all."""
        vals = train.get((*cell, j))
        if not vals:
            return None
        lo, hi = bisect.bisect_left(vals, val), bisect.bisect_right(vals, val)
        return (lo + 0.5 * (hi - lo)) / len(vals)

    def summary(ps):
        ps = [q for q in ps if q is not None]
        return {"values": len(ps), "outside_5_95": sum(q < 0.05 or q > 0.95 for q in ps) / len(ps),
                "below_5": sum(q < 0.05 for q in ps) / len(ps), "above_95": sum(q > 0.95 for q in ps) / len(ps)}
    ref = []
    for i in sp["ns"]:
        c, cm = enc(rend[i]["settings"], kept[i]["amp"])
        ref += [pct((kept[i]["amp"], kept[i]["cls"]), j, float(c[j])) for j in today if cm[j] > 0]
    found, moved, per = [], [], {}
    ms = A.L.menu_S()
    for p in sorted(glob.glob(str(DATA / "learn/arm-a-mega53/F-perfect-sep/ZT/*/*/[AB].json"))):
        d = json.loads(pathlib.Path(p).read_text())
        if d["slug"] not in PR.VREAL:
            continue
        cell = (d["amp"], PR.VREAL[d["slug"]][1])
        c, cm = enc(d["settings"]["best"], d["amp"])
        s0, _, *_ = F.encode(ms[d["amp"]][cell[1]][1], d["amp"])
        for j in today:
            if cm[j] > 0:
                q = pct(cell, j, float(c[j]))
                found.append(q)
                per.setdefault(F.CONT[j], []).append(q)
                if abs(float(c[j]) - float(s0[j])) > 1e-6:          # the search moved it off S
                    moved.append(q)
    s_ = []
    for amp, by in ms.items():
        for cls, (_, S) in by.items():
            c, cm, *_ = F.encode(S, amp)
            s_ += [pct((amp, cls), j, float(c[j])) for j in today if cm[j] > 0]
    out = {"rule": "mid-rank percentile (labels below plus half the tied ones) of each sounding today's-space continuous "
                   "control among the ladder's training labels of the same (amp, part class) where it sounds; outside = "
                   "below the 5th or above the 95th",
           "search_best": summary(found), "search_best_moved_off_S": summary(moved), "ns_labels": summary(ref),
           "S": summary(s_),
           "per_control": {k: {"values": len([q for q in v if q is not None]), **summary(v)}
                           for k, v in sorted(per.items())}}
    save(out_dir() / "prior-edges.json", out)
    for k in ("search_best", "search_best_moved_off_S", "ns_labels", "S"):
        print(k, out[k])
    for k, v in sorted(out["per_control"].items(), key=lambda kv: -kv[1]["outside_5_95"])[:10]:
        print(f"  {k:32s} {v['outside_5_95']:.2f} (n {v['values']})")


# --- phase 4: V-real (P4: the clean-input model on real amp tracks; P3: the readouts), measurements only ------------

VREAL_DIR = "vreal"
SAME_INPUT = {"cambridge-wickerman-elecgtr2": "cambridge-wickerman-elecgtr2+3",
              "cambridge-wickerman-elecgtr3": "cambridge-wickerman-elecgtr2+3"}   # one input (review step 32)
ANY_HALF = "*"                      # an answer that does not depend on the search half (S, S', the constant)


def vreal_part_key(slug):
    """The unit a part's rows average into: Wickerman ElecGtr2 and 3 share one stem input, so in a stem or mix read
    they count as one (step 32); with `own_inputs` (P4: each its own amp track) they stay two."""
    return SAME_INPUT.get(slug, slug)


def part_members(key):
    """The V-real slugs a row's part key stands for."""
    return [m for m in PR.VREAL if m == key or vreal_part_key(m) == key]


def vreal_value(judge, tag, unit):
    """One answer's held-half distance on one direction: None (not rendered), "refused" (judged non-finite), or the
    distance. An answer stored for ANY_HALF serves every search half."""
    slug, amp, search, held = unit
    g = judge.get(tag, {}).get(f"{slug}|{amp}") or {}
    v = g.get(search) or g.get(ANY_HALF)
    if v is None or v.get(held) is None:
        return None
    x = v[held]
    return x if (isinstance(x, (int, float)) and math.isfinite(x) and x > 0) else "refused"


def vreal_rows(judge, a, b, units, own_inputs=False, base="S"):
    """[(band, part, ln(d_a / d_b))] on the common directions, with the established V-real rule
    (`direct_stems.add_step4_arm`, `step4_contrast`): a direction where `base` (S) is not judged finite drops for every
    row; a refused answer scores as S; a missing answer leaves the row incomplete. -> (rows, counts)."""
    rows, cnt = [], {"directions": len(units), "base_dropped": 0, "missing": 0, "refused_scored_as_S": 0}
    for u in units:
        s_ = vreal_value(judge, base, u)
        if not isinstance(s_, float):
            cnt["base_dropped"] += 1
            continue
        vals = []
        for t in (a, b):
            v = vreal_value(judge, t, u)
            if v is None:
                cnt["missing"] += 1
                break
            if v == "refused":
                cnt["refused_scored_as_S"] += 1
                v = s_
            vals.append(v)
        if len(vals) < 2:
            continue
        slug = u[0]
        rows.append((PR.VREAL[slug][0], slug if own_inputs else vreal_part_key(slug), math.log(vals[0] / vals[1])))
    cnt["complete"] = cnt["missing"] == 0 and cnt["base_dropped"] == 0
    return rows, cnt


def vreal_ctx():
    """V-real-11's frozen plan, directions and parts (T3's), and the stored S copies."""
    from learn import arm_a_mega53 as A
    from learn import trusted_data_t3 as T3
    from learn import trusted_data_t3_mix as TM
    from learn import verify_tracks as V

    root = V.out_root(argparse.Namespace(out=None, smoke=False))
    plan, drift = TM.load_frozen(root, False)
    dirs, parts, dropped = T3.vreal_dirs(root, plan, False)
    if dropped:
        raise SystemExit(f"V-real members dropped: {dropped}")
    return root, plan, drift, dirs, parts, A.L.menu_S()


def amp_track(slug, info):
    """A V-real part's recorded amp track (the crop's reference.wav), mono."""
    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR

    crop = A.f_part(slug)["crop"] if info["kind"] == "stagef" else pathlib.Path(info["crop"])
    return CR.mono(crop / "reference.wav")


def rung_median_lufs(ids, rung):
    """The median half loudness of rung `rung`'s training inputs (the level a model's input is brought to); D_fix's
    rung-b models read at P2b's (about -13.7 LUFS), not P2a's (about -21.5)."""
    import numpy as np

    v = []
    for i in ids:
        v += [float(z) for z in np.load(input_path(DATA, i, RUNG_KINDS[rung]))["lufs"]]
    return float(np.median(v))


def model_input_lufs(rec):
    """A run's own training inputs' median loudness, by its rung (P2a's rule for rung a)."""
    own = [i for i in rec["train_ids"] if i < REAL_ROW0]
    return rung_median_lufs(own, rec.get("rung", "a"))


def p2a_median_lufs(ids):
    """The median half loudness of P2a's training inputs (the level a P4 input is brought to)."""
    import numpy as np

    v = []
    for i in ids:
        v += [float(z) for z in np.load(input_path(DATA, i, RUNG_KINDS["a"]))["lufs"]]
    return float(np.median(v))


def cmd_p4_predict(args):
    """P4's answers on V-real-11 (zero renders): the ladder model `--name` (P2a; its seeds pooled) reads each part's
    own amp track, brought to the median loudness of its training inputs, on the search half, told the part's class
    and each forced amp; the plain readout on the class's S. Beside it the same answer pulled as D_CC's readout
    (`fit_knob_pull`), and the constant of the model's training labels. -> vreal/answers/<tag>.json."""
    import numpy as np

    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import trusted_data_t3 as T3

    e = require("phase_4")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    root, plan, drift, dirs, parts, ms = vreal_ctx()
    if args.which != "best":
        raise SystemExit("P4 reads the NS-best checkpoints (the declaration)")
    nets, recs = [], []
    for sd in SEEDS:
        if not (out_dir() / "runs" / f"{args.name}-{sd}.json").exists():
            raise SystemExit(f"P4 pools both seeds: {args.name}-{sd} has not run")
        n, r_ = load_run(args.name, sd, args.which)
        nets.append(n)
        recs.append(r_)
    rec = recs[0]
    if rec["rung"] != "a" or any(r_["train_ids"] != rec["train_ids"] for r_ in recs):
        raise SystemExit("P4 reads a P2a model, both seeds on one training set")
    target = p2a_median_lufs(rec["train_ids"])
    med, table = fit_knob_pull(nets, croot, kept, rend, sp, rec)
    const = constant_of(rung_rows(kept, rend, rec["train_ids"]))
    tag = f"P4-{args.name}-{args.which}"
    out = {tag: {}, f"{tag}-pulled": {}, f"{tag}-constant": {}, f"{tag}-dry": {}, f"{tag}-constant-dry": {}}
    dry = ("time effects and spring",)              # the family at S's values (cc_readout's co-primary readout)
    inputs, own, gaps, floor = {}, {}, {}, {}
    for slug, amp, search, _ in dirs:
        cls = PR.VREAL[slug][1]
        if slug not in inputs:
            ref = amp_track(slug, parts[slug])
            inputs[slug] = (ref, DE.inference_gain_db(ref, target))
        ref, g = inputs[slug]
        s8, _, ls, _ = DS.step4_half(ref, ref, search, g)
        floor.setdefault(slug, {})[search] = float(np.mean(np.all(s8 == 0, axis=0)))   # frames all at the grid floor
        x, c = DS.model_input(s8, s8, ls, ls, search, amp, cls, "Dstem")
        r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
        own[f"{slug}|{search}"] = {"amp": r["amp"], "p": r["amp_p"]}
        sel, S = ms[amp][cls]
        key = f"{slug}|{amp}"
        b, gap = DS.cell_b(table, (amp, cls), F.cell_masks(amp)[0])
        if gap:
            gaps[f"{amp}|{cls}"] = gap
        out[tag].setdefault(key, {})[search] = {"select": sel, "settings": LO.sdict(
            F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"]))}
        out[f"{tag}-pulled"].setdefault(key, {})[search] = {"select": sel, "settings": LO.sdict(
            F.answer_settings(amp, S, DS.pull(r["a2"], med[(amp, cls)], b), r["sw_p"], r["mics"]))}
        out[f"{tag}-constant"].setdefault(key, {})[ANY_HALF] = {"select": sel, "settings": LO.sdict(
            T3.constant_full(amp, S, const[(amp, cls)]))}
        out[f"{tag}-dry"].setdefault(key, {})[search] = {"select": sel, "settings": LO.sdict(
            F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"], at_S=dry))}
        cst = const[(amp, cls)]
        out[f"{tag}-constant-dry"].setdefault(key, {})[ANY_HALF] = {"select": sel, "settings": LO.sdict(
            F.answer_settings(amp, S, cst["cont"], [None if v is None else (1.0 if v else 0.0) for v in cst["sw"]],
                              cst["mics"], at_S=dry))}
    for t, a in out.items():
        save(out_dir() / VREAL_DIR / "answers" / f"{t}.json", {
            "plan": PLAN, "ledger": f"{LEDGER_ID} phase_4", "tag": t, "model": args.name, "which": args.which,
            "seeds": [r_["seed"] for r_ in recs], "model_sha256": [r_["model_sha256"]["best"] for r_ in recs],
            "input": "the part's own amp track (crop reference.wav)", "input_lufs": target,
            "gains_db": {k: v[1] for k, v in inputs.items()}, "own_amp": own, "pull_gaps": gaps,
            "floor_frame_share": floor, "answers": a, "drift": drift, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"P4 PREDICT DONE: {len(dirs)} directions; inputs at {target:.2f} LUFS; tags {list(out)}")


def cmd_vreal_sc(args):
    """5B.1c's answers on V-real-11 (zero renders): P4's own answers (P2a, both seeds, NS-best, the part's own amp
    track) re-centred on S as 5B.1b's P2a-Sc (`sc_cont`: S's sounding continuous controls at S's value plus P2a's
    deviation from its labels' constant, clipped; elsewhere P2a's value; switches and mics at S's). The model is
    re-run on the same inputs; the stored P4 answers are not rewritten. -> vreal/answers/P4-P2a-best-sc.json."""
    import numpy as np

    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO

    e = require("phase_5b1c")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    root, plan, drift, dirs, parts, ms = vreal_ctx()
    nets, recs = [], []
    for sd in SEEDS:
        n, r_ = load_run("P2a", sd, "best")
        nets.append(n)
        recs.append(r_)
    p4 = json.loads((out_dir() / VREAL_DIR / "answers" / "P4-P2a-best.json").read_text())
    if p4["model_sha256"] != [r_["model_sha256"]["best"] for r_ in recs]:
        raise SystemExit("P4's stored answers came from other models")
    target = p2a_median_lufs(recs[0]["train_ids"])
    const = constant_of(rung_rows(kept, rend, recs[0]["train_ids"]))
    out, inputs, same = {}, {}, []
    for slug, amp, search, _ in dirs:
        cls = PR.VREAL[slug][1]
        if slug not in inputs:
            ref = amp_track(slug, parts[slug])
            inputs[slug] = (ref, DE.inference_gain_db(ref, target))
        ref, g = inputs[slug]
        s8, _, ls, _ = DS.step4_half(ref, ref, search, g)
        x, c = DS.model_input(s8, s8, ls, ls, search, amp, cls, "Dstem")
        r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
        sel, S = ms[amp][cls]
        key = f"{slug}|{amp}"
        plain = LO.sdict(F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"]))
        same.append(plain == p4["answers"][key][search]["settings"])
        _, _, s_sw, s_swm, s_k, s_km, _ = F.encode(dict(S), amp)
        sw = [float(v) if m else None for v, m in zip(s_sw, s_swm)]
        mics = [int(v) if m else None for v, m in zip(s_k, s_km)]
        out.setdefault(key, {})[search] = {"select": sel, "settings": LO.sdict(F.answer_settings(
            amp, S, sc_cont(dict(S), amp, r["a2"], const[(amp, cls)]["cont"]), sw, mics))}
    save(out_dir() / VREAL_DIR / "answers" / "P4-P2a-best-sc.json", {
        "plan": PLAN, "ledger": f"{LEDGER_ID} phase_5b1c", "tag": "P4-P2a-best-sc", "model": "P2a", "which": "best",
        "seeds": [r_["seed"] for r_ in recs], "model_sha256": [r_["model_sha256"]["best"] for r_ in recs],
        "input_lufs": target, "plain_reproduces_p4": f"{sum(same)} of {len(same)}", "answers": out,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"VREAL-SC DONE: {len(dirs)} directions; the plain readout reproduces P4's stored answers on {sum(same)} "
          f"of {len(same)}")


def cmd_vreal_comparators(args):
    """S and S' (P5's crunch picks without V-real's parts) as V-real answers (zero renders): S on every part, S' on
    the crunch parts, each on its amp's live menu entry."""
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    require("phase_4")
    root, plan, drift, dirs, parts, ms = vreal_ctx()
    p5 = json.loads((out_dir() / "p5.json").read_text())["variants"]["without V-real's parts"]["picks"]
    rr = K.Renderer()
    try:
        menu = rr.menu()
    finally:
        rr.close()
    out = {"S": {}, "S-prime": {}}
    for slug, amp, _, _ in dirs:
        cls = PR.VREAL[slug][1]
        sel, S = ms[amp][cls]
        out["S"][f"{slug}|{amp}"] = {ANY_HALF: {"select": sel, "settings": LO.sdict(S)}}
        pick = p5[cls]["per_amp"][amp]
        if pick["changed"]:
            sel2, S2 = menu[amp][pick["picked"]]
            out["S-prime"][f"{slug}|{amp}"] = {ANY_HALF: {"select": sel2, "settings": LO.sdict(S2),
                                                          "preset": pick["picked"]}}
    for t, a in out.items():
        save(out_dir() / VREAL_DIR / "answers" / f"{t}.json", {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_4",
                                                              "tag": t, "answers": a,
                                                              "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"COMPARATORS DONE: S on {len(out['S'])} groups, S' on {len(out['S-prime'])}")


def cmd_vreal_render(args):
    """One shard of V-real (part, amp) groups for the answer sets `--names`: every answer, comparators included,
    through the part's measure DI in its own process primed with the same setting (step 33), judged against the
    part's amp track at its judge lag on both halves. isolate=True; at most 3 render processes; the 31 GB guard.
    -> vreal/judge/<tag>/<slug>|<amp>.json (a done group is kept)."""
    require("phase_4")
    tags = args.names.split(",")
    bad = [t for t in tags if t not in P4_TAGS]
    if bad:
        raise SystemExit(f"phase 4 renders only its declared tags {P4_TAGS}; not {bad}")
    if "P4-P2a-best-sc" in tags:
        require("phase_5b1c")
    vreal_render(tags, args.shard)


def vreal_render(tags, shard, recheck=None):
    """`vreal-render`'s loop on V-real (part, amp) groups of shard (k, n) for answer sets `tags`, every refusal its
    caller's. `recheck` {tag: stored tag}: each group's fresh render hashes recorded beside the stored tag's
    (`recheck_sha256`, `identical`), the stored group required before rendering."""
    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import trusted_data as T
    from learn import trusted_data_t3 as T3

    recheck = recheck or {}
    root, plan, drift, dirs, parts, ms = vreal_ctx()
    groups = sorted({(s_, a) for s_, a, _, _ in dirs})
    k, n = shard
    mine = [g for j, g in enumerate(groups) if j % n == k]
    LO._wait_cap()
    rr = CB.new_renderer()
    try:
        menu = rr.menu()
    finally:
        rr.close()
    for amp, by_cls in ms.items():                 # the live S must equal the stored copy (cc_readout's check)
        for cls, (_, S) in by_cls.items():
            if K.key(dict(menu[amp][K.START[cls][amp]][1])) != K.key(S):
                raise SystemExit(f"{amp} {cls}: the live S differs from the stored copy")
    renders, differ = 0, []
    for tag in tags:
        af = out_dir() / VREAL_DIR / "answers" / f"{tag}.json"
        ans = json.loads(af.read_text())["answers"]
        asha = answers_sha(ans)
        for slug, amp in mine:
            key = f"{slug}|{amp}"
            if key not in ans:
                continue
            gp = out_dir() / VREAL_DIR / "judge" / tag / f"{key}.json"
            if gp.exists():
                if json.loads(gp.read_text()).get("answers_sha256") != asha:
                    raise SystemExit(f"{gp}: rendered from other answers; move vreal/judge/{tag} aside first")
                continue
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            old = None
            if tag in recheck:
                op = out_dir() / VREAL_DIR / "judge" / recheck[tag] / f"{key}.json"
                if not op.exists():
                    raise SystemExit(f"{op}: no stored {recheck[tag]} render to check {tag} against")
                old = json.loads(op.read_text())["render_sha256"]
            info = parts[slug]
            ctx = (A.group_ctx(menu, ms, "F", slug, amp) if info["kind"] == "stagef"
                   else T3.t3_group_ctx(menu, ms, info, amp))
            rec = {"slug": slug, "amp": amp, "tag": tag, "answers_sha256": asha, "judge": {}, "render_sha256": {}}
            for search, a in sorted(ans[key].items()):
                st = LO.tdict(a["settings"])
                y = AM.fresh_render(CB.new_renderer, ctx["di32"], a["select"], st, st)
                renders += 2
                rec["judge"][search] = K.judge(ctx["ref"], y, ctx["di"], ctx["part"]["judge_lag"])
                rec["render_sha256"][search] = AM.audio_sha(y)
            rec["renders"] = 2 * len(ans[key])
            if old is not None:
                rec.update(recheck_of=recheck[tag], recheck_sha256=old, identical=old == rec["render_sha256"])
                if not rec["identical"]:
                    differ.append(f"{tag} {key}")
            save(gp, rec)
        print(f"{tag}: shard {k}/{n} done; renders so far {renders}", flush=True)
    if differ:
        print(f"RECHECK: {len(differ)} groups' renders differ from the stored ones: {differ}", flush=True)
    print(f"VREAL-RENDER DONE {k}/{n}: {renders} renders")


FLOOR_SIDE_ROW = 0.20
S_CONTROL_N = 60                    # stage F's 10 parts x 3 amps x 2 halves


def s_positive_control(sj):
    """The fresh S renders against the label table's stored `flat` distances (stage F's parts): |ln ratio| per
    (part, amp, half). It checks the render path and sizes the render-order effect (step 33) on V-real."""
    from learn import knob_ceiling as K

    vals = []
    for key, rec in sj.items():
        slug, amp = key.split("|")
        p = K.HOME / "learn/label-table" / slug / "menu.json"
        if slug in PR.IN_GROUP_S or not p.exists():      # T3's own crop: its label-table clip is another window
            continue
        st = json.loads(p.read_text()).get(amp, {})
        cls = PR.VREAL[slug][1]
        stored = (st.get(K.START[cls][amp]) or {}).get("flat") or {}
        for h in ("A", "B"):
            x, y = (rec.get(ANY_HALF) or {}).get(h), stored.get(h)
            ok = [z is not None and math.isfinite(z) and z > 0 for z in (x, y)]
            if all(ok):
                vals.append(abs(math.log(x / y)))
            elif any(ok):                                 # one side finite: a miss (`local_objective.deviation`)
                vals.append(math.inf)
    vals.sort()
    return {"n": len(vals), "max_abs_log": vals[-1] if vals else None,
            "median_abs_log": vals[len(vals) // 2] if vals else None, "tolerance": K.REPEAT_TOL,
            "within_tolerance": sum(v <= K.REPEAT_TOL for v in vals),
            "passes": bool(vals) and vals[-1] <= K.REPEAT_TOL}


P4_TAGS = ("P4-P2a-best", "P4-P2a-best-pulled", "P4-P2a-best-constant", "S", "S-prime", "P4-P2a-best-dry",
           "P4-P2a-best-constant-dry", "P4-P2a-best-sc")             # the last: 5B.1c (ledger phase_5b1c)


def answers_sha(ans):
    import hashlib

    return hashlib.sha256(json.dumps(ans, sort_keys=True).encode()).hexdigest()


def cmd_vreal_report(args):
    """Phase 4's rows: for each pair in `--pairs` ("a:b,a:b"), band-weighted ln(d_a / d_b) on the held half per
    direction, 90% band-clustered t (7 bands), per class, part-weighted, V-real-10 and leave-one-band-out beside.
    Wickerman ElecGtr2 and 3 count as one part unless both answers read their own amp tracks (`--own-inputs`)."""
    e = require("phase_4")
    root, plan, drift, dirs, parts, ms = vreal_ctx()
    v10 = set(plan["vreal"]["v_real_10"])
    judge = {}
    tags = {t for pair in args.pairs.split(",") for t in pair.split(":")} | {"S"}
    for t in tags:
        d = out_dir() / VREAL_DIR / "judge" / t
        judge[t] = {}
        for p in d.glob("*.json"):
            r = json.loads(p.read_text())
            judge[t][f"{r['slug']}|{r['amp']}"] = r["judge"]
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_4", "rows": {}}
    for t in tags:                                  # every judge record must come from today's answers
        af = out_dir() / VREAL_DIR / "answers" / f"{t}.json"
        asha = answers_sha(json.loads(af.read_text())["answers"])
        stale = [p.name for p in (out_dir() / VREAL_DIR / "judge" / t).glob("*.json")
                 if json.loads(p.read_text()).get("answers_sha256") != asha]
        if stale:
            raise SystemExit(f"{t}: {len(stale)} judge records come from other answers")
    p4 = out_dir() / VREAL_DIR / "answers" / "P4-P2a-best.json"
    floor = json.loads(p4.read_text()).get("floor_frame_share", {}) if p4.exists() else {}
    quiet_inputs = sorted(sl for sl, v in floor.items() if max(v.values()) > FLOOR_SIDE_ROW)
    out["side_row_without"] = {"rule": f"P4 inputs with more than {FLOOR_SIDE_ROW:.0%} of frames at the grid floor in "
                                       "either half (declared before the read)", "parts": quiet_inputs}
    out["positive_control_S"] = s_positive_control(judge.get("S", {}))
    pc0 = out["positive_control_S"]
    if not pc0["passes"] or pc0["n"] != S_CONTROL_N:
        raise SystemExit(f"the S positive control fails ({pc0}): no rows are read")
    for pair in args.pairs.split(","):
        a, b = pair.split(":")
        rows, cnt = vreal_rows(judge, a, b, dirs, own_inputs=args.own_inputs)
        res = {"all": clustered(rows), **cnt}
        side = [r for r in rows if not any(m in quiet_inputs for m in part_members(r[1]))]
        res["without_quiet_inputs"] = clustered(side) if quiet_inputs else None
        for cls in ("clean", "crunch"):
            res[cls] = clustered([r for r in rows if all(PR.VREAL[m][1] == cls for m in part_members(r[1]))])
        res["v_real_10"] = clustered([r for r in rows if all(m in v10 for m in part_members(r[1]))])
        out["rows"][f"{a} - {b}"] = res
        c = res["all"]
        iv = "" if c["lo90"] is None else f" [{c['lo90']:+.4f}, {c['hi90']:+.4f}]"
        print(f"{a} - {b}: {c['mean']:+.4f}{iv} ({c['clusters']} bands, {c['clusters_negative']} better; part-weighted "
              f"{c['part_weighted']:+.4f}, {c['parts_negative']} of {c['parts']} parts better; {len(rows)} of "
              f"{len(dirs)} directions; {'complete' if cnt['complete'] else 'INCOMPLETE'}, missing {cnt['missing']}, "
              f"S dropped {cnt['base_dropped']}, refused as S {cnt['refused_scored_as_S']})"
              if c["mean"] is not None else f"{a} - {b}: no rows ({cnt})")
        for cls in ("clean", "crunch"):
            z = res[cls]
            if z["mean"] is not None:
                print(f"    {cls}: {z['mean']:+.4f} ({z['clusters']} bands, {z['clusters_negative']} better)")
    pc = out["positive_control_S"]
    print(f"positive control: the fresh S against the label table's stored flat distance on {pc['n']} (part, amp, "
          f"half): max |ln ratio| {pc['max_abs_log']}, median {pc['median_abs_log']}")
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    rp = out_dir() / VREAL_DIR / f"report-{args.label or 'p4'}.json"
    if rp.exists():
        raise SystemExit(f"{rp.name} exists (a V-real report is never overwritten): name a new report with --label")
    save(rp, out)
    print("VREAL-REPORT DONE")


# --- main ------------------------------------------------------------------------------------------------------------

PANEL_DIR = "panel"                  # 5D's real-amp test panel (v1): PF/panel/
PANEL_PAIRS = REPO / "docs" / "panel-v1-pairs.json"
PANEL_SEED = 20261101
PANEL_WINDOWS = 3                    # windows per DI (shared by its amp tracks)
PANEL_GAP_S = 10.0                   # at least this much between a DI's windows
PANEL_WIDE_S = 1.5                   # the whole-track lag's search (Blue Manic's amp tracks run up to 1.2 s long)
PANEL_FAR = 240                      # a DI-to-track lag above this (5 ms at 48 kHz) flags a far mic
PANEL_LAG_TOL = 72                   # a window's lag this far from its track's is out (5C's tolerance)
PANEL_DI_NOISE_OK = {"hum"}         # 5D's amendment: a DI's hum flag passes (the amp heard it too, so the comparison
                                    # stays fair; for the test panel only)
PANEL_SILENT_DB, PANEL_PLAY_DB = 40.0, 20.0
PANEL_BLEED_MAX_DB = -18.35          # the largest bleed residual among BKS's reamps (22 of 40 measured; 2026-11-01):
                                     # a panel unit above it is "high bleed" (the residual holds amp and room tails too)   # the bleed residual's DI frames: silent below the window's DI peak
                                              # by this much, playing within this much of it


def panel_pairs():
    """5D's (DI, amp tracks) pairs, fixed with the declaration (`docs/panel-v1-pairs.json`, paths under ~). ->
    [{source, band, song, part, di, amps}]."""
    import os

    d = json.loads(PANEL_PAIRS.read_text())
    return [{"source": src["source"], "band": src["band"], "song": src.get("song"), **pr,
             "di": {**pr["di"], "path": os.path.expanduser(pr["di"]["path"])},
             "amps": [{**a, "path": os.path.expanduser(a["path"])} for a in pr["amps"]]}
            for src in d["sources"] for pr in src["pairs"]]


def panel_di_flagged(row, track):
    """The pool's DI screens (`clean_di.section_flags`) less the flags PANEL_DI_NOISE_OK lets through."""
    from learn import clean_di as CD

    flags, _ = CD.section_flags(row, track or {})
    return bool(set(flags) - PANEL_DI_NOISE_OK)


def panel_windows(rows, track, key, k=PANEL_WINDOWS, gap=PANEL_GAP_S, min_start_s=1.0):
    """5D's windows for one DI: its 10-s grid sections that pass the pool's activity rule and screens (as
    `goat_window`, with DI hum and slight hiss let through: `panel_di_flagged`), in a seeded order (PANEL_SEED with `key`), kept greedily while each starts at least `gap` s
    after the end of every kept one; up to k. -> sorted starts."""
    import random

    from learn import clean_di as CD
    from learn import pretrain_set as PS

    ok = [r["start_s"] for r in rows if r["passes_activity"] and r["start_s"] >= min_start_s
          and not (r.get("clip_runs") or r.get("dropouts") or r.get("hard_cuts"))
          and not panel_di_flagged(r, track)]
    order = sorted(ok)
    random.Random(f"{PANEL_SEED}|{key}").shuffle(order)
    kept = []
    for st in order:
        if all(abs(st - q) >= PS.SEC_S + gap for q in kept):
            kept.append(st)
        if len(kept) == k:
            break
    return sorted(kept)


def panel_bleed_db(amp, di, sr):
    """5D's bleed residual on one aligned window (zero renders): the amp track's level on frames where its DI is
    silent (PANEL_SILENT_DB under the window's DI peak) against its level where the DI plays (within PANEL_PLAY_DB
    of it), in dB; None with fewer than 4 frames of either."""
    import numpy as np

    from learn import clean_di as CD

    dd, ad = CD.frame_db(di), CD.frame_db(amp)
    n = min(len(dd), len(ad))
    dd, ad = dd[:n], ad[:n]
    top = float(np.max(dd)) if n else -300.0
    silent, play = dd < top - PANEL_SILENT_DB, dd > top - PANEL_PLAY_DB
    if silent.sum() < 4 or play.sum() < 4:
        return None
    p = lambda m: 10 * np.log10(np.mean(10 ** (ad[m] / 10)) + 1e-30)
    return float(p(silent) - p(play))


def panel_cut(di, amp, lo, n, track_lag):
    """5D's aligned windows: the DI's n samples from lo and the amp track's from lo + track_lag (amp[t] ~ DI[t - lag],
    `estimate_lag`'s convention), so the two line up; empty when the amp window would start before 0."""
    import numpy as np

    a0 = lo + track_lag
    return di[lo:lo + n], (amp[a0:a0 + n] if a0 >= 0 else np.zeros(0))


def panel_folds(dis_by_band):
    """5D's folds: each new DI a fold, seeded (PANEL_SEED), dealt round-robin within each band from a running start
    so the folds stay balanced across bands. -> {di: fold}."""
    import random

    out, at = {}, 0
    for band in sorted(dis_by_band):
        dis = sorted(dis_by_band[band])
        random.Random(f"{PANEL_SEED}|folds|{band}").shuffle(dis)
        for d in dis:
            out[d] = at % REAL_FOLDS
            at += 1
    return out


def file_key(path):
    """A file's size and the sha256 of its first MiB: a cheap identity that survives copies and renames."""
    import hashlib

    path = pathlib.Path(path)
    with open(path, "rb") as fh:
        return path.stat().st_size, hashlib.sha256(fh.read(1 << 20)).hexdigest()


def panel_leaks(pairs, pool_paths, bands_out):
    """5D's leakage guard: panel files that are, by name or content (`file_key`), any pool DI (training's
    inventory, every session), and panel bands among `bands_out` (V-real's, training's). -> [problems]."""
    import os

    files = {p["di"]["path"] for p in pairs} | {a["path"] for p in pairs for a in p["amps"]}
    keys = {file_key(f): f for f in files}
    bad = [f for f in files if os.path.realpath(f) in {os.path.realpath(q) for q in pool_paths}]
    for q in pool_paths:
        if os.path.exists(q) and file_key(q) in keys:
            bad.append(f"{keys[file_key(q)]} = pool file {q}")
    bad += [f"band {p['band']} is out" for p in pairs if p["band"] in bands_out]
    return sorted(set(bad))


def panel_units():
    """5D's panel units (panel/units.json, from `panel-sections`)."""
    return json.loads((out_dir() / PANEL_DIR / "units.json").read_text())["units"]


def panel_heard(units, verdicts):
    """5D's ear gate: the units the listener answered "amp" ("a real amp, the guitar alone"); every other verdict,
    "not sure" included, is out. -> (passed set, unheard list)."""
    ok = {u for u in units if (verdicts.get(u) or {}).get("verdict") == "amp"}
    return ok, [u for u in units if u not in verdicts]


PANEL_DI_LIKE = {"Guitar-TECHS P3", "Dahka Band"}   # 5D's ear check: their amp tracks measure as near copies of the
                                                    # DI (1/3-octave difference SD about 3 dB), out whatever the verdict


def panel_read_units():
    """5D's units for reads and renders: every panel unit heard, and only those that passed (the re-check's verdict,
    panel/recheck.json, replacing the first for the units it covers); bands in PANEL_DI_LIKE out; refuses while any
    unit is unheard."""
    units = panel_units()
    ep = out_dir() / PANEL_DIR / "ear.json"
    if not ep.exists():
        raise SystemExit("panel units not yet heard: the ear page comes before any panel render")
    verdicts = json.loads(ep.read_text())["verdicts"]
    rp = out_dir() / PANEL_DIR / "recheck.json"
    if rp.exists():
        verdicts = {**verdicts, **json.loads(rp.read_text())["verdicts"]}
    ok, missing = panel_heard([u["unit"] for u in units], verdicts)
    if missing:
        raise SystemExit(f"{len(missing)} panel units not yet heard")
    return [u for u in units if u["unit"] in ok and u["band"] not in PANEL_DI_LIKE]


def cmd_panel_sections(args):
    """5D's data (zero renders): per DI of the fixed pairs (`panel_pairs`), the pool's DI measures and up to
    PANEL_WINDOWS windows (`panel_windows`; Guitar-TECHS P3's excerpts one each), shared by its amp tracks. Per amp
    track, its DI-to-track lag over the whole track (`estimate_lag`, the DI as the render, ±PANEL_WIDE_S) and per
    window, with that as the hint; a window more than PANEL_LAG_TOL from its track's lag is out; a track lag above
    PANEL_FAR flags a far mic. The amp window is cut at the window plus the track lag (so the judge's residual lag is
    small), checked for clipping, classed against its DI (`classify` on `gainmeasure`; high gain out) and given its
    bleed residual (`panel_bleed_db`). Everything at 48 kHz. -> panel/sections/*.wav, panel/units.json."""
    import sys

    import numpy as np
    import soundfile as sf

    from analysis.aligned import estimate_lag
    from learn import clean_di as CD
    from learn import pretrain_set as PS

    require("phase_5d")
    from learn import cc_build as CB

    inv = CB.cc_inventory()
    pool_bands = {r.get("band") for r in inv.values()}
    leaks = panel_leaks(panel_pairs(), [r["path"] for r in inv.values() if r.get("path")], VREAL_BANDS | pool_bands)
    if leaks:
        raise SystemExit(f"panel leakage: {leaks}")
    sys.path.insert(0, str(PS.HOME / "references/datasets-set3/_tools"))
    import classify as C
    import gainmeasure as GM

    pd = out_dir() / PANEL_DIR
    sec = pd / "sections"
    sec.mkdir(parents=True, exist_ok=True)
    n = int(round((PS.SEC_S + PS.TRIM_S) * PS.SR))
    trim = int(PS.TRIM_S * PS.SR)
    units, dis, notes = [], {}, []

    def read(path):
        x, sr = sf.read(path, dtype="float64", always_2d=True)
        return CD.resample(x.mean(1), sr, PS.SR), sr

    for pr in panel_pairs():
        band, key = pr["band"], f"{pr['band']}|{pr['part']}"
        x, sr = read(pr["di"]["path"])
        f, fs = CD.floor_spectrum(x)
        votes = {k: [v] for k, v in ({mm: CD.line_count(f, fs, mm) for mm in CD.MAINS} if fs is not None
                                     else {}).items()}
        track, rows = CD.measure_di(x, PS.SR, CD.session_mains(votes))
        k = 1 if pr["source"].startswith("Guitar-TECHS") else PANEL_WINDOWS
        starts = panel_windows(rows, track, key, k=k)
        row_at = {r["start_s"]: r for r in rows}
        if track["near_fs"] or not starts:
            notes.append({"di": key, "out": "DI near full scale" if track["near_fs"] else "no window"})
            print(f"{key}: {notes[-1]['out']}", flush=True)
            continue
        di_id = f"panel/{band}/{pr['part']}"
        for a in pr["amps"]:
            y, _ = read(a["path"])
            tname = pathlib.Path(a["path"]).name
            try:
                tlag = int(estimate_lag(y, [x], max_lag_s=PANEL_WIDE_S))
            except ValueError as err:
                notes.append({"di": key, "track": tname, "out": f"no track lag: {err}"})
                continue
            for st in starts:
                lo = int(round((st - PS.TRIM_S) * PS.SR))
                dsec, asec = panel_cut(x, y, lo, n, tlag)
                u = f"{di_id}@{st:.1f}#{tname}"
                if len(dsec) < n or len(asec) < n:
                    notes.append({"unit": u, "out": "window runs past an end"})
                    continue
                try:
                    wlag = int(estimate_lag(asec, [dsec], hint=0)) + tlag
                except ValueError as err:
                    notes.append({"unit": u, "out": f"no window lag: {err}"})
                    continue
                rec = {"unit": u, "out": None}
                if abs(wlag - tlag) > PANEL_LAG_TOL:
                    rec["out"] = f"window lag {wlag} off the track's {tlag}"
                elif len(CD.clip_runs(asec, peak=float(np.max(np.abs(y))))):
                    rec["out"] = "the amp track clips in the window"
                gm = GM.measures(np.asarray(asec[trim:], np.float64), np.asarray(dsec[trim:], np.float64), PS.SR)
                cls = C.classify(gm)[0] if gm else None
                if rec["out"] is None and cls not in ("clean", "crunch"):
                    rec["out"] = f"class {cls}"
                if rec["out"]:
                    notes.append({**rec, "class": cls, "track_lag": tlag, "window_lag": wlag})
                    continue
                stem = u.replace("/", "__").replace("#", "__").replace(" ", "_")
                dp, ap = sec / f"{stem}.di.wav", sec / f"{stem}.amp.wav"
                if not dp.exists():
                    sf.write(dp, dsec.astype(np.float32), PS.SR, subtype="FLOAT")
                sf.write(ap, asec.astype(np.float32), PS.SR, subtype="FLOAT")
                units.append({"unit": u, "section": f"{di_id}@{st:.1f}", "track": ap.name, "rig": f"{di_id}#{tname}",
                              "set": "panel", "di": di_id, "band": band, "source": pr["source"], "cls": cls,
                              "sd": str(sec), "start_s": PS.TRIM_S, "di_path": str(dp), "window_s": st,
                              "track_lag": tlag, "window_lag": wlag, "far": abs(tlag) > PANEL_FAR,
                              "bleed_db": panel_bleed_db(asec[trim:], dsec[trim:], PS.SR), "gain_measures": gm,
                              "di_flags": CD.section_flags(row_at[st], track)[0],
                              "di_file": pr["di"]["path"], "amp_file": a["path"], "mic": a.get("mic")})
                dis.setdefault(band, set()).add(di_id)
        print(f"{key}: windows {starts}; units so far {len(units)}", flush=True)
    fold = panel_folds(dis)
    for u in units:
        u["fold"] = fold[u["di"]]
    save(pd / "units.json", {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_5d", "pairs": str(PANEL_PAIRS),
                             "units": units, "out": notes, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    cnt = {}
    for u in units:
        cnt.setdefault(u["band"], {}).setdefault(u["cls"], set()).add(u["di"])
    print("PANEL-SECTIONS DONE: " + "; ".join(
        f"{b}: " + ", ".join(f"{c} {len(v)} DIs/{sum(1 for u in units if u['band'] == b and u['cls'] == c)} units"
                             for c, v in sorted(cs.items())) for b, cs in sorted(cnt.items())))


PANEL_LATENCY = 52                   # the plugin's render latency (samples), as `aligned_distance`'s default


def panel_halves(units):
    """5D's search halves: A and B alternating over each DI's units in sorted order (5B.2's per-DI rule)."""
    out, by = {}, {}
    for u in sorted(units, key=lambda p_: p_["unit"]):
        j = by.setdefault(u["di"], 0)
        out[u["unit"]] = "AB"[j % 2]
        by[u["di"]] += 1
    return out


def panel_fname(key):
    return key.replace("/", "__").replace(" ", "_")


def cmd_panel_lags(args):
    """5D's lags (one shard of the passed units): S (the class's, on each amp) rendered fresh, the judge lag pooled
    over the three (`estimate_lag`, searched around the window's residual lag less the plugin's latency), the unit out
    if the two differ by more than PANEL_LAG_TOL; S's judges and shas stored. -> panel/lags/<unit>.json."""
    import numpy as np

    from analysis.aligned import estimate_lag
    from learn import arm_a_levers as L
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    require("phase_5d")
    units = sorted(panel_read_units(), key=lambda p_: p_["unit"])
    k, n = args.shard
    mine = [p_ for j, p_ in enumerate(units) if j % n == k]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    ms = L.menu_S()
    LO._wait_cap()
    ldir = out_dir() / PANEL_DIR / "lags"
    renders = 0
    for prt in mine:
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        lp = ldir / f"{panel_fname(prt['unit'])}.json"
        if lp.exists():
            continue
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        ys = {}
        for a in AMPS3:
            sel, S = ms[a][prt["cls"]]
            xs = LO.tdict(LO.sdict(S))
            ys[a] = np.asarray(AM.fresh_render(CB.new_renderer, di32, sel, xs, xs), np.float64)[trim[0]:trim[1]]
            renders += 2
        expect = prt["window_lag"] - prt["track_lag"] - PANEL_LATENCY
        try:
            lag, status = int(estimate_lag(ref, list(ys.values()), hint=expect)), "ok"
        except ValueError as err:
            lag, status = None, f"no lag: {err}"
        if lag is not None and abs(lag - expect) > PANEL_LAG_TOL:
            status = f"judge lag {lag} off the DI-to-track estimate {expect}"
        save(lp, {"unit": prt["unit"], "lag": lag, "expect": expect, "status": status, "phase": "phase_5d",
                  "s": {a: {"judge": None if lag is None else K.judge(ref, ys[a], di, lag),
                            "render_sha256": AM.audio_sha(ys[a])} for a in AMPS3}})
        print(f"{prt['unit'][-60:]}: lag {lag} (expect {expect}) {status}; renders so far {renders}", flush=True)
    print(f"PANEL-LAGS DONE {k}/{n}: {renders} renders")


def panel_lagged_units():
    """5D's units with a usable lag (panel/lags status "ok"); refuses while any passed unit has no lag record."""
    units = panel_read_units()
    ldir = out_dir() / PANEL_DIR / "lags"
    recs = {}
    for p_ in units:
        lp = ldir / f"{panel_fname(p_['unit'])}.json"
        if not lp.exists():
            raise SystemExit(f"{p_['unit']}: no lag yet (panel-lags first)")
        recs[p_["unit"]] = json.loads(lp.read_text())
    return [dict(p_, lag=recs[p_["unit"]]["lag"]) for p_ in units if recs[p_["unit"]]["status"] == "ok"], recs


def cmd_panel_centres(args):
    """5D's centres and S (zero renders), each new unit by its fold, as F37's: RcBG_k on exactly model k's training
    lists, Rcs2_k on model k's BKS list, RcG on every GOAT label (`centre_records`), by Rc's rule on the class's S;
    S itself. Every answer on each of the three amps. -> panel/answers/{RcBG,Rcs2,RcG,S}.json."""
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    require("phase_5d")
    units, _ = panel_lagged_units()
    brecs, by_unit, folds = real_labels(2)
    grecs, gunits, _ = goat_labels()
    ms = A_menu_S()
    src = {}
    for k in range(REAL_FOLDS):
        src[k] = centre_records(brecs, by_unit, folds, grecs, gunits, k)
        src[k]["Rcs2"] = fold_records(brecs, by_unit, folds, k)

    def cls_of(r):
        return (by_unit[r["unit"]] if r["unit"] in by_unit else gunits[r["unit"]])["cls"]

    out = {t: {} for t in ("RcBG", "Rcs2", "RcG", "S")}
    used = {t: {} for t in ("RcBG", "Rcs2", "RcG")}
    for prt in units:
        for amp in AMPS3:
            sel, S = ms[amp][prt["cls"]]
            key = real_key(prt, amp)
            out["S"][key] = {ANY_HALF: {"select": sel, "settings": LO.sdict(S)}}
            for t in ("RcBG", "Rcs2", "RcG"):
                labels = [LO.tdict(r["label"]) for r in src[prt["fold"]][t]
                          if r["amp"] == amp and cls_of(r) == prt["cls"]]
                out[t][key] = {ANY_HALF: {"select": sel, "settings": LO.sdict(rc_setting(K.space(amp, S), S, labels))}}
                used[t][key] = len(labels)
    for t, a in out.items():
        save(out_dir() / PANEL_DIR / "answers" / f"{t}.json", {
            "plan": PLAN, "ledger": f"{LEDGER_ID} phase_5d", "tag": t, "labels_used": used.get(t), "answers": a,
            "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"PANEL CENTRES DONE: {len(units)} units x {len(AMPS3)} amps; " + "; ".join(
        f"{t} labels {min(v.values())}-{max(v.values())}" for t, v in used.items()))


PANEL_MODELS = {"P2a-goat": "P2a-goat{k}", "P2a-reals2": "P2a-real{k}s2"}


def cmd_panel_predict(args):
    """5D's model answers (torch, zero renders): each new unit read by its fold's runs (both seeds pooled, at their
    training inputs' median loudness, per search half) on each of the three amps, as `goat_predict`.
    -> panel/answers/<name>.json."""
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO

    require("phase_5d")
    if args.names not in PANEL_MODELS:
        raise SystemExit(f"--names one of {sorted(PANEL_MODELS)}")
    units, _ = panel_lagged_units()
    models = {}
    for k in sorted({p_["fold"] for p_ in units}):
        nets, recs = zip(*(load_run(PANEL_MODELS[args.names].format(k=k), sd, "best") for sd in SEEDS))
        own = [i for i in recs[0]["train_ids"] if i < REAL_ROW0]
        models[k] = (list(nets), [r_["model_sha256"]["best"] for r_ in recs], p2a_median_lufs(own))
    ms = A_menu_S()
    out = {}
    for prt in units:
        nets, _, target = models[prt["fold"]]
        ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        g = DE.inference_gain_db(ref, target)
        for search in ("A", "B"):
            s8, _, ls, _ = DS.step4_half(ref, ref, search, g)
            for amp in AMPS3:
                sel, S = ms[amp][prt["cls"]]
                x, c = DS.model_input(s8, s8, ls, ls, search, amp, prt["cls"], "Dstem")
                r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
                st = F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"])
                out.setdefault(real_key(prt, amp), {})[search] = {"select": sel, "settings": LO.sdict(st)}
    save(out_dir() / PANEL_DIR / "answers" / f"{args.names}.json", {
        "plan": PLAN, "ledger": f"{LEDGER_ID} phase_5d", "tag": args.names,
        "models": {k: {"sha256": m[1], "input_lufs": m[2]} for k, m in models.items()}, "answers": out,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"PANEL PREDICT DONE: {args.names} on {len(units)} units")


def cmd_panel_render(args):
    """5D's read renders (one shard): each answer of `--names` through the unit's DI in its own primed process, judged
    against the amp track on both halves at the unit's lag; S's judges come from its lag record (the same renders).
    -> panel/judge/<tag>/<unit>|<amp>.json."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    require("phase_5d")
    tags = [t for t in args.names.split(",") if t and t != "S"]
    ans = {t: json.loads((out_dir() / PANEL_DIR / "answers" / f"{t}.json").read_text())["answers"] for t in tags}
    units, recs = panel_lagged_units()
    k, n = args.shard
    mine = [p_ for j, p_ in enumerate(units) if j % n == k]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    for prt in mine:
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        for amp in AMPS3:
            key = real_key(prt, amp)
            sp = out_dir() / PANEL_DIR / "judge" / "S" / f"{panel_fname(key)}.json"
            if not sp.exists():
                save(sp, {"unit": prt["unit"], "amp": amp, "tag": "S", "lag": prt["lag"],
                          "judge": {ANY_HALF: recs[prt["unit"]]["s"][amp]["judge"]},
                          "render_sha256": {ANY_HALF: recs[prt["unit"]]["s"][amp]["render_sha256"]}})
            for t in tags:
                gp = out_dir() / PANEL_DIR / "judge" / t / f"{panel_fname(key)}.json"
                asha = answers_sha({key: ans[t][key]})
                if gp.exists():
                    if json.loads(gp.read_text()).get("answers_sha256") != asha:
                        raise SystemExit(f"{gp}: rendered from other answers")
                    continue
                rec = {"unit": prt["unit"], "amp": amp, "tag": t, "lag": prt["lag"], "answers_sha256": asha,
                       "judge": {}, "render_sha256": {}}
                for search, a in sorted(ans[t][key].items()):
                    st = LO.tdict(a["settings"])
                    y = np.asarray(AM.fresh_render(CB.new_renderer, di32, a["select"], st, st),
                                   np.float64)[trim[0]:trim[1]]
                    renders += 2
                    rec["judge"][search] = K.judge(ref, y, di, prt["lag"])
                    rec["render_sha256"][search] = AM.audio_sha(y)
                save(gp, rec)
        print(f"{prt['unit'][-60:]}: renders so far {renders}", flush=True)
    print(f"PANEL-RENDER DONE {k}/{n}: {renders} renders")


def panel_ceiling_units(units):
    """5D's ceiling units: one per band, seeded (PANEL_SEED), each on one seeded amp. -> [(unit, amp)]."""
    import random

    out = []
    for band in sorted({p_["band"] for p_ in units}):
        rng = random.Random(f"{PANEL_SEED}|ceiling|{band}")
        prt = rng.choice(sorted((p_ for p_ in units if p_["band"] == band), key=lambda p_: p_["unit"]))
        out.append((prt, rng.choice(AMPS3)))
    return out


def cmd_panel_ceiling(args):
    """5D's true-DI ceiling (one shard): on each ceiling unit and amp, arm A's main stage (`K.space`, 52 evaluations,
    seed `L.SEED`) from the class's S, scored by the judge on the unit's search half at its lag, as 5B.2's stage 2;
    its best judged on both halves. -> panel/ceiling/<unit>|<amp>.json."""
    import numpy as np

    from learn import arm_a_levers as L
    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    require("phase_5d")
    units, recs = panel_lagged_units()
    halves = panel_halves(units)
    k, n = args.shard
    mine = [x for j, x in enumerate(panel_ceiling_units(units)) if j % n == k]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    ms = L.menu_S()
    LO._wait_cap()
    renders = 0
    for prt, amp in mine:
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        key = real_key(prt, amp)
        path = out_dir() / PANEL_DIR / "ceiling" / f"{panel_fname(key)}.json"
        if path.exists():
            continue
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        search = halves[prt["unit"]]
        held = "B" if search == "A" else "A"
        sel, S = ms[amp][prt["cls"]]
        dims = K.space(amp, S)
        seen, first = {}, {}
        rr = CB.new_renderer()
        try:
            rr.render(di32, sel, LO.tdict(LO.sdict(S)))
            renders += 1

            def f(x):
                y = np.asarray(rr.render(di32, sel, LO.tdict(LO.sdict(x))), np.float64)[trim[0]:trim[1]]
                j = K.judge(ref, y, di, prt["lag"])
                if not first:
                    first.update(sha=AM.audio_sha(y))
                    if first["sha"] != recs[prt["unit"]]["s"][amp]["render_sha256"]:
                        raise SystemExit(f"{key}: S's first evaluation is not bit-identical to its fresh render")
                seen[K.key(x)] = {"judge": j, "peak_dbfs": A.peak_dbfs(y, trim_s=0.0)}
                return j[search]

            best_x, best_v, evals = L.main_stage(dims, S, f, seed=L.SEED)
            renders += evals
        finally:
            rr.close()
        best = dict(seen[K.key(best_x)], settings=LO.sdict(best_x))
        s_j = recs[prt["unit"]]["s"][amp]["judge"]
        save(path, {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_5d", "unit": prt["unit"], "band": prt["band"],
                    "amp": amp, "search": search, "held": held, "lag": prt["lag"], "s_judge": s_j,
                    "best": best, "evaluations": evals, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{key[-70:]}: {search}->{held} S {s_j[held]:.3f} best {best['judge'][held]:.3f}; renders so far "
              f"{renders}", flush=True)
    print(f"PANEL-CEILING DONE {k}/{n}: {renders} renders")


def weighted_clustered(rows, weight_of):
    """rows: [(cluster, value)]; weight_of: {cluster: weight}. The weighted mean of cluster means and its 90% interval
    clustered by cluster (sandwich variance with the small-sample factor, t with clusters - 1 df); the effective
    number of clusters 1/sum(w^2) over the normalised weights."""
    import statistics

    by = {}
    for c, v in rows:
        by.setdefault(c, []).append(v)
    means = {c: statistics.fmean(v) for c, v in by.items()}
    w = {c: weight_of[c] for c in means}
    tot = sum(w.values())
    w = {c: x / tot for c, x in w.items()}
    m = sum(w[c] * means[c] for c in means)
    g = len(means)
    if g < 2:
        return {"mean": m, "lo90": None, "hi90": None, "clusters": g, "n_eff": 1.0}
    var = g / (g - 1) * sum(w[c] ** 2 * (means[c] - m) ** 2 for c in means)
    half = t95(g - 1) * math.sqrt(var)
    return {"mean": m, "lo90": m - half, "hi90": m + half, "clusters": g,
            "n_eff": 1 / sum(x * x for x in w.values()), "clusters_negative": sum(v < 0 for v in means.values())}


def panel_rows(a, b, units, halves, judge):
    """ln(d_a / d_b) on the held half per (unit, amp, search): a model answers for its search half, a centre or S
    for any half; a missing or non-finite judge drops the direction. -> [(unit, amp, value)], dropped."""
    rows, dropped = [], 0
    for p_ in units:
        sh = halves[p_["unit"]]
        held = "B" if sh == "A" else "A"
        for amp in AMPS3:
            key = real_key(p_, amp)
            vals = []
            for t in (a, b):
                j = judge[t].get(key)
                x = None if j is None else (j.get(sh) or j.get(ANY_HALF) or {}).get(held)
                vals.append(x)
            if all(x is not None and math.isfinite(x) and x > 0 for x in vals):
                rows.append((p_, amp, math.log(vals[0] / vals[1])))
            else:
                dropped += 1
    return rows, dropped


def panel_weights(units, capped=True):
    """5D's DI weights: each band weighs as min(its DIs, 4) (capped) or 1 (equal), its DIs equal within it."""
    by = {}
    for p_ in units:
        by.setdefault(p_["band"], set()).add(p_["di"])
    return {d: (min(len(ds), 4) if capped else 1) / len(ds) for b, ds in by.items() for d in ds}


def cmd_panel_report(args):
    """5D's rows (zero renders): for each pair in `--pairs`, ln(d_a / d_b) on the held half, the capped band-weighted
    mean with its DI-clustered interval (primary), equal band weights, DI-weighted and band-clustered beside; per
    band (clustered by DI, or by window where a band has one DI), per class, leave-one-band-out, and with the
    hum-passed, far-mic, high-bleed and unmeasured units apart. -> panel/report-<label>.json."""
    require("phase_5d")
    units, _ = panel_lagged_units()
    halves = panel_halves(units)
    tags = {t for pair in args.pairs.split(",") for t in pair.split(":")}
    judge = {}
    for t in tags:
        judge[t] = {}
        for f in (out_dir() / PANEL_DIR / "judge" / t).glob("*.json"):
            r = json.loads(f.read_text())
            judge[t][f"{r['unit']}|{r['amp']}"] = r["judge"]
    wc, we = panel_weights(units), panel_weights(units, capped=False)

    def summary(rows):
        if not rows:
            return None
        di_rows = [(p_["di"], v) for p_, _, v in rows]
        dis = {p_["di"] for p_, _, _ in rows}
        out = {"capped": weighted_clustered(di_rows, {d: wc[d] for d in dis}),
               "equal_bands": weighted_clustered(di_rows, {d: we[d] for d in dis}),
               "di_weighted": weighted_clustered(di_rows, {d: 1.0 for d in dis}),
               "band_clustered": clustered([(p_["band"], p_["di"], v) for p_, _, v in rows]),
               "directions": len(rows)}
        return out

    rep = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_5d", "status": "strong hint (effective N below the minimum)",
           "units": len(units), "rows": {}}
    for pair in args.pairs.split(","):
        a, b = pair.split(":")
        rows, dropped = panel_rows(a, b, units, halves, judge)
        row = {"all": summary(rows), "dropped": dropped, "per_band": {}, "per_class": {}, "leave_one_band_out": {},
               "apart": {}}
        for band in sorted({p_["band"] for p_ in units}):
            br = [r for r in rows if r[0]["band"] == band]
            one = len({p_["di"] for p_, _, _ in br}) == 1
            cl = clustered([((p_["section"] if one else p_["di"]), p_["unit"], v) for p_, _, v in br]) if br else None
            row["per_band"][band] = cl and {q: cl.get(q) for q in ("mean", "lo90", "hi90", "clusters", "parts")}
            rest = [r for r in rows if r[0]["band"] != band]
            row["leave_one_band_out"][band] = summary(rest)["capped"]["mean"] if rest else None
        for cls in ("clean", "crunch"):
            row["per_class"][cls] = summary([r for r in rows if r[0]["cls"] == cls])
        groups = {"hum": lambda p_: "hum" in p_.get("di_flags", []), "far": lambda p_: p_.get("far"),
                  "high_bleed": lambda p_: p_["bleed_db"] is not None and p_["bleed_db"] > PANEL_BLEED_MAX_DB,
                  "unmeasured_bleed": lambda p_: p_["bleed_db"] is None}
        for g, f in groups.items():
            row["apart"][g] = {"with": summary([r for r in rows if f(r[0])]),
                               "without": summary([r for r in rows if not f(r[0])])}
        row["apart"]["without_all"] = summary([r for r in rows if not any(f(r[0]) for f in groups.values())])
        rep["rows"][f"{a} - {b}"] = row
        c = row["all"]["capped"] if row["all"] else None
        if c and c["lo90"] is not None:
            print(f"{a} - {b}: capped {c['mean']:+.4f} [{c['lo90']:+.4f}, {c['hi90']:+.4f}] (n_eff {c['n_eff']:.1f}, "
                  f"{c['clusters_negative']} of {c['clusters']} DIs better); band-clustered "
                  f"{row['all']['band_clustered']['mean']:+.4f} [{row['all']['band_clustered']['lo90']:+.4f}, "
                  f"{row['all']['band_clustered']['hi90']:+.4f}]; dropped {dropped}")
    save(out_dir() / PANEL_DIR / f"report-{args.label or 'panel'}.json", rep)
    print("PANEL-REPORT DONE")


# --- D_fix (declared 2026-11-02, ledger phase_dfix): the real rows in backings and their training mode ----------------

DFIX_SEED = 20261102
DFIX_K = 25                          # variants per real unit: a BKS unit's own section's backing and 24 pool backings,
                                     # a GOAT unit's 25 pool backings
DFIX_DIR = "dfix"                    # under out_dir(): inputs/, lends-k-of-n.json
DFIX_HELD0 = 500_000                 # the held fold's real rows (the diagnostic): ids REAL_ROW0 or GOAT_ROW0 + this + j


DFIX_SHARES = {"p33": 1 / 3, "p10": 1 / 10}      # the share amendment (F39, `phase_dfix_share`): a training real row is
                                                # shown in an epoch with probability p (`dfix_shown`)
DFIX_BASES = ("P2b-dfix",) + tuple(f"P2b-dfix{t}" for t in DFIX_SHARES)   # the all-labels runs, D_fix's and each D_p


DFIX_READS = {t for b in DFIX_BASES for t in (b, f"{b}-clean")}   # read 2's BKS tags: fold models on the backed (own
                                                                   # section) input, and on the clean amp track beside


def dfix_backed(unit, v=0):
    """A real unit's D_fix input variant v (0: a BKS unit's own section's backing) as {half: (uint8 mel, LUFS)}."""
    import numpy as np

    d = np.load(dfix_input_path(unit, v))
    return {"A": (d["sA"], float(d["lufs"][0])), "B": (d["sB"], float(d["lufs"][1]))}


def dfix_input_path(unit, v):
    return out_dir() / DFIX_DIR / "inputs" / f"{unit.replace('/', '__')}-v{v:02d}.npz"


def dfix_units():
    """D_fix's real units: every unit with a labelled record, BKS's stage 1-2 (`real_labels(2)`) and GOAT's
    (`goat_labels`); a unit's records (one per amp) share its audio. -> [(unit, "bks" | "goat", part)], sorted."""
    brecs, by_unit, _ = real_labels(2)
    grecs, gunits, _ = goat_labels()
    out = {r["unit"]: (r["unit"], "bks", by_unit[r["unit"]]) for r in brecs}
    for r in grecs:
        if r["unit"] in out and out[r["unit"]][1] == "bks":
            raise SystemExit(f"{r['unit']}: both a BKS and a GOAT unit")
        out[r["unit"]] = (r["unit"], "goat", gunits[r["unit"]])
    return [out[u] for u in sorted(out)]


def dfix_read_only(units, read_units):
    """The GOAT read units with no D_fix row (a unit the ear passed whose search gave no label, read all the same):
    they need their inputs for read 2 (variant 0 at least) but are never trained on. -> [(unit, "goat", part)]."""
    have = {u for u, _, _ in units}
    return [(p_["unit"], "goat", p_) for p_ in sorted(read_units, key=lambda q: q["unit"]) if p_["unit"] not in have]


def dfix_lend(unit, cls, train_ids, kept, section=None, seed=DFIX_SEED):
    """The training example that lends a real unit its levels: a seeded choice among P2b-wide24's training examples of
    the unit's own section (a BKS unit), else (a GOAT unit, or a BKS section with no training example: recorded) of
    its class. -> (example id, "section" | "class")."""
    import random

    rng = random.Random(f"{seed}|lend|{unit}")
    own = sorted(i for i in train_ids if section is not None and kept[i]["section"] == section)
    if own:
        return rng.choice(own), "section"
    same = sorted(i for i in train_ids if kept[i]["cls"] == cls)
    if not same:
        raise SystemExit(f"{unit}: no training example of class {cls}")
    return rng.choice(same), "class"


def dfix_draws(unit, section, entries, own=True, k=DFIX_K, seed=DFIX_SEED):
    """A real unit's k backings: with `own` (a BKS unit) variant 0 is its own section's backing (None), then pool
    entries drawn as `wide_draws` draws them (a session uniformly among the pool's sessions other than the unit's own,
    then one of its entries, and a vocal flag p 0.5), seeded by the unit. -> [(entry index or None, vocals or None)]."""
    import random

    by_s = {}
    for j, e_ in enumerate(entries):
        by_s.setdefault(e_["session"], []).append(j)
    s_ = session_of(section)
    sess = sorted(x for x in by_s if x not in (s_, pathlib.Path(s_).name))
    rng = random.Random(f"{seed}|{unit}")
    out = [(None, None)] if own else []
    return out + [(rng.choice(by_s[rng.choice(sess)]), rng.random() < 0.5) for _ in range(k - len(out))]


def dfix_level(y, target_lufs, lufs):
    """A real amp track brought to the lending example's stored target loudness (its `y`, before the overall gain),
    measured by `lufs` (`song_aug.lufs`, the pipeline's). -> (scaled track, gain dB)."""
    lr = float(lufs(y))
    if lr <= -69.9:
        raise SystemExit("a silent amp track")
    g = float(target_lufs) - lr
    return y * 10 ** (g / 20), g


def dfix_backing_gain(e_gb, e_own_lv, ent_lv):
    """`cmd_build_wide`'s backing gain: the lending example's stored gb plus its own bare backing's level (in its own
    vocal variant) less the new backing's."""
    return e_gb + e_own_lv - ent_lv


def dfix_mix(guitar, back, gb, ga):
    """`cmd_build_wide`'s mix before the mastering draw: (guitar + backing at gb) at the overall gain ga (dB)."""
    return (guitar + back * 10 ** (gb / 20)) * 10 ** (ga / 20)


def dfix_di_tracks(prt, inv):
    """Every track of a BKS unit's DI (the DI file, its amp track, its other reamps: one performance), which its own
    section's backing must not hold."""
    return set(inv[prt["di"]].get("own") or []) | {prt["di"].rsplit("/", 1)[-1], prt["track"]}


def cmd_build_dfix_real(args):
    """D_fix's real rows' inputs (CPU, zero renders). Each labelled real unit's amp section (`real_amp_track`: the
    10-s trimmed section a D_CC target is, length asserted) in DFIX_K backings, levelled by a lending training example
    (`dfix_lend`) exactly as `cmd_build_wide` levels that example's own variants: the track brought to the example's
    stored target loudness, each backing at the example's gb plus its own bare level less the backing's, the sum at the
    example's ga, then the example's mastering draw. A BKS unit's variant 0 is its own section's backing: the section's
    non-guitar stems in the lending example's own vocal variant (exactly its P2b backing when it lends from the
    section), asserted free of every track of the unit's DI; its other 24 and all of a GOAT unit's 25 are pool
    backings (`dfix_draws`, never the unit's own session). One shard of units; an existing file is kept after its pool
    check. -> dfix/inputs/<unit>-vNN.npz and dfix/lends-k-of-n.json (each unit's lender and rule)."""
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_aug as SA
    from learn import trusted_data as T

    e = require("phase_dfix")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    a = argparse.Namespace(out=None, smoke=False)
    stems = T.Stems(CB.ctx_for(a))
    built = T.rows_of(croot, CB.STAGE, "build")
    inv = CB.cc_inventory()
    pool = json.loads(wide_pool_path().read_text())["entries"]
    psha = pool_sha(pool)
    own_lv = json.loads((out_dir() / "inputs" / "backings-levels.json").read_text())["levels"]
    kk, n = args.shard
    units = dfix_units()
    if args.reads_only:                            # read 2's GOAT units with no row (`dfix_read_only`)
        units = dfix_read_only(units, goat_read_units())
    mine = [u for q, u in enumerate(units) if q % n == kk]
    lends, t0, done = {}, time.time(), 0
    for m, (unit, kind, prt) in enumerate(mine):
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        bks = kind == "bks"
        i, rule = dfix_lend(unit, prt["cls"], sp["train"], kept, prt["section"] if bks else None)
        x, rw, bw = kept[i], rend[i], built[i]
        e_voc = bool(x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"])
        draws = dfix_draws(unit, prt["section"], pool, own=bks)
        paths = [dfix_input_path(unit, v) for v in range(DFIX_K)]
        for p in paths:
            if p.exists() and str(np.load(p)["pool_sha256"]) != psha:
                raise SystemExit(f"{p}: built from another pool")
        lends[unit] = {"kind": kind, "lend": i, "rule": rule, "lend_section": x["section"]}
        todo = [v for v, p in enumerate(paths) if not p.exists()]
        if not todo:
            lends[unit]["target_lufs"] = float(np.load(paths[0])["target_lufs"])
            continue
        y = np.asarray(G.read_flac(T.flac_path(croot, CB.STAGE, i, "target"), rw["target"]["scale"],
                                   rw["target"]["sha256"]), np.float64)
        tl = float(SA.lufs(y))
        ref = np.asarray(real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64)
        if len(ref) != len(y):
            raise SystemExit(f"{unit}: {len(ref)} samples against the lending target's {len(y)}")
        gtr, g = dfix_level(ref, tl, SA.lufs)
        lends[unit].update(target_lufs=tl, guitar_gain_db=g)
        e_lv = own_lv[x["section"]][str(e_voc)]
        for v in todo:
            j, voc = draws[v]
            if j is None:                          # a BKS unit's own section's backing (non-guitar stems only)
                own_x = x if rule == "section" else kept[min(q for q in kept if kept[q]["section"] == prt["section"])]
                tracks = bare_tracks(own_x, e_voc)
                if dfix_di_tracks(prt, inv) & set(tracks):
                    raise SystemExit(f"{unit}: its own backing holds a track of its DI")
                voc = bool(e_voc and own_x["stems"]["v"] != own_x["stems"]["n"])
                back = np.asarray(stems.get(prt["section"], tracks), np.float64)
                lv = own_lv[prt["section"]][str(voc)] if rule == "section" else float(SA.lufs(back))
                if lv < BACKING_FLOOR_LUFS:
                    raise SystemExit(f"{unit}: its own backing is silent ({lv:.1f} LUFS)")
                bid = prt["section"]
            else:
                ent = pool[j]
                tracks = ent["tracks"]["v" if voc else "n"]
                back = np.asarray(stems.get(ent["id"], tracks) if ent["kind"] == "training"
                                  else bare_backing(ent["sd"], tracks, ent["start_s"]), np.float64)
                lv, bid = ent["lufs"][str(bool(voc))], ent["id"]
            gb, ga = dfix_backing_gain(bw["gains_db"]["gb"], e_lv, lv), bw["gains_db"]["ga"]
            mix = dfix_mix(gtr, back, gb, ga)
            mastered, mrng = DS.master_draw(i)
            if mastered:
                mix = SA.compress(mix, mrng)
            f, lu, _ = DS.half_features(mix)
            DS._save_npz(paths[v], sA=f["A"], sB=f["B"], lufs=[lu["A"], lu["B"]], lend=i, lend_rule=rule,
                         backing=bid, vocals=bool(voc), gains=[gb, ga], guitar_gain_db=g, target_lufs=tl,
                         pool_sha256=psha)
            done += 1
        if m % 10 == 0:
            print(f"unit {m + 1}/{len(mine)}: {done} built; {(time.time() - t0) / max(1, done):.2f} s each", flush=True)
    tag = "reads-" if args.reads_only else ""
    save(out_dir() / DFIX_DIR / f"lends-{tag}{kk}-of-{n}.json",
         {"rule": cmd_build_dfix_real.__doc__, "pool_sha256": psha, "units": lends})
    fb = sorted(u for u, r in lends.items() if r["kind"] == "bks" and r["rule"] == "class")
    print(f"BUILD-DFIX-REAL DONE {kk}/{n}: {done} built for {len(mine)} units; BKS units lent by class (no training "
          f"example in their section): {len(fb)} {fb}")


def dfix_run_name(real_fold, share=None):
    """D_fix's run names: `P2b-dfix` (every real label) and `P2b-dfix{k}` (fold k's BKS DIs and GOAT items out); a
    share's `P2b-dfix{share}` and `P2b-dfix{share}-k{k}` (the `-k` keeps p10's fold 0 apart from a p100); no other run
    takes these names."""
    if share is not None and share not in DFIX_SHARES:
        raise SystemExit(f"--dfix-share in {sorted(DFIX_SHARES)}")
    return dfix_fold_name(f"P2b-dfix{share or ''}", real_fold)


def dfix_fold_name(base, k):
    """The run of D_fix family member `base` (an all-labels name, or its `-clean` read tag) for fold k (None: base)."""
    base = base.removesuffix("-clean")
    if base not in DFIX_BASES:
        raise SystemExit(f"{base}: not a D_fix run ({', '.join(DFIX_BASES)})")
    if k is None:
        return base
    return f"{base}{k}" if base == "P2b-dfix" else f"{base}-k{k}"


def dfix_share_of(name):
    """A D_fix family name's p (1.0 for D_fix itself), all-labels, fold (`P2b-dfix{k}`, `P2b-dfix{share}-k{k}`) or
    read tag."""
    import re

    tag = re.sub(r"-k\d+$", "", name.removesuffix("-clean")).removeprefix("P2b-dfix")
    return 1.0 if tag == "" or tag.isdigit() else DFIX_SHARES[tag]


def dfix_phase(name):
    """A D_fix family name's ledger phase: the share amendment's for a D_p, D_fix's otherwise."""
    return "phase_dfix_share" if dfix_share_of(name) < 1 else "phase_dfix"


def dfix_shown(i, epoch, p):
    """Whether training real row i is shown in `epoch` at share p: a seeded draw on its own key, independent of
    `dfix_variant`'s; p = 1 shows every row."""
    import random

    return p >= 1 or random.Random(f"{DFIX_SEED}|show|{i}|{epoch}").random() < p


def dfix_refusal(args):
    """The training flags' guard: why `--dfix` with anything but `--rung b [--real-fold k] [--stage 2] [--seed s]` is
    refused, or why `--wide --real-fold` without `--dfix` is (D_fix's own branch); None when allowed."""
    if not getattr(args, "dfix", False):
        if getattr(args, "wide", False) and args.real_fold is not None:
            return "--wide --real-fold is D_fix's run: train --dfix --rung b [--real-fold k]"
        if getattr(args, "dfix_share", None) is not None:
            return "--dfix-share is the share amendment's D_fix: train --dfix --dfix-share p33|p10"
        return None
    if getattr(args, "dfix_share", None) not in (None, *DFIX_SHARES):
        return f"--dfix-share in {sorted(DFIX_SHARES)}"
    if args.rung != "b":
        return "--dfix is P2b-wide24's recipe plus the real rows: --rung b"
    bad = [f"--{f.replace('_', '-')}" for f in ("aug", "backings", "dd", "pc", "pcsz", "wide", "goat", "goat_shuffle")
           if getattr(args, f, False)]
    bad += ["--fold"] * (args.fold is not None) + ["--frac"] * (args.frac != 1.0) \
        + ["--sections"] * (args.sections != 1.0) + ["--stage"] * (args.stage not in (0, 2))
    return f"--dfix takes only --real-fold, --stage 2 and --seed: {' '.join(bad)} refused" if bad else None


def dfix_records(brecs, by_unit, folds, grecs, gunits, k):
    """D_fix's real records for model k: training BKS `fold_records` and GOAT `goat_fold_records`, each cycled to its
    rows per epoch, and the held fold's records once each (the diagnostic). k None (D_fix) takes every label and holds
    none; a list longer than its rows per epoch is kept whole (BKS has 306 labels: cycling to 300 would drop six).
    -> (bks, goat, bks held, goat held)."""
    if k is None:
        return (cycled(brecs, max(REAL_PER_EPOCH, len(brecs))), cycled(grecs, max(GOAT_PER_EPOCH, len(grecs))), [], [])
    return (fold_records(brecs, by_unit, folds, k), goat_fold_records(grecs, gunits, k),
            [r for r in brecs if folds[by_unit[r["unit"]]["di"]] == k],
            [r for r in grecs if gunits[r["unit"]]["fold"] == k])


def record_rows(recs, by_unit, row0, label_of=None):
    """Rows of labelled real records, one per record with ids from row0, as `real_rows_for` and `goat_rows` build
    them (the label `F.label_of` of the search's best setting) but without their 5B.1-path inputs."""
    if label_of is None:
        from learn import full_space as F
        from learn import local_objective as LO

        def label_of(rec):
            return F.label_of(LO.tdict(rec["label"]), rec["amp"])
    out = []
    for j, rec in enumerate(recs):
        prt = by_unit[rec["unit"]]
        out.append({"i": row0 + j, "section": prt["section"], "band": prt["band"], "amp": rec["amp"],
                    "cls": prt["cls"], "base": prt["cls"], "label": label_of(rec), "real": rec["unit"]})
    return out


def dfix_rows_of(brecs, by_unit, folds, grecs, gunits, k, label_of=None):
    """D_fix's real rows for model k (`dfix_records`): training rows with BKS ids from REAL_ROW0 and GOAT's from
    GOAT_ROW0 (as `real_rows_for` and `goat_rows` number them), the held fold's from those + DFIX_HELD0.
    -> (training rows, held rows, counts)."""
    b, g, bh, gh = dfix_records(brecs, by_unit, folds, grecs, gunits, k)
    if max(len(b), len(bh)) >= DFIX_HELD0 or REAL_ROW0 + DFIX_HELD0 + len(bh) > GOAT_ROW0:
        raise SystemExit("D_fix's real row ids would collide")
    train = record_rows(b, by_unit, REAL_ROW0, label_of) + record_rows(g, gunits, GOAT_ROW0, label_of)
    held = (record_rows(bh, by_unit, REAL_ROW0 + DFIX_HELD0, label_of)
            + record_rows(gh, gunits, GOAT_ROW0 + DFIX_HELD0, label_of))
    return train, held, {"real_rows": len(b), "goat_rows": len(g), "held_real_rows": len(bh),
                         "held_goat_rows": len(gh)}


def dfix_real_rows(k):
    """`dfix_rows_of` on the stored labels: BKS stage 1-2 (`real_labels(2)`) and GOAT's (`goat_labels`)."""
    brecs, by_unit, folds = real_labels(2)
    grecs, gunits, _ = goat_labels()
    return dfix_rows_of(brecs, by_unit, folds, grecs, gunits, k)


def dfix_variant(i, epoch):
    """The variant real row `i` shows at `epoch`: a seeded draw of DFIX_K in training, variant 0 at eval (epoch < 0)."""
    import random

    return 0 if epoch < 0 else random.Random(f"{DFIX_SEED}|{i}|{epoch}").randrange(DFIX_K)


class DfixData(WideData):
    """D_fix's data: P2b-wide24's plugin rows exactly as WideData (its variant check on the plugin training ids only),
    and real rows reading `build-dfix-real`'s variants: in training a real row shows `dfix_variant(row id, epoch)`;
    eval reads variant 0 (a BKS unit's own section's backing). Refuses a real unit lacking any variant or built from
    another pool."""

    def __init__(self, rows, path_of, plugin_ids, real_train_ids, share=1.0):
        import hashlib

        import numpy as np

        from learn import direct_stems as DS

        unit = {r["i"]: r["real"] for r in rows if "real" in r}
        units = sorted(set(unit.values()))
        missing = [u for u in units if not all(dfix_input_path(u, v).exists() for v in range(DFIX_K))]
        if missing:
            raise SystemExit(f"build-dfix-real is incomplete: {len(missing)} real units lack variants")
        super().__init__(rows, lambda i: dfix_input_path(unit[i], 0) if i in unit else path_of(i), plugin_ids)
        psha = pool_sha(json.loads(wide_pool_path().read_text())["entries"])
        train_units = {unit[i] for i in real_train_ids}
        h = hashlib.sha256()
        self.RV, self.target_lufs = {}, {}
        for u in units:
            arr = np.zeros((DFIX_K, 2, 96, 446), np.uint8)
            lu = np.zeros((DFIX_K, 2), np.float32)
            for v in range(DFIX_K):
                p = dfix_input_path(u, v)
                d = np.load(p)
                if str(d["pool_sha256"]) != psha:
                    raise SystemExit(f"{p}: built from another pool")
                if u in train_units:
                    arr[v, 0], arr[v, 1], lu[v] = d["sA"], d["sB"], d["lufs"]
                h.update(f"{p.name} {DS.hashlib_file(p)}\n".encode())
            self.target_lufs[u] = float(np.load(dfix_input_path(u, 0))["target_lufs"])
            if u in train_units:
                self.RV[u] = (arr, lu)
        self.inputs_sha256 = h.hexdigest()
        self.RJ = {j: r["real"] for j, r in enumerate(rows) if r["i"] in real_train_ids}
        self.counts = dict(self.counts, real_rows=len(self.RJ), real_units=len(train_units), real_variants=DFIX_K)
        self.share = float(share)
        if self.share < 1:
            self.epoch_keep = self._epoch_keep

    def _epoch_keep(self, order, epoch):
        """The share amendment's filter on `fit`'s permuted order: plugin rows all kept, each training real row kept
        by `dfix_shown` (order kept)."""
        import numpy as np

        return np.asarray([j for j in order if int(j) not in self.RJ
                           or dfix_shown(self.rows[int(j)]["i"], epoch, self.share)], dtype=np.asarray(order).dtype)

    def real_choices(self, idx, epoch):
        """{row index: (unit, variant)} for a batch's training real rows at `epoch`."""
        return {int(j): (self.RJ[int(j)], dfix_variant(self.rows[int(j)]["i"], epoch)) for j in idx
                if int(j) in self.RJ}

    def batch(self, idx, epoch, dev):
        import numpy as np

        saved = {}
        if epoch >= 0:
            for j, (u, v) in self.real_choices(np.asarray(idx), epoch).items():
                if v:
                    saved[j] = (self.X[j].copy(), self.L[j].copy())
                    self.X[j], self.L[j] = self.RV[u][0][v], self.RV[u][1][v]
        try:
            return WideData.batch(self, idx, epoch, dev)
        finally:
            for j, (x, lu) in saved.items():
                self.X[j], self.L[j] = x, lu


# --- D_fix to V-real (declared 2026-11-02 after F40, ledger phase_dfix_vreal): read 3 on the X-LANCE crop stems -------

DFIX_VREAL_MODELS = ("P2b-dfix", "P2b-wide24")     # the declared models: D_fix, and W beside
DFIX_VREAL_BASE = "S-recheck-dfix"                  # S re-rendered under its own tag (phase 4's S groups are kept)
DFIX_VREAL_TAGS = {                                 # tag: (model, input, readout); per search half unless ANY_HALF
    "DV-P2b-dfix-stem": ("P2b-dfix", "stem", "plain"),          # the primary
    "DV-P2b-wide24-stem": ("P2b-wide24", "stem", "plain"),
    "DV-P2b-dfix-stem-sc": ("P2b-dfix", "stem", "sc"),          # re-centred on S (`sc_cont`)
    "DV-P2b-dfix-amp": ("P2b-dfix", "amp", "plain"),            # the part's own amp track at D_fix's input level
    "DV-RcG": (None, None, "RcG"),
    DFIX_VREAL_BASE: (None, None, "S"),
}
DFIX_VREAL_LEVEL = -12.25           # levels.json's eval_mix_lufs_median to 2 decimals (step4_half's rule)
DFIX_VREAL_HASHES = "phase_dfix_vreal_answers"      # the ledger key: {tag: sha256 of vreal/answers/<tag>.json}
DFIX_VREAL_P4 = "P4-P2a-best"                       # F20's stored P4 answers (amp track - P4, zero renders)
DFIX_VREAL_PAIRS = (                                # (row, a, b, own inputs): every row's base is DFIX_VREAL_BASE
    ("D_fix - S (primary)", "DV-P2b-dfix-stem", DFIX_VREAL_BASE, False),
    ("W - S", "DV-P2b-wide24-stem", DFIX_VREAL_BASE, False),
    ("D_fix - W", "DV-P2b-dfix-stem", "DV-P2b-wide24-stem", False),
    ("D_fix - RcG", "DV-P2b-dfix-stem", "DV-RcG", False),
    ("RcG - S", "DV-RcG", DFIX_VREAL_BASE, False),
    ("S-centred - S", "DV-P2b-dfix-stem-sc", DFIX_VREAL_BASE, False),
    ("amp track - S (Wickerman 2 and 3 apart)", "DV-P2b-dfix-amp", DFIX_VREAL_BASE, True),
    ("amp track - S (Wickerman 2 and 3 one part)", "DV-P2b-dfix-amp", DFIX_VREAL_BASE, False),
    ("amp track - P4", "DV-P2b-dfix-amp", DFIX_VREAL_P4, True),
)


def dfix_vreal_tags(names):
    """`--names` as declared tags (empty: every one); any other tag is refused."""
    tags = [t for t in names.split(",") if t] or list(DFIX_VREAL_TAGS)
    bad = [t for t in tags if t not in DFIX_VREAL_TAGS]
    if bad:
        raise SystemExit(f"D_fix to V-real declares only {sorted(DFIX_VREAL_TAGS)}; not {bad}")
    return tags


def dfix_vreal_load(name):
    """A declared model's NS-best checkpoints, both seeds pooled on one training set; any other model is refused.
    -> (nets, run records)."""
    if name not in DFIX_VREAL_MODELS:
        raise SystemExit(f"D_fix to V-real reads only {DFIX_VREAL_MODELS}; not {name}")
    nets, recs = zip(*(load_run(name, sd, "best") for sd in SEEDS))
    if any(r_["train_ids"] != recs[0]["train_ids"] or r_["held_ids"] != recs[0]["held_ids"] or r_["rung"] != "b"
           for r_ in recs):
        raise SystemExit(f"{name}: both seeds of one rung-b training set")
    return list(nets), list(recs)


def vreal_mix_target(levels=None):
    """The level a V-real crop's mix is brought to: levels.json's `eval_mix_lufs_median`, asserted -12.25 to 2
    decimals (the declaration's)."""
    from learn import direct_existing as DE

    v = json.loads(pathlib.Path(levels or DE.LEVELS).read_text())["summary"]["eval_mix_lufs_median"]
    if round(v, 2) != DFIX_VREAL_LEVEL:
        raise SystemExit(f"levels.json's eval_mix_lufs_median is {v}, not the declared {DFIX_VREAL_LEVEL}")
    return float(v)


def vreal_model_input(s8, lufs, half, amp, cls):
    """One half's input as every rung reads it (`RungData`: the signal in channel 0, the other channel and its
    loudness slot zeroed): `model_input` on (s8, s8), D_stem's zeroing."""
    from learn import direct_stems as DS

    return DS.model_input(s8, s8, lufs, lufs, half, amp, cls, "Dstem")


def floor_share(s8):
    """The share of a half's frames all at the grid floor (P4's quiet-input measure)."""
    import numpy as np

    return float(np.mean(np.all(np.asarray(s8) == 0, axis=0)))


def song_key(s):
    import re

    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def vreal_songs(inv):
    """V-real's songs as `song_key`s: every part's session folder and song title (the inventory's)."""
    recs = [r for r in inv.values() if r.get("slug") in PR.VREAL]
    if {r["slug"] for r in recs} != set(PR.VREAL):
        raise SystemExit(f"V-real parts missing from the inventory: {sorted(set(PR.VREAL) - {r['slug'] for r in recs})}")
    return {song_key(pathlib.Path(r["session_dir"]).name) for r in recs} | {song_key(r["song"]) for r in recs}


def leaks_of(sources, bands, songs):
    """sources [(what, band, [song names])] -> the problems: a source with no band, of a band in `bands`, or of a song
    whose `song_key` is in `songs`."""
    return sorted({f"{w}: no band" for w, b, _ in sources if b is None}
                  | {f"{w}: band {b}" for w, b, _ in sources if b in bands}
                  | {f"{w}: song {s}" for w, _, ss in sources for s in ss if s and song_key(s) in songs})


def dfix_training_sources(kept, inv, name="P2b-dfix"):
    """Every training input of D_fix's run `name` (both seeds' run files) as (what, band, [songs]): its plugin rows
    and NS rows (the NS-best choice); its BKS and GOAT real rows' units (`dfix_real_rows`, by the run's ids); each real
    unit's DFIX_K backings by `dfix/inputs`'s records (a BKS unit's own section, pool entries); and every entry of the
    backing pool (the plugin rows' 24 draws and the real units' come from it). -> (sources, counts)."""
    import numpy as np

    recs = [json.loads((out_dir() / "runs" / f"{name}-{sd}.json").read_text()) for sd in SEEDS]
    ids = sorted({i for r_ in recs for i in r_["train_ids"] + r_["held_ids"]})
    by_sec, by_sd = {}, {}
    for x in kept.values():
        by_sec.setdefault(x["section"], x)
    for r_ in inv.values():
        if r_.get("session_dir"):
            by_sd.setdefault(r_["session_dir"], r_)

    def of_section(sec):
        x = by_sec.get(sec)
        names = [pathlib.Path(session_of(sec)).name]
        return (None, names) if x is None else (x["band"], names + [pathlib.Path(x["session_dir"]).name,
                                                                    inv[x["di"]].get("song")])
    src, cnt = [], {"plugin_rows": 0, "real_rows": 0, "real_units": 0, "unit_backings": 0, "pool_entries": 0}
    for i in ids:
        if i < REAL_ROW0:
            src.append((f"plugin row {i}", *of_section(kept[i]["section"])))
            cnt["plugin_rows"] += 1
    rows = {r_["i"]: r_ for r_ in dfix_real_rows(None)[0]}
    real = [i for i in ids if i >= REAL_ROW0]
    if set(real) - set(rows):
        raise SystemExit(f"{name}: {len(set(real) - set(rows))} real row ids not among D_fix's labelled rows")
    units = {u: (k, p_) for u, k, p_ in dfix_units()}
    used = sorted({rows[i]["real"] for i in real})
    if any(set(r_["dfix"]["target_lufs"]) != set(used) for r_ in recs):
        raise SystemExit(f"{name}: the run's real units are not its rows' units")
    pool = json.loads(wide_pool_path().read_text())["entries"]
    by_id = {e_["id"]: e_ for e_ in pool}

    def of_entry(e_):
        if e_["kind"] == "training":
            return of_section(e_["id"])
        r_ = by_sd.get(e_["sd"]) or {}
        return r_.get("band"), [e_["session"], r_.get("song")]
    for u in used:
        kind, prt = units[u]
        songs = ([pathlib.Path(session_of(prt["section"])).name, pathlib.Path(prt["sd"]).name,
                  inv[prt["di"]].get("song")] if kind == "bks" else [prt.get("item")])
        src.append((f"real unit {u}", prt["band"], songs))
        cnt["real_units"] += 1
        for v in range(DFIX_K):
            bid = str(np.load(dfix_input_path(u, v))["backing"])
            if bid in by_id:
                src.append((f"{u} v{v} backing {bid}", *of_entry(by_id[bid])))
            elif v == 0 and kind == "bks" and bid == prt["section"]:
                src.append((f"{u} v0 own backing", *of_section(bid)))
            else:
                raise SystemExit(f"{u} v{v}: backing {bid} is neither a pool entry nor its own section")
            cnt["unit_backings"] += 1
    cnt["real_rows"] = len(real)
    for e_ in pool:
        src.append((f"pool entry {e_['id']}", *of_entry(e_)))
        cnt["pool_entries"] += 1
    return src, cnt


def dfix_vreal_leaks(kept, inv, name="P2b-dfix"):
    """The leakage guard: no V-real band (VREAL_BANDS) or song (`vreal_songs`) in any of run `name`'s training inputs
    (`dfix_training_sources`; D_fix's, or FT's all-labels run). Refuses on any. -> counts checked."""
    src, cnt = dfix_training_sources(kept, inv, name)
    bad = leaks_of(src, VREAL_BANDS, vreal_songs(inv))
    if bad:
        raise SystemExit(f"V-real in {name}'s training inputs ({len(bad)}): {bad[:20]}")
    return cnt


def vreal_stem_input(man, slug, info, target):
    """A V-real part's model input source (read 3's rule): its X-LANCE crop stem (stage F's stored one, or T3's
    crop-only stem) and its crop mix, with the gain that brings the mix to `target` LUFS.
    -> (stem, mix, gain_db, input hashes)."""
    from learn import confirm_run as CR
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import trusted_data_t3 as T3

    if info["kind"] == "stagef":
        mix, _, hs = DE.f_inputs(slug, "mega53")
        stem = DS.stored_stem(man, f"stagef/{slug}")
        if stem is None:
            raise SystemExit(f"{slug}: no stored X-LANCE stem")
        hashes = {"context": hs["context"], "stem": man["stems"][f"stagef/{slug}"]["sha256"]}
    else:                                                # T3's own crop: its mix.wav and crop-only stem
        mix = CR.mono(pathlib.Path(info["crop"]) / "mix.wav")
        stem = T3.crop_stem(info)
        hashes = {"crop_record": info["record_sha256"], "stem": info["stem"]["sha256"]}
    return stem, mix, DE.inference_gain_db(mix, target), hashes


def vreal_answers_path(tag):
    return out_dir() / VREAL_DIR / "answers" / f"{tag}.json"


def dfix_vreal_unhashed(tags, entry):
    """The answers files of `tags` whose sha256 is not the one the ledger's DFIX_VREAL_HASHES records ({tag: sha256}):
    renders and the report refuse on any. -> [problems]."""
    from learn import direct_stems as DS

    want = (entry or {}).get(DFIX_VREAL_HASHES) or {}
    out = []
    for t in tags:
        p = vreal_answers_path(t)
        if not p.exists():
            out.append(f"{t}: no answers file")
        elif want.get(t) != DS.hashlib_file(p):
            out.append(f"{t}: sha256 {DS.hashlib_file(p)[:12]} not recorded under {DFIX_VREAL_HASHES}")
    return out


def cmd_dfix_vreal_predict(args):
    """Read 3's answers on V-real-11 (zero renders; `phase_dfix_vreal`), after the leakage guard. Models (both seeds
    pooled, NS-best) per search half on the class's S (`F.answer_settings`): D_fix and W on each part's X-LANCE crop
    stem, the crop's mix brought to levels.json's eval_mix_lufs_median (-12.25, asserted) and the stem given the same
    gain (`step4_half`, T3's V-real rule); D_fix's stem answer re-centred on S (`sc_cont` on the constant of D_fix's
    plugin training labels, P2b-wide24's ids); D_fix on the part's own amp track at its training inputs' median
    (`model_input_lufs`, rung b). For any half: RcG (`rc_setting` on every GOAT label of the amp and class; S where
    none) and S again (phase 4's S answers, under DFIX_VREAL_BASE). A tag whose answers hash is in the ledger is not
    rewritten. -> vreal/answers/<tag>.json; prints each file's sha256 for the ledger's DFIX_VREAL_HASHES."""
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import trusted_data as T

    e = require("phase_dfix_vreal")
    tags = dfix_vreal_tags(args.names)
    if args.which != "best":
        raise SystemExit("read 3 reads the NS-best checkpoints (the declaration): --which best")
    fixed = [t for t in tags if t in (e.get(DFIX_VREAL_HASHES) or {}) and vreal_answers_path(t).exists()]
    if fixed:
        raise SystemExit(f"{fixed}: answers already recorded in the ledger (V-real is read once)")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    inv = CB.cc_inventory()
    guard = dfix_vreal_leaks(kept, inv)
    root, plan, drift, dirs, parts, ms = vreal_ctx()
    models = {m: dfix_vreal_load(m) for m in sorted({DFIX_VREAL_TAGS[t][0] for t in tags} - {None})}
    plugin = [i for i in models["P2b-dfix"][1][0]["train_ids"] if i < REAL_ROW0] if "P2b-dfix" in models else None
    if plugin is not None and any(plugin != json.loads((out_dir() / "runs" / f"P2b-wide24-{sd}.json").read_text())
                                  ["train_ids"] for sd in SEEDS):
        raise SystemExit("D_fix's plugin rows are not P2b-wide24's (both seeds)")
    const = constant_of(rung_rows(kept, rend, plugin)) if "DV-P2b-dfix-stem-sc" in tags else None
    target = vreal_mix_target()
    amp_level = model_input_lufs(models["P2b-dfix"][1][0]) if "DV-P2b-dfix-amp" in tags else None
    doubled = doubled_ids() if dropped["doubles"] == "fixed" else frozenset()
    stem_of = rung_path(croot, "d", doubled)
    p2d = float(np.median([float(z) for i in (plugin or []) for z in np.load(stem_of(i))["lufs"]])) if plugin else None
    man = DS._load(DS.stems_manifest_path(DS.ROOT, T.SEP))
    stems, amps, rcg = {}, {}, {}
    for slug in sorted({d[0] for d in dirs}):
        info = parts[slug]
        stems[slug] = vreal_stem_input(man, slug, info, target)
        if amp_level is not None:
            ref = amp_track(slug, info)
            amps[slug] = (ref, DE.inference_gain_db(ref, amp_level))
    if "DV-RcG" in tags:
        grecs, gunits, _ = goat_labels()
    s_ans = json.loads(vreal_answers_path("S").read_text())["answers"] if DFIX_VREAL_BASE in tags else None
    out = {t: {} for t in tags}
    floor, lufs, rcg_n = {"stem": {}, "amp": {}}, {"stem": {}, "amp": {}}, {}
    for slug, amp, search, _ in dirs:
        cls = PR.VREAL[slug][1]
        sel, S = ms[amp][cls]
        key = f"{slug}|{amp}"
        inp = {}
        stem, mix, g, _ = stems[slug]
        s8, _, ls, _ = DS.step4_half(stem, mix, search, g)
        inp["stem"] = (s8, ls)
        if slug in amps:
            ref, ga = amps[slug]
            inp["amp"] = DS.step4_half(ref, ref, search, ga)[0::2]
        for kind, (q8, lq) in inp.items():
            floor[kind].setdefault(slug, {})[search] = floor_share(q8)
            lufs[kind].setdefault(slug, {})[search] = lq
        reads = {}
        for t in tags:
            m, kind, ro = DFIX_VREAL_TAGS[t]
            if m is not None:
                if (m, kind) not in reads:
                    x, c = vreal_model_input(*inp[kind], search, amp, cls)
                    reads[(m, kind)] = F.readout([o[0] for o in F.run_nets(models[m][0], [x], [c])])
                r = reads[(m, kind)]
                if ro == "sc":
                    _, _, s_sw, s_swm, s_k, s_km, _ = F.encode(dict(S), amp)
                    st = F.answer_settings(amp, S, sc_cont(dict(S), amp, r["a2"], const[(amp, cls)]["cont"]),
                                           [float(v) if mk else None for v, mk in zip(s_sw, s_swm)],
                                           [int(v) if mk else None for v, mk in zip(s_k, s_km)])
                else:
                    st = F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"])
                out[t].setdefault(key, {})[search] = {"select": sel, "settings": LO.sdict(st)}
            elif ro == "RcG" and key not in out[t]:
                labels = [LO.tdict(q["label"]) for q in grecs if q["amp"] == amp and gunits[q["unit"]]["cls"] == cls]
                rcg_n[key] = len(labels)
                out[t][key] = {ANY_HALF: {"select": sel, "settings": LO.sdict(rc_setting(K.space(amp, S), S,
                                                                                         labels))}}
            elif ro == "S" and key not in out[t]:
                a = s_ans[key][ANY_HALF]
                if answers_sha(a) != answers_sha({"select": sel, "settings": LO.sdict(S)}):
                    raise SystemExit(f"{key}: phase 4's stored S is not the live menu's S")
                out[t][key] = {ANY_HALF: a}
    common = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_dfix_vreal", "drift": drift, "leakage_guard": guard}
    stem_meta = {"input": "the part's X-LANCE crop stem (xlance_g, crop-only), the crop's mix brought to levels.json "
                          "eval_mix_lufs_median and the stem given the same gain (step4_half)", "input_lufs": target,
                 "gains_db": {s_: v[2] for s_, v in stems.items()}, "input_hashes": {s_: v[3] for s_, v in stems.items()},
                 "floor_frame_share": floor["stem"], "stem_half_lufs": lufs["stem"],
                 "p2d_stems_median_lufs": p2d}
    amp_meta = {"input": "the part's own amp track (crop reference.wav), Wickerman ElecGtr2 and 3 each its own",
                "input_lufs": amp_level, "gains_db": {s_: v[1] for s_, v in amps.items()},
                "floor_frame_share": floor["amp"], "amp_half_lufs": lufs["amp"]}
    shas = {}
    for t in tags:
        m, kind, ro = DFIX_VREAL_TAGS[t]
        meta = {"stem": stem_meta, "amp": amp_meta}.get(kind, {})
        if m is not None:
            recs = models[m][1]
            meta = dict(meta, model=m, which="best", seeds=[r_["seed"] for r_ in recs],
                        model_sha256=[r_["model_sha256"]["best"] for r_ in recs], readout=ro)
        if ro == "sc":
            meta["constant"] = "D_fix's plugin training labels (P2b-wide24's ids), by (amp, class)"
        if ro == "RcG":
            meta = {"input": "none (a centre)", "rule": "rc_setting on every GOAT label of the amp and class; S where "
                                                         "none", "labels_used": rcg_n}
        if ro == "S":
            meta = {"input": "none (S)", "from": "vreal/answers/S.json (phase 4), asserted the live menu's S"}
        save(vreal_answers_path(t), {**common, "tag": t, **meta, "answers": out[t],
                                     "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        shas[t] = DS.hashlib_file(vreal_answers_path(t))
    st = {s_: round(statistics.fmean(v.values()), 2) for s_, v in lufs["stem"].items()}
    print(f"DFIX-VREAL PREDICT DONE: {len(dirs)} directions; mix target {target:.2f} LUFS; stems' half LUFS {st} "
          f"beside P2d's stored stems' median {p2d}; amp tracks at {amp_level}; RcG labels {rcg_n or '-'}; "
          f"guard {guard}")
    print(f"record in the ledger's pipeline-fix entry before rendering: \"{DFIX_VREAL_HASHES}\": "
          + json.dumps(shas, indent=1))


def cmd_dfix_vreal_render(args):
    """Read 3's renders, one shard (`vreal_render`): the declared tags only (`--names`, default all: four per-half
    tags x 132, RcG 66, S again 66 = 660), each answers file's sha256 first recorded in the ledger's DFIX_VREAL_HASHES;
    S's fresh renders recorded beside phase 4's stored render hashes."""
    e = require("phase_dfix_vreal")
    tags = dfix_vreal_tags(args.names)
    bad = dfix_vreal_unhashed(tags, e)
    if bad:
        raise SystemExit(f"renders refuse until the answers' hashes are in the ledger: {bad}")
    vreal_render(tags, args.shard, recheck={DFIX_VREAL_BASE: "S"})


def dfix_vreal_recheck(raw, stored):
    """S's fresh render hashes against phase 4's stored ones, per group. raw, stored {slug|amp: judge record}.
    -> [groups that differ or lack a stored hash]."""
    return sorted(k for k, r_ in raw.items() if (stored.get(k) or {}).get("render_sha256") != r_.get("render_sha256"))


def dfix_vreal_missing(judge, dirs, tags):
    """{tag: directions with no judge} over every declared direction (an incomplete row is not read)."""
    out = {t: sum(vreal_value(judge, t, u) is None for u in dirs) for t in tags}
    return {t: n for t, n in out.items() if n}


def dfix_vreal_read(judge, dirs, quiet):
    """Read 3's rows (zero renders) from judge {tag: {slug|amp: {half: {held: d}}}}: DFIX_VREAL_PAIRS by `vreal_rows`
    (base DFIX_VREAL_BASE: S not finite drops, a refusal scores as S), each band-clustered (7 bands) with its
    part-weighted mean and leave-one-band-out, clean and crunch apart, and without the `quiet` parts (the quiet-input
    side row). Refuses if any declared direction lacks a judge."""
    miss = dfix_vreal_missing(judge, dirs, sorted({t for _, a, b, _ in DFIX_VREAL_PAIRS for t in (a, b)}))
    if miss:
        raise SystemExit(f"incomplete: directions without a judge {miss}; no row is read")
    rows_out = {}
    for name, a, b, own in DFIX_VREAL_PAIRS:
        rows, cnt = vreal_rows(judge, a, b, dirs, own_inputs=own, base=DFIX_VREAL_BASE)
        res = {"a": a, "b": b, "own_inputs": own, "all": clustered(rows), **cnt}
        res["without_quiet_inputs"] = clustered([r for r in rows if not any(m in quiet for m in part_members(r[1]))
                                                 ]) if quiet else None
        for cls in ("clean", "crunch"):
            res[cls] = clustered([r for r in rows if all(PR.VREAL[m][1] == cls for m in part_members(r[1]))])
        rows_out[name] = res
    return rows_out


def cmd_dfix_vreal_report(args):
    """Read 3's report (zero renders), saved by `--label` (never overwritten: V-real is read once). In order, each a
    stop: the answers' hashes in the ledger; every judge record from today's answers; every declared direction
    judged; S's fresh renders identical to phase 4's (the differing groups printed); S's positive control on those
    renders (`s_positive_control`, as phase 4's report). Then DFIX_VREAL_PAIRS (`dfix_vreal_read`); the quiet-input
    side row from the stem inputs' floor-frame share (over FLOOR_SIDE_ROW in either half).
    -> vreal/report-<label>.json."""
    e = require("phase_dfix_vreal")
    if not args.label:
        raise SystemExit("name the report with --label")
    rp = out_dir() / VREAL_DIR / f"report-{args.label}.json"
    if rp.exists():
        raise SystemExit(f"{rp.name} exists: V-real is read once")
    bad = dfix_vreal_unhashed(list(DFIX_VREAL_TAGS), e)
    if bad:
        raise SystemExit(f"the answers' hashes are not the ledger's: {bad}")
    root, plan, drift, dirs, parts, ms = vreal_ctx()
    raw = {}
    for t in list(DFIX_VREAL_TAGS) + [DFIX_VREAL_P4, "S"]:
        raw[t] = {}
        for p in (out_dir() / VREAL_DIR / "judge" / t).glob("*.json"):
            r_ = json.loads(p.read_text())
            raw[t][f"{r_['slug']}|{r_['amp']}"] = r_
        asha = answers_sha(json.loads(vreal_answers_path(t).read_text())["answers"])
        stale = sorted(k for k, r_ in raw[t].items() if r_.get("answers_sha256") != asha)
        if stale:
            raise SystemExit(f"{t}: {len(stale)} judge records come from other answers")
    judge = {t: {k: r_["judge"] for k, r_ in v.items()} for t, v in raw.items()}
    miss = dfix_vreal_missing(judge, dirs, list(DFIX_VREAL_TAGS) + [DFIX_VREAL_P4])
    if miss:
        raise SystemExit(f"incomplete: directions without a judge {miss}; no row is read")
    differ = dfix_vreal_recheck(raw[DFIX_VREAL_BASE], raw["S"])
    if differ or len(raw[DFIX_VREAL_BASE]) != len(raw["S"]):
        raise SystemExit(f"S's fresh renders differ from phase 4's stored ones in {len(differ)} groups "
                         f"({len(raw[DFIX_VREAL_BASE])} fresh, {len(raw['S'])} stored): {differ}; no row is read")
    pc = s_positive_control(judge[DFIX_VREAL_BASE])
    if not pc["passes"] or pc["n"] != S_CONTROL_N:
        raise SystemExit(f"the S positive control fails ({pc}): no rows are read")
    stem = json.loads(vreal_answers_path("DV-P2b-dfix-stem").read_text())
    quiet = sorted(s_ for s_, v in stem["floor_frame_share"].items() if max(v.values()) > FLOOR_SIDE_ROW)
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_dfix_vreal", "label": args.label,
           "answers_sha256": (e.get(DFIX_VREAL_HASHES) or {}), "s_renders_identical_to_phase_4": len(raw["S"]),
           "positive_control_S": pc,
           "side_row_without": {"rule": f"stem inputs with more than {FLOOR_SIDE_ROW:.0%} of frames at the grid floor "
                                        "in either half (declared before the read)", "parts": quiet},
           "stem_half_lufs": stem["stem_half_lufs"], "p2d_stems_median_lufs": stem["p2d_stems_median_lufs"],
           "rcg_labels_used": json.loads(vreal_answers_path("DV-RcG").read_text())["labels_used"],
           "rows": dfix_vreal_read(judge, dirs, quiet)}
    for name, res in out["rows"].items():
        c = res["all"]
        iv = "" if c["lo90"] is None else f" [{c['lo90']:+.4f}, {c['hi90']:+.4f}]"
        print(f"{name}: {c['mean']:+.4f}{iv} ({c['clusters']} bands, {c['clusters_negative']} better; part-weighted "
              f"{c['part_weighted']:+.4f}, {c['parts_negative']} of {c['parts']} parts better; S dropped "
              f"{res['base_dropped']}, refused as S {res['refused_scored_as_S']})" if c["mean"] is not None
              else f"{name}: no rows")
        for cls in ("clean", "crunch"):
            z = res[cls]
            if z["mean"] is not None:
                print(f"    {cls}: {z['mean']:+.4f} ({z['clusters']} bands, {z['clusters_negative']} better; descriptive)")
        if c["leave_one_out"]:
            print("    leave one band out: " + ", ".join(f"{b} {v:+.4f}" for b, v in c["leave_one_out"].items()))
    print(f"S: {len(raw['S'])} groups' fresh renders identical to phase 4's; positive control max |ln ratio| "
          f"{pc['max_abs_log']} on {pc['n']}; quiet inputs {quiet}")
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save(rp, out)
    print("DFIX-VREAL-REPORT DONE")


# --- FT (declared 2026-11-02, ledger phase_ft): P2b-wide24 as pretraining, D_fix's real rows alone tune it ----------

FT_BASE = "P2b-ft"                   # the all-labels FT (V-real's, only after read 2's carry); FT_k `P2b-ft-k{k}`
FT_LR, FT_CAP = 1e-4, 100            # the declared rate and epoch cap; the fallbacks (`phase_ft_fallback`) below
FT_FALLBACK_LR, FT_FALLBACK_CAP = 3e-5, 300
FT_PATIENCE, FT_MIN_FALL, FT_SMOOTH, FT_EVERY = 15, 1e-3, 3, 5
FT_PRETRAIN = "P2b-wide24"           # W: its NS-best checkpoint per seed is FT's start
FTM_BASE = "P2b-ftm"                 # N1: FT with the heads outside the search masked on real rows
FTH_TAG = "P2b-fth"                  # N1's isolation: FT's stored answers, controls outside the search at S


def searched_heads(amp, S):
    """N1: the (continuous, switch, mic) masks of the heads `K.space(amp, S)` searches."""
    import numpy as np

    from learn import full_space as F
    from learn import knob_ceiling as K

    keys = {(d.module, d.key) for d in K.space(amp, S)}
    D = F.by_name()
    return tuple(np.array([(D[n].module, D[n].key) in keys for n in names], np.float32) for names in (F.CONT, F.SW, F.CAT))


def mask_searched(Y, rows, ms):
    """N1: on every real row (training or held), the heads the search did not move leave the loss, and the amp head too.
    Y: the data's encoded labels (`c, cm, s, sm, k, km, a`), changed in place; ms: `menu_S`."""
    for j, r in enumerate(rows):
        if "real" in r:
            c, s, k = searched_heads(r["amp"], ms[r["amp"]][r["cls"]][1])
            Y[1][j] *= c
            Y[3][j] *= s
            Y[5][j] *= k
            Y[6][j] = -100                     # a forced amp is no label for the amp head


def hold_outside_space(x, S, amp):
    """N1's readout: the searched controls from the answer, every other control at S (those heads keep W's training)."""
    from learn import full_space as F
    from learn import knob_ceiling as K

    y = F.sections_on(dict(S))
    for d in K.space(amp, S):
        k = (d.module, d.key)
        if k in x:
            y[k] = x[k]
    return y


def ft_name(k, inner=False, lr=FT_LR, cap=FT_CAP, base=FT_BASE):
    """FT's run names: `P2b-ft` (every label), `P2b-ft-k{k}` (fold k out), `P2b-ft-k{k}-inner` (k's epoch choice;
    a fallback's inner runs `-lr3e-05` and/or `-cap300` after it, so the declared ones are kept). `base` N1's."""
    if k is None:
        if inner:
            raise SystemExit("an inner run needs --real-fold")
        return base
    if k not in range(REAL_FOLDS):
        raise SystemExit(f"--real-fold in 0..{REAL_FOLDS - 1}")
    if not inner:
        return f"{base}-k{k}"
    return f"{base}-k{k}-inner" + ("" if lr == FT_LR else f"-lr{lr:g}") + ("" if cap == FT_CAP else f"-cap{cap}")


def ft_rows_of(brecs, by_unit, folds, grecs, gunits, k, inner, label_of=None):
    """FT's real rows (`dfix_rows_of`): FT_k's are D_fix_k's (fold k held, logged only); k's inner run drops fold k's
    records entirely and holds fold j = (k + 1) mod 4 (its validation). -> (training rows, held rows, counts)."""
    if not inner:
        return dfix_rows_of(brecs, by_unit, folds, grecs, gunits, k, label_of)
    b = [r for r in brecs if folds[by_unit[r["unit"]]["di"]] != k]
    g = [r for r in grecs if gunits[r["unit"]]["fold"] != k]
    return dfix_rows_of(b, by_unit, folds, g, gunits, (k + 1) % REAL_FOLDS, label_of)


def ft_real_rows(k, inner):
    brecs, by_unit, folds = real_labels(2)
    grecs, gunits, _ = goat_labels()
    return ft_rows_of(brecs, by_unit, folds, grecs, gunits, k, inner)


def ft_inner_E(log, track="real_val"):
    """An inner run's E as declared: the first argmin of the trailing moving average of `track` over the logged
    epochs (finite values only), + 1. (`fit`'s own best only moves on a fall of FT_MIN_FALL: the stop rule.)"""
    v = [(r_[f"{track}_smoothed"], r_["epoch"]) for r_ in log
         if f"{track}_smoothed" in r_ and math.isfinite(r_[f"{track}_smoothed"])]
    if not v:
        raise SystemExit("no finite smoothed validation loss")
    return min(v)[1] + 1                               # ties: the first epoch


def ft_fallback_refusal(get, lr, cap):
    """Why FT_k may not train at (lr, cap) yet, or None. `get(lr, cap)` -> that setting's 8 inner records or None.
    The declared order: at the base rate the rate rule (4+ of 8 with E <= 2) first, then the cap rule (4+ of 8 at the
    cap 100); each fallback at most once and only when its rule fired on the setting before it."""
    def fired(recs, rule):
        return sum(1 for r_ in recs if (ft_inner_E(r_["log"]) <= 2 if rule == "rate" else r_["at_cap"])) >= 4

    steps = [(FT_LR, FT_CAP)]
    base = get(FT_LR, FT_CAP)
    if base is None:
        return "the 8 inner runs at the declared rate and cap are not all done"
    cur = (FT_LR, FT_CAP)
    if fired(base, "rate"):
        cur = (FT_FALLBACK_LR, FT_CAP)
        steps.append(cur)
        if get(*cur) is None:
            return f"the rate rule fired: the 8 inner runs at lr {FT_FALLBACK_LR:g} are not all done"
    if fired(get(*cur), "cap"):
        cur = (cur[0], FT_FALLBACK_CAP)
        steps.append(cur)
        if get(*cur) is None:
            return f"the cap rule fired: the 8 inner runs at cap {FT_FALLBACK_CAP} are not all done"
    if (lr, cap) != cur:
        return f"the settled setting is lr {cur[0]:g}, cap {cur[1]} (steps {steps}), not lr {lr:g}, cap {cap}"
    return None


def ft_epoch_of(inner_recs):
    """The epoch count FT trains for: one inner run's E (from its log, `ft_inner_E`), or the median of several,
    rounded half up."""
    es = sorted(ft_inner_E(r["log"]) for r in inner_recs)
    if not es:
        raise SystemExit("no inner runs")
    m = (es[(len(es) - 1) // 2] + es[len(es) // 2]) / 2
    return int(math.floor(m + 0.5))


def ft_rate(args):
    """The declared rate and cap, or a fallback's once `phase_ft_fallback` records it. -> (lr, cap)."""
    lr = FT_LR if args.ft_lr is None else args.ft_lr
    cap = FT_CAP if args.ft_cap is None else args.ft_cap
    if lr not in (FT_LR, FT_FALLBACK_LR) or cap not in (FT_CAP, FT_FALLBACK_CAP):
        raise SystemExit(f"--ft-lr in {(FT_LR, FT_FALLBACK_LR)}, --ft-cap in {(FT_CAP, FT_FALLBACK_CAP)}")
    if (lr, cap) != (FT_LR, FT_CAP):
        require("phase_ft_fallback")
    return lr, cap


def ft_layout(n_plugin_tr, n_real, n_rows, n_real_held):
    """FT's index sets in `with_rows`' layout (plugin training, real training, plugin held, real held).
    -> (real training, plugin held (NS), real held)."""
    import numpy as np

    return (np.arange(n_plugin_tr, n_plugin_tr + n_real), np.arange(n_plugin_tr + n_real, n_rows - n_real_held),
            np.arange(n_rows - n_real_held, n_rows))


def ft_start_state(seed):
    """W's NS-best state for `seed` (hash checked by `load_run`). -> (state, W's run record)."""
    net, rec = load_run(FT_PRETRAIN, seed, "best")
    return {k: t.detach().cpu().clone() for k, t in net.state_dict().items()}, rec


def ft_inner_init_refusal(inners, w_best_of):
    """The inner runs whose start state is not their own seed's W best (`w_best_of(seed)` -> sha256); the all-labels
    FT takes all eight inner runs, both seeds. -> [(fold, seed)]."""
    return [(r_["real_fold"], r_["seed"]) for r_ in inners if r_["init"]["sha256"] != w_best_of(r_["seed"])]


def cmd_train_ft(args):
    """One FT run (demucs-venv): `--inner --real-fold k` (k's epoch choice: from W on the folds other than k and j,
    fold j's real loss each epoch, the trailing 3-epoch average's argmin + 1 = E, patience 15); `--real-fold k`
    (FT_k: from W on the folds other than k for its inner run's E, the state after E epochs read); neither (the
    all-labels FT, the median of the eight inner E's; only after `phase_ft_carry`)."""
    import numpy as np
    import torch

    from learn import direct_stems as DS

    require("phase_ft")
    k, inner, seed = args.real_fold, bool(args.inner), args.seed
    masked = bool(getattr(args, "masked", False))
    base = FTM_BASE if masked else FT_BASE
    if masked:
        require("phase_night2")
        if k is None:
            raise SystemExit("N1 runs FT_k and its inner runs only")
    if k is None:
        require("phase_ft_carry")
    if seed not in SEEDS:
        raise SystemExit(f"--seed in {SEEDS}")
    lr, cap = ft_rate(args)
    name = ft_name(k, inner, lr, cap, base)            # FT_k's name is one at any setting; its (lr, cap) recorded
    od = out_dir() / "runs"
    rp = od / f"{name}-{seed}.json"
    if rp.exists():
        print(f"{rp.name} exists: nothing to do")
        return
    if inner:
        epochs = cap
    else:
        def inner_set(lr_, cap_):
            ps = [od / f"{ft_name(q, True, lr_, cap_, base)}-{sd}.json" for q in range(REAL_FOLDS) for sd in SEEDS]
            return [json.loads(q.read_text()) for q in ps] if all(q.exists() for q in ps) else None

        why = ("the 8 inner runs are not all done" if inner_set(lr, cap) is None else None) if masked \
            else ft_fallback_refusal(inner_set, lr, cap)
        if why:
            raise SystemExit(f"{name}: {why}")
        allin = inner_set(lr, cap)
        if any(r_["lr"] != lr or r_["cap"] != cap for r_ in allin):
            raise SystemExit("the inner runs used another rate or cap")
        inners = [r_ for r_ in allin if k is None or (r_["real_fold"], r_["seed"]) == (k, seed)]
        epochs = ft_epoch_of(inners)
    e = require("phase_3")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    init, wrec = ft_start_state(seed)
    if not inner and ft_inner_init_refusal(inners, lambda sd: json.loads((od / f"{FT_PRETRAIN}-{sd}.json")
                                                                         .read_text())["model_sha256"]["best"]):
        raise SystemExit("an inner run started from another W state than its seed's")
    pa = argparse.Namespace(rung="b", fold=None, frac=1.0, sections=1.0, pc=False, pcsz=False, aug=False)
    tr, held, held_name, rows = plugin_rows(kept, sp, pa, lambda ids: rung_rows(kept, rend, ids))
    if tr != [i for i in wrec["train_ids"] if i < REAL_ROW0]:
        raise SystemExit(f"{FT_PRETRAIN}-{seed}: trained on other plugin rows than FT's")
    doubled = doubled_ids() if dropped["doubles"] == "fixed" else frozenset()
    rrows, real_held, info = ft_real_rows(k, inner)
    plugin_tr = tr
    tr, rows = with_rows(tr, rows, rrows)
    rows = rows + [dict(r, held=True) for r in real_held]
    data = DfixData(rows, rung_path(croot, "b", doubled), set(plugin_tr), {r["i"] for r in rrows}, 1.0)
    if masked:
        mask_searched(data.Y, rows, A_menu_S())
    if not inner:                                      # every unit loaded: D_fix_k's (or D_fix's) inputs exactly
        ref = dfix_run_name(k)
        want = json.loads((od / f"{ref}-{seed}.json").read_text())["dfix"]["inputs_sha256"]
        if data.inputs_sha256 != want:
            raise SystemExit(f"{name}: real-row inputs differ from {ref}'s ({data.inputs_sha256[:8]} vs {want[:8]})")
    ti, hi, rh = ft_layout(len(plugin_tr), len(rrows), len(rows), len(real_held))
    if not all("real" in rows[j] and not rows[j].get("held") for j in ti):
        raise SystemExit("a plugin or held row in FT's training rows")
    held_units = {r["real"] for r in real_held}
    if held_units & {r["real"] for r in rrows}:
        raise SystemExit("a held unit among the training rows")
    if inner:                                          # no fold-k unit anywhere; every held unit is fold j's
        brecs, by_unit, folds = real_labels(2)
        _, gunits, _ = goat_labels()

        def fold_of(u):
            return gunits[u]["fold"] if u in gunits else folds[by_unit[u]["di"]]

        if any(fold_of(r["real"]) == k for r in rrows + real_held) \
                or any(fold_of(u) != (k + 1) % REAL_FOLDS for u in held_units):
            raise SystemExit(f"{name}: fold {k} in its rows, or a held row outside fold {(k + 1) % REAL_FOLDS}")
    sub = np.sort(np.random.default_rng(SUBSET_SEED).choice(ti, min(SUBSET_N, len(ti)), replace=False))
    dev = device()
    torch.set_num_threads(2)
    log, t0 = [], time.time()
    start = None
    if inner:
        from learn import full_space as F

        net0 = F.build_net()
        net0.load_state_dict(init)
        start = head_losses(net0.to(dev), data, rh, dev)["total"]
        watch = {"train_real": sub, "real_val": rh}
        net, final, best_state, best_ep, best = fit(data, ti, watch, "real_val", seed, dev, log, epochs, every=1,
                                                    patience=FT_PATIENCE, min_gain=FT_MIN_FALL, init=init, lr=lr,
                                                    smooth=FT_SMOOTH)
    else:
        watch = {"train_real": sub, held_name: hi}
        if len(rh):                                    # fold k's real loss: logged, never `fit`'s tracked set
            watch["real_held"] = rh
        net, final, best_state, best_ep, best = fit(data, ti, watch, None, seed, dev, log, epochs, every=FT_EVERY,
                                                    init=init, lr=lr)
    out = {"plan": PLAN, "test": name, "ledger": f"{LEDGER_ID} {'phase_night2' if masked else 'phase_ft'}", "rung": "b",
           "seed": seed, "real_fold": k, "masked": masked, "inner": inner, "lr": lr, "cap": cap, "init": {"run": f"{FT_PRETRAIN}-{seed}", "which": "best",
                                                          "sha256": wrec["model_sha256"]["best"]},
           "train_ids": plugin_tr + [r["i"] for r in rrows], "ft_train_ids": [r["i"] for r in rrows],
           "held": held_name, "held_ids": held, "real_held_ids": [r["i"] for r in real_held],
           "real_held_units": sorted(held_units), "epochs_run": log[-1]["epoch"] + 1, "steps": log[-1]["steps"],
           "dfix": dict(info, fold=k, inner=inner, plugin_train=len(plugin_tr), inputs_sha256=data.inputs_sha256,
                        target_lufs=data.target_lufs, share=1.0),
           "backing_variants": getattr(data, "counts", None), "log": log,
           "minutes": round((time.time() - t0) / 60, 1), "device": str(dev), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    od.mkdir(parents=True, exist_ok=True)
    if inner:
        out["dfix"]["val_fold"] = (k + 1) % REAL_FOLDS
        out.update(E=ft_inner_E(log), stop_best_epoch=best_ep, best_smoothed_val=best, start_real_val=start,
                   at_cap=log[-1]["epoch"] + 1 == cap and best_ep >= cap - FT_PATIENCE)
    else:
        if not math.isfinite(log[-1]["train_real"]["total"]):
            raise SystemExit(f"{name}: a non-finite training loss at its last epoch")
        mp = od / f"{name}-{seed}-final.pt"
        torch.save(final, mp)
        sha = DS.hashlib_file(mp)
        out.update(E=epochs, read_checkpoint=f"the state after {epochs} epochs (final)",
                   models={"final": mp.name, "best": mp.name}, model_sha256={"final": sha, "best": sha})
    save(rp, out)
    print(f"TRAIN-FT DONE {name} {seed}: {out['epochs_run']} epochs, E {out['E']}; {out['minutes']} min")


def ft_read_check(rec):
    """FT's read guard: a read FT model is an FT_k or all-labels run (never an inner run) whose read checkpoint is the
    state after its E epochs: `load_run`'s "best" must be that same file and hash."""
    if not rec["test"].startswith(FT_BASE):
        return
    if rec.get("inner") or rec["models"]["best"] != rec["models"]["final"] \
            or rec["model_sha256"]["best"] != rec["model_sha256"]["final"] or rec.get("E") != rec.get("epochs_run"):
        raise SystemExit(f"{rec['test']}-{rec['seed']}: not FT's read checkpoint (the state after E epochs)")


def ft_recheck_pick(files, n, key):
    """The recheck's seeded pick of n stored judge files."""
    import random

    return sorted(random.Random(f"{DFIX_SEED}|ft-recheck|{key}").sample(sorted(files), min(n, len(files))))


def cmd_ft_recheck(args):
    """FT's render check before read 2 (`phase_ft`): 5 stored D_fix BKS judge files and 5 GOAT ones (both halves:
    20 renders) rendered again exactly as `real-render` and `goat-render` render them, the hashes compared.
    -> real/recheck-ft.json; refuses (after saving) on any mismatch."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    require("phase_ft")
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    bans = json.loads((out_dir() / REAL_DIR / "answers" / "P2b-dfix.json").read_text())
    gans = json.loads((out_dir() / GOAT_DIR / "answers" / "P2b-dfix.json").read_text())["answers"]
    parts = {p_["unit"]: p_ for p_ in bans["parts"]}
    gunits = {p_["unit"]: p_ for p_ in goat_read_units()}
    rows = []
    for kind, jd, ans, by in (("bks", out_dir() / REAL_DIR / "judge" / "P2b-dfix", bans["answers"], parts),
                              ("goat", out_dir() / GOAT_DIR / "judge" / "P2b-dfix", gans, gunits)):
        for f in ft_recheck_pick([q.name for q in jd.glob("*.json")], 5, kind):
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            old = json.loads((jd / f).read_text())
            if old["unit"] not in by:
                raise SystemExit(f"{jd / f}: its unit is no longer a read unit")
            prt = by[old["unit"]]
            key = real_key(prt, old["amp"])
            if old["answers_sha256"] != answers_sha(ans if kind == "bks" else {key: ans[key]}):
                raise SystemExit(f"{jd / f}: rendered from other answers than the stored file holds now")
            di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
            for search, a in sorted(ans[key].items()):
                st = LO.tdict(a["settings"])
                y = np.asarray(AM.fresh_render(CB.new_renderer, di32, a["select"], st, st), np.float64)[trim[0]:trim[1]]
                new = AM.audio_sha(y)
                rows.append({"kind": kind, "file": f, "half": search, "stored": old["render_sha256"][search],
                             "new": new, "same": new == old["render_sha256"][search]})
    miss = [r_ for r_ in rows if not r_["same"]]
    save(out_dir() / REAL_DIR / "recheck-ft.json", {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_ft", "rows": rows,
                                                     "mismatched": len(miss), "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"FT-RECHECK: {len(rows) - len(miss)} of {len(rows)} renders identical", flush=True)
    if miss:
        raise SystemExit(f"FT-RECHECK: {len(miss)} renders differ from the stored ones")
    print("FT-RECHECK DONE")


# --- FT to V-real (phase_ft's map, carried by phase_ft_carry): the second candidate on V-real-11, read 3's rules ----

FT_VREAL_TAG = "FV-P2b-ft-stem"     # the all-labels FT (both seeds pooled, its read checkpoint) on read 3's stems
FT_VREAL_RECHECK = "S-recheck-ft"   # FT_VREAL_RECHECK_N of phase 4's S groups rendered again, asserted identical
FT_VREAL_RECHECK_N = 10             # 10 groups x 2 renders (one priming each) = the declared 20
FT_VREAL_HASHES = "phase_ft_vreal_answers"          # the ledger key: {tag: sha256 of vreal/answers/<tag>.json}
FT_VREAL_TAGS = (FT_VREAL_TAG, FT_VREAL_RECHECK)
FT_VREAL_STORED = (DFIX_VREAL_BASE, "DV-P2b-dfix-stem", "DV-RcG")   # F41's stored renders: zero new
FT_VREAL_PAIRS = (                                  # (row, a, b): every row's base is DFIX_VREAL_BASE (F41's S)
    ("FT - S (primary)", FT_VREAL_TAG, DFIX_VREAL_BASE),
    ("FT - D_fix", FT_VREAL_TAG, "DV-P2b-dfix-stem"),
    ("FT - RcG", FT_VREAL_TAG, "DV-RcG"),
)
FT_VREAL_INPUT_KEYS = ("input_lufs", "gains_db", "input_hashes", "floor_frame_share", "stem_half_lufs")
FT_VREAL_F41 = ("report-dfix-vreal.json", (("D_fix - S (primary)", "DV-P2b-dfix-stem", DFIX_VREAL_BASE),
                                           ("D_fix - RcG", "DV-P2b-dfix-stem", "DV-RcG")))   # F41's rows, recomputed


def ft_vreal_recheck_groups(groups):
    """The seeded FT_VREAL_RECHECK_N of V-real's (part, amp) S groups rendered again before FT's rows are read."""
    import random

    return sorted(random.Random(f"{DFIX_SEED}|ft-vreal-recheck").sample(sorted(groups),
                                                                         min(FT_VREAL_RECHECK_N, len(groups))))


def ft_vreal_input_drift(mine, stored):
    """FT's stem inputs against read 3's (F41's DV-P2b-dfix-stem answers file): the declared same inputs, so every
    FT_VREAL_INPUT_KEYS value must be equal. -> [keys that differ]."""
    return [k for k in FT_VREAL_INPUT_KEYS if mine.get(k) != stored.get(k)]


def two_look_interval(per_cluster, looks=2, level=0.90):
    """The Bonferroni interval for a row read on the `looks`-th candidate: the cluster t interval at 1 - (1 - level)
    / looks (two looks at 90%: 95%), df = clusters - 1. -> (lo, hi) or (None, None)."""
    from scipy import stats

    v = list(per_cluster.values())
    if len(v) < 2:
        return None, None
    m = statistics.fmean(v)
    half = stats.t.ppf(1 - (1 - level) / looks / 2, len(v) - 1) * statistics.stdev(v) / math.sqrt(len(v))
    return m - half, m + half


def ft_vreal_load():
    """The all-labels FT, both seeds, at its read checkpoint (`ft_read_check`), with its declared provenance: one
    training set; trained for the median inner E (cap-300 inner runs); started from W's best; its training ids a
    subset of D_fix's and its real-row inputs D_fix's. -> (nets, run records)."""
    od = out_dir() / "runs"
    nets, recs = [], []
    for sd in SEEDS:
        net, rec = load_run(FT_BASE, sd, "best")
        ft_read_check(rec)
        if rec.get("inner") or rec.get("real_fold") is not None:
            raise SystemExit(f"{FT_BASE}-{sd}: not the all-labels run")
        nets.append(net)
        recs.append(rec)
    if any(r_["train_ids"] != recs[0]["train_ids"] or r_["held_ids"] != recs[0]["held_ids"] for r_ in recs):
        raise SystemExit(f"{FT_BASE}: both seeds of one training set")
    if any((r_["lr"], r_["cap"]) != (recs[0]["lr"], recs[0]["cap"]) for r_ in recs):
        raise SystemExit(f"{FT_BASE}: both seeds at one rate and cap")

    def inner_set(lr_, cap_):
        ps = [od / f"{ft_name(k, True, lr_, cap_)}-{sd}.json" for k in range(REAL_FOLDS) for sd in SEEDS]
        return [json.loads(q.read_text()) for q in ps] if all(q.exists() for q in ps) else None

    return nets, ft_vreal_provenance(recs, inner_set, lambda sd: json.loads((od / f"{FT_PRETRAIN}-{sd}.json")
                                                                            .read_text()),
                                     lambda sd: json.loads((od / f"{dfix_run_name(None)}-{sd}.json").read_text()))


def ft_vreal_provenance(recs, inner_set, w_of, d_of):
    """The all-labels FT runs' declared provenance (refuses on any miss): their (lr, cap) the settled one
    (`ft_fallback_refusal` on inner_set(lr, cap) -> the 8 inner records or None) and each inner run started from its
    own seed's W; E the inner median; each run started from its seed's W best, on W's plugin and NS-held ids, and on
    exactly D_fix's training labels and real-row inputs (plugin + BKS + GOAT). w_of(seed), d_of(seed) -> run
    records. -> recs."""
    lr, cap = recs[0]["lr"], recs[0]["cap"]
    why = ft_fallback_refusal(inner_set, lr, cap)
    if why:
        raise SystemExit(f"{FT_BASE}: {why}")
    inners = inner_set(lr, cap)
    if ft_inner_init_refusal(inners, lambda sd: w_of(sd)["model_sha256"]["best"]):
        raise SystemExit(f"{FT_BASE}: the inner runs are not all eight, each from its own seed's W")
    want = ft_epoch_of(inners)
    for r_ in recs:
        sd = r_["seed"]
        w, d = w_of(sd), d_of(sd)
        if r_["E"] != want:
            raise SystemExit(f"{FT_BASE}-{sd}: trained {r_['E']} epochs, not the inner median {want}")
        if r_["init"]["sha256"] != w["model_sha256"]["best"]:
            raise SystemExit(f"{FT_BASE}-{sd}: not started from {FT_PRETRAIN}'s best")
        if [i for i in r_["train_ids"] if i < REAL_ROW0] != w["train_ids"] or r_["held_ids"] != w["held_ids"]:
            raise SystemExit(f"{FT_BASE}-{sd}: plugin or held rows other than {FT_PRETRAIN}'s")
        if set(r_["train_ids"]) != set(d["train_ids"]) or r_["held_ids"] != d["held_ids"] \
                or set(r_["ft_train_ids"]) != {i for i in d["train_ids"] if i >= REAL_ROW0} \
                or r_["dfix"]["inputs_sha256"] != d["dfix"]["inputs_sha256"]:
            raise SystemExit(f"{FT_BASE}-{sd}: not D_fix's training labels and inputs")
    return recs


def ft_vreal_unhashed(entry):
    """FT's answers files and F41's stored ones whose sha256 is not the ledger's (FT_VREAL_HASHES, DFIX_VREAL_HASHES).
    -> [problems]."""
    from learn import direct_stems as DS

    out = dfix_vreal_unhashed(list(FT_VREAL_STORED), entry)
    want = (entry or {}).get(FT_VREAL_HASHES) or {}
    for t in FT_VREAL_TAGS:
        p = vreal_answers_path(t)
        if not p.exists():
            out.append(f"{t}: no answers file")
        elif want.get(t) != DS.hashlib_file(p):
            out.append(f"{t}: sha256 {DS.hashlib_file(p)[:12]} not recorded under {FT_VREAL_HASHES}")
    return out


def cmd_ft_vreal_predict(args):
    """FT's answers on V-real-11 (zero renders; demucs-venv), after the leakage guard on FT's own training inputs:
    the all-labels FT (`ft_vreal_load`) per search half on the class's S (`F.answer_settings`, plain readout) on read
    3's exact inputs (`vreal_stem_input`, `step4_half`, `vreal_model_input`; asserted equal to F41's recorded ones),
    and FT_VREAL_RECHECK: phase 4's S answers on the seeded recheck groups (asserted the live menu's S). Answers
    already in the ledger are never rewritten. -> vreal/answers/<tag>.json; prints the sha256s for FT_VREAL_HASHES."""
    from learn import cc_build as CB
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import trusted_data as T

    require("phase_ft")
    e = require("phase_ft_carry")
    if any(t in (e.get(FT_VREAL_HASHES) or {}) for t in FT_VREAL_TAGS):
        raise SystemExit("FT's V-real answers are already recorded in the ledger (V-real is read once)")
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    inv = CB.cc_inventory()
    guard = dfix_vreal_leaks(kept, inv, FT_BASE)
    root, plan, drift, dirs, parts, ms = vreal_ctx()
    nets, recs = ft_vreal_load()
    target = vreal_mix_target()
    man = DS._load(DS.stems_manifest_path(DS.ROOT, T.SEP))
    stems = {slug: vreal_stem_input(man, slug, parts[slug], target) for slug in sorted({d[0] for d in dirs})}
    out, floor, lufs = {}, {}, {}
    for slug, amp, search, _ in dirs:
        cls = PR.VREAL[slug][1]
        sel, S = ms[amp][cls]
        stem, mix, g, _ = stems[slug]
        s8, _, ls, _ = DS.step4_half(stem, mix, search, g)
        floor.setdefault(slug, {})[search] = floor_share(s8)
        lufs.setdefault(slug, {})[search] = ls
        x, c = vreal_model_input(s8, ls, search, amp, cls)
        r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
        st = F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"])
        out.setdefault(f"{slug}|{amp}", {})[search] = {"select": sel, "settings": LO.sdict(st)}
    meta = {"input": "read 3's: the part's X-LANCE crop stem, the crop's mix brought to levels.json "
                     "eval_mix_lufs_median and the stem given the same gain (step4_half)", "input_lufs": target,
            "gains_db": {s_: v[2] for s_, v in stems.items()}, "input_hashes": {s_: v[3] for s_, v in stems.items()},
            "floor_frame_share": floor, "stem_half_lufs": lufs}
    f41 = json.loads(vreal_answers_path("DV-P2b-dfix-stem").read_text())
    drift_keys = ft_vreal_input_drift(json.loads(json.dumps(meta, default=str)), f41)
    if drift_keys:
        raise SystemExit(f"FT's V-real inputs differ from read 3's in {drift_keys}: not the declared inputs")
    s_ans = json.loads(vreal_answers_path("S").read_text())["answers"]
    pick = ft_vreal_recheck_groups({f"{s_}|{a}" for s_, a, _, _ in dirs})
    recheck = {}
    for key in pick:
        slug, amp = key.split("|")
        sel, S = ms[amp][PR.VREAL[slug][1]]
        if answers_sha(s_ans[key][ANY_HALF]) != answers_sha({"select": sel, "settings": LO.sdict(S)}):
            raise SystemExit(f"{key}: phase 4's stored S is not the live menu's S")
        recheck[key] = {ANY_HALF: s_ans[key][ANY_HALF]}
    common = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_ft_carry", "drift": drift, "leakage_guard": guard}
    save(vreal_answers_path(FT_VREAL_TAG), {
        **common, "tag": FT_VREAL_TAG, **meta, "model": FT_BASE, "which": "the state after E epochs",
        "E": recs[0]["E"], "seeds": [r_["seed"] for r_ in recs],
        "model_sha256": [r_["model_sha256"]["best"] for r_ in recs], "readout": "plain", "answers": out,
        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    save(vreal_answers_path(FT_VREAL_RECHECK), {
        **common, "tag": FT_VREAL_RECHECK, "input": "none (S)",
        "from": "vreal/answers/S.json (phase 4) on the seeded recheck groups, asserted the live menu's S",
        "answers": recheck, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    shas = {t: DS.hashlib_file(vreal_answers_path(t)) for t in FT_VREAL_TAGS}
    print(f"FT-VREAL PREDICT DONE: {len(dirs)} directions; inputs identical to read 3's; recheck groups {pick}; "
          f"guard {guard}")
    print(f"record in the ledger's pipeline-fix entry before rendering: \"{FT_VREAL_HASHES}\": "
          + json.dumps(shas, indent=1))


def cmd_ft_vreal_render(args):
    """FT's V-real renders, one shard (`vreal_render`): FT on every direction (132) and FT_VREAL_RECHECK's groups
    (20), hashes recorded beside phase 4's stored S; every answers file's sha256 in the ledger first."""
    e = require("phase_ft_carry")
    bad = ft_vreal_unhashed(e)
    if bad:
        raise SystemExit(f"renders refuse until the answers' hashes are in the ledger: {bad}")
    vreal_render(list(FT_VREAL_TAGS), args.shard, recheck={FT_VREAL_RECHECK: "S"})


def cmd_ft_vreal_report(args):
    """FT's V-real report (zero renders), saved by `--label`, never overwritten. In order, each a stop: every answers
    hash the ledger's (FT's and F41's stored tags); every judge record from today's answers; every declared direction
    judged; the recheck's groups all rendered and identical to phase 4's. Then FT_VREAL_PAIRS by `vreal_rows` (base
    F41's S, band-clustered, part-weighted, leave-one-band-out, clean and crunch apart, the quiet-input side row as
    read 3's), the primary with its two-look 95% interval beside. -> vreal/report-<label>.json."""
    e = require("phase_ft_carry")
    if not args.label:
        raise SystemExit("name the report with --label")
    rp = out_dir() / VREAL_DIR / f"report-{args.label}.json"
    if rp.exists():
        raise SystemExit(f"{rp.name} exists: V-real is read once")
    bad = ft_vreal_unhashed(e)
    if bad:
        raise SystemExit(f"the answers' hashes are not the ledger's: {bad}")
    root, plan, drift, dirs, parts, ms = vreal_ctx()
    raw = {}
    for t in (*FT_VREAL_TAGS, *FT_VREAL_STORED, "S"):
        raw[t] = {}
        for p in (out_dir() / VREAL_DIR / "judge" / t).glob("*.json"):
            r_ = json.loads(p.read_text())
            raw[t][f"{r_['slug']}|{r_['amp']}"] = r_
        asha = answers_sha(json.loads(vreal_answers_path(t).read_text())["answers"])
        stale = sorted(k for k, r_ in raw[t].items() if r_.get("answers_sha256") != asha)
        if stale:
            raise SystemExit(f"{t}: {len(stale)} judge records come from other answers")
    judge = {t: {k: r_["judge"] for k, r_ in v.items()} for t, v in raw.items()}
    miss = dfix_vreal_missing(judge, dirs, [FT_VREAL_TAG, *FT_VREAL_STORED])
    if miss:
        raise SystemExit(f"incomplete: directions without a judge {miss}; no row is read")
    want = ft_vreal_recheck_groups({f"{s_}|{a}" for s_, a, _, _ in dirs})
    differ = dfix_vreal_recheck(raw[FT_VREAL_RECHECK], raw["S"])
    if sorted(raw[FT_VREAL_RECHECK]) != want or differ:
        raise SystemExit(f"the recheck's S renders: {len(raw[FT_VREAL_RECHECK])} of {len(want)} groups, differing "
                         f"from phase 4's in {differ}; no row is read")
    pc = s_positive_control(judge[DFIX_VREAL_BASE])
    if not pc["passes"] or pc["n"] != S_CONTROL_N:
        raise SystemExit(f"the S positive control fails ({pc}): no rows are read")
    f41p = out_dir() / VREAL_DIR / FT_VREAL_F41[0]
    f41 = json.loads(f41p.read_text())["rows"] if f41p.exists() else {}
    for name, a, b in FT_VREAL_F41[1]:                 # the comparators are F41's stored renders: its rows again
        m = clustered(vreal_rows(judge, a, b, dirs, base=DFIX_VREAL_BASE)[0])["mean"]
        if name not in f41 or m is None or not math.isclose(m, f41[name]["all"]["mean"], abs_tol=1e-12):
            raise SystemExit(f"{name}: {m} from today's judge files is not F41's {f41p.name}; no row is read")
    stem = json.loads(vreal_answers_path(FT_VREAL_TAG).read_text())
    quiet = sorted(s_ for s_, v in stem["floor_frame_share"].items() if max(v.values()) > FLOOR_SIDE_ROW)
    rows_out = {}
    for name, a, b in FT_VREAL_PAIRS:
        rows, cnt = vreal_rows(judge, a, b, dirs, base=DFIX_VREAL_BASE)
        res = {"a": a, "b": b, "all": clustered(rows), **cnt}
        res["without_quiet_inputs"] = clustered([r for r in rows if not any(m in quiet for m in part_members(r[1]))
                                                 ]) if quiet else None
        for cls in ("clean", "crunch"):
            res[cls] = clustered([r for r in rows if all(PR.VREAL[m][1] == cls for m in part_members(r[1]))])
        rows_out[name] = res
    prim = rows_out[FT_VREAL_PAIRS[0][0]]
    prim["two_look_95"] = two_look_interval(prim["all"]["per_cluster"])
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_ft_carry", "label": args.label,
           "answers_sha256": {**(e.get(FT_VREAL_HASHES) or {}),
                              **{t: (e.get(DFIX_VREAL_HASHES) or {}).get(t) for t in FT_VREAL_STORED}},
           "s_recheck_groups_identical": len(want),
           "positive_control_S": pc,
           "side_row_without": {"rule": f"stem inputs with more than {FLOOR_SIDE_ROW:.0%} of frames at the grid floor "
                                        "in either half (read 3's rule)", "parts": quiet},
           "selection": "the second candidate read on V-real (D_fix was the first, F41); any choice between FT and "
                        "D_fix from FT - D_fix here is selection-contaminated",
           "rows": rows_out}
    for name, res in rows_out.items():
        c = res["all"]
        iv = "" if c["lo90"] is None else f" [{c['lo90']:+.4f}, {c['hi90']:+.4f}]"
        print(f"{name}: {c['mean']:+.4f}{iv} ({c['clusters']} bands, {c['clusters_negative']} better; part-weighted "
              f"{c['part_weighted']:+.4f}, {c['parts_negative']} of {c['parts']} parts better; S dropped "
              f"{res['base_dropped']}, refused as S {res['refused_scored_as_S']})" if c["mean"] is not None
              else f"{name}: no rows")
        if "two_look_95" in res and res["two_look_95"][0] is not None:
            lo, hi = res["two_look_95"]
            print(f"    two-look (Bonferroni) 95%: [{lo:+.4f}, {hi:+.4f}]")
        for cls in ("clean", "crunch"):
            z = res[cls]
            if z["mean"] is not None:
                print(f"    {cls}: {z['mean']:+.4f} ({z['clusters']} bands, {z['clusters_negative']} better; descriptive)")
        if res["without_quiet_inputs"] and res["without_quiet_inputs"]["mean"] is not None:
            print(f"    without quiet inputs {quiet}: {res['without_quiet_inputs']['mean']:+.4f}")
        if c["leave_one_out"]:
            print("    leave one band out: " + ", ".join(f"{b} {v:+.4f}" for b, v in c["leave_one_out"].items()))
    print(f"S: {len(want)} recheck groups' renders identical to phase 4's; quiet inputs {quiet}")
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save(rp, out)
    print("FT-VREAL-REPORT DONE")


# --- FT's score by control group (ledger phase_ft_groups; descriptive, BKS only) -----------------------------------

FTG_GROUPS = ("drive", "tone", "cab")              # swapped; effects and other (gate, output gain, transpose, the amp
                                                     # section) are off or unchanged in S and FT on every BKS answer
FTG_ALL = (*FTG_GROUPS, "effects", "other")
FTG_HASHES = "phase_ft_groups_answers"              # the ledger key: {tag: sha256 of real/answers/<tag>.json}
FTG_WAYS = ("rev", "add")                           # rev-g: FT with g at S; add-g: S with g from FT
FTG_DRIVE = {"parameters/inputGain", "pedalParameters/sectionActive", "pr12Amp/pr12Volume", "sw50rAmp/sw50rVolume",
             "sw50rAmp/sw50rLevel", "sw50rAmp/sw50rInputMode", "ac20Amp/ac20Volume", "ac20Amp/ac20Power"}
FTG_TONE = {"pr12Amp/pr12Treble", "pr12Amp/pr12Bass", "sw50rAmp/sw50rTreble", "sw50rAmp/sw50rMid", "sw50rAmp/sw50rBass",
            "sw50rAmp/sw50rBright", "sw50rAmp/sw50rTrebleBoost", "ac20Amp/ac20Cut", "ac20Amp/ac20Bright",
            "ac20Amp/ac20BassTreble", "eqParameters/sectionActive"}
FTG_EFFECTS = {"pr12Amp/pr12Reverb", "pr12Amp/pr12Dwell", "sw50rAmp/sw50rReverb", "pr12Amp/springOn",
               "sw50rAmp/springOn", "fxParameters/sectionActive", "parameters/doublerActive", "parameters/doublerSpread"}


def ftg_tag(way, group):
    return f"FTg-{way}-{group}"


def ftg_group(key):
    """A settings key's control group (`phase_ft_groups`): drive, tone, cab, effects or other."""
    mod = key.split("/", 1)[0]
    if key in FTG_DRIVE or mod in ("drive1", "drive2", "compressor"):
        return "drive"
    if key in FTG_EFFECTS or mod in ("reverb", "delay", "tremolo"):
        return "effects"
    if key in FTG_TONE or mod in ("pr12EQ", "sw50rEQ", "ac20EQ"):
        return "tone"
    if mod == "cabParameters":
        return "cab"
    return "other"


def ftg_change(a, s, amp):
    """What an answer `a` changes from S `s` (settings dicts) on `amp`, per group of FTG_ALL, counting only what can
    sound (`full_space.encode`'s masks: the amp's own keys, switched-on modules, a gate threshold only with the gate
    on), in either: {group: (changed, mean |unit change| over the group's sounding continuous dims or None)}."""
    import numpy as np

    from learn import full_space as F

    def enc(x):
        return F.encode({tuple(k.rsplit("/", 1)): v for k, v in x.items()}, amp)

    ca, cma, sa, sma, ka, kma, _ = enc(a)
    cs, cms, ss, sms, ks, kms, _ = enc(s)
    out = {}
    for g in FTG_ALL:
        ci = [j for j, n in enumerate(F.CONT) if ftg_group(n) == g and (cma[j] or cms[j])]
        si = [j for j, n in enumerate(F.SW) if ftg_group(n) == g and (sma[j] or sms[j])]
        ki = [j for j, n in enumerate(F.CAT) if ftg_group(n) == g and (kma[j] or kms[j])]
        d = [abs(float(ca[j] - cs[j])) for j in ci]
        changed = any(x > 1e-6 for x in d) or any(sa[j] != ss[j] for j in si) or any(ka[j] != ks[j] for j in ki)
        out[g] = (bool(changed), float(np.mean(d)) if d else None)
    return out


def ftg_mix(base, donor, group):
    """`base`'s settings with `group`'s keys taken from `donor` (both full settings dicts on one key set)."""
    if set(base) != set(donor):
        raise SystemExit("ftg_mix: the two settings hold different keys")
    return {k: (donor[k] if ftg_group(k) == group else v) for k, v in base.items()}


def ftg_answers(ft, s_ans):
    """The hybrids of `phase_ft_groups` from FT's BKS answers {key: {half: answer}} and S's {key: {ANY_HALF: answer}}:
    {tag: {key: {half: answer}}} and per group the count of answers whose g-keys differ from S's."""
    out = {ftg_tag(w, g): {} for w in FTG_WAYS for g in FTG_GROUPS}
    differ = {g: {"any_key": 0, "sounding": 0, "unit_moves": []} for g in FTG_ALL}
    for key, halves in ft.items():
        s = s_ans[key][ANY_HALF]
        amp = key.rsplit("|", 1)[1]
        for half, a in halves.items():
            if a["select"] != s["select"]:
                raise SystemExit(f"{key} {half}: FT's select is not S's")
            snd = ftg_change(a["settings"], s["settings"], amp)
            for g, rec in differ.items():
                rec["any_key"] += any(a["settings"][k] != s["settings"][k] for k in a["settings"] if ftg_group(k) == g)
                rec["sounding"] += snd[g][0]
                if snd[g][1] is not None:
                    rec["unit_moves"].append(snd[g][1])
            for g in FTG_GROUPS:
                out[ftg_tag("rev", g)].setdefault(key, {})[half] = {
                    "select": a["select"], "settings": ftg_mix(a["settings"], s["settings"], g)}
                out[ftg_tag("add", g)].setdefault(key, {})[half] = {
                    "select": s["select"], "settings": ftg_mix(s["settings"], a["settings"], g)}
    for rec in differ.values():
        mv = rec.pop("unit_moves")
        rec["mean_unit_move"] = statistics.fmean(mv) if mv else None
    return out, differ


def ftg_unhashed(tags, entry):
    """The FTg- answers files among `tags` whose sha256 is not the ledger's FTG_HASHES record. -> [problems]."""
    from learn import direct_stems as DS

    want = (entry or {}).get(FTG_HASHES) or {}
    out = []
    for t in tags:
        if not t.startswith("FTg-"):
            continue
        p = out_dir() / REAL_DIR / "answers" / f"{t}.json"
        if not p.exists():
            out.append(f"{t}: no answers file")
        elif want.get(t) != DS.hashlib_file(p):
            out.append(f"{t}: sha256 not recorded under {FTG_HASHES}")
    return out


def cmd_ft_groups(args):
    """`phase_ft_groups`' answers (zero renders): FT's BKS read 2 answers split by control group into rev-g and add-g
    (`ftg_answers`), saved as real/answers/FTg-*.json for `real-render`; prints each file's sha256 for the ledger."""
    from learn import direct_stems as DS

    require("phase_ft_groups")
    ad = out_dir() / REAL_DIR / "answers"
    ft = json.loads((ad / f"{FT_BASE}.json").read_text())
    s_ans = json.loads((ad / "S.json").read_text())["answers"]
    out, differ = ftg_answers(ft["answers"], s_ans)
    shas = {}
    for tag, ans in out.items():
        p = ad / f"{tag}.json"
        if p.exists():
            raise SystemExit(f"{p.name} exists: the hybrids are written once")
        save(p, {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_ft_groups", "tag": tag, "from": f"{FT_BASE}.json and S.json",
                 "ft_answers_sha256": answers_sha(ft["answers"]), "differ_from_S": differ, "answers": ans,
                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        shas[tag] = DS.hashlib_file(p)
    n = sum(len(h) for h in ft["answers"].values())
    print(f"FT-GROUPS DONE: {len(out)} tags x {n} answers; answers whose group differs from S: {differ}")
    print(f"record in the ledger's pipeline-fix entry before rendering: \"{FTG_HASHES}\": "
          + json.dumps(shas, indent=1))


COMMANDS = {"panel-sections": cmd_panel_sections, "panel-lags": cmd_panel_lags, "panel-centres": cmd_panel_centres, "panel-predict": cmd_panel_predict, "panel-render": cmd_panel_render, "panel-report": cmd_panel_report, "panel-ceiling": cmd_panel_ceiling, "goat-sections": cmd_goat_sections, "goat-search": cmd_goat_search,
            "goat-stage-check": cmd_goat_stage_check, "goat-centres": cmd_goat_centres,
            "goat-predict": cmd_goat_predict, "goat-render": cmd_goat_render, "goat-report": cmd_goat_report,
            "p5": cmd_p5, "dirty-doubles": cmd_dirty_doubles, "p6": cmd_p6,
            "build-inputs": cmd_build_inputs, "p1": cmd_p1, "render-doubles": cmd_render_doubles,
            "build-doubles": cmd_build_doubles, "train": cmd_train, "read": cmd_read, "sample": cmd_sample,
            "answers": cmd_answers, "sound-render": cmd_sound_render, "sound-report": cmd_sound_report,
            "build-backings": cmd_build_backings, "p4-predict": cmd_p4_predict, "share": cmd_share,
            "prior-edges": cmd_prior_edges, "kfold-report": cmd_kfold_report, "wide-pool": cmd_wide_pool,
            "build-wide": cmd_build_wide, "real-predict": cmd_real_predict, "real-render": cmd_real_render,
            "real-report": cmd_real_report, "real-search": cmd_real_search, "real-ceiling": cmd_real_ceiling,
            "real-heads": cmd_real_heads, "real-setting-audit": cmd_real_setting_audit,
            "vreal-sc": cmd_vreal_sc, "vreal-comparators": cmd_vreal_comparators,
            "vreal-render": cmd_vreal_render, "vreal-report": cmd_vreal_report,
            "build-dfix-real": cmd_build_dfix_real, "sound-recheck": cmd_sound_recheck,
            "dfix-vreal-predict": cmd_dfix_vreal_predict, "dfix-vreal-render": cmd_dfix_vreal_render,
            "dfix-vreal-report": cmd_dfix_vreal_report, "train-ft": cmd_train_ft, "ft-recheck": cmd_ft_recheck,
            "ft-vreal-predict": cmd_ft_vreal_predict, "ft-vreal-render": cmd_ft_vreal_render,
            "ft-vreal-report": cmd_ft_vreal_report, "ft-groups": cmd_ft_groups}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline_fix", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=tuple(COMMANDS))
    ap.add_argument("--data-dir", default=str(DATA))
    ap.add_argument("--shard", type=lambda v: tuple(int(z) for z in v.split("/")), default=(0, 1))
    ap.add_argument("--reads-only", action="store_true", help="build-dfix-real: only the read units with no row")
    ap.add_argument("--rung", choices=tuple(RUNG_KINDS), default="a")
    ap.add_argument("--epochs", type=int, default=1500)
    ap.add_argument("--device", choices=("mps", "cpu"), default="mps")
    ap.add_argument("--seed", type=int, default=SEEDS[0])
    ap.add_argument("--frac", type=float, default=1.0)
    ap.add_argument("--sections", type=float, default=1.0)
    ap.add_argument("--fold", type=int, choices=tuple(FOLDS), default=None)
    ap.add_argument("--aug", action="store_true")
    ap.add_argument("--name", default=None)
    ap.add_argument("--which", choices=("final", "best"), default="final")
    ap.add_argument("--names", default="")
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--doubled", action="store_true")
    ap.add_argument("--desc", action="store_true")
    ap.add_argument("--readout", choices=("plain", "pulled", "sws", "nc"), default="plain")
    ap.add_argument("--amp-shift", type=int, choices=(0, 1, 2), default=0)
    ap.add_argument("--input-rung", choices=("b", "c", "d"), default=None)   # answers: read another rung's stored inputs
    ap.add_argument("--mastered", action="store_true")
    ap.add_argument("--seeds", default=str(SEEDS[0]))
    ap.add_argument("--against", default="")
    ap.add_argument("--pairs", default="")
    ap.add_argument("--own-inputs", action="store_true")
    ap.add_argument("--label", default="")
    ap.add_argument("--backings", action="store_true")
    ap.add_argument("--dd", action="store_true")
    ap.add_argument("--levels-only", action="store_true")
    ap.add_argument("--wide", action="store_true")
    ap.add_argument("--pc", action="store_true")
    ap.add_argument("--stage", type=int, default=0)
    ap.add_argument("--real-fold", type=int, choices=tuple(range(REAL_FOLDS)), default=None)
    ap.add_argument("--pcsz", action="store_true")
    ap.add_argument("--by-mode", action="store_true")
    ap.add_argument("--within", default="")
    ap.add_argument("--goat", action="store_true")
    ap.add_argument("--goat-shuffle", action="store_true")
    ap.add_argument("--dfix", action="store_true")
    ap.add_argument("--dfix-share", choices=tuple(DFIX_SHARES), default=None)
    ap.add_argument("--n", type=int, default=20, help="sound-recheck: stored renders per tag rendered again")
    ap.add_argument("--lags-only", action="store_true")
    ap.add_argument("--lag-tol", type=int, default=None)       # goat-report: read A on a narrower lag set
    ap.add_argument("--inner", action="store_true", help="train-ft: fold k's epoch-choice run")
    ap.add_argument("--masked", action="store_true", help="train-ft: N1, heads outside the search masked on real rows")
    ap.add_argument("--ft-lr", type=float, default=None)       # train-ft: a declared fallback only
    ap.add_argument("--ft-cap", type=int, default=None)
    args = ap.parse_args(argv)
    return COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
