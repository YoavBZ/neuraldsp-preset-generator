"""The separation plan's S1 Amendment 3 and S3 (`docs/separation-plan.md`; ledger `separation` `phase_s1_a3`,
`phase_s3`): steer the stereo pair so the named guitar sits in the centre, then separate.

- **Steering:** a constant-power pan p has the angle theta = (p + 1) * pi / 4 (L = cos theta, R = sin theta). Given a
  hint p_h, the pair is rotated by phi = pi / 4 - theta_h: a source at the hint lands in the centre, a source on the
  other side turns anti-phase. The rotation is orthonormal and undone by -phi.
- **The hint:** coarse, as the picker gives it (centre 0 if |p| < 0.25, left -0.7, right +0.7); a double by its louder
  (first) copy. In S0 it comes from the drawn pan, an oracle for the user's pick. `_exact` options use the drawn pan.
- **S1 Amendment 3 (zero training):** `steer_mdxc` (steer, MDX23C centre, the mean of its two outputs, X-LANCE),
  `steer_mid` (steer, X-LANCE on the steered pair, the mid of its two outputs), `steer_mdxc_exact` (the ceiling).
  A steered stem is the steered mid times cos phi: exactly what rotating a centred source back and averaging gives,
  so the stem sits at the target's level in the unsteered mid, like every S0 stem.

    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s3 s3-steer --set main|split     # CPU, 4 threads
    $TORCH_PY -m learn.sep_s3 s3-feats --set main|split                                     # the model's read
    .venv/bin/python -m learn.sep_s3 s3-read --set main|split

The pure parts (the angles, the rotation, the hint) are unit-tested.
"""

from __future__ import annotations

import argparse
import json
import math
import time

from learn import sep_s0 as S0
from learn import sep_s1b as S1B

PHASE_A3, PHASE_S3 = "phase_s1_a3", "phase_s3"
HINT_SIDE = 0.7                            # the coarse hint's left/right value (the plan, fixed before any read)
CENTRE_BAND = 0.25                         # |p| below this is a centre hint
STEER_OPTIONS = ("steer_mdxc", "steer_mid", "steer_mdxc_exact", "steer_mdxc_h1", "steer_xlmdxc")
RULE_STEER = ("steer_mdxc", "steer_xlmdxc")   # under S1's rule; steer_mid a control, `_exact` a ceiling, `_h1` a
#                                             sensitivity; steer_xlmdxc is Amendment 3b (s1b's centred winner, steered)
HINT_H1 = 1.0                              # the review's sensitivity: a hard side hint
TRAIN_BANDS = ("Forkupines", "BKS", "The Maybe Next Years", "Adam Buckley")   # cached; Adam Buckley validates
VAL_BAND = "Adam Buckley"                  # the review: a whole band for the curve, not in S0
HELD_BANDS = ("Hazael", "The Travelling Band", "Ale Lak", "Storm Of Particles", "Dunning Kruger")
TRAINED = ("s3", "s4")                     # the trained candidates read once on the held-out bands (S3, S4)


def require(phase):
    from learn import pipeline_fix as P

    d = json.loads((P.REPO / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == S0.LEDGER_ID), None)
    if not e or phase not in e:
        raise SystemExit(f"the ledger's separation entry has no {phase}: declare it before running")


# --- the pure parts -------------------------------------------------------------------------------------------------------

def theta(p):
    """The constant-power pan angle of p in [-1, 1] (S0.pan's law: L = cos theta, R = sin theta)."""
    return (max(-1.0, min(1.0, p)) + 1) * math.pi / 4


def steer_phi(p_hint):
    """The rotation that moves a source at p_hint to the centre."""
    return math.pi / 4 - theta(p_hint)


def rotate(L, R, phi):
    """[L, R] rotated by phi (orthonormal; rotate(*rotate(L, R, phi), -phi) gives L, R back)."""
    c, s = math.cos(phi), math.sin(phi)
    return c * L - s * R, s * L + c * R


def coarse(p, side=HINT_SIDE):
    """The picker-like hint of a pan: 0 in the centre band, else +-side."""
    return 0.0 if abs(p) < CENTRE_BAND else math.copysign(side, p)


def hint_of(meta, exact=False):
    """An item's hint from its drawn placement: its (louder, first) copy's pan, coarse unless exact."""
    p = float(meta["target"][0])
    return p if exact else coarse(p)


def hint_for(meta, option):
    """The hint an option steers by: the exact pan (`_exact`), a hard side hint (`_h1`), else the coarse hint."""
    if option.endswith("_exact"):
        return hint_of(meta, exact=True)
    if option.endswith("_h1"):
        return coarse(float(meta["target"][0]), HINT_H1)
    return hint_of(meta)


def steered_pan(p, p_hint):
    """Where a source at p sits after steering by p_hint (the review's |p'|), as a pan in [-1, 1] when it stays in the
    front quadrant (outside it the source is partly anti-phase)."""
    return (theta(p) + steer_phi(p_hint)) * 4 / math.pi - 1


def steered_stem(mid, phi):
    """A steered stem's mid moved to the unsteered mid's level: a centred source [m, m] rotated back by -phi and
    averaged is cos(phi) * m."""
    return math.cos(phi) * mid


# --- S1 Amendment 3: steering with the existing tools -----------------------------------------------------------------

def cmd_steer(args):
    import shutil

    import numpy as np

    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import stereo_side_screen as SSS
    from learn import trusted_data as T

    require(PHASE_A3)
    require("phase_s1_a3b")                    # steer_xlmdxc
    root = S1B.set_dir(args.set)
    sep = DS.stem_separator(T.SEP, "cpu")       # X-LANCE on the CPU, 4 threads: the MPS stays free for S3
    mdx = SSS.Centre()                          # MDX23C, hash-checked, CPU
    items = sorted((root / "items").glob("*.npz"))
    same = {"steer_mdxc": "mdxc", "steer_mdxc_h1": "mdxc", "steer_mid": "stereo",       # a centre hint: no rotation
            "steer_xlmdxc": "xlst_mdxc"}
    n_check, checks, t0 = 0, [], time.time()
    for m, p in enumerate(items):
        z = np.load(p)
        meta = json.loads(p.with_suffix(".json").read_text())
        L, R = np.asarray(z["L"], np.float64), np.asarray(z["R"], np.float64)
        cache = {}
        for o in (args.options or STEER_OPTIONS):
            q = root / "stems" / o / p.name
            if q.exists():
                continue
            q.parent.mkdir(parents=True, exist_ok=True)
            phi = steer_phi(hint_for(meta, o))
            src = root / "stems" / same.get(o, "-") / p.name
            if phi == 0.0 and src.exists():
                if n_check >= 5 or o not in same:
                    shutil.copyfile(src, q)
                    continue
            Ls, Rs = rotate(L, R, phi)
            if o == "steer_mid":
                s = S0.xl_stereo(sep, Ls, Rs)              # the mean of X-LANCE's two outputs: the steered mid
            elif o == "steer_xlmdxc":                       # X-LANCE on the steered pair, both outputs, then MDX23C
                from learn import separator_screen as SCR

                st2 = np.stack([SCR.to48(c, len(L)) for c in DS.xl_run_chunked(
                    sep._f, np.stack([SCR.to44(Ls), SCR.to44(Rs)]))])
                s = mdx(st2).mean(0)
            else:
                key = round(phi, 12)
                if key not in cache:                        # an equal hint: one centre pass
                    cache[key] = sep(mdx(np.stack([Ls, Rs])).mean(0))
                s = cache[key]
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            stem = np.asarray(steered_stem(s, phi), np.float16)[:len(L)]
            np.savez(q, stem=stem)
            if phi == 0.0 and src.exists() and o in same:   # the identity check: recomputed against the stored stem
                ref = np.asarray(np.load(src)["stem"], np.float64)
                k = min(len(ref), len(stem))
                checks.append({"item": p.stem, "option": o, "max_abs_diff": float(np.max(np.abs(
                    np.asarray(stem, np.float64)[:k] - ref[:k]))), "ref_peak": float(np.max(np.abs(ref)))})
                n_check += 1 / len(same)                    # an item's centre-hint options count as one check
        if m % 10 == 0:
            print(f"s3 steer {args.set} {m + 1}/{len(items)}: {time.time() - t0:.0f} s", flush=True)
    if checks:
        f = root / "steer-identity-check.json"
        old = json.loads(f.read_text()) if f.exists() else []
        f.write_text(json.dumps(old + checks, indent=1))
    print(f"S3 STEER DONE: {args.set} ({len(checks)} identity checks)", flush=True)


def existing_options(set_name):
    """Every option read before this amendment on a set (S1's and s1b's), mono first."""
    if set_name == "main":
        return ["mono"] + [o for o in S0.ALL_OPTIONS if o != "mono"] + [o for o in S1B.READ_OPTIONS
                                                                         if o not in S0.ALL_OPTIONS]
    return list(S1B.READ_OPTIONS)


def stem_any(root, set_name, o, name):
    """A stem of any option: S1's (main set), s1b's, or this module's (steer_*, s3)."""
    import numpy as np

    if o in STEER_OPTIONS or o in TRAINED:
        return np.asarray(np.load(root / "stems" / o / name)["stem"], np.float64)
    if set_name == "main" and o in S0.ALL_OPTIONS:
        return S0.stem_of(o, name)
    return S1B.stem_of(root, o, name)


def has_stem(root, o, name):
    if o in STEER_OPTIONS or o in TRAINED:
        return (root / "stems" / o / name).exists()
    if o in S0.DERIVED:
        return all((root / "stems" / k / name).exists() for k in ("mono", "mega"))
    return S1B._has_inputs(root, o, name)


def model_feats(nets, s, mix, cls):
    """The adopted model's floored body features of a stem at the product's input level (s1b-feats' f_of), 48 kHz."""
    import numpy as np

    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import product_path as PP

    g = DE.inference_gain_db(mix, PP.MIX_LEVEL)
    s8, _, ls, _ = DS.step4_half(s, mix, PP.HALF, g)
    s8 = np.maximum(s8, PP.FLOOR_U8)
    return PP._feats(nets, DS.model_input(s8, s8, ls, ls, PP.HALF, PP.EMBED_AMP, cls, "Dstem")[0])


def check_trained(what, root):
    """A trained candidate's stems on a set are from its picked checkpoint, and its phases are declared: S3 by
    Amendment 3d's pick, S4 by its own pick. Nothing for the zero-training options."""
    if what == "s3":
        from learn import sep_s3_train as TR

        require(TR.PHASE_S3D)
        TR.check_stems(root)                   # Amendment 3d: the stems are from the picked checkpoint
    elif what == "s4":
        from learn import sep_s4_train as S4T

        require(S4T.PHASE_S4)
        S4T.check_stems(root)


def cmd_feats(args):
    """The model's read (the adopted model's floored body features, cosine distance to the clean target's) for this
    module's options, as s1b-feats does for its own."""
    import numpy as np

    from learn import product_path as PP

    trained = args.options in TRAINED
    require(PHASE_S3 if trained else PHASE_A3)
    root = S1B.set_dir(args.set)
    check_trained(args.options, root)
    opts = (args.options,) if trained else STEER_OPTIONS
    nets, _, _ = PP._adopted()

    def f_of(s, mix, cls):
        return model_feats(nets, s, mix, cls)

    f = root / "feats-s3.json"
    out = json.loads(f.read_text())["cosine_distance_to_clean"] if f.exists() else {}
    for p in sorted((root / "items").glob("*.npz")):
        if not any(has_stem(root, o, p.name) for o in opts):
            continue
        z = np.load(p)
        meta = json.loads(p.with_suffix(".json").read_text())
        mix = (np.asarray(z["L"], np.float64) + np.asarray(z["R"], np.float64)) / 2
        ref = f_of(np.asarray(z["target"], np.float64), mix, meta["cls"])
        out.setdefault(p.stem, {}).update({o: PP.cosine_distance(f_of(stem_any(root, args.set, o, p.name), mix,
                                                                       meta["cls"]), ref)
                                           for o in opts if has_stem(root, o, p.name)})
    f.write_text(json.dumps({"cosine_distance_to_clean": out}))
    print(f"S3 FEATS DONE: {args.set} {args.options}", flush=True)


def _boot(diffs, rows, n=2000, seed=S0.SEED):
    """The item bootstrap within bands (beside, never under a rule): resample items within each band, keep the band
    mix. -> {mean, lo90, hi90}."""
    import numpy as np

    rng = np.random.default_rng(seed)
    by = {}
    for d_, r in zip(diffs, rows):
        by.setdefault(r["band"], []).append(d_)
    groups = [np.asarray(v) for v in by.values()]
    ms = [np.mean(np.concatenate([g[rng.integers(0, len(g), len(g))] for g in groups])) for _ in range(n)]
    return {"mean": float(np.mean(diffs)), "lo90": float(np.percentile(ms, 5)), "hi90": float(np.percentile(ms, 95))}


def _clustered(diffs, rows):
    """The band-clustered t interval (the repo's `clustered`: items averaged within a band, df = bands - 1)."""
    from learn import pipeline_fix as P

    c = P.clustered([(r["band"], r["i"], d_) for d_, r in zip(diffs, rows)])
    if not c.get("clusters"):
        return {"mean": None, "lo90": None, "hi90": None, "clusters": 0}
    return {k: c[k] for k in ("mean", "lo90", "hi90", "clusters", "clusters_positive", "clusters_negative",
                              "per_cluster")}


def routed(meta, what="a3"):
    """The existing option the coarse hint routes to: a centre hint to xlst_mdxc (Amendment 3b: s1b's centred winner,
    stronger than mdxc on the training-band items too), a side hint to side; for S3's read a side hint to
    steer_xlmdxc (Amendment 3c: A3's side winner, ahead of side on the training-band items too)."""
    if hint_of(meta) == 0.0:
        return "xlst_mdxc"
    return "steer_xlmdxc" if what in TRAINED else "side"


def s3_decision(si_mono, rd_mono, si_comp, rd_comp):
    """S3's rule for one cell from four clustered intervals (SI-SDR and read gains against mono and the routed
    comparator; a read gain is a drop in cosine distance). -> 'default' | 'picker choice' | 'not used'."""
    if None in (si_mono["lo90"], rd_mono["lo90"], si_comp["lo90"], si_comp["hi90"], rd_comp["hi90"]):
        return "not read"
    wins = si_mono["lo90"] > 0 and rd_mono["lo90"] > 0
    if wins and si_comp["lo90"] > 0 and rd_comp["hi90"] >= 0:
        return "default"
    if wins and rd_comp["hi90"] >= 0 and si_comp["hi90"] >= 0:      # SI-SDR undecided, not clearly worse
        return "picker choice"
    return "not used"


def trained_decision(what, si_mono, rd_mono, si_comp, rd_comp):
    """S3's rule for S3. For S4 (it starts at the routed comparator, so an unchanged model would pass as not worse):
    a picker choice also needs a decided read gain over the comparator (lo90 > 0)."""
    d = s3_decision(si_mono, rd_mono, si_comp, rd_comp)
    if what == "s4" and d == "picker choice" and not (rd_comp["lo90"] is not None and rd_comp["lo90"] > 0):
        return "not used"
    return d


PBINS = ((0.0, 0.15), (0.15, 0.3), (0.3, 9.0))


def cmd_read(args):
    """`--what a3`: S1's rule (band bootstrap against mono) for `steer_mdxc`, every steer option beside, all bands.
    `--what s3`: S3's rule on the held-out bands (the band-clustered t interval; against mono and the routed
    comparator; the read co-primary). Beside, both: the routed comparator, the clustered t and item-bootstrap
    intervals, the gain by the target's steered pan |p'|, and the best existing option per stratum chosen on the
    training-band items (Forkupines, BKS) then read on the others."""
    import numpy as np

    from learn import fx_reader as FX
    from learn import fx_t0 as T0
    from learn import pretrain_set as PS

    trained = args.what in TRAINED
    require(PHASE_S3 if trained else PHASE_A3)
    root = S1B.set_dir(args.set)
    if trained:
        require("phase_s1_a3c")                # the side hint read against steer_xlmdxc
        check_trained(args.what, root)
    h = PS.half_slices()["A"]
    feats = {}
    for fn in ("feats.json", "feats-s1b.json", "feats-s3.json"):
        if (root / fn).exists():
            for k, v in json.loads((root / fn).read_text())["cosine_distance_to_clean"].items():
                feats.setdefault(k, {}).update(v)
    new = ([args.what] if trained else []) + list(STEER_OPTIONS)
    old = existing_options(args.set)
    t0its, _ = T0.items()
    lab = {it["i"]: T0.labels(it["settings"]) for it in t0its}
    z0 = np.load(T0.out_dir() / "features.npz")
    lib_amp = np.array([it["amp"] for it in t0its])
    lib_band = np.array([it["band"] for it in t0its])
    lib_don = np.array([lab[it["i"]]["don"] for it in t0its])
    jd = [T0.FEATURES.index(f_) for f_ in T0.OWN["delay"]]

    def vote(s_, amp, band):
        sel = np.where((lib_amp == amp) & (lib_band != band))[0]
        q = np.asarray(T0.features(s_), np.float64)[jd][None]
        return float(lib_don[sel[T0.neighbours(z0["target"][sel][:, jd], q)[0]]].mean())

    full = set(new) | {"mono", "mdxc", "xlst_mdxc", "side"}   # the full row where a rule or a comparator reads it
    rows, metas = {o: {} for o in old + new}, {}
    for p in sorted((root / "items").glob("*.npz")):
        meta = json.loads(p.with_suffix(".json").read_text())
        held = meta["band"] in HELD_BANDS
        if trained and not held and meta["band"] not in ("Forkupines", "BKS"):
            continue
        metas[meta["i"]] = meta
        z = np.load(p)
        T_, O_ = np.asarray(z["target"], np.float64)[h], np.asarray(z["others"], np.float64)[h]
        y = lab[meta["i"]]
        for o in old + new:
            if not has_stem(root, o, p.name):
                continue
            s = stem_any(root, args.set, o, p.name)
            r = {"i": meta["i"], "band": meta["band"], "stratum": meta["stratum"], "si_sdr": S0.si_sdr(s[h], T_),
                 "held": held}
            if o in full and (held or args.what == "a3"):
                r["leak_db"] = (S1B.leak3_db(s[h], T_, np.asarray(z["others_own"], np.float64)[h],
                                             np.asarray(z["others_partner"], np.float64)[h]) if args.set == "split"
                                else S0.leak_db(s[h], T_, O_))
                r["cos"] = feats.get(p.stem, {}).get(o)
                r["delay_on"] = int(y["don"])
                r["delay_vote"] = vote(s, meta["amp"], meta["band"])
                if y["don"] == 1:
                    lag, _ = FX.cep_pick(FX.cepstrum(s))
                    r["delay_hit"] = float(abs(lag / 2 ** y["dtime"] - 1) <= 0.10)
            rows[o][meta["i"]] = r
    if args.what == "s4":                       # the review: every held-out item has its S4 stem
        n_held = sum(1 for m_ in metas.values() if m_["band"] in HELD_BANDS)
        n_s4 = sum(1 for r in rows["s4"].values() if r["held"])
        if n_s4 != n_held:
            raise SystemExit(f"S4 stems for {n_s4} of {n_held} held-out items: run s4-apply to the end first")
    read_on = (lambda r: r["held"]) if trained else (lambda r: True)
    # the best existing option per stratum: S3 chooses it on the training-band items (S0's Forkupines and BKS),
    # with the steer options among the candidates; A3 on the same items it reads (the plan, biased to the old options)
    choose_on = (lambda r: not r["held"]) if trained else (lambda r: True)
    cands = old[1:] + (list(STEER_OPTIONS) if trained else [])
    base = rows["mono"]
    strata = ("all",) + (S0.STRATA if args.set == "main" else ("split",))
    rep = {"set": args.set, "what": args.what, "bands_read": sorted({r["band"] for r in base.values() if read_on(r)}),
           "options": {}, "best_existing": {},
           "note": "the split set has no Dunning Kruger item, so its clustered interval has 4 bands (df 3)"}
    for strat in strata:
        sel = [i for i, r in base.items() if choose_on(r) and (strat == "all" or r["stratum"] == strat)]
        best, bm = None, -1e9
        for o in cands:
            pr = [rows[o][i]["si_sdr"] - base[i]["si_sdr"] for i in sel if i in rows[o]]
            if sel and len(pr) == len(sel) and float(np.mean(pr)) > bm:
                best, bm = o, float(np.mean(pr))
        rep["best_existing"][strat] = {"option": best, "n_chosen_on": len(sel)}

    def diff(rs, other, key, sign=1):
        """Paired differences (row minus the other option's row for the same item), key si_sdr or cos."""
        out, kept = [], []
        for r in rs:
            b = rows[other(r)].get(r["i"]) if callable(other) else rows[other].get(r["i"])
            if b is None or r.get(key) is None or b.get(key) is None:
                continue
            out.append(sign * (r[key] - b[key]))
            kept.append(r)
        return out, kept

    comp = lambda r: routed(metas[r["i"]], args.what)   # noqa: E731
    for o in new:
        if not rows[o]:
            continue
        rep["options"][o] = {}
        for strat in strata:
            rs = [r for r in rows[o].values() if read_on(r) and (strat == "all" or r["stratum"] == strat)]
            if not rs or not all(r["i"] in base for r in rs):
                continue
            e = {"n": len(rs), "n_cos": sum(r.get("cos") is not None for r in rs),
                 "si_sdr_median": float(np.median([r["si_sdr"] for r in rs])),
                 "leak_db_median": float(np.median([r["leak_db"] for r in rs if "leak_db" in r]))}
            d_si, k_si = diff(rs, "mono", "si_sdr")
            d_rd, k_rd = diff(rs, "mono", "cos", sign=-1)            # a drop in cosine distance is a gain
            c_si, kc_si = diff(rs, comp, "si_sdr")
            c_rd, kc_rd = diff(rs, comp, "cos", sign=-1)
            e["vs_mono"] = {"si_sdr_clustered": _clustered(d_si, k_si),
                            "si_sdr_band_boot": S0.band_boot(d_si, [r["band"] for r in k_si]),
                            "si_sdr_item_boot": _boot(d_si, k_si),
                            "read_clustered": _clustered(d_rd, k_rd) if len(k_rd) == len(rs) else None,
                            "read_band_boot": (S0.band_boot(d_rd, [r["band"] for r in k_rd])
                                               if len(k_rd) == len(rs) else None)}
            e["vs_routed"] = {"comparator": sorted({comp(r) for r in rs}),
                              "si_sdr_clustered": _clustered(c_si, kc_si),
                              "read_clustered": _clustered(c_rd, kc_rd) if len(kc_rd) == len(rs) else None}
            bx = rep["best_existing"][strat]["option"]
            if bx:
                b_si, kb_si = diff(rs, bx, "si_sdr")
                e["vs_best_existing (beside)"] = {"option": bx, **_clustered(b_si, kb_si)}
            if o in TRAINED:                                    # the plan: steer_mdxc among the comparisons
                t_si, kt_si = diff(rs, "steer_mdxc", "si_sdr")
                t_rd, kt_rd = diff(rs, "steer_mdxc", "cos", sign=-1)
                e["vs_steer_mdxc (beside)"] = {"si_sdr_clustered": _clustered(t_si, kt_si),
                                               "read_clustered": _clustered(t_rd, kt_rd)}
                s_si, ks_si = diff(rs, "side", "si_sdr")      # Amendment 3c: the own channel stays beside
                s_rd, ks_rd = diff(rs, "side", "cos", sign=-1)
                e["vs_side (beside)"] = {"si_sdr_clustered": _clustered(s_si, ks_si),
                                         "read_clustered": _clustered(s_rd, ks_rd)}
            if args.what == "a3":
                vm = e["vs_mono"]
                if o in RULE_STEER and vm["read_band_boot"] is not None:
                    e["wins"] = bool(vm["si_sdr_band_boot"]["lo90"] > 0 and vm["read_band_boot"]["hi90"] >= 0)
                elif o in RULE_STEER:
                    e["wins"] = "not read: the model's read is incomplete"
                else:
                    e["wins"] = "beside, not under the rule"
            elif o in TRAINED:
                if strat == "double":
                    e["decision"] = "descriptive: the double cell is out of S3's rule"
                elif strat in ("centred", "off-centre", "split") and e["vs_mono"]["read_clustered"] \
                        and e["vs_routed"]["read_clustered"]:
                    e["decision"] = trained_decision(o, e["vs_mono"]["si_sdr_clustered"],
                                                     e["vs_mono"]["read_clustered"],
                                                     e["vs_routed"]["si_sdr_clustered"],
                                                     e["vs_routed"]["read_clustered"])
            if o in TRAINED or o.startswith("steer"):           # the gain by the target's steered pan |p'|
                e["by_steered_pan"] = {}
                for lo, hi in PBINS:
                    kk = [(dv, r) for dv, r in zip(d_si, k_si)
                          if lo <= abs(steered_pan(float(metas[r["i"]]["target"][0]),
                                                   hint_of(metas[r["i"]]) if o in TRAINED else
                                                   hint_for(metas[r["i"]], o))) < hi]
                    if kk:
                        e["by_steered_pan"][f"{lo}-{hi if hi < 9 else 'up'}"] = {
                            "n": len(kk), "mean_gain": float(np.mean([dv for dv, _ in kk]))}
            dh = [r["delay_hit"] - base[r["i"]]["delay_hit"] for r in rs if "delay_hit" in r
                  and "delay_hit" in base[r["i"]]]
            von = [r["delay_vote"] - base[r["i"]]["delay_vote"] for r in rs if r.get("delay_on") == 1]
            voff = [r["delay_vote"] - base[r["i"]]["delay_vote"] for r in rs if r.get("delay_on") == 0]
            e["effects"] = {"delay_hit_change": float(np.mean(dh)) if dh else None,
                            "vote_on_change (up better)": float(np.mean(von)) if von else None,
                            "vote_off_change (down better)": float(np.mean(voff)) if voff else None}
            rep["options"][o][strat] = e
    f = root / f"read-s3-{args.what}-{args.set}.json"
    f.write_text(json.dumps(rep, indent=1))
    print(f"S3 READ ({args.what}, {args.set}; bands read {rep['bands_read']})")
    for strat in strata:
        print(f"  best existing on {strat} ({'chosen on the training bands' if trained else 'chosen on these items'}): "
              f"{rep['best_existing'][strat]['option']}")
    nan = {"mean": float("nan"), "lo90": float("nan"), "hi90": float("nan")}
    for o, v in rep["options"].items():
        for strat in strata:
            if strat not in v:
                continue
            e = v[strat]
            g = e["vs_mono"]["si_sdr_band_boot"] if args.what == "a3" else e["vs_mono"]["si_sdr_clustered"]
            rd = e["vs_mono"]["read_clustered"] or nan
            c = e["vs_routed"]["si_sdr_clustered"]
            print(f"  {o:17s} {strat:10s} n {e['n']:3d}  vs mono {g['mean']:+.2f} [{g['lo90'] or float('nan'):+.2f},"
                  f" {g['hi90'] or float('nan'):+.2f}] read {rd['mean'] or float('nan'):+.3f}  vs routed "
                  f"{e['vs_routed']['comparator']} {c['mean'] if c['mean'] is not None else float('nan'):+.2f} "
                  f"[{c['lo90'] if c['lo90'] is not None else float('nan'):+.2f}, "
                  f"{c['hi90'] if c['hi90'] is not None else float('nan'):+.2f}]  "
                  f"{e.get('wins', e.get('decision', ''))}")


ORDER = ("not read", "not used", "picker choice", "default")


def cmd_decide(args):
    """A trained candidate's per-hint decision from both reads (S3's rule, S4's too): the centre hint needs S0's
    centred cell and the split cell (the weaker of the two decides); the side hint is S0's off-centre cell. The double
    cell is descriptive."""
    what = getattr(args, "what", "s3")
    require(PHASE_S3)
    m = json.loads((S1B.set_dir("main") / f"read-s3-{what}-main.json").read_text())["options"][what]
    sp = json.loads((S1B.set_dir("split") / f"read-s3-{what}-split.json").read_text())["options"][what]
    cells = {"centred": m.get("centred", {}).get("decision", "not read"),
             "split": sp.get("split", {}).get("decision", "not read"),
             "off-centre": m.get("off-centre", {}).get("decision", "not read")}
    out = {"cells": cells, "centre_hint": min(cells["centred"], cells["split"], key=ORDER.index),
           "side_hint": cells["off-centre"], "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    (S0.out_dir().parent / f"{what}-decision.json").write_text(json.dumps(out, indent=1))
    print(f"{what.upper()} DECISION: centre hint {out['centre_hint']} (cells {cells['centred']}, {cells['split']}); "
          f"side hint {out['side_hint']}")


def choose(dec3, dec4, gap):
    """S4's plan, the two trained candidates for one hint. dec3, dec4: each one's own decision; gap: the paired mean
    held-out read of S4 minus S3's (cosine distance, negative = S4 reads better; the point estimate, decided or not).
    -> {"default": "s3" | "s4" | None (the routed comparator stays), "picker": the candidates on the picker, first
    first}."""
    dec = {"s3": dec3, "s4": dec4}
    q = [c for c in ("s3", "s4") if dec[c] in ("default", "picker choice")]
    if not q:
        return {"default": None, "picker": []}
    if len(q) == 1:                               # its own rule's outcome, exactly
        return {"default": q[0] if dec[q[0]] == "default" else None, "picker": q}
    if dec3 != dec4:                              # a default beats a picker choice; the other beside
        first = "s3" if dec3 == "default" else "s4"
    else:                                         # one level: the lower held-out read (a tie keeps S3, declared first)
        first = "s4" if gap is not None and gap < 0 else "s3"
    other = "s4" if first == "s3" else "s3"
    return {"default": first if dec[first] == "default" else None, "picker": [first, other]}


def cmd_choose(_args):
    """S4's plan: S3's and S4's decisions per hint combined by `choose`. The gap per hint is the paired mean read
    (S4 minus S3) on the held-out items both have: the centre hint pools S0's held-out centred items and the split
    set's held-out items; the side hint is S0's held-out off-centre items. S4 with no decision file counts as not used
    only when its gate kept it from the read (pick.json usable: false); otherwise this refuses, as without S3's."""
    import numpy as np

    from learn import sep_s4_train as S4T

    require(S4T.PHASE_S4)
    base = S0.out_dir().parent
    if not (base / "s3-decision.json").exists():
        raise SystemExit("S3 hasn't been decided (s3-decision.json): run s3-decide first")
    decs = {"s3": json.loads((base / "s3-decision.json").read_text())}
    if (base / "s4-decision.json").exists():
        decs["s4"] = json.loads((base / "s4-decision.json").read_text())
    else:                                         # not read only by S4's gate; otherwise it's too early
        pk = S4T.out_dir() / "run" / "pick.json"
        if not pk.exists() or json.loads(pk.read_text()).get("usable", True):
            raise SystemExit("S4 is neither decided nor gated out (s4-pick usable: false): too early to choose")
        decs["s4"] = {"centre_hint": "not used", "side_hint": "not used"}
    gaps = {"centre_hint": [], "side_hint": []}
    for set_name in ("main", "split"):
        root = S1B.set_dir(set_name)
        f = root / "feats-s3.json"
        cos = json.loads(f.read_text())["cosine_distance_to_clean"] if f.exists() else {}
        for p in sorted((root / "items").glob("*.npz")):
            meta = json.loads(p.with_suffix(".json").read_text())
            c = cos.get(p.stem, {})
            if meta["band"] not in HELD_BANDS or meta["stratum"] == "double" or "s3" not in c or "s4" not in c:
                continue
            gaps["centre_hint" if hint_of(meta) == 0.0 else "side_hint"].append(c["s4"] - c["s3"])
    out = {"time": time.strftime("%Y-%m-%d %H:%M:%S")}
    for h in ("centre_hint", "side_hint"):
        g = float(np.mean(gaps[h])) if gaps[h] else None
        out[h] = {"s3": decs["s3"][h], "s4": decs["s4"][h], "read_gap_s4_minus_s3": g, "n": len(gaps[h]),
                  **choose(decs["s3"][h], decs["s4"][h], g)}
    (base / "trained-choice.json").write_text(json.dumps(out, indent=1))
    for h in ("centre_hint", "side_hint"):
        o = out[h]
        print(f"TRAINED CHOICE {h}: S3 {o['s3']}, S4 {o['s4']}, gap {o['read_gap_s4_minus_s3']} (n {o['n']}) -> "
              f"default {o['default'] or 'the routed comparator'}, picker {o['picker']}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="learn.sep_s3")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("s3-steer")
    s.add_argument("--set", choices=("main", "split"), required=True)
    s.add_argument("--options", nargs="+", choices=STEER_OPTIONS,
                   help="only these (a second process beside a run, with options the run doesn't make)")
    s.set_defaults(fn=cmd_steer)
    s = sub.add_parser("s3-feats")
    s.add_argument("--set", choices=("main", "split"), required=True)
    s.add_argument("--options", choices=("steer",) + TRAINED, default="steer")
    s.set_defaults(fn=cmd_feats)
    s = sub.add_parser("s3-read")
    s.add_argument("--set", choices=("main", "split"), required=True)
    s.add_argument("--what", choices=("a3",) + TRAINED, default="a3")
    s.set_defaults(fn=cmd_read)
    sub.add_parser("s3-choose").set_defaults(fn=cmd_choose)
    s = sub.add_parser("s3-decide")
    s.add_argument("--what", choices=TRAINED, default="s3")
    s.set_defaults(fn=cmd_decide)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
