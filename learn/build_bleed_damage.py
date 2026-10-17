"""Bleed listening check 2: damage against a labelled original (`docs/bleed-listening-plan.md`,
amendment 1). Development only; descriptive.

    .venv/bin/python -m learn.build_bleed_damage build
    .venv/bin/python -m learn.build_bleed_damage score --answers "1X-little-tone 2N 3Y-lot-bg ..."

Check 1 asked about damage with no known reference, so a listener could take the original's
drive for damage (or the reverse). Here each trial plays the amp track labelled "Original", then
X and Y: one is the original again (a hidden reference) and one is the cleaned track, in a seeded
order. One null trial has X and Y both original. The listener names which one differs from the
Original (X, Y or N for neither), how much (little or lot), and what differs (the guitar's tone,
the background/leakage, both, or unsure). A cleaned pick is read as damage only with 'tone' or
'both'. Each encoded clip carries a random-length mp4 `free` box, so sizes and bytes say nothing.

Same five parts and halves as check 1, the same cleaning (`build_bleed_listening.bleed_estimate`),
zero plugin renders. The key is written under `private/`, never in the page.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import random
import re
import struct
import sys
import tempfile

from learn import build_bleed_listening as B1

SEED = 20261018
NULL = "null"
NULL_PART = ("telefunken-Gym_Hours-GTR_1", "B")


# --- pure functions (unit-tested) ------------------------------------------------------------------

def draw(seed=SEED, high=B1.HIGH, low_halves=None):
    """The trials in page order: the 3 high parts, the 2 low controls on the halves check 1 drew,
    and one null trial (X = Y = original) on NULL_PART. Shuffled; reshuffled while the null trial is
    trial 1 or sits next to the same part. Each trial gets {X, Y: 'original' | 'cleaned'}, the
    cleaned letter balanced over the 5 non-null trials."""
    if low_halves is None:
        low_halves = {t["slug"]: t["held"] for t in B1.draw() if t["kind"] == "low"}
    rng = random.Random(seed)
    trials = [{"slug": s, "held": h, "kind": "high"} for s, h in high]
    trials += [{"slug": s, "held": low_halves[s], "kind": "low"} for s in sorted(low_halves)]
    on_x = [True] * (len(trials) // 2) + [False] * (len(trials) - len(trials) // 2)
    if len(trials) % 2 and rng.random() < 0.5:
        on_x = [not x for x in on_x]
    rng.shuffle(on_x)
    for t, x in zip(trials, on_x):
        t["letters"] = {"X": "cleaned", "Y": "original"} if x else {"X": "original", "Y": "cleaned"}
    trials.append({"slug": NULL_PART[0], "held": NULL_PART[1], "kind": NULL,
                   "letters": {"X": "original", "Y": "original"}})
    while True:
        rng.shuffle(trials)
        i = next(i for i, t in enumerate(trials) if t["kind"] == NULL)
        near = [trials[j]["slug"] for j in (i - 1, i + 1) if 0 <= j < len(trials)]
        if i > 0 and NULL_PART[0] not in near:
            return trials


WHAT = ("tone", "bg", "both", "unsure")
ANSWER_RE = re.compile(r"(\d+)(?:(n|neither)(?:-no)?|(x|y)-(little|lot|alot|a-lot|\?)(?:-(tone|bg|both|unsure|\?))?|(\?))",
                       re.I)


def parse_answers(text):
    """'1X-little-tone 2N 3Y-lot-bg 4? 5X-?-?' -> {'1': ('X', 'little', 'tone'), '2': ('N', None, None),
    '3': ('Y', 'lot', 'bg'), '4': (None, None, None), '5': ('X', None, None)}."""
    out = {}
    for tok in text.replace("a lot", "lot").split():
        m = ANSWER_RE.fullmatch(tok.strip())
        if not m:
            raise SystemExit(f"cannot read answer {tok!r} (expected like 1X-little-tone, 2N, 3Y-lot-bg)")
        if m.group(2):
            out[m.group(1)] = ("N", None, None)
        elif m.group(3):
            amt = m.group(4).lower()
            amt = None if amt == "?" else ("lot" if amt in ("alot", "a-lot") else amt)
            what = (m.group(5) or "?").lower()
            out[m.group(1)] = (m.group(3).upper(), amt, None if what == "?" else what)
        else:
            out[m.group(1)] = (None, None, None)
    return out


def role(trial, pick):
    """What the pick names: 'cleaned', 'original' (the hidden reference), 'neither', for the null
    trial 'a letter' (both are the original); None if unanswered."""
    if pick is None:
        return None
    if pick == "N":
        return "neither"
    if trial["kind"] == NULL:
        return "a letter"
    return trial["letters"][pick]


def score_key(key, answers):
    rows = []
    for n, t in sorted(key["trials"].items(), key=lambda x: int(x[0])):
        pick, amt, what = answers.get(n, (None, None, None))
        names = role(t, pick)
        rows.append({"trial": int(n), "kind": t["kind"], "slug": t["slug"], "held": t["held"],
                     "bleed_removed_db": t.get("bleed_removed_db"), "pick": pick,
                     "names": names, "amount": amt, "what": what,
                     "damage": names == "cleaned" and what in ("tone", "both")})
    counts = {}
    for kind in ("high", "low", NULL):
        c = {}
        for r in rows:
            if r["kind"] == kind:
                k = "-".join(x for x in (r["names"] or "unanswered", r["amount"], r["what"]) if x)
                c[k] = c.get(k, 0) + 1
        counts[kind] = c
    return {"trials": rows, **counts}


# --- the page --------------------------------------------------------------------------------------

PAGE = B1.PAGE.split("<h1>")[0].replace("Leak listening check", "Guitar change check") + """<h1>Does the guitar sound changed?</h1>
<p class="muted">{count} trials. Each plays the same 4.5 seconds of a guitar track three times, at the
same loudness. <b>Original</b> is the track as recorded, drive and all. One of X and Y is that same
original; the other may have had leakage from other instruments taken out. Some trials may have X and
Y both the original. Headphones help; guess if unsure.</p>
<p class="muted">For each trial: <b>which one sounds different from the Original's guitar</b> (X, Y
or neither), <b>how much</b> (a little or a lot), and <b>what</b> differs: the guitar's tone (duller,
thinner, hollow, warbly, artifacts), the background (leakage from other instruments), both, or
unsure.</p>
{trials}
<h2>Your answers</h2>
<p class="muted">Copy this line and send it back, for example <code>1X-little</code>,
<code>1X-little-tone</code>, <code>2N</code> or <code>3Y-lot-bg</code>. A ? marks a trial not yet answered.</p>
<div id="line">—</div>
<script>
const key = "bleed-damage-{build}";
let a = {{}}; try {{ a = JSON.parse(localStorage.getItem(key) || "{{}}"); }} catch (e) {{}}
function show() {{
  document.querySelectorAll(".pick").forEach(p => p.querySelectorAll("button").forEach(b =>
    b.classList.toggle("on", (a[p.dataset.trial] || {{}})[p.dataset.q] === b.dataset.value)));
  const n = [...new Set([...document.querySelectorAll(".pick")].map(p => p.dataset.trial))];
  document.getElementById("line").textContent = n.map(t => {{
    const r = a[t] || {{}};
    if (r.which === "N") return t + "N";
    return t + (r.which || "?") + (r.which ? "-" + (r.amt || "?") + "-" + (r.what || "?") : "");
  }}).join(" ");
}}
document.querySelectorAll(".pick button").forEach(b => b.onclick = () => {{
  const p = b.parentElement;
  a[p.dataset.trial] = Object.assign(a[p.dataset.trial] || {{}}, {{[p.dataset.q]: b.dataset.value}});
  try {{ localStorage.setItem(key, JSON.stringify(a)); }} catch (e) {{}}
  show(); }});
document.querySelectorAll("audio").forEach(x => x.addEventListener("play", () =>
  document.querySelectorAll("audio").forEach(y => {{ if (y !== x) y.pause(); }})));
show();
</script></body></html>
"""


def section(n, clips):
    rows = "".join(f'<div class="row"><b>{L}</b><audio controls preload="none" src="{src}"></audio></div>'
                   for L, src in clips)
    which = "".join(f'<button type="button" data-value="{v}">{lab}</button>'
                    for v, lab in (("X", "X"), ("Y", "Y"), ("N", "Neither")))
    amt = "".join(f'<button type="button" data-value="{v}">{lab}</button>'
                  for v, lab in (("little", "A little"), ("lot", "A lot")))
    what = "".join(f'<button type="button" data-value="{v}">{lab}</button>'
                   for v, lab in (("tone", "Guitar tone"), ("bg", "Background"), ("both", "Both"),
                                  ("unsure", "Unsure")))
    return (f'<section><h2>Trial {n}</h2>{rows}'
            f'<div class="q">Which sounds different from the Original?</div>'
            f'<div class="pick" data-trial="{n}" data-q="which">{which}</div>'
            f'<div class="q">How much? (skip if neither)</div>'
            f'<div class="pick" data-trial="{n}" data-q="amt">{amt}</div>'
            f'<div class="q">What differs? (skip if neither)</div>'
            f'<div class="pick" data-trial="{n}" data-q="what">{what}</div></section>')


def pad(src, rng=None):
    """Append a random-length (64–4,095 byte) mp4 `free` box to a base64 data URI, so encoded
    sizes and bytes say nothing about which clips share samples. Players skip `free` boxes."""
    head, b64 = src.split(",", 1)
    n = (rng or random.SystemRandom()).randrange(64, 4096)
    blob = base64.b64decode(b64) + struct.pack(">I4s", 8 + n, b"free") + os.urandom(n)
    return head + "," + base64.b64encode(blob).decode()


def _out():
    from learn import knob_ceiling as K

    return K.HOME / "listening" / "bleed-2"


def build(args):
    import pathlib

    import numpy as np

    from learn import build_knob_listening as BK
    from learn import confirm_run as CR
    from learn import knob_ceiling as K
    from learn import phase2_set3 as P

    out_dir = _out()
    if (out_dir / "private" / "key.json").exists() and not args.force:
        raise SystemExit(f"{out_dir / 'private' / 'key.json'} exists; pass --force to rebuild")
    trials = draw()
    ps = json.loads((B1.ROOT / "docs" / "label-table-parts.json").read_text())["parts"]
    key = {"plan": "docs/bleed-listening-plan.md#amendment-1", "seed": SEED, "trials": {}}
    cache, sections = {}, []
    with tempfile.TemporaryDirectory() as tmp:
        for n, t in enumerate(trials, 1):
            slug, held = t["slug"], t["held"]
            print(f"  {n} {t['kind']:5s} {slug} held {held} letters {t['letters']}", flush=True)
            crop = pathlib.Path(ps[slug]["crop"])
            a, b = K.R.HALVES[held]
            orig = CR.mono(crop / "reference.wav")[int(a * P.SR):int(b * P.SR)]
            if (slug, held) not in cache:
                bl = B1.bleed_in_crop(B1.bleed_estimate(slug, crop, held), a, b)
                cache[slug, held] = (orig - bl, B1._db(float(np.sum(bl ** 2)) / float(np.sum(orig ** 2))))
            cleaned, removed = cache[slug, held]
            clips = {"original": orig, "cleaned": cleaned}
            enc = lambda x: pad(BK.aac(BK.fade(BK.level(np.asarray(x, np.float64))), tmp))
            srcs = [("Original", enc(orig))] + [(L, enc(clips[name])) for L, name in t["letters"].items()]
            sections.append(section(n, srcs).replace("<b>Original</b>", '<b style="width:5em">Original</b>'))
            key["trials"][str(n)] = {"kind": t["kind"], "slug": slug, "held": held,
                                     "letters": t["letters"], "bleed_removed_db": removed}
    build_id = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:12]
    page = PAGE.format(count=len(sections), build=build_id, trials="\n".join(sections))
    text = re.sub(r"base64,[A-Za-z0-9+/=]+", "", page).lower()
    for w in {t["slug"] for t in trials} | {"telefunken", "cambridge", "gym", "offering", "sculptor",
                                            "drag me", "farthest", "gtr_", "elecgtr", "null", "cleaned\""}:
        assert w.lower() not in text, w
    uris = re.findall(r'src="(data:[^"]+)"', page)
    assert len(uris) == 3 * len(sections) and len(set(uris)) == len(uris), "duplicate clip bytes"
    assert len({len(u) for u in uris}) > len(uris) // 2, "clip sizes too uniform"
    (out_dir / "private").mkdir(parents=True, exist_ok=True)
    (out_dir / "private" / "key.json").write_text(json.dumps(key, indent=1))
    page_path = out_dir / "bleed-damage.html"
    page_path.write_text(page)
    print(page_path, f"{page_path.stat().st_size / 1e6:.2f} MB")


def score(args):
    out_dir = _out()
    key = json.loads((out_dir / "private" / "key.json").read_text())
    rep = score_key(key, parse_answers(args.answers))
    for r in rep["trials"]:
        print(f"{r['trial']} {r['kind']:5s} {r['slug']} held {r['held']} removed {r['bleed_removed_db']} dB: "
              f"picked {r['pick']} -> {r['names']} {r['amount'] or ''} {r['what'] or ''}"
              f"{' (damage)' if r['damage'] else ''}")
    for k in ("high", "low", NULL):
        print(f"{k}:", rep[k])
    rep["answers"] = args.answers
    (out_dir / "private" / "score.json").write_text(json.dumps(rep, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("build", "score"))
    ap.add_argument("--answers", default="")
    ap.add_argument("--force", action="store_true", help="build: rebuild over an existing key")
    a = ap.parse_args(argv)
    build(a) if a.step == "build" else score(a)


if __name__ == "__main__":
    sys.exit(main())
