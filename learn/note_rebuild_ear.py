"""The note rebuild's ear check page (`docs/note-rebuild-plan.md` section 11e; ledger `note-rebuild` `phase_nr_1_ear`):
the clips `note_rebuild_s1 clips` wrote, on the regular card page of `ear_vreal` / `c1a_ear` (one numbered card per
recording, its play buttons and its answer buttons on the same card, answers kept in the page's db `answers/<build>`).

    .venv/bin/python -m learn.note_rebuild_ear page                # the page from the stored clips (zero renders)
    .venv/bin/python -m learn.note_rebuild_ear read OUT --answers F  # the declared read of the stored answers

One card per window and preset (4 items x clean, crunch = 8 cards). Each card plays the recorded DI and the two rebuilt
dry guitars through the same preset, looping and switching at the same place. For each rebuilt guitar the listener
marks "sounds like a real guitar on these notes", or each fault heard (hiss, out of tune, clicks or crackle, one note
much louder, timing), or "can't judge"; a note per card is optional. Not blind: the plan's ear check asks whether a
rebuilt guitar has a fault, not which is closer, so each version is named.

The read (`ear_verdict`, pure): "fault" when any card marks a fault on either rebuilt guitar (each listed with the
card's note); otherwise "incomplete" when a version on any card is unanswered; otherwise "undecided" when any version
on any card is "can't judge" (the cards listed: it goes to the orchestrator and the user, and `phase_nr_1_ear` is not
recorded as "ok" from it); otherwise "ok", every version on every card heard as real. Notes on cards without a fault
are listed beside, for the orchestrator to read before the verdict is recorded.

The redo's page (`docs/note-rebuild-plan.md` section 12; ledger `phase_nr_1_redo_ear`), in its own folder
`listening/note-rebuild-ear-page-2`, every file written once; the old page's key.json is never overwritten:

    .venv/bin/python -m learn.note_rebuild_ear redo-page                 # from `note_transcribe clips` (zero renders)
    .venv/bin/python -m learn.note_rebuild_ear redo-read OUT --answers F # `redo_verdict` of the stored answers

13 cards (8 clean, 4 crunch, 1 hidden control: the true DI as "Rebuilt"), each with the recorded DI and Rebuilt, and on
the card "Same notes and timing (the guitar's own sound may differ)", the content faults (missing notes, chords played as
single notes, notes cut short, extra or wrong notes), the signal faults (as above), "can't judge" and a note.
`redo_verdict` (pure): fault-content, fault-signal, incomplete, ask, ok, the first that holds.
"""

from __future__ import annotations

import argparse
import hashlib
import json

PHASE = "phase_nr_1_ear"
VERSIONS = (("A", "nr-plain", "Rebuilt A", "even levels"), ("B", "nr-level", "Rebuilt B", "levels from the record"))
CLASSES = ("clean", "crunch")
FAULTS = (("hiss", "Hiss"), ("tune", "Out of tune"), ("clicks", "Clicks or crackle"), ("loud", "One note much louder"),
          ("timing", "Timing off"))
TITLE = "Rebuilt Guitar Ear Check"

INTRO = """<h1>Do the rebuilt guitars sound like a real guitar?</h1>
<p class="intro">@@COUNT@@ recordings of 10 seconds, looping. Each card plays one window of a guitar part through one
plugin preset (clean or crunch). <b>Recorded DI</b> is the player's own guitar. <b>Rebuilt A</b> and <b>Rebuilt B</b> play
the same notes from a Stratocaster's single recorded notes: A at even levels, B at the levels of the recording. Everything
loops together and switches instantly at the same place: tap a button, or press R, A, B (or 1-3); Space stops. All clips
are set to the same loudness. Headphones, please.</p>
<p class="intro">For each rebuilt guitar, tap <b>Sounds real</b> if it sounds like a real guitar playing these notes, or tap
every fault you hear: hiss the Recorded DI does not have, notes out of tune or beating, clicks or crackle as notes ring
down, one note or chord much louder than its neighbours, notes early or late against the Recorded DI. A different tone
colour from the player's guitar is expected and is not a fault. <b>Can't judge</b> and the note are optional.
Answers are saved in this browser as you go; tap <b>Export</b> any time and send the text.</p>"""

CSS_EXTRA = """.cls { color:var(--mute); font-size:.85rem; margin:-.5rem 0 .6rem; }
.ver { border-top:1px solid var(--line); margin-top:.7rem; padding-top:.2rem; }
.conf.faults button { flex:1 1 120px; font-size:.9rem; }
.conf .sub { color:var(--mute); font-size:.85rem; flex-basis:100%; }
"""

# The player of `ear_vreal` is kept up to its answers; the answers are this page's own.
HEAD_EDITS = (
    ('const STORE = "ear-vreal:" + DATA.build;', 'const STORE = "note-rebuild-ear:" + DATA.build;'),
    ('KEYS = ["ref", "A", "B", "C", "D"]', 'KEYS = ["ref", "A", "B"]'),
    ('const NAMES = {ref: "the record\'s guitar", A: "A", B: "B", C: "C", D: "D"};',
     'const NAMES = {ref: "the recorded DI", A: "Rebuilt A (even levels)", B: "Rebuilt B (levels from the record)"};'),
)
ANSWERS_JS = r"""
const VERS = ["A", "B"];
function answered(v) { return !!v && (v.real || v.cant || (v.faults || []).length > 0); }
function paint() {
  let n = 0;
  items.forEach(it => {
    const a = ans[it.dataset.id] || {};
    VERS.forEach(l => {
      const v = a[l] || {};
      it.querySelectorAll('.ver[data-l="' + l + '"] button').forEach(b => b.setAttribute("aria-pressed", String(
        b.dataset.a === "real" ? !!v.real : b.dataset.a === "cant" ? !!v.cant : (v.faults || []).includes(b.dataset.f))));
    });
    const full = VERS.every(l => answered(a[l]));
    it.querySelector(".done").textContent = full ? "Answered" : "";
    if (full) n++;
    const note = it.querySelector(".note"); if (document.activeElement !== note) note.value = a.note || "";
  });
  document.getElementById("count").textContent = n + " of " + items.length + " answered";
}
items.forEach(it => {
  const id = it.dataset.id;
  it.querySelectorAll(".src").forEach(b => b.addEventListener("click", () => pick(it, b.dataset.k)));
  it.querySelector(".stop").addEventListener("click", stop);
  it.querySelectorAll(".ver button").forEach(b => b.addEventListener("click", () => {
    const l = b.closest(".ver").dataset.l;
    const a = ans[id] = ans[id] || {}; const v = a[l] = a[l] || {};
    if (b.dataset.a === "real" || b.dataset.a === "cant") {      // each excludes the other and every fault
      const k = b.dataset.a, on = !v[k];
      a[l] = on ? {[k]: true} : {};
    } else {
      const f = new Set(v.faults || []);
      if (f.has(b.dataset.f)) f.delete(b.dataset.f); else f.add(b.dataset.f);
      a[l] = f.size ? {faults: Array.from(f)} : {};
    }
    save(); paint();
  }));
  it.querySelector(".note").addEventListener("input", e => {
    const a = ans[id] = ans[id] || {}; a.note = e.target.value; save(); paint(); });
});
document.addEventListener("keydown", e => {
  if (e.metaKey || e.ctrlKey || e.altKey || (e.target.closest && e.target.closest("input, textarea"))) return;
  const it = cur ? cur.it : document.querySelector(".item.current") || items[0];
  const m = {r: "ref", a: "A", b: "B", "1": "ref", "2": "A", "3": "B"};
  const k = (e.key || "").toLowerCase();
  if (m[k]) { e.preventDefault(); pick(it, m[k]); }
  else if (k === "escape" || k === " ") { e.preventDefault(); stop(); }
});
function exportText() {
  const lines = ["note-rebuild-ear build " + DATA.build + " " + new Date().toISOString()];
  items.forEach(it => {
    const a = ans[it.dataset.id] || {};
    const say = v => !v ? "-" : v.real ? "real" : v.cant ? "cant" : (v.faults || []).join("+") || "-";
    lines.push(it.dataset.n + " A:" + say(a.A) + " B:" + say(a.B) + (a.note ? " | " + a.note : ""));
  });
  lines.push(JSON.stringify({build: DATA.build, answers: ans}));
  return lines.join("\n");
}
"""


def player_js():
    """`ear_vreal`'s player (decode, loop, switch at the same place) with this page's answers."""
    from learn import ear_vreal as E

    js = E.JS
    for old, new in HEAD_EDITS:
        if old not in js:
            raise SystemExit(f"ear_vreal's player changed: {old[:60]}")
        js = js.replace(old, new)
    a, b = js.index("function paint() {"), js.index('document.getElementById("export")')
    return (js[:a] + ANSWERS_JS.lstrip("\n") + js[b:]).replace('"ear-vreal-answers-"', '"note-rebuild-ear-answers-"')


def cards(items):
    """Each card: the recorded DI and the two rebuilt guitars to play; per rebuilt guitar, "sounds real", each fault,
    or "can't judge"; a note."""
    out = []
    for it in items:
        vers = "".join(
            f'<div class="ver" data-l="{l}"><div class="q">{name} ({what})</div>'
            '<div class="conf"><button type="button" data-a="real">Sounds real</button>'
            '<button type="button" data-a="cant">Can\'t judge</button></div>'
            '<div class="conf faults"><span class="sub">or every fault you hear:</span>'
            + "".join(f'<button type="button" data-f="{f}">{t}</button>' for f, t in FAULTS) + "</div></div>"
            for l, _, name, what in VERSIONS)
        out.append(
            f'<article class="item" data-id="{it["id"]}" data-n="{it["n"]}">'
            f'<div class="num">{it["n"]} / {len(items)}</div><h3>Recording {it["n"]}</h3>'
            f'<p class="cls">{it["cls"]} preset</p><div class="plays">'
            '<button type="button" class="src" data-k="ref" aria-pressed="false">Recorded DI (R)</button>'
            + "".join(f'<button type="button" class="src" data-k="{l}" aria-pressed="false">{name}</button>'
                      for l, _, name, _ in VERSIONS)
            + '<button type="button" class="stop" aria-label="Stop">&#9632;</button></div><p class="now"></p>'
            + vers + '<input class="note" type="text" placeholder="Note (optional)" aria-label="Note">'
            '<div class="done"></div></article>')
    return "".join(out)


def page_items(index):
    """(Pure.) The clips index -> the cards in a fixed order (item, then clean before crunch), each with its three
    clips' files and sha256. Refuses an index without exactly the recorded DI and both rebuilt guitars per card."""
    got = {}
    for c in index["clips"]:
        got.setdefault((c["item"], c["cls"]), {})[c["dry"]] = {"file": c["file"], "sha256": c["sha256"]}
    want = {"true", *(arm for _, arm, _, _ in VERSIONS)}
    out = []
    for n, (item, cls) in enumerate(sorted(got, key=lambda k: (k[0], CLASSES.index(k[1]))), 1):
        if set(got[(item, cls)]) != want:
            raise SystemExit(f"{item} {cls}: clips {sorted(got[(item, cls)])}, not {sorted(want)}")
        out.append({"id": f"c{n}", "n": n, "item": item, "cls": cls, "clips": got[(item, cls)]})
    return out


def build_id(items):
    """(Pure.) The page's build: the hash of its cards' clips, so republishing the same clips keeps the answers."""
    return hashlib.sha256(json.dumps([[it["item"], it["cls"], it["clips"]] for it in items],
                                     sort_keys=True).encode()).hexdigest()[:12]


def ear_verdict(items, answers):
    """(Pure.) The declared read of the stored answers. -> {verdict, faults, unanswered, cant_judge, notes}."""
    faults, unanswered, cant, notes = [], [], [], []
    for it in items:
        a = answers.get(it["id"]) or {}
        mine = []
        for l, arm, _, _ in VERSIONS:
            v = a.get(l) or {}
            if v.get("faults"):
                mine.append({"version": arm, "faults": sorted(v["faults"])})
            elif v.get("cant"):
                cant.append({"n": it["n"], "version": arm})
            elif not v.get("real"):
                unanswered.append({"n": it["n"], "version": arm})
        where = {"n": it["n"], "item": it["item"], "cls": it["cls"]}
        note = (a.get("note") or "").strip()
        if mine:
            faults.append({**where, "heard": mine, "note": note})
        elif note:
            notes.append({**where, "note": note})
    verdict = "fault" if faults else "incomplete" if unanswered else "undecided" if cant else "ok"
    return {"verdict": verdict, "faults": faults, "unanswered": unanswered, "cant_judge": cant, "notes": notes}


def page_html(items, clips, build):
    """The local page. -> (html, css, js)."""
    from learn import ear_vreal as E

    js, css = player_js(), E.CSS + CSS_EXTRA
    a, b = E.PAGE.index("<h1>"), E.PAGE.index("@@CARDS@@")
    data = json.dumps({"build": build, "items": [{"id": it["id"], "n": it["n"]} for it in items]})
    page = (E.PAGE[:a] + INTRO + "\n" + E.PAGE[b:]).replace("@@COUNT@@", str(len(items))) \
        .replace("@@CARDS@@", cards(items)).replace("@@CSS@@", css).replace("@@DATA@@", data) \
        .replace("@@CLIPS@@", json.dumps(clips)).replace("@@JS@@", js)
    if "<title>Record tone check</title>" not in page:
        raise SystemExit("ear_vreal's page title changed")
    return page.replace("<title>Record tone check</title>", f"<title>{TITLE}</title>"), css, js


def artifact_page(page, css, js):
    """`c1a_ear`'s Artifact page (themes, no wrapper, answers kept in `answers/<build>`), under this page's title."""
    from learn import c1a_ear as C

    out = C.artifact_page(page, css, js)
    old = "<title>Record A/B Check</title>"
    if not out.startswith(old):
        raise SystemExit("c1a_ear's artifact title changed")
    return f"<title>{TITLE}</title>" + out[len(old):]


def page_dir():
    from learn import pretrain_set as PS

    return PS.HOME / "listening" / "note-rebuild-ear-page"


def cmd_page(_args):
    """The page from the clips `note_rebuild_s1 clips` wrote (each checked against its index's sha256), each folded to
    mono (the plugin's two channels) and AAC-encoded as the regular pages are -> note-rebuild-ear-page/{index.html,
    artifact.html, key.json}."""
    import numpy as np
    import soundfile as sf

    from learn import ear_vreal as E
    from learn import note_rebuild as NR
    from learn import note_rebuild_s1 as S1

    if (page_dir() / "key.json").exists():          # the redo (2026-11-22): the old page's key is never overwritten
        raise SystemExit(f"{page_dir() / 'key.json'} exists: never overwritten (the redo's page is `redo-page`)")
    src = S1.clips_dir()
    index = json.loads((src / "index.json").read_text())
    if not index.get("all_ok"):
        raise SystemExit("the clips' pre-checks did not all pass")
    items = page_items(index)
    build = build_id(items)
    clips, spread = {}, 0.0
    for it in items:
        for k, dry in (("ref", "true"), *((l, arm) for l, arm, _, _ in VERSIONS)):
            f = src / it["clips"][dry]["file"]
            if NR.file_sha(f) != it["clips"][dry]["sha256"]:
                raise SystemExit(f"{f.name}: not the clip its index records")
            y, sr = sf.read(f, dtype="float64", always_2d=True)
            if sr != E.SR:
                raise SystemExit(f"{f.name}: {sr} Hz")
            spread = max(spread, float(np.abs(y[:, 0] - y[:, -1]).max()))
            clips[f"{it['id']}-{k}"] = E.encode(y.mean(1), page_dir() / "aac-cache")
    page, css, js = page_html(items, clips, build)
    out = page_dir()
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page)
    (out / "artifact.html").write_text(artifact_page(page, css, js))
    (out / "key.json").write_text(json.dumps({"phase": PHASE, "build": build, "items": items}, indent=1))
    print(f"NOTE-REBUILD-EAR PAGE: {len(items)} cards, build {build}; channels differ by at most {spread:.2e}; "
          f"{(out / 'artifact.html').stat().st_size / 1e6:.1f} MB -> {out / 'artifact.html'}", flush=True)


def cmd_read(args):
    """The declared read of the stored answers (`answers/<build>` or the Export text) -> OUT.json."""
    import pathlib

    from learn import ear_eat as EE

    key = json.loads((page_dir() / "key.json").read_text())
    ex = EE.stored_answers(pathlib.Path(args.answers).read_text())
    if ex.get("build") != key["build"]:
        raise SystemExit(f"answers for build {ex.get('build')}, the page's is {key['build']}")
    rep = {"phase": PHASE, "build": key["build"], **ear_verdict(key["items"], ex["answers"])}
    pathlib.Path(args.out).write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


# --- the redo's page (`docs/note-rebuild-plan.md` section 12; ledger `phase_nr_1_redo_ear`) -------------------------------
# A new page in a new folder, `listening/note-rebuild-ear-page-2`, from the clips `note_transcribe clips` wrote to
# `listening/note-rebuild-ear-2`; every file written once. The old page (`note-rebuild-ear-page`) and its key.json are
# never touched by these commands. Same regular card layout: one numbered card per recording, its play buttons and its
# answer buttons on the card, answers kept in the page's db (`answers/<build>`) and Export.

REDO_PHASE = "phase_nr_1_redo_ear"
REDO_TITLE = "Rebuilt Guitar Notes Check"
REDO_SAME = "Same notes and timing"
REDO_SAME_SUB = "the guitar's own sound may differ"
CONTENT_FAULTS = (("missing", "Missing notes"), ("chords", "Chords played as single notes"),
                  ("short", "Notes cut short"), ("extra", "Extra or wrong notes"))
SIGNAL_FAULTS = FAULTS                  # hiss, out of tune, clicks or crackle, one note much louder, timing off
REAL_CARDS = 12                         # 8 clean, 4 crunch; plus one hidden control
REDO_VERDICTS = ("ok", "fault-content", "fault-signal", "ask", "incomplete")

REDO_INTRO = """<h1>Does the rebuilt guitar play the same notes?</h1>
<p class="intro">@@COUNT@@ recordings of 10 seconds, looping. Each card plays one window of a guitar part through one
plugin preset (clean or crunch). <b>Recorded DI</b> is the player's own guitar. <b>Rebuilt</b> plays the notes read from
it, from a Stratocaster's single recorded notes. Both loop together and switch instantly at the same place: tap a
button, or press R or B (or 1, 2); Space stops. Both are set to the same loudness. Headphones, please.</p>
<p class="intro">Tap <b>Same notes and timing</b> when Rebuilt plays the notes the Recorded DI plays, when it plays them.
The guitar's own sound may differ: a different tone colour is expected and is not a fault. Otherwise tap every fault you
hear: notes missing, chords played as single notes, notes cut short, extra or wrong notes; or hiss the Recorded DI does
not have, notes out of tune or beating, clicks or crackle, one note or chord much louder than its neighbours, notes early
or late. <b>Can't judge</b> and the note are optional.
Answers are saved in this browser as you go; tap <b>Export</b> any time and send the text.</p>"""

REDO_HEAD_EDITS = (
    ('const STORE = "ear-vreal:" + DATA.build;', 'const STORE = "note-rebuild-ear-2:" + DATA.build;'),
    ('KEYS = ["ref", "A", "B", "C", "D"]', 'KEYS = ["ref", "B"]'),
    ('const NAMES = {ref: "the record\'s guitar", A: "A", B: "B", C: "C", D: "D"};',
     'const NAMES = {ref: "the recorded DI", B: "Rebuilt"};'),
)
REDO_ANSWERS_JS = r"""
function answered(v) { return !!v && (v.same || v.cant || (v.faults || []).length > 0); }
function paint() {
  let n = 0;
  items.forEach(it => {
    const v = ans[it.dataset.id] || {};
    it.querySelectorAll(".ver button").forEach(b => b.setAttribute("aria-pressed", String(
      b.dataset.a === "same" ? !!v.same : b.dataset.a === "cant" ? !!v.cant : (v.faults || []).includes(b.dataset.f))));
    const full = answered(v);
    it.querySelector(".done").textContent = full ? "Answered" : "";
    if (full) n++;
    const note = it.querySelector(".note"); if (document.activeElement !== note) note.value = v.note || "";
  });
  document.getElementById("count").textContent = n + " of " + items.length + " answered";
}
items.forEach(it => {
  const id = it.dataset.id;
  it.querySelectorAll(".src").forEach(b => b.addEventListener("click", () => pick(it, b.dataset.k)));
  it.querySelector(".stop").addEventListener("click", stop);
  it.querySelectorAll(".ver button").forEach(b => b.addEventListener("click", () => {
    const v = ans[id] = ans[id] || {}; const note = v.note;
    if (b.dataset.a === "same" || b.dataset.a === "cant") {      // each excludes the other and every fault
      const k = b.dataset.a, on = !v[k];
      ans[id] = on ? {[k]: true} : {};
    } else {
      const f = new Set(v.faults || []);
      if (f.has(b.dataset.f)) f.delete(b.dataset.f); else f.add(b.dataset.f);
      ans[id] = f.size ? {faults: Array.from(f)} : {};
    }
    if (note) ans[id].note = note;
    save(); paint();
  }));
  it.querySelector(".note").addEventListener("input", e => {
    const v = ans[id] = ans[id] || {}; v.note = e.target.value; save(); paint(); });
});
document.addEventListener("keydown", e => {
  if (e.metaKey || e.ctrlKey || e.altKey || (e.target.closest && e.target.closest("input, textarea"))) return;
  const it = cur ? cur.it : document.querySelector(".item.current") || items[0];
  const m = {r: "ref", b: "B", "1": "ref", "2": "B"};
  const k = (e.key || "").toLowerCase();
  if (m[k]) { e.preventDefault(); pick(it, m[k]); }
  else if (k === "escape" || k === " ") { e.preventDefault(); stop(); }
});
function exportText() {
  const lines = ["note-rebuild-ear-2 build " + DATA.build + " " + new Date().toISOString()];
  items.forEach(it => {
    const v = ans[it.dataset.id] || {};
    const say = !v ? "-" : v.same ? "same" : v.cant ? "cant" : (v.faults || []).join("+") || "-";
    lines.push(it.dataset.n + " " + say + (v.note ? " | " + v.note : ""));
  });
  lines.push(JSON.stringify({build: DATA.build, answers: ans}));
  return lines.join("\n");
}
"""


def redo_player_js():
    """`ear_vreal`'s player (decode, loop, switch at the same place) with the redo page's answers."""
    from learn import ear_vreal as E

    js = E.JS
    for old, new in REDO_HEAD_EDITS:
        if old not in js:
            raise SystemExit(f"ear_vreal's player changed: {old[:60]}")
        js = js.replace(old, new)
    a, b = js.index("function paint() {"), js.index('document.getElementById("export")')
    return (js[:a] + REDO_ANSWERS_JS.lstrip("\n") + js[b:]).replace('"ear-vreal-answers-"',
                                                                    '"note-rebuild-ear-2-answers-"')


def redo_cards(items):
    """Each card: the recorded DI and Rebuilt to play; "Same notes and timing", each content fault, each signal fault,
    or "can't judge"; a note. The hidden control looks like every other card."""
    def buttons(faults):
        return "".join(f'<button type="button" data-f="{f}">{t}</button>' for f, t in faults)
    out = []
    for it in items:
        out.append(
            f'<article class="item" data-id="{it["id"]}" data-n="{it["n"]}">'
            f'<div class="num">{it["n"]} / {len(items)}</div><h3>Recording {it["n"]}</h3>'
            f'<p class="cls">{it["cls"]} preset</p><div class="plays">'
            '<button type="button" class="src" data-k="ref" aria-pressed="false">Recorded DI (R)</button>'
            '<button type="button" class="src" data-k="B" aria-pressed="false">Rebuilt (B)</button>'
            '<button type="button" class="stop" aria-label="Stop">&#9632;</button></div><p class="now"></p>'
            '<div class="ver" data-l="B"><div class="q">Rebuilt</div>'
            f'<div class="conf"><button type="button" data-a="same">{REDO_SAME}<span class="sub"> ({REDO_SAME_SUB})'
            '</span></button><button type="button" data-a="cant">Can\'t judge</button></div>'
            '<div class="conf faults"><span class="sub">or every fault you hear, in the notes:</span>'
            + buttons(CONTENT_FAULTS) + '</div><div class="conf faults"><span class="sub">or in the sound:</span>'
            + buttons(SIGNAL_FAULTS) + "</div></div>"
            '<input class="note" type="text" placeholder="Note (optional)" aria-label="Note">'
            '<div class="done"></div></article>')
    return "".join(out)


def redo_items(index):
    """(Pure.) The clips index (`note_transcribe clips`) -> the cards in page order, each with its two clips' files
    and sha256 and whether it is the hidden control. Refuses an index without 13 cards, exactly one control, and the
    recorded DI and Rebuilt on every card."""
    cards = sorted(index["cards"], key=lambda c: c["n"])
    if len(cards) != REAL_CARDS + 1 or sum(bool(c["control"]) for c in cards) != 1:
        raise SystemExit(f"{len(cards)} cards with {sum(bool(c['control']) for c in cards)} controls, not "
                         f"{REAL_CARDS} and 1")
    out = []
    for c in cards:
        if set(c["clips"]) != {"ref", "reb"}:
            raise SystemExit(f"card {c['n']}: clips {sorted(c['clips'])}, not ref and reb")
        out.append({"id": c["id"], "n": c["n"], "item": c["item"], "cls": c["cls"], "control": bool(c["control"]),
                    "kind": c.get("kind"), "clips": c["clips"]})
    return out


def redo_build_id(items):
    """(Pure.) The page's build: the hash of its cards' clips."""
    return hashlib.sha256(json.dumps([[it["id"], it["cls"], it["clips"]] for it in items],
                                     sort_keys=True).encode()).hexdigest()[:12]


def redo_verdict(items, answers):
    """(Pure.) The redo's declared reading of the stored answers (plan section 12g), never from chat:
    - "fault-content": a content fault on any real card (stops the step);
    - "fault-signal": signal faults on 3 or more real cards (stops the step);
    - "incomplete": a card unanswered (nothing recorded);
    - "ask": signal faults on 1 or 2 real cards, any "can't judge", or any fault on the control card (to the user);
    - "ok": "Same notes and timing" on all 12 real cards (answers, score and read may run).
    The first that holds, in this order. -> {verdict, content, signal, unanswered, cant_judge, control, notes}."""
    content, signal, unanswered, cant, control, notes = [], [], [], [], None, []
    cf, sf = {f for f, _ in CONTENT_FAULTS}, {f for f, _ in SIGNAL_FAULTS}
    same_all = True
    for it in items:
        a = answers.get(it["id"]) or {}
        faults = set(a.get("faults") or [])
        where = {"n": it["n"], "item": it["item"], "cls": it["cls"], "note": (a.get("note") or "").strip()}
        if not (a.get("same") or a.get("cant") or faults):
            unanswered.append(it["n"])
        if a.get("cant"):
            cant.append(it["n"])
        if it["control"]:
            control = {**where, "faults": sorted(faults), "same": bool(a.get("same")), "cant": bool(a.get("cant"))}
            continue
        same_all = same_all and bool(a.get("same"))
        if faults & cf:
            content.append({**where, "heard": sorted(faults & cf)})
        if faults & sf:
            signal.append({**where, "heard": sorted(faults & sf)})
        if where["note"] and not faults:
            notes.append(where)
    if content:
        v = "fault-content"
    elif len(signal) >= 3:
        v = "fault-signal"
    elif unanswered:
        v = "incomplete"
    elif signal or cant or (control and control["faults"]):
        v = "ask"
    elif same_all:
        v = "ok"
    else:
        v = "ask"
    return {"verdict": v, "content": content, "signal": signal, "unanswered": unanswered, "cant_judge": cant,
            "control": control, "notes": notes}


def redo_page_html(items, clips, build):
    """The redo's local page. -> (html, css, js)."""
    from learn import ear_vreal as E

    js, css = redo_player_js(), E.CSS + CSS_EXTRA
    a, b = E.PAGE.index("<h1>"), E.PAGE.index("@@CARDS@@")
    data = json.dumps({"build": build, "items": [{"id": it["id"], "n": it["n"]} for it in items]})
    page = (E.PAGE[:a] + REDO_INTRO + "\n" + E.PAGE[b:]).replace("@@COUNT@@", str(len(items))) \
        .replace("@@CARDS@@", redo_cards(items)).replace("@@CSS@@", css).replace("@@DATA@@", data) \
        .replace("@@CLIPS@@", json.dumps(clips)).replace("@@JS@@", js)
    if "<title>Record tone check</title>" not in page:
        raise SystemExit("ear_vreal's page title changed")
    return page.replace("<title>Record tone check</title>", f"<title>{REDO_TITLE}</title>"), css, js


def redo_artifact_page(page, css, js):
    from learn import c1a_ear as C

    out = C.artifact_page(page, css, js)
    old = "<title>Record A/B Check</title>"
    if not out.startswith(old):
        raise SystemExit("c1a_ear's artifact title changed")
    return f"<title>{REDO_TITLE}</title>" + out[len(old):]


def redo_page_dir():
    from learn import pretrain_set as PS

    return PS.HOME / "listening" / "note-rebuild-ear-page-2"


def cmd_redo_page(_args):
    """The redo's page from `note_transcribe clips`' clips (each checked against its index's sha256), folded to mono and
    AAC-encoded as the regular pages are -> note-rebuild-ear-page-2/{index.html, artifact.html, key.json}, each
    written once."""
    import numpy as np
    import soundfile as sf

    from learn import ear_vreal as E
    from learn import note_rebuild as NR
    from learn import note_transcribe as NT

    out = redo_page_dir()
    for name in ("index.html", "artifact.html", "key.json"):
        NT.never_overwrite(out / name)
    src = NT.clips_dir()
    index = json.loads((src / "index.json").read_text())
    items = redo_items(index)
    build = redo_build_id(items)
    clips = {}
    for it in items:
        for k, ver in (("ref", "ref"), ("B", "reb")):
            f = src / it["clips"][ver]["file"]
            if NR.file_sha(f) != it["clips"][ver]["sha256"]:
                raise SystemExit(f"{f.name}: not the clip its index records")
            y, sr = sf.read(f, dtype="float64", always_2d=True)
            if sr != E.SR:
                raise SystemExit(f"{f.name}: {sr} Hz")
            clips[f"{it['id']}-{k}"] = E.encode(np.asarray(y).mean(1), out / "aac-cache")
    page, css, js = redo_page_html(items, clips, build)
    out.mkdir(parents=True, exist_ok=True)
    NR.write_once(out / "key.json", {"phase": REDO_PHASE, "build": build, "dry_build_sha256": index["build_sha256"],
                                     "items": items})
    for name, text in (("index.html", page), ("artifact.html", redo_artifact_page(page, css, js))):
        NT.never_overwrite(out / name)
        (out / name).write_text(text)
    print(f"NOTE-REBUILD-EAR PAGE 2: {len(items)} cards, build {build} -> {out / 'artifact.html'}", flush=True)


def cmd_redo_read(args):
    """The redo's declared read of the stored answers (`answers/<build>` or the Export text) -> OUT.json (written
    once); its verdict goes into the ledger as phase_nr_1_redo_ear."""
    import pathlib

    from learn import ear_eat as EE
    from learn import note_transcribe as NT

    NT.never_overwrite(args.out)
    key = json.loads((redo_page_dir() / "key.json").read_text())
    ex = EE.stored_answers(pathlib.Path(args.answers).read_text())
    if ex.get("build") != key["build"]:
        raise SystemExit(f"answers for build {ex.get('build')}, the page's is {key['build']}")
    rep = {"phase": REDO_PHASE, "build": key["build"], "dry_build_sha256": key["dry_build_sha256"],
           **redo_verdict(key["items"], ex["answers"])}
    pathlib.Path(args.out).write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("page").set_defaults(fn=cmd_page)
    s = sub.add_parser("read")
    s.add_argument("out")
    s.add_argument("--answers", required=True)
    s.set_defaults(fn=cmd_read)
    sub.add_parser("redo-page").set_defaults(fn=cmd_redo_page)
    s = sub.add_parser("redo-read")
    s.add_argument("out")
    s.add_argument("--answers", required=True)
    s.set_defaults(fn=cmd_redo_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
