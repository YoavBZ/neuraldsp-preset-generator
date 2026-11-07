"""S11, reading more of a song (`docs/efficientat-plan.md`): does an answer read over more of a take sit closer to its rig's label?
No training and no render. The same fitted readers read more sections; the label is always the rig's own.

    $TORCH_PY -m learn.eat_windows bks                      # S11.1, stored answers, single sections against the rig mean
    $TORCH_PY -m learn.eat_windows check                    # the chain on labelled windows against their stored inputs
    $TORCH_PY -m learn.eat_windows windows --shard 0/3      # S11.2, GOAT's other windows through the unit's own chain (CPU)
    $TORCH_PY -m learn.eat_windows read                     # S11.2's read, `M-pcs`, by the fold's own fit
    $TORCH_PY -m learn.eat_windows predict --tag M-win      # S11.3's answers, CPU, zero renders; then `eat_render render` and `report`

It reads BKS and GOAT only. Levels and backing ids come from each unit's stored variant 0. `base_rows` goes through `recipe_inputs`,
as every read does, for ids and refusals only.
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import math
import pathlib
import pickle
import random
import sys
import time
import zipfile
import zlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learn import bakeoff as B               # noqa: E402
from learn import eat_read as ER             # noqa: E402

EAT = "eat"                                  # under out_dir()
SEED = 20261221
MORE = 5                                     # other windows at most, S11
BKS_K = (1, 2, 3, 5)
BKS_DRAWS = 200
BKS_READERS = ("M-pcs", "E-mix", "W-pcs", "EW-mix", "FTM")
ALL = "all"                                  # every section or window of the rig


def stored_rows():
    """The read's stored rows with `EW-mix` joined by position. No reader is refitted."""
    from learn import pipeline_fix as P

    root = P.out_dir() / EAT
    rows = pickle.loads((root / "read.json.rows.pkl").read_bytes())
    for k in range(ER.FOLDS):                          # S8.3b's fixed answers: the column in `s83-read`'s rows is the read before the scaling fix
        mu = np.load(root / "reads" / "mn10_as-pub-pc64" / "ew" / "answers" / f"EW-mix-k{k}.npz")["mu"]
        fold = [r for r in rows if r["fold"] == k]
        if len(fold) != len(mu):
            raise SystemExit(f"fold {k}: {len(fold)} rows, {len(mu)} answers")
        for r, v in zip(fold, mu):
            r["EW-mix_ans"] = v
    return rows


def picked(n, k, rng):
    """Which of a rig's n sections a k-section read averages; all of them at `ALL`."""
    return np.arange(n) if k == ALL or k >= n else rng.choice(n, k, replace=False)


def rig_rng(seed, draw, cell, rig):
    """A draw's choice for one rig, the same whichever other rigs a jackknife leaves out."""
    return np.random.default_rng([seed, draw, zlib.crc32(repr((cell, rig)).encode())])


def section_blocks(rows, label, k, seed=SEED, draw=0):
    """`reads_v3.blocks` with the answer averaged over k of the rig's sections and the label over all of them."""
    from learn import reads_v3 as R

    cells = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        cells[(r["fold"], r["amp"], r["cls"])][r["rec"]].append(r)
    out = []
    for cell, recs in cells.items():
        amp, cls = cell[1:]
        use = np.nonzero(R.searched(amp, cls)[0])[0]
        items = []
        for rig, rr in sorted(recs.items()):
            C, M = np.array([r["c"] for r in rr], float), np.array([r["cm"] for r in rr], float)
            lab = np.where(M.sum(0) > 0, (C * M).sum(0) / np.maximum(M.sum(0), 1), np.nan)
            some = picked(len(rr), k, rig_rng(seed, draw, cell, rig))
            items.append((np.mean([rr[j][f"{label}_ans"] for j in some], 0), lab, rr[0]["cluster"], rig))
        if len(items) >= 2:
            out.append((use, items, amp))
    return out


def read_k(rows, label, k, draws=BKS_DRAWS, seed=SEED):
    """r by group for a k-section read, over seeded draws of the sections. -> {group: r}."""
    from learn import reads_v3 as R

    if k == ALL:
        return {g: v[0] for g, v in R.corr(section_blocks(rows, label, ALL)).items()}
    got = collections.defaultdict(list)
    for d in range(draws):
        for g, v in R.corr(section_blocks(rows, label, k, seed, d)).items():
            got[g].append(v[0])
    return {g: float(np.mean(v)) for g, v in got.items()}


def jackknife(rows, label, k=1, draws=BKS_DRAWS):
    """All sections less k sections by group, with `reads_v3.bks_pair`'s delete-one-block interval, t(3), over (fold, class)."""
    from learn import reads_v3 as R

    recs = collections.defaultdict(set)
    for r in rows:
        recs[(r["fold"], r["cls"])].add(r["rec"])
    keys = sorted(q for q, v in recs.items() if len(v) >= 2)
    if len(keys) != 4:
        raise SystemExit(f"{len(keys)} usable BKS blocks, not 4")

    def diff(S):
        a, b = read_k(S, label, ALL), read_k(S, label, k, draws)
        return {g: a[g] - b[g] for g in a if g in b}

    whole, out = diff(rows), {}
    jk = [diff([r for r in rows if (r["fold"], r["cls"]) != q]) for q in keys]
    per = [diff([r for r in rows if (r["fold"], r["cls"]) == q]) for q in keys]
    for g in R.GROUPS:
        if any(g not in d for d in per):
            raise SystemExit(f"{g} is not in all 4 BKS blocks: the jackknife does not apply")
        v = np.array([d[g] for d in jk], float)
        h = 2.353 * math.sqrt(3 / 4 * ((v - v.mean()) ** 2).sum())
        out[g] = {"diff": whole[g], "lo90": whole[g] - h, "hi90": whole[g] + h, "blocks_positive": sum(d[g] > 0 for d in per)}
    return out


def cmd_bks(_a):
    from learn import pipeline_fix as P

    S = [r for r in stored_rows() if r["set"] == "BKS"]
    sizes = collections.Counter()
    for r in S:
        sizes[(r["fold"], r["amp"], r["cls"], r["rec"])] += 1
    res = {"rigs": len(sizes), "sections_per_rig": sorted(sizes.values()), "readers": {}}
    song = lambda r: r["cluster"].split("/")[1]           # noqa: E731
    for label in BKS_READERS:
        res["readers"][label] = {"r": {str(k): read_k(S, label, k) for k in (*BKS_K, ALL)}, "all_less_one": jackknife(S, label),
                                 "by_song": {s: {str(k): read_k([r for r in S if song(r) == s], label, k) for k in (1, ALL)} for s in sorted({song(r) for r in S})}}
    out = P.out_dir() / EAT / "s11-bks.json"
    out.write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({m: v["all_less_one"] for m, v in res["readers"].items()}, indent=1, default=float))


# --- GOAT's other windows ---------------------------------------------------------------------------------------------

def windows_root():
    from learn import pipeline_fix as P

    return P.out_dir() / EAT / "windows"


def window_path(unit, w):
    return windows_root() / f"{unit.replace('/', '__')}-w{w:02d}.npz"


def eligible(rows, track, min_start_s=1.0):
    """`pipeline_fix.goat_window`'s rule: the DI's grid sections it could draw from, before its choice."""
    from learn import clean_di as CD

    return sorted(r["start_s"] for r in rows if r["passes_activity"] and r["start_s"] >= min_start_s
                  and not (r.get("clip_runs") or r.get("dropouts") or r.get("hard_cuts")) and not CD.section_flags(r, track or {})[0])


def far_enough(start, taken, length):
    """No overlap with any window already held."""
    return all(abs(start - t) >= length for t in taken)


def backing_entries(pool, entry_id, session):
    """The pool entries of a unit's own backing's session, its own first left out, in a seeded order; reused when the session runs short."""
    same = sorted(j for j, e in enumerate(pool) if e["session"] == session and e["id"] != entry_id)
    random.Random(f"{SEED}|{entry_id}").shuffle(same)
    return same


def windows_of(unit, stored_start, rng_key, ok, length):
    """A unit's candidate starts in a seeded order: never its labelled window, none overlapping it."""
    order = [s for s in ok if far_enough(s, [stored_start], length)]
    random.Random(f"{SEED}|{rng_key}").shuffle(order)
    return order


def amp_section(a, sr, start):
    """A window of a take's render as `cmd_goat_sections` wrote it and `real_amp_track` reads it: resampled, trimmed, at the centred
    mono fold, on which each unit's stored guitar gain was set. -> (the slice before the fold and trim, the window)."""
    from learn import clean_di as CD
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    lo, hi = window_range(start, sr)
    raw = CD.resample(a[lo:hi], sr, PS.SR)[:int(round((PS.SEC_S + PS.TRIM_S) * PS.SR))]
    return raw, raw[int(PS.TRIM_S * PS.SR):] * T.pan_fold(0.0)


def window_range(start, sr):
    from learn import pretrain_set as PS

    return max(0, int(round((start - PS.TRIM_S) * sr))), int(round((start + PS.SEC_S) * sr))


def mix_of(window, gain_db, back, gb, ga, lend):
    """`cmd_build_dfix_real`'s input for one window at the unit's own fixed levels."""
    from learn import direct_stems as DS
    from learn import pipeline_fix as P
    from learn import song_aug as SA

    gtr = np.asarray(window, np.float64) * 10 ** (gain_db / 20)
    mix = P.dfix_mix(gtr, back, gb, ga)
    mastered, mrng = DS.master_draw(int(lend))
    return SA.compress(mix, mrng) if mastered else mix


def backing_of(ent, voc, stems):
    from learn import pipeline_fix as P

    tracks = ent["tracks"]["v" if voc else "n"]
    return np.asarray(stems.get(ent["id"], tracks) if ent["kind"] == "training" else P.bare_backing(ent["sd"], tracks, ent["start_s"]), np.float64), ent["lufs"][str(bool(voc))]


def units_read():
    """The GOAT units the read holds, by item. -> ({item: [unit]}, data)."""
    from learn import pipeline_fix as P

    _, data = B.base_rows()
    units = {}
    for k in range(ER.FOLDS):
        units.update({h["real"]: data[4][h["real"]] for h in P.dfix_rows_of(*data, k)[1] if h["real"].startswith("goat/")})
    by = collections.defaultdict(list)
    for u in sorted(units):
        by[units[u]["item"]].append(units[u])
    return by, data


def source():
    from learn import cc_build as CB
    from learn import pipeline_fix as P
    from learn import trusted_data as T

    pool = json.loads(P.wide_pool_path().read_text())["entries"]
    return pool, T.Stems(CB.ctx_for(argparse.Namespace(out=None, smoke=False)))


def cmd_windows(a):
    import soundfile as sf

    from analysis.aligned import estimate_lag
    from learn import clean_di as CD
    from learn import direct_stems as DS
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    sys.path.insert(0, str(PS.HOME / "references/datasets-set3/_tools"))
    import classify as C
    import gainmeasure as GM

    k, n = (int(q) for q in a.shard.split("/"))
    by, _ = units_read()
    pool, stems = source()
    ids = {e["id"]: j for j, e in enumerate(pool)}
    windows_root().mkdir(parents=True, exist_ok=True)
    length = PS.SEC_S
    samples, trim = int(round((PS.SEC_S + PS.TRIM_S) * PS.SR)), int(PS.TRIM_S * PS.SR)
    log, t0 = {}, time.time()
    with zipfile.ZipFile(P.GOAT_ZIP) as z:
        meta = {m["item"]: m for m in P.goat_items_from(z)}
        for q, item in enumerate(sorted(by)):
            if q % n != k:
                continue
            if PS.free_gb() < 33:
                raise SystemExit("free disk below 33 GB")
            m = meta[item]
            x, sr = sf.read(io.BytesIO(z.read(P.goat_member(item, m["di_audio_path"]))), dtype="float64", always_2d=True)
            x = x.mean(1)
            f, fs = CD.floor_spectrum(CD.resample(x, sr, CD.SR))
            votes = {v: [CD.line_count(f, fs, v)] for v in CD.MAINS} if fs is not None else {}
            track, rows = CD.measure_di(x, sr, CD.session_mains(votes))
            ok = eligible(rows, track)
            for u in by[item]:
                unit = u["unit"]
                z0 = np.load(P.dfix_input_path(unit, 0))
                bid, voc = str(z0["backing"]), bool(z0["vocals"])
                ent0 = pool[ids[bid]]
                back_order = backing_entries(pool, bid, ent0["session"])
                gb0, ga = (float(v) for v in z0["gains"])
                a_, sra = sf.read(io.BytesIO(z.read(P.goat_member(item, m[f"amp_audio_path_{u['render']}"]))), dtype="float64", always_2d=True)
                a_ = a_.mean(1)
                peak = float(np.max(np.abs(a_)))
                held, refused = [], collections.Counter()
                for start in windows_of(unit, u["window_s"], unit, ok, length):
                    if len(held) == MORE:
                        break
                    if not far_enough(start, [h[0] for h in held], length):
                        continue
                    lo, hi = window_range(start, sr)
                    if len(CD.clip_runs(a_[lo:hi], peak=peak)):
                        refused["clips"] += 1
                        continue
                    dsec = CD.resample(x[lo:hi], sr, PS.SR)[:samples]
                    asec, sec = amp_section(a_, sr, start)
                    if len(asec) < samples or len(dsec) < samples:
                        refused["past the end"] += 1
                        continue
                    gm = GM.measures(np.asarray(asec[trim:], np.float64), np.asarray(dsec[trim:], np.float64), PS.SR)
                    cls = C.classify(gm)[0] if gm else None
                    if cls not in ("clean", "crunch"):
                        refused["class"] += 1
                        continue
                    try:
                        lag = int(estimate_lag(asec, [dsec]))
                    except ValueError:
                        refused["no lag"] += 1
                        continue
                    if abs(lag - u["item_lag"]) > P.GOAT_LAG_TOL:
                        refused["lag"] += 1
                        continue
                    held.append((float(start), sec, cls, lag))
                done = []
                for w, (start, sec, cls, lag) in enumerate(held):
                    path = window_path(unit, w)
                    j = back_order[w % len(back_order)] if back_order else ids[bid]
                    back, lv = backing_of(pool[j], voc, stems)
                    gb = P.dfix_backing_gain(gb0, ent0["lufs"][str(voc)], lv)
                    feats, lu, _ = DS.half_features(mix_of(sec, float(z0["guitar_gain_db"]), back, gb, ga, z0["lend"]))
                    DS._save_npz(path, sA=feats["A"], sB=feats["B"], lufs=[lu["A"], lu["B"]], start_s=start, backing=pool[j]["id"], cls=cls, lag=lag, gains=[gb, ga])
                    done.append({"start_s": start, "backing": pool[j]["id"], "cls": cls, "lag": lag})
                log[unit] = {"windows": done, "refused": dict(refused), "sessions_entries": len(back_order)}
            print(f"{q}: {item}: {[len(log[u['unit']]['windows']) for u in by[item]]}; {time.time() - t0:.0f} s", flush=True)
    (windows_root() / f"log-{k}-of-{n}.json").write_text(json.dumps(log, indent=1))
    print(f"WINDOWS DONE {a.shard}: {sum(len(v['windows']) for v in log.values())} windows, {len(log)} units", flush=True)


def cmd_check(_a):
    """`amp_section` and the chain on 12 sampled units' labelled windows, from the zip as `cmd_windows` reads them, must give each unit's
    stored variant 0 within 1 grid step."""
    import soundfile as sf

    from learn import direct_stems as DS
    from learn import pipeline_fix as P

    by, _ = units_read()
    pool, stems = source()
    ids = {e["id"]: j for j, e in enumerate(pool)}
    units = [u for item in sorted(by) for u in by[item]]
    random.Random(SEED).shuffle(units)
    worst = 0
    with zipfile.ZipFile(P.GOAT_ZIP) as z:
        meta = {m["item"]: m for m in P.goat_items_from(z)}
        for u in units[:12]:
            z0 = np.load(P.dfix_input_path(u["unit"], 0))
            a_, sra = sf.read(io.BytesIO(z.read(P.goat_member(u["item"], meta[u["item"]][f"amp_audio_path_{u['render']}"]))), dtype="float64", always_2d=True)
            _, sec = amp_section(a_.mean(1), sra, u["window_s"])
            back, _ = backing_of(pool[ids[str(z0["backing"])]], bool(z0["vocals"]), stems)
            gb, ga = (float(v) for v in z0["gains"])
            f, _, _ = DS.half_features(mix_of(sec, float(z0["guitar_gain_db"]), back, gb, ga, z0["lend"]))
            worst = max(worst, *(int(np.abs(f[h].astype(int) - z0[n].astype(int)).max()) for h, n in (("A", "sA"), ("B", "sB"))))
    print(f"CHECK: worst {worst} grid steps over 12 units", flush=True)
    if worst > 1:
        raise SystemExit("the chain differs from the stored inputs")


# --- the read ---------------------------------------------------------------------------------------------------------

def rotated(by_cell):
    """The placebo's map: each unit reads the next item's windows in its own fold, amp and class, so a window of another take stands in
    for its own under the same fit and centre."""
    out = {}
    for cell, units in by_cell.items():
        items = sorted({u.split("@")[0] for u in units})
        if len(items) < 2:
            raise SystemExit(f"{cell}: one item, no other take to borrow")
        for u in units:
            other = items[(items.index(u.split("@")[0]) + 1) % len(items)]
            out[u] = next(v for v in units if v.split("@")[0] == other)
    return out


def cmd_read(_a):
    from learn import pipeline_fix as P
    from learn import reads_v3 as R
    from learn import trusted_data_t3 as T3

    B.sha_ok()
    ER.with_pcs(64)
    _, data = B.base_rows()
    rows = stored_rows()
    enc = T3.encode_for(T3.FULL)
    out_rows = []
    for k in range(ER.FOLDS):
        fold = [r for r in rows if r["fold"] == k]
        _, held, _ = P.dfix_rows_of(*data, k)
        rows_tr, clusters, files = B.training_set("real", k, data)
        Y_tr = [np.stack(z) for z in zip(*(enc(h["label"]) for h in rows_tr))]
        te_rows, te_files, where = [], [], []
        goat = [(r, h) for r, h in zip(fold, held) if r["set"] == "GOAT"]
        for j, (r, h) in enumerate(goat):
            unit = h["real"]
            r["unit"] = unit
            te_rows.append(h)
            te_files.append(str(P.dfix_input_path(unit, 0)))
            where.append((j, -1))
            for w in range(MORE):
                p = window_path(unit, w)
                if p.exists():
                    te_rows.append(h)
                    te_files.append(str(p))
                    where.append((j, w))
        mu, _ = B.candidate_answers(("mel", "ridge", "real"), rows_tr, clusters, files, te_rows, te_files, Y_tr, R.searched, (None,))
        for r, _h in goat:
            r["win"] = {}
        for (j, w), v in zip(where, mu):
            goat[j][0]["win"][w] = v
        out_rows += [r for r, _ in goat]
        print("fold", k, "read", len(te_files), flush=True)
    worst = max(float(np.abs(r["win"][-1] - r["M-pcs_ans"]).max()) for r in out_rows)
    print(f"CONTROL: labelled window against the stored `M-pcs`, worst {worst:.2e}", flush=True)
    if worst > 1e-5:
        raise SystemExit("the fit differs from the stored reader")
    by_cell = collections.defaultdict(list)
    for r in out_rows:
        by_cell[(r["fold"], r["amp"], r["cls"])].append(r["unit"])
    rot, of = rotated(by_cell), {r["unit"]: r for r in out_rows}
    for r in out_rows:
        others = [v for w, v in sorted(r["win"].items()) if w >= 0]
        r["L_ans"] = r["win"][-1]
        r["ALL_ans"] = np.mean([r["win"][-1], *others], 0)
        r["OTHERS_ans"] = np.mean(others, 0) if others else r["win"][-1]
        r["O1_ans"] = others[0] if others else r["win"][-1]
        placebo = [v for w, v in sorted(of[rot[r["unit"]]]["win"].items()) if w >= 0]
        r["PLACEBO_ans"] = np.mean([r["win"][-1], *placebo], 0)
        for n_ in (1, 2, 3):
            r[f"N{n_}_ans"] = np.mean([r["win"][-1], *others[:n_]], 0)
    labels = ("L", "ALL", "OTHERS", "O1", "PLACEBO", "N1", "N2", "N3")
    pairs = [("ALL", "L"), ("OTHERS", "L"), ("PLACEBO", "L")]
    res = {"units": len(out_rows), "windows": collections.Counter(len(r["win"]) - 1 for r in out_rows), "r": {m: {g: v[0] for g, v in R.corr(R.blocks(out_rows, m)).items()} for m in labels}}
    iv = R.goat_intervals(out_rows, list(labels), pairs)
    res["pairs"] = {f"{a}-{b}": {g: iv[(f"{a}-{b}", g)] for g in R.GROUPS} for a, b in pairs}
    two = [r for r in out_rows if len(r["win"]) - 1 >= 2]              # no searched window on either side of this primary
    iv2 = R.goat_intervals(two, ["OTHERS", "O1"], [("OTHERS", "O1")])
    res["unsearched"] = {"units": len(two), "OTHERS-O1": {g: iv2[("OTHERS-O1", g)] for g in R.GROUPS},
                         "r": {m: {g: v[0] for g, v in R.corr(R.blocks(two, m)).items()} for m in ("OTHERS", "O1")}}
    res["harness_fault"] = [g for g in R.GROUPS if res["pairs"]["PLACEBO-L"][g]["lo90"] > 0]
    res["player"] = B.player_read(out_rows, list(labels), data[4])
    full = [r for r in out_rows if len(r["win"]) - 1 >= 3]
    res["three_or_more"] = {"units": len(full), "r": {m: {g: v[0] for g, v in R.corr(R.blocks(full, m)).items()} for m in ("L", "ALL", "OTHERS", "O1", "PLACEBO")}}
    (P.out_dir() / EAT / "s11-goat.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k_: res[k_] for k_ in ("units", "windows", "r", "unsearched", "pairs", "harness_fault")}, indent=1, default=float))


# --- the score step ---------------------------------------------------------------------------------------------------

SCORE_TAGS = ("M-win", "M-far")
MIN_OTHERS = 2


def blended(x, others, keep_search):
    """A unit's (2, d) mel input with its other windows' both halves at equal weight per half. `keep_search`: each direction keeps its own
    search half of the labelled window. It never takes the labelled window's other half, the held half that direction is judged on."""
    more = np.concatenate(others, 0)
    if not keep_search:
        return np.broadcast_to(more.mean(0), x.shape).copy()
    return np.stack([np.concatenate([x[h:h + 1], more], 0).mean(0) for h in range(2)])


def score_units():
    """{str(variant 0 file): the unit's other windows' files}, for units with `MIN_OTHERS` or more."""
    from learn import pipeline_fix as P

    out = {}
    for u in sorted(p for q in units_read()[0].values() for p in (v["unit"] for v in q)):
        files = [str(window_path(u, w)) for w in range(MORE) if window_path(u, w).exists()]
        if len(files) >= MIN_OTHERS:
            out[str(P.dfix_input_path(u, 0))] = files
    return out


def cmd_predict(a):
    """`bakeoff_render.cmd_predict` for `M-pcs` unchanged, with a fold's fit left alone and only the held read's input blended. Units with too
    few windows run through unblended, so their answers must equal stored `M-pcs`'s: the control. Only the blended units are kept."""
    from learn import bakeoff_render as BR
    from learn import eat_render as ERN
    from learn import pipeline_fix as P

    if a.tag not in SCORE_TAGS:
        raise SystemExit(f"--tag {SCORE_TAGS}")
    a.mid, a.pcs, a.net = "pub", 64, "mn10_as"
    ER.real_setup(a)
    B.CANDIDATES = {**B.CANDIDATES, a.tag: ER.SAME_COUNT["M-pcs"]}
    BR.root = ERN.score_root
    units = score_units()
    state, feature, fit = {"fitting": False}, B.feature, BR.fit_fold

    def fit_fold(*q, **kw):
        state["fitting"] = True
        try:
            return fit(*q, **kw)
        finally:
            state["fitting"] = False

    def read(name, seed, f, amp, cls):
        x = feature(name, seed, f, amp, cls)
        if state["fitting"] or f not in units:
            return x
        return blended(x, [B.summary_of("mel", w) for w in units[f]], a.tag == "M-win")

    B.feature, BR.fit_fold = read, fit_fold
    BR.cmd_predict(a)
    stored = BR.stored_answers("goat", "M-pcs")
    path = BR.answers_path("goat", a.tag)
    got = json.loads(path.read_text())
    held = {f for f in units}
    mine, same = {}, 0
    for key, ans in got["answers"].items():
        if str(P.dfix_input_path(key.split("|")[0], 0)) in held:
            mine[key] = {BR.ANY: ans["A"]} if a.tag == "M-far" else ans
        elif ans != stored[key]:
            raise SystemExit(f"control: {key} differs from stored `M-pcs` though no window was blended")
        else:
            same += 1
    got["answers"] = mine
    path.write_text(json.dumps(got))
    bks = BR.answers_path("bks", a.tag)
    b = json.loads(bks.read_text())
    b["answers"] = {}
    bks.write_text(json.dumps(b))
    print(f"CONTROL OK: {same} unblended keys equal stored `M-pcs`; {a.tag}: {len(mine)} keys", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bks").set_defaults(fn=cmd_bks)
    w = sub.add_parser("windows")
    w.add_argument("--shard", default="0/1")
    w.set_defaults(fn=cmd_windows)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    sub.add_parser("read").set_defaults(fn=cmd_read)
    p = sub.add_parser("predict")
    p.add_argument("--tag", required=True)
    p.set_defaults(fn=cmd_predict)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
