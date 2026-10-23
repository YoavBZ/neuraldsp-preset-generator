"""The trusted-data plan's self-built mixes, T1 and T2 (`docs/trusted-data-strategy-plan.md`, approved 2026-10-23 with
its recorded decisions; the design in `docs/trusted-data-t0-design.md`). Development data only. Every command here
reads T0's lists (`learn/verify_tracks.py lists`): only verified DIs, targets and stems are used.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    MSST=~/ndsp-presets/tools/msst-venv/bin/python; TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MAIN -m learn.trusted_data plan --stage t1|t2                 # zero renders: examples, draws, other guitars, counts
    $MAIN -u -m learn.trusted_data render --stage t1|t2 --shard k/3   # renders: T2's targets, every other guitar
    $MSST -m learn.trusted_data build --stage t1|t2 --device mps --order asc    # self-built mixes + X-LANCE stems
    $MSST -m learn.trusted_data build --stage t1|t2 --device cpu --order desc   # optional second worker
    $MAIN -m learn.trusted_data t1-read                            # T1: paired K - V_sep stem SNR; V-real beside
    $TORCH_PY -m learn.trusted_data train --arm SES|SYN|SYN-E --seed 20261042|20261043     # T2: 6 runs
    $TORCH_PY -m learn.trusted_data fit                            # per arm: the constant and the pull (early stopping)
    $TORCH_PY -m learn.trusted_data e-on-k                         # E on K per arm (zero renders)
    $TORCH_PY -m learn.trusted_data vreal-predict                  # the arms' answers on V-real (zero renders)
    $MAIN -u -m learn.trusted_data vreal-render --shard k/3        # the answers through the measure DI, judged
    $MAIN -m learn.trusted_data report                             # SYN - SES on V-real (primary) and the rest

**A self-built mix** (plan (c)), deterministic from the example's index; the recipe is stored, the audio is not:
- **The target:** the example's verified DI section through its drawn settings (part C's label, today's space).
  T1's K reuses R_in's stored truth renders; T2 re-renders each example (refused unless its mels match part C's).
- **Other guitars:** the session's other verified DIs that play in the section (at most `MAX_OTHERS`, the most
  active first, against each DI file's own playing level), each through its own preset drawn as part C draws a label
  (seed 20261102 per example and DI); a double of the target (a Cambridge "DT" name, or the cleaning plan's
  same-part rule by pitch in the section) takes the target's settings. A part whose amp tracks are silent in the
  section is left out. Each sits at its own amp track's LUFS in the section; a
  DI-only part at the median LUFS of the session's playing guitar amp tracks (failing that, of its stems). Parts
  with no DI are left out (decision 4: other guitars are DI renders only).
- **Other instruments:** the session's mix tracks that pass T0's stem scan, summed at the session's own balance;
  vocal tracks only when the example's vocal draw says so.
- **Pan:** a declared prior (other guitars uniform in [-1, 1]; a DT double opposite the target; stems centred),
  built with constant-power pans and folded to mono as at inference, (L + R) / 2.
- **Level, loudness, mastering:** the backing against the target at part C's ratio draw (`pretrain_set.mix_params`
  with its stored prior, so SES, SYN and K share the draws), vocals p 0.5, the evaluation median +- 3 dB, and the
  D build's mastering draw (compressor and limiter p 0.5, seed 20261076); all before separation. Controlled bleed
  is off (set by the ML session; the user may overrule). The re-derived level prior (T0) is for T3's new examples; it is stored, not used here.

**T1** (no training): K is R_in's examples outside John Morgan Kimock and Swatkins (set by the ML session: they stay out
of K) whose DIs pass T0, rebuilt with self-built backings and separated by X-LANCE. The read: per example the stem's
SNR on the stored mel grid (levels aligned by the median offset on the render's active cells), K against V_sep's
stored stem of the same example and draws, paired, 90% band-clustered (section-clustered beside); the audit's
contamination beside; V-real's stored crop stems against their amp tracks beside, by guitar-to-backing ratio.

**T2** (the pilot): 5k trusted-pool examples (seed 20261099, stratified by band) outside an early-stopping set of
about 5% of the trusted sections, at least one per band (seed 20261100, at most 1,000 examples). Arms: SES, the stored
session stems (the cleaning manifest's rebuilt files where listed); SYN, self-built backings of the same examples,
labels and draws; SYN-E, SYN with a seeded third (seed 20261101) swapped for Eggy examples whose DIs pass T0. D_stem's
recipe (`direct_stems.train_arm`, augmented), 2 seeds each, early stopping on the set in each arm's own mix type
(SYN-E reads SYN's). Per arm the constant (training-label medians) and amendment 5's pull (fitted on the set).
Reads: SYN - SES on V-real by the judge with the measure DI, paired by direction (primary; a tie under about 0.03
picks SYN, recorded decision 4); SYN-E - SYN; E on K; stem SNR.

The pure parts are unit-tested (`tests/test_trusted_data.py`); the commands that render, separate or train are not,
like the other step modules.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import statistics
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from learn import verify_tracks as V  # noqa: E402

ROOT = V.OUT
PLAN = V.PLAN
SR = 48_000
SEP = "xlance_g"
PILOT_SEED = 20261099
ES_SEED = 20261100
EGGY_SEED = 20261101                   # SYN-E's seeded third (set here; the plan gave none)
OTHER_SEED = 20261102                  # other guitars' presets and every pan (set here)
N_PILOT = 5_000
ES_SHARE = 0.05
ES_CAP = 1_000
EGGY_SHARE = 1 / 3
MAX_OTHERS = 4                         # the plan's "1-4 per example"
ACTIVE_MIN = 0.10                      # an other guitar plays: >= 10% of the section's frames within 40 dB of the
                                       # DI file's loudest frames (not the section's own: a resting floor reads 1.0)
ARMS = ("SES", "SYN", "SYN-E")
TRAIN_SEEDS = (20261042, 20261043)
MODEL_ARM = "Dstem"                    # D_stem's inputs (mix zeroed) and augmentations
TIE = 0.03                             # the plan's power: effects under about 0.03 read as ties
RATIO_BINS = (-15.0, -10.0, -5.0)
EGGY = V.EGGY
K_OUT_BANDS = V.K_OUT_BANDS
DISK_GUARD_GB = 31.0
PAN_PRIOR = {"other_guitar": "uniform [-1, 1]", "dt_double": "opposite the target", "target": "uniform [-1, 1]",
             "stems": "centre"}


# --- pure: the recipe ----------------------------------------------------------------------------------------

def pan_fold(p):
    """The mono gain of a source panned to p in [-1, 1] by the constant-power law, folded as (L + R) / 2."""
    th = (max(-1.0, min(1.0, p)) + 1) * math.pi / 4
    return (math.cos(th) + math.sin(th)) / 2


def seed_rng(*xs):
    from learn import pretrain_set as PS

    return random.Random(PS.seed_int(OTHER_SEED, *xs))


def target_pan(i):
    return seed_rng("pan", int(i), "target").uniform(-1.0, 1.0)


def other_pan(i, di, dt):
    return -target_pan(i) if dt else seed_rng("pan", int(i), di).uniform(-1.0, 1.0)


def other_draw(i, di):
    """An other guitar's preset draw, as part C draws a label: (amp, mode, base) and the rng's seed key; the
    settings are drawn from it with the live menu at render time (`pretrain_set.settings_for`)."""
    from learn import pretrain_set as PS

    rng = seed_rng("preset", int(i), di)
    amp = rng.choice(("pr12", "sw50r", "ac20"))
    mode = PS.mode_of(rng.random())
    base = rng.choice(("clean", "crunch"))
    return {"amp": amp, "mode": mode, "base": base}


def other_settings(i, di, menu):
    """(select, settings) of an other guitar's drawn preset (deterministic from its index and DI)."""
    from learn import knob_ceiling as K
    from learn import pretrain_set as PS

    rng = seed_rng("preset", int(i), di)
    amp = rng.choice(("pr12", "sw50r", "ac20"))
    mode = PS.mode_of(rng.random())
    base = rng.choice(("clean", "crunch"))
    sel, x, _, _ = PS.settings_for(rng, amp, mode, base, menu, K.START, K.space, K.fmt)
    return amp, sel, x


def pick_others(target_di, target_part, candidates, activity, max_n=MAX_OTHERS, active_min=ACTIVE_MIN, doubles=()):
    """The other guitars of one section: trusted DIs of the session other than the target that play (share >=
    active_min), the most active first (name order breaks ties), at most max_n. A double of the target is flagged:
    a DT partner by name, or a DI the cleaning plan's same-part rule confirms by pitch in this section (`doubles`;
    step 0 removed such tracks from SES's backings), so it takes the target's settings, as a DT double does.
    candidates: [di]; activity: {di: share}. -> [{"di", "dt"}]."""
    from learn import data_cleaning as DC

    c = [d for d in candidates if d != target_di and (activity.get(d) or 0.0) >= active_min]
    c.sort(key=lambda d: (-activity[d], d))
    return [{"di": d, "dt": bool(DC.name_partner(target_part, DC.part_base(d)) or DC.name_partner(target_part, d)
                                 or d in doubles)}
            for d in c[:max_n]]


def other_level(own_lufs, session_amp_lufs, stem_lufs, has_own=False):
    """An other guitar's LUFS in the section: its own amp track's; a DI-only part (no amp track: has_own False)
    takes the median of the session's playing guitar amp tracks; failing that, the median of its stems; else None
    (left out). A part whose own amp tracks are silent here is not in the arrangement here: None (left out)."""
    if own_lufs is not None:
        return own_lufs, "own amp track"
    if has_own:
        return None, "own amp tracks silent here"
    if session_amp_lufs:
        return statistics.median(session_amp_lufs), "session amp median"
    if stem_lufs:
        return statistics.median(stem_lufs), "stems median"
    return None, "none"


def stratified_by_band(rows, n, seed):
    """n rows stratified by band: proportional quotas by largest remainder, then a seeded sample per band (bands
    in sorted order). -> rows sorted by index."""
    strata = {}
    for r in sorted(rows, key=lambda r: r["i"]):
        strata.setdefault(r["band"], []).append(r)
    total = sum(len(v) for v in strata.values())
    if n > total:
        raise SystemExit(f"cannot pick {n} of {total}")
    q = {k: n * len(v) / total for k, v in strata.items()}
    base = {k: int(math.floor(v)) for k, v in q.items()}
    for k in sorted(q, key=lambda k: (-(q[k] - base[k]), k))[:n - sum(base.values())]:
        base[k] += 1
    rng = random.Random(seed)
    out = []
    for k in sorted(strata):
        out += rng.sample(strata[k], base[k])
    return sorted(out, key=lambda r: r["i"])


def es_sections(sections_by_band, share=ES_SHARE, seed=ES_SEED):
    """About `share` of each band's trusted sections, at least one per band, seeded. -> sorted section ids."""
    rng = random.Random(seed)
    out = []
    for band in sorted(sections_by_band):
        secs = sorted(sections_by_band[band])
        k = max(1, int(round(share * len(secs))))
        out += rng.sample(secs, min(k, len(secs)))
    return sorted(out)


def eggy_swap(pilot_ids, eggy_rows, share=EGGY_SHARE, seed=EGGY_SEED):
    """SYN-E's composition: a seeded `share` of the pilot's examples replaced by as many Eggy examples (a seeded
    sample). -> (kept pilot ids, swapped-out ids, Eggy ids)."""
    ids = sorted(pilot_ids)
    rng = random.Random(seed)
    n = int(round(share * len(ids)))
    out = sorted(rng.sample(ids, n))
    pool = sorted(r["i"] for r in eggy_rows)
    if len(pool) < n:
        raise SystemExit(f"{len(pool)} verified Eggy examples for a swap of {n}")
    eg = sorted(rng.sample(pool, n))
    gone = set(out)
    return [i for i in ids if i not in gone], out, eg


def mix_gains(lg, lb, draw):
    """The D build's gains for a drawn ratio, leak and target (`pretrain_set.mix_gains_db`). -> (gb, ga)."""
    from learn import pretrain_set as PS

    gb, _, ga = PS.mix_gains_db(lg, lb, draw["ratio_db"], draw["leak_db"], draw["target_lufs"])
    return gb, ga


def ratio_bin(r, edges=RATIO_BINS):
    lo = None
    for e in edges:
        if r < e:
            return f"< {e:+.0f}" if lo is None else f"{lo:+.0f} to {e:+.0f}"
        lo = e
    return f">= {edges[-1]:+.0f}"


def mel_snr(stem_u8, ref_u8, active_db=50.0):
    """Stem SNR on the stored mel grid (dB): the stem's level aligned to the render's by the median dB offset over
    the render's active cells (within active_db of its maximum), then sum(render power) over the summed squared
    magnitude error. None if the render is silent."""
    import numpy as np

    from learn import pretrain_set as PS

    s = PS.dequant(stem_u8).astype(np.float64)
    r = PS.dequant(ref_u8).astype(np.float64)
    act = r > r.max() - active_db
    if not act.any():
        return None
    off = float(np.median(s[act] - r[act]))
    S = 10 ** ((s - off) / 20)
    R = 10 ** (r / 20)
    err = float(np.sum((S - R) ** 2))
    return 10 * math.log10(float(np.sum(R ** 2)) / max(err, 1e-30))


def contamination(stem_u8, ref_u8, active_db=50.0):
    """The data-quality audit's contamination: the share of the level-aligned stem's power above the render."""
    import numpy as np

    from learn import pretrain_set as PS

    s = PS.dequant(stem_u8).astype(np.float64)
    r = PS.dequant(ref_u8).astype(np.float64)
    act = r > r.max() - active_db
    if not act.any():
        return None
    off = float(np.median(s[act] - r[act]))
    S = 10 ** ((s - off) / 10)
    R = 10 ** (r / 10)
    return float(np.sum(np.maximum(S - R, 0)) / max(float(np.sum(S)), 1e-30))


def reading(iv, tie=TIE):
    """The plan's T2 reading of SYN - SES (no pass bar): 'SYN better' below 0, 'SES better' above, a tie when the
    point is within `tie` (a tie picks SYN, recorded decision 4)."""
    if not iv or iv[0] is None:
        return "incomplete"
    m = iv[0]
    if abs(m) < tie:
        return "tie (picks SYN: recorded decision 4)"
    return "SYN better (T3 on self-built mixes)" if m < 0 else "SES better (realism levers at 5k before T3)"


def union_refused(*sets):
    out = set()
    for s in sets:
        out |= set(s)
    return out


# --- I/O ---------------------------------------------------------------------------------------------------------

_save, _load = V._save, V._load


def stage_root(root, stage):
    return root / stage


def plan_path(root, stage):
    return stage_root(root, stage) / "plan.json"


def flac_path(root, stage, i, what):
    return stage_root(root, stage) / "audio" / f"{i // 1000:04d}" / f"{i:07d}-{what}.flac"


def ex_path(root, stage, i, kind):
    from learn import direct_stems as DS

    return DS.ex_path(stage_root(root, stage), i, kind)


def rows_of(root, stage, prefix):
    from learn import direct_stems as DS

    out = {}
    for f in sorted((stage_root(root, stage) / "rows").glob(f"{prefix}-*.jsonl")):
        for r in DS.read_jsonl(f):
            out[r["i"]] = r
    return out


def load_lists(root, smoke=False):
    tr = _load(root / "t0" / "verified.json")
    if not tr or (tr.get("smoke") and not smoke):
        raise SystemExit("T0's lists are missing (run `verify_tracks lists`)")
    if tr.get("thresholds") != V.thresholds() and not smoke:
        raise SystemExit("T0's lists were made under other thresholds (rerun `verify_tracks lists`)")
    if not tr.get("ear_di_files") and not smoke:
        raise SystemExit("T0's lists were made without the sitting-1 export (rerun `verify_tracks lists --ear-di ...`)")
    return tr


def lists_sha(root):
    """The lists' hash, without their run time: a `lists` rerun that changes no verdict keeps it."""
    import hashlib

    tr = _load(root / "t0" / "verified.json") or {}
    body = {k: v for k, v in tr.items() if k != "time"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def stale_rows(old_plan, new_plan, rendered):
    """Examples already rendered whose recipe differs between the old and the new plan: `render` and `build` skip
    any example with a row, so re-planning over them would mix the old recipe's audio into the new plan."""
    if not old_plan:
        return []
    old = {x["i"]: x for x in old_plan.get("examples") or []}
    return sorted(x["i"] for x in new_plan["examples"] if x["i"] in rendered and old.get(x["i"]) != x)


def check_lists(root, plan, smoke=False):
    """Refuse a plan made from other T0 lists than the current verified.json (stale results never run)."""
    if not plan.get("lists_sha256") or plan["lists_sha256"] != lists_sha(root):
        if smoke:
            print("smoke: T0's lists changed since the plan", flush=True)
            return
        raise SystemExit("T0's verified.json changed since this plan was made: rerun `plan` (and what follows)")


def verified_dis(tr):
    """The DIs T0 trusts (pending-ear and excluded DIs are out)."""
    return {d for d, v in tr["dis"].items() if v["verdict"] == "verified"}


def windows_of(tr):
    """{di: {window id: 'usable' | 'pending ear' | 'excluded' | 'silent'}} of every window T0 measured."""
    return {d: v.get("sections") or {} for d, v in tr["dis"].items()}


def unusable(tr):
    """Sections T0 does not let any mix use: excluded, or waiting for the ear (D4 flags, pending DIs)."""
    return set(tr.get("unusable_sections") or [])


# --- plan (zero renders) -----------------------------------------------------------------------------------------

def section_activity(path, start_s, sr=SR, files=None):
    """The share of a DI's 10-s section frames that play: within 40 dB of the DI file's loudest frames
    (`clean_di.playing` over the whole file, as part A reads a DI), so a resting section's noise floor reads near 0.
    files: a cache {path: (frame dB, playing)} across calls."""
    import numpy as np

    from learn import clean_di as CD
    from learn import pretrain_set as PS

    files = {} if files is None else files
    if str(path) not in files:
        fdb = CD.frame_db(PS.load_mono(path, PS.SR))
        files[str(path)] = (fdb, CD.playing(fdb))
    fdb, play = files[str(path)]
    r = CD.frames_in(int(round(start_s * PS.SR)), int(round((start_s + PS.SEC_S) * PS.SR)), len(play))
    return float(np.mean(play[r.start:r.stop])) if len(r) else 0.0


def same_part_doubles(target_path, others, start_s, target_part):
    """{di}: the other DIs the cleaning plan's same-part rule (`data_cleaning.same_part`: a candidate by name or by
    onsets, confirmed by pitch) finds playing the target's part in this section. others: {di: path}."""
    from learn import data_cleaning as DC
    from learn import pretrain_set as PS

    t = DC.load_window(target_path, start_s, start_s + PS.SEC_S)
    t_on, t_ch = DC.onset_env(t), DC.chroma(t)
    out = set()
    for d, path in sorted(others.items()):
        y = DC.load_window(path, start_s, start_s + PS.SEC_S)
        partner = DC.name_partner(target_part, DC.part_base(d)) or DC.name_partner(target_part, d)
        if DC.same_part(DC.chroma_sim(t_ch, DC.chroma(y)), DC.best_corr(t_on, DC.onset_env(y)), None, partner):
            out.add(d)
    return out


def session_dis(ctx, sd, verified):
    """The session's trusted inventory DIs."""
    return sorted(d for d, r in ctx.inv.items() if r.get("session_dir") == sd and d in verified)


def stems_for(rec, verified_stems, sd):
    """(with vocals, without vocals): the session's mix tracks (inventory list, else every file) that are not guitar
    and pass T0's stem scan."""
    from learn import data_cleaning as DC
    from learn import pretrain_set as PS

    ok = set(verified_stems.get(sd) or [])
    names = rec.get("mix") or sorted(ok)
    keep = [f for f in names if f in ok and DC.track_class(f) != "guitar"]
    voc = set(rec.get("vocals") or [])
    v = [f for f in keep if f in voc or (not rec.get("vocals") and PS.is_vocal_name(f))]
    return keep, [f for f in keep if f not in v]


def example_recipe(ctx, r, verified, verified_stems, act_cache, bad_sections=frozenset(), dis_windows=None):
    """One example's self-built recipe (plan (c)), zero renders. r: a part C row; dis_windows: {di: {window id:
    status}} from T0's lists (an other guitar's window must have been measured and be usable)."""
    dis_windows = dis_windows or {}
    from learn import data_cleaning as DC
    from learn import direct_stems as DS
    from learn import pretrain_set as PS

    sec = ctx.sections[r["section"]]
    rec = ctx.inv[sec["di"]]
    sd = rec["session_dir"]
    cands = []
    for d in session_dis(ctx, sd, verified):              # other guitars: only windows T0 measured and found usable
        if d == sec["di"]:
            continue
        w = f"{d}@{float(sec['start_s']):.1f}"
        st = (dis_windows.get(d) or {}).get(w)
        if st is None:
            raise SystemExit(f"{r['i']}: {w} was never measured by T0 (rerun verify_tracks dis and lists)")
        if st == "usable" and w not in bad_sections:
            cands.append(d)
    files = act_cache.setdefault("files", {})
    for d in cands:
        key = (d, float(sec["start_s"]))
        if key not in act_cache:
            act_cache[key] = section_activity(ctx.inv[d]["path"], float(sec["start_s"]), files=files)
    activity = {d: act_cache[(d, float(sec["start_s"]))] for d in cands}
    part = rec.get("part") or DC.part_base(sec["di"])
    dkey = ("doubles", sec["di"], float(sec["start_s"]))
    if dkey not in act_cache:
        act_cache[dkey] = same_part_doubles(rec["path"], {d: ctx.inv[d]["path"] for d in cands},
                                            float(sec["start_s"]), part)
    others = pick_others(sec["di"], part, cands, activity, doubles=act_cache[dkey])
    for o in others:
        o["pan"] = other_pan(r["i"], o["di"], o["dt"])
        o["draw"] = "target" if o["dt"] else other_draw(r["i"], o["di"])
    withv, nov = stems_for(rec, verified_stems, sd)
    meta = json.loads(PS.backing_path(r["section"]).with_suffix(".json").read_text())
    ratio, v, leak, target = PS.mix_params(r["i"], ctx.ratios, meta["has_vocals"], ctx.eval_mix, 0)
    mastered, _ = DS.master_draw(r["i"])
    return {"i": r["i"], "section": r["section"], "band": r["band"], "di": sec["di"], "amp": r["amp"],
            "base": r["base"], "pan_target": target_pan(r["i"]), "others": others,
            "stems": {"v": withv, "n": nov}, "vocals": bool(v and withv != nov),
            "draw": {"ratio_db": ratio, "vocals_drawn": v, "leak_db": leak, "target_lufs": target, "mastered": mastered}}


def ses_rows(ctx):
    """The trusted session pool (the cleaning manifest): the D build's pool examples less the excluded and the
    refused. -> ({i: row}, {i: (mix path, stem path)})."""
    from learn import data_cleaning as DC
    from learn import direct_stems as DS

    man = _load(DC.pool_root(DC.OUT) / "manifest.json")
    if not man or not man.get("complete") or man.get("smoke"):
        raise SystemExit("the cleaning manifest is missing or incomplete (data_cleaning pool-status)")
    excl = {int(i) for i in man["excluded"]}
    rebuilt = {int(i): v for i, v in man["rebuilt"].items()}
    refused = set()
    for part in ("pilot", "rest"):
        for stage in ("mix", SEP):
            refused |= {i for i, m in DS.build_rows(DS.ROOT, part, stage).items() if m.get("refused")}
    rows, files = {}, {}
    for r in ctx.pool:
        i = r["i"]
        if i in excl or i in refused:
            continue
        rows[i] = r
        if i in rebuilt:
            files[i] = (rebuilt[i]["mix"], rebuilt[i]["stem"])
        else:
            files[i] = (str(DS.ex_path(DS.ROOT, i, "mix")), str(DS.ex_path(DS.ROOT, i, SEP)))
    return rows, files


def cmd_plan(args):
    """The examples and their recipes (zero renders, CPU): T1's K, or T2's pilot, early-stopping set and SYN-E swap."""
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS

    V.require_real(args)
    root = V.out_root(args)
    tr = load_lists(root, args.smoke)
    verified = verified_dis(tr)
    wins = windows_of(tr)
    ctx = DS.Ctx(quiet=True)
    act = {}
    if args.stage == "t1":
        truth = G.gate_rows(DS.ROOT / "gate", "truth")
        k_dis = set(tr["k_dis"])
        bad_secs = unusable(tr)
        rows = [r for r in ctx.parts["vsep"] if not ctx.tag[r["i"]] and r["band"] not in K_OUT_BANDS
                and ctx.sections[r["section"]]["di"] in k_dis and r["section"] not in bad_secs
                and r["i"] in truth and not truth[r["i"]].get("refused")]
        rows = rows[:args.limit or None]
        recipes = [example_recipe(ctx, r, verified, tr["stems"], act, bad_secs, wins) for r in rows]
        rec = {"plan": PLAN, "stage": "t1", "smoke": bool(args.smoke), "k_out_bands": list(K_OUT_BANDS),
               "examples": recipes, "renders_others": sum(len(x["others"]) for x in recipes),
               "renders_targets": 0, "separations": len(recipes)}
    else:
        ses, _ = ses_rows(ctx)
        bad_secs = unusable(tr)
        cand = [r for i, r in sorted(ses.items()) if r["band"] != EGGY and ctx.sections[r["section"]]["di"] in verified
                and r["section"] not in bad_secs]
        by_band = {}
        for r in cand:
            by_band.setdefault(r["band"], set()).add(r["section"])
        es_sec = set(es_sections(by_band))
        es = [r for r in cand if r["section"] in es_sec]
        if len(es) > ES_CAP:
            es = sorted(random.Random(ES_SEED).sample(es, ES_CAP), key=lambda r: r["i"])
        left = [r for r in cand if r["section"] not in es_sec]
        print("T2 candidates outside early stopping, by band: "
              + ", ".join(f"{b} {sum(1 for r in left if r['band'] == b)}" for b in sorted({r["band"] for r in left}))
              + f" (total {len(left)}; the pilot needs {N_PILOT})", flush=True)
        pilot = stratified_by_band(left, N_PILOT, PILOT_SEED)
        excluded_secs = unusable(tr)
        eggy = [r for r in ctx.pool if r["band"] == EGGY and not r.get("early_stop")
                and ctx.sections[r["section"]]["di"] in verified and r["section"] not in excluded_secs]
        try:
            kept, out, eg = eggy_swap([r["i"] for r in pilot], eggy)
            syn_e = {"kept": kept, "swapped_out": out, "eggy": eg}
        except SystemExit as e:                     # e.g. every Eggy DI heard processed (2026-10-23): SYN-E cannot run
            syn_e, eg = {"refused": str(e), "kept": [], "swapped_out": [], "eggy": []}, []
        rows_by = {r["i"]: r for r in ctx.pool}
        need = sorted({r["i"] for r in pilot} | {r["i"] for r in es} | set(eg))
        if args.limit:
            need = need[:args.limit]
        recipes = [example_recipe(ctx, rows_by[i], verified, tr["stems"], act, bad_secs, wins) for i in need]
        rec = {"plan": PLAN, "stage": "t2", "smoke": bool(args.smoke), "seeds": {"pilot": PILOT_SEED, "es": ES_SEED,
               "eggy": EGGY_SEED, "others": OTHER_SEED}, "pilot": [r["i"] for r in pilot], "es": [r["i"] for r in es],
               "es_sections": sorted(es_sec), "syn_e": syn_e,
               "bands": {b: sum(1 for r in pilot if r["band"] == b) for b in sorted({r["band"] for r in pilot})},
               "examples": recipes, "renders_targets": len(recipes),
               "renders_others": sum(len(x["others"]) for x in recipes), "separations": len(recipes)}
    rec["pan_prior"] = PAN_PRIOR
    rec["lists_sha256"] = lists_sha(root)
    stale = stale_rows(_load(plan_path(root, args.stage)), rec, rows_of(root, args.stage, "render"))
    if stale:
        raise SystemExit(f"{len(stale)} examples were rendered under another recipe (e.g. {stale[:3]}): move "
                         f"{stage_root(root, args.stage)}/rows and its audio aside before re-planning")
    bare = [x for x in rec["examples"] if not x["others"] and not x["stems"]["v"] and not x["stems"]["n"]]
    if bare:
        print(f"{len(bare)} examples have no other guitar and no stem (build refuses them): by band "
              + ", ".join(f"{b} {sum(1 for x in bare if x['band'] == b)}" for b in sorted({x["band"] for x in bare})))
    rec["max_others"] = MAX_OTHERS
    rec["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save(plan_path(root, args.stage), rec)
    n = len(rec["examples"])
    print(f"{args.stage}: {n} examples; renders {rec['renders_targets']} targets + {rec['renders_others']} other guitars "
          f"(+ priming); separations {rec['separations']}")
    if args.stage == "t2":
        print(f"pilot {len(rec['pilot'])} by band {rec['bands']}; early stopping {len(rec['es'])} examples in "
              f"{len(rec['es_sections'])} sections; SYN-E swaps {len(rec['syn_e']['eggy'])} for Eggy"
              + (f" (SYN-E refused: {rec['syn_e']['refused']})" if rec["syn_e"].get("refused") else ""))


# --- render (MAIN; renders) --------------------------------------------------------------------------------------

def lufs_or_none(x):
    import numpy as np

    from learn import song_aug as SA

    if not np.any(x):
        return None
    v = float(SA.lufs(x))
    return v if math.isfinite(v) and v > -69.0 else None


def section_levels(ctx, sec, others, stems):
    """{di: (LUFS, source)} of a section's other guitars (plan (c)'s level rule)."""
    from learn import clean_di as CD
    from learn import pretrain_set as PS

    rec = ctx.inv[sec["di"]]
    sess = pathlib.Path(rec["session_dir"])
    files = sorted(f.name for f in sess.glob("*.wav"))
    trim = int(PS.TRIM_S * PS.SR)

    def lu(name):
        return lufs_or_none(PS.section_audio(sess / name, sec["start_s"])[trim:])

    amp_tracks = [f for f in V.guitar_sources(files) if not CD.is_guitar_di(f)]
    sess_amp = [v for v in (lu(f) for f in amp_tracks) if v is not None]
    stem_l = [v for v in (lu(f) for f in stems) if v is not None]
    out = {}
    for o in others:
        orec = ctx.inv[o["di"]]
        own = V.own_amp_tracks(orec, files)
        vals = [v for v in (lu(a) for a in own) if v is not None]
        out[o["di"]] = other_level(max(vals) if vals else None, sess_amp, stem_l, has_own=bool(own))
    return out


def cmd_render(args):
    """Renders for one shard of whole sections: T2's targets (re-rendered, refused unless part C's mels match) and
    every other guitar (each scaled to its level, pan-folded, summed per example into one FLAC). isolate=True, a
    priming render on every (DI, amp) change (`direct_stems.Primer`), at most 3 render processes machine-wide."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_bank as B

    V.require_real(args)
    root = V.out_root(args)
    plan = _load(plan_path(root, args.stage))
    if not plan or (plan.get("smoke") and not args.smoke):
        raise SystemExit(f"run `plan --stage {args.stage}` first")
    check_lists(root, plan, args.smoke)
    k, n = args.shard
    shard = DS.shard_sections(plan["examples"], n)
    todo = [x for x in plan["examples"] if shard[x["section"]] == k]
    done = rows_of(root, args.stage, "render")
    todo = [x for x in todo if x["i"] not in done]
    if not todo:
        print(f"RENDER DONE {k}/{n} (nothing to do)")
        return
    if PS.free_gb() < DISK_GUARD_GB:
        raise SystemExit(f"free disk below {DISK_GUARD_GB:.0f} GB")
    ctx = DS.Ctx(quiet=True)
    by_sec = {}
    for x in todo:
        by_sec.setdefault(x["section"], []).append(x)
    LO._wait_cap()
    DS.wait_render_slot()
    rr = K.Renderer()
    primer = DS.Primer(rr)
    swap0 = DS.swap_mb()
    rp = stage_root(root, args.stage) / "rows" / f"render-{k}of{n}.jsonl"
    rp.parent.mkdir(parents=True, exist_ok=True)
    trim0, trim1 = int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR)
    t_start = time.time()
    try:
        DS.check_recipe(rr)
        menu = rr.menu()
        with open(rp, "a") as fh:
            for m, (sid, xs) in enumerate(sorted(by_sec.items())):
                g = DS._guards("t1t2-render", DISK_GUARD_GB, swap0)
                if g:
                    print(g[1], flush=True)
                    raise SystemExit(g[0])
                sec = ctx.sections[sid]
                rows = {x["i"]: {"i": x["i"], "section": sid, "others": []} for x in xs}
                acc = {x["i"]: np.zeros(trim1 - trim0) for x in xs}
                # T2's targets: part C's label re-rendered and checked against its stored mels
                if args.stage == "t2":
                    for x in sorted(xs, key=lambda x: (x["amp"], x["i"])):
                        r = ctx.rows[x["i"]]
                        rng, amp, mode, base = PS.plan_example(x["i"])
                        sel, st, _, _ = PS.settings_for(rng, amp, mode, base, menu, K.START, K.space, K.fmt)
                        if {f"{a}/{b}": v for (a, b), v in st.items()} != r["settings"]:
                            raise SystemExit(f"{x['i']}: settings differ from part C's row")
                        di = B.measure(PS.section_audio(sec["path"], sec["start_s"])).astype(np.float32)
                        y = primer.render((sid, amp), di, sel, st)
                        y = (y.mean(axis=1) if y.ndim == 2 else y)[trim0:trim1]
                        stored = np.load(PS.example_path(x["i"]))
                        share = min(DS.match_share(mm, stored[f"g{h}"]) for h, mm in PS.halves_mel(y).items())
                        if share < DS.MATCH_SHARE:
                            rows[x["i"]]["refused"] = f"target re-render differs from part C's mels ({share:.4f})"
                            continue
                        sc, sha = G.write_flac(flac_path(root, args.stage, x["i"], "target"), y, PS.SR)
                        rows[x["i"]]["target"] = {"scale": sc, "sha256": sha, "g_share": share}
                # other guitars: grouped by (DI, amp) so a group primes once
                stems = sorted({s for x in xs for s in x["stems"]["v"]})
                levels = section_levels(ctx, sec, [o for x in xs for o in x["others"]], stems)
                jobs = []
                for x in xs:
                    if rows[x["i"]].get("refused"):
                        continue
                    for o in x["others"]:
                        if o["dt"]:                              # a DT double: the target's own settings
                            r = ctx.rows[x["i"]]
                            amp = r["amp"]
                            sel = next(iter(menu[amp].values()))[0]
                            st = {tuple(kk.rsplit("/", 1)): v for kk, v in r["settings"].items()}
                        else:
                            amp, sel, st = other_settings(x["i"], o["di"], menu)
                        jobs.append((o["di"], amp, x["i"], o, sel, st))
                jobs.sort(key=lambda j: (j[0], j[1], j[2]))
                di_cache = {}
                for di_id, amp, i, o, sel, st in jobs:
                    lv, src = levels[di_id]
                    if lv is None:
                        rows[i]["others"].append({"di": di_id, "left_out": "no level"})
                        continue
                    if di_id not in di_cache:
                        di_cache = {di_id: B.measure(PS.section_audio(ctx.inv[di_id]["path"], sec["start_s"])).astype(np.float32)}
                    y = primer.render((f"{sid}|{di_id}", amp), di_cache[di_id], sel, st)
                    y = (y.mean(axis=1) if y.ndim == 2 else y)[trim0:trim1]
                    ly = lufs_or_none(y)
                    if ly is None:
                        rows[i]["others"].append({"di": di_id, "left_out": "silent render"})
                        continue
                    gain = 10 ** ((lv - ly) / 20) * pan_fold(o["pan"])
                    acc[i] += y * gain
                    rows[i]["others"].append({"di": di_id, "dt": o["dt"], "amp": amp, "settings": LO.sdict(st),
                                              "level_lufs": lv, "level_from": src, "render_lufs": ly, "pan": o["pan"],
                                              "gain_db": 20 * math.log10(gain)})
                for x in xs:
                    rw = rows[x["i"]]
                    if not rw.get("refused"):
                        sc, sha = G.write_flac(flac_path(root, args.stage, x["i"], "others"), acc[x["i"]], PS.SR)
                        rw["others_file"] = {"scale": sc, "sha256": sha}
                    rw["renders_so_far"] = primer.renders
                    fh.write(json.dumps(rw) + "\n")
                fh.flush()
                print(f"section {m + 1}/{len(by_sec)} {sid[-50:]}: {len(xs)} examples; renders {primer.renders} "
                      f"({primer.primes} priming); {(time.time() - t_start) / (m + 1):.0f} s per section", flush=True)
    finally:
        rr.close()
    print(f"RENDER DONE {k}/{n}: {primer.renders} renders ({primer.primes} priming)")


# --- build (MSST; separations) -----------------------------------------------------------------------------------

class Stems:
    """A section's stems summed at the session's balance (cached per section and vocal variant)."""

    def __init__(self, ctx):
        self.ctx, self.cache = ctx, {}

    def get(self, sid, tracks):
        import numpy as np

        from learn import pretrain_set as PS

        key = (sid, tuple(tracks))
        if key not in self.cache:
            sec = self.ctx.sections[sid]
            sess = pathlib.Path(self.ctx.inv[sec["di"]]["session_dir"])
            b = np.zeros(int(round((PS.SEC_S + PS.TRIM_S) * PS.SR)))
            for t in tracks:
                b += PS.section_audio(sess / t, sec["start_s"])
            if len(self.cache) >= 4:
                self.cache.pop(next(iter(self.cache)))
            self.cache[key] = b[int(PS.TRIM_S * PS.SR):]
        return self.cache[key]


def self_built_mix(y, others, stems_audio, x):
    """The mix of one example (plan (c)): backing = other guitars (already levelled and pan-folded) + stems (centred,
    so folded by pan_fold(0), as a centred other guitar would be); the backing set against the target by the drawn
    ratio, the drawn loudness, and the drawn mastering. -> (mix, gains {gb, ga}, backing LUFS)."""
    from learn import direct_stems as DS
    from learn import song_aug as SA

    b = others + stems_audio * pan_fold(0.0)
    lg, lb = float(SA.lufs(y)), float(SA.lufs(b))
    gb, ga = mix_gains(lg, lb, x["draw"])
    mix = (y + b * 10 ** (gb / 20)) * 10 ** (ga / 20)
    mastered, mrng = DS.master_draw(x["i"])
    if mastered != x["draw"]["mastered"]:
        raise SystemExit(f"{x['i']}: the mastering draw changed")
    if mastered:
        mix = SA.compress(mix, mrng)
    return mix, {"gb": gb, "ga": ga}, lb


def empty_backing_ok(y, lb):
    """False when the backing is (near) silence: `mix_gains_db` clamps it 40 dB under the target, so the mix would
    be the target alone at an unmet ratio."""
    from learn import song_aug as SA

    lg = float(SA.lufs(y))
    return math.isfinite(lb) and lb > lg - 40.0


def cmd_build(args):
    """Mixes and X-LANCE stems (msst-venv): per example the target (K: the stored truth; T2: the stored target
    render), the other guitars' FLAC, the stems; features saved as the D build's (`mix-{stage}`, `xlance_g-{stage}`)."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS

    V.require_real(args)
    root = V.out_root(args)
    plan = _load(plan_path(root, args.stage))
    if not plan:
        raise SystemExit(f"run `plan --stage {args.stage}` first")
    check_lists(root, plan, args.smoke)
    rend = rows_of(root, args.stage, "render")
    built = rows_of(root, args.stage, "build")
    todo = [x for x in plan["examples"] if x["i"] in rend and x["i"] not in built]
    todo.sort(key=lambda x: (x["section"], x["i"]), reverse=args.order == "desc")
    todo = todo[:args.limit or None]
    print(f"build {args.stage}: {len(todo)} to build ({len(rend)} rendered, {len(built)} built) on {args.device}", flush=True)
    if not todo:
        return
    ctx = DS.Ctx(quiet=True)
    ctx.rows = None
    truth = G.gate_rows(DS.ROOT / "gate", "truth") if args.stage == "t1" else {}
    sep = DS.stem_separator(SEP, args.device)
    stems = Stems(ctx)
    swap0 = DS.swap_mb()
    rp = stage_root(root, args.stage) / "rows" / f"build-{args.device}-{os.getpid()}.jsonl"
    rp.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(rp, "a") as fh:
        for m, x in enumerate(todo):
            g = DS._guards("t1t2-build", DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            if ex_path(root, args.stage, x["i"], f"{SEP}-{args.stage}").exists():
                continue                                    # the other worker's
            rw = rend[x["i"]]
            base = {"i": x["i"], "section": x["section"], "band": x["band"]}
            if rw.get("refused"):
                fh.write(json.dumps({**base, "refused": rw["refused"]}) + "\n")
                continue
            if args.stage == "t1":
                t = truth[x["i"]]
                y = G.read_flac(G.truth_path(DS.ROOT / "gate", x["i"]), t["scale"], t["sha256"])
            else:
                y = G.read_flac(flac_path(root, args.stage, x["i"], "target"), rw["target"]["scale"], rw["target"]["sha256"])
            oth = G.read_flac(flac_path(root, args.stage, x["i"], "others"), rw["others_file"]["scale"],
                              rw["others_file"]["sha256"])
            voc = x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"]
            st = stems.get(x["section"], x["stems"]["v" if voc else "n"])
            mix, gains, lb = self_built_mix(np.asarray(y, np.float64), np.asarray(oth, np.float64), st, x)
            if not empty_backing_ok(y, lb):
                fh.write(json.dumps({**base, "refused": "no backing: the drawn ratio cannot be met"}) + "\n")
                fh.flush()
                continue
            s = np.asarray(sep(mix), np.float64)
            if len(s) != len(mix) or not np.isfinite(s).all():
                raise SystemExit(f"{x['i']}: bad stem")
            mm, ml, _ = DS.half_features(mix)
            sm, sl, floor = DS.half_features(s)
            DS._save_npz(ex_path(root, args.stage, x["i"], f"mix-{args.stage}"), mA=mm["A"], mB=mm["B"],
                         lufs=[ml["A"], ml["B"]], gain_db=gains["ga"], mastered=x["draw"]["mastered"])
            DS._save_npz(ex_path(root, args.stage, x["i"], f"{SEP}-{args.stage}"), sA=sm["A"], sB=sm["B"],
                         lufs=[sl["A"], sl["B"]])
            fh.write(json.dumps({**base, "vocals": bool(voc), "gains_db": gains, "lufs_backing": lb,
                                 "lufs_mA": ml["A"], "lufs_mB": ml["B"], "lufs_sA": sl["A"], "lufs_sB": sl["B"],
                                 "floor_share": floor, "snr_audio_db": DS.snr_db(s, y * 10 ** (gains["ga"] / 20)),
                                 "device": args.device}) + "\n")
            fh.flush()
            if m % 25 == 0:
                print(f"build {m + 1}/{len(todo)}: {(time.time() - t0) / (m + 1):.1f} s per example", flush=True)
    print(f"BUILD DONE {args.stage} ({args.device})")


# --- T1: the paired stem-quality check (zero renders) -------------------------------------------------------------

def cmd_t1_read(args):
    """T1's read: per K example the stem's mel SNR (and contamination) against its truth render, K's self-built stem
    against V_sep's stored stem of the same example and draws (paired, band-clustered; section-clustered beside);
    by guitar-to-backing ratio; V-real's stored crop stems against their amp tracks beside."""
    import numpy as np

    from learn import data_cleaning as DC
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pretrain_set as PS

    V.require_real(args)
    root = V.out_root(args)
    plan = _load(plan_path(root, "t1"))
    if plan:
        check_lists(root, plan, args.smoke)
    built = {i: r for i, r in rows_of(root, "t1", "build").items() if not r.get("refused")}
    allrows = rows_of(root, "t1", "build")
    if not plan or (any(x["i"] not in allrows for x in plan["examples"]) and not args.smoke):
        raise SystemExit("K is not fully built (run render and build --stage t1)")
    truth = G.gate_rows(DS.ROOT / "gate", "truth")
    tr = load_lists(root, args.smoke)
    per = {"K": {}, "V_sep": {}}
    cont = {"K": {}, "V_sep": {}}
    band_of, section_of, ratio_of = {}, {}, {}
    for x in plan["examples"]:
        i = x["i"]
        if i not in built:
            continue
        t = truth[i]
        y = G.read_flac(G.truth_path(DS.ROOT / "gate", i), t["scale"], t["sha256"])
        ref = PS.halves_mel(y)
        k = np.load(ex_path(root, "t1", i, f"{SEP}-t1"))
        v = np.load(DS.ex_path(DS.ROOT, i, SEP))
        for name, d in (("K", k), ("V_sep", v)):
            per[name][i] = statistics.fmean([mel_snr(d[f"s{h}"], ref[h]) for h in "AB"])
            cont[name][i] = statistics.fmean([contamination(d[f"s{h}"], ref[h]) for h in "AB"])
        band_of[i], section_of[i], ratio_of[i] = x["band"], x["section"], x["draw"]["ratio_db"]
    keep = set(per["K"]) & set(per["V_sep"])
    bands = sorted({band_of[i] for i in keep})
    band_iv = DS.paired(per["K"], per["V_sep"], band_of, keep)
    sec_iv = DC.section_interval(per["K"], per["V_sep"], section_of, keep)
    primary = band_iv if len(bands) >= 2 else sec_iv       # one band (K is Adam Buckley alone): a band interval is +-inf
    res = {"examples": len(keep), "bands": bands,
           "primary": "band-clustered" if len(bands) >= 2 else "section-clustered (one band)",
           "K - V_sep mel SNR (primary)": primary,
           "K - V_sep mel SNR (paired, band-clustered)": band_iv,
           "K - V_sep mel SNR (section-clustered)": sec_iv,
           "K - V_sep contamination (paired)": DS.paired(cont["K"], cont["V_sep"], band_of, keep),
           "levels": {n: PS.band_t_interval(PS.by_band({i: per[n][i] for i in keep}, band_of)) for n in per},
           "by_ratio": {}}
    for i in keep:
        b = ratio_bin(ratio_of[i])
        res["by_ratio"].setdefault(b, {"n": 0, "K": [], "V_sep": []})
        res["by_ratio"][b]["n"] += 1
        res["by_ratio"][b]["K"].append(per["K"][i])
        res["by_ratio"][b]["V_sep"].append(per["V_sep"][i])
    res["by_ratio"] = {b: {"n": v["n"], "K": statistics.median(v["K"]), "V_sep": statistics.median(v["V_sep"])}
                       for b, v in sorted(res["by_ratio"].items())}
    # V-real beside: the stored crop-only xlance_g stems against the amp tracks, at the crop's ratio
    man = DS._load(DS.stems_manifest_path(DS.ROOT, SEP)) or {"stems": {}}
    lt = V.label_table()
    vr = {}
    for slug in tr["v_real"] + tr["v_real_pending"]:
        st = DS.stored_stem(man, f"stagef/{slug}")
        if st is None:
            continue
        crop = pathlib.Path(lt[slug]["crop"])
        ref, bk = V.mono(crop / "reference.wav"), V.mono(crop / "backing.wav")
        rm, sm = PS.halves_mel(ref), PS.halves_mel(np.asarray(st, np.float64)[:len(ref)])
        rows = {}
        for h, sl in PS.half_slices().items():
            lr, lb_ = lufs_or_none(ref[sl]), lufs_or_none(bk[sl])        # LUFS, as K's drawn ratio
            rows[h] = {"mel_snr": mel_snr(sm[h], rm[h]), "contamination": contamination(sm[h], rm[h]),
                       "ratio_db": lr - lb_ if lr is not None and lb_ is not None else None}
        vr[slug] = {"verified": slug in tr["v_real"], "halves": rows}
    rv = [(h["ratio_db"], h["mel_snr"]) for v in vr.values() if v["verified"] for h in v["halves"].values()
          if h["ratio_db"] is not None and h["mel_snr"] is not None]      # pending parts are shown, not pooled
    if rv:
        lo, hi = min(r for r, _ in rv), max(r for r, _ in rv)
        m = {i for i in keep if lo <= ratio_of[i] <= hi}
        res["matched_ratio"] = {"v_real_range_db": [lo, hi], "examples": len(m),
                                "K": statistics.median([per["K"][i] for i in m]) if m else None,
                                "V_sep": statistics.median([per["V_sep"][i] for i in m]) if m else None,
                                "V_real": statistics.median([s for _, s in rv])}
    res["v_real"] = vr
    # descriptive (ROADMAP (b)): K cleaner than V_sep is the cleaning gain the plan expects (no other take, no
    # original-tone bleed), not a realism verdict; realism is K against V-real at matched ratio, beside. No lever is
    # coded or approved, so T1 changes nothing in T2 by itself
    res["reading"] = ("K's stems are cleaner than V_sep's (the expected cleaning gain); realism: see matched_ratio"
                      if (primary or (0, 0, 0, 0))[1] > 0 else "K's stems are not shown cleaner than V_sep's")
    out = {"plan": PLAN, "stage": "T1", "smoke": bool(args.smoke), "results": res, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(stage_root(root, "t1") / "read.json", out)
    print(json.dumps({k: v for k, v in res.items() if k != "v_real"}, indent=1, default=float))
    print(f"T1: {res['reading']}")


# --- T2: training, fitting, readouts ------------------------------------------------------------------------------

def arms_of(plan):
    """The arms T2 can run: SYN-E only when its Eggy swap was drawn (every Eggy DI must pass T0)."""
    return tuple(a for a in ARMS if a != "SYN-E" or not (plan.get("syn_e") or {}).get("refused"))


def arm_files(root, plan, arm, ses_files):
    """{i: (mix path, stem path)} of an arm's training and early-stopping examples."""
    out = {}
    syn = {x["i"] for x in plan["examples"]}
    if arm == "SES":
        for i in plan["pilot"] + plan["es"]:
            out[i] = ses_files[i]
        return out
    ids = (plan["pilot"] if arm == "SYN" else plan["syn_e"]["kept"] + plan["syn_e"]["eggy"]) + plan["es"]
    for i in ids:
        m, s = ex_path(root, "t2", i, "mix-t2"), ex_path(root, "t2", i, f"{SEP}-t2")
        if i in syn and m.exists() and s.exists():          # a refused or unbuilt example has no files
            out[i] = (str(m), str(s))
    return out


def arm_rows(ctx, plan, arm, files, refused):
    """(training rows, early-stopping rows) of an arm, the shared refusals dropped (every arm drops the pilot
    examples any arm refused; SYN-E's own swap-ins drop only from SYN-E)."""
    by = {r["i"]: r for r in ctx.pool}
    tr_ids = plan["pilot"] if arm in ("SES", "SYN") else plan["syn_e"]["kept"] + plan["syn_e"]["eggy"]
    tr = [{**by[i], "early_stop": False, "split": "train"} for i in tr_ids if i not in refused and i in files]
    es = [{**by[i], "early_stop": True, "split": "train"} for i in plan["es"] if i not in refused and i in files]
    return tr, es


class ArmData:
    """`direct_stems.StemData` with explicit feature files per example (an arm's own mixes and stems)."""

    def __new__(cls, rows, files, aug=True):
        import numpy as np

        from learn import direct_stems as DS
        from learn import pretrain_set as PS
        from learn import song_model as SM

        self = object.__new__(DS.StemData)
        self.rows, self.arm, self.aug = rows, MODEL_ARM, aug
        n = len(rows)
        self.M = np.zeros((n, 2, 96, 446), np.uint8)
        self.LM = np.zeros((n, 2), np.float32)
        self.S = np.zeros((n, 2, 96, 446), np.uint8)
        self.LS = np.zeros((n, 2), np.float32)
        self.ga = np.zeros(n, np.float32)
        for j, r in enumerate(rows):
            mp, sp = files[r["i"]]
            d, e = np.load(mp), np.load(sp)
            self.M[j, 0], self.M[j, 1], self.LM[j] = d["mA"], d["mB"], d["lufs"]
            self.ga[j] = float(d["gain_db"])
            self.S[j, 0], self.S[j, 1], self.LS[j] = e["sA"], e["sB"], e["lufs"]
        self.cands = DS.merge_candidates(rows) if aug else {}
        self.gpos, self.G = {}, None
        if aug:
            pos = sorted({p for v in self.cands.values() for p, _ in v})
            self.gpos = {p: k for k, p in enumerate(pos)}
            self.G = np.zeros((len(pos), 2, 96, 446), np.uint8)
            for p, k in self.gpos.items():
                g = np.load(PS.example_path(rows[p]["i"]))
                self.G[k, 0], self.G[k, 1] = g["gA"], g["gB"]
        self.centres = DS.mel_centres_hz()
        enc = [SM.encode(r["label"]) for r in rows]
        self.Y = [np.stack(z) for z in zip(*enc)]
        self.masked = 0
        self.applied = {}
        return self


def t2_refused(root, plan, ses_rows_):
    """Pilot and early-stopping examples any arm cannot read: refused or unbuilt in SYN, or absent from SES."""
    rend = rows_of(root, "t2", "render")
    built = rows_of(root, "t2", "build")
    bad = {i for i, r in {**rend, **built}.items() if r.get("refused")}
    need = set(plan["pilot"]) | set(plan["es"])
    unbuilt = {i for i in need if i not in built}          # a refused build row counts as built: dropped above
    absent = {i for i in need if i not in ses_rows_}
    return union_refused(bad & need, unbuilt, absent), unbuilt


def run_path(root, arm, seed):
    return stage_root(root, "t2") / "runs" / f"{arm}-{seed}.json"


def cmd_train(args):
    """One T2 run (demucs-venv): D_stem's recipe on an arm's 5k (augmented), early stopping on the arm's set."""
    import numpy as np
    import torch

    from learn import direct_stems as DS
    from learn import pretrain_set as PS

    V.require_real(args)
    root = V.out_root(args)
    if args.arm not in ARMS or (args.seed not in TRAIN_SEEDS and not args.smoke):
        raise SystemExit(f"--arm in {ARMS}, --seed in {TRAIN_SEEDS}")
    rp = run_path(root, args.arm, args.seed)
    if rp.exists():
        print(f"{rp.name} exists: nothing to do")
        return
    plan = _load(plan_path(root, "t2"))
    if not plan:
        raise SystemExit("run `plan --stage t2` first")
    check_lists(root, plan, args.smoke)
    if args.arm not in arms_of(plan):
        raise SystemExit(f"{args.arm} cannot run: {plan['syn_e'].get('refused')}")
    ctx = DS.Ctx(quiet=True)
    ses, ses_files = ses_rows(ctx)
    refused, unbuilt = t2_refused(root, plan, ses)
    if unbuilt and not args.smoke:
        raise SystemExit(f"{len(unbuilt)} pilot or early-stopping examples are not built: every arm waits for the build")
    files = arm_files(root, plan, args.arm, ses_files)
    tr_rows, es_rows = arm_rows(ctx, plan, args.arm, files, refused)
    rows = tr_rows + es_rows
    tr = np.arange(len(tr_rows))
    es = np.arange(len(tr_rows), len(rows))
    torch.set_num_threads(2)
    dev = torch.device("cpu" if os.environ.get("DS_DEVICE") == "cpu" or not torch.backends.mps.is_available() else "mps")
    data = ArmData(rows, files, aug=True)
    print(f"T2 {args.arm} seed {args.seed}: {len(tr)} train, {len(es)} early stopping, {len(refused)} dropped; {dev}",
          flush=True)
    t0 = time.time()
    for attempt in (1, 2):
        log = []
        data.masked, data.applied = 0, {}
        try:
            net, state, best_ep, best = DS.train_arm(data, tr, es, args.seed, dev, log, DS.MAX_EPOCHS)
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
    rec = {"plan": PLAN, "stage": "T2", "arm": args.arm, "seed": args.seed, "model_arm": MODEL_ARM, "stem_sep": SEP,
           "train": len(tr), "early_stop": len(es), "dropped": sorted(refused), "attempts": attempt,
           "epochs_run": len(log), "best_epoch": best_ep, "best_early_stop_loss": best,
           "minutes": round((time.time() - t0) / 60, 1), "augmentations_applied": data.applied, "device": str(dev),
           "model": mp.name, "model_sha256": DS.hashlib_file(mp), "log": log, "smoke": bool(args.smoke),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(rp, rec)
    print(f"TRAIN DONE T2 {args.arm} {args.seed}: best epoch {best_ep} of {len(log)}")
    if best_ep is not None and best_ep >= DS.MAX_EPOCHS - CAP_EDGE:
        print(f"WARNING: best epoch {best_ep} is within {CAP_EDGE} of the cap {DS.MAX_EPOCHS}: still improving "
              "(report flags it); extend this run before reading")


def load_arm(root, arm, smoke=False):
    """(nets, run records) of an arm's two seeds."""
    import torch

    from learn import pretrain_set as PS

    nets, recs = [], []
    for s in TRAIN_SEEDS:
        rec = _load(run_path(root, arm, s))
        if not rec or (rec.get("smoke") and not smoke):
            raise SystemExit(f"{arm} seed {s} has no run")
        net = PS.build_net()
        net.load_state_dict(torch.load(run_path(root, arm, s).with_suffix(".pt"), map_location="cpu"))
        net.eval()
        nets.append(net)
        recs.append(rec)
    return nets, recs


def cmd_fit(args):
    """Per arm (zero renders): the constant (the arm's training-label medians per amp and base class, audible knobs)
    and amendment 5's pull, fitted on the arm's early-stopping set read through its own mixes and stems."""
    from learn import data_cleaning as DC
    from learn import direct_stems as DS

    V.require_real(args)
    root = V.out_root(args)
    plan = _load(plan_path(root, "t2"))
    if not plan:
        raise SystemExit("run `plan --stage t2` first")
    check_lists(root, plan, args.smoke)
    ctx = DS.Ctx(quiet=True)
    ses, ses_files = ses_rows(ctx)
    refused, _ = t2_refused(root, plan, ses)
    out = {"plan": PLAN, "stage": "T2 fit", "readout_rule": DS.READOUT_RULE, "arms": {}}
    for arm in arms_of(plan):
        nets, recs = load_arm(root, arm, args.smoke)
        files = arm_files(root, plan, arm, ses_files)
        tr_rows, es_rows = arm_rows(ctx, plan, arm, files, refused)
        med = DS.label_medians(tr_rows, DS.encode_audible)
        cell_of = {r["i"]: (r["amp"], r["base"]) for r in es_rows}
        outs, who, Y = DS.run_rows(nets, es_rows, lambda rr, f=files: DC.stem_tensors(
            rr, lambda i: f[i][0], lambda i: f[i][1], MODEL_ARM))
        Ym = DS.silent_masks(Y)
        _, ans = DS.median_answers(outs, who)
        table = DS.fit_pull_table(ans, DS.labels_of(who, Ym), cell_of, med)
        out["arms"][arm] = {"models": {str(r["seed"]): r["model_sha256"] for r in recs}, "constant": DS.medians_json(med),
                            "pull": DS.table_json(table), "pull_summary": DS.pull_summary(table),
                            "early_stop_examples": len(es_rows)}
        print(f"{arm}: pull {DS.pull_summary(table)}", flush=True)
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save(stage_root(root, "t2") / "fit.json", out)


def arm_fit(root, arm, recs):
    from learn import direct_stems as DS

    f = (_load(stage_root(root, "t2") / "fit.json") or {}).get("arms", {}).get(arm)
    if not f:
        raise SystemExit("run `fit` first")
    if f["models"] != {str(r["seed"]): r["model_sha256"] for r in recs}:
        raise SystemExit(f"{arm}: the fit was made with other models")
    return DS.medians_from_json(f["constant"]), DS.table_from_json(f["pull"])


def cmd_e_on_k(args):
    """E on K per arm (zero renders): amendment 5's answer on K's self-built stems, masked E, the arm's constant and
    pull; the constant's E and the paired contrasts beside."""
    from learn import data_cleaning as DC
    from learn import direct_stems as DS
    from learn import pretrain_set as PS

    V.require_real(args)
    root = V.out_root(args)
    k_plan = _load(plan_path(root, "t1"))
    if not k_plan:
        raise SystemExit("run `plan --stage t1` first")
    check_lists(root, k_plan, args.smoke)
    built = {i for i, r in rows_of(root, "t1", "build").items() if not r.get("refused")}
    ctx = DS.Ctx(quiet=True)
    by = {r["i"]: r for r in ctx.parts["vsep"]}
    rows = [by[x["i"]] for x in k_plan["examples"] if x["i"] in built]
    band_of = {r["i"]: r["band"] for r in rows}
    cell_of = {r["i"]: (r["amp"], r["base"]) for r in rows}
    per, consts = {}, {}
    arms = arms_of(_load(plan_path(root, "t2")) or {})
    for arm in arms:
        nets, recs = load_arm(root, arm, args.smoke)
        med, table = arm_fit(root, arm, recs)
        outs, who, Y = DS.run_rows(nets, rows, lambda rr: DC.stem_tensors(
            rr, lambda i: ex_path(root, "t1", i, "mix-t1"), lambda i: ex_path(root, "t1", i, f"{SEP}-t1"), MODEL_ARM))
        per[arm] = DS.readout_per(DS.score_all(outs, who, DS.silent_masks(Y), cell_of, med, table)[0])["A1+A2+A3"]
        consts[arm] = DS.const_errors(rows, med, DS.encode_audible)
    ids = set(per["SES"])
    res = {"examples": len(ids), "levels": {a: PS.band_t_interval(PS.by_band(per[a], band_of)) for a in arms},
           "constant": {a: PS.band_t_interval(PS.by_band(consts[a], band_of)) for a in arms},
           "SYN - SES": DS.paired(per["SYN"], per["SES"], band_of, ids),
           "SYN-E - SYN": DS.paired(per["SYN-E"], per["SYN"], band_of, ids) if "SYN-E" in per else None,
           "per arm - its constant": {a: DS.paired(per[a], consts[a], band_of, ids) for a in arms}}
    if len({band_of[i] for i in ids}) < 2:            # one band: a band interval is +-inf (T1's fallback, as there)
        section_of = {x["i"]: x["section"] for x in k_plan["examples"]}
        res["section-clustered (one band)"] = {
            "SYN - SES": DC.section_interval(per["SYN"], per["SES"], section_of, ids),
            "per arm - its constant": {a: DC.section_interval(per[a], consts[a], section_of, ids) for a in arms}}
    _save(stage_root(root, "t2") / "e-on-k.json", {"plan": PLAN, "results": res, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(json.dumps(res, indent=1, default=float))


def vreal_dirs(tr):
    """V-real's directions: stage F's on the trusted V-real parts."""
    from learn import arm_a_mega53 as A

    keep = set(tr["v_real"])
    return [d for d in A.stage_dirs("F") if d[0] in keep]


def cmd_vreal_predict(args):
    """The arms' answers on V-real (zero renders): step 4's inputs path (the stored crop and its xlance_g crop stem,
    one gain to the training median), the search half, amendment 5's answer with the arm's constant and pull."""
    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import local_objective as LO

    V.require_real(args)
    root = V.out_root(args)
    tr = load_lists(root, args.smoke)
    dirs = vreal_dirs(tr)
    if not dirs:
        raise SystemExit("V-real is empty: the ear has confirmed no stage F part yet")
    man = DS._load(DS.stems_manifest_path(DS.ROOT, SEP))
    target = json.loads(DE.LEVELS.read_text())["summary"]["eval_mix_lufs_median"]
    ms = A.L.menu_S()
    arms = arms_of(_load(plan_path(root, "t2")) or {})
    preds, inputs = {a: {} for a in arms}, {}
    for arm in arms:
        nets, recs = load_arm(root, arm, args.smoke)
        med, table = arm_fit(root, arm, recs)
        for slug, amp, search, held in dirs:
            part = A.f_part(slug)
            cls = part["gain_class"]
            if slug not in inputs:
                mix, _, hashes = DE.f_inputs(slug, "mega53")
                cf = DS.stored_stem(man, f"stagef/{slug}")
                inputs[slug] = {"mix": mix, "stem": cf, "gain_db": DE.inference_gain_db(mix, target),
                                "hashes": {"context": hashes["context"], "stem": man["stems"][f"stagef/{slug}"]["sha256"]}}
            it = inputs[slug]
            b, gap = DS.cell_b(table, (amp, cls), DS.masks(amp, cls)[0])
            if gap and not args.smoke:
                raise SystemExit(f"{arm} {amp} {cls}: {gap} labelled dims have no fitted weight")
            s8, m8, ls, lm = DS.step4_half(it["stem"], it["mix"], search, it["gain_db"])
            x, c = DS.model_input(s8, m8, ls, lm, search, amp, cls, MODEL_ARM)
            cont, sw, mics, diag, _ = DS.answer(nets, x, c, b, med[(amp, cls)])
            _, S = ms[amp][cls]
            preds[arm][f"{slug}|{amp}|{search}"] = {"settings": LO.sdict(DS.settings_from(amp, S, cont, sw, mics)),
                                                    "held": held, "diag": diag}
    _save(stage_root(root, "t2") / "vreal" / "predictions.json",
          {"plan": PLAN, "smoke": bool(args.smoke), "directions": len(dirs), "arms": list(arms), "predictions": preds,
           "inputs": {s: v["hashes"] for s, v in inputs.items()}, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"VREAL PREDICT: {len(dirs)} directions x {len(ARMS)} arms")


def cmd_vreal_render(args):
    """V-real's renders for one shard of (part, amp) groups: one discarded priming render at S, then each arm's
    answer once per direction through the part's measure DI, judged on both halves (`direct_stems.run_group`).
    isolate=True; at most 3 render processes machine-wide; resumable."""
    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    V.require_real(args)
    root = V.out_root(args)
    od = stage_root(root, "t2") / "vreal"
    pred = _load(od / "predictions.json")
    if not pred or (pred.get("smoke") and not args.smoke):
        raise SystemExit("run `vreal-predict` first")
    tr = load_lists(root, args.smoke)
    groups = A.groups(vreal_dirs(tr))
    mine = DE.shard(groups, args.shard)
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
            ctx = A.group_ctx(menu, ms, "F", slug, amp)
            if K.key(dict(ctx["S"])) != K.key(ctx["S_stored"]):
                raise SystemExit(f"{amp}: the live S differs from the stored copy")
            g = {"sel": ctx["sel"], "S": ctx["S"], "di": ctx["di"], "di32": ctx["di32"], "ref": ctx["ref"],
                 "lag": ctx["part"]["judge_lag"]}
            arms = tuple(pred.get("arms") or ARMS)
            settings = {a: {sh: LO.tdict(pred["predictions"][a][f"{slug}|{amp}|{sh}"]["settings"]) for sh, _ in K.DIRECTIONS}
                        for a in arms}
            rec = DS.run_group(rr, g, settings, False, None, K.judge, arms=arms)
            rec.update(slug=slug, amp=amp)
            _save(gp, rec)
            print(slug, amp, rec["renders"], flush=True)
    finally:
        rr.close()
    print(f"VREAL RENDER DONE {args.shard[0]}/{args.shard[1]}; renders {rr.count}")


CAP_EDGE = 4                           # a best epoch this close to the cap: the run was still improving


def report_gaps(units, arms, groups, predicted, keep, refused):
    """Why T2's reading cannot be read yet (an empty list when it can): unjudged directions, groups not done,
    predictions for another V-real list, or answers refused (scored as S)."""
    gaps = []
    for a in arms:
        n = sum(1 for u in units if u["d"].get(a) is None)
        if n:
            gaps.append(f"{n} directions have no {a} value")
    notdone = sorted(f"{s}|{m}" for (s, m) in {(u["slug"], u["amp"]) for u in units}
                     if (groups.get((s, m)) or {}).get("status") != "done")
    if notdone:
        gaps.append(f"{len(notdone)} groups not done (e.g. {notdone[:2]})")
    if predicted != keep:
        gaps.append(f"the predictions cover other V-real parts (missing {sorted(keep - predicted)[:3]}, extra "
                    f"{sorted(predicted - keep)[:3]}): rerun vreal-predict and vreal-render")
    bad = {a: n for a, n in (refused or {}).items() if n}
    if bad:
        gaps.append(f"refused answers scored as S {bad}: declare their scoring before reading")
    return gaps


def runs_at_cap(root, arms):
    """T2 runs whose best epoch sits within CAP_EDGE of the epoch cap (the pilot hit 38-39 of 40 at 5k)."""
    from learn import direct_stems as DS

    out = []
    for a in arms:
        for seed in TRAIN_SEEDS:
            r = _load(run_path(root, a, seed)) or {}
            if r.get("best_epoch") is not None and r["best_epoch"] >= DS.MAX_EPOCHS - CAP_EDGE:
                out.append(f"{a} seed {seed} (best epoch {r['best_epoch']}/{DS.MAX_EPOCHS})")
    return out


def cmd_report(args):
    """T2's report: SYN - SES on V-real (primary, paired by direction, band-weighted, 90% band-clustered), SYN-E - SYN
    and each arm - S beside (rows: all, F-song, without the MUSDB18 songs; per class and amp in report.json); E on K;
    T1's stem SNR; the reading (no pass bar; a tie picks SYN). The reading is 'incomplete' until every V-real
    direction is judged for every arm, the predictions cover exactly today's V-real parts, and no answer was refused
    (a refused answer would score as S, which can favour the broken arm)."""
    from learn import arm_a_mega53 as A
    from learn import direct_stems as DS
    from learn import local_objective_1c as C
    from learn import perfect_sep_arm as P

    V.require_real(args)
    root = V.out_root(args)
    od = stage_root(root, "t2") / "vreal"
    tr = load_lists(root, args.smoke)
    keep = set(tr["v_real"])
    units = [u for u in P.build_units() if u["slug"] in keep]
    groups = {}

    def value(arm):
        def f(u):
            k = (u["slug"], u["amp"])
            if k not in groups:
                groups[k] = _load(od / "groups" / f"{u['slug']}|{u['amp']}.json") or {}
            g = groups[k]
            return g["judge"][f"{arm}|{u['search']}"][u["held"]] if g.get("status") == "done" else None
        return f

    pred = _load(od / "predictions.json") or {}
    arms = tuple(pred.get("arms") or ARMS)
    refused = {a: DS.add_step4_arm(units, a, value(a)) for a in arms}
    rows_ = ("all", "f_song", "without_any_musdb")
    bt = C.load_bleed_table()
    filt = {r: A.row_filter(r, "F", bt, {}) for r in rows_}
    con = {}
    for name, (a, b) in {"SYN - SES": ("SYN", "SES"), "SYN-E - SYN": ("SYN-E", "SYN"), "SES - S": ("SES", "S"),
                         "SYN - S": ("SYN", "S"), "SYN-E - S": ("SYN-E", "S")}.items():
        if a in arms and (b in arms or b == "S"):
            con[name] = DS.step4_contrast(units, a, b, filt, rows=rows_, fixed=("S",))
    prim = (con["SYN - SES"]["rows"].get("all") or {}).get("all") or {}
    iv = (prim.get("band_weighted_mean"), prim.get("lo90"), prim.get("hi90"))
    gaps = report_gaps(units, arms, groups, set(pred.get("inputs") or {}), keep, refused)
    rep = {"plan": PLAN, "stage": "T2", "v_real_parts": sorted(keep), "directions": len(units),
           "done": sum(1 for u in units if u["d"].get("SYN") is not None), "refused_scored_as_S": refused,
           "complete": not gaps, "incomplete_because": gaps, "runs_at_epoch_cap": runs_at_cap(root, arms),
           "contrasts": con, "reading": reading(iv) if not gaps else "incomplete",
           "e_on_k": (_load(stage_root(root, "t2") / "e-on-k.json") or {}).get("results"),
           "t1": ((_load(stage_root(root, "t1") / "read.json") or {}).get("results") or {}).get(
               "K - V_sep mel SNR (primary)"),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(stage_root(root, "t2") / "report.json", rep)
    print(f"{rep['done']}/{rep['directions']} V-real directions; refused scored as S {refused}")
    for g in gaps:
        print(f"  incomplete: {g}")
    for r in rep["runs_at_epoch_cap"]:
        print(f"  WARNING: {r} stopped within {CAP_EDGE} epochs of the cap: still improving, extend it before reading")
    for name, c in con.items():
        for row in rows_:
            s = (c["rows"].get(row) or {}).get("all") or {}
            print(f"  {name:12s} {row:18s} {s.get('band_weighted_mean')} [{s.get('lo90')}, {s.get('hi90')}] "
                  f"({s.get('bands')} bands)")
        for cls, s in sorted(((c["rows"].get("all") or {}).get("per_class") or {}).items()):
            print(f"  {'':12s} class {cls:12s} {s.get('band_weighted_mean')} [{s.get('lo90')}, {s.get('hi90')}] "
                  f"({s.get('bands')} bands)")
    print(f"T2 READING: {rep['reading']}")


# --- main --------------------------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(prog="trusted_data", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("plan", "render", "build", "t1-read", "train", "fit", "e-on-k", "vreal-predict",
                                    "vreal-render", "report"))
    ap.add_argument("--stage", choices=("t1", "t2"), default="t1")
    ap.add_argument("--shard", type=V.parse_shard, default=(0, 1))
    ap.add_argument("--device", default="mps")
    ap.add_argument("--order", choices=("asc", "desc"), default="asc")
    ap.add_argument("--arm", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)
    if args.limit and not args.smoke:
        raise SystemExit("--limit is for smoke runs (with --smoke and --out)")
    {"plan": cmd_plan, "render": cmd_render, "build": cmd_build, "t1-read": cmd_t1_read, "train": cmd_train,
     "fit": cmd_fit, "e-on-k": cmd_e_on_k, "vreal-predict": cmd_vreal_predict, "vreal-render": cmd_vreal_render,
     "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
