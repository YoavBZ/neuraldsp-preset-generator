"""5D's ear page (`docs/pipeline-fix-plan.md`, ledger `phase_5d`): every panel unit heard before any panel render.

One card per unit: its DI window (A) and its recorded amp track (B) on the instant A/B switch (`goat_ear_page`'s
player and cards), both at -23 LUFS, in a seeded order (bands mixed); one question, "a real amp, the guitar alone?".
Only "amp" passes (`pipeline_fix.panel_heard`).

    $MAIN -m learn.panel_ear_page build              # -> ~/ndsp-presets/listening/panel-ear/part-1.html
    $MAIN -m learn.panel_ear_page answers EXPORT.json  # -> panel/ear.json (the verdicts by unit)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

PAGE_NAME = "panel-ear"
RECHECK_PAGE = "panel-ear-recheck"
SEED = 20261102
VERDICTS = [("amp", "A real amp, the guitar alone"), ("bleed", "Other instruments audible in the amp track"),
            ("odd", "Odd or processed amp sound"), ("di_bad", "The DI itself sounds processed or noisy"),
            ("unsure", "Not sure")]
SPEC = {"page": PAGE_NAME, "verdicts": VERDICTS, "title": "Real-amp panel ear", "head": "Real amp recordings",
        "h1": "A real amp, with the guitar alone?",
        "ask": """A is a guitar DI, B is the same performance recorded through a real amp
and mic in a studio. Press Play and switch between A and B as often as you like: the Switch button, the A and B
buttons, or the S, A and B keys; the switch is instant. Judge B: is it a real guitar amp with only this guitar in it?
If you can hear other instruments in B (drums, bass, another guitar, vocals), choose that answer. If B sounds odd or
processed, or A, the DI, already sounds processed or noisy, say so. Hum in the DI is expected on some recordings and
is fine if B has it too."""}


def cmd_build(args):
    from learn import goat_ear_page as G
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    P.require("phase_5d")
    units = {u["unit"]: u for u in P.panel_units()}
    key_path = P.out_dir() / P.PANEL_DIR / "ear-key.json"
    if key_path.exists() and not args.force:
        raise SystemExit(f"{key_path} exists: a rebuild hides the listener's stored answers (--force)")
    order = sorted(units)
    random.Random(SEED).shuffle(order)
    items = [{"id": "panel-" + hashlib.sha256(f"{SEED}|{u}".encode()).hexdigest()[:12], "unit": u} for u in order]
    build = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    out = PS.HOME / "listening" / PAGE_NAME
    out.mkdir(parents=True, exist_ok=True)
    trim = int(PS.TRIM_S * PS.SR)
    clips = {}
    for it in items:
        prt = units[it["unit"]]
        di = PS.section_audio(prt["di_path"], prt["start_s"])[trim:]
        amp = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        clips[it["id"] + "-1"], clips[it["id"] + "-2"] = G.pair_clips(di, amp, out / "cache")
    p = out / "part-1.html"
    p.write_text(G.page_html(items, clips, build, 1, 1, 1, SPEC))
    P.save(key_path, {"page": PAGE_NAME, "seed": SEED, "build": build, "items": items,
                      "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"PANEL EAR PAGE DONE: {len(items)} cards, {p.stat().st_size / 1e6:.1f} MB -> {p}")


RECHECK = {**SPEC, "page": RECHECK_PAGE, "title": "Real-amp panel re-check", "head": "Re-check: clean recordings",
           "ask": """A second listen to a few clean recordings you were unsure about or marked
"DI bad". A measurement says A is a guitar DI here (bright, full dynamics) and B a real amp recording (darker,
coloured), so A is not an amp track in disguise. Judge again: is B a real amp with only this guitar in it, and does A
sound like an ordinary DI (hum is fine)? Switch with the buttons or the S, A and B keys."""}


def cmd_recheck(args):
    """A re-check page for the units in `--units` (one per line in a file), with RECHECK's question."""
    from learn import goat_ear_page as G
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    P.require("phase_5d")
    units = {u["unit"]: u for u in P.panel_units()}
    chosen = [u for u in pathlib.Path(args.units).read_text().splitlines() if u.strip()]
    if not set(chosen) <= set(units):
        raise SystemExit(f"not panel units: {sorted(set(chosen) - set(units))}")
    random.Random(f"{SEED}|recheck").shuffle(chosen)
    items = [{"id": "recheck-" + hashlib.sha256(f"{SEED}|recheck|{u}".encode()).hexdigest()[:12], "unit": u}
             for u in chosen]
    build = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    out = PS.HOME / "listening" / RECHECK_PAGE
    out.mkdir(parents=True, exist_ok=True)
    trim = int(PS.TRIM_S * PS.SR)
    clips = {}
    for it in items:
        prt = units[it["unit"]]
        di = PS.section_audio(prt["di_path"], prt["start_s"])[trim:]
        amp = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        clips[it["id"] + "-1"], clips[it["id"] + "-2"] = G.pair_clips(di, amp, PS.HOME / "listening" / PAGE_NAME / "cache")
    p = out / "part-1.html"
    p.write_text(G.page_html(items, clips, build, 1, 1, 1, RECHECK))
    P.save(P.out_dir() / P.PANEL_DIR / "recheck-key.json", {"page": RECHECK_PAGE, "seed": SEED, "build": build,
                                                             "items": items, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"PANEL RECHECK PAGE DONE: {len(items)} cards, {p.stat().st_size / 1e6:.1f} MB -> {p}")


def cmd_answers(args, key_name="ear-key.json", page=PAGE_NAME, out_name="ear.json"):
    """Exports -> {unit: {verdict, note}}, saved as panel/ear.json (the re-check's: panel/recheck.json); refuses
    another page's or build's export."""
    from learn import pipeline_fix as P

    key = json.loads((P.out_dir() / P.PANEL_DIR / key_name).read_text())
    unit_of = {it["id"]: it["unit"] for it in key["items"]}
    got = {}
    for f in args.exports:
        ex = json.loads(pathlib.Path(f).read_text())
        if ex.get("page") != page or ex.get("build") != key["build"]:
            raise SystemExit(f"{f}: not this page's export (page {ex.get('page')}, build {ex.get('build')})")
        for a in ex.get("answers", []):
            if a["id"] in unit_of and a.get("verdict"):
                got[unit_of[a["id"]]] = {"verdict": a["verdict"], "note": a.get("note") or ""}
    P.save(P.out_dir() / P.PANEL_DIR / out_name, {"page": page, "build": key["build"], "exports": args.exports,
                                                   "verdicts": got, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    c = {}
    for v in got.values():
        c[v["verdict"]] = c.get(v["verdict"], 0) + 1
    print(f"PANEL {page.upper()} ANSWERS: {len(got)} of {len(unit_of)} heard; {c}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--force", action="store_true")
    a = sub.add_parser("answers")
    a.add_argument("exports", nargs="+")
    r = sub.add_parser("recheck")
    r.add_argument("units")
    ra = sub.add_parser("recheck-answers")
    ra.add_argument("exports", nargs="+")
    args = ap.parse_args(argv)
    {"build": cmd_build, "answers": cmd_answers, "recheck": cmd_recheck,
     "recheck-answers": lambda a: cmd_answers(a, "recheck-key.json", RECHECK_PAGE, "recheck.json")}[args.cmd](args)


if __name__ == "__main__":
    main()
