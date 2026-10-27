"""ROADMAP step (c), the measurement: how audible each "on" time effect is in its own self-built mix
(`docs/trusted-data-t0-design.md`, "Audibility in the mix: the measurement"; ledger `trusted-data-t3`, amendment 5).
Approved by the user 2026-10-27 ("Yes for all"). Descriptive: it decides nothing and relabels nothing; how a label
may use it waits for the user's three rulings ([research](../docs/research/effect-detection-2026-10.md)). FS5 is
development data; V-real is not touched. Outputs go to `trusted-data/audibility/` and the listening page only; `t0/`,
`t2/`, `t3/` and `tone-probe/` are read, never written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    $MAIN -m learn.audibility_measure plan                   # zero renders: FS5's "on" examples drawn, plan.json
    $MAIN -u -m learn.audibility_measure render --shard k/3  # the effect-off renders, repeats and priming (~900)
    $MAIN -m learn.audibility_measure measure                # zero renders: A_e and the solo distance per pair
    $MAIN -m learn.audibility_measure read                   # zero renders: the tone probe's switches by A_e
    $MAIN -m learn.audibility_measure page                   # the ear check of tau, a listening page

**A_e.** For an FS5 example i with effect e on, r_on is its stored target render, r_off the same setting with e
switched off (rendered here), m its stored self-built mix (rebuilt bit-for-bit from the stored target, other guitars,
stems and draw, and checked against the stored mix features; nothing is re-mixed). The judge J scores a render against
the mix on the two halves; A_e = |mean over halves of log(J(r_off, m) / J(r_on, m))|. Beside it, solo, the plain
distance J(r_off, r_on) (no threshold), and a repeat floor: r_on rendered again once per (section, amp) group.
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
DESIGN = ("docs/trusted-data-t0-design.md#audibility-in-the-mix-the-measurement-roadmap-step-c-declared-2026-10-27-"
          "nothing-run")
STATUS = ("declared 2026-10-27 before any render (ledger trusted-data-t3, amendment 5); descriptive, decides nothing; "
          "FS5 read before by R0, the tone probe and step (a)")
# name: (switch head, the edit that turns it off, the tone probe's proxy for its level)
EFFECTS = {"delay": ("delay/delayActive", (("delay", "delayActive"), "false"), "delay/delayMix"),
           "reverb": ("reverb/reverbActive", (("reverb", "reverbActive"), "false"), "reverb/reverbMix"),
           "tremolo": ("tremolo/tremoloActive", (("tremolo", "tremoloActive"), "false"), "tremolo/tremoloDepth"),
           "pr12 spring": ("pr12Amp/springOn", (("pr12Amp", "pr12Reverb"), "0"), "pr12Amp/pr12Reverb"),
           "sw50r spring": ("sw50rAmp/springOn", (("sw50rAmp", "sw50rReverb"), "0"), "sw50rAmp/sw50rReverb")}
REPEAT = "repeat"                                     # r_on rendered again: the render's own floor
N_MAX = 200                                           # "on" examples per effect (the research's ranked change 2)
SEED = 20261113                                       # the draw of N_MAX among more (set here)
PAGE_SEED = 20261114                                  # the page's order and each pair's play order (set here)
TAU = 0.005                                           # the every-control plan's log bar: the starting threshold
NEAR = 2                                              # page: the pairs nearest tau on each side, per effect
CATCH = 3                                             # page: identical pairs (the mix against itself)
WORKERS = 4                                           # measure: one section per worker (as the tone probe's 4)
HALVES = ("A", "B")
WHICH = ("all on", "measured", "bottom third", "middle third", "top third", "below tau", "at or above tau")
PAGE_NAME = "audibility-mix"
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
    """{(section, amp): the group's least chosen id}: one repeat render of r_on per group that renders anything."""
    out = {}
    for ids in chosen.values():
        for i in ids:
            g = group_of[i]
            out[g] = min(i, out.get(g, i))
    return out


def jobs_of(chosen, reps, group_of):
    """The renders, in (section, amp, id) order, each id's repeat first and its effects in EFFECTS order: a group
    primes once. -> [{"i", "section", "amp", "what"}]."""
    rank = {REPEAT: -1, **{e: k for k, e in enumerate(EFFECTS)}}
    out = [{"i": i, "section": g[0], "amp": g[1], "what": REPEAT} for g, i in reps.items()]
    out += [{"i": i, "section": group_of[i][0], "amp": group_of[i][1], "what": e} for e, ids in chosen.items() for i in ids]
    return sorted(out, key=lambda j: (j["section"], j["amp"], j["i"], rank[j["what"]]))


def plan_unchanged(old, new):
    """The stored plan and a recomputed one draw the same renders (a re-run of the chain resumes)."""
    return all(old.get(k) == new.get(k) for k in ("seed", "n_max", "tau", "chosen", "jobs"))


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


def ledger_declared():
    d = json.loads((V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == T3.LEDGER_ID), {})
    return LEDGER_MARK in str(e.get(LEDGER_KEY, ""))


def require_declared():
    if not ledger_declared():
        raise SystemExit(f"the ledger's {T3.LEDGER_ID} has no {LEDGER_KEY} declaring '{LEDGER_MARK}': runs refuse")


def mix_with(r, others, stems_audio, gains, i, mastered):
    """A mix of render r with an example's stored backing at its stored gains (gb, ga) and its mastering draw: the
    stored mix when r is the stored target, the listening page's "off" mix when r is r_off."""
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
    rec = {"design": DESIGN, "status": STATUS, "seed": SEED, "n_max": N_MAX, "tau": TAU,
           "fs5": len(fs), "fs5_sections": len({r["section"] for r in fs}),
           "on": {e: len(v) for e, v in on_ids.items()}, "chosen": chosen,
           "repeats": [{"section": g[0], "amp": g[1], "i": i} for g, i in sorted(reps.items())],
           "jobs": jobs, "groups": len({(j["section"], j["amp"]) for j in jobs}),
           "renders_projected": len(jobs) + len({(j["section"], j["amp"]) for j in jobs}),
           "drift": {k: drift[k] for k in ("ok", "plan_lists_sha256", "today_lists_sha256", "frozen")},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    old = _load(od / "plan.json")
    if old and plan_unchanged(old, rec):
        print(f"PLAN DONE (unchanged, {od / 'plan.json'}): {len(jobs)} renders + {rec['groups']} priming")
        return
    if old and (od / "rows").exists() and any((od / "rows").iterdir()):
        raise SystemExit("renders exist and the plan would change: it is fixed")
    if old and not args.force:
        raise SystemExit(f"{od / 'plan.json'} exists and differs (--force to rewrite before any render)")
    od.mkdir(parents=True, exist_ok=True)
    _save(od / "plan.json", rec)
    print(f"FS5: {rec['fs5']} examples in {rec['fs5_sections']} sections; on: {rec['on']}")
    print(f"chosen: { {e: len(v) for e, v in chosen.items()} }; repeats {len(reps)}; groups {rec['groups']}")
    print(f"PLAN DONE: {len(jobs)} renders + {rec['groups']} priming = {rec['renders_projected']} projected")


# --- render (MAIN) ---------------------------------------------------------------------------------------------------

def _render_setup(plan3):
    """T3's renderer setup (`trusted_data_t3._render_setup`) without its rows path: the menus rebuilt and checked
    against the live menu and the factory gate cap, the render-slot waits, isolate=True, the priming rule."""
    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS

    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"free disk below {T.DISK_GUARD_GB:.0f} GB")
    menus = T3.Menus()
    menus.gate_u = plan3["gate_cap"]["unit"]
    LO._wait_cap()
    DS.wait_render_slot()
    rr = K.Renderer()
    try:
        DS.check_recipe(rr)
        T3.check_menu(rr.menu(), menus.dried)
        if abs(F.gate_cap_u(menus.gate_thresholds())[0] - plan3["gate_cap"]["unit"]) > 1e-12:
            raise SystemExit("the factory gate thresholds changed since T3's plan")
    except BaseException:
        rr.close()
        raise
    return menus, rr, DS.Primer(rr)


def cmd_render(args):
    """One shard of whole sections: per job, the example's full twin rebuilt (`full_twin`) and checked against T3's
    render row, then r_on again (a repeat, checked against the stored target's mels) or r_off (the effect switched
    off, checked to encode as off), 0.25 s trimmed, written as FLAC with a row."""
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
    k, n = args.shard
    rp = od / "rows" / f"render-{k}of{n}.jsonl"
    done = set()
    for p in sorted((od / "rows").glob("render-*.jsonl")) if (od / "rows").exists() else []:
        for ln in p.read_text().splitlines():
            if ln.strip():
                r = json.loads(ln)
                done.add((r["i"], r["what"]))
    shard = DS.shard_sections(ap["jobs"], n)
    todo = [j for j in ap["jobs"] if shard[j["section"]] == k and (j["i"], j["what"]) not in done]
    if not todo:
        print(f"AUDIBILITY RENDER DONE {k}/{n} (nothing to do)")
        return
    from learn import trusted_data_t3_mix as M

    plan3, _ = M.load_frozen(root)
    rend = T.rows_of(root, T3.STAGE, "render")
    ctx = DS.Ctx(quiet=True)
    menus, rr, primer = _render_setup(plan3)
    swap0 = DS.swap_mb()
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    rp.parent.mkdir(parents=True, exist_ok=True)
    t0, di_cache, n_done = time.time(), {}, 0
    try:
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
                row = {"i": i, "section": sid, "amp": amp, "what": j["what"]}
                if j["what"] == REPEAT:
                    x = xf
                else:
                    x = off_settings(xf, j["what"])
                    sw = EFFECTS[j["what"]][0]
                    js = F.SW.index(sw)
                    e_on, e_off = F.encode(xf, amp), F.encode(x, amp)
                    if not (e_on[3][js] > 0 and e_on[2][js] > 0.5) or e_off[2][js] > 0.5:
                        raise SystemExit(f"{i}: {j['what']} does not encode on, then off")
                    row["off"] = {"path": "/".join(EFFECTS[j["what"]][1][0]), "value": EFFECTS[j["what"]][1][1]}
                y = primer.render((sid, amp), di_cache[sid], sel, x)
                y = (y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]]
                if j["what"] == REPEAT:
                    stored = np.load(T3.tgt_path(root, i))
                    h = PS.halves_mel(y)
                    row["repeat_share"] = min(DS.match_share(h[q], stored[f"g{q}"]) for q in h)
                    row["repeat_ok"] = row["repeat_share"] >= DS.MATCH_SHARE
                sc, sha = G.write_flac(flac_of(root, i, j["what"]), y, PS.SR)
                row.update(file={"scale": sc, "sha256": sha}, lufs=T.lufs_or_none(y), renders_so_far=primer.renders,
                           primes_so_far=primer.primes)
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                n_done += 1
                if n_done % 50 == 0:
                    print(f"{n_done}/{len(todo)} jobs; renders {primer.renders} ({primer.primes} priming); "
                          f"{(time.time() - t0) / n_done:.1f} s per job", flush=True)
    finally:
        rr.close()
    print(f"AUDIBILITY RENDER DONE {k}/{n}: {primer.renders} renders ({primer.primes} priming), "
          f"{(time.time() - t0) / 60:.1f} min")


# --- measure (MAIN; zero renders) ---------------------------------------------------------------------------------

_W = {}


def _init_worker():
    from learn import direct_stems as DS

    ctx = DS.Ctx(quiet=True)
    ctx.rows = None
    _W["ctx"], _W["stems"] = ctx, T.Stems(ctx)


def _measure_section(job):
    """One section's examples: each stored mix rebuilt and checked, then J(r_on, m), and per render row J(r_off, m)
    and J(r_off, r_on) (or, for a repeat, J(r_on', m))."""
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
        base = {"i": i, "section": sid, "mix_share": share, "gains_ok": gains_ok}
        if share < DS.MATCH_SHARE or not gains_ok:
            out.append({**base, "refused": "the stored mix does not rebuild"})
            continue
        j_on = K.judge(m, y, di, 0)
        rows = []
        for r in e["renders"]:
            z = np.asarray(G.read_flac(flac_of(root, i, r["what"]), r["file"]["scale"], r["file"]["sha256"]), np.float64)
            j_m = K.judge(m, z, di, 0)
            if r["what"] == REPEAT:
                rows.append({"what": REPEAT, "j_m": j_m, "floor": a_e(j_on, j_m), "repeat_ok": r.get("repeat_ok")})
            else:
                rows.append({"what": r["what"], "j_m": j_m, "a": a_e(j_on, j_m), "solo": solo(K.judge(y, z, di, 0))})
        out.append({**base, "j_on": j_on, "rows": rows})
    return out


def cmd_measure(args):
    """Every rendered pair's A_e and solo distance, and each group's repeat floor, to audibility/measure.json."""
    from multiprocessing import Pool

    require_declared()
    root = V.OUT
    od = out_dir(root)
    ap = _load(od / "plan.json")
    if not ap:
        raise SystemExit("run `plan` first")
    rows = []
    for p in sorted((od / "rows").glob("render-*.jsonl")):
        rows += [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]
    have = {(r["i"], r["what"]) for r in rows}
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
                          "gains": built[i]["gains_db"], "renders": rs} for i, rs in sorted(exs.items())])
            for sid, exs in sorted(by.items())]
    t0 = time.time()
    with Pool(min(WORKERS, len(jobs)), initializer=_init_worker) as pool:
        res = [r for part in pool.imap_unordered(_measure_section, jobs) for r in part]
        print(f"{len(res)} examples measured in {time.time() - t0:.0f} s", flush=True)
    res.sort(key=lambda r: r["i"])
    pairs, floors = [], []
    for r in res:
        for q in r.get("rows", []):
            if q["what"] == REPEAT:
                floors.append({"i": r["i"], "section": r["section"], "floor": q["floor"], "repeat_ok": q["repeat_ok"]})
            else:
                a = q["a"] or {}
                pairs.append({"i": r["i"], "section": r["section"], "effect": q["what"], "a_e": a.get("a_e"),
                              "signed": a.get("signed"), "halves": a.get("halves"), "solo": q["solo"]})
    bad_groups = {f["section"] for f in floors if not f["repeat_ok"]}
    summ = {}
    for e in EFFECTS:
        v = [p for p in pairs if p["effect"] == e]
        fin = [p["a_e"] for p in v if p["a_e"] is not None]
        summ[e] = {"pairs": len(v), "measured": len(fin), "below_tau": sum(a < TAU for a in fin),
                   "share_below_tau": (sum(a < TAU for a in fin) / len(fin)) if fin else None,
                   "negative_signed": sum(1 for p in v if p["signed"] is not None and p["signed"] < 0),
                   "a_e": quantiles(fin), "solo": quantiles([p["solo"] for p in v])}
    fl = [f["floor"]["a_e"] for f in floors if f["floor"]]
    rec = {"design": DESIGN, "status": STATUS, "tau": TAU, "examples": len(res),
           "refused": [{"i": r["i"], "why": r["refused"]} for r in res if r.get("refused")],
           "renders": render_count(od), "rows": len(rows),
           "repeat_floor": {"groups": len(floors), "repeat_mel_ok": sum(bool(f["repeat_ok"]) for f in floors),
                            "a_e": quantiles(fl), "sections_with_a_failed_repeat": sorted(bad_groups)},
           "summary": summ, "pairs": pairs, "floors": floors, "examples_detail": res,
           "minutes": round((time.time() - t0) / 60, 1), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(od / "measure.json", rec)
    print(f"renders used: {rec['renders']}")
    print(f"repeat floor: {rec['repeat_floor']}")
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
    """{renders, priming} over every shard's rows (`run_totals`; a run that rendered and wrote no row is not seen)."""
    tot = {"renders": 0, "priming": 0}
    for p in sorted((od / "rows").glob("render-*.jsonl")):
        c = [(r["renders_so_far"], r["primes_so_far"]) for r in
             (json.loads(ln) for ln in p.read_text().splitlines() if ln.strip())]
        r, q = run_totals(c)
        tot["renders"] += r
        tot["priming"] += q
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


def read_rows(meas, stored):
    """`cmd_read`'s rows from a measure record and the tone probe's stored audible.json. -> (read, spearman)."""
    import numpy as np

    from learn import tone_info_probe as P
    from learn import trusted_data_t3_r as R

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
            ref = (((stored or {}).get("read") or {}).get(sw) or {}).get("all on", {}).get(key, {}).get("point")
            now = read[e]["rows"]["all on"][key]["point"]
            if ref is not None and (now is None or abs(now - ref) > 1e-9):
                raise SystemExit(f"{e} ({key}): the refitted probe's all-on AUC {now} is not the stored {ref}")
        meas_on = [i for i in mids if (e, i) in by and by[(e, i)]["a_e"] is not None and i not in refused]
        proxy = [float(lab_te[0][pos[i], jp]) for i in meas_on]
        aes = [by[(e, i)]["a_e"] for i in meas_on]
        corr[e] = {"a_e_vs_proxy": spearman(aes, proxy), "a_e_vs_solo": spearman(aes, [by[(e, i)]["solo"] for i in meas_on])}
    return read, corr


# --- page (MAIN; zero renders) ------------------------------------------------------------------------------------

def page_dir():
    return V.HOME / "listening" / PAGE_NAME


def pair_audio(root, it, ctx, stems, t2, t2rend, rend, built, cache):
    """(on mix, off mix) for a page item: the stored mix rebuilt, and r_off in the same backing at the same gains and
    mastering (`mix_with`); "same": the stored mix twice."""
    import numpy as np

    from learn import direct_sound_gate as G

    i, e = it["i"], it["effect"]
    x = t2[i]
    if i not in cache:
        tg = rend[i]["target"]
        y = np.asarray(G.read_flac(T.flac_path(root, T3.STAGE, i, "target"), tg["scale"], tg["sha256"]), np.float64)
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
    rows = [json.loads(ln) for p in sorted((out_dir(root) / "rows").glob("render-*.jsonl"))
            for ln in p.read_text().splitlines() if ln.strip()]
    r = next(r for r in rows if r["i"] == i and r["what"] == e)
    z = np.asarray(G.read_flac(flac_of(root, i, e), r["file"]["scale"], r["file"]["sha256"]), np.float64)
    return m_on, mix_with(z, oth, st, gains, i, x["draw"]["mastered"])


def pair_clips(a, b, cache_dir):
    """Both clips with ONE gain (the "on" mix at -23 LUFS, lowered together if either would pass -1 dBTP), 10-ms
    fades, AAC, base64: the level difference the effect makes is kept."""
    import numpy as np
    import soundfile as sf

    from analysis import io

    from learn import build_data_review as BDR

    _, g, _, _ = BDR.level_clip(a)
    pk = max(io.true_peak_dbtp(io.from_samples((v * 10 ** (g / 20)).reshape(-1, 1), BDR.SR)) or -120.0 for v in (a, b))
    if pk > BDR.PEAK_CEILING_DBTP:
        g -= pk - BDR.PEAK_CEILING_DBTP
    out = []
    for v in (a, b):
        y = BDR.fade(np.asarray(v, np.float64) * 10 ** (g / 20))
        h = hashlib.sha256(y.astype(np.float32).tobytes()).hexdigest()[:16]
        flac = pathlib.Path(cache_dir) / f"{h}.flac"
        flac.parent.mkdir(parents=True, exist_ok=True)
        if not flac.exists():
            sf.write(str(flac), y, BDR.SR, subtype="PCM_24")
        out.append(BDR.aac_b64(flac, cache_dir))
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
Both clips share one volume, so a level change counts too. Headphones help. Answers are saved in this browser as you
go; tap <b>Export</b> any time, even halfway, and send the file.</p>
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
    """The ear check of tau: `page_items` from measure.json, each pair rendered as two mixes; the page, and items.json
    (the key: each item's effect, example, kind, A_e and play order; never shown on the page)."""
    from learn import direct_stems as DS

    require_declared()
    root = V.OUT
    meas = _load(out_dir(root) / "measure.json")
    if not meas:
        raise SystemExit("run `measure` first")
    refused = {r["i"] for r in meas["refused"]}
    items = page_items([p for p in meas["pairs"] if p["i"] not in refused])
    pd = page_dir()
    if (pd / "items.json").exists() and not args.force:
        raise SystemExit(f"{pd / 'items.json'} exists: a rebuild hides the listener's stored answers (--force)")
    ctx = DS.Ctx(quiet=True)
    ctx.rows = None
    stems = T.Stems(ctx)
    t2 = {x["i"]: x for x in _load(T.plan_path(root, "t2"))["examples"]}
    t2rend = T.rows_of(root, "t2", "render")
    rend, built = T.rows_of(root, T3.STAGE, "render"), T.rows_of(root, T3.STAGE, "build")
    clips, cache = {}, {}
    for it in sorted(items, key=lambda it: it["i"]):
        on, off = pair_audio(root, it, ctx, stems, t2, t2rend, rend, built, cache)
        first, second = (on, off) if it["first"] == "on" else (off, on)
        clips[it["id"] + "-1"], clips[it["id"] + "-2"] = pair_clips(first, second, pd / "cache")
    key = {"page": PAGE_NAME, "tau": TAU, "seed": PAGE_SEED, "items": items, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    build = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    key["build"] = build
    pd.mkdir(parents=True, exist_ok=True)
    _save(pd / "items.json", key)
    p = pd / "index.html"
    p.write_text(page_html(items, clips, build))
    print(f"PAGE DONE: {len(items)} items, {p.stat().st_size / 1e6:.1f} MB -> {p}")


COMMANDS = {"plan": cmd_plan, "render": cmd_render, "measure": cmd_measure, "read": cmd_read, "page": cmd_page}


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
