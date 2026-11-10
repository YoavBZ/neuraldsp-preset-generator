"""L1a, the first capture batch (`docs/pipeline-fix-plan.md`, ledger `phase_l1a`): does a label searched on a capture of
a real amp sound closer than S, before more captures are asked for?

    $MAIN -m learn.capture_labels dis                     # the 50 captures checked, the DIs levelled -> captures/plan.json
    $NAM -I nam_notk.py learn/capture_units.py PLAN OUT   # the walk (zero plugin renders) -> OUT/units.json, renders.npz
    $MAIN -m learn.capture_labels units                   # sections, folds, lags to the DI, the counts -> captures/units.json
    $MAIN -m learn.capture_labels page / answers EXPORT   # one card per capture
    $MAIN -m learn.capture_labels heavy / heavy-answers EXPORT
    $MAIN -m learn.capture_labels scope / scope-answers EXPORT
    $MAIN -m learn.capture_labels search --lags-only --before-ear --shard k/n    # the night's path, nothing read
    $MAIN -m learn.capture_labels search --stage third --before-ear --shard k/n
    $MAIN -m learn.capture_labels night-check             # go or stop, no figure
    $MAIN -m learn.capture_labels search --stage all --before-ear --shard k/n
    $MAIN -m learn.capture_labels stage-check             # after the ear, on the trusted units
    $MAIN -m learn.capture_labels items                   # after both gates, once

L1c (`docs/full-controls-plan.md`, ledger `phase_l1c`), the third batch, C4's source: `--batch 3` with dis, units, page,
answers, heavy, heavy-answers and gate-read alone (no labels, no search).
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
SEED3 = 20261150                     # L1c's DI order, walk and amps
VERDICTS3 = [("amp", "A believable amp tone"), ("distorted", "Too distorted for clean or light crunch"),
             ("odd", "Odd amp sound (muffled, fizzy, artifacts)"), ("di_bad", "The DI itself sounds processed or noisy"),
             ("unsure", "Not sure")]
BATCH3 = {"dir": "captures3", "phase": "phase_l1c", "night": None, "manifest": "manifest-batch3.csv", "page": "-3",
          "name": "third", "captures": 44, "seed": SEED3, "minimum": False, "threads": 2}
EARLIER = ("manifest.csv", "manifest-batch2.csv")       # L1c refuses a capture already fetched in these
BATCH3_CMDS = ("dis", "units", "page", "answers", "heavy", "heavy-answers", "gate-read")
B2_YIELD = {"heard": 147, "passed": 49, "di_bad": 14, "trusted_after_lag_and_t0": 32}   # L1b's ear page (before the heavy
#   page, the lag rule and T0; its 14 bad-DI verdicts fell on DIs T0 never verified) and N10b's 32 (after the lag rule and T0)
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
SCOPE_DB = -3.0                      # undriven crunch units at or above this nonlinear share go on the scope page (F57)
LABEL_PAGE_OUT = ("cap/ca2a7be3-377d-48e8-94b1-d3cb5f47b32e#sw50r",   # "Too distorted, out of scope" on the label page (F57)
                  "cap/npd1zhu905b#pr12")
HELD_OUT_READ = {"04cf993bee72": "reaching one half"}   # a part held out of scope, not a partial file: either answer reaches (F57)
PAGE_NAME, HEAVY_PAGE, SCOPE_PAGE = "capture-ear", "capture-heavy", "capture-scope"
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
SCOPE_SPEC = dict(HEAVY_SPEC, page=SCOPE_PAGE, title="Capture scope check", head="Capture scope check",
                  h1="Too distorted for our clean/crunch scope?")
if "not muffled, not fizzy, with no artifacts?" not in EAR_SPEC["ask"]:
    raise SystemExit("the ear page's ask changed: L1c's added line has no place")
EAR_SPEC3 = dict(EAR_SPEC, verdicts=VERDICTS3, ask=EAR_SPEC["ask"].replace(
    "not muffled, not fizzy, with no artifacts?",
    "not muffled, not fizzy, with no artifacts? Our presets are clean and light crunch: if B is more distorted than that, say\nso with its own button, even if it sounds like a good amp.", 1))
ARTIFACT_INTRO = ("Answers are saved in this browser as you go; tap <b>Export</b> any time, even halfway, and send the file.",
                  "Your answers save as you go, and I can read them from here when you tell me you are done. Use one device for "
                  "this page. If the line below says they are not saving, tap <b>Export</b> and send the text instead."
                  ' <b id="sync">Not saved yet.</b>')
GATE_SYNC = r"""
let dbDoc = null, syncTimer = null, syncBusy = false, syncAgain = false;
function push() {
  if (!dbDoc) return;
  if (syncBusy) { syncAgain = true; return; }
  syncBusy = true;
  const el = document.getElementById("sync");
  dbDoc.set(JSON.parse(exportText())).then(() => { if (el) el.textContent = "Saved."; })
    .catch(() => { if (el) el.textContent = "Not saving here: tap Export and send the text."; }).finally(() => {
    syncBusy = false; if (syncAgain) { syncAgain = false; push(); } });
}
const saveHere = save;
save = function () { saveHere(); if (dbDoc) { clearTimeout(syncTimer); syncTimer = setTimeout(push, 700); } };
(async () => {
  try {
    if (!window.claude) { const el = document.getElementById("sync");
      if (el) el.textContent = "Not saving here: tap Export and send the text."; return; }
    const db = await window.claude.use("db");
    const el = document.getElementById("sync");
    if (!db) { if (el) el.textContent = "Not saving here: tap Export and send the text."; return; }
    const d = db.doc("answers/" + DATA.build + "-part" + DATA.part), snap = await d.get();
    if (snap.exists && !Object.keys(store).length) {
      for (const a of (snap.data().answers || [])) if (a.verdict || a.note) store[a.id] = {verdict: a.verdict, note: a.note, t: a.t};
      saveHere(); paint();
    }
    dbDoc = d;
    if (Object.keys(store).length) push();
  } catch (e) { const el = document.getElementById("sync"); if (el) el.textContent = "Not saving here: tap Export and send the text."; }
})();
"""


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


def earlier_overlap(rows, earlier):
    """L1c: the batch's manifest rows whose capture an earlier batch already holds, by sha256 or model id.
    rows, earlier: manifest rows. -> [file_name]."""
    sha = {r["sha256"] for r in earlier if r.get("sha256")}
    mid = {r["model_id"] for r in earlier if r.get("model_id")}
    return sorted(r["file_name"] for r in rows if r["sha256"] in sha or (r.get("model_id") and r["model_id"] in mid))


def l1c_sections(sections, verdict_of, w_files, played=frozenset()):
    """L1c's DI pool before L1b's library rule: the sections whose DI T0 verified, whose DI file is not among W's training
    rows and was heard on no ranking or preset page (`played`, from `played_dis`). verdict_of(di) -> T0's verdict or None
    (no verdict: left out). -> [section row]."""
    return [s for s in sections if verdict_of(s["di"]) == "verified" and s["di"] not in w_files and s["di"] not in played]


def played_dis(*card_lists):
    """The DI files heard on a ranking or preset page: each card's own `di`, or its part's (`prt`, as C1a's ear plan stores
    it). A card with neither refuses. The risk is ranking memory, which a gate page does not carry, so L1b's gate page
    (`capture-ear-2`, record-only) is not among the lists. -> frozenset of DI files."""
    out = set()
    for cards in card_lists:
        for c in cards:
            di = c.get("di") or (c.get("prt") or {}).get("di")
            if not di:
                raise SystemExit(f"a played card with no DI file: {c.get('unit') or c}")
            out.add(di)
    return frozenset(out)


def gate_read(units, ear, trusted_units, b2=B2_YIELD):
    """L1c's read of its gate, zero renders. units: the batch's; ear: {capture: {verdict}}; trusted_units: the set of units
    `trusted` keeps. -> the declared tables."""
    def tally(rows, key, val):
        t = {}
        for r in rows:
            k = str(key(r))
            t.setdefault(k, {})
            v = val(r)
            t[k][v] = t[k].get(v, 0) + 1
        return dict(sorted(t.items()))

    verdict = lambda u: (ear.get(u["capture"]) or {}).get("verdict") or "unheard"
    kept = [u for u in units if u["unit"] in trusted_units]
    count = lambda rows, key: dict(sorted({str(k): sum(1 for r in rows if key(r) == k) for k in {key(r) for r in rows}}.items()))
    heard = sum(verdict(u) != "unheard" for u in units)
    passed_n = sum(verdict(u) == "amp" for u in units)
    return {"units": len(units), "heard": heard, "passed": passed_n, "trusted": len(kept),
            "by_tag": tally(units, lambda u: u["label"], verdict), "by_class": tally(units, lambda u: u["cls"], verdict),
            "by_amp": tally(units, lambda u: u["amp"], verdict),
            "distorted_vs_odd": {"distorted": sum(verdict(u) == "distorted" for u in units), "odd": sum(verdict(u) == "odd" for u in units)},
            "trusted_by": {"amp_class": count(kept, lambda u: (u["amp"], u["cls"])), "creator": count(kept, lambda u: u["creator"]),
                           "band": count(kept, lambda u: u["player"]), "di_file": count(kept, lambda u: u["di"])},
            "units_per_section": count(units, lambda u: u["di_item"]),
            "bad_di_on_t0_verified": sorted(u["unit"] for u in units if verdict(u) == "di_bad"),   # disagreements with T0
            "yield": {"passed_share": passed_n / heard if heard else None,
                      "batch2_passed_share (the ear page alone, like for like)": b2["passed"] / b2["heard"],
                      "trusted_share (no lag rule in L1c)": len(kept) / len(units) if units else None,
                      "batch2_trusted_share (after the lag rule and T0, not like for like)": b2["trusted_after_lag_and_t0"] / b2["heard"],
                      "batch2_di_bad (on DIs T0 never verified)": b2["di_bad"]}}


def artifact_gate(page, js):
    """A gate page for the Artifact viewer: no document wrapper, its three themes, no file save, answers kept for reading
    back (`answers/<build>-part<k>`, the Export's own text)."""
    from learn import ear_eat as EE

    css = page[page.index("<style>") + len("<style>"):page.index("</style>")]
    body = page[page.index("<body>") + len("<body>"):page.index("</body>")]
    title = page[page.index("<title>") + len("<title>"):page.index("</title>")]
    for old in (ARTIFACT_INTRO[0], '<button type="button" id="save">Save file</button>', "<script>" + js + "</script>"):
        if old not in body:
            raise SystemExit(f"the gate page changed: {old[:60]}")
    hook = 'document.getElementById("save").addEventListener("click", () => {'
    decl = "const save = () => {"
    if hook not in js or decl not in js:
        raise SystemExit("the gate page's save hooks changed")
    js2 = js.replace(hook, "if (false) " + hook).replace(decl, "let save = () => {")
    body = body.replace(*ARTIFACT_INTRO).replace('<button type="button" id="save">Save file</button>', "") \
        .replace("<script>" + js + "</script>", "<script>" + js2 + GATE_SYNC + "</script>")
    return (f"<title>{title}</title>\n" + '<meta name="claude:viewport-fit-sides" content="cover">\n<style>'
            + EE.artifact_css(css) + "</style>\n" + body)


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
            and r["s_judge"][r["held"]] and r["best"]["judge"][r["held"]] > 0
            and math.isfinite(r["s_judge"][r["held"]] + r["best"]["judge"][r["held"]])]
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
    if BATCH is BATCH3:
        if len(rows) != BATCH["captures"]:
            raise SystemExit(f"{len(rows)} captures in {BATCH['manifest']}: {BATCH['captures']} declared")
        earlier = [r for m in EARLIER for r in csv.DictReader(open(tone3000() / m))]
        dup = earlier_overlap(list(rows.values()), earlier)
        if dup:
            raise SystemExit(f"{len(dup)} captures already fetched in an earlier batch, first {dup[0]}")
        bad = sorted(r["file_name"] for r in rows.values() if r["class_guess"] not in ("clean", "crunch"))
        if bad:
            raise SystemExit(f"{len(bad)} captures tagged neither clean nor crunch, first {bad[0]}")
    if BATCH["dir"] != CAPTURE_DIR:
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
    if BATCH["dir"] != CAPTURE_DIR:
        lib = json.loads((PS.HOME / "learn/clean-di/manifest.json").read_text())["sections"]
        seed = SEED
        if BATCH is BATCH3:
            from learn import score_ear as SE
            from learn import verify_tracks as VT

            verified = json.loads((VT.OUT / "t0" / "verified.json").read_text())

            def verdict_of(di):
                try:
                    return di_verdict(di, verified)
                except SystemExit:
                    return None

            pages = [json.loads((SE.wide_dir() / f).read_text()) for f in ("plan.json", "h4b/plan.json")]
            cards = [d["cards"] + d.get("spares", []) for d in pages]           # N12's and H4b's cards and spares
            cards.append(json.loads((P.out_dir() / "c1a" / "ear" / "plan.json").read_text())["items"])   # C1a's ear page
            played = played_dis(*cards)
            lib, seed = l1c_sections(lib, verdict_of, SE.w_dis(), played), SEED3
            print(f"L1c's DI pool: {len(lib)} sections, {len({s['di'] for s in lib})} DI files; {len(played)} ranked-page DI files out")
        for band, rows in library_dis(lib, seed=seed).items():
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
    if BATCH is BATCH3:
        spec.update(seed=str(SEED3), amp_of=CU.amps_balanced([c["capture"] for c in plan], str(SEED3)),
                    prefer={c["capture"]: c["label"] for c in plan}, threads=BATCH["threads"])
    P.save(root() / "plan.json", spec)
    print(f"CAPTURE-DIS DONE: {len(plan)} captures, {len(dis)} DIs, {len({m['di'] for m in meta.values()})} DI files, "
          f"players { {k: len(v) for k, v in players.items()} }")


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
            if BATCH["dir"] != CAPTURE_DIR:            # the DI's section beside the render, so one start reads both
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
    if BATCH.get("minimum") is False:                  # L1c: no centre read, so the cells are reported, not gated
        stated["short_cells"], short = {str(k): v for k, v in short.items()}, {}
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
    verdicts = spec.get("verdicts") or (G.VERDICTS if spec is EAR_SPEC else G.HEAVY_VERDICTS)
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
        html_text = G.page_html(its, clips, build, k, len(parts), 1 + (k - 1) * PART_CARDS, dict(spec, page=page, verdicts=verdicts))
        q.write_text(html_text)
        print(f"{page}: {len(its)} cards, {q.stat().st_size / 1e6:.1f} MB -> {q}; build {build}")
        if BATCH is BATCH3 and its:                     # L1c: the Artifact's copy, answers kept in its store
            from learn import build_ear_page as BEP
            from learn import cc_drive_page as CDP

            js = BEP.JS_HEAD + CDP.PLAYER_JS.replace("XFADE_S", repr(CDP.XFADE_S)) + BEP.JS_ANSWERS
            a = root() / "page" / f"{page}-{k}.html"
            a.parent.mkdir(parents=True, exist_ok=True)
            a.write_text(artifact_gate(html_text, js))
            print(f"{page}: the Artifact's copy {a.stat().st_size / 1e6:.1f} MB -> {a}")
    P.save(key_path, {"page": page, "seed": SEED, "batch_seed": BATCH.get("seed"), "build": build, "items": items, **(extra or {}),
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
    build_page(items, EAR_SPEC3 if BATCH is BATCH3 else EAR_SPEC, "ear-key.json", by_unit,
               {"tilt": tilts, "outside_bks_range": outside})


def read_export(exports, key_name, page, store=None):
    """Exports, and the Artifact's stored copy if given -> (the page's key, {item id: item}, {item id: {verdict, note}}).
    Refuses another page's or build's file. The stored copy wins: an Export whose verdict on any id differs from it, or that
    answers an id it lacks, is refused and the ids named, never merged; without a stored copy, Exports that differ on an id
    are refused the same way."""
    from learn import ear_eat as EE

    key = json.loads((root() / key_name).read_text())
    unit_of = {it["id"]: it for it in key["items"]}

    def answers(f):
        ex = EE.stored_answers(pathlib.Path(f).read_text())     # the Export's text, or the Artifact's stored copy
        if ex.get("page") != page or ex.get("build") != key["build"]:
            raise SystemExit(f"{f}: not this page's export (page {ex.get('page')}, build {ex.get('build')})")
        return {a["id"]: {"verdict": a["verdict"], "note": a.get("note") or ""}
                for a in ex.get("answers", []) if a["id"] in unit_of and a.get("verdict")}

    got = answers(store) if store else {}
    for f in exports:
        ex = answers(f)
        clash = sorted(i for i, a in ex.items() if (i in got and got[i]["verdict"] != a["verdict"]) or (store and i not in got))
        if clash:
            raise SystemExit(f"{f}: {len(clash)} answers differ from {'the stored copy' if store else 'an earlier file'}, "
                             f"first {clash[:3]}: not merged")
        for i, a in ex.items():
            got.setdefault(i, a)
    return key, unit_of, got


def cmd_answers(args):
    from learn import pipeline_fix as P

    P.require(BATCH["phase"])
    key, unit_of, got = read_export(args.exports, "ear-key.json", PAGE_NAME + BATCH["page"], getattr(args, "store", None))
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


def scope_cards(units, heard):
    """The undriven crunch units at or above SCOPE_DB that no question on scope has reached, sorted. units: the trusted
    ones; heard: the label page's units. The firmly driven had the heavy page."""
    return sorted(u["unit"] for u in units if u["cls"] == "crunch" and u["split"] != "driven"
                  and u["nonlinear_db"] >= SCOPE_DB and u["unit"] not in heard)


def cmd_scope(_args):
    from learn import pipeline_fix as P

    P.require(BATCH["phase"])
    P.require("phase_l1a_scope")
    if BATCH["dir"] != CAPTURE_DIR:
        raise SystemExit("the scope page is the first batch's: on the second, the ear card is the unit itself")
    units = trusted_units()[0]
    heard = {it["unit"] for it in json.loads((root() / "ear-check" / "key.json").read_text())["items"]}
    chosen = scope_cards(units, heard)
    random.Random(f"{SEED}|scope").shuffle(chosen)
    by_unit = {u["unit"]: u for u in units}
    items = [{"id": "capscope-" + hashlib.sha256(f"{SEED}|{u}".encode()).hexdigest()[:12], "unit": u,
              "render_sha256": by_unit[u]["render_sha256"]} for u in chosen]
    build_page(items, SCOPE_SPEC, "scope-key.json", by_unit)


def cmd_scope_answers(args):
    from learn import pipeline_fix as P

    P.require(BATCH["phase"])
    key, unit_of, got = read_export(args.exports, "scope-key.json", SCOPE_PAGE + BATCH["page"], getattr(args, "store", None))
    P.save(root() / "scope.json", {"page": SCOPE_PAGE + BATCH["page"], "build": key["build"], "exports": args.exports,
                                   "verdicts": {unit_of[i]["unit"]: v for i, v in got.items()},
                                   "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"CAPTURE SCOPE ANSWERS: {len(got)} of {len(unit_of)} heard")


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
    key, unit_of, got = read_export(args.exports, "heavy-key.json", HEAVY_PAGE + BATCH["page"], getattr(args, "store", None))
    P.save(root() / "heavy.json", {"page": HEAVY_PAGE + BATCH["page"], "build": key["build"], "exports": args.exports,
                                   "verdicts": {unit_of[i]["unit"]: v for i, v in got.items()},
                                   "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"CAPTURE HEAVY ANSWERS: {len(got)} of {len(unit_of)} heard")


def scope_out():
    """Units out of scope by ear after the gates: the label page's two, and any card of the scope page not kept.
    Refuses while a card is unheard or the answers are another build's, as the heavy page does."""
    out = set(LABEL_PAGE_OUT)
    kp = root() / "scope-key.json"
    if not kp.exists():
        return out
    key = json.loads(kp.read_text())
    p = root() / "scope.json"
    got = json.loads(p.read_text()) if p.exists() else {"build": key["build"], "verdicts": {}}
    if got["build"] != key["build"]:
        raise SystemExit("captures/scope.json is not from the scope page's build")
    cards = [it["unit"] for it in key["items"]]
    unheard = [u for u in cards if u not in got["verdicts"]]
    if unheard:
        raise SystemExit(f"{len(unheard)} scope cards still unheard")
    return out | {u for u in cards if got["verdicts"][u]["verdict"] != "keep"}


# T0 holds these DIs by their crop's slug, not their path (`verified.json` `measure_dis`). A library section's `training_ok` is no
# T0 verdict, and L1b's draw took it for one: the review of `docs/score-ear-plan.md` found 15 of the second batch's 47 units on DIs
# T0 had refused or left unheard.
T0_SLUG = {"cambridge/TheTravellingBand_Quicksand_Full/16_ElecGtr1DI.wav": "cambridge-Quicksand-ElecGtr1",
           "cambridge/TimoAndTheTimezone_JustDontTalk_Full/TimoAndTheTimezone_JustDontTalk_Full/13_ElecGtr3DI.wav":
               "cambridge-just-don-t-talk-elecgtr3",
           "telefunken/Doom Flamingo - Blind Spots LFTL/GTR DI_TDP-1.wav": "telefunken-Blind_Spots-GTR",
           "telefunken/Doom Flamingo - Long Way Home LFTL/GTR DI_TDP-1.wav": "telefunken-Long_Way_Home-GTR",
           "telefunken/Doom Flamingo - Measurements LFTL/GTR DI_TDP-1.wav": "telefunken-Measurements-GTR",
           "telefunken/Doom Flamingo - Strangest Places LFTL/GTR DI_TDP-1.wav": "telefunken-Strangest_Places-GTR",
           "telefunken/Shes Gone Bernard Purdie Tribute All Stars/GTR DI.wav": "telefunken-She's_Gone-GTR"}


def di_verdict(di, verified):
    """T0's verdict on a DI path, from `verified.json`; refuses a DI T0 has no verdict on, since unheard is not trusted."""
    for table in ("dis", "intake_dis"):
        if di in verified[table]:
            return verified[table][di]["verdict"]
    if di in T0_SLUG:
        return verified["measure_dis"][T0_SLUG[di]]["verdict"]
    raise SystemExit(f"{di}: T0 has no verdict on this DI")


def t0_dropped(units, verified=None):
    """The units whose DI T0 did not verify. GOAT's DIs are outside T0, passed by `goat-ear`, and stay."""
    from learn import verify_tracks as VT

    if verified is None:
        verified = json.loads((VT.OUT / "t0" / "verified.json").read_text())
    return {u["unit"] for u in units if not u["di"].startswith("goat/") and di_verdict(u["di"], verified) != "verified"}


def trusted(units):
    """`passed` on the stored verdicts, less `scope_out` and any unit on a DI T0 did not verify; refuses while anything is unheard
    or any page is not the current one."""
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
    ok -= scope_out()
    return ok - t0_dropped([u for u in units if u["unit"] in ok])


def cmd_gate_read(_args):
    """L1c's declared read of its gate, zero renders -> captures3/gate-read.json."""
    from learn import pipeline_fix as P

    P.require(BATCH["phase"])
    if BATCH is not BATCH3:
        raise SystemExit("gate-read is L1c's")
    units = units_of()
    rep = {"phase": BATCH["phase"], **gate_read(units, ear_verdicts(), trusted(units)), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(root() / "gate-read.json", rep)
    print(json.dumps(rep, indent=1))


def lags_of(units):
    """{unit: lag} of `units` and the one-window rule's refused units (`goat_lag_refused`), its median over them."""
    from learn import pipeline_fix as P

    ldir = root() / "lags"
    missing = [u["unit"] for u in units if not (ldir / f"{u['unit'].replace('/', '__')}.json").exists()]
    if missing:
        raise SystemExit(f"{len(missing)} units have no lag: run the lag pass first")
    lags = {u["unit"]: json.loads((ldir / f"{u['unit'].replace('/', '__')}.json").read_text())["lag"] for u in units}
    return lags, P.goat_lag_refused(lags, {u["unit"]: u["item_lag"] for u in units})


def gated_units():
    """The units both gates passed and the lag rule keeps, the lag median taken over them alone. -> (units, {unit: lag})."""
    units = units_of()
    ok = trusted(units)
    tr = [u for u in units if u["unit"] in ok]
    lags, off = lags_of(tr)
    return [u for u in tr if u["unit"] not in off], lags


trusted_units = gated_units                  # the older name; CodeQL reads "trusted" as a secret in code that stores or prints a unit


def search_records():
    """The one loader of the search records: every reader goes through `trusted_units`. -> {unit: record}."""
    from learn import pipeline_fix as P

    keep = {u["unit"] for u in gated_units()[0]}
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


def v2_searcher():
    """N2's search for the capture labels, the short mic lists from GOAT's labels."""
    from learn import knob_ceiling as K
    from learn import night2 as N
    from learn import pipeline_fix as P

    mics = N.mic_lists(P.goat_labels()[0])
    return lambda dims, S, f, amp: N.search_v2(dims, S, f, mics[amp], K.fmt)


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
            print(f"CAPTURE-SEARCH LAGS DONE {k}/{n}: {P.search_units(mine, root(), BATCH['phase'], halves, set(), True, quiet=True)} renders")
            return
        if args.stage == "all":
            gate = root() / "night-check.json"
            if not gate.exists() or json.loads(gate.read_text()).get("stop") is not False:
                raise SystemExit("the rest of the night's labels wait for the fault check, and do not run on its stop")
        by = {u["unit"]: u for u in units}
        mine = [by[u] for j, u in enumerate(stage_set(night_order(units), 0, args.stage)) if j % n == k]
        how = v2_searcher() if args.recipe == "v2" else None
        print(f"CAPTURE-SEARCH DONE {k}/{n} ({args.stage}, {args.recipe}): "
              f"{P.search_units(mine, root(), BATCH['phase'], halves, set(), False, quiet=True, searcher=how)} renders")
        return
    ok = trusted(units)
    tr = [u for u in units if u["unit"] in ok]
    halves = {u["unit"]: u["search"] for u in tr}
    if args.lags_only:
        mine = [u for j, u in enumerate(sorted(tr, key=lambda u: u["unit"])) if j % n == k]
        print(f"CAPTURE-SEARCH LAGS DONE {k}/{n}: {P.search_units(mine, root(), BATCH['phase'], halves, set(), True)} renders")
        return
    lags, off = lags_of(tr)
    items = json.loads((root() / "items.json").read_text())["items"]
    by = {u["unit"]: u for u in tr}
    first = [u for u in [it["unit"] for it in items] + placebo_units(items) if u in by]
    order = search_order([u for u in sorted(by) if u not in off], first)
    todo = stage_set(order, len(first), args.stage)
    if args.stage == "all":
        rest_may_run()
    recs = {u: json.loads(q.read_text())["label"] for u, q in ((u, root() / P.SEARCH_DIR / f"{u.replace('/', '__')}|{by[u]['amp']}.json")
                                                               for u in by) if q.exists()}
    todo += [u for u in fallbacks_due(items, recs) if u not in todo and u in by]
    mine = [by[u] for j, u in enumerate(todo) if j % n == k]
    print(f"CAPTURE-SEARCH DONE {k}/{n} ({args.stage}): {P.search_units(mine, root(), BATCH['phase'], halves, off, False)} renders")


def rest_may_run():
    """The remaining labels and the centre read: only after the label page and the scope page, and never on the primary
    share clear below."""
    gate, stage = root() / "ear-check.json", root() / "stage-check.json"
    rep = json.loads(gate.read_text()) if gate.exists() else {}
    if (rep.get("branch") or HELD_OUT_READ.get(rep.get("build"))) not in ("clear above", "reaching one half"):
        raise SystemExit("the rest waits for the label page, and does not run if the primary share is clear below")
    if not stage.exists() or json.loads(stage.read_text()).get("stop") is not False:
        raise SystemExit("the rest waits for the stage check, and does not run on its stop")
    if not (root() / "scope.json").exists():
        raise SystemExit("the rest waits for the scope page")
    scope_out()                                        # refuses a partial or stale scope page


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
    ap.add_argument("--batch", type=int, choices=(1, 2, 3), default=1)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("dis", "units", "page", "heavy", "scope", "items", "stage-check", "night-check", "gate-read"):
        sub.add_parser(c)
    for c in ("answers", "heavy-answers", "scope-answers"):
        a = sub.add_parser(c)
        a.add_argument("exports", nargs="*")
        a.add_argument("--store", help="the Artifact's stored copy (`answers/<build>-part<k>`), which wins")
    s = sub.add_parser("search")
    s.add_argument("--lags-only", action="store_true")
    s.add_argument("--before-ear", action="store_true")
    s.add_argument("--recipe", choices=("goat", "v2"), default="goat")
    s.add_argument("--stage", default="third")
    s.add_argument("--shard", type=shard, default=(0, 1))
    args = ap.parse_args(argv)
    if args.cmd in ("answers", "heavy-answers", "scope-answers") and not (args.exports or args.store):
        raise SystemExit(f"{args.cmd}: give the stored copy, an Export, or both")
    if args.batch == 2:
        BATCH = BATCH2
    if args.batch == 3:
        if args.cmd not in BATCH3_CMDS:
            raise SystemExit(f"{args.cmd}: not L1c's (no labels, no search on the third batch)")
        BATCH = BATCH3
    {"dis": cmd_dis, "units": cmd_units, "page": cmd_page, "answers": cmd_answers, "heavy": cmd_heavy,
     "heavy-answers": cmd_heavy_answers, "scope": cmd_scope, "scope-answers": cmd_scope_answers, "items": cmd_items,
     "search": cmd_search,
     "stage-check": cmd_stage_check, "night-check": cmd_night_check, "gate-read": cmd_gate_read}[args.cmd](args)


if __name__ == "__main__":
    main()
