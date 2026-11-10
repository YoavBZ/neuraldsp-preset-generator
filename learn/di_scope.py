"""The DI scope (`docs/full-controls-plan.md`, "C2r and C3r, Amendment 1 (2026-11-10): the DI scope"; ledger
`pipeline-fix` `phase_c2r_a1`): one blind card per library DI file C3r would train on (C2r's n12 and panel blocks), the DI
alone, levelled; Keep, "Drop: too low or too metal", Not sure. Only Keep stays in: a DI file not kept takes every unit on
it out of C2r's records, C3r's rows and every read. Zero renders.

    .venv/bin/python -m learn.di_scope page [--out DIR]     # the page (PF/di-scope by default; refuses over a key)
    .venv/bin/python -m learn.di_scope answers --store FILE  # the Artifact's stored answers/<build> -> di-scope/verdicts.json

The page was published as build f75f017f9d66 from the scratch builder this module ports; `page` reproduces its ids and
build hash. The user's choice ("Library recordings"): GOAT's dataset DIs (and so cap1's) and BKS's are not checked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import time

PHASE = "phase_c2r_a1"
DIR = "di-scope"
SEED = 20261153                      # the cards' order and ids
WINDOW_S = 10.0                      # each card: 10 s of the DI from the first unit on its file, by key
BUILD = "f75f017f9d66"               # the published build; C3r's training refuses until its 26 answers are in
N_CARDS = 26                         # n12's 18 DI files and the panel's 8
VERDICTS = (("keep", "Keep", "K"), ("heavy", "Drop: too low or too metal", "D"), ("unsure", "Not sure", "N"))
LEAK_WORDS = ("cambridge", "telefunken", "ElecGtr", "DI.wav", "panel", "n12")
INTRO = ("dry guitar recordings (DIs), each on its own, looping. Keep one if it fits the guitar parts the model should "
         "learn from. Drop it if it is tuned too low or played too metal for that, as on the batch 3 page. Only Keep stays "
         "in, so Not sure counts as dropped. All are set to the same loudness, and a tap moves on to the next one. ")


def scope_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / DIR


# --- the cards (zero renders) -----------------------------------------------------------------------------------------

def card_sources(n12_units, panel_units):
    """One card per DI file: the first unit on it by key, n12's then the panel's. n12_units, panel_units: [unit dict with
    unit, di, di_path, start_s]. -> {di: {set, unit, path, start}}."""
    cards = {}
    for u in sorted(n12_units, key=lambda u: u["unit"]):
        cards.setdefault(u["di"], {"set": "n12", "unit": u["unit"], "path": u["di_path"], "start": u["start_s"]})
    for u in sorted(panel_units, key=lambda u: u["unit"]):
        cards.setdefault(u["di"], {"set": "panel", "unit": u["unit"], "path": u["di_path"],
                                   "start": float(u["start_s"])})
    return cards


def card_id(di, seed=SEED):
    return "d" + hashlib.sha256(f"{seed}|{di}".encode()).hexdigest()[:10]


def card_order(dis, seed=SEED):
    """The cards' seeded order over the sorted DI files."""
    out = sorted(dis)
    random.Random(seed).shuffle(out)
    return out


def build_of(ids):
    return hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:12]


def library_units():
    """C2r's library units: n12's (batch 2's trusted units with a C1a record) and the panel's kept units. -> (n12, panel)."""
    from learn import capture_labels as CL
    from learn import full_controls_c2r as R
    from learn import pipeline_fix as P

    n12 = {json.loads(p.read_text())["unit"] for p in (P.out_dir() / "captures2" / "search-c1a").glob("*.json")}
    keep = CL.BATCH
    CL.BATCH = CL.BATCH2
    try:
        t2 = [u for u in CL.trusted_units()[0] if u["unit"] in n12]
    finally:
        CL.BATCH = keep
    return t2, R.panel_kept_units()


def page_cards():
    """The page's cards in page order, with their ids and build (zero renders, no audio). -> (cards, ids, build)."""
    n12, panel = library_units()
    src = card_sources(n12, panel)
    dis = card_order(src)
    cards = [dict(src[d], di=d, id=card_id(d)) for d in dis]
    ids = [c["id"] for c in cards]
    return cards, ids, build_of(ids)


def leaks(page):
    """The words the page shows before its clips that would name a source."""
    head = page.split('<script id="clips"')[0]
    return [w for w in LEAK_WORDS if w in head]


def page_html(ids, clips, build):
    """The scope page's page (`scope_page.page_html`) with this page's verdicts, title and intro."""
    from learn import scope_page as SP

    keep = SP.VERDICTS
    SP.VERDICTS = VERDICTS
    try:
        page = SP.page_html(ids, clips, build)
    finally:
        SP.VERDICTS = keep
    page = page.replace("<title>Keep Or Drop</title>", "<title>Guitar DI Check</title>").replace(
        "<h1>Keep or drop</h1>", "<h1>Guitar DI check</h1>")
    i0, i1 = page.index('<p class="intro">'), page.index('<span id="saveline">')
    return page[:i0] + '<p class="intro">' + f"{len(ids)} " + INTRO + page[i1:]


def cmd_page(args):
    """The page and its key -> DIR/page.html and DIR/key.json (PF/di-scope by default). Refuses over an existing key: a
    rebuild would hide the listener's stored answers."""
    import soundfile as sf

    from learn import build_data_review as BDR
    from learn import scope_page as SP

    out = pathlib.Path(args.out) if args.out else scope_dir()
    if (out / "key.json").exists():
        raise SystemExit(f"{out / 'key.json'} exists: a rebuild hides the stored answers; never overwrite it")
    out.mkdir(parents=True, exist_ok=True)
    cards, ids, build = page_cards()
    items, clips = [], {}
    for c in cards:
        y, sr = sf.read(c["path"], always_2d=True)
        y = y.mean(1)
        if sr != BDR.SR:
            raise SystemExit(f"{c['path']}: rate {sr}")
        a = int(c["start"] * sr)
        y = y[a:a + int(WINDOW_S * sr)]
        y, gain, _, cut = BDR.level_clip(y)
        clips[c["id"]] = SP.encode(y, out / "aac-cache")
        items.append({"id": c["id"], "di": c["di"], "set": c["set"], "unit": c["unit"], "path": c["path"],
                      "start": c["start"], "gain_db": gain, "peak_cut_db": cut})
    page = page_html(ids, clips, build)
    shown = leaks(page)
    if shown:
        raise SystemExit(f"the page names {shown}")
    (out / "page.html").write_text(page)
    (out / "key.json").write_text(json.dumps({"page": DIR, "build": build, "seed": SEED, "window_s": WINDOW_S,
                                              "items": items, "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
    print(f"DI SCOPE PAGE {len(items)} cards, build {build}, {len(page) / 1e6:.1f} MB -> {out / 'page.html'}")


# --- the answers and the rule -----------------------------------------------------------------------------------------

def di_verdicts(answers, items):
    """A stored `answers` ({card id: {"v": verdict}}) -> {di: verdict}; refuses an id or verdict the page never showed. A
    partial sitting is kept partial: the unanswered DIs are neither kept nor dropped yet."""
    di_of = {it["id"]: it["di"] for it in items}
    known = {v for v, _, _ in VERDICTS}
    bad = [k for k, a in answers.items() if k not in di_of or (a or {}).get("v") not in known]
    if bad:
        raise SystemExit(f"answers this page never showed: {bad}")
    return {di_of[k]: a["v"] for k, a in answers.items()}


def cmd_answers(args):
    """The Artifact's stored answers/<build> (a file: the stored document or the page's Export text) -> verdicts.json."""
    from learn import ear_eat as EE
    from learn import pipeline_fix as P

    P.require(PHASE)
    d = scope_dir()
    key = json.loads((d / "key.json").read_text())
    ex = EE.stored_answers(pathlib.Path(args.store).read_text())
    if ex.get("build") != key["build"]:
        raise SystemExit(f"{args.store}: build {ex.get('build')}, this page's is {key['build']}")
    got = di_verdicts(ex.get("answers") or {}, key["items"])
    rec = {"page": DIR, "build": key["build"], "store": str(args.store), "verdicts": got,
           "answered": len(got), "cards": len(key["items"]), "complete": len(got) == len(key["items"]),
           "dropped": sorted(di for di, v in got.items() if v != "keep"), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(d / "verdicts.json", rec)
    c = {}
    for v in got.values():
        c[v] = c.get(v, 0) + 1
    print(f"DI SCOPE ANSWERS: {len(got)} of {len(key['items'])} heard; {c}; dropped {len(rec['dropped'])} DI files")


def verdicts():
    """The stored verdicts, or None while there are none. Refuses another build's."""
    p = scope_dir() / "verdicts.json"
    if not p.exists():
        return None
    v = json.loads(p.read_text())
    if v.get("build") != BUILD:
        raise SystemExit(f"{p}: build {v.get('build')}, the published page's is {BUILD}")
    return v


def dropped_of(v):
    """The DI files a verdicts record does not keep (answered, not "keep"). -> frozenset."""
    return frozenset(di for di, x in (v.get("verdicts") or {}).items() if x != "keep")


def dropped_dis():
    """The DI files not kept, or None while the verdicts are missing. With a partial sitting, only the answered DIs not
    kept (an unanswered one is not dropped yet; C3r's training waits for all of them)."""
    v = verdicts()
    return None if v is None else dropped_of(v)


def complete_refusal(v=None, n=N_CARDS):
    """Why C3r may not train yet on the scope, or None: the verdicts hold all n answers for the published build."""
    v = verdicts() if v is None else v
    if v is None:
        return f"the DI scope's verdicts are missing ({DIR}/verdicts.json: the page's {n} answers)"
    got = len(v.get("verdicts") or {})
    if v.get("build") != BUILD or got != n:
        return f"the DI scope's verdicts hold {got} of {n} answers for build {v.get('build')} (need {BUILD})"
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("page")
    p.add_argument("--out", help="the folder to build into (default PF/di-scope)")
    p.set_defaults(fn=cmd_page)
    a = sub.add_parser("answers")
    a.add_argument("--store", required=True, help="the Artifact's stored answers/<build>, as a file")
    a.set_defaults(fn=cmd_answers)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
