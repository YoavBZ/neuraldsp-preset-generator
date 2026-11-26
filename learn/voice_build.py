"""The sound-gap test's builders (`docs/scratch-voice-plan.md`, Unit B; ledger `preset-ladder` `phase_scratch_voice`,
then the hash PR `phase_scratch_voice_dry` with build.json's sha256). Zero renders.

It builds on the core (`learn/scratch_voice.py`: the declared rules `WINDOWS`, `NOTCH`, `FIN_RULE`, `ENV`, the figures
`played_windows`, `cover_figures`, `unclaimed_groups`, the paths and the guard), which it imports and never redefines.
Every constant is an existing one in `note_rebuild.py` or the core.

    $MAIN -m learn.voice_build build --shard k/n   # n <= 8: that slice's dry guitars and per-part records, each once
    $MAIN -m learn.voice_build build --combine     # once every part is there: build.json (written once)
    $MAIN -m learn.voice_build build               # one process: every part, then the same combine

**Inputs.** `rederive_fit.bench_parts(m)` (hash-checked): each part's build-2 notes after the fixes, the measured true
DI, `tr-di` (X), the true-DI values T, the bank, the ring variant, the loudness option and the part's finish `p.finish`
(`song_bank.measure`, then `average_balance` with the part's others). The raw section is
`pretrain_set.section_audio` of the part's DI, float64; it must measure to the true DI exactly (`raw_is_true_di`).
The padded raw section (`padded_raw`) is that section followed by the file's real continuation past it, up to
n + END_PAD_S samples, zeros where the file ends (the counts recorded per part as `pad`).
`scratch_readerr.played_trace` (T's tuning and mutes, the padded length, as `rebuild_redo` makes `tr-di`) gives each
note's span as `synthesise_redo` plays it.

**The chain** (the orchestrator's call on amendment 1, and review B1: `vc-own`, `vc-cut` and `vc-fin` exactly as
`tr-di`'s `compose`): the padded raw section times the gate (made on the padded timeline, with `synthesise_redo`'s 10-ms
edge fade at both padded ends), `p.finish` once, cut to n, then -22.9 LUFS by `at_lufs`; `measure` is never applied
twice. All three carry the same edge fade, so N and K carry none of it; the finish-length term sits in F.
- `vc-fin`: the gate is the edge fade alone (`edge_gain`).
- `vc-own`: the played-note gate (`own_gain`): per played note a window from round((on - PRE_ATTACK_S) * SR) to its
  trace end, its first NOTE_FADE_IN_S a linear fade-in (the sample's own `prepare_sample` ramp), its last the end
  kind's linear fade (re-pluck 10 ms, mute 30 ms, release 150 ms, sample end 150 ms, cut 10 ms; `synthesise_redo`'s
  `min(dur, round(fade * SR))`); the two fades multiply inside a window as they do on a sample. Windows combine by
  MAXIMUM, never by sum. Skipped notes open no window. No per-note gain, tilt, tuning or denoise; the overall level
  step is recorded.
- `vc-cut`: the notch gate (`cut_gain`): at every onset group's first onset t, a 10-ms linear fade-out ending at
  round(t * SR) and a 2-ms linear fade-in from round((t - PRE_ATTACK_S) * SR), combined by maximum (a notch of about
  -15.6 dB at about 1.67 ms before the onset). It is made with the same window machinery: one window per stretch
  between onsets, so groups (at least CHORD_S apart) never share a notch.
- `vc-env` (beside): `tr-di` (X) times a gain (`env_db`) whose 20-ms, 5-ms-hop frame levels follow the true DI's: per
  frame the true DI's level less `tr-di`'s, in dB, clipped to +-20 dB, 0 dB where `tr-di`'s frame is under its own
  loudest less 40 dB; linear in dB between frame centres (i * hop + frame / 2), held before the first and after the
  last. Then -22.9 LUFS.

**The proofs** (`scratch_voice.PROOFS`), on every part; any failure stops the build before that part writes anything:
1. `rule_off_is_tr_di`: the gate off, the same notes, bank, ring, loudness option, finish and T rebuild `tr-di`
   (`rederive_fit.guitar`) byte for byte, its sha256 build 2's;
2. `trace_is_tr_di_report`: the trace's counts equal build 2's stored `tr-di` report (`trace_equals_report`);
3. `all_pass_is_vc_fin`: the padded gate path with one all-pass window (no fades, the edge fade on) through the window
   machinery gives the padded `vc-fin` byte for byte;
4. `vc_fin_is_avg` (re-declared by review B1): the same builder with the pad off and no edge fade (the section's n
   samples, `p.finish`, -22.9 LUFS) against the stored `PF/replay/di/avg` brought to -22.9 LUFS by `at_lufs`:
   max |difference| / max |pad-off vc-fin| <= FIN_PROOF_TOL (1e-5). A failure goes to the user; never loosened.

Beside the proofs, two checks also stop the build: `raw_is_true_di` (above) and `synth_inside_gate` (every nonzero
sample of `tr-di`'s unfinished synthesis, `synthesise_redo` with T on the padded length, lies inside a window of the
same trace; the count outside `gate > 0` is recorded beside). And `length_term` beside (review B1): the held-half RMS
ratio and `logmel_distance` between the padded and the pad-off `vc-fin`, the size of the length term inside F.

**The figures** (zero renders, per part, what `scratch_voice read` consumes): `unclaimed` (`unclaimed_groups` of the
onset groups' first onsets on the true DI's `rise_curve`), `cover` (`cover_figures` of the true DI's 20-ms levels,
`played_windows` of the trace, the part's held half) and `ends` (the trace's ends by kind, every kind of
`scratch_voice.END_KINDS` listed, "sample" included). build.json also holds `scratch_readerr.py`'s git blob sha and
`played_trace`'s source sha256 (every part's record must agree).

**Files** (PF/fs/voice/, each written once): `dry/<guitar>/<part>.npy` (float32), `build-parts/<part>.json` (one
record a part, written by its shard; the implementer's file, so shards can combine) and `build.json`. Part keys hold
file names: they appear only under PF; the log prints 12-hex tags only.

Every command refuses unless `scratch_voice.require_voice` holds (main's code and keys) and `rederive_fit`'s
CODE_FILES and `scratch_readerr.py` equal origin/main's. The pure parts and the builders on synthetic signals are
tested in tests/test_voice_build.py (numpy behind `importorskip`); nothing here imports numpy at module level.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import pathlib
import time

from learn import note_rebuild as NR
from learn import rederive_fit as RF
from learn import scratch_exact as SE
from learn import scratch_search as S
from learn import scratch_voice as SV

PLAN = SV.PLAN
MODULE = "learn/voice_build.py"
SR = NR.SR
OWN, CUT, FIN, ENV_G, AVG_MILD = SV.OWN, SV.CUT, SV.FIN, SV.ENV_G, SV.AVG_MILD
BUILT = SV.BUILT                         # vc-fin, vc-cut, vc-own, vc-env
GUITARS = BUILT + (AVG_MILD,)            # build.json's per-part guitars: the built four and the stored avg+mild
PROOFS = SV.PROOFS
CHECKS = ("raw_is_true_di", "synth_inside_gate")   # beside the proofs; each stops the build too
FIN_PROOF_TOL = SV.FIN_PROOF_TOL
READERR = "learn/scratch_readerr.py"     # the note track's: equal to main's at build time, its blob sha recorded
EXTRA_CODE = RF.CODE_FILES + (READERR,)  # bench_parts' code (rederive_fit, the rederive core's pinned files), the trace

CHOICES = {
    "window_fades": "inside one window the start fade and the end fade multiply, as they do on a synthesised sample "
                    "(prepare_sample's ramp times synthesise_redo's end fade); they overlap only on notes shorter "
                    "than both fades",
    "window_samples": "a window runs [round((on - PRE_ATTACK_S) * SR), round(trace end * SR)), the trace end being "
                      "synthesise_redo's start + dur; the fade-in is linspace(0, 1, int(NOTE_FADE_IN_S * SR)) cut to "
                      "the window, the end fade linspace(1, 0, min(dur, round(fade * SR))); a window before 0 is cut "
                      "as synthesise_redo cuts a sample",
    "padded_chain": "review B1 (binding): tr-di's compose finishes n + END_PAD_S samples ending in the edge fade and "
                    "cuts to n after; eq_to filters circularly and average_balance with zero continuation, so a finish "
                    "on exactly n samples changes the section's end (half B ends at the last sample) and wraps onto "
                    "its start. So vc-own, vc-cut and vc-fin take the raw section on the padded length (the file's "
                    "real continuation past n, zeros where the file ends, both counts recorded per part as `pad`), "
                    "the gate on the padded timeline, synthesise_redo's edge fade at both padded ends (all three "
                    "alike, so N and K carry none of it), p.finish, cut to n, -22.9 LUFS. The true DI keeps its "
                    "n-length finish, so the length term sits in F, its size recorded beside (`length_term`: the held-half RMS "
                    "ratio and logmel_distance, pad-off the reference side, between padded and pad-off vc-fin). "
                    "Proof 4 is re-declared on the same builder with the pad off and no edge fade against the stored "
                    "avg; proof 3 is the padded all-pass gate path against the padded vc-fin (edge_gain, a separate "
                    "code path from window_gain)",
    "padded_read": "the padded raw section is pretrain_set.section_audio's n samples (exactly the true DI's source) "
                   "followed by samples n..n + END_PAD_S of one longer load_mono read of the same file from the same "
                   "start (so a resampled file's continuation comes from the longer read; whether its first n "
                   "samples equal section_audio's is recorded as `pad.first_n_equal`)",
    "synth_inside_gate": "the review's non-binding check, as a stop: every nonzero sample of tr-di's unfinished "
                         "synthesis (scratch_rederive._synth with T, before the hiss removal, which spreads) lies in a "
                         "window span [start, end) of the same trace; the count of nonzero samples where gate == 0 "
                         "(a window's first sample is 0 by its ramp, a resampled sample's need not be) is recorded",
    "notch_groups": "every onset group's first onset, skipped notes' groups included (NOTCH: every one of our onset "
                    "groups); each notch the maximum of the two fades, notches never overlap (groups are at least "
                    "CHORD_S apart), made as windows between onsets",
    "notch_samples": "the fade-out ends at round(t * SR) (as a re-pluck end), the fade-in starts at "
                     "round((t - PRE_ATTACK_S) * SR) (as the next window)",
    "env_frames": "the frame levels of tr-di and the true DI by note_rebuild.frame_levels_db (960-sample frames at a "
                  "240-sample hop), the frame centre i * hop + frame / 2 (COVER's), numpy.interp over the samples",
    "gain_db": "each guitar's overall level step: 20 log10 of the RMS after at_lufs over the RMS before it; "
               "build.json's gain_db is vc-own's, lufs_gain_db every guitar's",
    "raw_is_true_di": "the raw section, measured (song_bank.measure) and rounded to float32 as note_replay.di_section "
                      "does, must equal the true DI exactly, or the build stops",
    "part_files": "one record a part under build-parts/: the shards write them, the combine reads them",
    "readerr_pinned": "scratch_readerr.py must equal origin/main's at build time (the review's non-binding fix), "
                      "beside its recorded blob sha",
}


# --- the gates (numpy, lazily) ----------------------------------------------------------------------------------------

def fade_in_samples(rate=SR):
    """NOTE_FADE_IN_S in samples, as `prepare_sample` counts it (int)."""
    return int(SV.WINDOWS["start_fade_s"] * rate)


def end_fade_samples(kind, rate=SR):
    """An end kind's fade in samples, as `synthesise_redo` counts it (round)."""
    fades = SV.WINDOWS["end_fades_s"]
    if kind not in fades:
        raise ValueError(f"unknown end kind {kind!r}")
    return int(round(fades[kind] * rate))


def edge_samples(length, rate=SR):
    """`synthesise_redo`'s edge fade on a window of `length` samples."""
    return min(length // 2, int(SV.WINDOWS["edge_fade_s"] * rate))


def own_windows(notes, trace, rate=SR):
    """(Pure.) vc-own's windows from the notes and their `played_trace` records, in order: per played note
    (start, end, fade-in, end fade) in samples; skipped notes open none."""
    if len(notes) != len(trace):
        raise ValueError("the notes and the trace differ in length")
    out = []
    for n, t in zip(notes, trace):
        if not t.get("played"):
            continue
        a = int(round((n["on"] - SV.WINDOWS["lead_s"]) * rate))
        b = int(round(t["end"] * rate))
        out.append((a, b, fade_in_samples(rate), end_fade_samples(t["end_kind"], rate)))
    return out


def cut_windows(onsets, length, rate=SR):
    """(Pure.) vc-cut's notches as windows between onsets: before the first onset a window ending there with the
    10-ms fade-out; between onsets one opening 2 ms before an onset (the 2-ms fade-in) and ending at the next with the
    fade-out; after the last one to `length` with no end fade. No onsets: one all-pass window."""
    fo = int(round(SV.NOTCH["fade_out_s"] * rate))
    fi = int(SV.NOTCH["fade_in_s"] * rate)
    ts = sorted(onsets)
    if not ts:
        return [(0, length, 0, 0)]
    ends = [int(round(t * rate)) for t in ts]
    starts = [int(round((t - SV.WINDOWS["lead_s"]) * rate)) for t in ts]
    out = [(min(0, ends[0] - fo), ends[0], 0, fo)]
    for k in range(len(ts)):
        last = k + 1 == len(ts)
        out.append((starts[k], length if last else ends[k + 1], fi, 0 if last else fo))
    return out


def window_gain(windows, length, edge=0):
    """The gate on `length` samples: each window (start, end, fade-in, end fade) an envelope of ones with its fade-in
    (linspace(0, 1, fade-in) cut to the window) times its end fade (linspace(1, 0, min(dur, end fade))) over its last
    samples, cut at 0 and `length`; windows combine by maximum, never by sum; then `edge` samples of linear fade at
    both ends (`synthesise_redo`'s edge fade; 0: none). -> float64 array."""
    import numpy as np

    g = np.zeros(length)
    for a, b, fi, fo in windows:
        dur = b - a
        if dur <= 0:
            continue
        env = np.ones(dur)
        if fi:
            k = min(dur, fi)
            env[:k] = np.linspace(0.0, 1.0, fi)[:k]
        fo = min(dur, fo)
        if fo:
            env[dur - fo:] *= np.linspace(1.0, 0.0, fo)
        s = a
        if s < 0:
            env, s = env[-s:], 0
        e = min(length, s + len(env))
        if e > s:
            np.maximum(g[s:e], env[:e - s], out=g[s:e])
    if edge:
        g[:edge] *= np.linspace(0.0, 1.0, edge)
        g[length - edge:] *= np.linspace(1.0, 0.0, edge)
    return g


def own_gain(notes, trace, length, rate=SR):
    """vc-own's gate on the padded length, with the edge fade."""
    return window_gain(own_windows(notes, trace, rate), length, edge_samples(length, rate))


def cut_gain(onsets, length, rate=SR):
    """vc-cut's gate on the padded length, with the edge fade (review B1: as vc-own's and vc-fin's)."""
    return window_gain(cut_windows(onsets, length, rate), length, edge_samples(length, rate))


def edge_gain(length, rate=SR):
    """vc-fin's gate: `synthesise_redo`'s edge fade alone on the padded length (ones with the two ramps), made apart
    from `window_gain` so proof 3 compares two code paths."""
    import numpy as np

    g = np.ones(length)
    edge = edge_samples(length, rate)
    if edge:
        g[:edge] *= np.linspace(0.0, 1.0, edge)
        g[length - edge:] *= np.linspace(1.0, 0.0, edge)
    return g


def all_pass_gain(length, rate=SR):
    """Proof 3's gate: one all-pass window (no fades) through `window_gain`, with the edge fade."""
    return window_gain([(0, length, 0, 0)], length, edge_samples(length, rate))


def span_mask(windows, length):
    """(numpy) Where any window [start, end) lies, cut at 0 and `length`."""
    import numpy as np

    m = np.zeros(length, bool)
    for a, b, _, _ in windows:
        m[max(0, a):max(0, min(length, b))] = True
    return m


def support_check(synth, windows, gate):
    """The `synth_inside_gate` check: every nonzero sample of the unfinished synthesis inside a window span; beside,
    the nonzero samples where the gate is 0. -> {"inside", "nonzero", "nonzero_outside_spans",
    "nonzero_outside_gate"}."""
    import numpy as np

    y = np.asarray(synth)
    if len(y) != len(gate):
        raise ValueError("the synthesis and the gate differ in length")
    nz = y != 0
    out_spans = int((nz & ~span_mask(windows, len(y))).sum())
    return {"inside": out_spans == 0, "nonzero": int(nz.sum()), "nonzero_outside_spans": out_spans,
            "nonzero_outside_gate": int((nz & (np.asarray(gate) == 0)).sum())}


def group_onsets(notes):
    """(Pure.) Every onset group's first onset, in seconds (`note_rebuild.onset_groups`)."""
    return [notes[g[0]]["on"] for g in NR.onset_groups(notes)]


# --- the guitars (numpy, lazily) --------------------------------------------------------------------------------------

def level_step_db(before, after):
    import numpy as np

    a, b = float(np.sqrt(np.mean(np.square(before)))), float(np.sqrt(np.mean(np.square(after))))
    return 20 * math.log10(b / a) if a > 0 and b > 0 else None


def pad_samples(rate=SR):
    """END_PAD_S in samples, as `scratch_rederive._padded` counts it."""
    return int(round(NR.END_PAD_S * rate))


def chain(x, finish, n, rate=SR):
    """`compose`'s tail after the synthesis: the finish (None: none) on all of `x`, cut to n, then -22.9 LUFS by
    `at_lufs`. -> (float64 audio, the level step in dB)."""
    import numpy as np

    x = np.asarray(x, np.float64)
    if len(x) < n:
        raise ValueError("the input is shorter than the section")
    y = finish(x) if finish is not None else x
    y = np.asarray(y, np.float64)[:n]
    out = NR.at_lufs(y, NR.ASSUMED_LUFS, rate)
    return out, level_step_db(y, out)


def through_gate(raw_l, gain, finish, n, rate=SR):
    """The gate path (review B1): the padded raw section times the gate (the same padded length, its edge fade in
    it), then `chain`. -> (float64 audio, the level step in dB)."""
    import numpy as np

    x = np.asarray(raw_l, np.float64)
    if len(gain) != len(x):
        raise ValueError("the gate is not the padded raw section's length")
    return chain(x * gain, finish, n, rate)


def pad_off(raw_n, finish, n, rate=SR):
    """Proof 4's builder: the same chain with the pad off and no edge fade, on the section's n samples."""
    if len(raw_n) != n:
        raise ValueError("the raw section is not n samples")
    return chain(raw_n, finish, n, rate)


def padded_raw(path, start_s, rate=SR):
    """The padded raw section (review B1): `pretrain_set.section_audio`'s n samples, then samples n to
    n + END_PAD_S of one longer `load_mono` read of the same file from the same start, zeros where the file ends.
    -> (float64 array of n + END_PAD_S, {"real", "zeros", "first_n_equal"})."""
    import numpy as np

    from learn import pretrain_set as PS

    sec = np.asarray(PS.section_audio(path, start_s, rate), np.float32)
    n, pad = len(sec), pad_samples(rate)
    a = start_s - PS.TRIM_S
    x = PS.load_mono(path, rate, max(0.0, a), PS.SEC_S + PS.TRIM_S + NR.END_PAD_S - max(0.0, -a))
    if a < 0:
        x = np.concatenate([np.zeros(int(round(-a * rate)), np.float32), x])
    x = np.asarray(x, np.float32)
    real = max(0, min(len(x), n + pad) - n)
    tail = np.zeros(pad, np.float32)
    tail[:real] = x[n:n + real]
    first = len(x) >= n and x[:n].tobytes() == sec.tobytes()
    return (np.asarray(np.concatenate([sec, tail]), np.float64),
            {"real": int(real), "zeros": int(pad - real), "first_n_equal": bool(first)})


def length_term(padded, off, held, rate=SR):
    """Review B1's size figure beside: the padded against the pad-off vc-fin, on the part's held half (HALVES on the
    trimmed timeline) and whole: the RMS ratio (padded over pad-off) and `logmel_distance` (pad-off the reference
    side). -> dict."""
    import numpy as np

    a, b = SV.HALVES[held]
    lo, hi = int(round((a + SV.TRIM_S) * rate)), int(round((b + SV.TRIM_S) * rate))
    p, o = np.asarray(padded, np.float64), np.asarray(off, np.float64)
    hi = min(hi, len(p), len(o))
    ok = hi - lo >= 2048                     # at least one of logmel_distance's 2,048-sample frames
    rp = float(np.sqrt(np.mean(p[lo:hi] ** 2))) if ok else 0.0
    ro = float(np.sqrt(np.mean(o[lo:hi] ** 2))) if ok else 0.0
    ratio = rp / ro if ro > 0 else None
    return {"held": held, "held_rms_ratio": ratio,
            "held_rms_db": 20 * math.log10(ratio) if ratio else None,
            "logmel_held": NR.logmel_distance(o[lo:hi], p[lo:hi], rate) if ok else None,
            "logmel_whole": NR.logmel_distance(o, p, rate), "reference": "pad-off vc-fin"}


def env_db(tr, di, rate=SR):
    """vc-env's gain in dB per sample of `tr` (ENV), and its report. -> (float64 array, dict)."""
    import numpy as np

    frame, hop = int(round(SV.ENV["frame_s"] * rate)), int(round(SV.ENV["hop_s"] * rate))
    clamp, floor = SV.ENV["clamp_db"], SV.ENV["floor_db"]
    lt = NR.frame_levels_db(tr, frame, hop)
    ld = NR.frame_levels_db(di, frame, hop)
    k = min(len(lt), len(ld))
    if k == 0:
        return np.zeros(len(tr)), {"frames": 0, "floored": 0, "clamped": 0, "max_abs_db": 0.0}
    lt, ld = lt[:k], ld[:k]
    raw = ld - lt
    g = np.clip(raw, -clamp, clamp)
    floored = lt < lt.max() - floor
    g[floored] = 0.0
    centres = np.arange(k) * hop + frame / 2
    per = np.interp(np.arange(len(tr), dtype=np.float64), centres, g)
    return per, {"frames": int(k), "floored": int(floored.sum()),
                 "clamped": int(((np.abs(raw) > clamp) & ~floored).sum()), "max_abs_db": float(np.abs(g).max())}


def env_guitar(tr64, di64, rate=SR):
    """vc-env: tr-di times 10^(env_db / 20), then -22.9 LUFS. -> (float64 audio, level step dB, report)."""
    import numpy as np

    x = np.asarray(tr64, np.float64)
    per, rep = env_db(x, np.asarray(di64, np.float64), rate)
    y = x * 10 ** (per / 20)
    out = NR.at_lufs(y, NR.ASSUMED_LUFS, rate)
    return out, level_step_db(y, out), rep


def build_guitars(raw_l, notes, trace, finish, n, tr64, di64, rate=SR):
    """The four guitars of one part, proof 3's all-pass guitar and proof 4's pad-off vc-fin, float32. raw_l: the
    padded raw section (n + END_PAD_S samples, the length the trace was made on). -> {"guitars": {guitar: float32},
    "all_pass", "fin_pad_off": float32, "gates": {guitar: float64}, "lufs_gain_db": {...}, "env": report}."""
    import numpy as np

    f32 = lambda y: np.asarray(y, np.float32)   # noqa: E731
    length = len(raw_l)
    gates = {FIN: edge_gain(length, rate), OWN: own_gain(notes, trace, length, rate),
             CUT: cut_gain(group_onsets(notes), length, rate)}
    made = {g: through_gate(raw_l, gates[g], finish, n, rate) for g in (FIN, CUT, OWN)}
    allp, _ = through_gate(raw_l, all_pass_gain(length, rate), finish, n, rate)
    off, _ = pad_off(np.asarray(raw_l, np.float64)[:n], finish, n, rate)
    env, env_step, rep = env_guitar(tr64, di64, rate)
    return {"guitars": {FIN: f32(made[FIN][0]), CUT: f32(made[CUT][0]), OWN: f32(made[OWN][0]), ENV_G: f32(env)},
            "all_pass": f32(allp), "fin_pad_off": f32(off), "gates": gates,
            "lufs_gain_db": {FIN: made[FIN][1], CUT: made[CUT][1], OWN: made[OWN][1], ENV_G: env_step}, "env": rep}


def fin_ratio(fin32, avg64, rate=SR):
    """Proof 4's figure: max |pad-off vc-fin - at_lufs(avg)| / max |pad-off vc-fin| (inf on a length mismatch or a
    silent guitar)."""
    import numpy as np

    a = np.asarray(fin32, np.float64)
    b = NR.at_lufs(np.asarray(avg64, np.float64), NR.ASSUMED_LUFS, rate)
    top = float(np.max(np.abs(a))) if len(a) else 0.0
    if len(a) != len(b) or top <= 0 or not np.isfinite(b).all():
        return math.inf
    return float(np.max(np.abs(a - b))) / top


def same_bytes(a, b):
    import numpy as np

    a, b = np.asarray(a, np.float32), np.asarray(b, np.float32)
    return a.shape == b.shape and a.tobytes() == b.tobytes()


# --- the records (pure) -----------------------------------------------------------------------------------------------

def ends_of(rep):
    """(Pure.) The trace's ends by kind, every END_KINDS kind listed (zeros included); an unknown kind refuses."""
    ends = dict((rep or {}).get("ends") or {})
    bad = sorted(set(ends) - set(SV.END_KINDS))
    if bad:
        raise SystemExit(f"the trace has end kinds {bad} outside {SV.END_KINDS}")
    return {k: int(ends.get(k, 0)) for k in SV.END_KINDS}


def proof_failures(proofs):
    """(Pure.) The failing proofs' names, in PROOFS' order (a missing proof fails)."""
    return [k for k in PROOFS if proofs.get(k) is not True]


def git_blob_sha(data):
    """(Pure.) git's blob sha1 of `data` (bytes): what `git hash-object` prints."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def code_identity():
    """scratch_readerr.py's git blob sha and played_trace's source sha256, as this process imported them."""
    from learn import scratch_readerr as RX

    data = pathlib.Path(RX.__file__).read_bytes()
    return {"scratch_readerr_blob_sha": git_blob_sha(data),
            "played_trace_sha256": hashlib.sha256(inspect.getsource(RX.played_trace).encode()).hexdigest()}


PART_FIELDS = ("plan", "part", "tag", "set", "held", "renders", "code", "checks", "proofs", "fin_ratio", "guitars",
               "gain_db", "lufs_gain_db", "env", "pad", "length_term", "support", "unclaimed", "cover", "ends",
               "trace_report")
BUILD_PART_FIELDS = ("tag", "set", "held", "guitars", "gain_db", "lufs_gain_db", "env", "pad", "length_term",
                     "support", "unclaimed", "cover", "ends", "fin_ratio", "proofs", "checks", "trace_report")


def combine_body(per, keys):
    """(Pure.) build.json from the per-part records ({pkey: record}) over the draw's `keys`: every part's proofs, the
    counts held of all, `proofs_hold` (every proof on every part of SV.PARTS), the code identity (every part's the
    same, or a refusal), the declared rules and the per-part figures. No time, so a rerun is byte-identical."""
    keys = sorted(keys)
    if sorted(per) != keys:
        raise SystemExit("the part records are not the draw's parts")
    ids = {json.dumps(per[k]["code"], sort_keys=True) for k in keys}
    if len(ids) != 1:
        raise SystemExit("the parts were built from different scratch_readerr code: rebuild from one checkout")
    proofs = {p: {"held": sum(per[k]["proofs"].get(p) is True for k in keys), "of": len(keys)} for p in PROOFS}
    checks = {c: {"held": sum(per[k]["checks"].get(c) is True for k in keys), "of": len(keys)} for c in CHECKS}
    hold = (len(keys) == SV.PARTS and all(v["held"] == v["of"] for v in proofs.values())
            and all(v["held"] == v["of"] for v in checks.values()))
    ends = {e: sum(per[k]["ends"][e] for k in keys) for e in SV.END_KINDS}
    gains = [per[k]["gain_db"] for k in keys if per[k]["gain_db"] is not None]
    ratios = [per[k]["fin_ratio"] for k in keys]

    def span(f):
        xs = [per[k]["length_term"].get(f) for k in keys]
        xs = [x for x in xs if isinstance(x, (int, float)) and math.isfinite(x)]
        return [min(xs), max(xs)] if xs else None
    return {"plan": PLAN, "ledger": f"{SV.LEDGER_ID} {SV.PHASE}", "renders": 0, **json.loads(next(iter(ids))),
            "rules": {"windows": SV.WINDOWS, "notch": SV.NOTCH, "fin": SV.FIN_RULE, "env": SV.ENV,
                      "fin_proof_tol": FIN_PROOF_TOL, "choices": CHOICES},
            "parts_n": len(keys), "proofs": proofs, "checks": checks, "proofs_hold": hold, "ends": ends,
            "gain_db_range": [min(gains), max(gains)] if gains else None,
            "fin_ratio_max": max(ratios) if ratios else None,
            "pad": {"zero_padded_parts": sum(per[k]["pad"]["zeros"] > 0 for k in keys),
                    "first_n_unequal_parts": sum(not per[k]["pad"]["first_n_equal"] for k in keys)},
            "length_term": {"held_rms_db_range": span("held_rms_db"), "logmel_held_range": span("logmel_held"),
                            "logmel_whole_range": span("logmel_whole"), "label": "beside: the length term inside F"},
            "support": {"nonzero_outside_gate": sum(per[k]["support"]["nonzero_outside_gate"] for k in keys)},
            "parts": {k: {f: per[k][f] for f in BUILD_PART_FIELDS} for k in keys}}


def dry_body(build, sha):
    """(Pure.) The hash PR's ledger body (`phase_scratch_voice_dry`): counts and sha256s only, no part keys."""
    return {"sha256": sha, "plan": PLAN, "renders": 0, "parts": build["parts_n"],
            "proofs": {p: f"{v['held']} of {v['of']}" for p, v in build["proofs"].items()},
            "proofs_hold": build["proofs_hold"], "ends": build["ends"],
            "scratch_readerr_blob_sha": build["scratch_readerr_blob_sha"],
            "played_trace_sha256": build["played_trace_sha256"], "fin_ratio_max": build["fin_ratio_max"],
            "gain_db_range": build["gain_db_range"],
            "checks": {c: f"{v['held']} of {v['of']}" for c, v in build["checks"].items()},
            "pad": build["pad"], "length_term": build["length_term"], "support": build["support"]}


# --- paths, the guard -------------------------------------------------------------------------------------------------

def part_path(pk):
    return SV.voice_dir() / "build-parts" / f"{SE._f(pk)}.json"


def code_refusal():
    """Why bench_parts' code (rederive_fit's CODE_FILES) or scratch_readerr.py is not origin/main's, or None."""
    bad = [f for f in EXTRA_CODE if SV._git("diff", "--quiet", "origin/main", "--", f).returncode != 0]
    return f"this checkout's {bad} differ from main's: run from merged code" if bad else None


def require_build():
    """Refuse unless the core's guard holds (main's code and keys, the declaration on main) and bench_parts' code is
    main's. -> main's `preset-ladder` entry."""
    m = SV.require_voice()
    why = code_refusal()
    if why:
        raise SystemExit(why)
    return m


def _save_once(path, obj):
    from learn import note_transcribe as NT
    from learn import pipeline_fix as P

    NT.never_overwrite(path)
    P.save(path, obj)
    return S.file_sha(path)


# --- one part (data) --------------------------------------------------------------------------------------------------

def part_record(p, dp, raw_l, pad, avg64, am_path, am_file_sha, stored_rep, ident, rate=SR):
    """One part: the checks, the four proofs, the guitars (written once only when every check and proof holds), the
    figures. p: a `bench_parts` Part; dp: its draw part (held half, set); raw_l, pad: `padded_raw`'s padded raw
    section and its counts; avg64: the stored avg DI; am_path, am_file_sha: avg+mild's file and blur.json's sha256
    of it. -> the record (saved once)."""
    import numpy as np

    from learn import scratch_readerr as RX
    from learn import scratch_rederive as RD
    from learn import song_bank as SB

    tag = SV.tag(p.key)
    length = p.n + pad_samples(rate)
    raw_l = np.asarray(raw_l, np.float64)
    if len(raw_l) != length:
        raise SystemExit(f"part {tag}: the padded raw section is not n + END_PAD_S samples")
    if not same_bytes(np.asarray(np.asarray(SB.measure(raw_l[:p.n]), np.float32), np.float64), p.di):
        raise SystemExit(f"part {tag}: the raw section does not measure to the true DI: to the user")
    trace, rep = RX.played_trace(p.notes, length, p.bank, p.T["tuning"], p.ring, p.T["mutes"], rate)
    off = RF.guitar(p, p.T)                     # the gate off: rederive_fit's compose of T, float32
    proofs = {"rule_off_is_tr_di": same_bytes(off, p.X) and S.npy_sha(off) == p.x_sha,
              "trace_is_tr_di_report": RX.trace_equals_report(rep, stored_rep)}
    b = build_guitars(raw_l, p.notes, trace, p.finish, p.n, p.X, p.di, rate)
    g = b["guitars"]
    proofs["all_pass_is_vc_fin"] = same_bytes(b["all_pass"], g[FIN])
    ratio = fin_ratio(b["fin_pad_off"], avg64, rate)
    proofs["vc_fin_is_avg"] = bool(ratio <= FIN_PROOF_TOL)
    bad = proof_failures(proofs)
    if bad:
        raise SystemExit(f"part {tag}: proof(s) {bad} failed (pad-off vc-fin ratio {ratio:.3g} against "
                         f"{FIN_PROOF_TOL}): the build stops; to the user, never loosened")
    v = p.T
    synth, _ = RD._synth(p.notes, p.n, p.bank, p.ring, v["tuning"], v["mutes"], v["tilt"], v["levels"], p.loud, rate,
                         last=True)             # tr-di's unfinished synthesis (before the hiss removal)
    support = support_check(synth, own_windows(p.notes, trace, rate), b["gates"][OWN])
    if not support["inside"]:
        raise SystemExit(f"part {tag}: {support['nonzero_outside_spans']} nonzero samples of tr-di's synthesis lie "
                         "outside the trace's windows: the build stops; to the user")
    if S.file_sha(am_path) != am_file_sha:
        raise SystemExit(f"part {tag}: avg+mild is not the guitar blur.json recorded")
    lterm = length_term(g[FIN], b["fin_pad_off"], dp["held"], rate)
    onsets = group_onsets(p.notes)                 # the figures first: nothing is written before they are made
    rise, hop = NR.rise_curve(p.di, rate)
    unclaimed = SV.unclaimed_groups(onsets, rise.tolist(), hop, rate)
    levels = NR.frame_levels_db(p.di, SV.COVER["frame"], SV.COVER["hop"]).tolist()
    windows, skipped = SV.played_windows(p.notes, trace, p.n, rate)
    cover = SV.cover_figures(levels, windows, skipped, dp["held"], rate=rate)
    ends = ends_of(rep)
    if part_path(p.key).exists():
        raise SystemExit(f"part {tag}: its record exists: never overwritten")
    guitars = {}
    for name in BUILT:
        try:
            fs = RD._write_once(SV.dry_path(name, p.key), g[name])
        except SystemExit:
            raise SystemExit(f"part {tag}: its {name} guitar exists with other samples: never overwritten") from None
        guitars[name] = {"file_sha256": fs, "audio_sha256": S.npy_sha(g[name])}
    guitars[AVG_MILD] = {"file_sha256": am_file_sha, "audio_sha256": S.npy_sha(np.load(am_path))}
    rec = {"plan": PLAN, "part": p.key, "tag": tag, "set": p.set, "held": dp["held"], "renders": 0, "code": ident,
           "checks": {"raw_is_true_di": True, "synth_inside_gate": True}, "proofs": proofs, "fin_ratio": ratio,
           "guitars": guitars, "gain_db": b["lufs_gain_db"][OWN], "lufs_gain_db": b["lufs_gain_db"], "env": b["env"],
           "pad": dict(pad), "length_term": lterm, "support": support,
           "unclaimed": unclaimed, "cover": cover, "ends": ends, "trace_report": rep}
    _save_once(part_path(p.key), rec)
    return rec


# --- the command ------------------------------------------------------------------------------------------------------

def _draw_parts():
    draw, _ = SE.context()
    return {p["pkey"]: p for p in draw["parts"]}


def _build_parts(m, need, by):
    """Build the parts `need` (keys) from bench_parts, each saved once."""
    import numpy as np

    from learn import note_replay as R
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
    draw, sd = SE.context()
    blur = json.loads((R.replay_dir() / "blur.json").read_text())
    if blur["draw_sha256"] != draw["replay_draw_sha256"]:
        raise SystemExit("blur.json was made from another replay draw")
    rby = {p["pkey"]: p for p in R.require_draw()["parts"]}
    b2 = SE.bank_build(m)
    ident = code_identity()
    t0 = time.time()
    for j, p in enumerate(RF.bench_parts(m, set(need))):
        dp = by[p.key]
        prt = sd.units[(dp["set"], dp["unit"], dp["amp"])]["prt"]
        raw_l, pad = padded_raw(prt["di_path"], prt["start_s"])
        di32 = np.asarray(p.di, np.float32)
        avg64 = np.asarray(R.load_dry("avg", rby[p.key], di32, blur), np.float64)
        rec = part_record(p, dp, raw_l, pad, avg64, R.blur_path(AVG_MILD, p.key),
                          blur["parts"][p.key]["sha256"][AVG_MILD], b2["parts"][p.key]["arms"][SE.BANK_ARM]["report"],
                          ident)
        gdb = "none" if rec["gain_db"] is None else f"{rec['gain_db']:+.3f} dB"
        lt = rec["length_term"]
        print(f"part {rec['tag']} ({j + 1} of {len(need)}): proofs hold, vc-own's level step {gdb}, pad-off ratio "
              f"{rec['fin_ratio']:.2e}, pad {pad['real']} real + {pad['zeros']} zeros, length term "
              f"{lt['held_rms_db']} dB / logmel {lt['logmel_held']} ({time.time() - t0:.0f} s in all)", flush=True)


def cmd_build(args):
    """build (zero renders): `--shard k/n` that slice's guitars and part records (parts already there are kept);
    `--combine` build.json once every part is there; neither: every part, then the combine."""
    m = require_build()
    from learn import note_transcribe as NT

    mode = RF.run_mode(args)
    if mode != "shard":
        NT.never_overwrite(SV.build_path())
    by = _draw_parts()
    keys = sorted(by)
    if mode in ("one", "shard"):
        shard = getattr(args, "shard", None)
        mine = RF.shard_keys(keys, shard)
        need = [k for k in mine if not part_path(k).exists()]
        if need:
            _build_parts(m, need, by)
        if mode == "shard":
            print(f"VB BUILD SHARD {shard[0]}/{shard[1]}: {len(mine)} parts ({len(need)} new); `build --combine` once "
                  "every shard is done")
            return
    missing = [k for k in keys if not part_path(k).exists()]
    if missing:
        raise SystemExit(f"{len(missing)} of {len(keys)} parts have no record yet: run every shard first")
    per = {}
    for k in keys:
        r = json.loads(part_path(k).read_text())
        if r.get("part") != k or tuple(r) != PART_FIELDS:
            raise SystemExit(f"part {SV.tag(k)}: a malformed part record")
        for g in BUILT:
            if S.file_sha(SV.dry_path(g, k)) != r["guitars"][g]["file_sha256"]:
                raise SystemExit(f"part {SV.tag(k)}: its {g} guitar changed since its record")
        per[k] = r
    out = combine_body(per, keys)
    sha = _save_once(SV.build_path(), out)
    print(f"VB BUILD: {out['parts_n']} parts, proofs " + ", ".join(f"{p} {v['held']}/{v['of']}" for p, v in
                                                                    out["proofs"].items())
          + f" -> {'hold' if out['proofs_hold'] else 'DO NOT HOLD: to the user'}; build.json sha256 {sha}")
    print(json.dumps({SV.PHASE_DRY: dry_body(out, sha)}, indent=1))


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
