"""L1a's ear check of the labels (`docs/pipeline-fix-plan.md`, ledger `phase_l1a`): on a capture of a real amp, is J0's
search label heard closer than S, and closer than another capture's label?

Blind. 12 parts, 2 per amp and class, each with S, the label and a placebo (the label of another capture of the same
amp and class from another creator), through the unit's measure DI, the capture's own render as the Record. Layout as
L0's page (`learn/ear_vreal.py`).

    $MAIN -m learn.capture_ear plan                 # letters and order
    $MAIN -m learn.capture_ear render --shard k/n   # 72 renders, 3 processes
    $MAIN -m learn.capture_ear page                 # -> ~/ndsp-presets/listening/capture-labels/index.html
    $MAIN -m learn.capture_ear score --answers FILE
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
import re
import secrets
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from learn import capture_labels as L        # noqa: E402
from learn import ear_vreal as E             # noqa: E402

CANDS = ("S", "label", "placebo")
LETTERS = ("A", "B", "C")
REPEATS, REPEAT_GAP = 2, 4
PAGE_SEED, BOOT_SEED, BOOT_N = 20261106, 20261107, 20000
JUDGE_TOL = 1e-3                     # |ln ratio| of a label's fresh judge to its in-process one
CLOSE_VALUE = E.CLOSE_VALUE
CELLS = ("amp", "cls")


# --- pure functions (unit-tested) ------------------------------------------------------------------------------------

def balanced(rng, rows=12):
    """`rows` permutations of the candidates, each candidate on each letter equally often (Latin squares)."""
    out = []
    for _ in range(rows // len(LETTERS)):
        base = rng.sample(list(CANDS), len(CANDS))
        out += [tuple(base[i:] + base[:i]) for i in range(len(CANDS))]
    rng.shuffle(out)
    return out


def draw(units, seed=PAGE_SEED, repeats=REPEATS, gap=REPEAT_GAP):
    """The page's order: every unit once with letters balanced over those first hearings, `repeats` of them again at
    least `gap` items later, every candidate on another letter there. units: [{unit, ...}].
    -> [{**unit, id, n, letters: {letter: cand}, repeat_of}]."""
    rng = random.Random(seed)
    by = {u["unit"]: u for u in units}
    twice = rng.sample(sorted(by), repeats)
    seq = sorted(by) + twice
    while True:
        rng.shuffle(seq)
        if all(seq.index(t) + gap <= len(seq) - 1 - seq[::-1].index(t) for t in twice):
            break
    perms = iter(balanced(rng, len(by)))
    items, first = [], {}
    for n, u in enumerate(seq, 1):
        if u in first:
            order = tuple(first[u][1][1:] + first[u][1][:1])       # a cyclic move: every candidate changes letter
        else:
            order = next(perms)
        items.append({**by[u], "id": f"i{n}", "n": n, "letters": dict(zip(LETTERS, order)),
                      "repeat_of": first[u][0] if u in first else None})
        first.setdefault(u, (f"i{n}", list(order)))
    return items


def unblind(item, ans):
    """One item's answer -> {cand: {rank, close}}, or None unless all three ranks and ratings are there."""
    r, c = ans.get("rank") or {}, ans.get("close") or {}
    if sorted(r.get(k) or 0 for k in LETTERS) != [1, 2, 3] or any(c.get(k) not in CLOSE_VALUE for k in LETTERS):
        return None
    return {item["letters"][k]: {"rank": r[k], "close": CLOSE_VALUE[c[k]]} for k in LETTERS}


def boot_share(rows, n=BOOT_N, seed=BOOT_SEED):
    """90% interval of the pooled mean over creators resampled with replacement. rows: [(creator, x)]."""
    rng = random.Random(seed)
    by = {}
    for k, x in rows:
        by.setdefault(k, []).append(x)
    groups = list(by.values())
    d = []
    for _ in range(n):
        pick = rng.choices(groups, k=len(groups))
        tot = sum(sum(g) for g in pick)
        d.append(tot / sum(len(g) for g in pick))
    d.sort()
    return d[int(0.05 * n)], d[int(0.95 * n) - 1]


def share_row(rows):
    """[(creator, 1 if a above b else 0)] -> the share, its interval and which side of one half it reads."""
    lo, hi = boot_share(rows)
    return {"share": sum(x for _, x in rows) / len(rows), "lo90": lo, "hi90": hi, "parts": len(rows),
            "reads": "clear above" if lo > 0.5 else "clear below" if hi < 0.5 else "reaching one half"}


def gap_row(rows):
    lo, hi = boot_share(rows)
    return {"mean": sum(x for _, x in rows) / len(rows), "lo90": lo, "hi90": hi, "parts": len(rows)}


def pair_rows(first, heard, a, b, dist):
    """Row of candidate `a` over `b` on the first hearings: rank share (pairwise from the forced rank), closeness gap,
    the score's gap ln(d_b / d_a)."""
    cr = [(it["creator"], it) for it in first]
    return {"rank": share_row([(c, float(heard[it["id"]][a]["rank"] < heard[it["id"]][b]["rank"])) for c, it in cr]),
            "close": gap_row([(c, heard[it["id"]][a]["close"] - heard[it["id"]][b]["close"]) for c, it in cr]),
            "score": gap_row([(c, math.log(dist(it, b) / dist(it, a))) for c, it in cr])}


def report(items, heard, unsure=()):
    """items: the key's, with `judge` {cand: held-half distance}; heard: {id: `unblind`'s}. First hearings make the rows."""
    first = [it for it in items if it["repeat_of"] is None and heard.get(it["id"])]
    dist = lambda it, c: it["judge"][c]
    rows = {"parts": len(first), "primary": pair_rows(first, heard, "label", "S", dist),
            "label_vs_placebo": pair_rows(first, heard, "label", "placebo", dist),
            "placebo_vs_S": pair_rows(first, heard, "placebo", "S", dist)}
    rows["by"] = {}
    for key in CELLS:
        for v in sorted({it[key] for it in first}):
            sub = [it for it in first if it[key] == v]
            rows["by"][f"{key}:{v}"] = {
                "parts": len(sub),
                "label_above_S": sum(heard[it["id"]]["label"]["rank"] < heard[it["id"]]["S"]["rank"] for it in sub),
                "close_gap": sum(heard[it["id"]]["label"]["close"] - heard[it["id"]]["S"]["close"] for it in sub) / len(sub)}
    rows["leave_one_cell_out"] = {}
    for cell in sorted({(it["amp"], it["cls"]) for it in first}):
        sub = [it for it in first if (it["amp"], it["cls"]) != cell]
        if sub:
            rows["leave_one_cell_out"]["/".join(cell)] = share_row(
                [(it["creator"], float(heard[it["id"]]["label"]["rank"] < heard[it["id"]]["S"]["rank"])) for it in sub])
    sure = [it for it in first if it["id"] not in set(unsure)]
    if sure and len(sure) < len(first):
        rows["unsure_out"] = pair_rows(sure, heard, "label", "S", dist)["rank"]
    gaps = [(it["creator"], heard[it["id"]]["label"]["close"] - heard[it["id"]]["S"]["close"],
             math.log(dist(it, "S") / dist(it, "label"))) for it in first]
    rng = random.Random(BOOT_SEED)
    by = {}
    for c, x, y in gaps:
        by.setdefault(c, []).append((x, y))
    groups, boots = list(by.values()), []
    for _ in range(2000):
        pool = [p for g in rng.choices(groups, k=len(groups)) for p in g]
        r = E.spearman([p[0] for p in pool], [p[1] for p in pool])
        if r is not None:
            boots.append(r)
    boots.sort()
    rows["ear_vs_score"] = {"spearman": E.spearman([g[1] for g in gaps], [g[2] for g in gaps]),
                            "lo90": boots[int(0.05 * len(boots))] if boots else None,
                            "hi90": boots[int(0.95 * len(boots)) - 1] if boots else None}
    rows["repeats"] = []
    for it in items:
        if it["repeat_of"] and heard.get(it["id"]) and heard.get(it["repeat_of"]):
            a, b = heard[it["repeat_of"]], heard[it["id"]]
            rows["repeats"].append({"unit": it["unit"], "same_order": all(a[c]["rank"] == b[c]["rank"] for c in CANDS),
                                    "same_top": min(a, key=lambda c: a[c]["rank"]) == min(b, key=lambda c: b[c]["rank"])})
    whole = len(first) == sum(it["repeat_of"] is None for it in items)    # a partial answer file decides nothing
    rows["branch"] = rows["primary"]["rank"]["reads"] if whole else None
    return rows


def page_js():
    """L0's player with three letters."""
    js = E.JS
    for old, new in (('KEYS = ["ref", "A", "B", "C", "D"]', 'KEYS = ["ref", "A", "B", "C"]'),
                     ('A: "A", B: "B", C: "C", D: "D"}', 'A: "A", B: "B", C: "C"}'),
                     ('["A", "B", "C", "D"]', '["A", "B", "C"]'),
                     ('a: "A", b: "B", c: "C", d: "D", "1": "ref", "2": "A", "3": "B", "4": "C", "5": "D"',
                      'a: "A", b: "B", c: "C", "1": "ref", "2": "A", "3": "B", "4": "C"')):
        if old not in js:
            raise SystemExit(f"ear_vreal's player changed: {old}")
        js = js.replace(old, new)
    return js.replace("ear-vreal", "capture-labels")


def page_leaks(kept, body, data):
    """Whole words on the page that would give a candidate, a unit or a creator away (`aria-label` is not one)."""
    return [w for w in (*CANDS, *{it["unit"] for it in kept}, *{it["creator"] for it in kept})
            if len(w) > 2 and re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", body + data)]


def check_fresh(c, sha, judge, rec):
    """A fresh render against the search's record: S's hash must equal the lag pass's, the label's held-half judge must
    sit within JUDGE_TOL of its in-process value. c: the candidate; judge: the fresh {half: distance}."""
    if c == "S" and sha != rec["s_render_sha256"]:
        raise SystemExit(f"{rec['unit']}: S's fresh render is not the lag pass's")
    if c == "label" and abs(math.log(judge[rec["held"]] / rec["best"]["judge"][rec["held"]])) > JUDGE_TOL:
        raise SystemExit(f"{rec['unit']}: the label's fresh judge is off its in-process value")


def cards(items):
    out = []
    for it in items:
        rank = "".join(f'<span class="lab">{k}</span>' + "".join(
            f'<button type="button" data-l="{k}" data-r="{r}">{t}</button>'
            for r, t in ((1, "1st"), (2, "2nd"), (3, "3rd"))) for k in LETTERS)
        close = "".join(f'<span class="lab">{k}</span>' + "".join(
            f'<button type="button" data-l="{k}" data-v="{v}">{t}</button>' for v, t in E.CLOSE) for k in LETTERS)
        out.append(
            f'<article class="item" data-id="{it["id"]}" data-n="{it["n"]}">'
            f'<div class="num">{it["n"]} / {len(items)}</div><h3>Recording {it["n"]}</h3><div class="plays">'
            '<button type="button" class="src" data-k="ref" aria-pressed="false">Record (R)</button>'
            + "".join(f'<button type="button" class="src" data-k="{k}" aria-pressed="false">{k}</button>' for k in LETTERS)
            + '<button type="button" class="stop" aria-label="Stop">&#9632;</button></div><p class="now"></p>'
            '<div class="rank three"><span></span><span class="hd">closest</span><span class="hd"></span>'
            f'<span class="hd">furthest</span>{rank}</div>'
            f'<div class="q">How close is each one to the Record?</div><div class="rank close">{close}</div>'
            '<div class="conf"><span>Confidence:</span><button type="button" data-c="sure">Sure</button>'
            '<button type="button" data-c="unsure">Unsure</button></div>'
            f'<input class="note" type="text" placeholder="Note (optional)" aria-label="Note">'
            f'<div class="done"></div></article>')
    return "".join(out)


INTRO = """<h1>Which preset sounds most like the recording?</h1>
<p class="intro">@@COUNT@@ items of about 4 seconds, looping. <b>Record</b> is a guitar through a captured real amp. A, B and C
are three presets playing <b>the very same performance</b>, so every note lines up and only the tone differs. Everything
loops together and switches instantly at the same moment: tap a button, or press R, A, B, C (or 1-4); Space stops. All
clips are set to the same loudness. Headphones, please.</p>
<p class="intro">For each item, rank A, B and C by how close their tone is to the Record (1st = closest), then rate how
close each one is: two presets can get the same rating if you cannot tell them apart. Say whether you are sure. Which
preset is which is hidden and shuffled per item, and a few items may come back later. Answers are saved in this browser
as you go; tap <b>Export</b> any time and send the text.</p>"""


# --- the commands ----------------------------------------------------------------------------------------------------

def data_dir():
    return L.root() / "ear-check"


def page_dir():
    from learn import pretrain_set as PS

    return PS.HOME / "listening" / "capture-labels"


def donor(it, recs):
    """The part's placebo: its first placebo unit that gave a label. recs: {unit: search record}."""
    for u in it["placebos"]:
        if (recs.get(u) or {}).get("label") is not None:
            return u
    raise SystemExit(f"{it['unit']}: no placebo gave a label")


def cmd_plan(_args):
    from learn import pipeline_fix as P

    P.require(L.PHASE)
    if json.loads((L.root() / "stage-check.json").read_text()).get("stop") is not False:
        raise SystemExit("the stage check stopped: the label page is held")
    picked = json.loads((L.root() / "items.json").read_text())["items"]
    by = {u["unit"]: u for u in L.units_of()}
    recs = L.search_records()
    units = []
    for it in picked:
        if (recs.get(it["unit"]) or {}).get("label") is None:
            raise SystemExit(f"{it['unit']}: the item gave no label")
        u = by[it["unit"]]
        units.append({"unit": it["unit"], "placebo": donor(it, recs), "amp": u["amp"], "cls": u["cls"],
                      "creator": u["creator"], "held": u["held_half"], "search": u["search"]})
    P.save(data_dir() / "plan.json", {"phase": L.PHASE, "items": draw(units), "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"CAPTURE-EAR PLAN DONE: {len(units)} parts")


def cmd_render(args):
    """S, the label and the placebo through the unit's measure DI, each fresh in its own process. S's hash must equal the
    lag pass's; the label's judge must match its in-process value within JUDGE_TOL; the held window, aligned, is kept."""
    import numpy as np

    from learn import arm_a_levers as AL
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import rescore as R
    from learn import song_bank as B
    from learn import trusted_data as T

    P.require(L.PHASE)
    k, n = (int(x) for x in args.shard.split("/"))
    items = [it for it in json.loads((data_dir() / "plan.json").read_text())["items"] if it["repeat_of"] is None]
    by = {u["unit"]: u for u in L.units_of()}
    recs = L.search_records()
    ms = AL.menu_S()
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    for it in [it for j, it in enumerate(sorted(items, key=lambda i: i["unit"])) if j % n == k]:
        out = data_dir() / "renders" / it["unit"].replace("/", "__")
        if (out / "rec.json").exists():
            continue
        prt, rec = by[it["unit"]], recs[it["unit"]]
        sel, S = ms[prt["amp"]][prt["cls"]]
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
        ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        lag = rec["lag"]
        a, b = (int(x * E.SR) for x in R.HALVES[rec["held"]])
        settings = {"S": LO.sdict(S), "label": rec["label"], "placebo": recs[it["placebo"]]["label"]}
        keep = {"unit": it["unit"], "lag": lag, "judge": {}, "sha": {}}
        clips = {}
        for c in CANDS:
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            st = LO.tdict(settings[c])
            y = np.asarray(AM.fresh_render(CB.new_renderer, di32, sel, st, st), np.float64)[trim[0]:trim[1]]
            renders += 2
            j = K.judge(ref, y, di, lag)
            check_fresh(c, AM.audio_sha(y), j, rec)
            mono = y.mean(axis=1) if y.ndim == 2 else y
            s0, s1 = E.window(a, b, len(ref), len(mono), lag)
            clips[c] = mono[s0 - lag:s1 - lag].astype(np.float32)
            keep["judge"][c], keep["sha"][c] = j[rec["held"]], AM.audio_sha(y)
        keep["window"] = [s0, s1]
        out.mkdir(parents=True, exist_ok=True)
        np.savez(out / "clips.npz", **clips)
        P.save(out / "rec.json", keep)
        print(f"{it['unit']}: renders so far {renders}", flush=True)
    print(f"CAPTURE-EAR RENDER DONE {k}/{n}: {renders} renders")


def cmd_page(_args):
    import numpy as np

    from learn import pipeline_fix as P

    P.require(L.PHASE)
    key_path = data_dir() / "key.json"
    if key_path.exists():
        raise SystemExit(f"{key_path} exists: a rebuild hides the listener's stored answers; move it aside first")
    plan = json.loads((data_dir() / "plan.json").read_text())
    by = {u["unit"]: u for u in L.units_of()}
    cache, od = data_dir() / "aac-cache", page_dir()
    od.mkdir(parents=True, exist_ok=True)
    clips, kept = {}, []
    for it in plan["items"]:
        d = data_dir() / "renders" / it["unit"].replace("/", "__")
        rec = json.loads((d / "rec.json").read_text())
        s0, s1 = rec["window"]
        z = np.load(d / "clips.npz")
        prt = by[it["unit"]]
        ref = np.asarray(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64)[s0:s1]
        group = {"ref": ref, **{k: np.asarray(z[c], np.float64) for k, c in it["letters"].items()}}
        if len({len(v) for v in group.values()}) != 1:
            raise SystemExit(f"{it['unit']}: clip lengths differ")
        lev, info = E.level_group(group)
        for k, y in lev.items():
            clips[f"{it['id']}-{k}"] = E.encode(y, cache)
        kept.append({**it, "judge": rec["judge"], "sha": rec["sha"], "levels": info, "window": rec["window"]})
    salt = secrets.token_hex(8)
    build = hashlib.sha256((json.dumps([k["letters"] for k in kept]) + salt).encode()).hexdigest()[:12]
    body = cards(kept)
    data = json.dumps({"build": build, "items": [{"id": it["id"], "n": it["n"]} for it in kept]})
    a, b = E.PAGE.index("<h1>"), E.PAGE.index("@@CARDS@@")
    page = (E.PAGE[:a] + INTRO + "\n" + E.PAGE[b:]).replace("@@COUNT@@", str(len(kept))).replace("@@CARDS@@", body) \
        .replace("@@CSS@@", E.CSS + ".rank.three { grid-template-columns:auto repeat(3, 1fr); }") \
        .replace("@@DATA@@", data).replace("@@CLIPS@@", json.dumps(clips)).replace("@@JS@@", page_js())
    leaks = page_leaks(kept, body, data)
    if leaks:
        raise SystemExit(f"the page names {leaks}")
    P.save(key_path, {"page": "capture-labels", "build": build, "phase": L.PHASE, "items": kept,
                      "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    (od / "index.html").write_text(page)
    print(f"CAPTURE-EAR PAGE DONE: {len(kept)} items -> {od / 'index.html'}; build {build}")


def cmd_score(args):
    from learn import pipeline_fix as P

    P.require(L.PHASE)
    key = json.loads((data_dir() / "key.json").read_text())
    last = [ln for ln in pathlib.Path(args.answers).read_text().splitlines() if ln.startswith("{")][-1]
    ex = json.loads(last)
    if ex.get("build") != key["build"]:
        raise SystemExit(f"{args.answers}: build {ex.get('build')}, this page's is {key['build']}")
    heard = {it["id"]: unblind(it, ex["answers"].get(it["id"]) or {}) for it in key["items"]}
    unsure = [it["id"] for it in key["items"] if (ex["answers"].get(it["id"]) or {}).get("conf") == "unsure"]
    rep = report(key["items"], heard, unsure)
    rep.update(build=key["build"], answered=sum(v is not None for v in heard.values()), items=len(key["items"]),
               unsure=unsure, per_item=[{k: it[k] for k in ("unit", "placebo", "amp", "cls", "creator", "repeat_of", "judge")}
                                        | {"heard": heard[it["id"]], "note": (ex["answers"].get(it["id"]) or {}).get("note")}
                                        for it in key["items"]])
    P.save(L.root() / "ear-check.json", rep)
    print(json.dumps({k: v for k, v in rep.items() if k != "per_item"}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    sub.add_parser("page")
    r = sub.add_parser("render")
    r.add_argument("--shard", default="0/1")
    s = sub.add_parser("score")
    s.add_argument("--answers", required=True)
    args = ap.parse_args(argv)
    {"plan": cmd_plan, "render": cmd_render, "page": cmd_page, "score": cmd_score}[args.cmd](args)


if __name__ == "__main__":
    main()
