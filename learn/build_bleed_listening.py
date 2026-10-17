"""Bleed listening check 1 (`docs/bleed-listening-plan.md`). Development only; descriptive.

    .venv/bin/python -m learn.build_bleed_listening build
    .venv/bin/python -m learn.build_bleed_listening score --answers "1A-no 2N-no 3B-little ..."

Can a listener hear the other-instrument bleed the 2026-10-16 audit measured in the amp tracks
(`docs/audits/bleed-2026-10-16/`), and does removing it damage the guitar? Five parts on one held
half each (three flagged high, two low controls), plus a repeat of one control with A = B, both
original. Per trial: the original amp track (`reference.wav`) and a cleaned one (the amp track
minus the audit's held-out bleed estimate, "clean" regressor set), in a seeded order.

Two questions per trial; the answer line reads "1A-no 2N-little 3Both-lot ...":
- which one has other instruments leaking in: A, B, N (neither) or Both;
- does either one's guitar sound damaged: no, little or lot.

Zero plugin renders. The key is written under `private/`, never in the page. The pure functions
(the draw, the letters, parsing and scoring) are unit-tested; the build reads audio and is not.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import random
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "audits" / "bleed-2026-10-16"
SEED = 20261016
LETTER_SEED = SEED + 1
HIGH = (("telefunken-Gym_Hours-GTR_1", "B"),
        ("telefunken-First_Offering-GTR_1", "A"),
        ("telefunken-Sculptor's_Request-GTR_1", "B"))
LOW = ("cambridge-Drag_Me_Down-ElecGtr4", "telefunken-Farthest_Step-GTR")
REPEAT = "repeat"
LEAK = ("A", "B", "N", "Both")
DAMAGE = ("no", "little", "lot")


# --- pure functions (unit-tested) ------------------------------------------------------------------

def draw(seed=SEED, high=HIGH, low=LOW):
    """The declared trials, in page order. Each control's half is drawn (sorted controls, one
    rng.choice('AB') each); the repeated control is drawn next; then the 6 trials are shuffled,
    reshuffling while the repeat is trial 1 or sits next to its control. Kinds: 'high', 'low', 'repeat'."""
    rng = random.Random(seed)
    trials = [{"slug": s, "held": h, "kind": "high"} for s, h in high]
    trials += [{"slug": s, "held": rng.choice("AB"), "kind": "low"} for s in sorted(low)]
    src = rng.choice([t for t in trials if t["kind"] == "low"])
    trials.append({**src, "kind": REPEAT})
    while True:
        rng.shuffle(trials)
        i = next(i for i, t in enumerate(trials) if t["kind"] == REPEAT)
        j = next(j for j, t in enumerate(trials) if t["kind"] == "low" and t["slug"] == src["slug"])
        if i > 0 and abs(i - j) > 1:
            return trials


def letters(trials, seed=LETTER_SEED):
    """Per trial, {letter: 'original' | 'cleaned'}. The cleaned clip's letter is balanced over
    the non-repeat trials (A on n//2 or n - n//2 of them, which one by a coin; positions
    shuffled); the repeat trial is original on both letters."""
    rng = random.Random(seed)
    n = sum(t["kind"] != REPEAT for t in trials)
    on_a = [True] * (n // 2) + [False] * (n - n // 2)
    if n % 2 and rng.random() < 0.5:
        on_a = [not x for x in on_a]
    rng.shuffle(on_a)
    it = iter(on_a)
    return [{"A": "original", "B": "original"} if t["kind"] == REPEAT else
            ({"A": "cleaned", "B": "original"} if next(it) else {"A": "original", "B": "cleaned"})
            for t in trials]


ANSWER_RE = re.compile(r"(\d+)(both|a|b|n|\?)-(no|little|lot|alot|a-lot|\?)", re.I)


def parse_answers(text):
    """'1A-no 2N-little 3Both-lot 4?-?' -> {'1': ('A', 'no'), '2': ('N', 'little'),
    '3': ('Both', 'lot'), '4': (None, None)}. 'a lot' may be written lot, alot or a-lot."""
    out = {}
    for tok in text.replace("a lot", "lot").split():
        m = ANSWER_RE.fullmatch(tok.strip())
        if not m:
            raise SystemExit(f"cannot read answer {tok!r} (expected like 1A-no, 2Both-little, 3N-lot)")
        leak = {"a": "A", "b": "B", "n": "N", "both": "Both", "?": None}[m.group(2).lower()]
        dmg = m.group(3).lower()
        dmg = None if dmg == "?" else ("lot" if dmg in ("alot", "a-lot") else dmg)
        out[m.group(1)] = (leak, dmg)
    return out


def leak_role(trial, leak):
    """What the leak answer names: 'original', 'cleaned', 'both', 'neither', for the repeat
    trial 'a letter' when A or B was named (both are the same clip); None if unanswered."""
    if leak is None:
        return None
    if leak == "N":
        return "neither"
    if leak == "Both":
        return "both"
    if trial["kind"] == REPEAT:
        return "a letter"
    return trial["letters"][leak]


def score_key(key, answers):
    """The plan's descriptive reading from the key and parsed answers."""
    rows = []
    for n, t in sorted(key["trials"].items(), key=lambda x: int(x[0])):
        leak, dmg = answers.get(n, (None, None))
        rows.append({"trial": int(n), "kind": t["kind"], "slug": t["slug"], "held": t["held"],
                     "bleed_removed_db": t.get("bleed_removed_db"), "leak": leak,
                     "leak_names": leak_role(t, leak), "damage": dmg})
    counts = {}
    for kind in ("high", "low"):
        c = {k: 0 for k in ("original", "cleaned", "both", "neither", "unanswered")}
        d = {k: 0 for k in (*DAMAGE, "unanswered")}
        for r in rows:
            if r["kind"] == kind:
                c[r["leak_names"] or "unanswered"] += 1
                d[r["damage"] or "unanswered"] += 1
        counts[kind] = {"leak": c, "damage": d}
    rep = next((r for r in rows if r["kind"] == REPEAT), None)
    pair = None
    if rep is not None:
        src = next(r for r in rows if r["kind"] == "low" and r["slug"] == rep["slug"] and r["held"] == rep["held"])
        pair = {"repeat_trial": rep["trial"], "control_trial": src["trial"],
                "repeat": {"leak": rep["leak_names"], "damage": rep["damage"]},
                "control": {"leak": src["leak_names"], "damage": src["damage"]}}
    return {"trials": rows, "high": counts["high"], "low": counts["low"], "repeat": pair}


# --- the bleed estimate (zero renders) -------------------------------------------------------------

def _bleed4():
    spec = importlib.util.spec_from_file_location("bleed4", AUDIT / "bleed4.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out4 = AUDIT / "out4"                          # bleed4 creates it on import; leave no trace
    if out4.is_dir() and not any(out4.iterdir()):
        out4.rmdir()
    return mod


def bleed_estimate(slug, crop, held):
    """The audit's held-out bleed estimate for `held`, as a 48 kHz signal aligned with the crop's
    reference.wav, plus checks. Exactly bleed4's real pass: own-DI stage (fit on the context minus
    the held half), mics decontaminated of the own DI, the "clean" regressor set, one complex
    weight per 4-bin band. The per-frame estimate X_clean w is overlap-added over every frame
    touching the held half (window-sum normalised) and upsampled 24 -> 48 kHz."""
    import numpy as np
    from scipy import signal

    B4 = _bleed4()
    P = B4.Part(slug, crop)
    groups = P.groups
    mic_idx = [cs[0] for _, k, cs in groups if k == "mic"]
    cols = P.columns(None)
    acc, _ = P.accumulate(cols, keep=())
    osh = B4.own_share(acc)
    a, b = B4.HALVES[held]
    i0 = P.start - P.c0 + int(a * B4.SR)
    i1 = P.start - P.c0 + int(b * B4.SR)
    st = P.starts[(P.starts + B4.NFFT > i0 - B4.HOP) & (P.starts < i1 + B4.HOP)]
    X = B4.stft_at(cols, st)
    Y = B4.stft_at(P.y[None], st)[..., 0]
    del cols
    accd, kp, share = B4.decontaminate(acc, {"F": (X, Y)}, mic_idx, P.P)
    del acc, X
    shares = {groups[i][0]: share[cs[0]] for i, (_, k, cs) in enumerate(groups) if k == "mic"}
    risk = {n: B4.db(max(v, 0)) + B4.db(max(1 - osh, 1e-9)) for n, v in shares.items()}
    clean = [i for i, (n, k, _) in enumerate(groups) if k == "di" or risk[n] <= B4.PROXY_DB]
    excluded = sorted(groups[i][0] for i in range(len(groups)) if groups[i][1] == "mic" and i not in clean)

    # evaluate()'s held-out fit for the clean set
    Fi = list(range(B4.NOWN))
    DN = np.real(np.einsum("bii->bi", B4.add(*accd.values())[0]))
    other = "B" if held == "A" else "A"
    tr = B4.add(accd["C"], accd[other])
    te = accd[held]
    E = float(te[2].sum())
    wF = B4.solve(tr[0], tr[1], Fi, dn=DN)
    e_nl = B4.res_energy(te, wF, Fi)
    Oi = [c for i in clean for c in groups[i][2]]
    G = tr[0]
    bR = tr[1] - np.einsum("bpf,bf->bp", G[:, :, Fi], wF)
    wb = B4.expand(B4.solve(B4.pool(G), B4.pool(bR), Oi, alpha=B4.ALPHA_B, dn=B4.pool(DN)))
    e = B4.res_energy(te, np.concatenate([wF, wb], 1), Fi + Oi)
    gain = (e_nl - e) / E                                  # the audit's held-out gain (before the null)
    comp = B4.quad(te[0], wb, Oi) / E                      # bleed component energy / amp track energy

    Xd = kp["F"][0]
    Bf = np.einsum("btp,bp->bt", Xd[:, :, Oi], wb)        # NB x frames
    seg = np.fft.irfft(Bf.T, n=B4.NFFT, axis=-1)           # frames x NFFT (windowed segments)
    lo = int(st[0])
    n = int(st[-1]) + B4.NFFT - lo
    ola, wsum = np.zeros(n), np.zeros(n)
    for k, s in enumerate(st):
        ola[s - lo:s - lo + B4.NFFT] += seg[k]
        wsum[s - lo:s - lo + B4.NFFT] += B4.WIN
    bl24 = ola / np.maximum(wsum, 1e-3)
    bl48 = signal.resample_poly(bl24, 2, 1)
    # 24 kHz context index j is absolute 48 kHz sample 2 (c0 + j); the crop starts at s48
    off = P.rec["excerpt_start_frame"] - 2 * (P.c0 + lo)
    return {"bleed48": bl48, "offset": off, "gain": gain, "comp": comp, "E": E,
            "excluded": excluded, "n_clean": len(clean), "groups": len(groups), "crop_check": P.chk,
            "own_share": osh}


def bleed_in_crop(est, a, b):
    """The estimate cut to crop samples [a*SR, b*SR) (zeros where it does not reach)."""
    import numpy as np

    from learn import phase2_set3 as P

    i0, i1 = int(a * P.SR), int(b * P.SR)
    out = np.zeros(i1 - i0)
    src0 = est["offset"] + i0
    lo = max(0, -src0)
    hi = min(i1 - i0, len(est["bleed48"]) - src0)
    if hi > lo:
        out[lo:hi] = est["bleed48"][src0 + lo:src0 + hi]
    return out


# --- the page --------------------------------------------------------------------------------------

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Leak listening check</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --line:#e3e0d8; --card:#fff; --acc:#2d5bd7; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#161614; --fg:#ecebe6; --muted:#a3a29c;
  --line:#33322e; --card:#1f1f1c; --acc:#7da0ff; }} }}
body {{ background:var(--bg); color:var(--fg); font:16px/1.45 -apple-system,system-ui,sans-serif;
  margin:0 auto; max-width:720px; padding:16px; }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 14px;
  margin:14px 0; }}
.row {{ display:flex; align-items:center; gap:10px; margin:6px 0; }}
.row b {{ width:2em; }} audio {{ width:100%; }}
.q {{ margin:10px 0 2px; }}
.pick button {{ font-size:16px; padding:8px 14px; margin:4px 6px 0 0; border-radius:8px;
  border:1px solid var(--line); background:var(--bg); color:var(--fg); }}
.pick button.on {{ background:var(--acc); color:#fff; border-color:var(--acc); }}
#line {{ font:15px ui-monospace,monospace; padding:10px; border:1px dashed var(--line); border-radius:8px;
  word-break:break-all; }} .muted {{ color:var(--muted); }}
</style></head><body>
<h1>Can you hear other instruments leaking in?</h1>
<p class="muted">{count} trials. Each plays the same 4.5 seconds of a guitar track twice, as A and
B, at the same loudness. In a live room, the guitar's microphone can pick up drums, another guitar
or other instruments. One of A and B may have had that leakage taken out. Some trials may have two
identical clips. Headphones help; guess if unsure.</p>
<p class="muted">For each trial, answer two things:</p>
<ol class="muted">
<li><b>Leaking:</b> which one has other instruments leaking in? A, B, Both, or N for neither.</li>
<li><b>Damage:</b> does either one's guitar sound damaged compared with the other (duller, thinner,
hollow, warbly or with artifacts)? No, a little, or a lot.</li>
</ol>
{trials}
<h2>Your answers</h2>
<p class="muted">Copy this line and send it back. Each item is the trial number, the leaking
one (A, B, Both or N) and the damage (no, little or lot), for example <code>1A-no</code> or
<code>2Both-little</code>. A ? marks a question not yet answered.</p>
<div id="line">—</div>
<script>
const key = "bleed-listen-{build}";
let a = {{}}; try {{ a = JSON.parse(localStorage.getItem(key) || "{{}}"); }} catch (e) {{}}
function show() {{
  document.querySelectorAll(".pick").forEach(p => p.querySelectorAll("button").forEach(b =>
    b.classList.toggle("on", (a[p.dataset.trial] || {{}})[p.dataset.q] === b.dataset.value)));
  const n = [...new Set([...document.querySelectorAll(".pick")].map(p => p.dataset.trial))];
  document.getElementById("line").textContent =
    n.map(t => t + ((a[t] || {{}}).leak || "?") + "-" + ((a[t] || {{}}).dmg || "?")).join(" ");
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
    leak = "".join(f'<button type="button" data-value="{v}">{lab}</button>'
                   for v, lab in (("A", "A"), ("B", "B"), ("Both", "Both"), ("N", "Neither")))
    dmg = "".join(f'<button type="button" data-value="{v}">{lab}</button>'
                  for v, lab in (("no", "No"), ("little", "A little"), ("lot", "A lot")))
    return (f'<section><h2>Trial {n}</h2>{rows}'
            f'<div class="q">Leaking?</div><div class="pick" data-trial="{n}" data-q="leak">{leak}</div>'
            f'<div class="q">Damage?</div><div class="pick" data-trial="{n}" data-q="dmg">{dmg}</div></section>')


def _out():
    from learn import knob_ceiling as K

    return K.HOME / "listening" / "bleed-1"


def _db(x):
    import math

    return round(10 * math.log10(max(x, 1e-12)), 1)


def build(args):
    import numpy as np

    from learn import build_knob_listening as BK
    from learn import confirm_run as CR
    from learn import knob_ceiling as K
    from learn import phase2_set3 as P

    out_dir = _out()
    if (out_dir / "private" / "key.json").exists() and not args.force:
        raise SystemExit(f"{out_dir / 'private' / 'key.json'} exists; pass --force to rebuild")
    trials = draw()
    lets = letters(trials)
    for n, (t, ls) in enumerate(zip(trials, lets), 1):
        print(f"  {n} {t['kind']:6s} {t['slug']} held {t['held']} letters {ls}", flush=True)
    ps = json.loads((ROOT / "docs" / "label-table-parts.json").read_text())["parts"]
    table = json.loads((AUDIT / "bleed-table.json").read_text())
    key = {"plan": "docs/bleed-listening-plan.md", "seed": SEED, "letter_seed": LETTER_SEED,
           "audit": "docs/audits/bleed-2026-10-16", "trials": {}}
    cache, sections = {}, []
    with tempfile.TemporaryDirectory() as tmp:
        for n, (t, ls) in enumerate(zip(trials, lets), 1):
            slug, held = t["slug"], t["held"]
            crop = pathlib.Path(ps[slug]["crop"])
            ref = CR.mono(crop / "reference.wav")
            a, b = K.R.HALVES[held]
            orig = ref[int(a * P.SR):int(b * P.SR)]
            ck = (slug, held)
            if ck not in cache:
                est = bleed_estimate(slug, crop, held)
                bl = bleed_in_crop(est, a, b)
                cleaned = orig - bl
                eo = float(np.sum(orig ** 2))
                cache[ck] = {"cleaned": cleaned,
                             "info": {"bleed_removed_db": _db(float(np.sum(bl ** 2)) / eo),
                                      "change_db": _db(float(np.sum(cleaned ** 2)) / eo),
                                      "model_component_db": _db(est["comp"]),
                                      "model_gain_db": _db(est["gain"]),
                                      "audit_bleed_db": table[slug]["halves"][held]["bleed_db"],
                                      "audit_flag": table[slug]["halves"][held]["flag"],
                                      "excluded_mics": est["excluded"],
                                      "regressor_tracks": est["n_clean"], "tracks": est["groups"],
                                      "crop_check_maxabs": est["crop_check"]}}
                print(slug, held, cache[ck]["info"], flush=True)
            clips = {"original": orig, "cleaned": cache[ck]["cleaned"]}
            srcs = [(L, BK.aac(BK.fade(BK.level(np.asarray(clips[name], np.float64))), tmp))
                    for L, name in ls.items()]
            sections.append(section(n, srcs))
            key["trials"][str(n)] = {"kind": t["kind"], "slug": slug, "held": held, "letters": ls,
                                     **cache[ck]["info"]}
    build_id = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:12]
    page = PAGE.format(count=len(sections), build=build_id, trials="\n".join(sections))
    text = re.sub(r"base64,[A-Za-z0-9+/=]+", "", page).lower()
    words = {t["slug"] for t in trials} | {"telefunken", "cambridge", "gym", "offering", "sculptor",
                                           "drag me", "farthest", "gtr_", "elecgtr", "repeat"}
    for w in words:
        assert w.lower() not in text, w
    (out_dir / "private").mkdir(parents=True, exist_ok=True)
    old = out_dir / "private" / "key.json"
    if old.exists():                       # keep earlier builds' keys
        old.rename(old.with_name(f"key-{int(old.stat().st_mtime)}.json"))
    old.write_text(json.dumps(key, indent=1))
    page_path = out_dir / "bleed-listening.html"
    page_path.write_text(page)
    print(page_path, f"{page_path.stat().st_size / 1e6:.2f} MB",
          "key sha256", hashlib.sha256(old.read_bytes()).hexdigest())


def score(args):
    out_dir = _out()
    key = json.loads((out_dir / "private" / "key.json").read_text())
    rep = score_key(key, parse_answers(args.answers))
    for r in rep["trials"]:
        print(f"{r['trial']} {r['kind']:6s} {r['slug']} held {r['held']} removed {r['bleed_removed_db']} dB: "
              f"leaking {r['leak']} -> {r['leak_names']}; damage {r['damage']}")
    print("high:", rep["high"])
    print("low:", rep["low"])
    print("repeat (A = B, consistency only):", rep["repeat"])
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
