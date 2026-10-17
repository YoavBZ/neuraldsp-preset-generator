"""Arm A listening check 1 (`docs/arm-a-listening-plan.md`). Development only; descriptive.

    .venv/bin/python -m learn.build_arm_a_listening build
    .venv/bin/python -m learn.build_arm_a_listening score --answers "1A 2B 3S ..."

Is arm A's current best ("3-C′ shrunk halfway") audibly closer to the record than the starting
preset S? 8 trials drawn with random.Random(20261026) from the directions where the judge's
held-half |log(d_armA / d_S)| >= 0.03 (at most one per band; PR12 3, SW50R 3, AC20 2), plus one
catch trial where A and B are the same S render. Each trial plays the held half: the record,
then arm A and S under seeded random letters (balanced: arm A is A on half the trials). Answers are A, B or S (= "same"). The key is
written under `private/`, never in the page.

The pure functions (eligibility, the draw, letters, scoring, the binomial interval) are
unit-tested; the build renders and is not.
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

LEVER = "lever-shrink-0.5"
SEED = 20261026
LETTER_SEED = SEED + 1
MIN_ABS_LOG = 0.03
QUOTA = {"pr12": 3, "sw50r": 3, "ac20": 2}
N_TRIALS = 8
CONF = 0.90
CATCH = "catch"


# --- pure functions (unit-tested) ------------------------------------------------------------------

def finite_pos(x):
    return x is not None and math.isfinite(x) and x > 0


def eligible(rows, min_abs=MIN_ABS_LOG):
    """rows: dicts with slug, band, amp, search, held, d_armA, d_S (held-half judge distances).
    Adds `log` = log(d_armA / d_S); keeps |log| >= min_abs, sorted by (slug, amp, search)."""
    out = []
    for r in rows:
        if finite_pos(r["d_armA"]) and finite_pos(r["d_S"]):
            lg = math.log(r["d_armA"] / r["d_S"])
            if abs(lg) >= min_abs:
                out.append({**r, "log": lg})
    return sorted(out, key=lambda r: (r["slug"], r["amp"], r["search"]))


def draw(pool, seed=SEED, quota=QUOTA, n=N_TRIALS):
    """The declared draw: shuffle the sorted pool; walk it, taking a direction when its band is
    unused and its amp's quota not full, until n. The catch trial is the next direction in the
    walk from an unused band (any amp); its position is drawn from trials 2..n+1.
    Returns (trials in page order, each with `kind` 'test' or 'catch')."""
    rng = random.Random(seed)
    order = sorted(pool, key=lambda r: (r["slug"], r["amp"], r["search"]))
    rng.shuffle(order)
    left, bands, picks = dict(quota), set(), []
    i = 0
    for i, r in enumerate(order):
        if len(picks) == n:
            break
        if r["band"] in bands or left.get(r["amp"], 0) <= 0:
            continue
        picks.append({**r, "kind": "test"})
        bands.add(r["band"])
        left[r["amp"]] -= 1
    if len(picks) < n:
        raise SystemExit(f"only {len(picks)} directions fit the draw; the bar is not lowered")
    catch = next((r for r in order[i:] if r["band"] not in bands), None)
    if catch is None:
        raise SystemExit("no band left for the catch trial")
    pos = rng.randint(1, n)                      # 0-based index 1..n = trials 2..n+1
    return picks[:pos] + [{**catch, "kind": CATCH}] + picks[pos:]


def letters(trials, seed=LETTER_SEED):
    """Per trial, {letter: option}. Test trials: arm A's letter at random but balanced (A on
    exactly half of the test trials, the positions shuffled with the seeded RNG), so a
    preference for a position cannot lean towards either arm; the catch trial: both are S."""
    n = sum(t["kind"] != CATCH for t in trials)
    on_a = [True] * (n // 2) + [False] * (n - n // 2)
    random.Random(seed).shuffle(on_a)
    it = iter(on_a)
    return [{"A": "S", "B": "S"} if t["kind"] == CATCH else
            ({"A": "armA", "B": "S"} if next(it) else {"A": "S", "B": "armA"}) for t in trials]


def parse_answers(text):
    """'1A 2b 3S' -> {'1': 'A', '2': 'B', '3': 'S'}."""
    out = {}
    for tok in text.split():
        m = re.fullmatch(r"(\d+)([ABSabs?])", tok.strip())
        if not m:
            raise SystemExit(f"cannot read answer {tok!r}")
        if m.group(2) != "?":
            out[m.group(1)] = m.group(2).upper()
    return out


def outcome(trial, answer):
    """'armA', 'S' or 'same' for a test trial; for the catch trial 'same' or 'letter'; None if
    unanswered."""
    if answer is None:
        return None
    if answer == "S":
        return "same"
    if trial["kind"] == CATCH:
        return "letter"
    return trial["letters"][answer]


def _binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(k, n, conf=CONF):
    """Exact two-sided binomial interval (equal tails), by bisection."""
    if n == 0:
        return (0.0, 1.0)
    a = (1 - conf) / 2

    def solve(f):                                # f increasing in p; root of f(p) = 0
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
        return (lo + hi) / 2

    lower = 0.0 if k == 0 else solve(lambda p: (1 - _binom_cdf(k - 1, n, p)) - a)
    upper = 1.0 if k == n else solve(lambda p: a - _binom_cdf(k, n, p))
    return (lower, upper)


def score_key(key, answers):
    """The plan's reading from the key and parsed answers."""
    rows, per_amp = [], {}
    for n, t in sorted(key["trials"].items(), key=lambda x: int(x[0])):
        o = outcome(t, answers.get(n))
        judge_pref = None if t["kind"] == CATCH else ("armA" if t["judge_log"] < 0 else "S")
        rows.append({"trial": int(n), "kind": t["kind"], "slug": t["slug"], "amp": t["amp"],
                     "judge_log": t["judge_log"], "judge_prefers": judge_pref, "answer": answers.get(n),
                     "outcome": o, "agrees_with_judge": (o == judge_pref) if o in ("armA", "S") else None})
        if t["kind"] != CATCH:
            c = per_amp.setdefault(t["amp"], {"armA": 0, "S": 0, "same": 0, "unanswered": 0})
            c[o or "unanswered"] += 1
    tests = [r for r in rows if r["kind"] != CATCH]
    k = sum(r["outcome"] == "armA" for r in tests)
    decided = sum(r["outcome"] in ("armA", "S") for r in tests)
    answered = sum(r["outcome"] is not None for r in tests)
    lo, hi = clopper_pearson(k, decided)
    lo2, hi2 = clopper_pearson(k, answered)
    agree = [r["agrees_with_judge"] for r in tests if r["agrees_with_judge"] is not None]
    catch = next((r for r in rows if r["kind"] == CATCH), None)
    return {"trials": rows,
            "armA_share": {"k": k, "n": decided, "share": k / decided if decided else None, "ci90": [lo, hi]},
            "same": sum(r["outcome"] == "same" for r in tests),
            "armA_share_same_as_not": {"k": k, "n": answered, "share": k / answered if answered else None,
                                       "ci90": [lo2, hi2]},
            "judge_agreement": {"agree": sum(agree), "n": len(agree)},
            "per_amp": per_amp,
            "catch": None if catch is None else {"trial": catch["trial"], "outcome": catch["outcome"]}}


# --- data (zero renders) ---------------------------------------------------------------------------

def scored_rows():
    """The 142 scored directions with arm A's (3-C′ shrunk halfway) and S's held-half distances,
    gathered and dropped as `arm_a_levers.cmd_report_3` does."""
    from learn import arm_a_levers as L

    units = L.gathered_units()
    for u in units:
        u["d"]["3-C'"] = L._held_from(L.OUT / "early" / "C'", u)
        u["d"][LEVER] = L._held_from(L.OUT / "early" / LEVER, u)
    base, _ = L.drop(units, ("3-C'",))
    return [{"slug": u["slug"], "band": u["band"], "cls": u["cls"], "amp": u["amp"], "search": u["search"],
             "held": u["held"], "d_armA": u["d"][LEVER], "d_S": u["d"]["S"]} for u in base]


# --- the page --------------------------------------------------------------------------------------

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Listening check</title>
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
<h1>Which is closer to the record?</h1>
<p class="muted">{count} trials. In each, play the <b>Record</b>, then A and B. Every clip is the
same 4.5 seconds of guitar, at the same loudness. Pick the one that sounds closer to the record.
Some trials may have two identical options; if A and B sound the same to you, pick
<b>Same</b>. Guess if unsure. Headphones help.</p>
{trials}
<h2>Your answers</h2>
<p class="muted">Copy this line and send it back (S = Same).</p>
<div id="line">—</div>
<script>
const key = "arm-a-listen-{build}";
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


def _out():
    from learn import knob_ceiling as K

    return K.HOME / "listening" / "arm-a-1"


def build(args):
    import numpy as np

    from learn import arm_a_levers as L
    from learn import build_knob_listening as B
    from learn import confirm_run as CR
    from learn import knob_ceiling as K
    from learn.di_fine_structure import TRIM_S
    from learn.phase2_set3 import SR

    out_dir = _out()
    if (out_dir / "private" / "key.json").exists() and not args.force:
        raise SystemExit(f"{out_dir / 'private' / 'key.json'} exists; pass --force to rebuild")
    pool = eligible(scored_rows())
    trials = draw(pool)
    lets = letters(trials)
    for t in trials:
        assert K.R.HALVES[t["held"]][0] >= TRIM_S
    print(f"eligible {len(pool)}; trials:", flush=True)
    for n, (t, ls) in enumerate(zip(trials, lets), 1):
        print(f"  {n} {t['kind']:5s} {t['slug']} {t['amp']} search {t['search']} held {t['held']} "
              f"judge log {t['log']:+.3f} letters {ls}", flush=True)
    ps = K.parts()
    ms = L.menu_S()
    rr = K.Renderer()
    key = {"plan": "docs/arm-a-listening-plan.md", "seed": SEED, "letter_seed": LETTER_SEED,
           "lever": LEVER, "min_abs_log": MIN_ABS_LOG, "eligible": len(pool), "trials": {}}
    sections = []
    try:
        menu = rr.menu()
        with tempfile.TemporaryDirectory() as tmp:
            for n, (t, ls) in enumerate(zip(trials, lets), 1):
                slug, amp, search, held = t["slug"], t["amp"], t["search"], t["held"]
                part = ps[slug]
                sel, S = menu[amp][K.START[part["gain_class"]][amp]]
                sel_b, S_b = ms[amp][part["gain_class"]]
                assert sel == sel_b and K.key(S) == K.key(S_b), f"S differs from menu_S for {slug} {amp}"
                stored = json.loads((L.OUT / "early" / LEVER / slug / amp / f"{search}.json").read_text())
                assert stored["held"] == held
                x = L._settings(L.OUT / "early" / LEVER / slug / amp / f"{search}.json")
                main = L._settings(L.OUT / "replay" / "armA" / slug / amp / f"{search}-main.json")
                assert K.key(x) == K.key(L.lever("shrink-0.5", K.space(amp, S), S, main)), \
                    f"stored settings differ from the recomputed lever for {slug} {amp} {search}"
                di = K.measure_di(part)
                di32 = di.astype(np.float32)
                ref_full = CR.mono(part["crop"] / "reference.wav")
                rr.render(di32, sel, S)                                       # warm-up
                renders = {"S": rr.render(di32, sel, S)}
                if t["kind"] != CATCH:
                    renders["armA"] = rr.render(di32, sel, x)
                rejudge = {}
                for name, y in renders.items():
                    j = K.judge(ref_full, y, di, part["judge_lag"])[held]
                    want = t["d_armA"] if name == "armA" else t["d_S"]
                    rejudge[name] = abs(math.log(j / want)) if finite_pos(j) else math.inf
                ref = B.fade(B.level(B.clip(ref_full, held)))
                rows = [f'<div class="row"><b>Record</b><audio controls preload="none" '
                        f'src="{B.aac(ref, tmp)}"></audio></div>']
                for L_, name in ls.items():
                    y = np.asarray(renders[name], np.float64).copy()
                    y[:int(TRIM_S * SR)] = 0                                   # the isolate fade-in
                    clip = B.fade(B.level(B.clip(y, held)))
                    rows.append(f'<div class="row"><b>{L_}</b><audio controls preload="none" '
                                f'src="{B.aac(clip, tmp)}"></audio></div>')
                buttons = "".join(f'<button type="button" data-value="{v}">{lab}</button>'
                                  for v, lab in (("A", "A"), ("B", "B"), ("S", "Same")))
                sections.append(f'<section><h2>Trial {n}</h2>{"".join(rows)}'
                                f'<div class="pick" data-trial="{n}">{buttons}</div></section>')
                key["trials"][str(n)] = {"kind": t["kind"], "slug": slug, "band": t["band"], "cls": t["cls"],
                                         "amp": amp, "search": search, "held": held, "letters": ls,
                                         "judge_held": {"armA": t["d_armA"], "S": t["d_S"]},
                                         "judge_log": t["log"], "rejudge_abs_log": rejudge}
                print(n, t["kind"], slug, amp, "rejudge", {k: round(v, 5) for k, v in rejudge.items()},
                      flush=True)
        key["renders"] = rr.count
    finally:
        rr.close()
    build_id = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:12]
    page = PAGE.format(count=len(sections), build=build_id, trials="\n".join(sections))
    text = re.sub(r"base64,[A-Za-z0-9+/=]+", "", page).lower()
    for word in {t["slug"] for t in trials} | {t["band"] for t in trials} | \
            {"pr12", "sw50r", "ac20", "factory", "arm a", "shrink", "catch trial"}:
        assert word.lower() not in text, word
    (out_dir / "private").mkdir(parents=True, exist_ok=True)
    old = out_dir / "private" / "key.json"
    if old.exists():                       # keep earlier builds' keys
        old.rename(old.with_name(f"key-{int(old.stat().st_mtime)}.json"))
    old.write_text(json.dumps(key, indent=1))
    page_path = out_dir / "arm-a-listening.html"
    page_path.write_text(page)
    worst = max(v for t in key["trials"].values() for v in t["rejudge_abs_log"].values())
    print(page_path, f"{page_path.stat().st_size / 1e6:.1f} MB", "renders", key["renders"],
          "worst rejudge |log|", round(worst, 5),
          "key sha256", hashlib.sha256(old.read_bytes()).hexdigest())


def score(args):
    out_dir = _out()
    key = json.loads((out_dir / "private" / "key.json").read_text())
    rep = score_key(key, parse_answers(args.answers))
    for r in rep["trials"]:
        print(f"{r['trial']} {r['kind']:5s} {r['slug']} {r['amp']} judge {r['judge_log']:+.3f} "
              f"answer {r['answer']} -> {r['outcome']}")
    s, s2 = rep["armA_share"], rep["armA_share_same_as_not"]
    if s["n"]:
        print(f"arm A chosen {s['k']}/{s['n']} = {s['share']:.2f}, 90% [{s['ci90'][0]:.2f}, {s['ci90'][1]:.2f}]")
    print(f"same on {rep['same']} test trial(s); with same as not-arm-A: {s2['k']}/{s2['n']}"
          + (f", 90% [{s2['ci90'][0]:.2f}, {s2['ci90'][1]:.2f}]" if s2["n"] else ""))
    print("agrees with judge sign:", rep["judge_agreement"])
    print("per amp:", rep["per_amp"])
    print("catch trial:", rep["catch"])
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
