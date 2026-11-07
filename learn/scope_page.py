"""The keep-or-drop page: the labelled GOAT and BKS recordings over the drive line that no page has asked about, heard
blind, one tap each (the user's yes, 2026-11-07). Only "keep" stays in, as on `goat_ear_page`'s heavy check; the line
only says who is asked, since nothing measured tells out from kept above it.

    $MAIN -m learn.scope_page list                  # -> scope/list.json: every labelled recording's measure and marks
    $MAIN -m learn.scope_page page                  # -> scope/page.html, scope/key.json
    $MAIN -m learn.scope_page answers STORED.json   # -> scope/verdicts.json
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import pathlib
import random
import re
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

SCOPE_DIR = "scope"
CUT_DB = -2.91                      # the best cut on the 90 units the ear has marked; a screen, not a verdict
SEED = 20261311
KBPS = 72                           # AAC: 124 clips under the artifact's 16 MB; no fizz added, faint floors kept better than at 64
SLIP = ("ear-eat-1", "i2")          # the user's ruling: this out mark was a slip
VERDICTS = (("keep", "Keep", "K"), ("heavy", "Too heavy or distorted", "D"), ("unsure", "Not sure", "N"))
WORDS = ("BKS", "Bulldozer", "TooMuch", "goat", "GOAT", "item_", "amp_", "Reamp", "ElecGtr", "nonlinear", "pr12", "sw50r", "ac20")


def ask(nl, marks, cut=CUT_DB):
    """The recordings at or over the line that no page has marked, sorted. nl: {unit: dB}; marks: {unit: keep or out}."""
    if any(v is None for v in nl.values()):
        raise SystemExit("a recording has no measure")
    return sorted(u for u, v in nl.items() if v >= cut and u not in marks)


def merge_marks(rows):
    """[(page, id, unit, out)] -> {unit: "keep" or "out"}; out wins, and the slip counts as keep."""
    got = {}
    for page, cid, unit, out in rows:
        out = out and (page, cid) != SLIP
        got[unit] = "out" if out or got.get(unit) == "out" else "keep"
    return got


def order(units, seed=SEED):
    got = list(units)
    random.Random(seed).shuffle(got)
    return got


def item_id(unit, seed=SEED):
    return "r" + hashlib.sha256(f"{seed}|{unit}".encode()).hexdigest()[:12]


def unit_verdicts(answers, items):
    """A stored `answers` -> {unit: verdict}; refuses a partial sitting, and an id or verdict the page never showed."""
    unit_of = {it["id"]: it["unit"] for it in items}
    known = {v for v, _, _ in VERDICTS}
    bad = [k for k, a in answers.items() if k not in unit_of or a.get("v") not in known]
    if bad:
        raise SystemExit(f"answers this page never showed: {bad}")
    missing = [k for k in unit_of if k not in answers]
    if missing:
        raise SystemExit(f"{len(missing)} of {len(unit_of)} cards have no answer")
    return {unit_of[k]: a["v"] for k, a in answers.items()}


def out_units(verdicts, marks):
    """What leaves: every recording the page did not keep, and every one an earlier page already marked out."""
    return sorted({u for u, v in verdicts.items() if v != "keep"} | {u for u, m in marks.items() if m == "out"})


def leaks(page, units):
    """What the page shows of a recording's name, set or measure, its clips and hashed ids aside."""
    a = page.index('<script id="clips"')
    shown = re.sub(r"\br?[0-9a-f]{12}\b", "", page[:a] + page[page.index("</script>", a):])
    return [w for w in (*WORDS, *units) if w in shown]


def stored_marks():
    """What the pages that asked about scope said, on GOAT and BKS: the heavy check and both record-tone pages."""
    from learn import ear_eat as EE
    from learn import pipeline_fix as P

    root = P.out_dir()
    rows = [("goat-heavy", u, u, v["verdict"] != "keep")
            for u, v in json.loads((root / P.GOAT_DIR / "heavy.json").read_text())["verdicts"].items()]
    for page, sub, name in (("ear-eat-1", "eat/ear", "answers.txt"), ("ear-eat-2", "eat/ear2", "answers.json")):
        answers = EE.stored_answers((root / sub / name).read_text())["answers"]
        rows += [(page, it["id"], it["unit"], bool(answers[it["id"]].get("scope")))
                 for it in json.loads((root / sub / "key.json").read_text())["items"] if it["id"] in answers]
    return merge_marks(rows)


def labelled_parts():
    """{unit: part} of every recording with a search label, GOAT and BKS, by the loaders' own lists."""
    from learn import cc_build as CB
    from learn import pipeline_fix as P

    goat = {u["unit"]: u for u in P.goat_units()}
    recs = P.goat_labels()[0]
    parts = {r["unit"]: {**goat[r["unit"]], "source": "goat"} for r in recs}
    e = P.require("phase_5b2")
    _, kept, _, sp, _ = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    inv = CB.cc_inventory()
    bks = {}
    for stage in (1, 2):
        for prt in P.stage_units(kept, sp, inv, stage):
            bks.setdefault(prt["unit"], prt)
    for r in P.real_labels(2)[0]:
        parts[r["unit"]] = {**bks[r["unit"]], "source": "bks"}
    return parts


def scope_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / SCOPE_DIR


def cmd_list(_args):
    from learn import ear_eat as EE

    parts = labelled_parts()
    nl = {u: EE.nonlinear_db(prt["source"], prt) for u, prt in sorted(parts.items())}
    marks = stored_marks()
    asked = ask(nl, marks)
    d = scope_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "list.json").write_text(json.dumps({
        "cut_db": CUT_DB, "nl": nl, "marks": {u: m for u, m in marks.items() if u in nl}, "ask": asked,
        "source": {u: prt["source"] for u, prt in parts.items()}, "cls": {u: parts[u].get("cls") for u in parts},
        "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
    over = [u for u, v in nl.items() if v >= CUT_DB]
    print(f"SCOPE LIST: {len(nl)} labelled, {len(over)} over the line, {len(asked)} to ask")


def encode(y, cache):
    """One levelled clip -> AAC base64."""
    import numpy as np
    import soundfile as sf

    from learn import audibility_measure as AM
    from learn import build_data_review as BDR

    y = BDR.fade(y)
    cache.mkdir(parents=True, exist_ok=True)
    flac = cache / f"{hashlib.sha256(y.astype(np.float32).tobytes()).hexdigest()[:16]}.flac"
    if not flac.exists():
        sf.write(str(flac), y, BDR.SR, subtype="PCM_24")
    return AM.aac_b64(flac, cache, KBPS)


CSS = r"""
:root { --bg:#fbfaf7; --card:#ffffff; --fg:#1d1d1f; --mute:#6b6b70; --line:#dcdad3; --on:#2f5d8a; --on-fg:#fff; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#141416; --card:#1d1d20; --fg:#ececee;
  --mute:#9a9aa2; --line:#34343a; --on:#6f9fd0; --on-fg:#0d1117; color-scheme:dark; } }
:root[data-theme="dark"] { --bg:#141416; --card:#1d1d20; --fg:#ececee; --mute:#9a9aa2; --line:#34343a; --on:#6f9fd0;
  --on-fg:#0d1117; color-scheme:dark; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI",
  Roboto, sans-serif; }
main { max-width:560px; margin:0 auto; padding-block:16px 40px;
  padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); }
h1 { font-size:1.35rem; margin:.4rem 0 .6rem; }
.intro { color:var(--mute); }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; margin:18px 0; }
.top { display:flex; justify-content:space-between; gap:12px; color:var(--mute); font-size:.9rem; }
.bar { height:6px; border-radius:3px; background:var(--line); margin:.5rem 0 1rem; overflow:hidden; }
#fill { height:100%; width:0; background:var(--on); }
button { min-height:52px; border-radius:10px; border:1px solid var(--line); background:var(--bg); color:var(--fg);
  font-size:1rem; font-weight:600; cursor:pointer; touch-action:manipulation; }
#play { width:100%; min-height:64px; }
#now { min-height:1.4em; color:var(--mute); font-size:.9rem; margin:.5rem 0; }
.vs { display:grid; gap:8px; }
.vs button { min-height:60px; }
.vs button[aria-pressed="true"] { background:var(--on); color:var(--on-fg); border-color:var(--on); }
.nav { display:flex; gap:8px; margin-top:12px; }
.nav button { flex:1; min-height:44px; font-weight:500; }
button:disabled { opacity:.45; cursor:default; }
.keys { color:var(--mute); font-size:.85rem; margin-bottom:0; }
#show { width:100%; margin-top:12px; min-height:44px; font-weight:500; }
#out { width:100%; height:140px; margin-top:8px; font:12px/1.4 ui-monospace, monospace; background:var(--bg); color:var(--fg);
  border:1px solid var(--line); border-radius:8px; }
"""

JS = r"""
const DATA = JSON.parse(document.getElementById("data").textContent);
const CLIPS = JSON.parse(document.getElementById("clips").textContent);
const STORE = "scope:" + DATA.build, ids = DATA.items, ARM_MS = 600, LIMIT_MS = 15000, $ = id => document.getElementById(id);
const FINAL = ["invalid_argument", "quota_exceeded", "revoked", "not_granted", "capability_disabled", "capability_removed", "transform_error"];
const vs = Array.from(document.querySelectorAll(".vs button")), pending = new Set();
let ans = {};
try { ans = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (e) { ans = {}; }
function fill() { $("out").value = JSON.stringify({build: DATA.build, answers: ans}); }
function keep() { try { localStorage.setItem(STORE, JSON.stringify(ans)); } catch (e) {}
  if (!$("out").hidden) fill(); }
function timed(p) { return new Promise((ok, no) => { const t = setTimeout(() => no({code: "unavailable"}), LIMIT_MS);
  p.then(v => { clearTimeout(t); ok(v); }, e => { clearTimeout(t); no(e); }); }); }
function firstOpen() { for (let j = 0; j < ids.length; j++) if (!ans[ids[j]]) return j; return -1; }
function openFrom(i) { for (let j = 1; j <= ids.length; j++) { const q = (i + j) % ids.length; if (!ans[ids[q]]) return q; } return -1; }
let at = Math.max(firstOpen(), 0), actx = null, src = null, token = 0, armTimer = null;
let dbDoc = null, ready = false, exists = false, offline = false, busy = false, retrying = false, timer = null, pause = 2000;
const bufs = {};
try { if (navigator.audioSession) navigator.audioSession.type = "playback"; } catch (e) {}
function bytes(id) { const b = atob(CLIPS[id]), u = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u.buffer; }
function decode(id) { if (!bufs[id]) bufs[id] = new Promise((ok, no) => actx.decodeAudioData(bytes(id), ok, no));
  return bufs[id]; }
function prune() { const near = new Set([at - 1, at, at + 1, openFrom(at)].map(j => ids[j]));
  Object.keys(bufs).forEach(id => { if (!near.has(id)) delete bufs[id]; }); }
function arm(on) { clearTimeout(armTimer); vs.forEach(b => { b.disabled = !on; }); }
function stop() { token++; if (src) { try { src.stop(); } catch (e) {} src = null; }
  $("now").textContent = ""; $("play").textContent = "Play"; }
async function play() {
  stop();
  const my = token, id = ids[at];
  if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
  try { await actx.resume(); } catch (e) {}
  $("now").textContent = "Loading...";
  let b;
  try { b = await decode(id); } catch (e) { delete bufs[id]; $("now").textContent = "This clip did not load. Press Play to try again."; return; }
  if (my !== token) return;
  src = actx.createBufferSource(); src.buffer = b; src.loop = true; src.connect(actx.destination); src.start();
  $("now").textContent = "Playing (it loops)"; $("play").textContent = "Stop";
  if (vs[0].disabled) armTimer = setTimeout(() => arm(true), ARM_MS);
  prune();
  const nx = openFrom(at); if (nx >= 0) decode(ids[nx]).catch(() => {});
}
function paint() {
  const n = ids.filter(id => ans[id]).length, a = ans[ids[at]] || {}, all = n === ids.length;
  $("pos").textContent = "Recording " + (at + 1) + " of " + ids.length + ", " + n + " answered";
  $("fill").style.width = (100 * n / ids.length) + "%";
  vs.forEach(b => b.setAttribute("aria-pressed", String(a.v === b.dataset.v)));
  $("back").disabled = at === 0;
  $("next").textContent = all ? "Next" : "Skip for now";
  $("done").hidden = !all || !(offline || (ready && !pending.size && !busy));
  $("done").textContent = offline ? "All answered. Tap Show answers and send me the text." : "All answered and saved. Tell me when you are done.";
}
function go(i) { at = i; arm(false); paint(); }
function answer(v) {
  if (vs[0].disabled) return;
  ans[ids[at]] = {v: v, t: Date.now()}; pending.add(ids[at]); save();
  const nx = openFrom(at);
  if (nx < 0) { stop(); arm(false); paint(); return; }
  go(nx); play();
}
function back() { if (at > 0) { go(at - 1); play(); } }
function next() { const nx = openFrom(at); go(nx >= 0 ? nx : (at + 1) % ids.length); play(); }
function note(t) { $("saved").textContent = t; }
function cutOff() {
  offline = true; dbDoc = null; clearTimeout(timer); note("Not connected");
  $("saveline").textContent = "This copy cannot reach the store, so when you are done tap Show answers and send me the text.";
  paint();
}
function flush() {
  if (!ready || !dbDoc || busy || !pending.size) return;
  const sent = Array.from(pending), body = {build: DATA.build, answers: {}, at: Date.now()};
  sent.forEach(id => { body.answers[id] = ans[id]; });
  pending.clear(); busy = true;
  timed(exists ? dbDoc.update(body) : dbDoc.set(body)).then(() => {
    exists = true; busy = false; pause = 2000;
    if (pending.size) flush(); else { note("Saved"); paint(); }
  }, e => {
    busy = false; sent.forEach(id => pending.add(id));
    if (FINAL.includes(e && e.code)) { cutOff(); return; }
    note("Not saved yet, retrying"); paint();
    retrying = true;
    timer = setTimeout(() => { pull().catch(() => {}).finally(() => { retrying = false; flush();
      if (!offline && !pending.size && !busy) note("Saved");
      paint(); }); }, pause + Math.random() * 1000);
    pause = Math.min(pause * 2, 30000);
  });
}
function save() { keep(); paint(); if (offline) return; if (dbDoc) note("Saving"); if (retrying) return;
  clearTimeout(timer); timer = setTimeout(flush, 400); }
function leave() { clearTimeout(timer); retrying = false; flush(); }
function merge(got) {
  Object.keys(got).forEach(id => { if (!ans[id] || got[id].t > ans[id].t) ans[id] = got[id]; });
  ids.forEach(id => { if (ans[id]) { if (!got[id] || ans[id].t > got[id].t) pending.add(id); else pending.delete(id); } });
  keep();
}
async function pull() {
  const snap = await timed(dbDoc.get());
  exists = snap.exists;
  merge((exists && snap.data().answers) || {});
}
function moveOn() {
  if (!ans[ids[at]] || firstOpen() < 0) return;
  stop(); go(firstOpen());
  if (!actx) $("now").textContent = "Press Play to start.";
}
vs.forEach(b => b.addEventListener("click", () => { b.blur(); answer(b.dataset.v); }));
$("play").addEventListener("click", () => { if (src) stop(); else play(); });
$("back").addEventListener("click", back);
$("next").addEventListener("click", next);
$("show").addEventListener("click", () => { const o = $("out"); o.hidden = false; fill(); o.focus(); o.select(); });
window.addEventListener("pagehide", leave);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) { leave(); return; }
  if (dbDoc) pull().then(() => { if (!src) moveOn(); paint(); flush(); }, () => {});
});
document.addEventListener("keydown", e => {
  if (e.repeat || e.metaKey || e.ctrlKey || e.altKey || e.target === $("out")) return;
  const k = e.key.toLowerCase();
  if (k === "k") answer("keep"); else if (k === "d") answer("heavy"); else if (k === "n") answer("unsure");
  else if (k === "arrowleft") back(); else if (k === "arrowright") next();
  else if (k === " ") { e.preventDefault(); if (src) stop(); else play(); }
});
arm(false); paint();
async function connect(left) {
  try {
    note("Connecting");
    const db = window.claude ? await window.claude.use("db") : null;
    if (!db) { cutOff(); return; }
    dbDoc = db.doc("answers/" + DATA.build);
    await pull();
    ready = true; moveOn();
    note("Connected"); paint(); flush();
  } catch (e) {
    dbDoc = null;
    if (left > 0 && !FINAL.includes(e && e.code)) setTimeout(() => connect(left - 1), 2000 + Math.random() * 1000);
    else cutOff();
  }
}
connect(3);
"""


def page_html(ids, clips, build):
    """The page: no names, measures or sources, only ids. ids: in page order; clips: {id: base64}."""
    e = html.escape
    buttons = "".join(f'<button type="button" data-v="{v}" aria-pressed="false">{e(t)}</button>' for v, t, _ in VERDICTS)
    data = json.dumps({"build": build, "items": ids})
    return f"""<title>Keep Or Drop</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>{CSS}</style>
<main>
<h1>Keep or drop</h1>
<p class="intro">{len(ids)} recordings, each a guitar through an amp, on its own, looping. Keep one if it is clean or
crunch you would want the model to learn from. Drop it if it is too heavy or too distorted for that. Only Keep stays in,
so Not sure counts as dropped. All are set to the same loudness, and a tap moves on to the next one.
<span id="saveline">Your answers save as you go, and I can read them from here when you tell me you are done.</span></p>
<section class="card">
<div class="top"><span id="pos"></span><span id="saved"></span></div>
<div class="bar"><div id="fill"></div></div>
<button type="button" id="play">Play</button>
<p id="now">Press Play to start.</p>
<div class="vs">{buttons}</div>
<div class="nav"><button type="button" id="back">Back</button><button type="button" id="next">Skip for now</button></div>
<p id="done" hidden>All answered. Tell me when you are done.</p>
<p class="keys">Keys: K keep, D drop, N not sure, space play or stop, arrows back and skip.</p>
<button type="button" id="show">Show answers</button>
<textarea id="out" hidden readonly aria-label="Your answers"></textarea>
</section>
</main>
<script id="data" type="application/json">{data}</script>
<script id="clips" type="application/json">{json.dumps(clips)}</script>
<script>{JS}</script>
"""


def cmd_page(_args):
    from learn import build_data_review as BDR
    from learn import pipeline_fix as P

    d = scope_dir()
    if (d / "key.json").exists():
        raise SystemExit(f"{d / 'key.json'} exists: a rebuild hides the listener's stored answers; move it aside first")
    listed = json.loads((d / "list.json").read_text())
    parts = labelled_parts()
    units = order(listed["ask"])
    items, clips = [], {}
    for u in units:
        prt, cid = parts[u], item_id(u)
        y, gain, _, cut = BDR.level_clip(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]))
        clips[cid] = encode(y, d / "aac-cache")
        items.append({"id": cid, "unit": u, "nl": listed["nl"][u], "source": prt["source"], "cls": prt.get("cls"),
                      "gain_db": gain, "peak_cut_db": cut})
    ids = [it["id"] for it in items]
    build = hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:12]
    page = page_html(ids, clips, build)
    shown = leaks(page, units)
    if shown:
        raise SystemExit(f"the page names {shown}")
    (d / "page.html").write_text(page)
    (d / "key.json").write_text(json.dumps({"page": SCOPE_DIR, "build": build, "seed": SEED, "cut_db": CUT_DB, "items": items,
                                            "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
    print(f"SCOPE PAGE DONE: {len(items)} cards, build {build}, {len(page) / 1e6:.1f} MB -> {d / 'page.html'}")


def cmd_answers(args):
    from learn import ear_eat as EE

    d = scope_dir()
    key = json.loads((d / "key.json").read_text())
    ex = EE.stored_answers(pathlib.Path(args.stored).read_text())
    if ex.get("build") != key["build"]:
        raise SystemExit(f"{args.stored}: build {ex.get('build')}, this page's is {key['build']}")
    got = unit_verdicts(ex["answers"], key["items"])
    marks = json.loads((d / "list.json").read_text())["marks"]
    (d / "verdicts.json").write_text(json.dumps({"page": SCOPE_DIR, "build": key["build"], "verdicts": got,
                                                 "out": out_units(got, marks),
                                                 "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
    c = {}
    for v in got.values():
        c[v] = c.get(v, 0) + 1
    print(f"SCOPE ANSWERS: {len(got)} of {len(key['items'])} heard; {c}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    sub.add_parser("page").set_defaults(fn=cmd_page)
    a = sub.add_parser("answers")
    a.add_argument("stored")
    a.set_defaults(fn=cmd_answers)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
