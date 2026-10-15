"""Arm B: the bank's mixtures, separation and features (`docs/song-settings-plan.md`, arm B).

Runs in the torch interpreter (it separates with `learn/separate.py`'s `GuitarSeparator`):

    $TORCH_PY -m learn.song_aug build --shard 0/2      # mix, master, separate, features
    $TORCH_PY -m learn.song_aug eval                    # the same features for step 3's 24 parts

Per example (deterministic from its seed), with all sources from its own fold:
- **The guitar:** the bank render, set against an other-fold-free backing at a guitar-to-backing
  level drawn from the measured development distribution (`bank/levels.json`).
- **A second guitar,** with p 0.3: another same-fold bank render, 3–9 dB down.
- **The mix** is normalised to a loudness drawn around the evaluation mixes' median
  (±3 dB, uniform).
- **Mastering** on half: an RMS compressor (ratio 2–4, 10/100 ms) with make-up gain to 0–4 dB above
  the input's loudness, a limiter to −1 dBFS and,
  with p 0.5, AAC at 128–256 kbps (`afconvert`).
- **The stem:** on the separated half, htdemucs_6s's guitar from the 10-s mixture. Otherwise the
  clean guitar at its level in the mix.
- **The features,** per half (A = 1.0–5.5 s, B = 5.5–10 s): a 2 × MELS × frames log-mel of stem
  and mix (level kept), plus the stem's and the mix's LUFS. Saved float16.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import subprocess
import sys
import tempfile

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from learn import song_bank as B  # noqa: E402

SR = 48000
N_FFT, HOP, MELS = 2048, 480, 96
FMIN, FMAX = 30.0, 16000.0
HALVES = {"A": (1.0, 5.5), "B": (5.5, 10.0)}
FEAT = B.OUT / "features"


def mel_matrix():
    import numpy as np

    def hz_to_mel(f):
        return 2595 * np.log10(1 + f / 700)

    def mel_to_hz(m):
        return 700 * (10 ** (m / 2595) - 1)

    freqs = np.fft.rfftfreq(N_FFT, 1 / SR)
    edges = mel_to_hz(np.linspace(hz_to_mel(FMIN), hz_to_mel(FMAX), MELS + 2))
    m = np.zeros((MELS, len(freqs)), np.float32)
    for b in range(MELS):
        lo, c, hi = edges[b], edges[b + 1], edges[b + 2]
        m[b] = np.clip(np.minimum((freqs - lo) / max(c - lo, 1e-9), (hi - freqs) / max(hi - c, 1e-9)), 0, None)
    return m


_MEL = None


def logmel(x):
    """[MELS, frames] dB, level kept (no loudness normalisation), floored at −120 dB."""
    import numpy as np
    from scipy.signal import stft

    global _MEL
    if _MEL is None:
        _MEL = mel_matrix()
    _, _, Z = stft(x, fs=SR, nperseg=N_FFT, noverlap=N_FFT - HOP, boundary=None, padded=False)
    p = _MEL @ (np.abs(Z) ** 2)
    return (10 * np.log10(p + 1e-12)).clip(min=-120).astype(np.float32)


def lufs(x):
    import numpy as np
    import pyloudnorm

    v = pyloudnorm.Meter(SR).integrated_loudness(x)
    return float(v) if np.isfinite(v) else -70.0


def features(stem, mix):
    """{half: (2 × MELS × frames float16, [stem LUFS, mix LUFS])} on each half alone."""
    import numpy as np

    out = {}
    for h, (a, b) in HALVES.items():
        s, m = stem[int(a * SR):int(b * SR)], mix[int(a * SR):int(b * SR)]
        out[h] = (np.stack([logmel(s), logmel(m)]).astype(np.float16), np.array([lufs(s), lufs(m)], np.float32))
    return out


def compress(x, rng):
    import numpy as np

    ratio = rng.uniform(2, 4)
    thr = 10 * np.log10(np.mean(x ** 2) + 1e-12) + 3            # about 3 dB above the mean power
    a_att, a_rel = np.exp(-1 / (0.010 * SR)), np.exp(-1 / (0.100 * SR))
    env = np.empty_like(x)
    e = 0.0
    for i, v in enumerate(x ** 2):                               # a simple RMS detector
        a = a_att if v > e else a_rel
        e = a * e + (1 - a) * v
        env[i] = e
    db = 10 * np.log10(env + 1e-12)
    gain = np.where(db > thr, (thr - db) * (1 - 1 / ratio), 0.0)
    y = x * 10 ** (gain / 20)
    # make-up gain: mastering keeps or raises loudness (0–4 dB above the input), then a hard
    # limiter at −1 dBFS
    y = y * 10 ** ((lufs(x) + rng.uniform(0, 4) - lufs(y)) / 20)
    peak = 10 ** (-1 / 20)
    return np.clip(y, -peak, peak)


def aac(x, rng, tmp):
    import soundfile as sf

    w, m, back = (pathlib.Path(tmp) / n for n in ("a.wav", "a.m4a", "b.wav"))
    sf.write(str(w), x.astype("float32"), SR)
    rate = rng.choice((128, 160, 192, 256)) * 1000
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", str(rate), str(w), str(m)], check=True,
                   capture_output=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEF32@48000", str(m), str(back)], check=True,
                   capture_output=True)
    y, _ = sf.read(str(back), dtype="float64")
    y = y.mean(axis=1) if y.ndim == 2 else y
    out = y[:len(x)] if len(y) >= len(x) else __import__("numpy").pad(y, (0, len(x) - len(y)))
    return out


def load_render(i):
    import soundfile as sf

    y, _ = sf.read(str(B.OUT / "renders" / f"{i:05d}.flac"), dtype="float64")
    peak = json.loads((B.OUT / "renders" / f"{i:05d}.json").read_text())["peak"]
    return y / 0.99 * peak


def mixture(e, by_fold, levels, eval_mix_lufs):
    """(stem-before-separation guitar, mix) for an example."""
    import numpy as np
    import soundfile as sf

    rng = random.Random(e["seed"] ^ 0x5EED)
    g = load_render(e["i"])
    n = len(g)
    back, _ = sf.read(e["backing"], dtype="float64") if e["backing"] else (np.zeros(n), SR)
    back = back.mean(axis=1) if back.ndim == 2 else back
    back = np.pad(back, (0, max(0, n - len(back))))[:n]
    g2b = rng.choice(levels)
    lg, lb = lufs(g), lufs(back)
    gain_b = 10 ** ((lg - g2b - lb) / 20) if lb > -70 else 0.0
    guitar = g.copy()
    if e["second_guitar"]:
        others = [j for j in by_fold[e["fold"]] if j != e["i"] and (B.OUT / "renders" / f"{j:05d}.flac").exists()]
        if others:
            g2 = load_render(rng.choice(others))[:n]
            g2 = np.pad(g2, (0, n - len(g2)))
            l2 = lufs(g2)
            if l2 > -70:
                guitar = guitar + g2 * 10 ** ((lg - rng.uniform(3, 9) - l2) / 20)
    mix = guitar + back * gain_b
    target = eval_mix_lufs + rng.uniform(-3, 3)
    k = 10 ** ((target - lufs(mix)) / 20)
    return g * k, mix * k, rng


def build(shard, only_unseparated=False):
    import numpy as np

    ex = json.loads((B.OUT / "examples.json").read_text())
    lv = json.loads((B.OUT / "levels.json").read_text())
    levels = list(lv["guitar_to_backing_db"].values())
    eval_mix = lv["summary"]["eval_mix_lufs_median"]
    by_fold = {}
    for e in ex:
        by_fold.setdefault(e["fold"], []).append(e["i"])
    sep = None
    FEAT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for e in ex[shard[0]::shard[1]]:
            out = FEAT / f"{e['i']:05d}.npz"
            if out.exists() or not (B.OUT / "renders" / f"{e['i']:05d}.flac").exists():
                continue
            if only_unseparated and e["separated"]:
                continue
            g, mix, rng = mixture(e, by_fold, levels, eval_mix)
            if e["mastered"]:
                mix = compress(mix, rng)
                if e["aac"]:
                    mix = aac(mix, rng, tmp)
            if e["separated"]:
                if sep is None:
                    from learn.separate import GuitarSeparator
                    sep = GuitarSeparator()
                stem = sep(mix.astype(np.float32)).astype(np.float64)
            else:
                stem = g
            f = features(stem, mix)
            np.savez(out, featA=f["A"][0], lufsA=f["A"][1], featB=f["B"][0], lufsB=f["B"][1])
            if e["i"] % 200 == 0:
                print(e["i"], flush=True)


def eval_features():
    """The same features for step 3's 24 evaluation parts: their stem and instrumental mix."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import knob_ceiling as K
    from learn import songs_check as SC

    sc = SC.parts()
    d = B.OUT.parent / "eval-features"
    d.mkdir(parents=True, exist_ok=True)
    for slug in sorted(K.parts()):
        if slug == "telefunken-Honey-GTR":
            continue
        f = features(CR.mono(sc[slug]["stem"]), B.eval_mix(slug))
        np.savez(d / f"{slug}.npz", featA=f["A"][0], lufsA=f["A"][1], featB=f["B"][0], lufsB=f["B"][1])
        print(slug, flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("build", "eval"))
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--only-unseparated", action="store_true", help="skip examples that need separation")
    a = ap.parse_args(argv)
    i, n = map(int, a.shard.split("/"))
    build((i, n), a.only_unseparated) if a.step == "build" else eval_features()


if __name__ == "__main__":
    main()
