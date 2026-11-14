"""The separation plan's S1 Amendment 2 (`docs/separation-plan.md`; ledger `separation` `phase_s1_a2`): the cloud
researcher's rank-1 and rank-3/4 tests (`docs/research/lead-guitar-extraction-2026-11.md`), on S0's items and on a
"split" set with independent rhythm takes on both sides.

- **xlst2:** X-LANCE on the true stereo pair, both output channels kept (S1's (a) averaged them). From it:
  - **xlst_psi:** the psi^4 * max(cos, 0) mask applied after separating, on the stem's own channels;
  - **xlst_coh:** a time-smoothed coherence x level-similarity mask (Avendano-Jot, forgetting 0.90 per frame).
- **cw:** gilliaan's CenterWide BS-RoFormer v2 'center' output, then X-LANCE.
- **keys:** X-LANCE's keys model on the mix, as a competing mask on today's guitar stem: G * |G| / (|G| + |K|).
- **lr_mbr_lead / lr_mbr_rest:** listra92's lead/rhythm Mel-Band RoFormer on the xlst2 stem: its Lead output, and
  the stem less it.
- **lr_htd_lead / lr_htd_rhythm:** Dry Paint Dealer's lead/rhythm HTDemucs on the xlst2 stem, both outputs.
- **The split set:** 60 of S0's items rebuilt with the target centred, its own other guitars hard to one side, and an
  independent other-guitar take from another item of the same band on the other side.

    .venv/bin/python -m learn.sep_s1b s1b-build-split                          # the split set (zero renders)
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s1b s1b-sep --set main --device mps --below-guard
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.sep_s1b s1b-sep --set split --device mps --below-guard
    $TORCH_PY -m learn.sep_s1b s1b-feats --set main|split                       # the model's read
    .venv/bin/python -m learn.sep_s1b s1b-read --set main|split

Every new checkpoint is hash-checked against `tools/sep-models/manifest.json` and loaded with `weights_only=True`;
its yaml must pass `yaml.safe_load` first. The pure parts (the masks, the split draw) are unit-tested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import sys
import time

from learn import sep_s0 as S0

PHASE = "phase_s1_a2"
MODELS = pathlib.Path("~/ndsp-presets/tools/sep-models").expanduser()
NFFT, HOP, LAMBDA = 4096, 1024, 0.90
N_SPLIT = 60
NEW = ("xlst2", "cw", "keys", "lr_mbr", "lr_htd", "xlst_mdxc")         # what s1b-sep writes
DERIVED = ("xlst_psi", "xlst_coh", "xlst_coh4", "keymask", "lr_mbr_lead", "lr_mbr_rest", "lr_htd_lead",
           "lr_htd_rhythm")
SPLIT_FLOOR_DB = 20.0                      # both takes within 20 dB of the target (the review)
SPLIT_ALSO = ("mono", "stereo", "centre4", "mdxc", "side")             # S1's options rerun on the split set
READ_OPTIONS = ("mono", "stereo", "centre4", "mdxc", "side", "xlst_psi", "xlst_coh", "xlst_coh4", "xlst_mdxc", "cw",
                "keymask", "lr_mbr_lead", "lr_mbr_rest", "lr_htd_lead", "lr_htd_rhythm")


def require():
    from learn import pipeline_fix as P

    d = json.loads((P.REPO / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == S0.LEDGER_ID), None)
    if not e or PHASE not in e:
        raise SystemExit(f"the ledger's separation entry has no {PHASE}: declare it before running")


def set_dir(name):
    return S0.out_dir() if name == "main" else S0.out_dir().parent / "s1b-split"


# --- the pure parts -------------------------------------------------------------------------------------------------------

def _stft(x):
    from scipy.signal import stft

    return stft(x, nperseg=NFFT, noverlap=NFFT - HOP)[2]


def _istft(Z, n):
    import numpy as np
    from scipy.signal import istft

    y = istft(Z, nperseg=NFFT, noverlap=NFFT - HOP)[1]
    return np.pad(y, (0, max(0, n - len(y))))[:n]


def psi_mask(SL, SR, power=4):
    import numpy as np

    aL, aR = np.abs(SL), np.abs(SR)
    psi = 2 * aL * aR / (aL ** 2 + aR ** 2 + 1e-12)
    cos = np.real(SL * np.conj(SR)) / (aL * aR + 1e-12)
    return psi ** power * np.maximum(cos, 0.0)


def coherence_mask(SL, SR, lam=LAMBDA):
    """Avendano-Jot: the cross- and auto-spectra smoothed over frames (forgetting lam), coherence |Phi_LR| /
    sqrt(Phi_LL Phi_RR) times the level similarity 2 Phi_LR-magnitude-free psi from the smoothed auto-spectra."""
    import numpy as np

    F, T = SL.shape
    pLR, pLL, pRR = np.zeros(F, complex), np.zeros(F), np.zeros(F)
    m = np.zeros((F, T))
    for t in range(T):
        pLR = lam * pLR + (1 - lam) * SL[:, t] * np.conj(SR[:, t])
        pLL = lam * pLL + (1 - lam) * np.abs(SL[:, t]) ** 2
        pRR = lam * pRR + (1 - lam) * np.abs(SR[:, t]) ** 2
        coh = np.abs(pLR) / np.sqrt(pLL * pRR + 1e-20)
        sim = 2 * np.sqrt(pLL * pRR) / (pLL + pRR + 1e-20)
        m[:, t] = coh * sim
    return m


def post_mask(stem2, kind):
    """A mask applied after separating, on the stem's own two channels -> the mono centre of the stem. kind: psi
    (psi^4 max(cos, 0)), coh (the smoothed similarity, psi^1) or coh4 (its 4th power, exponent-matched to psi)."""
    import numpy as np

    L, R = np.asarray(stem2[0], np.float64), np.asarray(stem2[1], np.float64)
    SL, SR = _stft(L), _stft(R)
    m = psi_mask(SL, SR) if kind == "psi" else coherence_mask(SL, SR) ** (4 if kind == "coh4" else 1)
    return _istft(m * (SL + SR) / 2, len(L))


def competing_mask(g, k):
    """Today's guitar stem under a competing keys estimate: G * |G| / (|G| + |K|)."""
    import numpy as np

    G, K = _stft(np.asarray(g, np.float64)), _stft(np.asarray(k, np.float64))
    return _istft(G * np.abs(G) / (np.abs(G) + np.abs(K) + 1e-12), len(g))


def split_partner(meta, metas, seed=S0.SEED):
    """Another item of the same band from another section, whose other guitars become the independent take. -> i or
    None."""
    rng = random.Random(f"{seed}|split-partner|{meta['i']}")
    pool = sorted(m["i"] for m in metas if m["band"] == meta["band"] and m["i"] != meta["i"]
                  and m.get("section") != meta.get("section"))
    return rng.choice(pool) if pool else None


# --- the models -----------------------------------------------------------------------------------------------------------

def _manifest_sha(rel):
    man = json.loads((MODELS / "manifest.json").read_text())
    return next(f["sha256"] for f in man["files"] if f["path"] == rel)


def _check(path, rel):
    if hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest() != _manifest_sha(rel):
        raise SystemExit(f"{rel}: hash differs from the manifest")


DEMUCS_SP = pathlib.Path("~/ndsp-presets/tools/demucs-venv/lib/python3.14/site-packages").expanduser()
DEMUCS_PKGS = ("demucs", "julius")


def _demucs_pkgs():
    """A folder holding only the demucs-venv's pure-Python demucs, openunmix and julius (links), so the msst-venv can
    build HTDemucs without the other venv's torch."""
    d = MODELS / "lead-rhythm-htdemucs" / "pkgs"
    d.mkdir(exist_ok=True)
    for k in DEMUCS_PKGS:
        if not (d / k).exists():
            (d / k).symlink_to(DEMUCS_SP / k)
    return d


def _tuple_safe_loader():
    import yaml

    class L(yaml.SafeLoader):
        pass

    L.add_constructor("tag:yaml.org,2002:python/tuple", lambda ld, node: tuple(ld.construct_sequence(node)))
    return L


_TupleSafe = None


class Msst:
    """An MSST model from tools/sep-models (hash-checked; the yaml safe-loaded first; weights_only), on 44.1-kHz
    stereo. -> {instrument: [2, n] at 48 kHz}."""

    def __init__(self, model_type, cfg_rel, ckpt_rel, device):
        import torch
        import yaml

        from learn import separator_screen as SCR

        global _TupleSafe
        _TupleSafe = _TupleSafe or _tuple_safe_loader()
        _check(MODELS / ckpt_rel, ckpt_rel)
        _check(MODELS / cfg_rel, cfg_rel)                           # the config too: a changed one changes the model
        yaml.load((MODELS / cfg_rel).read_text(), Loader=_TupleSafe)   # safe, plus MSST's !!python/tuple only
        if "wandb" not in sys.modules:                              # MSST's training-log import; never called here
            sys.modules["wandb"] = __import__("types").ModuleType("wandb")
        if model_type == "htdemucs":                                # demucs and julius from the torch venv, openunmix
            sys.path.append(str(_demucs_pkgs()))                    # (1.3.0, no deps) fetched into pkgs-pip
            sys.path.append(str(MODELS / "lead-rhythm-htdemucs" / "pkgs-ou"))   # openunmix.filtering only
        SCR.verify_msst()
        sys.path.insert(0, str(SCR.msst_root() / "repo"))
        SCR.lzma_stub()
        from utils.settings import get_model_from_config

        self.model, self.config = get_model_from_config(model_type, str(MODELS / cfg_rel))
        sd = torch.load(MODELS / ckpt_rel, map_location="cpu", weights_only=True)
        self.model.load_state_dict(sd.get("state_dict", sd) if isinstance(sd, dict) else sd)
        self.model.eval()
        self.device = torch.device(device)
        self.model = self.model.to(self.device)
        self.model_type = model_type

    def __call__(self, x2):
        import numpy as np
        import torch

        from learn import separator_screen as SCR
        from utils.model_utils import demix

        n = x2.shape[1]
        y = np.stack([SCR.to44(np.asarray(c, np.float64)) for c in x2]).astype(np.float32)
        with torch.no_grad():
            out = demix(self.config, self.model, y, self.device, self.model_type, pbar=False)
        return {k: np.stack([SCR.to48(v[c], n) for c in range(2)]) for k, v in out.items()}


class XLanceKeys:
    """X-LANCE's keys model (`key_mss.pth`), run exactly as `direct_stems.XLanceG` runs `gtr_mss.pth`."""

    def __init__(self, device):
        import os

        import torch

        from learn import direct_stems as DS
        from learn import separator_screen as SCR  # noqa: F401  (its lzma stub)

        rel = "xlance-keys/key_mss.pth"
        _check(MODELS / rel, rel)
        if tuple(int(x) for x in torch.__version__.split("+")[0].split(".")[:2]) < (2, 6):
            raise SystemExit("XLanceKeys relies on torch.load's weights_only default (torch >= 2.6)")
        for k in [k for k in sys.modules if k in ("models", "inference") or k.startswith(("models.", "inference."))]:
            del sys.modules[k]
        code = str(DS.XL_ROOT / "code")
        sys.path.insert(0, code)
        cwd = os.getcwd()
        os.chdir(code)
        try:
            from inference import load_config_and_state_dict, load_generator
            cfg, sd = load_config_and_state_dict(str(MODELS / rel), "cpu")
            self.model = load_generator(cfg, sd, device="cpu")
        finally:
            os.chdir(cwd)
            DS.xl_unload(code)
        self.device = torch.device(device)
        self.model = self.model.to(self.device)

    _f = None

    def __call__(self, x):
        import numpy as np

        from learn import direct_stems as DS
        from learn import separator_screen as SCR

        self._f = DS.XLanceG._f.__get__(self)
        y = SCR.to44(np.asarray(x, np.float64))
        return SCR.to48(DS.xl_run_chunked(self._f, np.stack([y, y])).mean(0), len(x))


# --- the split set --------------------------------------------------------------------------------------------------------

def fold(p):
    """A source's gain in the mid, (L + R) / 2, under the build's law (constant power, x sqrt 2 so centred is 1)."""
    gl, gr = S0.pan(p)
    return (gl + gr) / 2 / S0.pan(0.0)[0]


def split_ok(meta, lufs_t, lufs_o, lufs_p, floor=SPLIT_FLOOR_DB):
    """The review's fixes: no double as a source, and both takes within `floor` dB of the target."""
    return meta["stratum"] != "double" and lufs_o > lufs_t - floor and lufs_p > lufs_t - floor


def cmd_build_split(_args):
    import numpy as np

    from learn import cc_build as CB
    from learn import song_aug as SA

    require()
    src = S0.out_dir() / "items"
    metas = [json.loads(p.read_text()) for p in sorted(src.glob("*.json"))]
    plan = {x["i"]: x for x in CB.load_plan(argparse.Namespace(out=None, smoke=False))["examples"]}
    for m in metas:
        m["section"] = plan[m["i"]]["section"]
    lev = {}
    for m in metas:
        z = np.load(src / f"{m['i']:07d}.npz")
        lev[m["i"]] = (float(SA.lufs(np.asarray(z["target"], np.float64))), float(SA.lufs(np.asarray(z["others"], np.float64))))
    nodbl = [m for m in metas if m["stratum"] != "double"]
    ok = []
    for m in nodbl:
        q = split_partner(m, nodbl)
        if q is not None and split_ok(m, lev[m["i"]][0], lev[m["i"]][1], lev[q][1]):
            ok.append((m, q))
    rng = random.Random(f"{S0.SEED}|split-pick")
    pick = sorted(rng.sample(ok, min(N_SPLIT, len(ok))), key=lambda t: t[0]["i"])
    d = set_dir("split") / "items"
    d.mkdir(parents=True, exist_ok=True)
    for m, q in pick:
        p = d / f"{m['i']:07d}.npz"
        if p.exists():
            continue
        z, zo = np.load(src / f"{m['i']:07d}.npz"), np.load(src / f"{q:07d}.npz")
        rr = random.Random(f"{S0.SEED}|split-pans|{m['i']}")
        side, pt = rr.choice((-1, 1)), rr.uniform(-0.15, 0.15)
        po, pp = side * rr.uniform(0.8, 1.0), -side * rr.uniform(0.8, 1.0)
        tgt, oth = (np.asarray(z[k], np.float64) for k in ("target", "others"))
        oth2 = np.asarray(zo["others"], np.float64)
        mid0 = (np.asarray(z["L"], np.float64) + np.asarray(z["R"], np.float64)) / 2
        rest = mid0 - tgt - oth                                     # the item's built rest, centred
        k = 1 / S0.pan(0.0)[0]
        L, R = rest.copy(), rest.copy()
        for x_, p_ in ((tgt, pt), (oth, po), (oth2, pp)):
            gl, gr = S0.pan(p_)
            L, R = L + x_ * gl * k, R + x_ * gr * k
        g = 10 ** ((float(SA.lufs(mid0)) - float(SA.lufs((L + R) / 2))) / 20)   # LUFS-matched to its source
        L, R = L * g, R * g
        refs = {"target": tgt * fold(pt) * g, "others_own": oth * fold(po) * g, "others_partner": oth2 * fold(pp) * g}
        np.savez(p, L=L.astype(np.float32), R=R.astype(np.float32), clean=np.asarray(z["clean"], np.float32),
                 others=(refs["others_own"] + refs["others_partner"]).astype(np.float32),
                 **{k_: v.astype(np.float32) for k_, v in refs.items()})
        (d / f"{m['i']:07d}.json").write_text(json.dumps({**{k_: m[k_] for k_ in ("i", "band", "amp", "cls")},
                                                          "stratum": "split", "target": [pt], "pans": [po, pp],
                                                          "partner": q, "gain_db": 20 * float(np.log10(g))}))
    print(f"S1B SPLIT BUILD DONE: {len(pick)} items (of {len(ok)} eligible)", flush=True)


def leak3_db(est, target, own, partner):
    """The split's leak: both takes' share of the stem against the target's, fitted on all three references."""
    import numpy as np

    A = np.stack([np.asarray(target, np.float64), np.asarray(own, np.float64), np.asarray(partner, np.float64)], 1)
    c, *_ = np.linalg.lstsq(A, np.asarray(est, np.float64), rcond=None)
    e = [np.sum((c[j] * A[:, j]) ** 2) for j in range(3)]
    return float(10 * np.log10((e[1] + e[2] + 1e-12) / (e[0] + 1e-12)))


# --- the separations ------------------------------------------------------------------------------------------------------

def cmd_sep(args):
    import numpy as np

    from learn import direct_stems as DS
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    require()
    root = set_dir(args.set)
    items = sorted((root / "items").glob("*.npz"))
    xl = DS.stem_separator(T.SEP, args.device)
    cw = Msst("bs_roformer", "centerwide/gilliaan_bsroformer_centerwide_v2.yaml",
              "centerwide/gilliaan_bsroformer_centerwide_v2.ckpt", args.device)
    mbr = Msst("mel_band_roformer", "lead-rhythm-mbr/mbr_lead_rhythm_guitar_listra92_config.yaml",
               "lead-rhythm-mbr/mbr_lead_rhythm_guitar_listra92.ckpt", args.device)
    htd = Msst("htdemucs", "lead-rhythm-htdemucs/demucs4_lead_rhythm_guitar_drypaint_config.yaml",
               "lead-rhythm-htdemucs/demucs4_lead_rhythm_guitar_drypaint.ckpt", "cpu")   # demucs's spectro
    # moves MPS input to the CPU and MSST's HTDemucs never moves it back, so its convs fail on MPS
    keys = XLanceKeys(args.device)
    mdx = None
    t0 = time.time()
    for m_, p in enumerate(items):
        z = np.load(p)
        L, R = np.asarray(z["L"], np.float64), np.asarray(z["R"], np.float64)
        mono = (L + R) / 2

        def save(o, arr):
            q = root / "stems" / o / p.name
            q.parent.mkdir(parents=True, exist_ok=True)
            np.savez(q, stem=np.asarray(arr, np.float16))

        def have(o):
            return (root / "stems" / o / p.name).exists()

        if PS.free_gb() < (S0.BELOW_GUARD_GB if args.below_guard else T.DISK_GUARD_GB):
            raise SystemExit("DISK GUARD")
        if not have("xlst2"):
            from learn import separator_screen as SCR

            a = np.stack([SCR.to44(L), SCR.to44(R)])
            save("xlst2", np.stack([SCR.to48(c, len(L)) for c in DS.xl_run_chunked(xl._f, a)]))
        st2 = np.asarray(np.load(root / "stems" / "xlst2" / p.name)["stem"], np.float64)
        if not have("xlst_mdxc"):                                      # October's setup: separate, then centre
            if mdx is None:
                from learn import stereo_side_screen as SSS

                mdx = SSS.Centre()
            save("xlst_mdxc", mdx(st2).mean(0))
        if not have("cw"):
            save("cw", xl(cw(np.stack([L, R]))["center"].mean(0)))
        if not have("keys"):
            save("keys", keys(mono))
        if not have("lr_mbr"):
            out = mbr(st2)
            save("lr_mbr", out[next(k for k in out if k.lower() == "lead")].mean(0))
        if not have("lr_htd"):
            out = htd(st2)
            save("lr_htd", np.stack([out["lead"].mean(0), out["rhythm"].mean(0)]))
        if args.set == "split":                                         # S1's options on the split set
            for o in SPLIT_ALSO:
                if have(o):
                    continue
                if o == "mono":
                    s = xl(mono)
                elif o == "stereo":
                    s = st2.mean(0)
                elif o == "centre4":
                    s = xl(S0.centre(L, R, 4, PS.SR))
                elif o == "side":
                    s = xl(L if S0.target_side(json.loads(p.with_suffix(".json").read_text())) < 0 else R)
                else:
                    if mdx is None:
                        from learn import stereo_side_screen as SSS

                        mdx = SSS.Centre()
                    s = xl(mdx(np.stack([L, R])).mean(0))
                save(o, s)
        if m_ % 10 == 0:
            print(f"s1b sep {args.set} {m_ + 1}/{len(items)}: {time.time() - t0:.0f} s", flush=True)
    print(f"S1B SEP DONE: {args.set}", flush=True)


def stem_of(root, o, name):
    import numpy as np

    st = lambda k: np.asarray(np.load(root / "stems" / k / name)["stem"], np.float64)   # noqa: E731
    if o in ("xlst_psi", "xlst_coh", "xlst_coh4"):
        return post_mask(st("xlst2"), o[5:])
    if o == "keymask":
        return competing_mask(st("mono"), st("keys"))
    if o == "lr_mbr_lead":
        return st("lr_mbr")
    if o == "lr_mbr_rest":
        return st("xlst2").mean(0) - st("lr_mbr")
    if o in ("lr_htd_lead", "lr_htd_rhythm"):
        return st("lr_htd")[0 if o.endswith("lead") else 1]
    return st(o)


def cmd_feats(args):
    import numpy as np

    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import product_path as PP

    require()
    root = set_dir(args.set)
    nets, _, _ = PP._adopted()
    out = {}

    def f_of(s, mix, cls):
        g = DE.inference_gain_db(mix, PP.MIX_LEVEL)
        s8, _, ls, _ = DS.step4_half(s, mix, PP.HALF, g)
        s8 = np.maximum(s8, PP.FLOOR_U8)
        return PP._feats(nets, DS.model_input(s8, s8, ls, ls, PP.HALF, PP.EMBED_AMP, cls, "Dstem")[0])

    for p in sorted((root / "items").glob("*.npz")):
        z = np.load(p)
        meta = json.loads(p.with_suffix(".json").read_text())
        mix = (np.asarray(z["L"], np.float64) + np.asarray(z["R"], np.float64)) / 2
        ref = f_of(np.asarray(z["target"], np.float64), mix, meta["cls"])
        out[p.stem] = {o: PP.cosine_distance(f_of(stem_of(root, o, p.name), mix, meta["cls"]), ref)
                       for o in READ_OPTIONS if (o in DERIVED or (root / "stems" / o / p.name).exists())
                       and _has_inputs(root, o, p.name)}
    (root / "feats-s1b.json").write_text(json.dumps({"cosine_distance_to_clean": out}))
    print(f"S1B FEATS DONE: {args.set}", flush=True)


def _has_inputs(root, o, name):
    need = {"xlst_psi": ["xlst2"], "xlst_coh": ["xlst2"], "xlst_coh4": ["xlst2"], "keymask": ["mono", "keys"],
            "lr_mbr_lead": ["lr_mbr"],
            "lr_mbr_rest": ["xlst2", "lr_mbr"], "lr_htd_lead": ["lr_htd"], "lr_htd_rhythm": ["lr_htd"]}.get(o, [o])
    return all((root / "stems" / k / name).exists() for k in need)


def cmd_read(args):
    import numpy as np

    from learn import pretrain_set as PS

    require()
    root = set_dir(args.set)
    h = PS.half_slices()["A"]
    feats = json.loads((root / "feats-s1b.json").read_text())["cosine_distance_to_clean"]
    if args.set == "main":                        # S1's own feats for its options
        feats0 = json.loads((root / "feats.json").read_text())["cosine_distance_to_clean"]
        for k, v in feats0.items():
            feats.setdefault(k, {}).update({o: c for o, c in v.items() if o not in feats[k]})
    from learn import fx_reader as FX
    from learn import fx_t0 as T0

    t0its, _ = T0.items()
    lab = {it["i"]: T0.labels(it["settings"]) for it in t0its}
    z0 = np.load(T0.out_dir() / "features.npz")
    lib_amp = np.array([it["amp"] for it in t0its])
    lib_band = np.array([it["band"] for it in t0its])
    lib_don = np.array([lab[it["i"]]["don"] for it in t0its])
    jd = [T0.FEATURES.index(f) for f in T0.OWN["delay"]]

    def vote(s_, amp, band):
        sel = np.where((lib_amp == amp) & (lib_band != band))[0]
        q = np.asarray(T0.features(s_), np.float64)[jd][None]
        return float(lib_don[sel[T0.neighbours(z0["target"][sel][:, jd], q)[0]]].mean())

    rows = {o: [] for o in READ_OPTIONS}
    for p in sorted((root / "items").glob("*.npz")):
        z = np.load(p)
        meta = json.loads(p.with_suffix(".json").read_text())
        T_, O_ = np.asarray(z["target"], np.float64)[h], np.asarray(z["others"], np.float64)[h]
        for o in READ_OPTIONS:
            if not _has_inputs(root, o, p.name):
                continue
            s = (S0.stem_of(o, p.name) if (args.set == "main" and o in S0.ALL_OPTIONS) else stem_of(root, o, p.name))
            leak = (leak3_db(s[h], T_, np.asarray(z["others_own"], np.float64)[h],
                             np.asarray(z["others_partner"], np.float64)[h]) if args.set == "split"
                    else S0.leak_db(s[h], T_, O_))
            y = lab[meta["i"]]
            r = {"i": meta["i"], "band": meta["band"], "stratum": meta["stratum"], "si_sdr": S0.si_sdr(s[h], T_),
                 "leak_db": leak, "cos": feats.get(p.stem, {}).get(o), "delay_on": int(y["don"]),
                 "delay_vote": vote(s, meta["amp"], meta["band"])}
            if y["don"] == 1:
                lag, _ = FX.cep_pick(FX.cepstrum(s))
                r["delay_hit"] = float(abs(lag / 2 ** y["dtime"] - 1) <= 0.10)
            rows[o].append(r)
    base = {r["i"]: r for r in rows["mono"]}
    strata = ("all",) + (S0.STRATA if args.set == "main" else ("split",))
    rep = {"set": args.set, "options": {}}
    for o, rs_all in rows.items():
        if not rs_all:
            continue
        rep["options"][o] = {}
        for strat in strata:
            rs = [r for r in rs_all if strat == "all" or r["stratum"] == strat]
            if not rs:
                continue
            pair = [(r, base[r["i"]]) for r in rs if r["i"] in base]
            e = {"n": len(rs), "n_cos": sum(r["cos"] is not None for r in rs),
                 "si_sdr_median": float(np.median([r["si_sdr"] for r in rs])),
                 "leak_db_median": float(np.median([r["leak_db"] for r in rs]))}
            if o != "mono" and pair:
                bands = [r["band"] for r, _ in pair]
                e["si_sdr_gain"] = S0.band_boot([r["si_sdr"] - b["si_sdr"] for r, b in pair], bands)
                e["leak_change_db"] = S0.band_boot([r["leak_db"] - b["leak_db"] for r, b in pair], bands)
                cp = [(r, b) for r, b in pair if r["cos"] is not None and b["cos"] is not None]
                if len(cp) == len(pair):
                    e["cos_gain"] = S0.band_boot([b["cos"] - r["cos"] for r, b in cp], [r["band"] for r, _ in cp])
                    e["wins"] = bool(e["si_sdr_gain"]["lo90"] > 0 and e["cos_gain"]["hi90"] >= 0)
                else:
                    e["wins"] = "not read: the model's read is incomplete"
                dh = [r["delay_hit"] - b["delay_hit"] for r, b in pair if "delay_hit" in r and "delay_hit" in b]
                von = [r["delay_vote"] - b["delay_vote"] for r, b in pair if r["delay_on"] == 1]
                voff = [r["delay_vote"] - b["delay_vote"] for r, b in pair if r["delay_on"] == 0]
                e["effects"] = {"delay_hit_change": float(np.mean(dh)) if dh else None,
                                "vote_on_change (up better)": float(np.mean(von)) if von else None,
                                "vote_off_change (down better)": float(np.mean(voff)) if voff else None}
            rep["options"][o][strat] = e
    # beside, not under the rule: the ear-pick ceiling of each lead/rhythm pair (the better output per item, an oracle)
    for a_, b_ in (("lr_mbr_lead", "lr_mbr_rest"), ("lr_htd_lead", "lr_htd_rhythm")):
        ra, rb = {r["i"]: r for r in rows[a_]}, {r["i"]: r for r in rows[b_]}
        both = [(ra[i], rb[i]) for i in ra if i in rb and i in base]
        if both:
            rep.setdefault("ear_pick_ceiling (oracle, beside)", {})[a_[:6]] = S0.band_boot(
                [max(x["si_sdr"], y["si_sdr"]) - base[x["i"]]["si_sdr"] for x, y in both], [x["band"] for x, _ in both])
    # the review: wins are candidates for the ear, ranked by the SI-SDR gain's lo90; the S2/S3 trigger reads the best lo90
    cands = sorted(((o, s_, v[s_]["si_sdr_gain"]["lo90"]) for o, v in rep["options"].items() for s_ in v
                    if v[s_].get("wins") is True), key=lambda t: -t[2])
    rep["candidates_by_lo90"] = [{"option": o, "stratum": s_, "lo90": l} for o, s_, l in cands]
    rep["best_candidate_lo90"] = cands[0][2] if cands else None       # this read only; the trigger is s1b-trigger's
    (root / f"read-s1b-{args.set}.json").write_text(json.dumps(rep, indent=1))
    for o, v in rep["options"].items():
        line = "  ".join(f"{s}: {v[s].get('si_sdr_gain', {}).get('mean', 0):+.2f}" for s in strata if s in v)
        print(f"{o:14s} n {v['all']['n']} SI-SDR {v['all']['si_sdr_median']:+.1f}  gain {line}  wins "
              f"{[s for s in strata if s in v and v[s].get('wins') is True]}")


def trigger_of(reads):
    """The S2/S3 trigger by the score (the review): the best SI-SDR gain lo90 among candidates (options that win under
    the rule), over S1's read and s1b's main and split reads together. -> (best lo90 or None, fires, the candidates)."""
    cands = []
    for name, rep in reads.items():
        for o, v in rep["options"].items():
            for strat, e in v.items():
                if e.get("wins") is True:
                    cands.append({"read": name, "option": o, "stratum": strat, "lo90": e["si_sdr_gain"]["lo90"]})
    cands.sort(key=lambda c: -c["lo90"])
    best = cands[0]["lo90"] if cands else None
    return best, bool(best is None or best < 1.0), cands


def cmd_trigger(_args):
    require()
    reads = {"S1": json.loads((S0.out_dir() / "read.json").read_text()),
             "s1b main": json.loads((set_dir("main") / "read-s1b-main.json").read_text()),
             "s1b split": json.loads((set_dir("split") / "read-s1b-split.json").read_text())}
    best, fires, cands = trigger_of(reads)
    out = {"best_candidate_lo90": best, "s2_s3_trigger_by_score": fires, "candidates": cands,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    (S0.out_dir().parent / "s1-trigger.json").write_text(json.dumps(out, indent=1))
    print(f"S1 TRIGGER: best candidate lo90 {best}; S2/S3 by the score: {'yes' if fires else 'no'}; "
          f"{len(cands)} candidates: {[(c['option'], c['stratum'], round(c['lo90'], 2)) for c in cands[:6]]}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("s1b-build-split").set_defaults(fn=cmd_build_split)
    sub.add_parser("s1b-trigger").set_defaults(fn=cmd_trigger)
    s = sub.add_parser("s1b-sep")
    s.add_argument("--set", choices=("main", "split"), required=True)
    s.add_argument("--device", default="mps")
    s.add_argument("--below-guard", action="store_true")
    s.set_defaults(fn=cmd_sep)
    for name, fn in (("s1b-feats", cmd_feats), ("s1b-read", cmd_read)):
        q = sub.add_parser(name)
        q.add_argument("--set", choices=("main", "split"), required=True)
        q.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
