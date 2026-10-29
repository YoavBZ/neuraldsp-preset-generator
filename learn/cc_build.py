"""The clean/crunch pool's step 2 build and its arm D_CC (`docs/clean-crunch-pool-plan.md`, steps 2-3, approved by the
user on 2026-10-28, "Yes for all"; ledger `clean-crunch-pool-dcc`). The pool's examples are new: part
C never drew the released sessions, so each example is drawn here as part C draws one (`pretrain_set.plan_example`,
`settings_for`) with T3's full twin on top (`trusted_data_t3.full_twin`: every control, part C's mode), and built by
T2's recipe (`trusted_data.example_recipe`, rule 1, the cap, the per-example leak rule). D_CC trains with D_F5's
recipe and is read by `learn.cc_readout`.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    MSST=~/ndsp-presets/tools/msst-venv/bin/python; TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MAIN -m learn.cc_build verdicts                   # zero audio: the ear's and the measures' verdicts per DI
    $MAIN -u -m learn.cc_build checks --shard k/3      # zero renders: D2/D4 per window, each section's gain class
    $MAIN -u -m learn.cc_build stem-scan               # zero renders: T0's stem scan on the tier-1 sessions it lacks
    $MAIN -u -m learn.cc_build amp-bleed --shard k/3   # zero renders: rule 1's bleed check on the needed amp tracks
    $MAIN -u -m learn.cc_build cleaning-scan --shard k/3   # zero renders: the cleaning scan where it has no row
    $MAIN -m learn.cc_build ear-page                   # zero renders: part 13, the stem spot-checks and flagged DIs
    $MAIN -m learn.cc_build plan [--dry]               # zero renders: the yield, the composition, every recipe
                                                       # (dry only: --no-bleed-gate, --sum-lower; amendment 1)
    $MAIN -u -m learn.cc_build render --shard k/3      # renders: each target in its own process; the other guitars
    $MSST -m learn.cc_build build --device mps|cpu     # mixes and X-LANCE stems
    $MAIN -m learn.cc_build check                      # every example built or refused, by reason
    $TORCH_PY -m learn.cc_build train --seed 20261042|20261043

**The DIs** (`verdicts`): a released DI trains only when the ear heard it clean (ear pages parts 11 and 12, and 13's
DI cards once answered; a later part's answer replaces an earlier part's "not sure" on the same DI; any processed,
not-a-DI or hum answer excludes it) and step 0's DI-level measures pass (D3 passes, D1 not failed; D2 gates each window,
not the DI: amendment 1). Tier 1: Adam Buckley's DIs as T0 verifies them (decision A); Quicksand ElecGtr1 (T0's
measure DI, verified) and ElecGtr2 (heard clean, held by D4 alone, which no longer holds a DI the ear heard clean);
Quicksand ElecGtr3 is out until heard. Turbosauro (no clean section in part A's manifest) and Starnes And Shah ElecGtr4
(too short) stay out. The heavy share: Storm Of Particles and Ale Lak, T0-verified DIs, classed sections only. Death
Of A Romantic and Hollow Ground are out (decision D). Every DI row passes `cc_pool.check_pool_rows`.

**The sections.** A target section is part A's clean section (no screen flag) of a training DI, usable under T0's
section rule (D2 on the window passes; D4 not flagged unless the ear heard the window or the DI clean; not silent),
and not high gain. Its class: the ear's call on an overlapping heard window, else part A's class, else part A's classifier on its
own amp track (T3's order, `trusted_data_t3.gain_class`); a heavy band's unclassed section is out. T0's statuses stand
where T0 measured (Adam Buckley, Storm Of Particles, Ale Lak); `checks` measures the rest the same way
(`verify_tracks.di_processing`, `DiD2`, part A's stored flags).

**The examples** (`plan`). Rule 1 and the cap as T2 ran them (`apply_rule1` with `doubles_out`, `apply_cap`); a
section whose rule-1 amp tracks have no cleaning scan row is left out (fail closed). The fit and early-stopping set
(FS_CC): T2's early-stopping rule (about 5% of each band's sections, at least one) plus 2 more per band (FS5's rule),
never more than half a band's sections. Training: N_TRAIN examples (F5's count) over the training sections by part
C's cycle (`pretrain_set.section_for`), FS_CC's at the same rate per section. Heavy training sections are dropped,
seeded, until heavy examples are at most 20%. Example i = CC_BASE + j (under part C's validation ids).

**Renders.** isolate=True; the target (its full twin) in a fresh renderer process with one discarded priming render
of its own setting (the carry-over rule: time effects keep state within a process), 0.25 s trimmed; the other
guitars (today's space, S's modules: no time effects) as T2 rendered them, one priming render per (DI, amp). A DT
double takes the target's core setting, as D_F5's did. At most 3 render processes (`local_objective.RENDERS`); 31 GB
disk guard.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import time

from learn import cc_pool as CP
from learn import trusted_data as T
from learn import verify_tracks as V

STAGE = "cc"
PLAN = CP.PLAN
LEDGER_ID = "clean-crunch-pool-dcc"              # the pool's own entry (cc_pool's entry: "its own entries before any render")
LEDGER_KEY = "declaration"
LEDGER_MARK = "D_CC (clean/crunch pool steps 2-3"
ARM = "D_CC"
HOME = CP.HOME
INTAKE = HOME / "learn/trusted-data/intake-2026-10-28"
LISTEN = HOME / "listening/trusted-data-ear"
EAR_PARTS = {11: (INTAKE / "ear-answers-part11.json", LISTEN / "part11-clean-crunch/items.json"),
             12: (INTAKE / "ear-answers-part12.json", LISTEN / "part12-clean-crunch-di-amp/items.json")}
REJECT = ("processed", "not_a_di", "hum")
TIER1_MEASURE = {"cambridge/TheTravellingBand_Quicksand_Full/16_ElecGtr1DI.wav": "cambridge-Quicksand-ElecGtr1",
                 "cambridge/TheTravellingBand_Quicksand_Full/19_ElecGtr2DI.wav": "cambridge-Quicksand-ElecGtr2"}
D4_CONFLICT = ["conflict: heard clean, D4 flags it"]    # T0's why when only D4 held a heard-clean DI (no longer holds)
TIER1_STEP0 = {"cambridge/TheTravellingBand_Quicksand_Full/22_ElecGtr3DI.wav": "TheTravellingBand_Quicksand_Full"}
TIER1_T0_BANDS = ("Adam Buckley",)               # decision A: T0's verified DIs and sections
HEAVY_BANDS = ("Storm Of Particles", "Ale Lak")  # classed, non-high-gain sections only, at most HEAVY_MAX
HEAVY_OUT = ("Death Of A Romantic", "Hollow Ground")   # decision D: every DI high gain
HEAVY_MAX = 0.20
CC_BASE = 800_000                                # example ids: CC_BASE + j (training), FS_BASE + j (FS_CC)
FS_BASE = 900_000
N_TRAIN = 3_467                                  # F5's training examples (the plan: the size matches F5)
CC_SEED = 20261110                               # the section cycle (set here)
HEAVY_SEED = 20261111                            # which heavy sections stay under the cap (set here)
FS_EXTRA = 2                                     # FS5's 2 more sections per band
FS_SEED = 20261112
NO_SCAN = "no cleaning scan row"
BLEED_GATE = True          # rule 1's bleed gate on stand-ins (today's); `plan --no-bleed-gate` reads the user's open
                           # policy question (a stand-in's non-guitar bleed is what the real mix holds too)
DEVICES = ("mps", "cpu")
SPOT_PART = 13                                   # the stem spot-check page for the pool's unheard sessions
SPOT_DIR = LISTEN / "part13-clean-crunch-stems"
SPOT_ANSWERS = INTAKE / "ear-answers-part13.json"
SPOT_PAGE = "trusted-data-ear-clean-crunch"
TIER1_STEMS = "ccstems-tier1.json"               # T0's root: the tier-1 sessions' stem scan

_save, _load = V._save, V._load


# --- pure: the ear and the admission ------------------------------------------------------------------------------

def ear_windows(parts):
    """parts: [(answers {id: answer}, items [item])], oldest first. -> ({DI path: [(part, start_s, verdict)]},
    {DI path: [(start_s, class verdict, note)]}): every heard DI window and every heard amp-track class."""
    dis, cls = {}, {}
    for n, (ans, items) in enumerate(parts):
        for it in items:
            a = ans.get(it["id"])
            if a is None:
                continue
            if it["family"] == "di":
                dis.setdefault(it["paths"]["di"], []).append((n, float(it["start_s"]), a["verdict"]))
            elif it["family"] == "scope":
                cls.setdefault(it["paths"]["di"], []).append((float(it["start_s"]), a["verdict"], a.get("note") or ""))
    return dis, cls


def ear_verdict(heard):
    """A DI's ear verdict from its heard windows [(part, start, verdict)]: 'rejected' on any processed, not-a-DI or
    hum answer; else 'clean' when every answer is clean once a later part's answers replace the earlier parts'
    'unsure'; else 'unsure' (None when never heard)."""
    if not heard:
        return None
    if any(v in REJECT for _, _, v in heard):
        return "rejected"
    last = max(p for p, _, _ in heard)
    vs = [v for p, _, v in heard if not (v == "unsure" and p < last and any(q > p for q, _, _ in heard))]
    return "clean" if vs and all(v == "clean" for v in vs) else "unsure"


def measured_ok(status):
    """Step 0's DI-level measures: D3 passes and D1 is not failed. D2 gates each window (`section_status`), not the
    whole DI, as T0's `di_row_status` reads it (the audit, 2026-10-29: step 0 had combined D2 over every picked
    window, so one flagged window kept the DI from the ear). The ear still decides (`admit`)."""
    return bool(status) and status.get("D3") == "pass" and status.get("D1") != "fail"


def admit(ear, status):
    """(trains, why) for a released DI: the ear heard it clean and the measures passed (fails closed)."""
    if not measured_ok(status):
        return False, f"step 0's measures: {status}"
    if ear != "clean":
        return False, f"the ear: {ear or 'never heard'}"
    return True, "heard clean; measures pass"


def overlap_s(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def ear_class(start_s, heard, dur=V.CROP_S, min_s=5.0):
    """The ear's class call on a section from the amp-track windows heard overlapping it by at least `min_s`: high
    gain wins, then crunch, then clean; 'unsure' and 'not_fit' are no call. -> class or None."""
    calls = {v for t, v, _ in heard if overlap_s(start_s, start_s + dur, t, t + dur) >= min_s}
    for c in ("high_gain", "crunch", "clean"):
        if c in calls:
            return c.replace("_", "-")
    return None


def section_status(d2, d4, heard_clean_covers, di_heard_clean=False):
    """T0's section rule: D2 fail excludes; D4 'silent' is silent; a D4 flag sends the window to the ear unless the
    ear has heard it, or the DI, clean (D4 does not override the ear: the audit, 2026-10-29); else usable."""
    if d2 == "fail":
        return "excluded"
    if d4 == "silent":
        return "silent"
    if d4 == "fail" and not (heard_clean_covers or di_heard_clean):
        return "pending ear"
    return "usable"


# --- pure: the composition ----------------------------------------------------------------------------------------

def fs_sections(by_band, share=T.ES_SHARE, es_seed=T.ES_SEED, extra=FS_EXTRA, seed=FS_SEED):
    """FS_CC: T2's early-stopping draw (`trusted_data.es_sections`) plus `extra` more per band (FS5's rule), never
    more than half of a band's sections (floor; a band of one section keeps it for training). -> sorted ids."""
    es = set(T.es_sections(by_band, share, es_seed))
    rng = random.Random(seed)
    out = []
    for band in sorted(by_band):
        secs = sorted(by_band[band])
        cap = len(secs) // 2
        mine = sorted(s for s in secs if s in es)[:cap]
        rest = sorted(set(secs) - set(mine))
        mine += rng.sample(rest, min(extra, len(rest), max(0, cap - len(mine))))
        out += mine
    return sorted(out)


def heavy_trim(train_by_band, heavy=HEAVY_BANDS, cap=HEAVY_MAX, seed=HEAVY_SEED):
    """Drop heavy training sections (seeded, bands in sorted order, one at a time from the largest heavy band) until
    heavy sections are at most `cap` of all training sections; examples follow sections one to one under part C's
    cycle. -> ({band: kept sections}, [dropped])."""
    rng = random.Random(seed)
    out = {b: sorted(v) for b, v in train_by_band.items()}
    for b in out:
        if b in heavy:
            rng.shuffle(out[b])
    dropped = []

    def share():
        n = sum(len(v) for v in out.values())
        return sum(len(v) for b, v in out.items() if b in heavy) / n if n else 0.0

    while share() > cap + 1e-12:
        b = max((b for b in out if b in heavy and out[b]), key=lambda b: (len(out[b]), b))
        dropped.append(out[b].pop())
    return {b: sorted(v) for b, v in out.items() if v}, sorted(dropped)


def allocate(sections, n, base, seed=CC_SEED):
    """n examples over `sections` (sorted) by part C's cycle (`pretrain_set.section_for`). -> [(i, section)]."""
    from learn import pretrain_set as PS

    secs = sorted(sections)
    if not secs:
        return []
    return [(base + j, secs[PS.section_for(j, len(secs), seed)]) for j in range(n)]


def check_ids(ids):
    """Every example id lies in this pool's range and under part C's validation ids (`direct_stems.merge_candidates`
    asserts training rows below them)."""
    from learn import direct_stems as DS

    bad = [i for i in ids if not (CC_BASE <= i < DS.VAL_BASE_ID)]
    if bad:
        raise SystemExit(f"example ids outside [{CC_BASE}, {DS.VAL_BASE_ID}): {bad[:3]}")


# --- data: the sources ----------------------------------------------------------------------------------------------

def root_of(args):
    return T.stage_root(V.out_root(args), STAGE)


def ledger_declared(path=None):
    d = json.loads(pathlib.Path(path or V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == LEDGER_ID), {})
    return LEDGER_MARK in str(e.get(LEDGER_KEY, ""))


def require(args, renders=False):
    """Smoke runs write to a scratch --out; real runs need the ledger's declaration (before any render)."""
    if getattr(args, "smoke", False):
        if not getattr(args, "out", None):
            raise SystemExit("--smoke writes into a scratch --out only")
        return
    if getattr(args, "out", None):
        raise SystemExit("--out is for smoke runs only")
    if renders and not ledger_declared():
        raise SystemExit(f"no `{LEDGER_KEY}` declaration ({LEDGER_MARK!r}) in the ledger's {LEDGER_ID!r} entry")


def ear_parts():
    """Parts 11 and 12, and part 13 (its DI cards) once its answers exist."""
    out = dict(EAR_PARTS)
    if SPOT_ANSWERS.exists():
        out[SPOT_PART] = (SPOT_ANSWERS, SPOT_DIR / "items.json")
    return out


def load_ear():
    parts = []
    for n, (ap, ip) in sorted(ear_parts().items()):
        a, it = json.loads(ap.read_text()), json.loads(ip.read_text())
        if a.get("build") != it.get("build") or a.get("part") != n:
            raise SystemExit(f"ear part {n}: the answers' build {a.get('build')} is not the page's {it.get('build')}")
        parts.append(({x["id"]: x for x in a["answers"]}, it["items"]))
    return ear_windows(parts)


def verdicts():
    """{DI id: {"band", "path", "ear", "heard", "classes", "measures", "trains", "why", "source"}} over the released
    inventory, tier 1 and the heavy bands (zero audio)."""
    from learn import pretrain_set as PS

    tr = T.load_lists(V.OUT)
    dis, cls = load_ear()
    summ = json.loads((INTAKE / "summary.json").read_text())["sessions"]
    out = {}
    for r in CP._inv():
        st = (summ.get(r["song"]) or {}).get(pathlib.Path(r["path"]).name, {}).get("status")
        ear = ear_verdict(dis.get(r["path"]))
        ok, why = admit(ear, st)
        out[r["id"]] = {"band": r["band"], "path": r["path"], "source": "released", "ear": ear,
                        "heard": dis.get(r["path"], []), "classes": cls.get(r["path"], []), "measures": st,
                        "trains": ok, "why": why}
    inv = {r["id"]: r for r in json.loads(PS.INVENTORY.read_text())["dis"]}
    for d, slug in TIER1_MEASURE.items():
        v = (tr.get("measure_dis") or {}).get(slug) or {}
        ok = v.get("verdict") == "verified" or v.get("why") == D4_CONFLICT     # heard clean: D4 no longer holds it
        out[d] = {"band": inv[d]["band"], "path": inv[d]["path"], "source": "tier 1 (T0 measure DI)",
                  "ear": "clean" if ok else None, "heard": [], "classes": [], "measures": v.get("status"),
                  "trains": ok, "why": ("T0 verified" if v.get("verdict") == "verified" else
                                        "heard clean; only D4 held it" if ok else f"T0: {v.get('verdict')} {v.get('why')}")}
    for d, key in TIER1_STEP0.items():
        st = (summ.get(key) or {}).get(pathlib.Path(d).name, {}).get("status")
        ear = ear_verdict(dis.get(inv[d]["path"]))
        ok, why = admit(ear, st)
        out[d] = {"band": inv[d]["band"], "path": inv[d]["path"], "source": "tier 1 (step 0)", "ear": ear,
                  "heard": dis.get(inv[d]["path"], []), "classes": cls.get(inv[d]["path"], []), "measures": st,
                  "trains": ok, "why": why}
    for d, v in sorted(tr["dis"].items()):
        band = v.get("band")
        if band in TIER1_T0_BANDS or band in HEAVY_BANDS:
            ok = v["verdict"] == "verified"
            out[d] = {"band": band, "path": inv[d]["path"], "source": "heavy" if band in HEAVY_BANDS else
                      "tier 1 (T0)", "ear": None, "heard": [], "classes": [], "measures": v["status"], "trains": ok,
                      "why": "T0 verified" if ok else f"T0: {v['verdict']} {v.get('why')}"}
    for d, v in out.items():
        if v["band"] in HEAVY_OUT:
            v.update(trains=False, why="decision D: the band is high gain")
    rel = {r["id"]: r for r in CP._inv()}
    CP.check_pool_rows([inv.get(d) or rel[d] for d, v in sorted(out.items()) if v["trains"]])
    return out


def cc_inventory():
    """Every DI row the pool's sessions hold (part A's inventory and the released one), by id."""
    from learn import pretrain_set as PS

    inv = {r["id"]: r for r in json.loads(PS.INVENTORY.read_text())["dis"]}
    for r in CP._inv():
        if r["id"] in inv:
            raise SystemExit(f"{r['id']}: in both inventories")
        inv[r["id"]] = r
    return inv


def manifest_sections(ver):
    """{section id: section} of the training DIs: part A's manifest rows and the released sessions' (cc_pool's)."""
    from learn import pretrain_set as PS

    rows = json.loads(PS.MANIFEST.read_text())["sections"] + json.loads((CP.OUT / "sections.json").read_text())["sections"]
    out = {}
    for s in rows:
        if s["di"] in ver and ver[s["di"]]["trains"]:
            sid = f"{s['di']}@{float(s['start_s']):.1f}"
            out[sid] = {**s, "id": sid}
    return out


class Ctx:
    """`direct_stems.Ctx`'s face for this pool (what `trusted_data`'s plan, recipe and build helpers read): the
    sessions' DI rows, the pool's sections and example rows, part C's ratio prior and evaluation loudness."""

    def __init__(self, inv, sections, rows=()):
        from learn import pretrain_set as PS
        from learn import song_bank as B

        self.inv, self.sections = inv, sections
        self.pool = list(rows)
        self.rows = {r["i"]: r for r in rows}
        self.ratios = PS.ratio_values()
        self.eval_mix = json.loads((B.OUT / "levels.json").read_text())["summary"]["eval_mix_lufs_median"]


def session_of(inv, di):
    return inv[di]["session_dir"]


def windows_needed(inv, sections, trains):
    """{(DI id, start_s)}: every training DI of a candidate section's session at that section's time (an other
    guitar's window must be measured before it can be rendered there); `checks` measures those T0 did not."""
    by_sd = {}
    for d in trains:
        by_sd.setdefault(session_of(inv, d), []).append(d)
    out = set()
    for s in sections.values():
        for d in by_sd.get(session_of(inv, s["di"]), []):
            out.add((d, round(float(s["start_s"]), 1)))
    return out


# --- commands ---------------------------------------------------------------------------------------------------------

def cmd_verdicts(args):
    import collections

    require(args)
    ver = verdicts()
    _save(root_of(args) / "verdicts.json", {"plan": PLAN, "dis": ver, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    by = collections.Counter((v["band"], v["source"], v["trains"]) for v in ver.values())
    for (band, src, ok), n in sorted(by.items()):
        print(f"  {band:24s} {src:24s} {'trains' if ok else 'out':6s} {n}")
    for d, v in sorted(ver.items()):
        if not v["trains"] and v["source"] == "released" and v["ear"] is not None:
            print(f"  out: {d[-60:]}: {v['why']}")
    print(f"VERDICTS: {sum(v['trains'] for v in ver.values())} of {len(ver)} DIs train")


def _ver(args):
    d = _load(root_of(args) / "verdicts.json")
    if not d:
        raise SystemExit("run `verdicts` first")
    if d["dis"] != json.loads(json.dumps(verdicts(), default=float)):
        raise SystemExit("verdicts.json is stale (the ear, the measures or T0's lists changed): rerun `verdicts`")
    return d["dis"]


def cmd_checks(args):
    """Per window of the sessions T0 did not measure: D2 (part A's stored flags, else measured) and D4; per candidate
    section of every training DI: its class (the ear, part A, the classifier on its own amp track)."""
    import numpy as np  # noqa: F401

    from learn import pretrain_set as PS
    from learn import trusted_data_t3 as T3

    require(args)
    ver = _ver(args)
    inv = cc_inventory()
    secs = manifest_sections(ver)
    tr = T.load_lists(V.OUT)
    t0w = T.windows_of(tr)
    trains = {d for d, v in ver.items() if v["trains"]}
    need = sorted((d, t) for d, t in windows_needed(inv, secs, trains) if f"{d}@{t:.1f}" not in (t0w.get(d) or {}))
    flags = {}
    for s in json.loads(PS.MANIFEST.read_text())["sections"] + json.loads((CP.OUT / "sections.json").read_text())["sections"]:
        flags[(s["di"], round(float(s["start_s"]), 1))] = list(s.get("flags") or [])
    k, n = args.shard
    by_di = {}
    for d, t in need:
        by_di.setdefault(d, []).append(t)
    jobs = [d for j, d in enumerate(sorted(by_di)) if j % n == k]
    cjobs = [sid for j, sid in enumerate(sorted(secs)) if j % n == k]
    path = root_of(args) / f"checks-{k}of{n}.json"
    prev = _load(path) or {}
    done_w, done_c = prev.get("windows", {}), prev.get("classes", {})
    ctx = Ctx(inv, secs)
    t0 = time.time()
    for m, d in enumerate(jobs):
        rec = inv[d]
        d2m = None
        for t in sorted(by_di[d]):
            key = f"{d}@{t:.1f}"
            if key in done_w:
                continue
            f = flags.get((d, t))
            src = "part A's flags"
            if f is None:
                d2m = d2m or V.DiD2(rec["path"])
                f = d2m.window(t)[0]
                src = "measured here"
            d4 = V.di_processing(V.mono(rec["path"], t, V.CROP_S))
            done_w[key] = {"di": d, "start_s": t, "d2_flags": f, "d2_source": src,
                           "D2": V.d2_status(f, d in PS.HUM_SUSPECT),
                           "D4": "silent" if d4["crest_db"] is None else V.d4_status(d4["crest_db"], d4["bright_slope"]),
                           "d4": d4}
        _save(path, {"plan": PLAN, "shard": [k, n], "windows": done_w, "classes": done_c,
                     "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"windows {m + 1}/{len(jobs)} {d[-50:]}: {len(by_di[d])} ({time.time() - t0:.0f} s)", flush=True)
    for m, sid in enumerate(cjobs):
        if sid in done_c:
            continue
        s = secs[sid]
        heard = ver[s["di"]]["classes"]
        e = ear_class(float(s["start_s"]), [(float(t), v, nt) for t, v, nt in heard])
        a = inv[s["di"]].get("gain_class")
        c = None if (e or a) else T3._amp_track_class(ctx, s)
        cls, src = T3.gain_class(a, e, c)
        done_c[sid] = {"class": cls, "from": src, "ear": e, "part_a": a, "classifier": c}
        if m % 25 == 0:
            _save(path, {"plan": PLAN, "shard": [k, n], "windows": done_w, "classes": done_c,
                         "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            print(f"classes {m + 1}/{len(cjobs)} ({time.time() - t0:.0f} s)", flush=True)
    _save(path, {"plan": PLAN, "shard": [k, n], "complete": True, "windows": done_w, "classes": done_c,
                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"CHECKS DONE {k}/{n}: {len(done_w)} windows, {len(done_c)} sections classed")


def load_checks(root):
    w, c, shards = {}, {}, []
    for p in sorted(root.glob("checks-*of*.json")):
        d = _load(p)
        if not d.get("complete"):
            raise SystemExit(f"{p.name} is incomplete: finish `checks`")
        w.update(d["windows"])
        c.update(d["classes"])
        shards.append(tuple(d["shard"]))
    ns = {n for _, n in shards}
    if len(ns) != 1 or sorted(k for k, _ in shards) != list(range(next(iter(ns)))):
        raise SystemExit(f"`checks` shards incomplete: {shards}")
    return w, c


def lists_for(tr, ver, inv, secs, windows):
    """T0's lists widened to this pool (`trusted_data`'s plan reads these): (verified, windows, bad): T0's verdicts
    and window statuses where T0 measured; the released and tier-1 training DIs verified, and every window `checks`
    measured (T0's DIs' windows T0 never read included) by T0's rule (a heard-clean window covering it clears a D4
    flag)."""
    verified = {d for d in T.verified_dis(tr)}
    wins = T.windows_of(tr)
    t0w = {d: set(v) for d, v in wins.items()}
    bad = set(T.unusable(tr))
    for d, v in ver.items():
        if v["trains"] and d not in tr["dis"]:
            verified.add(d)
        elif d in verified and not v["trains"]:
            verified.discard(d)
    t0_heard = set(T.verified_dis(tr))                     # T0 verifies a DI only once it is heard
    for key, w in windows.items():
        d = w["di"]
        if key in t0w.get(d, ()):                            # T0's own reading stands
            continue
        heard = [(t, t + V.CROP_S, vv) for _, t, vv in (ver.get(d) or {}).get("heard", [])]
        cov = any(V.covers(a, b, w["start_s"]) and vv == "clean" for a, b, vv in heard)
        di_clean = (ver.get(d) or {}).get("ear") == "clean" or d in t0_heard
        st = section_status(w["D2"], w["D4"], cov, di_clean) if d in verified else "excluded"
        wins.setdefault(d, {})[key] = st
        if st != "usable":
            bad.add(key)
    return verified, wins, bad


def cmd_stem_scan(args):
    """T0's session-level stem scan (`verify_tracks.scan_session_stems`, T0's floor) on the pool's sessions that
    neither T0 nor cc_pool scanned (tier 1's Quicksand), into T0's root under this prefix."""
    require(args)
    ver = _ver(args)
    inv = cc_inventory()
    have, floor = merged_takes()
    sds = sorted({session_of(inv, d) for d, v in ver.items() if v["trains"]} - set(have))
    path = V.OUT / "t0" / TIER1_STEMS
    prev = _load(path) or {}
    if prev and prev.get("floor_db") != floor:
        raise SystemExit(f"{path} was scanned at another floor: move it aside by hand")
    done = prev.get("sessions", {})
    for sd in sds:
        if sd in done:
            continue
        ids = [d for d, r in inv.items() if r["session_dir"] == sd]
        done[sd] = V.scan_session_stems(sd, ids, floor)
        _save(path, {"plan": PLAN, "floor_db": floor, "sessions": done, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{pathlib.Path(sd).name}: {len(done[sd]['stems'])} stems", flush=True)
    print(f"STEM SCAN DONE: {len(sds)} sessions")


def merged_takes():
    """({session dir: {"sources", "stems": {stem: takes_db}}}, floor): T0's scan, cc_pool's and tier 1's, one floor."""
    a, floor = T.stem_takes(V.OUT)
    b, fb = CP.cc_stem_takes(V.OUT)
    if fb != floor:
        raise SystemExit("the scans read at different floors")
    out = {**a, **b}
    t1 = _load(V.OUT / "t0" / TIER1_STEMS) or {}
    if t1 and t1.get("floor_db") == floor:
        out.update({sd: {"sources": list(r["sources"]), "stems": {f: v["takes_db"] for f, v in r["stems"].items()}}
                    for sd, r in t1["sessions"].items()})
    return out, floor


def scan_rows_raw():
    """{session dir: scan row} with each stem's session-wide pass (cc_pool's shards and tier 1's file, T0's floor)."""
    floor = V.stem_floor(V.OUT)
    rows, probs = V.load_shards(V.OUT, CP.STEM_PREFIX, "sessions", lambda d: d.get("floor_db") == floor)
    if probs:
        raise SystemExit(f"cc_pool's stem scan cannot be read: {probs}")
    t1 = _load(V.OUT / "t0" / TIER1_STEMS) or {}
    if t1 and t1.get("floor_db") == floor:
        rows = {**rows, **t1["sessions"]}
    return rows


def spot_sessions(tr, ver, inv):
    """The pool's sessions whose stems T0 has not heard (no clean spot-check in T0's lists)."""
    return sorted({session_of(inv, d) for d, v in ver.items() if v["trains"]} - set(tr["stems"]))


def spot_answers():
    """{session dir: verdict} from the part-13 export (None when not yet answered); the page's build must match."""
    if not SPOT_ANSWERS.exists():
        return None
    a = json.loads(SPOT_ANSWERS.read_text())
    it = json.loads((SPOT_DIR / "items.json").read_text())
    if a.get("build") != it.get("build") or a.get("part") != SPOT_PART:
        raise SystemExit(f"part {SPOT_PART}: the answers' build {a.get('build')} is not the page's {it.get('build')}")
    ans = {x["id"]: x["verdict"] for x in a["answers"]}
    return {i["session_dir"]: ans.get(i["id"]) for i in it["items"] if i["family"] == "stem"}


def verified_stems(tr, ver, inv):
    """T0's verified stems, widened by the part-13 spot-check: a session heard clean gives its stems that pass the
    session-wide scan (T0's rule; the per-example rule then reads them); a guitar heard, 'not sure' or unheard
    gives none."""
    out = dict(tr["stems"])
    heard = spot_answers() or {}
    rows = scan_rows_raw()
    for sd in spot_sessions(tr, ver, inv):
        if heard.get(sd) == "clean" and sd in rows:
            out[sd] = sorted(f for f, v in rows[sd]["stems"].items() if v["pass"] and not V.NON_MUSICAL.search(f))
    return out


def flagged_sections(args):
    """The candidate sections T0's rule holds for the ear (a D4 flag no heard-clean window covers), not high gain,
    each with the DI's own amp track for the card. -> [{"section", "di", "start_s", "amp", "band"}]."""
    ctx, verified, wins, bad, cands = candidates(args)
    out = []
    for sid, r in sorted(cands.items()):
        if r["why"] != "section pending ear" or r["class"] == "high-gain" or (r["band"] in HEAVY_BANDS and not r["class"]):
            continue
        rec = ctx.inv[r["di"]]
        files = sorted(f.name for f in pathlib.Path(rec["session_dir"]).glob("*.wav"))
        own = V.own_amp_tracks(rec, files)
        sec = ctx.sections[sid]
        out.append({"section": sid, "di": r["di"], "path": rec["path"], "start_s": float(sec["start_s"]),
                    "amp": str(pathlib.Path(rec["session_dir"]) / own[0]) if own else None, "band": r["band"]})
    return out


def cmd_ear_page(args):
    """Ear page part 13 (zero renders): the stem spot-checks of the pool's sessions T0 has not heard (T0's rule: a
    session's stems count once its spot-check is heard clean; per session the passing stem nearest the floor at its
    busiest candidate section, `pick_stem_checks`), then the candidate sections a D4 flag holds for the ear, each
    as the DI then its own amp track (the user asked to hear DIs that way, 2026-10-29)."""
    import hashlib

    from learn import build_ear_page as BEP

    require(args)
    if (SPOT_DIR / "index.html").exists():
        raise SystemExit(f"{SPOT_DIR / 'index.html'} exists: a rebuild hides stored answers")
    ver = _ver(args)
    inv = cc_inventory()
    tr = T.load_lists(V.OUT)
    rows = scan_rows_raw()
    sds = spot_sessions(tr, ver, inv)
    missing = [sd for sd in sds if sd not in rows]
    if missing:
        raise SystemExit(f"no stem scan for {missing}: run `stem-scan`")
    secs = manifest_sections(ver)
    di_rows = {d: {"path": inv[d]["path"], "sections": [{"start_s": float(s["start_s"]), "own": True}
                                                        for s in secs.values() if s["di"] == d and s.get("clean")]}
               for d, v in ver.items() if v["trains"]}
    picks = V.pick_stem_checks({sd: rows[sd] for sd in sds}, di_rows, {})
    items = []
    for sd in sds:
        c = picks[sd]
        if "stem" not in c:
            print(f"  {pathlib.Path(sd).name}: {c['none']}")
            continue
        path = str(pathlib.Path(sd) / c["stem"])
        items.append({"id": V.item_id("stem-cc-2026-10-29", path, c["start_s"]), "kind": "stem", "family": "stem",
                      "key": path, "paths": {"stem": path}, "start_s": c["start_s"], "dur_s": V.CROP_S,
                      "session_dir": sd, "band": next(v["band"] for d, v in ver.items()
                                                      if v["trains"] and session_of(inv, d) == sd),
                      "risk_db": c["risk_db"], "share": c["share"]})
    for f in flagged_sections(args):
        if not f["amp"]:
            print(f"  {f['section']}: no own amp track (left for a later sitting)")
            continue
        items.append({"id": V.item_id("di-flagged-cc-2026-10-29", f["path"], f["start_s"]), "kind": "di",
                      "family": "di", "key": f["path"], "paths": {"di": f["path"], "amp": f["amp"]},
                      "start_s": f["start_s"], "dur_s": V.CROP_S, "band": f["band"], "section": f["section"]})

    def title_of(it):
        if it["family"] == "stem":
            return (f"{it['band']} · {pathlib.Path(it['session_dir']).name.removesuffix('_Full')} · "
                    f"{pathlib.Path(it['paths']['stem']).stem}")
        return f"{it['band']} · {pathlib.Path(it['paths']['di']).parent.name.removesuffix('_Full')} · " \
               f"{pathlib.Path(it['paths']['di']).name}"

    def subtitle_of(it):
        a = it["start_s"]
        w = f"{BEP.mmss(a)}–{BEP.mmss(a + it['dur_s'])}"
        if it["family"] == "stem":
            return f"{w} · {pathlib.Path(it['paths']['stem']).name} alone"
        return f"{w} · the DI, then its amp track {pathlib.Path(it['paths']['amp']).name}"

    def item_clips(it):
        a, d = it["start_s"], it["dur_s"]
        if it["family"] == "stem":
            return [(it["id"] + "-stem", it["paths"]["stem"], a, d, "the track")]
        return [(it["id"] + "-di", it["paths"]["di"], a, d, "the DI"),
                (it["id"] + "-amp", it["paths"]["amp"], a, d, "its amp track")]

    BEP.title_of, BEP.subtitle_of, BEP.item_clips = title_of, subtitle_of, item_clips    # this process only
    BEP.VT.EAR_PAGE = SPOT_PAGE
    BEP.ASK["di"] = "Judge the first sound, the DI: is it a clean, unprocessed DI?"
    BEP.ASK["stem"] = "Is an electric guitar audible in this track, even faintly?"
    build = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    SPOT_DIR.mkdir(parents=True, exist_ok=True)
    clips = {}
    for it in items:
        for key, path, a, d, _ in item_clips(it):
            clips[key] = BEP.clip_b64(path, a, d, SPOT_DIR / "clips")
    html_ = BEP.page_html(SPOT_PART, items, clips, build, SPOT_PART, title="New songs: tracks and DIs")
    generic = "Items the earlier pages do not hold."
    assert generic in html_
    n_stem = sum(i["family"] == "stem" for i in items)
    html_ = html_.replace(generic, (
        f"Two kinds of card. <b>Track cards</b> (the first {n_stem}): one drum, bass, keys or vocal track per new "
        "training song, alone; can you hear an electric guitar in it, even faintly? A song's backing tracks are used "
        "only once its card has no guitar. <b>DI cards</b> (the rest): a DI the measures flag here, then its amp "
        "track from the same moment; judge the DI: is it a clean, unprocessed DI? All clips at &minus;23 LUFS."))
    html_ = html_.replace(f"<title>Trusted data ear {SPOT_PART}</title>", "<title>New songs ear</title>")
    (SPOT_DIR / "index.html").write_text(html_)
    _save(SPOT_DIR / "items.json", {"page": SPOT_PAGE, "part": SPOT_PART, "build": build, "items": items})
    print(f"EAR PAGE: {n_stem} track cards, {len(items) - n_stem} DI cards, "
          f"{(SPOT_DIR / 'index.html').stat().st_size / 1e6:.1f} MB -> {SPOT_DIR / 'index.html'}")


class ScanMeta:
    """`data_cleaning.Meta`'s face for `scan_di` on this pool: its sections and DI rows; part C's leak drops where
    part C read the DI, none elsewhere (the per-example stem rule reads leakage for these sessions)."""

    def __init__(self, ctx):
        from learn import pretrain_set as PS

        self.sections, self.inv = ctx.sections, ctx.inv
        leak = PS._load(PS.OUT / "leakage.json") or {}
        self.leak = {d: leak.get(d) or {"dropped": []} for d in ctx.inv}


def scan_rows_all(root):
    """The cleaning scan's rows by section: part C's (`data_cleaning.scan_rows`) and this pool's own (cc/scan/)."""
    from learn import data_cleaning as DC

    out = dict(DC.scan_rows(DC.OUT))
    for f in sorted((root / "scan").glob("rows-*.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out.setdefault(r["section"], r)
    return out


def cmd_cleaning_scan(args):
    """The cleaning scan (`data_cleaning.scan_di`, zero renders, CPU) on the candidate sections that have no scan
    row, per DI, a shard of the DIs; rows in cc/scan/ (part C's scan folder is not written)."""
    from learn import direct_stems as DS

    require(args)
    ctx, verified, wins, bad, cands = candidates(args)
    root = root_of(args)
    have = scan_rows_all(root)
    todo = {}
    for sid, r in sorted(cands.items()):
        if r["why"] is None and sid not in have:
            todo.setdefault(r["di"], []).append(sid)
    k, n = args.shard
    dis = [d for j, d in enumerate(sorted(todo)) if j % n == k]
    print(f"cleaning scan {k}/{n}: {len(dis)} DIs, {sum(len(todo[d]) for d in dis)} sections "
          f"(of {sum(len(v) for v in todo.values())} without a row)", flush=True)
    meta = ScanMeta(ctx)
    rp = root / "scan" / f"rows-{k}of{n}.jsonl"
    rp.parent.mkdir(parents=True, exist_ok=True)
    swap0 = DS.swap_mb()
    t0 = time.time()
    with open(rp, "a") as fh:
        for m, d in enumerate(dis):
            g = DS._guards("cc-scan", T.DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            from learn import data_cleaning as DC

            rows = DC.scan_di(meta, d, todo[d], log=lambda x: print(x, flush=True))
            for row in rows:
                fh.write(json.dumps(row) + "\n")
            fh.flush()
            print(f"  {m + 1}/{len(dis)} DIs ({time.time() - t0:.0f} s)", flush=True)
    print(f"CLEANING SCAN DONE {k}/{n}")


def cmd_amp_bleed(args):
    """Rule 1's bleed check on the amp tracks the pool's candidate sections need (`trusted_data.measure_amp_bleed`),
    stored where T2's readings are (one file per session)."""
    require(args)
    root = V.out_root(args)
    ctx, verified, wins, bad, cands = candidates(args)
    blocked = T.blocked_by_section(ctx, [{"section": s} for s in cands], verified, wins, bad, {})
    need = T.needed_amp_tracks(ctx, blocked)
    k, n = args.shard
    print(f"amp-bleed: {sum(len(v) for v in need.values())} amp tracks in {len(need)} sessions; shard {k}/{n}",
          flush=True)
    for m, (sd, tracks) in enumerate(need.items()):
        if m % n != k:
            continue
        path = T.amp_bleed_path(root, sd)
        prev = _load(path) or {}
        if prev and (prev.get("measure") != T.AMP_BLEED_MEASURE or prev.get("session_dir") != sd):
            raise SystemExit(f"{path} was read under another measure: move it aside by hand")
        have = dict(prev.get("tracks") or {})
        todo = [t for t in tracks if t not in have]
        if todo:
            have.update(T.measure_amp_bleed(sd, todo))
            _save(path, {"plan": PLAN, "measure": T.AMP_BLEED_MEASURE, "session_dir": sd,
                         "threshold_db": T.AMP_BLEED_DB, "tracks": have, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        for t in tracks:
            print(f"  {pathlib.Path(sd).name[:40]} {t}: {T.amp_status(have[t])}", flush=True)
    print(f"AMP-BLEED DONE {k}/{n}")


def candidates(args):
    """(ctx, verified, windows, bad, {section: row}): the candidate target sections (part A's clean, usable, a
    training DI, not high gain; a heavy band's only when classed), before rule 1 and the cap."""
    ver = _ver(args)
    inv = cc_inventory()
    secs = manifest_sections(ver)
    tr = T.load_lists(V.OUT)
    windows, classes = load_checks(root_of(args))
    verified, wins, bad = lists_for(tr, ver, inv, secs, windows)
    out = {}
    for sid, s in sorted(secs.items()):
        c = classes.get(sid) or {}
        band = ver[s["di"]]["band"]
        why = None
        if not s.get("clean"):
            why = "part A's screen flags the section"
        elif s["di"] not in verified:
            why = "the DI is not verified"
        elif (wins.get(s["di"]) or {}).get(sid) != "usable" or sid in bad:
            why = f"section {(wins.get(s['di']) or {}).get(sid) or 'not measured'}"
        elif c.get("class") == "high-gain":
            why = "high gain"
        elif band in HEAVY_BANDS and not c.get("class"):
            why = "a heavy band's unclassed section"
        out[sid] = {"section": sid, "band": band, "di": s["di"], "class": c.get("class"), "class_from": c.get("from"),
                    "why": why}
    return Ctx(inv, secs), verified, wins, bad, out


def cmd_plan(args):
    """The yield and the composition (zero renders); with --dry nothing is written."""
    import collections

    gate = BLEED_GATE and not args.no_bleed_gate
    if not gate and not args.dry:
        raise SystemExit("--no-bleed-gate is for dry runs until the user rules on it")
    if args.sum_lower and not args.dry:
        raise SystemExit("--sum-lower is for dry runs until it is reviewed and adopted")
    T.AMP_SUM_LOWER = T.AMP_SUM_LOWER or bool(args.sum_lower)
    require(args, renders=not args.dry)
    ctx, verified, wins, bad, cands = candidates(args)
    root = V.out_root(args)
    act = {}
    elig = [r for r in cands.values() if not r["why"]]
    rows = [{"i": n, "section": r["section"], "band": r["band"]} for n, r in enumerate(elig)]
    scan = scan_rows_all(root_of(args))
    kept, left, amp_of = T.apply_rule1(ctx, root, rows, verified, wins, bad, act, scan, doubles_out=True,
                                       bleed_gate=gate)
    kept, left_cap = T.apply_cap(ctx, kept, verified, wins, bad, act)
    left = sorted(left + left_cap, key=lambda x: x["section"])
    why = collections.Counter(r["why"] for r in cands.values() if r["why"])
    print("YIELD (sections; zero renders)")
    print(f"  candidate sections of training DIs: {len(cands)}; out before rule 1: "
          + ", ".join(f"{w} {n}" for w, n in why.most_common()))
    lw = collections.Counter(x["reason"] if x["reason"] != T.LEFT_OUT_OWN_TAKE or not any(
        g.get("why") == NO_SCAN or g.get("part") == NO_SCAN for g in x["guitars"]) else NO_SCAN for x in left)
    print(f"  eligible {len(elig)}; rule 1 and the cap leave out {len(left)}: "
          + ", ".join(f"{w} {n}" for w, n in lw.most_common()))
    by = collections.defaultdict(lambda: collections.Counter())
    for r in kept:
        c = cands[r["section"]]
        by[r["band"]][c["class"] or "unclassed"] += 1
    for b in sorted(by):
        print(f"  {b:24s} {sum(by[b].values()):4d} sections: {dict(by[b])}")
    print(f"  kept {len(kept)} sections in {len(by)} bands")
    by_band = {}
    for r in kept:
        by_band.setdefault(r["band"], []).append(r["section"])
    fs = fs_sections(by_band)
    train_by = {b: [s for s in v if s not in set(fs)] for b, v in by_band.items()}
    train_by, dropped = heavy_trim(train_by)
    train_secs = sorted(s for v in train_by.values() for s in v)
    n_fs = int(round(N_TRAIN * len(fs) / len(train_secs))) if train_secs else 0
    ex = allocate(train_secs, N_TRAIN, CC_BASE) + allocate(fs, n_fs, FS_BASE, CC_SEED + 1)
    check_ids([i for i, _ in ex])
    per = collections.Counter(cands[s]["band"] for _, s in ex[:N_TRAIN])
    heavy = sum(n for b, n in per.items() if b in HEAVY_BANDS)
    print(f"  FS_CC {len(fs)} sections ({n_fs} examples); training {len(train_secs)} sections ({N_TRAIN} examples, "
          f"{N_TRAIN / max(1, len(train_secs)):.1f} per section); heavy {heavy}/{N_TRAIN} ({heavy / N_TRAIN:.0%}), "
          f"{len(dropped)} heavy sections dropped for the cap")
    print("  training examples by band: " + ", ".join(f"{b} {n}" for b, n in sorted(per.items())))
    if args.dry:
        print("PLAN DRY: nothing written")
        return
    write_plan(args, ctx, verified, wins, bad, cands, ex, set(fs), amp_of, left, dropped)


def example_row(i, sid, band, es):
    """Example i's part C draw (amp, mode, base) and its row as `trusted_data` reads one."""
    from learn import pretrain_set as PS

    _, amp, mode, base = PS.plan_example(i)
    return {"i": i, "section": sid, "band": band, "amp": amp, "mode": mode, "base": base, "early_stop": es,
            "split": "train", "set": "fs" if es else "train"}


def write_plan(args, ctx, verified, wins, bad, cands, ex, fs, amp_of, left, dropped):
    root = root_of(args)
    takes = merged_takes()
    tr = T.load_lists(V.OUT)
    vstems = verified_stems(tr, _ver(args), ctx.inv)
    unheard = [sd for sd in spot_sessions(tr, _ver(args), ctx.inv) if sd not in vstems]
    if unheard and not args.smoke:
        raise SystemExit(f"{len(unheard)} sessions' stem spot-checks are not heard clean (e.g. {unheard[:2]}): the "
                         f"plan waits for part {SPOT_PART}'s answers")
    from learn import local_objective as LO
    from learn import trusted_data_t3 as T3

    gc = gate_cap()
    menus = T3.Menus()
    menus.gate_u = gc["unit"]
    act = {}
    recipes = []
    rows = [example_row(i, s, cands[s]["band"], s in fs) for i, s in ex]
    ctx.pool, ctx.rows = rows, {r["i"]: r for r in rows}
    for r in rows:
        sd = ctx.inv[ctx.sections[r["section"]]["di"]]["session_dir"]
        x = T.example_recipe(ctx, r, verified, vstems, act, bad, wins, amp_of.get(r["section"], ()),
                             takes=takes, vocals_from_stems=True)
        amp, mode, base, sel, xf, core, cname, tries = T3.full_twin(r["i"], menus)
        if (amp, mode, base) != (r["amp"], r["mode"], r["base"]):
            raise SystemExit(f"{r['i']}: the full twin's draw is not part C's")
        x.update(set=r["set"], mode=mode, centre=cname, tries=tries, settings=LO.sdict(xf), core=LO.sdict(core),
                 cls=cands[r["section"]]["class"], session_dir=sd)
        recipes.append(x)
    old = _load(root / "plan.json")
    stale = T.stale_rows(old, {"examples": recipes}, T.rows_of(V.out_root(args), STAGE, "render"))
    if stale:
        raise SystemExit(f"{len(stale)} examples were rendered under another recipe: move {root} aside first")
    _save(root / "plan.json", {"plan": PLAN, "ledger": f"{LEDGER_ID} {LEDGER_KEY}", "stage": STAGE,
                               "train": [i for i, s in ex if s not in fs], "fs": [i for i, s in ex if s in fs],
                               "fs_sections": sorted(fs), "heavy_dropped": dropped, "left_out": left,
                               "examples": recipes, "lists_sha256": T.lists_sha(V.out_root(args)),
                               "verified_stems_sessions": sorted(vstems), "gate_cap": gc,
                               "renders_targets": len(recipes), "renders_others": sum(len(x["others"]) for x in recipes),
                               "separations": len(recipes), "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"PLAN: {len(recipes)} examples; renders {len(recipes)} targets + "
          f"{sum(len(x['others']) for x in recipes)} other guitars (+ priming); separations {len(recipes)}")


def gate_cap():
    """The full twins' gate cap from the factory menu (no renderer), which must be T3's (D_F5's draw rule)."""
    from learn import full_space as F
    from learn import trusted_data_t3 as T3

    u, db = F.gate_cap_u(T3.Menus().gate_thresholds())
    t3 = (_load(T.plan_path(V.OUT, T3.STAGE)) or {}).get("gate_cap") or {}
    if abs(u - t3.get("unit", -1.0)) > 1e-12:
        raise SystemExit(f"the factory gate cap {u} is not T3's {t3.get('unit')}: D_CC would draw by another rule")
    return {"unit": u, "db": db}


def load_plan(args):
    p = _load(root_of(args) / "plan.json")
    if not p or (p.get("smoke") and not args.smoke):
        raise SystemExit("run `plan` first")
    return p


def tgt_path(root, i):
    return T.ex_path(root, STAGE, i, f"tgt-{STAGE}")


def ctx_for(args):
    ver = _ver(args)
    return Ctx(cc_inventory(), manifest_sections(ver))


def new_renderer():
    """A new plugin server once a render slot is free (at most 3 machine-wide), its recipe checked."""
    from learn import direct_stems as DS
    from learn import knob_ceiling as K

    DS.wait_render_slot()
    rr = K.Renderer()
    try:
        DS.check_recipe(rr)
    except BaseException:
        rr.close()
        raise
    return rr


def render_target(x, menus, di, trim, make=None):
    """One example's full twin in its own new plugin process (one discarded priming render of the same setting:
    every kept target sits at the same process position). -> (row, trimmed mono render)."""
    from learn import audibility_measure as AM
    from learn import local_objective as LO
    from learn import trusted_data_t3 as T3

    amp, mode, base, sel, xf, core, cname, tries = T3.full_twin(x["i"], menus)
    if amp != x["amp"] or base != x["base"] or LO.sdict(xf) != x["settings"]:
        raise SystemExit(f"{x['i']}: the full twin differs from the plan's draw")
    y = AM.fresh_render(make or new_renderer, di, sel, xf, xf)
    y = (y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]]
    return {"i": x["i"], "section": x["section"], "amp": amp, "mode": mode, "centre": cname, "tries": tries,
            "settings": LO.sdict(xf)}, y


def cmd_render(args):
    """Renders for one shard of whole sections: per section the targets (each in its own process), then one plugin
    process for the other guitars (T2's rule: one priming render per (DI, amp), each scaled to its level, pan-folded,
    summed per example). At most one plugin process per shard at a time."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data_t3 as T3

    require(args, renders=True)
    root = V.out_root(args)
    plan = load_plan(args)
    T.check_lists(root, plan, args.smoke)
    k, n = args.shard
    shard = DS.shard_sections(plan["examples"], n)
    done = T.rows_of(root, STAGE, "render")
    todo = [x for x in plan["examples"] if shard[x["section"]] == k and x["i"] not in done]
    if not todo:
        print(f"RENDER DONE {k}/{n} (nothing to do)")
        return
    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"free disk below {T.DISK_GUARD_GB:.0f} GB")
    ctx = ctx_for(args)
    menus = T3.Menus()
    menus.gate_u = plan["gate_cap"]["unit"]
    LO._wait_cap()
    rr = new_renderer()
    try:
        T3.check_menu(rr.menu(), menus.dried)
        if abs(F_gate(menus) - plan["gate_cap"]["unit"]) > 1e-12:
            raise SystemExit("the factory gate thresholds changed since the plan")
        menu = rr.menu()
    finally:
        rr.close()
    by_sec = {}
    for x in todo:
        by_sec.setdefault(x["section"], []).append(x)
    rp = T.stage_root(root, STAGE) / "rows" / f"render-{k}of{n}.jsonl"
    rp.parent.mkdir(parents=True, exist_ok=True)
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    swap0 = DS.swap_mb()
    t_start, written, n_renders = time.time(), [], 0
    with open(rp, "a") as fh:
        for m, (sid, xs) in enumerate(sorted(by_sec.items())):
            g = DS._guards("cc-render", T.DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            sec = ctx.sections[sid]
            di = B.measure(PS.section_audio(sec["path"], sec["start_s"])).astype(np.float32)
            rows, acc, cores = {}, {}, {}
            for x in sorted(xs, key=lambda x: (x["amp"], x["i"])):
                row, y = render_target(x, menus, di, trim)
                n_renders += 2
                ly = T.lufs_or_none(y)
                why = T.near_silent(ly)
                row["others"] = []
                if why:
                    row.update(refused=f"target: {why}", lufs=ly)
                else:
                    sc, sha = G.write_flac(T.flac_path(root, STAGE, x["i"], "target"), y, PS.SR)
                    mels, halves = T3.target_features(y)
                    DS._save_npz(tgt_path(root, x["i"]), lufs=[halves["lufs_A"], halves["lufs_B"]], **mels)
                    row["target"] = {"scale": sc, "sha256": sha, "lufs": ly, **halves,
                                     "tgt_sha256": DS.hashlib_file(tgt_path(root, x["i"]))}
                rows[x["i"]], acc[x["i"]] = row, np.zeros(trim[1] - trim[0])
                cores[x["i"]] = T3.full_twin(x["i"], menus)
            stems = sorted({s for x in xs for s in x["stems"]["v"]})
            levels = T.section_levels(ctx, sec, [o for x in xs for o in x["others"]], stems)
            jobs = []
            for x in xs:
                if rows[x["i"]].get("refused"):
                    continue
                for o in x["others"]:
                    if o["dt"]:                                  # a DT double: the target's core setting (D_F5's)
                        amp, _, _, sel, _, core, _, _ = cores[x["i"]]
                        jobs.append((o["di"], amp, x["i"], o, sel, core))
                    else:
                        amp, sel, st = T.other_settings(x["i"], o["di"], menu)
                        jobs.append((o["di"], amp, x["i"], o, sel, st))
            jobs.sort(key=lambda j: (j[0], j[1], j[2]))
            if jobs:
                rr = new_renderer()
                try:
                    primer = DS.Primer(rr)
                    di_cache = {}
                    for di_id, amp, i, o, sel, st in jobs:
                        if rows[i].get("refused"):
                            continue
                        lv, src = levels[di_id]
                        if lv is None:
                            rows[i]["others"].append({"di": di_id, "left_out": "no level"})
                            continue
                        if di_id not in di_cache:
                            di_cache = {di_id: B.measure(PS.section_audio(ctx.inv[di_id]["path"], sec["start_s"]))
                                        .astype(np.float32)}
                        y = primer.render((f"{sid}|{di_id}", amp), di_cache[di_id], sel, st)
                        y = (y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]]
                        acc[i] = T.place_other(rows[i], acc[i], y, T.lufs_or_none(y), lv, src, o, amp, LO.sdict(st))
                    n_renders += primer.renders
                finally:
                    rr.close()
            for x in xs:
                rw = rows[x["i"]]
                if not rw.get("refused"):
                    sc, sha = G.write_flac(T.flac_path(root, STAGE, x["i"], "others"), acc[x["i"]], PS.SR)
                    rw["others_file"] = {"scale": sc, "sha256": sha}
                rw["renders_so_far"] = n_renders
                written.append(rw)
                fh.write(json.dumps(rw) + "\n")
            fh.flush()
            print(f"section {m + 1}/{len(by_sec)} {sid[-50:]}: {len(xs)} examples; renders {n_renders}; "
                  f"{(time.time() - t_start) / (m + 1):.0f} s per section", flush=True)
    print(f"refused in this shard, by reason: {T.refusal_counts(written) or 'none'}")
    print(f"RENDER DONE {k}/{n}: {n_renders} renders (priming included)")


def F_gate(menus):
    from learn import full_space as F

    return F.gate_cap_u(menus.gate_thresholds())[0]


def cmd_build(args):
    """Mixes and X-LANCE stems (msst-venv), T2's recipe (`trusted_data.self_built_mix`): features `mix-cc` and
    `xlance_g-cc`."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS

    require(args, renders=True)
    root = V.out_root(args)
    plan = load_plan(args)
    T.check_lists(root, plan, args.smoke)
    rend = T.rows_of(root, STAGE, "render")
    built = T.rows_of(root, STAGE, "build")
    todo = [x for x in plan["examples"] if x["i"] in rend and x["i"] not in built]
    todo.sort(key=lambda x: (x["section"], x["i"]), reverse=args.order == "desc")
    todo = todo[:args.limit or None]
    print(f"build {STAGE}: {len(todo)} to build ({len(rend)} rendered, {len(built)} built) on {args.device}", flush=True)
    if not todo:
        return
    ctx = ctx_for(args)
    sep = DS.stem_separator(T.SEP, args.device)
    stems = T.Stems(ctx)
    swap0 = DS.swap_mb()
    rp = T.stage_root(root, STAGE) / "rows" / f"build-{args.device}-{os.getpid()}.jsonl"
    rp.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(rp, "a") as fh:
        for m, x in enumerate(todo):
            g = DS._guards("cc-build", T.DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            if T.ex_path(root, STAGE, x["i"], f"{T.SEP}-{STAGE}").exists():
                continue                                    # the other worker's
            rw = rend[x["i"]]
            base = {"i": x["i"], "section": x["section"], "band": x["band"]}
            if rw.get("refused"):
                fh.write(json.dumps({**base, "refused": rw["refused"]}) + "\n")
                continue
            y = G.read_flac(T.flac_path(root, STAGE, x["i"], "target"), rw["target"]["scale"], rw["target"]["sha256"])
            oth = G.read_flac(T.flac_path(root, STAGE, x["i"], "others"), rw["others_file"]["scale"],
                              rw["others_file"]["sha256"])
            voc = x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"]
            st = stems.get(x["section"], T.backing_tracks(x, voc))
            mix, gains, lb = T.self_built_mix(np.asarray(y, np.float64), np.asarray(oth, np.float64), st, x)
            if not T.empty_backing_ok(y, lb):
                fh.write(json.dumps({**base, "refused": "no backing: the drawn ratio cannot be met"}) + "\n")
                fh.flush()
                continue
            s_ = np.asarray(sep(mix), np.float64)
            if len(s_) != len(mix) or not np.isfinite(s_).all():
                raise SystemExit(f"{x['i']}: bad stem")
            mm, ml, _ = DS.half_features(mix)
            sm, sl, floor = DS.half_features(s_)
            DS._save_npz(T.ex_path(root, STAGE, x["i"], f"mix-{STAGE}"), mA=mm["A"], mB=mm["B"],
                         lufs=[ml["A"], ml["B"]], gain_db=gains["ga"], mastered=x["draw"]["mastered"])
            DS._save_npz(T.ex_path(root, STAGE, x["i"], f"{T.SEP}-{STAGE}"), sA=sm["A"], sB=sm["B"],
                         lufs=[sl["A"], sl["B"]])
            fh.write(json.dumps({**base, "vocals": bool(voc), "gains_db": gains, "lufs_backing": lb,
                                 "lufs_mA": ml["A"], "lufs_mB": ml["B"], "lufs_sA": sl["A"], "lufs_sB": sl["B"],
                                 "floor_share": floor, "snr_audio_db": DS.snr_db(s_, y * 10 ** (gains["ga"] / 20)),
                                 "device": args.device}) + "\n")
            fh.flush()
            if m % 25 == 0:
                print(f"build {m + 1}/{len(todo)}: {(time.time() - t0) / (m + 1):.1f} s per example", flush=True)
    print(f"BUILD DONE {STAGE} ({args.device})")


def sets(root, plan):
    """(training ids, FS_CC ids, refused, unbuilt): a render or build refusal drops the example."""
    rend, built = T.rows_of(root, STAGE, "render"), T.rows_of(root, STAGE, "build")
    bad = {i for i, r in rend.items() if r.get("refused")} | {i for i, r in built.items() if r.get("refused")}
    need = set(plan["train"]) | set(plan["fs"])
    unbuilt = {i for i in need if i not in built and i not in bad}
    keep = lambda ids: [i for i in ids if i not in bad and i not in unbuilt]  # noqa: E731
    return keep(plan["train"]), keep(plan["fs"]), bad & need, unbuilt


def cmd_check(args):
    import collections

    require(args)
    root = V.out_root(args)
    plan = load_plan(args)
    tr_ids, fs_ids, bad, unbuilt = sets(root, plan)
    rend, built = T.rows_of(root, STAGE, "render"), T.rows_of(root, STAGE, "build")
    why = collections.Counter((rend.get(i) or {}).get("refused") or (built.get(i) or {}).get("refused") for i in bad)
    print(f"{STAGE}: {len(plan['examples'])} planned; rendered {len(rend)}, built {len(built)}; refused {len(bad)} "
          f"({dict(why)}); unbuilt {len(unbuilt)}; training {len(tr_ids)}, FS_CC {len(fs_ids)}")
    print("CHECK DONE" if not unbuilt else "CHECK: not finished")


def arm_rows(args, plan):
    """(training rows, FS_CC rows, files): the plan's rows with their full twins' labels and target half loudness
    (the merge augmentation's gains), as T3's D_F5 rows."""
    from learn import full_space as F

    root = V.out_root(args)
    tr_ids, fs_ids, _, unbuilt = sets(root, plan)
    if unbuilt and not args.smoke:
        raise SystemExit(f"{len(unbuilt)} examples are not built: every run waits for the build")
    ex = {x["i"]: x for x in plan["examples"]}
    rend = T.rows_of(root, STAGE, "render")

    def row(i, es):
        x = ex[i]
        st = {tuple(k.rsplit("/", 1)): v for k, v in rend[i]["settings"].items()}
        return {"i": i, "section": x["section"], "band": x["band"], "amp": x["amp"], "base": x["base"],
                "early_stop": es, "split": "train", "label": F.label_of(st, x["amp"]),
                "lufs_A": rend[i]["target"]["lufs_A"], "lufs_B": rend[i]["target"]["lufs_B"]}

    tr = [row(i, False) for i in tr_ids]
    fs = [row(i, True) for i in fs_ids]
    files = {r["i"]: (str(T.ex_path(root, STAGE, r["i"], f"mix-{STAGE}")),
                      str(T.ex_path(root, STAGE, r["i"], f"{T.SEP}-{STAGE}"))) for r in tr + fs}
    return tr, fs, files


def run_path(root, seed):
    return T.stage_root(root, STAGE) / "runs" / f"{ARM}-{seed}.json"


def cmd_train(args):
    """One D_CC run (demucs-venv): D_F5's recipe (`trusted_data_t3.cmd_train` for D_F5: the full heads, the masked
    loss, the amp head, D_stem's augmentation with the full twins' target mels as merge partners), early stopping on
    FS_CC."""
    import numpy as np
    import torch

    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import pretrain_set as PS
    from learn import trusted_data_t3 as T3

    require(args, renders=True)
    root = V.out_root(args)
    if args.seed not in T.TRAIN_SEEDS and not args.smoke:
        raise SystemExit(f"--seed in {T.TRAIN_SEEDS}")
    rp = run_path(root, args.seed)
    if rp.exists():
        print(f"{rp.name} exists: nothing to do")
        return
    plan = load_plan(args)
    tr_rows, es_rows, files = arm_rows(args, plan)
    rows_ = tr_rows + es_rows
    tr, es = np.arange(len(tr_rows)), np.arange(len(tr_rows), len(rows_))
    torch.set_num_threads(2)
    dev = torch.device("cpu" if os.environ.get("DS_DEVICE") == "cpu" or not torch.backends.mps.is_available()
                       else "mps")
    data = T.ArmData(rows_, files, aug=True, encode=T3.encode_for(T3.FULL), partner_path=lambda i: tgt_path(root, i))
    print(f"{ARM} seed {args.seed}: {len(tr)} train, {len(es)} early stopping (FS_CC); {dev}", flush=True)
    t0 = time.time()
    for attempt in (1, 2):
        log = []
        data.masked, data.applied = 0, {}
        try:
            net, state, best_ep, best = DS.train_arm(data, tr, es, args.seed, dev, log, DS.MAX_EPOCHS,
                                                     build=F.build_net, loss=F.loss_fn)
            break
        except PS.StepsSkipped as e:
            print(f"attempt {attempt} aborted: {e}", flush=True)
            if dev.type == "mps":
                torch.mps.empty_cache()
            if attempt == 2:
                raise SystemExit(f"TRAIN FAILED {ARM} {args.seed}: {e}")
    rp.parent.mkdir(parents=True, exist_ok=True)
    mp = rp.with_suffix(".pt")
    torch.save(state, mp)
    _save(rp, {"plan": PLAN, "stage": ARM, "ledger": f"{LEDGER_ID} {LEDGER_KEY}", "arm": ARM, "seed": args.seed,
               "model_arm": T.MODEL_ARM, "stem_sep": T.SEP, "augmented": True,
               "labels": "115 (full space, masked; amp head)", "train": len(tr), "early_stop": len(es),
               "bands": sorted({r["band"] for r in tr_rows}), "attempts": attempt, "epochs_run": len(log),
               "best_epoch": best_ep, "best_early_stop_loss": best, "minutes": round((time.time() - t0) / 60, 1),
               "augmentations_applied": data.applied, "device": str(dev), "model": mp.name,
               "model_sha256": DS.hashlib_file(mp), "log": log, "smoke": bool(args.smoke),
               "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"TRAIN DONE {ARM} {args.seed}: best epoch {best_ep} of {len(log)}")
    if best_ep is not None and best_ep >= DS.MAX_EPOCHS - T3.CAP_EDGE:
        print(f"WARNING: best epoch {best_ep} is within {T3.CAP_EDGE} of the cap {DS.MAX_EPOCHS}: extend this run "
              "before it is read")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cc_build", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("verdicts", cmd_verdicts), ("checks", cmd_checks), ("stem-scan", cmd_stem_scan),
                     ("amp-bleed", cmd_amp_bleed), ("cleaning-scan", cmd_cleaning_scan), ("ear-page", cmd_ear_page),
                     ("plan", cmd_plan),
                     ("render", cmd_render), ("build", cmd_build), ("check", cmd_check), ("train", cmd_train)):
        s = sub.add_parser(name)
        s.set_defaults(fn=fn)
        s.add_argument("--out", default=None)
        s.add_argument("--smoke", action="store_true")
        if name in ("checks", "render", "amp-bleed", "cleaning-scan"):
            s.add_argument("--shard", type=CP.parse_shard, default=(0, 1))
        if name == "plan":
            s.add_argument("--dry", action="store_true")
            s.add_argument("--no-bleed-gate", action="store_true")
            s.add_argument("--sum-lower", action="store_true")
        if name == "build":
            s.add_argument("--device", choices=DEVICES, required=True)
            s.add_argument("--order", choices=("asc", "desc"), default="asc")
            s.add_argument("--limit", type=int, default=0)
        if name == "train":
            s.add_argument("--seed", type=int, required=True)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
