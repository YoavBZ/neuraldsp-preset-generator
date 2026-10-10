#!/usr/bin/env python3
"""Listening check H: on heavy tones, which part of the judge does the ear follow?

Declared in `docs/heavy-listening-plan.md` (finding 8 and the decisions of
`docs/closeness-review-2026-10-10.md`).

    .venv/bin/python -m learn.build_heavy_listening count     # counts only, no pair named
    .venv/bin/python -m learn.build_heavy_listening build     # trials, audio, private key
    .venv/bin/python -m learn.build_heavy_listening phone     # one phone page per sitting
    .venv/bin/python -m learn.build_heavy_listening check --answers SHEET   # public check
    .venv/bin/python -m learn.build_heavy_listening score --answers SHEET   # after its hash is committed

Nothing is rendered: every option is a stored `measfix` render of `learn/set3_gap_split.py`
(the measure DI at −22.9 LUFS through every menu preset), development parts only.
`count` and `build` first compute, once, the judge's three numbers (distance, tonal,
temporal) on half B for every menu preset, cached beside the outputs, and check the
distance against the stored one.

As in `learn/build_avg_listening.py`, whose audio, sheet and phone helpers are reused:
the listener's folder holds numbered trial files only; the key is `private/trials.json`,
its sha256 is recorded in the plan and the scorer refuses any other key; the scorer
records the answer sheet's sha256 before it reads the key and refuses a different sheet.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import pathlib
import random
import re
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))
sys.path.append(str(PLUGIN_ROOT / "scripts"))

from _cli import die, guarded  # noqa: E402
from learn import build_avg_listening as L  # noqa: E402

HOME = pathlib.Path(os.path.expanduser("~/ndsp-presets"))
CROPS = HOME / "references" / "validation-crops-set3"
GAP = HOME / "learn" / "direc" / "gap-split"
MEASFIX = GAP / "measfix"
LP3K = HOME / "learn" / "direc" / "v2-eval" / "lp3k" / "distances.json"
OUT = HOME / "listening" / "heavy"
PLAN = PLUGIN_ROOT / "docs" / "heavy-listening-plan.md"
ANSWERS_SHA = PLUGIN_ROOT / "docs" / "heavy-listening-answers.sha256"

SR, LATENCY = L.SR, L.LATENCY
HALF_B = L.HALF_B                       # (5.5, 10.0)
BANDS = "recording"
SEED = 20261010
AMPS = ("pr12", "sw50r", "ac20")
DRIVEN_PARTS = ("crunch", "high-gain")  # set-3 gain_class
CONSTANT = {"pr12": "factory:Neural DSP/Vintage Metal",
            "sw50r": "factory:Artists/Royce Whittaker/Wall Of Doom",
            "ac20": "factory:Artists/Charlie Robbins/Dirty Coil Rhythm"}
PICKS = ("lp3k", "net", "oracle")       # the choosers whose picks meet the constant

CONFLICT = 0.10                         # block 1: tonal and temporal opposite, each >= this
CLEAR = 0.15                            # block 2: judge |log ratio| above this
SMALL = (0.03, 0.08)                    # block 3: judge |log ratio| within this
TEXTURE, CLEAR_N, SMALL_N, HIDDEN, REPEATS = 16, 10, 4, 3, 3
CLEAR_QUOTA = {"sw50r": 5, "ac20": 5}   # block 2: >= 4 each declared; 5 and 5 built
PER_PART, PER_BAND = 2, 6
MIN_BANDS = 16                          # judge v2's refusal: fewer scored bands is treble-deaf
EXPOSED = 0.9
SITTING = L.SITTING                     # 18
# Sitting 1: 9 texture (3 to be repeated), 5 clear, 2 small, 2 hidden references.
# Sitting 2: 7 texture, 5 clear, 2 small, 1 hidden reference, 3 repeats.
SPLIT = {"texture": (9, 7), "clear": (5, 5), "small": (2, 2), "hidden": (2, 1)}
# Outcomes (the plan): block 1 at >= 12 of 16 either way; block 2 >= 8 or <= 5 of 10;
# void on 2+ hidden references missed or fewer than 2 of 3 repeats the same.
SIDE, CLEAR_PASS, CLEAR_FAIL, MAX_HIDDEN_MISSED, MIN_CONSISTENT = 12, 8, 5, 1, 2


def sha256(path) -> str:
    return L.sha256(path)


def slug_of(name: str) -> str:
    return hashlib.sha1(name.encode()).hexdigest()[:12]      # render_preset_panel._slug


def render_path(part: str, amp: str, name: str) -> pathlib.Path:
    return MEASFIX / part / amp / f"{slug_of(name)}.flac"


def parts() -> dict:
    """{slug: declaration row} for the crunch and high-gain development parts."""
    from learn import set3

    return {p["slug"]: p for p in set3.parts("development") if p["gain_class"] in DRIVEN_PARTS}


def provenance() -> dict:
    from learn import set3

    return {"set3": sha256(set3.DECLARATION), "gap_split_distances": sha256(GAP / "distances.json"),
            "lp3k_distances": sha256(LP3K)}


# --- step 1: the judge's three numbers on half B -----------------------------------

def measure_part(job):
    import numpy as np

    import kill_tests as K
    from analysis.aligned import aligned_distance

    part, lag, names = job
    ref, di = L.mono(CROPS / part / "reference.wav"), np.load(MEASFIX / part / "di.npy")
    out = {"exposure": K.active_fraction(di, *HALF_B), "bands": None}
    for amp, ns in names.items():
        row = {}
        for n in ns:
            r = aligned_distance(ref, L.mono(render_path(part, amp, n)), di, lag=lag,
                                 render_latency=LATENCY, start_s=HALF_B[0], end_s=HALF_B[1],
                                 bands=BANDS)
            row[n] = None if r.distance is None else {"distance": r.distance, "tonal": r.tonal,
                                                      "temporal": r.temporal}
            if r.distance is not None:
                out["bands"] = r.bands      # recording bands: the recording's alone
        out[amp] = row
    print(part, flush=True)
    return part, out


def components() -> dict:
    """{part: {"exposure": share, amp: {name: {distance, tonal, temporal} | None}}}, cached;
    the distance must equal the stored `measfix_B` one."""
    cache = OUT / "work" / "components.json"
    prov = provenance()
    if cache.exists():
        cached = json.loads(cache.read_text())
        if cached["provenance"] != prov:
            die(f"{cache} was computed from other inputs; move it aside")
        return cached["parts"]
    from concurrent.futures import ProcessPoolExecutor

    ps = parts()
    stored = json.loads((GAP / "distances.json").read_text())
    names = {p: {a: sorted(stored[p][f"{BANDS}|{a}|measfix_B"]) for a in AMPS} for p in ps}
    with ProcessPoolExecutor(6) as ex:
        res = dict(ex.map(measure_part, [(p, ps[p]["judge_lag_samples"], names[p])
                                         for p in sorted(ps)]))
    worst = 0.0
    for p in ps:
        for a in AMPS:
            for n, v in stored[p][f"{BANDS}|{a}|measfix_B"].items():
                mine = res[p][a][n]
                if (v is None) != (mine is None):
                    die(f"{p} {a} {n}: scored here and not stored, or the reverse")
                if v is not None:
                    worst = max(worst, abs(math.log(mine["distance"] / v)))
    if worst > 1e-6:
        die(f"recomputed distances differ from the stored ones (worst {worst:.2e} log)")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"provenance": prov, "max_log_deviation_from_stored": worst,
                                 "parts": res}, indent=1) + "\n")
    return res


# --- step 2: presets, picks and pairs ------------------------------------------------

def driven_preset(name: str, amp: str) -> bool:
    """A factory preset that is not clean (`listening_check.gain_class`) and not for bass."""
    import listening_check as LC
    import render_preset_panel as RP

    if not name.startswith("factory:") or re.search(r"\bbass\b", name, re.I):
        return False
    return LC.gain_class(RP.FACTORY / (name[len("factory:"):] + ".xml"), amp) != "clean"


def argmin(row: dict):
    row = {n: v for n, v in row.items() if v}
    return min(row, key=lambda n: (row[n], n)) if row else None


def picks() -> dict:
    """{part: {amp: {chooser: preset}}}: the low-pass and network picks (half A of
    `v2-eval/lp3k`) and the true-DI oracle at the fixed level (half A of `measfix`)."""
    lp = json.loads(LP3K.read_text())
    gs = json.loads((GAP / "distances.json").read_text())
    return {p: {a: {"lp3k": argmin(lp[p][f"{BANDS}|{a}|lp3k_A"]),
                    "net": argmin(lp[p][f"{BANDS}|{a}|net_A"]),
                    "oracle": argmin(gs[p][f"{BANDS}|{a}|measfix_A"])} for a in AMPS}
            for p in parts()}


def pair(part, band, amp, c1, c2, comp, exposure, source):
    v1, v2 = comp[c1], comp[c2]
    return {"part": part, "band": band, "amp": amp, "first": c1, "second": c2,
            "source": source, "exposure": exposure,
            "log_ratio": {k: math.log(v1[k] / v2[k]) for k in ("distance", "tonal", "temporal")}}


def pools(comp, decl, chosen_by, driven) -> tuple:
    """(pick pairs, menu pairs): each pick against its amp's constant; every pair of
    driven menu presets."""
    pick_pool, menu_pool = {}, []
    for p in sorted(comp):
        for a in AMPS:
            row = comp[p][a]
            const = CONSTANT[a]
            for kind in PICKS:
                n = chosen_by[p][a][kind]
                if n is None or n == const or not row.get(n) or not row.get(const):
                    continue
                key = (p, a, n)
                if key in pick_pool:
                    pick_pool[key]["source"] += "+" + kind
                else:
                    pick_pool[key] = pair(p, decl[p]["band"], a, n, const, row,
                                          comp[p]["exposure"], "pick:" + kind)
            ok = sorted(n for n, v in row.items() if v and n in driven[a])
            menu_pool += [pair(p, decl[p]["band"], a, c1, c2, row, comp[p]["exposure"], "menu")
                          for c1, c2 in itertools.combinations(ok, 2)]
    return list(pick_pool.values()), menu_pool


def conflict(q) -> bool:
    """Block 1: the tonal and temporal parts disagree, each by >= CONFLICT."""
    t, m = q["log_ratio"]["tonal"], q["log_ratio"]["temporal"]
    return abs(t) >= CONFLICT and abs(m) >= CONFLICT and t * m < 0


def clear(q) -> bool:
    return abs(q["log_ratio"]["distance"]) > CLEAR and not conflict(q)


def small(q) -> bool:
    return SMALL[0] <= abs(q["log_ratio"]["distance"]) <= SMALL[1] and not conflict(q)


def select(cands, quota, state, rank):
    """Round-robin over amps (quota {amp: n}, or {None: n} for any amp), each amp taking its
    best fitting pair by `rank`; at most PER_PART trials a part and PER_BAND a band over the
    whole test, no pair twice."""
    cands = sorted(cands, key=rank)
    per_part, per_band, used = state
    left = dict(quota)
    chosen = []

    def fits(q):
        return (per_part.get(q["part"], 0) < PER_PART and per_band.get(q["band"], 0) < PER_BAND
                and (q["part"], q["amp"], *sorted((q["first"], q["second"]))) not in used)

    def take(q):
        chosen.append(q)
        per_part[q["part"]] = per_part.get(q["part"], 0) + 1
        per_band[q["band"]] = per_band.get(q["band"], 0) + 1
        used.add((q["part"], q["amp"], *sorted((q["first"], q["second"]))))

    if None in left:
        n = left.pop(None)
        while len(chosen) < n:
            best = {}
            for q in cands:
                if fits(q) and q["amp"] not in best:
                    best[q["amp"]] = q
            if not best:
                break
            for amp in sorted(best, key=lambda a: rank(best[a])):
                q = next((x for x in cands if x["amp"] == amp and fits(x)), None)
                if q is not None and len(chosen) < n:
                    take(q)
        return chosen
    while any(left.values()):
        progressed = False
        for amp in sorted(left):
            if not left[amp]:
                continue
            q = next((x for x in cands if x["amp"] == amp and fits(x)), None)
            if q is not None:
                take(q)
                left[amp] -= 1
                progressed = True
        if not progressed:
            break
    return chosen


def choose(pick_pool, menu_pool, comp, decl):
    """The four blocks, deterministic in SEED: texture (16, picks against the constant
    first, then menu pairs), clear (5 SW50R, 5 AC20), small (4), hidden references (3,
    one per amp), and which 3 texture trials are repeated."""
    rng = random.Random(SEED)
    tie = {}

    def t(q):
        return tie.setdefault(id(q), rng.random())

    state = ({}, {}, set())
    exposed = lambda q: q["exposure"] < EXPOSED  # noqa: E731

    def by_conflict(q):
        return (exposed(q), -min(abs(q["log_ratio"]["tonal"]), abs(q["log_ratio"]["temporal"])),
                t(q))

    texture = select([q for q in pick_pool if conflict(q)], {None: TEXTURE}, state, by_conflict)
    if len(texture) < TEXTURE:
        texture += select([q for q in menu_pool if conflict(q)], {None: TEXTURE - len(texture)},
                          state, by_conflict)
    rand = lambda q: (exposed(q), t(q))  # noqa: E731
    clear_ = select([q for q in menu_pool if clear(q)], CLEAR_QUOTA, state, rand)
    small_ = select([q for q in menu_pool if small(q)], {None: SMALL_N}, state, rand)
    hidden = []
    per_part, per_band, _ = state
    for amp in AMPS:
        ok = [p for p in sorted(comp) if per_part.get(p, 0) < PER_PART
              and per_band.get(decl[p]["band"], 0) < PER_BAND and comp[p][amp].get(CONSTANT[amp])
              and p not in {h["part"] for h in hidden}]
        ok.sort(key=lambda p: (comp[p]["exposure"] < EXPOSED, rng.random()))
        if ok:
            p = ok[0]
            hidden.append({"part": p, "band": decl[p]["band"], "amp": amp,
                           "first": "reference", "second": CONSTANT[amp], "source": "hidden",
                           "exposure": comp[p]["exposure"], "log_ratio": None})
            per_part[p] = per_part.get(p, 0) + 1
            per_band[decl[p]["band"]] = per_band.get(decl[p]["band"], 0) + 1
    repeated = sorted(rng.sample(range(len(texture)), min(REPEATS, len(texture))))
    return {"texture": texture, "clear": clear_, "small": small_, "hidden": hidden}, repeated


def tally(qs) -> dict:
    out = {"pairs": len(qs), "parts": len({q["part"] for q in qs}),
           "bands": len({q["band"] for q in qs})}
    for a in AMPS:
        out[a] = sum(q["amp"] == a for q in qs)
    return out


def everything():
    decl = parts()
    comp = components()
    deaf = sorted(p for p in comp if comp[p]["bands"] < MIN_BANDS)
    comp = {p: v for p, v in comp.items() if p not in deaf}
    driven = {a: {n for n in comp[next(iter(comp))][a] if driven_preset(n, a)} for a in AMPS}
    pick_pool, menu_pool = pools(comp, decl, picks(), driven)
    blocks, repeated = choose(pick_pool, menu_pool, comp, decl)
    qualifying = {"texture_picks": tally([q for q in pick_pool if conflict(q)]),
                  "texture_menu": tally([q for q in menu_pool if conflict(q)]),
                  "clear": tally([q for q in menu_pool if clear(q)]),
                  "small": tally([q for q in menu_pool if small(q)]),
                  "pick_pairs": tally(pick_pool), "menu_pairs": tally(menu_pool),
                  "driven_presets": {a: len(driven[a]) for a in AMPS},
                  "parts": len(comp), "parts_dropped_under_min_bands": len(deaf)}
    return decl, comp, blocks, repeated, qualifying


def short(blocks) -> list:
    need = {"texture": TEXTURE, "clear": CLEAR_N, "small": SMALL_N, "hidden": HIDDEN}
    out = [f"{k} {len(blocks[k])} of {n}" for k, n in need.items() if len(blocks[k]) < n]
    if sum(q["amp"] == "sw50r" for q in blocks["clear"]) < 4 or \
            sum(q["amp"] == "ac20" for q in blocks["clear"]) < 4:
        out.append("clear: fewer than 4 on SW50R or AC20")
    return out


def count(args):
    _, comp, blocks, repeated, qualifying = everything()
    print(f"parts: {len(comp)} crunch and high-gain development parts with >= {MIN_BANDS} "
          f"scored bands ({qualifying['parts_dropped_under_min_bands']} dropped)")
    for k, v in qualifying.items():
        print(f"qualifying {k}: {v}")
    for k, qs in blocks.items():
        print(f"choosable {k}: {tally(qs)}"
              + (f"; from picks {sum(q['source'] != 'menu' for q in qs)}" if k == "texture" else ""))
    if short(blocks):
        print("SHORT: " + "; ".join(short(blocks)))


# --- build ---------------------------------------------------------------------------

def order(blocks, repeated, rng):
    """Two sittings of 18 (SPLIT), the repeated trials' originals in the first and their
    repeats in the second; no part twice in a row within a sitting."""
    first, second = [], []
    tex = [("texture", i) for i in range(len(blocks["texture"])) if i not in repeated]
    rng.shuffle(tex)
    originals = [("texture", i) for i in repeated]
    n1 = SPLIT["texture"][0] - len(originals)
    first += originals + tex[:n1]
    second += tex[n1:] + [("repeat", i) for i in repeated]
    for kind in ("clear", "small", "hidden"):
        items = [(kind, i) for i in range(len(blocks[kind]))]
        rng.shuffle(items)
        if kind == "clear":       # 5 and 5 within each amp's share, as near as can be
            items.sort(key=lambda x: blocks[kind][x[1]]["amp"])
            items = items[0::2] + items[1::2]
        first += items[:SPLIT[kind][0]]
        second += items[SPLIT[kind][0]:]

    def part(x):
        return blocks["texture" if x[0] == "repeat" else x[0]][x[1]]["part"]

    for block in (first, second):
        for _ in range(10000):
            rng.shuffle(block)
            if all(part(x) != part(y) for x, y in zip(block, block[1:])):
                break
        else:
            die("could not order a sitting without a part twice in a row")
    return first, second


def build(args):
    import secrets

    decl, comp, blocks, repeated, qualifying = everything()
    if short(blocks):
        die("cannot build as declared: " + "; ".join(short(blocks))
            + "; amend the plan, do not lower the bar here")
    listen, private = OUT / "listen", OUT / "private"
    for folder in (listen, private):
        if folder.exists() and any(folder.iterdir()):
            die(f"{folder} is not empty; the trials are built once")
        folder.mkdir(parents=True, exist_ok=True)
    rng = secrets.SystemRandom()
    first, second = order(blocks, repeated, rng)
    # Balanced A/B: the tonal-closer option is A on half the texture trials, the judge's
    # option on half the clear and small trials; the reference copy's side is drawn.
    lead_a = set()
    for kind in ("texture", "clear", "small"):
        n = len(blocks[kind])
        lead_a |= {(kind, i) for i in rng.sample(range(n), n // 2)}
    lead_a |= {("hidden", i) for i in range(HIDDEN) if rng.random() < 0.5}
    rows = []
    for sitting, seq in ((1, first), (2, second)):
        for kind, i in seq:
            src = "texture" if kind == "repeat" else kind
            q = blocks[src][i]
            if kind == "hidden":
                lead, other = "reference", q["second"]
            else:
                # The lead option: the tonal-closer one in block 1, the judge's in 2 and 3.
                m = "tonal" if src == "texture" else "distance"
                lead = q["first"] if q["log_ratio"][m] < 0 else q["second"]
                other = q["second"] if lead == q["first"] else q["first"]
            a_is_lead = ((kind, i) in lead_a if kind != "repeat"
                         else ("texture", i) not in lead_a)
            r = {"trial": len(rows) + 1, "sitting": sitting, "block": kind,
                 "id": {"texture": "t", "clear": "c", "small": "s", "hidden": "h",
                        "repeat": "r"}[kind] + f"{i:02d}",
                 "part": q["part"], "band": q["band"], "amp": q["amp"],
                 "lag": decl[q["part"]]["judge_lag_samples"],
                 "gain_class": decl[q["part"]]["gain_class"], "exposure": q["exposure"],
                 "source": q["source"],
                 "A": lead if a_is_lead else other, "B": other if a_is_lead else lead}
            if kind == "repeat":
                r["of"] = f"t{i:02d}"
            if kind == "hidden":
                r["copy"] = "A" if a_is_lead else "B"
            else:
                sign = 1 if r["A"] == q["first"] else -1
                r["log_ratio_A_over_B"] = {k: sign * v for k, v in q["log_ratio"].items()}
                for k, label in (("distance", "judge"), ("tonal", "tonal"),
                                 ("temporal", "temporal")):
                    r[f"{label}_pick"] = "A" if r["log_ratio_A_over_B"][k] < 0 else "B"
                r["components"] = {x: comp[q["part"]][q["amp"]][r[x]] for x in "AB"}
            rows.append(r)
    clips = []
    for r in rows:
        ref_path = CROPS / r["part"] / "reference.wav"
        ref = L.mono(ref_path)
        paths = {"R": ref_path}
        xs = {}
        for x in "AB":
            if r[x] == "reference":
                continue
            paths[x] = render_path(r["part"], r["amp"], r[x])
            xs[x] = L.mono(paths[x])
        if len(xs) == 1:                      # hidden reference: the other option twice
            xs = {x: next(iter(xs.values())) for x in "AB"}
        rr, aa, bb = L.excerpt(ref, xs["A"], xs["B"], r["lag"])
        if r["block"] == "hidden":
            aa, bb = (rr, bb) if r["copy"] == "A" else (aa, rr)
        clips += [L.fade(rr), L.fade(aa), L.fade(bb)]
        r["sources"] = {k: {"path": str(v), "sha256": sha256(v)} for k, v in paths.items()}
        r["excerpt_s"] = len(rr) / SR
    target, levelled, after = L.level(clips)
    for k, r in enumerate(rows):
        rr, aa, bb = levelled[3 * k: 3 * k + 3]
        n = f"{r['trial']:02d}"
        L.write(listen / f"trial-{n}.flac", L.montage(rr, aa, bb))
        for label, x in zip("RAB", (rr, aa, bb)):
            L.write(listen / f"trial-{n}-{label}.flac", x)
        r["lufs_after"] = dict(zip("RAB", (round(v, 3) for v in after[3 * k: 3 * k + 3])))
    key = {"schema": "heavy-listening-key-v1", "plan": PLAN.name, "seed": SEED,
           "bands": BANDS, "half": HALF_B, "provenance": provenance(),
           "thresholds": {"conflict": CONFLICT, "clear": CLEAR, "small": SMALL},
           "qualifying": qualifying, "repeated": [f"t{i:02d}" for i in repeated],
           "level": {"target_lufs": round(target, 3),
                     "peak_ceiling_dbtp": L.PEAK_CEILING_DBTP, "fade_s": L.FADE_S},
           "trials": rows}
    text = json.dumps(key, indent=1) + "\n"
    (private / "trials.json").write_text(text)
    print(f"qualifying: {json.dumps(qualifying)}")
    for kind in ("texture", "clear", "small", "hidden", "repeat"):
        rs = [r for r in rows if r["block"] == kind]
        print(f"{kind}: {len(rs)} trials, " + ", ".join(
            f"{a} {sum(r['amp'] == a for r in rs)}" for a in AMPS)
            + f"; sittings {sum(r['sitting'] == 1 for r in rs)}/{sum(r['sitting'] == 2 for r in rs)}")
    print(f"built {len(rows)} trials in {listen}; target {target:.2f} LUFS")
    print(f"key sha256 {hashlib.sha256(text.encode()).hexdigest()} (record it in {PLAN.name})")


# --- phone -------------------------------------------------------------------------------

def phone_template() -> str:
    page = L.PHONE
    for old, new in (("Listening check L", "Listening check H"),
                     ('"avg-{build}', '"heavy-{build}'),
                     ("Which of A and B is closer to the Reference?",
                      "Which of A and B is closer <b>in tone</b> to the Reference? Ignore loudness: "
                      "every clip is at the same level.")):
        if old not in page:
            raise RuntimeError(f"the phone template changed: {old!r} is gone")
        page = page.replace(old, new)
    return page


def phone_leaks(page: str) -> list:
    """Names the page must not hold: any menu preset, part, band, song or amp."""
    import base64

    stored = json.loads((GAP / "distances.json").read_text())
    decl = parts()
    names = {n for p in stored for k, v in stored[p].items() if k.endswith("measfix_B") for n in v}
    words = (set(decl) | {d["band"] for d in decl.values()} | {d["song"] for d in decl.values()}
             | {seg for n in names for seg in n.split(":", 1)[-1].split("/")
                if seg not in ("Artists", "Neural DSP")})
    words = {w for w in words if len(w) >= 4}
    text_only = re.compile("|".join([r"\bAC20\b", r"\bPR12\b", r"\bSW50R\b", r"\.xml",
                                     "factory", r"template\+R", "tonal", "temporal", "judge"]
                                    + [re.escape(w) for w in sorted(words)]), re.I)
    payloads = re.findall(r"base64,([A-Za-z0-9+/=]+)", page)
    bad = sorted(set(text_only.findall(re.sub(r"base64,[A-Za-z0-9+/=]+", "", page))))
    binary = re.compile("|".join(re.escape(w) for w in sorted(words) if len(w) >= 6).encode(),
                        re.I)
    for p in payloads:
        bad += sorted({m.decode(errors="replace") for m in binary.findall(base64.b64decode(p))})
    return bad


def phone(args):
    saved = L.PHONE, L.phone_leaks
    L.PHONE, L.phone_leaks = phone_template(), phone_leaks
    try:
        L.phone(args)
    finally:
        L.PHONE, L.phone_leaks = saved


def check(args):
    sheet = args.answers.expanduser()
    answers = L.read_sheet(sheet)
    shown = L.public_trials(OUT / "listen")
    missing = sorted(set(shown) - {n for n, a in answers.items() if a})
    extra = sorted(set(answers) - set(shown))
    if missing or extra:
        die(f"the sheet does not answer exactly the built trials: missing {missing}, "
            f"extra {extra}")
    print(f"the sheet answers all {len(shown)} trials; its sha256 is {sha256(sheet)}")


# --- score -------------------------------------------------------------------------------

def declared_key_sha256() -> str:
    found = re.findall(r"`([0-9a-f]{64})`", PLAN.read_text())
    if len(found) != 1:
        die(f"{PLAN} must record exactly one key sha256")
    return found[0]


def score_rows_partial(rows, answers) -> dict:
    """The amended outcomes (plan, "Amendment: unanswered trials"): unanswered trials are
    left out, and each rule uses the exact one-sided binomial p of its original threshold."""
    answered = [r for r in rows if answers.get(r["trial"])]
    by_id = {r["id"]: r for r in rows}
    chosen = {r["trial"]: r[answers[r["trial"]]] for r in answered}
    of = {k: [r for r in answered if r["block"] == k] for k in
          ("texture", "clear", "small", "hidden", "repeat")}

    def agree(rs, field):
        return sum(answers[r["trial"]] == r[field] for r in rs)

    missed = sum(answers[r["trial"]] != r["copy"] for r in of["hidden"])
    pairs = [r for r in of["repeat"] if by_id[r["of"]]["trial"] in chosen]
    consistent = sum(chosen[r["trial"]] == chosen[by_id[r["of"]]["trial"]] for r in pairs)
    tonal, n_tex = agree(of["texture"], "tonal_pick"), len(of["texture"])
    judge, n_clear = agree(of["clear"], "judge_pick"), len(of["clear"])
    reliability = ("unassessed" if len(pairs) < 2 else "ok")
    void = missed >= 2 or (len(pairs) >= 2 and consistent < 2 * len(pairs) / 3)
    p_t, p_m = L.binomial_p(tonal, n_tex), L.binomial_p(n_tex - tonal, n_tex)
    p_j = L.binomial_p(judge, n_clear)
    outcome = {"void": void} if void else {
        "void": False,
        "texture": "tonal" if p_t <= 0.038 else "temporal" if p_m <= 0.038 else "neither",
        "clear": ("judge extends" if p_j <= 0.055 else
                  "judge not ground truth" if judge <= n_clear / 2 else "inconclusive")}
    return {"outcome": outcome, "amended": True,
            "unanswered": sorted(r["trial"] for r in rows if not answers.get(r["trial"])),
            "unanswered_by_block": {k: sum(1 for r in rows if r["block"] == k and not answers.get(r["trial"]))
                                    for k in ("texture", "clear", "small", "hidden", "repeat")},
            "reliability": {"hidden_missed": missed, "hidden_answered": len(of["hidden"]),
                            "repeat_pairs_answered": len(pairs), "repeats_consistent": consistent,
                            "status": reliability},
            "texture": {"tonal_side": tonal, "temporal_side": n_tex - tonal, "of": n_tex,
                        "p_one_sided_tonal": p_t, "p_one_sided_temporal": p_m,
                        "agree_with_judge": agree(of["texture"], "judge_pick")},
            "clear": {"agree_with_judge": judge, "of": n_clear, "p_one_sided": p_j},
            "small": {"agree_with_judge": agree(of["small"], "judge_pick"), "of": len(of["small"])},
            "answered_A": sum(a == "A" for a in answers.values() if a)}


def score_rows(rows, answers) -> dict:
    """The declared outcomes from the key's rows and {trial: "A" | "B"}."""
    chosen = {r["trial"]: r[answers[r["trial"]]] for r in rows}
    by_id = {r["id"]: r for r in rows}
    of = {k: [r for r in rows if r["block"] == k] for k in
          ("texture", "clear", "small", "hidden", "repeat")}

    def agree(rs, field):
        return sum(answers[r["trial"]] == r[field] for r in rs)

    missed = sum(answers[r["trial"]] != r["copy"] for r in of["hidden"])
    consistent = sum(chosen[r["trial"]] == chosen[by_id[r["of"]]["trial"]] for r in of["repeat"])
    tonal = agree(of["texture"], "tonal_pick")
    n_tex, n_clear = len(of["texture"]), len(of["clear"])
    judge = agree(of["clear"], "judge_pick")
    if missed > MAX_HIDDEN_MISSED or consistent < MIN_CONSISTENT:
        outcome = {"void": True}
    else:
        outcome = {"void": False,
                   "texture": ("tonal" if tonal >= SIDE else
                               "temporal" if n_tex - tonal >= SIDE else "neither"),
                   "clear": ("judge extends" if judge >= CLEAR_PASS else
                             "judge not ground truth" if judge <= CLEAR_FAIL else "inconclusive")}

    def per_amp(rs, field):
        return {a: [agree([r for r in rs if r["amp"] == a], field),
                    sum(r["amp"] == a for r in rs)] for a in AMPS}

    return {"outcome": outcome,
            "reliability": {"hidden_missed": missed, "of": len(of["hidden"]),
                            "repeats_consistent": consistent, "repeats": len(of["repeat"])},
            "texture": {"tonal_side": tonal, "temporal_side": n_tex - tonal, "of": n_tex,
                        "p_one_sided_tonal": L.binomial_p(tonal, n_tex),
                        "p_one_sided_temporal": L.binomial_p(n_tex - tonal, n_tex),
                        "agree_with_judge": agree(of["texture"], "judge_pick"),
                        "tonal_side_by_amp": per_amp(of["texture"], "tonal_pick"),
                        "tonal_side_picks_vs_constant": agree(
                            [r for r in of["texture"] if r["source"] != "menu"], "tonal_pick"),
                        "picks_vs_constant": sum(r["source"] != "menu" for r in of["texture"]),
                        "tonal_side_by_sitting": {s: agree([r for r in of["texture"]
                                                            if r["sitting"] == s], "tonal_pick")
                                                  for s in (1, 2)}},
            "clear": {"agree_with_judge": judge, "of": n_clear,
                      "p_one_sided": L.binomial_p(judge, n_clear),
                      "by_amp": per_amp(of["clear"], "judge_pick")},
            "small": {"agree_with_judge": agree(of["small"], "judge_pick"),
                      "of": len(of["small"])},
            "answered_A": sum(a == "A" for a in answers.values()),
            "per_trial": [{"trial": r["trial"], "block": r["block"], "answer": answers[r["trial"]]}
                          for r in rows]}


def score(args):
    private = OUT / "private"
    sheet = args.answers.expanduser()
    raw = sheet.read_bytes()
    answers = L.read_sheet(sheet)
    built = set(L.public_trials(OUT / "listen"))
    if args.allow_unanswered:
        if not answers or set(answers) - built:
            die("the sheet answers trials that were not built")
        answers = {t: answers.get(t) for t in built}
    else:
        if not answers or not all(answers.values()):
            die("every trial needs an answer, A or B")
        if set(answers) != built:
            die("the sheet does not answer exactly the built trials (run `check` first)")
    answers_sha = hashlib.sha256(raw).hexdigest()
    if not ANSWERS_SHA.exists() or answers_sha not in ANSWERS_SHA.read_text():
        die(f"commit this sheet's sha256 in {ANSWERS_SHA.name} first")
    recorded = private / "answers.sha256"
    if recorded.exists() and recorded.read_text().strip() != answers_sha:
        die("these answers differ from the ones already scored")
    recorded.write_text(answers_sha + "\n")
    # Only now, with the sheet's hash recorded, is the key read.
    text = (private / "trials.json").read_text()
    if hashlib.sha256(text.encode()).hexdigest() != declared_key_sha256():
        die("the key is not the one the plan declares")
    key = json.loads(text)
    if set(answers) != {r["trial"] for r in key["trials"]}:
        die("the sheet's trials are not the built trials")
    rows = score_rows_partial(key["trials"], answers) if args.allow_unanswered \
        else score_rows(key["trials"], answers)
    out = {"answers_sha256": answers_sha, **rows}
    text = json.dumps(out, indent=1) + "\n"
    print(text)
    args.json.expanduser().write_text(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("count")
    sub.add_parser("build")
    ph = sub.add_parser("phone")
    ph.add_argument("--listen-dir", type=pathlib.Path, default=OUT / "listen")
    ph.add_argument("--sitting", type=int, action="append", choices=(1, 2),
                    help="one sitting's page (default: both)")
    c = sub.add_parser("check")
    c.add_argument("--answers", type=pathlib.Path, required=True)
    s = sub.add_parser("score")
    s.add_argument("--answers", type=pathlib.Path, required=True)
    s.add_argument("--json", type=pathlib.Path, default=OUT / "score.json")
    s.add_argument("--allow-unanswered", action="store_true",
                   help="the plan's amendment: score answered trials only")
    args = ap.parse_args()
    if args.cmd in ("count", "build"):
        from analysis import require

        require("the heavy-tone listening check")
    {"count": count, "build": build, "phone": phone, "check": check, "score": score}[args.cmd](args)


if __name__ == "__main__":
    guarded(main)
