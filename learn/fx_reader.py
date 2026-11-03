"""The effects route (ledger `phase_fx_reader`, docs/pipeline-fix-plan.md "The effects route").

E0 (zero renders, exploratory): do the product's own blind measures (`analysis.features.time_effects`, through
`analysis.fingerprint` as match runs it on a separated stem) read reverb and delay through the separators? Data: the
judge-v5 separator check's stems (2 presets x 3 backings x 2 ratios x 7 renders, per separator), the renders without
backing as the ceiling and S2 as a second dry case.

    PYTHONPATH=. .venv/bin/python -m learn.fx_reader e0
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("e0").set_defaults(fn=cmd_e0)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
