"""The DI scope (`docs/full-controls-plan.md`, "C2r and C3r, Amendment 1 (2026-11-10): the DI scope"; ledger
`pipeline-fix` `phase_c2r_a1`): one blind card per library DI file C3r would train on (C2r's n12 and panel blocks), the DI
alone, levelled; Keep, "Drop: too low or too metal", Not sure. Only Keep stays in: a DI file not kept takes every unit on
it out of C2r's records, C3r's rows and every read. Zero renders.

    .venv/bin/python -m learn.di_scope page [--out DIR]     # the page (PF/di-scope by default; refuses over a key)
    .venv/bin/python -m learn.di_scope page-amp [--out DIR] # the same cards, each DI with its session's amp track
    .venv/bin/python -m learn.di_scope answers --store FILE  # the Artifact's stored answers/<build> -> di-scope/verdicts.json
    .venv/bin/python -m learn.di_scope ready                 # exit 0 complete, 3 not yet, 2 never as it stands

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
VERDICTS = (("keep", "Keep", "K"), ("heavy", "Drop: too low or too metal", "D"), ("processed", "Drop: processed", "P"),
            ("unsure", "Not sure", "N"))   # "processed" since the amp-track page (2026-11-11); every non-keep drops
LEAK_WORDS = ("cambridge", "telefunken", "ElecGtr", "DI.wav", "panel", "n12")
INTRO = ("dry guitar recordings (DIs), each on its own, looping. Keep one if it fits the guitar parts the model should "
         "learn from. Drop it if it is tuned too low or played too metal for that, as on the batch 3 page. Only Keep stays "
         "in, so Not sure counts as dropped. All are set to the same loudness, and a tap moves on to the next one. ")


# The amp-track page (2026-11-11, the user's ask: "add the amp track also so I could compare the DI and make sure its not
# processed"): the same 26 cards, ids and build, each DI with the amp track its own session recorded for the same part, at
# the same moment, levelled alike, with an instant switch. n12's DI files -> that amp track, by the session's own names;
# the panel's units carry theirs (`amp_file`). Dark Ride's three DIs have none. At zero renders (2026-11-11) the waveform
# or onset correlation peaks within 2 ms of the same moment on every pair but The Long Wait's, shown with a note.
AMP_PAGE, AMP_KEY = "page-amp.html", "amp-key.json"
SESSION_AMP = {
    "cambridge/AleLak_NossoMundoDeixouDeExistir_Full/09_ElecGtr01DI.wav": "08_ElecGtr01.wav",
    "cambridge/AleLak_NossoMundoDeixouDeExistir_Full/13_ElecGtr02DI.wav": "12_ElecGtr02.wav",
    "cambridge/AleLak_NossoMundoDeixouDeExistir_Full/20_ElecGtr04DI.wav": "19_ElecGtr04.wav",
    "cambridge/AleLak_NossoMundoDeixouDeExistir_Full/24_ElecGtr05DI.wav": "23_ElecGtr05.wav",
    "cambridge/TheTravellingBand_Quicksand_Full/16_ElecGtr1DI.wav": "14_ElecGtr1Close.wav",
    "cambridge/StormOfParticles_OfIceAndHopelessFate_Full/StormOfParticles_OfIceAndHopelessFate_Full/15_ElecGtr04DI.wav":
        "14_ElecGtr04.wav",
    "cambridge/StormOfParticles_OfIceAndHopelessFate_Full/StormOfParticles_OfIceAndHopelessFate_Full/17_ElecGtr05DI.wav":
        "16_ElecGtr05.wav",
    "cambridge/StormOfParticles_OfIceAndHopelessFate_Full/StormOfParticles_OfIceAndHopelessFate_Full/19_ElecGtr06DI.wav":
        "18_ElecGtr06.wav",
    "cambridge/TheLongWait_Drag_Full/TheLongWait_Drag_Full/10_ElecGtr1DI.wav": "08_ElecGtr1Mic1.wav",
    "cambridge/RebuildTheEvil_BurialOfSilence_Full/RebuildTheEvil_BurialOfSilence_Full/21_ElecGtr3DI.wav": "20_ElecGtr3.wav",
    "cambridge/RebuildTheEvil_BurialOfSilence_Full/RebuildTheEvil_BurialOfSilence_Full/23_ElecGtr4DI.wav": "22_ElecGtr4.wav",
    "cambridge/CnocAnTursa_Bannockburn_Full/CnocAnTursa_Bannockburn_Full/32_ElecGtr5DI.wav": "33_ElecGtr5Mic1.wav",
    "cambridge/CnocAnTursa_Bannockburn_Full/CnocAnTursa_Bannockburn_Full/35_ElecGtr6D.wav": "36_ElecGtr6Mic1.wav",
    "cambridge/DeathOfARomantic_TheWell_Full/DeathOfARomantic_TheWell_Full/16_ElecGtr03DI.wav": "15_ElecGtr03.wav",
    "telefunken/Renesans - Labor Of Hate/Renesans - Labor Of Hate Take 2/GTR 1 DI_TDP-1.wav": "GTR 1 Amp_M81.wav",
}
NO_SESSION_AMP = ("cambridge/DarkRide_DeadEnemies_Full/27_ElecGtr09DI.wav",
                  "cambridge/DarkRide_DeadEnemies_Full/28_ElecGtr10DI.wav",
                  "cambridge/DarkRide_DeadEnemies_Full/29_ElecGtr11DI.wav")
UNALIGNED = ("cambridge/TheLongWait_Drag_Full/TheLongWait_Drag_Full/10_ElecGtr1DI.wav",)
NO_AMP_NOTE = "No amp track was recorded with this DI."
UNALIGNED_NOTE = "This amp track does not clearly line up with the DI: it may be another take."
AMP_INTRO = ("dry guitar recordings (DIs), each on its own, looping. Each also has the amp track recorded with it, where "
             "there is one, at the same moment and the same loudness: switch between them to check that the DI is clean, "
             "not already processed. Judge the DI. Keep one if it fits the guitar parts the model should learn from. Drop "
             "it if it is tuned too low or played too metal, or if it is processed. Only Keep stays in, so Not sure counts "
             "as dropped. A tap moves on to the next one. ")


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


def amp_sources(items, n12, panel, di_meta):
    """Each card's amp track: {card id: {path, start, di_file} or None}. n12: the session's track for the DI file
    (`SESSION_AMP`) at the section's start in the DI file (batch 2's `di_meta`); the panel: the unit's own amp file at its
    window. Refuses an n12 DI file in neither list."""
    by = {u["unit"]: u for u in list(n12) + list(panel)}
    out = {}
    for it in items:
        u = by[it["unit"]]
        if it["set"] == "n12":
            if it["di"] in NO_SESSION_AMP:
                out[it["id"]] = None
                continue
            if it["di"] not in SESSION_AMP:
                raise SystemExit(f"{it['di']}: no session amp track named")
            m = di_meta[u["di_item"]]
            out[it["id"]] = {"path": str(pathlib.Path(m["di_path"]).parent / SESSION_AMP[it["di"]]),
                             "start": float(m["start_s"]), "di_file": m["di_path"]}
        else:
            out[it["id"]] = {"path": u["amp_file"], "start": float(u["window_s"]), "di_file": u["di_file"]}
    return out


AMP_CSS = """
.ab { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:.6rem 0 .2rem; }
.ab button { min-height:48px; }
.ab button[aria-pressed="true"] { background:var(--on); color:var(--on-fg); border-color:var(--on); }
#note { min-height:1.2em; color:var(--mute); font-size:.9rem; margin:.2rem 0 .6rem; }
"""

AMP_JS = [   # (old, new) on scope_page's script: two sources a card, started together, switched by gain
    ('const bufs = {};',
     'const bufs = {}, AMP = DATA.amp || {}, NOTES = DATA.notes || {};\nlet side = "d", gains = null, srcs = [];'),
    ('function prune() { const near = new Set([at - 1, at, at + 1, openFrom(at)].map(j => ids[j]));',
     'function prune() { const near = new Set();\n  [at - 1, at, at + 1, openFrom(at)].forEach(j => { const id = ids[j]; '
     'if (id) { near.add(id); if (AMP[id]) near.add(AMP[id]); } });'),
    ('function stop() { token++; if (src) { try { src.stop(); } catch (e) {} src = null; }',
     'function stop() { token++; srcs.forEach(s => { try { s.stop(); } catch (e) {} }); srcs = []; src = null; gains = null;'),
    ('  let b;\n'
     '  try { b = await decode(id); } catch (e) { delete bufs[id]; $("now").textContent = "This clip did not load. Press Play '
     'to try again."; return; }\n'
     '  if (my !== token) return;\n'
     '  src = actx.createBufferSource(); src.buffer = b; src.loop = true; src.connect(actx.destination); src.start();\n'
     '  $("now").textContent = "Playing (it loops)"; $("play").textContent = "Stop";',
     '  let b, ba = null;\n'
     '  try { b = await decode(id); if (AMP[id]) ba = await decode(AMP[id]); }\n'
     '  catch (e) { delete bufs[id]; if (AMP[id]) delete bufs[AMP[id]]; $("now").textContent = "This clip did not load. Press '
     'Play to try again."; return; }\n'
     '  if (my !== token) return;\n'
     '  const end = ba ? Math.min(b.duration, ba.duration) : b.duration, t0 = actx.currentTime + 0.05;\n'
     '  gains = {d: actx.createGain(), a: actx.createGain()};\n'
     '  srcs = [[b, gains.d]].concat(ba ? [[ba, gains.a]] : []).map(([buf, g]) => { const s = actx.createBufferSource();\n'
     '    s.buffer = buf; s.loop = true; s.loopStart = 0; s.loopEnd = end; s.connect(g); g.connect(actx.destination); '
     's.start(t0); return s; });\n'
     '  src = srcs[0]; setSide(side); $("play").textContent = "Stop";'),
    ('const nx = openFrom(at); if (nx >= 0) decode(ids[nx]).catch(() => {});',
     'const nx = openFrom(at); if (nx >= 0) { decode(ids[nx]).catch(() => {}); if (AMP[ids[nx]]) '
     'decode(AMP[ids[nx]]).catch(() => {}); }'),
    ('function go(i) { at = i; arm(false); paint(); }',
     'function go(i) { at = i; side = "d"; arm(false); paint(); }\n'
     'function setSide(s) { if (s === "a" && !AMP[ids[at]]) s = "d"; side = s;\n'
     '  if (gains) { const t = actx.currentTime; gains.d.gain.setTargetAtTime(s === "d" ? 1 : 0, t, 0.004);\n'
     '    gains.a.gain.setTargetAtTime(s === "a" ? 1 : 0, t, 0.004);\n'
     '    $("now").textContent = s === "a" ? "Playing the amp track (it loops)" : "Playing the DI (it loops)"; }\n'
     '  paint(); }'),
    ('  $("back").disabled = at === 0;',
     '  $("back").disabled = at === 0;\n'
     '  $("sa").disabled = !AMP[ids[at]]; $("sd").setAttribute("aria-pressed", String(side === "d"));\n'
     '  $("sa").setAttribute("aria-pressed", String(side === "a")); $("note").textContent = NOTES[ids[at]] || "";'),
    ('$("back").addEventListener("click", back);',
     '$("back").addEventListener("click", back);\n$("sd").addEventListener("click", () => setSide("d"));\n'
     '$("sa").addEventListener("click", () => setSide("a"));'),
    ('if (k === "k") answer("keep"); else if (k === "d") answer("heavy"); else if (k === "n") answer("unsure");',
     'if (k === "k") answer("keep"); else if (k === "d") answer("heavy"); else if (k === "n") answer("unsure");\n'
     '  else if (k === "p") answer("processed"); else if (k === "a") setSide(side === "a" ? "d" : "a");'),
]


def page_html_amp(ids, clips, amp, notes, build):
    """The DI page with each card's amp track: the same ids and build, so the answers stored so far carry over. amp: {card
    id: its amp clip's id}; notes: {card id: text}."""
    page = page_html(ids, clips, build)
    i0, i1 = page.index('<p class="intro">'), page.index('<span id="saveline">')
    page = page[:i0] + '<p class="intro">' + f"{len(ids)} " + AMP_INTRO + page[i1:]
    swaps = [("</style>", AMP_CSS + "</style>"),
             ('<p id="now">Press Play to start.</p>',
              '<div class="ab"><button type="button" id="sd" aria-pressed="true">DI</button>'
              '<button type="button" id="sa" aria-pressed="false">Amp track</button></div><p id="note"></p>\n'
              '<p id="now">Press Play to start.</p>'),
             ("Keys: K keep, D drop, N not sure, space play or stop, arrows back and skip.",
              "Keys: K keep, D drop (too low or metal), P drop (processed), N not sure, A switch DI and amp track, space "
              "play or stop, arrows back and skip."),
             (json.dumps({"build": build, "items": ids}), json.dumps({"build": build, "items": ids, "amp": amp,
                                                                     "notes": notes}))]
    for old, new in swaps + AMP_JS:
        if page.count(old) != 1:
            raise SystemExit(f"the scope page changed: {old[:60]!r} is not there once")
        page = page.replace(old, new)
    return page


def cmd_page_amp(args):
    """The amp-track page -> DIR/page-amp.html and DIR/amp-key.json. Never touches key.json; refuses unless the cards are
    the published build's, and over an existing amp key."""
    import numpy as np
    import soundfile as sf

    from learn import build_data_review as BDR
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import scope_page as SP

    d = scope_dir()
    out = pathlib.Path(args.out) if args.out else d
    if (out / AMP_KEY).exists():
        raise SystemExit(f"{out / AMP_KEY} exists: move it aside first")
    key = json.loads((d / "key.json").read_text())
    _, ids, build = page_cards()
    if build != BUILD or key["build"] != BUILD or ids != [it["id"] for it in key["items"]]:
        raise SystemExit("the cards are not the published page's")
    n12, panel = library_units()
    meta = json.loads((P.out_dir() / "captures2" / "plan.json").read_text())["di_meta"]
    src = amp_sources(key["items"], n12, panel, meta)
    clips, amp, notes, rows = {}, {}, {}, []
    for it in key["items"]:
        y, sr = sf.read(it["path"], always_2d=True)
        y = y.mean(1)
        a = int(it["start"] * sr)
        y, _, _, _ = BDR.level_clip(y[a:a + int(WINDOW_S * sr)])
        clips[it["id"]] = SP.encode(y, out / "aac-cache")            # the published clip: the same steps, the same cache
        s = src[it["id"]]
        row = {"id": it["id"], "di": it["di"], "set": it["set"], "amp": None}
        if s is None:
            notes[it["id"]] = NO_AMP_NOTE
        else:
            z = np.asarray(PS.load_mono(s["path"], BDR.SR, s["start"], WINDOW_S), np.float64)
            z = np.pad(z, (0, max(0, len(y) - len(z))))[:len(y)]
            z, gain, _, cut = BDR.level_clip(z)
            amp[it["id"]] = it["id"] + "a"
            clips[it["id"] + "a"] = SP.encode(z, out / "aac-cache")
            row.update(amp=s["path"], start=s["start"], di_file=s["di_file"], gain_db=gain, peak_cut_db=cut)
            if it["di"] in UNALIGNED:
                notes[it["id"]] = UNALIGNED_NOTE
        rows.append(row)
    page = page_html_amp(ids, clips, amp, notes, build)
    shown = leaks(page)
    if shown:
        raise SystemExit(f"the page names {shown}")
    out.mkdir(parents=True, exist_ok=True)
    (out / AMP_PAGE).write_text(page)
    (out / AMP_KEY).write_text(json.dumps({"page": DIR, "build": build, "window_s": WINDOW_S, "items": rows,
                                           "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
    print(f"DI SCOPE AMP PAGE {len(rows)} cards, {len(amp)} with an amp track, build {build}, {len(page) / 1e6:.1f} MB "
          f"-> {out / AMP_PAGE}")


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
    vp = d / "verdicts.json"
    if vp.exists():                                    # a later sitting may only add answers, never change one
        got = merged_verdicts(json.loads(vp.read_text()), got, key["build"])
    rec = {"page": DIR, "build": key["build"], "store": str(args.store), "verdicts": got,
           "answered": len(got), "cards": len(key["items"]), "complete": len(got) == len(key["items"]),
           "dropped": sorted(di for di, v in got.items() if v != "keep"), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(d / "verdicts.json", rec)
    c = {}
    for v in got.values():
        c[v] = c.get(v, 0) + 1
    print(f"DI SCOPE ANSWERS: {len(got)} of {len(key['items'])} heard; {c}; dropped {len(rec['dropped'])} DI files")


def merged_verdicts(old, new, build):
    """A stored verdicts record and a new sitting's {di: verdict} -> every answer: the stored ones and the new. Refuses a
    stored answer changed (a scope_out record already written on it would go stale) and another build's record."""
    if old.get("build") != build:
        raise SystemExit(f"verdicts.json is build {old.get('build')}'s, this page's is {build}: move it aside first")
    prev = old.get("verdicts") or {}
    changed = sorted(di for di, v in new.items() if di in prev and prev[di] != v)
    if changed:
        raise SystemExit(f"{len(changed)} stored answers would change (first {changed[0]}: {prev[changed[0]]} -> "
                         f"{new[changed[0]]}): a later sitting may only add answers")
    return {**prev, **new}


def ready_state():
    """The scope's state for a waiting launcher: (0, why) complete, (3, why) not yet (missing or partial), (2, why) never
    on its own (another build's verdicts, or an unreadable file): the launcher stops and says why."""
    try:
        v = verdicts()
    except SystemExit as e:
        return 2, str(e)
    except (ValueError, OSError) as e:
        return 2, f"{DIR}/verdicts.json unreadable: {e}"
    why = complete_refusal(v)
    return (0, f"complete: {N_CARDS} answers for build {BUILD}") if why is None else (3, why)


def cmd_ready(_args):
    """Exit 0 when the verdicts hold every answer, 3 while they don't yet, 2 when they never will as they stand."""
    code, why = ready_state()
    print(f"DI SCOPE {'READY' if code == 0 else 'WAITING' if code == 3 else 'REFUSED'}: {why}", flush=True)
    raise SystemExit(code)


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
    q = sub.add_parser("page-amp")
    q.add_argument("--out", help="the folder to build into (default PF/di-scope)")
    q.set_defaults(fn=cmd_page_amp)
    a = sub.add_parser("answers")
    a.add_argument("--store", required=True, help="the Artifact's stored answers/<build>, as a file")
    a.set_defaults(fn=cmd_answers)
    sub.add_parser("ready").set_defaults(fn=cmd_ready)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
