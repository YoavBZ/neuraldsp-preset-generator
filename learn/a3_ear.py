"""A3 by ear (`docs/full-controls-plan.md`, "A3 in detail"; ledger `pipeline-fix` `phase_a3`): A2's declared product step's
ear check. On items where A1's stock-DI pick (frozen, on R-all's answers) and R-all's own amp head choose different amps, a
blind page plays R-all's preset on each of the three amps beside the record, ranked 1 to 3 (ties allowed). Read: the pick's
amp over the head's (primary) and over always-sw50r.

    zsh logs/launch-a3.zsh /path/to/worktree       # the commands below
    .venv/bin/python -m learn.a3_ear a3-draw                        # the items (zero renders)
    .venv/bin/python -m learn.a3_ear a3-render --shard 0/3          # the held-half clips (renders)
    .venv/bin/python -m learn.a3_ear a3-page                        # the page (zero renders)
    .venv/bin/python -m learn.a3_ear a3-read OUT --answers F        # the read (zero renders)

The presets are A2's stored answers (`a2/answers.json`), so no model runs. The pure parts (the draw, the roles, the read
and the rule) are unit-tested; C4's page order, unblinding, cards and player are reused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time

from learn import c4_ear as C4

PHASE = "phase_a3"
DRAW_SEED = 20261129                 # the items' draw
PAGE_SEED = 20261130                 # the page order's, repeats' and letters'
AMPS = ("pr12", "sw50r", "ac20")     # the three letters: R-all's preset on each amp
SETS = ("cap1", "panel")             # A2's deciding sets
N_ITEMS = 18                         # first hearings: every panel DI, then cap1 creators by the seeded draw
MIN_READ = 12
ROLES = (("pick", "head"), ("pick", "sw50r"), ("head", "sw50r"))   # the first decides
LISTENING = "a3-ear"


def ear_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "a3"


# --- the draw -----------------------------------------------------------------------------------------------------------

def candidates(units, picks, heads):
    """Every direction of A2's deciding units where the pick and the head choose different amps (both present, the unit
    lagged). units: A2's; picks / heads: {unit: {search half: amp}}. -> {cluster: [candidate]}."""
    out = {}
    for u in units:
        if u["set"] not in SETS or u["lag"] is None:
            continue
        for sh, h in (("A", "B"), ("B", "A")):
            p, w = (picks.get(u["unit"]) or {}).get(sh), (heads.get(u["unit"]) or {}).get(sh)
            if p in AMPS and w in AMPS and p != w:
                out.setdefault(u["cluster"], []).append(
                    {"set": u["set"], "unit": u["unit"], "cluster": u["cluster"], "cls": u["cls"], "lag": u["lag"],
                     "search": sh, "held": h, "pick": p, "head": w})
    return out


def draw(cands, n=N_ITEMS, seed=DRAW_SEED):
    """One item per cluster: every panel DI first, then cap1 creators in a seeded order, up to n; within a cluster, one
    direction at random. -> [item], sorted by key."""
    rng = random.Random(seed)
    panel = sorted(c for c, v in cands.items() if v[0]["set"] == "panel")
    cap = sorted(c for c, v in cands.items() if v[0]["set"] != "panel")
    rng.shuffle(cap)
    items = []
    for c in (panel + cap)[:n]:
        it = rng.choice(sorted(cands[c], key=lambda d: (d["unit"], d["search"])))
        key = f"{it['unit']}|{it['search']}"
        items.append({**it, "key": key, "slug": hashlib.sha256(key.encode()).hexdigest()[:16]})
    return sorted(items, key=lambda it: it["key"])


# --- the read -----------------------------------------------------------------------------------------------------------

def role_amp(item, role):
    return "sw50r" if role == "sw50r" else item[role]


def outcome(primary, over_sw50r, page_failed):
    """The declared rule. Primary, the pick over the head: "above" or "undecided" keeps the pick as the declared amp choice
    (the score's A2 reading stands, PR #422's rule: adoption the default); "below" on the primary or on the pick over
    always-sw50r goes to the user. -> "not read" | "keep" | "user"."""
    if page_failed:
        return "not read"
    return "user" if "below" in (primary, over_sw50r) else "keep"


def ear_read(items, got):
    """The declared read. items: the key's, each with cluster, cls, pick, head, letters and j0 {amp: held distance};
    got: {id: answer}. A pair is read on the first hearings where its two amps differ."""
    import math

    heard = {it["id"]: C4.unblind(it, got.get(it["id"])) for it in items}
    first = [it for it in items if it["repeat_of"] is None]
    rows, verdicts, cards_by = {}, {}, {}
    for a, b in ROLES:
        cards = []
        for it in first:
            x, y = role_amp(it, a), role_amp(it, b)
            if heard[it["id"]] and x != y:
                cards.append({"id": it["id"], "cls": it["cls"], "set": it["set"], "cluster": it["cluster"],
                              "pref": C4.pref(heard[it["id"]], x, y), "j0": math.log(it["j0"][x] / it["j0"][y])})
        name = f"{a} over {b}"
        cards_by[name] = cards
        decided = [c for c in cards if c["pref"] != 0.5]
        rows[name] = {**C4.share_row(cards),
                      "by_class": {k: C4.share_row([c for c in cards if c["cls"] == k]) for k in ("clean", "crunch")},
                      "by_set": {s: C4.share_row([c for c in cards if c["set"] == s]) for s in SETS},
                      "j0_agrees": {"decided": len(decided),
                                    "agree": sum((c["j0"] < 0) == (c["pref"] == 1.0) for c in decided)}}
    read = len(cards_by["pick over head"])
    failed = read < MIN_READ
    for name, r in rows.items():
        verdicts[name] = "not read" if failed else C4.verdict(r)
    best = {}
    for it in first:
        h = heard[it["id"]]
        if h:
            top = sorted(a for a in AMPS if h[a]["rank"] == min(h[x]["rank"] for x in AMPS))
            for r in ("pick", "head"):
                best.setdefault(r, 0)
                best[r] += it[r] in top and len(top) == 1
            best.setdefault("tied first", 0)
            best["tied first"] += len(top) > 1
    reps = []
    for it in items:
        if it["repeat_of"] and heard[it["id"]] and heard[it["repeat_of"]]:
            agree = all(C4.pref(heard[it["repeat_of"]], a, b) == C4.pref(heard[it["id"]], a, b)
                        for a in AMPS for b in AMPS if a < b)
            reps.append({"id": it["id"], "repeat_of": it["repeat_of"], "agree": agree})
    return {"read": read, "unanswered": [it["id"] for it in first if not heard[it["id"]]], "page_failed": failed,
            "rows": rows, "verdicts": verdicts,
            "outcome": outcome(verdicts["pick over head"], verdicts["pick over sw50r"], failed),
            "ranked_first_alone": best, "repeats": reps, "cards": cards_by}


# --- the page -----------------------------------------------------------------------------------------------------------

INTRO = """<h1>Which preset sounds most like the recording?</h1>
<p class="intro">@@COUNT@@ items of about 4 seconds, looping. <b>Record</b> is the guitar as recorded through an amp.
A, B and C are three presets playing <b>the very same performance</b>, so every note lines up and only the tone differs.
Everything loops together and switches instantly at the same moment: tap a button, or press R, A, B, C (or 1-4); Space stops.
All clips are set to the same loudness. Headphones, please.</p>
<p class="intro">For each item, rank A, B and C: 1 is closest to the Record. If two or all three sound the same to you, give
them the same rank. Rating how close each one is, and saying whether you are sure, are optional. Which preset is which is
hidden and shuffled per item, and a couple of items come back later.
Answers are saved in this browser as you go; tap <b>Export</b> any time and send the text.</p>"""

TITLE = "Tone Ranking Check"           # neutral: it doesn't tell the listener what differs


def canary(items, recs, stored, tol=1e-6):
    """The review's no-render check: each item's judge, per amp and half, equals A2's or C3r's stored judge for the same
    unit, amp and search half. items: the plan's; recs: {slug: clip record}; stored: {(set, unit, amp): {search half:
    {half: value}}}. -> [mismatch]."""
    bad = []
    for it in items:
        for a in AMPS:
            got = recs[it["slug"]]["cands"][a]["judge"]
            want = ((stored.get((it["set"], it["unit"], a)) or {}).get(it["search"])) or {}
            for h in ("A", "B"):
                x, y = got.get(h), want.get(h)
                if x is None or y is None or abs(x - y) > tol * max(1.0, abs(y)):
                    bad.append(f"{it['key']}|{a}|{h}: {x} against {y}")
    return bad


def artifact_page(page, css, js):
    from learn import c1a_ear as C

    return C.artifact_page(page, css, js).replace("<title>Record A/B Check</title>", f"<title>{TITLE}</title>")


def leaks(text, items):
    """Names the page must not carry: C4's, and the amps."""
    words = set(C4.leaks(text, items))
    for w in (*AMPS, "Morgan", "PR12", "SW50", "AC20"):
        if w in text:
            words.add(w)
    return sorted(words)


# --- the commands -------------------------------------------------------------------------------------------------------

def cmd_draw(_args):
    """The items from A2's deciding units, their picks (A2's embed) and heads (A2's amp_p) -> a3/plan.json, written once."""
    from learn import amp_di_compare_r as R
    from learn import full_controls_c3 as X
    from learn import full_space as FS
    from learn import pipeline_fix as P

    P.require(PHASE)
    p = ear_dir() / "plan.json"
    if p.exists():
        raise SystemExit(f"{p} exists: the items are drawn once")
    _, units = R.state_units()
    ans = json.loads((R.a2_dir() / "answers.json").read_text())
    picks, heads = {}, {}
    for u in units:
        if u["set"] in SETS:
            e = json.loads((R.a2_dir() / "embed" / f"{u['set']}__{u['unit'].replace('/', '__')}.json").read_text())
            picks[u["unit"]] = e["picks"]["stem"]
            heads[u["unit"]] = X.s2_picks(ans.get("amp_p") or {}, u["unit"], FS.AMPS)
    cands = candidates(units, picks, heads)
    items = draw(cands)
    prt = {u["unit"]: u["prt"] for u in units}
    items = [{**it, "prt": prt[it["unit"]]} for it in items]
    P.save(p, {"phase": PHASE, "items": items, "eligible": {"clusters": len(cands),
                                                             "directions": sum(len(v) for v in cands.values())},
               "a2_answers_sha256": hashlib.sha256((R.a2_dir() / "answers.json").read_bytes()).hexdigest(),
               "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"A3 DRAW: {len(items)} items on {len({it['cluster'] for it in items})} clusters "
          f"({sum(it['set'] == 'panel' for it in items)} panel); eligible {len(cands)} clusters")


def cmd_render(args):
    """Each item's three presets (R-all's answer on each amp from the search half's input, A2's), fresh (own process, one
    priming render), judged on both halves at the unit's lag; the held-half window clips -> a3/clips/<slug>.npz, .json."""
    import numpy as np

    from learn import amp_di_compare_r as R
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
    raw = (R.a2_dir() / "answers.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != plan["a2_answers_sha256"]:
        raise SystemExit("a2/answers.json changed since the draw")
    ans = json.loads(raw)["answers"]
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
        for a in AMPS:
            x = ans[it["set"]][f"{it['unit']}|{a}"][it["search"]]
            st = LO.tdict(x["settings"])
            y = np.asarray(AM.fresh_render(CB.new_renderer, di32, x["select"], st, st), np.float64)[trim[0]:trim[1]]
            renders += 2
            j = K.judge(ref, y, di, lag)
            mono = np.mean(y, 1) if y.ndim == 2 else y
            s0, s1 = SE.h4_window(held, len(ref), len(mono), lag)
            if win not in (None, (s0, s1)):
                raise SystemExit(f"{it['key']}: the renders' windows differ")
            win = (s0, s1)
            kept[a] = mono[s0 - lag:s1 - lag].astype(np.float32)
            rec["cands"][a] = {"judge": j, "sha": AM.audio_sha(y)}
        s0, s1 = win
        rec["window"] = [s0, s1]
        d.mkdir(parents=True, exist_ok=True)
        np.savez(d / f"{it['slug']}.npz", ref=ref[s0:s1].astype(np.float32), window=np.array([s0, s1]), **kept)
        P.save(d / f"{it['slug']}.json", rec)                # the resume marker, after its clips
        print(f"{it['cls']}: renders so far {renders}", flush=True)
    print(f"A3 RENDER DONE {k}/{n}: {renders} renders", flush=True)


def cmd_page(_args):
    """The page in one part, every clip from the stored renders -> a3/{page/artifact-1.html, key.json}."""
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
    from learn import amp_di_compare_r as R

    recs = {it["slug"]: json.loads((ear_dir() / "clips" / f"{it['slug']}.json").read_text()) for it in plan["items"]}
    bad = canary(plan["items"], recs, R.judges())
    if bad:
        raise SystemExit(f"{len(bad)} clip judges differ from A2's or C3r's (first {bad[0]}): no page")
    items = C4.page_order(plan["items"], seed=PAGE_SEED, cands=AMPS)
    clips, kept = {}, []
    for it in items:
        z = np.load(ear_dir() / "clips" / f"{it['slug']}.npz")
        rec = json.loads((ear_dir() / "clips" / f"{it['slug']}.json").read_text())
        group = {"ref": np.asarray(z["ref"], np.float64), **{k: np.asarray(z[a], np.float64) for k, a in it["letters"].items()}}
        if len({len(v) for v in group.values()}) != 1:
            raise SystemExit(f"{it['key']}: clip lengths differ")
        lev, info = E.level_group(group)
        for k, y in lev.items():
            clips[f"{it['id']}-{k}"] = E.encode(y, ear_dir() / "aac-cache")
        kept.append({**{k: v for k, v in it.items() if k != "prt"}, "levels": info,
                     "j0": {a: rec["cands"][a]["judge"][it["held"]] for a in AMPS}, "window": rec["window"]})
    build = hashlib.sha256(f"{json.dumps([k['letters'] for k in kept])}{time.time_ns()}".encode()).hexdigest()[:12]
    page, css, js = C4.page_html(kept, clips, build, intro=INTRO)
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
    print(f"A3 PAGE: {len(kept)} items -> {out}; build {build}; {out.stat().st_size / 1e6:.1f} MB", flush=True)


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
    print(json.dumps({k: rep[k] for k in ("read", "verdicts", "outcome", "ranked_first_alone")}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("a3-draw").set_defaults(fn=cmd_draw)
    r = sub.add_parser("a3-render")
    r.add_argument("--shard", type=C4.shard, default=(0, 1))
    r.set_defaults(fn=cmd_render)
    sub.add_parser("a3-page").set_defaults(fn=cmd_page)
    q = sub.add_parser("a3-read")
    q.add_argument("out")
    q.add_argument("--answers", required=True)
    q.set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
