"""N8: does the separated guitar lean toward the loudest other guitar? (`docs/stem-lean-plan.md`; ledger `phase_stem_lean`.)
The deep review's step 4: from the stem, an amp reader hit the dominant other guitar's amp more than the target's, with
no interval. Zero renders, zero separations, no training beyond linear probes; the tone probe's split on T2's core twins, whose targets and other guitars share one
kind of preset draw. V-real, the NS songs, the panel and the captures are not read.

    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python   # `reads_v3` imports torch
    PYTHONPATH=. $TORCH_PY -m learn.stem_lean              # tone-probe/stem-lean.json, read once

Two linear readers per input, as `tone_info_probe.fit_probe`, on the rows whose loudest other guitar is not a double of
the target: T learns the target's labels, O the loudest other's, each conditioned on its own amp and class, with the
constant of its own labels.
"""

from __future__ import annotations

import argparse
import math
import time

import numpy as np

from learn import tone_info_probe as P

OUT = "stem-lean.json"
FEATS = "stem-lean-features.npz"
INPUTS = {"c": "stem", "b": "mix", "a": "target"}
FAMILY = "today"


# --- pure -----------------------------------------------------------------------------------------------------------

def dominant(others):
    """The loudest other guitar in a mix, by its render's level plus its gain; None if there is none or it is a double
    of the target, which shares the target's preset."""
    if not others:
        return None
    o = max(others, key=lambda x: x["render_lufs"] + x["gain_db"])
    return None if o.get("dt") else o


def other_rows(rows, render, plan_others):
    """`rows` with a dominant other, as (the target's row, the same row carrying that other's amp, class and label)."""
    pairs = []
    for r in rows:
        o = dominant(render[r["i"]]["others"])
        if o is None:
            continue
        draw = next(p["draw"] for p in plan_others[r["i"]] if p["di"] == o["di"] and isinstance(p["draw"], dict))
        pairs.append((r, {**r, "amp": o["amp"], "base": draw["base"], "mode": draw["mode"], "settings": o["settings"],
                          "label": {"amp": o["amp"], "settings": o["settings"]}}))
    return pairs


def core_rows(rows):
    """`rows` labelled by their full settings: a core row's own `label` is today's, unit-scaled, and `encode` needs these."""
    return [{**r, "label": {"amp": r["amp"], "settings": r["settings"]}} for r in rows]


def hits(prob, amps, names):
    """1 where the amp head's top answer is the example's amp, else 0. prob: [n, amps]; amps: names; names: the order."""
    top = np.argmax(np.asarray(prob), axis=1)
    return (top == np.array([names.index(a) for a in amps])).astype(np.float64)


def group_rows(answers, y_t, y_o):
    """(r with the target, r with the other) over pooled entries, already demeaned."""
    def r(a, b):
        va, vb = float((a * a).sum()), float((b * b).sum())
        return float((a * b).sum() / math.sqrt(va * vb)) if va > 0 and vb > 0 else float("nan")
    return r(answers, y_t), r(answers, y_o)


def demean(values, cells):
    """`values` less their mean within each cell."""
    v = np.asarray(values, np.float64).copy()
    c = np.asarray(cells)
    for k in set(c.tolist()):
        m = c == k
        v[m] -= v[m].mean()
    return v


def clean_of_cells(values, target_cells, section_cells):
    """`values` less T's conditioning, then less section and head: an answer that only knows the cell reads zero."""
    return demean(demean(values, target_cells), section_cells)


def jackknife(point_fn, sections, t90):
    """A statistic of a section subset with its delete-one-section 90% t interval. point_fn(mask) -> float."""
    s = np.asarray(sections)
    names = sorted(set(s.tolist()))
    pt = point_fn(np.ones(len(s), bool))
    th = np.array([point_fn(s != n) for n in names])
    n = len(th)
    h = t90(n - 1) * math.sqrt((n - 1) / n * float(((th - th.mean()) ** 2).sum()))
    return {"point": pt, "lo": pt - h, "hi": pt + h, "sections": n}


def clear(row, above):
    """True if a row's interval clears zero on that side."""
    if row["lo"] is None or row["hi"] is None:
        return False
    return row["lo"] > 0 if above else row["hi"] < 0


def reading(lean_stem, follow_stem, lean_mix, stem_minus_mix, control_holds):
    """The declared map, first match: `lean_*` O's amp hits less T's; `stem_minus_mix` that lean on the stem less on the
    mix, paired by example; `follow_stem` T's answers on the target's amp less the other's on rows whose amps differ;
    `control_holds`, on the clean target T's amp head reads and O's does not."""
    if not control_holds:
        return "void"
    if clear(lean_stem, True):
        if clear(stem_minus_mix, True):
            return "the lead holds"
        return "already in the mix" if clear(lean_mix, True) else "not shown"
    if clear(lean_stem, False) and clear(follow_stem, True):
        return "the lead does not hold"
    return "not shown"


# --- the stored data --------------------------------------------------------------------------------------------------

def _feats(job):
    """One example's core-twin summaries: (a) its target, (b) its mix, (c) its stem."""
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    root, i = job
    g, m, x = np.load(PS.example_path(i)), np.load(T.ex_path(root, "t2", i, "mix-t2")), np.load(T.ex_path(root, "t2", i, "xlance_g-t2"))
    return i, {"a": P.mel_summary({"A": g["gA"], "B": g["gB"]}), "b": P.mel_summary({"A": m["mA"], "B": m["mB"]}),
               "c": P.mel_summary({"A": x["sA"], "B": x["sB"]})}


def features(root, rows):
    """The summaries, cached apart from the tone probe's, which are the full twins'. -> {key: {id: summary}}."""
    from multiprocessing import Pool

    path = P.out_dir(root) / FEATS
    if not path.exists():
        with Pool(P.WORKERS) as pool:
            got = dict(pool.imap_unordered(_feats, [(root, r["i"]) for r in rows], chunksize=16))
        ids = sorted(got)
        np.savez(path, ids=np.array(ids), **{k: np.stack([got[i][k] for i in ids]) for k in INPUTS})
    z = np.load(path)
    pos = {int(i): n for n, i in enumerate(z["ids"])}
    return {k: z[k] for k in INPUTS}, pos


def encode(label):
    from learn import full_space as F

    return F.encode({tuple(k.rsplit("/", 1)): v for k, v in label["settings"].items()}, label["amp"])


def prepared(tr, fs, arrays, pos):
    """What `tone_info_probe.fit_input` reads, for one reader: its own labels, cells and constant over its training rows."""
    from learn import direct_sound_gate as G
    from learn import full_space as F
    from learn import song_model as SM
    from learn import trusted_data_t3_r as R

    const = G.constant_answers(tr, lambda lab: encode(lab)[:6], len(F.CONT), len(F.SW), len(F.CAT))

    def labels(rows):
        L = [encode(r["label"])[:6] for r in rows]
        return [np.stack([np.asarray(t[q], np.float64) for t in L]) for q in range(6)] + [
            np.array([F.AMPS.index(r["amp"]) for r in rows])]

    def X_of(key, rows):
        return np.zeros((len(rows), 1)) if key == "cond" else arrays[key][[pos[r["i"]] for r in rows]]

    rates, majority = R.train_priors([encode(r["label"])[:6] for r in tr], [r["amp"] for r in tr])
    return {"X_of": X_of,
            "cond": lambda rows: np.stack([SM.cond_vec(r["amp"], r["base"], [0.0, 0.0])[:len(SM.AMPS) + len(SM.CLASSES)]
                                           for r in rows]),
            "lab_tr": labels(tr), "lab_te": labels(fs), "const": const,
            "const_tr": np.stack([np.asarray(const[(r["amp"], r["base"])]["cont"], np.float64) for r in tr]),
            "const_te": np.stack([np.asarray(const[(r["amp"], r["base"])]["cont"], np.float64) for r in fs]),
            "sec_tr": np.array([r["section"] for r in tr]), "rates": rates, "majority": majority,
            "info": {r["i"]: {"section": r["section"], "cell": (r["amp"], r["base"]), "amp": r["amp"]} for r in fs},
            "sec": {r["i"]: r["section"] for r in fs}, "ids": [r["i"] for r in fs]}


def read_rows(S, P_):
    """R0's table for one fit."""
    from learn import trusted_data_t3_r as R

    t = S["lab_te"]
    ex = {i: {"a2": P_["a2"][n], "sw_p": P_["sw_p"][n], "mic_p": [m[n] for m in P_["mic_p"]], "amp_p": P_["amp_p"][n],
              "c": t[0][n], "cm": t[1][n], "s": t[2][n], "sm": t[3][n], "k": t[4][n], "km": t[5][n]}
          for n, i in enumerate(S["ids"])}
    return R.r0_rows(ex, S["info"], S["const"], S["rates"], S["majority"])


def main(argv=None):
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import pipeline_fix as PF
    from learn import pretrain_set as PS
    from learn import reads_v3 as RV
    from learn import trusted_data as T
    from learn import trusted_data_t3 as T3
    from learn import trusted_data_t3_r as R
    from learn import verify_tracks as V

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    PF.require("phase_stem_lean")
    root = V.OUT
    od = P.out_dir(root)
    if (od / OUT).exists() and not a.force:
        raise SystemExit(f"{od / OUT} exists: the read is run once (--force to rewrite)")
    plan = V._load(T.plan_path(root, T3.STAGE))
    if not plan or plan.get("smoke"):
        raise SystemExit("T3's plan is missing")
    tr, fs = T3.arm_rows(root, DS.Ctx(quiet=True), plan, T3.CORE)
    if set(r["section"] for r in tr) & set(r["section"] for r in fs):
        raise SystemExit("the training and FS5 sections overlap")
    render = T.rows_of(root, "t2", "render")
    plan_others = {x["i"]: x["others"] for x in V._load(T.plan_path(root, "t2"))["examples"]}
    ptr, pfs = other_rows(core_rows(tr), render, plan_others), other_rows(core_rows(fs), render, plan_others)
    tr_t, tr_o = [p[0] for p in ptr], [p[1] for p in ptr]
    fs_t, fs_o = [p[0] for p in pfs], [p[1] for p in pfs]
    arrays, pos = features(root, tr_t + fs_t)
    ST, SO = prepared(tr_t, fs_t, arrays, pos), prepared(tr_o, fs_o, arrays, pos)
    sec = np.array([r["section"] for r in fs_t])
    amps_t, amps_o = [r["amp"] for r in fs_t], [r["amp"] for r in fs_o]
    cell_t = [f"{r['amp']}|{r['base']}" for r in fs_t]
    differ = np.array([x != y for x, y in zip(amps_t, amps_o)])
    no_wide = np.array([t["mode"] != "wide" and o["mode"] != "wide" for t, o in zip(fs_t, fs_o)])
    by_id = dict(enumerate(sec.tolist()))
    lean_of = {}
    t0 = time.time()
    rec = {"design": "docs/stem-lean-plan.md", "train": len(tr_t), "fs5": len(fs_t), "fs5_of": len(fs), "train_of": len(tr),
           "amps_differ": int(differ.sum()), "sections": len(set(sec.tolist())), "inputs": {}}
    today = lambda rows: [r for r in rows if r["family"] in (FAMILY, "amp_choice")]  # noqa: E731
    pc_t, pc_o = P.fit_input(ST, "cond", tr_t, fs_t)[0], P.fit_input(SO, "cond", tr_o, fs_o)[0]
    rec["conditioning_alone_today"] = {"T": sum(r["readable"] for r in today(read_rows(ST, pc_t))),
                                       "O": sum(r["readable"] for r in today(read_rows(SO, pc_o)))}
    for key, name in INPUTS.items():
        pt, po = P.fit_input(ST, key, tr_t, fs_t)[0], P.fit_input(SO, key, tr_o, fs_o)[0]
        rt, ro = read_rows(ST, pt), read_rows(SO, po)
        ht, ho = hits(pt["amp_p"], amps_t, F.AMPS), hits(po["amp_p"], amps_o, F.AMPS)
        on_t, on_o = ht[differ], hits(pt["amp_p"], amps_o, F.AMPS)[differ]
        groups = {}
        for g, heads in RV.HEADS.items():
            ans, yt, yo, cells, tcells, secs = [], [], [], [], [], []
            for j in heads:
                m = (ST["lab_te"][1][:, j] > 0) & (SO["lab_te"][1][:, j] > 0)
                ans.append(pt["a2"][m, j]); yt.append(ST["lab_te"][0][m, j]); yo.append(SO["lab_te"][0][m, j])
                cells += [f"{s_}|{j}" for s_ in sec[m]]; secs += sec[m].tolist()
                tcells += [f"{c}|{j}" for c, ok in zip(cell_t, m) if ok]
            ans, yt, yo = (clean_of_cells(np.concatenate(v), tcells, cells) for v in (ans, yt, yo))
            secs = np.array(secs)

            def diff(k):
                r_t, r_o = group_rows(ans[k], yt[k], yo[k])
                return r_t - r_o
            r_t, r_o = group_rows(ans, yt, yo)
            groups[g] = {"n": len(ans), "r_target_minus_other": jackknife(diff, secs, PS.t90), "r_target": r_t, "r_other": r_o}
        amp = {w: next(r for r in rows if r["name"] == R.AMP_NAME) for w, rows in (("T", rt), ("O", ro))}
        rec["inputs"][key] = {
            "name": name, "amp_hit_T": float(ht.mean()), "amp_hit_O": float(ho.mean()),
            "majority_share_T": float(np.mean([x == ST["majority"] for x in amps_t])),
            "majority_share_O": float(np.mean([x == SO["majority"] for x in amps_o])),
            "amp_readable": {w: bool(r["readable"]) for w, r in amp.items()},
            "lean_O_minus_T": R.section_t(dict(enumerate((ho - ht).tolist())), by_id),
            "lean_neither_wide": R.section_t({n: float(v) for n, v in enumerate(ho - ht) if no_wide[n]}, by_id),
            "follow_target_minus_other": R.section_t(dict(enumerate((on_t - on_o).tolist())),
                                                     dict(enumerate(sec[differ].tolist()))),
            "readable_T": sum(r["readable"] for r in rt), "readable_O": sum(r["readable"] for r in ro),
            "today_readable_T": sum(r["readable"] for r in today(rt)), "today_readable_O": sum(r["readable"] for r in today(ro)),
            "groups": groups}
        lean_of[key] = ho - ht
        x = rec["inputs"][key]
        print(f"({key}) {name}: amp hit T {x['amp_hit_T']:.3f} O {x['amp_hit_O']:.3f}, lean {x['lean_O_minus_T']}, follow "
              f"{x['follow_target_minus_other']}, today readable T {x['today_readable_T']} O {x['today_readable_O']} "
              f"({time.time() - t0:.0f} s)", flush=True)
    c, b, t = (rec["inputs"][k] for k in "cba")
    rec["control_holds"] = t["amp_readable"]["T"] and not t["amp_readable"]["O"]
    rec["neither_wide"] = int(no_wide.sum())
    rec["stem_minus_mix"] = R.section_t(dict(enumerate((lean_of["c"] - lean_of["b"]).tolist())), by_id)
    rec["branch"] = reading(c["lean_O_minus_T"], c["follow_target_minus_other"], b["lean_O_minus_T"], rec["stem_minus_mix"],
                            rec["control_holds"])
    rec["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    V._save(od / OUT, rec)
    print(f"BRANCH: {rec['branch']}\nLEAN DONE: {od / OUT}")


if __name__ == "__main__":
    main()
