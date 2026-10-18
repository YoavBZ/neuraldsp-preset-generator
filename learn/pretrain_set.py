"""A labelled pre-training render set, part C (`docs/pretrain-set-plan.md`). Development only.

    .venv/bin/python -m learn.pretrain_set pool                 # the section pool and split (zero renders)
    .venv/bin/python -m learn.pretrain_set backings             # session backings: mels, leakage (zero renders)
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.pretrain_set render --shard i/3 --n 40000
    .venv/bin/python -m learn.pretrain_set recheck              # 30 audit re-renders against the stored audio
    $TORCH_PY -m learn.pretrain_set curve --n 40000             # the learning curve (MPS)
    .venv/bin/python -m learn.pretrain_set decide --n 40000     # prints DECISION EXTEND or DECISION STOP
    .venv/bin/python -m learn.pretrain_set report

Outputs go to ~/ndsp-presets/learn/pretrain-set/. Every example is deterministic from its index:
its section, amp, mode, base class and settings (`plan_example`, `settings_for`). What is stored
per example is the isolated render's log-mel (arm B's features, uint8 at 0.5 dB, zlib) and one JSON
row (label, settings, gain measures, LUFS); validation examples also store the true stem and mix
features, and the audit examples the render's audio. Mixes for training are made in the
mel-power domain at training time (`powersum_db`).

The pool comes from part A's manifest through `pool_rows`, which re-checks every row against the
inventory, refuses held-out material and part B's DIs, and leaves out the hum-audit superset
(`HUM_SUSPECT`). The pre-amendment manifest is refused (`PRE_AMENDMENT_SHA`).

The pure parts are unit-tested with fakes (`tests/test_pretrain_set.py`); the commands that render
or train are not, like the other step modules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import random
import shutil
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/pretrain-set"
CLEAN = HOME / "learn/clean-di"
MANIFEST = CLEAN / "manifest.json"
INVENTORY = CLEAN / "inventory.json"
SECTIONS_MS = HOME / "learn/multi-section/sections"
SR = 48000
SEC_S = 10.0
TRIM_S = 0.25
LATENCY = 52

# --- the pool ----------------------------------------------------------------------------------------
PRE_AMENDMENT_SHA = "22a61fb76b918b25"         # part A's manifest before the hum-screen amendment
# The hum audit's 10 probably-hummy DIs, as the superset the code can name (plan, "The pool"): every
# Guitar-TECHS DI with a clean section (7 P1 chord files, 1 P2 chord file), Prodigal ElecGtr1 and 3,
# and Wickerman ElecGtr7. Left out until a dated amendment says otherwise.
HUM_SUSPECT = frozenset({
    "guitar-techs/P1-downloads/P1_chords/audio/directinput/directinput_Drop3_Maj7.wav",
    "guitar-techs/P1-downloads/P1_chords/audio/directinput/directinput_Drop3_m7b5.wav",
    "guitar-techs/P1-downloads/P1_chords/audio/directinput/directinput_Set1_Maj7.wav",
    "guitar-techs/P1-downloads/P1_chords/audio/directinput/directinput_Set2_Maj7.wav",
    "guitar-techs/P1-downloads/P1_chords/audio/directinput/directinput_Set2_m7.wav",
    "guitar-techs/P1-downloads/P1_chords/audio/directinput/directinput_Set2_m7b5.wav",
    "guitar-techs/P1-downloads/P1_chords/audio/directinput/directinput_Set4_dim.wav",
    "guitar-techs/P2-downloads/P2_chords/audio/directinput/directinput_Set1_maj.wav",
    "cambridge/StarnesAndShah_Prodigal_Full/06_ElecGtr1DI.wav",
    "cambridge/StarnesAndShah_Prodigal_Full/10_ElecGtr3DI.wav",
    "cambridge/EatTheFeeder_Wickerman_Full/EatTheFeeder_Wickerman_Full/37_ElecGtr7DI.wav",
})
EXCLUDE_SOURCES = ("guitar-techs",)           # declared (amendment 1, item 10): out by source
EXCLUDE_BANDS = ("Timo And The Timezone",)    # amendment 1, item 18: a part-B2 candidate's band
HUM_MARKER = CLEAN / "HUM_AMENDMENT.json"     # amendment 1, item 9: the positive marker
VAL_SEED = 20261041
VAL_MIN_SHARE = 0.15
VAL_MIN_BANDS = 8
VAL_SKIP_LARGEST = 3
VAL_MIN_BAND_SECTIONS = 5
VAL_MAX_BAND_SECTIONS = 20                    # val bands are small whole bands (5-20 sections), so there are many
ES_SHARE = 0.05                               # early-stopping sections (whole sections of train)
AUDIT_SECTIONS = 40
AUDIT_EVERY = 10

# --- the draw ----------------------------------------------------------------------------------------
SEED = 20261040
MODES = (("factory", 0.4), ("start", 0.2), ("wide", 0.4))
SIGMA = 0.1
KEEP_P = 0.7
VAL_BASE = 1_000_000                          # validation example ids: VAL_BASE + j
N_PILOT = 40_000
N_VAL = 3_000

# --- features ----------------------------------------------------------------------------------------
Q_LO_DB = -112.0
Q_STEP_DB = 0.5
HALVES = {"A": (1.0, 5.5), "B": (5.5, 10.0)}
# Amendment 2, item 2: the model never sees half A's first second. Part C has no priming render,
# and a render's first ~4 s can carry the previous plugin state's transient
# (docs/audits/start-transient-2026-10-18.md). The mel frames whose window starts in that second
# are set to 0 in the normalised input (-60 dB), stem and mix alike, in training, early stopping
# and every val readout. Stored features are unchanged.
MASK_A_S = 1.0
MEL_HOP = 480                                 # song_aug.HOP
MASK_A_FRAMES = -(-int(MASK_A_S * SR) // MEL_HOP)
STEM_LEAK_DB = (0.0, 6.0)                     # guitar-to-leak of the stand-in stem
MIX_LUFS_SPREAD = 3.0

# --- machine -----------------------------------------------------------------------------------------
DISK_GUARD_GB = 31.0
DISK_EVERY = 50
EXIT_DISK = 4

# --- the curve ---------------------------------------------------------------------------------------
SIZES = (5_000, 10_000, 20_000, 40_000)
CURVE_SEEDS = (20261042, 20261043, 20261044)
SEEDS_SMALL = 2                               # 5k and 10k: two seeds; 20k and up: three
HALF_SECTIONS_N = 20_000                      # the diversity axis: 20k over half the train sections
MASTER_P = 0.5                                # val examples mastered (compressor and limiter)
WIDTHS = (16, 32, 64, 96)
EPOCHS, PATIENCE, BATCH, LR = 30, 4, 64, 1e-3
T90 = {1: 6.314, 2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015, 6: 1.943, 7: 1.895, 8: 1.860, 9: 1.833,
       10: 1.812, 11: 1.796, 12: 1.782, 13: 1.771, 14: 1.761, 15: 1.753, 16: 1.746, 17: 1.740,
       18: 1.734, 19: 1.729, 20: 1.725}


def _save(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


def _load(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else None


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def seed_int(*xs):
    """A stable 63-bit seed from integers (numpy's SeedSequence when present, else sha256)."""
    h = hashlib.sha256(json.dumps(list(xs)).encode()).digest()
    return int.from_bytes(h[:8], "big") >> 1


# --- the pool ----------------------------------------------------------------------------------------

def training_ok(path, inventory):
    """`clean_di.assert_training_ok`'s rule on one path: (ok, why)."""
    by = {r["path"]: r for r in inventory["dis"]}
    r = by.get(str(path))
    if r is None:
        return False, "not in the DI inventory"
    if r["split"] != "library" or not r["training_ok"]:
        return False, f"not for training ({r['split']})"
    return True, ""


def manifest_ok(sha):
    """The pre-amendment manifest is refused (plan, gate)."""
    return not str(sha).startswith(PRE_AMENDMENT_SHA)


def hum_amended(manifest, sha, marker=None):
    """The positive gate (amendment 1, item 9): the manifest names the hum-screen amendment, or the
    marker file names this manifest's sha256; and it is not the pre-amendment manifest."""
    if not manifest_ok(sha):
        return False
    if manifest.get("hum_amendment"):
        return True
    if 3 in (manifest.get("amendments") or []) and (manifest.get("version") or 0) >= 2:
        return True                            # learn/clean_di.py's amendment 3 (the hum rule), manifest version 2
    return bool(marker) and marker.get("manifest_sha256") == sha


def pool_rows(manifest, inventory, refuse=None):
    """The pool: the manifest's non-overlapping clean sections that may train, re-checked against
    the inventory, less the hum superset and Guitar-TECHS; `refuse(rec)` raises on held-out
    material (`clean_di.refuse_held_out`). -> (rows, dropped {reason: n})."""
    recs = {r["path"]: r for r in inventory["dis"]}
    rows, dropped = [], {}

    def drop(why):
        dropped[why] = dropped.get(why, 0) + 1

    for r in manifest["sections"]:
        if not (r.get("disjoint") and r.get("clean")):
            continue
        if r.get("split") != "library" or not r.get("training_ok"):
            drop("not library / training_ok in the manifest")
            continue
        ok, why = training_ok(r["path"], inventory)
        if not ok:
            drop(why)
            continue
        if r["di"] in HUM_SUSPECT:
            drop("hum-audit superset")
            continue
        if r.get("source") in EXCLUDE_SOURCES:
            drop("Guitar-TECHS")
            continue
        if r.get("band") in EXCLUDE_BANDS:
            drop("band excluded (part B2 candidate)")
            continue
        if refuse is not None:
            refuse(recs[r["path"]])
        rows.append(r)
    assert not any(r["di"] in HUM_SUSPECT for r in rows)
    return rows, dropped


def section_id(r):
    return f"{r['di']}@{float(r['start_s']):.1f}"


def stage_f_dis(inventory):
    return {d["id"] for d in inventory["dis"] if any("stage F" in n for n in d.get("notes", []))}


def split_pool(rows, inventory, has_backing, seed=VAL_SEED, min_share=VAL_MIN_SHARE, min_bands=VAL_MIN_BANDS,
               skip_largest=VAL_SKIP_LARGEST, min_band_sections=VAL_MIN_BAND_SECTIONS,
               max_band_sections=VAL_MAX_BAND_SECTIONS):
    """{section id: reserve | val | train}. Reserve: stage F's DIs. Val: whole bands with a session
    backing and `min_band_sections` to `max_band_sections` sections (the largest few left out),
    added in seeded order until both minimums hold or the candidates run out."""
    sf = stage_f_dis(inventory)
    out = {}
    rest = []
    for r in rows:
        if r["di"] in sf:
            out[section_id(r)] = "reserve"
        else:
            rest.append(r)
    per_band = {}
    for r in rest:
        per_band[r["band"]] = per_band.get(r["band"], 0) + 1
    largest = set(sorted(per_band, key=lambda b: (-per_band[b], b))[:skip_largest])
    cands = sorted(b for b in per_band if b not in largest and min_band_sections <= per_band[b] <= max_band_sections
                   and all(has_backing(r) for r in rest if r["band"] == b))
    random.Random(seed).shuffle(cands)
    val, n = [], 0
    for b in cands:
        if n >= min_share * len(rest) and len(val) >= min_bands:
            break
        val.append(b)
        n += per_band[b]
    for r in rest:
        out[section_id(r)] = "val" if r["band"] in val else "train"
    return out, sorted(val)


def es_sections(train_ids, seed=VAL_SEED + 1, share=ES_SHARE):
    ids = sorted(train_ids)
    k = max(1, round(share * len(ids)))
    return set(random.Random(seed).sample(ids, k))


def audit_sections(train_ids, es, seed=VAL_SEED + 2, n=AUDIT_SECTIONS):
    ids = sorted(set(train_ids) - set(es))
    return set(random.Random(seed).sample(ids, min(n, len(ids))))


# --- the draw ----------------------------------------------------------------------------------------

def section_for(i, n_sections, seed=SEED):
    """Example i's section index: a seeded permutation per cycle, so every section is used equally
    (to within one) and i alone decides it."""
    c, k = divmod(i, n_sections)
    perm = list(range(n_sections))
    random.Random(seed_int(seed, "cycle", c)).shuffle(perm)
    return perm[k]


def mode_of(u, modes=MODES):
    acc = 0.0
    for m, p in modes:
        acc += p
        if u < acc:
            return m
    return modes[-1][0]


def plan_example(i, amps=("pr12", "sw50r", "ac20")):
    """(rng, amp, mode, base class) of example i; the rng goes on to draw its settings."""
    rng = random.Random(seed_int(SEED, i))
    amp = rng.choice(amps)
    mode = mode_of(rng.random())
    base = rng.choice(("clean", "crunch"))
    return rng, amp, mode, base


def settings_for(rng, amp, mode, base, menu, start, space, fmt, sigma=SIGMA, keep_p=KEEP_P):
    """(select, settings, label, centre name) for one example. `menu[amp]`: {name: (select,
    {(module, key): stored})}; `start[base][amp]`: S's name; `space(amp, S)`: the labelled
    dimensions (knob_ceiling.Dim); `fmt`: the stored-value formatter. Every module outside the space
    comes from S; the space's values from the centre, drawn as the mode says."""
    sname = start[base][amp]
    sel, S = menu[amp][sname]
    centre, cname = dict(S), sname
    if mode == "factory":
        cname = rng.choice(sorted(menu[amp]))
        centre.update(menu[amp][cname][1])
    elif mode == "wide":
        cname = None
    x, label = dict(S), {}
    for d in space(amp, S):
        k = (d.module, d.key)
        if d.kind in ("cont", "log"):
            if mode == "wide":
                u = rng.random()
            else:
                u = min(1.0, max(0.0, d.to_unit(centre.get(k, S.get(k, d.lo))) + rng.gauss(0, sigma)))
            x[k] = fmt(d.from_unit(u))
            label[d.name] = u
        else:
            v = centre.get(k)
            if mode == "wide" or rng.random() > keep_p or v not in d.values:
                v = rng.choice(d.values)
            x[k] = v
            label[d.name] = v
    return sel, x, label, cname


def example_ids(n_train, n_val=N_VAL):
    return list(range(n_train)) + [VAL_BASE + j for j in range(n_val)]


def example_path(i):
    return OUT / "examples" / f"{i // 1000:04d}" / f"{i:07d}.npz"


# --- features ----------------------------------------------------------------------------------------

def quant(db):
    import numpy as np

    return np.clip(np.round((np.asarray(db, np.float64) - Q_LO_DB) / Q_STEP_DB), 0, 255).astype(np.uint8)


def dequant(q):
    import numpy as np

    return np.asarray(q, np.float32) * Q_STEP_DB + Q_LO_DB


def half_slices(sr=SR):
    return {h: slice(int(a * sr), int(b * sr)) for h, (a, b) in HALVES.items()}


def mask_half_a(x, is_a):
    """Zero the first MASK_A_FRAMES frames (last axis) of the inputs where `is_a`; `x` is a
    normalised [N, 2, mels, frames] array or tensor, changed in place and returned."""
    x[is_a, ..., :MASK_A_FRAMES] = 0
    return x


def halves_mel(y):
    """{half: uint8 [96, frames]} of arm B's log-mel (`song_aug.logmel`)."""
    from learn import song_aug as A

    return {h: quant(A.logmel(y[s])) for h, s in half_slices().items()}


def db_sum(*levels):
    """Power sum of dB levels."""
    return 10 * math.log10(sum(10 ** (v / 10) for v in levels))


def mix_gains_db(lg, lb, ratio_db, leak_db, target_lufs):
    """dB gains (backing in the mix, backing in the stem, overall) so that the guitar sits
    `ratio_db` above the backing in the mix and `leak_db` above it in the stem, and the mix reads
    `target_lufs` by the power sum of the stored loudness values."""
    lb = max(lb, lg - 40.0)                        # a near-silent backing is not lifted more than 40 dB over its read
    gb = lg - ratio_db - lb
    gl = lg - leak_db - lb
    mix = db_sum(lg, lb + gb)
    return gb, gl, target_lufs - mix


def powersum_db(g_db, b_db, gain_b_db, gain_all_db):
    """The mel-power-domain mix in dB: 10 log10(10^(g/10) + 10^((b + gain_b)/10)) + gain_all."""
    import numpy as np

    return 10 * np.log10(10 ** (np.asarray(g_db, np.float64) / 10) + 10 ** ((np.asarray(b_db, np.float64)
                                                                            + gain_b_db) / 10)) + gain_all_db


def ratio_values():
    """{band: [guitar-to-backing dB]} of multi-section step 1's passing development sections."""
    vals = {}
    for f in sorted(SECTIONS_MS.glob("*.json")):
        d = json.loads(f.read_text())
        for r in d["rows"]:
            if r.get("passes") and r.get("snr_db") is not None:
                vals.setdefault(d.get("band") or f.stem, []).append(float(r["snr_db"]))
    return vals


def mix_params(i, ratios, has_vocals, eval_mix_lufs, epoch=0):
    """(ratio dB, with vocals, stem leak dB, target LUFS) for example i (and epoch, at training);
    the ratio band-weighted: a band uniformly, then one of its values."""
    rng = random.Random(seed_int(SEED, "mix", i, epoch))
    r = rng.choice(ratios[rng.choice(sorted(ratios))])
    v = has_vocals and rng.random() < 0.5
    leak = rng.uniform(*STEM_LEAK_DB)
    return r, v, leak, eval_mix_lufs + rng.uniform(-MIX_LUFS_SPREAD, MIX_LUFS_SPREAD)


# --- backings ----------------------------------------------------------------------------------------

VOCAL_WORDS = ("vox", "vocal", "voc ")


def is_vocal_name(name):
    n = pathlib.PurePosixPath(name).name.lower()
    return any(w in n for w in VOCAL_WORDS)


def backing_tracks(rec, session_files, leaking=()):
    """(with vocals, without vocals) track names for a DI's backing: the inventory's mix list (or,
    without one, every non-DI file of the session), less every guitar DI, less the DI's own tracks,
    less the leaking tracks."""
    from learn import clean_di as CD

    names = rec.get("mix") or [f for f in session_files if f.lower().endswith(".wav")]
    own = set(rec.get("own") or [])
    vocals = set(rec.get("vocals") or [])
    keep = [f for f in names if f not in own and not CD.is_guitar_di(f) and f not in set(leaking)]
    voc = [f for f in keep if f in vocals or (not rec.get("vocals") and is_vocal_name(f))]
    return keep, [f for f in keep if f not in voc]


def leak_excess(X_track, X_amp, play_rows, bins):
    """Part A's bleed measure: mean magnitude-squared coherence less the 1/N bias."""
    from learn import clean_di as CD

    msc, bias = CD.coherence(X_track, X_amp, play_rows, bins)
    return msc - bias


LEAK_EXCESS = 0.05


def load_mono(path, sr_out, start_s=None, dur_s=None):
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    info = sf.info(str(path))
    kw = {}
    if start_s is not None:
        kw = {"start": max(0, int(round(start_s * info.samplerate))),
              "frames": int(round(dur_s * info.samplerate))}
    x, sr = sf.read(str(path), dtype="float32", always_2d=True, **kw)
    x = x.mean(axis=1)
    if sr != sr_out:
        g = math.gcd(sr_out, sr)
        x = resample_poly(x, sr_out // g, sr // g).astype(np.float32)
    return x


def section_audio(path, start_s, sr=SR):
    """The section with TRIM_S before it (zeros where the file starts later)."""
    import numpy as np

    n = int(round((SEC_S + TRIM_S) * sr))
    a = start_s - TRIM_S
    x = load_mono(path, sr, max(0.0, a), SEC_S + TRIM_S - max(0.0, -a))
    if a < 0:
        x = np.concatenate([np.zeros(int(round(-a * sr)), np.float32), x])
    return np.pad(x, (0, max(0, n - len(x))))[:n]


# --- the commands: pool and backings ---------------------------------------------------------------

def cmd_pool(_args):
    from learn import clean_di as CD

    sha = file_sha256(MANIFEST)
    man = json.loads(MANIFEST.read_text())
    if not hum_amended(man, sha, _load(HUM_MARKER)):
        raise SystemExit(f"NOT AMENDED: manifest {sha[:16]} carries no hum-screen amendment marker")
    inv = json.loads(INVENTORY.read_text())
    rows, dropped = pool_rows(man, inv, refuse=CD.refuse_held_out)
    recs = {r["id"]: r for r in inv["dis"]}

    def has_backing(r):
        rec = recs[r["di"]]
        return bool(rec.get("mix")) or bool(rec.get("session_dir"))

    split, val_bands = split_pool(rows, inv, has_backing)
    folds = json.loads((PLUGIN_ROOT / "docs/song-settings-folds.json").read_text())["folds"]
    sf = stage_f_dis(inv)
    sess_f = {recs[d]["session_dir"] for d in sf if recs.get(d, {}).get("session_dir")}
    train = [section_id(r) for r in rows if split[section_id(r)] == "train"]
    es = es_sections(train)
    audit = audit_sections(train, es)
    out = []
    for r in rows:
        sid = section_id(r)
        rec = recs[r["di"]]
        out.append({"id": sid, "di": r["di"], "path": r["path"], "start_s": r["start_s"], "band": r["band"],
                    "source": r["source"], "split": split[sid], "early_stop": sid in es, "audit": sid in audit,
                    "fold": folds.get(r["band"]), "stage_f_session": rec.get("session_dir") in sess_f,
                    "bleed_status": r.get("bleed_status"), "style": r.get("style"), "gain_class": r.get("gain_class"),
                    "licence": r.get("licence"), "tags": r.get("tags")})
    out.sort(key=lambda x: x["id"])
    counts = {k: sum(1 for x in out if x["split"] == k) for k in ("train", "val", "reserve")}
    val_cls = {}
    for x in out:
        if x["split"] == "val":
            val_cls[str(x["gain_class"])] = val_cls.get(str(x["gain_class"]), 0) + 1
    _save(OUT / "pool.json", {"manifest_sha256": sha, "inventory_sha256": file_sha256(INVENTORY),
                              "val_by_gain_class": val_cls,
                              "dropped": dropped, "val_bands": val_bands, "counts": counts,
                              "early_stop": len(es), "audit": len(audit), "sections": out})
    print("pool", counts, "val bands", val_bands, "dropped", dropped)
    print("POOL DONE")


def cmd_gate(_args):
    """Exit 0 when the manifest carries the hum-screen amendment (amendment 1, item 9), else 10."""
    sha = file_sha256(MANIFEST)
    ok = hum_amended(json.loads(MANIFEST.read_text()), sha, _load(HUM_MARKER))
    print("AMENDED" if ok else "NOT AMENDED", sha[:16])
    raise SystemExit(0 if ok else 10)


def pool():
    p = _load(OUT / "pool.json")
    if p is None:
        raise SystemExit("run `pool` first")
    return p


def split_sections(p, split):
    return [s for s in p["sections"] if s["split"] == split]


def cmd_backings(_args):
    """Per DI: the leakage check (once), then per section the backing's mels and LUFS with and
    without vocals; audio kept for val and audit sections."""
    import numpy as np
    import soundfile as sf

    from learn import clean_di as CD
    from learn import song_aug as A

    p = pool()
    inv = {r["id"]: r for r in json.loads(INVENTORY.read_text())["dis"]}
    d = OUT / "backings"
    d.mkdir(parents=True, exist_ok=True)
    leak = _load(OUT / "leakage.json") or {}
    secs = [s for s in p["sections"] if s["split"] in ("train", "val")]
    by_di = {}
    for s in secs:
        by_di.setdefault(s["di"], []).append(s)
    bins = CD.bleed_bins()
    for di, ss in sorted(by_di.items()):
        rec = inv[di]
        sess = pathlib.Path(rec["session_dir"])
        files = sorted(f.name for f in sess.glob("*.wav"))
        if di not in leak:
            dropped, readings = [], {}
            amps = [load_mono(sess / o, CD.BLEED_SR) for o in rec.get("own") or []]
            keep_all, _ = backing_tracks(rec, files)
            for a in amps:
                Xa = CD.stft16(a)
                pa = 10 * np.log10(np.mean(np.abs(Xa) ** 2, 1) + 1e-20)
                rows_ = pa >= pa.max() - CD.OTHER_ACTIVE_DB
                for t in keep_all:
                    y = load_mono(sess / t, CD.BLEED_SR)
                    n = min(len(y), len(a))
                    Y = CD.stft16(y[:n])
                    e = leak_excess(Y, Xa[:len(Y)], rows_[:len(Y)], bins)
                    readings[t] = max(readings.get(t, -1.0), round(float(e), 4))
            dropped = sorted(t for t, e in readings.items() if e > LEAK_EXCESS)
            leak[di] = {"dropped": dropped, "excess": readings}
            _save(OUT / "leakage.json", leak)
        withv, nov = backing_tracks(rec, files, leak[di]["dropped"])
        for s in ss:
            out = d / f"{hashlib.sha1(s['id'].encode()).hexdigest()[:16]}.npz"
            if out.exists():
                continue
            parts = {"v": withv, "n": nov}
            arrays, meta = {}, {"id": s["id"], "tracks": parts, "has_vocals": len(withv) > len(nov)}
            for k, names in parts.items():
                b = np.zeros(int(round((SEC_S + TRIM_S) * SR)), np.float64)
                for t in names:
                    b += section_audio(sess / t, s["start_s"])
                b = b[int(TRIM_S * SR):]
                for h, m in halves_mel(b).items():
                    arrays[f"{k}{h}"] = m
                meta[f"lufs_{k}"] = A.lufs(b)
                for h, sl in half_slices().items():
                    meta[f"lufs_{k}{h}"] = A.lufs(b[sl])
                if s["split"] == "val" or s["audit"]:
                    pk = float(np.max(np.abs(b))) or 1.0
                    sf.write(str(out.with_name(out.stem + f"-{k}.flac")), (b / pk * 0.99).astype(np.float32), SR,
                             subtype="PCM_24")
                    meta[f"peak_{k}"] = pk
            np.savez_compressed(out, **arrays)
            _save(out.with_suffix(".json"), meta)
        print("backings", di, len(ss), "dropped", leak[di]["dropped"], flush=True)
    print("backings done")


def backing_path(sid):
    return OUT / "backings" / f"{hashlib.sha1(sid.encode()).hexdigest()[:16]}.npz"


def load_backing_audio(sid, kind):
    import soundfile as sf

    p = backing_path(sid)
    meta = json.loads(p.with_suffix(".json").read_text())
    y, _ = sf.read(str(p.with_name(p.stem + f"-{kind}.flac")), dtype="float64")
    return y / 0.99 * meta[f"peak_{kind}"], meta


# --- the render --------------------------------------------------------------------------------------

def free_gb():
    return shutil.disk_usage(pathlib.Path.home()).free / 1e9


def disk_ok(guard=DISK_GUARD_GB, free=None):
    return (free_gb() if free is None else free) >= guard


def shard_ids(ids, shard):
    k, n = shard
    return [i for i in ids if i % n == k]


def gain_class(y, di):
    sys.path.insert(0, str(HOME / "references/datasets-set3/_tools"))
    import classify as C
    import gainmeasure as GM

    import numpy as np

    y = np.asarray(y, np.float64)
    y = y.mean(axis=1) if y.ndim == 2 else y
    m = GM.measures(y, np.asarray(di, np.float64), SR, lag=LATENCY)
    cls, conf, why, split = C.classify(m) if m else (None, None, [], None)
    return {"class": cls, "clean_vs_driven": split,
            "nl_db": m and m["nonlinear_to_linear_db"], "slope": m and m["level_slope"]}


def cmd_render(args):
    import numpy as np
    import soundfile as sf

    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import song_aug as A
    from learn import song_bank as B

    p = pool()
    if not manifest_ok(p["manifest_sha256"]):
        raise SystemExit("the pool was built from the pre-amendment manifest")
    from learn import confirm_run as CR
    secs = {k: split_sections(p, k) for k in ("train", "val")}
    lv = json.loads((B.OUT / "levels.json").read_text())
    eval_mix = lv["summary"]["eval_mix_lufs_median"]
    ratios = ratio_values()
    ids = shard_ids(example_ids(args.n, args.n_val), args.shard)
    rows_path = OUT / "rows" / f"shard-{args.shard[0]}.jsonl"
    rows_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if rows_path.exists():
        for r in read_rows(rows_path, repair=True):
            done.add(r["i"])
    todo = []
    for i in ids:
        if i in done:
            continue
        _, amp, mode, base = plan_example(i)
        todo.append((amp, base, i))
    todo.sort()
    print("shard", args.shard, "todo", len(todo), flush=True)
    if not todo:
        print(f"SHARD DONE {args.shard[0]}/{args.shard[1]}", flush=True)
        return
    LO._wait_cap()
    rr = K.Renderer()
    if rr.r.isolate is not True:
        raise SystemExit("the renderer is not isolating renders")
    try:
        menu = rr.menu()
        rec = {"plugin_version": rr.r.metadata().plugin_version, "isolate": True, "latency_samples": LATENCY,
               "latency_trimmed": False, "sr": SR, "lead_in_s": TRIM_S, "average": str(CR.AVERAGE),
               "average_sha256": file_sha256(CR.AVERAGE)}
        old = _load(OUT / "recipe.json")
        if old and old != rec:
            raise SystemExit(f"the recipe changed since the first shard: {old} -> {rec}")
        _save(OUT / "recipe.json", rec)
        last_amp = None
        with open(rows_path, "a") as fh:
            for n, (amp, base, i) in enumerate(todo):
                if n % DISK_EVERY == 0 and not disk_ok():
                    print("DISK GUARD", round(free_gb(), 1), flush=True)
                    raise SystemExit(EXIT_DISK)
                if amp != last_amp:
                    LO._wait_cap()
                    last_amp = amp
                t0 = time.time()
                val = i >= VAL_BASE
                ss = secs["val" if val else "train"]
                s = ss[section_for(i - VAL_BASE if val else i, len(ss), SEED + (1 if val else 0))]
                rng, amp_, mode, base_ = plan_example(i)
                sel, x, label, cname = settings_for(rng, amp_, mode, base_, menu, K.START, K.space, K.fmt)
                di = B.measure(section_audio(s["path"], s["start_s"])).astype(np.float32)
                y = np.asarray(rr.render(di, sel, x), np.float64)
                y = y.mean(axis=1) if y.ndim == 2 else y
                y = y[int(TRIM_S * SR):int((TRIM_S + SEC_S) * SR)]
                di_t = di[int(TRIM_S * SR):].astype(np.float64)
                g = halves_mel(y)
                arrays = {f"g{h}": m for h, m in g.items()}
                row = {"i": i, "section": s["id"], "band": s["band"], "fold": s["fold"], "split": "val" if val else "train",
                       "licence": s.get("licence"), "di_gain_class": s.get("gain_class"),
                       "early_stop": s["early_stop"], "audit": bool(s["audit"] and not val and i % AUDIT_EVERY == 0),
                       "amp": amp_, "mode": mode, "base": base_, "centre": cname, "select": sel, "label": label,
                       "settings": {f"{m}/{k}": v for (m, k), v in x.items()},
                       "lufs": A.lufs(y), **{f"lufs_{h}": A.lufs(y[sl]) for h, sl in half_slices().items()},
                       "peak": float(np.max(np.abs(y))), "gain": gain_class(y, di_t)}
                if val or row["audit"]:
                    meta = json.loads(backing_path(s["id"]).with_suffix(".json").read_text())
                    r, v, leak, target = mix_params(i, ratios, meta["has_vocals"], eval_mix)
                    b, _ = load_backing_audio(s["id"], "v" if v else "n")
                    gb, gl, ga = mix_gains_db(row["lufs"], meta["lufs_" + ("v" if v else "n")], r, leak, target)
                    k = 10 ** (ga / 20)
                    mix = (y + b * 10 ** (gb / 20)) * k
                    stem = (y + b * 10 ** (gl / 20)) * k
                    mrng = random.Random(seed_int(SEED, "master", i))
                    mastered = bool(val and mrng.random() < MASTER_P)
                    if mastered:
                        mix = A.compress(mix, mrng)
                    for h, m in halves_mel(stem).items():
                        arrays[f"s{h}"] = m
                    for h, m in halves_mel(mix).items():
                        arrays[f"m{h}"] = m
                    row["mix"] = {"ratio_db": r, "vocals": v, "leak_db": leak, "target_lufs": target,
                                  "mastered": mastered,
                                  "gains_db": [gb, gl, ga],
                                  **{f"lufs_{c}{h}": A.lufs(z[sl]) for c, z in (("s", stem), ("m", mix))
                                     for h, sl in half_slices().items()}}
                if row["audit"]:
                    pk = max(row["peak"], 1e-12)
                    f = example_path(i).with_suffix(".flac")
                    f.parent.mkdir(parents=True, exist_ok=True)
                    sf.write(str(f), (y / pk * 0.99).astype(np.float32), SR, subtype="PCM_16")
                example_path(i).parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(example_path(i), **arrays)
                row["seconds"] = round(time.time() - t0, 2)
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                if n % 200 == 0:
                    print("rendered", n, "of", len(todo), i, amp_, mode, row["gain"]["class"], row["seconds"], flush=True)
    finally:
        rr.close()
    print(f"SHARD DONE {args.shard[0]}/{args.shard[1]}", flush=True)


def read_rows(path, repair=False):
    """The rows of one shard's JSONL. A torn last line (a shard killed mid-write) is skipped, and with
    `repair` cut from the file so the next append starts on a fresh line."""
    text = pathlib.Path(path).read_text() if pathlib.Path(path).exists() else ""
    lines = text.split("\n")
    out, good, pos = [], 0, 0
    for k, line in enumerate(lines):
        pos += len(line) + 1
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
            good = pos
        except json.JSONDecodeError:
            if k < len(lines) - 1 and any(x.strip() for x in lines[k + 1:]):
                raise
    if repair and text and good != len(text):
        with open(path, "r+") as fh:
            if good > len(text):                   # a complete last row without its newline
                fh.seek(0, 2)
                fh.write("\n")
            else:
                fh.truncate(good)
    return out


def all_rows():
    out = {}
    for f in sorted((OUT / "rows").glob("shard-*.jsonl")):
        for r in read_rows(f):
            out[r["i"]] = r
    return out


def beyond_threshold(rows):
    """Per amp, the scope line: the 10th percentile of the level slope of the `start`-mode,
    crunch-base examples (plan, "No metal")."""
    out = {}
    for amp in sorted({r["amp"] for r in rows}):
        s = sorted(r["gain"]["slope"] for r in rows if r["amp"] == amp and r["mode"] == "start"
                   and r["base"] == "crunch" and r["gain"].get("slope") is not None)
        if s:
            out[amp] = s[int(0.1 * (len(s) - 1))]
    return out


def is_beyond(row, thr):
    s = row["gain"].get("slope")
    return s is not None and row["amp"] in thr and s < thr[row["amp"]]


RECHECK_LATE_S = 4.0                          # the start transient is below 0.005 by 3.5-4 s (audit)


def primed_render(rr, di, sel, x):
    """A re-render preceded by one discarded render at the same DI and settings (amendment 2,
    item 1): the plugin's first render after a process start, amp change or DI change starts
    louder for about 4 s (docs/audits/start-transient-2026-10-18.md). Priming removes it from the
    re-render only: the stored render was not primed, so `cmd_recheck` also reports the comparison
    past RECHECK_LATE_S and on half B."""
    import numpy as np

    rr.render(di, sel, x)
    return np.asarray(rr.render(di, sel, x), np.float64)


def cmd_recheck(args):
    """Re-render 30 seeded audit examples, each primed (`primed_render`), and compare with the
    stored audio."""
    import numpy as np
    import soundfile as sf

    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import song_bank as B

    rows = all_rows()
    aud = sorted(i for i, r in rows.items() if r.get("audit"))
    pick = sorted(random.Random(SEED + 7).sample(aud, min(30, len(aud))))
    p = pool()
    secs = {s["id"]: s for s in p["sections"]}
    LO._wait_cap()
    rr = K.Renderer()
    out = []
    try:
        menu = rr.menu()
        for i in pick:
            r = rows[i]
            s = secs[r["section"]]
            rng, amp, mode, base = plan_example(i)
            sel, x, label, _ = settings_for(rng, amp, mode, base, menu, K.START, K.space, K.fmt)
            assert {f"{m}/{k}": v for (m, k), v in x.items()} == r["settings"], i
            di = B.measure(section_audio(s["path"], s["start_s"])).astype(np.float32)
            y = primed_render(rr, di, sel, x)
            y = (y.mean(axis=1) if y.ndim == 2 else y)[int(TRIM_S * SR):int((TRIM_S + SEC_S) * SR)]
            st, _ = sf.read(str(example_path(i).with_suffix(".flac")), dtype="float64")
            st = st / 0.99 * r["peak"]
            d = y - st
            snr = 10 * math.log10(float(np.sum(st ** 2)) / max(float(np.sum(d ** 2)), 1e-30))
            g = np.load(example_path(i))
            same = float(np.mean(np.concatenate([(halves_mel(y)[h] == g[f"g{h}"]).ravel() for h in "AB"])))
            # The stored render was not primed, so its first seconds can carry the previous plugin
            # state's transient; past RECHECK_LATE_S (and in half B) the comparison is of the recipe.
            late = slice(int(RECHECK_LATE_S * SR), None)
            snr_late = 10 * math.log10(float(np.sum(st[late] ** 2)) / max(float(np.sum(d[late] ** 2)), 1e-30))
            same_b = float(np.mean(halves_mel(y)["B"] == g["gB"]))
            out.append({"i": i, "max_abs": float(np.max(np.abs(d))), "snr_db": snr, "mel_cells_identical": same,
                        "max_abs_late": float(np.max(np.abs(d[late]))), "snr_db_late": snr_late,
                        "mel_cells_identical_b": same_b})
            print(out[-1], flush=True)
    finally:
        rr.close()
    _save(OUT / "recheck.json", {"n": len(out), "rows": out})
    print("RECHECK DONE")


# --- the curve ---------------------------------------------------------------------------------------

def band_t_interval(values_by_band):
    """(band-weighted mean, lo, hi, bands): the mean of band means with a 90% t interval."""
    means = [sum(v) / len(v) for v in values_by_band.values() if v]
    n = len(means)
    m = sum(means) / n
    if n < 2:
        return m, -math.inf, math.inf, n
    sd = math.sqrt(sum((x - m) ** 2 for x in means) / (n - 1))
    h = T90.get(n - 1, 1.645) * sd / math.sqrt(n)
    return m, m - h, m + h, n


def decide(delta):
    """EXTEND while the latest doubling's 90% interval lies entirely below 0."""
    _, lo, hi, _ = delta
    return "EXTEND" if hi < 0 else "STOP"


def build_net(width=WIDTHS):
    import torch
    import torch.nn as nn

    from learn import song_model as SM

    class Block(nn.Module):
        def __init__(self, i, o):
            super().__init__()
            self.net = nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(),
                                     nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU())
            self.skip = nn.Conv2d(i, o, 1)
            self.pool = nn.AvgPool2d(2)

        def forward(self, x):
            return self.pool(self.net(x) + self.skip(x))

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            c = (2, *width)
            self.body = nn.Sequential(*[Block(c[j], c[j + 1]) for j in range(len(width))])
            d = width[-1] * (96 // 2 ** len(width)) * 2 + len(SM.AMPS) + len(SM.CLASSES) + 2
            self.trunk = nn.Sequential(nn.Linear(d, 256), nn.ReLU(), nn.Dropout(0.2), nn.Linear(256, 256), nn.ReLU())
            n = len(SM.CONT)
            self.pi = nn.Linear(256, SM.K_MIX)
            self.mu = nn.Linear(256, SM.K_MIX * n)
            self.ls = nn.Linear(256, SM.K_MIX * n)
            self.sw = nn.Linear(256, len(SM.SW))
            self.cat = nn.ModuleList([nn.Linear(256, len(SM.MICS)) for _ in SM.CAT])

        def forward(self, x, cond):
            h = self.body(x)
            h = torch.cat([h.mean(-1), h.std(-1)], dim=1).flatten(1)
            h = self.trunk(torch.cat([h, cond], dim=1))
            n = len(SM.CONT)
            return (torch.log_softmax(self.pi(h), -1), torch.sigmoid(self.mu(h)).view(-1, SM.K_MIX, n),
                    self.ls(h).view(-1, SM.K_MIX, n).clamp(-6, 1), self.sw(h), [c(h) for c in self.cat])

    return Net()


def top_error(logpi, mu, c, cm):
    """Per example: mean |μ_top − θ| over the present continuous settings."""
    import torch

    top = logpi.argmax(-1)
    m = mu[torch.arange(len(top)), top]
    return ((m - c).abs() * cm).sum(-1) / cm.sum(-1).clamp(min=1)


class CurveData:
    """Train examples in memory (uint8 guitar mels, backings per section), mixed per batch."""

    def __init__(self, rows, ratios, eval_mix):
        import numpy as np

        from learn import song_model as SM

        self.rows = rows
        self.ratios, self.eval_mix = ratios, eval_mix
        sec_ix = {}
        self.G = np.zeros((len(rows), 2, 96, 446), np.uint8)
        self.sec = np.zeros(len(rows), np.int64)
        for j, r in enumerate(rows):
            d = np.load(example_path(r["i"]))
            self.G[j, 0], self.G[j, 1] = d["gA"], d["gB"]
            self.sec[j] = sec_ix.setdefault(r["section"], len(sec_ix))
        self.B = np.zeros((len(sec_ix), 2, 2, 96, 446), np.uint8)
        self.bmeta = [None] * len(sec_ix)
        for sid, k in sec_ix.items():
            d = np.load(backing_path(sid))
            meta = json.loads(backing_path(sid).with_suffix(".json").read_text())
            for v, kind in enumerate("vn"):
                self.B[k, v, 0], self.B[k, v, 1] = d[f"{kind}A"], d[f"{kind}B"]
            self.bmeta[k] = meta
        enc = [SM.encode(r["label"]) for r in rows]
        self.Y = [np.stack(z) for z in zip(*enc)]
        self.amp = [r["amp"] for r in rows]
        self.base = [r["base"] for r in rows]

    def params(self, j, epoch):
        """(half, variant, gain_b, gain_leak, gain_all, stem LUFS, mix LUFS) of row j at an epoch."""
        r = self.rows[j]
        meta = self.bmeta[self.sec[j]]
        ratio, v, leak, target = mix_params(r["i"], self.ratios, meta["has_vocals"], self.eval_mix, epoch + 1)
        kind = "v" if v else "n"
        gb, gl, ga = mix_gains_db(r["lufs"], meta[f"lufs_{kind}"], ratio, leak, target)
        h = int(random.Random(seed_int(SEED, "half", r["i"], epoch)).random() < 0.5)
        hh = "AB"[h]
        lbh = max(meta[f"lufs_{kind}{hh}"], r[f"lufs_{hh}"] - 40.0)     # the same cap as mix_gains_db
        ls = db_sum(r[f"lufs_{hh}"], lbh + gl) + ga
        lm = db_sum(r[f"lufs_{hh}"], lbh + gb) + ga
        return h, 0 if v else 1, gb, gl, ga, ls, lm

    def batch(self, idx, epoch, dev):
        """One half per example, mixed in the mel-power domain on the device."""
        import numpy as np
        import torch

        from learn import song_model as SM

        idx = np.asarray(idx)
        P = [self.params(int(j), epoch) for j in idx]
        h = np.array([p[0] for p in P])
        v = np.array([p[1] for p in P])
        g = torch.tensor(self.G[idx, h], device=dev).float() * Q_STEP_DB + Q_LO_DB
        b = torch.tensor(self.B[self.sec[idx], v, h], device=dev).float() * Q_STEP_DB + Q_LO_DB
        k = torch.tensor(np.array([p[2:5] for p in P], np.float32), device=dev)[:, :, None, None]
        pg, pb = 10 ** (g / 10), 10 ** (b / 10)
        mix = 10 * torch.log10(pg + pb * 10 ** (k[:, 0] / 10)) + k[:, 2]
        stem = 10 * torch.log10(pg + pb * 10 ** (k[:, 1] / 10)) + k[:, 2]
        x = mask_half_a((torch.stack([stem, mix], 1) + 60.0) / 30.0, torch.tensor(h == 0, device=dev))
        c = torch.tensor(np.stack([SM.cond_vec(self.amp[j], self.base[j], [P[n][5], P[n][6]])
                                   for n, j in enumerate(idx)]), device=dev)
        y = [torch.tensor(z[idx], device=dev) for z in self.Y]
        return x, c, y


def val_tensors(rows, powersum=False, clean_stem=False):
    """Val examples' features, both halves (2 rows per example): the true stem and mix, or
    (`powersum`) the same composition rebuilt from the stored guitar and backing mels (unmastered
    examples only)."""
    import numpy as np

    from learn import song_model as SM

    X, C, Y, who = [], [], [], []
    for r in rows:
        if powersum and r["mix"].get("mastered"):
            continue
        d = np.load(example_path(r["i"]))
        if powersum:
            bz = np.load(backing_path(r["section"]))
            kind = "v" if r["mix"]["vocals"] else "n"
            gb, gl, ga = r["mix"]["gains_db"]
        for h in "AB":
            if powersum:
                g, b = dequant(d[f"g{h}"]), dequant(bz[f"{kind}{h}"])
                st, mx = powersum_db(g, b, gl, ga), powersum_db(g, b, gb, ga)
            else:
                st, mx = dequant(d[f"s{h}"]), dequant(d[f"m{h}"])
                if clean_stem:                    # the guitar alone (stem = guitar × k, no leak), the true mix
                    st = dequant(d[f"g{h}"]) + r["mix"]["gains_db"][2]
            X.append(mask_half_a(SM.norm_feat(np.stack([st, mx]))[None], [h == "A"])[0])
            C.append(SM.cond_vec(r["amp"], r["base"], [r["mix"][f"lufs_s{h}"], r["mix"][f"lufs_m{h}"]]))
            Y.append(SM.encode(r["label"]))
            who.append(r["i"])
    return np.stack(X).astype(np.float32), np.stack(C), [np.stack(z) for z in zip(*Y)], who


def evaluate(net, val, dev):
    """Per example (mean over its halves): the single answer's continuous error, switch error and
    mic agreement; and the B0 loss."""
    import torch

    from learn import song_model as SM

    Xv, Cv, Yv, who = val
    errs, sws, mics, nll = [], [], [], []
    with torch.no_grad():
        for j in range(0, len(Xv), 256):
            x = torch.tensor(Xv[j:j + 256], device=dev)
            c = torch.tensor(Cv[j:j + 256], device=dev)
            y = [torch.tensor(z[j:j + 256], device=dev) for z in Yv]
            out = net(x, c)
            errs += top_error(out[0], out[1], y[0], y[1]).cpu().tolist()
            sw = ((out[3] > 0).float() != y[2]).float() * y[3]
            sws += (sw.sum(-1) / y[3].sum(-1).clamp(min=1)).cpu().tolist()
            hit = torch.stack([(out[4][m].argmax(-1) == y[4][:, m]).float() * y[5][:, m] for m in range(len(out[4]))], -1)
            mics += (hit.sum(-1) / y[5].sum(-1).clamp(min=1)).cpu().tolist()
            nll.append(float(SM.loss_fn(out, *y)))

    def per(vals):
        d = {}
        for i, e in zip(who, vals):
            d.setdefault(str(i), []).append(e)
        return {i: sum(v) / len(v) for i, v in d.items()}

    return per(errs), sum(nll) / max(1, len(nll)), {"switch_error": per(sws), "mic_agreement": per(mics)}


class StepsSkipped(Exception):
    pass


MAX_SKIP_SHARE = 0.05                          # an epoch skipping more non-finite steps than this aborts the run


def train_one(data, train_ix, es_ix, vals, seed, dev, log):
    import numpy as np
    import torch

    from learn import song_model as SM

    torch.manual_seed(seed)
    net = build_net().to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    best, bad, state = math.inf, 0, None
    rng = np.random.default_rng(seed)
    for epoch in range(EPOCHS):
        net.train()
        t0 = time.time()
        order = rng.permutation(train_ix)
        tl, skipped, steps = [], 0, 0
        for j in range(0, len(order), BATCH):
            x, c, y = data.batch(order[j:j + BATCH], epoch, dev)
            loss = SM.loss_fn(net(x, c), *y)
            opt.zero_grad()
            loss.backward()
            g = torch.nn.utils.clip_grad_norm_(net.parameters(), 1e9)
            steps += 1
            if torch.isfinite(g) and torch.isfinite(loss):
                for q in net.parameters():
                    if q.grad is not None:
                        q.grad.mul_(min(1.0, 5.0 / (float(g) + 1e-9)))
                opt.step()
                tl.append(float(loss))
            else:
                skipped += 1
        net.eval()
        with torch.no_grad():
            el = []
            for j in range(0, len(es_ix), BATCH):
                x, c, y = data.batch(es_ix[j:j + BATCH], -1, dev)          # one fixed draw for every epoch
                el.append(float(SM.loss_fn(net(x, c), *y)))
        v = sum(el) / max(1, len(el))
        dt = max(time.time() - t0, 1e-9)
        log.append({"epoch": epoch, "train": sum(tl) / max(1, len(tl)), "early_stop": v, "seconds": round(dt, 1),
                    "samples_per_s": round(len(order) / dt, 1), "skipped_steps": skipped, "steps": steps})
        print(log[-1], flush=True)
        if skipped > MAX_SKIP_SHARE * max(1, steps):
            raise StepsSkipped(f"epoch {epoch}: {skipped} of {steps} steps non-finite")
        if math.isfinite(v) and v < best - 1e-4:
            best, bad = v, 0
            state = {k: t.detach().cpu().clone() for k, t in net.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    if state is None:
        raise StepsSkipped("no finite early-stopping loss in any epoch")
    net.load_state_dict(state)
    net.eval()
    return {name: evaluate(net, val, dev) for name, val in vals.items()}, state


def curve_runs(n_final):
    """[(label, n, seed, half_sections)]: the sizes up to n_final (two seeds below 20k, three from
    20k), and the diversity axis (20k over half the train sections, one seed)."""
    sizes = [x for x in SIZES if x <= n_final]
    k = 2 * SIZES[-1]
    while k <= n_final:
        sizes.append(k)
        k *= 2
    out = []
    for n in sizes:
        seeds = CURVE_SEEDS[:SEEDS_SMALL] if n < 20_000 else CURVE_SEEDS
        out += [(str(n), n, s, False) for s in seeds]
    if n_final >= 2 * HALF_SECTIONS_N:
        out.append(("20000-halfsec", HALF_SECTIONS_N, CURVE_SEEDS[0], True))
    return out


def frozen_threshold(rows):
    """The scope threshold, computed once from the pilot's examples and reused (amendment 1, item 15)."""
    f = OUT / "scope-threshold.json"
    t = _load(f)
    if t is None:
        t = beyond_threshold(rows)
        _save(f, t)
    return t


def cmd_curve(args):
    """Train the half-width model on nested prefixes and read the val bands (one GPU job)."""
    import numpy as np
    import torch

    from learn import song_bank as B

    rows = all_rows()
    thr = frozen_threshold([r for r in rows.values() if r["i"] < N_PILOT or r["i"] >= VAL_BASE])
    tr_all = [rows[i] for i in sorted(rows) if i < args.n and not is_beyond(rows[i], thr)]
    va = [rows[i] for i in sorted(rows) if i >= VAL_BASE]
    lv = json.loads((B.OUT / "levels.json").read_text())
    data = CurveData(tr_all, ratio_values(), lv["summary"]["eval_mix_lufs_median"])
    vals = {"true": val_tensors(va), "powersum": val_tensors(va, powersum=True),
            "clean_stem": val_tensors(va, clean_stem=True)}
    p = pool()
    tr_secs = sorted(s["id"] for s in p["sections"] if s["split"] == "train" and not s["early_stop"])
    half = set(tr_secs[:len(tr_secs) // 2])
    dev = torch.device("mps" if torch.backends.mps.is_available() and os.environ.get("CURVE_DEVICE") != "cpu" else "cpu")
    res = _load(OUT / "curve.json") or {"runs": {}}
    res["scope_threshold"] = thr
    for label, n, seed, halfsec in curve_runs(args.n):
        key = f"{label}-{seed}"
        if key in res["runs"]:
            continue
        lim = 2 * n if halfsec else n
        ix = [j for j, r in enumerate(tr_all) if r["i"] < lim and (not halfsec or r["section"] in half or r["early_stop"])]
        tr = np.array([j for j in ix if not tr_all[j]["early_stop"]])
        es = np.array([j for j in ix if tr_all[j]["early_stop"]])
        if not len(es) or not len(tr):
            raise SystemExit(f"{key}: {len(tr)} training and {len(es)} early-stopping examples")
        t0 = time.time()
        for attempt in (1, 2):
            log = []
            try:
                out, state = train_one(data, tr, es, vals, seed, dev, log)
                break
            except StepsSkipped as e:
                print(f"{key}: attempt {attempt} aborted: {e}", flush=True)
                if dev.type == "mps":
                    torch.mps.empty_cache()
                if attempt == 2:
                    raise SystemExit(f"CURVE FAILED {key}: {e}")
        (OUT / "curve-models").mkdir(parents=True, exist_ok=True)
        torch.save(state, OUT / "curve-models" / f"{key}.pt")
        res["runs"][key] = {"label": label, "n": n, "seed": seed, "half_sections": halfsec, "train": len(tr),
                            "early_stop": len(es), "val_nll": out["true"][1], "per_example": out["true"][0],
                            "per_example_powersum": out["powersum"][0], "per_example_clean_stem": out["clean_stem"][0],
                            "switch_error": out["true"][2]["switch_error"], "mic_agreement": out["true"][2]["mic_agreement"],
                            "attempts": attempt, "log": log,
                            "minutes": round((time.time() - t0) / 60, 1), "device": str(dev)}
        _save(OUT / "curve.json", res)
        print("curve", key, "train", len(tr), "minutes", res["runs"][key]["minutes"], flush=True)
    print("CURVE DONE", args.n)


def seed_avg(runs, keep):
    """{example: mean over the runs} on the examples every run has and `keep` allows."""
    keys = set.intersection(*(set(r) for r in runs)) & keep
    return {i: sum(r[i] for r in runs) / len(runs) for i in keys}


def by_band(per, band_of):
    out = {}
    for i, e in per.items():
        out.setdefault(band_of[i], []).append(e)
    return out


def curve_table(res, band_of, keep, field="per_example"):
    """E(n) per size (seed-averaged, band-weighted, with intervals), and each doubling's Δ: seed-
    averaged and per seed (seed k at n against seed k at 2n)."""
    runs = {}
    for r in res["runs"].values():
        if not r.get("half_sections"):
            runs.setdefault(r["n"], {})[r["seed"]] = r[field]
    E = {n: band_t_interval(by_band(seed_avg(list(rs.values()), keep), band_of)) for n, rs in runs.items()}
    deltas = {}
    ns = sorted(runs)
    for a, b in zip(ns, ns[1:]):
        pa, pb = seed_avg(list(runs[a].values()), keep), seed_avg(list(runs[b].values()), keep)
        d = {"avg": band_t_interval(by_band({i: pb[i] - pa[i] for i in set(pa) & set(pb)}, band_of))}
        for s in sorted(set(runs[a]) & set(runs[b])):
            qa, qb = runs[a][s], runs[b][s]
            d[str(s)] = band_t_interval(by_band({i: qb[i] - qa[i] for i in set(qa) & set(qb) & keep}, band_of))
        deltas[f"{a}->{b}"] = d
    return E, deltas


def decide_full(d, prev_point):
    """(decision, reading). EXTEND when the seed-averaged interval and every seed's lie below 0;
    otherwise STOP, read 'flat' only when the interval rules out a gain half the previous doubling's."""
    seeds = [v for k, v in d.items() if k != "avg"]
    if decide(d["avg"]) == "EXTEND" and seeds and all(decide(v) == "EXTEND" for v in seeds):
        return "EXTEND", "improving"
    lo = d["avg"][1]
    if prev_point is not None and prev_point < 0 and lo > 0.5 * prev_point:
        return "STOP", "flat"
    return "STOP", "undecided"


def cmd_decide(args):
    res = _load(OUT / "curve.json")
    rows = all_rows()
    thr = res["scope_threshold"]
    band_of = {str(i): r["band"] for i, r in rows.items()}
    keep_in = {str(i) for i, r in rows.items() if r["split"] == "val" and not is_beyond(r, thr)}
    keep_all = {str(i) for i, r in rows.items() if r["split"] == "val"}
    E, deltas = curve_table(res, band_of, keep_in)
    E_all, _ = curve_table(res, band_of, keep_all)
    E_ps, _ = curve_table(res, band_of, keep_in, "per_example_powersum")
    ns = sorted(E)
    if args.n not in E or len(ns) < 2:
        raise SystemExit(f"no curve at {args.n}")
    prev = ns[ns.index(args.n) - 1]
    d = deltas[f"{prev}->{args.n}"]
    pk = f"{ns[ns.index(prev) - 1]}->{prev}" if ns.index(prev) > 0 else None
    out, reading = decide_full(d, deltas[pk]["avg"][0] if pk else None)
    if out == "EXTEND" and not disk_ok(DISK_GUARD_GB + 3.0):
        out, reading = "STOP", "disk"
    _save(OUT / f"decide-{args.n}.json", {"E": {str(k): v for k, v in E.items()},
                                          "E_with_scope_tagged": {str(k): v for k, v in E_all.items()},
                                          "E_powersum_val": {str(k): v for k, v in E_ps.items()},
                                          "deltas": deltas, "decision": out, "reading": reading})
    for n in ns:
        print(f"E({n}) = {E[n][0]:.4f} [{E[n][1]:.4f}, {E[n][2]:.4f}] over {E[n][3]} bands")
    for k, v in deltas.items():
        print(f"delta {k} = {v['avg'][0]:+.4f} [{v['avg'][1]:+.4f}, {v['avg'][2]:+.4f}]; per seed "
              + ", ".join(f"{s}: {x[0]:+.4f} [{x[1]:+.4f}, {x[2]:+.4f}]" for s, x in v.items() if s != "avg"))
    print(f"READING {reading}")
    print(f"DECISION {out}")


def cmd_report(_args):
    """Counts, class shares, scope tags, the power-sum audit and disk, from what is stored."""
    import numpy as np

    from collections import Counter

    rows = list(all_rows().values())
    thr = _load(OUT / "scope-threshold.json") or beyond_threshold(rows)
    rep = {"examples": len(rows), "train": sum(r["split"] == "train" for r in rows),
           "val": sum(r["split"] == "val" for r in rows), "audit": sum(bool(r.get("audit")) for r in rows),
           "class_by_mode": {f"{k[0]}|{k[1]}": v for k, v in Counter((r["mode"], r["gain"]["class"]) for r in rows).items()},
           "beyond_threshold": thr, "beyond": sum(is_beyond(r, thr) for r in rows),
           "seconds_median": float(np.median([r["seconds"] for r in rows])) if rows else None,
           "disk_gb": sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file()) / 1e9}
    errs = []
    for r in rows:
        if not r.get("audit"):
            continue
        d = np.load(example_path(r["i"]))
        meta = json.loads(backing_path(r["section"]).with_suffix(".json").read_text())
        kind = "v" if r["mix"]["vocals"] else "n"
        bz = np.load(backing_path(r["section"]))
        gb, gl, ga = r["mix"]["gains_db"]
        for h in "AB":
            true = dequant(d[f"m{h}"])
            approx = powersum_db(dequant(d[f"g{h}"]), dequant(bz[f"{kind}{h}"]), gb, ga)
            keep = true >= true.max(axis=0, keepdims=True) - 60
            errs.append(np.abs(approx - true)[keep])
        del meta
    if errs:
        e = np.concatenate(errs)
        rep["powersum_abs_db"] = {"median": float(np.median(e)), "p90": float(np.percentile(e, 90)),
                                  "p99": float(np.percentile(e, 99))}
    _save(OUT / "report.json", rep)
    print(json.dumps(rep, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gate")
    sub.add_parser("pool")
    sub.add_parser("backings")
    r = sub.add_parser("render")
    r.add_argument("--shard", type=lambda s: tuple(int(x) for x in s.split("/")), required=True)
    r.add_argument("--n", type=int, default=N_PILOT)
    r.add_argument("--n-val", type=int, default=N_VAL)
    sub.add_parser("recheck")
    c = sub.add_parser("curve")
    c.add_argument("--n", type=int, default=N_PILOT)
    d = sub.add_parser("decide")
    d.add_argument("--n", type=int, default=N_PILOT)
    sub.add_parser("report")
    a = ap.parse_args(argv)
    {"gate": cmd_gate, "pool": cmd_pool, "backings": cmd_backings, "render": cmd_render, "recheck": cmd_recheck, "curve": cmd_curve,
     "decide": cmd_decide, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
