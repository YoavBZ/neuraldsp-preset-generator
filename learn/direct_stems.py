"""The direct model with realistic stems (`docs/direct-model-stems-plan.md`, amendment 1 in force).
Development data only. Gate 1's zero-render checks (steps 1a, 1b), 1c, the pilot build and the
pilot (step 2). Steps 3-4 are not implemented yet.

    MSST=~/ndsp-presets/tools/msst-venv/bin/python; TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MSST     -m learn.direct_stems separate --sep mega53     # Mega-53 fast: audit true mixes + stage F crops
    $TORCH_PY -m learn.direct_stems separate --sep htdemucs   # htdemucs: audit true mixes
    $TORCH_PY -m learn.direct_stems move                      # 1a: stem-swap movement, the audit cost, GATE1
    $TORCH_PY -m learn.direct_stems reliance                  # 1b: stem vs mix reliance (V_dev, stage F)
    $MSST     -m learn.direct_stems sepcheck                  # 1c: fast vs stored Mega-53 (MPS), SEPCHECK FAST|STORED
    .venv/bin/python -m learn.direct_stems build --part pilot --stage mix --shard k/3   # renders + true mixes
    .venv/bin/python -m learn.direct_stems build --part vsep --stage mix --shard k/3
    $MSST     -m learn.direct_stems build --part pilot --stage stem --sep mega53 --device mps --order asc
    $MSST     -m learn.direct_stems build --part pilot --stage stem --sep mega53 --device cpu --order desc
    $TORCH_PY -m learn.direct_stems build --part vsep --stage stem --sep htdemucs
    $TORCH_PY -m learn.direct_stems train --arm D0|Dmix|Dstem|Dstem-noaug --n 5000 --seed 20261042|20261043
    $TORCH_PY -m learn.direct_stems pilot-report              # PILOT STOP | PILOT MIX | PILOT STEM

Outputs go to ~/ndsp-presets/learn/direct-stems/ (gate 1 under gate1/, 1c under sepcheck/, the
build under build/, the pilot's runs under pilot/).

**1a.** D_existing (part C's three 40k curve models, hashes checked against
`direct-existing/predictions.json`) reads stage F's 126 directions with the stored mix crop held
fixed and the stem swapped: a (the amp track), a' (the amp track plus the part's own backing at a
leak drawn U(0, 6) dB below the guitar, as part C; three draws per direction), b (htdemucs, as
stored), c (Mega-53, as stored), c_f (Mega-53 fast, the 10-s crop alone), z (stem zeroed), m (stem
:= mix). Each condition runs with its own stem LUFS (as at inference) and with the stem LUFS held at
b's. Per seed: movement (mean |delta| of the top-component means over the amp's labelled continuous
settings), switch and mic agreement, and the likelihood shift. Band-weighted with 90% band-bootstrap
intervals (4,000 draws). The audit cost: E on the 164 non-stage-F audit examples under (i) the
training stem, (ii) the guitar alone, (iii) Mega-53 fast, (iv) htdemucs of the true mix.
Prints `GATE1 STEM` or `GATE1 MIX-ONLY`.

**1b.** E on V_dev (part C's val examples of the 5 non-stage-F val bands) under stem or mix zeroed,
shuffled, stem := mix, stem := guitar alone; and stage F movement with the mix zeroed or shuffled.
Descriptive.

**1c.** Gate 1's Mega-53 fast stems of the 164 audit true mixes (hashes recorded and checked, five
re-separated on MPS within 60 dB) against the stored setting on MPS; SNR against the rendered
guitar, paired, band-clustered t (6 bands). Fast if the interval reaches 0 or lies above it.

**The build.** The band-clean pool (21,311 examples, 277 sections, 9 bands; every exclusion asserted,
recounted and printed), split into the pilot (5k stratified by band and amp, seed 20261073, plus the
1,000 early-stopping examples), the rest and V_sep (V_dev's 1,720). Per example, deterministic
from its index: the guitar re-rendered (isolated, one discarded priming render first, 0.25 s
trimmed) and refused unless its mels match part C's within one step on 99% of cells; the true mix
with its section's backing rebuilt from the session's tracks (checked against part C's stored
backing); mastering p 0.5 (seed 20261076). The mix stage stores the mix mels and exact half LUFS;
the stem stage re-renders, checks the mix reproduces, and separates (Mega-53 in 1c's setting;
htdemucs for V_sep). Disk guard 31 GB (pilot build: down to 26 GB, logged), memory and swap guards.

**The pilot.** D0 (part C's composition), D_mix (stem zeroed), D_stem (mix zeroed, augmented:
separator failure, merged training-pool guitar, drop-outs, darkening, in that order) and
D_stem-noaug; part C's net and recipe, at most 40 epochs, patience 4. `pilot-report` reads R_out
(unmastered V_sep, htdemucs stem) and R_in (V_sep, Mega-53 stem), Bannockburn and every
MUSDB18-tagged section left out, and applies amendment 1's rules.

The pure parts are unit-tested (`tests/test_direct_stems.py`); the commands that load models or
separators are not, like the other step modules.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import re
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/direct-stems/gate1"
DE_OUT = HOME / "learn/direct-existing"
LEAK_SEED = 20261071                  # a' leak draws
BOOT_SEED = 20261078                  # band bootstrap
SHUFFLE_SEED = 20261079               # 1b shuffles (stated in the results; the plan gave no seed)
BOOT_N = 4000
N_LEAK = 3
LEAK_DB = (0.0, 6.0)                  # pretrain_set.STEM_LEAK_DB
FAST_CHUNK = 441_000                  # Mega-53 fast: one 10-s chunk at 44.1 kHz, overlap 1
FAST_OVERLAP = 1
MUSDB_SONGS = ("It Was My Fault For Waiting", "Femme", "Signs")
THREADS = 4
REPRO_TOL = 1e-4                      # the stored D_existing run's pooled weight, reproduced
BACKING_TOL = 1e-4                    # mix - reference against backing.wav


def _save(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


def _load(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else None


# --- pure helpers ------------------------------------------------------------------------------------

def norm_name(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def is_musdb(slug, songs=MUSDB_SONGS):
    n = f" {norm_name(slug)} "
    return any(f" {norm_name(s)} " in n for s in songs)


def leak_draws(dirs, seed=LEAK_SEED, n=N_LEAK, lo_hi=LEAK_DB):
    """{direction key: [leak dB] * n}, drawn in the sorted order of the directions."""
    rng = random.Random(seed)
    return {k: [rng.uniform(*lo_hi) for _ in range(n)] for k in sorted(dirs)}


def leak_gain_db(lufs_guitar, lufs_backing, leak_db):
    """The backing's gain so it sits `leak_db` below the guitar (part C's `mix_gains_db` rule,
    the backing's read capped at 40 dB below the guitar)."""
    lb = max(lufs_backing, lufs_guitar - 40.0)
    return lufs_guitar - leak_db - lb


def training_stem(ref, backing, leak_db, lufs):
    """a': the amp track plus its own backing `leak_db` below it (LUFS over the whole clip)."""
    import numpy as np

    g = leak_gain_db(lufs(ref), lufs(backing), leak_db)
    return np.asarray(ref, np.float64) + np.asarray(backing, np.float64) * 10 ** (g / 20)


def derangement_avoid(keys, group_of, avoid, seed, max_tries=10_000):
    """{key: partner}: within each group a random permutation where no key gets a partner for which
    `avoid(key, partner)` holds (retried; SystemExit if impossible)."""
    rng = random.Random(seed)
    groups = {}
    for k in sorted(keys):
        groups.setdefault(group_of(k), []).append(k)
    out = {}
    for g in sorted(groups):
        ks = groups[g]
        for _ in range(max_tries):
            p = ks[:]
            rng.shuffle(p)
            if all(not avoid(a, b) for a, b in zip(ks, p)):
                out.update(zip(ks, p))
                break
        else:
            raise SystemExit(f"no admissible shuffle in group {g!r}")
    return out


def top(logpi, mu):
    import numpy as np

    return np.asarray(mu, np.float64)[int(np.argmax(logpi))]


def movement(ox, oy, cm, swm, km):
    """One seed's answer movement between two inputs. o = (logpi [K], mu [K, n], ls [K, n],
    swl [n_sw], [cat logits]); masks over the continuous, switch and mic dims.
    -> (mean |delta top mean| over cm, switch agreement, mic agreement)."""
    import numpy as np

    cm, swm, km = (np.asarray(m, bool) for m in (cm, swm, km))
    d = float(np.abs(top(ox[0], ox[1]) - top(oy[0], oy[1]))[cm].mean())
    sx, sy = np.asarray(ox[3]) > 0, np.asarray(oy[3]) > 0
    sw = float((sx == sy)[swm].mean()) if swm.any() else math.nan
    mx = np.array([int(np.argmax(z)) for z in ox[4]])
    my = np.array([int(np.argmax(z)) for z in oy[4]])
    mic = float((mx == my)[km].mean()) if km.any() else math.nan
    return d, sw, mic


def mixture_logp(o, theta, cm):
    """log p(theta) under the seed's mixture over the masked continuous dims, per dim (nats)."""
    import numpy as np

    logpi, mu, ls = (np.asarray(v, np.float64) for v in o[:3])
    cm = np.asarray(cm, bool)
    z = (np.asarray(theta, np.float64)[None] - mu) / np.exp(ls)
    lp = ((-0.5 * z ** 2 - ls - 0.5 * math.log(2 * math.pi)) * cm[None]).sum(-1)
    a = logpi + lp
    m = a.max()
    return float((m + math.log(np.exp(a - m).sum())) / max(1, cm.sum()))


def likelihood_shift(ox, oy, cm):
    """log p_x(theta_x | x) - log p_x(theta_y | x): how unlikely y's answer looks to the model on x."""
    return mixture_logp(ox, top(ox[0], ox[1]), cm) - mixture_logp(ox, top(oy[0], oy[1]), cm)


def top_error(o, c, cm):
    """One seed's continuous error against a label: mean |top mean - theta| over the label's mask."""
    import numpy as np

    cm = np.asarray(cm, bool)
    return float(np.abs(top(o[0], o[1]) - np.asarray(c))[cm].mean())


def band_weighted(rows):
    """rows: (band, part, value). Part means, then band means, then the mean of bands.
    -> (mean, {band: mean})."""
    parts = {}
    for b, p, v in rows:
        parts.setdefault((b, p), []).append(v)
    bands = {}
    for (b, _), vs in parts.items():
        bands.setdefault(b, []).append(sum(vs) / len(vs))
    bm = {b: sum(v) / len(v) for b, v in bands.items()}
    return (sum(bm.values()) / len(bm) if bm else math.nan), bm


def bootstrap(rows, n=BOOT_N, seed=BOOT_SEED):
    """Band-weighted mean with a 90% band-bootstrap interval (bands resampled with replacement)."""
    m, bm = band_weighted(rows)
    bands = sorted(bm)
    if len(bands) < 2:
        return {"mean": m, "lo90": None, "hi90": None, "bands": len(bands)}
    rng = random.Random(seed)
    vals = sorted(sum(bm[rng.choice(bands)] for _ in bands) / len(bands) for _ in range(n))
    return {"mean": m, "lo90": vals[int(0.05 * n)], "hi90": vals[int(0.95 * n) - 1], "bands": len(bands),
            "bands_positive": sum(v > 0 for v in bm.values())}


def t_interval(rows):
    """Band-weighted mean with a 90% band-clustered t interval (bands - 1 df)."""
    from learn import pretrain_set as PS

    _, bm = band_weighted(rows)
    by = {b: [v] for b, v in bm.items()}
    m, lo, hi, n = PS.band_t_interval(by) if by else (math.nan, None, None, 0)
    return {"mean": m, "lo90": lo if n > 1 else None, "hi90": hi if n > 1 else None, "bands": n,
            "bands_positive": sum(v > 0 for v in bm.values())}


def above_zero(s):
    return s is not None and s.get("lo90") is not None and s["lo90"] > 0


def gate1(f_rows, audit_cost):
    """The declared gate: the stem matters if any of d(a', b) - null or d(a, b) - null on stage F
    (all bands or the unseen bands), or the audit cost (iii) - (i), has an interval entirely above 0.
    f_rows: {contrast: {row: interval}}. -> (decision, [reasons])."""
    why = []
    for c in ("d(a',b)-null", "d(a,b)-null"):
        for r in ("all", "unseen_by_part_c"):
            if above_zero(f_rows.get(c, {}).get(r)):
                why.append(f"{c} on {r}")
    if above_zero(audit_cost):
        why.append("audit (iii)-(i)")
    return ("STEM" if why else "MIX-ONLY"), why


# --- shared model plumbing ---------------------------------------------------------------------------

def load_nets():
    import torch

    from learn import direct_existing as DE
    from learn import pretrain_set as PS

    torch.set_num_threads(THREADS)
    stored = _load(DE_OUT / "predictions.json")
    nets = []
    for p in DE.model_paths():
        if DE.sha256(p) != stored["models"][p.name]:
            raise SystemExit(f"{p.name}: hash differs from direct-existing's")
        net = PS.build_net()
        net.load_state_dict(torch.load(p, map_location="cpu"))
        nets.append(net.eval())
    return nets


def run_nets(nets, X, C, batch=128):
    """-> per seed, per row: (logpi, mu, ls, swl, [cat logits]) as numpy."""
    import numpy as np
    import torch

    outs = [[] for _ in nets]
    with torch.no_grad():
        for j in range(0, len(X), batch):
            x = torch.tensor(np.asarray(X[j:j + batch], np.float32))
            c = torch.tensor(np.asarray(C[j:j + batch], np.float32))
            for k, net in enumerate(nets):
                lp, mu, ls, sw, cat = net(x, c)
                for n in range(len(x)):
                    outs[k].append((lp[n].numpy(), mu[n].numpy(), ls[n].numpy(), sw[n].numpy(),
                                    [z[n].numpy() for z in cat]))
    return outs


def feat(stem_db, mix_db, half):
    """Normalised, half-A-masked input from dB mels (already quantised)."""
    import numpy as np

    from learn import pretrain_set as PS
    from learn import song_model as SM

    return PS.mask_half_a(SM.norm_feat(np.stack([stem_db, mix_db]))[None], [half == "A"])[0]


def qmel(y):
    from learn import pretrain_set as PS
    from learn import song_aug as SA

    q = PS.quant(SA.logmel(y))
    return PS.dequant(q), float((q == 0).mean())


def masks(amp, cls):
    """(continuous, switch, mic) masks of the amp's labelled dims (`knob_ceiling.space` at the
    class's S; it equals part C's label keys per amp and class, checked by hand 2026-10-19)."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import knob_ceiling as K
    from learn import song_model as SM

    _, S = A.L.menu_S()[amp][cls]
    names = {d.name for d in K.space(amp, S)}
    return (np.array([n in names for n in SM.CONT]), np.array([n in names for n in SM.SW]),
            np.array([n in names for n in SM.CAT]))


# --- separation (msst-venv for Mega-53, demucs-venv for htdemucs) -------------------------------------

def audit_rows():
    from learn import arm_a_mega53 as A
    from learn import pretrain_set as PS

    F = set(A.F_POOL)
    rows = sorted((r for r in PS.all_rows().values() if r.get("audit") and r["band"] not in F), key=lambda r: r["i"])
    if len(rows) != 164 or any(r["mix"].get("mastered") for r in rows):
        raise SystemExit(f"{len(rows)} non-stage-F audit rows (plan: 164, unmastered)")
    return rows


def audit_audio(r):
    """(guitar render, backing at the mix's gain, backing at the stem's gain, overall gain dB)."""
    import soundfile as sf

    from learn import pretrain_set as PS

    y, _ = sf.read(str(PS.example_path(r["i"]).with_suffix(".flac")), dtype="float64")
    y = y / 0.99 * r["peak"]
    b, _ = PS.load_backing_audio(r["section"], "v" if r["mix"]["vocals"] else "n")
    gb, gl, ga = r["mix"]["gains_db"]
    return y, b * 10 ** (gb / 20), b * 10 ** (gl / 20), ga


def stem_path(sep, kind, key):
    return OUT / "stems" / sep / kind / f"{key}.npy"


def separator(sep):
    if sep == "mega53":
        from learn import separator_screen as SCR

        s = SCR.MsstSeparator(prune=True)
        s.config.inference.chunk_size = FAST_CHUNK
        s.config.inference.num_overlap = FAST_OVERLAP
        return s
    from learn import separator_screen as SCR

    return SCR.htdemucs()


def cmd_separate(args):
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR
    from learn import pretrain_set as PS

    if not PS.disk_ok(guard=20.0):
        raise SystemExit("free disk below 20 GB")
    sep = separator(args.sep)
    jobs = [("audit", str(r["i"]), r) for r in audit_rows()]
    if args.sep == "mega53":
        jobs += [("stagef", s, None) for s in A.pool_slugs()]
    t0, n = time.time(), 0
    for kind, key, r in jobs:
        p = stem_path(args.sep, kind, key)
        if p.exists():
            continue
        if kind == "audit":
            y, bm, _, _ = audit_audio(r)
            x = y + bm
        else:
            x = CR.mono(A.f_part(key)["crop"] / "mix.wav")
        s = np.asarray(sep(x), np.float32)
        if len(s) != len(x) or not np.isfinite(s).all():
            raise SystemExit(f"{kind} {key}: bad stem")
        p.parent.mkdir(parents=True, exist_ok=True)
        np.save(p.with_suffix(".tmp.npy"), s)
        p.with_suffix(".tmp.npy").replace(p)
        n += 1
        if n % 10 == 0:
            print(f"{args.sep}: {n} done, {(time.time() - t0) / n:.1f} s each", flush=True)
    info = sep.info() if hasattr(sep, "info") else {}
    info.pop("pip_freeze", None)
    _save(OUT / "stems" / args.sep / "run.json", {"separator": args.sep, "info": info, "jobs": len(jobs),
                                                    "fast": args.sep == "mega53", "chunk_size": FAST_CHUNK if args.sep == "mega53" else None,
                                                    "num_overlap": FAST_OVERLAP if args.sep == "mega53" else None,
                                                    "seconds": round(time.time() - t0, 1), "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"SEPARATE {args.sep}: {len(jobs)} stems ({n} new) in {time.time() - t0:.0f} s")


# --- 1a and the stage F reliance rows ----------------------------------------------------------------

STEM_CONDS = ("a", "b", "c", "c_f", "m") + tuple(f"a'{j}" for j in range(N_LEAK))


def stage_f_inputs():
    """Per part: the stored mix crop (hash-checked), stems b and c, the amp track, the backing,
    c_f, gain; and the direction list."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR
    from learn import direct_existing as DE
    from learn import song_aug as SA

    stored = _load(DE_OUT / "predictions.json")
    parts = {}
    for slug in A.pool_slugs():
        mix, stem_b, h = DE.f_inputs(slug, "htdemucs")
        if h != stored["inputs"][slug]:
            raise SystemExit(f"{slug}: htdemucs inputs differ from the stored run")
        _, stem_c, _ = DE.f_inputs(slug, "mega53")
        crop = A.f_part(slug)["crop"]
        ref = CR.mono(crop / "reference.wav")
        back = mix - ref
        bwav = CR.mono(crop / "backing.wav")
        dev = float(np.max(np.abs(back - bwav)))
        cf = np.load(stem_path("mega53", "stagef", slug)).astype(np.float64)
        parts[slug] = {"mix": mix, "b": stem_b, "c": stem_c, "a": ref, "back": back, "c_f": cf,
                       "backing_dev": dev, "gain_db": DE.inference_gain_db(mix, stored["target_mix_lufs"]),
                       "lufs_ref": SA.lufs(ref), "lufs_back": SA.lufs(back)}
        if dev > BACKING_TOL:
            raise SystemExit(f"{slug}: mix - reference differs from backing.wav by {dev:.2e}")
    return parts, stored


def half_input(stem, mix, half, gain_stem_db, gain_mix_db):
    """(stem dB mel, mix dB mel, stem LUFS, mix LUFS, stem floor share) of one half."""
    from learn import direct_existing as DE
    from learn import pretrain_set as PS
    from learn import song_aug as SA

    sl = PS.half_slices()[half]
    s = DE.mono(stem)[sl] * 10 ** (gain_stem_db / 20)
    m = DE.mono(mix)[sl] * 10 ** (gain_mix_db / 20)
    sd, fl = qmel(s)
    md, _ = qmel(m)
    return sd, md, SA.lufs(s), SA.lufs(m), fl


def cmd_move(args):
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import song_model as SM
    from learn import song_aug as SA

    nets = load_nets()
    parts, stored = stage_f_inputs()
    dirs = A.stage_dirs("F")
    keys = [f"{s}|{a}|{sh}" for s, a, sh, _ in dirs]
    leaks = leak_draws(keys)
    slugs = sorted(parts)
    band_of = {s: A.f_part(s)["band"] for s in slugs}
    sh_stem = derangement_avoid(slugs, lambda s: 0, lambda x, y: band_of[x] == band_of[y], SHUFFLE_SEED)
    sh_mix = derangement_avoid(slugs, lambda s: 0, lambda x, y: band_of[x] == band_of[y], SHUFFLE_SEED + 1)
    # per (slug, half): the mels of every stem and the mix, computed once
    X, C, who, floor, lufs_tab = [], [], [], {}, {}
    for slug, amp, search, held in dirs:
        p = parts[slug]
        k = f"{slug}|{amp}|{search}"
        g = p["gain_db"]
        cls = A.f_part(slug)["gain_class"]
        stems = {"a": p["a"], "b": p["b"], "c": p["c"], "c_f": p["c_f"], "m": p["mix"]}
        for j, ld in enumerate(leaks[k]):
            stems[f"a'{j}"] = training_stem(p["a"], p["back"], ld, SA.lufs)
        base = half_input(p["b"], p["mix"], search, g, g)
        lb_s, lb_m = base[2], base[3]
        for name, st in stems.items():
            sd, md, ls, lm, fl = half_input(st, p["mix"], search, g, g)
            floor[(k, name)] = fl
            lufs_tab[(k, name)] = ls
            for conv, lu in (("own", [ls, lm]), ("held", [lb_s, lm])):
                X.append(feat(sd, md, search))
                C.append(SM.cond_vec(amp, cls, lu))
                who.append((k, name, conv))
        # z: stem zeroed (LUFS held at b's); mix zeroed (b's stem, mix LUFS held)
        sd, md = base[0], base[1]
        x = feat(sd, md, search)
        xz = x.copy()
        xz[0] = 0
        X.append(xz), C.append(SM.cond_vec(amp, cls, [lb_s, lb_m])), who.append((k, "z", "held"))
        xm = x.copy()
        xm[1] = 0
        X.append(xm), C.append(SM.cond_vec(amp, cls, [lb_s, lb_m])), who.append((k, "mix0", "held"))
        # stem shuffled across parts (another band's b stem at its own gain); mix shuffled likewise
        q = parts[sh_stem[slug]]
        sd2, _, ls2, _, _ = half_input(q["b"], q["mix"], search, q["gain_db"], q["gain_db"])
        for conv, lu in (("own", [ls2, lb_m]), ("held", [lb_s, lb_m])):
            X.append(feat(sd2, md, search)), C.append(SM.cond_vec(amp, cls, lu)), who.append((k, "stem_shuf", conv))
        q = parts[sh_mix[slug]]
        _, md2, _, lm2, _ = half_input(q["b"], q["mix"], search, q["gain_db"], q["gain_db"])
        for conv, lu in (("own", [lb_s, lm2]), ("held", [lb_s, lb_m])):
            X.append(feat(sd, md2, search)), C.append(SM.cond_vec(amp, cls, lu)), who.append((k, "mix_shuf", conv))
    outs = run_nets(nets, X, C)
    O = {w: [outs[s][n] for s in range(len(nets))] for n, w in enumerate(who)}
    # reproduce the stored run (b, own LUFS) through the ensemble
    repro = 0.0
    for k in keys:
        _, _, _, diag = DE.ensemble([(o[0], o[1], o[3], o[4]) for o in O[(k, "b", "own")]])
        sd_ = stored["predictions"][k]["diag"]
        if diag["seed"] != sd_["seed"] or diag["component"] != sd_["component"]:
            raise SystemExit(f"{k}: ensemble choice differs from the stored run")
        repro = max(repro, abs(diag["pooled_weight"] - sd_["pooled_weight"]))
    if repro > REPRO_TOL:
        raise SystemExit(f"stored run not reproduced: pooled weight off by {repro:.2e}")
    unseen = set(stored["unseen_by_part_c"])
    per_dir = {}
    for slug, amp, search, held in dirs:
        k = f"{slug}|{amp}|{search}"
        cm, swm, km = masks(amp, A.f_part(slug)["gain_class"])

        def mv(x, y, conv="own", kk=k, cm=cm, swm=swm, km=km):
            ox, oy = O[(kk, x, conv if (kk, x, conv) in O else "held")], O[(kk, y, conv if (kk, y, conv) in O else "held")]
            r = [movement(ox[s], oy[s], cm, swm, km) + (likelihood_shift(ox[s], oy[s], cm),) for s in range(len(ox))]
            return [float(np.nanmean([v[i] for v in r])) for i in range(4)]

        rec = {"slug": slug, "band": band_of[slug], "amp": amp, "search": search, "musdb": is_musdb(slug),
               "unseen": band_of[slug] in unseen, "leaks_db": leaks[k],
               "floor": {n: floor[(k, n)] for n in STEM_CONDS}, "lufs": {n: lufs_tab[(k, n)] for n in STEM_CONDS}}
        for conv in ("own", "held"):
            m = {}
            ap = [f"a'{j}" for j in range(N_LEAK)]
            pairs = [(ap[i], ap[j]) for i in range(N_LEAK) for j in range(N_LEAK) if i != j]
            null = np.mean([mv(x, y, conv) for x, y in pairs], axis=0)
            m["null"] = null.tolist()
            for y in ("b", "c", "c_f", "z", "m", "stem_shuf"):
                m[f"a'|{y}"] = np.mean([mv(x, y, conv) for x in ap], axis=0).tolist()
            for x, y in (("a", "b"), ("a", "c"), ("a", "c_f"), ("b", "c"), ("c", "c_f"), ("b", "z"), ("b", "m"),
                         ("b", "mix0"), ("b", "mix_shuf"), ("b", "stem_shuf"), ("a", "z")):
                m[f"{x}|{y}"] = mv(x, y, conv)
            m["a|a'"] = np.mean([mv("a", y, conv) for y in ap], axis=0).tolist()
            rec[conv] = m
        per_dir[k] = rec
    # the readout
    rows_def = {"all": lambda r: True, "unseen_by_part_c": lambda r: r["unseen"], "no_musdb": lambda r: not r["musdb"]}
    contrasts = {
        "d(a',b)-null": lambda m: m["a'|b"][0] - m["null"][0],
        "d(a,b)-null": lambda m: m["a|b"][0] - m["null"][0],
        "d(a',c)-null": lambda m: m["a'|c"][0] - m["null"][0],
        "d(a',c_f)-null": lambda m: m["a'|c_f"][0] - m["null"][0],
        "d(a,c)-null": lambda m: m["a|c"][0] - m["null"][0],
        "dl(a',b)-null": lambda m: m["a'|b"][3] - m["null"][3],
        "dl(a,b)-null": lambda m: m["a|b"][3] - m["null"][3],
    }
    levels = {f"{x}|{y}": (lambda m, xy=f"{x}|{y}": m[xy]) for x, y in (
        ("a'", "b"), ("a'", "c"), ("a'", "c_f"), ("a", "b"), ("a", "c"), ("a", "c_f"), ("a", "a'"), ("b", "c"),
        ("c", "c_f"), ("b", "z"), ("b", "m"), ("b", "mix0"), ("b", "mix_shuf"), ("b", "stem_shuf"), ("a", "z"),
        ("a'", "z"), ("a'", "m"), ("a'", "stem_shuf"))}
    levels["null"] = lambda m: m["null"]
    rep = {"plan": "docs/direct-model-stems-plan.md 1a",
           "c_f": "Mega-53 fast (one 10-s chunk, overlap 1) on the crop alone; 1c not run, so not 'the setting 1c picks'",
           "decision_rule": "own stem LUFS decides, held reported; audit (iii)-(i) on the band t interval, bootstrap reported",
           "directions": len(per_dir), "repro_pooled_weight_max_dev": repro,
           "backing_dev_max": max(p["backing_dev"] for p in parts.values()), "shuffle_stem": sh_stem, "shuffle_mix": sh_mix,
           "contrasts": {}, "levels": {}, "floor_share_median": {}, "lufs_median": {}}
    for conv in ("own", "held"):
        rep["contrasts"][conv] = {c: {rn: bootstrap([(r["band"], r["slug"], f(r[conv])) for r in per_dir.values() if rf(r)])
                                      for rn, rf in rows_def.items()} for c, f in contrasts.items()}
        rep["levels"][conv] = {c: {nm: band_weighted([(r["band"], r["slug"], f(r[conv])[i]) for r in per_dir.values()
                                                       if not math.isnan(f(r[conv])[i])])[0]
                                   for i, nm in enumerate(("move", "switch_agree", "mic_agree", "dloglik"))}
                               for c, f in levels.items()}
    for n in STEM_CONDS:
        rep["floor_share_median"][n] = float(np.median([r["floor"][n] for r in per_dir.values()]))
        rep["lufs_median"][n] = float(np.median([r["lufs"][n] for r in per_dir.values()]))
    # the audit cost
    rep["audit"] = audit_cost(nets)
    dec, why = gate1(rep["contrasts"]["own"], rep["audit"]["contrasts"]["own"]["(iii)-(i)"])
    rep["gate1"] = {"decision": dec, "reasons": why, "convention": "own stem LUFS (as at inference)"}
    dec_h, why_h = gate1(rep["contrasts"]["held"], rep["audit"]["contrasts"]["held"]["(iii)-(i)"])
    rep["gate1_held_lufs"] = {"decision": dec_h, "reasons": why_h}
    rep["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save(OUT / "move.json", rep)
    _save(OUT / "move-directions.json", per_dir)
    for conv in ("own", "held"):
        print(f"[{conv} stem LUFS]")
        for c, v in rep["contrasts"][conv].items():
            print(f"  {c:16s}", "  ".join(f"{rn}: {fmt(s)}" for rn, s in v.items()))
        for c, v in rep["levels"][conv].items():
            print(f"  level {c:12s} move {v['move']:.4f} switch {v['switch_agree']:.3f} mic {v['mic_agree']:.3f} "
                  f"dloglik {v['dloglik']:+.3f}")
        print("  audit E", {k: round(v, 4) for k, v in rep["audit"]["E"][conv].items()})
        for c, s in rep["audit"]["contrasts"][conv].items():
            print(f"  audit {c:12s} {fmt(s)}")
    print("floor share", rep["floor_share_median"])
    print(f"GATE1 {dec}", why, "| held-LUFS reading:", dec_h, why_h)


def fmt(s):
    if not s or s.get("mean") is None or (isinstance(s["mean"], float) and math.isnan(s["mean"])):
        return "n/a"
    lo, hi = s.get("lo90"), s.get("hi90")
    return f"{s['mean']:+.4f}" + ("" if lo is None else f" [{lo:+.4f}, {hi:+.4f}]") + f" ({s['bands']}b)"


def audit_cost(nets):
    """E of D_existing on the 164 non-stage-F audit examples with the true mix and four stems."""
    import numpy as np

    from learn import direct_existing as DE
    from learn import pretrain_set as PS
    from learn import song_model as SM

    rows = audit_rows()
    X, C, who, Y, parity = [], [], [], {}, []
    for r in rows:
        y, bm, bl, ga = audit_audio(r)
        mix = y + bm
        stems = {"(i)": y + bl, "(ii)": y, "(iii)": np.load(stem_path("mega53", "audit", r["i"])).astype(np.float64),
                 "(iv)": np.load(stem_path("htdemucs", "audit", r["i"])).astype(np.float64)}
        Y[r["i"]] = SM.encode(r["label"])
        d = np.load(PS.example_path(r["i"]))
        for h in "AB":
            ins = {n: half_input(s, mix, h, ga, ga) for n, s in stems.items()}
            stored_s = PS.dequant(d[f"s{h}"])
            keep = np.ones(stored_s.shape, bool)
            if h == "A":
                keep[:, :PS.MASK_A_FRAMES] = False
            parity.append(float(np.mean(np.abs(ins["(i)"][0] - stored_s)[keep] <= PS.Q_STEP_DB + 1e-6)))
            held = ins["(i)"][2]
            for n, (sd, md, ls, lm, _) in ins.items():
                for conv, lu in (("own", [ls, lm]), ("held", [held, lm])):
                    X.append(feat(sd, md, h)), C.append(SM.cond_vec(r["amp"], r["base"], lu)), who.append((r["i"], n, conv))
    if min(parity) < DE.PARITY_CELL_SHARE:
        raise SystemExit(f"audit parity: worst share within one step {min(parity):.4f}")
    outs = run_nets(nets, X, C)
    E = {}
    for n_, (i, n, conv) in enumerate(who):
        c, cm = Y[i][0], Y[i][1]
        e = float(np.mean([top_error(outs[s][n_], c, cm) for s in range(len(nets))]))
        E.setdefault((conv, n, i), []).append(e)
    band = {r["i"]: r["band"] for r in rows}
    out = {"examples": len(rows), "bands": sorted(set(band.values())), "parity_worst_share": min(parity),
           "E": {}, "contrasts": {}}
    for conv in ("own", "held"):
        per = {n: {i: float(np.mean(E[(conv, n, i)])) for i in band} for n in ("(i)", "(ii)", "(iii)", "(iv)")}
        out["E"][conv] = {n: t_interval([(band[i], str(i), v) for i, v in per[n].items()])["mean"] for n in per}
        out["contrasts"][conv] = {f"{a}-{b}": t_interval([(band[i], str(i), per[a][i] - per[b][i]) for i in band])
                                  for a, b in (("(iii)", "(i)"), ("(iv)", "(i)"), ("(ii)", "(i)"), ("(iii)", "(iv)"))}
        out["contrasts"][conv]["(iii)-(i) bootstrap"] = bootstrap([(band[i], str(i), per["(iii)"][i] - per["(i)"][i]) for i in band])
    return out


# --- 1b: V_dev ---------------------------------------------------------------------------------------

def vdev_rows():
    from learn import arm_a_mega53 as A
    from learn import pretrain_set as PS

    F = set(A.F_POOL)
    rows = sorted((r for r in PS.all_rows().values() if r["split"] == "val" and r["band"] not in F), key=lambda r: r["i"])
    if len(rows) != 1720:
        raise SystemExit(f"V_dev has {len(rows)} examples, not the plan's 1,720")
    return rows


def cmd_reliance(args):
    import numpy as np

    from learn import pretrain_set as PS
    from learn import song_model as SM

    nets = load_nets()
    rows = vdev_rows()
    by_i = {r["i"]: r for r in rows}
    part = derangement_avoid([r["i"] for r in rows], lambda i: (by_i[i]["amp"], by_i[i]["base"]),
                             lambda a, b: by_i[a]["section"] == by_i[b]["section"], SHUFFLE_SEED)
    conds = ("stored", "stem0", "stem_shuf_own", "stem_shuf_held", "mix0", "mix_shuf_own", "mix_shuf_held",
             "stem=mix_own", "stem=mix_held", "stem=guitar_own", "stem=guitar_held", "both0",
             "guitar+mix0", "guitar+mix_shuf")     # the last two: post hoc, the clean-target-only reading
    E = {c: {} for c in conds}
    cache = {}

    def load(i):
        if i not in cache:
            cache[i] = np.load(PS.example_path(i))
        return cache[i]

    for j0 in range(0, len(rows), 200):
        X, C, who = [], [], []
        for r in rows[j0:j0 + 200]:
            d, q = load(r["i"]), load(part[r["i"]])
            rq = by_i[part[r["i"]]]
            for h in "AB":
                st, mx = PS.dequant(d[f"s{h}"]), PS.dequant(d[f"m{h}"])
                ls, lm = r["mix"][f"lufs_s{h}"], r["mix"][f"lufs_m{h}"]
                st2, mx2 = PS.dequant(q[f"s{h}"]), PS.dequant(q[f"m{h}"])
                ls2, lm2 = rq["mix"][f"lufs_s{h}"], rq["mix"][f"lufs_m{h}"]
                ga = r["mix"]["gains_db"][2]
                g = PS.dequant(d[f"g{h}"]) + ga
                lg = r[f"lufs_{h}"] + ga
                x = feat(st, mx, h)
                variants = {"stored": (x, [ls, lm]), "stem_shuf_own": (feat(st2, mx, h), [ls2, lm]),
                            "stem_shuf_held": (feat(st2, mx, h), [ls, lm]), "mix_shuf_own": (feat(st, mx2, h), [ls, lm2]),
                            "mix_shuf_held": (feat(st, mx2, h), [ls, lm]), "stem=mix_own": (feat(mx, mx, h), [lm, lm]),
                            "stem=mix_held": (feat(mx, mx, h), [ls, lm]), "stem=guitar_own": (feat(g, mx, h), [lg, lm]),
                            "stem=guitar_held": (feat(g, mx, h), [ls, lm])}
                x0 = x.copy()
                x0[0] = 0
                variants["stem0"] = (x0, [ls, lm])
                x1 = x.copy()
                x1[1] = 0
                variants["mix0"] = (x1, [ls, lm])
                x2 = x.copy()
                x2[:] = 0
                variants["both0"] = (x2, [ls, lm])
                xg = feat(g, mx, h)
                xg[1] = 0
                variants["guitar+mix0"] = (xg, [lg, lm])
                variants["guitar+mix_shuf"] = (feat(g, mx2, h), [lg, lm2])
                for c, (xx, lu) in variants.items():
                    X.append(xx), C.append(SM.cond_vec(r["amp"], r["base"], lu)), who.append((r["i"], c))
        outs = run_nets(nets, X, C)
        for n_, (i, c) in enumerate(who):
            y = SM.encode(by_i[i]["label"])
            e = float(np.mean([top_error(outs[s][n_], y[0], y[1]) for s in range(len(nets))]))
            E[c].setdefault(i, []).append(e)
        cache.clear()
        print(f"reliance: {min(j0 + 200, len(rows))}/{len(rows)}", flush=True)
    per = {c: {i: float(np.mean(v)) for i, v in E[c].items()} for c in conds}
    band = {r["i"]: r["band"] for r in rows}
    rep = {"plan": "docs/direct-model-stems-plan.md 1b", "examples": len(rows), "bands": sorted(set(band.values())),
           "E": {c: t_interval([(band[i], str(i), v) for i, v in per[c].items()])["mean"] for c in conds},
           "dE": {c: t_interval([(band[i], str(i), per[c][i] - per["stored"][i]) for i in band]) for c in conds if c != "stored"},
           "per_band_dE": {}}
    for c in conds[1:]:
        rep["per_band_dE"][c] = band_weighted([(band[i], str(i), per[c][i] - per["stored"][i]) for i in band])[1]
    # with a clean guitar stem, what does the mix add? (post hoc, the clean-target-only reading)
    rep["clean_target"] = {f"{a} - {b}": t_interval([(band[i], str(i), per[a][i] - per[b][i]) for i in band])
                           for a, b in (("guitar+mix0", "stem=guitar_own"), ("guitar+mix_shuf", "stem=guitar_own"))}
    _save(OUT / "reliance-per-example.json", {"band": {str(i): b for i, b in band.items()},
                                               "E": {c: {str(i): v for i, v in per[c].items()} for c in conds}})
    for a, b, name in (("stem0", "mix0", "zeroed"), ("stem_shuf_held", "mix_shuf_held", "shuffled_held"),
                       ("stem_shuf_own", "mix_shuf_own", "shuffled_own")):
        ds, dm = rep["dE"][a]["mean"], rep["dE"][b]["mean"]
        rep[f"stem_share_{name}"] = ds / (ds + dm) if (ds + dm) else None
    mo = _load(OUT / "move.json")
    if mo:
        rep["stage_f_movement"] = {c: mo["levels"][conv][c] for conv in ("own", "held")
                                   for c in ("b|z", "b|m", "b|mix0", "b|mix_shuf", "b|stem_shuf", "null")}
        rep["stage_f_movement_by_conv"] = {conv: {c: mo["levels"][conv][c] for c in
                                                  ("null", "b|z", "b|m", "b|mix0", "b|mix_shuf", "b|stem_shuf")}
                                           for conv in ("own", "held")}
        rep.pop("stage_f_movement")
    rep["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save(OUT / "reliance.json", rep)
    print("E", {c: round(v, 4) for c, v in rep["E"].items()})
    for c, s in rep["dE"].items():
        print(f"  dE {c:18s} {fmt(s)}")
    for c, s_ in rep["clean_target"].items():
        print(f"  clean target {c:34s} {fmt(s_)}")
    print("stem share", {k: rep[k] for k in rep if k.startswith("stem_share")})
    if mo:
        print(json.dumps(rep["stage_f_movement_by_conv"], indent=1))


def cmd_audit_mix(_args):
    """Post hoc (the audit's suggestion): on the 164 audit examples, what the mix adds behind each
    stem. E with the mix present against the mix channel zeroed (mix LUFS held), own stem LUFS."""
    import numpy as np

    from learn import song_model as SM

    nets = load_nets()
    rows = audit_rows()
    X, C, who, Y = [], [], [], {}
    for r in rows:
        y, bm, bl, ga = audit_audio(r)
        mix = y + bm
        stems = {"(i)": y + bl, "(ii)": y, "(iii)": np.load(stem_path("mega53", "audit", r["i"])).astype(np.float64),
                 "(iv)": np.load(stem_path("htdemucs", "audit", r["i"])).astype(np.float64)}
        Y[r["i"]] = SM.encode(r["label"])
        for h in "AB":
            for n, st in stems.items():
                sd, md, ls, lm, _ = half_input(st, mix, h, ga, ga)
                x = feat(sd, md, h)
                x0 = x.copy()
                x0[1] = 0
                for m, xx in (("mix", x), ("mix0", x0)):
                    X.append(xx), C.append(SM.cond_vec(r["amp"], r["base"], [ls, lm])), who.append((r["i"], n, m))
    outs = run_nets(nets, X, C)
    E = {}
    for k, (i, n, m) in enumerate(who):
        e = float(np.mean([top_error(outs[s][k], Y[i][0], Y[i][1]) for s in range(len(nets))]))
        E.setdefault((n, m), {}).setdefault(i, []).append(e)
    per = {key: {i: float(np.mean(v)) for i, v in d.items()} for key, d in E.items()}
    band = {r["i"]: r["band"] for r in rows}
    rep = {"post_hoc": True, "examples": len(rows),
           "E": {f"{n} {m}": t_interval([(band[i], str(i), v) for i, v in per[(n, m)].items()])["mean"] for n, m in per},
           "mix0_minus_mix": {n: t_interval([(band[i], str(i), per[(n, "mix0")][i] - per[(n, "mix")][i]) for i in band])
                              for n in ("(i)", "(ii)", "(iii)", "(iv)")},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(OUT / "audit-mix.json", rep)
    print("E", {k: round(v, 4) for k, v in rep["E"].items()})
    for n, st in rep["mix0_minus_mix"].items():
        print(f"  mix zeroed - mix, stem {n:6s} {fmt(st)}")


# =====================================================================================================
# Step 1c, the pilot build and the pilot (plan step 2, as amendment 1 has it)
# =====================================================================================================

ROOT = HOME / "learn/direct-stems"
SEPCHECK_REPRO_SEED = 20261081        # 1c: the fast stems re-separated on MPS (set here; the plan gave none)
SEPCHECK_REPRO_N = 5
SEPCHECK_REPRO_DB = 60.0              # the plan's MPS-against-CPU check read 81 dB
PILOT_SEED = 20261073                 # the pilot's 5k, stratified by band and amp
AUG_SEED = 20261074                   # SeedSequence([AUG_SEED, i, epoch])
MASTER_SEED = 20261076                # mastering, p 0.5, seeded by index
MASTER_P = 0.5
TRAIN_SEEDS = (20261042, 20261043)
N_PILOT_TRAIN = 5_000
MAX_EPOCHS = 40
MATCH_SHARE = 0.99                    # a re-render: within one 0.5-dB step of the stored mels on 99% of cells
POOL_EXPECT = {"examples": 21_311, "train": 20_311, "early_stop": 1_000, "sections": 277, "bands": 9}
VSEP_EXPECT = {"examples": 1_720, "bands": 5}
KNOWN_ANSWER_BANDS = frozenset({"Chris Coltraine", "Rebecca Haviland", "The Apprehended"})   # clean_di.KNOWN_ANSWER
MUSDB_TRAIN = frozenset({"It Was My Fault For Waiting", "Femme", "Bannockburn"})          # locator_truth
MUSDB_TEST = frozenset({"Signs", "Ill Fate"})
MUSDB_ARTIST = frozenset({"The Long Wait"})
DISK_GUARD_GB = 31.0
DISK_GUARD_PILOT_GB = 26.0
DISK_OVERRIDE_NOTE = "user, 2026-10-20: pilot build only, stop below 26 GB"
FULL_BUILD_START_GB = 34.0
MEM_FREE_MIN_GB = 4.0
SWAP_GROWTH_MB = 256.0
EXIT_DISK, EXIT_MEMORY = 4, 5
QUEUE = 2                             # the stem stage's bounded render -> separation queue
RENDER_CAP = 3
ARMS = ("D0", "Dmix", "Dstem", "Dstem-noaug")
STEM_ARMS = ("Dstem", "Dstem-noaug")
# the augmentations (plan, "Augmentations"; amendment 1's order: failure, merge, drop-outs, darkening)
P_FAIL, P_MERGE, P_DROP, P_DARK = 0.05, 0.2, 0.3, 0.3
FAIL_DB = (-6.0, 0.0)
MERGE_DB = (-12.0, 0.0)
DROP_N = (1, 3)
DROP_S = (0.2, 1.0)
DROP_DB = (10.0, 40.0)
DARK_HZ = (3000.0, 8000.0)
DARK_DB = (0.0, 15.0)
FRAMES_PER_S = 100                    # song_aug: 48 kHz, hop 480
Q_FLOOR_DB = -112.0                   # pretrain_set.Q_LO_DB: the stored grid's floor


# --- pure: the pool, exclusions, tags -----------------------------------------------------------------

def musdb_tag(song, band):
    """'musdb_train' / 'musdb_test' / 'musdb_artist' or None: material a separator may have trained on."""
    if song in MUSDB_TRAIN:
        return "musdb_train"
    if song in MUSDB_TEST:
        return "musdb_test"
    if band in MUSDB_ARTIST:
        return "musdb_artist"
    return None


def check_example(r, sec, split, f_bands, ka_bands, refuse, held_bands=frozenset()):
    """Assert every exclusion on one example and its section (SystemExit naming what failed);
    `refuse(sec)` raises on held-out material (clean_di.refuse_held_out)."""
    why = []
    if r["band"] in f_bands:
        why.append("a stage F band")
    if r["band"] in ka_bands:
        why.append("a known-answer band")
    if r["band"] in held_bands:
        why.append("a held-out band")
    if sec is None:
        why.append("its section is not in part C's pool")
    else:
        path = str(sec.get("path", ""))
        if sec["split"] != split:
            why.append(f"section split {sec['split']!r}, not {split!r}")
        if sec["band"] != r["band"]:
            why.append("band differs from its section's")
        if sec.get("source") == "guitar-techs" or "guitar-techs" in path.lower():
            why.append("Guitar-TECHS")
        if "P3" in path:
            why.append("Guitar-TECHS P3")
        if sec.get("stage_f_session"):
            why.append("a stage F session")
        if split == "train" and bool(sec.get("early_stop")) != bool(r.get("early_stop")):
            why.append("early-stopping flag differs from its section's")
    if why:
        raise SystemExit(f"example {r['i']}: refused ({'; '.join(why)})")
    refuse(sec)


def pool_examples(rows, sections, f_bands, ka_bands=KNOWN_ANSWER_BANDS, refuse=lambda s: None,
                  held_bands=frozenset()):
    """The band-clean pool: part C's train and early-stopping examples outside stage F's and the
    known-answer bands, every other exclusion asserted. -> rows sorted by index."""
    out = []
    for r in rows:
        if r["split"] != "train" or r["band"] in f_bands or r["band"] in ka_bands:
            continue
        check_example(r, sections.get(r["section"]), "train", f_bands, ka_bands, refuse, held_bands)
        out.append(r)
    return sorted(out, key=lambda r: r["i"])


def vsep_examples(rows, sections, f_bands, ka_bands=KNOWN_ANSWER_BANDS, refuse=lambda s: None,
                  held_bands=frozenset()):
    """V_sep: part C's val examples outside stage F's bands (V_dev), exclusions asserted."""
    out = []
    for r in rows:
        if r["split"] != "val" or r["band"] in f_bands:
            continue
        check_example(r, sections.get(r["section"]), "val", f_bands, ka_bands, refuse, held_bands)
        out.append(r)
    return sorted(out, key=lambda r: r["i"])


def counts(rows):
    bands = {}
    for r in rows:
        bands[r["band"]] = bands.get(r["band"], 0) + 1
    return {"examples": len(rows), "train": sum(not r.get("early_stop") for r in rows),
            "early_stop": sum(bool(r.get("early_stop")) for r in rows),
            "sections": len({r["section"] for r in rows}), "bands": len(bands), "per_band": dict(sorted(bands.items()))}


def check_counts(c, expect, what):
    bad = {k: (c[k], v) for k, v in expect.items() if c[k] != v}
    if bad:
        raise SystemExit(f"{what}: recount differs from the plan's: {bad}")


def stratified_pick(rows, n, seed=PILOT_SEED):
    """n rows, stratified by (band, amp): proportional quotas by largest remainder, then a seeded
    sample within each stratum (strata in sorted order). -> rows sorted by index."""
    strata = {}
    for r in sorted(rows, key=lambda r: r["i"]):
        strata.setdefault((r["band"], r["amp"]), []).append(r)
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


def split_parts(pool, vsep, n_pilot=N_PILOT_TRAIN, seed=PILOT_SEED):
    """{pilot: 5k stratified train + every early-stopping example, rest: the other train examples,
    vsep: V_sep}."""
    train = [r for r in pool if not r.get("early_stop")]
    pick = stratified_pick(train, n_pilot, seed)
    ids = {r["i"] for r in pick}
    pilot = sorted(pick + [r for r in pool if r.get("early_stop")], key=lambda r: r["i"])
    return {"pilot": pilot, "rest": [r for r in train if r["i"] not in ids], "vsep": list(vsep)}


# --- pure: features, guards ---------------------------------------------------------------------------

def match_share(a, b):
    """Share of uint8 mel cells within one 0.5-dB step."""
    import numpy as np

    return float(np.mean(np.abs(np.asarray(a, np.int16) - np.asarray(b, np.int16)) <= 1))


def half_features(y, logmel=None, lufs=None):
    """({half: uint8 mel}, {half: LUFS}, floor share) of a 10-s signal. A silent stem (a separator
    that hears no guitar) reads -70 LUFS (`song_aug.lufs`) and sits at the grid's floor."""
    import numpy as np

    from learn import pretrain_set as PS
    from learn import song_aug as SA

    logmel = logmel or SA.logmel
    lufs = lufs or SA.lufs
    mels, lu = {}, {}
    for h, sl in PS.half_slices().items():
        mels[h] = PS.quant(logmel(np.asarray(y, np.float64)[sl]))
        lu[h] = float(lufs(np.asarray(y, np.float64)[sl]))
    floor = float(np.mean(np.concatenate([(m == 0).ravel() for m in mels.values()])))
    return mels, lu, floor


def master_draw(i):
    """(mastered, rng): the mastering draw of example i (seed 20261076, p 0.5); the rng goes on to
    `song_aug.compress`."""
    from learn import pretrain_set as PS

    rng = random.Random(PS.seed_int(MASTER_SEED, int(i)))
    return rng.random() < MASTER_P, rng


def snr_db(est, ref):
    import numpy as np

    est, ref = np.asarray(est, np.float64), np.asarray(ref, np.float64)
    return 10 * math.log10(float(np.sum(ref ** 2)) / max(float(np.sum((est - ref) ** 2)), 1e-30))


def sepcheck_rule(iv):
    """1c's declared rule on the paired SNR difference (fast - stored), iv = (mean, lo, hi, bands):
    fast if the interval reaches 0 or lies above it, else stored."""
    return "fast" if iv[2] >= 0 else "stored"


def disk_guard(part, guard_gb=None):
    """-> (guard GB, note). The 31 GB guard by default; the pilot build only (pilot, vsep) may
    run to 26 GB, and the override is logged with the user's note."""
    g = DISK_GUARD_GB if guard_gb is None else float(guard_gb)
    if g >= DISK_GUARD_GB:
        return g, None
    if part not in ("pilot", "vsep"):
        raise SystemExit(f"the {DISK_GUARD_GB:.0f} GB guard holds for --part {part} (amendment 1)")
    if g < DISK_GUARD_PILOT_GB:
        raise SystemExit(f"--disk-guard-gb {g} is below the user's {DISK_GUARD_PILOT_GB:.0f} GB")
    return g, DISK_OVERRIDE_NOTE


def rest_allowed(report, stage):
    """The rest of the build follows the pilot's rule only: PILOT STEM (both stages) or PILOT MIX (the
    mix stage only), from a real (not smoke) pilot-report. SystemExit otherwise."""
    if not report or report.get("smoke"):
        raise SystemExit("--part rest needs a real pilot-report (PILOT STEM, or PILOT MIX for the mix stage)")
    dec = report.get("decision")
    if dec == "STEM" or (dec == "MIX" and stage == "mix"):
        return dec
    raise SystemExit(f"the pilot read PILOT {dec}: --part rest --stage {stage} is not built")


def disk_start_ok(part, free_gb, guard):
    """A build may start: free disk at or above its guard, and the rest at 34 GB or more."""
    return free_gb >= guard and (part != "rest" or free_gb >= FULL_BUILD_START_GB)


def disk_stop(free_gb, guard):
    return free_gb < guard


def mem_stop(avail_gb, swap_growth_mb, min_free=MEM_FREE_MIN_GB, max_growth=SWAP_GROWTH_MB):
    """The memory guard: a reason to stop, or None."""
    if avail_gb is not None and avail_gb < min_free:
        return f"free memory {avail_gb:.1f} GB below {min_free:.0f} GB"
    if swap_growth_mb is not None and swap_growth_mb > max_growth:
        return f"swap grew by {swap_growth_mb:.0f} MB"
    return None


def avail_gb():
    """Free + inactive + speculative memory (vm_stat), GB; None if unreadable."""
    import subprocess

    try:
        s = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
        page = int(re.search(r"page size of (\d+)", s).group(1))
        n = sum(int(re.search(rf"Pages {k}:\s+(\d+)", s).group(1)) for k in ("free", "inactive", "speculative"))
        return n * page / 1e9
    except Exception:
        return None


def swap_mb():
    from learn import separator_screen as SCR

    return SCR.swap_used_mb()


def render_slot_free(python_renders, servers, cap=RENDER_CAP):
    """Another render process may start: fewer than `cap` render processes machine-wide, counted
    both as python render jobs and as running render servers."""
    return python_renders < cap and servers < cap


def wait_render_slot():
    from learn import ks_extend as X
    from learn import local_objective as LO

    own = {os.getpid(), os.getppid()}
    while True:
        ps = X._ps()
        servers = sum("au_render_server" in c for _, c in ps)
        if render_slot_free(len(LO.others_rendering(ps, own)), servers):
            return
        print("waiting for a render slot", flush=True)
        time.sleep(60)


def needs_priming(last, key):
    """A discarded priming render is due when the (DI section, amp) changes, and at process start
    (last is None)."""
    return last is None or last != key


def render_order(rows, reverse=False):
    """Rows grouped by (section, amp), then index: the order that primes once per group."""
    return sorted(rows, key=lambda r: (r["section"], r["amp"], r["i"]), reverse=reverse)


def shard_sections(rows, n):
    """{section: shard}: whole sections to shards, largest first to the least-loaded shard
    (deterministic), so a shard's (section, amp) groups stay whole."""
    size = {}
    for r in rows:
        size[r["section"]] = size.get(r["section"], 0) + 1
    load, out = [0] * n, {}
    for sec in sorted(size, key=lambda s: (-size[s], s)):
        k = min(range(n), key=lambda j: (load[j], j))
        out[sec] = k
        load[k] += size[sec]
    return out


def render_count(rows):
    """Renders for one pass over `rows` in render order (one shard or worker): examples + groups."""
    return len(rows) + len({(r["section"], r["amp"]) for r in rows})


# --- pure: the arms' inputs and the augmentations -----------------------------------------------------

def half_of(i, epoch):
    """The half example i shows at an epoch (part C's draw, `CurveData.params`; epoch -1 is the
    fixed early-stopping draw). 0 = A, 1 = B."""
    from learn import pretrain_set as PS

    return int(random.Random(PS.seed_int(PS.SEED, "half", int(i), int(epoch))).random() < 0.5)


def zero_inputs(x, c, arm):
    """Amendment 1's exact zeroing, on normalised inputs [N, 2, mels, frames] (after the half-A
    mask) and conditioning [N, ...] (`cond_vec`; the last two slots are stem and mix LUFS):
    D_mix's stem and D_stem's mix are 0 (-60 dB), and their LUFS slot 0. In place; returned."""
    if arm == "Dmix":
        x[:, 0] = 0
        c[:, -2] = 0
    elif arm in STEM_ARMS:
        x[:, 1] = 0
        c[:, -1] = 0
    elif arm != "D0":
        raise ValueError(f"unknown arm {arm!r}")
    return x, c


def mel_centres_hz():
    import numpy as np

    from learn import song_aug as SA

    def hz_to_mel(f):
        return 2595 * np.log10(1 + f / 700)

    def mel_to_hz(m):
        return 700 * (10 ** (m / 2595) - 1)

    edges = mel_to_hz(np.linspace(hz_to_mel(SA.FMIN), hz_to_mel(SA.FMAX), SA.MELS + 2))
    return edges[1:-1]


def aug_rng(i, epoch):
    import numpy as np

    return np.random.default_rng(np.random.SeedSequence([AUG_SEED, int(i), int(epoch)]))


def sep_failure(mix_db, lufs_mix, rng):
    """stem := the true-mix mel + U(-6, 0) dB; its LUFS := the mix LUFS + the same offset."""
    import numpy as np

    off = float(rng.uniform(*FAIL_DB))
    return np.maximum(np.asarray(mix_db, np.float32) + off, Q_FLOOR_DB), lufs_mix + off


def merge_guitar(stem_db, other_db, gain_db):
    """Another guitar's mel added in the power domain at `gain_db`."""
    import numpy as np

    s, o = np.asarray(stem_db, np.float64), np.asarray(other_db, np.float64) + gain_db
    return (10 * np.log10(10 ** (s / 10) + 10 ** (o / 10))).astype(np.float32)


def merge_gain_db(lufs_target_half, mix_gain_db, lufs_other_half, u_db):
    """The merged guitar's gain: it sits u_db (U(-12, 0)) relative to the target guitar at its level
    in the mix (render LUFS + the mix's overall gain)."""
    return lufs_target_half + mix_gain_db - lufs_other_half + u_db


def dropouts(stem_db, rng, fps=FRAMES_PER_S):
    """1-3 segments of 0.2-1.0 s, each attenuated by U(10, 40) dB (floored at the grid's floor)."""
    import numpy as np

    x = np.array(stem_db, np.float32)
    n_fr = x.shape[-1]
    for _ in range(int(rng.integers(DROP_N[0], DROP_N[1] + 1))):
        L = max(1, min(n_fr, int(round(float(rng.uniform(*DROP_S)) * fps))))
        a = int(rng.integers(0, n_fr - L + 1))
        x[..., a:a + L] -= float(rng.uniform(*DROP_DB))
    return np.maximum(x, Q_FLOOR_DB)


def darken(stem_db, rng, centres_hz):
    """Mel bands centred above a corner at U(3, 8) kHz attenuated by U(0, 15) dB."""
    import numpy as np

    corner, att = float(rng.uniform(*DARK_HZ)), float(rng.uniform(*DARK_DB))
    x = np.array(stem_db, np.float32)
    x[np.asarray(centres_hz) > corner] -= att
    return np.maximum(x, Q_FLOOR_DB)


def augment(i, epoch, stem_db, lufs_stem, mix_db, lufs_mix, merge_draw, centres_hz):
    """D_stem's augmentations on one stem half, in amendment 1's order: separator failure (p 0.05),
    the merged guitar (p 0.2; `merge_draw(rng)` -> (other guitar dB mel, gain dB)), drop-outs
    (p 0.3), darkening (p 0.3). The four gates are drawn first, then each applied step's values.
    Only the failure step changes the LUFS. -> (stem dB, stem LUFS, [applied])."""
    rng = aug_rng(i, epoch)
    u = rng.random(4)
    applied = []
    stem = stem_db
    if u[0] < P_FAIL:
        stem, lufs_stem = sep_failure(mix_db, lufs_mix, rng)
        applied.append("fail")
    if u[1] < P_MERGE:
        other, gain = merge_draw(rng)
        stem = merge_guitar(stem, other, gain)
        applied.append("merge")
    if u[2] < P_DROP:
        stem = dropouts(stem, rng)
        applied.append("drop")
    if u[3] < P_DARK:
        stem = darken(stem, rng, centres_hz)
        applied.append("dark")
    return stem, lufs_stem, applied


def merge_candidates(rows):
    """{base class: [(position, section)]} over training rows only (never early stopping or V_sep;
    asserted)."""
    out = {}
    for pos, r in enumerate(rows):
        if r.get("split") != "train" or r.get("early_stop"):
            continue
        out.setdefault(r["base"], []).append((pos, r["section"]))
    for v in out.values():
        for pos, _ in v:
            assert rows[pos]["split"] == "train" and not rows[pos].get("early_stop") and rows[pos]["i"] < VAL_BASE_ID
    return out


VAL_BASE_ID = 1_000_000                # pretrain_set.VAL_BASE


def merge_partner(rng, cands, section, tries=1000):
    """A partner position from `cands` ([(position, section)]) in another section."""
    for _ in range(tries):
        pos, sec = cands[int(rng.integers(len(cands)))]
        if sec != section:
            return pos
    raise SystemExit("no merge partner in another section")


# --- pure: the pilot readout --------------------------------------------------------------------------

def paired(per_a, per_b, band_of, keep):
    """Paired difference a - b per example on `keep`, band-clustered t: (mean, lo, hi, bands)."""
    from learn import pretrain_set as PS

    by = {}
    for i in sorted(set(per_a) & set(per_b) & set(keep)):
        by.setdefault(band_of[i], []).append(per_a[i] - per_b[i])
    return PS.band_t_interval(by) if by else None


def pilot_rules(c):
    """Amendment 1's rules, in order. c: {'Dstem-D0|R_out', 'Dmix-D0|R_out', 'Dmix-Dstem|R_in',
    'Dstem-Dstem-noaug|R_in'}: (mean, lo, hi, bands) or None.
    -> (decision STOP / MIX / STEM, augmentation kept, [reasons])."""
    def below(k):
        return c.get(k) is not None and c[k][2] is not None and c[k][2] < 0

    def above(k):
        return c.get(k) is not None and c[k][1] is not None and c[k][1] > 0

    why = []
    stem_beats, mix_beats = below("Dstem-D0|R_out"), below("Dmix-D0|R_out")
    if stem_beats:
        why.append("D_stem beat D0 on R_out")
    if mix_beats:
        why.append("D_mix beat D0 on R_out")
    if not (stem_beats or mix_beats):
        dec = "STOP"
        why.append("neither D_stem nor D_mix beat D0 on R_out (rule 1)")
    elif mix_beats and below("Dmix-Dstem|R_in"):
        dec = "MIX"
        why.append("D_mix clearly better than D_stem on R_in and beat D0 (rule 2)")
    else:
        dec = "STEM"
        why.append("rule 3: build the rest, train D_stem")
    aug = not above("Dstem-Dstem-noaug|R_in")
    why.append("augmentation kept (rule 4)" if aug else "augmentation dropped: D_stem worse than noaug on R_in (rule 4)")
    return dec, aug, why


# --- the build: paths, context ------------------------------------------------------------------------

def out_root(args):
    return pathlib.Path(args.out).expanduser() if getattr(args, "out", None) else ROOT


def ex_path(root, i, kind):
    return root / "build" / "ex" / f"{int(i) // 1000:04d}" / f"{int(i):07d}-{kind}.npz"


def rows_dir(root):
    return root / "build" / "rows"


def read_jsonl(path):
    from learn import pretrain_set as PS

    return PS.read_rows(path) if pathlib.Path(path).exists() else []


def build_rows(root, part, stage):
    """{i: last row} over every worker's JSONL of a part and stage ('mix', 'mega53', 'htdemucs')."""
    out = {}
    for f in sorted(rows_dir(root).glob(f"{part}-{stage}-*.jsonl")):
        for r in read_jsonl(f):
            out[r["i"]] = r
    return out


def _save_npz(path, **arrays):
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + f".{os.getpid()}.tmp.npz")
    np.savez_compressed(tmp, **arrays)
    tmp.replace(path)


class Ctx:
    """Part C's rows and pool, the exclusions asserted, the parts, the tags, and the backings."""

    def __init__(self, quiet=False):
        from learn import arm_a_mega53 as A
        from learn import clean_di as CD
        from learn import pretrain_set as PS
        from learn import song_bank as B

        if set(CD.KNOWN_ANSWER) != KNOWN_ANSWER_BANDS:
            raise SystemExit("clean_di.KNOWN_ANSWER changed")
        from learn import locator_truth as LT

        if (set(LT.MUSDB_TRAIN), set(LT.MUSDB_TEST), set(LT.MUSDB_ARTIST)) != (MUSDB_TRAIN, MUSDB_TEST, MUSDB_ARTIST):
            raise SystemExit("locator_truth's MUSDB18 lists changed")
        self.p = PS.pool()
        if not PS.manifest_ok(self.p["manifest_sha256"]):
            raise SystemExit("part C's pool was built from the pre-amendment manifest")
        self.sections = {s["id"]: s for s in self.p["sections"]}
        self.inv = {r["id"]: r for r in json.loads(PS.INVENTORY.read_text())["dis"]}
        self.rows = PS.all_rows()
        self.f_bands = set(A.F_POOL)
        held = CD._held_out_names()
        refused = {}

        def refuse(sec):
            if sec["id"] not in refused:
                CD.refuse_held_out(self.inv[sec["di"]])
                refused[sec["id"]] = True

        ordered = [self.rows[i] for i in sorted(self.rows)]
        self.pool = pool_examples(ordered, self.sections, self.f_bands, KNOWN_ANSWER_BANDS, refuse, held)
        self.vsep = vsep_examples(ordered, self.sections, self.f_bands, KNOWN_ANSWER_BANDS, refuse, held)
        self.pool_counts, self.vsep_counts = counts(self.pool), counts(self.vsep)
        check_counts(self.pool_counts, POOL_EXPECT, "the pool")
        check_counts(self.vsep_counts, VSEP_EXPECT, "V_sep")
        if set(self.pool_counts["per_band"]) & (set(self.vsep_counts["per_band"]) | self.f_bands | KNOWN_ANSWER_BANDS):
            raise SystemExit("training bands overlap V_sep, stage F or the known-answer bands")
        self.parts = split_parts(self.pool, self.vsep)
        self.tag = {}
        for r in self.pool + self.vsep:
            sec = self.sections[r["section"]]
            self.tag[r["i"]] = musdb_tag(self.inv[sec["di"]].get("song"), r["band"])
        self.leak = PS._load(PS.OUT / "leakage.json")
        self.ratios = PS.ratio_values()
        self.eval_mix = json.loads((B.OUT / "levels.json").read_text())["summary"]["eval_mix_lufs_median"]
        self._back = {}
        if not quiet:
            self.print_counts()

    def print_counts(self):
        c, v = self.pool_counts, self.vsep_counts
        print(f"pool: {c['examples']:,} examples ({c['train']:,} train, {c['early_stop']:,} early stopping) from "
              f"{c['sections']} sections in {c['bands']} bands: {c['per_band']}", flush=True)
        tags = {}
        for i, t in self.tag.items():
            if t:
                tags.setdefault(t, set()).add(self.rows[i]["section"])
        print("MUSDB18-tagged sections:", {k: len(s) for k, s in sorted(tags.items())}, flush=True)
        print(f"V_sep: {v['examples']:,} examples in {v['bands']} bands {v['per_band']}; "
              f"Bannockburn (MUSDB18 train) left out of readouts: "
              f"{sum(1 for r in self.vsep if self.tag[r['i']])} examples", flush=True)
        print("parts:", {k: len(v) for k, v in self.parts.items()}, flush=True)

    def backing(self, sid, kind):
        """The section's backing rebuilt from the session's tracks by part C's rule, checked
        against part C's stored backing mels and LUFS. -> (audio, stored meta)."""
        import numpy as np

        from learn import pretrain_set as PS
        from learn import song_aug as SA

        key = (sid, kind)
        if key not in self._back:
            sec = self.sections[sid]
            rec = self.inv[sec["di"]]
            sess = pathlib.Path(rec["session_dir"])
            files = sorted(f.name for f in sess.glob("*.wav"))
            withv, nov = PS.backing_tracks(rec, files, self.leak[sec["di"]]["dropped"])
            b = np.zeros(int(round((PS.SEC_S + PS.TRIM_S) * PS.SR)), np.float64)
            for t in (withv if kind == "v" else nov):
                b += PS.section_audio(sess / t, sec["start_s"])
            b = b[int(PS.TRIM_S * PS.SR):]
            meta = json.loads(PS.backing_path(sid).with_suffix(".json").read_text())
            stored = np.load(PS.backing_path(sid))
            share = min(match_share(m, stored[f"{kind}{h}"]) for h, m in PS.halves_mel(b).items())
            dl = abs(SA.lufs(b) - meta[f"lufs_{kind}"])
            if share < MATCH_SHARE or dl > 0.01:
                raise SystemExit(f"{sid}/{kind}: rebuilt backing differs from part C's (cells {share:.4f}, LUFS {dl:.3f})")
            if len(self._back) >= 4:
                self._back.pop(next(iter(self._back)))
            self._back[key] = (b, meta)
        return self._back[key]


class Primer:
    """The renderer with the priming rule: one discarded render after any process start, amp change
    or DI change. Examples run in (section, amp) order, so a group sharing a DI section and amp is
    primed once; every render is counted."""

    def __init__(self, rr):
        self.rr, self.last, self.renders, self.primes = rr, None, 0, 0

    def render(self, key, di, sel, x):
        import numpy as np

        if needs_priming(self.last, key):
            self.rr.render(di, sel, x)
            self.renders += 1
            self.primes += 1
        self.last = key
        self.renders += 1
        return np.asarray(self.rr.render(di, sel, x), np.float64)


def example_audio(ctx, primer, menu, r):
    """Example r re-rendered (primed on a DI or amp change) and mixed. -> dict with 'refused' (a reason) or the render y,
    the mastered true mix, the mix draw and the render's match share."""
    import numpy as np

    from learn import knob_ceiling as K
    from learn import pretrain_set as PS
    from learn import song_bank as B

    i = r["i"]
    sec = ctx.sections[r["section"]]
    check_example(r, sec, "val" if i >= VAL_BASE_ID else "train", ctx.f_bands, KNOWN_ANSWER_BANDS, lambda s: None)
    rng, amp, mode, base = PS.plan_example(i)
    if (amp, base) != (r["amp"], r["base"]):
        raise SystemExit(f"{i}: the plan's draw differs from part C's row")
    sel, x, label, _ = PS.settings_for(rng, amp, mode, base, menu, K.START, K.space, K.fmt)
    if {f"{m}/{k}": v for (m, k), v in x.items()} != r["settings"]:
        raise SystemExit(f"{i}: settings differ from part C's row")
    di = B.measure(PS.section_audio(sec["path"], sec["start_s"])).astype(np.float32)
    y = primer.render((r["section"], amp), di, sel, x)
    y = (y.mean(axis=1) if y.ndim == 2 else y)[int(PS.TRIM_S * PS.SR):int((PS.TRIM_S + PS.SEC_S) * PS.SR)]
    stored = np.load(PS.example_path(i))
    share = min(match_share(m, stored[f"g{h}"]) for h, m in PS.halves_mel(y).items())
    if share < MATCH_SHARE:
        return {"refused": "re-render differs from part C's stored mels", "g_share": share}
    meta = json.loads(PS.backing_path(r["section"]).with_suffix(".json").read_text())
    ratio, v, leak, target = PS.mix_params(i, ctx.ratios, meta["has_vocals"], ctx.eval_mix, 0)
    kind = "v" if v else "n"
    b, meta = ctx.backing(r["section"], kind)
    gb, gl, ga = PS.mix_gains_db(r["lufs"], meta[f"lufs_{kind}"], ratio, leak, target)
    if i >= VAL_BASE_ID and max(abs(p - q) for p, q in zip((gb, gl, ga), r["mix"]["gains_db"])) > 1e-6:
        raise SystemExit(f"{i}: the V_sep mix draw differs from part C's val mix")
    mix = (y + b * 10 ** (gb / 20)) * 10 ** (ga / 20)
    mastered, mrng = master_draw(i)
    if mastered:
        from learn import song_aug as SA

        mix = SA.compress(mix, mrng)
    return {"y": y, "mix": mix, "g_share": share, "mastered": mastered,
            "draw": {"ratio_db": ratio, "vocals": v, "target_lufs": target, "gains_db": [gb, ga]}}


def check_recipe(rr):
    from learn import confirm_run as CR
    from learn import pretrain_set as PS

    old = PS._load(PS.OUT / "recipe.json")
    pv = rr.r.metadata().plugin_version
    if rr.r.isolate is not True:
        raise SystemExit("the renderer is not isolating renders")
    if pv != old["plugin_version"] or PS.file_sha256(CR.AVERAGE) != old["average_sha256"]:
        raise SystemExit(f"part C's recipe changed: plugin {pv} vs {old['plugin_version']}, or the average DI")


def _guards(part, guard, swap0):
    """None, or (exit code, reason): disk, then memory and swap."""
    from learn import pretrain_set as PS

    free = PS.free_gb()
    if disk_stop(free, guard):
        return EXIT_DISK, f"DISK GUARD: {free:.1f} GB free, below {guard:.0f} GB"
    s = swap_mb()
    why = mem_stop(avail_gb(), None if swap0 is None or s is None else s - swap0)
    return (EXIT_MEMORY, f"MEMORY GUARD: {why}") if why else None


def _log_build(root, rec):
    rows_dir(root).mkdir(parents=True, exist_ok=True)
    with open(rows_dir(root) / "build-log.jsonl", "a") as fh:
        fh.write(json.dumps(rec) + "\n")


def parse_shard(s):
    k, n = (int(x) for x in s.split("/"))
    if not 0 <= k < n:
        raise argparse.ArgumentTypeError(f"bad shard {s}")
    return k, n


def cmd_build(args):
    from learn import pretrain_set as PS

    root = out_root(args)
    if args.limit and not args.out:
        raise SystemExit("--limit is for smoke tests into a scratch --out only")
    guard, note = disk_guard(args.part, args.disk_guard_gb)
    free = PS.free_gb()
    if not disk_start_ok(args.part, free, guard):
        raise SystemExit(f"free disk {free:.1f} GB: the {args.part} build needs {guard:.0f} GB"
                         + (f" (and {FULL_BUILD_START_GB:.0f} GB to start)" if args.part == "rest" else ""))
    if args.part == "rest":
        rest_allowed(_load(root / "pilot" / "pilot-report.json"), args.stage)
    ctx = Ctx()
    items = ctx.parts[args.part]
    if args.limit:
        items = items[:args.limit] if args.part != "pilot" else (
            [r for r in items if not r["early_stop"]][:args.limit - args.limit // 4]
            + [r for r in items if r["early_stop"]][:args.limit // 4])
    log = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "pid": os.getpid(), "part": args.part, "stage": args.stage,
           "sep": args.sep, "device": args.device, "shard": args.shard, "items": len(items), "disk_guard_gb": guard,
           "disk_override_note": note, "free_gb": round(free, 1), "limit": args.limit}
    if note:
        print(f"disk guard {guard:.0f} GB ({note})", flush=True)
    _log_build(root, log)
    if args.stage == "mix":
        stage_mix(args, ctx, items, root, guard)
    else:
        stage_stem(args, ctx, items, root, guard)


def stage_mix(args, ctx, items, root, guard):
    """Renders (primed), true mixes and mastering; the mix mels and exact half LUFS stored. No
    separation."""
    from learn import knob_ceiling as K
    from learn import pretrain_set as PS

    k, n = args.shard
    done = set(build_rows(root, args.part, "mix"))
    shard = shard_sections(items, n)
    todo = render_order(r for r in items if shard[r["section"]] == k and r["i"] not in done)
    print(f"mix stage {args.part} shard {k}/{n}: {len(todo)} to do", flush=True)
    if not todo:
        print(f"BUILD DONE {args.part} mix {k}/{n}", flush=True)
        return
    wait_render_slot()
    rr = K.Renderer()
    primer = Primer(rr)
    refused = 0
    try:
        menu = rr.menu()
        check_recipe(rr)
        rp = rows_dir(root) / f"{args.part}-mix-{k}of{n}.jsonl"
        PS.read_rows(rp, repair=True) if rp.exists() else None
        with open(rp, "a") as fh:
            for m, r in enumerate(todo):
                g = _guards(args.part, guard, None)
                if g:
                    print(g[1], flush=True)
                    raise SystemExit(g[0])
                t0 = time.time()
                ex = example_audio(ctx, primer, menu, r)
                row = {"i": r["i"], "section": r["section"], "band": r["band"], "early_stop": bool(r.get("early_stop")),
                       "split": r["split"], "amp": r["amp"], "base": r["base"], "tag": ctx.tag[r["i"]]}
                if "refused" in ex:
                    refused += 1
                    row.update(refused=ex["refused"], g_share=ex["g_share"])
                else:
                    mels, lu, _ = half_features(ex["mix"])
                    _save_npz(ex_path(root, r["i"], "mix"), mA=mels["A"], mB=mels["B"],
                              lufs=[lu["A"], lu["B"]], gain_db=ex["draw"]["gains_db"][1], mastered=ex["mastered"])
                    row.update(g_share=ex["g_share"], mastered=ex["mastered"], lufs_mA=lu["A"], lufs_mB=lu["B"],
                               **ex["draw"])
                row["seconds"] = round(time.time() - t0, 2)
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                if m % 50 == 0:
                    print(f"mix {m + 1}/{len(todo)} i={r['i']} {row['seconds']} s, refused so far {refused}", flush=True)
    finally:
        rr.close()
    print(f"BUILD DONE {args.part} mix {k}/{n} (refused {refused}; renders {primer.renders}, of them priming "
          f"{primer.primes})", flush=True)


def mega53_separator(setting, device):
    """Mega-53's pruned electric-guitar head in the 1c setting ('fast': one 10-s chunk, overlap 1;
    'stored': the yaml's 20-s chunks, overlap 2), on 'mps' or 'cpu' (4 threads)."""
    import torch

    from learn import separator_screen as SCR

    s = SCR.MsstSeparator(prune=True)
    if setting == "fast":
        s.config.inference.chunk_size = FAST_CHUNK
        s.config.inference.num_overlap = FAST_OVERLAP
    elif setting != "stored":
        raise SystemExit(f"unknown setting {setting!r}")
    if device == "mps":
        if not torch.backends.mps.is_available():
            raise SystemExit("MPS is not available")
        s.model = s.model.to("mps")
        s.device = torch.device("mps")
        torch.set_num_threads(2)
    s.setting, s.device_name = setting, device
    return s


def chosen_setting(root, override=None):
    sc = _load(root / "sepcheck" / "sepcheck.json") or _load(ROOT / "sepcheck" / "sepcheck.json")
    if override:
        if sc and sc["chosen"] != override:
            raise SystemExit(f"--setting {override} contradicts 1c's {sc['chosen']}")
        return override, sc is None
    if not sc:
        raise SystemExit("run `sepcheck` first (1c chooses the separator setting)")
    return sc["chosen"], False


def stage_stem(args, ctx, items, root, guard):
    """Separation of each example's true mix, fed by its own re-render through a bounded queue:
    the re-render and mix must reproduce the stored mix mels (99% of cells within one step)."""
    import queue
    import threading

    import numpy as np

    from learn import knob_ceiling as K
    from learn import pretrain_set as PS

    sep_name = args.sep or "mega53"
    if sep_name == "htdemucs" and args.part != "vsep":
        raise SystemExit("htdemucs stems are for V_sep only")
    setting, unchecked = chosen_setting(root, args.setting) if sep_name == "mega53" else (None, False)
    if unchecked and not args.out:
        raise SystemExit("--setting without a 1c result is for smoke tests into a scratch --out only")
    mixrows = build_rows(root, args.part, "mix")
    done = set(build_rows(root, args.part, sep_name))
    todo = render_order([r for r in items if r["i"] in mixrows and not mixrows[r["i"]].get("refused")
                         and r["i"] not in done], reverse=args.order == "desc")
    waiting = sum(1 for r in items if r["i"] not in mixrows)
    print(f"stem stage {args.part} {sep_name} ({setting or 'htdemucs'}, {args.device if sep_name == 'mega53' else 'cpu'}, "
          f"{args.order}): {len(todo)} to do; "
          f"{waiting} without a mix yet", flush=True)
    if not todo:
        print(f"BUILD DONE {args.part} {sep_name}", flush=True)
        return
    if sep_name == "mega53":
        sep = mega53_separator(setting, args.device)
    else:
        import torch

        from learn import separator_screen as SCR

        sep = SCR.htdemucs()
        torch.set_num_threads(2)
    swap0 = swap_mb()
    q, stop, err = queue.Queue(maxsize=QUEUE), threading.Event(), []
    device = args.device if sep_name == "mega53" else "cpu"          # htdemucs: CPU, as `separator_screen.htdemucs`
    worker = f"{device}-{args.order}-{os.getpid()}"

    def produce():
        rr = None
        try:
            wait_render_slot()
            rr = K.Renderer()
            primer = Primer(rr)
            menu = rr.menu()
            check_recipe(rr)
            for r in todo:
                if stop.is_set():
                    break
                if r["i"] in build_rows(root, args.part, sep_name):         # another worker's row: done
                    continue
                ex = example_audio(ctx, primer, menu, r)
                if "refused" not in ex:
                    st = np.load(ex_path(root, r["i"], "mix"))
                    mels, lu, _ = half_features(ex["mix"])
                    ms = min(match_share(mels[h], st[f"m{h}"]) for h in "AB")
                    if ms < MATCH_SHARE:
                        ex = {"refused": "the mix differs from the stored mix stage", "g_share": ex["g_share"], "m_share": ms}
                    else:
                        ex["m_share"] = ms
                while not stop.is_set():
                    try:
                        q.put((r, ex), timeout=1)
                        break
                    except queue.Full:
                        pass
        except BaseException as e:                     # noqa: BLE001 - handed to the main thread
            err.append(e)
        finally:
            if rr is not None:
                rr.close()
            while True:
                try:
                    q.put(None, timeout=1)
                    break
                except queue.Full:
                    if stop.is_set():
                        try:
                            q.get_nowait()
                        except queue.Empty:
                            pass

    th = threading.Thread(target=produce, daemon=True)
    th.start()
    rp = rows_dir(root) / f"{args.part}-{sep_name}-{worker}.jsonl"
    rp.parent.mkdir(parents=True, exist_ok=True)
    n_done, refused, exit_code = 0, 0, 0
    t_start = time.time()
    counter = {}
    try:
        _consume(q, stop, args, root, guard, swap0, sep, sep_name, setting, worker, ctx, rp, todo, t_start, counter)
    finally:
        stop.set()
        while th.is_alive():
            try:
                q.get(timeout=1)
            except queue.Empty:
                pass
        th.join()
    n_done, refused, exit_code = counter.get("done", 0), counter.get("refused", 0), counter.get("exit", 0)
    if err:
        raise err[0]
    if exit_code:
        raise SystemExit(exit_code)
    print(f"BUILD DONE {args.part} {sep_name} ({n_done} this run, refused {refused})", flush=True)


def _consume(q, stop, args, root, guard, swap0, sep, sep_name, setting, worker, ctx, rp, todo, t_start, counter):
    import numpy as np

    n_done, refused = 0, 0
    with open(rp, "a") as fh:
        while True:
            item = q.get()
            if item is None:
                break
            g = _guards(args.part, guard, swap0)
            if g:
                print(g[1], flush=True)
                counter["exit"] = g[0]
                stop.set()
                break
            r, ex = item
            out = ex_path(root, r["i"], sep_name)
            if r["i"] in build_rows(root, args.part, sep_name):              # rows decide "done", not files
                continue
            row = {"i": r["i"], "sep": sep_name, "setting": setting, "device": worker.split("-")[0], "worker": worker,
                   "tag": ctx.tag[r["i"]]}
            if "refused" in ex:
                refused += 1
                counter["refused"] = refused
                row.update(refused=ex["refused"], g_share=ex.get("g_share"), m_share=ex.get("m_share"))
            else:
                t0 = time.time()
                s = np.asarray(sep(ex["mix"]), np.float64)
                if len(s) != len(ex["mix"]) or not np.isfinite(s).all():
                    raise SystemExit(f"{r['i']}: bad stem")
                mels, lu, floor = half_features(s)
                _save_npz(out, sA=mels["A"], sB=mels["B"], lufs=[lu["A"], lu["B"]])
                row.update(lufs_sA=lu["A"], lufs_sB=lu["B"], floor_share=floor, g_share=ex["g_share"],
                           m_share=ex["m_share"], sep_seconds=round(time.time() - t0, 2))
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            n_done += 1
            counter.update(done=n_done, refused=refused)
            if n_done % 25 == 0:
                print(f"{sep_name} {n_done}/{len(todo)} i={r['i']} {(time.time() - t_start) / n_done:.1f} s each, "
                      f"refused {refused}", flush=True)


# --- 1c: the separator setting (msst-venv, MPS) -------------------------------------------------------

def cmd_sepcheck(args):
    """1c: Mega-53 fast (gate 1's stored audit stems, hash-checked, a sample reproduced on MPS)
    against the stored setting (separated here on MPS) on the 164 non-stage-F audit true mixes;
    SNR against the rendered guitar, paired, band-clustered; the declared rule picks the setting."""
    import gc
    import hashlib

    import numpy as np
    import torch

    from learn import pretrain_set as PS

    root = out_root(args)
    d = root / "sepcheck"
    guard, note = disk_guard("pilot", args.disk_guard_gb)              # 1c belongs to the pilot build
    if note:
        print(f"disk guard {guard:.0f} GB ({note})", flush=True)
        _log_build(root, {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "pid": os.getpid(), "cmd": "sepcheck",
                          "disk_guard_gb": guard, "disk_override_note": note})
    if disk_stop(PS.free_gb(), guard):
        raise SystemExit(f"free disk below {guard:.0f} GB")
    rows = audit_rows()
    run = _load(OUT / "stems" / "mega53" / "run.json")
    inf = run["info"]["inference"]
    if not (run["fast"] and inf["chunk_size"] == FAST_CHUNK and inf["num_overlap"] == FAST_OVERLAP):
        raise SystemExit("gate 1's Mega-53 stems are not the fast setting")
    hashes = {str(r["i"]): hashlib.sha256(stem_path("mega53", "audit", r["i"]).read_bytes()).hexdigest() for r in rows}
    old = _load(d / "fast-stem-hashes.json")
    if old is not None and old != hashes:
        raise SystemExit("gate 1's fast audit stems changed since their hashes were recorded")
    if old is None:
        _save(d / "fast-stem-hashes.json", hashes)
    log = {r["i"]: r for r in read_jsonl(d / "per-example.jsonl")}
    rep = _load(d / "repro.json")
    if rep is None:                                       # the stored fast stems, reproduced on MPS
        sep = mega53_separator("fast", "mps")
        pick = sorted(random.Random(SEPCHECK_REPRO_SEED).sample([r["i"] for r in rows], SEPCHECK_REPRO_N))
        by = {r["i"]: r for r in rows}
        rep = {"seed": SEPCHECK_REPRO_SEED, "min_db": SEPCHECK_REPRO_DB, "rows": {}}
        for i in pick:
            y, bm, _, _ = audit_audio(by[i])
            t0 = time.time()
            s = np.asarray(sep(y + bm), np.float64)
            rep["rows"][str(i)] = {"snr_vs_stored_cpu_db": snr_db(s, np.load(stem_path("mega53", "audit", i))),
                                   "seconds": round(time.time() - t0, 2)}
            print("repro", i, rep["rows"][str(i)], flush=True)
        rep["worst_db"] = min(v["snr_vs_stored_cpu_db"] for v in rep["rows"].values())
        if rep["worst_db"] < SEPCHECK_REPRO_DB:
            raise SystemExit(f"MPS fast does not reproduce gate 1's CPU stems: {rep['worst_db']:.1f} dB")
        _save(d / "repro.json", rep)
        del sep
        gc.collect()
        torch.mps.empty_cache()
    todo = [r for r in rows if r["i"] not in log]
    if todo:
        sep = mega53_separator("stored", "mps")
        inference = dict(sep.config.inference)
        swap0 = swap_mb()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "per-example.jsonl", "a") as fh:
            for n, r in enumerate(todo):
                s0 = swap_mb()
                why = mem_stop(avail_gb(), None if swap0 is None or s0 is None else s0 - swap0)
                if why:
                    print("MEMORY GUARD", why, flush=True)
                    raise SystemExit(EXIT_MEMORY)
                y, bm, _, _ = audit_audio(r)
                t0 = time.time()
                s = np.asarray(sep(y + bm), np.float64)
                dt = time.time() - t0
                fast = np.load(stem_path("mega53", "audit", r["i"])).astype(np.float64)
                rec = {"i": r["i"], "band": r["band"], "snr_stored_db": snr_db(s, y), "snr_fast_db": snr_db(fast, y),
                       "seconds": round(dt, 2), "stem_sha256": hashlib.sha256(s.astype(np.float32).tobytes()).hexdigest()}
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                log[r["i"]] = rec
                if n % 10 == 0:
                    print(f"stored {n + 1}/{len(todo)}", rec, flush=True)
    else:
        inference = None
    vals = [(v["band"], str(i), v["snr_fast_db"] - v["snr_stored_db"]) for i, v in sorted(log.items())]
    t = t_interval(vals)
    iv = (t["mean"], t["lo90"], t["hi90"], t["bands"])
    chosen = sepcheck_rule(iv)
    out = {"plan": "docs/direct-model-stems-plan.md 1c (amendment 1: first)", "examples": len(log),
           "bands": sorted({v["band"] for v in log.values()}),
           "snr_fast_minus_stored": t, "snr_fast_minus_stored_bootstrap": bootstrap(vals),
           "snr_fast_mean": t_interval([(v["band"], str(i), v["snr_fast_db"]) for i, v in log.items()])["mean"],
           "snr_stored_mean": t_interval([(v["band"], str(i), v["snr_stored_db"]) for i, v in log.items()])["mean"],
           "per_band": band_weighted(vals)[1], "seconds_stored_median": float(np.median([v["seconds"] for v in log.values()])),
           "rule": "fast if the paired interval (fast - stored) reaches 0 or lies above it, else stored",
           "chosen": chosen, "fast": {"chunk_size": FAST_CHUNK, "num_overlap": FAST_OVERLAP},
           "stored_inference": inference, "repro": rep, "fast_stem_hashes": "fast-stem-hashes.json",
           "device": "mps", "disk_guard_gb": guard, "disk_override_note": note,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(d / "sepcheck.json", out)
    print(f"SNR fast {out['snr_fast_mean']:.2f} dB, stored {out['snr_stored_mean']:.2f} dB; fast - stored {fmt(t)}")
    print(f"SEPCHECK {chosen.upper()}: Mega-53 {'fast (one 10-s chunk, overlap 1)' if chosen == 'fast' else 'stored (20-s chunks, overlap 2) on exact 10-s clips'}")


# --- the pilot training (TORCH_PY, MPS) ----------------------------------------------------------------

def pilot_examples(ctx, root, arm, smoke=False):
    """(rows, dropped): the pilot's examples with every feature this arm needs; refused examples
    (either stage) are dropped from every arm."""
    mixrows = build_rows(root, "pilot", "mix")
    stemrows = build_rows(root, "pilot", "mega53")
    unbuilt = pilot_unbuilt(ctx.parts["pilot"], mixrows, stemrows)
    if unbuilt and not smoke:
        raise SystemExit(f"{len(unbuilt)} pilot examples lack a mix or Mega-53 row: the stem stage must finish "
                         "before any arm trains (every arm drops the same refusals)")
    out, dropped, missing = [], refusals(mixrows, stemrows, {r["i"] for r in ctx.parts["pilot"]}), []
    for r in ctx.parts["pilot"]:
        i = r["i"]
        if i in dropped:
            continue
        if i not in mixrows or (arm in STEM_ARMS and i not in stemrows):
            missing.append(i)                                 # smoke only (rows decide what is built)
            continue
        need = ["mix"] + (["mega53"] if arm in STEM_ARMS else [])
        if any(not ex_path(root, i, k).exists() for k in need):
            raise SystemExit(f"{i}: a row says built but the features file is missing")
        out.append(r)
    return out, sorted(dropped)


def refusals(mixrows, stemrows, ids):
    """The examples refused by either stage."""
    return {i for i in ids if mixrows.get(i, {}).get("refused") or stemrows.get(i, {}).get("refused")}


def pilot_unbuilt(items, mixrows, stemrows):
    """Examples without a mix row, or unrefused without a Mega-53 row (rows decide, not files)."""
    return [r["i"] for r in items if r["i"] not in mixrows
            or (not mixrows[r["i"]].get("refused") and r["i"] not in stemrows)]


def check_run_parity(runs, final_refused, n_train_expected):
    """Every run dropped exactly the final refusal set and trained on the same count. -> [problems]."""
    bad = []
    for r in runs:
        if set(r.get("dropped_refused") or []) != set(final_refused):
            bad.append(f"{r['arm']}-{r['seed']}: dropped {len(r.get('dropped_refused') or [])}, final {len(final_refused)}")
        if r.get("train") != n_train_expected:
            bad.append(f"{r['arm']}-{r['seed']}: trained on {r.get('train')}, expected {n_train_expected}")
    return bad


class StemData:
    """The pilot's stored true mixes and Mega-53 stems in memory (uint8 halves), the arm's inputs
    per batch: D_mix's stem and D_stem's mix zeroed, D_stem's stem augmented (training only)."""

    def __init__(self, rows, arm, root, aug):
        import numpy as np

        from learn import pretrain_set as PS
        from learn import song_model as SM

        self.rows, self.arm, self.aug = rows, arm, aug
        n = len(rows)
        self.M = np.zeros((n, 2, 96, 446), np.uint8)
        self.LM = np.zeros((n, 2), np.float32)
        self.S = np.zeros((n, 2, 96, 446), np.uint8) if arm in STEM_ARMS else None
        self.LS = np.zeros((n, 2), np.float32)
        self.ga = np.zeros(n, np.float32)
        for j, r in enumerate(rows):
            d = np.load(ex_path(root, r["i"], "mix"))
            self.M[j, 0], self.M[j, 1], self.LM[j] = d["mA"], d["mB"], d["lufs"]
            self.ga[j] = float(d["gain_db"])
            if self.S is not None:
                e = np.load(ex_path(root, r["i"], "mega53"))
                self.S[j, 0], self.S[j, 1], self.LS[j] = e["sA"], e["sB"], e["lufs"]
        self.cands = merge_candidates(rows) if aug else {}
        self.gpos, self.G = {}, None
        if aug:
            pos = sorted({p for v in self.cands.values() for p, _ in v})
            self.gpos = {p: k for k, p in enumerate(pos)}
            self.G = np.zeros((len(pos), 2, 96, 446), np.uint8)
            for p, k in self.gpos.items():
                d = np.load(PS.example_path(rows[p]["i"]))
                self.G[k, 0], self.G[k, 1] = d["gA"], d["gB"]
        self.centres = mel_centres_hz()
        enc = [SM.encode(r["label"]) for r in rows]
        self.Y = [np.stack(z) for z in zip(*enc)]
        self.masked = 0
        self.applied = {}

    def half_input(self, j, epoch):
        """(stem dB, mix dB, stem LUFS, mix LUFS, half) of row j at an epoch (augmented if training)."""
        from learn import pretrain_set as PS

        r = self.rows[j]
        h = half_of(r["i"], epoch)
        mix = PS.dequant(self.M[j, h])
        lm = float(self.LM[j, h])
        if self.S is None:
            return mix, mix, 0.0, lm, h
        stem, ls = PS.dequant(self.S[j, h]), float(self.LS[j, h])
        if self.aug and epoch >= 0:
            def draw(rng, j=j, h=h, r=r):
                p = merge_partner(rng, self.cands[r["base"]], r["section"])
                q = self.rows[p]
                assert q["split"] == "train" and not q.get("early_stop")
                hh = "AB"[h]
                gain = merge_gain_db(r[f"lufs_{hh}"], float(self.ga[j]), q[f"lufs_{hh}"], float(rng.uniform(*MERGE_DB)))
                return PS.dequant(self.G[self.gpos[p], h]), gain

            stem, ls, ap = augment(r["i"], epoch, stem, ls, mix, lm, draw, self.centres)
            for a in ap:
                self.applied[a] = self.applied.get(a, 0) + 1
        return stem, mix, ls, lm, h

    def batch(self, idx, epoch, dev):
        import numpy as np
        import torch

        from learn import pretrain_set as PS
        from learn import song_model as SM

        idx = np.asarray(idx)
        X, C, H = [], [], []
        for j in idx:
            stem, mix, ls, lm, h = self.half_input(int(j), epoch)
            X.append(np.stack([stem, mix]))
            C.append(SM.cond_vec(self.rows[j]["amp"], self.rows[j]["base"], [ls, lm]))
            H.append(h == 0)
        x = SM.norm_feat(np.stack(X))
        PS.mask_half_a(x, np.array(H))
        c = np.stack(C)
        zero_inputs(x, c, self.arm)
        if epoch >= 0:
            self.masked += int(np.sum(H)) * PS.MASK_A_FRAMES
        y = [torch.tensor(z[idx], device=dev) for z in self.Y]
        return torch.tensor(x, device=dev), torch.tensor(c, device=dev), y


class D0Data:
    """Part C's composition (`CurveData`: leak stem, power-sum mix redrawn every epoch), counting
    the masked frames."""

    def __init__(self, rows):
        from learn import pretrain_set as PS
        from learn import song_bank as B

        lv = json.loads((B.OUT / "levels.json").read_text())
        self.d = PS.CurveData(rows, PS.ratio_values(), lv["summary"]["eval_mix_lufs_median"])
        self.rows = rows
        self.masked = 0
        self.applied = {}

    def batch(self, idx, epoch, dev):
        from learn import pretrain_set as PS

        if epoch >= 0:
            self.masked += sum(half_of(self.rows[int(j)]["i"], epoch) == 0 for j in idx) * PS.MASK_A_FRAMES
        return self.d.batch(idx, epoch, dev)


def readout_tensors(root, vrows, stem_kind, arm):
    """V_sep inputs for an arm: (X, C, Y, who) over both halves, the stored true mix and the
    `stem_kind` stem ('mega53' R_in, 'htdemucs' R_out), exact LUFS, mask and zeroing as in training."""
    import numpy as np

    from learn import pretrain_set as PS
    from learn import song_model as SM

    X, C, Y, who = [], [], [], []
    for r in vrows:
        pm, ps_ = ex_path(root, r["i"], "mix"), ex_path(root, r["i"], stem_kind)
        if not (pm.exists() and ps_.exists()):
            raise SystemExit(f"{r['i']}: a row says built but the features file is missing")
        dm, ds = np.load(pm), np.load(ps_)
        for k, h in enumerate("AB"):
            x = SM.norm_feat(np.stack([PS.dequant(ds[f"s{h}"]), PS.dequant(dm[f"m{h}"])]))[None]
            PS.mask_half_a(x, [h == "A"])
            c = SM.cond_vec(r["amp"], r["base"], [float(ds["lufs"][k]), float(dm["lufs"][k])])[None]
            zero_inputs(x, c, arm)
            X.append(x[0]), C.append(c[0]), Y.append(SM.encode(r["label"])), who.append(r["i"])
    if not X:
        return None
    return np.stack(X).astype(np.float32), np.stack(C), [np.stack(z) for z in zip(*Y)], who


def vsep_ready(ctx, root, smoke=False):
    """{readout: rows} when V_sep is built (mix, Mega-53 and htdemucs for every unrefused
    example); None otherwise (smoke: whatever is built)."""
    mixrows = build_rows(root, "vsep", "mix")
    out = {}
    for name, kind in (("R_in", "mega53"), ("R_out", "htdemucs")):
        st = build_rows(root, "vsep", kind)
        ok = [r for r in ctx.parts["vsep"] if r["i"] in mixrows and not mixrows[r["i"]].get("refused")
              and r["i"] in st and not st[r["i"]].get("refused")]
        pending = [r for r in ctx.parts["vsep"] if r["i"] not in mixrows or (r["i"] not in st and not mixrows[r["i"]].get("refused"))]
        if pending and not smoke:
            return None
        out[name] = ok
    return out


def evaluate_readouts(net, ctx, root, arm, dev, smoke=False):
    from learn import pretrain_set as PS

    ready = vsep_ready(ctx, root, smoke)
    if ready is None:
        return None
    res = {}
    for name, kind in (("R_in", "mega53"), ("R_out", "htdemucs")):
        val = readout_tensors(root, ready[name], kind, arm)
        if val is None:
            res[name] = {}
            continue
        per, nll, extra = PS.evaluate(net, val, dev)
        res[name] = {"per_example": per, "nll": nll, "switch_error": extra["switch_error"],
                     "mic_agreement": extra["mic_agreement"]}
    return res


def grad_norm(params):
    """The global gradient norm, computed by hand (MPS `clip_grad_norm_` has returned NaN here)."""
    import torch

    gs = [p.grad.detach().float().pow(2).sum() for p in params if p.grad is not None]
    return torch.sqrt(torch.stack(gs).sum()) if gs else torch.tensor(0.0)


def train_arm(data, tr, es, seed, dev, log, epochs=MAX_EPOCHS):
    """Part C's recipe (`pretrain_set.train_one`): Adam 1e-3, batch 64, one half per example per
    epoch, gradients scaled to norm 5, early stopping on the early-stopping loss (patience 4), at
    most `epochs`; an epoch skipping more than 5% of its steps aborts. -> (best state, best epoch)."""
    import numpy as np
    import torch

    from learn import pretrain_set as PS
    from learn import song_model as SM

    torch.manual_seed(seed)
    net = PS.build_net().to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=PS.LR)
    best, bad, state, best_ep = math.inf, 0, None, None
    rng = np.random.default_rng(seed)
    for epoch in range(epochs):
        net.train()
        t0 = time.time()
        order = rng.permutation(tr)
        tl, skipped, steps = [], 0, 0
        for j in range(0, len(order), PS.BATCH):
            x, c, y = data.batch(order[j:j + PS.BATCH], epoch, dev)
            loss = SM.loss_fn(net(x, c), *y)
            opt.zero_grad()
            loss.backward()
            g = grad_norm(net.parameters())
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
            for j in range(0, len(es), PS.BATCH):
                x, c, y = data.batch(es[j:j + PS.BATCH], -1, dev)          # one fixed draw, never augmented
                el.append(float(SM.loss_fn(net(x, c), *y)))
        v = sum(el) / max(1, len(el))
        dt = max(time.time() - t0, 1e-9)
        mem = None
        if dev.type == "mps":
            mem = round(torch.mps.driver_allocated_memory() / 1e9, 2)
        log.append({"epoch": epoch, "train": sum(tl) / max(1, len(tl)), "early_stop": v, "seconds": round(dt, 1),
                    "samples_per_s": round(len(order) / dt, 1), "skipped_steps": skipped, "steps": steps,
                    "mps_driver_gb": mem})
        print(log[-1], flush=True)
        if skipped > PS.MAX_SKIP_SHARE * max(1, steps):
            raise PS.StepsSkipped(f"epoch {epoch}: {skipped} of {steps} steps non-finite")
        if math.isfinite(v) and v < best - 1e-4:
            best, bad, best_ep = v, 0, epoch
            state = {k: t.detach().cpu().clone() for k, t in net.state_dict().items()}
        else:
            bad += 1
            if bad >= PS.PATIENCE:
                break
    if state is None or not math.isfinite(best):
        raise PS.StepsSkipped("no finite early-stopping loss in any epoch")
    net.load_state_dict(state)
    net.eval()
    return net, state, best_ep, best


def run_path(root, arm, n, seed):
    return root / "pilot" / "runs" / f"{arm}-{n}-{seed}.json"


def cmd_train(args):
    import resource

    import numpy as np
    import torch

    from learn import pretrain_set as PS

    if args.epochs and not 0 < args.epochs <= MAX_EPOCHS:
        raise SystemExit(f"--epochs must be 1-{MAX_EPOCHS}")
    if args.n != "5000":
        raise SystemExit("--n full is step 3 (not implemented yet)")
    if args.smoke and not args.out:
        raise SystemExit("--smoke writes into a scratch --out only")
    if args.seed not in TRAIN_SEEDS and not args.smoke:
        raise SystemExit(f"the pilot's seeds are {TRAIN_SEEDS}")
    root = out_root(args)
    rp = run_path(root, args.arm, args.n, args.seed)
    if rp.exists():
        print(f"{rp.name} exists: nothing to do")
        return
    ctx = Ctx()
    rows, dropped = pilot_examples(ctx, root, args.arm, args.smoke)
    tr = np.array([j for j, r in enumerate(rows) if not r["early_stop"]])
    es = np.array([j for j, r in enumerate(rows) if r["early_stop"]])
    if not len(tr) or not len(es):
        raise SystemExit(f"{len(tr)} training and {len(es)} early-stopping examples")
    if not args.smoke and len(tr) + len(dropped) - sum(1 for i in dropped if ctx.rows[i]["early_stop"]) != N_PILOT_TRAIN:
        raise SystemExit("the pilot's training examples do not add up to 5,000")
    torch.set_num_threads(2)
    dev = torch.device("cpu" if os.environ.get("DS_DEVICE") == "cpu" or not torch.backends.mps.is_available() else "mps")
    t_load = time.time()
    data = D0Data(rows) if args.arm == "D0" else StemData(rows, args.arm, root, aug=args.arm == "Dstem")
    print(f"{args.arm} seed {args.seed}: {len(tr)} train, {len(es)} early stopping, {len(dropped)} refused examples "
          f"dropped; loaded in {time.time() - t_load:.0f} s on {dev}", flush=True)
    t0 = time.time()
    for attempt in (1, 2):
        log = []
        data.masked, data.applied = 0, {}
        try:
            net, state, best_ep, best = train_arm(data, tr, es, args.seed, dev, log, args.epochs or MAX_EPOCHS)
            break
        except PS.StepsSkipped as e:
            print(f"attempt {attempt} aborted: {e}", flush=True)
            if dev.type == "mps":
                torch.mps.empty_cache()
            if attempt == 2:
                raise SystemExit(f"TRAIN FAILED {args.arm} {args.seed}: {e}")
    minutes = (time.time() - t0) / 60
    rp.parent.mkdir(parents=True, exist_ok=True)
    mp = rp.with_suffix(".pt")
    torch.save(state, mp)
    readouts = evaluate_readouts(net, ctx, root, args.arm, dev, args.smoke)
    rec = {"plan": "docs/direct-model-stems-plan.md step 2, amendment 1", "arm": args.arm, "n": args.n, "seed": args.seed,
           "train": len(tr), "early_stop": len(es), "dropped_refused": dropped, "attempts": attempt,
           "epochs_run": len(log), "best_epoch": best_ep, "best_early_stop_loss": best, "minutes": round(minutes, 1),
           "examples_per_s": round(len(tr) * len(log) / max(minutes * 60, 1e-9), 1),
           "skipped_steps": sum(e["skipped_steps"] for e in log), "masked_frames": int(data.masked),
           "augmentations_applied": data.applied, "peak_rss_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2),
           "peak_mps_driver_gb": max((e["mps_driver_gb"] or 0) for e in log), "device": str(dev),
           "max_epochs": args.epochs or MAX_EPOCHS, "smoke": bool(args.smoke), "model": mp.name,
           "model_sha256": hashlib_file(mp), "readouts": readouts, "log": log, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(rp, rec)
    print(f"TRAIN DONE {args.arm} {args.seed}: best epoch {best_ep} of {len(log)}, {minutes:.1f} min"
          + ("" if readouts else "; V_sep not built yet, readouts pending (pilot-report evaluates them)"), flush=True)


def hashlib_file(p):
    import hashlib

    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


# --- the pilot readout -----------------------------------------------------------------------------------

def cmd_pilot_report(args):
    """R_out (unmastered V_sep, htdemucs stem) and R_in (V_sep, Mega-53 stem): E seed-averaged,
    paired per example, band-clustered t over V_sep's bands, Bannockburn and every MUSDB18-tagged
    section left out; amendment 1's rules."""
    root = out_root(args)
    ctx = Ctx()
    runs = {}
    for arm in ARMS:
        for seed in TRAIN_SEEDS:
            r = _load(run_path(root, arm, "5000", seed))
            if r is None:
                continue
            if not r.get("readouts"):
                import torch

                from learn import pretrain_set as PS

                dev = torch.device("cpu" if os.environ.get("DS_DEVICE") == "cpu" or not torch.backends.mps.is_available() else "mps")
                net = PS.build_net()
                net.load_state_dict(torch.load(run_path(root, arm, "5000", seed).with_suffix(".pt"), map_location="cpu"))
                net = net.to(dev).eval()
                r["readouts"] = evaluate_readouts(net, ctx, root, arm, dev, args.smoke)
                if r["readouts"] is None:
                    raise SystemExit("V_sep is not built: no readout yet")
                _save(run_path(root, arm, "5000", seed), r)
            runs.setdefault(arm, []).append(r)
    missing = [f"{a}-{s}" for a in ARMS for s in TRAIN_SEEDS if not any(x["seed"] == s for x in runs.get(a, []))]
    if missing and not args.smoke:
        raise SystemExit(f"runs missing: {missing}")
    pm, pst = build_rows(root, "pilot", "mix"), build_rows(root, "pilot", "mega53")
    pilot_ids = {r["i"] for r in ctx.parts["pilot"]}
    final = refusals(pm, pst, pilot_ids)
    n_tr = sum(1 for r in ctx.parts["pilot"] if not r["early_stop"] and r["i"] not in final)
    bad = check_run_parity([x for rs in runs.values() for x in rs], final, n_tr)
    if pilot_unbuilt(ctx.parts["pilot"], pm, pst):
        bad.append("the pilot's stem stage is not complete")
    if bad and not args.smoke:
        raise SystemExit("arms did not train on the same examples: " + "; ".join(bad))
    mixrows = build_rows(root, "vsep", "mix")
    band_of = {str(r["i"]): r["band"] for r in ctx.parts["vsep"]}
    untagged = {str(r["i"]) for r in ctx.parts["vsep"] if not ctx.tag[r["i"]]}
    unmastered = {str(i) for i, m in mixrows.items() if not m.get("refused") and not m.get("mastered")}
    keep = {"R_in": untagged, "R_out": untagged & unmastered}
    from learn import pretrain_set as PS

    per = {(a, ro): PS.seed_avg([x["readouts"][ro]["per_example"] for x in rs], keep[ro])
           for a, rs in runs.items() for ro in ("R_in", "R_out")}
    levels = {f"{a}|{ro}": PS.band_t_interval({b: v for b, v in PS.by_band(p, band_of).items()}) if p else None
              for (a, ro), p in per.items()}
    want = {"Dstem-D0|R_out": ("Dstem", "D0", "R_out"), "Dmix-D0|R_out": ("Dmix", "D0", "R_out"),
            "Dmix-Dstem|R_in": ("Dmix", "Dstem", "R_in"), "Dstem-Dstem-noaug|R_in": ("Dstem", "Dstem-noaug", "R_in")}
    beside = {"Dstem-D0|R_in": ("Dstem", "D0", "R_in"), "Dmix-D0|R_in": ("Dmix", "D0", "R_in"),
              "Dmix-Dstem|R_out": ("Dmix", "Dstem", "R_out"), "Dstem-Dstem-noaug|R_out": ("Dstem", "Dstem-noaug", "R_out")}
    thr = PS._load(PS.OUT / "scope-threshold.json")                     # part C's frozen scope line
    scope_in = {str(r["i"]) for r in ctx.parts["vsep"] if not PS.is_beyond(r, thr)}
    con = {}
    for k, (a, b, ro) in {**want, **beside}.items():
        pa, pb = per.get((a, ro)), per.get((b, ro))
        con[k] = paired(pa, pb, band_of, keep[ro]) if pa and pb else None
    for k, (a, b, ro) in want.items():                                  # descriptive: part C's keep_in rule
        pa, pb = per.get((a, ro)), per.get((b, ro))
        con[f"scope_in {k}"] = paired(pa, pb, band_of, keep[ro] & scope_in) if pa and pb else None
    dec, aug, why = pilot_rules({k: con[k] for k in want})
    out = {"plan": "docs/direct-model-stems-plan.md step 2, amendment 1 rules", "levels": levels, "contrasts": con,
           "deciding": list(want), "decision": dec, "augmentation_kept": aug, "reasons": why,
           "examples": {ro: len(keep[ro]) for ro in keep}, "scope_in_examples": len(scope_in),
           "parity_problems": bad, "final_refused": sorted(final),
           "left_out_tagged": sum(1 for r in ctx.parts["vsep"] if ctx.tag[r["i"]]),
           "runs": {a: [x["seed"] for x in rs] for a, rs in runs.items()}, "smoke": bool(args.smoke),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "pilot" / "pilot-report.json", out)

    def f(v):
        return "n/a" if v is None else f"{v[0]:+.4f} [{v[1]:+.4f}, {v[2]:+.4f}] ({v[3]} bands)"

    for k, v in levels.items():
        print(f"E {k:20s} {f(v)}")
    for k, v in con.items():
        print(f"{'*' if k in want else ' '} {k:26s} {f(v)}")
    print("; ".join(why))
    print(f"PILOT {dec}" + ("" if aug else " (augmentation dropped)"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("separate", "move", "reliance", "audit-mix", "sepcheck", "build", "train",
                                    "pilot-report"))
    ap.add_argument("--sep", choices=("mega53", "htdemucs"))
    ap.add_argument("--part", choices=("pilot", "vsep", "rest"))
    ap.add_argument("--stage", choices=("mix", "stem"))
    ap.add_argument("--shard", type=parse_shard, default=(0, 1), help="mix stage: whole sections, balanced (shard_sections)")
    ap.add_argument("--device", choices=("mps", "cpu"), default="mps", help="stem stage, Mega-53")
    ap.add_argument("--order", choices=("asc", "desc"), default="asc",
                    help="stem stage: two workers (MPS asc, CPU desc) meet in the middle")
    ap.add_argument("--setting", choices=("fast", "stored"), help="smoke tests only: a Mega-53 setting without 1c")
    ap.add_argument("--disk-guard-gb", type=float, default=None,
                    help=f"default {DISK_GUARD_GB:.0f}; the pilot build may go to {DISK_GUARD_PILOT_GB:.0f} ({DISK_OVERRIDE_NOTE})")
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--n", default="5000", choices=("5000", "full"))
    ap.add_argument("--seed", type=int)
    ap.add_argument("--epochs", type=int, help=f"at most {MAX_EPOCHS} (smoke tests: fewer)")
    ap.add_argument("--out", help="a scratch output root instead of ~/ndsp-presets/learn/direct-stems (smoke tests)")
    ap.add_argument("--limit", type=int, help="build: the first N examples of the part (smoke tests, scratch --out only)")
    ap.add_argument("--smoke", action="store_true", help="train / pilot-report on whatever is built (scratch --out only)")
    a = ap.parse_args(argv)
    if a.sep == "htdemucs":
        os.environ.setdefault("HF_HUB_OFFLINE", "1")          # the cached htdemucs model only, before any import
    if a.cmd == "separate" and not a.sep:
        ap.error("separate needs --sep")
    if a.cmd == "build" and not (a.part and a.stage):
        ap.error("build needs --part and --stage")
    if a.cmd == "train" and not (a.arm and a.seed is not None):
        ap.error("train needs --arm and --seed")
    {"separate": cmd_separate, "move": cmd_move, "reliance": cmd_reliance, "audit-mix": cmd_audit_mix,
     "sepcheck": cmd_sepcheck, "build": cmd_build, "train": cmd_train, "pilot-report": cmd_pilot_report}[a.cmd](a)


if __name__ == "__main__":
    main()
