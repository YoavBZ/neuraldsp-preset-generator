"""The effects route (ledger `phase_fx_reader`, docs/pipeline-fix-plan.md "The effects route").

E0 (zero renders, exploratory): do the product's own blind measures (`analysis.features.time_effects`, through
`analysis.fingerprint` as match runs it on a separated stem) read reverb and delay through the separators? Data: the
judge-v5 separator check's stems (2 presets x 3 backings x 2 ratios x 7 renders, per separator), the renders without
backing as the ceiling and S2 as a second dry case.

    PYTHONPATH=. .venv/bin/python -m learn.fx_reader e0

E1a (zero renders): a reader learned on D_CC's stored examples (`trusted-data/cc`: Morgan targets with random reverb
and delay, each rendered in a fresh process, mixed with the song's other guitars and backing, separated by X-LANCE;
their stored uint8 half log-mels), read leave-one-song-out on three inputs (the X-LANCE stem, the mix, the clean
target as the ceiling), against the training prior and the product's own measures on the clean targets.

    PYTHONPATH=. .venv/bin/python -m learn.fx_reader e1a-data          # arrays, labels, comparators, external stems
    PYTHONPATH=. ~/ndsp-presets/tools/demucs-venv/bin/python -m learn.fx_reader e1a-train [--fold SONG] [--arm stem]
    PYTHONPATH=. ~/ndsp-presets/tools/demucs-venv/bin/python -m learn.fx_reader e1a-score
"""

import argparse
import hashlib
import json
import pathlib
import time

ROOT = pathlib.Path("~/ndsp-presets/learn/trusted-data/judge-v5").expanduser()
SEP = ROOT / "separator-check"
OUT = ROOT / "fx-reader"
SR = 48000
SEPS = ("xlance_g", "htdemucs")
CLASSES = ("clean", "crunch")
BACKINGS = ("eggy", "ronnie", "starnes")
RATIOS = ("med", "q75")
TRUTH = {   # render kind -> (delay ms or None, delay mix, reverb mix, reverb decay)
    "S": (None, 0, 0, None),
    "reverb-small": (None, 0, 0.15, 1.48), "reverb-large": (None, 0, 0.40, 1.48), "reverb-decay": (None, 0, 0.40, 3.0),
    "delay-small": (500.0, 0.15, 0, None), "delay-large": (500.0, 0.40, 0, None), "delay-time": (300.0, 0.40, 0, None),
}
SET_FEEDBACK = 0.30
TOL = 0.05                   # +-5% of the set time (declared; the code's own `fundamental()` uses 1%)
FLOOR = 0.15                 # `match.invert.delay_settings` / `compare._ambience`
COMB_CAP = 0.14              # `features.DELAY_COMB_CONFIDENCE_CAP`
HALVES = {"full": None, "0-5": (0, 5), "5-10": (5, 10)}


def time_fx(y):
    from analysis import fingerprint as FP
    from analysis import io

    return dict(FP.fingerprint(io.from_samples(y, SR), regime="separated_stem").time_fx)


def mono(a):
    import numpy as np

    a = np.asarray(a, np.float64)
    return a.mean(axis=1) if a.ndim == 2 else a


def near(ms, target):
    return ms is not None and abs(ms - target) <= TOL * target


def delay_outcome(fx, target):
    """(a) hit at or above the floor; (b) within tolerance at the comb cap; (c) at 2x or 1/2x; (d) none/elsewhere."""
    ms, conf = fx.get("delay_ms"), float(fx.get("delay_confidence") or 0.0)
    if near(ms, target):
        if conf >= FLOOR:
            return "a"
        if abs(conf - COMB_CAP) < 1e-6:
            return "b"
        return "d"
    if ms is not None and (near(ms, 2 * target) or near(ms, target / 2)):
        return "c"
    return "d"


def reverb_outcome(fx):
    """`match.invert.reverb_from_rt60`'s decision, counterfactually (the product applies it to probes only)."""
    from match import invert as INV

    class F:
        time_fx = fx
        regime = "probe"

    inv = INV.reverb_from_rt60(F())
    if inv.values.get("reverb/reverbActive"):
        return "on"
    rt60, conf = fx.get("rt60_s"), float(fx.get("rt60_confidence") or 0.0)
    if rt60 is None:
        return "no-tail"
    if conf < 0.3:
        return "low-conf"
    return "below-floor"


def items():
    """Every audio item: (source, cls, backing, ratio, kind, path or render key)."""
    out = []
    for sep in SEPS:
        for c in CLASSES:
            for b in BACKINGS:
                for r in RATIOS:
                    for k in TRUTH:
                        out.append((sep, c, b, r, k, SEP / "stems" / sep / f"{c}-{b}-{r}-{k}.npy"))
    for c in CLASSES:
        for k in tuple(TRUTH) + ("S2",):
            out.append(("clean-render", c, "-", "-", k, ROOT / "renders" / f"{c}-{k}.npy"))
    return out


def cmd_e0(args):
    import numpy as np

    OUT.mkdir(parents=True, exist_ok=True)
    feats = pathlib.Path(__file__).resolve().parent.parent / "analysis" / "features.py"
    rows = []
    for src, c, b, r, k, path in items():
        y = mono(np.load(path))
        for h, span in HALVES.items():
            seg = y if span is None else y[span[0] * SR: span[1] * SR]
            fx = time_fx(seg)
            rows.append({"src": src, "cls": c, "backing": b, "ratio": r, "kind": k, "half": h,
                         **{f: (None if fx.get(f) is None else (float(fx[f]) if not isinstance(fx[f], str) else fx[f]))
                            for f in ("delay_ms", "delay_confidence", "delay_feedback_est", "bpm_est", "rt60_s",
                                      "rt60_confidence", "predelay_ms")},
                         "delay_note_division": fx.get("delay_note_division"),
                         "reverb_rule": reverb_outcome(fx)})
        print(src, c, b, r, k, flush=True)
    res = {"time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "features_sha256": hashlib.sha256(feats.read_bytes()).hexdigest(),
           "rows": rows, "summary": summarise(rows)}
    (OUT / "e0.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res["summary"], indent=1))


def summarise(rows):
    import numpy as np

    out = {}
    by = {(x["src"], x["cls"], x["backing"], x["ratio"], x["kind"], x["half"]): x for x in rows}
    for src in SEPS + ("clean-render",):
        for h in HALVES:
            s = {}
            cells = [(c, b, r) for c in CLASSES for b in BACKINGS for r in RATIOS] if src != "clean-render" \
                else [(c, "-", "-") for c in CLASSES]
            for k, (dms, dmix, rmix, rdec) in TRUTH.items():
                got = [by[(src, c, b, r, k, h)] for c, b, r in cells]
                d = {"n": len(got)}
                if dms is not None:
                    oc = []
                    for (c, b, r), x in zip(cells, got):
                        o = delay_outcome(x, dms)
                        if o == "a" and dms == 500.0 and near(by[(src, c, b, r, "S", h)]["delay_ms"], 500.0):
                            o = "a-but-S-500"
                        oc.append(o)
                    d["delay_outcomes"] = {o: oc.count(o) for o in sorted(set(oc))}
                    d["delay_outcomes_by_cell"] = {f"{c}-{b}-{r}": o for (c, b, r), o in zip(cells, oc)}
                    fb = [x["delay_feedback_est"] for x in got if x["delay_feedback_est"] is not None and near(x["delay_ms"], dms)]
                    d["feedback_est_median_at_hits"] = float(np.median(fb)) if fb else None
                else:
                    d["false_delay_reports"] = sum(1 for x in got if x["delay_ms"] is not None
                                                   and float(x["delay_confidence"] or 0) >= FLOOR)
                    d["delay_reports_any_conf"] = sum(1 for x in got if x["delay_ms"] is not None)
                rt = [x["rt60_s"] for x in got if x["rt60_s"] is not None]
                d["rt60_median"] = float(np.median(rt)) if rt else None
                d["rt60_conf_median"] = float(np.median([x["rt60_confidence"] or 0 for x in got]))
                rr = [x["reverb_rule"] for x in got]
                d["reverb_rule"] = {o: rr.count(o) for o in sorted(set(rr))}
                d["reverb_rule_correct"] = sum((o == "on") == (rmix > 0) for o in rr)
                s[k] = d
            # matched pairs
            def rises(k1, k0, f):
                n = up = 0
                for c, b, r in cells:
                    v1, v0 = by[(src, c, b, r, k1, h)][f], by[(src, c, b, r, k0, h)][f]
                    v1 = 0.0 if v1 is None else v1
                    v0 = 0.0 if v0 is None else v0
                    n += 1
                    up += v1 > v0
                return {"up": up, "n": n}
            s["pairs"] = {"rt60 S->reverb-large": rises("reverb-large", "S", "rt60_s"),
                          "rt60 reverb-large->reverb-decay": rises("reverb-decay", "reverb-large", "rt60_s"),
                          "delay_conf delay-small->delay-large": rises("delay-large", "delay-small", "delay_confidence")}
            out[f"{src}|{h}"] = s
    return out


# ---------------------------------------------------------------- E1a

CC = pathlib.Path("~/ndsp-presets/learn/trusted-data/cc").expanduser()
E1A = OUT / "e1a"
ARMS = {"stem": "xlance_g-cc", "mix": "mix-cc", "target": "tgt-cc"}
HALF_KEYS = {"stem": ("sA", "sB"), "mix": ("mA", "mB"), "target": ("gA", "gB")}
NS_SONGS = ("AdamBuckley_DragMeDown_Full", "TheMaybeNextYears_OneFlipFlop_Full")   # held out: never read here
E0_SONG = "TheTravellingBand_Quicksand_Full"       # E0's DI: the external check uses the fold that holds it out
LAGS = 150                                         # mel-envelope autocorrelation lags, 10 ms each (to 1.5 s)
SEED = 20261107
BOOT_SEED = 20261108
BOOT_N = 2000
EPOCHS = 40
BATCH = 64
LR = 1e-3
INNER_SHARE = 0.15                                 # the training songs' sections held for early stopping
SPRING_MIN = 1e-3
SPRING_LEVEL = {"pr12": "pr12Amp/pr12Reverb", "sw50r": "sw50rAmp/sw50rReverb"}   # the AC20 has none
KNOBS = ("rmix", "rdecay", "dmix", "dtime", "dfb")  # rmix/dmix/dfb rotations; rdecay, dtime log2
E1C = OUT / "e1c"                                  # E1a plus a lag head for delay time (same data build)
LAG_SIGMA = 1.0                                    # soft target: a Gaussian of one lag around the set lag
LAG_RANGE = (6, 80)                                # lags searched: the draw's 60-800 ms (a range the product can be given)


def labels(settings, amp):
    import math

    s = settings
    ron = s.get("reverb/reverbActive") == "true"
    don = s.get("delay/delayActive") == "true"
    k = SPRING_LEVEL.get(amp)
    spring = float(s.get(k, 0) or 0) if k else 0.0          # only the selected amp's spring sounds
    return {"ron": float(ron), "don": float(don),
            "rmix": float(s["reverb/reverbMix"]) if ron else float("nan"),
            "rdecay": math.log2(float(s["reverb/reverbDecay"])) if ron else float("nan"),
            "dmix": float(s["delay/delayMix"]) if don else float("nan"),
            "dtime": math.log2(float(s["delay/delayTime"])) if don else float("nan"),
            "dfb": float(s["delay/delayFeedback"]) if don else float("nan"),
            "spring": float(spring > SPRING_MIN)}


def env_acf(q):
    """Mean over mel bands (weighted by band level) of the normalised autocorrelation of each band's dB series,
    lags 1..LAGS frames (10 ms each): what repeats in the envelope, where an echo shows."""
    import numpy as np

    db = np.asarray(q, np.float64) * 0.5
    w = db.mean(axis=1)
    w = np.clip(w - w.max() + 40.0, 0, None)
    x = db - db.mean(axis=1, keepdims=True)
    n = x.shape[1]
    f = np.fft.rfft(x, 2 * n, axis=1)
    ac = np.fft.irfft(np.abs(f) ** 2, axis=1)[:, : LAGS + 1]
    ac = ac / np.maximum(ac[:, :1], 1e-9)
    return (ac[:, 1:] * w[:, None]).sum(0) / max(w.sum(), 1e-9)


def stem_feats(y):
    from learn import direct_stems as DS

    m, _, _ = DS.half_features(y)
    return m["A"], m["B"]


def cmd_e1a_data(args):
    """Zero renders: the examples with all three stored inputs, their labels, the product's measures on the clean
    targets, and the external check's features (E0's 84 X-LANCE stems)."""
    import glob

    import numpy as np
    import soundfile as sf

    E1A.mkdir(parents=True, exist_ok=True)
    rows = {}
    for f in sorted(glob.glob(str(CC / "rows" / "render-*.jsonl"))):
        for line in open(f):
            r = json.loads(line)
            rows[r["i"]] = r
    plan = json.loads((CC / "plan.json").read_text())
    keep, X, A, L, meta = [], {a: [] for a in ARMS}, {a: [] for a in ARMS}, [], []
    skipped = {"ns": 0, "missing": 0}
    for e in plan["examples"]:
        song = e["section"].split("/")[1]
        if song in NS_SONGS:
            skipped["ns"] += 1
            continue
        i = e["i"]
        paths = {a: CC / "build" / "ex" / f"{i:07d}"[:4] / f"{i:07d}-{k}.npz" for a, k in ARMS.items()}
        if i not in rows or not all(p.exists() for p in paths.values()):
            skipped["missing"] += 1
            continue
        for a, p in paths.items():
            z = np.load(p)
            ha, hb = (z[k] for k in HALF_KEYS[a])
            X[a].append(np.stack([ha, hb]))
            A[a].append(np.concatenate([env_acf(ha), env_acf(hb)]))
        L.append(labels(rows[i]["settings"], e["amp"]))
        meta.append({"i": i, "song": song, "band": e["band"], "section": e["section"], "amp": e["amp"],
                     "base": e["base"], "mode": rows[i].get("mode"), "centre": rows[i].get("centre")})
    for a in ARMS:
        np.save(E1A / f"x-{a}.npy", np.stack(X[a]))
        np.save(E1A / f"acf-{a}.npy", np.stack(A[a]).astype(np.float32))
    np.save(E1A / "labels.npy", np.array([[l[k] for k in ("ron", "don") + KNOBS + ("spring",)] for l in L], np.float32))
    # the product's own measures on the clean targets (their ceiling)
    meas = []
    for m in meta:
        f = CC / "audio" / f"{m['i']:07d}"[:4] / f"{m['i']:07d}-target.flac"
        if not f.exists():
            meas.append(None)
            continue
        y, sr = sf.read(str(f))
        fx = time_fx(mono(y))
        meas.append({"delay_ms": fx.get("delay_ms"), "delay_confidence": float(fx.get("delay_confidence") or 0),
                     "rt60_s": fx.get("rt60_s"), "rt60_confidence": float(fx.get("rt60_confidence") or 0),
                     "reverb_rule": reverb_outcome(fx)})
    # external: E0's X-LANCE stems
    ext, extx, exta, extl = [], [], [], []
    for c in CLASSES:
        for b in BACKINGS:
            for r in RATIOS:
                for k in TRUTH:
                    y = np.load(SEP / "stems" / "xlance_g" / f"{c}-{b}-{r}-{k}.npy")
                    from learn import song_aug as SA

                    ha, hb = stem_feats(mono(y))
                    extl.append(float(SA.lufs(mono(y))))
                    extx.append(np.stack([ha, hb]))
                    exta.append(np.concatenate([env_acf(ha), env_acf(hb)]))
                    ext.append({"cls": c, "backing": b, "ratio": r, "kind": k})
    np.save(E1A / "x-ext.npy", np.stack(extx))
    np.save(E1A / "acf-ext.npy", np.stack(exta).astype(np.float32))
    stem_lufs = []
    for m in meta:
        z = np.load(CC / "build" / "ex" / f"{m['i']:07d}"[:4] / f"{m['i']:07d}-xlance_g-cc.npz")
        stem_lufs.append(float(np.mean(z["lufs"])))
    (E1A / "meta.json").write_text(json.dumps({
        "examples": meta, "skipped": skipped, "measures": meas, "ext": ext,
        "label_cols": ["ron", "don", *KNOBS, "spring"],
        "ext_lufs_summary": {"e0_stems_median": float(np.median(extl)),
                             "dcc_stems_half_mean_median": float(np.median(stem_lufs))}}, indent=0))
    print(f"E1a data: {len(meta)} examples ({skipped}), {len(set(m['song'] for m in meta))} songs; "
          f"{sum(x is not None for x in meas)} with measures; {len(ext)} external stems")


def folds():
    meta = json.loads((E1A / "meta.json").read_text())["examples"]
    return sorted({m["song"] for m in meta})


def prominence(torch, a):
    """Each half's autocorrelation minus its local mean (lags 3-6 frames either side): (B, 2*LAGS) -> (B, 2, LAGS)."""
    x = a.view(a.shape[0], 2, LAGS)
    k = torch.tensor([1.0] * 4 + [0.0] * 5 + [1.0] * 4, device=a.device) / 8.0     # offsets -6..-3 and +3..+6
    pad = torch.nn.functional.pad(x, (6, 6), mode="replicate")
    nb = torch.nn.functional.conv1d(pad.reshape(-1, 1, LAGS + 12), k.view(1, 1, -1)).view_as(x)
    return x - nb


def net(torch, lag=False):
    nn = torch.nn

    class Reader(nn.Module):
        def __init__(self):
            super().__init__()
            if lag:          # E1c: logits over lags from the prominence curve, shared over halves (slides over lags);
                with torch.random.fork_rng(devices=[]):     # drawn on a forked stream: the trunk's weights stay E1a's
                    self.lag = nn.Sequential(nn.Conv1d(1, 16, 5, padding=2), nn.ReLU(),
                                             nn.Conv1d(16, 16, 5, padding=2), nn.ReLU(), nn.Conv1d(16, 1, 1))
            layers, c = [], 2
            for w in (16, 32, 64, 96):
                layers += [nn.Conv2d(c, w, 3, padding=1), nn.BatchNorm2d(w), nn.ReLU(), nn.AvgPool2d(2)]
                c = w
            self.conv = nn.Sequential(*layers)
            self.acf = nn.Sequential(nn.Linear(2 * LAGS, 64), nn.ReLU())
            self.fc = nn.Sequential(nn.Linear(2 * c + 64, 128), nn.ReLU(), nn.Dropout(0.2))
            self.head = nn.Linear(128, 2 + len(KNOBS))

        def forward(self, x, a):
            h = self.conv(x)
            h = torch.cat([h.mean(dim=(2, 3)), h.amax(dim=(2, 3))], 1)
            out = self.head(self.fc(torch.cat([h, self.acf(a)], 1)))
            if lag:
                p = prominence(torch, a)
                g = self.lag(p.reshape(-1, 1, LAGS)).view(a.shape[0], 2, LAGS).sum(1)
                k = torch.arange(1, LAGS + 1, device=a.device)
                g = g.masked_fill((k < LAG_RANGE[0]) | (k > LAG_RANGE[1]), -1e4)
                out = torch.cat([out, g], 1)
            return out

    return Reader()


def norm_knobs(y):
    """Knob targets on comparable scales: rotations as is, log2 decay and time centred on their declared ranges."""
    import numpy as np

    z = np.array(y, np.float32)
    z[:, 3] = (z[:, 3] - 1.0) / 2.0          # log2 decay value 1..6 -> -0.5..0.79
    z[:, 5] = (z[:, 5] - 6.0) / 4.0          # log2 time 60..800 ms -> about -0.03..0.9
    return z


def denorm(z):
    import numpy as np

    y = np.array(z, np.float64)
    y[:, 3] = y[:, 3] * 2.0 + 1.0
    y[:, 5] = y[:, 5] * 4.0 + 6.0
    return y


def cmd_e1a_train(args):
    _train(args, E1A / "runs", lag=False)


def cmd_e1c_train(args):
    _train(args, E1C / "runs", lag=True)


def lag_target(t_log2):
    """Soft lag targets (n, LAGS) for set times (log2 ms): lag k (k = 1..LAGS, 10 ms each) at index k - 1, within
    LAG_RANGE (the head's unmasked lags) and renormalised there."""
    import numpy as np

    k = np.arange(1, LAGS + 1)
    c = 2.0 ** np.asarray(t_log2, np.float64)[:, None] / 10.0
    g = np.exp(-0.5 * ((k[None] - c) / LAG_SIGMA) ** 2) * ((k >= LAG_RANGE[0]) & (k <= LAG_RANGE[1]))[None]
    return (g / g.sum(1, keepdims=True)).astype(np.float32)


def _train(args, root, lag):
    import numpy as np
    import torch

    import hashlib as H

    meta = json.loads((E1A / "meta.json").read_text())["examples"]
    meta_sha = H.sha256((E1A / "meta.json").read_bytes()).hexdigest()
    songs = np.array([m["song"] for m in meta])
    sections = np.array([m["section"] for m in meta])
    Y = norm_knobs(np.load(E1A / "labels.npy")[:, :2 + len(KNOBS)])
    if lag:              # lag targets appended; NaN rows (delay off) carry no lag loss
        tl = np.load(E1A / "labels.npy")[:, 2 + KNOBS.index("dtime")]
        T = np.full((len(Y), LAGS), np.nan, np.float32)
        T[~np.isnan(tl)] = lag_target(tl[~np.isnan(tl)])
        Y = np.concatenate([Y, T], 1)
    nk = 2 + len(KNOBS)
    dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    todo = [args.fold] if args.fold else folds()
    arms = [args.arm] if args.arm else list(ARMS)
    for arm in arms:
        X = np.load(E1A / f"x-{arm}.npy", mmap_mode="r")
        Ac = np.load(E1A / f"acf-{arm}.npy")
        ext = arm == "stem"
        for song in todo:
            out = root / arm / f"{song}.npz"
            if out.exists() and not args.force:
                continue
            t0 = time.time()
            torch.manual_seed(SEED)
            rng = np.random.default_rng(SEED)
            tr = np.where(songs != song)[0]
            secs = sorted(set(sections[tr]))
            inner_secs = set(rng.choice(secs, max(1, int(INNER_SHARE * len(secs))), replace=False))
            inner = np.array([i for i in tr if sections[i] in inner_secs])
            fit = np.array([i for i in tr if sections[i] not in inner_secs])
            te = np.where(songs == song)[0]
            model = net(torch, lag=lag).to(dev)
            opt = torch.optim.Adam(model.parameters(), lr=LR)

            def batch(idx):
                x = torch.tensor(np.asarray(X[idx], np.float32) / 255.0, device=dev)
                a = torch.tensor(Ac[idx], device=dev)
                return x, a

            def main_loss(out, y):     # E1a's loss (y a tensor); the trunk's epoch choice, unchanged by a lag head
                bce = torch.nn.functional.binary_cross_entropy_with_logits(out[:, :2], y[:, :2])
                k, t = out[:, 2:nk], y[:, 2:nk]
                m = ~torch.isnan(t)
                mse = ((k - torch.nan_to_num(t)) ** 2)[m].mean() if m.any() else out.sum() * 0
                return bce + mse

            def lag_ce(out, y):
                on = ~torch.isnan(y[:, nk])
                return (-(y[on, nk:] * torch.log_softmax(out[on, nk:], 1)).sum(1)).mean() if on.any() else out.sum() * 0

            def loss_fn(out, y):
                y = torch.tensor(y, device=dev)
                return main_loss(out, y) + lag_ce(out, y) if lag else main_loss(out, y)

            def predict(idx_or_x, a=None):
                model.eval()
                res = []
                with torch.no_grad():
                    if a is None:
                        for j in range(0, len(idx_or_x), 256):
                            x, aa = batch(idx_or_x[j:j + 256])
                            res.append(model(x, aa).cpu().numpy())
                    else:
                        for j in range(0, len(idx_or_x), 256):
                            x = torch.tensor(np.asarray(idx_or_x[j:j + 256], np.float32) / 255.0, device=dev)
                            res.append(model(x, torch.tensor(a[j:j + 256], device=dev)).cpu().numpy())
                return np.concatenate(res)

            best, best_state, best_ep, curve = None, None, -1, []
            lbest, lbest_state, lbest_ep, lcurve = None, None, -1, []
            for ep in range(EPOCHS):
                model.train()
                perm = rng.permutation(fit)
                for j in range(0, len(perm), BATCH):
                    idx = np.sort(perm[j:j + BATCH])
                    x, a = batch(idx)
                    opt.zero_grad()
                    l = loss_fn(model(x, a), Y[idx])
                    l.backward()
                    opt.step()
                model.eval()
                with torch.no_grad():
                    pv = torch.tensor(predict(inner), device=dev)
                    yi = torch.tensor(Y[inner], device=dev)
                    vl = float(main_loss(pv, yi))
                    if lag:
                        cl = float(lag_ce(pv, yi))
                curve.append(vl)
                if best is None or vl < best:
                    best, best_ep = vl, ep
                    best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
                if lag:
                    lcurve.append(cl)
                    if lbest is None or cl < lbest:     # the lag head's own epoch, by its inner cross-entropy
                        lbest, lbest_ep = cl, ep
                        lbest_state = {k: v.detach().clone() for k, v in model.lag.state_dict().items()}
            model.load_state_dict(best_state)
            if lag:
                model.lag.load_state_dict(lbest_state)
            pred = predict(te)
            res = {"idx": te, "pred": pred, "curve": np.array(curve), "best_epoch": best_ep,
                   "minutes": (time.time() - t0) / 60, "meta_sha256": meta_sha}
            if lag:
                res.update(lag_curve=np.array(lcurve), lag_best_epoch=lbest_ep)
            if ext and song == E0_SONG:
                res["ext_pred"] = predict(np.load(E1A / "x-ext.npy"), np.load(E1A / "acf-ext.npy"))
            out.parent.mkdir(parents=True, exist_ok=True)
            np.savez(out, **res)
            print(f"{arm} {song}: {len(fit)} fit, {len(inner)} inner, {len(te)} test; best epoch {best_ep}; "
                  f"{res['minutes']:.1f} min", flush=True)


def picker(A):
    """F49's training-free time picker: per half, each lag's autocorrelation minus the mean of lags +-3..6 (missing
    neighbours dropped at the edges), summed over halves; the argmax within LAG_RANGE, as log2 ms."""
    import numpy as np

    x = np.asarray(A, np.float64).reshape(len(A), 2, LAGS)
    p = np.empty_like(x)
    for k in range(LAGS):
        nb = [j for j in list(range(k - 6, k - 2)) + list(range(k + 3, k + 7)) if 0 <= j < LAGS]
        p[:, :, k] = x[:, :, k] - x[:, :, nb].mean(2)
    s = p.sum(1)[:, LAG_RANGE[0] - 1:LAG_RANGE[1]]
    return np.log2(10.0 * (np.argmax(s, 1) + LAG_RANGE[0]))


def spearman(a, b):
    import numpy as np
    from scipy.stats import spearmanr

    a, b = np.asarray(a), np.asarray(b)
    return float(spearmanr(a, b)[0]) if len(a) > 2 else float("nan")


def auc(y, s):
    import numpy as np

    y, s = np.asarray(y), np.asarray(s)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    from scipy.stats import rankdata

    r = rankdata(np.concatenate([pos, neg]))
    return float((r[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def cmd_e1a_score(args):
    _score(E1A / "runs", E1A / "score.json", lag=False)


def cmd_e1c_score(args):
    _score(E1C / "runs", E1C / "score.json", lag=True)


def _score(root, dest, lag):
    """Every readout on all items and on the wide draws (every switch a fair coin, every knob uniform and independent
    of the other controls): the reader, the draw-only comparator, the median priors (all draws; and, draw-aware, the
    wide-draw median and the amp x draw x class cell median), the product's measures; with lag, E1c's time readouts."""
    import hashlib as H

    import numpy as np

    mj = json.loads((E1A / "meta.json").read_text())
    meta_sha = H.sha256((E1A / "meta.json").read_bytes()).hexdigest()
    meta = mj["examples"]
    n = len(meta)
    songs = np.array([m["song"] for m in meta])
    bands = np.array([m["band"] for m in meta])
    wide = np.array([m["mode"] == "wide" for m in meta])
    L = np.load(E1A / "labels.npy")
    Yk = L[:, 2:2 + len(KNOBS)]
    spring = L[:, -1]
    cl = sorted(set(bands))
    rng = np.random.default_rng(BOOT_SEED)
    boots = [np.concatenate([np.where(bands == cl[j])[0] for j in rng.integers(0, len(cl), len(cl))])
             for _ in range(BOOT_N)]

    def ci(fn):
        v = [fn(b) for b in boots]
        v = [x for x in v if x == x]
        return [float(np.percentile(v, 5)), float(np.percentile(v, 95))] if v else [None, None]

    # comparators that use no audio
    prior = np.full_like(Yk, np.nan, dtype=np.float64)
    pw = np.full_like(Yk, np.nan, dtype=np.float64)       # draw-aware: the training songs' wide-draw median
    pc = np.full_like(Yk, np.nan, dtype=np.float64)       # draw-aware: the amp x draw x class cell median
    cell = np.array(["|".join((m["amp"], m["mode"], m["base"])) for m in meta])
    draw = np.full((n, 2), np.nan)
    for song in folds():
        te, tr = songs == song, songs != song
        prior[te] = np.nanmedian(Yk[tr], axis=0)
        pw[te] = np.nanmedian(Yk[tr & wide], axis=0)
        for c in set(cell[te]):
            mt = tr & (cell == c)
            draw[te & (cell == c)] = (L[mt, :2].sum(0) + 2 * L[tr, :2].mean(0)) / (mt.sum() + 2)
            v = np.nanmedian(Yk[mt], axis=0) if mt.any() else prior[te][0]
            pc[te & (cell == c)] = np.where(np.isnan(v), prior[te][0], v)

    def readouts(P, K, mask):
        r = {"n": int(mask.sum())}
        for e, (col, mixcol) in {"reverb": (0, 0), "delay": (1, 2)}.items():
            y, s, dr = L[:, col], P[:, col], draw[:, col]
            on_mix = Yk[:, mixcol]
            ons = mask & (y == 1)
            hi, lo = np.nanpercentile(on_mix[ons], 100 * 2 / 3), np.nanpercentile(on_mix[ons], 100 / 3)
            m_all = mask
            m_strong = mask & ((y == 0) | ((y == 1) & (on_mix >= hi)))
            m_weak = mask & ((y == 0) | ((y == 1) & (on_mix < lo)))
            d = {"strong_mix_from": float(hi), "weak_mix_below": float(lo)}
            for name, m in (("all", m_all), ("strong_third", m_strong), ("weak_third", m_weak)):
                d[name] = {"auc": auc(y[m], s[m]), "auc_ci": ci(lambda b: auc(y[b][m[b]], s[b][m[b]])),
                           "auc_draw": auc(y[m], dr[m]),
                           "reader_minus_draw": auc(y[m], s[m]) - auc(y[m], dr[m]),
                           "reader_minus_draw_ci": ci(lambda b: auc(y[b][m[b]], s[b][m[b]]) - auc(y[b][m[b]], dr[b][m[b]]))}
            bs = {c: auc(y[mask & (songs == c)], s[mask & (songs == c)]) for c in sorted(set(songs))}
            d["auc_by_song"] = bs
            v = [x for x in bs.values() if x == x]
            d["auc_song_mean"] = float(np.mean(v)) if v else None
            if e == "reverb":
                for nm, sp in (("spring_on_offs", 1), ("spring_off_offs", 0)):
                    m = mask & ((y == 1) | ((y == 0) & (spring == sp)))
                    d[nm] = {"auc": auc(y[m], s[m]), "auc_ci": ci(lambda b: auc(y[b][m[b]], s[b][m[b]])),
                             "n_offs": int((m & (y == 0)).sum())}
            r[e] = d
        kn = {}
        for j, k in enumerate(KNOBS):
            on = mask & ~np.isnan(Yk[:, j])
            err = np.abs(K[:, j] - Yk[:, j])
            perr = np.abs(prior[:, j] - Yk[:, j])
            kn[k] = {"n_on": int(on.sum()), "mae_reader": float(np.mean(err[on])), "mae_prior": float(np.mean(perr[on])),
                     "diff": float(np.mean(err[on]) - np.mean(perr[on])),
                     "diff_ci": ci(lambda b: float(np.mean(err[b][on[b]]) - np.mean(perr[b][on[b]])))}
            for nm, pv in (("wide_median", pw), ("cell_median", pc)):
                qerr = np.abs(pv[:, j] - Yk[:, j])
                kn[k][f"mae_{nm}"] = float(np.mean(qerr[on]))
                kn[k][f"diff_vs_{nm}"] = float(np.mean(err[on]) - np.mean(qerr[on]))
                kn[k][f"diff_vs_{nm}_ci"] = ci(lambda b: float(np.mean(err[b][on[b]]) - np.mean(qerr[b][on[b]])))
            kn[k]["spearman"] = spearman(K[on, j], Yk[on, j])
            if k == "dtime":
                kn[k]["within_10pct_reader"] = float(np.mean(np.abs(2 ** (K[on, j] - Yk[on, j]) - 1) <= 0.10))
                kn[k]["within_10pct_prior"] = float(np.mean(np.abs(2 ** (prior[on, j] - Yk[on, j]) - 1) <= 0.10))
        r["knobs"] = kn
        if lag:
            r["time"] = time_readouts(mask)
        return r

    def time_readouts(mask):
        """E1c on delay-ons: the lag head (within +-10% from its argmax lag; MAE and Spearman from its posterior
        median), the training-free picker (argmax of the summed prominence), E1a's regression head, against the
        draw-aware priors and, for the head, against the picker."""
        j = KNOBS.index("dtime")
        y = Yk[:, j]
        ons = mask & ~np.isnan(y)
        hi, lo = np.nanpercentile(Yk[ons, 2], 100 * 2 / 3), np.nanpercentile(Yk[ons, 2], 100 / 3)
        within = lambda est: np.abs(2 ** (est - y) - 1) <= 0.10
        cand = {"lag_head": (T_arg, T_med), "picker": (T_pick, T_pick), "regression": (K[:, j], K[:, j])}
        priors = (("wide_median", pw[:, j]), ("cell_median", pc[:, j]), ("all_median", prior[:, j]))
        res = {}
        for part, m in (("all", ons), ("strong_third", ons & (Yk[:, 2] >= hi)), ("weak_third", ons & (Yk[:, 2] < lo))):
            d = {"n": int(m.sum())}
            for nm, (hit_est, pt_est) in cand.items():
                w, e = within(hit_est), np.abs(pt_est - y)
                d[nm] = {"within_10pct": float(w[m].mean()), "mae_log2": float(e[m].mean()),
                         "spearman": spearman(pt_est[m], y[m]),
                         "spearman_ci": ci(lambda b: spearman(pt_est[b][m[b]], y[b][m[b]])),
                         "double_lag_share": float((np.abs(2 ** (hit_est - y) - 2) <= 0.2)[m].mean())}
                others = priors + ((("picker", T_pick),) if nm == "lag_head" else ())
                for pn, pv in others:
                    pw_, pe = within(pv), np.abs(pv - y)
                    d[nm][f"within_diff_vs_{pn}"] = float(w[m].mean() - pw_[m].mean())
                    d[nm][f"within_diff_vs_{pn}_ci"] = ci(lambda b: float(w[b][m[b]].mean() - pw_[b][m[b]].mean()))
                    d[nm][f"mae_diff_vs_{pn}"] = float(e[m].mean() - pe[m].mean())
                    d[nm][f"mae_diff_vs_{pn}_ci"] = ci(lambda b: float(e[b][m[b]].mean() - pe[b][m[b]].mean()))
            for pn, pv in priors:
                d[f"prior_{pn}"] = {"within_10pct": float(within(pv)[m].mean()),
                                    "mae_log2": float(np.abs(pv - y)[m].mean())}
            res[part] = d
        return res

    out = {"n": n, "songs": sorted(set(songs)), "bands": cl, "n_wide": int(wide.sum()), "meta_sha256": meta_sha,
           "arms": {}}
    nk = 2 + len(KNOBS)
    for arm in ARMS:
        P = np.full((n, nk + (LAGS if lag else 0)), np.nan)
        minutes, epochs = {}, {}
        for song in folds():
            f = root / arm / f"{song}.npz"
            if not f.exists():
                continue
            z = np.load(f)
            if str(z["meta_sha256"]) != meta_sha:
                raise SystemExit(f"{f}: trained on another data build")
            P[z["idx"]] = z["pred"]
            minutes[song] = float(z["minutes"])
            epochs[song] = int(z["best_epoch"])
        if np.isnan(P[:, 0]).any():
            out["arms"][arm] = {"missing": int(np.isnan(P[:, 0]).sum())}
            continue
        K = denorm(P[:, :nk])[:, 2:]
        if lag:
            g = P[:, nk:]
            pr_ = np.exp(g - g.max(1, keepdims=True))
            pr_ /= pr_.sum(1, keepdims=True)
            T_arg = np.log2(10.0 * (np.argmax(g, 1) + 1))
            T_med = np.log2(10.0 * (np.argmax(np.cumsum(pr_, 1) >= 0.5, 1) + 1))    # posterior median lag
            T_pick = picker(np.load(E1A / f"acf-{arm}.npy"))
        out["arms"][arm] = {"train_minutes": minutes, "best_epochs": epochs,
                            "all": readouts(P, K, np.ones(n, bool)), "wide": readouts(P, K, wide)}
        if arm == "stem":
            f = root / "stem" / f"{E0_SONG}.npz"
            if f.exists() and "ext_pred" in np.load(f).files:
                ep = np.load(f)["ext_pred"]
                pr = 1 / (1 + np.exp(-ep[:, :2]))
                ek = denorm(ep[:, :nk])[:, 2:]
                by = {}
                for j, x in enumerate(mj["ext"]):
                    by.setdefault(x["kind"], []).append((pr[j, 0], pr[j, 1], 2 ** ek[j, 1], 2 ** ek[j, 3]))
                out["external"] = {k: {"p_reverb_median": float(np.median([v[0] for v in vs])),
                                       "p_delay_median": float(np.median([v[1] for v in vs])),
                                       "reverb_decay_median": float(np.median([v[2] for v in vs])),
                                       "delay_time_ms_median": float(np.median([v[3] for v in vs]))}
                                   for k, vs in by.items()}
                out["external_lufs"] = mj.get("ext_lufs_summary")
    # the product's own measures on the clean targets (a ceiling for them, not like for like with the stem reader)
    ms = mj["measures"]
    for name, mask in (("all", np.ones(n, bool)), ("wide", wide)):
        ok = np.array([j for j, m in enumerate(ms) if m is not None and mask[j]])
        if not len(ok):
            continue
        don, ron = L[ok, 1] == 1, L[ok, 0] == 1
        hit = np.array([L[j, 1] == 1 and ms[j]["delay_ms"] is not None and ms[j]["delay_confidence"] >= FLOOR
                        and abs(ms[j]["delay_ms"] - 2 ** Yk[j, 3]) <= 0.10 * 2 ** Yk[j, 3] for j in ok])
        fired = np.array([ms[j]["delay_ms"] is not None and ms[j]["delay_confidence"] >= FLOOR for j in ok])
        rv = np.array([ms[j]["reverb_rule"] == "on" for j in ok])
        out.setdefault("measures_on_targets", {})[name] = {
            "n": len(ok), "delay_hit_within_10pct_of_ons": float(hit[don].mean()),
            "delay_fired_on_offs": float(fired[~don].mean()), "delay_fired_on_ons": float(fired[don].mean()),
            "reverb_rule_on_of_ons": float(rv[ron].mean()), "reverb_rule_on_of_offs": float(rv[~ron].mean())}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)[:8000])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("e0").set_defaults(fn=cmd_e0)
    sub.add_parser("e1a-data").set_defaults(fn=cmd_e1a_data)
    t = sub.add_parser("e1a-train")
    t.add_argument("--fold")
    t.add_argument("--arm", choices=list(ARMS))
    t.add_argument("--force", action="store_true")
    t.set_defaults(fn=cmd_e1a_train)
    sub.add_parser("e1a-score").set_defaults(fn=cmd_e1a_score)
    t = sub.add_parser("e1c-train")
    t.add_argument("--fold")
    t.add_argument("--arm", choices=list(ARMS))
    t.add_argument("--force", action="store_true")
    t.set_defaults(fn=cmd_e1c_train)
    sub.add_parser("e1c-score").set_defaults(fn=cmd_e1c_score)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
