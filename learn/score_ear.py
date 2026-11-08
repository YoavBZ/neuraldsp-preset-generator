"""N11 and N12: the score against the ear, on more songs (`docs/score-ear-plan.md`; ledger `phase_n11`, `phase_n12`).

    $MAIN -m learn.score_ear stored OUT.json                        # N11, every stored blind page, zero renders
    $MAIN -m learn.score_ear draw                                   # N12's cards, seeded, on metadata alone, once
    $TORCH_PY -m learn.score_ear answers                            # FTm per search half, after a control on stored answers
    $MAIN -m learn.score_ear render --shard k/n                     # every reader on every unit, the cards' clips kept
    $MAIN -m learn.score_ear page                                   # -> listening/ear-wide-1 and -2, and two artifact pages
    $MAIN -m learn.score_ear wide OUT.json --answers FILE1 FILE2    # N12's rows

Nothing here changes J0 or picks a model. A card is one part of one page: its ear ranks and closeness, and J0's held-half distance
per candidate. V-real's and `record-match-1`'s rows inform the report and never brief a judge term.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import math
import pathlib
import random
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

PHASE = "phase_n11"
SEED = 20261301
BOOT = 4000
READERS = ("L0", "N4", "F57", "ear-eat")             # the pooled pages; `record-match-1` stands beside
LABELS = ("label", "C")                              # J0 chose these: rows without them read the order J0 did not set
ENDS = ("S", *LABELS)

WIDE = "phase_n12"
WIDE_DIR, LISTENING = "ear-wide", "ear-wide"
CANDS = ("S", "FTm", "M-pcs", "EW-mix", "label")
READ = ("FTm", "M-pcs", "EW-mix")                    # answers on every unit; S and the label stand in their search record
DRAW_SEED, PAGE_SEED = 20261302, 20261303
CARDS = 14
OUT_LIMIT = 3                                        # cards unfilled past this: reported, nothing concluded
PAGE_ITEMS = 9                                       # items a page, since 18 at `ear-eat`'s clip size pass the artifact's 16 MB
# The fill, fixed by `docs/score-ear-plan.md` before any answer: (band, class, cards, DI file stem or None for any).
SLOTS = (("Ale Lak", "crunch", 2, None), ("Dark Ride", "crunch", 2, None), ("Renesans", "crunch", 1, None),
         ("Rebuild The Evil", "crunch", 1, "21_ElecGtr3DI"), ("Rebuild The Evil", "clean", 1, "23_ElecGtr4DI"),
         ("Storm Of Particles", "clean", 2, None), ("Cnoc An Tursa", "clean", 2, None), ("Death Of A Romantic", "clean", 1, None),
         ("The Long Wait", "clean", 1, None), ("The Travelling Band", "clean", 1, None))
SPARE_BANDS = ("Ale Lak", "Dark Ride")               # the third crunch DI of each, in this order


# --- pure functions (unit-tested) ------------------------------------------------------------------------------------

def ranks(xs):
    """Average ranks, 1 up, ties sharing their mean."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for q in range(i, j + 1):
            out[order[q]] = (i + j) / 2 + 1
        i = j + 1
    return out


def spearman(a, b):
    """Spearman with ties; None if either side holds one value."""
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    da, db = sum((x - ma) ** 2 for x in ra), sum((y - mb) ** 2 for y in rb)
    if not da or not db:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / math.sqrt(da * db)


def cands_of(card, drop=()):
    return [c for c in card["ear"] if c in card["j0"] and c not in drop]


def j0_rho(card, drop=()):
    """The card's order of ear and J0, on its candidates less `drop`; None under 3 candidates, where a rho is only ±1."""
    cs = cands_of(card, drop)
    return None if len(cs) < 3 else spearman([card["ear"][c]["rank"] for c in cs], [card["j0"][c] for c in cs])


def s_last_rho(card, drop=()):
    """The order that needs no score: S last, the rest tied. None with no S or under 3 candidates."""
    cs = cands_of(card, drop)
    if "S" not in cs or len(cs) < 3:
        return None
    return spearman([card["ear"][c]["rank"] for c in cs], [float(c == "S") for c in cs])


def reranked(card, cs):
    """{candidate: rank among `cs` alone}, a dropped candidate's place taken back."""
    return dict(zip(cs, ranks([card["ear"][c]["rank"] for c in cs])))


def mean_rank_rho(card, others, drop=()):
    """The order of each candidate's mean rank over `others`: a fixed order of candidates, ranks taken again among those kept."""
    cs = cands_of(card, drop)
    if len(cs) < 3:
        return None
    usable = [reranked(o, cs) for o in others if all(c in o["ear"] for c in cs)]
    if not usable:
        return None
    return spearman([card["ear"][c]["rank"] for c in cs], [sum(u[c] for u in usable) / len(usable) for c in cs])


def others_of(card, cards):
    """The fixed order's cards: the same page, the card's whole cluster left out so a sibling lends it no order."""
    return [o for o in cards if o["page"] == card["page"] and o["cluster"] != card["cluster"]]


def per_card(cards, drop=()):
    """[{cluster, page, j0, s_last, mean_rank}], each card once; a value is None where it has no order to read."""
    out = []
    for card in cards:
        out.append({"cluster": card["cluster"], "page": card["page"], "id": card["id"], "j0": j0_rho(card, drop),
                    "s_last": s_last_rho(card, drop), "mean_rank": mean_rank_rho(card, others_of(card, cards), drop)})
    return out


def interval(pairs, t90, seed=SEED, boot=BOOT):
    """The mean of (cluster, value) with its delete-one-cluster 90% t interval, and the percentile by cluster beside."""
    pairs = [(c, v) for c, v in pairs if v is not None]
    if not pairs:
        return None
    by = {}
    for c, v in pairs:
        by.setdefault(c, []).append(v)
    names = sorted(by)

    def mean(items):
        return sum(items) / len(items)

    point = mean([v for _, v in pairs])
    out = {"mean": point, "cards": len(pairs), "clusters": len(names)}
    if len(names) < 3:
        return out
    th = [mean([v for c, v in pairs if c != drop]) for drop in names]
    n = len(th)
    mt = sum(th) / n
    se = math.sqrt((n - 1) / n * sum((x - mt) ** 2 for x in th))
    h = t90(n - 1) * se
    rng = random.Random(seed)
    draws = sorted(mean([v for k in rng.choices(names, k=n) for v in by[k]]) for _ in range(boot))
    return {**out, "se": se, "df": n - 1, "lo": point - h, "hi": point + h, "pct_lo": draws[int(0.05 * boot)], "pct_hi": draws[int(0.95 * boot)]}


def added(cards, drop=()):
    """What J0 adds: the mean over cards of J0's rho less the fixed order's, on these cards alone."""
    v = [r["j0"] - r["mean_rank"] for r in per_card(cards, drop) if r["j0"] is not None and r["mean_rank"] is not None]
    return sum(v) / len(v) if v else None


def added_row(cards, t90, drop=()):
    """`added` with a delete-one-cluster t interval, the fixed order recomputed at every deletion, since jackknifing fixed card
    differences understates. A deletion that leaves no value is not a survivor, and df is the survivors less one."""
    point = added(cards, drop)
    if point is None:
        return None
    th = []
    for name in sorted({r["cluster"] for r in per_card(cards, drop) if r["j0"] is not None and r["mean_rank"] is not None}):
        v = added([c for c in cards if c["cluster"] != name], drop)
        if v is not None:
            th.append(v)
    n = len(th)
    if n < 3:
        return {"mean": point, "clusters": n}
    mt = sum(th) / n
    se = math.sqrt((n - 1) / n * sum((x - mt) ** 2 for x in th))
    h = t90(n - 1) * se
    return {"mean": point, "clusters": n, "se": se, "df": n - 1, "lo": point - h, "hi": point + h}


def welch(a, b, t90):
    """a − b for two independent `interval` rows, the SE from their jackknifes, Welch's df."""
    if not a or not b or "se" not in a or "se" not in b:
        return None
    va, vb = a["se"] ** 2, b["se"] ** 2
    if not va + vb:
        return None
    df = (va + vb) ** 2 / (va ** 2 / a["df"] + vb ** 2 / b["df"])
    h = t90(max(int(df), 1)) * math.sqrt(va + vb)
    d = a["mean"] - b["mean"]
    return {"diff": d, "lo": d - h, "hi": d + h, "df": df}


def side_of_s(cards):
    """{model: {same, of}} over cards: does J0 put it on the ear's side of S? A tie in either counts as not the same."""
    out = {}
    for card in cards:
        if "S" not in card["j0"] or "S" not in card["ear"]:
            continue
        for c in cands_of(card, ("S",)):
            ear = card["ear"][c]["rank"] - card["ear"]["S"]["rank"]
            j = card["j0"][c] - card["j0"]["S"]
            q = out.setdefault(c, {"same": 0, "of": 0})
            q["of"] += 1
            q["same"] += int(ear * j > 0)
    return out


def pairs_of(cards, drop=ENDS):
    """Every pair on a card, S and labels left out by default: J0's gap, and whether J0 and the ear agree. Sorted by J0's gap, largest
    first. `lnr` is ln(d_b/d_a) > 0 with a the one J0 prefers."""
    out = []
    for card in cards:
        cs = cands_of(card, drop)
        for i, x in enumerate(cs):
            for y in cs[i + 1:]:
                a, b = (x, y) if card["j0"][x] <= card["j0"][y] else (y, x)
                row = {"page": card["page"], "id": card["id"], "cluster": card["cluster"], "cls": card.get("cls"), "amp": card.get("amp"),
                       "a": a, "b": b, "lnr": math.log(card["j0"][b] / card["j0"][a]), "agree": card["ear"][a]["rank"] < card["ear"][b]["rank"],
                       "close_a": card["ear"][a].get("close"), "close_b": card["ear"][b].get("close")}
                out.append(row)
    return sorted(out, key=lambda r: -r["lnr"])


def gap_bins(pairs, bins=3):
    """The ear's agreement with J0 by size of J0's gap, in equal-count bins."""
    if not pairs:
        return []
    size = math.ceil(len(pairs) / bins)
    out = []
    for i in range(0, len(pairs), size):
        v = pairs[i:i + size]
        out.append({"pairs": len(v), "lnr_hi": v[0]["lnr"], "lnr_lo": v[-1]["lnr"], "agree": sum(r["agree"] for r in v) / len(v)})
    return out


def claim_pairs(cards, drop=LABELS):
    """(cluster, gain by the score, closeness gap) per model and card: ln(d_S/d_m) against the ear's closeness over S."""
    out = []
    for card in cards:
        if "S" not in card["j0"] or card["ear"].get("S", {}).get("close") is None:
            continue
        for c in cands_of(card, (*drop, "S")):
            if card["ear"][c].get("close") is not None:
                out.append((card["cluster"], math.log(card["j0"]["S"] / card["j0"][c]), card["ear"][c]["close"] - card["ear"]["S"]["close"]))
    return out


def claim_row(pairs):
    """The Spearman of score gain and closeness gain, with each one's mean and the share of gains J0 and the ear both call positive."""
    if len(pairs) < 3:
        return None
    gain, close = [p[1] for p in pairs], [p[2] for p in pairs]
    return {"pairs": len(pairs), "rho": spearman(gain, close), "score_gain_positive": sum(g > 0 for g in gain) / len(gain),
            "ear_gain_positive": sum(c > 0 for c in close) / len(close), "ear_equal": sum(c == 0 for c in close) / len(close)}


def page_rows(cards, t90, drop=()):
    """The order rows on `cards`: J0's, the two no-score baselines', and what J0 adds to each."""
    pc = per_card(cards, drop)
    rows = {k: interval([(r["cluster"], r[k]) for r in pc], t90) for k in ("j0", "s_last", "mean_rank")}
    rows["j0_less_s_last"] = interval([(r["cluster"], None if r["j0"] is None or r["s_last"] is None else r["j0"] - r["s_last"]) for r in pc], t90)
    rows["j0_less_mean_rank"] = added_row(cards, t90, drop)
    return rows


def di_stem(u):
    return u["di"].rsplit("/", 1)[1].rsplit(".", 1)[0]


def slot_options(units):
    """Each slot's card choices: one tuple per way of filling it, no DI twice in a band across a slot."""
    out = []
    for band, cls, n, stem in SLOTS:
        pool = [u for u in units if u["player"] == band and u["cls"] == cls and (stem is None or di_stem(u) == stem)]
        ways = [c for c in itertools.combinations(sorted(pool, key=lambda u: u["unit"]), n) if len({u["di"] for u in c}) == n]
        if not ways:
            raise SystemExit(f"{band} {cls}: no way to fill {n}")
        out.append(ways)
    return out


def amp_spread(cards):
    n = collections.Counter(u["amp"] for u in cards)
    return max(n.get(a, 0) for a in ("pr12", "sw50r", "ac20")) - min(n.get(a, 0) for a in ("pr12", "sw50r", "ac20"))


def draw_cards(units, seed=DRAW_SEED):
    """The cards and spares from unit metadata alone: the fills whose amps are most even, one by the seed, then each spare band's
    crunch unit on a DI its cards do not use. -> (cards, spares)."""
    ways = [tuple(u for slot in fill for u in slot) for fill in itertools.product(*slot_options(units))]
    best = min(amp_spread(w) for w in ways)
    rng = random.Random(seed)
    cards = list(rng.choice(sorted((w for w in ways if amp_spread(w) == best), key=lambda w: [u["unit"] for u in w])))
    spares = []
    for band in SPARE_BANDS:
        used = {u["di"] for u in cards if u["player"] == band}
        pool = sorted((u for u in units if u["player"] == band and u["cls"] == "crunch" and u["di"] not in used), key=lambda u: u["unit"])
        if not pool:
            raise SystemExit(f"{band}: no spare DI")
        spares.append(rng.choice(pool))
    return cards, spares


def page_order(cards, spares, cands, letters, seed=PAGE_SEED, gap=4):
    """The page's order: every card and spare once, letters balanced, and two cards again, one of each class, at least `gap` items
    later, every candidate on another letter there. -> [{**unit, id, n, letters, repeat_of, spare}]."""
    from learn import capture_ear as C

    keep = C.CANDS, C.LETTERS
    C.CANDS, C.LETTERS = cands, letters
    try:
        rng = random.Random(seed)
        by = {u["unit"]: dict(u, spare=False) for u in cards} | {u["unit"]: dict(u, spare=True) for u in spares}
        twice = [rng.choice(sorted(u["unit"] for u in cards if u["cls"] == c)) for c in ("clean", "crunch")]
        seq = sorted(by) + twice
        while True:
            rng.shuffle(seq)
            if all(seq.index(t) + gap <= len(seq) - 1 - seq[::-1].index(t) for t in twice):
                break
        perms = iter(C.balanced(rng, len(by)))
        items, first = [], {}
        for n, u in enumerate(seq, 1):
            order = tuple(first[u][1][1:] + first[u][1][:1]) if u in first else next(perms)
            items.append({**by[u], "id": f"i{n}", "n": n, "letters": dict(zip(letters, order)), "repeat_of": first[u][0] if u in first else None})
            first.setdefault(u, (f"i{n}", list(order)))
    finally:
        C.CANDS, C.LETTERS = keep
    return items


def filled(items, heard, out):
    """The first hearings read: cards in scope and answered, a crunch card out or unanswered giving way to the next crunch spare
    in page order."""
    first = [it for it in items if it["repeat_of"] is None]
    kept = [it for it in first if not it["spare"] and heard.get(it["id"]) and it["id"] not in out]
    gone = sum(1 for it in first if not it["spare"] and it["cls"] == "crunch" and it not in kept)
    spares = [it for it in first if it["spare"] and heard.get(it["id"]) and it["id"] not in out]
    return kept + sorted(spares, key=lambda it: SPARE_BANDS.index(it["band"]))[:gone]


def failed(read):
    """More of the cards left unfilled than the limit, after the spares: out of scope and unanswered alike."""
    return CARDS - read > OUT_LIMIT


def repeat_rhos(rows):
    """Each repeat's Spearman with its first hearing. rows: a page in its order, each {heard, repeat_of}; `repeat_of` is "i<n>"."""
    out = []
    for r in rows:
        if r.get("repeat_of"):
            first = rows[int(r["repeat_of"][1:]) - 1]
            if r["heard"] and first["heard"]:
                cs = sorted(r["heard"])
                out.append(spearman([r["heard"][c]["rank"] for c in cs], [first["heard"][c]["rank"] for c in cs]))
    return out


def holm(ps):
    """Holm's adjusted p for {row: p}."""
    names = sorted(ps, key=ps.get)
    out, top = {}, 0.0
    for i, name in enumerate(names):
        top = max(top, min(1.0, (len(names) - i) * ps[name]))
        out[name] = top
    return out


def sign_p(wins, n):
    """One-sided sign test on `n` cards."""
    return sum(math.comb(n, k) for k in range(wins, n + 1)) / 2 ** n if n else 1.0


# --- the stored pages ------------------------------------------------------------------------------------------------

def vreal_cards():
    """L0's first hearings from `ear-vreal/score.json`, by band."""
    from learn import pipeline_fix as P

    rep = json.loads((P.out_dir() / "ear-vreal" / "score.json").read_text())
    return [{"page": "L0", "id": it["slug"], "cluster": it["band"], "cls": it["cls"], "amp": it["amp"], "ear": it["heard"], "j0": it["judge"]}
            for it in rep["per_item"] if it["repeat_of"] is None and it["heard"]]


def ftm_rows():
    """N4's page in order: `ear_ftm`'s key and the listener's export (`ear-ftm/ear-answers.txt`, the upload `score` read), roles named back."""
    from learn import capture_ear as C
    from learn import ear_ftm as EF
    from learn import pipeline_fix as P

    names = {v: k for k, v in EF.ROLE.items()}
    root = P.out_dir() / "ear-ftm"
    key = json.loads((root / "key.json").read_text())
    last = [ln for ln in (root / "ear-answers.txt").read_text().splitlines() if ln.startswith("{")][-1]
    ex = json.loads(last)
    if ex.get("build") != key["build"]:
        raise SystemExit(f"ear-answers.txt: build {ex.get('build')}, the page's is {key['build']}")
    out = []
    for it in key["items"]:
        heard = C.unblind(it, ex["answers"].get(it["id"]) or {})
        out.append({**it, "heard": {names[c]: v for c, v in heard.items()} if heard else None, "judge": {names[c]: v for c, v in it["judge"].items()}})
    return out


def ftm_cards():
    """N4's first hearings, by band."""
    return [{"page": "N4", "id": it["slug"], "cluster": it["band"], "cls": it["cls"], "amp": it["amp"], "ear": it["heard"], "j0": it["judge"]}
            for it in ftm_rows() if it["repeat_of"] is None and it["heard"]]


def capture_cards():
    """F57's first hearings from `captures/ear-check.json`, less the label page's out-of-scope units, item 8 by the listener's own
    blind correction. Clustered by the DI's GOAT player, since its creators sit on players `ear-eat` shares."""
    from learn import capture_labels as CL
    from learn import pipeline_fix as P

    root = P.out_dir() / "captures"
    rep = json.loads((root / "ear-check.json").read_text())
    fix = json.loads((root / "ear-check" / "item8-correction.json").read_text())
    player = {u["unit"]: u["player"] for u in CL.units_of()}
    out = []
    for n, it in enumerate(rep["per_item"], 1):
        if it["repeat_of"] is not None or not it["heard"] or it["unit"] in CL.LABEL_PAGE_OUT:
            continue
        ear = {c: dict(v) for c, v in it["heard"].items()}
        if f"i{n}" == fix["item"]:
            for letter, rank in fix["corrected_rank"].items():
                ear[fix["letters"][letter]]["rank"] = rank
        out.append({"page": "F57", "id": it["unit"], "cluster": f"GOAT {player[it['unit']]}", "cls": it["cls"], "amp": it["amp"], "ear": ear, "j0": it["judge"]})
    return out


def eat_j0(which, tag, key, search, held):
    """A reader's held-half J0 from `eat/score/score-judge`."""
    from learn import pipeline_fix as P

    rec = json.loads((P.out_dir() / "eat" / "score" / "score-judge" / which / tag / f"{key.replace('/', '__')}.json").read_text())
    judge = rec["judge"]
    return judge[search if search in judge else next(iter(judge))][held]["distance"]


def eat_cards():
    """`ear-eat`'s 13 pooled cards, J0 joined per candidate: readers from their records, the label from the search's best, the
    same judge within 0.1% on the checked labels (`docs/score-ear-plan.md`)."""
    from learn import pipeline_fix as P

    root = P.out_dir() / "eat"
    pooled = json.loads((root / "ear2" / "pooled.json").read_text())
    keys = {"p1": {it["id"]: it for it in json.loads((root / "ear" / "key.json").read_text())["items"]},
            "p2": {it["id"]: it for it in json.loads((root / "ear2" / "key.json").read_text())["items"]}}
    tags = {"S": "S", "FTm": "P2b-ftm", "M-pcs": "M-pcs", "EW-mix": "EW-mix"}
    out = []
    for card in pooled["by_card"]:
        page, i = card["id"].split(":")
        it = keys[page][i]
        d = P.out_dir() / (P.GOAT_DIR if it["which"] == "goat" else P.REAL_DIR)
        rec = json.loads((d / P.SEARCH_DIR / f"{it['key'].replace('/', '__')}.json").read_text())
        if (rec["search"], rec["held"]) != (it["search"], it["held"]):
            raise SystemExit(f"{it['key']}: the card's direction is not the search's")
        j0 = {c: eat_j0(it["which"], t, it["key"], it["search"], it["held"]) for c, t in tags.items()}
        j0["label"] = rec["best"]["judge"][it["held"]]
        song = it["key"].split("/")[1] if it["which"] == "bks" else card["cluster"]       # `cluster` is the DI on BKS
        out.append({"page": "ear-eat", "id": card["id"], "cluster": song, "cls": card["cls"], "amp": card["amp"], "set": card["which"],
                    "ear": {c: card["heard"][c] for c in j0}, "j0": j0})
    return out


def record_cards():
    """`record-match-1`, beside only: rank pages hold the day's judge as ranks. Mostly V-real's bands, so it never pools."""
    from learn import pretrain_set as PS

    rep = json.loads((PS.HOME / "listening" / "record-match-1" / "private" / "score.json").read_text())
    return [{"page": "record-match", "id": t["slug"], "cluster": t["slug"], "ear": {c: {"rank": r} for c, r in t["arm_ranks"].items()},
             "j0": t["judge_ranks"]} for t in rep["trials"] if t["repeat_of"] is None]


def repeats():
    """Each page's repeats, as Spearmans from its stored per-item ranks."""
    from learn import pipeline_fix as P

    root = P.out_dir()
    return {"L0": repeat_rhos(json.loads((root / "ear-vreal" / "score.json").read_text())["per_item"]), "N4": repeat_rhos(ftm_rows()),
            "F57": repeat_rhos(json.loads((root / "captures" / "ear-check.json").read_text())["per_item"]),
            "ear-eat": repeat_rhos(json.loads((root / "eat" / "ear" / "score.json").read_text())["per_item"])}


def cmd_stored(args):
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    P.require(PHASE)
    t90 = PS.t90
    pages = {"L0": vreal_cards(), "N4": ftm_cards(), "F57": capture_cards(), "ear-eat": eat_cards()}
    beside = record_cards()
    pooled = [c for p in READERS for c in pages[p]]
    dev = pages["F57"] + pages["ear-eat"]
    groups = {**pages, "pooled": pooled, "development": dev}
    rep = {"phase": PHASE, "cards": {k: len(v) for k, v in groups.items()}, "rows": {}, "repeats": repeats()}
    for name, cards in groups.items():
        rep["rows"][name] = {"all": page_rows(cards, t90), "no_label": page_rows(cards, t90, LABELS), "models_only": page_rows(cards, t90, ENDS),
                             "side_of_s": side_of_s(cards), "gap_bins": gap_bins(pairs_of(cards)), "gap_bins_with_ends": gap_bins(pairs_of(cards, ())),
                             "claim": claim_row(claim_pairs(cards))}
    rep["beside_record_match"] = {"cards": len(beside), "all": page_rows(beside, t90), "no_label": page_rows(beside, t90, LABELS),
                                  "side_of_s": side_of_s(beside), "rho": {c["id"]: j0_rho(c) for c in beside}}
    rep["development_disagreements"] = [r for r in pairs_of(dev, LABELS) if not r["agree"]]
    rep["vreal_disagreements"] = [r for r in pairs_of(pages["L0"] + pages["N4"], LABELS) if not r["agree"]]
    pathlib.Path(args.out).write_text(json.dumps(rep, indent=1))
    print(json.dumps({"cards": rep["cards"], "no_label_j0": {k: v["no_label"]["j0"] for k, v in rep["rows"].items()}}, indent=1))


# --- N12 -------------------------------------------------------------------------------------------------------------

def wide_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / WIDE_DIR


def wide_units():
    """(the second batch's trusted units with a finite held judge for S and the label, {unit: search record}, what was refused)."""
    from learn import capture_labels as CL

    keep = CL.BATCH
    CL.BATCH = CL.BATCH2
    try:
        units = CL.gated_units()[0]
        recs = CL.search_records()
    finally:
        CL.BATCH = keep
    finite = [u for u in units if math.isfinite(recs[u["unit"]]["s_judge"][recs[u["unit"]]["held"]])
              and math.isfinite(recs[u["unit"]]["best"]["judge"][recs[u["unit"]]["held"]])]
    return finite, recs, sorted({u["unit"] for u in units} - {u["unit"] for u in finite})


def slug_of(unit):
    return hashlib.sha256(unit.encode()).hexdigest()[:12]


def cmd_draw(_args):
    from learn import pipeline_fix as P

    P.require(WIDE)
    path = wide_dir() / "plan.json"
    if path.exists():
        raise SystemExit(f"{path} exists: the cards are drawn once")
    from learn import capture_labels as CL
    from learn import ear_vreal as E

    units, recs, refused = wide_units()
    active = {u["unit"]: E.activity(P.real_amp_track(u["sd"], u["track"], u["start_s"]))[recs[u["unit"]]["held"]] for u in units}
    quiet = sorted(k for k, v in active.items() if v < CL.ITEM_ACTIVE)
    cards, spares = draw_cards([u for u in units if u["unit"] not in quiet])
    row = lambda u, s: {"unit": u["unit"], "slug": slug_of(u["unit"]), "amp": u["amp"], "cls": u["cls"], "band": u["player"], "cluster": u["player"],     # noqa: E731
                        "di": u["di"], "search": recs[u["unit"]]["search"], "held": recs[u["unit"]]["held"], "spare": s}
    wide_dir().mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"seed": DRAW_SEED, "phase": WIDE, "units_read": len(units), "refused": refused, "held_activity": active, "too_quiet": quiet,
                                "cards": [row(u, False) for u in cards], "spares": [row(u, True) for u in spares]}, indent=1))
    for u in cards + spares:
        print(u["player"], u["cls"], u["amp"], di_stem(u), "spare" if u in spares else "", flush=True)
    print(len(cards), "cards", len(spares), "spares; amps", collections.Counter(u["amp"] for u in cards), flush=True)


def cmd_answers(_args):
    """FTm per search half, all 8 fold-and-seed models pooled, after `net_answers`' path reproduces stored answers on BKS and GOAT."""
    from learn import bakeoff_render as BR
    from learn import bakeoff_train as T
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    P.require(WIDE)
    folds = {k: [P.load_run(f"{BR.FTM}-k{k}", sd, "best")[0] for sd in T.SEEDS] for k in range(P.REAL_FOLDS)}
    some = BR.read_units()[::12]
    got = BR.net_answers(folds, some)
    for w in BR.SETS:
        want = BR.stored_answers(w, BR.FTM)
        bad = [k for k in got[w] if got[w][k] != want[k]]
        if bad or not got[w]:
            raise SystemExit(f"control: {w}: {len(bad)} of {len(got[w])} keys differ from the stored answers")
    print("CONTROL OK", {w: len(got[w]) for w in BR.SETS}, flush=True)
    nets = [n for k in folds for n in folds[k]]
    ms = P.A_menu_S()
    units, recs, _ = wide_units()
    out = {}
    for u in units:
        sel, S = ms[u["amp"]][u["cls"]]
        search = recs[u["unit"]]["search"]
        s8, ls = P.dfix_backed(u["unit"])[search]
        x, c = DS.model_input(s8, s8, ls, ls, search, u["amp"], u["cls"], "Dstem")
        r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
        st = P.hold_outside_space(F.answer_settings(u["amp"], S, r["a2"], r["sw_p"], r["mics"]), S, u["amp"])
        out[u["unit"]] = {search: {"select": sel, "settings": LO.sdict(st)}}
    path = wide_dir() / "answers" / "FTm.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tag": "FTm", "time": time.strftime("%Y-%m-%d %H:%M:%S"), "answers": out}))
    print("FTm", len(out), "units", flush=True)


def stored_reader(tag):
    return json.loads((wide_dir() / "answers" / f"{tag}.json").read_text())["answers"]


def cmd_render(args):
    """Each reader through each unit's DI, a fresh process and a priming render each, judged on the held half. On a card or spare S and
    the label render too: S held to its stored hash, the label to its stored judge. The held window, aligned, is kept for the cards."""
    import numpy as np

    from learn import arm_a_levers as AL
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import ear_vreal as E
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import rescore as R
    from learn import song_bank as B
    from learn import trusted_data as T

    P.require(WIDE)
    plan = json.loads((wide_dir() / "plan.json").read_text())
    on_page = {u["unit"]: u for u in plan["cards"] + plan["spares"]}
    units, recs, _ = wide_units()
    readers = {t: stored_reader(t) for t in args.tags.split(",")}
    ms = AL.menu_S()
    k, n = (int(x) for x in args.shard.split("/"))
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    for u in sorted(units, key=lambda q: q["unit"])[k::n]:
        out = wide_dir() / "renders" / slug_of(u["unit"])
        if (out / "rec.json").exists():
            continue
        rec = recs[u["unit"]]
        search, held, lag = rec["search"], rec["held"], rec["lag"]
        sel, S = ms[u["amp"]][u["cls"]]
        di32 = B.measure(PS.section_audio(u["di_path"], u["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = np.asarray(P.real_amp_track(u["sd"], u["track"], u["start_s"]), np.float64)
        settings = {t: (a[u["unit"]][search]["select"], a[u["unit"]][search]["settings"]) for t, a in readers.items()}
        if u["unit"] in on_page:
            settings |= {"S": (sel, LO.sdict(S)), "label": (rec["select"], rec["label"])}
        keep = {"unit": u["unit"], "lag": lag, "held": held, "judge": {}, "sha": {}}
        clips = {}
        for c, (s_, st_) in settings.items():
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            st = LO.tdict(st_)
            y = np.asarray(AM.fresh_render(CB.new_renderer, di32, s_, st, st), np.float64)[trim[0]:trim[1]]
            renders += 2
            keep["sha"][c] = AM.audio_sha(y)
            keep["judge"][c] = K.judge(ref, y, di, lag)[held]
            if c == "S" and keep["sha"][c] != rec["s_render_sha256"]:
                raise SystemExit(f"{u['unit']}: S's render differs from the search's")
            if c == "label" and abs(math.log(keep["judge"][c] / rec["best"]["judge"][held])) > 1e-3:
                raise SystemExit(f"{u['unit']}: the label's judge is off the search's")
            clips[c] = np.mean(y, 1) if y.ndim == 2 else y
        if u["unit"] in on_page:
            a, b = (int(x * E.SR) for x in R.HALVES[held])
            s0, s1 = E.window(a, b, len(ref), max(len(v) for v in clips.values()), lag)
            out.mkdir(parents=True, exist_ok=True)
            np.savez(out / "clips.npz", ref=ref[s0:s1].astype(np.float32), **{c.replace("-", "_"): v[s0 - lag:s1 - lag].astype(np.float32) for c, v in clips.items()})
            keep["window"] = [s0, s1]
        out.mkdir(parents=True, exist_ok=True)
        (out / "rec.json").write_text(json.dumps(keep, indent=1))
        print(f"{u['amp']} {u['cls']} {u['player']}: renders so far {renders}", flush=True)
    print(f"N12 RENDER DONE {k}/{n}: {renders} renders", flush=True)


def cmd_page(_args):
    """`ear_eat`'s page, its fixes and its artifact form, on these cards, in two parts for the artifact's size limit."""
    import numpy as np

    from learn import ear_eat as EE
    from learn import ear_vreal as E
    from learn import pretrain_set as PS

    key_path = wide_dir() / "key.json"
    if key_path.exists():
        raise SystemExit(f"{key_path} exists: a rebuild hides the listener's stored answers; move it aside first")
    plan = json.loads((wide_dir() / "plan.json").read_text())
    items = page_order(plan["cards"], plan["spares"], CANDS, EE.LETTERS)
    cache = wide_dir() / "aac-cache"
    intro = EE.INTRO.replace("the guitar as it was recorded through a real amp", "the guitar through a real amp, or a close capture of one")
    if intro == EE.INTRO:
        raise SystemExit("the intro's Record line has changed: word it again")
    kept, builds = [], []
    for part, start in enumerate(range(0, len(items), PAGE_ITEMS), 1):
        chunk = [{**it, "n": j, "part": part} for j, it in enumerate(items[start:start + PAGE_ITEMS], 1)]
        clips = {}
        for q, it in enumerate(chunk):
            z = np.load(wide_dir() / "renders" / it["slug"] / "clips.npz")
            group = {"ref": np.asarray(z["ref"], np.float64), **{k: np.asarray(z[c.replace("-", "_")], np.float64) for k, c in it["letters"].items()}}
            if len({len(v) for v in group.values()}) != 1:
                raise SystemExit(f"{it['slug']}: clip lengths differ")
            lev, info = E.level_group(group)
            for k, y in lev.items():
                clips[f"{it['id']}-{k}"] = E.encode(y, cache)
            chunk[q] = {**it, "levels": info}
        build = hashlib.sha256(f"{json.dumps([k['letters'] for k in chunk])}{time.time_ns()}".encode()).hexdigest()[:12]      # a page's name, no secret
        body = EE.cards(chunk)
        data = json.dumps({"build": build, "items": [{"id": it["id"], "n": it["n"]} for it in chunk]})
        a, b = E.PAGE.index("<h1>"), E.PAGE.index("@@CARDS@@")
        css = E.CSS + ".rank.five { grid-template-columns:auto repeat(5, 1fr); }\n.rank.close { grid-template-columns:auto repeat(4, 1fr); }\n.conf .scope { flex:1 1 180px; }\n"
        page = (E.PAGE[:a] + intro + "\n" + E.PAGE[b:]).replace("@@COUNT@@", str(len(chunk))).replace("@@CARDS@@", body) \
            .replace("@@CSS@@", css).replace("@@DATA@@", data).replace("@@CLIPS@@", json.dumps(clips)).replace("@@JS@@", EE.player_js())
        words = (*CANDS, *{u["unit"] for u in items}, *{u["band"] for u in items}, *{di_stem(u) for u in items})
        leaks = [w for w in words if len(w) > 2 and w != "label" and w in body + data]
        if leaks:
            raise SystemExit(f"the page names {leaks}")
        local = PS.HOME / "listening" / f"{LISTENING}-{part}" / "index.html"
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(page)
        out = wide_dir() / "page" / f"artifact-{part}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(EE.artifact_page(page, css, EE.player_js()))
        kept += chunk
        builds.append(build)
        print(f"N12 PAGE {part}: {len(chunk)} items -> {out}; build {build}; {out.stat().st_size / 1e6:.1f} MB")
    key_path.write_text(json.dumps({"page": WIDE_DIR, "builds": builds, "items": kept, "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))


def cmd_wide(args):
    from learn import capture_ear as C
    from learn import ear_eat as EE
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    P.require(WIDE)
    key = json.loads((wide_dir() / "key.json").read_text())
    got = {}
    seen = set()
    for f in args.answers:
        ex = EE.stored_answers(pathlib.Path(f).read_text())
        if ex.get("build") not in key["builds"]:
            raise SystemExit(f"{f}: build {ex.get('build')}, this page's are {key['builds']}")
        seen.add(ex["build"])
        got |= ex["answers"]
    if seen != set(key["builds"]):
        raise SystemExit("every part's answers are needed")
    items = key["items"]
    heard = {it["id"]: EE.unblind(it, got.get(it["id"]) or {}) for it in items}
    out = {it["id"] for it in items if (got.get(it["id"]) or {}).get("scope")}
    both = sorted(i for i in out if heard[i])
    if both:
        raise SystemExit(f"{both} hold both a scope mark and ranks: these go to the user before scoring")
    first_out = [it["id"] for it in items if it["repeat_of"] is None and not it["spare"] and it["id"] in out]
    read = filled(items, heard, out)
    judge = {it["unit"]: json.loads((wide_dir() / "renders" / it["slug"] / "rec.json").read_text())["judge"] for it in items}
    cards = [{"page": "N12", "id": it["id"], "cluster": it["cluster"], "cls": it["cls"], "amp": it["amp"], "ear": heard[it["id"]], "j0": judge[it["unit"]]} for it in read]
    eat = eat_cards()
    t90 = PS.t90
    a, b = page_rows(cards, t90, LABELS), page_rows(eat, t90, LABELS)
    pairs = [("label", "S"), ("FTm", "S"), ("M-pcs", "S"), ("EW-mix", "S"), ("EW-mix", "FTm"), ("M-pcs", "FTm")]
    ear = {}
    for x, y in pairs:
        pts = [(c["cluster"], float(c["ear"][x]["rank"] < c["ear"][y]["rank"])) for c in cards]
        gaps = [(c["cluster"], float(c["ear"][x]["close"] - c["ear"][y]["close"])) for c in cards]
        ear[f"{x} over {y}"] = {"share": C.share_row(pts), "close_gap": C.gap_row(gaps), "p": sign_p(int(sum(v for _, v in pts)), len(pts))}
    adj = holm({k: v["p"] for k, v in ear.items()})
    for k, v in ear.items():
        v["holm"] = adj[k]
    units, recs, _ = wide_units()
    score = {}
    for x, y in (("FTm", "S"), ("M-pcs", "S"), ("EW-mix", "S"), ("EW-mix", "FTm"), ("M-pcs", "FTm"), ("label", "S")):
        v = []
        for u in units:
            rec = recs[u["unit"]]
            j = dict(json.loads((wide_dir() / "renders" / slug_of(u["unit"]) / "rec.json").read_text())["judge"])
            j.setdefault("S", rec["s_judge"][rec["held"]])
            j.setdefault("label", rec["best"]["judge"][rec["held"]])
            v.append((u["player"], math.log(j[x] / j[y])))
        score[f"{x} less {y}"] = interval(v, t90)
    rep = {"phase": WIDE, "builds": key["builds"], "out_of_scope": sorted(out), "first_hearings_out": first_out, "page_failed": failed(len(read)),
           "read": [it["id"] for it in read], "spares_used": [it["id"] for it in read if it["spare"]],
           "unsure": [it["id"] for it in items if (got.get(it["id"]) or {}).get("conf") == "unsure"],
           "primary": a["j0_less_mean_rank"], "order_no_label": a, "order_all": page_rows(cards, t90), "order_models": page_rows(cards, t90, ENDS),
           "ear_eat_no_label": b, "pages_difference": welch(a["j0_less_mean_rank"], b["j0_less_mean_rank"], t90),
           "side_of_s": side_of_s(cards), "gap_bins": gap_bins(pairs_of(cards)), "claim": claim_row(claim_pairs(cards)),
           "disagreements": [r for r in pairs_of(cards, LABELS) if not r["agree"]], "ear": ear, "by_score": score,
           "repeats": [{"unit": it["unit"], "rho": spearman([heard[it["id"]][c]["rank"] for c in CANDS], [heard[it["repeat_of"]][c]["rank"] for c in CANDS])}
                       for it in items if it["repeat_of"] and heard.get(it["id"]) and heard.get(it["repeat_of"])]}
    pathlib.Path(args.out).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("primary", "pages_difference", "page_failed", "ear", "by_score", "repeats")}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("draw", cmd_draw), ("answers", cmd_answers), ("page", cmd_page)):
        sub.add_parser(name).set_defaults(fn=fn)
    s = sub.add_parser("render")
    s.add_argument("--shard", default="0/1")
    s.add_argument("--tags", default=",".join(READ))
    s.set_defaults(fn=cmd_render)
    s = sub.add_parser("wide")
    s.add_argument("out")
    s.add_argument("--answers", nargs="+", required=True)
    s.set_defaults(fn=cmd_wide)
    s = sub.add_parser("stored")
    s.add_argument("out")
    s.set_defaults(fn=cmd_stored)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
