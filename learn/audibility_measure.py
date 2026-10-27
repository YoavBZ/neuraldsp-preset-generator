"""ROADMAP step (c), the measurement: how audible each "on" time effect is in its own self-built mix
(`docs/trusted-data-t0-design.md`, "Audibility in the mix: the measurement"; ledger `trusted-data-t3`, amendment 5).
Approved by the user 2026-10-27 ("Yes for all"). Descriptive: it decides nothing and relabels nothing; how a label
may use it waits for the user's three rulings ([research](../docs/research/effect-detection-2026-10.md)). FS5 is
development data; V-real is not touched. Outputs go to `trusted-data/audibility/` and the listening page only; `t0/`,
`t2/`, `t3/` and `tone-probe/` are read, never written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    $MAIN -m learn.audibility_measure archive                # zero renders: the first run moved aside (a record)
    $MAIN -m learn.audibility_measure plan                   # zero renders: FS5's "on" examples drawn, plan.json
    $MAIN -u -m learn.audibility_measure render --shard k/3  # r_on', the effect-off renders, repeats (~2,700)
    $MAIN -m learn.audibility_measure measure                # zero renders: A_e and the solo distance per pair
    $MAIN -m learn.audibility_measure read                   # zero renders: the tone probe's switches by A_e
    $MAIN -m learn.audibility_measure page                   # the ear check of tau, a listening page

**A_e (the fresh-process recipe, amendment 5's fix).** Morgan's tremolo, tape delay and rack reverb run on across
renders in one plugin process (isolate=True does not reset them), so a render is a fixed function of its position in
its process. Every render here therefore runs in its own new plugin process: one discarded priming render with the
example's own setting (r_on's), then the one render kept. For an FS5 example i with effect e on, r_on' is that render
of its own setting and r_off the same setting with e switched off, both at the same process position; m' is r_on' in
the example's stored backing at its stored gains and mastering (`mix_with`, checked first to rebuild the stored mix
from the stored target). The judge J scores a render against the mix on the two halves; A_e = |mean over halves of
log(J(r_off, m') / J(r_on', m'))|. Beside it, solo, the plain distance J(r_off, r_on') (no threshold), and a repeat:
r_on' rendered again, in its own new process, once per (section, amp) group, which must be bit-identical. The first
run (2026-10-27: stored r_on and m, renders sharing a process) is kept under `audibility/first-run-2026-10-27/`.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import pathlib
import random
import time

from learn import full_space as F
from learn import trusted_data as T
from learn import trusted_data_t3 as T3
from learn import verify_tracks as V

OUT_DIR = "audibility"                                # trusted-data/audibility/: never under t3/
LEDGER_KEY = "amendment_5"
LEDGER_MARK = "audibility measurement (ROADMAP (c))"
FIX_KEY = "amendment_5_fix"
FIX_MARK = "audibility fresh-process recipe (ROADMAP (c))"
DESIGN = ("docs/trusted-data-t0-design.md#audibility-in-the-mix-the-measurement-roadmap-step-c-declared-2026-10-27-"
          "nothing-run")
STATUS = ("declared 2026-10-27 before any render (ledger trusted-data-t3, amendment 5); re-declared 2026-10-27 after "
          "the first run and before any re-render (amendment 5's fix: every render in its own new plugin process); "
          "descriptive, decides nothing; FS5 read before by R0, the tone probe, step (a) and the first run")
RECIPE = "fresh"                                      # each render in its own new process, primed with r_on's setting
ARCHIVE = "first-run-2026-10-27"                      # the first run's files, moved aside as a record
MODULATED = ("delay", "reverb", "tremolo")            # run on across renders in a process; the springs do not
# name: (switch head, the edit that turns it off, the tone probe's proxy for its level)
EFFECTS = {"delay": ("delay/delayActive", (("delay", "delayActive"), "false"), "delay/delayMix"),
           "reverb": ("reverb/reverbActive", (("reverb", "reverbActive"), "false"), "reverb/reverbMix"),
           "tremolo": ("tremolo/tremoloActive", (("tremolo", "tremoloActive"), "false"), "tremolo/tremoloDepth"),
           "pr12 spring": ("pr12Amp/springOn", (("pr12Amp", "pr12Reverb"), "0"), "pr12Amp/pr12Reverb"),
           "sw50r spring": ("sw50rAmp/springOn", (("sw50rAmp", "sw50rReverb"), "0"), "sw50rAmp/sw50rReverb")}
ON = "on"                                             # r_on': the example's own setting, rendered fresh
REPEAT = "repeat"                                     # r_on' rendered again, fresh: it must be bit-identical
N_MAX = 200                                           # "on" examples per effect (the research's ranked change 2)
SEED = 20261113                                       # the draw of N_MAX among more (set here)
PAGE_SEED = 20261114                                  # the page's order and each pair's play order (set here)
TAU = 0.005                                           # the every-control plan's log bar: the starting threshold
NEAR = 2                                              # page: the pairs nearest tau on each side, per effect
CATCH = 3                                             # page: identical pairs (the mix against itself)
WORKERS = 2                                           # measure: one section per worker (2: memory beside step (b))
HALVES = ("A", "B")
WHICH = ("all on", "measured", "bottom third", "middle third", "top third", "below tau", "at or above tau")
PAGE_NAME = "audibility-mix"
PAGE_KBPS = 128                                       # AAC: above the ear pages' 96; the page about 10 MB
VERDICTS = [("different", "They differ"), ("maybe", "Maybe, barely"), ("same", "Same to me"), ("unsure", "Not sure")]

_save, _load = V._save, V._load


# --- pure: the draw ----------------------------------------------------------------------------------------------

def on_effects(t):
    """The effects on in an encoded label t = (c, cm, s, sm, ...): the switch sounds (masked in) and is on, the tone
    probe's rule."""
    out = []
    for e, (sw, _, _) in EFFECTS.items():
        j = F.SW.index(sw)
        if t[3][j] > 0 and t[2][j] > 0.5:
            out.append(e)
    return out


def select(on_ids, n_max=N_MAX, seed=SEED):
    """{effect: sorted ids}: every "on" example, or a seeded draw of n_max when there are more."""
    from learn import pretrain_set as PS

    out = {}
    for e, ids in on_ids.items():
        ids = sorted(ids)
        if len(ids) > n_max:
            ids = sorted(random.Random(PS.seed_int(seed, e)).sample(ids, n_max))
        out[e] = ids
    return out


def repeats(chosen, group_of):
    """{(section, amp): the group's least chosen id}: one repeat render of r_on' per group that renders anything."""
    out = {}
    for ids in chosen.values():
        for i in ids:
            g = group_of[i]
            out[g] = min(i, out.get(g, i))
    return out


def jobs_of(chosen, reps, group_of):
    """The jobs, in (section, amp, id) order: each chosen id's r_on' first, then its repeat (if any), then its effects
    off in EFFECTS order. Each job is one new process: a priming render, then the render kept.
    -> [{"i", "section", "amp", "what"}]."""
    rank = {ON: -2, REPEAT: -1, **{e: k for k, e in enumerate(EFFECTS)}}
    ids = sorted({i for v in chosen.values() for i in v})
    out = [{"i": i, "section": group_of[i][0], "amp": group_of[i][1], "what": ON} for i in ids]
    out += [{"i": i, "section": g[0], "amp": g[1], "what": REPEAT} for g, i in reps.items()]
    out += [{"i": i, "section": group_of[i][0], "amp": group_of[i][1], "what": e}
            for e, ids_e in chosen.items() for i in ids_e]
    return sorted(out, key=lambda j: (j["section"], j["amp"], j["i"], rank[j["what"]]))


def plan_unchanged(old, new):
    """The stored plan and a recomputed one draw the same renders (a re-run of the chain resumes)."""
    return all(old.get(k) == new.get(k) for k in ("recipe", "seed", "n_max", "tau", "chosen", "jobs"))


def fresh_render(make, di, sel, x_prime, x):
    """One render in its own new process: `make()` opens a renderer, one discarded priming render with `x_prime`
    (r_on's setting, the same for every job of an example), then the render of `x` that is kept; the renderer is
    closed whatever happens. Every kept render so sits at the same process position. -> the kept render."""
    import numpy as np

    rr = make()
    try:
        rr.render(di, sel, x_prime)
        return np.asarray(rr.render(di, sel, x), np.float64)
    finally:
        rr.close()


def audio_sha(y):
    """sha256 of a render's float64 samples: two renders are bit-identical exactly when these agree."""
    import numpy as np

    return hashlib.sha256(np.ascontiguousarray(y, np.float64).tobytes()).hexdigest()


def clean_pair(settings, effect):
    """True when no modulated effect other than `effect` is on in the setting (T3's render-row form, "module/key"):
    the first run's r_off then differed from its stored r_on by `effect` alone (the consistency check's pairs)."""
    for f in MODULATED:
        if f == effect:
            continue
        (m, k), _ = EFFECTS[f][1]
        if F._truthy(settings.get(f"{m}/{k}")):
            return False
    return True


def consistency(old, new, clean, tau=TAU):
    """The first run's A_e against this run's, on the clean pairs. old, new: {(effect, i): A_e or None}; clean: a set
    of (effect, i). -> {effect or "all": {"n", "spearman", "median_abs_diff", "crossed_tau"}}."""
    out = {}
    for e in (*EFFECTS, "all"):
        ks = sorted(k for k in clean if (e == "all" or k[0] == e) and old.get(k) is not None
                    and new.get(k) is not None)
        a, b = [old[k] for k in ks], [new[k] for k in ks]
        d = sorted(abs(x - y) for x, y in zip(a, b))
        out[e] = {"n": len(ks), "spearman": spearman(a, b)[0] if ks else None,
                  "median_abs_diff": d[len(d) // 2] if d else None,
                  "crossed_tau": sum((x < tau) != (y < tau) for x, y in zip(a, b))}
    return out


def off_settings(x, effect):
    """Setting x with `effect` switched off and nothing else changed. Refuses a setting where it is not on."""
    _, (path, off), _ = EFFECTS[effect]
    v = x.get(path)
    on = F._truthy(v) if off == "false" else (v is not None and float(v) > 0)
    if not on:
        raise ValueError(f"{effect} is not on in this setting ({path} = {v!r})")
    y = dict(x)
    y[path] = off
    return y


# --- pure: A_e --------------------------------------------------------------------------------------------------

def _finite_pos(v):
    return v is not None and math.isfinite(v) and v > 0


def a_e(j_on, j_off):
    """{"signed", "a_e", "halves"} from J(r_on, m) and J(r_off, m) per half: the mean over the halves of
    log(J(r_off, m) / J(r_on, m)) and its absolute value. None when a half is refused (infinite) or zero."""
    if not all(_finite_pos(j_on.get(h)) and _finite_pos(j_off.get(h)) for h in HALVES):
        return None
    lr = {h: math.log(j_off[h] / j_on[h]) for h in HALVES}
    s = sum(lr.values()) / len(HALVES)
    return {"signed": s, "a_e": abs(s), "halves": lr}


def solo(j):
    """The mean over the halves of J(r_off, r_on), the plain distance (no threshold); None when a half is refused."""
    if not all(j.get(h) is not None and math.isfinite(j[h]) for h in HALVES):
        return None
    return sum(j[h] for h in HALVES) / len(HALVES)


def thirds(values):
    """The tertile cuts (t1, t2) of the finite values; None with fewer than 3."""
    import numpy as np

    v = np.asarray([x for x in values if x is not None and math.isfinite(x)], np.float64)
    if len(v) < 3:
        return None
    return float(np.percentile(v, 100 / 3)), float(np.percentile(v, 200 / 3))


def subset(on, ae, which, cuts, tau=TAU):
    """FS5's scored examples kept for one read: every "off", and the "on" ones in `which` by A_e (NaN: not measured,
    kept only in "all on")."""
    import numpy as np

    on, ae = np.asarray(on, bool), np.asarray(ae, np.float64)
    fin = np.isfinite(ae)
    if which == "all on":
        sel = np.ones_like(on)
    elif which == "measured":
        sel = fin
    elif which in ("bottom third", "middle third", "top third"):
        if cuts is None:
            sel = np.zeros_like(on)
        else:
            t1, t2 = cuts
            with np.errstate(invalid="ignore"):
                sel = {"bottom third": ae <= t1, "middle third": (ae > t1) & (ae <= t2), "top third": ae > t2}[which]
            sel = sel & fin
    elif which == "below tau":
        sel = fin & (np.nan_to_num(ae, nan=np.inf) < tau)
    elif which == "at or above tau":
        sel = fin & (np.nan_to_num(ae, nan=-np.inf) >= tau)
    else:
        raise ValueError(which)
    return ~on | (on & sel)


def quantiles(values, qs=(0, 10, 25, 50, 75, 90, 100)):
    import numpy as np

    v = np.asarray([x for x in values if x is not None and math.isfinite(x)], np.float64)
    return {str(q): float(np.percentile(v, q)) for q in qs} if len(v) else {}


# --- pure: the page ---------------------------------------------------------------------------------------------

def item_id(effect, i, kind):
    return "aud-" + hashlib.sha256(f"{effect}|{i}|{kind}".encode()).hexdigest()[:12]


def page_items(measured, tau=TAU, near=NEAR, n_catch=CATCH, seed=PAGE_SEED):
    """The ear check's pairs: per effect the `near` measured pairs nearest tau below it and above it, and the
    loudest (an anchor), then `n_catch` identical pairs (the mix against itself) from different effects; shuffled,
    each pair's play order drawn. measured: [{"i", "effect", "a_e"}]. -> [item dicts]."""
    rng = random.Random(seed)
    out, used = [], set()
    for e in EFFECTS:
        rows = [m for m in measured if m["effect"] == e and m.get("a_e") is not None]
        below = sorted((m for m in rows if m["a_e"] < tau), key=lambda m: (-m["a_e"], m["i"]))[:near]
        above = sorted((m for m in rows if m["a_e"] >= tau), key=lambda m: (m["a_e"], m["i"]))[:near]
        pick = [(m, "near tau, below") for m in below] + [(m, "near tau, above") for m in above]
        top = max(rows, key=lambda m: (m["a_e"], -m["i"]), default=None)
        if top is not None and all(top is not m for m, _ in pick):
            pick.append((top, "anchor (loudest)"))
        for m, kind in pick:
            out.append({"id": item_id(e, m["i"], kind), "effect": e, "i": m["i"], "kind": kind, "a_e": m["a_e"]})
            used.add((e, m["i"]))
    pool = sorted({(it["effect"], it["i"]) for it in out})
    rng.shuffle(pool)
    seen = set()
    for e, i in pool:
        if len([c for c in out if c["kind"] == "same"]) >= n_catch:
            break
        if e in seen:
            continue
        seen.add(e)
        out.append({"id": item_id(e, i, "same"), "effect": e, "i": i, "kind": "same", "a_e": None})
    rng.shuffle(out)
    for it in out:
        it["first"] = rng.choice(("on", "off"))
    return out


# --- I/O helpers --------------------------------------------------------------------------------------------------

def out_dir(root):
    return root / OUT_DIR


def flac_of(root, i, what):
    return out_dir(root) / "renders" / f"{i}-{what.replace(' ', '_')}.flac"


def render_rows(od, own=None):
    """Every shard's render rows (`pretrain_set.read_rows`: a torn last line, from a shard killed mid-write, is
    skipped). Only `own`, the calling shard's file, is repaired; another shard may be writing its own. A row of another
    recipe (the first run's, left in place by mistake) refuses."""
    from learn import pretrain_set as PS

    d = od / "rows"
    paths = sorted(d.glob("render-*.jsonl")) if d.exists() else []
    rows = [r for p in paths for r in PS.read_rows(p, repair=own is not None and p == own)]
    other = [(r.get("i"), r.get("what")) for r in rows if r.get("recipe") != RECIPE]
    if other:
        raise SystemExit(f"{len(other)} render rows are not the {RECIPE} recipe's (e.g. {other[:3]}): run `archive`")
    return rows


def ledger_declared(key=LEDGER_KEY, mark=LEDGER_MARK):
    d = json.loads((V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == T3.LEDGER_ID), {})
    return mark in str(e.get(key, ""))


def require_declared():
    for key, mark in ((LEDGER_KEY, LEDGER_MARK), (FIX_KEY, FIX_MARK)):
        if not ledger_declared(key, mark):
            raise SystemExit(f"the ledger's {T3.LEDGER_ID} has no {key} declaring '{mark}': runs refuse")


def mix_with(r, others, stems_audio, gains, i, mastered):
    """A mix of render r with an example's stored backing at its stored gains (gb, ga) and its mastering draw: the
    stored mix when r is the stored target, m' when r is r_on', the page's "off" mix when r is r_off."""
    from learn import direct_stems as DS
    from learn import song_aug as SA

    mix = (r + (others + stems_audio) * 10 ** (gains["gb"] / 20)) * 10 ** (gains["ga"] / 20)
    m2, rng = DS.master_draw(i)
    if m2 != mastered:
        raise SystemExit(f"{i}: the mastering draw changed")
    return SA.compress(mix, rng) if mastered else mix


def load_fs5(root):
    """(T3's frozen plan, its drift record, FS5 rows with full labels, T3's render rows): the drift check of step (a)
    refuses when today's T0 lists remove anything FS5 uses."""
    from learn import direct_stems as DS
    from learn import trusted_data_t3_mix as M

    plan, drift = M.load_frozen(root)
    ctx = DS.Ctx(quiet=True)
    _, fs = T3.arm_rows(root, ctx, plan, T3.FULL)
    return plan, drift, fs, T.rows_of(root, T3.STAGE, "render")


# --- archive (zero renders) ------------------------------------------------------------------------------------------

FIRST_RUN = ("measure.json", "read.json", "page-key.json", "rows", "renders", "plan.json")   # the plan last


def archive_moves(od, pd):
    """(source, destination) pairs that move the first run aside: the listening page made from it (not to be sent)
    into the archive's page/, then its files under audibility/, plan.json last, so a move cut short leaves the first
    run's plan in place and `archive` runs again. Only what exists."""
    a = od / ARCHIVE
    out = [(pd / n, a / "page" / n) for n in ("index.html", "cache") if (pd / n).exists()]
    out += [(od / n, a / n) for n in FIRST_RUN if (od / n).exists()]
    return out


def cmd_archive(args):
    """The first run (renders sharing a process) moved under audibility/first-run-2026-10-27/: renamed, never
    deleted. A plan of this recipe is left alone, so a re-run of the chain resumes; a destination that exists
    refuses (nothing is overwritten)."""
    require_declared()
    od, pd = out_dir(V.OUT), page_dir()
    plan = _load(od / "plan.json")
    if plan and plan.get("recipe") == RECIPE:
        print(f"ARCHIVE DONE (nothing to move: the plan is the {RECIPE} recipe)")
        return
    moves = archive_moves(od, pd)
    if not moves:
        print("ARCHIVE DONE (nothing to move)")
        return
    clash = [str(d) for _, d in moves if d.exists()]
    if clash:
        raise SystemExit(f"the archive already holds {clash}: nothing moved")
    for src, dst in moves:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        print(f"moved {src} -> {dst}")
    print(f"ARCHIVE DONE: {len(moves)} moved under {od / ARCHIVE}")


# --- plan (zero renders) ---------------------------------------------------------------------------------------------

def cmd_plan(args):
    """FS5's "on" examples per effect, the draw of N_MAX, the repeats and the render count, to audibility/plan.json."""
    require_declared()
    root = V.OUT
    od = out_dir(root)
    plan, drift, fs, rend = load_fs5(root)
    enc = T3.encode_for(T3.FULL)
    on_ids, group_of = {e: [] for e in EFFECTS}, {}
    for r in fs:
        group_of[r["i"]] = (r["section"], r["amp"])
        for e in on_effects(enc(r["label"])):
            on_ids[e].append(r["i"])
    chosen = select(on_ids)
    reps = repeats(chosen, group_of)
    jobs = jobs_of(chosen, reps, group_of)
    rec = {"design": DESIGN, "status": STATUS, "recipe": RECIPE, "seed": SEED, "n_max": N_MAX, "tau": TAU,
           "fs5": len(fs), "fs5_sections": len({r["section"] for r in fs}),
           "on": {e: len(v) for e, v in on_ids.items()}, "chosen": chosen,
           "repeats": [{"section": g[0], "amp": g[1], "i": i} for g, i in sorted(reps.items())],
           "jobs": jobs, "groups": len({(j["section"], j["amp"]) for j in jobs}),
           "renders_projected": 2 * len(jobs),          # each job a new process: one priming render, one kept
           "drift": {k: drift[k] for k in ("ok", "plan_lists_sha256", "today_lists_sha256", "frozen")},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    old = _load(od / "plan.json")
    if old and old.get("recipe") != RECIPE:
        raise SystemExit("the stored plan is the first run's (renders sharing a process): run `archive` first")
    if old and plan_unchanged(old, rec):
        print(f"PLAN DONE (unchanged, {od / 'plan.json'}): {len(jobs)} jobs, {rec['renders_projected']} renders")
        return
    if old and (od / "rows").exists() and any((od / "rows").iterdir()):
        raise SystemExit("renders exist and the plan would change: it is fixed")
    if old and not args.force:
        raise SystemExit(f"{od / 'plan.json'} exists and differs (--force to rewrite before any render)")
    od.mkdir(parents=True, exist_ok=True)
    _save(od / "plan.json", rec)
    print(f"FS5: {rec['fs5']} examples in {rec['fs5_sections']} sections; on: {rec['on']}")
    n_on = sum(j["what"] == ON for j in jobs)
    print(f"chosen: { {e: len(v) for e, v in chosen.items()} }; r_on' {n_on}; repeats {len(reps)}; "
          f"groups {rec['groups']}")
    print(f"PLAN DONE: {len(jobs)} jobs, each a new process (1 priming + 1 kept) = {rec['renders_projected']} renders "
          f"projected")


# --- render (MAIN) ---------------------------------------------------------------------------------------------------

SHARD_CMD = "-m learn.audibility_measure render"     # this step's own render shards (siblings, not outside jobs)
SERVER = "au_render_server"


def ps_tree():
    """[(pid, ppid, command)] for every process."""
    import subprocess

    s = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True).stdout
    out = []
    for line in s.split("\n"):
        f = line.split(None, 2)
        if len(f) == 3 and f[0].isdigit() and f[1].isdigit():
            out.append((int(f[0]), int(f[1]), f[2]))
    return out


def outside_servers(rows):
    """Render servers not started by one of this step's render shards (a server's ancestors are walked): the renders
    of other jobs. rows: `ps_tree()`."""
    parent = {p: q for p, q, _ in rows}
    shards = {p for p, _, c in rows if SHARD_CMD in c}
    out = []
    for p, _, c in rows:
        if SERVER not in c:
            continue
        q, seen = parent.get(p), set()
        while q and q not in shards and q not in seen and q != 1:
            seen.add(q)
            q = parent.get(q)
        if q not in shards:
            out.append(p)
    return out


def job_wait_reason(rows, own=()):
    """Why a new process must wait before its renders, or None: a separation running, or a render server of another
    job. Sibling shards never count here (the machine-wide cap of 3 render processes is checked once per shard at its
    start), so the shards cannot wait on each other."""
    from learn import local_objective as LO

    sep = LO.separating([(p, c) for p, _, c in rows], set(own))
    if sep:
        return f"a separation is running (pid {sep[0]})"
    srv = outside_servers(rows)
    if srv:
        return f"another job's render server is running (pid {srv[0]})"
    return None


def wait_for_job(poll_s=30):
    """Wait, printing when a wait starts and ends, until `job_wait_reason` clears."""
    own = (os.getpid(), os.getppid())
    waited = None
    while True:
        why = job_wait_reason(ps_tree(), own)
        if why is None:
            if waited:
                print(f"wait over ({time.time() - waited:.0f} s)", flush=True)
            return
        if not waited:
            waited = time.time()
            print(f"waiting: {why}", flush=True)
        time.sleep(poll_s)


def new_renderer():
    """A new plugin process once `wait_for_job` clears (no separation, no other job's render server), its recipe
    checked (isolate=True, part C's plugin version and average DI)."""
    from learn import direct_stems as DS
    from learn import knob_ceiling as K

    wait_for_job()
    rr = K.Renderer()
    try:
        DS.check_recipe(rr)
    except BaseException:
        rr.close()
        raise
    return rr


def _render_setup(plan3):
    """Once per shard: the machine-wide cap (`local_objective._wait_cap`: fewer than 3 render processes and no
    separation; `direct_stems.wait_render_slot`: the render servers), as every render step checks it at its start; then
    T3's renderer checks (`trusted_data_t3._render_setup`): the menus rebuilt and checked against the live menu and the
    factory gate cap. That renderer only reads the menu (no render) and is closed; every job then opens its own
    (`new_renderer`)."""
    from learn import direct_stems as DS
    from learn import local_objective as LO
    from learn import pretrain_set as PS

    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"free disk below {T.DISK_GUARD_GB:.0f} GB")
    menus = T3.Menus()
    menus.gate_u = plan3["gate_cap"]["unit"]
    print("checking the render cap (3 render processes, no separation)", flush=True)
    LO._wait_cap()
    DS.wait_render_slot()
    rr = new_renderer()
    try:
        T3.check_menu(rr.menu(), menus.dried)
        if abs(F.gate_cap_u(menus.gate_thresholds())[0] - plan3["gate_cap"]["unit"]) > 1e-12:
            raise SystemExit("the factory gate thresholds changed since T3's plan")
    finally:
        rr.close()
    return menus


def cmd_render(args):
    """One shard of whole sections: per job, the example's full twin rebuilt (`full_twin`) and checked against T3's
    render row, then, in a new plugin process primed once with that setting, r_on' (the setting), a repeat of it (which
    must be bit-identical to r_on') or r_off (the effect switched off, checked to encode as off); 0.25 s trimmed,
    written as FLAC with a row."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B

    require_declared()
    root = V.OUT
    od = out_dir(root)
    ap = _load(od / "plan.json")
    if not ap:
        raise SystemExit("run `plan` first")
    if ap.get("recipe") != RECIPE:
        raise SystemExit("the stored plan is the first run's: run `archive`, then `plan`")
    k, n = args.shard
    rp = od / "rows" / f"render-{k}of{n}.jsonl"
    rows = render_rows(od, own=rp)
    failed = [r["i"] for r in rows if r["what"] == REPEAT and not r.get("repeat_exact")]
    if failed:
        raise SystemExit(f"a stored repeat is not bit-identical to its r_on' (ids {failed[:5]}): the recipe failed")
    done = {(r["i"], r["what"]) for r in rows}
    on_sha = {r["i"]: r["audio_sha256"] for r in rows if r["what"] == ON}
    shard = DS.shard_sections(ap["jobs"], n)
    todo = [j for j in ap["jobs"] if shard[j["section"]] == k and (j["i"], j["what"]) not in done]
    if not todo:
        print(f"AUDIBILITY RENDER DONE {k}/{n} (nothing to do)")
        return
    from learn import trusted_data_t3_mix as M

    plan3, _ = M.load_frozen(root)
    rend = T.rows_of(root, T3.STAGE, "render")
    ctx = DS.Ctx(quiet=True)
    ctx.rows = None                                   # part C's rows are not used here (memory beside step (b))
    menus = _render_setup(plan3)
    swap0 = DS.swap_mb()
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    rp.parent.mkdir(parents=True, exist_ok=True)
    t0, di_cache, n_done, renders = time.time(), {}, 0, 0
    with open(rp, "a") as fh:
        for j in todo:
            g = DS._guards("audibility-render", T.DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            i, sid = j["i"], j["section"]
            rw = rend[i]
            if rw.get("refused") or "target" not in rw:
                raise SystemExit(f"{i}: T3 refused this example; it cannot be in FS5")
            amp, mode, base, sel, xf, core, cname, tries = T3.full_twin(i, menus)
            if amp != j["amp"] or LO.sdict(xf) != rw["settings"]:
                raise SystemExit(f"{i}: the rebuilt full twin differs from T3's render row")
            if sid not in di_cache:
                sec = ctx.sections[sid]
                di_cache = {sid: B.measure(PS.section_audio(sec["path"], sec["start_s"])).astype(np.float32)}
            row = {"i": i, "section": sid, "amp": amp, "what": j["what"], "recipe": RECIPE}
            if j["what"] in (ON, REPEAT):
                x = xf
            else:
                x = off_settings(xf, j["what"])
                sw = EFFECTS[j["what"]][0]
                js = F.SW.index(sw)
                e_on, e_off = F.encode(xf, amp), F.encode(x, amp)
                if not (e_on[3][js] > 0 and e_on[2][js] > 0.5) or e_off[2][js] > 0.5:
                    raise SystemExit(f"{i}: {j['what']} does not encode on, then off")
                row["off"] = {"path": "/".join(EFFECTS[j["what"]][1][0]), "value": EFFECTS[j["what"]][1][1]}
            if j["what"] == REPEAT and i not in on_sha:
                raise SystemExit(f"{i}: the repeat comes before its r_on' (the plan's order)")
            y = fresh_render(new_renderer, di_cache[sid], sel, xf, x)
            renders += 2
            y = np.ascontiguousarray((y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]])
            sc, sha = G.write_flac(flac_of(root, i, j["what"]), y, PS.SR)
            row.update(file={"scale": sc, "sha256": sha}, audio_sha256=audio_sha(y), lufs=T.lufs_or_none(y),
                       renders=2, primes=1)
            if j["what"] == ON:
                on_sha[i] = row["audio_sha256"]
            if j["what"] == REPEAT:
                row["repeat_exact"] = row["audio_sha256"] == on_sha[i]
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if j["what"] == REPEAT and not row["repeat_exact"]:
                raise SystemExit(f"{i}: the repeat is not bit-identical to r_on' (the fresh-process recipe fails)")
            n_done += 1
            if n_done % 50 == 0:
                print(f"{n_done}/{len(todo)} jobs; renders {renders} ({renders // 2} priming); "
                      f"{(time.time() - t0) / n_done:.1f} s per job", flush=True)
    print(f"AUDIBILITY RENDER DONE {k}/{n}: {renders} renders ({renders // 2} priming), "
          f"{(time.time() - t0) / 60:.1f} min")


# --- measure (MAIN; zero renders) ---------------------------------------------------------------------------------

_W = {}


def _init_worker():
    from learn import direct_stems as DS

    ctx = DS.Ctx(quiet=True)
    ctx.rows = None
    _W["ctx"], _W["stems"], _W["swap0"] = ctx, T.Stems(ctx), DS.swap_mb()


def _guard(part, swap0):
    """The render steps' disk, memory and swap guard (`direct_stems._guards`), raised as an error that stops the
    measure (in a worker too)."""
    from learn import direct_stems as DS

    g = DS._guards(part, T.DISK_GUARD_GB, swap0)
    if g:
        raise RuntimeError(g[1])


def _measure_section(job):
    """One section's examples: each stored mix rebuilt from the stored target and checked (features, gains, and
    `mix_with` against `self_built_mix`), then m' = r_on' in that backing (`mix_with`), J(r_on', m'), and per render
    row J(r_off, m') and J(r_off, r_on') (or, for a repeat, J(repeat, m'))."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import pretrain_set as PS
    from learn import song_bank as B

    root, sid, exs = job
    ctx = _W["ctx"]
    sec = ctx.sections[sid]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    di = B.measure(PS.section_audio(sec["path"], sec["start_s"])).astype(np.float64)[trim[0]:trim[1]]
    out = []
    for e in exs:
        _guard("audibility-measure", _W.get("swap0"))
        x, i = e["t2"], e["i"]
        y = G.read_flac(T.flac_path(root, T3.STAGE, i, "target"), e["target"]["scale"], e["target"]["sha256"])
        oth = G.read_flac(T.flac_path(root, "t2", i, "others"), e["others"]["scale"], e["others"]["sha256"])
        voc = x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"]
        st = _W["stems"].get(sid, T.backing_tracks(x, voc))
        y, oth = np.asarray(y, np.float64), np.asarray(oth, np.float64)
        m, gains, _ = T.self_built_mix(y, oth, st, x)
        mm, _, _ = DS.half_features(m)
        stored = np.load(T.ex_path(root, T3.STAGE, i, f"mix-{T3.STAGE}"))
        share = T3.feature_share({"mA": mm["A"], "mB": mm["B"]}, stored, ("mA", "mB"))
        gains_ok = all(abs(gains[q] - e["gains"][q]) < 1e-6 for q in ("gb", "ga"))
        mastered = x["draw"]["mastered"]
        mw = mix_with(y, oth, st, e["gains"], i, mastered)
        mix_with_ok = bool(np.allclose(mw, m, rtol=0, atol=1e-9))
        base = {"i": i, "section": sid, "mix_share": share, "gains_ok": gains_ok, "mix_with_ok": mix_with_ok}
        if share < DS.MATCH_SHARE or not gains_ok or not mix_with_ok:
            out.append({**base, "refused": "the stored mix does not rebuild"})
            continue
        on = [r for r in e["renders"] if r["what"] == ON]
        if len(on) != 1:
            out.append({**base, "refused": f"{len(on)} r_on' renders"})
            continue
        f = on[0]["file"]
        r_on = np.asarray(G.read_flac(flac_of(root, i, ON), f["scale"], f["sha256"]), np.float64)
        mp = mix_with(r_on, oth, st, e["gains"], i, mastered)
        j_on = K.judge(mp, r_on, di, 0)
        rows = []
        for r in e["renders"]:
            if r["what"] == ON:
                continue
            f = r["file"]
            z = np.asarray(G.read_flac(flac_of(root, i, r["what"]), f["scale"], f["sha256"]), np.float64)
            j_m = K.judge(mp, z, di, 0)
            if r["what"] == REPEAT:
                rows.append({"what": REPEAT, "j_m": j_m, "floor": a_e(j_on, j_m),
                             "repeat_exact": r.get("repeat_exact")})
            else:
                rows.append({"what": r["what"], "j_m": j_m, "a": a_e(j_on, j_m),
                             "solo": solo(K.judge(r_on, z, di, 0)), "clean": clean_pair(e["settings"], r["what"])})
        out.append({**base, "j_on": j_on, "rows": rows})
    return out


def cmd_measure(args):
    """Every rendered pair's A_e and solo distance, each group's repeat (it must be bit-identical, or the step refuses
    before writing anything), and the first run's A_e against this run's on the clean pairs, to
    audibility/measure.json."""
    from multiprocessing import Pool

    require_declared()
    root = V.OUT
    od = out_dir(root)
    ap = _load(od / "plan.json")
    if not ap:
        raise SystemExit("run `plan` first")
    if ap.get("recipe") != RECIPE:
        raise SystemExit("the stored plan is the first run's: run `archive`, then `plan`")
    rows = render_rows(od)
    inexact = [(r["i"], r["section"]) for r in rows if r["what"] == REPEAT and not r.get("repeat_exact")]
    if inexact:
        raise SystemExit(f"{len(inexact)} repeats are not bit-identical to their r_on' (e.g. {inexact[:3]}): refused")
    have ={(r["i"], r["what"]) for r in rows}
    missing = [j for j in ap["jobs"] if (j["i"], j["what"]) not in have]
    if missing:
        raise SystemExit(f"{len(missing)} planned renders are missing (e.g. {missing[:3]})")
    t2 = {x["i"]: x for x in _load(T.plan_path(root, "t2"))["examples"]}
    t2rend = T.rows_of(root, "t2", "render")
    rend, built = T.rows_of(root, T3.STAGE, "render"), T.rows_of(root, T3.STAGE, "build")
    by = {}
    for r in rows:
        by.setdefault(r["section"], {}).setdefault(r["i"], []).append(r)
    jobs = [(root, sid, [{"i": i, "t2": t2[i], "target": rend[i]["target"], "others": t2rend[i]["others_file"],
                          "gains": built[i]["gains_db"], "settings": rend[i]["settings"], "renders": rs}
                         for i, rs in sorted(exs.items())])
            for sid, exs in sorted(by.items())]
    from learn import direct_stems as DS

    _guard("audibility-measure", DS.swap_mb())
    t0 = time.time()
    with Pool(min(WORKERS, len(jobs)), initializer=_init_worker) as pool:
        res = [r for part in pool.imap_unordered(_measure_section, jobs) for r in part]
        print(f"{len(res)} examples measured in {time.time() - t0:.0f} s", flush=True)
    res.sort(key=lambda r: r["i"])
    pairs, floors = [], []
    for r in res:
        for q in r.get("rows", []):
            if q["what"] == REPEAT:
                floors.append({"i": r["i"], "section": r["section"], "floor": q["floor"],
                               "repeat_exact": q["repeat_exact"]})
            else:
                a = q["a"] or {}
                pairs.append({"i": r["i"], "section": r["section"], "effect": q["what"], "a_e": a.get("a_e"),
                              "signed": a.get("signed"), "halves": a.get("halves"), "solo": q["solo"],
                              "clean": q["clean"]})
    old = _load(od / ARCHIVE / "measure.json") or {}
    old_ae = {(p["effect"], p["i"]): p["a_e"] for p in old.get("pairs", [])}
    new_ae = {(p["effect"], p["i"]): p["a_e"] for p in pairs}
    cons = consistency(old_ae, new_ae, {(p["effect"], p["i"]) for p in pairs if p["clean"]}) if old_ae else None
    summ = {}
    for e in EFFECTS:
        v = [p for p in pairs if p["effect"] == e]
        fin = [p["a_e"] for p in v if p["a_e"] is not None]
        summ[e] = {"pairs": len(v), "measured": len(fin), "below_tau": sum(a < TAU for a in fin),
                   "share_below_tau": (sum(a < TAU for a in fin) / len(fin)) if fin else None,
                   "negative_signed": sum(1 for p in v if p["signed"] is not None and p["signed"] < 0),
                   "a_e": quantiles(fin), "solo": quantiles([p["solo"] for p in v])}
    fl = [f["floor"]["a_e"] for f in floors if f["floor"]]
    rec = {"design": DESIGN, "status": STATUS, "recipe": RECIPE, "tau": TAU, "examples": len(res),
           "refused": [{"i": r["i"], "why": r["refused"]} for r in res if r.get("refused")],
           "renders": render_count(od), "rows": len(rows),
           "repeat_floor": {"groups": len(floors), "repeat_exact": sum(bool(f["repeat_exact"]) for f in floors),
                            "a_e": quantiles(fl)},
           "clean_pairs": {e: sum(1 for p in pairs if p["effect"] == e and p["clean"]) for e in EFFECTS},
           "first_run_consistency": cons,
           "summary": summ, "pairs": pairs, "floors": floors, "examples_detail": res,
           "minutes": round((time.time() - t0) / 60, 1), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(od / "measure.json", rec)
    print(f"renders used: {rec['renders']}")
    print(f"repeat floor: {rec['repeat_floor']}")
    print(f"clean pairs (no other modulated effect on): {rec['clean_pairs']}")
    print(f"first run against this run, clean pairs: {cons}")
    for e, s in summ.items():
        print(f"{e:13s} measured {s['measured']:3d}/{s['pairs']:3d}; below tau {s['below_tau']} "
              f"({0 if s['share_below_tau'] is None else s['share_below_tau']:.2f}); negative {s['negative_signed']}; "
              f"A_e {s['a_e']}")
    print(f"refused: {len(rec['refused'])}")
    print(f"MEASURE DONE: {od / 'measure.json'}")


def run_totals(counts):
    """Renders over a shard's rows: each process run counts from zero, so a run ends where the running count drops.
    counts: [(renders_so_far, primes_so_far)] in file order. -> (renders, priming)."""
    tot_r = tot_p = 0
    prev = None
    for c in counts:
        if prev is not None and c[0] < prev[0]:
            tot_r, tot_p = tot_r + prev[0], tot_p + prev[1]
        prev = c
    if prev is not None:
        tot_r, tot_p = tot_r + prev[0], tot_p + prev[1]
    return tot_r, tot_p


def render_count(od):
    """{renders, priming} over every shard's rows: each row is one new process, its own priming render and the one
    kept (a job that rendered and wrote no row is not seen). The first run's rows carried running counts
    (`run_totals`)."""
    tot = {"renders": 0, "priming": 0}
    for r in render_rows(od):
        tot["renders"] += r["renders"]
        tot["priming"] += r["primes"]
    return tot


# --- read (MAIN; zero renders) ------------------------------------------------------------------------------------

def spearman(a, b):
    """Spearman's rho over the pairs where both are finite; None with fewer than 5. -> (rho, n)."""
    import numpy as np
    from scipy.stats import spearmanr

    v = [(x, y) for x, y in zip(a, b) if x is not None and y is not None and math.isfinite(x) and math.isfinite(y)]
    if len(v) < 5:
        return None, len(v)
    r = spearmanr(np.array([p[0] for p in v]), np.array([p[1] for p in v])).correlation
    return (float(r) if math.isfinite(r) else None), len(v)


def cmd_read(args):
    """The tone probe's switch readouts for the target, the mix and the stem (its probes refitted, deterministic),
    read on FS5 with "off" against the "on" examples in each A_e subset; plus A_e against the proxy level and the solo
    distance. The probe's stored "all on" row must reproduce."""
    from learn import tone_info_probe as P

    require_declared()
    root = V.OUT
    od = out_dir(root)
    meas = _load(od / "measure.json")
    if not meas:
        raise SystemExit("run `measure` first")
    if meas.get("recipe") != RECIPE:
        raise SystemExit("measure.json is not the fresh-process recipe's")
    read, corr = read_rows(meas, _load(P.out_dir(root) / "audible.json"))
    rec = {"design": DESIGN, "status": STATUS, "tau": TAU, "lists_check": P.LISTS.get("check"), "read": read,
           "spearman": corr, "renders": meas.get("renders"), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(od / "read.json", rec)
    for e, r in read.items():
        print(f"\n{e} (cuts {None if r['cuts'] is None else [round(c, 4) for c in r['cuts']]}); Spearman A_e vs proxy "
              f"{corr[e]['a_e_vs_proxy']}, vs solo {corr[e]['a_e_vs_solo']}")
        for which, row in r["rows"].items():
            cells = []
            for key in "abc":
                x = row[key]
                iv = "no interval" if x["lo"] is None else f"[{x['lo']:.3f},{x['hi']:.3f}]"
                pt = "n/a" if x["point"] is None else f"{x['point']:.3f}"
                cells.append(f"{key} {pt} {iv}{' R' if x['readable'] else ''} ({x['n_on']}/{x['n_off']})")
            print(f"  {which:16s} " + " | ".join(cells))
    print(f"READ DONE: {od / 'read.json'}")


def reproduce_fail(stored, sw, key, now, tol=1e-9):
    """Why the refitted probe's all-on AUC does not reproduce the tone probe's stored one (audible.json), or None.
    A missing file, switch, input or point refuses too: the check is declared, never skipped."""
    if not stored:
        return "the tone probe's audible.json is missing"
    try:
        ref = stored["read"][sw]["all on"][key]["point"]
    except (KeyError, TypeError):
        return f"audible.json holds no all-on point for {sw} ({key})"
    if ref is None or now is None:
        return f"an undefined all-on AUC (stored {ref}, refitted {now})"
    if abs(now - ref) > tol:
        return f"the refitted probe's all-on AUC {now} is not the stored {ref}"
    return None


def read_rows(meas, stored):
    """`cmd_read`'s rows from a measure record and the tone probe's stored audible.json. -> (read, spearman)."""
    import numpy as np

    from learn import tone_info_probe as P
    from learn import trusted_data_t3_r as R

    if not stored:
        raise SystemExit("the tone probe's audible.json is missing: the all-on check cannot run")
    root_, _, tr, fs, _ = P.load_sets()
    S = P.prepare(root_, tr, fs)
    lab_te, sec, ids = S["lab_te"], S["sec"], S["ids"]
    pos = {i: n for n, i in enumerate(ids)}
    by = {(p["effect"], p["i"]): p for p in meas["pairs"]}
    refused = {r["i"] for r in meas["refused"]}
    preds, read, corr, t0 = {}, {}, {}, time.time()
    for key in "abc":
        preds[key], _ = P.fit_input(S, key, tr, fs)
        print(f"({key}) {P.INPUTS[key]} refitted ({time.time() - t0:.0f} s)", flush=True)
    for e, (sw, _, px) in EFFECTS.items():
        js, jp = F.SW.index(sw), F.CONT.index(px)
        m = lab_te[3][:, js] > 0
        on = lab_te[2][m, js] > 0.5
        mids = [i for i, ok in zip(ids, m) if ok]
        ae = np.array([np.nan if i in refused or (e, i) not in by or by[(e, i)]["a_e"] is None
                       else by[(e, i)]["a_e"] for i in mids])
        g = np.array([sec[i] for i in mids])
        cuts = thirds(ae[on])
        read[e] = {"cuts": cuts, "rows": {}}
        for which in WHICH:
            k = subset(on, ae, which, cuts)
            row = {}
            for key in "abc":
                q = preds[key]["sw_p"][m, js]
                st = R.jackknife_auc(on[k], q[k], g[k])
                ok, _ = R.readable("switch", st)
                row[key] = {**st, "readable": ok, "n_on": int((on & k).sum()), "n_off": int((~on & k).sum())}
            read[e]["rows"][which] = row
        for key in "abc":
            why = reproduce_fail(stored, sw, key, read[e]["rows"]["all on"][key]["point"])
            if why:
                raise SystemExit(f"{e} ({key}): {why}")
        meas_on = [i for i in mids if (e, i) in by and by[(e, i)]["a_e"] is not None and i not in refused]
        proxy = [float(lab_te[0][pos[i], jp]) for i in meas_on]
        aes = [by[(e, i)]["a_e"] for i in meas_on]
        corr[e] = {"a_e_vs_proxy": spearman(aes, proxy),
                   "a_e_vs_solo": spearman(aes, [by[(e, i)]["solo"] for i in meas_on])}
    return read, corr


# --- page (MAIN; zero renders) ------------------------------------------------------------------------------------

def page_dir():
    return V.HOME / "listening" / PAGE_NAME


def key_path(root):
    """The page's answer key, kept with the measurement and away from the listening folder."""
    return out_dir(root) / "page-key.json"


def pair_audio(root, it, stems, t2, t2rend, built, rows, cache):
    """(on mix, off mix) for a page item: m' (r_on' in the stored backing at the stored gains and mastering,
    `mix_with`) and r_off in the same backing; both renders sit at the same process position. "same": m' twice.
    rows: {(i, what): render row}."""
    import numpy as np

    from learn import direct_sound_gate as G

    i, e = it["i"], it["effect"]
    x = t2[i]
    if i not in cache:
        r = rows[(i, ON)]
        y = np.asarray(G.read_flac(flac_of(root, i, ON), r["file"]["scale"], r["file"]["sha256"]), np.float64)
        o = t2rend[i]["others_file"]
        oth = np.asarray(G.read_flac(T.flac_path(root, "t2", i, "others"), o["scale"], o["sha256"]), np.float64)
        voc = x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"]
        st = stems.get(x["section"], T.backing_tracks(x, voc))
        cache.clear()
        cache[i] = (y, oth, st)
    y, oth, st = cache[i]
    gains = built[i]["gains_db"]
    m_on = mix_with(y, oth, st, gains, i, x["draw"]["mastered"])
    if it["kind"] == "same":
        return m_on, m_on.copy()
    r = rows[(i, e)]
    z = np.asarray(G.read_flac(flac_of(root, i, e), r["file"]["scale"], r["file"]["sha256"]), np.float64)
    return m_on, mix_with(z, oth, st, gains, i, x["draw"]["mastered"])


def level_free(a, b):
    """Both clips at the same loudness, each levelled on its own (`build_data_review.level_clip`, -23 LUFS), as the
    judge levels render and mix apart: A_e cannot see a level change the effect makes, so the ear check must not hear
    one either. If the true-peak ceiling lowers one clip, the other is lowered by as much. -> (a', b')."""
    from learn import build_data_review as BDR

    ya, _, _, ca = BDR.level_clip(a)
    yb, _, _, cb = BDR.level_clip(b)
    cut = max(ca, cb)
    return ya * 10 ** (-(cut - ca) / 20), yb * 10 ** (-(cut - cb) / 20)


def aac_b64(flac, cache, kbps=PAGE_KBPS):
    """AAC (mono, `kbps`) of a FLAC clip, cached by the clip's hash and bitrate, as base64."""
    import base64
    import subprocess

    h = hashlib.sha256(pathlib.Path(flac).read_bytes()).hexdigest()[:16]
    out = pathlib.Path(cache) / f"{h}-{kbps}.m4a"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(out.stem + ".tmp.m4a")
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", str(kbps * 1000), str(flac), str(tmp)],
                       check=True)
        tmp.replace(out)
    return base64.b64encode(out.read_bytes()).decode()


def pair_clips(a, b, cache_dir):
    """Both clips level-free (`level_free`: each at -23 LUFS on its own), 10-ms fades, AAC at PAGE_KBPS, base64."""
    import numpy as np
    import soundfile as sf

    from learn import build_data_review as BDR

    out = []
    for v in level_free(np.asarray(a, np.float64), np.asarray(b, np.float64)):
        y = BDR.fade(v)
        h = hashlib.sha256(y.astype(np.float32).tobytes()).hexdigest()[:16]
        flac = pathlib.Path(cache_dir) / f"{h}.flac"
        flac.parent.mkdir(parents=True, exist_ok=True)
        if not flac.exists():
            sf.write(str(flac), y, BDR.SR, subtype="PCM_24")
        out.append(aac_b64(flac, cache_dir))
    return out


def page_html(items, clips, build):
    """The page: per item, the two mixes one after the other (blind order), "do they differ?"; the ear page's style,
    player and export (`build_ear_page`)."""
    from learn import build_ear_page as BEP

    e = html.escape
    total = len(items)
    secs = {it["id"]: 2 * 10.0 + BEP.GAP_S + BEP.DECIDE_S for it in items}
    cards = []
    for n, it in enumerate(items):
        a, b = it["id"] + "-1", it["id"] + "-2"
        vs = "".join(f'<button type="button" class="v" data-v="{v}">{e(t)}</button>' for v, t in VERDICTS)
        cards.append(
            f'<article class="item" data-id="{it["id"]}" data-n="{n + 1}"><div class="num">{n + 1} / {total}</div>'
            f'<h3>Listen for: {e(it["effect"])}</h3><p class="sub">The same 10 s of a song twice</p>'
            f'<div class="plays"><button type="button" class="play main" data-seq="{a},{b}" '
            f'data-names="the first mix|the second mix">&#9654; Play both</button>'
            f'<button type="button" class="play small" data-seq="{a}" data-names="the first mix">First only</button>'
            f'<button type="button" class="play small" data-seq="{b}" data-names="the second mix">Second only</button>'
            f'</div><p class="now"></p><div class="vs">{vs}</div>'
            f'<input class="note" type="text" placeholder="Note (optional)" aria-label="Note"></article>')
    data = {"page": PAGE_NAME, "part": 1, "build": build,
            "items": [{"id": it["id"], "title": f"Listen for: {it['effect']}", "subtitle": ""} for it in items],
            "secs": secs}
    minutes = round(sum(secs.values()) / 60)
    js = BEP.JS.replace("GAP_MS", str(int(BEP.GAP_S * 1000)))
    data_json = json.dumps(data).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Effect audibility check</title>
<style>{BEP.CSS}</style></head><body>
<header><div class="hrow"><b>Can you hear the effect in the song?</b><span id="count"></span></div>
<div class="hrow"><label><input type="checkbox" id="auto"> Autoplay next</label>
<span id="left" class="ask"></span></div><div class="prog"><div id="bar"></div></div></header>
<main>
<h1>Do the two mixes differ?</h1>
<p class="intro">{total} items, about {minutes} minutes. Each Play button plays the same 10 seconds of a song twice.
In one, the guitar's named effect is on; in the other it is switched off, and nothing else changes. The order is
random, and a few items are the very same mix twice. Answer whether you hear <b>any</b> difference, however small.
Both clips are set to the same loudness, so listen for the effect itself, not a volume change. Headphones help.
Answers are saved in this browser as you go; tap <b>Export</b> any time, even halfway, and send the file.</p>
{"".join(cards)}
</main>
<footer><button type="button" id="next">Next unanswered</button>
<button type="button" id="export" class="primary">Export</button></footer>
<div id="exp"><b>Your answers</b><p class="ask">Save it as a file, or copy it, and send it.</p>
<textarea id="out" readonly></textarea>
<div class="row"><button type="button" id="copy">Copy</button><button type="button" id="save">Save file</button>
<button type="button" id="close">Close</button></div></div>
<audio id="player" preload="none" playsinline></audio>
<script id="data" type="application/json">{data_json}</script>
<script id="clips" type="application/json">{json.dumps(clips)}</script>
<script>{js}</script></body></html>"""


def cmd_page(args):
    """The ear check of tau: `page_items` from measure.json, each pair rendered as two mixes. The blind page and its
    clips go to listening/audibility-mix/; the key (each item's effect, example, kind, A_e and play order) goes to
    trusted-data/audibility/page-key.json, outside the listening folder. Reading an export against the key is for the
    relabel's declaration (no reader here yet)."""
    from learn import direct_stems as DS

    require_declared()
    root = V.OUT
    meas = _load(out_dir(root) / "measure.json")
    if not meas:
        raise SystemExit("run `measure` first")
    if meas.get("recipe") != RECIPE:
        raise SystemExit("measure.json is not the fresh-process recipe's: the page is built from it only")
    refused = {r["i"] for r in meas["refused"]}
    items = page_items([p for p in meas["pairs"] if p["i"] not in refused])
    pd, kp = page_dir(), key_path(root)
    if kp.exists() and not args.force:
        raise SystemExit(f"{kp} exists: a rebuild hides the listener's stored answers (--force)")
    ctx = DS.Ctx(quiet=True)
    ctx.rows = None
    stems = T.Stems(ctx)
    t2 = {x["i"]: x for x in _load(T.plan_path(root, "t2"))["examples"]}
    t2rend = T.rows_of(root, "t2", "render")
    built = T.rows_of(root, T3.STAGE, "build")
    rows = {(r["i"], r["what"]): r for r in render_rows(out_dir(root))}
    clips, cache = {}, {}
    for it in sorted(items, key=lambda it: it["i"]):
        on, off = pair_audio(root, it, stems, t2, t2rend, built, rows, cache)
        first, second = (on, off) if it["first"] == "on" else (off, on)
        clips[it["id"] + "-1"], clips[it["id"] + "-2"] = pair_clips(first, second, pd / "cache")
    key = {"page": PAGE_NAME, "tau": TAU, "seed": PAGE_SEED, "items": items, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    build = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    key["build"] = build
    pd.mkdir(parents=True, exist_ok=True)
    _save(kp, key)
    p = pd / "index.html"
    p.write_text(page_html(items, clips, build))
    print(f"PAGE DONE: {len(items)} items, {p.stat().st_size / 1e6:.1f} MB -> {p}")


COMMANDS = {"archive": cmd_archive, "plan": cmd_plan, "render": cmd_render, "measure": cmd_measure, "read": cmd_read,
            "page": cmd_page}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="audibility_measure", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=tuple(COMMANDS))
    ap.add_argument("--shard", type=V.parse_shard, default=(0, 1))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    if args.shard != (0, 1) and args.cmd != "render":
        raise SystemExit("--shard is for render")
    if args.force and args.cmd not in ("plan", "page"):
        raise SystemExit("--force is for plan and page")
    return COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
