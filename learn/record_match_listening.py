"""Record-match listening check 1 (`docs/record-match-listening-plan.md`): does the held-half judge
rank presets the way the ear does? Development only; descriptive.

    .venv/bin/python -m learn.record_match_listening choose                  # zero renders
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.record_match_listening render --shard i/3
    .venv/bin/python -m learn.record_match_listening build
    .venv/bin/python -m learn.record_match_listening score --answers "1 B>D>A>C very; 2 ..."

Five stage-F parts, one direction each. Per part: S, H (arm A's stored answer), D (the existing
direct model's stored answer) and C (a 150-render K_S-style knob search through the true raw DI
against the amp track on the search half), all rendered through the raw DI and played on the held
half beside the record. The listener ranks the four; `score` maps ranks to arms and sets them
beside the judge's held-half ranking.

The pure parts (the choice rule, the trial draw, the answer parser, the scoring) are unit-tested
(`tests/test_record_match_listening.py`); the commands that render are not, like the other steps.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
import re
import sys
import tempfile

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "listening" / "record-match-1"
PRIVATE = OUT / "private"
DIRECT = HOME / "learn" / "direct-existing"
ARMS = ("S", "H", "D", "C")
LETTERS = ("A", "B", "C", "D")
N_PARTS = 5
CLASS_MAX = 3
ACTIVE_MIN = 0.8
ACTIVE_DB = 25.0
BAD_FLAGS = ("moderate", "high")
HELD_SEED = 20261019
PAGE_SEED = 20261020
C_BUDGET = 150                       # knob_ceiling.BUDGET["K_S"]
TOL = 0.005                          # |log| repeat tolerance
CLOSE = ("very", "some", "not")
EXPECTED = ("cambridge-Signs-ElecGtr3", "cambridge-get-out-of-bed-elecgtr2", "telefunken-Gym_Hours-GTR_2",
            "cambridge-Today's_The_Day-ElecGtr07", "cambridge-magilla-elecgtr1")


# --- pure functions (unit-tested) ------------------------------------------------------------------

def choose(rows, s_raw, seed=HELD_SEED):
    """rows: [{slug, band, cls, snr, flags: {A, B}, act: {A, B}}]; s_raw: {slug: {amp: {A, B}}}
    (S's raw-DI judge). -> [{slug, band, cls, held, search, amp}] in walk order (plan, the rule)."""
    ok = [r for r in rows if not any(r["flags"][h] in BAD_FLAGS for h in "AB")
          and max(r["act"].values()) >= ACTIVE_MIN]
    ok.sort(key=lambda r: (-r["snr"], r["slug"]))
    rng, bands, n_cls, out = random.Random(seed), set(), {}, []
    for r in ok:
        if r["band"] in bands or n_cls.get(r["cls"], 0) >= CLASS_MAX:
            continue
        bands.add(r["band"])
        n_cls[r["cls"]] = n_cls.get(r["cls"], 0) + 1
        a, b = r["act"]["A"], r["act"]["B"]
        held = "A" if a > b else "B" if b > a else rng.choice("AB")
        search = "B" if held == "A" else "A"
        amp = min(sorted(s_raw[r["slug"]]), key=lambda m: s_raw[r["slug"]][m][search])
        out.append({"slug": r["slug"], "band": r["band"], "cls": r["cls"], "held": held, "search": search,
                    "amp": amp})
        if len(out) == N_PARTS:
            break
    if len(out) < N_PARTS or min(n_cls.values()) < 2 or len(n_cls) < 2:
        raise SystemExit(f"the rule found {len(out)} parts, classes {n_cls}")
    return out


def draw(parts, seed=PAGE_SEED):
    """Page trials: the parts shuffled, each with letters {A..D: arm}, then a repeat of one of
    trials 1-4 with a fresh letter order."""
    rng = random.Random(seed)
    order = list(parts)
    rng.shuffle(order)
    trials = []
    for p in order:
        arms = list(ARMS)
        rng.shuffle(arms)
        trials.append({"slug": p["slug"], "repeat_of": None, "letters": dict(zip(LETTERS, arms))})
    src = rng.randrange(len(trials) - 1)
    while True:
        arms = list(ARMS)
        rng.shuffle(arms)
        if dict(zip(LETTERS, arms)) != trials[src]["letters"]:
            break
    trials.append({"slug": trials[src]["slug"], "repeat_of": src + 1, "letters": dict(zip(LETTERS, arms))})
    return trials


ANSWER_RE = re.compile(r"(\d+)\s+([A-D?](?:\s*>\s*[A-D?]){3})\s+(very|some|not|\?)", re.I)


def parse_answers(text):
    """'1 B>D>A>C very; 2 ?>?>?>? ?' -> {1: (['B','D','A','C'], 'very'), 2: (None, None)}."""
    out = {}
    for m in ANSWER_RE.finditer(text):
        order = [x.strip().upper() for x in m.group(2).split(">")]
        ok = "?" not in order and len(set(order)) == 4
        close = m.group(3).lower()
        out[int(m.group(1))] = (order if ok else None, None if close == "?" else close)
    if not out and text.strip():
        raise SystemExit(f"cannot read {text!r} (expected like '1 B>D>A>C very; 2 A>C>B>D some')")
    return out


def ranks(values):
    """Average ranks, 1 = smallest."""
    idx = sorted(range(len(values)), key=lambda i: values[i])
    r = [0.0] * len(values)
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and values[idx[j + 1]] == values[idx[i]]:
            j += 1
        for k in range(i, j + 1):
            r[idx[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else None


def arm_ranks(trial, order):
    """The listener's order of letters -> {arm: rank}."""
    return {trial["letters"][L]: i + 1 for i, L in enumerate(order)}


def score_key(key, answers):
    trials = {int(n): t for n, t in key["trials"].items()}
    rows = []
    for n, t in sorted(trials.items()):
        order, close = answers.get(n, (None, None))
        row = {"trial": n, "slug": t["slug"], "repeat_of": t["repeat_of"], "close": close, "order": order}
        if order:
            ar = arm_ranks(t, order)
            j = t["judge_held"]
            row.update(arm_ranks=ar, judge_ranks=dict(zip(ARMS, ranks([j[a] for a in ARMS]))),
                       rho=spearman([ar[a] for a in ARMS], [j[a] for a in ARMS]),
                       top=trial_top(t, order), judge_top=j[t["letters"][order[0]]], judge_C=j["C"])
        rows.append(row)
    main = [r for r in rows if r["repeat_of"] is None and r["order"]]
    rep = {"trials": rows, "answered": len(main)}
    rep["mean_rank"] = {a: (sum(r["arm_ranks"][a] for r in main) / len(main) if main else None) for a in ARMS}
    rep["beats_S"] = {a: sum(r["arm_ranks"][a] < r["arm_ranks"]["S"] for r in main) for a in ("C", "H", "D")}
    rhos = [r["rho"] for r in main if r["rho"] is not None]
    rep["rho_mean"] = sum(rhos) / len(rhos) if rhos else None
    rep["rho_positive"] = sum(x > 0 for x in rhos)
    rep["close"] = {c: sum(r["close"] == c for r in rows if r["repeat_of"] is None) for c in CLOSE}
    for r in rows:
        if r["repeat_of"] is not None and r["order"]:
            first = next((x for x in rows if x["trial"] == r["repeat_of"]), None)
            if first and first["order"]:
                rep["repeat"] = {"rho": spearman([first["arm_ranks"][a] for a in ARMS],
                                                 [r["arm_ranks"][a] for a in ARMS]),
                                 "same_close": first["close"] == r["close"],
                                 "same_top": first["top"] == r["top"]}
    return rep


def trial_top(t, order):
    return t["letters"][order[0]]


# --- inputs ----------------------------------------------------------------------------------------

def choice_rows():
    """The rule's inputs: stage F's parts with class, band, stored htdemucs SNR, bleed flags and
    the record's activity per half; S's stored raw-DI judges per amp."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR
    from learn import local_objective_1c as C1
    from learn import rescore as R

    bt = C1.load_bleed_table()
    snr = json.loads((A.OUT / "report-F.json").read_text())["snr_db_htdemucs_instrumental"]
    rows, s_raw = [], {}
    for s in A.pool_slugs():
        p = A.f_part(s)
        ref = CR.mono(p["crop"] / "reference.wav")
        fr = int(0.1 * A.SR)
        db = np.array([20 * np.log10(np.sqrt(np.mean(ref[i:i + fr] ** 2)) + 1e-12)
                       for i in range(0, len(ref) - fr, fr)])
        act = {h: float(np.mean(db[int(a * 10):int(b * 10)] > db.max() - ACTIVE_DB)) for h, (a, b) in R.HALVES.items()}
        rows.append({"slug": s, "band": p["band"], "cls": p["gain_class"], "snr": snr[s], "act": act,
                     "flags": {h: bt[s]["halves"][h]["flag"] for h in "AB"}})
        s_raw[s] = {amp: json.loads((DIRECT / "groups" / f"{s}|{amp}.json").read_text())["raw"]["S"]
                    for amp in ("pr12", "sw50r", "ac20")}
    return rows, s_raw


def cmd_choose(_args):
    rows, s_raw = choice_rows()
    parts = choose(rows, s_raw)
    if tuple(p["slug"] for p in parts) != EXPECTED:
        raise SystemExit(f"the rule gave {[p['slug'] for p in parts]}, not the plan's")
    PRIVATE.mkdir(parents=True, exist_ok=True)
    (PRIVATE / "choice.json").write_text(json.dumps({"parts": parts, "rows": rows}, indent=1))
    for p in parts:
        print(p)


def _parts():
    return json.loads((PRIVATE / "choice.json").read_text())["parts"]


def raw_di(part):
    from learn import confirm_run as CR
    from learn.direc_check import to_lufs

    return to_lufs(CR.mono(part["crop"] / "di.wav"))


PEAK = 0.9
TARGET_LUFS = -20.0


def common_gains(lufs, peaks, target=TARGET_LUFS, peak=PEAK):
    """One loudness for every clip of a trial: -20 LUFS, or lower if a clip would peak above 0.9
    there. -> (the trial's LUFS, a linear gain per clip)."""
    t = min([target] + [l + 20 * math.log10(peak / p) for l, p in zip(lufs, peaks) if p > 0])
    return t, [10 ** ((t - l) / 20) for l in lufs]


def as_mono(y):
    """A render folded to mono, as the judge folds it (`analysis.aligned`), like the mono record."""
    import numpy as np

    y = np.asarray(y, np.float64)
    return y.mean(axis=1) if y.ndim == 2 else y


def trim(y, s=0.25, sr=48000):
    y = y.copy()
    y[:int(s * sr)] = 0.0
    return y


class PartStopped(Exception):
    """A plumbing check failed: that part stops, the shard goes on."""


def render_part(rr, menu, ms, c):
    """C's search on the search half, then S, H, D and C's best, all through the raw DI. Priming
    renders after the process start and every DI or amp change."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    slug, amp, search, held = c["slug"], c["amp"], c["search"], c["held"]
    path = PRIVATE / "renders" / f"{slug}.json"
    if path.exists() and json.loads(path.read_text()).get("status") == "done":
        return
    ctx = A.group_ctx(menu, ms, "F", slug, amp)
    if K.key(dict(ctx["S"])) != K.key(ctx["S_stored"]):
        raise SystemExit(f"{amp}: the live S differs from the stored copy")
    part, sel, S, ref, lag = ctx["part"], ctx["sel"], ctx["S"], ctx["ref"], ctx["part"]["judge_lag"]
    di = raw_di(part)
    di32 = di.astype(np.float32)
    n0 = rr.count
    rr.render(di32, sel, S)                                                 # priming, discarded
    evals = []
    stored = json.loads((DIRECT / "groups" / f"{slug}|{amp}.json").read_text())["raw"]

    def f(x):
        d = K.judge(ref, rr.render(di32, sel, x), di, lag)
        evals.append({"x": LO.sdict(x), "d": d})
        if len(evals) == 1:                                                # the first evaluation is S
            dev = max(LO.deviation(d[h], stored["S"][h]) for h in "AB")
            if dev > TOL:
                raise PartStopped(f"{slug}: S's raw judge moved {dev:.4f} from direct-existing's")
        return d[search]

    cx, cbest, _, stages = K.knob_search(K.space(amp, S), S, f, C_BUDGET, K.SEED)
    n_search = rr.count - n0 - 1
    h_ = json.loads(A.result_path("F", "H", slug, amp, search).read_text())
    pred = json.loads((DIRECT / "predictions.json").read_text())["predictions"][f"{slug}|{amp}|{search}"]
    settings = {"S": dict(S), "H": LO.tdict(h_["settings"]["output"]), "D": LO.tdict(pred["settings"]), "C": cx}
    judge, audio = {}, {}
    for arm in ARMS:
        y = rr.render(di32, sel, settings[arm])
        judge[arm] = K.judge(ref, y, di, lag)
        a, b = K.R.HALVES[held]
        audio[arm] = trim(y)[int(a * A.SR):int(b * A.SR)]
    devs = {"S": LO.deviation(judge["S"][held], stored["S"][held]),
            "H": LO.deviation(judge["H"][held], stored[f"H|{search}"][held]),
            "D": LO.deviation(judge["D"][held], stored[f"D|{search}"][held]),
            "C": LO.deviation(judge["C"][search], cbest)}
    rec = {"slug": slug, "amp": amp, "search": search, "held": held, "judge": judge, "devs": devs,
           "c_stages": stages, "c_search_renders": n_search, "settings": {k: LO.sdict(v) for k, v in settings.items()},
           "renders": rr.count - n0, "evals": evals}
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path.with_suffix(".npz"), **audio)
    rec["status"] = "done" if max(devs.values()) <= TOL else "stopped"
    path.write_text(json.dumps(rec, indent=1))
    print(slug, amp, "held", held, {a: round(judge[a][held], 4) for a in ARMS}, "devs",
          {a: round(v, 5) for a, v in devs.items()}, "renders", rec["renders"], flush=True)
    if rec["status"] != "done":
        raise PartStopped(f"{slug}: repeat check failed {devs}")


def cmd_render(args):
    from learn import arm_a_mega53 as A
    from learn import local_objective as LO

    i, n = (int(x) for x in args.shard.split("/"))
    mine = [c for k, c in enumerate(_parts()) if k % n == i]
    if not LO.disk_ok(LO.disk_free_gb(), 0):
        raise SystemExit("free disk below the 31 GB guard")
    LO._wait_cap()
    rr = A.renderer()
    try:
        menu, ms = rr.menu(), A.L.menu_S()
        for c in mine:
            if not LO.disk_ok(LO.disk_free_gb(), 0):
                raise SystemExit("free disk below the 31 GB guard")
            try:
                render_part(rr, menu, ms, c)
            except PartStopped as e:
                print("STOPPED", e, flush=True)
    finally:
        rr.close()


# --- the page --------------------------------------------------------------------------------------

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Record match check</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e3e0d8; --card:#fff; --acc:#2d5bd7; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#161614; --fg:#ecebe6; --muted:#a3a29c;
  --line:#33322e; --card:#1f1f1c; --acc:#7da0ff; }} }}
body {{ background:var(--bg); color:var(--fg); font:16px/1.45 -apple-system,system-ui,sans-serif;
  margin:0 auto; max-width:720px; padding:16px; }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 14px;
  margin:14px 0; }}
.row {{ display:flex; align-items:center; gap:10px; margin:6px 0; }}
.row b {{ width:4.5em; flex:none; }} audio {{ width:100%; }}
.q {{ margin:10px 0 2px; }}
.pick {{ display:flex; flex-wrap:wrap; align-items:center; }}
.pick span {{ width:5.5em; color:var(--muted); }}
.pick button {{ font-size:16px; padding:8px 14px; margin:4px 6px 0 0; border-radius:8px;
  border:1px solid var(--line); background:var(--bg); color:var(--fg); }}
.pick button.on {{ background:var(--acc); color:#fff; border-color:var(--acc); }}
#line {{ font:15px ui-monospace,monospace; padding:10px; border:1px dashed var(--line); border-radius:8px;
  word-break:break-all; }} .muted {{ color:var(--muted); }}
</style></head><body>
<h1>Which preset sounds most like the record?</h1>
<p class="muted">{count} trials. Each plays the same 4.5 seconds: <b>Record</b> is the guitar as it was
recorded, on its own. A, B, C and D are presets played with the same performance, at the same loudness.
Their timing and performance may differ a little from the Record; ignore that and listen to the
<b>tone</b>. Headphones help; guess if unsure.</p>
<p class="muted">For each trial: <b>rank A–D</b> from closest to furthest from the Record's guitar tone
(pick a letter on each line), and say <b>how close the closest one is</b>.</p>
{trials}
<h2>Your answers</h2>
<p class="muted">Copy this line and send it back. Each trial reads closest first, then the closeness
(very, some or not), for example <code>1 B&gt;D&gt;A&gt;C very</code>. A ? marks something not yet answered.</p>
<div id="line">—</div>
<script>
const key = "record-match-{build}";
let a = {{}}; try {{ a = JSON.parse(localStorage.getItem(key) || "{{}}"); }} catch (e) {{}}
const trials = [...new Set([...document.querySelectorAll(".pick")].map(p => p.dataset.trial))];
function show() {{
  document.querySelectorAll(".pick").forEach(p => p.querySelectorAll("button").forEach(b =>
    b.classList.toggle("on", (a[p.dataset.trial] || {{}})[p.dataset.q] === b.dataset.value)));
  document.getElementById("line").textContent = trials.map(t => {{
    const r = a[t] || {{}};
    return t + " " + [1, 2, 3, 4].map(i => r["r" + i] || "?").join(">") + " " + (r.close || "?");
  }}).join("; ");
}}
document.querySelectorAll(".pick button").forEach(b => b.onclick = () => {{
  const p = b.parentElement, t = p.dataset.trial, q = p.dataset.q, v = b.dataset.value;
  const r = a[t] = a[t] || {{}};
  if (q.startsWith("r")) for (const k of ["r1", "r2", "r3", "r4"]) if (k !== q && r[k] === v) delete r[k];
  r[q] = v;
  try {{ localStorage.setItem(key, JSON.stringify(a)); }} catch (e) {{}}
  show(); }});
document.querySelectorAll("audio").forEach(x => x.addEventListener("play", () =>
  document.querySelectorAll("audio").forEach(y => {{ if (y !== x) y.pause(); }})));
show();
</script></body></html>
"""

RANK_NAMES = ("Closest", "2nd", "3rd", "Furthest")


def section(n, clips):
    rows = "".join(f'<div class="row"><b>{L}</b><audio controls preload="none" src="{src}"></audio></div>'
                   for L, src in clips)
    ranks_ = "".join(f'<div class="pick" data-trial="{n}" data-q="r{i + 1}"><span>{name}</span>'
                     + "".join(f'<button type="button" data-value="{L}">{L}</button>' for L in LETTERS)
                     + "</div>" for i, name in enumerate(RANK_NAMES))
    close = "".join(f'<button type="button" data-value="{v}">{lab}</button>'
                    for v, lab in (("very", "Very close"), ("some", "Somewhat"), ("not", "Not close")))
    return (f'<section><h2>Trial {n}</h2>{rows}'
            f'<div class="q">Rank A–D, closest to the Record first:</div>{ranks_}'
            f'<div class="q">How close is the closest?</div>'
            f'<div class="pick" data-trial="{n}" data-q="close">{close}</div></section>')


def leak_words(parts):
    words = {p["slug"] for p in parts} | {p["band"] for p in parts}
    for p in parts:
        words |= {w for w in re.split(r"[-_ ]+", p["slug"]) if len(w) > 4}
    return words | {"telefunken", "cambridge", "elecgtr", "gtr_", "pr12", "sw50r", "ac20", "factory:",
                    "royally", "americana", "hair metal", "mid-gain", "pedal platform", "modern metal",
                    "\"s\"", "\"h\"", "ceiling", "direct model", "arm a"}


def build(args):
    import numpy as np

    from learn import build_bleed_damage as BD
    from learn import build_knob_listening as BK
    from learn import confirm_run as CR
    from learn import local_objective as LO
    from learn import rescore as R

    if (PRIVATE / "key.json").exists() and not args.force:
        raise SystemExit(f"{PRIVATE / 'key.json'} exists; pass --force to rebuild")
    parts = {p["slug"]: p for p in _parts()}
    recs = {s: json.loads((PRIVATE / "renders" / f"{s}.json").read_text()) for s in parts}
    if any(r.get("status") != "done" for r in recs.values()):
        raise SystemExit("render every part first")
    from learn import arm_a_mega53 as A

    trials = draw(list(parts.values()))
    key = {"plan": "docs/record-match-listening-plan.md", "seed": PAGE_SEED, "trials": {}}
    sections = []
    with tempfile.TemporaryDirectory() as tmp:
        enc = lambda x: BD.pad(BK.aac(BK.fade(x), tmp))
        for n, t in enumerate(trials, 1):
            p, rec = parts[t["slug"]], recs[t["slug"]]
            a, b = R.HALVES[p["held"]]
            ref = CR.mono(A.f_part(p["slug"])["crop"] / "reference.wav")[int(a * A.SR):int(b * A.SR)]
            audio = np.load(PRIVATE / "renders" / f"{p['slug']}.npz")
            raw = {"Record": np.asarray(ref, np.float64), **{arm: as_mono(audio[arm]) for arm in ARMS}}
            names = list(raw)
            target, gains = common_gains([LO.lufs(raw[k]) for k in names], [float(np.abs(raw[k]).max()) for k in names])
            lev = {k: raw[k] * g for k, g in zip(names, gains)}
            spread = max(abs(LO.lufs(v) - target) for v in lev.values())
            assert spread < 0.1, (t["slug"], spread)
            clips = [("Record", enc(lev["Record"]))] + [(L, enc(lev[arm])) for L, arm in t["letters"].items()]
            sections.append(section(n, clips))
            key["trials"][str(n)] = {**t, "amp": p["amp"], "held": p["held"], "band": p["band"], "cls": p["cls"],
                                     "judge_held": {arm: rec["judge"][arm][p["held"]] for arm in ARMS},
                                     "lufs": target, "level_spread_lu": spread}
            print(f"  {n} {p['slug']} {p['amp']} held {p['held']} letters {t['letters']}", flush=True)
    build_id = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:12]
    page = PAGE.format(count=len(sections), build=build_id, trials="\n".join(sections))
    check_page(page, parts.values(), len(sections))
    PRIVATE.mkdir(parents=True, exist_ok=True)
    (PRIVATE / "key.json").write_text(json.dumps(key, indent=1))
    path = OUT / "record-match.html"
    path.write_text(page)
    print(path, f"{path.stat().st_size / 1e6:.2f} MB")


def check_page(page, parts, n_trials):
    text = re.sub(r"base64,[A-Za-z0-9+/=]+", "", page).lower()
    for w in leak_words(list(parts)):
        assert w.lower() not in text, w
    uris = re.findall(r'src="(data:[^"]+)"', page)
    assert len(uris) == 5 * n_trials and len(set(uris)) == len(uris), "duplicate clip bytes"
    assert len({len(u) for u in uris}) > len(uris) // 2, "clip sizes too uniform"


def score(args):
    key = json.loads((PRIVATE / "key.json").read_text())
    rep = score_key(key, parse_answers(args.answers))
    for r in rep["trials"]:
        extra = "" if not r["order"] else (f" arms {r['arm_ranks']} judge {r['judge_ranks']} rho {r['rho'] if r['rho'] is None else round(r['rho'], 2)}"
                                           f" top {r['top']} d_top {r['judge_top']:.3f} d_C {r['judge_C']:.3f}")
        print(f"{r['trial']}{' (repeat of ' + str(r['repeat_of']) + ')' if r['repeat_of'] else ''} {r['slug']}: "
              f"{'>'.join(r['order']) if r['order'] else '?'} {r['close']}{extra}")
    print("mean rank", {a: None if v is None else round(v, 2) for a, v in rep["mean_rank"].items()},
          f"(of {rep['answered']})")
    print("above S", rep["beats_S"], "| mean rho", None if rep["rho_mean"] is None else round(rep["rho_mean"], 2),
          f"rho > 0 in {rep['rho_positive']}", "| closeness", rep["close"])
    print("repeat", rep.get("repeat"))
    rep["answers"] = args.answers
    (PRIVATE / "score.json").write_text(json.dumps(rep, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("choose", "render", "build", "score"))
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--answers", default="")
    ap.add_argument("--force", action="store_true", help="build: rebuild over an existing key")
    a = ap.parse_args(argv)
    {"choose": cmd_choose, "render": cmd_render, "build": build, "score": score}[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
