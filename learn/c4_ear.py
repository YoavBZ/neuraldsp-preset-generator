"""C4 by ear (`docs/full-controls-plan.md`, "C4 in detail"; ledger `pipeline-fix` `phase_c4`): a blind ranking page of three
presets against the record, on batch 3's 18 trusted units (L1c), which no model trained on and no read chose anything on.
The presets: the adopted model (R-all's all-labels pair, held as C3-cabS), FTm's all-labels pair (the model C3 replaced) and
the class's S. Ranks 1 to 3, ties allowed.

    zsh logs/launch-c4.zsh /path/to/worktree       # the lag pass, the inputs, then the commands below
    .venv/bin/python -m learn.c4_ear c4-draw                        # the items (zero renders)
    $TORCH_PY -m learn.c4_ear c4-answers                            # each preset's answer (zero renders, CPU)
    .venv/bin/python -m learn.c4_ear c4-render --shard 0/3          # the held-half clips (renders)
    .venv/bin/python -m learn.c4_ear c4-page                        # the page (zero renders)
    .venv/bin/python -m learn.c4_ear c4-read OUT --answers F        # the read (zero renders)

The pure parts (the draw, the page order and letters, the tie-aware unblinding, the pairwise shares and the rule, the cards
and the player) are unit-tested; the render and answer commands are not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time

PHASE = "phase_c4"
PAGE_SEED = 20261127                 # the page order's, repeats' and letters'
GAP = 4                              # a repeat sits at least this many items after its first hearing
REPEATS = 2
CANDS = ("adopted", "FTm", "S")      # the adopted model (R-all), the model it replaced (FTm), the factory start
LETTERS = ("A", "B", "C")
PAIRS = (("adopted", "FTm"), ("adopted", "S"), ("FTm", "S"))   # the first decides
MIN_READ = 12                        # first hearings answered for the page to be read (of 18)
ALPHA = 0.05                         # the declared one-sided level, as C1a's
ADOPTED = {"base": "C3r-all", "hold": "C3-cabS"}   # adopted-model.json's
FTM = {"base": "P2b-ftm", "hold": None}            # `K.space`, FTm's own hold
LISTENING = "c4-ear"


def ear_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "c4"


# --- the draw -----------------------------------------------------------------------------------------------------------

def item_of(u):
    """One unit's item: its forced amp, its held half (L1c's), its DI file as the cluster."""
    return {"unit": u["unit"], "key": f"{u['unit']}|{u['amp']}", "amp": u["amp"], "cls": u["cls"], "cluster": u["di"],
            "search": u["search"], "held": u["held_half"], "slug": u["unit"].replace("/", "__").replace("#", "_")}


def page_order(items, seed=PAGE_SEED, gap=GAP, repeats=REPEATS):
    """Every item once, then `repeats` of them again at least `gap` items after their first hearing, with the letters
    rotated. Each first hearing's letters are a seeded permutation of the three presets. -> [{**item, id, n, letters,
    repeat_of}]."""
    rng = random.Random(seed)
    by = {it["key"]: it for it in items}
    twice = rng.sample(sorted(by), repeats)
    seq = sorted(by) + twice
    for _ in range(10000):
        rng.shuffle(seq)
        if all(seq.index(t) + gap <= len(seq) - 1 - seq[::-1].index(t) for t in twice):
            break
    else:
        raise SystemExit(f"{len(by)} items cannot hold repeats {gap} items after their first hearings")
    out, first = [], {}
    for n, k in enumerate(seq, 1):
        if k in first:
            fid, lets = first[k]
            lets = {LETTERS[i]: lets[LETTERS[(i + 1) % 3]] for i in range(3)}     # rotated, so no letter keeps its preset
        else:
            perm = list(CANDS)
            rng.shuffle(perm)
            fid, lets = None, dict(zip(LETTERS, perm))
            first[k] = (f"i{n}", lets)
        out.append({**by[k], "id": f"i{n}", "n": n, "letters": lets, "repeat_of": fid})
    return out


# --- the read -----------------------------------------------------------------------------------------------------------

def unblind(item, ans):
    """One item's answer -> {cand: {rank, close}}, ties allowed; None unless every letter holds a rank of 1 to 3."""
    from learn import ear_vreal as E

    r, c = (ans or {}).get("rank") or {}, (ans or {}).get("close") or {}
    if any(r.get(k) not in (1, 2, 3) for k in LETTERS):
        return None
    return {item["letters"][k]: {"rank": r[k], "close": E.CLOSE_VALUE.get(c.get(k))} for k in LETTERS}


def pref(heard, a, b):
    """a over b: 1 above, 0 below, 0.5 a tie."""
    x, y = heard[a]["rank"], heard[b]["rank"]
    return 1.0 if x < y else 0.0 if x > y else 0.5


def share_row(cards, key="cluster"):
    """C1a's jackknife-t share (ties a half) and its counts, clustered by `key`."""
    from learn import c1a_ear as C

    return C.share_row(cards, key)


def verdict(row, alpha=ALPHA):
    from learn import c1a_ear as C

    return C.verdict(row, alpha)


def outcome(primary_verdict, over_s_verdict, page_failed):
    """The declared rule. Primary, adopted over FTm: "above" or "undecided" keeps the adopted model; "below" (the ear says
    worse where the score says level) goes to the user, the adopted model staying until they decide (PR #422's conflict
    rule, adoption the default). The adopted model below S goes to the user too. -> "not read" | "keep" | "user"."""
    if page_failed:
        return "not read"
    return "user" if "below" in (primary_verdict, over_s_verdict) else "keep"


def ear_read(items, got):
    """The declared read. items: the key's, each with cluster, cls and j0 {cand: held distance}; got: {id: answer}."""
    heard = {it["id"]: unblind(it, got.get(it["id"])) for it in items}
    first = [it for it in items if it["repeat_of"] is None]
    rows, cards_by = {}, {}
    for a, b in PAIRS:
        cards = [{"id": it["id"], "cls": it["cls"], "cluster": it["cluster"], "pref": pref(heard[it["id"]], a, b),
                  "j0": math.log(it["j0"][a] / it["j0"][b])} for it in first if heard[it["id"]]]
        cards_by[f"{a} over {b}"] = cards
        decided = [c for c in cards if c["pref"] != 0.5]
        rows[f"{a} over {b}"] = {**share_row(cards), "by_class": {k: share_row([c for c in cards if c["cls"] == k])
                                                                    for k in ("clean", "crunch")},
                                 "j0_agrees": {"decided": len(decided),
                                               "agree": sum((c["j0"] < 0) == (c["pref"] == 1.0) for c in decided)}}
    read = len(cards_by["adopted over FTm"])
    failed = read < MIN_READ
    reps = []
    for it in items:
        if it["repeat_of"] and heard[it["id"]] and heard[it["repeat_of"]]:
            agree = all(pref(heard[it["repeat_of"]], a, b) == pref(heard[it["id"]], a, b) for a, b in PAIRS)
            reps.append({"id": it["id"], "repeat_of": it["repeat_of"], "agree": agree})
    v = {n: ("not read" if failed else verdict(r)) for n, r in rows.items()}
    return {"read": read, "unanswered": [it["id"] for it in first if not heard[it["id"]]], "page_failed": failed,
            "rows": rows, "verdicts": v, "outcome": outcome(v["adopted over FTm"], v["adopted over S"], failed),
            "repeats": reps, "cards": cards_by}


# --- the page -----------------------------------------------------------------------------------------------------------

INTRO = """<h1>Which preset sounds most like the recording?</h1>
<p class="intro">@@COUNT@@ items of about 4 seconds, looping. <b>Record</b> is the guitar as recorded through a captured amp.
A, B and C are three presets playing <b>the very same performance</b>, so every note lines up and only the tone differs.
Everything loops together and switches instantly at the same moment: tap a button, or press R, A, B, C (or 1-4); Space stops.
All clips are set to the same loudness. Headphones, please.</p>
<p class="intro">For each item, rank A, B and C: 1 is closest to the Record. If two or all three sound the same to you, give
them the same rank. Rating how close each one is, and saying whether you are sure, are optional. Which preset is which is
hidden and shuffled per item, and a couple of items come back later. Answers are saved in this browser as you go; tap
<b>Export</b> any time and send the text.</p>"""


def cards(items):
    """Each item's card: the Record and A, B, C to play; ranks 1 to 3 per letter (ties allowed); closeness, confidence."""
    from learn import ear_vreal as E

    out = []
    for it in items:
        rank = "".join(f'<span class="lab">{k}</span>' + "".join(f'<button type="button" data-l="{k}" data-r="{r}">{r}</button>'
                                                                 for r in (1, 2, 3)) for k in LETTERS)
        close = "".join(f'<span class="lab">{k}</span>' + "".join(
            f'<button type="button" data-l="{k}" data-v="{v}">{t}</button>' for v, t in E.CLOSE) for k in LETTERS)
        out.append(
            f'<article class="item" data-id="{it["id"]}" data-n="{it["n"]}">'
            f'<div class="num">{it["n"]} / {len(items)}</div><h3>Recording {it["n"]}</h3><div class="plays">'
            '<button type="button" class="src" data-k="ref" aria-pressed="false">Record (R)</button>'
            + "".join(f'<button type="button" class="src" data-k="{k}" aria-pressed="false">{k}</button>' for k in LETTERS)
            + '<button type="button" class="stop" aria-label="Stop">&#9632;</button></div><p class="now"></p>'
            '<div class="q">Rank them, 1 closest to the Record (the same rank if you can\'t tell them apart)</div>'
            f'<div class="rank three"><span></span><span class="hd">closest</span><span class="hd">middle</span>'
            f'<span class="hd">furthest</span>{rank}</div>'
            f'<div class="q">How close is each one to the Record? (optional)</div><div class="rank close">{close}</div>'
            '<div class="conf"><span>Confidence (optional):</span><button type="button" data-c="sure">Sure</button>'
            '<button type="button" data-c="unsure">Unsure</button></div>'
            '<input class="note" type="text" placeholder="Note (optional)" aria-label="Note">'
            '<div class="done"></div></article>')
    return "".join(out)


JS_EDITS = (
    ('const STORE = "ear-vreal:" + DATA.build;', 'const STORE = "c4-ear:" + DATA.build;'),
    ('KEYS = ["ref", "A", "B", "C", "D"]', 'KEYS = ["ref", "A", "B", "C"]'),
    ('const NAMES = {ref: "the record\'s guitar", A: "A", B: "B", C: "C", D: "D"};',
     'const NAMES = {ref: "the record\'s guitar", A: "A", B: "B", C: "C"};'),
    ("    Object.keys(r).forEach(o => { if (o !== l && r[o] === v) delete r[o]; });   // a rank is held by one letter\n", ""),
    ('const full = ["A", "B", "C", "D"].every(l => r[l] && cl[l]) && a.conf;', 'const full = ["A", "B", "C"].every(l => r[l]);'),
    ('a: "A", b: "B", c: "C", d: "D", "1": "ref", "2": "A", "3": "B", "4": "C", "5": "D"',
     'a: "A", b: "B", c: "C", "1": "ref", "2": "A", "3": "B", "4": "C"'),
    ('(order.join(">") || "-")', '(order.map(l => l + r[l]).join(" ") || "-")'),          # ties shown plainly, A1 B1 C2
)


def player_js():
    """`ear_vreal`'s player for three letters, ties allowed, closeness and confidence optional."""
    from learn import ear_vreal as E

    js = E.JS
    for old, new in JS_EDITS:
        if old not in js:
            raise SystemExit(f"ear_vreal's player changed: {old[:60]}")
        js = js.replace(old, new)
    js = js.replace('["A", "B", "C", "D"]', '["A", "B", "C"]').replace("ear-vreal", "c4-ear")
    if '"D"' in js or "delete r[o]" in js:
        raise SystemExit("the player still holds a fourth letter or the one-letter-a-rank rule")
    return js


CSS_EXTRA = ".rank.three { grid-template-columns:auto repeat(3, 1fr); }\n.rank.close { grid-template-columns:auto repeat(4, 1fr); }\n"


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
    """C1a's Artifact wrapping (answers kept in the page's store, `answers/<build>`), under C4's title."""
    from learn import c1a_ear as C

    return C.artifact_page(page, css, js).replace("<title>Record A/B Check</title>", "<title>Three Presets Check</title>")


def leaks(text, items):
    """Names the page must not carry: units, keys, DI files and stems, captures, the presets' tags."""
    words = {"P2b", "C3r", "FTm", "R-all", "adopted", "cabS"}
    for it in items:
        words |= {it["unit"], it["key"], str(it["cluster"]), it["slug"], it["unit"].split("/")[-1].split("#")[0]}
        words.add(str(it["cluster"]).rsplit("/", 1)[-1])
    return sorted(w for w in words if len(w) > 2 and w in text)


# --- the commands -------------------------------------------------------------------------------------------------------

def trusted_units():
    from learn import capture_labels as CL

    CL.BATCH = CL.BATCH3
    units, lags = CL.trusted_units()
    return units, lags


def cmd_draw(_args):
    """The 18 items from L1c's trusted units, their lags (the lag pass) -> c4/plan.json, written once."""
    from learn import pipeline_fix as P

    P.require(PHASE)
    p = ear_dir() / "plan.json"
    if p.exists():
        raise SystemExit(f"{p} exists: the items are drawn once")
    units, lags = trusted_units()
    items = [{**item_of(u), "lag": lags[u["unit"]], "prt": u} for u in sorted(units, key=lambda u: u["unit"])]
    if any(it["lag"] is None for it in items):
        raise SystemExit("a unit with no lag: C4 reads only lagged units")
    P.save(p, {"phase": PHASE, "items": items, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"C4 DRAW: {len(items)} items on {len({it['cluster'] for it in items})} DI files")


def cmd_answers(_args):
    """Each item's three presets from its search half's input (D_fix variant 0, `dfix_backed`), on its forced amp: the
    adopted model's and FTm's all-labels pairs (both seeds pooled), each with its own hold, and S. -> c4/answers.json."""
    from learn import direct_stems as DS
    from learn import full_controls_c3 as C3
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    P.require(PHASE)
    plan = json.loads((ear_dir() / "plan.json").read_text())
    adopted = json.loads((P.out_dir() / "adopted-model.json").read_text())
    if adopted["model"]["base"] != ADOPTED["base"] or not adopted["answer_hold"].startswith(ADOPTED["hold"]):
        raise SystemExit("adopted-model.json names another model than C4 was declared on")
    nets = {}
    for c, m in (("adopted", ADOPTED), ("FTm", FTM)):
        loaded = [P.load_run(m["base"], sd, "best") for sd in P.SEEDS]
        if c == "adopted" and [r_["model_sha256"]["best"] for _, r_ in loaded] != [
                adopted["model"]["sha256"][str(sd)]["best"] for sd in P.SEEDS]:
            raise SystemExit("the adopted model's runs differ from adopted-model.json")
        nets[c] = [n_ for n_, _ in loaded]
    holds = {"adopted": C3.hold_for(ADOPTED["hold"]), "FTm": None}
    ms = P.A_menu_S()
    out = {}
    for it in plan["items"]:
        sel, S = ms[it["amp"]][it["cls"]]
        s8, ls = P.dfix_backed(it["unit"])[it["search"]]
        x, cvec = DS.model_input(s8, s8, ls, ls, it["search"], it["amp"], it["cls"], "Dstem")
        out[it["key"]] = {"S": {"select": sel, "settings": LO.sdict(S)}}
        for c in ("adopted", "FTm"):
            r = F.readout([o[0] for o in F.run_nets(nets[c], [x], [cvec])])
            st = F.answer_settings(it["amp"], S, r["a2"], r["sw_p"], r["mics"])
            st = P.hold_outside_space(st, S, it["amp"]) if holds[c] is None else P.hold_outside_space(st, S, it["amp"], holds[c])
            out[it["key"]][c] = {"select": sel, "settings": LO.sdict(st)}
    P.save(ear_dir() / "answers.json", {"phase": PHASE, "models": {"adopted": ADOPTED, "FTm": FTM}, "answers": out,
                                        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"C4 ANSWERS: {len(out)} items x {len(CANDS)} presets")


def cmd_render(args):
    """Each item's three presets, fresh (own process, one priming render), judged on both halves at the unit's lag; the
    held-half window clips -> c4/clips/<slug>.npz, .json."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import score_ear as SE
    from learn import song_bank as B
    from learn import trusted_data as T

    P.require(PHASE)
    plan = json.loads((ear_dir() / "plan.json").read_text())
    ans = json.loads((ear_dir() / "answers.json").read_text())["answers"]
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
        prt, held, lag = it["prt"], it["held"], it["lag"]
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = np.asarray(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64)
        kept, rec, win = {}, {"unit": it["unit"], "key": it["key"], "held": held, "lag": lag, "cands": {}}, None
        for c in CANDS:
            a = ans[it["key"]][c]
            st = LO.tdict(a["settings"])
            y = np.asarray(AM.fresh_render(CB.new_renderer, di32, a["select"], st, st), np.float64)[trim[0]:trim[1]]
            renders += 2
            j = K.judge(ref, y, di, lag)
            mono = np.mean(y, 1) if y.ndim == 2 else y
            s0, s1 = SE.h4_window(held, len(ref), len(mono), lag)
            if win not in (None, (s0, s1)):
                raise SystemExit(f"{it['key']}: the renders' windows differ")
            win = (s0, s1)
            kept[c] = mono[s0 - lag:s1 - lag].astype(np.float32)
            rec["cands"][c] = {"judge": j, "sha": AM.audio_sha(y)}
        s0, s1 = win
        rec["window"] = [s0, s1]
        d.mkdir(parents=True, exist_ok=True)
        np.savez(d / f"{it['slug']}.npz", ref=ref[s0:s1].astype(np.float32), window=np.array([s0, s1]), **kept)
        P.save(d / f"{it['slug']}.json", rec)                # the resume marker, after its clips
        print(f"{it['cls']}: renders so far {renders}", flush=True)
    print(f"C4 RENDER DONE {k}/{n}: {renders} renders", flush=True)


def cmd_page(_args):
    """The page in one part, every clip from the stored renders -> c4/{page/artifact-1.html, key.json}."""
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
                     "j0": {c: rec["cands"][c]["judge"][it["held"]] for c in CANDS}, "window": rec["window"]})
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
    print(f"C4 PAGE: {len(kept)} items -> {out}; build {build}; {out.stat().st_size / 1e6:.1f} MB", flush=True)


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
    rep = {"phase": PHASE, "build": key["build"], **ear_read(key["items"], ex["answers"]),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(pathlib.Path(args.out), rep)
    print(json.dumps({k: rep[k] for k in ("read", "verdicts", "outcome")}, indent=1))


def shard(s):
    a, b = s.split("/")
    return int(a), int(b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("c4-draw").set_defaults(fn=cmd_draw)
    sub.add_parser("c4-answers").set_defaults(fn=cmd_answers)
    r = sub.add_parser("c4-render")
    r.add_argument("--shard", type=shard, default=(0, 1))
    r.set_defaults(fn=cmd_render)
    sub.add_parser("c4-page").set_defaults(fn=cmd_page)
    q = sub.add_parser("c4-read")
    q.add_argument("out")
    q.add_argument("--answers", required=True)
    q.set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
