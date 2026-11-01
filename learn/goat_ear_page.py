"""5C's ear page (`docs/pipeline-fix-plan.md`, ledger `phase_5c`): every kept GOAT unit heard before any GOAT render.

One card per unit: its DI window (A) and its capture render (B) on the instant A/B switch (`cc_drive_page`'s player),
both at -23 LUFS; one question, "a believable amp tone, from a clean DI?". Flagged units (the render's cab roll-off or
low end outside the range of BKS's reamped tracks, a doubled cab or a capture without one) are always on the page,
never marked as flagged. With `--sample N`, the flagged units plus a seeded sample of the rest up to N.

    $MAIN -m learn.goat_ear_page build [--sample N]   # -> ~/ndsp-presets/listening/goat-ear/part-<k>.html
    $MAIN -m learn.goat_ear_page answers EXPORT.json ...   # -> goat/ear.json (the verdicts by unit)
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import pathlib
import random
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

PAGE_NAME = "goat-ear"
SEED = 20261048
PART_ITEMS = 75                     # cards per page file (phone-sized)
ITEM_S = 15.0                       # listening time per card (the page's estimate)
BANDS = {"hi": (6000.0, 10000.0), "mid": (1000.0, 3000.0), "lo": (60.0, 150.0)}
VERDICTS = [("amp", "A believable amp tone"), ("odd", "Odd amp sound (muffled, fizzy, artifacts)"),
            ("di_bad", "The DI itself sounds processed or noisy"), ("unsure", "Not sure")]


def band_db(x, sr, band):
    import numpy as np

    f = np.fft.rfftfreq(len(x), 1.0 / sr)
    p = np.abs(np.fft.rfft(np.asarray(x, np.float64) * np.hanning(len(x)))) ** 2
    return 10 * np.log10(p[(f >= band[0]) & (f < band[1])].sum() + 1e-30)


def tilt(x, sr):
    """The render's cab roll-off and low end: 6-10 kHz and 60-150 Hz power, each against 1-3 kHz (dB)."""
    m = band_db(x, sr, BANDS["mid"])
    return {"hi_db": band_db(x, sr, BANDS["hi"]) - m, "lo_db": band_db(x, sr, BANDS["lo"]) - m}


def flagged(t, ref):
    """Outside BKS's reamps' range on either measure. ref: {"hi_db": (min, max), "lo_db": (min, max)}."""
    return any(not (ref[k][0] <= t[k] <= ref[k][1]) for k in ("hi_db", "lo_db"))


def pick(units, flags, n=None, seed=SEED):
    """Every flagged unit, then a seeded sample of the rest up to n (all with n None), in a seeded order."""
    rng = random.Random(seed)
    fl = sorted(u for u in units if flags[u])
    rest = sorted(u for u in units if not flags[u])
    if n is not None:
        rest = rng.sample(rest, max(0, min(len(rest), n - len(fl))))
    out = fl + rest
    rng.shuffle(out)
    return out


def bks_ref():
    """The range of BKS's reamped tracks over every searched BKS section (5B.2's records)."""
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    recs, by_unit, _ = P.real_labels(2)
    vals = {"hi_db": [], "lo_db": []}
    for u in sorted({r["unit"] for r in recs}):
        prt = by_unit[u]
        t = tilt(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), PS.SR)
        for k in vals:
            vals[k].append(t[k])
    return {k: (min(v), max(v)) for k, v in vals.items()}, len(vals["hi_db"])


def card(it, n, total):
    e = html.escape
    vs = "".join(f'<button type="button" class="v" data-v="{v}">{e(t)}</button>' for v, t in VERDICTS)
    return (f'<article class="item" data-id="{it["id"]}" data-n="{n}"><div class="num">{n} / {total}</div>'
            f'<h3>Recording {n}</h3><p class="sub">A: the DI · B: the amp recording</p>'
            f'<div class="plays"><button type="button" class="play main">&#9654; Play</button>'
            f'<button type="button" class="ab" data-side="0" aria-pressed="false">A</button>'
            f'<button type="button" class="ab" data-side="1" aria-pressed="false">B</button>'
            f'<button type="button" class="sw">Switch A/B (S)</button>'
            f'</div><p class="now"></p><div class="vs">{vs}</div>'
            f'<input class="note" type="text" placeholder="Note (optional)" aria-label="Note"></article>')


def page_html(items, clips, build, part, n_parts, start_n):
    from learn import build_ear_page as BEP
    from learn import cc_drive_page as CDP

    total = len(items)
    secs = {it["id"]: ITEM_S for it in items}
    data = {"page": PAGE_NAME, "part": part, "build": build,
            "items": [{"id": it["id"], "title": f"Recording {start_n + j}", "subtitle": ""}
                      for j, it in enumerate(items)], "secs": secs}
    js = BEP.JS_HEAD + CDP.PLAYER_JS.replace("XFADE_S", repr(CDP.XFADE_S)) + BEP.JS_ANSWERS
    body = "".join(card(it, start_n + j, start_n + total - 1) for j, it in enumerate(items))
    minutes = round(sum(secs.values()) / 60)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>GOAT ear {part}</title>
<style>{BEP.CSS}{CDP.CSS}</style></head><body>
<header><div class="hrow"><b>Part {part} of {n_parts}: GOAT amp recordings</b><span id="count"></span></div>
<div class="hrow"><label><input type="checkbox" id="auto"> Autoplay next</label>
<span id="left" class="ask"></span></div><div class="prog"><div id="bar"></div></div></header>
<main>
<h1>A believable amp tone, from a clean DI?</h1>
<p class="intro">{total} recordings, about {minutes} minutes. A is a guitar DI, B is the same performance played
through a captured amp and cab (a neural capture, not our plugin). Press Play and switch between A and B as often as
you like: the Switch button, the A and B buttons, or the S, A and B keys; the switch is instant. Judge B: does it sound
like a believable guitar amp and cab, not muffled as if through two cabs, not fizzy as if through none, with no
artifacts? And if A, the DI, already sounds processed, noisy or hummy, say so. Both are set to the same loudness.
Answers are saved in this browser as you go; tap <b>Export</b> any time, even halfway, and send the file.</p>
{body}
</main>
<footer><button type="button" id="next">Next unanswered</button>
<button type="button" id="export" class="primary">Export</button></footer>
<div id="exp"><b>Your answers</b><p class="ask">Save it as a file, or copy it, and send it.</p>
<textarea id="out" readonly></textarea>
<div class="row"><button type="button" id="copy">Copy</button><button type="button" id="save">Save file</button>
<button type="button" id="close">Close</button></div></div>
<script id="data" type="application/json">{json.dumps(data).replace("</", "<\\/")}</script>
<script id="clips" type="application/json">{json.dumps(clips)}</script>
<script>{js}</script></body></html>"""


def cmd_build(args):
    from learn import audibility_measure as AM
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    P.require("phase_5c")
    units = {u["unit"]: u for u in P.goat_units()}
    ref, n_ref = bks_ref()
    trim = int(PS.TRIM_S * PS.SR)
    tilts, flags = {}, {}
    for u, prt in units.items():
        tilts[u] = tilt(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), PS.SR)
        flags[u] = flagged(tilts[u], ref)
    chosen = pick(sorted(units), flags, args.sample)
    out = PS.HOME / "listening" / PAGE_NAME
    key_path = P.out_dir() / P.GOAT_DIR / "ear-key.json"
    if key_path.exists() and not args.force:
        raise SystemExit(f"{key_path} exists: a rebuild hides the listener's stored answers (--force)")
    items = [{"id": "goat-" + hashlib.sha256(f"{SEED}|{u}".encode()).hexdigest()[:12], "unit": u} for u in chosen]
    build = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    parts = [items[j:j + PART_ITEMS] for j in range(0, len(items), PART_ITEMS)]
    out.mkdir(parents=True, exist_ok=True)
    for k, its in enumerate(parts, 1):
        clips = {}
        for it in its:
            prt = units[it["unit"]]
            di = PS.section_audio(prt["di_path"], prt["start_s"])[trim:]
            amp = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            clips[it["id"] + "-1"], clips[it["id"] + "-2"] = AM.pair_clips(di, amp, out / "cache")
        p = out / f"part-{k}.html"
        p.write_text(page_html(its, clips, build, k, len(parts), 1 + (k - 1) * PART_ITEMS))
        print(f"part {k}: {len(its)} cards, {p.stat().st_size / 1e6:.1f} MB -> {p}")
    P.save(key_path, {"page": PAGE_NAME, "seed": SEED, "build": build, "sample": args.sample, "bks_range": ref,
                      "bks_sections": n_ref, "items": items, "flagged": sorted(u for u in chosen if flags[u]),
                      "tilt": tilts, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"GOAT EAR PAGE DONE: {len(items)} cards ({sum(flags[u] for u in chosen)} flagged), {len(parts)} parts")


def cmd_answers(args):
    from learn import pipeline_fix as P

    key = json.loads((P.out_dir() / P.GOAT_DIR / "ear-key.json").read_text())
    unit_of = {it["id"]: it["unit"] for it in key["items"]}
    got = {}
    for f in args.exports:
        ex = json.loads(pathlib.Path(f).read_text())
        if ex.get("page") != PAGE_NAME or ex.get("build") != key["build"]:
            raise SystemExit(f"{f}: not this page's export (page {ex.get('page')}, build {ex.get('build')})")
        for a in ex.get("answers", []):
            if a["id"] in unit_of and a.get("verdict"):
                got[unit_of[a["id"]]] = {"verdict": a["verdict"], "note": a.get("note") or ""}
    P.save(P.out_dir() / P.GOAT_DIR / "ear.json", {"page": PAGE_NAME, "build": key["build"], "exports": args.exports,
                                                   "verdicts": got, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    c = {}
    for v in got.values():
        c[v["verdict"]] = c.get(v["verdict"], 0) + 1
    print(f"GOAT EAR ANSWERS: {len(got)} of {len(unit_of)} heard; {c}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--sample", type=int, default=None)
    b.add_argument("--force", action="store_true")
    a = sub.add_parser("answers")
    a.add_argument("exports", nargs="+")
    args = ap.parse_args(argv)
    {"build": cmd_build, "answers": cmd_answers}[args.cmd](args)


if __name__ == "__main__":
    main()
