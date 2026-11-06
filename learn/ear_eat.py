"""The EfficientAT study by ear (`docs/efficientat-plan.md`, task S9): the readers on BKS's and GOAT's held halves, one listener.

The user set the score aside and asked to hear them. So no score picks a part, and each candidate plays the answer it was scored
with, on the same direction: a fold-held reader's settings for the search half, heard on the other half, the search's own direction.
`label` is the search's best setting on that half, fitted on the true DI: a ceiling, not a product. The parts are a seeded draw
inside amp and class, one GOAT and one BKS part in each, at most one per take, clusters spread. It adopts nothing.

    $MAIN -m learn.ear_eat plan                 # the parts, zero renders
    $MAIN -m learn.ear_eat render --shard k/n   # each candidate's clip, its render hash held to the stored one
    $MAIN -m learn.ear_eat page                 # -> PF/eat/ear/page/artifact.html, and listening/ear-eat/index.html
    $MAIN -m learn.ear_eat score --answers FILE
"""
from __future__ import annotations

import argparse
import collections
import hashlib
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

from learn import bakeoff_render as BR       # noqa: E402
from learn import capture_ear as C           # noqa: E402
from learn import ear_vreal as E             # noqa: E402
from learn import eat_render as ER           # noqa: E402

P_SEARCH = "search"                          # `pipeline_fix.SEARCH_DIR`

CANDS = ("S", "FTm", "M-pcs", "EW-mix", "label")
LETTERS = ("A", "B", "C", "D", "E")
TAGS = {"S": "S", "FTm": BR.FTM, "M-pcs": "M-pcs", "EW-mix": "EW-mix"}
AMPS = ("pr12", "sw50r", "ac20")
CLASSES = ("clean", "crunch")
SETS = ("goat", "bks")
PLAN_SEED, PAGE_SEED = 20261201, 20261202
ROWS = (("EW-mix", "FTm"), ("EW-mix", "S"), ("FTm", "S"), ("M-pcs", "FTm"), ("EW-mix", "M-pcs"), ("label", "S"), ("label", "EW-mix"))
PRIMARY = ROWS[0]
SIM_PAGES, SIM_SEED = 400, 20261203
JUDGE_TOL = 1e-3


# --- pure functions (unit-tested) ------------------------------------------------------------------------------------

def take_of(prt):
    """A part's take: no two parts of a page share one."""
    return prt["di"]


def cluster_of(which, prt):
    """A part's cluster for the read: its DI on BKS, its player on GOAT."""
    return prt["di"] if which == "bks" else prt["band"]


def pick(rows, seed=PLAN_SEED, amps=AMPS, classes=CLASSES, sets=SETS):
    """One part of each set in each amp and class, no take twice, clusters spread, by a seeded draw that looks at no score.
    rows: [{cell, set, take, cluster, ...}]. -> the chosen rows."""
    rng = random.Random(seed)
    takes, used, out = set(), collections.Counter(), []
    for cell in ((a, c) for a in amps for c in classes):
        for st in sets:
            pool = [r for r in rows if r["cell"] == cell and r["set"] == st and r["take"] not in takes]
            rng.shuffle(pool)
            if pool:
                r = min(pool, key=lambda q: used[q["cluster"]])
                takes.add(r["take"])
                used[r["cluster"]] += 1
                out.append(r)
    return out


def unblind(item, ans):
    """One item's answer -> {cand: {rank, close}}, or None unless every rank and rating is there."""
    r, c = ans.get("rank") or {}, ans.get("close") or {}
    if sorted(r.get(k) or 0 for k in LETTERS) != list(range(1, len(LETTERS) + 1)) or any(c.get(k) not in E.CLOSE_VALUE for k in LETTERS):
        return None
    return {item["letters"][k]: {"rank": r[k], "close": E.CLOSE_VALUE[c[k]]} for k in LETTERS}


def share_rows(items, heard, scope_out=()):
    """The declared rows on first hearings: for each pair, (cluster, 1 if a ranks above b), and the closeness gap."""
    first = [it for it in items if it["repeat_of"] is None and heard.get(it["id"]) and it["id"] not in set(scope_out)]
    out = {}
    for a, b in ROWS:
        pts = [(it["cluster"], float(heard[it["id"]][a]["rank"] < heard[it["id"]][b]["rank"])) for it in first]
        gaps = [(it["cluster"], float(heard[it["id"]][a]["close"] - heard[it["id"]][b]["close"])) for it in first]
        out[f"{a} over {b}"] = {"parts": len(pts), "share": C.share_row(pts) if pts else None, "close_gap": C.gap_row(gaps) if gaps else None}
    return out


def table(items, heard):
    """Each candidate's mean rank, mean closeness and firsts on first hearings."""
    first = [it for it in items if it["repeat_of"] is None and heard.get(it["id"])]
    return {c: {"rank": sum(heard[it["id"]][c]["rank"] for it in first) / max(len(first), 1),
                "close": sum(heard[it["id"]][c]["close"] for it in first) / max(len(first), 1),
                "firsts": sum(heard[it["id"]][c]["rank"] == 1 for it in first)} for c in CANDS}


def simulate(clusters, shares=(0.5, 0.6, 0.75, 0.9), pages=SIM_PAGES, seed=SIM_SEED, n=2000):
    """How often a true share clears one half on this page, by `capture_ear.boot_share` on these cards' clusters."""
    rng = random.Random(seed)
    out = {}
    for p in shares:
        clear = 0
        for j in range(pages):
            rows = [(c, float(rng.random() < p)) for c in clusters]
            lo, _ = C.boot_share(rows, n=n, seed=seed + j)
            clear += lo > 0.5
        out[str(p)] = clear / pages
    return out


# --- paths -----------------------------------------------------------------------------------------------------------

def data_dir():
    return ER.score_root().parent / "ear"


def plan_path():
    return data_dir() / "plan.json"


def clip_path(slug):
    return data_dir() / "renders" / slug / "clips.npz"


def slug_of(key):
    return hashlib.sha256(key.encode()).hexdigest()[:12]


# --- the commands ----------------------------------------------------------------------------------------------------

def search_record(which, key):
    """The search's stored record of a key: its direction and its best setting."""
    return json.loads((BR.stored_dir(which) / P_SEARCH / f"{key.replace('/', '__')}.json").read_text())


def cmd_plan(_args):
    BR.root = ER.score_root
    ER.linked()
    rows, units = [], {}
    for which, prt in BR.read_units():
        units[(which, prt["unit"])] = prt
        for key in BR.keys_of(which, prt):
            amp = key.rsplit("|", 1)[1]
            p = BR.stored_dir(which) / P_SEARCH / f"{key.replace('/', '__')}.json"
            if prt["cls"] in CLASSES and p.exists():
                r = json.loads(p.read_text())
                if r.get("held") in ("A", "B") and r.get("best"):
                    rows.append({"cell": (amp, prt["cls"]), "set": which, "take": take_of(prt), "cluster": cluster_of(which, prt), "key": key,
                                 "search": r["search"], "held": r["held"]})
    out = []
    for r in pick(rows):
        unit = r["key"].rsplit("|", 1)[0]
        prt = units[(r["set"], unit)]
        out.append({"which": r["set"], "key": r["key"], "unit": unit, "amp": r["cell"][0], "cls": r["cell"][1], "band": prt["band"],
                    "cluster": r["cluster"], "search": r["search"], "held": r["held"], "slug": slug_of(r["key"])})
    data_dir().mkdir(parents=True, exist_ok=True)
    sim = simulate([u["cluster"] for u in out])
    plan_path().write_text(json.dumps({"seed": PLAN_SEED, "units": out, "clears_one_half": sim}, indent=1))
    for u in out:
        print(u["which"], u["amp"], u["cls"], u["cluster"][-28:], flush=True)
    print("clusters", len({u["cluster"] for u in out}), "cards", len(out), "clears one half", sim, flush=True)


def cmd_render(args):
    """Every candidate on a part's direction: its stored answer rendered again, held to its stored hash, the held window kept."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B

    BR.root = ER.score_root
    ER.linked()
    units = json.loads(plan_path().read_text())["units"]
    parts = {(w, q["unit"]): q for w, q in BR.read_units()}
    answers = {w: {c: BR.stored_answers(w, t) for c, t in TAGS.items()} for w in BR.SETS}
    k, n = (int(x) for x in args.shard.split("/"))
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    for u in units[k::n]:
        out = clip_path(u["slug"])
        if out.exists():
            continue
        if PS.free_gb() < BR.FLOOR_GB:
            raise SystemExit(f"DISK GUARD: free disk below {BR.FLOOR_GB} GB")
        which, prt, key, search = u["which"], parts[(u["which"], u["unit"])], u["key"], u["search"]
        lag = prt["lag"] if which == "goat" else json.loads(
            (P.out_dir() / P.REAL_DIR / "lags" / f"{prt['unit'].replace('/', '__')}.json").read_text())["lag"]
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        ref = np.asarray(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64)
        a, b = (int(x * E.SR) for x in K.R.HALVES[u["held"]])
        clips, shas = {}, {}
        search_rec = search_record(which, key)
        if (search_rec["search"], search_rec["held"]) != (search, u["held"]):
            raise SystemExit(f"{key}: the plan's direction is not the search's")
        for c in CANDS:
            if c == "label":
                st, sel = LO.tdict(search_rec["best"]["settings"]), search_rec["select"]
            else:
                got = answers[which][c][key]
                half = search if search in got else BR.ANY
                st, sel = LO.tdict(got[half]["settings"]), got[half]["select"]
            y = np.asarray(AM.fresh_render(CB.new_renderer, di32, sel, st, st), np.float64)[trim[0]:trim[1]]
            renders += 2
            sha = AM.audio_sha(y)
            if c == "label":                            # the search's stored judge, as `capture_ear.check_fresh` holds a label
                di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
                fresh = K.judge(ref, y, di, lag)[u["held"]]
                if abs(math.log(fresh / search_rec["best"]["judge"][u["held"]])) > JUDGE_TOL:
                    raise SystemExit(f"label {key}: its fresh judge is off the search's")
            else:
                rec = json.loads(BR.judge_path(which, TAGS[c], key).read_text())
                if sha != rec["render_sha256"][half]:
                    raise SystemExit(f"{c} {key} {half}: the render differs from the one judged")
            mono = y.mean(axis=1) if y.ndim == 2 else y
            s0, s1 = E.window(a, b, len(ref), len(mono), lag)
            clips[c] = mono[s0 - lag:s1 - lag].astype(np.float32)
            shas[c] = sha
        out.parent.mkdir(parents=True, exist_ok=True)
        np.savez(out, ref=ref[s0:s1].astype(np.float32), **{c.replace("-", "_"): v for c, v in clips.items()})
        (out.parent / "rec.json").write_text(json.dumps({"key": key, "lag": lag, "window": [s0, s1], "render_sha256": shas}, indent=1))
        print(f"{which} {u['amp']} {u['cls']}: renders so far {renders}", flush=True)
    print(f"EAR-EAT RENDER DONE {k}/{n}: {renders} renders", flush=True)


def player_js():
    js = E.JS
    for old, new in (('KEYS = ["ref", "A", "B", "C", "D"]', 'KEYS = ["ref", "A", "B", "C", "D", "E"]'),
                     ('A: "A", B: "B", C: "C", D: "D"}', 'A: "A", B: "B", C: "C", D: "D", E: "E"}'),
                     ('["A", "B", "C", "D"]', '["A", "B", "C", "D", "E"]'),
                     ('a: "A", b: "B", c: "C", d: "D", "1": "ref", "2": "A", "3": "B", "4": "C", "5": "D"',
                      'a: "A", b: "B", c: "C", d: "D", e: "E", "1": "ref", "2": "A", "3": "B", "4": "C", "5": "D", "6": "E"')):
        if old not in js:
            raise SystemExit(f"ear_vreal's player changed: {old}")
        js = js.replace(old, new)
    extra = """
items.forEach(it => { const b = it.querySelector(".scope"), id = it.dataset.id;
  b.setAttribute("aria-pressed", String(!!(ans[id] || {}).scope));
  b.addEventListener("click", () => { const a = ans[id] = ans[id] || {}; a.scope = !a.scope;
    b.setAttribute("aria-pressed", String(a.scope)); save(); paint(); }); });
"""
    full = '.every(l => r[l] && cl[l]) && a.conf;'
    if full not in js or not js.rstrip().endswith("paint();"):
        raise SystemExit("ear_vreal's player changed")
    js = js.replace(full, '.every(l => r[l] && cl[l]) && a.conf || !!a.scope;')
    return js.replace("ear-vreal", "ear-eat").rstrip()[:-len("paint();")] + extra + "paint();\n"


def cards(items):
    rows = "".join(f'<span class="hd">{t}</span>' for t in ("closest", "", "", "", "furthest"))
    out = []
    for it in items:
        rank = "".join(f'<span class="lab">{k}</span>' + "".join(f'<button type="button" data-l="{k}" data-r="{r}">{r}</button>'
                                                                 for r in range(1, len(LETTERS) + 1)) for k in LETTERS)
        close = "".join(f'<span class="lab">{k}</span>' + "".join(
            f'<button type="button" data-l="{k}" data-v="{v}">{t}</button>' for v, t in E.CLOSE) for k in LETTERS)
        out.append(
            f'<article class="item" data-id="{it["id"]}" data-n="{it["n"]}">'
            f'<div class="num">{it["n"]} / {len(items)}</div><h3>Recording {it["n"]}</h3><div class="plays">'
            '<button type="button" class="src" data-k="ref" aria-pressed="false">Record (R)</button>'
            + "".join(f'<button type="button" class="src" data-k="{k}" aria-pressed="false">{k}</button>' for k in LETTERS)
            + '<button type="button" class="stop" aria-label="Stop">&#9632;</button></div><p class="now"></p>'
            f'<div class="q">Rank them, 1 closest to the Record</div><div class="rank five"><span></span>{rows}{rank}</div>'
            f'<div class="q">How close is each one to the Record?</div><div class="rank close">{close}</div>'
            '<div class="conf"><span>Confidence:</span><button type="button" data-c="sure">Sure</button>'
            '<button type="button" data-c="unsure">Unsure</button>'
            '<button type="button" class="scope" aria-pressed="false">Too distorted, out of scope</button></div>'
            f'<input class="note" type="text" placeholder="Note (optional)" aria-label="Note">'
            f'<div class="done"></div></article>')
    return "".join(out)


INTRO = """<h1>Which preset sounds most like the recording?</h1>
<p class="intro">@@COUNT@@ items of about 4 seconds, looping. <b>Record</b> is the guitar as it was recorded through a real amp.
A to E are five presets playing <b>the very same performance</b>, so every note lines up and only the tone differs. Everything loops
together and switches instantly at the same moment: tap a button, or press R, then A to E (or 1-6); Space stops. All clips are set to
the same loudness. Headphones, please.</p>
<p class="intro">For each item, rank the five by how close their tone is to the Record, then rate how close each one is: two presets
can get the same rating if you cannot tell them apart. Say whether you are sure. If an item is too distorted to be in scope, tap that
button instead. Which preset is which is hidden and shuffled per item, and a few items come back later. Answers are saved in this browser as you go; tap <b>Export</b> any time and send the text.</p>"""


SYNC = r"""
let dbDoc = null, syncTimer = null, syncBusy = false, syncAgain = false;
function push() {
  if (!dbDoc) return;
  if (syncBusy) { syncAgain = true; return; }
  syncBusy = true;
  dbDoc.set({build: DATA.build, answers: ans, at: Date.now()}).catch(() => {}).finally(() => {
    syncBusy = false; if (syncAgain) { syncAgain = false; push(); } });
}
const saveHere = save;
save = function () { saveHere(); if (dbDoc) { clearTimeout(syncTimer); syncTimer = setTimeout(push, 700); } };
(async () => {
  try {
    if (!window.claude) return;
    const db = await window.claude.use("db");
    if (!db) return;
    const d = db.doc("answers/" + DATA.build), snap = await d.get();
    if (snap.exists && !Object.keys(ans).length) {
      ans = snap.data().answers || {}; saveHere(); paint();
      items.forEach(it => it.querySelector(".scope").setAttribute("aria-pressed", String(!!(ans[it.dataset.id] || {}).scope)));
    }
    dbDoc = d;
    if (Object.keys(ans).length) push();
  } catch (e) {}
})();
"""
ARTIFACT_INTRO = ("Answers are saved in this browser as you go; tap <b>Export</b> any time and send the text.",
                  "Your answers save as you go, and I can read them from here when you tell me you are done.")


def artifact_css(css):
    """The page's colours in the viewer's three themes, and its gutter on a phone."""
    light = css[css.index(":root {"):css.index("@media (prefers-color-scheme: dark)")]
    start = css.index("@media (prefers-color-scheme: dark) { :root {") + len("@media (prefers-color-scheme: dark) { :root {")
    dark = css[start:css.index("} }", start)].strip()
    themed = (light + "@media (prefers-color-scheme: dark) { :root:not([data-theme=\"light\"]) { " + dark + " color-scheme:dark; } }\n"
              + ":root[data-theme=\"dark\"] { " + dark + " color-scheme:dark; }\n")
    rest = css[css.index("} }", start) + 3:]
    return themed + rest.replace("main { max-width:760px; margin:0 auto; padding:16px 16px 120px; }",
                                 "main { max-width:760px; margin:0 auto; padding-block:16px 120px; "
                                 "padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); }")


def artifact_page(page, css, js):
    """The same page for the Artifact viewer: no document wrapper, its themes, answers kept for reading back, no file save."""
    body = page[page.index("<body>") + len("<body>"):page.index("</body>")]
    body = body.replace(*ARTIFACT_INTRO).replace('<button type="button" id="save">Save file</button>', "")
    body = body.replace("<script>" + js + "</script>", "<script>" + js.replace(
        'document.getElementById("save").addEventListener("click", () => {', 'if (false) document.getElementById("save").addEventListener("click", () => {')
        + SYNC + "</script>")
    return ('<title>Record Tone Check</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n<style>'
            + artifact_css(css) + "</style>\n" + body)


def cmd_page(_args):
    import numpy as np

    from learn import pretrain_set as PS

    key_path = data_dir() / "key.json"
    if key_path.exists():
        raise SystemExit(f"{key_path} exists: a rebuild hides the listener's stored answers; move it aside first")
    units = json.loads(plan_path().read_text())["units"]
    C.CANDS, C.LETTERS = CANDS, LETTERS
    items = C.draw(units, PAGE_SEED, repeats=2, gap=4)
    cache = data_dir() / "aac-cache"
    clips, kept = {}, []
    for it in items:
        z = np.load(clip_path(it["slug"]))
        have = {c: z[c.replace("-", "_")] for c in CANDS}
        group = {"ref": np.asarray(z["ref"], np.float64), **{k: np.asarray(have[c], np.float64) for k, c in it["letters"].items()}}
        if len({len(v) for v in group.values()}) != 1:
            raise SystemExit(f"{it['slug']}: clip lengths differ")
        lev, info = E.level_group(group)
        for k, y in lev.items():
            clips[f"{it['id']}-{k}"] = E.encode(y, cache)
        kept.append({**it, "levels": info})
    build = hashlib.sha256((json.dumps([k["letters"] for k in kept]) + secrets.token_hex(8)).encode()).hexdigest()[:12]
    body = cards(kept)
    data = json.dumps({"build": build, "items": [{"id": it["id"], "n": it["n"]} for it in kept]})
    a, b = E.PAGE.index("<h1>"), E.PAGE.index("@@CARDS@@")
    css = E.CSS + ".rank.five { grid-template-columns:auto repeat(5, 1fr); }\n.rank.close { grid-template-columns:auto repeat(4, 1fr); }\n.conf .scope { flex:1 1 180px; }\n"
    page = (E.PAGE[:a] + INTRO + "\n" + E.PAGE[b:]).replace("@@COUNT@@", str(len(kept))).replace("@@CARDS@@", body) \
        .replace("@@CSS@@", css).replace("@@DATA@@", data).replace("@@CLIPS@@", json.dumps(clips)).replace("@@JS@@", player_js())
    leaks = [w for w in (*CANDS, *{u["unit"] for u in units}, *{u["band"] for u in units}) if len(w) > 2 and w != "label" and w in body + data]
    if leaks:
        raise SystemExit(f"the page names {leaks}")
    key_path.write_text(json.dumps({"page": "ear-eat", "build": build, "items": kept, "time": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
    local = PS.HOME / "listening" / "ear-eat" / "index.html"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(page)
    out = data_dir() / "page" / "artifact.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(artifact_page(page, css, player_js()))
    print(f"EAR-EAT PAGE DONE: {len(kept)} items -> {out}; build {build}; {out.stat().st_size / 1e6:.1f} MB")


def cmd_score(args):
    key = json.loads((data_dir() / "key.json").read_text())
    last = [ln for ln in pathlib.Path(args.answers).read_text().splitlines() if ln.startswith("{")][-1]
    ex = json.loads(last)
    if ex.get("build") != key["build"]:
        raise SystemExit(f"{args.answers}: build {ex.get('build')}, this page's is {key['build']}")
    got = ex["answers"]
    heard = {it["id"]: unblind(it, got.get(it["id"]) or {}) for it in key["items"]}
    out_of_scope = [it["id"] for it in key["items"] if (got.get(it["id"]) or {}).get("scope")]
    unsure = [it["id"] for it in key["items"] if (got.get(it["id"]) or {}).get("conf") == "unsure"]
    rep = {"answered": sum(v is not None for v in heard.values()), "items": len(key["items"]), "out_of_scope": out_of_scope, "unsure": unsure,
           "by_candidate": table(key["items"], heard), "rows": share_rows(key["items"], heard, out_of_scope),
           "rows_unsure_out": share_rows(key["items"], heard, [*out_of_scope, *unsure]),
           "repeats": [{"same_top": min(heard[it["id"]], key=lambda c: heard[it["id"]][c]["rank"]) ==
                        min(heard[it["repeat_of"]], key=lambda c: heard[it["repeat_of"]][c]["rank"])}
                       for it in key["items"] if it["repeat_of"] and heard.get(it["id"]) and heard.get(it["repeat_of"])],
           "per_item": [{k: it[k] for k in ("amp", "cls", "band", "which", "repeat_of", "letters")} | {"heard": heard[it["id"]],
                        "conf": (got.get(it["id"]) or {}).get("conf"), "note": (got.get(it["id"]) or {}).get("note")} for it in key["items"]]}
    (data_dir() / "score.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "per_item"}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan").set_defaults(fn=cmd_plan)
    r = sub.add_parser("render")
    r.add_argument("--shard", default="0/1")
    r.set_defaults(fn=cmd_render)
    sub.add_parser("page").set_defaults(fn=cmd_page)
    s = sub.add_parser("score")
    s.add_argument("--answers", required=True)
    s.set_defaults(fn=cmd_score)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
