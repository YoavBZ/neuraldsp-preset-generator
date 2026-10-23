"""The trusted-data ear page: T0's queue (`t0/ear-queue.json`) as listening pages.

Three parts, one question each, so each file stays phone-sized:
1. **Targets:** the DI, then the target track (6 s each, both at -23 LUFS); judge the target.
2. **DI and amp pairs:** the DI, then its amp track (10 s each); is the amp track an amp take of this DI?
3. **DIs:** one 10-s DI window; is it a clean, unprocessed DI? Blind: why an item is queued (a D4 flag, a D4-passed
   sample, a conflict, a DI-only part) is not shown, and the DI files are shuffled (seed 20261023), each file's windows
   kept together in time order.

Exports carry page `trusted-data-ear` and the queue's item ids, which `verify_tracks lists --ear` decodes through
`t0/ear-items.json`. Each part exports its own file; pass each as its own `--ear`. A partial export is fine: unanswered
items stay pending. The DI part's blindness has one limit: D4-flagged windows come in runs, so a file with many windows
is likely a flagged one.

Every clip must be audible (peak at least SILENT_PEAK): the build refuses a silent window.

    $MAIN -m learn.build_ear_page build      # -> ~/ndsp-presets/listening/trusted-data-ear/part-{1,2,3}.html
    $MAIN -m learn.build_ear_page extra      # queued items no built part holds -> part-<next>.html (manifest updated)
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import pathlib
import random
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from learn import verify_tracks as VT  # noqa: E402

T0 = VT.OUT / "t0"
OUT = VT.HOME / "listening" / VT.EAR_PAGE
SEED = 20261023
AAC_KBPS = 96                 # 128 in earlier pages; 96 keeps part 3 (122 clips) near 20 MB for a phone
GAP_S = 0.5
DECIDE_S = 4.0                # listening time beyond the clips, per item
SILENT_PEAK = 1e-4            # a clip whose source window peaks below this is digital silence: refused

LABELS = {
    "target": [("clean_amp", "Clean amp recording"), ("bleed", "Other instruments leak in"),
               ("other_guitar", "Another guitar plays"), ("not_amp", "Not an amp (sounds like the DI)"),
               ("unsure", "Not sure")],
    "di_amp": [("amp", "Yes: an amp take of this DI"), ("same_di", "No: the same DI again (no amp)"),
               ("processed", "The DI itself sounds processed"), ("unsure", "Not sure")],
    "di": [("clean", "Clean DI"), ("processed", "Processed (pedals or effects)"),
           ("not_a_di", "Not a DI (amp or mic sound)"), ("hum", "Hum or buzz"), ("unsure", "Not sure")],
}
PARTS = {
    1: dict(family="target", title="Targets",
            question="Judge the second sound, the target: is it a clean amp recording?",
            intro="Each Play button plays the DI first, then, after a short gap, the target track (the original "
                  "amp sound we train toward) from the same moment. <b>Judge the target only</b>: is it an amp "
                  "recording with no other instruments leaking in and no other guitar? The DI is there for "
                  "comparison. Both are levelled to the same loudness (&minus;23 LUFS)."),
    2: dict(family="di_amp", title="DI and amp pairs",
            question="Is the second sound an amp recording of this same DI take?",
            intro="Each Play button plays the DI first, then, after a short gap, the track the session lists as "
                  "its amp, from the same moment. Is the second sound <b>an amp recording of this same "
                  "performance</b>? If it is just the DI again, pick <b>No</b>. If the DI itself sounds "
                  "processed (pedals or effects before the DI box), say so. Both are levelled to &minus;23 LUFS."),
    3: dict(family="di", title="DIs",
            question="Is this a clean, unprocessed DI?",
            intro="Each clip is a DI alone, 10 seconds. Is it a <b>clean, unprocessed DI</b>: the guitar straight "
                  "into the DI box, no pedals or effects, no amp or mic sound, no hum? Clips of the same DI file "
                  "sit together. Levelled to &minus;23 LUFS."),
}


def plan_parts(queue, seed=SEED):
    """{part: [items in display order]}. Targets by key then half; pairs in queue order; DIs blind: files shuffled
    with `seed`, each file's windows in time order."""
    targets = sorted((i for i in queue if i["family"] == "target"), key=lambda i: (i["key"], i["half"]))
    pairs = [i for i in queue if i["family"] == "di_amp"]
    by_file = {}
    for i in queue:
        if i["family"] == "di":
            by_file.setdefault(i["paths"]["di"], []).append(i)
    files = sorted(by_file)
    random.Random(seed).shuffle(files)
    dis = [i for f in files for i in sorted(by_file[f], key=lambda i: i["start_s"])]
    left = {i["family"] for i in queue} - {"target", "di_amp", "di"}
    if left:
        raise SystemExit(f"unknown item families {sorted(left)}")
    return {1: targets, 2: pairs, 3: dis}


def title_of(item):
    """'Song · track' from the item's paths; a crop's slug when the DI is a crop's."""
    p = pathlib.Path(item["paths"]["di"])
    if p.name == "di.wav":                          # validation-crops/<source>-<Song>-<Track>/di.wav
        song, _, track = p.parent.name.split("-", 1)[1].rpartition("-")
        return f"{song.replace('_', ' ')} · {track}"
    folder = p.parent.name.removesuffix("_Full")
    return f"{folder.replace('_', ' ')} · {p.stem}"


def mmss(t):
    s = f"{int(t // 60)}:{int(t % 60):02d}"
    return s if t == int(t) else s + f"{t % 1:.1f}"[1:]


def subtitle_of(item):
    a, b = item["start_s"], item["start_s"] + item["dur_s"]
    if item["family"] == "target":
        half = "first" if item["half"] == "A" else "second"
        return f"Crop {a:.1f}–{b:.1f} s (covers its {half} half) · DI, then the target track"
    if item["family"] == "di_amp":
        return (f"{mmss(a)}–{mmss(b)} · DI ({pathlib.Path(item['paths']['di']).name}), then "
                f"{pathlib.Path(item['paths']['amp']).name}")
    return f"{mmss(a)}–{mmss(b)} · {pathlib.Path(item['paths']['di']).name}"


def seconds_of(item):
    n = 2 if item["family"] in ("target", "di_amp") else 1
    return n * item["dur_s"] + (n - 1) * GAP_S + DECIDE_S


def clip_b64(path, start_s, dur_s, cache):
    """A mono clip at -23 LUFS with 10-ms fades, AAC at AAC_KBPS, cached by its source and window, as base64."""
    import soundfile as sf

    from learn import build_data_review as BDR

    key = hashlib.sha256(f"{path}|{start_s}|{dur_s}|{AAC_KBPS}".encode()).hexdigest()[:16]
    m4a = pathlib.Path(cache) / f"{key}.m4a"
    x = BDR.load(path, start_s, dur_s)                  # checked even when cached
    if not abs(x).max() >= SILENT_PEAK:
        raise SystemExit(f"silent window: {path} at {start_s} s (peak {abs(x).max():.2g}); fix the queue first")
    if not m4a.exists():
        m4a.parent.mkdir(parents=True, exist_ok=True)
        y, _, _, _ = BDR.level_clip(x)
        flac = m4a.with_suffix(".flac")
        sf.write(str(flac), BDR.fade(y), BDR.SR, subtype="PCM_24")
        tmp = m4a.with_name(m4a.stem + ".tmp.m4a")
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", str(AAC_KBPS * 1000), str(flac), str(tmp)],
                       check=True)
        tmp.replace(m4a)
        flac.unlink()
    return base64.b64encode(m4a.read_bytes()).decode()


def item_clips(item):
    """[(clip key, source path, start, duration, 'Now:' label)] in play order."""
    a, d = item["start_s"], item["dur_s"]
    if item["family"] == "target":
        return [(item["id"] + "-di", item["paths"]["di"], a, d, "the DI"),
                (item["id"] + "-target", item["paths"]["target"], a, d, "the target track")]
    if item["family"] == "di_amp":
        return [(item["id"] + "-di", item["paths"]["di"], a, d, "the DI"),
                (item["id"] + "-amp", item["paths"]["amp"], a, d, "the amp track")]
    return [(item["id"] + "-di", item["paths"]["di"], a, d, "the DI")]


ASK = {"target": "Judge the target (second sound): a clean amp recording?",
       "di_amp": "Is the second sound an amp recording of this same DI take?",
       "di": "Is this a clean, unprocessed DI?"}


def item_html(item, n, total, ask=False):
    e = html.escape
    clips = item_clips(item)
    seq = ",".join(c[0] for c in clips)
    names = "|".join(c[4] for c in clips)
    plays = [f'<button type="button" class="play main" data-seq="{seq}" data-names="{e(names)}">&#9654; Play</button>']
    if len(clips) == 2:
        plays += [f'<button type="button" class="play small" data-seq="{c[0]}" data-names="{e(c[4])}">'
                  f'{"DI only" if c[0].endswith("-di") else ("Target only" if c[0].endswith("-target") else "Amp only")}'
                  f'</button>' for c in clips]
    vs = "".join(f'<button type="button" class="v" data-v="{v}">{e(t)}</button>' for v, t in LABELS[item["family"]])
    return (f'<article class="item" data-id="{item["id"]}" data-n="{n}"><div class="num">{n} / {total}</div>'
            f'<h3>{e(title_of(item))}</h3><p class="sub">{e(subtitle_of(item))}</p>'
            + (f'<p class="ask"><b>{e(ASK[item["family"]])}</b></p>' if ask else "") +
            f'<div class="plays">{"".join(plays)}</div><p class="now"></p><div class="vs">{vs}</div>'
            f'<input class="note" type="text" placeholder="Note (optional)" aria-label="Note"></article>')


CSS = """
:root { --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e3e0d8; --card:#fff; --on:#1d1d1b;
        --on-fg:#fff; --accent:#2f6f4f; --bar:#e9e6de; }
@media (prefers-color-scheme: dark) { :root { --bg:#171716; --fg:#ecebe6; --muted:#a19f97; --line:#34332f;
  --card:#201f1d; --on:#ecebe6; --on-fg:#171716; --accent:#7fc4a0; --bar:#2c2b28; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
       font:17px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
header { position:sticky; top:0; z-index:5; background:var(--card); border-bottom:1px solid var(--line); padding:10px 16px; }
.prog { height:6px; background:var(--bar); border-radius:3px; overflow:hidden; margin-top:6px; }
.prog > div { height:100%; width:0; background:var(--accent); }
.hrow { display:flex; gap:10px; align-items:center; justify-content:space-between; flex-wrap:wrap; }
.hrow label { font-size:15px; display:flex; gap:6px; align-items:center; }
main { max-width:720px; margin:0 auto; padding:8px 16px 140px; }
h1 { font-size:1.2rem; margin:14px 0 4px; }
.ask, .intro { color:var(--muted); margin:2px 0 10px; }
.item { border:1px solid var(--line); border-radius:12px; background:var(--card); padding:12px 14px;
        margin:12px 0; scroll-margin-top:90px; }
.item.done { opacity:.72; }
.item.current { outline:2px solid var(--accent); }
.num { color:var(--muted); font-size:14px; }
h3 { font-size:1.02rem; margin:2px 0; overflow-wrap:anywhere; }
.sub { color:var(--muted); margin:0 0 8px; font-size:15px; overflow-wrap:anywhere; }
.plays { display:flex; gap:8px; flex-wrap:wrap; }
button { font:inherit; color:var(--fg); }
.play { min-height:52px; border-radius:10px; border:1px solid var(--line); background:var(--bg); padding:0 18px; }
.play.main { flex:1 1 60%; font-weight:600; }
.play.small { flex:1 1 30%; font-size:15px; }
.play.on { background:var(--on); color:var(--on-fg); }
.now { min-height:1.3em; margin:4px 0; color:var(--accent); font-size:15px; }
.vs { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.v { min-height:56px; border-radius:10px; border:1px solid var(--line); background:var(--bg); padding:6px; }
.v[aria-pressed="true"] { background:var(--on); color:var(--on-fg); border-color:var(--on); }
.note { width:100%; margin-top:8px; font:inherit; font-size:16px; padding:10px; border-radius:8px;
        border:1px solid var(--line); background:var(--bg); color:var(--fg); }
footer { position:fixed; left:0; right:0; bottom:0; z-index:5; background:var(--card); border-top:1px solid var(--line);
         padding:10px 16px calc(10px + env(safe-area-inset-bottom)); display:flex; gap:8px; }
footer button { flex:1; min-height:48px; border-radius:10px; border:1px solid var(--line); background:var(--bg); }
footer button.primary { background:var(--on); color:var(--on-fg); }
#exp { display:none; position:fixed; inset:0; z-index:9; background:var(--bg); padding:16px; overflow:auto; }
#exp textarea { width:100%; height:50vh; font:13px ui-monospace, monospace; padding:8px; background:var(--card);
                color:var(--fg); border:1px solid var(--line); border-radius:8px; }
#exp .row { display:flex; gap:8px; margin:10px 0; }
#exp .row button { flex:1; min-height:48px; border-radius:10px; border:1px solid var(--line); background:var(--bg); }
"""

JS = """
const DATA = JSON.parse(document.getElementById("data").textContent);
const CLIPS = JSON.parse(document.getElementById("clips").textContent);
const KEY = DATA.page + "/part" + DATA.part + "/" + DATA.build + "/answers";
const AUTO = DATA.page + "/autoplay";
let store = {};
try { store = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) {} };
const items = [...document.querySelectorAll(".item")];
const player = document.getElementById("player");
const urls = {};
let cur = null;           // {btn, seq, names, i}
let gapTimer = null;
function url(key) {
  if (!urls[key]) {
    const bin = atob(CLIPS[key]); const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    urls[key] = URL.createObjectURL(new Blob([buf], {type: "audio/mp4"}));
  }
  return urls[key];
}
function setNow(t) { if (cur) cur.btn.closest(".item").querySelector(".now").textContent = t; }
function stop() {
  player.pause(); clearTimeout(gapTimer);
  if (cur) { setNow(""); cur.btn.classList.remove("on"); }
  cur = null;
}
function step() {
  if (!cur) return;
  if (cur.i >= cur.seq.length) { stop(); return; }
  player.src = url(cur.seq[cur.i]);
  setNow(cur.seq.length > 1 ? "Now: " + cur.names[cur.i] : "");
  player.play().catch(() => {});
}
function play(btn) {
  const same = cur && cur.btn === btn;
  stop();
  if (same) return;
  items.forEach(i => i.classList.remove("current"));
  btn.closest(".item").classList.add("current");
  cur = {btn: btn, seq: btn.dataset.seq.split(","), names: btn.dataset.names.split("|"), i: 0};
  btn.classList.add("on");
  step();
}
player.addEventListener("ended", () => {
  if (!cur) return;
  cur.i++;
  if (cur.i < cur.seq.length) { setNow(""); gapTimer = setTimeout(step, GAP_MS); } else stop();
});
document.querySelectorAll(".play").forEach(b => b.addEventListener("click", () => play(b)));
function paint() {
  let n = 0, left_s = 0;
  items.forEach(it => {
    const a = store[it.dataset.id] || {};
    it.querySelectorAll(".v").forEach(b => b.setAttribute("aria-pressed", String(a.verdict === b.dataset.v)));
    const note = it.querySelector(".note");
    if (document.activeElement !== note) note.value = a.note || "";
    it.classList.toggle("done", !!a.verdict);
    if (a.verdict) n++; else left_s += DATA.secs[it.dataset.id];
  });
  document.getElementById("count").textContent = n + " / " + items.length + " done";
  document.getElementById("bar").style.width = (100 * n / items.length) + "%";
  document.getElementById("left").textContent = n < items.length ? "about " + Math.max(1, Math.round(left_s / 60)) + " min left" : "all answered";
}
function nextOpen(from) {
  const k = items.indexOf(from);
  for (let j = 1; j <= items.length; j++) {
    const it = items[(k + j) % items.length];
    if (!(store[it.dataset.id] || {}).verdict) return it;
  }
  return null;
}
function go(it, autoplay) {
  if (!it) return;
  it.scrollIntoView({behavior: "smooth", block: "start"});
  if (autoplay) play(it.querySelector(".play.main"));
  else { items.forEach(i => i.classList.remove("current")); it.classList.add("current"); }
}
items.forEach(it => {
  it.querySelectorAll(".v").forEach(b => b.addEventListener("click", () => {
    const id = it.dataset.id; const a = store[id] || {};
    a.verdict = a.verdict === b.dataset.v ? null : b.dataset.v; a.t = new Date().toISOString();
    store[id] = a; save(); paint();
    if (a.verdict && document.getElementById("auto").checked) go(nextOpen(it), true);
  }));
  it.querySelector(".note").addEventListener("input", e => {
    const id = it.dataset.id; const a = store[id] || {};
    a.note = e.target.value; a.t = new Date().toISOString(); store[id] = a; save();
  });
});
const auto = document.getElementById("auto");
try { auto.checked = localStorage.getItem(AUTO) === "1"; } catch (e) {}
auto.addEventListener("change", () => { try { localStorage.setItem(AUTO, auto.checked ? "1" : "0"); } catch (e) {} });
document.getElementById("next").addEventListener("click", () => {
  const c = document.querySelector(".item.current") || items[items.length - 1];
  go(nextOpen(c), auto.checked);
});
function exportText() {
  const answers = DATA.items.map(i => ({id: i.id, title: i.title, subtitle: i.subtitle,
    verdict: (store[i.id] || {}).verdict || null, note: (store[i.id] || {}).note || "", t: (store[i.id] || {}).t || null}));
  return JSON.stringify({page: DATA.page, part: DATA.part, build: DATA.build,
    exported: new Date().toISOString(), answered: answers.filter(a => a.verdict).length,
    total: answers.length, answers: answers}, null, 1);
}
document.getElementById("export").addEventListener("click", () => {
  stop(); document.getElementById("out").value = exportText();
  document.getElementById("exp").style.display = "block";
});
document.getElementById("close").addEventListener("click", () => { document.getElementById("exp").style.display = "none"; });
document.getElementById("copy").addEventListener("click", async () => {
  const t = document.getElementById("out");
  try { await navigator.clipboard.writeText(t.value); } catch (e) { t.select(); document.execCommand("copy"); }
});
document.getElementById("save").addEventListener("click", () => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([exportText()], {type: "application/json"}));
  a.download = DATA.page + "-part" + DATA.part + ".json";
  document.body.appendChild(a); a.click(); a.remove();
});
paint();
"""


def page_html(part, items, clips, build, n_parts, title=None):
    fams = {i["family"] for i in items}
    spec = PARTS[part] if part in PARTS else dict(
        title=title or "Extra items",
        question="A few more items: each card says what to judge.",
        intro="These replace items that were silent on the earlier pages. Each card's buttons follow its question: "
              "<b>DI then target</b>, judge the target; <b>DI then amp track</b>, is it an amp take of this DI; "
              "<b>a DI alone</b>, is it a clean, unprocessed DI?")
    if part in PARTS and fams - {spec["family"]}:
        raise SystemExit(f"part {part} holds {sorted(fams)}")
    total = len(items)
    minutes = round(sum(seconds_of(i) for i in items) / 60)
    data = {"page": VT.EAR_PAGE, "part": part, "build": build,
            "items": [{"id": i["id"], "title": title_of(i), "subtitle": subtitle_of(i)} for i in items],
            "secs": {i["id"]: seconds_of(i) for i in items}}
    body = "\n".join(item_html(i, n + 1, total, ask=part not in PARTS) for n, i in enumerate(items))
    js = JS.replace("GAP_MS", str(int(GAP_S * 1000)))
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    clips_json = json.dumps(clips)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Trusted data ear {part}</title>
<style>{CSS}</style></head><body>
<header><div class="hrow"><b>Part {part} of {n_parts}: {spec['title']}</b><span id="count"></span></div>
<div class="hrow"><label><input type="checkbox" id="auto"> Autoplay next</label>
<span id="left" class="ask"></span></div><div class="prog"><div id="bar"></div></div></header>
<main>
<h1>{spec['question']}</h1>
<p class="intro">{total} items, about {minutes} minutes. {spec['intro']} Answers are saved in this browser as you go;
tap <b>Export</b> any time, even halfway, and send the file. Unanswered items simply stay open.</p>
{body}
</main>
<footer><button type="button" id="next">Next unanswered</button>
<button type="button" id="export" class="primary">Export</button></footer>
<div id="exp"><b>Your answers</b><p class="ask">Save it as a file, or copy it, and send it.</p>
<textarea id="out" readonly></textarea>
<div class="row"><button type="button" id="copy">Copy</button><button type="button" id="save">Save file</button>
<button type="button" id="close">Close</button></div></div>
<audio id="player" preload="none" playsinline></audio>
<script id="data" type="application/json">{data_json}</script>
<script id="clips" type="application/json">{clips_json}</script>
<script>{js}</script></body></html>"""


def load_queue():
    q = json.loads((T0 / "ear-queue.json").read_text())
    reg = json.loads((T0 / "ear-items.json").read_text())
    retired = [i["id"] for i in q["queue"] if reg.get(i["id"], {}).get("retired")]
    if retired:
        raise SystemExit(f"{len(retired)} queued items are retired: {retired[:3]}")
    if q.get("page") != VT.EAR_PAGE:
        raise SystemExit(f"ear-queue.json is for page {q.get('page')}")
    missing = [i["id"] for i in q["queue"] if i["id"] not in reg]
    if missing:
        raise SystemExit(f"{len(missing)} queued items are not in ear-items.json: {missing[:3]}")
    build = hashlib.sha256((T0 / "ear-items.json").read_bytes()).hexdigest()[:12]
    return [reg[i["id"]] for i in q["queue"]], build


def write_part(out, part, items, build, n_parts, title=None):
    clips = {}
    for it in items:
        for key, path, a, d, _ in item_clips(it):
            clips[key] = clip_b64(path, a, d, out / "cache")
    p = out / f"part-{part}.html"
    p.write_text(page_html(part, items, clips, build, n_parts, title))
    rec = {"file": p.name, "build": build, "items": [i["id"] for i in items],
           "minutes": round(sum(seconds_of(i) for i in items) / 60, 1), "mb": round(p.stat().st_size / 1e6, 1)}
    print(f"part {part}: {len(items)} items, about {rec['minutes']} min, {rec['mb']} MB -> {p}")
    return rec


def cmd_build(args):
    if (pathlib.Path(args.out) / "manifest.json").exists() and not args.force:
        raise SystemExit("built pages exist: a rebuild changes their build ids and hides the listener's stored "
                         "answers (export them first); use `extra` for new items, or --force")
    queue, build = load_queue()
    parts = plan_parts(queue, args.seed)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"page": VT.EAR_PAGE, "build": build, "seed": args.seed, "aac_kbps": AAC_KBPS, "parts": {}}
    for part, items in parts.items():
        manifest["parts"][str(part)] = write_part(out, part, items, build, len(parts))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))


def cmd_extra(args):
    """Queued items that no built part holds (e.g. re-picked windows after a queue fix) as one more part, in the
    parts' order; the built parts and their stored answers are left alone."""
    out = pathlib.Path(args.out)
    manifest = json.loads((out / "manifest.json").read_text())
    have = {i for rec in manifest["parts"].values() for i in rec["items"]}
    queue, build = load_queue()
    items = [i for part in plan_parts(queue, manifest["seed"]).values() for i in part if i["id"] not in have]
    if not items:
        print("every queued item is on a built part")
        return
    part = max(int(k) for k in manifest["parts"]) + 1
    manifest["parts"][str(part)] = write_part(out, part, items, build, part, title="Extra items")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="the listening pages from t0/ear-queue.json")
    b.add_argument("--out", default=str(OUT))
    b.add_argument("--seed", type=int, default=SEED)
    b.add_argument("--force", action="store_true", help="rebuild over built pages (export their answers first)")
    b.set_defaults(fn=cmd_build)
    x = sub.add_parser("extra", help="queued items no built part holds, as one more part")
    x.add_argument("--out", default=str(OUT))
    x.set_defaults(fn=cmd_extra)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
