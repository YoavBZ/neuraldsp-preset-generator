"""Zero-render check (a): does arm A's best shrink depend on the stem's quality?

    .venv/bin/python -m learn.shrink_vs_snr          # reads stored records only, writes the report

Stored records score each direction at three points of the shrink: the unshrunk best (kept
fraction f = 1), the recipe's halfway shrink (f = 0.5) and S (f = 0). Stage D's experiment-1
records (the 150-render search A, htdemucs instrumental stems) add f = 0.25 and 0.75. No other
shrink is scored anywhere, and a new one needs renders, so a rule can only choose among these.

The rule: f_lo below an SNR threshold t, f_hi at or above it (t = -inf is a constant f). It is
fitted on all other bands and applied to the held-out band (leave one band out, bands pooled
across stages). Its gain is log(d_rule / d_recipe) on held-out bands, averaged per (stage, arm,
part), band-weighted, with a 90% band-clustered t interval (`song_readout.bw_stats`).
"""

from __future__ import annotations

import itertools
import json
import math
import pathlib
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn" / "shrink-vs-snr"
PERFECT = math.inf
RECIPE = 0.5


# --- pure parts --------------------------------------------------------------------------------

def rule_f(rule, snr):
    t, lo, hi = rule
    return hi if snr >= t else lo


def thresholds(snrs):
    """Candidate thresholds: -inf (a constant), the midpoints between distinct SNRs, and inf
    (perfect stems alone above)."""
    xs = sorted(set(snrs))
    mids = [(a + b) / 2 if math.isfinite(b) else 1e9 for a, b in zip(xs, xs[1:])]
    return [-math.inf, *mids]


def band_mean(units, value):
    """Band-weighted mean of value(unit), averaged per (stage, arm, part) first."""
    by = {}
    for u in units:
        by.setdefault(u["band"], {}).setdefault((u["stage"], u["arm"], u["slug"]), []).append(value(u))
    return statistics.fmean(statistics.fmean(statistics.fmean(v) for v in parts.values()) for parts in by.values())


def logr(u, f, ref=RECIPE):
    return math.log(u["d"][f] / u["d"][ref])


def fit(units, levels, constant=False):
    """The rule minimising the band-weighted mean log distance against the recipe (ties: the
    first in a fixed order, which puts the recipe's constant first)."""
    ts = [-math.inf] if constant else thresholds(u["snr"] for u in units)
    best, best_v = None, None
    order = [RECIPE] + [x for x in levels if x != RECIPE]
    for t in ts:
        for lo, hi in itertools.product(order, order):
            if t == -math.inf and lo != hi:
                continue
            v = band_mean(units, lambda u: logr(u, rule_f((t, lo, hi), u["snr"])))
            if best_v is None or v < best_v - 1e-12:
                best, best_v = (t, lo, hi), v
    return best, best_v


def cross_validate(units, levels, constant=False):
    """Leave one band out: fit on the rest, score the held band. -> (per-unit gains, rules)."""
    gains, rules = [], {}
    for b in sorted({u["band"] for u in units}):
        train = [u for u in units if u["band"] != b]
        rule, _ = fit(train, levels, constant)
        rules[b] = rule
        for u in units:
            if u["band"] == b:
                gains.append({**{k: u[k] for k in ("stage", "arm", "slug", "band", "cls")},
                              "f": rule_f(rule, u["snr"]), "g": logr(u, rule_f(rule, u["snr"]))})
    return gains, rules


def summarise(gains, key="g"):
    from learn import song_readout as R

    by = {}
    for g in gains:
        by.setdefault((g["stage"], g["arm"], g["slug"], g["band"]), []).append(g[key])
    return R.bw_stats([(b, statistics.fmean(v)) for (_, _, _, b), v in sorted(by.items())])


def spearman(x, y):
    from scipy import stats

    r = stats.spearmanr(x, y)
    return float(r.statistic), float(r.pvalue)


# --- data (no renders) -------------------------------------------------------------------------

def snr_tables():
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR
    from learn import local_objective as LO

    rf = json.loads((A.OUT / "report-F.json").read_text())
    rd = json.loads((A.OUT / "report-D.json").read_text())
    f_h = {s: v["snr_db_vs_reference"] for s, v in rf["separation"]["htdemucs"].items()}
    f_m = {s: v["snr_db_vs_reference"] for s, v in rf["separation"]["mega53"].items()}
    d_h = dict(rd["snr_db_htdemucs_instrumental"])
    d_m = {}
    for s in d_h:
        p = LO.sep_crop_path("mega53", s)
        ref = CR.mono(A.part_of("D", s)["crop"] / "reference.wav")
        d_m[s] = A.C.snr_db(np.load(p).astype(np.float64), ref) if p.exists() else None
    return {("F", "H"): f_h, ("F", "XO"): f_h, ("F", "M"): f_m, ("D", "H"): d_h, ("D", "M"): d_m}


def gather():
    """Units {stage, arm, slug, band, cls, amp, search, snr, d: {1, 0.5, 0}} from the stored records."""
    from learn import arm_a_mega53 as A
    from learn import perfect_sep_arm as PS

    snr = snr_tables()
    out = []
    f_units = PS.build_units()
    d_units = A.build_units("D", A.ARMS["D"])
    for stage, units, arms in (("F", f_units, ("H", "M", "XO", "YT", "ZT")), ("D", d_units, ("H", "M", "T"))):
        for u in units:
            for arm in arms:
                d = {1.0: u["d"].get(f"{arm}_unshrunk"), RECIPE: u["d"].get(arm), 0.0: u["d"].get("S")}
                if not all(x is not None and math.isfinite(x) and x > 0 for x in d.values()):
                    continue
                s = PERFECT if arm in ("YT", "ZT", "T") else snr[(stage, arm)].get(u["slug"])
                if s is None:
                    continue
                out.append({"stage": stage, "arm": arm, "slug": u["slug"], "band": u["band"], "cls": u["cls"],
                            "amp": u["amp"], "search": u["search"], "snr": s, "d": d})
    return out


def gather_exp1():
    """Stage D's experiment 1 (search A, 150 renders): f in {0, 0.25, 0.5, 0.75, 1}."""
    from learn import arm_a_levers as L

    snr = snr_tables()[("D", "H")]
    out = []
    units, _ = L.drop(L.gathered_units(), ("shrink-0.25", "shrink-0.5", "shrink-0.75"))
    for u in units:
        d = {1.0: u["d"].get("A"), 0.75: L._held_from(L.OUT / "exp1", u, "shrink-0.75"),
             0.5: L._held_from(L.OUT / "exp1", u, "shrink-0.5"), 0.25: L._held_from(L.OUT / "exp1", u, "shrink-0.25"),
             0.0: u["d"].get("S")}
        if all(x is not None and math.isfinite(x) and x > 0 for x in d.values()) and snr.get(u["slug"]) is not None:
            out.append({"stage": "D150", "arm": "A", "slug": u["slug"], "band": u["band"], "cls": u["cls"],
                        "amp": u["amp"], "search": u["search"], "snr": snr[u["slug"]], "d": d})
    return out


def fmt(s):
    return (f"{s['band_weighted_mean']:+.4f} [{s['lo90']:+.4f}, {s['hi90']:+.4f}] "
            f"({s['bands']} bands, {s['bands_negative']}-/{s['bands_positive']}+)")


def analyse(units, levels, name):
    rep = {"units": len(units), "bands": len({u["band"] for u in units})}
    rule, v = fit(units, levels)
    const, cv_ = fit(units, levels, constant=True)
    rep["in_sample"] = {"rule": rule, "gain": v, "best_constant": const, "best_constant_gain": cv_}
    g, rules = cross_validate(units, levels)
    gc, rules_c = cross_validate(units, levels, constant=True)
    rep["cv_rule_vs_recipe"] = summarise(g)
    rep["cv_constant_vs_recipe"] = summarise(gc)
    paired = [{**a, "g": a["g"] - b["g"]} for a, b in zip(g, gc)]
    rep["cv_rule_vs_constant"] = summarise(paired)
    rep["rules_per_fold"] = {b: list(r) for b, r in rules.items()}
    rep["constants_per_fold"] = {b: r[1] for b, r in rules_c.items()}
    per_arm = {}
    for key in sorted({(u["stage"], u["arm"]) for u in units}):
        sel = [x for x in g if (x["stage"], x["arm"]) == key]
        per_arm["/".join(key)] = summarise(sel) if len({x["band"] for x in sel}) > 1 else None
    rep["cv_rule_vs_recipe_per_arm"] = per_arm
    # descriptive: each fixed level against the recipe, per arm
    fixed = {}
    for key in sorted({(u["stage"], u["arm"]) for u in units}):
        sel = [u for u in units if (u["stage"], u["arm"]) == key]
        fixed["/".join(key)] = {
            "median_snr": statistics.median(u["snr"] for u in sel) if all(math.isfinite(u["snr"]) for u in sel) else "perfect",
            **{str(f): summarise([{**u, "g": logr(u, f)} for u in sel]) for f in levels if f != RECIPE}}
    rep["fixed_levels_vs_recipe"] = fixed
    print(f"\n== {name}: {len(units)} units, {rep['bands']} bands")
    print("  in-sample rule", rule, f"{v:+.4f}", "best constant", const[1], f"{cv_:+.4f}")
    print("  CV rule − recipe     ", fmt(rep["cv_rule_vs_recipe"]))
    print("  CV constant − recipe ", fmt(rep["cv_constant_vs_recipe"]))
    print("  CV rule − constant   ", fmt(rep["cv_rule_vs_constant"]))
    print("  folds' rules:", sorted({tuple(r) for r in rules.values()}, key=str))
    for k, s in per_arm.items():
        print("   ", k, fmt(s) if s else "-")
    for k, s in fixed.items():
        print("    fixed", k, s["median_snr"] if s["median_snr"] == "perfect" else round(s["median_snr"], 2),
              {f: round(x["band_weighted_mean"], 4) for f, x in s.items() if f != "median_snr"})
    return rep


def main():
    units = gather()
    realistic = [u for u in units if math.isfinite(u["snr"]) and u["arm"] != "XO"]
    rep = {"levels": [0.0, 0.5, 1.0]}
    rep["main"] = analyse([u for u in units if u["arm"] != "XO"], (0.0, 0.5, 1.0),
                          "main: F H, M, YT, ZT + D H, M, T")
    rep["with_xo"] = analyse(units, (0.0, 0.5, 1.0), "sensitivity: + F XO")
    rep["realistic_only"] = analyse(realistic, (0.0, 0.5, 1.0), "realistic stems only (F H, M; D H, M)")
    e1 = gather_exp1()
    rep["exp1_five_levels"] = analyse(e1, (0.0, 0.25, 0.5, 0.75, 1.0), "stage D exp 1, 5 levels")
    # post hoc: per (stage, arm, part) unshrunk − recipe against SNR, realistic stems
    by = {}
    for u in realistic:
        by.setdefault((u["stage"], u["arm"], u["slug"]), {"snr": u["snr"], "v": []})["v"].append(logr(u, 1.0))
    xs = [v["snr"] for v in by.values()]
    ys = [statistics.fmean(v["v"]) for v in by.values()]
    rep["spearman_unshrunk_minus_recipe_vs_snr"] = dict(zip(("rho", "p", "n"), (*spearman(xs, ys), len(xs))))
    print("\nSpearman (part: unshrunk − recipe vs SNR, realistic):", rep["spearman_unshrunk_minus_recipe_vs_snr"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(rep, indent=1, default=lambda x: None if x != x else str(x)))
    print("written", OUT / "report.json")


if __name__ == "__main__":
    main()
