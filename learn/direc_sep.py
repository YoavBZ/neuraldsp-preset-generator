"""Separator-robust C′ (`docs/cprime-sep-plan.md`): the residual library, its per-fold split,
and the zero-render evaluation on real stems.

    # the library (CPU, minutes; main .venv)
    .venv/bin/python -m learn.direc_sep lib
    # training: learn.direc fit ... --sep-lib ~/ndsp-presets/learn/direc-sep/lib.npz
    # the evaluation (torch interpreter; MPS when free)
    $TORCH_PY -m learn.direc_sep eval --arm sep --models '~/ndsp-presets/learn/direc-sep/models-sep-f{f}/fold{f}.pt'
    $TORCH_PY -m learn.direc_sep report

The library holds, for every usable sets 1–2 stem part and four real stems (htdemucs_6s and
BS-Roformer-SW, each from the full mix and from the instrumental), what the separator did to
that part's amp track (`reference.wav`):
- G, the least-squares transfer function per STFT bin (stem ≈ G · amp track);
- the residual r = stem − G · amp track: other guitars, bleed and separation artefacts;
- the residual-to-guitar ratio rsr = rms(r) / rms(G · amp track).
Set 3's stems are never in the library: set 3 parts are evaluation parts for every fold."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/direc-sep"
STEMS = HOME / "learn/poc/stems"
CROPS = HOME / "references/validation-crops"
SR = 48000
NFFT, HOP = 4096, 1024
KINDS = (("htdemucs_6s", "instrumental_guitar"), ("htdemucs_6s", "mix_guitar"),
         ("bs_roformer_sw", "instrumental_guitar"), ("bs_roformer_sw", "mix_guitar"))
GDB_RANGE = (-30.0, 10.0)
VAL_MIN_PARTS = 2


# --- the library -------------------------------------------------------------------------------

def separator_channel(ref, stem):
    """(G (complex, NFFT/2+1), G·ref, residual) for one amp track and its stem (same length)."""
    import numpy as np
    from scipy.signal import istft, stft

    _, _, R = stft(ref, fs=SR, nperseg=NFFT, noverlap=NFFT - HOP)
    _, _, S = stft(stem, fs=SR, nperseg=NFFT, noverlap=NFFT - HOP)
    den = (np.abs(R) ** 2).sum(1)
    G = (S * np.conj(R)).sum(1) / (den + 1e-20 * max(den.max(), 1e-30))
    _, h = istft(G[:, None] * R, fs=SR, nperseg=NFFT, noverlap=NFFT - HOP)
    h = np.asarray(h[:len(ref)], np.float64)
    if len(h) < len(ref):
        h = np.pad(h, (0, len(ref) - len(h)))
    return G, h, stem - h, den


def smoothed_gain_db(G, den, freqs):
    """|G| in dB, smoothed over a third of an octave (weighted by the amp track's power), held
    flat outside 40 Hz–16 kHz, mean-removed over 100 Hz–8 kHz and clipped to GDB_RANGE."""
    import numpy as np

    mag = np.abs(G)
    out = np.zeros_like(mag)
    f = np.maximum(freqs, 1.0)
    for k in range(len(freqs)):
        sel = (f >= f[k] * 2 ** (-1 / 6)) & (f <= f[k] * 2 ** (1 / 6))
        w = den[sel]
        out[k] = (mag[sel] * w).sum() / (w.sum() + 1e-30)
    db = 20 * np.log10(np.maximum(out, 1e-6))
    lo, hi = np.searchsorted(freqs, 40), np.searchsorted(freqs, 16000)
    db[:lo], db[hi:] = db[lo], db[hi - 1]
    band = (freqs >= 100) & (freqs <= 8000)
    db = db - db[band].mean()
    return np.clip(db, *GDB_RANGE).astype(np.float32)


def build_lib(out=OUT):
    import numpy as np

    from learn import train as TR
    from learn.confirm_run import mono

    man = json.loads((STEMS / "manifest.json").read_text())["parts"]
    fold_of, band_of = TR.k3_folds()
    freqs = np.fft.rfftfreq(NFFT, 1 / SR)
    rows, rs = [], []
    for part in sorted(p for p, v in man.items() if v.get("usable")):
        rec = json.loads((CROPS / part / "record.json").read_text())
        assert rec["split"] == "development", part
        band = band_of[part]
        assert band in fold_of and not band.lower().startswith("guitar-techs"), (part, band)
        ref = mono(CROPS / part / "reference.wav")
        for model, name in KINDS:
            stem = mono(STEMS / model / part / f"{name}.wav")
            assert len(stem) == len(ref) == 480000, part
            G, h, r, den = separator_channel(ref, stem)
            rsr = float(np.sqrt((r ** 2).mean() / max((h ** 2).mean(), 1e-30)))
            rows.append({"id": f"{part}|{model}|{name}", "part": part, "band": band, "fold": fold_of[band],
                         "model": model, "input": name, "rsr_db": round(20 * math.log10(rsr), 3),
                         "r_rms": float(np.sqrt((r ** 2).mean())),
                         "manifest_snr_db": man[part]["stems"][model][name.replace("_guitar", "").replace(
                             "instrumental", "mix_instrumental")]["snr_db"]})
            rs.append((r.astype(np.float32), smoothed_gain_db(G, den, freqs)))
            print(f"{rows[-1]['id']}: residual {rows[-1]['rsr_db']:+.1f} dB re guitar "
                  f"(scalar-gain SNR {rows[-1]['manifest_snr_db']:.1f} dB)", flush=True)
    out.mkdir(parents=True, exist_ok=True)
    np.savez(out / "lib.npz", r=np.stack([a for a, _ in rs]), gdb=np.stack([b for _, b in rs]), freqs=freqs)
    (out / "lib.json").write_text(json.dumps({"kinds": KINDS, "nfft": NFFT, "hop": HOP, "rows": rows}, indent=1))
    med = sorted(r["rsr_db"] for r in rows)[len(rows) // 2]
    print(f"{len(rows)} entries from {len(rows) // len(KINDS)} parts; median residual {med:+.1f} dB re guitar", flush=True)


def split_bands(bands, fold):
    """(train bands, validation bands) of the library for `fold`: the smallest bands first (a
    seeded order breaks ties) until they hold at least VAL_MIN_PARTS parts, so the large bands
    stay in training. `bands`: {band: parts}."""
    order = sorted(bands)
    random.Random(f"cprime-sep|{fold}").shuffle(order)
    order.sort(key=lambda b: len(bands[b]))                  # stable: the shuffle breaks ties
    val, n = [], 0
    for b in order:
        if n >= VAL_MIN_PARTS:
            break
        val.append(b)
        n += len(bands[b])
    return sorted(set(order) - set(val)), sorted(val)


def load_lib(path, fold):
    """([train entry], [validation entry]) for a network that leaves out K3 `fold`. No entry
    comes from a band in that fold (asserted)."""
    import numpy as np

    path = pathlib.Path(path)
    meta = json.loads(path.with_suffix(".json").read_text())["rows"]
    z = np.load(path)
    r, gdb, freqs = z["r"], z["gdb"], z["freqs"]
    entries = [dict(m, r=r[k], gdb=gdb[k], freqs=freqs, rsr=10 ** (m["rsr_db"] / 20))
               for k, m in enumerate(meta) if m["fold"] != fold]
    assert entries and all(e["fold"] != fold for e in entries)
    bands = {}
    for e in entries:
        bands.setdefault(e["band"], set()).add(e["part"])
    trb, vab = split_bands(bands, fold)
    tr = [e for e in entries if e["band"] in trb]
    va = [e for e in entries if e["band"] in vab]
    print(f"separator library, fold {fold}: train {len(tr)} entries / {len(trb)} bands, "
          f"validation {len(va)} entries / bands {vab}", flush=True)
    return tr, va


# --- the evaluation (zero renders) -------------------------------------------------------------

def eval_parts():
    """Step 3's 24 parts: slug -> {band, fold (song-settings folds), hint, crop, inputs}."""
    from learn import knob_ceiling as K
    from learn import song_settings as SS
    from learn.phase2_set3 import LATENCY

    fo = SS.folds()
    out = {}
    for slug, p in K.parts().items():                     # step 3's parts (clean and crunch)
        if slug == "telefunken-Honey-GTR":
            continue
        assert not p["band"].lower().startswith("guitar-techs"), slug
        inputs = {"stem": p["stem"], "ref": p["crop"] / "reference.wav"}
        bs = STEMS / "bs_roformer_sw" / slug / "instrumental_guitar.wav"
        if p["set"] == 12 and bs.exists():
            inputs["stem_bs"] = bs
        out[slug] = {"band": p["band"], "fold": fo[p["band"]], "set": p["set"],
                     "hint": p["judge_lag"] + LATENCY, "di": p["crop"] / "di.wav", "inputs": inputs}
    return out


def lsd_db(a, b, lo=80.0, hi=8000.0):
    """Spectral-envelope error (dB) of `a` against `b` (review change 2): the RMS over the
    third-octave bands in [lo, hi] of the dB difference of their long-term Welch spectra
    (nperseg 8192), after removing the mean offset. Coherence can't see a linear colouration;
    this can. Lower is better."""
    import numpy as np
    from scipy.signal import welch

    f, pa = welch(a, fs=SR, nperseg=8192)
    _, pb = welch(b, fs=SR, nperseg=8192)
    d = []
    c = lo * 2 ** (1 / 6)
    while c * 2 ** (1 / 6) <= hi:
        sel = (f >= c * 2 ** (-1 / 6)) & (f < c * 2 ** (1 / 6))
        if sel.any():
            d.append(10 * np.log10((pa[sel].mean() + 1e-30) / (pb[sel].mean() + 1e-30)))
        c *= 2 ** (1 / 3)
    d = np.asarray(d)
    return float(np.sqrt(((d - d.mean()) ** 2).mean()))


def evaluate(arm, pattern, device=None):
    """Coherence (80 Hz–1 kHz, 1–3 kHz, 3–8 kHz) and the spectral-envelope error (`lsd_db`)
    between each part's true DI and the rebuild by its own fold's network (`pattern` with {f})
    from each input. Writes eval-<arm>.json."""
    import numpy as np
    import torch

    from learn import direc as D
    from learn import song_settings as SS
    from learn.confirm_run import mono
    from learn.residual_eval import _aligned, _coherence

    dev = torch.device(device or ("mps" if torch.backends.mps.is_available() else "cpu"))
    lib_band = {m["id"]: m["band"] for m in json.loads((OUT / "lib.json").read_text())["rows"]}
    nets = {}
    rows = {}
    for slug, p in sorted(eval_parts().items()):
        f = p["fold"]
        path = SS.cprime(f) if pattern == "cprime" else pathlib.Path(pattern.format(f=f)).expanduser()
        if pattern != "cprime":
            assert (path.parent / "DONE").exists(), path
            used = json.loads((path.parent / "config.json").read_text())["sep"]
            assert p["band"] not in {lib_band[i] for i in used["train"] + used["val"]}, (slug, path)
        if f not in nets:
            nets[f] = D.load_model(path, device=dev).to(dev).eval()
        di = mono(p["di"])
        rows[slug] = {"band": p["band"], "fold": f, "set": p["set"], "net": str(path), "device": dev.type,
                      "lsd": {}}
        for k, src in p["inputs"].items():
            x = mono(src).astype(np.float32)
            rb = D.rebuild(nets[f], x, device=dev).astype(np.float64)
            a, b, lag = _aligned(rb, di, p["hint"])
            rows[slug][k] = _coherence(a, b)
            rows[slug]["lsd"][k] = lsd_db(a, b)
        print(slug, arm, {k: [round(v, 3) for v in rows[slug][k]] + [round(rows[slug]["lsd"][k], 2)]
                          for k in p["inputs"]}, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"eval-{arm}.json").write_text(json.dumps(rows, indent=1))
    return rows


def _bleed_high():
    t = json.loads((PLUGIN_ROOT / "docs/audits/bleed-2026-10-16/bleed-table.json").read_text())
    return {s for s, v in t.items() if v.get("flag") == "high"}


def _value(row, key, measure):
    """measure: an int (a coherence band), 'coh3' (the mean of the three) or 'lsd'."""
    if measure == "lsd":
        return row["lsd"].get(key)
    c = row.get(key)
    if c is None:
        return None
    return sum(c) / len(c) if measure == "coh3" else c[measure]


def contrast(a, b, key, measure=1, parts=None, key_b=None):
    """Band-weighted paired difference a − b of `measure` for input `key` (and, with `key_b`, the
    difference in differences (a − b on key) − (a − b on key_b)), with the 90% band-clustered
    interval and the leave-one-band-out range."""
    from learn import song_readout as R

    rows = []
    for s in sorted(set(a) & set(b)):
        if parts is not None and s not in parts:
            continue
        va, vb = _value(a[s], key, measure), _value(b[s], key, measure)
        if va is None or vb is None:
            continue
        d = va - vb
        if key_b is not None:
            wa, wb = _value(a[s], key_b, measure), _value(b[s], key_b, measure)
            if wa is None or wb is None:
                continue
            d -= wa - wb
        rows.append((a[s]["band"], d))
    st = R.bw_stats(rows)
    lobo = st.pop("leave_one_band_out")
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in st.items()} | {
        "lobo": [round(min(lobo), 4), round(max(lobo), 4)] if lobo else None}


def report():
    """The declared contrasts (docs/cprime-sep-plan.md, "What is reported")."""
    from learn import song_readout as R

    ev = {a: json.loads((OUT / f"eval-{a}.json").read_text())
          for a in ("cprime", "sep", "control") if (OUT / f"eval-{a}.json").exists()}
    devices = {a: sorted({r.get("device") for r in e.values()}) for a, e in ev.items()}
    assert len({tuple(d) for d in devices.values()}) == 1, devices
    base, out = ev["cprime"], {"devices": devices}
    no_high = {s for s in base if s not in _bleed_high()}

    def block(e, b):
        return {
            "stem_1_3k": contrast(e, b, "stem"),
            "stem_lsd": contrast(e, b, "stem", "lsd"),
            "stem_3band": contrast(e, b, "stem", "coh3"),
            "per_band_hz": {lab: contrast(e, b, "stem", i) for i, lab in enumerate(("80-1k", "1k-3k", "3k-8k"))},
            "stem_1_3k_no_high_bleed": contrast(e, b, "stem", parts=no_high),
            "stem_lsd_no_high_bleed": contrast(e, b, "stem", "lsd", parts=no_high),
            "stem_bs_1_3k": contrast(e, b, "stem_bs"),
            "stem_bs_lsd": contrast(e, b, "stem_bs", "lsd"),
            "ref_1_3k": contrast(e, b, "ref"),
            "ref_lsd": contrast(e, b, "ref", "lsd"),
            "stem_minus_ref_1_3k": contrast(e, b, "stem", key_b="ref"),
            "stem_minus_ref_lsd": contrast(e, b, "stem", "lsd", key_b="ref"),
            "per_fold_stem_1_3k": {f: contrast(e, b, "stem", parts={s for s in base if base[s]["fold"] == f})
                                   for f in sorted({r["fold"] for r in base.values()})},
        }

    for arm in [a for a in ("sep", "control") if a in ev]:
        out[arm] = block(ev[arm], base)
    if "sep" in ev and "control" in ev:
        out["sep_vs_control"] = block(ev["sep"], ev["control"])
    for m, name in ((1, "1_3k"), ("lsd", "lsd")):
        gap = R.bw_stats([(base[s]["band"], _value(base[s], "ref", m) - _value(base[s], "stem", m)) for s in base])
        out[f"cprime_ref_minus_stem_{name}"] = round(gap["band_weighted_mean"], 4)
        if "sep" in out and gap["band_weighted_mean"]:
            # coherence gains are positive, LSD gains negative; the share is positive when closing
            out["sep"][f"share_of_ref_gap_{name}"] = round(
                out["sep"][f"stem_{name}"]["band_weighted_mean"] / gap["band_weighted_mean"], 3)
    def level(e, k, m):
        v = R.bw_stats([(r["band"], _value(r, k, m)) for r in e.values() if _value(r, k, m) is not None])
        return None if v["band_weighted_mean"] is None else round(v["band_weighted_mean"], 4)

    out["levels"] = {a: {f"{k}_{name}": level(e, k, m) for k in ("stem", "stem_bs", "ref")
                         for m, name in ((1, "1_3k"), ("lsd", "lsd"))} for a, e in ev.items()}
    (OUT / "report.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lib")
    e = sub.add_parser("eval")
    e.add_argument("--arm", required=True, choices=("cprime", "sep", "control"))
    e.add_argument("--models", required=True, help="'cprime' or a path pattern with {f}")
    e.add_argument("--device")
    sub.add_parser("report")
    a = ap.parse_args(argv)
    if a.cmd == "lib":
        build_lib()
    elif a.cmd == "eval":
        evaluate(a.arm, a.models, a.device)
    else:
        report()


if __name__ == "__main__":
    main()
