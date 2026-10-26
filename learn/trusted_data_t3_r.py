"""T3's F5 follow-up R (`docs/trusted-data-t0-design.md`, "F5 follow-up: readability (R0) and the unreadable controls
at S (R1)"; ledger `trusted-data-t3`, amendment 1). Post hoc and descriptive: F5's V-real reads are seen. Outputs go
to `t3/followup-r/` only; F5's files are read, never written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $TORCH_PY -m learn.trusted_data_t3_r r0                     # zero renders: each D_F5 head's readability on FS5
    $MAIN -m learn.trusted_data_t3_r r1-predict                 # zero renders: D_F5:R from F5's stored readout
    $MAIN -u -m learn.trusted_data_t3_r r1-render --shard k/3   # 99 renders in all (33 groups x (1 priming + 2))
    $MAIN -m learn.trusted_data_t3_r r1-report                  # R1's rows, the time-effects row, F5's rows beside

**R0** (zero renders): D_F5's two seeds on FS5 (the set `fit` read), each example's answer as the readout makes it
(A1 + A2 over seeds and halves; the mean switch, mic and amp probabilities), against D_F5's constant (`fit.json`):
continuous heads by E against the constant (A1 + A2 without the pull, which is fitted on FS5), section-clustered t;
switches by AUC, delete-one-section jackknife t; the amp choice by accuracy against the training majority amp, and
the mics by accuracy against the constant's mic mode, section-clustered t. All 90%. Readable iff the interval excludes
chance in the right direction; otherwise unreadable (no interval included).

**R1** (99 renders): one answer set, D_F5:R: D_F5's pulled answer (rebuilt from F5's stored readout and checked equal
to F5's stored D_F5 answer) with every R0-unreadable head at S's value. Rendered as F5's V-real (`direct_stems.
run_group`: one discarded priming render at S per (part, amp) group, both directions), isolate=True, the first
0.25 s trimmed, at most 3 render processes machine-wide (`local_objective.RENDERS`), the 31 GB disk guard.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time

from learn import full_space as F
from learn import trusted_data as T
from learn import trusted_data_t3 as T3
from learn import verify_tracks as V

R_DIR = "followup-r"
R_ARM = f"{T3.FULL}:R"                              # D_F5 with every unreadable head at S
TIME_ARM = f"{T3.FULL}:at-S:time effects and spring"  # F5's stored family arm (the audit's re-read)
LEDGER_KEY = "amendment_1"
LEDGER_MARK = "F5 follow-up R"
DESIGN = "docs/trusted-data-t0-design.md#f5-follow-up-readability-r0-and-the-unreadable-controls-at-s-r1-declared-2026-10-26"
STATUS = "post hoc and descriptive: F5's V-real reads are seen; neither R0 nor R1 decides F20"
FAMILY_ORDER = ("today", "amp_choice", "amp_eq", "pedals", "time_effects", "spring", "gate_doubler", "cab_rest")
AMP_NAME = "amp choice"
CHANCE = {"switch": 0.5, "continuous": 0.0, "accuracy": 0.0}
RENDERS_PER_GROUP = 3                                # 1 priming at S + 2 directions

_save, _load = V._save, V._load


# --- pure: the statistics ---------------------------------------------------------------------------------------

def auc(y, q):
    """The Mann-Whitney AUC (average ranks for ties); None with one class."""
    import numpy as np
    from scipy.stats import rankdata

    y, q = np.asarray(y, bool), np.asarray(q, np.float64)
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return None
    r = rankdata(q)
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def jackknife_auc(y, q, groups):
    """AUC with the delete-one-section jackknife's 90% t interval (sections - 1 df). No interval (lo, hi None) with
    fewer than 2 sections, one class, or a fold left with one class. -> {point, lo, hi, sections}."""
    import numpy as np

    from learn import pretrain_set as PS

    y, q, g = np.asarray(y, bool), np.asarray(q, np.float64), np.asarray(groups)
    a = auc(y, q)
    secs = sorted(set(g.tolist()))
    out = {"point": a, "lo": None, "hi": None, "sections": len(secs)}
    if a is None or len(secs) < 2:
        return out
    th = []
    for s in secs:
        v = auc(y[g != s], q[g != s])
        if v is None:
            return out
        th.append(v)
    th = np.asarray(th)
    k = len(th)
    se = math.sqrt((k - 1) / k * float(((th - th.mean()) ** 2).sum()))
    h = PS.t90(k - 1) * se
    out.update(lo=a - h, hi=a + h)
    return out


def section_t(diffs, section_of):
    """A per-example paired difference, clustered by section: the mean of section means with its 90% t interval
    (`pretrain_set.band_t_interval`). No interval with fewer than 2 sections. -> {point, lo, hi, sections}."""
    from learn import pretrain_set as PS

    by = {}
    for i, d in diffs.items():
        by.setdefault(section_of[i], []).append(float(d))
    if not by:
        return {"point": None, "lo": None, "hi": None, "sections": 0}
    m, lo, hi, n = PS.band_t_interval(by)
    ok = n >= 2 and math.isfinite(lo) and math.isfinite(hi)
    return {"point": m, "lo": lo if ok else None, "hi": hi if ok else None, "sections": n}


def readable(kind, s):
    """The declared rule: the interval excludes chance in the right direction. -> (readable?, why)."""
    if s.get("lo") is None or s.get("hi") is None:
        return False, "no interval"
    if kind == "switch":
        return (True, "AUC interval above 0.5") if s["lo"] > CHANCE[kind] else (False, "AUC interval holds 0.5")
    if kind == "continuous":
        return (True, "E interval below the constant's") if s["hi"] < 0 else (False, "E interval holds 0")
    if kind == "accuracy":
        return (True, "accuracy interval above the base rate") if s["lo"] > 0 else (False, "accuracy interval holds 0")
    raise ValueError(kind)


# --- pure: the heads and their families ---------------------------------------------------------------------------

def family_of_name(name):
    """A head's family (the every-control table's), the springs' derived switches in 'spring'."""
    D = F.by_name()
    d = D[name]
    if d.key == F.SPRING_KEY:
        return "spring"
    return F.family_of((d.module, d.key))


def per_example(outs, who, Y):
    """Each FS5 example's readout over seeds and halves: A1 + A2, the mean switch, mic and amp probabilities, and its
    encoded label (the first row's). outs: `full_space.run_nets`'s, per seed per row. -> {i: dict}."""
    import numpy as np

    from learn import direct_stems as DS

    _, a2 = DS.median_answers(outs, who)
    rows = {}
    for n, i in enumerate(who):
        rows.setdefault(i, []).append(n)
    out = {}
    for i, ix in rows.items():
        o = [s[n] for s in outs for n in ix]
        n0 = ix[0]
        out[i] = {"a2": np.asarray(a2[i], np.float64),
                  "sw_p": np.mean([1.0 / (1.0 + np.exp(-np.asarray(z[3], np.float64))) for z in o], axis=0),
                  "mic_p": [np.mean([F._softmax(z[4][j]) for z in o], axis=0) for j in range(len(F.CAT))],
                  "amp_p": np.mean([F._softmax(z[5]) for z in o], axis=0),
                  "c": Y[0][n0], "cm": Y[1][n0], "s": Y[2][n0], "sm": Y[3][n0], "k": Y[4][n0], "km": Y[5][n0]}
    return out


def train_priors(train_labels, train_amps):
    """The training prior an unreadable head falls back on: each switch's on-rate where it is scored, and the
    majority amp. train_labels: encoded labels (c, cm, s, sm, k, km). -> ({switch: rate or None}, majority amp)."""
    import numpy as np

    S = np.stack([np.asarray(t[2], np.float64) for t in train_labels])
    M = np.stack([np.asarray(t[3], np.float64) for t in train_labels]) > 0
    rates = {n: (float(S[M[:, j], j].mean()) if M[:, j].any() else None) for j, n in enumerate(F.SW)}
    counts = {a: train_amps.count(a) for a in F.AMPS}
    return rates, max(F.AMPS, key=lambda a: (counts[a], -F.AMPS.index(a)))


def r0_rows(ex, info, const, train_rates, majority_amp):
    """R0's table. ex: `per_example`'s; info: {i: {"section", "cell": (amp, base), "amp"}}; const: D_F5's constant
    answers per cell ({"cont", "sw", "mics"}). -> rows, one per head (continuous, switch, mic, the amp choice)."""
    import numpy as np

    sec = {i: info[i]["section"] for i in ex}
    rows = []

    def row(name, kind, stat, n, extra):
        ok, why = readable(kind, stat)
        rows.append({"name": name, "family": "amp_choice" if name == AMP_NAME else family_of_name(name),
                     "kind": kind, "n": n, "sections": stat["sections"], "point": stat["point"], "lo": stat["lo"],
                     "hi": stat["hi"], "chance": CHANCE[kind], "readable": ok, "why": why, **extra})

    for j, n in enumerate(F.CONT):
        d, em, ec = {}, [], []
        for i, e in ex.items():
            c0 = float(const[info[i]["cell"]]["cont"][j])
            if e["cm"][j] > 0 and math.isfinite(c0):
                y = float(e["c"][j])
                em.append(abs(float(e["a2"][j]) - y))
                ec.append(abs(c0 - y))
                d[i] = em[-1] - ec[-1]
        row(n, "continuous", section_t(d, sec), len(d),
            {"e_model": float(np.mean(em)) if em else None, "e_constant": float(np.mean(ec)) if ec else None})
    for j, n in enumerate(F.SW):
        ids = [i for i, e in ex.items() if e["sm"][j] > 0]
        y = [float(ex[i]["s"][j]) > 0.5 for i in ids]
        st = jackknife_auc(y, [float(ex[i]["sw_p"][j]) for i in ids], [sec[i] for i in ids])
        row(n, "switch", st, len(ids), {"on_rate_fs5": float(np.mean(y)) if y else None,
                                         "on_rate_train": train_rates.get(n)})
    for j, n in enumerate(F.CAT):
        d, acc, base = {}, [], []
        for i, e in ex.items():
            m0 = const[info[i]["cell"]]["mics"][j]
            if e["km"][j] > 0 and m0 is not None:
                acc.append(float(int(np.argmax(e["mic_p"][j])) == int(e["k"][j])))
                base.append(float(int(m0) == int(e["k"][j])))
                d[i] = acc[-1] - base[-1]
        row(n, "accuracy", section_t(d, sec), len(d),
            {"accuracy": float(np.mean(acc)) if acc else None, "base_rate": float(np.mean(base)) if base else None})
    d, acc, base = {}, [], []
    for i, e in ex.items():
        a = F.AMPS.index(info[i]["amp"])
        acc.append(float(int(np.argmax(e["amp_p"])) == a))
        base.append(float(F.AMPS.index(majority_amp) == a))
        d[i] = acc[-1] - base[-1]
    row(AMP_NAME, "accuracy", section_t(d, sec), len(d),
        {"accuracy": float(np.mean(acc)) if acc else None, "base_rate": float(np.mean(base)) if base else None,
         "majority_amp": majority_amp})
    return rows


def by_family(rows):
    """{family: {"heads", "readable", "unreadable"}} in FAMILY_ORDER (then any other)."""
    out = {}
    for r in rows:
        f = out.setdefault(r["family"], {"heads": 0, "readable": 0, "unreadable": 0})
        f["heads"] += 1
        f["readable" if r["readable"] else "unreadable"] += 1
    order = [f for f in FAMILY_ORDER if f in out] + sorted(set(out) - set(FAMILY_ORDER))
    return {f: out[f] for f in order}


def unreadable_heads(rows):
    """The heads R1 writes at S: (continuous names, switch names, mic names). An unreadable derived spring switch
    puts its whole spring (its level and the PR12's dwell) at S."""
    un = {r["name"] for r in rows if not r["readable"]}
    cont = {n for n in F.CONT if n in un}
    sw = {n for n in F.SW if n in un}
    D = F.by_name()
    for n in sw:
        if D[n].key == F.SPRING_KEY:
            cont |= {c for c in F.CONT if D[c].module == D[n].module and family_of_name(c) == "spring"}
    return sorted(cont), sorted(sw), sorted(n for n in F.CAT if n in un)


def heads_at_S(cont, sw_p, mics, unreadable):
    """The heads with every unreadable one unset (NaN, None), so `full_space.answer_settings` keeps S's value."""
    import numpy as np

    uc, us, uk = (set(v) for v in unreadable)
    c = np.array(cont, np.float64)
    for j, n in enumerate(F.CONT):
        if n in uc:
            c[j] = np.nan
    s = [None if n in us else float(sw_p[j]) for j, n in enumerate(F.SW)]
    k = [None if n in uk else mics[j] for j, n in enumerate(F.CAT)]
    return c, s, k


def r_answer(amp, S, r, med, b, unreadable):
    """D_F5:R: D_F5's pulled answer (A1 + A2 pulled by the FS5 fit; switches by the mean probability; mics by the
    mean's argmax) with every unreadable head at S's value."""
    from learn import direct_stems as DS

    cont = DS.pull(r["a2"], med, b)
    c, s, k = heads_at_S(cont, r["sw_p"], r["mics"], unreadable)
    return F.answer_settings(amp, S, c, s, k)


def r1_contrasts():
    """{name: (a, b)}: R1's rows, the time-effects row (F5's stored renders), then every F5 row beside."""
    out = {f"{R_ARM} - {T3.CORE} (R1, post hoc)": (R_ARM, T3.CORE),
           f"{R_ARM} - S": (R_ARM, "S"), f"{R_ARM} - constant": (R_ARM, T3.CONST),
           f"{R_ARM} - {T3.FULL} (what the at-S rule changes)": (R_ARM, T3.FULL),
           f"{R_ARM} - {TIME_ARM}": (R_ARM, TIME_ARM),
           f"{TIME_ARM} - {T3.CORE} (time effects only; F5's renders, already seen)": (TIME_ARM, T3.CORE)}
    out.update({f"F5: {k}": v for k, v in T3.contrasts().items()})
    return out


def r1_answers(dirs, cls_of, S_of, stored, med, table, un, sdict):
    """D_F5:R per direction from F5's stored D_F5 readout (`diag`), pulled by F5's fit, every unreadable head at
    S. Refuses unless F5's D_F5 answer rebuilds exactly from the same readout. -> ({key: {settings, held}},
    {key: the controls that differ from F5's D_F5})."""
    from learn import direct_stems as DS

    out, changed = {}, {}
    for slug, amp, search, held in dirs:
        cls = cls_of[slug]
        S = S_of(amp, cls)
        key = f"{slug}|{amp}|{search}"
        st = stored[key]
        r = stored_readout(st["diag"])
        b, _ = DS.cell_b(table, (amp, cls), F.cell_masks(amp)[0])
        m = med[(amp, cls)]
        if sdict(T3.full_answer(amp, S, r, m, b)) != st["settings"]:
            raise SystemExit(f"{key}: F5's D_F5 answer does not rebuild from its stored readout")
        x = sdict(r_answer(amp, S, r, m, b, un))
        out[key] = {"settings": x, "held": held}
        changed[key] = sorted(k for k in set(x) | set(st["settings"]) if x.get(k) != st["settings"].get(k))
    return out, changed


def renders_needed(groups):
    return RENDERS_PER_GROUP * groups


# --- I/O ---------------------------------------------------------------------------------------------------------

def out_dir(root):
    return T.stage_root(root, T3.STAGE) / R_DIR


def ledger_declared():
    d = json.loads((V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == T3.LEDGER_ID), {})
    return LEDGER_MARK in str(e.get(LEDGER_KEY, ""))


def require_r(args):
    T3.require_t3(args)
    if not args.smoke and not ledger_declared():
        raise SystemExit(f"the ledger's {T3.LEDGER_ID} has no {LEDGER_KEY} declaring '{LEDGER_MARK}': real runs refuse")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_fit(root):
    fit = _load(T.stage_root(root, T3.STAGE) / "fit.json")
    if not fit:
        raise SystemExit("F5's fit.json is missing")
    return fit


def print_r0(rows):
    print(f"R0, readability on FS5 ({STATUS}); readable iff the 90% interval excludes chance in the right direction")
    fam = by_family(rows)
    for f, c in fam.items():
        print(f"\n{f}: {c['readable']} readable of {c['heads']}")
        for r in (x for x in rows if x["family"] == f):
            iv = "no interval" if r["lo"] is None else f"[{r['lo']:+.3f}, {r['hi']:+.3f}]"
            pt = "n/a" if r["point"] is None else f"{r['point']:+.3f}"
            extra = ""
            if r["kind"] == "switch":
                extra = f" on-rate FS5 {r['on_rate_fs5']}, train {r['on_rate_train']}"
            elif r["kind"] == "accuracy":
                extra = f" accuracy {r['accuracy']}, base {r['base_rate']}"
            else:
                extra = f" E model {r['e_model']}, constant {r['e_constant']}"
            stat = {"switch": "AUC", "continuous": "E diff", "accuracy": "acc diff"}[r["kind"]]
            print(f"  {r['name']:34s} {stat:8s} {pt:>7s} {iv:20s} n {r['n']:4d} sec {r['sections']:2d} "
                  f"{'READABLE' if r['readable'] else 'unreadable'}{extra}")
    tot = sum(c["readable"] for c in fam.values())
    per = ", ".join(f"{f} {c['readable']}/{c['heads']}" for f, c in fam.items())
    print(f"\nR0: {tot} readable of {len(rows)} heads ({per})")


# --- R0 (zero renders; TORCH_PY) ----------------------------------------------------------------------------------

def cmd_r0(args):
    """Each D_F5 head's readability on FS5 against D_F5's constant (zero renders). Read once: an existing r0.json
    is kept."""
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS

    require_r(args)
    root = V.out_root(args)
    op = out_dir(root) / "r0.json"
    if op.exists():
        print(f"{op} exists: R0 is read once (the table it holds is the declared one)")
        print_r0(_load(op)["rows"])
        return
    plan = T3.load_plan(root, args.smoke)
    fit = load_fit(root)
    nets, recs = T3.load_models(root, T3.FULL, args.smoke)
    f = fit["models"][T3.FULL]
    if f["models"] != {str(r["seed"]): r["model_sha256"] for r in recs}:
        raise SystemExit("D_F5: fit.json was made with other models")
    ctx = DS.Ctx(quiet=True)
    tr_rows, fs_rows = T3.arm_rows(root, ctx, plan, T3.FULL)
    if [r["i"] for r in fs_rows] != fit["fs5_ids"]:
        raise SystemExit("FS5 differs from the set fit.json read")
    enc = T3.encode_for(T3.FULL)
    files = {r["i"]: T3.files_of(root, T3.FULL, r["i"]) for r in fs_rows}
    X, C, Y, who = T3.fs_tensors(fs_rows, files, lambda lab: enc(lab)[:6])
    outs = F.run_nets(nets, X, C)
    ex = per_example(outs, who, Y)
    info = {r["i"]: {"section": r["section"], "cell": (r["amp"], r["base"]), "amp": r["amp"]} for r in fs_rows}
    rates, majority = train_priors([enc(r["label"])[:6] for r in tr_rows], [r["amp"] for r in tr_rows])
    const = G.const_from_json(f["constant_answers"])
    rows = r0_rows(ex, info, const, rates, majority)
    un = unreadable_heads(rows)
    _save(op, {"plan": T.PLAN, "design": DESIGN, "stage": "T3 F5 follow-up R0", "status": STATUS,
               "rule": "readable iff the 90% interval excludes chance in the right direction (AUC lo > 0.5; E "
                       "difference hi < 0; accuracy difference lo > 0); otherwise unreadable, no interval included",
               "models": f["models"], "fit_time": fit.get("time"), "fs5_examples": len(ex),
               "fs5_sections": len({v["section"] for v in info.values()}), "majority_amp": majority,
               "rows": rows, "by_family": by_family(rows),
               "unreadable": {"continuous": un[0], "switch": un[1], "mic": un[2]},
               "smoke": bool(args.smoke), "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print_r0(rows)
    print(f"R0 DONE: {op}")


# --- R1 (MAIN) ----------------------------------------------------------------------------------------------------

def load_r0(root, smoke=False):
    r0 = _load(out_dir(root) / "r0.json")
    if not r0 or (r0.get("smoke") and not smoke):
        raise SystemExit("run `r0` first")
    return r0


def stored_readout(diag):
    import numpy as np

    return {"a2": np.asarray(diag["a2"], np.float64), "sw_p": np.asarray(diag["sw_p"], np.float64),
            "mics": list(diag["mics"])}


def cmd_r1_predict(args):
    """D_F5:R on V-real-11 (zero renders): F5's stored D_F5 readout (its `diag`), pulled by F5's fit, every
    R0-unreadable head at S. Refuses unless the rebuilt D_F5 answer equals F5's stored one in every direction."""
    from learn import arm_a_mega53 as A
    from learn import direct_stems as DS
    from learn import local_objective as LO

    require_r(args)
    root = V.out_root(args)
    plan = T3.load_plan(root, args.smoke)
    r0 = load_r0(root, args.smoke)
    fit = load_fit(root)
    pp = T.stage_root(root, T3.STAGE) / "vreal" / "predictions.json"
    pred = _load(pp)
    if not pred or (pred.get("smoke") and not args.smoke):
        raise SystemExit("F5's V-real predictions are missing")
    if pred["models"][T3.FULL] != fit["models"][T3.FULL]["models"] or r0["models"] != fit["models"][T3.FULL]["models"]:
        raise SystemExit("F5's predictions, fit and R0 were not made with the same D_F5 models")
    if pred["members"] != plan["vreal"]["members"]:
        raise SystemExit("F5's predictions were made for another V-real membership")
    dirs, parts, dropped = T3.vreal_dirs(root, plan, bool(pred.get("dropped_members")))
    if sorted(dropped) != sorted(pred.get("dropped_members") or []):
        raise SystemExit("V-real's parts changed since F5's predictions")
    f = fit["models"][T3.FULL]
    med, table = DS.medians_from_json(f["constant"]), DS.table_from_json(f["pull"])
    un = (r0["unreadable"]["continuous"], r0["unreadable"]["switch"], r0["unreadable"]["mic"])
    ms = A.L.menu_S()
    cls_of = {slug: T3.part_info(slug, parts[slug])[0] for slug in {d[0] for d in dirs}}
    out, changed = r1_answers(dirs, cls_of, lambda amp, cls: ms[amp][cls][1], pred["predictions"][T3.FULL],
                              med, table, un, LO.sdict)
    od = out_dir(root)
    _save(od / "r1-predictions.json", {
        "plan": T.PLAN, "design": DESIGN, "stage": "T3 F5 follow-up R1", "status": STATUS, "arm": R_ARM,
        "smoke": bool(args.smoke), "members": plan["vreal"]["members"], "dropped_members": dropped,
        "directions": len(dirs), "predictions": {R_ARM: out}, "changed_from_D_F5": changed,
        "unreadable": r0["unreadable"], "r0_sha256": sha(od / "r0.json"), "f5_predictions_sha256": sha(pp),
        "models": pred["models"], "output_gain": "S's here; fitted per answer at render (" + F.OUTPUT_FIT_STATUS + ")",
        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    groups = len({(s, a) for s, a, _, _ in dirs})
    n_changed = sum(1 for v in changed.values() if v)
    print(f"R1 PREDICT: {len(dirs)} directions; {n_changed} differ from F5's D_F5; {groups} groups, "
          f"{renders_needed(groups)} renders to come")


def cmd_r1_render(args):
    """D_F5:R's V-real renders for one shard of (part, amp) groups: one discarded priming render at S, then the
    answer once per direction, judged on both halves; output gain fitted to the stem's loudness and its |LUFS error|
    recorded. isolate=True; at most 3 render processes machine-wide; the 31 GB disk guard; a done group is kept."""
    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS

    require_r(args)
    root = V.out_root(args)
    plan = T3.load_plan(root, args.smoke)
    od = out_dir(root)
    pred = _load(od / "r1-predictions.json")
    if not pred or (pred.get("smoke") and not args.smoke):
        raise SystemExit("run `r1-predict` first")
    if pred["members"] != plan["vreal"]["members"]:
        raise SystemExit("R1's predictions were made for another V-real membership")
    if pred["r0_sha256"] != sha(od / "r0.json"):
        raise SystemExit("r0.json changed since r1-predict")
    dirs, parts, dropped = T3.vreal_dirs(root, plan, bool(pred.get("dropped_members")))
    if sorted(dropped) != sorted(pred.get("dropped_members") or []):
        raise SystemExit("V-real's parts changed since r1-predict")
    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"free disk below {T.DISK_GUARD_GB:.0f} GB")
    man = DS._load(DS.stems_manifest_path(DS.ROOT, T.SEP))
    mine = DE.shard(A.groups(dirs), args.shard)
    LO._wait_cap()
    DS.wait_render_slot()
    rr = A.renderer()
    ms = A.L.menu_S()
    try:
        menu = rr.menu()
        for slug, amp in mine:
            gp = od / "groups" / f"{slug}|{amp}.json"
            if (_load(gp) or {}).get("status") == "done":
                continue
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            info = parts[slug]
            ctx = (A.group_ctx(menu, ms, "F", slug, amp) if info["kind"] == "stagef"
                   else T3.t3_group_ctx(menu, ms, info, amp))
            if K.key(dict(ctx["S"])) != K.key(ctx["S_stored"]):
                raise SystemExit(f"{amp}: the live S differs from the stored copy")
            g = {"sel": ctx["sel"], "S": ctx["S"], "di": ctx["di"], "di32": ctx["di32"], "ref": ctx["ref"],
                 "lag": ctx["part"]["judge_lag"]}
            stem = DS.stored_stem(man, f"stagef/{slug}") if info["kind"] == "stagef" else T3.crop_stem(info)
            settings = {R_ARM: {sh: LO.tdict(pred["predictions"][R_ARM][f"{slug}|{amp}|{sh}"]["settings"])
                                for sh, _ in K.DIRECTIONS}}
            held_of = dict(K.DIRECTIONS)
            checks = {}

            def keep(arm, search, y, settings=settings, stem=stem, ref=g["ref"], checks=checks):
                gain = float(settings[arm][search].get(F.OUTPUT, "0"))
                checks[f"{arm}|{search}"] = T3.lufs_check(gain, y, stem, ref, search, held_of[search])

            rec = DS.run_group(rr, g, settings, False, None, K.judge, keep=keep, arms=(R_ARM,))
            rec.update(slug=slug, amp=amp, lufs=checks, output_gain_fit=F.OUTPUT_FIT_STATUS, status_r=STATUS)
            _save(gp, rec)
            print(slug, amp, rec["renders"], flush=True)
    finally:
        rr.close()
    print(f"R1 RENDER DONE {args.shard[0]}/{args.shard[1]}; renders {rr.count}")


def cmd_r1_report(args):
    """R1's rows (post hoc, descriptive): D_F5:R against D_core5, S, the constant, D_F5 and D_F5 with time effects
    at S; the time-effects row from F5's renders; every F5 row beside. Band-weighted, 90% band-clustered t, per
    class and V-real-10 beside."""
    from learn import arm_a_mega53 as A
    from learn import direct_stems as DS
    from learn import perfect_sep_arm as P

    require_r(args)
    root = V.out_root(args)
    plan = T3.load_plan(root, args.smoke)
    od = out_dir(root)
    f5d = T.stage_root(root, T3.STAGE) / "vreal"
    pred = _load(f5d / "predictions.json") or {}
    rp = _load(od / "r1-predictions.json") or {}
    members = set(plan["vreal"]["members"]) - set(pred.get("dropped_members") or [])
    v10 = set(plan["vreal"]["v_real_10"])
    crops = (_load(T3.crops_manifest_path(root)) or {}).get("crops") or {}
    parts, _ = T3.vreal_parts(sorted(members), A.pool_slugs(), crops, drop_missing=True)
    units = [u for u in P.build_units() if u["slug"] in members] + T3.t3_units(parts, f5d / "groups")
    cache, t2g = {}, {}

    def value(arm):
        def f(u):
            k = (u["slug"], u["amp"])
            if arm == T3.D_SYN:
                if k not in t2g:
                    t2g[k] = _load(T.stage_root(root, "t2") / "vreal" / "groups" / f"{u['slug']}|{u['amp']}.json") or {}
                return T.group_value(t2g[k], {}, "SYN", u["search"], u["held"])
            d = od if arm == R_ARM else f5d
            ck = (str(d), *k)
            if ck not in cache:
                cache[ck] = _load(d / "groups" / f"{u['slug']}|{u['amp']}.json") or {}
            gr = cache[ck]
            if gr.get("status") != "done":
                return None
            return ((gr.get("judge") or {}).get(f"{arm}|{u['search']}") or {}).get(u["held"])
        return f

    refused = {a: DS.add_step4_arm(units, a, value(a)) for a in T3.ANSWERS + (T3.D_SYN, R_ARM)}
    gaps = [f"{n} directions have no {a} value" for a in T3.ANSWERS + (R_ARM,)
            if (n := sum(1 for u in units if u["d"].get(a) is None))]
    bad = {a: n for a, n in refused.items() if n and a != T3.D_SYN}
    if bad:
        gaps.append(f"refused answers scored as S {bad}")
    rows_ = ("all", "v_real_10")
    filt = {"all": lambda u: True, "v_real_10": lambda u: u["slug"] in v10}
    con = {name: DS.step4_contrast(units, a, b, filt, rows=rows_, fixed=("S",)) for name, (a, b) in r1_contrasts().items()}
    lufs = {}
    for (d, *_), gr in cache.items():
        if d == str(od):
            for k, v in (gr.get("lufs") or {}).items():
                lufs.setdefault(k.split("|")[0], []).append(v)
    renders = sum((_load(p) or {}).get("renders", 0) for p in (od / "groups").glob("*.json"))
    rep = {"plan": T.PLAN, "design": DESIGN, "stage": "T3 F5 follow-up R1", "status": STATUS,
           "v_real": sorted(members), "directions": len(units), "complete": not gaps, "incomplete_because": gaps,
           "refused_scored_as_S": refused, "unreadable": rp.get("unreadable"), "contrasts": con,
           "abs_lufs_error": {a: T3.lufs_summary(v) for a, v in lufs.items()}, "renders": renders,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(od / "r1-report.json", rep)
    print(f"T3 F5 follow-up R1 ({STATUS}): V-real {len(members)} parts ({len(units)} directions); renders {renders}")
    for g in gaps:
        print(f"  incomplete: {g}")
    for name, c in con.items():
        for row in rows_:
            r = c["rows"].get(row) or {}
            for cls, s in [("", r.get("all") or {})] + sorted((r.get("per_class") or {}).items()):
                sign = f"; bands -/+ {s.get('bands_negative')}/{s.get('bands_positive')}" if s.get("bands") else ""
                print(f"  {name if not cls and row == 'all' else '':78s} {(row + ' ' + cls).strip():18s} "
                      f"{s.get('band_weighted_mean')} [{s.get('lo90')}, {s.get('hi90')}] ({s.get('bands')} bands{sign}) "
                      f"{T3.rule_reading(s)}")
    print(f"|LUFS error| (a pipeline check): {rep['abs_lufs_error']}")
    print("R1 REPORT DONE (post hoc, descriptive; not a gate)")


# --- main ---------------------------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(prog="trusted_data_t3_r", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("r0", "r1-predict", "r1-render", "r1-report"))
    ap.add_argument("--shard", type=V.parse_shard, default=(0, 1))
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args(argv)
    if args.shard != (0, 1) and args.cmd != "r1-render":
        raise SystemExit("--shard is for r1-render")
    return {"r0": cmd_r0, "r1-predict": cmd_r1_predict, "r1-render": cmd_r1_render, "r1-report": cmd_r1_report}[args.cmd](args)


if __name__ == "__main__":
    main()
