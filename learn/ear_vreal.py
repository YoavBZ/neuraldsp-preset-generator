"""L0, the ear on held-out real songs (`docs/pipeline-fix-plan.md`, ledger `phase_ear_vreal`): does "level with S by
the score" hold by ear when the models play the song's own performance? Development only; descriptive.

    .venv/bin/python -m learn.ear_vreal plan                                # zero renders: the 10 items
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.ear_vreal render --shard i/3
    .venv/bin/python -m learn.ear_vreal page
    .venv/bin/python -m learn.ear_vreal score --answers FILE

One direction per V-real part, chosen from the record's activity and S's stored distances alone. S, FT, D_fix and W,
each from its stored V-real answer, are re-rendered through the part's measure DI, its own performance at the level
and average-guitar EQ every V-real read used (each hash must equal the stored render's, so the audio is exactly what
the score read), and played on the held half, sample-aligned with the amp track.
The listener ranks them and rates each one's closeness; `score` unblinds and sets the ear beside the stored scores.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import pathlib
import random
import secrets
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from learn.record_match_listening import spearman  # noqa: E402

PHASE = "phase_ear_vreal"
CANDS = {"S": "S", "FT": "FV-P2b-ft-stem", "D_fix": "DV-P2b-dfix-stem", "W": "DV-P2b-wide24-stem"}
MODELS = ("FT", "D_fix", "W")
LETTERS = ("A", "B", "C", "D")
CLOSE = (("very", "Very close"), ("close", "Close"), ("some", "Somewhat"), ("far", "Not close"))
CLOSE_VALUE = {"very": 3, "close": 2, "some": 1, "far": 0}
ACTIVE_DB = 25.0
REPEATS = 2
REPEAT_GAP = 4                        # items from a first hearing to its repeat, at least
PAGE_SEED = 20261104
BOOT_SEED, BOOT_N = 20261105, 20000
SR = 48000


# --- pure functions (unit-tested) ------------------------------------------------------------------------------------

def choose(rows):
    """rows: [{slug, key, band, cls, act: {A, B}, s: {amp: {A, B}}}], `key` the part (members sharing an input share
    it). One unit per key: the held half is a member's more active half (A on a tie), the member the one with the most
    active held half (first by name on a tie), the amp the one whose S is closest on the search half."""
    out = {}
    for r in sorted(rows, key=lambda x: x["slug"]):
        held = "A" if r["act"]["A"] >= r["act"]["B"] else "B"
        search = "B" if held == "A" else "A"
        cur = out.get(r["key"])
        if cur is None or r["act"][held] > cur["active"]:
            amp = min(sorted(r["s"]), key=lambda a: r["s"][a][search])
            out[r["key"]] = {"slug": r["slug"], "key": r["key"], "band": r["band"], "cls": r["cls"], "amp": amp,
                             "search": search, "held": held, "active": r["act"][held]}
    return [out[k] for k in sorted(out)]


def balanced(rng, rows=12):
    """`rows` distinct permutations of the candidates, each candidate on each letter equally often (Latin squares)."""
    while True:
        out = []
        for _ in range(rows // len(LETTERS)):
            base = rng.sample(list(CANDS), len(CANDS))
            out += [tuple(base[i:] + base[:i]) for i in range(len(CANDS))]
        if len(set(out)) == rows:
            rng.shuffle(out)
            return out


def draw(units, seed, repeats=REPEATS, gap=REPEAT_GAP):
    """The page's items: every unit once and `repeats` of them twice, in a seeded order with a repeat at least `gap`
    items after its first hearing, letters balanced and every candidate on another letter in a repeat.
    -> [{**unit, id, n, letters: {letter: cand}, repeat_of}]."""
    rng = random.Random(seed)
    twice = [u["slug"] for u in rng.sample(sorted(units, key=lambda u: u["slug"]), repeats)]
    by = {u["slug"]: u for u in units}
    seq = sorted(by) + twice
    while True:
        rng.shuffle(seq)
        if all(seq.index(t) + gap <= len(seq) - 1 - seq[::-1].index(t) for t in twice):
            break
    while True:
        perms = balanced(rng, len(seq))
        if all(all(x != y for x, y in zip(perms[seq.index(t)], perms[len(seq) - 1 - seq[::-1].index(t)])) for t in twice):
            break
    items, first = [], {}
    for n, (slug, order) in enumerate(zip(seq, perms), 1):
        items.append({**by[slug], "id": f"i{n}", "n": n, "letters": dict(zip(LETTERS, order)),
                      "repeat_of": first.get(slug)})
        first.setdefault(slug, f"i{n}")
    return items


def window(a, b, n_ref, n_ren, lag):
    """The judge's window (`analysis.aligned`) for half [a, b) in samples: record[s0:s1] lines up with
    render[s0 - lag:s1 - lag]; it stops where either side ends."""
    return max(a, lag if lag > 0 else 0), min(b, n_ref, n_ren + lag)


def unblind(item, ans):
    """One item's answer -> {cand: {rank, close}}, or None unless all four ranks and ratings are there."""
    r, c = ans.get("rank") or {}, ans.get("close") or {}
    if sorted(r.get(L) or 0 for L in LETTERS) != [1, 2, 3, 4] or any(c.get(L) not in CLOSE_VALUE for L in LETTERS):
        return None
    return {item["letters"][L]: {"rank": r[L], "close": CLOSE_VALUE[c[L]]} for L in LETTERS}


def band_mean(rows):
    """[(band, x)] -> the mean of the bands' means."""
    b = {}
    for k, x in rows:
        b.setdefault(k, []).append(x)
    return sum(sum(v) / len(v) for v in b.values()) / len(b)


def boot(rows, n=BOOT_N, seed=BOOT_SEED):
    """90% percentile interval of `band_mean` over bands resampled with replacement."""
    rng = random.Random(seed)
    b = {}
    for k, x in rows:
        b.setdefault(k, []).append(x)
    means = [sum(v) / len(v) for v in b.values()]
    d = sorted(sum(rng.choices(means, k=len(means))) / len(means) for _ in range(n))
    return d[int(0.05 * n)], d[int(0.95 * n) - 1]


def pair_row(rows):
    """[(band, a - b)] -> the row's mean, interval and counts (better = above zero)."""
    lo, hi = boot(rows)
    bands = {}
    for k, x in rows:
        bands.setdefault(k, []).append(x)
    return {"mean": band_mean(rows), "lo90": lo, "hi90": hi, "parts_above": sum(x > 0 for _, x in rows),
            "parts_level": sum(x == 0 for _, x in rows), "parts_below": sum(x < 0 for _, x in rows), "parts": len(rows),
            "bands_above": sum(sum(v) > 0 for v in bands.values()), "bands": len(bands)}


def report(items, heard):
    """items: the key's; heard: {item id: unblind's result}. First hearings make the rows, repeats the consistency."""
    first = [it for it in items if it["repeat_of"] is None and heard.get(it["id"])]
    rows = {"parts": len(first), "candidates": {}, "against_S": {}, "by_class": {}, "ear_vs_score": {}, "repeats": []}
    for c in CANDS:
        rows["candidates"][c] = {
            "mean_rank": band_mean([(it["band"], heard[it["id"]][c]["rank"]) for it in first]),
            "mean_close": band_mean([(it["band"], heard[it["id"]][c]["close"]) for it in first]),
            "first_places": sum(heard[it["id"]][c]["rank"] == 1 for it in first),
            "last_places": sum(heard[it["id"]][c]["rank"] == 4 for it in first)}
    for m in MODELS:
        rows["against_S"][m] = {
            "rank": pair_row([(it["band"], heard[it["id"]]["S"]["rank"] - heard[it["id"]][m]["rank"]) for it in first]),
            "close": pair_row([(it["band"], heard[it["id"]][m]["close"] - heard[it["id"]]["S"]["close"])
                               for it in first])}
    rows["score_on_items"] = {m: pair_row([(it["band"], math.log(it["judge"]["S"] / it["judge"][m])) for it in first])
                              for m in MODELS}
    for cls in sorted({it["cls"] for it in first}):
        sub = [it for it in first if it["cls"] == cls]
        rows["by_class"][cls] = {"parts": len(sub), **{m: {
            "rank": band_mean([(it["band"], heard[it["id"]]["S"]["rank"] - heard[it["id"]][m]["rank"]) for it in sub]),
            "close": band_mean([(it["band"], heard[it["id"]][m]["close"] - heard[it["id"]]["S"]["close"]) for it in sub]),
            "parts_above": sum(heard[it["id"]][m]["rank"] < heard[it["id"]]["S"]["rank"] for it in sub)}
            for m in MODELS}}
    per = [(it["band"], spearman([heard[it["id"]][c]["rank"] for c in CANDS], [it["judge"][c] for c in CANDS]))
           for it in first]
    per = [(b, r) for b, r in per if r is not None]
    lo, hi = boot(per)
    gaps = []
    for m in MODELS:
        for it in first:
            ear = heard[it["id"]]["S"]["rank"] - heard[it["id"]][m]["rank"]
            sc = math.log(it["judge"]["S"] / it["judge"][m])
            gaps.append((ear > 0) == (sc > 0))
    rows["ear_vs_score"] = {"spearman_mean": band_mean(per), "lo90": lo, "hi90": hi, "items": len(per),
                            "same_side_of_S": sum(gaps), "pairs": len(gaps)}
    for it in items:
        if it["repeat_of"] and heard.get(it["id"]) and heard.get(it["repeat_of"]):
            a, b = heard[it["repeat_of"]], heard[it["id"]]
            rows["repeats"].append({"slug": it["slug"], "spearman": spearman([a[c]["rank"] for c in CANDS],
                                                                             [b[c]["rank"] for c in CANDS]),
                                    "same_top": min(a, key=lambda c: a[c]["rank"]) == min(b, key=lambda c: b[c]["rank"])})
    return rows


# --- the page -------------------------------------------------------------------------------------------------------

CSS = r"""
:root { --bg:#fbfaf7; --card:#ffffff; --fg:#1d1d1f; --mute:#6b6b70; --line:#dcdad3; --on:#2f5d8a; --on-fg:#fff;
  --ref:#7a4d1c; --sel:#e8eef5; }
@media (prefers-color-scheme: dark) { :root { --bg:#141416; --card:#1d1d20; --fg:#ececee; --mute:#9a9aa2;
  --line:#34343a; --on:#6f9fd0; --on-fg:#0d1117; --ref:#d9a35f; --sel:#23303d; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI",
  Roboto, sans-serif; }
main { max-width:760px; margin:0 auto; padding:16px 16px 120px; }
h1 { font-size:1.35rem; margin:.4rem 0 .6rem; }
.intro { color:var(--mute); }
.item { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; margin:18px 0; }
.item.current { border-color:var(--on); }
.num { color:var(--mute); font-size:.85rem; }
.item h3 { margin:.2rem 0 .7rem; font-size:1.1rem; }
.plays { display:flex; flex-wrap:wrap; gap:8px; }
.plays button { min-height:52px; border-radius:10px; border:1px solid var(--line); background:var(--bg);
  color:var(--fg); padding:0 14px; font-weight:600; font-size:1rem; flex:1 1 70px; cursor:pointer; }
.plays .src[data-k="ref"] { color:var(--ref); flex-basis:140px; }
.plays .src[aria-pressed="true"] { background:var(--on); color:var(--on-fg); border-color:var(--on); }
.plays .stop { flex:0 0 64px; }
.now { min-height:1.4em; color:var(--mute); font-size:.9rem; margin:.5rem 0; }
.rank { display:grid; grid-template-columns:auto repeat(4, 1fr); gap:6px 8px; align-items:center; margin:.6rem 0; }
.rank .lab { font-weight:700; width:2.2em; }
.rank button, .conf button { min-height:44px; border-radius:9px; border:1px solid var(--line); background:var(--bg);
  color:var(--fg); font-size:.95rem; cursor:pointer; }
.rank button[aria-pressed="true"], .conf button[aria-pressed="true"] { background:var(--on); color:var(--on-fg);
  border-color:var(--on); }
.rank .hd { color:var(--mute); font-size:.8rem; text-align:center; }
.conf { display:flex; gap:8px; margin:.4rem 0 .6rem; align-items:center; flex-wrap:wrap; }
.conf button { flex:1 1 90px; }
.note { width:100%; min-height:44px; border-radius:9px; border:1px solid var(--line); background:var(--bg);
  color:var(--fg); padding:8px 10px; font-size:.95rem; }
.done { color:var(--on); font-size:.85rem; }
footer { position:fixed; left:0; right:0; bottom:0; background:var(--card); border-top:1px solid var(--line);
  padding:10px 16px calc(10px + env(safe-area-inset-bottom)); display:flex; gap:8px; justify-content:center; }
footer button { min-height:48px; border-radius:10px; border:1px solid var(--line); background:var(--bg);
  color:var(--fg); padding:0 18px; font-weight:600; font-size:1rem; }
footer .primary { background:var(--on); color:var(--on-fg); border-color:var(--on); }
#exp { display:none; position:fixed; inset:10% 5% auto 5%; max-width:640px; margin:0 auto; background:var(--card);
  border:1px solid var(--line); border-radius:14px; padding:16px; z-index:5; }
#exp textarea { width:100%; height:220px; font:12px/1.4 ui-monospace, monospace; background:var(--bg);
  color:var(--fg); border:1px solid var(--line); border-radius:8px; }
#exp .row { display:flex; gap:8px; margin-top:8px; }
#exp .row button { flex:1; min-height:44px; border-radius:9px; border:1px solid var(--line); background:var(--bg);
  color:var(--fg); }
.close button { font-size:.82rem; }
.q { margin:.7rem 0 .1rem; font-weight:600; }
"""

JS = r"""
const DATA = JSON.parse(document.getElementById("data").textContent);
const CLIPS = JSON.parse(document.getElementById("clips").textContent);
const STORE = "ear-vreal:" + DATA.build;
const XF = 0.012, KEYS = ["ref", "A", "B", "C", "D"];
let ans = {};
try { ans = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (e) { ans = {}; }
function save() { try { localStorage.setItem(STORE, JSON.stringify(ans)); } catch (e) {} }
const items = Array.from(document.querySelectorAll(".item"));
let actx = null, cur = null, token = 0;
const bufs = {};
try { if (navigator.audioSession) navigator.audioSession.type = "playback"; } catch (e) {}
function bytes(k) { const b = atob(CLIPS[k]); const u = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u.buffer; }
function decode(k) { if (!bufs[k]) bufs[k] = new Promise((ok, no) => actx.decodeAudioData(bytes(k), ok, no));
  return bufs[k]; }
const NAMES = {ref: "the record's guitar", A: "A", B: "B", C: "C", D: "D"};
function mark() {
  items.forEach(it => it.querySelectorAll(".src").forEach(b => b.setAttribute("aria-pressed",
    String(!!cur && cur.it === it && b.dataset.k === cur.k))));
  if (cur) cur.it.querySelector(".now").textContent = "Playing " + NAMES[cur.k] + " (loops; switch any time)";
}
function stop() {
  token++;
  if (!cur) return;
  cur.srcs.forEach(s => { try { s.stop(); } catch (e) {} });
  cur.it.querySelector(".now").textContent = ""; cur = null; mark();
}
async function start(it, k) {
  stop();
  const my = token;
  items.forEach(i => i.classList.remove("current")); it.classList.add("current");
  if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
  try { await actx.resume(); } catch (e) {}
  it.querySelector(".now").textContent = "Loading...";
  let b;
  try { b = await Promise.all(KEYS.map(x => decode(it.dataset.id + "-" + x))); }
  catch (e) { it.querySelector(".now").textContent = "This browser could not decode the clips."; return; }
  if (my !== token) return;
  const end = Math.min(...b.map(x => x.duration)), t0 = actx.currentTime + 0.05;
  const srcs = [], gains = {};
  b.forEach((buf, j) => {
    const s = actx.createBufferSource(); s.buffer = buf; s.loop = true; s.loopStart = 0; s.loopEnd = end;
    const g = actx.createGain(); g.gain.value = KEYS[j] === k ? 1 : 0;
    s.connect(g); g.connect(actx.destination); s.start(t0); srcs.push(s); gains[KEYS[j]] = g;
  });
  cur = {it: it, srcs: srcs, gains: gains, k: k}; mark();
}
function pick(it, k) {
  if (!cur || cur.it !== it) { start(it, k); return; }
  if (cur.k === k) return;
  const t = actx.currentTime;
  KEYS.forEach(x => { const g = cur.gains[x].gain; g.cancelScheduledValues(t); g.setValueAtTime(g.value, t);
    g.linearRampToValueAtTime(x === k ? 1 : 0, t + XF); });
  cur.k = k; mark();
}
function paint() {
  let n = 0;
  items.forEach(it => {
    const a = ans[it.dataset.id] || {}, r = a.rank || {};
    it.querySelectorAll(".rank:not(.close) button").forEach(b => b.setAttribute("aria-pressed",
      String(r[b.dataset.l] === Number(b.dataset.r))));
    it.querySelectorAll(".conf button").forEach(b => b.setAttribute("aria-pressed", String(a.conf === b.dataset.c)));
    const cl = a.close || {};
    it.querySelectorAll(".close button").forEach(b => b.setAttribute("aria-pressed", String(cl[b.dataset.l] === b.dataset.v)));
    const full = ["A", "B", "C", "D"].every(l => r[l] && cl[l]) && a.conf;
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
  it.querySelectorAll(".rank:not(.close) button").forEach(b => b.addEventListener("click", () => {
    const a = ans[id] = ans[id] || {}; const r = a.rank = a.rank || {};
    const l = b.dataset.l, v = Number(b.dataset.r);
    Object.keys(r).forEach(o => { if (o !== l && r[o] === v) delete r[o]; });   // a rank is held by one letter
    if (r[l] === v) delete r[l]; else r[l] = v;
    save(); paint();
  }));
  it.querySelectorAll(".close button").forEach(b => b.addEventListener("click", () => {
    const a = ans[id] = ans[id] || {}; const c = a.close = a.close || {};
    if (c[b.dataset.l] === b.dataset.v) delete c[b.dataset.l]; else c[b.dataset.l] = b.dataset.v;
    save(); paint();
  }));
  it.querySelectorAll(".conf button").forEach(b => b.addEventListener("click", () => {
    const a = ans[id] = ans[id] || {}; a.conf = a.conf === b.dataset.c ? undefined : b.dataset.c; save(); paint();
  }));
  it.querySelector(".note").addEventListener("input", e => {
    const a = ans[id] = ans[id] || {}; a.note = e.target.value; save(); paint(); });
});
document.addEventListener("keydown", e => {
  if (e.metaKey || e.ctrlKey || e.altKey || (e.target.closest && e.target.closest("input, textarea"))) return;
  const it = cur ? cur.it : document.querySelector(".item.current") || items[0];
  const m = {r: "ref", a: "A", b: "B", c: "C", d: "D", "1": "ref", "2": "A", "3": "B", "4": "C", "5": "D"};
  const k = (e.key || "").toLowerCase();
  if (m[k]) { e.preventDefault(); pick(it, m[k]); }
  else if (k === "escape" || k === " ") { e.preventDefault(); stop(); }
});
function exportText() {
  const lines = ["ear-vreal build " + DATA.build + " " + new Date().toISOString()];
  items.forEach(it => {
    const a = ans[it.dataset.id] || {}, r = a.rank || {};
    const order = ["A", "B", "C", "D"].filter(l => r[l]).sort((p, q) => r[p] - r[q]);
    const cl = a.close || {};
    lines.push(it.dataset.n + " " + (order.join(">") || "-") + " " + ["A", "B", "C", "D"].map(l => l + ":" + (cl[l] || "-")).join(" ") + " " + (a.conf || "-") + (a.note ? " | " + a.note : ""));
  });
  lines.push(JSON.stringify({build: DATA.build, answers: ans}));
  return lines.join("\n");
}
document.getElementById("export").addEventListener("click", () => { stop();
  document.getElementById("out").value = exportText(); document.getElementById("exp").style.display = "block"; });
document.getElementById("close").addEventListener("click", () => document.getElementById("exp").style.display = "none");
document.getElementById("copy").addEventListener("click", async () => {
  const t = document.getElementById("out"); t.select();
  try { await navigator.clipboard.writeText(t.value); } catch (e) { document.execCommand("copy"); } });
document.getElementById("save").addEventListener("click", () => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([exportText()], {type: "text/plain"}));
  a.download = "ear-vreal-answers-" + DATA.build + ".txt"; a.click(); });
paint();
"""

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Record tone check</title>
<style>@@CSS@@</style></head><body>
<main>
<h1>Which preset sounds most like the record?</h1>
<p class="intro">@@COUNT@@ items of about 4 seconds, looping. <b>Record</b> is the guitar as it was recorded through a real
amp. A, B, C and D are four presets playing <b>the very same performance</b>, so every note lines up and only the tone
differs. Everything loops together and switches instantly at the same moment: tap a button, or press R, A, B, C, D (or
1-5); Space stops. All clips are set to the same loudness. Headphones, please.</p>
<p class="intro">For each item, rank A, B, C and D by how close their tone is to the Record (1st = closest), then rate
how close each one is: two presets can get the same rating if you cannot tell them apart. Say whether you are sure.
Which preset is which is hidden and shuffled per item, and a few items may come back later. Answers are saved in this
browser as you go; tap <b>Export</b> any time and send the text.</p>
@@CARDS@@
</main>
<footer><span id="count" style="align-self:center;color:var(--mute)"></span>
<button type="button" id="export" class="primary">Export</button></footer>
<div id="exp"><b>Your answers</b><p class="intro">Copy it or save it as a file, and send it.</p>
<textarea id="out" readonly></textarea>
<div class="row"><button type="button" id="copy">Copy</button><button type="button" id="save">Save file</button>
<button type="button" id="close">Close</button></div></div>
<script id="data" type="application/json">@@DATA@@</script>
<script id="clips" type="application/json">@@CLIPS@@</script>
<script>@@JS@@</script></body></html>"""


# --- the commands ----------------------------------------------------------------------------------------------------

def data_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "ear-vreal"


def page_dir():
    from learn import pretrain_set as PS

    return PS.HOME / "listening" / "ear-vreal"


def stored(tag, unit):
    """(answer, stored judge group's held distance, stored render hash) of `tag` on a unit's direction."""
    from learn import pipeline_fix as P

    key, root = f"{unit['slug']}|{unit['amp']}", P.out_dir() / P.VREAL_DIR
    ans = json.loads((root / "answers" / f"{tag}.json").read_text())["answers"][key]
    grp = json.loads((root / "judge" / tag / f"{key}.json").read_text())
    half = unit["search"] if unit["search"] in ans else P.ANY_HALF
    return ans[half], grp["judge"][half][unit["held"]], grp["render_sha256"][half]


def activity(ref):
    """The share of 100-ms frames within ACTIVE_DB of the crop's loudest, per judge half (`record_match_listening`)."""
    import numpy as np

    from learn import rescore as R

    fr = int(0.1 * SR)
    db = np.array([20 * np.log10(np.sqrt(np.mean(ref[i:i + fr] ** 2)) + 1e-12) for i in range(0, len(ref) - fr, fr)])
    return {h: float(np.mean(db[int(a * 10):int(b * 10)] > db.max() - ACTIVE_DB)) for h, (a, b) in R.HALVES.items()}


def cmd_plan(_args):
    """The items, from the record's activity and S's stored distances alone; no model's answer or score is opened."""
    from learn import knob_ceiling as K
    from learn import pipeline_fix as P
    from learn import pipeline_review as PR

    P.require(PHASE)
    root, plan, drift, dirs, parts, ms = P.vreal_ctx()
    rows = []
    for slug, (band, cls) in sorted(PR.VREAL.items()):
        s = {a: json.loads((P.out_dir() / P.VREAL_DIR / "judge" / "S" / f"{slug}|{a}.json").read_text())["judge"]
             [P.ANY_HALF] for a in K.AMPS}
        rows.append({"slug": slug, "key": P.vreal_part_key(slug), "band": band, "cls": cls,
                     "act": activity(P.amp_track(slug, parts[slug])), "s": s})
    units = choose(rows)
    items = draw(units, PAGE_SEED)
    P.save(data_dir() / "plan.json", {"phase": PHASE, "seed": PAGE_SEED, "units": units, "items": items,
                                      "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    for u in units:
        print(f"{u['band']:<20} {u['slug']:<52} {u['cls']:<7} {u['amp']:<6} held {u['held']} active {u['active']:.2f}")
    print(f"EAR-VREAL PLAN: {len(units)} parts, {len(items)} items, {len({u['band'] for u in units})} bands")


def cmd_render(args):
    """Every candidate on every unit through the part's measure DI, in `vreal_render`'s recipe; a kept render whose
    hash differs from the stored one stops the shard. The held window, aligned to the record, is kept."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import rescore as R
    from learn import trusted_data as T
    from learn import trusted_data_t3 as T3

    P.require(PHASE)
    k, n = (int(x) for x in args.shard.split("/"))
    units = json.loads((data_dir() / "plan.json").read_text())["units"]
    if args.only:
        units = [u for u in units if u["slug"] == args.only]
    root, plan, drift, dirs, parts, ms = P.vreal_ctx()
    LO._wait_cap()
    rr = CB.new_renderer()
    try:
        menu = rr.menu()
    finally:
        rr.close()
    renders = 0
    for u in [u for j, u in enumerate(units) if j % n == k]:
        slug, amp, held = u["slug"], u["amp"], u["held"]
        info = parts[slug]
        ctx = (A.group_ctx(menu, ms, "F", slug, amp) if info["kind"] == "stagef"
               else T3.t3_group_ctx(menu, ms, info, amp))
        lag = ctx["part"]["judge_lag"]
        a, b = (int(x * SR) for x in R.HALVES[held])
        rec = {"slug": slug, "amp": amp, "held": held, "search": u["search"], "lag": lag, "judge": {}, "sha": {}}
        out = data_dir() / "renders" / slug
        if (out / "rec.json").exists():
            continue
        clips = {}
        for c, tag in CANDS.items():
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            ans, d, sha = stored(tag, u)
            st = LO.tdict(ans["settings"])
            y = AM.fresh_render(CB.new_renderer, ctx["di32"], ans["select"], st, st)
            renders += 2
            if AM.audio_sha(y) != sha:
                raise SystemExit(f"{slug} {amp} {c}: the render differs from the stored one; stop")
            mono = y.mean(axis=1) if y.ndim == 2 else y
            s0, s1 = window(a, b, len(ctx["ref"]), len(mono), lag)
            clips[c] = mono[s0 - lag:s1 - lag].astype(np.float32)
            rec["judge"][c], rec["sha"][c] = d, sha
        rec["window"] = [s0, s1]
        out.mkdir(parents=True, exist_ok=True)
        np.savez(out / "clips.npz", **clips)
        P.save(out / "rec.json", rec)
        print(f"{slug} {amp}: 4 hashes equal the stored renders; renders so far {renders}", flush=True)
    print(f"EAR-VREAL RENDER DONE {k}/{n}: {renders} renders")


def level_group(clips):
    """{name: y} each to -23 LUFS on its own; every clip lowered by the item's largest peak cut (`real-song-check`)."""
    from learn import build_data_review as BDR

    lev = {k: BDR.level_clip(v) for k, v in clips.items()}
    cut = max(c for _, _, _, c in lev.values())
    return ({k: y * 10 ** (-(cut - c) / 20) for k, (y, _, _, c) in lev.items()},
            {k: {"gain_db": g - (cut - c), "own_peak_cut_db": c, "group_cut_db": cut} for k, (_, g, _, c) in lev.items()})


def encode(y, cache):
    """A levelled clip -> AAC base64."""
    import numpy as np
    import soundfile as sf

    from learn import audibility_measure as AM
    from learn import build_data_review as BDR

    y = BDR.fade(y)
    cache.mkdir(parents=True, exist_ok=True)
    flac = cache / f"{hashlib.sha256(y.astype(np.float32).tobytes()).hexdigest()[:16]}.flac"
    if not flac.exists():
        sf.write(str(flac), y, SR, subtype="PCM_24")
    return AM.aac_b64(flac, cache)


def cards(items):
    out = []
    for it in items:
        rank = "".join(f'<span class="lab">{L}</span>' + "".join(
            f'<button type="button" data-l="{L}" data-r="{r}">{t}</button>'
            for r, t in ((1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"))) for L in LETTERS)
        close = "".join(f'<span class="lab">{L}</span>' + "".join(
            f'<button type="button" data-l="{L}" data-v="{v}">{t}</button>' for v, t in CLOSE) for L in LETTERS)
        out.append(
            f'<article class="item" data-id="{it["id"]}" data-n="{it["n"]}">'
            f'<div class="num">{it["n"]} / {len(items)}</div><h3>Recording {it["n"]}</h3><div class="plays">'
            '<button type="button" class="src" data-k="ref" aria-pressed="false">Record (R)</button>'
            + "".join(f'<button type="button" class="src" data-k="{L}" aria-pressed="false">{L}</button>' for L in LETTERS)
            + '<button type="button" class="stop" aria-label="Stop">&#9632;</button></div><p class="now"></p>'
            '<div class="rank"><span></span><span class="hd">closest</span><span class="hd"></span><span class="hd"></span>'
            f'<span class="hd">furthest</span>{rank}</div>'
            f'<div class="q">How close is each one to the Record?</div><div class="rank close">{close}</div>'
            '<div class="conf"><span>Confidence:</span><button type="button" data-c="sure">Sure</button>'
            '<button type="button" data-c="unsure">Unsure</button></div>'
            f'<input class="note" type="text" placeholder="Note (optional)" aria-label="Note">'
            f'<div class="done"></div></article>')
    return "".join(out)


def cmd_page(args):
    import numpy as np

    from learn import pipeline_fix as P

    P.require(PHASE)
    key_path = data_dir() / "key.json"
    if key_path.exists() and not args.force:
        raise SystemExit(f"{key_path} exists: a rebuild hides the listener's stored answers (--force)")
    plan = json.loads((data_dir() / "plan.json").read_text())
    root, _, _, _, parts, _ = P.vreal_ctx()
    cache, od = data_dir() / "aac-cache", page_dir()
    od.mkdir(parents=True, exist_ok=True)
    clips, kept = {}, []
    for it in plan["items"]:
        d = data_dir() / "renders" / it["slug"]
        rec = json.loads((d / "rec.json").read_text())
        s0, s1 = rec["window"]
        z = np.load(d / "clips.npz")
        ref = np.asarray(P.amp_track(it["slug"], parts[it["slug"]]), np.float64)[s0:s1]
        group = {"ref": ref, **{L: np.asarray(z[c], np.float64) for L, c in it["letters"].items()}}
        if len({len(v) for v in group.values()}) != 1:
            raise SystemExit(f"{it['slug']}: clip lengths differ")
        lev, info = level_group(group)
        for k, y in lev.items():
            clips[f"{it['id']}-{k}"] = encode(y, cache)
        kept.append({**it, "judge": rec["judge"], "sha": rec["sha"], "levels": info, "window": rec["window"]})
    salt = secrets.token_hex(8)
    build = hashlib.sha256((json.dumps([k["letters"] for k in kept]) + salt).encode()).hexdigest()[:12]
    body = cards(kept)
    data = json.dumps({"build": build, "items": [{"id": it["id"], "n": it["n"]} for it in kept]})
    page = PAGE.replace("@@COUNT@@", str(len(kept))).replace("@@CARDS@@", body).replace("@@CSS@@", CSS) \
        .replace("@@DATA@@", data).replace("@@CLIPS@@", json.dumps(clips)).replace("@@JS@@", JS)
    leaks = [w for w in (*CANDS, *{it["slug"] for it in kept}, *{it["band"] for it in kept})
             if len(w) > 2 and w in body + data]
    if leaks:
        raise SystemExit(f"the page names {leaks}")
    P.save(key_path, {"page": "ear-vreal", "build": build, "phase": PHASE, "items": kept,
                      "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    (od / "index.html").write_text(page)
    print(f"EAR-VREAL PAGE DONE: {len(kept)} items, {(od / 'index.html').stat().st_size / 1e6:.1f} MB -> "
          f"{od / 'index.html'}; build {build}")


def cmd_score(args):
    from learn import pipeline_fix as P

    P.require(PHASE)
    key = json.loads((data_dir() / "key.json").read_text())
    last = [ln for ln in pathlib.Path(args.answers).read_text().splitlines() if ln.startswith("{")][-1]
    ex = json.loads(last)
    if ex.get("build") != key["build"]:
        raise SystemExit(f"{args.answers}: build {ex.get('build')}, this page's is {key['build']}")
    heard = {it["id"]: unblind(it, ex["answers"].get(it["id"]) or {}) for it in key["items"]}
    rep = report(key["items"], heard)
    rep.update(build=key["build"], answered=sum(v is not None for v in heard.values()), items=len(key["items"]),
               unsure=[it["id"] for it in key["items"] if (ex["answers"].get(it["id"]) or {}).get("conf") == "unsure"],
               per_item=[{"slug": it["slug"], "band": it["band"], "cls": it["cls"], "amp": it["amp"],
                          "repeat_of": it["repeat_of"], "judge": it["judge"], "heard": heard[it["id"]],
                          "note": (ex["answers"].get(it["id"]) or {}).get("note")} for it in key["items"]])
    P.save(data_dir() / "score.json", rep)
    print(json.dumps({k: rep[k] for k in ("answered", "items", "candidates", "against_S", "by_class", "score_on_items",
                                          "ear_vs_score", "repeats")},
                     indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    r = sub.add_parser("render")
    r.add_argument("--shard", default="0/1")
    r.add_argument("--only", help="one part's slug (the first run: an effects-on W)")
    p = sub.add_parser("page")
    p.add_argument("--force", action="store_true")
    s = sub.add_parser("score")
    s.add_argument("--answers", required=True)
    args = ap.parse_args(argv)
    {"plan": cmd_plan, "render": cmd_render, "page": cmd_page, "score": cmd_score}[args.cmd](args)


if __name__ == "__main__":
    main()
