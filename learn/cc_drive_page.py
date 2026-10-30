"""The clean/crunch pool's drive-pedal listening page (`docs/clean-crunch-pool-plan.md`, step 4's follow-up; ledger
`clean-crunch-pool-dcc`, `amendment_5`; approved by the user 2026-10-30). Can the listener hear a drive pedal switched
off in a clean/crunch mix? The D_CC audit traced D_CC's loss to crunch drive pedals switched off. Descriptive: it
decides nothing and relabels nothing. A thin adapter over `cc_audibility` (step 4): the same qualifying examples,
recipe, A_e and page rule, with the two drive pedals in place of the time effects, and a new player: both mixes of a
pair loop in sync and one control switches between A and B at once (step 4's page played them one after the other,
and its loudest pairs were not heard). Outputs go to `trusted-data/cc-drive-page/` and `listening/cc-drive-page/`
only; `cc/` and step 4's `cc-audibility/` are read, never written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    $MAIN -m learn.cc_drive_page plan                   # zero renders: the drive-on examples, the jobs
    $MAIN -u -m learn.cc_drive_page render --shard k/3  # new r_on', repeats, r_off: 2 renders per job
    $MAIN -m learn.cc_drive_page measure                # zero renders: A_e and solo per pair, the repeat floor
    $MAIN -m learn.cc_drive_page page                   # the blind A/B page and its key (the key outside the page)

**The pairs.** Step 4's qualifying examples (`cc_audibility.qualifies`: 44 of the 3,033 kept) less the runaway-
flagged targets (`RUNAWAY`), with drive pedal 1 or 2 on (the tone probe's rule, `audibility_measure.on_effects`, on
the pedals' switches); every one is measured (`N_MAX` is above both counts). Where step 4 rendered the example's r_on'
it is reused, not rendered again: the example's repeat, rendered here, must match it bit for bit, else render refuses.
**The checks.** Step 4's loudest reverb and sw50r spring pairs (`CHECKS`), re-cut from step 4's stored renders, each
beside a catch under its title (its mix against itself), and 3 catch pairs on drive examples. Heard means the verdict
"They differ". A check heard here but not on step 4's page is consistent with step 4's format hiding differences, not
proof of it: only the checks carry those titles, it is the listener's second hearing of them, and the listener may
know which items are checks. Step 4's item 4 (900215, the runaway delay) is a dirty example and is not re-used.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import pathlib
import random
import time

from learn import audibility_measure as AM
from learn import cc_audibility as CA
from learn import cc_build as CB
from learn import full_space as F
from learn import trusted_data_t3 as T3
from learn import verify_tracks as V

OUT_DIR = "cc-drive-page"                       # trusted-data/cc-drive-page/
PAGE_NAME = "cc-drive-page"                     # listening/cc-drive-page/
LEDGER_ID = CB.LEDGER_ID                        # clean-crunch-pool-dcc
LEDGER_KEY = "amendment_5"
LEDGER_MARK = "The drive-pedal listening page"
# name: (switch head, the edit that turns it off, the level proxy) as audibility_measure.EFFECTS
DRIVES = {"drive1": ("drive1/drive1Active", (("drive1", "drive1Active"), "false"), "drive1/drive1Drive"),
          "drive2": ("drive2/drive2Active", (("drive2", "drive2Active"), "false"), "drive2/drive2Gain")}
LABEL = {"drive1": "drive pedal 1", "drive2": "drive pedal 2", "reverb": "reverb", "sw50r spring": "sw50r spring"}


def label(effect):
    """An item's title word: LABEL's, else the effect's own name (step 4's titles)."""
    return LABEL.get(effect, effect)
N_MAX = 30                                      # "on" examples per pedal: above both counts, so no draw
SEED = 20261117                                 # the draw of N_MAX among more (none here)
PAGE_SEED = 20261118                            # the page's order and each item's A/B order
NEAR = 3                                        # per pedal: the pairs nearest tau on each side, then the loudest
CATCH = 3                                       # identical pairs (a mix against itself), from different examples
CHECKS = ((800877, "reverb"), (802682, "sw50r spring"))   # step 4's loudest reverb and sw50r spring pairs
ITEM_S = 30.0                                   # listening time per item (the page's estimate)
XFADE_S = 0.01                                  # the A/B switch's crossfade
# The runaway-flagged D_CC targets ('clear' and 'likely', the 2026-10-30 scan; ledger amendment_3_answers): a
# self-oscillating delay, not a usable mix. 900215 is the only one among the 44 qualifying examples.
RUNAWAY = frozenset((
    800027, 800058, 800063, 800101, 800413, 800434, 800615, 800671, 800673, 800758, 800761, 800893, 800974, 800996,
    801049, 801117, 801136, 801156, 801193, 801338, 801389, 801402, 801418, 801516, 801527, 801570, 801592, 801620,
    801642, 801655, 801657, 801672, 801735, 801763, 801769, 801828, 801905, 801978, 802036, 802047, 802104, 802107,
    802192, 802233, 802290, 802297, 802329, 802505, 802569, 802582, 802610, 802878, 802891, 803017, 803032, 803087,
    803135, 803297, 900119, 900137, 900205, 900215, 900314, 900356))

_save, _load = V._save, V._load


# --- pure ---------------------------------------------------------------------------------------------------------

def drives_on(t):
    """The drive pedals on in an encoded label t = (c, cm, s, sm, ...): the tone probe's rule
    (`audibility_measure.on_effects`) on the pedals' switches."""
    out = []
    for e, (sw, _, _) in DRIVES.items():
        j = F.SW.index(sw)
        if t[3][j] > 0 and t[2][j] > 0.5:
            out.append(e)
    return out


def qualifies(x, levels_of, runaway=RUNAWAY):
    """(ok, why): step 4's rule (`cc_audibility.qualifies`), a runaway-flagged target out first."""
    if x["i"] in runaway:
        return False, "a runaway-flagged target"
    return CA.qualifies(x, levels_of)


def candidates(rows, ex, levels_of, encode):
    """({pedal: [ids]}, {id: (section, amp)}, {why: n}) over the kept pool rows and their plan recipes."""
    import collections

    on = {e: [] for e in DRIVES}
    group, why = {}, collections.Counter()
    for r in rows:
        ok, w = qualifies(ex[r["i"]], levels_of)
        if not ok:
            why[w] += 1
            continue
        group[r["i"]] = (r["section"], r["amp"])
        for e in drives_on(encode(r["label"])):
            on[e].append(r["i"])
    return on, group, dict(why)


def jobs_for(chosen, group, reused):
    """`audibility_measure.jobs_of` with DRIVES, less the r_on' of every `reused` example (step 4 rendered it): its
    repeat stays and is checked against step 4's r_on'."""
    reps = AM.repeats(chosen, group)
    jobs = AM.jobs_of(chosen, reps, group, DRIVES)
    return [j for j in jobs if not (j["what"] == AM.ON and j["i"] in reused)], reps


def items_of(measured, checks, near=NEAR, n_catch=CATCH, seed=PAGE_SEED):
    """The page's items: per pedal `audibility_measure.page_items`' pairs (the `near` nearest tau on each side, then
    the loudest), `n_catch` catch pairs from different examples, the `checks` [(i, effect, a_e)], and a catch under
    each check's title (its mix against itself), so a check's title does not mark a real difference; shuffled, each
    item's A/B order drawn ("first": the mix on A)."""
    rng = random.Random(seed)
    picked = AM.page_items(measured, near=near, n_catch=0, seed=seed, effects=DRIVES)
    out = sorted(({k: it[k] for k in ("id", "effect", "i", "kind", "a_e")} for it in picked), key=lambda it: it["id"])
    ids = sorted({it["i"] for it in out})
    rng.shuffle(ids)
    for i in ids[:n_catch]:
        e = min(it["effect"] for it in out if it["i"] == i)
        out.append({"id": AM.item_id(e, i, "same"), "effect": e, "i": i, "kind": "same", "a_e": None})
    for i, e, a in checks:
        out.append({"id": AM.item_id(e, i, "check"), "effect": e, "i": i, "kind": "check (step 4's loudest)", "a_e": a})
        out.append({"id": AM.item_id(e, i, "same"), "effect": e, "i": i, "kind": "same", "a_e": None})
    rng.shuffle(out)
    for it in out:
        it["first"] = rng.choice(("on", "off"))
    return out


# --- I/O ------------------------------------------------------------------------------------------------------------

def out_dir(root):
    return pathlib.Path(root) / OUT_DIR


def flac_of(root, i, what):
    return out_dir(root) / "renders" / f"{i}-{what.replace(' ', '_')}.flac"


def flac_for(reused):
    """flac(root, i, what): step 4's file for a reused r_on' and for the checks' renders, this step's otherwise."""
    def flac(root, i, what):
        if (what == AM.ON and i in reused) or what not in (AM.ON, AM.REPEAT, *DRIVES):
            return CA.flac_of(root, i, what)
        return flac_of(root, i, what)
    return flac


def key_path(root):
    return out_dir(root) / "page-key.json"


def page_dir(args):
    """~/ndsp-presets/listening/cc-drive-page for real runs; under --out for a smoke run."""
    return (pathlib.Path(args.out) / "listening" if args.smoke else V.HOME / "listening") / PAGE_NAME


def step4_on_rows(root):
    """{i: step 4's r_on' render row} (`cc_audibility`'s folder; the fresh recipe's rows only)."""
    return {r["i"]: r for r in CA.render_rows(CA.out_dir(root)) if r["what"] == AM.ON}


def reader(root, ap):
    """read(i, what) -> the stored render as float64 (hash-checked): this step's renders, step 4's for a reused r_on'
    and for the checks' pairs (`ap`: this step's plan.json)."""
    import numpy as np

    from learn import direct_sound_gate as G

    reused = set(ap["reused_on"]) | {i for i, _ in CHECKS}       # the checks' r_on' are step 4's too
    flac = flac_for(reused)
    rows = {(r["i"], r["what"]): r for r in CA.render_rows(out_dir(root))}
    rows.update({(i, AM.ON): r for i, r in step4_on_rows(root).items() if i in reused})
    rows.update({(r["i"], r["what"]): r for r in CA.render_rows(CA.out_dir(root)) if (r["i"], r["what"]) in CHECKS})

    def read(i, what):
        f = rows[(i, what)]["file"]
        return np.asarray(G.read_flac(flac(root, i, what), f["scale"], f["sha256"]), np.float64)
    return read


def ledger_declared(path=None):
    d = json.loads(pathlib.Path(path or V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == LEDGER_ID), {})
    return LEDGER_MARK in str(e.get(LEDGER_KEY, ""))


def require_declared():
    if not ledger_declared():
        raise SystemExit(f"the ledger's {LEDGER_ID} has no {LEDGER_KEY} declaring '{LEDGER_MARK}': runs refuse")


# --- commands ---------------------------------------------------------------------------------------------------------

def cmd_plan(args):
    """The drive-on examples, the reused r_on', the repeats and the jobs (zero renders), to plan.json."""
    require_declared()
    root = V.out_root(args)
    od = out_dir(root)
    _, rows, ex, _ = CA.pool(args)
    on, group, why = candidates(rows, ex, CA.window_levels(CB.ctx_for(args)), T3.encode_for(T3.FULL))
    chosen = AM.select(on, N_MAX, SEED)
    ids = sorted({i for v in chosen.values() for i in v})
    s4 = step4_on_rows(root)
    reused = sorted(i for i in ids if i in s4)
    jobs, reps = jobs_for(chosen, group, set(reused))
    s4m = _load(CA.out_dir(root) / "measure.json") or {}
    have = {(p["i"], p["effect"]) for p in s4m.get("pairs", [])}
    lost = [c for c in CHECKS if c not in have or c[0] in RUNAWAY]
    if lost:
        raise SystemExit(f"step 4's measure.json lacks the checks {lost} (or one is runaway-flagged)")
    rec = {"plan": CB.PLAN, "ledger": f"{LEDGER_ID} {LEDGER_KEY}", "recipe": AM.RECIPE, "seed": SEED,
           "n_max": N_MAX, "tau": AM.TAU, "drives": {e: list(v[1][0]) for e, v in DRIVES.items()},
           "kept": len(rows), "out_by_rule": why, "qualify": len(group), "on": {e: len(v) for e, v in on.items()},
           "chosen": chosen, "examples": len(ids), "sections": len({group[i][0] for i in ids}),
           "reused_on": reused, "checks": [list(c) for c in CHECKS],
           "repeats": [{"section": g[0], "amp": g[1], "i": i} for g, i in sorted(reps.items())],
           "jobs": jobs, "renders_projected": 2 * len(jobs), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    old = _load(od / "plan.json")
    if old and old.get("jobs") == jobs:
        print(f"PLAN DONE (unchanged, {od / 'plan.json'}): {len(jobs)} jobs, {2 * len(jobs)} renders")
        return
    if old and (od / "rows").exists() and any((od / "rows").iterdir()):
        raise SystemExit("renders exist and the plan would change: it is fixed")
    if old and not args.force:
        raise SystemExit(f"{od / 'plan.json'} exists and differs (--force to rewrite before any render)")
    _save(od / "plan.json", rec)
    print(f"kept {len(rows)}; out by the rule {why}; qualify {len(group)}; on {rec['on']}")
    print(f"{len(ids)} examples in {rec['sections']} sections; r_on' reused from step 4 {len(reused)}, new "
          f"{len(ids) - len(reused)}; repeats {len(reps)}")
    print(f"PLAN DONE: {len(jobs)} jobs, each a new process (1 priming + 1 kept) = {rec['renders_projected']} renders")


def cmd_render(args):
    """One shard (`cc_audibility.render_shard`, DRIVES): a reused example's repeat must match step 4's r_on'."""
    require_declared()                              # before any import: the light CI has no numpy
    root = V.out_root(args)
    od = out_dir(root)
    ap = _load(od / "plan.json") or {}
    s4 = step4_on_rows(root)
    on_sha0 = {i: s4[i]["audio_sha256"] for i in ap.get("reused_on", [])}
    CA.render_shard(args, od, DRIVES, on_sha0, flac=flac_for(set(on_sha0)), label="CC DRIVE PAGE")


def cmd_measure(args):
    """Every pair's A_e and solo, each group's repeat floor (`cc_audibility.measure_step`, DRIVES), to measure.json;
    a reused r_on' is read from step 4's folder."""
    require_declared()                              # before any import: the light CI has no numpy
    root = V.out_root(args)
    od = out_dir(root)
    ap = _load(od / "plan.json")
    if not ap:
        raise SystemExit("run `plan` first")
    s4 = step4_on_rows(root)
    reused = set(ap["reused_on"])
    CA.measure_step(args, od, DRIVES, [s4[i] for i in sorted(reused)], flac=flac_for(reused),
                    ledger=f"{LEDGER_ID} {LEDGER_KEY}")


def cmd_page(args):
    """The blind A/B page (`items_of`, the checks from step 4's measure.json), its key to page-key.json outside the
    listening folder."""
    require_declared()                              # before any import: the light CI has no numpy
    from learn import trusted_data as T

    root = V.out_root(args)
    od = out_dir(root)
    meas = _load(od / "measure.json")
    if not meas or meas.get("recipe") != AM.RECIPE:
        raise SystemExit("run `measure` first")
    ap = _load(od / "plan.json")
    s4m = _load(CA.out_dir(root) / "measure.json")
    a4 = {(p["i"], p["effect"]): p["a_e"] for p in s4m["pairs"]}
    refused = {r["i"] for r in meas["refused"]}
    items = items_of([p for p in meas["pairs"] if p["i"] not in refused], [(i, e, a4[(i, e)]) for i, e in CHECKS])
    pd, kp = page_dir(args), key_path(root)
    if kp.exists() and not args.force:
        raise SystemExit(f"{kp} exists: a rebuild hides the listener's stored answers (--force)")
    plan = CB.load_plan(args)
    ex = {x["i"]: x for x in plan["examples"]}
    rend, built = T.rows_of(root, CB.STAGE, "render"), T.rows_of(root, CB.STAGE, "build")
    stems = T.Stems(CB.ctx_for(args))
    read = reader(root, ap)
    clips = {}
    for it in sorted(items, key=lambda it: it["i"]):
        i, x = it["i"], ex[it["i"]]
        _, oth, st = CA.backing(root, i, x, rend, stems)
        g, mst = built[i]["gains_db"], x["draw"]["mastered"]
        on = AM.mix_with(read(i, AM.ON), oth, st, g, i, mst)
        off = on.copy() if it["kind"] == "same" else AM.mix_with(read(i, it["effect"]), oth, st, g, i, mst)
        a, b = (on, off) if it["first"] == "on" else (off, on)
        clips[it["id"] + "-1"], clips[it["id"] + "-2"] = AM.pair_clips(a, b, pd / "cache")
        it.update(band=x["band"], cls=x.get("cls"), ratio_db=x["draw"]["ratio_db"], others=len(x["others"]),
                  stand_ins=len(x.get("amp_tracks") or []))
    build = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    _save(kp, {"page": PAGE_NAME, "tau": AM.TAU, "seed": PAGE_SEED, "build": build, "items": items,
               "player": "A/B", "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    pd.mkdir(parents=True, exist_ok=True)
    p = pd / "index.html"
    p.write_text(page_html(items, clips, build))
    print(f"PAGE DONE: {len(items)} items, {p.stat().st_size / 1e6:.1f} MB -> {p}")


# --- the page -------------------------------------------------------------------------------------------------------

CSS = """
.plays .ab, .plays .sw { min-height:52px; border-radius:10px; border:1px solid var(--line); background:var(--bg);
  padding:0 16px; font-weight:600; }
.plays .ab { flex:0 0 64px; }
.plays .sw { flex:1 1 40%; }
.plays .ab[aria-pressed="true"] { background:var(--on); color:var(--on-fg); border-color:var(--on); }
"""

# The A/B player (`build_ear_page.JS_HEAD` before it, `JS_ANSWERS` after: the same answers store and export). Both
# clips of an item are decoded and start together on loop, each through its own gain; A and B set which one is heard,
# with a XFADE_S crossfade, so a switch lands at the same moment of the music. It defines stop() and play(btn), which
# JS_ANSWERS calls (Export stops playback; autoplay starts the next item's Play).
PLAYER_JS = """
const XF = XFADE_S;
let actx = null, cur = null, token = 0;
const bufs = {};
try { if (navigator.audioSession) navigator.audioSession.type = "playback"; } catch (e) {}
function bytes(key) {
  const bin = atob(CLIPS[key]); const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u.buffer;
}
function decode(key) {
  if (!bufs[key]) bufs[key] = new Promise((ok, no) => actx.decodeAudioData(bytes(key), ok, no));
  return bufs[key];
}
function setNow(it, t) { it.querySelector(".now").textContent = t; }
function mark() {
  items.forEach(it => it.querySelectorAll(".ab").forEach(b => b.setAttribute("aria-pressed",
    String(!!cur && cur.it === it && Number(b.dataset.side) === cur.side))));
  if (cur) setNow(cur.it, "Playing " + "AB"[cur.side] + " (it loops; switch any time)");
}
function stop() {
  token++;
  if (!cur) return;
  cur.srcs.forEach(s => { try { s.stop(); } catch (e) {} });
  cur.btn.classList.remove("on"); setNow(cur.it, "");
  cur = null; mark();
}
async function play(btn, side) {
  const it = btn.closest(".item");
  const same = cur && cur.btn === btn;
  stop();
  if (same && side === undefined) return;
  const my = token;
  items.forEach(i => i.classList.remove("current")); it.classList.add("current");
  if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
  try { await actx.resume(); } catch (e) {}
  setNow(it, "Loading...");
  let b;
  try { b = await Promise.all([decode(it.dataset.id + "-1"), decode(it.dataset.id + "-2")]); }
  catch (e) { setNow(it, "This browser could not decode the clips."); return; }
  if (my !== token) return;
  const s0 = side || 0, end = Math.min(b[0].duration, b[1].duration), t0 = actx.currentTime + 0.05;
  const srcs = [], gains = [];
  b.forEach((buf, k) => {
    const s = actx.createBufferSource(); s.buffer = buf; s.loop = true; s.loopStart = 0; s.loopEnd = end;
    const g = actx.createGain(); g.gain.value = k === s0 ? 1 : 0;
    s.connect(g); g.connect(actx.destination); s.start(t0); srcs.push(s); gains.push(g);
  });
  cur = {btn: btn, it: it, srcs: srcs, gains: gains, side: s0};
  btn.classList.add("on"); mark();
}
function pick(it, side) {
  if (!cur || cur.it !== it) { play(it.querySelector(".play.main"), side); return; }
  if (cur.side === side) return;
  const t = actx.currentTime;
  cur.gains.forEach((g, k) => {
    g.gain.cancelScheduledValues(t); g.gain.setValueAtTime(g.gain.value, t);
    g.gain.linearRampToValueAtTime(k === side ? 1 : 0, t + XF);
  });
  cur.side = side; mark();
}
function flip(it) { if (cur && cur.it === it) pick(it, 1 - cur.side); else play(it.querySelector(".play.main"), 0); }
items.forEach(it => {
  it.querySelector(".play.main").addEventListener("click", e => play(e.currentTarget));
  it.querySelectorAll(".ab").forEach(b => b.addEventListener("click", () => pick(it, Number(b.dataset.side))));
  it.querySelector(".sw").addEventListener("click", () => flip(it));
});
document.addEventListener("keydown", e => {
  if (e.metaKey || e.ctrlKey || e.altKey || (e.target.closest && e.target.closest("input, textarea"))) return;
  const k = (e.key || "").toLowerCase();
  const it = cur ? cur.it : document.querySelector(".item.current");
  if (!it) return;
  if (k === "s") { e.preventDefault(); flip(it); }
  else if (k === "a" || k === "b") { e.preventDefault(); pick(it, k === "a" ? 0 : 1); }
  else if (k === "escape") stop();
});
"""


SOLO_TEXT = {      # the guitar-only pages' wording (ledger amendment_6, `cc_solo_pages`)
    "title": "Guitar-only check", "head": "Can you hear it on the guitar alone?",
    "sub": "The same 10 s of a guitar part, alone, as A and B, looping",
    "intro": "Each item is the same 10 seconds of a guitar part, played alone (no band), as A and B,\nlooping.",
    "same": "clip"}
MIX_TEXT = {
    "title": "Drive pedal check", "head": "Can you hear the pedal in the song?",
    "sub": "The same 10 s of a song as A and B, looping",
    "intro": "Each item is the same 10 seconds of a song as A and B,\nlooping.", "same": "mix"}


def page_html(items, clips, build, name=PAGE_NAME, part=1, solo=False):
    """The page: per item one looping pair, A and B switched at once (`PLAYER_JS`), "do A and B differ?"; the ear
    page's style, answers store and export (`build_ear_page`), so an export reads as step 4's did. `solo`: the
    guitar-only pages' wording (`cc_solo_pages`); `part`: the export's part number."""
    from learn import build_ear_page as BEP

    e = html.escape
    tx = SOLO_TEXT if solo else MIX_TEXT
    total = len(items)
    secs = {it["id"]: ITEM_S for it in items}
    cards = []
    for n, it in enumerate(items):
        vs = "".join(f'<button type="button" class="v" data-v="{v}">{e(t)}</button>' for v, t in AM.VERDICTS)
        cards.append(
            f'<article class="item" data-id="{it["id"]}" data-n="{n + 1}"><div class="num">{n + 1} / {total}</div>'
            f'<h3>Listen for: {e(label(it["effect"]))}</h3><p class="sub">{tx["sub"]}</p>'
            f'<div class="plays"><button type="button" class="play main">&#9654; Play</button>'
            f'<button type="button" class="ab" data-side="0" aria-pressed="false">A</button>'
            f'<button type="button" class="ab" data-side="1" aria-pressed="false">B</button>'
            f'<button type="button" class="sw">Switch A/B (S)</button>'
            f'</div><p class="now"></p><div class="vs">{vs}</div>'
            f'<input class="note" type="text" placeholder="Note (optional)" aria-label="Note"></article>')
    data = {"page": name, "part": part, "build": build,
            "items": [{"id": it["id"], "title": f"Listen for: {label(it['effect'])}", "subtitle": ""} for it in items],
            "secs": secs}
    minutes = round(sum(secs.values()) / 60)
    js = BEP.JS_HEAD + PLAYER_JS.replace("XFADE_S", repr(XFADE_S)) + BEP.JS_ANSWERS
    data_json = json.dumps(data).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{tx["title"]}</title>
<style>{BEP.CSS}{CSS}</style></head><body>
<header><div class="hrow"><b>{tx["head"]}</b><span id="count"></span></div>
<div class="hrow"><label><input type="checkbox" id="auto"> Autoplay next</label>
<span id="left" class="ask"></span></div><div class="prog"><div id="bar"></div></div></header>
<main>
<h1>Do A and B differ?</h1>
<p class="intro">{total} items, about {minutes} minutes. {tx["intro"]} Press Play, then switch between A and B as often as you like: the Switch button, the A and B buttons, or
the S, A and B keys. The switch is instant and lands at the same moment of the music. In one of A and B the named
pedal or effect is on; in the other it is switched off, and nothing else changes. Which is which is random, and a few
items are the very same {tx["same"]} as A and B. Answer whether you hear <b>any</b> difference, however small. A and B are set
to the same loudness, so listen for the sound itself, not a volume change. Headphones help; on an iPhone, turn the
silent switch off. Answers are saved in this browser as you go; tap <b>Export</b> any time, even halfway, and send
the file.</p>
{"".join(cards)}
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


COMMANDS = {"plan": cmd_plan, "render": cmd_render, "measure": cmd_measure, "page": cmd_page}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cc_drive_page", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--shard", type=V.parse_shard, default=(0, 1))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args(argv)
    if args.shard != (0, 1) and args.cmd != "render":
        raise SystemExit("--shard is for render")
    if args.force and args.cmd not in ("plan", "page"):
        raise SystemExit("--force is for plan and page")
    CA.require_run(args)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
