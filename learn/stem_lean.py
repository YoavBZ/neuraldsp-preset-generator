"""N8: does the separated guitar lean toward the loudest other guitar? (`docs/stem-lean-plan.md`; ledger `phase_stem_lean`.)
The deep review's step 4: from the stem, an amp reader hit the dominant other guitar's amp more than the target's, with
no interval. Zero renders, zero separations, no training beyond linear probes; F5's examples and FS5, whose mixes carry
other guitars with their own presets. V-real, the NS songs, the panel and the captures are not read.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    PYTHONPATH=. $MAIN -m learn.stem_lean                 # tone-probe/stem-lean.json, read once

Two linear readers per input, as `tone_info_probe.fit_probe`, on the rows whose loudest other guitar is not a double of
the target: T learns the target's labels, O the loudest other's, each conditioned on its own amp and class.
"""

from __future__ import annotations

import argparse
import math
import time

import numpy as np

from learn import tone_info_probe as P

OUT = "stem-lean.json"
INPUTS = {"c": "stem", "b": "mix", "a": "target"}
FAMILY = "today"
AMP_NAME = "amp choice"


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
        base = next(p["draw"]["base"] for p in plan_others[r["i"]] if p["di"] == o["di"] and isinstance(p["draw"], dict))
        pairs.append((r, {**r, "amp": o["amp"], "base": base, "label": {"amp": o["amp"], "settings": o["settings"]},
                          "target_gap_db": o["render_lufs"] + o["gain_db"]}))
    return pairs


def hits(prob, amps, names):
    """1 where the amp head's top answer is the example's amp, else 0. prob: [n, amps]; amps: names; names: the order."""
    top = np.argmax(np.asarray(prob), axis=1)
    return (top == np.array([names.index(a) for a in amps])).astype(np.float64)


def group_rows(answers, y_t, y_o, sections):
    """(r with the target, r with the other) over pooled entries, each array demeaned by the caller's cell."""
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


def jackknife(point_fn, sections, t90):
    """A statistic of a section subset with its delete-one-section 90% t interval. point_fn(mask) -> float."""
    s = np.asarray(sections)
    names = sorted(set(s.tolist()))
    pt = point_fn(np.ones(len(s), bool))
    th = np.array([point_fn(s != n) for n in names])
    n = len(th)
    h = t90(n - 1) * math.sqrt((n - 1) / n * float(((th - th.mean()) ** 2).sum()))
    return {"point": pt, "lo": pt - h, "hi": pt + h, "sections": n}


def reading(lean, follow):
    """The declared map from the stem's rows: `lean` (O's amp hits less T's), `follow` (T's answers on the target's amp
    less the other's, on rows whose amps differ)."""
    if lean["lo"] is not None and lean["lo"] > 0:
        return "the lead holds"
    if lean["hi"] is not None and lean["hi"] < 0 and follow["lo"] is not None and follow["lo"] > 0:
        return "the lead does not hold"
    return "not shown"


# --- the stored data --------------------------------------------------------------------------------------------------

def prepared(root, tr, fs):
    """What `tone_info_probe.fit_input` reads, on these rows' labels, cells and stored summaries."""
    from learn import direct_sound_gate as G
    from learn import full_space as F
    from learn import song_model as SM
    from learn import trusted_data_t3 as T3
    from learn import trusted_data_t3_r as R

    z = np.load(P.out_dir(root) / "features.npz")
    pos = {int(i): n for n, i in enumerate(z["ids"])}
    arrays = {k: z[k] for k in INPUTS}
    const = G.const_from_json(R.load_fit(root)["models"][T3.FULL]["constant_answers"])
    enc = T3.encode_for(T3.FULL)

    def labels(rows):
        L = [enc(r["label"])[:6] for r in rows]
        return [np.stack([np.asarray(t[q], np.float64) for t in L]) for q in range(6)] + [
            np.array([F.AMPS.index(r["amp"]) for r in rows])]

    rates, majority = R.train_priors([enc(r["label"])[:6] for r in tr], [r["amp"] for r in tr])
    return {"X_of": lambda key, rows: arrays[key][[pos[r["i"]] for r in rows]],
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
    from learn import full_space as F
    from learn import pipeline_fix as PF
    from learn import pretrain_set as PS
    from learn import reads_v3 as RV
    from learn import trusted_data as T
    from learn import trusted_data_t3_r as R
    from learn import verify_tracks as V

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    PF.require("phase_stem_lean")
    root, _, tr, fs, _ = P.load_sets()
    od = P.out_dir(root)
    if (od / OUT).exists() and not a.force:
        raise SystemExit(f"{od / OUT} exists: the read is run once (--force to rewrite)")
    render = T.rows_of(root, "t2", "render")
    plan_others = {x["i"]: x["others"] for x in V._load(T.plan_path(root, "t2"))["examples"]}
    ptr, pfs = other_rows(tr, render, plan_others), other_rows(fs, render, plan_others)
    tr_t, tr_o = [p[0] for p in ptr], [p[1] for p in ptr]
    fs_t, fs_o = [p[0] for p in pfs], [p[1] for p in pfs]
    ST, SO = prepared(root, tr_t, fs_t), prepared(root, tr_o, fs_o)
    sec = np.array([r["section"] for r in fs_t])
    amps_t, amps_o = [r["amp"] for r in fs_t], [r["amp"] for r in fs_o]
    differ = np.array([x != y for x, y in zip(amps_t, amps_o)])
    t0 = time.time()
    rec = {"design": "docs/stem-lean-plan.md", "train": len(tr_t), "fs5": len(fs_t), "fs5_of": len(fs), "train_of": len(tr),
           "amps_differ": int(differ.sum()), "sections": len(set(sec.tolist())), "inputs": {}}
    for key, name in INPUTS.items():
        pt, po = P.fit_input(ST, key, tr_t, fs_t)[0], P.fit_input(SO, key, tr_o, fs_o)[0]
        rt, ro = read_rows(ST, pt), read_rows(SO, po)
        ht, ho = hits(pt["amp_p"], amps_t, F.AMPS), hits(po["amp_p"], amps_o, F.AMPS)
        follow_t, follow_o = hits(pt["amp_p"], amps_t, F.AMPS)[differ], hits(pt["amp_p"], amps_o, F.AMPS)[differ]
        groups = {}
        for g, heads in RV.HEADS.items():
            ans, yt, yo, cells, secs = [], [], [], [], []
            for j in heads:
                m = (ST["lab_te"][1][:, j] > 0) & (SO["lab_te"][1][:, j] > 0)
                ans.append(pt["a2"][m, j]); yt.append(ST["lab_te"][0][m, j]); yo.append(SO["lab_te"][0][m, j])
                cells += [f"{s}|{j}" for s in sec[m]]; secs += sec[m].tolist()
            ans, yt, yo = (demean(np.concatenate(v), cells) for v in (ans, yt, yo))
            secs = np.array(secs)

            def diff(k):
                r_t, r_o = group_rows(ans[k], yt[k], yo[k], None)
                return r_t - r_o
            groups[g] = {"n": len(ans), "r_target_minus_other": jackknife(diff, secs, PS.t90),
                         "r_target": group_rows(ans, yt, yo, None)[0], "r_other": group_rows(ans, yt, yo, None)[1]}
        today = lambda rows: [r for r in rows if r["family"] == FAMILY or r["family"] == "amp_choice"]  # noqa: E731
        rec["inputs"][key] = {
            "name": name, "amp_hit_T": float(ht.mean()), "amp_hit_O": float(ho.mean()),
            "majority_share_T": float(np.mean([x == ST["majority"] for x in amps_t])),
            "majority_share_O": float(np.mean([x == SO["majority"] for x in amps_o])),
            "lean_O_minus_T": R.section_t(dict(enumerate((ho - ht).tolist())), dict(enumerate(sec.tolist()))),
            "follow_target_minus_other": R.section_t(dict(enumerate((follow_t - follow_o).tolist())),
                                                     dict(enumerate(sec[differ].tolist()))),
            "readable_T": sum(r["readable"] for r in rt), "readable_O": sum(r["readable"] for r in ro),
            "today_readable_T": sum(r["readable"] for r in today(rt)), "today_readable_O": sum(r["readable"] for r in today(ro)),
            "groups": groups}
        x = rec["inputs"][key]
        print(f"({key}) {name}: amp hit T {x['amp_hit_T']:.3f} O {x['amp_hit_O']:.3f}, lean {x['lean_O_minus_T']}, follow "
              f"{x['follow_target_minus_other']}, today readable T {x['today_readable_T']} O {x['today_readable_O']} "
              f"({time.time() - t0:.0f} s)", flush=True)
    c = rec["inputs"]["c"]
    rec["branch"] = reading(c["lean_O_minus_T"], c["follow_target_minus_other"])
    rec["control_clean_O_reads_nothing"] = rec["inputs"]["a"]["today_readable_O"]
    rec["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    V._save(od / OUT, rec)
    print(f"BRANCH: {rec['branch']}\nLEAN DONE: {od / OUT}")


if __name__ == "__main__":
    main()
