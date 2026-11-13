"""R1, the real-song test by ear (`docs/full-controls-plan.md`, "R1 in detail"; ledger `pipeline-fix` `phase_r1`): on the
user's seven songs, generate's research preset (R), the model path (M) and the model path with the delay reader (D),
ranked blind against each song's separated guitar, ties allowed. Every arm plays the class's two stock DIs (A1's), so
the listener compares tone across different playing: the product's own condition (no DI from the user).

    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.product_path separate SONG --out r1/<song>   # the windows, first
    (the product session writes r1/<song>/research.json and r1/<song>/arms/{R,M,D}.xml, D's delay.json beside)
    .venv/bin/python -m learn.r1_ear r1-tail                        # the priming tail check (6 renders), first
    .venv/bin/python -m learn.r1_ear r1-check                       # every input present, hashed -> r1/plan.json
    .venv/bin/python -m learn.r1_ear r1-render --shard 0/3          # each arm through both stock DIs (renders)
    .venv/bin/python -m learn.r1_ear r1-page                        # the page (zero renders)
    .venv/bin/python -m learn.r1_ear r1-read OUT --answers F        # the read (zero renders)

When the delay reader stays off, D's preset equals M's and D plays M's render (one card letter holds identical audio:
its ranks against M are a check of the ear's noise, not read for the delay). The pure parts (the arms' equality, the
song tally, the rule and the read) are unit-tested; C4's page order, unblinding and player are reused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time

from learn import c4_ear as C4

PHASE = "phase_r1"
PAGE_SEED = 20261141                # unused elsewhere (the review: 20261131 was T0's)
PAD_S = 6.0                         # r1-tail's padded probe, and the preroll its rule turns on
TAIL_DB, TAIL_LUFS = 40.0, -60.0    # the declared rule: planned - padded under 40 dB, or the tail above -60 LUFS
PROBE = "/Library/Audio/Presets/Neural DSP/Morgan Amps Suite/Artists/Mark Johnston/Royally Ambient.xml"
PROBE_FX = {("delay", "delayActive"): "true", ("delay", "delaySync"): "0", ("delay", "delayTime"): "450",
            ("delay", "delayMix"): "0.6", ("delay", "delayFeedback"): "0.7", ("reverb", "reverbActive"): "true",
            ("reverb", "reverbMix"): "0.5"}     # long tails on purpose
GAP, REPEATS = 4, 2
ARMS = ("R", "M", "D")              # research, the model path, the model path with the delay reader
LETTERS = C4.LETTERS
MIN_READ = 12                       # first hearings answered (of 14)
LISTENING = "r1-ear"
N_SONGS = 7                          # the user's seven (2026-11-13); their files are listed outside the repo,
#                                      in r1/songs.json (the user: no local song or its files in git)


def songs():
    """slug -> the song's local file, from r1/songs.json (outside the repo)."""
    d = json.loads((ear_dir() / "songs.json").read_text())["songs"]
    if len(d) != N_SONGS:
        raise SystemExit(f"r1/songs.json lists {len(d)} songs, not {N_SONGS}")
    return d


def ear_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "r1"


# --- the pure parts -------------------------------------------------------------------------------------------------------

def same_preset(a, b):
    """Two parsed presets (select, {(module, key): stored}) play the same: the same amp and every control equal."""
    return a[0] == b[0] and a[1] == b[1]


def card_score(heard):
    """One card's M against R: +1 M ranked above, -1 below, 0 tied."""
    m, r = heard["M"]["rank"], heard["R"]["rank"]
    return 1 if m < r else -1 if m > r else 0


def song_tally(scores):
    """{song: [card scores]} -> {song: "ahead" | "behind" | "level"} by the cards' sum."""
    return {s: "ahead" if sum(v) > 0 else "behind" if sum(v) < 0 else "level" for s, v in scores.items() if v}


def rule(tally, n_songs=N_SONGS, page_failed=False):
    """The declared rule on M against R: the model ahead (at least 5 of 7 ahead, at most 1 behind), research ahead (the
    mirror), else level."""
    if page_failed:
        return "not read"
    ahead = sum(v == "ahead" for v in tally.values())
    behind = sum(v == "behind" for v in tally.values())
    need, allow = n_songs - 2, 1
    if ahead >= need and behind <= allow:
        return "the model ahead"
    if behind >= need and ahead <= allow:
        return "research ahead"
    return "level"


def delay_rule(d_scores):
    """{song: [D against M card scores]} on the songs the reader switched on -> its line: never below -> "stays the
    candidate"; below on most of them -> "off"; else "undecided"; none on -> "undecided (none switched on)"."""
    if not d_scores:
        return "undecided (none switched on)"
    per = {s: sum(v) for s, v in d_scores.items() if v}
    if not per:
        return "undecided (none heard)"
    if all(x >= 0 for x in per.values()):
        return "stays the candidate"
    if sum(x < 0 for x in per.values()) > len(per) / 2:
        return "off"
    return "undecided"


def ear_read(items, got):
    """The declared read. items: the key's (song, di, cls, reader_on, letters, repeat_of); got: {id: answer}."""
    heard = {it["id"]: C4.unblind(it, got.get(it["id"])) for it in items}
    first = [it for it in items if it["repeat_of"] is None]
    read = sum(1 for it in first if heard[it["id"]])
    failed = read < MIN_READ
    scores, d_scores, d_check, firsts, cards = {}, {}, [], {a: 0 for a in ARMS}, []
    for it in first:
        h = heard[it["id"]]
        if not h:
            continue
        sc = card_score(h)
        scores.setdefault(it["song"], []).append(sc)
        dm = 1 if h["D"]["rank"] < h["M"]["rank"] else -1 if h["D"]["rank"] > h["M"]["rank"] else 0
        if it["reader_on"]:
            d_scores.setdefault(it["song"], []).append(dm)
        else:
            d_check.append({"id": it["id"], "song": it["song"], "tied": dm == 0})
        best = min(v["rank"] for v in h.values())
        for a in ARMS:
            firsts[a] += h[a]["rank"] == best
        cards.append({"id": it["id"], "song": it["song"], "cls": it["cls"], "di": it["di"], "M_vs_R": sc, "D_vs_M": dm,
                      "ranks": {a: h[a]["rank"] for a in ARMS}})
    tally = song_tally(scores)
    n = [c["M_vs_R"] for c in cards]
    share = (sum(1.0 if x > 0 else 0.5 if x == 0 else 0.0 for x in n) / len(n)) if n else None
    reps = [{"id": it["id"], "repeat_of": it["repeat_of"],
             "agree": all(C4.pref(heard[it["repeat_of"]], a, b) == C4.pref(heard[it["id"]], a, b)
                          for a, b in (("M", "R"), ("D", "M"), ("D", "R")))}
            for it in items if it["repeat_of"] and heard[it["id"]] and heard[it["repeat_of"]]]
    by_class = {}
    for c in cards:
        by_class.setdefault(c["cls"], []).append(c["M_vs_R"])
    return {"read": read, "page_failed": failed, "unanswered": [it["id"] for it in first if not heard[it["id"]]],
            "songs": tally, "ahead": sum(v == "ahead" for v in tally.values()),
            "behind": sum(v == "behind" for v in tally.values()), "level": sum(v == "level" for v in tally.values()),
            "cards_share_M_over_R": share, "rule": rule(tally, page_failed=failed),
            "delay": {"on_songs": sorted(d_scores), "scores": d_scores, "rule": delay_rule(d_scores),
                      "identical_check": d_check},
            "firsts": firsts, "by_class": {k: {"cards": len(v), "M_above": sum(x > 0 for x in v),
                                               "M_below": sum(x < 0 for x in v)} for k, v in by_class.items()},
            "repeats": reps, "cards": cards}


# --- the inputs -----------------------------------------------------------------------------------------------------------

def _rp():
    from learn import pipeline_fix as P

    root = pathlib.Path(P.__file__).resolve().parents[1] / "research"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import render_preset_panel as RP

    return RP


def parse_preset(path, pack):
    """A whole preset -> (select, {(module, key): stored}), every writable control (no rule set)."""
    sel, ed = _rp().preset_edits(pathlib.Path(path), pack, None, "", False)
    return sel, {(e["module"], e["key"]): e["value"] for e in ed}


def _sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def cmd_check(_args):
    """Every song's window, research and three arms present; each arm parsed and hashed; D's equality with M -> plan."""
    from packs.loader import load_pack

    from learn import pipeline_fix as P

    P.require(PHASE)
    pack = load_pack("morgan")
    rows, missing = [], []
    for s, path in songs().items():
        d = ear_dir() / s
        need = [d / "window.json", d / "window.npz", d / "research.json", *[d / "arms" / f"{a}.xml" for a in ARMS]]
        miss = [str(p) for p in need if not p.exists()]
        if miss:
            missing += miss
            continue
        res = json.loads((d / "research.json").read_text())
        if res.get("cls") not in ("clean", "crunch"):
            raise SystemExit(f"{s}: research.json's cls is {res.get('cls')!r}, not clean or crunch")
        parsed = {a: parse_preset(d / "arms" / f"{a}.xml", pack) for a in ARMS}
        dl = d / "arms" / "delay.json"
        reader = json.loads(dl.read_text()) if dl.exists() else None
        rows.append({"song": s, "file": path, "file_sha256": _sha(path), "cls": res["cls"],
                      "window_start_s": json.loads((d / "window.json").read_text())["start_s"],
                      "arms": {a: {"sha256": _sha(d / "arms" / f"{a}.xml"), "select": parsed[a][0]} for a in ARMS},
                      "D_is_M": same_preset(parsed["D"], parsed["M"]),
                      "reader_on": bool(reader and reader.get("on")), "reader": reader})
    if missing:
        raise SystemExit("missing inputs:\n  " + "\n  ".join(missing))
    bad = [x["song"] for x in rows if x["reader_on"] == x["D_is_M"]]
    if bad:
        raise SystemExit(f"{bad}: D's preset should equal M's exactly when the reader is off, and differ when it is on")
    P.save(ear_dir() / "plan.json", {"phase": PHASE, "songs": rows, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"R1 CHECK: {len(rows)} songs; the reader on for {[x['song'] for x in rows if x['reader_on']]}")


def cmd_render(args):
    """Each song's arms through the class's two stock DIs, fresh and primed, trimmed as the model path's -> r1/clips."""
    import numpy as np
    from packs.loader import load_pack

    from learn import amp_di_compare as A1
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    P.require(PHASE)
    plan = json.loads((ear_dir() / "plan.json").read_text())
    pack = load_pack("morgan")
    k, n = args.shard
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    stock_all = json.loads((A1.a1_dir() / "plan.json").read_text())["stock"]
    pre = pre_s()
    LO._wait_cap()
    renders, out = 0, ear_dir() / "clips"
    out.mkdir(parents=True, exist_ok=True)
    for x in plan["songs"][k::n]:
        d = ear_dir() / x["song"]
        for a in ARMS:
            if _sha(d / "arms" / f"{a}.xml") != x["arms"][a]["sha256"]:
                raise SystemExit(f"{x['song']} {a}: the preset changed since r1-check")
        w = np.load(d / "window.npz")
        for j, s in enumerate(stock_all[x["cls"]]):
            p = out / f"{x['song']}__{j}.npz"
            if p.exists():
                continue
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            di = B.measure(PS.section_audio(s["di_path"], s["start_s"])).astype(np.float32)
            clips, shas = {}, {}
            for a in ARMS:
                if a == "D" and x["D_is_M"]:
                    clips[a], shas[a] = clips["M"], shas["M"]               # the same preset: M's render
                    continue
                sel, ed = parse_preset(d / "arms" / f"{a}.xml", pack)
                y = render_kept(CB.new_renderer, AM, di, sel, ed, trim, pre)
                renders += 1
                shas[a] = AM.audio_sha(y)
                clips[a] = (np.mean(y, 1) if y.ndim == 2 else y).astype(np.float32)
            h = PS.half_slices()["A"]                                       # the half the pick read (the review)
            np.savez(p, ref=np.asarray(w["stem"])[h], mix=np.asarray(w["mix"])[h], **{a_: v[h] for a_, v in clips.items()})
            P.save(out / f"{x['song']}__{j}.json", {"song": x["song"], "di": s["di"], "shas": shas, "pre_s": pre})
            print(f"{x['song']} DI {j}: renders so far {renders}", flush=True)
    print(f"R1 RENDER DONE {k}/{n}: {renders} kept renders", flush=True)


def tail_decision(half_a_db, tail_lufs):
    """The declared rule on r1-tail's numbers -> {pre_s, why}."""
    over = [f"planned - padded {half_a_db:.1f} dB, under {TAIL_DB:.0f}"] if half_a_db < TAIL_DB else []
    if any(x > TAIL_LUFS for x in tail_lufs):
        over.append(f"the priming tail alone reaches {max(tail_lufs):.1f} LUFS, above {TAIL_LUFS:.0f}")
    return {"pre_s": PAD_S if over else 0.0, "why": "; ".join(over) or "neither trigger"}


def pre_s():
    """The preroll r1-tail decided; refuses without it."""
    p = ear_dir() / "tail.json"
    if not p.exists() or "decision" not in json.loads(p.read_text()):
        raise SystemExit("no r1-tail decision (r1/tail.json): run r1-tail first")
    return float(json.loads(p.read_text())["decision"]["pre_s"])


def render_kept(make, AM, di, sel, ed, trim, pre):
    """One fresh, primed render with `pre` seconds of silence before the DI (cut off), trimmed as the model path's."""
    import numpy as np

    from learn import pretrain_set as PS

    pre = int(pre * PS.SR)
    x = np.concatenate([np.zeros(pre, np.float32), di]).astype(np.float32)
    y = np.asarray(AM.fresh_render(make, x, sel, ed, ed), np.float64)[pre:]
    return y[trim[0]:trim[1]]


def cmd_tail(_args):
    """The review's check: does the priming render leave a tail in the kept one, with time effects on? A long-tailed
    probe (the clean pr12 start with a strong delay and reverb) through the clean stock DI: the kept render as planned
    (no preroll) against one with 6 s of silent preroll, and the priming render's tail alone (silence after it)."""
    import numpy as np
    from packs.loader import load_pack

    from learn import amp_di_compare as A1
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_aug as SA
    from learn import song_bank as B

    P.require(PHASE)
    sel, ed = parse_preset(PROBE, load_pack("morgan"))
    ed = {**ed, **PROBE_FX}
    s = json.loads((A1.a1_dir() / "plan.json").read_text())["stock"]["clean"][0]
    di = B.measure(PS.section_audio(s["di_path"], s["start_s"])).astype(np.float32)
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    mono = lambda y: np.mean(y, 1) if y.ndim == 2 else y            # noqa: E731
    planned = mono(render_kept(CB.new_renderer, AM, di, sel, ed, trim, 0.0))
    padded = mono(render_kept(CB.new_renderer, AM, di, sel, ed, trim, PAD_S))
    rr = CB.new_renderer()                                         # the tail alone: prime with the DI, then silence
    try:
        rr.render(di, sel, ed)
        tail = mono(np.asarray(rr.render(np.zeros_like(di), sel, ed), np.float64))
    finally:
        rr.close()
    h = PS.half_slices()["A"]
    db = lambda x: float(10 * np.log10(np.mean(np.square(x)) + 1e-20))   # noqa: E731
    rep = {"probe": PROBE, "fx": {f"{m}/{k}": v for (m, k), v in PROBE_FX.items()}, "di": s["di"],
           "half A: planned - padded, dB below the clip": db(planned[h]) - db(planned[h] - padded[h]),
           "first 0.5 s: planned - padded, dB below the clip": db(planned[:int(0.5 * PS.SR)]) -
           db(planned[:int(0.5 * PS.SR)] - padded[:int(0.5 * PS.SR)]),
           "the priming tail's level, LUFS by second": [round(float(SA.lufs(tail[int(t * PS.SR):int((t + 1) * PS.SR)])), 1)
                                                         for t in range(int(len(tail) / PS.SR))],
           "the clip's LUFS": float(SA.lufs(planned)), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    rep["decision"] = tail_decision(rep["half A: planned - padded, dB below the clip"],
                                    rep["the priming tail's level, LUFS by second"])
    P.save(ear_dir() / "tail.json", rep)
    print(json.dumps(rep, indent=1))


# --- the page -------------------------------------------------------------------------------------------------------------

INTRO = """<h1>Which preset sounds most like the song's guitar?</h1>
<p class="intro">@@COUNT@@ items of about 4.5 seconds, looping. <b>Guitar (G)</b> is the song's guitar, separated from the
mix; <b>Song (S)</b> is the same moment of the full song, for context only. A, B and C are three presets playing
<b>another guitarist's performance</b>, so the notes differ: judge the tone, not the playing.
Everything switches instantly: tap a button, or press G, S, A, B, C; Space stops. All clips are set to the same loudness.
Headphones, please.</p>
<p class="intro">For each item, rank A, B and C: 1 is closest to the song's guitar. If two or all three sound the same to
you, give them the same rank. Closeness and confidence are optional. Which preset is which is hidden and shuffled per
item, and a couple of items come back later. Answers are saved in this browser as you go; tap <b>Export</b> any time and
send the text.</p>"""


def cards(items):
    """C4's cards with the song's guitar (G) and the song (S) to play."""
    html = C4.cards(items)
    old = '<button type="button" class="src" data-k="ref" aria-pressed="false">Record (R)</button>'
    new = ('<button type="button" class="src" data-k="ref" aria-pressed="false">Guitar (G)</button>'
           '<button type="button" class="src" data-k="mix" aria-pressed="false">Song (S)</button>')
    if html.count(old) != len(items):
        raise SystemExit("C4's cards changed")
    return (html.replace(old, new).replace("closest to the Record", "closest to the song's guitar")
            .replace("to the Record?", "to the song's guitar?").replace("<h3>Recording ", "<h3>Item "))


JS_EDITS = (
    ('KEYS = ["ref", "A", "B", "C"]', 'KEYS = ["ref", "mix", "A", "B", "C"]'),
    ('const NAMES = {ref: "the record\'s guitar", A: "A", B: "B", C: "C"};',
     'const NAMES = {ref: "the song\'s guitar", mix: "the song", A: "A", B: "B", C: "C"};'),
    ('a: "A", b: "B", c: "C", "1": "ref", "2": "A", "3": "B", "4": "C"',
     'a: "A", b: "B", c: "C", g: "ref", s: "mix", "1": "ref", "2": "A", "3": "B", "4": "C"'),
)


def player_js():
    js = C4.player_js().replace("c4-ear", LISTENING)
    for old, new in JS_EDITS:
        if old not in js:
            raise SystemExit(f"C4's player changed: {old[:60]}")
        js = js.replace(old, new)
    return js


def page_html(chunk, clips, build):
    from learn import ear_vreal as E

    js, css = player_js(), E.CSS + C4.CSS_EXTRA
    a, b = E.PAGE.index("<h1>"), E.PAGE.index("@@CARDS@@")
    data = json.dumps({"build": build, "items": [{"id": it["id"], "n": it["n"]} for it in chunk]})
    page = (E.PAGE[:a] + INTRO + "\n" + E.PAGE[b:]).replace("@@COUNT@@", str(len(chunk))).replace("@@CARDS@@", cards(chunk)) \
        .replace("@@CSS@@", css).replace("@@DATA@@", data).replace("@@CLIPS@@", json.dumps(clips)).replace("@@JS@@", js)
    return page, css, js


def leaks(text, plan):
    words = {"research", "model path", "delay reader", "R-all", "adopted"}
    for x in plan["songs"]:
        words |= {x["song"], pathlib.Path(x["file"]).stem}
    return sorted(w for w in words if w in text)


def cmd_page(_args):
    """The page from the stored clips -> r1/{page/artifact-1.html, key.json}."""
    import numpy as np

    from learn import ear_vreal as E
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    P.require(PHASE)
    key_path = ear_dir() / "key.json"
    if key_path.exists():
        raise SystemExit(f"{key_path} exists: a rebuild hides the listener's stored answers; move it aside first")
    plan = json.loads((ear_dir() / "plan.json").read_text())
    items = []
    for x in plan["songs"]:
        for j in (0, 1):
            if not (ear_dir() / "clips" / f"{x['song']}__{j}.npz").exists():
                raise SystemExit(f"no clips for {x['song']} DI {j}: every render comes first")
            items.append({"key": f"{x['song']}|{j}", "song": x["song"], "di": j, "cls": x["cls"],
                          "reader_on": x["reader_on"], "slug": f"{x['song']}__{j}"})
    order = C4.page_order(items, seed=PAGE_SEED, gap=GAP, repeats=REPEATS, cands=ARMS)
    clips, kept = {}, []
    for it in order:
        z = np.load(ear_dir() / "clips" / f"{it['slug']}.npz")
        group = {"ref": z["ref"], "mix": z["mix"], **{k: z[c] for k, c in it["letters"].items()}}
        lev, info = E.level_group({k: np.asarray(v, np.float64) for k, v in group.items()})
        for k, y in lev.items():
            clips[f"{it['id']}-{k}"] = E.encode(y, ear_dir() / "aac-cache")
        kept.append({**it, "levels": info})
    build = hashlib.sha256(f"{json.dumps([k['letters'] for k in kept])}{time.time_ns()}".encode()).hexdigest()[:12]
    page, css, js = page_html(kept, clips, build)
    bad = leaks(page.split('<script id="clips"')[0], plan)
    if bad:
        raise SystemExit(f"the page names {bad}")
    local = PS.HOME / "listening" / LISTENING / "index.html"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(page)
    out = ear_dir() / "page" / "artifact-1.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    from learn import c1a_ear as C

    out.write_text(C.artifact_page(page, css, js).replace("<title>Record A/B Check</title>", "<title>Song Tone Check</title>"))
    P.save(key_path, {"phase": PHASE, "build": build, "items": kept, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"R1 PAGE: {len(kept)} items -> {out}; build {build}; {out.stat().st_size / 1e6:.1f} MB", flush=True)


def cmd_read(args):
    from learn import pipeline_fix as P

    P.require(PHASE)
    key = json.loads((ear_dir() / "key.json").read_text())
    got = json.loads(pathlib.Path(args.answers).read_text())
    got = got.get("answers", got)
    rep = {"phase": PHASE, "build": key["build"], **ear_read(key["items"], got),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(pathlib.Path(args.out), rep)
    print(json.dumps({k: rep[k] for k in ("read", "songs", "ahead", "behind", "level", "cards_share_M_over_R", "rule",
                                          "firsts")}, indent=1))
    print("DELAY:", json.dumps({k: rep["delay"][k] for k in ("on_songs", "rule")}))


def shard(s):
    k, n = (int(x) for x in s.split("/"))
    return k, n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("r1-check").set_defaults(fn=cmd_check)
    sub.add_parser("r1-tail").set_defaults(fn=cmd_tail)
    r = sub.add_parser("r1-render")
    r.add_argument("--shard", type=shard, default=(0, 1))
    r.set_defaults(fn=cmd_render)
    sub.add_parser("r1-page").set_defaults(fn=cmd_page)
    rd = sub.add_parser("r1-read")
    rd.add_argument("out")
    rd.add_argument("--answers", required=True)
    rd.set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
