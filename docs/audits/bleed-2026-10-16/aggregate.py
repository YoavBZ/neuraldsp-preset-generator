import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
KC = set(json.load(open(HERE / "kc_parts.json")))


def db(x):
    return round(10 * math.log10(x), 1) if x > 1e-9 else -90.0


def flag(d):
    return "high" if d > -20 else ("moderate" if d >= -30 else "low")


def short(n):
    return pathlib.Path(n).stem.replace("-Norm_03-01", "").replace("-Norm_01-01", "").replace("-Norm_02-01", "")


def runs(t, ok):
    out, cur = [], None
    for ti, o in zip(t, ok):
        if o:
            cur = [ti, ti] if cur is None else [cur[0], ti]
        elif cur is not None:
            out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    # frame hop ~43 ms; pad half a window
    return [(round(a - 0.04, 2), round(b + 0.04, 2)) for a, b in out if b - a >= 0.08]


rows = {}
for f in sorted((HERE / "out4").glob("*.json")):
    r = json.load(open(f))
    if "error" in r:
        rows[r["slug"]] = {"error": r["error"]}
        continue
    row = {"set": "knob-ceiling" if r["slug"] in KC else "label-table-only", "source": r["source"],
           "di_lag_ms": round(r["di_lag_24k"] / 24, 2), "excluded_proxy_mics": [short(m) for m in r["excluded_proxy_mics"]],
           "amp_zero_where_di_silent_frac": r["amp_zero_where_di_silent_frac"],
           "amp_level_where_di_silent_db": None if r["amp_level_where_di_silent_db"] is None else round(r["amp_level_where_di_silent_db"], 1),
           "halves": {}}
    for h, v in r["halves"].items():
        if v.get("silent"):
            row["halves"][h] = {"silent": True, "bleed_db": -99, "flag": "silent"}
            continue
        c, fu = v["clean"], v["full"]
        nc = max(c["gain_null_mean"], 0.0)
        bfrac = c["gain"] - nc
        ffrac = fu["gain"] - max(fu["gain_null_mean"], 0.0)
        bd = db(bfrac)
        hd = {
            "guitar_share_linear": v["guitar_share_linear"],
            "guitar_share_nl": v["guitar_share_nl"],
            "bleed_db": bd,
            "bleed_frac": round(bfrac, 5),
            "bleed_db_penalty_corrected": db(c["gain"] - c["gain_null_mean"]) if -0.005 <= c["gain_null_mean"] <= 0 else None,
            "bleed_full_db": db(ffrac),
            "null_gain_mean": c["gain_null_mean"],
            "unexplained_frac": c["unexplained_frac"],
            "unexplained_db": c["unexplained_db"],
            "top": [(short(n), d, (r["lags_24k"].get(n) or [None])[0]) for n, _, d in c["top"]],
            "flag": flag(bd),
        }
        notes = []
        if v["guitar_share_nl"] < 0.8:
            notes.append("weak DI model: residual is mostly unexplained, not bleed")
        if hd["bleed_full_db"] > -20 and hd["bleed_full_db"] - bd > 6:
            notes.append("ambient/proxy mics explain more (full set); could be bleed or the guitar's own room sound")
        if c["gain"] < -0.01:
            notes.append("bleed model generalises badly in this half (negative held-out gain)")
        hd["notes"] = notes
        t = c.get("frames_t", [])
        if t:
            br, gr = c["frames_bleed_rel_db"], c["frames_gain_rel_db"]
            ok = [b >= -10 and g >= -13 for b, g in zip(br, gr)]
            hd["clear_bleed_spans_s"] = runs(t, ok)
        row["halves"][h] = hd
    worst = max(row["halves"].values(), key=lambda x: x["bleed_db"])
    row["flag"] = worst["flag"]
    row["flagged_halves"] = [h for h, x in row["halves"].items() if x["flag"] in ("moderate", "high")]
    rows[r["slug"]] = row

json.dump(rows, open(HERE / "bleed-table.json", "w"), indent=1)

# print table
print(f"{'part':52s} {'set':3s} {'A bleed':>7s} {'B bleed':>7s} {'A gtr':>5s} {'B gtr':>5s} {'A unex':>6s} {'B unex':>6s} {'flag':8s} top (A | B)")
for s, row in sorted(rows.items(), key=lambda kv: (kv[1].get("set", ""), kv[0])):
    if "error" in row:
        print(s, "ERROR", row["error"])
        continue
    A, B = row["halves"]["A"], row["halves"]["B"]
    g = lambda x, k, f: (format(x[k], f) if k in x else "silent")
    tops = " | ".join(", ".join(f"{n}({d:.0f})" for n, d, _ in x.get("top", [])) for x in (A, B))
    print(f"{s[:52]:52s} {'kc' if row['set']=='knob-ceiling' else 'lt':3s} {g(A,'bleed_db','7.1f'):>7s} {g(B,'bleed_db','7.1f'):>7s} {g(A,'guitar_share_nl','5.2f'):>5s} {g(B,'guitar_share_nl','5.2f'):>5s} "
          f"{g(A,'unexplained_db','6.1f'):>6s} {g(B,'unexplained_db','6.1f'):>6s} {row['flag']:8s} {tops[:110]}")
