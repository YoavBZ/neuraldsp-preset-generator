"""The model comparison's judge battery (`docs/model-comparison-plan.md`, T3.4), on stored pages, no renders.

    $TORCH_PY -m learn.bakeoff_judge OUT.json              # CPU only

Three terms on each stored item: J0's `distance`, its `tonal`, and a cross-fitted per-band error: the band's mean dB error on
odd 1 s blocks times that on even blocks, averaged over scored bands, with a signed square root, averaged over frame sizes.
A steady error adds to the product; noise that differs between the blocks does not, so it has no floor of its own.
`band_errors` copies `analysis.aligned.aligned_distance`'s default path up to its D, so `control` can hold it to J0.

The pages are in-sample, one listener, 48 items, read many times: a pass here is a screen and leads only to a proposal for a
fresh blind page. No weight is fitted.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

SR = 48000
BLOCK_S = 1.0
EAR = {"same": 0, "barely": 1, "clearly": 2, "very": 3}
TERMS = ("distance", "tonal", "cross")
FLIP_EFFECTS = ("clean-reverb-large", "clean-delay-large")
FLIP_ANCHOR = "clean-anchor-high+6"
KNOWN_PAIRS = (("clean-S", "clean-cab-large"), ("clean-S", "clean-drive-small"), ("clean-S", "clean-drive-large"),
               ("clean-S", "clean-tone-small"), ("crunch-tone-large", "crunch-S"), ("clean-S", "clean-tone-large"),
               ("crunch-S", "clean-tone-large"), ("crunch-S", "clean-drive-large"), ("crunch-S", "clean-S"),
               ("clean-S", "crunch-S"), ("crunch-drive-large", "clean-S"))
ERRORS = ((3.0, "bell", 1600.0), (6.0, "bell", 1600.0), (6.0, "shelf", 4000.0))


# --- pure functions (unit-tested) ------------------------------------------------------------------------------------

def terms_of(frames):
    """[(D [frames, bands], block ids per frame)], one per frame size, D already less its mean. -> {term: value}."""
    dist, ton, cross = [], [], []
    for D, blocks in frames:
        band = D.mean(0)
        dist.append(float(np.abs(D).mean()))
        ton.append(float(np.abs(band).mean()))
        odd = blocks % 2 == 1
        if odd.any() and (~odd).any():
            c = float((D[odd].mean(0) * D[~odd].mean(0)).mean())
            cross.append(math.copysign(math.sqrt(abs(c)), c))
    return {"distance": float(np.mean(dist)), "tonal": float(np.mean(ton)), "cross": float(np.mean(cross)) if cross else 0.0}


def spearman(x, y):
    def rank(a):
        a = np.asarray(a, float)
        order, r = a.argsort(), np.zeros(len(a))
        r[order] = np.arange(len(a))
        for v in set(a.tolist()):
            r[a == v] = r[a == v].mean()
        return r
    a, b = rank(x), rank(y)
    a, b = a - a.mean(), b - b.mean()
    return float(a @ b / math.sqrt((a @ a) * (b @ b) + 1e-15))


def gamma(x, ear):
    """Goodman-Kruskal gamma of a term against the ear's ordered ratings."""
    c = d = 0
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            s = (x[i] - x[j]) * (ear[i] - ear[j])
            c += s > 0
            d += s < 0
    return (c - d) / max(c + d, 1)


def flip_orders(term, ear):
    """Of the ear's strict orders between an effect and the shelf on each page, how many the term shares.
    term, ear: {page: {item: value}}. -> (right, counted)."""
    right = counted = 0
    for page in term:
        for e in FLIP_EFFECTS:
            if ear[page][e] == ear[page][FLIP_ANCHOR]:
                continue
            counted += 1
            right += (term[page][e] - term[page][FLIP_ANCHOR]) * (ear[page][e] - ear[page][FLIP_ANCHOR]) > 0
    return right, counted


def tone_in_top_three(values, groups):
    top = sorted(values, key=values.get, reverse=True)[:3]
    return sum(groups[i] == "tone" for i in top)


def drive_order(values, ear, groups):
    """Share of (heard, unheard) drive pairs the term orders the ear's way."""
    heard = [i for i in values if groups[i] == "drive" and ear[i] >= 1]
    quiet = [i for i in values if groups[i] == "drive" and ear[i] == 0]
    pairs = [(a, b) for a in heard for b in quiet]
    return sum(values[a] > values[b] for a, b in pairs) / len(pairs) if pairs else None


def fft_shape(x, gain_db_of):
    """x through a zero-phase gain curve; gain_db_of(freqs) -> dB."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    f[0] = 1.0
    return np.fft.irfft(X * 10 ** (gain_db_of(f) / 20), len(x))


def bell_gain(fc, db, octaves=1.0):
    return lambda f: db * (0.5 - 0.5 * np.cos(np.pi * np.clip(1 - np.abs(np.log2(f / fc)) / (octaves / 2), 0, 1)))


def shelf_gain(fc, db, width=0.5):
    return lambda f: db * (0.5 - 0.5 * np.cos(np.pi * np.clip((np.log2(f / fc) + width / 2) / width, 0, 1)))


# --- J0's path -------------------------------------------------------------------------------------------------------

def band_errors(recording, render, di, render_latency, start_s, end_s, lag=0, tail_s=1.5, floor_db=30.0, mask_db=40.0, di_floor_db=40.0):
    """`aligned_distance`'s default path up to its D, one per frame size: [(D less its mean, each frame's block)]."""
    import analysis.aligned as A

    recording, render, di = A._signal(recording, "recording"), A._signal(render, "render"), A._signal(di, "DI")
    end = min(len(recording), len(render) + lag, int(end_s * SR))
    start = max(int(start_s * SR), lag if lag > 0 else 0)
    ref, ren = recording[start:end], render[start - lag: end - lag]
    di_start = start - lag - render_latency
    ref_n, ren_n = A._normalise(ref, SR), A._normalise(ren, SR)
    out = []
    for n_fft in A.FRAME_SIZES:
        hop = n_fft // 4
        R, _ = A._logmel(ref_n, n_fft, SR, False)
        X, _ = A._logmel(ren_n, n_fft, SR, False)
        k = min(len(R), len(X))
        R, X = R[:k], X[:k]
        tail, pre = int(round(tail_s * SR / hop)), int(math.ceil(tail_s * SR / hop))
        seg = A._segment(di, di_start - pre * hop, len(ref) + pre * hop)
        playing = A._frame_db(seg, n_fft) >= A._frame_db(di, n_fft).max() - di_floor_db
        scored = A._extend(playing, tail)
        playing, scored = playing[pre: pre + k], scored[pre: pre + k]
        floor_r = np.maximum(R.max() - 70.0, R.max(axis=1, keepdims=True) - mask_db)
        audible = R >= floor_r
        ltas = 10 * np.log10(np.mean(10 ** (np.maximum(R, floor_r)[scored] / 10), axis=0))
        bins = ltas >= ltas.max() - floor_db
        level = float(np.median((X[playing][:, bins] - R[playing][:, bins])[audible[playing][:, bins]]))
        R, X = np.maximum(R, floor_r), np.maximum(X - level, floor_r)
        D = X[scored][:, bins] - R[scored][:, bins]
        out.append((D - D.mean(), (np.nonzero(scored)[0] * hop / SR / BLOCK_S).astype(int)))
    return out


def judged(ref, alt, di, latency):
    """{half: {term: value}}: A and B as `knob_ceiling.judge` scores them."""
    from learn import knob_ceiling as K

    return {h: terms_of(band_errors(ref, alt, di, latency, a, b)) for h, (a, b) in K.R.HALVES.items()}


def mean_terms(by_half):
    return {t: float(np.mean([v[t] for v in by_half.values()])) for t in TERMS}


def spread(values):
    """The noise of a term between halves: the sd of A − B over stored items, per half."""
    return float(np.std([v["A"] - v["B"] for v in values], ddof=1) / math.sqrt(2))


# --- the pages -------------------------------------------------------------------------------------------------------

def page(name):
    """(renders, di, items): items {item: (ref, alt array, group, ear)}, with catches out. The anchors' items carry their page's
    shelf on the alt side."""
    from learn import judge_ear as JE
    from learn import pipeline_fix as P

    root = P.DATA / "learn" / "trusted-data" / name
    lo, hi = JE.trim()
    di = np.asarray(np.load(root / "di.npy"), np.float64)[lo:hi]
    y = lambda j: np.asarray(np.load(root / "renders" / f"{j}.npy"), np.float64)   # noqa: E731
    items = {}
    if name == "judge-ear":
        for r in json.loads((root / "score.json").read_text())["rows"]:
            if r["group"] != "catch" and r["rating"] in EAR:
                items[r["pair"]] = (f"{r['cls']}-S", y(r["pair"]), r["group"], EAR[r["rating"]], r["judge"])
        for r in json.loads((root / "anchors-score.json").read_text())["rows"]:
            if "anchor" in r["item"] and r["rating"] in EAR:
                cls, rest = r["item"].split("-anchor-")
                kind, db = ("high", int(rest[len("high"):])) if rest.startswith("high") else ("low", int(rest[len("low"):]))
                items[r["item"]] = (f"{cls}-S", JE.shelve(y(f"{cls}-S"), kind, db), "anchor", EAR[r["rating"]], r["judge"])
    else:
        plan = {i["item"]: i for i in json.loads((root / "plan.json").read_text())["items"]}
        for r in json.loads((root / "score.json").read_text())["rows"]:
            it = plan[r["item"]]
            if r["group"] == "catch" or r["rating"] not in EAR:
                continue
            alt = y(it["alt"]) if not it["shelf"] else JE.shelve(y(it["alt"]), it["shelf"][0], it["shelf"][1])
            items[r["item"]] = (it["ref"], alt, r["group"], EAR[r["rating"]], r["j0"])
    return y, di, items


def anchors_ear(root):
    """The anchor page's own ratings, the flip's first DI: {item: ear}."""
    return {r["item"]: EAR[r["rating"]] for r in json.loads((root / "anchors-score.json").read_text())["rows"] if r["rating"] in EAR}


def sensitivity():
    """The review's known-error table: on judge-ear's renders as stand-in recordings, each term's change on removing a known
    error, averaged over +e and −e so the pair's own gap cancels, against d, in split-half sds of that term."""
    from learn import knob_ceiling as K

    y, di, _ = page("judge-ear")
    rows, diffs = [], []
    for rec, x in KNOWN_PAIRS:
        base = judged(y(rec), y(x), di, K.P.LATENCY)
        diffs.append(base)
        d0 = mean_terms(base)["distance"]
        for db, kind, fc in ERRORS:
            gain = bell_gain if kind == "bell" else shelf_gain
            fixed, broken = [], []
            for s in (db, -db):
                r2 = fft_shape(y(rec), gain(fc, s))
                fixed.append(mean_terms(judged(r2, fft_shape(y(x), gain(fc, s)), di, K.P.LATENCY)))
                broken.append(mean_terms(judged(r2, y(x), di, K.P.LATENCY)))
            rows.append({"recording": rec, "candidate": x, "d": d0, "error_db": db, "kind": kind,
                         **{t: float(np.mean([b[t] - f[t] for f, b in zip(fixed, broken)])) for t in TERMS}})
    sd = {t: spread([{h: b[h][t] for h in b} for b in diffs]) for t in TERMS}
    return {"rows": rows, "half_sd": sd}


def main(out):
    from learn import knob_ceiling as K
    from learn import pipeline_fix as P

    root = P.DATA / "learn" / "trusted-data" / "judge-ear"
    res = {"pages": {}}
    term_flip, ear_flip = {}, {}
    for name in ("judge-ear", "judge-v5"):
        y, di, items = page(name)
        vals, ear, groups = {}, {}, {}
        worst = 0.0
        for item, (ref, alt, group, rating, stored) in items.items():
            v = mean_terms(judged(y(ref), alt, di, K.P.LATENCY))
            worst = max(worst, abs(v["distance"] - stored))
            vals[item], ear[item], groups[item] = v, rating, group
        if worst > 1e-6:
            raise SystemExit(f"control: {name}: distance differs from the stored judge by {worst:.2e}")
        print(name, "control ok, worst gap", worst, flush=True)
        names = list(vals)
        res["pages"][name] = {"items": len(names), "control_worst": worst, "ear": ear, "values": vals, **{t: {
            "spearman": spearman([vals[i][t] for i in names], [ear[i] for i in names]),
            "gamma": gamma([vals[i][t] for i in names], [ear[i] for i in names]),
            "tone_in_top_three": tone_in_top_three({i: vals[i][t] for i in names if groups[i] != "anchor"}, groups),
            "drive_order": drive_order({i: vals[i][t] for i in names}, ear, groups)} for t in TERMS}}
        term_flip[name] = {t: {i: vals[i][t] for i in names if i in (*FLIP_EFFECTS, FLIP_ANCHOR)} for t in TERMS}
        ear_flip[name] = {i: ear[i] for i in names if i in (*FLIP_EFFECTS, FLIP_ANCHOR)}
    ear_flip["judge-ear"].update({k: v for k, v in anchors_ear(root).items() if k in (*FLIP_EFFECTS, FLIP_ANCHOR)})
    res["flip"] = {"ear": ear_flip, **{t: dict(zip(("right", "counted"), flip_orders({p: term_flip[p][t] for p in term_flip}, ear_flip)))
                                       for t in TERMS}}
    res["sensitivity"] = sensitivity()
    pathlib.Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "pages"})[:1500])


if __name__ == "__main__":
    main(sys.argv[1])
