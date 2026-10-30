"""The clean/crunch pool's step 4: the listening page (`docs/clean-crunch-pool-plan.md`, step 4; ledger
`clean-crunch-pool-dcc`, `amendment_3`). ROADMAP (c)'s ear check of tau on clean/crunch mixes: the user found FS5's
audibility pairs, the exposed ones too, too dense to hear. Descriptive: it decides nothing and relabels nothing. A thin
adapter over `audibility_measure`: the same effects, A_e, recipe (`amendment_5_fix`: every render in its own new
plugin process, primed once with the example's own setting) and page rule, read on the D_CC pool's kept examples.
Outputs go to `trusted-data/cc-audibility/` and `listening/cc-audibility/` only; `cc/` is read, never written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    $MAIN -m learn.cc_audibility plan                   # zero renders: the candidates, the draw, the jobs
    $MAIN -u -m learn.cc_audibility render --shard k/3  # r_on', r_off, repeats: 2 renders per job
    $MAIN -m learn.cc_audibility measure                # zero renders: A_e and solo per pair, the repeat floor
    $MAIN -m learn.cc_audibility page                   # the blind page and its key (the key outside the page)

**The pairs.** A D_CC pool example (kept: built, not refused) qualifies when its guitar is exposed by the earlier
exposed page's rule (`audibility_measure.EXPOSED`: drawn ratio at least -6 dB, no vocals drawn, at most 2 other
guitars, counting this pool's recorded amp-track stand-ins), its backing holds a drum and a bass track
(`data_cleaning.track_class`) each playing within PLAYS_WITHIN_DB of the backing in its 10-s window, its band is not
one of the pool's heavy bands, and its drawn tone is typical: part C's "factory" or "start" mode (centred on a factory
or starting preset), not the uniform "wide" draw, with the drawn class (part C's base) the section's class. Per effect
at most N_MAX "on" examples, seeded (`audibility_measure.select`). Each job's new plugin process opens through
`cc_build.new_renderer` after a wait for any running separation (`new_process`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import time

from learn import audibility_measure as AM
from learn import cc_build as CB
from learn import trusted_data as T
from learn import trusted_data_t3 as T3
from learn import verify_tracks as V

OUT_DIR = "cc-audibility"                       # trusted-data/cc-audibility/
PAGE_NAME = "cc-audibility"                     # listening/cc-audibility/
LEDGER_ID = CB.LEDGER_ID                        # clean-crunch-pool-dcc
LEDGER_KEY = "amendment_3"
LEDGER_MARK = "Step 4's listening page"
N_MAX = 30                                      # "on" examples measured per effect
SEED = 20261115                                 # the draw of N_MAX among more
PAGE_SEED = 20261116                            # the page's order and each pair's play order
TYPICAL_MODES = ("factory", "start")            # part C's draws centred on a real preset (not "wide")
CLASS_MATCH = True                              # the drawn setting's class (part C's base) is the section's class
NEEDS = ("drums", "bass")                       # the backing must hold one track of each, playing in the window
PLAYS_WITHIN_DB = 20.0                          # each needed class's summed level within this of the backing's

_save, _load = V._save, V._load


# --- pure ---------------------------------------------------------------------------------------------------------

def drawn_stems(x):
    """The stems an example's drawn vocal variant sums."""
    return x["stems"]["v"] if x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"] else x["stems"]["n"]


def backing_classes(x):
    """The track classes of the stems an example's drawn vocal variant sums (`data_cleaning.track_class`)."""
    from learn import data_cleaning as DC

    return {DC.track_class(s) for s in drawn_stems(x)}


def exposed(x, rule=AM.EXPOSED):
    """The earlier exposed page's rule (`audibility_measure.exposed`), with this pool's recorded amp-track stand-ins
    counted as other guitars beside the rendered ones: they sit in the backing too."""
    d = x["draw"]
    n = len(x["others"]) + len(x.get("amp_tracks") or [])
    return d["ratio_db"] >= rule["min_ratio_db"] and bool(d["vocals_drawn"]) == rule["vocals"] and n <= rule["max_others"]


def plays(levels, need=NEEDS, within=PLAYS_WITHIN_DB):
    """Each needed class plays in the window: its summed tracks' RMS level (dB) at least the backing's less `within`.
    levels: {class: dB, "all": the drawn stems' sum}."""
    return all(levels.get(c) is not None and levels[c] >= levels["all"] - within for c in need)


def qualifies(x, levels_of, heavy=CB.HEAVY_BANDS):
    """(ok, why): the page's rule on one pool example (its plan recipe); `levels_of(x)` reads the window's audio
    (`window_levels`) and is called last."""
    if not exposed(x):
        return False, "not exposed"
    if not set(NEEDS) <= backing_classes(x):
        return False, "no drums or no bass track in the backing"
    if x["band"] in heavy:
        return False, "a heavy band"
    if x.get("mode") not in TYPICAL_MODES:
        return False, "an atypical tone (part C's wide draw)"
    if CLASS_MATCH and x.get("base") != x.get("cls"):
        return False, "the drawn class is not the section's"
    if not plays(levels_of(x)):
        return False, "drums or bass not playing in the window"
    return True, None


def window_levels(ctx, cache=None):
    """levels_of(x) -> {class: dB, "all": dB}: the RMS level of each track class's summed stems, and of all the drawn
    stems, over the example's section window (cached per section and stem list)."""
    import math

    cache = {} if cache is None else cache

    def levels_of(x):
        import numpy as np

        from learn import data_cleaning as DC
        from learn import pretrain_set as PS

        st = drawn_stems(x)
        key = (x["section"], tuple(st))
        if key not in cache:
            sec = ctx.sections[x["section"]]
            sess = pathlib.Path(ctx.inv[sec["di"]]["session_dir"])
            acc = {}
            for t in st:
                c = DC.track_class(t)
                acc[c] = acc.get(c, 0.0) + PS.section_audio(sess / t, sec["start_s"])

            def db(v):
                r = float(np.sqrt(np.mean(np.asarray(v, np.float64) ** 2)))
                return -120.0 if r <= 0 else 20 * math.log10(r)
            cache[key] = {**{c: db(v) for c, v in acc.items()}, "all": db(sum(acc.values()))}
        return cache[key]
    return levels_of


def candidates(rows, ex, levels_of):
    """({effect: [ids]}, {id: (section, amp)}, {why: n}) over the kept pool rows (`cc_build.arm_rows`'s) and their
    plan recipes `ex`."""
    import collections

    enc = T3.encode_for(T3.FULL)
    on = {e: [] for e in AM.EFFECTS}
    group, why = {}, collections.Counter()
    for r in rows:
        ok, w = qualifies(ex[r["i"]], levels_of)
        if not ok:
            why[w] += 1
            continue
        group[r["i"]] = (r["section"], r["amp"])
        for e in AM.on_effects(enc(r["label"])):
            on[e].append(r["i"])
    return on, group, dict(why)


def wait_no_separation(poll_s=30):
    """amendment_5_fix's wait before each new plugin process: no separation running (`local_objective.separating`).
    The render cap itself is `cc_build.new_renderer`'s (a machine-wide render slot)."""
    from learn import local_objective as LO

    own = {os.getpid(), os.getppid()}
    waited = None
    while True:
        sep = LO.separating([(p, c) for p, _, c in AM.ps_tree()], own)
        if not sep:
            if waited:
                print(f"wait over ({time.time() - waited:.0f} s)", flush=True)
            return
        if not waited:
            waited = time.time()
            print(f"waiting: a separation is running (pid {sep[0]})", flush=True)
        time.sleep(poll_s)


def new_process():
    """One new plugin process for one job: the separation wait, then `cc_build.new_renderer` (a free render slot
    under the machine-wide cap, the recipe checked). `audibility_measure.new_renderer` is not used: it counts every
    render server outside its own shards as another job's, so this module's shards would wait on each other."""
    wait_no_separation()
    return CB.new_renderer()


# --- I/O ------------------------------------------------------------------------------------------------------------

def out_dir(root):
    return pathlib.Path(root) / OUT_DIR


def flac_of(root, i, what):
    return out_dir(root) / "renders" / f"{i}-{what.replace(' ', '_')}.flac"


def key_path(root):
    return out_dir(root) / "page-key.json"


def page_dir(args):
    """The listening folder: ~/ndsp-presets/listening/cc-audibility for real runs; under --out for a smoke run, so a
    smoke run never touches the real page."""
    return (pathlib.Path(args.out) / "listening" if args.smoke else V.HOME / "listening") / PAGE_NAME


def require_run(args):
    """Smoke runs write under a scratch --out only; real runs take no --out (`cc_build.require`'s rule)."""
    if args.smoke and not args.out:
        raise SystemExit("--smoke writes into a scratch --out only")
    if args.out and not args.smoke:
        raise SystemExit("--out is for smoke runs only")


def ledger_declared(path=None):
    d = json.loads(pathlib.Path(path or V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == LEDGER_ID), {})
    return LEDGER_MARK in str(e.get(LEDGER_KEY, ""))


def require_declared():
    if not ledger_declared():
        raise SystemExit(f"the ledger's {LEDGER_ID} has no {LEDGER_KEY} declaring '{LEDGER_MARK}': runs refuse")


def pool(args):
    """(plan, kept rows (train + FS_CC, with labels), {i: recipe}, {i: render row}) of the D_CC pool."""
    plan = CB.load_plan(args)
    tr, fs, _ = CB.arm_rows(args, plan)
    return plan, tr + fs, {x["i"]: x for x in plan["examples"]}, T.rows_of(V.out_root(args), CB.STAGE, "render")


def render_rows(od, own=None):
    """`audibility_measure.render_rows` on this step's folder (the fresh recipe's rows only)."""
    return AM.render_rows(od, own)


def reader(root):
    """read(i, what) -> this step's stored render as float64 (hash-checked)."""
    import numpy as np

    from learn import direct_sound_gate as G

    rows = {(r["i"], r["what"]): r for r in render_rows(out_dir(root))}

    def read(i, what):
        f = rows[(i, what)]["file"]
        return np.asarray(G.read_flac(flac_of(root, i, what), f["scale"], f["sha256"]), np.float64)
    return read


# --- commands ---------------------------------------------------------------------------------------------------------

def cmd_plan(args):
    """The candidates, the draw of N_MAX per effect, the repeats and the jobs (zero renders), to plan.json."""
    require_declared()
    root = V.out_root(args)
    od = out_dir(root)
    _, rows, ex, _ = pool(args)
    on, group, why = candidates(rows, ex, window_levels(CB.ctx_for(args)))
    chosen = AM.select(on, N_MAX, SEED)
    reps = AM.repeats(chosen, group)
    jobs = AM.jobs_of(chosen, reps, group)
    ids = sorted({i for v in chosen.values() for i in v})
    rec = {"plan": CB.PLAN, "ledger": f"{LEDGER_ID} {LEDGER_KEY}", "recipe": AM.RECIPE, "seed": SEED, "n_max": N_MAX,
           "tau": AM.TAU, "rule": {"exposed": AM.EXPOSED, "needs": list(NEEDS), "heavy_out": list(CB.HEAVY_BANDS),
                                    "modes": list(TYPICAL_MODES)},
           "kept": len(rows), "out_by_rule": why, "qualify": len(group), "on": {e: len(v) for e, v in on.items()},
           "chosen": chosen, "examples": len(ids), "sections": len({group[i][0] for i in ids}),
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
    print(f"chosen { {e: len(v) for e, v in chosen.items()} }: {len(ids)} examples in {rec['sections']} sections; "
          f"repeats {len(reps)}")
    print(f"PLAN DONE: {len(jobs)} jobs, each a new process (1 priming + 1 kept) = {rec['renders_projected']} renders")


def cmd_render(args):
    """One shard of whole sections (`audibility_measure.cmd_render`'s recipe on the pool): per job the example's full
    twin rebuilt and checked against its render row, then in a new plugin process primed once with it, r_on', a
    repeat (bit-identical to r_on') or r_off (the effect off, checked to encode off); 0.25 s trimmed; FLAC and a row."""
    require_declared()                              # before any import: the light CI has no numpy
    render_shard(args, out_dir(V.out_root(args)))


def render_shard(args, od, table=AM.EFFECTS, on_sha0=None, flac=None, label="CC AUDIBILITY"):
    """`cmd_render`'s body on any step folder `od` (its plan.json's jobs), effects off from `table`. on_sha0: {i: the
    audio sha256 of an r_on' rendered by an earlier step under the same recipe}, which that example's repeat must
    then match bit for bit (its r_on' reused, not rendered again). flac(root, i, what): where each render is written."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B

    root = V.out_root(args)
    flac = flac or flac_of
    ap = _load(od / "plan.json")
    if not ap or ap.get("recipe") != AM.RECIPE:
        raise SystemExit("run `plan` first")
    k, n = args.shard
    rp = od / "rows" / f"render-{k}of{n}.jsonl"
    rows = render_rows(od, own=rp)
    if any(r["what"] == AM.REPEAT and not r.get("repeat_exact") for r in rows):
        raise SystemExit("a stored repeat is not bit-identical to its r_on': the recipe failed")
    done = {(r["i"], r["what"]) for r in rows}
    on_sha = {**(on_sha0 or {}), **{r["i"]: r["audio_sha256"] for r in rows if r["what"] == AM.ON}}
    shard = DS.shard_sections(ap["jobs"], n)
    todo = [j for j in ap["jobs"] if shard[j["section"]] == k and (j["i"], j["what"]) not in done]
    if not todo:
        print(f"{label} RENDER DONE {k}/{n} (nothing to do)")
        return
    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"free disk below {T.DISK_GUARD_GB:.0f} GB")
    plan = CB.load_plan(args)
    rend = T.rows_of(root, CB.STAGE, "render")
    ctx = CB.ctx_for(args)
    menus = T3.Menus()
    menus.gate_u = plan["gate_cap"]["unit"]
    LO._wait_cap()
    rr = CB.new_renderer()                        # reads the live menu only (no render), then closed
    try:
        T3.check_menu(rr.menu(), menus.dried)
        if abs(F.gate_cap_u(menus.gate_thresholds())[0] - plan["gate_cap"]["unit"]) > 1e-12:
            raise SystemExit("the factory gate thresholds changed since the pool's plan")
    finally:
        rr.close()
    swap0 = DS.swap_mb()
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    rp.parent.mkdir(parents=True, exist_ok=True)
    t0, di_cache, renders = time.time(), {}, 0
    with open(rp, "a") as fh:
        for m, j in enumerate(todo):
            g = DS._guards(f"{label.lower().replace(' ', '-')}-render", T.DISK_GUARD_GB, swap0)  # cc-audibility-render
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            i, sid = j["i"], j["section"]
            rw = rend[i]
            if rw.get("refused") or "target" not in rw:
                raise SystemExit(f"{i}: the pool refused this example; it cannot be on the page")
            amp, mode, base, sel, xf, core, cname, tries = T3.full_twin(i, menus)
            if amp != j["amp"] or LO.sdict(xf) != rw["settings"]:
                raise SystemExit(f"{i}: the rebuilt full twin differs from the pool's render row")
            if sid not in di_cache:
                sec = ctx.sections[sid]
                di_cache = {sid: B.measure(PS.section_audio(sec["path"], sec["start_s"])).astype(np.float32)}
            row = {"i": i, "section": sid, "amp": amp, "what": j["what"], "recipe": AM.RECIPE}
            if j["what"] in (AM.ON, AM.REPEAT):
                x = xf
            else:
                x = AM.off_settings(xf, j["what"], table)
                js = F.SW.index(table[j["what"]][0])
                e_on, e_off = F.encode(xf, amp), F.encode(x, amp)
                if not (e_on[3][js] > 0 and e_on[2][js] > 0.5) or e_off[2][js] > 0.5:
                    raise SystemExit(f"{i}: {j['what']} does not encode on, then off")
                row["off"] = {"path": "/".join(table[j["what"]][1][0]), "value": table[j["what"]][1][1]}
            if j["what"] == AM.REPEAT and i not in on_sha:
                raise SystemExit(f"{i}: the repeat comes before its r_on' (the plan's order)")
            y = AM.fresh_render(new_process, di_cache[sid], sel, xf, x)
            renders += 2
            y = np.ascontiguousarray((y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]])
            sc, sha = G.write_flac(flac(root, i, j["what"]), y, PS.SR)
            row.update(file={"scale": sc, "sha256": sha}, audio_sha256=AM.audio_sha(y), lufs=T.lufs_or_none(y),
                       renders=2, primes=1)
            if j["what"] == AM.ON:
                on_sha[i] = row["audio_sha256"]
            if j["what"] == AM.REPEAT:
                row["repeat_exact"] = row["audio_sha256"] == on_sha[i]
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if j["what"] == AM.REPEAT and not row["repeat_exact"]:
                raise SystemExit(f"{i}: the repeat is not bit-identical to r_on' (the fresh-process recipe fails)")
            if (m + 1) % 25 == 0:
                print(f"{m + 1}/{len(todo)} jobs; renders {renders}; {(time.time() - t0) / (m + 1):.1f} s per job",
                      flush=True)
    print(f"{label} RENDER DONE {k}/{n}: {renders} renders ({renders // 2} priming), "
          f"{(time.time() - t0) / 60:.1f} min")


def backing(root, i, x, rend, stems):
    """(target, other guitars, stems audio) of a pool example, from the pool's stored files."""
    import numpy as np

    from learn import direct_sound_gate as G

    rw = rend[i]
    y = G.read_flac(T.flac_path(root, CB.STAGE, i, "target"), rw["target"]["scale"], rw["target"]["sha256"])
    o = rw["others_file"]
    oth = G.read_flac(T.flac_path(root, CB.STAGE, i, "others"), o["scale"], o["sha256"])
    voc = x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"]
    st = stems.get(x["section"], T.backing_tracks(x, voc))
    return np.asarray(y, np.float64), np.asarray(oth, np.float64), st


def measure_example(root, i, x, rend, built, stems, di, renders, flac=None):
    """One example (`audibility_measure._measure_section`'s steps): the stored mix rebuilt from the stored target and
    checked (features, gains, `mix_with`), then m' = r_on' in that backing, J(r_on', m'), and per render row J(r_off,
    m') and J(r_off, r_on') (a repeat: J(repeat, m')). flac(root, i, what): where each render is read."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import knob_ceiling as K

    flac = flac or flac_of
    y, oth, st = backing(root, i, x, rend, stems)
    m, gains, _ = T.self_built_mix(y, oth, st, x)
    mm, _, _ = DS.half_features(m)
    stored = np.load(T.ex_path(root, CB.STAGE, i, f"mix-{CB.STAGE}"))
    share = T3.feature_share({"mA": mm["A"], "mB": mm["B"]}, stored, ("mA", "mB"))
    g = built[i]["gains_db"]
    gains_ok = all(abs(gains[q] - g[q]) < 1e-6 for q in ("gb", "ga"))
    mw = AM.mix_with(y, oth, st, g, i, x["draw"]["mastered"])
    base = {"i": i, "section": x["section"], "mix_share": share, "gains_ok": gains_ok,
            "mix_with_ok": bool(np.allclose(mw, m, rtol=0, atol=1e-9))}
    if share < DS.MATCH_SHARE or not gains_ok or not base["mix_with_ok"]:
        return {**base, "refused": "the stored mix does not rebuild"}
    on = [r for r in renders if r["what"] == AM.ON]
    if len(on) != 1:
        return {**base, "refused": f"{len(on)} r_on' renders"}
    f = on[0]["file"]
    r_on = np.asarray(G.read_flac(flac(root, i, AM.ON), f["scale"], f["sha256"]), np.float64)
    mp = AM.mix_with(r_on, oth, st, g, i, x["draw"]["mastered"])
    j_on = K.judge(mp, r_on, di, 0)
    rows = []
    for r in renders:
        if r["what"] == AM.ON:
            continue
        f = r["file"]
        z = np.asarray(G.read_flac(flac(root, i, r["what"]), f["scale"], f["sha256"]), np.float64)
        j_m = K.judge(mp, z, di, 0)
        if r["what"] == AM.REPEAT:
            rows.append({"what": AM.REPEAT, "j_m": j_m, "floor": AM.a_e(j_on, j_m), "repeat_exact": r.get("repeat_exact")})
        else:
            rows.append({"what": r["what"], "j_m": j_m, "a": AM.a_e(j_on, j_m), "solo": AM.solo(K.judge(r_on, z, di, 0)),
                         "clean": AM.clean_pair(x["settings"], r["what"])})
    return {**base, "j_on": j_on, "rows": rows}


def cmd_measure(args):
    """Every rendered pair's A_e and solo, each group's repeat floor (every repeat must be bit-identical, or the step
    refuses before writing), to measure.json."""
    require_declared()                              # before any import: the light CI has no numpy
    measure_step(args, out_dir(V.out_root(args)))


def measure_step(args, od, table=AM.EFFECTS, reused=(), flac=None, ledger=f"{LEDGER_ID} {LEDGER_KEY}"):
    """`cmd_measure`'s body on any step folder `od`, the summary per `table` entry. reused: render rows of r_on'
    rendered by an earlier step (read through `flac`), measured beside this step's own rows; `renders` counts this
    step's own only."""
    import numpy as np

    from learn import pretrain_set as PS
    from learn import song_bank as B

    root = V.out_root(args)
    ap = _load(od / "plan.json")
    if not ap:
        raise SystemExit("run `plan` first")
    own = render_rows(od)
    if any(r["what"] == AM.REPEAT and not r.get("repeat_exact") for r in own):
        raise SystemExit("a repeat is not bit-identical to its r_on': refused")
    have = {(r["i"], r["what"]) for r in own}
    missing = [j for j in ap["jobs"] if (j["i"], j["what"]) not in have]
    if missing:
        raise SystemExit(f"{len(missing)} planned renders are missing (e.g. {missing[:3]})")
    rows = own + [r for r in reused if (r["i"], r["what"]) not in have]
    plan = CB.load_plan(args)
    ex = {x["i"]: x for x in plan["examples"]}
    rend, built = T.rows_of(root, CB.STAGE, "render"), T.rows_of(root, CB.STAGE, "build")
    ctx = CB.ctx_for(args)
    stems = T.Stems(ctx)
    by = {}
    for r in rows:
        by.setdefault(r["section"], {}).setdefault(r["i"], []).append(r)
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    t0, res = time.time(), []
    for sid, exs in sorted(by.items()):
        sec = ctx.sections[sid]
        di = B.measure(PS.section_audio(sec["path"], sec["start_s"])).astype(np.float64)[trim[0]:trim[1]]
        for i, rs in sorted(exs.items()):
            res.append(measure_example(root, i, ex[i], rend, built, stems, di, rs, flac))
    pairs, floors = [], []
    for r in res:
        for q in r.get("rows", []):
            if q["what"] == AM.REPEAT:
                floors.append({"i": r["i"], "section": r["section"], "floor": q["floor"], "repeat_exact": q["repeat_exact"]})
            else:
                a = q["a"] or {}
                pairs.append({"i": r["i"], "section": r["section"], "effect": q["what"], "a_e": a.get("a_e"),
                              "signed": a.get("signed"), "halves": a.get("halves"), "solo": q["solo"],
                              "clean": q["clean"]})
    summ = {}
    for e in table:
        fin = [p["a_e"] for p in pairs if p["effect"] == e and p["a_e"] is not None]
        v = [p for p in pairs if p["effect"] == e]
        summ[e] = {"pairs": len(v), "measured": len(fin), "below_tau": sum(a < AM.TAU for a in fin),
                   "share_below_tau": (sum(a < AM.TAU for a in fin) / len(fin)) if fin else None,
                   "negative_signed": sum(1 for p in v if p["signed"] is not None and p["signed"] < 0),
                   "a_e": AM.quantiles(fin), "solo": AM.quantiles([p["solo"] for p in v])}
    fl = [f["floor"]["a_e"] for f in floors if f["floor"]]
    rec = {"plan": CB.PLAN, "ledger": ledger, "recipe": AM.RECIPE, "tau": AM.TAU,
           "examples": len(res), "refused": [{"i": r["i"], "why": r["refused"]} for r in res if r.get("refused")],
           "renders": AM.render_count(od), "rows": len(own), "repeat_floor": {"groups": len(floors),
                                               "repeat_exact": sum(bool(f["repeat_exact"]) for f in floors),
                                               "a_e": AM.quantiles(fl)},
           "summary": summ, "pairs": pairs, "floors": floors, "examples_detail": res,
           "minutes": round((time.time() - t0) / 60, 1), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(od / "measure.json", rec)
    for e, s in summ.items():
        print(f"{e:13s} measured {s['measured']:3d}/{s['pairs']:3d}; below tau {s['below_tau']}; A_e {s['a_e']}")
    print(f"renders used: {rec['renders']}; repeat floor: {rec['repeat_floor']}; refused {len(rec['refused'])}")
    print(f"MEASURE DONE: {od / 'measure.json'}")
    return rec


def cmd_page(args):
    """The blind page (`audibility_measure.page_items` with PAGE_SEED; the pairs as two mixes each, level-free, AAC at
    256 kbps) to listening/cc-audibility/, its key to trusted-data/cc-audibility/page-key.json."""
    require_declared()                              # before any import: the light CI has no numpy
    import numpy as np

    from learn import direct_sound_gate as G

    root = V.out_root(args)
    od = out_dir(root)
    meas = _load(od / "measure.json")
    if not meas or meas.get("recipe") != AM.RECIPE:
        raise SystemExit("run `measure` first")
    refused = {r["i"] for r in meas["refused"]}
    items = AM.page_items([p for p in meas["pairs"] if p["i"] not in refused], seed=PAGE_SEED)
    pd, kp = page_dir(args), key_path(root)
    if kp.exists() and not args.force:
        raise SystemExit(f"{kp} exists: a rebuild hides the listener's stored answers (--force)")
    plan = CB.load_plan(args)
    ex = {x["i"]: x for x in plan["examples"]}
    rend, built = T.rows_of(root, CB.STAGE, "render"), T.rows_of(root, CB.STAGE, "build")
    stems = T.Stems(CB.ctx_for(args))
    rows = {(r["i"], r["what"]): r for r in render_rows(od)}
    clips = {}
    for it in sorted(items, key=lambda it: it["i"]):
        i, x = it["i"], ex[it["i"]]
        _, oth, st = backing(root, i, x, rend, stems)
        g, mst = built[i]["gains_db"], x["draw"]["mastered"]
        r = rows[(i, AM.ON)]
        y = np.asarray(G.read_flac(flac_of(root, i, AM.ON), r["file"]["scale"], r["file"]["sha256"]), np.float64)
        on = AM.mix_with(y, oth, st, g, i, mst)
        if it["kind"] == "same":
            off = on.copy()
        else:
            r = rows[(i, it["effect"])]
            z = np.asarray(G.read_flac(flac_of(root, i, it["effect"]), r["file"]["scale"], r["file"]["sha256"]),
                           np.float64)
            off = AM.mix_with(z, oth, st, g, i, mst)
        first, second = (on, off) if it["first"] == "on" else (off, on)
        clips[it["id"] + "-1"], clips[it["id"] + "-2"] = AM.pair_clips(first, second, pd / "cache")
        it.update(band=x["band"], cls=x.get("cls"), ratio_db=x["draw"]["ratio_db"], others=len(x["others"]),
                  stand_ins=len(x.get("amp_tracks") or []))
    build = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    _save(kp, {"page": PAGE_NAME, "tau": AM.TAU, "seed": PAGE_SEED, "build": build, "items": items,
               "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    pd.mkdir(parents=True, exist_ok=True)
    p = pd / "index.html"
    p.write_text(AM.page_html(items, clips, build, PAGE_NAME))
    print(f"PAGE DONE: {len(items)} items, {p.stat().st_size / 1e6:.1f} MB -> {p}")


COMMANDS = {"plan": cmd_plan, "render": cmd_render, "measure": cmd_measure, "page": cmd_page}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cc_audibility", description=__doc__.split("\n")[0])
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
    require_run(args)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
