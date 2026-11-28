"""The spectral-envelope steps' builder (`docs/scratch-envelope-plan.md`, Unit 2; ledger `preset-ladder`
`phase_scratch_envelope`, then the hash PR `phase_scratch_envelope_dry` with build.json's sha256). Zero renders.

    $MAIN -m learn.envelope_build build --shard k/3   # that slice's five guitars and per-part records, each once
    $MAIN -m learn.envelope_build build --combine     # once every part is there: build.json (written once)
    $MAIN -m learn.envelope_build build               # one process: every part, then the same combine

Per part (`part_record`), from `rederive_fit.bench_parts` (hash-checked) and the stored sound-gap build:
- **the source** `tr-di` before its finish: `note_rebuild.denoise_above(scratch_rederive._synth(..., last=True))` with
  T, on n + END_PAD_S samples (compose's own steps, as `voice_control.bank_guitar`);
- **the target** `vc-own` before its finish: the padded raw section (`voice_build.padded_raw`) times
  `voice_build.own_gain` on `scratch_readerr.played_trace(p.notes, n + pad, p.bank, T's tuning, p.ring, T's mutes)`
  with the end fade at `real_end(n, pad)`, as `voice_build.part_record` builds `vc-own`;
- both exactly n + `pad_samples()` long, or the part stops;
- **the transform** (`scratch_envelope.TRANSFORM`, amendment 1): `stft`, the band energies per unit (`unit_energy`), the
  gains (`eq_gains`: amplitude dB clamped to +-20, the 40-dB power floor per band over the part's units), `apply_gains`
  (edge bins at 0 dB), `swap` (the phase donor's zero magnitude keeps the other signal's bin), `istft` (overlap-add
  over the sum of w^2);
- **the guitars** `vt-part`, `vt-group`, `vt-win`, `vt-mag`, `vt-phase`, each through `voice_build.chain` (p.finish on
  the padded length, cut to n, -22.9 LUFS), float32;
- **the proofs** (`scratch_envelope.PROOFS`; any failure stops the shard before that part writes anything):
  `source_is_tr_di` (chain of the source is `tr-di` byte for byte, build 2's sha256), `target_is_vc_own` (chain of the
  target is the stored `vc-own` byte for byte, the sound-gap build.json's `audio_sha256`), `unity_is_source` (unity
  gains through `apply_gains` on each EQ step's units and `istft` return the source within 1e-9 of its peak),
  `swap_is_target` (the target's STFT through `swap` with its own magnitude and phase, then `istft`, returns the target
  within 1e-9);
- **the realised error** (amendment 2, `scratch_envelope.ERROR_RULE`): before the finish against the clamped intent,
  and the finished `vt-k` against the finished `vc-own`, on the cells not floored; the clamped and floored shares;
  spectral convergence for the swaps; the level change.

**Files** (PF/fs/envelope/, each written once): `dry/<guitar>/<part>.npy` (float32), `build-parts/<part>.json` and
`build.json`. Part keys hold file names only under PF; the log prints 12-hex tags only. Every command refuses unless
`scratch_envelope.require_envelope` holds (main's code and keys) and `rederive_fit`'s CODE_FILES and
`scratch_readerr.py` equal origin/main's (`voice_build.code_refusal`). Nothing here imports numpy at module level; the
transform and the proofs are tested on synthetic signals in tests/test_envelope_build.py (numpy behind `importorskip`).
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import time

from learn import note_rebuild as NR
from learn import rederive_fit as RF
from learn import scratch_envelope as E
from learn import scratch_exact as SE
from learn import scratch_search as S
from learn import scratch_voice as SV
from learn import voice_build as VB

PLAN = E.PLAN
MODULE = "learn/envelope_build.py"
SR = NR.SR
GUITAR, BUILT, STEPS, EQ_STEPS, SWAP_STEPS = E.GUITAR, E.BUILT, E.STEPS, E.EQ_STEPS, E.SWAP_STEPS
PROOFS = E.PROOFS
CHOICES = {
    "error_abs": "the realised error's median and 90th percentile are of |error| in dB; the signed median beside",
    "error_cells_swaps": "vt-mag and vt-phase are read on vt-win's cells (one frame, a band) and vt-win's floor (the "
                         "source's); their intent is the magnitude donor's band power (the target's for vt-mag, the "
                         "source's for vt-phase)",
    "unity_proof": "unity gains run through apply_gains on each EQ step's own units (part, group, win) and istft; the "
                   "proof's figure is the largest of the three ratios",
    "group_units_empty": "a group unit with no frame (a bound at or before sample 0, or two bounds inside one hop) "
                         "is dropped; the units are numbered in order (scratch_envelope.unit_ids)",
    "proof_stops_shard": "the orchestrator's call: a proof failure stops the shard (SystemExit), as voice_build does",
    "target_finished": "the finished target is chain(target): byte for byte the stored vc-own by proof 2",
    "level_align": "the implementer's call (recorded, to the orchestrator): before the gains, the target's STFT is "
                   "scaled by one factor per part, sqrt of the source's in-band power over the target's (all 20 "
                   "bands, every frame of the padded part), so the +-20 dB clamp bounds the envelope's shape and not "
                   "the two signals' arbitrary levels (on 3 real parts, unaligned, the level offset was 17-20 dB and "
                   "40-100% of vt-part's cells clamped). The finish (song_bank.measure: a re-EQ to the average guitar, "
                   "then -22.9 LUFS) and chain's -22.9 LUFS re-level every guitar, so the factor reaches a finished "
                   "guitar only through the clamp; it is recorded per part as target_align_db; proof 4 runs on the "
                   "unscaled target",
}


# --- the transform (numpy, lazily) --------------------------------------------------------------------------------------

def window(n=E.N_FFT):
    """The periodic Hann window: 0.5 - 0.5 cos(2 pi j / n), j = 0..n-1."""
    import numpy as np

    return 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / n)


def _frame_index(length):
    import numpy as np

    f = E.frame_count(length)
    return f, np.arange(f)[:, None] * E.HOP + np.arange(E.N_FFT)[None, :]


def stft(x):
    """The declared STFT (scratch_envelope.TRANSFORM["stft"]): frames 0..(L - 1) // HOP of the signal zero-extended by
    HALF at both ends (frame i centred on sample HOP i), periodic Hann, rfft. -> complex (frames, BINS)."""
    import numpy as np

    x = np.asarray(x, np.float64)
    f, idx = _frame_index(len(x))
    need = (f - 1) * E.HOP + E.N_FFT
    xp = np.zeros(need)
    xp[E.HALF:E.HALF + len(x)] = x
    return np.fft.rfft(xp[idx] * window(), axis=1)


def istft(X, length):
    """The declared inverse: irfft of each frame times the window, overlap-added at the hop, divided by the overlap-added
    w^2, cut back to 0..length-1. -> float64 of `length`."""
    import numpy as np

    X = np.asarray(X)
    f = E.frame_count(length)
    if X.shape != (f, E.BINS):
        raise ValueError("the STFT is not the declared frames and bins of this length")
    w = window()
    frames = np.fft.irfft(X, n=E.N_FFT, axis=1) * w
    need = (f - 1) * E.HOP + E.N_FFT
    y, norm = np.zeros(need), np.zeros(need)
    w2 = w * w
    for i in range(f):
        a = i * E.HOP
        y[a:a + E.N_FFT] += frames[i]
        norm[a:a + E.N_FFT] += w2
    norm = norm[E.HALF:E.HALF + length]
    if not np.all(norm > 0):
        raise ValueError("the overlap-added window is 0 inside the signal")
    return y[E.HALF:E.HALF + length] / norm


def band_matrix():
    """(numpy) The bins-by-bands indicator (edge bins in no band). -> float64 (BINS, bands)."""
    import numpy as np

    of = E.band_of_bins()
    m = np.zeros((E.BINS, len(E.band_table())))
    for j, b in enumerate(of):
        if b >= 0:
            m[j, b] = 1.0
    return m


def unit_energy(X, units):
    """E[unit, band]: |X|^2 summed over each unit's frames and each band's bins. units: one id per frame of X (the
    first len(units) frames are read when X has more). -> float64 (units, bands)."""
    import numpy as np

    u = np.asarray(units, int)
    P = np.abs(np.asarray(X)[:len(u)]) ** 2 @ band_matrix()
    out = np.zeros((int(u.max()) + 1 if len(u) else 0, P.shape[1]))
    np.add.at(out, u, P)
    return out


def eq_gains(e_src, e_tgt):
    """The declared gains per cell (amendment 1): 10 log10(E_tgt / E_src) amplitude dB clamped to +-CLAMP_DB; 0 dB where
    E_src is 0 or under its band's largest cell (over the units) times FLOOR_POWER; E_tgt = 0 with E_src > 0 gives
    -CLAMP_DB. -> (gain dB, floored mask, clamped mask)."""
    import numpy as np

    es, et = np.asarray(e_src, np.float64), np.asarray(e_tgt, np.float64)
    top = es.max(axis=0, keepdims=True) if es.size else es
    floored = (es <= 0) | (es < top * E.FLOOR_POWER)
    raw = 10 * (np.log10(np.where(et > 0, et, 1.0)) - np.log10(np.where(es > 0, es, 1.0)))   # no ratio: no overflow
    raw = np.where(es > 0, raw, 0.0)
    raw = np.where((et <= 0) & (es > 0), -np.inf, raw)
    clamped = (np.abs(raw) > E.CLAMP_DB) & ~floored
    g = np.clip(raw, -E.CLAMP_DB, E.CLAMP_DB)
    g[floored] = 0.0
    return g, floored, clamped


def apply_gains(X, units, g_db):
    """X times each frame's unit gains, the same for every bin of a band; edge bins keep 0 dB. -> complex like X."""
    import numpy as np

    of = np.asarray(E.band_of_bins())
    lin = 10 ** (np.asarray(g_db, np.float64) / 20)
    per = lin[np.asarray(units, int)][:, np.where(of >= 0, of, 0)]
    per[:, of < 0] = 1.0
    return np.asarray(X) * per


def swap(M, P):
    """M's magnitude with P's phase in every bin; where |P| is 0, M's own bin is kept (amendment 1). The phase is
    numpy.angle's (atan2), so a subnormal |P| cannot overflow."""
    import numpy as np

    M, P = np.asarray(M), np.asarray(P)
    out = M.astype(complex)
    nz = np.abs(P) > 0
    out[nz] = np.abs(M[nz]) * np.exp(1j * np.angle(P[nz]))
    return out


def level_align(e_src, e_tgt):
    """The target's one level factor in power (CHOICES["level_align"]): the source's in-band power over the target's,
    summed over the whole padded part (1.0 when either is 0)."""
    import numpy as np

    a, b = float(np.sum(e_src)), float(np.sum(e_tgt))
    return a / b if a > 0 and b > 0 else 1.0


def ratio(y, x):
    """Proofs 3 and 4's figure: max |y - x| / max |x| (inf on a length mismatch or a silent x)."""
    import numpy as np

    y, x = np.asarray(y, np.float64), np.asarray(x, np.float64)
    top = float(np.max(np.abs(x))) if len(x) else 0.0
    if y.shape != x.shape or top <= 0:
        return math.inf
    return float(np.max(np.abs(y - x))) / top


# --- the realised error (numpy) -------------------------------------------------------------------------------------------

def _stats(err):
    import numpy as np

    err = np.asarray(err, np.float64)
    if not err.size:
        return {"cells": 0, "median_abs_db": None, "p90_abs_db": None, "signed_median_db": None}
    a = np.abs(err)
    return {"cells": int(err.size), "median_abs_db": float(np.median(a)), "p90_abs_db": float(np.percentile(a, 90)),
            "signed_median_db": float(np.median(err))}


def cell_error(e_got, e_ref, mask, intent_db=None):
    """Per cell 10 log10(e_got / e_ref) less the intent (dB; None: 0), on `mask` where both powers are positive.
    -> stats dict."""
    import numpy as np

    g, r = np.asarray(e_got, np.float64), np.asarray(e_ref, np.float64)
    k = min(len(g), len(r))
    g, r, m = g[:k], r[:k], np.asarray(mask, bool)[:k]
    ok = m & (g > 0) & (r > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        d = 10 * np.log10(np.where(ok, g, 1.0) / np.where(ok, r, 1.0))
    if intent_db is not None:
        d = d - np.asarray(intent_db, np.float64)[:k]
    return _stats(d[ok])


def spectral_convergence(Y, M):
    """|| |Y| - |M| ||_F / || |M| ||_F (None when M is silent)."""
    import numpy as np

    a, b = np.abs(np.asarray(Y)), np.abs(np.asarray(M))
    den = float(np.sqrt(np.sum(b ** 2)))
    return float(np.sqrt(np.sum((a - b) ** 2))) / den if den > 0 else None


def rms_db(y, x):
    import numpy as np

    a, b = float(np.sqrt(np.mean(np.square(y)))), float(np.sqrt(np.mean(np.square(x))))
    return 20 * math.log10(a / b) if a > 0 and b > 0 else None


# --- one part's guitars (numpy) -------------------------------------------------------------------------------------------

def build_guitars(source, target, finish, n, onsets, rate=SR):
    """The five guitars of one part from the source (`tr-di` before its finish) and the target (`vc-own` before its
    finish), both n + END_PAD_S samples; the proofs' figures; the realised error. Nothing written.
    -> {"guitars": {guitar: float32}, "source_out", "target_out": float32 (chain of each), "unity_ratio",
    "swap_ratio", "units": {step: count}, "frames", "error": {guitar: {...}}, "lufs_gain_db": {guitar: dB},
    "target_align_db"}."""
    import numpy as np

    x = np.asarray(source, np.float64)
    t = np.asarray(target, np.float64)
    length = n + VB.pad_samples(rate)
    if len(x) != length or len(t) != length:
        raise SystemExit("the source or the target is not n + END_PAD_S samples: the part stops before writing")
    f32 = lambda y: np.asarray(y, np.float32)   # noqa: E731
    Xs, Xt0 = stft(x), stft(t)
    F = Xs.shape[0]
    units = {s: E.unit_ids(s, F, onsets, rate) for s in EQ_STEPS}
    align = level_align(unit_energy(Xs, units["part"]), unit_energy(Xt0, units["part"]))
    Xt = Xt0 * math.sqrt(align)                     # the level-aligned target (CHOICES["level_align"])
    src_out, _ = VB.chain(x, finish, n, rate)
    tgt_out, _ = VB.chain(t, finish, n, rate)
    unity = max(ratio(istft(apply_gains(Xs, units[s], np.zeros((max(units[s]) + 1, len(E.band_table())))), length), x)
                for s in EQ_STEPS)
    swap_r = ratio(istft(swap(Xt0, Xt0), length), t)
    Fn = E.frame_count(n)
    Xo = stft(np.asarray(f32(tgt_out), np.float64))
    win_e_src = unit_energy(Xs, units["win"])
    win_fl = eq_gains(win_e_src, unit_energy(Xt, units["win"]))[1]
    guitars, error, steps = {}, {}, {}
    for s in STEPS:
        g = GUITAR[s]
        if s in EQ_STEPS:
            es, et = unit_energy(Xs, units[s]), unit_energy(Xt, units[s])
            gain, floored, clamped = eq_gains(es, et)
            Y = apply_gains(Xs, units[s], gain)
            u, fl = units[s], floored
        else:
            Y = swap(Xt, Xs) if s == "mag" else swap(Xs, Xt)
            u, fl, gain = units["win"], win_fl, None
            es, clamped = win_e_src, np.zeros_like(win_fl)
        y = istft(Y, length)
        out, step = VB.chain(y, finish, n, rate)
        guitars[g], steps[g] = f32(out), step
        Xy = stft(y)
        ey = unit_energy(Xy, u)
        if s in EQ_STEPS:
            intent = cell_error(ey, es, ~fl, gain)
        else:
            intent = cell_error(ey, unit_energy(Xt, u) if s == "mag" else es, ~fl)
        cells = fl.size or 1
        intent.update(floored_share=float(fl.sum()) / cells, clamped_share=float(np.asarray(clamped).sum()) / cells)
        Xf = stft(np.asarray(guitars[g], np.float64))
        uf = u[:Fn]
        tgt = cell_error(unit_energy(Xf, uf), unit_energy(Xo, uf), ~fl[:max(uf) + 1] if len(uf) else fl[:0])
        rec = {"intent": intent, "target": tgt, "level_change_db": rms_db(y, x), "units": len(set(u))}
        if s in SWAP_STEPS:
            rec["spectral_convergence"] = spectral_convergence(Xy, Xt if s == "mag" else Xs)
        error[g] = rec
    return {"guitars": guitars, "source_out": f32(src_out), "target_out": f32(tgt_out), "unity_ratio": unity,
            "swap_ratio": swap_r, "units": {s: len(set(units[s])) for s in EQ_STEPS}, "frames": int(F),
            "error": error, "lufs_gain_db": steps, "target_align_db": 10 * math.log10(align)}


def proofs_of(b, x_sha, x32, own_sha):
    """(numpy) The four proofs from `build_guitars`' figures: tr-di's bytes and build 2's sha256, the stored vc-own's
    audio_sha256, the unity and swap ratios within PROOF_TOL."""
    return {"source_is_tr_di": VB.same_bytes(b["source_out"], x32) and S.npy_sha(b["source_out"]) == x_sha,
            "target_is_vc_own": bool(own_sha) and S.npy_sha(b["target_out"]) == own_sha,
            "unity_is_source": bool(b["unity_ratio"] <= E.PROOF_TOL),
            "swap_is_target": bool(b["swap_ratio"] <= E.PROOF_TOL)}


PART_FIELDS = ("plan", "part", "tag", "set", "held", "renders", "code", "proofs", "proof_ratios", "guitars", "parents",
               "units", "frames", "groups", "pad", "target_align_db", "error", "lufs_gain_db")
BUILD_PART_FIELDS = ("tag", "set", "held", "proofs", "proof_ratios", "guitars", "parents", "units", "frames", "groups",
                     "pad", "target_align_db", "error", "lufs_gain_db")


def part_record(p, dp, raw_l, pad, vb, ident, rate=SR):
    """One part: the source and the target, the four proofs (any failure stops before anything is written), the five
    guitars (each written once), the record. p: a `bench_parts` Part; dp: its draw part; raw_l, pad: `padded_raw`'s;
    vb: the sound-gap build.json's part record (vc-own's audio_sha256). -> the record (saved once)."""
    import numpy as np

    from learn import scratch_readerr as RX
    from learn import scratch_rederive as RD

    tag = SV.tag(p.key)
    length = p.n + VB.pad_samples(rate)
    raw_l = np.asarray(raw_l, np.float64)
    if len(raw_l) != length:
        raise SystemExit(f"part {tag}: the padded raw section is not n + END_PAD_S samples: the shard stops")
    v = p.T
    trace, _rep = RX.played_trace(p.notes, length, p.bank, v["tuning"], p.ring, v["mutes"], rate)
    target = raw_l * VB.own_gain(p.notes, trace, length, rate, VB.real_end(p.n, pad))
    synth, _ = RD._synth(p.notes, p.n, p.bank, p.ring, v["tuning"], v["mutes"], v["tilt"], v["levels"], p.loud, rate,
                         last=True)
    source = NR.denoise_above(synth, rate)
    if len(source) != length or len(target) != length:
        raise SystemExit(f"part {tag}: the source or the target is not n + END_PAD_S samples: the shard stops")
    onsets = VB.group_onsets(p.notes)
    b = build_guitars(source, target, p.finish, p.n, onsets, rate)
    own_sha = ((vb.get("guitars") or {}).get(E.OWN) or {}).get("audio_sha256")
    proofs = proofs_of(b, p.x_sha, np.asarray(p.X, np.float32), own_sha)
    bad = E.proof_failures(proofs)
    if bad:
        raise SystemExit(f"part {tag}: proof(s) {bad} failed (unity {b['unity_ratio']:.3g}, swap {b['swap_ratio']:.3g} "
                         f"against {E.PROOF_TOL}): the shard stops before anything is written; to the user, never "
                         "loosened")
    if E.part_path(p.key).exists():
        raise SystemExit(f"part {tag}: its record exists: never overwritten")
    guitars = {}
    for g in BUILT:
        try:
            fs = RD._write_once(E.dry_path(g, p.key), b["guitars"][g])
        except SystemExit:
            raise SystemExit(f"part {tag}: its {g} guitar exists with other samples: never overwritten") from None
        guitars[g] = {"file_sha256": fs, "audio_sha256": S.npy_sha(b["guitars"][g])}
    rec = {"plan": PLAN, "part": p.key, "tag": tag, "set": p.set, "held": dp["held"], "renders": 0, "code": ident,
           "proofs": proofs, "proof_ratios": {"unity": b["unity_ratio"], "swap": b["swap_ratio"]}, "guitars": guitars,
           "parents": {E.BANK: p.x_sha, E.OWN: own_sha}, "units": b["units"], "frames": b["frames"],
           "groups": len(onsets), "pad": dict(pad), "target_align_db": b["target_align_db"], "error": b["error"],
           "lufs_gain_db": b["lufs_gain_db"]}
    VB._save_once(E.part_path(p.key), rec)
    return rec


# --- the records (pure) -----------------------------------------------------------------------------------------------------

def combine_body(per, keys):
    """(Pure.) build.json from the per-part records over the draw's `keys`: every proof held of all, `proofs_hold`
    (every proof on every part of the 47), the code identity (every part's the same, or a refusal), the bands, the
    rules, the realised error's spans, the per-part records. No time, so a rerun is byte-identical."""
    keys = sorted(keys)
    if sorted(per) != keys:
        raise SystemExit("the part records are not the draw's parts")
    ids = {json.dumps(per[k]["code"], sort_keys=True) for k in keys}
    if len(ids) != 1:
        raise SystemExit("the parts were built from different scratch_readerr code: rebuild from one checkout")
    proofs = {p: {"held": sum(per[k]["proofs"].get(p) is True for k in keys), "of": len(keys)} for p in PROOFS}
    hold = len(keys) == E.PARTS and all(v["held"] == v["of"] for v in proofs.values())
    ratios = {r: max(per[k]["proof_ratios"][r] for k in keys) for r in ("unity", "swap")}
    parts = {k: {f: per[k][f] for f in BUILD_PART_FIELDS} for k in keys}
    return {"plan": PLAN, "ledger": f"{E.LEDGER_ID} {E.PHASE}", "renders": 0, **json.loads(next(iter(ids))),
            "rules": {"transform": E.TRANSFORM, "error": E.ERROR_RULE, "choices": CHOICES, "proof_tol": E.PROOF_TOL,
                      "bands": E.band_rows(), "edge_bins": "0-2, 767-1024"},
            "parts_n": len(keys), "proofs": proofs, "proofs_hold": hold, "proof_ratio_max": ratios,
            "error_47": E.error_summary(parts, keys), "parts": parts}


def dry_body(build, sha):
    """(Pure.) The hash PR's ledger body (`phase_scratch_envelope_dry`): counts, figures and sha256s, no part keys."""
    err = {g: {f: (v.get(f) or {}).get("median") if isinstance(v.get(f), dict) else v.get(f)
               for f in ("intent_median_abs_db", "intent_p90_abs_db", "target_median_abs_db", "target_p90_abs_db",
                         "clamped_share", "floored_share")}
           for g, v in build["error_47"].items()}
    return {"sha256": sha, "plan": PLAN, "renders": 0, "parts": build["parts_n"],
            "proofs": {p: f"{v['held']} of {v['of']}" for p, v in build["proofs"].items()},
            "proofs_hold": build["proofs_hold"], "proof_ratio_max": build["proof_ratio_max"],
            "scratch_readerr_blob_sha": build["scratch_readerr_blob_sha"],
            "played_trace_sha256": build["played_trace_sha256"], "realised_error_medians_47": err}


# --- the command -------------------------------------------------------------------------------------------------------------

def require_build():
    """Refuse unless the core's guard holds (main's code and keys, the declaration on main, the vc-own row's code) and
    bench_parts' code is main's (`voice_build.code_refusal`). -> main's `preset-ladder` entry."""
    m = E.require_envelope(*E.PHASES["build"])
    why = VB.code_refusal()
    if why:
        raise SystemExit(why)
    return m


def _draw_parts():
    draw, _ = SE.context()
    return {p["pkey"]: p for p in draw["parts"]}


def _build_parts(m, need, by):
    """Build the parts `need` (keys) from bench_parts, each saved once."""
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
    _, sd = SE.context()
    vbuild = SV._build(m)
    if vbuild.get("proofs_hold") is not True:
        raise SystemExit("the sound-gap build's proofs did not hold")
    ident = VB.code_identity()
    t0 = time.time()
    for j, p in enumerate(RF.bench_parts(m, set(need))):
        dp = by[p.key]
        prt = sd.units[(dp["set"], dp["unit"], dp["amp"])]["prt"]
        raw_l, pad = VB.padded_raw(prt["di_path"], prt["start_s"])
        rec = part_record(p, dp, raw_l, pad, vbuild["parts"][p.key], ident)
        e = rec["error"]
        print(f"part {rec['tag']} ({j + 1} of {len(need)}): proofs hold (unity {rec['proof_ratios']['unity']:.1e}, "
              f"swap {rec['proof_ratios']['swap']:.1e}); vt-win intent median "
              f"{e[GUITAR['win']]['intent']['median_abs_db']} dB; {time.time() - t0:.0f} s in all", flush=True)


def cmd_build(args):
    """build (zero renders): `--shard k/n` that slice's guitars and part records (parts already there are kept);
    `--combine` build.json once every part is there; neither: every part, then the combine."""
    m = require_build()
    from learn import note_transcribe as NT

    mode = RF.run_mode(args)
    if mode != "shard":
        NT.never_overwrite(E.build_path())
    by = _draw_parts()
    keys = sorted(by)
    if mode in ("one", "shard"):
        shard = getattr(args, "shard", None)
        mine = RF.shard_keys(keys, shard)
        need = [k for k in mine if not E.part_path(k).exists()]
        if need:
            _build_parts(m, need, by)
        if mode == "shard":
            print(f"VT BUILD SHARD {shard[0]}/{shard[1]}: {len(mine)} parts ({len(need)} new); `build --combine` once "
                  "every shard is done")
            return
    missing = [k for k in keys if not E.part_path(k).exists()]
    if missing:
        raise SystemExit(f"{len(missing)} of {len(keys)} parts have no record yet: run every shard first")
    per = {}
    for k in keys:
        r = json.loads(E.part_path(k).read_text())
        if r.get("part") != k or tuple(r) != PART_FIELDS:
            raise SystemExit(f"part {SV.tag(k)}: a malformed part record")
        for g in BUILT:
            if S.file_sha(E.dry_path(g, k)) != r["guitars"][g]["file_sha256"]:
                raise SystemExit(f"part {SV.tag(k)}: its {g} guitar changed since its record")
        per[k] = r
    out = combine_body(per, keys)
    sha = VB._save_once(E.build_path(), out)
    print(f"VT BUILD: {out['parts_n']} parts, proofs " + ", ".join(f"{p} {v['held']}/{v['of']}" for p, v in
                                                                    out["proofs"].items())
          + f" -> {'hold' if out['proofs_hold'] else 'DO NOT HOLD: to the user'}; build.json sha256 {sha}")
    print(json.dumps({E.PHASE_DRY: dry_body(out, sha)}, indent=1))


COMMANDS = {"build": cmd_build}


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--shard", type=RF.shard_arg, default=None, help=f"k/n (n <= {RF.SHARD_MAX}): this slice")
    ap.add_argument("--combine", action="store_true", help="refused until every part is there; build.json")
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
