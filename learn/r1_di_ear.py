"""R1 Amendment 5, the matched DIs picked by ear (`docs/full-controls-plan.md`, "R1 in detail"; ledger `pipeline-fix`
`phase_r1_a5`). On the user's windows, the pitch tracker misreads two centre-only stems: Frail Grasp's solo and Long
Road's read as low and mostly unpitched. Asked, the user chose to pick by ear. Each song's card plays its guitar (the
chosen version's stem) and its mix, beside six candidate DIs:
- the three nearest by the calibrated distance (Amendment 3);
- three single-note lines (voiced share >= 0.85) at a low, a middle and a high register (MIDI 55, 64, 72), each the
  nearest in pace, as a hedge where the pitch is misread.
All candidates are on distinct source performances. The user marks up to two that play most like the part, or none.
The marks replace the DI check: a DI the user picks is one they kept. A song gets one card per DI picked; a song with
none picked leaves the page.

    .venv/bin/python -m learn.r1_di_ear di-ear-cands     # -> di-match/ear/candidates.json (zero renders)
    .venv/bin/python -m learn.r1_di_ear di-ear-page      # -> di-match/ear/page.html, key.json
    .venv/bin/python -m learn.r1_di_ear di-ear-final --store F   # -> r1/matched-dis.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time

PHASE = "phase_r1_a5"
NEAREST, LEADS, LEAD_REGISTERS, LEAD_VOICED = 3, 3, (55.0, 64.0, 72.0), 0.85
MAX_PICKS = 2
HALF_A = (1.0, 5.5)                  # what R1's cards play: the stem's and each DI's half A (the review)


def ear_dir():
    from learn import r1_di as D

    return D.out_dir() / "ear"


def lead_pick(song_onsets_log2, segs, register, used):
    """The single-note segment (voiced >= LEAD_VOICED) nearest `register` in median pitch, then in pace (log2 onsets),
    on a source not in `used`. -> seg or None."""
    import math

    pool = [s for s in segs if s["voiced"] >= LEAD_VOICED and s["di"] not in used]
    if not pool:
        return None
    return min(pool, key=lambda s: (abs(s["median"] - register) + abs(math.log2(max(s["onset_rate"], 0.2)) - song_onsets_log2),
                                    s["di"], s["start"]))


def candidates(song, segs, cal):
    """The six candidates for one song: the NEAREST by the calibrated distance, then a lead line per register."""
    import math

    from learn import r1_di as D

    near = D.pick(song, segs, k=NEAREST, dist=lambda a, b: D.cal_distance(a, b, cal))
    out = [{**s, "why": "nearest"} for s in near]
    used = {s["di"] for s in out}
    onsets = math.log2(max(song["onset_rate"], 0.2)) - cal["log2_onsets"][0]
    for r in LEAD_REGISTERS:
        s = lead_pick(onsets, segs, r, used)
        if s:
            out.append({**s, "distance": D.cal_distance(song, s, cal), "why": f"lead line near MIDI {r:.0f}"})
            used.add(s["di"])
    return out


def picks_of(answers, key):
    """The stored answers -> {song: [candidate records picked]} (at most MAX_PICKS; 'none' -> [])."""
    out = {}
    for it in key["songs"]:
        a = (answers or {}).get(it["id"]) or {}
        fits = [] if a.get("none") else [c for c in it["cands"] if c["id"] in (a.get("fits") or [])]
        if len(fits) > MAX_PICKS:
            raise SystemExit(f"{it['song']}: {len(fits)} picked, at most {MAX_PICKS}")
        out[it["song"]] = fits
    return out


def cmd_cands(_args):
    import numpy as np

    from learn import pipeline_fix as P
    from learn import r1_di as D
    from learn import r1_ear as R

    P.require(PHASE)
    songs = json.loads((D.out_dir() / "songs.json").read_text())["songs"]
    cal = json.loads((D.out_dir() / "calibration.json").read_text())["by_class"]
    cls = {x: json.loads((R.ear_dir() / x / "research.json").read_text())["cls"] for x in songs}
    segs = []
    for p in sorted((D.out_dir() / "pool").glob("*.npz")):
        z = np.load(p)
        hop, dur, path = float(z["hop"][0]), float(z["seconds"][0]), str(z["path"][0])
        a = D.LEAD_S
        while a + D.SEG_S <= dur - 0.25:
            f = D.seg_features(z["midi"], z["voiced"], z["active"], z["onsets"], a, a + D.SEG_S, hop)
            if f:
                segs.append({"file": path, "di": str(z["di"][0]), "set": str(z["set"][0]), "start": round(a, 3), **f})
            a += D.SEG_HOP_S
    out = {}
    for s, f in songs.items():
        c = {k: tuple(v) for k, v in cal[cls[s]]["cal"].items()}
        out[s] = [{"source": x["di"], "di": f"{x['di']}@{x['start']:.1f}", "di_path": x["file"],
                   "start_s": round(x["start"] - D.LEAD_S, 3), "set": x["set"], "why": x["why"],
                   "distance": x["distance"], "features": {k: x[k] for k in ("voiced", "median", "p10", "p90", "onset_rate")}}
                  for x in candidates(f, segs, c)]
        print(s, [(x["di"][-28:], x["why"], round(x["distance"], 2)) for x in out[s]], flush=True)
    ear_dir().mkdir(parents=True, exist_ok=True)
    P.save(ear_dir() / "candidates.json", {"phase": PHASE, "songs": out, "time": time.strftime("%Y-%m-%d %H:%M:%S")})


PAGE_CSS = """:root { --bg:#fbfaf7; --card:#fff; --fg:#1d1d1f; --mute:#6b6b70; --line:#dcdad3; --on:#2f5d8a; --on-fg:#fff; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#141416; --card:#1d1d20; --fg:#ececee;
  --mute:#9a9aa2; --line:#34343a; --on:#6f9fd0; --on-fg:#0d1117; color-scheme:dark; } }
:root[data-theme="dark"] { --bg:#141416; --card:#1d1d20; --fg:#ececee; --mute:#9a9aa2; --line:#34343a; --on:#6f9fd0;
  --on-fg:#0d1117; color-scheme:dark; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.45 -apple-system, system-ui, sans-serif; }
main { max-width:760px; margin:0 auto; padding:16px; }
h1 { font-size:21px; margin:8px 0; } .intro { color:var(--mute); }
.song { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px; margin:14px 0; }
.song h3 { margin:0 0 8px; font-size:16px; } .row { display:flex; flex-wrap:wrap; gap:6px; margin:6px 0; align-items:center; }
button { font:inherit; padding:7px 11px; border-radius:7px; border:1px solid var(--line); background:var(--card);
  color:var(--fg); cursor:pointer; min-width:44px; }
button[aria-pressed="true"] { background:var(--on); color:var(--on-fg); border-color:var(--on); }
.fit button { min-width:auto; } .done { color:var(--mute); font-size:13px; } #status { color:var(--mute); font-size:13px; }
"""

PAGE_JS = r"""
const DATA = JSON.parse(document.getElementById("data").textContent);
const CLIPS = JSON.parse(document.getElementById("clips").textContent);
const STORE = "r1-di-ear:" + DATA.build;
let ans = {}; try { ans = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (e) { ans = {}; }
let actx = null, bufs = {}, cur = null;
function ctx() { if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)(); return actx; }
function bytes(k) { const s = atob(CLIPS[k]); const b = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i); return b.buffer; }
async function buf(k) { if (!bufs[k]) bufs[k] = await new Promise((ok, no) => ctx().decodeAudioData(bytes(k), ok, no)); return bufs[k]; }
function stop() { if (cur) { try { cur.src.stop(); } catch (e) {} cur = null; } mark(); }
async function play(song, k) {
  const key = song + "-" + k, b = await buf(key), c = ctx();
  let pos = 0;
  if (cur && cur.song === song) pos = (c.currentTime - cur.t0) % cur.dur;
  if (cur) { try { cur.src.stop(); } catch (e) {} }
  const src = c.createBufferSource(); src.buffer = b; src.loop = true; src.connect(c.destination);
  src.start(0, pos % b.duration); cur = {song, k, src, t0: c.currentTime - pos, dur: b.duration}; mark();
}
function mark() { document.querySelectorAll(".src").forEach(b => b.setAttribute("aria-pressed", String(!!cur && cur.song === b.dataset.s && cur.k === b.dataset.k))); }
function save() { try { localStorage.setItem(STORE, JSON.stringify(ans)); } catch (e) {} paint(); sync(); }
function paint() {
  let n = 0;
  DATA.songs.forEach(s => {
    const a = ans[s.id] || {}, el = document.querySelector('.song[data-id="' + s.id + '"]');
    el.querySelectorAll(".fitb").forEach(b => b.setAttribute("aria-pressed", String((a.fits || []).includes(b.dataset.c))));
    el.querySelector(".noneb").setAttribute("aria-pressed", String(!!a.none));
    const done = a.none || (a.fits || []).length > 0; if (done) n++;
    el.querySelector(".done").textContent = done ? "Answered" : "";
  });
  document.getElementById("status").textContent = n + " of " + DATA.songs.length + " songs answered";
}
document.addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  if (b.classList.contains("src")) { play(b.dataset.s, b.dataset.k); return; }
  if (b.classList.contains("stop")) { stop(); return; }
  const id = b.closest(".song") && b.closest(".song").dataset.id; if (!id) return;
  const a = ans[id] = ans[id] || {fits: []};
  if (b.classList.contains("fitb")) {
    a.none = false; const c = b.dataset.c, i = a.fits.indexOf(c);
    if (i >= 0) a.fits.splice(i, 1); else { a.fits.push(c); if (a.fits.length > DATA.max) a.fits.shift(); }
  } else if (b.classList.contains("noneb")) { a.none = !a.none; if (a.none) a.fits = []; }
  save();
});
document.addEventListener("keydown", e => { if (e.key === " ") { e.preventDefault(); stop(); } });
let dbDoc = null, busy = false, again = false;
function sync() {
  if (!dbDoc) return; if (busy) { again = true; return; } busy = true;
  dbDoc.set({build: DATA.build, answers: ans, at: Date.now()}).catch(() => {}).finally(() => { busy = false; if (again) { again = false; sync(); } });
}
(async () => { try {
  if (!window.claude) return; const db = await window.claude.use("db"); if (!db) return;
  const d = db.doc("answers/" + DATA.build), snap = await d.get();
  if (snap.exists && !Object.keys(ans).length) { ans = snap.data().answers || {}; try { localStorage.setItem(STORE, JSON.stringify(ans)); } catch (e) {} }
  dbDoc = d; paint(); if (Object.keys(ans).length) sync();
} catch (e) {} })();
paint();
"""


def page(items, clips, build):
    import html as H

    cards = []
    for n, it in enumerate(items, 1):
        cands = "".join(f'<button type="button" class="src" data-s="{it["id"]}" data-k="{c["id"]}" aria-pressed="false">'
                        f'{j}</button>' for j, c in enumerate(it["cands"], 1))
        fits = "".join(f'<button type="button" class="fitb" data-c="{c["id"]}" aria-pressed="false">{j} fits</button>'
                       for j, c in enumerate(it["cands"], 1))
        cards.append(f'<section class="song" data-id="{it["id"]}"><h3>Song {n} of {len(items)}</h3>'
                     f'<div class="row"><button type="button" class="src" data-s="{it["id"]}" data-k="G" aria-pressed="false">'
                     f'Guitar (G)</button><button type="button" class="src" data-s="{it["id"]}" data-k="S" '
                     f'aria-pressed="false">Song (S)</button>{cands}<button type="button" class="stop" aria-label="Stop">'
                     f'&#9632;</button></div><div class="row fit">{fits}<button type="button" class="noneb" '
                     f'aria-pressed="false">None fits</button></div><div class="done"></div></section>')
    data = json.dumps({"build": build, "max": MAX_PICKS, "songs": [{"id": it["id"]} for it in items]})
    intro = ("<h1>Which recordings play like the song's guitar?</h1><p class=\"intro\">For each song, <b>Guitar (G)</b> is "
             "the song's separated guitar and <b>Song (S)</b> the full mix, for context. 1 to 6 are dry guitar recordings "
             "by other players. Mark the one or two that play most like the song's part: the same kind of playing "
             "(single notes or chords), about as high or low, about as busy. Their tone doesn't matter yet; the presets "
             "come later. Mark one only if it's also fine by your DI rule (not tuned too low, not played too metal, not "
             "processed). Mark <b>None fits</b> if none does. Each clip is the 4.5 seconds the next page will play. Everything loops and switches instantly; Space stops. "
             "All clips are set to the same loudness. Your marks save as you go, and I can read them from here when you "
             "tell me you are done.</p><p id=\"status\"></p>")
    return (f"<title>Matching Guitar Parts</title>\n<style>{PAGE_CSS}</style>\n<main>{intro}{''.join(cards)}</main>"
            f'<script id="data" type="application/json">{H.escape(data, quote=False)}</script>'
            f'<script id="clips" type="application/json">{json.dumps(clips)}</script><script>{PAGE_JS}</script>')


def cmd_page(_args):
    import numpy as np

    from learn import build_data_review as BDR
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import r1_ear as R
    from learn import scope_page as SP

    P.require(PHASE)
    d = ear_dir()
    if (d / "key.json").exists():
        raise SystemExit(f"{d / 'key.json'} exists: a rebuild hides the stored answers")
    cands = json.loads((d / "candidates.json").read_text())["songs"]
    items, clips = [], {}
    for s in R.songs():
        sid = hashlib.sha256(f"r1-di-ear|{s}".encode()).hexdigest()[:8]
        w = np.load(R.ear_dir() / s / "window.npz")
        h = PS.half_slices()["A"]
        for k, y in (("G", w["stem"]), ("S", w["mix"])):
            clips[f"{sid}-{k}"] = SP.encode(BDR.level_clip(np.asarray(y, np.float64)[h])[0], d / "aac-cache")
        cs = []
        for c in cands[s]:
            cid = hashlib.sha256(f"{sid}|{c['di']}".encode()).hexdigest()[:8]
            y = PS.load_mono(c["di_path"], PS.SR, c["start_s"] + HALF_A[0], HALF_A[1] - HALF_A[0])
            clips[f"{sid}-{cid}"] = SP.encode(BDR.level_clip(np.asarray(y, np.float64))[0], d / "aac-cache")
            cs.append({**c, "id": cid})
        items.append({"id": sid, "song": s, "cands": cs})
    order = sorted(items, key=lambda it: it["id"])                  # by hash: no song order to read meaning into
    build = hashlib.sha256(json.dumps([[c["id"] for c in it["cands"]] for it in order]).encode()).hexdigest()[:12]
    html = page(order, clips, build)
    head = html.split('<script id="clips"')[0]
    bad = [w for w in ("goat", "GOAT", "BKS", "item_", "ElecGtr", "panel", "cambridge", *R.songs()) if w in head]
    if bad:
        raise SystemExit(f"the page names {bad}")
    d.mkdir(parents=True, exist_ok=True)
    (d / "page.html").write_text(html)
    (d / "key.json").write_text(json.dumps({"phase": PHASE, "build": build, "songs": order,
                                            "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
    print(f"R1 DI EAR PAGE: {len(order)} songs, build {build}, {len(html) / 1e6:.1f} MB -> {d / 'page.html'}")


def cmd_final(args):
    import pathlib

    from learn import ear_eat as EE
    from learn import pipeline_fix as P
    from learn import r1_di as D

    P.require(PHASE)
    key = json.loads((ear_dir() / "key.json").read_text())
    ex = EE.stored_answers(pathlib.Path(args.store).read_text())
    if ex.get("build") != key["build"]:
        raise SystemExit(f"{args.store}: build {ex.get('build')}, the page's is {key['build']}")
    picks = picks_of(ex.get("answers"), key)
    unanswered = [it["song"] for it in key["songs"] if not ((ex.get("answers") or {}).get(it["id"]) or {}).get("none")
                  and not picks[it["song"]]]
    if unanswered:
        raise SystemExit(f"no answer yet for {unanswered}")
    songs = json.loads((D.out_dir() / "songs.json").read_text())["songs"]
    P.save(D.R1_MATCHED(), {"phase": PHASE, "ear_build": key["build"], "dropped": sorted(s for s, v in picks.items() if not v),
                            "songs": {s: {"song": songs[s], "dis": v} for s, v in picks.items() if v},
                            "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    for s, v in picks.items():
        print(s, "->", [x["di"] for x in v] or "none fits: off the page")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("di-ear-cands").set_defaults(fn=cmd_cands)
    sub.add_parser("di-ear-page").set_defaults(fn=cmd_page)
    f = sub.add_parser("di-ear-final")
    f.add_argument("--store", required=True)
    f.set_defaults(fn=cmd_final)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
