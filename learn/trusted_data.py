"""The trusted-data plan's self-built mixes, T1 and T2 (`docs/trusted-data-strategy-plan.md`, approved 2026-10-23 with
its recorded decisions; the design in `docs/trusted-data-t0-design.md`). Development data only. Every command here
reads T0's lists (`learn/verify_tracks.py lists`): only verified DIs, targets and stems are used.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    MSST=~/ndsp-presets/tools/msst-venv/bin/python; TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MAIN -u -m learn.trusted_data amp-bleed --stage t1|t2 --shard k/n   # zero renders: rule 1's amp-track bleed check
    $MAIN -m learn.trusted_data plan --stage t1|t2                 # zero renders: examples, draws, other guitars, counts
    $MAIN -u -m learn.trusted_data render --stage t1|t2 --shard k/3   # renders: T2's targets, every other guitar
    $MSST -m learn.trusted_data build --stage t1|t2 --device mps --order asc    # self-built mixes + X-LANCE stems
    $MSST -m learn.trusted_data build --stage t1|t2 --device cpu --order desc   # optional second worker
    $MAIN -m learn.trusted_data t1-read [--subset rules|rules-di]  # T1: paired K - V_sep stem SNR; V-real beside
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
  with no DI are not rendered (decision 4: other guitars are DI renders only). *Rule 1 (the user, 2026-10-25):* a
  session guitar that plays in the section (amp track or DI, against its own file's level) but cannot be rendered (no
  DI, a DI T0 does not verify, or a window it does not mark usable) is its own recorded amp or mic tracks, summed
  with the stems at the session's balance and folded like them, when each passes an automatic bleed check (A6's
  line: other-instrument bleed under -30 dB, `amp-bleed`; no listening); acoustic guitars too. A part with no such
  track, or one that fails, leaves the example out of every arm at plan time (LEFT_OUT_NO_AMP). *Rule 2 (T1 audit):*
  an other guitar's render below RENDER_FLOOR_LUFS (or silent) refuses its example, never lifted to its level.
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
stored stem of the same example and draws, paired, 90% band-clustered with at least 3 bands, else section-clustered
(primary; the other beside), means with medians and the share of stems below 0 dB; the audit's contamination beside;
V-real's stored crop stems against their amp tracks beside, by guitar-to-backing ratio. `t1-read --subset` re-reads
the stored rows under the T1 audit's rules at zero renders (rule 1 as the audit coded it: the stored K mixes have no
amp tracks).

**T2** (the pilot): 5k trusted-pool examples (seed 20261099, stratified by band) outside an early-stopping set of
about 5% of the trusted sections, at least one per band (seed 20261100, at most 1,000 examples). Arms: SES, the stored
session stems (the cleaning manifest's rebuilt files where listed); SYN, self-built backings of the same examples,
labels and draws; SYN-E, SYN with a seeded third (seed 20261101) swapped for Eggy examples whose DIs pass T0. D_stem's
recipe (`direct_stems.train_arm`, augmented), 2 seeds each, early stopping on the set in each arm's own mix type
(SYN-E reads SYN's). Per arm the constant (training-label medians) and amendment 5's pull (fitted on the set).
Reads: SYN - SES on V-real by the judge with the measure DI, paired by direction (primary; a tie under about 0.03
picks SYN, recorded decision 4); SYN-E - SYN; each arm against the song-blind constant (the step 3 gate's
constant on the training labels, rendered on V-real as one more arm: user, 2026-10-24), so a gain over S can be split
into the song and the constant's pull; E on K; stem SNR.

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
CONST_ARM = "constant"                 # the song-blind constant on V-real (user, 2026-10-24): one more answer per
                                       # direction, read beside the primary
TRAIN_SEEDS = (20261042, 20261043)
MODEL_ARM = "Dstem"                    # D_stem's inputs (mix zeroed) and augmentations
TIE = 0.03                             # the plan's power: effects under about 0.03 read as ties
RATIO_BINS = (-15.0, -10.0, -5.0)
EGGY = V.EGGY
K_OUT_BANDS = V.K_OUT_BANDS
DISK_GUARD_GB = 31.0
PAN_PRIOR = {"other_guitar": "uniform [-1, 1]", "dt_double": "opposite the target", "target": "uniform [-1, 1]",
             "stems": "centre"}
# The T1 audit (2026-10-25): a self-built mix never drops an active guitar or lifts a near-silent render
LEFT_OUT_ACTIVE = "an active guitar cannot be rendered"   # plan time: a session guitar plays here, no usable DI
RENDER_FLOOR_LUFS = -50.0              # render time: an other guitar's render below this is refused, never lifted
NEAR_SILENT = "near-silent render (gate or low output)"
MIN_BANDS = 3                          # fewer bands: the section-clustered interval is primary (2 bands = 1 df)
# The user's decision (2026-10-25, the ML session's option 1): in K's and SYN's backings an active guitar that cannot
# be rendered is the session's own recorded amp or mic track(s), at the session's balance, after an automatic bleed
# check equivalent to the targets' A6 (no listening); a part with no such track, or one that fails, leaves the example
# out of every arm
LEFT_OUT_NO_AMP = "an active guitar has no usable amp track"
LEFT_OUT_CAP = "more active guitars than the cap"           # more renderable active guitars than MAX_OTHERS
LEFT_OUT_OWN_TAKE = "an added amp track is in the cleaning scan's removed or same-part tracks"
AMP_BLEED_DB = V.A6_BLEED_DB           # an amp track is used when its other-instrument bleed reads under this (-30 dB)
AMP_BLEED_DIR = "amp-bleed"            # root/amp-bleed/<session>.json: the readings (`amp-bleed`)
AMP_SOURCE_MIN_SHARE = 0.5             # a source playing on fewer of the amp track's playing frames is unmeasurable
AMP_BLEED_MEASURE = ("data_cleaning's session-level take estimator (SessionMeter, counted frames, rolled nulls; the "
                     "stem scan's) over the whole session, with each non-guitar track as the source (never another "
                     "guitar track: bleed_sources) and the amp track as the reference; stored raw per source: the real "
                     "and rolled held-out explained energies as shares of the amp track's energy on its playing "
                     "frames, and the source's active share of those frames (v3)")


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


# --- pure: the T1 audit's fixes (2026-10-25) ----------------------------------------------------------------------

def part_number(key):
    """The part number in a part key ('elecgtr1a' -> 1, 'gtr2' -> 2, 'elecgtr02dt' -> 2), None without one."""
    import re

    m = re.search(r"(\d+)", key or "")
    return int(m.group(1)) if m else None


def part_keys(files, owners=None):
    """{guitar track: part key}: `verify_tracks.guitar_part_key`, except that an inventory DI's own amp tracks take
    the DI's part (owners: {DI file: [its own amp tracks]}, the inventory's `own`): Hollow Ground's ElecGtr1a_Amp1,
    ElecGtr1b_Amp2 and ElecGtr1c_DI are one take, which the name key splits by their letters. An own track whose name
    gives another part number than the DI's stays its own part (Renesans' "GTR 2 Amp_M81" under "GTR 1 DI")."""
    keys = {f: V.guitar_part_key(f) for f in V.guitar_sources(files)}
    base = dict(keys)
    for di, own in sorted((owners or {}).items()):
        for o in own or []:
            if di in keys and o in keys:
                a, b = part_number(base[o]), part_number(base[di])
                if a is None or b is None or a == b:
                    keys[o] = keys[di]
    return keys


def session_guitar_parts(files, mix, target_di, own=(), is_di=None, owners=None):
    """{part key: [track]}: the session's guitar tracks (`verify_tracks.guitar_sources`, acoustic ones included)
    other than the target's own part, grouped by part (`part_keys`). Non-DI tracks count only when they are in the
    inventory's mix list (the stored session backing's source), when there is one; DIs always count (the stored
    backing never holds a DI, but a self-built mix renders one). files: the session's file names."""
    if is_di is None:
        from learn import clean_di as CD

        is_di = CD.is_guitar_di
    tname = pathlib.PurePosixPath(target_di).name
    keys = part_keys(files, owners)
    tkey = keys.get(tname) or V.guitar_part_key(tname)
    mixset = set(mix or [])
    out = {}
    for f in V.guitar_sources(files):
        if f == tname or f in set(own) or V.NON_MUSICAL.search(f):
            continue
        if not is_di(f) and mixset and f not in mixset:
            continue
        k = keys[f]
        if k != tkey:
            out.setdefault(k, []).append(f)
    return {k: sorted(v) for k, v in sorted(out.items())}


def blocked_parts(parts, activity, renderable, active_min=ACTIVE_MIN, scope="all"):
    """The T1 audit's rule 1: the other guitars that play in the section but cannot be rendered. parts: {part:
    [track]}; activity: {track: share of the section's frames playing against the track's own file's level}; a part
    plays when any of its tracks (amp track or DI) reaches active_min. renderable: {part: None if a DI of the part can
    be rendered here, else why not ('no DI', 'DI not verified', 'window excluded', ...)}; a part missing from it has
    no DI. scope 'di' (a diagnostic, not the rule) counts only parts that have a DI.
    -> [{"part", "activity", "why"}], sorted by part."""
    out = []
    for p, tracks in sorted(parts.items()):
        why = renderable.get(p, "no DI")
        if why is None or (scope == "di" and why == "no DI"):
            continue
        a = max((activity.get(t) or 0.0) for t in tracks) if tracks else 0.0
        if a >= active_min:
            out.append({"part": p, "activity": round(a, 3), "why": why})
    return out


def near_silent(render_lufs, floor=RENDER_FLOOR_LUFS):
    """The T1 audit's rule 2: an other guitar's render below the floor (or silent: None) is refused, never lifted to
    its level. -> the refusal reason, or None."""
    if render_lufs is None or render_lufs < floor:
        return NEAR_SILENT
    return None


def rule2_examples(render_rows, floor=RENDER_FLOOR_LUFS):
    """Examples of stored render rows that rule 2 would have refused: an other guitar rendered below the floor, or
    left out as a silent render (the old path). -> sorted ids."""
    out = set()
    for i, r in render_rows.items():
        for o in r.get("others") or []:
            if o.get("left_out") == "silent render" or o.get("refused") == NEAR_SILENT or (
                    o.get("render_lufs") is not None and o["render_lufs"] < floor):
                out.add(i)
    return sorted(out)


def amp_bleed_total(takes, floor=None):
    """An amp track's other-instrument bleed in dB of the amp track: the power sum of the other tracks' takes in it
    that reach the cleaning plan's floor (`data_cleaning.FLOOR_DB`, -40 dB: a take under it counts as none, as in
    `data_cleaning.removal`). None when no take reaches it. takes: {source: dB or None}."""
    from learn import data_cleaning as DC

    floor = DC.FLOOR_DB if floor is None else floor
    v = [x for x in takes.values() if x is not None and x >= floor]
    return DC.db_sum(v) if v else None


def source_take(src, thr=AMP_BLEED_DB, min_share=None):
    """One non-guitar source's reading in an amp track, from its stored raw values (src: {"real", "nulls": held-out
    explained energies as shares of the amp track's energy on its playing frames, "active_share"}). -> (take dB or
    None, unmeasurable reason or None). The take is `data_cleaning.take_db` on the raw values (no clipping), capped
    at 0 dB. A source is unmeasurable, and fails its track, when the estimator cannot be trusted on it:
    - a blow-up: the real or a rolled reading beyond the amp track's own energy (|share| > 1), which a sane fit
      cannot reach (a source silent for long stretches gives fold weights that blow up where it plays);
    - rolled readings spread as wide as the line itself (max - min >= 10^(thr/10)): the chance level is not known
      well enough to place the take on either side of it;
    - the source plays on fewer than `min_share` of the amp track's playing frames (within 40 dB of its own loudest,
      `data_cleaning.counted_frames`), where the fold weights are fitted on too little of it."""
    from learn import data_cleaning as DC

    min_share = AMP_SOURCE_MIN_SHARE if min_share is None else min_share
    r, n = src["real"], list(src["nulls"])
    if abs(r) > 1.0 or any(abs(v) > 1.0 for v in n):
        why = "blow-up (a held-out reading beyond the amp track's energy)"
    elif n and max(n) - min(n) >= 10 ** (thr / 10):
        why = f"rolled readings spread as wide as the line ({10 * math.log10(max(n) - min(n)):+.1f} dB)"
    elif src["active_share"] < min_share:
        why = f"source plays on {100 * src['active_share']:.0f}% of the amp track's playing frames"
    else:
        why = None
    t = DC.take_db(r, n, 1.0)
    return (None if t is None else min(t, 0.0)), why


def track_bleed(reading, thr=AMP_BLEED_DB, min_share=None):
    """An amp track's bleed from its stored reading (`measure_amp_bleed`): {"bleed_db" (the power sum of the takes at
    or above -40 dB, `amp_bleed_total`; None under it), "takes", "unmeasurable" {source: reason}, "worst" (source, dB)
    or None}."""
    takes, bad = {}, {}
    for s, src in sorted((reading.get("sources") or {}).items()):
        takes[s], why = source_take(src, thr, min_share)
        if why:
            bad[s] = why
    worst = max(((v, s) for s, v in takes.items() if v is not None), default=None)
    return {"bleed_db": amp_bleed_total(takes), "takes": takes, "unmeasurable": bad,
            "worst": None if worst is None else (worst[1], worst[0])}


def amp_status(reading, thr=AMP_BLEED_DB):
    """An amp track's bleed check (A6's line): 'pass' when its bleed reads under thr (None: under the floor), 'fail'
    at or above it, 'unmeasurable' when a source cannot be read (it fails too: only what can be trusted is used),
    'silent' for a silent file, 'not measured' without a reading."""
    if not reading:
        return "not measured"
    if reading.get("silent"):
        return "silent"
    tb = track_bleed(reading, thr)
    if tb["unmeasurable"]:
        return "unmeasurable"
    return "pass" if tb["bleed_db"] is None or tb["bleed_db"] < thr else "fail"


def amp_reason(reading, thr=AMP_BLEED_DB):
    """A short reason for an amp track's verdict, with its numbers."""
    st = amp_status(reading, thr)
    if st in ("not measured", "silent"):
        return st
    tb = track_bleed(reading, thr)
    if st == "unmeasurable":
        return "unmeasurable: " + "; ".join(f"{s} {w}" for s, w in sorted(tb["unmeasurable"].items()))
    b = tb["bleed_db"]
    w = f", worst {tb['worst'][0]} {tb['worst'][1]:+.1f}" if tb["worst"] else ""
    return f"bleed {'under -40' if b is None else f'{b:+.1f}'} dB{w}"


AMP_WHY = {"fail": f"amp track bleed at or above {AMP_BLEED_DB:.0f} dB", "unmeasurable": "amp track bleed unmeasurable",
           "silent": "amp track silent"}


def resolve_blocked(blocked, readings, thr=AMP_BLEED_DB):
    """The user's rule 1 (2026-10-25) on one section. blocked: the active guitars that cannot be rendered ([{"part",
    "activity", "why", "amp_tracks"}], `section_blocked`); readings: {track: reading} (`measure_amp_bleed`). A part is
    represented by all its amp or mic tracks when every one passes the bleed check; a part with none, or with one that
    fails or cannot be measured, is unusable. -> (amp tracks [{"part", "track", "bleed_db"}], unusable parts [{**part,
    "amp", "amp_why"}]); the section's examples are left out when the second is not empty."""
    use, bad = [], []
    for b in blocked:
        tracks = b.get("amp_tracks") or []
        if not tracks:
            bad.append({**b, "amp": [], "amp_why": "no amp track"})
            continue
        amp = []
        for t in tracks:
            r = readings.get(t)
            st = amp_status(r, thr)
            amp.append({"track": t, "status": st, "reason": amp_reason(r, thr),
                        "bleed_db": track_bleed(r, thr)["bleed_db"] if st not in ("not measured", "silent") else None})
        miss = [a["track"] for a in amp if a["status"] == "not measured"]
        if miss:
            raise SystemExit(f"no bleed reading for {miss} (run `amp-bleed` for this stage first)")
        sts = {a["status"] for a in amp}
        if sts == {"pass"}:
            use += [{"part": b["part"], "track": a["track"], "bleed_db": a["bleed_db"]} for a in amp]
        else:
            bad.append({**b, "amp": amp, "amp_why": "; ".join(AMP_WHY[k] for k in ("fail", "unmeasurable", "silent")
                                                               if k in sts)})
    return use, bad


def backing_tracks(x, vocals):
    """The session tracks summed into a self-built backing at the session's balance: the drawn stem variant, then the
    amp or mic tracks that stand for active guitars that cannot be rendered (rule 1, 2026-10-25)."""
    return list(x["stems"]["v" if vocals else "n"]) + [a["track"] for a in x.get("amp_tracks") or []]


def primary_interval(band_iv, sec_iv, n_bands, min_bands=MIN_BANDS):
    """(label, interval): band-clustered with at least min_bands bands; else section-clustered (with 2 bands a
    band-clustered t interval has 1 df: the design's one-band rule, extended by the T1 audit)."""
    if n_bands >= min_bands:
        return "band-clustered", band_iv
    return f"section-clustered (fewer than {min_bands} bands)", sec_iv


def holds_zero(iv):
    return iv is None or iv[0] is None or not (iv[1] > 0 or iv[2] < 0)


def t1_reading(iv):
    """T1's reading, keyed on the primary interval (descriptive; no pass bar)."""
    if not iv or iv[0] is None:
        return "incomplete"
    if holds_zero(iv):
        return "no difference shown between K's and V_sep's stems"
    return ("K's stems are cleaner than V_sep's (the expected cleaning gain); realism: see matched_ratio"
            if iv[1] > 0 else "K's stems are less clean than V_sep's")


def share_below(values, thr=0.0):
    v = [x for x in values if x is not None]
    return sum(1 for x in v if x < thr) / len(v) if v else None


def t1_summary(per, band_of, section_of, keep, min_bands=MIN_BANDS):
    """T1's K - V_sep summary on `keep`: per arm the mean, median and share of stems below 0 dB; the paired
    difference's mean and median, band-clustered and section-clustered intervals, per band, the primary interval
    and the reading. per: {"K": {i: dB}, "V_sep": {i: dB}}."""
    from learn import data_cleaning as DC
    from learn import direct_stems as DS

    keep = sorted(set(keep) & set(per["K"]) & set(per["V_sep"]))
    bands = sorted({band_of[i] for i in keep})
    diff = {i: per["K"][i] - per["V_sep"][i] for i in keep}
    band_iv = DS.paired(per["K"], per["V_sep"], band_of, keep) if keep else None
    sec_iv = DC.section_interval(per["K"], per["V_sep"], section_of, keep) if keep else None
    label, prim = primary_interval(band_iv, sec_iv, len(bands), min_bands)
    by_band = {}
    for i in keep:
        by_band.setdefault(band_of[i], []).append(diff[i])
    return {"examples": len(keep), "bands": bands, "sections": len({section_of[i] for i in keep}), "primary": label,
            "K - V_sep mel SNR (primary)": prim,
            "K - V_sep mel SNR (paired, band-clustered)": band_iv,
            "K - V_sep mel SNR (section-clustered)": sec_iv,
            "K - V_sep mean": statistics.fmean(diff.values()) if keep else None,
            "K - V_sep median": statistics.median(diff.values()) if keep else None,
            "per arm": {n: {"mean": statistics.fmean(per[n][i] for i in keep) if keep else None,
                            "median": statistics.median(per[n][i] for i in keep) if keep else None,
                            "share below 0 dB": share_below([per[n][i] for i in keep])} for n in ("K", "V_sep")},
            "per band": {b: {"n": len(v), "mean": statistics.fmean(v), "median": statistics.median(v)}
                         for b, v in sorted(by_band.items())},
            "reading": t1_reading(prim)}


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


def session_owners(ctx, sd):
    """{DI file: [its own amp tracks]} of a session's inventory DIs."""
    return {pathlib.Path(r["path"]).name: list(r.get("own") or []) for r in ctx.inv.values()
            if r.get("session_dir") == sd}


def section_blocked(ctx, sid, verified, dis_windows, bad_sections, act_cache, scope="all"):
    """The session's other guitars that play in one section (any of their tracks, amp track or DI, against its own
    file's level, `section_activity`) but have no DI that can be rendered here (no DI, a DI T0 does not verify, or a
    window T0 marks other than usable); zero renders. -> [{"part", "activity", "why", "amp_tracks"}] (amp_tracks: the
    part's amp or mic tracks in the session's mix list). The T1 audit left the section's examples out when it was not
    empty (`leave_out_blocked`, kept for `t1-read --subset`); since the user's decision of 2026-10-25 the amp tracks
    stand for them when they pass the bleed check (`apply_rule1`)."""
    sec = ctx.sections[sid]
    rec = ctx.inv[sec["di"]]
    sd = pathlib.Path(rec["session_dir"])
    start = float(sec["start_s"])
    key = ("blocked", sid, scope)
    if key in act_cache:
        return act_cache[key]
    names = sorted(f.name for f in sd.glob("*.wav"))
    parts = session_guitar_parts(names, rec.get("mix"), sec["di"], rec.get("own") or [],
                                 owners=session_owners(ctx, rec["session_dir"]))
    inv_of = {pathlib.Path(r["path"]).name: d for d, r in ctx.inv.items()
              if r.get("session_dir") == rec["session_dir"]}
    from learn import clean_di as CD

    renderable = {}
    for p, tracks in parts.items():
        whys = []
        for t in tracks:
            if not CD.is_guitar_di(t):
                continue
            d = inv_of.get(t)
            if d is None:
                whys.append("DI not in the inventory")
                continue
            if d not in verified:
                whys.append("DI not verified")
                continue
            w = f"{d}@{start:.1f}"
            st = (dis_windows.get(d) or {}).get(w)
            if st == "usable" and w not in bad_sections:
                whys.append(None)
            elif st == "usable":
                whys.append("window in T0's unusable sections")
            else:
                whys.append(f"window {st or 'not measured'}")
        if whys:
            renderable[p] = None if None in whys else "; ".join(sorted(set(whys)))
    files = act_cache.setdefault("files", {})
    activity = {}
    for tracks in parts.values():
        for t in tracks:
            k = ("track", str(sd / t), start)
            if k not in act_cache:
                act_cache[k] = section_activity(sd / t, start, files=files)
            activity[t] = act_cache[k]
    act_cache[key] = [{**b, "amp_tracks": [t for t in parts[b["part"]] if not CD.is_guitar_di(t)]}
                      for b in blocked_parts(parts, activity, renderable, scope=scope)]
    return act_cache[key]


def leave_out_blocked(ctx, rows, verified, dis_windows, bad_sections, act_cache, scope="all"):
    """The T1 audit's rule 1 as first coded (kept only for `t1-read --subset`, which re-reads the stored K mixes,
    built without amp tracks): rows whose section has an active guitar that cannot be rendered are left out of every
    arm. -> (kept rows, left-out records)."""
    kept, out = [], {}
    for r in rows:
        b = section_blocked(ctx, r["section"], verified, dis_windows, bad_sections, act_cache, scope)
        if b:
            o = out.setdefault(r["section"], {"section": r["section"], "band": r["band"], "reason": LEFT_OUT_ACTIVE,
                                              "guitars": b, "examples": 0})
            o["examples"] += 1
        else:
            kept.append(r)
    return kept, [out[s] for s in sorted(out)]


def print_left_out(left, reason=LEFT_OUT_ACTIVE):
    """Print the left-out examples, once per reason (records carry their own reason; `reason` names the rule when
    nothing is left out)."""
    if not sum(x["examples"] for x in left):
        print(f"left out: none ({reason})", flush=True)
        return
    for rsn in sorted({x.get("reason", reason) for x in left}):
        xs = [x for x in left if x.get("reason", reason) == rsn]
        bands, why = {}, {}
        for x in xs:
            bands[x["band"]] = bands.get(x["band"], 0) + x["examples"]
            for w in {g.get("amp_why") or g["why"] for g in x["guitars"]}:
                why[w] = why.get(w, 0) + x["examples"]
        print(f"left out: {sum(x['examples'] for x in xs)} examples in {len(xs)} sections ({rsn}); by band "
              + ", ".join(f"{b} {k}" for b, k in sorted(bands.items())) + "; examples per blocking reason "
              + ", ".join(f"{w} {k}" for w, k in sorted(why.items())), flush=True)


def cleaning_clash(amp_tracks, scan_row):
    """The added amp tracks that the cleaning scan removed from the section's backing or confirmed as another take of
    the target's part (`data_cleaning.section_decision`, `same_part`): they must never come back in a self-built
    backing. A section the scan has no row for clashes as a whole. -> sorted tracks (or ['no cleaning scan row'])."""
    from learn import data_cleaning as DC

    if not amp_tracks:
        return []
    if scan_row is None:
        return ["no cleaning scan row"]
    removed = set(DC.section_decision(scan_row)[0]) | set(scan_row.get("removed") or [])
    same = {t for t, v in (scan_row.get("tracks") or {}).items() if v.get("same_part")}
    return sorted({a["track"] for a in amp_tracks} & (removed | same))


def section_session(ctx, sid):
    return ctx.inv[ctx.sections[sid]["di"]]["session_dir"]


def blocked_by_section(ctx, rows, verified, dis_windows, bad_sections, act_cache):
    """{section: its active guitars that cannot be rendered} over the rows' sections (`section_blocked`)."""
    return {sid: section_blocked(ctx, sid, verified, dis_windows, bad_sections, act_cache)
            for sid in sorted({r["section"] for r in rows})}


def needed_amp_tracks(ctx, blocked):
    """{session dir: [amp or mic track]}: every track that stands for an active guitar that cannot be rendered."""
    out = {}
    for sid, b in blocked.items():
        for p in b:
            out.setdefault(section_session(ctx, sid), set()).update(p.get("amp_tracks") or [])
    return {sd: sorted(v) for sd, v in sorted(out.items()) if v}


def amp_bleed_path(root, sd):
    import hashlib

    return root / AMP_BLEED_DIR / f"{pathlib.Path(sd).name}-{hashlib.sha1(str(sd).encode()).hexdigest()[:8]}.json"


def load_amp_bleed(root, needed):
    """{session dir: {track: reading}} of the needed tracks; refuses when one has no reading under today's measure
    and threshold (run `amp-bleed`)."""
    out, miss = {}, []
    for sd, tracks in needed.items():
        rec = _load(amp_bleed_path(root, sd)) or {}
        ok = rec.get("measure") == AMP_BLEED_MEASURE and rec.get("session_dir") == sd
        have = rec.get("tracks") or {} if ok else {}
        miss += [f"{pathlib.Path(sd).name}/{t}" for t in tracks if t not in have]
        out[sd] = {t: have[t] for t in tracks if t in have}
    if miss:
        raise SystemExit(f"{len(miss)} amp tracks have no bleed reading (e.g. {miss[:3]}): run `amp-bleed` for this "
                         "stage first")
    return out


def bleed_sources(files):
    """The bleed check's sources: the session's non-guitar tracks (drums, room, vocals, bass, keys and the rest), as
    the stem scan classifies them (`verify_tracks.guitar_sources`). Never another guitar track: A6 reads
    other-instrument bleed, and in these sessions guitars double or play the same riffs, which the estimator reads as
    a coherent path (DT pairs read each other at -24 to -27 dB, 2026-10-25)."""
    allg = set(V.guitar_sources(files))
    return [f for f in files if f not in allg]


def source_raw(S, Y):
    """One source's raw reading in one amp track (STFTs on `data_cleaning.band_bins`): the real and rolled held-out
    explained energies (`data_cleaning.SessionMeter`, the nulls' rolls of `TakeReader`) as shares of the amp track's
    energy on its playing frames, and the share of those frames where the source plays (within 40 dB of its own
    loudest frame). -> {"real", "nulls", "active_share"} (None for a silent amp track)."""
    import numpy as np

    from learn import data_cleaning as DC

    tr = DC.TakeReader(S, Y)
    if tr.ref <= 0 or not tr.counted.any():
        return None
    vals = []
    for roll in [0] + tr.rolls:
        meter = DC.SessionMeter(np.roll(S, roll, axis=1) if roll else S, tr.counted, tr.band)
        vals.append(meter.explained(Y))
        del meter
    act = DC.counted_frames(S)
    return {"real": vals[0] / tr.ref, "nulls": [v / tr.ref for v in vals[1:]],
            "active_share": float(np.mean(act[tr.counted]))}


def measure_amp_bleed(sd, tracks, log=print):
    """Each amp or mic track's raw other-instrument bleed readings (zero renders, CPU), one reading per session (not
    per section or half: a recorded leakage path does not change between sections), by the cleaning plan's take
    estimator with the roles of A6's bleed: each non-guitar track of the session (`bleed_sources`) is the source and
    the amp track the reference (`source_raw`). The verdict is drawn from the stored raw values (`track_bleed`,
    `amp_status`). Injection-checked in these roles on synthetic signals (tests) and on Hollow Ground's and Dark Ride's
    amp tracks (the design).
    -> {track: {"silent", "sources": {source: raw}}}."""
    import gc

    import numpy as np

    from learn import data_cleaning as DC

    sd = pathlib.Path(sd)
    files = sorted(f.name for f in sd.glob("*.wav"))
    dur = max(DC.file_seconds(sd / f) for f in files)
    idx, _ = DC.band_bins()
    srcs = bleed_sources(files)
    Ys = {t: DC.stft(DC.load_window(sd / t, 0.0, dur))[idx] for t in tracks}
    silent = {t for t, Y in Ys.items() if not DC.counted_frames(Y).any()}
    out = {t: {"silent": t in silent, "sources": {}} for t in tracks}
    t0 = time.time()
    for m, s in enumerate(srcs):
        want = [t for t in tracks if t not in silent]
        if not want:
            continue
        S = DC.stft(DC.load_window(sd / s, 0.0, dur))[idx]
        if not (np.abs(S) > 0).any():                       # a silent file cannot leak
            continue
        for t in want:
            raw = source_raw(S, Ys[t])
            if raw is not None:
                out[t]["sources"][s] = raw
        del S
        gc.collect()
        log(f"  {sd.name[:40]}: source {m + 1}/{len(srcs)} {s} ({time.time() - t0:.0f} s)")
    return out


def apply_rule1(ctx, root, rows, verified, dis_windows, bad_sections, act_cache, scan=None):
    """The user's rule 1 (2026-10-25) at plan time: in each row's section, every active guitar that cannot be
    rendered is represented by its amp or mic tracks when each passes the bleed check (`resolve_blocked`); otherwise
    the row is left out of every arm (LEFT_OUT_NO_AMP), with the guitars, tracks and readings recorded. An added amp
    track that the cleaning scan removed or confirmed as the target's other take leaves the row out too
    (LEFT_OUT_OWN_TAKE; scan: {section: scan row}, `data_cleaning.scan_rows`).
    -> (kept rows, left-out records, {section: amp tracks})."""
    blocked = blocked_by_section(ctx, rows, verified, dis_windows, bad_sections, act_cache)
    readings = load_amp_bleed(root, needed_amp_tracks(ctx, blocked))
    res = {}
    for sid, b in blocked.items():
        use, bad = resolve_blocked(b, readings.get(section_session(ctx, sid)) or {})
        clash = cleaning_clash(use, (scan or {}).get(sid)) if not bad else []
        res[sid] = (use, bad, clash)
    kept, out = [], {}
    for r in rows:
        use, bad, clash = res[r["section"]]
        if bad or clash:
            o = out.setdefault(r["section"], {
                "section": r["section"], "band": r["band"], "reason": LEFT_OUT_NO_AMP if bad else LEFT_OUT_OWN_TAKE,
                "guitars": bad or [{"part": t, "why": LEFT_OUT_OWN_TAKE} for t in clash], "examples": 0})
            o["examples"] += 1
        else:
            kept.append(r)
    amp_of = {sid: use for sid, (use, bad, clash) in res.items() if use and not bad and not clash}
    return kept, [out[s] for s in sorted(out)], amp_of


def print_amp_use(recipes):
    with_amp = [x for x in recipes if x.get("amp_tracks")]
    parts = {}
    for x in with_amp:                                  # a part is per session (ElecGtr2 in two sessions is two parts)
        sess = pathlib.PurePosixPath(x["di"]).parent.name
        for a in x["amp_tracks"]:
            parts.setdefault(f"{sess}/{a['part']}", set()).add(a["track"])
    print(f"amp tracks (rule 1, 2026-10-25): {len(with_amp)} of {len(recipes)} examples carry the session's own amp "
          f"tracks for {len(parts)} parts" + (": " + ", ".join(f"{p} ({len(t)})" for p, t in sorted(parts.items()))
                                               if parts else ""), flush=True)


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


def section_candidates(ctx, sid, verified, dis_windows, bad_sections, act_cache):
    """(candidates, {di: activity}): the section's other trusted DIs whose window T0 measured and found usable, with
    their share of playing frames (`section_activity`); `pick_others` takes the active ones, at most MAX_OTHERS."""
    sec = ctx.sections[sid]
    sd = ctx.inv[sec["di"]]["session_dir"]
    start = float(sec["start_s"])
    cands = []
    for d in session_dis(ctx, sd, verified):              # other guitars: only windows T0 measured and found usable
        if d == sec["di"]:
            continue
        w = f"{d}@{start:.1f}"
        st = (dis_windows.get(d) or {}).get(w)
        if st is None:
            raise SystemExit(f"{sid}: {w} was never measured by T0 (rerun verify_tracks dis and lists)")
        if st == "usable" and w not in bad_sections:
            cands.append(d)
    files = act_cache.setdefault("files", {})
    for d in cands:
        key = (d, start)
        if key not in act_cache:
            act_cache[key] = section_activity(ctx.inv[d]["path"], start, files=files)
    return cands, {d: act_cache[(d, start)] for d in cands}


def over_cap(cands, activity, max_n=MAX_OTHERS, active_min=ACTIVE_MIN):
    """The renderable other guitars that play in a section beyond the cap: `pick_others` would drop them silently, so
    the section's examples are left out instead (LEFT_OUT_CAP). -> sorted DIs past the cap (empty: within it)."""
    act = sorted((d for d in cands if (activity.get(d) or 0.0) >= active_min), key=lambda d: (-activity[d], d))
    return sorted(act[max_n:])


def apply_cap(ctx, rows, verified, dis_windows, bad_sections, act_cache, max_n=MAX_OTHERS):
    """Rows whose section has more renderable active guitars than the cap are left out of every arm (before any draw).
    -> (kept rows, left-out records)."""
    kept, out, memo = [], {}, {}
    for r in rows:
        sid = r["section"]
        if sid not in memo:
            memo[sid] = over_cap(*section_candidates(ctx, sid, verified, dis_windows, bad_sections, act_cache), max_n)
        if memo[sid]:
            o = out.setdefault(sid, {"section": sid, "band": r["band"], "reason": LEFT_OUT_CAP, "examples": 0,
                                     "guitars": [{"part": d.split("/")[-1], "why": LEFT_OUT_CAP} for d in memo[sid]]})
            o["examples"] += 1
        else:
            kept.append(r)
    return kept, [out[s] for s in sorted(out)]


def example_recipe(ctx, r, verified, verified_stems, act_cache, bad_sections=frozenset(), dis_windows=None,
                   amp_tracks=()):
    """One example's self-built recipe (plan (c)), zero renders. r: a part C row; dis_windows: {di: {window id:
    status}} from T0's lists (an other guitar's window must have been measured and be usable); amp_tracks: the
    section's amp tracks that stand for active guitars that cannot be rendered (`apply_rule1`)."""
    dis_windows = dis_windows or {}
    from learn import data_cleaning as DC
    from learn import direct_stems as DS
    from learn import pretrain_set as PS

    sec = ctx.sections[r["section"]]
    rec = ctx.inv[sec["di"]]
    sd = rec["session_dir"]
    cands, activity = section_candidates(ctx, r["section"], verified, dis_windows, bad_sections, act_cache)
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
            "stems": {"v": withv, "n": nov}, "amp_tracks": [dict(a) for a in amp_tracks],
            "vocals": bool(v and withv != nov),
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


def stage_rows(ctx, tr, stage, limit=0):
    """The stage's candidate rows before rule 1 (zero renders): T1's K examples (V_sep's rows outside Kimock and
    Swatkins whose DIs T0 puts in K, with a stored truth render); T2's trusted-pool rows outside Eggy, then the Eggy
    rows SYN-E may swap in, each on a verified DI in a section T0 lets a mix use. -> (rows, Eggy rows)."""
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS

    verified = verified_dis(tr)
    bad_secs = unusable(tr)
    if stage == "t1":
        truth = G.gate_rows(DS.ROOT / "gate", "truth")
        k_dis = set(tr["k_dis"])
        rows = [r for r in ctx.parts["vsep"] if not ctx.tag[r["i"]] and r["band"] not in K_OUT_BANDS
                and ctx.sections[r["section"]]["di"] in k_dis and r["section"] not in bad_secs
                and r["i"] in truth and not truth[r["i"]].get("refused")]
        return rows[:limit or None], []
    ses, _ = ses_rows(ctx)
    cand = [r for i, r in sorted(ses.items()) if r["band"] != EGGY and ctx.sections[r["section"]]["di"] in verified
            and r["section"] not in bad_secs]
    eggy = [r for r in ctx.pool if r["band"] == EGGY and not r.get("early_stop")
            and ctx.sections[r["section"]]["di"] in verified and r["section"] not in bad_secs]
    return cand, eggy


def cmd_plan(args):
    """The examples and their recipes (zero renders, CPU): T1's K, or T2's pilot, early-stopping set and SYN-E swap.
    Rule 1 (the user, 2026-10-25) first: an active guitar that cannot be rendered is its amp tracks (read by
    `amp-bleed`), or the example is left out of every arm before any draw; so is an example with more renderable
    active guitars than the cap (`apply_cap`)."""
    from learn import data_cleaning as DC
    from learn import direct_stems as DS

    V.require_real(args)
    root = V.out_root(args)
    tr = load_lists(root, args.smoke)
    verified = verified_dis(tr)
    wins = windows_of(tr)
    bad_secs = unusable(tr)
    ctx = DS.Ctx(quiet=True)
    act = {}
    rows, eggy = stage_rows(ctx, tr, args.stage, args.limit)
    scan = DC.scan_rows(DC.OUT)                         # the cleaning scan (read only): rule 1's own-take guard
    if not scan:
        raise SystemExit(f"the cleaning scan's rows are missing ({DC.OUT / 'scan'})")
    rows, left, amp_of = apply_rule1(ctx, root, rows, verified, wins, bad_secs, act, scan)   # every arm drops them
    rows, left_cap = apply_cap(ctx, rows, verified, wins, bad_secs, act)
    left = sorted(left + left_cap, key=lambda x: x["section"])
    print_left_out(left, LEFT_OUT_NO_AMP)
    if args.stage == "t1":
        recipes = [example_recipe(ctx, r, verified, tr["stems"], act, bad_secs, wins, amp_of.get(r["section"], ()))
                   for r in rows]
        rec = {"plan": PLAN, "stage": "t1", "smoke": bool(args.smoke), "k_out_bands": list(K_OUT_BANDS),
               "examples": recipes, "renders_others": sum(len(x["others"]) for x in recipes),
               "renders_targets": 0, "separations": len(recipes)}
    else:
        cand = rows
        by_band = {}
        for r in cand:
            by_band.setdefault(r["band"], set()).add(r["section"])
        es_sec = set(es_sections(by_band))
        es = [r for r in cand if r["section"] in es_sec]
        if len(es) > ES_CAP:
            es = sorted(random.Random(ES_SEED).sample(es, ES_CAP), key=lambda r: r["i"])
        rest = [r for r in cand if r["section"] not in es_sec]
        print("T2 candidates outside early stopping, by band: "
              + ", ".join(f"{b} {sum(1 for r in rest if r['band'] == b)}" for b in sorted({r["band"] for r in rest}))
              + f" (total {len(rest)} in {len({r['section'] for r in rest})} sections; early stopping {len(es)} in "
              f"{len(es_sec)} sections; the pilot needs {N_PILOT})", flush=True)
        pilot = stratified_by_band(rest, N_PILOT, PILOT_SEED)
        eggy, left_e, amp_e = apply_rule1(ctx, root, eggy, verified, wins, bad_secs, act, scan)
        eggy, left_ec = apply_cap(ctx, eggy, verified, wins, bad_secs, act)
        if left_e or left_ec:
            print(f"Eggy (SYN-E's swap pool): {sum(x['examples'] for x in left_e + left_ec)} left out", flush=True)
        left = sorted(left + left_e + left_ec, key=lambda x: x["section"])
        amp_of.update(amp_e)
        try:
            kept, out, eg = eggy_swap([r["i"] for r in pilot], eggy)
            syn_e = {"kept": kept, "swapped_out": out, "eggy": eg}
        except SystemExit as e:                     # e.g. every Eggy DI heard processed (2026-10-23): SYN-E cannot run
            syn_e, eg = {"refused": str(e), "kept": [], "swapped_out": [], "eggy": []}, []
        rows_by = {r["i"]: r for r in ctx.pool}
        need = sorted({r["i"] for r in pilot} | {r["i"] for r in es} | set(eg))
        if args.limit:
            need = need[:args.limit]
        recipes = [example_recipe(ctx, rows_by[i], verified, tr["stems"], act, bad_secs, wins,
                                  amp_of.get(rows_by[i]["section"], ())) for i in need]
        rec = {"plan": PLAN, "stage": "t2", "smoke": bool(args.smoke), "seeds": {"pilot": PILOT_SEED, "es": ES_SEED,
               "eggy": EGGY_SEED, "others": OTHER_SEED}, "pilot": [r["i"] for r in pilot], "es": [r["i"] for r in es],
               "es_sections": sorted(es_sec), "syn_e": syn_e,
               "bands": {b: sum(1 for r in pilot if r["band"] == b) for b in sorted({r["band"] for r in pilot})},
               "examples": recipes, "renders_targets": len(recipes),
               "renders_others": sum(len(x["others"]) for x in recipes), "separations": len(recipes)}
    rec["pan_prior"] = PAN_PRIOR
    rec["left_out"] = left
    rec["left_out_examples"] = sum(x["examples"] for x in left)
    rec["amp_bleed_db"] = AMP_BLEED_DB
    print_amp_use(rec["examples"])
    rec["lists_sha256"] = lists_sha(root)
    stale = stale_rows(_load(plan_path(root, args.stage)), rec, rows_of(root, args.stage, "render"))
    if stale:
        raise SystemExit(f"{len(stale)} examples were rendered under another recipe (e.g. {stale[:3]}): move "
                         f"{stage_root(root, args.stage)}/rows and its audio aside before re-planning")
    bare = [x for x in rec["examples"] if not x["others"] and not x["stems"]["v"] and not x["stems"]["n"]
            and not x["amp_tracks"]]
    if bare:
        print(f"{len(bare)} examples have no other guitar, no stem and no amp track (build refuses them): by band "
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


def cmd_amp_bleed(args):
    """Rule 1's bleed check (zero renders, CPU; before `plan`): every amp or mic track that would stand for an active
    guitar that cannot be rendered in the stage's candidate sections, read once per session (`measure_amp_bleed`) and
    stored in root/amp-bleed/; a shard reads every n-th session. Readings under today's measure are kept."""
    from learn import direct_stems as DS

    V.require_real(args)
    root = V.out_root(args)
    tr = load_lists(root, args.smoke)
    ctx = DS.Ctx(quiet=True)
    rows, eggy = stage_rows(ctx, tr, args.stage, args.limit)
    blocked = blocked_by_section(ctx, rows + eggy, verified_dis(tr), windows_of(tr), unusable(tr), {})
    need = needed_amp_tracks(ctx, blocked)
    k, n = args.shard
    print(f"amp-bleed {args.stage}: {sum(len(v) for v in need.values())} amp tracks in {len(need)} sessions; shard "
          f"{k}/{n}", flush=True)
    for m, (sd, tracks) in enumerate(need.items()):
        if m % n != k:
            continue
        path = amp_bleed_path(root, sd)
        prev = _load(path) or {}
        if prev and (prev.get("measure") != AMP_BLEED_MEASURE or prev.get("session_dir") != sd):
            raise SystemExit(f"{path} was read under another measure: move it aside by hand (no silent resume)")
        have = dict(prev.get("tracks") or {})
        todo = [t for t in tracks if t not in have]
        if todo:
            t0 = time.time()
            have.update(measure_amp_bleed(sd, todo))
            _save(path, {"plan": PLAN, "smoke": bool(args.smoke), "measure": AMP_BLEED_MEASURE, "session_dir": sd,
                         "threshold_db": AMP_BLEED_DB, "tracks": have, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            print(f"{pathlib.Path(sd).name}: {len(todo)} read in {time.time() - t0:.0f} s", flush=True)
        for t in tracks:
            print(f"  {pathlib.Path(sd).name[:40]} {t}: {amp_status(have[t])} ({amp_reason(have[t])})", flush=True)
    print(f"AMP-BLEED DONE {k}/{n}")


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


def place_other(row, acc, y, ly, level, level_from, o, amp, settings):
    """One other guitar's render into its example (rule 2, T1 audit): a render below RENDER_FLOOR_LUFS, or silent,
    refuses the example (row["refused"]), never lifted to its level; otherwise it is scaled to its level, pan-folded
    and added. -> the example's accumulated other guitars."""
    why = near_silent(ly)
    if why:
        row["refused"] = why
        row["others"].append({"di": o["di"], "amp": amp, "render_lufs": ly, "refused": why})
        return acc
    gain = 10 ** ((level - ly) / 20) * pan_fold(o["pan"])
    row["others"].append({"di": o["di"], "dt": o["dt"], "amp": amp, "settings": settings, "level_lufs": level,
                          "level_from": level_from, "render_lufs": ly, "pan": o["pan"], "gain_db": 20 * math.log10(gain)})
    return acc + y * gain


def refusal_counts(rows):
    """{reason: examples} of refused rows (render or build rows)."""
    out = {}
    for r in rows:
        if r.get("refused"):
            out[r["refused"]] = out.get(r["refused"], 0) + 1
    return dict(sorted(out.items()))


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
    written = []
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
                    if rows[i].get("refused"):                   # refused by an earlier render: no more renders
                        continue
                    lv, src = levels[di_id]
                    if lv is None:
                        rows[i]["others"].append({"di": di_id, "left_out": "no level"})
                        continue
                    if di_id not in di_cache:
                        di_cache = {di_id: B.measure(PS.section_audio(ctx.inv[di_id]["path"], sec["start_s"])).astype(np.float32)}
                    y = primer.render((f"{sid}|{di_id}", amp), di_cache[di_id], sel, st)
                    y = (y.mean(axis=1) if y.ndim == 2 else y)[trim0:trim1]
                    acc[i] = place_other(rows[i], acc[i], y, lufs_or_none(y), lv, src, o, amp, LO.sdict(st))
                for x in xs:
                    rw = rows[x["i"]]
                    if not rw.get("refused"):
                        sc, sha = G.write_flac(flac_path(root, args.stage, x["i"], "others"), acc[x["i"]], PS.SR)
                        rw["others_file"] = {"scale": sc, "sha256": sha}
                    rw["renders_so_far"] = primer.renders
                    written.append(rw)
                    fh.write(json.dumps(rw) + "\n")
                fh.flush()
                print(f"section {m + 1}/{len(by_sec)} {sid[-50:]}: {len(xs)} examples; renders {primer.renders} "
                      f"({primer.primes} priming); {(time.time() - t_start) / (m + 1):.0f} s per section", flush=True)
    finally:
        rr.close()
    print(f"refused in this shard, by reason: {refusal_counts(written) or 'none'}")
    print(f"RENDER DONE {k}/{n}: {primer.renders} renders ({primer.primes} priming)")


# --- build (MSST; separations) -----------------------------------------------------------------------------------

class Stems:
    """A section's stems summed at the session's balance (cached per section and vocal variant), folded to mono as a
    centred source: a mono file by pan_fold(0); a stereo file is folded already ((L + R) / 2 on loading)."""

    def __init__(self, ctx):
        self.ctx, self.cache = ctx, {}

    def get(self, sid, tracks):
        import numpy as np
        import soundfile as sf

        from learn import pretrain_set as PS

        key = (sid, tuple(tracks))
        if key not in self.cache:
            sec = self.ctx.sections[sid]
            sess = pathlib.Path(self.ctx.inv[sec["di"]]["session_dir"])
            b = np.zeros(int(round((PS.SEC_S + PS.TRIM_S) * PS.SR)))
            for t in tracks:
                fold = pan_fold(0.0) if sf.info(str(sess / t)).channels == 1 else 1.0
                b += PS.section_audio(sess / t, sec["start_s"]) * fold
            if len(self.cache) >= 4:
                self.cache.pop(next(iter(self.cache)))
            self.cache[key] = b[int(PS.TRIM_S * PS.SR):]
        return self.cache[key]


def self_built_mix(y, others, stems_audio, x):
    """The mix of one example (plan (c)): backing = other guitars (already levelled and pan-folded) + stems (already
    folded as centred sources by `Stems`); the backing set against the target by the drawn ratio, the drawn loudness,
    and the drawn mastering. -> (mix, gains {gb, ga}, backing LUFS)."""
    from learn import direct_stems as DS
    from learn import song_aug as SA

    b = others + stems_audio
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
            st = stems.get(x["section"], backing_tracks(x, voc))   # stems + rule 1's amp tracks, as recorded
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

def t1_subset(ctx, root, plan, tr, scope="all"):
    """The zero-render re-read's subset (`t1-read --subset`): the plan's examples less those rule 1 (an active guitar
    that cannot be rendered, under today's lists) and rule 2 (any stored other-guitar render below the floor, or
    silent) would have left out. -> (kept ids, {"rule 1": n, "rule 2": n, "either": n})."""
    ids = [x["i"] for x in plan["examples"]]
    rows = [{"i": x["i"], "section": x["section"], "band": x["band"]} for x in plan["examples"]]
    _, left = leave_out_blocked(ctx, rows, verified_dis(tr), windows_of(tr), unusable(tr), {}, scope)
    r1 = {x["i"] for x in rows if x["section"] in {o["section"] for o in left}}
    r2 = set(rule2_examples(rows_of(root, "t1", "render")))
    gone = r1 | (r2 & set(ids))
    return [i for i in ids if i not in gone], {"rule 1": len(r1), "rule 2": len(r2 & set(ids)), "either": len(gone),
                                               "rule 1 sections": left}


def cmd_t1_read(args):
    """T1's read: per K example the stem's mel SNR (and contamination) against its truth render, K's self-built stem
    against V_sep's stored stem of the same example and draws (paired; band-clustered with at least MIN_BANDS bands,
    else section-clustered, primary; the other beside); means and medians, the share of stems below 0 dB per arm, per
    band and by guitar-to-backing ratio; V-real's stored crop stems against their amp tracks beside.
    --subset rules|rules-di: the T1 audit's zero-render re-read of the stored rows under rules 1 and 2 (rules-di, a
    diagnostic: rule 1 on parts that have a DI only). It writes nothing and reads stale lists with a warning."""
    import numpy as np

    from learn import data_cleaning as DC
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pretrain_set as PS

    V.require_real(args)
    root = V.out_root(args)
    subset = getattr(args, "subset", None)
    plan = _load(plan_path(root, "t1"))
    if plan:
        if subset and plan.get("lists_sha256") != lists_sha(root):
            print("WARNING: T0's lists changed since T1's plan (read-only re-read; re-plan before any T1 run)",
                  flush=True)
        else:
            check_lists(root, plan, args.smoke)
    built = {i: r for i, r in rows_of(root, "t1", "build").items() if not r.get("refused")}
    allrows = rows_of(root, "t1", "build")
    if not plan or (any(x["i"] not in allrows for x in plan["examples"]) and not args.smoke):
        raise SystemExit("K is not fully built (run render and build --stage t1)")
    planned = {x["i"] for x in plan["examples"]}
    print(f"T1 refused (every arm drops them), by reason: "
          f"{refusal_counts(r for i, r in allrows.items() if i in planned) or 'none'}", flush=True)
    truth = G.gate_rows(DS.ROOT / "gate", "truth")
    tr = load_lists(root, args.smoke)
    only = None
    if subset:
        only, counts = t1_subset(DS.Ctx(quiet=True), root, plan, tr, "di" if subset == "rules-di" else "all")
        print(f"subset {subset}: {len(plan['examples'])} planned; rule 1 leaves out {counts['rule 1']} "
              f"({LEFT_OUT_ACTIVE}), rule 2 {counts['rule 2']} ({NEAR_SILENT}, floor {RENDER_FLOOR_LUFS} LUFS), "
              f"either {counts['either']}; {len(only)} kept", flush=True)
        print_left_out(counts["rule 1 sections"])
        only = set(only)
    per = {"K": {}, "V_sep": {}}
    cont = {"K": {}, "V_sep": {}}
    band_of, section_of, ratio_of = {}, {}, {}
    for x in plan["examples"]:
        i = x["i"]
        if i not in built or (only is not None and i not in only):
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
    if not keep:
        print("T1: no examples to read")
        return
    res = t1_summary(per, band_of, section_of, keep)
    res["K - V_sep contamination (paired)"] = DS.paired(cont["K"], cont["V_sep"], band_of, keep)
    res["levels"] = {n: PS.band_t_interval(PS.by_band({i: per[n][i] for i in keep}, band_of)) for n in per}
    res["by_ratio"] = {}
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
    # coded or approved, so T1 changes nothing in T2 by itself. The reading keys on the primary interval only.
    print(json.dumps({k: v for k, v in res.items() if k != "v_real"}, indent=1, default=float))
    pa = res["per arm"]
    print(f"K - V_sep: mean {res['K - V_sep mean']:+.2f} dB, median {res['K - V_sep median']:+.2f} dB; primary "
          f"{res['primary']} {fmt_iv(res['K - V_sep mel SNR (primary)'])}; band-clustered "
          f"{fmt_iv(res['K - V_sep mel SNR (paired, band-clustered)'])}; n {res['examples']} in {len(res['bands'])} "
          f"bands, {res['sections']} sections")
    print("stems below 0 dB: " + ", ".join(f"{n} {100 * pa[n]['share below 0 dB']:.1f}% (mean {pa[n]['mean']:+.2f}, "
                                           f"median {pa[n]['median']:+.2f})" for n in ("K", "V_sep")))
    if subset:
        print(f"T1 (subset {subset}, nothing written): {res['reading']}")
        return
    out = {"plan": PLAN, "stage": "T1", "smoke": bool(args.smoke), "results": res, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(stage_root(root, "t1") / "read.json", out)
    print(f"T1: {res['reading']}")


def fmt_iv(iv):
    if not iv or iv[0] is None:
        return "n/a"
    return f"{iv[0]:+.2f} [{iv[1]:+.2f}, {iv[2]:+.2f}] ({iv[3]} clusters)"


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
    train_rows = {}
    for arm in arms_of(plan):
        nets, recs = load_arm(root, arm, args.smoke)
        files = arm_files(root, plan, arm, ses_files)
        tr_rows, es_rows = arm_rows(ctx, plan, arm, files, refused)
        train_rows[arm] = tr_rows
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
    out["constant_arm"] = constant_arm(train_rows["SYN"])
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save(stage_root(root, "t2") / "fit.json", out)


def constant_arm(rows):
    """The song-blind constant as an answer per (amp, base class): the step 3 sound gate's constant
    (`direct_sound_gate.constant_answers`: continuous medians of the audible labels, switches by majority, mics by the
    most frequent) over the SYN arm's training rows (SES trains on the same examples and labels)."""
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import song_model as SM

    const = G.constant_answers(rows, DS.encode_audible, len(SM.CONT), len(SM.SW), len(SM.CAT))
    return {"from": "the SYN arm's training labels (SES's are the same)", "rows": len(rows),
            "constant": G.const_json(const)}


def constant_settings(fit, amp, cls, S):
    """The constant arm's settings for one direction (the gate's `_answer_settings` on the cell's labelled dims)."""
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS

    c = G.const_from_json(fit["constant"])[(amp, cls)]
    return G._answer_settings(amp, S, {"cont": c["cont"], "sw": c["sw"], "mics": c["mics"]}, DS.masks(amp, cls))


def t2_contrasts(arms):
    """{name: (a, b)} of T2's V-real contrasts: the primary SYN - SES first, then the arms against S and against the
    song-blind constant (does an arm read the song, or only the constant's pull?)."""
    pairs = {"SYN - SES": ("SYN", "SES"), "SYN-E - SYN": ("SYN-E", "SYN"), "SES - S": ("SES", "S"),
             "SYN - S": ("SYN", "S"), "SYN-E - S": ("SYN-E", "S"), "SES - constant": ("SES", CONST_ARM),
             "SYN - constant": ("SYN", CONST_ARM), "constant - S": (CONST_ARM, "S")}
    return {k: (a, b) for k, (a, b) in pairs.items() if a in arms and (b in arms or b == "S")}


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
    nb = len({band_of[i] for i in ids})
    res["primary"] = primary_interval(None, None, nb)[0]
    if nb < MIN_BANDS:                  # 1-2 bands: a band interval is +-inf or 1 df (T1's rule, as there): primary
        section_of = {x["i"]: x["section"] for x in k_plan["examples"]}
        res[f"section-clustered (fewer than {MIN_BANDS} bands: primary)"] = {
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
    cfit = (_load(stage_root(root, "t2") / "fit.json") or {}).get("constant_arm")
    if not cfit:
        raise SystemExit("fit.json has no constant arm: rerun `fit`")
    preds[CONST_ARM] = {}
    for slug, amp, search, held in dirs:
        _, S = ms[amp][A.f_part(slug)["gain_class"]]
        preds[CONST_ARM][f"{slug}|{amp}|{search}"] = {
            "settings": LO.sdict(constant_settings(cfit, amp, A.f_part(slug)["gain_class"], S)), "held": held, "diag": {}}
    arms = tuple(arms) + (CONST_ARM,)
    _save(stage_root(root, "t2") / "vreal" / "predictions.json",
          {"plan": PLAN, "smoke": bool(args.smoke), "directions": len(dirs), "arms": list(arms), "predictions": preds,
           "inputs": {s: v["hashes"] for s, v in inputs.items()}, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"VREAL PREDICT: {len(dirs)} directions x {len(arms)} arms ({', '.join(arms)})")


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
    and each arm - S and - the song-blind constant beside (rows: all, F-song, without the MUSDB18 songs; per class
    and amp in report.json); E on K;
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
    for name, (a, b) in t2_contrasts(arms).items():
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
    ap.add_argument("cmd", choices=("amp-bleed", "plan", "render", "build", "t1-read", "train", "fit", "e-on-k",
                                    "vreal-predict", "vreal-render", "report"))
    ap.add_argument("--stage", choices=("t1", "t2"), default="t1")
    ap.add_argument("--shard", type=V.parse_shard, default=(0, 1))
    ap.add_argument("--device", default="mps")
    ap.add_argument("--order", choices=("asc", "desc"), default="asc")
    ap.add_argument("--arm", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--subset", choices=("rules", "rules-di"), default=None,
                    help="t1-read only: the T1 audit's zero-render re-read under rules 1-2 (writes nothing)")
    args = ap.parse_args(argv)
    if args.subset and args.cmd != "t1-read":
        raise SystemExit("--subset is for t1-read")
    if args.limit and not args.smoke:
        raise SystemExit("--limit is for smoke runs (with --smoke and --out)")
    {"amp-bleed": cmd_amp_bleed, "plan": cmd_plan, "render": cmd_render, "build": cmd_build, "t1-read": cmd_t1_read, "train": cmd_train,
     "fit": cmd_fit, "e-on-k": cmd_e_on_k, "vreal-predict": cmd_vreal_predict, "vreal-render": cmd_vreal_render,
     "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
