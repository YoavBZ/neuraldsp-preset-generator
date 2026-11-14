"""The separation plan's S0 and S1 (`docs/separation-plan.md`; ledger `separation`): a known-truth stereo measuring stick
and the existing tools on it. 200 of E1e's wide draws are rebuilt in stereo by D_CC's recipe, with the target placed in
one of three strata (a centred lead, an off-centre target, a double-tracked target). Each S1 option's mono stem is
scored against the target as it sits in the mix: SI-SDR on half A, the other guitars' leak, the adopted model's read
(its floored body features against the clean target's), and the effects row (the delay's cepstral hit and T0's vote).

    .venv/bin/python -m learn.sep_s0 s0-build                                   # the stereo mixes (zero renders)
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s0 s0-sep --options xl --device mps
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s0 s0-sep --options mega --device mps
    $TORCH_PY -m learn.sep_s0 s0-feats                                          # the model's read
    .venv/bin/python -m learn.sep_s0 s0-read                                    # the scores, per stratum and band

The pure parts (the pan law, the strata draw, the linked compressor's gain, the metrics) are unit-tested.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import time

LEDGER_ID = "separation"
SEED = 20261151
N_ITEMS = 200
STRATA = ("centred", "off-centre", "double")
CENTRED_TRACKS = ("bass", "kick", "snare", "vox", "vocal", "voc", "lead vox")
XL_OPTIONS = ("mono", "stereo", "centre2", "centre4", "centre8", "second")
MEGA_OPTIONS = ("mega",)
DERIVED = ("agree",)                       # from mono and mega, no separation of its own
ALL_OPTIONS = XL_OPTIONS + MEGA_OPTIONS + DERIVED
BASELINE = "mono"
BELOW_GUARD_GB = 26.0                      # the user's yes (2026-11-14): S1's stems may go under the render guard


def require():
    from learn import pipeline_fix as P

    d = json.loads((P.REPO / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == LEDGER_ID), None)
    if not e or "phase_s0" not in e or "phase_s1" not in e:
        raise SystemExit("the ledger's separation entry has no phase_s0/phase_s1: declare them before running")


def out_dir():
    from learn import pipeline_fix as P

    return P.out_dir().parent / "separation" / "s0"


# --- the pure parts -------------------------------------------------------------------------------------------------------

def pan(p):
    """Constant-power pan gains (L, R) for p in [-1, 1]."""
    th = (max(-1.0, min(1.0, p)) + 1) * math.pi / 4
    return math.cos(th), math.sin(th)


def draw_stratum(i, seed=SEED):
    """An item's stratum and placements, seeded by its index. -> {stratum, target: [p...], target_offset_ms,
    target_db2, others: p}."""
    rng = random.Random(f"{seed}|{i}")
    s = STRATA[rng.randrange(3)]
    side = rng.choice((-1, 1))
    if s == "centred":
        return {"stratum": s, "target": [rng.uniform(-0.15, 0.15)], "others": side * rng.uniform(0.6, 1.0)}
    if s == "off-centre":
        others = -side * rng.uniform(0.4, 1.0) if rng.random() < 0.5 else rng.uniform(-0.15, 0.15)
        return {"stratum": s, "target": [side * rng.uniform(0.4, 0.8)], "others": others}
    return {"stratum": s, "target": [rng.uniform(0.6, 1.0), -rng.uniform(0.6, 1.0)],
            "target_offset_ms": rng.uniform(12.0, 30.0), "target_db2": -rng.uniform(1.0, 3.0),
            "others": rng.uniform(-0.15, 0.15)}


def backing_pan(track, rng):
    """A backing track's pan: the rhythm section and vocals centred, the rest within +-0.5."""
    t = track.lower()
    return 0.0 if any(k in t for k in CENTRED_TRACKS) else rng.uniform(-0.5, 0.5)


def linked_gain(mid, rng, sr):
    """`song_aug.compress`'s gain curve and make-up, on the mid signal, to apply to both channels alike (a linked
    stereo compressor). -> (gain per sample, make-up dB). Consumes rng as `compress` does (ratio, then make-up)."""
    import numpy as np

    ratio = rng.uniform(2, 4)
    thr = 10 * np.log10(np.mean(mid ** 2) + 1e-12) + 3
    a_att, a_rel = np.exp(-1 / (0.010 * sr)), np.exp(-1 / (0.100 * sr))
    env = np.empty_like(mid)
    e = 0.0
    for k, v in enumerate(mid ** 2):
        a = a_att if v > e else a_rel
        e = a * e + (1 - a) * v
        env[k] = e
    db = 10 * np.log10(env + 1e-12)
    return 10 ** (np.where(db > thr, (thr - db) * (1 - 1 / ratio), 0.0) / 20), rng.uniform(0, 4)


def si_sdr(est, ref):
    import numpy as np

    est, ref = np.asarray(est, np.float64), np.asarray(ref, np.float64)
    a = np.dot(est, ref) / (np.dot(ref, ref) + 1e-12)
    t = a * ref
    return float(10 * np.log10(np.dot(t, t) / (np.dot(est - t, est - t) + 1e-12) + 1e-12))


def leak_db(est, target, others):
    """The other guitars' share of the stem against the target's, by least squares on both references (dB; lower is
    cleaner). -inf-ish when the others don't project."""
    import numpy as np

    A = np.stack([np.asarray(target, np.float64), np.asarray(others, np.float64)], 1)
    c, *_ = np.linalg.lstsq(A, np.asarray(est, np.float64), rcond=None)
    et, eo = np.sum((c[0] * A[:, 0]) ** 2), np.sum((c[1] * A[:, 1]) ** 2)
    return float(10 * np.log10((eo + 1e-12) / (et + 1e-12)))


def band_boot(diffs, bands, n=2000, seed=SEED):
    """The mean of paired differences and its 90% band-bootstrap interval."""
    import numpy as np

    d, b = np.asarray(diffs, float), np.asarray(bands)
    u = sorted(set(b))
    idx = {x: np.where(b == x)[0] for x in u}
    rng = np.random.default_rng(seed)
    m = [d[np.concatenate([idx[u[j]] for j in rng.integers(0, len(u), len(u))])].mean() for _ in range(n)]
    return {"mean": float(d.mean()), "lo90": float(np.percentile(m, 5)), "hi90": float(np.percentile(m, 95)),
            "n": int(len(d)), "bands": len(u)}


# --- the build ------------------------------------------------------------------------------------------------------------

def pick_items(its, n=N_ITEMS, seed=SEED):
    """n items, round-robin over bands in a seeded order. -> [item]."""
    rng = random.Random(seed)
    by = {}
    for it in its:
        by.setdefault(it["band"], []).append(it)
    for v in by.values():
        rng.shuffle(v)
    bands = sorted(by)
    rng.shuffle(bands)
    out = []
    while len(out) < n and any(by.values()):
        for b in bands:
            if by[b] and len(out) < n:
                out.append(by[b].pop())
    return out


def load_track(path, start_s, sr):
    """A session track's 10-s section as [n, 2] (a mono file twice), at sr."""
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    from learn import pretrain_set as PS

    info = sf.info(str(path))
    x, fsr = sf.read(str(path), dtype="float64", always_2d=True, start=int(round(start_s * info.samplerate)),
                     frames=int(round(PS.SEC_S * info.samplerate)))
    if fsr != sr:
        g = math.gcd(sr, fsr)
        x = resample_poly(x, sr // g, fsr // g, axis=0)
    n = int(PS.SEC_S * sr)
    x = np.pad(x, ((0, max(0, n - len(x))), (0, 0)))[:n]
    return x, info.channels


def cmd_build(_args):
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import fx_t0 as T0
    from learn import pretrain_set as PS
    from learn import song_aug as SA
    from learn import trusted_data as T

    require()
    sr = PS.SR
    ns = argparse.Namespace(out=None, smoke=False)
    root = CB.V.out_root(ns)
    plan = {x["i"]: x for x in CB.load_plan(ns)["examples"]}
    rend = T.rows_of(root, CB.STAGE, "render")
    ctx = CB.ctx_for(ns)
    stems = T.Stems(ctx)
    its, _ = T0.items()
    items = pick_items(its)
    d = out_dir() / "items"
    d.mkdir(parents=True, exist_ok=True)
    e1e = pathlib.Path(T0.root()) / "e1e" / "audio"
    t0 = time.time()
    for m, it in enumerate(items):
        p = d / f"{it['i']:07d}.npz"
        j = d / f"{it['i']:07d}.json"
        if p.exists() and j.exists() and "guitar_amps" in json.loads(j.read_text()):
            continue
        x, rw = plan[it["i"]], rend[it["i"]]
        y = np.asarray(G.read_flac(T.flac_path(root, CB.STAGE, it["i"], "target"), rw["target"]["scale"],
                                   rw["target"]["sha256"]), np.float64)
        oth = np.asarray(G.read_flac(T.flac_path(root, CB.STAGE, it["i"], "others"), rw["others_file"]["scale"],
                                     rw["others_file"]["sha256"]), np.float64)
        voc = x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"]
        tracks = T.backing_tracks(x, voc)
        st = np.asarray(stems.get(x["section"], tracks), np.float64)
        same, gains, _ = T.self_built_mix(y, oth, st, x)               # the recipe check, as T0x's
        if not np.allclose(same.astype(np.float32), np.load(e1e / f"{it['i']:07d}.npz")["mix"], atol=1e-5):
            raise SystemExit(f"{it['i']}: the mono rebuild differs from E1e's stored mix")
        gb, ga = gains["gb"], gains["ga"]
        n = len(y)
        lay = draw_stratum(it["i"])
        # the target, placed (a double: a second copy delayed and lowered on the other side)
        tL, tR = np.zeros(n), np.zeros(n)
        for k, pp in enumerate(lay["target"]):
            src = y
            if k == 1:
                lag = int(lay["target_offset_ms"] / 1000 * sr)
                src = np.concatenate([np.zeros(lag), y[:n - lag]]) * 10 ** (lay["target_db2"] / 20)
            gl, gr = pan(pp)
            tL, tR = tL + gl * src, tR + gr * src
        kt = 1 / pan(0.0)[0]                       # the target and the others enter the recipe unfolded: centred,
        tL, tR = tL * kt, tR * kt                  # their (L+R)/2 is the recipe's own track
        gl, gr = pan(lay["others"])
        oL, oR = gl * oth * kt, gr * oth * kt
        kb = T.pan_fold(0.0) / pan(0.0)[0]         # a mono backing track centred folds as the recipe's (= 1)
        # the backing, track by track: a stereo file keeps its image, a mono one is panned
        sec = ctx.sections[x["section"]]
        sess = pathlib.Path(ctx.inv[sec["di"]]["session_dir"])
        rng = random.Random(f"{SEED}|backing|{it['i']}")
        bL, bR, pans = np.zeros(n), np.zeros(n), {}
        guitar_amps = {a_["track"] for a_ in x.get("amp_tracks") or []}   # other active guitars, as amp tracks
        for t in tracks:
            a, ch = load_track(sess / t, sec["start_s"], sr)
            if ch == 1:
                pp = lay["others"] if t in guitar_amps else backing_pan(t, rng)   # other guitars sit with the others
                gl, gr = pan(pp)
                bL, bR = bL + a[:n, 0] * gl * kb, bR + a[:n, 0] * gr * kb
                pans[t] = round(pp, 3)
            else:
                bL, bR = bL + a[:n, 0], bR + a[:n, 1]  # (L+R)/2 is the recipe's own fold of a stereo file
                pans[t] = "stereo"
        g_b, g_a = 10 ** (gb / 20), 10 ** (ga / 20)
        L = (tL + (oL + bL) * g_b) * g_a
        R = (tR + (oR + bR) * g_b) * g_a
        refT, refO = (tL + tR) / 2 * g_a, (oL + oR) / 2 * g_b * g_a
        mastered, mrng = DS.master_draw(it["i"])
        if mastered:
            mid = (L + R) / 2
            g, mk = linked_gain(mid, mrng, sr)
            gm = 10 ** ((float(SA.lufs(mid)) + mk - float(SA.lufs(mid * g))) / 20)
            L, R, refT, refO = L * g * gm, R * g * gm, refT * g * gm, refO * g * gm
            peak = 10 ** (-1 / 20)
            L, R = np.clip(L, -peak, peak), np.clip(R, -peak, peak)
        np.savez(p, L=L.astype(np.float32), R=R.astype(np.float32), target=refT.astype(np.float32),
                 others=refO.astype(np.float32), clean=y.astype(np.float32))
        (d / f"{it['i']:07d}.json").write_text(json.dumps({"i": it["i"], "band": it["band"], "amp": it["amp"],
                                                           "cls": x["cls"], "mastered": mastered, **lay,
                                                           "backing_pans": pans, "guitar_amps": sorted(guitar_amps)}))
        if m % 20 == 0:
            print(f"s0 build {m + 1}/{len(items)}: {(time.time() - t0) / (m + 1):.1f} s an item", flush=True)
    print(f"S0 BUILD DONE: {len(items)} items", flush=True)


# --- the separations ------------------------------------------------------------------------------------------------------

def xl_stereo(sep, L, R):
    """X-LANCE on two real channels (the mean of its two outputs), as `XLanceG` does on a duplicated mono channel."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import separator_screen as SCR

    a = np.stack([SCR.to44(np.asarray(L, np.float64)), SCR.to44(np.asarray(R, np.float64))])
    return SCR.to48(DS.xl_run_chunked(sep._f, a).mean(0), len(L))


def centre(L, R, power, sr):
    from learn import product_path as PP

    keep = PP.CENTRE_POW
    try:
        PP.CENTRE_POW = power
        return PP.centre_mix(L, R, sr)
    finally:
        PP.CENTRE_POW = keep


def cmd_sep(args):
    import numpy as np

    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    require()
    sr = PS.SR
    group = XL_OPTIONS if args.options == "xl" else MEGA_OPTIONS
    sep = DS.stem_separator(T.SEP, args.device) if args.options == "xl" else DS.stem_separator("mega53", args.device,
                                                                                              setting="fast")
    items = sorted((out_dir() / "items").glob("*.npz"))
    t0 = time.time()
    for m, p in enumerate(items):
        z = np.load(p)
        L, R = np.asarray(z["L"], np.float64), np.asarray(z["R"], np.float64)
        mono = (L + R) / 2
        for o in group:
            q = out_dir() / "stems" / o / p.name
            if q.exists():
                continue
            q.parent.mkdir(parents=True, exist_ok=True)
            if o == "mono" or o == "mega":
                s = sep(mono)
            elif o == "stereo":
                s = xl_stereo(sep, L, R)
            elif o.startswith("centre"):
                s = sep(centre(L, R, int(o[6:]), sr))
            elif o == "second":
                s = sep(np.asarray(np.load(out_dir() / "stems" / "mono" / p.name)["stem"], np.float64))
            if PS.free_gb() < (BELOW_GUARD_GB if args.below_guard else T.DISK_GUARD_GB):
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB (or {BELOW_GUARD_GB} with "
                                 "--below-guard, the user's yes of 2026-11-14 for S1's stems: no renders)")
            np.savez(q, stem=np.asarray(s, np.float16)[:len(mono)])           # half size: the disk guard
        if m % 20 == 0:
            print(f"s0 sep {args.options} {m + 1}/{len(items)}: {time.time() - t0:.0f} s", flush=True)
    print(f"S0 SEP DONE: {args.options}", flush=True)


def agree(xl, mega, nfft=4096, hop=1024):
    """The agreement ensemble: per STFT bin the smaller of the two magnitudes, X-LANCE's phase."""
    import numpy as np
    from scipy.signal import istft, stft

    _, _, X = stft(np.asarray(xl, np.float64), nperseg=nfft, noverlap=nfft - hop)
    _, _, M = stft(np.asarray(mega, np.float64), nperseg=nfft, noverlap=nfft - hop)
    _, y = istft(np.minimum(np.abs(X), np.abs(M)) * np.exp(1j * np.angle(X)), nperseg=nfft, noverlap=nfft - hop)
    return np.pad(y, (0, max(0, len(xl) - len(y))))[:len(xl)]


def stem_of(option, name):
    import numpy as np

    if option == "agree":
        return agree(np.load(out_dir() / "stems" / "mono" / name)["stem"], np.load(out_dir() / "stems" / "mega" / name)["stem"])
    return np.asarray(np.load(out_dir() / "stems" / option / name)["stem"], np.float64)


# --- the model's read and the scores --------------------------------------------------------------------------------------

def cmd_feats(_args):
    import numpy as np

    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import product_path as PP

    require()
    nets, _, _ = PP._adopted()
    items = sorted((out_dir() / "items").glob("*.npz"))
    out = {}

    def f_of(s, mix, cls):
        g = DE.inference_gain_db(mix, PP.MIX_LEVEL)
        s8, _, ls, _ = DS.step4_half(s, mix, PP.HALF, g)
        s8 = np.maximum(s8, PP.FLOOR_U8)
        return PP._feats(nets, DS.model_input(s8, s8, ls, ls, PP.HALF, PP.EMBED_AMP, cls, "Dstem")[0])

    for m, p in enumerate(items):
        z = np.load(p)
        meta = json.loads(p.with_suffix(".json").read_text())
        mix = (np.asarray(z["L"], np.float64) + np.asarray(z["R"], np.float64)) / 2
        ref = f_of(np.asarray(z["target"], np.float64), mix, meta["cls"])
        row = {}
        for o in ALL_OPTIONS:
            try:
                row[o] = PP.cosine_distance(f_of(stem_of(o, p.name), mix, meta["cls"]), ref)
            except FileNotFoundError:
                pass
        out[p.stem] = row
        if m % 20 == 0:
            print(f"s0 feats {m + 1}/{len(items)}", flush=True)
    (out_dir() / "feats.json").write_text(json.dumps({"cosine_distance_to_clean": out,
                                                      "time": time.strftime("%Y-%m-%d %H:%M:%S")}))
    print("S0 FEATS DONE", flush=True)


def cmd_read(_args):
    import numpy as np

    from learn import fx_reader as FX
    from learn import fx_t0 as T0
    from learn import pretrain_set as PS

    require()
    h = PS.half_slices()["A"]
    items = sorted((out_dir() / "items").glob("*.npz"))
    feats = json.loads((out_dir() / "feats.json").read_text())["cosine_distance_to_clean"]
    t0its, _ = T0.items()
    lab = {it["i"]: T0.labels(it["settings"]) for it in t0its}
    z0 = np.load(T0.out_dir() / "features.npz")                     # T0's library: E1e's clean targets
    if [it["i"] for it in t0its] != list(z0["i"]):
        raise SystemExit("T0's items differ from its features")
    lib_amp = np.array([it["amp"] for it in t0its])
    lib_band = np.array([it["band"] for it in t0its])
    lib_don = np.array([lab[it["i"]]["don"] for it in t0its])
    jd = [T0.FEATURES.index(f) for f in T0.OWN["delay"]]

    def vote(s, amp, band):
        """T0's delay vote: the share of the 15 nearest clean targets (same amp, other bands) with a delay."""
        sel = np.where((lib_amp == amp) & (lib_band != band))[0]
        q = np.asarray(T0.features(s), np.float64)[jd][None]
        return float(lib_don[sel[T0.neighbours(z0["target"][sel][:, jd], q)[0]]].mean())
    rows = {o: [] for o in ALL_OPTIONS}
    for p in items:
        z = np.load(p)
        meta = json.loads(p.with_suffix(".json").read_text())
        T_, O_ = np.asarray(z["target"], np.float64)[h], np.asarray(z["others"], np.float64)[h]
        y = lab[meta["i"]]
        for o in ALL_OPTIONS:
            try:
                s = stem_of(o, p.name)
            except FileNotFoundError:
                continue
            r = {"i": meta["i"], "band": meta["band"], "stratum": meta["stratum"], "si_sdr": si_sdr(s[h], T_),
                 "leak_db": leak_db(s[h], T_, O_), "cos": feats.get(p.stem, {}).get(o)}
            r["delay_on"] = int(y["don"])
            r["delay_vote"] = vote(s, meta["amp"], meta["band"])
            if y["don"] == 1:
                lag, _ = FX.cep_pick(FX.cepstrum(s))
                r["delay_hit"] = float(abs(lag / 2 ** y["dtime"] - 1) <= 0.10)
            rows[o].append(r)
    base = {r["i"]: r for r in rows[BASELINE]}
    rep = {"items": len(items), "options": {}}
    for o in ALL_OPTIONS:
        if not rows[o]:
            continue
        rep["options"][o] = {}
        for strat in ("all",) + STRATA:
            rs = [r for r in rows[o] if strat == "all" or r["stratum"] == strat]
            pair = [(r, base[r["i"]]) for r in rs if r["i"] in base]
            bands = [r["band"] for r, _ in pair]
            e = {"n": len(rs), "si_sdr_median": float(np.median([r["si_sdr"] for r in rs])),
                 "leak_db_median": float(np.median([r["leak_db"] for r in rs]))}
            if o != BASELINE and pair:
                e["si_sdr_gain"] = band_boot([r["si_sdr"] - b["si_sdr"] for r, b in pair], bands)
                e["leak_change_db"] = band_boot([r["leak_db"] - b["leak_db"] for r, b in pair], bands)
                cp = [(r["cos"], b["cos"]) for r, b in pair if r["cos"] is not None and b["cos"] is not None]
                if cp:
                    e["cos_gain"] = band_boot([b_ - a_ for a_, b_ in cp],             # > 0: closer to the clean read
                                              [r["band"] for r, b in pair if r["cos"] is not None and b["cos"] is not None])
                dh = [r["delay_hit"] - b["delay_hit"] for r, b in pair if "delay_hit" in r and "delay_hit" in b]
                if dh:
                    e["delay_hit_change"] = float(np.mean(dh))
                von = [r["delay_vote"] - b["delay_vote"] for r, b in pair if r["delay_on"] == 1]
                voff = [r["delay_vote"] - b["delay_vote"] for r, b in pair if r["delay_on"] == 0]
                e["delay_vote_change"] = {"on (up is better)": float(np.mean(von)) if von else None,
                                          "off (down is better)": float(np.mean(voff)) if voff else None}
            rep["options"][o][strat] = e
    (out_dir() / "read.json").write_text(json.dumps(rep, indent=1))
    for o, v in rep["options"].items():
        a = v["all"]
        g = a.get("si_sdr_gain", {})
        print(f"{o:8s} SI-SDR {a['si_sdr_median']:+.1f} dB (gain {g.get('mean', 0):+.2f} [{g.get('lo90', 0):+.2f}, "
              f"{g.get('hi90', 0):+.2f}])  leak {a['leak_db_median']:+.1f} dB  "
              + "  ".join(f"{s}: {v[s].get('si_sdr_gain', {}).get('mean', 0):+.2f}" for s in STRATA if s in v))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("s0-build").set_defaults(fn=cmd_build)
    s = sub.add_parser("s0-sep")
    s.add_argument("--options", choices=("xl", "mega"), required=True)
    s.add_argument("--device", default="mps")
    s.add_argument("--below-guard", action="store_true", help="the user's yes: run under the 31-GB render guard")
    s.set_defaults(fn=cmd_sep)
    sub.add_parser("s0-feats").set_defaults(fn=cmd_feats)
    sub.add_parser("s0-read").set_defaults(fn=cmd_read)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
