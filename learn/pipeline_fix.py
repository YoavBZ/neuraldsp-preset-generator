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
    parity = []
    t0 = time.time()
    for m, i in enumerate(todo):
        pa, pb = (input_path(DATA, i, RUNG_KINDS[r]) for r in OWN_KINDS)
        if pa.exists() and pb.exists():
            continue
        x, rw, bw = ex[i], rend[i], built[i]
        y = G.read_flac(T.flac_path(root, CB.STAGE, i, "target"), rw["target"]["scale"], rw["target"]["sha256"])
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
        stored = np.load(T.ex_path(root, CB.STAGE, i, "mix-cc"))
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

    def __init__(self, rows, path_of, aug=True):
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


def recipe_inputs(root=DATA):
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
    croot, kept, rend, sp, dropped = recipe_inputs()
    name = run_name(args.rung, args.frac, args.aug, args.fold, args.sections)
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
              "length": length, "augmentations_applied": data.applied,
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

    def others_of(xs, sec, new):
        """{i: (others sum, rows)} for the examples xs of one section."""
        nonlocal renders
        stems = sorted({s for x in xs for s in x["stems"]["v"]})
        levels = T.section_levels(ctx, sec, [o for x in xs for o in x["others"]], stems)
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
        for i in pick:
            x = ex[i]
            sec = dict(ctx.sections[x["section"]], id=x["section"])
            acc, rows = others_of([x], sec, new=False)
            rw = rend[i]
            old = G.read_flac(T.flac_path(croot, CB.STAGE, i, "others"), rw["others_file"]["scale"],
                              rw["others_file"]["sha256"])
            step = float(rw["others_file"]["scale"]) / 2 ** 23
            dev = float(np.max(np.abs(acc[i] - old)))
            control.append({"i": i, "max_abs_dev": dev, "flac_step": step, "ok": dev <= step})
            print(f"control {i}: max |re-render - stored| {dev:.3g} (FLAC step {step:.3g})", flush=True)
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
    todo = sorted((i for i in new if i not in built), key=lambda i: (ex[i]["section"], i))
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


def cmd_read(args):
    """The by-knob read of one model (`--name`, both seeds where both ran, `--which` final|best): R0's rule on FS and
    the held-out set (NS or the fold), against the constant of its own training labels; the family table; E split by
    draw mode and by mastering. Zero renders. -> reads/<name>-<which>.json."""
    import numpy as np

    from learn import full_space as F
    from learn import trusted_data_t3_r as R

    require("phase_3")
    croot, kept, rend, sp, dropped = recipe_inputs()
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
            "e_minus_constant_all": split_e(ex, info, const, lambda i: "all")["all"]}
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
    require("phase_3")
    croot, kept, rend, sp, dropped = recipe_inputs()
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
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import trusted_data_t3 as T3
    from learn import trusted_data_t3_r as R

    require("phase_3")
    croot, kept, rend, sp, dropped = recipe_inputs()
    ids = sorted(set(sum(sample_ids(2 * SAMPLE_N).values(), [])))
    ms = A.L.menu_S()
    rows = rung_rows(kept, rend, ids)
    out = {}
    if args.name in ("S", "constant"):
        const = constant_of(rung_rows(kept, rend, sp["train"]))
        for r in rows:
            sel, S = ms[r["amp"]][r["cls"]]
            x = dict(S) if args.name == "S" else T3.constant_full(r["amp"], S, const[(r["amp"], r["cls"])])
            out[str(r["i"])] = {"select": sel, "settings": LO.sdict(x)}
        tag = args.name
    else:
        nets, rec = [], None
        for sd in SEEDS:
            if (out_dir() / "runs" / f"{args.name}-{sd}.json").exists():
                n, rec = load_run(args.name, sd, args.which)
                nets.append(n)
        if not nets:
            raise SystemExit(f"{args.name}: no run")
        doubled = doubled_ids() if dropped["doubles"] == "fixed" else frozenset()
        data = RungData(rows, rung_path(croot, rec["rung"], doubled), aug=False)
        X, C, who = read_inputs(data)
        outs = F.run_nets(nets, X, C)
        Y = [np.repeat(data.Y[q], 2, axis=0) for q in range(6)]
        ex = R.per_example(outs, who, Y)
        for r in rows:
            e = ex[r["i"]]
            sel, S = ms[r["amp"]][r["cls"]]
            mics = [int(np.argmax(m)) for m in e["mic_p"]]
            x = F.answer_settings(r["amp"], S, e["a2"], e["sw_p"], mics)
            out[str(r["i"])] = {"select": sel, "settings": LO.sdict(x)}
        tag = f"{args.name}-{args.which}"
    save(out_dir() / SOUND_DIR / "answers" / f"{tag}.json", {"plan": PLAN, "ledger": f"{LEDGER_ID} phase_3",
                                                            "name": tag, "answers": out,
                                                            "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"ANSWERS DONE {tag}: {len(out)} examples")


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
        gd = out_dir() / SOUND_DIR / "judge" / tag
        di_cache = {}
        for i in mine:
            gp = gd / f"{i}.json"
            if gp.exists():
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
            save(gp, {"i": i, "tag": tag, "judge": j, "render_sha256": AM.audio_sha(y)})
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
            rows, missing = [], 0
            for i in sids:
                v = log_ratio(judge(ta, i), judge(tb, i))
                if v is None:
                    missing += 1
                    continue
                cl = ex[i]["band"] if set_name == "fs" else ex[i]["section"]
                rows.append((cl, ex[i]["section"], v))
            c = clustered(rows)
            key = f"{ta} - {tb}"
            out["rows"].setdefault(key, {})[set_name] = {
                **{k: c.get(k) for k in ("mean", "lo90", "hi90", "clusters", "clusters_negative", "clusters_positive",
                                         "part_weighted", "parts")},
                "clustered_by": "band" if set_name == "fs" else "section (NS is 2 bands)", "missing": missing}
            r = out["rows"][key][set_name]
            if r["mean"] is not None:
                iv = "" if r["lo90"] is None else f" [{r['lo90']:+.4f}, {r['hi90']:+.4f}]"
                print(f"  {key:40s} {set_name}: {r['mean']:+.4f}{iv} ({r['clusters']} {r['clustered_by'].split()[0]}s, "
                      f"{r['clusters_negative']} better){' MISSING ' + str(missing) if missing else ''}")
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save(out_dir() / SOUND_DIR / "report.json", out)
    print("SOUND-REPORT DONE")


# --- main ------------------------------------------------------------------------------------------------------------

COMMANDS = {"p5": cmd_p5, "dirty-doubles": cmd_dirty_doubles, "p6": cmd_p6,
            "build-inputs": cmd_build_inputs, "p1": cmd_p1, "render-doubles": cmd_render_doubles,
            "build-doubles": cmd_build_doubles, "train": cmd_train, "read": cmd_read, "sample": cmd_sample,
            "answers": cmd_answers, "sound-render": cmd_sound_render, "sound-report": cmd_sound_report}


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
    args = ap.parse_args(argv)
    return COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
