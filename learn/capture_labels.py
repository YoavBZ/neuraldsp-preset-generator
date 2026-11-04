"""L1a, the first capture batch (`docs/pipeline-fix-plan.md`, ledger `phase_l1a`): does a label searched on a capture of
a real amp sound closer than S, before more captures are asked for?

    $MAIN -m learn.capture_labels dis                     # the 50 captures checked, the DIs levelled -> captures/plan.json
    $NAM -I nam_notk.py learn/capture_units.py PLAN OUT   # the walk (zero plugin renders) -> OUT/units.json, renders.npz
    $MAIN -m learn.capture_labels units                   # sections, folds, lags to the DI, the counts -> captures/units.json
    $MAIN -m learn.capture_labels page / answers EXPORT   # one card per capture
    $MAIN -m learn.capture_labels heavy / heavy-answers EXPORT
    $MAIN -m learn.capture_labels search --lags-only --before-ear --shard k/n    # the night's path, nothing read
    $MAIN -m learn.capture_labels search --stage third --before-ear --shard k/n
    $MAIN -m learn.capture_labels night-check             # go or stop, no figure
    $MAIN -m learn.capture_labels search --stage all --before-ear --shard k/n
    $MAIN -m learn.capture_labels stage-check             # after the ear, on the trusted units
    $MAIN -m learn.capture_labels items                   # after both gates, once
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import random
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

PHASE, NIGHT = "phase_l1a", "phase_l1a_night"
CAPTURE_DIR = "captures"             # under out_dir(), apart from goat/ and real/
BATCH = {"dir": CAPTURE_DIR, "phase": PHASE, "night": NIGHT, "manifest": "manifest.csv", "page": "", "name": "first"}
BATCH2 = {"dir": "captures2", "phase": "phase_l1b", "night": "phase_l1b_night", "manifest": "manifest-batch2.csv", "page": "-2",
          "name": "second"}
HELD_BANDS = ("Atlantis Bound", "Diesel13", "Eat The Feeder", "Magician's Nephew", "Szymon Skiba", "Wall Of Death", "Zeno",  # V-real
              "Adam Buckley", "The Maybe Next Years",  # NS
              "Aimee Norwich", "Big Troubles", "Blue Manic", "Dahka Band", "Guitar-TECHS P3", "Jen Hartswick & Nick Cassarino",
              "Little Tybee", "Port St Willow", "Sonnet & Alcohol", "The Laminar Flow", "BKS")  # the panel, the reserve, BKS
BAND_SECTIONS = 40                   # library sections per band in L1b's DI plan, seeded
PART_CARDS = 75                      # cards per page file
SEED = 20261105
CAPTURES = 50
FOLDS = 4
MIN_PER_CELL = 10                    # units per amp and class, before the ear and after the ear and the lag rule
CELL_ITEMS = 2                       # ear items per amp and class
ITEM_ACTIVE = 0.8                    # the held half's activity, at least
PLACEBO_FALLBACKS = 2                # fallbacks per part, taken only when a placebo unit gives no label
PAGE_NAME, HEAVY_PAGE = "capture-ear", "capture-heavy"
EAR_SPEC = {"page": PAGE_NAME, "title": "Capture ear", "head": "Amp captures", "h1": "A believable amp tone, from a clean DI?",
            "ask": """A is a guitar DI, B is the same performance played through a captured amp and cab (a neural
capture, not our plugin). Press Play and switch between A and B as often as you like: the Switch button, the A and B
buttons, or the S, A and B keys; the switch is instant. Judge B: does it sound like a believable guitar amp and cab,
not muffled, not fizzy, with no artifacts? And if A, the DI, already sounds processed, noisy or hummy, say so."""}
HEAVY_SPEC = {"page": HEAVY_PAGE, "title": "Capture heavy check", "head": "Capture heavy check",
              "h1": "Too heavy or fizzy for our clean/crunch scope?",
              "ask": """These are the more driven recordings of the amps you passed. This time judge only how heavy B
is: the presets we build are clean and crunch, with heavy tones a small minority and never very heavy. Keep a recording
if B is clean or crunch you would want the model to learn from; mark it too heavy or fizzy if it is beyond that. A is
the DI, B the captured amp; switch with the buttons or the S, A and B keys."""}


# --- pure functions (unit-tested) ------------------------------------------------------------------------------------

def folds_by_creator(units, folds=FOLDS, seed=SEED):
    """A creator's units stay in one fold, largest creators first (ties seeded), each to the emptiest fold.
    units: [{creator}]. -> {creator: fold}."""
    n = {}
    for u in units:
        n[u["creator"]] = n.get(u["creator"], 0) + 1
    rng = random.Random(f"{seed}|folds")
    names = sorted(n)
    rng.shuffle(names)
    load, out = [0] * folds, {}
    for c in sorted(names, key=lambda c: -n[c]):
        k = load.index(min(load))
        out[c] = k
        load[k] += n[c]
    return out


def counts(units):
    """What is stated before the ear. units: [{amp, cls, player, label, di_item, level_held, level_dbu}]."""
    def tally(keys):
        t = {}
        for u in units:
            k = keys(u)
            t[k] = t.get(k, 0) + 1
        return {str(k): v for k, v in sorted(t.items(), key=str)}

    return {"units": len(units), "amp_class": tally(lambda u: (u["amp"], u["cls"])),
            "player_class": tally(lambda u: (u["player"], u["cls"])), "label_class": tally(lambda u: (u["label"], u["cls"])),
            "most_used_dis": dict(sorted(tally(lambda u: u["di_item"]).items(), key=lambda kv: -kv[1])[:8]),
            "level_held": sum(bool(u["level_held"]) for u in units), "uncalibrated": sum(u["level_dbu"] is None for u in units)}


def card_units(units):
    """One unit per capture, its most driven (highest non-linear share; ties by name). -> [unit]."""
    best = {}
    for u in sorted(units, key=lambda u: u["unit"]):
        c = best.get(u["capture"])
        if c is None or u["nonlinear_db"] > c["nonlinear_db"]:
            best[u["capture"]] = u
    return [best[c] for c in sorted(best)]


def passed(units, ear, heavy_cards, heavy):
    """The two gates. ear: {capture: {verdict}}, only "amp" passes and any other verdict drops the capture; every capture
    needs one. heavy_cards: the units on the heavy page; heavy: {unit: {verdict}}, only "keep" stays and it drops that
    unit alone; every card needs one. -> (units passed, what is still unheard)."""
    miss = sorted({u["capture"] for u in units} - set(ear)) + [u for u in heavy_cards if u not in heavy]
    ok = {u["unit"] for u in units if (ear.get(u["capture"]) or {}).get("verdict") == "amp"}
    return ok - {u for u in heavy_cards if (heavy.get(u) or {}).get("verdict") != "keep"}, miss


def pick_items(units, active, seed=SEED, per_cell=CELL_ITEMS, fallbacks=PLACEBO_FALLBACKS, amps=None):
    """The ear items and their placebos, from unit metadata alone. Items: `per_cell` units of each amp and class, one held A
    and one held B, held half at least ITEM_ACTIVE active, no two from one pack, at most 2 from one creator. Each part's
    placebo: a unit of the same amp and class from another creator, not an item and serving one part, with seeded
    fallbacks (taken only when a unit gives no label). units: [{unit, amp, cls, held_half, pack, creator}]; active:
    {unit: {A, B}}. -> ([{unit, placebos: [unit]}]), or SystemExit if a cell cannot supply them."""
    from learn import pipeline_fix as P

    amps = amps or P.AMPS3
    rng = random.Random(f"{seed}|items")
    pool = sorted(units, key=lambda u: u["unit"])
    ok = [u for u in pool if active[u["unit"]][u["held_half"]] >= ITEM_ACTIVE]
    cells = [(a, c) for a in amps for c in ("clean", "crunch")]
    for _ in range(20000):
        rng.shuffle(ok)
        rng.shuffle(pool)
        rng.shuffle(cells)
        packs, creators, chosen = set(), {}, []
        for a, c in cells:
            got = {}
            for u in ok:
                if u["amp"] != a or u["cls"] != c or u["held_half"] in got or u["pack"] in packs:
                    continue
                if creators.get(u["creator"], 0) >= 2:
                    continue
                got[u["held_half"]] = u
                packs.add(u["pack"])
                creators[u["creator"]] = creators.get(u["creator"], 0) + 1
                if len(got) == per_cell:
                    break
            if len(got) < per_cell:
                break
            chosen += [got[h] for h in sorted(got)]
        else:
            taken = {u["unit"] for u in chosen}
            out = {it["unit"]: [] for it in chosen}
            for turn in range(1 + fallbacks):                  # every part's first placebo before any fallback
                for it in sorted(chosen, key=lambda u: u["unit"]):
                    cand = [u for u in pool if u["amp"] == it["amp"] and u["cls"] == it["cls"] and u["unit"] not in taken
                            and u["creator"] != it["creator"]]
                    if cand:
                        taken.add(cand[0]["unit"])
                        out[it["unit"]].append(cand[0]["unit"])
            if all(out.values()):
                return [{"unit": u, "placebos": v} for u, v in sorted(out.items())]
    raise SystemExit("no draw of the ear items and placebos fits the declared rules: the batch stops; revise the block")


def fallbacks_due(items, labels):
    """The next placebo of each part whose earlier ones all gave no label. labels: {unit: label or None}, searched units."""
    out = []
    for it in items:
        for u in it["placebos"]:
            if u not in labels:
                out.append(u)
                break
            if labels[u] is not None:
                break
    return out


def input_gain(label):
    return float(label["parameters/inputGain"])


def search_row(recs):
    """Mean S held-half distance and mean search gain, ln(d_S / d_best) on the held half, of search records."""
    rows = [(r["s_judge"][r["held"]], r["best"]["judge"][r["held"]]) for r in recs if r["label"] is not None
            and r["s_judge"][r["held"]] and r["best"]["judge"][r["held"]] > 0]
    if not rows:
        return None
    return {"n": len(rows), "s_held": sum(s for s, _ in rows) / len(rows),
            "search_gain": sum(math.log(s / b) for s, b in rows) / len(rows)}


def stage_beside(recs, units):
    """The rows beside the stage check (zero renders): the label's inputGain against the unit's capture gain, by creator; S's
    held-half distance and the search gain on captures against GOAT's and BKS's. recs: search records; units: {unit: record}."""
    from learn import ear_vreal as E
    from learn import pipeline_fix as P

    lab = [r for r in recs if r["label"] is not None]
    pairs = [(units[r["unit"]]["creator"], units[r["unit"]]["gain_db"], input_gain(r["label"])) for r in lab]
    by = {}
    for c, x, y in pairs:
        by.setdefault(c, []).append((x, y))
    rng, groups, boots = random.Random(f"{SEED}|beside"), list(by.values()), []
    for _ in range(2000):
        pool = [q for g in rng.choices(groups, k=len(groups)) for q in g]
        r = E.spearman([q[0] for q in pool], [q[1] for q in pool])
        if r is not None:
            boots.append(r)
    boots.sort()

    def stored(d):
        return search_row([json.loads(q.read_text()) for q in sorted((P.out_dir() / d / P.SEARCH_DIR).glob("*.json"))])

    return {"input_gain_vs_capture_gain": {
        "spearman": E.spearman([q[1] for q in pairs], [q[2] for q in pairs]) if pairs else None,
        "lo90": boots[int(0.05 * len(boots))] if boots else None, "hi90": boots[int(0.95 * len(boots)) - 1] if boots else None},
        "captures": search_row(lab), "goat": stored(P.GOAT_DIR), "bks": stored(P.REAL_DIR)}


def placebo_units(items):
    """The first placebo of every part: searched with the items. items: `pick_items`' result."""
    return [it["placebos"][0] for it in items]


def search_order(units, first, seed=SEED):
    """The search's order: the ear items and placebos first, then the rest in a seeded order. units, first: [unit ids]."""
    rest = [u for u in units if u not in set(first)]
    random.Random(f"{seed}|search").shuffle(rest)
    return sorted(first) + rest


def stage_set(order, n_items, stage):
    """The units of a search stage: "first" the items and placebos, "third" up to a third of all units, "all" every one."""
    if stage == "first":
        return order[:n_items]
    if stage == "third":
        return order[:max(n_items, -(-len(order) // 3))]
    if stage == "all":
        return list(order)
    raise SystemExit(f"--stage first, third or all, not {stage}")


# --- the commands ----------------------------------------------------------------------------------------------------

def root():
    from learn import pipeline_fix as P

    return P.out_dir() / BATCH["dir"]


def tone3000():
    from learn import pretrain_set as PS

    return PS.HOME / "references/datasets-tone3000"


def units_of():
    """The batch's units; refuses while the first minimum is short."""
    d = json.loads((root() / "units.json").read_text())
    if d.get("short"):
        raise SystemExit(f"under {MIN_PER_CELL} units in {d['short']}: the batch stopped at the data stage")
    return d["units"]


def check_files():
    """The captures against the manifest (sha256, count): -> [{capture, path, level_dbu, creator, pack, label}]."""
    from learn import capture_units as CU

    rows = {r["file_name"]: r for r in csv.DictReader(open(tone3000() / BATCH["manifest"]))}
    if BATCH is BATCH2:
        return sorted((plan_row(r, CU) for r in rows.values()), key=lambda c: c["capture"])
    read = json.loads((tone3000() / "capture-read.json").read_text())
    if len(read) != CAPTURES or len(rows) != CAPTURES:
        raise SystemExit(f"{len(read)} captures read, {len(rows)} in the manifest: {CAPTURES} declared")
    out = []
    for e in read:
        m = rows[e["file"]]
        path = next(tone3000().rglob(e["file"]))
        if CU.sha256_file(path) != m["sha256"]:
            raise SystemExit(f"{path}: not the manifest's file")
        out.append({"capture": pathlib.Path(e["file"]).stem, "name": e["capture"], "path": str(path),
                    "level_dbu": e["input_level_dbu"], "creator": m["creator"], "pack": e["pack"],
                    "label": m["class_guess"], "sha256": m["sha256"]})
    return sorted(out, key=lambda c: c["capture"])


def plan_row(m, CU):
    """A second-batch manifest row -> its plan row: the file found and checked, its level read from its metadata as data."""
    path = next(tone3000().rglob(m["file_name"]))
    if CU.sha256_file(path) != m["sha256"]:
        raise SystemExit(f"{path}: not the manifest's file")
    meta = json.loads(path.read_text()).get("metadata") or {}
    return {"capture": path.stem, "name": m["capture_name"], "path": str(path), "level_dbu": meta.get("input_level_dbu"),
            "creator": m["creator"], "pack": path.parent.name, "label": m["class_guess"], "sha256": m["sha256"]}


def library_dis(sections, held=HELD_BANDS, per_band=BAND_SECTIONS, seed=SEED):
    """L1b's DIs: the clean-DI library's trusted, clean, disjoint sections outside every held band, at most `per_band` a band,
    seeded. sections: `clean_di` manifest rows. -> {band: [section row]}."""
    by = {}
    for s in sorted(sections, key=lambda s: (s["di"], s["start_s"])):
        if s["training_ok"] and s["clean"] and s["disjoint"] and s["band"] not in held:
            by.setdefault(s["band"], []).append(s)
    out = {}
    for band, v in sorted(by.items()):
        random.Random(f"{seed}|{band}").shuffle(v)
        out[band] = v[:per_band]
    return out


def cmd_dis(_args):
    import numpy as np

    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn.direc_check import to_lufs

    P.require(BATCH["phase"])
    plan = check_files()
    dis, players, meta = {}, {}, {}
    if BATCH is BATCH2:
        lib = json.loads((PS.HOME / "learn/clean-di/manifest.json").read_text())["sections"]
        for band, rows in library_dis(lib).items():
            for s in rows:
                item = "lib-" + hashlib.sha256(f"{s['di']}@{s['start_s']}".encode()).hexdigest()[:12]
                dis[item] = to_lufs(PS.section_audio(s["path"], s["start_s"]).astype(np.float64)).astype(np.float32)
                players.setdefault(band, []).append(item)
                meta[item] = {"di_path": s["path"], "start_s": s["start_s"], "player": band, "di": s["di"]}
    else:
        for u in P.goat_units():
            if u["item"] in dis:
                continue
            dis[u["item"]] = to_lufs(PS.section_audio(u["di_path"], u["start_s"]).astype(np.float64)).astype(np.float32)
            players.setdefault(u["band"].split()[-1], []).append(u["item"])
            meta[u["item"]] = {"di_path": u["di_path"], "start_s": u["start_s"], "player": u["band"].split()[-1], "di": f"goat/{u['item']}"}
    root().mkdir(parents=True, exist_ok=True)
    np.savez(root() / "dis.npz", **dis)
    from learn import capture_units as CU

    spec = {"seed": SEED, "plan": plan, "players": players, "dis": str(root() / "dis.npz"), "di_meta": meta}
    if BATCH is BATCH2:
        spec.update(seed=f"{SEED}|b2", amp_of=CU.amps_balanced([c["capture"] for c in plan], f"{SEED}|b2"))
    P.save(root() / "plan.json", spec)
    print(f"CAPTURE-DIS DONE: {len(plan)} captures, {len(dis)} DIs, players { {k: len(v) for k, v in players.items()} }")


def cmd_units(_args):
    import numpy as np
    import soundfile as sf

    from analysis.aligned import estimate_lag
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    P.require(BATCH["phase"])
    spec = json.loads((root() / "plan.json").read_text())
    plan = {c["capture"]: c for c in spec["plan"]}
    meta = spec["di_meta"]
    raw = json.loads((root() / "walk" / "units.json").read_text())
    audio = np.load(root() / "walk" / "renders.npz")
    dis = np.load(root() / "dis.npz")
    sec = root() / "sections"
    sec.mkdir(parents=True, exist_ok=True)
    units = []
    for name, amps in sorted(raw["taken"].items()):
        c = plan[name]
        for amp, item in sorted(amps.items()):
            rec = raw["candidates"][f"{name}|{item}"]
            y = np.asarray(audio[f"{name}|{amp}"], np.float64)
            sha = hashlib.sha256(np.asarray(y, np.float32).tobytes()).hexdigest()
            track = f"{name}.{amp}.wav"
            sf.write(sec / track, y.astype(np.float32), PS.SR, subtype="FLOAT")
            try:
                lag = int(estimate_lag(y, [np.asarray(dis[item], np.float64)]))
            except ValueError as err:
                print(f"{name} {amp}: no lag to the DI ({err}); out", flush=True)
                continue
            g = meta[item]
            if BATCH is BATCH2:                        # the DI's section beside the render, so one start reads both
                dp = sec / f"{name}.{amp}.di.wav"
                sf.write(dp, PS.section_audio(g["di_path"], g["start_s"]).astype(np.float32), PS.SR, subtype="FLOAT")
                g = dict(g, di_path=str(dp))
            units.append({"unit": f"cap/{name}#{amp}", "capture": name, "name": c["name"], "section": f"cap/{name}#{amp}",
                          "track": track, "rig": f"cap/{name}", "set": "captures", "di": g["di"],
                          "band": c["creator"], "creator": c["creator"], "pack": c["pack"], "label": c["label"],
                          "cls": rec["class"], "split": rec["split"], "nonlinear_db": rec["gain_measures"]["nonlinear_to_linear_db"],
                          "sd": str(sec), "start_s": PS.TRIM_S, "di_path": g["di_path"], "di_item": item,
                          "item": c["creator"], "player": g["player"], "item_lag": lag, "amp": amp,
                          "gain_db": rec["gain_db"], "level_held": rec["held"], "level_dbu": c["level_dbu"],
                          "render_sha256": sha, "capture_sha256": c["sha256"], "far": abs(lag) > P.PANEL_FAR})
    fold = folds_by_creator(units)
    for u in units:
        u["fold"] = fold[u["creator"]]
    hal = P.goat_halves(units)
    for u in units:
        u["search"], u["held_half"] = hal[u["unit"]], "B" if hal[u["unit"]] == "A" else "A"
    stated = counts(units)
    short = P.goat_short_cells(units, MIN_PER_CELL)
    P.save(root() / "units.json", {"plan": P.PLAN, "ledger": f"{P.LEDGER_ID} {BATCH['phase']}", "units": units, "stated": stated,
                                   "short": {str(k): v for k, v in short.items()}, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(json.dumps(stated, indent=1))
    if short:
        raise SystemExit(f"under {MIN_PER_CELL} units in {short}: the batch stops at the data stage")
    print(f"CAPTURE-UNITS DONE: {len(units)} units, far {sum(u['far'] for u in units)}")


def build_page(items, spec, key_name, by_unit, extra=None):
    from learn import goat_ear_page as G
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    page = spec["page"] + BATCH["page"]
    out = PS.HOME / "listening" / page
    key_path = root() / key_name
    if key_path.exists():
        raise SystemExit(f"{key_path} exists: a rebuild hides the listener's stored answers; move it aside first")
    build = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    trim = int(PS.TRIM_S * PS.SR)
    out.mkdir(parents=True, exist_ok=True)
    verdicts = G.VERDICTS if spec is EAR_SPEC else G.HEAVY_VERDICTS
    parts = [items[j:j + PART_CARDS] for j in range(0, len(items), PART_CARDS)] or [[]]
    for k, its in enumerate(parts, 1):
        clips = {}
        for it in its:
            prt = by_unit[it["unit"]]
            di = PS.section_audio(prt["di_path"], prt["start_s"])[trim:]
            amp = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            clips[it["id"] + "-1"], clips[it["id"] + "-2"] = G.pair_clips(di, amp, out / "cache")
        name = "index.html" if len(parts) == 1 else f"part-{k}.html"
        q = out / name
        q.write_text(G.page_html(its, clips, build, k, len(parts), 1 + (k - 1) * PART_CARDS, dict(spec, page=page, verdicts=verdicts)))
        print(f"{page}: {len(its)} cards, {q.stat().st_size / 1e6:.1f} MB -> {q}; build {build}")
    P.save(key_path, {"page": page, "seed": SEED, "build": build, "items": items, **(extra or {}),
                      "time": time.strftime("%Y-%m-%d %H:%M:%S")})


def cmd_page(_args):
    from learn import goat_ear_page as G
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    P.require(BATCH["phase"])
    units = units_of()
    by_unit = {u["unit"]: u for u in units}
    cards = card_units(units)
    random.Random(f"{SEED}|page").shuffle(cards)
    items = [{"id": "cap-" + hashlib.sha256(f"{SEED}|{u['capture']}".encode()).hexdigest()[:12], "unit": u["unit"],
              "capture": u["capture"], "render_sha256": u["render_sha256"]} for u in cards]
    ref = json.loads((P.out_dir() / P.GOAT_DIR / "ear-key.json").read_text())["bks_range"]
    tilts = {it["unit"]: G.tilt(P.real_amp_track(by_unit[it["unit"]]["sd"], by_unit[it["unit"]]["track"],
                                                 by_unit[it["unit"]]["start_s"]), PS.SR) for it in items}
    outside = sorted(u for u, t in tilts.items() if G.flagged(t, ref))
    print(f"outside BKS's cab range on the page's own clips: {len(outside)} of {len(items)}")
    build_page(items, EAR_SPEC, "ear-key.json", by_unit, {"tilt": tilts, "outside_bks_range": outside})


def read_export(exports, key_name, page):
    """Exports -> (the page's key, {item id: item}, {item id: {verdict, note}}); refuses another page's or build's export."""
    key = json.loads((root() / key_name).read_text())
    unit_of = {it["id"]: it for it in key["items"]}
    got = {}
    for f in exports:
        ex = json.loads(pathlib.Path(f).read_text())
        if ex.get("page") != page or ex.get("build") != key["build"]:
            raise SystemExit(f"{f}: not this page's export (page {ex.get('page')}, build {ex.get('build')})")
        for a in ex.get("answers", []):
            if a["id"] in unit_of and a.get("verdict"):
                got[a["id"]] = {"verdict": a["verdict"], "note": a.get("note") or ""}
    return key, unit_of, got


def cmd_answers(args):
    from learn import pipeline_fix as P

    P.require(BATCH["phase"])
    key, unit_of, got = read_export(args.exports, "ear-key.json", PAGE_NAME + BATCH["page"])
    P.save(root() / "ear.json", {"page": PAGE_NAME + BATCH["page"], "build": key["build"], "exports": args.exports,
                                 "verdicts": {unit_of[i]["capture"]: v for i, v in got.items()},
                                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"CAPTURE EAR ANSWERS: {len(got)} of {len(unit_of)} heard")


def ear_verdicts():
    p = root() / "ear.json"
    return json.loads(p.read_text())["verdicts"] if p.exists() else {}


def heavy_candidates(units, ear):
    """The firmly driven units of the captures the ear passed, sorted."""
    return sorted(u["unit"] for u in units if u["split"] == "driven" and (ear.get(u["capture"]) or {}).get("verdict") == "amp")


def cmd_heavy(_args):
    from learn import pipeline_fix as P

    P.require(BATCH["phase"])
    units = units_of()
    ear = ear_verdicts()
    miss = {u["capture"] for u in units} - set(ear)
    if miss:
        raise SystemExit(f"{len(miss)} captures not yet heard on the ear page")
    chosen = heavy_candidates(units, ear)
    random.Random(f"{SEED}|heavy").shuffle(chosen)
    by_unit = {u["unit"]: u for u in units}
    items = [{"id": "capheavy-" + hashlib.sha256(f"{SEED}|{u}".encode()).hexdigest()[:12], "unit": u,
              "render_sha256": by_unit[u]["render_sha256"]} for u in chosen]
    build_page(items, HEAVY_SPEC, "heavy-key.json", by_unit)


def cmd_heavy_answers(args):
    from learn import pipeline_fix as P

    P.require(BATCH["phase"])
    key, unit_of, got = read_export(args.exports, "heavy-key.json", HEAVY_PAGE + BATCH["page"])
    P.save(root() / "heavy.json", {"page": HEAVY_PAGE + BATCH["page"], "build": key["build"], "exports": args.exports,
                                   "verdicts": {unit_of[i]["unit"]: v for i, v in got.items()},
                                   "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"CAPTURE HEAVY ANSWERS: {len(got)} of {len(unit_of)} heard")


def trusted(units):
    """`passed` on the stored verdicts; refuses while anything is unheard or either page is not the current one."""
    ear = ear_verdicts()
    ek = root() / "ear-key.json"
    if ear and (not ek.exists() or json.loads((root() / "ear.json").read_text())["build"] != json.loads(ek.read_text())["build"]):
        raise SystemExit("captures/ear.json is not from the ear page's build")
    kp = root() / "heavy-key.json"
    if not kp.exists():
        raise SystemExit("the heavy check is not built yet")
    key = json.loads(kp.read_text())
    cards = [it["unit"] for it in key["items"]]
    if sorted(cards) != heavy_candidates(units, ear):
        raise SystemExit("the heavy page's units are not the current firmly driven passed units: rebuild it")
    hp = root() / "heavy.json"
    hv = json.loads(hp.read_text()) if hp.exists() else {"build": key["build"], "verdicts": {}}
    if hv["build"] != key["build"]:
        raise SystemExit("captures/heavy.json is not from the heavy page's build")
    ok, miss = passed(units, ear, cards, hv["verdicts"])
    if miss:
        raise SystemExit(f"{len(miss)} still unheard: both pages come before any plugin render")
    return ok


def lags_of(units):
    """{unit: lag} of `units` and the one-window rule's refused units (`goat_lag_refused`), its median over them."""
    from learn import pipeline_fix as P

    ldir = root() / "lags"
    missing = [u["unit"] for u in units if not (ldir / f"{u['unit'].replace('/', '__')}.json").exists()]
    if missing:
        raise SystemExit(f"{len(missing)} units have no lag: run the lag pass first")
    lags = {u["unit"]: json.loads((ldir / f"{u['unit'].replace('/', '__')}.json").read_text())["lag"] for u in units}
    return lags, P.goat_lag_refused(lags, {u["unit"]: u["item_lag"] for u in units})


def trusted_units():
    """The units both gates passed and the lag rule keeps, the lag median taken over them alone. -> (units, {unit: lag})."""
    units = units_of()
    ok = trusted(units)
    tr = [u for u in units if u["unit"] in ok]
    lags, off = lags_of(tr)
    return [u for u in tr if u["unit"] not in off], lags


def search_records():
    """The one loader of the search records: every reader goes through `trusted_units`. -> {unit: record}."""
    from learn import pipeline_fix as P

    keep = {u["unit"] for u in trusted_units()[0]}
    recs = [json.loads(q.read_text()) for q in sorted((root() / P.SEARCH_DIR).glob("*.json"))]
    return {r["unit"]: r for r in recs if r["unit"] in keep}


def cmd_items(_args):
    """The 12 ear items and their placebos, after both gates, from unit metadata alone; written once."""
    from learn import ear_vreal as E
    from learn import pipeline_fix as P

    P.require(BATCH["phase"])
    if (root() / "items.json").exists():
        raise SystemExit("captures/items.json exists: the items are drawn once")
    tr, _ = trusted_units()
    short = P.goat_short_cells(tr, MIN_PER_CELL)
    if short:
        raise SystemExit(f"under {MIN_PER_CELL} trusted units in {short}: the batch stops at the data stage")
    active = {u["unit"]: E.activity(P.real_amp_track(u["sd"], u["track"], u["start_s"])) for u in tr}
    items = pick_items(tr, active)
    P.save(root() / "items.json", {"plan": P.PLAN, "ledger": f"{P.LEDGER_ID} {BATCH['phase']}", "seed": SEED, "items": items,
                                   "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print("CAPTURE ITEMS DONE: " + ", ".join(it["unit"][-24:] for it in items))


def batch_digest(units):
    """One hash of a batch's captures: the sorted sha256 of its files."""
    return hashlib.sha256("".join(sorted({u["capture_sha256"] for u in units})).encode()).hexdigest()


def night_guard(units):
    """The pre-ear path: the batch's own declared files only (`phase_l1a_night_batch`, `phase_l1b_night_batch`). -> the ledger entry."""
    from learn import pipeline_fix as P

    e = P.require(BATCH["night"])
    if batch_digest(units) != e.get(f"{BATCH['night']}_batch"):
        raise SystemExit(f"--before-ear covers the {BATCH['name']} batch's declared files only")
    return e


def night_order(units):
    """The night's order: every unit, seeded, no items first."""
    return search_order(sorted(u["unit"] for u in units), [])


def cmd_search(args):
    """The lag pass, then the labels (`pipeline_fix.search_units`, GOAT's recipe), in `search_order`. By default only
    after both gates. `--before-ear` (`phase_l1a_night`): every unit of the first batch in the seeded order, nothing read."""
    from learn import pipeline_fix as P

    P.require(BATCH["phase"])
    units = units_of()
    k, n = args.shard
    if args.before_ear:
        night_guard(units)
        halves = {u["unit"]: u["search"] for u in units}
        if args.lags_only:
            mine = [u for j, u in enumerate(sorted(units, key=lambda u: u["unit"])) if j % n == k]
            print(f"CAPTURE-SEARCH LAGS DONE {k}/{n}: {P.search_units(mine, root(), BATCH["phase"], halves, set(), True, quiet=True)} renders")
            return
        if args.stage == "all":
            gate = root() / "night-check.json"
            if not gate.exists() or json.loads(gate.read_text()).get("stop") is not False:
                raise SystemExit("the rest of the night's labels wait for the fault check, and do not run on its stop")
        by = {u["unit"]: u for u in units}
        mine = [by[u] for j, u in enumerate(stage_set(night_order(units), 0, args.stage)) if j % n == k]
        print(f"CAPTURE-SEARCH DONE {k}/{n} ({args.stage}): {P.search_units(mine, root(), BATCH["phase"], halves, set(), False, quiet=True)} renders")
        return
    ok = trusted(units)
    tr = [u for u in units if u["unit"] in ok]
    halves = {u["unit"]: u["search"] for u in tr}
    if args.lags_only:
        mine = [u for j, u in enumerate(sorted(tr, key=lambda u: u["unit"])) if j % n == k]
        print(f"CAPTURE-SEARCH LAGS DONE {k}/{n}: {P.search_units(mine, root(), BATCH["phase"], halves, set(), True)} renders")
        return
    lags, off = lags_of(tr)
    items = json.loads((root() / "items.json").read_text())["items"]
    first = [it["unit"] for it in items] + placebo_units(items)
    by = {u["unit"]: u for u in tr}
    order = search_order([u for u in sorted(by) if u not in off], first)
    todo = stage_set(order, len(first), args.stage)
    if args.stage == "all":
        rest_may_run()
    recs = {u: json.loads(q.read_text())["label"] for u, q in ((u, root() / P.SEARCH_DIR / f"{u.replace('/', '__')}|{by[u]['amp']}.json")
                                                               for u in by) if q.exists()}
    todo += [u for u in fallbacks_due(items, recs) if u not in todo and u in by]
    mine = [by[u] for j, u in enumerate(todo) if j % n == k]
    print(f"CAPTURE-SEARCH DONE {k}/{n} ({args.stage}): {P.search_units(mine, root(), BATCH["phase"], halves, off, False)} renders")


def rest_may_run():
    """The remaining labels and the centre read: only after the label page, and never on the primary share clear below."""
    gate, stage = root() / "ear-check.json", root() / "stage-check.json"
    if not gate.exists() or json.loads(gate.read_text()).get("branch") not in ("clear above", "reaching one half"):
        raise SystemExit("the rest waits for the label page, and does not run if the primary share is clear below")
    if not stage.exists() or json.loads(stage.read_text()).get("stop") is not False:
        raise SystemExit("the rest waits for the stage check, and does not run on its stop")


def cmd_night_check(_args):
    """The pre-ear fault check at a third: stores and prints only go or stop; its figures stay unread."""
    from learn import pipeline_fix as P

    units = units_of()
    night_guard(units)
    by = {u["unit"]: u for u in units}
    third = stage_set(night_order(units), 0, "third")
    missing = [u for u in third if not (root() / P.SEARCH_DIR / f"{u.replace('/', '__')}|{by[u]['amp']}.json").exists()]
    if missing:
        raise SystemExit(f"{len(missing)} of the third have no record yet")
    read = P.stage_read(root(), BATCH["phase"])
    stop = bool(read["stop"]) or not read["labelled"]
    P.save(root() / "night-check.json", {"stop": stop, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print("STOP" if stop else "GO")
    if stop:
        raise SystemExit(1)


def cmd_stage_check(_args):
    """The declared check, after the ear, on the trusted units alone; its stop holds the label page."""
    from learn import pipeline_fix as P

    P.require(BATCH["phase"])
    tr, _ = trusted_units()
    keep = {u["unit"] for u in tr}
    have = [q for q in (root() / P.SEARCH_DIR).glob("*.json") if json.loads(q.read_text())["unit"] in keep]
    if 3 * len(have) < len(tr):
        raise SystemExit(f"{len(have)} of {len(tr)} trusted units searched: the check reads at a third")
    out = P.stage_check(root(), BATCH["phase"], keep)
    out["beside"] = stage_beside(list(search_records().values()), {u["unit"]: u for u in tr})
    P.save(root() / "stage-check.json", out)
    print(json.dumps(out["beside"], indent=1))


def shard(s):
    a, b = s.split("/")
    return int(a), int(b)


def main(argv=None):
    global BATCH
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", type=int, choices=(1, 2), default=1)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("dis", "units", "page", "heavy", "items", "stage-check", "night-check"):
        sub.add_parser(c)
    for c in ("answers", "heavy-answers"):
        sub.add_parser(c).add_argument("exports", nargs="+")
    s = sub.add_parser("search")
    s.add_argument("--lags-only", action="store_true")
    s.add_argument("--before-ear", action="store_true")
    s.add_argument("--stage", default="third")
    s.add_argument("--shard", type=shard, default=(0, 1))
    args = ap.parse_args(argv)
    if args.batch == 2:
        BATCH = BATCH2
    {"dis": cmd_dis, "units": cmd_units, "page": cmd_page, "answers": cmd_answers, "heavy": cmd_heavy,
     "heavy-answers": cmd_heavy_answers, "items": cmd_items, "search": cmd_search,
     "stage-check": cmd_stage_check, "night-check": cmd_night_check}[args.cmd](args)


if __name__ == "__main__":
    main()
