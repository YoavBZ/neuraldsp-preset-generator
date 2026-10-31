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


def fit(data, tr, watch, track, seed, dev, log, epochs, every=1, patience=None, min_gain=1e-4):
    """D_CC's optimiser (Adam 1e-3, batch 64, gradients scaled to norm 5; `direct_stems.train_arm`) with the eval-mode
    diagnostics: every `every` epochs (and at the last) the summed loss on each `watch` set {name: idx} and its family
    means. The checkpoint with the lowest `track` loss is kept beside the final one. With `patience` (P1 only) it stops
    once `track` has not improved by min_gain for that many checks; otherwise it runs the full `epochs`.
    -> (net at its final state, final state, best state, best epoch, best value)."""
    import numpy as np
    import torch

    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import pretrain_set as PS

    torch.manual_seed(seed)
    net = F.build_net().to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=PS.LR)
    rng = np.random.default_rng(seed)
    best, bad, best_state, best_ep, steps = math.inf, 0, None, None, 0
    for epoch in range(epochs):
        net.train()
        t0 = time.time()
        order = rng.permutation(tr)
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
        log.append(rec)
        print(json.dumps(rec), flush=True)
        v = rec[track]["total"]
        if math.isfinite(v) and v < best - min_gain:
            best, bad, best_ep = v, 0, epoch
            best_state = {k: t.detach().cpu().clone() for k, t in net.state_dict().items()}
        else:
            bad += 1
            if patience is not None and bad >= patience:
                break
    if best_state is None:
        raise PS.StepsSkipped("no finite watched loss")
    final = {k: t.detach().cpu().clone() for k, t in net.state_dict().items()}
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


def cmd_train(args):
    """One model of the ladder (demucs-venv): the common recipe on rung `--rung`'s input for the declared number of
    epochs, the eval-mode diagnostics at every checkpoint (a fixed training subset and the held-out set, per family),
    the final and the held-out-best checkpoints kept, each with its per-head table against the label-marginal
    baseline. `--frac`: a nested share of the training examples within sections; `--sections`: a share of the
    sections with all their examples; `--fold k`: new songs by k-fold (all kept examples of the other folds' bands;
    the final checkpoint is the one read); `--aug`: P2d-aug."""
    import numpy as np
    import torch

    from learn import direct_stems as DS

    e = require("phase_3")
    length = e["phase_3_length"]
    croot, kept, rend, sp, dropped = recipe_inputs(pin=e.get("phase_3_doubles"))
    name = run_name(args.rung, args.frac, args.aug, args.fold, args.sections) + ("-bk8" if args.backings else "") \
        + ("-dd" if args.dd else "") + (f"-wide{WIDE_K}" if args.wide else "")
    od = out_dir() / "runs"
    rp = od / f"{name}-{args.seed}.json"
    if rp.exists():
        print(f"{rp.name} exists: nothing to do")
        return
    if args.seed not in SEEDS:
        raise SystemExit(f"--seed in {SEEDS}")
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
    doubled = doubled_ids() if dropped["doubles"] == "fixed" else frozenset()
    rows = rung_rows(kept, rend, tr) + [dict(r, held=True) for r in rung_rows(kept, rend, held)]
    if args.wide:
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
    else:
        data = arm_data(rows, croot, args.rung, doubled, rend, args.aug)
    ti, hi = np.arange(len(tr)), np.arange(len(tr), len(rows))
    sub = np.sort(np.random.default_rng(SUBSET_SEED).choice(ti, min(SUBSET_N, len(ti)), replace=False))
    cells = [(r["amp"], r["cls"]) for r in rows]
    base = Baseline([z[ti] for z in data.Y], [cells[j] for j in ti])
    bl = {"train_subset": base.losses([z[sub] for z in data.Y], [cells[j] for j in sub]),
          held_name: base.losses([z[hi] for z in data.Y], [cells[j] for j in hi])}
    dev = device()
    torch.set_num_threads(2)
    log = []
    t0 = time.time()
    net, final, best_state, best_ep, best = fit(data, ti, {"train_subset": sub, held_name: hi}, held_name, args.seed,
                                                dev, log, epochs=int(length["epochs"]), every=int(length["every"]))
    heads = {}
    od.mkdir(parents=True, exist_ok=True)
    for which, st in (("final", final), ("best", best_state)):
        net.load_state_dict(st)
        heads[which] = {k: head_table(head_losses(net, data, idx, dev), bl[k])
                        for k, idx in (("train_subset", sub), (held_name, hi))}
        torch.save(st, od / f"{name}-{args.seed}-{which}.pt")
    save(rp, {"plan": PLAN, "test": name, "ledger": f"{LEDGER_ID} phase_3", "rung": args.rung,
              "input": RUNG_KINDS[args.rung], "aug": bool(args.aug), "frac": args.frac, "sections": args.sections,
              "fold": args.fold, "held": held_name, "seed": args.seed, "train": len(tr), "held_n": len(held),
              "train_ids": tr, "held_ids": held, "dropped": dropped, "split_dropped": sp["dropped"],
              "epochs_run": log[-1]["epoch"] + 1, "best_epoch": best_ep, "best_held_loss": best,
              "steps": log[-1]["steps"], "minutes": round((time.time() - t0) / 60, 1), "device": str(dev),
              "length": length, "augmentations_applied": data.applied, "flags": {"dd": bool(args.dd),
              "backings": bool(args.backings), "aug": bool(args.aug), "wide": bool(args.wide)},
              "backing_variants": getattr(data, "counts", None),
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
        path_of = rung_path(croot, rec["rung"], doubled)
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
               + amp_tag(args.amp_shift))
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
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_3_sound", "sample_n": n_each, "rows": {}}
    for set_name, sids in ids.items():
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
                cl = ex[i]["band"] if set_name == "fs" else ex[i]["section"]
                rows.append((cl, ex[i]["section"], v))
            c = clustered(rows)
            key = f"{ta} - {tb}"
            out["rows"].setdefault(key, {})[set_name] = {
                **{k: c.get(k) for k in ("mean", "lo90", "hi90", "clusters", "clusters_negative", "clusters_positive",
                                         "part_weighted", "parts")},
                "clustered_by": "band" if set_name == "fs" else "section (NS is 2 bands)", "missing": missing,
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

    require("phase_5b1")
    tags = ["S"] + [t for t in args.names.split(",") if t and t != "S"]
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
    renders = 0

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
    print(f"REAL-RENDER DONE {k}/{n}: {renders} renders")


def cmd_real_report(args):
    """5B.1's rows: for each pair in `--pairs`, ln(d_a / d_b) on the held half per (unit, amp, search), with S
    refused dropping the direction and a refused answer scored as S (the V-real rule); clustered by DI (the
    performance: rigs sharing a DI share its sections and its S and constant renders), parts the units; by rig beside;
    part-weighted beside; the lag refusals counted apart from the missing. -> real/report-<label>.json."""
    require("phase_5b1")
    tags = {t for pair in args.pairs.split(",") for t in pair.split(":")} | {"S"}
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
    phase = "phase_5b1b" if any(t in ("P2a-Sc", "S-shift") for t in tags) else "phase_5b1"
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {phase}", "units": len(parts), "no_lag": no_lag, "rows": {}}
    units = [(p_["unit"], amp, sh, h) for p_ in parts for amp in AMPS3 for sh, h in (("A", "B"), ("B", "A"))]
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
    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import trusted_data as T
    from learn import trusted_data_t3 as T3

    require("phase_4")
    root, plan, drift, dirs, parts, ms = vreal_ctx()
    groups = sorted({(s_, a) for s_, a, _, _ in dirs})
    k, n = args.shard
    mine = [g for j, g in enumerate(groups) if j % n == k]
    bad = [t for t in args.names.split(",") if t not in P4_TAGS]
    if bad:
        raise SystemExit(f"phase 4 renders only its declared tags {P4_TAGS}; not {bad}")
    if "P4-P2a-best-sc" in args.names.split(","):
        require("phase_5b1c")
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
    renders = 0
    for tag in args.names.split(","):
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
            save(gp, rec)
        print(f"{tag}: shard {k}/{n} done; renders so far {renders}", flush=True)
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
    save(out_dir() / VREAL_DIR / f"report-{args.label or 'p4'}.json", out)
    print("VREAL-REPORT DONE")


# --- main ------------------------------------------------------------------------------------------------------------

COMMANDS = {"p5": cmd_p5, "dirty-doubles": cmd_dirty_doubles, "p6": cmd_p6,
            "build-inputs": cmd_build_inputs, "p1": cmd_p1, "render-doubles": cmd_render_doubles,
            "build-doubles": cmd_build_doubles, "train": cmd_train, "read": cmd_read, "sample": cmd_sample,
            "answers": cmd_answers, "sound-render": cmd_sound_render, "sound-report": cmd_sound_report,
            "build-backings": cmd_build_backings, "p4-predict": cmd_p4_predict, "share": cmd_share,
            "prior-edges": cmd_prior_edges, "kfold-report": cmd_kfold_report, "wide-pool": cmd_wide_pool,
            "build-wide": cmd_build_wide, "real-predict": cmd_real_predict, "real-render": cmd_real_render,
            "real-report": cmd_real_report, "vreal-sc": cmd_vreal_sc, "vreal-comparators": cmd_vreal_comparators,
            "vreal-render": cmd_vreal_render, "vreal-report": cmd_vreal_report}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline_fix", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=tuple(COMMANDS))
    ap.add_argument("--data-dir", default=str(DATA))
    ap.add_argument("--shard", type=lambda v: tuple(int(z) for z in v.split("/")), default=(0, 1))
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
    args = ap.parse_args(argv)
    return COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
