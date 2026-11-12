"""LS by ear (`docs/full-controls-plan.md`, "LS in detail"; ledger `pipeline-fix` `phase_ls`): the loudness step's short
page. 12 of LS's 29 items, each with S and the matched preset at their own levels (not level-matched; both lowered by the
same gain so the louder peak sits at -1 dBFS), looping in sync with an instant switch. The question: is B louder than A,
about the same, or quieter? Zero renders: the clips are LS's stored ones.

    .venv/bin/python -m learn.ls_ear ls-page                        # the page (zero renders)
    .venv/bin/python -m learn.ls_ear ls-ear-read OUT --answers F    # the read (zero renders)

The pure parts (the draw, the letters, the unblinding, the sign test) are unit-tested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time

PHASE = "phase_ls"
DRAW_SEED = 20261132
N_ITEMS = 12
ALPHA = 0.10                         # two-sided
MIN_READ = 8                         # answered items for the page to be read (of 12)
NEAR_DB = 1.0                        # the played clips' LUFS gap within which "about the same" is LUFS's own answer
CEIL_DBFS = -1.0
CHOICES = ("louder", "same", "quieter")   # "B is louder than A", "about the same", "B is quieter"


def ls_dir():
    from learn import loudness_step as L

    return L.ls_dir()


# --- the pure parts -----------------------------------------------------------------------------------------------------

def draw(keys, n=N_ITEMS, seed=DRAW_SEED):
    """n of the items' keys, seeded, each with its letters: which of S and the matched preset is A. -> [item]."""
    rng = random.Random(seed)
    pick = sorted(rng.sample(sorted(keys), n))
    firsts = ["S"] * (n // 2) + ["matched"] * (n - n // 2)      # balanced: the matched preset is A on half the items
    rng.shuffle(firsts)
    out = []
    for j, (k, a) in enumerate(zip(pick, firsts), 1):
        out.append({"id": f"i{j}", "n": j, "key": k, "letters": {"A": a, "B": "matched" if a == "S" else "S"}})
    return out


def unblind(item, answer):
    """One answer -> the matched preset against S: +1 louder, 0 about the same, -1 quieter; None if unanswered."""
    c = (answer or {}).get("choice")
    if c not in CHOICES:
        return None
    b_vs_a = {"louder": 1, "same": 0, "quieter": -1}[c]
    return b_vs_a if item["letters"]["B"] == "matched" else -b_vs_a


def sign_test(plus, minus):
    """Two-sided exact sign test on louder against quieter (ties dropped)."""
    n = plus + minus
    if n == 0:
        return 1.0
    k = min(plus, minus)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def counts(v):
    plus, zero, minus = sum(x == 1 for x in v), sum(x == 0 for x in v), sum(x == -1 for x in v)
    return {"matched louder": plus, "about the same": zero, "matched quieter": minus, "sign_test_p": sign_test(plus, minus)}


def ear_read(items, got):
    """The declared read, and beside it (the review) the same test on the items whose played clips sit within NEAR_DB
    of each other by LUFS, and on the rest whether the ear's direction agrees with the clips' measured gap."""
    heard = {it["id"]: unblind(it, got.get(it["id"])) for it in items}
    v = [x for x in heard.values() if x is not None]
    c = counts(v)
    bias = "louder" if c["matched louder"] > c["matched quieter"] else "quieter" if c["matched quieter"] > c["matched louder"] \
        else None
    failed = len(v) < MIN_READ
    shown = not failed and c["sign_test_p"] < ALPHA and bias is not None
    near = [heard[it["id"]] for it in items if heard[it["id"]] is not None and abs(it.get("clip_gap_db", 0.0)) <= NEAR_DB]
    far = [(heard[it["id"]], it["clip_gap_db"]) for it in items
           if heard[it["id"]] is not None and abs(it.get("clip_gap_db", 0.0)) > NEAR_DB]
    return {"answered": len(v), "of": len(items), "page_failed": failed, **c,
            "shown_bias": bias if shown else None, "outcome": "not read" if failed else "user" if shown else "stands",
            "within 1 dB": counts(near),
            "beyond 1 dB": {"n": len(far), "direction agrees": sum(h != 0 and (h > 0) == (g > 0) for h, g in far),
                            "heard the same": sum(h == 0 for h, _ in far)},
            "by_item": heard}


def peak_gain(clips, ceil_dbfs=CEIL_DBFS):
    """The one gain (linear) that puts the item's louder peak at `ceil_dbfs`, never raising: the clips' relative level
    is kept."""
    import numpy as np

    pk = max(float(np.max(np.abs(y))) for y in clips.values())
    return min(1.0, 10 ** (ceil_dbfs / 20) / max(pk, 1e-12))


# --- the page -----------------------------------------------------------------------------------------------------------

CSS = r"""
:root { --bg:#fbfaf7; --card:#ffffff; --fg:#1d1d1f; --mute:#6b6b70; --line:#dcdad3; --on:#2f5d8a; --on-fg:#fff; }
@media (prefers-color-scheme: dark) { :root { --bg:#141416; --card:#1d1d20; --fg:#ececee; --mute:#9a9aa2;
  --line:#34343a; --on:#6f9fd0; --on-fg:#0d1117; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI",
  Roboto, sans-serif; }
main { max-width:760px; margin:0 auto; padding:16px 16px 120px; }
h1 { font-size:1.35rem; margin:.4em 0 .3em; }
.intro { color:var(--mute); }
.item { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px; margin:14px 0; }
.num { color:var(--mute); font-size:.85rem; }
.plays, .choice { display:flex; gap:8px; flex-wrap:wrap; margin:10px 0; }
button { font:inherit; padding:10px 16px; border-radius:10px; border:1px solid var(--line); background:var(--bg);
  color:var(--fg); min-width:56px; cursor:pointer; }
button[aria-pressed="true"] { background:var(--on); color:var(--on-fg); border-color:var(--on); }
.note { width:100%; padding:8px; border-radius:8px; border:1px solid var(--line); background:var(--bg); color:var(--fg); }
.bar { position:fixed; left:0; right:0; bottom:0; background:var(--card); border-top:1px solid var(--line);
  padding:10px 16px; display:flex; justify-content:space-between; align-items:center; }
"""

INTRO = """<h1>Is B louder than A?</h1>
<p class="intro">@@COUNT@@ items of about 5 seconds, looping. A and B are two presets playing <b>the same
performance</b>. They are <b>not</b> level-matched: loudness is the question. Tap A or B (or press A / B, Space stops) to
switch instantly. For each item, say whether B sounds louder than A, about the same, or quieter. A note is optional.
Headphones, please, at one fixed volume for the whole page.</p>
<p class="intro">Your answers save as you go, and I can read them from here when you tell me you are done.</p>"""


def cards(items):
    out = []
    for it in items:
        out.append(
            f'<article class="item" data-id="{it["id"]}"><div class="num">{it["n"]} / {len(items)}</div>'
            '<div class="plays"><button type="button" class="src" data-k="A" aria-pressed="false">A</button>'
            '<button type="button" class="src" data-k="B" aria-pressed="false">B</button>'
            '<button type="button" class="stop" aria-label="Stop">&#9632;</button></div>'
            '<div class="choice">'
            '<button type="button" data-c="louder" aria-pressed="false">B is louder</button>'
            '<button type="button" data-c="same" aria-pressed="false">About the same</button>'
            '<button type="button" data-c="quieter" aria-pressed="false">B is quieter</button></div>'
            '<input class="note" type="text" placeholder="Note (optional)" aria-label="Note"></article>')
    return "".join(out)


JS = r"""
const DATA = JSON.parse(document.getElementById("data").textContent);
const CLIPS = JSON.parse(document.getElementById("clips").textContent);
const STORE = "ls-ear:" + DATA.build;
let ans = {};
try { ans = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (e) { ans = {}; }
function save() { try { localStorage.setItem(STORE, JSON.stringify(ans)); } catch (e) {} }
function paint() {
  document.querySelectorAll(".item").forEach(el => {
    const a = ans[el.dataset.id] || {};
    el.querySelectorAll("[data-c]").forEach(b => b.setAttribute("aria-pressed", String(a.choice === b.dataset.c)));
    const n = el.querySelector(".note"); if (n && document.activeElement !== n) n.value = a.note || "";
  });
  const done = DATA.items.filter(it => (ans[it.id] || {}).choice).length;
  document.getElementById("count").textContent = done + " of " + DATA.items.length + " answered";
}
let ctx = null, cur = null;
const bufs = {};
async function buffer(key) {
  if (bufs[key]) return bufs[key];
  const bin = Uint8Array.from(atob(CLIPS[key]), c => c.charCodeAt(0));
  bufs[key] = await ctx.decodeAudioData(bin.buffer);
  return bufs[key];
}
function stop() {
  if (cur) { cur.srcs.forEach(s => { try { s.stop(); } catch (e) {} }); cur = null; }
  document.querySelectorAll(".src").forEach(b => b.setAttribute("aria-pressed", "false"));
}
async function play(id, k) {
  ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
  if (cur && cur.id === id) {
    const t = ctx.currentTime;
    for (const [kk, g] of Object.entries(cur.gains)) { g.gain.setTargetAtTime(kk === k ? 1 : 0, t, 0.004); }
    cur.k = k;
  } else {
    stop();
    const [ba, bb] = await Promise.all([buffer(id + "-A"), buffer(id + "-B")]);
    const t = ctx.currentTime + 0.05, srcs = [], gains = {};
    for (const [kk, b] of [["A", ba], ["B", bb]]) {
      const s = ctx.createBufferSource(); s.buffer = b; s.loop = true;
      const g = ctx.createGain(); g.gain.value = kk === k ? 1 : 0;
      s.connect(g).connect(ctx.destination); s.start(t); srcs.push(s); gains[kk] = g;
    }
    cur = {id, k, srcs, gains};
  }
  document.querySelectorAll(".item").forEach(el => el.querySelectorAll(".src").forEach(b =>
    b.setAttribute("aria-pressed", String(el.dataset.id === id && b.dataset.k === k))));
}
let focusId = DATA.items.length ? DATA.items[0].id : null;
document.querySelectorAll(".item").forEach(el => {
  const id = el.dataset.id;
  el.addEventListener("pointerdown", () => { focusId = id; });
  el.querySelectorAll(".src").forEach(b => b.addEventListener("click", () => play(id, b.dataset.k)));
  el.querySelector(".stop").addEventListener("click", stop);
  el.querySelectorAll("[data-c]").forEach(b => b.addEventListener("click", () => {
    ans[id] = Object.assign(ans[id] || {}, {choice: b.dataset.c}); save(); paint(); }));
  el.querySelector(".note").addEventListener("input", e => { ans[id] = Object.assign(ans[id] || {}, {note: e.target.value}); save(); });
});
document.addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT") return;
  if (e.key === " ") { e.preventDefault(); stop(); }
  const k = e.key.toUpperCase(); if ((k === "A" || k === "B") && focusId) play(focusId, k);
});
document.getElementById("export").addEventListener("click", () => {
  const t = JSON.stringify({build: DATA.build, answers: ans});
  try { navigator.clipboard.writeText(t); } catch (e) {}
  document.getElementById("out").textContent = t;
});
paint();
"""


def page_html(items, clips, build):
    data = json.dumps({"build": build, "items": [{"id": it["id"], "n": it["n"]} for it in items]})
    body = (f'<main>{INTRO.replace("@@COUNT@@", str(len(items)))}{cards(items)}<pre id="out"></pre></main>'
            '<div class="bar"><span id="count"></span><button type="button" id="export">Export</button></div>'
            f'<script type="application/json" id="data">{data}</script>'
            f'<script type="application/json" id="clips">{json.dumps(clips)}</script>')
    return body


def artifact_page(body, js):
    from learn import c1a_ear as C

    from learn import ear_eat as EE

    return ('<title>Loudness Check</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n<style>'
            + EE.artifact_css(CSS) + "</style>\n" + body + "<script>" + js + C.SYNC + "</script>")   # C1a's sync


def leaks(text, items):
    words = {"pr12", "sw50r", "ac20", "factory", "S's"}
    for it in items:
        words |= {it["key"], it["key"].split("|")[1]}
    return sorted(w for w in words if len(w) > 2 and w in text)


# --- the commands -------------------------------------------------------------------------------------------------------

def cmd_page(_args):
    import numpy as np

    from learn import ear_vreal as E
    from learn import loudness_step as L
    from learn import pipeline_fix as P
    from learn import song_aug as SA

    P.require(PHASE)
    key_path = ls_dir() / "ear" / "key.json"
    if key_path.exists():
        raise SystemExit(f"{key_path} exists: a rebuild hides the listener's stored answers; move it aside first")
    plan = json.loads((ls_dir() / "plan.json").read_text())["items"]
    rep = json.loads((ls_dir() / "report.json").read_text())
    if rep.get("reading") != "closer" or not rep["linearity"]["holds"]:
        raise SystemExit("LS's read didn't pass its rule: no page")
    items = draw([it["key"] for it in plan])
    clips, kept = {}, []
    for it in items:
        z = np.load(ls_dir() / "items" / f"{L.fname(it['key'])}.npz")
        grp = {k: np.asarray(z[c], np.float64) for k, c in it["letters"].items()}
        g = peak_gain(grp)
        for k, y in grp.items():
            clips[f"{it['id']}-{k}"] = E.encode(y * g, ls_dir() / "ear" / "aac-cache")
        by = {it["letters"][k]: grp[k] * g for k in grp}
        lu = {c: SA.lufs(y) for c, y in by.items()}
        pk = {c: 20 * math.log10(max(float(np.max(np.abs(y))), 1e-12)) for c, y in by.items()}
        kept.append({**it, "gain_db": 20 * math.log10(g), "clip_lufs": lu, "clip_peak_dbfs": pk,
                     "clip_gap_db": lu["matched"] - lu["S"], "clip_peak_gap_db": pk["matched"] - pk["S"]})
    build = hashlib.sha256(f"{json.dumps([k['letters'] for k in kept])}{time.time_ns()}".encode()).hexdigest()[:12]
    body = page_html(kept, clips, build)
    bad = leaks(body.split('<script type="application/json" id="clips"')[0], kept)
    if bad:
        raise SystemExit(f"the page names {bad}")
    out = ls_dir() / "ear" / "artifact-1.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(artifact_page(body, JS))
    P.save(key_path, {"phase": PHASE, "build": build, "items": kept, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"LS PAGE: {len(kept)} items -> {out}; build {build}; {out.stat().st_size / 1e6:.1f} MB", flush=True)


def cmd_read(args):
    import pathlib

    from learn import ear_eat as EE
    from learn import pipeline_fix as P

    P.require(PHASE)
    key = json.loads((ls_dir() / "ear" / "key.json").read_text())
    ex = EE.stored_answers(pathlib.Path(args.answers).read_text())
    if ex.get("build") != key["build"]:
        raise SystemExit(f"answers for build {ex.get('build')}, the page's is {key['build']}")
    rep = {"phase": PHASE, "build": key["build"], **ear_read(key["items"], ex["answers"]),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(pathlib.Path(args.out), rep)
    print(json.dumps({k: v for k, v in rep.items() if k != "by_item"}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ls-page").set_defaults(fn=cmd_page)
    q = sub.add_parser("ls-ear-read")
    q.add_argument("out")
    q.add_argument("--answers", required=True)
    q.set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
