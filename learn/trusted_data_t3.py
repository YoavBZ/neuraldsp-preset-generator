"""T3's first step, F5: the paired pilot (`docs/trusted-data-t0-design.md`, "T3 (declared 2026-10-26, nothing run)";
`docs/every-control-plan.md`, amendment 2; ledger `trusted-data-t3`). Reached through `learn.trusted_data` with
`--stage t3`:

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    MSST=~/ndsp-presets/tools/msst-venv/bin/python; TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MAIN -m learn.trusted_data plan --stage t3 --dry                # zero renders: the pool, the sets; writes nothing
    $MAIN -m learn.trusted_data plan --stage t3                      # the same, written to t3/plan.json (V-real frozen)
    $MAIN -u -m learn.trusted_data render --stage t3 --shard k/3     # the full twins' targets + the positive control
    $MSST -m learn.trusted_data build --stage t3 --device mps --order asc    # mixes and X-LANCE stems
    $MSST -m learn.trusted_data build --stage t3 --device cpu --order desc   # optional second worker
    $TORCH_PY -m learn.trusted_data train --stage t3 --arm D_F5|D_core5 --seed 20261042|20261043
    $TORCH_PY -m learn.trusted_data fit --stage t3                   # constants, pulls (shared FS5), folds, E on FS
    $MSST -m learn.trusted_data vreal-crops --stage t3 --device mps  # the recovered members' crops and stems
    $TORCH_PY -m learn.trusted_data vreal-predict --stage t3         # the answer sets on V-real (zero renders)
    $MAIN -u -m learn.trusted_data vreal-render --stage t3 --shard k/3
    $MAIN -m learn.trusted_data report --stage t3                    # every F5 row

**F5** (declared): T2's own examples (its SYN builds are the core twins) re-rendered with full-space labels
(`learn/full_space.py`): each example keeps its T2 draw for today's space and every mix draw, its other-guitar renders,
stems and pans; only the target's new controls differ (seed 20261107 per example, part C's mode). FS5, the shared
early-stopping and fit set: T2's 4 early-stopping sections plus 2 more per band from T2's sections (seed 20261105),
12 sections; F5: T2's training examples less those on FS5's 8 new sections. A refusal in either twin drops the
example from both. The positive control: 50 F5 examples (seeded) rendered with every new control at S's value must
reproduce T2's stored target, and then, carried through the build and separation, T2's stored mix and stem features
(T2's match share, 0.99 of cells within one 0.5-dB step). D_core5 (today's 25, T2's recipe) and D_F5 (115: the
masked loss, the amp head) train on the same examples, seeds 20261042 and 20261043, early-stopping on FS5 in their
own twins; each model's constant and pull are fitted on FS5 (the same sections and examples), with the pull's
two-fold check printed. V-real: amp-fixed answers (S on the same amp), the gate D_F5 - D_core5 with both per-seed
pairs, no-pull answers, the constant, the families at S, T2's stored SYN; the output gain fitted to the stem's
loudness per answer (confirmed by the user 2026-10-26), its |LUFS error| a pipeline check.

Every Morgan render is isolate=True with one discarded priming render per (DI, amp) change (`direct_stems.Primer`)
and the first 0.25 s trimmed; at most 3 render processes machine-wide (`local_objective.RENDERS` matches
`trusted_data render|vreal-render`); 31 GB disk guard. Renders and separations do not overlap (the chain's order).
The pure parts are unit-tested (`tests/test_trusted_data_t3.py`, `tests/test_full_space.py`).
"""

from __future__ import annotations

import json
import math
import os
import pathlib
import random
import statistics
import time

from learn import full_space as F
from learn import trusted_data as T
from learn import verify_tracks as V

STAGE = "t3"
LEDGER_ID = "trusted-data-t3"
DESIGN = "docs/trusted-data-t0-design.md#t3-declared-2026-10-26-nothing-run"
FS_SEED = 20261105                       # FS5's 2 extra sections per band
FS_EXTRA = 2
PC_N = 50                                # the positive control's examples
PC_SEED_KEY = "positive control"         # set here (the plan gave none): seed_int(20261107, this key)
ARMS = ("D_core5", "D_F5")
TRAIN_SEEDS = T.TRAIN_SEEDS              # 20261042, 20261043
CORE, FULL = ARMS
DISK_PROJECT_GB = T.DISK_GUARD_GB + 5.0  # plan refuses a projection under 36 GB
ADMITTED_DI = "cambridge-new/EmptySignifier_Change_Full/20_ElecGtr2DI.wav"    # PR #296's admission
KEPT_OUT_BANDS = ("Adam Buckley", "Dark Ride", "Cnoc An Tursa")              # K's bands, and Cnoc An Tursa
RECOVERED = {"cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1": (90.0, 100.0),
             "cambridge-Signs-ElecGtr6": (63.5, 73.5)}
NEEDS_PART8 = "cambridge-Signs-ElecGtr6"                                    # only if part 8 clears its DI
NOT_ELIGIBLE = {"cambridge-Nosso_Mundo_Deixou_De_Existir-ElecGtr03": "recovered, but Ale Lak trains"}
METAL_INTAKE = "intake-2026-10-26"
METAL_BANDS = ("Arcadian Alone", "Daimon B", "Dark Illusion", "Inhumanity Vortex", "Peppermark", "Serapis", "DGX")
RENESANS = "Renesans"
RATES = {"renders_per_h": 6_900, "sep_per_h_mps": 850, "sep_per_h_both": 1_350, "train_min_per_4_7k": (11, 15)}
CONST = "constant"
FAMILY_ARMS = tuple(f"{FULL}:at-S:{k}" for k in F.FAMILIES)
SEED_ARMS = tuple(f"{a}:s{s}" for a in ARMS for s in TRAIN_SEEDS)
NOPULL_ARMS = tuple(f"{a}:nopull" for a in ARMS)
ANSWERS = ARMS + NOPULL_ARMS + SEED_ARMS + (CONST,) + FAMILY_ARMS          # 14 per direction
D_SYN = "D_SYN"                          # T2's stored SYN answers (their own pull), read from T2's V-real groups
CAP_EDGE = T.CAP_EDGE

_save, _load = V._save, V._load


# --- pure: the sets ------------------------------------------------------------------------------------------

def fs5_sections(train_sections_by_band, es_sections, seed=FS_SEED, extra=FS_EXTRA):
    """FS5: T2's early-stopping sections plus `extra` more per band, drawn (seeded, bands in sorted order, each
    band's sections sorted) from the band's T2 training sections. -> (all FS5 sections, the new ones), sorted."""
    rng = random.Random(seed)
    new = []
    for band in sorted(train_sections_by_band):
        secs = sorted(set(train_sections_by_band[band]) - set(es_sections))
        new += rng.sample(secs, min(extra, len(secs)))
    return sorted(set(es_sections) | set(new)), sorted(new)


def split_f5(train_ids, es_ids, section_of, fs_new):
    """(F5 ids, FS5 ids): FS5 is T2's early-stopping examples plus T2's training examples on FS5's new sections;
    F5 the rest of T2's training examples."""
    new = set(fs_new)
    moved = [i for i in train_ids if section_of[i] in new]
    f5 = sorted(i for i in train_ids if section_of[i] not in new)
    return f5, sorted(set(es_ids) | set(moved))


def positive_ids(f5_ids, n=PC_N):
    from learn import pretrain_set as PS

    ids = sorted(f5_ids)
    return sorted(random.Random(PS.seed_int(F.NEW_SEED, PC_SEED_KEY)).sample(ids, min(n, len(ids))))


def drop_both(ids, *refusal_sets):
    """A refusal in either twin drops the example from both."""
    bad = set().union(*refusal_sets) if refusal_sets else set()
    return [i for i in ids if i not in bad]


def vreal_membership(tr):
    """V-real's frozen membership (T3's plan step): T0's V-real-10, the recovered It Was My Fault ElecGtr1 (its band
    is a V-real band and never trains), Signs ElecGtr6 only when part 8 has cleared its DI (its target and measure DI
    verified in T0's lists). A member whose crop does not build is dropped before any read (printed then)."""
    base = list(tr["v_real"])
    rec = {}
    for slug, win in RECOVERED.items():
        t = (tr.get("targets") or {}).get(slug) or {}
        m = (tr.get("measure_dis") or {}).get(slug) or {}
        recovered = slug in (tr.get("recovered_targets") or [])
        ok = recovered and t.get("verdict") == "verified"
        why = "eligible" if ok else ("not recovered by the window re-check" if not recovered
                                    else f"target {t.get('verdict')}")
        if ok and slug == NEEDS_PART8 and m.get("verdict") != "verified":
            ok, why = False, f"part 8 has not cleared its DI (measure DI {m.get('verdict')}): out of all of T3"
        rec[slug] = {"window_s": list(win), "eligible": ok, "why": why}
    members = base + [s for s, v in rec.items() if v["eligible"]]
    return {"members": members, "v_real_10": base, "recovered": rec, "not_eligible": dict(NOT_ELIGIBLE),
            "name": f"V-real-{len(members)}", "rule": "frozen at F5's plan step; a later ear sitting cannot change it"}


# --- pure: the gain groups -------------------------------------------------------------------------------------

def gain_class(part_a=None, ear_call=None, classified=None):
    """A section's gain class by the declared order: part A's class, else the intake's ear call on the amp track,
    else part A's classifier on the section's own amp track, else None (unclassed). -> (class, source)."""
    for v, src in ((part_a, "part A"), (ear_call, "intake ear call"), (classified, "classifier on the amp track")):
        if v:
            return str(v).replace("_", "-"), src
    return None, "unclassed"


def gain_group(cls, metal_intake):
    """High gain or not: an unclassed section counts as high gain if its band came through the metal intake, else
    not (T2's unclassed bands, Ale Lak and Storm Of Particles; a stated limit)."""
    if cls is None:
        return "high gain" if metal_intake else "not high gain"
    return "high gain" if cls == "high-gain" else "not high gain"


def pool_table(rows):
    """rows: [{"band", "status", "class", "group"}] (one per section). -> {band: {status: {"sections", "by_class",
    "by_group"}}} and the totals by status and group."""
    out, tot = {}, {}
    for r in rows:
        b = out.setdefault(r["band"], {}).setdefault(r["status"], {"sections": 0, "by_class": {}, "by_group": {}})
        b["sections"] += 1
        c = r["class"] or "unclassed"
        b["by_class"][c] = b["by_class"].get(c, 0) + 1
        b["by_group"][r["group"]] = b["by_group"].get(r["group"], 0) + 1
        t = tot.setdefault(r["status"], {})
        t[r["group"]] = t.get(r["group"], 0) + 1
    return out, tot


# --- pure: the readout and the report ---------------------------------------------------------------------------

def contrasts():
    """{name: (a, b)} of F5's V-real rows: the gate, its per-seed pairs and no-pull beside, each model against S and
    the constant, D_core5 against T2's stored SYN, and the families."""
    out = {f"{FULL} - {CORE} (the gate)": (FULL, CORE)}
    for s in TRAIN_SEEDS:
        out[f"{FULL}:s{s} - {CORE}:s{s}"] = (f"{FULL}:s{s}", f"{CORE}:s{s}")
    out[f"{FULL}:nopull - {CORE}:nopull"] = (f"{FULL}:nopull", f"{CORE}:nopull")
    out.update({f"{FULL} - S": (FULL, "S"), f"{CORE} - S": (CORE, "S"), f"{FULL} - constant": (FULL, CONST),
                f"{FULL}:nopull - S": (f"{FULL}:nopull", "S"), f"{CORE}:nopull - S": (f"{CORE}:nopull", "S"),
                f"{CORE} - {D_SYN} (T2's stored, own pull)": (CORE, D_SYN)})
    for k in F.FAMILIES:
        out[f"family {k}: {FULL} - {FULL} with it at S"] = (FULL, f"{FULL}:at-S:{k}")
    return out


def rule_reading(s):
    """The user's rule: an effect size with its interval, no pass bar."""
    if not s or s.get("band_weighted_mean") is None:
        return "incomplete"
    m, lo, hi = s["band_weighted_mean"], s.get("lo90"), s.get("hi90")
    if lo is None or hi is None:
        return "no interval (one band)" + (": point below 0" if m < 0 else ": point at or above 0")
    if hi < 0:
        return "shown (interval below 0)"
    if m < 0:
        return "leans better (point below 0, interval holds 0): built on, not shown"
    if lo > 0:
        return "worse (interval above 0)"
    return "point at or above 0 (not shown)"


def gate_next(s):
    if not s or s.get("band_weighted_mean") is None:
        return "incomplete: no decision"
    if s["band_weighted_mean"] < 0:
        return "point below 0: F20 runs (the user's OK on the T3 plan covers it)"
    return "at or above 0: stop and report; F20 only with the user's yes (the every-control plan's 2D tie rule)"


def lufs_summary(errs):
    """The output-gain fit's |LUFS error| over directions: mean, median, max, n, clamped count."""
    vals = [e["abs_error_db"] for e in errs if e.get("abs_error_db") is not None and math.isfinite(e["abs_error_db"])]
    if not vals:
        return {"n": 0}
    return {"n": len(vals), "mean_db": statistics.fmean(vals), "median_db": statistics.median(vals),
            "max_db": max(vals), "clamped": sum(1 for e in errs if e.get("clamped"))}


def runs_at_cap(recs, max_epochs):
    return [f"{r['arm']} seed {r['seed']} (best epoch {r['best_epoch']}/{max_epochs})" for r in recs
            if r and r.get("best_epoch") is not None and r["best_epoch"] >= max_epochs - CAP_EDGE]


def f5_estimate(n_targets, n_pc, n_groups, n_train, n_vreal_parts, rates=RATES):
    """F5's cost from the pool (T2's measured rates): renders (targets, the positive control's, one priming per
    (section, amp) group), separations (twins + the positive control's), 4 runs, V-real (14 answer sets x 3 amps x
    2 directions per part, one priming per group). -> dict with hours."""
    renders = n_targets + n_pc + n_groups
    seps = n_targets + n_pc
    lo, hi = rates["train_min_per_4_7k"]
    train_h = (4 * lo * n_train / 4700 / 60, 4 * hi * n_train / 4700 / 60)
    vreal = n_vreal_parts * 3 * (2 * len(ANSWERS) + 1)
    return {"renders": renders, "render_h": renders / rates["renders_per_h"], "separations": seps,
            "sep_h": (seps / rates["sep_per_h_both"], seps / rates["sep_per_h_mps"]), "train_h": train_h,
            "vreal_renders": vreal, "vreal_h": vreal / rates["renders_per_h"]}


# --- I/O --------------------------------------------------------------------------------------------------------

def require_t3(args):
    V.require_real(args)
    if not args.smoke and f'"{LEDGER_ID}"' not in (V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text():
        raise SystemExit(f"the ledger has no {LEDGER_ID} entry: real T3 runs refuse")


def load_plan(root, smoke=False):
    plan = _load(T.plan_path(root, STAGE))
    if not plan or (plan.get("smoke") and not smoke):
        raise SystemExit("run `plan --stage t3` first")
    T.check_lists(root, plan, smoke)
    return plan


def run_path(root, arm, seed):
    return T.stage_root(root, STAGE) / "runs" / f"{arm}-{seed}.json"


def files_of(root, arm, i):
    """(mix, stem) features: D_core5 reads T2's stored SYN build (the core twin), D_F5 its full twin's."""
    st = "t2" if arm == CORE else STAGE
    return str(T.ex_path(root, st, i, f"mix-{st}")), str(T.ex_path(root, st, i, f"{T.SEP}-{st}"))


class Menus:
    """The factory menu without a render: the dried menu `phase2_set3.menus` makes (rule set R) and the same presets
    un-dried (the factory centres of the new controls), through `render_preset_panel` with a stand-in for the
    renderer's stored-value conversion (the pack's own)."""

    def __init__(self):
        import argparse
        import sys

        sys.path.insert(0, str(V.PLUGIN_ROOT / "research"))
        import render_preset_panel as RP

        from packs.loader import load_pack

        class _Shim:
            warnings: list = []

            @staticmethod
            def _stored(pack, spec, value):
                return pack.to_stored(spec, value)

        self.pack = load_pack("morgan")
        self.dried, self.undried, self.gate_u = {}, {}, None
        for amp in F.AMPS:
            m = RP.candidates(argparse.Namespace(amp=amp, factory_dir=RP.FACTORY), self.pack, _Shim)
            for n, (path, rule) in m.items():
                if n == "template":
                    continue
                for tgt, r in ((self.dried, rule), (self.undried, False)):
                    sel, ed = RP.preset_edits(path, self.pack, _Shim, amp, r)
                    tgt.setdefault(amp, {})[n] = (sel, {(e["module"], e["key"]): e["value"] for e in ed})

    def gate_thresholds(self):
        return [v[1][F.GATE_THR] for m in self.undried.values() for v in m.values() if F.GATE_THR in v[1]]

    def centre(self, amp, name):
        return self.undried[amp][name][1]


def check_menu(live, dried):
    """The live menu (rr.menu()) must be the menu this module rebuilt without the renderer."""
    if live != dried:
        bad = sorted({(a, n) for a in set(live) | set(dried) for n in set(live.get(a, {})) ^ set(dried.get(a, {}))}
                     | {(a, n) for a in live for n in live[a] if n in dried.get(a, {}) and live[a][n] != dried[a][n]})
        raise SystemExit(f"the live menu differs from the rebuilt one (e.g. {bad[:3]})")


def core_settings(i, menu):
    """Example i's core twin setting (part C's draw, T2's target). -> (amp, mode, base, select, x, centre name)."""
    from learn import knob_ceiling as K
    from learn import pretrain_set as PS

    rng, amp, mode, base = PS.plan_example(i)
    sel, x, _, cname = PS.settings_for(rng, amp, mode, base, menu, K.START, K.space, K.fmt)
    return amp, mode, base, sel, x, cname


def full_twin(i, menus):
    """Example i's full twin: (amp, mode, base, select, full setting, core setting, centre name, tries)."""
    from learn import knob_ceiling as K

    amp, mode, base, sel, core, cname = core_settings(i, menus.dried)
    S = menus.dried[amp][K.START[base][amp]][1]
    centre = menus.centre(amp, cname) if mode == "factory" else S
    x, tries = F.draw_new(i, mode, core, centre, S, menus.gate_u)
    return amp, mode, base, sel, x, core, cname, tries


# --- plan (zero renders) ---------------------------------------------------------------------------------------

def _t2_sets(root, ctx, tr):
    """T2's kept examples under T2's own refusals, and those today's T0 lists no longer let a mix use.
    -> (train ids, es ids, {i: section}, {i: band}, stale [(i, why)])."""
    t2 = _load(T.plan_path(root, "t2"))
    if not t2:
        raise SystemExit("T2's plan is missing (t2/plan.json): F5 re-renders T2's examples")
    ses, _ = T.ses_rows(ctx)
    refused, unbuilt = T.t2_refused(root, t2, ses)
    if unbuilt:
        raise SystemExit(f"{len(unbuilt)} of T2's examples are not built")
    ex = {x["i"]: x for x in t2["examples"]}
    verified, bad = T.verified_dis(tr), T.unusable(tr)
    stale = []
    for i in t2["pilot"] + t2["es"]:
        if i in refused:
            continue
        x = ex[i]
        if x["di"] not in verified:
            stale.append((i, "the target's DI is no longer verified"))
        elif x["section"] in bad:
            stale.append((i, "the section is no longer usable"))
        elif any(o["di"] not in verified for o in x["others"]):
            stale.append((i, "an other guitar's DI is no longer verified"))
    gone = refused | {i for i, _ in stale}
    tr_ids = [i for i in t2["pilot"] if i not in gone]
    es_ids = [i for i in t2["es"] if i not in gone]
    return t2, tr_ids, es_ids, {i: ex[i]["section"] for i in ex}, {i: ex[i]["band"] for i in ex}, stale, refused


def _amp_track_class(ctx, sec):
    """Part A's classifier (`classify`) on the section's own amp track against its DI (zero renders)."""
    import sys

    import numpy as np

    from learn import pretrain_set as PS

    rec = ctx.inv[sec["di"]]
    sess = pathlib.Path(rec["session_dir"])
    own = V.own_amp_tracks(rec, sorted(f.name for f in sess.glob("*.wav")))
    if not own:
        return None
    sys.path.insert(0, str(PS.HOME / "references/datasets-set3/_tools"))
    import classify as C
    import gainmeasure as GM

    trim = int(PS.TRIM_S * PS.SR)
    di = PS.section_audio(sec["path"], sec["start_s"])[trim:]
    amp = PS.section_audio(sess / own[0], sec["start_s"])[trim:]
    m = GM.measures(np.asarray(amp, np.float64), np.asarray(di, np.float64), PS.SR)
    return C.classify(m)[0] if m else None


def _pool_rows(ctx, tr, t2, kept_sections, classify=True):
    """One row per candidate training section of the pool (zero renders): T2's kept sections (F5's), T2's left-out
    ones with their reason, and the trusted sections T2 never drew (Renesans: waiting on the session_guitar_parts
    fix and its stems; sections whose part C examples the cleaning manifest excluded or the D build refused).
    Kept-out bands (K's, Cnoc An Tursa) and V-real's never appear."""
    from learn import data_cleaning as DC

    verified, bad = T.verified_dis(tr), T.unusable(tr)
    ses, _ = T.ses_rows(ctx)
    ses_secs = {r["section"] for r in ses.values()}
    man = _load(DC.pool_root(DC.OUT) / "manifest.json") or {}
    excl = {int(i) for i in man.get("excluded") or []}
    pool_by = {}
    for r in ctx.pool:
        pool_by.setdefault(r["section"], []).append(r["i"])
    left = {x["section"]: x["reason"] for x in t2.get("left_out") or []}
    intake_calls = {d: ear_call(v) for d, v in (tr.get("intake_dis") or {}).items()}
    rows = []
    for sid, sec in sorted(ctx.sections.items()):
        rec = ctx.inv.get(sec["di"]) or {}
        band = sec.get("band") or rec.get("band")
        if sec["di"] not in tr["training_dis"] or sec["di"] not in verified or sid in bad or band in KEPT_OUT_BANDS:
            continue
        if sid in kept_sections:
            status = "T2's sections (F5)"
        elif sid in left:
            status = f"left out at T2: {left[sid]}"
        elif band == RENESANS:
            status = "waits: the session_guitar_parts fix and its stems"
        elif sid in pool_by and sid not in ses_secs:
            ids = pool_by[sid]
            status = ("not in T2's candidates: the cleaning manifest excluded its examples" if all(i in excl for i in ids)
                      else "not in T2's candidates: excluded at cleaning or refused at the D build")
        else:
            status = "not in T2's candidates: no part C training examples"
        cls_a = rec.get("gain_class")
        amp_cls = _amp_track_class(ctx, sec) if (classify and not cls_a and not intake_calls.get(sec["di"])) else None
        cls, src = gain_class(cls_a, intake_calls.get(sec["di"]), amp_cls)
        rows.append({"section": sid, "band": band, "status": status, "class": cls, "class_from": src,
                     "group": gain_group(cls, band in METAL_BANDS)})
    return rows


def ear_call(rec):
    """An intake DI's ear call: its own tone card on its amp track; else, for a DI with no amp track of its own, the
    playing style heard on its DI card (part 9's second question, `style_class`: clean_crunch or high_gain; can't
    tell leaves it None); else its session's tone (PR #297's metal records); else the metal intake's rule for a
    session with no amp track (DGX, and Strobe's and MekaPhil's DI-only DIs heard "can't tell" or not asked: counts as
    high gain). Only an explicit clean/crunch-style answer makes a DI-only DI not high gain."""
    return (rec.get("tone_class") or rec.get("style_class") or rec.get("session_tone")
            or rec.get("no_tone_counts_as"))


def metal_counts(intake_dis, summary):
    """{band: {verdict: DIs}} of the metal intake: T0's lists' verdicts where they hold the metal DIs (PR #297's
    `metal_verdicts`), else the intake's measured T0 checks (every DI then waits for the ear: nothing is heard yet).
    -> (counts, source)."""
    rec = {d: v for d, v in (intake_dis or {}).items() if v.get("band") in METAL_BANDS}
    by = {}
    if rec:
        for v in rec.values():
            b = by.setdefault(v["band"], {})
            b[v["verdict"]] = b.get(v["verdict"], 0) + 1
        return by, "T0's lists"
    for sess, d in (summary.get("sessions") or {}).items():
        for f, v in d.items():
            b = by.setdefault(v["band"], {})
            k = "excluded" if v["verdict"][0] == "excluded" else "pending ear"
            b[k] = b.get(k, 0) + 1
    return by, "the intake's T0 checks (not yet in T0's lists)"


def _intake_lines(tr, root):
    """The admitted non-metal intake DIs (Empty Signifier's; Strobe's and MekaPhil's, part 9) and the metal intake
    (zero renders): what joins once each passes."""
    out = []
    for d, v in sorted((tr.get("intake_dis") or {}).items()):
        if d in (tr.get("intake_admitted") or []) and v.get("band") not in METAL_BANDS:
            call = ear_call(v)
            src = ("its amp track's tone card" if v.get("tone_class") else "the playing style on its DI card"
                   if v.get("style_class") else "its session's tone card" if v.get("session_tone")
                   else "the DI-only rule" if v.get("no_tone_counts_as") else "none: unclassed")
            line = (f"  {v.get('band')}: {pathlib.Path(d).name} admitted, ear call {call} "
                    f"({gain_group(gain_class(None, call)[0], False)}; from {src}); "
                    f"heard windows {[w[:2] for w in v.get('heard') or []]}; trains once the DI inventory is "
                    "rebuilt (its sections are counted then)")
            if v.get("band") == "Empty Signifier":
                line += ("; ElecGtr1's DI is excluded (hum), so sections where ElecGtr1 plays leave unless its mic "
                         "tracks pass the bleed check (PR #296)")
            out.append(line)
    s = _load(root / METAL_INTAKE / "summary.json") or {}
    by, src = metal_counts(tr.get("intake_dis"), s)
    n_adm = sum(b.get("verified", 0) for b in by.values())
    out.append(f"  the metal and hard-rock intake ({METAL_INTAKE}; verdicts from {src}): "
               f"{sum(sum(b.values()) for b in by.values())} electric DIs in {len(by)} bands, {n_adm} admitted so far; "
               "none is in the pool until heard (each joins F20 after T0's checks and the ear, under the caps, as high "
               "gain unless its tone card says otherwise):")
    for b in sorted(by):
        out.append(f"    {b}: " + ", ".join(f"{k} {n}" for k, n in sorted(by[b].items())))
    return out


def print_pool(rows, tr, root):
    table, tot = pool_table(rows)
    print("THE POOL, by band and gain group (zero renders; each section's class: part A's, else the intake's ear "
          "call, else part A's classifier on its own amp track; unclassed counts as not high gain outside the metal "
          "intake):")
    for band in sorted(table):
        for status, v in sorted(table[band].items()):
            cls = ", ".join(f"{k} {n}" for k, n in sorted(v["by_class"].items()))
            grp = ", ".join(f"{k} {n}" for k, n in sorted(v["by_group"].items()))
            print(f"  {band:22s} {v['sections']:3d} sections  [{status}]  classes: {cls}; groups: {grp}")
    for status, g in sorted(tot.items()):
        print(f"  total [{status}]: {sum(g.values())} sections; " + ", ".join(f"{k} {n}" for k, n in sorted(g.items())))
    for line in _intake_lines(tr, root):
        print(line)
    print(f"  kept out: {', '.join(KEPT_OUT_BANDS)} (K's bands and Cnoc An Tursa), every reservation in the ledger, "
          "V-real's bands; Rebuild The Evil and The Long Wait stay out under rule 1 (no amp track passed the bleed "
          "check)")


def cmd_plan(args):
    """F5's plan (zero renders, CPU): FS5 and F5 from T2's examples, the positive control, the new controls' modes,
    the wide gate cap, V-real's frozen membership, the pool by band and gain group, the cost. `--dry` prints only."""
    from learn import direct_stems as DS
    from learn import pretrain_set as PS

    require_t3(args)
    root = V.out_root(args)
    tr = T.load_lists(root, args.smoke)
    if ADMITTED_DI not in (tr.get("intake_admitted") or []) and not args.smoke:
        raise SystemExit("T0's lists lack PR #296's admission (Empty Signifier 20_ElecGtr2DI): rerun `verify_tracks lists`")
    ctx = DS.Ctx(quiet=True)
    t2, tr_ids, es_ids, section_of, band_of, stale, t2_refused = _t2_sets(root, ctx, tr)
    if t2.get("lists_sha256") != T.lists_sha(root):
        print("T0's lists changed since T2's plan: T2's examples re-checked under today's lists "
              f"({len(stale)} dropped)", flush=True)
    for i, why in stale[:10]:
        print(f"  dropped {i}: {why}")
    by_band = {}
    for i in tr_ids:
        by_band.setdefault(band_of[i], set()).add(section_of[i])
    fs_all, fs_new = fs5_sections(by_band, t2["es_sections"])
    f5, fs = split_f5(tr_ids, es_ids, section_of, fs_new)
    pc = positive_ids(f5)
    menus = Menus()
    gate_u, gate_v = F.gate_cap_u(menus.gate_thresholds())
    menus.gate_u = gate_u
    modes = {}
    for i in f5 + fs:
        mode = PS.plan_example(i)[2]
        modes[mode] = modes.get(mode, 0) + 1
    vr = vreal_membership(tr)
    exs = []
    for i in sorted(f5 + fs):
        _, amp, mode, base = PS.plan_example(i)
        exs.append({"i": i, "section": section_of[i], "band": band_of[i], "set": "FS5" if i in set(fs) else "F5",
                    "amp": amp, "base": base, "mode": mode, "positive": i in set(pc)})
    sections = sorted({x["section"] for x in exs})
    groups = len({(x["section"], x["amp"]) for x in exs})
    est = f5_estimate(len(exs), len(pc), groups, len(f5), len(vr["members"]))
    t2_bytes = sum(p.stat().st_size for p in (T.stage_root(root, "t2") / "audio").rglob("*-target.flac"))
    n_t2_targets = sum(1 for _ in (T.stage_root(root, "t2") / "audio").rglob("*-target.flac")) or 1
    npz = sum(p.stat().st_size for p in (T.stage_root(root, "t2") / "build").rglob("*.npz"))
    n_npz = sum(1 for _ in (T.stage_root(root, "t2") / "build").rglob("*.npz")) or 1
    add_gb = (len(exs) + len(pc)) * t2_bytes / n_t2_targets / 1e9 + 2 * len(exs) * npz / n_npz / 1e9
    free = PS.free_gb()
    print(f"T3 F5 plan ({DESIGN}){' [dry run: nothing written]' if args.dry else ''}")
    print(f"T2's examples kept: {len(tr_ids)} training + {len(es_ids)} early stopping ({len(t2_refused)} refused at T2, "
          f"{len(stale)} dropped under today's lists); {len({section_of[i] for i in tr_ids + es_ids})} sections in "
          f"{len(by_band)} bands")
    print(f"FS5: {len(fs_all)} sections ({len(t2['es_sections'])} T2 early-stopping + {len(fs_new)} new, seed {FS_SEED}), "
          f"{len(fs)} examples: " + ", ".join(f"{b} {sum(1 for x in exs if x['set'] == 'FS5' and x['band'] == b)}"
                                              for b in sorted(by_band)))
    for s in fs_new:
        print(f"  new FS5 section: {s}")
    print(f"F5: {len(f5)} examples in {len({section_of[i] for i in f5})} sections: "
          + ", ".join(f"{b} {sum(1 for x in exs if x['set'] == 'F5' and x['band'] == b)}" for b in sorted(by_band)))
    print(f"the positive control: {len(pc)} F5 examples (seed_int({F.NEW_SEED}, {PC_SEED_KEY!r}))")
    print(f"the new controls' modes (part C's, per example): {dict(sorted(modes.items()))}; the wide gate threshold "
          f"stops at the factory presets' {F.GATE_CAP_PCT}th percentile, {gate_v:g} dB (unit {gate_u:.4f}, "
          f"{len(menus.gate_thresholds())} presets)")
    print(f"V-real: {vr['name']} frozen: " + ", ".join(vr["members"]))
    for s, v in vr["recovered"].items():
        print(f"  {s}: {v['why']} (window {v['window_s'][0]}-{v['window_s'][1]} s)")
    prow = _pool_rows(ctx, tr, t2, {section_of[i] for i in tr_ids + es_ids})
    print_pool(prow, tr, root)
    grp = {r["section"]: r["group"] for r in prow}
    src = {r["section"]: r["class_from"] for r in prow}
    hg = sum(1 for x in exs if grp.get(x["section"]) == "high gain")
    hg_a = sum(1 for x in exs if grp.get(x["section"]) == "high gain" and src.get(x["section"]) == "part A")
    print(f"F5 and FS5 by gain group (example-weighted): high gain {hg}/{len(exs)} ({hg / max(1, len(exs)):.0%}); "
          f"by part A's class alone {hg_a}/{len(exs)} ({hg_a / max(1, len(exs)):.0%}). F5 keeps T2's mix (pairing); "
          "the 50% cap applies to F20's new draws")
    print(f"cost (T2's rates): {est['renders']} renders ({len(exs)} full-twin targets, {len(pc)} positive control, "
          f"about {est['renders'] - len(exs) - len(pc)} priming), about {est['render_h']:.1f} h on 3 processes; "
          f"{est['separations']} separations, about {est['sep_h'][0]:.1f}-{est['sep_h'][1]:.1f} h; 4 runs about "
          f"{est['train_h'][0]:.1f}-{est['train_h'][1]:.1f} h MPS; V-real {est['vreal_renders']} renders about "
          f"{est['vreal_h']:.1f} h")
    print(f"disk: about {add_gb:.1f} GB added (T2's measured file sizes); {free:.1f} GB free, projected "
          f"{free - add_gb:.1f} GB (plan refuses under {DISK_PROJECT_GB:.0f} GB)")
    if free - add_gb < DISK_PROJECT_GB and not args.smoke:
        raise SystemExit(f"projected free disk {free - add_gb:.1f} GB is under {DISK_PROJECT_GB:.0f} GB")
    if args.dry:
        return
    rec = {"plan": T.PLAN, "design": DESIGN, "stage": STAGE, "step": "F5", "smoke": bool(args.smoke),
           "seeds": {"fs": FS_SEED, "new_controls": F.NEW_SEED, "positive_control": [F.NEW_SEED, PC_SEED_KEY],
                     "train": list(TRAIN_SEEDS)},
           "t2_plan": T.plan_key(t2), "f5": f5, "fs5": fs, "fs5_sections": fs_all, "fs5_new_sections": fs_new,
           "positive_control": pc, "stale_dropped": stale, "examples": exs, "gate_cap": {"unit": gate_u, "db": gate_v,
           "pct": F.GATE_CAP_PCT}, "vreal": {**vr, "frozen": time.strftime("%Y-%m-%d %H:%M:%S")},
           "output_gain_fit": F.OUTPUT_FIT_STATUS, "estimate": est, "sections": len(sections),
           "lists_sha256": T.lists_sha(root), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    old = _load(T.plan_path(root, STAGE))
    if old and T.rows_of(root, STAGE, "render"):
        keep = {k: old.get(k) for k in ("f5", "fs5", "positive_control", "examples")}
        if keep != {k: rec[k] for k in keep} or old.get("vreal", {}).get("members") != vr["members"]:
            raise SystemExit("T3 was rendered under another plan (or V-real membership): move t3/ aside first")
        rec["vreal"] = old["vreal"]                                     # frozen: a re-plan never changes it
    _save(T.plan_path(root, STAGE), rec)
    print(f"T3 PLAN WRITTEN: {len(exs)} examples, V-real {vr['name']} frozen")


# --- render (MAIN; renders) --------------------------------------------------------------------------------------

CONTROL_MOVE_DB = 12.0                   # the control check: the amp EQ's 1-kHz band at +12 dB (EQ on)
PC_DEVICE_RULE = ("the positive control's stems are compared within one device: each control example is separated "
                  "on the device T2 built it on (T2's build rows); the chain runs the MPS and CPU workers")


def control_move(x, amp):
    """The control check's moved setting: x with the amp's EQ on (section on) and its 1-kHz band at +12 dB, a new
    control that sounds whenever the amp is selected."""
    y = dict(x)
    y[("eqParameters", "sectionActive")] = "true"
    y[(f"{amp}EQ", f"{amp}EQActive")] = "true"
    y[(f"{amp}EQ", f"{amp}EQBand5")] = f"{CONTROL_MOVE_DB:g}"
    return y


def render_example(x, menus, primer, sid, di, part_c_settings, kind, trim):
    """One example's render (`kind` "full": its full twin; "positive": every new control at S's value). The row's
    stored settings are exactly the settings rendered. -> (row, trimmed mono render, core setting)."""
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    amp, mode, base, sel, xf, core, cname, tries = full_twin(x["i"], menus)
    if {f"{a}/{b}": v for (a, b), v in core.items()} != part_c_settings or amp != x["amp"]:
        raise SystemExit(f"{x['i']}: the core draw differs from part C's row")
    settings = xf if kind == "full" else F.positive_settings(core, menus.dried[amp][K.START[base][amp]][1])
    y = primer.render((sid, amp), di, sel, settings)
    y = (y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]]
    row = {"i": x["i"], "section": sid, "set": x["set"], "kind": kind, "amp": amp, "mode": mode, "centre": cname,
           "tries": tries, "settings": LO.sdict(settings)}
    return row, y, core


def target_features(y):
    """A target render's half mels and half loudness, as part C stored its targets (`halves_mel`; LUFS per half):
    the full twins' merge partners for D_F5's augmentation. -> ({"gA", "gB"}, {"lufs_A", "lufs_B"})."""
    from learn import pretrain_set as PS
    from learn import song_aug as SA

    m = PS.halves_mel(y)
    return {"gA": m["A"], "gB": m["B"]}, {f"lufs_{h}": float(SA.lufs(y[s])) for h, s in PS.half_slices().items()}


def tgt_path(root, i):
    return T.ex_path(root, STAGE, i, f"tgt-{STAGE}")


def _render_setup(args, plan, prefix):
    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS

    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"free disk below {T.DISK_GUARD_GB:.0f} GB")
    menus = Menus()
    menus.gate_u = plan["gate_cap"]["unit"]
    LO._wait_cap()
    DS.wait_render_slot()
    rr = K.Renderer()
    try:
        DS.check_recipe(rr)
        check_menu(rr.menu(), menus.dried)
        if abs(F.gate_cap_u(menus.gate_thresholds())[0] - plan["gate_cap"]["unit"]) > 1e-12:
            raise SystemExit("the factory gate thresholds changed since the plan")
    except BaseException:
        rr.close()
        raise
    k, n = args.shard
    rp = T.stage_root(T.V.out_root(args), STAGE) / "rows" / f"{prefix}-{k}of{n}.jsonl"
    rp.parent.mkdir(parents=True, exist_ok=True)
    return menus, rr, DS.Primer(rr), rp


def cmd_control_check(args):
    """The chain's first renders (3: one priming, then 2): the first positive-control example with every new control
    at S's value, and the same with one new control moved (`control_move`). The two must differ (the plugin takes
    the new controls' edits); written to t3/control-check.json, and an unchanged output stops here."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import pretrain_set as PS
    from learn import song_bank as B

    require_t3(args)
    root = V.out_root(args)
    plan = load_plan(root, args.smoke)
    x = next(e for e in plan["examples"] if e["i"] == plan["positive_control"][0])
    ctx = DS.Ctx(quiet=True)
    sec = ctx.sections[x["section"]]
    di = B.measure(PS.section_audio(sec["path"], sec["start_s"])).astype(np.float32)
    menus, rr, primer, _ = _render_setup(args, plan, "control")
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    try:
        amp, mode, base, sel, xf, core, cname, tries = full_twin(x["i"], menus)
        S = menus.dried[amp][K.START[base][amp]][1]
        a = F.positive_settings(core, S)
        b = control_move(a, amp)
        ya = primer.render((x["section"], amp), di, sel, a)
        yb = primer.render((x["section"], amp), di, sel, b)
    finally:
        rr.close()
    ya, yb = ((y.mean(axis=1) if y.ndim == 2 else y)[trim[0]:trim[1]] for y in (ya, yb))
    share = min(DS.match_share(PS.halves_mel(yb)[h], m) for h, m in PS.halves_mel(ya).items())
    diff = float(np.max(np.abs(ya - yb)))
    rec = {"i": x["i"], "amp": amp, "move": f"{amp}EQ/{amp}EQBand5 at +{CONTROL_MOVE_DB:g} dB (EQ on)",
           "mel_share_unchanged": share, "max_abs_diff": diff, "renders": primer.renders, "primes": primer.primes,
           "changed": share < DS.MATCH_SHARE, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(T.stage_root(root, STAGE) / "control-check.json", rec)
    print(f"control check: {rec}")
    if not rec["changed"]:
        raise SystemExit("CONTROL CHECK FAILED: moving a new control did not change the render")
    print("CONTROL CHECK OK")


def cmd_render(args):
    """Renders for one shard of whole sections (isolate=True, one priming render per (DI, amp) change, 0.25 s
    trimmed). Default: each example's full twin (T2's core draw + the new controls), refused below
    RENDER_FLOOR_LUFS, its half mels and loudness saved as `tgt-t3` (D_F5's merge partners). `--positive-only`:
    the positive control's 50 examples with every new control at S's value, each compared with T2's stored target
    and part C's mels (T2's match share); the chain renders and builds them before anything else."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import song_bank as B

    require_t3(args)
    root = V.out_root(args)
    plan = load_plan(root, args.smoke)
    kind = "positive" if args.positive_only else "full"
    prefix = "pc-render" if kind == "positive" else "render"
    k, n = args.shard
    pcs = set(plan["positive_control"])
    exs = [x for x in plan["examples"] if kind == "full" or x["i"] in pcs]
    shard = DS.shard_sections(exs, n)
    done = T.rows_of(root, STAGE, prefix)
    todo = [x for x in exs if shard[x["section"]] == k and x["i"] not in done]
    if not todo:
        print(f"RENDER DONE {k}/{n} (nothing to do)")
        return
    t2rend = T.rows_of(root, "t2", "render") if kind == "positive" else {}
    ctx = DS.Ctx(quiet=True)
    by_sec = {}
    for x in todo:
        by_sec.setdefault(x["section"], []).append(x)
    menus, rr, primer, rp = _render_setup(args, plan, prefix)
    swap0 = DS.swap_mb()
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    t_start, written = time.time(), []
    try:
        with open(rp, "a") as fh:
            for m, (sid, xs) in enumerate(sorted(by_sec.items())):
                g = DS._guards("t3-render", T.DISK_GUARD_GB, swap0)
                if g:
                    print(g[1], flush=True)
                    raise SystemExit(g[0])
                sec = ctx.sections[sid]
                di = B.measure(PS.section_audio(sec["path"], sec["start_s"])).astype(np.float32)
                for x in sorted(xs, key=lambda x: (x["amp"], x["i"])):
                    row, y, _ = render_example(x, menus, primer, sid, di, ctx.rows[x["i"]]["settings"], kind, trim)
                    if kind == "full":
                        ly = T.lufs_or_none(y)
                        why = T.near_silent(ly)
                        if why:
                            row.update(refused=f"full twin: {why}", lufs=ly)
                        else:
                            sc, sha = G.write_flac(T.flac_path(root, STAGE, x["i"], "target"), y, PS.SR)
                            mels, halves = target_features(y)
                            DS._save_npz(tgt_path(root, x["i"]), lufs=[halves["lufs_A"], halves["lufs_B"]], **mels)
                            row["target"] = {"scale": sc, "sha256": sha, "lufs": ly, **halves,
                                             "tgt_sha256": DS.hashlib_file(tgt_path(root, x["i"]))}
                    else:
                        stored = np.load(PS.example_path(x["i"]))
                        h1 = PS.halves_mel(y)
                        share_c = min(DS.match_share(h1[h], stored[f"g{h}"]) for h in h1)
                        t2r = t2rend[x["i"]]["target"]
                        h2 = PS.halves_mel(G.read_flac(T.flac_path(root, "t2", x["i"], "target"), t2r["scale"], t2r["sha256"]))
                        share_t2 = min(DS.match_share(h1[h], h2[h]) for h in h1)
                        sc, sha = G.write_flac(T.flac_path(root, STAGE, x["i"], "pc-target"), y, PS.SR)
                        row["positive"] = {"share_t2_target": share_t2, "share_part_c": share_c,
                                           "ok": share_t2 >= DS.MATCH_SHARE and share_c >= DS.MATCH_SHARE,
                                           "file": {"scale": sc, "sha256": sha}}
                    row["renders_so_far"] = primer.renders
                    written.append(row)
                    fh.write(json.dumps(row) + "\n")
                fh.flush()
                print(f"section {m + 1}/{len(by_sec)} {sid[-50:]}: {len(xs)} examples; renders {primer.renders} "
                      f"({primer.primes} priming); {(time.time() - t_start) / (m + 1):.0f} s per section", flush=True)
    finally:
        rr.close()
    print(f"refused in this shard, by reason: {T.refusal_counts(written) or 'none'}")
    if kind == "positive":
        print(f"positive control (render) in this shard: {sum(r['positive']['ok'] for r in written)}/{len(written)} "
              f"match (min share vs T2's target {min(r['positive']['share_t2_target'] for r in written):.4f})")
    print(f"RENDER DONE {k}/{n}: {primer.renders} renders ({primer.primes} priming)")


# --- build (MSST; separations) -----------------------------------------------------------------------------------

def feature_share(new, stored, keys):
    """The least DS.match_share over the halves' features (uint8 mels). new/stored: {key: array}."""
    from learn import direct_stems as DS

    return min(DS.match_share(new[k], stored[k]) for k in keys)


def pc_todo(pcs, pc_rendered, pc_built, t2_device, device):
    """The positive control's examples this worker separates: rendered, not built, and built by T2 on this device
    (the stems are compared within one device)."""
    return [i for i in sorted(pcs) if i in pc_rendered and i not in pc_built and t2_device.get(i) == device]


def cmd_build(args):
    """Mixes and X-LANCE stems (msst-venv), with T2's stored other guitars, stems, pans and mix draw
    (`trusted_data.self_built_mix`). Default: the full twins, features as `mix-t3` and `xlance_g-t3`.
    `--positive-only`: the positive control's S-valued renders, built and separated on the device T2 built them on,
    their mix and stem features compared with T2's stored `mix-t2` and `xlance_g-t2` (T2's match share); nothing
    is saved but the comparison."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS

    require_t3(args)
    root = V.out_root(args)
    plan = load_plan(root, args.smoke)
    t2 = _load(T.plan_path(root, "t2"))
    rec2 = {x["i"]: x for x in t2["examples"]}
    t2rend = T.rows_of(root, "t2", "render")
    t2built = T.rows_of(root, "t2", "build")
    xp_of = {x["i"]: x for x in plan["examples"]}
    if args.positive_only:
        pc_rend = T.rows_of(root, STAGE, "pc-render")
        ids = pc_todo(plan["positive_control"], pc_rend, T.rows_of(root, STAGE, "pc-build"),
                      {i: r.get("device") for i, r in t2built.items()}, args.device)
        rp = T.stage_root(root, STAGE) / "rows" / f"pc-build-{args.device}-{os.getpid()}.jsonl"
    else:
        rend = T.rows_of(root, STAGE, "render")
        built = T.rows_of(root, STAGE, "build")
        ids = [x["i"] for x in plan["examples"] if x["i"] in rend and x["i"] not in built]
        rp = T.stage_root(root, STAGE) / "rows" / f"build-{args.device}-{os.getpid()}.jsonl"
    ids.sort(key=lambda i: (xp_of[i]["section"], i), reverse=args.order == "desc")
    ids = ids[:args.limit or None]
    print(f"build t3{' (positive control)' if args.positive_only else ''}: {len(ids)} to build on {args.device}",
          flush=True)
    if not ids:
        print(f"BUILD DONE t3 ({args.device})")
        return
    ctx = DS.Ctx(quiet=True)
    ctx.rows = None
    sep = DS.stem_separator(T.SEP, args.device)
    stems = T.Stems(ctx)
    swap0 = DS.swap_mb()
    rp.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    def make(y, oth, st, x):
        mix, gains, lb = T.self_built_mix(np.asarray(y, np.float64), np.asarray(oth, np.float64), st, x)
        if not T.empty_backing_ok(y, lb):
            return None
        s = np.asarray(sep(mix), np.float64)
        if len(s) != len(mix) or not np.isfinite(s).all():
            raise SystemExit(f"{x['i']}: bad stem")
        return mix, s, gains, lb

    with open(rp, "a") as fh:
        for m, i in enumerate(ids):
            g = DS._guards("t3-build", T.DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            if not args.positive_only and T.ex_path(root, STAGE, i, f"{T.SEP}-{STAGE}").exists():
                continue                                    # the other worker's
            x = rec2[i]
            row = {"i": i, "section": x["section"], "band": x["band"], "set": xp_of[i]["set"], "device": args.device}
            o2 = t2rend[i]["others_file"]
            oth = G.read_flac(T.flac_path(root, "t2", i, "others"), o2["scale"], o2["sha256"])
            voc = x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"]
            st = stems.get(x["section"], T.backing_tracks(x, voc))
            row["vocals"] = bool(voc)
            if args.positive_only:
                pf = pc_rend[i]["positive"]["file"]
                made = make(G.read_flac(T.flac_path(root, STAGE, i, "pc-target"), pf["scale"], pf["sha256"]), oth, st, x)
                if made is None:
                    row["positive"] = {"ok": False, "why": "no backing (T2 built this example)"}
                else:
                    mix, s, _, _ = made
                    mm, ml, _ = DS.half_features(mix)
                    sm, _, _ = DS.half_features(s)
                    d2m, d2s = np.load(T.ex_path(root, "t2", i, "mix-t2")), np.load(T.ex_path(root, "t2", i, f"{T.SEP}-t2"))
                    sh_m = feature_share({"mA": mm["A"], "mB": mm["B"]}, d2m, ("mA", "mB"))
                    sh_s = feature_share({"sA": sm["A"], "sB": sm["B"]}, d2s, ("sA", "sB"))
                    row["positive"] = {"mix_share": sh_m, "stem_share": sh_s, "t2_device": t2built[i].get("device"),
                                       "mix_lufs_diff": float(max(abs(ml["A"] - d2m["lufs"][0]), abs(ml["B"] - d2m["lufs"][1]))),
                                       "ok": sh_m >= DS.MATCH_SHARE and sh_s >= DS.MATCH_SHARE}
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                continue
            rw = rend[i]
            if rw.get("refused"):
                fh.write(json.dumps({**row, "refused": rw["refused"]}) + "\n")
                fh.flush()
                continue
            tf = rw["target"]
            y = G.read_flac(T.flac_path(root, STAGE, i, "target"), tf["scale"], tf["sha256"])
            made = make(y, oth, st, x)
            if made is None:
                fh.write(json.dumps({**row, "refused": "no backing: the drawn ratio cannot be met"}) + "\n")
                fh.flush()
                continue
            mix, s, gains, lb = made
            mm, ml, _ = DS.half_features(mix)
            sm, sl, floor = DS.half_features(s)
            DS._save_npz(T.ex_path(root, STAGE, i, f"mix-{STAGE}"), mA=mm["A"], mB=mm["B"], lufs=[ml["A"], ml["B"]],
                         gain_db=gains["ga"], mastered=x["draw"]["mastered"])
            DS._save_npz(T.ex_path(root, STAGE, i, f"{T.SEP}-{STAGE}"), sA=sm["A"], sB=sm["B"], lufs=[sl["A"], sl["B"]])
            row.update({"gains_db": gains, "lufs_backing": lb, "lufs_mA": ml["A"], "lufs_mB": ml["B"],
                        "lufs_sA": sl["A"], "lufs_sB": sl["B"], "floor_share": floor,
                        "snr_audio_db": DS.snr_db(s, y * 10 ** (gains["ga"] / 20))})
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if m % 25 == 0:
                print(f"build {m + 1}/{len(ids)}: {(time.time() - t0) / (m + 1):.1f} s per example", flush=True)
    print(f"BUILD DONE t3 ({args.device})")


def positive_control(root, plan):
    """The positive control's state from its own render and build rows (`--positive-only`): (ok, summary dict)."""
    rend, built = T.rows_of(root, STAGE, "pc-render"), T.rows_of(root, STAGE, "pc-build")
    pcs = plan["positive_control"]
    r = [rend[i].get("positive") or {} for i in pcs if i in rend]
    b = [built[i].get("positive") or {} for i in pcs if i in built]
    s = {"examples": len(pcs), "rendered": len(r), "built": len(b),
         "render_ok": sum(1 for v in r if v.get("ok")), "build_ok": sum(1 for v in b if v.get("ok")),
         "min_render_share": min((v.get("share_t2_target", 0) for v in r), default=None),
         "min_mix_share": min((v.get("mix_share", 0) for v in b), default=None),
         "min_stem_share": min((v.get("stem_share", 0) for v in b), default=None), "rule": PC_DEVICE_RULE}
    s["ok"] = s["render_ok"] == s["build_ok"] == len(pcs)
    return s["ok"], s


def cmd_pc_check(args):
    """The positive control's verdict (zero renders): exits non-zero unless every control example matched T2 in
    the render and in the build."""
    require_t3(args)
    root = V.out_root(args)
    ok, s = positive_control(root, load_plan(root, args.smoke))
    print(f"positive control: {s}")
    if not ok:
        raise SystemExit("POSITIVE CONTROL FAILED: the pipeline does not repeat T2; nothing else runs")
    print("POSITIVE CONTROL OK")


# --- train, fit (demucs-venv) ------------------------------------------------------------------------------------

def t3_sets(root, plan):
    """(F5 ids, FS5 ids, refused, unbuilt): a refusal in either twin (render or build) drops it from both (T2's
    refusals left the plan already)."""
    rend, built = T.rows_of(root, STAGE, "render"), T.rows_of(root, STAGE, "build")
    bad = {i for i, r in rend.items() if r.get("refused")} | {i for i, r in built.items() if r.get("refused")}
    need = set(plan["f5"]) | set(plan["fs5"])
    unbuilt = {i for i in need if i not in built}
    return drop_both(plan["f5"], bad, unbuilt), drop_both(plan["fs5"], bad, unbuilt), bad & need, unbuilt


def arm_rows(root, ctx, plan, arm):
    """(training rows, FS5 rows) of an arm, the same examples in the same order for both arms: part C's rows; D_F5's
    labels and target half loudness (`lufs_A`, `lufs_B`: the merge augmentation's gains) are its full twins' (from
    the render rows), as its merge partners' mels are (`partner_path`)."""
    f5, fs, _, _ = t3_sets(root, plan)
    by = {r["i"]: r for r in ctx.pool}
    rend = T.rows_of(root, STAGE, "render") if arm == FULL else {}

    def row(i, es):
        r = {**by[i], "early_stop": es, "split": "train"}
        if arm == FULL:
            x = {tuple(k.rsplit("/", 1)): v for k, v in rend[i]["settings"].items()}
            r["label"] = F.label_of(x, r["amp"])
            r["lufs_A"], r["lufs_B"] = rend[i]["target"]["lufs_A"], rend[i]["target"]["lufs_B"]
        return r

    return [row(i, False) for i in f5], [row(i, True) for i in fs]


def partner_path(root, arm):
    """Where an arm's merge partners' half mels are: part C's stored targets (the core twins' renders) for
    D_core5, the full twins' `tgt-t3` for D_F5."""
    if arm == CORE:
        return None                                           # ArmData's default: pretrain_set.example_path
    return lambda i: tgt_path(root, i)


def shared_fs(fs_by_arm):
    """Both models are fitted on the same FS5 examples (the shared fit): -> the ids, or refuse."""
    ids = {a: [r["i"] for r in rows] for a, rows in fs_by_arm.items()}
    first = next(iter(ids.values()))
    if any(v != first for v in ids.values()):
        raise SystemExit(f"the arms' FS5 sets differ: {[(a, len(v)) for a, v in ids.items()]}")
    return first


def encode_for(arm):
    """The arm's label encoding: today's (`song_model.encode`) or the full space's (with the amp index)."""
    from learn import song_model as SM

    if arm == CORE:
        return SM.encode

    def enc(label):
        x = {tuple(k.rsplit("/", 1)): v for k, v in label["settings"].items()}
        return F.encode(x, label["amp"])
    return enc


def cmd_train(args):
    """One F5 run (demucs-venv): D_stem's recipe (augmented) on F5's twins of the arm, early stopping on FS5's; D_F5
    with the full heads, the masked loss and the amp head. D_F5 waits for the positive control."""
    import numpy as np
    import torch

    from learn import direct_stems as DS
    from learn import pretrain_set as PS

    require_t3(args)
    root = V.out_root(args)
    if args.arm not in ARMS or (args.seed not in TRAIN_SEEDS and not args.smoke):
        raise SystemExit(f"--arm in {ARMS}, --seed in {TRAIN_SEEDS}")
    rp = run_path(root, args.arm, args.seed)
    if rp.exists():
        print(f"{rp.name} exists: nothing to do")
        return
    plan = load_plan(root, args.smoke)
    ok, pc = positive_control(root, plan)
    if not ok and not args.smoke:
        raise SystemExit(f"the positive control has not passed: {pc}")
    f5, fs, refused, unbuilt = t3_sets(root, plan)
    if unbuilt and not args.smoke:
        raise SystemExit(f"{len(unbuilt)} F5 or FS5 examples are not built: every run waits for the build")
    ctx = DS.Ctx(quiet=True)
    tr_rows, es_rows = arm_rows(root, ctx, plan, args.arm)
    rows = tr_rows + es_rows
    files = {r["i"]: files_of(root, args.arm, r["i"]) for r in rows}
    tr = np.arange(len(tr_rows))
    es = np.arange(len(tr_rows), len(rows))
    torch.set_num_threads(2)
    dev = torch.device("cpu" if os.environ.get("DS_DEVICE") == "cpu" or not torch.backends.mps.is_available() else "mps")
    data = T.ArmData(rows, files, aug=True, encode=encode_for(args.arm), partner_path=partner_path(root, args.arm))
    kw = {"build": F.build_net, "loss": F.loss_fn} if args.arm == FULL else {}
    print(f"T3 F5 {args.arm} seed {args.seed}: {len(tr)} train, {len(es)} early stopping (FS5), {len(refused)} "
          f"refused in either twin; {dev}", flush=True)
    t0 = time.time()
    for attempt in (1, 2):
        log = []
        data.masked, data.applied = 0, {}
        try:
            net, state, best_ep, best = DS.train_arm(data, tr, es, args.seed, dev, log, DS.MAX_EPOCHS, **kw)
            break
        except PS.StepsSkipped as e:
            print(f"attempt {attempt} aborted: {e}", flush=True)
            if dev.type == "mps":
                torch.mps.empty_cache()
            if attempt == 2:
                raise SystemExit(f"TRAIN FAILED {args.arm} {args.seed}: {e}")
    rp.parent.mkdir(parents=True, exist_ok=True)
    mp = rp.with_suffix(".pt")
    torch.save(state, mp)
    rec = {"plan": T.PLAN, "design": DESIGN, "stage": "T3 F5", "arm": args.arm, "seed": args.seed,
           "labels": "today's 25 (part C)" if args.arm == CORE else "115 (full space, masked; amp head)",
           "model_arm": T.MODEL_ARM, "stem_sep": T.SEP, "train": len(tr), "early_stop": len(es),
           "bands": sorted({r["band"] for r in tr_rows}), "dropped": sorted(refused), "attempts": attempt,
           "epochs_run": len(log), "best_epoch": best_ep, "best_early_stop_loss": best,
           "minutes": round((time.time() - t0) / 60, 1), "augmentations_applied": data.applied, "device": str(dev),
           "model": mp.name, "model_sha256": DS.hashlib_file(mp), "log": log, "smoke": bool(args.smoke),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(rp, rec)
    print(f"TRAIN DONE T3 {args.arm} {args.seed}: best epoch {best_ep} of {len(log)}")
    if best_ep is not None and best_ep >= DS.MAX_EPOCHS - CAP_EDGE:
        print(f"WARNING: best epoch {best_ep} is within {CAP_EDGE} of the cap {DS.MAX_EPOCHS}: extend this run "
              "before it is read (report marks the reading incomplete)")


def load_models(root, arm, smoke=False):
    import torch

    from learn import pretrain_set as PS

    nets, recs = [], []
    for s in TRAIN_SEEDS:
        rec = _load(run_path(root, arm, s))
        if not rec or (rec.get("smoke") and not smoke):
            raise SystemExit(f"{arm} seed {s} has no run")
        net = F.build_net() if arm == FULL else PS.build_net()
        net.load_state_dict(torch.load(run_path(root, arm, s).with_suffix(".pt"), map_location="cpu"))
        net.eval()
        nets.append(net)
        recs.append(rec)
    return nets, recs


def fs_tensors(rows, files, encode):
    """(X, C, Y, who) over both halves of rows from their feature files (D_stem's inputs, as `data_cleaning.
    stem_tensors`), Y by the arm's encoding."""
    import numpy as np

    from learn import direct_stems as DS

    X, C, Y, who = [], [], [], []
    for r in rows:
        mp, sp = files[r["i"]]
        dm, ds = np.load(mp), np.load(sp)
        for k, h in enumerate("AB"):
            x, c = DS.model_input(ds[f"s{h}"], dm[f"m{h}"], float(ds["lufs"][k]), float(dm["lufs"][k]), h,
                                  r["amp"], r["base"], T.MODEL_ARM)
            X.append(x), C.append(c), Y.append(encode(r["label"])), who.append(r["i"])
    return np.stack(X).astype(np.float32), np.stack(C), [np.stack(z) for z in zip(*Y)], who


def family_masks():
    """{family: continuous mask over the full layout} for E per family (today's space included)."""
    import numpy as np

    D = F.by_name()
    fam = {c.path: c.family for c in F.learned_controls()}
    out = {"today": np.array([n in F.TODAY for n in F.CONT])}
    for k, fs in F.FAMILIES.items():
        out[k] = np.array([fam.get((D[n].module, D[n].key)) in fs for n in F.CONT])
    return out


def family_e(ans, lab, cell_of, med, table, masks):
    """{family: {i: E}} of the pulled answer over the family's sounding continuous dims (None where none sounds)."""
    import numpy as np

    from learn import direct_stems as DS

    out = {k: {} for k in masks}
    for i, a in ans.items():
        c, cm = lab[i]
        b, _ = DS.cell_b(table, cell_of[i], cm) if table is not None else (np.zeros(len(a)), 0)
        th = DS.pull(a, med[cell_of[i]], b) if table is not None else np.asarray(a)
        th = np.asarray(th, np.float64)
        for k, fm in masks.items():
            m = (np.asarray(cm) > 0) & fm & np.isfinite(th)
            if m.any():
                out[k][i] = float(np.abs(np.asarray(th, np.float64) - np.asarray(c, np.float64))[m].mean())
    return out


def cmd_fit(args):
    """Per model (zero renders): the constant (its training labels: medians over sounding labels per amp and class,
    switch majority, mic mode) and amendment 5's pull, fitted on FS5 in the model's own twins (the same sections and
    examples for both), with b refitted on FS5's two section folds (printed, descriptive); E on FS per family, D_F5
    against its constant (section-clustered), pulled and A1 + A2."""
    import numpy as np

    from learn import data_cleaning as DC
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import song_model as SM

    require_t3(args)
    root = V.out_root(args)
    plan = load_plan(root, args.smoke)
    ctx = DS.Ctx(quiet=True)
    out = {"plan": T.PLAN, "design": DESIGN, "stage": "T3 F5 fit", "readout_rule": DS.READOUT_RULE + " (T3's)",
           "models": {}}
    rows_of_arm = {arm: arm_rows(root, ctx, plan, arm) for arm in ARMS}
    out["fs5_ids"] = shared_fs({a: v[1] for a, v in rows_of_arm.items()})
    for arm in ARMS:
        nets, recs = load_models(root, arm, args.smoke)
        tr_rows, fs_rows = rows_of_arm[arm]
        files = {r["i"]: files_of(root, arm, r["i"]) for r in tr_rows + fs_rows}
        enc = encode_for(arm) if arm == FULL else DS.encode_audible
        enc6 = (lambda lab: enc(lab)[:6]) if arm == FULL else enc
        med = DS.label_medians(tr_rows, enc6)
        const = G.constant_answers(tr_rows, enc6, len(F.CONT if arm == FULL else SM.CONT),
                                   len(F.SW if arm == FULL else SM.SW), len(F.CAT if arm == FULL else SM.CAT))
        cell_of = {r["i"]: (r["amp"], r["base"]) for r in fs_rows}
        section_of = {r["i"]: r["section"] for r in fs_rows}
        X, C, Y, who = fs_tensors(fs_rows, files, enc6)        # D_core5: amendment 5's silent masks (T2's)
        outs = F.run_nets(nets, X, C)
        _, ans = DS.median_answers(outs, who)
        lab = DS.labels_of(who, Y)
        table = DS.fit_pull_table(ans, lab, cell_of, med)
        folds = DS.section_folds(fs_rows)
        fold_tables = {f: DS.fit_pull_table({i: a for i, a in ans.items() if folds[i] == f}, lab, cell_of, med)
                       for f in (0, 1)}
        ent = {"models": {str(r["seed"]): r["model_sha256"] for r in recs}, "constant": DS.medians_json(med),
               "constant_answers": G.const_json(const), "pull": DS.table_json(table),
               "pull_summary": DS.pull_summary(table),
               "pull_folds": {str(f): DS.pull_summary(t) for f, t in fold_tables.items()},
               "fs5_examples": len(fs_rows), "fs5_sections": len(set(section_of.values())),
               "train_bands": sorted({r["band"] for r in tr_rows})}
        print(f"{arm}: pull {ent['pull_summary']}; folds {ent['pull_folds']}", flush=True)
        if arm == FULL:
            fm = family_masks()
            e_model = family_e(ans, lab, cell_of, med, table, fm)
            e_a1a2 = family_e(ans, lab, cell_of, med, None, fm)
            e_const = family_e({i: med[cell_of[i]] for i in ans}, lab, cell_of, med, None, fm)
            ent["e_on_fs"] = {k: {"pulled - constant": DC.section_interval(e_model[k], e_const[k], section_of, list(ans)),
                                  "A1+A2 - constant": DC.section_interval(e_a1a2[k], e_const[k], section_of, list(ans)),
                                  "examples": len(e_model[k])} for k in fm}
            amp_of = {r["i"]: r["amp"] for r in fs_rows}
            amp_acc = [float(int(np.argmax(np.mean([F._softmax(o[n][5]) for o in outs], axis=0))) == F.AMPS.index(amp_of[i]))
                       for n, i in enumerate(who)]
            ent["amp_head_fs_accuracy"] = float(np.mean(amp_acc)) if amp_acc else None
            for k, v in ent["e_on_fs"].items():
                print(f"  E on FS {k}: pulled - constant {v['pulled - constant']}", flush=True)
        out["models"][arm] = ent
    out["output_gain_fit"] = F.OUTPUT_FIT_STATUS
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save(T.stage_root(root, STAGE) / "fit.json", out)
    print("FIT DONE t3")


# --- V-real (predict: demucs-venv, zero renders; render: MAIN) --------------------------------------------------

def crops_root(root):
    return T.stage_root(root, STAGE) / "vreal" / "crops"


def crops_manifest_path(root):
    return crops_root(root) / "manifest.json"


def recut_window(tr, slug):
    """A recovered target's ear-verified re-cut window from T0's lists (the window re-check, PR #296): the re-check's
    `crop_window_s`, its target verified and recovered, the window heard. -> ([start, end] or None, why)."""
    t = (tr.get("targets") or {}).get(slug) or {}
    rc = t.get("recheck") or {}
    w = rc.get("crop_window_s")
    if slug not in (tr.get("recovered_targets") or []) or not rc.get("recovered"):
        return None, "not a recovered target in T0's lists"
    if t.get("verdict") != "verified" or rc.get("verdict") != "verified" or not w:
        return None, f"its re-check is not verified ({rc.get('verdict')})"
    if not (rc.get("heard") or {}).get(str(float(w[0]))):
        return None, f"its re-cut window {w} was not heard"
    return [float(w[0]), float(w[1])], "ear-verified re-cut window"


def crop_jobs(members, pool):
    """The frozen members stage F has no crop for: T3 cuts their crops (`vreal-crops`)."""
    return [m for m in members if m not in set(pool)]


def vreal_parts(members, pool, crops, drop_missing=False):
    """V-real's parts: stage F's crops for its pool, T3's own crops for the rest. crops: the vreal-crops manifest's
    entries. A member whose crop did not build under T0's rules is dropped before any read (printed); a member with
    no crop attempt refuses, unless `drop_missing` (an opt-in escape) drops it too.
    -> ({slug: {"kind": "stagef"} | {"kind": "t3", **entry}}, [(dropped member, why)])."""
    parts, dropped, missing = {}, [], []
    for m in members:
        e = crops.get(m) or {}
        if m in set(pool):
            parts[m] = {"kind": "stagef"}
        elif e.get("status") == "built":
            parts[m] = {"kind": "t3", **e}
        elif e.get("status") == "dropped":
            dropped.append((m, f"its crop did not build: {e.get('why')}"))
        else:
            missing.append(m)
    if missing and not drop_missing:
        raise SystemExit(f"frozen V-real members without a crop: {missing} (run `vreal-crops --stage t3`; "
                         "--drop-missing-crops drops them instead, an opt-in escape)")
    return parts, dropped + [(m, "no crop (dropped by --drop-missing-crops)") for m in missing]


def vreal_dirs(root, plan, drop_missing=False):
    """V-real's directions on the frozen members (stage F's, then T3's crops on every amp and direction).
    -> (dirs, {slug: part info}, dropped members)."""
    from learn import arm_a_mega53 as A
    from learn import knob_ceiling as K

    crops = (_load(crops_manifest_path(root)) or {}).get("crops") or {}
    parts, dropped = vreal_parts(plan["vreal"]["members"], A.pool_slugs(), crops, drop_missing)
    for m, why in dropped:
        print(f"V-real member dropped before any read: {m} ({why})", flush=True)
    dirs = [d for d in A.stage_dirs("F") if d[0] in parts]
    dirs += [(s, a, sh, h) for s in sorted(p for p, v in parts.items() if v["kind"] == "t3")
             for a in K.AMPS for sh, h in K.DIRECTIONS]
    return dirs, parts, [m for m, _ in dropped]


def crop_stem(info):
    """A T3 crop's stored xlance_g stem, hash-checked."""
    import numpy as np

    from learn import direct_stems as DS

    st = info["stem"]
    if DS.hashlib_file(st["path"]) != st["sha256"]:
        raise SystemExit(f"{st['path']}: the stored stem changed since it was recorded")
    return np.load(st["path"]).astype(np.float64)


def part_info(slug, info):
    """(gain class, band) of a V-real part: stage F's label table, or the T3 crop's entry."""
    from learn import arm_a_mega53 as A

    if info["kind"] == "stagef":
        p = A.f_part(slug)
        return p["gain_class"], p["band"]
    return info["gain_class"], info["band"]


def cmd_vreal_crops(args):
    """The stage-F-style crops of the frozen V-real members stage F has none for (msst-venv; no render): the session's
    unity sum, the DI and the amp track cut on the member's ear-verified re-cut window (T0's re-check,
    `recut_window`; it must be the window frozen in the plan) by the validation-crop builder's `window` rule, into
    t3/vreal/crops/<slug>/ (the same files and record as stage F's crops; no existing crop is touched), and its
    crop-only xlance_g stem as step 4 made stage F's (gtr_mss on the crop's mix alone). The judge lag is the label
    table's for the same DI and amp track. A crop that does not build is recorded as dropped (before any V-real
    read). Recorded crops are kept, hash-checked."""
    import sys

    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR
    from learn import direct_stems as DS

    require_t3(args)
    root = V.out_root(args)
    plan = load_plan(root, args.smoke)
    tr = T.load_lists(root, args.smoke)
    sys.path.insert(0, str(V.PLUGIN_ROOT / "research"))
    import build_validation_crops as BVC

    mp = crops_manifest_path(root)
    man = _load(mp) or {"plan": T.PLAN, "design": DESIGN, "separator": T.SEP, "setting": "gtr_mss", "crops": {}}
    for slug, e in man["crops"].items():
        if e.get("status") == "built":
            if DS.hashlib_file(pathlib.Path(e["crop"]) / "record.json") != e["record_sha256"]:
                raise SystemExit(f"{slug}: its crop record changed since it was recorded")
            crop_stem(e)
    jobs = crop_jobs(plan["vreal"]["members"], A.pool_slugs())
    catalog = json.loads(BVC.CATALOG.read_text())
    sep = None
    for slug in jobs:
        if slug in man["crops"]:
            print(f"{slug}: {man['crops'][slug]['status']} (kept)", flush=True)
            continue
        frozen = (plan["vreal"]["recovered"].get(slug) or {}).get("window_s")
        w, why = recut_window(tr, slug)
        lt = A.lt_parts().get(slug)
        old = _load(pathlib.Path(lt["crop"]) / "record.json") if lt else None
        e = {"status": "dropped", "window_s": w}
        if w is None:
            e["why"] = why
        elif w != frozen:
            e["why"] = f"T0's re-cut window {w} is not the one frozen in the plan ({frozen})"
        elif not lt or not old:
            e["why"] = "no label-table entry (band, class, judge lag) for the part"
        else:
            out = crops_root(root) / slug
            try:
                rec = BVC.build(BVC.CATALOG, pathlib.Path(catalog["root"]).expanduser(), old["source"], old["song"],
                                old["part"], out, rule="window", start_s=w[0])
            except ValueError as err:
                rec, e["why"] = None, f"the crop builder refused: {err}"
            if rec is not None:
                srcs = {k: old["verified_source_sha256"].get(k) for k in rec["verified_source_sha256"]}
                same = all(srcs[k] == v for k, v in rec["verified_source_sha256"].items() if srcs[k] is not None)
                if not same:
                    e["why"] = "the cut read other source files than the label table's crop (its judge lag would not hold)"
                else:
                    if sep is None:
                        sep = DS.stem_separator(T.SEP, args.device)
                    x = CR.mono(out / "mix.wav")
                    st = np.asarray(sep(x), np.float32)
                    if len(st) != len(x) or not np.isfinite(st).all():
                        raise SystemExit(f"{slug}: bad stem")
                    sp = out.parent / f"{slug}.{T.SEP}.npy"
                    np.save(sp.with_suffix(".tmp.npy"), st)
                    sp.with_suffix(".tmp.npy").replace(sp)
                    e = {"status": "built", "crop": str(out), "window_s": w, "record_sha256": DS.hashlib_file(out / "record.json"),
                         "di_activity": rec.get("di_activity"), "reference_lufs": rec["reference_lufs"],
                         "band": lt["band"], "gain_class": lt["gain_class"], "judge_lag": lt["judge_lag"],
                         "stem": {"path": str(sp), "sha256": DS.hashlib_file(sp), "device": args.device}}
        man["crops"][slug] = {**e, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
        _save(mp, man)
        print(f"{slug}: {e['status']}" + (f" ({e['why']})" if e.get("why") else f", window {w} s"), flush=True)
    print(f"VREAL CROPS DONE t3: {sum(1 for e in man['crops'].values() if e['status'] == 'built')} built, "
          f"{sum(1 for e in man['crops'].values() if e['status'] == 'dropped')} dropped")


def core_answer(amp, S, r, med, b, seed=None):
    """D_core5's answer (T2's settings on S's today's space), from the T3 readout: pulled (b not None) A1 + A2, or one
    seed's A1; switches by the mean probability, mics by the mean's argmax."""
    import numpy as np

    from learn import direct_stems as DS

    a = r["a2"] if seed is None else r["a1"][seed]
    sw = r["sw_p"] if seed is None else r["sw_p_seed"][seed]
    mics = r["mics"] if seed is None else r["mics_seed"][seed]
    cont = DS.pull(a, med, b) if b is not None else np.asarray(a)
    return DS.settings_from(amp, S, cont, np.asarray(sw) > 0.5, mics)


def full_answer(amp, S, r, med, b, seed=None, at_S=()):
    from learn import direct_stems as DS

    a = r["a2"] if seed is None else r["a1"][seed]
    sw = r["sw_p"] if seed is None else r["sw_p_seed"][seed]
    mics = r["mics"] if seed is None else r["mics_seed"][seed]
    cont = DS.pull(a, med, b) if b is not None else a
    return F.answer_settings(amp, S, cont, sw, mics, at_S)


def constant_full(amp, S, c):
    """The full constant as an answer: medians, switch majorities (None -> S's), mic modes."""
    sw = [None if v is None else (1.0 if v else 0.0) for v in c["sw"]]
    return F.answer_settings(amp, S, c["cont"], sw, c["mics"])


def cmd_vreal_predict(args):
    """F5's answer sets on V-real (zero renders): step 4's inputs path (the stored crop and its xlance_g stem, one
    gain to the training median), the search half; per direction D_F5 and D_core5 pulled (their FS5 fit), without
    the pull, each seed alone, D_F5's constant, and D_F5 with each family at S; D_F5's own amp (its amp head)
    recorded. Output gain stays S's here and is fitted at render."""
    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import local_objective as LO

    require_t3(args)
    root = V.out_root(args)
    plan = load_plan(root, args.smoke)
    dirs, parts, dropped = vreal_dirs(root, plan, args.drop_missing_crops)
    fit = _load(T.stage_root(root, STAGE) / "fit.json")
    if not fit:
        raise SystemExit("run `fit --stage t3` first")
    man = DS._load(DS.stems_manifest_path(DS.ROOT, T.SEP))
    target = json.loads(DE.LEVELS.read_text())["summary"]["eval_mix_lufs_median"]
    ms = A.L.menu_S()
    models, fits, preds, own, inputs, gaps = {}, {}, {a: {} for a in ANSWERS}, {}, {}, {}
    for arm in ARMS:
        nets, recs = load_models(root, arm, args.smoke)
        f = fit["models"][arm]
        if f["models"] != {str(r["seed"]): r["model_sha256"] for r in recs}:
            raise SystemExit(f"{arm}: the fit was made with other models")
        models[arm] = (nets, f["models"])
        fits[arm] = (DS.medians_from_json(f["constant"]), DS.table_from_json(f["pull"]),
                     G.const_from_json(f["constant_answers"]))
    for slug, amp, search, held in dirs:
        cls, _ = part_info(slug, parts[slug])
        if slug not in inputs and parts[slug]["kind"] == "stagef":
            mix, _, hashes = DE.f_inputs(slug, "mega53")
            cf = DS.stored_stem(man, f"stagef/{slug}")
            inputs[slug] = {"mix": mix, "stem": cf, "gain_db": DE.inference_gain_db(mix, target),
                            "hashes": {"context": hashes["context"], "stem": man["stems"][f"stagef/{slug}"]["sha256"]}}
        elif slug not in inputs:                            # T3's own crop: its mix.wav and crop-only stem
            from learn import confirm_run as CR

            info = parts[slug]
            mix = CR.mono(pathlib.Path(info["crop"]) / "mix.wav")
            inputs[slug] = {"mix": mix, "stem": crop_stem(info), "gain_db": DE.inference_gain_db(mix, target),
                            "hashes": {"crop_record": info["record_sha256"], "stem": info["stem"]["sha256"]}}
        it = inputs[slug]
        s8, m8, ls, lm = DS.step4_half(it["stem"], it["mix"], search, it["gain_db"])
        x, c = DS.model_input(s8, m8, ls, lm, search, amp, cls, T.MODEL_ARM)
        _, S = ms[amp][cls]
        key = f"{slug}|{amp}|{search}"
        for arm in ARMS:
            nets, _ = models[arm]
            med, table, const = fits[arm]
            mask = F.cell_masks(amp)[0] if arm == FULL else DS.masks(amp, cls)[0]
            b, gap = DS.cell_b(table, (amp, cls), mask)
            if gap:                                     # cell_b's rule: no FS5 example sounds it -> b = 0 (the constant)
                gaps[f"{arm}|{amp}|{cls}"] = gap
            r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
            ans = full_answer if arm == FULL else core_answer
            m = med[(amp, cls)]
            diag = {"a2": [float(v) for v in r["a2"]], "sw_p": [float(v) for v in r["sw_p"]], "mics": r["mics"]}
            preds[arm][key] = {"settings": LO.sdict(ans(amp, S, r, m, b)), "held": held, "diag": diag}
            preds[f"{arm}:nopull"][key] = {"settings": LO.sdict(ans(amp, S, r, m, None)), "held": held}
            for k, s in enumerate(TRAIN_SEEDS):
                preds[f"{arm}:s{s}"][key] = {"settings": LO.sdict(ans(amp, S, r, m, b, seed=k)), "held": held}
            if arm == FULL:
                own[f"{slug}|{search}"] = {"amp": r["amp"], "p": r["amp_p"]}
                for fam in F.FAMILIES:
                    preds[f"{FULL}:at-S:{fam}"][key] = {"settings": LO.sdict(full_answer(amp, S, r, m, b, at_S=(fam,))),
                                                        "held": held}
                preds[CONST][key] = {"settings": LO.sdict(constant_full(amp, S, const[(amp, cls)])), "held": held}
    pp = T.stage_root(root, STAGE) / "vreal" / "predictions.json"
    prev = _load(pp)
    if prev and prev.get("models") != {a: m for a, (_, m) in models.items()} and \
            any((T.stage_root(root, STAGE) / "vreal" / "groups").glob("*.json")):
        raise SystemExit("V-real was rendered from other models' predictions: move t3/vreal aside first")
    _save(pp, {"plan": T.PLAN, "design": DESIGN, "smoke": bool(args.smoke), "members": plan["vreal"]["members"],
               "dropped_members": dropped, "t3_crops": sorted(p for p, v in parts.items() if v["kind"] == "t3"), "directions": len(dirs), "answers": list(ANSWERS), "predictions": preds,
               "own_amp": own, "pull_gaps": gaps, "inputs": {s: v["hashes"] for s, v in inputs.items()},
               "models": {a: m for a, (_, m) in models.items()}, "output_gain": "S's here; fitted per answer at render ("
               + F.OUTPUT_FIT_STATUS + ")", "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"VREAL PREDICT t3: {len(dirs)} directions x {len(ANSWERS)} answer sets"
          + (f"; dropped members {dropped}" if dropped else "")
          + (f"; dims with no fitted pull (read at the constant) {gaps}" if gaps else ""))


def half_lufs(y, half):
    """A half's LUFS (the judge's halves, 1.0-5.5 s and 5.5-10 s) of a 48-kHz signal."""
    from learn import direct_existing as DE

    a, b = V.HALVES[half]
    return T.lufs_or_none(DE.mono(y)[int(a * T.SR):int(b * T.SR)])     # None when silent (at or under -69 LUFS)


def lufs_check(gain_now, render, stem, ref, search, held):
    """The output-gain fit on one direction (confirmed by the user 2026-10-26): the gain that brings the render's
    search half to the stem's search-half loudness; the |LUFS error| of the gained render's held half against the
    amp track's (a pipeline check). -> dict."""
    rs, rh, ss, fh = (half_lufs(render, search), half_lufs(render, held), half_lufs(stem, search), half_lufs(ref, held))
    if None in (rs, rh, ss, fh):
        return {"abs_error_db": None, "why": "a silent half"}
    g, clamped = F.output_gain_fit(gain_now, rs, ss)
    pred = rh + (g - gain_now)
    return {"gain_db": g, "clamped": clamped, "render_search": rs, "stem_search": ss, "pred_held": pred,
            "amp_track_held": fh, "abs_error_db": abs(pred - fh)}


def t3_group_ctx(menu, ms, info, amp):
    """`arm_a_mega53.group_ctx` for a T3 crop: S of the part's class on the amp, the crop's measure DI (as stage F's:
    `knob_ceiling.measure_di`), its amp track as the reference, the label table's judge lag."""
    from learn import confirm_run as CR
    from learn import knob_ceiling as K

    crop = pathlib.Path(info["crop"])
    cls = info["gain_class"]
    sel, S = menu[amp][K.START[cls][amp]]
    di = K.measure_di({"crop": crop})
    part = {"gain_class": cls, "band": info["band"], "judge_lag": info["judge_lag"], "crop": crop}
    return {"part": part, "sel": sel, "S": S, "S_stored": ms[amp][cls][1], "di": di, "di32": di.astype("float32"),
            "ref": CR.mono(crop / "reference.wav")}


def t3_units(parts, groups_dir):
    """Report units for T3's crops (as `perfect_sep_arm.build_units` gives stage F's): every amp and direction, S's
    held-half distance from the group's own S render (None until rendered)."""
    from learn import knob_ceiling as K

    out = []
    for slug in sorted(p for p, v in parts.items() if v["kind"] == "t3"):
        for amp in K.AMPS:
            gr = _load(groups_dir / f"{slug}|{amp}.json") or {}
            for sh, h in K.DIRECTIONS:
                s = ((gr.get("judge") or {}).get(f"S|{sh}") or {}).get(h) if gr.get("status") == "done" else None
                out.append({"slug": slug, "band": parts[slug]["band"], "cls": parts[slug]["gain_class"], "amp": amp,
                            "search": sh, "held": h, "d": {"S": s}, "rec": {}})
    return out


def cmd_vreal_render(args):
    """F5's V-real renders for one shard of (part, amp) groups: one discarded priming render at S, then each answer
    set once per direction through the part's measure DI, judged on both halves (`direct_stems.run_group`); each
    render's output gain fitted to the stem's loudness and its |LUFS error| recorded. isolate=True; at most 3 render
    processes machine-wide; a done group is kept."""
    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    require_t3(args)
    root = V.out_root(args)
    plan = load_plan(root, args.smoke)
    od = T.stage_root(root, STAGE) / "vreal"
    pred = _load(od / "predictions.json")
    if not pred or (pred.get("smoke") and not args.smoke):
        raise SystemExit("run `vreal-predict --stage t3` first")
    if pred["members"] != plan["vreal"]["members"]:
        raise SystemExit("the predictions were made for another V-real membership")
    dirs, parts, dropped = vreal_dirs(root, plan, bool(pred.get("dropped_members")))
    if sorted(dropped) != sorted(pred.get("dropped_members") or []):
        raise SystemExit("V-real's parts changed since the predictions: rerun vreal-predict")
    man = DS._load(DS.stems_manifest_path(DS.ROOT, T.SEP))
    mine = DE.shard(A.groups(dirs), args.shard)
    LO._wait_cap()
    DS.wait_render_slot()
    rr = A.renderer()
    ms = A.L.menu_S()
    try:
        menu = rr.menu()
        for slug, amp in mine:
            gp = od / "groups" / f"{slug}|{amp}.json"
            if (_load(gp) or {}).get("status") == "done":
                continue
            info = parts[slug]
            ctx = A.group_ctx(menu, ms, "F", slug, amp) if info["kind"] == "stagef" else t3_group_ctx(menu, ms, info, amp)
            if K.key(dict(ctx["S"])) != K.key(ctx["S_stored"]):
                raise SystemExit(f"{amp}: the live S differs from the stored copy")
            g = {"sel": ctx["sel"], "S": ctx["S"], "di": ctx["di"], "di32": ctx["di32"], "ref": ctx["ref"],
                 "lag": ctx["part"]["judge_lag"]}
            stem = DS.stored_stem(man, f"stagef/{slug}") if info["kind"] == "stagef" else crop_stem(info)
            settings = {a: {sh: LO.tdict(pred["predictions"][a][f"{slug}|{amp}|{sh}"]["settings"]) for sh, _ in K.DIRECTIONS}
                        for a in ANSWERS}
            arms = ANSWERS
            if info["kind"] == "t3":                        # a new crop has no stored S: S is rendered here (6 a part)
                settings["S"] = {sh: dict(g["S"]) for sh, _ in K.DIRECTIONS}
                arms = ("S",) + ANSWERS
            held_of = dict(K.DIRECTIONS)
            checks = {}

            def keep(arm, search, y, settings=settings, stem=stem, ref=g["ref"], checks=checks):
                gain = float(settings[arm][search].get(F.OUTPUT, "0"))
                checks[f"{arm}|{search}"] = lufs_check(gain, y, stem, ref, search, held_of[search])

            rec = DS.run_group(rr, g, settings, False, None, K.judge, keep=keep, arms=arms)
            rec.update(slug=slug, amp=amp, lufs=checks, output_gain_fit=F.OUTPUT_FIT_STATUS)
            _save(gp, rec)
            print(slug, amp, rec["renders"], flush=True)
    finally:
        rr.close()
    print(f"VREAL RENDER DONE {args.shard[0]}/{args.shard[1]}; renders {rr.count}")


# --- report ------------------------------------------------------------------------------------------------------

def cmd_report(args):
    """F5's report: every declared F5 row, effect sizes with 90% band-clustered intervals (band-weighted), per class
    and V-real-10 beside; the gate D_F5 - D_core5 with both per-seed pairs and their sign split over bands, and the
    no-pull pair; each model against S, D_F5 against its constant; D_core5 against T2's stored SYN; the families;
    the output-gain fit's |LUFS error| (a pipeline check); E on FS per family; the bands each arm trained on."""
    from learn import arm_a_mega53 as A
    from learn import direct_stems as DS
    from learn import perfect_sep_arm as P

    require_t3(args)
    root = V.out_root(args)
    plan = load_plan(root, args.smoke)
    od = T.stage_root(root, STAGE) / "vreal"
    pred = _load(od / "predictions.json") or {}
    members = set(plan["vreal"]["members"]) - set(pred.get("dropped_members") or [])
    v10 = set(plan["vreal"]["v_real_10"])
    crops = (_load(crops_manifest_path(root)) or {}).get("crops") or {}
    parts, _ = vreal_parts(sorted(members), A.pool_slugs(), crops, drop_missing=True)
    units = [u for u in P.build_units() if u["slug"] in members] + t3_units(parts, od / "groups")
    groups, t2g = {}, {}

    def value(arm):
        def f(u):
            k = (u["slug"], u["amp"])
            if arm == D_SYN:
                if k not in t2g:
                    t2g[k] = _load(T.stage_root(root, "t2") / "vreal" / "groups" / f"{u['slug']}|{u['amp']}.json") or {}
                return T.group_value(t2g[k], {}, "SYN", u["search"], u["held"])
            if k not in groups:
                groups[k] = _load(od / "groups" / f"{u['slug']}|{u['amp']}.json") or {}
            gr = groups[k]
            if gr.get("status") != "done":
                return None
            return ((gr.get("judge") or {}).get(f"{arm}|{u['search']}") or {}).get(u["held"])
        return f

    refused = {a: DS.add_step4_arm(units, a, value(a)) for a in ANSWERS + (D_SYN,)}
    gaps = [f"{n} directions have no {a} value" for a in ANSWERS
            if (n := sum(1 for u in units if u["d"].get(a) is None))]
    bad = {a: n for a, n in refused.items() if n and a != D_SYN}
    if bad:
        gaps.append(f"refused answers scored as S {bad}: declare their scoring before reading")
    recs = [_load(run_path(root, a, s)) or {} for a in ARMS for s in TRAIN_SEEDS]
    cap = runs_at_cap(recs, DS.MAX_EPOCHS)
    if cap:
        gaps.append(f"runs within {CAP_EDGE} epochs of the cap (extend before reading): {cap}")
    rows_ = ("all", "v_real_10")
    filt = {"all": lambda u: True, "v_real_10": lambda u: u["slug"] in v10}
    con = {name: DS.step4_contrast(units, a, b, filt, rows=rows_, fixed=("S",)) for name, (a, b) in contrasts().items()}
    gate = (con[f"{FULL} - {CORE} (the gate)"]["rows"].get("all") or {}).get("all") or {}
    lufs = {}
    for gr in groups.values():
        for k, v in (gr.get("lufs") or {}).items():
            lufs.setdefault(k.split("|")[0], []).append(v)
    fit = _load(T.stage_root(root, STAGE) / "fit.json") or {}
    _, pc = positive_control(root, plan)
    rep = {"plan": T.PLAN, "design": DESIGN, "stage": "T3 F5", "v_real": sorted(members),
           "dropped_members": pred.get("dropped_members") or [], "directions": len(units),
           "refused_scored_as_S": refused, "complete": not gaps, "incomplete_because": gaps, "positive_control": pc,
           "contrasts": con, "gate": {"row": gate, "reading": rule_reading(gate) if not gaps else "incomplete",
                                      "next": gate_next(gate) if not gaps else "incomplete: no decision"},
           "output_gain_fit": {"status": F.OUTPUT_FIT_STATUS, "abs_lufs_error": {a: lufs_summary(v) for a, v in lufs.items()}},
           "e_on_fs": (fit.get("models") or {}).get(FULL, {}).get("e_on_fs"),
           "pull": {a: {"summary": m.get("pull_summary"), "folds": m.get("pull_folds")} for a, m in (fit.get("models") or {}).items()},
           "bands_per_arm": {r["arm"]: r.get("bands") for r in recs if r},
           "runs": {f"{r['arm']}-{r['seed']}": {"best_epoch": r.get("best_epoch"), "epochs": r.get("epochs_run"),
                                                "train": r.get("train"), "early_stop": r.get("early_stop")} for r in recs if r},
           "own_amp": pred.get("own_amp"), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(T.stage_root(root, STAGE) / "report.json", rep)
    print(f"T3 F5 report: V-real {len(members)} parts ({len(units)} directions); dropped {rep['dropped_members'] or 'none'}")
    print(f"positive control: {pc}")
    for g in gaps:
        print(f"  incomplete: {g}")

    def line(name, row, s):
        sign = f"; bands -/+ {s.get('bands_negative')}/{s.get('bands_positive')}" if s.get("bands") else ""
        print(f"  {name:52s} {row:12s} {s.get('band_weighted_mean')} [{s.get('lo90')}, {s.get('hi90')}] "
              f"({s.get('bands')} bands{sign}) {rule_reading(s)}")

    for name, c in con.items():
        for row in rows_:
            r = (c["rows"].get(row) or {})
            line(name, row, r.get("all") or {})
            for cls, s in sorted((r.get("per_class") or {}).items()):
                line("", f"{row} {cls}", s)
    print("the output-gain fit's |LUFS error| (a pipeline check, " + F.OUTPUT_FIT_STATUS + "):")
    for a, s in sorted(rep["output_gain_fit"]["abs_lufs_error"].items()):
        print(f"  {a:28s} {s}")
    print("E on FS5 per family, D_F5 against its constant (section-clustered, zero renders):")
    for k, v in (rep["e_on_fs"] or {}).items():
        print(f"  {k:24s} pulled - constant {v.get('pulled - constant')}; A1+A2 - constant {v.get('A1+A2 - constant')}")
    print(f"the pull: {rep['pull']}")
    print(f"bands per arm: {rep['bands_per_arm']}")
    print(f"T3 F5 GATE ({FULL} - {CORE}): {rep['gate']['reading']}; next: {rep['gate']['next']}")
