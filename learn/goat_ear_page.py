"""5C's ear page (`docs/pipeline-fix-plan.md`, ledger `phase_5c`): every kept GOAT unit heard before any GOAT render.

One card per unit: its DI window (A) and its capture render (B) on the instant A/B switch (`cc_drive_page`'s player),
both at -23 LUFS; one question, "a believable amp tone, from a clean DI?". Flagged units (the render's cab roll-off or
low end outside the range of BKS's reamped tracks, a doubled cab or a capture without one) are always on the page,
never marked as flagged. With `--sample N`, the flagged units plus a seeded sample of the rest up to N.

    $MAIN -m learn.goat_ear_page build [--sample N]   # -> ~/ndsp-presets/listening/goat-ear/part-<k>.html
    $MAIN -m learn.goat_ear_page answers EXPORT.json ...   # -> goat/ear.json (the verdicts by unit)

The heavy check (amendment of 2026-11-01): the units the ear passed that the pool's classifier calls firmly driven
(`classify`'s clean_vs_driven split "driven": non-linear share >= 0 dB and level slope <= 0.3) are heard again,
blind to the measure, against the pool's clean/crunch scope; only "keep" stays in (`pipeline_fix.goat_heavy_out`).

    $MAIN -m learn.goat_ear_page heavy                     # -> ~/ndsp-presets/listening/goat-heavy/part-1.html
    $MAIN -m learn.goat_ear_page heavy-answers EXPORT.json  # -> goat/heavy.json
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
HEAVY_PAGE = "goat-heavy"
SEED = 20261048
PART_ITEMS = 75                     # cards per page file
KBPS = 96                           # AAC: an amp-tone check, not a near-threshold one (about 21 MB a part)
ITEM_S = 15.0                       # listening time per card (the page's estimate)
BANDS = {"hi": (6000.0, 10000.0), "mid": (1000.0, 3000.0), "lo": (60.0, 150.0)}
VERDICTS = [("amp", "A believable amp tone"), ("odd", "Odd amp sound (muffled, fizzy, artifacts)"),
            ("di_bad", "The DI itself sounds processed or noisy"), ("unsure", "Not sure")]
HEAVY_VERDICTS = [("keep", "Keep: clean or crunch, within our scope"), ("heavy", "Too heavy or fizzy"),
                  ("unsure", "Not sure")]
EAR = {"page": PAGE_NAME, "verdicts": VERDICTS, "title": "GOAT ear", "head": "GOAT amp recordings",
       "h1": "A believable amp tone, from a clean DI?",
       "ask": """A is a guitar DI, B is the same performance played
through a captured amp and cab (a neural capture, not our plugin). Press Play and switch between A and B as often as
you like: the Switch button, the A and B buttons, or the S, A and B keys; the switch is instant. Judge B: does it sound
like a believable guitar amp and cab, not muffled as if through two cabs, not fizzy as if through none, with no
artifacts? And if A, the DI, already sounds processed, noisy or hummy, say so."""}
HEAVY = {"page": HEAVY_PAGE, "verdicts": HEAVY_VERDICTS, "title": "GOAT heavy check",
         "head": "GOAT heavy check", "h1": "Too heavy or fizzy for our clean/crunch scope?",
         "ask": """You passed all of these as believable amps. This time judge only how
heavy B is: the presets we build are clean and crunch, with heavy tones a small minority and never very heavy. Keep a
recording if B is clean or crunch you would want the model to learn from; mark it too heavy or fizzy if it is beyond
that. A is the DI, B the captured amp; switch with the buttons or the S, A and B keys."""}


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


def pair_clips(a, b, cache_dir, kbps=KBPS):
    """`audibility_measure.pair_clips` at KBPS: both clips at -23 LUFS, 10-ms fades, AAC, base64."""
    import numpy as np
    import soundfile as sf

    from learn import audibility_measure as AM
    from learn import build_data_review as BDR

    out = []
    for v in AM.level_free(np.asarray(a, np.float64), np.asarray(b, np.float64)):
        y = BDR.fade(v)
        h = hashlib.sha256(y.astype(np.float32).tobytes()).hexdigest()[:16]
        flac = pathlib.Path(cache_dir) / f"{h}.flac"
        flac.parent.mkdir(parents=True, exist_ok=True)
        if not flac.exists():
            sf.write(str(flac), y, BDR.SR, subtype="PCM_24")
        out.append(AM.aac_b64(flac, cache_dir, kbps))
    return out


def firmly_driven(gm):
    """The heavy check's candidates: `classify`'s clean_vs_driven split is "driven" (gm: `gainmeasure.measures`)."""
    from learn import pretrain_set as PS

    if str(PS.HOME / "references/datasets-set3/_tools") not in sys.path:
        sys.path.insert(0, str(PS.HOME / "references/datasets-set3/_tools"))
    import classify as C

    return bool(gm) and C.classify(gm)[3] == "driven"


def card(it, n, total, verdicts=VERDICTS):
    e = html.escape
    vs = "".join(f'<button type="button" class="v" data-v="{v}">{e(t)}</button>' for v, t in verdicts)
    return (f'<article class="item" data-id="{it["id"]}" data-n="{n}"><div class="num">{n} / {total}</div>'
            f'<h3>Recording {n}</h3><p class="sub">A: the DI · B: the amp recording</p>'
            f'<div class="plays"><button type="button" class="play main">&#9654; Play</button>'
            f'<button type="button" class="ab" data-side="0" aria-pressed="false">A</button>'
            f'<button type="button" class="ab" data-side="1" aria-pressed="false">B</button>'
            f'<button type="button" class="sw">Switch A/B (S)</button>'
            f'</div><p class="now"></p><div class="vs">{vs}</div>'
            f'<input class="note" type="text" placeholder="Note (optional)" aria-label="Note"></article>')


def page_html(items, clips, build, part, n_parts, start_n, spec=EAR):
    from learn import build_ear_page as BEP
    from learn import cc_drive_page as CDP

    total = len(items)
    secs = {it["id"]: ITEM_S for it in items}
    data = {"page": spec["page"], "part": part, "build": build,
            "items": [{"id": it["id"], "title": f"Recording {start_n + j}", "subtitle": ""}
                      for j, it in enumerate(items)], "secs": secs}
    js = BEP.JS_HEAD + CDP.PLAYER_JS.replace("XFADE_S", repr(CDP.XFADE_S)) + BEP.JS_ANSWERS
    body = "".join(card(it, start_n + j, start_n + total - 1, spec["verdicts"]) for j, it in enumerate(items))
    minutes = round(sum(secs.values()) / 60)
    data_json = json.dumps(data).replace("</", "<\\/")      # no backslash inside an f-string before Python 3.12
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{spec["title"]} {part}</title>
<style>{BEP.CSS}{CDP.CSS}</style></head><body>
<header><div class="hrow"><b>Part {part} of {n_parts}: {spec["head"]}</b><span id="count"></span></div>
<div class="hrow"><label><input type="checkbox" id="auto"> Autoplay next</label>
<span id="left" class="ask"></span></div><div class="prog"><div id="bar"></div></div></header>
<main>
<h1>{spec["h1"]}</h1>
<p class="intro">{total} recordings, about {minutes} minutes. {spec["ask"]} Both are set to the same loudness.
Answers are saved in this browser as you go; tap <b>Export</b> any time, even halfway, and send the file.</p>
{body}
</main>
<footer><button type="button" id="next">Next unanswered</button>
<button type="button" id="export" class="primary">Export</button></footer>
<div id="exp"><b>Your answers</b><p class="ask">Save it as a file, or copy it, and send it.</p>
<textarea id="out" readonly></textarea>
<div class="row"><button type="button" id="copy">Copy</button><button type="button" id="save">Save file</button>
<button type="button" id="close">Close</button></div></div>
<script id="data" type="application/json">{data_json}</script>
<script id="clips" type="application/json">{json.dumps(clips)}</script>
<script>{js}</script></body></html>"""


def cmd_build(args):
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
            clips[it["id"] + "-1"], clips[it["id"] + "-2"] = pair_clips(di, amp, out / "cache")
        p = out / f"part-{k}.html"
        p.write_text(page_html(its, clips, build, k, len(parts), 1 + (k - 1) * PART_ITEMS))
        print(f"part {k}: {len(its)} cards, {p.stat().st_size / 1e6:.1f} MB -> {p}")
    P.save(key_path, {"page": PAGE_NAME, "seed": SEED, "build": build, "sample": args.sample, "bks_range": ref,
                      "bks_sections": n_ref, "items": items, "flagged": sorted(u for u in chosen if flags[u]),
                      "tilt": tilts, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"GOAT EAR PAGE DONE: {len(items)} cards ({sum(flags[u] for u in chosen)} flagged), {len(parts)} parts")


def heavy_candidates():
    """The units the ear passed whose render the pool's classifier calls firmly driven (goat/units.json's
    gain measures), sorted. Reads goat/ear.json directly: the gate itself waits for the heavy check."""
    from learn import pipeline_fix as P

    gd = P.out_dir() / P.GOAT_DIR
    items = json.loads((gd / "units.json").read_text())["items"]
    ok, missing = P.goat_heard([u["unit"] for u in P.goat_units()],
                               json.loads((gd / "ear.json").read_text())["verdicts"])
    if missing:
        raise SystemExit(f"{len(missing)} units not yet heard on the ear page")
    return sorted(u["unit"] for u in P.goat_units()
                  if u["unit"] in ok and firmly_driven(items[u["item"]]["renders"][str(u["render"])]["gain_measures"]))


def cmd_heavy(args):
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    P.require("phase_5c")
    units = {u["unit"]: u for u in P.goat_units()}
    chosen = heavy_candidates()
    random.Random(f"{SEED}|heavy").shuffle(chosen)
    key_path = P.out_dir() / P.GOAT_DIR / "heavy-key.json"
    if key_path.exists() and not args.force:
        raise SystemExit(f"{key_path} exists: a rebuild hides the listener's stored answers (--force)")
    items = [{"id": "heavy-" + hashlib.sha256(f"{SEED}|heavy|{u}".encode()).hexdigest()[:12], "unit": u}
             for u in chosen]
    build = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    out = PS.HOME / "listening" / HEAVY_PAGE
    out.mkdir(parents=True, exist_ok=True)
    trim = int(PS.TRIM_S * PS.SR)
    clips = {}
    for it in items:
        prt = units[it["unit"]]
        di = PS.section_audio(prt["di_path"], prt["start_s"])[trim:]
        amp = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        clips[it["id"] + "-1"], clips[it["id"] + "-2"] = pair_clips(di, amp, PS.HOME / "listening" / PAGE_NAME / "cache")
    p = out / "part-1.html"
    p.write_text(page_html(items, clips, build, 1, 1, 1, HEAVY))
    P.save(key_path, {"page": HEAVY_PAGE, "seed": SEED, "build": build, "rule": "classify clean_vs_driven == driven",
                      "items": items, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"GOAT HEAVY PAGE DONE: {len(items)} cards, {p.stat().st_size / 1e6:.1f} MB -> {p}")


def read_answers(exports, key_name, page, out_name):
    """Exports -> {unit: {verdict, note}}, saved as goat/<out_name>; refuses another page's or build's export."""
    from learn import pipeline_fix as P

    key = json.loads((P.out_dir() / P.GOAT_DIR / key_name).read_text())
    unit_of = {it["id"]: it["unit"] for it in key["items"]}
    got = {}
    for f in exports:
        ex = json.loads(pathlib.Path(f).read_text())
        if ex.get("page") != page or ex.get("build") != key["build"]:
            raise SystemExit(f"{f}: not this page's export (page {ex.get('page')}, build {ex.get('build')})")
        for a in ex.get("answers", []):
            if a["id"] in unit_of and a.get("verdict"):
                got[unit_of[a["id"]]] = {"verdict": a["verdict"], "note": a.get("note") or ""}
    P.save(P.out_dir() / P.GOAT_DIR / out_name, {"page": page, "build": key["build"], "exports": exports,
                                                 "verdicts": got, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    c = {}
    for v in got.values():
        c[v["verdict"]] = c.get(v["verdict"], 0) + 1
    return got, len(unit_of), c


def cmd_heavy_answers(args):
    got, n, c = read_answers(args.exports, "heavy-key.json", HEAVY_PAGE, "heavy.json")
    print(f"GOAT HEAVY ANSWERS: {len(got)} of {n} heard; {c}")


def cmd_answers(args):
    got, n, c = read_answers(args.exports, "ear-key.json", PAGE_NAME, "ear.json")
    print(f"GOAT EAR ANSWERS: {len(got)} of {n} heard; {c}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--sample", type=int, default=None)
    b.add_argument("--force", action="store_true")
    a = sub.add_parser("answers")
    a.add_argument("exports", nargs="+")
    h = sub.add_parser("heavy")
    h.add_argument("--force", action="store_true")
    ha = sub.add_parser("heavy-answers")
    ha.add_argument("exports", nargs="+")
    args = ap.parse_args(argv)
    {"build": cmd_build, "answers": cmd_answers, "heavy": cmd_heavy, "heavy-answers": cmd_heavy_answers}[args.cmd](args)


if __name__ == "__main__":
    main()
