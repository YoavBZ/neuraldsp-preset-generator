"""C1a by ear (`docs/full-controls-plan.md`, "C1a by ear"; ledger `pipeline-fix` `phase_c1a_ear`): a blind A/B page of each
record's stored label against C1a's best, on N12's never-heard units and a seeded draw of BKS's records. Ranks allow ties.

    .venv/bin/python -m learn.c1a_ear c1a-ear-draw                   # the items (zero renders)
    .venv/bin/python -m learn.c1a_ear c1a-ear-render --shard 0/3     # the label's and C1a's held-half clips (renders)
    .venv/bin/python -m learn.c1a_ear c1a-ear-page                   # the page, one part (zero renders)
    .venv/bin/python -m learn.c1a_ear c1a-ear-read OUT --answers F   # the read (zero renders)

The pure parts (the never-heard pool, the BKS draw, the page order, the tie-aware unblinding, the read, the page's cards and
player) are unit-tested; the render command is tested on a stub renderer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from collections import defaultdict

PHASE = "phase_c1a_ear"
SEED = 20261125                      # the BKS draw's
PAGE_SEED = 20261126                 # the page order's and letters'
BKS_N = 7                            # BKS records, at most one a DI
GAP = 4                              # a repeat sits at least this many items after its first hearing
SETS = ("n12", "bks")
CANDS = ("label", "C1a")
LETTERS = ("A", "B")
MIN_READ = 10                        # first hearings answered for the page to be read (of 14)
ALPHA = 0.05                         # the declared decision rule's one-sided level
NEVER_HEARD = ("cap/1w1lkv30jfn#ac20", "cap/3iqknlf6u0x_a2#sw50r", "cap/9nbhb9zvawu#ac20", "cap/a9j26sllzrq_a2#ac20",
               "cap/piou1nfi5cm_a2#ac20", "cap/rtxifphieu#sw50r", "cap/wji8wcrx9yf#sw50r")   # declared in the plan
LISTENING = "c1a-ear"


def ear_dir():
    from learn import full_controls as F

    return F.c1a_dir() / "ear"


# --- the draw ---------------------------------------------------------------------------------------------------------

def never_heard(units, n12_plan, n12_key, h4b_plan):
    """N12's units never on a page: not N12's cards or spares, not played on N12's page, not H4b's cards. -> [unit]."""
    seen = ({u["unit"] for u in n12_plan["cards"] + n12_plan["spares"]} | {it["unit"] for it in n12_key["items"]}
            | {u["unit"] for u in h4b_plan["cards"]})
    return sorted(u["unit"] for u in units if u["unit"] not in seen)


def bks_draw(recs, n=BKS_N, seed=SEED):
    """`n` of BKS's searched records outside real_out, at most one a DI: `n` DIs seeded, then one record each. -> [record]."""
    by = defaultdict(list)
    for r in sorted((r for r in recs if r["set"] == "bks" and not r["real_out"]), key=lambda r: r["key"]):
        by[r["cluster"]].append(r)
    if len(by) < n:
        raise SystemExit(f"{n} BKS records at most one a DI, the pool has {len(by)} DIs")
    rng = random.Random(seed)
    dis = sorted(rng.sample(sorted(by), n))
    return [rng.choice(by[d]) for d in dis]


# --- the page order ----------------------------------------------------------------------------------------------------

def page_order(items, seed=PAGE_SEED, gap=GAP):
    """Every item once, then one repeat of each set at least `gap` items after its first hearing, the letters swapped there.
    The label sits on A for half the first hearings (seeded). items: [{key, set, ...}]. -> [{**item, id, n, letters, repeat_of}]."""
    rng = random.Random(seed)
    by = {it["key"]: it for it in items}
    twice = [rng.choice(sorted(k for k, it in by.items() if it["set"] == s)) for s in SETS]
    seq = sorted(by) + twice
    for _ in range(10000):
        rng.shuffle(seq)
        if all(seq.index(t) + gap <= len(seq) - 1 - seq[::-1].index(t) for t in twice):
            break
    else:
        raise SystemExit(f"{len(by)} items cannot hold repeats {gap} items after their first hearings")
    flags = [i % 2 == 0 for i in range(len(by))]
    rng.shuffle(flags)
    flags = iter(flags)
    out, first = [], {}
    for n, k in enumerate(seq, 1):
        if k in first:
            fid, lets = first[k]
            lets = {"A": lets["B"], "B": lets["A"]}
        else:
            fid, lets = None, ({"A": "label", "B": "C1a"} if next(flags) else {"A": "C1a", "B": "label"})
            first[k] = (f"i{n}", lets)
        out.append({**by[k], "id": f"i{n}", "n": n, "letters": lets, "repeat_of": fid})
    return out


# --- the read ----------------------------------------------------------------------------------------------------------

def unblind(item, ans):
    """One item's answer -> {cand: {rank, close}}, ties allowed (both may hold rank 1, or 2); closeness optional (None).
    None unless both letters hold a rank of 1 or 2."""
    from learn import ear_vreal as E

    r, c = (ans or {}).get("rank") or {}, (ans or {}).get("close") or {}
    if any(r.get(k) not in (1, 2) for k in LETTERS):
        return None
    return {item["letters"][k]: {"rank": r[k], "close": E.CLOSE_VALUE.get(c.get(k))} for k in LETTERS}


def pref(heard):
    """C1a over the label: 1 above, 0 below, 0.5 a tie."""
    a, b = heard["C1a"]["rank"], heard["label"]["rank"]
    return 1.0 if a < b else 0.0 if a > b else 0.5


def share_row(cards, key="cluster"):
    """The jackknife-t share of C1a over the label (ties a half), its 90% jackknife interval and its counts, clustered by
    `key`. cards: [{cluster, pref, ...}]."""
    from learn import pretrain_set as PS
    from learn import score_ear as SE

    pairs = [(c[key], c["pref"]) for c in cards]
    row = SE.jackknife_t(pairs) if cards else {"share": None, "cards": 0, "p": None}
    return {**row, "interval": SE.interval(pairs, PS.t90), "above": sum(c["pref"] == 1.0 for c in cards),
            "ties": sum(c["pref"] == 0.5 for c in cards), "below": sum(c["pref"] == 0.0 for c in cards)}


def verdict(row, alpha=ALPHA):
    """The declared rule on the primary: "above" if the one-sided p is below `alpha`; "below" if the share is under one half
    and the mirrored one-sided p (1 - p) is below `alpha`; else "undecided"."""
    p = row.get("p")
    if p is None or row.get("share") is None:
        return "undecided"
    if p < alpha:
        return "above"
    if row["share"] < 0.5 and 1 - p < alpha:
        return "below"
    return "undecided"


def song_of(cluster):
    """A BKS DI's song: its session folder ("set5/BKS_Bulldozer_Full")."""
    return "/".join(str(cluster).split("/")[:2])


def ear_read(items, got):
    """The declared read. items: the key's, each with cluster, set, cls and j0 {cand: held distance}; got: {id: answer}."""
    heard = {it["id"]: unblind(it, got.get(it["id"])) for it in items}
    first = [it for it in items if it["repeat_of"] is None]
    cards = [{"id": it["id"], "set": it["set"], "cls": it["cls"], "cluster": f"{it['set']}:{it['cluster']}",
              "song": f"{it['set']}:{song_of(it['cluster'])}",
              "pref": pref(heard[it["id"]]), "j0": math.log(it["j0"]["C1a"] / it["j0"]["label"]),
              "close_gap": (heard[it["id"]]["C1a"]["close"] - heard[it["id"]]["label"]["close"]
                            if None not in (heard[it["id"]]["C1a"]["close"], heard[it["id"]]["label"]["close"]) else None)}
             for it in first if heard[it["id"]]]
    reps = []
    for it in items:
        if it["repeat_of"] and heard[it["id"]] and heard[it["repeat_of"]]:
            a, b = pref(heard[it["repeat_of"]]), pref(heard[it["id"]])
            reps.append({"id": it["id"], "repeat_of": it["repeat_of"], "first": a, "again": b, "agree": a == b})
    decided = [c for c in cards if c["pref"] != 0.5]
    gaps = [c["close_gap"] for c in cards if c["close_gap"] is not None]
    primary = share_row(cards)
    return {"read": len(cards), "unanswered": [it["id"] for it in first if not heard[it["id"]]],
            "page_failed": len(cards) < MIN_READ, "primary": primary,
            "verdict": "not read" if len(cards) < MIN_READ else verdict(primary),
            "by_set": {s: share_row([c for c in cards if c["set"] == s]) for s in SETS},
            "bks_by_song": share_row([c for c in cards if c["set"] == "bks"], key="song"),
            "by_class": {k: share_row([c for c in cards if c["cls"] == k]) for k in ("clean", "crunch")},
            "repeats": reps,
            "j0_agrees": {"decided": len(decided), "agree": sum((c["j0"] < 0) == (c["pref"] == 1.0) for c in decided),
                          "j0_closer_c1a": sum(c["j0"] < 0 for c in cards)},
            "close_gap_mean": sum(gaps) / len(gaps) if gaps else None, "close_gap_n": len(gaps), "cards": cards}


# --- the page ----------------------------------------------------------------------------------------------------------

INTRO = """<h1>Which preset sounds more like the recording?</h1>
<p class="intro">@@COUNT@@ items of about 4 seconds, looping. <b>Record</b> is the guitar as it was recorded through a real amp,
or a close capture of one. A and B are two presets playing <b>the very same performance</b>, so every note lines up and only the
tone differs. Everything loops together and switches instantly at the same moment: tap a button, or press R, A, B (or 1-3); Space
stops. All clips are set to the same loudness. Headphones, please.</p>
<p class="intro">For each item, rank A and B: 1 is closer to the Record. If you can't tell them apart, give both the same rank.
Rating how close each one is, and saying whether you are sure, are optional. Which preset is which is hidden and shuffled per item,
and a couple of items come back later. Answers are saved in this browser as you go; tap <b>Export</b> any time and send the text.</p>"""


def cards(items):
    """Each item's card: the Record and A, B to play; ranks 1 and 2 per letter (a tie allowed); closeness and confidence."""
    from learn import ear_vreal as E

    out = []
    for it in items:
        rank = "".join(f'<span class="lab">{k}</span>' + "".join(f'<button type="button" data-l="{k}" data-r="{r}">{r}</button>'
                                                                 for r in (1, 2)) for k in LETTERS)
        close = "".join(f'<span class="lab">{k}</span>' + "".join(
            f'<button type="button" data-l="{k}" data-v="{v}">{t}</button>' for v, t in E.CLOSE) for k in LETTERS)
        out.append(
            f'<article class="item" data-id="{it["id"]}" data-n="{it["n"]}">'
            f'<div class="num">{it["n"]} / {len(items)}</div><h3>Recording {it["n"]}</h3><div class="plays">'
            '<button type="button" class="src" data-k="ref" aria-pressed="false">Record (R)</button>'
            + "".join(f'<button type="button" class="src" data-k="{k}" aria-pressed="false">{k}</button>' for k in LETTERS)
            + '<button type="button" class="stop" aria-label="Stop">&#9632;</button></div><p class="now"></p>'
            '<div class="q">Rank them, 1 closer to the Record (the same rank if you can\'t tell them apart)</div>'
            f'<div class="rank two"><span></span><span class="hd">closer</span><span class="hd">further</span>{rank}</div>'
            f'<div class="q">How close is each one to the Record? (optional)</div><div class="rank close">{close}</div>'
            '<div class="conf"><span>Confidence (optional):</span><button type="button" data-c="sure">Sure</button>'
            '<button type="button" data-c="unsure">Unsure</button></div>'
            '<input class="note" type="text" placeholder="Note (optional)" aria-label="Note">'
            '<div class="done"></div></article>')
    return "".join(out)


JS_EDITS = (
    ('const STORE = "ear-vreal:" + DATA.build;', 'const STORE = "c1a-ear:" + DATA.build;'),
    ('KEYS = ["ref", "A", "B", "C", "D"]', 'KEYS = ["ref", "A", "B"]'),
    ('const NAMES = {ref: "the record\'s guitar", A: "A", B: "B", C: "C", D: "D"};',
     'const NAMES = {ref: "the record\'s guitar", A: "A", B: "B"};'),
    ("    Object.keys(r).forEach(o => { if (o !== l && r[o] === v) delete r[o]; });   // a rank is held by one letter\n", ""),
    ('const full = ["A", "B", "C", "D"].every(l => r[l] && cl[l]) && a.conf;', 'const full = ["A", "B"].every(l => r[l]);'),
    ('a: "A", b: "B", c: "C", d: "D", "1": "ref", "2": "A", "3": "B", "4": "C", "5": "D"', 'a: "A", b: "B", "1": "ref", "2": "A", "3": "B"'),
    ('(order.join(">") || "-")', '(order.length === 2 && r.A === r.B ? "A=B" : order.join(">") || "-")'),     # a tie, plainly
)


def player_js():
    """`ear_vreal`'s player for two letters, ties allowed (a rank may be held by both), closeness and confidence optional."""
    from learn import ear_vreal as E

    js = E.JS
    for old, new in JS_EDITS:
        if old not in js:
            raise SystemExit(f"ear_vreal's player changed: {old[:60]}")
        js = js.replace(old, new)
    js = js.replace('["A", "B", "C", "D"]', '["A", "B"]').replace("ear-vreal", "c1a-ear")
    if '"C"' in js or "delete r[o]" in js:
        raise SystemExit("the player still holds a third letter or the one-letter-a-rank rule")
    return js


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
    if (snap.exists && !Object.keys(ans).length) { ans = snap.data().answers || {}; saveHere(); paint(); }
    dbDoc = d;
    if (Object.keys(ans).length) push();
  } catch (e) {}
})();
"""
CSS_EXTRA = ".rank.two { grid-template-columns:auto repeat(2, 1fr); }\n.rank.close { grid-template-columns:auto repeat(4, 1fr); }\n"


def page_html(chunk, clips, build):
    """The local page. -> (html, css, js)."""
    from learn import ear_vreal as E

    js, css = player_js(), E.CSS + CSS_EXTRA
    a, b = E.PAGE.index("<h1>"), E.PAGE.index("@@CARDS@@")
    data = json.dumps({"build": build, "items": [{"id": it["id"], "n": it["n"]} for it in chunk]})
    page = (E.PAGE[:a] + INTRO + "\n" + E.PAGE[b:]).replace("@@COUNT@@", str(len(chunk))).replace("@@CARDS@@", cards(chunk)) \
        .replace("@@CSS@@", css).replace("@@DATA@@", data).replace("@@CLIPS@@", json.dumps(clips)).replace("@@JS@@", js)
    return page, css, js


def artifact_page(page, css, js):
    """The page for the Artifact viewer: no document wrapper, its themes, answers kept for reading back (`answers/<build>`)."""
    from learn import ear_eat as EE

    body = page[page.index("<body>") + len("<body>"):page.index("</body>")]
    if EE.ARTIFACT_INTRO[0] not in body:
        raise SystemExit("the intro's save line has changed")
    body = body.replace(*EE.ARTIFACT_INTRO).replace('<button type="button" id="save">Save file</button>', "")
    hook = 'document.getElementById("save").addEventListener("click", () => {'
    if hook not in js:
        raise SystemExit("the player's save hook has changed")
    body = body.replace("<script>" + js + "</script>", "<script>" + js.replace(hook, "if (false) " + hook) + SYNC + "</script>")
    return ('<title>Record A/B Check</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n<style>'
            + EE.artifact_css(css) + "</style>\n" + body)


def leaks(text, items):
    """Names the page must not carry: units, keys, bands, DI stems, the candidates' tags."""
    words = {"P2b", *CANDS[1:]}
    for it in items:
        words |= {it["unit"], it["key"], str(it["cluster"]), it.get("slug", "")}
        words.add(str(it["cluster"]).rsplit("/", 1)[-1])
    return sorted(w for w in words if len(w) > 2 and w in text)


# --- the commands -------------------------------------------------------------------------------------------------------

def slug_of(key):
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def cmd_draw(_args):
    """The items, once: N12's never-heard units and BKS's seeded draw, each with a C1a label -> c1a/ear/plan.json."""
    from learn import full_controls as F
    from learn import pipeline_fix as P
    from learn import score_ear as SE

    P.require(F.PHASE)
    P.require(PHASE)
    path = ear_dir() / "plan.json"
    if path.exists():
        raise SystemExit(f"{path} exists: the items are drawn once")
    recs = json.loads((F.c1a_dir() / "records.json").read_text())["records"]

    def labelled(r):
        root, sub = F.OUT_DIRS[r["set"]]
        p = P.out_dir() / root / sub / f"{F.fname(r['key'])}.json"
        return p.exists() and json.loads(p.read_text()).get("label") is not None

    units, _, _ = SE.wide_units()
    never = set(never_heard(units, json.loads((SE.wide_dir() / "plan.json").read_text()),
                            json.loads((SE.wide_dir() / "key.json").read_text()),
                            json.loads((SE.h4b_dir() / "plan.json").read_text())))
    if never != set(NEVER_HEARD):
        raise SystemExit(f"the never-heard units {sorted(never)} are not the plan's {sorted(NEVER_HEARD)}")
    n12 = [r for r in recs if r["set"] == "n12" and r["unit"] in never]
    if len(n12) != len(never) or not all(labelled(r) for r in n12):
        raise SystemExit("a never-heard N12 unit has no C1a record or label")
    bks = bks_draw([r for r in recs if r["set"] == "bks" and labelled(r)])
    if {r["cls"] for r in bks} != {"clean", "crunch"}:
        raise SystemExit("the BKS draw does not span clean and crunch")
    items = [{k: r[k] for k in ("set", "key", "unit", "amp", "cls", "cluster", "source", "prt")} | {"slug": slug_of(r["key"])}
             for r in n12 + bks]
    P.save(path, {"phase": PHASE, "seed": SEED, "page_seed": PAGE_SEED, "items": items,
                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print("C1A-EAR DRAW", {s: sum(it["set"] == s for it in items) for s in SETS}, "renders", 2 * 2 * len(items), flush=True)


def cmd_render(args):
    """Each item's label and C1a best, fresh (own process, one priming render), judged on the held half at the record's lag and
    held to the stored held judge within `full_controls.START_TOL`; the held-window clips -> c1a/ear/clips/<slug>.npz, .json."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import full_controls as F
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import score_ear as SE
    from learn import song_bank as B
    from learn import trusted_data as T

    P.require(PHASE)
    plan = json.loads((ear_dir() / "plan.json").read_text())
    k, n = args.shard
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    d = ear_dir() / "clips"
    for it in plan["items"][k::n]:
        if (d / f"{it['slug']}.json").exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        src = json.loads(open(it["source"]).read())
        root, sub = F.OUT_DIRS[it["set"]]
        c1 = json.loads((P.out_dir() / root / sub / f"{F.fname(it['key'])}.json").read_text())
        if (src["unit"], src["amp"], src["held"], src["lag"]) != (c1["unit"], c1["amp"], c1["held"], c1["lag"]) \
                or src["unit"] != it["unit"] or c1.get("label") is None:
            raise SystemExit(f"{it['key']}: the source and C1a records do not fit")
        held, lag, sel, prt = src["held"], src["lag"], src["select"], it["prt"]
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = np.asarray(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64)
        kept, rec, win = {}, {"unit": it["unit"], "key": it["key"], "held": held, "lag": lag, "cands": {}}, None
        for c, settings, stored, stored_sha in (
                ("label", src["best"]["settings"], src["best"]["judge"][held], src["best"].get("render_sha256")),
                ("C1a", c1["label"], c1["fresh"]["best"]["judge"][held], c1["fresh"]["best"].get("render_sha256"))):
            st = LO.tdict(settings)
            y = np.asarray(AM.fresh_render(CB.new_renderer, di32, sel, st, st), np.float64)[trim[0]:trim[1]]
            renders += 2
            j = K.judge(ref, y, di, lag)
            if not F.within(j[held], stored):
                raise SystemExit(f"{it['key']}: {c}'s fresh held judge {j[held]} is not the stored {stored} within {F.START_TOL}")
            mono = np.mean(y, 1) if y.ndim == 2 else y
            s0, s1 = SE.h4_window(held, len(ref), len(mono), lag)
            if win not in (None, (s0, s1)):
                raise SystemExit(f"{it['key']}: the two renders' windows differ")
            win = (s0, s1)
            kept[c] = mono[s0 - lag:s1 - lag].astype(np.float32)
            sha = AM.audio_sha(y)
            rec["cands"][c] = {"judge": j[held], "stored": stored, "sha": sha, "stored_sha": stored_sha,
                               "bit_identical": sha == stored_sha}
        s0, s1 = win
        rec["window"] = [s0, s1]
        d.mkdir(parents=True, exist_ok=True)
        np.savez(d / f"{it['slug']}.npz", ref=ref[s0:s1].astype(np.float32), window=np.array([s0, s1]), **kept)
        P.save(d / f"{it['slug']}.json", rec)                # the resume marker, after its clips
        print(f"{it['set']} {it['cls']}: renders so far {renders}", flush=True)
    print(f"C1A-EAR RENDER DONE {k}/{n}: {renders} renders", flush=True)


def cmd_page(_args):
    """The page in one part, every clip from the stored renders -> c1a/ear/{page/artifact-1.html, key.json}."""
    import numpy as np

    from learn import ear_vreal as E
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    P.require(PHASE)
    key_path = ear_dir() / "key.json"
    if key_path.exists():
        raise SystemExit(f"{key_path} exists: a rebuild hides the listener's stored answers; move it aside first")
    plan = json.loads((ear_dir() / "plan.json").read_text())
    missing = [it["key"] for it in plan["items"] if not ((ear_dir() / "clips" / f"{it['slug']}.npz").exists()
                                                         and (ear_dir() / "clips" / f"{it['slug']}.json").exists())]
    if missing:
        raise SystemExit(f"no clips for {missing}: every item's renders come first, and no partial page is built")
    items = page_order(plan["items"])
    clips, kept = {}, []
    for it in items:
        z = np.load(ear_dir() / "clips" / f"{it['slug']}.npz")
        rec = json.loads((ear_dir() / "clips" / f"{it['slug']}.json").read_text())
        group = {"ref": np.asarray(z["ref"], np.float64), **{k: np.asarray(z[c], np.float64) for k, c in it["letters"].items()}}
        if len({len(v) for v in group.values()}) != 1:
            raise SystemExit(f"{it['key']}: clip lengths differ")
        lev, info = E.level_group(group)
        for k, y in lev.items():
            clips[f"{it['id']}-{k}"] = E.encode(y, ear_dir() / "aac-cache")
        kept.append({**{k: v for k, v in it.items() if k != "prt"}, "levels": info,
                     "j0": {c: rec["cands"][c]["judge"] for c in CANDS}, "window": rec["window"]})
    build = hashlib.sha256(f"{json.dumps([k['letters'] for k in kept])}{time.time_ns()}".encode()).hexdigest()[:12]
    page, css, js = page_html(kept, clips, build)
    bad = leaks(page.split('<script id="clips"')[0], plan["items"])
    if bad:
        raise SystemExit(f"the page names {bad}")
    local = PS.HOME / "listening" / LISTENING / "index.html"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(page)
    out = ear_dir() / "page" / "artifact-1.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(artifact_page(page, css, js))
    P.save(key_path, {"phase": PHASE, "build": build, "items": kept, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"C1A-EAR PAGE: {len(kept)} items -> {out}; build {build}; {out.stat().st_size / 1e6:.1f} MB", flush=True)


def cmd_read(args):
    """The declared read of the stored answers (`answers/<build>` or the Export text) -> OUT.json."""
    import pathlib

    from learn import ear_eat as EE
    from learn import pipeline_fix as P

    P.require(PHASE)
    key = json.loads((ear_dir() / "key.json").read_text())
    ex = EE.stored_answers(pathlib.Path(args.answers).read_text())
    if ex.get("build") != key["build"]:
        raise SystemExit(f"answers for build {ex.get('build')}, the page's is {key['build']}")
    rep = {"phase": PHASE, "build": key["build"], **ear_read(key["items"], ex["answers"])}
    pathlib.Path(args.out).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("read", "page_failed", "verdict", "primary", "by_set", "bks_by_song", "repeats",
                                          "j0_agrees")}, indent=1))


def shard(s):
    a, b = s.split("/")
    return int(a), int(b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("c1a-ear-draw").set_defaults(fn=cmd_draw)
    s = sub.add_parser("c1a-ear-render")
    s.add_argument("--shard", type=shard, default=(0, 1))
    s.set_defaults(fn=cmd_render)
    sub.add_parser("c1a-ear-page").set_defaults(fn=cmd_page)
    s = sub.add_parser("c1a-ear-read")
    s.add_argument("out")
    s.add_argument("--answers", required=True)
    s.set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
