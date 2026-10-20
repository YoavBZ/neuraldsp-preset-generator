"""The direct model with realistic stems: gate 1, the zero-render checks
(`docs/direct-model-stems-plan.md`, steps 1a and 1b). Development data only. No training, no
renders, no training-set build.

    MSST=~/ndsp-presets/tools/msst-venv/bin/python; TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MSST     -m learn.direct_stems separate --sep mega53     # Mega-53 fast: audit true mixes + stage F crops
    $TORCH_PY -m learn.direct_stems separate --sep htdemucs   # htdemucs: audit true mixes
    $TORCH_PY -m learn.direct_stems move                      # 1a: stem-swap movement, the audit cost, GATE1
    $TORCH_PY -m learn.direct_stems reliance                  # 1b: stem vs mix reliance (V_dev, stage F)

Outputs go to ~/ndsp-presets/learn/direct-stems/gate1/.

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

The pure parts are unit-tested (`tests/test_direct_stems.py`); the commands that load models or
separators are not, like the other step modules.
"""

from __future__ import annotations

import argparse
import json
import math
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("separate", "move", "reliance", "audit-mix"))
    ap.add_argument("--sep", choices=("mega53", "htdemucs"))
    a = ap.parse_args(argv)
    if a.cmd == "separate" and not a.sep:
        ap.error("separate needs --sep")
    {"separate": cmd_separate, "move": cmd_move, "reliance": cmd_reliance, "audit-mix": cmd_audit_mix}[a.cmd](a)


if __name__ == "__main__":
    main()
