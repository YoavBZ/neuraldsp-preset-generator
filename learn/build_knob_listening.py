"""The knob-ceiling listening page (`docs/knob-ceiling-plan.md`, amendment 4). Development only.

    .venv/bin/python -m learn.build_knob_listening build     # renders M, writes the page and key
    .venv/bin/python -m learn.build_knob_listening score --answers "1B 2A ..."

Per cell, the held half only: the recording, then 2–3 unlabelled options in a seeded random
order (the menu oracle M, the knob search K_M, and the EQ stage where it adds ≤ −0.04 on that
direction). The listener picks the option closest to the recording. The key is written beside
the page under `private/`, never in it.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import pathlib
import random
import subprocess
import sys
import tempfile

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import confirm_run as CR  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import phase2_set3 as P  # noqa: E402

OUT = K.HOME / "listening" / "knob-ceiling"
SEED = 20261013
TOP = 4
RANDOM = 2
EQ_ADDS = -0.04
KBPS = 160
TARGET_LUFS = -20.0


def gain(cell, search):
    run, held = cell["runs"][search], "B" if search == "A" else "A"
    return math.log(run["K_M"]["held"] / cell["menu"][run["M"]][held])


def choose():
    """The declared cells: the top 4 by cross-half K_M gain (direction: the larger held gain),
    2 at random, and the largest-EQ-gain cell with an edge band at ±12 dB, if new."""
    cells = {}
    for p in sorted((K.OUT / "cells").glob("*/*/result.json")):
        c = json.loads(p.read_text())
        rows, _ = K.cell_rows(c)
        if "KM_vs_M" in rows:
            cells[(c["slug"], c["amp"])] = (c, rows)
    top = sorted(cells, key=lambda k: cells[k][1]["KM_vs_M"])[:TOP]
    picks = []
    for k in top:
        c = cells[k][0]
        d = min((s for s, _ in K.DIRECTIONS if "skipped" not in c["runs"][s]), key=lambda s: gain(c, s))
        picks.append((k, d, "top"))
    rest = sorted(set(cells) - set(top))
    for k in random.Random(SEED).sample(rest, RANDOM):
        picks.append((k, "A", "random"))
    chosen = {k for k, _, _ in picks}
    best = None
    for k, (c, _) in cells.items():
        for s, held in K.DIRECTIONS:
            run = c["runs"][s]
            if "skipped" in run:
                continue
            eq = json.loads((K.OUT / "cells" / k[0] / k[1] / f"EQ-{s}.json").read_text())
            edge = any(abs(float(eq[f"{k[1]}EQ/{k[1]}EQBand{i}"])) >= 12 for i in (1, 9))
            g = math.log(run["EQ"]["held"] / run["K_M"]["held"])
            if edge and k not in chosen and (best is None or g < best[0]):
                best = (g, k, s)
    if best:
        picks.append((best[1], best[2], "eq-edge"))
    return picks, cells


def clip(x, half):
    if x.ndim == 2:
        x = x.mean(axis=1)
    a, b = K.R.HALVES[half]
    return x[int(a * P.SR):int(b * P.SR)]


def level(x):
    import numpy as np
    import pyloudnorm

    m = pyloudnorm.Meter(P.SR)
    y = x * 10 ** ((TARGET_LUFS - m.integrated_loudness(x)) / 20)
    peak = np.abs(y).max()
    return y * (0.9 / peak) if peak > 0.9 else y


def fade(x, s=0.02):
    import numpy as np

    n = int(s * P.SR)
    r = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))
    y = x.copy()
    y[:n] *= r
    y[-n:] *= r[::-1]
    return y


def aac(x, tmp):
    import soundfile as sf

    wav, m4a = pathlib.Path(tmp) / "c.wav", pathlib.Path(tmp) / "c.m4a"
    sf.write(str(wav), x.astype("float32"), P.SR)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", str(KBPS * 1000), str(wav), str(m4a)],
                   check=True)
    return "data:audio/mp4;base64," + base64.b64encode(m4a.read_bytes()).decode()


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Knob listening check</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e3e0d8; --card:#fff; --acc:#2d5bd7; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#161614; --fg:#ecebe6; --muted:#a3a29c;
  --line:#33322e; --card:#1f1f1c; --acc:#7da0ff; }} }}
body {{ background:var(--bg); color:var(--fg); font:16px/1.45 -apple-system,system-ui,sans-serif;
  margin:0 auto; max-width:720px; padding:16px; }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 14px;
  margin:14px 0; }}
.row {{ display:flex; align-items:center; gap:10px; margin:6px 0; }}
.row b {{ width:5.5em; }} audio {{ width:100%; }}
.pick button {{ font-size:16px; padding:8px 16px; margin:4px 6px 0 0; border-radius:8px;
  border:1px solid var(--line); background:var(--bg); color:var(--fg); }}
.pick button.on {{ background:var(--acc); color:#fff; border-color:var(--acc); }}
#line {{ font:15px ui-monospace,monospace; padding:10px; border:1px dashed var(--line); border-radius:8px;
  word-break:break-all; }} .muted {{ color:var(--muted); }}
</style></head><body>
<h1>Which is closest to the record?</h1>
<p class="muted">{count} trials. In each, play the <b>Record</b>, then the options. Every clip is
the same 4.5 seconds of guitar, at the same loudness. Pick the option that sounds most like the
record. Guess if unsure. Headphones help.</p>
{trials}
<h2>Your answers</h2>
<p class="muted">Copy this line and send it back.</p>
<div id="line">—</div>
<script>
const key = "knob-listen-{build}";
let a = {{}}; try {{ a = JSON.parse(localStorage.getItem(key) || "{{}}"); }} catch (e) {{}}
function show() {{
  document.querySelectorAll(".pick").forEach(p => p.querySelectorAll("button").forEach(b =>
    b.classList.toggle("on", a[p.dataset.trial] === b.dataset.value)));
  const n = [...document.querySelectorAll(".pick")].map(p => p.dataset.trial);
  document.getElementById("line").textContent = n.map(t => t + (a[t] || "?")).join(" ");
}}
document.querySelectorAll(".pick button").forEach(b => b.onclick = () => {{
  a[b.parentElement.dataset.trial] = b.dataset.value;
  try {{ localStorage.setItem(key, JSON.stringify(a)); }} catch (e) {{}}
  show(); }});
document.querySelectorAll("audio").forEach(x => x.addEventListener("play", () =>
  document.querySelectorAll("audio").forEach(y => {{ if (y !== x) y.pause(); }})));
show();
</script></body></html>
"""


def build(args):
    import numpy as np
    import soundfile as sf

    picks, cells = choose()
    ps = K.parts()
    rng = random.Random(SEED)
    rng.shuffle(picks)
    rr = K.Renderer()
    key, sections = {"seed": SEED, "trials": {}}, []
    used = [0, 0, 0]
    try:
        menu = rr.menu()
        with tempfile.TemporaryDirectory() as tmp:
            for n, ((slug, amp), search, why) in enumerate(picks, 1):
                c, _ = cells[(slug, amp)]
                held = "B" if search == "A" else "A"
                run = c["runs"][search]
                part = ps[slug]
                d = K.OUT / "cells" / slug / amp
                di32 = K.measure_di(part).astype(np.float32)
                rr.render(di32, *menu[amp][run["M"]])                       # warm-up
                options = {"M": rr.render(di32, *menu[amp][run["M"]]),
                           "K_M": sf.read(str(d / f"K_M-{search}.flac"))[0]}
                eq_gain = math.log(run["EQ"]["held"] / run["K_M"]["held"])
                if eq_gain <= EQ_ADDS:
                    options["EQ"] = sf.read(str(d / f"EQ-{search}.flac"))[0]
                # K_M's position rotates over the trials (A, B, C, A, ...), so no letter is the
                # usual answer; the others fill the remaining positions in seeded order.
                others = [x for x in options if x != "K_M"]
                rng.shuffle(others)
                pos = min(range(len(options)), key=lambda i: (used[i], i))
                used[pos] += 1
                names = others[:pos] + ["K_M"] + others[pos:]
                letters = "ABC"[:len(names)]
                ref = fade(level(clip(CR.mono(part["crop"] / "reference.wav"), held)))
                rows = [f'<div class="row"><b>Record</b><audio controls preload="none" src="{aac(ref, tmp)}">'
                        f'</audio></div>']
                for L, name in zip(letters, names):
                    x = fade(level(clip(np.asarray(options[name], np.float64), held)))
                    rows.append(f'<div class="row"><b>{L}</b><audio controls preload="none" '
                                f'src="{aac(x, tmp)}"></audio></div>')
                buttons = "".join(f'<button type="button" data-value="{L}">{L}</button>' for L in letters)
                sections.append(f'<section><h2>Trial {n}</h2>{"".join(rows)}'
                                f'<div class="pick" data-trial="{n}">{buttons}</div></section>')
                key["trials"][str(n)] = {"slug": slug, "amp": amp, "search": search, "held": held,
                                         "why": why, "M": run["M"], "letters": dict(zip(letters, names)),
                                         "judge_held": {"M": c["menu"][run["M"]][held],
                                                        "K_M": run["K_M"]["held"], "EQ": run["EQ"]["held"]}}
                print(n, slug, amp, search, why, names, flush=True)
    finally:
        rr.close()
    build_id = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:12]
    page = PAGE.format(count=len(sections), build=build_id, trials="\n".join(sections))
    for word in {s for (s, a), _, _ in picks} | {"PR12", "SW50R", "AC20", "factory", "K_M"}:
        text = __import__("re").sub(r"base64,[A-Za-z0-9+/=]+", "", page).lower()
        assert word.lower() not in text, word
    (OUT / "private").mkdir(parents=True, exist_ok=True)
    (OUT / "private" / "key.json").write_text(json.dumps(key, indent=1))
    out = OUT / "knob-listening.html"
    out.write_text(page)
    print(out, f"{out.stat().st_size / 1e6:.1f} MB", "key sha256",
          hashlib.sha256((OUT / "private" / "key.json").read_bytes()).hexdigest())


def score(args):
    key = json.loads((OUT / "private" / "key.json").read_text())
    ans = dict((t[:-1], t[-1]) for t in args.answers.split())
    wins = {"K_M": 0, "EQ": 0, "M": 0}
    for n, t in sorted(key["trials"].items(), key=lambda x: int(x[0])):
        pick = t["letters"].get(ans.get(n, "?"))
        if pick:
            wins[pick] += 1
        print(n, t["slug"], t["amp"], t["why"], "picked", pick, "judge", t["judge_held"])
    print("picked:", wins, "of", len(key["trials"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("build", "score"))
    ap.add_argument("--answers", default="")
    a = ap.parse_args(argv)
    build(a) if a.step == "build" else score(a)


if __name__ == "__main__":
    main()
