"""The judges we have, on whole presets the ear ranked (`docs/judge-screen-plan.md`, S12; ledger `judge-screen`). CPU, zero renders.

    $TORCH_PY -m learn.judge_screen judge OUT.json     # every judge on every candidate of the 36 development cards, J0's control first
    $MAIN -m learn.judge_screen report OUT.json REP.json

The stored clips are each card's held half: the reference's [s0, s1) and each render's [s0 - lag, s1 - lag), in mono. Each render
goes back into zeros the length of the section at [s0, s1), so it lines up with the reference at lag 0, and the DI moves by the same
lag, so the judge's DI frames, pre-roll included, are the ones it saw. The reference is rebuilt from its source and held to the stored
clip where one is stored. J0 recomputed this way must match the stored J0 within CONTROL_TOL on every candidate, or the card is out.

Nothing is fitted: every judge runs as its code and frozen constants stand. Labels are out of the primary, since J0 chose them.
"""
from __future__ import annotations

import itertools
import json
import math
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

KEY = "judge-screen"
SR = 48000
CONTROL_TOL = 1e-3                                   # |ln| between recomputed and stored J0
REF_TOL = 1e-5                                       # the rebuilt reference against a stored float32 clip, relative to its peak
MAX_OUT = 3                                          # cards failing the control past this: nothing is read
JUDGES = ("v2", "v3", "J5", "tonal", "J-f6")
LABELS = ("label",)
SMALL = 0.06                                         # the J0 log ratio under which N12's ear was at chance between models


# --- pure functions (unit-tested) ------------------------------------------------------------------------------------

def placed(clip, s0, s1, n):
    """A render clip [s0 - lag, s1 - lag) back at [s0, s1) of n zeros: the render at lag 0."""
    import numpy as np

    y = np.zeros(n)
    y[s0:s1] = np.asarray(clip, np.float64)[: s1 - s0]
    return y


def shifted(di, lag):
    """The DI on the reference's timeline: out[t] = di[t - lag], zeros where that falls outside."""
    import numpy as np

    di = np.asarray(di, np.float64)
    out = np.zeros(len(di))
    lo, hi = max(0, lag), min(len(di), len(di) + lag)
    if hi > lo:
        out[lo:hi] = di[lo - lag:hi - lag]
    return out


def window_s(s0, s1):
    """[s0, s1) in seconds, so that int(x * SR) gives back the samples."""
    return (s0 + 0.5) / SR, (s1 + 0.5) / SR


def agreement(dx, dy, x_closer):
    """1 if the judge gives the lower distance to the one the ear put closer, a half on a tie, else 0."""
    if dx == dy:
        return 0.5
    return float((dx < dy) == x_closer)


def pairs_of(cards, judges, drop=LABELS):
    """Every pair of candidates on a card, `drop` left out: the ear's two orders, J0's gap and each judge's agreement.
    `heard` is a pair whose closeness ratings differ; `closer` is then by closeness, else by rank. A judge with a refusal on
    either side gives None for the pair."""
    out = []
    for card in cards:
        cs = [c for c in card["ear"] if c not in drop and c in card["d"]["J0"]]
        for x, y in itertools.combinations(cs, 2):
            ex, ey = card["ear"][x], card["ear"][y]
            heard = ex.get("close") is not None and ey.get("close") is not None and ex["close"] != ey["close"]
            by_close = heard and ex["close"] > ey["close"]
            by_rank = ex["rank"] < ey["rank"]
            j0x, j0y = card["d"]["J0"][x], card["d"]["J0"][y]
            row = {"page": card["page"], "id": card["id"], "cluster": card["cluster"], "a": x, "b": y, "heard": heard,
                   "models": not ({x, y} & {"S", "placebo", *LABELS}), "lnr": abs(math.log(j0y / j0x)), "agree": {}}
            for j in ("J0", *judges):
                dx, dy = card["d"][j].get(x), card["d"][j].get(y)
                ok = dx is not None and dy is not None and math.isfinite(dx) and math.isfinite(dy)
                row["agree"][j] = {"close": agreement(dx, dy, by_close) if ok and heard else None,
                                   "rank": agreement(dx, dy, by_rank) if ok else None,
                                   "order": (dx < dy) if ok else None}
            out.append(row)
    return out


def jackknife(rows, value, t90):
    """The pair-pooled mean of value(row) over rows where it is not None, with a delete-one-cluster jackknife t interval
    (df clusters less one) and a two-sided p from the t distribution."""
    from scipy import stats

    pts = [(r["cluster"], v) for r in rows if (v := value(r)) is not None]
    if not pts:
        return None
    mean = sum(v for _, v in pts) / len(pts)
    cl = sorted({c for c, _ in pts})
    g = len(cl)
    out = {"mean": mean, "pairs": len(pts), "clusters": g}
    if g < 2:
        return out
    thetas = []
    for c in cl:
        rest = [v for k, v in pts if k != c]
        thetas.append(sum(rest) / len(rest))
    tb = sum(thetas) / g
    se = math.sqrt((g - 1) / g * sum((t - tb) ** 2 for t in thetas))
    df = g - 1
    out |= {"se": se, "df": df, "lo": mean - t90(df) * se, "hi": mean + t90(df) * se,
            "p": float(2 * stats.t.sf(abs(mean) / se, df)) if se > 0 else (1.0 if mean == 0 else 0.0)}
    return out


def contrast(rows, j, kind):
    """Per pair, judge j's agreement less J0's, on pairs where both read."""
    def value(r):
        a, b = r["agree"][j][kind], r["agree"]["J0"][kind]
        return None if a is None or b is None else a - b
    return value


def holm(ps):
    """{name: p} -> {name: Holm-adjusted p}."""
    order = sorted(ps, key=lambda k: ps[k])
    out, run = {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * ps[k]))
        out[k] = run
    return out


def card_rho(card, j, drop=LABELS):
    """Spearman of the ear's rank and judge j's distance on one card, `drop` left out; None under three candidates or a refusal."""
    from learn import score_ear as SE

    cs = [c for c in card["ear"] if c not in drop and c in card["d"]["J0"]]
    vals = [card["d"][j].get(c) for c in cs]
    if len(cs) < 3 or any(v is None or not math.isfinite(v) for v in vals):
        return None
    return SE.spearman([card["ear"][c]["rank"] for c in cs], vals)


def named(rows):
    """The judge the plan names for H4's page: the highest primary mean above zero, or None."""
    best = max(((j, r["mean"]) for j, r in rows.items() if r and r["mean"] > 0), key=lambda q: q[1], default=None)
    return best[0] if best else None


# --- the cards and their audio ---------------------------------------------------------------------------------------

def cards():
    """The 36 development cards: score_ear's own loaders, each joined to its clip folder, window, lag, held half and source."""
    from learn import bakeoff_render as BR
    from learn import capture_labels as CL
    from learn import ear_eat as EE
    from learn import pipeline_fix as P
    from learn import score_ear as SE

    pf = P.out_dir()
    out = []
    f57 = {it["unit"]: it for it in json.loads((pf / "captures" / "ear-check" / "key.json").read_text())["items"] if it["repeat_of"] is None}
    by = {u["unit"]: u for u in CL.units_of()}
    for c in SE.capture_cards():
        it = f57[c["id"]]
        out.append({**c, "dir": pf / "captures" / "ear-check" / "renders" / c["id"].replace("/", "__"), "held": it["held"],
                    "src": by[c["id"]], "ref_stored": False})
    keys = {"p1": {it["id"]: it for it in json.loads((pf / "eat" / "ear" / "key.json").read_text())["items"]},
            "p2": {it["id"]: it for it in json.loads((pf / "eat" / "ear2" / "key.json").read_text())["items"]}}
    parts = {(w, q["unit"]): q for w, q in BR.read_units()}
    for c in SE.eat_cards():
        page, i = c["id"].split(":")
        it = keys[page][i]
        d = pf / "eat" / ("ear" if page == "p1" else "ear2") / "renders" / it["slug"]
        if not d.exists():
            d = pf / "eat" / "ear" / "renders" / it["slug"]
        out.append({**c, "dir": d, "held": it["held"], "src": parts[(it["which"], it["unit"])], "ref_stored": True})
    key = json.loads((SE.wide_dir() / "key.json").read_text())
    wide = {it["id"]: it for it in key["items"]}
    units = {u["unit"]: u for u in SE.wide_units()[0]}
    got = {}
    for b in key["builds"]:
        got |= json.loads((SE.wide_dir() / "heard" / f"{b}.json").read_text())["answers"]
    heard = {it["id"]: EE.unblind(it, got.get(it["id"]) or {}) for it in key["items"]}
    scope = {it["id"] for it in key["items"] if (got.get(it["id"]) or {}).get("scope")}
    for it in SE.filled(key["items"], heard, scope):
        rec = json.loads((SE.wide_dir() / "renders" / it["slug"] / "rec.json").read_text())
        out.append({"page": "N12", "id": it["id"], "cluster": it["cluster"], "cls": it["cls"], "amp": it["amp"], "ear": heard[it["id"]],
                    "j0": rec["judge"], "dir": SE.wide_dir() / "renders" / it["slug"], "held": wide[it["id"]]["held"],
                    "src": units[it["unit"]], "ref_stored": True})
    return out


def audio(card):
    """(reference, DI on the reference's timeline, {candidate: render at lag 0}, s0, s1) for one card."""
    import numpy as np

    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B

    rec = json.loads((card["dir"] / "rec.json").read_text())
    lag, (s0, s1) = int(rec["lag"]), rec["window"]
    src = card["src"]
    ref = np.asarray(P.real_amp_track(src["sd"], src["track"], src["start_s"]), np.float64)
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    di = np.asarray(B.measure(PS.section_audio(src["di_path"], src["start_s"])).astype(np.float32), np.float64)[trim[0]:trim[1]]
    z = np.load(card["dir"] / "clips.npz")
    if card["ref_stored"]:
        r = z["ref"].astype(np.float64)
        if len(r) != s1 - s0 or np.max(np.abs(r - ref[s0:s1])) > REF_TOL * np.max(np.abs(ref[s0:s1])):
            raise SystemExit(f"{card['page']} {card['id']}: the rebuilt reference is not the stored clip")
    n = len(ref)
    rens = {c: placed(z[c.replace("-", "_")], s0, s1, n) for c in card["ear"] if c.replace("-", "_") in z.files}
    return ref, shifted(di, lag), rens, s0, s1


def judge_all(ref, di, ren, s0, s1, deep):
    """{judge: distance} for one candidate on its card's held half; None where a judge refuses."""
    from analysis import aligned as A
    from learn import bakeoff_judge as BJ
    from learn import judge_v5 as J5
    from learn import pretrain_set as PS

    a, b = window_s(s0, s1)
    kw = dict(lag=0, render_latency=PS.LATENCY, start_s=a, end_s=b)
    out = {"J0": A.aligned_distance(ref, ren, di, **kw).distance,
           "v2": A.aligned_distance(ref, ren, di, bands="fixed", **kw).distance,
           "v3": A.aligned_distance(ref, ren, di, **A.JUDGE_V3, **kw).distance}
    w = J5.window(ref, ren, di, latency=PS.LATENCY, start_s=a, end_s=b)
    out["J5"] = J5.j5([w], deep["w_c"])
    out["tonal"] = BJ.terms_of(BJ.band_errors(ref, ren, di, PS.LATENCY, a, b))["tonal"]
    out["J-f6"] = deep["terms"](ref, ren, {"h": (a, b)})["h"]["J-f6"]
    return out


def cmd_control(out_path):
    """J0 alone, recomputed on every candidate and held to the stored J0: run and read before any other judge."""
    from analysis import aligned as A
    from learn import pretrain_set as PS

    res, failed = [], []
    for card in cards():
        ref, di, rens, s0, s1 = audio(card)
        a, b = window_s(s0, s1)
        d = {c: A.aligned_distance(ref, y, di, lag=0, render_latency=PS.LATENCY, start_s=a, end_s=b).distance for c, y in rens.items()}
        missing = sorted(set(card["ear"]) - set(rens))
        worst = max(abs(math.log(d[c] / card["j0"][c])) for c in rens)
        res.append({"page": card["page"], "id": card["id"], "control": worst, "missing": missing})
        if worst > CONTROL_TOL or missing:
            failed.append(card["id"])
        print(f"{card['page']} {card['id']}: control {worst:.2e}{' missing ' + str(missing) if missing else ''}", flush=True)
    pathlib.Path(out_path).write_text(json.dumps({"key": KEY, "control_tol": CONTROL_TOL, "failed": failed, "cards": res}, indent=1))
    print(json.dumps({"cards": len(res), "failed": failed}), flush=True)


def cmd_judge(out_path):
    import torch

    from learn import eat_judge as EJ
    from learn import eat_net as EN
    from learn import eat_read as ER
    from learn import judge_v5 as J5

    torch.set_num_threads(4)
    _, w_c = J5.require_frozen()
    net = EN.load("mn10_as")
    bank = ER.Bank("mn10_as")
    sds = {s: bank.sd(s) for s in EJ.TERMS.values()}
    deep = {"w_c": w_c, "terms": lambda r, x, h: EJ.deep_terms(net, sds, r, x, h)}
    res, failed = [], []
    for card in cards():
        ref, di, rens, s0, s1 = audio(card)
        d = {c: judge_all(ref, di, y, s0, s1, deep) for c, y in rens.items()}
        worst = max(abs(math.log(d[c]["J0"] / card["j0"][c])) for c in rens)
        row = {k: card[k] for k in ("page", "id", "cluster", "cls", "amp", "ear")}
        row |= {"j0_stored": {c: card["j0"][c] for c in rens}, "control": worst, "window": [s0, s1],
                "d": {j: {c: d[c][j] for c in rens} for j in ("J0", *JUDGES)}}
        res.append(row)
        if worst > CONTROL_TOL:
            failed.append(card["id"])
        print(f"{card['page']} {card['id']}: control {worst:.2e}", flush=True)
    rep = {"key": KEY, "w_c": w_c, "control_tol": CONTROL_TOL, "failed": failed, "cards": res}
    pathlib.Path(out_path).write_text(json.dumps(rep, indent=1))
    print(json.dumps({"cards": len(res), "failed": failed}), flush=True)
    if len(failed) > MAX_OUT:
        raise SystemExit(f"{len(failed)} cards fail the control: nothing is read")


def cmd_report(in_path, out_path):
    from learn import pretrain_set as PS

    got = json.loads(pathlib.Path(in_path).read_text())
    if len(got["failed"]) > MAX_OUT:
        raise SystemExit("the control failed: nothing is read")
    cs = [c for c in got["cards"] if c["id"] not in got["failed"]]
    t90 = PS.t90
    rows = pairs_of(cs, JUDGES)
    with_labels = pairs_of(cs, JUDGES, drop=())
    heard = [r for r in rows if r["heard"]]
    rep = {"cards": len(cs), "out": got["failed"], "clusters": len({c["cluster"] for c in cs}), "pairs": len(rows), "heard": len(heard),
           "j0_heard": jackknife(heard, lambda r: r["agree"]["J0"]["close"], t90),
           "j0_rank": jackknife(rows, lambda r: r["agree"]["J0"]["rank"], t90)}
    primary = {j: jackknife(heard, contrast(heard, j, "close"), t90) for j in JUDGES}
    adj = holm({j: v["p"] for j, v in primary.items()})
    for j, v in primary.items():
        v["holm"] = adj[j]
    rep["primary"] = primary
    rep["rank"] = {j: jackknife(rows, contrast(rows, j, "rank"), t90) for j in JUDGES}
    rho = {j: [(c["cluster"], card_rho(c, j)) for c in cs] for j in ("J0", *JUDGES)}

    def rho_row(j):
        pts = [{"cluster": k, "v": v - w} for (k, v), (_, w) in zip(rho[j], rho["J0"]) if v is not None and w is not None]
        return jackknife(pts, lambda r: r["v"], t90)
    rep["order"] = {j: rho_row(j) for j in JUDGES}
    lh = [r for r in with_labels if r["heard"]]
    rep["labels_in"] = {j: {"heard": jackknife(lh, contrast(lh, j, "close"), t90), "rank": jackknife(with_labels, contrast(with_labels, j, "rank"), t90)}
                        for j in JUDGES}
    rep["by_page"] = {pg: {j: {"heard": jackknife(h := [r for r in heard if r["page"] == pg], contrast(h, j, "close"), t90),
                               "rank": jackknife(a := [r for r in rows if r["page"] == pg], contrast(a, j, "rank"), t90)} for j in JUDGES}
                      for pg in ("F57", "ear-eat", "N12")}
    move = {}
    for j in JUDGES:
        dif = [r for r in rows if r["agree"][j]["order"] is not None and r["agree"][j]["order"] != r["agree"]["J0"]["order"]]
        hd = [r for r in dif if r["heard"]]
        move[j] = {"differs": len(dif), "heard": len(hd), "heard_its_way": sum(r["agree"][j]["close"] == 1 for r in hd),
                   "refused": sum(r["agree"][j]["rank"] is None for r in rows)}
        for name, sub in (("small", [r for r in heard if r["lnr"] < SMALL]), ("models", [r for r in heard if r["models"]])):
            ok = [r for r in sub if r["agree"][j]["close"] is not None]
            move[j][name] = {"pairs": len(ok), "agree": sum(r["agree"][j]["close"] for r in ok), "j0": sum(r["agree"]["J0"]["close"] for r in ok)}
    rep["move"] = move
    rep["named"] = named(primary)
    pathlib.Path(out_path).write_text(json.dumps(rep, indent=1))
    print(json.dumps({"primary": primary, "named": rep["named"], "move": move}, indent=1))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["control"] and len(argv) == 2:
        return cmd_control(argv[1])
    if argv[:1] == ["judge"] and len(argv) == 2:
        return cmd_judge(argv[1])
    if argv[:1] == ["report"] and len(argv) == 3:
        return cmd_report(argv[1], argv[2])
    raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
