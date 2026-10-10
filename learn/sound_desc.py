"""Predict the sound, not the knobs: the first test (`docs/sound-desc-plan.md`).

    $TORCH_PY -m learn.sound_desc targets                 # T(p): the average guitar through every preset
    $TORCH_PY -m learn.sound_desc windows                 # the declared training windows
    $TORCH_PY -m learn.sound_desc render --shard 0/6      # X = D(render) for each window × preset
    $TORCH_PY -m learn.sound_desc evaluate                # leave-band-out on real recordings
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import statistics
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import phase2_set3 as P  # noqa: E402

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/sound-desc"
POOLS = (HOME / "learn/poc/di-windows.json", HOME / "learn/direc/set3-di-windows.json")
AVERAGE = HOME / "learn/direc/cache/average-fold2.npy"
SR, PRE, KEEP = 48000, 2.0, 6.0
SEED = 20261011
PER_BAND = 12
N_MELS, FMIN, FMAX, NFFT, HOP = 64, 50.0, 16000.0, 2048, 512
GT = "Guitar-TECHS P1"


# --- the description ---------------------------------------------------------------

_MEL = {}


def _mel():
    if "m" not in _MEL:
        from analysis.aligned import _mel_matrix
        import analysis.aligned as A

        old = (A.FMIN, A.FMAX, A.MEL_BANDS)
        A.FMIN, A.FMAX, A.MEL_BANDS = FMIN, FMAX, N_MELS
        try:
            _MEL["m"] = _mel_matrix(NFFT, SR)[0]
        finally:
            A.FMIN, A.FMAX, A.MEL_BANDS = old
    return _MEL["m"]


def describe(x):
    """D(x): 64 mean-removed long-term log-mel bands, 64 per-band frame standard deviations,
    crest factor and the 90th–10th percentile spread of frame RMS (dB), over playing frames."""
    import numpy as np

    x = np.asarray(x, np.float64)
    x = x / (np.sqrt(np.mean(x ** 2)) + 1e-12)
    n = 1 + (len(x) - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    fr = x[idx]
    rms = 10 * np.log10(np.mean(fr ** 2, axis=1) + 1e-20)
    play = rms >= rms.max() - 40
    S = np.abs(np.fft.rfft(fr[play] * np.hanning(NFFT), axis=1)) ** 2
    L = 10 * np.log10(S @ _mel().T + 1e-12)
    tone = L.mean(axis=0)
    tone = tone - tone.mean()
    texture = L.std(axis=0)
    crest = 20 * np.log10(np.abs(x).max() / (np.sqrt(np.mean(x ** 2)) + 1e-12))
    spread = np.percentile(rms[play], 90) - np.percentile(rms[play], 10)
    return np.concatenate([tone, texture, [crest, spread]]).astype(np.float32)


def augment(x, rng):
    """A stand-in for mic and room: a ±3 dB tilt, a ±4 dB bell (200 Hz–5 kHz), noise
    50–70 dB below the signal."""
    import numpy as np

    n = len(x)
    f = np.maximum(np.fft.rfftfreq(n, 1 / SR), 20)
    lf = np.log2(f / 1000)
    tilt = rng.uniform(-3, 3) * np.clip(lf / 3.32, -1, 1)
    fc, g = rng.uniform(math.log2(200), math.log2(5000)), rng.uniform(-4, 4)
    bell = g * np.exp(-0.5 * ((np.log2(f) - fc) / 0.5) ** 2)
    y = np.fft.irfft(np.fft.rfft(x) * 10 ** ((tilt + bell) / 20), n)
    noise = rng.standard_normal(n) * np.sqrt(np.mean(y ** 2)) * 10 ** (-rng.uniform(50, 70) / 20)
    return y + noise


# --- the menu and the renderer -------------------------------------------------------

def renderer():
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    pack = load_pack("morgan")

    class PanelRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edits = self.commands[settings["panel"]]
            command = {"edits": edits}
            if select is not None:
                command["selectAmp"] = select
            return command

    r = PanelRenderer("morgan", process_policy="reuse")
    M = P.menus(pack, r)
    PanelRenderer.commands = {f"{amp}|{n}": v for amp, m in M.items() for n, v in m.items()}
    return r, M


def _render(r, di, key):
    import numpy as np

    y = np.asarray(r.render(di.astype(np.float32), {"panel": key}).audio, np.float64)
    return y.mean(axis=1) if y.ndim == 2 else y


# --- windows ---------------------------------------------------------------------------

def _pool():
    from learn import set3
    from learn import train as TR

    _, band_of = TR.k3_folds()
    rows = []
    for path in POOLS:
        for w in json.loads(path.read_text())["windows"]:
            if set3.is_held_out(w["file"]):
                raise ValueError(f"held-out window in a development pool: {w['file']}")
            rows.append(dict(w))
    return rows


G_BANDS = ("Ale Lak", "John Morgan Kimock", "Bernard Purdie Tribute All-Stars", "Cnoc An Tursa")


def average_windows():
    """G (plan v2): for each of 4 non-test bands, its first window by sorted path, then
    start, from either development pool."""
    pool = _pool()
    # amendment 6: the first window with activity of at least 0.9
    return [min((x for x in pool if x["band"] == b and x.get("active", 1.0) >= 0.9),
                key=lambda x: (x["file"], x["start_s"])) for b in G_BANDS]


def load_window(w):
    import numpy as np

    from analysis import io

    x = np.asarray(io.load(w["file"]).mono(), np.float64)
    a = int(w["start_s"] * SR)
    return x[a:a + int((PRE + KEEP) * SR)]


def targets():
    """T(p) for every menu preset of the three amps, from G at the average balance."""
    import numpy as np

    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to, to_lufs

    avg = np.load(AVERAGE)
    G = []
    for w in average_windows():
        di = load_window(w)
        own = smoothed_spectrum(di[int(PRE * SR):])
        G.append(to_lufs(eq_to(di, avg - (own - own.mean()))))
    r, M = renderer()
    T, TF = {}, {}
    try:
        for amp, m in M.items():
            for n in m:
                ds, frs = [], []
                for g in G:
                    _render(r, g, f"{amp}|template+R")        # flush the reused instance
                    y = _render(r, g, f"{amp}|{n}")[int(PRE * SR):]
                    ds.append(describe(y))
                    frs.append(y)
                T[f"{amp}|{n}"] = np.mean(ds, axis=0).tolist()
                # Stage 0 (plan v2): every declared description and gate, on 4.5-s segments.
                from learn import sound_desc_stage0 as S0
                for gate in S0.GATES:
                    per = []
                    for y in frs:
                        for a in (0, int(1.5 * SR)):
                            per.append(S0.descriptors(*S0.frames(y[a:a + int(4.5 * SR)]), gate))
                    for name in S0.NAMES:
                        TF.setdefault(name, {}).setdefault(gate, {})[f"{amp}|{n}"] = \
                            np.mean([d[name] for d in per], axis=0).tolist()
                print(amp, n, flush=True)
    finally:
        r.close()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "targets.json").write_text(json.dumps({"windows": average_windows(), "T": T}))
    (OUT / "targets-frames.json").write_text(json.dumps(TF))


def choose_windows():
    """Up to PER_BAND windows per band, seed SEED, from both development pools."""
    rows = _pool()
    by = {}
    for w in rows:
        by.setdefault(w["band"], []).append(w)
    rng = random.Random(SEED)
    out = []
    for band in sorted(by):
        ws = sorted(by[band], key=lambda x: (x["file"], x["start_s"]))
        out += rng.sample(ws, min(PER_BAND, len(ws)))
    for i, w in enumerate(out):
        w["id"] = f"w{i:04d}"
        w["gain_db"] = round(rng.uniform(-6, 6), 2)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "windows.json").write_text(json.dumps(out, indent=0))
    print(len(out), "windows from", len(by), "bands")


def render(shard):
    """For each declared window (its own balance, −22.9 LUFS + its gain) through every menu
    preset: D(render) and D(augmented render). Descriptors only."""
    import numpy as np

    from learn.direc_check import to_lufs

    ws = json.loads((OUT / "windows.json").read_text())[shard[0]::shard[1]]
    dest = OUT / "renders"
    dest.mkdir(parents=True, exist_ok=True)
    r, M = renderer()
    try:
        for w in ws:
            path = dest / f"{w['id']}.npz"
            if path.exists():
                continue
            raw = load_window(w)
            di = to_lufs(raw, -22.9 + w["gain_db"])
            rng = np.random.default_rng(int(w["id"][1:]) + SEED)
            keys, X, Xa = [], [], []
            for amp, m in M.items():
                _render(r, di, f"{amp}|template+R")
                for n in m:
                    y = _render(r, di, f"{amp}|{n}")[int(PRE * SR):]
                    keys.append(f"{amp}|{n}")
                    X.append(describe(y))
                    Xa.append(describe(augment(y, rng)))
            np.savez(path, keys=np.array(keys), X=np.array(X), Xa=np.array(Xa))
            print(w["id"], w["band"], flush=True)
    finally:
        r.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("targets", "windows", "render", "evaluate"))
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args(argv)
    if a.cmd == "targets":
        targets()
    elif a.cmd == "windows":
        choose_windows()
    elif a.cmd == "render":
        render(tuple(int(v) for v in a.shard.split("/")))
    else:
        from learn import sound_desc_eval

        sound_desc_eval.evaluate()


if __name__ == "__main__":
    main()
