"""D1, the delay reader's operating rule (`docs/full-controls-plan.md`, "D1 in detail"; ledger `pipeline-fix` `phase_d1`):
zero renders, zero separations. F88 found delay is the first effect whose on/off and time read from the separated stem
at the product's exposure, but a half vote switches it on too often and the direct time reader is all or nothing. D1
sets the reader's rule on known truth, leaving each band out, and reads it on that band:

- **on/off:** T0x's neighbour on-share against a threshold, chosen on the other bands as the lowest of THRESHOLDS whose
  false-on rate on their delay-offs is at most MAX_FALSE_ON;
- **time, when on:** the stem's own cepstral peak if its halves agree within 10%, else the neighbours' median time;
- **the rest:** at the draw-aware prior (delay mix and feedback, F88).

    .venv/bin/python -m learn.fx_d1 d1-read
"""

from __future__ import annotations

import argparse
import json
import time

PHASE = "phase_d1"
THRESHOLDS = tuple(round(0.5 + 0.05 * j, 2) for j in range(10))      # 0.50 .. 0.95
MAX_FALSE_ON = 0.10


def choose_threshold(scores, is_on, thresholds=THRESHOLDS, max_false_on=MAX_FALSE_ON):
    """The lowest threshold whose false-on rate (score >= t among the offs) is at most max_false_on; the highest if
    none is. scores, is_on: arrays over the training items."""
    import numpy as np

    offs = ~np.asarray(is_on, bool)
    for t in thresholds:
        if np.mean(np.asarray(scores)[offs] >= t) <= max_false_on:
            return t
    return thresholds[-1]


def time_pick(halves_ms, whole_ms, knn_ms):
    """The stem's own peak if its halves agree within 10%, else the neighbours' median time."""
    a, b = halves_ms
    return whole_ms if abs(a / b - 1) <= 0.10 else knn_ms


def cmd_read(_args):
    import numpy as np

    from learn import fx_t0 as T0
    from learn import fx_t0x as T0X
    from learn import pipeline_fix as P

    P.require(PHASE)
    its, _ = T0.items()
    z = np.load(T0.out_dir() / "features.npz")
    recs = [json.loads((T0X.out_dir() / "items" / f"{it['i']:07d}.json").read_text()) for it in its]
    X = np.array([r["stem"] for r in recs])
    L = [T0.labels(it["settings"]) for it in its]
    Y = {c: np.array([l_[c] for l_ in L]) for c in L[0]}
    bands = np.array([it["band"] for it in its])
    amps = np.array([it["amp"] for it in its])
    pred, prior = T0.predict("delay", z["target"], X, Y, bands, amps, T0.OWN["delay"])
    s = pred["don"]
    don = Y["don"] == 1
    hi = np.nanpercentile(Y["dmix"][don], 200 / 3)
    strong = don & (Y["dmix"] >= hi)
    sub_votes = {}
    for b in sorted(set(bands)):                         # the training votes with the held-out band out of the library too
        tr = bands != b
        ps, _ = T0.predict("delay", z["target"][tr], X[tr], {c: v[tr] for c, v in Y.items()}, bands[tr], amps[tr],
                           T0.OWN["delay"])
        sub_votes[b] = ps["don"]

    def operate(max_false_on):
        on_p, ch = np.zeros(len(its), bool), {}
        for b in sorted(set(bands)):
            tr, te = bands != b, bands == b
            t = choose_threshold(sub_votes[b], don[tr], max_false_on=max_false_on)
            ch[b] = t
            on_p[te] = s[te] >= t
        return on_p, ch
    on_pred, chosen = operate(MAX_FALSE_ON)
    curve = {}
    for f in (0.05, 0.10, 0.20):
        op, _ = operate(f)
        curve[f"target {int(f * 100)}% false-on"] = {"false-on": float(np.mean(op[~don])), "on (all ons)": float(np.mean(op[don])),
                                                    "on (audible)": float(np.mean(op[strong]))}
    t_ms = 2 ** Y["dtime"]
    pick = np.array([time_pick(r["stem_cep_peak_halves_ms"], r["stem_cep_peak_ms"], 2 ** pred["dtime"][j])
                     for j, r in enumerate(recs)])
    beside = {"always the peak": np.array([r["stem_cep_peak_ms"] for r in recs]), "always the neighbours": 2 ** pred["dtime"]}
    prior_ms = 2 ** prior["dtime"]

    def rate(m, sel):
        return float(np.mean(m[sel])) if sel.any() else None
    rep = {"phase": PHASE, "n": len(its), "thresholds chosen (leaving each band out)": chosen,
           "on/off": {"false-on (delay-offs)": rate(on_pred, ~don), "on (all delay-ons)": rate(on_pred, don),
                      "on (audible: the strong third)": rate(on_pred, strong),
                      "false-on (every effect off)": rate(on_pred, (Y["ron"] == 0) & (Y["don"] == 0) & (Y["ton"] == 0))},
           "operating curve (leaving each band out)": curve,
           "time, on the delay-ons it switches on": {},
           "the time read is in-sample for its gate": "the halves gate was noticed on these same 770 (F88); the real-song test is its out-of-sample check"}
    for nm, m in (("all", don & on_pred), ("audible", strong & on_pred)):
        hit = np.abs(pick / t_ms - 1) <= 0.10
        le, lp = np.abs(np.log2(pick) - Y["dtime"]), np.abs(np.log2(prior_ms) - Y["dtime"])
        rep["time, on the delay-ons it switches on"][nm] = {
            "n": int(m.sum()), "within_10pct": rate(hit, m), "within_10pct_prior": rate(np.abs(prior_ms / t_ms - 1) <= 0.10, m),
            "log2 error - prior": T0._stats(lambda x, le=le, lp=lp, m=m: float(np.mean(le[x][m[x]]) - np.mean(lp[x][m[x]]))
                                            if m[x].any() else float("nan"), bands),
            **{f"{k}: within_10pct": rate(np.abs(v / t_ms - 1) <= 0.10, m) for k, v in beside.items()}}
    rep["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(T0X.out_dir().parent / "d1" / "read.json", rep)
    print(json.dumps(rep, indent=1, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("d1-read").set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
