"""Knob ceiling 2, stage 2's listening page (`docs/knob-ceiling-2-plan.md`). Development only.

    .venv/bin/python -m learn.build_effects_listening build
    .venv/bin/python -m learn.build_effects_listening score --answers "1A 2B ..."

Among the cells whose stage-2 result is wet:
- the 4 parts with the largest judge gain (wet vs dry, held half), each in its better direction;
- 2 drawn with `random.Random(20261015).sample(sorted(remaining parts), 2)`, in direction A→B
  (B→A if A isn't wet);
- 2 more that turned on a reverb or a delay, if not already chosen (the largest gains).

Per trial, the held half: the record, then dry (stage 1) and wet (stage 2), unlabelled, with the
wet option's letter drawn at random per trial (seeded). The first sitting (2026-10-15) used the
least-used letter instead, which alternated A/B with the trial number and so confounded a
listener's position preference with the effect; see docs/knob-ceiling-2-results.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import tempfile

from learn import build_knob_listening as B
from learn import confirm_run as CR
from learn import knob_ceiling as K
from learn import knob_ceiling2 as K2

OUT = K.HOME / "listening" / "knob-ceiling-2-effects"
SEED = 20261015


def wet_rows():
    rows = [json.loads(p.read_text()) for p in sorted((K2.OUT / "stage2").glob("*/[AB].json"))]
    return [r for r in rows if r["wet"]]


def gain(r):
    return math.log(r["held"] / r["start_held"])


def choose():
    rows = wet_rows()
    by = {}
    for r in rows:
        by.setdefault(r["slug"], []).append(r)
    best = {s: min(v, key=gain) for s, v in by.items()}
    top = sorted(best, key=lambda s: gain(best[s]))[:4]
    picks = [(best[s], "top") for s in top]
    rest = sorted(set(by) - set(top))
    for s in random.Random(SEED).sample(rest, min(2, len(rest))):
        cand = [r for r in by[s] if r["search_half"] == "A"] or by[s]
        picks.append((cand[0], "random"))
    chosen = {r["slug"] for r, _ in picks}
    extra = sorted((r for r in rows if r["slug"] not in chosen and r["effects_on"]
                    and r["effects_on"][0] in ("reverb", "delay")), key=gain)
    for r in extra:
        if len([p for p in picks if p[1] == "reverb-delay"]) >= 2:
            break
        if r["slug"] not in {p[0]["slug"] for p in picks}:
            picks.append((r, "reverb-delay"))
    return picks


def _settings(path):
    return {tuple(k.rsplit("/", 1)): v for k, v in json.loads(path.read_text()).items()}


def build(args):
    import numpy as np

    picks = choose()
    rng = random.Random(SEED)
    rng.shuffle(picks)
    ps = K.parts()
    rr = K.Renderer()
    key, sections, used = {"seed": SEED, "trials": {}}, [], [0, 0]
    letter_rng = random.Random(SEED + 1)
    try:
        menu = rr.menu()
        with tempfile.TemporaryDirectory() as tmp:
            for n, (r, why) in enumerate(picks, 1):
                slug, amp, search, held = r["slug"], r["amp"], r["search_half"], r["held_half"]
                part = ps[slug]
                di32 = K.measure_di(part).astype(np.float32)
                select = next(iter(menu[amp].values()))[0]
                dry = _settings(K2.OUT / "stage1" / slug / f"{search}-settings.json")
                wet = _settings(K2.OUT / "stage2" / slug / f"{search}-settings.json")
                rr.render(di32, select, dry)                                 # warm-up
                options = {"dry": rr.render(di32, select, dry), "wet": rr.render(di32, select, wet)}
                pos = letter_rng.randrange(2)
                used[pos] += 1
                names = ["dry"]
                names.insert(pos, "wet")
                letters = "AB"
                ref = B.fade(B.level(B.clip(CR.mono(part["crop"] / "reference.wav"), held)))
                rows = [f'<div class="row"><b>Record</b><audio controls preload="none" src="{B.aac(ref, tmp)}">'
                        f'</audio></div>']
                for L, name in zip(letters, names):
                    x = B.fade(B.level(B.clip(np.asarray(options[name], np.float64), held)))
                    rows.append(f'<div class="row"><b>{L}</b><audio controls preload="none" '
                                f'src="{B.aac(x, tmp)}"></audio></div>')
                buttons = "".join(f'<button type="button" data-value="{L}">{L}</button>' for L in letters)
                sections.append(f'<section><h2>Trial {n}</h2>{"".join(rows)}'
                                f'<div class="pick" data-trial="{n}">{buttons}</div></section>')
                key["trials"][str(n)] = {"slug": slug, "amp": amp, "search": search, "held": held, "why": why,
                                         "effect": r["effects_on"], "letters": dict(zip(letters, names)),
                                         "judge_held": {"dry": r["start_held"], "wet": r["held"]}}
                print(n, slug, amp, search, why, r["effects_on"], names, flush=True)
    finally:
        rr.close()
    build_id = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:12]
    page = B.PAGE.format(count=len(sections), build=build_id, trials="\n".join(sections))
    page = page.replace("Knob listening check", "Effects listening check")
    text = re.sub(r"base64,[A-Za-z0-9+/=]+", "", page).lower()
    for word in {r["slug"] for r, _ in picks} | {"pr12", "sw50r", "ac20", "factory", "reverb", "delay"}:
        assert word.lower() not in text, word
    (OUT / "private").mkdir(parents=True, exist_ok=True)
    old = OUT / "private" / "key.json"
    if old.exists():                       # keep earlier sittings' keys
        old.rename(old.with_name(f"key-{int(old.stat().st_mtime)}.json"))
    (OUT / "private" / "key.json").write_text(json.dumps(key, indent=1))
    out = OUT / "effects-listening.html"
    out.write_text(page)
    print(out, f"{out.stat().st_size / 1e6:.1f} MB")


def score(args):
    key = json.loads((OUT / "private" / "key.json").read_text())
    ans = dict((t[:-1], t[-1]) for t in args.answers.split())
    wins = {"wet": 0, "dry": 0}
    for n, t in sorted(key["trials"].items(), key=lambda x: int(x[0])):
        pick = t["letters"].get(ans.get(n, "?"))
        if pick:
            wins[pick] += 1
        print(n, t["slug"], t["amp"], t["why"], t["effect"], "picked", pick, "judge", t["judge_held"])
    print("picked:", wins, "of", len(key["trials"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("build", "score"))
    ap.add_argument("--answers", default="")
    a = ap.parse_args(argv)
    build(a) if a.step == "build" else score(a)


if __name__ == "__main__":
    main()
