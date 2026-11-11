"""A1, choosing the amp by a stock-DI comparison (`docs/full-controls-plan.md`, "A1 in detail"; ledger `pipeline-fix`
`phase_a1`). The product has no DI, so it can't render its answer per amp against the song. Instead each amp's answer is
rendered through a stock DI (a library DI section of the unit's class), and the amp whose render's spectral shape sits
closest to the song's separated guitar (the model's own input) is picked. Read at the end against always-sw50r on the
model's own per-amp renders (C3-cabS's, C3b stage 2).

    .venv/bin/python -m learn.amp_di_compare a1-draw                    # the units and stock DIs (zero renders)
    .venv/bin/python -m learn.amp_di_compare a1-render --shard 0/3      # each amp's answer through each stock DI (renders)
    .venv/bin/python -m learn.amp_di_compare a1-rows                    # the picks and the read (zero renders)

The pure parts (the stock-DI draw, the shape and distance, the pick and the rows) are unit-tested; the render is not.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time

PHASE = "phase_a1"
SEED = 20261128                      # the stock-DI draw's
PER_CLASS = 2                        # stock DIs per class, on distinct DI files
AMPS = ("pr12", "sw50r", "ac20")
MODEL = "C3-cabS"                    # the model whose per-amp renders read the pick (C3b stage 2's)
FLOOR_U8 = 44                        # -90 dB on the inputs' quantised grid: the common floor (the review, before the read)


def a1_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "a1"


# --- pure parts ---------------------------------------------------------------------------------------------------------

def draw_stock(candidates, per_class=PER_CLASS, seed=SEED):
    """`per_class` stock DIs per class on distinct DI files, seeded. candidates: [{di, cls, di_path, start_s, unit}].
    -> {cls: [candidate]}."""
    rng = random.Random(seed)
    out = {}
    for cls in sorted({c["cls"] for c in candidates}):
        by_file = {}
        for c in sorted(candidates, key=lambda c: c["unit"]):
            if c["cls"] == cls:
                by_file.setdefault(c["di"], c)
        files = sorted(by_file)
        if len(files) < per_class:
            raise SystemExit(f"{cls}: {len(files)} DI files for {per_class} stock DIs")
        out[cls] = [by_file[f] for f in rng.sample(files, per_class)]
    return out


def shape(mel_u8):
    """A log-mel's spectral shape: each band's mean over time, less the mean over bands (level removed). mel_u8: [bands,
    frames] (or nested lists). -> [float per band]."""
    rows = [list(map(float, r)) for r in mel_u8]
    means = [sum(r) / len(r) for r in rows]
    m = sum(means) / len(means)
    return [x - m for x in means]


def band_mask(lo_hz=60.0, hi_hz=8000.0):
    """The mel bands whose centres sit in [lo_hz, hi_hz] (`song_aug`'s grid): the review's beside band. -> [bool]."""
    import numpy as np

    from learn import song_aug as SA

    def hz_to_mel(f):                                   # song_aug.mel_matrix's own scale
        return 2595 * np.log10(1 + f / 700)

    def mel_to_hz(m):
        return 700 * (10 ** (m / 2595) - 1)

    edges = mel_to_hz(np.linspace(hz_to_mel(SA.FMIN), hz_to_mel(SA.FMAX), SA.MELS + 2))
    return [bool(lo_hz <= c <= hi_hz) for c in edges[1:-1]]


def shape_in(mel_u8, mask):
    """`shape` on the bands `mask` keeps."""
    return shape([r for r, keep in zip(mel_u8, mask) if keep])


def distance(a, b):
    """The L2 distance of two shapes."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def band_pick(band, rec, sh, mask, amps=AMPS):
    """The pick on the 60 Hz-8 kHz bands, from the stored mels (the stored shapes are full-band): each amp's stock-DI
    renders' model-input mel on both halves, band-limited. -> amp."""
    import numpy as np

    z = np.load(a1_dir() / "mels" / f"{rec['set']}__{rec['unit'].replace('/', '__')}.npz")
    n = len(rec["shapes"][sh][amps[0]])
    renders = {a: [shape_in(np.concatenate([z[f"{sh}_{a}_{j}_A"], z[f"{sh}_{a}_{j}_B"]], axis=1).tolist(), mask)
                   for j in range(n)] for a in amps}
    return pick(band, renders, amps)


def pick(target, renders, amps=AMPS):
    """The amp whose stock-DI renders' shapes sit closest to `target` on average over the stock DIs. renders: {amp:
    [shape per stock DI]}. Ties go to the first amp in `amps`' order. -> amp."""
    d = {a: sum(distance(target, s) for s in renders[a]) / len(renders[a]) for a in amps}
    return min(amps, key=lambda a: d[a])


ROWS_BY_CLASS = ("DI-compare - always sw50r", "DI-compare - W")


def unit_rows(unit, cluster, cls, judge, picks, w, amps=AMPS):
    """One unit's rows on the model's own per-amp renders (judge: {amp: {search half: {half: value}}}), per direction
    (search half sh, held half h), on the held half: each pick (picks: {name: {sh: amp}}) and W's (w: {sh: amp}) against
    always-sw50r and W, and the search half's own argmin (the ceiling) against always-sw50r; the primary also by class.
    -> ({row: [(cluster, unit, value)]}, directions dropped)."""
    from learn import full_controls_c3 as X

    rows, dropped = {}, 0

    def add(name, v):
        rows.setdefault(name, []).append((cluster, unit, v))
        if name in ROWS_BY_CLASS:
            rows.setdefault(f"{name} ({cls})", []).append((cluster, unit, v))

    for sh, h in (("A", "B"), ("B", "A")):
        hv = {a: ((judge.get(a) or {}).get(sh) or {}).get(h) for a in amps}
        sv = {a: ((judge.get(a) or {}).get(sh) or {}).get(sh) for a in amps}
        if w.get(sh) is None or any(p.get(sh) is None for p in picks.values()) or not all(
                X.finite_pos(v) for v in (*hv.values(), *sv.values())):
            dropped += 1
            continue
        lv = {a: math.log(float(v)) for a, v in hv.items()}
        for name, p in picks.items():
            label = ("DI-compare" if name == "embedding" else "DI-compare by shape" if name == "stem"
                     else f"DI-compare by {name}" if name.startswith("embedding") else f"DI-compare by shape on the {name}")
            add(f"{label} - always sw50r", lv[p[sh]] - lv["sw50r"])
            add(f"{label} - W", lv[p[sh]] - lv[w[sh]])
        add("W - always sw50r", lv[w[sh]] - lv["sw50r"])
        add("search-half argmin - always sw50r", lv[min(sorted(amps), key=lambda a: sv[a])] - lv["sw50r"])
    return rows, dropped


def reading(primary):
    """The declared reading of "DI-compare - always sw50r" by C3's test: "learns" (better somewhere, worse nowhere), else
    its direction."""
    from learn import full_controls_c3 as X

    d = X.direction(primary)
    return "learns" if d == "better" else d


def cosine_distance(a, b):
    """1 less the cosine of two feature vectors."""
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return 1.0 - sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 1.0


def embed_pick(target, renders, amps=AMPS):
    """The amendment's pick: the amp whose renders' embeddings sit closest (cosine, averaged over the stock DIs) to the
    target's. renders: {amp: [feature vector per stock DI]}. Ties to the first amp. -> amp."""
    d = {a: sum(cosine_distance(target, r) for r in renders[a]) / len(renders[a]) for a in amps}
    return min(amps, key=lambda a: d[a])


# --- the commands -------------------------------------------------------------------------------------------------------

def read_units():
    """GOAT's read units and BKS's 40, each with its class, its cluster, and the model's answers per amp and half."""
    from learn import pipeline_fix as P

    root = P.out_dir()
    out = []
    ga = json.loads((root / P.GOAT_DIR / P.AMPS3_DIR / f"{MODEL}.json").read_text())
    for prt in P.goat_read_units():
        out.append({"set": "goat", "unit": prt["unit"], "cls": prt["cls"], "cluster": prt["item"],
                    "answers": {a: ga["answers"][f"{prt['unit']}|{a}"] for a in AMPS}})
    ba = json.loads((root / P.REAL_DIR / "answers" / f"{MODEL}.json").read_text())
    for prt in ba["parts"]:
        out.append({"set": "bks", "unit": prt["unit"], "cls": prt["cls"], "cluster": prt["di"],
                    "answers": {a: ba["answers"][f"{prt['unit']}|{a}"] for a in AMPS}})
    return out


def target_lufs():
    """The model's own input loudness (C3's fold models'), the gain the clean inputs and the stock-DI renders are read at."""
    from learn import pipeline_fix as P

    rec = json.loads((P.out_dir() / "runs" / f"C3-ftm-k0-{P.SEEDS[0]}.json").read_text())
    return P.model_input_lufs(rec)


def cmd_draw(_args):
    """The stock DIs, 2 per class from C3r's n12 units (the library DIs the DI check kept), and the units -> a1/plan.json,
    written once."""
    from learn import full_controls_c3r as R3
    from learn import pipeline_fix as P

    P.require(PHASE)
    p = a1_dir() / "plan.json"
    if p.exists():
        raise SystemExit(f"{p} exists: drawn once")
    cands = [{"unit": ru["unit"], "di": ru["prt"]["di"], "cls": ru["prt"]["cls"], "di_path": ru["prt"]["di_path"],
              "start_s": ru["prt"]["start_s"]} for ru in R3.read_units(R3.state()) if ru["set"] == "n12"]
    units = [{k: v for k, v in u.items() if k != "answers"} for u in read_units()]
    own = {u["cluster"] for u in units}                # a read unit's own DI file never serves as a stock DI
    stock = draw_stock([c for c in cands if c["di"] not in own])
    P.save(p, {"phase": PHASE, "stock": stock, "units": units, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"A1 DRAW: {len(units)} units; stock DIs {json.dumps({c: [s['di'] for s in v] for c, v in stock.items()})}")


def render_units(units, out_dir, shard, stock=None, target=None):
    """Each unit's answer per amp and search half, through each stock DI of its class, fresh (own process, one priming
    render), trimmed; its log-mel shape -> <out_dir>/shapes/<unit>.json, and (the review) its model-input mel per half at
    the model's input gain (`step4_half`, uint8 and LUFS) -> <out_dir>/mels/<unit>.npz. units: [{set, unit, cls,
    answers: {amp: {half: answer}}}]; stock: A1's stock DIs by class (default A1's plan's)."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_aug as SA
    from learn import song_bank as B
    from learn import trusted_data as T

    stock = stock or json.loads((a1_dir() / "plan.json").read_text())["stock"]
    target = target_lufs() if target is None else target
    k, n = shard
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    dis = {cls: [B.measure(PS.section_audio(s["di_path"], s["start_s"])).astype(np.float32) for s in ss]
           for cls, ss in stock.items()}
    LO._wait_cap()
    renders = 0
    d, dm = out_dir / "shapes", out_dir / "mels"
    d.mkdir(parents=True, exist_ok=True)
    dm.mkdir(parents=True, exist_ok=True)
    for u in units[k::n]:
        out = d / f"{u['set']}__{u['unit'].replace('/', '__')}.json"
        if out.exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        rec = {"set": u["set"], "unit": u["unit"], "cls": u["cls"], "target_lufs": target, "shapes": {}}
        mels = {}
        for sh in ("A", "B"):
            for a in AMPS:
                x = u["answers"][a][sh]
                st = LO.tdict(x["settings"])
                got = []
                for j, di32 in enumerate(dis[u["cls"]]):
                    y = np.asarray(AM.fresh_render(CB.new_renderer, di32, x["select"], st, st), np.float64)[trim[0]:trim[1]]
                    renders += 2
                    got.append(shape(PS.quant(SA.logmel(DE.mono(y))).tolist()))
                    g = DE.inference_gain_db(y, target)
                    for h in ("A", "B"):
                        s8, _, ls, _ = DS.step4_half(y, y, h, g)
                        mels[f"{sh}_{a}_{j}_{h}"] = s8
                        mels[f"{sh}_{a}_{j}_{h}_lufs"] = np.array([ls], np.float32)
                rec["shapes"].setdefault(sh, {})[a] = got
        np.savez_compressed(dm / f"{u['set']}__{u['unit'].replace('/', '__')}.npz", **mels)
        P.save(out, rec)                                # the resume marker, after its mels
        print(f"{u['set']} {u['cls']}: renders so far {renders}", flush=True)
    print(f"RENDER DONE {k}/{n}: {renders} renders", flush=True)


def cmd_render(args):
    """A1's renders (`render_units` on A1's plan) -> a1/shapes, a1/mels."""
    from learn import pipeline_fix as P

    P.require(PHASE)
    plan = json.loads((a1_dir() / "plan.json").read_text())
    ans = {(u["set"], u["unit"]): u["answers"] for u in read_units()}
    render_units([{**u, "answers": ans[(u["set"], u["unit"])]} for u in plan["units"]], a1_dir(), args.shard,
                 plan["stock"])


def fold_model(name, unit, goat_fold, unit_model):
    """The C3 fold model that held the unit out: GOAT by its item fold, BKS by C3-cabS's own unit-to-model record."""
    return f"C3-ftm-k{goat_fold}" if name == "goat" else unit_model[unit]


def embed_units(units, out_dir, target=None):
    """The amendment's features (zero renders, CPU, torch): per unit and search half, the pooled body features of the
    fold model `u["model"]` that held the unit out (both seeds averaged), for the separated stem's input on that half
    (D_fix variant 0), the clean amp track's at the model's input gain, and each stock-DI render's stored mel on the same
    half, each floored at -90 dB (and unfloored beside); the cosine distances and picks -> <out_dir>/embed/<unit>.json.
    units: [{set, unit, cls, prt (sd, track, start_s), model}]."""
    import numpy as np
    import torch

    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import pipeline_fix as P

    target = target_lufs() if target is None else target
    nets = {}

    def feats(name, x):
        with torch.no_grad():
            X = torch.tensor(np.asarray([x], np.float32))
            hs = []
            for net in nets[name]:
                h = net.body(X)
                hs.append(torch.cat([h.mean(-1), h.std(-1)], dim=1).flatten(1)[0].numpy())
        return np.mean(hs, 0).tolist()

    d = out_dir / "embed"
    d.mkdir(parents=True, exist_ok=True)
    for u in units:
        out = d / f"{u['set']}__{u['unit'].replace('/', '__')}.json"
        if out.exists():
            continue
        prt, name = u["prt"], u["model"]
        if name not in nets:
            nets[name] = [P.load_run(name, sd, "best")[0].eval() for sd in P.SEEDS]
        backed = P.dfix_backed(u["unit"])
        ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        g = DE.inference_gain_db(ref, target)
        z = np.load(out_dir / "mels" / f"{u['set']}__{u['unit'].replace('/', '__')}.npz")
        rec = {"set": u["set"], "unit": u["unit"], "model": name, "floor_u8": FLOOR_U8, "picks": {}, "dist": {}}

        def emb(m8, lu, sh, floor):
            m8 = np.maximum(m8, FLOOR_U8) if floor else m8
            return feats(name, DS.model_input(m8, m8, lu, lu, sh, "sw50r", u["cls"], "Dstem")[0])

        for sh in ("A", "B"):
            s8, ls = backed[sh]
            c8, _, lc, _ = DS.step4_half(ref, ref, sh, g)
            n = sum(1 for k in z.files if k.startswith(f"{sh}_{AMPS[0]}_") and k.endswith(f"_{sh}"))
            for floor, kinds in ((True, {"stem": (s8, ls), "clean amp track": (c8, lc)}), (False, {"stem, no floor": (s8, ls)})):
                renders = {a: [emb(z[f"{sh}_{a}_{j}_{sh}"], float(z[f"{sh}_{a}_{j}_{sh}_lufs"][0]), sh, floor)
                               for j in range(n)] for a in AMPS}
                for kind, (m8, lu) in kinds.items():
                    t = emb(m8, lu, sh, floor)
                    rec["picks"].setdefault(kind, {})[sh] = embed_pick(t, renders)
                    rec["dist"].setdefault(kind, {})[sh] = {a: sum(cosine_distance(t, r) for r in renders[a]) / n
                                                            for a in AMPS}
        P.save(out, rec)
    print(f"EMBED DONE: {len(units)} units")


def cmd_embed(_args):
    """A1's features (`embed_units` on A1's plan, by the C3 fold model that held each unit out) -> a1/embed."""
    from learn import pipeline_fix as P

    P.require(PHASE)
    plan = json.loads((a1_dir() / "plan.json").read_text())
    root = P.out_dir()
    bks = json.loads((root / P.REAL_DIR / "answers" / f"{MODEL}.json").read_text())
    gparts = {p_["unit"]: p_ for p_ in P.goat_read_units()}
    bparts = {p_["unit"]: p_ for p_ in bks["parts"]}
    units = []
    for u in plan["units"]:
        prt = gparts[u["unit"]] if u["set"] == "goat" else bparts[u["unit"]]
        units.append({**u, "prt": prt, "model": fold_model(u["set"], u["unit"], prt.get("fold"), bks["unit_model"])})
    embed_units(units, a1_dir())


def cmd_rows(_args):
    """The picks and the read -> a1/a1.json: per direction, the separated stem's shape (the model's own input, D_fix
    variant 0) against each amp's stock-DI shapes; beside, the clean amp track's (which the product never has)."""
    from learn import direct_stems as DS
    from learn import full_controls_c3 as X
    from learn import full_space as FS
    from learn import pipeline_fix as P

    P.require(PHASE)
    plan = json.loads((a1_dir() / "plan.json").read_text())
    from learn import direct_existing as DE

    root = P.out_dir()
    target, mask = target_lufs(), band_mask()
    sets, counts = {}, {}
    for name, d, sa, sj in (("bks", P.REAL_DIR, "answers", "judge"), ("goat", P.GOAT_DIR, P.AMPS3_DIR, P.AMPS3_JUDGE)):
        judge = {k: v["judge"] for k, v in X._judge_files(root / d / sj / MODEL).items()}
        amp_p = json.loads((root / d / sa / f"{MODEL}.json").read_text()).get("amp_p") or {}
        gparts = {p_["unit"]: p_ for p_ in P.goat_read_units()} if name == "goat" else {
            p_["unit"]: p_ for p_ in json.loads((root / d / "answers" / f"{MODEL}.json").read_text())["parts"]}
        rows, dropped, by_amp = {}, 0, {}
        for u in [x for x in plan["units"] if x["set"] == name]:
            rec = json.loads((a1_dir() / "shapes" / f"{name}__{u['unit'].replace('/', '__')}.json").read_text())
            backed = P.dfix_backed(u["unit"])
            prt = gparts[u["unit"]]
            ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            g = DE.inference_gain_db(ref, target)           # the clean track at the model's input gain (the review)
            emb = json.loads((a1_dir() / "embed" / f"{name}__{u['unit'].replace('/', '__')}.json").read_text())
            picks = {"embedding": emb["picks"]["stem"], "embedding with no floor": emb["picks"]["stem, no floor"],
                     "embedding on the clean amp track": emb["picks"]["clean amp track"],
                     "stem": {}, "clean amp track": {}, "60 Hz-8 kHz band": {}}
            for sh in ("A", "B"):
                stem = backed[sh][0].tolist()
                picks["stem"][sh] = pick(shape(stem), rec["shapes"][sh])
                picks["clean amp track"][sh] = pick(shape(DS.step4_half(ref, ref, sh, g)[0].tolist()), rec["shapes"][sh])
                picks["60 Hz-8 kHz band"][sh] = band_pick(shape_in(stem, mask), rec, sh, mask)
            for nm, p_ in picks.items():                 # every pick row's spread over the amps (the bias check)
                for sh in ("A", "B"):
                    by_amp.setdefault(nm, {a: 0 for a in AMPS})[p_[sh]] += 1
            w = X.s2_picks(amp_p, u["unit"], FS.AMPS)
            r, dr = unit_rows(u["unit"], u["cluster"], u["cls"], {a: judge[(u["unit"], a)] for a in AMPS}, picks, w)
            dropped += dr
            for k, v in r.items():
                rows.setdefault(k, []).extend(v)
        sets[name] = {k: P.clustered(v) for k, v in rows.items()}
        counts[name] = {"picks_by_amp": by_amp, "dropped": dropped}
    names = sorted(set(sets["bks"]) | set(sets["goat"]))
    jr = {nm: X.judged(sets["bks"].get(nm) or {}, sets["goat"].get(nm) or {}) for nm in names}
    rd = reading(jr["DI-compare - always sw50r"])
    P.save(a1_dir() / "a1.json", {"phase": PHASE, "rows": jr, "counts": counts, "reading": rd,
                                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    for nm in names:
        j = jr[nm]
        p_ = j["pooled"] or {}
        print(f"{nm}: BKS {(j['bks'] or {}).get('mean')}, GOAT {(j['goat'] or {}).get('mean')}, pooled {p_.get('mean')} "
              f"[{p_.get('lo90')}, {p_.get('hi90')}]")
    print(f"A1 READING (DI-compare - always sw50r): {rd}")


def shard(s):
    a, b = s.split("/")
    return int(a), int(b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("a1-draw").set_defaults(fn=cmd_draw)
    r = sub.add_parser("a1-render")
    r.add_argument("--shard", type=shard, default=(0, 1))
    r.set_defaults(fn=cmd_render)
    sub.add_parser("a1-embed").set_defaults(fn=cmd_embed)
    sub.add_parser("a1-rows").set_defaults(fn=cmd_rows)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
