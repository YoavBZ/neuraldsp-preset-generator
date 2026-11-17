"""The score against the ear on today's decisions: the ladder's ear check (`docs/ladder-ear-plan.md`; ledger `preset-ladder`
`phase_lear`, then `phase_lear_draw` with the draw file's sha256, then `phase_lear_outcome`).

On the ladder's held-out parts, with the recorded guitar (the amp track) as the reference and every preset through the
part's own DI, does the ear order S, Cen, the model's answer on the product's stem (`xl@-3`), the re-centred answer
(`rc-xl@-3`) and the label the way J0 does? A blind page of guitar-only cards, five letters a card, ties allowed.

    .venv/bin/python -m learn.ladder_ear draw                       # both sittings' cards and spares (zero renders), once
    # the draw file's sha256 goes into the ledger (`phase_lear_draw`) before any judge file is read
    .venv/bin/python -u -m learn.ladder_ear render --shard k/3      # k = 0, 1, 2: every card and spare, the hash guards
    .venv/bin/python -m learn.ladder_ear page --sitting 1           # two Artifact parts and the key (zero renders)
    .venv/bin/python -m learn.ladder_ear read --sitting 1 --answers P1.json P2.json   # the rows and the outcome, once
    .venv/bin/python -m learn.ladder_ear power --draws 60000        # the declared power and false-(b) figures

The pure parts (the draw's filters and spread, the page order, the tie-aware unblinding, every row, `outcome`, the power
simulation) are unit-tested in tests/test_ladder_ear.py; the render and page commands are not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
import statistics
import time

LEDGER_ID = "preset-ladder"
PLAN = "docs/ladder-ear-plan.md"
PHASE = "phase_lear"                  # the declaration: before the draw
PHASE_DRAW = "phase_lear_draw"        # the draw file's sha256: before any judge file is read
PHASE_OUT = "phase_lear_outcome"
DRAW_SEED = 20261171
PAGE_SEED = 20261172
SIM_SEED = 20261173
SETS = ("goat", "bks", "panel", "cap1")           # the draw's order
DECIDING = ("goat", "bks", "panel")
CARDS = {"goat": 10, "bks": 4, "panel": 4, "cap1": 4}       # a sitting's first hearings, half clean and half crunch
CLASSES = ("clean", "crunch")
SPARES = {"goat": ("clean", "crunch"), "bks": ("clean", "crunch"), "panel": (None,), "cap1": ("clean", "crunch")}
GOAT_PLAYER_MAX = 7
GOAT_AMPS = (4, 3, 3)                 # GOAT's cards per amp, in any order
BKS_AMP_MAX = 2
CAP1_AMPS = 3                         # cap1's four cards on three amps
AMP_RANGE = (6, 8)                    # each amp's cards in a sitting
ACTIVE = 0.8                          # `capture_labels.ITEM_ACTIVE`: the held half's activity, at least
TRIES = 20000                         # the draw's seeded attempts at a sitting that meets every limit
EARLIER_PAGES = (                     # ranking pages whose cards are not fresh: (page, key file under PF)
    ("F57", "captures/ear-check/key.json"), ("ear-eat 1", "eat/ear/key.json"), ("ear-eat 2", "eat/ear2/key.json"),
    ("N12", "ear-wide/key.json"), ("C1a", "c1a/ear/key.json"), ("C4", "c4/key.json"), ("A3", "a3/key.json"),
    ("H4b", "ear-wide/h4b/key.json"))
STRICT_FRESH = ("goat", "cap1")       # heard units out; BKS and the panel are too small to fill without them (heard last)

CANDS = ("S", "Cen", "M", "rc", "L")
ROW_OF = {"Cen": "cen", "M": "xl@-3", "rc": "rc-xl@-3"}     # the ladder's stored answers and judge files
LETTERS = "ABCDE"
REPEATS = 2                           # one clean and one crunch
GAP = 4                               # a repeat sits at least this many items after its first hearing
PART_SIZE = 12                        # items an Artifact part (16 MB)
MIN_RANKED = 18                       # first hearings ranked, of a sitting's 22
LEVEL_TOL_LU = 0.5                    # every letter within this of the Record's loudness after levelling
START_TOL = 0.005                     # `full_controls.START_TOL`: |ln(fresh held J0 / stored)|

CONTROL = ("L", "S")
KEY_PAIRS = (("L", "S"), ("Cen", "S"), ("M", "Cen"), ("rc", "Cen"), ("L", "Cen"))
BESIDE_PAIRS = (("M", "S"), ("rc", "S"), ("rc", "M"), ("L", "M"), ("L", "rc"))
DECIDED = (("L", "S"), ("Cen", "S"), ("L", "Cen"))          # row 2: an inversion of these is a (b)
MODEL = (("M", "Cen"), ("rc", "Cen"))                        # row 4: either firmly above Cen is a (b)
FIXED = {"L": 0, "Cen": 1, "rc": 1, "M": 2, "S": 3}          # A3's order with no audio (the pool's J0 order), lower closer
GAP_BINS = (0.05, 0.15)               # A4's |ln ratio| bins
SIGN_ALPHA = 0.05                     # "firmly": the one-sided sign test on untied cards, p at most this
HEARD_ABOVE, HEARD_BELOW, NOT_KNOWN = "heard above", "heard below", "not known by ear"


def ear_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "ladder" / "ear"


def plan_path():
    return ear_dir() / "plan.json"


def ledger_entry():
    from learn import preset_ladder as L

    return L.ledger_entry()


def require(*keys):
    e = ledger_entry()
    for k in keys:
        if not e or k not in e:
            raise SystemExit(f"the ledger's {LEDGER_ID} entry has no {k}: declare it before running")
    return e


def file_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def draw_refusal(entry, sha):
    """Why the renders, the page or the read may not use the draw file, or None (pure)."""
    rec = (entry or {}).get(PHASE_DRAW)
    if not isinstance(rec, dict) or not rec.get("sha256"):
        return f"the ledger's {LEDGER_ID} entry has no {PHASE_DRAW} sha256: record the draw file's hash first"
    if rec["sha256"] != sha:
        return f"the draw file's sha256 {sha[:12]} is not the ledger's {rec['sha256'][:12]}"
    return None


def require_draw():
    e = require(PHASE, PHASE_DRAW)
    why = draw_refusal(e, file_sha(plan_path()))
    if why:
        raise SystemExit(why)
    return json.loads(plan_path().read_text())


# --- the pool and the draw (zero renders, no judge value) --------------------------------------------------------------

def mild_units(drive, cls_of):
    """{set: the crunch units at or under the set's crunch median of the stored drive measure}. drive: {set: {unit:
    value or None}}, cls_of: {unit: class}. A crunch unit with no measure is not mild (pure)."""
    out = {}
    for s, d in drive.items():
        vals = [v for u, v in d.items() if cls_of[u] == "crunch" and v is not None]
        med = statistics.median(vals) if vals else None
        out[s] = {u for u, v in d.items() if cls_of[u] == "crunch" and v is not None and v <= med}
    return out


def eligible(parts, mild, active, heard):
    """The draw's pool from the ladder's parts (pure). parts: [{set, unit, cls, held, ...}]; mild: {set: units} (crunch
    only; the panel takes its DIs' "keep" instead and has no measure); active: {unit: {half: share}}; heard: unit ids
    on earlier pages. -> (pool with `heard` flags, {reason: count} of parts left out)."""
    pool, out = [], {"not judgeable (activity)": 0, "crunch over the set's median": 0, "heard before (strict set)": 0}
    for p in parts:
        if active.get(p["unit"], {}).get(p["held"], 0.0) < ACTIVE:
            out["not judgeable (activity)"] += 1
            continue
        if p["cls"] == "crunch" and p["set"] != "panel" and p["unit"] not in mild.get(p["set"], set()):
            out["crunch over the set's median"] += 1
            continue
        h = p["unit"] in heard
        if h and p["set"] in STRICT_FRESH:
            out["heard before (strict set)"] += 1
            continue
        pool.append({**p, "heard": h})
    return pool, out


def _order(rng, parts, fresh_first):
    """A seeded order; fresh parts first (stable within) when `fresh_first`."""
    xs = list(parts)
    rng.shuffle(xs)
    if fresh_first:
        xs.sort(key=lambda p: p["heard"])
    return xs


def _greedy(order, n, key, taken, units):
    """Up to n parts in `order` with `key` values not in `taken` and units not in `units` (both updated)."""
    out = []
    for p in order:
        if len(out) == n:
            break
        k = key(p)
        if k in taken or p["unit"] in units:
            continue
        out.append(p)
        taken.add(k)
        units.add(p["unit"])
    return out


def _amps(cards):
    c = {}
    for p in cards:
        c[p["amp"]] = c.get(p["amp"], 0) + 1
    return c


def song_of(cluster):
    """A BKS DI file's song: its session folder ("set5/BKS_Bulldozer_Full")."""
    return "/".join(str(cluster).split("/")[:2])


def set_cards(rng, s, pool, sitting, used):
    """One set's cards for one sitting, or None when this attempt breaks a set limit. used: {clusters, units, items,
    windows} taken so far (not changed here)."""
    half = CARDS[s] // 2
    mine = [p for p in pool if p["set"] == s and p["cluster"] not in used["clusters"] and p["unit"] not in used["units"]]
    units = set(used["units"])
    if s == "goat":
        taken = set(used["items"])
        cards = []
        for c in CLASSES:
            cards += _greedy(_order(rng, [p for p in mine if p["cls"] == c and p["item"] not in used["items"]], False),
                             half, lambda p: p["item"], taken, units)
        players = {}
        for p in cards:
            players[p["player"]] = players.get(p["player"], 0) + 1
        if len(cards) != CARDS[s] or max(players.values()) > GOAT_PLAYER_MAX or \
                tuple(sorted(_amps(cards).values(), reverse=True)) != GOAT_AMPS:
            return None
        return cards
    if s == "bks":
        cards = []
        for c in CLASSES:
            dis = sorted({p["cluster"] for p in mine if p["cls"] == c})
            rng.shuffle(dis)
            for d in dis[:half]:
                cards += _greedy(_order(rng, [p for p in mine if p["cluster"] == d], True), 1, lambda p: p["cluster"],
                                 set(), units)
        if any(v > BKS_AMP_MAX for v in _amps(cards).values()):
            return None
        if len(cards) == CARDS[s] and len({song_of(p["cluster"]) for p in cards}) < 2:
            return None                                   # both songs
        return cards
    if s == "panel":
        mine = [p for p in pool if p["set"] == s and p["unit"] not in used["units"]]   # the panel's clusters repeat in sitting 2
        cards, taken = [], set()
        for c in ("crunch", "clean"):
            cand = _order(rng, [p for p in mine if p["cls"] == c], True)
            got = _greedy(cand, half, (lambda p: p["band"]) if sitting == 1 else (lambda p: p["cluster"]), taken, units)
            if sitting != 1 and len(got) < half:          # sitting 2: other windows of the same DI files
                got += _greedy(cand, half - len(got), lambda p: p["unit"], set(), units)
            cards += got
        return cards
    taken = set(used["clusters"])                         # cap1: one a creator, never a GOAT card's item
    cards = []
    for c in CLASSES:
        cards += _greedy(_order(rng, [p for p in mine if p["cls"] == c and p["di_item"] not in used["items"]], False),
                         half, lambda p: p["cluster"], taken, units)
    if len(cards) == CARDS[s] and len(_amps(cards)) != CAP1_AMPS:
        return None
    return cards


def set_spares(rng, s, pool, cards, used):
    """One set's spares for one sitting, in the draw's order (SPARES[s]: their classes; None, the first class with a part
    left, clean first). BKS's spares sit on the sitting's own DI files, its clusters being few, else on another DI file of
    their class."""
    out, units = [], set(used["units"])
    for c in SPARES[s]:
        for cls in ((c,) if c else CLASSES):
            mine = [p for p in pool if p["set"] == s and p["cls"] == cls and p["unit"] not in units]
            if s == "goat":
                mine = [p for p in mine if p["item"] not in used["items"] and p["cluster"] not in used["clusters"]]
            elif s == "cap1":
                mine = [p for p in mine if p["di_item"] not in used["items"] and p["cluster"] not in used["clusters"]]
            elif s == "bks":                      # the sitting's own DI files first, else another of the class
                own = {q["cluster"] for q in cards if q["cls"] == cls}
                mine = [p for p in mine if p["cluster"] in own] or mine
            got = _greedy(_order(rng, mine, s in ("bks", "panel")), 1, lambda p: p["unit"], set(), units)
            if got:
                out.append(got[0])
                if s in ("goat", "cap1"):
                    used["clusters"].add(got[0]["cluster"])
                if s == "goat":
                    used["items"].add(got[0]["item"])
                break
    return out


def sitting_refusal(cards, strict=True):
    """Why a sitting's cards break the declared spread, or None (pure). Not strict (the second sitting): a cell its pool
    can't fill may run short, counted in the plan file; the amp limits hold either way."""
    for s, n in CARDS.items():
        got = [p for p in cards if p["set"] == s]
        for c in CLASSES:
            k = sum(p["cls"] == c for p in got)
            if k > n // 2 or (k < n // 2 and strict):
                return f"{s}: {k} {c} cards, not {n // 2}"
    lo, hi = AMP_RANGE
    for a, v in _amps(cards).items():
        if not lo <= v <= hi:
            return f"{v} cards on {a}"
    if len(_amps(cards)) != 3:
        return "not every amp holds cards"
    return None


def _take(used, cards, spares=False):
    """Mark cards (or spares) used. A BKS spare never claims its DI file: the other sitting may still need it."""
    for p in cards:
        used["units"].add(p["unit"])
        if p["set"] in ("goat", "cap1") or (p["set"] == "bks" and not spares):
            used["clusters"].add(p["cluster"])
        if p["set"] == "goat":
            used["items"].add(p["item"])
        if p["set"] == "cap1":
            used["items"].add(p["di_item"])


def draw_sittings(pool, seed=DRAW_SEED, tries=TRIES):
    """Both sittings' cards and spares in one seeded pass (pure). -> {"sittings": {"1": {cards, spares}, "2": ...},
    "attempts": {sitting: attempts}}. Refuses when a sitting can't meet its limits in `tries` attempts."""
    rng = random.Random(seed)
    used = {"clusters": set(), "units": set(), "items": set()}
    out, attempts = {}, {}
    for sitting in (1, 2):
        for t in range(1, tries + 1):
            trial = {k: set(v) for k, v in used.items()}
            cards, ok = [], True
            for s in SETS:
                got = set_cards(rng, s, pool, sitting, trial)
                if got is None:
                    ok = False
                    break
                _take(trial, got)
                cards += got
            if ok and sitting_refusal(cards, strict=sitting == 1) is None:
                spares = []
                for s in SETS:
                    spares += set_spares(rng, s, pool, [p for p in cards if p["set"] == s], trial)
                _take(trial, spares, spares=True)
                used = trial
                out[str(sitting)] = {"cards": cards, "spares": spares}
                attempts[str(sitting)] = t
                break
        else:
            raise SystemExit(f"sitting {sitting}: no draw met the limits in {tries} attempts")
    return {"sittings": out, "attempts": attempts}


def slug_of(set_, key):
    return hashlib.sha256(f"{set_}:{key}".encode()).hexdigest()[:16]


def heard_pages():
    """{page: unit ids}: every unit a card on an earlier ranking page, from those pages' keys (unit ids only)."""
    from learn import pipeline_fix as P

    out = {}
    for page, rel in EARLIER_PAGES:
        p = P.out_dir() / rel
        if not p.exists():
            raise SystemExit(f"{p}: an earlier page's key is missing")
        out[page] = sorted({it["unit"] for it in json.loads(p.read_text())["items"]})
    return out


def heard_units(pages):
    """{page: units} -> {unit: [pages]}."""
    out = {}
    for page, units in pages.items():
        for u in units:
            out.setdefault(u, []).append(page)
    return out


def page_matches(pages, ladder_units):
    """{page: {units on the page, of them among the ladder's parts}}: the "fresh" filter's matches, per page (pure)."""
    return {page: {"units": len(us), "matched": len(set(us) & set(ladder_units))} for page, us in pages.items()}


def labels(st):
    """{(unit, amp): the C2 or C2r output's label: select, settings, search, held, render sha256} (no judge value)."""
    out = {}
    for d in (st["c2"], st["c2r"]):
        for r in d["records"]:
            o = d["outputs"].get(r["key"]) or {}
            sha = ((o.get("fresh") or {}).get("label") or {}).get("render_sha256")
            if o.get("label") is not None and sha and o.get("search") in ("A", "B"):
                out[(r["unit"], r["amp"])] = {"select": o["select"], "settings": o["label"], "search": o["search"],
                                              "held": o["held"], "sha": sha, "output_key": r["key"], "which": d is st["c2r"]}
    return out


def cmd_draw(_args):
    """Both sittings' cards and spares from the ladder's 480 parts, on metadata and audio alone -> ladder/ear/plan.json,
    written once. No judge value is used: `R.state()` loads the C2 and C2r outputs, which carry judge values, but the
    draw reads only the label's search half and hash from their own fields, and the answers from the ladder's answer
    files; no judge file is opened."""
    require(PHASE)
    if plan_path().exists():
        raise SystemExit(f"{plan_path()} exists: the cards are drawn once")
    import numpy as np

    from learn import ear_vreal as E
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P
    from learn import preset_ladder as L

    st = R.state()
    lab = labels(st)
    ans = {c: json.loads(L.answers_path(r).read_text())["answers"] for c, r in ROW_OF.items()}
    pages = heard_pages()
    heard = heard_units(pages)
    nl = json.loads((P.out_dir() / "scope" / "list.json").read_text())["nl"]
    parts, left = [], {"n12 (beside the deciding pool)": 0, "no lag": 0, "no label": 0, "no ladder answer": 0}
    for ru in R.read_units(st):
        if ru["set"] not in SETS:
            left["n12 (beside the deciding pool)"] += 1
            continue
        key = f"{ru['unit']}|{ru['amp']}"
        lb = lab.get((ru["unit"], ru["amp"]))
        if ru["lag"] is None:
            left["no lag"] += 1
            continue
        if lb is None:
            left["no label"] += 1
            continue
        if any(((ans[c].get(ru["set"]) or {}).get(key) or {}).get("*" if c == "Cen" else lb["search"]) is None for c in ROW_OF):
            left["no ladder answer"] += 1
            continue
        prt = ru["prt"]
        parts.append({"set": ru["set"], "unit": ru["unit"], "amp": ru["amp"], "key": key, "cls": prt["cls"],
                      "cluster": ru["cluster"], "fold": ru["fold"], "lag": ru["lag"], "search": lb["search"],
                      "held": lb["held"], "player": R.player_of(ru["set"], prt) if ru["set"] == "goat" else None,
                      "item": prt.get("item") if ru["set"] == "goat" else None,
                      "di_item": prt.get("di_item") if ru["set"] == "cap1" else None, "band": prt.get("band"),
                      "slug": slug_of(ru["set"], key), "prt": prt})
    cls_of = {p["unit"]: p["cls"] for p in parts}
    drive = {s: {} for s in ("goat", "bks", "cap1")}
    for p in parts:
        if p["set"] in drive:
            drive[p["set"]][p["unit"]] = p["prt"].get("nonlinear_db") if p["set"] == "cap1" else nl.get(p["unit"])
    mild = mild_units(drive, cls_of)
    active = {}
    for p in parts:
        if p["unit"] not in active:
            prt = p["prt"]
            active[p["unit"]] = E.activity(np.asarray(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64))
    pool, out = eligible(parts, mild, active, set(heard))
    d = draw_sittings(pool)
    medians = {s: statistics.median([v for u, v in dv.items() if cls_of[u] == "crunch" and v is not None]) for s, dv in drive.items()}
    rows = {k: [{**p, "sitting": int(k), "role": role} for role in ("cards", "spares") for p in v[role]]
            for k, v in d["sittings"].items()}
    doc = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "seed": DRAW_SEED, "parts_read": len(parts),
           "left_out": left, "left_out_of_pool": out, "pool": len(pool), "crunch_medians": medians,
           "held_activity": active, "heard_pages": {u: v for u, v in heard.items() if u in cls_of},
           "earlier_page_matches": page_matches(pages, cls_of),
           "heard_used": {k: sum(p["heard"] for p in v) for k, v in rows.items()},
           "short": {k: {f"{s} {c}": CARDS[s] // 2 - sum(p["set"] == s and p["cls"] == c and p["role"] == "cards"
                                                          for p in v)
                         for s in SETS for c in CLASSES} for k, v in rows.items()},
           "attempts": d["attempts"], "sittings": rows, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(plan_path(), doc)
    for k, v in rows.items():
        cards = [p for p in v if p["role"] == "cards"]
        per = ", ".join(f"{s} {sum(p['set'] == s for p in cards)}" for s in SETS)
        print(f"sitting {k}: {len(cards)} cards ({per}), amps {_amps(cards)}, spares {len(v) - len(cards)}, "
              f"heard used {doc['heard_used'][k]}")
    print(f"LADDER-EAR DRAW DONE: pool {len(pool)} of {len(parts)} parts; record in the ledger's {PHASE_DRAW}: "
          f"sha256 {file_sha(plan_path())}")


# --- the renders (after the draw's hash is in the ledger) -------------------------------------------------------------

def preset_sha(select, settings):
    return hashlib.sha256(json.dumps([select, settings], sort_keys=True).encode()).hexdigest()


def guard(cand, fresh_held, sha, stored_sha=None, stored_held=None):
    """A clip's guard (pure): Cen, M and rc by their stored render hash; S by its fresh held J0 against the stored within
    START_TOL; L by its hash, or where that differs by its held J0 within START_TOL (N12's rule, F66's audit note).
    -> "hash" | "j0" | "failed"."""
    if cand in ("Cen", "M", "rc"):
        return "hash" if stored_sha is not None and sha == stored_sha else "failed"
    if cand == "L" and stored_sha is not None and sha == stored_sha:
        return "hash"
    ok = isinstance(stored_held, (int, float)) and stored_held > 0 and isinstance(fresh_held, (int, float)) and \
        fresh_held > 0 and abs(math.log(fresh_held / stored_held)) <= START_TOL
    return "j0" if ok else "failed"


def clip_paths(p):
    d = ear_dir() / "clips"
    return d / f"{p['slug']}.npz", d / f"{p['slug']}.json"


def cmd_render(args):
    """Every card and spare of both sittings (one shard): the five presets each fresh in its own primed process through the
    part's measure DI, trimmed as the judge renders are, judged on both halves at the part's lag, each guarded; the held
    window's clips -> ladder/ear/clips/<slug>.npz, .json (the resume marker, after its clips)."""
    plan = require_draw()
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import full_controls_c3r as R
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import preset_ladder as L
    from learn import pretrain_set as PS
    from learn import score_ear as SE
    from learn import song_bank as B
    from learn import trusted_data as T

    st = R.state()
    lab = labels(st)
    ans = {c: json.loads(L.answers_path(r).read_text())["answers"] for c, r in ROW_OF.items()}
    ms = P.A_menu_S()
    every = [p for k in ("1", "2") for p in plan["sittings"][k]]
    k, n = args.shard
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    for p in every[k::n]:
        npz, rp = clip_paths(p)
        if rp.exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        prt, held, search, lag = p["prt"], p["held"], p["search"], p["lag"]
        ru = {"set": p["set"], "unit": p["unit"], "amp": p["amp"]}
        lb = lab[(p["unit"], p["amp"])]
        if lb["search"] != search:
            raise SystemExit(f"{p['key']}: the label's search half changed since the draw")
        sel, S = ms[p["amp"]][p["cls"]]
        presets = {"S": (sel, LO.sdict(S)), "L": (lb["select"], lb["settings"])}
        for c, row in ROW_OF.items():
            a = ans[c][p["set"]][p["key"]]["*" if c == "Cen" else search]
            presets[c] = (a["select"], a["settings"])
        out = (st["c2r"] if lb["which"] else st["c2"])["outputs"][lb["output_key"]]
        stored = {"L": (lb["sha"], R.half_value({search: out["fresh"]["label"]["judge"]}, search, held)),
                  "S": (None, R.half_value({P.ANY_HALF: R.s_judges(st, ru)}, search, held))}
        for c, row in ROW_OF.items():
            jp = L.judge_path(row, ru)
            j = json.loads(jp.read_text()) if jp.exists() else {}
            stored[c] = ((j.get("render_sha256") or {}).get("*" if c == "Cen" else search), None)
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = np.asarray(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64)
        rec = {"set": p["set"], "unit": p["unit"], "key": p["key"], "held": held, "search": search, "lag": lag,
               "cands": {}}
        kept, win = {}, None
        for c in CANDS:
            sl, stg = presets[c]
            x = LO.tdict(stg)
            y = np.asarray(AM.fresh_render(CB.new_renderer, di32, sl, x, x), np.float64)[trim[0]:trim[1]]
            renders += 2
            j = K.judge(ref, y, di, lag)
            sha = AM.audio_sha(y)
            g = guard(c, j.get(held), sha, *stored[c])
            mono = np.mean(y, 1) if y.ndim == 2 else y
            s0, s1 = SE.h4_window(held, len(ref), len(mono), lag)
            if win not in (None, (s0, s1)):
                raise SystemExit(f"{p['key']}: the renders' windows differ")
            win = (s0, s1)
            kept[c] = mono[s0 - lag:s1 - lag].astype(np.float32)
            rec["cands"][c] = {"preset_sha256": preset_sha(sl, stg), "judge": j, "render_sha256": sha,
                               "stored_sha256": stored[c][0], "stored_held": stored[c][1], "guard": g}
        rec["window"] = list(win)
        rec["ok"] = all(v["guard"] != "failed" for v in rec["cands"].values())
        rec["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        npz.parent.mkdir(parents=True, exist_ok=True)
        np.savez(npz, ref=ref[win[0]:win[1]].astype(np.float32), **kept)
        P.save(rp, rec)
        print(f"{p['set']} {p['cls']} {p['role']}: guards {[rec['cands'][c]['guard'] for c in CANDS]}; renders so far "
              f"{renders}", flush=True)
    print(f"LADDER-EAR RENDER DONE {k}/{n}: {renders} renders", flush=True)


# --- the page ------------------------------------------------------------------------------------------------------------

def groups_of(presets):
    """{cand: preset sha256} -> groups of candidates playing the same preset, in CANDS order (identical presets share a
    letter)."""
    out = []
    for c in CANDS:
        if c not in presets:
            continue
        g = next((g for g in out if presets[g[0]] == presets[c]), None)
        if g is None:
            out.append([c])
        else:
            g.append(c)
    return [tuple(g) for g in out]


def substitute(cards, spares, bad):
    """Each card a guard put out gives way to the first unused spare of its set and class that no guard put out (pure).
    -> (the sitting's cards, [(card key, spare key or None)])."""
    left = [s for s in spares if s["key"] not in bad]
    out, subs = [], []
    for c in cards:
        if c["key"] not in bad:
            out.append(c)
            continue
        sp = next((s for s in left if s["set"] == c["set"] and s["cls"] == c["cls"]), None)
        subs.append((c["key"], sp["key"] if sp else None))
        if sp:
            left.remove(sp)
            out.append(sp)
    return out, subs


def floor_refusal(cards, drawn, subs):
    """Why no page may be built, or None (pure): a card a guard put out with no spare left would leave the sitting
    short of the cards it drew, and a page once built is never rebuilt."""
    if len(cards) < len(drawn):
        return (f"{len(drawn) - len(cards)} of the sitting's {len(drawn)} cards were put out with no spare left "
                f"({[k for k, sp in subs if sp is None]}): nothing is written; this goes to the orchestrator")
    return None


def page_order(cards, sitting, seed=PAGE_SEED, gap=GAP):
    """Every card once and two repeats, one clean and one crunch, each at least `gap` items after its first hearing,
    the order and each card's letters seeded; in a repeat every preset group sits on another letter (pure).
    cards: [{key, cls, groups, ...}] -> [{**card, id, n, letters: {letter: group}, repeat_of}]."""
    rng = random.Random(seed + sitting)
    by = {c["key"]: c for c in cards}
    twice = [rng.choice(sorted(k for k, c in by.items() if c["cls"] == cl)) for cl in CLASSES]
    seq = sorted(by) + twice
    for _ in range(10000):
        rng.shuffle(seq)
        if all(seq.index(t) + gap <= len(seq) - 1 - seq[::-1].index(t) for t in twice):
            break
    else:
        raise SystemExit("no order holds the repeats apart")
    out, first = [], {}
    for n, k in enumerate(seq, 1):
        gs = list(by[k]["groups"])
        order = rng.sample(gs, len(gs))
        if k in first and len(gs) > 1:
            before = first[k]["letters"]
            for _ in range(10000):
                if all(before[LETTERS[i]] != g for i, g in enumerate(order)):
                    break
                order = rng.sample(gs, len(gs))
            else:
                raise SystemExit(f"{k}: no letter rotation found")
        it = {**by[k], "id": f"i{n}", "n": n, "letters": {LETTERS[i]: tuple(g) for i, g in enumerate(order)},
              "repeat_of": first[k]["id"] if k in first else None}
        out.append(it)
        first.setdefault(k, it)
    return out


INTRO = """<h1>Which preset sounds most like the recording?</h1>
<p class="intro">@@COUNT@@ items of about 4 seconds, looping. <b>Record</b> is the guitar as it was recorded. The lettered
presets play <b>the very same performance</b>, so every note lines up and only the tone differs. Most items have five
letters, a few fewer. Everything loops together and switches instantly at the same moment: tap a button, or press R and
the letters (or 1-6); Space stops. All clips are set to the same loudness. Headphones, please.</p>
<p class="intro">For each item, rank the letters: 1 is closest to the Record. Give the same rank to any you can't tell
apart, as many as you like. Rating how close each one is, and saying whether you are sure, are optional. If you can't
judge an item at all, tap <b>Can't judge this one</b>. Which preset is which is hidden and shuffled per item, and a
couple of items come back later.
Answers are saved in this browser as you go; tap <b>Export</b> any time and send the text.</p>"""

JS_EDITS = (
    ('const STORE = "real-song-exam:" + DATA.build;', 'const STORE = "ladder-ear:" + DATA.build;'),
    ('const NAMES = {ref: "the record\'s guitar", A: "A", B: "B", C: "C", D: "D"};',
     'const NAMES = {ref: "the record\'s guitar", A: "A", B: "B", C: "C", D: "D", E: "E"};'),
    ('a: "A", b: "B", c: "C", d: "D", "1": "ref", "2": "A", "3": "B", "4": "C", "5": "D"',
     'a: "A", b: "B", c: "C", d: "D", e: "E", "1": "ref", "2": "A", "3": "B", "4": "C", "5": "D", "6": "E"'),
    ("  const my = token;\n",
     "  const my = token;\n  if (stampReady) { const a0 = ans[it.dataset.id] = ans[it.dataset.id] || {};\n"
     "    if (!a0.t_play) { a0.t_play = Date.now(); save(); } }\n"),
    ("let ans = {};\n", "let ans = {};\nlet stampReady = !window.claude;   // the first-play stamp waits for the db's restore\n"),
    ('it.querySelectorAll(".conf button").forEach(b => b.setAttribute("aria-pressed", String(a.conf === b.dataset.c)));',
     'it.querySelectorAll(".conf button[data-c]").forEach(b => b.setAttribute("aria-pressed", String(a.conf === b.dataset.c)));\n'
     '    it.querySelector(".scope").setAttribute("aria-pressed", String(!!a.scope));'),
    ('it.querySelectorAll(".conf button").forEach(b => b.addEventListener("click", () => {',
     'it.querySelectorAll(".conf button[data-c]").forEach(b => b.addEventListener("click", () => {'),
    ('const full = it.dataset.letters.split("").every(l => r[l]);',
     'const full = it.dataset.letters.split("").every(l => r[l]) || !!a.scope;'),
    ('it.querySelector(".done").textContent = full ? "Answered" : "";',
     'it.querySelector(".done").textContent = a.scope ? "Marked: can\'t judge" : full ? "Answered" : "";'),
    ('" " + (a.conf || "-") + (a.note ? " | " + a.note : "")', '" " + (a.conf || "-") + (a.scope ? " cant-judge" : "") + (a.note ? " | " + a.note : "")'),
    ('const lines = ["ear-vreal build "', 'const lines = ["ladder-ear build "'),
    ('a.download = "ear-vreal-answers-"', 'a.download = "ladder-ear-answers-"'),
)
SCOPE_JS = """
items.forEach(it => { const b = it.querySelector(".scope"), id = it.dataset.id;
  b.addEventListener("click", () => { const a = ans[id] = ans[id] || {}; a.scope = !a.scope; a.t_last = Date.now();
    save(); paint(); }); });
"""


def player_js():
    """The exam's player (each item's own letters, ties allowed) for up to five letters, with the can't-judge mark and the
    first-play and last-change times."""
    from learn import real_song_exam as X

    js = X.player_js()
    for old, new in JS_EDITS:
        if old not in js:
            raise SystemExit(f"the exam's player changed: {old[:60]}")
        js = js.replace(old, new)
    stamp = "const a = ans[id] = ans[id] || {};"
    if js.count(stamp) < 3:
        raise SystemExit("the exam's player changed: its answer handlers")
    js = js.replace(stamp, stamp + " a.t_last = Date.now();")
    if not js.rstrip().endswith("paint();") or "delete r[o]" in js:
        raise SystemExit("the exam's player changed")
    return js.rstrip()[:-len("paint();")] + SCOPE_JS + "paint();\n"


CSS_EXTRA = "".join(f".rank.n{n} {{ grid-template-columns:auto repeat({n}, 1fr); }}\n" for n in (2, 3, 4, 5)) + \
    ".rank.close { grid-template-columns:auto repeat(4, 1fr); }\n.conf .scope { flex:1 1 180px; }\n" \
    ".rank.n5 button { padding-left:0; padding-right:0; min-width:0; }\n"


def cards_html(items, total):
    """Each item's card: the Record and its letters; ranks 1 to n (ties allowed); closeness, confidence, the can't-judge
    mark and a note."""
    from learn import ear_vreal as E

    out = []
    for it in items:
        ls = sorted(it["letters"])
        n = len(ls)
        rank = "".join(f'<span class="lab">{k}</span>' + "".join(
            f'<button type="button" data-l="{k}" data-r="{r}">{r}</button>' for r in range(1, n + 1)) for k in ls)
        close = "".join(f'<span class="lab">{k}</span>' + "".join(
            f'<button type="button" data-l="{k}" data-v="{v}">{t}</button>' for v, t in E.CLOSE) for k in ls)
        heads = '<span class="hd">closest</span>' + '<span class="hd"></span>' * (n - 2) + '<span class="hd">furthest</span>'
        out.append(
            f'<article class="item" data-id="{it["id"]}" data-n="{it["n"]}" data-letters="{"".join(ls)}">'
            f'<div class="num">{it["n"]} / {total}</div><h3>Recording {it["n"]}</h3><div class="plays">'
            '<button type="button" class="src" data-k="ref" aria-pressed="false">Record (R)</button>'
            + "".join(f'<button type="button" class="src" data-k="{k}" aria-pressed="false">{k}</button>' for k in ls)
            + '<button type="button" class="stop" aria-label="Stop">&#9632;</button></div><p class="now"></p>'
            '<div class="q">Rank them, 1 closest to the Record (the same rank for any you can\'t tell apart)</div>'
            f'<div class="rank n{n}"><span></span>{heads}{rank}</div>'
            f'<div class="q">How close is each one to the Record? (optional)</div><div class="rank close">{close}</div>'
            '<div class="conf"><span>Confidence (optional):</span><button type="button" data-c="sure">Sure</button>'
            '<button type="button" data-c="unsure">Unsure</button>'
            '<button type="button" class="scope" aria-pressed="false">Can\'t judge this one</button></div>'
            '<input class="note" type="text" placeholder="Note (optional)" aria-label="Note">'
            '<div class="done"></div></article>')
    return "".join(out)


def page_html(chunk, clips, build, total):
    from learn import ear_vreal as E

    js, css = player_js(), E.CSS + CSS_EXTRA
    a, b = E.PAGE.index("<h1>"), E.PAGE.index("@@CARDS@@")
    data = json.dumps({"build": build, "items": [{"id": it["id"], "n": it["n"]} for it in chunk]})
    page = (E.PAGE[:a] + INTRO + "\n" + E.PAGE[b:]).replace("@@COUNT@@", str(len(chunk))) \
        .replace("@@CARDS@@", cards_html(chunk, total)).replace("@@CSS@@", css).replace("@@DATA@@", data) \
        .replace("@@CLIPS@@", json.dumps(clips)).replace("@@JS@@", js)
    return page, css, js


SYNC_END = ("    if (Object.keys(ans).length) push();\n  } catch (e) {}\n})();",
            "    if (Object.keys(ans).length) push();\n  } catch (e) {} finally { stampReady = true; }\n})();")


def artifact_page(page, css, js, part):
    """C1a's Artifact wrapping (answers kept in the page's store, `answers/<build>`), under this page's title. The
    first-play stamp is armed only once the db has connected and restored (or failed), so a play before the restore
    never creates an answer that would block it."""
    from learn import c1a_ear as C

    art = C.artifact_page(page, css, js).replace("<title>Record A/B Check</title>", f"<title>Five Presets Check {part}</title>")
    if art.count(SYNC_END[0]) != 1:
        raise SystemExit("C1a's db sync changed: its end")
    return art.replace(*SYNC_END)


def page_leaks(text, cards):
    words = {"xl@-3", "rc-xl", "R-all", "ladder", "centre", "Cen ", "search", "X-LANCE", "GOAT", "BKS", "cap1", "panel"}
    for c in cards:
        words |= {c["unit"], c["key"], str(c["cluster"]), c["slug"], str(c["cluster"]).rsplit("/", 1)[-1]}
        if c.get("band"):
            words.add(c["band"])
    return sorted(w for w in words if len(w) > 2 and w in text)


def level_refusal(levels_lufs, tol=LEVEL_TOL_LU):
    """{name: LUFS after levelling} -> the letters off the Record's loudness by more than tol (pure)."""
    ref = levels_lufs["ref"]
    return sorted(k for k, v in levels_lufs.items() if k != "ref" and (v is None or ref is None or abs(v - ref) > tol))


def cmd_page(args):
    """One sitting's page (zero renders): the cards after their guards (a card a guard put out gives way to a spare),
    identical presets on one letter, two repeats, every clip at -23 LUFS by `ear_vreal.level_group`, in two Artifact
    parts of 12 -> ladder/ear/key-<s>.json, ladder/ear/page/sitting-<s>-part-<p>.html and the local pages. Refuses,
    writing nothing, when the cards left after the spares are fewer than the sitting drew."""
    plan = require_draw()
    s = args.sitting
    kp = ear_dir() / f"key-{s}.json"
    if kp.exists():
        raise SystemExit(f"{kp} exists: a rebuild hides the listener's stored answers")
    if s == 2:
        r1 = ear_dir() / "read-1.json"
        if not r1.exists() or json.loads(r1.read_text())["outcome"]["letter"] != "c":
            raise SystemExit("the second sitting is built only after the first reads (c)")
    import numpy as np

    from learn import build_data_review as BDR
    from learn import ear_vreal as E
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from analysis import io

    rows = plan["sittings"][str(s)]
    recs = {}
    for p in rows:
        _, rp = clip_paths(p)
        if not rp.exists():
            raise SystemExit(f"{p['key']}: not rendered; every card and spare renders first")
        recs[p["key"]] = json.loads(rp.read_text())
    bad, levelled, why = set(), {}, {}
    for p in rows:
        rec = recs[p["key"]]
        if not rec["ok"]:
            bad.add(p["key"])
            why[p["key"]] = {c: v["guard"] for c, v in rec["cands"].items()}
            continue
        npz, _ = clip_paths(p)
        z = np.load(npz)
        group = {"ref": np.asarray(z["ref"], np.float64), **{c: np.asarray(z[c], np.float64) for c in CANDS}}
        if len({len(v) for v in group.values()}) != 1:
            raise SystemExit(f"{p['key']}: clip lengths differ")
        lev, info = E.level_group(group)
        lufs = {k: io.loudness_lufs(io.from_samples(y.reshape(-1, 1), BDR.SR)) for k, y in lev.items()}
        off = level_refusal(lufs)
        if off:
            bad.add(p["key"])
            why[p["key"]] = {"level_off": off}
            continue
        levelled[p["key"]] = (lev, info, lufs)
    drawn = [p for p in rows if p["role"] == "cards"]
    cards, subs = substitute(drawn, [p for p in rows if p["role"] == "spares"], bad)
    why_short = floor_refusal(cards, drawn, subs)
    if why_short:
        raise SystemExit(why_short)
    for c in cards:
        c["groups"] = groups_of({x: recs[c["key"]]["cands"][x]["preset_sha256"] for x in CANDS})
    items = page_order(cards, s)
    cache = ear_dir() / "aac-cache"
    parts, kept = {}, []
    for it in items:
        lev, info, lufs = levelled[it["key"]]
        part = (it["n"] - 1) // PART_SIZE + 1
        clips = parts.setdefault(part, {})
        clips[f"{it['id']}-ref"] = E.encode(lev["ref"], cache)
        for letter, g in it["letters"].items():
            clips[f"{it['id']}-{letter}"] = E.encode(lev[g[0]], cache)
        rec = recs[it["key"]]
        kept.append({**{k: v for k, v in it.items() if k != "prt"}, "part": part, "levels": info, "lufs": lufs,
                     "j0": {c: rec["cands"][c]["judge"][it["held"]] for c in CANDS},
                     "guards": {c: rec["cands"][c]["guard"] for c in CANDS}, "window": rec["window"]})
    builds = {}
    for part in sorted(parts):
        chunk = [it for it in kept if it["part"] == part]
        build = hashlib.sha256(f"{json.dumps([k['letters'] for k in chunk])}{time.time_ns()}".encode()).hexdigest()[:12]
        builds[part] = build
        page, css, js = page_html(chunk, parts[part], build, len(kept))
        leaks = page_leaks(page.split('<script id="clips"')[0], rows)
        if leaks:
            raise SystemExit(f"the page names {leaks}")
        local = PS.HOME / "listening" / "ladder-ear" / f"sitting-{s}" / f"part-{part}" / "index.html"
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(page)
        out = ear_dir() / "page" / f"sitting-{s}-part-{part}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(artifact_page(page, css, js, part))
        print(f"part {part}: {len(chunk)} items, build {build}, {out} ({out.stat().st_size / 1e6:.1f} MB)")
    P.save(kp, {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "sitting": s, "builds": builds, "items": kept,
                "put_out": why, "substitutions": subs, "draw_sha256": file_sha(plan_path()),
                "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"LADDER-EAR PAGE DONE: sitting {s}, {len(kept)} items in {len(builds)} parts; {len(bad)} put out, "
          f"substitutions {subs}")


# --- the read (zero renders) ---------------------------------------------------------------------------------------------

def unblind(item, ans):
    """One item's answer -> {cand: {rank, close}} (ties allowed; a shared letter gives its candidates one rank), or None
    when it is marked can't-judge or any letter lacks a rank from 1 to the item's letter count (pure)."""
    from learn import ear_vreal as E

    a = ans or {}
    if a.get("scope"):
        return None
    r, c = a.get("rank") or {}, a.get("close") or {}
    n = len(item["letters"])
    if any(r.get(k) not in range(1, n + 1) for k in item["letters"]):
        return None
    return {cand: {"rank": r[k], "close": E.CLOSE_VALUE.get(c.get(k))} for k, g in item["letters"].items() for cand in g}


def pref(heard, a, b):
    """a over b: 1 above, 0 below, 0.5 tied."""
    x, y = heard[a]["rank"], heard[b]["rank"]
    return 1.0 if x < y else 0.0 if x > y else 0.5


def same_letter(item, a, b):
    return any(a in g and b in g for g in item["letters"].values())


def sign_p(k, n):
    """One-sided sign test: P(X >= k) for X ~ Binomial(n, 1/2); 1 when n is 0 (pure)."""
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def reading(lo, hi):
    if lo is not None and lo > 0.5:
        return HEARD_ABOVE
    if hi is not None and hi < 0.5:
        return HEARD_BELOW
    return NOT_KNOWN


def mean_interval(pairs):
    """(cluster, value) -> the mean with its 90% delete-one-cluster jackknife t interval (`score_ear.interval`)."""
    from learn import pretrain_set as PS
    from learn import score_ear as SE

    return SE.interval(pairs, PS.t90)


def pair_row(cards, a, b):
    """One pair's row on the cards that hold both on different letters (pure apart from the interval helpers). cards:
    [{id, cluster, heard, j0, item}]."""
    from learn import score_ear as SE

    use = [c for c in cards if not same_letter(c["item"], a, b)]
    pr = [(c["cluster"], pref(c["heard"], a, b)) for c in use]
    iv = mean_interval(pr) if pr else None
    lo, hi = (iv or {}).get("lo"), (iv or {}).get("hi")
    above, below = sum(v == 1.0 for _, v in pr), sum(v == 0.0 for _, v in pr)
    ties = len(pr) - above - below
    read = reading(lo, hi)
    p_above, p_below = sign_p(above, above + below), sign_p(below, above + below)
    jt = SE.jackknife_t(pr) if pr else {"p": None}
    j0 = [(c["cluster"], math.log(c["j0"][a] / c["j0"][b])) for c in use]
    j0_iv = mean_interval(j0) if j0 else None
    cl = [(c["cluster"], c["heard"][a]["close"] - c["heard"][b]["close"]) for c in use
          if c["heard"][a]["close"] is not None and c["heard"][b]["close"] is not None]
    untied = [(v, j) for (_, v), (_, j) in zip(pr, j0) if v != 0.5]
    return {"pair": f"{a} over {b}", "cards": len(pr), "same_letter": len(cards) - len(use),
            "share": iv["mean"] if iv else None, "lo90": lo, "hi90": hi, "clusters": (iv or {}).get("clusters"),
            "above": above, "ties": ties, "below": below, "untied": above + below,
            "sign_p_above": p_above, "sign_p_below": p_below, "reading": read,
            "firmly": (read == HEARD_ABOVE and p_above <= SIGN_ALPHA and "above") or
                      (read == HEARD_BELOW and p_below <= SIGN_ALPHA and "below") or None,
            "p_two_sided": None if jt.get("p") is None else min(1.0, 2 * min(jt["p"], 1 - jt["p"])),
            "j0_mean": j0_iv["mean"] if j0_iv else None, "j0_lo90": (j0_iv or {}).get("lo"),
            "j0_hi90": (j0_iv or {}).get("hi"), "j0_first_closer": sum(v < 0 for _, v in j0),
            "j0_agrees_untied": sum((j < 0) == (v == 1.0) for v, j in untied),
            "closeness_gap": (mean_interval(cl) or {}).get("mean") if cl else None,
            "closeness_lo90": (mean_interval(cl) or {}).get("lo") if cl else None,
            "closeness_hi90": (mean_interval(cl) or {}).get("hi") if cl else None, "closeness_rated": len(cl)}


def holm(ps):
    """{name: p} -> {name: Holm-adjusted p} (None stays None)."""
    named = sorted((p, k) for k, p in ps.items() if p is not None)
    out, run = {k: None for k in ps}, 0.0
    m = len(named)
    for i, (p, k) in enumerate(named):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def card_pairs(c, drop=()):
    """The card's candidate pairs on different letters, candidates in `drop` left out: [(a, b)] with a before b in CANDS."""
    cs = [x for x in CANDS if x in c["heard"] and x not in drop]
    return [(a, b) for i, a in enumerate(cs) for b in cs[i + 1:] if not same_letter(c["item"], a, b)]


def a1_rows(cards, drop=()):
    """A1, heard-pair agreement (S12's measure): over pairs the ear did not tie, the share J0 orders the ear's way, pooled
    over cards by pairs with the cluster jackknife interval; the fixed order's agreement on the same pairs (a fixed tie
    a half) and J0's less it (A3). -> {j0, fixed, j0_less_fixed, pairs}."""
    j, f, d = [], [], []
    for c in cards:
        for a, b in card_pairs(c, drop):
            p = pref(c["heard"], a, b)
            if p == 0.5:
                continue
            ear_a = p == 1.0
            agree = float((c["j0"][a] < c["j0"][b]) == ear_a)
            fx = 0.5 if FIXED[a] == FIXED[b] else float((FIXED[a] < FIXED[b]) == ear_a)
            j.append((c["cluster"], agree))
            f.append((c["cluster"], fx))
            d.append((c["cluster"], agree - fx))
    return {"pairs": len(j), "j0": mean_interval(j) if j else None, "fixed": mean_interval(f) if f else None,
            "j0_less_fixed": mean_interval(d) if d else None}


def a2_rows(cards, drop=()):
    """A2, order within a card (N11's row 1): Spearman of the ear's ranks (ties averaged) and J0 per card over its letter
    groups, the mean over cards; the fixed order's the same way and J0's less it (A3). A card ranked all equal has no
    order and is counted apart."""
    from learn import score_ear as SE

    j, f, d, flat = [], [], [], 0
    for c in cards:
        gs = [[x for x in g if x not in drop] for g in c["item"]["letters"].values()]
        gs = [g for g in gs if g]
        if len(gs) < 3:
            continue
        ear = [c["heard"][g[0]]["rank"] for g in gs]
        if len(set(ear)) == 1:
            flat += 1
            continue
        rj = SE.spearman(ear, [c["j0"][g[0]] for g in gs])
        rf = SE.spearman(ear, [statistics.mean(FIXED[x] for x in g) for g in gs])
        if rj is not None:
            j.append((c["cluster"], rj))
        if rf is not None:
            f.append((c["cluster"], rf))
        if rj is not None and rf is not None:
            d.append((c["cluster"], rj - rf))
    return {"cards": len(j), "all_equal": flat, "j0": mean_interval(j) if j else None,
            "fixed": mean_interval(f) if f else None, "j0_less_fixed": mean_interval(d) if d else None}


def a4_rows(cards):
    """A4, by the size of J0's gap: every pair binned by |ln ratio| (under 0.05, 0.05 to 0.15, over), the tie rate and
    the agreement on untied pairs. Descriptive."""
    bins = {}
    for c in cards:
        for a, b in card_pairs(c):
            g = abs(math.log(c["j0"][a] / c["j0"][b]))
            name = "under 0.05" if g < GAP_BINS[0] else "0.05 to 0.15" if g < GAP_BINS[1] else "0.15 and over"
            row = bins.setdefault(name, {"pairs": 0, "ties": 0, "untied": 0, "agree": 0})
            p = pref(c["heard"], a, b)
            row["pairs"] += 1
            if p == 0.5:
                row["ties"] += 1
            else:
                row["untied"] += 1
                row["agree"] += int((c["j0"][a] < c["j0"][b]) == (p == 1.0))
    for row in bins.values():
        row["tie_rate"] = row["ties"] / row["pairs"]
        row["agreement"] = row["agree"] / row["untied"] if row["untied"] else None
    return bins


def a5_rows(items, heard):
    """A5, the repeats: of each repeated card's pairs, how many the listener ordered the same twice."""
    out = []
    for it in items:
        if it["repeat_of"] and heard.get(it["id"]) and heard.get(it["repeat_of"]):
            h0, h1 = heard[it["repeat_of"]], heard[it["id"]]
            cs = [x for x in CANDS if x in h0]
            prs = [(a, b) for i, a in enumerate(cs) for b in cs[i + 1:] if not same_letter(it, a, b)]
            out.append({"id": it["id"], "repeat_of": it["repeat_of"], "pairs": len(prs),
                        "same": sum(pref(h0, a, b) == pref(h1, a, b) for a, b in prs)})
    return out


def outcome(ranked, rows, a1_hi, min_ranked=MIN_RANKED):
    """The declared outcome table, the first row that holds (pure). ranked: first hearings ranked (each sitting's, a
    list when pooled); rows: {"a over b": {reading, firmly}} for every KEY_PAIRS pair; a1_hi: the upper end of A1's
    interval without the label, or None. -> {letter, row, named, text}."""
    need = [f"{a} over {b}" for a, b in KEY_PAIRS]
    missing = [n for n in need if n not in rows]
    if missing:
        raise SystemExit(f"the read lacks {missing}")
    rk = ranked if isinstance(ranked, (list, tuple)) else [ranked]
    if any(r < min_ranked for r in rk):
        return {"letter": "c", "row": 1, "named": [], "text": "the page failed: rows reported, nothing concluded"}
    inv = [f"{a} over {b}" for a, b in DECIDED if rows[f"{a} over {b}"]["firmly"] == "below"]
    if inv or (a1_hi is not None and a1_hi < 0.5):
        return {"letter": "b", "row": 2, "named": inv + (["A1"] if a1_hi is not None and a1_hi < 0.5 else []),
                "text": "the ear inverts the score on the named row"}
    if rows["L over S"]["reading"] != HEARD_ABOVE:
        return {"letter": "c", "row": 3, "named": ["L over S"],
                "text": "the label control not heard: page or score"}
    up = [f"{a} over {b}" for a, b in MODEL if rows[f"{a} over {b}"]["firmly"] == "above"]
    if up:
        return {"letter": "b", "row": 4, "named": up,
                "text": "the ear hears the model's preset on the product's stem closer than Cen"}
    if rows["Cen over S"]["reading"] == HEARD_ABOVE and rows["L over Cen"]["reading"] == HEARD_ABOVE:
        return {"letter": "a", "row": 5, "named": ["Cen over S", "L over Cen"],
                "text": "trusted for the three covered reads", "M over Cen": rows["M over Cen"]["reading"],
                "rc over Cen": rows["rc over Cen"]["reading"]}
    return {"letter": "c", "row": 6, "named": [n for n in ("Cen over S", "L over Cen") if rows[n]["reading"] != HEARD_ABOVE],
            "text": "not known on the named pair; the second sitting follows"}


def read_cards(items, got):
    """The first hearings the listener ranked, each with its unblinded ranks, J0 and cluster; and every item's heard."""
    heard = {it["id"]: unblind(it, got.get(it["id"])) for it in items}
    cards = [{"id": it["id"], "set": it["set"], "cls": it["cls"], "amp": it["amp"],
              "cluster": f"{it['set']}:{it['cluster']}", "heard": heard[it["id"]], "j0": it["j0"], "item": it}
             for it in items if it["repeat_of"] is None and heard[it["id"]]]
    return cards, heard


def ear_read(sittings):
    """The declared read. sittings: [(items, {id: answer})], one per sitting read (pooled when two). -> report."""
    cards, heard_all, items_all, ranked, scope = [], {}, [], [], []
    for s, (items, got) in enumerate(sittings, 1):
        cs, heard = read_cards(items, got)
        for c in cs:
            c["id"] = f"s{s}:{c['id']}"
        cards += cs
        heard_all.update({f"s{s}:{k}": v for k, v in heard.items()})
        items_all += [{**it, "id": f"s{s}:{it['id']}", "repeat_of": it["repeat_of"] and f"s{s}:{it['repeat_of']}"}
                      for it in items]
        ranked.append(len(cs))
        scope += [f"s{s}:{it['id']}" for it in items if (got.get(it["id"]) or {}).get("scope")]
    rows = {f"{a} over {b}": pair_row(cards, a, b) for a, b in KEY_PAIRS + BESIDE_PAIRS}
    adj = holm({f"{a} over {b}": rows[f"{a} over {b}"]["p_two_sided"] for a, b in KEY_PAIRS})
    for k, v in adj.items():
        rows[k]["holm_p"] = v
    split = {}
    for name, keep in (("deciding sets", lambda c: c["set"] in DECIDING),
                       *((f"set {s}", (lambda s_: lambda c: c["set"] == s_)(s)) for s in SETS),
                       *((f"class {k}", (lambda k_: lambda c: c["cls"] == k_)(k)) for k in CLASSES),
                       *((f"amp {a}", (lambda a_: lambda c: c["amp"] == a_)(a)) for a in sorted({c["amp"] for c in cards}))):
        sub = [c for c in cards if keep(c)]
        split[name] = {f"{a} over {b}": pair_row(sub, a, b) for a, b in KEY_PAIRS} if sub else None
    a1 = {"labels out": a1_rows(cards, drop=("L",)), "labels in": a1_rows(cards)}
    a1_hi = ((a1["labels out"]["j0"]) or {}).get("hi")
    out = outcome(ranked, rows, a1_hi)
    return {"ranked": ranked, "items": len(items_all), "scope_marked": scope, "rows": rows, "split": split,
            "A1": a1, "A2": {"all": a2_rows(cards), "labels out": a2_rows(cards, drop=("L",))}, "A4": a4_rows(cards),
            "A5": a5_rows(items_all, heard_all), "outcome": out,
            "times": {k: {f: (v or {}).get(f) for f in ("t_play", "t_last")} for k, v in
                      ((f"s{s}:{i}", a) for s, (_, got) in enumerate(sittings, 1) for i, a in got.items())}}


def load_answers(paths, builds):
    """Each part's stored answers (`answers/<build>` or the Export text) -> one {id: answer}; every part's build checked."""
    from learn import ear_eat as EE

    got, seen = {}, set()
    for p in paths:
        ex = EE.stored_answers(pathlib.Path(p).read_text())
        if ex.get("build") not in builds.values():
            raise SystemExit(f"{p}: build {ex.get('build')} is none of this sitting's {sorted(builds.values())}")
        seen.add(ex["build"])
        got.update(ex["answers"])
    if seen != set(builds.values()):
        raise SystemExit(f"answers for {sorted(seen)}, the sitting's parts are {sorted(builds.values())}")
    return got


def cmd_read(args):
    """The declared read, once: sitting 1 alone, or sitting 2 pooled with sitting 1 -> ladder/ear/read-<s>.json, the raw
    answers kept beside."""
    import shutil

    from learn import pipeline_fix as P

    require_draw()
    s = args.sitting
    rp = ear_dir() / f"read-{s}.json"
    if rp.exists():
        raise SystemExit(f"{rp} exists: the sitting is read once")
    key = json.loads((ear_dir() / f"key-{s}.json").read_text())
    builds = {int(k): v for k, v in key["builds"].items()}
    got = load_answers(args.answers, builds)
    raw = ear_dir() / "answers"
    raw.mkdir(parents=True, exist_ok=True)
    for p in args.answers:
        shutil.copy2(p, raw / f"sitting-{s}-{pathlib.Path(p).name}")
    P.save(raw / f"sitting-{s}.json", {"builds": builds, "answers": got})
    sittings = [(key["items"], got)]
    if s == 2:
        k1 = json.loads((ear_dir() / "key-1.json").read_text())
        sittings.insert(0, (k1["items"], json.loads((raw / "sitting-1.json").read_text())["answers"]))
    for items, _ in sittings:
        for it in items:
            it["letters"] = {k: tuple(v) for k, v in it["letters"].items()}
    rep = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "sitting": s, "pooled": s == 2, **ear_read(sittings),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(rp, rep)
    print(json.dumps({"ranked": rep["ranked"], "outcome": rep["outcome"],
                      "rows": {k: {f: v[f] for f in ("share", "lo90", "hi90", "above", "ties", "below", "reading", "firmly")}
                               for k, v in rep["rows"].items() if tuple(k.split(" over ")) in KEY_PAIRS}}, indent=1))
    print(f"record in the ledger's {PHASE_OUT}: {rp.name} sha256 {file_sha(rp)}")


# --- the power simulation (declared figures; numpy) ---------------------------------------------------------------------

def sim_prefs(rng, draws, n, share, tie):
    """draws x n card preferences: a tie (0.5) at rate `tie`, else 1 or 0 so the expected share is `share`."""
    import numpy as np

    q = (share - 0.5 * tie) / (1 - tie) if tie < 1 else 0.5
    if not 0 <= q <= 1:
        raise ValueError(f"share {share} can't hold a tie rate of {tie}")
    u = rng.random((draws, n))
    v = rng.random((draws, n))
    return np.where(u < tie, 0.5, np.where(v < q, 1.0, 0.0))


def sim_read(x):
    """Each draw's reading of one pair (independent cards, one a cluster, so the jackknife t is the plain t): {lo, hi,
    above, below, firm_above, firm_below} as arrays."""
    import numpy as np

    from learn import pretrain_set as PS

    n = x.shape[1]
    m = x.mean(1)
    sd = x.std(1, ddof=1)
    h = PS.t90(n - 1) * sd / math.sqrt(n)
    lo, hi = m - h, m + h
    up, down = (x == 1.0).sum(1), (x == 0.0).sum(1)
    tail = np.array([[sign_p(k, t) if k <= t else 1.0 for k in range(n + 1)] for t in range(n + 1)])
    pa, pb = tail[up + down, up], tail[up + down, down]
    above, below = lo > 0.5, hi < 0.5
    return {"lo": lo, "hi": hi, "above": above, "below": below,
            "firm_above": above & (pa <= SIGN_ALPHA), "firm_below": below & (pb <= SIGN_ALPHA)}


def sim_outcome(r):
    """`outcome` rows 2 to 6 per draw on simulated readings (row 1 and A1 not simulated). r: {pair: sim_read}. -> array
    of "a", "b", "c"."""
    import numpy as np

    b2 = r["L over S"]["firm_below"] | r["Cen over S"]["firm_below"] | r["L over Cen"]["firm_below"]
    c3 = ~r["L over S"]["above"]
    b4 = r["M over Cen"]["firm_above"] | r["rc over Cen"]["firm_above"]
    a5 = r["Cen over S"]["above"] & r["L over Cen"]["above"]
    return np.where(b2, "b", np.where(c3, "c", np.where(b4, "b", np.where(a5, "a", "c"))))


def sim_scenario(rng, draws, shares, ties, n=22):
    """Both looks as declared: the first sitting's n cards, then, after a (c), the pooled 2n. shares, ties: {pair: value}
    for the five KEY_PAIRS. -> {first, declared, forced} shares of "a" and "b"."""
    import numpy as np

    x1 = {k: sim_prefs(rng, draws, n, shares[k], ties.get(k, 0.0)) for k in shares}
    x2 = {k: np.concatenate([x1[k], sim_prefs(rng, draws, n, shares[k], ties.get(k, 0.0))], 1) for k in shares}
    o1 = sim_outcome({k: sim_read(v) for k, v in x1.items()})
    o2 = sim_outcome({k: sim_read(v) for k, v in x2.items()})
    dec = np.where(o1 == "c", o2, o1)
    return {"first": {"a": float((o1 == "a").mean()), "b": float((o1 == "b").mean())},
            "declared": {"a": float((dec == "a").mean()), "b": float((dec == "b").mean())},
            "forced_b": float(((o1 == "b") | (o2 == "b")).mean())}


POWER_ROWS = ((0.90, 0.0), (0.80, 0.0), (0.73, 0.0), (0.70, 0.2), (0.65, 0.0), (0.50, 0.0), (0.50, 0.5), (0.50, 0.85))
NULL_TIES = (0.0, 0.2, 0.5, 0.85)       # the tie rates of the model-against-Cen pairs under no preference
CEN_SHARES = (0.70, 0.73, 0.80)


def power_tables(draws=60000, seed=SIM_SEED):
    """The declared figures: one pair's power ("heard above", "firmly above") at 22 and 44 cards; row 4's false rate;
    the combined false (b) and the odds of (a) when the score is right, both looks as declared and forced."""
    import numpy as np

    rng = np.random.default_rng(seed)
    one = []
    for share, tie in POWER_ROWS:
        row = {"share": share, "tie": tie}
        for n in (22, 44):
            r = sim_read(sim_prefs(rng, draws, n, share, tie))
            row[f"above_{n}"] = float(r["above"].mean())
            row[f"firm_above_{n}"] = float(r["firm_above"].mean())
        one.append(row)
    combined = []
    for cs in CEN_SHARES:
        for tie in NULL_TIES:
            shares = {"L over S": 0.9, "L over Cen": 0.9, "Cen over S": cs, "M over Cen": 0.5, "rc over Cen": 0.5}
            got = sim_scenario(rng, draws, shares, {"M over Cen": tie, "rc over Cen": tie})
            combined.append({"cen_share": cs, "model_tie": tie, **got})
    rng_ = {k: (min(r[k] for r in combined), max(r[k] for r in combined)) for k in ("forced_b",)}
    for look in ("first", "declared"):
        for o in ("a", "b"):
            vals = [r[look][o] for r in combined]
            rng_[f"{look}_{o}"] = (min(vals), max(vals))
    return {"draws": draws, "seed": seed, "one_pair": one, "combined": combined, "ranges": rng_}


def cmd_power(args):
    from learn import pipeline_fix as P

    out = power_tables(args.draws)
    P.save(ear_dir() / "power.json", out)
    for r in out["one_pair"]:
        print(f"share {r['share']:.2f} tie {r['tie']:.2f}: 22 cards {r['above_22']:.3f} (firmly {r['firm_above_22']:.3f}); "
              f"44 cards {r['above_44']:.3f} (firmly {r['firm_above_44']:.3f})")
    for k, (a, b) in out["ranges"].items():
        print(f"{k}: {a:.3f} to {b:.3f}")


def shard(s):
    a, b = s.split("/")
    return int(a), int(b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("draw").set_defaults(fn=cmd_draw)
    r = sub.add_parser("render")
    r.add_argument("--shard", type=shard, default=(0, 1))
    r.set_defaults(fn=cmd_render)
    pg = sub.add_parser("page")
    pg.add_argument("--sitting", type=int, choices=(1, 2), required=True)
    pg.set_defaults(fn=cmd_page)
    rd = sub.add_parser("read")
    rd.add_argument("--sitting", type=int, choices=(1, 2), required=True)
    rd.add_argument("--answers", nargs="+", required=True)
    rd.set_defaults(fn=cmd_read)
    pw = sub.add_parser("power")
    pw.add_argument("--draws", type=int, default=60000)
    pw.set_defaults(fn=cmd_power)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
